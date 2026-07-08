# -*- coding: utf-8 -*-
"""
=============================================================================
LangGraph RAG 工作流 - 节点函数
=============================================================================

包含 4 个节点函数 + 1 个条件边函数：
- query_rewriter_node       节点1：把口语化问题改写为检索友好的 query
- retriever_node            节点2：向量检索
- relevance_grader_node     节点3：LLM 评估每个 chunk 的相关性
- answer_generator_node     节点4：生成最终答案
- should_retry              条件边：决定重检索还是生成答案

所有节点函数均做失败兜底，保证工作流不会因单点失败而崩溃。

=============================================================================
"""

from typing import Dict, Any, List
import json

from langchain_openai import ChatOpenAI

from config import LLM_API_KEY, LLM_API_BASE, LLM_MODEL
from services.document_service import (
    get_chroma_client,
    get_llm_client,
    build_context_from_chunks,
)
from rich.pretty import pprint

# ============================================================================
# 节点 1：查询改写
# ============================================================================


def _rewriter_llm() -> ChatOpenAI:
    """改写专用 LLM（低温度）"""
    return ChatOpenAI(
        model=LLM_MODEL,
        api_key=LLM_API_KEY,
        base_url=LLM_API_BASE,
        temperature=0.0,
    )


def query_rewriter_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """把口语化问题改写为关键词查询，便于向量检索"""
    query = state["query"]
    prompt = (
        "将以下用户问题改写为更适合向量检索的关键词查询。"
        "保留原意，去掉口语化表达，输出不超过 30 字。仅输出改写结果。\n"
        f"用户问题：{query}\n改写："
    )
    # print("prompt--------")
    # print(query)
    try:
        rewritten = _rewriter_llm().invoke(prompt).content.strip()
        pprint(f"rewritten--------{rewritten}")

        if not rewritten:
            rewritten = query
    except Exception:
        rewritten = query

    return {"rewritten_query": rewritten}


# ============================================================================
# 节点 2：向量检索
# ============================================================================


def retriever_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """向量检索，复用现有 similarity_search_with_score"""
    vectorstore = get_chroma_client()
    search_query = state.get("rewritten_query") or state["query"]
    try:
        docs = vectorstore.similarity_search_with_score(query=search_query, k=10)
        chunks: List[Dict[str, Any]] = [
            {
                "content": doc.page_content,
                "source": doc.metadata.get("source", "unknown"),
                "doc_id": doc.metadata.get("doc_id", ""),
                "distance": 1 - score,
                "chunk_id": (
                    f"{doc.metadata.get('doc_id', '')}_"
                    f"{doc.metadata.get('chunk_index', 0)}"
                ),
            }
            for doc, score in docs
        ]
    except Exception:
        chunks = []

    return {
        "retrieved_chunks": chunks,
        "retry_count": state.get("retry_count", 0) + 1,
    }


# ============================================================================
# 节点 3：相关性评估
# ============================================================================


def relevance_grader_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LLM 批量评估所有 chunk 的相关性，一次调用完成过滤"""
    query = state["query"]
    chunks = state.get("retrieved_chunks", []) or []
    if not chunks:
        return {"relevant_chunks": [], "is_relevant": False}

    # 构建批量评估 prompt
    chunks_text = "\n\n".join(
        f"[Chunk {i}] {chunk['content'][:400]}" for i, chunk in enumerate(chunks)
    )
    print(f"chunks_text--------{chunks_text}")
    prompt = f"""判断以下每个文档片段是否与问题相关。相关=包含直接回答问题的信息。

问题：{query}

{chunks_text}

请按以下 JSON 格式输出，仅输出 JSON，不要其他内容：
{{"results": [{{"index": 0, "relevant": true/false}}, ...]}}"""

    grader = ChatOpenAI(
        model=LLM_MODEL,
        api_key=LLM_API_KEY,
        base_url=LLM_API_BASE,
        temperature=0.0,
    )

    try:
        response = grader.invoke(prompt).content.strip()

        # 解析 JSON 结果
        json_match = response[response.find("{") : response.rfind("}") + 1]
        data = json.loads(json_match)
        indices = {r["index"] for r in data.get("results", []) if r.get("relevant")}
        print(f"indices--------{indices}")
        relevant = [chunks[i] for i in indices if i < len(chunks)]
    except Exception:
        # 解析失败时保守保留所有 chunk
        relevant = list(chunks)

    return {"relevant_chunks": relevant, "is_relevant": len(relevant) > 0}


# ============================================================================
# 节点 4：答案生成
# ============================================================================

_ANSWER_PROMPT_TEMPLATE = """你是一个专业的技术文档问答助手。你的任务是根据提供的文档片段回答用户的问题。

## 重要规则：
1. 只基于提供的文档内容回答，不要编造信息
2. 如果文档中包含多个来源的信息，可以进行对比分析
3. 如果某个问题涉及的参数在多个文档中都有提到，请明确指出每个来源的具体数值
4. 如果文档中没有相关信息，明确告知用户"根据当前文档无法回答此问题"
5. 回答要清晰、专业，使用列表或表格来组织对比信息（当涉及多文档对比时）

## 文档片段：
{context}

## 用户问题：
{query}

## 回答要求：
- 直接回答问题
- 指出信息来源
- 如果涉及对比，给出对比表格
"""


def answer_generator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """生成最终答案，输出形状与原 qa_search 完全一致"""
    query = state["query"]
    relevant = state.get("relevant_chunks") or []
    conversation_history = state.get("conversation_history") or []

    if not relevant:
        return {
            "answer": (
                "抱歉，没有找到与您问题相关的文档内容。"
                "请尝试上传相关文档或调整问题表述。"
            ),
            "sources": [],
            "used_chunks": 0,
            "groups": {},
            "total_retrieved": 0,
            "total_docs": 0,
        }

    context = build_context_from_chunks(relevant)

    # 如果有对话历史，使用增强的 prompt 以保留上下文
    if conversation_history:
        from services.rag_nodes_chat import build_conversation_prompt
        prompt = build_conversation_prompt(
            conversation_history=conversation_history,
            current_query=query,
        )
        # 把 context 注入到 prompt 中
        prompt = prompt.replace("{context}", context)
    else:
        prompt = _ANSWER_PROMPT_TEMPLATE.format(context=context, query=query)

    try:
        llm = get_llm_client()
        answer = llm.invoke(prompt).content
    except Exception as e:
        answer = f"抱歉，生成回答时出现错误：{str(e)}"

    # 按 source 分组（保持与原 retrieve_and_group 一致的结构）
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for chunk in relevant:
        groups.setdefault(chunk["source"], []).append(chunk)

    return {
        "answer": answer,
        "sources": sorted({c["source"] for c in relevant}),
        "used_chunks": len(relevant),
        "groups": groups,
        "total_retrieved": len(relevant),
        "total_docs": len(groups),
    }


# ============================================================================
# 条件边：决定重检索还是生成答案
# ============================================================================


def should_retry(state: Dict[str, Any]) -> str:
    """条件边：决定是回到 rewrite 还是进入 generate

    重试上限逻辑：
    - retry_count 在 retriever_node 中 +1
    - 初值 0，所以最多进入 retrieve 2 次（首轮 1 次 + 重试 1 次）
    - 当 retry_count >= 2 时强制进入 generate，避免无限循环
    """
    if state.get("is_relevant") or state.get("retry_count", 0) >= 2:
        return "generate"
    return "rewrite"

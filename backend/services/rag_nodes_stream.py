# -*- coding: utf-8 -*-
"""
=============================================================================
LangGraph RAG 工作流 - 流式输出节点
=============================================================================

提供流式输出的 answer_generator_node，可以将 LLM 生成过程以 chunk 形式
逐步返回给调用方。

使用：
    from services.rag_nodes_stream import answer_generator_stream_node
    for state in stream_workflow(initial_state):
        print(state)

=============================================================================
"""

from typing import Dict, Any, List, Iterator
import json
import asyncio
import queue
import threading

from langchain_openai import ChatOpenAI

from config import LLM_API_KEY, LLM_API_BASE, LLM_MODEL
from services.document_service import build_context_from_chunks, get_llm_client
from services.rag_nodes_chat import build_conversation_prompt


def answer_generator_stream_node(
    state: Dict[str, Any],
) -> Iterator[Dict[str, Any]]:
    """
    流式版本的 answer_generator_node

    行为与 answer_generator_node 相同（同样的输入产出同样的最终结果），
    区别在于 LLM 答案生成阶段会逐步 yield 出部分内容：

    - 首次 yield: {"_stream": "answer_start"}
    - 中间 yield: {"_stream": "answer_chunk", "delta": "...", "answer": "...累计..."}
    - 末尾 yield: 完整的最终状态（与原节点字段一致）

    调用方在拿到第一个 start chunk 后，会按 chunk 累计到 answer 字段。
    """
    query = state["query"]
    relevant = state.get("relevant_chunks") or []
    conversation_history = state.get("conversation_history") or []

    if not relevant:
        result = {
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
        yield {"_stream": "answer_start"}
        yield {"_stream": "answer_chunk", "delta": result["answer"], "answer": result["answer"]}
        yield result
        return

    context = build_context_from_chunks(relevant)

    if conversation_history:
        prompt = build_conversation_prompt(
            conversation_history=conversation_history,
            current_query=query,
        )
        prompt = prompt.replace("{context}", context)
    else:
        from services.rag_nodes import _ANSWER_PROMPT_TEMPLATE

        prompt = _ANSWER_PROMPT_TEMPLATE.format(context=context, query=query)

    # 发出开始信号
    yield {"_stream": "answer_start"}

    # 同步 LLM 流式调用（通过线程 + queue 在生成器内桥接）
    q: queue.Queue = queue.Queue()
    error_holder: List[Exception] = []

    def _stream_in_thread():
        try:
            llm = get_llm_client()
            for chunk in llm.stream(prompt):
                content = chunk.content
                if content:
                    q.put(("data", content))
            q.put(("done", None))
        except Exception as e:
            error_holder.append(e)
            q.put(("error", e))

    t = threading.Thread(target=_stream_in_thread, daemon=True)
    t.start()

    accumulated = ""
    while True:
        kind, payload = q.get()
        if kind == "done":
            break
        if kind == "error":
            err_msg = f"抱歉，生成回答时出现错误：{str(payload)}"
            accumulated = err_msg
            yield {
                "_stream": "answer_chunk",
                "delta": err_msg,
                "answer": err_msg,
            }
            break
        if kind == "data":
            accumulated += payload
            yield {
                "_stream": "answer_chunk",
                "delta": payload,
                "answer": accumulated,
            }

    # 按 source 分组
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for chunk in relevant:
        groups.setdefault(chunk["source"], []).append(chunk)

    final = {
        "answer": accumulated,
        "sources": sorted({c["source"] for c in relevant}),
        "used_chunks": len(relevant),
        "groups": groups,
        "total_retrieved": len(relevant),
        "total_docs": len(groups),
    }
    yield final

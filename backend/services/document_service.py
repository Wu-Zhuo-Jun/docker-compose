# -*- coding: utf-8 -*-
"""
=============================================================================
文档服务模块
=============================================================================

功能:
- 解析 Word 文档 (.docx)
- 语义分块 (Semantic Chunking)
- 向量化存储到 ChromaDB
- 两阶段检索 + LLM 整合
- 问答机器人

=============================================================================
"""

import uuid
import io
from typing import List, Dict, Any, Optional, Tuple
from docx import Document
from docx.text.paragraph import Paragraph
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LCDocument
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
import chromadb
from chromadb.config import Settings
import os

from config import CHROMA_HOST, CHROMA_PORT, LLM_API_KEY, LLM_API_BASE, LLM_MODEL

# 获取 API Key
_deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
if not _deepseek_api_key:
    raise ValueError("请设置 DEEPSEEK_API_KEY 环境变量")


# ============================================================================
# ChromaDB 客户端管理
# ============================================================================

_chroma_client: Optional[chromadb.PersistentClient] = None


def get_chroma_client() -> chromadb.PersistentClient:
    """获取 ChromaDB 客户端（单例）"""
    global _chroma_client
    if _chroma_client is None:
        persist_dir = os.environ.get("CHROMA_PERSIST_DIR", "/app/chroma_data")
        os.makedirs(persist_dir, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )
    return _chroma_client


# ============================================================================
# Embedding 配置
# ============================================================================


def get_embeddings():
    """获取 Embedding 函数（使用 DeepSeek）"""
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_base="https://api.deepseek.com",
        openai_api_key=_deepseek_api_key,
    )


# ============================================================================
# Word 文档解析
# ============================================================================


def extract_heading_chain(
    paragraphs: List[Paragraph],
) -> Dict[int, Tuple[int, str, str]]:
    """
    提取文档中的标题结构

    Returns:
        Dict[paragraph_index, (level, heading_text, full_chain)]
        例如: {3: (1, "第一章", "第一章"), 7: (2, "第一节", "第一章 > 第一节")}
    """
    heading_info = {}
    current_chain: List[str] = []

    for idx, para in enumerate(paragraphs):
        if para.style.name.startswith("Heading"):
            # 提取标题级别
            level = (
                int(para.style.name.replace("Heading ", ""))
                if "Heading " in para.style.name
                else 1
            )
            text = para.text.strip()

            # 更新标题链
            current_chain = current_chain[: level - 1] + [text]
            full_chain = " > ".join(current_chain)

            heading_info[idx] = (level, text, full_chain)

    return heading_info


def parse_word_document(file_content: bytes) -> Tuple[str, List[Tuple[str, str, int]]]:
    """
    解析 Word 文档，提取文本和标题信息

    Returns:
        (full_text, [(paragraph_text, heading_chain, para_index), ...])
    """
    doc = Document(io.BytesIO(file_content))
    paragraphs = list(doc.paragraphs)
    heading_info = extract_heading_chain(paragraphs)

    content_items = []
    full_text_parts = []

    for idx, para in enumerate(paragraphs):
        text = para.text.strip()
        if not text:
            continue

        full_text_parts.append(text)

        # 获取该段落的标题链
        heading_chain = ""
        for i in range(idx, -1, -1):
            if i in heading_info:
                heading_chain = heading_info[i][2]
                break

        content_items.append((text, heading_chain, idx))

    # 提取表格内容
    table_items, table_text = extract_tables(doc, len(paragraphs), heading_info)
    content_items.extend(table_items)

    if table_text:
        full_text_parts.append(table_text)

    full_text = "\n\n".join(full_text_parts)
    return full_text, content_items


def extract_tables(
    doc: Document, base_index: int, heading_info: Dict[int, Tuple[int, str, str]]
) -> Tuple[List[Tuple[str, str, int]], str]:
    """
    从 Word 文档中提取表格内容

    Args:
        doc: Document 对象
        base_index: 基础段落索引，用于计算表格索引
        heading_info: 标题信息字典

    Returns:
        (table_items, table_text): 表格项列表和合并的表格文本
    """
    table_items = []
    table_text_parts = []

    for table_idx, table in enumerate(doc.tables):
        table_index = base_index + table_idx
        table_text = format_table_as_text(table)

        if table_text.strip():
            table_items.append((table_text, "[表格]", table_index))
            table_text_parts.append(table_text)

    table_text = (
        "\n\n[表格内容]\n" + "\n".join(table_text_parts) if table_text_parts else ""
    )
    return table_items, table_text


def format_table_as_text(table) -> str:
    """
    将表格格式化为易读的文本格式

    使用分隔符将表格行列转换为文本，保留表格结构信息。
    """
    if not table.rows:
        return ""

    rows_text = []
    for row in table.rows:
        cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
        row_text = " | ".join(cells)
        if row_text.strip():
            rows_text.append(row_text)

    if not rows_text:
        return ""

    return "\n".join(rows_text)


# ============================================================================
# 语义分块
# ============================================================================


def semantic_chunk_documents(text: str) -> List[LCDocument]:
    """
    使用递归字符分块将文本分割成块

    按段落和字符长度递归分割，保持语义完整性。
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,  # 每个块的最大字符数
        chunk_overlap=100,  # 块之间的重叠字符数
        separators=["\n\n", "\n", "。", "！", "？", " ", ""],  # 分割符优先级
    )

    return splitter.create_documents([text])


# ============================================================================
# 文档上传
# ============================================================================


def upload_document(file_content: bytes, filename: str) -> Dict[str, Any]:
    """
    上传并处理 Word 文档

    Args:
        file_content: 文件二进制内容
        filename: 文件名

    Returns:
        {"doc_id": str, "chunk_count": int, "chunks": list}
    """
    # 1. 解析文档
    full_text, content_items = parse_word_document(file_content)

    if not full_text.strip():
        raise ValueError("文档内容为空")

    # 2. 语义分块
    langchain_docs = semantic_chunk_documents(full_text)

    # 3. 获取 ChromaDB 集合
    client = get_chroma_client()
    collection_name = "documents"

    try:
        collection = client.get_collection(name=collection_name)
    except Exception:
        # 集合不存在则创建
        embeddings = get_embeddings()
        collection = client.create_collection(
            name=collection_name,
            embedding_function=embeddings.embed_documents,
            metadata={"description": "Word documents chunks"},
        )

    # 4. 准备数据并存储
    doc_id = str(uuid.uuid4())
    documents = []
    metadatas = []
    ids = []

    for idx, doc in enumerate(langchain_docs):
        chunk_id = f"{doc_id}_{idx}"
        documents.append(doc.page_content)
        metadatas.append(
            {
                "source": filename,
                "doc_id": doc_id,
                "chunk_index": idx,
                "total_chunks": len(langchain_docs),
            }
        )
        ids.append(chunk_id)

    collection.add(documents=documents, metadatas=metadatas, ids=ids)

    return {
        "doc_id": doc_id,
        "filename": filename,
        "chunk_count": len(documents),
        "chunks": [
            {
                "id": chunk_id,
                "content": doc.page_content[:200] + "..."
                if len(doc.page_content) > 200
                else doc.page_content,
            }
            for chunk_id, doc in zip(ids, langchain_docs)
        ],
    }


# ============================================================================
# 文档检索 - 基础检索
# ============================================================================


def search_documents(
    query: str, top_k: int = 5, doc_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    搜索文档（基础检索）

    Args:
        query: 查询文本
        top_k: 返回结果数量
        doc_id: 可选，限定在某个文档内搜索

    Returns:
        {"results": [...], "query": str}
    """
    client = get_chroma_client()

    try:
        collection = client.get_collection(name="documents")
    except Exception:
        return {"results": [], "query": query, "message": "No documents found"}

    # 构建查询条件
    where_filter = {"doc_id": doc_id} if doc_id else None

    # 执行相似度搜索
    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    # 格式化结果
    formatted_results = []
    if results["documents"] and results["documents"][0]:
        for i, doc in enumerate(results["documents"][0]):
            formatted_results.append(
                {
                    "content": doc,
                    "metadata": results["metadatas"][0][i]
                    if results["metadatas"]
                    else {},
                    "distance": results["distances"][0][i]
                    if results["distances"]
                    else 0,
                    "chunk_id": results["ids"][0][i] if results["ids"] else "",
                }
            )

    return {
        "query": query,
        "results": formatted_results,
        "total": len(formatted_results),
    }


# ============================================================================
# 两阶段检索 + LLM 整合
# ============================================================================


def retrieve_and_group(query: str, top_k: int = 10) -> Dict[str, Any]:
    """
    第一阶段：检索并按文档分组

    Args:
        query: 查询文本
        top_k: 检索数量（不限制，让 LLM 做筛选）

    Returns:
        {"groups": {doc_name: [chunks]}, "all_chunks": [...]}
    """
    client = get_chroma_client()

    try:
        collection = client.get_collection(name="documents")
    except Exception:
        return {"groups": {}, "all_chunks": [], "message": "No documents found"}

    # 执行相似度搜索，获取更多结果
    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    # 解析结果
    all_chunks = []
    if results["documents"] and results["documents"][0]:
        for i, doc in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            all_chunks.append({
                "content": doc,
                "source": metadata.get("source", "unknown"),
                "doc_id": metadata.get("doc_id", ""),
                "distance": results["distances"][0][i] if results["distances"] else 0,
                "chunk_id": results["ids"][0][i] if results["ids"] else "",
            })

    # 按文档分组
    groups = {}
    for chunk in all_chunks:
        source = chunk["source"]
        if source not in groups:
            groups[source] = []
        groups[source].append(chunk)

    return {
        "groups": groups,
        "all_chunks": all_chunks,
        "total_chunks": len(all_chunks),
        "total_docs": len(groups),
    }


def get_llm_client() -> ChatOpenAI:
    """获取 LLM 客户端（单例）"""
    return ChatOpenAI(
        model=LLM_MODEL,
        api_key=LLM_API_KEY,
        base_url=LLM_API_BASE,
        temperature=0.3,  # 低温度，更准确的回答
    )


def build_context_from_chunks(all_chunks: List[Dict]) -> str:
    """
    将 chunks 构建为 LLM 上下文

    Args:
        all_chunks: 检索到的 chunks 列表

    Returns:
        格式化的上下文字符串
    """
    if not all_chunks:
        return "未找到相关文档内容。"

    # 按文档分组构建上下文
    context_parts = []
    current_source = None

    for chunk in all_chunks:
        source = chunk.get("source", "未知来源")
        content = chunk.get("content", "")

        # 如果换了文档来源，添加分隔
        if source != current_source:
            if current_source is not None:
                context_parts.append("")
            context_parts.append(f"【{source}】")
            current_source = source

        context_parts.append(f"- {content}")

    return "\n".join(context_parts)


def generate_answer_with_llm(query: str, chunks: List[Dict]) -> Dict[str, Any]:
    """
    第二阶段：使用 LLM 整合检索结果生成答案

    Args:
        query: 用户问题
        chunks: 检索到的相关 chunks

    Returns:
        {"answer": str, "sources": [...], "used_chunks": int}
    """
    if not chunks:
        return {
            "answer": "抱歉，没有找到与您问题相关的文档内容。请尝试上传相关文档或调整问题表述。",
            "sources": [],
            "used_chunks": 0,
        }

    # 构建上下文
    context = build_context_from_chunks(chunks)

    # 构建 Prompt（直接使用字符串）
    prompt = f"""你是一个专业的技术文档问答助手。你的任务是根据提供的文档片段回答用户的问题。

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

    # 调用 LLM
    llm = get_llm_client()

    try:
        response = llm.invoke(prompt)
        answer = response.content
    except Exception as e:
        answer = f"抱歉，生成回答时出现错误：{str(e)}"

    # 提取来源信息
    sources = list(set([chunk.get("source", "未知") for chunk in chunks]))

    return {
        "answer": answer,
        "sources": sources,
        "used_chunks": len(chunks),
    }


def qa_search(query: str, top_k: int = 10) -> Dict[str, Any]:
    """
    问答式搜索（两阶段检索 + LLM 整合）

    流程：
    1. 检索：向量搜索获取相关 chunks
    2. 分组：按文档分组
    3. 整合：LLM 分析并生成答案

    Args:
        query: 用户问题
        top_k: 检索数量

    Returns:
        {
            "answer": str,           # LLM 生成的回答
            "sources": [...],         # 涉及的文档列表
            "used_chunks": int,       # 使用的 chunk 数量
            "groups": {...},          # 按文档分组的结果（供前端展示）
        }
    """
    # 第一阶段：检索并分组
    retrieval_result = retrieve_and_group(query, top_k)

    if retrieval_result["total_chunks"] == 0:
        return {
            "answer": "抱歉，没有找到与您问题相关的文档内容。请尝试上传相关文档或调整问题表述。",
            "sources": [],
            "used_chunks": 0,
            "groups": {},
            "query": query,
        }

    # 第二阶段：LLM 整合
    llm_result = generate_answer_with_llm(query, retrieval_result["all_chunks"])

    return {
        "answer": llm_result["answer"],
        "sources": llm_result["sources"],
        "used_chunks": llm_result["used_chunks"],
        "groups": retrieval_result["groups"],  # 返回分组信息供前端展示
        "query": query,
        "total_retrieved": retrieval_result["total_chunks"],
        "total_docs": retrieval_result["total_docs"],
    }


# ============================================================================
# 文档管理
# ============================================================================


def list_documents() -> List[Dict[str, Any]]:
    """列出所有已上传的文档"""
    client = get_chroma_client()

    try:
        collection = client.get_collection(name="documents")
    except Exception:
        return []

    # 获取所有唯一的文档
    all_data = collection.get(include=["metadatas"])

    if not all_data or not all_data.get("ids"):
        return []

    # 按 doc_id 分组
    docs_map = {}
    for i, metadata in enumerate(all_data.get("metadatas", [])):
        if metadata:
            doc_id = metadata.get("doc_id")
            if doc_id and doc_id not in docs_map:
                docs_map[doc_id] = {
                    "doc_id": doc_id,
                    "source": metadata.get("source", "unknown"),
                    "total_chunks": metadata.get("total_chunks", 0),
                    "chunk_ids": [],
                }
            if doc_id:
                docs_map[doc_id]["chunk_ids"].append(all_data["ids"][i])

    return list(docs_map.values())


def delete_document(doc_id: str) -> Dict[str, Any]:
    """删除指定文档的所有块"""
    client = get_chroma_client()

    try:
        collection = client.get_collection(name="documents")
    except Exception:
        return {"success": False, "message": "Collection not found"}

    # 获取该文档的所有块 ID
    all_data = collection.get(include=["metadatas"])

    chunk_ids = []
    for i, metadata in enumerate(all_data.get("metadatas", [])):
        if metadata and metadata.get("doc_id") == doc_id:
            chunk_ids.append(all_data["ids"][i])

    if not chunk_ids:
        return {"success": False, "message": "Document not found"}

    collection.delete(ids=chunk_ids)

    return {"success": True, "deleted_chunks": len(chunk_ids)}

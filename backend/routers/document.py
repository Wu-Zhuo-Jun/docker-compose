# -*- coding: utf-8 -*-
"""
=============================================================================
文档管理路由
=============================================================================

提供文档上传、搜索、管理接口

=============================================================================
"""

from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from services.document_service import (
    upload_document,
    search_documents,
    qa_search,
    list_documents,
    delete_document
)


router = APIRouter(prefix="/documents", tags=["文档管理"])


# ============================================================================
# 请求/响应模型
# ============================================================================


class SearchRequest(BaseModel):
    """搜索请求（基础检索）"""
    query: str
    top_k: Optional[int] = 5
    doc_id: Optional[str] = None


class SearchResponse(BaseModel):
    """搜索响应"""
    query: str
    results: list
    total: int


class QASearchRequest(BaseModel):
    """问答式搜索请求"""
    query: str
    top_k: Optional[int] = 10  # 默认检索更多结果给 LLM


class QASearchResponse(BaseModel):
    """问答式搜索响应"""
    answer: str           # LLM 生成的回答
    sources: list         # 涉及的文档列表
    used_chunks: int      # 使用的 chunk 数量
    groups: dict          # 按文档分组的结果
    query: str
    total_retrieved: int  # 检索到的总 chunk 数
    total_docs: int       # 涉及的文档数量


class DocumentListItem(BaseModel):
    """文档列表项"""
    doc_id: str
    source: str
    total_chunks: int
    chunk_ids: list


# ============================================================================
# 上传接口
# ============================================================================


@router.post("/upload")
async def upload_document_file(file: UploadFile = File(...)):
    """
    上传 Word 文档

    支持 .docx 格式，会自动进行语义分块和向量化存储
    """
    # 检查文件类型
    if not file.filename.endswith(".docx"):
        raise HTTPException(
            status_code=400,
            detail="只支持 .docx 格式的 Word 文档"
        )

    try:
        content = await file.read()
        result = upload_document(content, file.filename)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理文档失败: {str(e)}")


# ============================================================================
# 搜索接口
# ============================================================================


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    搜索文档内容（基础检索）

    Args:
        query: 查询文本
        top_k: 返回结果数量（默认 5）
        doc_id: 可选，限定在某个文档内搜索
    """
    try:
        result = search_documents(
            query=request.query,
            top_k=request.top_k,
            doc_id=request.doc_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.post("/qa", response_model=QASearchResponse)
async def qa_search_endpoint(request: QASearchRequest):
    """
    问答式搜索（两阶段检索 + LLM 整合）

    流程：
    1. 向量检索获取相关 chunks
    2. 按文档分组
    3. LLM 整合分析生成答案

    Args:
        query: 用户问题
        top_k: 检索数量（默认 10）
    """
    try:
        result = qa_search(
            query=request.query,
            top_k=request.top_k
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"问答搜索失败: {str(e)}")


# ============================================================================
# 文档管理接口
# ============================================================================


@router.get("/list")
async def get_document_list():
    """获取已上传文档列表"""
    try:
        documents = list_documents()
        return {"documents": documents, "total": len(documents)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取列表失败: {str(e)}")


@router.delete("/{doc_id}")
async def delete_document_by_id(doc_id: str):
    """删除指定文档"""
    try:
        result = delete_document(doc_id)
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

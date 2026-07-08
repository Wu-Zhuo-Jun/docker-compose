# -*- coding: utf-8 -*-
"""
=============================================================================
文档管理路由（带审核功能）
=============================================================================

提供文档上传、搜索、管理、审核接口。

工作流:
1. 用户上传文档 -> 进入 pending 状态，保存到 pending_documents 表
2. Admin 在审核列表中看到 pending 文档
3. Admin 审批通过 -> 触发文档索引（向量化到 ChromaDB）-> status=approved
4. Admin 拒绝 -> 删除 pending_documents 中的内容 -> status=rejected

注意:
- 本文件中保留 upload_document_file 直接上传（admin 用），供向后兼容
- 普通用户走 /documents/upload_pending 走审核流

=============================================================================
"""

import uuid
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from services.database import get_db
from services.document_service import (
    upload_document,
    search_documents,
    qa_search,
    list_documents,
    delete_document,
)
from db_models import (
    DocumentReview,
    PendingDocument,
    User,
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
    top_k: Optional[int] = 10


class QASearchResponse(BaseModel):
    """问答式搜索响应"""

    answer: str
    sources: list
    used_chunks: int
    groups: dict
    query: str
    total_retrieved: int
    total_docs: int


class DocumentListItem(BaseModel):
    """文档列表项"""

    doc_id: str
    source: str
    total_chunks: int
    chunk_ids: list


class ReviewRequest(BaseModel):
    """审批请求"""

    comment: Optional[str] = None
    reviewer_id: int


class PendingDocumentResponse(BaseModel):
    """待审核文档响应"""

    id: str
    doc_id: str
    filename: str
    uploader_id: int
    uploader_username: Optional[str] = None
    created_at: str


class ReviewListResponse(BaseModel):
    """审核列表响应"""

    id: str
    doc_id: str
    filename: str
    uploader_id: int
    uploader_username: Optional[str] = None
    status: str
    reviewer_id: Optional[int] = None
    reviewer_username: Optional[str] = None
    review_comment: Optional[str] = None
    created_at: str
    reviewed_at: Optional[str] = None


class UploadPendingResponse(BaseModel):
    """上传到待审核的响应"""

    doc_id: str
    review_id: str
    filename: str
    status: str = "pending"
    message: str = "文档已提交审核，等待管理员审批"


# ============================================================================
# 上传接口
# ============================================================================


def _check_file_type(filename: str) -> None:
    """检查文件类型"""
    if not (filename.endswith(".docx") or filename.endswith(".txt")):
        raise HTTPException(
            status_code=400,
            detail="只支持 .docx 格式的 Word 文档和 .txt 格式的文本文件",
        )


@router.post("/upload")
async def upload_document_file(file: UploadFile = File(...)):
    """
    直接上传文档（管理员用，兼容旧接口，立即向量化）

    普通用户请使用 /documents/upload-pending 走审核流程。
    """
    _check_file_type(file.filename)
    try:
        content = await file.read()
        result = upload_document(content, file.filename)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理文档失败: {str(e)}")


@router.post("/upload-pending", response_model=UploadPendingResponse)
async def upload_pending_document(
    file: UploadFile = File(...),
    uploader_id: int = Query(..., description="上传者用户ID"),
    db: Session = Depends(get_db),
):
    """
    上传文档到待审核列表（普通用户用）

    流程：
    1. 解析文档内容，存入 pending_documents 表
    2. 在 document_reviews 表创建审核记录（status=pending）
    3. 等待管理员审批后才会被索引到 ChromaDB
    """
    _check_file_type(file.filename)

    # 检查上传者是否存在
    uploader = db.query(User).filter(User.id == uploader_id).first()
    if not uploader:
        raise HTTPException(status_code=404, detail="用户不存在")

    try:
        content = await file.read()

        # 解析文档原始文本（用于后续索引）
        from services.document_service import parse_word_document, parse_txt_document

        if file.filename.lower().endswith(".txt"):
            full_text, _ = parse_txt_document(content)
        else:
            full_text, _ = parse_word_document(content)

        if not full_text.strip():
            raise HTTPException(status_code=400, detail="文档内容为空")

        # 1. 创建 doc_id
        doc_id = uuid.uuid4()

        # 2. 存储到 pending_documents
        pending_doc = PendingDocument(
            id=uuid.uuid4(),
            doc_id=doc_id,
            filename=file.filename,
            content=full_text,
            uploader_id=uploader_id,
        )
        db.add(pending_doc)

        # 3. 创建审核记录
        review = DocumentReview(
            id=uuid.uuid4(),
            doc_id=doc_id,
            filename=file.filename,
            uploader_id=uploader_id,
            status="pending",
        )
        db.add(review)
        db.commit()
        db.refresh(review)

        return UploadPendingResponse(
            doc_id=str(doc_id),
            review_id=str(review.id),
            filename=file.filename,
            status="pending",
            message="文档已提交审核，等待管理员审批",
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"上传文档失败: {str(e)}")


# ============================================================================
# 搜索接口
# ============================================================================


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """搜索文档内容（基础检索）"""
    try:
        result = search_documents(
            query=request.query, top_k=request.top_k, doc_id=request.doc_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.post("/qa", response_model=QASearchResponse)
async def qa_search_endpoint(request: QASearchRequest):
    """问答式搜索（两阶段检索 + LLM 整合）"""
    try:
        result = qa_search(query=request.query, top_k=request.top_k)
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
    """删除指定文档（ChromaDB 中已索引的）"""
    try:
        result = delete_document(doc_id)
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


# ============================================================================
# 文档审核接口
# ============================================================================


def _check_admin(user_id: int, db: Session) -> User:
    """检查用户是否为管理员"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


def _build_review_response(review: DocumentReview, db: Session) -> ReviewListResponse:
    """构建审核响应"""
    uploader = db.query(User).filter(User.id == review.uploader_id).first()
    reviewer = (
        db.query(User).filter(User.id == review.reviewer_id).first()
        if review.reviewer_id
        else None
    )
    return ReviewListResponse(
        id=str(review.id),
        doc_id=str(review.doc_id),
        filename=review.filename,
        uploader_id=review.uploader_id,
        uploader_username=uploader.username if uploader else None,
        status=review.status,
        reviewer_id=review.reviewer_id,
        reviewer_username=reviewer.username if reviewer else None,
        review_comment=review.review_comment,
        created_at=review.created_at.isoformat() if review.created_at else "",
        reviewed_at=review.reviewed_at.isoformat() if review.reviewed_at else None,
    )


@router.get("/reviews/pending", response_model=List[ReviewListResponse])
def list_pending_reviews(
    admin_id: int = Query(..., description="管理员ID"),
    db: Session = Depends(get_db),
):
    """获取所有待审核文档列表（管理员用）"""
    _check_admin(admin_id, db)

    reviews = (
        db.query(DocumentReview)
        .filter(DocumentReview.status == "pending")
        .order_by(DocumentReview.created_at.desc())
        .all()
    )
    return [_build_review_response(r, db) for r in reviews]


@router.get("/reviews/all", response_model=List[ReviewListResponse])
def list_all_reviews(
    admin_id: int = Query(..., description="管理员ID"),
    status: Optional[str] = Query(None, description="筛选状态: pending/approved/rejected"),
    db: Session = Depends(get_db),
):
    """获取所有审核记录（管理员用）"""
    _check_admin(admin_id, db)

    query = db.query(DocumentReview)
    if status:
        query = query.filter(DocumentReview.status == status)
    reviews = query.order_by(DocumentReview.created_at.desc()).all()
    return [_build_review_response(r, db) for r in reviews]


@router.post("/reviews/{review_id}/approve")
def approve_review(
    review_id: str,
    request: ReviewRequest,
    db: Session = Depends(get_db),
):
    """
    审批通过文档（管理员用）

    流程：
    1. 校验审核记录和待审核文档
    2. 从 pending_documents 取出原始内容
    3. 调用 upload_document 向量化到 ChromaDB
    4. 更新审核状态为 approved
    5. 删除 pending_documents 中的临时内容
    """
    _check_admin(request.reviewer_id, db)

    # 校验 review_id
    try:
        rid = uuid.UUID(review_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的审核ID格式")

    review = db.query(DocumentReview).filter(DocumentReview.id == rid).first()
    if not review:
        raise HTTPException(status_code=404, detail="审核记录不存在")
    if review.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"该文档已被处理（状态: {review.status}）",
        )

    # 查找 pending_documents 中的内容
    pending = (
        db.query(PendingDocument)
        .filter(PendingDocument.doc_id == review.doc_id)
        .first()
    )
    if not pending:
        raise HTTPException(status_code=404, detail="待审核文档内容丢失")

    try:
        # 触发文档索引 - 写入 ChromaDB
        # 由于 upload_document 内部会重新生成 doc_id，
        # 这里直接处理 chunks 写入，保持原 doc_id 一致
        from services.document_service import semantic_chunk_documents, get_chroma_client
        from langchain_core.documents import Document as LCDocument

        langchain_docs = semantic_chunk_documents(pending.content)
        vectorstore = get_chroma_client()

        lc_documents = []
        for idx, doc in enumerate(langchain_docs):
            lc_documents.append(
                LCDocument(
                    page_content=doc.page_content,
                    metadata={
                        "source": pending.filename,
                        "doc_id": str(review.doc_id),
                        "chunk_index": idx,
                        "total_chunks": len(langchain_docs),
                    },
                )
            )

        vectorstore.add_documents(documents=lc_documents)

        # 更新审核状态
        review.approve(reviewer_id=request.reviewer_id, comment=request.comment)

        # 删除 pending_documents 中的临时内容（已索引）
        db.delete(pending)
        db.commit()

        return {
            "success": True,
            "review_id": str(review.id),
            "doc_id": str(review.doc_id),
            "status": "approved",
            "message": "文档已审批通过并完成索引",
            "chunk_count": len(lc_documents),
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"审批失败: {str(e)}")


@router.post("/reviews/{review_id}/reject")
def reject_review(
    review_id: str,
    request: ReviewRequest,
    db: Session = Depends(get_db),
):
    """审批拒绝文档（管理员用）"""
    _check_admin(request.reviewer_id, db)

    try:
        rid = uuid.UUID(review_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的审核ID格式")

    review = db.query(DocumentReview).filter(DocumentReview.id == rid).first()
    if not review:
        raise HTTPException(status_code=404, detail="审核记录不存在")
    if review.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"该文档已被处理（状态: {review.status}）",
        )

    try:
        # 更新审核状态
        review.reject(reviewer_id=request.reviewer_id, comment=request.comment)

        # 删除 pending_documents 中的临时内容
        pending = (
            db.query(PendingDocument)
            .filter(PendingDocument.doc_id == review.doc_id)
            .first()
        )
        if pending:
            db.delete(pending)

        db.commit()

        return {
            "success": True,
            "review_id": str(review.id),
            "doc_id": str(review.doc_id),
            "status": "rejected",
            "message": "文档已被拒绝",
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"拒绝失败: {str(e)}")
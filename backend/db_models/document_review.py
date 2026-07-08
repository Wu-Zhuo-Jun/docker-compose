# -*- coding: utf-8 -*-
"""
=============================================================================
Document Review Models - 文档审核模型
=============================================================================

用于文档审核功能：
- DocumentReview: 记录文档审核状态和审核信息
- PendingDocument: 存储待审核文档的原始内容（索引前）

审核流程：
1. 用户上传文档 -> PendingDocument + DocumentReview(status=pending)
2. Admin 审批通过 -> 触发文档索引 -> DocumentReview(status=approved)
3. Admin 拒绝 -> DocumentReview(status=rejected) + 清理 PendingDocument

=============================================================================
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from services.database import Base


class DocumentReview(Base):
    """文档审核记录表"""
    __tablename__ = "document_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doc_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(20), default="pending", nullable=False)  # pending / approved / rejected
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    reviewed_at = Column(DateTime, nullable=True)

    uploader = relationship("User", foreign_keys=[uploader_id])
    reviewer = relationship("User", foreign_keys=[reviewer_id])

    def approve(self, reviewer_id: int, comment: str = None):
        """审批通过"""
        self.status = "approved"
        self.reviewer_id = reviewer_id
        self.review_comment = comment
        self.reviewed_at = func.now()

    def reject(self, reviewer_id: int, comment: str = None):
        """审批拒绝"""
        self.status = "rejected"
        self.reviewer_id = reviewer_id
        self.review_comment = comment
        self.reviewed_at = func.now()


class PendingDocument(Base):
    """待审核文档内容表（索引前的原始内容）"""
    __tablename__ = "pending_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doc_id = Column(UUID(as_uuid=True), nullable=False, index=True, unique=True)
    filename = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)  # 原始文本内容
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    uploader = relationship("User")

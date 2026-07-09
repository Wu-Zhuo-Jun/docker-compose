# -*- coding: utf-8 -*-
"""
=============================================================================
Chat 会话路由 - 多轮对话 API
=============================================================================

提供会话管理和多轮问答接口：
- GET  /chat/sessions      - 获取用户所有会话列表
- POST /chat/sessions      - 创建新会话
- GET  /chat/sessions/{id} - 获取会话详情（含消息）
- DELETE /chat/sessions/{id} - 删除会话
- POST /chat/qa            - 多轮问答
- POST /chat/qa/stream     - 多轮问答（SSE 流式输出）
- PATCH /chat/sessions/{id} - 更新会话（如自动生成标题）

=============================================================================
"""

import uuid
import json
import asyncio
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from services.database import get_db
from db_models import User, ChatSession, ChatMessage


router = APIRouter(prefix="/chat", tags=["对话"])


# ============================================================================
# 请求/响应模型
# ============================================================================


class CreateSessionRequest(BaseModel):
    """创建会话请求"""

    title: Optional[str] = "新对话"


class SessionResponse(BaseModel):
    """会话响应"""

    id: str
    user_id: int
    title: str
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    """消息响应"""

    id: str
    session_id: str
    role: str
    content: str
    metadata: Optional[dict] = None
    created_at: str


class SessionDetailResponse(BaseModel):
    """会话详情响应"""

    session: SessionResponse
    messages: List[MessageResponse]


class QARequest(BaseModel):
    """多轮问答请求"""

    session_id: Optional[str] = None  # 可选，新建会话时为空
    query: str
    top_k: int = Field(default=10, ge=1, le=50)


class QAResponse(BaseModel):
    """多轮问答响应"""

    session_id: str
    message_id: str
    answer: str
    sources: List[str]
    used_chunks: int
    groups: dict
    query: str
    total_retrieved: int
    total_docs: int
    conversation_history: List[dict]


# ============================================================================
# 会话管理接口
# ============================================================================


@router.get("/sessions", response_model=List[SessionResponse])
def list_sessions(
    user_id: int = Query(..., description="用户ID"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    获取用户所有会话列表（按更新时间倒序）
    """
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user_id)
        .order_by(desc(ChatSession.updated_at))
        .limit(limit)
        .all()
    )
    return [SessionResponse(**s.to_dict()) for s in sessions]


@router.post("/sessions", response_model=SessionResponse, status_code=201)
def create_session(
    request: CreateSessionRequest,
    user_id: int = Query(..., description="用户ID"),
    db: Session = Depends(get_db),
):
    """
    创建新会话
    """
    session = ChatSession(user_id=user_id, title=request.title or "新对话")
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionResponse(**session.to_dict())


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session(
    session_id: str,
    user_id: int = Query(..., description="用户ID"),
    db: Session = Depends(get_db),
):
    """
    获取会话详情（含消息列表）
    """
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的会话ID格式")

    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == sid, ChatSession.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == sid)
        .order_by(ChatMessage.created_at)
        .all()
    )

    return SessionDetailResponse(
        session=SessionResponse(**session.to_dict()),
        messages=[MessageResponse(**m.to_dict()) for m in messages],
    )


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: str,
    user_id: int = Query(..., description="用户ID"),
    db: Session = Depends(get_db),
):
    """
    删除会话（级联删除所有消息）
    """
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的会话ID格式")

    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == sid, ChatSession.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    db.delete(session)
    db.commit()
    return {"success": True, "message": "会话已删除"}


# ============================================================================
# 多轮问答接口
# ============================================================================


@router.post("/qa", response_model=QAResponse)
def multi_turn_qa(
    request: QARequest,
    user_id: int = Query(..., description="用户ID"),
    db: Session = Depends(get_db),
):
    """
    多轮问答接口

    流程：
    1. 如果没有 session_id，创建新会话
    2. 加载对话历史
    3. 调用 RAG 工作流（带历史上下文）
    4. 保存问答记录到数据库
    5. 更新会话标题（如果是第一条消息）
    """
    # 1. 获取或创建会话
    if request.session_id:
        try:
            sid = uuid.UUID(request.session_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的会话ID格式")

        session = (
            db.query(ChatSession)
            .filter(ChatSession.id == sid, ChatSession.user_id == user_id)
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
    else:
        session = ChatSession(user_id=user_id, title="新对话")
        db.add(session)
        db.commit()
        db.refresh(session)

    # 2. 加载对话历史
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    conversation_history = [{"role": m.role, "content": m.content} for m in messages]

    # 3. 调用 RAG 工作流
    from services.document_service import qa_search_with_context

    rag_result = qa_search_with_context(
        query=request.query,
        conversation_history=conversation_history,
        top_k=request.top_k,
    )

    # 4. 保存用户消息
    user_msg = ChatMessage(session_id=session.id, role="user", content=request.query)
    db.add(user_msg)

    # 5. 保存助手回复
    assistant_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=rag_result["answer"],
        metadata={
            "sources": rag_result.get("sources", []),
            "used_chunks": rag_result.get("used_chunks", 0),
            "groups": rag_result.get("groups", {}),
            "total_retrieved": rag_result.get("total_retrieved", 0),
            "total_docs": rag_result.get("total_docs", 0),
        },
    )
    db.add(assistant_msg)
    db.commit()

    # 6. 更新会话标题（第一条消息时用问题前20字作为标题）
    if len(messages) == 0 and len(request.query) > 0:
        session.title = request.query[:20] + ("..." if len(request.query) > 20 else "")
        db.commit()

    # 7. 重新查询更新后的历史
    updated_messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    updated_history = [{"role": m.role, "content": m.content} for m in updated_messages]

    return QAResponse(
        session_id=str(session.id),
        message_id=str(assistant_msg.id),
        answer=rag_result["answer"],
        sources=rag_result.get("sources", []),
        used_chunks=rag_result.get("used_chunks", 0),
        groups=rag_result.get("groups", {}),
        query=request.query,
        total_retrieved=rag_result.get("total_retrieved", 0),
        total_docs=rag_result.get("total_docs", 0),
        conversation_history=updated_history,
    )


# ============================================================================
# 流式问答接口 (SSE)
# ============================================================================


def _sse_format(event: str, data: dict) -> str:
    """格式化为 SSE 事件字符串"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/qa/stream")
async def multi_turn_qa_stream(
    request: QARequest,
    user_id: int = Query(..., description="用户ID"),
    db: Session = Depends(get_db),
):
    """
    多轮问答（SSE 流式输出）

    事件流：
    - event: session  -> 包含 session_id
    - event: history  -> 包含对话历史
    - event: chunk    -> 包含 answer 的增量内容
    - event: sources  -> 包含 sources, groups 等元数据
    - event: done     -> 包含最终 message_id
    - event: error    -> 错误信息
    """
    print("调用流式问答接口")
    # 1. 获取或创建会话
    if request.session_id:
        try:
            sid = uuid.UUID(request.session_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的会话ID格式")

        session = (
            db.query(ChatSession)
            .filter(ChatSession.id == sid, ChatSession.user_id == user_id)
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
    else:
        session = ChatSession(user_id=user_id, title="新对话")
        db.add(session)
        db.commit()
        db.refresh(session)

    session_id_str = str(session.id)

    # 2. 加载对话历史
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    conversation_history = [{"role": m.role, "content": m.content} for m in messages]

    async def event_generator():
        # 发送 session 事件
        yield _sse_format(
            "session",
            {
                "session_id": session_id_str,
                "conversation_history": conversation_history,
            },
        )

        # 离线保存：用户消息
        try:
            user_msg = ChatMessage(
                session_id=session.id,
                role="user",
                content=request.query,
            )
            db.add(user_msg)
            db.commit()
            db.refresh(user_msg)
        except Exception as e:
            db.rollback()
            yield _sse_format("error", {"detail": f"保存用户消息失败: {str(e)}"})
            return

        # 调用流式 RAG
        from services.rag_nodes_chat import (
            conversation_context_node,
            conversation_save_node,
        )
        from services.rag_nodes import (
            query_rewriter_node,
            retriever_node,
            relevance_grader_node,
            should_retry,
        )
        from services.rag_nodes_stream import answer_generator_stream_node

        # 加载最新历史
        conversation_history_full = conversation_history + [
            {"role": "user", "content": request.query}
        ]

        state = {
            "query": request.query,
            "session_id": session_id_str,
            "user_id": user_id,
            "conversation_history": conversation_history_full,
            "retry_count": 0,
        }

        # 离线跑前面节点（rewrite -> retrieve -> grade）
        try:
            loop = asyncio.get_event_loop()
            state.update(await loop.run_in_executor(None, query_rewriter_node, state))
            state.update(await loop.run_in_executor(None, retriever_node, state))
            state.update(await loop.run_in_executor(None, relevance_grader_node, state))

            # 重试逻辑
            while should_retry(state) == "rewrite":
                state.update(
                    await loop.run_in_executor(None, query_rewriter_node, state)
                )
                state.update(await loop.run_in_executor(None, retriever_node, state))
                state.update(
                    await loop.run_in_executor(None, relevance_grader_node, state)
                )
        except Exception as e:
            yield _sse_format("error", {"detail": f"检索失败: {str(e)}"})
            return

        # 流式生成答案
        final_state = None
        try:
            for partial in answer_generator_stream_node(state):
                if partial.get("_stream") == "answer_start":
                    continue
                if partial.get("_stream") == "answer_chunk":
                    yield _sse_format(
                        "chunk",
                        {
                            "delta": partial["delta"],
                            "answer": partial["answer"],
                        },
                    )
                else:
                    final_state = partial
        except Exception as e:
            yield _sse_format("error", {"detail": f"生成回答失败: {str(e)}"})
            return

        if not final_state:
            yield _sse_format("error", {"detail": "未生成回答"})
            return

        # 保存 AI 回答
        try:
            assistant_msg = ChatMessage(
                session_id=session.id,
                role="assistant",
                content=final_state.get("answer", ""),
                metadata_={
                    "sources": final_state.get("sources", []),
                    "used_chunks": final_state.get("used_chunks", 0),
                    "groups": final_state.get("groups", {}),
                    "total_retrieved": final_state.get("total_retrieved", 0),
                    "total_docs": final_state.get("total_docs", 0),
                },
            )
            db.add(assistant_msg)
            db.commit()
            db.refresh(assistant_msg)
        except Exception as e:
            db.rollback()
            yield _sse_format("error", {"detail": f"保存 AI 回答失败: {str(e)}"})
            return

        # 发送 sources 事件
        yield _sse_format(
            "sources",
            {
                "sources": final_state.get("sources", []),
                "used_chunks": final_state.get("used_chunks", 0),
                "total_retrieved": final_state.get("total_retrieved", 0),
                "total_docs": final_state.get("total_docs", 0),
                "groups": final_state.get("groups", {}),
            },
        )

        # 自动生成标题（如果是新会话且只有 1 轮对话）
        new_title = None
        if session.title == "新对话":
            new_title = await _generate_title(
                request.query, final_state.get("answer", "")
            )
            if new_title:
                session.title = new_title
                try:
                    db.commit()
                except Exception:
                    db.rollback()

        # 发送 done 事件
        yield _sse_format(
            "done",
            {
                "message_id": str(assistant_msg.id),
                "session_id": session_id_str,
                "new_title": new_title,
            },
        )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _generate_title(query: str, answer: str) -> Optional[str]:
    """
    根据用户问题和 AI 回答，自动生成简短的会话标题。
    使用 LLM 总结，限制 6-15 个字。
    """
    if not query:
        return None
    try:
        from services.document_service import get_llm_client

        prompt = (
            "请根据用户的提问和AI的回答,生成一个不超过12个字的会话标题。"
            "直接输出标题,不要标点符号,不要引号。\n"
            f"用户问题: {query}\n"
            f"AI回答: {answer[:200] if answer else ''}\n"
            "标题:"
        )

        loop = asyncio.get_event_loop()
        llm = await loop.run_in_executor(None, get_llm_client)
        response = await loop.run_in_executor(None, lambda: llm.invoke(prompt).content)
        title = (response or "").strip().split("\n")[0].strip()

        # 清理
        for ch in ['"', "'", "「", "」", "《", "》", ":", "："]:
            title = title.replace(ch, "")

        if 2 <= len(title) <= 15:
            return title
        # 太长则截断，太短则回退
        if len(title) > 15:
            return title[:15]
        if len(title) >= 1:
            return title
    except Exception:
        pass

    # 兜底：直接用问题前几个字
    fallback = query.strip()[:12]
    return fallback if fallback else "新对话"


# ============================================================================
# 会话更新接口
# ============================================================================


class UpdateSessionRequest(BaseModel):
    """更新会话请求"""

    title: Optional[str] = None


@router.patch("/sessions/{session_id}", response_model=SessionResponse)
def update_session(
    session_id: str,
    request: UpdateSessionRequest,
    user_id: int = Query(..., description="用户ID"),
    db: Session = Depends(get_db),
):
    """更新会话（目前仅支持修改标题）"""
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的会话ID格式")

    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == sid, ChatSession.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    if request.title is not None:
        session.title = request.title.strip() or "新对话"

    session.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(session)
    return SessionResponse(**session.to_dict())

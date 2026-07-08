# -*- coding: utf-8 -*-
"""
=============================================================================
LangGraph RAG 工作流 - 会话管理节点
=============================================================================

包含 2 个会话管理节点：
- conversation_context_node: 从数据库加载对话历史，构建上下文
- conversation_save_node: 保存对话到数据库

这些节点使 RAG 工作流支持多轮对话。

使用方式：
    from services.rag_nodes_chat import conversation_context_node, conversation_save_node
"""

import uuid
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from db_models.chat import ChatSession, ChatMessage


# ============================================================================
# 会话上下文节点：加载历史对话
# ============================================================================


def conversation_context_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    从数据库加载对话历史，构建上下文。

    逻辑：
    1. 如果有 session_id，从数据库查询历史消息
    2. 限制上下文长度（最近 10 轮，避免 token 过多）
    3. 返回 conversation_history

    Args:
        state: RAGState，包含 session_id, user_id

    Returns:
        包含 conversation_history 的更新状态
    """
    from services.database import SessionLocal

    session_id = state.get("session_id")
    conversation_history: List[Dict[str, str]] = []

    if session_id:
        db: Session = SessionLocal()
        try:
            # 查询会话中的历史消息
            messages = (
                db.query(ChatMessage)
                .filter(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at.desc())
                .limit(20)  # 最近 20 条消息，约 10 轮对话
                .all()
            )

            # 按时间正序排列（最老的在前）
            messages = list(reversed(messages))

            for msg in messages:
                conversation_history.append({
                    "role": msg.role,
                    "content": msg.content,
                })
        finally:
            db.close()

    return {"conversation_history": conversation_history}


# ============================================================================
# 会话保存节点：保存对话到数据库
# ============================================================================


def conversation_save_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    保存对话到数据库（用户消息 + AI 回答）。

    逻辑：
    1. 如果有 session_id，直接保存消息
    2. 如果没有 session_id，创建新会话后再保存
    3. 返回新的 session_id（如果是新建的）

    Args:
        state: RAGState，包含 query, answer, sources, conversation_history 等

    Returns:
        包含 session_id, message_id 的更新状态
    """
    from services.database import SessionLocal

    session_id = state.get("session_id")
    user_id = state.get("user_id")
    query = state.get("query", "")
    answer = state.get("answer", "")
    sources = state.get("sources", [])
    groups = state.get("groups", {})

    db: Session = SessionLocal()
    try:
        # 如果没有会话，创建一个新会话
        if not session_id:
            chat_session = ChatSession(user_id=user_id or 1)
            db.add(chat_session)
            db.flush()  # 获取 id
            session_id = str(chat_session.id)
        else:
            chat_session = (
                db.query(ChatSession)
                .filter(ChatSession.id == session_id)
                .first()
            )
            if not chat_session:
                chat_session = ChatSession(user_id=user_id or 1)
                db.add(chat_session)
                db.flush()
                session_id = str(chat_session.id)

        # 保存用户消息
        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=query,
            metadata={"sources": sources},
        )
        db.add(user_msg)
        db.flush()
        user_msg_id = str(user_msg.id)

        # 保存 AI 回答
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=answer,
            metadata={
                "sources": sources,
                "groups": groups,
                "used_chunks": state.get("used_chunks", 0),
                "total_retrieved": state.get("total_retrieved", 0),
                "total_docs": state.get("total_docs", 0),
            },
        )
        db.add(assistant_msg)
        db.flush()
        assistant_msg_id = str(assistant_msg.id)

        # 更新会话的 updated_at 时间
        chat_session.updated_at = chat_session.updated_at

        # 如果会话标题是默认的，尝试生成简短标题
        if chat_session.title == "新对话" and query:
            chat_session.title = query[:50] + ("..." if len(query) > 50 else "")

        db.commit()

        return {
            "session_id": session_id,
            "message_id": assistant_msg_id,
        }

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


# ============================================================================
# 辅助函数
# ============================================================================


def build_conversation_prompt(
    conversation_history: List[Dict[str, str]],
    current_query: str,
    system_prompt: str = None,
) -> str:
    """
    构建包含对话历史的完整 prompt。

    Args:
        conversation_history: 对话历史列表
        current_query: 当前问题
        system_prompt: 系统提示词（可选）

    Returns:
        完整的 prompt 字符串
    """
    from services.rag_nodes import _ANSWER_PROMPT_TEMPLATE

    if not conversation_history:
        return _ANSWER_PROMPT_TEMPLATE.format(
            context="{context}",
            query=current_query,
        )

    # 构建历史对话字符串
    history_text = "\n\n".join(
        f"【{msg['role'].upper()}】: {msg['content']}"
        for msg in conversation_history
    )

    # 在 system prompt 中加入历史上下文
    enhanced_prompt = f"""你是一个专业的技术文档问答助手。你需要根据提供的文档片段和对话历史来回答用户的问题。

## 对话历史：
{history_text}

## 当前问题：
{current_query}

## 回答要求：
1. 参考对话历史中的上下文信息
2. 只基于提供的文档内容回答，不要编造信息
3. 如果涉及多文档对比，给出清晰的对比分析
4. 如果没有相关信息，明确告知用户
"""

    return enhanced_prompt

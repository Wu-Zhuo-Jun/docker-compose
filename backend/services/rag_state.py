# -*- coding: utf-8 -*-
"""
=============================================================================
LangGraph RAG 工作流 - 状态定义
=============================================================================

定义 RAGState TypedDict，作为整个工作流的共享内存。

字段说明：
- query:              用户原始问题（输入）
- session_id:         会话 ID（用于加载/保存对话历史）
- user_id:            用户 ID
- conversation_history: 对话历史 [{"role": "user/assistant", "content": "..."}]

检索阶段：
- rewritten_query:    改写后的检索 query（节点1产出）
- retrieved_chunks:   当前轮次检索到的 chunks（节点2产出）

评估阶段：
- relevant_chunks:    通过相关性过滤的 chunks（节点3产出）
- is_relevant:        是否有至少一个相关 chunk（节点3产出）
- retry_count:        已重试次数（节点2每执行一次 +1）

以下字段为最终输出，与现有 QASearchResponse 保持兼容：
- answer / sources / used_chunks / groups / total_retrieved / total_docs

=============================================================================
"""

from typing import TypedDict, List, Dict, Any


class RAGState(TypedDict, total=False):
    # 输入
    query: str
    session_id: str
    user_id: int

    # 对话上下文
    conversation_history: List[Dict[str, str]]  # [{"role": "user/assistant", "content": "..."}]

    # 检索阶段
    rewritten_query: str
    retrieved_chunks: List[Dict[str, Any]]

    # 评估阶段
    relevant_chunks: List[Dict[str, Any]]
    is_relevant: bool

    # 控制
    retry_count: int

    # 输出（与 QASearchResponse 兼容）
    answer: str
    sources: List[str]
    used_chunks: int
    groups: Dict[str, List[Dict[str, Any]]]
    total_retrieved: int
    total_docs: int

    # 消息元数据（保存时使用）
    message_id: str
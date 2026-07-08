# -*- coding: utf-8 -*-
"""
=============================================================================
LangGraph RAG 工作流 - 图构建
=============================================================================

构建 StateGraph 并编译为可执行对象 rag_graph。

工作流（带多轮对话支持）：
    load_history -> rewrite -> retrieve -> grade ->[should_retry]-> rewrite / generate
    -> save_history -> END

设计决策：
- 不引入 Checkpointer（数据库存储对话历史，无需 LangGraph 内置）
- 不引入 MemorySaver（数据库已经持久化对话）
- 编译在模块加载时执行一次，rag_graph 是单例

=============================================================================
"""

from langgraph.graph import StateGraph, END

from services.rag_state import RAGState
from services.rag_nodes import (
    query_rewriter_node,
    retriever_node,
    relevance_grader_node,
    answer_generator_node,
    should_retry,
)
from services.rag_nodes_chat import (
    conversation_context_node,
    conversation_save_node,
)


def build_rag_graph():
    """构建并编译 RAG 工作流图"""
    workflow = StateGraph[RAGState, None, RAGState, RAGState](RAGState)

    # 原有节点
    workflow.add_node("rewrite", query_rewriter_node)
    workflow.add_node("retrieve", retriever_node)
    workflow.add_node("grade", relevance_grader_node)
    workflow.add_node("generate", answer_generator_node)

    # 新增会话节点
    workflow.add_node("load_history", conversation_context_node)
    workflow.add_node("save_history", conversation_save_node)

    # 新流程: load_history -> rewrite -> retrieve -> grade -> generate -> save_history -> END
    workflow.set_entry_point("load_history")
    workflow.add_edge("load_history", "rewrite")
    workflow.add_edge("rewrite", "retrieve")
    workflow.add_edge("retrieve", "grade")
    workflow.add_conditional_edges(
        "grade",
        should_retry,
        {
            "rewrite": "rewrite",
            "generate": "generate",
        },
    )
    workflow.add_edge("generate", "save_history")
    workflow.add_edge("save_history", END)

    return workflow.compile()


# 模块级单例，导入时构建一次
rag_graph = build_rag_graph()
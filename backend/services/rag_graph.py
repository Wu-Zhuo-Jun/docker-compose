# -*- coding: utf-8 -*-
"""
=============================================================================
LangGraph RAG 工作流 - 图构建
=============================================================================

构建 StateGraph 并编译为可执行对象 rag_graph。

工作流：
    rewrite -> retrieve -> grade ->[should_retry]-> rewrite / generate -> END

设计决策：
- 不引入 Checkpointer（MVP 阶段无状态）
- 不引入 MemorySaver（无需会话记忆）
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


def build_rag_graph():
    """构建并编译 RAG 工作流图"""
    workflow = StateGraph(RAGState)

    workflow.add_node("rewrite", query_rewriter_node)
    workflow.add_node("retrieve", retriever_node)
    workflow.add_node("grade", relevance_grader_node)
    workflow.add_node("generate", answer_generator_node)

    workflow.set_entry_point("rewrite")
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
    workflow.add_edge("generate", END)

    return workflow.compile()


# 模块级单例，导入时构建一次
rag_graph = build_rag_graph()

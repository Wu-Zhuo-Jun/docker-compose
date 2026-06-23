# -*- coding: utf-8 -*-
"""
=============================================================================
FastAPI 主应用入口
=============================================================================

包含:
- 文档上传与语义分块接口
- ChromaDB 向量检索

=============================================================================
"""

from fastapi import FastAPI
from routers import document
from services.document_service import get_chroma_client
import config  # noqa: F401 - 加载配置（设置环境变量等）
import uvicorn

app = FastAPI(title="Document RAG API", version="1.0.0")


@app.get("/")
async def root():
    return {"message": "Document RAG API with Semantic Chunking"}


@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        get_chroma_client().heartbeat()
        return {"status": "healthy", "chromadb": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.get("/vector-db-info")
async def get_vector_db_info():
    """向量数据库信息"""
    return {
        "current_db": "ChromaDB",
        "features": ["semantic_chunking", "document_upload", "vector_search"],
    }


# 注册路由
app.include_router(document.router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

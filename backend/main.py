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
from routers import document, auth
from services.document_service import get_chroma_client
from services.database import engine
from sqlalchemy import text
import config  # noqa: F401 - 加载配置（设置环境变量等）
import uvicorn
import logging

logger = logging.getLogger("startup")

app = FastAPI(title="Document RAG API", version="1.0.0")


@app.on_event("startup")
def verify_dependencies():
    """启动时确认 Postgres / Chroma 可达,失败直接挂,避免请求阶段才报错。"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("[startup] postgres OK")
    except Exception as e:
        logger.error("[startup] postgres UNREACHABLE: %s", e)
        raise

    try:
        # Chroma 包装类没 heartbeat,直接用底层 PersistentClient
        chroma = get_chroma_client()
        underlying = getattr(chroma, "_client", None) or getattr(chroma, "client", None)
        if underlying is None:
            raise RuntimeError("无法拿到 chromadb 底层 client")
        underlying.heartbeat()
        logger.info("[startup] chromadb OK")
    except Exception as e:
        logger.error("[startup] chromadb UNREACHABLE: %s", e)
        raise


@app.get("/")
async def root():
    return {"message": "Document RAG API with Semantic Chunking"}


@app.get("/health")
async def health_check():
    """健康检查"""
    status = {"status": "healthy", "chromadb": "unknown", "postgres": "unknown"}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        status["postgres"] = "connected"
    except Exception as e:
        status["postgres"] = f"error: {e}"
        status["status"] = "unhealthy"
    try:
        chroma = get_chroma_client()
        underlying = getattr(chroma, "_client", None) or getattr(chroma, "client", None)
        if underlying is None:
            raise RuntimeError("no underlying client")
        underlying.heartbeat()
        status["chromadb"] = "connected"
    except Exception as e:
        status["chromadb"] = f"error: {e}"
        status["status"] = "unhealthy"
    return status


@app.get("/vector-db-info")
async def get_vector_db_info():
    """向量数据库信息"""
    return {
        "current_db": "ChromaDB",
        "features": ["semantic_chunking", "document_upload", "vector_search"],
    }


# 注册路由
app.include_router(document.router)
app.include_router(auth.router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

from fastapi import FastAPI
import chromadb
import os
from functools import lru_cache

app = FastAPI()

_chroma_client = None


def get_chroma_client():
    """懒加载 ChromaDB 客户端"""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.HttpClient(
            host=os.getenv("VECTOR_DB_HOST", "chromadb"),
            port=os.getenv("VECTOR_DB_PORT", "8001"),
        )
    return _chroma_client


@app.get("/")
async def root():
    return {"message": "FastAPI Backend with ChromaDB"}


@app.get("/health")
async def health_check():
    try:
        # 检查 ChromaDB 连接
        get_chroma_client().heartbeat()
        return {"status": "healthy", "chromadb": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


# Day 6 预留的 Qdrant 接口
@app.get("/vector-db-info")
async def get_vector_db_info():
    return {
        "current_db": "ChromaDB",
        "next_db": "Qdrant (Day 6)",
        "migration_plan": "Ready",
    }

# -*- coding: utf-8 -*-
"""
=============================================================================
配置模块
=============================================================================

包含:
- DeepSeek 模型配置
- ChromaDB 配置
- LLM 检索配置
- 其他全局配置

=============================================================================
"""

import os

# DeepSeek API Key
os.environ["OPENAI_API_KEY"] = "sk-e6d2f16fbdd5462ea26a0d8202e843fc"

# ChromaDB 配置
CHROMA_HOST = os.getenv("VECTOR_DB_HOST", "chromadb")
CHROMA_PORT = os.getenv("VECTOR_DB_PORT", "8000")

# LLM 配置
LLM_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-e6d2f16fbdd5462ea26a0d8202e843fc")
LLM_API_BASE = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")
LLM_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

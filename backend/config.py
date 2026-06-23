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
from pathlib import Path

# 加载 .env 文件（项目根目录）
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())

# DeepSeek API Key - 必须通过环境变量设置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise ValueError("请设置 DEEPSEEK_API_KEY 环境变量")

os.environ["OPENAI_API_KEY"] = DEEPSEEK_API_KEY

# ChromaDB 配置
CHROMA_HOST = os.getenv("VECTOR_DB_HOST", "chromadb")
CHROMA_PORT = os.getenv("VECTOR_DB_PORT", "8000")

# LLM 配置
LLM_API_KEY = DEEPSEEK_API_KEY
LLM_API_BASE = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")
LLM_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

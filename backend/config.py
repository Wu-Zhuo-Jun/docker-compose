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

# PostgreSQL 配置
# 本地 .env 有 DB_HOST=host.docker.internal / DB_PORT=5433 / DB_NAME=MyAgentApp（走宿主机）
# Zeabur 上由 DATABASE_URL 环境变量整体覆盖，host/port/name 均以 DATABASE_URL 为准
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "compose_yml")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# 数据库连接 URL（Zeabur 会用 DATABASE_URL 环境变量覆盖此值）
DATABASE_URL = os.getenv("DATABASE_URL") or (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ChromaDB 配置
CHROMA_HOST = os.getenv("VECTOR_DB_HOST", "chromadb")
CHROMA_PORT = os.getenv("VECTOR_DB_PORT", "8000")

# LLM 配置
LLM_API_KEY = DEEPSEEK_API_KEY
LLM_API_BASE = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")
LLM_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


# PASSWORD=dwbzL98K3Z65GRjf7Q2EVYyc41H0nCSB
# PGDATA=/var/lib/postgresql/18/docker/pgdata
# POSTGRES_CONNECTION_STRING=postgresql://${POSTGRES_USERNAME}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DATABASE}
# POSTGRES_DATABASE=${POSTGRES_DB}
# POSTGRES_DB=zeabur
# POSTGRES_HOST=${CONTAINER_HOSTNAME}
# POSTGRES_PASSWORD=${PASSWORD}
# POSTGRES_PORT=${DATABASE_PORT}
# POSTGRES_URI=${POSTGRES_CONNECTION_STRING}
# POSTGRES_USER=root
# POSTGRES_USERNAME=${POSTGRES_USER}

# DB_HOST=postgresql.zeabur.internal
# DB_NAME=zeabur
# DB_PASSWORD=dwbzL98K3Z65GRjf7Q2EVYyc41H0nCSB
# DB_PORT=5432
# DB_USER=root
# DEEPSEEK_API_KEY=sk-65a35f195fac4c208bb55e6753dfef22
# PASSWORD=3prufIzG94PXjgNa5V2786ZcQUdFy1i0
# PORT=${WEB_PORT}

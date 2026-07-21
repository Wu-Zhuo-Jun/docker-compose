# syntax=docker/dockerfile:1.7
# Zeabur 专用后端 Dockerfile
# Build context 必须是项目根目录（与 zeabur.json 同级）
# 在 backend/ 目录下执行: zeabur.yml deploy --project-dir ..
FROM python:3.10-slim AS builder
WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir uv

RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 \
    uv pip install --system -r requirements.txt

FROM python:3.10-slim

RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

RUN --mount=type=cache,target=/root/.cache,sharing=locked \
    mkdir -p /app/models && \
    python -c "from langchain_huggingface import HuggingFaceEmbeddings; HuggingFaceEmbeddings(model_name='BAAI/bge-small-zh-v1.5', cache_folder='/app/models', model_kwargs={'device':'cpu'}, encode_kwargs={'normalize_embeddings': True})"

# 从项目根目录构建时，只复制 backend/ 下的源码
COPY . /app/

# 调试：列出 /app 内容，确认文件结构
RUN ls -la /app/ && echo "=== /app/routers exists? ===" && ls /app/routers/ 2>&1 || echo "routers NOT FOUND"

RUN mkdir -p /app/chroma_data && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

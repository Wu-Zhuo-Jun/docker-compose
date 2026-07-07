# syntax=docker/dockerfile:1.7
FROM python:3.10-slim AS builder
WORKDIR /app

# 先复制依赖文件（利用 Docker 缓存）
COPY requirements.txt .

# 安装 uv（官方推荐方式：装到隔离目录，复用 pip 缓存）
# BuildKit cache mount: keep pip wheels across builds, no extra image layers.
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    pip install --no-cache-dir uv

# 用 uv 装项目依赖（比 pip 快数倍，且 uv 的全局缓存跨构建复用）
# BuildKit cache mount: keep uv's global content-addressed cache across builds.
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 \
    uv pip install --system -r requirements.txt

FROM python:3.10-slim
WORKDIR /app

# 只复制运行时必需的内容：依赖 + 可执行入口 + 模型 + 业务代码
# 注意：uvicorn 等包会把入口脚本装到 /usr/local/bin，必须一并复制，
# 否则多阶段构建的运行时镜像里 $PATH 找不到 uvicorn。
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 模型在最终阶段下载 预先下载 embedding 模型到 /app/models，与运行时 HF_HOME / EMBEDDING_CACHE_DIR 保持一致
# BuildKit cache mount: reuse HuggingFace hub cache across builds.
RUN --mount=type=cache,target=/root/.cache/huggingface,sharing=locked \
    mkdir -p /app/models && \
    python -c "from langchain_huggingface import HuggingFaceEmbeddings; HuggingFaceEmbeddings(model_name='BAAI/bge-small-zh-v1.5', cache_folder='/app/models', model_kwargs={'device':'cpu'}, encode_kwargs={'normalize_embeddings': True})"

COPY main.py .

# 暴露端口
EXPOSE 8000
# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

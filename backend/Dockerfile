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

# 创建模型目录（模型在容器启动时通过 entrypoint 脚本从镜像下载）
RUN mkdir -p /app/models

# 如果有本地模型缓存卷，可以在启动时直接挂载
# 模型会在运行时下载到 /app/models

COPY main.py .

# 创建启动脚本（模型只在不存在时下载一次）
RUN printf '#!/bin/bash\n\
echo "[entrypoint] 检查 embedding 模型..."\n\
export HF_ENDPOINT="https://hf-mirror.com"\n\
export HF_HUB_OFFLINE=0\n\
MODEL_PATH="/app/models/models--BAAI--bge-small-zh-v1.5"\n\
if [ -d "$MODEL_PATH" ] && [ -n "$(ls -A $MODEL_PATH 2>/dev/null)" ]; then\n\
    echo "[entrypoint] 模型已存在，跳过下载"\nelse\n\
    echo "[entrypoint] 正在下载 embedding 模型..."\n\
    python -c "from huggingface_hub import snapshot_download; snapshot_download('\''BAAI/bge-small-zh-v1.5'\'', cache_dir='\''/app/models'\'')"\n\
    if [ $? -ne 0 ]; then\n\
        echo "[entrypoint] 模型下载失败，尝试备用源..."\n\
        python -c "from huggingface_hub import snapshot_download; snapshot_download('\''BAAI/bge-small-zh-v1.5'\'', cache_dir='\''/app/models'\'', endpoint='\''https://huggingface.co'\'')" || true\n\
    fi\n\
fi\necho "[entrypoint] 启动 FastAPI 服务..."\n\
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload\n' > /entrypoint.sh && chmod +x /entrypoint.sh

# 暴露端口
EXPOSE 8000
# 使用启动脚本（自动下载模型）
CMD ["/entrypoint.sh"]

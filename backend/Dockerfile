FROM python:3.10-slim AS builder
WORKDIR /app

# 先复制依赖文件（利用 Docker 缓存）
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 预先下载 embedding 模型到 /app/models，与运行时 HF_HOME / EMBEDDING_CACHE_DIR 保持一致
RUN mkdir -p /app/models && \
    python -c "from langchain_huggingface import HuggingFaceEmbeddings; HuggingFaceEmbeddings(model_name='BAAI/bge-small-zh-v1.5', cache_folder='/app/models', model_kwargs={'device':'cpu'}, encode_kwargs={'normalize_embeddings': True})"

FROM python:3.10-slim
WORKDIR /app

# 只复制运行时必需的内容：依赖 + 模型 + 业务代码
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /app/models /app/models

COPY main.py .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

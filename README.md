# Compose-YML Project

基于 Docker Compose 的 FastAPI + ChromaDB 项目。

## 项目结构

```
compose-yml/
├── docker-compose.yml      # Docker Compose 配置文件
├── backend/
│   ├── Dockerfile           # 后端镜像构建文件
│   ├── main.py              # FastAPI 主应用
│   ├── requirements.txt     # Python 依赖
│   └── fastapi_project/     # FastAPI 完整项目（备用）
└── README.md
```

## 快速开始

### 1. 启动所有服务

```bash
docker-compose up -d
```

### 2. 查看服务状态

```bash
docker-compose ps
```

### 3. 查看日志

```bash
# 查看所有服务日志
docker-compose logs

# 实时查看后端日志
docker-compose logs -f backend

# 查看 ChromaDB 日志
docker-compose logs -f chromadb

# 查看最近 50 行日志
docker-compose logs --tail=50 backend
```

### 4. 停止服务

```bash
docker-compose down
```

### 5. 重启服务

```bash
docker-compose restart
```

### 6. 重新构建并启动

```bash
docker-compose down && docker-compose up -d --build
```

---

## Docker 常用命令

### 容器管理

```bash
# 进入容器内部
docker exec -it fastapi_backend /bin/sh

# 进入 ChromaDB 容器
docker exec -it chromadb_service /bin/sh

# 停止容器
docker stop fastapi_backend

# 启动容器
docker start fastapi_backend

# 查看运行中的容器
docker ps

# 查看所有容器（包括已停止）
docker ps -a
```

### 镜像管理

```bash
# 查看所有镜像
docker images

# 删除镜像
docker rmi compose-yml-backend

# 强制删除镜像
docker rmi -f compose-yml-backend

# 重新构建镜像（不缓存）
docker-compose build --no-cache
```

### 数据卷管理

```bash
# 查看所有数据卷
docker volume ls

# 查看 ChromaDB 数据卷信息
docker volume inspect compose-yml_chroma_data

# 查看数据卷在主机上的实际路径
docker volume inspect compose-yml_chroma_data --format '{{ .Mountpoint }}'

# 删除未使用的数据卷
docker volume prune
```

### 网络管理

```bash
# 查看网络
docker network ls

# 查看项目网络详情
docker network inspect compose-yml_app_network
```

### 清理

```bash
# 停止并删除所有容器、网络（保留镜像和数据卷）
docker-compose down

# 停止并删除所有资源（包括数据卷！）
docker-compose down -v

# 删除已停止的容器、无用的镜像、悬挂的构建缓存
docker system prune -a
```

---

## 服务访问地址

| 服务 | 容器内地址 | 主机访问地址 |
|------|-----------|-------------|
| FastAPI | http://backend:8000 | http://localhost:8000 |
| FastAPI 文档 | - | http://localhost:8000/docs |
| ChromaDB | http://chromadb:8000 | http://localhost:8001 |
| 健康检查 | - | http://localhost:8000/health |

---

## API 接口

### 健康检查

```bash
curl http://localhost:8000/health
```

### ChromaDB 信息

```bash
curl http://localhost:8000/vector-db-info
```

---

## 问题排查

### 1. 容器启动失败

```bash
# 查看详细日志
docker-compose logs backend
docker-compose logs chromadb
```

### 2. 端口冲突

如果提示端口被占用：

```bash
# Windows 查看端口占用
netstat -ano | findstr :8000

# 杀死占用进程（PID 替换为实际值）
taskkill /PID <PID> /F
```

### 3. 容器无法连接 ChromaDB

确保 `docker-compose.yml` 中环境变量配置正确：

```yaml
environment:
  - VECTOR_DB_HOST=chromadb      # 使用 Docker 网络中的服务名
  - VECTOR_DB_PORT=8000         # 使用容器内部端口
```

**注意**：容器之间通信使用**容器内部端口**，主机访问使用**映射端口**。

### 4. 健康检查失败

如果 ChromaDB 健康检查一直失败（`health: unhealthy`），但服务实际正常运行，可以修改 `depends_on` 条件：

```yaml
depends_on:
  chromadb:
    condition: service_started   # 而非 service_healthy
```

### 5. 数据持久化问题

ChromaDB 数据已配置持久化到 Docker 数据卷 `chroma_data`。

```bash
# 确认数据卷存在
docker volume ls | grep chroma_data

# 查看数据内容
docker exec -it chromadb_service ls /chroma/chroma
```

---

## 环境变量说明

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `VECTOR_DB_HOST` | `chromadb` | ChromaDB 服务名（Docker 网络内） |
| `VECTOR_DB_PORT` | `8000` | ChromaDB 容器内端口 |
| `IS_PERSISTENT` | `TRUE` | 启用数据持久化 |

---

## 技术栈

- **后端框架**: FastAPI
- **向量数据库**: ChromaDB
- **容器化**: Docker + Docker Compose
- **运行环境**: Python 3.10

---

## 常见问题总结

### Q1: 为什么容器间要用服务名连接？

在 Docker 网络中，容器通过服务名（如 `chromadb`）进行通信，而不是 `localhost` 或 IP 地址。

### Q2: 为什么 `localhost:8001` 访问不到 ChromaDB？

确保使用正确的端口映射：
- 容器内部：ChromaDB 监听 `8000`
- 主机映射：`8001:8000`
- 主机访问：`http://localhost:8001`

### Q3: 如何备份 ChromaDB 数据？

```bash
# 复制数据卷到主机
docker cp chromadb_service:/chroma/chroma ./backup_chroma
```

### Q4: 修改代码后需要重启吗？

由于配置了 volume 挂载（`./backend:/app`），修改代码后会自动重载。但如需完全重置：

```bash
docker-compose down && docker-compose up -d --build
```

Embedding模型需要从hugFace拉去某些镜像，比较久，可以自己从国内镜像源拉取
docker exec fastapi_backend python -c "from huggingface_hub import snapshot_download; snapshot_download('BAAI/bge-small-zh-v1.5', cache_dir='/app/models', endpoint='https://hf-mirror.com')"

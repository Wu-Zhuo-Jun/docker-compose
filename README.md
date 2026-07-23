# Compose-YML Project

基于 Docker Compose 的 FastAPI + ChromaDB 项目。

## 项目结构

```
compose-yml/
├── zeabur.json            # Zeabur 部署配置（前后端独立 service）
├── local/
│   └── compose.yml # 本地开发用 Docker Compose 配置
├── backend/
│   ├── Dockerfile         # 后端镜像构建文件（Zeabur 部署）
│   ├── zeabur.Dockerfile  # Zeabur 专用 Dockerfile
│   ├── main.py            # FastAPI 主应用
│   └── requirements.txt   # Python 依赖
└── frontend/              # React + Vite 前端
```

## Zeabur 部署

### ⚠️ 重要说明

本项目配置为 Zeabur 多 service 部署（backend、frontend、postgres 三个独立 service）。

**部署方式**：在 Zeabur Dashboard 手动创建三个服务：
1. **backend**：Root Directory 设为 `backend`，Dockerfile 选 `Dockerfile`
2. **frontend**：Root Directory 设为 `frontend`，Dockerfile 选 `Dockerfile`
3. **postgres**：选 PostgreSQL preset

### 部署后配置

1. 在 backend 服务中添加环境变量 `DEEPSEEK_API_KEY`
2. 配置域名：
   - backend：`/api` 路径
   - frontend：`/` 路径
3. 给 backend 服务挂载持久卷（用于 ChromaDB 数据）

### 本地开发

### 前后端分离模式（推荐）

**后端**：
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**前端**：
```bash
cd frontend
npm install
npm run dev
```

前端访问 http://localhost:5173，API 请求自动代理到 http://localhost:8000

### Docker Compose 模式（本地完整环境）

> 注意：`local/compose.yml` 不在 Git 追踪范围内。如需使用，请手动创建或从项目历史中恢复。

```bash
docker-compose -f local/compose.yml up -d
```

---

## Docker Compose 常用命令（本地完整环境）

> 注意：使用 `docker-compose -f local/compose.yml` 指定配置文件

### 容器管理

```bash
# 进入容器内部
docker exec -it compose-yml_backend_1 /bin/sh

# 停止容器
docker stop compose-yml_backend_1

# 启动容器
docker start compose-yml_backend_1

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
docker-compose -f local/compose.yml build --no-cache
```

### 数据卷管理

```bash
# 查看所有数据卷
docker volume ls

# 删除未使用的数据卷
docker volume prune
```

### 清理

```bash
# 停止并删除所有容器、网络（保留镜像和数据卷）
docker-compose -f local/compose.yml down

# 停止并删除所有资源（包括数据卷！）
docker-compose -f local/compose.yml down -v

# 删除已停止的容器、无用的镜像、悬挂的构建缓存
docker system prune -a
```

---


### cache清理
```bash
# 检查docker的磁盘使用情况
docker system df 
docker systen df  -v

# 查看构建缓存（Docker 18.09+）
docker builder df
docker builder dx 

# 安全清理cache（保留你能用的 cache）
docker buildx prune
docker buildx prune -a -f

#清除dangling镜像
docker image prune

#删除未使用资源（比较危险）
docker system prune
docker system prune -a -f  

# 检查
```




## 服务访问地址

| 服务         | 容器内地址           | 主机访问地址                 |
| ------------ | -------------------- | ---------------------------- |
| FastAPI      | http://backend:8000  | http://localhost:8000        |
| FastAPI 文档 | -                    | http://localhost:8000/docs   |
| ChromaDB     | http://chromadb:8000 | http://localhost:8001        |
| 健康检查     | -                    | http://localhost:8000/health |

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
docker-compose -f local/compose.yml logs backend
docker-compose -f local/compose.yml logs chromadb
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
  - VECTOR_DB_HOST=chromadb # 使用 Docker 网络中的服务名
  - VECTOR_DB_PORT=8000 # 使用容器内部端口
```

**注意**：容器之间通信使用**容器内部端口**，主机访问使用**映射端口**。

### 4. 健康检查失败

如果 ChromaDB 健康检查一直失败（`health: unhealthy`），但服务实际正常运行，可以修改 `depends_on` 条件：

```yaml
depends_on:
  chromadb:
    condition: service_started # 而非 service_healthy
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

| 变量名           | 默认值     | 说明                             |
| ---------------- | ---------- | -------------------------------- |
| `VECTOR_DB_HOST` | `chromadb` | ChromaDB 服务名（Docker 网络内） |
| `VECTOR_DB_PORT` | `8000`     | ChromaDB 容器内端口              |
| `IS_PERSISTENT`  | `TRUE`     | 启用数据持久化                   |

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


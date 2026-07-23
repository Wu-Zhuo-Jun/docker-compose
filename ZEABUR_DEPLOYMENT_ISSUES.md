# Zeabur 部署问题汇总与解决方案

> 本文档汇总了 `compose-yml` 项目在 Zeabur 部署过程中遇到的所有问题、原因分析以及解决方案。

---

## 目录

1. [Docker-compose 模式误触发](#1-docker-compose-模式误触发)
2. [前端 502 错误](#2-前端-502-错误)
3. [后端 API 404 错误](#3-后端-api-404-错误)
4. [前端静态资源无法访问](#4-前端静态资源无法访问)
5. [ConfigProvider 未定义错误](#5-configprovider-未定义错误)
6. [HOSTNAME_NOT_FOUND 错误](#6-hostname_not_found-错误)
7. [服务被 OOM 驱逐（内存不足）](#7-服务被-oom-驱逐内存不足)
8. [前端打包体积优化](#8-前端打包体积优化)
9. [ChromaDB preset 缺失](#9-chromadb-preset-缺失)
10. [中国大陆网络限制](#10-中国大陆网络限制)
11. [购买服务器后的调整](#11-购买服务器后的调整)
12. [代码中的信息泄露](#12-代码中的信息泄露)

---

## 1. Docker-compose 模式误触发

### 问题描述

项目上传 Zeabur 后触发了 docker-compose 模式，即使 `zeabur.json` 中已经明确配置了 backend 和 frontend 为独立服务。

### 原因分析

**Zeabur 的 compose 检测极其激进**，不只是检测根目录的 `docker-compose.yml`，而是：

1. 检测任何 `docker-compose*.yml` 文件（放在子目录也会被检测到）
2. 检测 `compose*.yml` 文件（如 `local/compose.yml`）
3. **检测 Git 历史中曾经的 compose 文件**
4. **缓存项目级别的检测结果**，即使文件删除了，旧的 compose 镜像仍然被使用

> ⚠️ **实测发现**：即使把 `docker-compose.yml` 改名为 `local/compose.yml`，Zeabur 仍会检测到并进入 compose 模式。即使删除服务重建、GitHub 仓库已干净，Zeabur 仍会使用缓存的 compose 镜像。

### 解决方案

| 尝试方法 | 结果 |
|---------|------|
| 改名 `docker-compose.yml` → `docker-compose.local.yml` | ❌ 无效 |
| 移到子目录 `local/` | ❌ 无效（Zeabur 扫描整个树） |
| 加入 `.gitignore` + 从 Git 删除 | ⚠️ Git 干净了，但 Zeabur 缓存仍存在 |
| 删除服务重建 | ❌ 仍用缓存的 compose 镜像 |
| 改名 `local/compose.yml` | ❌ 无效（Zeabur 检测 `compose*.yml` 模式） |

**根因**：Zeabur registry 缓存了 `docker-compose` 模式的镜像（镜像 tag 以 `d-` 开头），新部署会继续使用旧镜像而不是重新构建。

**方案 A（推荐）：删除整个 Zeabur 项目重建**
1. 删除整个 Zeabur 项目
2. 创建新项目
3. 让 Zeabur 从 GitHub 重新检测

**方案 B：拆分仓库**
- `compose-yml`：backend + frontend（无 compose 文件）
- 本地私有仓库：保留完整的 compose 配置

**方案 C：触发强制重建**
```bash
git commit --allow-empty -m "force rebuild" && git push
```
然后在 Zeabur 控制台触发 Redeploy。

**方案 D：联系 Zeabur 支持**
请求清除 registry 缓存，这是平台层面的问题。

---

## 2. 前端 502 错误

### 问题描述

访问前端域名（如 `https://henghuaragfrontend.zeabur.app/`）返回 502 错误。

### 原因分析

502 是 Zeabur 网关层返回的，说明：
- **frontend 容器没有正常响应**
- 或者 Zeabur 健康检查探测了错误的端口

常见原因：
1. Docker 构建在 Zeabur 端失败
2. 健康检查配置端口错误（如 Zeabur 探测 8080，但 nginx 监听 80）
3. 容器启动后崩溃

### 解决方案

**方案 A：重新部署**

在 Zeabur Dashboard → frontend 服务 → 点击 **Redeploy**。

**方案 B：检查健康检查配置**

确保 Zeabur 控制台中 frontend 服务的：
- 端口设置为 **80**
- 健康检查路径设置为 `/` 或 `/health`

**方案 C：禁用健康检查临时测试**

在服务设置中临时禁用健康检查，看服务是否能正常访问。

---

## 3. 后端 API 404 / routers 模块找不到

### 问题描述

后端启动时报错：
```
ModuleNotFoundError: No module named 'routers'
    from routers import document, auth, chat
  File "/app/main.py", line 15, in <module>
```

### 原因分析

当 Zeabur 在 docker-compose 模式下运行时：
- Zeabur 把整个项目目录当作 working directory（`/app`）
- `main.py` 实际在 `/app/backend/main.py`
- 但代码中 `from routers import ...` 期望 routers 在 `/app/` 目录下
- 路径不匹配导致模块找不到

### 解决方案

1. **首先解决 docker-compose 模式问题**（参见第 1 节）
2. 确保 Zeabur 使用 Dockerfile 模式部署后端
3. Dockerfile 的 `WORKDIR /app` + `COPY . .` 会正确复制 backend 目录内容

### 后端启动失败的直接原因

```
Started container docker-compose  ← Zeabur 在跑 compose 模式
```

日志中出现 `Started container docker-compose` 而不是 `Started container backend` 就说明用的是 compose 模式。

---

## 4. 前端静态资源无法访问

### 问题描述

即使前端服务显示正常，访问前端域名也无法加载页面。

### 原因分析

1. **域名配置错误**：访问了错误的域名
2. **端口不匹配**：nginx 监听端口与 Zeabur 探测端口不一致
3. **健康检查失败**：容器被标记为不健康

### 解决方案

**确认正确的访问地址**

在 Zeabur Dashboard → frontend 服务 → Domains，查看实际的域名。

- 如果配置 `name: "web"`，完整域名应为 `web-项目名.zeabur.app` 或类似格式
- 如果配置为空或留空，则使用根域名 `项目名.zeabur.app`

**nginx.conf 配置参考**

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

---

## 5. ConfigProvider 未定义错误

### 问题描述

浏览器控制台报错：`Uncaught ReferenceError: ConfigProvider is not defined`

### 原因分析

`babel-plugin-import` 是为 Ant Design v4 设计的按需导入插件，与 Ant Design v5 不兼容，导致组件未被正确打包。

### 解决方案

**移除 babel-plugin-import 插件**（Ant Design v5 已经自动做 Tree Shaking）：

1. 更新 `vite.config.js`，移除 babel 插件配置：

```javascript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  build: {
    minify: 'esbuild',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          antd: ['antd'],
        },
      },
    },
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
      },
    },
  },
});
```

2. 从 `package.json` 中移除依赖：

```bash
npm uninstall babel-plugin-import
```

3. 重新构建部署：

```bash
rm -rf dist node_modules/.vite
npm install
npm run build
```

---

## 6. HOSTNAME_NOT_FOUND 错误

### 问题描述

访问前端页面时，浏览器控制台显示 `404: HOSTNAME_NOT_FOUND` 或服务无法处理请求。

### 原因分析

这是 DNS/服务发现错误，通常意味着：
1. **后端服务未就绪**或未正常启动
2. **数据库连接失败**导致后端启动崩溃
3. **服务启动超时**被 Zeabur kill

### 解决方案

**步骤 1：检查后端服务状态**

访问 `https://api.你的域名.com/health` 查看后端是否响应。

**步骤 2：确认 PostgreSQL 服务已就绪**

在 Zeabur 控制台确认：
- Postgres 服务状态为 ✅ Ready（不是 ⏳ Provisioning）
- DATABASE_URL 环境变量已正确注入

**步骤 3：添加启动重试逻辑**

在 `backend/main.py` 中添加数据库连接重试：

```python
import asyncio
import asyncpg

async def wait_for_db(max_retries=30, delay=3):
    """等待数据库就绪，带重试"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set yet, retrying...")
        return False
    
    for i in range(max_retries):
        try:
            conn = await asyncpg.connect(db_url)
            await conn.close()
            print("Database connected!")
            return True
        except Exception as e:
            print(f"DB not ready ({i+1}/{max_retries}): {e}")
            if i < max_retries - 1:
                await asyncio.sleep(delay)
    return False

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up...")
    db_ready = await wait_for_db()
    if not db_ready:
        print("WARNING: Database unavailable at startup")
    # ... 其余代码
```

---

## 7. 服务被 OOM 驱逐（内存不足）

### 问题描述

Zeabur 日志显示 Pod 被 Evicted，错误信息：
```
The node was low on resource: memory
Threshold quantity: 100Mi, available: 91332Ki
Container was using 551444Ki (≈538Mi)
```

服务反复启动后被杀死，形成死亡循环。

### 原因分析

**内存消耗过大**：
| 组件 | 预估内存 |
|------|----------|
| HuggingFace Embedding 模型 (BAAI/bge-small-zh-v1.5) | 100-200 MB |
| ChromaDB 向量索引 | 200-300+ MB |
| LangGraph 编译图 | 50-100 MB |
| 对话历史缓冲 | 20-50 MB |
| **总计** | **~400-650 MB** |

538Mi 的内存消耗对 Zeabur 共享节点来说**远超合理范围**。

### 解决方案

**方案 A：优化代码（根本解决）**

1. **使用更轻量的 Embedding 模型**：
   - 考虑 ONNX 量化版本（减少 50-70% 内存）
   - 或使用纯 API 调用方式

2. **ChromaDB 内存优化**：
   - 使用 `chromadb.HttpClient` 模式独立部署

3. **按需加载模型**：
   - 将 HuggingFace 模型改为请求时才加载

**方案 B：升级 Zeabur 套餐**

获取更大内存的节点，避免与其他用户竞争资源。

**方案 C：临时缓解**

1. 减少索引的文档数量
2. 重启后不要立即发送大量请求
3. 使用健康检查机制，在内存稳定后再接入流量

---

## 8. 前端打包体积优化

### 问题描述

前端打包产物过大，影响加载速度。

### 解决方案

**步骤 1：安装压缩插件**

```bash
npm install vite-plugin-compression -D
```

**步骤 2：更新 vite.config.js**

```javascript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import viteCompression from 'vite-plugin-compression';

export default defineConfig({
  plugins: [
    react(),
    viteCompression({
      algorithm: 'gzip',
      ext: '.gz',
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  build: {
    minify: 'esbuild',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          antd: ['antd'],
        },
      },
    },
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
      },
    },
  },
});
```

**步骤 3：更新 nginx.conf 支持 gzip 静态文件**

```nginx
server {
    gzip on;
    gzip_vary on;
    gzip_static on;  # 优先使用预压缩的 .gz 文件
    gzip_types text/plain application/javascript application/css application/json;
    gzip_min_length 1024;
    
    location ~* \.(js|css|html|svg)$ {
        gzip_static on;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

**优化效果**（以 antd 为例）：
| 文件 | 优化前 | 优化后 | 节省 |
|------|--------|--------|------|
| antd | 983 KB | 498 KB | -49% |
| antd (gzip) | 309 KB | 161 KB | -48% |

---

## 9. ChromaDB preset 缺失

### 问题描述

Zeabur 预设市场没有 ChromaDB 选项。

### 解决方案

**方案 A：使用 ChromaDB 官方 Docker 镜像（推荐）**

在 Zeabur 控制台 **Add Service → Docker Image**，填入：

```
chromadb/chroma:latest
```

配置：
| 配置项 | 值 |
|--------|-----|
| Port | `8000`（TCP） |
| 环境变量 `IS_PERSISTENT` | `TRUE` |
| 环境变量 `ANONYMIZED_TELEMETRY` | `FALSE` |
| 持久卷挂载 | 容器内 `/chroma/chroma` → Zeabur 持久卷 |

然后后端环境变量指向它：
```
CHROMA_HOST=<chroma服务的内部域名>
CHROMA_PORT=8000
```

> ⚠️ 需要将 `document_service.py` 里的 `PersistentClient` 改成 `HttpClient`。

**方案 B：继续嵌入式模式（零代码改动）**

在 Zeabur 控制台给 backend 服务挂一个持久卷到 `/app/chroma_data`，ChromaDB 数据目录即可持久化。

**方案 C：在后端容器内同时运行 Chroma**

修改 Dockerfile，同时启动 uvicorn 和 chroma 进程：

```dockerfile
CMD ["sh", "-c", "chroma run --path /app/chroma_data --host 0.0.0.0 --port 8000 & uvicorn main:app --host 0.0.0.0 --port 8000"]
```

---

## 10. 中国大陆网络限制

### 备案域名限制

只影响 Zeabur 给的默认子域名，有以下绕过方式：

| 选项 | 可行性 |
|------|--------|
| 使用 `.zeabur.app` 子域名 | ❌ 需要实名 |
| 自有阿里云备案域名 CNAME 到 Zeabur | ✅ 完全可以 |
| 海外用户访问 | ✅ 完全没问题 |

### GFW / Docker Hub 访问限制

**推荐方案：选择 Zeabur 香港/新加坡/日本区域**

- GFW 影响小
- 大陆访问延迟低（30~80ms）
- 不需要备案

在 `zeabur.json` 里：
```json
"region": "hkg01"
```

**镜像加速（如果必须用大陆节点）**

| 资源 | 国内镜像 |
|------|----------|
| Docker Hub | `docker.m.daocloud.io` |
| HuggingFace | `HF_ENDPOINT=https://hf-mirror.com` |
| PyPI | `https://mirrors.aliyun.com/pypi/simple/` |

---

## 11. 购买服务器后的调整

### ⚠️ 关键问题：docker-compose 模式阻塞 zeabur.json

**核心发现**：`zeabur.json` **不是**用于 GitHub 自动部署多 service 的配置文件。它是 **Template 配置文件**，必须通过 CLI 手动触发才能部署：

```bash
npx zeabur template deploy -f zeabur.json
```

**重要**：GitHub 自动部署时，Zeabur **不会**读取 `zeabur.json` 来创建多 service。GitHub 推送只会触发一次部署，Zeabur 只会检测到一个服务。

### 解决方案

**方案 A：在 Zeabur Dashboard 手动创建服务（推荐）**

1. 删除现有服务
2. 在同一项目下，手动点击 **Add Service** 三次：
   - Service 1：选 GitHub → 选仓库 → **Root Directory 设为 `backend`** → Dockerfile 选 `zeabur.Dockerfile`
   - Service 2：选 GitHub → 选仓库 → **Root Directory 设为 `frontend`** → Dockerfile 选 `Dockerfile`
   - Service 3：选 **Postgres** preset

3. 配置域名和环境变量

**方案 B：使用 Template CLI 手动部署**

```bash
npx zeabur template deploy -f zeabur.json
```

但这不能实现 GitHub push 自动部署。

### 必须修复的代码问题

**问题 A：`DB_PORT` 默认值错误**

```python
DB_PORT = os.getenv("DB_PORT", "5433")  # ❌ 应该是 5432
```

**问题 B：数据库迁移缺失**

容器启动命令需要先运行迁移：

```dockerfile
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"]
```

**问题 C：ChromaDB 持久化**

确保 `/app/chroma_data` 目录挂载了 Zeabur 持久卷。

### 前端 Dockerfile 优化

```dockerfile
# 多阶段构建
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# 生产镜像
FROM nginx:1.27-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 后端 Dockerfile 优化

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 12. 代码中的信息泄露

### 严重泄露（Critical）

**DeepSeek API Key 暴露在源代码中**

`config.py` 包含明文 API Key：
```python
# DEEPSEEK_API_KEY=sk-65a35f195fac4c208bb55e6753dfef22
```

**数据库密码暴露**

```json
"DATABASE_URL": "postgresql://root:dwbzL98K3Z65GRjf7Q2EVYyc41H0nCSB@..."
```

### 修复建议

1. **立即轮换 DeepSeek API Key**：[DeepSeek 平台](https://platform.deepseek.com/) 重新生成
2. **从 Git 历史中移除敏感信息**：使用 `git filter-branch` 或 `BFG Repo-Cleaner`
3. **使用环境变量而非硬编码**

---

## 13. Zeabur 镜像缓存问题

### 问题描述

删除 GitHub 上的 compose 文件后，Zeabur 仍使用缓存的 compose 模式镜像部署。

### 原因分析

Zeabur registry 缓存了 docker-compose 模式的镜像，镜像 tag 以 `d-` 开头（如 `d-6a58add7e9e39c73978fb421`）。

### 解决方案

1. **删除整个 Zeabur 项目**，让 Zeabur 重新扫描仓库
2. **联系 Zeabur 支持**，请求清除项目/仓库关联的缓存镜像
3. **在 GitHub 创建新 Release**，触发新的 webhook

---

## 快速检查清单

部署前请确认以下事项：

- [ ] `zeabur.json` 配置正确（服务名、路径、端口）
- [ ] `config.py` 中数据库端口为 5432
- [ ] `Dockerfile` 使用生产模式（移除 `--reload`）
- [ ] `.env` 文件在 `.gitignore` 中
- [ ] ChromaDB 有持久化方案
- [ ] 前端已重新构建
- [ ] 数据库迁移命令已配置
- [ ] API Key 和密码已从代码中移除

---

## 联系与支持

如有问题，请检查：
1. Zeabur Dashboard → 服务 Logs
2. 浏览器开发者工具 → Network 面板
3. GitHub Issues

---

*文档生成时间：2026-07-23*

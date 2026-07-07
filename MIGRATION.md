# 数据迁移与跨机器部署指南

本指南说明如何把 `compose-yml` 项目（包括数据库、向量缓存、Embedding 模型）从一台机器完整迁移到另一台机器。

---

## 一、需要迁移的内容

光搬数据不够，下面这些**都要一起带走**：

| 内容 | 存储位置 | 是否必须 |
|---|---|---|
| 项目源代码 | `D:\Code\compose-yml\` 整个目录 | ✅ 必须 |
| 环境变量 | 项目根目录的 `.env`（含数据库密码、密钥等） | ✅ 必须 |
| 数据库数据 | Docker 命名卷 `compose-yml_postgres_data` | ✅ 必须（如果想保留用户/文档数据） |
| Chroma 向量数据 | Docker 命名卷 `compose-yml_chroma_data` | ⚠️ 视情况（重建也行，但会丢失已索引的文档向量） |
| Embedding 模型缓存 | Docker 命名卷 `compose-yml_embedding_models` | ⚠️ 视情况（不迁则重新下载，国内用 hf-mirror 加速） |
| Alembic 版本文件 | `backend/alembic/versions/` | ✅ 必须（跟代码一起走） |

> **验证卷实际路径**
>
> ```powershell
> docker volume inspect compose-yml_postgres_data --format "{{ .Mountpoint }}"
> ```
>
> Windows 下通常落在 Docker 管理的虚拟磁盘中，不会出现在你的项目目录里。

---

## 二、迁移方案 A —— 直接复制 Docker 卷（最快）

适用于：完全相同的项目结构，只是换台机器开发。

### 1. 在当前机器导出

```powershell
# 1. 导出 Postgres 卷
docker run --rm -v compose-yml_postgres_data:/source -v ${PWD}:/backup alpine tar czf /backup/postgres_data.tar.gz -C /source .

# 2. 导出 Chroma 向量数据
docker run --rm -v compose-yml_chroma_data:/source -v ${PWD}:/backup alpine tar czf /backup/chroma_data.tar.gz -C /source .

# 3. 导出 Embedding 模型缓存
docker run --rm -v compose-yml_embedding_models:/source -v ${PWD}:/backup alpine tar czf /backup/embedding_models.tar.gz -C /source .

# 4. 把整个项目目录 + 三个 .tar.gz + .env 一起打包传到新机器
# 例如用 git 推送 / U 盘 / scp 都行
```

### 2. 在新机器导入

```powershell
# 1. 把项目放到新机器的任意目录（路径不一定要一致）

# 2. 启动容器（先创建空卷）
docker compose up -d postgres

# 3. 导入 Postgres 数据
docker run --rm -v compose-yml_postgres_data:/target -v ${PWD}:/backup alpine sh -c "tar xzf /backup/postgres_data.tar.gz -C /target"

# 4. 导入 Chroma 数据
docker run --rm -v compose-yml_chroma_data:/target -v ${PWD}:/backup alpine sh -c "tar xzf /backup/chroma_data.tar.gz -C /target"

# 5. 导入 Embedding 模型（可选）
docker run --rm -v compose-yml_embedding_models:/target -v ${PWD}:/backup alpine sh -c "tar xzf /backup/embedding_models.tar.gz -C /target"

# 6. 重启所有服务
docker compose restart
```

**优点**：字节级一致，最快。
**缺点**：对 Postgres 版本敏感（小版本不同可能不兼容，建议新机器保持 `postgres:16-alpine`）。

---

## 三、迁移方案 B —— `pg_dump` 导出 SQL（最稳）

适用于：换数据库版本、只想保留业务数据、或作为日常备份方案。

### 1. 在当前机器导出

```powershell
# 1. 导出数据库为 SQL
docker exec postgres_service pg_dump -U postgres MyAgentApp > backup.sql

# 2. 单独打包 Chroma 数据（Chroma 用文件系统，不走 SQL）
docker run --rm -v compose-yml_chroma_data:/source -v ${PWD}:/backup alpine tar czf /backup/chroma_backup.tar.gz -C /source .

# 3. 打包项目代码 + .env + backup.sql + chroma_backup.tar.gz 一并迁移
```

### 2. 在新机器导入

```powershell
# 1. 启动空数据库
docker compose up -d postgres

# 2. 导入 SQL
Get-Content backup.sql | docker exec -i postgres_service psql -U postgres MyAgentApp

# 3. 恢复 Chroma 数据
docker run --rm -v compose-yml_chroma_data:/target -v ${PWD}:/backup alpine sh -c "tar xzf /backup/chroma_backup.tar.gz -C /target"

# 4. 重启服务
docker compose restart
```

**优点**：跨 Postgres 版本兼容，文件小，可读，方便做版本控制。
**缺点**：Chroma 仍然要走文件系统单独处理。

---

## 四、只迁移数据库的最小操作（备份常用）

如果只是日常备份（不换机器），一条命令足够：

```powershell
# 导出
docker exec postgres_service pg_dump -U postgres MyAgentApp > backup_%date:~0,4%%date:~5,2%%date:~8,2%.sql
```

恢复：

```powershell
# 导入
Get-Content backup_20260707.sql | docker exec -i postgres_service psql -U postgres MyAgentApp
```

---

## 五、常见坑

1. **`.env` 没带过去** → 容器连不上数据库、Chroma 报错。第一件事就把 `.env` 带上。
2. **Embedding 模型没迁** → 启动后端时卡住，几分钟才进 ready 状态，因为要从 HuggingFace 拉模型。建议用国内镜像：
   ```powershell
   docker exec fastapi_backend python -c "from huggingface_hub import snapshot_download; snapshot_download('BAAI/bge-small-zh-v1.5', cache_dir='/app/models', endpoint='https://hf-mirror.com')"
   ```
3. **Postgres 版本不一致** → 用方案 B（pg_dump）规避，或保持镜像 tag 不变（`postgres:16-alpine`）。
4. **alembic 版本文件缺失** → 容器启动时 alembic 识别不到迁移，会让你手动 `alembic upgrade head`。把 `backend/alembic/versions/` 完整保留。
5. **容器卷名依赖项目目录名** → 卷名是 `compose-yml_postgres_data`（前缀来自 `docker-compose.yml` 所在目录）。如果新机器项目目录改名了，卷也会改名，需要在脚本里同步改前缀。

---

## 六、推荐做法

- **日常备份** → 方案 B（pg_dump 单独导出）
- **整盘换机器** → 方案 A（卷打包，速度最快）
- **CI / 测试环境** → 方案 B（可重复构建）
- **不迁移 Embedding 模型** → 让新机器按需从 `hf-mirror.com` 拉，比传一个几 GB 的 tar 灵活

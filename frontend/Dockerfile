# ============================================================
# Frontend 生产环境 Dockerfile (用于 Zeabur 部署)
#
# 本地开发请使用：
#   npm run dev
# 或 docker-compose（frontend 默认已注释，需要时启用）
# ============================================================

# ---- 构建阶段：编译 Vite 产物 ----
FROM node:18-alpine AS builder

WORKDIR /app

# 先拷贝 package 文件，利用 docker layer cache
COPY package*.json ./

# npm ci 比 npm install 更稳定（要求 package-lock.json 存在）
RUN npm ci --no-audit --no-fund

# 拷贝源码
COPY . .

# 构建生产产物到 /app/dist
RUN npm run build

# ---- 运行阶段：nginx 服务静态文件 ----
FROM nginx:1.27-alpine

# 移除 nginx 默认配置
RUN rm -f /etc/nginx/conf.d/default.conf

# 拷贝自定义 nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 从构建阶段拷贝 dist 产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 暴露 80 端口（必须与 zeabur.json 的 port 一致）
EXPOSE 80

# 健康检查：访问首页
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q -O- http://127.0.0.1/ >/dev/null 2>&1 || exit 1

# nginx 镜像默认 CMD 已包含 nginx -g "daemon off;"
CMD ["nginx", "-g", "daemon off;"]

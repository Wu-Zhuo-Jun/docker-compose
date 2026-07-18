#!/bin/sh
# ============================================================
# frontend/docker-entrypoint.sh
# ============================================================
# 在 nginx 启动前，把 nginx 配置里的 ${API_UPSTREAM} 替换成
# 实际的上游地址（通过环境变量注入）。
#   - Zeabur 上: http://${BACKEND_HOSTNAME}:8000
#   - 本地 docker-compose: http://backend:8000
# ============================================================
set -e

# 缺省值：本地开发默认指向 docker-compose 里的 backend 服务名
: "${API_UPSTREAM:=http://backend:8000}"

# 把环境变量展开到 nginx 配置里
envsubst '${API_UPSTREAM}' < /etc/nginx/conf.d/default.conf \
    > /etc/nginx/conf.d/default.conf.tmp \
    && mv /etc/nginx/conf.d/default.conf.tmp /etc/nginx/conf.d/default.conf

echo "[entrypoint] API_UPSTREAM=${API_UPSTREAM}"
echo "[entrypoint] nginx config:"
cat /etc/nginx/conf.d/default.conf

# 启动 nginx（前台运行）
exec nginx -g "daemon off;"

#!/bin/sh
# ============================================================
# frontend/docker-entrypoint.sh
# ============================================================
set -e

# 缺省值（本地 docker-compose 使用）
DEFAULT_UPSTREAM="http://backend.zeabur.internal:8000"

# Zeabur 会注入 API_UPSTREAM 环境变量；优先用它，没有则用默认值
UPSTREAM="${API_UPSTREAM:-${DEFAULT_UPSTREAM}}"

echo "[entrypoint] API_UPSTREAM=${API_UPSTREAM}"
echo "[entrypoint] Using UPSTREAM=${UPSTREAM}"

# 读取模板配置，把 ${API_UPSTREAM} 替换成实际地址，写入 nginx 配置目录
sed "s|\${API_UPSTREAM}|${UPSTREAM}|g" /etc/nginx/conf.d/default.conf \
    > /etc/nginx/conf.d/default.conf.tmp \
    && mv /etc/nginx/conf.d/default.conf.tmp /etc/nginx/conf.d/default.conf

# 验证 proxy_pass 是否被正确替换
if grep -q '\${API_UPSTREAM}' /etc/nginx/conf.d/default.conf; then
    echo "[entrypoint] ERROR: proxy_pass still contains unsubstituted \${API_UPSTREAM}"
    exit 1
fi

echo "[entrypoint] nginx config OK, starting nginx..."
exec nginx -g "daemon off;"

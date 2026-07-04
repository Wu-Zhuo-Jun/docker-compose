"""
PostgreSQL 连接冒烟测试。

执行方式（在项目根目录）：
  docker exec fastapi_backend python -c "$(cat backend/_test_pg.py)"

或者分两步：
  docker cp backend/_test_pg.py fastapi_backend:/tmp/_test_pg.py
  docker exec -w /app fastapi_backend python /tmp/_test_pg.py
"""

import os
import sys

import psycopg2
from psycopg2 import OperationalError, sql


def main() -> int:
    db_host = os.environ.get("DB_HOST", "host.docker.internal")
    db_port = int(os.environ.get("DB_PORT", "5432"))
    db_name = os.environ.get("DB_NAME", "MyAgentApp")
    db_user = os.environ.get("DB_USER", "postgres")
    db_password = os.environ.get("DB_PASSWORD", "")

    print(f"Target: postgresql://{db_user}:***@{db_host}:{db_port}/{db_name}")
    print(f"psycopg2 version: {psycopg2.__version__.strip()}")
    print("-" * 50)

    try:
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password,
            connect_timeout=5,
        )
    except OperationalError as e:
        print("FAILED to connect:")
        print(f"  {type(e).__name__}: {e}")
        return 1

    try:
        with conn.cursor() as cur:
            # 1. 服务端版本
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
            print("CONNECTED")
            print(f"  Server: {version}")

            # 2. 当前用户/库
            cur.execute("SELECT current_user, current_database();")
            user, db = cur.fetchone()
            print(f"  current_user     = {user}")
            print(f"  current_database = {db}")

            # 3. 列出所有表（确认 MyAgentApp 库里能看到表）
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' ORDER BY table_name;"
            )
            tables = [row[0] for row in cur.fetchall()]
            print(f"  tables in 'public' ({len(tables)}): {tables or '[]'}")
    finally:
        conn.close()
        print("CONNECTION CLOSED")

    return 0


if __name__ == "__main__":
    sys.exit(main())
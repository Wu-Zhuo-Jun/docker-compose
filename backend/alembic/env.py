import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# 让 alembic 进程能 import 项目内的包
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

from services.database import Base  # noqa: E402
from db_models import User  # noqa: F401  触发模型注册到 Base.metadata

# Alembic Config 对象,提供 alembic.ini 的访问
config = context.config

# 读取 alembic.ini 的日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 直接从项目 config 拿 DATABASE_URL,避免在 ini 里硬编码
from config import DATABASE_URL  # noqa: E402

config.set_main_option("sqlalchemy.url", DATABASE_URL)

# autogenerate 要靠这个对比模型和数据库的差异
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """offline 模式:只生成 SQL 不连库。"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """online 模式:直接连库执行。"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
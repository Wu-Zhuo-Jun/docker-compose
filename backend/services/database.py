# -*- coding: utf-8 -*-
"""
=============================================================================
数据库连接模块
=============================================================================

提供 PostgreSQL 数据库连接，支持 SQLAlchemy ORM 和原生 SQL。
使用前需确保：
1. PostgreSQL 服务已启动
2. .env 文件中配置了 DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

=============================================================================
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from config import DATABASE_URL

# 创建引擎
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Session 工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ORM 基类
Base = declarative_base()


def get_db():
    """获取数据库会话，yield 模式，自动关闭"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库（创建所有表）"""
    Base.metadata.create_all(bind=engine)

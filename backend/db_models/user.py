# -*- coding: utf-8 -*-
"""
User 模型 —— 对应 public.users 表。

字段:
- id          : 自增主键
- username    : 登录名,唯一
- password_hash : bcrypt 摘要(不存明文)
- created_at  : 注册时间

使用:
    from db_models import User
    db.add(User(username="admin", password_hash=User.hash_password("admin")))
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
import bcrypt

from services.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    @staticmethod
    def hash_password(raw: str) -> str:
        # bcrypt 限制密码不超过 72 字节,提前截断避免 ValueError
        raw_bytes = raw.encode("utf-8")[:72]
        return bcrypt.hashpw(raw_bytes, bcrypt.gensalt()).decode("utf-8")

    def verify_password(self, raw: str) -> bool:
        try:
            raw_bytes = raw.encode("utf-8")[:72]
            return bcrypt.checkpw(raw_bytes, self.password_hash.encode("utf-8"))
        except Exception:
            return False

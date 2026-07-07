# -*- coding: utf-8 -*-
"""
用户认证路由 —— 极简实现,只满足"登录页接得上"。

POST /auth/register  : 创建用户(明文密码经过 bcrypt 摘要后入库)
POST /auth/login     : 校验用户名/密码

后续要扩展(jwt / session / 角色 / 找回密码)再迭代。
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from services.database import get_db
from db_models import User

router = APIRouter(prefix="/auth", tags=["认证"])


class AuthPayload(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    created_at: str


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: AuthPayload, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="用户已存在")

    user = User(
        username=payload.username,
        password_hash=User.hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _serialize(user)


@router.post("/login", response_model=UserOut)
def login(payload: AuthPayload, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not user.verify_password(payload.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return _serialize(user)


def _serialize(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }

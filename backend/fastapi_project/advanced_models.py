# -*- coding: utf-8 -*-
"""
=============================================================================
FastAPI 请求和响应模型示例
=============================================================================

本文件展示 FastAPI 中更复杂的请求和响应模式：
1. 嵌套 Pydantic 模型
2. 列表类型字段
3. 自定义验证器
4. 文件上传
5. 响应模型配置

=============================================================================
"""

from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator, model_validator, computed_field
from pydantic_settings import BaseSettings
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from enum import Enum
from decimal import Decimal
import json
import csv
import io


app = FastAPI(title="高级请求响应示例")


# ============================================================================
# 第一部分：嵌套模型和复杂类型
# ============================================================================

class Address(BaseModel):
    """地址模型"""
    street: str
    city: str
    state: str
    zip_code: str = Field(pattern=r"^\d{6}$")  # 6位数字邮编
    country: str = "中国"


class User(BaseModel):
    """用户模型 - 展示嵌套 Pydantic 模型"""
    
    id: int
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    age: Optional[int] = Field(None, ge=0, le=150)
    
    # 嵌套模型
    address: Optional[Address] = None
    
    # 列表字段
    hobbies: List[str] = Field(default_factory=list)
    
    # 字典字段
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # 计算属性（基于其他字段自动计算）
    @computed_field
    @property
    def username_length(self) -> int:
        """用户名长度"""
        return len(self.username)
    
    # 自定义验证器
    @field_validator("username")
    @classmethod
    def username_no_spaces(cls, v: str) -> str:
        """验证用户名不包含空格"""
        if " " in v:
            raise ValueError("用户名不能包含空格")
        return v.lower()  # 自动转为小写


class OrderStatus(str, Enum):
    """订单状态枚举"""
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class OrderItem(BaseModel):
    """订单项"""
    product_id: int
    product_name: str
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0, decimal_places=2)


class Order(BaseModel):
    """订单模型 - 展示模型验证"""
    
    id: int
    user_id: int
    items: List[OrderItem]
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    
    # 模型级别验证
    @model_validator(mode="after")
    def validate_order(self):
        """验证订单"""
        if not self.items:
            raise ValueError("订单必须包含至少一个商品")
        
        # 计算总金额
        total = sum(item.quantity * item.unit_price for item in self.items)
        
        # 可以在这里添加额外验证逻辑
        if total > Decimal("100000"):
            raise ValueError("单笔订单金额不能超过 100000")
        
        return self
    
    @computed_field
    @property
    def total_amount(self) -> Decimal:
        """订单总金额"""
        return sum(item.quantity * item.unit_price for item in self.items)
    
    @computed_field
    @property
    def item_count(self) -> int:
        """商品总数量"""
        return sum(item.quantity for item in self.items)


# ============================================================================
# 第二部分：请求体示例
# ============================================================================

@app.post("/users/", response_model=User, tags=["请求体"])
async def create_user(user: User):
    """
    创建用户
    
    展示各种字段类型的验证
    """
    return user


@app.post("/orders/", response_model=Order, tags=["请求体"])
async def create_order(order: Order):
    """
    创建订单
    
    展示模型级别的验证
    """
    return order


# ============================================================================
# 第三部分：表单数据
# ============================================================================

class LoginRequest(BaseModel):
    """登录请求模型（也可以用表单）"""
    username: str
    password: str


@app.post("/login-form/", tags=["表单"])
async def login_form(
    username: str = Form(..., description="用户名"),
    password: str = Form(..., description="密码"),
    remember_me: bool = Form(False, description="记住我")
):
    """
    模拟登录（使用表单数据）
    
    当请求 Content-Type 是 application/x-www-form-urlencoded 时使用
    """
    return {
        "username": username,
        "password": "***",  # 安全起见不返回密码
        "remember_me": remember_me,
        "login_time": datetime.now().isoformat()
    }


# ============================================================================
# 第四部分：文件上传
# ============================================================================

@app.post("/upload-file/", tags=["文件上传"])
async def upload_file(
    file: UploadFile = File(..., description="要上传的文件"),
    description: Optional[str] = Form(None, description="文件描述")
):
    """
    单文件上传
    
    - **file**: 上传的文件
    - **description**: 可选的描述信息
    """
    # 读取文件内容
    contents = await file.read()
    
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(contents),
        "description": description,
        "uploaded_at": datetime.now().isoformat()
    }


@app.post("/upload-files/", tags=["文件上传"])
async def upload_multiple_files(
    files: List[UploadFile] = File(..., description="多个文件")
):
    """
    多文件上传
    
    同时上传多个文件
    """
    results = []
    for file in files:
        contents = await file.read()
        results.append({
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(contents)
        })
    
    return {
        "total_files": len(files),
        "files": results
    }


# ============================================================================
# 第五部分：自定义响应
# ============================================================================

@app.get("/export/orders/csv", tags=["导出"])
async def export_orders_csv(
    status: Optional[OrderStatus] = None
):
    """
    导出订单为 CSV 格式
    
    使用 StreamingResponse 流式返回大文件
    """
    # 创建内存中的 CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入表头
    writer.writerow(["订单ID", "用户ID", "状态", "总金额", "创建时间"])
    
    # 模拟数据
    sample_orders = [
        [1, 100, "pending", "199.99", "2024-01-01 10:00:00"],
        [2, 101, "paid", "299.99", "2024-01-02 11:00:00"],
    ]
    
    # 筛选
    if status:
        sample_orders = [o for o in sample_orders if o[2] == status.value]
    
    # 写入数据
    for order in sample_orders:
        writer.writerow(order)
    
    # 获取 CSV 内容
    csv_content = output.getvalue()
    output.close()
    
    # 返回流式响应
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=orders.csv"
        }
    )


# ============================================================================
# 第六部分：Settings 配置
# ============================================================================

class Settings(BaseSettings):
    """
    应用配置模型
    
    使用 pydantic-settings 从环境变量加载配置
    
    在 .env 文件中设置：
    DATABASE_URL=postgresql://localhost:5432/mydb
    SECRET_KEY=your-secret-key
    DEBUG=true
    """
    app_name: str = "FastAPI 应用"
    debug: bool = False
    database_url: str = "sqlite:///./default.db"
    secret_key: str = "default-secret-key"
    
    class Config:
        env_file = ".env"  # 读取 .env 文件
        case_sensitive = False  # 环境变量不区分大小写


settings = Settings()


@app.get("/settings", tags=["配置"])
async def get_settings():
    """
    获取当前配置（敏感信息已隐藏）
    """
    return {
        "app_name": settings.app_name,
        "debug": settings.debug,
        "database_url": "***",  # 隐藏敏感信息
        "secret_key": "***"     # 隐藏敏感信息
    }


# ============================================================================
# 第七部分：响应模型配置
# ============================================================================

class UserPublic(BaseModel):
    """
    公开的用户信息（不包含敏感字段）
    
    使用 response_model 控制返回字段
    """
    id: int
    username: str
    email: str


class UserPrivate(BaseModel):
    """完整的用户信息（包含敏感字段）"""
    id: int
    username: str
    email: str
    password_hash: str  # 敏感字段
    api_key: str       # 敏感字段


@app.get("/users/{user_id}/public", response_model=UserPublic, tags=["响应模型"])
async def get_user_public(user_id: int):
    """
    获取公开的用户信息
    
    只返回非敏感字段
    """
    return {
        "id": user_id,
        "username": "example_user",
        "email": "user@example.com",
        "password_hash": "should_not_show",
        "api_key": "should_not_show"
    }


@app.get("/users/{user_id}/private", response_model=UserPrivate, tags=["响应模型"])
async def get_user_private(user_id: int):
    """
    获取完整的用户信息（需要权限）
    
    包含敏感字段
    """
    return {
        "id": user_id,
        "username": "example_user",
        "email": "user@example.com",
        "password_hash": "hashed_password_here",
        "api_key": "sk-1234567890"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

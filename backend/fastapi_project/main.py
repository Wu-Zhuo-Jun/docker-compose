# -*- coding: utf-8 -*-
"""
=============================================================================
FastAPI 项目入口文件
=============================================================================

FastAPI 是一个现代化的 Python Web 框架，具有以下特点：

1. 高性能：基于 Starlette 和 Pydantic，速度可与 Node.js 和 Go 相媲美
2. 自动文档：自动生成 OpenAPI (Swagger) 文档
3. 类型安全：完全基于类型注解，支持 IDE 自动补全
4. 异步支持：原生支持 async/await

本文件展示 FastAPI 的核心功能和 CRUD 操作。

运行方式：
    uvicorn main:app --reload  # 开发模式
    uvicorn main:app --host 0.0.0.0 --port 8000  # 生产模式

文档地址：
    http://localhost:8000/docs  # Swagger UI
    http://localhost:8000/redoc  # ReDoc
    http://localhost:8000/openapi.json  # OpenAPI JSON

=============================================================================
"""

from fastapi import FastAPI, HTTPException, Path, Query, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum
import uvicorn


# ============================================================================
# 第一部分：Pydantic 模型定义
# ============================================================================


class ItemCategory(str, Enum):
    """
    商品分类枚举

    使用 Enum 的好处：
    1. 限制可选值，防止无效数据
    2. IDE 自动补全支持
    3. 文档中清晰展示可选值
    """

    ELECTRONICS = "electronics"
    BOOKS = "books"
    CLOTHING = "clothing"
    FOOD = "food"
    OTHER = "other"


class ItemBase(BaseModel):
    """
    商品基础模型

    BaseModel 自动提供：
    - 数据验证
    - JSON 序列化/反序列化
    - Pydantic V2: 使用 model_config 配置
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="商品名称",
        examples=["iPhone 15"],
    )
    description: Optional[str] = Field(None, max_length=500, description="商品描述")
    price: float = Field(
        ...,
        gt=0,  # greater than，必须大于 0
        description="商品价格",
        examples=[999.99],
    )
    category: ItemCategory = Field(default=ItemCategory.OTHER, description="商品分类")
    tags: List[str] = Field(default=[], description="商品标签")


class ItemCreate(ItemBase):
    """
    创建商品时使用的模型

    继承 ItemBase 的所有字段，但可以添加创建时特有的字段
    例如：创建时可以指定 id，但通常 id 由数据库自动生成
    """

    pass


class ItemUpdate(BaseModel):
    """
    更新商品时使用的模型

    所有字段都是可选的，表示部分更新
    使用 | None 而不是 Optional[str]（Python 3.10+）
    """

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    price: float | None = Field(None, gt=0)
    category: ItemCategory | None = None
    tags: List[str] | None = None


class Item(ItemBase):
    """
    完整商品模型，包含自动生成的字段

    model_config 配置：
    - from_attributes=True: 允许从 ORM 对象创建 Pydantic 模型
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="商品唯一标识")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class ChatRequest(BaseModel):
    """聊天接口请求模型"""

    message: str = Field(..., description="用户输入消息", examples=["你好", "diaoni"])


class ChatResponse(BaseModel):
    """聊天接口响应模型"""

    response: str = Field(
        ..., description="接口返回内容", examples=["这是假数据：我收到了你的消息"]
    )


class ItemQueryRequest(BaseModel):
    """商品查询请求模型"""

    skip: int = Field(0, ge=0, description="跳过的记录数")
    limit: int = Field(100, ge=1, le=1000, description="返回的记录数")
    category: Optional[ItemCategory] = Field(None, description="按分类筛选")
    min_price: Optional[float] = Field(None, ge=0, description="最低价格")
    max_price: Optional[float] = Field(None, ge=0, description="最高价格")
    search: Optional[str] = Field(None, description="搜索名称或描述")


class ItemDetailRequest(BaseModel):
    """商品详情请求模型"""

    item_id: int = Field(..., ge=1, description="商品ID")


class ItemUpdateRequest(BaseModel):
    """商品更新请求模型"""

    item_id: int = Field(..., ge=1, description="商品ID")
    item: ItemUpdate = Field(..., description="更新的商品信息")


class ItemDeleteRequest(BaseModel):
    """商品删除请求模型"""

    item_id: int = Field(..., ge=1, description="商品ID")


# ============================================================================
# 第二部分：FastAPI 应用初始化
# ============================================================================

app = FastAPI(
    title="商品管理 API",
    description="""
    这是一个完整的 FastAPI CRUD 示例项目。

    ## 功能
    - 聊天 (POST /chat)
    - 创建商品 (POST /items)
    - 查询商品列表 (POST /items/query)
    - 获取单个商品 (POST /items/detail)
    - 更新商品 (POST /items/update)
    - 删除商品 (POST /items/delete)

    ## 特性
    - 完整的数据验证
    - 自动文档生成
    - 异步支持
    """,
    version="1.0.0",
    contact={"name": "技术支持", "email": "support@example.com"},
    docs_url="/docs",  # Swagger 文档地址
    redoc_url="/redoc",  # ReDoc 文档地址
)


# ============================================================================
# 第三部分：模拟数据库
# ============================================================================

# 使用内存字典模拟数据库
# 在实际应用中，这里会是 SQLAlchemy、SQLModel、Tortoise 等 ORM
items_db: Dict[int, Item] = {
    1: Item(
        id=1,
        name="iPhone 15 Pro",
        description="苹果最新款智能手机",
        price=999.99,
        category=ItemCategory.ELECTRONICS,
        tags=["手机", "苹果", "旗舰"],
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    ),
    2: Item(
        id=2,
        name="Python 入门到精通",
        description="全面的 Python 编程教程",
        price=79.99,
        category=ItemCategory.BOOKS,
        tags=["编程", "Python", "教程"],
        created_at=datetime(2024, 1, 15),
        updated_at=datetime(2024, 1, 15),
    ),
}

# 模拟自增 ID
current_max_id = 2


# ============================================================================
# 第四部分：API 路由
# ============================================================================


@app.get("/", tags=["首页"])
async def root():
    """
    首页

    返回 API 基本信息和文档链接
    """
    return {
        "message": "欢迎使用商品管理 API",
        "docs": "/docs",
        "redoc": "/redoc",
        "version": "1.0.0",
    }


@app.get("/health", tags=["系统"])
async def health_check():
    """
    健康检查

    用于监控和负载均衡探测
    """
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post(
    "/chat",
    response_model=ChatResponse,
    tags=["聊天"],
    summary="简易聊天接口",
    description="接收用户消息并返回假数据回复",
)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    简易聊天接口

    - **message**: 用户输入消息
    """
    return ChatResponse(response="这是假数据：我收到了你的消息")


@app.post(
    "/items",
    response_model=Item,
    status_code=201,
    tags=["商品管理"],
    summary="创建商品",
    description="创建一个新的商品",
)
async def create_item(item: ItemCreate) -> Item:
    """
    创建商品

    - **name**: 商品名称（必填，1-100字符）
    - **description**: 商品描述（可选）
    - **price**: 价格（必填，必须大于0）
    - **category**: 分类（可选）
    - **tags**: 标签列表（可选）
    """
    global current_max_id

    # 生成新 ID
    current_max_id += 1

    # 创建商品对象
    new_item = Item(
        id=current_max_id,
        name=item.name,
        description=item.description,
        price=item.price,
        category=item.category,
        tags=item.tags,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # 保存到数据库
    items_db[current_max_id] = new_item

    return new_item


@app.post(
    "/items/query",
    response_model=List[Item],
    tags=["商品管理"],
    summary="查询商品列表",
    description="根据 requestBody 查询商品列表",
)
async def query_items(request: ItemQueryRequest) -> List[Item]:
    """
    查询商品列表

    支持分页和筛选：
    - **skip**: 跳过的记录数（用于分页）
    - **limit**: 返回的记录数
    - **category**: 按分类筛选
    - **min_price/max_price**: 按价格区间筛选
    - **search**: 搜索名称或描述
    """
    result = list(items_db.values())

    # 按分类筛选
    if request.category:
        result = [item for item in result if item.category == request.category]

    # 按价格区间筛选
    if request.min_price is not None:
        result = [item for item in result if item.price >= request.min_price]
    if request.max_price is not None:
        result = [item for item in result if item.price <= request.max_price]

    # 搜索名称或描述
    if request.search:
        search_lower = request.search.lower()
        result = [
            item
            for item in result
            if search_lower in item.name.lower()
            or (item.description and search_lower in item.description.lower())
        ]

    # 分页
    result = result[request.skip : request.skip + request.limit]

    return result


@app.post(
    "/items/detail",
    response_model=Item,
    tags=["商品管理"],
    summary="获取单个商品",
    description="根据 requestBody 获取商品详情",
)
async def detail_item(request: ItemDetailRequest) -> Item:
    """
    获取单个商品

    - **item_id**: 商品的唯一标识
    """
    if request.item_id not in items_db:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "商品不存在",
                "item_id": request.item_id,
                "suggestion": "请检查商品ID是否正确",
            },
        )

    return items_db[request.item_id]


@app.post(
    "/items/update",
    response_model=Item,
    tags=["商品管理"],
    summary="更新商品",
    description="更新指定商品的信息",
)
async def update_item(request: ItemUpdateRequest) -> Item:
    """
    更新商品

    - **item_id**: 要更新的商品 ID
    - **item**: 要更新的字段（部分更新）

    使用 PATCH 语义：只更新提供的字段
    """
    if request.item_id not in items_db:
        raise HTTPException(
            status_code=404, detail={"error": "商品不存在", "item_id": request.item_id}
        )

    # 获取现有数据
    existing_item = items_db[request.item_id]

    # 动态更新字段（只更新非 None 的字段）
    update_data = request.item.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(existing_item, field, value)

    # 更新时间戳
    existing_item.updated_at = datetime.now()

    return existing_item


@app.post(
    "/items/delete",
    status_code=204,
    tags=["商品管理"],
    summary="删除商品",
    description="删除指定商品",
)
async def delete_item(request: ItemDeleteRequest) -> None:
    """
    删除商品

    - **item_id**: 要删除的商品 ID

    删除成功返回 204 No Content
    """
    if request.item_id not in items_db:
        raise HTTPException(
            status_code=404, detail={"error": "商品不存在", "item_id": request.item_id}
        )

    # 删除商品
    del items_db[request.item_id]

    # 返回 204 表示成功但无内容
    return None


# ============================================================================
# 第五部分：自定义响应和错误处理
# ============================================================================


@app.exception_handler(ValueError)
async def value_error_handler(request, exc: ValueError):
    """自定义异常处理器"""
    return JSONResponse(
        status_code=400, content={"error": "数据验证错误", "detail": str(exc)}
    )


# ============================================================================
# 主函数入口
# ============================================================================

if __name__ == "__main__":
    """
    直接运行此文件启动开发服务器
    
    uvicorn 配置说明：
    - reload: 启用热重载，开发时自动重载代码
    - host: 监听地址，0.0.0.0 表示所有网络接口
    - port: 端口号
    - log_level: 日志级别
    """
    print("=" * 60)
    print("启动 FastAPI 服务器")
    print("文档地址: http://localhost:8000/docs")
    print("=" * 60)

    uvicorn.run("main:app", reload=True, host="0.0.0.0", port=8000, log_level="info")

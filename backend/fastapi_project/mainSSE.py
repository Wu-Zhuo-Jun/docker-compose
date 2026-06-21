# -*- coding: utf-8 -*-
"""
=============================================================================
SSE 流式 Agent API
=============================================================================

基于 Server-Sent Events (SSE) 的流式 Agent 接口。

SSE 事件格式：
- text: LLM 逐字输出
- tool_start: 工具调用开始
- tool_end: 工具调用结束
- thinking_complete: 推理完成，最终回复

运行方式：
    cd fastapi_project
    uvicorn mainSSE:app --reload

测试：
    curl -X POST http://localhost:8000/agent/stream \
      -H "Content-Type: application/json" \
      -d "{\"message\": \"北京今天天气怎么样？\"}"

=============================================================================
"""

import os
import json
import asyncio
from typing import AsyncGenerator, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from langchain.chat_models import init_chat_model
from langchain.agents.factory import create_agent
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool, BaseTool
import uvicorn


# ============================================================================
# 环境配置
# ============================================================================

os.environ["OPENAI_API_KEY"] = "sk-e6d2f16fbdd5462ea26a0d8202e843fc"

model = init_chat_model(
    model="deepseek-chat",
    model_provider="openai",  # 使用 openai provider
    base_url="https://api.deepseek.com",  # DeepSeek API 地址
    temperature=0,
)


# ============================================================================
# 第一部分：工具定义
# ============================================================================


@tool
def get_weather(location: str) -> str:
    """
    查询指定城市的天气情况

    Args:
        location: 城市名称

    Returns:
        天气描述
    """
    weather_db = {
        "北京": "天气晴朗，温度25°C，适合户外活动",
        "上海": "天气多云，温度28°C，有轻度污染",
        "广州": "雷阵雨，温度32°C，建议带伞",
        "深圳": "天气晴朗，温度30°C，注意防晒",
    }

    if location in weather_db:
        return f"{location}：{weather_db[location]}"
    return f"抱歉，暂不支持查询 {location} 的天气"


@tool
def calculate(expression: str) -> str:
    """
    执行数学计算

    Args:
        expression: 数学表达式

    Returns:
        计算结果
    """
    try:
        result = eval(expression)
        return f"{expression} = {result}"
    except Exception as e:
        return f"计算错误: {str(e)}"


@tool
def get_current_time() -> str:
    """
    获取当前时间

    Returns:
        当前时间字符串
    """
    from datetime import datetime

    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")


def get_all_tools() -> List[BaseTool]:
    """获取所有工具"""
    return [get_weather, calculate, get_current_time]


# ============================================================================
# 第二部分：Pydantic 模型
# ============================================================================


class AgentRequest(BaseModel):
    """Agent 流式请求模型"""

    message: str = Field(..., description="用户输入消息")
    session_id: Optional[str] = Field(None, description="会话ID，用于区分不同对话")


class SSEvent(BaseModel):
    """SSE 事件模型"""

    event: str = Field(
        ..., description="事件类型: text, tool_start, tool_end, thinking_complete"
    )
    data: dict = Field(..., description="事件数据")


# ============================================================================
# 第三部分：SSE 流生成器
# ============================================================================


def format_sse(event_type: str, data: dict) -> str:
    """格式化 SSE 事件"""
    json_data = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {json_data}\n\n"


async def stream_with_astream_events(
    message: str, session_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    使用 astream_events 实现真正的流式输出

    捕获的事件类型：
    - on_chat_model_start: 模型开始
    - on_chat_model_stream: 模型逐字输出 -> text 事件
    - on_tool_start: 工具调用开始 -> tool_start 事件
    - on_tool_end: 工具调用结束 -> tool_end 事件
    """
    tools = get_all_tools()

    system_prompt = """你是一个智能助手，可以调用工具来回答问题。

    工作流程：
    1. 分析用户问题
    2. 决定是否需要调用工具
    3. 调用工具获取信息
    4. 基于结果给出回答

    回复要求：简洁明了，直接回答用户问题。
    """

    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
    )

    config: RunnableConfig = {"recursion_limit": 15, "session_id": session_id}

    full_response = ""

    try:
        # 使用 astream_events 捕获所有事件
        async for event in agent.astream_events(
            {"messages": [HumanMessage(content=message)]}, config, version="v1"
        ):
            # event 可能是字典或 AIMessageChunk 对象
            if hasattr(event, "get"):
                # 是字典
                event_type = event.get("event")
                data = event.get("data", {})
            else:
                # 是 AIMessageChunk 或其他对象
                event_type = None
                data = {"chunk": event}

            run_id = event.get("run_id", "") if hasattr(event, "get") else ""

            # 模型开始生成
            if event_type == "on_chat_model_start":
                name = (
                    event.get("name", "unknown")
                    if hasattr(event, "get")
                    else str(type(event).__name__)
                )
                yield format_sse(
                    "thinking_start", {"run_id": str(run_id), "model": name}
                )

            # 模型流式输出 - 这是主要的文本输出事件
            elif event_type == "on_chat_model_stream":
                chunk = data.get("chunk")
                if chunk is None:
                    chunk = event  # event 本身就是 chunk

                if hasattr(chunk, "content"):
                    content = chunk.content
                elif isinstance(chunk, dict):
                    content = chunk.get("content", "")
                else:
                    content = str(chunk) if chunk else ""

                if content:
                    full_response += content
                    yield format_sse(
                        "text", {"content": content, "full_text": full_response}
                    )

            # 工具调用开始
            elif event_type == "on_tool_start":
                tool_name = data.get("name", "unknown")
                tool_input = data.get("input", {})
                yield format_sse(
                    "tool_start",
                    {"tool": tool_name, "input": tool_input, "run_id": str(run_id)},
                )

            # 工具调用结束
            elif event_type == "on_tool_end":
                tool_output = data.get("output", "")
                tool_name = (
                    event.get("name", "unknown") if hasattr(event, "get") else "unknown"
                )
                yield format_sse(
                    "tool_end",
                    {
                        "tool": tool_name,
                        "output": str(tool_output),
                        "run_id": str(run_id),
                    },
                )

            # 链结束
            elif event_type == "on_chain_end":
                yield format_sse("thinking_complete", {"content": full_response})

    except Exception as e:
        yield format_sse("error", {"message": str(e)})


async def stream_agent_events(
    message: str, session_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    流式生成 Agent 事件

    Args:
        message: 用户消息
        session_id: 会话ID

    Yields:
        SSE 格式的事件字符串
    """
    tools = get_all_tools()

    system_prompt = """你是一个智能助手，可以调用工具来回答问题。

    工作流程：
    1. 分析用户问题
    2. 决定是否需要调用工具
    3. 调用工具获取信息
    4. 基于结果给出回答

    回复要求：简洁明了，直接回答用户问题。
    """

    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
    )

    config: RunnableConfig = {"recursion_limit": 15}

    messages = [HumanMessage(content=message)]
    full_response = ""

    try:
        # 使用 astream 异步流式获取输出
        async for chunk in agent.astream({"messages": messages}, config):
            if isinstance(chunk, dict):
                # 检查是否有新消息
                if "messages" in chunk:
                    for msg in chunk["messages"]:
                        if isinstance(msg, AIMessage):
                            # 检查是否有工具调用
                            if hasattr(msg, "tool_calls") and msg.tool_calls:
                                for tc in msg.tool_calls:
                                    # 发送 tool_start 事件
                                    yield format_sse(
                                        "tool_start",
                                        {
                                            "tool": tc.get("name", "unknown"),
                                            "input": tc.get("args", {}),
                                        },
                                    )

                            # 检查工具结果（在 addition_kwargs 中）
                            if hasattr(msg, "additional_kwargs"):
                                # 工具结果通过其他方式处理
                                pass

                            # 文本内容
                            if hasattr(msg, "content") and msg.content:
                                content = msg.content
                                if content != full_response:
                                    # 只发送新增的部分
                                    new_content = content[len(full_response) :]
                                    if new_content:
                                        full_response = content
                                        yield format_sse(
                                            "text", {"content": new_content}
                                        )

                # 检查是否有工具结果（AIMessageChunk 或 ToolMessage）
                for key, value in chunk.items():
                    if key == "messages":
                        continue
                    # 其他类型的 chunk（如 agent outcome）
                    if value:
                        yield format_sse("text", {"content": str(value)[:100]})

        # 发送 thinking_complete 事件
        yield format_sse("thinking_complete", {"content": full_response})

    except Exception as e:
        yield format_sse("error", {"message": str(e)})


async def stream_agent_events_v2(
    message: str, session_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    流式生成 Agent 事件（改进版，捕获工具调用）

    这个版本通过 ainvoke 获取完整结果，同时实时发送文本事件
    """
    tools = get_all_tools()

    system_prompt = """你是一个智能助手，可以调用工具来回答问题。

    请根据用户问题决定是否需要调用工具。
    """

    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
    )

    config: RunnableConfig = {"recursion_limit": 15}

    # 首先发送开始事件
    yield format_sse("text", {"content": ""})

    try:
        # 使用 ainvoke 获取结果
        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=message)]}, config
        )

        # 解析结果并发送事件
        if isinstance(result, dict) and "messages" in result:
            messages = result["messages"]

            for i, msg in enumerate(messages):
                if isinstance(msg, AIMessage):
                    # 检查工具调用
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tc in msg.tool_calls:
                            tool_name = tc.get("name", "unknown")
                            tool_args = tc.get("args", {})
                            yield format_sse(
                                "tool_start", {"tool": tool_name, "input": tool_args}
                            )

                    # 检查工具结果（在 ToolMessage 中）
                    if hasattr(msg, "name") and msg.name:
                        # 这是一个工具返回消息
                        yield format_sse(
                            "tool_end",
                            {
                                "tool": msg.name,
                                "output": msg.content
                                if hasattr(msg, "content")
                                else str(msg),
                            },
                        )

                    # 普通文本回复
                    if hasattr(msg, "content") and msg.content:
                        # 检查是否包含思考过程
                        content = msg.content

                        # 尝试解析结构化输出
                        if "Action:" in content or "Observation:" in content:
                            # ReAct 格式的输出
                            lines = content.split("\n")
                            for line in lines:
                                if line.strip():
                                    yield format_sse("text", {"content": line + "\n"})
                        else:
                            yield format_sse("text", {"content": content})

            # 发送完成事件
            final_content = messages[-1].content if messages else ""
            yield format_sse("thinking_complete", {"content": final_content})

    except Exception as e:
        yield format_sse("error", {"message": f"Agent 执行出错: {str(e)}"})


# ============================================================================
# 第四部分：FastAPI 应用
# ============================================================================

app = FastAPI(
    title="SSE Agent API",
    description="""
    基于 Server-Sent Events 的流式 Agent 接口。

    ## 事件类型

    - **text**: LLM 逐字输出
    - **tool_start**: 工具调用开始
    - **tool_end**: 工具调用结束
    - **thinking_complete**: 推理完成
    - **error**: 错误信息

    ## 测试

    ```bash
    curl -X POST http://localhost:8000/agent/stream \
      -H "Content-Type: application/json" \
      -d "{\"message\": \"北京今天天气怎么样？\"}"
    ```
    """,
    version="1.0.0",
)


# ============================================================================
# 第五部分：API 路由
# ============================================================================


@app.get("/", tags=["首页"])
async def root():
    """首页"""
    return {
        "message": "SSE Agent API",
        "docs": "/docs",
        "endpoints": {"stream": "POST /agent/stream", "health": "GET /health"},
    }


@app.get("/health", tags=["系统"])
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


@app.post(
    "/chat",
    tags=["Agent"],
    summary="流式 Agent 接口 (astream_events)",
    description="使用 astream_events 实现真正的流式输出",
)
async def chat_stream(request: AgentRequest):
    """
    流式 Agent 接口

    基于 astream_events 实现，返回以下 SSE 事件：
    - text: LLM 逐字输出
    - tool_start: 工具调用开始
    - tool_end: 工具调用结束
    - thinking_start: 开始思考
    - thinking_complete: 思考完成
    - error: 错误信息
    """
    return StreamingResponse(
        stream_with_astream_events(
            message=request.message, session_id=request.session_id
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post(
    "/agent/stream",
    tags=["Agent"],
    summary="流式 Agent 接口 (astream)",
    description="发送消息并接收 SSE 流式响应",
)
async def agent_stream(request: AgentRequest):
    """
    流式 Agent 接口

    - **message**: 用户消息（必填）
    - **session_id**: 会话ID（可选）

    返回 SSE 流，包含以下事件：
    - text: LLM 输出
    - tool_start: 工具调用开始
    - tool_end: 工具调用结束
    - thinking_complete: 推理完成
    """
    return StreamingResponse(
        stream_agent_events_v2(message=request.message, session_id=request.session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post(
    "/agent/chat",
    tags=["Agent"],
    summary="非流式 Agent 接口",
    description="发送消息并接收完整响应（非流式）",
)
async def agent_chat(request: AgentRequest):
    """
    非流式 Agent 接口

    - **message**: 用户消息（必填）
    """
    tools = get_all_tools()

    system_prompt = "你是一个智能助手。"

    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
    )

    config: RunnableConfig = {"recursion_limit": 15}

    try:
        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=request.message)]}, config
        )

        if isinstance(result, dict) and "messages" in result:
            response = result["messages"][-1].content
            return {"response": response}

        return {"response": str(result)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 第六部分：主函数
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("SSE Agent API 服务")
    print("=" * 60)
    print("流式接口: POST http://localhost:8000/agent/stream")
    print("非流式接口: POST http://localhost:8000/agent/chat")
    print("文档地址: http://localhost:8000/docs")
    print("=" * 60)

    uvicorn.run("mainSSE:app", reload=True, host="0.0.0.0", port=8000, log_level="info")

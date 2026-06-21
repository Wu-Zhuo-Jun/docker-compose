# -*- coding: utf-8 -*-
"""
Agent 控制台调试脚本
"""

import asyncio
import os
from langchain.chat_models import init_chat_model
from langchain.agents.factory import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool, BaseTool


# ============================================================================
# 配置
# ============================================================================

os.environ["OPENAI_API_KEY"] = "sk-e6d2f16fbdd5462ea26a0d8202e843fc"

model = init_chat_model(
    model="deepseek-chat",
    model_provider="openai",
    base_url="https://api.deepseek.com",
    temperature=0,
)


# ============================================================================
# 工具定义
# ============================================================================

@tool
def get_weather(location: str) -> str:
    """查询指定城市的天气情况

    Args:
        location: 城市名称，如"北京"、"上海"

    Returns:
        天气描述信息
    """
    weather_db = {
        "北京": "天气晴朗，温度25°C，适合户外活动",
        "上海": "天气多云，温度28°C，有轻度污染",
        "广州": "雷阵雨，温度32°C，建议带伞",
        "深圳": "天气晴朗，温度30°C，注意防晒",
        "杭州": "阴天，温度26°C，空气湿润",
        "成都": "小雨，温度22°C，凉爽舒适",
    }
    return weather_db.get(location, f"抱歉，暂不支持查询 {location} 的天气信息")


@tool
def get_current_time() -> str:
    """获取当前日期和时间

    Returns:
        当前日期时间字符串
    """
    from datetime import datetime
    now = datetime.now()
    weekday_names = ["一", "二", "三", "四", "五", "六", "日"]
    return now.strftime(f"%Y年%m月%d日 星期{weekday_names[now.weekday()]} %H:%M:%S")


@tool
def calculate(expression: str) -> str:
    """执行数学计算

    Args:
        expression: 数学表达式，如 "2 + 3 * 4"

    Returns:
        计算结果
    """
    try:
        result = eval(expression)
        return f"{expression} = {result}"
    except Exception as e:
        return f"计算错误: {str(e)}"


# ============================================================================
# 颜色定义
# ============================================================================

class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"


# ============================================================================
# 主函数
# ============================================================================

async def stream_chat(message: str, config: RunnableConfig):
    """
    流式聊天（带颜色输出）

    Args:
        message: 用户消息
        config: 运行配置
    """
    tools = [get_weather, get_current_time, calculate]

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

    full_response = ""

    print(f"{Colors.CYAN}[Agent]{Colors.RESET} ", end="", flush=True)

    async for event in agent.astream_events(
        {"messages": [HumanMessage(content=message)]},
        config,
        version="v1"
    ):
        event_type = event.get("event") if hasattr(event, "get") else None
        data = event.get("data", {}) if hasattr(event, "get") else {}
        
        # 获取 tool_calls
        # if event_type == "on_chat_model_end":
        #     messages = data.get("input", {}).get("messages", [])
        #     for msg in reversed(messages):
        #         if hasattr(msg, "tool_calls") and msg.tool_calls:
        #             tool_calls = msg.tool_calls
        #             print(f"{Colors.YELLOW}[工具调用1] {tool_calls}{Colors.RESET}")
        #             break


        # 模型流式输出
        if event_type == "on_chat_model_stream":
            chunk = data.get("chunk", event)
            if hasattr(chunk, "content"):
                content = chunk.content
            elif isinstance(chunk, dict):
                content = chunk.get("content", "")
            else:
                content = str(chunk) if chunk else ""

            if content:
                full_response += content
                print(content, end="", flush=True)



        # 工具调用开始
        # elif event_type == "on_tool_start":
            
        #     tool_name = data.get("name", "unknown")
        #     print(f"\n{Colors.YELLOW}[工具调用] {tool_name}{Colors.RESET}")

        # 工具调用结束
        elif event_type == "on_tool_end":
            
            output = data.get("output", "")

            tool_name = data.get("name", "unknown") if hasattr(event, "get") else "unknown"
            print(data)
            print(f"{Colors.GREEN}[工具结果] {output}{Colors.RESET}")

        # 链结束
        elif event_type == "on_chain_end":
            print(1)


async def main():
    """
    主循环
    """
    config: RunnableConfig = {"recursion_limit": 15}

    print(f"{Colors.CYAN}{'=' * 50}{Colors.RESET}")
    print(f"{Colors.CYAN}       Agent 控制台调试工具{Colors.RESET}")
    print(f"{Colors.CYAN}{'=' * 50}{Colors.RESET}")
    print(f"{Colors.WHITE}提示：{Colors.RESET}")
    print(f"  - 输入问题与 Agent 对话")
    print(f"  - 输入 'q' 或 'quit' 退出")
    print(f"  - 输入 'clear' 清屏")
    print(f"{Colors.CYAN}{'=' * 50}{Colors.RESET}")
    print()

    while True:
        try:
            message = input(f"{Colors.GREEN}你{Colors.RESET}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n")
            break

        if not message:
            continue

        if message.lower() in ['q', 'quit', 'exit']:
            print(f"{Colors.CYAN}再见！{Colors.RESET}")
            break

        if message.lower() == 'clear':
            os.system('cls' if os.name == 'nt' else 'clear')
            continue

        print()
        await stream_chat(message, config)
        print()


if __name__ == "__main__":
    print(f"{Colors.CYAN}正在初始化 Agent...\n{Colors.RESET}")
    asyncio.run(main())




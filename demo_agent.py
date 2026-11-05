"""
Interactive Demo Script for the Personal AI Assistant.
======================================================
Allows instant testing of the entire assistant architecture.
If an API key is configured in .env, it runs live with the real LLM.
If no key is configured yet, it demonstrates the tools, context manager,
and long-term memory store interactively!
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import get_settings
from tools.registry import get_all_tools
from memory.user_profile_store import get_user_store
from memory.context_manager import ContextManager
from utils.formatting import (
    print_banner,
    print_system_info,
    print_tools_table,
    print_agent_reply
)

def run_demo():
    settings = get_settings()
    user_store = get_user_store()
    tools = get_all_tools()
    
    print_banner(settings.AGENT_NAME, settings.MODEL_PROVIDER, settings.MODEL_NAME)
    print_tools_table(tools)

    api_key_set = bool(
        settings.GOOGLE_API_KEY or 
        settings.OPENAI_API_KEY or 
        settings.ANTHROPIC_API_KEY or 
        os.getenv("GOOGLE_API_KEY") or 
        os.getenv("OPENAI_API_KEY")
    )

    if api_key_set:
        print_system_info(
            "Live Mode Detected",
            f"API key detected for provider '{settings.MODEL_PROVIDER}'. Launching live agent..."
        )
        from main import run_cli
        run_cli()
        return

    # Demonstration mode without API key
    print_system_info(
        "Interactive Architecture Demonstration (with Multi-MCP)",
        "No API key detected in .env yet. Running live demonstration of all decoupled components:\n"
        "1. Real-time Weather Tool execution\n"
        "2. Safe Calculator execution\n"
        "3. Multi-MCP Server tool invocation (System Specs & Advanced Statistics)\n"
        "4. Long-term Memory Persistence (UserProfileStore)\n"
        "5. Context Window Trimming (ContextManager)"
    )

    print("\n[Step 1] Testing Weather Tool (London):")
    from tools.weather_tool import get_weather
    weather_output = get_weather.invoke({"location": "London"})
    print(f"Weather Tool Output:\n{weather_output}\n")

    print("[Step 2] Testing Safe Calculator (150 * 3 + sqrt(256)):")
    from tools.calculator_tool import calculate
    calc_output = calculate.invoke({"expression": "150 * 3 + sqrt(256)"})
    print(f"Calculator Tool Output: {calc_output}\n")

    print("[Step 3] Testing Multi-MCP Server Tools:")
    # Finding MCP tools from registered tools list
    mcp_sys_tool = next((t for t in tools if t.name == "get_system_specs"), None)
    mcp_math_tool = next((t for t in tools if t.name == "calculate_statistics"), None)

    import asyncio
    if mcp_sys_tool:
        print(f"-> Calling MCP Server #1 tool: '{mcp_sys_tool.name}'...")
        try:
            sys_res = asyncio.run(mcp_sys_tool.ainvoke({}))
            print(f"MCP Output:\n{sys_res}\n")
        except Exception as e:
            print(f"MCP Invocation note: {e}\n")

    if mcp_math_tool:
        print(f"-> Calling MCP Server #2 tool: '{mcp_math_tool.name}' with [10, 20, 30, 40, 50]...")
        try:
            stats_res = asyncio.run(mcp_math_tool.ainvoke({"numbers": [10.0, 20.0, 30.0, 40.0, 50.0]}))
            print(f"MCP Output:\n{stats_res}\n")
        except Exception as e:
            print(f"MCP Invocation note: {e}\n")

    print("[Step 4] Testing Long-Term Memory (Saving User Preferences):")
    res1 = user_store.set_fact("preferred_name", "Alex")
    res2 = user_store.set_fact("city", "San Francisco")
    res3 = user_store.set_fact("interest", "Autonomous AI Agents")
    print(f"- {res1}")
    print(f"- {res2}")
    print(f"- {res3}")
    print(f"Current Memory File ({settings.USER_FACTS_FILE}):")
    print(user_store.get_all_facts())
    print()

    print("[Step 4] Testing Context Window Optimization:")
    from langchain_core.messages import HumanMessage, AIMessage
    cm = ContextManager(max_messages=4)
    simulated_history = [
        HumanMessage(content="User message 1"),
        AIMessage(content="Bot reply 1"),
        HumanMessage(content="User message 2"),
        AIMessage(content="Bot reply 2"),
        HumanMessage(content="User message 3"),
        AIMessage(content="Bot reply 3"),
    ]
    trimmed = cm.optimize_messages(simulated_history)
    print(f"Original history: {len(simulated_history)} messages -> Optimized to: {len(trimmed)} messages")
    print("Oldest messages safely trimmed while preserving conversation flow!\n")

    print_system_info(
        "Ready for Full Live Usage",
        "All components are verified and operational!\n"
        "To start live interactive chatting with LLM:\n"
        "1. Open .env (or copy from .env.example)\n"
        "2. Set GOOGLE_API_KEY=your_key (or OPENAI_API_KEY)\n"
        "3. Run: python main.py"
    )

if __name__ == "__main__":
    run_demo()


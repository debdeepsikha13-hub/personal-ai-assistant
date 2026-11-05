"""
LangGraph StateGraph Definition & Compilation.
==============================================
Assembles the model, tools, memory, and routing into a compiled execution graph.

WHY THIS FOLDER MATTERS:
- Modify this file if you want to alter the agent's reasoning loop (e.g., adding a
  reflection step, plan-and-solve node, or human-in-the-loop approval step).
- Everything here connects modularly to `llm/`, `tools/`, and `memory/`.
"""

from typing import List, Dict, Any
from langchain_core.messages import SystemMessage, BaseMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from core.state import AgentState
from prompts.system_prompts import build_system_prompt
from memory.context_manager import ContextManager
from memory.user_profile_store import get_user_store
from memory.checkpointer import get_checkpointer
from config.settings import get_settings


def create_agent_graph(
    model: BaseChatModel,
    tools: List[BaseTool],
    context_manager: ContextManager
):
    """
    Constructs and compiles the full agent StateGraph.

    Architecture Flow:
      [START] 
         │
         ▼
      [agent_node] ◄────────┐
         │                  │
   (tool calls?)            │
     ├─ Yes ──► [tools_node]┘
     └─ No ───► [END]

    Args:
        model: Model-agnostic LLM instance (Gemini, OpenAI, Claude, Ollama).
        tools: List of registered tools.
        context_manager: Trims and manages conversation token windows.

    Returns:
        CompiledStateGraph: The ready-to-run compiled graph.
    """
    cfg = get_settings()
    user_store = get_user_store()
    model_with_tools = model.bind_tools(tools)
    tool_node = ToolNode(tools)

    def agent_node(state: AgentState) -> Dict[str, Any]:
        """Core reasoning node: prepares context and calls LLM."""
        # 1. Fetch persistent user facts
        current_facts = user_store.get_all_facts()
        user_name = current_facts.get("user_name", cfg.DEFAULT_USER_NAME)

        # 2. Build personalized system prompt
        sys_prompt_text = build_system_prompt(
            agent_name=cfg.AGENT_NAME,
            user_name=user_name,
            user_facts=current_facts
        )
        system_msg = SystemMessage(content=sys_prompt_text)

        # 3. Context window management (trimming if history is too long)
        raw_messages = state["messages"]
        trimmed_messages = context_manager.optimize_messages(raw_messages)

        # 4. Invoke LLM with system message + conversation history
        # If tools have just executed (last message is a tool response), invoke base model
        # directly to synthesize the final answer in 1 step, preventing slow infinite search loops.
        has_tool_output = len(trimmed_messages) > 0 and getattr(trimmed_messages[-1], "type", "") == "tool"
        full_conversation = [system_msg] + trimmed_messages

        if has_tool_output:
            response = model.invoke(full_conversation)
        else:
            response = model_with_tools.invoke(full_conversation)

        return {
            "messages": [response],
            "user_facts": current_facts
        }

    # Initialize the graph with AgentState
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)

    # Add edges
    workflow.add_edge(START, "agent")
    
    # Conditional routing: if LLM decided to call tools, go to tools; otherwise finish
    workflow.add_conditional_edges(
        "agent",
        tools_condition,
        {
            "tools": "tools",
            END: END
        }
    )
    # After executing tools, return to agent to generate the final answer
    workflow.add_edge("tools", "agent")

    # Compile with memory checkpointer
    checkpointer = get_checkpointer()
    compiled_app = workflow.compile(checkpointer=checkpointer)

    return compiled_app


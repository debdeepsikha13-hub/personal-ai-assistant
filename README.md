# 🐺 Wolf: Personal AI Assistant with LangGraph & Multi-MCP

[![Python](https://img.shields.io/badge/Python-3.14-blue.svg)](https://www.python.org/)
[![LangChain](https://img.shields.io/badge/LangChain-v0.3-emerald.svg)](https://www.langchain.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-v0.2-purple.svg)](https://langchain-ai.github.io/langgraph/)
[![FastMCP](https://img.shields.io/badge/MCP-FastMCP_Standard-orange.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A scalable, model-agnostic personal AI assistant named **Wolf**, built with **LangGraph** and Anthropic's **Model Context Protocol (MCP)**. Features a decoupled architecture where components (Tools, MCP Servers, Memory, Prompts, LLMs) are isolated in dedicated directories—**modifications never touch `main.py`**.

Includes both an interactive **Terminal CLI** and a modern **Web Interface** (with a sweet girl robot avatar, dark-studio aesthetic, and collapsible tool inspection pills).

---

## 🌟 Key Architecture Highlights

| Layer | Implementation | Purpose & Where It Lives |
| :--- | :--- | :--- |
| **Multi-MCP Servers** | FastMCP stdio Microservices | 4 standalone tool servers (Hardware, Math, GitHub, Web Search) in [`mcp_service/servers/`](mcp_service/servers/) |
| **Model Agnostic** | Factory Pattern (`BaseChatModel`) | Hot-swap Gemini, OpenAI, Claude, or Ollama in [`.env`](.env) via [`llm/factory.py`](llm/factory.py) |
| **Short-Term Memory** | LangGraph Thread Checkpointing | Preserves multi-turn conversational context in [`memory/checkpointer.py`](memory/checkpointer.py) |
| **Long-Term Memory** | Persistent Profile Store | Remembers user facts across server restarts in [`data/user_profile.json`](data/user_profile.json) |
| **Context Management** | `trim_messages` Optimization | Auto-trims token windows to prevent context overflow in [`memory/context_manager.py`](memory/context_manager.py) |
| **Native Tools** | LangChain `@tool` Decorators | Live weather, safe calculator, notes in [`tools/`](tools/) |
| **Stateful Graph** | LangGraph `StateGraph` | Cyclic reasoning and tool execution loop in [`core/graph.py`](core/graph.py) |
| **Web UI** | Starlette & Glassmorphism HTML | Interactive UI with collapsible tool execution details in [`frontend/`](frontend/) |

---

## 🔌 4 Connected MCP Microservices

1. **GitHub Read-Only MCP Server** (`mcp_service/servers/github_server.py`)
   * `list_repositories`: Inspects repositories with stars, forks, visibility, and descriptions.
   * `list_issues`: Inspects open/closed issues for any repository (`owner/repo`).
   * *Security*: Strictly read-only; cannot push commits or modify code.
2. **Web Search & News MCP Server** (`mcp_service/servers/search_server.py`)
   * `search_web`: Fast, unblocked web query retrieval with links.
   * `search_news`: Live news headlines and article sources.
3. **System Diagnostics MCP Server** (`mcp_service/servers/system_server.py`)
   * `get_system_specs`: Operating system details, CPU architecture, RAM, and machine name.
   * `get_disk_usage`: Total, used, and free storage for host drives (e.g. `C:\`).
4. **Advanced Math & Stats MCP Server** (`mcp_service/servers/math_server.py`)
   * `calculate_statistics`: Mean, median, standard deviation, min, max, and sum.
   * `is_prime` & `calculate_factorial`: Number theory calculations.

---

## 📁 Project Directory Structure

```text
agent/
├── app.py                         # Web Application server launcher
├── main.py                        # Terminal CLI interactive launcher
├── .env.example                   # Environment configuration template
├── requirements.txt               # Dependencies
│
├── config/                        # Settings & MCP Server registry
│   ├── settings.py                # Pydantic Settings
│   └── mcp_servers.json           # Declarative MCP server configurations
│
├── core/                          # LangGraph core orchestration
│   ├── state.py                   # AgentState TypedDict schema
│   ├── graph.py                   # StateGraph (Reasoning -> ToolNode -> Synthesizer)
│   └── agent.py                   # PersonalAssistant facade
│
├── tools/                         # Native LangChain tools
│   ├── weather_tool.py            # Live Kolkata & global weather API
│   ├── calculator_tool.py         # Safe AST math parser
│   ├── notes_tool.py              # Local text note creator & reader
│   └── memory_tool.py             # Semantic user fact storer
│
├── mcp_service/                   # Model Context Protocol layer
│   ├── config.py                  # JSON loader for MCP configurations
│   ├── manager.py                 # MultiServerMCPClient thread-safe wrapper
│   └── servers/                   # FastMCP independent microservices
│       ├── github_server.py       # Read-only GitHub repos & issues
│       ├── search_server.py       # Live internet search & news
│       ├── system_server.py       # Host hardware & disk diagnostics
│       └── math_server.py         # Advanced statistics & primes
│
├── memory/                        # Checkpointing & Context management
│   ├── checkpointer.py            # Multi-turn conversation checkpointer
│   ├── context_manager.py         # Window trimmer
│   └── user_profile_store.py      # Permanent fact storage
│
├── frontend/                      # Web user interface
│   ├── index.html                 # Glassmorphism dark studio UI
│   └── app.py                     # Starlette REST endpoints
│
└── tests/                         # Automated unit tests
    └── test_agent.py              # Layer-by-layer test suite
```

---

## 🚀 Quickstart Guide

### 1. Clone & Set Up Virtual Environment

```bash
git clone https://github.com/debdeepsikha13-hub/personal-ai-assistant.git
cd personal-ai-assistant

python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment (`.env`)

Copy `.env.example` to `.env` and insert your API keys:

```bash
cp .env.example .env
```

```env
MODEL_PROVIDER=gemini
MODEL_NAME=gemini-flash-lite-latest
GOOGLE_API_KEY=your_gemini_api_key

# Optional for GitHub MCP Server:
GITHUB_USERNAME=your_username
GITHUB_TOKEN=your_personal_access_token
```

### 3. Run the Web Application

```bash
python app.py
```
Open **`http://127.0.0.1:8000`** in your browser.

### 4. Run in Terminal (CLI Mode)

```bash
python main.py
```

---

## 🧪 Running Unit Tests

Verify all components in isolation:

```bash
python tests/test_agent.py
```

---

## 📜 License

MIT License. Free to use, adapt, and build upon.

"""
Personal AI Assistant Entry Point.
=================================
This is the lightweight entry point for running the assistant in terminal mode.

WHY THIS ARCHITECTURE IS SPECIAL:
- Notice how short and clean this file is (less than 70 lines).
- If you ever need to rectify or enhance anything:
    - Change/Add Tools:       modify 'tools/'
    - Change Model Provider:  modify '.env' or 'llm/factory.py'
    - Modify Memory Storage:  modify 'memory/'
    - Change Agent Prompts:   modify 'prompts/system_prompts.py'
    - Change Workflow Logic:  modify 'core/graph.py'
  You NEVER need to break or touch `main.py`!
"""

import sys
from config.settings import get_settings
from core.agent import PersonalAssistant
from utils.formatting import (
    print_banner,
    print_agent_reply,
    print_user_prompt,
    print_system_info,
    print_tools_table
)


def run_cli():
    """Main interactive loop for the Personal AI Assistant."""
    settings = get_settings()

    # Display welcome banner
    print_banner(
        agent_name=settings.AGENT_NAME,
        model_provider=settings.MODEL_PROVIDER,
        model_name=settings.MODEL_NAME
    )

    try:
        # Initialize the assistant
        assistant = PersonalAssistant()
    except Exception as e:
        print_system_info(
            "Initialization Error",
            f"Failed to start {settings.AGENT_NAME}:\n{str(e)}\n\n"
            f"Tip: Check your .env file to ensure the API key for '{settings.MODEL_PROVIDER}' is set,\n"
            f"or switch MODEL_PROVIDER to 'ollama' in .env"
        )
        sys.exit(1)

    user_name = settings.DEFAULT_USER_NAME

    # Interactive chat loop
    while True:
        try:
            user_input = print_user_prompt(user_name).strip()

            if not user_input:
                continue

            # Command: exit / quit
            if user_input.lower() in ["exit", "quit", "q", "bye"]:
                print(f"\n👋 Goodbye! Have a productive day ahead.")
                break

            # Command: inspect permanent memory
            if user_input.lower() in ["memory", "facts"]:
                facts = assistant.get_user_facts()
                facts_str = "\n".join([f"• {k}: {v}" for k, v in facts.items()]) or "No facts remembered yet."
                print_system_info("🧠 Long-Term Memory (User Profile)", facts_str)
                continue

            # Command: list active tools
            if user_input.lower() in ["tools", "help"]:
                print_tools_table(assistant.tools)
                continue

            # Process conversational turn through the Agent Graph
            response = assistant.chat(user_input)
            print_agent_reply(settings.AGENT_NAME, response)

        except KeyboardInterrupt:
            print(f"\n👋 Session interrupted. Goodbye!")
            break
        except Exception as e:
            print_system_info("Runtime Error", f"An error occurred while processing: {str(e)}")


if __name__ == "__main__":
    run_cli()


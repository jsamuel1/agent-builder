#!/usr/bin/env python3
"""
Strands - A minimal CLI interface for Strands
"""

import argparse
import base64
import logging
import os
import uuid

# Strands
from strands import Agent

# Strands tools
from strands_tools import (
    agent_graph,
    calculator,
    editor,
    environment,
    file_read,
    file_write,
    generate_image,
    http_request,
    image_reader,
    journal,
    load_tool,
    memory,
    nova_reels,
    python_repl,
    retrieve,
    shell,
    slack,
    speak,
    stop,
    swarm,
    think,
    use_aws,
    use_llm,
    workflow,
)
from strands_tools.utils.user_input import get_user_input

from strands_agents_builder.handlers.callback_handler import callback_handler
from strands_agents_builder.utils import model_utils
from strands_agents_builder.utils.kb_utils import load_system_prompt, store_conversation_in_kb
from strands_agents_builder.utils.welcome_utils import render_goodbye_message, render_welcome_message

# Custom tools, handlers, utils
from tools import (
    store_in_kb,
    strand,
    welcome,
)

# Get keys for your project from the project settings page: https://cloud.langfuse.com
# os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-lf-..."
# os.environ["LANGFUSE_SECRET_KEY"] = "sk-lf-..."
# os.environ["LANGFUSE_HOST"] = "https://cloud.langfuse.com" # 🇪🇺 EU region (default)
# os.environ["LANGFUSE_HOST"] = "https://us.cloud.langfuse.com" # 🇺🇸 US region

otel_host = os.environ.get("LANGFUSE_HOST")

if otel_host:
    # Set up endpoint for OpenTelemetry
    otel_endpoint = str(os.environ.get("LANGFUSE_HOST")) + "/api/public/otel/v1/traces"

    # Create authentication token for OpenTelemetry
    auth_token = base64.b64encode(
        f"{os.environ.get('LANGFUSE_PUBLIC_KEY')}:{os.environ.get('LANGFUSE_SECRET_KEY')}".encode()
    ).decode()
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = otel_endpoint
    os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {auth_token}"

os.environ["STRANDS_TOOL_CONSOLE_MODE"] = "enabled"


# Enabling debugger (will be activated if --debug flag is passed)
def setup_debug_logging():
    # Enables Strands debug log level
    logging.getLogger("strands").setLevel(logging.DEBUG)

    # Sets the logging format and streams logs to stderr
    logging.basicConfig(format="%(levelname)s | %(name)s | %(message)s", handlers=[logging.StreamHandler()])


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Strands - A minimal CLI interface for Strands")
    parser.add_argument("query", nargs="*", help="Query to process")
    parser.add_argument(
        "--kb",
        "--knowledge-base",
        dest="knowledge_base_id",
        help="Knowledge base ID to use for retrievals",
    )
    parser.add_argument(
        "--model-provider",
        type=model_utils.load_path,
        default="bedrock",
        help="Model provider to use for inference",
    )
    parser.add_argument(
        "--model-config",
        type=model_utils.load_config,
        default="{}",
        help="Model config as JSON string or path",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    # Setup debug logging if --debug flag is provided
    if args.debug:
        setup_debug_logging()

    # Get knowledge_base_id from args or environment variable
    knowledge_base_id = args.knowledge_base_id or os.getenv("STRANDS_KNOWLEDGE_BASE_ID")

    model = model_utils.load_model(args.model_provider, args.model_config)

    # Load system prompt
    system_prompt = load_system_prompt()

    tools = [
        memory,
        file_read,
        file_write,
        shell,
        editor,
        http_request,
        python_repl,
        calculator,
        retrieve,
        use_aws,
        load_tool,
        environment,
        use_llm,
        think,
        load_tool,
        journal,
        image_reader,
        generate_image,
        nova_reels,
        agent_graph,
        swarm,
        workflow,
        slack,
        stop,
        speak,
        # Strands tools
        store_in_kb,
        strand,
        welcome,
    ]

    # Generate a unique session ID using UUID
    session_id = str(uuid.uuid4())

    agent = Agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        callback_handler=callback_handler,
        trace_attributes={
            "session.id": session_id,  # Use UUID for unique session tracking
            "user.id": "agent-builder@strandsagents.com",
            "langfuse.tags": [
                "Strands-Agents-Builder",
            ],
        },
    )

    logging.debug("Agent initialized with %d tools", len(tools))

    # Process query or enter interactive mode
    if args.query:
        query = " ".join(args.query)
        logging.debug("Processing command line query: %s", query)
        # Use retrieve if knowledge_base_id is defined
        if knowledge_base_id:
            logging.debug("Using knowledge base for retrieval: %s", knowledge_base_id)
            agent.tool.retrieve(text=query, knowledgeBaseId=knowledge_base_id)

        agent(query)

        if knowledge_base_id:
            # Store conversation in knowledge base
            store_conversation_in_kb(agent, query, knowledge_base_id)
    else:
        # Display welcome text at startup
        logging.debug("Starting interactive mode")
        welcome_result = agent.tool.welcome(action="view", record_direct_tool_call=False)
        welcome_text = ""
        if welcome_result["status"] == "success":
            welcome_text = welcome_result["content"][0]["text"]
            render_welcome_message(welcome_text)
        while True:
            try:
                user_input = get_user_input("\n~ ")
                if user_input.lower() in ["exit", "quit"]:
                    render_goodbye_message()
                    break
                if user_input.startswith("!"):
                    shell_command = user_input[1:]  # Remove the ! prefix
                    print(f"$ {shell_command}")

                    try:
                        # Execute shell command directly using the shell tool
                        agent.tool.shell(
                            command=shell_command,
                            user_message_override=user_input,
                            non_interactive_mode=True,
                        )

                        print()  # new line after shell command execution
                    except Exception as e:
                        print(f"Shell command execution error: {str(e)}")
                    continue

                elif user_input.startswith(">"):
                    python_code = user_input[1:].strip()  # Remove the > prefix
                    try:
                        # Execute Python code directly using the python_repl tool
                        agent.tool.python_repl(code=python_code, interactive=False, user_message_override=user_input)

                        print()
                    except Exception as e:
                        print(f"Python execution error: {str(e)}")
                    continue

                if user_input.strip():
                    # Use retrieve if knowledge_base_id is defined
                    if knowledge_base_id:
                        agent.tool.retrieve(text=user_input, knowledgeBaseId=knowledge_base_id)
                    # Read welcome text and add it to the system prompt
                    welcome_result = agent.tool.welcome(action="view", record_direct_tool_call=False)
                    base_system_prompt = load_system_prompt()
                    welcome_text = ""

                    if welcome_result["status"] == "success":
                        welcome_text = welcome_result["content"][0]["text"]

                    # Combine welcome text with base system prompt
                    combined_system_prompt = f"{base_system_prompt}\n\nWelcome Text Reference:\n{welcome_text}"
                    response = agent(user_input, system_prompt=combined_system_prompt)

                    if knowledge_base_id:
                        # Store conversation in knowledge base
                        store_conversation_in_kb(agent, user_input, response, knowledge_base_id)
            except (KeyboardInterrupt, EOFError):
                render_goodbye_message()
                break
            except Exception as e:
                print(f"\nError: {str(e)}")


if __name__ == "__main__":
    main()
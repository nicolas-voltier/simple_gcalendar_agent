#!/usr/bin/env python3
"""
Google Calendar Agent - Uses OpenAI Agents SDK + BasicMCPClient for calendar operations.
This version uses the OpenAI Agents SDK to handle agent orchestration automatically.
"""
from dotenv import load_dotenv
load_dotenv()
import os
import json
import sys
import asyncio
from typing import Dict, Any, List, Callable
from agents import Agent, function_tool, Runner
from llama_index.tools.mcp import BasicMCPClient


# Configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8080/sse")
OPENAI_MODEL = "gpt-5-mini"
OPENAI_REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT", "low")
OPENAI_VERBOSITY = os.getenv("OPENAI_VERBOSITY", "low")

# MCP Client
mcp_client: BasicMCPClient = None

# Store tool wrappers for the agent
agent_tools: List = []


def get_system_instructions() -> str:
    """Generate system instructions for the agent."""
    return """You are managing a Google Calendar for a user. Act according to their latest request.

Your workflow:
1. Analyze the user request and current context
2. Decide which functions to call
3. After execution, you'll receive results
4. Based on results, decide if more actions are needed
5. If more actions are needed, repeat the process
6. If no more actions are needed, return the final result

Always be thorough and ensure the user's request is fully completed."""


async def load_mcp_tools():
    """Load available tools from MCP server and create function tool wrappers."""
    global mcp_client, agent_tools
    
    print("Loading tools from MCP server...")
    print(f"   Connecting to: {MCP_SERVER_URL}")
    
    try:
        # Initialize MCP client
        mcp_client = BasicMCPClient(MCP_SERVER_URL)
        
        # List available tools
        tools_result = await mcp_client.list_tools()
        
        # Extract tools list from result
        if hasattr(tools_result, 'tools'):
            tools_list = tools_result.tools
        elif isinstance(tools_result, list):
            tools_list = tools_result
        else:
            tools_list = list(tools_result) if tools_result else []
        
        # Create function tool wrappers for each MCP tool
        agent_tools = []
        for tool in tools_list:
            try:
                if hasattr(tool, 'metadata'):
                    tool_name = tool.metadata.name
                    tool_desc = tool.metadata.description
                    tool_schema = getattr(tool.metadata, 'parameters', {})
                elif hasattr(tool, 'name'):
                    tool_name = tool.name
                    tool_desc = getattr(tool, 'description', '')
                    tool_schema = getattr(tool, 'parameters', {})
                else:
                    print(f"   Warning: Unknown tool format: {type(tool)}")
                    continue
                
                # Create a wrapper function for this MCP tool using closure
                def make_tool_wrapper(name: str, description: str):
                    """Factory function to create tool wrappers with proper closure."""
                    async def tool_wrapper(**kwargs) -> str:
                        """Execute the MCP tool and return result as string."""
                        try:
                            result = await mcp_client.call_tool(name, kwargs)
                            
                            # Extract content from result
                            if hasattr(result, 'content') and result.content:
                                if isinstance(result.content, list) and len(result.content) > 0:
                                    first_item = result.content[0]
                                    if hasattr(first_item, 'text'):
                                        return first_item.text
                                    return str(first_item)
                                return str(result.content)
                            
                            return str(result)
                        except Exception as e:
                            return f"Error calling {name}: {str(e)}"
                    
                    # Set proper metadata for the wrapper
                    tool_wrapper.__name__ = name
                    tool_wrapper.__doc__ = description
                    return tool_wrapper
                
                # Create and register the tool wrapper
                wrapper_func = make_tool_wrapper(tool_name, tool_desc)
                wrapped_tool = function_tool(wrapper_func)
                agent_tools.append(wrapped_tool)
                
                print(f"   ✓ Loaded tool: {tool_name}")
                
            except Exception as e:
                print(f"   Warning: Failed to parse tool: {e}")
        
        if agent_tools:
            print(f"\n✅ Loaded {len(agent_tools)} tools from MCP server\n")
        else:
            print("⚠️  Warning: No tools loaded from MCP server\n")
            
    except Exception as e:
        print(f"⚠️  Error loading tools from MCP: {e}\n")
        raise


def create_agent() -> Agent:
    """Create and configure the OpenAI Agent with MCP tools."""
    if not agent_tools:
        raise RuntimeError("No tools available. Please load MCP tools first.")
    
    agent = Agent(
        name="Google Calendar Manager",
        instructions=get_system_instructions(),
        tools=agent_tools,
        model=OPENAI_MODEL,
    )
    
    return agent


async def run_agent_async(agent: Agent, user_request: str) -> Any:
    """Run the agent with a user request asynchronously."""
    try:
        runner = Runner(agent)
        result = await runner.run(user_request)
        return result
    except Exception as e:
        print(f"❌ ERROR: Agent execution failed: {e}")
        raise


def run_agent_sync(agent: Agent, user_request: str) -> Any:
    """Synchronous wrapper for running the agent."""
    return Runner.run_sync(agent, user_request)


def print_separator():
    """Print a visual separator between requests."""
    print("\n" + "=" * 70 + "\n")


def print_result(result: Any):
    """Print the agent result in a formatted way."""
    print("✅ RESULT:")
    if hasattr(result, 'final_output'):
        print(f"   {result.final_output}")
    elif hasattr(result, 'output'):
        print(f"   {result.output}")
    elif hasattr(result, 'messages') and result.messages:
        # Print the last message if available
        last_msg = result.messages[-1]
        if hasattr(last_msg, 'content'):
            print(f"   {last_msg.content}")
        else:
            print(f"   {last_msg}")
    else:
        print(f"   {result}")
    print()


def print_error(error_msg: str):
    """Print error message in a formatted way."""
    print(f"❌ ERROR: {error_msg}\n")


async def main_async():
    """Main execution loop (async version)."""
    print("=" * 70)
    print("Google Calendar Agent (Agents SDK Version)")
    print("=" * 70)
    print("Type 'exit' to quit, or press Ctrl+C\n")
    
    # Load tools from MCP server
    await load_mcp_tools()
    
    if not agent_tools:
        print("ERROR: No tools available from MCP server. Exiting.")
        sys.exit(1)
    
    # Create the agent
    agent = create_agent()
    
    try:
        while True:
            try:
                # Get user input
                user_request = input("Please enter your request: ").strip()
                
                # Check for exit command
                if user_request.lower() in ["exit", "quit", "q"]:
                    print("\nGoodbye!")
                    break
                
                if not user_request:
                    print("Please enter a valid request.\n")
                    continue
                
                print_separator()
                
                # Run the agent (using sync version for simplicity)
                try:
                    result = run_agent_sync(agent, user_request)
                    print_result(result)
                except KeyboardInterrupt:
                    print("\n\nInterrupted by user. Goodbye!")
                    break
                except EOFError:
                    print("\n\nGoodbye!")
                    break
            except Exception as e:
                print_error(f"Unexpected error: {e}")
                import traceback
                traceback.print_exc()
                continue  # Continue the loop instead of exiting
    except Exception as e:
        print_error(f"Fatal error: {e}")
        sys.exit(1)


def main():
    """Main execution entry point."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()

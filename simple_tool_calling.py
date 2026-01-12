#!/usr/bin/env python3
"""
Google Calendar Agent - Uses OpenAI + BasicMCPClient for calendar operations.
Simplified version using llama-index's MCP client for protocol handling.
"""
from dotenv import load_dotenv
load_dotenv()
import os
import json
import sys
import asyncio
from typing import Dict, Any
from openai import OpenAI
from llama_index.tools.mcp import BasicMCPClient


# Configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8080/sse")
OPENAI_MODEL = "gpt-5-mini"
OPENAI_REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT", "low")
OPENAI_VERBOSITY = os.getenv("OPENAI_VERBOSITY", "low")

# MCP Client and available tools
mcp_client: BasicMCPClient = None
AVAILABLE_FUNCTIONS = {}



def get_system_prompt() -> str:
    """Generate the system prompt with Task, Context, and Output format."""
    if not AVAILABLE_FUNCTIONS:
        functions_description = "Loading tools from MCP server..."
    else:
        functions_description = "\n".join([
            f"- {name}: {info['description']}"
            for name, info in AVAILABLE_FUNCTIONS.items()
        ])
    
    return f"""## Task

You are managing a google calendar for a user. Act as per his latest request.

## Context

Available calendar functions:
{functions_description}
## Workflow

1. Analyze the user request and current context
2. Decide which functions to call
3. After execution, you'll receive results
4. Based on results, decide if more actions are needed
5. If more actions are needed, repeat the process
6. If no more actions are needed, return the final result

## Output Format

Output shall be a JSON file with below fields:
{{
  "function_calls": [
    {{
      "name": "...",
      "arguments": {{...}}
    }},
    ...
  ],
  "reasoning": "..."
}}

The "function_calls" field should contain a list of function calls to execute. Each function call should have:
- "name": The name of the function (one of: {", ".join(AVAILABLE_FUNCTIONS.keys()) if AVAILABLE_FUNCTIONS else "loading..."})
- "arguments": A dictionary of arguments to pass to the function. Be vigilant using proper types for arguments.

The "reasoning" field should contain a brief explanation of why you selected these functions and arguments."""


def get_openai_client() -> OpenAI:
    """Initialize and return OpenAI client."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable is not set.")
        sys.exit(1)
    return OpenAI(api_key=api_key)


def call_openai(client: OpenAI, user_prompt: str) -> Dict[str, Any]:
    """
    Call OpenAI API to interpret user request and generate function call.
    
    Returns:
        Dictionary with function_calls (list) and reasoning
    """
    user_message = f"User request: {user_prompt}"
    
    try:
        system_prompt = get_system_prompt()
        # print(f"System prompt: {system_prompt}")
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            reasoning={"effort": OPENAI_REASONING_EFFORT},
            text={
                "verbosity": OPENAI_VERBOSITY,
                "format": {"type": "json_object"},
            },
            timeout=60.0
        )

        content = response.output_text
        return json.loads(content)
    
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse OpenAI response as JSON: {e}")
        print(f"Response content: {content}")
        raise
    except Exception as e:
        print(f"ERROR: OpenAI API call failed: {e}")
        raise


async def load_mcp_tools():
    """Load available tools from MCP server using BasicMCPClient."""
    global mcp_client, AVAILABLE_FUNCTIONS
    
    print("Loading tools from MCP server...")
    print(f"   Connecting to: {MCP_SERVER_URL}")
    
    try:
        # Initialize MCP client
        mcp_client = BasicMCPClient(MCP_SERVER_URL)
        
        # List available tools
        # BasicMCPClient.list_tools() returns a ListToolsResult object or list of tools
        tools_result = await mcp_client.list_tools()
        
        #print(f"   Got tools result, type: {type(tools_result)}")
        
        # Extract tools list from result
        # ListToolsResult may have a 'tools' attribute or be iterable
        if hasattr(tools_result, 'tools'):
            print(f"   Got tools result, tools: {tools_result.tools}")
            tools_list = tools_result.tools
        elif isinstance(tools_result, list):
            print(f"   Got tools result, list: {tools_result}")
            tools_list = tools_result
        else:
            print(f"   Got tools result, else: {tools_result}")
            # Try iterating directly
            tools_list = list(tools_result) if tools_result else []
        
        #print(f"   Processing {len(tools_list)} tools")
        
        # Convert to our format
        for tool in tools_list:
            # Tools are FunctionTool objects with name and metadata attributes
            try:
                if hasattr(tool, 'metadata'):
                    # FunctionTool from llama-index
                    tool_name = tool.metadata.name
                    tool_desc = tool.metadata.description
                    AVAILABLE_FUNCTIONS[tool_name] = {
                        "description": tool_desc,
                        "schema": {}
                    }
                elif hasattr(tool, 'name'):
                    # Simple object with name attribute
                    tool_name = tool.name
                    tool_desc = getattr(tool, 'description', '')
                    AVAILABLE_FUNCTIONS[tool_name] = {
                        "description": tool_desc,
                        "schema": {}
                    }
                else:
                    print(f"   Warning: Unknown tool format: {type(tool)}")
            except Exception as e:
                print(f"   Warning: Failed to parse tool: {e}")
        
        # if AVAILABLE_FUNCTIONS:
        #     print(f"✅ Loaded {len(AVAILABLE_FUNCTIONS)} tools from MCP server:")
        #     for name, info in AVAILABLE_FUNCTIONS.items():
        #         print(f"   - {name}: {info['description']}")
        #     print()
        # else:
        #     print("⚠️  Warning: No tools loaded from MCP server\n")
            
    except Exception as e:
        print(f"⚠️  Error loading tools from MCP: {e}\n")


async def call_mcp_tool_async(tool_name: str, arguments: Dict[str, Any]) -> str:
    """
    Call MCP tool using BasicMCPClient.
    
    Args:
        tool_name: Name of the tool to call
        arguments: Dictionary of arguments
        
    Returns:
        Tool result as string
    """
    try:
        result = await mcp_client.call_tool(tool_name, arguments)
        
        # BasicMCPClient returns a result object with content
        if hasattr(result, 'content') and result.content:
            # Content is typically a list of content items
            if isinstance(result.content, list) and len(result.content) > 0:
                first_item = result.content[0]
                if hasattr(first_item, 'text'):
                    return first_item.text
                return str(first_item)
            return str(result.content)
        
        return str(result)
        
    except Exception as e:
        raise RuntimeError(f"Failed to call MCP tool '{tool_name}': {e}")


def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Synchronous wrapper for async MCP tool call."""
    return asyncio.run(call_mcp_tool_async(tool_name, arguments))


def validate_openai_response(response: Dict[str, Any]) -> bool:
    """Validate that OpenAI response contains required fields."""
    required_fields = ["function_calls", "reasoning"]
    for field in required_fields:
        if field not in response:
            print(f"ERROR: OpenAI response missing required field: {field}")
            return False
    
    if not isinstance(response["function_calls"], list):
        print("ERROR: 'function_calls' must be a list")
        return False
    
    if len(response["function_calls"]) == 0:
        # If no function calls, show the AI's reasoning for why it couldn't act
        print("ℹ️  No action to perform.")
        if "reasoning" in response:
            print("🤔 REASONING:")
            print(f"   {response['reasoning']}\n")
        return False
    
    for i, func_call in enumerate(response["function_calls"]):
        if not isinstance(func_call, dict):
            print(f"ERROR: function_calls[{i}] must be a dictionary")
            return False
        
        if "name" not in func_call:
            print(f"ERROR: function_calls[{i}] missing required field: name")
            return False
        
        if "arguments" not in func_call:
            print(f"ERROR: function_calls[{i}] missing required field: arguments")
            return False
        
        if func_call["name"] not in AVAILABLE_FUNCTIONS:
            print(f"ERROR: Invalid function name in function_calls[{i}]: {func_call['name']}")
            return False
        
        if not isinstance(func_call["arguments"], dict):
            print(f"ERROR: function_calls[{i}]['arguments'] must be a dictionary")
            return False
    
    return True

########### Agentic loop
def run_agent_loop(client: OpenAI, user_request: str, max_iterations: int = 5):
    """
    Boucle agentic qui permet à l'agent de voir les résultats et décider des actions suivantes.
    
    Args:
        client: OpenAI client
        user_request: Requête initiale de l'utilisateur
        max_iterations: Nombre maximum d'itérations
        
    Returns:
        List of all results from function executions
    """
    # Pour la première itération, on utilise la requête originale
    current_prompt = user_request
    all_results = []
    conversation_context = []  # Garde trace de ce qui s'est passé
    
    for iteration in range(max_iterations):
        print(f"\n{'='*70}")
        print(f"🔄 ITERATION {iteration + 1}/{max_iterations}")
        print(f"{'='*70}\n")
        
        # Appel à OpenAI avec le prompt courant
        try:
            response = call_openai(client, current_prompt)
        except Exception as e:
            print_error(f"Failed to get response from OpenAI: {e}")
            break
        
        # Valider la réponse
        if not validate_openai_response(response):
            break
        
        function_calls = response["function_calls"]
        reasoning = response["reasoning"]
        
        # Afficher le raisonnement
        print_reasoning(reasoning)
        
        # Si pas d'actions, l'agent a terminé
        if len(function_calls) == 0:
            print("✅ AGENT COMPLETED THE TASK\n")
            break
        
        # Afficher les actions planifiées
        print_action(function_calls)
        
        # Exécuter les fonctions et collecter les résultats
        iteration_results = []
        for func_call in function_calls:
            try:
                result = call_mcp_tool(func_call["name"], func_call["arguments"])
                iteration_results.append({
                    "function": func_call["name"],
                    "arguments": func_call["arguments"],
                    "result": result,
                    "success": True
                })
                all_results.append(iteration_results[-1])
                print_result(result)
            except Exception as e:
                error_msg = str(e)
                iteration_results.append({
                    "function": func_call["name"],
                    "arguments": func_call["arguments"],
                    "error": error_msg,
                    "success": False
                })
                all_results.append(iteration_results[-1])
                print_error(error_msg)
        
        # Ajouter à l'historique contextuel
        conversation_context.append({
            "iteration": iteration + 1,
            "actions": function_calls,
            "results": iteration_results
        })
        
        # Construire le nouveau prompt pour la prochaine itération
        context_summary = "\n\n".join([
            f"Iteration {ctx['iteration']}:\n"
            f"Actions taken: {json.dumps(ctx['actions'], indent=2)}\n"
            f"Results: {json.dumps(ctx['results'], indent=2)}"
            for ctx in conversation_context
        ])
        
        current_prompt = f"""Original user request: {user_request}

Previous actions and results:
{context_summary}

Based on these results, what should be done next to complete the user's request?
If the task is complete, return empty function_calls: []"""
    
    if iteration == max_iterations - 1:
        print(f"\n⚠️  Warning: Reached maximum iterations ({max_iterations})\n")
        
        print_separator()
    
    return all_results

########### Print functions
def print_separator():
    """Print a visual separator between requests."""
    print("\n" + "=" * 70 + "\n")


def print_reasoning(reasoning: str):
    """Print the AI's reasoning in a formatted way."""
    print("🤔 REASONING:")
    print(f"   {reasoning}\n")


def print_action(function_calls: list):
    """Print the action being taken in a formatted way."""
    print("⚙️  ACTION:")
    for i, func_call in enumerate(function_calls):
        if len(function_calls) > 1:
            print(f"   Function Call {i+1}:")
        print(f"   Function: {func_call['name']}")
        print(f"   Arguments: {json.dumps(func_call['arguments'], indent=6)}")
        if i < len(function_calls) - 1:
            print()
    print()


def print_result(result: Any):
    """Print the result from MCP execution in a formatted way."""
    print("✅ RESULT:")
    if isinstance(result, dict):
        print(json.dumps(result, indent=2))
    else:
        print(f"   {result}")
    print()


def print_error(error_msg: str):
    """Print error message in a formatted way."""
    print(f"❌ ERROR: {error_msg}\n")


def main():
    """Main execution loop."""
    print("=" * 70)
    print("Google Calendar Agent (v3 - using BasicMCPClient)")
    print("=" * 70)
    print("Type 'exit' to quit, or press Ctrl+C\n")
    
    # Load tools from MCP server
    asyncio.run(load_mcp_tools())
    
    if not AVAILABLE_FUNCTIONS:
        print("ERROR: No tools available from MCP server. Exiting.")
        sys.exit(1)
    
    client = get_openai_client()
    
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
                
                # Call OpenAI to interpret request
                try:
                    run_agent_loop(client, user_request, max_iterations=5)
                except KeyboardInterrupt:
                    print("\n\nInterrupted by user. Goodbye!")
                    break
                except EOFError:
                    print("\n\nGoodbye!")
                    break
            except Exception as e:
                print_error(f"Unexpected error: {e}")
                continue  # Continue the loop instead of exiting
    except Exception as e:
        print_error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
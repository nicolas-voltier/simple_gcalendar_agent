#!/usr/bin/env python3
"""
Standalone script to test the get_system_prompt() function.
This script demonstrates the function's output in different scenarios.
"""

# Standalone version of the function (copied from simple_tool_calling.py)
# This avoids importing the entire module which has dependencies

# Global variable to simulate AVAILABLE_FUNCTIONS
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


def test_empty_functions():
    """Test the function when AVAILABLE_FUNCTIONS is empty."""
    print("=" * 70)
    print("TEST 1: Empty AVAILABLE_FUNCTIONS")
    print("=" * 70)
    
    # Clear AVAILABLE_FUNCTIONS
    global AVAILABLE_FUNCTIONS
    AVAILABLE_FUNCTIONS.clear()
    
    prompt = get_system_prompt()
    print(prompt)
    
    print("\n")


def test_with_sample_functions():
    """Test the function with sample calendar functions."""
    print("=" * 70)
    print("TEST 2: With Sample AVAILABLE_FUNCTIONS")
    print("=" * 70)
    
    # Set up sample functions
    global AVAILABLE_FUNCTIONS
    AVAILABLE_FUNCTIONS = {
        "create_event": {
            "description": "Create a new calendar event with title, start time, and end time",
            "schema": {}
        },
        "list_events": {
            "description": "List all events in the calendar for a given date range",
            "schema": {}
        },
        "delete_event": {
            "description": "Delete an event by its event ID",
            "schema": {}
        },
        "update_event": {
            "description": "Update an existing event's details",
            "schema": {}
        }
    }
    
    prompt = get_system_prompt()
    print(prompt)
    
    print("\n")


def main():
    """Run all tests."""
    print("\nTesting get_system_prompt() function\n")
    
    # Test with empty functions
    test_empty_functions()
    
    # Test with sample functions
    test_with_sample_functions()
    
    print("=" * 70)
    print("Tests completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()

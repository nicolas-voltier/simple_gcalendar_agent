# Comparison: Standard OpenAI SDK vs OpenAI Agents SDK

This document outlines the key differences between the two implementations of the Google Calendar Agent:
- **Original Implementation**: `simple_tool_calling.py` - Uses standard OpenAI SDK with manual agent loop
- **Agents SDK Implementation**: `agents_sdk_calendar.py` - Uses OpenAI Agents SDK for automatic orchestration

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Key Differences](#key-differences)
3. [Code Structure Comparison](#code-structure-comparison)
4. [Dependencies](#dependencies)
5. [Advantages and Disadvantages](#advantages-and-disadvantages)
6. [Migration Guide](#migration-guide)

---

## Architecture Overview

### Original Implementation (`simple_tool_calling.py`)
- **Approach**: Manual agent orchestration
- **Flow**: 
  1. Load MCP tools into dictionary
  2. Manually call OpenAI Responses API with JSON format
  3. Parse JSON response for function calls
  4. Execute functions manually
  5. Build context for next iteration
  6. Repeat until task complete (max 5 iterations)

### Agents SDK Implementation (`agents_sdk_calendar.py`)
- **Approach**: SDK-managed agent orchestration
- **Flow**:
  1. Load MCP tools and wrap them as `function_tool` decorators
  2. Create `Agent` instance with tools
  3. Use `Runner` to execute agent
  4. SDK handles iteration, context management, and tool calling automatically

---

## Key Differences

### 1. Imports and Dependencies

**Original:**
```python
from openai import OpenAI
from llama_index.tools.mcp import BasicMCPClient
```

**Agents SDK:**
```python
from agents import Agent, function_tool, Runner
from llama_index.tools.mcp import BasicMCPClient
```

### 2. API Usage

**Original:**
- Directly uses `OpenAI` client
- Calls `client.responses.create()` with manual prompt construction
- Requires JSON parsing of responses
- Manual format specification (`format: {"type": "json_object"}`)
- Manual reasoning effort and verbosity configuration

```python
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
```

**Agents SDK:**
- Uses `Agent` class to encapsulate behavior
- Uses `Runner` to execute agent
- Automatic tool calling and response handling
- No manual JSON parsing needed
- SDK handles conversation flow automatically

```python
agent = Agent(
    name="Google Calendar Manager",
    instructions=get_system_instructions(),
    tools=agent_tools,
    model=OPENAI_MODEL,
)

runner = Runner(agent)
result = Runner.run_sync(agent, user_request)
```

### 3. Tool Integration

**Original:**
- Stores tools in a dictionary (`AVAILABLE_FUNCTIONS`)
- Manually validates tool names and arguments
- Manual tool execution with error handling
- Tools described in system prompt as text
- Tools referenced by name as strings

```python
AVAILABLE_FUNCTIONS = {}
# ... load tools into dictionary ...

# Manual execution
result = call_mcp_tool(func_call["name"], func_call["arguments"])
```

**Agents SDK:**
- Wraps MCP tools using `@function_tool` decorator
- SDK automatically handles tool validation and execution
- Tools are first-class objects passed to the agent
- Type-safe tool definitions
- Tools are callable functions

```python
@function_tool
async def tool_wrapper(**kwargs) -> str:
    result = await mcp_client.call_tool(name, kwargs)
    return str(result)

agent_tools.append(function_tool(tool_wrapper))
```

### 4. Agent Loop Management

**Original:**
- **Manual loop implementation** (~100 lines of code)
- Explicit iteration counter (`max_iterations=5`)
- Manual context building for each iteration
- Manual prompt construction with conversation history
- Manual validation of responses
- Manual tracking of conversation context

```python
def run_agent_loop(client: OpenAI, user_request: str, max_iterations: int = 5):
    current_prompt = user_request
    all_results = []
    conversation_context = []
    
    for iteration in range(max_iterations):
        response = call_openai(client, current_prompt)
        # ... validate, execute, build context ...
        current_prompt = f"""Original user request: {user_request}
        Previous actions and results: {context_summary}
        ..."""
```

**Agents SDK:**
- **Automatic loop management** (handled by SDK)
- No explicit iteration management needed
- Automatic context and conversation management
- Built-in retry and error handling
- Simpler code (~5 lines for execution)
- SDK manages conversation state internally

```python
runner = Runner(agent)
result = Runner.run_sync(agent, user_request)
# SDK handles all iterations automatically
```

### 5. Response Handling

**Original:**
- Manual JSON parsing
- Custom validation logic (`validate_openai_response()`)
- Manual extraction of function calls and reasoning
- Manual result aggregation
- Manual error handling at each step

```python
response = json.loads(content)
if not validate_openai_response(response):
    break
function_calls = response["function_calls"]
reasoning = response["reasoning"]
```

**Agents SDK:**
- Automatic response handling
- Built-in result objects with `final_output` or `output` attributes
- No manual parsing needed
- SDK manages intermediate results
- Built-in error handling

```python
result = Runner.run_sync(agent, user_request)
print(result.final_output)  # Direct access to final result
```

### 6. System Prompt / Instructions

**Original:**
- Complex system prompt with JSON format specification
- Includes explicit workflow steps
- Requires function list in prompt
- Must specify output format structure
- Dynamic prompt generation based on available functions

```python
def get_system_prompt() -> str:
    return f"""## Task
    ...
    ## Output Format
    Output shall be a JSON file with below fields:
    {{
      "function_calls": [...],
      "reasoning": "..."
    }}
    ..."""
```

**Agents SDK:**
- Simpler instructions (natural language)
- No format specification needed
- SDK handles tool discovery automatically
- More conversational approach
- Static instructions (no dynamic function list)

```python
def get_system_instructions() -> str:
    return """You are managing a Google Calendar for a user.
    Your workflow:
    1. Analyze the user request...
    ..."""
```

### 7. Error Handling

**Original:**
- Manual error handling at each step
- Custom error messages
- Manual retry logic (if needed)
- Explicit error propagation
- Try-catch blocks around each operation

**Agents SDK:**
- Built-in error handling
- Automatic retries (configurable)
- Standardized error messages
- Better observability
- SDK handles errors gracefully

### 8. Code Complexity

| Metric | Original | Agents SDK |
|--------|----------|------------|
| Total Lines | ~464 | ~200 |
| Agent Loop Code | ~100 lines | ~5 lines |
| Tool Integration | ~60 lines | ~50 lines |
| Response Handling | ~50 lines | ~5 lines |
| Manual Validation | ~40 lines | 0 lines (automatic) |
| Context Management | ~30 lines | 0 lines (automatic) |

**Code Reduction**: ~57% fewer lines of code

---

## Dependencies

### Original Implementation
```txt
openai>=1.0.0
python-dotenv>=1.0.0
httpx>=0.27.0
llama-index-tools-mcp>=0.1.0
```

### Agents SDK Implementation
```txt
openai-agents>=1.0.0  # New dependency
python-dotenv>=1.0.0
httpx>=0.27.0
llama-index-tools-mcp>=0.1.0
```

**Note**: The Agents SDK may have its own dependencies on the OpenAI package. Install with:
```bash
pip install openai-agents
```

---

## Advantages and Disadvantages

### Original Implementation

**Advantages:**
- ✅ Full control over agent loop behavior
- ✅ Customizable iteration logic and max iterations
- ✅ Explicit control over context building
- ✅ No additional dependencies
- ✅ Easier to debug (all logic visible)
- ✅ Can customize JSON response format
- ✅ Fine-grained control over reasoning effort and verbosity
- ✅ Can see intermediate reasoning at each step
- ✅ Full control over conversation history format

**Disadvantages:**
- ❌ More code to maintain (~464 lines)
- ❌ Manual error handling
- ❌ Manual validation logic
- ❌ More prone to bugs
- ❌ Harder to extend
- ❌ Must manually manage conversation state
- ❌ More complex to understand
- ❌ JSON parsing can fail

### Agents SDK Implementation

**Advantages:**
- ✅ Less code (~200 lines, ~57% reduction)
- ✅ Automatic agent orchestration
- ✅ Built-in error handling and retries
- ✅ Better observability and debugging tools
- ✅ Easier to extend with new tools
- ✅ Industry-standard approach
- ✅ Automatic conversation management
- ✅ Better integration with OpenAI features
- ✅ Type-safe tool definitions
- ✅ No JSON parsing needed
- ✅ Cleaner, more maintainable code

**Disadvantages:**
- ❌ Less control over loop behavior
- ❌ Additional dependency (`openai-agents`)
- ❌ May have less control over specific API parameters (reasoning effort, verbosity)
- ❌ Learning curve for SDK API
- ❌ Potential abstraction overhead
- ❌ Less visibility into intermediate steps
- ❌ May not support all OpenAI API features directly

---

## Migration Guide

If you want to migrate from the original implementation to the Agents SDK version:

### Step 1: Install Dependencies
```bash
pip install openai-agents
```

### Step 2: Update Imports
Replace:
```python
from openai import OpenAI
```
With:
```python
from agents import Agent, function_tool, Runner
```

### Step 3: Wrap MCP Tools
Convert your tool loading to use `@function_tool`:
```python
# Instead of storing in dictionary
def make_tool_wrapper(name: str, description: str):
    async def tool_wrapper(**kwargs):
        return await mcp_client.call_tool(name, kwargs)
    tool_wrapper.__name__ = name
    tool_wrapper.__doc__ = description
    return tool_wrapper

wrapped_tool = function_tool(make_tool_wrapper(tool_name, tool_desc))
agent_tools.append(wrapped_tool)
```

### Step 4: Create Agent
Replace manual client usage with Agent:
```python
# Instead of:
client = OpenAI(api_key=api_key)

# Use:
agent = Agent(
    name="Google Calendar Manager",
    instructions=get_system_instructions(),
    tools=agent_tools,
    model=OPENAI_MODEL,
)
```

### Step 5: Replace Agent Loop
Replace `run_agent_loop()` with:
```python
# Instead of:
run_agent_loop(client, user_request, max_iterations=5)

# Use:
result = Runner.run_sync(agent, user_request)
```

### Step 6: Simplify Response Handling
Remove JSON parsing and validation:
```python
# Instead of:
response = json.loads(content)
if not validate_openai_response(response):
    break
function_calls = response["function_calls"]

# Use:
result = Runner.run_sync(agent, user_request)
print(result.final_output)
```

### Step 7: Remove Manual Validation
Delete the `validate_openai_response()` function - SDK handles this automatically.

### Step 8: Simplify System Prompt
Convert complex JSON-format system prompt to simple instructions - SDK handles tool discovery.

---

## Example Usage Comparison

### Original Implementation
```python
# Load tools
asyncio.run(load_mcp_tools())

# Create client
client = get_openai_client()

# Run agent loop
run_agent_loop(client, "Schedule a meeting tomorrow at 2pm", max_iterations=5)
```

### Agents SDK Implementation
```python
# Load tools
await load_mcp_tools()

# Create agent
agent = create_agent()

# Run agent
result = Runner.run_sync(agent, "Schedule a meeting tomorrow at 2pm")
print(result.final_output)
```

---

## Conclusion

The **Agents SDK implementation** offers significant advantages in terms of code simplicity, maintainability, and built-in features. However, the **original implementation** provides more fine-grained control for custom use cases.

**Choose Agents SDK if:**
- You want less code to maintain
- You need standard agent behavior
- You want built-in error handling and observability
- You're building production applications
- You want to follow industry best practices
- You want easier tool integration

**Choose Original if:**
- You need custom iteration logic
- You want full control over API parameters (reasoning effort, verbosity)
- You have specific JSON format requirements
- You want to minimize dependencies
- You need to see intermediate reasoning at each step
- You want complete control over conversation history format

Both implementations achieve the same goal of managing Google Calendar through MCP tools, but with different levels of abstraction and control. The Agents SDK version is recommended for most use cases due to its simplicity and maintainability.

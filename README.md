# simple_gcalendar_agent
Simple google calendar agent using Openai SDK for discovery of agentic AI

# Actions to setup
1. Create a file named `.env` in the root of this project.

2. Inside `.env`, add your OpenAI API key like so:

```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Replace `sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` with your actual OpenAI API key.


3. (Optional, but recommended) Create and activate a Python virtual environment:
<details>
<summary>Show instructions</summary>

```bash
python3 -m venv .venv
source .venv/bin/activate    # On macOS/Linux

# or, on Windows:
.venv\Scripts\activate
```
</details>

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Configure the MCP server port

By default, the app talks to MCP at `http://127.0.0.1:58426`.  
To change the port, set the `MCP_SERVER_URL` in **simple_tool_calling.py**
```
MCP_SERVER_URL=http://127.0.0.1:12345
```

Update the port number as needed to match your MCP server setup.



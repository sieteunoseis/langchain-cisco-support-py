# LangChain + OpenRouter + Cisco MCP (Python)

A Python implementation of a LangChain agent that integrates with OpenRouter and the Cisco Support MCP (Model Context Protocol) server. This enables AI agents to query Cisco support APIs for bug information, cases, end-of-life data, and security vulnerabilities.

This is a Python port of the TypeScript version available at [sieteunoseis/langchain-cisco-support-ts](https://github.com/sieteunoseis/langchain-cisco-support-ts).

## Features

- **LangChain Agent Integration**: Uses OpenRouter as the LLM provider with support for multiple AI models
- **MCP Server Bridge**: Connects to Cisco Support MCP server to access structured API tools
- **Multi-API Support**: Provides access to 8 different Cisco APIs:
  - Bug API (14 tools) - Search for product bugs and vulnerabilities
  - Case API (4 tools) - Manage support cases
  - EoX API (4 tools) - End-of-life information
  - PSIRT API (8 tools) - Security vulnerability data
  - Product API - Product information
  - Software API - Software details
  - Serial API - Serial number lookups
  - RMA API - Return merchandise authorization
- **Flexible Model Selection**: Switch between various OpenRouter-supported models (Claude, GPT-4, Gemini, etc.)
- **Customizable API Endpoints**: Enable/disable specific Cisco APIs as needed

## Prerequisites

- Python 3.10 or higher
- A running MCP server instance in HTTP mode (see [MCP Server Setup](#mcp-server-setup))
- API credentials from:
  - [OpenRouter](https://openrouter.ai/) - For AI model access
  - [Cisco API Console](https://apiconsole.cisco.com/) - For Cisco API access

## Installation

1. Clone or download this repository

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

Or using Poetry:
```bash
poetry install
```

3. Create a `.env` file in the project root with your credentials:
```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
CISCO_CLIENT_ID=your_cisco_client_id_here
CISCO_CLIENT_SECRET=your_cisco_client_secret_here
MCP_SERVER_URL=http://localhost:3000/mcp
MCP_AUTH_TOKEN=your_mcp_auth_token_here
```

Note: `MCP_AUTH_TOKEN` is optional and only needed if your MCP server requires authentication.

## MCP Server Setup

This client requires a running MCP server instance in HTTP mode. You have several options:

### Option 1: Run the mcp-cisco-support server in HTTP mode

If you have the [mcp-cisco-support](https://github.com/sieteunoseis/mcp-cisco-support) server, you can run it in HTTP mode:

```bash
# Set environment variables
export CISCO_CLIENT_ID=your_cisco_client_id_here
export CISCO_CLIENT_SECRET=your_cisco_client_secret_here
export SUPPORT_API=all

# Run the server in HTTP mode on port 3000
mcp-cisco-support --http --port 3000
```

### Option 2: Use Docker

```bash
docker run -p 3000:3000 \
  -e CISCO_CLIENT_ID=your_cisco_client_id \
  -e CISCO_CLIENT_SECRET=your_cisco_client_secret \
  -e SUPPORT_API=all \
  mcp-cisco-support:latest --http --port 3000
```

### Option 3: Custom MCP Server URL

If your MCP server is running elsewhere, update the `MCP_SERVER_URL` in your `.env` file:

```env
MCP_SERVER_URL=http://your-server:port/mcp
```

## Usage

Run the agent:
```bash
python main.py
```

Or with Poetry:
```bash
poetry run python main.py
```

## Example Queries

The agent can handle natural language queries about Cisco products and support information:

- "Search for recent bugs related to 'crash' in Cisco products"
- "Find high-severity bugs modified in the last 30 days"
- "Search for bugs affecting Catalyst 9200 series"
- "Show me end-of-life information for product XYZ"
- "What security vulnerabilities affect IOS-XE version 17.3?"

## Customization

### Changing the AI Model

Edit [main.py:159](main.py#L159) to use a different model from OpenRouter:

```python
model = ChatOpenAI(
    model="anthropic/claude-3.5-sonnet",  # Change this
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)
```

Available models include:
- `anthropic/claude-3.5-sonnet`
- `openai/gpt-4-turbo`
- `google/gemini-pro-1.5`
- `meta-llama/llama-3.1-70b-instruct`
- And many more from [OpenRouter's model list](https://openrouter.ai/models)

### Selecting Specific APIs

To only load specific Cisco APIs instead of all of them, configure the `SUPPORT_API` environment variable on your MCP server when starting it:

```bash
export SUPPORT_API="bug,psirt"  # Only load Bug and PSIRT APIs
mcp-cisco-support --http --port 3000
```

Available API options: `bug`, `case`, `eox`, `psirt`, `product`, `software`, `serial`, `rma`, or `all`

### Modifying Queries

Edit the `queries` list in [main.py:185-189](main.py#L185-L189) to test different questions:

```python
queries = [
    "Your custom query here",
    "Another query",
]
```

## Architecture

The application follows a three-layer architecture:

1. **LangChain Agent** - Orchestrates the AI interaction and tool calling
2. **MCP Client (HTTP)** - Bridges communication with the Cisco Support MCP server via HTTP/SSE
3. **MCP Server** - Provides tools and access to Cisco Support APIs
4. **Cisco Support APIs** - Provides access to bug, case, security, and product data

```
┌─────────────────┐
│  LangChain      │
│  Agent          │
│  (Python)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  MCP Client     │
│  (Python/HTTP)  │
└────────┬────────┘
         │ HTTP/SSE
         ▼
┌─────────────────┐
│  MCP Server     │
│  (Any Language) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Cisco Support  │
│  APIs           │
└─────────────────┘
```

## Project Structure

```
.
├── main.py              # Main agent implementation
├── requirements.txt     # Python dependencies
├── pyproject.toml       # Poetry configuration
├── .env                 # Environment variables (not committed)
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## Key Functions

- `initialize_mcp_client()` - Sets up the MCP client connection to Cisco Support
- `create_pydantic_model_from_schema()` - Converts JSON schemas to Pydantic models
- `create_langchain_tools_from_mcp()` - Converts MCP tools to LangChain-compatible tools
- `main()` - Main execution flow

## Troubleshooting

### "Module not found" errors
Make sure all dependencies are installed:
```bash
pip install -r requirements.txt
```

### MCP connection errors
Ensure your MCP server is running and accessible at the configured URL. Test the connection:
```bash
curl http://localhost:3000/sse
```

If your server requires authentication, make sure to include the proper headers or query parameters.

### Authentication errors
Verify your Cisco credentials are correct at the [Cisco API Console](https://apiconsole.cisco.com/)

### OpenRouter API errors
Check your OpenRouter API key at [OpenRouter Settings](https://openrouter.ai/settings)

## License

MIT

## Related Projects

- [TypeScript version](https://github.com/sieteunoseis/langchain-cisco-support-ts) - Original TypeScript implementation
- [mcp-cisco-support](https://github.com/sieteunoseis/mcp-cisco-support) - The underlying MCP server
- [LangChain Python](https://python.langchain.com/) - LangChain for Python
- [OpenRouter](https://openrouter.ai/) - Unified API for AI models

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

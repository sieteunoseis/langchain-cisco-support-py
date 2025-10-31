"""
LangChain agent with OpenRouter and Cisco MCP integration.

This module demonstrates integration of LangChain with OpenRouter and the Cisco Support
MCP (Model Context Protocol) server, enabling AI agents to query Cisco support APIs
for bug information, cases, end-of-life data, and security vulnerabilities.
"""

import os
import json
import asyncio
from typing import Any, Dict, List
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# Load environment variables
load_dotenv()


async def initialize_mcp_client(server_url: str, auth_token: str = "") -> ClientSession:
    """
    Initialize the MCP client for Cisco Support via HTTP.

    Args:
        server_url: URL of the MCP server (e.g., "http://localhost:3000/mcp")
        auth_token: Optional authentication token

    Returns:
        ClientSession: Connected MCP client session
    """
    print(f"Initializing MCP client for Cisco Support at {server_url}...")

    # Create headers with authentication if token provided
    headers = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    # Create and return the streamable HTTP client
    async with streamablehttp_client(server_url, headers=headers) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return session


def create_pydantic_model_from_schema(schema: Dict[str, Any], model_name: str) -> type[BaseModel]:
    """
    Create a Pydantic model from a JSON schema.

    Args:
        schema: JSON schema dictionary
        model_name: Name for the Pydantic model

    Returns:
        Pydantic model class
    """
    if not schema or "properties" not in schema:
        return create_model(model_name)

    fields = {}
    properties = schema.get("properties", {})
    required = schema.get("required", [])

    for field_name, field_info in properties.items():
        field_type = str  # Default to string
        field_description = field_info.get("description", "")

        # Determine the field type
        if field_info.get("type") == "integer":
            field_type = int
        elif field_info.get("type") == "number":
            field_type = float
        elif field_info.get("type") == "boolean":
            field_type = bool
        elif field_info.get("type") == "array":
            field_type = List[Any]
        elif field_info.get("type") == "object":
            field_type = Dict[str, Any]

        # Create field with or without default based on required status
        if field_name in required:
            fields[field_name] = (field_type, Field(description=field_description))
        else:
            fields[field_name] = (field_type, Field(default=None, description=field_description))

    return create_model(model_name, **fields)


async def create_langchain_tools_from_mcp(session: ClientSession) -> List[StructuredTool]:
    """
    Convert MCP tools to LangChain tools.

    Args:
        session: MCP client session

    Returns:
        List of LangChain StructuredTool objects
    """
    print("Converting MCP tools to LangChain tools...")

    # List all available tools from the MCP server
    tools_list = await session.list_tools()

    langchain_tools = []

    for mcp_tool in tools_list.tools:
        # Create a closure to capture the tool name and session
        def make_tool_func(tool_name: str, tool_session: ClientSession):
            async def tool_func(**kwargs: Any) -> str:
                """Execute the MCP tool with given arguments."""
                try:
                    result = await tool_session.call_tool(tool_name, arguments=kwargs)

                    # Extract text content from the MCP response
                    if result.content:
                        for content_item in result.content:
                            if hasattr(content_item, 'type') and content_item.type == "text":
                                return content_item.text
                        # If no text content found, return JSON representation
                        return json.dumps([c.model_dump() for c in result.content], indent=2)

                    return "No response from tool"
                except Exception as e:
                    return f"Error executing tool: {str(e)}"

            return tool_func

        # Create Pydantic model for the tool's input schema
        input_schema = mcp_tool.inputSchema if hasattr(mcp_tool, 'inputSchema') else {}
        args_schema = create_pydantic_model_from_schema(
            input_schema,
            f"{mcp_tool.name.replace('-', '_').title()}Input"
        )

        # Create the LangChain StructuredTool
        tool_func = make_tool_func(mcp_tool.name, session)

        langchain_tool = StructuredTool(
            name=mcp_tool.name,
            description=mcp_tool.description or f"MCP tool: {mcp_tool.name}",
            func=lambda *args, **kwargs: asyncio.run(tool_func(**kwargs)),
            coroutine=tool_func,
            args_schema=args_schema,
        )

        langchain_tools.append(langchain_tool)

    return langchain_tools


async def main():
    """Main execution function."""
    try:
        # Get MCP server URL from environment variable or use default
        mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:3000/mcp")
        mcp_auth_token = os.getenv("MCP_AUTH_TOKEN", "")

        print(f"Connecting to MCP server at {mcp_server_url}...")

        # Create headers with authentication if token provided
        headers = {}
        if mcp_auth_token:
            headers["Authorization"] = f"Bearer {mcp_auth_token}"

        # Initialize MCP client via HTTP
        async with streamablehttp_client(mcp_server_url, headers=headers) as (read, write, get_session_id):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Convert MCP tools to LangChain tools
                cisco_tools = await create_langchain_tools_from_mcp(session)
                print(f"Loaded {len(cisco_tools)} Cisco Support tools")

                # Create the OpenAI model configured for OpenRouter
                model = ChatOpenAI(
                    model="anthropic/claude-3.5-sonnet",
                    api_key=os.getenv("OPENROUTER_API_KEY"),
                    base_url="https://openrouter.ai/api/v1",
                    default_headers={
                        "HTTP-Referer": "http://localhost:3000",
                        "X-Title": "LangChain Cisco MCP Agent",
                    }
                )

                # Create agent with Cisco Support tools
                agent = create_agent(
                    model=model,
                    tools=cisco_tools,
                )

                # Example queries
                queries = [
                    "Search for recent bugs related to 'crash' in Cisco products",
                    "Find high-severity bugs modified in the last 30 days",
                    "Search for bugs affecting Catalyst 9200 series",
                ]

                # Run the first query
                query = queries[0]
                print(f"\nRunning query: {query}")

                result = await agent.ainvoke({"messages": [{"role": "user", "content": query}]})

                print("\n--- Agent Response ---")
                print(json.dumps(result, indent=2, default=str))

    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

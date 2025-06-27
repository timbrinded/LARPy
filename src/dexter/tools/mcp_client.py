"""MCP (Model Context Protocol) client integration for LangGraph agents.

This module provides integration with MCP servers, specifically the Perplexity server
for enhanced search capabilities.
"""

import asyncio
import os
from dataclasses import dataclass
from typing import Any, Dict, List

from langchain_core.tools import tool
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@dataclass
class MCPToolResult:
    """Result from an MCP tool execution."""
    success: bool
    content: Any
    error: str | None = None


class MCPClient:
    """Client for interacting with MCP servers."""
    
    def __init__(self):
        """Initialize MCP client."""
        self.session: ClientSession | None = None
        self.perplexity_available = False
        
    async def connect_perplexity(self):
        """Connect to the Perplexity MCP server."""
        try:
            # Get the path to the Perplexity MCP server
            perplexity_path = os.getenv("PERPLEXITY_MCP_PATH", "npx")
            perplexity_args = ["-y", "@ppl-ai/mcp-perplexity"]
            
            # Add API key if available
            api_key = os.getenv("PERPLEXITY_API_KEY")
            if api_key:
                perplexity_args.extend(["--api-key", api_key])
            
            server_params = StdioServerParameters(
                command=perplexity_path,
                args=perplexity_args,
                env=os.environ.copy()
            )
            
            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    self.session = session
                    await session.initialize()
                    
                    # List available tools
                    tools = await session.list_tools()
                    self.perplexity_available = any(
                        tool.name == "perplexity_ask" for tool in tools.tools
                    )
                    
                    return self.perplexity_available
                    
        except Exception:
            # Log error silently - tools will return error message
            return False
    
    async def ask_perplexity(self, messages: List[Dict[str, str]]) -> MCPToolResult:
        """Ask Perplexity a question using the MCP protocol."""
        if not self.session or not self.perplexity_available:
            # Try to connect if not already connected
            if not await self.connect_perplexity():
                return MCPToolResult(
                    success=False,
                    content=None,
                    error="Failed to connect to Perplexity MCP server"
                )
        
        try:
            # Call the perplexity_ask tool
            if self.session is None:
                raise RuntimeError("Session not initialized")
                
            result = await self.session.call_tool(
                "perplexity_ask",
                {"messages": messages}
            )
            
            # Handle different content types
            content = None
            if result.content:
                first_content = result.content[0]
                if hasattr(first_content, 'text'):
                    content = first_content.text
                else:
                    content = str(first_content)
            
            return MCPToolResult(
                success=True,
                content=content
            )
        except Exception as e:
            return MCPToolResult(
                success=False,
                content=None,
                error=str(e)
            )


# Global MCP client instance
_mcp_client = MCPClient()


@tool
async def perplexity_search(query: str) -> str:
    """Search for information using Perplexity AI through MCP.
    
    This tool provides access to Perplexity's advanced search capabilities,
    offering more accurate and up-to-date results than traditional web search.
    
    Args:
        query: The search query or question to ask Perplexity
        
    Returns:
        The response from Perplexity AI
    """
    messages = [
        {"role": "user", "content": query}
    ]
    
    # Create event loop if not in async context
    try:
        result = await _mcp_client.ask_perplexity(messages)
    except RuntimeError:
        # Not in async context, create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_mcp_client.ask_perplexity(messages))
        loop.close()
    
    if result.success:
        return result.content or "No response from Perplexity"
    else:
        return f"Error: {result.error}"


@tool
async def perplexity_conversation(messages: List[Dict[str, str]]) -> str:
    """Have a multi-turn conversation with Perplexity AI through MCP.
    
    This tool allows for more complex interactions with Perplexity,
    maintaining context across multiple messages.
    
    Args:
        messages: List of message dictionaries with 'role' and 'content' keys.
                 Role can be 'system', 'user', or 'assistant'.
        
    Returns:
        The response from Perplexity AI
    """
    # Validate message format
    for msg in messages:
        if not isinstance(msg, dict) or 'role' not in msg or 'content' not in msg:
            return "Error: Each message must be a dict with 'role' and 'content' keys"
        if msg['role'] not in ['system', 'user', 'assistant']:
            return f"Error: Invalid role '{msg['role']}'. Must be 'system', 'user', or 'assistant'"
    
    # Create event loop if not in async context
    try:
        result = await _mcp_client.ask_perplexity(messages)
    except RuntimeError:
        # Not in async context, create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_mcp_client.ask_perplexity(messages))
        loop.close()
    
    if result.success:
        return result.content or "No response from Perplexity"
    else:
        return f"Error: {result.error}"


# Optional: Direct MCP tool wrapper for raw MCP access
@tool
async def call_mcp_tool(server: str, tool_name: str, arguments: Dict[str, Any]) -> str:
    """Call any MCP tool directly (advanced usage).
    
    This is a lower-level interface for calling MCP tools when you need
    direct access to MCP server capabilities.
    
    Args:
        server: The MCP server to connect to (currently only 'perplexity' supported)
        tool_name: The name of the tool to call
        arguments: The arguments to pass to the tool
        
    Returns:
        The tool execution result
    """
    if server != "perplexity":
        return f"Error: Server '{server}' not supported. Only 'perplexity' is currently available."
    
    if not _mcp_client.session:
        connected = await _mcp_client.connect_perplexity()
        if not connected:
            return "Error: Failed to connect to Perplexity MCP server"
    
    try:
        if _mcp_client.session is None:
            return "Error: Session not initialized"
            
        result = await _mcp_client.session.call_tool(tool_name, arguments)
        if result.content:
            first_content = result.content[0]
            if hasattr(first_content, 'text'):
                return first_content.text
            else:
                return str(first_content)
        return "No content returned from tool"
    except Exception as e:
        return f"Error calling MCP tool: {str(e)}"
"""
MCP (Model Context Protocol) client for communicating with the MCP server.
"""

import json
from typing import Dict, Any, Optional
import httpx

from app.config import settings


class MCPClient:
    """Client for communicating with the MCP server via HTTP."""
    
    def __init__(self):
        self.base_url = settings.APP_URL.rstrip('/')  # e.g., "http://localhost:8000"
        self.mcp_endpoint = f"{self.base_url}/mcp"
        self._client: Optional[httpx.AsyncClient] = None
        self._timeout = httpx.Timeout(30.0, connect=5.0)
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call an MCP tool via HTTP POST.
        
        Args:
            tool_name: Name of the tool to call (e.g., "execute_sql", "query_data")
            arguments: Arguments to pass to the tool
            
        Returns:
            Dictionary containing the tool result
            
        Raises:
            Exception: If the tool call fails
        """
        # MCP over HTTP uses JSON-RPC 2.0 format
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": 1
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        # Add API key if configured
        if settings.MCP_API_KEY:
            headers["Authorization"] = f"Bearer {settings.MCP_API_KEY}"
        
        try:
            response = await self.client.post(
                self.mcp_endpoint,
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Check for JSON-RPC error
            if "error" in result:
                raise Exception(f"MCP tool error: {result['error']}")
            
            # Extract the actual result
            return result.get("result", {})
            
        except httpx.HTTPStatusError as e:
            raise Exception(f"HTTP error calling MCP tool '{tool_name}': {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            raise Exception(f"Request error calling MCP tool '{tool_name}': {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response from MCP tool '{tool_name}': {str(e)}")
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Global MCP client instance
mcp_client = MCPClient()
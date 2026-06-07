from mcp.server.fastmcp import FastMCP

from dynamic_mcp_skill_hub.interceptor import QueryInterceptor
from dynamic_mcp_skill_hub.storage import FilesystemToolRegistry

mcp = FastMCP("dynamic-mcp-skill-hub")
registry = FilesystemToolRegistry()
interceptor = QueryInterceptor(registry=registry)


@mcp.tool()
def create_dynamic_tool(request: str) -> dict[str, object]:
    """Create or update a versioned filesystem-backed MCP tool."""
    return interceptor.intercept(request)


@mcp.tool()
def query_interceptor(query: str) -> dict[str, object]:
    """Intercept a natural-language query, generate a tool, and publish it."""
    return interceptor.intercept(query)


def run_server() -> None:
    registry.ensure_base_dirs()
    mcp.run()

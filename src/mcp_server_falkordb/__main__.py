"""Entry point for ``python -m mcp_server_falkordb`` and ``mcp-server-falkordb`` CLI."""

from __future__ import annotations


def main() -> None:
    """Start the FalkorDB MCP server (stdio transport)."""
    from .server import mcp

    mcp.run()


if __name__ == "__main__":
    main()

"""Error-path tests for all 6 MCP tools.

Each test patches the underlying FalkorDB operation to raise an exception
and asserts the tool returns a user-friendly error string (not a raw traceback).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from mcp_server_falkordb.client import FalkorDBConnection
from mcp_server_falkordb.server import (
    GraphDeleteInput,
    GraphDescribeInput,
    GraphExploreInput,
    GraphListInput,
    GraphMutateInput,
    GraphQueryInput,
    graph_delete,
    graph_describe,
    graph_explore,
    graph_list,
    graph_mutate,
    graph_query,
)


def _make_ctx(conn: FalkorDBConnection) -> object:
    """Minimal mock Context supplying a FalkorDB connection."""
    ctx = AsyncMock()
    ctx.request_context.lifespan_context = {"conn": conn}
    return ctx


def _make_conn() -> FalkorDBConnection:
    """Return a FalkorDBConnection backed by a mock FalkorDB client."""
    mock_db = AsyncMock()
    return FalkorDBConnection(mock_db)


class TestToolErrorPaths:
    """Each tool must return a user-friendly error string on exception."""

    @pytest.mark.asyncio
    async def test_graph_list_error_returns_friendly_string(self) -> None:
        conn = _make_conn()
        with patch.object(conn, "list_graphs", side_effect=RuntimeError("boom")):
            ctx = _make_ctx(conn)
            result = await graph_list(GraphListInput(), ctx)  # type: ignore[arg-type]
        assert isinstance(result, str)
        assert "Error" in result
        assert "Traceback" not in result

    @pytest.mark.asyncio
    async def test_graph_describe_error_returns_friendly_string(self) -> None:
        conn = _make_conn()
        with patch.object(conn, "query_graph", side_effect=RuntimeError("boom")):
            ctx = _make_ctx(conn)
            result = await graph_describe(
                GraphDescribeInput(graph="test_graph"),
                ctx,  # type: ignore[arg-type]
            )
        assert isinstance(result, str)
        assert "Error" in result
        assert "Traceback" not in result

    @pytest.mark.asyncio
    async def test_graph_query_error_returns_friendly_string(self) -> None:
        conn = _make_conn()
        with patch.object(conn, "query_graph", side_effect=RuntimeError("boom")):
            ctx = _make_ctx(conn)
            result = await graph_query(
                GraphQueryInput(graph="test_graph", query="MATCH (n) RETURN n"),
                ctx,  # type: ignore[arg-type]
            )
        assert isinstance(result, str)
        assert "error" in result.lower()
        assert "Traceback" not in result

    @pytest.mark.asyncio
    async def test_graph_mutate_error_returns_friendly_string(self) -> None:
        conn = _make_conn()
        with patch.object(conn, "query_graph", side_effect=RuntimeError("boom")):
            ctx = _make_ctx(conn)
            result = await graph_mutate(
                GraphMutateInput(graph="test_graph", query="CREATE (n:Foo)"),
                ctx,  # type: ignore[arg-type]
            )
        assert isinstance(result, str)
        assert "error" in result.lower()
        assert "Traceback" not in result

    @pytest.mark.asyncio
    async def test_graph_explore_error_returns_friendly_string(self) -> None:
        conn = _make_conn()
        with patch.object(conn, "query_graph", side_effect=RuntimeError("boom")):
            ctx = _make_ctx(conn)
            result = await graph_explore(
                GraphExploreInput(graph="test_graph"),
                ctx,  # type: ignore[arg-type]
            )
        assert isinstance(result, str)
        assert "Error" in result
        assert "Traceback" not in result

    @pytest.mark.asyncio
    async def test_graph_delete_error_returns_friendly_string(self) -> None:
        conn = _make_conn()
        with patch.object(conn, "delete_graph", side_effect=RuntimeError("boom")):
            ctx = _make_ctx(conn)
            result = await graph_delete(
                GraphDeleteInput(graph="test_graph", confirm=True),
                ctx,  # type: ignore[arg-type]
            )
        assert isinstance(result, str)
        assert "Error" in result
        assert "Traceback" not in result

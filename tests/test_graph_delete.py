"""Tests for graph_delete tool logic."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from falkordb.asyncio import FalkorDB

from mcp_server_falkordb.client import FalkorDBConnection
from mcp_server_falkordb.server import GraphDeleteInput, graph_delete


class TestGraphDeleteConfirmGate:
    """Unit tests for the confirm=True gate in the graph_delete tool.

    These call the raw tool function with a mock Context to verify the
    gate fires before any database operation, not just at the client layer.
    """

    def _make_ctx(self, falkordb_client: FalkorDB) -> object:
        """Build a minimal mock Context that supplies the FalkorDB connection."""
        mock_conn = FalkorDBConnection(falkordb_client)
        ctx = AsyncMock()
        ctx.request_context.lifespan_context = {"conn": mock_conn}
        return ctx

    @pytest.mark.asyncio
    async def test_confirm_false_refuses_deletion(self, falkordb_client: FalkorDB) -> None:
        """Tool-level: confirm=False must return a refusal string, not delete anything."""
        # Create a graph so we can assert it still exists after the refusal
        name = f"_test_mcp_confirmgate_{uuid.uuid4().hex[:8]}"
        graph = falkordb_client.select_graph(name)
        await graph.query("CREATE (n:Temp)")

        try:
            ctx = self._make_ctx(falkordb_client)
            params = GraphDeleteInput(graph=name, confirm=False)
            result = await graph_delete(params, ctx)  # type: ignore[arg-type]

            assert "refused" in result.lower() or "confirm" in result.lower()

            # Graph must still exist
            conn = FalkorDBConnection(falkordb_client)
            graphs = await conn.list_graphs()
            assert name in graphs
        finally:
            import contextlib

            with contextlib.suppress(Exception):
                await graph.delete()

    @pytest.mark.asyncio
    async def test_confirm_true_deletes_graph(self, falkordb_client: FalkorDB) -> None:
        """Tool-level: confirm=True must delete the graph."""
        name = f"_test_mcp_confirmgate_{uuid.uuid4().hex[:8]}"
        graph = falkordb_client.select_graph(name)
        await graph.query("CREATE (n:Temp)")

        ctx = self._make_ctx(falkordb_client)
        params = GraphDeleteInput(graph=name, confirm=True)
        result = await graph_delete(params, ctx)  # type: ignore[arg-type]

        assert "deleted" in result.lower()

        conn = FalkorDBConnection(falkordb_client)
        graphs = await conn.list_graphs()
        assert name not in graphs


@pytest.mark.asyncio
class TestGraphDeleteIntegration:
    async def test_delete_removes_graph(self, falkordb_client: FalkorDB) -> None:
        """Create an ephemeral graph, delete it, confirm it's gone."""
        conn = FalkorDBConnection(falkordb_client)

        name = f"_test_mcp_del_{uuid.uuid4().hex[:8]}"
        graph = falkordb_client.select_graph(name)
        await graph.query("CREATE (n:Temp)")

        graphs_before = await conn.list_graphs()
        assert name in graphs_before

        await conn.delete_graph(name)

        graphs_after = await conn.list_graphs()
        assert name not in graphs_after

    async def test_delete_nonexistent_graph_raises(self, falkordb_client: FalkorDB) -> None:
        """Deleting a graph that doesn't exist should raise an error."""
        from redis import ResponseError

        conn = FalkorDBConnection(falkordb_client)
        with pytest.raises(ResponseError):
            await conn.delete_graph("_test_mcp_nonexistent_should_not_exist_xyz")

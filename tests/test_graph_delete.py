"""Tests for graph_delete tool logic."""

from __future__ import annotations

import uuid

import pytest
from falkordb.asyncio import FalkorDB

from mcp_server_falkordb.client import FalkorDBConnection


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

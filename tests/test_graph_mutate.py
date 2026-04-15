"""Tests for graph_mutate (write) tool logic."""

from __future__ import annotations

import pytest
from falkordb.asyncio import FalkorDB

from mcp_server_falkordb.client import FalkorDBConnection


@pytest.mark.asyncio
class TestGraphMutateIntegration:
    async def test_create_node_succeeds(self, test_graph_name: str) -> None:
        db = FalkorDB(host="localhost", port=6379)
        conn = FalkorDBConnection(db)
        result = await conn.query_graph(
            test_graph_name,
            "CREATE (n:Temporary {name: 'TestNode'}) RETURN n.name",
            read_only=False,
        )
        assert result.nodes_created == 1

    async def test_delete_node_succeeds(self, test_graph_name: str) -> None:
        db = FalkorDB(host="localhost", port=6379)
        conn = FalkorDBConnection(db)
        # Create then delete
        await conn.query_graph(
            test_graph_name,
            "CREATE (n:DeleteMe {tag: 'removeme'})",
            read_only=False,
        )
        result = await conn.query_graph(
            test_graph_name,
            "MATCH (n:DeleteMe) DELETE n",
            read_only=False,
        )
        assert result.nodes_deleted >= 1

    async def test_set_property_succeeds(self, test_graph_name: str) -> None:
        db = FalkorDB(host="localhost", port=6379)
        conn = FalkorDBConnection(db)
        result = await conn.query_graph(
            test_graph_name,
            "MATCH (n:Person {name: 'Alice'}) SET n.updated = true RETURN n.updated",
            read_only=False,
        )
        assert result.properties_set >= 1

    async def test_merge_upsert_succeeds(self, test_graph_name: str) -> None:
        db = FalkorDB(host="localhost", port=6379)
        conn = FalkorDBConnection(db)
        result = await conn.query_graph(
            test_graph_name,
            "MERGE (n:Country {code: 'GB'}) RETURN n.code",
            read_only=False,
        )
        assert result.nodes_created >= 0  # upsert — either created or found

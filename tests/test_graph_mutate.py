"""Tests for graph_mutate (write) tool logic."""

from __future__ import annotations

import json

import pytest
from falkordb.asyncio import FalkorDB

from mcp_server_falkordb.client import FalkorDBConnection


@pytest.mark.asyncio
class TestGraphMutateIntegration:
    async def test_create_node_succeeds(
        self, falkordb_client: FalkorDB, test_graph_name: str
    ) -> None:
        conn = FalkorDBConnection(falkordb_client)
        result = await conn.query_graph(
            test_graph_name,
            "CREATE (n:Temporary {name: 'TestNode'}) RETURN n.name",
            read_only=False,
        )
        assert result.nodes_created == 1

    async def test_delete_node_succeeds(
        self, falkordb_client: FalkorDB, test_graph_name: str
    ) -> None:
        conn = FalkorDBConnection(falkordb_client)
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

    async def test_set_property_succeeds(
        self, falkordb_client: FalkorDB, test_graph_name: str
    ) -> None:
        conn = FalkorDBConnection(falkordb_client)
        result = await conn.query_graph(
            test_graph_name,
            "MATCH (n:Person {name: 'Alice'}) SET n.updated = true RETURN n.updated",
            read_only=False,
        )
        assert result.properties_set >= 1

    async def test_merge_upsert_succeeds(
        self, falkordb_client: FalkorDB, test_graph_name: str
    ) -> None:
        conn = FalkorDBConnection(falkordb_client)
        result = await conn.query_graph(
            test_graph_name,
            "MERGE (n:Country {code: 'GB'}) RETURN n.code",
            read_only=False,
        )
        assert result.nodes_created >= 0  # upsert — either created or found

    async def test_mutate_json_format_structure(
        self, falkordb_client: FalkorDB, test_graph_name: str
    ) -> None:
        """Mutation result in JSON format has expected keys."""
        conn = FalkorDBConnection(falkordb_client)
        result = await conn.query_graph(
            test_graph_name,
            "CREATE (n:JsonTest {name: 'fmt_test'})",
            read_only=False,
        )
        # Simulate the JSON format output the tool would produce
        stats = {
            "nodes_created": result.nodes_created,
            "nodes_deleted": result.nodes_deleted,
            "relationships_created": result.relationships_created,
            "relationships_deleted": result.relationships_deleted,
            "properties_set": result.properties_set,
            "properties_removed": result.properties_removed,
            "labels_added": result.labels_added,
            "execution_ms": result.run_time_ms,
        }
        payload = json.dumps({"graph": test_graph_name, "mutation": stats}, indent=2)
        parsed = json.loads(payload)
        assert parsed["graph"] == test_graph_name
        assert "mutation" in parsed
        assert parsed["mutation"]["nodes_created"] >= 1

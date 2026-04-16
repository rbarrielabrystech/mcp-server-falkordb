"""Tests for graph_describe tool logic (schema retrieval)."""

from __future__ import annotations

import json

import pytest
from falkordb.asyncio import FalkorDB

from mcp_server_falkordb.client import FalkorDBConnection
from mcp_server_falkordb.formatters import format_schema_json, format_schema_markdown


async def _get_schema(conn: FalkorDBConnection, graph_name: str) -> dict:  # type: ignore[type-arg]
    """Helper: return schema dict for a graph."""
    # Node labels
    result = await conn.query_graph(
        graph_name,
        "CALL db.labels() YIELD label RETURN label",
        read_only=True,
    )
    labels = [row[0] for row in result.result_set]

    # Relationship types
    result = await conn.query_graph(
        graph_name,
        "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType",
        read_only=True,
    )
    rel_types = [row[0] for row in result.result_set]

    # Property keys
    result = await conn.query_graph(
        graph_name,
        "CALL db.propertyKeys() YIELD propertyKey RETURN propertyKey",
        read_only=True,
    )
    prop_keys = [row[0] for row in result.result_set]

    # Node counts per label
    node_counts: dict[str, int] = {}
    for label in labels:
        r = await conn.query_graph(
            graph_name,
            f"MATCH (n:{label}) RETURN count(n)",
            read_only=True,
        )
        node_counts[label] = r.result_set[0][0] if r.result_set else 0

    # Rel counts per type
    rel_counts: dict[str, int] = {}
    for rtype in rel_types:
        r = await conn.query_graph(
            graph_name,
            f"MATCH ()-[r:{rtype}]->() RETURN count(r)",
            read_only=True,
        )
        rel_counts[rtype] = r.result_set[0][0] if r.result_set else 0

    return {
        "labels": labels,
        "rel_types": rel_types,
        "prop_keys": prop_keys,
        "node_counts": node_counts,
        "rel_counts": rel_counts,
    }


@pytest.mark.asyncio
class TestGraphDescribeIntegration:
    async def test_labels_detected(self, falkordb_client: FalkorDB, test_graph_name: str) -> None:
        conn = FalkorDBConnection(falkordb_client)
        schema = await _get_schema(conn, test_graph_name)
        assert "Person" in schema["labels"]
        assert "City" in schema["labels"]

    async def test_relationship_types_detected(
        self, falkordb_client: FalkorDB, test_graph_name: str
    ) -> None:
        conn = FalkorDBConnection(falkordb_client)
        schema = await _get_schema(conn, test_graph_name)
        assert "KNOWS" in schema["rel_types"]
        assert "LIVES_IN" in schema["rel_types"]

    async def test_property_keys_detected(
        self, falkordb_client: FalkorDB, test_graph_name: str
    ) -> None:
        conn = FalkorDBConnection(falkordb_client)
        schema = await _get_schema(conn, test_graph_name)
        assert "name" in schema["prop_keys"]

    async def test_node_counts_correct(
        self, falkordb_client: FalkorDB, test_graph_name: str
    ) -> None:
        conn = FalkorDBConnection(falkordb_client)
        schema = await _get_schema(conn, test_graph_name)
        assert schema["node_counts"].get("Person", 0) == 2
        assert schema["node_counts"].get("City", 0) == 1

    async def test_schema_markdown_format(
        self, falkordb_client: FalkorDB, test_graph_name: str
    ) -> None:
        conn = FalkorDBConnection(falkordb_client)
        schema = await _get_schema(conn, test_graph_name)
        text = format_schema_markdown(
            test_graph_name,
            schema["labels"],
            schema["rel_types"],
            schema["prop_keys"],
            schema["node_counts"],
            schema["rel_counts"],
        )
        assert "Person" in text
        assert "KNOWS" in text
        assert "name" in text
        assert "Schema:" in text

    async def test_schema_json_format(
        self, falkordb_client: FalkorDB, test_graph_name: str
    ) -> None:
        conn = FalkorDBConnection(falkordb_client)
        schema = await _get_schema(conn, test_graph_name)
        text = format_schema_json(
            test_graph_name,
            schema["labels"],
            schema["rel_types"],
            schema["prop_keys"],
            schema["node_counts"],
            schema["rel_counts"],
        )
        data = json.loads(text)
        assert "Person" in data["labels"]
        assert "KNOWS" in data["relationship_types"]

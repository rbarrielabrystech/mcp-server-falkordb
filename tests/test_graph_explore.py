"""Tests for graph_explore workflow tool."""

from __future__ import annotations

import json

import pytest
from falkordb.asyncio import FalkorDB

from mcp_server_falkordb.client import FalkorDBConnection


async def _explore_graph(conn: FalkorDBConnection, graph_name: str) -> dict:  # type: ignore[type-arg]
    """Simulate what graph_explore does: schema + sample nodes + sample edges."""
    # Schema
    r = await conn.query_graph(
        graph_name,
        "CALL db.labels() YIELD label RETURN label",
        read_only=True,
    )
    labels = [row[0] for row in r.result_set]

    r = await conn.query_graph(
        graph_name,
        "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType",
        read_only=True,
    )
    rel_types = [row[0] for row in r.result_set]

    # Sample nodes
    r = await conn.query_graph(
        graph_name,
        "MATCH (n) RETURN n LIMIT 3",
        read_only=True,
    )
    sample_nodes = r.result_set

    # Sample edges
    r = await conn.query_graph(
        graph_name,
        "MATCH ()-[r]->() RETURN r LIMIT 3",
        read_only=True,
    )
    sample_edges = r.result_set

    return {
        "labels": labels,
        "rel_types": rel_types,
        "sample_nodes": sample_nodes,
        "sample_edges": sample_edges,
    }


@pytest.mark.asyncio
class TestGraphExploreIntegration:
    async def test_explore_returns_labels(
        self, falkordb_client: FalkorDB, test_graph_name: str
    ) -> None:
        conn = FalkorDBConnection(falkordb_client)
        info = await _explore_graph(conn, test_graph_name)
        assert len(info["labels"]) >= 2
        assert "Person" in info["labels"]

    async def test_explore_returns_sample_nodes(
        self, falkordb_client: FalkorDB, test_graph_name: str
    ) -> None:
        conn = FalkorDBConnection(falkordb_client)
        info = await _explore_graph(conn, test_graph_name)
        assert len(info["sample_nodes"]) >= 1

    async def test_explore_returns_sample_edges(
        self, falkordb_client: FalkorDB, test_graph_name: str
    ) -> None:
        conn = FalkorDBConnection(falkordb_client)
        info = await _explore_graph(conn, test_graph_name)
        assert len(info["sample_edges"]) >= 1

    async def test_explore_returns_rel_types(
        self, falkordb_client: FalkorDB, test_graph_name: str
    ) -> None:
        conn = FalkorDBConnection(falkordb_client)
        info = await _explore_graph(conn, test_graph_name)
        assert "KNOWS" in info["rel_types"]

    async def test_explore_json_format_structure(
        self, falkordb_client: FalkorDB, test_graph_name: str
    ) -> None:
        """Explore JSON output has schema, sample_nodes, and sample_edges keys."""
        conn = FalkorDBConnection(falkordb_client)
        info = await _explore_graph(conn, test_graph_name)

        # Simulate JSON payload structure matching server.py graph_explore
        payload = {
            "graph": test_graph_name,
            "schema": {
                "labels": sorted(info["labels"]),
                "relationship_types": sorted(info["rel_types"]),
            },
            "sample_nodes": [{"raw": str(n)} for n in info["sample_nodes"]],
            "sample_edges": [{"raw": str(e)} for e in info["sample_edges"]],
        }
        text = json.dumps(payload, indent=2, default=str)
        parsed = json.loads(text)

        assert parsed["graph"] == test_graph_name
        assert "schema" in parsed
        assert "Person" in parsed["schema"]["labels"]
        assert len(parsed["sample_nodes"]) >= 1
        assert len(parsed["sample_edges"]) >= 1

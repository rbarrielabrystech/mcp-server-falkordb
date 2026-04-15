"""Tests for graph_explore workflow tool."""

from __future__ import annotations

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
    async def test_explore_returns_labels(self, test_graph_name: str) -> None:
        db = FalkorDB(host="localhost", port=6379)
        conn = FalkorDBConnection(db)
        info = await _explore_graph(conn, test_graph_name)
        assert len(info["labels"]) >= 2
        assert "Person" in info["labels"]

    async def test_explore_returns_sample_nodes(self, test_graph_name: str) -> None:
        db = FalkorDB(host="localhost", port=6379)
        conn = FalkorDBConnection(db)
        info = await _explore_graph(conn, test_graph_name)
        assert len(info["sample_nodes"]) >= 1

    async def test_explore_returns_sample_edges(self, test_graph_name: str) -> None:
        db = FalkorDB(host="localhost", port=6379)
        conn = FalkorDBConnection(db)
        info = await _explore_graph(conn, test_graph_name)
        assert len(info["sample_edges"]) >= 1

    async def test_explore_returns_rel_types(self, test_graph_name: str) -> None:
        db = FalkorDB(host="localhost", port=6379)
        conn = FalkorDBConnection(db)
        info = await _explore_graph(conn, test_graph_name)
        assert "KNOWS" in info["rel_types"]

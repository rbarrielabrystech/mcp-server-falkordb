"""Tests for graph_query (read-only) tool logic."""

from __future__ import annotations

import json

import pytest
from falkordb.asyncio import FalkorDB

from mcp_server_falkordb.client import FalkorDBConnection
from mcp_server_falkordb.formatters import (
    format_query_result_json,
    format_query_result_markdown,
)
from mcp_server_falkordb.validators import CypherWriteError, validate_read_only_query


@pytest.mark.asyncio
class TestGraphQueryIntegration:
    async def test_simple_match_returns_results(
        self, falkordb_client: FalkorDB, test_graph_name: str
    ) -> None:
        conn = FalkorDBConnection(falkordb_client)
        result = await conn.query_graph(
            test_graph_name,
            "MATCH (n:Person) RETURN n.name ORDER BY n.name",
            read_only=True,
        )
        names = [row[0] for row in result.result_set]
        assert "Alice" in names
        assert "Bob" in names

    async def test_count_query(self, falkordb_client: FalkorDB, test_graph_name: str) -> None:
        conn = FalkorDBConnection(falkordb_client)
        result = await conn.query_graph(
            test_graph_name,
            "MATCH (n) RETURN count(n) as total",
            read_only=True,
        )
        total = result.result_set[0][0]
        assert total >= 2  # Alice, Bob, London

    async def test_write_rejected_before_execution(self, test_graph_name: str) -> None:
        with pytest.raises(CypherWriteError):
            validate_read_only_query("CREATE (n:Spy {name: 'Eve'})")

    async def test_markdown_format_has_table(
        self, falkordb_client: FalkorDB, test_graph_name: str
    ) -> None:
        conn = FalkorDBConnection(falkordb_client)
        result = await conn.query_graph(
            test_graph_name,
            "MATCH (n:Person) RETURN n.name",
            read_only=True,
        )
        text = format_query_result_markdown(result)
        assert "Alice" in text
        assert "|" in text  # markdown table

    async def test_json_format_has_rows(
        self, falkordb_client: FalkorDB, test_graph_name: str
    ) -> None:
        conn = FalkorDBConnection(falkordb_client)
        result = await conn.query_graph(
            test_graph_name,
            "MATCH (n:Person) RETURN n.name AS name",
            read_only=True,
        )
        text = format_query_result_json(result)
        data = json.loads(text)
        assert data["row_count"] >= 2
        names = [row["name"] for row in data["rows"]]
        assert "Alice" in names

    async def test_empty_result_returns_no_results_message(
        self, falkordb_client: FalkorDB, test_graph_name: str
    ) -> None:
        conn = FalkorDBConnection(falkordb_client)
        result = await conn.query_graph(
            test_graph_name,
            "MATCH (n:NonExistentLabel) RETURN n",
            read_only=True,
        )
        text = format_query_result_markdown(result)
        assert "No results" in text

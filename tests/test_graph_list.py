"""Tests for graph_list tool logic."""

from __future__ import annotations

import pytest

from mcp_server_falkordb.client import FalkorDB, FalkorDBConnection
from mcp_server_falkordb.formatters import (
    format_graph_list_json,
    format_graph_list_markdown,
)


class TestGraphListFormatters:
    def test_markdown_non_empty(self) -> None:
        text = format_graph_list_markdown(["alpha", "beta", "gamma"])
        assert "alpha" in text
        assert "beta" in text
        assert "Total: 3" in text

    def test_markdown_empty(self) -> None:
        text = format_graph_list_markdown([])
        assert "No graphs" in text

    def test_json_non_empty(self) -> None:
        import json

        text = format_graph_list_json(["alpha", "beta"])
        data = json.loads(text)
        assert data["count"] == 2
        assert "alpha" in data["graphs"]

    def test_json_empty(self) -> None:
        import json

        data = json.loads(format_graph_list_json([]))
        assert data["count"] == 0


@pytest.mark.asyncio
class TestGraphListIntegration:
    """Hit the real FalkorDB."""

    async def test_list_graphs_returns_list(
        self, falkordb_client: FalkorDB, test_graph_name: str
    ) -> None:
        conn = FalkorDBConnection(falkordb_client)
        graphs = await conn.list_graphs()
        assert isinstance(graphs, list)
        # The ephemeral test graph must appear
        assert test_graph_name in graphs

    async def test_list_graphs_does_not_include_test_prefix_by_default(
        self, falkordb_client: FalkorDB, test_graph_name: str
    ) -> None:
        conn = FalkorDBConnection(falkordb_client)
        graphs = await conn.list_graphs()
        # The test graph we just created should appear
        assert test_graph_name in graphs

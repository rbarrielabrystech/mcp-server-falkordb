"""FalkorDB async client wrapper.

Holds a single async FalkorDB connection, reused across all tool calls.
Connection details come from environment variables (with defaults).
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from falkordb.asyncio import FalkorDB
from falkordb.asyncio.graph import Graph
from falkordb.query_result import QueryResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment-based configuration
# ---------------------------------------------------------------------------

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 6379


def _get_config() -> dict[str, Any]:
    host = os.environ.get("FALKORDB_HOST", DEFAULT_HOST)
    port_str = os.environ.get("FALKORDB_PORT", str(DEFAULT_PORT))
    password = os.environ.get("FALKORDB_PASSWORD", None)
    try:
        port = int(port_str)
    except ValueError:
        port = DEFAULT_PORT
    return {"host": host, "port": port, "password": password}


# ---------------------------------------------------------------------------
# Lifespan-managed connection
# ---------------------------------------------------------------------------


class FalkorDBConnection:
    """Wraps a single async FalkorDB client, opened at server start."""

    def __init__(self, db: FalkorDB) -> None:
        self._db = db

    async def list_graphs(self) -> list[str]:
        """Return all graph names in the database."""
        result: Any = await self._db.list_graphs()
        return list(result)

    def select_graph(self, name: str) -> Graph:
        """Return a Graph handle (no network call yet)."""
        raw: Any = self._db.select_graph(name)
        return raw

    async def query_graph(
        self,
        graph_name: str,
        cypher: str,
        params: dict[str, object] | None = None,
        read_only: bool = True,
    ) -> QueryResult:
        """Execute a Cypher query against *graph_name*."""
        graph = self._db.select_graph(graph_name)
        raw: Any
        if read_only:
            raw = await graph.ro_query(cypher, params=params)
        else:
            raw = await graph.query(cypher, params=params)
        result: QueryResult = raw
        return result

    async def delete_graph(self, graph_name: str) -> None:
        """Drop an entire graph."""
        graph = self._db.select_graph(graph_name)
        await graph.delete()


@asynccontextmanager
async def create_falkordb_connection() -> AsyncIterator[FalkorDBConnection]:
    """Async context manager used as the FastMCP lifespan."""
    cfg = _get_config()
    db = FalkorDB(
        host=cfg["host"],
        port=cfg["port"],
        password=cfg["password"],
    )
    conn = FalkorDBConnection(db)
    try:
        yield conn
    finally:
        # FalkorDB async client wraps redis.asyncio; aclose() drains the
        # underlying connection pool. The `connection_pool` attribute used
        # previously does not exist on FalkorDB — the AttributeError was
        # silently swallowed, leaking sockets into TIME_WAIT on every shutdown.
        try:
            await db.aclose()
        except Exception as e:
            logger.warning("FalkorDB shutdown cleanup failed: %s", e)

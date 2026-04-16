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
DEFAULT_QUERY_TIMEOUT_MS = 30_000


def _get_config() -> dict[str, Any]:
    host = os.environ.get("FALKORDB_HOST", DEFAULT_HOST)
    port_str = os.environ.get("FALKORDB_PORT", str(DEFAULT_PORT))
    password = os.environ.get("FALKORDB_PASSWORD", None)
    timeout_str = os.environ.get("FALKORDB_QUERY_TIMEOUT_MS", str(DEFAULT_QUERY_TIMEOUT_MS))
    try:
        port = int(port_str)
    except ValueError:
        port = DEFAULT_PORT
    try:
        query_timeout_ms = int(timeout_str)
    except ValueError:
        query_timeout_ms = DEFAULT_QUERY_TIMEOUT_MS
    return {"host": host, "port": port, "password": password, "query_timeout_ms": query_timeout_ms}


# ---------------------------------------------------------------------------
# Lifespan-managed connection
# ---------------------------------------------------------------------------


class FalkorDBConnection:
    """Wraps a single async FalkorDB client, opened at server start."""

    def __init__(self, db: FalkorDB, query_timeout_ms: int = DEFAULT_QUERY_TIMEOUT_MS) -> None:
        self._db = db
        self._query_timeout_ms = query_timeout_ms

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
        """Execute a Cypher query against *graph_name*.

        Applies a timeout of ``FALKORDB_QUERY_TIMEOUT_MS`` milliseconds
        (default 30 000 ms). Override via the environment variable to allow
        longer-running analytical queries.
        """
        graph = self._db.select_graph(graph_name)
        raw: Any
        if read_only:
            raw = await graph.ro_query(cypher, params=params, timeout=self._query_timeout_ms)
        else:
            raw = await graph.query(cypher, params=params, timeout=self._query_timeout_ms)
        result: QueryResult = raw
        return result

    async def delete_graph(self, graph_name: str) -> None:
        """Drop an entire graph."""
        graph = self._db.select_graph(graph_name)
        await graph.delete()


@asynccontextmanager
async def create_falkordb_connection() -> AsyncIterator[FalkorDBConnection]:
    """Async context manager used as the FastMCP lifespan.

    Performs a non-fatal startup probe (``list_graphs`` with a 3-second
    timeout). If FalkorDB is unreachable, logs a WARNING and continues —
    tools will fail on their first call with a descriptive error.
    """
    import asyncio

    cfg = _get_config()
    db = FalkorDB(
        host=cfg["host"],
        port=cfg["port"],
        password=cfg["password"],
    )
    conn = FalkorDBConnection(db, query_timeout_ms=cfg["query_timeout_ms"])

    # Startup probe: attempt list_graphs with a short timeout.
    # Non-fatal — lazy connection is still valid; early warning helps users.
    try:
        await asyncio.wait_for(conn.list_graphs(), timeout=3.0)
        logger.debug("FalkorDB startup probe succeeded at %s:%d", cfg["host"], cfg["port"])
    except Exception:
        logger.warning(
            "FalkorDB not reachable at %s:%d — tools will fail on first call",
            cfg["host"],
            cfg["port"],
        )

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

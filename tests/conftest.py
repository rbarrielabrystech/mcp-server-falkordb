"""Shared fixtures for mcp-server-falkordb tests.

All tests that touch FalkorDB use ephemeral graphs with the _test_mcp_ prefix.
The fixture creates a unique graph, yields its name, and deletes it on teardown.
hive_* graphs are NEVER touched.
"""

from __future__ import annotations

import uuid

import pytest
from falkordb.asyncio import FalkorDB

TEST_HOST = "localhost"
TEST_PORT = 6379
TEST_GRAPH_PREFIX = "_test_mcp_"


@pytest.fixture(scope="session")
def event_loop_policy() -> None:
    return None  # use default policy


@pytest.fixture
async def falkordb_client():  # type: ignore[return]
    """Return a connected async FalkorDB client; closes connection on teardown."""
    import contextlib

    db = FalkorDB(host=TEST_HOST, port=TEST_PORT)
    yield db
    with contextlib.suppress(Exception):
        await db.aclose()


@pytest.fixture
async def test_graph_name(falkordb_client: FalkorDB):  # type: ignore[type-arg]
    """Create an ephemeral test graph, yield its name, delete on teardown."""
    name = f"{TEST_GRAPH_PREFIX}{uuid.uuid4().hex[:8]}"
    assert name.startswith(TEST_GRAPH_PREFIX), "Safety: test graph must use prefix"

    graph = falkordb_client.select_graph(name)
    # Seed with minimal data so schema calls return something
    await graph.query(
        "CREATE (:Person {name: 'Alice', age: 30})-[:KNOWS]->(:Person {name: 'Bob', age: 25})"
    )
    await graph.query("CREATE (:City {name: 'London', population: 9000000})")
    await graph.query(
        "MATCH (a:Person {name:'Alice'}), (c:City {name:'London'}) CREATE (a)-[:LIVES_IN]->(c)"
    )

    yield name

    # Teardown — best-effort, ignore errors
    import contextlib  # noqa: PLC0415

    with contextlib.suppress(Exception):
        await graph.delete()

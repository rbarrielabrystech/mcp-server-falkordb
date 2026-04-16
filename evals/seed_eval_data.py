#!/usr/bin/env python3
"""Seed the eval_data graph in FalkorDB for evaluation tests.

Creates 13 nodes (5 Agent, 5 Skill, 3 Project) and 7 relationships
(4 USES, 3 WORKS_ON) matching the evals/falkordb.xml expectations.

Usage:
    uv run python evals/seed_eval_data.py          # default localhost:6379
    FALKORDB_HOST=10.0.0.1 uv run python evals/seed_eval_data.py
"""

from __future__ import annotations

import os
import sys

from falkordb import FalkorDB

GRAPH_NAME = "eval_data"
HOST = os.environ.get("FALKORDB_HOST", "localhost")
PORT = int(os.environ.get("FALKORDB_PORT", "6379"))
PASSWORD = os.environ.get("FALKORDB_PASSWORD", None)


def seed() -> None:
    """Drop and recreate the eval_data graph with synthetic test data."""
    db = FalkorDB(host=HOST, port=PORT, password=PASSWORD)
    graph = db.select_graph(GRAPH_NAME)

    # Drop existing graph (ignore error if it doesn't exist)
    try:
        graph.delete()
        print(f"Dropped existing '{GRAPH_NAME}' graph.")
    except Exception:  # noqa: BLE001
        print(f"No existing '{GRAPH_NAME}' graph to drop.")

    # Re-select after delete
    graph = db.select_graph(GRAPH_NAME)

    # --- Agents (5 nodes) ---
    graph.query("CREATE (:Agent {name: 'python-pro', tasks: 42, status: 'active'})")
    graph.query("CREATE (:Agent {name: 'security-auditor', tasks: 17, status: 'active'})")
    graph.query("CREATE (:Agent {name: 'database-optimizer', tasks: 8, status: 'active'})")
    graph.query("CREATE (:Agent {name: 'fastapi-expert', tasks: 23, status: 'active'})")
    graph.query("CREATE (:Agent {name: 'test-writer', tasks: 5, status: 'inactive'})")

    # --- Skills (5 nodes) ---
    graph.query("CREATE (:Skill {name: 'test-driven-development', uses: 150})")
    graph.query("CREATE (:Skill {name: 'code-review', uses: 89})")
    graph.query("CREATE (:Skill {name: 'dependency-check', uses: 34})")
    graph.query("CREATE (:Skill {name: 'mcp-builder', uses: 12})")
    graph.query("CREATE (:Skill {name: 'diagram', uses: 7})")

    # --- Projects (3 nodes) — synthetic names, no real project references ---
    graph.query("CREATE (:Project {name: 'alpha-service', language: 'python'})")
    graph.query("CREATE (:Project {name: 'beta-frontend', language: 'dart'})")
    graph.query("CREATE (:Project {name: 'gamma-tools', language: 'python'})")

    # --- USES relationships (4 edges) ---
    graph.query(
        "MATCH (a:Agent {name: 'python-pro'}), (s:Skill {name: 'test-driven-development'}) "
        "CREATE (a)-[:USES]->(s)"
    )
    graph.query(
        "MATCH (a:Agent {name: 'python-pro'}), (s:Skill {name: 'code-review'}) "
        "CREATE (a)-[:USES]->(s)"
    )
    graph.query(
        "MATCH (a:Agent {name: 'security-auditor'}), (s:Skill {name: 'dependency-check'}) "
        "CREATE (a)-[:USES]->(s)"
    )
    graph.query(
        "MATCH (a:Agent {name: 'fastapi-expert'}), (s:Skill {name: 'test-driven-development'}) "
        "CREATE (a)-[:USES]->(s)"
    )

    # --- WORKS_ON relationships (3 edges) ---
    graph.query(
        "MATCH (a:Agent {name: 'python-pro'}), (p:Project {name: 'alpha-service'}) "
        "CREATE (a)-[:WORKS_ON]->(p)"
    )
    graph.query(
        "MATCH (a:Agent {name: 'security-auditor'}), (p:Project {name: 'alpha-service'}) "
        "CREATE (a)-[:WORKS_ON]->(p)"
    )
    graph.query(
        "MATCH (a:Agent {name: 'test-writer'}), (p:Project {name: 'beta-frontend'}) "
        "CREATE (a)-[:WORKS_ON]->(p)"
    )

    # Verify
    result = graph.query("MATCH (n) RETURN count(n) AS c")
    node_count = result.result_set[0][0]
    result = graph.query("MATCH ()-[r]->() RETURN count(r) AS c")
    edge_count = result.result_set[0][0]

    print(f"Seeded '{GRAPH_NAME}': {node_count} nodes, {edge_count} edges.")
    assert node_count == 13, f"Expected 13 nodes, got {node_count}"
    assert edge_count == 7, f"Expected 7 edges, got {edge_count}"
    print("Verification passed.")


if __name__ == "__main__":
    try:
        seed()
    except Exception as e:
        print(f"Error seeding eval_data: {e}", file=sys.stderr)
        sys.exit(1)

"""FalkorDB MCP server — 6 tools for graph query and management.

Tools:
    graph_list      — list all graphs (read-only)
    graph_describe  — full schema of one graph (read-only)
    graph_query     — read-only Cypher query with write-keyword enforcement
    graph_mutate    — write Cypher query (destructive)
    graph_explore   — one-call full overview: describe + samples (heavier than graph_describe)
    graph_delete    — drop an entire graph (requires confirm=True, destructive)
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from enum import StrEnum
from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field

from .client import FalkorDBConnection, create_falkordb_connection
from .formatters import (
    _truncate,
    format_graph_list_json,
    format_graph_list_markdown,
    format_query_result_json,
    format_query_result_markdown,
    format_schema_json,
    format_schema_markdown,
)
from .validators import (
    CypherWriteError,
    GraphNameError,
    validate_graph_name,
    validate_read_only_query,
)

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ResponseFormat(StrEnum):
    """Output format for tool responses."""

    MARKDOWN = "markdown"
    JSON = "json"


# ---------------------------------------------------------------------------
# Lifespan: open FalkorDB connection once, share across tools
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    async with create_falkordb_connection() as conn:
        yield {"conn": conn}


# ---------------------------------------------------------------------------
# FastMCP app
# ---------------------------------------------------------------------------

mcp = FastMCP("falkordb_mcp", lifespan=_lifespan)


def _conn(ctx: Context) -> FalkorDBConnection:  # type: ignore[type-arg]
    """Extract the shared FalkorDB connection from lifespan state."""
    state: dict[str, Any] = ctx.request_context.lifespan_context  # type: ignore[assignment]
    conn: FalkorDBConnection = state["conn"]
    return conn


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------


class GraphListInput(BaseModel):
    """Input for graph_list."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' (default) or 'json'.",
    )


class GraphDescribeInput(BaseModel):
    """Input for graph_describe."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    graph: str = Field(
        ...,
        description="Name of the graph to describe (e.g. 'my_graph').",
        min_length=1,
        max_length=200,
    )
    format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' (default) or 'json'.",
    )


class GraphQueryInput(BaseModel):
    """Input for graph_query (read-only)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    graph: str = Field(
        ...,
        description="Name of the graph to query (e.g. 'my_graph').",
        min_length=1,
        max_length=200,
    )
    query: str = Field(
        ...,
        description=(
            "Read-only Cypher query (MATCH, RETURN, CALL db.*, etc.). "
            "Write keywords (CREATE, DELETE, SET, MERGE, REMOVE, DROP) are rejected — "
            "use graph_mutate for writes. Example: "
            '"MATCH (n:Person) RETURN n.name LIMIT 10"'
        ),
        min_length=1,
        max_length=4000,
    )
    format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' table (default) or 'json' array.",
    )


class GraphMutateInput(BaseModel):
    """Input for graph_mutate (write)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    graph: str = Field(
        ...,
        description="Name of the graph to mutate (e.g. 'my_graph').",
        min_length=1,
        max_length=200,
    )
    query: str = Field(
        ...,
        description=(
            "Write Cypher query (CREATE, MERGE, SET, DELETE, REMOVE). "
            "Example: \"CREATE (n:Person {name: 'Alice', age: 30})\""
        ),
        min_length=1,
        max_length=4000,
    )
    format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' (default) or 'json'.",
    )


class GraphExploreInput(BaseModel):
    """Input for graph_explore."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    graph: str = Field(
        ...,
        description="Name of the graph to explore (e.g. 'my_graph').",
        min_length=1,
        max_length=200,
    )
    format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' (default) or 'json'.",
    )


class GraphDeleteInput(BaseModel):
    """Input for graph_delete."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    graph: str = Field(
        ...,
        description="Name of the graph to permanently delete.",
        min_length=1,
        max_length=200,
    )
    confirm: bool = Field(
        default=False,
        description=(
            "Must be set to true to confirm deletion. "
            "This operation is irreversible — all nodes, edges, and data in the graph "
            "will be permanently destroyed."
        ),
    )


# ---------------------------------------------------------------------------
# Schema helper (shared by graph_describe and graph_explore)
# ---------------------------------------------------------------------------


async def _fetch_schema(
    conn: FalkorDBConnection,
    graph_name: str,
) -> tuple[list[str], list[str], list[str], dict[str, int], dict[str, int]]:
    """Return (labels, rel_types, prop_keys, node_counts, rel_counts)."""
    r = await conn.query_graph(
        graph_name,
        "CALL db.labels() YIELD label RETURN label",
        read_only=True,
    )
    labels = [row[0] for row in (r.result_set or [])]

    r = await conn.query_graph(
        graph_name,
        "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType",
        read_only=True,
    )
    rel_types = [row[0] for row in (r.result_set or [])]

    r = await conn.query_graph(
        graph_name,
        "CALL db.propertyKeys() YIELD propertyKey RETURN propertyKey",
        read_only=True,
    )
    prop_keys = [row[0] for row in (r.result_set or [])]

    node_counts: dict[str, int] = {}
    for label in labels:
        r2 = await conn.query_graph(
            graph_name,
            f"MATCH (n:`{label}`) RETURN count(n) AS c",
            read_only=True,
        )
        node_counts[label] = r2.result_set[0][0] if r2.result_set else 0

    rel_counts: dict[str, int] = {}
    for rtype in rel_types:
        r2 = await conn.query_graph(
            graph_name,
            f"MATCH ()-[r:`{rtype}`]->() RETURN count(r) AS c",
            read_only=True,
        )
        rel_counts[rtype] = r2.result_set[0][0] if r2.result_set else 0

    return labels, rel_types, prop_keys, node_counts, rel_counts


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool(
    name="graph_list",
    annotations=ToolAnnotations(
        title="List FalkorDB Graphs",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
async def graph_list(params: GraphListInput, ctx: Context) -> str:  # type: ignore[type-arg]
    """List all graphs in the FalkorDB instance with their names.

    Returns the names of all available graphs. Use graph_describe or
    graph_explore to get schema details for a specific graph.

    Args:
        params (GraphListInput):
            - format: 'markdown' (default) or 'json'

    Returns:
        str: List of graph names. Markdown bullet list or JSON array.

    Examples:
        - Use when: "What graphs exist in FalkorDB?"
        - Use when: "Show me all available graphs"
        - Don't use when: You need schema details — use graph_describe instead
    """
    try:
        graphs = await _conn(ctx).list_graphs()
        if params.format == ResponseFormat.JSON:
            return format_graph_list_json(graphs)
        return format_graph_list_markdown(graphs)
    except Exception as e:
        return f"Error listing graphs: {e}\nHint: Check that FalkorDB is running and accessible."


@mcp.tool(
    name="graph_describe",
    annotations=ToolAnnotations(
        title="Describe FalkorDB Graph Schema",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
async def graph_describe(params: GraphDescribeInput, ctx: Context) -> str:  # type: ignore[type-arg]
    """Return the full schema of a single graph: node labels, relationship types,
    property keys, and node/edge counts per label/type.

    Use this before writing queries to understand what labels and relationships
    exist. For a combined overview with sample data, use graph_explore instead.

    Args:
        params (GraphDescribeInput):
            - graph (str): Graph name (e.g. 'my_graph')
            - format: 'markdown' (default) or 'json'

    Returns:
        str: Schema with label names, relationship types, property keys,
             and counts per label/type.

    Examples:
        - Use when: "What node labels does the my_graph graph have?"
        - Use when: "Show me the schema for the knowledge graph"
        - Don't use when: You want sample nodes too — use graph_explore
    """
    try:
        validate_graph_name(params.graph)
    except GraphNameError as e:
        return f"Error: {e}"

    try:
        labels, rel_types, prop_keys, node_counts, rel_counts = await _fetch_schema(
            _conn(ctx), params.graph
        )
        if params.format == ResponseFormat.JSON:
            return format_schema_json(
                params.graph, labels, rel_types, prop_keys, node_counts, rel_counts
            )
        return format_schema_markdown(
            params.graph, labels, rel_types, prop_keys, node_counts, rel_counts
        )
    except Exception as e:
        return (
            f"Error describing graph '{params.graph}': {e}\n"
            f"Hint: Run graph_list to verify the graph exists."
        )


@mcp.tool(
    name="graph_query",
    annotations=ToolAnnotations(
        title="Query FalkorDB Graph (Read-Only)",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
async def graph_query(params: GraphQueryInput, ctx: Context) -> str:  # type: ignore[type-arg]
    """Execute a read-only Cypher query against a FalkorDB graph.

    Write keywords (CREATE, DELETE, SET, MERGE, REMOVE, DROP) are rejected
    before the query reaches the database. Use graph_mutate for write queries.

    Args:
        params (GraphQueryInput):
            - graph (str): Graph name (e.g. 'my_graph')
            - query (str): Read-only Cypher query
            - format: 'markdown' table (default) or 'json'

    Returns:
        str: Query results as a markdown table or JSON.
             Truncated with notice if response exceeds 25,000 chars.

    Examples:
        - "MATCH (n:Person) RETURN n.name, n.age LIMIT 20"
        - "MATCH (a)-[r:KNOWS]->(b) RETURN a.name, b.name"
        - "CALL db.labels() YIELD label RETURN label"
        - Don't use for writes — use graph_mutate

    Error Handling:
        - Write keywords detected → "Use graph_mutate instead"
        - Graph not found → suggests graph_list
        - FalkorDB syntax error → returns the error + hint to run graph_describe
    """
    try:
        validate_graph_name(params.graph)
    except GraphNameError as e:
        return f"Error: {e}"

    try:
        validate_read_only_query(params.query)
    except CypherWriteError as e:
        return str(e)

    try:
        result = await _conn(ctx).query_graph(params.graph, params.query, read_only=True)
        if params.format == ResponseFormat.JSON:
            return format_query_result_json(result)
        return format_query_result_markdown(result)
    except Exception as e:
        err_str = str(e)
        hint = "Try running graph_describe to see available labels and relationship types."
        return f"Query error on '{params.graph}': {err_str}\n\nHint: {hint}"


@mcp.tool(
    name="graph_mutate",
    annotations=ToolAnnotations(
        title="Mutate FalkorDB Graph (Write)",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=False,
    ),
)
async def graph_mutate(params: GraphMutateInput, ctx: Context) -> str:  # type: ignore[type-arg]
    """Execute a write Cypher query against a FalkorDB graph.

    Supports CREATE, MERGE, SET, DELETE, REMOVE. Results include
    mutation statistics (nodes created, relationships deleted, etc.).

    This tool is intentionally separate from graph_query so that read
    operations are clearly annotated as non-destructive.

    Args:
        params (GraphMutateInput):
            - graph (str): Graph name (e.g. 'my_graph')
            - query (str): Write Cypher query
            - format: 'markdown' (default) or 'json'

    Returns:
        str: Mutation statistics: nodes created/deleted, relationships
             created/deleted, properties set/removed, execution time.

    Examples:
        - "CREATE (n:Person {name: 'Alice', age: 30})"
        - "MATCH (n:Person {name: 'Bob'}) SET n.age = 26"
        - "MATCH (n:Temp) DELETE n"
        - "MERGE (n:Country {code: 'GB'}) ON CREATE SET n.name = 'United Kingdom'"

    Error Handling:
        - Syntax errors → FalkorDB error message + hint to verify with graph_describe
    """
    try:
        validate_graph_name(params.graph)
    except GraphNameError as e:
        return f"Error: {e}"

    try:
        result = await _conn(ctx).query_graph(params.graph, params.query, read_only=False)
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

        if params.format == ResponseFormat.JSON:
            return json.dumps(
                {"graph": params.graph, "mutation": stats},
                indent=2,
            )

        lines = [f"# Mutation complete on `{params.graph}`", ""]
        for k, v in stats.items():
            if v:
                lines.append(f"- **{k.replace('_', ' ').title()}**: {v}")
        if not any(stats[k] for k in stats if k != "execution_ms"):
            lines.append("_No changes made (query matched nothing or was a no-op)._")
        lines.append(f"\n_Execution: {result.run_time_ms:.2f} ms_")
        return "\n".join(lines)
    except Exception as e:
        return (
            f"Mutation error on '{params.graph}': {e}\n"
            f"Hint: Run graph_describe to verify labels and relationship types exist."
        )


@mcp.tool(
    name="graph_explore",
    annotations=ToolAnnotations(
        title="Explore FalkorDB Graph (Quick Look)",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
async def graph_explore(params: GraphExploreInput, ctx: Context) -> str:  # type: ignore[type-arg]
    """One-call overview of a graph: schema + sample nodes + sample edges.

    Combines graph_describe with up to 3 sample nodes (any labels) and up to 3
    sample edges. The ideal starting point when exploring an unfamiliar graph.

    Args:
        params (GraphExploreInput):
            - graph (str): Graph name (e.g. 'my_graph')
            - format: 'markdown' (default) or 'json'

    Returns:
        str: Markdown overview with:
             - Node labels, relationship types, property keys with counts
             - Up to 3 sample nodes (any labels, global LIMIT 3)
             - Up to 3 sample edges

    Examples:
        - Use when: "What's in the my_graph graph?" (first look)
        - Use when: "Explore the knowledge graph before writing queries"
        - Use graph_query afterward to dig deeper
    """
    try:
        validate_graph_name(params.graph)
    except GraphNameError as e:
        return f"Error: {e}"

    conn = _conn(ctx)
    try:
        labels, rel_types, prop_keys, node_counts, rel_counts = await _fetch_schema(
            conn, params.graph
        )

        # Sample nodes (up to 3)
        r = await conn.query_graph(
            params.graph,
            "MATCH (n) RETURN n LIMIT 3",
            read_only=True,
        )
        sample_nodes = r.result_set or []

        # Sample edges (up to 3)
        _edge_q = (
            "MATCH (a)-[r]->(b) "
            "RETURN type(r) AS rel, a.name AS from_name, b.name AS to_name LIMIT 3"
        )
        r = await conn.query_graph(params.graph, _edge_q, read_only=True)
        sample_edges = r.result_set or []

        # Convert sample data to serialisable form for both formats
        node_dicts: list[dict[str, Any]] = []
        for row in sample_nodes:
            node = row[0]
            if hasattr(node, "properties") and hasattr(node, "labels"):
                node_dicts.append(
                    {
                        "labels": list(node.labels),
                        "properties": dict(node.properties),
                    }
                )
            else:
                node_dicts.append({"raw": str(node)})

        edge_dicts: list[dict[str, str]] = []
        for row in sample_edges:
            edge_dicts.append(
                {
                    "type": row[0] if row else "?",
                    "from": row[1] if len(row) > 1 else "?",
                    "to": row[2] if len(row) > 2 else "?",
                }
            )

        if params.format == ResponseFormat.JSON:
            payload = {
                "graph": params.graph,
                "schema": {
                    "labels": sorted(labels),
                    "relationship_types": sorted(rel_types),
                    "property_keys": sorted(prop_keys),
                    "node_counts_by_label": node_counts,
                    "rel_counts_by_type": rel_counts,
                },
                "sample_nodes": node_dicts,
                "sample_edges": edge_dicts,
            }
            return _truncate(json.dumps(payload, indent=2, default=str))

        # Build markdown output
        schema_text = format_schema_markdown(
            params.graph, labels, rel_types, prop_keys, node_counts, rel_counts
        )

        lines = [schema_text, "", "---", "", "## Sample Nodes (up to 3)", ""]
        if node_dicts:
            for nd in node_dicts:
                if "labels" in nd:
                    label_str = ":".join(nd["labels"])
                    props = json.dumps(nd["properties"], default=str)
                    lines.append(f"- `(:{label_str})` \u2192 {props}")
                else:
                    lines.append(f"- {nd['raw']}")
        else:
            lines.append("_No nodes found._")

        lines += ["", "## Sample Edges (up to 3)", ""]
        if edge_dicts:
            for ed in edge_dicts:
                lines.append(f"- `({ed['from']})-[:{ed['type']}]->({ed['to']})`")
        else:
            lines.append("_No edges found._")

        result = "\n".join(lines)
        return _truncate(result)
    except Exception as e:
        return (
            f"Error exploring graph '{params.graph}': {e}\n"
            f"Hint: Run graph_list to verify the graph name is correct."
        )


@mcp.tool(
    name="graph_delete",
    annotations=ToolAnnotations(
        title="Delete FalkorDB Graph (Destructive)",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=False,
    ),
)
async def graph_delete(params: GraphDeleteInput, ctx: Context) -> str:  # type: ignore[type-arg]
    """Permanently drop an entire graph and all its data.

    This operation is IRREVERSIBLE. All nodes, edges, and properties in
    the graph will be destroyed. Requires confirm=true.

    Args:
        params (GraphDeleteInput):
            - graph (str): Name of the graph to delete
            - confirm (bool): Must be true — safety gate against accidental deletion

    Returns:
        str: Confirmation message on success, or error/refusal message.

    Examples:
        - Use when: Cleaning up a temporary test graph
        - NEVER use on production graphs without explicit operator instruction
        - Always run graph_list first to double-check the name

    Error Handling:
        - confirm=false → Refuses with instructions to re-submit with confirm=true
        - Graph not found → FalkorDB error message
    """
    try:
        validate_graph_name(params.graph)
    except GraphNameError as e:
        return f"Error: {e}"

    if not params.confirm:
        return (
            f"Deletion refused: confirm=false.\n\n"
            f"To permanently delete graph '{params.graph}' and ALL its data, "
            f"re-submit with confirm=true.\n\n"
            f"**WARNING**: This operation is irreversible."
        )

    try:
        await _conn(ctx).delete_graph(params.graph)
        return f"Graph '{params.graph}' has been permanently deleted."
    except Exception as e:
        return (
            f"Error deleting graph '{params.graph}': {e}\n"
            f"Hint: Run graph_list to verify the graph name exists."
        )

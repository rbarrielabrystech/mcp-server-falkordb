"""Output formatters for FalkorDB query results.

Supports markdown (default, human-readable) and JSON (machine-readable).
Enforces CHARACTER_LIMIT with a trailing truncation notice.
"""

from __future__ import annotations

import json
from typing import Any

from falkordb.query_result import QueryResult

CHARACTER_LIMIT = 25_000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _truncate(text: str, extra_rows: int = 0) -> str:
    """Truncate *text* to CHARACTER_LIMIT and append a notice."""
    if len(text) <= CHARACTER_LIMIT:
        return text
    truncated = text[:CHARACTER_LIMIT]
    notice = (
        f"\n\n... [truncated — response exceeded {CHARACTER_LIMIT} chars. "
        f"Refine your query with LIMIT or add filters to reduce result size.]"
    )
    if extra_rows:
        notice = (
            f"\n\n... [truncated {extra_rows} more rows — response exceeded "
            f"{CHARACTER_LIMIT} chars. Refine query with LIMIT.]"
        )
    return truncated + notice


def _result_to_rows(result: QueryResult) -> tuple[list[str], list[list[Any]]]:
    """Extract header and rows from a QueryResult.

    FalkorDB returns headers as ``[[type_int, col_name], ...]``.
    We extract the column name (index 1) from each entry.
    """
    raw_headers = result.header if result.header else []
    headers: list[str] = []
    for h in raw_headers:
        if isinstance(h, (list, tuple)) and len(h) >= 2:
            headers.append(str(h[1]))
        else:
            headers.append(str(h))
    rows: list[list[Any]] = result.result_set if result.result_set else []
    return headers, rows


def _cell_to_str(cell: Any) -> str:
    """Convert a single result cell to a display string."""
    if cell is None:
        return "null"
    if isinstance(cell, (dict, list)):
        return json.dumps(cell, default=str)
    return str(cell)


# ---------------------------------------------------------------------------
# Query result formatters
# ---------------------------------------------------------------------------


def format_query_result_markdown(result: QueryResult, query: str = "") -> str:
    """Format a QueryResult as a markdown table."""
    headers, rows = _result_to_rows(result)

    if not rows:
        return "_No results returned._"

    # Build markdown table
    lines: list[str] = []
    if headers:
        lines.append("| " + " | ".join(str(h) for h in headers) + " |")
        lines.append("|" + "|".join([" --- "] * len(headers)) + "|")
    for row in rows:
        cells = [_cell_to_str(c) for c in row]
        lines.append("| " + " | ".join(cells) + " |")

    lines.append(f"\n_Rows: {len(rows)} — Execution: {result.run_time_ms:.2f} ms_")
    text = "\n".join(lines)
    return _truncate(text, max(0, len(rows) - 100))


def format_query_result_json(result: QueryResult) -> str:
    """Format a QueryResult as a JSON string."""
    headers, rows = _result_to_rows(result)

    records: list[dict[str, Any]] = []
    for row in rows:
        record: dict[str, Any] = {}
        for i, cell in enumerate(row):
            key = headers[i] if i < len(headers) else f"col_{i}"
            # Convert Node/Edge objects to dicts for JSON serialisation
            record[key] = _cell_to_serialisable(cell)
        records.append(record)

    payload = {
        "rows": records,
        "row_count": len(records),
        "execution_ms": result.run_time_ms,
    }
    text = json.dumps(payload, indent=2, default=str)
    return _truncate(text)


def _cell_to_serialisable(cell: Any) -> Any:
    """Recursively convert FalkorDB result types to JSON-serialisable forms."""
    if cell is None:
        return None
    if isinstance(cell, (str, int, float, bool)):
        return cell
    if isinstance(cell, list):
        return [_cell_to_serialisable(c) for c in cell]
    if isinstance(cell, dict):
        return {k: _cell_to_serialisable(v) for k, v in cell.items()}
    # Node or Edge: FalkorDB objects have id, labels/type, properties
    if hasattr(cell, "properties"):
        result: dict[str, Any] = {}
        if hasattr(cell, "labels"):
            result["labels"] = list(cell.labels)
        if hasattr(cell, "label"):
            result["type"] = cell.label
        result["id"] = getattr(cell, "id", None)
        result["properties"] = dict(cell.properties)
        return result
    return str(cell)


# ---------------------------------------------------------------------------
# Schema / list formatters
# ---------------------------------------------------------------------------


def format_graph_list_markdown(graphs: list[str]) -> str:
    """Format graph list as markdown."""
    if not graphs:
        return "_No graphs found in this FalkorDB instance._"
    lines = ["# FalkorDB Graphs", ""]
    for name in graphs:
        lines.append(f"- `{name}`")
    lines.append(f"\n_Total: {len(graphs)} graph(s)_")
    return "\n".join(lines)


def format_graph_list_json(graphs: list[str]) -> str:
    """Format graph list as JSON."""
    return json.dumps({"graphs": graphs, "count": len(graphs)}, indent=2)


def format_schema_markdown(
    graph_name: str,
    labels: list[str],
    rel_types: list[str],
    property_keys: list[str],
    node_counts: dict[str, int],
    rel_counts: dict[str, int],
) -> str:
    """Format graph schema as readable markdown."""
    lines = [f"# Schema: `{graph_name}`", ""]

    lines.append("## Node Labels")
    if labels:
        for label in sorted(labels):
            count = node_counts.get(label, 0)
            lines.append(f"- `:{label}` — {count} node(s)")
    else:
        lines.append("_No node labels defined._")

    lines.append("")
    lines.append("## Relationship Types")
    if rel_types:
        for rtype in sorted(rel_types):
            count = rel_counts.get(rtype, 0)
            lines.append(f"- `[:{rtype}]` — {count} relationship(s)")
    else:
        lines.append("_No relationship types defined._")

    lines.append("")
    lines.append("## Property Keys")
    if property_keys:
        for key in sorted(property_keys):
            lines.append(f"- `{key}`")
    else:
        lines.append("_No property keys defined._")

    return "\n".join(lines)


def format_schema_json(
    graph_name: str,
    labels: list[str],
    rel_types: list[str],
    property_keys: list[str],
    node_counts: dict[str, int],
    rel_counts: dict[str, int],
) -> str:
    """Format graph schema as JSON."""
    return json.dumps(
        {
            "graph": graph_name,
            "labels": sorted(labels),
            "relationship_types": sorted(rel_types),
            "property_keys": sorted(property_keys),
            "node_counts_by_label": node_counts,
            "rel_counts_by_type": rel_counts,
        },
        indent=2,
    )

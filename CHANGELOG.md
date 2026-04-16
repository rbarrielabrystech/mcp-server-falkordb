# Changelog

All notable changes to `mcp-server-falkordb` are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-04-16

### Added

First public release. Initial six-tool MCP server for [FalkorDB](https://falkordb.com/).

- `graph_list` — enumerate all graphs in the database
- `graph_describe` — full schema (labels, relationship types, property keys) with per-label counts
- `graph_query` — read-only Cypher execution with client-side write-keyword guard and server-side `ro_query` enforcement
- `graph_mutate` — write Cypher execution with parameterized-query support
- `graph_explore` — one-call schema + sample nodes + sample edges for fast orientation
- `graph_delete` — irreversible graph drop, requires explicit `confirm: true`

### Features

- **FastMCP**-based server with complete `ToolAnnotations` (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`)
- **Pydantic v2** input validation with `extra="forbid"` on every model
- **Parameterized Cypher** via `params` field on `graph_query` and `graph_mutate`
- **Query timeout** (30s default, `FALKORDB_QUERY_TIMEOUT_MS` override)
- **Non-fatal startup connection probe** with `WARNING` log on failure
- **Batched schema introspection** — label and relationship counts via `asyncio.gather` for 4-10× speedup on dense graphs
- **Response truncation** at 25,000 characters with actionable notice (suggests `LIMIT` refinement)
- **Defense-in-depth read-only validator** — handles string literals, backtick-quoted identifiers, block comments, line comments, mixed-case writes, and `CALL db.*` admin procedures
- **markdown** (default) and **json** output formats on all query/listing tools

### Tested

- 98 integration + unit tests passing
- mypy strict mode, zero errors
- ruff lint + format clean

### Requirements

- Python 3.12+
- `falkordb>=1.6.0`
- `mcp[cli]>=1.27.0`

[Unreleased]: https://github.com/rbarrielabrystech/mcp-server-falkordb/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/rbarrielabrystech/mcp-server-falkordb/releases/tag/v0.1.0

# mcp-server-falkordb

MCP server for [FalkorDB](https://falkordb.com/) — a property graph database built on Redis. Exposes 6 agent-centric tools for graph query, schema inspection, and management.

## Tools

| Tool | Purpose | Destructive? |
|------|---------|--------------|
| `graph_list` | List all graphs with names | No |
| `graph_describe` | Full schema: labels, rel types, property keys, counts | No |
| `graph_query` | Execute read-only Cypher (write keywords rejected) | No |
| `graph_mutate` | Execute write Cypher (CREATE, MERGE, SET, DELETE, REMOVE) | Yes |
| `graph_explore` | One-call overview: schema + 3 sample nodes + 3 sample edges | No |
| `graph_delete` | Drop an entire graph (requires `confirm: true`) | Yes — irreversible |

**Not in v1** (by design):
- No direct node/edge CRUD — Cypher via `graph_mutate` is more powerful and honest
- No index management — advanced, add via `graph_mutate` when needed
- No backup/restore — use `docker exec` + RDB snapshots

## Installation

### Requirements

- Python 3.12+
- `uv` package manager
- Running FalkorDB instance (default: `localhost:6379`)

### Local (rmcp-mux)

1. Add to `~/dev/mcp-mux-daemon/mux.toml`:

```toml
[servers.falkordb-hive]
socket = "~/mcp-sockets/falkordb-hive.sock"
cmd = "uv"
args = ["--directory", "/Users/rob/dev/tools/mcp-server-falkordb", "run", "mcp-server-falkordb"]
env = { FALKORDB_HOST = "localhost", FALKORDB_PORT = "6379" }
lazy_start = true
max_restarts = 20
```

2. Restart the mux daemon:
```bash
launchctl kickstart -k gui/$(id -u)/com.labrys.mcp-mux
```

3. Add to Claude Code:
```bash
claude mcp add --scope user falkordb-hive -- rmcp-mux-proxy --socket ~/mcp-sockets/falkordb-hive.sock
```

4. Verify:
```bash
claude mcp list | grep falkordb-hive
```

### Direct (without rmcp-mux)

```bash
uv --directory /path/to/mcp-server-falkordb run mcp-server-falkordb
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `FALKORDB_HOST` | `localhost` | FalkorDB host |
| `FALKORDB_PORT` | `6379` | FalkorDB port |
| `FALKORDB_PASSWORD` | _(none)_ | Redis AUTH password (optional) |

## Usage Examples

### Explore a graph

```
graph_explore(graph="hive_hive")
```

Returns labels, relationship types, property keys with counts, plus sample nodes and edges.

### Query data

```
graph_query(
  graph="hive_hive",
  query="MATCH (n:Memory) RETURN n.content LIMIT 10"
)
```

Write keywords (CREATE, DELETE, SET, MERGE, REMOVE, DROP) are rejected — use `graph_mutate`.

### Write data

```
graph_mutate(
  graph="hive_hive",
  query="CREATE (n:Note {content: 'Remember this', created: '2026-04-15'})"
)
```

### Delete a graph

```
graph_delete(graph="my_temp_graph", confirm=true)
```

`confirm` must be `true` — this is irreversible.

## Response Formats

All listing and query tools support `format: "markdown"` (default) or `format: "json"`.

- **markdown**: Human-readable tables and lists, good for agent reasoning
- **json**: Machine-readable, good for programmatic processing

## Read-Only Enforcement

`graph_query` enforces read-only semantics before the query reaches FalkorDB:

1. Strips string literals (prevents false positives on keywords in strings)
2. Regex-checks for write keywords: `CREATE`, `DELETE`, `SET`, `MERGE`, `REMOVE`, `DROP`
3. Checks for write/admin `CALL db.*` procedures

If a write keyword is detected, the error message explicitly directs to `graph_mutate`.

## Development

```bash
# Install deps
uv sync

# Run tests (requires live FalkorDB at localhost:6379)
uv run pytest

# Type check
uv run mypy src/

# Lint
uv run ruff check src/ tests/
```

Tests use ephemeral graphs with the `_test_mcp_` prefix. The `hive_*` production graphs are never touched.

## Architecture

```
src/mcp_server_falkordb/
├── __main__.py     Entry point
├── server.py       FastMCP app + 6 tool registrations
├── client.py       Async FalkorDB connection (lifespan-managed)
├── validators.py   Cypher read-only enforcement + graph name validation
└── formatters.py   Markdown/JSON output + CHARACTER_LIMIT truncation
```

## License

MIT — Copyright (c) 2026 Labrys Technology

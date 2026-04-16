# mcp-server-falkordb

[![PyPI version](https://img.shields.io/pypi/v/mcp-server-falkordb.svg)](https://pypi.org/project/mcp-server-falkordb/)
[![Python versions](https://img.shields.io/pypi/pyversions/mcp-server-falkordb.svg)](https://pypi.org/project/mcp-server-falkordb/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-compatible-blue.svg)](https://modelcontextprotocol.io/)

MCP server for [FalkorDB](https://falkordb.com/) — a property graph database built on Redis. Connects LLM agents (Claude, or any MCP client) to a running FalkorDB instance via 6 agent-centric tools covering graph discovery, read queries, writes, and schema inspection.

## Quick Start

One-block install + first call:

```bash
# 1. Start FalkorDB (if not already running)
docker run -d -p 6379:6379 falkordb/falkordb

# 2. Register the MCP in Claude Code
claude mcp add falkordb -- uvx mcp-server-falkordb

# 3. From your agent: explore a graph
# (Claude will call: graph_explore(graph="my_graph"))
```

That's it. Six graph tools now available to any MCP-compatible agent.

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
- Running FalkorDB instance (default: `localhost:6379`)

### Claude Desktop / Claude Code (uvx — recommended)

Add to your `claude_desktop_config.json` (or Claude Code MCP config):

```json
{
  "mcpServers": {
    "falkordb": {
      "command": "uvx",
      "args": ["mcp-server-falkordb"],
      "env": {
        "FALKORDB_HOST": "localhost",
        "FALKORDB_PORT": "6379"
      }
    }
  }
}
```

Or add via CLI:
```bash
claude mcp add falkordb -- uvx mcp-server-falkordb
```

To specify a custom host/port via CLI:
```bash
claude mcp add falkordb --env FALKORDB_HOST=localhost --env FALKORDB_PORT=6379 -- uvx mcp-server-falkordb
```

If `FALKORDB_HOST` and `FALKORDB_PORT` are omitted, they default to `localhost:6379`.

### pip

```bash
pip install mcp-server-falkordb
mcp-server-falkordb   # starts on stdio
```

### From source

```bash
git clone https://github.com/rbarrielabrystech/mcp-server-falkordb
cd mcp-server-falkordb
uv run mcp-server-falkordb
```

<details>
<summary>Advanced: custom MCP multiplexer (rmcp-mux)</summary>

1. Add to your `mux.toml`:

```toml
[servers.falkordb]
socket = "~/mcp-sockets/falkordb.sock"
cmd = "uv"
args = ["--directory", "/path/to/mcp-server-falkordb", "run", "mcp-server-falkordb"]
env = { FALKORDB_HOST = "localhost", FALKORDB_PORT = "6379" }
lazy_start = true
max_restarts = 20
```

2. Restart the mux daemon and register with your MCP client:
```bash
claude mcp add --scope user falkordb -- rmcp-mux-proxy --socket ~/mcp-sockets/falkordb.sock
```

</details>

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `FALKORDB_HOST` | `localhost` | FalkorDB host |
| `FALKORDB_PORT` | `6379` | FalkorDB port |
| `FALKORDB_PASSWORD` | _(none)_ | Redis AUTH password (optional) |
| `FALKORDB_QUERY_TIMEOUT_MS` | `30000` | Query timeout in milliseconds (0 = no timeout) |

## Usage Examples

### Explore a graph

```
graph_explore(graph="my_graph")
```

Returns labels, relationship types, property keys with counts, plus sample nodes and edges.

### Query data

```
graph_query(
  graph="my_graph",
  query="MATCH (n:Memory) RETURN n.content LIMIT 10"
)
```

Write keywords (CREATE, DELETE, SET, MERGE, REMOVE, DROP) are rejected — use `graph_mutate`.

### Parameterized query

```
graph_query(
  graph="my_graph",
  query="MATCH (n:Person {name: $name}) RETURN n",
  params={"name": "Alice"}
)
```

### Write data

```
graph_mutate(
  graph="my_graph",
  query="CREATE (n:Note {content: $content, created: $date})",
  params={"content": "Remember this", "date": "2026-04-16"}
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

1. Strips string literals and backtick-quoted identifiers (prevents false positives on keywords in strings and labels)
2. Regex-checks for write keywords: `CREATE`, `DELETE`, `SET`, `MERGE`, `REMOVE`, `DROP`
3. Checks for write/admin `CALL db.*` procedures

If a write keyword is detected, the error message explicitly directs to `graph_mutate`. The authoritative read-only gate is FalkorDB's server-side `ro_query` mode — the client-side regex is defense-in-depth to avoid unnecessary round-trips.

## Troubleshooting

### FalkorDB not running

**Symptom**: first tool call returns a connection refused error.

**Fix**: start FalkorDB with Docker:
```bash
docker run -p 6379:6379 falkordb/falkordb
```

### Wrong host or port

Set `FALKORDB_HOST` and `FALKORDB_PORT` environment variables (see [Configuration](#configuration) above).

### Password-protected FalkorDB

Set `FALKORDB_PASSWORD` to your Redis AUTH password. The server passes it transparently to the FalkorDB client.

### Graph name with special characters

FalkorDB graph names support alphanumeric characters, underscores (`_`), and hyphens (`-`). Names with other special characters will be rejected with a `GraphNameError` before the query reaches the database.

### Large result sets

All tools truncate responses at 25,000 characters and append a notice. Add a `LIMIT` clause to your Cypher query or use the `format: "json"` output to reduce payload size.

### Query timing out

The default query timeout is 30 seconds. For longer-running analytical queries, increase it via `FALKORDB_QUERY_TIMEOUT_MS=60000` (or whatever millisecond value suits).

## Development

```bash
# Install deps
uv sync

# Run tests (requires live FalkorDB at localhost:6379)
uv run pytest

# Type check
uv run mypy src/

# Lint + format
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

All tests use ephemeral graphs with a unique `_test_mcp_<uuid>` prefix. No pre-existing graph in your FalkorDB instance is ever touched.

## Architecture

```
src/mcp_server_falkordb/
├── __main__.py     Entry point
├── server.py       FastMCP app + 6 tool registrations
├── client.py       Async FalkorDB connection (lifespan-managed)
├── validators.py   Cypher read-only enforcement + graph name validation
└── formatters.py   Markdown/JSON output + CHARACTER_LIMIT truncation
```

## Contributing

Contributions welcome! Please:

1. Open an issue describing what you want to change before starting work
2. Fork the repo, create a feature branch
3. Add tests for any new behavior
4. Run the full gate locally before opening a PR: `uv run pytest && uv run mypy src/ && uv run ruff check src/ tests/`
5. PRs should target `main` with a clear title and description

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

## Acknowledgments

- **[FalkorDB](https://falkordb.com/)** — the graph database this server targets. FalkorDB is a fork of RedisGraph maintained by the original team.
- **[falkordb-py](https://github.com/FalkorDB/falkordb-py)** — the Python client used under the hood.
- **[Model Context Protocol](https://modelcontextprotocol.io/)** — the protocol spec and Python SDK that make agent-tool integration possible.
- **[FastMCP](https://github.com/jlowin/fastmcp)** — the Python framework this server uses.

## License

MIT — see [LICENSE](LICENSE).

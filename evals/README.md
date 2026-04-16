# FalkorDB MCP Server Evaluations

## Eval graph: `eval_data`

The evaluations in `falkordb.xml` run against a pre-seeded FalkorDB graph
called `eval_data`. This graph contains **synthetic** data only -- no real
project names or identifying information.

### Seed the graph

```bash
uv run python evals/seed_eval_data.py          # default localhost:6379
```

Or with a custom connection:

```bash
FALKORDB_HOST=10.0.0.1 FALKORDB_PORT=6379 uv run python evals/seed_eval_data.py
```

### Data shape

| Category       | Count | Details |
|----------------|-------|---------|
| Agent nodes    | 5     | python-pro (42 tasks), security-auditor (17), database-optimizer (8), fastapi-expert (23), test-writer (5) |
| Skill nodes    | 5     | test-driven-development (150 uses), code-review (89), dependency-check (34), mcp-builder (12), diagram (7) |
| Project nodes  | 3     | alpha-service (python), beta-frontend (dart), gamma-tools (python) |
| USES edges     | 4     | python-pro->tdd, python-pro->code-review, security-auditor->dependency-check, fastapi-expert->tdd |
| WORKS_ON edges | 3     | python-pro->alpha-service, security-auditor->alpha-service, test-writer->beta-frontend |

**Total: 13 nodes, 7 relationships.**

### Re-seeding

The seed script drops the existing `eval_data` graph before recreating it.
Safe to re-run at any time.

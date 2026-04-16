# Contributing to mcp-server-falkordb

Thanks for considering a contribution! This project is small and focused — clarity and quality matter more than volume.

## Before you start

- **Open an issue first** for anything beyond a typo fix. A 2-line issue describing what you want to change saves both of us a round-trip.
- **Check existing issues + PRs** to avoid duplicating work.

## Development setup

Requirements: Python 3.12+, a running FalkorDB instance (for integration tests), and [uv](https://github.com/astral-sh/uv).

```bash
git clone https://github.com/rbarrielabrystech/mcp-server-falkordb
cd mcp-server-falkordb
uv sync
```

Start FalkorDB locally if you don't have one running:

```bash
docker run -d -p 6379:6379 falkordb/falkordb
```

## Running the full gate

Every PR must pass all of these before review:

```bash
uv run pytest              # 98+ tests, requires live FalkorDB at localhost:6379
uv run mypy src/           # strict mode, zero errors
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```

If you add new behavior, add tests. If you add new tools, add tests covering:
- Happy path
- Error path (raise from underlying client, expect friendly error string)
- Input validation edge cases (Pydantic model rejection)

## Tests

- **Integration tests** live in `tests/` and hit a real FalkorDB. They use ephemeral graphs with a unique `_test_mcp_<uuid>` prefix — your own data is never touched.
- **Unit tests** live in `tests/unit/` and run without a database.

Integration tests are slow enough to be visible; unit tests are fast. Prefer unit tests where possible.

## Code style

- **Type hints required** — mypy strict mode is enabled
- **No `Any` escapes** unless truly necessary, and documented why
- **Pydantic v2** for all input models with `ConfigDict(extra="forbid")`
- **Async throughout** — every I/O operation uses `async`/`await`
- **Docstrings** on every public function, Google-style with examples where helpful

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat(scope): add new thing`
- `fix(scope): correct broken behavior`
- `docs(scope): update documentation`
- `test(scope): expand test coverage`
- `refactor(scope): improve structure, no behavior change`
- `perf(scope): optimization with measurable impact`

Keep commits focused. One logical change per commit.

## Pull requests

1. Fork the repo and create a feature branch off `main`
2. Make your changes with tests
3. Run the full gate (see above)
4. Open a PR with:
   - Clear title describing the change
   - Description explaining *why* (not just *what* — the diff shows that)
   - Link to the issue it addresses

## Reporting bugs

Open a GitHub issue with:
- What you ran (MCP client, command, query)
- What you expected
- What happened (paste the error message + stack if you have one)
- Your FalkorDB version (`docker inspect falkordb/falkordb` or equivalent)
- Your Python version

## Proposing new tools

The 6-tool surface is intentionally minimal. Before proposing a 7th:
- Can the desired workflow be accomplished with `graph_mutate` + Cypher?
- Is this genuinely general-purpose (useful to >50% of users) or specific to your workflow?
- Does it fit the agent-centric design (one call does one useful thing)?

If the answer is "yes" to all three, open an issue to discuss.

## Security

If you find a security issue — a way to bypass the read-only enforcement in `graph_query`, a Cypher injection vector, or anything else — please **do not** open a public issue. Email the maintainer (contact via the GitHub profile) or use GitHub's security advisory feature.

## License

By contributing, you agree that your contributions will be licensed under the project's MIT License.

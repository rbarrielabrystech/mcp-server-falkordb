"""Cypher query validation and graph name guards.

Read-only enforcement: rejects write-Cypher keywords before the query
reaches FalkorDB. Uses regex-based detection on the query text after
stripping string literals to avoid false positives on keyword-in-string.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class CypherWriteError(ValueError):
    """Raised when a write-Cypher keyword is detected in a read-only context."""


class GraphNameError(ValueError):
    """Raised when a graph name fails validation."""


# ---------------------------------------------------------------------------
# Write-keyword detection
# ---------------------------------------------------------------------------

# These keywords, when appearing as standalone tokens (word-boundary delimited),
# indicate write operations.  We check AFTER stripping string literals so that
# "CREATE is a keyword" inside a string value does not trigger rejection.
_WRITE_KEYWORDS: list[str] = [
    "CREATE",
    "DELETE",
    "SET",
    "MERGE",
    "REMOVE",
    "DROP",
]

# Compiled pattern: any write keyword as a whole token (case-insensitive)
_WRITE_PATTERN: re.Pattern[str] = re.compile(
    r"\b(?:" + "|".join(_WRITE_KEYWORDS) + r")\b",
    re.IGNORECASE,
)

# Secondary pattern: CALL db.* procedures that perform write/admin operations.
# FalkorDB uses camelCase procedure names like db.createIndex, db.dropIndex.
_WRITE_PROCEDURE_PATTERN: re.Pattern[str] = re.compile(
    r"\bCALL\s+db\.\w*(create|drop|delete|set|remove)\w*",
    re.IGNORECASE,
)

# Pattern to strip single-quoted and double-quoted string literals from a query
# so that keywords embedded in strings don't cause false positives.
_STRING_LITERAL_PATTERN: re.Pattern[str] = re.compile(
    r"'[^'\\]*(?:\\.[^'\\]*)*'|\"[^\"\\]*(?:\\.[^\"\\]*)*\"",
    re.DOTALL,
)


def _strip_string_literals(query: str) -> str:
    """Replace all string literals in *query* with empty placeholders."""
    return _STRING_LITERAL_PATTERN.sub("''", query)


def validate_read_only_query(query: str) -> None:
    """Assert that *query* contains no write-Cypher keywords.

    Raises:
        CypherWriteError: if a write keyword is detected, with a hint to use
            the ``graph_mutate`` tool instead.
    """
    sanitised = _strip_string_literals(query)
    match = _WRITE_PATTERN.search(sanitised)
    if match:
        keyword = match.group(0).upper()
        raise CypherWriteError(
            f"Query contains write keyword '{keyword}' which is not allowed in "
            f"graph_query (read-only). Use graph_mutate to execute write queries."
        )
    proc_match = _WRITE_PROCEDURE_PATTERN.search(sanitised)
    if proc_match:
        raise CypherWriteError(
            f"Query calls a write/admin procedure ('{proc_match.group(0)}') which is not "
            f"allowed in graph_query (read-only). Use graph_mutate to execute write queries."
        )


# ---------------------------------------------------------------------------
# Graph name validation
# ---------------------------------------------------------------------------

_MAX_GRAPH_NAME_LEN = 200


def validate_graph_name(name: str) -> None:
    """Assert that *name* is a valid non-empty graph name.

    Raises:
        GraphNameError: if the name is empty, blank, or exceeds the maximum length.
    """
    if not name or not name.strip():
        raise GraphNameError("Graph name must not be empty or blank.")
    if len(name) > _MAX_GRAPH_NAME_LEN:
        raise GraphNameError(
            f"Graph name is too long ({len(name)} chars, max {_MAX_GRAPH_NAME_LEN})."
        )

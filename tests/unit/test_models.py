"""Unit tests for Pydantic model validation in server.py input models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from mcp_server_falkordb.server import (
    GraphDeleteInput,
    GraphDescribeInput,
    GraphExploreInput,
    GraphListInput,
    GraphMutateInput,
    GraphQueryInput,
)


class TestExtraForbid:
    """All input models must reject unknown fields (extra='forbid')."""

    def test_graph_list_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError):
            GraphListInput(unknown_field="oops")  # type: ignore[call-arg]

    def test_graph_describe_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError):
            GraphDescribeInput(graph="test", unknown_field="oops")  # type: ignore[call-arg]

    def test_graph_query_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError):
            GraphQueryInput(  # type: ignore[call-arg]
                graph="test", query="MATCH (n) RETURN n", unknown_field="oops"
            )

    def test_graph_mutate_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError):
            GraphMutateInput(  # type: ignore[call-arg]
                graph="test", query="CREATE (n:Foo)", unknown_field="oops"
            )

    def test_graph_explore_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError):
            GraphExploreInput(graph="test", unknown_field="oops")  # type: ignore[call-arg]

    def test_graph_delete_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError):
            GraphDeleteInput(graph="test", unknown_field="oops")  # type: ignore[call-arg]


class TestGraphFieldConstraints:
    """graph field: min_length=1, max_length=200."""

    def test_empty_graph_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GraphDescribeInput(graph="")

    def test_graph_name_too_long_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GraphDescribeInput(graph="a" * 201)

    def test_graph_name_at_max_length_accepted(self) -> None:
        model = GraphDescribeInput(graph="a" * 200)
        assert len(model.graph) == 200

    def test_whitespace_only_graph_name_trimmed_and_rejected(self) -> None:
        # str_strip_whitespace=True trims; then min_length=1 rejects empty
        with pytest.raises(ValidationError):
            GraphDescribeInput(graph="   ")


class TestParamsField:
    """params: dict[str, Any] | None — added in C1."""

    def test_params_defaults_to_none(self) -> None:
        model = GraphQueryInput(graph="test", query="MATCH (n) RETURN n")
        assert model.params is None

    def test_params_accepts_dict(self) -> None:
        model = GraphQueryInput(
            graph="test",
            query="MATCH (n:Person {name: $name}) RETURN n",
            params={"name": "Alice"},
        )
        assert model.params == {"name": "Alice"}

    def test_params_accepts_none_explicitly(self) -> None:
        model = GraphQueryInput(graph="test", query="MATCH (n) RETURN n", params=None)
        assert model.params is None

    def test_mutate_params_accepts_dict(self) -> None:
        model = GraphMutateInput(
            graph="test",
            query="CREATE (n:Person {name: $name})",
            params={"name": "Bob"},
        )
        assert model.params == {"name": "Bob"}

    def test_params_rejects_list(self) -> None:
        with pytest.raises(ValidationError):
            GraphQueryInput(
                graph="test",
                query="MATCH (n) RETURN n",
                params=["not", "a", "dict"],  # type: ignore[arg-type]
            )

    def test_params_rejects_string(self) -> None:
        with pytest.raises(ValidationError):
            GraphQueryInput(
                graph="test",
                query="MATCH (n) RETURN n",
                params="not a dict",  # type: ignore[arg-type]
            )

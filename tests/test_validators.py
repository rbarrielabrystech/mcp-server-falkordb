"""Tests for Cypher read-only validation and query guards."""

import pytest

from mcp_server_falkordb.validators import (
    CypherWriteError,
    GraphNameError,
    validate_graph_name,
    validate_read_only_query,
)


class TestReadOnlyQueryValidation:
    """Cypher read-only enforcement."""

    def test_match_query_is_allowed(self) -> None:
        validate_read_only_query("MATCH (n) RETURN n")

    def test_match_with_where_is_allowed(self) -> None:
        validate_read_only_query("MATCH (n:Person) WHERE n.age > 30 RETURN n.name")

    def test_call_labels_is_allowed(self) -> None:
        validate_read_only_query("CALL db.labels() YIELD label RETURN label")

    def test_call_relationship_types_is_allowed(self) -> None:
        q = "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
        validate_read_only_query(q)

    def test_unwind_is_allowed(self) -> None:
        validate_read_only_query("UNWIND range(1,5) AS x RETURN x")

    def test_with_is_allowed(self) -> None:
        validate_read_only_query("MATCH (n) WITH n RETURN n")

    def test_create_is_rejected(self) -> None:
        with pytest.raises(CypherWriteError, match="graph_mutate"):
            validate_read_only_query("CREATE (n:Person {name: 'Alice'})")

    def test_create_lowercase_is_rejected(self) -> None:
        with pytest.raises(CypherWriteError):
            validate_read_only_query("create (n) return n")

    def test_delete_is_rejected(self) -> None:
        with pytest.raises(CypherWriteError, match="graph_mutate"):
            validate_read_only_query("MATCH (n) DELETE n")

    def test_set_is_rejected(self) -> None:
        with pytest.raises(CypherWriteError):
            validate_read_only_query("MATCH (n) SET n.age = 30")

    def test_merge_is_rejected(self) -> None:
        with pytest.raises(CypherWriteError):
            validate_read_only_query("MERGE (n:Person {name: 'Alice'})")

    def test_remove_is_rejected(self) -> None:
        with pytest.raises(CypherWriteError):
            validate_read_only_query("MATCH (n) REMOVE n.age")

    def test_drop_is_rejected(self) -> None:
        with pytest.raises(CypherWriteError):
            validate_read_only_query("CALL db.idx.drop('Person', 'age')")

    def test_call_db_create_index_is_rejected(self) -> None:
        with pytest.raises(CypherWriteError):
            validate_read_only_query("CALL db.createIndex('Person', ['name'])")

    def test_create_in_string_value_is_allowed(self) -> None:
        """'CREATE' inside a string literal should not trigger rejection."""
        validate_read_only_query("MATCH (n) WHERE n.text = 'CREATE is a keyword' RETURN n")

    def test_set_in_string_value_is_allowed(self) -> None:
        validate_read_only_query("MATCH (n) WHERE n.description = 'SET this value' RETURN n")

    def test_match_then_create_on_newline_is_rejected(self) -> None:
        query = "MATCH (n)\nCREATE (m:Foo)"
        with pytest.raises(CypherWriteError):
            validate_read_only_query(query)

    def test_backtick_label_containing_create_is_allowed(self) -> None:
        """Label named CREATE (backtick-quoted) must not trigger rejection."""
        validate_read_only_query("MATCH (n:`CREATE`) RETURN n")

    def test_backtick_label_containing_delete_is_allowed(self) -> None:
        """Label named DELETE (backtick-quoted) must not trigger rejection."""
        validate_read_only_query("MATCH (n:`DELETE`) RETURN n")

    def test_backtick_label_with_keyword_suffix_is_allowed(self) -> None:
        """Label CREATE_COOL is a valid backtick-quoted identifier, not a write op."""
        validate_read_only_query("MATCH (n:`CREATE_COOL`) RETURN n")


class TestGraphNameValidation:
    """Graph name validation."""

    def test_valid_graph_name(self) -> None:
        validate_graph_name("my_graph")

    def test_hive_graph_passes(self) -> None:
        validate_graph_name("hive_hive")

    def test_empty_name_is_rejected(self) -> None:
        with pytest.raises(GraphNameError):
            validate_graph_name("")

    def test_name_with_only_spaces_is_rejected(self) -> None:
        with pytest.raises(GraphNameError):
            validate_graph_name("   ")

    def test_name_too_long_is_rejected(self) -> None:
        with pytest.raises(GraphNameError):
            validate_graph_name("a" * 201)

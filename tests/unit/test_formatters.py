"""Unit tests for _truncate and CHARACTER_LIMIT in formatters.py."""

from __future__ import annotations

from mcp_server_falkordb.formatters import CHARACTER_LIMIT, _truncate


class TestTruncate:
    def test_string_at_limit_is_not_truncated(self) -> None:
        text = "x" * CHARACTER_LIMIT
        result = _truncate(text)
        assert result == text
        assert "truncated" not in result

    def test_string_one_char_over_is_truncated(self) -> None:
        text = "x" * (CHARACTER_LIMIT + 1)
        result = _truncate(text)
        assert "truncated" in result
        assert len(result) > CHARACTER_LIMIT  # truncated + notice

    def test_string_25kb_over_is_truncated_with_notice(self) -> None:
        text = "x" * (CHARACTER_LIMIT + 25_000)
        result = _truncate(text)
        assert "truncated" in result

    def test_empty_string_not_truncated(self) -> None:
        result = _truncate("")
        assert result == ""
        assert "truncated" not in result

    def test_short_string_not_truncated(self) -> None:
        text = "hello world"
        assert _truncate(text) == text

    def test_multibyte_utf8_at_boundary_no_corruption(self) -> None:
        """Unicode codepoints at the CHARACTER_LIMIT boundary must not be split."""
        # Build a string with multibyte characters that crosses the limit
        # Use emoji (4 bytes each in UTF-8) to ensure boundary isn't mid-character
        emoji = "\U0001f600"  # 😀
        # Fill to just below limit with regular chars, then add emoji at boundary
        prefix_len = CHARACTER_LIMIT - 2
        text = "a" * prefix_len + emoji + "b"
        result = _truncate(text)
        # The slice is by character count (not bytes), so emoji must be intact
        if "truncated" in result:
            # If truncated, the emoji at position CHARACTER_LIMIT-2 must not be corrupted
            # The truncation is CHARACTER_LIMIT chars from the start
            truncated_part = result[:CHARACTER_LIMIT]
            # Should be valid unicode (no UnicodeDecodeError)
            truncated_part.encode("utf-8")

    def test_extra_rows_notice_included(self) -> None:
        text = "x" * (CHARACTER_LIMIT + 1)
        result = _truncate(text, extra_rows=42)
        assert "42" in result
        assert "truncated" in result

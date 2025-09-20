from __future__ import annotations

import re
from collections.abc import Iterator

from re_static.re_static import StaticRegex
from re_static.types import SENTINEL


class TestEmailRegex(StaticRegex):
    REGEX = r"(?P<username>[a-zA-Z0-9._%+-]+)@(?P<domain>[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"


class TestDigitsRegex(StaticRegex):
    REGEX = r"(?P<digits>\d+)"


class TestOptionalGroupRegex(StaticRegex):
    REGEX = r"(?P<required>[a-z]+)(?P<optional>[0-9]*)?"


class TestMultipleGroupsRegex(StaticRegex):
    REGEX = r"(?P<first>\w+)\s+(?P<second>\w+)\s*(?P<third>\w+)?"


class TestStaticRegexInitSubclass:
    def test_regex_compiled_on_subclass_creation(self):
        class TestRegex(StaticRegex):
            REGEX = r"\d+"

        assert hasattr(TestRegex, "REGEX_COMPILED")
        assert isinstance(TestRegex.REGEX_COMPILED, re.Pattern)
        assert TestRegex.REGEX_COMPILED.pattern == r"\d+"

    def test_regex_flags_applied(self):
        class TestRegexWithFlags(StaticRegex):
            REGEX = r"test"
            REGEX_FLAGS = re.IGNORECASE

        assert TestRegexWithFlags.REGEX_COMPILED.flags & re.IGNORECASE

    def test_no_regex_defined_no_compilation(self):
        class TestRegexNoPattern(StaticRegex):
            pass

        # Should not have REGEX_COMPILED if REGEX is not defined
        assert not hasattr(TestRegexNoPattern, "REGEX_COMPILED")


class TestGetSingle:
    def test_get_single_with_match(self):
        def producer():
            match = re.match(TestEmailRegex.REGEX, "test@example.com")
            return match

        result = TestEmailRegex._get_single(producer)

        assert result is not None
        assert isinstance(result, TestEmailRegex)
        assert result.username == "test"
        assert result.domain == "example.com"

    def test_get_single_with_no_match(self):
        def producer():
            return None

        result = TestEmailRegex._get_single(producer)
        assert result is None

    def test_get_single_sets_attributes_from_groupdict(self):
        def producer():
            return re.match(TestDigitsRegex.REGEX, "12345")

        result = TestDigitsRegex._get_single(producer)

        assert result is not None
        assert result.digits == "12345"


class TestGetIterator:
    def test_get_iterator_with_multiple_matches(self):
        def producer():
            return re.finditer(TestDigitsRegex.REGEX, "123 456 789")

        results = list(TestDigitsRegex._get_iterator(producer))

        assert len(results) == 3
        assert all(isinstance(result, TestDigitsRegex) for result in results)
        assert results[0].digits == "123"
        assert results[1].digits == "456"
        assert results[2].digits == "789"

    def test_get_iterator_with_no_matches(self):
        def producer():
            return re.finditer(TestDigitsRegex.REGEX, "no digits here")

        results = list(TestDigitsRegex._get_iterator(producer))
        assert len(results) == 0

    def test_get_iterator_returns_iterator(self):
        def producer():
            return re.finditer(TestDigitsRegex.REGEX, "123")

        result = TestDigitsRegex._get_iterator(producer)
        assert isinstance(result, Iterator)


class TestMatchMethod:
    def test_match_success(self):
        result = TestEmailRegex.match("test@example.com")

        assert result is not None
        assert isinstance(result, TestEmailRegex)
        assert result.username == "test"
        assert result.domain == "example.com"

    def test_match_failure(self):
        result = TestEmailRegex.match("invalid-email")
        assert result is None

    def test_match_with_pos(self):
        result = TestDigitsRegex.match("abc123", pos=3)

        assert result is not None
        assert result.digits == "123"

    def test_match_with_endpos(self):
        result = TestDigitsRegex.match("12345", endpos=3)

        assert result is not None
        assert result.digits == "123"

    def test_match_with_pos_and_endpos(self):
        result = TestDigitsRegex.match("abc123def", pos=3, endpos=6)

        assert result is not None
        assert result.digits == "123"

    def test_match_with_sentinel_defaults(self):
        # Should work the same as without pos/endpos
        result = TestEmailRegex.match("test@example.com", SENTINEL, SENTINEL)

        assert result is not None
        assert result.username == "test"
        assert result.domain == "example.com"


class TestSearchMethod:
    def test_search_success(self):
        result = TestEmailRegex.search("Contact us at test@example.com for help")

        assert result is not None
        assert isinstance(result, TestEmailRegex)
        assert result.username == "test"
        assert result.domain == "example.com"

    def test_search_failure(self):
        result = TestEmailRegex.search("No email address here")
        assert result is None

    def test_search_finds_first_match(self):
        result = TestDigitsRegex.search("abc123def456")

        assert result is not None
        assert result.digits == "123"

    def test_search_with_pos(self):
        result = TestDigitsRegex.search("123abc456", pos=6)

        assert result is not None
        assert result.digits == "456"

    def test_search_with_endpos(self):
        result = TestDigitsRegex.search("123abc456", endpos=3)

        assert result is not None
        assert result.digits == "123"


class TestFullmatchMethod:
    def test_fullmatch_success(self):
        result = TestEmailRegex.fullmatch("test@example.com")

        assert result is not None
        assert isinstance(result, TestEmailRegex)
        assert result.username == "test"
        assert result.domain == "example.com"

    def test_fullmatch_failure_partial_match(self):
        result = TestEmailRegex.fullmatch("test@example.com and more text")
        assert result is None

    def test_fullmatch_failure_no_match(self):
        result = TestEmailRegex.fullmatch("not an email")
        assert result is None

    def test_fullmatch_with_pos_and_endpos(self):
        result = TestDigitsRegex.fullmatch("abc123def", pos=3, endpos=6)

        assert result is not None
        assert result.digits == "123"


class TestFindallMethod:
    def test_findall_multiple_matches(self):
        results = TestDigitsRegex.findall("123 abc 456 def 789")

        assert len(results) == 3
        assert all(isinstance(result, TestDigitsRegex) for result in results)
        assert results[0].digits == "123"
        assert results[1].digits == "456"
        assert results[2].digits == "789"

    def test_findall_no_matches(self):
        results = TestDigitsRegex.findall("no numbers here")
        assert len(results) == 0
        assert isinstance(results, list)

    def test_findall_single_match(self):
        results = TestDigitsRegex.findall("only 123 here")

        assert len(results) == 1
        assert results[0].digits == "123"

    def test_findall_with_pos(self):
        results = TestDigitsRegex.findall("123 456 789", pos=4)

        assert len(results) == 2
        assert results[0].digits == "456"
        assert results[1].digits == "789"

    def test_findall_with_endpos(self):
        results = TestDigitsRegex.findall("123 456 789", endpos=7)

        assert len(results) == 2
        assert results[0].digits == "123"
        assert results[1].digits == "456"


class TestFinditerMethod:
    def test_finditer_multiple_matches(self):
        results = list(TestDigitsRegex.finditer("123 abc 456 def 789"))

        assert len(results) == 3
        assert all(isinstance(result, TestDigitsRegex) for result in results)
        assert results[0].digits == "123"
        assert results[1].digits == "456"
        assert results[2].digits == "789"

    def test_finditer_returns_iterator(self):
        result = TestDigitsRegex.finditer("123")
        assert isinstance(result, Iterator)

    def test_finditer_no_matches(self):
        results = list(TestDigitsRegex.finditer("no numbers here"))
        assert len(results) == 0

    def test_finditer_with_pos_and_endpos(self):
        results = list(TestDigitsRegex.finditer("123 456 789", pos=4, endpos=7))

        assert len(results) == 1
        assert results[0].digits == "456"


class TestComplexRegexPatterns:
    def test_multiple_groups_all_present(self):
        result = TestMultipleGroupsRegex.match("hello world test")

        assert result is not None
        assert result.first == "hello"
        assert result.second == "world"
        assert result.third == "test"

    def test_multiple_groups_optional_missing(self):
        result = TestMultipleGroupsRegex.match("hello world")

        assert result is not None
        assert result.first == "hello"
        assert result.second == "world"
        # third group should be None or empty string depending on regex behavior
        assert hasattr(result, "third")

    def test_optional_group_present(self):
        result = TestOptionalGroupRegex.match("hello123")

        assert result is not None
        assert result.required == "hello"
        assert result.optional == "123"

    def test_optional_group_absent(self):
        result = TestOptionalGroupRegex.match("hello")

        assert result is not None
        assert result.required == "hello"
        # optional should be None or empty string
        assert hasattr(result, "optional")


class TestEdgeCases:
    def test_empty_string_input(self):
        result = TestDigitsRegex.match("")
        assert result is None

    def test_regex_with_no_named_groups(self):
        class NoGroupsRegex(StaticRegex):
            REGEX = r"\d+"

        result = NoGroupsRegex.match("123")
        assert result is not None
        # Should not have any attributes set

    def test_overlapping_matches_findall(self):
        class OverlapRegex(StaticRegex):
            REGEX = r"(?P<char>.)"

        results = OverlapRegex.findall("abc")

        assert len(results) == 3
        assert results[0].char == "a"
        assert results[1].char == "b"
        assert results[2].char == "c"

    def test_zero_pos_endpos(self):
        result = TestDigitsRegex.match("123", pos=0, endpos=0)
        assert result is None  # No characters to match

    def test_pos_greater_than_string_length(self):
        result = TestDigitsRegex.match("123", pos=10)
        assert result is None

    def test_endpos_less_than_pos(self):
        result = TestDigitsRegex.match("123", pos=2, endpos=1)
        assert result is None

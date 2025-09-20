from __future__ import annotations

from re_static.types import SENTINEL, MatchArgs, Sentinel, build_match_args


class TestSentinel:
    def test_sentinel_is_enum(self):
        assert isinstance(SENTINEL, Sentinel)
        assert SENTINEL == Sentinel.TOKEN

    def test_sentinel_equality(self):
        assert SENTINEL == SENTINEL
        assert SENTINEL != "some_string"
        assert SENTINEL != 42
        assert SENTINEL is not None

    def test_sentinel_uniqueness(self):
        assert SENTINEL is Sentinel.TOKEN
        assert id(SENTINEL) == id(Sentinel.TOKEN)


class TestBuildMatchArgs:
    def test_only_string_provided(self):
        result = build_match_args("test_string", SENTINEL, SENTINEL)
        expected: MatchArgs = {"string": "test_string"}
        assert result == expected

    def test_string_and_pos(self):
        result = build_match_args("test_string", 5, SENTINEL)
        expected: MatchArgs = {"string": "test_string", "pos": 5}
        assert result == expected

    def test_string_and_endpos(self):
        result = build_match_args("test_string", SENTINEL, 10)
        expected: MatchArgs = {"string": "test_string", "endpos": 10}
        assert result == expected

    def test_string_pos_and_endpos(self):
        result = build_match_args("test_string", 5, 10)
        expected: MatchArgs = {"string": "test_string", "pos": 5, "endpos": 10}
        assert result == expected

    def test_pos_zero_is_included(self):
        result = build_match_args("test_string", 0, SENTINEL)
        expected: MatchArgs = {"string": "test_string", "pos": 0}
        assert result == expected

    def test_endpos_zero_is_included(self):
        result = build_match_args("test_string", SENTINEL, 0)
        expected: MatchArgs = {"string": "test_string", "endpos": 0}
        assert result == expected

    def test_empty_string(self):
        result = build_match_args("", SENTINEL, SENTINEL)
        expected: MatchArgs = {"string": ""}
        assert result == expected

    def test_negative_pos(self):
        result = build_match_args("test_string", -1, SENTINEL)
        expected: MatchArgs = {"string": "test_string", "pos": -1}
        assert result == expected

    def test_negative_endpos(self):
        result = build_match_args("test_string", SENTINEL, -1)
        expected: MatchArgs = {"string": "test_string", "endpos": -1}
        assert result == expected

    def test_return_type_is_match_args(self):
        result = build_match_args("test", 1, 2)
        assert isinstance(result, dict)
        # Verify it has the correct keys for MatchArgs
        assert "string" in result
        assert result["string"] == "test"
        assert result.get("pos") == 1
        assert result.get("endpos") == 2


class TestMatchArgsTypedDict:
    def test_match_args_with_all_fields(self):
        args: MatchArgs = {"string": "test", "pos": 1, "endpos": 5}
        assert args["string"] == "test"
        assert args["pos"] == 1
        assert args["endpos"] == 5

    def test_match_args_string_only(self):
        args: MatchArgs = {"string": "test"}
        assert args["string"] == "test"
        assert "pos" not in args
        assert "endpos" not in args

    def test_match_args_with_pos_only(self):
        args: MatchArgs = {"string": "test", "pos": 3}
        assert args["string"] == "test"
        assert args["pos"] == 3
        assert "endpos" not in args

    def test_match_args_with_endpos_only(self):
        args: MatchArgs = {"string": "test", "endpos": 7}
        assert args["string"] == "test"
        assert args["endpos"] == 7
        assert "pos" not in args

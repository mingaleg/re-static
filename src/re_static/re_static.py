from __future__ import annotations

from abc import ABC
from collections.abc import Callable, Iterable, Iterator
from re import Match, Pattern
from re import compile as re_compile
from typing import ClassVar, Self

from re_static.types import SENTINEL, Sentinel, build_match_args


class StaticRegex(ABC):
    REGEX: ClassVar[str]
    REGEX_FLAGS: ClassVar[int] = 0
    REGEX_COMPILED: ClassVar[Pattern[str]]

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        if hasattr(cls, "REGEX"):
            cls.REGEX_COMPILED = re_compile(cls.REGEX, cls.REGEX_FLAGS)

    @classmethod
    def _get_single(cls, producer: Callable[[], Match[str] | None]) -> Self | None:
        if (result := producer()) is None:
            return None
        ret = cls()
        for name, string in result.groupdict().items():
            setattr(ret, name, string)
        return ret

    @classmethod
    def _get_iterator(cls, producer: Callable[[], Iterable[Match[str]]]) -> Iterator[Self]:
        for it in producer():
            ret = cls()
            for name, string in it.groupdict().items():
                setattr(ret, name, string)
            yield ret

    @classmethod
    def match(
        cls, string: str, pos: int | Sentinel = SENTINEL, endpos: int | Sentinel = SENTINEL
    ) -> Self | None:
        return cls._get_single(
            lambda: cls.REGEX_COMPILED.match(**build_match_args(string, pos, endpos))
        )

    @classmethod
    def search(
        cls, string: str, pos: int | Sentinel = SENTINEL, endpos: int | Sentinel = SENTINEL
    ) -> Self | None:
        return cls._get_single(
            lambda: cls.REGEX_COMPILED.search(**build_match_args(string, pos, endpos))
        )

    @classmethod
    def fullmatch(
        cls, string: str, pos: int | Sentinel = SENTINEL, endpos: int | Sentinel = SENTINEL
    ) -> Self | None:
        return cls._get_single(
            lambda: cls.REGEX_COMPILED.fullmatch(**build_match_args(string, pos, endpos))
        )

    @classmethod
    def findall(
        cls, string: str, pos: int | Sentinel = SENTINEL, endpos: int | Sentinel = SENTINEL
    ) -> list[Self]:
        return list(cls.finditer(string, pos, endpos))

    @classmethod
    def finditer(
        cls, string: str, pos: int | Sentinel = SENTINEL, endpos: int | Sentinel = SENTINEL
    ) -> Iterator[Self]:
        yield from cls._get_iterator(
            lambda: cls.REGEX_COMPILED.finditer(**build_match_args(string, pos, endpos))
        )

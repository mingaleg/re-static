from enum import Enum
from typing import NotRequired, TypedDict


class Sentinel(Enum):
    TOKEN = object()


SENTINEL = Sentinel.TOKEN


class MatchArgs(TypedDict):
    string: str
    pos: NotRequired[int]
    endpos: NotRequired[int]


def build_match_args(string: str, pos: int | Sentinel, endpos: int | Sentinel) -> MatchArgs:
    result: MatchArgs = {
        "string": string,
    }
    if pos is not SENTINEL:
        result["pos"] = pos
    if endpos is not SENTINEL:
        result["endpos"] = endpos
    return result

from collections.abc import Collection, Iterator, Mapping, Sequence
from dataclasses import dataclass
from sre_constants import SUBPATTERN
from sre_parse import SubPattern, parse


@dataclass(frozen=True)
class Group:
    index: int
    name: str | None
    always_present: bool


def get_groups(pattern: str, flags: int) -> list[Group]:
    parsed = parse(pattern, flags=flags)
    rev_groupdict = {v: k for k, v in parsed.state.groupdict.items()}
    return [
        Group(
            index=0,
            name=None,
            always_present=True,
        ),
        *sorted(
            list(
                _analyze(
                    rev_groupdict=rev_groupdict,
                    data=parsed.data,
                    top_level=True,
                )
            ),
            key=lambda it: it.index,
        ),
    ]


def _analyze(*, rev_groupdict: Mapping[int, str], data: object, top_level: bool) -> Iterator[Group]:
    if isinstance(data, SubPattern):
        data = data.data
    if not isinstance(data, Collection):
        return
    for datum in data:
        if isinstance(datum, Sequence) and len(datum) == 2 and datum[0] is SUBPATTERN:
            group, _add_flags, _del_flags, p = datum[1]
            yield Group(
                index=group,
                name=rev_groupdict.get(group),
                always_present=top_level,
            )
            yield from _analyze(
                rev_groupdict=rev_groupdict,
                data=p,
                top_level=top_level,
            )
            continue

        yield from _analyze(
            rev_groupdict=rev_groupdict,
            data=datum,
            top_level=False,
        )

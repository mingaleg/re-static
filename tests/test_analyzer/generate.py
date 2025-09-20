import json
import random
import re
from collections.abc import Iterator
from dataclasses import dataclass
from logging import Logger
from pathlib import Path
from typing import Final

from jinja2 import Environment, PackageLoader, select_autoescape
from more_itertools import pairwise, powerset, split_into

from re_static.analyzer import get_groups

logger = Logger(__name__)

JINJA_ENV = Environment(
    loader=PackageLoader("tests.test_analyzer", "templates"),
    autoescape=select_autoescape(),
)

DIR = Path(__file__).parent
TEST_TEMPLATE = JINJA_ENV.get_template("test_analyzer.py.jinja2")
TEST_OUTPUT = DIR / "test_analyzer.py"


BASE_CASES = [
    "[a-z](?P<digits>[0-9]+)(?P<letter>[a-z])?",
    # tests adopted from
    # https://github.com/python/cpython/blob/b75ed951d4de8ba85349d80c8e7f097b3cd6052f/Lib/test/re_tests.py
    "(?P<foo_123",
    "(?P<1>a)",
    "(?P<!>a)",
    "(?P<foo!>a)",
    "(?P<foo_123>a)(?P=foo_123",
    "(?P<foo_123>a)(?P=1)",
    "(?P<foo_123>a)(?P=!)",
    "(?P<foo_123>a)(?P=foo_124",
    "(?P<foo_123>a)",
    "(?P<foo_123>a)(?P=foo_123)",
    "\\1",
    "[\\1]",
    "\\09",
    "\\141",
    "(a)(b)(c)(d)(e)(f)(g)(h)(i)(j)(k)(l)\\119",
    "\\0",
    "[\\0a]",
    "[a\\0]",
    "[^a\\0]",
    "\\a[\\b]\\f\\n\\r\\t\\v",
    "[\\a][\\b][\\f][\\n][\\r][\\t][\\v]",
    "\\u",
    "\\x00ffffffffffffff",
    "\\x00f",
    "\\x00fe",
    "^\\w+=(\\\\[\\000-\\277]|[^\\n\\\\])*",
    "a.b",
    "a.*b",
    "a.{4,5}b",
    "(?s)a.b",
    "(?s)a.*b",
    "(?s)a.{4,5}b",
    ")",
    "",
    "abc",
    "ab*c",
    "ab*bc",
    "ab+bc",
    "ab?bc",
    "ab?c",
    "^abc$",
    "^abc",
    "abc$",
    "^",
    "$",
    "a.c",
    "a.*c",
    "a[bc]d",
    "a[b-d]e",
    "a[b-d]",
    "a[-b]",
    "a[\\-b]",
    "a[]b",
    "a[",
    "a\\",
    "abc)",
    "(abc",
    "a]",
    "a[]]b",
    "a[\\]]b",
    "a[^bc]d",
    "a[^-b]c",
    "a[^]b]c",
    "\\ba\\b",
    "\\by\\b",
    "x\\b",
    "x\\B",
    "\\Bz",
    "z\\B",
    "\\Bx",
    "\\Ba\\B",
    "\\By\\B",
    "\\By\\b",
    "\\by\\B",
    "ab|cd",
    "()ef",
    "$b",
    "a\\(b",
    "a\\(*b",
    "a\\\\b",
    "((a))",
    "(a)b(c)",
    "a+b+c",
    "(a+|b)*",
    "(a+|b)+",
    "(a+|b)?",
    ")(",
    "[^ab]*",
    "a*",
    "a|b|c|d|e",
    "(a|b|c|d|e)f",
    "abcd*efg",
    "ab*",
    "(ab|cd)e",
    "[abhgefdc]ij",
    "^(ab|cd)e",
    "(abc|)ef",
    "(a|b)c*d",
    "(ab|ab*)bc",
    "a([bc]*)c*",
    "a([bc]*)(c*d)",
    "a([bc]+)(c*d)",
    "a([bc]*)(c+d)",
    "a[bcd]*dcdcde",
    "a[bcd]+dcdcde",
    "(ab|a)b*c",
    "((a)(b)c)(d)",
    "[a-zA-Z_][a-zA-Z0-9_]*",
    "^a(bc+|b[eh])g|.h$",
    "(bc+d$|ef*g.|h?i(j|k))",
    "(((((((((a)))))))))",
    "multiple words of text",
    "multiple words",
    "(.*)c(.*)",
    "\\((.*), (.*)\\)",
    "[k]",
    "a[-]?c",
    "(abc)\\1",
    "([a-c]*)\\1",
    "^(.+)?B",
    "(a+).\\1$",
    "^(a+).\\1$",
    "([a-c]+)\\1",
    "(a)\\1",
    "(a+)\\1",
    "(a+)+\\1",
    "(a).+\\1",
    "(a)ba*\\1",
    "(aa|a)a\\1$",
    "(a|aa)a\\1$",
    "(a+)a\\1$",
    "([abc]*)\\1",
    "(a)(b)c|ab",
    "(a)+x",
    "([ac])+x",
    "([^/]*/)*sub1/",
    "([^.]*)\\.([^:]*):[T ]+(.*)",
    "([^N]*N)+",
    "([abc]*)x",
    "([xyz]*)x",
    "(a)+b|aac",
    "(?P<i d>aaa)a",
    "(?P<id>aaa)a",
    "(?P<id>aa)(?P=id)",
    "(?P<id>aa)(?P=xd)",
    "ab{0,}bc",
    "ab{1,}bc",
    "ab{1,3}bc",
    "ab{3,4}bc",
    "ab{4,5}bc",
    "ab{0,1}bc",
    "ab{0,1}c",
    "a[b-]",
    "a[b-a]",
    "*a",
    "(*)b",
    "a{1,}b{1,}c",
    "a**",
    "a.+?c",
    "(a+|b){0,}",
    "(a+|b){1,}",
    "(a+|b){0,1}",
    "([abc])*d",
    "([abc])*bcd",
    "((((((((((a))))))))))",
    "((((((((((a))))))))))\\10",
    "((((((((((a))))))))))\\41",
    "(?i)((((((((((a))))))))))\\41",
    "(?i)abc",
    "(?i)ab*c",
    "(?i)ab*bc",
    "(?i)ab*?bc",
    "(?i)ab{0,}?bc",
    "(?i)ab+?bc",
    "(?i)ab+bc",
    "(?i)ab{1,}bc",
    "(?i)ab{1,}?bc",
    "(?i)ab{1,3}?bc",
    "(?i)ab{3,4}?bc",
    "(?i)ab{4,5}?bc",
    "(?i)ab??bc",
    "(?i)ab{0,1}?bc",
    "(?i)ab??c",
    "(?i)ab{0,1}?c",
    "(?i)^abc$",
    "(?i)^abc",
    "(?i)abc$",
    "(?i)^",
    "(?i)$",
    "(?i)a.c",
    "(?i)a.*?c",
    "(?i)a.*c",
    "(?i)a[bc]d",
    "(?i)a[b-d]e",
    "(?i)a[b-d]",
    "(?i)a[-b]",
    "(?i)a[b-]",
    "(?i)a[b-a]",
    "(?i)a[]b",
    "(?i)a[",
    "(?i)a]",
    "(?i)a[]]b",
    "(?i)a[^bc]d",
    "(?i)a[^-b]c",
    "(?i)a[^]b]c",
    "(?i)ab|cd",
    "(?i)()ef",
    "(?i)*a",
    "(?i)(*)b",
    "(?i)$b",
    "(?i)a\\",
    "(?i)a\\(b",
    "(?i)a\\(*b",
    "(?i)a\\\\b",
    "(?i)abc)",
    "(?i)(abc",
    "(?i)((a))",
    "(?i)(a)b(c)",
    "(?i)a+b+c",
    "(?i)a{1,}b{1,}c",
    "(?i)a**",
    "(?i)a.+?c",
    "(?i)a.{0,5}?c",
    "(?i)(a+|b)*",
    "(?i)(a+|b){0,}",
    "(?i)(a+|b)+",
    "(?i)(a+|b){1,}",
    "(?i)(a+|b)?",
    "(?i)(a+|b){0,1}",
    "(?i)(a+|b){0,1}?",
    "(?i))(",
    "(?i)[^ab]*",
    "(?i)a*",
    "(?i)([abc])*d",
    "(?i)([abc])*bcd",
    "(?i)a|b|c|d|e",
    "(?i)(a|b|c|d|e)f",
    "(?i)abcd*efg",
    "(?i)ab*",
    "(?i)(ab|cd)e",
    "(?i)[abhgefdc]ij",
    "(?i)^(ab|cd)e",
    "(?i)(abc|)ef",
    "(?i)(a|b)c*d",
    "(?i)(ab|ab*)bc",
    "(?i)a([bc]*)c*",
    "(?i)a([bc]*)(c*d)",
    "(?i)a([bc]+)(c*d)",
    "(?i)a([bc]*)(c+d)",
    "(?i)a[bcd]*dcdcde",
    "(?i)a[bcd]+dcdcde",
    "(?i)(ab|a)b*c",
    "(?i)((a)(b)c)(d)",
    "(?i)[a-zA-Z_][a-zA-Z0-9_]*",
    "(?i)^a(bc+|b[eh])g|.h$",
    "(?i)(bc+d$|ef*g.|h?i(j|k))",
    "(?i)((((((((((a))))))))))",
    "(?i)((((((((((a))))))))))\\10",
    "(?i)(((((((((a)))))))))",
    "(?i)(?:(?:(?:(?:(?:(?:(?:(?:(?:(a))))))))))",
    "(?i)(?:(?:(?:(?:(?:(?:(?:(?:(?:(a|b|c))))))))))",
    "(?i)multiple words of text",
    "(?i)multiple words",
    "(?i)(.*)c(.*)",
    "(?i)\\((.*), (.*)\\)",
    "(?i)[k]",
    "(?i)a[-]?c",
    "(?i)(abc)\\1",
    "(?i)([a-c]*)\\1",
    "a(?!b).",
    "a(?=d).",
    "a(?=c|d).",
    "a(?:b|c|d)(.)",
    "a(?:b|c|d)*(.)",
    "a(?:b|c|d)+?(.)",
    "a(?:b|(c|e){1,2}?|d)+?(.)",
    "(?<!-):(.*?)(?<!-):",
    "(?<!\\\\):(.*?)(?<!\\\\):",
    "(?<!\\?)'(.*?)(?<!\\?)'",
    "w(?# comment",
    "w(?# comment 1)xy(?# comment 2)z",
    "(?i)w",
    "(?x)w# comment 1\n        x y\n        # comment 2\n        z",
    "(?m)^abc",
    "(?m)abc$",
    "\\w+",
    "[\\w]+",
    "\\D+",
    "[\\D]+",
    "[\\da-fA-F]+",
    "([\\s]*)([\\S]*)([\\s]*)",
    "(\\s*)(\\S*)(\\s*)",
    "\\xff",
    "\\x00ff",
    "\\t\\n\\v\\r\\f\\a",
    "\t\n\x0b\r\x0c\x07",
    "[\\t][\\n][\\v][\\r][\\f][\\b]",
    "(([a-z]+):)?([a-z]+)$",
    "((.)\\1+)",
    ".*d",
    "(",
    "[\\41]",
    "(x?)?",
    "(?x) foo ",
    "(?<!abc)(d.f)",
    "[\\w-]+",
    ".*?\\S *:",
    "a[ ]*?\\ (\\d+).*",
    "(?ms).*?x\\s*\\Z(.*)",
    "(?i)M+",
    "(?i)m+",
    "(?i)[M]+",
    "(?i)[m]+",
    "^*",
    "'(?:\\\\'|[^'])*?'",
    "^.*?$",
    "a[^>]*?b",
    "^a*?$",
    "^((a)c)?(ab)$",
    "^([ab]*?)(?=(b)?)c",
    "^([ab]*?)(?!(b))c",
    "^([ab]*?)(?<!(a))c",
    "\\b.\\b",
    "(?u)\\b.\\b",
    "(?u)\\w",
]


def expand_case(pattern: str) -> Iterator[str]:
    max_cases_produced: Final = 5
    rnd = random.Random(42)  # noqa S311: no need for secure randomness here
    open_parens_indices = [it.start() for it in re.finditer(r"\([^?]", pattern)]
    all_selected_indices = [*powerset(open_parens_indices)]
    if len(all_selected_indices) > max_cases_produced:
        all_selected_indices = rnd.sample(all_selected_indices, max_cases_produced)
    for _selected_indices in all_selected_indices:
        selected_indices = [0, *_selected_indices]
        split_into_sizes = [next - prev for prev, next in pairwise(selected_indices)] + [None]
        first_chunk, *chunks = ["".join(it) for it in split_into(pattern, split_into_sizes)]
        candidate_pattern = first_chunk + "".join(
            f"(?P<group{idx}>{chunk[1:]}" if chunk else "" for idx, chunk in enumerate(chunks)
        )
        try:
            re.compile(candidate_pattern)
        except Exception as exc:
            logger.debug(
                f"skipping broken pattern {candidate_pattern!r} generated from {pattern!r}: {exc}",
                exc_info=True,
            )
            # no need to log an exception, broken patterns are expected here
            continue
        yield candidate_pattern


@dataclass(frozen=True)
class TestSuite:
    base_regex: str
    cases: list[str]


def render() -> str:
    test_suites: list[TestSuite] = []
    for base_case in BASE_CASES:
        test_suite = TestSuite(
            base_regex=json.dumps(base_case),
            cases=[],
        )
        for case in expand_case(base_case):
            case_lines = [
                "    check(",
                f"        {json.dumps(case)},",
            ]
            for group in get_groups(case, flags=0):
                if group.index == 0:
                    continue
                helper_func = "always_present" if group.always_present else "optional"
                if group.name is not None:
                    case_lines.append(f'        {helper_func}("{group.name}"),')
                else:
                    case_lines.append(f"        {helper_func}(),")
            case_lines.append("    )")
            test_suite.cases.append("\n".join(case_lines))
        if test_suite.cases:
            test_suites.append(test_suite)
    return TEST_TEMPLATE.render(test_suites=test_suites)


def main():
    print(render(), file=TEST_OUTPUT.open("w"), end="")


if __name__ == "__main__":
    main()

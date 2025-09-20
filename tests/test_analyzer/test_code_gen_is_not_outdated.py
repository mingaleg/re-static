from pathlib import Path

from tests.test_analyzer.generate import render

DIR = Path(__file__).parent
TEST = DIR / "test_analyzer.py"


def test_code_gen_is_not_outdated():
    assert render() == TEST.open().read(), (
        "run `python ./tests/test_analyzer/generate.py` to regen outdated test_analyzer.py"
    )

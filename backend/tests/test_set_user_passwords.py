"""The password-setting script: parsing rules (pure logic, no database needed)."""
import pytest

from app.scripts.set_user_passwords import parse_lines


def test_parses_lines_and_ignores_comments_and_blanks():
    text = "# demo accounts\n\n  Swara@Demo : first-password-12 \npranav@demo:second-password-34\n"
    assert parse_lines(text) == {
        "swara@demo": "first-password-12",
        "pranav@demo": "second-password-34",
    }


def test_password_may_contain_a_colon():
    assert parse_lines("a@demo: pass:word-with-colon-1") == {"a@demo": "pass:word-with-colon-1"}


@pytest.mark.parametrize(
    "bad",
    [
        "no-separator-here",
        "a@demo:",
        ": only-a-password-123",
        "a@demo: short",
        "a@demo: " + "x" * 129,
        "a@demo: long-enough-password-1\na@demo: another-long-password-2",
    ],
)
def test_bad_lines_are_rejected(bad):
    with pytest.raises(ValueError):
        parse_lines(bad)

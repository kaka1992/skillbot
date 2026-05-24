import sys
sys.path.insert(0, "src")

from jupyter.feedback import parse_feedback_line


class TestParseFeedback:
    def test_yes(self):
        r = parse_feedback_line("yes")
        assert r == ("yes", None)

    def test_no(self):
        r = parse_feedback_line("no")
        assert r == ("no", None)

    def test_yes_with_comment(self):
        r = parse_feedback_line("yes --comment 'looks good'")
        assert r == ("yes", "looks good")

    def test_no_with_reason(self):
        r = parse_feedback_line("no --comment 'missing chart'")
        assert r == ("no", "missing chart")

    def test_invalid(self):
        r = parse_feedback_line("maybe")
        assert r == (None, None)

    def test_empty(self):
        r = parse_feedback_line("")
        assert r == (None, None)

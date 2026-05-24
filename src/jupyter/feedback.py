"""%feedback / %fb line magic — user confirms agent output meets expectations."""

import shlex


def parse_feedback_line(line: str) -> tuple[str | None, str | None]:
    """Parse feedback input. Returns (result, comment) or (None, None) for invalid."""
    args = shlex.split(line)
    if not args:
        return None, None

    result = args[0].lower()
    if result not in ("yes", "no"):
        return None, None

    comment = None
    i = 1
    while i < len(args):
        if args[i] in ("--comment", "--reason") and i + 1 < len(args):
            comment = args[i + 1]
            i += 2
        else:
            i += 1
    return result, comment

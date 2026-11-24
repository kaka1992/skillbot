import json

from jupyter.cell_reference import (
    format_cell_references,
    parse_cell_references,
    referenced_edit_target,
)


def test_parse_cell_references_validates_deduplicates_and_bounds_content():
    raw = json.dumps([
        {
            "cell_id": "cell-a",
            "label": "Cell 3",
            "cell_type": "code",
            "code": "x" * 6000,
            "output": "ok",
            "error": "",
        },
        {"cell_id": "cell-a", "code": "duplicate"},
        {"cell_id": "", "code": "missing identity"},
    ])

    references = parse_cell_references(raw)

    assert len(references) == 1
    assert references[0]["cell_id"] == "cell-a"
    assert len(references[0]["code"]) == 5000


def test_format_cell_references_includes_code_output_and_error():
    context = format_cell_references([
        {
            "cell_id": "cell-a",
            "label": "Cell 2",
            "cell_type": "code",
            "code": "print(value)",
            "output": "",
            "error": "NameError: value",
        }
    ])

    assert "Explicitly referenced notebook cells" in context
    assert "Cell 2 (cell_id: cell-a)" in context
    assert "print(value)" in context
    assert "NameError: value" in context


def test_edit_target_requires_one_reference_and_explicit_edit_intent():
    references = [{"cell_id": "cell-a"}]

    assert referenced_edit_target("修复这个单元格的报错", references) == "cell-a"
    assert referenced_edit_target("explain this error", references) == ""
    assert referenced_edit_target(
        "fix these cells",
        [{"cell_id": "cell-a"}, {"cell_id": "cell-b"}],
    ) == ""

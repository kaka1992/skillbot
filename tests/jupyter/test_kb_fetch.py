import runpy
from pathlib import Path


def test_fetch_creates_draft_categories_on_first_run(tmp_path, monkeypatch):
    script = Path(__file__).resolve().parents[2] / "scripts" / "kb_fetch.py"
    main = runpy.run_path(str(script))["main"]
    draft = tmp_path / "knowledge_base_draft"
    monkeypatch.setitem(main.__globals__, "DRAFT", draft)
    monkeypatch.setitem(main.__globals__, "DOCS", [("category", "id", "Title", "docx")])
    monkeypatch.setitem(
        main.__globals__, "fetch",
        lambda _: {"ok": True, "data": {"document": {"content": "Hello"}}},
    )

    main()

    assert (draft / "category" / "Title.md").read_text(encoding="utf-8").endswith("Hello")

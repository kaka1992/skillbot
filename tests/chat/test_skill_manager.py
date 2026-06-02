"""Tests for cross-agent skill management — SkillManager + persistence."""
import io
import json
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from chat.skill import SkillManager, SkillInfo


@pytest.fixture
def tmp_skill_dir():
    d = tempfile.mkdtemp(prefix="skillbot-test-")
    s1 = Path(d) / "test-skill"
    s1.mkdir()
    (s1 / "SKILL.md").write_text(
        "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test Skill\n\nBody content."
    )
    (s1 / "references").mkdir()
    (s1 / "references" / "helper.py").write_text("print('hello')")

    s2 = Path(d) / "another-skill"
    s2.mkdir()
    (s2 / "SKILL.md").write_text(
        "---\nname: another-skill\ndescription: Another one\n---\n\n## Another\n\nMore body."
    )
    yield d
    shutil.rmtree(d)


@pytest.fixture
def mgr(tmp_skill_dir):
    return SkillManager(tmp_skill_dir)


def _make_zip(skill_name: str, skill_md_content: str, extra_files: dict | None = None) -> bytes:
    """Helper: create an in-memory zip for a skill."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(f"{skill_name}/SKILL.md", skill_md_content)
        for path, content in (extra_files or {}).items():
            zf.writestr(f"{skill_name}/{path}", content)
    return buf.getvalue()


# ============================================================================
# SkillInfo dataclass
# ============================================================================

class TestSkillInfo:
    def test_defaults(self):
        s = SkillInfo(name="s", description="d", path="/p")
        assert s.enabled is False
        assert s.body == ""

# ============================================================================
# list / get
# ============================================================================

class TestListGet:
    def test_list_skills_default_all_enabled(self, mgr):
        skills = mgr.list_skills()
        assert len(skills) == 2
        assert all(s.enabled for s in skills)

    def test_list_skills_reflects_enable_status(self, mgr):
        mgr.disable("test-skill")
        skills = {s.name: s.enabled for s in mgr.list_skills()}
        assert skills == {"test-skill": False, "another-skill": True}

    def test_get_skill(self, mgr):
        s = mgr.get_skill("test-skill")
        assert s is not None
        assert s.name == "test-skill"
        assert s.enabled is True
        assert s.description == "A test skill"
        assert "Body content" in s.body
        assert s.path.endswith("test-skill")

    def test_get_skill_disabled(self, mgr):
        mgr.disable("test-skill")
        s = mgr.get_skill("test-skill")
        assert s is not None
        assert s.enabled is False

    def test_get_skill_missing(self, mgr):
        assert mgr.get_skill("nonexistent") is None

    def test_list_skills_empty_dir(self, tmp_skill_dir):
        # Empty dir (no skills installed)
        empty = Path(tmp_skill_dir) / "empty"
        empty.mkdir()
        mgr = SkillManager(str(empty))
        assert mgr.list_skills() == []
        assert mgr.active_skills == []

    def test_list_skills_non_existent_dir(self):
        mgr = SkillManager("/tmp/skillbot-nonexistent-dir-xyz")
        assert mgr.list_skills() == []
        assert mgr.active_skills == []

# ============================================================================
# enable / disable
# ============================================================================

class TestEnableDisable:
    def test_default_all_enabled(self, mgr):
        assert mgr.active_skills == ["another-skill", "test-skill"]
        assert mgr.disabled_skills == []

    def test_enable_disable_toggle(self, mgr):
        mgr.disable("test-skill")
        assert mgr.active_skills == ["another-skill"]
        assert mgr.disabled_skills == ["test-skill"]

        mgr.enable("test-skill")
        assert mgr.active_skills == ["another-skill", "test-skill"]
        assert mgr.disabled_skills == []

    def test_disable_already_disabled_noop(self, mgr):
        mgr.disable("test-skill")
        mgr.disable("test-skill")  # no-op
        assert mgr.active_skills == ["another-skill"]

    def test_enable_already_enabled_noop(self, mgr):
        mgr.enable("test-skill")  # no-op
        assert mgr.active_skills == ["another-skill", "test-skill"]

    def test_enable_missing_raises(self, mgr):
        with pytest.raises(FileNotFoundError):
            mgr.enable("nonexistent")

    def test_disable_missing_raises(self, mgr):
        with pytest.raises(FileNotFoundError):
            mgr.disable("nonexistent")

    def test_disabled_skills_filters_uninstalled(self, mgr, tmp_skill_dir):
        """After uninstall, disabled_skills should not include the removed skill."""
        mgr.disable("test-skill")
        mgr.uninstall("test-skill")
        mgr2 = SkillManager(tmp_skill_dir)
        assert "test-skill" not in mgr2.disabled_skills

# ============================================================================
# persistence
# ============================================================================

class TestPersistence:
    def test_survives_reload(self, mgr, tmp_skill_dir):
        mgr.disable("test-skill")
        mgr2 = SkillManager(tmp_skill_dir)
        assert "test-skill" not in mgr2.active_skills
        s = mgr2.get_skill("test-skill")
        assert s.enabled is False

    def test_state_file_is_valid_json(self, mgr, tmp_skill_dir):
        mgr.disable("test-skill")
        state = Path(tmp_skill_dir) / ".skill_state.json"
        assert state.is_file()
        data = json.loads(state.read_text())
        assert data == {"disabled": ["test-skill"]}

    def test_corrupt_state_file_falls_back_to_empty(self, tmp_skill_dir):
        (Path(tmp_skill_dir) / ".skill_state.json").write_text("not json {{{")
        mgr = SkillManager(tmp_skill_dir)
        assert mgr.active_skills == ["another-skill", "test-skill"]

    def test_state_file_missing_falls_back_to_all_enabled(self, tmp_skill_dir):
        # No .skill_state.json → all enabled
        mgr = SkillManager(tmp_skill_dir)
        assert mgr.active_skills == ["another-skill", "test-skill"]

    def test_empty_state_file(self, tmp_skill_dir):
        (Path(tmp_skill_dir) / ".skill_state.json").write_text("{}")
        mgr = SkillManager(tmp_skill_dir)
        assert mgr.active_skills == ["another-skill", "test-skill"]
        assert mgr.disabled_skills == []

# ============================================================================
# inject_prompt
# ============================================================================

class TestInjectPrompt:
    def test_default_injects_all_enabled(self, mgr):
        prompt = mgr.inject_prompt()
        assert "test-skill" in prompt
        assert "Body content" in prompt
        assert "another-skill" in prompt
        assert "More body" in prompt

    def test_all_disabled_shows_disabled_notice(self, mgr):
        mgr.disable("test-skill")
        mgr.disable("another-skill")
        prompt = mgr.inject_prompt()
        assert "DISABLED" in prompt
        assert "test-skill" in prompt
        assert "another-skill" in prompt
        assert "active for this conversation" not in prompt.lower()

    def test_partially_disabled_shows_both(self, mgr):
        mgr.disable("test-skill")
        prompt = mgr.inject_prompt()
        assert "active for this conversation" in prompt.lower()
        assert "DISABLED" in prompt
        assert "test-skill" in prompt

    def test_explicit_list(self, mgr):
        mgr.disable("test-skill")
        # Explicitly request a disabled skill
        prompt = mgr.inject_prompt(["test-skill"])
        assert "test-skill" in prompt
        assert "another-skill" not in prompt

    def test_explicit_empty_list(self, mgr):
        assert mgr.inject_prompt([]) == ""

    def test_explicit_nonexistent_skill_skipped(self, mgr):
        prompt = mgr.inject_prompt(["test-skill", "nonexistent"])
        assert "test-skill" in prompt
        assert "nonexistent" not in prompt

    def test_no_skills_installed(self, mgr):
        mgr.uninstall("test-skill")
        mgr.uninstall("another-skill")
        assert mgr.inject_prompt() == ""

    def test_skill_with_empty_body(self, tmp_skill_dir):
        s = Path(tmp_skill_dir) / "empty-body"
        s.mkdir()
        (s / "SKILL.md").write_text("---\nname: empty-body\ndescription: E\n---\n\n")
        mgr = SkillManager(tmp_skill_dir)
        prompt = mgr.inject_prompt()
        assert "empty-body" not in prompt  # no body → skipped

# ============================================================================
# install
# ============================================================================

class TestInstall:
    def test_basic(self, mgr):
        data = _make_zip("install-test",
            "---\nname: install-test\ndescription: Zip\n---\n\n# Installed\n\nZip content.")
        zip_path = Path(mgr._dir) / "test.zip"
        zip_path.write_bytes(data)

        info = mgr.install(str(zip_path))
        assert info.name == "install-test"
        assert info.enabled is True
        assert (Path(mgr._dir) / "install-test" / "SKILL.md").is_file()
        assert "install-test" in mgr.active_skills

    def test_with_references(self, mgr):
        data = _make_zip("with-refs",
            "---\nname: with-refs\ndescription: Ref\n---\n\n# Ref\n\nBody.",
            {"references/helper.py": "print(1)", "references/data.csv": "a,b\n1,2"})
        zip_path = Path(mgr._dir) / "refs.zip"
        zip_path.write_bytes(data)

        mgr.install(str(zip_path))
        assert (Path(mgr._dir) / "with-refs" / "references" / "helper.py").is_file()
        assert (Path(mgr._dir) / "with-refs" / "references" / "data.csv").is_file()

    def test_overwrite(self, mgr):
        data1 = _make_zip("overwrite", "---\nname: overwrite\ndescription: v1\n---\n\n# V1\n\nOld.")
        data2 = _make_zip("overwrite", "---\nname: overwrite\ndescription: v2\n---\n\n# V2\n\nNew.")

        p = Path(mgr._dir) / "ow.zip"
        p.write_bytes(data1)
        mgr.install(str(p))
        p.write_bytes(data2)
        mgr.install(str(p))

        s = mgr.get_skill("overwrite")
        assert "V2" in s.body

    def test_overwrite_preserves_enabled(self, mgr, tmp_skill_dir):
        data = _make_zip("overwrite", "---\nname: overwrite\ndescription: v1\n---\n\nBody.")
        p = Path(mgr._dir) / "ow.zip"
        p.write_bytes(data)
        mgr.install(str(p))
        mgr.disable("overwrite")

        # Overwrite with new version — should re-enable (new skills default enabled)
        data2 = _make_zip("overwrite", "---\nname: overwrite\ndescription: v2\n---\n\nV2.")
        p.write_bytes(data2)
        mgr.install(str(p))
        assert "overwrite" in mgr.active_skills  # re-enabled after install

    def test_missing_frontmatter(self, mgr):
        data = _make_zip("bad", "No frontmatter here")
        p = Path(mgr._dir) / "bad.zip"
        p.write_bytes(data)
        with pytest.raises(ValueError, match="frontmatter"):
            mgr.install(str(p))

    def test_missing_skill_md(self, mgr):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("no-md/README.md", "not a skill")
        p = Path(mgr._dir) / "nomd.zip"
        p.write_bytes(buf.getvalue())
        with pytest.raises(ValueError, match="SKILL.md"):
            mgr.install(str(p))

    def test_invalid_name_dotfile(self, mgr):
        data = _make_zip(".hidden", "---\nname: .hidden\ndescription: h\n---\n\nBody.")
        p = Path(mgr._dir) / "hidden.zip"
        p.write_bytes(data)
        with pytest.raises(ValueError, match="invalid skill name"):
            mgr.install(str(p))

    def test_invalid_name_pycache(self, mgr):
        data = _make_zip("__pycache__", "---\nname: cache\ndescription: c\n---\n\nBody.")
        p = Path(mgr._dir) / "cache.zip"
        p.write_bytes(data)
        with pytest.raises(ValueError, match="invalid skill name"):
            mgr.install(str(p))

    def test_empty_zip(self, mgr):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            pass  # empty
        p = Path(mgr._dir) / "empty.zip"
        p.write_bytes(buf.getvalue())
        with pytest.raises(ValueError, match="empty"):
            mgr.install(str(p))

    def test_not_a_zip(self, mgr):
        """Non-.zip extension should be rejected before opening."""
        p = Path(mgr._dir) / "not.txt"
        p.write_text("hello world")
        with pytest.raises(ValueError, match=".zip"):
            mgr.install(str(p))

    def test_file_not_found(self, mgr):
        with pytest.raises(FileNotFoundError):
            mgr.install("/tmp/skillbot-nonexistent-file.zip")

    def test_zip_with_multiple_top_level_dirs(self, mgr):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("skill-a/SKILL.md", "---\nname: a\ndescription: A\n---\n\nA body.")
            zf.writestr("skill-b/SKILL.md", "---\nname: b\ndescription: B\n---\n\nB body.")
        p = Path(mgr._dir) / "multi.zip"
        p.write_bytes(buf.getvalue())
        with pytest.raises(ValueError, match="SKILL.md"):
            mgr.install(str(p))

    def test_corrupt_zip(self, mgr):
        p = Path(mgr._dir) / "corrupt.zip"
        p.write_bytes(b"\x00\x01\x02")
        with pytest.raises((ValueError, zipfile.BadZipFile)):
            mgr.install(str(p))

# ============================================================================
# uninstall
# ============================================================================

class TestUninstall:
    def test_basic(self, mgr):
        mgr.uninstall("test-skill")
        assert mgr.get_skill("test-skill") is None
        assert "test-skill" not in mgr.active_skills
        assert "test-skill" not in mgr.disabled_skills

    def test_cleans_state_file(self, mgr, tmp_skill_dir):
        mgr.disable("test-skill")
        mgr.uninstall("test-skill")
        mgr2 = SkillManager(tmp_skill_dir)
        assert "test-skill" not in mgr2.disabled_skills

    def test_missing_raises(self, mgr):
        with pytest.raises(FileNotFoundError):
            mgr.uninstall("nonexistent")

# ============================================================================
# frontmatter edge cases
# ============================================================================

class TestFrontmatter:
    def test_windows_line_endings(self, tmp_skill_dir):
        s = Path(tmp_skill_dir) / "win-skill"
        s.mkdir()
        (s / "SKILL.md").write_text(
            "---\r\nname: win-skill\r\ndescription: Windows\r\n---\r\n\r\nBody with CRLF.\r\n"
        )
        mgr = SkillManager(tmp_skill_dir)
        info = mgr.get_skill("win-skill")
        assert info is not None
        assert "Body with CRLF" in info.body

    def test_no_trailing_newline(self, tmp_skill_dir):
        s = Path(tmp_skill_dir) / "no-nl"
        s.mkdir()
        (s / "SKILL.md").write_text(
            "---\nname: no-nl\ndescription: NoNL\n---\nBody without trailing newline"
        )
        mgr = SkillManager(tmp_skill_dir)
        info = mgr.get_skill("no-nl")
        assert info is not None
        assert "Body without trailing newline" in info.body

    def test_name_falls_back_to_dirname(self, tmp_skill_dir):
        s = Path(tmp_skill_dir) / "dir-named"
        s.mkdir()
        (s / "SKILL.md").write_text(
            "---\ndescription: No name field\n---\n\nJust body."
        )
        mgr = SkillManager(tmp_skill_dir)
        info = mgr.get_skill("dir-named")
        assert info is not None
        assert info.name == "dir-named"

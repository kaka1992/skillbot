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

from chat import ChatClient
from chat.skill import SkillManager, SkillInfo, _tokenize


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

    def test_categorized_layout_enables_custom_skills(self, tmp_skill_dir):
        root = Path(tmp_skill_dir) / "categorized"
        custom = root / "custom" / "risk-knowledge-base"
        research = root / "research" / "paper-search"
        custom.mkdir(parents=True)
        research.mkdir(parents=True)
        (custom / "SKILL.md").write_text(
            "---\nname: risk-knowledge-base\ndescription: Risk KB\n---\n\nBody."
        )
        (research / "SKILL.md").write_text(
            "---\nname: paper-search\ndescription: Research\n---\n\nBody."
        )

        states = {s.name: s.enabled for s in SkillManager(str(root)).list_skills()}

        assert states == {"paper-search": False, "risk-knowledge-base": True}

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
        assert data == {"disabled": ["test-skill"], "enabled": []}

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


class TestProgressiveInject:
    def test_routing_layer_has_names_and_descriptions(self, mgr):
        prompt = mgr.inject_prompt(progressive=True)
        assert "test-skill" in prompt
        assert "A test skill" in prompt
        assert "another-skill" in prompt
        assert "Another one" in prompt

    def test_omits_full_bodies(self, mgr):
        prompt = mgr.inject_prompt(progressive=True)
        assert "Body content" not in prompt
        assert "More body" not in prompt

    def test_points_to_skill_md_path(self, mgr):
        prompt = mgr.inject_prompt(progressive=True)
        assert "SKILL.md" in prompt
        assert "test-skill/SKILL.md" in prompt

    def test_size_is_independent_of_large_body(self, tmp_skill_dir):
        skill = Path(tmp_skill_dir) / "big-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text(
            "---\nname: big-skill\ndescription: A big skill\n---\n\n"
            + ("lorem ipsum body line\n" * 500)
        )
        manager = SkillManager(tmp_skill_dir)

        full = manager.inject_prompt()
        progressive = manager.inject_prompt(progressive=True)

        assert len(progressive) < len(full)
        assert "lorem ipsum body line" not in progressive

    def test_disabled_notice_still_present(self, mgr):
        mgr.disable("test-skill")
        prompt = mgr.inject_prompt(progressive=True)
        assert "DISABLED" in prompt
        assert "test-skill" in prompt
        assert "another-skill" in prompt

    def test_skill_without_description_is_skipped(self, tmp_skill_dir):
        skill = Path(tmp_skill_dir) / "no-description"
        skill.mkdir()
        (skill / "SKILL.md").write_text(
            "---\nname: no-description\n---\n\nBody only."
        )
        prompt = SkillManager(tmp_skill_dir).inject_prompt(progressive=True)
        assert "no-description" not in prompt

    def test_full_mode_remains_default(self, mgr):
        prompt = mgr.inject_prompt()
        assert "Body content" in prompt
        assert "More body" in prompt


@pytest.fixture
def retrieval_mgr(tmp_skill_dir):
    for name, description in [
        ("join-skill", "把样本表和特征表做 LEFT JOIN 拼接特征"),
        ("face-skill", "比对两张人脸照片相似度判断是否同一人"),
        ("sql-skill", "validate Hive SQL and submit async query jobs via tqs"),
    ]:
        skill = Path(tmp_skill_dir) / name
        skill.mkdir()
        (skill / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: {description}\n---\n\nBody."
        )
    return SkillManager(tmp_skill_dir)


class TestKeywordRetrieval:
    def test_tokenize_keeps_ascii_identifiers(self):
        tokens = _tokenize("feature_join TQS")
        assert "feature_join" in tokens
        assert "feature" in tokens
        assert "join" in tokens
        assert "tqs" in tokens

    def test_tokenize_cjk_unigrams_and_bigrams(self):
        tokens = _tokenize("人脸相似")
        assert "人" in tokens
        assert "人脸" in tokens

    def test_retrieve_ranks_relevant_skill_first(self, retrieval_mgr):
        ranked = retrieval_mgr.retrieve("比对人脸照片是不是同一个人", top_k=3)
        assert ranked[0][0] == "face-skill"

    def test_retrieve_english_identifier_query(self, retrieval_mgr):
        ranked = retrieval_mgr.retrieve(
            "check Hive SQL syntax then submit tqs job", top_k=3
        )
        assert ranked[0][0] == "sql-skill"

    def test_retrieve_respects_top_k(self, retrieval_mgr):
        ranked = retrieval_mgr.retrieve("特征 人脸 SQL", top_k=2)
        assert len(ranked) <= 2

    def test_retrieve_unrelated_query_returns_empty(self, retrieval_mgr):
        assert retrieval_mgr.retrieve("zzz qqq xxx", top_k=5) == []

    def test_retrieve_excludes_disabled_skills(self, retrieval_mgr):
        retrieval_mgr.disable("face-skill")
        names = {
            name
            for name, _ in retrieval_mgr.retrieve(
                "比对人脸照片是不是同一个人", top_k=5
            )
        }
        assert "face-skill" not in names

    def test_query_narrows_progressive_catalog(self, retrieval_mgr):
        prompt = retrieval_mgr.inject_prompt(
            progressive=True,
            query="拼接特征表",
            top_k=1,
        )
        assert "join-skill" in prompt
        assert "face-skill" not in prompt
        assert "sql-skill" not in prompt

    def test_unrelated_query_does_not_fall_back_to_full_catalog(
        self, retrieval_mgr
    ):
        prompt = retrieval_mgr.inject_prompt(
            progressive=True,
            query="zzz qqq xxx",
            top_k=1,
        )
        assert prompt == ""

    def test_no_query_keeps_all_skills(self, retrieval_mgr):
        prompt = retrieval_mgr.inject_prompt(progressive=True)
        assert "join-skill" in prompt
        assert "face-skill" in prompt
        assert "sql-skill" in prompt


class TestLLMRerank:
    def test_reorders_by_model_output(self, retrieval_mgr, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        monkeypatch.setattr(
            SkillManager,
            "_deepseek_rank",
            staticmethod(
                lambda *args, **kwargs: [
                    "face-skill",
                    "sql-skill",
                    "join-skill",
                ]
            ),
        )
        result = retrieval_mgr.rerank(
            "anything",
            ["join-skill", "sql-skill", "face-skill"],
        )
        assert result[0] == "face-skill"

    def test_appends_candidates_omitted_by_model(self, retrieval_mgr, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        monkeypatch.setattr(
            SkillManager,
            "_deepseek_rank",
            staticmethod(lambda *args, **kwargs: ["face-skill"]),
        )
        result = retrieval_mgr.rerank(
            "query",
            ["join-skill", "sql-skill", "face-skill"],
        )
        assert set(result) == {"join-skill", "sql-skill", "face-skill"}

    def test_ignores_unknown_model_names(self, retrieval_mgr, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        monkeypatch.setattr(
            SkillManager,
            "_deepseek_rank",
            staticmethod(lambda *args, **kwargs: ["invented", "face-skill"]),
        )
        result = retrieval_mgr.rerank(
            "query",
            ["join-skill", "face-skill"],
        )
        assert "invented" not in result
        assert set(result) == {"join-skill", "face-skill"}

    def test_falls_back_to_keyword_order_on_error(
        self, retrieval_mgr, monkeypatch
    ):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

        def fail(*args, **kwargs):
            raise RuntimeError("network unavailable")

        monkeypatch.setattr(
            SkillManager,
            "_deepseek_rank",
            staticmethod(fail),
        )
        candidates = ["join-skill", "sql-skill", "face-skill"]
        assert retrieval_mgr.rerank("query", candidates) == candidates

    def test_no_key_keeps_keyword_order(self, retrieval_mgr, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        candidates = ["join-skill", "sql-skill"]
        assert retrieval_mgr.rerank("query", candidates) == candidates

    def test_top_k_truncates_result(self, retrieval_mgr, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        monkeypatch.setattr(
            SkillManager,
            "_deepseek_rank",
            staticmethod(
                lambda *args, **kwargs: [
                    "face-skill",
                    "sql-skill",
                    "join-skill",
                ]
            ),
        )
        result = retrieval_mgr.rerank(
            "query",
            ["join-skill", "sql-skill", "face-skill"],
            top_k=1,
        )
        assert result == ["face-skill"]


class TestChatClientSkillRouting:
    def test_top_k_routes_each_message_independently(
        self, retrieval_mgr, monkeypatch
    ):
        monkeypatch.setenv("SKILLBOT_PROGRESSIVE_SKILLS", "1")
        monkeypatch.setenv("SKILLBOT_SKILL_TOPK", "1")
        monkeypatch.delenv("SKILLBOT_SKILL_RERANK", raising=False)
        client = object.__new__(ChatClient)
        client._agent = "hermes-agent"
        client.skills = retrieval_mgr
        client._skill_version = None

        join_prompt = client._maybe_inject_skills("请拼接样本和特征表")
        face_prompt = client._maybe_inject_skills("请比对两张人脸照片")

        assert "join-skill" in join_prompt
        assert "face-skill" not in join_prompt
        assert "face-skill" in face_prompt
        assert "join-skill" not in face_prompt

    def test_false_like_env_values_disable_feature(self, monkeypatch):
        monkeypatch.setenv("SKILLBOT_PROGRESSIVE_SKILLS", "False")
        monkeypatch.setenv("SKILLBOT_SKILL_RERANK", "off")
        assert ChatClient._progressive_skills_enabled() is False
        assert ChatClient._skill_rerank_enabled() is False

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

    def test_install_is_explicitly_enabled_in_categorized_layout(self, tmp_skill_dir):
        root = Path(tmp_skill_dir) / "categorized-install"
        existing = root / "software-development" / "existing"
        existing.mkdir(parents=True)
        (existing / "SKILL.md").write_text(
            "---\nname: existing\ndescription: Existing\n---\n\nBody."
        )
        mgr = SkillManager(str(root))
        data = _make_zip(
            "installed",
            "---\nname: installed\ndescription: Installed\n---\n\nBody.",
        )
        zip_path = root / "installed.zip"
        zip_path.write_bytes(data)

        info = mgr.install(str(zip_path))

        assert info.enabled is True
        assert mgr.get_skill("installed").enabled is True
        assert SkillManager(str(root)).get_skill("installed").enabled is True

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

    def test_overwrite_preserves_enabled(self, mgr):
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


class TestLoaderRecoversFromBrokenFrontmatter:
    def test_missing_delimiters_warns_and_recovers(
        self, tmp_skill_dir, caplog
    ):
        skill = Path(tmp_skill_dir) / "broken-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text(
            "name: broken-skill\ndescription: pure yaml, no delimiters\n"
        )
        manager = SkillManager(tmp_skill_dir)

        with caplog.at_level("WARNING", logger="chat.skill"):
            skills = manager.list_skills()

        info = {item.name: item for item in skills}["broken-skill"]
        assert info.description == "pure yaml, no delimiters"
        assert any(
            "broken-skill" in record.message
            and "frontmatter" in record.message
            for record in caplog.records
        )

    def test_markdown_escaped_underscores_are_recovered(
        self, tmp_skill_dir, caplog
    ):
        skill = Path(tmp_skill_dir) / "rule_generate"
        skill.mkdir()
        (skill / "SKILL.md").write_text(
            "name: rule\\_generate\n"
            'description: "触发词：rule\\_generate、规则生成。"\n'
            "author: risk\\_recomm\\_team\n"
        )
        manager = SkillManager(tmp_skill_dir)

        with caplog.at_level("WARNING", logger="chat.skill"):
            skills = manager.list_skills()

        info = {item.name: item for item in skills}["rule_generate"]
        assert "\\" not in info.name
        assert "规则生成" in info.description

    def test_separator_noise_is_skipped(self, tmp_skill_dir):
        skill = Path(tmp_skill_dir) / "sample_prepare"
        skill.mkdir()
        (skill / "SKILL.md").write_text(
            "***\n\nname: sample\\_prepare\n"
            'description: "从 Hive 表抽取样本。"\n'
            + "-" * 80
            + "\n\n# Sample Prepare\n"
        )

        skills = SkillManager(tmp_skill_dir).list_skills()
        info = {item.name: item for item in skills}["sample_prepare"]
        assert info.name == "sample_prepare"

    def test_malformed_yaml_warns_and_recovers(
        self, tmp_skill_dir, caplog
    ):
        skill = Path(tmp_skill_dir) / "bad-yaml"
        skill.mkdir()
        (skill / "SKILL.md").write_text(
            '---\nname: bad-yaml\ndescription: "unterminated\n---\n\nBody.\n'
        )
        manager = SkillManager(tmp_skill_dir)

        with caplog.at_level("WARNING", logger="chat.skill"):
            names = {item.name for item in manager.list_skills()}

        assert "bad-yaml" in names
        assert any(
            "bad-yaml" in record.message and "malformed" in record.message
            for record in caplog.records
        )

    def test_valid_skill_does_not_warn(self, mgr, caplog):
        with caplog.at_level("WARNING", logger="chat.skill"):
            mgr.list_skills()
        assert not [
            record
            for record in caplog.records
            if "frontmatter" in record.message
        ]

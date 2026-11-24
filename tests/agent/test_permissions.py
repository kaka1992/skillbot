import os

import pytest

from agent.permissions import ExecutionMode, ToolPolicy, check_cell_permission


@pytest.fixture
def policy(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    artifacts = work / "artifacts" / "session"
    artifacts.mkdir(parents=True)
    return ToolPolicy(ExecutionMode.AUTO, work, (work,), artifacts)


@pytest.mark.parametrize("mode", list(ExecutionMode))
@pytest.mark.parametrize("tool", ["Bash", "Agent", "Task", "NotebookEdit", "mcp__db__write", "ExitPlanMode"])
def test_uncontrolled_tools_always_denied(policy, mode, tool):
    from dataclasses import replace
    assert not replace(policy, mode=mode).decide(tool, {}).allowed


def test_only_explicitly_enabled_skill_is_allowed(policy):
    from dataclasses import replace

    scoped = replace(policy, allowed_skills=frozenset({"risk-kb"}))
    assert scoped.decide("Skill", {"skill": "risk-kb"}).allowed
    assert not scoped.decide("Skill", {"skill": "unknown"}).allowed
    assert not scoped.decide("Skill", {}).allowed
    assert not replace(
        scoped,
        denied_tools=frozenset({"Skill"}),
    ).decide("Skill", {"skill": "risk-kb"}).allowed


@pytest.mark.parametrize("mode", [ExecutionMode.DEFAULT, ExecutionMode.PLAN, ExecutionMode.EDIT])
@pytest.mark.parametrize("tool", ["Write", "Edit"])
def test_readonly_modes_deny_writes(policy, mode, tool):
    from dataclasses import replace
    assert not replace(policy, mode=mode).decide(
        tool, {"file_path": str(policy.write_root / "ok.txt")},
    ).allowed


def test_read_allowed_write_scoped(policy):
    assert policy.decide("Read", {"file_path": str(policy.cwd / "data.csv")}).allowed
    assert policy.decide("Write", {"file_path": str(policy.write_root / "ok.txt")}).allowed
    assert not policy.decide("Write", {"file_path": str(policy.cwd / "source.py")}).allowed


@pytest.mark.parametrize("path", ["../outside.txt", "/etc/passwd", ".env", ".claude/settings.json"])
def test_read_rejects_outside_or_hidden(policy, path):
    assert not policy.decide("Read", {"file_path": path}).allowed


def test_symlink_escape_and_hardlink_denied(policy, tmp_path):
    outside = tmp_path / "secret"
    outside.write_text("secret")
    link = policy.write_root / "alias"
    link.symlink_to(outside)
    assert not policy.decide("Write", {"file_path": str(link)}).allowed
    hard = policy.write_root / "hard"
    os.link(outside, hard)
    assert not policy.decide("Read", {"file_path": str(hard)}).allowed
    assert not policy.decide("Write", {"file_path": str(hard)}).allowed
    assert not policy.decide("Grep", {"path": str(policy.write_root), "pattern": "."}).allowed


def test_write_root_cannot_be_redirected(policy, tmp_path):
    policy.write_root.rmdir()
    policy.write_root.symlink_to(tmp_path, target_is_directory=True)
    assert not policy.decide("Write", {"file_path": str(policy.write_root / "escape")}).allowed


@pytest.mark.parametrize("pattern", ["../**/*", "/etc/*"])
def test_glob_cannot_escape(policy, pattern):
    assert not policy.decide("Glob", {"path": str(policy.cwd), "pattern": pattern}).allowed


def test_recursive_search_does_not_expose_hidden_file(policy):
    (policy.cwd / ".env").write_text("secret")
    assert not policy.decide("Grep", {"path": str(policy.cwd), "pattern": "."}).allowed


def test_restrictions_only_narrow(policy):
    from dataclasses import replace
    p = replace(policy, allowed_tools=frozenset({"Bash", "Read"}), denied_tools=frozenset({"Read"}))
    assert not p.decide("Bash", {"command": "echo x"}).allowed
    assert not p.decide("Read", {"file_path": str(policy.cwd / "data.csv")}).allowed


@pytest.mark.parametrize("mode,auto,allowed", [
    ("plan", False, False), ("plan", True, False),
    ("default", False, False), ("default", True, False),
    ("edit", False, True), ("edit", True, False),
    ("execute", True, True), ("auto", True, True),
])
def test_cell_authorization(mode, auto, allowed):
    assert check_cell_permission(mode, auto).allowed is allowed


def test_unknown_mode_fails_closed():
    with pytest.raises(ValueError):
        check_cell_permission("bypassPermissions", True)

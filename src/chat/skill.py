"""Cross-agent skill management — install, list, uninstall, prompt injection."""

from __future__ import annotations

import json
import logging
import re
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

import yaml

_log = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\s*\r?\n(.*?)\r?\n---\s*(?:\r?\n|$)", re.DOTALL)
_STATE_FILE = ".skill_state.json"


@dataclass
class SkillInfo:
    name: str
    description: str
    path: str
    enabled: bool = False
    body: str = ""


class SkillManager:
    """Manage skills in a directory: list, install from .zip, uninstall.

    Enable/disable state is persisted in ``.skill_state.json`` inside the
    skill directory.  All installed skills default to enabled.
    """

    def __init__(self, skill_dir: str) -> None:
        self._dir = Path(skill_dir)
        self._disabled: set[str] = set()
        self._load_state()

    # ------------------------------------------------------------------
    # state persistence
    # ------------------------------------------------------------------

    @property
    def _state_path(self) -> Path:
        return self._dir / _STATE_FILE

    def _load_state(self) -> None:
        try:
            data = json.loads(self._state_path.read_text(encoding="utf-8"))
            self._disabled = set(data.get("disabled", []))
        except Exception:
            self._disabled = set()

    def _save_state(self) -> None:
        if not self._dir.is_dir():
            self._dir.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(
            json.dumps({"disabled": sorted(self._disabled)}, indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # discovery
    # ------------------------------------------------------------------

    def list_skills(self) -> list[SkillInfo]:
        """List all installed skills with enable status."""
        skills: list[SkillInfo] = []
        if not self._dir.is_dir():
            return skills
        for md_file in sorted(self._dir.glob("*/SKILL.md")):
            info = self._parse_skill(md_file)
            if info:
                info.enabled = info.name not in self._disabled
                skills.append(info)
        return skills

    def get_skill(self, name: str) -> SkillInfo | None:
        """Get a single skill by name."""
        md = self._dir / name / "SKILL.md"
        if not md.is_file():
            return None
        info = self._parse_skill(md)
        if info:
            info.enabled = info.name not in self._disabled
        return info

    # ------------------------------------------------------------------
    # install / uninstall
    # ------------------------------------------------------------------

    def install(self, zip_path: str) -> SkillInfo:
        """Install a skill from a .zip file.

        The zip must contain a single top-level directory whose name
        becomes the skill name. That directory must contain SKILL.md.
        New skills default to enabled.
        """
        zpath = Path(zip_path)
        if not zpath.is_file():
            raise FileNotFoundError(f"zip not found: {zip_path}")
        if zpath.suffix != ".zip":
            raise ValueError(f"expected .zip file, got: {zpath.suffix}")

        with tempfile.TemporaryDirectory(prefix="skillbot-install-") as tmp:
            with zipfile.ZipFile(zpath, "r") as zf:
                zf.extractall(tmp)

            tmp_path = Path(tmp)
            entries = list(tmp_path.iterdir())

            if not entries:
                raise ValueError("zip is empty")

            # Find the skill root: if zip extracts a single dir, use it;
            # otherwise use the extraction dir itself
            if len(entries) == 1 and entries[0].is_dir():
                skill_root = entries[0]
            else:
                skill_root = tmp_path

            name = skill_root.name
            if name.startswith(".") or name in ("__pycache__",):
                raise ValueError(f"invalid skill name: {name}")

            skill_md = skill_root / "SKILL.md"
            if not skill_md.is_file():
                raise ValueError(
                    f"SKILL.md not found in skill root. "
                    f"Expected: {skill_md}"
                )

            # Parse to validate frontmatter
            info = self._parse_skill(skill_md)
            if not info:
                raise ValueError("SKILL.md has invalid or missing YAML frontmatter")

            # Install
            self._dir.mkdir(parents=True, exist_ok=True)
            dest = self._dir / name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(skill_root, dest)
            _log.info("skill installed: %s (%d files)", name,
                       len(list(dest.rglob("*"))))

        # New skills default to enabled
        self._disabled.discard(name)
        self._save_state()

        return SkillInfo(name=info.name, description=info.description,
                         path=str(dest), enabled=True)

    def uninstall(self, name: str) -> None:
        """Remove an installed skill."""
        dest = self._dir / name
        if not dest.is_dir():
            raise FileNotFoundError(f"skill not found: {name}")
        shutil.rmtree(dest)
        self._disabled.discard(name)
        self._save_state()
        _log.info("skill uninstalled: %s", name)

    # ------------------------------------------------------------------
    # enable / disable (persisted)
    # ------------------------------------------------------------------

    def enable(self, name: str) -> None:
        """Enable a skill. Persisted to disk."""
        if not (self._dir / name / "SKILL.md").is_file():
            raise FileNotFoundError(f"skill not installed: {name}")
        self._disabled.discard(name)
        self._save_state()
        _log.info("skill enabled: %s", name)

    def disable(self, name: str) -> None:
        """Disable a skill. Persisted to disk."""
        if not (self._dir / name / "SKILL.md").is_file():
            raise FileNotFoundError(f"skill not installed: {name}")
        self._disabled.add(name)
        self._save_state()
        _log.info("skill disabled: %s", name)

    @property
    def active_skills(self) -> list[str]:
        """Return enabled skill names."""
        installed = set()
        if self._dir.is_dir():
            for md_file in self._dir.glob("*/SKILL.md"):
                installed.add(md_file.parent.name)
        return sorted(installed - self._disabled)

    @property
    def disabled_skills(self) -> list[str]:
        """Return disabled skill names (only for currently installed skills)."""
        installed = set()
        if self._dir.is_dir():
            for md_file in self._dir.glob("*/SKILL.md"):
                installed.add(md_file.parent.name)
        return sorted(self._disabled & installed)

    # ------------------------------------------------------------------
    # prompt injection
    # ------------------------------------------------------------------

    def inject_prompt(self, skills: list[str] | None = None) -> str:
        """Build a prompt injection string for the given skills.

        Used by agents without native skill support (deer-flow, nanobot,
        hermes-agent). The returned text should be prepended to the
        user message or injected into the system prompt.

        If *skills* is None, all active (enabled) skills are injected.
        """
        # Scan once — collect all skill info
        all_skills = {s.name: s for s in self.list_skills()}
        if skills is not None:
            names = skills
        else:
            names = [s.name for s in all_skills.values() if s.enabled]
        disabled = {name for name, s in all_skills.items() if not s.enabled}
        if not names and not disabled:
            return ""
        parts: list[str] = []
        for name in names:
            info = all_skills.get(name)
            if info and info.body:
                parts.append(f"# Skill: {info.name}\n{info.body}")
        result_parts: list[str] = []
        if parts:
            result_parts.append(
                "[System: The following skills are active for this conversation]\n\n"
                + "\n\n---\n\n".join(parts)
            )
        if disabled:
            result_parts.append(
                "[System: The following skills are DISABLED and must NOT be used: "
                + ", ".join(sorted(disabled)) + "]"
            )
        return "\n\n".join(result_parts) if result_parts else ""

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_skill(md_file: Path) -> SkillInfo | None:
        """Parse a SKILL.md file and return SkillInfo, or None."""
        try:
            text = md_file.read_text(encoding="utf-8")
        except Exception:
            return None

        m = _FRONTMATTER_RE.match(text)
        if not m:
            return None
        try:
            meta = yaml.safe_load(m.group(1)) or {}
        except Exception:
            return None

        name = meta.get("name", md_file.parent.name)
        description = meta.get("description", "")
        body = text[m.end():].strip()
        return SkillInfo(
            name=name,
            description=description,
            path=str(md_file.parent),
            body=body,
        )

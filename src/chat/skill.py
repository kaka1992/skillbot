"""Cross-agent skill management — install, list, uninstall, prompt injection."""

from __future__ import annotations

import json
import logging
import math
import os
import re
import shutil
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

import yaml

_log = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\s*\r?\n(.*?)\r?\n---\s*(?:\r?\n|$)", re.DOTALL)
_STATE_FILE = ".skill_state.json"
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_ASCII_TOKEN_RE = re.compile(r"[a-z0-9_]+")

_DEEPSEEK_BASE = os.environ.get(
    "DEEPSEEK_API_BASE", "https://api.deepseek.com"
).rstrip("/")
_DEEPSEEK_MODEL = os.environ.get("SKILLBOT_RERANK_MODEL", "deepseek-chat")

# Skills are discovered recursively, so a categorized layout
# (``<dir>/<category>/<skill>/SKILL.md``, e.g. hermes-agent) can hold dozens of
# skills. Enabling every one by default would inject hundreds of thousands of
# tokens of skill bodies into every message, so for *categorized* layouts only
# these categories are enabled by default. Flat layouts (e.g. claude-code's
# ``.claude/skills/<skill>/SKILL.md``) are unaffected and stay all-enabled.
_DEFAULT_ENABLED_CATEGORIES = {"software-development", "custom"}


def _est_tokens(text: str) -> int:
    """Return a rough token estimate for mixed Chinese and English text."""
    return len(text) * 10 // 35


def _tokenize(text: str) -> list[str]:
    """Tokenize mixed Chinese and English text without extra dependencies."""
    text = text.lower()
    tokens: list[str] = []
    for match in _ASCII_TOKEN_RE.finditer(text):
        token = match.group(0)
        tokens.append(token)
        if "_" in token:
            tokens.extend(part for part in token.split("_") if part)

    cjk = _CJK_RE.findall(text)
    tokens.extend(cjk)
    tokens.extend(cjk[i] + cjk[i + 1] for i in range(len(cjk) - 1))
    return tokens


def _clean_macos_junk(root: Path) -> None:
    """Remove macOS resource forks and __MACOSX dirs from extracted zip."""
    for item in list(root.rglob("*")):
        if item.name == "__MACOSX" or item.name.startswith("._"):
            try:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
            except Exception:
                pass


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
    skill directory. Explicit installs default to enabled; recursively
    discovered categorized skills follow the category policy above.
    """

    def __init__(self, skill_dir: str) -> None:
        self._dir = Path(skill_dir)
        self._disabled: set[str] = set()
        self._enabled: set[str] = set()   # skills the user explicitly enabled (overrides default policy)
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
            self._enabled = set(data.get("enabled", []))
        except Exception:
            self._disabled = set()
            self._enabled = set()

    def _save_state(self) -> None:
        if not self._dir.is_dir():
            self._dir.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(
            json.dumps(
                {"disabled": sorted(self._disabled), "enabled": sorted(self._enabled)},
                indent=2,
            ),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # discovery
    # ------------------------------------------------------------------

    def list_skills(self) -> list[SkillInfo]:
        """List all installed skills with enable status.

        Discovery is recursive: both a flat layout
        (``<dir>/<skill>/SKILL.md``) and a categorized one
        (``<dir>/<category>/<skill>/SKILL.md``) are supported.
        """
        skills: list[SkillInfo] = []
        if not self._dir.is_dir():
            return skills
        for md in self._discover_skill_mds():
            info = self._parse_skill(md)
            if info:
                info.enabled = self._is_enabled(info.name, md)
                skills.append(info)
        skills.sort(key=lambda s: s.name.lower())
        return skills

    def _discover_skill_mds(self) -> list[Path]:
        """Recursively find every SKILL.md under the skill directory.

        A directory that directly contains a SKILL.md is treated as a skill
        root; recursion does not descend into it (skills don't nest inside
        skills). Hidden dirs (``.git``, ``.skill_state.json`` parent, etc.) are
        skipped.
        """
        found: list[Path] = []

        def _walk(d: Path) -> None:
            try:
                entries = sorted(d.iterdir())
            except Exception:
                return
            md = self._find_skill_md(d)
            if md is not None:
                found.append(md)
                return  # this dir IS a skill — don't recurse into it
            for e in entries:
                if e.is_dir() and not e.name.startswith(".") and e.name != "__pycache__":
                    _walk(e)

        _walk(self._dir)
        return found

    def _is_enabled(self, name: str, md: Path) -> bool:
        """Default-enable policy for a discovered skill.

        Explicit user state in ``.skill_state.json`` always wins. For skills the
        user hasn't touched:

        * **Flat** layout (every skill sits directly under ``_dir``, e.g.
          claude-code) → all enabled.
        * **Categorized** layout (skills live under ``_dir/<category>/...``,
          e.g. hermes-agent) → only skills whose top-level category is in
          :data:`_DEFAULT_ENABLED_CATEGORIES` are enabled. A skill placed
          directly under ``_dir`` in an otherwise-categorized tree (e.g.
          ``yuanbao``) is treated as an uncategorized skill and left disabled,
          so injection stays bounded.
        """
        if name in self._disabled:
            return False
        if name in self._enabled:
            return True
        # Not explicitly set by the user — apply default policy.
        try:
            rel = md.parent.relative_to(self._dir)
        except Exception:
            return True
        parts = rel.parts
        if not self._is_categorized():
            return True  # flat layout → enable everything
        if len(parts) <= 1:
            return False  # uncategorized skill in a categorized tree → off by default
        return parts[0] in _DEFAULT_ENABLED_CATEGORIES

    def _is_categorized(self) -> bool:
        """True if this skill dir uses a nested ``<category>/<skill>`` layout.

        A layout is categorized if any discovered SKILL.md is more than one
        level below ``_dir``. The cache is invalidated when this manager mutates
        the tree through install/uninstall.
        """
        cached = getattr(self, "_categorized_cache", None)
        if cached is not None:
            return cached
        result = False
        for md in self._discover_skill_mds():
            try:
                if len(md.parent.relative_to(self._dir).parts) > 1:
                    result = True
                    break
            except Exception:
                continue
        self._categorized_cache = result
        return result

    def _find_skill_md(self, skill_dir: Path) -> Path | None:
        """Find SKILL.md directly inside a directory, case-insensitive."""
        if not skill_dir.is_dir():
            return None
        try:
            for f in skill_dir.iterdir():
                if f.is_file() and f.name.lower() == "skill.md":
                    return f
        except Exception:
            return None
        return None

    def _find_skill_md_by_name(self, name: str) -> Path | None:
        """Locate a skill's SKILL.md by its (unique) name, searching recursively."""
        for md in self._discover_skill_mds():
            info = self._parse_skill(md)
            if info and info.name == name:
                return md
        # Fall back to directory-name match for skills without a name in frontmatter.
        for md in self._discover_skill_mds():
            if md.parent.name == name:
                return md
        return None

    def get_skill(self, name: str) -> SkillInfo | None:
        """Get a single skill by name (recursive lookup)."""
        md = self._find_skill_md_by_name(name)
        if not md:
            return None
        info = self._parse_skill(md)
        if info:
            info.enabled = self._is_enabled(info.name, md)
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
            entries = [e for e in tmp_path.iterdir()
                       if e.name not in ("__MACOSX",) and not e.name.startswith("._")]

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

            # Find SKILL.md case-insensitively
            skill_md = self._find_skill_md(skill_root)
            if not skill_md:
                files = [f.name for f in skill_root.iterdir()] if skill_root.is_dir() else []
                raise ValueError(
                    f"SKILL.md not found. Contents: {files or '(empty directory)'}"
                )

            # Parse to validate frontmatter
            info = self._parse_skill(skill_md, recover=False)
            if not info:
                raise ValueError("SKILL.md has invalid or missing YAML frontmatter")

            # Clean macOS resource forks before install
            _clean_macos_junk(skill_root)

            # Install
            self._dir.mkdir(parents=True, exist_ok=True)
            dest = self._dir / name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(skill_root, dest)
            self._categorized_cache = None
            _log.info("skill installed: %s (%d files)", name,
                       len(list(dest.rglob("*"))))

        # New skills default to enabled
        self._disabled.discard(info.name)
        self._enabled.add(info.name)
        self._save_state()

        return SkillInfo(name=info.name, description=info.description,
                         path=str(dest), enabled=True)

    def uninstall(self, name: str) -> None:
        """Remove an installed skill."""
        md = self._find_skill_md_by_name(name)
        dest = md.parent if md else (self._dir / name)
        if not dest.is_dir():
            raise FileNotFoundError(f"skill not found: {name}")
        shutil.rmtree(dest)
        self._categorized_cache = None
        self._disabled.discard(name)
        self._enabled.discard(name)
        self._save_state()
        _log.info("skill uninstalled: %s", name)

    # ------------------------------------------------------------------
    # enable / disable (persisted)
    # ------------------------------------------------------------------

    def enable(self, name: str) -> None:
        """Enable a skill. Persisted to disk."""
        if not self._find_skill_md_by_name(name):
            raise FileNotFoundError(f"skill not installed: {name}")
        self._disabled.discard(name)
        self._enabled.add(name)   # explicit override of the default-enable policy
        self._save_state()
        _log.info("skill enabled: %s", name)

    def disable(self, name: str) -> None:
        """Disable a skill. Persisted to disk."""
        if not self._find_skill_md_by_name(name):
            raise FileNotFoundError(f"skill not installed: {name}")
        self._disabled.add(name)
        self._enabled.discard(name)
        self._save_state()
        _log.info("skill disabled: %s", name)

    @property
    def active_skills(self) -> list[str]:
        """Return enabled skill names."""
        return sorted(s.name for s in self.list_skills() if s.enabled)

    @property
    def disabled_skills(self) -> list[str]:
        """Return disabled skill names (only for currently installed skills)."""
        return sorted(s.name for s in self.list_skills() if not s.enabled)

    # ------------------------------------------------------------------
    # retrieval
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        skills: list[str] | None = None,
    ) -> list[tuple[str, float]]:
        """Rank enabled skills by TF-IDF relevance over name and description."""
        if top_k <= 0:
            return []

        infos = {skill.name: skill for skill in self.list_skills()}
        if skills is None:
            pool = [skill for skill in infos.values() if skill.enabled]
        else:
            pool = [infos[name] for name in skills if name in infos]
        if not pool:
            return []

        documents: dict[str, list[str]] = {}
        for info in pool:
            name_tokens = _tokenize(info.name)
            description_tokens = _tokenize(info.description or "")
            documents[info.name] = name_tokens * 3 + description_tokens

        document_frequency: dict[str, int] = {}
        for tokens in documents.values():
            for token in set(tokens):
                document_frequency[token] = document_frequency.get(token, 0) + 1

        document_count = len(documents)
        inverse_frequency = {
            token: math.log(1 + document_count / (1 + count))
            for token, count in document_frequency.items()
        }
        query_tokens = set(_tokenize(query))

        scored: list[tuple[str, float]] = []
        for name, tokens in documents.items():
            term_frequency: dict[str, int] = {}
            for token in tokens:
                term_frequency[token] = term_frequency.get(token, 0) + 1
            score = sum(
                term_frequency[token] * inverse_frequency.get(token, 0.0)
                for token in query_tokens
                if token in term_frequency
            )
            if score > 0:
                scored.append((name, score))

        scored.sort(key=lambda item: (-item[1], item[0].lower()))
        return scored[:top_k]

    def rerank(
        self,
        query: str,
        candidates: list[str],
        top_k: int | None = None,
        timeout: int = 20,
    ) -> list[str]:
        """Best-effort semantic rerank of keyword candidates using DeepSeek."""
        if not candidates:
            return []
        if len(candidates) == 1:
            return candidates[:top_k] if top_k else candidates

        key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        if not key:
            _log.debug("skill rerank skipped: DEEPSEEK_API_KEY is not set")
            return candidates[:top_k] if top_k else candidates

        infos = {skill.name: skill for skill in self.list_skills()}
        catalog = "\n".join(
            f"- {name}: {(infos[name].description if name in infos else '')[:200]}"
            for name in candidates
        )
        allowed_names = json.dumps(candidates, ensure_ascii=False)
        prompt = (
            "You are a skill router. Rank the candidate skills from most to least "
            "relevant to the user request.\n\n"
            f"User request:\n{query}\n\n"
            f"Candidate skills:\n{catalog}\n\n"
            "Return only a JSON array using exactly these skill names: "
            f"{allowed_names}."
        )

        try:
            ranked = self._deepseek_rank(prompt, key, timeout)
        except Exception as exc:
            _log.warning("skill rerank failed; using keyword order (%s)", exc)
            return candidates[:top_k] if top_k else candidates

        candidate_set = set(candidates)
        seen: set[str] = set()
        result: list[str] = []
        for name in ranked:
            if name in candidate_set and name not in seen:
                result.append(name)
                seen.add(name)
        for name in candidates:
            if name not in seen:
                result.append(name)
                seen.add(name)
        return result[:top_k] if top_k else result

    @staticmethod
    def _deepseek_rank(prompt: str, key: str, timeout: int) -> list[str]:
        """Call DeepSeek chat and parse a JSON array of skill names."""
        body = json.dumps(
            {
                "model": _DEEPSEEK_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": 256,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{_DEEPSEEK_BASE}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read())
        content = data["choices"][0]["message"]["content"].strip()
        match = re.search(r"\[.*\]", content, re.DOTALL)
        if not match:
            raise ValueError(f"no JSON array in rerank response: {content[:120]!r}")
        parsed = json.loads(match.group(0))
        if not isinstance(parsed, list):
            raise ValueError("rerank response is not a JSON array")
        return [str(item) for item in parsed]

    # ------------------------------------------------------------------
    # prompt injection
    # ------------------------------------------------------------------

    def inject_prompt(
        self,
        skills: list[str] | None = None,
        progressive: bool = False,
        query: str | None = None,
        top_k: int = 5,
        rerank: bool = False,
        rerank_pool: int = 10,
    ) -> str:
        """Build a prompt injection string for the given skills.

        Used by agents without native skill support (deer-flow, nanobot,
        hermes-agent). The returned text should be prepended to the
        user message or injected into the system prompt.

        If *skills* is None, all active (enabled) skills are injected.

        Progressive mode injects only each skill's name, description, and
        ``SKILL.md`` path. When *query* is provided, keyword retrieval narrows
        the injected catalog to the most relevant skills; optional reranking
        semantically reorders that candidate pool.
        """
        all_skills = {s.name: s for s in self.list_skills()}
        if skills is not None:
            names = skills
        else:
            names = [s.name for s in all_skills.values() if s.enabled]

        if query:
            pool_size = max(top_k, rerank_pool) if rerank else top_k
            ranked = self.retrieve(query, top_k=pool_size, skills=names)
            names = [name for name, _ in ranked]
            if rerank and names:
                names = self.rerank(query, names, top_k=top_k)

        disabled = {name for name, s in all_skills.items() if not s.enabled}
        if not names and not disabled:
            return ""

        parts: list[str] = []
        per_skill_tokens: list[tuple[str, int]] = []
        for name in names:
            info = all_skills.get(name)
            if not info:
                continue
            if progressive:
                if not info.description:
                    continue
                entry = (
                    f"## {info.name}\n"
                    f"{info.description.strip()}\n"
                    f"To use this skill, read its full instructions: "
                    f"{info.path}/SKILL.md"
                )
            elif info.body:
                entry = f"# Skill: {info.name}\n{info.body}"
            else:
                continue
            parts.append(entry)
            per_skill_tokens.append((info.name, _est_tokens(entry)))

        result_parts: list[str] = []
        if parts:
            if progressive:
                result_parts.append(
                    "[System: The following skills are available. Each entry lists "
                    "its name, when to use it, and where to read its full "
                    "instructions. Only read a skill's SKILL.md when you decide "
                    "to use it.]\n\n"
                    + "\n\n".join(parts)
                )
            else:
                result_parts.append(
                    "[System: The following skills are active for this conversation]\n\n"
                    + "\n\n---\n\n".join(parts)
                )
        if disabled:
            result_parts.append(
                "[System: The following skills are DISABLED and must NOT be used: "
                + ", ".join(sorted(disabled)) + "]"
            )
        result = "\n\n".join(result_parts) if result_parts else ""
        self._log_injection_cost(progressive, per_skill_tokens, result)
        return result

    @staticmethod
    def _log_injection_cost(
        progressive: bool,
        per_skill_tokens: list[tuple[str, int]],
        result: str,
    ) -> None:
        """Log estimated prompt cost for observability."""
        if not per_skill_tokens:
            return
        mode = "progressive" if progressive else "full"
        total = _est_tokens(result)
        entry_total = sum(tokens for _, tokens in per_skill_tokens)
        _log.info(
            "skill injection [%s]: %d skills, ~%d tokens total "
            "(%d in skill entries)",
            mode,
            len(per_skill_tokens),
            total,
            entry_total,
        )
        for name, tokens in sorted(per_skill_tokens, key=lambda item: -item[1]):
            percent = tokens * 100 // entry_total if entry_total else 0
            _log.debug(
                "skill injection entry: name=%s tokens~%d share=%d%%",
                name,
                tokens,
                percent,
            )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_skill(md_file: Path, recover: bool = True) -> SkillInfo | None:
        """Parse a skill, recovering metadata on load but not on install."""
        try:
            text = md_file.read_text(encoding="utf-8")
        except Exception as exc:
            _log.warning("skill skipped: cannot read %s (%s)", md_file, exc)
            return None

        m = _FRONTMATTER_RE.match(text)
        if not m:
            if not recover:
                return None
            _log.warning(
                "%s has no valid YAML frontmatter; recovering metadata "
                "best-effort",
                md_file,
            )
            return SkillManager._recover_metadata(md_file, text)
        try:
            meta = yaml.safe_load(m.group(1)) or {}
        except Exception as exc:
            if not recover:
                return None
            _log.warning(
                "%s has malformed YAML frontmatter (%s); recovering metadata "
                "best-effort",
                md_file,
                exc,
            )
            return SkillManager._recover_metadata(md_file, text)

        name = meta.get("name", md_file.parent.name)
        description = meta.get("description", "")
        body = text[m.end():].strip()
        return SkillInfo(
            name=name,
            description=description,
            path=str(md_file.parent),
            body=body,
        )

    @staticmethod
    def _recover_metadata(md_file: Path, text: str) -> SkillInfo | None:
        """Recover name and description from malformed skill frontmatter."""
        name = ""
        description = ""
        for raw in text.splitlines():
            line = raw.replace("\\_", "_").strip()
            if not line or set(line) <= {"*", "-", " "}:
                continue
            if not name:
                match = re.match(
                    r"^-?\s*name\s*:\s*(.+)$", line, re.IGNORECASE
                )
                if match:
                    name = match.group(1).strip().strip("'\"")
                    continue
            if not description:
                match = re.match(
                    r"^-?\s*description\s*:\s*(.+)$", line, re.IGNORECASE
                )
                if match:
                    description = match.group(1).strip().strip("'\"")
            if name and description:
                break

        name = name or md_file.parent.name
        if not name:
            _log.warning("skill skipped: %s has no recoverable name", md_file)
            return None
        return SkillInfo(
            name=name,
            description=description,
            path=str(md_file.parent),
            body=text.strip(),
        )

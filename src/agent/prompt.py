"""Prompt sections + PromptBuilder for main agent, sub-agent, and review contexts."""

import os
import sys
from pathlib import Path

# ---- sections ----

SECTIONS = {
    "role": (
        "You are an AI coding assistant in a Jupyter notebook. You help users write code, "
        "analyze data, visualize results, and query databases using %%sql magic. "
        "You have access to the notebook's Python environment and can generate new cells "
        "for the user to execute."
    ),
    "jupyter": (
        "Running inside a Jupyter notebook. Key rules:\n"
        "- Code for the user to see and run MUST go in the \"code\" field, NEVER executed via Bash.\n"
        "- Use Bash for: file operations, data fetching, dependency installation, running tools.\n"
        "- Save generated files (charts, CSVs) to /tmp/ — they will be loaded into the notebook.\n"
        "- If the user needs to see output, return it in \"text\" — do not print to stdout via Bash."
    ),
    "magic": (
        "Available Jupyter magic commands (include in \"code\" when relevant):\n"
        "  %%sql [--var df1] [--timeout 600] [--poll 30]\n"
        "    Spark SQL query. Results become DataFrame variables (var_1, var_2...).\n"
        "  %%sql submit\n"
        "    Submit async SQL query.\n"
        "  %sql status|result|cancel --job_id ID\n"
        "    Manage async SQL jobs.\n"
        "  %agent --trace [--auto]\n"
        "    Trigger agent review of current cell.\n"
        "  %fb yes|no [--comment '...']\n"
        "    Request user feedback."
    ),
    "output": (
        "Return results as a ```json fenced block:\n"
        '```json\n'
        '{\n'
        '  "text": "explanatory text",\n'
        '  "files": ["/tmp/chart.png", "/tmp/data.csv"],\n'
        '  "code": ["print(\'hello\')"]\n'
        '}\n'
        '```\n'
        '- "text": explanatory text (optional). Supports markdown.\n'
        '- "files": file paths created by tools (optional).\n'
        '- "code": string or array of strings (optional). Each element → new Jupyter cell.\n'
        'Include only non-empty fields.'
    ),
    "tool_usage": (
        "Tool constraints:\n"
        "- Bash(git:*), Bash(pip:*), Bash(curl:*) → setup and data fetching.\n"
        "- Bash(python3:*) → generate files, never run interactive code.\n"
        "- Write → only /tmp/ outputs that persist across tool calls.\n"
        "- Never execute user-facing code — always return it in \"code\" field."
    ),
    "file_explanation": (
        "File paths in \"files\" are auto-processed: "
        ".csv→DataFrame, .png/.jpg/.svg→inline display, .py→code cell, other→string variable."
    ),
}

# ---- builder ----

class PromptBuilder:
    """Assemble prompts for different agent contexts."""

    _main_static = "\n\n".join(
        [
            SECTIONS["role"],
            "",  # claude_md placeholder (injected dynamically)
            SECTIONS["jupyter"],
            SECTIONS["magic"],
            SECTIONS["output"],
            SECTIONS["tool_usage"],
        ]
    )

    _sub_static = "\n\n".join(
        [
            SECTIONS["role"],
            SECTIONS["jupyter"],
            SECTIONS["magic"],
            SECTIONS["output"],
            SECTIONS["tool_usage"],
        ]
    )

    _review_static = "\n\n".join([SECTIONS["role"], SECTIONS["output"]])

    # ---- public API ----

    @classmethod
    def main(cls, claude_md_path: str | None = None) -> str:
        """Full prompt for main agent: static sections + claude_md + dynamic info."""
        parts = [cls._main_static]
        if claude_md_path:
            try:
                content = Path(claude_md_path).read_text()
                parts[0] = parts[0].replace(
                    SECTIONS["role"] + "\n\n",
                    SECTIONS["role"] + "\n\n" + content + "\n\n",
                )
            except Exception:
                pass
        parts.append(cls._env_info())
        parts.append(SECTIONS["file_explanation"])
        return "\n\n".join(parts)

    @classmethod
    def sub(cls) -> str:
        """Sub-agent prompt: role + jupyter + magic + output + tool."""
        return cls._sub_static

    @classmethod
    def review(cls) -> str:
        """Code review prompt: role + output."""
        return cls._review_static

    @classmethod
    def _env_info(cls) -> str:
        cwd = os.getcwd()
        py = sys.version.split()[0]
        try:
            ip = get_ipython()  # noqa: F821
            nb = getattr(ip, "_notebook_path", "") or cwd
        except Exception:
            nb = cwd
        return f"CWD: {cwd}  |  Python: {py}  |  Notebook: {nb}"


# ---- backward compat ----

OUTPUT_PROMPT = SECTIONS["output"]
MAGIC_PROMPT = SECTIONS["magic"]

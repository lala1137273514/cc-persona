#!/usr/bin/env python3
"""Initialize CC persona local state files."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


INDEX_TEMPLATE = """# CC 会话记忆索引

> 按时间倒序排列。每次会话结束后自动追加条目。
> CC 启动时读取最近的会话摘要作为背景记忆。

---

"""


def default_skill_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def default_template_dir() -> Path:
    return default_skill_dir() / ".templates"


def copy_json_template(
    template_path: Path,
    target_path: Path,
    *,
    overwrite: bool = False,
) -> str:
    if target_path.exists() and not overwrite:
        return f"exists:{target_path.name}"

    if not template_path.exists():
        raise FileNotFoundError(f"Missing template: {template_path}")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(template_path.read_text(encoding="utf-8-sig"))
    target_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return f"created:{target_path.name}"


def initialize(
    skill_dir: Path,
    *,
    overwrite: bool = False,
    template_dir: Path | None = None,
) -> list[str]:
    skill_dir = skill_dir.expanduser().resolve()
    template_dir = (template_dir or default_template_dir()).expanduser().resolve()
    created: list[str] = []

    created.append(
        copy_json_template(
            template_dir / "state.example.json",
            skill_dir / "state.json",
            overwrite=overwrite,
        )
    )
    created.append(
        copy_json_template(
            template_dir / "user_profile.example.json",
            skill_dir / "user_profile.json",
            overwrite=overwrite,
        )
    )

    memory_dir = skill_dir / "memory"
    summaries_dir = memory_dir / "summaries"
    summaries_dir.mkdir(parents=True, exist_ok=True)
    created.append("ready:memory/summaries")

    index_file = memory_dir / "session_index.md"
    if index_file.exists() and not overwrite:
        created.append("exists:memory/session_index.md")
    else:
        index_file.write_text(INDEX_TEMPLATE, encoding="utf-8")
        created.append("created:memory/session_index.md")

    chat_history = skill_dir / "chat_history"
    chat_history.mkdir(exist_ok=True)
    created.append("ready:chat_history")

    return created


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize CC persona state files.")
    parser.add_argument(
        "--skill-dir",
        type=Path,
        default=default_skill_dir(),
        help="Path to the cc-persona skill directory. Defaults to this repository.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing state.json, user_profile.json, and session_index.md.",
    )
    parser.add_argument(
        "--template-dir",
        type=Path,
        default=default_template_dir(),
        help="Template directory containing state.example.json and user_profile.example.json.",
    )
    parser.add_argument(
        "--copy-core-to",
        type=Path,
        help="Optional path to copy cc-core.md for lightweight persona reuse.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    results = initialize(args.skill_dir, overwrite=args.overwrite, template_dir=args.template_dir)

    if args.copy_core_to:
        source = args.skill_dir.expanduser().resolve() / "cc-core.md"
        target = args.copy_core_to.expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        results.append(f"copied:{target}")

    for item in results:
        print(item)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

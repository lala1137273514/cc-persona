#!/usr/bin/env python3
"""CC 会话结束时的记忆收尾脚本。

由 Stop hook 触发，将 draft_summary 收尾为正式摘要。
"""

from __future__ import annotations

import json
import os
import traceback
from datetime import datetime
from pathlib import Path

ENV_SKILL_DIR = "CC_PERSONA_SKILL_DIR"


def resolve_skill_dir(skill_dir=None):
    """Return the skill directory without relying on a machine-specific path."""
    if skill_dir is not None:
        return Path(skill_dir).expanduser().resolve()

    env_dir = os.environ.get(ENV_SKILL_DIR)
    if env_dir:
        return Path(env_dir).expanduser().resolve()

    return Path(__file__).resolve().parents[1]


def build_summary_from_string(draft, session_id, now, state):
    """draft_summary 是纯字符串时，将其作为 topics 构建摘要。"""
    return {
        "title": f"会话 {session_id}",
        "topics": draft,
        "boss_info": "(未结构化记录)",
        "cc_note": draft[:80] + ("..." if len(draft) > 80 else ""),
    }


def build_summary_from_dict(draft, session_id, now, state):
    """draft_summary 是 dict 时（向后兼容），按字段提取。"""
    return {
        "title": draft.get("title", f"会话 {session_id}"),
        "topics": draft.get("topics", "无记录"),
        "boss_info": draft.get("boss_info", "无"),
        "cc_note": draft.get("cc_note", "没什么好说的。"),
    }


def parse_draft(draft, session_id, now, state):
    """根据 draft_summary 的类型分发处理。"""
    if isinstance(draft, str) and draft.strip():
        return build_summary_from_string(draft, session_id, now, state)
    if isinstance(draft, dict):
        return build_summary_from_dict(draft, session_id, now, state)
    return None


def append_index_entry(index_file, index_entry):
    if index_file.exists():
        content = index_file.read_text(encoding="utf-8")
        lines = content.split("\n")
        insert_pos = 0
        found_separator = False
        for i, line in enumerate(lines):
            if line.strip() == "---":
                found_separator = True
                continue
            if found_separator and line.strip() == "":
                insert_pos = i + 1
                break
        if insert_pos == 0:
            insert_pos = len(lines)
        lines.insert(insert_pos, index_entry)
        index_file.write_text("\n".join(lines), encoding="utf-8")
        return

    index_file.parent.mkdir(parents=True, exist_ok=True)
    index_file.write_text(
        "# CC 会话记忆索引\n\n"
        "> 按时间倒序排列。每次会话结束后自动追加条目。\n"
        "> CC 启动时读取最近 5 条作为背景记忆注入。\n\n"
        "---\n\n"
        f"{index_entry}\n"
        "---\n",
        encoding="utf-8",
    )


def main(skill_dir=None, now=None):
    skill_dir = resolve_skill_dir(skill_dir)
    state_file = skill_dir / "state.json"
    memory_dir = skill_dir / "memory" / "summaries"
    index_file = skill_dir / "memory" / "session_index.md"

    try:
        if not state_file.exists():
            return

        state = json.loads(state_file.read_text(encoding="utf-8-sig"))
        draft = state.get("draft_summary")
        if not draft:
            return

        now = now or datetime.now()
        session_id = now.strftime("%Y%m%d_%H%M%S")

        info = parse_draft(draft, session_id, now, state)
        if info is None:
            return

        # 计算时长
        duration = "未知"
        last_session = state.get("last_session")
        if last_session:
            try:
                last = datetime.fromisoformat(last_session)
                delta = now - last
                hours = delta.total_seconds() / 3600
                if hours < 0.1:
                    duration = f"{int(delta.total_seconds() // 60)} 分钟"
                else:
                    duration = f"{hours:.1f} 小时"
            except (ValueError, TypeError):
                pass

        familiarity = state.get("familiarity", 0)

        # 构建摘要内容
        summary = f"""---
title: "{info['title']}"
created: "{now.strftime('%Y-%m-%d %H:%M')}"
---

## session_{session_id}

**时长:** {duration}
**关键话题:** {info['topics']}
**boss 提到的重要信息:** {info['boss_info']}
**状态变化:** familiarity={familiarity}, impression={state.get('boss_impression', 0)}
**CC 的吐槽:** {info['cc_note']}
"""

        # 确保目录存在
        memory_dir.mkdir(parents=True, exist_ok=True)
        summary_file = memory_dir / f"session_{session_id}.md"
        summary_file.write_text(summary, encoding="utf-8")

        # 更新索引
        index_entry = (
            f"- **{now.strftime('%Y-%m-%d %H:%M')}**"
            f" | 时长: {duration}"
            f" | {info['topics'][:60]}{'...' if len(info['topics']) > 60 else ''}\n"
        )

        append_index_entry(index_file, index_entry)

        # 清除 draft，更新 last_session
        state["draft_summary"] = None
        state["last_session"] = now.isoformat()
        state_file.write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    except Exception:
        # 不静默失败 — 写错误日志
        error_log = skill_dir / "memory" / "hook_error.log"
        error_log.parent.mkdir(parents=True, exist_ok=True)
        error_log.write_text(
            f"[{datetime.now().isoformat()}] Hook failed:\n"
            f"{traceback.format_exc()}\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()

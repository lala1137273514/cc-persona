from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import analyze_dataset
import extract_cc_candidates
import init_persona
import session_cleanup


class PersonaSkillTests(unittest.TestCase):
    def test_init_persona_creates_open_box_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "cc-persona"
            results = init_persona.initialize(skill_dir)

            self.assertIn("created:state.json", results)
            self.assertIn("created:user_profile.json", results)
            self.assertTrue((skill_dir / "state.json").exists())
            self.assertTrue((skill_dir / "user_profile.json").exists())
            self.assertTrue((skill_dir / "memory" / "session_index.md").exists())
            self.assertTrue((skill_dir / "memory" / "summaries").is_dir())

            state = json.loads((skill_dir / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["mood"], "normal")
            self.assertEqual(state["mood_level"], 1)

    def test_session_cleanup_converts_string_draft_to_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "cc-persona"
            init_persona.initialize(skill_dir)
            state_path = skill_dir / "state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["draft_summary"] = "修了 Stop hook 路径问题"
            state["familiarity"] = 12
            state["boss_impression"] = 2
            state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

            now = datetime(2026, 5, 11, 10, 30, 0)
            session_cleanup.main(skill_dir=skill_dir, now=now)

            updated = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertIsNone(updated["draft_summary"])
            self.assertEqual(updated["last_session"], now.isoformat())

            summary_file = skill_dir / "memory" / "summaries" / "session_20260511_103000.md"
            self.assertTrue(summary_file.exists())
            summary_text = summary_file.read_text(encoding="utf-8")
            self.assertIn("修了 Stop hook 路径问题", summary_text)

            index_text = (skill_dir / "memory" / "session_index.md").read_text(encoding="utf-8")
            self.assertIn("2026-05-11 10:30", index_text)

    def test_session_cleanup_converts_dict_draft_to_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "cc-persona"
            init_persona.initialize(skill_dir)
            state_path = skill_dir / "state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["draft_summary"] = {
                "title": "路径修复",
                "topics": "去掉硬编码路径",
                "boss_info": "希望开箱即用",
                "cc_note": "路径写死会翻车。",
            }
            state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

            session_cleanup.main(skill_dir=skill_dir, now=datetime(2026, 5, 11, 11, 0, 0))

            summary_text = (
                skill_dir / "memory" / "summaries" / "session_20260511_110000.md"
            ).read_text(encoding="utf-8")
            self.assertIn("路径修复", summary_text)
            self.assertIn("希望开箱即用", summary_text)

    def test_session_cleanup_accepts_windows_utf8_bom_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "cc-persona"
            init_persona.initialize(skill_dir)
            state_path = skill_dir / "state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["draft_summary"] = "PowerShell UTF8 BOM 兼容"
            state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8-sig")

            session_cleanup.main(skill_dir=skill_dir, now=datetime(2026, 5, 11, 12, 0, 0))

            summary_file = skill_dir / "memory" / "summaries" / "session_20260511_120000.md"
            self.assertTrue(summary_file.exists())
            self.assertIn("PowerShell UTF8 BOM", summary_file.read_text(encoding="utf-8"))

    def test_dataset_analysis_helpers_do_not_require_network(self) -> None:
        rows = [
            {"instruction": "为什么代码总有 bug？", "output": "因为需求会变。"},
            {"instruction": "工作好累怎么办？", "output": "先睡觉。"},
            {"instruction": "朋友怎么相处？", "output": "不是讨好，是边界。"},
        ]

        stats = analyze_dataset.analyze_rows(rows, sample_size=3, validation_size=2, seed=1)
        self.assertEqual(stats["sample_size"], 3)
        self.assertIn("幽默/反转", stats["category_distribution"])
        self.assertIn("哲理金句型", stats["style_distribution"])

    def test_candidate_extraction_helpers_do_not_require_network(self) -> None:
        rows = [
            {"instruction": "为什么代码总有 bug？", "output": "因为需求会变。"},
            {"instruction": "这功能怎么样？", "output": "不是不行，是麻烦。"},
            {"instruction": "工作好累", "output": "先睡。"},
        ]

        result, categories = extract_cc_candidates.extract_candidates(rows, sample_size=3, seed=1)
        self.assertEqual(result["sample_size"], 3)
        self.assertGreaterEqual(len(result["短刀流"]), 1)
        self.assertGreaterEqual(sum(categories.values()), 3)

    def test_data_script_help_does_not_require_datasets_package(self) -> None:
        for script_name in ["analyze_dataset.py", "extract_cc_candidates.py"]:
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / script_name), "--help"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("usage:", result.stdout)

    def test_docs_keep_tsundere_state_boundary_consistent(self) -> None:
        state_rules = (ROOT / "references" / "state_rules.md").read_text(encoding="utf-8")
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("mood_level += 1 | 不超过 4", state_rules)
        self.assertIn("mood_level -= 1 | 回到 normal 为止", state_rules)
        self.assertIn("收敛不是变温柔", state_rules)
        self.assertIn("人格示例集（19 个场景", skill)

    def test_docs_keep_priority_iron_law(self) -> None:
        """事实 > CC 风格 > 人性化 的优先级和 protected spans 不能被悄悄删掉。"""
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        core = (ROOT / "cc-core.md").read_text(encoding="utf-8")

        for doc_name, doc in (("SKILL.md", skill), ("cc-core.md", core)):
            self.assertIn("优先级铁律", doc, f"{doc_name} missing 优先级铁律 section")
            self.assertIn(
                "事实保真 > CC 风格 > 人性化收束",
                doc,
                f"{doc_name} missing the three-tier priority",
            )
            self.assertIn("Protected spans", doc, f"{doc_name} missing protected spans section")
            self.assertIn("commit hash", doc, f"{doc_name} missing commit hash in protected list")
            self.assertIn("错误码", doc, f"{doc_name} missing 错误码 in protected list")
            self.assertIn(
                "1:1",
                doc,
                f"{doc_name} missing the 1:1 preservation requirement for protected spans",
            )


if __name__ == "__main__":
    unittest.main()

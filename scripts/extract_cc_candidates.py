#!/usr/bin/env python3
"""Extract short CC-style candidate lines from the source dataset."""

from __future__ import annotations

import argparse
import collections
import json
import random
from pathlib import Path

DATASET_NAME = "LooksJuicy/Chinese-Emotional-Intelligence"
CC_STYLE_KEYWORDS = ["算了", "不过", "就这", "自己", "省得", "免得", "懒得", "罢了"]


def cc_candidate_score(row: dict) -> int:
    output = row["output"]
    checks = [
        "不是" in output and len(output) <= 40,
        output.startswith("因为") and len(output) <= 40,
        len(output) <= 15,
        any(pattern in output for pattern in ["难道", "你以为", "凭什么"]),
        any(pattern in output for pattern in ["不过是", "无非是", "就是", "在于"]),
        any(pattern in output for pattern in ["但", "却"]) and len(output) <= 40,
    ]
    return sum(1 for matched in checks if matched)


def classify_instruction(instruction: str) -> str:
    if any(keyword in instruction for keyword in ["喜欢", "爱", "分手", "恋爱"]):
        return "情感/恋爱"
    if any(keyword in instruction for keyword in ["人生", "意义", "命运", "活着"]):
        return "人生/哲理"
    if any(keyword in instruction for keyword in ["朋友", "别人", "相处", "社交"]):
        return "社交/人际"
    if any(keyword in instruction for keyword in ["难过", "伤心", "孤独", "累"]):
        return "负面情绪"
    if any(keyword in instruction for keyword in ["自己", "算了", "人类"]):
        return "自嘲/吐槽"
    if any(keyword in instruction for keyword in ["工作", "老板", "同事", "工资"]):
        return "工作/职场"
    if instruction.endswith("？") or instruction.endswith("?"):
        return "提问类"
    return "其他"


def compact_rows(rows) -> list[dict]:
    return [{"i": row["instruction"], "o": row["output"]} for row in rows]


def extract_candidates(dataset, *, sample_size: int, seed: int) -> tuple[dict, collections.Counter]:
    total = len(dataset)
    random.seed(seed)
    sampled_rows = [dataset[i] for i in random.sample(range(total), min(sample_size, total))]

    scored = [(cc_candidate_score(row), row) for row in sampled_rows]
    cc_candidates = [(score, row) for score, row in scored if score >= 1]
    cc_candidates.sort(key=lambda item: -item[0])

    result = {
        "total_rows": total,
        "sample_size": len(sampled_rows),
        "反转结构_不是但": compact_rows(
            row for _, row in cc_candidates if "不是" in row["output"] and len(row["output"]) <= 40
        )[:15],
        "哲理金句_因为": compact_rows(
            row for _, row in cc_candidates if row["output"].startswith("因为")
        )[:15],
        "短刀流": compact_rows(row for _, row in cc_candidates if len(row["output"]) <= 15)[:15],
        "反差_但却": compact_rows(
            row
            for _, row in cc_candidates
            if any(pattern in row["output"] for pattern in ["但", "却"]) and len(row["output"]) <= 40
        )[:15],
        "_CC风格语料_精选": compact_rows(row for _, row in cc_candidates)[:20],
        "_关键词命中语料": compact_rows(
            row for row in sampled_rows if any(keyword in row["output"] for keyword in CC_STYLE_KEYWORDS)
        )[:20],
    }

    categories = collections.Counter(classify_instruction(dataset[i]["instruction"]) for i in range(total))
    return result, categories


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract CC-style candidate lines.")
    parser.add_argument("--dataset", default=DATASET_NAME)
    parser.add_argument("--split", default="train")
    parser.add_argument("--sample-size", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).with_name("cc_candidates.json"),
    )
    return parser.parse_args(argv)


def print_preview(result: dict, categories: collections.Counter) -> None:
    print("=" * 50)
    print(f"Sample analysis complete: {result['sample_size']} rows")
    print("=" * 50)
    for key in ["反转结构_不是但", "哲理金句_因为", "短刀流", "反差_但却"]:
        print(f"\n【{key}】{len(result[key])} 条")
        for item in result[key][:5]:
            print(f"  Q: {item['i']}")
            print(f"  A: {item['o']}")
            print()

    print("\n【全量分类统计】")
    total = sum(categories.values())
    for category, count in categories.most_common():
        print(f"  {category}: {count} ({count / total * 100:.1f}%)")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    from datasets import load_dataset

    dataset = load_dataset(args.dataset, split=args.split)
    result, categories = extract_candidates(dataset, sample_size=args.sample_size, seed=args.seed)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print_preview(result, categories)
    print(f"\nWritten to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

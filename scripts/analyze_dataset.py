#!/usr/bin/env python3
"""Analyze Chinese emotional-intelligence samples for CC speech material."""

from __future__ import annotations

import argparse
import collections
import json
import random
from pathlib import Path

DATASET_NAME = "LooksJuicy/Chinese-Emotional-Intelligence"

CAT_PATTERNS = {
    "情感/恋爱": ["喜欢", "爱", "分手", "恋爱", "爱情", "感情", "男女", "对象", "暧昧", "心动", "告白"],
    "人生/哲理": ["人生", "意义", "活着", "命运", "理想", "梦想", "成熟", "成长", "成功"],
    "社交/人际": ["朋友", "友谊", "社交", "相处", "别人", "关系", "同事", "同学"],
    "负面情绪": ["难过", "伤心", "孤独", "寂寞", "累了", "心累", "疲惫", "焦虑", "痛苦", "低谷"],
    "幽默/反转": ["为什么", "怎么办", "怎样", "如何", "哪个", "会怎样", "是不是"],
    "工作/职场": ["工作", "职场", "老板", "同事", "加班", "升职", "辞职", "工资"],
    "家庭/亲情": ["爸爸", "妈妈", "父母", "孩子", "家人", "家庭", "结婚"],
    "哲理/诗词": ["天若有情", "最是", "所谓", "莫过于", "何必", "无非"],
    "自嘲/吐槽": ["自己", "我这个人", "我就是", "像我", "算了", "罢了", "人类"],
}

STYLE_PATTERNS = {
    "哲理金句型": ["因为", "就是", "不过是", "无非是", "所谓", "在于"],
    "反转/意外的": ["不是", "才", "但", "却", "然而", "反而", "其实"],
    "反问/怼人型": ["难道", "你以", "凭什么", "谁让", "以为", "有意思吗"],
    "标签/格言型": ["——", "，就是", "的。 ", "了。"],
}


def classify_instruction(instruction: str) -> str:
    for category, patterns in CAT_PATTERNS.items():
        if any(pattern in instruction for pattern in patterns):
            return category
    if instruction.endswith("？") or instruction.endswith("?"):
        return "提问类(未分类)"
    return "其他"


def classify_style(output: str) -> str:
    for style, patterns in STYLE_PATTERNS.items():
        if any(pattern in output for pattern in patterns):
            return style
    if len(output) <= 12:
        return "短句/一刀流"
    return "叙述/故事型"


def length_bucket(text: str) -> str:
    length = len(text)
    if length <= 10:
        return "1-10字"
    if length <= 20:
        return "11-20字"
    if length <= 40:
        return "21-40字"
    if length <= 60:
        return "41-60字"
    return "61字以上"


def analyze_rows(dataset, *, sample_size: int, validation_size: int, seed: int) -> dict:
    total = len(dataset)
    random.seed(seed)
    sample_indices = random.sample(range(total), min(sample_size, total))
    sample_rows = [dataset[i] for i in sample_indices]

    lengths_inst = [len(row["instruction"]) for row in sample_rows]
    lengths_out = [len(row["output"]) for row in sample_rows]

    categories = collections.Counter(classify_instruction(row["instruction"]) for row in sample_rows)
    styles = collections.Counter(classify_style(row["output"]) for row in sample_rows)
    len_buckets = collections.Counter(length_bucket(row["output"]) for row in sample_rows)

    start_patterns = collections.Counter(row["output"][:2] for row in sample_rows if len(row["output"]) >= 2)
    end_patterns = collections.Counter(row["output"][-2:] for row in sample_rows if len(row["output"]) >= 2)

    typical_examples = {}
    for category, patterns in [
        ("情感/恋爱", ["喜欢", "爱", "分手"]),
        ("人生/哲理", ["人生", "意义"]),
        ("幽默/反转", ["为什么"]),
        ("自嘲/吐槽", ["自己", "算了"]),
        ("社交/人际", ["朋友", "别人"]),
        ("负面情绪", ["难过", "累了"]),
    ]:
        examples = []
        for row in sample_rows:
            if any(pattern in row["instruction"] for pattern in patterns):
                examples.append({"instruction": row["instruction"], "output": row["output"]})
            if len(examples) >= 5:
                break
        if examples:
            typical_examples[category] = examples

    validation_indices = random.sample(range(total), min(validation_size, total))
    validation_rows = [dataset[i] for i in validation_indices]
    validation_categories = collections.Counter(
        classify_instruction(row["instruction"]) for row in validation_rows
    )

    return {
        "total_rows": total,
        "sample_size": len(sample_rows),
        "instruction_len": {
            "min": min(lengths_inst),
            "max": max(lengths_inst),
            "avg": round(sum(lengths_inst) / len(lengths_inst), 1),
            "median": sorted(lengths_inst)[len(lengths_inst) // 2],
        },
        "output_len": {
            "min": min(lengths_out),
            "max": max(lengths_out),
            "avg": round(sum(lengths_out) / len(lengths_out), 1),
            "median": sorted(lengths_out)[len(lengths_out) // 2],
        },
        "category_distribution": dict(categories.most_common()),
        "top_start_phrases": dict(start_patterns.most_common(20)),
        "top_end_phrases": dict(end_patterns.most_common(20)),
        "style_distribution": dict(styles.most_common()),
        "output_len_distribution": {
            bucket: len_buckets.get(bucket, 0)
            for bucket in ["1-10字", "11-20字", "21-40字", "41-60字", "61字以上"]
        },
        "typical_examples": typical_examples,
        "validation_category": dict(validation_categories.most_common()),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze CC-style source dataset.")
    parser.add_argument("--dataset", default=DATASET_NAME)
    parser.add_argument("--split", default="train")
    parser.add_argument("--sample-size", type=int, default=2000)
    parser.add_argument("--validation-size", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).with_name("dataset_analysis.json"),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    from datasets import load_dataset

    dataset = load_dataset(args.dataset, split=args.split)
    stats = analyze_rows(
        dataset,
        sample_size=args.sample_size,
        validation_size=args.validation_size,
        seed=args.seed,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Done. Analysis written to {args.output}")
    print(f"Avg instruction length: {stats['instruction_len']['avg']} chars")
    print(f"Avg output length: {stats['output_len']['avg']} chars")
    print(f"Top categories: {list(stats['category_distribution'].keys())[:5]}")
    print(f"Top styles: {list(stats['style_distribution'].keys())[:5]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

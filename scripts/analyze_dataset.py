import json, re, random, collections
from datasets import load_dataset

dataset = load_dataset("LooksJuicy/Chinese-Emotional-Intelligence", split="train")
total = len(dataset)
print(f"Total rows: {total}")

# ── 1. 全量采样：取 2000 条随机样本做深度分析 ──
random.seed(42)
sample_indices = random.sample(range(total), 2000)
sample_rows = [dataset[i] for i in sample_indices]

# ── 2. 基础统计 ──
lengths_inst = [len(r["instruction"]) for r in sample_rows]
lengths_out  = [len(r["output"]) for r in sample_rows]

stats = {
    "total_rows": total,
    "sample_size": 2000,
    "instruction_len": {
        "min": min(lengths_inst), "max": max(lengths_inst),
        "avg": round(sum(lengths_inst)/len(lengths_inst), 1),
        "median": sorted(lengths_inst)[len(lengths_inst)//2]
    },
    "output_len": {
        "min": min(lengths_out), "max": max(lengths_out),
        "avg": round(sum(lengths_out)/len(lengths_out), 1),
        "median": sorted(lengths_out)[len(lengths_out)//2]
    }
}

# ── 3. 自动分类：通过 instruction 的关键词匹配 ──
categories = collections.Counter()
cat_patterns = {
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
for r in sample_rows:
    inst = r["instruction"]
    matched = False
    for cat, patterns in cat_patterns.items():
        if any(p in inst for p in patterns):
            categories[cat] += 1
            matched = True
            break
    if not matched:
        # try heuristic: instruction ends with ? → 幽默/反转
        if inst.endswith("？") or inst.endswith("?"):
            categories["提问类(未分类)"] += 1
        else:
            categories["其他"] += 1

stats["category_distribution"] = dict(categories.most_common())

# ── 4. 出口句式分析（output 的开头和结尾模式） ──
start_patterns = collections.Counter()
end_patterns = collections.Counter()
for r in sample_rows:
    out = r["output"]
    if len(out) >= 2:
        start = out[:2]
        start_patterns[start] += 1
    if len(out) >= 2:
        end = out[-2:]
        end_patterns[end] += 1

stats["top_start_phrases"] = dict(start_patterns.most_common(20))
stats["top_end_phrases"] = dict(end_patterns.most_common(20))

# ── 5. 按句式特点分类 (更有价值的分类法) ──
style_categories = collections.Counter()
style_patterns = {
    "哲理金句型": ["因为", "就是", "不过是", "无非是", "所谓", "在于"],
    "反转/意外的": ["不是", "才", "但", "却", "然而", "反而", "其实"],
    "反问/怼人型": ["难道", "你以", "凭什么", "谁让", "以为", "有意思吗"],
    "标签/格言型": ["——", "，就是", "的。 ", "了。"],
}
for r in sample_rows:
    out = r["output"]
    matched = False
    for style, patterns in style_patterns.items():
        if any(p in out for p in patterns):
            style_categories[style] += 1
            matched = True
            break
    if not matched:
        if len(out) <= 12:
            style_categories["短句/一刀流"] += 1
        else:
            style_categories["叙述/故事型"] += 1

stats["style_distribution"] = dict(style_categories.most_common())

# ── 6. 按 output 长度分档 ──
len_buckets = {"1-10字":0, "11-20字":0, "21-40字":0, "41-60字":0, "61字以上":0}
for r in sample_rows:
    l = len(r["output"])
    if l <= 10: len_buckets["1-10字"] += 1
    elif l <= 20: len_buckets["11-20字"] += 1
    elif l <= 40: len_buckets["21-40字"] += 1
    elif l <= 60: len_buckets["41-60字"] += 1
    else: len_buckets["61字以上"] += 1
stats["output_len_distribution"] = len_buckets

# ── 7. 抽取各分类的典型代表（每条分类抽 5 条） ──
typical_examples = {}
for cat, patterns in [("情感/恋爱", ["喜欢", "爱", "分手"]),
                      ("人生/哲理", ["人生", "意义"]),
                      ("幽默/反转", ["为什么"]),
                      ("自嘲/吐槽", ["自己", "算了"]),
                      ("社交/人际", ["朋友", "别人"]),
                      ("负面情绪", ["难过", "累了"])]:
    examples = []
    for r in sample_rows:
        if any(p in r["instruction"] for p in patterns):
            examples.append({"instruction": r["instruction"], "output": r["output"]})
            if len(examples) >= 5:
                break
    if examples:
        typical_examples[cat] = examples

stats["typical_examples"] = typical_examples

# ── 8. 全文量二次验证：对所有样本再随机取 200 条复制分析一致性 ──
validation_indices = random.sample(range(total), 200)
validation_rows = [dataset[i] for i in validation_indices]
val_categories = collections.Counter()
for r in validation_rows:
    inst = r["instruction"]
    matched = False
    for cat, patterns in cat_patterns.items():
        if any(p in inst for p in patterns):
            val_categories[cat] += 1
            matched = True
            break
    if not matched:
        val_categories["其他"] += 1
stats["validation_200_category"] = dict(val_categories.most_common())

# ── 输出 ──
with open("C:\\Users\\11372\\.claude\\skills\\cc-persona\\scripts\\dataset_analysis.json", "w", encoding="utf-8") as f:
    json.dump(stats, f, ensure_ascii=False, indent=2)

print("Done. Analysis written to dataset_analysis.json")
print(f"\nKey stats:")
print(f"  Avg instruction length: {stats['instruction_len']['avg']} chars")
print(f"  Avg output length: {stats['output_len']['avg']} chars")
print(f"  Top categories: {list(stats['category_distribution'].keys())[:5]}")
print(f"  Top styles: {list(stats['style_distribution'].keys())[:5]}")
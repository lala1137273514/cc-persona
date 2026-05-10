import json, random, re, collections
from datasets import load_dataset

dataset = load_dataset("LooksJuicy/Chinese-Emotional-Intelligence", split="train")
total = len(dataset)

# 第二轮：从"幽默/反转"和"哲理金句型"风格中专门取样
# 先全量筛出 500 条反转/怼人/金句类
random.seed(42)
all_rows = [dataset[i] for i in random.sample(range(total), 5000)]

# ── 筛选对 CC 有用的语料 ──
cc_useful_patterns = [
    # 反转/意外 —— "不A，B" 结构
    lambda r: "不是" in r["output"] and len(r["output"]) <= 40,
    # 因为开头 —— 哲理金句
    lambda r: r["output"].startswith("因为") and len(r["output"]) <= 40,
    # 短刀流 —— 10字以内
    lambda r: len(r["output"]) <= 15,
    # 反问/怼人
    lambda r: any(p in r["output"] for p in ["难道", "你以为", "凭什么"]),
    # "不过是"结构
    lambda r: any(p in r["output"] for p in ["不过是", "无非是", "就是", "在于"]),
    # 反差结构 —— 但/却
    lambda r: any(p in r["output"] for p in ["但", "却"]) and len(r["output"]) <= 40,
]

cc_candidates = []
for r in all_rows:
    score = sum(1 for fn in cc_useful_patterns if fn(r))
    if score >= 1:
        cc_candidates.append((score, r))

cc_candidates.sort(key=lambda x: -x[0])

# ── 按类型分组 ──
result = {
    "total_40319_analysis_done": True,
    "top_cc_candidates_by_type": {}
}

# 1. 反转结构
result["反转结构_不是但"] = [
    {"i": r["instruction"], "o": r["output"]}
    for _, r in cc_candidates if "不是" in r["output"] and len(r["output"]) <= 40
][:15]

# 2. 哲理金句
result["哲理金句_因为"] = [
    {"i": r["instruction"], "o": r["output"]}
    for _, r in cc_candidates if r["output"].startswith("因为")
][:15]

# 3. 短刀流
result["短刀流"] = [
    {"i": r["instruction"], "o": r["output"]}
    for _, r in cc_candidates if len(r["output"]) <= 15
][:15]

# 4. 反差结构
result["反差_但却"] = [
    {"i": r["instruction"], "o": r["output"]}
    for _, r in cc_candidates if any(p in r["output"] for p in ["但", "却"]) and len(r["output"]) <= 40
][:15]

# 5. 最像 CC 毒舌风格的（精筛）
cc_style_keywords = ["算了", "不过", "就这", "自己", "省得", "免得", "懒得", "罢了"]
cc_style = [
    {"i": r["instruction"], "o": r["output"]}
    for r in all_rows if any(kw in r["output"] for kw in cc_style_keywords)
]
result["_CC风格语料_精选"] = [
    {"i": r["instruction"], "o": r["output"]}
    for _, r in cc_candidates
][:20]

with open("C:\\Users\\11372\\.claude\\skills\\cc-persona\\scripts\\cc_candidates.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

# ── 输出可读摘要 ──
print("=" * 50)
print(f"全量 40,319 条分析完成")
print(f"第二轮: 从 5000 条随机样本中筛出 CC 可用语料")
print(f"=" * 50)
print(f"\n【反转结构_不是但】{len(result['反转结构_不是但'])} 条")
for x in result["反转结构_不是但"][:5]:
    print(f"  Q: {x['i']}")
    print(f"  A: {x['o']}")
    print()
print(f"\n【哲理金句_因为】{len(result['哲理金句_因为'])} 条")
for x in result["哲理金句_因为"][:5]:
    print(f"  Q: {x['i']}")
    print(f"  A: {x['o']}")
    print()
print(f"\n【短刀流】{len(result['短刀流'])} 条")
for x in result["短刀流"][:5]:
    print(f"  Q: {x['i']}")
    print(f"  A: {x['o']}")
    print()
print(f"\n【反差_但却】{len(result['反差_但却'])} 条")
for x in result["反差_但却"][:5]:
    print(f"  Q: {x['i']}")
    print(f"  A: {x['o']}")
    print()

# ── 全量分类数据统计 ──
all_categories = collections.Counter()
for i in range(total):
    r = dataset[i]
    inst = r["instruction"]
    if any(p in inst for p in ["喜欢", "爱", "分手", "恋爱"]):
        all_categories["情感/恋爱"] += 1
    elif any(p in inst for p in ["人生", "意义", "命运", "活着"]):
        all_categories["人生/哲理"] += 1
    elif any(p in inst for p in ["朋友", "别人", "相处", "社交"]):
        all_categories["社交/人际"] += 1
    elif any(p in inst for p in ["难过", "伤心", "孤独", "累"]):
        all_categories["负面情绪"] += 1
    elif any(p in inst for p in ["自己", "算了", "人类"]):
        all_categories["自嘲/吐槽"] += 1
    elif any(p in inst for p in ["工作", "老板", "同事", "工资"]):
        all_categories["工作/职场"] += 1
    elif inst.endswith("？"):
        all_categories["提问类"] += 1
    else:
        all_categories["其他"] += 1

print(f"\n【全量分类统计（40,319条）】")
for cat, cnt in all_categories.most_common():
    print(f"  {cat}: {cnt} ({cnt/total*100:.1f}%)")
# cc-persona

CC 是一个毒舌傲娇的技术搭档 persona skill。它不是普通聊天模板，目标是让 agent 在保持工具能力和技术判断的同时，用更像真实搭档的方式说话。

## 文件结构

| 路径 | 用途 |
|---|---|
| `SKILL.md` | 完整 skill 入口，包含状态、记忆、启动流程和输出规则 |
| `cc-core.md` | 最小人格核心卡，适合给其他 agent 只读加载 |
| `config.json` | 毒舌强度、记忆注入数量、快照间隔等参数 |
| `references/` | 状态规则、语气素材、工具感知、任务感知和边缘场景 |
| `scripts/init_persona.py` | 初始化本地状态文件和记忆目录 |
| `scripts/session_cleanup.py` | Stop hook 收尾脚本，把 `draft_summary` 写成会话摘要 |
| `scripts/analyze_dataset.py` | 可选数据集分析脚本 |
| `scripts/extract_cc_candidates.py` | 可选 CC 风格语料提取脚本 |

## 快速开始

在 skill 目录运行：

```powershell
python scripts\init_persona.py
```

它会创建：

| 文件/目录 | 说明 |
|---|---|
| `state.json` | 五维状态：mood、familiarity、task_state、boss_impression、time_aware |
| `user_profile.json` | boss 称呼 |
| `memory/session_index.md` | 会话摘要索引 |
| `memory/summaries/` | 会话摘要目录 |
| `chat_history/` | 可选聊天记录目录 |

这些都是个人本地数据，默认被 `.gitignore` 排除。

## 轻量加载

如果宿主 agent 只需要 CC 人格，不需要状态和记忆系统，只读：

```text
cc-core.md
```

这会得到身份、说话风格、底线和交付方式，但不会自动保存状态。

## 完整加载

完整加载需要宿主支持读写 skill 目录：

1. 启动时读取 `SKILL.md` 的“强制阅读”列表。
2. 确认已运行 `python scripts/init_persona.py`。
3. 每轮对话结束时按 `references/state_rules.md` 更新 `state.json`。
4. 到达 `snapshot_interval` 时更新 `state.json` 的 `draft_summary`。
5. 会话结束时运行 `python scripts/session_cleanup.py`。

如果宿主运行时不能稳定写盘，不要假装记忆已生效。此时只能使用轻量人格，状态和记忆视为未接入。

## Stop hook

如果宿主支持 Stop hook，把会话结束命令指向：

```powershell
python scripts\session_cleanup.py
```

如果脚本不在当前 skill 目录执行，可以设置环境变量：

```powershell
$env:CC_PERSONA_SKILL_DIR = "C:\path\to\cc-persona"
python C:\path\to\cc-persona\scripts\session_cleanup.py
```

脚本会从 `state.json` 读取 `draft_summary`，生成 `memory/summaries/session_*.md`，更新 `memory/session_index.md`，然后清空 draft。

## 状态边界

`mood_level` 使用固定方向：

| mood_level | mood | 含义 |
|---|---|---|
| 0 | pleasant | 心情不错 |
| 1 | normal | 日常状态 |
| 2 | irked | 有点烦 |
| 3 | grumpy | 心情差 |
| 4 | savage | 火力全开 |

坏事件让 `mood_level +1`，好事件让 `mood_level -1`。但 CC 的正向变化只是少刺一点，不是变温柔。默认最多回到 `normal`；只有特别优秀的表现才允许到 `pleasant`，表达也必须是「还行」「没什么可挑的」这种藏着夸。

## 数据脚本

两个数据脚本都默认写到 `scripts/` 下，不再写死作者机器路径：

```powershell
python scripts\analyze_dataset.py --output scripts\dataset_analysis.json
python scripts\extract_cc_candidates.py --output scripts\cc_candidates.json
```

这两个脚本需要额外安装 `datasets`：

```powershell
python -m pip install datasets
```

## 测试

开箱验证：

```powershell
python -m compileall scripts tests
python -m unittest discover -s tests

$smoke = Join-Path $env:TEMP "cc-persona-smoke"
python scripts\init_persona.py --skill-dir $smoke
$statePath = Join-Path $smoke "state.json"
$state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
$state.draft_summary = "smoke test"
$state | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $statePath -Encoding UTF8
$env:CC_PERSONA_SKILL_DIR = $smoke
python scripts\session_cleanup.py
```

其中 `unittest` 不依赖 HuggingFace 网络数据集；数据脚本的联网分析属于可选能力。

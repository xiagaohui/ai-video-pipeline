#!/usr/bin/env python3
"""Local video-generation pipeline MVP.

This script owns the topic-to-publish video production workflow:

- select and validate a video topic
- create a standard video project
- generate agent-specific task packs for Codex / Claude Code / generic agents
- turn an approved voiceover into a structured scene plan
- scaffold a reusable HyperFrames project from that scene plan
- validate gates and package finished deliverables

It intentionally uses only the Python standard library so the pipeline can be
open-sourced without forcing a runtime stack on contributors.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import textwrap
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "video-pipeline"
PROJECTS = PIPELINE / "projects"
CONFIG = PIPELINE / "config"
STATE = PIPELINE / "state"

DEFAULT_BRAND_OPENING = "大家好，欢迎来到今天的 AI 工程观察。"
DEFAULT_BRAND_CLOSING = "以上就是今天的内容，希望对你有启发，我们下期见。"
BRAND_OPENING = os.environ.get("AI_VIDEO_PIPELINE_OPENING", DEFAULT_BRAND_OPENING)
BRAND_CLOSING = os.environ.get("AI_VIDEO_PIPELINE_CLOSING", DEFAULT_BRAND_CLOSING)

GATES = [
    "topic_selection",
    "material_type",
    "intent",
    "research",
    "voiceover_review",
    "voiceover_self_approved",
    "scene_plan",
    "visual_logic",
    "cover_hook",
    "logic_visual_alignment",
    "pronunciation",
    "audio",
    "video_render",
    "cover",
    "publish_copy",
    "qa",
    "package",
]

BLOCKING_GATE_ORDER = [
    "topic_selection",
    "material_type",
    "intent",
    "research",
    "voiceover_review",
    "voiceover_self_approved",
    "scene_plan",
    "visual_logic",
    "cover_hook",
    "logic_visual_alignment",
    "pronunciation",
    "video_render",
    "cover",
    "publish_copy",
    "qa",
    "package",
]

PRINCIPLES = """\
## 最高优先级原则

1. 立意必须从观众视角出发，真的有价值，并且便于传播。
   立意要回答“观众看完能得到什么”，可以是可实操方法、新判断框架、新观点，或真实痛点建议。
   好立意必须能被普通观众一句话转述，并且最好带有纠偏、反差或行动建议。

2. 表达必须从观众视角出发，让观众看得懂、听得懂。
   口播、标题、字幕、封面和配图都要避免过于抽象，尽量使用现实工作中的名词、角色、动作和场景。

3. 配图必须简洁，并且图内、图与图之间都有清楚逻辑。
   让观众能够看懂永远是第一优先级。每张图只服务一个核心意思，图内元素必须有明确阅读顺序、因果、对比或流程关系；前后图片必须沿同一条主线递进。图内元素不得互相覆盖、贴边或被裁切，字幕不得遮挡图片里的核心文字、节点、结论条和流程箭头。
"""

VISUAL_QA_HARD_RULES = """\
## Post-EP04 Render QA Rules

These rules came from repeated fixes after the Loop Engineering EP04 workflow. They are blocking checks, not visual preferences.

1. **Clean stale segments before every re-render.** Remove old `source/segments/s*.png`, `s*.mp4`, `segments.txt`, and `silent.mp4` so old frames cannot pollute QA.
2. **Trust only `segments.txt` for used clips.** `qa/segment_contact_sheets/` must read the segments that were actually concatenated, not every file in the folder.
3. **Final QA must use final MP4 frames.** Source images without subtitles are only layout drafts; final contact sheets must come from the rendered MP4.
4. **Video, subtitles, and audio share one timeline.** Scene switches should be derived from final audio/VTT timing, not estimated storyboard durations.
5. **Subtitles are max two lines.** They must not be clipped or cover conclusion bars, flow nodes, key cards, or arrows. Fix the layout before shrinking subtitles.
6. **Run internal visual collision checks.** Text, arrows, nodes, cards, titles, and takeaway bars must not overlap, touch edges, or be cropped; arrowheads must be visible.
7. **Check subtitle-image alignment.** A subtitle must explain the current frame, not the previous or next one.
8. **Use clean solid backgrounds by default.** Avoid grid, checker, and noise textures unless they do not hurt text readability.
9. **Protect English term spacing.** Do not merge `Claude Code`, `Context Engineering`, or `Prompt Engineering` into `ClaudeCode` or `ContextEngineering`.
10. **Keep publish copy synchronized.** If the cover title changes, update title, short title, description, QA notes, and platform cover assets.
"""

DEFAULT_AGENTS = {
    "version": 1,
    "profiles": {
        "codex": {
            "name": "Codex",
            "description": "OpenAI Codex style coding agent. Uses AGENTS.md and Markdown task prompts.",
            "instruction_file": "AGENTS.md",
            "prompt_dir": "agent-pack/codex",
            "handoff_style": "workspace-files",
        },
        "claude-code": {
            "name": "Claude Code",
            "description": "Claude Code style agent. Uses CLAUDE.md and Markdown task prompts.",
            "instruction_file": "CLAUDE.md",
            "prompt_dir": "agent-pack/claude-code",
            "handoff_style": "workspace-files",
        },
        "generic": {
            "name": "Generic Agent",
            "description": "Vendor-neutral agent profile. Uses README.md and Markdown task prompts.",
            "instruction_file": "AGENT_TASKS.md",
            "prompt_dir": "agent-pack/generic",
            "handoff_style": "workspace-files",
        },
    },
}

MATERIAL_TYPES = {
    "unknown": {
        "label": "待判断",
        "video_focus": "先判断材料类型，再决定视频结构",
        "default_structure": "素材类型 -> 观众收益 -> 立意 -> 结构",
        "common_trap": "直接套统一模板，导致观点、科普、新功能和工程实践混在一起",
    },
    "opinion": {
        "label": "观点文章 / 访谈",
        "video_focus": "提炼一个可传播判断",
        "default_structure": "观点是什么 -> 对观众意味着什么 -> 你该怎么做",
        "common_trap": "只复述作者说了什么，没有给观众建议",
    },
    "explainer": {
        "label": "科普 / 概念解释",
        "video_focus": "让观众听懂一个概念",
        "default_structure": "常见误区 -> 人话解释 -> 现实例子 -> 使用边界",
        "common_trap": "堆定义和术语，缺少现实例子",
    },
    "product_feature": {
        "label": "产品新功能",
        "video_focus": "讲清解决什么问题，以及背后的工作方式变化",
        "default_structure": "功能表象 -> 背后变化 -> 谁能用 -> 怎么落地 -> 边界提醒",
        "common_trap": "只做 release note，或者把机制当成立意",
    },
    "engineering_practice": {
        "label": "工程实践 / 技术博客",
        "video_focus": "给方法和流程",
        "default_structure": "问题场景 -> 方法框架 -> 实操步骤 -> 风险清单",
        "common_trap": "讲成概念科普，没有给可执行步骤",
    },
    "case_study": {
        "label": "案例复盘",
        "video_focus": "提炼可复用经验",
        "default_structure": "案例做了什么 -> 为什么有效 -> 普通人怎么借鉴",
        "common_trap": "只讲案例很厉害，没有抽出可迁移方法",
    },
    "open_source_tool": {
        "label": "开源项目 / 工具",
        "video_focus": "判断能不能用、适合谁用",
        "default_structure": "解决什么问题 -> 怎么用 -> 适合谁 -> 坑在哪里",
        "common_trap": "只介绍仓库功能，不讲使用门槛和适用场景",
    },
    "official_doc": {
        "label": "官方文档",
        "video_focus": "翻译成使用建议",
        "default_structure": "官方说了什么 -> 关键变化 -> 使用场景 -> 注意边界",
        "common_trap": "逐条翻译文档，没有提炼用户该怎么做",
    },
    "hot_concept": {
        "label": "热点概念",
        "video_focus": "借热点讲落地",
        "default_structure": "大家误解什么 -> 真正关键是什么 -> 如何落地",
        "common_trap": "只解释名词，蹭热点但不给方法",
    },
}

TOPIC_SELECTION_CRITERIA = [
    ("viewer_value", "观众价值", "观众看完是否能得到方法、判断、新观点或真实痛点建议"),
    ("spread_hook", "传播钩子", "是否有纠偏、反差、痛点、方法或结果，能不能被一句话转述"),
    ("source_strength", "来源强度", "来源是否可信、足够新、足够具体，是否有一手材料支撑"),
    ("visual_potential", "视觉潜力", "能否做成清晰信息图、流程图、对比图或案例图"),
    ("actionability", "可执行性", "观众能否带走检查清单、操作步骤或决策框架"),
    ("compliance", "合规安全", "是否能避开版权、夸大、敏感表达和平台误读风险"),
]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def today() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().date().isoformat()


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"https?://", "", value)
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value)
    value = value.strip("-")
    if not value:
        return "video"
    asciiish = re.sub(r"[^a-z0-9-]+", "", value)
    return asciiish[:72].strip("-") or "video"


def project_dir(slug: str) -> Path:
    path = Path(slug)
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] in {"video-pipeline", "deliverables"}:
        return ROOT / path
    return PROJECTS / slug


def ensure_base_dirs() -> None:
    for path in [PIPELINE, PROJECTS, CONFIG, STATE]:
        path.mkdir(parents=True, exist_ok=True)


def agents_config() -> dict[str, Any]:
    return read_json(CONFIG / "agents.json", DEFAULT_AGENTS)


def load_project(path_or_slug: str) -> tuple[Path, dict[str, Any]]:
    path = project_dir(path_or_slug)
    state_path = path / "state.json"
    if not state_path.exists():
        raise SystemExit(f"Project state not found: {state_path}")
    return path, read_json(state_path, {})


def save_project(path: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = now_iso()
    write_json(path / "state.json", state)


def init_cmd(_: argparse.Namespace) -> None:
    ensure_base_dirs()
    if not (CONFIG / "agents.json").exists():
        write_json(CONFIG / "agents.json", DEFAULT_AGENTS)
    write_text(PIPELINE / "README.md", pipeline_readme())
    print(f"Initialized {PIPELINE}")


def pipeline_readme() -> str:
    return """\
# 视频生成流水线

本目录负责“选题到发布”的短视频生产流程。它不绑定具体 Agent，Codex、Claude Code 或其他 Agent 都通过同一套项目文件、门禁和任务包协作。

## 基本命令

```bash
python3 scripts/video_pipeline.py init
python3 scripts/video_pipeline.py create --slug demo --title "AI 能读懂的知识库怎么建" --topic-hook "AI 能读懂的企业知识库怎么建" --topic-reason "Google OKF 给了可落地方法" --audience-pain "企业知识散乱，Agent 读不懂" --material-type engineering_practice --thesis "把知识整理成 AI 可用的工程资产"
python3 scripts/video_pipeline.py agent-pack demo --agent codex
python3 scripts/video_pipeline.py scene-plan demo --voiceover process/03_voiceover_confirmed.md
python3 scripts/video_pipeline.py scaffold-hyperframes demo
python3 scripts/video_pipeline.py qa demo
python3 scripts/video_pipeline.py package demo
```

## 门禁

1. 选题判断：候选素材是否值得做，钩子、痛点、观众收益和风险是否成立。
2. 素材类型判断：观点、科普、新功能、工程实践、案例、工具、官方文档或热点概念。
3. 立意、观众价值和传播性确认。
4. 口播多视角审阅。
5. 主 agent 结合独立审阅完成口播自确认。
6. 配图逻辑确认。
7. 视频、封面和发布包 QA。

## 立意传播测试

- 观众能不能用一句话转述这条视频。
- 这个选题为什么现在值得做，观众痛点是否真实。
- 这句话是否包含明确收益，而不是只复述材料。
- 标题、封面和开头是否围绕同一句主判断。
- 是否有纠偏、反差、行动建议或痛点解决。
- 视频结构是否匹配素材类型；新功能和新机制必须追问背后的工作方式变化，不能把机制当立意。

任何 Agent 都不能绕过这些门禁；但默认由执行 Agent 自审、自改、自确认，不再等待用户确认中间产物。
"""


def create_cmd(args: argparse.Namespace) -> None:
    ensure_base_dirs()
    slug = args.slug or f"{today()}-{slugify(args.title)}"
    path = project_dir(slug)
    if path.exists() and not args.force:
        raise SystemExit(f"Project already exists: {path}. Use --force to reuse it.")

    for folder in ["process", "agent-pack", "source", "cover", "qa", "final", "publish"]:
        (path / folder).mkdir(parents=True, exist_ok=True)

    state = {
        "schema_version": 1,
        "slug": path.name,
        "title": args.title,
        "topic_hook": args.topic_hook,
        "topic_reason": args.topic_reason,
        "audience_pain": args.audience_pain,
        "material_type": args.material_type,
        "thesis": args.thesis,
        "viewer_value": args.viewer_value or "",
        "source_url": args.source_url or "",
        "source_file": args.source_file or "",
        "duration_target": args.duration,
        "language": args.language,
        "format": args.format,
        "primary_agent": args.agent,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "gates": {gate: "not_started" for gate in GATES},
        "artifacts": {},
        "notes": [],
    }
    state["gates"]["topic_selection"] = "approved" if args.topic_reason and args.audience_pain else "needs_agent_review"
    state["gates"]["material_type"] = "approved" if args.material_type != "unknown" else "needs_agent_review"
    state["gates"]["intent"] = "approved" if args.thesis else "needs_agent_review"
    write_json(path / "state.json", state)
    write_text(path / "process" / "00_topic_selection.md", topic_selection_doc(state))
    write_text(path / "process" / "00_material_type.md", material_type_doc(state))
    write_text(path / "process" / "00_intent.md", intent_doc(state))
    write_text(path / "process" / "01_research_brief.md", research_stub(state))
    write_text(path / "process" / "02_voiceover_draft.md", voiceover_draft_stub(state))
    write_text(path / "process" / "03_voiceover_confirmed.md", confirmed_voiceover_stub(state))
    write_text(path / "process" / "04_pronunciation_notes.md", pronunciation_notes_stub(state))
    write_text(path / "process" / "05_visual_rules.md", visual_rules_doc(state))
    write_text(path / "README.md", project_readme(state))
    write_agent_pack(path, state, args.agent)

    print(f"Created video project: {path}")
    print(f"Next: fill {path / 'process/03_voiceover_confirmed.md'} after audience-perspective review passes.")


def topic_selection_doc(state: dict[str, Any]) -> str:
    criteria_rows = "\n".join(
        f"| {key} | {label} | {description} | 1-5 | |"
        for key, label, description in TOPIC_SELECTION_CRITERIA
    )
    return f"""\
# 00 选题门禁

选题决定这条视频是否值得做。进入素材类型、立意和口播前，必须先判断：这条素材能不能形成一个对观众有价值、能传播、能讲清楚、能合规发布的短视频。

## 当前选题

- 标题：{state['title']}
- 选题钩子：{state.get('topic_hook') or '待补充'}
- 为什么现在值得做：{state.get('topic_reason') or '待补充'}
- 观众痛点：{state.get('audience_pain') or '待补充'}
- 观众收益：{state.get('viewer_value') or '待补充'}
- 来源 URL：{state.get('source_url') or '待补充'}
- 来源文件：{state.get('source_file') or '待补充'}

## 候选选题评分

| 维度 | 名称 | 判断问题 | 分数 | 备注 |
| --- | --- | --- | --- | --- |
{criteria_rows}

## 进入下一步前必须确认

- [ ] 这个选题不是单纯“有材料”，而是真的有观众收益。
- [ ] 选题钩子能被一句话转述。
- [ ] 观众痛点是真实的，不是作者自己想讲的内部问题。
- [ ] 来源足够可信，事实边界能说清。
- [ ] 能形成清晰画面，不会只能堆文字。
- [ ] 有合规边界，不靠夸大、误导或未经授权素材吸引点击。
"""


def material_type_doc(state: dict[str, Any]) -> str:
    material_type = state.get("material_type", "unknown")
    info = MATERIAL_TYPES.get(material_type, MATERIAL_TYPES["unknown"])
    rows = "\n".join(
        f"| `{key}` | {value['label']} | {value['video_focus']} | {value['default_structure']} |"
        for key, value in MATERIAL_TYPES.items()
        if key != "unknown"
    )
    return f"""\
# 00 素材类型门禁

素材类型决定视频结构。进入立意和口播前，必须先判断原始材料到底是什么类型，不能把观点、科普、产品新功能、工程实践和案例复盘硬套同一套结构。

## 当前判断

- 素材类型：`{material_type}` / {info['label']}
- 视频重点：{info['video_focus']}
- 默认结构：{info['default_structure']}
- 常见坑：{info['common_trap']}

## 可选类型

| 类型 | 含义 | 视频重点 | 默认结构 |
| --- | --- | --- | --- |
{rows}

## 进入下一步前必须确认

- [ ] 已判断原始材料类型。
- [ ] 当前立意符合该类型的视频重点。
- [ ] 默认结构已按材料类型调整，而不是套统一模板。
- [ ] 已写出这种材料最容易踩的坑。
- [ ] 如果是产品新功能或新机制，已经追问背后的工作方式变化，不能把机制直接当立意。
"""


def intent_doc(state: dict[str, Any]) -> str:
    material_type = state.get("material_type", "unknown")
    info = MATERIAL_TYPES.get(material_type, MATERIAL_TYPES["unknown"])
    return f"""\
# 00 立意门禁

{PRINCIPLES}

## 项目

- 标题：{state['title']}
- 素材类型：`{material_type}` / {info['label']}
- 默认结构：{info['default_structure']}
- 立意：{state['thesis'] or '待确认'}
- 观众价值：{state['viewer_value'] or '待补充'}
- 来源 URL：{state['source_url'] or '待补充'}
- 来源文件：{state['source_file'] or '待补充'}
- 目标时长：{state['duration_target']} 秒
- 画幅：{state['format']}

## 进入口播前必须确认

- [ ] 观众看完能得到明确收益。
- [ ] 立意能被观众一句话转述。
- [ ] 标题、封面和前 15 秒开头都围绕同一句立意展开。
- [ ] 传播钩子明确：纠偏、反差、行动建议或痛点解决。
- [ ] 不是单纯复述材料或 release note。
- [ ] 立意符合素材类型；如果是新功能/新机制，已经讲清工作方式变化。
- [ ] 可以用现实名词讲清楚。
- [ ] 合规和版权边界已写清。
- [ ] 这条视频适合做成短视频，而不是长文或纯工具文档。
"""


def research_stub(state: dict[str, Any]) -> str:
    material_type = state.get("material_type", "unknown")
    info = MATERIAL_TYPES.get(material_type, MATERIAL_TYPES["unknown"])
    return f"""\
# 01 研究材料包

## 来源

- URL：{state['source_url'] or '待补充'}
- 文件：{state['source_file'] or '待补充'}

## 立意

{state['thesis'] or '待确认'}

## 素材类型

- 类型：`{material_type}` / {info['label']}
- 视频重点：{info['video_focus']}
- 默认结构：{info['default_structure']}
- 常见坑：{info['common_trap']}

## 必须补齐

- 素材类型是否判断正确，是否需要改类型。
- 一手来源的关键事实。
- 观众真实痛点。
- 一句话转述版立意。
- 可执行建议。
- 不能夸大的边界。
- 适合转成图的 3-6 个逻辑节点。
"""


def voiceover_draft_stub(state: dict[str, Any]) -> str:
    return f"""\
# 02 口播初稿

请在这里放口播初稿。要求：

- 第一幕必须包含固定开场：{BRAND_OPENING}
- 最后一幕必须包含固定结束语：{BRAND_CLOSING}
- 每一节默认采用“观点 -> 意味着什么 -> 给观众的建议”。
- 开头 15 秒必须说清一句可传播主判断。
- 英文专有名词保留英文，不翻译、不音译。
- 多音字、英文名、产品名必须在音频生成前单独做发音稿检查。
- 写完后必须经过多个观众视角审阅，由主 agent 汇总修改并自确认后继续。
"""


def confirmed_voiceover_stub(state: dict[str, Any]) -> str:
    return f"""\
# 03 审阅通过口播稿

把多视角审阅并修改通过后的最终口播稿放在这里。流水线只会从这个文件生成正式分镜。

```text
{BRAND_OPENING}

这里替换为审阅通过后的口播正文。

{BRAND_CLOSING}
```
"""


def pronunciation_notes_stub(_: dict[str, Any]) -> str:
    return """\
# 04 发音稿与多音字检查

音频生成前必须补齐本文件，并将 `pronunciation` 门禁更新为 `approved`。

## 硬规则

- 英文产品名、人名、公司名保留英文，不做中文音译或翻译。
- 多音字、行业术语、缩写必须单独列出。
- 发音稿只允许调整停顿、连读和读音提示，不得改事实、观点、术语和字幕文案。

## 发音表

| 原文 | 正确读音 | 备注 |
| --- | --- | --- |
| 超级个体长出来 | 长 = zhang | 表示“生长出来”，不是 chang |
| 反直觉 | 觉 = jue | 如果 TTS 读成 jiao，优先改写成“出乎意料” |
"""


def visual_rules_doc(_: dict[str, Any]) -> str:
    return f"""\
# 05 配图与封面规则

{PRINCIPLES}

## 信息图硬规则

- 每张图只讲一个核心意思。
- 图内必须有明确阅读顺序：从左到右、从上到下、问题到方法、输入到输出。
- 前后图必须递进：上一张讲为什么，下一张讲怎么做。
- 宁可少放内容，也不要让观众猜图在讲什么。
- 做 3 秒扫视测试：能不能看出主题、主线和观众收益。
- 封面必须一图概括同一句可传播立意，不能只放功能名或组件名。

{VISUAL_QA_HARD_RULES}
"""


def project_readme(state: dict[str, Any]) -> str:
    material_type = state.get("material_type", "unknown")
    info = MATERIAL_TYPES.get(material_type, MATERIAL_TYPES["unknown"])
    return f"""\
# {state['title']}

## 选题

- 钩子：{state.get('topic_hook') or '待补充'}
- 为什么值得做：{state.get('topic_reason') or '待补充'}
- 观众痛点：{state.get('audience_pain') or '待补充'}

## 素材类型

`{material_type}` / {info['label']}

默认结构：{info['default_structure']}

## 立意

{state['thesis'] or '待确认'}

## 目录

- `process/`：研究、口播、分镜、视觉规则。
- `agent-pack/`：给 Codex / Claude Code / generic agent 的任务包。
- `source/`：HyperFrames 或其他渲染工程。
- `cover/`：封面源文件和导出图。
- `qa/`：抽帧、截图、检查报告。
- `final/`：最终 MP4。

## 推荐流程

```bash
python3 scripts/video_pipeline.py agent-pack {state['slug']} --agent {state['primary_agent']}
python3 scripts/video_pipeline.py scene-plan {state['slug']}
python3 scripts/video_pipeline.py scaffold-hyperframes {state['slug']}
python3 scripts/video_pipeline.py qa {state['slug']}
python3 scripts/video_pipeline.py package {state['slug']}
```
"""


def write_agent_pack(path: Path, state: dict[str, Any], agent: str) -> None:
    profiles = agents_config()["profiles"]
    if agent not in profiles:
        raise SystemExit(f"Unknown agent profile: {agent}. Available: {', '.join(profiles)}")

    # Always generate all common instructions so the project is portable across agents.
    write_text(path / "AGENTS.md", agent_instruction_doc(state, "codex"))
    write_text(path / "CLAUDE.md", agent_instruction_doc(state, "claude-code"))
    write_text(path / "AGENT_TASKS.md", agent_instruction_doc(state, "generic"))
    for profile_id in profiles:
        prompt_dir = path / profiles[profile_id]["prompt_dir"]
        write_text(prompt_dir / "01_research.md", research_prompt(state, profile_id))
        write_text(prompt_dir / "02_voiceover_review.md", voiceover_review_prompt(state, profile_id))
        write_text(prompt_dir / "03_scene_and_visuals.md", scene_visual_prompt(state, profile_id))
        write_text(prompt_dir / "04_qa.md", qa_prompt(state, profile_id))


def agent_instruction_doc(state: dict[str, Any], profile_id: str) -> str:
    label = {"codex": "Codex", "claude-code": "Claude Code", "generic": "Generic Agent"}[profile_id]
    material_type = state.get("material_type", "unknown")
    info = MATERIAL_TYPES.get(material_type, MATERIAL_TYPES["unknown"])
    return f"""\
# {label} 视频项目协作说明

项目：{state['title']}

选题钩子：{state.get('topic_hook') or '待补充'}

观众痛点：{state.get('audience_pain') or '待补充'}

素材类型：`{material_type}` / {info['label']}

立意：{state['thesis'] or '待确认'}

{PRINCIPLES}

## 协作约定

- 读取 `state.json` 判断当前门禁状态。
- 先确认 `process/00_topic_selection.md` 的选题判断；如果选题没有观众收益或传播钩子，先修正选题。
- 先确认 `process/00_material_type.md` 的素材类型判断；如果材料类型不对，先修正素材类型和默认结构。
- 只在对应门禁允许时修改对应文件。
- 口播稿完成多视角审阅并自确认前，不得生成正式配音、字幕和视频。
- 配图必须简洁，图内和前后图之间要有逻辑。
- 渲染和 QA 必须遵守成片规则：清理旧片段、只认 `segments.txt`、最终 MP4 抽帧、字幕两行以内、画面/字幕/音频同轴、无方格背景、无遮挡和裁切。
- 所有输出写入当前项目目录，不要散落到仓库根目录。
- 不复制 `node_modules`、渲染缓存或临时逐帧文件到交付包。

## 关键产物

- `process/01_research_brief.md`
- `process/02_voiceover_draft.md`
- `process/03_voiceover_confirmed.md`
- `process/04_scene_plan.json`
- `source/hyperframes/`
- `cover/`
- `qa/`
- `final/`
"""


def research_prompt(state: dict[str, Any], profile_id: str) -> str:
    material_type = state.get("material_type", "unknown")
    info = MATERIAL_TYPES.get(material_type, MATERIAL_TYPES["unknown"])
    return f"""\
# 研究任务（{profile_id}）

请完整阅读来源材料，更新 `process/01_research_brief.md`。

## 目标

- 先判断选题是否成立：观众痛点、传播钩子、来源强度、视觉潜力和合规边界是否足够。
- 先判断原始素材类型是不是 `{info['label']}`；如果不对，改写 `process/00_material_type.md` 并标明原因。
- 判断这条内容是否真的对观众有价值。
- 提炼 1 句话立意，并检查普通观众是否能转述。
- 提炼观众痛点、可执行建议和合规边界。
- 判断它的传播钩子属于纠偏、反差、行动建议还是痛点解决。
- 列出适合做成简洁配图的逻辑节点。

## 当前立意

{state['thesis'] or '待确认'}

## 当前选题

- 钩子：{state.get('topic_hook') or '待补充'}
- 为什么值得做：{state.get('topic_reason') or '待补充'}
- 观众痛点：{state.get('audience_pain') or '待补充'}

## 当前素材类型

- 类型：`{material_type}` / {info['label']}
- 默认结构：{info['default_structure']}
- 常见坑：{info['common_trap']}
"""


def voiceover_review_prompt(state: dict[str, Any], profile_id: str) -> str:
    material_type = state.get("material_type", "unknown")
    info = MATERIAL_TYPES.get(material_type, MATERIAL_TYPES["unknown"])
    return f"""\
# 口播审阅任务（{profile_id}）

请从观众视角审阅 `process/02_voiceover_draft.md`，输出修改建议。

必须检查：

- 口播是否承接选题钩子：{state.get('topic_hook') or '待补充'}。
- 口播是否回应观众痛点：{state.get('audience_pain') or '待补充'}。
- 口播结构是否符合素材类型：{info['default_structure']}。
- 普通观众是否听得懂。
- 目标受众是否觉得有价值。
- 观众能不能一句话转述这条视频。
- 开头 15 秒是否说清同一句主判断。
- 每个观点是否给了建议。
- 英文专有名词是否保留英文。
- 口播、字幕和画面标题是否会一致。
- 是否存在合规或版权风险。

项目标题：{state['title']}
"""


def scene_visual_prompt(state: dict[str, Any], profile_id: str) -> str:
    material_type = state.get("material_type", "unknown")
    info = MATERIAL_TYPES.get(material_type, MATERIAL_TYPES["unknown"])
    return f"""\
# 分镜与配图任务（{profile_id}）

请基于 `process/03_voiceover_confirmed.md` 和 `process/04_scene_plan.json` 设计画面。这里的 confirmed 表示“审阅通过”，不表示必须等待用户确认。

硬规则：

- 封面和第一幕要直接承接选题钩子：{state.get('topic_hook') or '待补充'}。
- 画面结构要符合素材类型：{info['label']} / {info['default_structure']}。
- 每屏只讲一个核心意思。
- 图内要有阅读顺序。
- 前后图沿同一主线递进。
- 3 秒扫视能看懂主题、主线和收益。
- 每张图和封面是否都服务同一句可传播立意。
- 不做抽象科技背景，不堆小字。
- 不使用方格、网格或噪声纹理背景，默认纯色或干净深色底。
- 图内文字、箭头、节点、卡片、结论条不能互相遮挡、贴边或裁切。
- 底部字幕安全区不能放核心信息。
- 箭头必须完整可见，不能只剩一条线。

输出建议写到 `process/04_scene_plan.md` 或更新结构化 JSON。
"""


def qa_prompt(state: dict[str, Any], profile_id: str) -> str:
    material_type = state.get("material_type", "unknown")
    info = MATERIAL_TYPES.get(material_type, MATERIAL_TYPES["unknown"])
    return f"""\
# QA 任务（{profile_id}）

请检查视频项目是否满足发布前门禁。

重点：

- 选题是否仍然成立：观众痛点、钩子、收益和来源边界是否清楚。
- 素材类型是否判断正确：`{material_type}` / {info['label']}。
- 视频结构是否符合该类型的默认结构：{info['default_structure']}。
- 标题、立意、口播、画面、封面是否一致。
- 标题、封面和开头是否围绕同一句可传播立意。
- 配图是否简洁、有图内逻辑和前后递进。
- 9:16 是否有黑边、重叠、贴边、裁切。
- 底部关键文字是否会被播放器遮挡。
- 是否清理旧片段，并确认 QA 只检查 `segments.txt` 中实际使用的片段。
- 最终 QA 是否来自最终 MP4 抽帧，而不是无字幕源图。
- 字幕是否最多两行，未裁切，且没有遮挡图内核心信息。
- 当前字幕是否解释当前画面，没有图先切、字幕还在讲上一页的问题。
- 背景是否干净纯色，没有方格、网格或噪声纹理。
- 英文专名是否保留空格，没有出现 `ClaudeCode`、`ContextEngineering` 一类粘连。
- 箭头、连线、流程方向是否完整可见。
- 英文名、多音字、字幕是否有明显问题。

把结果写入 `qa/qa-report.md`。
"""


def agent_pack_cmd(args: argparse.Namespace) -> None:
    path, state = load_project(args.project)
    write_agent_pack(path, state, args.agent)
    state["primary_agent"] = args.agent
    save_project(path, state)
    print(f"Wrote agent pack for {args.agent}: {path / 'agent-pack'}")


def extract_text_block(markdown: str) -> str:
    fence = re.search(r"```(?:text)?\n(.*?)```", markdown, flags=re.S)
    if fence:
        return fence.group(1).strip()
    lines = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped.startswith("- ["):
            continue
        if stripped:
            lines.append(stripped)
    return "\n".join(lines).strip()


def split_voiceover(text: str) -> list[str]:
    text = re.sub(r"\r\n?", "\n", text)
    raw_parts = [part.strip() for part in re.split(r"\n\s*\n+", text) if part.strip()]
    parts: list[str] = []
    for part in raw_parts:
        if len(part) <= 110:
            parts.append(part)
            continue
        sentences = re.split(r"(?<=[。！？!?])", part)
        chunk = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if len(chunk) + len(sentence) > 105 and chunk:
                parts.append(chunk.strip())
                chunk = sentence
            else:
                chunk += sentence
        if chunk.strip():
            parts.append(chunk.strip())
    return parts


def estimate_duration(text: str, min_seconds: float = 4.0) -> float:
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin_words = len(re.findall(r"[A-Za-z][A-Za-z0-9_-]*", text))
    punctuation = len(re.findall(r"[，。！？；：,.!?;:]", text))
    seconds = chinese_chars / 4.7 + latin_words * 0.45 + punctuation * 0.16
    return max(min_seconds, round(seconds, 3))


def short_title(text: str, fallback: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if cleaned.startswith(BRAND_OPENING):
        return "开场"
    if cleaned.startswith(BRAND_CLOSING):
        return "结束语"
    marks = ["。", "？", "！", "，", "；", ".", "?", "!", ",", ";", ":"]
    positions = [cleaned.find(mark) for mark in marks if cleaned.find(mark) > 0]
    if positions:
        cleaned = cleaned[: min(positions)]
    cleaned = re.sub(rf"^{re.escape(BRAND_OPENING)}", "开场", cleaned)
    if len(cleaned) > 22:
        cleaned = cleaned[:22]
    return cleaned or fallback


def visual_items(text: str) -> list[str]:
    tokens = re.split(r"[，。！？；：,.!?;:\n]+", text)
    items = []
    for token in tokens:
        token = token.strip()
        if 3 <= len(token) <= 18:
            items.append(token)
        if len(items) >= 4:
            break
    if not items:
        items = ["问题", "方法", "收益"]
    return items


def scene_plan_cmd(args: argparse.Namespace) -> None:
    path, state = load_project(args.project)
    voiceover_path = resolve_project_path(path, args.voiceover or "process/03_voiceover_confirmed.md")
    if not voiceover_path.exists():
        raise SystemExit(f"Voiceover file not found: {voiceover_path}")
    voiceover = extract_text_block(voiceover_path.read_text(encoding="utf-8"))
    if BRAND_OPENING not in voiceover:
        raise SystemExit(f"Approved voiceover must include fixed opening: {BRAND_OPENING}")
    if BRAND_CLOSING not in voiceover:
        raise SystemExit(f"Approved voiceover must include fixed closing: {BRAND_CLOSING}")

    parts = split_voiceover(voiceover)
    total_estimated = sum(estimate_duration(part) for part in parts)
    target = float(args.duration or state.get("duration_target") or total_estimated)
    scale = target / total_estimated if total_estimated else 1.0
    start = 0.0
    scenes = []
    for index, part in enumerate(parts, 1):
        duration = round(estimate_duration(part) * scale, 3)
        end = round(start + duration, 3)
        kicker = "开场" if index == 1 else ("结尾" if index == len(parts) else f"第 {index - 1} 点")
        scene = {
            "id": f"s{index:02d}",
            "start": round(start, 3),
            "end": end,
            "duration": duration,
            "kicker": kicker,
            "title": short_title(part, kicker),
            "subtitle": part if len(part) <= 42 else part[:42] + "…",
            "voiceover": part,
            "visual_type": "logic-card",
            "visual_goal": "用一张简洁图解释本段核心意思。",
            "visual_items": visual_items(part),
            "qa": {
                "one_core_idea": True,
                "has_reading_order": True,
                "audience_can_scan_in_3s": False,
            },
        }
        scenes.append(scene)
        start = end

    data = {
        "schema_version": 1,
        "title": state["title"],
        "thesis": state.get("thesis", ""),
        "duration": round(start, 3),
        "format": state.get("format", "9:16"),
        "source_url": state.get("source_url", ""),
        "scenes": scenes,
        "rules": {
            "visual_first_priority": "观众能看懂",
            "visual_style": "简洁信息图",
            "visual_logic": "图内有顺序，前后有递进",
        },
    }
    write_json(path / "process" / "04_scene_plan.json", data)
    write_text(path / "process" / "04_scene_plan.md", scene_plan_markdown(data))
    state["gates"]["voiceover_self_approved"] = "approved"
    state["gates"]["scene_plan"] = "draft_ready"
    state["artifacts"]["scene_plan"] = "process/04_scene_plan.json"
    save_project(path, state)
    print(f"Wrote scene plan: {path / 'process/04_scene_plan.json'}")


def scene_plan_markdown(data: dict[str, Any]) -> str:
    lines = [
        f"# 04 分镜计划：{data['title']}",
        "",
        f"- 立意：{data.get('thesis', '')}",
        f"- 时长：{data['duration']} 秒",
        f"- 配图原则：{data['rules']['visual_first_priority']}；{data['rules']['visual_logic']}",
        "",
        "| 时间 | 标题 | 画面目标 | 口播 |",
        "| --- | --- | --- | --- |",
    ]
    for scene in data["scenes"]:
        lines.append(
            f"| {scene['start']:.1f}-{scene['end']:.1f}s | {scene['title']} | {scene['visual_goal']} | {scene['voiceover']} |"
        )
    return "\n".join(lines)


def resolve_project_path(project: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return project / path


def scaffold_hyperframes_cmd(args: argparse.Namespace) -> None:
    path, state = load_project(args.project)
    scene_plan_path = resolve_project_path(path, args.scene_plan or "process/04_scene_plan.json")
    if not scene_plan_path.exists():
        raise SystemExit(f"Scene plan not found: {scene_plan_path}. Run scene-plan first.")
    scene_plan = read_json(scene_plan_path, {})
    hf_dir = path / "source" / "hyperframes"
    (hf_dir / "data").mkdir(parents=True, exist_ok=True)
    write_text(hf_dir / "package.json", hyperframes_package_json(path.name))
    write_text(hf_dir / "hyperframes.json", hyperframes_config())
    write_text(hf_dir / "data" / "scenes.js", "window.VIDEO_PIPELINE_DATA = " + json.dumps(scene_plan, ensure_ascii=False, indent=2) + ";\n")
    write_text(hf_dir / "index.html", generic_hyperframes_html())
    state["gates"]["visual_logic"] = "draft_ready"
    state["artifacts"]["hyperframes"] = "source/hyperframes"
    save_project(path, state)
    print(f"Scaffolded HyperFrames project: {hf_dir}")
    print(f"Preview with: cd {hf_dir} && npm run preview")


def hyperframes_package_json(name: str) -> str:
    return json.dumps(
        {
            "name": f"video-pipeline-{slugify(name)}",
            "private": True,
            "type": "module",
            "scripts": {
                "check": "npx --yes hyperframes@0.6.111 lint && npx --yes hyperframes@0.6.111 validate && npx --yes hyperframes@0.6.111 inspect",
                "render": "npx --yes hyperframes@0.6.111 render",
                "preview": "npx --yes hyperframes@0.6.111 preview",
            },
            "dependencies": {"gsap": "^3.15.0"},
        },
        ensure_ascii=False,
        indent=2,
    )


def hyperframes_config() -> str:
    return json.dumps(
        {
            "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
            "registry": "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry",
            "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"},
        },
        indent=2,
    )


def generic_hyperframes_html() -> str:
    return """\
<!doctype html>
<html lang="zh-CN" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="./node_modules/gsap/dist/gsap.min.js"></script>
    <script src="./data/scenes.js"></script>
    <style>
      * { box-sizing: border-box; }
      html, body { margin: 0; width: 1080px; height: 1920px; overflow: hidden; background: #f7fbff; }
      body { font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", Arial, sans-serif; color: #111827; letter-spacing: 0; }
      #root { position: relative; width: 1080px; height: 1920px; overflow: hidden; background: linear-gradient(135deg, #f8fbff, #f1faf7 60%, #fff9ec); }
      .safe { position: absolute; inset: 70px 70px 92px; }
      .topbar, .footer { position: absolute; left: 0; right: 0; display: flex; justify-content: space-between; align-items: center; color: #526174; font-weight: 850; }
      .topbar { top: 0; font-size: 24px; }
      .footer { bottom: 0; font-size: 22px; }
      .mark { display: inline-grid; place-items: center; width: 48px; height: 48px; margin-right: 14px; border-radius: 13px; background: #f9ab00; color: #111827; font-weight: 950; }
      .progress-track { position: absolute; left: 0; right: 0; bottom: -24px; height: 10px; background: rgba(15, 118, 110, .12); border-radius: 99px; overflow: hidden; }
      .progress { height: 100%; width: 0; background: linear-gradient(90deg, #25a898, #f9ab00); }
      .scene { position: absolute; inset: 0; visibility: hidden; opacity: 0; }
      .head { position: absolute; top: 96px; left: 0; right: 0; display: grid; gap: 18px; }
      .kicker { width: fit-content; padding: 8px 18px; border-radius: 999px; background: #e7f8f4; border: 2px solid #8dd7cc; color: #0f766e; font-size: 24px; font-weight: 950; }
      h1 { margin: 0; max-width: 910px; font-size: 68px; line-height: 1.08; font-weight: 950; }
      .subtitle { max-width: 900px; font-size: 31px; line-height: 1.35; font-weight: 800; color: #526174; }
      .board { position: absolute; top: 438px; left: 0; right: 0; min-height: 780px; padding: 54px; border: 3px solid #d0dedc; border-radius: 38px; background: rgba(255, 255, 255, .94); box-shadow: 0 18px 34px rgba(18, 48, 71, .12); }
      .flow { display: grid; grid-template-columns: repeat(3, 1fr); gap: 28px; margin-top: 28px; }
      .card { min-height: 238px; padding: 32px 28px; border-radius: 28px; border: 4px solid #25a898; background: #eefcf8; display: grid; align-content: start; gap: 18px; }
      .card:nth-child(2) { border-color: #f9ab00; background: #fff8ea; }
      .card:nth-child(3) { border-color: #4285f4; background: #f1f6ff; }
      .num { width: 42px; height: 42px; display: grid; place-items: center; border-radius: 50%; background: #111827; color: white; font-size: 22px; font-weight: 950; }
      .card b { font-size: 31px; line-height: 1.18; }
      .card span { font-size: 24px; line-height: 1.32; color: #526174; font-weight: 760; }
      .takeaway { position: absolute; left: 54px; right: 54px; bottom: 54px; padding: 25px 32px; border-radius: 24px; background: #102a43; color: white; font-size: 30px; line-height: 1.32; font-weight: 900; }
      .caption { position: absolute; left: 96px; right: 96px; bottom: 210px; min-height: 96px; display: grid; place-items: center; padding: 24px 34px; border-radius: 28px; background: rgba(17, 24, 39, .86); color: white; font-size: 34px; line-height: 1.26; font-weight: 850; text-align: center; visibility: hidden; opacity: 0; }
    </style>
  </head>
  <body>
    <div id="root">
      <div class="safe">
        <div class="topbar"><div><span class="mark">AI</span>工程观察</div><div id="source"></div></div>
        <div id="scenes"></div>
        <div id="captions"></div>
        <div class="footer"><div id="footer-title"></div><div>Video Pipeline</div></div>
        <div class="progress-track"><div class="progress"></div></div>
      </div>
    </div>
    <script>
      const data = window.VIDEO_PIPELINE_DATA;
      const scenesEl = document.querySelector("#scenes");
      const captionsEl = document.querySelector("#captions");
      document.querySelector("#source").textContent = data.source_url ? "SOURCE" : "DRAFT";
      document.querySelector("#footer-title").textContent = data.title;
      const esc = (s) => String(s || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
      const short = (s, n) => String(s || "").length > n ? String(s || "").slice(0, n) + "…" : String(s || "");
      data.scenes.forEach((scene, index) => {
        const items = (scene.visual_items || ["问题", "方法", "收益"]).slice(0, 3);
        const node = document.createElement("section");
        node.className = "scene clip";
        node.id = `scene-${index}`;
        node.dataset.start = String(scene.start);
        node.dataset.duration = String(scene.end - scene.start);
        node.dataset.trackIndex = "1";
        node.innerHTML = `
          <div class="head">
            <div class="kicker">${esc(scene.kicker)}</div>
            <h1>${esc(scene.title)}</h1>
            <div class="subtitle">${esc(scene.subtitle)}</div>
          </div>
          <div class="board">
            <div class="flow">
              ${items.map((item, i) => `<div class="card"><div class="num">${i + 1}</div><b>${esc(item)}</b><span>${esc(i === 0 ? "先看清问题" : i === 1 ? "再找到方法" : "最后落到收益")}</span></div>`).join("")}
            </div>
            <div class="takeaway">带走：${esc(short(scene.visual_goal || scene.title, 34))}</div>
          </div>`;
        scenesEl.appendChild(node);
        const cap = document.createElement("div");
        cap.className = "caption clip";
        cap.id = `caption-${index}`;
        cap.dataset.start = String(scene.start);
        cap.dataset.duration = String(scene.end - scene.start);
        cap.dataset.trackIndex = "8";
        cap.textContent = short(scene.voiceover, 38);
        captionsEl.appendChild(cap);
      });
      window.__timelines = window.__timelines || {};
      const tl = gsap.timeline({ paused: true });
      data.scenes.forEach((scene, index) => {
        const sel = `#scene-${index}`;
        tl.set(sel, { autoAlpha: 1 }, scene.start);
        tl.fromTo(sel, { y: 34, scale: .988 }, { y: 0, scale: 1, duration: .6, ease: "power3.out", overwrite: "auto" }, scene.start);
        tl.fromTo(`${sel} h1`, { y: 26, opacity: 0 }, { y: 0, opacity: 1, duration: .46, ease: "power3.out", overwrite: "auto" }, scene.start + .12);
        tl.fromTo(`${sel} .card`, { y: 24, opacity: 0 }, { y: 0, opacity: 1, duration: .42, stagger: .08, ease: "power2.out", overwrite: "auto" }, scene.start + .28);
        tl.to(sel, { autoAlpha: 0, y: -18, duration: .32, overwrite: "auto" }, Math.max(scene.start, scene.end - .32));
        const cap = `#caption-${index}`;
        tl.set(cap, { autoAlpha: 1 }, scene.start);
        tl.to(cap, { autoAlpha: 0, duration: .1, overwrite: "auto" }, Math.max(scene.start, scene.end - .1));
      });
      tl.to(".progress", { width: "100%", duration: data.duration, ease: "none" }, 0);
      window.__timelines.main = tl;
    </script>
  </body>
</html>
"""


def gate_cmd(args: argparse.Namespace) -> None:
    path, state = load_project(args.project)
    if args.name not in GATES:
        raise SystemExit(f"Unknown gate: {args.name}. Available: {', '.join(GATES)}")
    state["gates"][args.name] = args.status
    note = args.note or f"{args.name} -> {args.status}"
    state.setdefault("notes", []).append({"at": now_iso(), "note": note})
    save_project(path, state)
    print(f"Updated gate: {args.name}={args.status}")


def status_cmd(args: argparse.Namespace) -> None:
    if args.project:
        path, state = load_project(args.project)
        print_project_status(path, state)
        return
    ensure_base_dirs()
    print("Video pipeline status")
    projects = sorted(PROJECTS.glob("*"))
    print(f"- Projects: {len(projects)}")
    for path in projects:
        state = read_json(path / "state.json", {})
        if not state:
            continue
        gates = state.get("gates", {})
        done = sum(1 for value in gates.values() if value in {"approved", "passed", "packaged"})
        print(f"  - {path.name}: {state.get('title')} ({done}/{len(GATES)} gates done)")


def print_project_status(path: Path, state: dict[str, Any]) -> None:
    print(f"Project: {path}")
    print(f"- Title: {state.get('title')}")
    print(f"- Topic Hook: {state.get('topic_hook', '')}")
    print(f"- Audience Pain: {state.get('audience_pain', '')}")
    print(f"- Material Type: {state.get('material_type', 'unknown')}")
    print(f"- Thesis: {state.get('thesis')}")
    print(f"- Agent: {state.get('primary_agent')}")
    print("- Gates:")
    for gate in GATES:
        print(f"  - {gate}: {state.get('gates', {}).get(gate, 'missing')}")
    if state.get("artifacts"):
        print("- Artifacts:")
        for key, value in state["artifacts"].items():
            print(f"  - {key}: {value}")


def qa_cmd(args: argparse.Namespace) -> None:
    path, state = load_project(args.project)
    issues: list[str] = []
    warnings: list[str] = []
    gates = state.get("gates", {})
    material_type = state.get("material_type", "unknown")

    if not state.get("topic_hook") or not state.get("audience_pain"):
        message = "选题钩子或观众痛点尚未确认，需先完成 topic_selection 门禁。"
        if args.final:
            issues.append(message)
        else:
            warnings.append(message)

    if material_type not in MATERIAL_TYPES or material_type == "unknown":
        message = "素材类型尚未确认，需先完成 material_type 门禁。"
        if args.final:
            issues.append(message)
        else:
            warnings.append(message)

    voiceover_path = path / "process" / "03_voiceover_confirmed.md"
    if voiceover_path.exists():
        voiceover = extract_text_block(voiceover_path.read_text(encoding="utf-8"))
        if BRAND_OPENING not in voiceover:
            issues.append("审阅通过口播缺少固定开场。")
        if BRAND_CLOSING not in voiceover:
            issues.append("审阅通过口播缺少固定结束语。")
    else:
        issues.append("缺少 process/03_voiceover_confirmed.md。")

    scene_path = path / "process" / "04_scene_plan.json"
    if scene_path.exists():
        plan = read_json(scene_path, {})
        for scene in plan.get("scenes", []):
            if len(scene.get("visual_items", [])) > 4:
                warnings.append(f"{scene.get('id')} 配图元素超过 4 个，可能过复杂。")
            if not scene.get("qa", {}).get("has_reading_order"):
                issues.append(f"{scene.get('id')} 缺少图内阅读顺序。")
        if plan.get("duration", 0) <= 0:
            issues.append("分镜时长无效。")
    else:
        warnings.append("尚未生成 process/04_scene_plan.json。")

    if args.final:
        if gates.get("topic_selection") not in {"approved", "passed"}:
            issues.append("最终 QA 前必须完成 topic_selection 选题门禁。")
        if gates.get("material_type") not in {"approved", "passed"}:
            issues.append("最终 QA 前必须完成 material_type 素材类型门禁。")
        if gates.get("visual_logic") not in {"approved", "passed"}:
            issues.append("最终 QA 前必须完成 visual_logic 门禁。")
        if gates.get("cover_hook") not in {"approved", "passed"}:
            issues.append("最终 QA 前必须完成 cover_hook 封面钩子门禁。")
        if gates.get("logic_visual_alignment") not in {"approved", "passed"}:
            issues.append("最终 QA 前必须完成 logic_visual_alignment 图文一致性门禁。")
        if gates.get("pronunciation") not in {"approved", "passed"}:
            issues.append("最终 QA 前必须完成 pronunciation 发音门禁。")
        contact_sheets = list((path / "qa").glob("**/*contact-sheet*.jpg")) + list((path / "qa").glob("**/*contact-sheet*.png"))
        if not contact_sheets:
            issues.append("最终 QA 缺少抽帧联系表，需生成 qa/**/*contact-sheet*.jpg 或 png。")
        final_frame_sheets = [
            path / "qa" / "contact-sheet-final-all-frames.jpg",
            path / "qa" / "contact-sheet-final-all-frames.png",
        ]
        if not any(sheet.exists() for sheet in final_frame_sheets):
            issues.append("最终 QA 缺少最终 MP4 逐场景抽帧 contact-sheet-final-all-frames，不能只检查源图或旧片段。")
        segment_sheet_dir = path / "qa" / "segment_contact_sheets"
        if not segment_sheet_dir.exists() or not list(segment_sheet_dir.glob("*")):
            issues.append("最终 QA 缺少 qa/segment_contact_sheets；需按 segments.txt 检查实际参与拼接的片段。")
        visual_review_files = [
            path / "qa" / "visual-review.md",
            path / "qa" / "recheck" / "recheck-notes.md",
        ]
        if not any(review.exists() for review in visual_review_files):
            issues.append("最终 QA 缺少人工视觉复检记录，需补 qa/visual-review.md 或 qa/recheck/recheck-notes.md。")

    hf_dir = path / "source" / "hyperframes"
    if not (hf_dir / "index.html").exists():
        warnings.append("尚未生成 HyperFrames 工程。")
    has_video = bool(list((path / "final").glob("*.mp4")))
    has_cover = bool(list((path / "cover").glob("*.png")))
    if has_video:
        state["gates"]["video_render"] = "passed"
    elif args.final:
        issues.append("最终 QA 缺少 final/*.mp4。")
    else:
        warnings.append("尚未生成最终 MP4；当前只做规划阶段 QA。")
    if has_cover:
        state["gates"]["cover"] = "passed"
    elif args.final:
        issues.append("最终 QA 缺少 cover/*.png。")
    else:
        warnings.append("尚未生成封面 PNG；当前只做规划阶段 QA。")

    report = qa_report(path, state, issues, warnings)
    write_text(path / "qa" / "qa-report.md", report)
    state["gates"]["qa"] = ("passed" if args.final else "planning_passed") if not issues else "blocked"
    state["artifacts"]["qa_report"] = "qa/qa-report.md"
    save_project(path, state)
    print(f"Wrote QA report: {path / 'qa/qa-report.md'}")
    if issues:
        raise SystemExit("QA blocked:\n- " + "\n- ".join(issues))


def qa_report(path: Path, state: dict[str, Any], issues: list[str], warnings: list[str]) -> str:
    return f"""\
# QA Report

- Project: `{path.name}`
- Title: {state.get('title')}
- Generated: {now_iso()}
- Status: {'BLOCKED' if issues else 'PASS'}

## Blocking Issues

{bullet_list(issues) if issues else '- None'}

## Warnings

{bullet_list(warnings) if warnings else '- None'}

## Visual Logic Checklist

这些是人工审阅项。最终 QA 必须同时保留抽帧联系表和 `qa/visual-review.md` 或 `qa/recheck/recheck-notes.md`，不能只依赖媒体参数。

- [ ] 配图足够简洁，3 秒内能看出主题、主线和观众收益。
- [ ] 每张图内部有明确阅读顺序、因果、对比或流程关系。
- [ ] 前后图片沿同一条内容主线推进，没有各讲各的。
- [ ] 每次重渲前已清理旧 `source/segments`，避免旧片段混入。
- [ ] 封面标题、流程节点、底部标签、角标没有互相覆盖、贴边或裁切。
- [ ] 视频无黑边，字幕和主体内容不重叠。
- [ ] QA 抽帧来自最终 MP4，不只看无字幕源图。
- [ ] 已生成 `qa/contact-sheet-final-all-frames.jpg` 或 png。
- [ ] `qa/segment_contact_sheets/` 只包含 `segments.txt` 中实际拼进成片的片段。
- [ ] 字幕最多两行，没有被裁切，也没有压住底部安全区。
- [ ] 字幕、音频和当前画面语义一致，没有图先切、字幕还在讲上一页的问题。
- [ ] 背景为纯色或干净底色，没有方格、网格、噪声纹理。
- [ ] 英文专名没有被字幕切分粘连，例如 `ClaudeCode`、`ContextEngineering`。
- [ ] 箭头、连线、流程方向完整可见；不能只剩一条线或箭头头部被卡片遮住。
"""


def bullet_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def render_cmd(args: argparse.Namespace) -> None:
    path, state = load_project(args.project)
    hf_dir = path / "source" / "hyperframes"
    if not (hf_dir / "package.json").exists():
        raise SystemExit(f"HyperFrames project not found: {hf_dir}. Run scaffold-hyperframes first.")
    cmd = ["npm", "run", "check" if args.check_only else "render"]
    print(f"Running in {hf_dir}: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=hf_dir, check=True)
    state["gates"]["video_render"] = "passed" if not args.check_only else "checked"
    save_project(path, state)


def package_cmd(args: argparse.Namespace) -> None:
    path, state = load_project(args.project)
    if not args.allow_incomplete:
        if not list((path / "final").glob("*.mp4")):
            raise SystemExit("Package blocked: missing final/*.mp4. Use --allow-incomplete for a draft package.")
        if not list((path / "cover").glob("*.png")):
            raise SystemExit("Package blocked: missing cover/*.png. Use --allow-incomplete for a draft package.")
    deliverable = ROOT / "deliverables" / (args.slug or path.name)
    if deliverable.exists() and args.force:
        shutil.rmtree(deliverable)
    for folder in ["final", "cover", "qa", "process", "source"]:
        (deliverable / folder).mkdir(parents=True, exist_ok=True)

    copy_tree_contents(path / "final", deliverable / "final")
    copy_tree_contents(path / "cover", deliverable / "cover")
    copy_tree_contents(path / "qa", deliverable / "qa")
    copy_tree_contents(path / "process", deliverable / "process")
    copy_source(path / "source", deliverable / "source")
    write_json(deliverable / "pipeline-state.json", state)
    write_text(deliverable / "README.md", deliverable_readme(state))
    state["gates"]["package"] = "draft_packaged" if args.allow_incomplete else "packaged"
    state["artifacts"]["deliverable"] = str(deliverable.relative_to(ROOT))
    save_project(path, state)
    print(f"Packaged deliverable: {deliverable}")


def copy_tree_contents(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    for item in src.iterdir():
        if item.name in {"node_modules", ".DS_Store"}:
            continue
        target = dst / item.name
        if item.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(item, target, ignore=shutil.ignore_patterns("node_modules", ".DS_Store", "renders", ".cache"))
        else:
            shutil.copy2(item, target)


def copy_source(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("node_modules", ".DS_Store", "renders", ".cache"))


def deliverable_readme(state: dict[str, Any]) -> str:
    return f"""\
# {state.get('title')}

## 立意

{state.get('thesis') or '待补充'}

## 产物

- `final/`：最终视频。
- `cover/`：封面图。
- `qa/`：QA 报告和抽帧。
- `process/`：口播、分镜和制作过程文件。
- `source/`：可再生成的视频源工程。

## 流水线状态

```json
{json.dumps(state.get('gates', {}), ensure_ascii=False, indent=2)}
```
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Video generation pipeline MVP")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="Create video-pipeline config and folders")
    p.set_defaults(func=init_cmd)

    p = sub.add_parser("create", help="Create a standard video project")
    p.add_argument("--slug")
    p.add_argument("--title", required=True)
    p.add_argument("--topic-hook", default="")
    p.add_argument("--topic-reason", default="")
    p.add_argument("--audience-pain", default="")
    p.add_argument("--material-type", choices=list(MATERIAL_TYPES.keys()), default="unknown")
    p.add_argument("--thesis", default="")
    p.add_argument("--viewer-value", default="")
    p.add_argument("--source-url", default="")
    p.add_argument("--source-file", default="")
    p.add_argument("--duration", type=int, default=180)
    p.add_argument("--language", default="zh-CN")
    p.add_argument("--format", default="9:16")
    p.add_argument("--agent", choices=["codex", "claude-code", "generic"], default="codex")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=create_cmd)

    p = sub.add_parser("agent-pack", help="Generate agent-specific task packs")
    p.add_argument("project")
    p.add_argument("--agent", choices=["codex", "claude-code", "generic"], default="codex")
    p.set_defaults(func=agent_pack_cmd)

    p = sub.add_parser("scene-plan", help="Create scene plan from approved voiceover")
    p.add_argument("project")
    p.add_argument("--voiceover", default="process/03_voiceover_confirmed.md")
    p.add_argument("--duration", type=float)
    p.set_defaults(func=scene_plan_cmd)

    p = sub.add_parser("scaffold-hyperframes", help="Create a generic HyperFrames project from scene plan")
    p.add_argument("project")
    p.add_argument("--scene-plan", default="process/04_scene_plan.json")
    p.set_defaults(func=scaffold_hyperframes_cmd)

    p = sub.add_parser("render", help="Run HyperFrames check or render")
    p.add_argument("project")
    p.add_argument("--check-only", action="store_true")
    p.set_defaults(func=render_cmd)

    p = sub.add_parser("gate", help="Set a project gate status")
    p.add_argument("project")
    p.add_argument("name", choices=GATES)
    p.add_argument("status")
    p.add_argument("--note", default="")
    p.set_defaults(func=gate_cmd)

    p = sub.add_parser("qa", help="Run pipeline QA")
    p.add_argument("project")
    p.add_argument("--final", action="store_true", help="Require final video and cover assets")
    p.set_defaults(func=qa_cmd)

    p = sub.add_parser("package", help="Package a video project into deliverables")
    p.add_argument("project")
    p.add_argument("--slug")
    p.add_argument("--force", action="store_true")
    p.add_argument("--allow-incomplete", action="store_true", help="Create a draft package without final video/cover")
    p.set_defaults(func=package_cmd)

    p = sub.add_parser("status", help="Show video pipeline status")
    p.add_argument("project", nargs="?")
    p.set_defaults(func=status_cmd)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

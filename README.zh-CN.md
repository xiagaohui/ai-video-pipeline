# AI Video Pipeline

[English](README.md)

AI Video Pipeline 是一套文件驱动的短视频生产流水线，用来把文章、博客、官方文档、产品更新、访谈或开源项目，转成有立意、有脚本、有配图、有 QA、有发布素材的知识类短视频。

它不是“一句话生成视频”的玩具流程，而是把视频生产拆成一组可检查、可交接、可复用的节点。Codex、Claude Code 或其他 coding agent 都可以通过同一套文件继续工作。

## 解决什么问题

很多 AI 视频流程会直接从“给一个链接”跳到“生成一个视频”。这样很容易出现三个问题：

- 选题对观众没有价值。
- 口播只是复述原文，没有给出观点、方法或建议。
- 配图看起来很专业，但普通观众看不懂逻辑。

这套流水线在生成视频前加了门禁：

```text
原始材料
-> 选题判断
-> 材料类型判断
-> 立意和观众收益
-> 研究简报
-> 口播初稿
-> 观众视角审稿
-> 确认口播稿
-> 发音检查
-> 分镜计划
-> 视觉逻辑
-> 封面钩子
-> 渲染
-> 抽帧 QA
-> 发布包
```

## 核心原则

- **观众优先**：每个视频必须回答“观众看完能得到什么”。
- **材料类型优先**：产品新功能、观点文章、科普解释、工程实践、案例分析、官方文档和开源工具，不能用同一种脚本结构。
- **配图必须可读**：每张图本身要能讲清楚一个意思，不能靠字幕硬解释。
- **Agent 可交接**：Codex、Claude Code 或其他 agent 都通过 `state.json`、`process/*.md`、`agent-pack/*` 协作。
- **全过程有门禁**：选题、口播、配图、发音、封面、成片 QA 都有检查点。

## 沉淀下来的硬性 QA 规则

这些规则来自真实多集视频制作和反复修复：

- 最终 QA 必须检查渲染后的 MP4 抽帧，不能只看无字幕源图。
- 重新渲染前必须清理旧片段，抽帧必须严格跟随 `segments.txt`。
- 字幕最多两行，不能遮挡关键卡片、箭头、流程节点和结论条。
- 画面切换必须跟最终音频/VTT 时间轴一致，不能按分镜估算硬切。
- 默认使用干净纯色背景，不用方格、网格、噪声纹理堆“技术感”。
- 封面、正式标题、短标题、简介、平台封面导出必须保持一致。

## 快速开始

```bash
python3 scripts/video_pipeline.py init

python3 scripts/video_pipeline.py create \
  --slug claude-tag-ai-employee \
  --title "Claude Tag core idea: AI moves from personal assistant to org employee" \
  --topic-hook "AI moves from personal assistant to organization employee" \
  --topic-reason "Claude Tag shows a new way for AI to enter team workflows" \
  --audience-pain "People see only a tagging feature and miss the organizational design shift" \
  --material-type product_feature \
  --thesis "Claude Tag represents AI moving from personal assistant to organization employee" \
  --viewer-value "Viewers learn the six questions to ask before adding AI to team workflows" \
  --source-url "https://example.com/source" \
  --agent codex \
  --duration 180
```

生成 agent 任务包：

```bash
python3 scripts/video_pipeline.py agent-pack claude-tag-ai-employee --agent codex
python3 scripts/video_pipeline.py agent-pack claude-tag-ai-employee --agent claude-code
```

查看项目状态：

```bash
python3 scripts/video_pipeline.py status claude-tag-ai-employee
```

确认口播稿之后，生成分镜计划：

```bash
python3 scripts/video_pipeline.py scene-plan claude-tag-ai-employee --duration 180
```

生成一个简单的 HyperFrames 风格视觉工程：

```bash
python3 scripts/video_pipeline.py scaffold-hyperframes claude-tag-ai-employee
```

运行 QA：

```bash
python3 scripts/video_pipeline.py qa claude-tag-ai-employee
python3 scripts/video_pipeline.py qa claude-tag-ai-employee --final
```

打包交付物：

```bash
python3 scripts/video_pipeline.py package claude-tag-ai-employee --slug claude-tag-ai-employee
```

更多示例见 [examples/README.md](examples/README.md)。

## 材料类型

使用 `--material-type` 选择初始结构：

| 类型 | 适合材料 | 默认结构 |
| --- | --- | --- |
| `opinion` | 观点文章、访谈 | 观点 -> 对观众意味着什么 -> 建议 |
| `explainer` | 概念科普 | 误区 -> 大白话解释 -> 例子 -> 边界 |
| `product_feature` | 产品新功能 | 功能表层 -> 工作方式变化 -> 谁能用 -> 怎么用 -> 边界 |
| `engineering_practice` | 工程实践博客 | 问题 -> 方法 -> 步骤 -> 风险清单 |
| `case_study` | 案例分析 | 发生了什么 -> 为什么有效 -> 观众能复用什么 |
| `open_source_tool` | 开源工具和代码仓库 | 解决什么问题 -> 怎么用 -> 适合谁 -> 坑点 |
| `official_doc` | 官方文档 | 发生了什么变化 -> 场景 -> 使用建议 -> 边界 |
| `hot_concept` | 热点概念 | 误区 -> 真正关键点 -> 如何落地 |

## 项目结构

```text
video-pipeline/projects/<slug>/
  state.json
  README.md
  AGENTS.md
  CLAUDE.md
  AGENT_TASKS.md
  process/
    00_topic_selection.md
    00_material_type.md
    00_intent.md
    01_research_brief.md
    02_voiceover_draft.md
    03_voiceover_confirmed.md
    04_pronunciation_notes.md
    04_scene_plan.json
    04_scene_plan.md
    05_visual_rules.md
  agent-pack/
    codex/
    claude-code/
    generic/
  source/
  cover/
  qa/
  final/
  publish/
```

## Agent 支持

流水线会为不同 agent 生成任务包：

- Codex：`AGENTS.md` 和 `agent-pack/codex/`
- Claude Code：`CLAUDE.md` 和 `agent-pack/claude-code/`
- 通用 agent：`AGENT_TASKS.md` 和 `agent-pack/generic/`

协作约定很简单：读取 `state.json`，处理当前 gate，把产物写回项目文件夹，不跳过 QA。

## 自定义开头和结尾

默认开头和结尾可以通过环境变量覆盖，不需要改代码：

```bash
export AI_VIDEO_PIPELINE_OPENING="大家好，欢迎来到今天的 AI 工程笔记。"
export AI_VIDEO_PIPELINE_CLOSING="以上就是今天的内容，我们下期见。"
```

详见 [docs/customization.md](docs/customization.md)。

## 发音规则

生成 TTS 之前，流水线会要求先做发音检查：英文人名、产品名、缩写、多音字都要提前处理。

如果使用免费 TTS，不要只依赖拼音备注。对于容易读错、又不是必须保留原词的中文多音字，优先改写成无歧义表达。比如 `反直觉` 的 `觉` 如果被读成 `jiao`，口播里可以改成 `出乎意料`。

## 文档

- [流水线指南](docs/video-generation-pipeline.md)
- [品牌与发布规则](docs/video-branding.md)
- [最终 QA 清单](docs/final-qa-checklist.md)
- [制作经验沉淀](docs/video-production-learnings.md)
- [自定义说明](docs/customization.md)
- [开源发布检查清单](docs/open-source-checklist.md)
- [贡献指南](CONTRIBUTING.md)
- [安全说明](SECURITY.md)

## 不包含什么

这个仓库故意不包含：

- 已生成视频
- 个人草稿或私有发布历史
- 平台账号凭证
- 付费 TTS key
- 下载过的原始视频
- 微信视频号、抖音、小红书或其他平台的登录状态

## 许可证

Apache License 2.0。见 [LICENSE](LICENSE)。

## 当前状态

早期本地 MVP。CLI 目前保持轻量，只依赖 Python 标准库。

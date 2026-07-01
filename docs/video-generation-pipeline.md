# 视频生成流水线 V1

这套流水线负责“选题到发布”的视频生产。信息雷达负责发现候选素材，视频流水线负责把候选素材推进到：选题判断、素材类型判断、立意、口播、分镜、画面工程、QA、封面、发布包。

## 设计目标

1. **可控**：关键节点必须门禁自确认，尤其是口播、配图、封面和最终 QA；默认由主 agent 自审、自改、自推进。
2. **可复用**：每条视频都有统一目录结构，方便后续重剪、复盘和发布。
3. **可适配多 Agent**：Codex、Claude Code 或其他 Agent 都读取同一套 `state.json`、`process/` 和 `agent-pack/`。
4. **可开源**：核心脚本只依赖 Python 标准库；渲染层用项目内生成的 HyperFrames 工程，可替换成其他渲染器。

## 核心原则

视频流水线默认执行三条最高优先级原则：

1. 立意必须从观众视角出发，真的有价值，并且便于传播。
2. 表达必须让观众看得懂、听得懂。
3. 配图必须简洁，并且图内、前后图片之间都有清楚逻辑。

第一条还包含传播门槛：好立意不是作者脑子里的主题句，而是观众愿意帮你转述的一句话。它必须能自然变成标题、封面和开头钩子。

第三条是新增硬规则：让观众能够看懂永远是第一优先级。配图不是信息堆叠容器，而是理解路径。

## 封面与图文一致性硬规则

封面、立意、逻辑线和配图必须服务同一个主判断。任何一项对不上，都不能进入最终渲染。

封面必须先通过“一眼看懂测试”：

- 普通观众 1 秒内能看懂这条视频要解决什么问题。
- 大字必须是人话问题、反差判断或直接收益，不要只是材料标题或抽象概念。
- 封面要有钩子：纠偏、反差、痛点、方法或结果，至少命中一种。
- 封面小字只能补充来源或收益，不能让用户靠小字才明白主题。
- 封面里的每个元素都要能解释：为什么它会让用户更想点开。

逻辑线必须通过“逐幕转述测试”：

- 抽帧接触表不听音频也能看出主线推进。
- 每一幕只服务一个论点：误区、原因、判断标准、操作方法、结论不能混在一张图里。
- 画面标题要和这一幕口播作用一致，不能只是漂亮信息图。
- 场景之间要有因果关系，不要变成材料摘要列表。
- 结尾清单必须和中段判断框架一致，不能新增另一套概念。

配图必须通过“用户看懂测试”：

- 优先使用现实工作名词，例如代码、日志、CI、测试、需求、diff、工具权限、验证标准。
- 少用抽象词和组织图，除非画面能立刻说明它在解决什么问题。
- 图内文字宁可少，也要让主语、动作、结果清楚。
- 模式、架构、框架类画面必须优先展示架构关系，而不是解释卡片。默认版式是：架构图为主，`适用 / 优势 / 风险` 为辅，再给一个现实场景。
- 架构图必须能展示动作流：谁触发、谁处理、谁验证、谁汇总、失败怎么回流。只写模式名和定义不合格。
- 每种模式必须有明显不同的图形关系。比如生成验证是线性加回路，子 Agent 是主从分发，Teams 是多线并行，总线是事件分发，共享状态是多方读写同一状态。
- 抽帧检查时发现“听得懂但看不懂”，必须重做画面，不要只改字幕。

## 立意传播门禁

进入素材类型和立意前，必须先通过“选题门禁”。选题不是材料标题，而是这条视频为什么值得做。

选题必须回答：

- 这条素材能解决观众什么真实痛点？
- 它的传播钩子是什么：纠偏、反差、痛点、方法、结果还是新观点？
- 为什么现在值得做：来源新、观点强、问题热，还是能给方法？
- 来源是否足够可信，边界能不能说清？
- 能不能做成清楚画面，而不是只能堆文字？

选题评分默认看 6 个维度：

| 维度 | 判断问题 |
| --- | --- |
| 观众价值 | 观众看完是否能得到方法、判断、新观点或真实痛点建议 |
| 传播钩子 | 是否有纠偏、反差、痛点、方法或结果，能不能被一句话转述 |
| 来源强度 | 来源是否可信、足够新、足够具体，是否有一手材料支撑 |
| 视觉潜力 | 能否做成清晰信息图、流程图、对比图或案例图 |
| 可执行性 | 观众能否带走检查清单、操作步骤或决策框架 |
| 合规安全 | 是否能避开版权、夸大、敏感表达和平台误读风险 |

进入立意前，必须先通过“素材类型门禁”。原始材料类型不同，视频结构不同，不能用统一模板硬套。

| 素材类型 | 视频重点 | 默认结构 | 常见坑 |
| --- | --- | --- | --- |
| 观点文章 / 访谈 | 提炼一个可传播判断 | 观点是什么 -> 对观众意味着什么 -> 你该怎么做 | 只复述作者说了什么，没有给观众建议 |
| 科普 / 概念解释 | 让观众听懂一个概念 | 常见误区 -> 人话解释 -> 现实例子 -> 使用边界 | 堆定义和术语，缺少现实例子 |
| 产品新功能 | 讲清解决什么问题和工作方式变化 | 功能表象 -> 背后变化 -> 谁能用 -> 怎么落地 -> 边界提醒 | 只做 release note，或者把机制当立意 |
| 工程实践 / 技术博客 | 给方法和流程 | 问题场景 -> 方法框架 -> 实操步骤 -> 风险清单 | 讲成概念科普，没有给可执行步骤 |
| 案例复盘 | 提炼可复用经验 | 案例做了什么 -> 为什么有效 -> 普通人怎么借鉴 | 只讲案例很厉害，没有抽出可迁移方法 |
| 开源项目 / 工具 | 判断能不能用、适合谁用 | 解决什么问题 -> 怎么用 -> 适合谁 -> 坑在哪里 | 只介绍仓库功能，不讲使用门槛和适用场景 |
| 官方文档 | 翻译成使用建议 | 官方说了什么 -> 关键变化 -> 使用场景 -> 注意边界 | 逐条翻译文档，没有提炼用户该怎么做 |
| 热点概念 | 借热点讲落地 | 大家误解什么 -> 真正关键是什么 -> 如何落地 | 只解释名词，蹭热点但不给方法 |

进入口播前，必须先通过“一句话转述测试”：

- 普通观众看完后，能不能用一句人话复述这条视频。
- 这句话是否包含明确收益，而不是只说“某公司发布了某功能”。
- 这句话是否有传播钩子：纠偏、反差、行动建议或痛点解决。
- 标题、封面和前 15 秒开头，是否都围绕同一句立意展开。
- 来源背书是否只是可信度证据，而不是替代立意本身。
- 如果视频讲的是新功能或新机制，必须追问它代表的工作方式变化。机制不能直接当立意；例如 `Agent identity` 是机制，`AI 从个人助手变成组织员工` 才是可传播的主判断。

## 基本命令

初始化：

```bash
python3 scripts/video_pipeline.py init
```

创建一个视频项目：

```bash
python3 scripts/video_pipeline.py create \
  --slug google-okf \
  --title "AI 能读懂的企业知识库怎么建？Google 给出了答案" \
  --topic-hook "AI 能读懂的企业知识库怎么建" \
  --topic-reason "Google OKF 给出了可落地的底层方法" \
  --audience-pain "企业知识散乱，Agent 读不懂也用不好" \
  --material-type engineering_practice \
  --thesis "Google OKF 给出了一套把企业知识整理成 AI 可用工程资产的方法" \
  --viewer-value "观众能学会从散乱知识到 Agent 可用上下文的落地路径" \
  --source-url "https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing" \
  --agent codex \
  --duration 180
```

生成 Agent 任务包：

```bash
python3 scripts/video_pipeline.py agent-pack google-okf --agent codex
python3 scripts/video_pipeline.py agent-pack google-okf --agent claude-code
```

口播自审通过后，生成分镜：

```bash
python3 scripts/video_pipeline.py scene-plan google-okf --duration 180
```

生成通用 HyperFrames 工程：

```bash
python3 scripts/video_pipeline.py scaffold-hyperframes google-okf
```

检查状态和 QA：

```bash
python3 scripts/video_pipeline.py status google-okf
python3 scripts/video_pipeline.py qa google-okf
python3 scripts/video_pipeline.py qa google-okf --final
```

打包到 `deliverables/`：

```bash
python3 scripts/video_pipeline.py package google-okf --slug google-okf
```

`qa` 默认做规划阶段检查；`qa --final` 会要求最终 MP4 和封面 PNG 已经存在。`package` 默认也要求最终视频和封面都存在；如果只是测试目录结构，可以显式使用 `--allow-incomplete` 生成草稿包。

## 标准项目结构

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
    hyperframes/
  cover/
  qa/
  final/
```

## Agent 适配方式

流水线不直接假设某个 Agent 的命令行接口，而是生成同一套可读写文件：

- Codex：读取 `AGENTS.md` 和 `agent-pack/codex/*.md`。
- Claude Code：读取 `CLAUDE.md` 和 `agent-pack/claude-code/*.md`。
- 其他 Agent：读取 `AGENT_TASKS.md` 和 `agent-pack/generic/*.md`。

每个 Agent 的任务都被拆成四类：

1. `01_research.md`：研究材料、确认事实、补观众价值。
2. `02_voiceover_review.md`：从观众视角审口播。
3. `03_scene_and_visuals.md`：检查分镜和配图逻辑。
4. `04_qa.md`：最终 QA。

这让不同 Agent 可以接力，而不会互相覆盖状态。真正的流程状态只看 `state.json`。

## 门禁

当前门禁包括：

- `topic_selection`
- `material_type`
- `intent`
- `research`
- `voiceover_review`
- `voiceover_self_approved`
- `scene_plan`
- `visual_logic`
- `cover_hook`
- `logic_visual_alignment`
- `pronunciation`
- `audio`
- `video_render`
- `cover`
- `publish_copy`
- `qa`
- `package`

`pronunciation` 是音频生成前的强制门禁：

- 英文产品名、人名、公司名保留英文，不做中文音译或翻译。
- 多音字、行业术语、缩写必须单独列入发音稿。
- 例：`超级个体长出来` 中的 `长` 必须读 `zhang`，表示“生长出来”，不能读 `chang`。
- 发音稿只能调整停顿、连读和读音提示，不能改事实、观点、术语和字幕文案。

`cover_hook` 是封面生成前后的强制门禁：

- 封面大字必须能独立表达立意。
- 封面必须有传播钩子，不能只是“某报告/某文章/某功能解读”。
- 封面和标题、开头 15 秒必须围绕同一个问题。
- 理念型新功能封面优先写成 `产品名核心理念：旧角色/旧方式变成新角色/新方式`，让观众一眼看懂变化，而不是只看见功能名或机制名。
- 生成后必须查看成图，检查文字完整、无重叠、缩略图可读。
- 如果封面标题被用户或主 agent 改动，必须同步更新发布标题、短标题、简介、QA 记录和平台封面 JPG。

`publish_copy` 是发布包生成前的强制门禁：

- 短标题必须按平台限制单独生成，不能直接复用封面大标题。
- 视频号短标题默认控制在 12 个汉字以内；用户要求 16 个字符以内时，英文、数字、空格和标点全部计入。
- 简介第一句必须回答“观众看完能得到什么”，后面再补来源、结构和话题。
- 话题标签要少而准，优先主题、工具、受众和内容形态，不堆无关热词。

`logic_visual_alignment` 是最终渲染前的强制门禁：

- 先生成代表帧或接触表。
- 对照逻辑线逐幕检查：这一幕到底在讲什么，画面是否直接表达。
- 如果配图和逻辑线不对齐，优先改画面，不要用字幕硬解释。
- 通过标准是：不听音频，只看抽帧，也能看懂视频的主要推进。

`qa` 是发布前的最终成片门禁：

- 必须检查最终 MP4 抽帧，不得只检查无字幕源图。
- 必须清理旧片段后重渲；QA 只能检查 `segments.txt` 里实际使用的片段，不能混用历史 segments 文件。
- 必须生成 `qa/segment_contact_sheets/` 和 `qa/contact-sheet-final-all-frames.jpg`，一个看实际拼接片段，一个看最终成片逐场景画面。
- 字幕必须与音频语义一致，并且与当前画面同步。
- 字幕最多两行，不能被裁切，也不能遮挡图片里的核心信息。
- 图片内部元素不得重叠、贴边、截断；发现后必须重排版再渲染。
- 背景默认纯色，不使用方格、网格或噪声纹理。

## Post-EP04 Repair Lessons As Gates

These checks were added after repeated fixes in a real multi-episode production run. They are now blocking gates, not optional polish:

- **Keep the episode topic aligned.** Cover, title, voiceover, visuals, and publish copy must serve the same episode promise.
- **The frame must explain before the subtitle helps.** Subtitles support the image; they cannot rescue a confusing chart.
- **Clean stale render segments before re-rendering.** QA must inspect only clips listed in `segments.txt`.
- **Use final MP4 frames for QA.** Generate both `qa/segment_contact_sheets/` and `qa/contact-sheet-final-all-frames.jpg`.
- **Subtitles must not cover the visual.** Max two lines; no blocking takeaway bars, flow nodes, key cards, or arrows.
- **No internal visual collisions.** Titles, cards, nodes, arrows, lines, and takeaway bars need safe spacing; arrowheads must be visible.
- **Use final audio/VTT timing for scene switches.** Avoid storyboard-estimated durations that cause subtitle-frame drift.
- **Prefer solid backgrounds.** Grid, checker, and noise textures are disabled by default because they reduce readability.
- **Protect English term spacing.** Do not merge `Claude Code`, `Context Engineering`, or `Prompt Engineering`.
- **Keep publish copy synchronized.** Cover changes must update title, short title, description, QA notes, and platform cover exports.

Passing standard: viewers should understand the main logic from final contact sheets without audio, and subtitles should never hide the information they are explaining.

可以手动更新门禁：

```bash
python3 scripts/video_pipeline.py gate google-okf voiceover_review approved --note "多视角审稿已完成"
```

## 当前 V1 能做什么

- 创建标准视频项目。
- 生成 Codex / Claude Code / generic Agent 任务包。
- 从自审通过口播生成结构化分镜 JSON 和 Markdown。
- 生成通用 HyperFrames 工程骨架。
- 运行轻量 QA，检查固定开场、结束语、立意传播性、分镜结构和配图逻辑标记。
- 按标准目录打包到 `deliverables/`；正式打包要求已有最终视频和封面。

## 当前 V1 还不做什么

- 不自动调用 LLM 写口播。
- 不绕过门禁，但默认由主 agent 按规范自审、自改、自确认；只有账号登录、扫码授权、付费服务、人声授权、来源事实无法确认或高风险合规边界不清时才暂停询问用户。
- 不自动调用 TTS。
- 不自动设计最终精美封面。
- 不自动点击平台发布。

这些能力可以作为 V2/V3 插件接入，但不能破坏门禁。

## 开源边界

未来开源时，建议保留：

- `scripts/video_pipeline.py`
- `docs/video-generation-pipeline.md`
- 通用 HyperFrames 模板
- Agent profile 配置
- 门禁规则和 QA 清单

不应默认包含：

- 个人账号、Cookie、平台登录态
- 私有 API Key
- 未授权字体、音乐、图片、视频素材
- 平台自动发布的绕过逻辑

## 和内容流水线的关系

`scripts/content_pipeline.py` 负责：

- 信息雷达
- 选题评分
- 创建选题项目
- 生成发布包
- 回填发布数据

`scripts/video_pipeline.py` 负责：

- 立意确认后的单条视频生产
- 口播、分镜、画面、QA、打包
- 多 Agent 协作门禁

两者可以串起来，但不强绑定。

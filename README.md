# AI Video Pipeline

[中文说明](README.zh-CN.md)

A file-driven workflow for turning source material into short-form knowledge videos with agent handoff, topic gates, script review, visual QA, and publish-ready packaging.

This project is designed for Codex, Claude Code, and other coding agents, but it is not tied to any single agent runtime. Agents coordinate through plain files such as `state.json`, `process/*.md`, and `agent-pack/*`.

## What It Solves

Most AI-assisted video workflows jump straight from "here is a link" to "generate a video". That creates three common failures:

- The topic is not valuable enough for viewers.
- The script explains the source but does not give a useful takeaway.
- The visuals look polished but viewers cannot understand the logic.

This pipeline adds gates before generation:

```text
source material
-> topic selection
-> material type
-> thesis and viewer value
-> research brief
-> voiceover draft
-> audience-perspective review
-> confirmed voiceover
-> pronunciation notes
-> scene plan
-> visual logic
-> cover hook
-> render
-> contact-sheet QA
-> publish package
```

## Core Ideas

- **Viewer-first thesis**: every video must answer what the viewer gains.
- **Material-aware structure**: product updates, opinion essays, explainers, engineering blogs, case studies, docs, and tools need different scripts.
- **Readable visuals**: every scene should be understandable from the frame, not rescued by narration.
- **Agent-portable handoff**: Codex, Claude Code, or another agent can continue from the same project folder.
- **Gated production**: topic, script, visuals, pronunciation, cover, and QA have explicit checkpoints.

## Hard QA Lessons

The workflow includes repair lessons from real multi-episode production:

- Final QA must inspect rendered MP4 frames, not only source images.
- Re-rendering must clear stale segments, and segment contact sheets must follow `segments.txt`.
- Subtitles are max two lines and cannot cover key cards, arrows, flow nodes, or takeaway bars.
- Scene switches should follow final audio/VTT timing, not estimated storyboard durations.
- Visuals use clean solid backgrounds by default; grid/checker/noise backgrounds are disabled unless explicitly justified.
- Cover, title, short title, description, and platform cover exports must stay synchronized.

## Quick Start

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

Generate an agent task pack:

```bash
python3 scripts/video_pipeline.py agent-pack claude-tag-ai-employee --agent codex
python3 scripts/video_pipeline.py agent-pack claude-tag-ai-employee --agent claude-code
```

Check project status:

```bash
python3 scripts/video_pipeline.py status claude-tag-ai-employee
```

After the confirmed voiceover is written, generate a scene plan:

```bash
python3 scripts/video_pipeline.py scene-plan claude-tag-ai-employee --duration 180
```

Scaffold a simple HyperFrames-style visual project:

```bash
python3 scripts/video_pipeline.py scaffold-hyperframes claude-tag-ai-employee
```

Run QA:

```bash
python3 scripts/video_pipeline.py qa claude-tag-ai-employee
python3 scripts/video_pipeline.py qa claude-tag-ai-employee --final
```

Package deliverables:

```bash
python3 scripts/video_pipeline.py package claude-tag-ai-employee --slug claude-tag-ai-employee
```

More examples are in [examples/README.md](examples/README.md).

## Material Types

Use `--material-type` to choose the starting structure:

| Type | Best For | Default Structure |
| --- | --- | --- |
| `opinion` | Opinion essays, interviews | Point -> viewer meaning -> advice |
| `explainer` | Concepts and education | Misconception -> plain explanation -> example -> boundary |
| `product_feature` | Product updates | Feature surface -> work shift -> who can use it -> how to apply -> boundary |
| `engineering_practice` | Engineering blogs | Problem -> method -> steps -> risk checklist |
| `case_study` | Case studies | What happened -> why it worked -> what viewers can reuse |
| `open_source_tool` | Tools and repos | Problem solved -> how to use -> fit -> pitfalls |
| `official_doc` | Official docs | What changed -> scenarios -> usage advice -> boundaries |
| `hot_concept` | Trend concepts | Misconception -> real key -> how to implement |

## Project Structure

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

## Agent Support

The pipeline generates task packs for:

- Codex: `AGENTS.md` and `agent-pack/codex/`
- Claude Code: `CLAUDE.md` and `agent-pack/claude-code/`
- Generic agents: `AGENT_TASKS.md` and `agent-pack/generic/`

The contract is simple: read `state.json`, work on the current gate, write outputs into the project folder, and do not skip QA.

## Customization

The default opening and closing lines can be overridden without changing code:

```bash
export AI_VIDEO_PIPELINE_OPENING="大家好，欢迎来到今天的 AI 工程笔记。"
export AI_VIDEO_PIPELINE_CLOSING="以上就是今天的内容，我们下期见。"
```

See [docs/customization.md](docs/customization.md).

## Pronunciation Rule

Before generating TTS, the pipeline should create a pronunciation checklist for English names, product names, abbreviations, and Chinese polyphones.

For free TTS engines, do not rely on pinyin notes alone. If a Chinese polyphone is likely to be misread and the wording is not essential, rewrite it into an unambiguous phrase before synthesis. For example, if `反直觉` is read with `觉` as `jiao`, rewrite the spoken line as `出乎意料`.

## Documentation

- [Pipeline Guide](docs/video-generation-pipeline.md)
- [Branding And Publishing Rules](docs/video-branding.md)
- [Final QA Checklist](docs/final-qa-checklist.md)
- [Production Learnings](docs/video-production-learnings.md)
- [Customization](docs/customization.md)
- [Open-Source Release Checklist](docs/open-source-checklist.md)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)

## What Is Not Included

This repo intentionally does not include:

- Generated videos
- Personal drafts or private publishing history
- Platform credentials
- Paid TTS keys
- Downloaded source videos
- WeChat, Douyin, Xiaohongshu, or other platform session data

## License

Apache License 2.0. See [LICENSE](LICENSE).

## Status

Early local MVP. The CLI is intentionally small and uses only the Python standard library.

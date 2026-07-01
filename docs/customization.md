# Customization

## Opening And Closing Lines

The pipeline enforces a fixed opening and closing line so every video has a consistent brand rhythm.

Defaults:

```text
大家好，欢迎来到今天的 AI 工程观察。
以上就是今天的内容，希望对你有启发，我们下期见。
```

Override them without editing code:

```bash
export AI_VIDEO_PIPELINE_OPENING="大家好，欢迎来到今天的 AI 工程笔记。"
export AI_VIDEO_PIPELINE_CLOSING="以上就是今天的内容，我们下期见。"
```

The same values are used by scene generation and QA. If the final voiceover does not contain the configured opening and closing lines, final QA will fail.

## Agent Profiles

The default profiles are:

- `codex`
- `claude-code`
- `generic`

Each project contains:

- `AGENTS.md` for Codex-style agents
- `CLAUDE.md` for Claude Code
- `AGENT_TASKS.md` for generic agents
- `agent-pack/<agent>/task.md` for specific handoff instructions

## Publishing Platforms

Publishing is intentionally not automated in the open-source MVP. Keep platform credentials and login state outside the repository.


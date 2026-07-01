# Contributing

Thanks for helping improve AI Video Pipeline.

This project is intentionally file-driven and agent-portable. A useful contribution should make the workflow easier to understand, easier to audit, or easier to run across Codex, Claude Code, and other agents.

## Development Setup

The core CLI uses only the Python standard library.

```bash
python3 scripts/video_pipeline.py init
python3 -m py_compile scripts/video_pipeline.py
```

Run a small smoke test before opening a pull request:

```bash
python3 scripts/video_pipeline.py create \
  --slug smoke-test \
  --title "Smoke test" \
  --topic-hook "A useful viewer-first hook" \
  --topic-reason "This checks project creation" \
  --audience-pain "Viewers need a clear workflow" \
  --material-type explainer \
  --thesis "A pipeline should make video decisions explicit" \
  --viewer-value "Viewers learn what to check before rendering" \
  --source-url "https://example.com" \
  --agent codex \
  --duration 120

python3 scripts/video_pipeline.py status smoke-test
python3 scripts/video_pipeline.py qa smoke-test
```

Delete the generated smoke project before committing:

```bash
rm -rf video-pipeline/projects/smoke-test
```

## Contribution Principles

- Keep viewer value first. A video must solve a viewer problem or give a useful judgment.
- Keep language concrete. Avoid abstract labels that only make sense to the author.
- Keep visuals readable. Every frame should have a clear title, structure, and reading order.
- Keep agent handoff explicit. Important decisions should be written to files, not hidden in chat history.
- Keep private data out of the repo. Do not commit generated videos, platform sessions, API keys, cookies, QR codes, or personal drafts.

## Pull Request Checklist

- [ ] The CLI still passes `python3 -m py_compile scripts/video_pipeline.py`.
- [ ] Any new gate or artifact is documented in `README.md`.
- [ ] Examples do not contain private links, credentials, or personal publishing history.
- [ ] Large generated media files are not included.
- [ ] Changes preserve Codex, Claude Code, and generic agent handoff paths.


# Open-Source Release Checklist

Use this before pushing the repository to GitHub.

## Must Pass

- [ ] The repo contains only reusable pipeline code, docs, and examples.
- [ ] Generated videos, covers, audio, downloaded source files, and platform screenshots are excluded.
- [ ] No `.env`, API keys, cookies, QR codes, or login state are present.
- [ ] `python3 -m py_compile scripts/video_pipeline.py` passes.
- [ ] A smoke project can be created and checked with `status`.
- [ ] README quick start works from a fresh clone.
- [x] Apache-2.0 license has been selected and `LICENSE` is present.
- [ ] Final QA rules are documented: stale segment cleanup, `segments.txt`, final MP4 frame contact sheet, subtitle-image alignment, and publish copy synchronization.

## Suggested Scan

```bash
rg -n "/Users/|xwechat|api[_-]?key|secret|token|password|cookie|authorization|Bearer|sk-|AKIA|私钥|二维码" .
find . -type f -size +1M -print
```

Review every hit before publishing.

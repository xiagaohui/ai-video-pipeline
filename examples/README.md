# Examples

These examples show how to start different kinds of video projects. They intentionally use placeholder source URLs.

## Product Feature

Use this for product updates where the real value is not the UI feature itself, but the workflow shift behind it.

```bash
python3 scripts/video_pipeline.py create \
  --slug claude-tag-ai-employee \
  --title "Claude Tag core idea: AI moves from personal assistant to org employee" \
  --topic-hook "AI moves from personal assistant to organization employee" \
  --topic-reason "The feature reveals a new way to put AI into team workflows" \
  --audience-pain "People see only the feature and miss the work design shift" \
  --material-type product_feature \
  --thesis "Claude Tag represents AI moving from personal assistant to organization employee" \
  --viewer-value "Viewers learn what to check before adding AI to team workflows" \
  --source-url "https://example.com/source" \
  --agent codex \
  --duration 180
```

## Engineering Practice

Use this for technical posts that should become a practical method.

```bash
python3 scripts/video_pipeline.py create \
  --slug minimal-agent-loop \
  --title "Build a minimal useful Agent Loop" \
  --topic-hook "14 steps to build a minimal useful Agent Loop" \
  --topic-reason "Loop Engineering is easy to discuss and hard to operate" \
  --audience-pain "People let AI run more rounds but cannot recover, observe, or take over the loop" \
  --material-type engineering_practice \
  --thesis "A useful Loop needs task fit, recovery, observation, and takeover points" \
  --viewer-value "Viewers get a practical checklist for building a minimal Loop" \
  --source-url "https://example.com/source" \
  --agent claude-code \
  --duration 240
```

## Hot Concept

Use this when a concept is trending and the video needs to correct a common misunderstanding.

```bash
python3 scripts/video_pipeline.py create \
  --slug loop-engineering-hot-concept \
  --title "Loop Engineering is not just running AI more times" \
  --topic-hook "The key is not more loops, but recoverable loops" \
  --topic-reason "The term is popular, but many explanations stay abstract" \
  --audience-pain "Viewers want to know how to apply the concept in real work" \
  --material-type hot_concept \
  --thesis "Loop Engineering becomes useful only when the loop is recoverable, observable, and controllable" \
  --viewer-value "Viewers learn the minimum conditions for deciding whether a task should enter a loop" \
  --source-url "https://example.com/source" \
  --agent generic \
  --duration 180
```


# Clipfarm v0.5 — Editing Intelligence

Pass 5 adds an editing-decision layer on top of the v0.4 viral/retention ranking.

## What changed

- sentence-aware boundary repair
- clip-type edit profiles:
  - story
  - utility
  - reaction
  - debate
  - default
- dead-air trimming plans
- filler-removal plans
- attention-event-driven zoom events
- caption emphasis metadata
- three variants per candidate:
  - balanced
  - tight
  - punchy
- edit plans are now embedded into `render_plan.json`

## Important

This pass generates structured edit instructions. The renderer still needs to consume every
instruction type fully. That is intentional: Pass 6 can make batch rendering, QA, retries and
variant execution reliable instead of hiding orchestration inside the editor.

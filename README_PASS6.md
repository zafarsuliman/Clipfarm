# Clipfarm v0.6 — Production Engine

Pass 6 turns the intelligent clipping pipeline into a production-oriented workflow.

## Added

- batch processing across multiple source URLs/files
- retry handling for failed source jobs
- duplicate candidate removal
- production execution for top-ranked candidates
- technical QA using ffprobe
- automatic separation of passed vs rejected renders
- batch reports and production reports
- failure isolation so one broken item does not stop an entire batch

## New concepts

### Batch
`batch_engine.py` runs multiple sources concurrently with retries.

### Deduplication
`dedupe.py` removes highly overlapping or transcript-near-identical candidates before render.

### Technical QA
`qa.py` checks:
- output exists
- video stream exists
- audio stream exists
- file isn't trivially empty
- duration is within bounds
- aspect ratio is correct

### Production execution
`production.py`:
1. loads a run manifest
2. deduplicates candidates
3. takes the top N
4. renders them
5. runs QA
6. writes a production report

## Important limitation

This pass still uses the current renderer's core `render_candidate` path. The v0.5 structured
edit plan is not yet executed at full fidelity for every zoom/tightening instruction. Pass 7
should be the end-to-end integration/hardening pass that unifies those edit instructions with
the production renderer and CLI.

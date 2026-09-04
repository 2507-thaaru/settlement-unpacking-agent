# Antigravity quick start

Everything needed to start building is already in this repo. Nothing
below requires you to design anything new — just open the folder and
start assigning briefs to agents.

## 1. Open the repo

Open this folder (`settlement-unpacking-agent/`) as a project in
Antigravity's Editor view. Let it index the full codebase before
spawning any agents — the schema and docstrings are what keep agents
from inventing generic reconciliation logic instead of this specific
design.

## 2. Read order (for you, before assigning agents)

1. `docs/project-plan.md` — problem statement, why it's underserved
2. `docs/architecture.md` — module map, exception-to-pass mapping, assumptions
3. `src/schemas.py` — the fixed data contract every pass builds against

## 3. Assign work in the Manager surface, in this order

| Order | Brief | Can run in parallel with |
|---|---|---|
| 1 | `docs/agent-briefs/pass1-batch-match.md` | Passes 2, 3, 4 |
| 1 | `docs/agent-briefs/pass2-order-validation.md` | Passes 1, 3, 4 |
| 1 | `docs/agent-briefs/pass3-reserve-forecast.md` | Passes 1, 2, 4 |
| 1 | `docs/agent-briefs/pass4-gst-itc.md` | Passes 1, 2, 3 |
| 2 | `docs/agent-briefs/pass5-and-integration.md` (Pass 5 half) | Nothing — do this after 1-4 are green |
| 3 | `docs/agent-briefs/pass5-and-integration.md` (integration half) | Nothing — this is the final verification step |

Passes 1-4 touch different files and read the same fixed input data, so
there's no reason not to run all four agents at once.

## 4. Verify as you go, don't wait until the end

After each pass agent finishes:
```bash
pytest tests/test_passN_*.py -v
python -m src.orchestrator --data-dir data
```
If a pass's tests pass and the orchestrator shows it as `"status": "ok"`,
move on. Don't let four passes all claim done and then discover two are
broken at integration time.

## 5. Final check before you stop for the day

```bash
pytest tests/ -v
streamlit run app/dashboard.py
```
Both should work even if Pass 5 (stretch) isn't done — the orchestrator
and dashboard degrade gracefully by design.

## 6. Keep WHAT_BROKE.md honest

This is a submission requirement, not a nice-to-have. Real entries from
real agent failures are worth more than generic ones written after the
fact — Antigravity's own verification runs and failed test output are
good raw material for this file.

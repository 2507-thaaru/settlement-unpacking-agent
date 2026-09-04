# Settlement Unpacking Agent

**Razorpay AI Buildathon 2026 — Track 4: AI Finance Controller**

An agent that explodes lumped Razorpay settlement credits back into their
components, tracks rolling reserve release, and catches GST-on-MDR ITC
leakage — three finance-ops loops most reconciliation tools treat separately,
closed here in one batch-explosion pipeline.

**Building this with Antigravity?** Start at [`ANTIGRAVITY_START_HERE.md`](ANTIGRAVITY_START_HERE.md) — everything's ready, nothing left to design.

Full problem statement: [`docs/project-plan.md`](docs/project-plan.md)
Full architecture: [`docs/architecture.md`](docs/architecture.md)

## Status

All scaffolding, schema, tests, orchestrator, and dashboard are complete
and verified working. All five matching passes are stubbed with a full
spec in their docstrings and a matching test file — implementing those
is the remaining work.

- [x] Synthetic data generator (settlement report, bank statement, GST invoice, sales ledger, reserve ledger)
- [x] Shared schema/data contract (`src/schemas.py`)
- [x] Orchestrator (`src/orchestrator.py`) — runs, degrades gracefully with unimplemented passes
- [x] Dashboard (`app/dashboard.py`) — runs, renders honest per-pass status
- [x] Test suite for all 5 passes, written against real ground truth (`tests/`)
- [x] Agent briefs for each pass, ready to paste into Antigravity (`docs/agent-briefs/`)
- [ ] Pass 1 — batch-level settlement <-> bank match
- [ ] Pass 2 — order-level explosion and validation
- [ ] Pass 3 — rolling reserve tracking & release forecast
- [ ] Pass 4 — GST-on-MDR ITC leakage detection
- [ ] Pass 5 (stretch) — cross-period settlement flagging
- [ ] Pitch video

## Repo structure

```
settlement-unpacking-agent/
├── ANTIGRAVITY_START_HERE.md   # entry point for building this with Antigravity
├── data_generator/
│   └── generate_data.py        # synthetic dataset generator with injected noise
├── data/                        # generated CSVs + ground truth (regeneratable)
├── src/
│   ├── schemas.py               # the fixed data contract every pass builds against
│   ├── orchestrator.py          # fully implemented — chains passes, aggregates report
│   └── matcher/
│       ├── pass1_batch_match.py       # stub + full spec in docstring
│       ├── pass2_order_validation.py  # stub + full spec in docstring
│       ├── pass3_reserve_forecast.py  # stub + full spec in docstring
│       ├── pass4_gst_itc.py           # stub + full spec in docstring
│       └── pass5_cross_period.py      # stub + full spec in docstring (stretch)
├── app/
│   └── dashboard.py             # fully implemented Streamlit dashboard
├── tests/                        # executable spec — one file per pass, checked against ground truth
├── docs/
│   ├── project-plan.md          # problem statement & scope
│   ├── architecture.md          # module map, data flow, assumptions
│   └── agent-briefs/            # ready-to-paste Antigravity task briefs, one per pass
└── WHAT_BROKE.md                 # running log of build issues + fixes (submission requirement)
```

## Running things

```bash
pip install -r requirements.txt

# regenerate synthetic data (optional, already generated)
cd data_generator && python generate_data.py --seed 42 --batches 18

# run the test suite (currently all fail with NotImplementedError — expected until passes are built)
pytest tests/ -v

# run the orchestrator directly
python -m src.orchestrator --data-dir data

# launch the dashboard
streamlit run app/dashboard.py
```

### Injected exceptions (ground truth, for evaluation)

The generator always injects exactly six known faults so the matching
pipeline's recall can be measured objectively:

1. A settlement batch with a **missing UTR** in the bank statement → Pass 1
2. A batch with an **unexplained deduction** not attributable to any known field → Pass 1
3. A batch charged **MDR at the wrong rate** → Pass 2
4. A batch whose **rolling reserve is never released**, even past the liability window → Pass 3
5. A monthly **GST invoice that under-reports** the GST-on-MDR actually charged → Pass 4
6. A **cross-period settlement** (order placed in one GST month, settled in the next) → Pass 5 (stretch)

`bank_statement_with_ground_truth.csv` includes a `settlement_id_hint`
column for pipeline self-checks during development only — this column
does not exist in real bank data and must never be used by the actual
matching logic, only by the test suite.

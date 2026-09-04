# Agent brief — Pass 5 (stretch) + Integration/Dashboard verification

## Pass 5 — only start this after Passes 1-4 are all green

### Paste into Antigravity's Manager surface:

> Implement `src/matcher/pass5_cross_period.py` in this repo. Full spec
> is in that file's module docstring. For every order row in
> `settlement_report.csv`, flag `CROSS_PERIOD_SETTLEMENT` when
> `order_date` and `settlement_date` fall in different calendar months.
> Return a `PassResult` per `src/schemas.py`. When done, run
> `pytest tests/test_pass5_cross_period.py -v` and confirm it passes.
> Log anything that breaks in `WHAT_BROKE.md`.

### Definition of done
- `pytest tests/test_pass5_cross_period.py -v` passes
- `python -m src.orchestrator --data-dir data` shows `pass5_cross_period` as `"status": "ok"`

---

## Integration + dashboard verification agent — run this last

### Paste into Antigravity's Manager surface:

> Run `pytest tests/ -v` in this repo and confirm every test across all
> five passes is green. Then run
> `python -m src.orchestrator --data-dir data --out report.json` and
> check the summary shows `passes_implemented` equal to `passes_total`
> and a non-zero `total_exceptions_found` that matches the six injected
> exceptions in `data/injected_exceptions.json`. Then launch
> `streamlit run app/dashboard.py`, use browser control to load it, and
> confirm: (1) every pass shows green/"ok" status, (2) the exception
> table lists all six injected exceptions with correct categories, (3)
> the reserve forecast section shows the still-held reserve batches.
> Take a screenshot as verification. If anything is broken, fix it and
> add an entry to `WHAT_BROKE.md` describing what broke and how it was
> fixed — this is a required part of the buildathon submission, so be
> specific rather than generic.

### Definition of done
- `pytest tests/ -v` — all tests across all passes pass
- `report.json` shows 5/5 (or 4/5 if Pass 5 was skipped) passes implemented
- Dashboard screenshot confirms the full pipeline renders correctly end to end
- `WHAT_BROKE.md` has real, specific entries from the actual build — this becomes evidence for the submission requirement to explain what broke and how you recovered

# Agent brief — Pass 4: GST-on-MDR ITC leakage detection

## Paste this into Antigravity's Manager surface as the task:

> Implement `src/matcher/pass4_gst_itc.py` in this repo. Full spec is in
> that file's module docstring. Derive each settlement's billing period
> from `settlement_date` (format "YYYY-MM"), sum `gst_on_mdr` from
> `settlement_report.csv` per period, and compare against
> `gst_invoice.csv`'s `gst_on_mdr_amount` for the same period, within
> `schemas.AMOUNT_TOLERANCE`. Flag `GST_ITC_MISMATCH` for any period
> where they don't reconcile, with the gap amount as the ITC leakage
> figure. Return a `PassResult` per `src/schemas.py`, with
> `total_itc_leakage` in metrics. When done, run
> `pytest tests/test_pass4_gst_itc.py -v` and confirm both tests pass —
> including that the one clean period is NOT flagged. Log anything that
> breaks in `WHAT_BROKE.md`.

## Context files to give the agent
- `src/matcher/pass4_gst_itc.py` (the stub with full spec)
- `src/schemas.py`
- `tests/test_pass4_gst_itc.py`
- `data/settlement_report.csv`, `data/gst_invoice.csv`

## Definition of done
- `pytest tests/test_pass4_gst_itc.py -v` — all tests pass
- `python -m src.orchestrator --data-dir data` shows `pass4_gst_itc` as `"status": "ok"`

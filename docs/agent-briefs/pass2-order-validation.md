# Agent brief — Pass 2: Order-level explosion and validation

## Paste this into Antigravity's Manager surface as the task:

> Implement `src/matcher/pass2_order_validation.py` in this repo. Full
> spec is in that file's module docstring. For every order row in
> `settlement_report.csv`, validate it exists with a matching amount in
> `sales_ledger.csv` (join on `order_id`), and check that `mdr_fee`
> equals `gross_amount * schemas.MDR_RATE` within
> `schemas.AMOUNT_TOLERANCE`. Flag `MDR_RATE_MISMATCH` for every order
> row that fails the rate check — one whole settlement batch in the
> synthetic data has every order overcharged by ~0.5 percentage points,
> and every one of those order rows needs its own exception, not just
> one per batch. Return a `PassResult` per `src/schemas.py`. When done,
> run `pytest tests/test_pass2_order_validation.py -v` and make sure
> both tests pass. Log anything that breaks, with how you fixed it, in
> `WHAT_BROKE.md`.

## Context files to give the agent
- `src/matcher/pass2_order_validation.py` (the stub with full spec)
- `src/schemas.py`
- `tests/test_pass2_order_validation.py`
- `data/settlement_report.csv`, `data/sales_ledger.csv`

## Definition of done
- `pytest tests/test_pass2_order_validation.py -v` — all tests pass
- `python -m src.orchestrator --data-dir data` shows `pass2_order_validation` as `"status": "ok"`

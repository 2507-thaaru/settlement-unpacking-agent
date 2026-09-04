# Agent brief — Pass 1: Batch-level settlement <-> bank match

## Paste this into Antigravity's Manager surface as the task:

> Implement `src/matcher/pass1_batch_match.py` in this repo. The full spec
> is in that file's module docstring — read it before writing any code.
> Match every settlement batch in `settlement_report.csv` to its bank
> credit row in `bank_statement.csv` using the reference code embedded in
> the bank narration (last 8 characters of `settlement_id`), not row
> order. Then reconcile the expected net credit (gross - mdr - gst -
> refund - chargeback - reserve_hold + reserve_released, using
> `reserve_ledger.csv` for the reserve figures) against the actual
> `credit_amount`, using `schemas.AMOUNT_TOLERANCE`. Flag `MISSING_UTR`
> when the UTR field is empty, and `UNEXPLAINED_DEDUCTION` when the
> reconciled amount doesn't match within tolerance. Return a `PassResult`
> per the schema in `src/schemas.py`. Do not use the
> `settlement_id_hint` column — it only exists in
> `bank_statement_with_ground_truth.csv` for testing and would not exist
> in a real bank statement. When done, run
> `pytest tests/test_pass1_batch_match.py -v` and make sure all three
> tests pass. Log anything that breaks along the way, with how you fixed
> it, as a new entry in `WHAT_BROKE.md`.

## Context files to give the agent (or let it read from the repo)
- `src/matcher/pass1_batch_match.py` (the stub with full spec)
- `src/schemas.py` (the data contract)
- `tests/test_pass1_batch_match.py` (the executable spec)
- `data/settlement_report.csv`, `data/bank_statement.csv`, `data/reserve_ledger.csv`

## Definition of done
- `pytest tests/test_pass1_batch_match.py -v` — all tests pass
- `python -m src.orchestrator --data-dir data` shows `pass1_batch_match` as `"status": "ok"`
- A `WHAT_BROKE.md` entry exists if anything broke during the build

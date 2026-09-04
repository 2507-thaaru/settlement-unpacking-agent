"""
Synthetic data generator for the Settlement Unpacking Agent.

Generates four linked datasets that mirror a Razorpay-style settlement
workflow, at order-level granularity:

  1. settlement_report.csv  - Razorpay's settlement export (order-level)
  2. bank_statement.csv     - bank NEFT credits for each settlement batch
  3. gst_invoice.csv        - Razorpay's monthly GST tax invoice on MDR
  4. sales_ledger.csv       - merchant's own order/sales records

Deliberately injects a known set of exceptions (recorded in
injected_exceptions.json) so the matching pipeline's recall can be
measured against ground truth instead of eyeballed.

Usage:
    python generate_data.py [--seed 42] [--batches 18] [--out ../data]
"""

import argparse
import json
import random
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

MDR_RATE = 0.02          # 2% merchant discount rate
GST_RATE = 0.18          # 18% GST on MDR
RESERVE_RATE = 0.05      # 5% of gross held as rolling reserve
RESERVE_WINDOW_DAYS = 120  # chargeback liability window before release


def rand_amount(low=500, high=45000):
    return round(random.uniform(low, high), 2)


def make_utr():
    return "UTR" + "".join(random.choice("0123456789") for _ in range(12))


def make_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:14]}"


def generate(seed: int, n_batches: int, orders_per_batch_range=(3, 6)):
    random.seed(seed)

    settlement_rows = []
    bank_rows = []
    ledger_rows = []
    reserve_rows = []
    invoice_rows = {}  # keyed by (year, month) -> accumulate totals

    injected = {
        "missing_utr_settlement_id": None,
        "mdr_rate_mismatch_settlement_id": None,
        "unexplained_deduction_settlement_id": None,
        "gst_invoice_mismatch_period": None,
        "reserve_not_released_settlement_id": None,
        "cross_period_settlement_id": None,
    }

    start_date = date(2026, 11, 20)  # deliberately spans a month boundary

    # pick which batch indices get which injected fault, spread out
    fault_slots = random.sample(range(n_batches), k=min(6, n_batches))
    (missing_utr_idx, mdr_mismatch_idx, unexplained_idx,
     gst_mismatch_idx, reserve_stuck_idx, cross_period_idx) = fault_slots

    for i in range(n_batches):
        settlement_id = make_id("setl")
        settlement_date = start_date + timedelta(days=i * 2)
        n_orders = random.randint(*orders_per_batch_range)

        batch_gross = 0.0
        batch_mdr = 0.0
        batch_gst = 0.0
        batch_refund = 0.0
        batch_chargeback = 0.0

        for _ in range(n_orders):
            order_id = make_id("order")
            payment_id = make_id("pay")

            # cross-period: order placed in one GST month, settled in the next
            if i == cross_period_idx:
                order_date = date(settlement_date.year, settlement_date.month, 1) - timedelta(days=3)
                injected["cross_period_settlement_id"] = settlement_id
            else:
                order_date = settlement_date - timedelta(days=random.randint(1, 2))

            gross = rand_amount()
            mdr = round(gross * MDR_RATE, 2)

            # inject: MDR rate mismatch (charged at wrong rate for this batch)
            if i == mdr_mismatch_idx:
                mdr = round(gross * (MDR_RATE + 0.005), 2)  # overcharged by 0.5%
                injected["mdr_rate_mismatch_settlement_id"] = settlement_id

            gst = round(mdr * GST_RATE, 2)
            refund = rand_amount(0, gross * 0.1) if random.random() < 0.12 else 0.0
            chargeback = rand_amount(0, gross * 0.2) if random.random() < 0.06 else 0.0

            batch_gross += gross
            batch_mdr += mdr
            batch_gst += gst
            batch_refund += refund
            batch_chargeback += chargeback

            settlement_rows.append({
                "settlement_id": settlement_id,
                "order_id": order_id,
                "payment_id": payment_id,
                "order_date": order_date.isoformat(),
                "settlement_date": settlement_date.isoformat(),
                "gross_amount": gross,
                "mdr_fee": mdr,
                "gst_on_mdr": gst,
                "refund_amount": refund,
                "chargeback_amount": chargeback,
            })

            ledger_rows.append({
                "order_id": order_id,
                "order_date": order_date.isoformat(),
                "invoice_amount": gross,
                "customer_ref": f"CUST{random.randint(1000,9999)}",
                "gst_period": f"{order_date.year}-{order_date.month:02d}",
            })

        reserve_hold = round(batch_gross * RESERVE_RATE, 2)
        release_due_date = settlement_date + timedelta(days=RESERVE_WINDOW_DAYS)

        # inject: reserve held but not actually released even after the window
        reserve_released = 0.0 if i == reserve_stuck_idx else reserve_hold
        if i == reserve_stuck_idx:
            injected["reserve_not_released_settlement_id"] = settlement_id

        net_amount = round(
            batch_gross - batch_mdr - batch_gst - batch_refund
            - batch_chargeback - reserve_hold + reserve_released,
            2,
        )

        # inject: unexplained deduction not attributable to any known field
        unexplained = 0.0
        if i == unexplained_idx:
            unexplained = rand_amount(200, 2000)
            net_amount = round(net_amount - unexplained, 2)
            injected["unexplained_deduction_settlement_id"] = settlement_id

        utr = make_utr()
        if i == missing_utr_idx:
            utr = ""
            injected["missing_utr_settlement_id"] = settlement_id

        reserve_rows.append({
            "settlement_id": settlement_id,
            "settlement_date": settlement_date.isoformat(),
            "reserve_hold_amount": reserve_hold,
            "reserve_released_amount": reserve_released,
            "release_due_date": release_due_date.isoformat(),
        })

        bank_rows.append({
            "date": (settlement_date + timedelta(days=2)).isoformat(),
            "narration": f"NEFT CR RAZORPAY SETTLEMENT {settlement_id[-8:]}",
            "utr": utr,
            "credit_amount": net_amount,
            "settlement_id_hint": settlement_id,  # not present in real bank data; kept for grading only
        })

        # accumulate monthly GST invoice totals
        period_key = (settlement_date.year, settlement_date.month)
        acc = invoice_rows.setdefault(period_key, {"mdr": 0.0, "gst": 0.0})
        acc["mdr"] += batch_mdr
        acc["gst"] += batch_gst

    # build GST invoice rows, injecting one period mismatch
    invoice_out = []
    mismatch_period_idx = gst_mismatch_idx % max(len(invoice_rows), 1)
    for j, ((yr, mo), totals) in enumerate(sorted(invoice_rows.items())):
        gst_amount = round(totals["gst"], 2)
        if j == mismatch_period_idx:
            gst_amount = round(gst_amount * 0.9, 2)  # invoice under-reports GST by 10%
            injected["gst_invoice_mismatch_period"] = f"{yr}-{mo:02d}"
        invoice_out.append({
            "invoice_number": f"INV-{yr}{mo:02d}-{random.randint(1000,9999)}",
            "period": f"{yr}-{mo:02d}",
            "total_mdr_amount": round(totals["mdr"], 2),
            "gst_on_mdr_amount": gst_amount,
            "invoice_date": date(yr, mo, 28).isoformat(),
        })

    return (
        pd.DataFrame(settlement_rows),
        pd.DataFrame(bank_rows),
        pd.DataFrame(invoice_out),
        pd.DataFrame(ledger_rows),
        pd.DataFrame(reserve_rows),
        injected,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--batches", type=int, default=18)
    parser.add_argument("--out", type=str, default="../data")
    args = parser.parse_args()

    out_dir = Path(__file__).parent / args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    settlement_df, bank_df, invoice_df, ledger_df, reserve_df, injected = generate(
        seed=args.seed, n_batches=args.batches
    )

    settlement_df.to_csv(out_dir / "settlement_report.csv", index=False)
    bank_df.drop(columns=["settlement_id_hint"]).to_csv(
        out_dir / "bank_statement.csv", index=False
    )
    # keep a grading-only version with the hint column, for pipeline self-check
    bank_df.to_csv(out_dir / "bank_statement_with_ground_truth.csv", index=False)
    invoice_df.to_csv(out_dir / "gst_invoice.csv", index=False)
    ledger_df.to_csv(out_dir / "sales_ledger.csv", index=False)
    reserve_df.to_csv(out_dir / "reserve_ledger.csv", index=False)

    with open(out_dir / "injected_exceptions.json", "w") as f:
        json.dump(injected, f, indent=2)

    print(f"Generated {len(settlement_df)} order-level settlement rows across {args.batches} batches")
    print(f"Bank statement rows: {len(bank_df)}")
    print(f"GST invoice periods: {len(invoice_df)}")
    print(f"Sales ledger rows: {len(ledger_df)}")
    print(f"Reserve ledger rows: {len(reserve_df)}")
    print(f"\nInjected exceptions (ground truth) written to injected_exceptions.json:")
    print(json.dumps(injected, indent=2))


if __name__ == "__main__":
    main()

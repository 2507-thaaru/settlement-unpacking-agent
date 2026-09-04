"""
Pass 5 (STRETCH — only build this after Passes 1-4 are solid and tested)

Cross-period settlement flagging.

OBJECTIVE
    Flag any order whose order_date and settlement_date fall in different
    calendar months (a proxy for different GST filing periods), since
    revenue may be booked in a different period than it's collected,
    risking a GSTR-1 vs GSTR-3B vs ledger mismatch.

LOGIC
    For each row in settlement_df, parse order_date and settlement_date.
    If order_date.strftime("%Y-%m") != settlement_date.strftime("%Y-%m"),
    raise CROSS_PERIOD_SETTLEMENT for that order, noting both periods.

EXCEPTIONS TO DETECT
    - CROSS_PERIOD_SETTLEMENT: order_date and settlement_date in different
      months.

METRICS TO RETURN
    - "orders_checked": int
    - "cross_period_orders": int

TEST CONTRACT
    tests/test_pass5_cross_period.py checks that every order under the
    known cross_period_settlement_id is flagged.
"""

import pandas as pd
from src.schemas import DataContext, PassResult, Exception_, ExceptionCategory


def run(ctx: DataContext) -> PassResult:
    settlement_df = ctx.settlement_df
    exceptions = []

    orders_checked = len(settlement_df)
    cross_period_orders = 0

    for _, row in settlement_df.iterrows():
        order_date_str = str(row["order_date"])[:7]
        settlement_date_str = str(row["settlement_date"])[:7]

        if order_date_str != settlement_date_str:
            cross_period_orders += 1
            exceptions.append(
                Exception_(
                    settlement_id=row["settlement_id"],
                    category=ExceptionCategory.CROSS_PERIOD_SETTLEMENT,
                    description=(
                        f"Cross-period settlement: order date {row['order_date']} "
                        f"({order_date_str}) vs settlement date {row['settlement_date']} "
                        f"({settlement_date_str})"
                    ),
                    order_id=row["order_id"],
                    amount=row["gross_amount"]
                )
            )

    return PassResult(
        pass_name="pass5_cross_period",
        exceptions=exceptions,
        metrics={
            "orders_checked": orders_checked,
            "cross_period_orders": cross_period_orders,
        },
    )

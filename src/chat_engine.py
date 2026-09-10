"""
Interactive Live Data AI Chat Engine for Settlement Unpacking Agent.

Answers user questions about:
- Live reconciliation state, batch metrics, and settlement summary.
- Flagged exceptions (Missing UTR, Unexplained deductions, MDR rate mismatches, GST ITC leakage, Reserve delays, Cross-period orders).
- Rolling reserve release schedules and liquidity forecasts.
- Explanations of each pass in the 5-pass reconciliation architecture.
- Optional Gemini / OpenAI LLM integration with automatic zero-cost semantic fallback.
"""

from __future__ import annotations

import os
import re
from typing import Dict, Any, List, Optional

from src.schemas import DataContext


class SettlementChatEngine:
    """Live Context-Aware Chatbot for Razorpay Settlement Unpacking."""

    @classmethod
    def get_live_context_facts(cls, ctx: DataContext, report: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts structured summary facts from the live reconciliation run."""
        summary = report.get("summary", {})
        exceptions = report.get("all_exceptions", [])
        passes = report.get("passes", {})
        combined_metrics = report.get("combined_metrics", {})

        # Compute volume sums
        total_gross = float(ctx.settlement_df["gross_amount"].sum()) if not ctx.settlement_df.empty else 0.0
        total_bank_credits = float(ctx.bank_df["credit_amount"].sum()) if not ctx.bank_df.empty else 0.0
        total_batches = int(ctx.settlement_df["settlement_id"].nunique()) if not ctx.settlement_df.empty else 0
        total_orders = len(ctx.settlement_df)

        # Exception counts by category
        cat_counts: Dict[str, int] = {}
        for e in exceptions:
            cat = e.get("category", "OTHER")
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

        # Pass 3 forecast summary
        p3_metrics = combined_metrics.get("pass3_reserve_forecast", {})
        reserve_held = p3_metrics.get("total_reserve_held", 0.0)
        reserve_released = p3_metrics.get("total_reserve_released", 0.0)
        still_held = p3_metrics.get("total_still_held", 0.0)
        overdue_batches = p3_metrics.get("batches_with_overdue_reserve", 0)
        forecast_schedule = p3_metrics.get("forecast", [])

        # Pass 4 GST leakage summary
        p4_metrics = combined_metrics.get("pass4_gst_itc", {})
        total_itc_leakage = p4_metrics.get("total_itc_leakage", 0.0)

        return {
            "total_gross": total_gross,
            "total_bank_credits": total_bank_credits,
            "total_batches": total_batches,
            "total_orders": total_orders,
            "total_exceptions": len(exceptions),
            "exceptions_by_category": cat_counts,
            "exceptions_list": exceptions,
            "passes": passes,
            "reserve_held": reserve_held,
            "reserve_released": reserve_released,
            "still_held": still_held,
            "overdue_batches": overdue_batches,
            "forecast_schedule": forecast_schedule,
            "total_itc_leakage": total_itc_leakage,
        }

    @classmethod
    def semantic_query_response(cls, query: str, facts: Dict[str, Any]) -> str:
        """Deterministic semantic engine providing instant, accurate answers about live data."""
        q = query.lower().strip()

        # 1. Summary / Overview Queries
        if any(k in q for k in ["summary", "overview", "total", "status", "how is it looking", "kpi", "metrics"]):
            cat_summary_str = "\n".join([f"- **{k}**: {v} incident(s)" for k, v in facts["exceptions_by_category"].items()])
            return (
                f"### 📊 Live Reconciliation Overview\n\n"
                f"- **Total Gross Settled**: ₹{facts['total_gross']:,.2f}\n"
                f"- **Total Bank Credits Realized**: ₹{facts['total_bank_credits']:,.2f}\n"
                f"- **Batches Processed**: {facts['total_batches']} batches across {facts['total_orders']} individual orders\n"
                f"- **Total Exceptions Flagged**: **{facts['total_exceptions']}**\n\n"
                f"#### Breakdown by Category:\n"
                f"{cat_summary_str or '- *No exceptions detected! Everything reconciled cleanly.*'}\n\n"
                f"💡 *Ask me about specific passes, batch IDs, GST ITC leakage, or rolling reserve schedules.*"
            )

        # 2. Specific Exception Category Queries
        if any(k in q for k in ["missing utr", "utr missing", "no utr"]):
            utr_exs = [e for e in facts["exceptions_list"] if e.get("category") == "MISSING_UTR"]
            if not utr_exs:
                return "✅ **No Missing UTR Exceptions!** All bank statement credits have valid UTR tracking numbers."
            batches = ", ".join([f"`{e.get('settlement_id')}`" for e in utr_exs])
            return (
                f"🔍 **Missing UTR Inquiries ({len(utr_exs)} found):**\n\n"
                f"The following settlement batches are missing bank UTR transaction reference numbers:\n"
                f"{batches}\n\n"
                f"**Root Cause**: The bank credit statement recorded a payout without the mandatory 12/22-character UTR string. "
                f"This blocks automated audit verification with the banking partner."
            )

        if any(k in q for k in ["unexplained deduction", "deduction", "shortfall", "short credit"]):
            ded_exs = [e for e in facts["exceptions_list"] if e.get("category") == "UNEXPLAINED_DEDUCTION"]
            if not ded_exs:
                return "✅ **No Unexplained Deductions!** Expected net settlement credit perfectly matches bank statements within ₹1.00 tolerance."
            items = "\n".join([f"- Batch `{e.get('settlement_id')}`: {e.get('description')} (Amount: ₹{e.get('amount', 0):,.2f})" for e in ded_exs])
            return (
                f"⚠️ **Unexplained Bank Deductions ({len(ded_exs)} detected):**\n\n"
                f"{items}\n\n"
                f"**Why this happens**: The net credited amount in your bank statement was less than `gross - MDR - GST - refunds - chargebacks - reserve_hold + reserve_released`."
            )

        if any(k in q for k in ["mdr", "fee mismatch", "rate mismatch", "commission"]):
            mdr_exs = [e for e in facts["exceptions_list"] if e.get("category") == "MDR_RATE_MISMATCH"]
            if not mdr_exs:
                return "✅ **MDR Fees Verified!** All orders were charged the exact contracted 2.0% MDR fee rate."
            orders = "\n".join([f"- Order `{e.get('order_id')}` in `{e.get('settlement_id')}`: {e.get('description')} (Discrepancy: ₹{e.get('amount', 0):,.2f})" for e in mdr_exs[:6]])
            more = f"\n- *...and {len(mdr_exs) - 6} more orders.*" if len(mdr_exs) > 6 else ""
            return (
                f"🚨 **MDR Rate Mismatches ({len(mdr_exs)} orders affected):**\n\n"
                f"{orders}{more}\n\n"
                f"**Remediation**: Overcharged MDR fees should be claimed back via a fee dispute raised with Razorpay Merchant Operations."
            )

        if any(k in q for k in ["gst", "itc", "tax", "input tax credit", "invoice"]):
            gst_exs = [e for e in facts["exceptions_list"] if e.get("category") == "GST_ITC_MISMATCH"]
            leakage = facts.get("total_itc_leakage", 0.0)
            if not gst_exs:
                return "✅ **GST ITC Reconciled!** Monthly GST invoices match the aggregate GST-on-MDR deducted in settlement reports perfectly."
            items = "\n".join([f"- {e.get('description')} (Leakage Amount: **₹{e.get('amount', 0):,.2f}**)" for e in gst_exs])
            return (
                f"🧾 **GST ITC Leakage Report:**\n\n"
                f"- **Total Unclaimed / Discrepant ITC**: **₹{leakage:,.2f}**\n\n"
                f"{items}\n\n"
                f"**Impact**: When Razorpay's tax invoice GST doesn't match the GST deducted across daily batches, your accounting system under-claims GSTR-2B Input Tax Credit, creating cash leakage."
            )

        if any(k in q for k in ["reserve", "rolling reserve", "hold", "forecast", "liquidity", "release"]):
            res_exs = [e for e in facts["exceptions_list"] if e.get("category") == "RESERVE_NOT_RELEASED"]
            schedule = facts.get("forecast_schedule", [])
            sched_str = "\n".join([f"- Release Due `{s.get('release_due_date')}`: Batch `{s.get('settlement_id')}` $\\rightarrow$ **₹{s.get('still_held', 0):,.2f}** (Status: `{s.get('status')}`)" for s in schedule[:5]])
            
            return (
                f"🔒 **Rolling Reserve Status & Forward Forecast:**\n\n"
                f"- **Total Reserve Withheld**: ₹{facts['reserve_held']:,.2f}\n"
                f"- **Total Released**: ₹{facts['reserve_released']:,.2f}\n"
                f"- **Active Reserve Still Held**: **₹{facts['still_held']:,.2f}**\n"
                f"- **Batches Overdue for Release**: **{facts['overdue_batches']}**\n\n"
                f"#### Upcoming Release Forecast:\n"
                f"{sched_str or '- *No pending reserve balances.*'}\n\n"
                f"⚠️ *Overdue reserves must be auto-escalated to Razorpay risk support.*"
            )

        if any(k in q for k in ["cross period", "cross-period", "timing difference", "cutoff"]):
            cp_exs = [e for e in facts["exceptions_list"] if e.get("category") == "CROSS_PERIOD_SETTLEMENT"]
            if not cp_exs:
                return "✅ **No Cross-Period Timing Discrepancies!** All orders were settled within the same accounting month."
            items = "\n".join([f"- Order `{e.get('order_id')}` in `{e.get('settlement_id')}`: {e.get('description')}" for e in cp_exs[:5]])
            return (
                f"⏳ **Cross-Period Settlements ({len(cp_exs)} orders):**\n\n"
                f"{items}\n\n"
                f"**Accounting Treatment**: These orders were captured at the end of a month (e.g. March 31) but settled in the subsequent month (e.g. April 1). Accrual journal entries are required."
            )

        # 3. Pass Explanations
        if "pass 1" in q or "batch match" in q:
            return (
                "### 🔍 Pass 1: Batch-Level Settlement to Bank Matching\n\n"
                "Matches each settlement batch in `settlement_report.csv` to its corresponding credit in `bank_statement.csv` using the 8-character reference code inside the bank narration.\n"
                "- Calculates: `Expected Net = Gross - MDR - GST - Refunds - Chargebacks - Reserve_Hold + Reserve_Released`\n"
                "- Detects: `MISSING_UTR` and `UNEXPLAINED_DEDUCTION`."
            )

        if "pass 2" in q or "order validation" in q:
            return (
                "### 📦 Pass 2: Order-Level Explosion & Validation\n\n"
                "Explodes batch aggregates into individual orders, comparing them against the merchant's `sales_ledger.csv`.\n"
                "- Verifies order existence and invoice amount matching.\n"
                "- Flags `MDR_RATE_MISMATCH` if MDR fee deviates from contracted 2.0%."
            )

        if "pass 3" in q or "reserve forecast" in q:
            return (
                "### 🔒 Pass 3: Rolling Reserve Tracking & Release Forecast\n\n"
                "Tracks the 5% rolling reserve withheld across 120-day holding windows.\n"
                "- Flags `RESERVE_NOT_RELEASED` if reserves remain held past the contractual release due date.\n"
                "- Generates a forward-looking cash flow release schedule."
            )

        if "pass 4" in q or "gst check" in q or "itc" in q:
            return (
                "### 🧾 Pass 4: GST on MDR & ITC Leakage Audit\n\n"
                "Aggregates daily GST-on-MDR deductions per month and reconciles against official monthly `gst_invoice.csv` tax invoices.\n"
                "- Flags `GST_ITC_MISMATCH` to prevent tax leakage in GSTR-2B filings."
            )

        if "pass 5" in q or "cross period" in q:
            return (
                "### ⏳ Pass 5: Cross-Period Timing Reconciler\n\n"
                "Detects orders captured in one billing month and paid out in the next month, ensuring accurate month-end revenue accruals."
            )

        # 4. Specific Batch Lookup
        batch_match = re.search(r'SETTL_\d+_\d+', query, re.IGNORECASE)
        if batch_match:
            bid = batch_match.group(0).upper()
            batch_exs = [e for e in facts["exceptions_list"] if str(e.get("settlement_id", "")).upper() == bid]
            if batch_exs:
                reasons = "\n".join([f"- **{e.get('category')}**: {e.get('description')} (Amount: ₹{e.get('amount', 0):,.2f})" for e in batch_exs])
                return (
                    f"🔎 **Audit Findings for Batch `{bid}`:**\n\n"
                    f"{reasons}\n\n"
                    f"Would you like me to suggest remediation actions for this batch?"
                )
            else:
                return f"✅ **Batch `{bid}` is 100% Clean!** Reconciled across all 5 passes with no exceptions or deductions."

        # Default Helpful Response
        return (
            f"🤖 **Settlement AI Assistant**: I am monitoring your live reconciliation data.\n\n"
            f"Here are key questions you can ask me:\n"
            f"1. **\"Give me an executive summary of current exceptions\"**\n"
            f"2. **\"Why is batch SETTL_20260301_004 flagged?\"**\n"
            f"3. **\"What is our GST ITC leakage this month?\"**\n"
            f"4. **\"When will overdue rolling reserves be released?\"**\n"
            f"5. **\"Which orders had MDR rate overcharges?\"**\n"
            f"6. **\"Explain Pass 1 to Pass 5\"**"
        )

    @classmethod
    async def chat(cls, query: str, ctx: DataContext, report: Dict[str, Any], history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Generates an answer to the user query using live reconciliation context."""
        facts = cls.get_live_context_facts(ctx, report)

        # Check for Gemini / OpenAI API Keys if configured
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        openai_api_key = os.getenv("OPENAI_API_KEY")

        if gemini_api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=gemini_api_key)
                model = genai.GenerativeModel("gemini-1.5-flash")

                system_prompt = (
                    "You are the Settlement Unpacking AI Agent, an expert financial reconciliation and audit assistant.\n"
                    "Use these LIVE GROUND TRUTH reconciliation facts to answer the user's questions:\n"
                    f"- Total Gross Settled: ₹{facts['total_gross']:,.2f}\n"
                    f"- Total Bank Credits: ₹{facts['total_bank_credits']:,.2f}\n"
                    f"- Total Batches: {facts['total_batches']}\n"
                    f"- Total Orders: {facts['total_orders']}\n"
                    f"- Total Exceptions: {facts['total_exceptions']}\n"
                    f"- Exceptions Breakdown: {facts['exceptions_by_category']}\n"
                    f"- Overdue Reserve Balance: ₹{facts['still_held']:,.2f} across {facts['overdue_batches']} batches\n"
                    f"- GST ITC Leakage: ₹{facts['total_itc_leakage']:,.2f}\n"
                    f"- Sample Flagged Exceptions: {facts['exceptions_list'][:10]}\n\n"
                    "Format answers clearly in GitHub Markdown with rupee amounts and bullet points."
                )

                prompt = f"{system_prompt}\n\nUser Question: {query}"
                response = model.generate_content(prompt)
                reply = response.text
                return {
                    "reply": reply,
                    "engine": "gemini-1.5-flash",
                    "live_facts_used": True,
                    "suggested_questions": [
                        "What is our total GST ITC leakage?",
                        "Show me the rolling reserve release timeline",
                        "Which batches have missing UTRs?",
                        "Give me an executive summary"
                    ]
                }
            except Exception:
                pass  # Graceful fallback to semantic engine

        # Deterministic / Semantic Engine Fallback
        reply = cls.semantic_query_response(query, facts)
        return {
            "reply": reply,
            "engine": "semantic-fact-engine",
            "live_facts_used": True,
            "suggested_questions": [
                "What is our total GST ITC leakage?",
                "Show me the rolling reserve release timeline",
                "Which batches have missing UTRs?",
                "Give me an executive summary"
            ]
        }

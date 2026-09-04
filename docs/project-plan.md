# Settlement Unpacking Agent — Project Plan
**Razorpay AI Buildathon 2026 — Track 4: AI Finance Controller**

---

## 1. Problem Statement

A Razorpay T+2 settlement lands in a merchant's bank account as a single lumped NEFT credit covering hundreds of individual orders, net of MDR (typically 2%), 18% GST on that MDR, refund/chargeback deductions, and rolling-reserve movements. Without exploding that lump sum back into its components, a finance team cannot:

- Post revenue and expense to the correct ledger accounts
- Claim Input Tax Credit (ITC) on the GST charged on MDR
- Know how much cash is actually locked in rolling reserve, or when it becomes available
- Catch settlements that straddle a GST filing period and create a GSTR-1 vs GSTR-3B mismatch

Existing reconciliation tools (HighRadius, Puzzle, ChatFin, Rillet, Cryptoworth) solve generic bank-to-ledger matching at enterprise scale, but none treat rolling-reserve release forecasting and GST-on-MDR ITC leakage as first-class outputs of the same settlement-batch explosion. That combination — narrow, India-specific, and provable on a small synthetic batch — is the gap this project targets.

## 2. Why This Is Underserved

| Problem | How commonly solved today |
|---|---|
| Generic bank ↔ ledger reconciliation | Heavily solved (multiple enterprise SaaS tools) |
| Settlement batch explosion (settlement_id → order_id) | Partially solved, rarely built around Razorpay's specific field structure |
| Rolling reserve release forecasting | Treated as a footnote inside bigger suites, not a standalone forecast |
| GST-on-MDR ITC leakage detection | Manual, checklist-driven, described as error-prone in practitioner sources |
| Cross-period revenue recognition breakage | Named as a top cause of GST notices, but caught reactively, not by an agent |

## 3. Scope for the Buildathon Submission

**In scope (core loop):**
1. Settlement batch → bank credit matching
2. Batch explosion to order/payment level
3. Rolling reserve tracking and release-date forecasting
4. GST-on-MDR ITC leakage detection against the monthly tax invoice

**Stretch (if time allows):**
5. Cross-period settlement flagging (GST filing period boundary risk)

Explicitly out of scope: multi-gateway support (PayU, Cashfree), UPI RRN fragmentation across TPAPs, live API integration with Razorpay — all reasonable v2 directions, not needed to prove the core loop.

## 4. Data Sources (Synthetic, 50+ Records)

Four synthetic datasets, generated to mirror real Razorpay field formats:

1. **Settlement report** (CSV) — `settlement_id`, `order_id`, `payment_id`, gross amount, MDR, GST on MDR, refund deduction, chargeback deduction, reserve hold/release flag, net amount
2. **Bank statement** (CSV) — date, narration (`NEFT CR: [bank] [UTR] RAZORPAY SETTLEMENT`), UTR, credited amount
3. **Monthly GST tax invoice** (CSV/PDF-like) — invoice number, period, total MDR, GST on MDR charged
4. **Sales ledger / order records** — order_id, invoice amount, order date, customer reference

Deliberately inject realistic noise: missing UTRs, an MDR rate mismatch, one unexplained deduction, one GST invoice discrepancy, a reserve hold that isn't released within the batch window, and at least one settlement that straddles a month boundary.

## 5. Architecture — Multi-Pass Matching Pipeline

**Pass 1 — Batch-level match**
`settlement_id` ↔ bank NEFT credit via UTR + date + net amount. Confirms the lump sum arrived and anchors the batch.

**Pass 2 — Explosion pass**
Break each matched batch into its component `order_id`/`payment_id` rows; validate each against the sales ledger.

**Pass 3 — Reserve tracking pass**
Separate held vs released reserve amounts per batch. Apply the chargeback-liability window to project a release date and produce a forward cash-availability forecast.

**Pass 4 — GST-on-MDR ITC pass**
Cross-check the GST-on-MDR line in the settlement file against the actual monthly tax invoice; flag leakage that would block an ITC claim.

**Pass 5 (stretch) — Cross-period flag**
Detect settlements where the collection date and settlement date fall in different GST filing periods; flag as a revenue-recognition risk.

## 6. Outputs (the "honest exception list")

- Match rate: batch-level % and order-level %
- Categorized exceptions: missing UTR, MDR rate mismatch, GST-on-MDR mismatch vs invoice, unexplained deduction, unaccounted reserve movement, cross-period settlement
- Reserve release forecast: projected cash available, by date
- ITC leakage flagged: amount and source invoice(s)
- Unresolved exceptions: explicitly listed, not hidden

## 7. Tech Stack (proposed)

- **Data generation & matching logic:** Python, pandas
- **Fuzzy/narration matching:** rapidfuzz (for noisy bank narrations)
- **Exception explanation / root-cause summaries:** LLM call (Claude) over the categorized exception rows, not raw data — keeps the matching logic deterministic and auditable, LLM only narrates
- **Interface:** simple CLI or lightweight Streamlit dashboard showing match rate, exceptions, and reserve forecast
- **Repo:** public GitHub repo with README doubling as architecture documentation

## 8. Evaluation Metrics (for the submission)

- Match rate (%) at batch and order level
- Precision on exception categorization (spot-checked against known injected noise)
- ITC leakage detection recall (did it catch every injected GST mismatch)
- Reserve forecast accuracy against the synthetic release schedule
- Exceptions correctly left unresolved and listed (avoiding false "100% matched" claims)

## 9. Deliverables (per Razorpay's requirements)

- [ ] Public GitHub repository with working code
- [ ] Architecture documentation (this plan, refined into README)
- [ ] 5-minute pitch video (problem, approach, results)
- [ ] Demonstrated measurable results with an audit trail

## 10. Status

| Component | Status |
|---|---|
| Problem selection & scoping | Done |
| Synthetic dataset design | Planned |
| Pass 1–2 (batch match + explosion) | Planned |
| Pass 3 (reserve forecast) | Planned |
| Pass 4 (ITC leakage) | Planned |
| Pass 5 (cross-period, stretch) | Not started |
| Interface / dashboard | Planned |
| Pitch video | Not started |

## 11. Open Risks

- Synthetic data needs to look convincingly like real Razorpay settlement fields — worth cross-checking field names against actual Razorpay dashboard exports if a sample is available
- Reserve-release forecasting requires assuming a chargeback-liability window (120 days is the common industry figure) — should be stated as an assumption, not presented as Razorpay's actual policy
- Scope creep risk: five passes is ambitious for a hackathon timeline — Pass 5 should stay stretch-only until 1–4 are solid

import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";

import { Hero } from "@/components/ui/hero-1";
import { ThemeToggle } from "@/components/theme-toggle";
import { UploadPanel } from "@/components/upload-panel";
import { summaryQuery } from "@/lib/api";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Settlement Unpacking Agent — Explode Razorpay settlements into ledger truth" },
      {
        name: "description",
        content:
          "Unpack lumped Razorpay T+2 settlement credits into orders, MDR, GST, refunds and rolling reserve — with live exception detection and reserve release forecasting.",
      },
      {
        property: "og:title",
        content: "Settlement Unpacking Agent — Razorpay settlement reconciliation",
      },
      {
        property: "og:description",
        content:
          "Five reconciliation passes over one settlement batch: batch match, order validation, reserve forecast, GST ITC check, cross-period flag.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Landing,
});

const PASSES = [
  { n: "01", name: "Batch match", detail: "Settlement ↔ bank credit, full amount reconciliation" },
  { n: "02", name: "Order validation", detail: "Explode to order level, catch MDR rate errors" },
  { n: "03", name: "Reserve forecast", detail: "Track held vs released, project release dates" },
  { n: "04", name: "GST ITC check", detail: "Catch tax-invoice mismatches that would kill a claim" },
  { n: "05", name: "Cross-period flag", detail: "Catch settlements straddling a GST filing period" },
];

function Landing() {
  const { data } = useQuery(summaryQuery());

  const stats = [
    { label: "Passes implemented", value: data ? `${data.passes_implemented} / ${data.passes_total}` : "—" },
    { label: "Exceptions found", value: data ? String(data.total_exceptions_found) : "—" },
    { label: "Settlement batches", value: data ? String(data.total_batches) : "—" },
    { label: "Orders processed", value: data ? String(data.total_orders) : "—" },
  ];

  return (
    <div className="relative min-h-screen bg-background">
      <header className="absolute inset-x-0 top-0 z-20 flex items-center justify-between px-6 py-5">
        <span className="font-display text-sm font-semibold tracking-tight text-foreground">
          Settlement Unpacking Agent
        </span>
        <div className="flex items-center gap-2">
          <Link
            to="/dashboard"
            className="rounded-full border border-border px-4 py-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
          >
            Open dashboard
          </Link>
          <ThemeToggle />
        </div>
      </header>

      <Hero
        eyebrow=""
        title="Explode a lumped settlement into ledger truth"
        subtitle="One NEFT credit hides hundreds of orders, MDR, GST on MDR, refunds, chargebacks and rolling reserve. This agent unpacks the lump sum, reconciles it order by order, and surfaces every exception worth money."
        ctaLabel="See the results"
        ctaTo="/dashboard"
        secondary={
          <Link
            to="/how-it-works"
            className="rounded-full border border-border px-7 py-3 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            How it works
          </Link>
        }
      />

      <section className="mx-auto max-w-6xl px-6 pb-24">
        <div className="mb-6">
          <UploadPanel />
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          <article className="panel p-7">
            <h2 className="text-xl font-semibold text-foreground">The problem</h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              A Razorpay T+2 settlement lands as a single lumped NEFT credit covering hundreds of
              orders — netted against MDR, GST on that MDR, refunds, chargebacks, and rolling
              reserve movements. Without exploding that lump sum back into its parts, a finance team
              can&apos;t post accurate ledger entries, claim the GST Input Tax Credit they&apos;re
              owed, know how much cash is actually locked in reserve, or catch revenue booked in the
              wrong GST filing period.
            </p>
          </article>

          <article className="panel p-7">
            <h2 className="text-xl font-semibold text-foreground">Why it&apos;s underserved</h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              Generic reconciliation tools solve bank-to-ledger matching at enterprise scale. Almost
              none of them treat{" "}
              <strong className="text-foreground">rolling-reserve release forecasting</strong> and{" "}
              <strong className="text-foreground">GST-on-MDR ITC leakage detection</strong> as
              first-class outputs of the same settlement-batch explosion — and none are built around
              India&apos;s MDR / GST / TDS / reserve stack specifically.
            </p>
          </article>
        </div>

        <div className="panel mt-6 p-7">
          <h2 className="text-xl font-semibold text-foreground">What this agent does</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            One pipeline, five passes, each closing a different finance-ops loop on the same exploded
            batch data.
          </p>
          <ol className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {PASSES.map((p) => (
              <li key={p.n} className="rounded-lg border border-border bg-background/40 p-4">
                <span className="font-mono text-xs text-primary">{p.n}</span>
                <p className="mt-1 text-sm font-medium text-foreground">{p.name}</p>
                <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{p.detail}</p>
              </li>
            ))}
          </ol>
          <p className="mt-6 text-xs text-muted-foreground">
            Every finding is measured against a known, honest exception list — not a cherry-picked
            demo match.
          </p>
        </div>

        <div className="mt-14">
          <h2 className="text-xs font-medium tracking-[0.2em] text-muted-foreground uppercase">
            Current run, at a glance
          </h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {stats.map((s) => (
              <div key={s.label} className="panel p-6">
                <p className="text-[11px] tracking-[0.16em] text-muted-foreground uppercase">
                  {s.label}
                </p>
                <p className="mt-3 font-display text-3xl font-semibold text-foreground">{s.value}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

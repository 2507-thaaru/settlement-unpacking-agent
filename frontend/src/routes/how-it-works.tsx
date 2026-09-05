import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";

import { AppShell, SectionHeading, StateCard } from "@/components/app-shell";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { KnowledgeGraph } from "@/components/knowledge-graph";
import { graphQuery } from "@/lib/api";


export const Route = createFileRoute("/how-it-works")({
  head: () => ({
    meta: [
      { title: "How It Works — Settlement Unpacking Agent" },
      {
        name: "description",
        content:
          "The five reconciliation passes explained: batch match, order validation, reserve forecast, GST ITC check and cross-period flagging, with the maths behind each.",
      },
      { property: "og:title", content: "How It Works — Settlement Unpacking Agent" },
      {
        property: "og:description",
        content: "Source files, five passes, exceptions and orchestration — end to end.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: HowItWorks,
});

const MATH: { title: string; body: string }[] = [
  {
    title: "Pass 1 — Batch match",
    body: "settlement_amount = gross_sales − refunds − chargebacks − MDR − GST_on_MDR − reserve_held + reserve_released. The computed net must equal the bank credit for that UTR. Any credit without a matching UTR, or a delta beyond rounding tolerance, is an exception.",
  },
  {
    title: "Pass 2 — Order validation",
    body: "For each order: expected_MDR = order_amount × contracted_rate, and expected_GST = expected_MDR × 18%. Where the charged MDR deviates from the contracted rate, the difference is an MDR_RATE_MISMATCH; unexplained residue after all known deductions is an UNEXPLAINED_DEDUCTION.",
  },
  {
    title: "Pass 3 — Reserve forecast",
    body: "still_held = reserve_held − reserve_released per batch, with release_due_date = settlement_date + reserve_period. Batches past their due date with a non-zero balance are flagged RESERVE_NOT_RELEASED and the rest form the forward release schedule.",
  },
  {
    title: "Pass 4 — GST ITC check",
    body: "GST on MDR is claimable input tax credit only when a matching tax invoice exists with the same taxable value. Invoice GST vs settlement GST_on_MDR is compared line by line; any gap is a GST_ITC_MISMATCH — real, unclaimed money.",
  },
  {
    title: "Pass 5 — Cross-period flag",
    body: "When the transaction date and the settlement date fall in different GST filing months, revenue and ITC land in different returns. Those batches are flagged CROSS_PERIOD_SETTLEMENT so the ledger entry can be split correctly.",
  },
];

function HowItWorks() {
  const graph = useQuery(graphQuery());

  const loading = graph.isLoading;
  const error = graph.error;

  return (
    <AppShell
      title="How It Works"
      description="Data flow, and exactly how each number is calculated — from the current run"
    >
      <SectionHeading>Knowledge graph</SectionHeading>
      {loading ? (
        <StateCard>Building the graph from the current run…</StateCard>
      ) : error ? (
        <StateCard>Could not reach the pipeline API: {(error as Error).message}</StateCard>
      ) : (
        <KnowledgeGraph graph={graph.data ?? { nodes: [], edges: [] }} />
      )}


      <div className="mt-10">
        <SectionHeading>The maths behind each pass</SectionHeading>
        <Accordion type="single" collapsible className="space-y-3">
          {MATH.map((m) => (
            <AccordionItem
              key={m.title}
              value={m.title}
              className="panel overflow-hidden rounded-xl border border-border bg-background/50 px-5 transition-colors duration-200 hover:bg-muted/60 data-[state=open]:bg-muted/80 data-[state=open]:border-foreground/20"
            >
              <AccordionTrigger className="text-sm font-medium text-foreground hover:no-underline [&[data-state=open]>svg]:text-foreground">
                {m.title}
              </AccordionTrigger>
              <AccordionContent>
                <p className="text-sm leading-relaxed text-muted-foreground">{m.body}</p>
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </AppShell>
  );
}

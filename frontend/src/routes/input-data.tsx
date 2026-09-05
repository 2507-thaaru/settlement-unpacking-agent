import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { AppShell, StateCard } from "@/components/app-shell";
import { datasetQuery, datasetsQuery } from "@/lib/api";

export const Route = createFileRoute("/input-data")({
  head: () => ({
    meta: [
      { title: "Input Data — Settlement Unpacking Agent" },
      {
        name: "description",
        content:
          "Explore the five source files the pipeline reads: settlement report, bank statement, GST invoice, sales ledger and reserve ledger.",
      },
      { property: "og:title", content: "Input Data — Settlement Unpacking Agent" },
      {
        property: "og:description",
        content: "Raw data explorer for every source file behind the reconciliation run.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: InputData,
});

function InputData() {
  const datasets = useQuery(datasetsQuery());
  const [active, setActive] = useState<string | null>(null);
  const list = datasets.data?.datasets ?? [];
  const current = active ?? list[0]?.name ?? null;
  const rows = useQuery({ ...datasetQuery(current ?? ""), enabled: Boolean(current) });

  return (
    <AppShell title="Input Data" description="The five source files every pass reads from">
      {datasets.isError && <StateCard>Could not reach the pipeline API.</StateCard>}

      <div className="flex flex-wrap gap-2">
        {list.map((d) => (
          <button
            key={d.name}
            type="button"
            onClick={() => setActive(d.name)}
            className={`rounded-full border px-4 py-1.5 text-xs transition-colors ${
              d.name === current
                ? "border-primary bg-primary/10 text-foreground"
                : "border-border text-muted-foreground hover:text-foreground"
            }`}
          >
            {d.name.replace(/_/g, " ")}
            <span className="ml-2 font-mono text-[10px] text-muted-foreground">{d.rows}</span>
          </button>
        ))}
        {datasets.isLoading &&
          Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-8 w-36 animate-pulse rounded-full bg-muted" />
          ))}
      </div>

      {current && (
        <div className="panel mt-6 overflow-hidden">
          <div className="border-b border-border px-6 py-4">
            <h2 className="text-base font-semibold text-foreground">
              {current.replace(/_/g, " ")}
            </h2>
            <p className="mt-1 text-xs text-muted-foreground">
              {list.find((d) => d.name === current)?.description} ·{" "}
              {rows.data ? `${rows.data.total_rows} rows` : "loading"}
            </p>
          </div>

          <div className="max-h-[560px] overflow-auto">
            {rows.isLoading && <div className="p-6 text-sm text-muted-foreground">Loading rows…</div>}
            {rows.data && <DataTable records={rows.data.records} />}
          </div>
        </div>
      )}
    </AppShell>
  );
}

function DataTable({ records }: { records: Record<string, string | number | null>[] }) {
  if (records.length === 0) return <div className="p-6 text-sm text-muted-foreground">No rows.</div>;
  const columns = Object.keys(records[0] ?? {});

  return (
    <table className="w-full border-collapse text-left text-xs">
      <thead className="sticky top-0 bg-card">
        <tr>
          {columns.map((c) => (
            <th
              key={c}
              className="border-b border-border px-4 py-3 font-medium tracking-wide text-muted-foreground whitespace-nowrap"
            >
              {c}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {records.map((r, i) => (
          <tr key={i} className="hover:bg-accent/40">
            {columns.map((c) => (
              <td
                key={c}
                className="border-b border-border/60 px-4 py-2.5 font-mono text-foreground/90 whitespace-nowrap"
              >
                {r[c] === null || r[c] === "" ? (
                  <span className="text-muted-foreground">—</span>
                ) : (
                  String(r[c])
                )}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

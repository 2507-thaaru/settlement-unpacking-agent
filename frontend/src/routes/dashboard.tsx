import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { AppShell, SectionHeading, StateCard } from "@/components/app-shell";
import {
  exceptionsQuery,
  forecastQuery,
  formatINR,
  PASS_LABELS,
  passesQuery,
  summaryQuery,
} from "@/lib/api";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "Results Dashboard — Settlement Unpacking Agent" },
      {
        name: "description",
        content:
          "Live KPIs, pass status, reserve release forecast and the full exception register from the latest reconciliation run.",
      },
      { property: "og:title", content: "Results Dashboard — Settlement Unpacking Agent" },
      {
        property: "og:description",
        content: "Exceptions, reserve forecast and pass status from the live pipeline.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Dashboard,
});

function Dashboard() {
  const summary = useQuery(summaryQuery());
  const passes = useQuery(passesQuery());
  const forecast = useQuery(forecastQuery());
  const exceptions = useQuery(exceptionsQuery());

  const [category, setCategory] = useState("ALL");
  const [search, setSearch] = useState("");

  const rows = exceptions.data?.exceptions ?? [];
  const categories = useMemo(
    () => Array.from(new Set(rows.map((r) => r.category))).sort(),
    [rows],
  );

  const filtered = rows.filter((r) => {
    if (category !== "ALL" && r.category !== category) return false;
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return [r.settlement_id, r.order_id, r.description, r.category]
      .filter(Boolean)
      .some((v) => String(v).toLowerCase().includes(q));
  });

  const chartData = (forecast.data?.forecast_schedule ?? []).map((f) => ({
    name: f.settlement_id,
    date: f.release_due_date,
    amount: f.still_held,
  }));

  const kpis = [
    {
      label: "Passes implemented",
      value: summary.data ? `${summary.data.passes_implemented} / ${summary.data.passes_total}` : "—",
    },
    { label: "Exceptions found", value: summary.data?.total_exceptions_found ?? "—" },
    { label: "Settlement batches", value: summary.data?.total_batches ?? "—" },
    { label: "Orders processed", value: summary.data?.total_orders ?? "—" },
  ];

  return (
    <AppShell
      title="Results Dashboard"
      description="Live output of the latest reconciliation run"
    >
      {summary.isError && <StateCard>Could not reach the pipeline API.</StateCard>}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {kpis.map((k) => (
          <div key={k.label} className="panel p-6">
            <p className="text-[11px] tracking-[0.16em] text-muted-foreground uppercase">
              {k.label}
            </p>
            <p className="mt-3 font-display text-3xl font-semibold text-foreground">
              {String(k.value)}
            </p>
          </div>
        ))}
      </div>

      <div className="mt-10">
        <SectionHeading>Reconciliation passes</SectionHeading>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {(passes.data ?? []).map((p, i) => {
            const clean = p.exception_count === 0;
            return (
              <div key={p.pass_name} className="panel p-5">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <span className="font-mono text-xs text-primary">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <p className="mt-1 text-sm font-medium text-foreground">
                      {PASS_LABELS[p.pass_name] ?? p.pass_name.replace(/_/g, " ")}
                    </p>
                  </div>
                  <span
                    className={`rounded-full px-2.5 py-1 text-[10px] font-medium ${
                      clean
                        ? "bg-emerald-500/15 text-emerald-500"
                        : "bg-amber-500/15 text-amber-500"
                    }`}
                  >
                    {clean ? "clean" : `${p.exception_count} exceptions`}
                  </span>
                </div>
                {p.detail && (
                  <p className="mt-3 text-xs leading-relaxed text-muted-foreground">{p.detail}</p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="mt-10">
        <SectionHeading>Reserve release forecast</SectionHeading>
        <div className="panel p-6">
          <div className="grid gap-4 sm:grid-cols-4">
            {[
              { l: "Total held", v: forecast.data?.total_reserve_held },
              { l: "Released", v: forecast.data?.total_reserve_released },
              { l: "Still held", v: forecast.data?.total_still_held },
            ].map((s) => (
              <div key={s.l}>
                <p className="text-[11px] tracking-[0.16em] text-muted-foreground uppercase">
                  {s.l}
                </p>
                <p className="mt-1 font-mono text-lg text-foreground">{formatINR(s.v)}</p>
              </div>
            ))}
            <div>
              <p className="text-[11px] tracking-[0.16em] text-muted-foreground uppercase">
                Overdue batches
              </p>
              <p className="mt-1 font-mono text-lg text-foreground">
                {forecast.data?.batches_with_overdue_reserve ?? "—"}
              </p>
            </div>
          </div>

          <div className="mt-6 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                  tickLine={false}
                  axisLine={false}
                  width={70}
                />
                <Tooltip
                  cursor={{ fill: "var(--accent)" }}
                  contentStyle={{
                    background: "var(--card)",
                    border: "1px solid var(--border)",
                    borderRadius: 10,
                    fontSize: 12,
                    color: "var(--foreground)",
                  }}
                  formatter={(v: number) => formatINR(v)}
                />
                <Bar dataKey="amount" fill="var(--primary)" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="mt-10">
        <SectionHeading>Exception register</SectionHeading>
        <div className="panel overflow-hidden">
          <div className="flex flex-wrap items-center gap-3 border-b border-border px-6 py-4">
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="rounded-lg border border-border bg-background px-3 py-1.5 text-xs text-foreground"
            >
              <option value="ALL">All categories</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search settlement, order or description…"
              className="min-w-56 flex-1 rounded-lg border border-border bg-background px-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground"
            />
            <span className="font-mono text-xs text-muted-foreground">
              {filtered.length} / {rows.length}
            </span>
          </div>

          <div className="max-h-[560px] overflow-auto">
            <table className="w-full border-collapse text-left text-xs">
              <thead className="sticky top-0 bg-card">
                <tr>
                  {["Settlement", "Order", "Category", "Description", "Amount"].map((h) => (
                    <th
                      key={h}
                      className="border-b border-border px-4 py-3 font-medium text-muted-foreground whitespace-nowrap"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((r, i) => (
                  <tr key={i} className="hover:bg-accent/40">
                    <td className="border-b border-border/60 px-4 py-2.5 font-mono whitespace-nowrap text-foreground">
                      {r.settlement_id ?? "—"}
                    </td>
                    <td className="border-b border-border/60 px-4 py-2.5 font-mono whitespace-nowrap text-muted-foreground">
                      {r.order_id ?? "—"}
                    </td>
                    <td className="border-b border-border/60 px-4 py-2.5 whitespace-nowrap">
                      <span className="rounded-full bg-destructive/10 px-2 py-0.5 text-[10px] text-destructive">
                        {r.category}
                      </span>
                    </td>
                    <td className="min-w-72 border-b border-border/60 px-4 py-2.5 text-muted-foreground">
                      {r.description}
                    </td>
                    <td className="border-b border-border/60 px-4 py-2.5 text-right font-mono whitespace-nowrap text-foreground">
                      {formatINR(r.amount)}
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                      {exceptions.isLoading ? "Loading exceptions…" : "No exceptions match."}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

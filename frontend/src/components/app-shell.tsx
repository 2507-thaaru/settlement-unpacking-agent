import { Link } from "@tanstack/react-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Database, GitBranch, Home, LayoutDashboard, Loader2, RefreshCw } from "lucide-react";
import type { ReactNode } from "react";
import { toast } from "sonner";

import { ThemeToggle } from "@/components/theme-toggle";
import { triggerRun } from "@/lib/api";

const NAV = [
  { to: "/", label: "Home", icon: Home },
  { to: "/input-data", label: "Input Data", icon: Database },
  { to: "/how-it-works", label: "How It Works", icon: GitBranch },
  { to: "/dashboard", label: "Results Dashboard", icon: LayoutDashboard },
] as const;

export function AppShell({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  const queryClient = useQueryClient();
  const rerun = useMutation({
    mutationFn: triggerRun,
    onSuccess: async () => {
      await queryClient.invalidateQueries();
      toast.success("Pipeline re-run complete");
    },
    onError: (error: Error) => toast.error(error.message),
  });

  return (
    <div className="relative flex min-h-screen bg-background">
      <div className="grid-bg pointer-events-none fixed inset-0 -z-10" aria-hidden />

      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar/80 p-5 backdrop-blur md:flex">
        <Link to="/" className="mb-8 block">
          <p className="font-display text-sm leading-tight font-semibold text-sidebar-foreground">
            Settlement
            <br />
            Unpacking Agent
          </p>
          <p className="mt-1 text-[10px] tracking-[0.2em] text-muted-foreground uppercase">
            Track 4 · Finance
          </p>
        </Link>

        <nav className="flex flex-col gap-1">
          {NAV.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              activeOptions={{ exact: to === "/" }}
              activeProps={{
                className: "bg-sidebar-accent text-sidebar-accent-foreground",
              }}
              inactiveProps={{ className: "text-muted-foreground hover:text-sidebar-foreground" }}
              className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors"
            >
              <Icon className="size-4" />
              {label}
            </Link>
          ))}
        </nav>

        <div className="mt-auto space-y-3 pt-6">
          <button
            type="button"
            onClick={() => rerun.mutate()}
            disabled={rerun.isPending}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-60"
          >
            {rerun.isPending ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <RefreshCw className="size-4" />
            )}
            Re-run pipeline
          </button>
          <p className="text-[11px] leading-relaxed text-muted-foreground">
            Every figure is read live from the pipeline API.
          </p>
        </div>
      </aside>

      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-10 border-b border-border bg-background/70 backdrop-blur">
          <div className="flex items-center gap-4 px-6 py-4">
            <div className="min-w-0">
              <h1 className="truncate text-lg font-semibold text-foreground">{title}</h1>
              <p className="truncate text-xs text-muted-foreground">{description}</p>
            </div>
            <div className="ml-auto flex items-center gap-2">
              <button
                type="button"
                onClick={() => rerun.mutate()}
                disabled={rerun.isPending}
                className="inline-flex items-center gap-2 rounded-full border border-border px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground md:hidden"
              >
                <RefreshCw className="size-3.5" /> Re-run
              </button>
              <ThemeToggle />
            </div>
          </div>
          <nav className="flex gap-1 overflow-x-auto border-t border-border px-4 py-2 md:hidden">
            {NAV.map(({ to, label }) => (
              <Link
                key={to}
                to={to}
                activeOptions={{ exact: to === "/" }}
                activeProps={{ className: "bg-accent text-accent-foreground" }}
                inactiveProps={{ className: "text-muted-foreground" }}
                className="rounded-full px-3 py-1.5 text-xs whitespace-nowrap"
              >
                {label}
              </Link>
            ))}
          </nav>
        </header>

        <main className="mx-auto max-w-7xl px-6 py-8">{children}</main>
      </div>
    </div>
  );
}

export function SectionHeading({ children }: { children: ReactNode }) {
  return (
    <h2 className="mb-4 text-xs font-medium tracking-[0.2em] text-muted-foreground uppercase">
      {children}
    </h2>
  );
}

export function StateCard({ children }: { children: ReactNode }) {
  return (
    <div className="panel p-6 text-sm text-muted-foreground">{children}</div>
  );
}

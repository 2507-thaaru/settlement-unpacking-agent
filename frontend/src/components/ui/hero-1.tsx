import { ChevronRight } from "lucide-react";
import { Link } from "@tanstack/react-router";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface HeroProps {
  eyebrow?: string;
  title: string;
  subtitle: string;
  ctaLabel?: string;
  ctaTo?: "/dashboard" | "/input-data" | "/how-it-works";

  secondary?: ReactNode;
  className?: string;
}

export function Hero({
  eyebrow = "Innovate Without Limits",
  title,
  subtitle,
  ctaLabel = "Explore Now",
  ctaTo = "/dashboard",
  secondary,
  className,
}: HeroProps) {
  return (
    <section
      className={cn(
        "relative isolate flex min-h-[78vh] flex-col items-center justify-center overflow-hidden px-6 py-28 text-center",
        className,
      )}
    >
      <div className="grid-bg absolute inset-0 -z-20" aria-hidden />
      <div className="radial-accent absolute inset-x-0 top-0 -z-10 h-[70vh]" aria-hidden />

      {eyebrow && (
        <div className="animate-fade-in mb-8">
          <span className="inline-flex items-center gap-2 rounded-full border border-border bg-card/60 px-4 py-1.5 text-xs font-medium tracking-[0.18em] text-muted-foreground uppercase backdrop-blur">
            {eyebrow}
            <ChevronRight className="size-3.5" />
          </span>
        </div>
      )}

      <h1 className="animate-fade-up max-w-4xl text-5xl leading-[1.05] font-semibold text-balance text-foreground sm:text-6xl md:text-7xl">
        {title}
      </h1>

      <p className="animate-fade-up mt-6 max-w-2xl text-base leading-relaxed text-pretty text-muted-foreground sm:text-lg">
        {subtitle}
      </p>

      {ctaLabel && (
        <div className="animate-fade-up mt-10 flex flex-wrap items-center justify-center gap-3">
          <Link
            to={ctaTo}
            className="group inline-flex items-center gap-2 rounded-full bg-primary px-7 py-3 text-sm font-medium text-primary-foreground transition-all hover:bg-primary/90 hover:shadow-[0_0_40px_-8px_var(--primary)]"
          >
            {ctaLabel}
            <ChevronRight className="size-4 transition-transform group-hover:translate-x-0.5" />
          </Link>
          {secondary}
        </div>
      )}

      <div className="bottom-fade pointer-events-none absolute inset-x-0 bottom-0 h-32" aria-hidden />
    </section>
  );
}

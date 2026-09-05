import { useMemo } from "react";

import GatewayFlow from "@/components/ui/gateway-flow";
import type { GraphEdge, GraphNode as ApiNode, GraphResponse } from "@/lib/api";

type Tone = "source" | "pass" | "idle" | "exception" | "hub" | "report";

type LaidOutNode = {
  id: string;
  x: number;
  y: number;
  w: number;
  h: number;
  title: string;
  subtitle?: string | undefined;
  tone: Tone;
};

const CATEGORY_ORDER = ["source_data", "pass", "exception_type", "orchestration", "report"];

const COLUMNS: Record<string, { cx: number; w: number; label?: string }> = {
  source_data: { cx: 150, w: 236, label: "Source data (this run)" },
  pass: { cx: 540, w: 224, label: "Matching passes (live status)" },
  exception_type: { cx: 930, w: 286, label: "Exceptions raised (live counts)" },
  orchestration: { cx: 1180, w: 148 },
  report: { cx: 1372, w: 176 },
};

const NODE_H = 62;
const ROW_GAP = 96;
const VIEW_W = 1480;
const PAD_Y = 56;

function toneFor(node: ApiNode): Tone {
  switch (node.category) {
    case "source_data":
      return "source";
    case "pass": {
      const idle =
        (node.exception_count ?? 0) === 0 &&
        !!node.status &&
        node.status.toLowerCase().includes("not");
      return idle ? "idle" : "pass";
    }
    case "exception_type":
      return "exception";
    case "orchestration":
      return "hub";
    case "report":
      return "report";
    default:
      return "idle";
  }
}

function splitLabel(label: string) {
  const [title = "", ...rest] = label.split("\n");
  const subtitle = rest.join(" ").replace(/^\(|\)$/g, "").trim();
  return { title: title.trim(), subtitle: subtitle || undefined };
}

function edgePath(from: LaidOutNode, to: LaidOutNode) {
  const x1 = from.x + from.w;
  const y1 = from.y + from.h / 2;
  const x2 = to.x;
  const y2 = to.y + to.h / 2;
  const dx = Math.max(40, (x2 - x1) * 0.5);
  return `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;
}

export function KnowledgeGraph({ graph }: { graph: GraphResponse }) {
  const { nodes, edges, height, groups } = useMemo(() => {
    const byCategory = new Map<string, ApiNode[]>();
    for (const n of graph.nodes ?? []) {
      const key = CATEGORY_ORDER.includes(n.category) ? n.category : "pass";
      const list = byCategory.get(key) ?? [];
      list.push(n);
      byCategory.set(key, list);
    }

    const rows = Math.max(1, ...[...byCategory.values()].map((l) => l.length));
    const totalH = rows * ROW_GAP - (ROW_GAP - NODE_H) + PAD_Y * 2;
    const inner = totalH - PAD_Y * 2;

    const laidOut: LaidOutNode[] = [];
    for (const category of CATEGORY_ORDER) {
      const list = byCategory.get(category) ?? [];
      const col = COLUMNS[category];
      if (!col || list.length === 0) continue;
      const blockH = list.length * NODE_H + Math.max(0, list.length - 1) * (ROW_GAP - NODE_H);
      const start = (inner - blockH) / 2;
      list.forEach((n, i) => {
        const { title, subtitle } = splitLabel(n.label ?? n.id);
        laidOut.push({
          id: n.id,
          title,
          subtitle,
          tone: toneFor(n),
          x: col.cx - col.w / 2,
          y: start + i * ROW_GAP,
          w: col.w,
          h: NODE_H,
        });
      });
    }

    const byId = new Map(laidOut.map((n) => [n.id, n]));
    const kindOf = (from: LaidOutNode) =>
      from.tone === "source" ? "flow" : from.tone === "pass" || from.tone === "idle" ? "raise" : "hub";

    const links = ((graph.edges ?? []) as GraphEdge[]).flatMap((e) => {
      const from = byId.get(e.from);
      const to = byId.get(e.to);
      if (!from || !to) return [];
      return [{ d: edgePath(from, to), kind: kindOf(from) as "flow" | "raise" | "hub" }];
    });

    const groupBands = CATEGORY_ORDER.filter(
      (c) => COLUMNS[c]?.label && (byCategory.get(c)?.length ?? 0) > 0,
    ).map((c) => {
      const col = COLUMNS[c]!;
      return { label: col.label!, cx: col.cx, w: col.w + 56 };
    });

    return { nodes: laidOut, edges: links, height: totalH, groups: groupBands };
  }, [graph]);

  return (
    <div className="panel relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 opacity-60">
        <GatewayFlow density={0.7} speed={0.7} opacity={0.55} strokeWidth={0.9} />
      </div>

      <div className="relative overflow-x-auto p-4 sm:p-6">
        <svg
          viewBox={`0 0 ${VIEW_W} ${height}`}
          className="h-auto w-full min-w-[720px]"
          role="img"
          aria-label={`Live knowledge graph with ${nodes.length} nodes and ${edges.length} connections`}
        >
          <defs>
            <marker
              id="kg-arrow"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" className="fill-muted-foreground/60" />
            </marker>
          </defs>

          <g transform={`translate(0, ${PAD_Y})`}>
            {groups.map((g) => (
              <g key={g.label}>
                <rect
                  x={g.cx - g.w / 2}
                  y={-36}
                  width={g.w}
                  height={height - PAD_Y * 2 + 68}
                  rx={20}
                  className="fill-foreground/[0.02] stroke-border"
                  strokeDasharray="6 7"
                />
                <text
                  x={g.cx}
                  y={-46}
                  textAnchor="middle"
                  className="fill-muted-foreground text-[15px] tracking-[0.14em] uppercase"
                >
                  {g.label}
                </text>
              </g>
            ))}

            {edges.map((e, i) => (
              <path
                key={i}
                d={e.d}
                fill="none"
                strokeWidth={1.4}
                markerEnd="url(#kg-arrow)"
                className={
                  e.kind === "flow"
                    ? "stroke-foreground/35"
                    : e.kind === "raise"
                      ? "stroke-foreground/55"
                      : "stroke-muted-foreground/35"
                }
                strokeDasharray="7 9"
              >
                <animate
                  attributeName="stroke-dashoffset"
                  from="32"
                  to="0"
                  dur="2.4s"
                  repeatCount="indefinite"
                />
              </path>
            ))}

            {nodes.map((n) => (
              <GraphNode key={n.id} node={n} />
            ))}
          </g>
        </svg>
      </div>

      <p className="relative border-t border-border px-6 py-4 text-xs leading-relaxed text-muted-foreground">
        Rendered live from <span className="font-mono">/api/graph</span> — every node, edge, row
        count and exception total comes from the current pipeline run, not a static diagram.
      </p>
    </div>
  );
}

function GraphNode({ node }: { node: LaidOutNode }) {
  const tone = {
    source: {
      box: "fill-foreground/[0.06] stroke-foreground/35",
      title: "fill-foreground",
      sub: "fill-muted-foreground",
      rx: 30,
    },
    pass: {
      box: "fill-foreground/[0.14] stroke-foreground/60",
      title: "fill-foreground",
      sub: "fill-muted-foreground",
      rx: 14,
    },
    idle: {
      box: "fill-muted/40 stroke-border",
      title: "fill-muted-foreground",
      sub: "fill-muted-foreground",
      rx: 14,
    },
    exception: {
      box: "fill-foreground/[0.09] stroke-foreground/45",
      title: "fill-foreground",
      sub: "fill-muted-foreground",
      rx: 10,
    },
    hub: {
      box: "fill-foreground/90 stroke-foreground",
      title: "fill-background",
      sub: "fill-background",
      rx: 16,
    },
    report: {
      box: "fill-foreground/[0.18] stroke-foreground/70",
      title: "fill-foreground",
      sub: "fill-muted-foreground",
      rx: 16,
    },
  }[node.tone];

  return (
    <g>
      <rect
        x={node.x}
        y={node.y}
        width={node.w}
        height={node.h}
        rx={tone.rx}
        strokeWidth={1.2}
        className={tone.box}
      />
      <text
        x={node.x + node.w / 2}
        y={node.y + (node.subtitle ? 26 : 36)}
        textAnchor="middle"
        className={`${tone.title} text-[15px] font-medium`}
      >
        {node.title}
      </text>
      {node.subtitle ? (
        <text
          x={node.x + node.w / 2}
          y={node.y + 45}
          textAnchor="middle"
          className={`${tone.sub} font-mono text-[13px]`}
        >
          {node.subtitle}
        </text>
      ) : null}
    </g>
  );
}

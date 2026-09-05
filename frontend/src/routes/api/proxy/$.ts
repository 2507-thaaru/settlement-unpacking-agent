import { createFileRoute } from "@tanstack/react-router";
import { getBackendBaseUrl } from "@/lib/backend-url";

// The backend base URL resolves from env vars (SETTLEMENT_API_URL and friends)
// and falls back to the deployed Render backend, so a host that is missing the
// env var still reaches production instead of failing with 503.
function baseUrl() {
  return getBackendBaseUrl();
}

async function forward(request: Request, splat: string | undefined) {
  const base = baseUrl();

  const incoming = new URL(request.url);
  const path = splat ?? "";
  // The backend exposes health at /health, everything else under /api/*.
  const target =
    path === "health"
      ? `${base}/health${incoming.search}`
      : `${base}/api/${path}${incoming.search}`;
  const body = request.method === "POST" ? await request.arrayBuffer() : undefined;
  const contentType = request.headers.get("content-type");


  let lastError: unknown;
  // Cloudflare quick tunnels drop briefly when restarted — retry before failing.
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const upstream = await fetch(target, {
        method: request.method,
        headers: {
          accept: "application/json",
          ...(contentType ? { "content-type": contentType } : {}),
        },
        ...(body === undefined ? {} : { body }),
      });
      if (upstream.status >= 500 && attempt < 2) {
        lastError = new Error(`Upstream returned ${upstream.status}`);
        await new Promise((r) => setTimeout(r, 400 * (attempt + 1)));
        continue;
      }
      const text = await upstream.text();
      return new Response(text, {
        status: upstream.status,
        headers: {
          "content-type": upstream.headers.get("content-type") ?? "application/json",
          "cache-control": "no-store",
        },
      });
    } catch (error) {
      lastError = error;
      await new Promise((r) => setTimeout(r, 400 * (attempt + 1)));
    }
  }

  return Response.json(
    {
      error: "upstream_unreachable",
      message:
        lastError instanceof Error
          ? `Could not reach the pipeline API (${lastError.message}). Is the Cloudflare tunnel running?`
          : "Could not reach the pipeline API",
    },
    { status: 502 },
  );
}


export const Route = createFileRoute("/api/proxy/$")({
  server: {
    handlers: {
      GET: async ({ request, params }) => forward(request, params._splat),
      POST: async ({ request, params }) => forward(request, params._splat),
    },
  },
});

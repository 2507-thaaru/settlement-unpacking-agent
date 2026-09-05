// Single source of truth for the pipeline backend base URL (server-side only).
//
// Production default is the deployed Render backend. Any hosting platform
// (Vercel, Lovable, local dev) can override it by setting one of the env vars
// below — useful for staging or a local FastAPI instance.
const DEFAULT_BACKEND_URL = "https://settlement-unpacking-agent.onrender.com";

const ENV_KEYS = [
  "SETTLEMENT_API_URL",
  "VITE_SETTLEMENT_API_URL",
  "PIPELINE_API_URL",
  "BACKEND_URL",
] as const;

export function getBackendBaseUrl(): string {
  for (const key of ENV_KEYS) {
    const value = process.env[key]?.trim();
    // Ignore placeholder / local values that would break a public deployment.
    if (!value) continue;
    if (/example\.com/i.test(value)) continue;
    if (/localhost|127\.0\.0\.1/i.test(value)) {
      // Allowed only outside production (local development).
      if (process.env["NODE_ENV"] === "production") continue;
    }
    return value.replace(/\/+$/, "");
  }
  return DEFAULT_BACKEND_URL;
}

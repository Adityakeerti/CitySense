/**
 * Runtime configuration. EXPO_PUBLIC_* variables are inlined at build time from mobile/.env
 * (see .env.example). Nothing environment-specific is hard-coded in the app.
 */
const rawBase = process.env.EXPO_PUBLIC_API_BASE_URL ?? "";

export const config = {
  apiBaseUrl: rawBase.replace(/\/+$/, ""),
  apiTimeoutMs: Number(process.env.EXPO_PUBLIC_API_TIMEOUT_MS ?? 15000),
};

export const isConfigured = /^https?:\/\//.test(config.apiBaseUrl);

/** Resolves a server-relative path (e.g. "/avatars/amit.png") against the API base URL. */
export function absoluteUrl(path: string): string {
  if (/^https?:\/\//.test(path)) return path;
  return `${config.apiBaseUrl}${path.startsWith("/") ? "" : "/"}${path}`;
}

/** STOMP endpoint derived from the API base (http -> ws, https -> wss). */
export function websocketUrl(path = "/ws"): string {
  return config.apiBaseUrl.replace(/^http/, "ws") + path;
}

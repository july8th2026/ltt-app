/**
 * Minimal TypeScript client for the LTT Studios Public API.
 *
 * Uses `fetch` and nothing else, so it runs in Node 18+, Deno, Bun and the
 * browser without a build step or a dependency.
 *
 * The rule this client exists to enforce, because getting it wrong costs the
 * customer money:
 *
 *     a chargeable POST is retried **only** with the same Idempotency-Key.
 *
 * ```ts
 * const client = new LttClient({ baseUrl: "https://app.lttstudios.com", apiKey });
 * const quote = await client.quote("image.thumbnail", { topic: "bánh mì", count: 2 });
 * const job = await client.waitForJob((await client.createJob(quote, { topic: "bánh mì", count: 2 })).id);
 * ```
 */

export interface LttClientOptions {
  baseUrl: string;
  apiKey: string;
  /** Retries for safe (idempotent) requests. Default 3. */
  maxRetries?: number;
  /** Injected in tests; production uses global fetch. */
  fetchImpl?: typeof fetch;
}

export interface Problem {
  type?: string;
  title?: string;
  status?: number;
  code?: string;
  detail?: unknown;
  instance?: string;
  request_id?: string;
  retry_after?: number;
  [key: string]: unknown;
}

export interface Quote {
  quote: string;
  tool: string;
  credit: number;
  expires_in: number;
  balance: number;
}

export type JobStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";

export interface Job {
  id: string;
  tool: string | null;
  status: JobStatus;
  progress: number;
  created_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  credit: { held: number; charged: number };
  outputs?: Array<{ id: string; field: string; index: number }>;
  result?: Record<string, unknown>;
  error?: { message: string };
}

/** One problem+json response, kept whole so callers can branch on `code`. */
export class LttApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId: string;
  readonly payload: Problem;

  constructor(status: number, payload: Problem) {
    const detail = typeof payload.detail === "string" ? payload.detail : payload.title;
    super(`${status} ${payload.code ?? ""}: ${detail ?? ""}`);
    this.name = "LttApiError";
    this.status = status;
    this.code = payload.code ?? "";
    this.requestId = payload.request_id ?? "";
    this.payload = payload;
  }

  get retryAfter(): number {
    return Number(this.payload.retry_after ?? 0) || 0;
  }
}

const RETRY_STATUSES = new Set([429, 500, 502, 503, 504]);
const USER_AGENT = "ltt-public-api-ts/1.0";

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export class LttClient {
  private readonly baseUrl: string;
  private readonly apiKey: string;
  private readonly maxRetries: number;
  private readonly fetchImpl: typeof fetch;

  constructor(options: LttClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/+$/, "");
    this.apiKey = options.apiKey;
    this.maxRetries = options.maxRetries ?? 3;
    this.fetchImpl = options.fetchImpl ?? fetch;
  }

  private url(path: string): string {
    return `${this.baseUrl}/api/v1${path}`;
  }

  private async request<T>(
    method: string,
    path: string,
    options: { body?: unknown; headers?: Record<string, string>; retry?: boolean } = {},
  ): Promise<T> {
    const headers: Record<string, string> = {
      Authorization: `Bearer ${this.apiKey}`,
      Accept: "application/json",
      "User-Agent": USER_AGENT,
      ...(options.headers ?? {}),
    };
    let body: string | undefined;
    if (options.body !== undefined) {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(options.body);
    }

    for (let attempt = 1; ; attempt += 1) {
      const response = await this.fetchImpl(this.url(path), { method, headers, body });
      const text = await response.text();
      let parsed: unknown = {};
      try {
        parsed = text ? JSON.parse(text) : {};
      } catch {
        parsed = {};
      }
      if (response.ok) {
        return parsed as T;
      }
      const problem = parsed as Problem;
      const retryable = options.retry === true && RETRY_STATUSES.has(response.status);
      if (retryable && attempt <= this.maxRetries) {
        // The server's own retry_after beats a guess from the client.
        const backoff = Math.min(8000, 500 * 2 ** (attempt - 1));
        await sleep(Math.max(Number(problem.retry_after ?? 0) * 1000, backoff));
        continue;
      }
      throw new LttApiError(response.status, problem);
    }
  }

  // ── Reads (safe to retry) ─────────────────────────────────────────────────

  me() {
    return this.request<Record<string, unknown>>("GET", "/me", { retry: true });
  }

  capabilities() {
    return this.request<Record<string, unknown>>("GET", "/capabilities", { retry: true });
  }

  tools(limit = 20, offset = 0) {
    return this.request<{ items: unknown[] }>(
      "GET", `/tools?limit=${limit}&offset=${offset}`, { retry: true });
  }

  tool(name: string) {
    return this.request<Record<string, unknown>>(
      "GET", `/tools/${encodeURIComponent(name)}`, { retry: true });
  }

  job(jobId: string) {
    return this.request<Job>("GET", `/jobs/${encodeURIComponent(jobId)}`, { retry: true });
  }

  balance() {
    return this.request<{ balance: number }>("GET", "/credits/balance", { retry: true });
  }

  usage() {
    return this.request<Record<string, unknown>>("GET", "/usage", { retry: true });
  }

  async artifactUrl(artifactId: string): Promise<string> {
    const body = await this.request<{ url: string }>(
      "GET", `/artifacts/${encodeURIComponent(artifactId)}`, { retry: true });
    return body.url;
  }

  // ── Writes ────────────────────────────────────────────────────────────────

  quote(tool: string, input: Record<string, unknown>) {
    return this.request<Quote>("POST", "/quotes", { body: { tool, input }, retry: true });
  }

  /**
   * Run a quoted call.
   *
   * The idempotency key is generated once and reused for every retry of *this*
   * call. A fresh key on retry is what turns one timeout into two charges.
   */
  createJob(quote: Quote, input: Record<string, unknown>, idempotencyKey?: string) {
    const key = idempotencyKey ?? crypto.randomUUID().replace(/-/g, "");
    return this.request<Job>("POST", "/jobs", {
      body: { tool: quote.tool, quote: quote.quote, input },
      headers: { "Idempotency-Key": key },
      retry: true,
    });
  }

  cancelJob(jobId: string) {
    return this.request<Job>("POST", `/jobs/${encodeURIComponent(jobId)}/cancel`);
  }

  async waitForJob(jobId: string, timeoutMs = 600_000, pollMs = 2000): Promise<Job> {
    const deadline = Date.now() + timeoutMs;
    for (;;) {
      const job = await this.job(jobId);
      if (job.status === "succeeded" || job.status === "failed" || job.status === "cancelled") {
        return job;
      }
      if (Date.now() >= deadline) {
        throw new Error(`job ${jobId} did not finish in ${timeoutMs}ms`);
      }
      await sleep(pollMs);
    }
  }

  createWebhook(url: string, events: string[] = []) {
    return this.request<{ id: string; secret: string }>(
      "POST", "/webhooks", { body: { url, events } });
  }
}

/**
 * Check a webhook delivery came from LTT and is not a replay.
 *
 * Run this before trusting the payload. `crypto.subtle` keeps it dependency
 * free; the comparison is constant time.
 */
export async function verifyWebhook(options: {
  secret: string;
  timestamp: string | number;
  eventId: string;
  body: string;
  signature: string;
  toleranceSeconds?: number;
}): Promise<boolean> {
  const sentAt = Number(options.timestamp);
  if (!Number.isFinite(sentAt)) return false;
  const tolerance = options.toleranceSeconds ?? 300;
  if (Math.abs(Math.floor(Date.now() / 1000) - sentAt) > tolerance) return false;

  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw", encoder.encode(options.secret),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const payload = encoder.encode(`${sentAt}.${options.eventId}.${options.body}`);
  const digest = await crypto.subtle.sign("HMAC", key, payload);
  const expected = "v1=" + Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0")).join("");

  const given = options.signature ?? "";
  if (expected.length !== given.length) return false;
  let mismatch = 0;
  for (let index = 0; index < expected.length; index += 1) {
    mismatch |= expected.charCodeAt(index) ^ given.charCodeAt(index);
  }
  return mismatch === 0;
}

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

export interface WorkflowQuote {
  quote: string;
  workflow_id: string;
  version_id: string;
  /** Tran duoc KY va duoc GIU. So toi da co the bi tru. */
  credit_max: number;
  /** So nhieu kha nang tra that. Khong duoc ky, khong duoc giu. */
  credit_estimate: number;
  expires_in: number;
  balance: number;
}

export interface WorkflowRun {
  id: string;
  workflow_id: string;
  version_id: string;
  status: string;
  trigger: string;
  /** Hai so, luon di cung nhau: thu khach dong y, va thu that su thu. */
  credit_max: number;
  credit_charged: number;
  settled: boolean;
  created_at: string | null;
}

export interface RunArtifact {
  id: string;
  kind: string;
  mime: string;
  size_bytes: number;
  checksum_sha256: string;
  created_at: string | null;
}

export interface ChatMessage {
  role: "system" | "user" | "assistant" | "tool";
  content: string | Array<Record<string, unknown>>;
}

export interface ChatCompletion {
  object: "chat.completion";
  model: string;
  choices: Array<{
    index: number;
    message: { role: string; content: string; tool_calls?: unknown[] };
    finish_reason: string;
  }>;
  usage: { prompt_tokens: number; completion_tokens: number; total_tokens: number };
  /** Everything OpenAI has no field for. The money lives here, not in `usage`:
   *  adding our own keys to `usage` would break clients that parse it strictly. */
  x_ltt: {
    /** What was ACTUALLY billed, not what was held. Usually well below it. */
    credit_charged: number;
    credit_held: number;
    usage_measured: boolean;
    cached_prompt_tokens: number;
    duration_seconds: number;
    test_mode: boolean;
  };
}

export interface ChatOptions {
  model?: string;
  maxTokens?: number;
  temperature?: number;
  tools?: unknown[];
  reasoningEffort?: string;
  idempotencyKey?: string;
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

  // @covers GET /me
  me() {
    return this.request<Record<string, unknown>>("GET", "/me", { retry: true });
  }

  // @covers GET /capabilities
  capabilities() {
    return this.request<Record<string, unknown>>("GET", "/capabilities", { retry: true });
  }

  // @covers GET /tools
  tools(limit = 20, offset = 0) {
    return this.request<{ items: unknown[] }>(
      "GET", `/tools?limit=${limit}&offset=${offset}`, { retry: true });
  }

  // @covers GET /tools/{tool_name}
  tool(name: string) {
    return this.request<Record<string, unknown>>(
      "GET", `/tools/${encodeURIComponent(name)}`, { retry: true });
  }

  /**
   * Model aliases this key may use.
   *
   * Aliases, never provider model ids: the platform publishes names it
   * controls, so a provider swap does not become your migration.
   */
  // @covers GET /models
  models(limit = 20, offset = 0) {
    return this.request<{ items: unknown[] }>(
      "GET", `/models?limit=${limit}&offset=${offset}`, { retry: true });
  }

  // @covers GET /models/{model_name}
  model(name: string) {
    return this.request<Record<string, unknown>>(
      "GET", `/models/${encodeURIComponent(name)}`, { retry: true });
  }

  /** Liveness of the API surface. Needs no credential, so it is the one call
   * worth making before blaming your key. */
  // @covers GET /health
  health() {
    return this.request<Record<string, unknown>>("GET", "/health",
      { retry: true });
  }

  // @covers GET /jobs/{job_id}
  job(jobId: string) {
    return this.request<Job>("GET", `/jobs/${encodeURIComponent(jobId)}`, { retry: true });
  }

  // @covers GET /jobs
  jobs(status = "", limit = 20, offset = 0) {
    const query = new URLSearchParams({ status, limit: String(limit),
                                        offset: String(offset) });
    return this.request<{ items: Job[] }>("GET", `/jobs?${query}`,
      { retry: true });
  }

  // @covers GET /credits/balance
  balance() {
    return this.request<{ balance: number }>("GET", "/credits/balance", { retry: true });
  }

  // @covers GET /usage
  usage() {
    return this.request<Record<string, unknown>>("GET", "/usage", { retry: true });
  }

  // @covers GET /artifacts/{artifact_id}
  async artifactUrl(artifactId: string): Promise<string> {
    const body = await this.request<{ url: string }>(
      "GET", `/artifacts/${encodeURIComponent(artifactId)}`, { retry: true });
    return body.url;
  }

  /**
   * The bytes of one output.
   *
   * Goes through `/content` rather than the signed URL so it works from a
   * server with no outbound access to object storage — and so a caller does
   * not have to handle a URL that expires while they are reading it.
   */
  // @covers GET /artifacts/{artifact_id}/content
  async downloadArtifact(artifactId: string): Promise<ArrayBuffer> {
    const response = await fetch(
      this.url(`/artifacts/${encodeURIComponent(artifactId)}/content`),
      { headers: { Authorization: `Bearer ${this.apiKey}` } });
    if (!response.ok) {
      throw new LttApiError(response.status, await response.json()
        .catch(() => ({})) as Problem);
    }
    return response.arrayBuffer();
  }

  // ── Writes ────────────────────────────────────────────────────────────────

  // @covers POST /quotes
  quote(tool: string, input: Record<string, unknown>) {
    return this.request<Quote>("POST", "/quotes", { body: { tool, input }, retry: true });
  }

  /**
   * Run a quoted call.
   *
   * The idempotency key is generated once and reused for every retry of *this*
   * call. A fresh key on retry is what turns one timeout into two charges.
   */
  // @covers POST /jobs
  createJob(quote: Quote, input: Record<string, unknown>, idempotencyKey?: string) {
    const key = idempotencyKey ?? crypto.randomUUID().replace(/-/g, "");
    return this.request<Job>("POST", "/jobs", {
      body: { tool: quote.tool, quote: quote.quote, input },
      headers: { "Idempotency-Key": key },
      retry: true,
    });
  }

  /**
   * A chat completion, answered in this request. Chargeable.
   *
   * Unlike `createJob` there is no quote: the price depends on the tokens the
   * model produces, which do not exist until it has run. Credit is held at a
   * ceiling before the model starts and settled from the measured usage, so
   * `x_ltt.credit_charged` is the real bill and is usually well below the hold.
   *
   * That missing quote is why the Idempotency-Key matters more here than
   * anywhere else on the surface: it is the only thing standing between a
   * network timeout and paying twice for the same generation. It is generated
   * once, here, and reused for every retry of *this* call.
   *
   * A call that cannot finish inside the server's synchronous budget is refused
   * with 400 rather than cut off mid-answer; send that work to `createJob`.
   */
  // @covers POST /chat/completions
  chat(messages: ChatMessage[], options: ChatOptions = {}) {
    const key = options.idempotencyKey ?? crypto.randomUUID().replace(/-/g, "");
    const body: Record<string, unknown> = {
      model: options.model ?? "ltt_llm",
      messages,
      max_tokens: options.maxTokens ?? 1024,
    };
    if (options.temperature !== undefined) body.temperature = options.temperature;
    if (options.tools?.length) body.tools = options.tools;
    if (options.reasoningEffort) body.reasoning_effort = options.reasoningEffort;
    return this.request<ChatCompletion>("POST", "/chat/completions", {
      body,
      headers: { "Idempotency-Key": key },
      // Safe precisely because the key is fixed for the whole loop.
      retry: true,
    });
  }

  // @covers-not POST /messages — an SSE stream in the Anthropic Messages shape,
  //   served for Claude Code and Claude Desktop rather than for this SDK. Those
  //   clients speak the protocol natively; wrapping it here would mean
  //   re-implementing their parsers badly. Point ANTHROPIC_BASE_URL at the /api
  //   parent of that route instead.
  // @covers-not POST /responses — the same, in the OpenAI Responses shape, for
  //   the Codex CLI and its VS Code extension. Set base_url to this route's
  //   parent and wire_api = "responses".
  //
  //   Neither takes an Idempotency-Key (Q107): no CLI sends one, so the money is
  //   protected by settling from the tokens actually produced instead. A stream
  //   you abandon halfway bills for what it generated, not for the ceiling.

  // ── Workflow (WF-802) ──────────────────────────────────────────────────
  //
  // Khac `/jobs` o cho dat nhat: bao gia gan voi GRAPH DA PUBLISH, va no giu
  // TRAN CHI PHI CUA CA DO THI chu khong phai gia cua mot loi goi tool.

  /**
   * Price a workflow run. Returns TWO numbers, and both matter.
   *
   * `credit_max` is the ceiling that gets signed and held; `credit_estimate`
   * is what the run will most likely cost. A single number would force the
   * caller to guess the other one.
   */
  // @covers POST /workflows/{workflow_id}/quotes
  quoteWorkflow(workflowId: string) {
    return this.request<WorkflowQuote>(
      "POST", `/workflows/${encodeURIComponent(workflowId)}/quotes`,
      { retry: true });
  }

  /**
   * Start a quoted workflow run.
   *
   * Same key discipline as `createJob`, and it matters more here: a second key
   * does not buy a second job, it buys a second *run of a whole graph*, at the
   * ceiling of that graph.
   */
  // @covers POST /workflows/{workflow_id}/runs
  startRun(workflowId: string, quote: WorkflowQuote, idempotencyKey?: string) {
    const key = idempotencyKey ?? crypto.randomUUID().replace(/-/g, "");
    return this.request<WorkflowRun>(
      "POST", `/workflows/${encodeURIComponent(workflowId)}/runs`, {
        body: { quote: quote.quote },
        headers: { "Idempotency-Key": key },
        retry: true,
      });
  }

  // @covers GET /runs/{run_id}
  getRun(runId: string) {
    return this.request<WorkflowRun>(
      "GET", `/runs/${encodeURIComponent(runId)}`, { retry: true });
  }

  /** Cancel a run. Cancelling an already-cancelled run is not an error. */
  // @covers POST /runs/{run_id}/cancel
  cancelRun(runId: string) {
    return this.request<WorkflowRun>(
      "POST", `/runs/${encodeURIComponent(runId)}/cancel`, { retry: true });
  }

  // @covers GET /runs/{run_id}/artifacts
  runArtifacts(runId: string) {
    return this.request<{ run_id: string; artifacts: RunArtifact[] }>(
      "GET", `/runs/${encodeURIComponent(runId)}/artifacts`, { retry: true });
  }

  // @covers POST /jobs/{job_id}/cancel
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

  // @covers POST /webhooks
  createWebhook(url: string, events: string[] = []) {
    return this.request<{ id: string; secret: string }>(
      "POST", "/webhooks", { body: { url, events } });
  }

  // @covers GET /webhooks
  webhooks() {
    return this.request<{ items: unknown[] }>("GET", "/webhooks",
      { retry: true });
  }

  // @covers DELETE /webhooks/{webhook_id}
  deleteWebhook(webhookId: string) {
    return this.request<Record<string, unknown>>(
      "DELETE", `/webhooks/${encodeURIComponent(webhookId)}`);
  }

  /**
   * What we tried to send you, and how it went.
   *
   * The first thing to read when a callback did not arrive: it separates "we
   * never sent it" from "we sent it and your endpoint refused".
   */
  // @covers GET /webhooks/deliveries
  webhookDeliveries(subscriptionId = "", status = "", limit = 20, offset = 0) {
    const query = new URLSearchParams({ limit: String(limit),
                                        offset: String(offset) });
    if (subscriptionId) query.set("subscription_id", subscriptionId);
    if (status) query.set("status", status);
    return this.request<{ items: unknown[] }>(
      "GET", `/webhooks/deliveries?${query}`, { retry: true });
  }

  /**
   * Put a file where a tool can read it: ticket, bytes, confirm.
   *
   * Three calls because the platform stages an upload before anything is paid
   * for, and promotes it only after the job holds credit (Q85). The direct PUT
   * is used when the storage backend offers one, so gigabytes never travel
   * through the API process.
   */
  // @covers POST /uploads
  // @covers POST /uploads/{upload_id}/content
  // @covers POST /uploads/{upload_id}/confirm
  async upload(tool: string, field: string, filename: string,
               contentType: string, data: Blob | ArrayBuffer): Promise<string> {
    const blob = data instanceof Blob ? data : new Blob([data]);
    const ticket = await this.request<{
      id: string;
      upload?: { method: string; url: string; headers?: Record<string, string> };
    }>("POST", "/uploads", {
      body: { tool, field, filename, content_type: contentType,
              size: blob.size },
    });

    const target = ticket.upload;
    if (target && target.method.toUpperCase() === "PUT") {
      const put = await fetch(target.url, {
        method: "PUT", body: blob,
        headers: { "Content-Type": contentType, ...(target.headers ?? {}) },
      });
      if (!put.ok) throw new Error(`upload failed: HTTP ${put.status}`);
    } else {
      const form = new FormData();
      form.append("file", blob, filename);
      const post = await fetch(
        this.url(`/uploads/${encodeURIComponent(ticket.id)}/content`),
        { method: "POST", body: form,
          headers: { Authorization: `Bearer ${this.apiKey}` } });
      if (!post.ok) throw new Error(`upload failed: HTTP ${post.status}`);
    }

    await this.request<Record<string, unknown>>(
      "POST", `/uploads/${encodeURIComponent(ticket.id)}/confirm`);
    return ticket.id;
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

// The one route no client method wraps, and why that is deliberate:
// @covers-not GET /openapi.json — machine-readable spec, not a call your code
// makes. Fetch it with any HTTP client, or download the versioned copy from the
// developer portal; wrapping it would imply the SDK parses it, which it does not.

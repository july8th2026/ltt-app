"""Runnable examples, generated from the contract rather than written twice.

Every snippet a developer copies — the quickstart, the per-tool recipe, the
n8n node body — is built here from the same :class:`PublicTool` the API
validates against. That is the only way an example cannot drift: there is no
second copy of the payload to forget to update.

Environment variables are part of the contract too, so they are named once:

    LTT_BASE_URL    where the API lives, e.g. https://app.lttstudios.com
    LTT_API_KEY     the developer key, ltt_sk_…
    LTT_PROJECT_ID  optional; only useful for a caller juggling several
                    integrations, since the key already decides the project

No snippet ever contains a key. They read the environment, and the tests refuse
anything that looks like a literal credential.
"""
from __future__ import annotations

import json

ENV_API_KEY = "LTT_API_KEY"
ENV_BASE_URL = "LTT_BASE_URL"
ENV_PROJECT_ID = "LTT_PROJECT_ID"

#: What a caller must set before anything works, and what each one is for.
ENV_VARS = (
    (ENV_BASE_URL, "https://app.lttstudios.com",
     "Where the API lives. No trailing slash; /api/v1 is added for you."),
    (ENV_API_KEY, "ltt_sk_…",
     "Your developer key. Create it in the portal; it is shown once."),
    (ENV_PROJECT_ID, "",
     "Optional. The key already belongs to a project — set this only if your "
     "own code routes by project."),
)

#: How to set them, per shell. People paste the wrong one constantly.
SHELL_EXPORTS = (
    ("bash / zsh (macOS, Linux)",
     'export LTT_BASE_URL="https://app.lttstudios.com"\n'
     'export LTT_API_KEY="ltt_sk_…"'),
    ("PowerShell (Windows)",
     '$env:LTT_BASE_URL = "https://app.lttstudios.com"\n'
     '$env:LTT_API_KEY  = "ltt_sk_…"'),
    ("cmd.exe (Windows)",
     'set LTT_BASE_URL=https://app.lttstudios.com\n'
     'set LTT_API_KEY=ltt_sk_…'),
)


def example_input(tool) -> dict:
    """A payload built from the tool's own declared examples.

    A required parameter with no declared example gets a typed placeholder
    rather than an invented value: a made-up prompt reads like advice, and
    ``<string>`` reads like the instruction it is.
    """
    schema = tool.input_schema
    required = set(schema.get("required", ()))
    payload: dict = {}
    for name, spec in (schema.get("properties") or {}).items():
        examples = spec.get("examples") or []
        if examples:
            payload[name] = examples[0]
        elif name in required:
            payload[name] = f"<{spec.get('type', 'string')}>"
    return payload


def _json(payload) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def curl_quote(tool) -> str:
    return (f'curl -X POST "${ENV_BASE_URL}/api/v1/quotes" \\\n'
            f'  -H "Authorization: Bearer ${ENV_API_KEY}" \\\n'
            f'  -H "Content-Type: application/json" \\\n'
            f"  -d '{_json({'tool': tool.name, 'input': example_input(tool)})}'")


def curl_submit(tool) -> str:
    """The chargeable call. The Idempotency-Key is not optional decoration."""
    return (f'curl -X POST "${ENV_BASE_URL}/api/v1/jobs" \\\n'
            f'  -H "Authorization: Bearer ${ENV_API_KEY}" \\\n'
            f'  -H "Content-Type: application/json" \\\n'
            f'  -H "Idempotency-Key: $(uuidgen)" \\\n'
            f"  -d '{_json({'tool': tool.name, 'quote': '<quote from the step above>', 'input': example_input(tool)})}'")


def python_snippet(tool) -> str:
    payload = _json(example_input(tool)).replace("\n", "\n    ")
    return f'''import os, time, uuid, urllib.request, json

BASE = os.environ["{ENV_BASE_URL}"].rstrip("/") + "/api/v1"
HEAD = {{"Authorization": "Bearer " + os.environ["{ENV_API_KEY}"],
        "Content-Type": "application/json",
        # BAT BUOC. Cloudflare tra 403 cho User-Agent mac dinh cua urllib
        # TRUOC khi request toi duoc may chu. Do 24/08: urllib mac dinh -> 403;
        # requests / openai / anthropic / curl / Go / node-fetch deu -> 401,
        # tuc chi rieng urllib bi chan. Dat bat cu ten nao cung qua.
        "User-Agent": "my-app/1.0"}}


def call(method, path, body=None, extra=None):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(BASE + path, data=data, method=method,
                                     headers={{**HEAD, **(extra or {{}})}})
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read())


payload = {payload}

quote = call("POST", "/quotes", {{"tool": "{tool.name}", "input": payload}})
print("costs", quote["credit"], "credit")

# The same key on every retry of THIS call: a timeout you retry without one is
# a second job and a second charge.
job = call("POST", "/jobs",
           {{"tool": "{tool.name}", "quote": quote["quote"], "input": payload}},
           {{"Idempotency-Key": str(uuid.uuid4())}})

while job["status"] in ("queued", "running"):
    time.sleep(2)
    job = call("GET", "/jobs/" + job["id"])
print(job["status"], job.get("outputs"))'''


def typescript_snippet(tool) -> str:
    payload = _json(example_input(tool)).replace("\n", "\n  ")
    return f'''const BASE = `${{process.env.{ENV_BASE_URL}}}/api/v1`;
const HEAD = {{
  Authorization: `Bearer ${{process.env.{ENV_API_KEY}}}`,
  "Content-Type": "application/json",
}};

async function call(method: string, path: string, body?: unknown,
                    extra: Record<string, string> = {{}}) {{
  const response = await fetch(BASE + path, {{
    method, headers: {{ ...HEAD, ...extra }},
    body: body === undefined ? undefined : JSON.stringify(body),
  }});
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}}

const input = {payload};

const quote = await call("POST", "/quotes", {{ tool: "{tool.name}", input }});
let job = await call("POST", "/jobs",
  {{ tool: "{tool.name}", quote: quote.quote, input }},
  {{ "Idempotency-Key": crypto.randomUUID() }});

while (job.status === "queued" || job.status === "running") {{
  await new Promise((r) => setTimeout(r, 2000));
  job = await call("GET", `/jobs/${{job.id}}`);
}}
console.log(job.status, job.outputs);'''


def raw_http_snippet(tool) -> str:
    """For anyone whose tool speaks HTTP and nothing else — n8n, Make, curl in
    a language nobody here has heard of."""
    body = _json({"tool": tool.name, "quote": "<quote>",
                  "input": example_input(tool)})
    return (f"POST /api/v1/jobs HTTP/1.1\n"
            f"Host: app.lttstudios.com\n"
            f"Authorization: Bearer <{ENV_API_KEY}>\n"
            f"Content-Type: application/json\n"
            f"Idempotency-Key: 8f14e45f-ea0b-4b3f-8c1a-0f9d2e6c7a10\n"
            f"\n{body}")


def powershell_snippet(tool) -> str:
    payload = _json(example_input(tool)).replace("\n", "\n  ")
    return f'''$base = "$env:{ENV_BASE_URL}/api/v1"
$head = @{{ Authorization = "Bearer $env:{ENV_API_KEY}" }}
$input = @'
{payload}
'@ | ConvertFrom-Json

$quote = Invoke-RestMethod -Method Post -Uri "$base/quotes" -Headers $head `
  -ContentType "application/json" `
  -Body (@{{ tool = "{tool.name}"; input = $input }} | ConvertTo-Json -Depth 8)

$head["Idempotency-Key"] = [guid]::NewGuid().ToString()
$job = Invoke-RestMethod -Method Post -Uri "$base/jobs" -Headers $head `
  -ContentType "application/json" `
  -Body (@{{ tool = "{tool.name}"; quote = $quote.quote; input = $input }} |
         ConvertTo-Json -Depth 8)
$job.id'''


#: Integrations that speak HTTP without code. Each entry is (name, how).
NO_CODE_RECIPES = (
    ("n8n — HTTP Request node",
     "Method POST, URL `{{$env.LTT_BASE_URL}}/api/v1/jobs`, Authentication "
     "*Generic → Header Auth* with name `Authorization` and value "
     "`Bearer {{$env.LTT_API_KEY}}`. Add a header `Idempotency-Key` set to an "
     "expression that is stable for one logical call — `{{$json.orderId}}` is "
     "right, `{{$now}}` is a second charge on every retry. Quote first in a "
     "preceding node and pass `quote` through."),
    ("Make — HTTP module",
     "Use *Make a request*: POST to `/api/v1/jobs`, headers `Authorization: "
     "Bearer …` and `Idempotency-Key`. Parse response = Yes. Make retries "
     "failed modules by default, which is safe here only because the key is "
     "constant per call — take it from the bundle, never from a timestamp."),
    ("Any HTTP client",
     "Two calls: POST /api/v1/quotes to learn the price, POST /api/v1/jobs "
     "with the quote and an Idempotency-Key. Then poll GET /api/v1/jobs/{id} "
     "or register a webhook. Nothing else is required."),
)


# ── The synchronous door: POST /chat/completions (Q106) ──────────────────────
#
# Why this door gets its own set of examples. The job door is three steps —
# quote, submit, poll. The chat door is *one*, has no quote at all, and returns
# the bill in the same response. Reusing the job examples here would teach a
# caller to ask for a quote that does not exist.
#
# MEASURED, NOT ASSUMED (2026-08-23, openai 2.30.0):
#
#     OpenAI(...).chat.completions.create(...)                    -> 400
#     ... create(..., extra_headers={"Idempotency-Key": ...})     -> 200
#
# The OpenAI SDK *does* generate an idempotency key for every POST and reuses it
# across its own retries — but it only sends one when `_idempotency_header` is
# set, and on the OpenAI client that attribute is `None`. The key is generated
# and then thrown away.
#
# So every example below carries the header. A "cleaner" example without it is
# an example that does not run, and the reader concludes the API is broken
# rather than that the example is wrong.

CHAT_MODEL = "ltt_llm"
CHAT_PATH = "/chat/completions"

#: Deliberately short. A long prompt pulls attention onto its content instead of
#: onto the shape of the call, which is the only thing these examples teach.
CHAT_PROMPT = "Say hello in one sentence."
CHAT_MESSAGES = [{"role": "user", "content": CHAT_PROMPT}]


def _chat_body(max_tokens: int = 300) -> dict:
    return {"model": CHAT_MODEL, "messages": CHAT_MESSAGES, "max_tokens": max_tokens}


def curl_chat() -> str:
    return (f'curl -X POST "${ENV_BASE_URL}/api/v1{CHAT_PATH}" \\\n'
            f'  -H "Authorization: Bearer ${ENV_API_KEY}" \\\n'
            f'  -H "Content-Type: application/json" \\\n'
            f'  -H "Idempotency-Key: $(uuidgen)" \\\n'
            f"  -d '{_json(_chat_body())}'")


#: Công cụ tạo ảnh, tên công khai. Một chỗ để mọi trang nói cùng một tên.
ANH_TOOL = "image.ltt"

#: Đầu vào mẫu cho một lượt vẽ. Giữ ở đây để ba đoạn dưới không lệch nhau.
ANH_INPUT = {"prompt": "a calico cat on a windowsill", "mode": "t2i", "count": 1}

#: Ba chế độ, chỉ MÃ. Văn xuôi mô tả nằm ở template — nơi `_()` hoạt động.
#:
#: ⚠️ Module này **không có bộ dịch**, và cố ý giữ như vậy: nó sinh **đoạn mã**,
#:    không sinh câu chữ hiển thị. Mọi chú thích trong đây là tiếng Anh, giống
#:    phần còn lại của tệp. Viết văn xuôi tiếng Việt vào đây là làm bánh cóc i18n
#:    báo động đúng — và nó đã báo, ngày 25/08, 9 chuỗi cùng lúc.
ANH_CHE_DO_MA = ("t2i", "edit", "subject")


def curl_anh_ba_buoc() -> str:
    """Three calls that make one image — copy-paste runnable.

    🔴 WHY THIS EXISTS. Measured 25/08: the only public integration page
       mentioned `ltt_llm` 16 times and `image.ltt` **zero**. We sell two things
       and advertise one.

    ⚠️ Step 3 reads the artifact from `outputs[]`, **not** from `result` — the
       exact place a real call stumbled while following the old docs.
    """
    than = _json(ANH_INPUT).replace("\n", " ").replace("  ", " ")
    goi_1 = f'{{"tool": "{ANH_TOOL}", "input": {than}}}'
    goi_2 = (f'{{"tool": "{ANH_TOOL}", "quote": "<quote from step 1>", '
             f'"input": {than}}}')
    return "\n".join([
        "# 1. Quote - cheap, never charged, safe to repeat",
        f'curl -X POST "${ENV_BASE_URL}/api/v1/quotes" \\',
        f'  -H "Authorization: Bearer ${ENV_API_KEY}" \\',
        '  -H "Content-Type: application/json" \\',
        f"  -d '{goi_1}'",
        "",
        "# 2. Run - send that quote back, plus ONE Idempotency-Key.",
        "#    Reuse the SAME key on every retry of this call: a new key is a",
        "#    second job and a second charge.",
        f'curl -X POST "${ENV_BASE_URL}/api/v1/jobs" \\',
        f'  -H "Authorization: Bearer ${ENV_API_KEY}" \\',
        '  -H "Content-Type: application/json" \\',
        '  -H "Idempotency-Key: $(uuidgen)" \\',
        f"  -d '{goi_2}'",
        "",
        "# 3. Poll until done. Artifacts live in outputs[], NOT in result.",
        f'curl "${ENV_BASE_URL}/api/v1/jobs/<job_id>" \\',
        f'  -H "Authorization: Bearer ${ENV_API_KEY}"',
        '#   -> {"status": "succeeded",',
        '#       "outputs": [{"id": "<job_id>.image_keys.0",',
        '#                    "field": "image_keys", "index": 0}]}',
        "",
        f'curl "${ENV_BASE_URL}/api/v1/artifacts/<outputs[0].id>" \\',
        f'  -H "Authorization: Bearer ${ENV_API_KEY}"',
        '#   -> {"url": "...", "expires_in": ...}   download that url',
    ])


def openai_python_chat() -> str:
    """As close to "point the SDK at us" as it gets — and the one line to add."""
    return (
        "# pip install openai\n"
        "import os, uuid\n"
        "from openai import OpenAI\n"
        "\n"
        "client = OpenAI(\n"
        f'    api_key=os.environ["{ENV_API_KEY}"],\n'
        f'    base_url=os.environ["{ENV_BASE_URL}"].rstrip("/") + "/api/v1",\n'
        ")\n"
        "\n"
        "answer = client.chat.completions.create(\n"
        f'    model="{CHAT_MODEL}",\n'
        f'    messages=[{{"role": "user", "content": "{CHAT_PROMPT}"}}],\n'
        "    max_tokens=300,\n"
        "    # REQUIRED. The OpenAI SDK does not send this header for you, so\n"
        "    # leaving it out is a 400. Generate it ONCE per call and reuse the\n"
        "    # same value on every retry of that call: it is what stops a network\n"
        "    # timeout from buying the same generation twice.\n"
        '    extra_headers={"Idempotency-Key": uuid.uuid4().hex},\n'
        ")\n"
        "\n"
        "print(answer.choices[0].message.content)\n"
        'print("charged:", answer.model_extra["x_ltt"]["credit_charged"], "credit")\n'
        "\n"
        "# Do NOT put the key in the client's default_headers. That makes it one\n"
        "# key for every call, and it fails in two ways: a different prompt gets\n"
        "# 409, and an identical prompt silently returns the FIRST answer again\n"
        "# without running anything. The key belongs to a call, not to a client."
    )


def openai_typescript_chat() -> str:
    return (
        "// npm i openai\n"
        'import OpenAI from "openai";\n'
        'import { randomUUID } from "node:crypto";\n'
        "\n"
        "const client = new OpenAI({\n"
        f"  apiKey: process.env.{ENV_API_KEY},\n"
        f"  baseURL: `${{process.env.{ENV_BASE_URL}}}/api/v1`,\n"
        "});\n"
        "\n"
        "const answer = await client.chat.completions.create(\n"
        "  {\n"
        f'    model: "{CHAT_MODEL}",\n'
        f'    messages: [{{ role: "user", content: "{CHAT_PROMPT}" }}],\n'
        "    max_tokens: 300,\n"
        "  },\n"
        "  // REQUIRED — the SDK does not send this header for you. One key per\n"
        "  // call, reused unchanged on every retry of that same call.\n"
        '  { headers: { "Idempotency-Key": randomUUID() } },\n'
        ");\n"
        "\n"
        "console.log(answer.choices[0].message.content);\n"
        'console.log("charged:", (answer as any).x_ltt.credit_charged, "credit");'
    )


def python_chat_snippet() -> str:
    """No dependencies, for anyone who would rather not add one."""
    return (
        "import os, uuid, json, urllib.request\n"
        "\n"
        f'BASE = os.environ["{ENV_BASE_URL}"].rstrip("/") + "/api/v1"\n'
        "\n"
        "def chat(messages, max_tokens=300, key=None):\n"
        f'    body = json.dumps({{"model": "{CHAT_MODEL}", "messages": messages,\n'
        '                       "max_tokens": max_tokens}).encode()\n'
        f'    request = urllib.request.Request(BASE + "{CHAT_PATH}", data=body,\n'
        '        method="POST",\n'
        f'        headers={{"Authorization": "Bearer " + os.environ["{ENV_API_KEY}"],\n'
        '                 "Content-Type": "application/json",\n'
        "                 # REQUIRED. Cloudflare refuses the default urllib\n"
        "                 # User-Agent with 403 before it reaches us.\n"
        '                 \"User-Agent\": \"my-app/1.0\",\n'
        '                 "Idempotency-Key": key or uuid.uuid4().hex})\n'
        "    with urllib.request.urlopen(request) as response:\n"
        "        return json.loads(response.read())\n"
        "\n"
        f'answer = chat([{{"role": "user", "content": "{CHAT_PROMPT}"}}])\n'
        'print(answer["choices"][0]["message"]["content"])\n'
        'print("charged:", answer["x_ltt"]["credit_charged"], "credit",\n'
        '      "· held:", answer["x_ltt"]["credit_held"])'
    )


def powershell_chat_snippet() -> str:
    return (
        f'$base = "$env:{ENV_BASE_URL}/api/v1"\n'
        "$head = @{\n"
        f'  Authorization     = "Bearer $env:{ENV_API_KEY}"\n'
        '  "Idempotency-Key" = [guid]::NewGuid().ToString()   # one key per CALL\n'
        "}\n"
        "$body = @{\n"
        f'  model      = "{CHAT_MODEL}"\n'
        f'  messages   = @(@{{ role = "user"; content = "{CHAT_PROMPT}" }})\n'
        "  max_tokens = 300\n"
        "} | ConvertTo-Json -Depth 8\n"
        "\n"
        f'$answer = Invoke-RestMethod -Method Post -Uri "$base{CHAT_PATH}" -Headers $head `\n'
        '  -ContentType "application/json" -Body $body\n'
        "$answer.choices[0].message.content\n"
        '"charged: $($answer.x_ltt.credit_charged) credit"'
    )


def raw_http_chat_snippet() -> str:
    return (f"POST /api/v1{CHAT_PATH} HTTP/1.1\n"
            f"Host: app.lttstudios.com\n"
            f"Authorization: Bearer <{ENV_API_KEY}>\n"
            f"Content-Type: application/json\n"
            f"Idempotency-Key: 8f14e45f-ea0b-4b3f-8c1a-0f9d2e6c7a10\n"
            f"\n{_json(_chat_body())}")


def chat_snippets() -> tuple:
    """Every chat-door example, in the order people actually try them."""
    return (
        ("Python — OpenAI SDK", openai_python_chat()),
        ("TypeScript — OpenAI SDK", openai_typescript_chat()),
        ("cURL", curl_chat()),
        ("Python — no dependencies", python_chat_snippet()),
        ("PowerShell", powershell_chat_snippet()),
        ("HTTP", raw_http_chat_snippet()),
    )


#: Where the chat door differs from the job door. Written down rather than left
#: for the reader to trip over, because every one of these has a failure mode.
CHAT_DIFFERENCES = (
    ("No quote",
     "The price depends on how many tokens the model produces, and that number "
     "does not exist when you call. The platform holds a CEILING before it "
     "touches the model and then charges the measured usage, so "
     "x_ltt.credit_charged is usually well below x_ltt.credit_held. If you "
     "need the price before the work runs, use POST /api/v1/quotes and the job "
     "door."),
    ("Idempotency-Key is required, not optional",
     "With no quote it is the only thing standing between a network retry and "
     "paying twice. The OpenAI SDK does NOT send this header for you — add it "
     "per call. Leaving it out is a 400 that says exactly what to do."),
    ("One key per CALL, not per client",
     "A fixed key in default_headers breaks in two ways: a different prompt "
     "gets 409, and an identical prompt silently returns the FIRST answer "
     "again with nothing to show for it. Generate the key right before the "
     "call, and reuse it only when retrying that same call."),
    ("There is a time budget, so there is a max_tokens ceiling",
     "The call has to finish inside the server's synchronous budget, so "
     "max_tokens is capped. Asking for more is refused immediately with a "
     "400 naming the number, rather than cut off half-written. For longer "
     "generations submit the same work to POST /api/v1/jobs, which has no such "
     "ceiling."),
    ("No streaming yet",
     '"stream": true is refused with 400. Accepting it and answering without '
     "a stream would break the SDK somewhere much harder to trace, so the "
     "server says so plainly."),
    ("Busy is 503, not 429",
     "503 means the machine cannot serve right now — you are NOT charged, and "
     "Retry-After says when to come back. 429 means something else entirely: "
     "you are calling too fast, or you hit an account limit."),
)


# ── Plugging a coding CLI into the API (Q107) ────────────────────────────────
#
# The lesson these exist for: what stops a developer is almost never the
# protocol, it is filling in a config file correctly. Two base URLs that differ
# by four characters, a model name that must match exactly, and one environment
# variable that has to be set at user level rather than in a shell — each of
# those is a silent failure with an unhelpful symptom.
#
# 🔴 THE TWO BASE URLs ARE NOT A TYPO. The clients append different suffixes:
#
#     Codex        base_url + "/responses"      -> needs …/api/v1
#     Claude       base    + "/v1/messages"     -> needs …/api
#
#   Swap them and Codex asks for /api/responses (404) while Claude asks for
#   /api/v1/v1/messages (404). Same host, same key, four characters apart.
#
# No snippet here contains a key, for the same reason as every other snippet in
# this module: they read the environment, and the tests refuse anything that
# looks like a literal credential.

#: The model alias a customer types. Deliberately the public alias, never the
#: internal id — a customer who pins to the internal id is a customer we cannot
#: move to a different model later without breaking them (test_212).
CLI_MODEL = "ltt_llm"

#: The route name Claude Desktop needs — and it is a **route name**, not a
#: product name. Everything a customer buys is still `ltt_llm`.
#:
#: Claude Desktop in `gateway` mode filters the model list before drawing the
#: picker: a name that does not contain `claude`, `anthropic`, or a Claude family
#: word is dropped. `ltt_llm` is dropped, the picker ends up empty, and the send
#: button then does nothing at all — no log line, no toast, no banner. Measured
#: 2026-08-24 against the shipped build; see `server.api.streaming` for the rule
#: as read out of the app's own bundle.
#:
#: The filter only asks that the name *contain* `claude`; it does not ask for a
#: real Anthropic model. So this name clears the gate without borrowing another
#: company's product name.
DESKTOP_MODEL = "ltt-llm-claude-compat"


def _goc(base_url: str) -> str:
    return (base_url or "https://app.lttstudios.com").rstrip("/")


def codex_config(base_url: str) -> str:
    """`~/.codex/config.toml` — the provider block. Additive; changes nothing else."""
    return (
        "# ~/.codex/config.toml — add this, change nothing above it.\n"
        "# Your existing default `model` stays the default; only\n"
        "# `codex --profile ltt` goes to LTT Studios.\n"
        "[model_providers.ltt]\n"
        'name = "LTT Studios"\n'
        f'base_url = "{_goc(base_url)}/api/v1"   # with /v1 — Codex appends /responses\n'
        f'env_key = "{ENV_API_KEY}"\n'
        'wire_api = "responses"                  # the only value Codex supports\n'
        "stream_idle_timeout_ms = 600000"
    )


def codex_profile() -> str:
    """`~/.codex/ltt.config.toml` — a separate file, and that is not optional.

    Codex 0.145 refuses `[profiles.X]` inside `config.toml` outright:
    *"cannot be used while config.toml contains legacy `[profiles.ltt]` config"*.
    """
    return (
        "# ~/.codex/ltt.config.toml — a SEPARATE file.\n"
        "# Codex 0.145+ refuses [profiles.ltt] inside config.toml.\n"
        f'model = "{CLI_MODEL}"\n'
        'model_provider = "ltt"\n'
        '# Left at its default the model spends most of max_tokens thinking\n'
        '# before it answers.\n'
        'model_reasoning_effort = "low"\n'
        'model_reasoning_summary = "none"\n'
        "model_context_window = 65536"
    )


def claude_code_env(base_url: str) -> str:
    """Claude Code CLI reads plain environment variables."""
    return (
        f'$env:ANTHROPIC_BASE_URL = "{_goc(base_url)}/api"   # NO /v1 — the client adds it\n'
        f'$env:ANTHROPIC_AUTH_TOKEN = $env:{ENV_API_KEY}\n'
        f'$env:ANTHROPIC_MODEL = "{CLI_MODEL}"\n'
        f'$env:ANTHROPIC_DEFAULT_HAIKU_MODEL = "{CLI_MODEL}"   # background work'
    )


def claude_code_settings(base_url: str) -> str:
    """`~/.claude/settings.json` — survives a new terminal."""
    return _json({
        "env": {
            "ANTHROPIC_BASE_URL": f"{_goc(base_url)}/api",
            "ANTHROPIC_AUTH_TOKEN": "<your ltt_sk_… key>",
            "ANTHROPIC_MODEL": CLI_MODEL,
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": CLI_MODEL,
        }
    })


def vscode_claude_settings(base_url: str) -> str:
    """Settings the **Claude Code VS Code extension** needs — not the same as the CLI.

    Measured on a clean VM, 2026-08-24: after configuring the CLI correctly, the
    extension still showed a **Sign In** screen. It does **not** pick up
    `ANTHROPIC_BASE_URL` from the OS the way the CLI does — a known regression
    since extension v2.0.0 (anthropics/claude-code issues #9010, #38430).

    The extension ships two settings of its own to work around it. Both names
    were read from the installed extension's ``package.json``, not from a blog
    post: an article we checked used ``claude-code.*`` and the real prefix is
    ``claudeCode.*``.

    ``claudeCode.environmentVariables`` is declared ``scope: "machine"``, so it
    only takes effect in **User** settings. Put it in a workspace
    ``.vscode/settings.json`` and nothing happens, with no error.
    """
    return (
        "{\n"
        '  "claudeCode.disableLoginPrompt": true,\n'
        '  "claudeCode.environmentVariables": [\n'
        '    {"name": "ANTHROPIC_BASE_URL", "value": "' + base_url + '/api"},\n'
        f'    {{"name": "ANTHROPIC_MODEL", "value": "{CLI_MODEL}"}},\n'
        f'    {{"name": "ANTHROPIC_DEFAULT_HAIKU_MODEL", "value": "{CLI_MODEL}"}}\n'
        "  ]\n"
        "}"
    )


def vscode_codex_config(base_url: str) -> str:
    """Config the **Codex VS Code extension** needs — root level, no profile.

    The extension has no provider settings at all (checked in its
    ``package.json``); it drives the Codex CLI and therefore reads
    ``~/.codex/config.toml``. But it has no way to pass ``--profile``.

    And a profile cannot be selected from the file either. Codex 0.145 rejects it
    outright::

        Error: legacy `profile = "ltt"` config is no longer supported;
               use `--profile ltt` with `ltt.config.toml` instead

    So for the extension the provider has to sit at the **root** of
    ``config.toml``. The trade-off is real and must be stated: this makes LTT the
    **default** for ``codex`` on the command line too, whereas the profile form
    leaves the customer's default untouched.
    """
    return (
        f'# Root level - REPLACES your default model for `codex` too.\n'
        f'# Use the profile form instead if you only want the CLI.\n'
        f'model = "{CLI_MODEL}"\n'
        f'model_provider = "ltt"\n'
        f'model_reasoning_effort = "low"\n'
        f'model_context_window = 65536\n'
        f'\n'
        f'[model_providers.ltt]\n'
        f'name = "LTT Studios"\n'
        f'base_url = "{base_url}/api/v1"\n'
        f'env_key = "{ENV_API_KEY}"\n'
        f'wire_api = "responses"\n'
        f'stream_idle_timeout_ms = 600000\n'
    )


#: Cai bay lon nhat cua phan tien ich, viet ra de khach khoi tu phat hien.
VSCODE_BAY = (
    "The extensions do NOT read OS environment variables the way the CLIs do. "
    "Configuring the CLI is not enough - see the two blocks above.",
    "Restart VS Code completely after any change. `setx` only affects NEW "
    "processes, and on Windows an already-running Explorer hands the old "
    "environment to everything you launch from the Start menu.",
    "Put the Claude settings in USER settings.json, not a workspace one: the "
    "setting is scope:machine and is silently ignored elsewhere.",
)


def claude_desktop_registry(base_url: str) -> str:
    r"""Claude Desktop on Windows: an OS **policy**, not an app config file.

    The app's runtime settings live in Electron's LevelDB and cannot be edited by
    hand. But the **third-party inference** section is read from OS-managed
    policy - a .mobileconfig on macOS, the **registry** on Windows. That is the
    enterprise deployment path and it is stable.

    Until we found this, the Claude Desktop section of our own guide said "manual
    entry only", which was wrong.

    Four rules from the official reference. Each of them fails **silently**:

    * `inferenceGatewayBaseUrl` is the **origin**; the app appends
      `/v1/messages` itself. Shipping `/v1` in the value yields
      `/v1/v1/messages` and a 404 with no other clue.
    * HTTPS is **required** (loopback excepted).
    * Config is read **once at launch**, so the app must be fully quit, not just
      closed to the tray.
    * A policy under `HKEY_LOCAL_MACHINE` makes the app ignore the
      `HKEY_CURRENT_USER` one **entirely**.
    """
    khoa = r"[HKEY_CURRENT_USER\SOFTWARE\Policies\Claude]"
    mo = '[{\\"name\\": \\"' + DESKTOP_MODEL + '\\"}]'
    dong = [
        "Windows Registry Editor Version 5.00",
        "",
        khoa,
        '"inferenceProvider"="gateway"',
        '"inferenceGatewayBaseUrl"="' + base_url + '/api"',
        '"inferenceGatewayApiKey"="<your ltt_sk_... key>"',
        '"inferenceGatewayAuthScheme"="bearer"',
        '"inferenceModels"="' + mo + '"',
        '"modelDiscoveryEnabled"="false"',
        # Without this the app opens only its Code tab, which starts a local
        # agent session instead of talking to the gateway — and with no local
        # runtime installed it sends nothing at all, silently.
        '"chatTabEnabled"="true"',
    ]
    return "\n".join(dong) + "\n"


def claude_desktop_steps(base_url: str) -> tuple:
    """Claude Desktop does NOT read ANTHROPIC_BASE_URL. It has its own form."""
    return (
        ("Open the window",
         "Help → Troubleshooting → Enable Developer Mode, then "
         "Developer → Configure Third-Party Inference…  (on Windows the app menu "
         "is the ☰ button at the top left of the sign-in screen)"),
        ("Inference provider", "Gateway"),
        ("Gateway base URL", f"{_goc(base_url)}/api"),
        ("Gateway API key", "your ltt_sk_… key"),
        ("Gateway auth scheme", "Bearer"),
        ("inferenceModels", DESKTOP_MODEL),
        ("Finish", "Apply locally, then let the app relaunch"),
    )


#: Where each client trips, written down instead of left to be discovered.
CLI_BAY = (
    ("The two base URLs differ by four characters",
     "Codex needs the one ending in /api/v1 because it appends /responses. "
     "Claude Code and Claude Desktop need the one ending in /api because they "
     "append /v1/messages. Swapping them produces a 404 with no other clue."),
    ("Set the key at user level, not in one terminal",
     "A shell variable is invisible to the VS Code extension and to Claude "
     "Desktop, because those are separate processes. Use setx on Windows or your "
     "shell profile, then restart the app."),
    ("ANTHROPIC_DEFAULT_HAIKU_MODEL is not optional",
     "Claude Code uses a second, smaller model for background work — summaries, "
     "session titles. Leave it unset and those calls ask for a Claude model this "
     "API does not serve, and fail quietly while the main session looks fine."),
    ("Claude Desktop ignores ANTHROPIC_BASE_URL",
     "It reads its own Third-Party Inference configuration instead. Setting the "
     "environment variable there does nothing at all."),
    ("Claude Desktop takes a different model name from every other client",
     f"It keeps only names containing claude, anthropic, or a Claude family "
     f"word, and drops the rest before the picker is drawn — so ltt_llm is "
     f"discarded, the picker ends up empty, and the send button silently stops "
     f"working. Give it {DESKTOP_MODEL}: the same model, under the one name "
     f"that clears its filter."),
    ("Only /responses requires streaming",
     'It is a streaming route: send "stream": true. POST /api/v1/messages '
     "serves both, and POST /api/v1/chat/completions is the plain "
     "request-response route the SDKs call."),
    ("A retry costs money",
     "These routes take no Idempotency-Key, because no CLI sends one. You are "
     "billed for the tokens actually produced, so an abandoned stream bills for "
     "what it generated — and a retry generates again."),
)


# ── Ho so TUNG BE MAT — cho trang cam kieu "chon mot, thay dung phan cua minh"
#
# 🔴 VI SAO CO KHOI NAY. Trang cam cu xep chong MOI be mat len nhau: nam khu,
#    muoi the, 133 dong. Khach cam Codex van phai cuon qua ca phan Claude
#    Desktop, va — te hon — van co the CHEP NHAM doan cua be mat khac. Hai gia
#    tri nguy hiem nhat cua ca khu API deu KHAC NHAU giua cac be mat:
#
#        dia chi   /api/v1  (Codex)   ><   /api  (Claude Code, Desktop)
#        model     ltt_llm            ><   ltt-llm-claude-compat (Desktop)
#
#    Xep chong nghia la ca hai gia tri cung nam tren man hinh cung luc, khong
#    co gi noi cai nao la cua ai. Do la mot cai bay do chinh trang huong dan
#    dung len.
#
# ⭐ Cach chua, doc duoc tu `api.nghimmo.com/huongdan` (soi that 25/08): MOT o
#    chon o dau, va TOAN BO ben duoi ve lai — dia chi, canh bao, ten model, cac
#    buoc. Do khi bam tu "Key Claude" sang "Key Codex": base URL doi, dong canh
#    bao doi, bang model doi, va ca bo tab cai dat doi theo. Khach khong bao gio
#    nhin thay thu khong ap dung cho minh.
#
# ⚠️ Ham nay KHONG sinh ra gia tri moi — no chi GOM lai nhung thu da co o tren.
#    Them mot nguon thu hai cho cung mot dia chi la cach hai nguon lech nhau.

#: Ma be mat → nhan hien thi. Tach rieng de test doi chieu duoc hai chieu.
BE_MAT_MA = ("codex", "claude-code", "vscode", "desktop", "http")

#: Ma buoc → doan ma. Tach khoi VAN XUOI co chu dich, xem `be_mat_cam`.
BUOC_MA = ("codex-config", "codex-profile", "dat-khoa", "env", "settings",
           "vscode-claude", "vscode-codex", "reg", "curl")


def be_mat_cam(base_url: str) -> tuple:
    """Mot ban ghi cho MOI be mat: dia chi, ten model, cac buoc.

    ⛔ KHONG co van xuoi hien thi o day, va do la mot chot chu khong phai mot
       thieu sot. Module nay sinh DOAN MA va co y khong co bo dich — mot cau
       tieng Viet viet o day se hien ra mat dau tren trang, dung nhu lan
       25/08 da mac. Van xuoi nam trong `_cam_chon.html`, boc trong `_()`.

    ⇒ Ban ghi chi mang thu KHONG dich duoc: dia chi, ten model, ten san pham,
      ten giao thuc, duong dan tep, va chinh cac doan ma.
    """
    goc = _goc(base_url)
    return (
        {"ma": "codex", "ten": "Codex CLI", "the": "OPENAI RESPONSES",
         "dia_chi": f"{goc}/api/v1", "model": CLI_MODEL,
         "buoc": (("codex-config", "~/.codex/config.toml", codex_config(goc)),
                  ("codex-profile", "~/.codex/ltt.config.toml", codex_profile()),
                  ("dat-khoa", None, f'setx {ENV_API_KEY} "<...>"')),
         "chay": "codex --profile ltt"},
        {"ma": "claude-code", "ten": "Claude Code (CLI)", "the": "ANTHROPIC MESSAGES",
         "dia_chi": f"{goc}/api", "model": CLI_MODEL,
         "buoc": (("env", None, claude_code_env(goc)),
                  ("settings", "~/.claude/settings.json", claude_code_settings(goc))),
         "chay": "claude"},
        # 🔴 BE MAT DUY NHAT PHUC VU HAI TIEN ICH, VA CHUNG DUNG HAI DIA CHI.
        #
        #    Ban dau khu nay khai mot dia chi `/api`, trong khi doan ma Codex
        #    ben trong no dung `/api/v1`. Tuc bang "Ket noi" **noi dung mot nua
        #    khu va sai nua con lai** — khach doc dong dia chi roi chep doan ma
        #    Codex se cam theo hai gia tri khong khop nhau.
        #
        #    `test_303` bat duoc bang cach doi chieu dia chi KHAI voi dia chi
        #    NAM TRONG doan ma. Do khong phai mot chi tiet trinh bay: no la
        #    dung cai bay ma ca trang cam duoc dung lai de dong.
        #
        # ⇒ Khu nao phuc vu nhieu hon mot cong cu thi khai `dia_chi_theo`, va
        #   bang Ket noi ve MOT DONG CHO MOI cong cu.
        {"ma": "vscode", "ten": "VS Code", "the": "CAU HINH RIENG",
         "dia_chi": f"{goc}/api", "model": CLI_MODEL,
         "dia_chi_theo": (("Claude Code", f"{goc}/api", CLI_MODEL),
                          ("Codex", f"{goc}/api/v1", CLI_MODEL)),
         "buoc": (("vscode-claude", "settings.json", vscode_claude_settings(goc)),
                  ("vscode-codex", "~/.codex/config.toml", vscode_codex_config(goc))),
         "chay": None},
        {"ma": "desktop", "ten": "Claude Desktop", "the": "REGISTRY",
         "dia_chi": f"{goc}/api", "model": DESKTOP_MODEL,
         "buoc": (("reg", ".reg", claude_desktop_registry(goc)),),
         "chay": None},
        {"ma": "http", "ten": "cURL", "the": "HTTP",
         "dia_chi": f"{goc}/api/v1", "model": CLI_MODEL,
         "buoc": (("curl", None, curl_chat()),),
         "chay": None},
    )

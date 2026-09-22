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

from platform_core.i18n import N_
from platform_core.llm import canonical

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
    _drop_mutually_exclusive(tool, payload)
    return payload


def _drop_mutually_exclusive(tool, payload: dict) -> None:
    """Keep the example a VALID call when the tool forbids a pair together.

    A param may declare ``exclusive_with`` (e.g. ``speech.ltt``: ``voice_id`` vs
    ``preset``): sending both is rejected by ``validate_public_input`` before any
    money moves. ``example_input`` fills every param that has a declared example,
    so without this it would print both and the pasted example would 400 — the
    exact "example worse than no example" failure EXT-07 tests for.

    ⛔ Reads the INTERNAL schema — the same declaration the validator enforces —
       not the public one: ``exclusive_with`` is an internal contract between app
       and platform, so it is deliberately absent from ``to_public_dict`` and
       moves no ``contract_hash``. When both sides of a pair are present, the one
       that *declares* the constraint is kept and its siblings dropped.
    """
    from platform_core.registry import discover

    schema = None
    for item in discover():
        if item.error or item.manifest.slug != getattr(tool, "app_slug", ""):
            continue
        for spec in item.manifest.tools:
            if spec.job_type == getattr(tool, "job_type", "") and (
                    spec.name == tool.name
                    or (spec.api_contract or {}).get("public_name") == tool.name):
                schema = spec.params_schema
                break
    if not schema:
        return
    for param, khai in schema.items():
        if param not in payload or not isinstance(khai, dict):
            continue
        for other in (khai.get("exclusive_with") or ()):
            payload.pop(str(other), None)


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

#: 🔑 DẪN TỪ `canonical`, KHÔNG GÕ TAY. Xem `CLI_MODELS` ngay dưới để biết vì sao.
CHAT_MODEL = canonical.MODEL_MAC_DINH
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
    # 🔴 MỤC NÀY TỪNG GHI "No streaming yet", VÀ NÓ ĐÃ SAI TỪ 24/08.
    #
    #    Streaming sống trên hai cửa khác từ hôm đó, và chính máy chủ trả về câu
    #    chỉ đúng hai cửa ấy khi bạn gửi `stream: true` vào cửa này. Nghĩa là
    #    **tài liệu mâu thuẫn với thông điệp lỗi của chính hệ thống** — khách
    #    đọc "chưa có streaming" thì không thử, và không bao giờ tìm ra hai cửa
    #    họ cần để cắm Codex hay Claude Code.
    #
    # ⭐ Đo lại qua Cloudflare 30/08, cả ba cửa cùng một khoá:
    #      /v1/chat/completions            200 application/json
    #      /v1/chat/completions stream     400 (chỉ sang hai cửa dưới)
    #      /v1/messages         stream     200 text/event-stream, 66 khối SSE
    #      /v1/responses        stream     200 text/event-stream, 63 khối SSE
    ("Streaming lives on two other doors, not this one",
     '"stream": true here is refused with 400 — and the 400 names where to go: '
     "POST /api/v1/messages (Anthropic Messages shape, what Claude Code "
     "speaks) or POST /api/v1/responses (OpenAI Responses shape, what Codex "
     "speaks). Both return text/event-stream. This door stays single-JSON on "
     "purpose: answering a stream request without a stream would break the SDK "
     "somewhere much harder to trace."),
    ("Three doors, and you pick by what your client speaks",
     "POST /api/v1/jobs — asynchronous, has a quote, no max_tokens ceiling; "
     "use it for long generations. POST /api/v1/chat/completions — one round "
     "trip, one JSON answer, priced after the fact. POST /api/v1/messages and "
     "POST /api/v1/responses — streaming, and these are the two a coding CLI "
     "plugs into. Same model, same key, same ledger behind all of them."),
    ("Read the 429 code, scope and reason before retrying",
     "`rate_limited` with reason `request_rate` or `create_rate` means the key "
     "or account called too fast. `concurrency_limited` with scope `execution` "
     "means the selected model lane is busy; its reason distinguishes a full "
     "waiting room from an upstream 429. In every case reuse the same request, "
     "honour Retry-After and do not increase concurrency. 503 means the model "
     "is unavailable rather than rate limited. Rejected requests are not charged."),
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

#: Every public alias a customer may type, in the order the pages list them.
#:
#: 🔴 THIS TUPLE IS DERIVED, AND THE DERIVATION IS THE POINT. Until 2026-09-12
#:    this module knew about exactly one model and said so in four hand-typed
#:    places. The platform had shipped a second one (`ltt-3.5`) days earlier, so
#:    every public page — connect guide, plug-in tool, developer portal — showed
#:    a **one-model product** while the catalogue, the price table and the
#:    billing ledger all knew about two. A customer could not discover the model
#:    they were already being charged different rates for.
#:
#: ⭐ Reading it off `canonical.ALIAS_SANG_ID` means the pages cannot lag the
#:    platform again: adding a third profile updates the guide in the same
#:    commit that adds the model, because there is no second list to remember.
#:
#: ⚠️ Left-hand side only — public aliases, never the internal ids behind them.
#:    A customer who pins to `qwen38-api` is a customer we cannot move to another
#:    model without breaking them (test_212). That is what the alias layer buys.
CLI_MODELS: tuple[str, ...] = tuple(canonical.MODEL_HOP_LE)

#: The one a customer gets when they say nothing. Same source, same reason.
CLI_MODEL = canonical.MODEL_MAC_DINH

#: The route name Claude Desktop needs — and it is a **route name**, not a
#: product name. Everything a customer buys is still `ltt-3.8` / `ltt-3.5`.
#:
#: Claude Desktop in `gateway` mode filters the model list before drawing the
#: picker: a name that does not contain `claude`, `anthropic`, or a Claude family
#: word is dropped. `ltt-3.8` is dropped, the picker ends up empty, and the send
#: button then does nothing at all — no log line, no toast, no banner. Measured
#: 2026-08-24 against the shipped build; see `server.api.streaming` for the rule
#: as read out of the app's own bundle.
#:
#: The filter only asks that the name *contain* `claude`; it does not ask for a
#: real Anthropic model. So this name clears the gate without borrowing another
#: company's product name.
#:
#: 🔑 ROUTE NAME → PUBLIC ALIAS. **The single source for both ends**:
#:    `server.api.streaming.TUYEN_TUONG_THICH` is built from this dict rather
#:    than repeating it, so the gateway that resolves the name and the page that
#:    prints it cannot disagree.
#:
#: 🔴 WHY A SECOND ROUTE EXISTS FROM 2026-09-12. There was exactly one, so
#:    Claude Desktop could reach exactly one of our two models — `ltt-3.5` was
#:    **unreachable from that client at any price**, because the only name that
#:    survives the picker filter resolved to `ltt-3.8`. Not a missing
#:    convenience: a product we sell with no door on one of its surfaces.
#:
#: ⚠️ The suffix is the alias' own distinguishing part, so a reader can see
#:    which model a route goes to without opening this file. Do not "tidy" the
#:    names to `-a` / `-b`: the name is what a customer pastes into a registry
#:    key, and it is the only place they will ever see which model they picked.
#:
#: ⛔ These are **route names of one client's protocol**, not product names. They
#:    do not belong in `canonical.ALIAS_SANG_ID`, and nothing in the catalogue,
#:    the price table or `/api/v1/tools` may print them as models for sale.
TUYEN_DESKTOP_CHINH: dict[str, str] = {
    "ltt-llm-claude-compat": "ltt-3.8",
    "ltt-llm-claude-compat-35": "ltt-3.5",
}
TUYEN_DESKTOP: dict[str, str] = dict(TUYEN_DESKTOP_CHINH)
NHAN_DESKTOP: dict[str, str] = {
    "ltt-llm-claude-compat": N_("LTT 3.8 (Mạnh)"),
    "ltt-llm-claude-compat-35": N_("LTT 3.5 (Nhanh)"),
}
#: Ánh xạ alias NỘI BỘ của Claude Desktop sang hai tuyến LTT. Đây không đổi
#: nhãn sản phẩm và không tuyên bố model nhà là model Anthropic. Nó chỉ bảo host
#: gửi việc nền `haiku` về tuyến nhanh và `opus` về tuyến mạnh, thay vì tự ghép
#: một model ID ngoài catalog mà gateway sẽ từ chối.
TANG_DESKTOP: dict[str, str] = {
    "ltt-llm-claude-compat": "opus",
    "ltt-llm-claude-compat-35": "haiku",
}

#: The route for the default model — what the Desktop surface shows by default.
DESKTOP_MODELS = tuple(TUYEN_DESKTOP_CHINH)
DESKTOP_MODEL = DESKTOP_MODELS[0]


def tuyen_desktop_cho(alias: str) -> str:
    """Public alias → the route name Claude Desktop must be given for it.

    ⛔ Raises rather than falling back to the default route. A wrong-but-plausible
       route name is the exact failure this whole mechanism exists to prevent:
       Desktop would answer from a model the customer did not pick, and the only
       symptom is a bill for the other price.
    """
    for tuyen, ten in TUYEN_DESKTOP.items():
        if ten == alias:
            return tuyen
    raise KeyError(f"khong co tuyen Desktop cho {alias!r} (co: {CLI_MODELS})")

#: Cửa sổ ngữ cảnh ta **công bố cho client**, và trần token ra.
#:
#: 🔴 ĐÂY LÀ BẢN SAO CÓ CHỦ Ý, KHÔNG PHẢI MỘT ĐỊNH NGHĨA THỨ HAI.
#:
#:    Nguồn chân lý là `apps/ltt_llm/ngan_sach.py`. Nhưng `platform_core`
#:    **không được** import `apps` — nền tảng không phụ thuộc app, và
#:    `test_147_layering` chốt điều đó. Nên hai con số này gõ lại ở đây, và việc
#:    đối chiếu là của TEST (`test_334::TestExamplesKhopNganSach`), đúng khuôn
#:    đã dùng cho `llm_gateway/config.py` và `tools/cam_cli.py`.
#:
#: ⛔ TRƯỚC 30/08 CHỖ NÀY GHI `65000`, VÀ TRANG CÔNG KHAI GHI `131K`. Cả hai đều
#:    sai và chúng mâu thuẫn nhau: `65000` bắt khách tự giới hạn thấp hơn thật
#:    26 nghìn token, còn `131K` hứa nhiều hơn thật 42 nghìn rồi để họ ăn **413**
#:    giữa hội thoại. Một con số gõ tay trong tài liệu bán hàng là một lời hứa.
#:
#: ✅ CHỦ DỰ ÁN CHỐT 22/09/2026: hạ số công bố để khớp TOKEN THẬT — chia cho
#:    `ngan_sach.HE_SO_UOC_TREN_THAT` thay vì bớt 8% cho lệch tokenizer. Xem
#:    `ngan_sach.cong_bo_cua` cho nguồn đo và lý do chọn hệ số.
CUA_SO_CONG_BO = 124_245
TOKEN_RA_TRAN = 32_768

#: Ngưỡng client **phải nén** hội thoại. Bản sao của `ngan_sach.NEN_CHO_CLIENT`,
#: cùng lý do và cùng cách đối chiếu như hai con số trên.
NEN_CLIENT = 91_477

#: Trần cho **một** kết quả công cụ, công bố vì nó đổi hành vi thấy được.
#:
#: ⛔ Không phải một chi tiết nội bộ: khách sẽ **thấy** kết quả một lệnh dài
#:    bị cắt ở giữa, và nếu trang này không nói trước thì họ báo đó là lỗi.
#:
#: 🔴 Và nó là hàng phòng thủ duy nhất chống một sự thật của cả hai client:
#:    chúng chỉ kiểm ngưỡng nén **giữa hai lượt**, không kiểm giữa các lần
#:    gọi công cụ trong cùng một lượt. Một kết quả không có trần thì một
#:    lượt duy nhất vượt được mọi khoảng dự trữ.
TRAN_KET_QUA_TOOL = 16_384


#: Năm con số của một hội thoại dài, và **vì sao chúng khác nhau**.
#:
#: 🔴 VÌ SAO PHẢI CÔNG KHAI CẢ NĂM. Trang này trước 03/09 không nói con số nào
#:    về ngữ cảnh, nên câu hỏi *"vì sao tôi ăn 413 giữa chừng"* không có chỗ nào
#:    trả lời — kể cả cho khách đã đọc hết trang. Và người ta đoán: đoán rằng
#:    `context_window` là thứ họ được phép gửi, rồi cấu hình client theo con số
#:    đó và hỏng đúng ở giữa một phiên dài.
#:
#: ⛔ ĐỪNG GỘP LẠI THÀNH MỘT SỐ. Chúng đo năm thứ khác nhau, và mỗi lần dự án
#:    này gộp hai trong số chúng lại thì kết quả là một lời hứa sai:
#:    `65000` bắt khách tự bó hẹp; `131K` hứa quá rồi để họ ăn 413; một con số
#:    dùng chung cho hai model có cửa sổ khác nhau hứa cho model nhỏ gấp 3,1 lần.
NGU_CANH_NAM_SO = (
    ("Engine context", "221,184",
     "What the model is loaded with on our GPU. You never send this much: "
     "input and output share this window."),
    ("Hard input limit", "186,368",
     "The most input we accept. Above it you get a 400 "
     "(`context_window_exceeded`) — never a silent truncation; a streaming "
     "Responses request instead gets a 200 with a terminal `response.failed` "
     "event (`context_length_exceeded`). It is the engine window minus the "
     "longest possible answer and a margin for token estimation."),
    ("Advertised context", f"{CUA_SO_CONG_BO:,}",
     "What you should configure your client with. It is the hard limit "
     "divided by 1.5, because the hard limit is computed from our own "
     "upper-bound token estimate at the gate, while this number must hold in "
     "REAL tokens as your client and the model count them; 1.5 is the worst "
     "observed ratio between the estimate and real usage."),
    ("Auto-compact at", f"{NEN_CLIENT:,}",
     "Where your client should summarise the conversation. It leaves room for "
     "one more full-length answer before the advertised ceiling, because a "
     "client only checks between turns."),
    ("Max output", f"{TOKEN_RA_TRAN:,}",
     "The most one answer can generate."),
    ("One tool result", f"{TRAN_KET_QUA_TOOL:,}",
     "The most a single command or tool result adds to the conversation. "
     "Longer output is trimmed in the middle, keeping the start and the end. "
     "Both clients check the compaction threshold only between turns, so "
     "without this ceiling one turn can outgrow every reserve."),
)

#: Vì sao một yêu cầu bị từ chối vì vượt trần ngữ cảnh (`400
#: context_window_exceeded`; Responses stream: `response.failed`), và **cách
#: sửa đúng chỗ**.
#:
#: ⛔ Không khuyên "xoá phiên rồi làm lại". Đó là cách chắc chắn để mất việc
#:    đang làm mà **không** sửa nguyên nhân — lần sau nó lặp lại y hệt.
LOI_413 = (
    ("Your client does not know our context window",
     "This is the common one. Codex without `model_catalog_json` assumes a "
     "272,000-token window and never compacts in time; Claude Code without "
     "`CLAUDE_CODE_MAX_CONTEXT_TOKENS` assumes 200,000 and says so in the "
     "session. Run our `cam` tool (or apply the manual config below) and start "
     "a new session — configuration is read at startup."),
    ("Claude Code: one variable is not enough",
     "`CLAUDE_CODE_MAX_CONTEXT_TOKENS` corrects the window Claude Code "
     "assumes, but it does not set the compaction threshold. Without "
     "`CLAUDE_CODE_AUTO_COMPACT_WINDOW`, Claude Code compacts only when the "
     "conversation reaches that window, which leaves less room than one full "
     "answer before our hard input limit. Set both."),
    ("Your client compacts, but too late",
     "If you configured the window by hand, check the compaction threshold "
     f"too: it must sit at least {TOKEN_RA_TRAN:,} tokens below the advertised "
     "window, because one turn can grow by a whole answer before your client "
     "gets to check again."),
    ("Your client is using the other model's profile",
     "Both models read images, but `ltt-3.5` has its own window and compact "
     "threshold, separate from `ltt-3.8`. The context-length error body carries the limit that "
     "actually applied, so read the number in the error rather than assuming."),
)

#: Ba cửa của `text.chat`, và **cửa nào cho việc gì**.
#:
#: 🔴 VÌ SAO NÓ PHẢI CÔNG KHAI. Cho tới 30/08 thông tin này chỉ nằm trong
#:    `CHAT_DIFFERENCES`, mà `CHAT_DIFFERENCES` chỉ hiện ở
#:    `/developers/quickstart` — **303 về `/login`** với khách ẩn danh.
#:
#:    Tức thứ trả lời câu *"tôi cắm được Codex/Claude Code vào đây không?"* —
#:    câu quyết định người ta có mua hay không — nằm sau cổng đăng ký. Đúng thứ
#:    tự sự của `server/routes/tai_lieu_api.py` sinh ra để sửa, chỉ là lần đó
#:    chưa áp cho mục này.
#:
#: ⛔ Và nó không mâu thuẫn với luật "/developers/* sau đăng nhập": danh mục,
#:    khoá và playground gắn với **một tài khoản**; còn "có ba cửa, cửa nào
#:    stream" là một **sự thật về sản phẩm**.
BA_CUA = (
    ("POST /api/v1/jobs", "asynchronous",
     "Has a quote before the work runs, and no max_tokens ceiling. Use it for "
     "long generations and when you want the price agreed up front."),
    ("POST /api/v1/chat/completions", "one JSON answer",
     "OpenAI Chat Completions shape. One round trip, priced after the fact "
     "against what the model actually produced. `stream: true` is refused "
     "here — the 400 points you at the two doors below."),
    ("POST /api/v1/messages", "streaming",
     "Anthropic Messages shape. This is what Claude Code speaks; returns "
     "text/event-stream."),
    ("POST /api/v1/responses", "streaming",
     "OpenAI Responses shape. This is what Codex speaks; returns "
     "text/event-stream."),
)

#: Tệp catalog model cho Codex — đường dẫn công cụ `cam` ghi ra.
#:
#: ⭐ Thiếu nó thì Codex **không có metadata** cho model nhà, rơi vào đường
#:    `compact_model_fallback` và mượn tên một model OpenAI cho lượt phụ; cổng
#:    của ta từ chối (fail-closed) và khách thấy "im lặng" ở hội thoại dài.
TEP_CATALOG_CODEX = r"C:\Users\YOUR_WINDOWS_USER\.codex\ltt_model_catalog.json"

# Mirrors app budgets without importing apps into platform_core. Tests compare
# every generated profile/catalog entry against apps/ltt_llm/ngan_sach.py.
CODEX_MODEL_LIMITS = {
    "ltt-3.8": (CUA_SO_CONG_BO, NEN_CLIENT),
    "ltt-3.5": (151_552, 118_784),
}

# Labels are product names shown to people.  Slugs remain the stable wire names
# stored in Codex thread history and sent to the gateway.
CODEX_MODEL_LABELS = {
    "ltt-3.8": "LTT 3.8 (Strong)",
    "ltt-3.5": "LTT 3.5 (Fast)",
}

# Codex requires one of its own effort enum values. Qwen3.5 only exposes
# thinking on/off, so `medium` is the neutral compatibility value understood by
# the pinned Froggeric template while the server keeps thinking enabled.
# ⭐ L-33 (chủ dự án 19/09 tối): 3.8 mặc định `medium` TOÀN nền tảng (model card
#    mặc định xhigh; đo LTTCODE lượt lập plan: medium ~½ thời gian và token ra).
#    Bảng này là mức MÁY CHỦ chèn khi request bỏ trống (`luong.chuan_hoa_suy_nghi`)
#    và mức catalog công bố; `ngan_sach.NGHI_MAC_DINH_THEO_MODEL` là bản sao đối
#    chiếu (`test_1430` buộc bằng nhau).
CODEX_MODEL_REASONING = {
    "ltt-3.8": "medium",
    "ltt-3.5": "medium",
}

# Values the Codex picker may offer. Codex requires this catalog field and
# sends its enum on every Responses request. Qwen3.5 has only thinking on/off;
# `medium` is the single transport label for thinking ON, not a native tier.
CODEX_MODEL_REASONING_LEVELS = {
    "ltt-3.8": ("low", "medium", "xhigh"),
    "ltt-3.5": ("medium",),
}

# ── ⭐ NGUỒN DUY NHẤT về mức suy nghĩ theo model (L-26, 18/09/2026) ───────────
#
# Catalog `/api/v1/models` (`server/api/tools._dang_codex`), catalog Codex cài
# trên máy khách (`codex_catalog`) và hàm chuẩn hoá mọi cửa
# (`runtime_noi_bo.luong.chuan_hoa_suy_nghi`) đều đọc ba bảng dưới + hai bảng
# trên. LTTCODE (Task 13) đọc danh sách mức từ `/api/v1/models`, không gõ cứng.
#
# Căn cứ (chủ dự án chốt 18/09: "giá trị theo khuyến nghị chính thức của model"):
#   * HF model card Qwen/Qwen3.8-27B: ba mức `xhigh` (mặc định), `medium`,
#     `low`, truyền qua `reasoning_effort`. Không có `high`.
#   * HF model card Qwen/Qwen3.5-9B: suy nghĩ BẬT mặc định, chỉ bật/tắt qua
#     `chat_template_kwargs.enable_thinking` — KHÔNG có mức effort.
#   * Template `llm_gateway/deploy/chat_template_v22.5.jinja` dòng 17-30: không
#     gửi effort ⇒ `medium` (prompt chính thức); `minimal`→low, `high|max`→xhigh.
#
# ⭐ CÁCH CLIENT HIỂN THỊ: model nằm trong `CODEX_MODEL_REASONING_CO_DINH` khai
#    đúng MỘT mức (`medium`, mô tả "Thinking on"). Đó là NHÃN CỐ ĐỊNH "Suy
#    nghĩ", không phải bộ chọn: client nên hiện một nhãn tĩnh và KHÔNG gửi
#    `reasoning_effort`. Gửi thì máy chủ vẫn nhận (Codex luôn gửi), gỡ trước
#    máy B và trả header `X-LTT-Effort-Bo-Qua: 1`.

#: Model chỉ có MỘT chế độ (suy nghĩ BẬT): effort được nhận rồi bỏ qua công khai.
CODEX_MODEL_REASONING_CO_DINH = frozenset({"ltt-3.5"})

#: Tên effort client hay gửi mà model không khai ⇒ mức gần nhất ĐÚNG CHIỀU,
#: cùng ánh xạ template v22.5 dòng 23-27 tự làm. Chỉ áp cho model có nấc.
REASONING_EFFORT_ALIASES = {"minimal": "low", "high": "xhigh", "max": "xhigh"}

#: Model cố định chấp nhận (rồi bỏ qua) đúng tập giá trị của model có nấc này,
#: để một client gửi cùng một effort cho hai model không nhận hai câu trả lời.
MODEL_EFFORT_THAM_CHIEU = "ltt-3.8"

#: Giá trị có nghĩa "tắt suy nghĩ" (template dòng 21-23) — bị CẤM ở mọi model:
#: đo 14/09 tắt suy nghĩ cho 2 token thay vì ~1.180 (L-02, `features.kiem_tham_so`).
REASONING_EFFORT_TAT = frozenset({"none", "off"})

_MO_TA_MUC = {"low": "Fast", "medium": "Balanced", "xhigh": "Deepest"}


def muc_suy_nghi(slug: str) -> list[dict]:
    """`supported_reasoning_levels` của một model — MỘT bản cho mọi catalog.

    Model cố định: một mục duy nhất mô tả "Thinking on" (hiển thị như nhãn,
    không phải bộ chọn — xem khối chú thích trên). Ném `KeyError` với slug lạ.
    """
    co_dinh = slug in CODEX_MODEL_REASONING_CO_DINH
    return [{"effort": effort,
             "description": "Thinking on" if co_dinh else _MO_TA_MUC[effort]}
            for effort in CODEX_MODEL_REASONING_LEVELS[slug]]

#: Bộ biến CHUẨN cho một phiên Claude Code Local chạy qua LTT Gateway.
#:
#: 🔴 Vì sao phải gom thành dữ liệu thay vì một khối chữ trong template. Danh
#:    sách này đã tăng từng dòng trong lúc chẩn lỗi, khiến người dùng phải sửa
#:    cấu hình nhiều lần và ba bề mặt (trang API, CLI, VS Code) bắt đầu lệch
#:    nhau. Từ Q126, code sinh cấu hình, trang hướng dẫn và test đều đọc cùng
#:    một bộ này; thêm hay bỏ một biến phải làm test "đúng 11 biến" đỏ.
#:
#: `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` đứng một mình có chủ ý trên Desktop:
#: Claude Code 2.1.257+ khi đó ép mọi subagent dùng model CHÍNH đang chọn. Không
#: ghim một tên model ở đây, vì picker Desktop phải tiếp tục đổi được giữa hai
#: tuyến LTT. CLI riêng sẽ đặt thêm `CLAUDE_CODE_SUBAGENT_MODEL` theo profile.
CLAUDE_LOCAL_COMMON_ENV: tuple[tuple[str, str], ...] = (
    ("CLAUDE_CODE_MAX_OUTPUT_TOKENS", str(TOKEN_RA_TRAN)),
    ("MAX_MCP_OUTPUT_TOKENS", str(TRAN_KET_QUA_TOOL)),
    ("CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS", "1"),
    ("CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH", "1"),
    ("CLAUDE_CODE_SUBAGENT_MODEL_FORCE", "1"),
    # Claude mặc định thử lại 10 lần và LTT GIỮ 10 (mặc định của client): hàng
    # chờ máy A trả 429 + Retry-After, nên thử lại theo nhịp đó không thành bão.
    # (Chú thích cũ ghi "LTT dùng 3" trong khi giá trị là 10 — sửa 18/09.)
    ("CLAUDE_CODE_MAX_RETRIES", "10"),
    ("API_TIMEOUT_MS", "600000"),
    ("CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK", "1"),
    ("ENABLE_TOOL_SEARCH", "false"),
)


def claude_local_env(model: str = CLI_MODEL) -> tuple[tuple[str, str], ...]:
    """Mười một dòng `.env` cho editor Local của Claude Desktop.

    Hai dòng đầu đổi theo model; chín dòng sau là hợp đồng dùng chung. Tên lạ
    ném `KeyError` thay vì rơi về 3.8, vì một preset mang ngân sách của model
    khác sẽ chỉ lộ ra bằng lỗi 413 giữa một phiên dài.

    🔴 `CLAUDE_CODE_AUTO_COMPACT_WINDOW` = CỬA SỔ CÔNG BỐ, không phải ngưỡng nén
       kiểu Codex (18/09, plan v2 Task 9, nhánh `phien/nen-claude-codex` 1b143291).
       Đo Claude Code 2.1.274: nó nén ở
       `min(AUTO_COMPACT_WINDOW, ctx) − min(MAX_OUTPUT_TOKENS, 20000) − 13000`
       — tức TỰ trừ phần ra và biên. Đưa nó ngưỡng Codex (`cửa sổ − 32.768`) là
       trừ phần ra HAI lần ⇒ nén sớm ~33K token. Codex giữ nguyên
       `model_auto_compact_token_limit` (= phần tử thứ hai của
       `CODEX_MODEL_LIMITS`), vì Codex dùng con số ấy trực tiếp.
    """
    context, _nen_codex = CODEX_MODEL_LIMITS[model]
    return (
        ("CLAUDE_CODE_MAX_CONTEXT_TOKENS", str(context)),
        ("CLAUDE_CODE_AUTO_COMPACT_WINDOW", str(context)),
        *CLAUDE_LOCAL_COMMON_ENV,
    )


#: Claude Code 2.1.274 (ĐO, Task 9, nhánh `phien/nen-claude-codex` 1b143291) nén ở
#: `min(AUTO_COMPACT_WINDOW, ctx) − min(MAX_OUTPUT_TOKENS, 20000) − 13000`.
CLAUDE_NEN_TRAN_RA = 20_000
CLAUDE_NEN_BIEN = 13_000


def claude_nguong_nen(model: str = CLI_MODEL) -> int:
    """Token ngữ cảnh mà Claude Code tự nén, với `claude_local_env(model)`."""
    env = dict(claude_local_env(model))
    cua_so = int(env["CLAUDE_CODE_AUTO_COMPACT_WINDOW"])
    ra = int(env["CLAUDE_CODE_MAX_OUTPUT_TOKENS"])
    return cua_so - min(ra, CLAUDE_NEN_TRAN_RA) - CLAUDE_NEN_BIEN


def claude_local_preset(model: str) -> tuple:
    """Một hàng bảng preset trang hướng dẫn: `(slug, MAX_CONTEXT, AUTO_COMPACT,
    nhãn mẫu số Context, % tự nén)` — dẫn xuất hết từ `claude_local_env`."""
    env = dict(claude_local_env(model))
    ctx = int(env["CLAUDE_CODE_MAX_CONTEXT_TOKENS"])
    cua_so = int(env["CLAUDE_CODE_AUTO_COMPACT_WINDOW"])
    return (model, ctx, cua_so, f"{cua_so / 1000:.1f}k",
            round(100 * claude_nguong_nen(model) / cua_so))


def claude_model_env(model: str = CLI_MODEL) -> tuple[tuple[str, str], ...]:
    """Mọi đường chọn model mà Claude Code 2.1.270 có thể tự dùng.

    `fable` và `default` là alias chính thức mới; thiếu chúng thì một thao tác
    nền hoặc lần fallback có thể gửi tên Anthropic ra gateway dù lượt chính đã
    ghim đúng LTT. Không có biến `ANTHROPIC_DEFAULT_MYTHOS_MODEL` trong bảng
    biến chính thức hiện tại, nên không bịa thêm một khóa không được client đọc.
    """
    if model not in CODEX_MODEL_LIMITS:
        raise KeyError(f"khong co ho so Claude cho {model!r}")
    return (
        ("ANTHROPIC_MODEL", model),
        ("ANTHROPIC_DEFAULT_MODEL", model),
        ("ANTHROPIC_DEFAULT_HAIKU_MODEL", model),
        ("ANTHROPIC_DEFAULT_OPUS_MODEL", model),
        ("ANTHROPIC_DEFAULT_SONNET_MODEL", model),
        ("ANTHROPIC_DEFAULT_FABLE_MODEL", model),
        ("CLAUDE_CODE_SUBAGENT_MODEL", model),
    )


def codex_catalog() -> str:
    """Copyable local metadata in the format accepted by Codex 0.145.0.

    This is not the OpenAI-shaped /v1/models listing. Omit the effective context
    percentage: CLI and IDE have incompatible types for that optional field.
    Unknown aliases fail rather than silently borrowing another model's budget.
    """
    models = []
    for slug in CLI_MODELS:
        context, compact = CODEX_MODEL_LIMITS[slug]
        models.append({
            "slug": slug, "display_name": CODEX_MODEL_LABELS[slug],
            "description": f"{CODEX_MODEL_LABELS[slug]} — LTT Studios",
            "default_reasoning_level": CODEX_MODEL_REASONING[slug],
            "supported_reasoning_levels": muc_suy_nghi(slug),
            "shell_type": "unified_exec", "visibility": "list",
            "supported_in_api": True, "priority": 1,
            "additional_speed_tiers": [], "service_tiers": [],
            "base_instructions": "",
            "include_skills_usage_instructions": False,
            "include_plugin_usage_instructions": False,
            "include_apps_usage_instructions": False,
            "supports_reasoning_summary_parameter": False,
            "default_reasoning_summary": "none", "support_verbosity": False,
            "apply_patch_tool_type": "freeform",
            "truncation_policy": {"mode": "tokens", "limit": TRAN_KET_QUA_TOOL},
            "supports_parallel_tool_calls": False,
            "supports_image_detail_original": False,
            "context_window": context, "max_context_window": context,
            "auto_compact_token_limit": compact,
            "experimental_supported_tools": [], "input_modalities": ["text", "image"],
            "supports_search_tool": False, "use_responses_lite": False,
            "node_repl_auto_review_required": False, "node_repl_disabled": False,
        })
    return json.dumps({"models": models}, indent=2)


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
        'env_key_instructions = "Create an LTT API key, then set LTT_API_KEY in the user environment."\n'
        'wire_api = "responses"                  # the only value Codex supports\n'
        'requires_openai_auth = false             # use LTT_API_KEY; skip OpenAI sign-in\n'
        'supports_websockets = false              # LTT streams Responses over SSE\n'
        "request_max_retries = 1                 # one retry; avoids retry amplification\n"
        "stream_max_retries = 0                  # never replay an opened stream\n"
        "stream_idle_timeout_ms = 600000"
    )


def _codex_model_root(model: str, *, desktop: bool = False) -> str:
    """Root keys shared by the CLI profile and Desktop user config."""
    context, compact = CODEX_MODEL_LIMITS[model]
    reasoning = CODEX_MODEL_REASONING[model]
    header = (
        "# %USERPROFILE%/.codex/config.toml — Desktop / IDE use root settings.\n"
        "# Keep the provider id `ltt` stable: saved threads remember it.\n"
        if desktop else
        "# ~/.codex/ltt.config.toml — a SEPARATE file.\n"
        "# Codex 0.145+ refuses [profiles.ltt] inside config.toml.\n"
    )
    return (
        header +
        f'model = "{model}"\n'
        'model_provider = "ltt"\n'
        '# Platform default: medium (LTT 3.8 also offers low and xhigh);\n'
        '# Qwen3.5 stays in thinking mode through the compatible medium value.\n'
        f'model_reasoning_effort = "{reasoning}"\n'
        'model_reasoning_summary = "none"\n'
        f"model_context_window = {context}\n"
        f"model_auto_compact_token_limit = {compact}\n"
        'model_auto_compact_token_limit_scope = "total"\n'
        f"tool_output_token_limit = {TRAN_KET_QUA_TOOL}\n"
        "# Declare the model so Codex stops guessing. Without this it warns\n"
        f"# `Model metadata for {model} not found`, then substitutes an OpenAI\n"
        "# model name on its own internal calls — which our gate rejects.\n"
        f"model_catalog_json = '{TEP_CATALOG_CODEX}'\n"
        "# LTT does not serve Codex's hosted web_search tool (R-11).\n"
        'web_search = "disabled"\n'
        "\n[agents]\n"
        f'default_subagent_model = "{model}"\n'
        f'default_subagent_reasoning_effort = "{reasoning}"\n'
        "max_concurrent_threads_per_session = 1"
    )


def codex_profile(model: str = CLI_MODEL) -> str:
    """`~/.codex/ltt.config.toml` — a separate CLI profile file."""
    return _codex_model_root(model)


def codex_desktop_config(base_url: str, model: str = CLI_MODEL) -> str:
    """Complete user-level config read by Codex Desktop and its app-server.

    Desktop cannot pass ``--profile``.  It therefore needs the selected model
    at the TOML root, while the provider stays under one stable ``ltt`` id.
    The local catalog is startup-only, so switching this block takes effect in
    a new Desktop process and a new thread.
    """
    if model not in CODEX_MODEL_LIMITS:
        raise KeyError(f"khong co ho so Codex cho {model!r}")
    return _codex_model_root(model, desktop=True) + "\n\n" + codex_config(base_url).split("\n", 3)[3]


def claude_code_env(base_url: str) -> str:
    """Claude Code CLI reads plain environment variables."""
    model_lines = "".join(
        f'$env:{name} = "{value}"\n'
        for name, value in claude_model_env(CLI_MODEL)
    )
    local_lines = "".join(
        f'$env:{name} = "{value}"\n'
        for name, value in claude_local_env(CLI_MODEL)
    ).rstrip("\n")
    return (
        f'$env:ANTHROPIC_BASE_URL = "{_goc(base_url)}/api"   # NO /v1 — the client adds it\n'
        f'$env:ANTHROPIC_AUTH_TOKEN = $env:{ENV_API_KEY}\n'
        f'{model_lines}'
        f'# Claude Code does not know `{CLI_MODEL}`, so it ASSUMES a 200,000\n'
        f'# token window and never compacts in time. This is the canonical\n'
        f'# LTT Local preset; copy every line and do not add 1M overrides.\n'
        f'#   MAX_CONTEXT_TOKENS    corrects the window it assumes\n'
        f'#   AUTO_COMPACT_WINDOW   sets WHEN it compacts. Without it Claude\n'
        f'#                         compacts only AT the window above, leaving\n'
        f'#                         less room than one full answer.\n'
        f'#   MAX_MCP_OUTPUT_TOKENS caps one MCP result: its default, 25000,\n'
        f'#                         can outgrow that room in a single turn.\n'
        f'{local_lines}'
    )


def claude_code_settings(base_url: str) -> str:
    """`~/.claude/settings.json` — survives a new terminal."""
    env = {
        "ANTHROPIC_BASE_URL": f"{_goc(base_url)}/api",
        "ANTHROPIC_AUTH_TOKEN": "<your ltt_sk_… key>",
    }
    env.update(claude_model_env(CLI_MODEL))
    env.update(claude_local_env(CLI_MODEL))
    return _json({
        "env": env
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
    model_rows = "".join(
        f'    {{"name": "{name}", "value": "{value}"}},\n'
        for name, value in claude_model_env(CLI_MODEL)
    )
    local_rows = "".join(
        f'    {{"name": "{name}", "value": "{value}"}},\n'
        for name, value in claude_local_env(CLI_MODEL)
    ).rstrip(",\n")
    return (
        "{\n"
        '  "claudeCode.disableLoginPrompt": true,\n'
        '  "claudeCode.environmentVariables": [\n'
        '    {"name": "ANTHROPIC_BASE_URL", "value": "' + base_url + '/api"},\n'
        f'{model_rows}'
        f'{local_rows}\n'
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
    return codex_desktop_config(base_url, CLI_MODEL)


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

    Desktop also has an in-app editor; ``claude_desktop_steps`` supplies its
    values.  This policy form remains useful for the connector and enterprise
    deployment.  Do not edit Electron's LevelDB files to configure either path.

    Four rules from the official reference. Each of them fails **silently**:

    * `inferenceGatewayBaseUrl` is the **origin**; the app appends
      `/v1/messages` itself. Shipping `/v1` in the value yields
      `/v1/v1/messages` and a 404 with no other clue.
    * HTTPS is **required**, including for loopback, in Desktop 1.52386.6.
    * Config is read **once at launch**, so the app must be fully quit, not just
      closed to the tray.
    * A policy under `HKEY_LOCAL_MACHINE` makes the app ignore the
      `HKEY_CURRENT_USER` one **entirely**.
    """
    khoa = r"[HKEY_CURRENT_USER\SOFTWARE\Policies\Claude]"
    mo = json.dumps([{"name": ten, "labelOverride": NHAN_DESKTOP[ten],
                      "anthropicFamilyTier": TANG_DESKTOP[ten],
                      "isFamilyDefault": True}
                     for ten in DESKTOP_MODELS],
                    separators=(",", ": ")).replace('"', '\\"')
    dong = [
        "Windows Registry Editor Version 5.00",
        "",
        khoa,
        '"inferenceProvider"="gateway"',
        '"inferenceGatewayBaseUrl"="' + base_url + '/api"',
        # ⛔ Dấu `…` (một ký tự), KHÔNG phải `...` (ba dấu chấm ASCII).
        #    Hai dòng anh em ngay dưới và ở `_gia_tri_cam()` đều dùng `…`, và
        #    `test_272::test_trang_cli_KHONG_chua_khoa_that` chốt rằng trang
        #    `/developers/cli` không chứa `ltt_sk_` nào NGOÀI hai chỗ giữ chỗ đã
        #    biết. Một biến thể thứ ba làm phép kiểm đó đỏ — và nó đỏ ĐÚNG: phép
        #    kiểm ấy canh việc một khoá THẬT rò ra trang, nên nó phải nghi ngờ
        #    mọi chuỗi `ltt_sk_` nó chưa từng thấy.
        '"inferenceGatewayApiKey"="<your ltt_sk_… key>"',
        '"inferenceGatewayAuthScheme"="bearer"',
        '"inferenceModels"="' + mo + '"',
        '"modelDiscoveryEnabled"=dword:00000000',
        # Without this the app opens only its Code tab, which starts a local
        # agent session instead of talking to the gateway — and with no local
        # runtime installed it sends nothing at all, silently.
        '"chatTabEnabled"=dword:00000001',
        # Force third-party mode even when the user previously persisted 1p.
        '"disableDeploymentModeChooser"=dword:00000001',
        # Ten minutes, aligned with the connector's fixed-capacity stream wait.
        '"inferenceStreamIdleTimeoutSec"=dword:00000258',
    ]
    return "\n".join(dong) + "\n"


def claude_desktop_steps(base_url: str) -> tuple:
    """Exact values for Claude Desktop's in-app 3P editor.

    Verified against the schema bundled in Desktop 1.52386.6.  Keep this as
    data because both the public guide and the signed-in developer guide render
    it; prose duplicated in two templates is how the old instructions drifted.

    Model discovery is deliberately off.  The public LTT catalog exposes the
    product IDs (``ltt-3.8`` / ``ltt-3.5``), while Desktop must send the two
    compatibility route IDs below.  An explicit list also lets us attach the
    product labels without inventing another backend alias.
    """
    return (
        ("Connection", "Gateway"),
        ("Credential kind", "Static API key"),
        ("Gateway base URL", f"{_goc(base_url)}/api"),
        ("Gateway API key", "your ltt_sk_… key"),
        ("Gateway auth scheme", "Bearer"),
        ("Artifact preview iframe origin", "leave blank"),
        ("Custom inference headers", "leave blank"),
        ("Stream idle timeout", "600 seconds"),
        ("Model discovery", "Off"),
        ("Default to 1M context", "Off"),
        ("Model 1 — Model ID", DESKTOP_MODELS[0]),
        ("Model 1 — Display name", NHAN_DESKTOP[DESKTOP_MODELS[0]]),
        ("Model 1 — Offer 1M-context variant", "Off"),
        ("Model 1 — Tier alias", TANG_DESKTOP[DESKTOP_MODELS[0]]),
        ("Model 1 — Default for tier", "On"),
        ("Model 2 — Model ID", DESKTOP_MODELS[1]),
        ("Model 2 — Display name", NHAN_DESKTOP[DESKTOP_MODELS[1]]),
        ("Model 2 — Offer 1M-context variant", "Off"),
        ("Model 2 — Tier alias", TANG_DESKTOP[DESKTOP_MODELS[1]]),
        ("Model 2 — Default for tier", "On"),
        ("Show estimated cost", "Off"),
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
     f"word, and drops the rest before the picker is drawn — so {CLI_MODEL} is "
     f"discarded, the picker ends up empty, and the send button silently stops "
     f"working. Give it {', '.join(DESKTOP_MODELS)}: two explicit LTT routes "
     f"that clear its filter and keep the model choice visible."),
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
#        model     ltt-3.8            ><   ltt-llm-claude-compat (Desktop)
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
BE_MAT_MA = ("codex", "codex-desktop", "claude-code", "vscode", "desktop", "http")

#: Ma buoc → doan ma. Tach khoi VAN XUOI co chu dich, xem `be_mat_cam`.
BUOC_MA = ("codex-catalog", "codex-config", "codex-profile", "dat-khoa", "env", "settings",
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
         "model_limits": tuple((slug, *CODEX_MODEL_LIMITS[slug]) for slug in CLI_MODELS),
         "buoc": (("codex-catalog", "~/.codex/ltt_model_catalog.json", codex_catalog()),
                  ("codex-config", "~/.codex/config.toml", codex_config(goc)),
                  ("codex-profile", "~/.codex/ltt.config.toml", codex_profile()),
                  ("codex-profile", "~/.codex/ltt-fast.config.toml", codex_profile("ltt-3.5")),
                  ("dat-khoa", None,
                   f"$env:{ENV_API_KEY} = [System.Net.NetworkCredential]::new(\n"
                   "    '', (Read-Host 'LTT API key' -AsSecureString)).Password\n"
                   "# Run Codex in this same PowerShell window.")),
         "chay": "codex --profile ltt"},
        {"ma": "codex-desktop", "ten": "Codex Desktop", "the": "CONFIG.TOML",
         "dia_chi": f"{goc}/api/v1", "model": CLI_MODEL,
         "models": tuple((slug, CODEX_MODEL_LABELS[slug]) for slug in CLI_MODELS),
         "model_limits": tuple((slug, *CODEX_MODEL_LIMITS[slug]) for slug in CLI_MODELS),
         "buoc": (("codex-catalog", "%USERPROFILE%/.codex/ltt_model_catalog.json", codex_catalog()),
                  ("codex-desktop-strong", "%USERPROFILE%/.codex/config.toml",
                   codex_desktop_config(goc, "ltt-3.8")),
                  ("codex-desktop-fast", "%USERPROFILE%/.codex/config.toml",
                   codex_desktop_config(goc, "ltt-3.5"))),
         "chay": None},
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
        {"ma": "desktop", "ten": "Claude Desktop", "the": "IN-APP GATEWAY",
         "dia_chi": f"{goc}/api", "model": DESKTOP_MODEL,
         "models": tuple((ten, NHAN_DESKTOP[ten]) for ten in DESKTOP_MODELS),
         "local_env": claude_local_env(),
         "local_presets": tuple(claude_local_preset(slug) for slug in CLI_MODELS),
         # The tool still uses ``claude_desktop_registry`` for repeatable fleet
         # setup.  The customer-facing path is the editor that ships in current
         # Desktop, so this surface has no copyable registry block.
         "buoc": (),
         "chay": None},
        {"ma": "http", "ten": "cURL", "the": "HTTP",
         "dia_chi": f"{goc}/api/v1", "model": CLI_MODEL,
         "buoc": (("curl", None, curl_chat()),),
         "chay": None},
    )

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
        ("inferenceModels", CLI_MODEL),
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
    ("Claude Desktop needs inferenceModels spelled out",
     "Its model auto-discovery keeps only IDs that look like Claude, so this "
     "model never appears on its own and the picker stays empty with nothing to "
     "explain why."),
    ("Streaming is required on these two routes",
     'Send "stream": true. For a single non-streaming answer use '
     "POST /api/v1/chat/completions, which is what the SDKs call."),
    ("A retry costs money",
     "These routes take no Idempotency-Key, because no CLI sends one. You are "
     "billed for the tokens actually produced, so an abandoned stream bills for "
     "what it generated — and a retry generates again."),
)

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
        "Content-Type": "application/json"}}


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

"""Generate the tool reference inside the developer guide from the catalog.

    python tools\\build_public_api_docs.py            # rewrite the section
    python tools\\build_public_api_docs.py --check    # fail if it is stale

Docs about an API drift the moment the API changes, and a wrong parameter list
costs a developer an afternoon. So the one part that must match the code exactly
— the published tools and their inputs — is generated from the same catalog the
API serves, between two markers in ``docs/PUBLIC_API/DEVELOPER_GUIDE.md``.

``--check`` is wired into the test suite, the same way ``build_system_profile``
guards the architecture dossier.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

GUIDE = ROOT / "docs" / "PUBLIC_API" / "DEVELOPER_GUIDE.md"
BEGIN = "<!-- BEGIN GENERATED TOOLS -->"
END = "<!-- END GENERATED TOOLS -->"

ENV_BEGIN = "<!-- BEGIN GENERATED ENV -->"
ENV_END = "<!-- END GENERATED ENV -->"

PROTOCOL = ROOT / "docs" / "PUBLIC_API" / "PROTOCOL_V1.md"
ERR_BEGIN = "<!-- BEGIN GENERATED ERRORS -->"
ERR_END = "<!-- END GENERATED ERRORS -->"


def _catalog():
    from platform_core.public_api.catalog import build_catalog
    from platform_core.public_api.config import load_public_api_config
    from platform_core.registry import discover

    # Every tool whose app declares it public — independent of what this
    # particular deployment switched on, because the guide documents the API,
    # not one installation.
    names = ",".join(sorted(tool.name for item in discover() if not item.error
                            for tool in item.manifest.tools if tool.api_exposed))
    config = load_public_api_config({"LTT_PUBLIC_API": "1",
                                     "LTT_PUBLIC_API_TOOLS": names})
    return build_catalog(config)


def _render_parameter(name: str, spec: dict, required: list) -> str:
    kind = str(spec.get("type", "string"))
    bits = [f"`{name}`", kind]
    if name in required:
        bits.append("**required**")
    if "enum" in spec:
        values = ", ".join(f"`{value}`" for value in spec["enum"])
        bits.append(f"one of {values}")
    for key, label in (("minimum", "min"), ("maximum", "max"),
                       ("maxLength", "max length"), ("default", "default")):
        if key in spec:
            bits.append(f"{label} {spec[key]}")
    if spec.get("description"):
        bits.append(str(spec["description"]))
    return " — ".join([bits[0], ", ".join(bits[1:])])


def render() -> str:
    lines = [BEGIN, ""]
    catalog = _catalog()
    if not catalog:
        lines += ["*No tool is published in this build.*", ""]
    for tool in catalog:
        schema = tool.input_schema
        required = list(schema.get("required", ()))
        lines.append(f"### `{tool.name}`")
        lines.append("")
        lines.append(tool.description)
        lines.append("")
        lines.append(f"Execution mode: `{tool.execution_mode}`")
        lines.append("")
        lines.append(f"Scopes: {', '.join(f'`{s}`' for s in tool.scopes) or '—'}")
        lines.append("")
        lines.append("Input:")
        lines.append("")
        for name, spec in schema.get("properties", {}).items():
            lines.append(f"- {_render_parameter(name, spec, required)}")
        lines.append("")
        outputs = tool.output_schema.get("properties", {})
        lines.append("Output: " + ", ".join(
            f"`{name}` ({spec.get('type')})" for name, spec in outputs.items()))
        lines.append("")
        if tool.aliases:
            lines.append("Also answers to: "
                         + ", ".join(f"`{alias}`" for alias in tool.aliases))
            lines.append("")
        if tool.deprecated:
            lines.append(f"> Deprecated: {tool.deprecated}")
            lines.append("")
        lines.append(f"Contract hash: `{tool.to_public_dict()['contract_hash']}`")
        lines.append("")

    from platform_core.public_api.catalog import build_models

    models = build_models(catalog)
    if models:
        lines += ["### Models", "",
                  "Aliases, not vendor model ids. What a call *costs* comes "
                  "from `POST /quotes`: price depends on the whole input, so a "
                  "number printed against a model would be wrong often enough "
                  "to matter.", "",
                  "| Alias | Capability | Stability | Tools | Notes |",
                  "|---|---|---|---|---|"]
        for model in models:
            note = model.description
            if model.replaced_by:
                note = f"{note} Replaced by `{model.replaced_by}`.".strip()
            lines.append(
                f"| `{model.name}` | {model.capability} | {model.stability} | "
                + ", ".join(f"`{name}`" for name in model.tools)
                + f" | {note} |")
        lines.append("")
    lines.append(END)
    return "\n".join(lines)


def render_env() -> str:
    """Environment variables and one runnable first call.

    Generated for the same reason the tool reference is: the snippet has to
    match a schema that changes, and a hand-written one silently stops matching.
    """
    from platform_core.public_api import examples

    lines = [ENV_BEGIN, "", "| Biến | Ví dụ | Để làm gì |", "|---|---|---|"]
    for name, sample, purpose in examples.ENV_VARS:
        shown = f"`{sample}`" if sample else "—"
        lines.append(f"| `{name}` | {shown} | {purpose} |")
    lines.append("")
    for shell, snippet in examples.SHELL_EXPORTS:
        lines += [f"**{shell}**", "", "```", snippet, "```", ""]

    catalog = _catalog()
    if catalog:
        tool = catalog[0]
        lines += [f"Lời gọi đầu tiên (`{tool.name}`) — báo giá trước, chạy sau:",
                  "", "```bash", examples.curl_quote(tool), "```", "",
                  "```bash", examples.curl_submit(tool), "```", ""]
    lines += ["Không viết khóa thẳng vào mã nguồn: nó sẽ đi theo mã vào git, "
              "vào log và vào ảnh chụp màn hình.", "", ENV_END]
    return "\n".join(lines)


def render_errors() -> str:
    """The error registry as a table — generated, because a stale retry table
    is worse than none: it tells a client to give up on a retryable failure."""
    from platform_core.public_api.error_registry import (IDEMPOTENCY_RULE,
                                                         RETRY_MATRIX, as_rows)

    lines = [ERR_BEGIN, "", "| Code | HTTP | Retry | Reuse Idempotency-Key | What to do |",
             "|---|---|---|---|---|"]
    for row in as_rows():
        lines.append(
            f"| `{row['code']}` | {row['status']} | `{row['retry']}` | "
            f"{'yes' if row['reuse_idempotency_key'] else 'no'} | "
            f"{row['action']} |")
    lines += ["", "### Retry matrix by status", "",
              "| Response | Retry | Note |", "|---|---|---|"]
    for status, retry, note in RETRY_MATRIX:
        lines.append(f"| {status} | `{retry}` | {note} |")
    lines += ["", f"> {IDEMPOTENCY_RULE}", "", ERR_END]
    return "\n".join(lines)


def _splice(text: str, block: str, begin: str = BEGIN, end: str = END) -> str:
    start = text.index(begin)
    stop = text.index(end) + len(end)
    return text[:start] + block + text[stop:]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    targets = [
        (GUIDE, render(), BEGIN, END, "developer guide"),
        (GUIDE, render_env(), ENV_BEGIN, ENV_END, "environment section"),
        (PROTOCOL, render_errors(), ERR_BEGIN, ERR_END, "protocol reference"),
    ]
    stale = False
    for path, block, begin, end, label in targets:
        current = path.read_text(encoding="utf-8")
        updated = _splice(current, block, begin, end)
        if args.check:
            if current != updated:
                print("STALE:", path)
                stale = True
            continue
        if current != updated:
            path.write_text(updated, encoding="utf-8")
            print("WROTE:", path)
        else:
            print("UNCHANGED:", path)
    if args.check:
        if stale:
            print("Run: python tools/build_public_api_docs.py")
            return 1
        print("PASS: docs match the published catalog and error registry")
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())

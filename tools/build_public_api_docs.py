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
        if tool.deprecated:
            lines.append(f"> Deprecated: {tool.deprecated}")
            lines.append("")
    lines.append(END)
    return "\n".join(lines)


def _splice(text: str, block: str) -> str:
    start = text.index(BEGIN)
    end = text.index(END) + len(END)
    return text[:start] + block + text[end:]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    current = GUIDE.read_text(encoding="utf-8")
    updated = _splice(current, render())
    if args.check:
        if current != updated:
            print("STALE:", GUIDE)
            print("Run: python tools/build_public_api_docs.py")
            return 1
        print("PASS: developer guide matches the published catalog")
        return 0
    GUIDE.write_text(updated, encoding="utf-8")
    print("WROTE:", GUIDE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

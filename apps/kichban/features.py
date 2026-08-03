"""Source/research, version payload and deterministic shot-list helpers."""
from __future__ import annotations

MAX_SOURCE_CHARS = 8_000
MAX_RESEARCH_CHARS = 8_000


def clean_context(value: str, limit: int = MAX_SOURCE_CHARS) -> str:
    return (value or "").strip()[:limit]


def context_directive(sources: str, research: str) -> str:
    blocks = []
    if clean_context(sources):
        blocks.append("SOURCES supplied by the user (do not invent citations):\n" + clean_context(sources))
    if clean_context(research, MAX_RESEARCH_CHARS):
        blocks.append("RESEARCH NOTES supplied by the user:\n" +
                      clean_context(research, MAX_RESEARCH_CHARS))
    return "\n\n".join(blocks)


def derive_shot_list(script: dict) -> list[dict]:
    rows = []
    if script.get("hook"):
        rows.append({"scene": 1, "section": "Hook", "visual": "Opening visual / pattern interrupt",
                     "voiceover": str(script["hook"])[:1200]})
    for section in list(script.get("sections") or [])[:40]:
        rows.append({"scene": len(rows) + 1,
                     "section": str(section.get("title") or f"Phần {len(rows)+1}")[:160],
                     "visual": str(section.get("visual") or
                                   f"B-roll minh hoạ: {section.get('title') or 'nội dung'}")[:500],
                     "voiceover": str(section.get("content") or "")[:1200]})
    if script.get("outro"):
        rows.append({"scene": len(rows) + 1, "section": "Outro & CTA",
                     "visual": "End card / call to action",
                     "voiceover": str(script["outro"])[:1200]})
    return rows


def project_payload(*, job_id: str, script: dict, sources: str, research: str) -> dict:
    return {"kind": "script_project", "source_job_id": job_id,
            "script": script, "sources": clean_context(sources),
            "research": clean_context(research, MAX_RESEARCH_CHARS),
            "shot_list": derive_shot_list(script)}

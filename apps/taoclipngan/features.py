"""Governed brand, rationale and social package helpers for Clip Studio."""
from __future__ import annotations

from platform_core.i18n import N_

BRAND_PRESETS = {
    "auto": {"label": N_("Tự động theo thể loại"), "overrides": {}},
    "ltt_red": {"label": N_("LTT Red"), "overrides": {
        "color_preset": "cinematic", "caption_preset": "viral_pop",
        "hook_caption_preset": "viral_pop"}},
    "creator_clean": {"label": N_("Creator Clean"), "overrides": {
        "color_preset": "clear_fresh", "caption_preset": "clean_boxed"}},
    "cinematic": {"label": N_("Cinematic"), "overrides": {
        "color_preset": "cinematic", "caption_preset": "cinematic"}},
}
PLATFORMS = ("tiktok", "youtube_shorts", "instagram_reels")


def clean_brand(value: str) -> str:
    return value if value in BRAND_PRESETS else "auto"


def brand_overrides(value: str) -> dict:
    return dict(BRAND_PRESETS[clean_brand(value)]["overrides"])


def clean_platforms(values) -> list[str]:
    if isinstance(values, str):
        values = values.split(",")
    out = []
    for value in values or []:
        item = str(value).strip()
        if item in PLATFORMS and item not in out:
            out.append(item)
    return out or list(PLATFORMS)


def score_rationale(candidate) -> dict:
    score = getattr(candidate, "score", None)
    explanation = getattr(candidate, "explanation", None)
    dimensions = {}
    for name in ("hook_strength", "pacing", "completeness", "visual_quality",
                 "audio_quality", "topic_coherence", "semantic_richness"):
        dimensions[name] = round(float(getattr(score, name, 0) or 0), 3)
    why = (getattr(explanation, "why_selected", "") if explanation else "") or \
          getattr(candidate, "why_selected", "") or \
          getattr(candidate, "strategy_reasoning", "") or "Xếp hạng từ tín hiệu nội dung và kỹ thuật."
    return {"overall": round(float(getattr(score, "overall", 0) or 0), 3),
            "dimensions": dimensions, "why_selected": str(why)[:1200],
            "intent": str(getattr(candidate, "clip_intent", "unknown"))[:80],
            "risk_level": str(getattr(explanation, "risk_level", "low") if explanation else "low")[:40],
            "risk_flags": [str(x)[:160] for x in
                           (getattr(explanation, "risk_flags", []) if explanation else
                            getattr(candidate, "risk_flags", []))][:12]}


def platform_copy(title: str, description: str, hashtags, platforms) -> dict:
    tags = [str(x).strip().lstrip("#")[:60] for x in (hashtags or []) if str(x).strip()][:12]
    if not tags:
        tags = ["shorts", "video"]
    base_title = str(title or "Clip ngắn").strip()[:120]
    base_description = str(description or "").strip()[:2000]
    limits = {"tiktok": 150, "youtube_shorts": 100, "instagram_reels": 125}
    out = {}
    for platform in clean_platforms(platforms):
        platform_tags = list(tags)
        if platform == "youtube_shorts" and "shorts" not in [x.lower() for x in platform_tags]:
            platform_tags.insert(0, "Shorts")
        out[platform] = {"title": base_title[:limits[platform]],
                         "description": base_description,
                         "hashtags": platform_tags}
    return out


def package_payload(*, job_id: str, original_clips: list[dict], drafts: list[dict],
                    platforms, brand_preset: str) -> dict:
    by_index = {int(x.get("index", -1)): x for x in drafts if isinstance(x, dict)
                and str(x.get("index", "")).lstrip("-").isdigit()}
    clips = []
    for index, source in enumerate(original_clips[:10]):
        draft = by_index.get(index, {})
        start = float(source.get("source_start") or 0)
        end = float(source.get("source_end") or source.get("duration_s") or start)
        text = str(draft.get("transcript_text") or "").strip()[:20000]
        transcript = source.get("transcript") or []
        if text:
            transcript = [{"start": start, "end": end, "text": text, "speaker": ""}]
        title = str(draft.get("title") or source.get("title") or f"Clip {index + 1}")[:120]
        clips.append({**source, "title": title, "transcript": transcript,
                      "platform_copy": platform_copy(title,
                          str(source.get("seo_description") or ""),
                          source.get("hashtags") or [], platforms)})
    return {"kind": "clip_social_package", "source_job_id": job_id,
            "brand_preset": clean_brand(brand_preset),
            "platforms": clean_platforms(platforms), "clips": clips}


def srt_text(segments: list[dict]) -> str:
    def stamp(value):
        total_ms = max(0, round(float(value or 0) * 1000))
        hours, rem = divmod(total_ms, 3_600_000)
        minutes, rem = divmod(rem, 60_000)
        seconds, millis = divmod(rem, 1000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"
    blocks = []
    for index, segment in enumerate(segments or [], 1):
        text = str(segment.get("text") or "").strip()
        if text:
            blocks.append(f"{index}\n{stamp(segment.get('start'))} --> {stamp(segment.get('end'))}\n{text}")
    return "\n\n".join(blocks) + ("\n" if blocks else "")

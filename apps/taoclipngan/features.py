"""Governed brand, rationale and social package helpers for Clip Studio."""
from __future__ import annotations

import threading

from platform_core.i18n import N_, _ as _t

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
ANALYSIS_ENGINES = ("scene", "motion", "speech", "audio", "visual", "content")


def candidate_gate_dict(cand) -> dict:
    """Ánh xạ `CandidateClip` → dict cho `QualityGate` (engine cutclipshort).

    Thang chuẩn của gate (`cutclipshort/evaluation/gate.py`): điểm chất lượng
    0-100 (`hook_score`, `completeness_score`, `pacing_score`, `audio_score`,
    `score`), `intent_confidence` 0-1, `duration` giây, `cluster_id` int.
    `CandidateScore` lưu 0-1 → nhân 100. Trừ trường nào thiếu thì gate tự
    dùng mặc định (50) — không raise.
    """
    score = getattr(cand, "score", None)
    rng = getattr(cand, "time_range", None)

    def _pct(name: str) -> float:
        try:
            return round(float(getattr(score, name, 0) or 0) * 100, 1)
        except (TypeError, ValueError):
            return 50.0

    try:
        duration = round(float(getattr(rng, "duration", 0) or 0), 2)
    except (TypeError, ValueError):
        duration = 0.0
    try:
        cluster = int(getattr(cand, "cluster_id", -1))
    except (TypeError, ValueError):
        cluster = -1
    return {
        "candidate_id": str(getattr(cand, "candidate_id", "") or ""),
        "hook_score": _pct("hook_strength"),
        "completeness_score": _pct("completeness"),
        "pacing_score": _pct("pacing"),
        "audio_score": _pct("audio_quality"),
        "score": _pct("overall"),
        "clip_intent": str(getattr(cand, "clip_intent", "unknown") or "unknown"),
        "intent_confidence": float(getattr(cand, "intent_confidence", 0) or 0),
        "duration": duration,
        "has_speech": bool(getattr(cand, "has_speech", True)),
        "cluster_id": cluster,
        "risk_flags": [str(x) for x in (getattr(cand, "risk_flags", None) or [])],
    }


def apply_quality_gate(candidates: list, mode: str) -> tuple[list, dict]:
    """Chạy quality gate v3 trên danh sách ứng viên đã xếp hạng.

    `mode="block"` — loại clip bị hard veto (hook<0.20, intent yếu, cắt giữa
    chừng, <5s, trùng cluster). Rỗng hoàn toàn → giữ top-1 + `qa["fallback"]`
    (không bao giờ trả rỗng).
    `mode="warn"` — không loại gì; toàn bộ quyết định nằm trong `qa`.

    Trả về `(kept, qa)`: `kept` = danh sách ứng viên còn lại theo thứ tự hạng
    gốc; `qa` = khối JSON gọn để ghi vào manifest `clips.json`.
    """
    if mode not in ("block", "warn"):
        raise ValueError(f"{_t('gate mode không hợp lệ: ')}{mode!r}")
    if not candidates:
        return [], {"mode": mode, "checked": 0, "fallback": True,
                    "vetoed": {}, "warnings": {}, "scores": {}}
    from cutclipshort.evaluation.gate import QualityGate

    gate = QualityGate()
    results = gate.batch_check([candidate_gate_dict(c) for c in candidates],
                               enforce_cluster_unique=True)
    qa: dict = {"mode": mode, "checked": len(candidates), "fallback": False,
                "vetoed": {}, "warnings": {}, "scores": {}}
    for cand in candidates:
        cid = str(getattr(cand, "candidate_id", "") or "")
        res = results.get(cid)
        if res is None:
            continue
        qa["scores"][cid] = res.score
        if res.vetoed:
            qa["vetoed"][cid] = list(res.veto_reasons)
        if res.soft_fail_reasons:
            qa["warnings"][cid] = list(res.soft_fail_reasons)

    if mode != "block":
        return list(candidates), qa

    kept = [c for c in candidates
            if not results.get(str(getattr(c, "candidate_id", "") or "")).vetoed]
    if not kept:
        # Không clip nào qua được gate → giữ ứng viên hạng nhất, đánh dấu fallback
        kept = list(candidates[:1])
        qa["fallback"] = True
    return kept, qa


class AnalysisProgressTracker:
    """Gộp tiến độ engine song song thành một dòng job đơn điệu, có tiết lưu."""

    def __init__(self, *, start: int = 5, end: int = 58, min_step: int = 2) -> None:
        self._start = start
        self._end = end
        self._min_step = max(1, min_step)
        self._values = {name: 0.0 for name in ANALYSIS_ENGINES}
        self._last = start
        self._lock = threading.Lock()

    def update(self, engine_name: str, pct: float) -> tuple[int, str] | None:
        """Trả về progress mới hoặc None nếu chưa đủ bước để ghi activity."""
        name = str(engine_name or "analysis")
        try:
            value = max(0.0, min(1.0, float(pct)))
        except (TypeError, ValueError):
            return None
        with self._lock:
            if name not in self._values:
                self._values[name] = 0.0
            self._values[name] = max(self._values[name], value)
            average = sum(self._values.values()) / max(1, len(self._values))
            current = self._start + int(average * (self._end - self._start))
            current = max(self._last, min(self._end, current))
            if current < self._last + self._min_step and current < self._end:
                return None
            if current == self._last:
                return None
            self._last = current
            return current, f"phân tích: {name}"


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


#: Ngưỡng một từ được coi là ghi lời kém (whisper: từ thật thường > 0.5,
#: từ ảo do nhiễu/nhạc thường gần 0). Dùng cho chỉ số độ tin cậy ghi lời.
NGUONG_TU_YEUNGHI = 0.5


def _du_lay_words(item) -> list:
    """Lấy danh sách từ (dict) từ một caption segment (dict hoặc object)."""
    words = item.get("words") if isinstance(item, dict) else getattr(item, "words", None)
    return [w for w in (words or []) if isinstance(w, dict) and "confidence" in w]


def tin_cay_ghi_loi(caption_segments, total_words: int | None = None) -> dict | None:
    """Độ tin cậy ghi lời của MỘT clip, từ confidence từng từ của whisper.

    Trả về dict ``{"value": float 0-1, "words": int, "low_words": int,
    "low_ratio": float}`` hoặc ``None`` khi clip không có word-level
    confidence (segment rỗng, hoặc bản ghi cũ chưa có khối ``words``) —
    UI ẩn chỉ số chứ không giả số. ``total_words`` (toàn job) nếu được
    truyền thì bổ sung vào kết quả để UI nêu rõ mẫu đo.

    Đây là số đo TÍN NHIỆM từ confidence, KHÔNG phải WER (không có bản
    tham chiếu để so); giữ tên "độ tin cậy ghi lời" để không hứa đo
    sai số mà chưa có corpus chuẩn.
    """
    confs: list[float] = []
    for seg in (caption_segments or []):
        for w in _du_lay_words(seg):
            try:
                confs.append(float(w.get("confidence")))
            except (TypeError, ValueError):
                continue
    if not confs:
        return None
    low = sum(1 for c in confs if c < NGUONG_TU_YEUNGHI)
    out = {
        "value": round(sum(confs) / len(confs), 3),
        "words": len(confs),
        "low_words": low,
        "low_ratio": round(low / len(confs), 3),
    }
    if total_words is not None:
        out["total_words"] = int(total_words)
    return out


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


def rebase_transcript(segments, *, source_start: float, source_end: float) -> list[dict]:
    """Đưa caption từ timeline video nguồn về timeline 0 của clip xuất."""
    start = max(0.0, float(source_start or 0))
    end = max(start, float(source_end or start))
    duration = end - start
    rows = [dict(item) for item in (segments or []) if isinstance(item, dict)]
    if not rows or duration <= 0:
        return []

    rebased = []
    for row in rows:
        try:
            local_start = max(0.0, float(row.get("start") or 0) - start)
            local_end = min(duration, float(row.get("end") or 0) - start)
        except (TypeError, ValueError):
            continue
        if local_end <= local_start or not str(row.get("text") or "").strip():
            continue
        row["start"] = round(local_start, 3)
        row["end"] = round(local_end, 3)
        rebased.append(row)
    return rebased


def package_payload(*, job_id: str, original_clips: list[dict], drafts: list[dict],
                    platforms, brand_preset: str) -> dict:
    by_index = {int(x.get("index", -1)): x for x in drafts if isinstance(x, dict)
                and str(x.get("index", "")).lstrip("-").isdigit()}
    clips = []
    for index, source in enumerate(original_clips[:10]):
        draft = by_index.get(index, {})
        start = float(source.get("source_start") or 0)
        end = float(source.get("source_end") or
                    (start + float(source.get("duration_s") or 0)))
        text = str(draft.get("transcript_text") or "").strip()[:20000]
        transcript = rebase_transcript(source.get("transcript") or [],
                                       source_start=start, source_end=end)
        if text:
            transcript = [{"start": 0.0, "end": round(max(0.0, end - start), 3),
                           "text": text, "speaker": ""}]
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

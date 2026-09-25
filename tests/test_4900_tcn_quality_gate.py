"""Pha 0.1 — quality gate nối vào apps/taoclipngan.

`apply_quality_gate` + `candidate_gate_dict` (features.py, thuần) chạy gate v3
của `cutclipshort/evaluation/gate.py` trên `CandidateClip`. Block mode loại
clip bị hard veto; warn mode chỉ ghi lý do. Test không cần worker/GPU.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from apps.taoclipngan.features import apply_quality_gate, candidate_gate_dict
from cutclipshort.types.base import ContentType, TimeRange
from cutclipshort.types.editorial import CandidateClip, CandidateScore


def _cand(cid: str, *, start: float = 10.0, end: float = 30.0, hook: float = 0.6,
          comp: float = 0.6, pacing: float = 0.6, audio: float = 0.6,
          overall: float = 0.6, intent: str = "story", conf: float = 0.8,
          speech: bool = True, cluster: int = -1) -> CandidateClip:
    return CandidateClip(
        candidate_id=cid,
        time_range=TimeRange(start=start, end=end),
        score=CandidateScore(overall=overall, hook_strength=hook, pacing=pacing,
                             completeness=comp, visual_quality=0.6, audio_quality=audio),
        content_type=ContentType.TALKING_HEAD,
        genre_fit=0.7, motion_avg=0.3, has_speech=speech,
        speech_text_preview="x",
        clip_intent=intent, intent_confidence=conf, cluster_id=cluster,
    )


def test_mapping_thang_gate():
    """CandidateClip 0-1 → dict gate 0-100 đúng trường."""
    d = candidate_gate_dict(_cand("c1", hook=0.15, comp=0.4, pacing=0.3,
                                  audio=0.25, overall=0.55, conf=0.7,
                                  end=26.0, cluster=3))
    assert d["candidate_id"] == "c1"
    assert d["hook_score"] == 15.0
    assert d["completeness_score"] == 40.0
    assert d["pacing_score"] == 30.0
    assert d["audio_score"] == 25.0
    assert d["score"] == 55.0
    assert d["intent_confidence"] == 0.7
    assert d["duration"] == 16.0
    assert d["has_speech"] is True
    assert d["cluster_id"] == 3
    assert d["risk_flags"] == []


def test_block_loai_clip_hook_yeu():
    cand_yeu = _cand("yeu", hook=0.10)          # hook 10 < 20 → veto
    cand_tot = _cand("tot")
    kept, qa = apply_quality_gate([cand_yeu, cand_tot], "block")
    assert [c.candidate_id for c in kept] == ["tot"]
    assert qa["vetoed"] and "yeu" in qa["vetoed"]
    assert any("hook" in r.lower() or "opening" in r.lower()
               for r in qa["vetoed"]["yeu"])
    assert qa["fallback"] is False


def test_block_loai_clip_ngan_va_intent_yeu():
    ngan = _cand("ngan", end=12.0)              # 2s < 5s → veto
    meo_intent = _cand("meo", intent="unknown", conf=0.1)
    tot = _cand("tot")
    kept, qa = apply_quality_gate([ngan, meo_intent, tot], "block")
    assert [c.candidate_id for c in kept] == ["tot"]
    assert set(qa["vetoed"]) == {"ngan", "meo"}


def test_block_bo_toan_bo_giu_top1_fallback():
    yeu1 = _cand("a", hook=0.05)
    yeu2 = _cand("b", comp=0.05)
    kept, qa = apply_quality_gate([yeu1, yeu2], "block")
    assert len(kept) == 1
    assert kept[0].candidate_id == "a"           # hạng nhất
    assert qa["fallback"] is True


def test_warn_khong_loai_gi():
    yeu = _cand("yeu", hook=0.10, pacing=0.20)
    tot = _cand("tot")
    kept, qa = apply_quality_gate([yeu, tot], "warn")
    assert [c.candidate_id for c in kept] == ["yeu", "tot"]
    assert qa["fallback"] is False
    # Lý do vẫn được ghi để manifest giải thích được
    assert "yeu" in qa["vetoed"]
    assert "pacing" in str(qa["warnings"].get("yeu", "")) or "Nhịp" in str(
        qa["warnings"].get("yeu", ""))
    assert qa["scores"]["yeu"] == pytest.approx(qa["scores"]["yeu"])  # số hợp lệ
    assert 0 <= qa["scores"]["yeu"] <= 100


def test_trung_cluster_bi_veto_block():
    a = _cand("a", cluster=7)
    b = _cand("b", cluster=7)                    # trùng cluster → veto
    kept, qa = apply_quality_gate([a, b], "block")
    assert [c.candidate_id for c in kept] == ["a"]
    assert any("cluster" in r.lower() for r in qa["vetoed"]["b"])


def test_danh_rong_tra_rong_fallback():
    kept, qa = apply_quality_gate([], "block")
    assert kept == []
    assert qa["fallback"] is True
    assert qa["checked"] == 0


def test_mode_sai_throw():
    with pytest.raises(ValueError):
        apply_quality_gate([_cand("x")], "silence")

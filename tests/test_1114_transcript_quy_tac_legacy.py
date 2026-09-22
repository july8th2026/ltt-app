"""App `transcript` khớp QUY TẮC của `bot_transcript` (đối chiếu 22/09/2026).

Bản port đầu chép fixer V5 nhưng không gọi, không chép từ điển, `min_s` mặc định
3.0 thay vì 1.5 của cấu hình đang chạy, và không có sổ "hệ". Tệp này chốt từng
chỗ đã sửa. Không gọi model thật: STT và VAD được thay bằng hàm giả.
"""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

from apps.transcript.services import he as sohe
from apps.transcript.services import phien_am, sua_chu


def _tu(chuoi: str, t0: float = 0.0, buoc: float = 0.4) -> list[dict]:
    return [{"start": round(t0 + i * buoc, 3), "end": round(t0 + (i + 1) * buoc, 3),
             "text": w} for i, w in enumerate(chuoi.split())]


def _doan(chuoi: str, t0: float = 0.0, buoc: float = 0.4) -> dict:
    tu = _tu(chuoi, t0, buoc)
    return {"start": tu[0]["start"], "end": tu[-1]["end"], "text": chuoi, "words": tu}


# ── chuẩn đoạn thô (whisper_integration.py:140-150, :75-97) ─────────────────

def test_chuan_doan_tho_bo_rong_dao_moc_va_doi_khoa_word() -> None:
    ra = sua_chu.chuan_doan_tho([
        {"start": 0, "end": 1, "text": "   ", "words": []},          # chữ rỗng
        {"start": 2.0, "end": 1.0, "text": "a b", "words": [          # mốc ngược
            {"start": 1.0, "end": 1.5, "text": "a"},
            {"start": 1.5, "end": 1.5, "text": "b"}]},                 # từ end<=start
        {"start": 3.0, "end": 3.01, "text": "ngan", "words": []},     # < 0.02 s
    ])
    assert len(ra) == 1
    assert (ra[0]["start"], ra[0]["end"]) == (1.0, 2.0)
    assert [w["word"] for w in ra[0]["words"]] == ["a"]


# ── sửa chữ V5 + từ điển legacy ─────────────────────────────────────────────

def test_ba_tu_dien_legacy_nam_canh_fixer() -> None:
    thu_muc = Path(sua_chu.__file__).parent / "engine"
    for ten in ("vi_corrections.json", "en_corrections.json", "vi_proper_nouns.json"):
        assert (thu_muc / ten).is_file(), ten


def test_v5_sua_tu_VI_theo_tu_dien() -> None:
    doan = sua_chu.chuan_doan_tho([_doan("Hai bà chưng chắc khởi nghĩa.")])
    ra = sua_chu.sua_chu_v5(doan, "vi")
    assert "Trưng Trắc" in ra[0]["text"]
    assert "Trưng" in [w["word"] for w in ra[0]["words"]]


def test_v5_sua_tu_EN_chi_khi_ngon_ngu_la_en() -> None:
    goc = sua_chu.chuan_doan_tho([_doan("Then Croc stands tall.")])
    assert "Grog" in sua_chu.sua_chu_v5(copy.deepcopy(goc), "en")[0]["text"]
    # Ngôn ngữ khác: KHÔNG áp từ điển EN (fixer_v5 set_language).
    assert "Croc" in sua_chu.sua_chu_v5(copy.deepcopy(goc), "vi")[0]["text"]


def test_v5_bo_cau_lap_ao_giac() -> None:
    doan = sua_chu.chuan_doan_tho([
        _doan("Cảm ơn các bạn đã theo dõi.", 0.0),
        _doan("Cảm ơn các bạn đã theo dõi.", 3.0),
    ])
    assert len(sua_chu.sua_chu_v5(doan, "vi")) == 1


# ── kiểm mốc từ (engine/stt.py:113-190) ─────────────────────────────────────

def test_kiem_moc_tu_moi_doan_phai_co_words() -> None:
    with pytest.raises(sua_chu.LoiMocTu):
        sua_chu.kiem_moc_tu([{"start": 0, "end": 1, "words": _tu("a b")},
                             {"start": 1, "end": 2, "words": []}])


def test_kiem_moc_tu_dong_bang_tu_20_phan_tram() -> None:
    dong_bang = [{"start": 5.0, "end": 5.5, "word": "x"} for _ in range(3)]
    tot = [{"start": float(i), "end": i + 0.5, "word": "y"} for i in range(7)]
    with pytest.raises(sua_chu.LoiMocTu, match="frozen"):
        sua_chu.kiem_moc_tu([{"words": dong_bang + tot}])
    assert sua_chu.kiem_moc_tu([{"words": tot}])["total_words"] == 7


# ── sổ hệ + tham số ─────────────────────────────────────────────────────────

def test_min_s_mac_dinh_la_cau_hinh_legacy_dang_chay() -> None:
    assert phien_am.chuan_hoa({"audio": "a.wav"}).min_s == 1.5


def test_he_mac_dinh_la_ltt_va_he_la_bi_tu_choi() -> None:
    yc = phien_am.chuan_hoa({"audio": "a.wav"})
    assert (yc.he, yc.model) == ("ltt", "large-v3")
    yc = phien_am.chuan_hoa({"audio": "a.wav", "he": "ltt_turbo"})
    assert yc.model == sohe.HE["ltt_turbo"].model
    with pytest.raises(phien_am.LoiPhienAm):
        phien_am.chuan_hoa({"audio": "a.wav", "he": "khong_co"})


def test_manifest_khai_he_va_khoa_idempotency_gom_he() -> None:
    from apps.transcript.manifest import MANIFEST

    tool = MANIFEST.tools[0]
    assert tool.params_schema["he"]["values"] == list(sohe.HE)
    assert tool.params_schema["min_s"]["default"] == 1.5
    assert "he" in tool.idempotency["key_fields"]


# ── đường chạy đầy đủ (STT/VAD giả) ─────────────────────────────────────────

def _gia_moi_truong(monkeypatch, tmp_path, tra_theo_lang: dict) -> tuple[Path, list]:
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"x")
    goi: list = []
    monkeypatch.setattr(phien_am, "vad_speech_segments",
                        lambda p: [{"start": 0.0, "end": 8.0}])
    monkeypatch.setattr(phien_am, "audio_duration_seconds", lambda p: 8.0)

    def _stt(duong, *, ten_ho_so, model, ngon_ngu):
        goi.append((model, ngon_ngu))
        return copy.deepcopy(tra_theo_lang.get(ngon_ngu, {"segments": []}))

    monkeypatch.setattr(phien_am.stt, "phien_am", _stt)
    return audio, goi


def test_chay_tu_do_rong_thi_thu_lai_en_roi_vi_va_ap_V5(monkeypatch, tmp_path) -> None:
    kq_vi = {"language": "vi", "language_probability": 0.99, "segments": [
        _doan("Hai bà chưng chắc khởi nghĩa chống giặc.", 0.5, 0.5),
        _doan("Quân dân cả nước cùng đứng lên.", 5.0, 0.4),
    ]}
    audio, goi = _gia_moi_truong(monkeypatch, tmp_path, {"vi": kq_vi})
    kq = phien_am.chay(phien_am.chuan_hoa({"audio": str(audio)}))
    assert [g[1] for g in goi] == [None, "en", "vi"]
    chu = " ".join(d["text"] for d in kq.doan if d["type"] == "speech")
    assert "Trưng Trắc" in chu and "chưng chắc" not in chu
    assert all(set(d) == set(phien_am.KHOA_DAY_DU) for d in kq.doan)
    assert kq.ngon_ngu == "vi"


def test_chay_he_turbo_goi_dung_model(monkeypatch, tmp_path) -> None:
    kq_en = {"language": "en", "language_probability": 0.99, "segments": [
        _doan("Grog stands tall with a pickaxe in hand.", 0.5, 0.5)]}
    audio, goi = _gia_moi_truong(monkeypatch, tmp_path, {"en": kq_en})
    phien_am.chay(phien_am.chuan_hoa(
        {"audio": str(audio), "language": "en", "he": "ltt_turbo"}))
    assert goi == [(sohe.HE["ltt_turbo"].model, "en")]

"""
test_610 — TRẦN VĂN BẢN của `speech.ltt`: 1.500 ký tự, KHÔNG NỚI. (H43 Phase 05)

Trần đặt ở `ToolSpec.params_schema["text"]["max_length"]` = `TRAN_KY_TU_CONG_KHAI`
(Q119: trần CHẤT LƯỢNG, nới phải qua cổng V10). Cửa nội bộ `bao_gia` kiểm ngay ở
`validate_tool_params` — trước tiền, trước hàng đợi, trước GPU.

Neo ở đây:
  1. 1.501 ký tự ⇒ `ThamSoSai` ở `bao_gia`; 1.500 thì qua. Hằng số vẫn 1.500.
  2. `features.chuan_hoa` KHÔNG cắt bớt và KHÔNG kiểm bằng số gõ tay (đúng thiết kế:
     cửa là schema; văn bản dài đi đường chia lượt, không bị cắt im lặng).
  3. Cổng trả 413 ⇒ `LoiGiongNoi` (lỗi người gọi, không thử lại).
  4. Từ điển riêng nở văn bản quá `3×thô + 200` ⇒ `LoiGiongNoi` TRƯỚC khi gọi cổng;
     văn bản thường (không nở) thì qua bình thường.
"""
from __future__ import annotations

import uuid

import pytest

TOOL = "speech.ltt"


@pytest.fixture()
def moi_truong(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       "sqlite:///" + (tmp_path / "tieng610.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_VOICE_SIDECAR_TOKEN", "thu-nghiem-610")
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    import apps.ltt_voice.tables  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core import storage
    storage.set_storage(storage.LocalStorage(str(tmp_path / "kho")))
    yield
    storage.set_storage(None)
    dbmod.reset_engine()


# ── 1. Trần ở cửa báo giá ───────────────────────────────────────────────────

def test_tran_la_1500_va_khong_noi():
    from apps.ltt_voice import tham_so_cong_khai as ts
    from apps.ltt_voice.manifest import MANIFEST
    tool = next(t for t in MANIFEST.tools if t.name == TOOL)
    assert tool.params_schema["text"]["max_length"] == ts.TRAN_KY_TU_CONG_KHAI
    assert ts.TRAN_KY_TU_CONG_KHAI <= 1500, "noi tran phai qua cong V10, khong qua test"
    assert ts.TRAN_MOI_LUOT_SINH == 1500


def test_bao_gia_tu_choi_1501_nhan_1500():
    from platform_core.runtime_noi_bo import job as rj
    with pytest.raises(rj.ThamSoSai, match="text"):
        rj.bao_gia(TOOL, {"text": "a" * 1501})
    bg = rj.bao_gia(TOOL, {"text": "a" * 1500})
    assert bg.credit > 0 and len(bg.tham_so_sach["text"]) == 1500


# ── 2. features không cắt, không tự đặt số ──────────────────────────────────

def test_chuan_hoa_khong_cat_bot_van_ban():
    from apps.ltt_voice import features
    dai = "b" * 1501
    assert features.chuan_hoa({"text": dai}).text == dai


def test_chuan_hoa_khong_go_tay_tran_ky_tu():
    """Trần thuộc schema/cổng; lặp lại một con số ở đây là hai bản sao sẽ lệch."""
    import inspect
    from apps.ltt_voice import features
    nguon = inspect.getsource(features.chuan_hoa)
    assert "1500" not in nguon and "1_500" not in nguon


# ── 3. Cổng 413 ⇒ lỗi người gọi ─────────────────────────────────────────────

def test_cong_tra_413_la_loi_nguoi_goi(monkeypatch):
    from platform_core import jobs as jobq
    from apps.ltt_voice import features, sidecar_client

    def _413(*a, **k):
        raise sidecar_client.VanBanQuaDai("qua dai")

    monkeypatch.setattr(sidecar_client, "noi", _413)
    with pytest.raises(features.LoiGiongNoi) as e:
        features.goi_cong("x", preset="p")
    assert isinstance(e.value, jobq.LoiNguoiGoi)


# ── 4. Từ điển riêng không được khuếch đại chi phí ──────────────────────────

def _handle_voi_tu_dien(monkeypatch, *, text: str, tu_dien: dict, owner: str):
    from apps.ltt_voice import giong_mau, jobs as vj, sidecar_client, tu_dien_rieng

    goi = []

    def _noi(*a, **k):
        goi.append(a)
        return b"RIFFxxxxWAVEfmt ", {"X-Duration-S": "1.0"}

    monkeypatch.setattr(sidecar_client, "noi", _noi)
    monkeypatch.setattr(sidecar_client, "noi_dai", _noi)
    monkeypatch.setattr(tu_dien_rieng, "nhu_dict", lambda db, o: dict(tu_dien))
    monkeypatch.setattr(vj, "_do_thoi_luong", lambda p: 1.0)
    kq = vj.handle({"text": text, "preset": giong_mau.MAC_DINH, "owner_id": owner,
                    "_job_type": "ltt_voice.synthesize"})
    return kq, goi


def test_tu_dien_no_qua_3x_cong_200_bi_chan_TRUOC_khi_goi_cong(moi_truong, monkeypatch):
    from platform_core import jobs as jobq
    from apps.ltt_voice import features, tu_dien_rieng

    tho = ("a " * 100).strip()                        # 199 ký tự thô ⇒ trần 797
    no = {"a": "x" * tu_dien_rieng.TRAN_THAY}          # mỗi "a" nở thành 160
    with pytest.raises(features.LoiGiongNoi) as e:
        _handle_voi_tu_dien(monkeypatch, text=tho, tu_dien=no, owner=str(uuid.uuid4()))
    assert isinstance(e.value, jobq.LoiNguoiGoi)
    assert "từ điển" in str(e.value).lower()


def test_tu_dien_thuong_khong_bi_chan(moi_truong, monkeypatch):
    tho = "Công ty LTT chào bạn, hôm nay là một ngày đẹp trời để làm việc."
    kq, goi = _handle_voi_tu_dien(monkeypatch, text=tho,
                                  tu_dien={"LTT": "e lờ tê tê"},
                                  owner=str(uuid.uuid4()))
    assert len(goi) == 1 and "e lờ tê tê" in kq["text"]
    assert len(kq["text"]) <= len(tho) * 3 + 200

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

def test_tran_cong_khai_khop_schema_va_tran_chat_luong_van_1500():
    """🔴 PHÉP KIỂM NÀY ĐÃ ĐỔI 03/09/2026, và chỗ đổi mới là chỗ đáng đọc.

    Bản trước tên là `test_tran_la_1500_va_khong_noi` và chốt
    `TRAN_KY_TU_CONG_KHAI <= 1500` kèm câu *"nới trần phải qua cổng V10, không
    qua test"*. Câu ấy **đúng** — và nó đã làm đúng việc của nó: nó đỏ đúng lúc
    trần được nới, buộc người nới phải quay lại đây và nói ra bằng chứng.

    ⭐ Nhưng nó chốt NHẦM HẰNG SỐ. Thứ Q119 bảo vệ là chỗ **giọng bắt đầu trôi**
       — tức trần của MỘT LƯỢT SINH. Trần của một YÊU CẦU là chuyện khác: nó là
       ngân sách tài nguyên. Trước 03/09 hai con số bằng nhau nên không ai phải
       phân biệt, và phép kiểm gọi tên con số dễ thấy hơn.

    ⇒ Nay nó chốt đúng thứ nó vốn muốn canh: **trần chất lượng vẫn là 1.500**.
      Trần yêu cầu được phép khác, và `tests/test_338` chốt nó nằm trong ngân
      sách thời gian job lẫn trần định dạng WAV.

    ⚠️ NÓI CHO ĐÚNG VỀ BẰNG CHỨNG: trần công khai được nới sau **một vòng đo**
       (`tools/do_bai_dai.py`, 03/09) chứ không phải sau một lượt cổng V10 đầy
       đủ. Bốn tài liệu độc lập và 17 đoạn cùng chỉ một hướng — bản ghép tốt hơn
       bản một lượt trên mọi chỉ số ASR, và tương đồng người nói không tụt dưới
       sàn nhiễu của chính nó ở bất kỳ độ dài nào. Chi tiết ở
       `apps/ltt_voice/tham_so_cong_khai.py`.
    """
    from apps.ltt_voice import tham_so_cong_khai as ts
    from apps.ltt_voice.manifest import MANIFEST
    tool = next(t for t in MANIFEST.tools if t.name == TOOL)
    assert tool.params_schema["text"]["max_length"] == ts.TRAN_KY_TU_CONG_KHAI
    assert ts.TRAN_MOI_LUOT_SINH == 1500, (
        "tran CHAT LUONG cua mot luot sinh la thu Q119 bao ve — noi no van "
        "phai qua cong V10, khong qua test")


def test_bao_gia_tu_choi_vuot_tran_nhan_dung_tran():
    """Cửa nội bộ vẫn chặn TRƯỚC tiền, trước hàng đợi, trước GPU.

    ⭐ Chốt theo `TRAN_KY_TU_CONG_KHAI` chứ không theo một con số gõ tay: phép
       bảo vệ ở đây là *"vượt trần thì bị từ chối ở cửa"*, và mệnh đề ấy không
       đổi khi con số đổi. Gõ tay `1501` là buộc phép kiểm phải sửa mỗi lần trần
       đổi, và mỗi lần sửa là một cơ hội sửa nhầm thành không kiểm gì cả.
    """
    from apps.ltt_voice.tham_so_cong_khai import TRAN_KY_TU_CONG_KHAI as TRAN
    from platform_core.runtime_noi_bo import job as rj
    with pytest.raises(rj.ThamSoSai, match="text"):
        rj.bao_gia(TOOL, {"text": "a" * (TRAN + 1)})
    bg = rj.bao_gia(TOOL, {"text": "a" * TRAN})
    assert bg.credit > 0 and len(bg.tham_so_sach["text"]) == TRAN


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

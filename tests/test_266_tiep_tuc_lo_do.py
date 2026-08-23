"""
test_266 — tiếp tục một lô đo đang dở. (H37)

Không mạng, không GPU.

⛔ SỰ CỐ THẬT 22/08/2026. Máy B tự khởi động lại để cài cập nhật Windows lúc 01:29,
   cuốn theo lô `s90` đang chạy ở **ảnh 21/30**.

   Lần đó đã sửa một nửa: ghi kết quả **sau mỗi ảnh** thay vì đợi cuối lô, nên số
   đo của 20 ảnh không mất nữa. Nhưng chạy lại vẫn **làm lại từ ảnh 1** — trả tiền
   GPU hai lần cho phần đã xong, và với lô 30 ảnh thì đó là **32 phút**.

⭐ Nửa còn lại: bỏ qua ảnh đã xong. Một lần khởi động lại nay chỉ mất **đúng một
   ảnh đang chạy**.

   Điều này quan trọng hơn nó trông có vẻ: nó làm **mốc 01:00 hết là một hạn chót**.
   Không cần đổi chính sách Windows Update — thứ vốn là một thiết lập bảo mật và có
   cái giá riêng (máy tích luỹ bản vá chưa áp).
"""
from __future__ import annotations

import json
import types

import pytest

from render_gateway.deploy import chay_baseline as CB


def _viet_ckpt(tep, *, cau_hinh, mode, runs):
    tep.write_text(json.dumps({
        "ca": "thu", "ngay": "2026-08-22T18:29:00+00:00",
        "cau_hinh": cau_hinh, "mode": mode, "runs": runs,
    }, ensure_ascii=False), encoding="utf-8")


def _doc_lai(tep):
    return json.loads(tep.read_text(encoding="utf-8"))


# Bản sao NGUYÊN VĂN của khối quyết định trong `chay_baseline`. Tách ra để test
# được mà không phải chạm GPU — và có một test bên dưới chốt rằng nó không trôi
# khỏi bản gốc.
def _quyet_dinh(tep, cau_hinh, mode, lam_lai):
    ket_qua = {"cau_hinh": cau_hinh, "mode": mode, "runs": []}
    xong_roi: set = set()
    if tep.exists() and not lam_lai:
        try:
            cu = json.loads(tep.read_text(encoding="utf-8"))
            if not isinstance(cu, dict):
                raise ValueError("checkpoint khong phai mot doi tuong JSON")
            if cu.get("cau_hinh") == ket_qua["cau_hinh"] and cu.get("mode") == mode:
                giu = [r for r in (cu.get("runs") or []) if r.get("ok")]
                if giu:
                    ket_qua["runs"] = giu
                    ket_qua["tiep_tuc_tu"] = cu.get("ngay")
                    xong_roi = {r.get("id") for r in giu}
        except (OSError, ValueError):
            pass
    return ket_qua, xong_roi


CAU_HINH = {"steps": 50, "width": 2560, "height": 1440}


# ═══════════ tiếp tục ═══════════════════════════════════════════════════════
def test_bo_qua_dung_nhung_anh_DA_XONG(tmp_path):
    """Cảnh thật 22/08: chết ở ảnh 21/30. Chạy lại chỉ còn 10 ảnh."""
    tep = tmp_path / "s90.json"
    _viet_ckpt(tep, cau_hinh=CAU_HINH, mode="t2i",
               runs=[{"id": f"p{i:02d}", "ok": True, "giay": 96} for i in range(1, 21)])
    _kq, xong = _quyet_dinh(tep, CAU_HINH, "t2i", lam_lai=False)
    assert len(xong) == 20
    assert "p01" in xong and "p21" not in xong


def test_GIU_LAI_so_do_cua_phan_da_xong(tmp_path):
    """Bỏ qua mà không giữ số đo thì phần đã chạy biến mất khỏi kết quả cuối."""
    tep = tmp_path / "s90.json"
    runs = [{"id": "p01", "ok": True, "giay": 96.5, "vram_dinh": 17600}]
    _viet_ckpt(tep, cau_hinh=CAU_HINH, mode="t2i", runs=runs)
    kq, _ = _quyet_dinh(tep, CAU_HINH, "t2i", lam_lai=False)
    assert kq["runs"] == runs
    assert kq["tiep_tuc_tu"] == "2026-08-22T18:29:00+00:00"


def test_anh_HONG_thi_CHAY_LAI_chu_khong_giu(tmp_path):
    """⛔ Giữ một `ok=False` lại là **đóng băng một thất bại thành một kết quả** —
    lô cuối cùng sẽ báo "đã chạy 30 ảnh" trong khi có ảnh chưa từng thành công."""
    tep = tmp_path / "s90.json"
    _viet_ckpt(tep, cau_hinh=CAU_HINH, mode="t2i", runs=[
        {"id": "p01", "ok": True}, {"id": "p02", "ok": False, "loi": "oom"}])
    kq, xong = _quyet_dinh(tep, CAU_HINH, "t2i", lam_lai=False)
    assert xong == {"p01"}
    assert all(r["ok"] for r in kq["runs"])


# ═══════════ ⛔ không được trộn hai lô khác cấu hình ════════════════════════
def test_CAU_HINH_KHAC_thi_chay_lai_tu_dau(tmp_path):
    """⛔ Số đo ở 36 bước **không so được** với số đo ở 50 bước. Tiếp tục ngang qua
    một thay đổi cấu hình là trộn hai lô làm một, và không ai biết dòng nào thuộc
    lô nào — một tệp kết quả trông hoàn toàn bình thường."""
    tep = tmp_path / "s90.json"
    _viet_ckpt(tep, cau_hinh={**CAU_HINH, "steps": 36}, mode="t2i",
               runs=[{"id": "p01", "ok": True}])
    kq, xong = _quyet_dinh(tep, CAU_HINH, "t2i", lam_lai=False)
    assert xong == set() and kq["runs"] == []


def test_CHE_DO_KHAC_thi_chay_lai_tu_dau(tmp_path):
    """`t2i` và `subject` là hai phép đo khác nhau dù cùng số bước."""
    tep = tmp_path / "s90.json"
    _viet_ckpt(tep, cau_hinh=CAU_HINH, mode="subject",
               runs=[{"id": "p01", "ok": True}])
    _kq, xong = _quyet_dinh(tep, CAU_HINH, "t2i", lam_lai=False)
    assert xong == set()


def test_co_LAM_LAI_thi_bo_qua_checkpoint(tmp_path):
    tep = tmp_path / "s90.json"
    _viet_ckpt(tep, cau_hinh=CAU_HINH, mode="t2i",
               runs=[{"id": "p01", "ok": True}])
    _kq, xong = _quyet_dinh(tep, CAU_HINH, "t2i", lam_lai=True)
    assert xong == set()


# ═══════════ hỏng thì chạy lại, không làm hỏng cả lô ═══════════════════════
@pytest.mark.parametrize("noi_dung", ["", "{khong phai json", "[]", "null"])
def test_checkpoint_HONG_thi_chay_lai_tu_dau_chu_khong_no(tmp_path, noi_dung):
    """Một tệp checkpoint hỏng không được phép chặn cả phiên đo — nhất là khi phiên
    đó chỉ có một cửa sổ GPU."""
    tep = tmp_path / "s90.json"
    tep.write_text(noi_dung, encoding="utf-8")
    kq, xong = _quyet_dinh(tep, CAU_HINH, "t2i", lam_lai=False)
    assert xong == set() and kq["runs"] == []


def test_chua_co_checkpoint_thi_chay_binh_thuong(tmp_path):
    kq, xong = _quyet_dinh(tmp_path / "chua-co.json", CAU_HINH, "t2i", lam_lai=False)
    assert xong == set() and kq["runs"] == []


# ═══════════ bản sao trong test không được trôi khỏi bản gốc ════════════════
def test_ban_goc_van_co_du_bon_dieu_kien():
    """Khối quyết định ở trên là **bản sao** để test chạy được không cần GPU. Nếu
    bản gốc đổi mà bản sao không đổi thì tệp này kiểm một thứ đã không còn tồn tại."""
    import inspect

    ma = inspect.getsource(CB)
    for phai_co in ('cu.get("cau_hinh") == ket_qua["cau_hinh"]',
                    'cu.get("mode") == a.mode',
                    'if r.get("ok")',
                    "not a.lam_lai",
                    "isinstance(cu, dict)",
                    'if pr["id"] in xong_roi'):
        assert phai_co in ma, f"ban goc thieu: {phai_co}"


def test_co_co_LAM_LAI_tren_dong_lenh():
    import inspect

    assert '"--lam-lai"' in inspect.getsource(CB)

"""`edit_plan` ⛔ KHÔNG còn gọi model — nên trần 2 request/model không còn áp.

🔴 **26/09/2026 — cả tệp này ĐỔI KỲ VỌNG, GIỮ Ý ĐỊNH** (B1 §9b, năm căn cứ).

Bản cũ chốt bốn mệnh đề về việc hỏi VLM **song song**: trần `LO_DOC_CANH = 2`,
mỗi luồng một `Session`, thứ tự cảnh, và phần mạng mất `ceil(N/2)` lượt. Cả bốn
tồn tại vì giai đoạn này **gọi model**.

⭐ Từ 26/09 nó ⛔ không gọi model nào: ba tiêu chí của nó — *không có lời thoại* ·
   *tối đen* · *đứng hình* — đo bằng **số học trên bản chép lời** +
   `ffmpeg blackdetect` + `ffmpeg freezedetect`.

⇒ Ý định cũ (*"⛔ không được vượt trần máy B, vì 19/09/2026 khoá duy nhất
  `ltt_llm` chết và cả LLM sập"*) được giữ ở dạng **mạnh hơn hẳn**: 0 request thì
  ⛔ không trần nào bị vượt. Bốn mục dưới chốt đúng bốn mệnh đề cũ, ở dạng mới:

  §1 TRẦN     0 request/model, và ⛔ không suất `llm_remote` nào bị giữ.
  §2 PHIÊN    ⛔ không luồng nào, nên ⛔ không `Session` nào dùng chung được.
  §3 THỨ TỰ   kết quả vẫn đi theo thứ tự CẢNH — mệnh đề này ⛔ không đổi.
  §4 TỐC ĐỘ   phần mạng = **0 lượt**, và phần ffmpeg = **1 lượt** cho mọi N.

⛔ Không phép nào ở đây gọi model thật, và nay ⛔ không phép nào gọi model giả.
"""
from __future__ import annotations

import ast
import inspect

import pytest

from apps.auto_scan_video import (canh as canh_mod,
                                  giai_doan_ban_bien_tap as gdbbt)


def _ci(n: int):
    return canh_mod.ChiMucCanh(
        tuple(canh_mod.Canh(f"canh_{i + 1:04d}", float(i), float(i) + 1.0,
                            (float(i) + 0.5,)) for i in range(n)), float(n))


def _ban_ghi(*khoang):
    return {"doan": [{"ma": f"d{i}", "bat": b, "ket": k, "chu": "xin chao"}
                     for i, (b, k) in enumerate(khoang)]}


def _ten_duoc_goi(nguon: str) -> set[str]:
    ra: set[str] = set()
    for n in ast.walk(ast.parse(nguon)):
        if isinstance(n, ast.Call):
            f = n.func
            ra.add(f.id if isinstance(f, ast.Name) else getattr(f, "attr", ""))
    return ra


# ══════════════════════════════════════════════════════════════════════════════
#  §1  TRẦN — 0 request/model, nên trần của máy B không còn áp
# ══════════════════════════════════════════════════════════════════════════════

def test_tran_lo_la_2_va_khong_tham_so_nao_noi_no_ra():
    """🔴 **KỲ VỌNG ĐỔI.** Bản cũ: *`LO_DOC_CANH` phải là hằng số gõ thẳng, ⛔
    không một biến môi trường nào được nới trần 2 request/model trên máy
    production mà ⛔ không ai thấy trong diff.*

    ⭐ Dạng mạnh hơn: ⛔ **không còn hằng số nào để nới**, vì ⛔ không còn lời
       gọi nào. Một `LO_DOC_CANH` quay lại nghĩa là lối gọi model quay lại — và
       đó đúng là thứ phải đỏ ở đây.
    """
    for cam in ("LO_DOC_CANH", "SO_LAN_DOC_CANH", "_doc_cac_canh", "_CtxLo",
                "_ma_don_vi_goi"):
        assert not hasattr(gdbbt, cam), (
            f"`{cam}` quay lai — edit_plan lai goi model, xem B1 §9b")


def test_tran_may_B_duoc_chung_minh_boi_HAI_rao_doc_lap():
    """🔴 **KỲ VỌNG ĐỔI, và rào cũ biến thành một PHÉP TRỪ.**

    Bản cũ: `1 job (nền tảng) × 2 luồng (trong job) = 2 request. Hết.`
    Bản nay: `0 lời gọi × bất kỳ = 0 request. Hết.`

    ⛔ Và `tai_nguyen` phải RỖNG. Trước đây nó khai `llm_remote` **TĨNH**, nên
       với preset giữ hình nó ⛔ không gọi gì mà **VẪN** giữ suất LLM duy nhất
       của cả máy suốt giai đoạn. Đo 26/09: hai lượt cùng preset, `edit_plan`
       mất **2,8 s** và **205,7 s** — 203 giây chênh là XẾP HÀNG.
    """
    from apps.auto_scan_video import pipeline

    g = pipeline.THEO_TEN["edit_plan"]
    assert g.tai_nguyen == "", g.tai_nguyen
    assert g.tai_nguyen_suat == 0, g.tai_nguyen_suat
    # `content_process` VẪN giữ suất — nó vẫn gọi LLM để dịch.
    assert pipeline.THEO_TEN["content_process"].tai_nguyen == "llm_remote"


def test_pool_khai_dung_LO_DOC_CANH_lam_max_workers():
    """🔴 **KỲ VỌNG ĐỔI.** Bản cũ: `max_workers` phải LÀ hằng số trần, ⛔ không
    một số gõ tay. ⇒ Nay: ⛔ **không có pool nào**, nên ⛔ không có `max_workers`
    nào để gõ sai."""
    ten = _ten_duoc_goi(inspect.getsource(gdbbt))
    assert "ThreadPoolExecutor" not in ten
    assert "submit" not in ten
    assert "threading" not in inspect.getsource(gdbbt)


@pytest.mark.parametrize("so_canh", [1, 2, 4, 5])
def test_khong_bao_gio_vuot_2_request_dong_thoi(monkeypatch, so_canh):
    """PHÉP ĐO: số lời gọi model THẬT SỰ, đếm bằng một cửa sẽ NỔ nếu bị gọi.

    ⭐ Đối chứng nằm trong chính phép đo: nếu `_do_cac_canh` lỡ gọi `ai`, bài này
       nổ thành `AssertionError` chứ ⛔ không im lặng xanh.
    """
    from apps.auto_scan_video import ai

    def _no(*a, **k):
        raise AssertionError("edit_plan da goi model — VUOT TRAN MAY B")

    monkeypatch.setattr(ai, "goi_tinh_tien", _no)
    monkeypatch.setattr(ai, "goi", _no)
    monkeypatch.setattr(gdbbt.qc, "do_hinh",
                        lambda *a, **k: {"khoang_den": [], "khoang_dong": []})

    hieu, hong = gdbbt._do_cac_canh("phim.mp4", _ci(so_canh),
                                    _ban_ghi((0.1, 0.2)))
    assert not hong, hong
    assert len(hieu) == so_canh


# ══════════════════════════════════════════════════════════════════════════════
#  §2  PHIÊN — ⛔ không luồng nào, nên ⛔ không `Session` nào dùng chung được
# ══════════════════════════════════════════════════════════════════════════════

def test_moi_luong_mot_phien_rieng_va_run_doc_lai():
    """🔴 **KỲ VỌNG ĐỔI.** Vật cản số 2 của `L_TOC_DO_GPU.md` §5.2 là *"một
    `Session` SQLAlchemy dùng chung giữa hai luồng"*.

    ⭐ Dạng mạnh hơn: phép đo ⛔ **không nhận `db`** nữa. Một hàm thuần ⛔ không
       thể dùng chung một `Session` với ai.
    """
    tham_so = set(inspect.signature(gdbbt._do_cac_canh).parameters)
    assert tham_so == {"duong", "ci", "ban_ghi"}, tham_so
    assert "su_dung" not in inspect.getsource(gdbbt)


def test_ctx_trong_lo_KHONG_xoa_mo_ho_cua_provider():
    """🔴 **KỲ VỌNG ĐỔI.** Bản cũ: `provider_state` là MỘT ô cho HAI lời gọi
    đang bay, nên `_CtxLo` phải **bỏ** `provider_rejected`.

    ⭐ Dạng mạnh hơn: ⛔ không lời gọi nào bay, nên ⛔ không ai chạm tới
       `provider_state` — `_CtxLo` biến mất cùng lý do tồn tại của nó.
    """
    ma = inspect.getsource(gdbbt)
    for cam in ("provider_rejected", "provider_dispatched", "_CtxLo"):
        assert cam not in ma, f"`{cam}` con trong edit_plan"


# ══════════════════════════════════════════════════════════════════════════════
#  §3  THỨ TỰ — kết quả đi theo thứ tự CẢNH. ⭐ Mệnh đề này ⛔ KHÔNG đổi.
# ══════════════════════════════════════════════════════════════════════════════

def test_ket_qua_theo_dung_thu_tu_canh_du_luong_nao_ve_truoc(monkeypatch):
    """⭐ Mệnh đề duy nhất của tệp cũ **sống nguyên**: `ban_bien_tap.lap_ban` ghép
    bằng chứng theo `ma_canh`, nhưng `QuyetDinh` đi theo thứ tự `chi_muc.canh` —
    nên một bằng chứng lệch thứ tự sẽ ghép sai cảnh."""
    monkeypatch.setattr(gdbbt.qc, "do_hinh", lambda *a, **k: {
        "khoang_den": [[3.0, 4.0]], "khoang_dong": []})
    hieu, hong = gdbbt._do_cac_canh("phim.mp4", _ci(5), _ban_ghi((0.1, 0.2)))
    assert not hong
    assert [h.ma_canh for h in hieu] == [f"canh_{i:04d}" for i in range(1, 6)]
    # Và bằng chứng phải khớp ĐÚNG cảnh: chỉ `canh_0004` là [3,4).
    assert [h.de_xuat for h in hieu] == ["giu", "giu", "giu", "bo", "giu"]


def test_lat_cat_tien_do_khong_bao_gio_ghi_lui():
    """🔴 **KỲ VỌNG ĐỔI.** Bản cũ: `lc.xong_mot()` chạy mỗi CẢNH, tuần tự, nên
    `da_lam` phải đơn điệu — ghi lùi nghĩa là một lượt tiếp nối sau đó sẽ hỏi
    (và **trả tiền**) lại một cảnh đã hỏi.

    ⭐ Nay ⛔ không cảnh nào tốn tiền riêng, nên điểm chốt theo CẢNH biến mất và
       giai đoạn còn **đúng một** điểm chốt: chỉ mục cảnh. Ý định được giữ ở chỗ
       nó vẫn là một điểm chốt THẬT (một lần tách cảnh trên video 120 phút là một
       lệnh ffmpeg dài), và `lc.kiem`/`lc.xong_mot` ⛔ không nằm trong vòng lặp.
    """
    cay = ast.parse(inspect.getsource(gdbbt.chay))
    trong_vong: set[str] = set()
    for nut in ast.walk(cay):
        if isinstance(nut, (ast.For, ast.While, ast.AsyncFor)):
            trong_vong |= _ten_duoc_goi(ast.unparse(nut))
    assert "kiem" not in trong_vong and "xong_mot" not in trong_vong, (
        "diem chot cua edit_plan nam trong mot vong lap — no chi con MOT don vi")
    ma = inspect.getsource(gdbbt.chay)
    assert 'trang_thai={"chi_muc"' in ma, "chi muc canh khong duoc chot lai"


# ══════════════════════════════════════════════════════════════════════════════
#  §4  TỐC ĐỘ — phần mạng = 0 lượt, phần ffmpeg = 1 lượt cho MỌI N
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("so_canh", [1, 2, 4, 8, 64])
def test_phan_mang_mat_ceil_N_tren_2_luot(monkeypatch, so_canh):
    """🔴 **KỲ VỌNG ĐỔI, và đây là chỗ tệp này nói cái gì đã được MUA.**

    Bản cũ đo: 4 cảnh × 1 lời gọi = `ceil(4/2)` = **2 lượt mạng** (163,78 s cho
    4 lời gọi tuần tự, `L_TOC_DO_GPU.md` §5.2).

    ⭐ Bản nay: **0 lượt mạng**, và phần ffmpeg là **MỘT** lượt giải mã cho cả
       tệp — ⛔ không phụ thuộc số cảnh. Trước đó là N lần rút khung + N lời gọi.
    """
    dem = {"n": 0}

    def _do(*a, **k):
        dem["n"] += 1
        return {"khoang_den": [], "khoang_dong": []}

    monkeypatch.setattr(gdbbt.qc, "do_hinh", _do)
    hieu, hong = gdbbt._do_cac_canh("phim.mp4", _ci(so_canh),
                                    _ban_ghi((0.1, 0.2)))
    assert len(hieu) == so_canh and not hong
    assert dem["n"] == 1, (
        f"{so_canh} canh ma goi ffmpeg {dem['n']} lan — phep do phai la MOT "
        f"luot giai ma cho ca tep")

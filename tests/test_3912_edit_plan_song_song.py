"""`edit_plan` hỏi VLM SONG SONG — và trần 2 request/model là trần của máy B.

Đo 23/09 (`docs/auto_scan_video_final/L_TOC_DO_GPU.md` §5.2): `edit_plan`
**163,78 s** cho **4** lời gọi `DOC_CANH` chạy **lần lượt**. Tệp này chốt bốn
mệnh đề, và ba trong bốn là **bất biến an toàn**, không phải hiệu năng:

  §1 TRẦN     ≤ `LO_DOC_CANH` = 2 request đồng thời. 🔴 Vượt trần làm sập pool
              máy B — 19/09/2026 khoá duy nhất `ltt_llm` chết, cả LLM sập.
  §2 PHIÊN    mỗi luồng một `Session` RIÊNG và một `run` đọc lại trong phiên đó.
              ⛔ Một `Session` SQLAlchemy dùng chung giữa hai luồng là vật cản
              số 2 mà `L_TOC_DO_GPU.md` §5.2 ghi.
  §3 THỨ TỰ   `lat_cat` đi tiến theo đúng thứ tự cảnh, và kết quả trả về cũng
              vậy — dù luồng nào về đích trước.
  §4 TỐC ĐỘ   phần MẠNG của N cảnh mất ~`ceil(N/2)` lượt, không `N` lượt.

⛔ Không phép nào ở đây gọi model thật.
"""
from __future__ import annotations

import ast
import inspect
import json
import threading
import time

import pytest

# ruff: noqa: F811 — fixture nhập từ `test_402` rồi nhận lại làm tham số; cả bộ
#   test ASV làm thế, đây không phải định nghĩa trùng.
from tests.test_402_asv_mach_doc_gia import db, kho_tam, _tao_run  # noqa: F401

from apps.auto_scan_video import (canh as canh_mod,  # noqa: E402
                                  giai_doan_ban_bien_tap as gdbbt)

#: Mỗi lời gọi giả "chạy" bao lâu. Đủ dài để hai lượt chồng nhau đo được, đủ
#: ngắn để cả tệp vẫn là lệnh **Vừa** (`docs/QUY_TAC_CHAY_LENH_NANG.md` §1).
GIAY_MOT_GOI = 0.40


def _ci(n: int):
    return canh_mod.ChiMucCanh(
        tuple(canh_mod.Canh(f"canh_{i + 1:04d}", float(i), float(i) + 1.0,
                            (float(i) + 0.5,)) for i in range(n)), float(n))


def _tra_loi(ma: str) -> dict:
    return {"noi_dung": json.dumps(
        {"loai": "canh", "chu_the": [], "hanh_dong": "", "cam_xuc": "",
         "quan_trong": 0.9, "de_xuat": "giu", "do_tin": 0.9,
         "ly_do": "", "canh_bao": []}, ensure_ascii=False),
        "finish_reason": "stop", "suy_nghi": "", "model": "gia",
        "ma_canh": ma}


class _CtxGia:
    """`ctx` tối thiểu. Đếm mọi lời gọi để §2 nói được cái gì bị chặn."""

    def __init__(self) -> None:
        self.job_id = "job-3902"
        self.da_tu_choi = 0
        self.da_gui = 0
        self.tien_do = 0

    def is_cancelled(self) -> bool:
        return False

    def provider_dispatched(self, provider: str = "") -> None:
        self.da_gui += 1

    def provider_rejected(self, provider: str = "") -> None:
        self.da_tu_choi += 1

    def progress(self, percent: int, message: str = "") -> None:
        self.tien_do += 1


class _Theo:
    """Bộ đếm đồng thời. `dinh` là số lời gọi CHỒNG NHAU cao nhất đã thấy."""

    def __init__(self) -> None:
        self.khoa = threading.Lock()
        self.dang = 0
        self.dinh = 0
        self.tong = 0
        self.phien: list = []
        self.run_khac_phien = []
        self.thu_tu: list = []


def _chuan_bi(db, monkeypatch, so_canh: int):
    """Vá ba cửa ra ngoài của `_doc_cac_canh`, trả về (run, ci, theo, ctx)."""
    run = _tao_run(db, owner="u3902")
    db.commit()

    theo = _Theo()
    ctx = _CtxGia()

    monkeypatch.setattr(gdbbt, "_nguon_soi_duoc", lambda *a, **k: "khong-dung")
    # `loi_nhac_canh` base64-hoá từng khung ⇒ khung phải là BYTES.
    monkeypatch.setattr(gdbbt, "_rut_khung", lambda duong, moc: tuple(
        f"khung-{i}".encode() for i in range(len(moc or ()))))

    def _goi_gia(db2, run2, thao_tac, messages, *, stage, item_key, ctx=None,
                 **_k):
        with theo.khoa:
            theo.dang += 1
            theo.dinh = max(theo.dinh, theo.dang)
            theo.tong += 1
            theo.phien.append(id(db2))
            theo.run_khac_phien.append(run2 is not run)
            theo.thu_tu.append(item_key)
        try:
            time.sleep(GIAY_MOT_GOI)
            return _tra_loi(item_key)
        finally:
            with theo.khoa:
                theo.dang -= 1

    monkeypatch.setattr(gdbbt.ai, "goi_tinh_tien", _goi_gia)
    return run, _ci(so_canh), theo, ctx


# ══════════════════════════════════════════════════════════════════════════════
#  §1  TRẦN — 2 request đồng thời mỗi model, và nó là trần của MÁY B
# ══════════════════════════════════════════════════════════════════════════════

def test_tran_lo_la_2_va_khong_tham_so_nao_noi_no_ra():
    """🔴 `LO_DOC_CANH` phải là 2, và ⛔ không được đọc từ môi trường.

    Trần vận hành của kho là **≤ 2 request đồng thời mỗi model** (CLAUDE.md mục
    ⭐). `qwen38-api` khai 3 suất engine, nhưng bản khai chặt hơn thắng. Một biến
    môi trường ở đây là một cách để trần bị nới trên máy production mà không ai
    thấy trong diff.
    """
    assert gdbbt.LO_DOC_CANH == 2
    nguon = inspect.getsource(gdbbt)
    cay = ast.parse(nguon)
    for nut in ast.walk(cay):
        if not (isinstance(nut, ast.Assign) and len(nut.targets) == 1):
            continue
        t = nut.targets[0]
        if isinstance(t, ast.Name) and t.id == "LO_DOC_CANH":
            assert isinstance(nut.value, ast.Constant), (
                "LO_DOC_CANH phai la mot HANG SO go thang, khong phai bieu thuc")


def test_tran_may_B_duoc_chung_minh_boi_HAI_rao_doc_lap():
    """🔴 `2 luong` an toàn CHỈ vì `edit_plan` giữ một suất `llm_remote` DUY NHẤT.

    ⛔ Đây là phép kiểm quan trọng nhất của tệp. `max_workers=2` một mình **không**
       chứng minh "≤ 2 request/model": nếu hai lần chạy ASV cùng vào `edit_plan`
       thì 2 × 2 = **4** request trên một model, tức vượt trần — đúng sự cố 19/09
       (khoá duy nhất `ltt_llm` chết, cả LLM sập).

    ⭐ Thứ làm nó an toàn là rào THỨ HAI, và nó nằm ở nền tảng:
       `pipeline.CHUOI` khai `EDIT_PLAN` với `tai_nguyen="llm_remote",
       tai_nguyen_suat=1`, nên `jobs._con_cho_tai_nguyen` +
       `UNIQUE(resource, slot)` của `ExecutionLease` cho **đúng một** job
       `llm_remote` chạy một lúc trên toàn nền tảng.

           1 job (nền tảng)  ×  2 luồng (trong job)  =  2 request.  Hết.

    ⛔ Hạ `tai_nguyen_suat` lên 2 mà không hạ `LO_DOC_CANH` là mở lại đúng lỗ đó.
    """
    from apps.auto_scan_video import pipeline

    g = pipeline.THEO_TEN["edit_plan"]
    assert g.tai_nguyen == "llm_remote", g.tai_nguyen
    assert g.tai_nguyen_suat == 1, g.tai_nguyen_suat
    assert g.tai_nguyen_suat * gdbbt.LO_DOC_CANH <= 2, (
        "1 suat x so luong da VUOT tran 2 request/model cua may B")
    # `content_process` dùng CHUNG tên tài nguyên ⇒ nó cũng không chồng được.
    assert pipeline.THEO_TEN["content_process"].tai_nguyen == "llm_remote"


def test_pool_khai_dung_LO_DOC_CANH_lam_max_workers():
    """Bánh cóc tĩnh: `max_workers` phải LÀ hằng số trần, không một số gõ tay."""
    cay = ast.parse(inspect.getsource(gdbbt._doc_cac_canh))
    thay = False
    for nut in ast.walk(cay):
        if (isinstance(nut, ast.Call)
                and getattr(nut.func, "id", "") == "ThreadPoolExecutor"):
            kw = {k.arg: k.value for k in nut.keywords}
            assert "max_workers" in kw, "pool khong khai max_workers"
            assert isinstance(kw["max_workers"], ast.Name), (
                "max_workers phai la ten hang so, khong phai so go tay")
            assert kw["max_workers"].id == "LO_DOC_CANH"
            thay = True
    assert thay, "khong con pool nao — edit_plan da quay ve tuan tu?"


@pytest.mark.parametrize("so_canh", [1, 2, 4, 5])
def test_khong_bao_gio_vuot_2_request_dong_thoi(db, kho_tam, monkeypatch, so_canh):
    """PHÉP ĐO: đỉnh đồng thời thật sự, đếm trong chính lời gọi."""
    run, ci, theo, ctx = _chuan_bi(db, monkeypatch, so_canh)
    hieu, hong = gdbbt._doc_cac_canh(db, None, run, ci, {}, ctx)
    assert theo.tong == so_canh, (theo.tong, so_canh)
    assert not hong, hong
    assert theo.dinh == min(gdbbt.LO_DOC_CANH, so_canh), theo.dinh
    assert theo.dinh <= 2, f"VUOT TRAN MAY B: {theo.dinh} request dong thoi"
    assert len(hieu) == so_canh


# ══════════════════════════════════════════════════════════════════════════════
#  §2  PHIÊN — mỗi luồng một `Session`, và một `run` đọc lại trong phiên đó
# ══════════════════════════════════════════════════════════════════════════════

def test_moi_luong_mot_phien_rieng_va_run_doc_lai(db, kho_tam, monkeypatch):
    """⛔ Vật cản số 2 của `L_TOC_DO_GPU.md` §5.2, đo bằng `id()` của phiên."""
    run, ci, theo, ctx = _chuan_bi(db, monkeypatch, 4)
    gdbbt._doc_cac_canh(db, None, run, ci, {}, ctx)
    assert id(db) not in theo.phien, (
        "mot luong da dung PHIEN CHINH — Session khong an toan da luong")
    assert len(set(theo.phien)) == 4, (
        f"4 loi goi chi co {len(set(theo.phien))} phien — co phien bi dung chung")
    assert all(theo.run_khac_phien), (
        "mot luong dung lai doi tuong `run` cua phien chinh")


def test_ctx_trong_lo_KHONG_xoa_mo_ho_cua_provider(db, kho_tam, monkeypatch):
    """🔴 `provider_state` là MỘT ô cho HAI lời gọi đang bay — xem `_CtxLo`."""
    run, ci, theo, ctx = _chuan_bi(db, monkeypatch, 4)

    def _goi_tu_choi(db2, run2, thao_tac, messages, *, stage, item_key,
                     ctx=None, **_k):
        if ctx is not None:
            ctx.provider_rejected("gia")
            ctx.progress(50, "khong duoc bao tu trong lo")
        return _tra_loi(item_key)

    monkeypatch.setattr(gdbbt.ai, "goi_tinh_tien", _goi_tu_choi)
    gdbbt._doc_cac_canh(db, None, run, ci, {}, ctx)
    assert ctx.da_tu_choi == 0, (
        "mot loi goi trong lo da xoa mo ho cua CA job — xem docstring _CtxLo")
    # Tiến độ của PHA 1 vẫn được báo (tuần tự), chỉ trong lô thì không.
    assert ctx.tien_do >= 1


# ══════════════════════════════════════════════════════════════════════════════
#  §3  THỨ TỰ — `lat_cat` và kết quả đi theo thứ tự CẢNH
# ══════════════════════════════════════════════════════════════════════════════

def test_ket_qua_theo_dung_thu_tu_canh_du_luong_nao_ve_truoc(db, kho_tam,
                                                             monkeypatch):
    run, ci, theo, ctx = _chuan_bi(db, monkeypatch, 4)

    def _goi_lech_nhip(db2, run2, thao_tac, messages, *, stage, item_key,
                       ctx=None, **_k):
        # Cảnh chẵn về đích SAU cảnh lẻ của cùng lô: nếu thu hoạch theo thứ tự
        # về đích thì thứ tự cảnh sẽ đảo.
        time.sleep(0.05 if "0002" in item_key or "0004" in item_key else 0.25)
        return _tra_loi(item_key)

    monkeypatch.setattr(gdbbt.ai, "goi_tinh_tien", _goi_lech_nhip)
    hieu, hong = gdbbt._doc_cac_canh(db, None, run, ci, {}, ctx)
    assert [h.ma_canh for h in hieu] == [f"canh_{i:04d}" for i in (1, 2, 3, 4)]
    assert not hong


def test_lat_cat_tien_do_khong_bao_gio_ghi_lui(db, kho_tam, monkeypatch):
    """`lc.xong_mot()` chỉ chạy ở PHA 3, tuần tự ⇒ `vi_tri` đơn điệu."""
    from apps.auto_scan_video import lat_cat

    run, ci, theo, ctx = _chuan_bi(db, monkeypatch, 5)
    moc: list[int] = []
    that = lat_cat.LatCat.xong_mot

    def _theo_doi(self):
        that(self)
        moc.append(int(self.da_lam))

    monkeypatch.setattr(lat_cat.LatCat, "xong_mot", _theo_doi)
    gdbbt._doc_cac_canh(db, None, run, ci, {}, ctx)
    # `da_lam` là con trỏ tiếp nối được lưu xuống `outputs` — ghi lùi nghĩa là
    # một lượt tiếp nối sau đó sẽ hỏi (và trả tiền) lại một cảnh đã hỏi.
    assert moc == sorted(moc), f"da_lam ghi lui: {moc}"
    assert moc == list(range(1, 6)), moc


# ══════════════════════════════════════════════════════════════════════════════
#  §4  TỐC ĐỘ — phần mạng mất ~ceil(N/2) lượt, không N lượt
# ══════════════════════════════════════════════════════════════════════════════

def test_phan_mang_mat_ceil_N_tren_2_luot(db, kho_tam, monkeypatch, capsys):
    """PHÉP ĐO có ĐỐI CHỨNG: cùng dữ liệu, `LO_DOC_CANH` = 1 so với 2.

    ⛔ Không so với một con số nhớ được: `LO_DOC_CANH = 1` chính là hành vi
       trước 25/09/2026, nên hai nhánh chỉ khác nhau đúng một hằng số.
    """
    import math

    so_canh = 4
    do: dict[int, float] = {}
    for lo in (1, gdbbt.LO_DOC_CANH):
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(gdbbt, "LO_DOC_CANH", lo)
            run, ci, theo, ctx = _chuan_bi(db, mp, so_canh)
            t0 = time.monotonic()
            hieu, hong = gdbbt._doc_cac_canh(db, None, run, ci, {}, ctx)
            do[lo] = time.monotonic() - t0
            assert len(hieu) == so_canh and not hong
            assert theo.dinh == min(lo, so_canh)

    with capsys.disabled():
        print()
        print(f"PHAN MANG cua {so_canh} canh, moi loi goi {GIAY_MOT_GOI:.2f}s:")
        for lo, giay in sorted(do.items()):
            print(f"  LO_DOC_CANH={lo}  {giay:6.3f}s  "
                  f"({giay / GIAY_MOT_GOI:.2f} x mot loi goi)")
        print(f"  ti so = {do[1] / do[gdbbt.LO_DOC_CANH]:.2f}x")

    luot_tuan_tu = so_canh
    luot_song_song = math.ceil(so_canh / gdbbt.LO_DOC_CANH)
    # Trần rộng 60 %: phép đo này nói về SỐ LƯỢT, không về hiệu năng tuyệt đối —
    # một máy đang tải làm cả hai nhánh chậm như nhau nên tỉ số vẫn đúng.
    assert do[1] > luot_tuan_tu * GIAY_MOT_GOI * 0.9
    assert do[gdbbt.LO_DOC_CANH] < luot_song_song * GIAY_MOT_GOI * 1.6
    assert do[1] / do[gdbbt.LO_DOC_CANH] > 1.5

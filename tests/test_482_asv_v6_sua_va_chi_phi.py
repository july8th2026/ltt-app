"""ASV V6 pha 29 + 30 — hai nang luc CO SAN ma KHONG AI DI TREN DUONG.

🔴 Pha 29: `sua_chua.lap_ke_hoach` nhan BON nguon khiem khuyet, nhung vong sua
   o `jobs.py` chi truyen HAI (`cac_nan`, `qc_ngu_nghia`). `tu_qc_giong` (doc
   sai) va `tu_qc_hinh` (cat sai theo hinh) co ma, co test don vi — va khong
   bao gio chay trong san pham. Bo do mo coi (`test_453`) khong thay, vi no
   khop theo TEN ham, ma ten ay co nguoi goi: chinh `lap_ke_hoach`.
   ⇒ Bai duoi chot TAP nguon da noi va TAP chua noi, kem ly do. Pha 28 noi
     them mot nguon thi phai chuyen no sang tap da noi — bang cach sua bai nay.

🔴 Pha 30: `quan_sat.tom_tat_cho_khach` tinh san bang chi phi cho khach tu V4
   — va khong route nao goi no. Khach tra tien ma khong thay tra cho viec gi.
"""
from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

from apps.auto_scan_video import quan_sat, sua_chua
from tests import test_423_asv_giao_dien as _mt
from tests.test_475_asv_v6_voice_binding import _mau

GOC = Path(__file__).resolve().parents[1]
moi_truong = _mt.moi_truong

#: Nguon CHUA noi vao vong sua, va vi sao. Rong dan theo pha 28 — khong phinh.
CHUA_NOI = {
    "qc_giong": "can ASR luot cuoi tren ban long tieng (pha 28 — speech QC)",
    "qc_hinh": "can VLM kiem canh tren ban ket xuat (pha 28 — visual QC)",
}


def _doi_so_duoc_truyen() -> set[str]:
    ra: set[str] = set()
    for p in (GOC / "apps").rglob("*.py"):
        cay = ast.parse(p.read_text(encoding="utf-8"))
        for n in ast.walk(cay):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "lap_ke_hoach"
                    and isinstance(n.func.value, ast.Name) and n.func.value.id == "sua_chua"):
                ra |= {k.arg for k in n.keywords if k.arg}
    return ra


def test_TAP_nguon_khiem_khuyet_DA_NOI_va_CHUA_NOI_khop_chu_ky():
    chu_ky = set(inspect.signature(sua_chua.lap_ke_hoach).parameters) - {"vong"}
    da_noi = _doi_so_duoc_truyen() - {"vong"}
    assert da_noi, "khong tim thay loi goi `sua_chua.lap_ke_hoach` nao — xanh rong"
    assert da_noi == {"cac_nan", "qc_ngu_nghia"}, da_noi
    assert da_noi | set(CHUA_NOI) == chu_ky
    assert not da_noi & set(CHUA_NOI), "mot nguon vua noi vua ghi CHUA noi"


def test_bang_chi_phi_CO_nguoi_goi_trong_route():
    cay = ast.parse((GOC / "apps/auto_scan_video/routes.py").read_text(encoding="utf-8"))
    goi = [n for n in ast.walk(cay) if isinstance(n, ast.Call)
           and isinstance(n.func, ast.Attribute) and n.func.attr == "tom_tat_cho_khach"]
    assert goi, "tom_tat_cho_khach lai mo coi"


def test_moi_nang_luc_TINH_TIEN_trong_ma_deu_co_NHAN():
    """Nang luc ghi so cai ma khong co nhan se hien "Viec khac" — dung, nhung la
       mot cau tra loi te hon mot nhan that."""
    ma = set()
    for p in (GOC / "apps/auto_scan_video").glob("*.py"):
        ma |= set(re.findall(r'nang_luc="([a-z_]+)"', p.read_text(encoding="utf-8")))
    ma |= {"dich_thuat", "chuyen_loi_thoai", "rut_ngan_cho_vua", "doc_canh",
           "ho_so_noi_dung", "qc_ngu_nghia"}   # `ai.ThaoTac(...)` — ma o doi so dau
    from apps.auto_scan_video import ai, jobs
    ma |= {t.ma for t in vars(ai).values() if isinstance(t, ai.ThaoTac)}
    ma |= {jobs.NANG_LUC_VONG_SUA, jobs.NANG_LUC_CON_LAI}
    thieu = ma - set(quan_sat.NHAN_NANG_LUC)
    assert not thieu, thieu


def _tao_va_quyet_toan(a, csrf, tmp_path):
    import platform_core.db as dbmod
    from apps.auto_scan_video import su_dung as sd
    from apps.auto_scan_video.tables import AsvRun
    from tests.fixtures.asv_media import tiny_mp4

    tep = tiny_mp4(tmp_path / "a.mp4", duration_s=1.0)
    with open(tep, "rb") as f:
        r = a.post("/auto-scan-video/tao", data={
            "csrf_token": csrf, "che_do": "fit_original", "che_do_giong": "USER_SELECTED",
            "giong_id": _mau()}, files={"video": ("a.mp4", f, "video/mp4")})
    run_id = str(r.url).rstrip("/").rsplit("/", 1)[-1]
    truoc = a.get(f"/auto-scan-video/run/{run_id}").text
    db = next(dbmod.get_session())
    run = db.get(AsvRun, run_id)
    sd.ghi(db, run, stage="voice_synthesis", item_key="seg_0",
           su_dung=sd.SuDung(nang_luc="tong_hop_tieng", app_chu="ltt_voice",
                             trang_thai=sd.DA_GIAO, don_vi=sd.KY_TU, so_luong=420.0,
                             credit=2, ma_dispatch="t482:0"))
    sd.ghi(db, run, stage="content_process", item_key="seg_1",
           su_dung=sd.SuDung(nang_luc="ma_la_chua_co_nhan", app_chu="ltt_llm",
                             trang_thai=sd.DA_GIAO, don_vi=sd.LUOT, so_luong=1.0,
                             credit=1, ma_dispatch="t482:1"))
    db.commit()
    giu = int(run.credit_held)
    db.close()
    sau = a.post(f"/auto-scan-video/run/{run_id}/huy", data={"csrf_token": csrf}).text
    return truoc, sau, giu


def _khoi(van):
    m = re.search(r'<details class="asv-nang-cao" id="asv-chi-phi">(.*?)</details>', van, re.S)
    assert m, "trang chi tiet khong co khoi chi phi"
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1)))


def test_HOAN_LAI_chi_hien_SAU_quyet_toan_va_KHOP_cong_thuc(moi_truong, tmp_path):
    _app, a, csrf, _b, _cb = moi_truong
    truoc, sau, giu = _tao_va_quyet_toan(a, csrf, tmp_path)
    assert "Hoàn lại" not in _khoi(truoc) and "khi lần chạy kết thúc" in _khoi(truoc)
    k = _khoi(sau)
    tinh = min(3, giu)
    assert f"Đã giữ khi tạo lần chạy: {giu} credit" in k
    assert f"Đã tính: {tinh} credit" in k
    assert f"Hoàn lại: {giu - tinh} credit" in k


def test_bang_theo_NANG_LUC_khong_lo_ma_noi_bo(moi_truong, tmp_path):
    _app, a, csrf, _b, _cb = moi_truong
    _truoc, sau, _giu = _tao_va_quyet_toan(a, csrf, tmp_path)
    k = _khoi(sau)
    assert "Đọc lời lồng tiếng 420 ký tự 2" in k
    assert "Việc khác 1 lượt 1" in k
    for noi_bo in ("tong_hop_tieng", "ma_la_chua_co_nhan", "ltt_voice", "ltt_llm"):
        assert noi_bo not in k, noi_bo

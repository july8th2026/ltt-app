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
#: ⭐ RONG tu 24/09: `qc_hinh` da duoc noi that o `ecd3b8e0` (23/09). Bai nay
#:    do DUNG 24 gio — thu duoc noi la ma, thu chua doi la HAI BAN KHAI
#:    (tap nay va bang nhan nang luc). Giu dict RONG, dung xoa: no la cho dat
#:    nguon ke tiep, va la cho bat buoc khai LY DO khi chua noi.
#:    ⚠️ 25/09: bang nhan ay (`quan_sat.NHAN_NANG_LUC`) da bi **xoa** cung hoa don
#:       theo nang luc — xem `test_KHONG_con_banh_coc_NHAN_NANG_LUC_gac_mot_man_hinh_da_mat`.
#:       Nen nay chi con MOT ban khai phai bat khop khi noi mot nguon moi: tap nay.
CHUA_NOI: dict[str, str] = {}


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
    assert da_noi == {"cac_nan", "qc_giong", "qc_ngu_nghia", "qc_hinh"}, da_noi
    assert da_noi | set(CHUA_NOI) == chu_ky
    assert not da_noi & set(CHUA_NOI), "mot nguon vua noi vua ghi CHUA noi"


def test_bang_chi_phi_CO_nguoi_goi_trong_route():
    cay = ast.parse((GOC / "apps/auto_scan_video/routes.py").read_text(encoding="utf-8"))
    goi = [n for n in ast.walk(cay) if isinstance(n, ast.Call)
           and isinstance(n.func, ast.Attribute) and n.func.attr == "tom_tat_cho_khach"]
    assert goi, "tom_tat_cho_khach lai mo coi"


def test_KHONG_con_banh_coc_NHAN_NANG_LUC_gac_mot_man_hinh_da_mat():
    """⭐ **`test_moi_nang_luc_TINH_TIEN_trong_ma_deu_co_NHAN` da bi XOA — 25/09.**

    No chot rang moi `nang_luc` ghi so cai deu co mot nhan tieng Viet trong
    `quan_sat.NHAN_NANG_LUC`, de hoa don theo nang luc cua khach ⛔ khong hien
    *"Viec khac"*. Gia phang thay hoa don do bang **mot dong**, nen ⛔ khong con man
    hinh nao in nhan — va ba bang nhan da bi xoa cung luc.

    🔑 **Giu lai phep kiem se la giu mot banh coc gac mot NGHIA VU MA.** No van
       xanh, van bat moi nang luc moi phai dich mot cau, cho mot man hinh ⛔ khong
       con ton tai. Mot bao dong gia lam nguoi ta **TAT** cong — do la ho loi
       `banh-coc-do-CACH-GO-thay-vi-do-tinh-chat`, va cach tranh no la xoa dung luc.

    ⇒ Bai nay thay cho no, va no do **hai chieu**: ba bang phai that su di, va
      ⛔ khong ai duoc lang le dung lai chung o cho khac.
    """
    for ten in ("NHAN_NANG_LUC", "NHAN_NANG_LUC_KHAC", "NHAN_DON_VI"):
        assert not hasattr(quan_sat, ten), (
            f"`quan_sat.{ten}` song lai — neu that su co mot man VAN HANH can ten "
            f"nang luc bang tieng Viet thi dung bang O DO, cho nguoi doc that")

    # ⛔ Va hoa don cua khach van la MOT dong, ⛔ khong len lai thanh mot bang.
    from apps.auto_scan_video import gia

    hd = gia.hoa_don(190.0)
    assert set(hd) == {"giay_nguon", "so_phut", "don_gia", "credit"}, hd


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
    """## ⭐ 25/09/2026 — `_tao_va_quyet_toan` HUY lan chay, va HUY thi KHONG thu

    Gia phang chot *"khong giao duoc thi khong thu"* (`features.CHI_THU_KHI_GIAO_DUOC`
    — so loi `N-21`). Lan chay o day ket bang `/huy`, nen so thu la **0** va toan bo
    hold quay ve, du so cai da ghi 3 credit chi phi noi bo.

    🔑 Bat bien duoc chot khong doi: *"Hoan lai" chi hien SAU quyet toan*, va ba con
       so tren man **khop nhau** (`giu = tinh + hoan`).
    """
    _app, a, csrf, _b, _cb = moi_truong
    truoc, sau, giu = _tao_va_quyet_toan(a, csrf, tmp_path)
    assert "Hoàn lại" not in _khoi(truoc) and "khi lần chạy kết thúc" in _khoi(truoc)
    k = _khoi(sau)
    tinh = 0
    assert f"Đã giữ khi tạo lần chạy: {giu} credit" in k
    assert f"Đã tính: {tinh} credit" in k
    assert f"Hoàn lại: {giu - tinh} credit" in k


def test_khoi_chi_phi_khong_lo_ma_noi_bo(moi_truong, tmp_path):
    """## ⭐ 25/09/2026 — bang theo NANG LUC ra khoi hoa don khach

    Bai cu chot rang khoi chi phi hien *"Doc loi long tieng 420 ky tu 2"* — mot dong
    cua bang `chi_phi_theo_nang_luc`. Gia phang tinh `10 credit x so phut video
    nguon`, nen bang do da roi khoi `quan_sat.tom_tat_cho_khach`: mot bang nam dong
    cho mot con so phang la mot bang **noi doi ve cach tinh**.

    ⚠️ **Nua VANG MAT cua bai nay khong tu do duoc.** *"Do vang mat thi xoa cung
       xanh"* — nen nua **CO MAT** duoc do o tang dich vu, noi ⛔ khong can mot
       template: `tests/test_3900_asv_gia_phang.py::test_HOA_DON_khach_la_MOT_dong_*`
       chot rang `tom_tat_cho_khach()["hoa_don"]` mang dung so phut, don gia, credit
       va cau luat lam tron.

    🔴 **Con lai o day la nua ⛔ KHONG duoc mat di**: khoi chi phi cua khach ⛔ khong
       bao gio duoc lo mot ma noi bo nao — ke ca khi ai do noi mot truong moi vao.

    ⇒ Lan `asv-gui` so huu `asv_chi_tiet.html` va se noi dong hoa don moi vao khoi
      `#asv-chi-phi`. Bai nay ⛔ khong chan viec do; no chan viec lam do kem mot ma
      noi bo.
    """
    _app, a, csrf, _b, _cb = moi_truong
    _truoc, sau, _giu = _tao_va_quyet_toan(a, csrf, tmp_path)
    k = _khoi(sau)
    assert "Đọc lời lồng tiếng 420 ký tự" not in k, (
        "bang theo nang luc con o hoa don khach — xem `gia.py` muc gia phang")
    for noi_bo in ("tong_hop_tieng", "ma_la_chua_co_nhan", "ltt_voice", "ltt_llm",
                   "sao_chep", "cat_ma_hoa_lai", "smart_localize"):
        assert noi_bo not in k, noi_bo

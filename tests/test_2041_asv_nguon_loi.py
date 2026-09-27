"""ASV — MOT duong duy nhat cho loi thoai goc: voice -> voice (Task 21, 26/09).

Tep nay giu **ba bat bien** cua quyet dinh bo `ocr`/`embedded`/`auto`
(`docs/auto_scan_video_final/B1_PLAN_DUONG_ONG_GD1.md` §11):

  1. `nguon_loi` chi con **MOT** che do hop le;
  2. mot **ho so da luu** mang `"ocr"`/`"embedded"`/`"auto"` doc ra `asr` va
     ⛔ **khong nem** — khach mo lai trang khong duoc gap loi vi mot che do ta
     vua bo;
  3. ⛔ **khong module nao** trong `apps/` con goi RapidOCR.

## ⛔ Cai gi da bien khoi tep nay, va vi sao

Ban truoc do (lan `ocr`, 22/09) do DINH TUYEN: `embedded` -> OCR -> ASR, voi mot
runner OCR gia va mot mp4 co phu de nhung mux that. Ca chum do **mat doi tuong**
khi ba duong bi bo — ⛔ khong con gi de dinh tuyen. Ten tung bai da xoa duoc ke
o thong diep commit cua Task 21.

⭐ `doc_srt` thi GIU: `assets.py` goi no de kiem mot tep `.srt` khach tai len co
   doc duoc khong. Do la mot duong SONG, khong dinh nhu cu.
"""
from __future__ import annotations

import ast
import logging
import pathlib

from apps.auto_scan_video import cai_dat, dich_vu_tao, nguon_loi as nl

GOC = pathlib.Path(__file__).resolve().parents[1]
LOGGER_NGUON_LOI = "apps.auto_scan_video.nguon_loi"

SRT = """1
00:00:00,000 --> 00:00:01,200
<i>即使遇到暴风雨</i>

2
00:00:01,300 --> 00:00:02,500
圆拱形状内部的空间
更是相当宽敞
"""


# ══ 1. MOT che do hop le ════════════════════════════════════════════════════

def test_chi_con_MOT_che_do_hop_le():
    """🔑 Bat bien 1. ⛔ Mot bang hai phan tu o day nghia la mot duong nua da
    duoc them lai — va §11 doi nguoi them phai bac duoc ca BA menh de o do."""
    assert nl.CHE_DO_HOP_LE == (nl.ASR,)
    assert nl.CHE_DO_MAC_DINH == nl.ASR


def test_ba_ten_DA_BO_khong_con_la_hang_so_cong_khai():
    """⛔ `AUTO`/`EMBEDDED`/`OCR` khong duoc con song nhu hang so.

    ⭐ Mot hang so con song la mot moi cho ai do go `nguon_loi.OCR` vao mot
       module moi va nghi rang duong do van chay. Ba ten do chi con o **mot**
       cho: `CHE_DO_DA_BO` — mot danh sach ten de DI TRU, ⛔ khong phai mot mien
       gia tri.
    """
    for ten in ("AUTO", "EMBEDDED", "OCR"):
        assert not hasattr(nl, ten), f"`nguon_loi.{ten}` con song"
    assert nl.CHE_DO_DA_BO == frozenset({"auto", "embedded", "ocr"})


def test_KHONG_con_ham_dinh_tuyen_hay_doc_hardsub():
    """⛔ Bo dinh tuyen va bo doc hardsub phai BIEN, khong phai bi vo hieu.

    ⚠️ Mot ham con nam do (du khong ai goi) la mot nang luc mo coi: `test_453`
       se bat no, va ai doc ma se tuong duong do chi dang tat tam.
    """
    for ten in ("dinh_tuyen", "doc_hardsub", "doc_phu_de_nhung", "luong_phu_de",
                "doan_chu_viet", "cho_giao_dien", "KhongCoNguon", "NHAN_CHE_DO",
                "MO_TA_CHE_DO", "PHIEN_BAN_DINH_TUYEN", "FPS_DOC",
                "CHE_DO_HO_SO_CU"):
        assert not hasattr(nl, ten), f"`nguon_loi.{ten}` con song"


# ══ 2. Ho so da luu cua khach ═══════════════════════════════════════════════

def test_HO_SO_CU_mang_che_do_DA_BO_doc_ra_asr_va_KHONG_nem():
    """🔑 Bat bien 2 — cho DUY NHAT phai can than khi bo ba duong.

    🔴 Do 26/09: ca 8 lan chay trong CSDL production deu `nguon_loi='asr'`, nen
       rui ro di tru gan bang khong. Nhung **ho so** (`cai_dat`) thi chua do
       duoc, va mot ho so con mang `"ocr"` phai doc ra `asr` — ⛔ khong nem vao
       mat mot khach chi vua mo lai trang.
    """
    for cu in ("ocr", "embedded", "auto", "OCR", "  Auto  ", "rac", "", None):
        assert nl.chuan_che_do(cu) == nl.ASR, cu


def test_chuan_che_do_ghi_LOG_cho_che_do_DA_BO_chu_khong_cho_gia_tri_la(caplog):
    """⭐ Hai tinh huong KHAC LOAI, ⛔ dung gop thanh mot.

    *"Mot ho so cu mang ten duong da bo"* la mot su that ve **so lieu di tru** —
    dem duoc, va con so do noi cho ta biet con bao nhieu ho so cu. *"Mot gia tri
    vo nghia"* thi khong noi gi ca. Gop chung lai lam ta mat kha nang dem, dung
    ho voi bai hoc `hai-trang-thai-gop-thanh-mot-gia-tri`.
    """
    with caplog.at_level(logging.INFO, logger=LOGGER_NGUON_LOI):
        nl.chuan_che_do("ocr")
    assert len(caplog.records) == 1, caplog.text
    assert "DA BO" in caplog.records[0].getMessage()

    caplog.clear()
    with caplog.at_level(logging.INFO, logger=LOGGER_NGUON_LOI):
        nl.chuan_che_do("khong-phai-mot-che-do")
        nl.chuan_che_do("")
    assert not caplog.records, caplog.text


def test_HO_SO_khong_con_mang_khoa_nguon_loi_khi_GHI():
    """⛔ Mot dieu khien da bo thi ho so ⛔ khong duoc mang khoa cua no nua.

    ⭐ Va ho so cu mang khoa do van DOC duoc: `tu_ho_so` bo qua khoa la thay vi
       nem. Do la luat `KHOA_THUA` doc theo chieu nguoc: khoa nao khong con
       nghia thi khong ghi, va ⛔ khong ai phai di tru mot hang CSDL nao.
    """
    assert "nguon_loi" not in cai_dat.chuan_hoa({"nguon_loi": "ocr"})
    assert "nguon_loi" not in cai_dat.chuan_hoa({"nguon_loi": "asr"})
    assert not hasattr(cai_dat.tu_ho_so({"nguon_loi": "ocr"}), "nguon_loi")


def test_CUA_TAO_nhan_ho_so_cu_mang_nguon_loi_ma_KHONG_bao_loi():
    """🔴 **Bay tuong minh.** `dich_vu_tao.KHOA_NHAN` tu choi khoa la voi cau
    *"Cai dat co truong la"*, va mot ho so doc tu run CU nop lai phai di qua cua
    NGUYEN VEN (chinh vi the `schema`/`voice_id` nam trong danh sach do).

    ⇒ Bo `nguon_loi` khoi `KHOA_NHAN` se bien mot viec DON thanh mot loi cho
      khach. Nen khoa GIU trong danh sach, gia tri bi VUT.
    """
    tho = {"preset": "localize_preserve_picture", "che_do_giong": "AUTO_MATCH",
           "giong_id": "", "ngon_ngu_nguon": "zh", "ngon_ngu_dich": "vi"}
    assert "nguon_loi" in dich_vu_tao.KHOA_NHAN
    for cu in ("ocr", "embedded", "auto", "asr", "doc-tam-linh"):
        ho_so = dich_vu_tao.dung_cai_dat(None, owner_id="u",
                                         tho={**tho, "nguon_loi": cu})
        assert "nguon_loi" not in ho_so, (cu, ho_so)


# ══ 3. ⛔ Khong ai con goi RapidOCR ═════════════════════════════════════════

def _nhap_cua(p: pathlib.Path) -> set[str]:
    """Moi ten module ma tep nay NHAP (`import x` / `from x import y`)."""
    ra: set[str] = set()
    try:
        cay = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return ra
    for n in ast.walk(cay):
        if isinstance(n, ast.Import):
            ra.update(a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom):
            goc = n.module or ""
            ra.add(goc)
            ra.update(f"{goc}.{a.name}" if goc else a.name for a in n.names)
    return ra


def test_KHONG_module_nao_trong_apps_con_goi_RapidOCR():
    """🔑 Bat bien 3 — do bang **duong NHAP** (AST), ⛔ khong bang chuoi.

    ⭐ Do CHUOI se do sai thu: `do_vung.py` nhac ten `RapidOCR` trong mot chu
       thich ghi lai mot phep DO co that (`RapidOCR 73,5-82,1 % vs OpenCV
       74,9-80,7 %` tren cung mot video) — do la bang chung lich su, ⛔ khong
       phai mot nguoi goi. Bai hoc `banh-coc-do-CACH-GO-thay-vi-tinh-chat`:
       phep kiem phai do **tinh chat** (co nap goi khong), ⛔ khong do cach go.

    ⚠️ `ocr_khung`/`phu_de_cung` cung bi hoi o day: mot `import` con sot lai lam
       app hong o **luc nap**, tuc o mot cho khong ai dang xem.
    """
    xau = ("rapidocr", "ocr_khung", "phu_de_cung")
    vi_pham = []
    for p in sorted((GOC / "apps").rglob("*.py")):
        for ten in _nhap_cua(p):
            if any(s in ten for s in xau):
                vi_pham.append(f"{p.relative_to(GOC).as_posix()} — nhap {ten!r}")
    assert not vi_pham, "con nhap duong OCR trong apps/:\n  " + "\n  ".join(vi_pham)


def test_hai_module_cua_duong_OCR_da_bi_XOA():
    for tuong_doi in ("apps/auto_scan_video/phu_de_cung.py",
                      "apps/asv_gpu/do_luong/ocr_khung.py"):
        assert not (GOC / tuong_doi).exists(), f"{tuong_doi} con ton tai"


def test_goi_rapidocr_da_ra_khoi_ban_khai_venv_do_luong():
    """⛔ Mot goi khong con ai dung ma con trong ban khai la mot goi se duoc CAI
    lai o lan `cai_qc_models.ps1` ke tiep — tuc mot phu thuoc song lau hon ly do
    ton tai cua no."""
    van = (GOC / "setup/qc_models_requirements.txt").read_text(encoding="utf-8")
    cai = [d.strip() for d in van.splitlines()
           if d.strip() and not d.strip().startswith("#")]
    assert not [d for d in cai if d.startswith(("rapidocr", "onnxruntime"))], cai


def test_be_mat_cong_khai_cua_asv_gpu_khong_con_khai_ocr_khung():
    """⭐ Nghia vu an o mot **so dang ky dung chung**: `BE_MAT_CONG_KHAI` khai
    canh lien-app, va `tools/lint_app_contract.py` doi soat no. Mot ban khai tro
    tay khong (module da xoa) la mot canh duoc phep di ma khong co duong."""
    from apps import asv_gpu

    assert all(ten != "ocr_khung" for _goi, ten in asv_gpu.BE_MAT_CONG_KHAI)


def test_hang_ffmpeg_TRAN_cua_hai_tep_da_bien_khoi_moc():
    """🔑 Nghia vu an thu hai: `tools/check_ffmpeg_tran.moc` dem cho goi
    `ffmpeg`/`ffprobe` TRAN theo tep. Hai cho cua `nguon_loi.py` (ffprobe liet
    luong phu de, ffmpeg rut SRT) di theo duong `embedded` ⇒ **hang** cua tep
    phai BIEN khoi moc, ⛔ khong phai tut xuong 0 (mot hang `0` la mot tep duoc
    theo doi, va tep nay khong con goi tien trinh con nao)."""
    van = (GOC / "apps/auto_scan_video/nguon_loi.py").read_text(encoding="utf-8")
    assert "subprocess" not in van

    moc = (GOC / "tools/check_ffmpeg_tran.moc").read_text(encoding="utf-8")
    assert "apps/auto_scan_video/nguon_loi.py" not in moc
    assert "ocr_khung.py" not in moc


# ══ 4. `doc_srt` va nhan — duong con SONG ═══════════════════════════════════

def test_doc_srt_bo_the_va_ghep_dong():
    """⭐ `assets.py` goi ham nay (bo doc SRT DUY NHAT cua app) de kiem mot tep
    phu de khach tai len. ⛔ Khong lien quan gi toi duong OCR da bo."""
    seg = nl.doc_srt(SRT)
    assert [s["text"] for s in seg] == ["即使遇到暴风雨",
                                        "圆拱形状内部的空间 更是相当宽敞"]
    assert seg[0]["start"] == 0.0 and seg[0]["end"] == 1.2
    assert seg[1]["confidence"] == 1.0


def test_NHAN_NGUON_THAT_chi_con_MOT_hang():
    """⛔ Mot ma ngoai bang (vd. `ocr` cua mot lan chay 22-26/09) duoc `quan_sat`
    in NGUYEN MA — ⛔ khong ai bia mot nhan tieng Viet cho mot duong khong con
    ton tai, vi lam vay la noi voi khach rang duong do van chay duoc."""
    assert set(nl.NHAN_NGUON_THAT) == {nl.ASR}

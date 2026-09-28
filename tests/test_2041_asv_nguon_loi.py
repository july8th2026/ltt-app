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


def test_KHONG_module_nao_trong_apps_dung_OCR_de_LAY_LOI_THOAI():
    """🔑 Bất biến 3 — đo bằng **đường NHẬP** (AST), ⛔ không bằng chuỗi.

    🔴 **THU HẸP 28/09 (B10-4) — chủ dự án chốt, và lý do là một phép đo.**

       Bản cũ cấm **mọi** đường nhập `rapidocr` trong `apps/`. Lệnh cấm ấy
       **rộng hơn lý do sinh ra nó**: quyết định 22/09 bỏ `nguon_loi` =
       `ocr`/`embedded`/`auto`, tức bỏ việc dùng OCR để **LẤY LỜI THOẠI** thay
       cho ASR. Việc xoá hai module và gỡ gói là **hệ quả dọn dẹp** của quyết
       định ấy, ⛔ không phải một phán quyết rằng OCR vô dụng cho mọi việc.

    ⚠️ Và chính `do_vung.py` giữ một phép đo nói **ngược lại** cho việc dò dải
       (chú thích `BU_MOI_DAU`, cùng video `H=1280`):

           RapidOCR 73,5–82,1 %   ·   OpenCV 74,9–80,7 %
           ⇒ OpenCV hụt ~1,4 % mỗi đầu ≈ 18 px ⇒ đỉnh và chân chữ Hán LỘ ra

       Ta đã phải thêm hằng số bù `BU_MOI_DAU = 0.015` để vá đúng chỗ hụt đó.

    ⭐ Đo lại 28/09 trên phim nghiệm thu, qua chính `_dai_chu_nhieu_tang`:

           tầng lùi   cao 15,5 %  ·  rộng 100 %
           tầng OCR   cao 10,7 %  ·  rộng 80,8 %     ⇒ diện tích **/1,78**

    ⇒ Bất biến nay nói đúng điều quyết định gốc nói: **⛔ không dùng OCR để lấy
      LỜI THOẠI.** Dò **HỘP** (det-only) thì được — xem bài kế tiếp, nó chốt
      rằng đường mới ⛔ không hề đọc trường văn bản.
    """
    xau = ("ocr_khung", "phu_de_cung")
    vi_pham = []
    for p in sorted((GOC / "apps").rglob("*.py")):
        for ten in _nhap_cua(p):
            if any(s in ten for s in xau):
                vi_pham.append(f"{p.relative_to(GOC).as_posix()} — nhap {ten!r}")
    assert not vi_pham, ("con nhap duong OCR-lay-loi trong apps/:\n  "
                         + "\n  ".join(vi_pham))


def test_CHI_MOT_module_duoc_nhap_rapidocr_va_van_ban_KHONG_ro_ra_ngoai():
    """🔑 Bất biến 3b — cập nhật B13 D1 (28/09): chủ dự án ĐẢO LẠI lệnh 27/09.

    ⛔ Thu hẹp một lệnh cấm mà ⛔ không đặt lại hàng rào ở chỗ mới thì là **gỡ**
       lệnh cấm — nhưng CHÍNH SÁCH đã đổi, nên hàng rào cũng phải đổi CHỖ:

       1. **Đúng MỘT module** được nhập `rapidocr`. Một lệnh cấm đổi thành
          "được phép ở khắp nơi" là ⛔ không còn lệnh cấm. (KHÔNG đổi.)
       2. **Cũ (27/09 → 28/09 sáng)**: *"⛔ không sử dụng text để đối chiếu"*
          — module ⛔ không được đọc `muc[1]`.
          **Mới (B13 D1, 28/09 chiều)**: *"nên bật lại OCR đọc text tham
          chiếu"* — module NAY ĐƯỢC ĐỌC `muc[1]`, nhưng văn bản đó CHỈ được
          dùng nội bộ để hỏi *"đổi hay không"* (`_van_ban_giong`), ⛔ không
          bao giờ được đi ra ngoài tệp: `_bao()` — hàm DUY NHẤT dựng dict trả
          về của `do_dai_chu_ocr`/`_theo_doan` — ⛔ không được đọc trường
          `van_ban`.

    ⚠️ Vế 2 đo bằng **AST**, ⛔ không phải chuỗi: đọc thân hàm `_bao` và đòi nó
       ⛔ không chứa bất kỳ `Name`/`Attribute`/khoá dict nào tên `van_ban`.
       Đo CHUỖI ở đây sẽ đo sai thứ: tệp ấy **nói về** văn bản trong nhiều chú
       thích — đó là bằng chứng, ⛔ không phải một phép đọc. Đúng bài học
       `banh-coc-do-CACH-GO-thay-vi-tinh-chat`.
    """
    import ast as _ast

    nhap = [p for p in sorted((GOC / "apps").rglob("*.py"))
            if any("rapidocr" in t for t in _nhap_cua(p))]
    assert [p.name for p in nhap] == ["do_vung_ocr.py"], (
        "dung MOT module duoc nhap rapidocr; thay: %s"
        % [p.relative_to(GOC).as_posix() for p in nhap])

    cay = _ast.parse(nhap[0].read_text(encoding="utf-8"))
    ham_bao = next((n for n in _ast.walk(cay)
                    if isinstance(n, _ast.FunctionDef) and n.name == "_bao"),
                   None)
    assert ham_bao is not None, "khong thay ham `_bao` — hinh dang tep da doi"

    ro_ra: list[int] = []
    for n in _ast.walk(ham_bao):
        if isinstance(n, _ast.Name) and n.id == "van_ban":
            ro_ra.append(n.lineno)
        if isinstance(n, _ast.Attribute) and n.attr == "van_ban":
            ro_ra.append(n.lineno)
        if isinstance(n, _ast.Constant) and n.value == "van_ban":
            # Khoa dict "van_ban" go tay (`_bao` tra ve mot dict-literal).
            ro_ra.append(n.lineno)
    assert not ro_ra, (
        "`_bao()` cham vao `van_ban` o dong %s — van ban OCR dang RO RA khoi "
        "ket qua tra ve, trai voi rang buoc D1 'chu CHI dung noi bo'" % ro_ra)


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

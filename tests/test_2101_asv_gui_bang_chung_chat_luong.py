"""Man mot lan chay: bang chung DA DO phai toi duoc nguoi tra tien.

## 🔴 Bon con so da ton tai, va khong cai nao voi toi duoc man hinh

`so_canh_hong`/`do_phu_bang_chung` (lan `fix-toc-do`), bao cao QC (`qc.tom_tat`),
trang thai tung bo do (`giai_doan_qc_do_luong`) va nguon loi thoai THAT
(`nguon_loi.dinh_tuyen`) deu nam trong `asv_stage.outputs` — doc duoc, boi mot
nguoi mo CSDL ra.

Hau qua do duoc o luot nen v3 (23/09): `smart_localize` giao mot video **khong
cat mot canh nao** vi VLM hong 4/12 luot, va man hinh cua khach noi dung mot
chu — *"Da xong."*

## Va mot cau loi da viet cho khach doc, cung khong toi duoc khach

`rang_giong.vi_sao_chua_rang` noi RO thieu gi tu 23/09. Nhung man mot lan chay
doc `outputs.ma_loi` (`quan_sat.LOI_CO_MA`), khong doc `error` — va `error` la
cho duy nhat cau ay di toi. Nen khach doc mot cau chung chung kem mot nut "Thu
lai buoc nay" **chac chan hong**.
"""
from __future__ import annotations

import json

from tests import test_423_asv_giao_dien as _mt

moi_truong = _mt.moi_truong

#: Hinh dang lay TU chinh `tom_tat` cua tung giai doan. Xem chu thich tung dong.
GIEO = {
    # giai_doan_chep_loi.chay()["tom_tat"]["dinh_tuyen"]
    #
    # ⛔ 26/09 (Task 21): hinh dang nay doi tu `{che_do: auto, nguon_loi: ocr,
    #    ly_do: [khong_co_phu_de_nhung]}` sang `asr` + `ly_do` RONG — mot duong
    #    duy nhat voice->voice. ⭐ Khuon gieo phai doi theo: mot khuon mang hinh
    #    dang cua mot duong DA BO la mot phep kiem doc THU DAI DIEN, va no se
    #    xanh trong khi duong THAT doi hinh dang.
    "transcribe": {"dinh_tuyen": {"che_do": "asr", "nguon_loi": "asr",
                                  "ly_do": []}},
    # giai_doan_ban_bien_tap.chay()["tom_tat"] — bo so cua luot nen v3
    "edit_plan": {"preset": "smart_localize", "so_canh": 6, "so_giu": 6,
                  "so_cat": 0, "so_canh_da_doc": 4, "so_canh_hong": 2,
                  "canh_hong": ["c3", "c5"], "do_phu_bang_chung": 0.6667},
    # qc.tom_tat(bao_cao)
    "qc": {"qc_ky_thuat_dat": False, "qc_so_muc_hong": 2,
           "qc_muc_hong": ["T13", "T18"], "qc_phien_ban": 4},
    # giai_doan_qc_do_luong.chay()["tom_tat"]
    "qc_do_luong": {"so_doan_do": 18,
                    "do_luong": {"giong": "xong", "chat_luong_tieng": "xong",
                                 "dich": "khong_kha_dung"},
                    "so_giong_khong_dat": 1,
                    "canh_bao_tieng": [{"ma": "seg_0004"}]},
}


def _gieo(run_id: str, gieo: dict = None) -> None:
    """Ghi `outputs` vao cac giai doan cua mot lan chay THAT."""
    import platform_core.db as dbmod
    from apps.auto_scan_video import tables as T

    db = next(dbmod.get_session())
    try:
        for ten, out in (gieo or GIEO).items():
            s = (db.query(T.AsvStage)
                 .filter(T.AsvStage.run_id == run_id, T.AsvStage.stage == ten)
                 .one())
            s.status = "succeeded"
            s.outputs = dict(out)
        db.commit()
    finally:
        db.close()


def _tao(a, csrf, tmp_path, **them) -> str:
    from tests.fixtures import asv_media as fx

    fx.require_ffmpeg()
    r = _mt._tao_run_cho(a, csrf, tmp_path, **them)
    assert r.status_code == 200, r.text[:400]
    return str(r.url).rstrip("/").rsplit("/", 1)[-1]


# ══════════════════════════════════════════════════════════════════════════════
#  1. Bon nhom bang chung len duoc man hinh
# ══════════════════════════════════════════════════════════════════════════════

def test_bang_chung_MANG_du_bon_nhom(moi_truong, tmp_path):
    _app, a, csrf, _b, _cb = moi_truong
    run_id = _tao(a, csrf, tmp_path, preset="smart_localize")
    _gieo(run_id)

    html = a.get(f"/auto-scan-video/run/{run_id}").text

    # nguon loi THAT. ⛔ Tu 26/09 chi con MOT gia tri, nen bai nay khong con
    # phan biet duoc "nguon THAT" voi "che do khach khai" — bai duoi lam viec do.
    assert "Nghe tiếng rồi chép lại" in html
    # do phu bang chung: 4/6 = 67%
    assert "4/6" in html and "67%" in html
    # canh doc HONG — con so ma luot nen v3 khong he noi ra
    assert "2 cảnh không đọc được" in html
    # QC: hai muc hong, KEM nhan tieng Viet chu khong chi ma
    assert "T13" in html and "T18" in html
    assert "Chất lượng hình sau mã hoá lại (VMAF)" in html
    # bo do: `khong_kha_dung` phai NOI RA, khong im lang
    assert "chưa đo được trên máy chủ" in html


def test_LAN_CHAY_CU_mang_nguon_ocr_hien_NGUYEN_MA_chu_khong_bia_nhan(
        moi_truong, tmp_path):
    """🔑 Ban ghi cua cac lan chay 22–26/09 THAT SU mang `nguon_loi: "ocr"`, va
    ⛔ ta khong viet lai CSDL. Man hinh phai doc duoc chung.

    ⛔ Nhung `NHAN_NGUON_THAT` chi con MOT hang (`asr`), nen `ocr` hien NGUYEN
       MA. Do la CO Y: bia mot nhan tieng Viet ("Chữ chạy trên hình") cho mot
       duong khong con ton tai la noi voi khach rang duong do van chay duoc.

    ⚠️ Bai nay la doi chung cho phep `dict.get(ma, ma)` o
       `quan_sat.bang_chung_chat_luong` — thieu no thi ai do "don dep" bang cach
       doi thanh `NHAN_NGUON_THAT[ma]` va man hinh cua mot lan chay CU se nem
       `KeyError`.
    """
    _app, a, csrf, _b, _cb = moi_truong
    run_id = _tao(a, csrf, tmp_path, preset="smart_localize")
    _gieo(run_id, {"transcribe": {"dinh_tuyen": {
        "che_do": "auto", "nguon_loi": "ocr",
        "ly_do": ["khong_co_phu_de_nhung"]}}})
    html = a.get(f"/auto-scan-video/run/{run_id}").text
    import re
    assert "Chữ chạy trên hình" not in html
    # ⚠️ Hoi DUNG dong bang chung, khong hoi "chuoi ocr co o dau do trong trang":
    #    mot phep do rong hon cau hoi se xanh vi mot chu `ocr` trong mot lop CSS.
    assert re.search(r'Lời thoại gốc lấy từ:\s*<strong>ocr</strong>', html), \
        'khong thay dong bang chung mang NGUYEN MA `ocr`'


def test_khong_co_giai_doan_nao_xong_thi_KHONG_hien_khoi_rong(moi_truong,
                                                              tmp_path):
    """⛔ Mot khoi "Bang chung chat luong" rong te hon khong co khoi nao: no
    hua mot cau tra loi roi khong tra loi."""
    _app, a, csrf, _b, _cb = moi_truong
    run_id = _tao(a, csrf, tmp_path)
    html = a.get(f"/auto-scan-video/run/{run_id}").text
    assert "Bằng chứng chất lượng" not in html


def test_bo_do_khong_kha_dung_KHONG_bi_doc_thanh_da_dat(moi_truong, tmp_path):
    """🔑 Luat §2 brief chung: model thieu ⇒ `khong_kha_dung`, ⛔ khong lui im
    lang. Mot bang bo mat hang "chua do duoc" doc y het mot bang da do het."""
    from apps.auto_scan_video import quan_sat, tables as T
    import platform_core.db as dbmod

    _app, a, csrf, _b, _cb = moi_truong
    run_id = _tao(a, csrf, tmp_path)
    _gieo(run_id)

    db = next(dbmod.get_session())
    try:
        run = db.get(T.AsvRun, run_id)
        bc = quan_sat.bang_chung_chat_luong(db, run)
    finally:
        db.close()

    theo_ma = {b["ma"]: b for b in bc["do_luong"]["bo_do"]}
    assert theo_ma["dich"]["trang_thai"] == "khong_kha_dung"
    assert theo_ma["dich"]["nhan_trang_thai"] != theo_ma["giong"]["nhan_trang_thai"]


def test_do_phu_bang_chung_la_PHAN_TRAM_doc_duoc(moi_truong, tmp_path):
    """⚠️ `0,6667` tren man hinh cua khach la mot con so khong ai doc duoc
    thanh mot cau."""
    from apps.auto_scan_video import quan_sat, tables as T
    import platform_core.db as dbmod

    _app, a, csrf, _b, _cb = moi_truong
    run_id = _tao(a, csrf, tmp_path)
    _gieo(run_id)

    db = next(dbmod.get_session())
    try:
        bc = quan_sat.bang_chung_chat_luong(db, db.get(T.AsvRun, run_id))
    finally:
        db.close()

    c = bc["canh"]
    assert c["do_phu_pt"] == 67
    # ⭐ Bat bien cua `giai_doan_ban_bien_tap`: da_doc + hong == so_canh.
    assert c["so_canh_da_doc"] + c["so_canh_hong"] == c["so_canh"]


def test_bang_chung_KHONG_lo_thu_cua_van_hanh(moi_truong, tmp_path):
    """⛔ Khong job id, khong ten model, khong duong dan tren dia."""
    _app, a, csrf, _b, _cb = moi_truong
    run_id = _tao(a, csrf, tmp_path)
    _gieo(run_id)
    html = a.get(f"/auto-scan-video/run/{run_id}").text

    khoi = html.split("Bằng chứng chất lượng", 1)[1].split("</section>", 1)[0]
    for cam in ("staging_key", "C:\\", "/tmp", "metricx", "squim", "whisper"):
        assert cam.lower() not in khoi.lower(), cam


# ══════════════════════════════════════════════════════════════════════════════
#  2. Cai dat da dung: cap ngon ngu khach CHON
#
#  ⛔ "nguon loi khach CHON" da ra khoi muc nay 26/09 (Task 21): o do khong
#     con tren trang, va man ho so khong con dong do. Nguon THAT thi van hien
#     — o muc 1, vi no la PROVENANCE chu khong phai mot lua chon.
# ══════════════════════════════════════════════════════════════════════════════

def test_man_lan_chay_noi_ra_cap_ngon_ngu(moi_truong, tmp_path):
    _app, a, csrf, _b, _cb = moi_truong
    run_id = _tao(a, csrf, tmp_path, ngon_ngu_nguon="zh")
    html = a.get(f"/auto-scan-video/run/{run_id}").text
    assert "Tiếng Trung" in html and "Tiếng Việt" in html


def test_nguon_khong_khai_noi_TU_NHAN_RA_chu_khong_bo_trong(moi_truong,
                                                            tmp_path):
    """⭐ `auto` khong phai mot ngon ngu. Mot o trong o cho le ra phai noi cach
    he thong chon nguon la dung kieu hong ma pha 07 da go mot lan."""
    _app, a, csrf, _b, _cb = moi_truong
    run_id = _tao(a, csrf, tmp_path)
    html = a.get(f"/auto-scan-video/run/{run_id}").text
    assert "Tự nhận ra" in html


# ══════════════════════════════════════════════════════════════════════════════
#  3. AUTO_MATCH khong rang duoc giong: cau loi phai TOI KHACH
# ══════════════════════════════════════════════════════════════════════════════

def test_moi_ly_do_CHUA_RANG_deu_co_ma_va_cau_rieng():
    """🔑 Mot ma, mot cau, va hai ly do khac nhau khong duoc dung chung cau:
    khach doc "khong giong nao khop" se lam mot viec khac han khi doc "chua du
    can cu"."""
    from apps.auto_scan_video import rang_giong as rg

    cau = set()
    for ly_do, ma in (("khong giong nao khop", rg.MA_KHONG_KHOP),
                      ("kho chung chi khai gioi — can gioi",
                       rg.MA_KHO_CHUNG_THIEU_GIOI),
                      ("chua co ho so noi dung", rg.MA_THIEU_CAN_CU)):
        kq = rg.KetQua(rg.CHUA_RANG, can_cu={"ly_do": ly_do})
        assert rg.ma_chua_rang(kq) == ma, ly_do
        c = rg.vi_sao_chua_rang(kq)
        assert "tự chọn" in c, c
        cau.add(c)
    assert len(cau) == 3


def test_ma_CHUA_RANG_nam_trong_bang_cau_cua_man_khach():
    """🔴 Khong co dong nay, cau da viet cho khach dung lai o cot `error` — mot
    cot man hinh cua khach CO Y khong doc."""
    from apps.auto_scan_video import quan_sat, rang_giong as rg

    for ma in (rg.MA_KHONG_KHOP, rg.MA_KHO_CHUNG_THIEU_GIOI,
               rg.MA_THIEU_CAN_CU):
        assert ma in quan_sat.LOI_CO_MA, ma
    # ⭐ MOT ban cua cau, khong hai: `quan_sat` muon lai bang cua `rang_giong`.
    for ma, cau in rg.CAU_CHUA_RANG.items():
        assert quan_sat.LOI_CO_MA[ma] == cau


def test_loi_CHUA_RANG_mang_ma_di_theo_ngoai_le():
    """`thi_hanh` do `exc.ma_loi` vao `stage.outputs`. Mot ngoai le khong mang
    ma thi khong bao gio toi duoc man hinh."""
    from apps.auto_scan_video import rang_giong as rg

    e = rg.ChuaRangError("cau cho khach", ma_loi=rg.MA_KHONG_KHOP)
    assert getattr(e, "ma_loi", "") == rg.MA_KHONG_KHOP
    # ⛔ Van la mot `RangGiongError` — `loi.phan_loai` xep no vao NGUOI_DUNG
    #    (that bai CUOI CUNG), khong phai `retry`.
    assert isinstance(e, rg.RangGiongError)


def test_cau_CHUA_RANG_hien_ra_va_KHONG_kem_nut_thu_lai(moi_truong, tmp_path):
    """⛔ "Thu lai buoc nay" o day la mot nut chac chan that bai: AUTO_MATCH
    tren cung ban chep loi cho ra dung cau tra loi do. `LOI_CO_MA` an nut."""
    import platform_core.db as dbmod
    from apps.auto_scan_video import rang_giong as rg, tables as T

    _app, a, csrf, _b, _cb = moi_truong
    run_id = _tao(a, csrf, tmp_path)

    db = next(dbmod.get_session())
    try:
        run = db.get(T.AsvRun, run_id)
        run.status = "error"
        s = (db.query(T.AsvStage)
             .filter(T.AsvStage.run_id == run_id,
                     T.AsvStage.stage == "content_process").one())
        s.status = "failed_terminal"
        s.error = "ChuaRangError: chi tiet cua van hanh"
        s.outputs = {"ma_loi": rg.MA_KHONG_KHOP}
        db.commit()
    finally:
        db.close()

    html = a.get(f"/auto-scan-video/run/{run_id}").text
    assert "Không có giọng nào hợp với nội dung này" in html
    assert "Thử lại bước này" not in html
    # ⛔ Va chu tu do cua van hanh khong lot ra man khach.
    assert "ChuaRangError" not in html

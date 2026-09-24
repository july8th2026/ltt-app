"""Studio: MOI dieu khien phai VE DICH — khong o nao chet.

## Phep thu cua lan `gui`

Mot o dieu khien chi song khi ca **bon** mat xich noi lien:

    giao dien -> form -> `dich_vu_tao.dung_cai_dat` -> `run.settings`

Ba mat xich dau deu co phep kiem rieng tu truoc, va chung van xanh khi mat xich
thu ba dut. Tep nay do dung **hai dau**: o co mat tren trang, va gia tri khach
chon nam trong ho so da luu.

## 🔴 Vi sao tep nay ton tai — mot o CHET da di qua moi phep kiem

`nguon_loi` (lan `ocr`, 22/09) co du: hang so, `chuan_che_do`, `dinh_tuyen` bon
che do, phep duyet o `dung_cai_dat`, khoa trong `KHOA_NHAN`, truong doc o
`cai_dat.tu_ho_so`, va `giai_doan_chep_loi` doc `cai.nguon_loi`. Chi mot dong
khong co: `dung_cai_dat` **khong dat `nguon_loi` vao ho so tra ve**.

Hau qua: khach ep "chu tren hinh", di qua CUA khong mot loi nao, va lan chay
van chay `auto`. Khong phep kiem nao keu — vi moi phep kiem hoi mot mat xich,
va `auto` la mot ket qua hop le, chi khong phai cai khach chon.

⇒ Nen phep kiem o day hoi CAU HOI CUOI: *"cai khach bam co nam trong ho so
  khong"*. Do la cau hoi duy nhat mot o chet khong tra loi duoc.
"""
from __future__ import annotations

import json

import pytest

from tests import test_423_asv_giao_dien as _mt

moi_truong = _mt.moi_truong

#: Ba o lan `gui` noi vao Studio 23/09, + gia tri KHAC mac dinh de doi duoc.
#:
#: ⛔ Gia tri phai khac mac dinh: `cai_dat.chuan_hoa` co y KHONG ghi khoa mang
#:    gia tri mac dinh (luat `KHOA_THUA`), nen mot phep kiem nop `auto` se
#:    khong phan biet duoc "da ve dich" voi "bi vut di".
O_MOI = {
    "ngon_ngu_nguon": ("zh", "ngon_ngu_nguon", "zh"),
    "ngon_ngu_dich": ("en", "ngon_ngu_dich", "en"),
    "nguon_loi": ("ocr", "nguon_loi", "ocr"),
}


def _run_moi_nhat(owner: str):
    import platform_core.db as dbmod
    from apps.auto_scan_video import tables as T

    db = next(dbmod.get_session())
    try:
        return (db.query(T.AsvRun).filter(T.AsvRun.owner_id == owner)
                .order_by(T.AsvRun.created_at.desc()).first())
    finally:
        db.close()


def _id_cua(email: str) -> str:
    import platform_core.db as dbmod
    from platform_core.models import User

    db = next(dbmod.get_session())
    try:
        return db.query(User).filter(User.email == email).one().id
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════
#  1. O co mat tren trang — va mang DUNG `name` may chu doc
# ══════════════════════════════════════════════════════════════════════════════

def test_trang_Studio_co_DU_ba_o_moi(moi_truong, tmp_path):
    """⭐ Doc `name=`, khong doc nhan: nhan doi theo ban dich, `name` la hop dong
    voi `routes.tao`."""
    _app, a, _csrf, _b, _cb = moi_truong
    html = a.get("/auto-scan-video").text

    for ten in ("ngon_ngu_nguon", "ngon_ngu_dich", "nguon_loi"):
        assert f'name="{ten}"' in html, ten


def test_mien_gia_tri_den_TU_module_chu_khong_go_tay(moi_truong, tmp_path):
    """⛔ Hop dong 22/09 song o `ngon_ngu.py`. Mot danh sach go tay trong Jinja
    la ban thu hai, va no lech ngay lan dau ai do them/bot mot ma."""
    from apps.auto_scan_video import ngon_ngu, nguon_loi

    _app, a, _csrf, _b, _cb = moi_truong
    html = a.get("/auto-scan-video").text

    for ma in ngon_ngu.NGUON_HOP_LE + (ngon_ngu.TU_DOAN,):
        assert f'value="{ma}"' in html, ma
    for ma in nguon_loi.CHE_DO_HOP_LE:
        assert f'value="{ma}"' in html, ma
    # ⛔ Va KHONG mot ma dich nao ngoai hop dong (vd `zh` o phia dich).
    assert list(dict(ngon_ngu.cho_giao_dien()["dich"])) == list(
        ngon_ngu.DICH_HOP_LE)


def test_o_giong_mang_LAN_de_giao_dien_loc_duoc(moi_truong, tmp_path):
    """🔑 `rang_giong._rang_khach_chon` tu choi o CUA mot giong lech lan voi
    `ngon_ngu_dich`. Khong co `data-lan`, giao dien khong loc duoc va khach chi
    biet minh chon sai **sau khi bam Gui**."""
    _app, a, _csrf, _b, _cb = moi_truong
    html = a.get("/auto-scan-video").text
    assert 'data-lan="' in html


# ══════════════════════════════════════════════════════════════════════════════
#  2. Gia tri khach chon NAM TRONG ho so da luu — phep kiem cua o chet
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("ten", sorted(O_MOI))
def test_moi_o_moi_DEU_vao_ho_so_lan_chay(moi_truong, tmp_path, ten):
    from tests.fixtures import asv_media as fx

    fx.require_ffmpeg()
    _app, a, csrf, _b, _cb = moi_truong
    chu = _id_cua("asv-a@example.com")

    gia_tri, khoa, mong_doi = O_MOI[ten]
    them = {ten: gia_tri}
    # ⚠️ `ngon_ngu_dich=en` doi mot giong lan `en`; kho giong mau cua bo test
    #    chi co `vi`, nen o do ta chuyen sang AUTO_MATCH (khong kem `giong_id`).
    if ten == "ngon_ngu_dich":
        them.update(che_do_giong="AUTO_MATCH", giong_id="")
    r = _mt._tao_run_cho(a, csrf, tmp_path, ten=f"{ten}.mp4", **them)
    assert r.status_code == 200, r.text[:400]

    run = _run_moi_nhat(chu)
    assert run is not None
    assert run.settings.get(khoa) == mong_doi, run.settings


def test_nguon_loi_ep_OCR_di_toi_GIAI_DOAN_chep_loi(moi_truong, tmp_path):
    """🔴 Bai kiem cua chinh loi 23/09: ho so luu `ocr`, va ban doc toan phan
    ma `giai_doan_chep_loi` dung cho ra `ocr` — khong phai `auto`."""
    from apps.auto_scan_video import cai_dat, nguon_loi
    from tests.fixtures import asv_media as fx

    fx.require_ffmpeg()
    _app, a, csrf, _b, _cb = moi_truong
    chu = _id_cua("asv-a@example.com")

    assert _mt._tao_run_cho(a, csrf, tmp_path, nguon_loi="ocr").status_code == 200
    run = _run_moi_nhat(chu)

    # ⭐ CUNG duong doc ma `giai_doan_chep_loi.chay` dung (`cai.nguon_loi`).
    cai = cai_dat.tu_ho_so(run.settings)
    assert cai.nguon_loi == nguon_loi.OCR


def test_nguon_loi_MAC_DINH_khong_ghi_khoa_nao(moi_truong, tmp_path):
    """⛔ Luat `KHOA_THUA`: khong ep nguon thi ho so giu nguyen hinh dang cu —
    tuc van tay cua nhung lan chay khong dung tinh nang nay KHONG doi."""
    from tests.fixtures import asv_media as fx

    fx.require_ffmpeg()
    _app, a, csrf, _b, _cb = moi_truong
    chu = _id_cua("asv-a@example.com")

    assert _mt._tao_run_cho(a, csrf, tmp_path).status_code == 200
    assert "nguon_loi" not in (_run_moi_nhat(chu).settings or {})


def test_nguon_loi_bia_ra_bi_tu_choi_O_CUA(moi_truong, tmp_path):
    """Truoc credit, khong phai o phut thu muoi."""
    from tests.fixtures import asv_media as fx

    fx.require_ffmpeg()
    _app, a, csrf, _b, _cb = moi_truong
    chu = _id_cua("asv-a@example.com")

    r = _mt._tao_run_cho(a, csrf, tmp_path, nguon_loi="doc-tam-linh")
    assert r.status_code == 400
    assert _run_moi_nhat(chu) is None


# ══════════════════════════════════════════════════════════════════════════════
#  3. Nap lai cai dat cua lan chay cu — ba o moi phai theo
# ══════════════════════════════════════════════════════════════════════════════

def test_chay_lai_voi_cai_dat_nay_NAP_ca_ba_o_moi(moi_truong, tmp_path):
    """🔑 `_ngu_canh_studio` dat mac dinh cho tung o. Quen mot o thi nut "Chay
    lai voi cai dat nay" lang le tra khach ve mac dinh cua o do — va ho khong
    co cach nao biet, vi cac o khac thi dung."""
    from tests.fixtures import asv_media as fx

    fx.require_ffmpeg()
    _app, a, csrf, _b, _cb = moi_truong

    r = _mt._tao_run_cho(a, csrf, tmp_path, ngon_ngu_nguon="zh",
                         nguon_loi="ocr", preset="smart_localize")
    assert r.status_code == 200, r.text[:400]
    run_id = str(r.url).rstrip("/").rsplit("/", 1)[-1]

    html = a.get(f"/auto-scan-video?run_id={run_id}").text
    # ⚠️ Khoang trang giua `value=` va `selected` do Jinja xuong dong, nen phep
    #    so chuoi tho o day se do vi mot dau xuong dong — mot phep do tra loi
    #    ve DINH DANG trong khi cau hoi la ve GIA TRI.
    import re
    assert re.search(r'value="zh"\s+selected', html), "nguon zh khong duoc nap lai"
    assert re.search(r'value="ocr"\s+checked', html), "nguon_loi ocr khong duoc nap lai"


# ══════════════════════════════════════════════════════════════════════════════
#  4. Tran cung cua hop dong app — o moi khong duoc mua bang do phinh
# ══════════════════════════════════════════════════════════════════════════════

def test_routes_va_module_JS_van_trong_tran():
    """⛔ `test_423` chot 900 dong / 30 handler cho `routes.py`, `test_468` chot
    320 dong moi module JS. Ba o moi phai vua trong do."""
    import pathlib

    goc = pathlib.Path(__file__).resolve().parent.parent
    ma = (goc / "apps/auto_scan_video/routes.py").read_text(encoding="utf-8")
    assert len(ma.splitlines()) < 900

    for tep in (goc / "server/static/asv").glob("*.js"):
        assert len(tep.read_text(encoding="utf-8").splitlines()) <= 320, tep.name


def test_CAU_hien_cho_khach_KHONG_nam_trong_js():
    """⛔ `_()` chi voi toi duoc tep Jinja. Mot CAU tieng Viet go thang vao
    `.js` la mot cau khong bao gio dich duoc.

    ⚠️ Phep do o day hoi *"co CAU tieng Viet khong"*, khong hoi *"co ky tu
       tieng Viet khong"* — va khac biet do la co that: `giong.js:khongDau()`
       mang `replace(/đ/g, "d")`, mot ky tu tieng Viet dung lam **du lieu cua
       thuat toan**, khong phai mot cau cho ai doc. Ban dau toi viet phep do
       theo ky tu va no danh hong dung dong ay — mot phep do lech ve phia HANH
       DONG, tuc phai bo chu khong phai mien tru.

    ⇒ Dau hieu cua mot CAU: co dau tieng Viet **va** co khoang trang trong
      cung mot chuoi nguyen ven.
    """
    import pathlib
    import re

    goc = pathlib.Path(__file__).resolve().parent.parent
    dau_viet = re.compile(r"[ăâđêôơưĂÂĐÊÔƠƯáàảãạéèẻẽẹíìỉĩịóòỏõọúùủũụ]")
    chuoi = re.compile(r'"([^"\n]*)"|\'([^\'\n]*)\'')

    for tep in (goc / "server/static/asv").glob("*.js"):
        ma = tep.read_text(encoding="utf-8")
        # Bo chu thich: chu thich viet cho nguoi doc MA, khong hien cho khach.
        than = re.sub(r"/\*.*?\*/", "", ma, flags=re.S)
        than = re.sub(r"^\s*//.*$", "", than, flags=re.M)
        for m in chuoi.finditer(than):
            s = m.group(1) or m.group(2) or ""
            assert not (dau_viet.search(s) and " " in s), f"{tep.name}: {s!r}"


def test_json_chuoi_cua_template_giai_duoc(moi_truong):
    """⭐ Khoi `#asv-chu` la mot tep JSON that. Mot chuoi moi thieu dau phay lam
    `JSON.parse` nem, va khi do MOI chuoi cua man Studio bien thanh rong — mot
    man hinh im lang, khong mot loi nao o may chu."""
    import re

    _app, a, _csrf, _b, _cb = moi_truong
    html = a.get("/auto-scan-video").text
    m = re.search(r'<script type="application/json" id="asv-chu">(.*?)</script>',
                  html, re.S)
    assert m, "khong tim thay khoi #asv-chu"
    chu = json.loads(m.group(1))
    # Hai chuoi cua lan `gui` phai co mat, neu khong o ngon ngu im lang.
    for k in ("nn_con_giong", "nn_het_giong", "giong_het_lan"):
        assert chu.get(k), k

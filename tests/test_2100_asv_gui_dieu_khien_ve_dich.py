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

## ⛔ 26/09 (Task 21): chinh o `nguon_loi` DA BI RUT KHOI STUDIO

San pham chi con MOT duong voice->voice, nen o do khong con gi de chon. Tep nay
GIU nguyen **phep thu bon mat xich** — no van dung cho hai o ngon ngu — va them
mot bai moi o cuoi muc 2: *o da rut thi truong form cu phai bi BO QUA, ⛔ khong
duoc thanh loi 400*. ⭐ Do la mat chieu nguoc cua cung mot cau hoi: mot o chet
la o co ma khong ve dich; mot o DA RUT la o khong co ma van phai khong lam
hong ai.
"""
from __future__ import annotations

import json

import pytest

from tests import test_423_asv_giao_dien as _mt

moi_truong = _mt.moi_truong

#: O lan `gui` noi vao Studio 23/09, + gia tri KHAC mac dinh de doi duoc.
#:
#: ⛔ Gia tri phai khac mac dinh: `cai_dat.chuan_hoa` co y KHONG ghi khoa mang
#:    gia tri mac dinh (luat `KHOA_THUA`), nen mot phep kiem nop gia tri mac dinh
#:    se khong phan biet duoc "da ve dich" voi "bi vut di".
#:
#: ⛔ Hang `nguon_loi` DA RUT 26/09 (Task 21): o do khong con tren trang. Xem
#:    `test_o_nguon_loi_DA_RUT_va_truong_form_cu_bi_BO_QUA` duoi day.
O_MOI = {
    "ngon_ngu_nguon": ("zh", "ngon_ngu_nguon", "zh"),
    "ngon_ngu_dich": ("en", "ngon_ngu_dich", "en"),
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

def test_trang_Studio_co_DU_cac_o_moi(moi_truong, tmp_path):
    """⭐ Doc `name=`, khong doc nhan: nhan doi theo ban dich, `name` la hop dong
    voi `routes.tao`."""
    _app, a, _csrf, _b, _cb = moi_truong
    html = a.get("/auto-scan-video").text

    for ten in sorted(O_MOI):
        assert f'name="{ten}"' in html, ten
    # ⛔ Va o DA RUT phai that su khong con: mot `name="nguon_loi"` con sot lai
    #    la mot o gui gia tri ma khong ai doc — dung hinh dang "o CHET" mA tep
    #    nay ton tai de bat, chi la chieu nguoc.
    assert 'name="nguon_loi"' not in html


def test_mien_gia_tri_den_TU_module_chu_khong_go_tay(moi_truong, tmp_path):
    """⛔ Hop dong 22/09 song o `ngon_ngu.py`. Mot danh sach go tay trong Jinja
    la ban thu hai, va no lech ngay lan dau ai do them/bot mot ma."""
    from apps.auto_scan_video import ngon_ngu

    _app, a, _csrf, _b, _cb = moi_truong
    html = a.get("/auto-scan-video").text

    for ma in ngon_ngu.NGUON_HOP_LE + (ngon_ngu.TU_DOAN,):
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


def test_o_nguon_loi_DA_RUT_va_truong_form_cu_bi_BO_QUA(moi_truong, tmp_path):
    """🔴 **Ba bai gop thanh mot 26/09 (Task 21).** Ba bai cu do ba dieu ve o
    `nguon_loi`: ep `ocr` co ve dich khong; `auto` co bi bo khi ghi khong; mot
    gia tri bia ra co bi tu choi o CUA khong. Ca ba **mat doi tuong** — o do da
    bi rut, va MOT duong duy nhat thi khong con gi de ep, de bo, hay de tu choi.

    ⭐ Cai CON lai la mot bat bien thuc su cua viec RUT mot o: mot khach (hay mot
       bot, hay mot ho so cu nop lai) van co the gui truong form cu. No phai bi
       **BO QUA** — ⛔ khong 400, ⛔ khong ghi vao ho so.

    ⚠️ Do la mat chieu nguoc cua "o chet": o chet = co o, gia tri khong ve dich.
       O da rut = khong co o, va gia tri cu ⛔ khong duoc lam hong ai.
    """
    from tests.fixtures import asv_media as fx

    fx.require_ffmpeg()
    _app, a, csrf, _b, _cb = moi_truong
    chu = _id_cua("asv-a@example.com")

    for cu in ("ocr", "embedded", "auto", "asr", "doc-tam-linh"):
        r = _mt._tao_run_cho(a, csrf, tmp_path, ten=f"{cu}.mp4", nguon_loi=cu)
        assert r.status_code == 200, (cu, r.status_code, r.text[:300])
        assert "nguon_loi" not in (_run_moi_nhat(chu).settings or {}), cu


# ══════════════════════════════════════════════════════════════════════════════
#  3. Nap lai cai dat cua lan chay cu — ba o moi phai theo
# ══════════════════════════════════════════════════════════════════════════════

def test_chay_lai_voi_cai_dat_nay_NAP_ca_cac_o_moi(moi_truong, tmp_path):
    """🔑 `_ngu_canh_studio` dat mac dinh cho tung o. Quen mot o thi nut "Chay
    lai voi cai dat nay" lang le tra khach ve mac dinh cua o do — va ho khong
    co cach nao biet, vi cac o khac thi dung."""
    from tests.fixtures import asv_media as fx

    fx.require_ffmpeg()
    _app, a, csrf, _b, _cb = moi_truong

    r = _mt._tao_run_cho(a, csrf, tmp_path, ngon_ngu_nguon="zh",
                         ngon_ngu_dich="en", che_do_giong="AUTO_MATCH",
                         giong_id="", preset="smart_localize")
    assert r.status_code == 200, r.text[:400]
    run_id = str(r.url).rstrip("/").rsplit("/", 1)[-1]

    html = a.get(f"/auto-scan-video?run_id={run_id}").text
    # ⚠️ Khoang trang giua `value=` va `selected` do Jinja xuong dong, nen phep
    #    so chuoi tho o day se do vi mot dau xuong dong — mot phep do tra loi
    #    ve DINH DANG trong khi cau hoi la ve GIA TRI.
    import re
    assert re.search(r'value="zh"\s+selected', html), "nguon zh khong duoc nap lai"
    assert re.search(r'value="en"\s+selected', html), "dich en khong duoc nap lai"


# ══════════════════════════════════════════════════════════════════════════════
#  4. Tran cung cua hop dong app — o moi khong duoc mua bang do phinh
# ══════════════════════════════════════════════════════════════════════════════

def test_routes_va_module_JS_van_trong_tran():
    """⛔ `test_423` chot 900 dong / 30 handler cho `routes.py`. Tran JS dung
    CHUNG hang so voi `test_468` (`TRAN_DONG`) thay vi chep lai mot con so
    rieng — ban cu cua bai nay khai 320 trong khi `test_468` da nang co CAN
    CU len 360 (lan `v4-be-mat-de-xuat`, xem docstring o do), va khong ai bat
    khop hai noi: dung mot ca hai lan choi tep `tai_len.js` phinh ra do dung
    lai bien dong rieng cua no thay vi tach them mot module (`hai-cho-khai-
    cung-mot-dieu-khong-ai-bat-khop`)."""
    import pathlib

    from tests.test_468_asv_v6_kien_truc_gui import TRAN_DONG

    goc = pathlib.Path(__file__).resolve().parent.parent
    ma = (goc / "apps/auto_scan_video/routes.py").read_text(encoding="utf-8")
    assert len(ma.splitlines()) < 900

    for tep in (goc / "server/static/asv").glob("*.js"):
        assert len(tep.read_text(encoding="utf-8").splitlines()) <= TRAN_DONG, tep.name


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

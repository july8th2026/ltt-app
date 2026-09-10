"""ASV V6 pha 07 — ProductSettings chuan tac, co phien ban va van tay.

`AsvRun.settings` da la ProductSettings tu V4. Pha 07 khong tao ra no; pha 07
lam no **tu khai**, **bam duoc**, va — quan trong nhat — **co MOT cho doc**.

🔴 Pha nay khong phai don dep cho dep. Truoc no, cung mot khoa `timing_mode` co
   HAI mac dinh khac nhau o hai tep:

       giai_doan_thoi_gian.py   ... or "fit_original"
       giai_doan_qc.py          ... or ""

   Tuc mot lan chay thieu khoa se **chay** o `fit_original` trong khi **bang
   chung QC ghi rong**. Khong cho nao bao loi — ca hai deu tim thay mot gia tri
   hop le cua rieng minh. Va `"fit_original"` o dong tren la ban chep CUNG thu
   ba cua `gia.CHE_DO_MAC_DINH`.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from apps.auto_scan_video import cai_dat, gia, hop_dong_v4
from tests import test_423_asv_giao_dien as _mt

GOC = Path(__file__).resolve().parents[1]
APP = GOC / "apps" / "auto_scan_video"


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Ho so TU KHAI, va nhan duoc ho so cu
# ══════════════════════════════════════════════════════════════════════════════

def test_chuan_hoa_dong_dau_phien_ban():
    ra = cai_dat.chuan_hoa({"preset": "smart_localize"})
    assert ra[cai_dat.KHOA_SCHEMA] == cai_dat.SCHEMA
    assert cai_dat.phien_ban_ho_so(ra) == cai_dat.PHIEN_BAN


def test_ho_so_TRUOC_v3_van_doc_duoc_va_KHONG_bi_coi_la_hong():
    """⛔ Co that hang nghin ho so khong co khoa `schema` trong CSDL. Mot lan
    chay lai tren ho so cu phai cho ra dung ket qua cu.

    ⭐ Va `phien_ban_ho_so` tra **0**, khong phai `None`: mot ho so cu la mot ho
       so co that va doc duoc, khong phai mot ho so thieu du lieu. Tra `None` se
       moi nguoi doc viet mot nhanh `is None` cho mot truong hop binh thuong.
    """
    cu = {"timing_mode": "fit_original", "preset": "smart_localize",
          "voice_id": "v9"}
    assert cai_dat.phien_ban_ho_so(cu) == 0
    c = cai_dat.tu_ho_so(cu)
    assert c.preset == "smart_localize"
    assert c.giong_id == "v9"


def test_chuan_hoa_LUY_DANG():
    """⛔ Mot ham chuan hoa khong luy dang thi moi lan luu lai cho mot ho so
    khac — tuc **van tay doi ma cau hinh thi khong**. Dung kieu hong ma
    `sap-xep-list-trong-van-tay-hai-chieu-hong` ghi lai, chi khac chieu."""
    tho = {"preset": "smart_localize", "lop_phu": [{"chu": "a"}], "voice_id": "v1"}
    mot = cai_dat.chuan_hoa(tho)
    assert cai_dat.chuan_hoa(mot) == mot
    assert cai_dat.chuan_hoa(cai_dat.chuan_hoa(mot)) == mot


# ══════════════════════════════════════════════════════════════════════════════
#  §2  MOT cho dat mac dinh — banh coc that su cua pha nay
# ══════════════════════════════════════════════════════════════════════════════

def _doc_settings_trong(p: Path) -> list[int]:
    """Dong nao doc thang mot khoa cua `settings`/`run.settings`. Doc **AST**.

    ⭐ Grep khop cach nguoi ta VIET, AST khop cai nguoi ta LAM. Bai nay tim mot
       hinh dang cu the: `<gi do>.get("<khoa>")` trong do `<gi do>` bat nguon tu
       `settings`.
    """
    van = p.read_bytes().decode("utf-8")
    ra: list[int] = []
    for n in ast.walk(ast.parse(van)):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "get" and n.args):
            continue
        if not (isinstance(n.args[0], ast.Constant)
                and isinstance(n.args[0].value, str)):
            continue
        # Nguon cua `.get` co dinh toi `settings` khong?
        goc = ast.unparse(n.func.value)
        if "settings" in goc:
            ra.append(n.lineno)
    return ra


def test_KHONG_giai_doan_nao_con_TU_doc_mot_khoa_cua_settings():
    """🔑 Menh de DUONG cua ca pha: chi con MOT cho biet hinh dang cua ho so.

    ⛔ Mot phep kiem chi doi *"`cai_dat.py` ton tai"* se xanh ngay ca khi muoi
       cho doc cu con nguyen — tuc pha 07 khong lam gi ca. Bai nay hoi cai
       nguoc lai, va do la cai dat.
    """
    xau = {}
    for p in sorted(APP.glob("giai_doan_*.py")):
        dong = _doc_settings_trong(p)
        if dong:
            xau[p.name] = dong
    assert not xau, (
        f"con giai doan tu doc khoa cua `settings`: {xau}. Moi cho nhu the la "
        "mot ban sao cua mot mac dinh, va hai ban sao la hai ban se lech")


def test_KHONG_ai_con_dung_fit_original_lam_DUONG_LUI():
    """Chot dung hinh dang da hong: `<gi do> or "fit_original"`.

    ⛔ **Ban dau bai nay cam chuoi `"fit_original"` xuat hien o bat cu dau ngoai
       `gia.py`, va no rong hon menh de no muon chot.** No bao dong tren ba cho
       khong phai loi:

         qc.py:169        `che_do_thoi_gian: str = "fit_original"`  <- mac dinh
         thoi_gian.py:112 `che_do: str = "fit_original"`            <- THAM SO
         thoi_gian.py:138 `if che_do not in ("fit_original", ...)`  <- can cuoc

       Mot mac dinh THAM SO cua module mien la hop dong cua chinh no, khong phai
       mot ban doc ho so khach. Va mot phep kiem tu cach thi phai nhac ten che
       do — cam no la cam module do noi ve chinh minh.

    ⭐ Thu that su hong la **duong lui**: `settings.get(...) or "fit_original"`.
       Do la cho mot mac dinh THU HAI ra doi, va la dung cho da lech khoi
       `giai_doan_qc` (`or ""`). Doc AST de hoi dung hinh dang ay.
    """
    xau = {}
    for p in sorted(APP.glob("*.py")):
        if p.name in ("gia.py", "cai_dat.py"):
            continue
        for n in ast.walk(ast.parse(p.read_bytes().decode("utf-8"))):
            if not (isinstance(n, ast.BoolOp) and isinstance(n.op, ast.Or)):
                continue
            for v in n.values:
                if isinstance(v, ast.Constant) and v.value == "fit_original":
                    xau.setdefault(p.name, []).append(n.lineno)
    assert not xau, (
        f"con duong lui `or \"fit_original\"` o {xau} — do la mot mac dinh thu "
        "hai, va ban thu hai chinh la ban da lech")


def test_hai_mac_dinh_tung_LECH_nay_gio_bang_nhau():
    """Doi chung truc tiep cho loi da tim ra: mot ho so **thieu** `timing_mode`
    phai cho CUNG mot cau tra loi o ca duong chay lan duong bang chung."""
    class _Run:
        settings = {"preset": "smart_localize"}

    c = cai_dat.doc(_Run())
    assert c.timing_mode == gia.CHE_DO_MAC_DINH
    assert c.timing_mode, "mac dinh rong lam bang chung QC noi mot dieu khac"


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Van tay
# ══════════════════════════════════════════════════════════════════════════════

def test_van_tay_doi_khi_BAT_KY_dieu_khien_nao_doi():
    goc = {"preset": "smart_localize"}
    v = cai_dat.van_tay(goc)
    for doi in ({"timing_mode": "x"}, {"giong_id": "g2"},
                {"cat": [0.1, 0.9]}, {"vung": [{"loai": "lam_mo"}]},
                {"lop_phu": [{"chu": "a"}]}, {"logo": [{"x": 0.1}]},
                {"tu_dien": {"a": "b"}}, {"ngon_ngu_nguon": "en"}):
        assert cai_dat.van_tay({**goc, **doi}) != v, f"van tay mu voi {doi}"


def test_van_tay_KHONG_doi_khi_chi_doi_THU_TU_KHOA():
    a = {"preset": "smart_localize", "giong_id": "g1"}
    b = {"giong_id": "g1", "preset": "smart_localize"}
    assert cai_dat.van_tay(a) == cai_dat.van_tay(b)


def test_THU_TU_PHAN_TU_trong_list_CO_doi_van_tay():
    """⛔ Day la nua nguy hiem cua `sap-xep-list-trong-van-tay-hai-chieu-hong`:
    **thua** mot `sorted()` con nguy hon thieu, vi no lam hai cau hinh KHAC nhau
    dung chung mot van tay.

    Thu tu cac lop phu la thu tu ve chong len nhau; thu tu cac logo la thu tu
    cac `<input type=file>` di trong multipart. Ca hai deu co nghia.
    """
    a = {"lop_phu": [{"chu": "a"}, {"chu": "b"}]}
    b = {"lop_phu": [{"chu": "b"}, {"chu": "a"}]}
    assert cai_dat.van_tay(a) != cai_dat.van_tay(b)


# ══════════════════════════════════════════════════════════════════════════════
#  §4  Luu THUA, doc TOAN PHAN
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("khoa", cai_dat.KHOA_THUA)
def test_khoa_khong_dung_toi_thi_KHONG_duoc_ghi(khoa):
    """⛔ `cat_dau_cuoi` L4 va cac ghi chu o `routes.tao` noi ro: khong thu hep
    gi thi khong ghi khoa nao. Mot mang rong ghi vao MOI lan chay lam ho so cua
    nhung lan **khong** dung tinh nang do khac di ma khong vi ly do gi — va
    `thi_hanh.van_tay` bam ca `settings`, nen no doi ca van tay giai doan."""
    assert khoa not in cai_dat.chuan_hoa({})
    assert khoa not in cai_dat.chuan_hoa({khoa: []})


@pytest.mark.parametrize("khoa,gt", [
    ("cat", [0.1, 0.9]),
    ("vung", [{"loai": "lam_mo"}]),
    ("lop_phu", [{"chu": "a"}]),
    ("logo", [{"x": 0.1}]),
])
def test_khoa_CO_dung_thi_phai_duoc_ghi(khoa, gt):
    """Nua DUONG. Thieu no thi mot ban `chuan_hoa` vut sach bon khoa cung xanh."""
    assert cai_dat.chuan_hoa({khoa: gt})[khoa] == gt


def test_doc_thi_TOAN_PHAN_du_ho_so_thua():
    c = cai_dat.tu_ho_so({})
    assert c.preset == hop_dong_v4.PRESET_MAC_DINH
    assert c.timing_mode == gia.CHE_DO_MAC_DINH
    assert c.cat is None and c.vung == () and c.lop_phu == () and c.logo == ()
    assert c.co_sua_diem_anh is False


def test_co_sua_diem_anh_hoi_MOT_lan_thay_vi_bon():
    for k in ("vung", "lop_phu", "logo"):
        assert cai_dat.tu_ho_so({k: [{"x": 1}]}).co_sua_diem_anh is True
    assert cai_dat.tu_ho_so({"cat": [0.1, 0.9]}).co_sua_diem_anh is False, (
        "cat dau/cuoi KHONG doi diem anh — no chi chon mot cua so thoi gian")


# ══════════════════════════════════════════════════════════════════════════════
#  §5  `giong_id` va `voice_id` — mot cau hoi, mot cho tra loi
# ══════════════════════════════════════════════════════════════════════════════

def test_hai_khoa_giong_hop_nhat_va_giong_id_THANG():
    """🔴 Hai khoa nay da song song mot thoi gian, va hau qua duoc ghi o
    `rang_giong.tu_thiet_lap`: mot lan chay co the **viet loi thoai CHO mot
    giong roi doc len bang mot giong khac**, khong cho nao bao loi."""
    assert cai_dat.tu_ho_so({"voice_id": "cu"}).giong_id == "cu"
    assert cai_dat.tu_ho_so({"giong_id": "moi", "voice_id": "cu"}).giong_id == "moi"
    ra = cai_dat.chuan_hoa({"giong_id": "moi", "voice_id": "cu"})
    assert ra["giong_id"] == ra[cai_dat.KHOA_BI_DANH_GIONG] == "moi", (
        "sau chuan hoa hai khoa phai noi CUNG mot dieu — de lech la de nguyen "
        "cai loi vua ke tren")


def test_routes_ghi_ho_so_QUA_chuan_hoa_chu_khong_ghi_thang():
    """Cho GHI cung phai co mot cua. Mot duong ghi thang `dict(...)` xuong
    `settings=` la mot ho so khong khai phien ban — va no se im lang."""
    van = (APP / "routes.py").read_bytes().decode("utf-8")
    assert "settings=dict(cai_dat)" not in van, (
        "routes van ghi thang dict tho xuong `settings=`")
    assert van.count("cai_dat_mod.chuan_hoa(") >= 3, (
        "khong du ba duong ghi (ben vung · multipart · gan logo) di qua "
        "`chuan_hoa`")
def test_template_KHONG_tu_doc_run_settings():
    """Man "Cai dat da dung" la NGUOI DOC THU BA cua ho so, va truoc pha 07 no
    doc **khong kem mac dinh**:

        {% set c = run.settings.get("timing_mode") %}
        {% for ma, ten, _ in che_do %}{% if ma == c %}...{% endif %}{% endfor %}

    Mot ho so thieu khoa thi vong lap khong khop gi, va khach doc mot dong
    **trong** o cho le ra phai noi cach khop thoi gian. Khong loi nao o dau ca.

    ⭐ Day la ve con lai cua cau ma pha 07 dat ra — *"preview va render doc cung
       config"*. Mot ban doc thu ba tu dat mac dinh la mot ban doc se lech, va
       lan nay no lech ve phia KHACH NHIN THAY.
    """
    # ⚠️ Bo khoi chu thich Jinja `{# ... #}` TRUOC khi quet. Ban dau bai nay
    #    quet ca tep va bao dong tren chinh doan chu thich GIAI THICH ban va —
    #    lan thu tu trong mot phien toi mac dung loi do
    #    (`bo-do-quet-van-ban-trung-phat-viec-giai-thich`). Do MA, dung do van
    #    xuoi noi ve ma.
    van = (APP / "templates" / "asv_chi_tiet.html").read_bytes().decode("utf-8")
    ma = re.sub(r"\{#.*?#\}", "", van, flags=re.S)
    assert "run.settings.get(" not in ma, (
        "template van tu doc `run.settings` — phai doc qua `cai` "
        "(`cai_dat.doc(run)`), noi duy nhat biet mac dinh")
    assert "cai.preset" in van and "cai.timing_mode" in van, (
        "template khong doc qua ban doc toan phan")


def test_trang_chi_tiet_HIEN_phien_ban_va_van_tay_ho_so():
    """⛔ Doi chung cho `test_453`: mot ham cong khai duoc GOI nhung gia tri cua
    no khong bao gio toi man hinh thi van la mot nang luc khong ai di tren
    duong — chi la duong dai them mot doan.
    """
    van = (APP / "templates" / "asv_chi_tiet.html").read_bytes().decode("utf-8")
    assert "ho_so_phien_ban" in van and "ho_so_van_tay" in van, (
        "hai gia tri vao context ma template khong hien — duong van cut")
# ══════════════════════════════════════════════════════════════════════════════
#  §6  Hai gia tri moi phai RA MAN HINH, khong chi vao context
# ══════════════════════════════════════════════════════════════════════════════

moi_truong = _mt.moi_truong


@pytest.fixture()
def mot_lan_chay(moi_truong):
    """Mot lan chay cua nguoi A, ho so co du dieu khien."""
    import platform_core.db as dbmod
    from platform_core.models import User

    from apps.auto_scan_video import tables as T

    app, a, csrf_a, b, csrf_b = moi_truong
    db = next(dbmod.get_session())
    u = db.query(User).filter(User.email == "asv-a@example.com").first()
    ho_so = cai_dat.chuan_hoa({
        "preset": hop_dong_v4.PRESET_GIU_HINH,
        "timing_mode": gia.CHE_DO_MAC_DINH,
        "giong_id": "giong-x",
        "vung": [{"loai": "lam_mo", "x0": 0.1, "y0": 0.1, "x1": 0.5, "y1": 0.5}]})
    db.add(T.AsvRun(id="r7-cai-dat", owner_id=u.id, status="done",
                    settings=ho_so))
    db.commit()
    db.close()
    return a, ho_so


def test_trang_chi_tiet_IN_RA_phien_ban_va_van_tay(mot_lan_chay):
    """Menh de DUONG: hai gia tri that su xuat hien trong HTML tra ve.

    ⛔ Phep kiem doc van ban template khong du — Jinja bien mot ten sai thanh
       chuoi rong ma khong keu mot tieng nao. Chi mot lan render THAT moi phan
       biet duoc "da noi day" voi "da noi day va no im".
    """
    a, ho_so = mot_lan_chay
    r = a.get("/auto-scan-video/run/r7-cai-dat")
    assert r.status_code == 200
    van = r.text
    assert f"v{cai_dat.PHIEN_BAN}" in van, "khong thay phien ban ho so tren trang"
    assert cai_dat.van_tay(ho_so) in van, (
        "khong thay van tay ho so tren trang — hai lan chay trong nhu nhau van "
        "khong phan biet duoc")


def test_trang_chi_tiet_HIEN_dung_che_do_du_ho_so_THIEU_khoa(moi_truong):
    """🔴 Loi that ma pha 07 sua, do o dung cho khach nhin.

    Truoc pha nay template goi `run.settings.get("timing_mode")` **khong kem mac
    dinh**, roi so no voi bang nhan. Mot ho so thieu khoa thi khong nhan nao
    khop, va dong "Cach khop thoi gian" hien ra **trong**.
    """
    import platform_core.db as dbmod
    from platform_core.models import User

    from apps.auto_scan_video import tables as T

    app, a, csrf_a, b, csrf_b = moi_truong
    db = next(dbmod.get_session())
    u = db.query(User).filter(User.email == "asv-a@example.com").first()
    # Ho so kieu CU: khong `schema`, va **khong** co `timing_mode`.
    db.add(T.AsvRun(id="r7-thieu", owner_id=u.id, status="done",
                    settings={"preset": hop_dong_v4.PRESET_GIU_HINH}))
    db.commit()
    db.close()

    r = a.get("/auto-scan-video/run/r7-thieu")
    assert r.status_code == 200
    nhan = dict((ma, ten) for ma, ten, _m in gia.CHE_DO_THOI_GIAN)
    assert nhan[gia.CHE_DO_MAC_DINH] in r.text, (
        "ho so thieu `timing_mode` van phai hien che do THAT SU duoc dung, "
        "khong duoc de mot dong trong")
    assert "v0" in r.text, "ho so truoc v3 phai duoc khai la v0, khong phai v3"

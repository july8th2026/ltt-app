"""Pha V5 — RANH CHAN hoi quy truoc khi xay lai giao dien.

`docs/auto_scan_video_v5/` muc 14 doi: **viet phep kiem hoi quy TRUOC khi
refactor GUI**, va GUI moi chi duoc hoa khi moi duong hien tai van chay.

## Vi sao tep nay khong lap lai `test_423`

`test_423` chot **nhung handler ton tai luc no duoc viet**. Do la mot chot theo
DANH SACH, va V5 them sau handler moi — moi cai la mot co hoi de bo quen mot
trong bon tai san o `CURRENT_UI_AUDIT.md` §3.

⇒ Tep nay chot theo **QUY TAC**, khong theo danh sach. Moi phep kiem duoi day
  duyet TOAN BO `routes.py` bang AST hoac bang bang dinh tuyen that, nen mot
  handler viet ngay mai **tu dong** nam trong pham vi. Do la khac biet duy nhat
  dang co giua tep nay va tep kia.

⭐ Va do la ly do chung doc AST chu khong goi HTTP: mot phep kiem HTTP chi tham
   duoc nhung URL no biet ten. Mot phep kiem AST tham duoc ca nhung URL chua ai
   viet.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path


# Dung lai moi truong HTTP that cua `test_423` — hai nguoi dung, hai phien,
# CSDL that. Viet lai mot ban thu hai la de hai ban troi khoi nhau.
# ⚠️ Nhap MODULE roi lay thuoc tinh, khong `from ... import moi_truong`.
#    Dang `import` truc tiep lam `ruff` bao F811 o **moi** ham nhan fixture nay
#    (tham so cung ten "dinh nghia lai" cai ten vua nhap) — nam bao dong gia cho
#    mot thanh ngu pytest hoan toan binh thuong, va banh coc `ruff` dem chung.
from tests import test_423_asv_giao_dien as _mt
from tests import asv_js

moi_truong = _mt.moi_truong
_tao_run_cho = _mt._tao_run_cho


DUONG_ROUTES = (Path(__file__).resolve().parents[1]
                / "apps" / "auto_scan_video" / "routes.py")


def _cay():
    return ast.parse(DUONG_ROUTES.read_bytes().decode("utf-8"))


def _handler():
    """Moi ham co decorator `@router.<method>(...)` — ke ca ham viet sau nay."""
    ra = []
    for nut in ast.walk(_cay()):
        if not isinstance(nut, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for d in nut.decorator_list:
            f = d.func if isinstance(d, ast.Call) else d
            if (isinstance(f, ast.Attribute)
                    and isinstance(f.value, ast.Name) and f.value.id == "router"):
                ra.append((nut, f.attr.lower()))
                break
    return ra


def _ten_goi(than) -> set[str]:
    ra = set()
    for nut in ast.walk(than):
        if isinstance(nut, ast.Call):
            f = nut.func
            if isinstance(f, ast.Name):
                ra.add(f.id)
            elif isinstance(f, ast.Attribute):
                ra.add(f.attr)
    return ra


def _thu_tu_depends(ham) -> list[str]:
    """Ten cac ham `Depends(...)` theo DUNG thu tu khai bao trong chu ky."""
    ra = []
    args = ham.args
    # Mac dinh nam o `defaults`/`kw_defaults`, khong o `args` — phai duyet ca hai.
    for m in list(args.defaults) + [d for d in args.kw_defaults if d is not None]:
        if (isinstance(m, ast.Call) and isinstance(m.func, ast.Name)
                and m.func.id == "Depends" and m.args):
            t = m.args[0]
            ra.append(t.id if isinstance(t, ast.Name) else getattr(t, "attr", "?"))
    return ra


# ══════════════════════════════════════════════════════════════════════════════
#  A. Tai san 4 — co tinh nang dat TRUOC `require_login`, o MOI handler
# ══════════════════════════════════════════════════════════════════════════════

def test_MOI_handler_dat_cong_co_TRUOC_require_login():
    """🔴 `Depends` chay theo thu tu khai bao.

    Dat `_cong_co` **sau** `require_login` thi mot route "da dong" van 303 ve
    `/login` — tuc no van thua nhan minh ton tai. `routes.py:63` ghi ro dieu do,
    va day la phep kiem lam cho loi ghi chu ay co rang.

    ⭐ Duyet bang AST nen sau handler moi cua V5 nam trong pham vi ma khong ai
       phai nho them chung vao mot danh sach.
    """
    for ham, _method in _handler():
        thu_tu = _thu_tu_depends(ham)
        assert "_cong_co" in thu_tu, f"{ham.name}: thieu cong co tinh nang"
        if "require_login" in thu_tu:
            assert thu_tu.index("_cong_co") < thu_tu.index("require_login"), (
                f"{ham.name}: `_cong_co` dat SAU `require_login` — route da dong "
                f"van 303 ve /login")


def test_co_TAT_thi_moi_route_deu_404_KHONG_303(moi_truong, monkeypatch):
    """Doi chung o tang HTTP that cho phep kiem AST o tren.

    ⚠️ Kiem ca route GET lan POST, va kiem ma **404** chu khong chi "khac 200":
       403 xac nhan co mot thu o day, 303 cung vay.
    """
    app, a, csrf, _b, _cb = moi_truong
    monkeypatch.delenv("LTT_AUTO_SCAN_VIDEO", raising=False)
    from fastapi.testclient import TestClient
    from apps.auto_scan_video.manifest import MANIFEST

    la = TestClient(app, base_url="https://testserver", follow_redirects=False)
    for duong in (MANIFEST.route_prefix, f"{MANIFEST.route_prefix}/run/bat-ky"):
        assert la.get(duong).status_code == 404, duong
    assert a.post(f"{MANIFEST.route_prefix}/tao",
                  data={"csrf_token": csrf}).status_code == 404
    la.close()


# ══════════════════════════════════════════════════════════════════════════════
#  B. CSRF tren MOI duong ghi
# ══════════════════════════════════════════════════════════════════════════════

def test_MOI_handler_ghi_deu_kiem_CSRF():
    """Mot handler `POST` khong goi `verify_csrf_token` la mot lo CSRF, ke ca khi
    no "chi luu nhap"."""
    for ham, method in _handler():
        if method in ("get", "head"):
            continue
        assert "verify_csrf_token" in _ten_goi(ham), (
            f"{ham.name} ({method.upper()}): khong kiem CSRF")


def test_MOI_handler_ghi_deu_NHAN_duoc_csrf_token():
    for ham, method in _handler():
        if method in ("get", "head"):
            continue
        ten = {m.arg for m in list(ham.args.args) + list(ham.args.kwonlyargs)}
        assert "csrf_token" in ten, f"{ham.name}: thieu tham so csrf_token"


# ══════════════════════════════════════════════════════════════════════════════
#  C. Tai san 2 — quyen so huu kiem o TANG DICH VU
# ══════════════════════════════════════════════════════════════════════════════

def test_MOI_handler_co_run_id_deu_di_qua_run_cua_toi():
    """⛔ `features.lay_run(db, id, owner)` nem khi khong phai cua ho, nen mot
    handler quen viet menh de loc van khong ro ri — **voi dieu kien no goi qua
    day**. Mot handler doc thang `db.query(AsvRun)` di vong qua ca co che.

    ⭐ V5 them `/run/{id}/nguon` va `/run/{id}/ket-qua`, ca hai deu tra URL
       presigned. Mot lo IDOR o do khong ro ri mot dong sieu du lieu — no ro ri
       ca tep video cua nguoi khac.
    """
    for ham, _method in _handler():
        ten = {m.arg for m in list(ham.args.args) + list(ham.args.kwonlyargs)}
        if "run_id" not in ten:
            continue
        assert "_run_cua_toi" in _ten_goi(ham), (
            f"{ham.name}: nhan run_id ma khong di qua `_run_cua_toi`")


def test_khong_handler_nao_TU_truy_van_bang_run():
    """Chan duong vong: khong ai duoc `db.query(AsvRun)` ngay trong `routes.py`."""
    van = DUONG_ROUTES.read_bytes().decode("utf-8")
    assert "AsvRun" not in van, (
        "`routes.py` cham thang vao model — quyen so huu phai kiem o tang dich vu")


def test_nguoi_khac_KHONG_doc_duoc_run_cua_toi_qua_MOI_duong(moi_truong, tmp_path):
    """Doi chung HTTP: nguoi B thu MOI duong `/run/{id}/...` cua nguoi A.

    ⭐ Duyet duong tu **bang dinh tuyen that**, khong go tay — nen mot duong V5
       them vao ngay mai cung bi thu o day.
    """
    from apps.auto_scan_video.manifest import MANIFEST
    from apps.auto_scan_video.routes import router
    from tests.fixtures import asv_media as fx

    fx.require_ffmpeg()
    _app, a, csrf_a, b, _csrf_b = moi_truong
    r = _tao_run_cho(a, csrf_a, tmp_path)
    assert r.status_code == 200, r.text[:400]
    run_id = r.url.path.rsplit("/", 1)[-1]

    for route in router.routes:
        duong = getattr(route, "path", "")
        if "{run_id}" not in duong or "GET" not in getattr(route, "methods", set()):
            continue
        u = MANIFEST.route_prefix + duong.replace("{run_id}", run_id)
        assert b.get(u, follow_redirects=False).status_code == 404, (
            f"{u} lo lan chay cua nguoi khac")


# ══════════════════════════════════════════════════════════════════════════════
#  D. Hai duong tao lan chay van song
# ══════════════════════════════════════════════════════════════════════════════

def test_duong_multipart_van_tao_duoc_lan_chay(moi_truong, tmp_path):
    from tests.fixtures import asv_media as fx

    fx.require_ffmpeg()
    _app, a, csrf, _b, _cb = moi_truong
    r = _tao_run_cho(a, csrf, tmp_path)
    assert r.status_code == 200, r.text[:400]
    assert "/run/" in r.url.path


def test_duong_ve_tai_len_van_cap_duoc_ve(moi_truong):
    """🔑 Route nay SONG nhung giao dien hom nay **khong goi**.

    Do la P0-1 cua `CURRENT_UI_AUDIT.md`, va phep kiem nay la thu giu cho no van
    chay trong luc V5 viet client cho no.
    """
    from apps.auto_scan_video.manifest import MANIFEST

    _app, a, csrf, _b, _cb = moi_truong
    r = a.post(f"{MANIFEST.route_prefix}/ve",
               data={"csrf_token": csrf, "ten_tep": "a.mp4",
                     "kieu": "video/mp4", "co": 1024})
    assert r.status_code == 200, r.text[:300]
    ra = r.json()
    # ⚠️ `LocalStorage` KHONG cap duoc presigned PUT, nen o may phat trien va
    #    trong bo test route nay tra `{"mode": "local"}` — mot cau tra loi THAT,
    #    khong phai mot loi. Tren R2 no tra `upload_id` + URL.
    #
    # ⭐ Chot CA HAI hinh dang la co y: chot mot hinh se lam phep kiem nay do
    #    tren may co R2, tuc no se do dung o noi no can xanh nhat.
    assert ra.get("mode") == "local" or ra.get("upload_id"), ra


def test_tran_90MB_van_tu_choi_bang_MOT_CAU_TIENG_VIET(moi_truong, monkeypatch):
    """⚠️ Tran ton tai vi Cloudflare cat o 100 MB. Khach phai nhan mot cau tieng
    Viet, khong phai trang loi 413 cua Cloudflare."""
    from apps.auto_scan_video import routes
    from apps.auto_scan_video.manifest import MANIFEST

    monkeypatch.setattr(routes, "TRAN_TAI_LEN", 16)
    _app, a, csrf, _b, _cb = moi_truong
    r = a.post(f"{MANIFEST.route_prefix}/tao",
               data={"csrf_token": csrf, "giong_id": "mau-1"},
               files={"video": ("a.mp4", b"x" * 512, "video/mp4")})
    assert r.status_code == 400
    assert "MB" in r.text


# ══════════════════════════════════════════════════════════════════════════════
#  E. Hop dong san pham khong bi GUI keo di
# ══════════════════════════════════════════════════════════════════════════════

def test_GUI_khong_mo_duoc_thao_tac_dang_bi_CAM():
    """🔴 Day la ranh chan quan trong nhat cua ca chuong trinh V5.

    Prompt V5 §6 xep `zoom` · ti le khung · toc do vao **P0**. `hop_dong_v4`
    cam chung, va chu thich cua chinh no ghi dieu kien de go: *"mot muc roi khoi
    day la mot quyet dinh san pham, va no can mot ADR"*.

    ⇒ `FEATURE_PARITY_MATRIX.md` xu ly bang `DEFER`. Phep kiem nay la thu bien
      `DEFER` tu mot cau trong tai lieu thanh mot rang buoc co rang: mot lan
      "tien tay" them `zoom` vao ban dung se lam luot gate do, va nguoi them phai
      di viet ADR.
    """
    from apps.auto_scan_video import hop_dong_v4

    assert "zoom" in hop_dong_v4.CAM_TRONG_MVP
    assert "crop" in hop_dong_v4.CAM_TRONG_MVP
    assert "reframe" in hop_dong_v4.CAM_TRONG_MVP
    assert "music_replace" in hop_dong_v4.CAM_TRONG_MVP
    assert hop_dong_v4.THAO_TAC_CHO_PHEP[hop_dong_v4.PRESET_GIU_HINH] == ()


def test_mot_nang_luc_da_MO_thi_phai_MO_HAN_o_bang_hop_dong():
    """🔑 Nua con lai cua bai tren, them o pha 14.

    Bai tren tra loi *"cai gi con bi cam"*. Bai nay tra loi *"cai da duoc mo thi
    trong ho so no ra sao"* — va do la cau hoi ma ban cu khong hoi duoc.

    `subtitle_burn` **da roi khoi `CAM_TRONG_MVP`** o pha 14. No duoc mo dung
    duong: doi hop dong, viet `phu_de.py`, ghi `PHA14_PHU_DE.md`. Nen dong cu
    (`assert "subtitle_burn" in CAM_TRONG_MVP`) da noi mot dieu khong con dung.

    ⛔ Nhung xoa dong do la mat mot rang chan. Mot lan "tien tay" tiep theo co
       the go mot muc khoi `CAM_TRONG_MVP` ma **khong** them no vao bang nang
       luc nao — luc ay tinh nang o trang thai *"khong bi cam, va cung khong
       ai khai"*: khong phep kiem nao chan, khong tai lieu nao noi. Do dung la
       `nang-luc-co-nhung-khong-ai-di-tren-duong`.

    ⇒ Bai nay chot mot menh de DUONG: **moi thu da roi khoi bang CAM phai co
      mat o dung mot bang nang luc.** Roi khoi ca hai la mot lo hong.
    """
    from apps.auto_scan_video import hop_dong_v4

    da_khai = (set(hop_dong_v4.NANG_LUC_DOI_DIEM_ANH)
               | set(hop_dong_v4.NANG_LUC_KHONG_DOI_DIEM_ANH))

    # `subtitle_burn` — truong hop cu the pha 14 vua mo.
    assert "subtitle_burn" not in hop_dong_v4.CAM_TRONG_MVP
    assert "subtitle_burn" in hop_dong_v4.NANG_LUC_DOI_DIEM_ANH
    assert "subtitle_burn" not in hop_dong_v4.NANG_LUC_KHONG_DOI_DIEM_ANH

    # ⭐ Va truc thu hai cua no — `.srt` — o **bang khac**, vi no khong cham
    #    mot diem anh nao. Gop hai bang lam mot se khoa mat lua chon phu de duy
    #    nhat con lai o preset giu hinh, va khoa im lang.
    assert "subtitle_srt" in hop_dong_v4.NANG_LUC_KHONG_DOI_DIEM_ANH
    assert "subtitle_srt" not in hop_dong_v4.NANG_LUC_DOI_DIEM_ANH

    # Menh de tong quat: khong nang luc nao vua bi cam vua duoc khai.
    chong = da_khai & set(hop_dong_v4.CAM_TRONG_MVP)
    assert not chong, (
        f"{sorted(chong)} vua nam trong CAM_TRONG_MVP vua duoc khai la nang "
        f"luc — ma thi dang chay, hop dong thi noi 'chua lam'")


def test_app_van_CHUA_mo_cho_khach_AN_DANH():
    """V5 la mot chuong trinh GIAO DIEN. No khong duoc PHAT HANH app.

    ⚠️ 13/09/2026 — chu san pham chot bat app cho khach DA DANG NHAP kiem thu,
       nen `enabled` da thanh `True`. Dieu do KHONG phai "phat hanh": phat hanh
       la `public=True` + `lifecycle="released"`, va ca hai van chua xay ra.

    ⇒ Menh de cua V5 giu nguyen, chi duoc phat bieu lai cho dung: V5 khong duoc
      dua app ra KHACH AN DANH va khong duoc tu nhan la da nghiem thu.

    (Xem ban song doi o `test_423_asv_giao_dien.py` — hai bo canh cung mot ranh
     gioi tu hai phia, nen sua mot ma quen kia la de lai mot cua mo.)
    """
    from apps.auto_scan_video.manifest import MANIFEST

    assert MANIFEST.enabled is True, (
        "chu san pham da bat app cho khach dang nhap (13/09); tat lai la mot "
        "thay doi CO Y va phai sua ca chu thich tren")
    assert MANIFEST.public is False, "V5 da day app ra khach AN DANH"
    assert MANIFEST.lifecycle == "development", "V5 tu nhan da nghiem thu"


def test_routes_van_trong_tran_hop_dong_app():
    """900 dong / 30 handler. V5 them ~6 handler; phep kiem nay bat luc no vuot."""
    so_dong = len(DUONG_ROUTES.read_bytes().decode("utf-8").splitlines())
    assert so_dong <= 900, f"routes.py {so_dong} dong — vuot tran hop dong app"
    assert len(_handler()) <= 30


# ══════════════════════════════════════════════════════════════════════════════
#  F. Nhan giai doan van lay khoa TU pipeline
# ══════════════════════════════════════════════════════════════════════════════

def test_nhan_giai_doan_phu_KIN_chuoi_pipeline():
    """Tai san 1: doi ten mot giai doan ma quen sua nhan thi phep kiem do, thay
    vi giao dien hien mot o trong."""
    from apps.auto_scan_video import pipeline
    from apps.auto_scan_video.routes import NHAN_GIAI_DOAN

    # ⚠️ `pipeline.CHUOI` la tuple cac `GiaiDoan`, khong phai chuoi ten.
    #    `TEN_GIAI_DOAN` la ban ten, va no duoc sinh TU `CHUOI` nen no khong troi.
    assert set(NHAN_GIAI_DOAN) == set(pipeline.TEN_GIAI_DOAN)
    assert all(str(v).strip() for v in NHAN_GIAI_DOAN.values())


# ══════════════════════════════════════════════════════════════════════════════
#  G. Chay lai voi cai dat cu (R2) — va no la mot duong DOC LAN CHAY
# ══════════════════════════════════════════════════════════════════════════════

def test_nap_lai_dien_san_preset_va_giong_cua_lan_chay_cu(moi_truong, tmp_path):
    """Menh de trung tam cua R2: cai dat cu **den duoc** man Studio."""
    from tests.fixtures import asv_media as fx

    fx.require_ffmpeg()
    _app, a, csrf, _b, _cb = moi_truong
    r = _tao_run_cho(a, csrf, tmp_path,
                     preset="smart_localize", che_do="natural")
    assert r.status_code == 200, r.text[:300]
    run_id = r.url.path.rsplit("/", 1)[-1]

    van = a.get(f"/auto-scan-video?run_id={run_id}").text
    # Preset cat phai duoc CHON san, khong phai preset mac dinh.
    m = re.search(r'<input type="radio" name="preset" value="smart_localize"[^>]*>', van)
    assert m and "checked" in m.group(0), "preset cu khong duoc dien san"
    m2 = re.search(r'<input type="radio" name="che_do" value="natural"[^>]*>', van)
    assert m2 and "checked" in m2.group(0), "che do cu khong duoc dien san"


def test_nap_lai_NOI_RA_rang_no_vua_dien_san(moi_truong, tmp_path):
    """⭐ Khong co dong bao nay, khach thay mot form khac mac dinh ma khong biet
    vi sao — va se tuong he thong tu doi."""
    from tests.fixtures import asv_media as fx

    fx.require_ffmpeg()
    _app, a, csrf, _b, _cb = moi_truong
    r = _tao_run_cho(a, csrf, tmp_path)
    run_id = r.url.path.rsplit("/", 1)[-1]
    van = a.get(f"/auto-scan-video?run_id={run_id}").text
    assert 'role="status"' in van


def test_nap_lai_KHONG_mang_theo_vung_che(moi_truong, tmp_path):
    """⛔ Vung che la toa do tren khung hinh cua MOT video. Dat chung len video
    khac la che nham mot vung khach khong chon — va khach khong biet, vi o chon
    tep da doi con cac o khac thi khong."""
    from tests.fixtures import asv_media as fx

    fx.require_ffmpeg()
    _app, a, csrf, _b, _cb = moi_truong
    vung = ('[{"loai":"lam_mo","y0":0.8,"y1":0.95,"x0":0.1,"x1":0.9}]')
    r = _tao_run_cho(a, csrf, tmp_path,
                     preset="smart_localize", vung=vung)
    assert r.status_code == 200, r.text[:300]
    run_id = r.url.path.rsplit("/", 1)[-1]

    van = a.get(f"/auto-scan-video?run_id={run_id}").text
    m = re.search(r'<input type="hidden" name="vung"[^>]*>', van)
    assert m and 'value=""' in m.group(0), "vung che bi nap lai — khong duoc"


def test_nguoi_khac_KHONG_nap_lai_duoc_cai_dat_cua_toi(moi_truong, tmp_path):
    """🔴 `run_id` trong URL la mot chuoi khach **sua duoc**.

    ⭐ Va day la ly do tham so ten dung la `run_id`: phep kiem AST o muc C tren
       tu dong phu no, khong ai phai nho them mot dong vao mot danh sach.
    """
    from tests.fixtures import asv_media as fx

    fx.require_ffmpeg()
    _app, a, csrf_a, b, _cb = moi_truong
    r = _tao_run_cho(a, csrf_a, tmp_path)
    run_id = r.url.path.rsplit("/", 1)[-1]
    assert b.get(f"/auto-scan-video?run_id={run_id}",
                 follow_redirects=False).status_code == 404


def test_run_id_bia_dat_tra_404_chu_khong_500(moi_truong):
    _app, a, _csrf, _b, _cb = moi_truong
    assert a.get("/auto-scan-video?run_id=khong-co-that",
                 follow_redirects=False).status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
#  Bo dieu kien cua CLIENT phai la ban SAO CHIEU cua bo dieu kien MAY CHU
# ═════════════════════════════════════════════════════════════════════════════

def _bo_chu_thich_js(ma: str) -> str:
    """Bo chu thich khoi JS truoc khi quet chuoi.

    🔴 Ban dau phep kiem duoi quet ca tep, va no **do ngay tren chinh doan
       chu thich giai thich no** — doan ay nhac ten hang so trong ngoac kep de
       noi ro dieu bi cam. Mot bo do quet van ban tho thi trung phat viec giai
       thich, va cach nguoi ta tranh hinh phat ay la **ngung giai thich**.

    ⚠️ Day khong phai mot trinh phan tich JS. No bo `/* */` va nhung dong bat
       dau bang `//`, the thoi. No se bo nham neu co ai viet mot chuoi chua
       `/*`. Ranh gioi do ghi ra day de nguoi sau biet no do duoc gi.
    """
    ra, i = [], 0
    while i < len(ma):
        j = ma.find("/*", i)
        if j < 0:
            ra.append(ma[i:])
            break
        ra.append(ma[i:j])
        k = ma.find("*/", j + 2)
        i = len(ma) if k < 0 else k + 2
    con = "".join(ra)
    return chr(10).join(dong for dong in con.splitlines()
                        if not dong.lstrip().startswith("//"))


def test_o_giong_chi_BAT_BUOC_o_dung_che_do_may_chu_doi():
    """🔴 Khiem khuyet buoc 24 (`V5_REAUDIT.md` §2) tim ra.

    `routes.tao` chi doi `giong_id` khi che do la `CHE_DO_GIONG_TU_CHON`. The
    `<select>` thi mang `required` **co dinh**, nen o che do kia trinh duyet
    cuong che mot truong ma may chu khong doi — hai ben noi hai luat khac nhau
    ve cung mot o.

    ⚠️ No **chua tung no**, vi danh sach giong luon co mot muc chon san. Mot
       mau thuan im lang nhu the song rat lau, va se thanh loi that dung vao ngay
       co nguoi them mot muc rong vao dau danh sach.

    ⭐ Phep kiem nay chot **cach noi**, khong chot ket qua: `data-can-giong` phai
       do template phat ra tu chinh hang so hop dong. Chot ket qua thi mot ban
       sao chuoi "USER_SELECTED" trong JS van xanh — ma do chinh la thu can cam.
    """
    from apps.auto_scan_video import hop_dong_v4

    mau = (DUONG_ROUTES.parent / "templates" / "asv_trang_chinh.html"
           ).read_text(encoding="utf-8")
    assert "che_do_giong_can_giong" in mau, (
        "template khong doc hang so hop dong — hoac no dang tu quyet, hoac ai do "
        "da go bien nay khoi ngu canh")
    assert "data-can-giong" in mau

    # Ngu canh cua `trang_chinh` phai phat dung hang so ay, khong phat mot chuoi
    # go tay trung tinh co.
    ma = DUONG_ROUTES.read_text(encoding="utf-8")
    assert "\"che_do_giong_can_giong\": hop_dong_v4.CHE_DO_GIONG_TU_CHON" in ma, (
        "ngu canh dang phat mot gia tri KHAC hang so hop dong")

    # Va JS phai DOC thuoc tinh do, khong duoc chep lai gia tri.
    js = asv_js.doc("asv/giong.js")
    assert "dataset.canGiong" in js, (
        "asv/giong.js khong doc `data-can-giong`")
    assert f'"{hop_dong_v4.CHE_DO_GIONG_TU_CHON}"' not in _bo_chu_thich_js(js), (
        f"asv/giong.js dang chep hang so hop dong ({hop_dong_v4.CHE_DO_GIONG_TU_CHON}) "
        "vao ma client — mot ban sao se troi khi hop dong doi, va troi im lang")


# ════════════════════════════════════════════════════════════════════════════
#  Moi mat loc ma nen tang bay ra deu phai toi duoc tay khach
# ════════════════════════════════════════════════════════════════════════════

def test_MOI_MAT_LOC_giong_deu_co_o_chon_tren_man_hinh(moi_truong):
    """🔴 Khiem khuyet tim ra 08/09, SAU khi buoc 24 da bao “xong”.

    `gia.NHAN_LOC` mang **ba** mat loc va `routes.danh_muc_giong` da loc theo
    ca ba tu truoc. Template thi chi ve **hai** o. Nen mat loc thu ba
    (`phong_cach`) song trong ma, duoc kiem thu, va **vo hinh voi khach**.

    ⚠️ Vi sao buoc 24 khong bat duoc: no doi chieu voi 22 hang cua bang
       audit **cu**, chu khong doi chieu voi cot *“V5 lam ngay”* cua chinh
       `V5_UI_INFORMATION_ARCHITECTURE.md` §4. Mot bai tai audit chi thay
       duoc nhung gi thuoc do cua no ke ten — doi thuoc do la doi ket qua,
       va thuoc do cu khong he sai, no chi hep hon loi hua.

    ⭐ Nen phep kiem nay chot theo **quy tac**: lay danh sach mat loc tu
       `gia.NHAN_LOC` luc chay, khong go tay ba cai ten. Ngay `ltt_voice`
       them mat thu tu, no do ngay — khong cho ai nho ra.
    """
    from apps.auto_scan_video import gia

    a = moi_truong[1]
    van = a.get("/auto-scan-video/").text

    thieu = []
    for mat, nhan in gia.NHAN_LOC.items():
        if not nhan:
            # Mat khong co nhan nao thi mot o chon rong la vo nghia.
            continue
        ma_o = "asv-loc-" + mat.replace("_", "-")
        if f'id="{ma_o}"' not in van:
            thieu.append(f"{mat} (cho o `{ma_o}`)")
    assert not thieu, (
        "nen tang bay ra mat loc ma giao dien khong ve o chon: "
        + ", ".join(thieu))


def test_moi_giong_MANG_du_thuoc_tinh_cho_tung_mat_loc(moi_truong):
    """Mot o chon khong loc duoc gi neu `<option>` khong mang nhan tuong ung.

    ⚠️ Tach khoi phep kiem tren la co y: hai cach hong khac nhau. O chon
       thieu thi khach **khong thay** mat loc; thuoc tinh thieu thi khach
       thay o chon, bam vao, va danh sach **rong** — kieu thu hai te hon vi
       no trong nhu san pham hong chu khong nhu tinh nang chua co.
    """
    from apps.auto_scan_video import gia

    a = moi_truong[1]
    van = a.get("/auto-scan-video/").text
    i = van.index('id="asv-giong"')
    khoi = van[i:van.index("</select>", i)]

    thieu = [mat for mat, nhan in gia.NHAN_LOC.items()
             if nhan and f'data-{mat.replace("_", "-")}=' not in khoi]
    assert not thieu, (
        "`<option>` giong khong mang nhan cho mat loc: " + ", ".join(thieu))

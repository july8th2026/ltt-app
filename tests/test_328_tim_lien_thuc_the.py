"""O tim lien thuc the (`24_DEFERRED_POST_MVP.md` muc B, mo khoa 2026-08-29).

## Vi sao muc nay bi chan lau den vay

Anh mockup ve mot o "Tim nguoi dung, don hang, log...". Suot dot MVP o do CHI tim
khach hang, va muc B ghi ro ly do: **khong co read-model nao tra lien thuc the**,
kem mot luat:

    ⛔ Khong lam o nhan ca don hang/log roi tra rong. Mot o hua nhieu hon no lam
       duoc la mot loi VAN HANH, khong phai mot thieu sot tham my.

`admin_console.tim_lien_thuc_the()` nay la read-model do. Tep nay chot rang
**nhan cua o va nang luc that cua no khong tach nhau ra** — do la ca noi dung
cua muc B.

## Cai bay tep nay canh

`payment_orders.order_code` la **BigInteger**. So sanh no voi mot chuoi chu la
mot loi CSDL o PostgreSQL, khong phai mot ket qua rong — nen mot o tim nhan moi
thu phai tu biet khi nao KHONG duoc cham vao bang do.
"""
from __future__ import annotations

import re
import uuid

import pytest

GOC_TEP = __file__


@pytest.fixture()
def app(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'tim.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-secret-tim-lien-thuc-the")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core.models import Job, PaymentOrder
    from platform_core.public_api.tables import ApiRequestLog
    from platform_core.users import tao_nguoi_dung

    gen = dbmod.get_session(); db = next(gen)
    try:
        tao_nguoi_dung(db, email="sep@example.com", password="matkhau-tot-12",
                       role="admin", is_verified=True)
        u = tao_nguoi_dung(db, email="mua.hang@congty.vn",
                           password="matkhau-tot-12", role="user",
                           is_verified=True)
        job = Job(user_id=u.id, app_slug="anhnoibo", job_type="render",
                  status="done", params={})
        db.add(job)
        db.add(PaymentOrder(order_code=778899, user_id=u.id, price_vnd=200000,
                            credits=2000, status="PAID", credited=True))
        db.add(ApiRequestLog(
            id=str(uuid.uuid4()), request_id="reqabc123456789", user_id=u.id,
            key_id="k_t", method="POST", route="/v1/tools/image.ltt",
            status=200, code="", latency_ms=12, tool="image.ltt",
            job_id="", credit_delta=0))
        db.commit()
        ids = {"uid": u.id, "job": job.id, "email": u.email}
    finally:
        try: next(gen)
        except StopIteration: pass

    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver")
    tok = re.search(r'name="csrf_token" value="([^"]+)"',
                    client.get("/login").text)
    r = client.post("/login", data={"username": "sep@example.com",
                                    "password": "matkhau-tot-12",
                                    "csrf_token": tok.group(1)},
                    follow_redirects=False)
    assert r.status_code == 303
    client.ids = ids
    try:
        yield client
    finally:
        dbmod.reset_engine()


def _tim(client, q: str):
    return client.get(f"/admin/tim?q={q}", follow_redirects=False)


# ── Nam loai, moi loai co mot bang that ──────────────────────────────────────

@pytest.mark.parametrize("loai,lay", [
    ("khach", lambda ids: "mua.hang@congty.vn"),
    ("khach_id", lambda ids: ids["uid"]),
    ("don", lambda _: "778899"),
    ("job", lambda ids: ids["job"][:12]),
    ("request", lambda _: "reqabc123456789"),
])
def test_moi_loai_tim_duoc_va_dan_toi_dich(app, loai, lay):
    """Mot ket qua duy nhat thi di THANG toi no.

    ⭐ Bat mot nguoi dang xu su co bam them mot lan vao mot danh sach co dung
       MOT dong la mot buoc thua o dung luc ho khong co thoi gian.
    """
    r = _tim(app, lay(app.ids))
    assert r.status_code == 303, (loai, r.status_code, r.text[:300])
    dich = r.headers["location"]
    assert dich.startswith("/admin/"), (loai, dich)
    # Va dich phai mo duoc that, khong chi la mot chuoi dung dinh dang.
    assert app.get(dich).status_code == 200, (loai, dich)


def test_nhieu_ket_qua_thi_hien_trang_phan_loai(app):
    """Chuoi khop nhieu khach ⇒ khong chuyen huong, ma liet ke theo nhom."""
    from platform_core import db as dbmod
    from platform_core.users import tao_nguoi_dung

    gen = dbmod.get_session(); db = next(gen)
    try:
        tao_nguoi_dung(db, email="mua.hang.2@congty.vn",
                       password="matkhau-tot-12", role="user", is_verified=True)
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass

    r = _tim(app, "mua.hang")
    assert r.status_code == 200
    assert "2 kết quả" in r.text
    assert "Khách hàng" in r.text


# ── Bay kieu du lieu ─────────────────────────────────────────────────────────

def test_chuoi_chu_khong_cham_vao_cot_so(app):
    """🔴 `payment_orders.order_code` la BigInteger.

    So sanh no voi mot chuoi chu la mot LOI CSDL o PostgreSQL, khong phai mot
    ket qua rong. Mot o tim nhan moi thu phai tu biet khi nao khong duoc cham
    vao bang do — neu khong, go mot email vao o tim se lam do trang 500.
    """
    r = _tim(app, "khong-phai-so-gi-ca")
    assert r.status_code == 200
    assert "Không có gì khớp" in r.text


def test_so_qua_lon_khong_lam_do_trang(app):
    """Mot chuoi so dai hon 64 bit van la `.isdigit()`, va `int()` nhan no —
    nhung cot BigInteger thi khong. Phai tra 200, khong phai 500."""
    r = _tim(app, "9" * 40)
    assert r.status_code in (200, 303), r.status_code


# ── Nhan khong duoc hua nhieu hon nang luc ───────────────────────────────────

def test_nhan_o_tim_va_read_model_khong_tach_nhau(app):
    """⛔ Chinh la luat cua muc B. Nhan liet ke NAM loai; read-model phai tra
    dung nam loai do.

    Neu ai them mot loai vao nhan ma khong them bang vao read-model, phep kiem
    nay do — va do la dung luc no phai do, chu khong phai luc mot nguoi van hanh
    go ma don vao o roi tuong don do khong ton tai.
    """
    import pathlib

    goc = pathlib.Path(GOC_TEP).resolve().parents[1]
    vo = (goc / "server/templates/admin/_vo.html").read_text(encoding="utf-8")
    o = vo[vo.index('id="adm-q"'):vo.index('id="adm-q"') + 400]
    for tu in ("email", "User ID", "mã đơn", "job id", "correlation id", "mã khoá"):
        assert tu in o, f"nhan o tim thieu {tu!r}"

    nguon = (goc / "platform_core/admin_console.py").read_text(encoding="utf-8")
    than = nguon[nguon.index("def tim_lien_thuc_the("):]
    for loai in ('"khach"', '"don"', '"job"', '"request"', '"khoa"'):
        assert f'_them({loai}' in than, f"read-model thieu loai {loai}"
    # Va template phai co nhan cho DUNG nam loai do — them mot loai vao
    # read-model ma quen nhan thi nhom hien ra bang khoa may (`don`, `khoa`).
    vo_kq = (goc / "server/templates/admin/tim_kiem.html").read_text(
        encoding="utf-8")
    for loai in ("khach", "don", "job", "request", "khoa"):
        assert f'"{loai}"' in vo_kq, f"template thieu nhan cho {loai!r}"


def test_read_model_khong_tu_quyet_nhan(app):
    """⛔ `platform_core` tra DU LIEU; template quyet CHU.

    Ban dau ham nay tra san "Khách hàng", "đã xác thực"... va
    `tools/check_i18n.py` bat ngay: muoi chuoi hien ra cho nguoi dung nam trong
    tang du lieu (774 -> 784). Banh coc do noi ve i18n, nhung thu no that su
    chan la **tang trinh bay ro xuong tang du lieu**.
    """
    import ast
    import pathlib

    goc = pathlib.Path(GOC_TEP).resolve().parents[1]
    nguon = (goc / "platform_core/admin_console.py").read_text(encoding="utf-8")

    # ⚠️ Doc bang `ast`, khong bang `in`. Chu thich va docstring GIAI THICH vi
    #    sao mot nhan bi cam — chung phai duoc nhac ten o do. Quet chuoi tho se
    #    bat chinh loi giai thich va bien mot phep kiem dung thanh mot phep kiem
    #    khong the thoa man.
    ham = next(n for n in ast.walk(ast.parse(nguon))
               if isinstance(n, ast.FunctionDef)
               and n.name == "tim_lien_thuc_the")
    than = list(ham.body)
    if (than and isinstance(than[0], ast.Expr)
            and isinstance(than[0].value, ast.Constant)):
        than = than[1:]                              # bo docstring

    chuoi = [c.value for nut in than for c in ast.walk(nut)
             if isinstance(c, ast.Constant) and isinstance(c.value, str)]
    for chu in ("Khách hàng", "đã xác thực", "chưa xác thực", "đã cộng",
                "không đặt tên", "Lời gọi API", "Khoá của khách"):
        xau = [g for g in chuoi if chu in g]
        assert not xau, f"nhan {chu!r} phai o template, khong o read-model: {xau}"


def test_khong_tim_toan_van(app):
    """⚠️ Khong `LIKE %q%` tren `jobs.params` hay `nhat_ky_admin.chi_tiet`.

    Ca hai la quet toan bang tren bang lon nhat he thong, va nguoi go vao o nay
    la dang co su co — mot truy van 30 giay o dung luc do te hon la khong co o
    tim. Phep kiem doc chinh nguon, vi day la mot rang buoc HIEU NANG: no khong
    lo ra o hanh vi cho toi khi bang du lon.
    """
    import pathlib

    goc = pathlib.Path(GOC_TEP).resolve().parents[1]
    nguon = (goc / "platform_core/admin_console.py").read_text(encoding="utf-8")
    than = nguon[nguon.index("def tim_lien_thuc_the("):]
    for cam in ("Job.params", "NhatKyAdmin.chi_tiet", "Job.error"):
        assert cam not in than, f"{cam} la mot phep quet toan bang"
    # Tien to job/request duoc phep, nhung phai la `q%` chu khong phai `%q%`.
    assert 'like(f"%{q}' not in than


def test_tien_to_qua_ngan_thi_khong_tra_bang_lon(app):
    """`LIKE 'a%'` tren bang job la quet gan nhu toan bang, va no khong thu hep
    duoc gi cho nguoi tim. Trang phai NOI RA dieu do thay vi im lang tra rong."""
    from platform_core import admin_console

    r = _tim(app, app.ids["job"][:3])
    assert r.status_code == 200
    assert str(admin_console.TIM_TIEN_TO_TOI_THIEU) in r.text


# ── Bi mat ───────────────────────────────────────────────────────────────────

def test_khong_tim_theo_nua_bi_mat_cua_khoa(app):
    """⛔ May chu chi giu dau van tay mot chieu cua khoa khach.

    Nen o tim CHI duoc tra `key_id` — nua cong khai. Khong co gi de tim theo nua
    bi mat, ke ca neu ai do muon.
    """
    import pathlib

    goc = pathlib.Path(GOC_TEP).resolve().parents[1]
    nguon = (goc / "platform_core/admin_console.py").read_text(encoding="utf-8")
    than = nguon[nguon.index("def tim_lien_thuc_the("):]
    for cam in ("secret_hash", "token_hash", "credential_enc", "password_hash"):
        assert cam not in than, cam

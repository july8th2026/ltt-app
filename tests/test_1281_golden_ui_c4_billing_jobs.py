"""Golden UI C4 (17/09/2026) — họ Billing + Jobs, vòng hai theo người chấm độc lập V2.

Billing
1. Đơn `pending` không có link cổng nói nhất quán "thủ công": không hứa "credit
   cộng tự động", fragment không nói "tự kiểm tra mỗi 4 giây" (vẫn poll).
2. Một badge trạng thái (tiêu đề trang) — fragment đang chờ không lặp badge;
   nút mở cổng căn giữa, cách bảng tóm tắt.
3. Mọi thông báo ở MỘT chỗ: đầu thẻ đơn, trước bảng tóm tắt; nút trong khối đơn
   đã chết cùng cỡ nút chính (không `btn sm`).
4. Trang đơn hai cột ở màn rộng: thẻ đơn + khối hướng dẫn/hỗ trợ theo trạng thái;
   chân trang dính đáy khi trang ngắn (CSS trong khối C4, không sửa base.html).
5. `/nap`: từ ba gói, gói giữa nổi bật, nút các gói khác là nút phụ; màn vừa ba cột.

Jobs
1. Chấm dòng thời gian trung tính; mốc đang diễn ra cảnh báo; đỏ chỉ cho lỗi.
2. Việc hoàn tất có nút mở ứng dụng (+ nút tới tệp kết quả nếu có).
3. `/jobs` không in số dư lần hai; bộ lọc là lưới cân.
4. Việc lỗi/hủy không vẽ thanh tiến độ ("Dừng ở N%"); danh sách trống chỉ một nút chính.
5. Câu giải thích việc đã hủy viết tự nhiên.

Hợp đồng giữ nguyên: form `/nap/tao`, `hx-get`/`hx-trigger`, đúng một `<div id="tt"`,
`role`/`aria-live`, tên trường lọc.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[1]
CSS = (GOC / "server" / "static" / "ltt.css").read_text(encoding="utf-8")


def _dang_nhap(c, email):
    tok = re.search(r'name="csrf_token" value="([^"]+)"', c.get("/login").text).group(1)
    r = c.post("/login", data={"username": email, "password": "matkhau-tot",
                               "csrf_token": tok}, follow_redirects=False)
    assert r.status_code == 303


@pytest.fixture()
def web(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    url = f"sqlite:///{(tmp_path / 'c4.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-golden-c4")
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "test-material-cho-secretbox-123")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    monkeypatch.delenv("RESEND_API_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core import credit
    from platform_core.models import CreditPackage, Job, JobEvent, PaymentOrder
    from platform_core.users import tao_nguoi_dung

    gen = dbmod.get_session(); s = next(gen)
    u = tao_nguoi_dung(s, email="c4@x.com", password="matkhau-tot", is_verified=True)
    tao_nguoi_dung(s, email="c4-trong@x.com", password="matkhau-tot", is_verified=True)
    credit.nap(s, u.id, 1250)
    goi = [CreditPackage(name="Khoi dau", price_vnd=50_000, credits_base=500,
                         bonus_percent=0, sort_order=1),
           CreditPackage(name="Pho bien", price_vnd=200_000, credits_base=2000,
                         bonus_percent=10, sort_order=2),
           CreditPackage(name="Chuyen nghiep", price_vnd=1_000_000, credits_base=10_000,
                         bonus_percent=25, sort_order=3)]
    s.add_all(goi); s.flush()
    now = datetime.now(timezone.utc)
    ids: dict = {"don": {}, "job": {}}

    def don(ten, st, link="https://pay.example/c4", **kw):
        o = PaymentOrder(order_code=790_000 + len(ids["don"]), user_id=u.id,
                         package_id=goi[1].id, price_vnd=200_000, credits=2200,
                         bonus_percent=10, status=st, credited=st == "paid",
                         gateway="payos", checkout_url=link,
                         created_at=now - timedelta(minutes=len(ids["don"])),
                         expires_at=now + timedelta(minutes=20), **kw)
        s.add(o); s.flush()
        ids["don"][ten] = o.id

    don("pending", "pending")
    don("pending_khong_link", "pending", link="")
    don("paid", "paid", paid_at=now, gateway_ref="FT-C4")
    for st in ("expired", "cancelled", "failed"):
        don(st, st)

    def job(ten, status, pct, result=None, events=(), **kw):
        j = Job(user_id=u.id, app_slug="taoanh", job_type="taoanh.generate",
                params={"prompt": "BI-MAT-PROMPT"}, status=status, progress=pct,
                result=result, **kw)
        s.add(j); s.flush()
        for seq, (code, lvl, text) in enumerate(events, start=1):
            s.add(JobEvent(job_id=j.id, user_id=u.id, app_slug="taoanh", sequence=seq,
                           event_code=code, level=lvl, public_message=text, details={}))
        ids["job"][ten] = j.id

    batdau = [("submitted", "info", "Đã tiếp nhận yêu cầu."), ("started", "info", "Bắt đầu xử lý.")]
    job("done", "done", 100, result={"credit": 1}, events=batdau + [
        ("completed", "info", "Đã hoàn tất.")])
    job("done_tep", "done", 100, result={"image_key": "u/a.png"})
    job("running", "running", 45, progress_msg="Đang tạo ảnh 2/4", events=batdau)
    job("error", "error", 30, error="RAW", events=batdau + [
        ("failed", "error", "Không thể hoàn tất yêu cầu. Bạn có thể thử lại.")])
    job("cancelled", "cancelled", 10, events=batdau)
    s.commit(); s.close()

    from server.app import create_app
    app = create_app()
    c = TestClient(app, base_url="https://testserver")
    _dang_nhap(c, "c4@x.com")
    trong = TestClient(app, base_url="https://testserver")
    _dang_nhap(trong, "c4-trong@x.com")
    try:
        yield c, trong, ids
    finally:
        dbmod.reset_engine()


def _khoi_c4() -> str:
    khoi = CSS.split("/* === C4: BILLING-JOBS === */", 1)
    assert len(khoi) == 2, "khối CSS C4 phải có mặt"
    return re.split(r"/\* === C\d: ", khoi[1], maxsplit=1)[0]


# ── Billing ──────────────────────────────────────────────────────────────────

def test_don_khong_link_noi_nhat_quan_thu_cong(web):
    c, _t, ids = web
    html = c.get(f"/nap/don/{ids['don']['pending_khong_link']}").text
    assert "credit cộng tự động" not in html
    assert "thủ công" in html and "Thanh toán thủ công" in html
    assert "Cổng thanh toán chưa cấu hình" in html
    frag = c.get(f"/nap/don/{ids['don']['pending_khong_link']}/trangthai").text
    assert "Tự kiểm tra mỗi 4 giây" not in frag
    assert "Đang chờ thanh toán" in frag and 'hx-trigger="every 4s"' in frag
    # Đơn có link vẫn giữ lời hứa tự động + hướng dẫn thanh toán.
    co_link = c.get(f"/nap/don/{ids['don']['pending']}").text
    assert "credit cộng tự động" in co_link and "Cách thanh toán" in co_link


def test_mot_badge_va_mot_cho_cho_thong_bao(web):
    c, _t, ids = web
    html = c.get(f"/nap/don/{ids['don']['pending']}?cancel=true").text
    assert html.count('data-trang-thai="pending"') == 1
    assert html.count('<div class="billing-status-slot" id="tt"') == 1
    assert 'role="status" aria-live="polite"' in html
    # Thông báo hủy ở cổng + ô trạng thái đứng TRƯỚC bảng tóm tắt; nút cổng sau cùng.
    i_huy = html.index("Bạn đã huỷ ở bước thanh toán")
    i_tt = html.index('id="tt"')
    i_tom_tat = html.index("Tóm tắt thanh toán")
    i_cong = html.index("billing-cta-full")
    assert i_huy < i_tt < i_tom_tat < i_cong
    frag = c.get(f"/nap/don/{ids['don']['pending']}/trangthai").text
    assert 'class="badge' not in frag, "fragment không lặp badge của tiêu đề"
    assert frag.count('<div id="tt"') == 1


@pytest.mark.parametrize("st", ["expired", "cancelled", "failed"])
def test_don_da_chet_nut_cung_co_va_khoi_ho_tro(web, st):
    c, _t, ids = web
    frag = c.get(f"/nap/don/{ids['don'][st]}/trangthai").text
    assert 'class="btn sm"' not in frag and '<a class="btn" href="/nap">' in frag
    assert 'role="alert"' in frag and "hx-trigger" not in frag
    html = c.get(f"/nap/don/{ids['don'][st]}").text
    assert "Cần hỗ trợ?" in html and "Cách thanh toán" not in html
    assert html.index('id="tt"') < html.index("Tóm tắt thanh toán")


def test_don_da_tra_khong_noi_het_han_ke_ca_khoi_ben(web):
    c, _t, ids = web
    html = c.get(f"/nap/don/{ids['don']['paid']}").text
    assert "Hết hạn" not in html and "Cần hỗ trợ?" in html
    assert 'class="billing-order-layout"' in html


def test_nap_goi_giua_noi_bat_goi_khac_nut_phu(web):
    c, _t, _ids = web
    html = c.get("/nap").text
    assert html.count("billing-package--noi-bat") == 1
    the = re.findall(r'<article class="appcard billing-package[^"]*">.*?</article>', html, flags=re.S)
    assert len(the) == 3
    assert "billing-package--noi-bat" in the[1]
    assert '<button class="btn"' in the[1]
    assert '<button class="btn ghost"' in the[0] and '<button class="btn ghost"' in the[2]
    # Hợp đồng form tạo đơn.
    assert html.count('action="/nap/tao"') == 3 and html.count('name="package_id"') == 3


def test_css_c4_billing_chi_token_va_bo_cuc():
    c4 = _khoi_c4()
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", c4), "khối C4 chỉ dùng token"
    assert ".billing-grid{grid-template-columns:repeat(3,minmax(0,1fr))}" in c4
    assert "grid-template-columns:minmax(0,1fr) minmax(280px,360px)" in c4
    assert "body:has(.billing-order-page)" in c4
    assert ".billing-order .billing-cta-full{display:flex" in c4


# ── Jobs ─────────────────────────────────────────────────────────────────────

def test_cham_dong_thoi_gian_trung_tinh_do_chi_cho_loi():
    c4 = _khoi_c4()
    assert ".job-timeline .job-event-dot{background:var(--text-muted)}" in c4
    do = [ln for ln in c4.splitlines() if "var(--err)" in ln]
    assert do and all("event-error" in ln for ln in do)


def test_viec_dang_chay_moc_cuoi_la_moc_hien_tai(web):
    c, _t, ids = web
    html = c.get(f"/jobs/{ids['job']['running']}").text
    moc = re.findall(r'<li class="(event-[^"]*)">', html)
    assert moc[-1].endswith("event-now") and all("event-now" not in m for m in moc[:-1])


def test_viec_xong_co_nut_mo_app_va_tep(web):
    c, _t, ids = web
    html = c.get(f"/jobs/{ids['job']['done']}").text
    assert re.search(r'<a class="btn" href="/taoanh">', html)
    assert "#job-artifacts" not in html
    assert "ma-completed" in html
    tep = c.get(f"/jobs/{ids['job']['done_tep']}").text
    assert 'href="#job-artifacts"' in tep and 'id="job-artifacts"' in tep


@pytest.mark.parametrize("ten,pct", [("error", 30), ("cancelled", 10)])
def test_viec_dung_khong_ve_thanh_tien_do(web, ten, pct):
    c, _t, ids = web
    html = c.get(f"/jobs/{ids['job'][ten]}").text
    assert 'role="progressbar"' not in html
    assert f"Dừng ở {pct}%" in html


def test_cau_huy_tu_nhien(web):
    c, _t, ids = web
    html = c.get(f"/jobs/{ids['job']['cancelled']}").text
    assert "credit giữ cho việc này được hoàn lại" not in html
    assert "Số credit tạm giữ cho việc này đã được hoàn về tài khoản." in html


def test_danh_sach_viec_khong_lap_so_du_va_an_thanh_viec_dung(web):
    c, _t, ids = web
    html = c.get("/jobs").text
    head = html.split('<div class="pagehead">', 1)[1].split("</div></div>", 1)[0]
    assert "credit" not in head, "số dư đã có ở thanh trên cùng"
    # Bảng + thẻ: mỗi việc không dừng một thanh ở mỗi bản; việc lỗi/hủy không có.
    assert html.count('role="progressbar"') == 2 * 3
    assert html.count("Dừng ở 30%") == 2 and html.count("Dừng ở 10%") == 2
    assert '<div class="job-filter-actions"><button class="btn" type="submit">' in html
    for ten in ('name="status"', 'name="app"', 'name="date_from"', 'name="date_to"',
                'action="/jobs"'):
        assert ten in html


def test_danh_sach_trong_chi_mot_nut_chinh(web):
    _c, trong, _ids = web
    html = trong.get("/jobs").text
    assert "Chưa có việc nào" in html
    assert '<button class="btn ghost" type="submit">' in html
    # Có lọc thì "Áp dụng" vẫn là nút chính.
    loc = trong.get("/jobs?status=error").text
    assert '<button class="btn" type="submit">' in loc

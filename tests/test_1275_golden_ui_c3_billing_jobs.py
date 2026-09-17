"""Golden UI C3 (17/09/2026) — họ Billing + Jobs, chốt theo khiếm khuyết người chấm ghi.

Billing
1. Đơn `expired`/`cancelled`/`failed` mỗi cái một badge, câu giải thích và nút —
   trước đây ba trang y hệt ("không hoàn tất hoặc đã hết hạn").
2. Hướng dẫn chuyển khoản, nút mở cổng và cảnh báo "cổng chưa cấu hình" chỉ khi
   đơn còn `pending`: đơn đã chết mà còn mời chuyển tiền là mời khách mất tiền.
3. `/nap` ở màn hẹp: lịch sử đơn có bản danh sách thẻ (bảng cắt cột trạng thái).
4. Khách vừa về từ cổng (`?ve=1` hoặc `status=PAID`) thấy "đang xác nhận", không
   thấy nút mở cổng lần nữa.
5. Thẻ gói không lặp "500 credit = 500 credit"; trang không in số dư lần hai.

Jobs
1. "Tệp kết quả bên dưới" chỉ khi trang có phần đó; thanh 100% mang màu thành công.
2. `/jobs` ở màn hẹp: thẻ thay bảng; bộ lọc gọn trong <details>.
3. Trang lỗi nêu lý do CÔNG KHAI (sự kiện cấp error), không in `job.error` thô;
   trang hủy có lời giải thích; lịch sử có mốc kết thúc.
4. Việc đang chạy chưa có sự kiện vẫn có "Lịch sử xử lý".
5. Danh sách nhận diện bằng thời điểm tạo đầy đủ (có năm), không chỉ mã hash.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[1]
CSS = (GOC / "server" / "static" / "ltt.css").read_text(encoding="utf-8")


@pytest.fixture()
def web(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    url = f"sqlite:///{(tmp_path / 'c3.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-golden-c3")
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
    u = tao_nguoi_dung(s, email="c3@x.com", password="matkhau-tot", is_verified=True)
    credit.nap(s, u.id, 1250)
    goi = [CreditPackage(name="Khoi dau", price_vnd=50_000, credits_base=500,
                         bonus_percent=0, sort_order=1),
           CreditPackage(name="Pho bien", price_vnd=200_000, credits_base=2000,
                         bonus_percent=10, sort_order=2)]
    s.add_all(goi); s.flush()
    now = datetime.now(timezone.utc)
    ids: dict = {"don": {}, "job": {}}
    for i, st in enumerate(("pending", "paid", "expired", "cancelled", "failed")):
        o = PaymentOrder(order_code=770_000 + i, user_id=u.id, package_id=goi[1].id,
                         price_vnd=200_000, credits=2200, bonus_percent=10, status=st,
                         credited=st == "paid", gateway="payos",
                         # Đơn đã chết VẪN mang link cổng: trang không được mời trả.
                         checkout_url="https://pay.example/c3",
                         created_at=now - timedelta(minutes=i),
                         expires_at=now + timedelta(minutes=20))
        s.add(o); s.flush()
        ids["don"][st] = o.id
    o = PaymentOrder(order_code=770_100, user_id=u.id, package_id=goi[1].id,
                     price_vnd=200_000, credits=2200, status="expired", gateway="payos",
                     checkout_url="")
    s.add(o); s.flush()
    ids["don"]["expired_khong_link"] = o.id

    def job(ten, status, pct, result=None, error="", events=(), **kw):
        j = Job(user_id=u.id, app_slug="taoanh", job_type="taoanh.generate",
                params={"prompt": "BI-MAT-PROMPT"}, status=status, progress=pct,
                result=result, error=error, **kw)
        s.add(j); s.flush()
        for seq, (code, lvl, text) in enumerate(events, start=1):
            s.add(JobEvent(job_id=j.id, user_id=u.id, app_slug="taoanh", sequence=seq,
                           event_code=code, level=lvl, public_message=text, details={}))
        ids["job"][ten] = j.id
        return j

    batdau = [("submitted", "info", "Đã tiếp nhận yêu cầu."), ("started", "info", "Bắt đầu xử lý.")]
    job("done", "done", 100, result={"credit": 1})
    job("done_tep", "done", 100, result={"image_key": "u/a.png"})
    job("error", "error", 30, error="Traceback RAW-INTERNAL-ERROR", events=batdau + [
        ("failed", "error", "Không thể hoàn tất yêu cầu. Bạn có thể thử lại.")])
    job("error_cu", "error", 30, error="RAW-INTERNAL-ERROR", events=batdau)
    job("cancelled", "cancelled", 10, events=batdau)
    job("running_rong", "running", 20, progress_msg="Đang tạo ảnh 1/4")
    s.commit(); s.close()

    from server.app import create_app
    c = TestClient(create_app(), base_url="https://testserver")
    tok = re.search(r'name="csrf_token" value="([^"]+)"', c.get("/login").text).group(1)
    r = c.post("/login", data={"username": "c3@x.com", "password": "matkhau-tot",
                               "csrf_token": tok}, follow_redirects=False)
    assert r.status_code == 303
    try:
        yield c, ids
    finally:
        dbmod.reset_engine()


# ── Billing ──────────────────────────────────────────────────────────────────

DUONG_CHET = {
    "expired": ("Đơn đã quá thời hạn thanh toán", "Đơn đã hết hạn thanh toán.", "Tạo đơn mới"),
    "cancelled": ("Đơn đã bị hủy nên không thể thanh toán tiếp.", "Đơn đã bị hủy.", "Tạo đơn mới"),
    "failed": ("Cổng thanh toán báo giao dịch không thành công", "Thanh toán không thành công.",
               "Thử lại với đơn mới"),
}


@pytest.mark.parametrize("st", sorted(DUONG_CHET))
def test_don_da_chet_moi_trang_thai_mot_loi_va_khong_moi_tra_tien(web, st):
    c, ids = web
    phu_de, tieu_de, nut = DUONG_CHET[st]
    html = c.get(f"/nap/don/{ids['don'][st]}").text
    assert f'data-trang-thai="{st}"' in html, "trang đơn phải có badge trạng thái"
    assert phu_de in html
    assert "Chuyển khoản đúng số tiền" not in html
    assert "Mở PayOS" not in html and "https://pay.example/c3" not in html
    # Các câu của trạng thái KHÁC không được lọt vào.
    for khac, (pd, _td, _n) in DUONG_CHET.items():
        if khac != st:
            assert pd not in html
    frag = c.get(f"/nap/don/{ids['don'][st]}/trangthai").text
    assert tieu_de in frag and nut in frag
    assert "Đơn không hoàn tất hoặc đã hết hạn" not in frag
    assert frag.count('<div id="tt"') == 1 and 'role="alert"' in frag
    assert "hx-trigger" not in frag, "đơn đã chết không poll nữa"


def test_don_het_han_khong_link_khong_hien_canh_bao_cong(web):
    c, ids = web
    html = c.get(f"/nap/don/{ids['don']['expired_khong_link']}").text
    assert "Cổng thanh toán chưa cấu hình" not in html
    assert "Hết hạn lúc" in html


def test_don_pending_van_huong_dan_va_mo_cong(web):
    c, ids = web
    html = c.get(f"/nap/don/{ids['don']['pending']}").text
    assert "Chuyển khoản đúng số tiền" in html and "Mở PayOS" in html
    assert 'data-trang-thai="pending"' in html


@pytest.mark.parametrize("qs", ["?ve=1", "?code=00&status=PAID&orderCode=770000"])
def test_vua_ve_tu_cong_noi_dang_xac_nhan_va_giau_nut_cong(web, qs):
    c, ids = web
    html = c.get(f"/nap/don/{ids['don']['pending']}{qs}").text
    assert "Đang xác nhận thanh toán" in html
    assert "không cần chuyển lại" in html
    assert "Mở PayOS" not in html
    assert f"/nap/don/{ids['don']['pending']}/trangthai?ve=1" in html


def test_ve_1_tren_don_da_tra_khong_noi_dang_xac_nhan(web):
    c, ids = web
    html = c.get(f"/nap/don/{ids['don']['paid']}?ve=1").text
    assert "Đang xác nhận thanh toán" not in html and "Đơn đã hoàn tất" in html


def test_huy_o_cong_chi_noi_con_hieu_luc_khi_don_con_pending(web):
    c, ids = web
    assert "Đơn vẫn còn hiệu lực" in c.get(f"/nap/don/{ids['don']['pending']}?cancel=true").text
    assert "Đơn vẫn còn hiệu lực" not in c.get(f"/nap/don/{ids['don']['cancelled']}?cancel=true").text


def test_trang_nap_khong_lap_credit_so_du_va_co_the_man_hep(web):
    c, ids = web
    html = c.get("/nap").text
    assert "= 500 credit" not in html, "gói không bonus không in '500 credit = 500 credit'"
    assert "= 2.200 credit" in html
    assert 'class="cover billing-cover"' not in html, "dải bìa 72px mỗi thẻ gói đã bỏ"
    main = html.split('class="pagehead billing-head"')[1].split("billing-history")[0]
    assert 'class="pill"' not in main, "số dư đã có ở thanh trên cùng"
    # Lịch sử: bảng + danh sách thẻ cùng dữ liệu.
    assert html.count('class="billing-history-item"') == 6
    assert 'class="tablewrap billing-history-table"' in html


def test_css_billing_man_hep_doi_bang_sang_the():
    khoi = CSS.split("/* === C3: BILLING-JOBS === */", 1)
    assert len(khoi) == 2, "khối CSS C3 phải có mặt"
    c3 = khoi[1]
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", c3), "khối C3 chỉ dùng token"
    hep = re.search(r"@media\(max-width:640px\)\{(.*?)\n\}", c3, flags=re.S).group(1)
    assert ".billing-history .billing-history-table" in hep and ".job-table" in hep
    assert "display:none" in hep and ".billing-history-list,.job-list{display:grid" in hep
    assert ".billing-history-list,.job-list{display:none" in c3
    assert ".job-state-done .ui-progress>i{background:var(--ok)}" in c3


# ── Jobs ─────────────────────────────────────────────────────────────────────

def test_viec_xong_khong_tep_khong_noi_tep_ket_qua(web):
    c, ids = web
    html = c.get(f"/jobs/{ids['job']['done']}").text
    assert "Tệp kết quả" not in html
    assert 'class="job-state-done"' in html
    assert "job vừa hoàn tất" not in html
    tep = c.get(f"/jobs/{ids['job']['done_tep']}").text
    assert "Tệp kết quả" in tep and "/artifacts/0" in tep


def test_viec_loi_neu_ly_do_cong_khai_khong_lo_loi_tho(web):
    c, ids = web
    html = c.get(f"/jobs/{ids['job']['error']}").text
    assert "Lý do:" in html and "Không thể hoàn tất yêu cầu. Bạn có thể thử lại." in html
    assert "RAW-INTERNAL-ERROR" not in html and "BI-MAT-PROMPT" not in html
    cu = c.get(f"/jobs/{ids['job']['error_cu']}").text
    assert "RAW-INTERNAL-ERROR" not in cu
    assert "Dừng do lỗi" in cu, "lịch sử phải có mốc kết thúc, không dừng ở 'Bắt đầu xử lý'"


def test_viec_huy_co_giai_thich_va_moc_huy(web):
    c, ids = web
    html = c.get(f"/jobs/{ids['job']['cancelled']}").text
    assert "Việc đã hủy." in html
    assert "Đã hủy theo yêu cầu." in html


def test_viec_dang_chay_chua_co_su_kien_van_co_lich_su(web):
    c, ids = web
    html = c.get(f"/jobs/{ids['job']['running_rong']}").text
    assert "Lịch sử xử lý" in html and "Đã tạo việc" in html
    frag = c.get(f"/jobs/{ids['job']['running_rong']}/progress").text
    assert "Lịch sử xử lý" in frag and 'data-running="true"' in frag


def test_danh_sach_viec_the_man_hep_bo_loc_gon_va_nhan_dien(web):
    c, ids = web
    html = c.get("/jobs").text
    assert re.search(r'<details class="job-filter-box" data-job-filter-box>', html), \
        "không lọc thì bộ lọc đóng sẵn (màn rộng mở bằng JS)"
    assert html.count('class="job-card job-state-') == len(ids["job"])
    nam = str(datetime.now(timezone.utc).year)
    assert re.search(r"\d\d:\d\d \d\d/\d\d/" + nam, html), "thời điểm tạo có đủ năm"
    assert "BI-MAT-PROMPT" not in html and "RAW-INTERNAL-ERROR" not in html
    loc = c.get("/jobs?status=error").text
    assert '<details class="job-filter-box" data-job-filter-box open>' in loc
    assert "1 đang áp dụng" in loc and "Xóa lọc" in loc
    # Hợp đồng form lọc giữ nguyên.
    for ten in ('name="status"', 'name="app"', 'name="date_from"', 'name="date_to"',
                'action="/jobs"'):
        assert ten in loc

r"""
golden_ui_dev.py — dựng nền tảng ở TRẠNG THÁI CÓ DỮ LIỆU cho chiến dịch Golden UI.

    python tools\golden_ui_dev.py --cong 8140          # seed + chay may chu
    python tools\golden_ui_dev.py --cong 8140 --cookie khach   # in cookie phien
    python tools\golden_ui_dev.py --cong 8140 --ids    # in id don/job da seed (JSON)

Cùng khuôn với `tools/studio_dev.py` (Voice), nhưng seed đủ **mọi state** của
các họ trang nền tảng để soi từng `màn × state` chứ không chỉ từng URL:

* 3 tài khoản: khách thường (có credit), admin, khách chưa xác thực email;
* 3 gói credit (có/không bonus);
* đơn nạp ở đủ 5 trạng thái + một đơn `pending` không có `checkout_url`;
* job ở đủ 5 trạng thái, một chuỗi retry, một job có artifact + timeline.

🔴 KHÔNG chạm CSDL thật và KHÔNG chạm kho thật. Mọi thứ nằm dưới
`tmp/golden_ui/`, một sqlite dùng một lần. Chạy lại là dựng lại từ đầu.

Đăng nhập đi bằng HTTP (`POST /login`) với tài khoản dùng một lần do chính tệp
này tạo — không mật khẩu thật nào của ai đi qua trình duyệt do máy điều khiển.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True)

THU_MUC = os.path.join(ROOT, "tmp", "golden_ui")
CSDL = os.path.join(THU_MUC, "golden.db")
KHO = os.path.join(THU_MUC, "kho")
IDS = os.path.join(THU_MUC, "ids.json")
MAT_KHAU = "khong-phai-mat-khau-that-12"
TAI_KHOAN = {
    "khach": "golden-khach@test.local",
    "admin": "golden-admin@test.local",
    "chua_xac_thuc": "golden-moi@test.local",
}
CONG_MAC_DINH = 8140


def _dat_moi_truong() -> None:
    os.environ["LTT_DATABASE_URL"] = "sqlite:///" + CSDL.replace("\\", "/")
    os.environ["LTT_ENV"] = "development"
    os.environ.setdefault("LTT_SESSION_SECRET", "golden-ui-dev-khong-bi-mat")
    os.environ.pop("TURNSTILE_SECRET_KEY", None)
    os.environ.setdefault("LTT_VOICE_SIDECAR_TOKEN", "golden-ui-token-gia")
    # Bật các bề mặt sau cờ để SOI được giao diện của chúng. Cây này không có
    # `secrets/` ⇒ không có khoá hạ tầng nào; lời gọi thật sẽ rơi vào nhánh
    # "hạ tầng lỗi" — đó cũng là một state cần soi.
    for co in ("LTT_VPS", "LTT_NEXUS", "LTT_AUTO_SCAN_VIDEO"):
        os.environ.setdefault(co, "1")


def seed() -> dict:
    if os.path.isdir(THU_MUC):
        shutil.rmtree(THU_MUC, ignore_errors=True)
    os.makedirs(THU_MUC, exist_ok=True)
    _dat_moi_truong()

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core import registry
    registry.load_app_tables()
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core.storage import LocalStorage, set_storage
    set_storage(LocalStorage(KHO))

    from platform_core import credit
    from platform_core.models import CreditPackage, Job, JobEvent, PaymentOrder
    from platform_core.users import tao_nguoi_dung

    gen = dbmod.get_session()
    db = next(gen)
    ids: dict = {"orders": {}, "jobs": {}}
    try:
        khach = tao_nguoi_dung(db, email=TAI_KHOAN["khach"], password=MAT_KHAU,
                               display_name="Khách Golden", is_verified=True)
        tao_nguoi_dung(db, email=TAI_KHOAN["admin"], password=MAT_KHAU,
                       display_name="Admin Golden", role="admin",
                       is_verified=True)
        tao_nguoi_dung(db, email=TAI_KHOAN["chua_xac_thuc"], password=MAT_KHAU,
                       is_verified=False)
        uid = str(khach.id)
        ids["khach_id"] = uid
        credit.nap(db, uid, 1250, note="golden-ui seed")

        goi = [
            CreditPackage(name="Khởi đầu", price_vnd=50_000, credits_base=500,
                          bonus_percent=0, sort_order=1),
            CreditPackage(name="Phổ biến", price_vnd=200_000, credits_base=2000,
                          bonus_percent=10, sort_order=2),
            CreditPackage(name="Chuyên nghiệp", price_vnd=1_000_000,
                          credits_base=10_000, bonus_percent=25, sort_order=3),
        ]
        db.add_all(goi)
        db.flush()

        bay_gio = datetime.now(timezone.utc)
        mau_don = [
            ("pending", "https://pay.payos.vn/web/golden-demo"),
            ("pending_khong_link", ""),
            ("paid", ""),
            ("expired", ""),
            ("cancelled", ""),
            ("failed", ""),
        ]
        for i, (ten, link) in enumerate(mau_don):
            status = "pending" if ten.startswith("pending") else ten
            o = PaymentOrder(
                order_code=880_000 + i, user_id=uid, package_id=goi[1].id,
                price_vnd=200_000, credits=2200, bonus_percent=10,
                status=status, credited=(status == "paid"), gateway="payos",
                gateway_ref=("FT26259GOLDEN" if status == "paid" else ""),
                checkout_url=link,
                created_at=bay_gio - timedelta(minutes=5 + i * 40),
                paid_at=(bay_gio - timedelta(minutes=3) if status == "paid" else None),
                expires_at=bay_gio + timedelta(minutes=25),
            )
            db.add(o)
            db.flush()
            ids["orders"][ten] = o.id

        app = "taoanh"
        mau_job = [
            ("queued", 0, ""),
            ("running", 45, "Đang tạo ảnh 2/4"),
            ("done", 100, ""),
            ("error", 30, ""),
            ("cancelled", 10, ""),
        ]
        for ten, pct, msg in mau_job:
            j = Job(
                user_id=uid, app_slug=app, job_type="taoanh.generate",
                params={"prompt": "Một chú mèo phi hành gia, ánh sáng điện ảnh"},
                status=ten, progress=pct, progress_msg=msg,
                result=({"images": ["/static/favicon.ico"], "credit": 12}
                        if ten == "done" else None),
                error=("Nhà cung cấp từ chối yêu cầu (nội dung không hợp lệ)."
                       if ten == "error" else ""),
                created_at=bay_gio - timedelta(minutes=len(ids["jobs"]) * 7),
            )
            db.add(j)
            db.flush()
            ids["jobs"][ten] = j.id
            for seq, (code, lvl, text) in enumerate([
                ("job.queued", "info", "Đã xếp hàng"),
                ("job.started", "info", "Bắt đầu xử lý"),
            ][: (1 if ten == "queued" else 2)], start=1):
                db.add(JobEvent(job_id=j.id, user_id=uid, app_slug=app,
                                sequence=seq, event_code=code, level=lvl,
                                public_message=text,
                                details={"percent": pct} if seq == 2 else {}))

        # chuỗi retry: một job lỗi sinh một job thử lại đang chạy
        con = Job(user_id=uid, app_slug=app, job_type="taoanh.generate",
                  params={"prompt": "thử lại"}, status="running", progress=20,
                  retry_of_id=ids["jobs"]["error"])
        db.add(con)
        db.flush()
        ids["jobs"]["retry_child"] = con.id
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    with open(IDS, "w", encoding="utf-8") as f:
        json.dump(ids, f, ensure_ascii=False, indent=2)
    print(f"  [OK] seed xong: {THU_MUC}")
    return ids


def lay_cookie(cong: int, vai: str) -> str:
    """Đăng nhập bằng HTTP rồi trả cookie phiên. Không đi qua ô mật khẩu nào."""
    import re
    import urllib.error
    import urllib.parse
    import urllib.request

    goc = f"http://127.0.0.1:{cong}"
    bo = urllib.request.HTTPCookieProcessor()
    mo = urllib.request.build_opener(bo)
    with mo.open(f"{goc}/login", timeout=30) as r:
        html = r.read().decode("utf-8", "replace")
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    if not m:
        raise SystemExit("khong lay duoc csrf_token — may chu da chay chua?")
    du_lieu = urllib.parse.urlencode({
        "username": TAI_KHOAN[vai], "password": MAT_KHAU,
        "csrf_token": m.group(1)}).encode()
    try:
        mo.open(urllib.request.Request(f"{goc}/login", data=du_lieu), timeout=30)
    except urllib.error.HTTPError as e:
        if e.code not in (302, 303):
            raise
    for c in bo.cookiejar:
        if "session" in c.name.lower():
            return f"{c.name}={c.value}"
    raise SystemExit(f"khong thay cookie phien; co: {[c.name for c in bo.cookiejar]}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cong", type=int, default=CONG_MAC_DINH)
    ap.add_argument("--cookie", choices=sorted(TAI_KHOAN),
                    help="in cookie phien roi thoat (may chu phai dang chay)")
    ap.add_argument("--ids", action="store_true", help="in id da seed")
    a = ap.parse_args(argv)

    if a.cookie:
        print(lay_cookie(a.cong, a.cookie))
        return 0
    if a.ids:
        with open(IDS, encoding="utf-8") as f:
            print(f.read())
        return 0

    seed()
    _dat_moi_truong()
    import uvicorn
    print(f"  Golden UI dev: http://127.0.0.1:{a.cong}/")
    uvicorn.run("server.app:create_app", factory=True, host="127.0.0.1",
                port=a.cong, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

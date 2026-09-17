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

from typing import Any

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
        ids["vps"] = _seed_vps(db, uid, bay_gio)
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


def _seed_vps(db, uid: str, bay_gio: datetime) -> dict:
    """Chèn máy VPS ở nhiều trạng thái cho khách — CHỈ ghi hàng CSDL.

    Không gọi provider/Proxmox/Vultr nào: máy không ghim hồ sơ hạ tầng
    (`profile_resolution_state` mặc định `NEEDS_REVIEW`) nên mọi đường điều
    khiển thật từ chối trước khi chạm mạng.
    """
    from apps.vps.tables import VpsEvent, VpsInstance, VpsIp

    gw = "golden-gw"
    mau: list[tuple[str, dict[str, Any], str]] = [
        ("chay", dict(ten="web-ban-hang", plan_id="vps-vua",
                      os_id="winsrv2022-gui", trang_thai="dang_chay",
                      vmid=9201, ip_noi_bo="10.51.0.50",
                      paid_until=bay_gio + timedelta(days=21),
                      bang_thong_byte=180 * 1024 ** 3,
                      sao_luu_luc=bay_gio - timedelta(hours=9),
                      quan_sat_luc=bay_gio - timedelta(minutes=2)),
         "203.0.113.10"),
        ("tat", dict(ten="may-thu-nghiem", plan_id="vps-nho", os_id="win10",
                     trang_thai="da_tat", vmid=9202, ip_noi_bo="10.51.0.51",
                     paid_until=bay_gio + timedelta(days=2),
                     bang_thong_byte=3 * 1024 ** 3,
                     quan_sat_luc=bay_gio - timedelta(minutes=4)),
         "203.0.113.11"),
        ("tao", dict(ten="may-moi-tao", plan_id="vps-nho",
                     os_id="winsrv2016-core", trang_thai="dang_tao"), ""),
        ("loi", dict(ten="may-bi-loi", plan_id="vps-lon",
                     os_id="winsrv2022-core", trang_thai="loi",
                     ly_do="Không tạo được máy trên máy chủ. Credit đã được hoàn lại.",
                     paid_until=bay_gio + timedelta(days=29)), ""),
    ]
    ids: dict = {}
    for i, (khoa, cot, ip) in enumerate(mau):
        m = VpsInstance(user_id=uid, gateway_id=gw,
                        created_at=bay_gio - timedelta(days=10 - i), **cot)
        db.add(m)
        db.flush()
        ids[khoa] = m.id
        if ip:
            db.add(VpsIp(gateway_id=gw, dia_chi=ip, state="BOUND",
                         instance_id=m.id, nhan="golden"))
        su_kien = [("tao_moi", {"plan_id": cot["plan_id"], "os_id": cot["os_id"]}, 10)]
        if khoa in ("chay", "tat"):
            su_kien += [
                ("tao_xong", {}, 9),
                ("thu_phi", {"credit": 900, "den": (bay_gio + timedelta(days=21)).isoformat()}, 9),
                ("doi_ten", {"cu": "vps-3f9a", "moi": cot["ten"]}, 5),
                ("sao_luu", {}, 1),
            ]
        if khoa == "tat":
            su_kien += [("xin_tat", {}, 0), ("tat", {}, 0)]
        if khoa == "loi":
            su_kien += [("loi", {"ma_loi": "tac_vu_that_bai"}, 9),
                        ("hoan_tien", {"credit": 2400}, 9)]
        for loai, ct, ngay in su_kien:
            db.add(VpsEvent(instance_id=m.id, loai=loai, boi=uid, chi_tiet=ct,
                            created_at=bay_gio - timedelta(days=ngay, minutes=len(loai))))
    db.flush()
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

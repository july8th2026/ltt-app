"""
tai_khoan_thu.py — tài khoản THỬ dùng chung để kiểm giao diện/API thật trên production.

Hướng dẫn đầy đủ: `docs/TAI_KHOAN_THU.md`. Tóm tắt (chạy bằng venv production):

    set PY=C:\\LTTPlatform\\venv\\Scripts\\python.exe
    set ENV=--app-env C:\\LTTPlatform\\secrets\\app.env

    %PY% tools\\tai_khoan_thu.py %ENV% --liet-ke            # xem bộ tài khoản + số dư
    %PY% tools\\tai_khoan_thu.py %ENV% --tao-bo             # đảm bảo 3 tài khoản chung + credit
    %PY% tools\\tai_khoan_thu.py %ENV% --cookie khach1.thu@lttstudios.local
                                                        # in `session=...` cho Playwright

⭐ VÌ SAO CẦN MỘT CÔNG CỤ, KHÔNG PHẢI MỘT LẦN GÕ TAY

   Luật dự án bắt kiểm giao diện bằng trình duyệt thật và chốt trên **URL công
   khai**. Cả hai đòi một phiên đăng nhập. Không có đường tạo tài khoản thử thì
   phép kiểm đó hoặc bị bỏ, hoặc phải mượn tài khoản thật của khách.

⭐ BỘ DÙNG CHUNG (chủ dự án chốt 16/09/2026)

   Ba tài khoản `khach{1,2,3}.thu@lttstudios.local` có sẵn cho MỌI phiên. Mật khẩu
   sinh ngẫu nhiên và chỉ nằm ở `<secrets_dir>\\tai_khoan_thu.json` trên máy chủ
   (ACL của `secrets\\`) — không trong kho git, không in ra màn hình. Phiên cần đăng
   nhập thì gọi `--cookie`: công cụ tự đăng nhập bằng HTTP và chỉ trả cookie phiên,
   nên không ai phải thấy hay gõ mật khẩu vào form.

   Chủ dự án cho phép cấp credit thoải mái cho tài khoản thử để chạy các hạng mục
   test. Credit đi bằng bút toán `grant` (`credit.cap_tay`), ghi rõ "tài khoản thử",
   nên không lẫn vào doanh thu nạp tiền của khách.

⛔ BA ĐIỀU CÔNG CỤ NÀY VẪN KHÔNG LÀM:

   1. **Không đụng tài khoản thật.** Mọi thao tác ghi chỉ nhận email đuôi `.local`.
   2. **Không đặt `role=admin`.** Mục đích là kiểm **bề mặt khách hàng**.
   3. **Không in mật khẩu** khi đã lưu vào kho (`--luu`, `--tao-bo`). Chế độ cũ
      (không `--luu`) vẫn hiện mật khẩu đúng một lần.
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import string
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: Nhận ra tài khoản thử bằng ĐUÔI EMAIL, không bằng một danh sách gõ tay.
DUOI_THU = ".local"
EMAIL_MAC_DINH = "thu.giongnoi@lttstudios.local"

#: Bộ dùng chung cho mọi phiên (16/09/2026).
BO_CHUNG = (
    ("khach1.thu@lttstudios.local", "Khach thu 1 (dung chung)"),
    ("khach2.thu@lttstudios.local", "Khach thu 2 (dung chung)"),
    ("khach3.thu@lttstudios.local", "Khach thu 3 (dung chung)"),
)
#: Mức credit `--tao-bo` nạp bù tới (không trừ bớt nếu đang cao hơn).
CREDIT_SAN = 5000
TEN_TEP_KHO = "tai_khoan_thu.json"
GOC_MAC_DINH = "http://127.0.0.1:8100"


def _mat_khau_manh(n: int = 24) -> str:
    bang = string.ascii_letters + string.digits
    return "".join(secrets.choice(bang) for _ in range(n))


def nap_env(duong: str) -> None:
    """Chỉ ĐẶT khoá chưa có — biến đã đặt trong phiên thắng tệp. Không in giá trị."""
    if not duong or not os.path.isfile(duong):
        return
    with open(duong, encoding="utf-8-sig") as fh:
        for dong in fh:
            t = dong.strip()
            if t and not t.startswith("#") and "=" in t:
                k, v = t.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def duong_kho(env: dict | None = None) -> str:
    from platform_core.runtime_paths import resolve_runtime_paths
    return os.path.join(resolve_runtime_paths(env).secrets_dir, TEN_TEP_KHO)


def doc_kho(duong: str) -> dict:
    if not os.path.isfile(duong):
        return {}
    with open(duong, encoding="utf-8-sig") as fh:
        d = json.load(fh)
    return d if isinstance(d, dict) else {}


def ghi_kho(duong: str, kho: dict) -> None:
    """Ghi nguyên tử, UTF-8 KHÔNG BOM (luật cấu hình của dự án)."""
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tmp"
    with open(tam, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(kho, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tam, duong)


def la_email_thu(email: str) -> bool:
    return (email or "").strip().lower().endswith(DUOI_THU)


def lay_cookie(email: str, mat_khau: str, goc: str = GOC_MAC_DINH) -> str:
    """Đăng nhập bằng HTTP như một trình duyệt; trả giá trị cookie `session`.

    Không đi qua ô mật khẩu nào trên giao diện, và không lách Turnstile: thử thách
    chỉ bật sau nhiều lần sai, và một lượt đúng không chạm nó."""
    import re
    import urllib.error
    import urllib.parse
    import urllib.request

    # 🔴 16/09/2026: cookie `session` của production mang cờ `Secure`. Một
    #    `CookieJar` KHÔNG gửi nó lại qua `http://127.0.0.1` ⇒ POST /login thiếu phiên
    #    ⇒ CSRF hỏng ⇒ 400. Nên tự mang cookie bằng header, và đọc `Set-Cookie` ngay
    #    ở phản hồi 303 thay vì đi theo chuyển hướng. (URL công khai thì Cloudflare
    #    chặn urllib 403 — đi loopback.)
    class _KhongChuyenHuong(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None

    def _phien(tieu_de) -> str:
        for sc in tieu_de.get_all("Set-Cookie") or []:
            mm = re.match(r"\s*session=([^;]*)", sc)
            if mm:
                return mm.group(1)
        return ""

    mo = urllib.request.build_opener(_KhongChuyenHuong())
    goc = goc.rstrip("/")
    with mo.open(f"{goc}/login", timeout=20) as r:
        html = r.read().decode("utf-8", "replace")
        an_danh = _phien(r.headers)
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    if not m or not an_danh:
        raise RuntimeError("khong lay duoc csrf_token/phien tu /login")
    du_lieu = urllib.parse.urlencode({
        "username": email, "password": mat_khau,
        "csrf_token": m.group(1), "next": ""}).encode()
    req = urllib.request.Request(f"{goc}/login", data=du_lieu,
                                 headers={"Cookie": f"session={an_danh}"})
    try:
        with mo.open(req, timeout=20) as r:
            ma, tieu_de = r.status, r.headers
    except urllib.error.HTTPError as e:
        ma, tieu_de = e.code, e.headers
    phien = _phien(tieu_de) if tieu_de is not None else ""
    # Chỉ 3xx là đăng nhập xong. 200/4xx nghĩa là form được trả lại (sai mật khẩu,
    # hết phiên) — cookie lúc ấy là phiên ẩn danh, không phải phiên đã đăng nhập.
    if 300 <= ma < 400 and phien:
        return phien
    raise RuntimeError(f"dang nhap that bai (HTTP {ma}) cho {email}")


def _nap_den(db, u, muc: int, by: str) -> tuple[int, int]:
    from platform_core import credit
    truoc = credit.so_du(db, u.id)
    if truoc < muc:
        credit.cap_tay(db, u.id, muc - truoc, by=by,
                       note=f"TAI KHOAN THU {u.email} - nap bu toi {muc} de chay test. "
                            "KHONG phai khoan nap cua khach.")
        db.commit()
    return truoc, credit.so_du(db, u.id)


def _dam_bao(db, email: str, ten: str, kho: dict, *, dat_lai: bool) -> tuple:
    """Tạo nếu chưa có; đặt lại mật khẩu nếu được yêu cầu HOẶC kho chưa có mật khẩu.
    Trả (user, mat_khau_moi | None, hanh_dong)."""
    from platform_core import users

    u = users.tim_theo_email(db, email)
    if u is None:
        mk = _mat_khau_manh()
        u = users.tao_nguoi_dung(
            db, email=email, password=mk, display_name=ten, role="user",
            is_verified=True, registration_ip="127.0.0.1")
        db.commit()
        return u, mk, "tao"
    if dat_lai or email not in kho:
        mk = _mat_khau_manh()
        users.doi_mat_khau(db, u, mk)
        users.thu_hoi_moi_phien(db, u.id)
        db.commit()
        return u, mk, "dat_lai"
    return u, None, "co_san"


def _luu(kho: dict, email: str, mk: str, ten: str) -> None:
    kho[email] = {"mat_khau": mk, "ten": ten,
                  "cap_nhat": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Tai khoan thu dung chung (.local).")
    ap.add_argument("--app-env", default="",
                    help="nap bien LTT_* tu tep env (vd C:\\LTTPlatform\\secrets\\app.env)")
    ap.add_argument("--email", default=EMAIL_MAC_DINH)
    ap.add_argument("--ten", default="Tai khoan thu (LTT VOICE)")
    ap.add_argument("--dat-lai-mat-khau", action="store_true",
                    help="Tai khoan da co thi dat lai mat khau va thu hoi phien cu.")
    ap.add_argument("--luu", action="store_true",
                    help="Luu mat khau vao kho secrets thay vi in ra.")
    ap.add_argument("--liet-ke", action="store_true",
                    help="Chi liet ke tai khoan thu + so du + co trong kho khong.")
    ap.add_argument("--tao-bo", action="store_true",
                    help=f"Dam bao {len(BO_CHUNG)} tai khoan dung chung, luu kho, nap bu credit.")
    ap.add_argument("--nap", type=int, default=0, metavar="N",
                    help="Cap them N credit (grant) cho tai khoan --email (.local).")
    ap.add_argument("--nap-den", type=int, default=None, metavar="N",
                    help=f"Nap bu toi N credit (mac dinh voi --tao-bo: {CREDIT_SAN}).")
    ap.add_argument("--cookie", metavar="EMAIL",
                    help="Dang nhap bang HTTP va in `session=...` (khong in mat khau).")
    ap.add_argument("--goc", default=GOC_MAC_DINH,
                    help="Goc may chu de dang nhap cho --cookie.")
    a = ap.parse_args(argv)

    nap_env(a.app_env)
    kho_duong = duong_kho()

    # ── cookie: không cần CSDL ───────────────────────────────────────────────
    if a.cookie:
        kho = doc_kho(kho_duong)
        muc = kho.get(a.cookie.strip().lower())
        if not muc:
            print(f"TU CHOI: {a.cookie} khong co trong kho {kho_duong}. "
                  "Chay --tao-bo (hoac --email X --dat-lai-mat-khau --luu).", file=sys.stderr)
            return 2
        try:
            print("session=" + lay_cookie(a.cookie.strip().lower(), muc["mat_khau"], a.goc))
        except (OSError, RuntimeError) as e:
            print(f"LOI: {type(e).__name__}: {e}", file=sys.stderr)
            return 1
        return 0

    from sqlalchemy import select

    from platform_core.db import get_session
    from platform_core.models import User

    gen = get_session()
    db = next(gen)
    try:
        kho = doc_kho(kho_duong)
        by = "tools/tai_khoan_thu.py"

        # ── liệt kê: chỉ tài khoản đuôi thử, không bao giờ in email khách ──────
        from platform_core import credit
        co = list(db.execute(select(User).where(User.email.like(f"%{DUOI_THU}"))).scalars())
        print(f"Tai khoan thu dang co ({len(co)}) — kho: {kho_duong}")
        for u in co:
            print(f"  {u.email:40} role={u.role:5} active={getattr(u, 'is_active', '?')!s:5} "
                  f"credit={credit.so_du(db, u.id):>7}  kho={'CO' if u.email in kho else '-'}")
        if a.liet_ke:
            return 0

        # ── bộ dùng chung ────────────────────────────────────────────────────
        if a.tao_bo:
            muc = CREDIT_SAN if a.nap_den is None else a.nap_den
            doi = False
            print("")
            for email, ten in BO_CHUNG:
                u, mk, hd = _dam_bao(db, email, ten, kho, dat_lai=a.dat_lai_mat_khau)
                if mk:
                    _luu(kho, email, mk, ten)
                    doi = True
                truoc, sau = _nap_den(db, u, muc, by)
                print(f"  {email:40} {hd:8} credit {truoc} -> {sau}")
            if doi:
                ghi_kho(kho_duong, kho)
            print(f"\nXONG. Mat khau o {kho_duong} (khong in ra). Lay cookie: --cookie <email>")
            return 0

        # ── một tài khoản ────────────────────────────────────────────────────
        if not la_email_thu(a.email):
            print(f"\nTU CHOI: email thu phai ket thuc bang '{DUOI_THU}'.", file=sys.stderr)
            return 2
        u, mk, hd = _dam_bao(db, a.email, a.ten, kho if a.luu else {a.email: 1},
                             dat_lai=a.dat_lai_mat_khau)
        print(f"\n{hd.upper()}: {u.email}")
        if mk:
            if a.luu:
                _luu(kho, a.email, mk, a.ten)
                ghi_kho(kho_duong, kho)
                print(f"  mat khau da luu vao {kho_duong} (khong in ra)")
            else:
                print("\n" + "=" * 62)
                print("  MAT KHAU (hien DUNG MOT LAN, khong ghi xuong dau ca):")
                print(f"    {mk}")
                print("=" * 62)
        if a.nap > 0:
            credit.cap_tay(db, u.id, a.nap, by=by,
                           note=f"TAI KHOAN THU {u.email} - cap {a.nap} de chay test. "
                                "KHONG phai khoan nap cua khach.")
            db.commit()
        if a.nap_den is not None:
            _nap_den(db, u, a.nap_den, by)
        print(f"So du: {credit.so_du(db, u.id)} credit")
        return 0
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


if __name__ == "__main__":
    raise SystemExit(main())

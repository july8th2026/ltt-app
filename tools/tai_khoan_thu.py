"""
tai_khoan_thu.py — tìm hoặc tạo một tài khoản THỬ để kiểm giao diện thật.

    C:\\LTTPlatform\\venv\\Scripts\\python.exe tools\\tai_khoan_thu.py
    ... --email thu.gionoi@lttstudios.local --dat-lai-mat-khau

Chạy qua `setup\\tai_khoan_thu.ps1` để có sẵn biến môi trường của production.

⭐ VÌ SAO CẦN MỘT CÔNG CỤ, KHÔNG PHẢI MỘT LẦN GÕ TAY

   `CLAUDE.md` quy tắc 5 bắt kiểm giao diện bằng trình duyệt thật sau mỗi thay
   đổi, và quy tắc 5b bắt kiểm trên **URL công khai**. Cả hai đòi một phiên đăng
   nhập. Không có đường tạo tài khoản thử thì phép kiểm đó hoặc bị bỏ, hoặc phải
   mượn tài khoản thật của khách — và mượn tài khoản khách để thử một tính năng
   mới là cách nhanh nhất để một lượt thử thành một dòng trong lịch sử của họ.

⛔ BA ĐIỀU CÔNG CỤ NÀY KHÔNG LÀM, VÀ CHÚNG LÀ CÓ CHỦ Ý:

   1. **Không cấp credit.** Nạp credit là một bút toán trong sổ tiền, và sổ tiền
      chỉ ghi thêm — không xoá được. Một tài khoản thử có credit tự cấp sẽ nằm
      trong mọi báo cáo doanh thu về sau như một khoản không ai giải thích được.
      Muốn chạy job trả phí thì **chủ sản phẩm nạp**, qua đúng đường đã có.

   2. **Không đặt `role=admin`.** Mục đích là kiểm **bề mặt khách hàng**. Một tài
      khoản admin nhìn thấy thứ khách không thấy, nên nó chứng minh sai thứ.

   3. **Không in mật khẩu ra log.** Nó chỉ hiện trên màn hình đúng một lần.

⚠️ Tên miền mặc định là `.local` — không phải một hộp thư có thật. Đó là chủ ý:
   tài khoản thử không được nhận thư thật, và một địa chỉ không tồn tại làm cho
   điều đó chắc chắn thay vì trông chờ vào việc không ai bấm gửi.
"""
from __future__ import annotations

import argparse
import os
import secrets
import string
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#: Nhận ra tài khoản thử bằng ĐUÔI EMAIL, không bằng một danh sách gõ tay. Danh
#: sách thì trôi; một quy ước thì tự khai.
DUOI_THU = ".local"
EMAIL_MAC_DINH = "thu.giongnoi@lttstudios.local"


def _mat_khau_manh(n: int = 20) -> str:
    bang = string.ascii_letters + string.digits
    return "".join(secrets.choice(bang) for _ in range(n))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", default=EMAIL_MAC_DINH)
    ap.add_argument("--ten", default="Tai khoan thu (LTT VOICE)")
    ap.add_argument("--dat-lai-mat-khau", action="store_true",
                    help="Tai khoan da co thi dat lai mat khau va thu hoi phien cu.")
    ap.add_argument("--liet-ke", action="store_true",
                    help="Chi liet ke tai khoan thu dang co, khong tao gi.")
    # ⛔ Mặc định 0, và **chỉ** nhận cho email đuôi `.local` (kiểm lại ở chỗ dùng).
    #    Đây là ngoại lệ có chủ ý với điều 1 ở đầu tệp: một lượt chạy thử
    #    đầu-tới-cuối phải trả phí thật thì mới chứng minh được sổ tiền, nhưng
    #    bút toán sinh ra mang ghi chú tự khai để một tháng sau còn truy được.
    ap.add_argument("--nap", type=int, default=0, metavar="N",
                    help="Nap N credit cho tai khoan THU (.local). Mac dinh 0.")
    a = ap.parse_args(argv)

    from sqlalchemy import select

    from platform_core import users
    from platform_core.db import get_session
    from platform_core.models import User

    gen = get_session()
    db = next(gen)
    try:
        # ── liệt kê ──────────────────────────────────────────────────────────
        # Chỉ lọc theo đuôi thử: KHÔNG liệt kê tài khoản khách thật. Một công cụ
        # tiện tay in ra toàn bộ email khách là một công cụ rò rỉ.
        co = list(db.execute(
            select(User).where(User.email.like(f"%{DUOI_THU}"))
        ).scalars())
        print(f"Tai khoan thu dang co ({len(co)}):")
        for u in co:
            print(f"  {u.email:44} role={u.role:6} verified={u.is_verified} "
                  f"active={getattr(u, 'is_active', '?')}")
        if a.liet_ke:
            return 0

        if not a.email.endswith(DUOI_THU):
            print(f"\nTU CHOI: email thu phai ket thuc bang '{DUOI_THU}'.\n"
                  "Do la thu giu cho mot tai khoan thu khong bao gio bi nham voi\n"
                  "tai khoan khach, va giu cho no khong nhan duoc thu that.",
                  file=sys.stderr)
            return 2

        u = users.tim_theo_email(db, a.email)
        mk = None

        if u is None:
            mk = _mat_khau_manh()
            u = users.tao_nguoi_dung(
                db, email=a.email, password=mk, display_name=a.ten,
                role="user",          # KHONG admin: can kiem be mat KHACH HANG
                is_verified=True,     # bo qua buoc gui thu — .local khong co that
                registration_ip="127.0.0.1")
            db.commit()
            print(f"\nDA TAO: {u.email}")
        elif a.dat_lai_mat_khau:
            mk = _mat_khau_manh()
            users.doi_mat_khau(db, u, mk)
            users.thu_hoi_moi_phien(db, u.id)
            db.commit()
            print(f"\nDA DAT LAI MAT KHAU: {u.email} (moi phien cu da bi thu hoi)")
        else:
            print(f"\nDA CO: {u.email} — them `--dat-lai-mat-khau` neu can mat khau moi.")

        if mk:
            print("\n" + "=" * 62)
            print("  MAT KHAU (hien DUNG MOT LAN, khong ghi xuong dau ca):")
            print(f"    {mk}")
            print("=" * 62)

        # ── số dư: nói ra, không tự sửa ──────────────────────────────────────
        #
        # ⛔ BẮT HẸP, KHÔNG BẮT `Exception`. Đây là chỗ **báo một con số**, và bắt
        #    rộng ở đó biến một lỗi lập trình thật (đổi chữ ký `so_du`, sai kiểu
        #    `user_id`) thành dòng chữ "không đọc được số dư" — một câu trả lời
        #    trông như đã xử lý xong, và người đọc sẽ đi tìm ở phía CSDL.
        #
        #    Thứ thật sự có thể hỏng ở đây mà **không phải lỗi của bước này** chỉ
        #    có hai: CSDL trục trặc, hoặc module credit chưa có mặt. Bắt đúng hai
        #    thứ đó; mọi thứ khác phải nổ ra.
        from sqlalchemy.exc import SQLAlchemyError
        try:
            from platform_core import credit
            so_du = credit.so_du(db, u.id)
        except (ImportError, SQLAlchemyError) as e:
            print(f"  (khong doc duoc so du: {type(e).__name__}: {e})",
                  file=sys.stderr)
            so_du = None

        # ── nạp, CHỈ khi được yêu cầu rõ ────────────────────────────────────
        if a.nap > 0:
            if not u.email.endswith(DUOI_THU):
                print("TU CHOI nap cho tai khoan khong phai `.local`.",
                      file=sys.stderr)
                return 2
            from platform_core import credit as _credit
            ghi_chu = (f"LUOT CHAY THU - tai khoan thu {u.email}, nap boi "
                       f"tools/tai_khoan_thu.py. KHONG phai khoan nap cua khach.")
            _credit.nap(db, u.id, a.nap, note=ghi_chu)
            db.commit()
            so_du = _credit.so_du(db, u.id)
            print("")
            print(f"DA NAP {a.nap} credit (but toan co ghi chu truy duoc).")

        if so_du is not None:
            print(f"\nSo du: {so_du} credit")
            if so_du <= 0:
                print("  ⚠️  Tai khoan nay KHONG chay duoc job tra phi.")
                print("      Cong cu nay CO Y khong nap credit: nap credit la mot but")
                print("      toan trong so tien, va so tien chi ghi them. Mot khoan tu")
                print("      cap se nam trong moi bao cao doanh thu ve sau nhu mot muc")
                print("      khong ai giai thich duoc.")
                print("      Muon chay job tra phi: chu san pham nap qua duong da co.")
        return 0
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


if __name__ == "__main__":
    raise SystemExit(main())

r"""
nap_credit_tai_khoan_thu.py — nạp credit cho một tài khoản THỬ (`.local`).

    powershell -ExecutionPolicy Bypass -File .\setup\nap_credit_tai_khoan_thu.ps1 `
        -Email thu.giongnoi@lttstudios.local -So 100 -GhiChu "nhap kho giong cu"

## ⛔ ĐÂY LÀ MỘT BÚT TOÁN TIỀN, VÀ NÓ KHÔNG XOÁ ĐƯỢC

Sổ credit là **append-only** — đó là cả thiết kế của nó, để mọi con số đều truy
được về một dòng bút toán. Hệ quả: một lần nạp nhầm thì **ở lại vĩnh viễn**, và
cách "sửa" duy nhất là ghi thêm một bút toán ngược, tức hai dòng sai thay vì
không dòng nào.

Nên tệp này có hai cái chốt, và cả hai đều cố ý gắt:

  ① **Chỉ tài khoản đuôi `.local`.** Nạp cho một khách thật là cho không tiền,
     và nó không đảo được.
  ② **Trần mỗi lượt.** Một con số gõ thừa số 0 là một trăm nghìn credit trong
     sổ, và không ai đọc lại dòng đó cho tới khi đối soát doanh thu.

⚠️ Công cụ này KHÔNG phải một cửa nạp tiền. Cửa nạp tiền của khách đi qua PayOS
   + webhook idempotent (`platform_core/thanh_toan/`). Đây là một lối tắt cho
   tài khoản thử, và nó phải trông đúng như một lối tắt.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    # ⛔ `reconfigure`, KHÔNG phải `io.TextIOWrapper(sys.stdout.buffer, ...)`.
    #    Một wrapper mới NHẬN QUYỀN SỞ HỮU buffer bên dưới; khi nó bị thu
    #    gom rác — hoặc khi một module thứ hai bọc đè lên cùng buffer ấy —
    #    nó ĐÓNG buffer thật, và cả tiến trình chết với `ValueError: I/O
    #    operation on closed file` ở dòng `print` tiếp theo, một thông
    #    điệp không nhắc gì tới mã hoá hay tới module nào gây ra.
    #    `reconfigure()` sửa tại chỗ, gọi nhiều lần vô hại.
    #    Bánh cóc: `tests/test_353_voice_sidecar_bo_do.py`.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True)

DUOI_THU = ".local"

#: Trần một lượt. Không phải một con số thiêng — chỉ đủ lớn cho mọi việc thử đã
#: gặp (nhập 25 giọng ~50 credit, một lô dài ~30) và đủ nhỏ để một lần gõ thừa
#: chữ số bị chặn thay vì đi vào sổ.
TRAN_MOI_LUOT = 1000


def _xem(email: str, n: int) -> int:
    """In `n` bút toán gần nhất. Không ghi gì.

    ⭐ Nó ở CÙNG tệp với `nap` chứ không phải một công cụ riêng, và đó là chủ ý:
       ai vừa nạp xong sẽ muốn xem ngay sổ đã ghi gì, và một câu hỏi phải đi tìm
       công cụ thứ hai là một câu hỏi sẽ không được hỏi.
    """
    from sqlalchemy import desc, select

    from platform_core import users
    from platform_core.db import get_session
    from platform_core.models import CreditEntry

    gen = get_session()
    db = next(gen)
    try:
        u = users.tim_theo_email(db, email)
        if u is None:
            print(f"KHONG THAY {email}", file=sys.stderr)
            return 2
        cac = list(db.execute(
            select(CreditEntry).where(CreditEntry.user_id == str(u.id))
            .order_by(desc(CreditEntry.id)).limit(n)).scalars())
        from platform_core import credit
        sd = credit.so_du(db, str(u.id))
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    print(f"{email}  so du = {sd}")
    print(f"{'id':>7} {'delta':>7}  {'kind':16} {'job':12} note")
    for e in cac:
        print(f"{e.id:>7} {e.delta:>+7}  {str(e.kind)[:16]:16} "
              f"{str(e.job_id or '')[:12]:12} {str(e.note or '')[:44]}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", required=True)
    ap.add_argument("--so", type=int, default=0,
                    help="So credit nap. 0 = chi XEM so.")
    ap.add_argument("--xem", type=int, default=0, metavar="N",
                    help="In N but toan gan nhat roi thoat.")
    ap.add_argument("--ghi-chu", default="")
    a = ap.parse_args(argv)

    if a.xem:
        return _xem(a.email, a.xem)
    if not a.email.endswith(DUOI_THU):
        print(f"TU CHOI: chi nap cho tai khoan duoi '{DUOI_THU}'. "
              f"So credit la append-only — nap cho khach that khong dao duoc.",
              file=sys.stderr)
        return 2
    if not 0 < a.so <= TRAN_MOI_LUOT:
        print(f"TU CHOI: `--so` phai trong (0, {TRAN_MOI_LUOT}]. "
              f"Nhan duoc {a.so}.", file=sys.stderr)
        return 2

    from platform_core import credit, users
    from platform_core.db import get_session

    gen = get_session()
    db = next(gen)
    try:
        u = users.tim_theo_email(db, a.email)
        if u is None:
            print(f"KHONG THAY {a.email}", file=sys.stderr)
            return 2
        truoc = credit.so_du(db, str(u.id))
        but = credit.nap(db, str(u.id), a.so,
                         note=(a.ghi_chu or "nap noi bo cho tai khoan thu"))
        db.commit()
        sau = credit.so_du(db, str(u.id))
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    # 🔴 IN ĐỘ CHÊNH ĐO ĐƯỢC, KHÔNG IN CON SỐ ĐÃ YÊU CẦU.
    #
    #    Lượt chạy đầu tiên yêu cầu 100 và in "+100"; sổ ghi **+70** và số dư đi
    #    1 → 71. Nguyên nhân KHÔNG phải worker xen vào (tôi đã đoán vậy và đoán
    #    sai) — trình bọc `.ps1` có tham số `-So` trùng tên với một bộ đếm biến
    #    môi trường `$so`, PowerShell không phân biệt hoa thường, nên con số đi
    #    vào công cụ là **70**: số biến đã nạp từ `app.env`.
    #
    # ⛔ Một công cụ ghi sổ tiền mà in lại con số nó ĐỊNH ghi thay vì con số nó
    #    ĐÃ ghi thì không kiểm được gì cả — nó chỉ lặp lại ý định của người gõ.
    #    Sổ credit là append-only, nên "phát hiện muộn" ở đây nghĩa là không sửa
    #    được, chỉ ghi thêm.
    #
    # ⭐ Nay in ba con số: yêu cầu · bút toán thật · độ chênh số dư. Ba con số
    #    ấy lệch nhau vì ba lý do khác nhau, và gộp chúng lại là đánh mất đúng
    #    thông tin cần để phân biệt.
    chenh = sau - truoc
    print(f"{a.email}: so du {truoc} -> {sau}")
    print(f"  yeu cau         : +{a.so}")
    print(f"  but toan da ghi : {but.delta:+d}   (id {but.id})")
    print(f"  so du thay doi  : {chenh:+d}")
    if but.delta != a.so:
        print(f"  🔴 BUT TOAN LECH YEU CAU {but.delta - a.so:+d} — con so di vao "
              f"`credit.nap` KHONG phai con so ban go. Kiem trinh boc `.ps1`: "
              f"mot bien cuc bo trung ten tham so se ghi de no.")
    if chenh != but.delta:
        print(f"  ⚠️ so du lech but toan {chenh - but.delta:+d} — co but toan "
              f"KHAC xen vao giua hai phep doc (vd worker dang quyet toan "
              f"job). Do la binh thuong tren mot he dang chay.")
    print(f"ghi chu: {a.ghi_chu or 'nap noi bo cho tai khoan thu'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

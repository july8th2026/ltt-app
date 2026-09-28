r"""Có ai đang dùng máy chủ không? — HỎI TRƯỚC KHI DEPLOY.

## 🔴 Vì sao công cụ này tồn tại

Đêm 28/09/2026, hai phiên gần như deploy chồng lên nhau. Phiên kia dừng lại đúng
lúc và nói ra lý do:

> *"deploy **khởi động lại `LTTStudioWorker`**, và tôi đang có một job ASV chạy
>   dở (`asvr_47327a869a8f`, giai đoạn 8/13, đã 11 phút, 50 credit). Khởi động
>   lại giữa chừng giết nó — đúng thứ đã xảy ra với tôi một lần rồi."*

⚠️ Và đây là chỗ đáng ghi: `git status` sạch, gate xanh, ba bánh cóc toàn cây
xanh — **⛔ không một cổng nào trong kho nói gì** về việc có ai đang dùng máy chủ.
Một lượt deploy là thao tác trên **HỆ ĐANG PHỤC VỤ**, ⛔ không chỉ trên cây mã.

🔴 **VÀ HỌ BIẾT ĐƯỢC CHỈ VÌ JOB ẤY LÀ CỦA CHÍNH HỌ** — họ tự đính chính điều đó:

> *"Tôi ⛔ không hề kiểm 'có ai đang chạy job không' trước khi định deploy. Tôi
>   biết vì chính job đó là của tôi và tôi vừa khởi động nó. Nếu job ấy của bạn,
>   tôi đã giết nó và ⛔ không có gì trên máy nói cho tôi biết."*

⇒ Nên tệp này ⛔ **không** phải "cơ học hoá một thói quen tốt" — ⛔ không ai có thói
  quen ấy, vì ⛔ không ai có cách. Nó cấp một thông tin mà **⛔ không ai từng có**.
  Đó cũng là lý do ⛔ đừng đọc lần thoát hiểm kia như một bằng chứng rằng sự cẩn
  thận là đủ: nó là **một sự trùng hợp về quyền sở hữu**, và trùng hợp ⛔ không
  lặp lại theo yêu cầu.

⇒ *"Ai đang chạy job"* là trạng thái **⛔ KHÔNG nằm trong git**, nên ⛔ không bánh
  cóc nào trong kho có thể bắt nó. Nó chỉ bắt được bằng một **cửa hỏi CSDL**.

## ⭐ Vế mười (chốt cùng phiên `Auto Scan Video`)

> Với mỗi bẫy môi trường đã biết, hỏi **"cái gì sẽ NỔ nếu nó xảy ra lần nữa?"**
> Nếu câu trả lời là *"tôi sẽ nhớ"*, thì **chưa có gì cả**.

Tệp này là câu trả lời cho bẫy *"deploy giết job của khách"*.

## ⛔ Công cụ này CHỈ ĐỌC

Nó ⛔ không dừng deploy, ⛔ không sửa gì, ⛔ không giết gì. Nó **in ra sự thật** và
trả mã thoát. Việc đấu nó vào `setup\2-cai-dat.ps1` là **thay đổi đường deploy**
⇒ chỉ chủ dự án chốt. Trong lúc chờ, ai deploy thì chạy tay:

    python tools\ai_dang_dung_may_chu.py

    0  RANH        ⛔ không job nào đang chạy hay xếp hàng
    3  DANG DUNG   có job — deploy sẽ giết nó
    4  KHONG BIET  ⛔ không đọc được CSDL ⇒ **đừng deploy**, đây ⛔ không phải "rảnh"

⚠️ Mã `4` cố ý KHÁC `0`. Gộp *"⛔ không có job"* với *"⛔ không đo được"* vào một
   giá trị là mất đúng khả năng phân biệt mà công cụ này tồn tại để cung cấp —
   và cái mất ấy nghiêng về phía **nguy hiểm**: một CSDL ⛔ không đọc được sẽ
   trông như một máy rảnh.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ⭐ Khuôn của kho (`tools/api_prod_canary.py:52`, `tools/ab_lay_mau_35.py:51`):
#    chạy `python tools/x.py` chỉ đặt **thư mục script** vào `sys.path`, ⛔ không
#    đặt gốc kho — nên `import platform_core` ném `ModuleNotFoundError`.
GOC = Path(__file__).resolve().parents[1]
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

RANH, DANG_DUNG, KHONG_BIET = 0, 3, 4


def _nap_env(duong: str) -> None:
    """Chi DAT khoa chua co — bien da dat trong phien thang tep. ⛔ Khong in gia tri.

    ⭐ Cung khuon `tools/tai_khoan_thu.py::nap_env`. `utf-8-sig` la co y: tep env
       tren may chu tung duoc ghi KEM BOM, va mot BOM o dau lam khoa dau tien
       mang mot ky tu vo hinh ⇒ `setdefault` dat mot ten khac va bien that van
       vang. `CLAUDE.md` luat 6: ghi cau hinh KHONG BOM — nhung doc thi phai
       chiu duoc.
    """
    import os
    if not duong or not os.path.isfile(duong):
        return
    with open(duong, encoding="utf-8-sig") as fh:
        for dong in fh:
            t = dong.strip()
            if t and not t.startswith("#") and "=" in t:
                k, v = t.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _ket_qua(ma: int, dong: str) -> int:
    print(dong)
    print(f"RESULT: {'RANH' if ma == RANH else 'DANG DUNG' if ma == DANG_DUNG else 'KHONG BIET'}")
    return ma


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__ and __doc__.splitlines()[0])
    ap.add_argument("--chi-tiet", action="store_true",
                    help="in tung job thay vi chi dem")
    ap.add_argument("--app-env", default="",
                    help=r"nap bien LTT_* tu tep env "
                         r"(vd C:\LTTPlatform\secretspp.env)")
    args = ap.parse_args(argv)

    # 🔴 VI SAO CAN CO NAY, va vi sao thieu no lam cong cu VO DUNG.
    #
    #    Bien `LTT_DATABASE_URL` cua may chu ⛔ KHONG nam trong venv — nssm nem no
    #    vao tien trinh dich vu luc khoi dong. Nen goi cong cu nay tu mot shell
    #    thuong (hay ca tu `venv` production) deu tra `KHONG BIET`, du may dang
    #    hoan toan ranh.
    #
    # ⚠️ Va do la hong kieu TE NHAT cho mot cong cu canh: no ⛔ khong bao sai, no
    #    bao *"khong biet"* **moi lan**. Mot canh bao luon bat thi nguoi ta hoc
    #    cach bo qua no — dung ho voi *"bao dong gia lam nguoi ta TAT cong"*.
    #    Mot guard ⛔ khong dung duoc con te hon khong co guard, vi no mua su yen
    #    tam bang tin dung gia.
    #
    # ⭐ Khuon lay tu `tools/tai_khoan_thu.py::nap_env` — ⛔ khong tu viet lai, va
    #    ⛔ khong in gia tri nao ra.
    _nap_env(args.app_env)

    # ⚠️ Import TRONG hàm: tệp này được chạy trên máy chủ, nơi `sys.path` do
    #    `2-cai-dat.ps1` dựng. Import ở mức module làm `--help` cũng đòi CSDL.
    try:
        from sqlalchemy import select

        import platform_core.db as dbmod
        from platform_core.models import JOB_QUEUED, JOB_RUNNING, Job
    except Exception as exc:  # noqa: BLE001
        # ⛔ Bắt rộng CÓ LÝ ở đây, và lý do phải nói ra: mọi cách thất bại
        #    (thiếu gói, sai `sys.path`, ENV chưa nạp) đều dẫn tới CÙNG một kết
        #    luận vận hành — **⛔ không biết** ⇒ đừng deploy. Và nó ⛔ không nuốt
        #    lỗi: thông điệp được in nguyên văn ngay dưới.
        return _ket_qua(KHONG_BIET, f"⛔ khong nap duoc platform_core: {exc!r}")

    try:
        gen = dbmod.get_session()
        db = next(gen)
    except Exception as exc:  # noqa: BLE001
        return _ket_qua(KHONG_BIET, f"⛔ khong mo duoc CSDL: {exc!r}")

    try:
        hang = list(db.execute(
            select(Job.id, Job.app_slug, Job.job_type, Job.status, Job.user_id)
            .where(Job.status.in_((JOB_QUEUED, JOB_RUNNING)))
            .order_by(Job.status.desc())).all())
    except Exception as exc:  # noqa: BLE001
        return _ket_qua(KHONG_BIET, f"⛔ khong truy van duoc bang `jobs`: {exc!r}")
    finally:
        # ⛔ KHONG boc `try/except: pass` quanh `db.close()`.
        #
        # 🔴 Banh coc `check_silent_except` bat dung dong nay (54 > moc 53), va no
        #    dung: mot `except: pass` lam loi **bien mat han**, ⛔ khong chi mat
        #    thong diep. Neu dong ket noi that bai thi trang thai ket noi dang
        #    hong, va do la thu nguoi sap deploy **can biet**.
        #
        # ⭐ De no nem: luc ay cong cu thoat khac `0`, va nguoi deploy doc do la
        #    *"co gi khong on — dung deploy"*. Dung theo luat toi vua chot cung
        #    phien `Auto Scan Video`: **neu buoc phai chon, nga ve phia TON KEM
        #    chu ⛔ dung nga ve phia IM LANG.** Mot lan deploy bi hoan oan ton mot
        #    lan chay lai; mot loi bi nuot o day ton mot job cua khach.
        db.close()

    dang_chay = [h for h in hang if h.status == JOB_RUNNING]
    xep_hang = [h for h in hang if h.status == JOB_QUEUED]

    if not hang:
        return _ket_qua(RANH, "⛔ khong job nao dang chay hay xep hang.")

    dong = [f"⚠️ {len(dang_chay)} job DANG CHAY, {len(xep_hang)} job xep hang.",
            "   Deploy khoi dong lai `LTTStudioWorker` ⇒ job dang chay BI GIET."]
    if args.chi_tiet:
        for h in hang[:20]:
            # ⛔ Không in `user_id` đầy đủ — một dòng log deploy ⛔ không cần danh
            #    tính khách để trả lời câu "có ai đang dùng không".
            dong.append(f"   {h.status:<8} {h.app_slug}/{h.job_type}  job={h.id[:8]}")
        if len(hang) > 20:
            dong.append(f"   ... con {len(hang) - 20} job nua")
    else:
        dong.append("   (them `--chi-tiet` de xem tung job)")
    return _ket_qua(DANG_DUNG, "\n".join(dong))


if __name__ == "__main__":
    raise SystemExit(main())

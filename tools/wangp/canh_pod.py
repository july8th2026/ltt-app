"""Canh pod C-CLOUD: rảnh lâu thì tắt. Chạy theo lịch trên **máy A**.

    py tools/wangp/canh_pod.py            # xem quyet dinh, KHONG tat
    py tools/wangp/canh_pod.py --tat      # tat that neu du dieu kien

⛔ **Vì sao nó ở máy A chứ không ở pod.** Pod tự tắt được thì nó phải giữ khoá
   RunPod — mà `Phần 7` của bản khoá security nói rõ C-CLOUD **không** được giữ
   credential của LTT. Một máy có quyền tự huỷ là một máy có quyền huỷ máy khác.

⛔ Mặc định là **xem thôi**. `--tat` mới thật sự gửi lệnh. `POST /stop` nhả card
   và có thể không thuê lại được (06/09: hơn một tiếng) — một lệnh đắt như vậy
   không nên là hành vi mặc định của một script chạy theo lịch.

Đặt lịch trên Windows (mỗi 10 phút):

    schtasks /Create /TN "LTTV canh pod" /SC MINUTE /MO 10 ^
      /TR "python D:\\LTTSTUDIOSAPP\\tools\\wangp\\canh_pod.py --tat"
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

POD_ID = "s6bbn2cip61wo3"
APP = "lttvideo"

#: Trạng thái coi là "đang bận". Lấy từ `platform_core.models` chứ không gõ tay
#: — một chuỗi chép lại là một chuỗi sẽ lệch khi nền tảng thêm trạng thái.
from platform_core.models import JOB_QUEUED, JOB_RUNNING  # noqa: E402


def _do_so_viec(db) -> tuple[int, float | None]:
    """Trả `(so viec dang ban, giay ke tu viec cuoi ket thuc)`."""
    from sqlalchemy import select

    from platform_core.models import Job

    ban = db.execute(
        select(Job).where(Job.app_slug == APP,
                          Job.status.in_((JOB_QUEUED, JOB_RUNNING)))
    ).scalars().all()

    cuoi = db.execute(
        select(Job).where(Job.app_slug == APP)
        .order_by(Job.created_at.desc()).limit(1)
    ).scalars().first()

    giay = None
    if cuoi is not None:
        moc = getattr(cuoi, "finished_at", None) or cuoi.created_at
        giay = max(0.0, time.time() - moc.timestamp())
    return len(ban), giay


def main() -> int:
    from apps.lttvideo.dieu_phoi import DieuPhoi
    from platform_core.db import get_session

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.wangp.may_cloud import nap_env, tao_client, tim_app_env

    nap_env(tim_app_env())
    api = tao_client()

    gen = get_session()
    db = next(gen)
    try:
        so_ban, giay = _do_so_viec(db)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    dp = DieuPhoi(api=api, pod_id=POD_ID, client=None)
    nen = dp.nen_tat(so_viec_dang_chay=so_ban, giay_ke_tu_viec_cuoi=giay)

    trang_thai = api.rest("GET", f"/pods/{POD_ID}").get("desiredStatus")
    print(f"pod={POD_ID} trang_thai={trang_thai} dang_ban={so_ban} "
          f"ranh_giay={'?' if giay is None else round(giay)} "
          f"nguong={dp.nghi_tat_sau_s:.0f} => nen_tat={nen}")

    if trang_thai != "RUNNING":
        print("=> may da tat, khong lam gi")
        return 0
    if not nen:
        return 0
    if "--tat" not in sys.argv:
        print("=> DU DIEU KIEN TAT, nhung dang o che do xem. Them `--tat` de tat that.")
        return 0
    api.rest("POST", f"/pods/{POD_ID}/stop")
    print("=> DA GUI LENH TAT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

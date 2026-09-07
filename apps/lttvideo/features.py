"""Quy tắc nghiệp vụ của `lttvideo` — hiện chỉ có một: **hạn giữ nội dung**.

📌 Ở `features.py` chứ không ở `routes.py`: hợp đồng app (`AGENTS.md` §8) nói
   route chỉ lo HTTP, nghiệp vụ ở `features.py` với app một miền.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

log = logging.getLogger(__name__)

#: `C2` — chủ dự án chốt 07/09: video giữ **3 ngày**.
#:
#: ⚠️ Nền tảng có hạn riêng, **30 ngày** (`platform_core.job_content
#: .RETENTION_DAYS`), áp cho **mọi** app. Ta ngắn hơn, nên phép quét của ta chạy
#: trước; phép quét của nền tảng sau đó chỉ thấy nội dung đã hết hạn rồi.
#:
#: ⛔ **KHÔNG** hạ hằng số toàn cục xuống 3: nó sẽ xoá sớm nội dung của mọi app
#:    khác — một thao tác không hoàn tác, làm thay người không hỏi.
GIU_NGAY = 3


def don_het_han(db, storage=None, *, gioi_han: int = 200,
                bay_gio: datetime | None = None) -> dict:
    """Hết hạn nội dung của job `lttvideo` đã kết thúc quá `GIU_NGAY`.

    ⭐ Dùng `platform_core.job_content.expire_content` chứ **không** tự xoá khoá
       R2. Hàm ấy chỉ đụng những chuỗi trong `params`/`result` **có chứa id của
       chính job đó**, nên cái sai tệ nhất có thể xảy ra là **bỏ sót** một tệp —
       không bao giờ là xoá tệp của job khác. Với một thao tác không hoàn tác,
       đó là hướng sai duy nhất chấp nhận được, và tự viết lại phép ấy là vứt bỏ
       chính đảm bảo đó.

    Trả `{"jobs": n, "files": m}`.
    """
    from sqlalchemy import select

    from platform_core.job_content import expire_content
    from platform_core.models import (JOB_CANCELLED, JOB_DONE, JOB_ERROR, Job)

    if storage is None:
        from platform_core.storage import get_storage

        storage = get_storage()

    gio = bay_gio or datetime.now(timezone.utc)
    moc = gio - timedelta(days=max(1, int(GIU_NGAY)))

    rows = db.execute(
        select(Job)
        .where(Job.app_slug == "lttvideo",
               Job.status.in_((JOB_DONE, JOB_ERROR, JOB_CANCELLED)),
               Job.content_expired_at.is_(None),
               Job.finished_at.is_not(None),
               Job.finished_at < moc)
        .order_by(Job.finished_at)
        .limit(max(1, int(gioi_han)))
    ).scalars().all()

    ra = {"jobs": 0, "files": 0}
    for job in rows:
        ra["files"] += expire_content(db, storage, job, now=gio)
        ra["jobs"] += 1
    if ra["jobs"]:
        log.info("lttvideo: het han noi dung cua %d job, %d tep",
                 ra["jobs"], ra["files"])
    return ra


# ══════════════════════════════════════════════════════════════════════════
#  Thư viện video — nghiệp vụ của khoang bên phải
#
#  📌 Ở `features.py` chứ không ở `routes.py`. Hợp đồng app (`AGENTS.md` §8):
#     route chỉ lo HTTP. Ở app khác chính chỗ này đã phình thành một tệp route
#     1.799 dòng vì mọi thứ rơi vào đấy.
# ══════════════════════════════════════════════════════════════════════════

#: Tab trạng thái. Khoá phải khớp `Job.status` của nền tảng — **không** đặt tên
#: riêng rồi ánh xạ, vì một bảng ánh xạ là một bản sao sẽ trôi.
TRANG_THAI_TAB = ("all", "running", "done", "error", "cancelled")

#: Trần số video nạp cho một trang. Seedance lấy 60; ta cũng vậy — đủ để lọc có
#: nghĩa mà không kéo cả lịch sử về.
GIOI_HAN_THU_VIEN = 60

#: Trần số tài sản gợi ý lại. Nhiều hơn thì danh sách thành nơi để lạc.
GIOI_HAN_TAI_SAN = 24


def _phan_tram(job) -> int:
    try:
        return max(0, min(100, int(getattr(job, "progress", 0) or 0)))
    except (TypeError, ValueError):
        return 0


def thu_vien(db, user_id, *, trang_thai: str = "all", sap_xep: str = "moi",
             storage=None) -> dict:
    """Dữ liệu cho khoang thư viện: đếm theo tab, danh sách đã lọc, tài sản.

    ⭐ Một lần đọc CSDL cho cả ba thứ. Đếm phải tính trên **toàn bộ** tập của
       chủ, không phải trên tập đã lọc — nếu không thì bấm vào tab "Lỗi" sẽ thấy
       mọi tab khác về 0, và người dùng đọc thành "mất hết video".
    """
    from sqlalchemy import select

    from platform_core.models import (JOB_CANCELLED, JOB_DONE, JOB_ERROR,
                                      JOB_QUEUED, JOB_RUNNING, Job)

    thu_tu = Job.created_at.asc() if sap_xep == "cu" else Job.created_at.desc()
    rows = db.execute(
        select(Job).where(Job.user_id == user_id, Job.app_slug == "lttvideo")
        .order_by(thu_tu).limit(GIOI_HAN_THU_VIEN)
    ).scalars().all()

    so_dem = {k: 0 for k in TRANG_THAI_TAB}
    so_dem["all"] = len(rows)
    for j in rows:
        if j.status in (JOB_QUEUED, JOB_RUNNING):
            so_dem["running"] += 1
        elif j.status == JOB_DONE:
            so_dem["done"] += 1
        elif j.status == JOB_ERROR:
            so_dem["error"] += 1
        elif j.status == JOB_CANCELLED:
            so_dem["cancelled"] += 1

    if trang_thai == "running":
        loc = [j for j in rows if j.status in (JOB_QUEUED, JOB_RUNNING)]
    elif trang_thai in (JOB_DONE, JOB_ERROR, JOB_CANCELLED):
        loc = [j for j in rows if j.status == trang_thai]
    else:
        loc = rows

    video = [{
        "job_id": j.id,
        "trang_thai": j.status,
        "phan_tram": _phan_tram(j),
        "loi_nhan": str(getattr(j, "progress_msg", "") or ""),
        "loi": str(getattr(j, "error", "") or ""),
        "khoa": _khoa_dau((j.result or {}).get("video_keys") or []),
        "prompt": str((j.params or {}).get("prompt", ""))[:180],
        "prompt_day_du": str((j.params or {}).get("prompt", ""))[:10000],
        "ti_le": _ti_le((j.params or {}).get("resolution", "")),
        "do_dai": (j.params or {}).get("duration_s", ""),
        # `C2`: nội dung bị hết hạn sau 3 ngày. Thẻ phải nói ra, vì một nút Tải
        # về dẫn tới 404 im lặng thì người dùng tưởng hệ thống hỏng.
        "het_han": bool(getattr(j, "content_expired_at", None)),
    } for j in loc]

    return {"so_dem": so_dem, "video": video,
            "prompt_gan_day": _prompt_gan_day(rows),
            "tai_san": tai_san_cua_toi(rows, storage=storage)}


def _khoa_dau(ds) -> str:
    return str(ds[0]) if ds else ""


def _ti_le(do_phan_giai: str) -> str:
    """`832x480` → `16:9`. Người dùng chọn tỉ lệ, không chọn số điểm ảnh."""
    bang = {"832x480": "16:9", "480x832": "9:16", "720x720": "1:1"}
    return bang.get(str(do_phan_giai or ""), str(do_phan_giai or ""))


def _prompt_gan_day(rows, gioi_han: int = 10) -> list[str]:
    ra: list[str] = []
    da_thay: set[str] = set()
    for j in rows:
        p = str((j.params or {}).get("prompt", "")).strip()
        if p and p not in da_thay:
            da_thay.add(p)
            ra.append(p)
        if len(ra) >= gioi_han:
            break
    return ra


def tai_san_cua_toi(rows, *, storage=None) -> list[dict]:
    """Media người dùng đã đính ở các lượt trước, để dùng lại.

    🔴 **Khoá dựng từ lịch sử job của CHỦ, không nhận từ trình duyệt.** Đây là
       cùng một họ bảo vệ với `routes._KHUON_KHOA`: một danh sách trắng dựng từ
       dữ liệu của chính chủ, chứ không phải một bộ lọc chuỗi. `apps/taovideo`
       nói thẳng lý do trong chú thích của nó: *"browser không được tự khai
       storage key"*.

    ⚠️ `C2` xoá nội dung sau 3 ngày, nên tệp có thể **không còn**. Đánh dấu
       `het_han` để giao diện nói ra, thay vì lặng lẽ bỏ qua rồi để người dùng
       tưởng mình bấm hỏng.
    """
    if storage is None:
        from platform_core.storage import get_storage

        storage = get_storage()

    ra: list[dict] = []
    da_thay: set[str] = set()
    for j in rows:
        khoa = str((j.params or {}).get("media_key") or "")
        if not khoa or khoa in da_thay:
            continue
        da_thay.add(khoa)
        duoi = khoa.rsplit(".", 1)[-1].lower()
        ra.append({
            "khoa": khoa,
            "loai": "video" if duoi == "mp4" else "anh",
            "ten": str((j.params or {}).get("prompt", ""))[:40] or khoa[-12:],
            "het_han": not storage.exists(khoa),
        })
        if len(ra) >= GIOI_HAN_TAI_SAN:
            break
    return ra


def khoa_tai_san_hop_le(rows, khoa: str, *, storage=None) -> bool:
    """Khoá này có thật sự thuộc lịch sử của chủ và còn tệp không?

    ⛔ Gọi hàm này **trước** khi đưa một khoá do trình duyệt gửi vào job.
    """
    if not khoa:
        return False
    return any(a["khoa"] == khoa and not a["het_han"]
               for a in tai_san_cua_toi(rows, storage=storage))

"""
checkpoint.py — **SỔ TIẾN ĐỘ** của job upscale. ⛔ KHÔNG phải resume.

## Nó là gì, và nó KHÔNG là gì

Nó ghi một tệp JSON nhỏ mỗi khi job đi qua một chặng, để người vận hành soi được
*"job chết ở đâu"* sau sự cố. **Không một dòng mã nào đọc nó để BỎ QUA việc đã
làm.** Retry chạy lại 100 %: tải lại nguồn, probe lại, tách khung lại, upscale
lại mọi batch.

## ⭐ VÒNG ĐỜI CHÍNH XÁC của một sổ (chốt 26/09)

1. `jobs.handle` gọi `don_so_cu_mot_lan()` **ở đầu job** — một lần cho mỗi tiến
   trình worker, dọn sổ mồ côi cũ hơn `TTL_NGAY`.
2. Mỗi chặng ghi một tệp qua `save_checkpoint`.
3. Job **THÀNH CÔNG** ⇒ `finally` của `jobs.handle` gọi `cleanup_job_checkpoints`
   ⇒ sổ bị xoá ngay. Không còn ai cần biết một job tốt đã đi qua đâu.
4. Job **LỖI / BỊ HUỶ / ném bất cứ gì** ⇒ sổ **Ở LẠI**. Đó chính là ca duy nhất
   tệp này tồn tại vì nó. Bản trước `rmtree` sổ ở `finally` trên **mọi** đường
   kể cả đường lỗi — tự huỷ đúng lúc cần dùng. Sổ ở lại được thu hồi bởi bước
   (1) của một job sau, trong `TTL_NGAY` ngày.
5. Worker bị `os._exit()` khi hết giờ cứng (`platform_core.job_runner`, hằng
   `RUNTIME_LIMIT_S`) ⇒ `finally` **không chạy**, sổ ở lại ⇒ cũng về (1).

⛔ **Đừng gọi nó là "resume".** Bản trước của tệp này mở đầu bằng *"Job checkpoint
system for stage-based resume … the job can resume from the last completed stage"*
trong khi `load_checkpoint`/`get_job_checkpoints` **không có một caller nào trong
cả kho** — `ruff` còn bắt được chính import chết đó ở `quality_gate.py:166`.
`docs/UPSCALE_V2/PROGRESS_REPORT.md:81` khai *"Resume logic: implemented in
jobs.py"*, và `13_FINAL_REPORT.md:63-64` tự cho *"Resume/Recovery 9/10 — Full
stage recovery"*. Cả ba đều sai. Toàn văn:
`docs/UPSCALE_V2_CORRECTION/00_CURRENT_TRUTH.md` ISSUE G.

## Thứ DUY NHẤT thật sự bỏ qua việc đã làm

`jobs.py` kiểm `storage.exists(out_key)` — idempotency ở mức **cả job**: đầu ra
cuối đã có trên R2 thì khỏi làm lại. Thô nhưng thật, và không liên quan tệp này.

## Muốn resume THẬT thì cần gì (chưa xây — `07_CORRECTION_PLAN.md`)

Một workspace **bền** (không phải `tempfile.mkdtemp()` bị `rmtree` ở `finally`),
cộng với **dấu tay** cho mỗi chặng: fingerprint tham số + model + nguồn + phiên
bản pipeline. Không có dấu tay thì tái dùng một chặng cũ là **nguy hiểm** — đổi
preset hay đổi model mà vẫn dùng khung cũ là giao hàng sai cho khách.
⛔ Đừng thêm đường đọc vào đây mà chưa có dấu tay.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Sổ cũ hơn mốc này bị dọn bởi `don_so_cu()` — job lỗi từ lâu thì sổ hết việc.
# `don_so_cu()` được gọi THẬT qua `don_so_cu_mot_lan()` ở đầu `jobs.handle`.
TTL_NGAY = 7

# Cờ "tiến trình này đã dọn rồi". Sweeper phải rẻ tới mức vô hình với job, nên
# nó chạy ĐÚNG MỘT LẦN mỗi tiến trình worker thay vì mỗi job.
_DA_DON_TRONG_TIEN_TRINH = False


def goc_so() -> Path:
    """Gốc chứa sổ tiến độ.

    ⚠️ Đây **không** phải thư mục làm việc của job. `jobs.py` dùng
    `tempfile.mkdtemp()` (theo `%TEMP%` hệ thống) cho khung/segment; sổ thì nằm ở
    `LTT_UPSCALE_TEMP`, mặc định `tmp/upscale` **tương đối theo CWD**. Hai gốc
    khác nhau là cố ý — sổ phải sống lâu hơn dữ liệu nó mô tả — nhưng đừng nhầm
    cái này với cái kia.
    """
    return Path(os.environ.get("LTT_UPSCALE_TEMP", "tmp/upscale"))


def get_checkpoint_path(job_id: str, stage: str) -> Path:
    return goc_so() / job_id / f"{stage}.json"


def save_checkpoint(job_id: str, stage: str, details: dict | None = None) -> None:
    """Ghi một dòng sổ. Không bao giờ ném — sổ hỏng không được làm đỏ một job tốt."""
    try:
        f = get_checkpoint_path(job_id, stage)
        f.parent.mkdir(parents=True, exist_ok=True)
        with open(f, "w", encoding="utf-8") as fh:
            json.dump({"job_id": job_id, "stage": stage,
                       "timestamp": time.time(), "details": details or {}}, fh)
    except OSError as e:
        logger.warning("[so-tien-do] khong ghi duoc %s/%s: %s", job_id, stage, e)


def load_checkpoint(job_id: str, stage: str) -> dict:
    """Đọc một dòng sổ. ⚠️ CHỈ để người/công cụ chẩn đoán soi — ⛔ không dùng để
    quyết định bỏ qua việc: chưa có fingerprint (xem docstring đầu tệp)."""
    f = get_checkpoint_path(job_id, stage)
    if not f.exists():
        return {}
    try:
        with open(f, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {}


def get_job_checkpoints(job_id: str) -> dict[str, dict]:
    """Mọi dòng sổ của một job: `{tên_chặng: dữ_liệu}`. Dùng để chẩn đoán."""
    job_dir = goc_so() / job_id
    if not job_dir.exists():
        return {}
    return {p.stem: load_checkpoint(job_id, p.stem) for p in job_dir.glob("*.json")}


def cleanup_job_checkpoints(job_id: str) -> None:
    """Xoá sổ của một job. ⭐ Gọi ở `finally` của `jobs.handle` **CHỈ khi job
    thành công** — xem mục "VÒNG ĐỜI CHÍNH XÁC" ở đầu tệp.

    ⛔ Đừng gọi nó trên đường lỗi. Bản trước làm thế và xoá đúng thứ người vận
    hành cần để biết job chết ở chặng nào; sổ của job lỗi thuộc `don_so_cu()`.
    """
    job_dir = goc_so() / job_id
    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)


def don_so_cu_mot_lan(ttl_ngay: int = TTL_NGAY) -> int:
    """`don_so_cu()` nhưng TỐI ĐA MỘT LẦN cho mỗi tiến trình, và **không bao giờ
    ném**. Đây là caller thật của sweeper (`jobs.handle`, đầu job).

    ⭐ Vì sao "một lần mỗi tiến trình" chứ không phải "mỗi job": sweeper quét cả
    gốc sổ, còn một job upscale kéo nhiều phút — thêm một lần quét thư mục vào
    MỖI job là chi phí không mua được gì. Worker khởi động lại ⇒ cờ về `False` ⇒
    quét lại. Không có lịch cron nào phải cài, không có tiến trình nào phải nuôi.

    ⚠️ Nuốt MỌI ngoại lệ: một job tốt ⛔ không được đỏ vì việc dọn rác.
    """
    global _DA_DON_TRONG_TIEN_TRINH
    if _DA_DON_TRONG_TIEN_TRINH:
        return 0
    _DA_DON_TRONG_TIEN_TRINH = True
    try:
        return don_so_cu(ttl_ngay)
    except Exception as e:  # noqa: BLE001 — don rac khong duoc lam do mot job tot
        logger.warning("[so-tien-do] don so cu that bai: %s", e)
        return 0


def don_so_cu(ttl_ngay: int = TTL_NGAY) -> int:
    """Dọn sổ mồ côi cũ hơn `ttl_ngay`. Trả số thư mục đã xoá.

    ⭐ Caller: `don_so_cu_mot_lan()`, được `jobs.handle` gọi ở đầu mỗi job. Đó là
    lịch chạy duy nhất, và là lịch có thật — đừng thêm chú thích nào nói tệp này
    được một cron ngoài dọn hộ.

    Hai nguồn sổ mồ côi, cả hai đều không có `finally` nào cứu:
    - job **LỖI** — sổ ở lại CÓ Ý (mục "VÒNG ĐỜI CHÍNH XÁC" ở đầu tệp);
    - worker bị `os._exit()` lúc hết giờ cứng (`platform_core.job_runner`, hằng
      `RUNTIME_LIMIT_S`) ⇒ `finally` không chạy. Tra theo TÊN HẰNG, đừng tra theo
      số dòng — chú thích cũ ghi `job_runner.py:637-669`, và số dòng thì rỗng.
    """
    goc = goc_so()
    if not goc.is_dir():
        return 0
    han = time.time() - ttl_ngay * 86400
    da_xoa = 0
    for d in goc.iterdir():
        if not d.is_dir():
            continue
        try:
            moi_nhat = max((p.stat().st_mtime for p in d.glob("*.json")), default=0)
        except OSError:
            continue
        if moi_nhat and moi_nhat < han:
            shutil.rmtree(d, ignore_errors=True)
            da_xoa += 1
    if da_xoa:
        logger.info("[so-tien-do] don %d so mo coi (> %d ngay)", da_xoa, ttl_ngay)
    return da_xoa


# Tên chặng theo thứ tự — để đọc sổ cho dễ. ⛔ Không phải một máy trạng thái:
# không có mã nào chuyển chặng theo danh sách này.
CHECKPOINT_STAGES = [
    "probe_completed",
    "stabilize_completed",
    "frame_extraction_completed",
    "upscale_batch_",   # upscale_batch_001, _002, …
    "encode_batch_",    # encode_batch_001, _002, …
    "concat_completed",
    "output_uploaded",
]

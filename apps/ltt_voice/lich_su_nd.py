"""
lich_su_nd.py — trạng thái NGƯỜI DÙNG áp lên một lượt lịch sử.

Ba việc, và cả ba đều là ghi hoặc tra cứu PHỤC VỤ một thao tác ghi (khác
`doc_man_lich_su.py` — chỉ đọc):

  · **đánh dấu đã tải** — khi khách bấm một liên kết tải về;
  · **xoá một lượt**    — dọn tệp sớm + đánh dấu đã xoá;
  · **liệt kê hậu quả**  — TRƯỚC khi xoá, cho hộp xác nhận biết khối Dự án nào
    đang dùng đúng audio này (D005).

⛔ XOÁ KHÔNG hard-delete hàng job. Hàng job là **bằng chứng** mà sổ credit trỏ
   về (`credit_entries` khoá ngoài RESTRICT). Xoá = `job_content.expire_content`
   (xoá tệp, dọn nội dung, đặt `content_expired_at`) + đánh dấu `da_xoa_luc`.
   Bằng chứng còn nguyên, chỉ nội dung mất — cùng bất biến `voice_profile` giữ.

⛔ Và chỉ xoá được job đã KẾT THÚC. Một job đang chờ/đang chạy còn cần chính
   `params` của nó để chạy; dọn nội dung giữa chừng là bẻ gãy worker. `job_content`
   cũng chỉ quét job terminal vì đúng lý do đó.

🔴 T-11 — KHOÁ LƯU TRỮ CŨ. `0a07a49e` (31/08/2026) đổi khuôn khoá lưu trữ của
   app này từ `voice/out/{owner}/{job_id}.wav` sang
   `voice/out/{owner}/{job_id}/tieng.wav`, vì `job_content.content_keys` nhận
   diện tệp thuộc một job bằng cách tìm `/{job_id}/` NHƯ MỘT ĐOẠN ĐƯỜNG DẪN —
   khoá cũ không có dấu `/` sau job id nên KHÔNG khớp, và `expire_content` bỏ
   sót nó (cố ý sai theo hướng bỏ sót, không xoá nhầm). Job sinh TRƯỚC ngày đó
   vẫn mang khoá cũ trong `result["audio_key"]`, và `expire_content` một mình
   không dọn được nó — `xoa()` ở đây phải tự thử dọn thêm.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)

#: Trạng thái job mà xoá-nội-dung an toàn. Trùng tập `job_content.purge_expired`
#: đụng tới — một job chưa xong còn cần `params` để chạy.
TRANG_THAI_XOA_DUOC = ("done", "error", "cancelled")


def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


def trang_thai(db, owner_id: str, job_ids) -> dict:
    """`{job_id: {"da_tai": bool, "da_xoa": bool}}` cho một danh sách job.

    ⚠️ MỘT truy vấn cho cả trang, không một truy vấn mỗi dòng: màn Lịch sử dựng
       tới `TRAN_DOC` dòng, và một lượt hỏi mỗi dòng là con đường được hỏi lại
       mỗi vài giây thành `TRAN_DOC` lượt gọi CSDL.
    """
    ids = [str(j) for j in job_ids if j]
    if not owner_id or not ids:
        return {}
    from sqlalchemy import select

    from .tables import VoiceLichSu
    ra: dict = {}
    for row in db.execute(
            select(VoiceLichSu).where(VoiceLichSu.owner_id == str(owner_id),
                                      VoiceLichSu.job_id.in_(ids))).scalars():
        ra[str(row.job_id)] = {"da_tai": row.da_tai_luc is not None,
                               "da_xoa": row.da_xoa_luc is not None}
    return ra


def _lay_hoac_tao(db, owner_id: str, job_id: str):
    """Lấy dòng trạng thái, tạo nếu chưa có. Idempotent trước bấm hai lần.

    ⭐ Cứ INSERT và coi `IntegrityError` là đường bình thường — cùng khuôn
       `platform_core/gpu_lease.py` và `apps/vps/tables.py`. Đọc-rồi-ghi có một
       khoảng trống giữa hai bước mà hai request đồng thời lọt qua.
    """
    from sqlalchemy import select
    from sqlalchemy.exc import IntegrityError

    from .tables import VoiceLichSu
    row = db.execute(
        select(VoiceLichSu).where(VoiceLichSu.owner_id == str(owner_id),
                                  VoiceLichSu.job_id == str(job_id))
    ).scalar_one_or_none()
    if row is not None:
        return row
    row = VoiceLichSu(owner_id=str(owner_id), job_id=str(job_id))
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        row = db.execute(
            select(VoiceLichSu).where(VoiceLichSu.owner_id == str(owner_id),
                                      VoiceLichSu.job_id == str(job_id))
        ).scalar_one()
    return row


def danh_dau_tai(db, owner_id: str, job_id: str) -> None:
    """Ghi mốc **đã tải**. Gọi nhiều lần thì giữ mốc đầu — "đã từng tải" là một
    bit, không phải một bộ đếm."""
    row = _lay_hoac_tao(db, owner_id, job_id)
    if row.da_tai_luc is None:
        row.da_tai_luc = _now()
    db.flush()


def _khoa_cu(owner_id: str, job_id: str) -> str:
    """Khoá lưu trữ CŨ (trước `0a07a49e`, 31/08/2026): `{job_id}.wav` — job id
    nằm CUỐI đường dẫn, theo sau là dấu chấm, KHÔNG có `/` sau job id.

    Xem docstring module (T-11): `job_content.content_keys` không nhận diện
    được khoá này, nên `expire_content` để nó lại — hàm này là bản vá RIÊNG
    của app cho đúng lượt job cũ đó.
    """
    return f"voice/out/{owner_id}/{job_id}.wav"


def xoa(db, storage, job) -> None:
    """Xoá NỘI DUNG của một lượt + đánh dấu đã xoá. Hàng job giữ nguyên.

    Người gọi (route) đã kiểm sở hữu (`job_history.get_owned`) và trạng thái
    (`TRANG_THAI_XOA_DUOC`) trước khi gọi.
    """
    from platform_core import job_content

    job_content.expire_content(db, storage, job)

    # T-11 — dọn thêm khoá CŨ nếu job này sinh trước 0a07a49e. `content_keys`
    # bỏ sót khoá dạng `{job_id}.wav` (không phải một đoạn đường dẫn `/id/`),
    # nên `expire_content()` ở trên không đụng tới nó — thử xoá RIÊNG ở đây.
    # `FileNotFoundError` là đường bình thường: phần lớn job không mang khoá
    # cũ (chỉ những job sinh trước ngày đổi khuôn mới có).
    try:
        storage.delete(_khoa_cu(str(job.user_id), str(job.id)))
    except FileNotFoundError:
        pass

    row = _lay_hoac_tao(db, str(job.user_id), str(job.id))
    if row.da_xoa_luc is None:
        row.da_xoa_luc = _now()
    db.flush()


def khoi_bi_anh_huong(db, *, owner_id: str, job_id: str) -> list[dict]:
    """Các khối DỰ ÁN đang dùng audio của job này — cho hộp xác nhận XOÁ nói
    trước hậu quả (D005), thay vì để khách xoá xong mới phát hiện dự án gãy.

    Trả `[{"project_id": ..., "du_an": ..., "khoi_so": ...}, ...]`.
    `project_id` là `public_id` (khách không bao giờ thấy khoá nội bộ);
    `khoi_so` là vị trí 1-based của khối trong dự án của nó — cùng thứ tự mà
    `du_an.cac_khoi()` liệt kê, để câu "Khối N" khớp đúng số khách nhìn thấy
    khi mở dự án.

    ⭐ Khớp qua `VoiceBlock.job_id`, không qua so khớp chuỗi `audio_key`: job_id
       là khoá trực tiếp và không đổi hình dạng theo khuôn lưu trữ (khác
       `audio_key`, T-11 vừa cho thấy khuôn khoá lưu trữ CÓ thể đổi).
    """
    from sqlalchemy import select

    from . import du_an
    from .tables_du_an import VoiceBlock, VoiceProject

    if not owner_id or not job_id:
        return []
    rows = list(db.execute(
        select(VoiceBlock, VoiceProject)
        .join(VoiceProject, VoiceProject.id == VoiceBlock.project_id)
        .where(VoiceProject.owner_id == str(owner_id),
               VoiceBlock.job_id == str(job_id))
    ))
    if not rows:
        return []

    # Vị trí của mỗi khối TRONG DỰ ÁN CỦA NÓ — một truy vấn cho mỗi dự án khác
    # nhau chạm tới (thường đúng một), không một truy vấn cho mỗi khối.
    cac_khoi_theo_du_an: dict = {}
    ra = []
    for khoi, du in rows:
        if du.id not in cac_khoi_theo_du_an:
            cac_khoi_theo_du_an[du.id] = du_an.cac_khoi(db, du.id)
        vi_tri = next((i + 1 for i, k in enumerate(cac_khoi_theo_du_an[du.id])
                      if k.id == khoi.id), 0)
        ra.append({"project_id": du.public_id, "du_an": du.ten or "",
                   "khoi_so": vi_tri})
    return ra

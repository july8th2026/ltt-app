"""dinh_tep.py — luồng đính tài liệu vào hội thoại. (H44 B1)

## Ba bước, và bước GIỮA là chỗ khách nhìn thấy giá

    1. nhan()   byte -> `upload_sessions` (stage + confirm)  -> BAO GIA
    2. (khach bam dong y)
    3. trich()  nop job (GIU credit) -> promote -> `kho_tep.gan`

⛔ Bước 1 **không** promote. `promote` là cửa credit (`upload_sessions.py` tự
   viết: *"để không ai biến input của job thành kho lưu trữ miễn phí"*), và nó
   đòi một `Job`. Nộp job ở bước 1 nghĩa là giữ tiền **trước khi** khách thấy
   giá — ngược đúng điều P06 §7 chốt.

⭐ Nên tệp ở giữa hai bước nằm ở trạng thái `ready`: byte đã lên `storage`, chưa
   ai bị trừ gì, và `upload_sessions.sweep()` tự dọn nếu khách bỏ đi.

## Vì sao không tái dùng `source_drafts.create_ticket` của autosubvideo

App không được nhập app (`CLAUDE.md`). Và luồng ấy giải bài **video 90 MB đi
thẳng R2** — tài liệu thì nhỏ, đi `multipart` như `anh_vao` đã làm trong chính
app này. Mượn **thứ tự bước**, không mượn mã.
"""
from __future__ import annotations

import logging

from apps.chatltt import gia_trich
from apps.chatltt.services import kho_tep, trich_van_ban as T
from apps.chatltt.tables import ChatlttConversation, ChatlttDoan
from platform_core import upload_sessions
from platform_core.models import UploadSession
from platform_core.storage import get_storage

log = logging.getLogger(__name__)

TEN_TOOL = "chatltt.trich_tep"

#: Trần một tài liệu. Cloudflare chặn ở **100 MB/request**, nhưng tài liệu để
#: hỏi thì nhỏ hơn hẳn — 20 MB đã là một cuốn sách quét.
#:
#: ⚠️ Trần đặt DƯỚI nhu cầu bình thường biến thất bại thành MẶC ĐỊNH. 20 MB bỏ
#:    xa ca thường (một hợp đồng PDF ~1–3 MB), nên nó chặn ca bệnh lý.
TRAN_BYTE = 20 * 1024 * 1024

#: Kiểu nhận được — **cùng tập** với `trich_van_ban.DUOC_NHAN`.
#: ⛔ Một giao diện mời người dùng chọn thứ ta không đọc được là một lời hứa
#:    hỏng. Đó đúng lỗi đang sống ở `chataistudio` với PDF.
KIEU_NHAN = T.DUOC_NHAN


class LoiDinhTep(ValueError):
    """Hỏng ở phía người dùng: kiểu lạ, quá lớn, không phải hội thoại của họ."""


def _hoi_thoai_cua(db, *, user_id: str, conversation_id: str):
    c = db.get(ChatlttConversation, str(conversation_id))
    if c is None or c.user_id != str(user_id):
        raise LoiDinhTep("hoi thoai khong thuoc ban")
    return c


def nhan(db, *, user_id: str, conversation_id: str, ten_tep: str,
         content_type: str, du_lieu: bytes) -> dict:
    """Bước 1: nhận byte, **chưa** thu tiền. Trả về báo giá để khách xem.

    ⭐ Kiểm kiểu **trước** khi ghi byte: từ chối sớm rẻ hơn ghi rồi dọn, và câu
       từ chối đọc được ngay thay vì tới sau một vòng job.
    """
    _hoi_thoai_cua(db, user_id=user_id, conversation_id=conversation_id)

    ct = (content_type or "").split(";")[0].strip().lower()
    if ct not in KIEU_NHAN:
        raise LoiDinhTep(f"chua doc duoc dinh dang {ct!r}")
    if not du_lieu:
        raise LoiDinhTep("tep rong")
    if len(du_lieu) > TRAN_BYTE:
        raise LoiDinhTep(
            f"tep {len(du_lieu):,} byte, tran {TRAN_BYTE:,}")

    ve = upload_sessions.stage_bytes(
        db, get_storage(), user_id=str(user_id), app_slug="chatltt",
        filename=str(ten_tep or "tai-lieu"), content_type=ct, data=du_lieu,
        max_size=TRAN_BYTE, allowed_types=tuple(KIEU_NHAN))

    from platform_core.runtime_noi_bo import job as J
    bg = J.bao_gia(TEN_TOOL, {"tep_id": "cho", "so_byte": len(du_lieu)},
                   db=db, user_id=str(user_id))
    return {"upload_id": ve.id, "ten_tep": ve.filename,
            "content_type": ve.content_type, "so_byte": int(ve.actual_size or 0),
            "bao_gia_credit": int(bg.credit),
            "phien_ban_gia": gia_trich.PHIEN_BAN_GIA,
            # 🔴 Noi that rang gia nay la TAM. Mot bao gia im lang ve trang thai
            #    cua chinh no la mot bao gia khach khong danh gia duoc.
            "gia_da_chot": bool(gia_trich.CHU_DU_AN_DA_CHOT)}


def trich(db, *, user_id: str, conversation_id: str, upload_id: str) -> dict:
    """Bước 3: khách đã bấm đồng ý ⇒ nộp job (GIỮ credit) → promote → gắn.

    ⛔ Thứ tự **không** đổi được: `promote` đòi một `Job`, và job phải là job
       **đã giữ credit** — đó là toàn bộ ý nghĩa của cửa ấy.
    """
    from platform_core.runtime_noi_bo import job as J

    _hoi_thoai_cua(db, user_id=user_id, conversation_id=conversation_id)
    ve = db.get(UploadSession, str(upload_id))
    if ve is None or ve.user_id != str(user_id) or ve.app_slug != "chatltt":
        raise LoiDinhTep("ve tai len khong thuoc ban")

    bg = J.bao_gia(TEN_TOOL, {"tep_id": "cho", "so_byte": int(ve.actual_size or 0)},
                   db=db, user_id=str(user_id))
    job = J.nop_job(db, user_id=str(user_id), bao_gia=bg,
                    correlation_id=str(conversation_id),
                    idempotency_key=f"trich:{ve.id}")

    khoa_cuoi = f"chatltt/{user_id}/tep/{ve.id}"
    upload_sessions.promote(db, get_storage(), ve, job=job, final_key=khoa_cuoi)

    tep = kho_tep.gan(db, user_id=str(user_id),
                      conversation_id=str(conversation_id), upload_id=ve.id)

    # ⭐ Job da duoc nop TRUOC khi co `tep_id`, nen bay gio moi noi hai dau lai.
    #    `params` la JSON nen sua duoc; va day la chỗ DUY NHAT lam viec do.
    params = dict(getattr(job, "params", None) or {})
    params.update({"tep_id": tep.id, "user_id": str(user_id)})
    job.params = params
    db.flush()

    return {"tep_id": tep.id, "job_id": job.id, "ten_tep": tep.ten_tep,
            "trang_thai_trich": tep.trang_thai_trich,
            "credit_da_giu": int(bg.credit)}


def danh_sach(db, *, user_id: str, conversation_id: str) -> list[dict]:
    """Tệp của một hội thoại, kèm số đoạn đã trích được."""
    _hoi_thoai_cua(db, user_id=user_id, conversation_id=conversation_id)
    return [{"tep_id": t.id, "ten_tep": t.ten_tep, "content_type": t.content_type,
             "so_byte": int(t.kich_thuoc or 0), "so_doan": int(t.so_doan or 0),
             "trang_thai_trich": t.trang_thai_trich,
             # ⛔ Ly do loi phai ra toi giao dien. Mot tep nam im o trang thai
             #    `loi` ma khong noi vi sao la mot tep nguoi dung se thu lai mai.
             "ly_do_loi": t.ly_do_loi}
            for t in kho_tep.cua_hoi_thoai(db, user_id=user_id,
                                           conversation_id=conversation_id)]


def go(db, *, user_id: str, tep_id: str) -> bool:
    """Gỡ một tệp khỏi hội thoại: xoá liên kết **và** các đoạn đã trích.

    ⛔ Xoá liên kết mà để lại `chatltt_doan` là để lại **chữ của khách** trong
       chỉ số tìm kiếm sau khi họ đã bấm gỡ. Giao diện sẽ nói "đã gỡ" trong khi
       model vẫn đọc được — đúng loại sai lệch không ai phát hiện.

    ⭐ Byte gốc thì **không** xoá ở đây: nó thuộc `upload_sessions`, có vòng đời
       và `sweep()` riêng. Hai hệ, hai lời hứa; xoá chéo là lấn việc.
    """
    tep = kho_tep.mot(db, user_id=user_id, tep_id=tep_id)
    if tep is None:
        return False
    db.query(ChatlttDoan).filter(ChatlttDoan.tep_id == tep.id).delete()
    db.delete(tep)
    db.flush()
    return True

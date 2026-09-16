"""
doc_man_giong.py — số liệu mà MÀN GIỌNG cần, gom trong ít truy vấn nhất.

⭐ VÌ SAO TÁCH KHỎI `tham_chieu.py`.

   `tham_chieu.py` trả lời câu hỏi của **nghiệp vụ**: giọng này của ai, biểu diễn
   nào đang dùng, tệp nguồn ở đâu. Tệp này trả lời câu hỏi của **một màn hình**:
   giọng này đã đọc bao nhiêu lượt, tổng bao nhiêu phút, dùng lần cuối khi nào.

   Trộn hai thứ đó thì tầng nghiệp vụ mọc dần những hàm chỉ một trang cần, và
   không ai dám xoá chúng vì không biết còn ai gọi. Tách ra thì ngày màn này
   đổi, chỗ phải sửa là **một tệp**, và nó không nằm trên đường đi của worker.

   *(Và có một lý do rất thực tế nữa: `tham_chieu.py` đang trong tay một phiên
   khác. Thêm một tệp thì không ai phải chờ ai.)*

⛔ MỌI THỨ Ở ĐÂY LÀ CHỈ ĐỌC. Không ghi, không quyết định gì. Một con số hỏng ở
   đây được phép trả về 0; nó không được phép làm sập trang.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def thong_ke_theo_giong(db, owner_id: str, app_slug: str) -> dict:
    """`{public_id: {so_luot, giay, lan_cuoi}}` cho MỌI giọng của một khách.

    🔴 MỘT truy vấn cho tất cả giọng, không một truy vấn mỗi giọng.

       Khuôn "mỗi thẻ hỏi một câu" chạy êm với hai giọng và sập với hai mươi —
       và nó sập ở chỗ khó thấy nhất, vì trang vẫn đúng, chỉ chậm dần theo số
       giọng khách tạo ra. Người dùng nhiều nhất là người chờ lâu nhất.

    ⚠️ Gom theo `params->voice_id`, và đó là một cột JSON. SQLite lẫn PostgreSQL
       đều đọc được nhưng bằng cú pháp khác nhau, nên ở đây gom **trong Python**
       sau một lượt lấy về. Đánh đổi có chủ ý: đúng trên cả hai CSDL, và số dòng
       bị chặn bởi `GIOI_HAN` bên dưới.
    """
    try:
        from sqlalchemy import select

        from platform_core.models import Job
    except Exception:  # noqa: BLE001 - khong nap duoc model thi tra rong
        # ⛔ Nuốt lỗi mà không ghi lại là làm nó biến mất ở đúng chỗ khó tìm
        #    nhất. `tools/check_silent_except.py` là bánh cóc cho đúng việc này,
        #    và nó bắt được dòng này ngay lượt gate đầu tiên.
        log.warning("khong nap duoc model Job de dem thong ke giong",
                    exc_info=True)
        return {}

    #: Trần dòng đọc về. Một khách sinh mười nghìn lượt thì con số "đã đọc bao
    #: nhiêu lượt" không đáng để quét cả bảng ở mỗi lượt dựng trang.
    GIOI_HAN = 2000

    kq: dict = {}
    try:
        dong = db.execute(
            select(Job.params, Job.result, Job.created_at)
            .where(Job.user_id == str(owner_id),
                   Job.app_slug == app_slug,
                   Job.job_type.endswith(".synthesize"))
            .order_by(Job.created_at.desc())
            .limit(GIOI_HAN)
        ).all()
    except Exception:  # noqa: BLE001 - so lieu trang tri, khong lam sap trang
        log.warning("khong doc duoc thong ke giong", exc_info=True)
        return {}

    for params, result, luc in dong:
        ma = str((params or {}).get("voice_id") or "").strip()
        if not ma:
            continue
        muc = kq.setdefault(ma, {"so_luot": 0, "giay": 0.0, "lan_cuoi": None})
        muc["so_luot"] += 1
        try:
            muc["giay"] += float((result or {}).get("duration_s") or 0.0)
        except (TypeError, ValueError):
            pass
        # Đã sắp giảm dần theo thời gian, nên dòng đầu gặp là lần gần nhất.
        if muc["lan_cuoi"] is None:
            muc["lan_cuoi"] = luc
    return kq


def clip_nguon(db, profile_id: int) -> list:
    """Các clip gốc của một giọng. Bản GỐC, thứ dựng lại giọng khi nâng engine."""
    try:
        from sqlalchemy import select

        from .tables import VoiceRef
        return list(db.execute(
            select(VoiceRef).where(VoiceRef.profile_id == int(profile_id))
            .order_by(VoiceRef.tao_luc.desc())
        ).scalars())
    except Exception:  # noqa: BLE001
        log.warning("khong doc duoc clip nguon cua %s", profile_id, exc_info=True)
        return []


def chi_tiet_cho_trang(db, giong: list, thong_ke: dict, duong_audio: str,
                       owner_id: str | None = None) -> dict:
    """Gói mọi thứ màn Giọng cần thành JSON, để bấm một thẻ **không gọi mạng**.

    ⭐ Hai mươi giọng mẫu cộng vài giọng riêng là một tập nhỏ và đã nằm sẵn
       trong phiên này. Nạp trước thì bấm thẻ nào cũng hiện tức thì; gọi thêm
       một vòng cho mỗi lần bấm là trả một cái giá thật cho một thứ đã biết.

    ⚠️ Đổi lại: đừng bao giờ nhét thứ **nặng** hay thứ **bí mật** vào đây. Không
       `speaker_emb`, không khoá kho thô — chỉ đường dẫn phát đã kiểm quyền.

    🔴 `owner_id` (GUI-D001, 16/09/2026): clip GỐC chỉ gửi cho CHỦ giọng. Trước
       đây mọi giọng trong `giong` — kể cả giọng kho chung của người khác — mang
       `clip[].url` = khoá kho thô `voice/<owner_uuid>/<public_id>/source.wav`
       vào JSON của trang: lộ UUID chủ sở hữu, và dựng một trình phát mà cửa
       `/audio` chắc chắn từ chối (chỉ mở `voice/{uid}/source.*`). `None` giữ
       hành vi cũ cho nơi gọi chưa truyền.
    """
    from .giong_vong_doi import NGUON_MAC_DINH_CU as _NGUON_MAC_DINH_CU

    ra: dict = {}
    for g in giong:
        tk = thong_ke.get(g.public_id) or {}
        giay = float(tk.get("giay") or 0.0)
        lan_cuoi = tk.get("lan_cuoi")
        ra[g.public_id] = {
            "ten": g.ten_hien_thi,
            "trang_thai": g.trang_thai,
            "so_luot": int(tk.get("so_luot") or 0),
            "phut": round(giay / 60.0, 1),
            "lan_cuoi": lan_cuoi.strftime("%d/%m/%Y") if lan_cuoi else "",
            # D003/D004: LÀN + xuất xứ của nó, cho panel chi tiết (JS đọc
            # `chi_tiet[ma]`, không đọc thẳng ORM). `can_xac_nhan_lan` gói sẵn
            # phép so `ngon_ngu_nguon == NGUON_MAC_DINH_CU` — thẩm quyền của ba
            # giá trị hợp lệ là `giong_vong_doi.py`, đọc từ đó thay vì gõ lại
            # chuỗi ở đây.
            "ngon_ngu": str(getattr(g, "ngon_ngu", "") or ""),
            "ngon_ngu_nguon": str(getattr(g, "ngon_ngu_nguon", "") or ""),
            "can_xac_nhan_lan": str(getattr(g, "ngon_ngu_nguon", "") or "")
                == _NGUON_MAC_DINH_CU,
            "clip": [
                {
                    "ten": (r.storage_key or "").rsplit("/", 1)[-1],
                    "giay": round(float(r.giay or 0.0), 1),
                    "url": f"{duong_audio}/{r.storage_key}",
                }
                for r in (clip_nguon(db, g.id)
                          if owner_id is None
                          or str(g.owner_id) == str(owner_id) else ())
            ],
        }
    return ra

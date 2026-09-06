"""
doc_man_lich_su.py — số liệu mà MÀN LỊCH SỬ cần.

⭐ Cùng lý do tách như `doc_man_giong.py`: đây là câu hỏi của **một màn hình**
   ("lượt nào, từ đâu, tốn bao nhiêu"), không phải quy tắc nghiệp vụ. Và nó
   không nằm trên đường đi của worker, nên đổi nó không chạm vào chỗ tiêu tiền.

⛔ CHỈ ĐỌC. Không ghi, không quyết định. Một con số hỏng ở đây được phép là 0.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)

#: Số dòng đọc về trước khi lọc trong Python.
#:
#: 🔴 VÌ SAO CÓ TRẦN, VÀ VÌ SAO NÓ PHẢI ĐƯỢC NÓI RA.
#:
#:    `nguon` và `voice_id` nằm trong cột JSON `params`. SQLite và PostgreSQL
#:    truy JSON bằng hai cú pháp khác nhau, nên lọc hai mặt đó ở tầng SQL sẽ là
#:    hai nhánh mã — và nhánh chỉ chạy trên một CSDL là nhánh sẽ mục.
#:    ⇒ Lọc trong Python, sau một lượt đọc có trần.
#:
#: ⛔ Nhưng một cái trần **không nói ra** thì tệ hơn không có trần: màn hình sẽ
#:    trông như đã liệt kê hết trong khi nó cắt bớt. `tom_tat()` trả `bi_cat` để
#:    giao diện nói thẳng điều đó.
TRAN_DOC = 500

#: Nguồn đã biết. Khớp giá trị `params["nguon"]` mà các cửa nộp ghi vào.
NGUON = ("studio", "giong", "du_an", "api")


def _nguon_cua(job) -> str:
    """Lượt này đến từ đâu.

    ⚠️ Job **cũ hơn P1** không có khoá `nguon` — chúng được nộp trước khi cửa
       ghi nó. Trả `""` chứ không đoán: đoán một nguồn cho dữ liệu lịch sử là
       bịa ra một sự thật không ai kiểm được nữa.
    """
    return str((job.params or {}).get("nguon") or "")


def _giong_cua(job) -> str:
    """Mã giọng đã đọc lượt này. Rỗng nghĩa là **giọng mặc định**.

    ⛔ RỖNG KHÔNG PHẢI "KHÔNG BIẾT". Khách không chọn gì thì cửa nộp ghi
       `voice_id=""` và `preset=""`, và engine đọc bằng preset mặc định của nó
       (`giong_mau.MAC_DINH`). Tức lượt ấy **có** một giọng xác định, chỉ là
       không ai gõ tên nó ra.

    ⚠️ Nhưng ĐỪNG điền tên mặc định ở đây. Hàm này cũng là thứ `loc()` so bằng
       và là thứ `tom_tat()` gom nhóm; nhét một cái tên vào sẽ làm các lượt
       "mặc định" trộn lẫn với các lượt khách CHỌN đúng giọng ấy — hai việc
       khác nhau, và gộp chúng là bịa ra một con số không ai kiểm được.
       Việc đặt tên cho ô trống là việc của **màn hình**: `dong_cho_trang`
       trả thêm `giong_mac_dinh` để khuôn mẫu nói ra, không đoán.
    """
    p = job.params or {}
    return str(p.get("voice_id") or p.get("preset") or "")


def loc(job_list, *, trang_thai: str = "", nguon: str = "", giong: str = ""):
    """Lọc trong Python. Chuỗi rỗng nghĩa là **không lọc mặt đó**."""
    ra = list(job_list)
    if trang_thai:
        ra = [j for j in ra if j.status == trang_thai]
    if nguon:
        ra = [j for j in ra if _nguon_cua(j) == nguon]
    if giong:
        ra = [j for j in ra if _giong_cua(j) == giong]
    return ra


def tom_tat(job_list) -> dict:
    """Đếm theo trạng thái + vài con số nhanh. Tính trên **tập đã đọc về**.

    ⚠️ Nói rõ phạm vi: đây là thống kê của `TRAN_DOC` lượt gần nhất, không phải
       của toàn bộ lịch sử. Một con số "tổng cộng" mà thật ra là "tổng của 500
       lượt gần đây" là một con số sai ở đúng chỗ người ta tin nó nhất.
    """
    dem = {"done": 0, "error": 0, "queued": 0, "running": 0, "cancelled": 0}
    tong_giay = 0.0
    tong_credit = 0
    dem_giong: dict = {}

    for j in job_list:
        if j.status in dem:
            dem[j.status] += 1
        kq = j.result or {}
        try:
            tong_giay += float(kq.get("duration_s") or 0.0)
        except (TypeError, ValueError):
            pass
        try:
            tong_credit += int(kq.get("credit_cost") or 0)
        except (TypeError, ValueError):
            pass
        g = _giong_cua(j)
        if g:
            dem_giong[g] = dem_giong.get(g, 0) + 1

    tong = len(job_list)
    hay_dung = max(dem_giong.items(), key=lambda x: x[1]) if dem_giong else None
    return {
        "tong": tong,
        "dem": dem,
        "dang_chay": dem["queued"] + dem["running"],
        "phut": round(tong_giay / 60.0, 1),
        "credit": tong_credit,
        # Tỉ lệ lỗi tính trên số lượt ĐÃ KẾT THÚC, không trên tổng: một lượt
        # đang chạy chưa hỏng, và đếm nó vào mẫu số làm tỉ lệ trông đẹp lên.
        "ti_le_loi": (round(dem["error"] * 100.0 / (dem["done"] + dem["error"]), 1)
                      if (dem["done"] + dem["error"]) else 0.0),
        "giong_hay_dung": hay_dung[0] if hay_dung else "",
        "giong_hay_dung_so": hay_dung[1] if hay_dung else 0,
    }


#: Các mốc lọc theo ngày. RỜI RẠC, không phải ô chọn ngày tự do: một
#: khoảng tuỳ ý mời khách chọn một khoảng không có dữ liệu rồi tưởng
#: màn hình hỏng. `0` = không lọc.
CAC_MOC_NGAY = (0, 1, 7, 30)


def _moc_ngay(so_ngay: int):
    """`so_ngay` ngày gần nhất -> mốc bắt đầu, hoặc `None` nếu không lọc.

    ⚠️ Dùng `timezone.utc`: `Job.created_at` là `DateTime(timezone=True)`, và so
       một mốc **không có múi giờ** với một cột **có múi giờ** thì PostgreSQL
       ném, còn SQLite thì so sai một cách im lặng. Production là PG, test là
       SQLite — nên lỗi ấy sẽ chỉ hiện ra ở một bên.
    """
    from datetime import datetime, timedelta, timezone

    if so_ngay <= 0:
        return None
    return datetime.now(timezone.utc) - timedelta(days=so_ngay)


def doc(db, owner_id: str, app_slug: str, *, trang_thai: str = "",
        nguon: str = "", giong: str = "", so_ngay: int = 0) -> dict:
    """Một lượt đọc, trả mọi thứ màn Lịch sử cần.

    ⭐ `so_ngay` lọc ở SQL (`list_owned(start=...)`), không lọc trong Python:
       trần `TRAN_DOC` cắt TRƯỚC khi lọc, nên lọc sau đó sẽ cho ra "7 ngày qua"
       tính trên một tập đã bị cắt — và con số ấy sai theo hướng khó thấy nhất
       (nó chỉ sai với người dùng nhiều).
    """
    from platform_core import job_history

    try:
        tat_ca, _cursor = job_history.list_owned(
            db, owner_id, app_slug=app_slug, limit=TRAN_DOC,
            start=_moc_ngay(so_ngay))
    except Exception:  # noqa: BLE001 - man hinh khong duoc sap vi mot truy van
        log.warning("khong doc duoc lich su cua %s", owner_id, exc_info=True)
        tat_ca = []

    return {
        "tat_ca": tat_ca,
        "dong": loc(tat_ca, trang_thai=trang_thai, nguon=nguon, giong=giong),
        "tom_tat": tom_tat(tat_ca),
        # Đúng bằng trần nghĩa là **có thể** còn nữa. Giao diện phải nói ra.
        "bi_cat": len(tat_ca) >= TRAN_DOC,
        "tran": TRAN_DOC,
        # Các giọng thực sự xuất hiện trong lịch sử — ô lọc chỉ nên liệt kê
        # những giọng có ít nhất một lượt, không liệt kê cả hai mươi hai.
        "giong_da_dung": sorted({_giong_cua(j) for j in tat_ca if _giong_cua(j)}),
        "nguon_da_dung": sorted({_nguon_cua(j) for j in tat_ca if _nguon_cua(j)}),
    }


def dong_cho_trang(job, duong_audio: str) -> dict:
    """Một dòng lịch sử, đã phẳng hoá cho template."""
    kq = job.result or {}
    return {
        "id": str(job.id),
        "luc": job.created_at,
        "trang_thai": job.status,
        "text": str((job.params or {}).get("text") or "")[:160],
        "giong": _giong_cua(job),
        # 🔴 Lượt không chọn giọng vẫn ĐƯỢC ĐỌC bằng một giọng có thật. Trước
        #    02/09/2026 dòng của nó không nói giọng nào cả — một ô trống ở giữa
        #    thời gian và thời lượng, đọc như "thiếu dữ liệu" chứ không như
        #    "mặc định". Với hai mươi giọng trong danh mục, đó đúng là câu hỏi
        #    khách quay lại lịch sử để hỏi: *lượt này đọc bằng giọng nào?*
        "giong_mac_dinh": not _giong_cua(job),
        "nguon": _nguon_cua(job),
        "giay": kq.get("duration_s"),
        "credit": kq.get("credit_cost"),
        "so_doan": kq.get("so_doan"),
        "audio_url": (f"{duong_audio}/{kq['audio_key']}"
                      if kq.get("audio_key") else ""),
    }

"""tim_doan.py — truy hồi đoạn văn bản của một hội thoại. (H44 P06 bước 4)

## Hai đường, và đường thứ hai KHÔNG được giả vờ là đường thứ nhất

    PostgreSQL   to_tsvector + plainto_tsquery + f_unaccent   <- DUONG THAT
    con lai      so khop chuoi con, khong dau                 <- CHI de test ACL

⛔ Đường SQLite **không phải** một bản triển khai thứ hai của tìm kiếm. Nó tồn
   tại để phép kiểm **quyền và phạm vi** chạy được ở mọi nơi — hai thứ ấy
   *không phụ thuộc* vào bộ xếp hạng. Đó đúng ranh giới của một "cửa giả" hợp
   lệ: nó chỉ trả lời được những câu **không phụ thuộc thứ nó thay**.

⇒ `nen_tang()` nói ra nó đang chạy đường nào, và `test_826` chốt rằng không ai
  được đọc kết quả SQLite như bằng chứng cho chất lượng tìm kiếm.

## Vì sao `simple` chứ không phải một cấu hình tiếng Việt

Postgres **không có** cấu hình `vietnamese` (đo 06/09: 30 cấu hình có sẵn,
không cái nào). Nhưng `simple` tách từ tiếng Việt **đúng** — theo khoảng trắng,
hạ chữ thường, giữ nguyên dấu. Thứ còn thiếu chỉ là **bỏ dấu**, và đó đúng là
việc của `unaccent`. Toàn bộ căn cứ ở `test_821`.

## `plainto_tsquery` nối các từ bằng AND

Nên một từ vắng mặt làm cả câu trượt — **giống hệt** triệu chứng thiếu dấu. Đó
là cái bẫy đã dính khi viết `test_821` (`"tinh tien theo token"`), và nó là lý
do hàm này trả về **số đoạn khớp** chứ không chỉ danh sách: người gọi phải phân
biệt được "không có tài liệu nào" với "câu hỏi quá hẹp".
"""
from __future__ import annotations

import unicodedata

from sqlalchemy import func, or_, select

from apps.chatltt.tables import ChatlttDoan

#: Tên hàm bọc `unaccent`, khai ở migration `b8c31f6e9d24`. Một chỗ khai, một
#: chỗ dùng — hai bên lệch tên thì hỏng lặng lẽ vào đúng lúc không ai nhìn.
HAM_BO_DAU = "f_unaccent"
CAU_HINH = "simple"

#: Trần số đoạn trả về. Năm đoạn ~1.350 token — vừa ngân sách một lượt.
SO_DOAN_MAC_DINH = 5


def nen_tang(db) -> str:
    """`"postgresql"` hay tên phương ngữ khác. Người gọi PHẢI đọc được cái này."""
    return db.get_bind().dialect.name


def _bo_dau_python(s: str) -> str:
    """⛔ CHỈ dùng cho đường không-phải-Postgres. Nó **khác** `unaccent` thật.

    Đo 06/09: Postgres ánh xạ `đ → d`, `NFD` thì không (`đ` là ký tự riêng, chứ
    không phải `d` + dấu tổ hợp). Ba trên sáu mẫu tiếng Việt thường lệch nhau —
    `"Đầu tư"`, `"đồng"`, `"điện thoại"`. Nên hàm này **không** tái hiện được
    hành vi thật, và không được dùng để kết luận gì về chất lượng tìm kiếm.
    """
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    # Vá đúng một khác biệt đã đo, để đường phụ ít lệch hơn — nhưng nó vẫn là
    # đường phụ: một bản vá theo danh sách không bao giờ đuổi kịp một từ điển.
    return s.replace("đ", "d").replace("Đ", "D").lower()


def _tim_postgres(db, *, user_id, conversation_id, cau_hoi, so_doan):
    hoi = func.plainto_tsquery(
        CAU_HINH, func.public.f_unaccent(cau_hoi))
    vec = func.to_tsvector(CAU_HINH, getattr(func, HAM_BO_DAU)(ChatlttDoan.noi_dung))
    return db.execute(
        select(ChatlttDoan, func.ts_rank(vec, hoi).label("diem"))
        .where(ChatlttDoan.user_id == user_id,
               ChatlttDoan.conversation_id == conversation_id,
               vec.op("@@")(hoi))
        .order_by(func.ts_rank(vec, hoi).desc(), ChatlttDoan.thu_tu)
        .limit(so_doan)
    ).all()


def _tim_chuoi_con(db, *, user_id, conversation_id, cau_hoi, so_doan):
    """⛔ KHÔNG phải tìm kiếm. Xem `_bo_dau_python`."""
    tu = [t for t in _bo_dau_python(cau_hoi).split() if t]
    if not tu:
        return []
    hang = db.execute(
        select(ChatlttDoan)
        .where(ChatlttDoan.user_id == user_id,
               ChatlttDoan.conversation_id == conversation_id)
        .order_by(ChatlttDoan.thu_tu)
    ).scalars().all()
    ra = []
    for d in hang:
        kho = _bo_dau_python(d.noi_dung)
        # AND giua cac tu — cung quy uoc voi `plainto_tsquery`, de phep kiem ACL
        # khong vo tinh dua tren mot quy uoc khac.
        if all(t in kho for t in tu):
            ra.append((d, float(sum(kho.count(t) for t in tu))))
    ra.sort(key=lambda x: (-x[1], x[0].thu_tu))
    return ra[:so_doan]


def tim(db, *, user_id: str, conversation_id: str, cau_hoi: str,
        so_doan: int = SO_DOAN_MAC_DINH) -> list:
    """Các đoạn khớp `cau_hoi`, trong phạm vi **một** hội thoại của **một** chủ.

    ⛔ Lọc theo **cả hai** `user_id` và `conversation_id`. Lọc riêng hội thoại là
       đủ *hôm nay*, nhưng nó vay một bất biến ở bảng bên cạnh — cùng luật đã
       ghi ở `kho_tep.cua_hoi_thoai`.

    Trả về `[(ChatlttDoan, điểm)]`, xếp giảm dần theo điểm rồi theo `thu_tu`.
    """
    if not (cau_hoi or "").strip():
        return []
    so_doan = max(1, min(int(so_doan), 50))
    ham = _tim_postgres if nen_tang(db) == "postgresql" else _tim_chuoi_con
    return [tuple(x) for x in ham(db, user_id=user_id,
                                  conversation_id=conversation_id,
                                  cau_hoi=cau_hoi, so_doan=so_doan)]


def trich_dan(doan) -> dict:
    """Bộ ba mà bước 5 đòi: `(tep_id, doan_id, trang)`.

    ⭐ `trang = 0` nghĩa là **không biết** (tệp không có khái niệm trang), không
       phải "trang đầu" — giao diện phải hiện được khác biệt đó, nếu không thì
       một trích dẫn `.txt` sẽ trỏ vào "trang 0" và trông như một lỗi.
    """
    return {"tep_id": doan.tep_id, "doan_id": doan.id,
            "trang": int(doan.trang or 0), "thu_tu": int(doan.thu_tu)}

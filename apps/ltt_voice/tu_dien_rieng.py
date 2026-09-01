r"""
tu_dien_rieng.py — từ điển phát âm riêng của từng khách.

## Vì sao module này tồn tại, và vì sao nó đến muộn

`text_pipeline.chuan_hoa(tu_dien_rieng=...)` và `tu_dien.ap_dung(them=...)` đã
nhận tham số này **từ lâu**, qua ba tầng. Không ai truyền nó, nên cả chuỗi ấy
chưa từng chạy một lần nào — một đường ống dựng xong rồi để không.

⭐ Và `tu_dien.py` đã vạch sẵn ranh giới: *"Đây là bảng CHUNG cho mọi khách. Từ
   điển riêng của một người (tên công ty, tên nhân vật) đi qua tham số `them=`
   — nó không được lẫn vào đây."* Tệp này là đầu kia của câu đó.

## Vì sao khách cần nó, nói bằng một ca thật

Upstream #168: engine đọc `ch` thành `tr` ở một số từ. Từ phổ thông thì bảng
chung lo được. Nhưng **tên riêng** thì không ai đoán trước: tên công ty, tên
nhân vật trong truyện dài, tên sản phẩm. Chúng lặp lại trong **mọi** kịch bản
của chính khách ấy.

⛔ Không có chỗ sửa thì khách phải **gõ sai chính tả trong kịch bản** để ép
   engine đọc đúng — và bản chép ấy sẽ đi vào tài liệu của họ, vào phụ đề, vào
   mọi chỗ khác. Ta đẩy một khuyết tật của mình sang bản gốc của khách.

## 🔴 BA GIỚI HẠN, và cả ba là để nó không thành một bề mặt tấn công

**① Trần số mục.** Mỗi phép thay là một lượt quét toàn văn bản. Một từ điển
   không giới hạn là một cách để một tài khoản làm chậm worker cho mọi người.

**② Trần độ dài.** `tu` ngắn hơn `thay`, và cả hai đều bị chặn — một mục
   `thay` dài mười nghìn ký tự làm một câu ngắn nở thành một job dài.

**③ KHÔNG regex, không ký tự đặc biệt.** `tu_dien._mau` đã `re.escape`, nên
   không có đường tiêm biểu thức. Nhưng ta vẫn từ chối ở cửa vào: một chuỗi
   trông như regex trong danh sách của khách là một thứ họ sẽ tưởng là chạy.
"""
from __future__ import annotations

import re

from platform_core.i18n import _ as _t

from .features import LoiGiongNoi

#: Trần số mục mỗi khách. Con số này là một LỰA CHỌN, không phải một số đo —
#: nói ra để người sau không phải cãi với một hằng số tưởng là kết quả đo.
#: Nới nó thì đo thời gian `chuan_hoa` trên một văn bản 1.500 ký tự trước.
TRAN_SO_MUC = 100

TRAN_TU = 80
TRAN_THAY = 160
TRAN_GHI_CHU = 200

#: Chỉ chữ, số, khoảng trắng và vài dấu nối. Không dấu ngoặc, không `\`, không
#: `*+?|` — xem giới hạn ③ ở docstring.
_CHU_HOP_LE = re.compile(r"^[\w\s.\-']+$", re.UNICODE)


def _kiem(tu: str, thay: str) -> tuple:
    tu = (tu or "").strip()
    thay = (thay or "").strip()
    if not tu or not thay:
        raise LoiGiongNoi(_t("Cần cả từ cần sửa và cách đọc thay thế."))
    if len(tu) > TRAN_TU or len(thay) > TRAN_THAY:
        raise LoiGiongNoi(_t(
            "Từ tối đa {a} ký tự, cách đọc tối đa {b} ký tự."
        ).format(a=TRAN_TU, b=TRAN_THAY))
    for s in (tu, thay):
        if not _CHU_HOP_LE.match(s):
            raise LoiGiongNoi(_t(
                "Chỉ dùng chữ, số, khoảng trắng và dấu . - ' — không dùng ký "
                "tự đặc biệt."))
    if tu.lower() == thay.lower():
        # Một mục thay chính nó là một mục không làm gì, và nó chiếm một suất
        # trong trần. Từ chối rõ ràng thay vì nhận rồi im.
        raise LoiGiongNoi(_t("Từ và cách đọc thay thế giống hệt nhau."))
    return tu, thay


def danh_sach(db, owner_id: str) -> list:
    from sqlalchemy import select

    from .tables import VoiceTuDien
    return list(db.execute(
        select(VoiceTuDien)
        .where(VoiceTuDien.owner_id == str(owner_id))
        .order_by(VoiceTuDien.tu)
    ).scalars().all())


def nhu_dict(db, owner_id: str) -> dict:
    """Dạng mà `tu_dien.ap_dung(them=...)` nhận.

    ⚠️ Trả `{}` khi không có mục nào — KHÔNG trả `None`. `ap_dung` xử lý được
       cả hai, nhưng một hàm trả hai kiểu là một chỗ để nơi gọi quên kiểm.
    """
    return {g.tu: g.thay for g in danh_sach(db, owner_id)}


def them(db, owner_id: str, *, tu: str, thay: str, ghi_chu: str = ""):
    from sqlalchemy import func, select

    from .tables import VoiceTuDien

    tu, thay = _kiem(tu, thay)
    so = db.execute(
        select(func.count()).select_from(VoiceTuDien)
        .where(VoiceTuDien.owner_id == str(owner_id))
    ).scalar_one()

    cu = db.execute(
        select(VoiceTuDien).where(VoiceTuDien.owner_id == str(owner_id),
                                  VoiceTuDien.tu == tu)
    ).scalars().first()
    if cu is not None:
        # SỬA, không phải lỗi trùng. Khách gõ lại cùng một từ gần như luôn có
        # nghĩa "đổi cách đọc", và bắt họ xoá rồi thêm lại là một bước thừa.
        cu.thay = thay
        cu.ghi_chu = (ghi_chu or "")[:TRAN_GHI_CHU]
        db.flush()
        return cu

    if so >= TRAN_SO_MUC:
        raise LoiGiongNoi(_t(
            "Từ điển đã đạt {n} mục — giới hạn hiện tại. Xoá bớt mục cũ trước."
        ).format(n=TRAN_SO_MUC))

    m = VoiceTuDien(owner_id=str(owner_id), tu=tu, thay=thay,
                    ghi_chu=(ghi_chu or "")[:TRAN_GHI_CHU])
    db.add(m)
    db.flush()
    return m


def xoa(db, owner_id: str, muc_id: int) -> bool:
    from sqlalchemy import select

    from .tables import VoiceTuDien
    m = db.execute(
        select(VoiceTuDien).where(VoiceTuDien.id == int(muc_id),
                                  VoiceTuDien.owner_id == str(owner_id))
    ).scalars().first()
    if m is None:
        return False
    db.delete(m)
    return True

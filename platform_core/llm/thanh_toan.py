"""
thanh_toan.py — thu tiền một lượt gọi model. Giữ chỗ → chạy → quyết toán. (H38)

⭐ MẶC ĐỊNH vẫn là **C1** (làm tròn LÊN mỗi lượt gọi). **C3** — tích luỹ phần
   lẻ, chỉ thu phần NGUYÊN — đã cài xong và bật bằng `LTT_TINH_TIEN_TICH_LUY=1`.

   Credit là số nguyên (`credit.tru()` nhận `int`), còn một lượt gọi điển hình
   tốn **0,3 credit**. Phần lẻ được giữ ở `users.mcredit_du` và cộng vào lượt
   sau, nên khách trả **đúng bảng giá** chứ không trả sàn.

   ⚠️ **Trước đây là C1** — làm tròn LÊN mỗi lượt gọi, tối thiểu 1 credit. Chính
   docstring cũ ở đây đã thừa nhận cái giá của nó: *"lượt gọi nhỏ trả nhiều hơn
   giá niêm yết, tới ~3,3 lần"*. Đo lại 05/09 thì nó lớn hơn thế:

     - lượt agentic 4 vòng : **0,92 credit thật → thu 4** (4,0×)
     - hội thoại 20 lượt ngắn: **3,13 credit thật → thu 20** (6,4×)
     - chat rất ngắn: ta thu **1**, cùng model trên OpenRouter là **0,21**
       ⇒ ta **đắt hơn giá bán lẻ 4,84 lần**

   Lý lẽ và số liệu đầy đủ: `docs/CHATLTT_V3/04_ADR_R2B_TINH_TIEN_LUOT.md`.

   ⛔ **Bảng giá KHÔNG đổi** (50 / 10 / 400 credit/1M). Neo thị trường đo lại
   hôm nay vẫn đúng: `qwen/qwen3.8-27b` = 110,5 / 789, ta ở 45 %/51 %. Thứ hỏng
   là **ranh giới làm tròn**, không phải đơn giá — và trộn hai chuyện đó là cách
   chắc chắn để không ai còn biết giá thật là bao nhiêu.

   🔑 C3 là **đề xuất chờ chốt**, không phải bản sửa đã duyệt: nó đổi
   `toi_thieu_moi_luot_credit` — một điều khoản CÔNG BỐ. Nên nó opt-in.

⭐ BA NGUYÊN HÀM ĐỀU CÓ SẴN, KHÔNG DỰNG SỔ TIỀN THỨ HAI:

     credit.giu_cho    giữ trước khi chạy — hết double-spend, có khoá theo user
     credit.quyet_toan chốt sau khi xong  — **không bao giờ thu quá phần đã giữ**
     credit.hoan       hoàn đủ khi hỏng   — idempotent theo job

   Module này chỉ dịch *token* thành *credit* rồi gọi ba hàm đó. Không ghi bút
   toán, không đụng số dư. `public_api/costing.py` nói đúng: **sổ cái là sự thật
   tính tiền**; ở đây chỉ là phép quy đổi.

⛔ KHÔNG ĐO ĐƯỢC THÌ KHÔNG THU. `usage` thiếu ⇒ `gia_token.tinh()` ném lỗi, và
   `quyet_toan_hoac_hoan()` **hoàn đủ rồi ghi cảnh báo**. Thu tiền mà không có
   bằng chứng còn tệ hơn mất một ít tiền, và nó phải hiếm — llama-server luôn trả
   `usage`. Nếu cảnh báo đó xuất hiện thường xuyên thì có thứ khác đang hỏng.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from platform_core import credit
from platform_core.llm import gia_token
from platform_core.llm.cong_vlm import SuDung

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class KetQuaThu:
    """Kết quả thu tiền một lượt, đủ để hiện lên hoá đơn và giải thích được."""

    da_giu_credit: int
    thu_credit: int
    hoan_credit: int
    chi_phi_mcredit: int
    phien_ban_gia: str
    #: `False` khi không đo được `usage` ⇒ đã hoàn đủ, không thu gì.
    da_do_duoc: bool = True

    def as_dict(self) -> dict:
        return {"da_giu_credit": self.da_giu_credit,
                "thu_credit": self.thu_credit,
                "hoan_credit": self.hoan_credit,
                "chi_phi_mcredit": self.chi_phi_mcredit,
                "phien_ban_gia": self.phien_ban_gia,
                "da_do_duoc": self.da_do_duoc}


def giu_cho_luot(db, *, user_id: str, request_id: str,
                 token_vao_uoc: int, max_tokens: int) -> int:
    """Giữ chỗ TRƯỚC khi gọi model. Trả về số credit đã giữ.

    Ném `credit.ThieuCreditError` khi không đủ số dư — và đó là **chốt chặn đúng
    chỗ**: không đủ tiền thì không đốt GPU.

    ⛔ Trần ước CAO (`gia_token.uoc_tran` giả định không có cache và sinh đủ
       `max_tokens`). Giữ thiếu thì khách tiêu quá số dư; giữ dư thì hoàn lại.
    """
    if not request_id:
        raise ValueError("thieu request_id — no la khoa cua giu cho va quyet toan")
    tran = gia_token.uoc_tran(token_vao_uoc=token_vao_uoc, max_tokens=max_tokens)
    so = tran.tong_credit_lam_tron_len
    credit.giu_cho(db, user_id, so, request_id)
    return so


#: Cờ BẬT C3 (tích luỹ phần lẻ). **Mặc định TẮT ⇒ vẫn là C1.**
#:
#: ⭐ Vì sao opt-in chứ không phải mặc định, dù C1 đã đo được là thu thừa:
#:    đây là **quyết định giá**, không phải một bản sửa lỗi. Nó đổi
#:    `toi_thieu_moi_luot_credit` — một **điều khoản công bố** qua
#:    `public_api/dieu_khoan.py`. Đổi điều khoản là việc của chủ dự án, và
#:    `04_ADR_R2B_TINH_TIEN_LUOT.md` ghi rõ nó đang ở trạng thái ĐỀ XUẤT.
#:
#: 🔑 Bật bằng một biến môi trường, không cần sửa mã:
#:
#:        LTT_TINH_TIEN_TICH_LUY=1
CO_TICH_LUY = "LTT_TINH_TIEN_TICH_LUY"

#: Tên cũ, giữ để không ai phải sửa hai chỗ khi đọc tài liệu cũ.
CO_SAN_MOI_LUOT = CO_TICH_LUY


def _tich_luy() -> bool:
    import os
    return (os.environ.get(CO_TICH_LUY) or "").strip().lower() in ("1", "true", "on")


def _san_moi_luot() -> bool:
    """C1 là mặc định; C3 chỉ chạy khi được bật rõ ràng."""
    return not _tich_luy()


#: Ngưỡng cảnh báo phần lẻ. Bình thường `mcredit_du` < 1.000; lớn hơn nhiều lần
#: nghĩa là quyết toán liên tục bị **cap ở mức đã giữ** — tức giữ chỗ đang thiếu.
TRAN_CANH_BAO_DU_MCREDIT = 5_000


def quyet_toan_luot(db, *, user_id: str, request_id: str,
                    su_dung: SuDung) -> KetQuaThu:
    """Chốt tiền sau khi lượt gọi xong.

    Ném `gia_token.KhongDoDuocError` khi thượng nguồn không trả `usage`. Bên gọi
    nên dùng `quyet_toan_hoac_hoan()` thay vì tự bắt.
    """
    chi_phi = gia_token.tinh(su_dung)
    if _san_moi_luot():                                  # C1 — đường lùi
        thu = chi_phi.tong_credit_lam_tron_len
        kq = credit.quyet_toan(db, user_id, request_id, thu)
    else:                                                # C3 — mặc định
        kq = _quyet_toan_tich_luy(db, user_id=user_id, request_id=request_id,
                                  chi_phi_mcredit=chi_phi.tong_mcredit)
    return KetQuaThu(
        da_giu_credit=kq.held_credit,
        thu_credit=kq.charged_credit,
        hoan_credit=kq.adjustment,
        chi_phi_mcredit=chi_phi.tong_mcredit,
        phien_ban_gia=chi_phi.phien_ban_gia,
    )


def _quyet_toan_tich_luy(db, *, user_id: str, request_id: str,
                         chi_phi_mcredit: int):
    """**C3** — cộng phần lẻ vào `users.mcredit_du`, chỉ thu phần NGUYÊN.

        du_moi = du_cu + chi_phi - (so credit THAT SU thu) * 1000

    ⭐ Trừ theo **số thật sự thu**, không theo số đề nghị. `credit.quyet_toan`
       cap ở mức đã giữ; nếu bị cap thì phần chưa thu **ở lại** trong `du` và
       lượt sau thu tiếp — thay vì bốc hơi.

    🔴 Hai chốt chặn, và cả hai đều là chuyện tiền:

    1. **Phát lại không được cộng `du` lần hai.** `credit.quyet_toan` idempotent
       theo `request_id`, nên nó trả kết quả cũ; nhưng `du` thì không tự biết.
       Hỏi `credit.da_quyet_toan()` trước.
    2. **Khoá hàng user trước khi đọc `du`.** Đọc-rồi-ghi có một khe, và hai lượt
       song song của cùng một user lọt vừa vào đó sẽ cùng đọc `du` cũ rồi cùng
       ghi đè — mất một phần lẻ, tức mất doanh thu im lặng.
    """
    from platform_core.models import User

    if credit.da_quyet_toan(db, request_id):
        # Phát lại: `quyet_toan` trả kết quả cũ. `actual=0` không đổi gì —
        # nó early-return trước khi đọc tới con số này.
        return credit.quyet_toan(db, user_id, request_id, 0)

    credit.khoa_user(db, user_id)
    u = db.get(User, str(user_id))
    du = int(getattr(u, "mcredit_du", 0) or 0) if u is not None else 0

    tong = du + max(0, int(chi_phi_mcredit))
    de_nghi = tong // gia_token.MCREDIT_MOI_CREDIT
    kq = credit.quyet_toan(db, user_id, request_id, de_nghi)

    if u is not None:
        con = tong - kq.charged_credit * gia_token.MCREDIT_MOI_CREDIT
        u.mcredit_du = max(0, con)
        # ⛔ `flush` chứ không đợi bên gọi `commit`. Không flush thì giá trị chỉ
        #    nằm trong bộ nhớ phiên; một truy vấn khác trong **cùng** transaction
        #    vẫn đọc ra số cũ — và phần lẻ vừa cộng biến mất mà không ai báo.
        db.flush()
        if u.mcredit_du >= TRAN_CANH_BAO_DU_MCREDIT:
            # Không phải lỗi của phép cộng — là dấu hiệu GIỮ CHỖ đang thiếu, nên
            # quyết toán bị cap liên tục. Nói ra để có người đi xem `uoc_tran`.
            log.warning(
                "phan le tich luy cao bat thuong: user=%s du=%s mcredit "
                "(nghi giu cho thieu, quyet toan bi cap)", user_id[:8], u.mcredit_du)
    return kq


def hoan_luot(db, *, user_id: str, request_id: str) -> None:
    """Hoàn đủ phần đã giữ. Dùng khi máy B bận, khi lỗi, khi khách huỷ.

    ⛔ **`BanError` phải đi đường này.** Bận không phải lỗi của khách, và cũng
       không phải lỗi của provider — không ai được trả tiền cho nó.
    """
    credit.hoan(db, user_id, request_id)


def quyet_toan_hoac_hoan(db, *, user_id: str, request_id: str,
                         su_dung: SuDung) -> KetQuaThu:
    """Chốt tiền; nếu không đo được thì **hoàn đủ và ghi cảnh báo**.

    Đây là hàm bên gọi nên dùng. Nó làm cho việc đúng trở thành việc dễ.
    """
    try:
        return quyet_toan_luot(db, user_id=user_id, request_id=request_id,
                               su_dung=su_dung)
    except gia_token.KhongDoDuocError:
        da_giu = credit.so_da_giu(db, request_id)
        hoan_luot(db, user_id=user_id, request_id=request_id)
        # Cảnh báo, không phải info: nó nghĩa là ta vừa đốt GPU mà không có bằng
        # chứng để thu tiền. Hiếm thì chấp nhận được; thường xuyên là có lỗi khác.
        log.warning(
            "khong do duoc usage — hoan du va KHONG thu. request=%s user=%s giu=%s",
            request_id[:8], user_id[:8], da_giu)
        return KetQuaThu(da_giu_credit=da_giu, thu_credit=0, hoan_credit=da_giu,
                         chi_phi_mcredit=0,
                         phien_ban_gia=gia_token.PHIEN_BAN_GIA,
                         da_do_duoc=False)


# ── Mã một lượt gọi, dùng làm khoá giữ chỗ/quyết toán ────────────────────────

def _tran_ma() -> int:
    """Đọc trần độ dài từ CHÍNH cột sẽ lưu nó, không gõ lại con số.

    Gõ lại `36` ở đây thì ngày ai đó nới cột lên 64, chỗ này vẫn kẹp 36 và không
    ai biết vì sao mã bị cắt ngắn.
    """
    from platform_core.models import CreditEntry

    return int(CreditEntry.__table__.c.job_id.type.length or 36)


def ma_luot(nguon: str) -> str:
    """Sinh mã cho một lượt gọi **không phải job**, đủ ngắn để lưu được.

    🔴 LỖI THẬT, VÀ NÓ CHỈ HIỆN RA TRÊN PRODUCTION. `credit_entries.job_id` là
       `VARCHAR(36)`. **SQLite không ép độ dài, PostgreSQL thì có** — nên hai cửa
       thu tiền chạy sạch qua toàn bộ bộ test rồi trả `500` ngay lượt gọi thật
       đầu tiên, ngày 23/08:

           stream:<32 hex>   39 ky tu  -> StringDataRightTruncation
           chat:<uuid4 36 ky tu> 41 ky tu  -> cung the

       Bài học không phải "đếm ký tự cẩn thận hơn", mà là: **một ràng buộc chỉ
       tồn tại ở production là một ràng buộc chưa được test**. `test_273` neo nó
       bằng cách đo thẳng, không cần PostgreSQL.

    ⛔ `nguon` tối đa 3 ký tự **ASCII**. Dài hơn thì ném ngay tại chỗ — cắt lặng
       lẽ sẽ làm hai nguồn khác nhau đụng mã nhau, và đụng mã ở đây nghĩa là
       **quyết toán nhầm lượt của người khác**.

    ⚠️ ASCII chứ không phải `isalnum()`. `"quá"` là ba **ký tự** nhưng bốn
       **byte**; PostgreSQL đếm ký tự nên nó lọt, còn một kho khác đếm byte thì
       không. Chặn ở ASCII là bỏ hẳn cả lớp nhầm lẫn đó thay vì phải nhớ kho nào
       đếm kiểu nào.
    """
    import uuid

    nguon = (nguon or "").strip()
    if not nguon or len(nguon) > 3 or not nguon.isascii() or not nguon.isalnum():
        raise ValueError(
            f"`nguon` phai la 1-3 ky tu chu/so, nhan duoc {nguon!r}")
    ma = f"{nguon}:{uuid.uuid4().hex}"
    tran = _tran_ma()
    if len(ma) > tran:                      # pragma: no cover - chan phong xa
        raise ValueError(f"ma dai {len(ma)} > tran {tran}: {ma}")
    return ma

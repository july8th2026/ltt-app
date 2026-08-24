"""
thanh_toan.py — thu tiền một lượt gọi model. Giữ chỗ → chạy → quyết toán. (H38)

⭐ PHƯƠNG ÁN **C1**, chốt 2026-08-22: **làm tròn LÊN credit nguyên mỗi lượt gọi.**

   Credit là số nguyên (`credit.tru()` nhận `int`), còn một lượt gọi điển hình
   tốn **0,3 credit**. C1 giải bằng cách làm tròn lên — đơn giản, không đụng sổ
   cái, dùng được ngay.

   ⚠️ **Cái giá của C1, phải nói ra chứ không giấu:** lượt gọi nhỏ trả **nhiều hơn
   giá niêm yết**, tới ~3,3 lần với lượt 0,3 credit. Vì thế `gia_token.bang_gia()`
   khai thẳng `toi_thieu_moi_luot_credit = 1` và giải thích trong `ghi_chu`.
   Một khách gọi nhiều sẽ tự tính ra trong vòng một ngày — thà họ đọc được từ
   trước còn hơn tự phát hiện.

   (Phương án C2 — sổ tích luỹ phần lẻ — vẫn để ngỏ. Nó chỉ đụng module này,
   **không** đụng `gia_token.py`. Ranh giới đó là có chủ ý.)

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


def quyet_toan_luot(db, *, user_id: str, request_id: str,
                    su_dung: SuDung) -> KetQuaThu:
    """Chốt tiền sau khi lượt gọi xong.

    Ném `gia_token.KhongDoDuocError` khi thượng nguồn không trả `usage`. Bên gọi
    nên dùng `quyet_toan_hoac_hoan()` thay vì tự bắt.
    """
    chi_phi = gia_token.tinh(su_dung)                    # C1: làm tròn LÊN
    thu = chi_phi.tong_credit_lam_tron_len
    kq = credit.quyet_toan(db, user_id, request_id, thu)
    return KetQuaThu(
        da_giu_credit=kq.held_credit,
        thu_credit=kq.charged_credit,
        hoan_credit=kq.adjustment,
        chi_phi_mcredit=chi_phi.tong_mcredit,
        phien_ban_gia=chi_phi.phien_ban_gia,
    )


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

"""
gia_token.py — giá token của model nhà, MỘT chỗ duy nhất. (H38)

⭐ CHỐT 2026-08-22 (chủ dự án duyệt), đơn vị **credit trên 1 triệu token**:

        Token vào (phải prefill thật)   ......   50 credit / 1M
        Token vào lấy lại từ cache      ......   10 credit / 1M
        Token ra (kể cả reasoning)      ......  400 credit / 1M

   Neo giá: **cùng model này trên OpenRouter là 105 / 789 credit/1M**
   ($0,40 / $3,00 ở tỉ giá 26.300đ/USD, 1 credit = 100đ). Ta rẻ hơn ~50 %.
   Chi phí điện biên đo được: ~3 credit/1M vào, ~50 credit/1M ra
   (358,65 W đo trên máy B, giả định 3.000đ/kWh) ⇒ lãi gộp ~16× / ~8×.

⛔ MỘT CHỖ, KHÔNG HAI. Cùng nguyên tắc `billing_math.py` đã chốt cho tỉ giá tiền:
   *"tính tiền hai chỗ là tiền lệch hai chỗ"*. Và cùng nguyên tắc
   `public_api/costing.py`: không dựng động cơ tính giá thứ hai.

⭐ VÌ SAO ĐƠN VỊ TRONG NÀY LÀ **MILLI-CREDIT**, KHÔNG PHẢI CREDIT.

   Credit là **số nguyên** (`credit.tru()` nhận `int`), nhưng một lượt gọi LLM
   điển hình — 2.000 token vào + 500 token ra — tốn **0,3 credit**. Ảnh và video
   không gặp chuyện này vì một job tốn vài credit trở lên.

   Nên module này tính bằng **milli-credit = 1/1.000 credit = 0,1đ**, **toàn bộ
   bằng số nguyên, không dùng float** — dấu phẩy động trong đường tiền là cách
   chắc chắn nhất để hai lần cộng ra hai kết quả.

   Việc **làm tròn về credit nguyên** là của tầng quyết toán, KHÔNG phải của đây.
   Đó là ranh giới có chủ ý: đổi cách làm tròn không được phép đụng vào bảng giá.

⛔ KHÔNG ĐOÁN SỐ ĐỂ TÍNH TIỀN. `SuDung.dang_tin=False` nghĩa là thượng nguồn không
   trả `usage`. Khi đó module này **ném lỗi** thay vì trả 0 — 0 token không có
   nghĩa là miễn phí, và một hoá đơn 0đ âm thầm là một lỗ hổng doanh thu im lặng.
"""
from __future__ import annotations

from dataclasses import dataclass

from platform_core.llm.cong_vlm import SuDung

#: Số milli-credit trong một credit. Đừng đổi — `credit.tru()` nhận credit nguyên.
MCREDIT_MOI_CREDIT = 1_000

#: ⭐ BẢNG GIÁ, đơn vị **credit trên 1.000.000 token**. Đây là ba con số duy nhất
#:   được phép đại diện cho giá model nhà trong toàn bộ mã nguồn.
GIA_VAO_MOI_CREDIT_1M = 50
GIA_VAO_CACHE_CREDIT_1M = 10
GIA_RA_CREDIT_1M = 400

#: Nhãn phiên bản giá, đóng dấu lên báo giá và lên job. `public_api/pricing.py`
#: nói rõ vì sao: *"reconciling a charge months later then means reading two facts
#: that were both written at the time"*. Đổi giá ⇒ **nhãn mới**, không sửa nhãn cũ.
PHIEN_BAN_GIA = "ltt-vlm-2026-08-22"

_MOT_TRIEU = 1_000_000


class KhongDoDuocError(ValueError):
    """Thượng nguồn không trả `usage` ⇒ không có căn cứ tính tiền.

    Bên gọi **phải** xử lý rõ ràng: hoặc hoàn lại phần giữ chỗ, hoặc ghi một sự
    kiện để người vận hành xem. Tuyệt đối không im lặng tính 0.
    """


@dataclass(frozen=True)
class ChiPhi:
    """Chi phí một lượt gọi, tách theo từng khoản để hoá đơn giải thích được."""

    vao_moi_mcredit: int = 0
    vao_cache_mcredit: int = 0
    ra_mcredit: int = 0
    phien_ban_gia: str = PHIEN_BAN_GIA

    @property
    def tong_mcredit(self) -> int:
        return self.vao_moi_mcredit + self.vao_cache_mcredit + self.ra_mcredit

    @property
    def tong_credit_lam_tron_len(self) -> int:
        """Số credit nguyên, **làm tròn LÊN**.

        Dùng cho *giữ chỗ* (giữ thiếu thì khách tiêu quá số dư) và cho phương án
        C1 (ngưỡng tối thiểu 1 credit mỗi lời gọi). **Không** dùng cho quyết toán
        nếu đã chọn C2 — ở C2, phần lẻ được cộng dồn chứ không làm tròn lên từng lượt.
        """
        m = self.tong_mcredit
        return -(-m // MCREDIT_MOI_CREDIT)      # ceil bằng số nguyên

    def as_dict(self) -> dict:
        return {"vao_moi_mcredit": self.vao_moi_mcredit,
                "vao_cache_mcredit": self.vao_cache_mcredit,
                "ra_mcredit": self.ra_mcredit,
                "tong_mcredit": self.tong_mcredit,
                "phien_ban_gia": self.phien_ban_gia}


def _mcredit(so_token: int, gia_credit_1m: int) -> int:
    """`so_token` token ở giá `gia_credit_1m` credit/1M ⇒ bao nhiêu milli-credit.

    Toàn số nguyên. Làm tròn XUỐNG ở đây là đúng chiều: phần lẻ dưới 0,0001đ
    nghiêng về phía khách, và nó cộng dồn ở tầng trên chứ không mất đi.
    """
    if so_token <= 0 or gia_credit_1m <= 0:
        return 0
    return (int(so_token) * int(gia_credit_1m) * MCREDIT_MOI_CREDIT) // _MOT_TRIEU


def tinh(su_dung: SuDung) -> ChiPhi:
    """Chi phí thật của một lượt đã chạy xong.

    ⛔ Ném `KhongDoDuocError` khi `su_dung.dang_tin` là `False`.
    """
    if not su_dung.dang_tin:
        raise KhongDoDuocError(
            "thuong nguon khong tra `usage` — khong co can cu tinh tien")

    return ChiPhi(
        vao_moi_mcredit=_mcredit(su_dung.token_vao_moi, GIA_VAO_MOI_CREDIT_1M),
        vao_cache_mcredit=_mcredit(su_dung.token_vao_cache, GIA_VAO_CACHE_CREDIT_1M),
        ra_mcredit=_mcredit(su_dung.token_ra, GIA_RA_CREDIT_1M),
    )


def uoc_tran(*, token_vao_uoc: int, max_tokens: int) -> ChiPhi:
    """Trần chi phí để **giữ chỗ trước khi chạy**.

    ⛔ Cố ý ước CAO: giả định **không có token nào lấy từ cache**, và giả định
    model sinh đủ `max_tokens`. Giữ thiếu thì khách tiêu quá số dư — chiều sai đó
    đắt hơn nhiều so với việc giữ dư rồi hoàn lại.

    Phần dư trả về cho khách ở `credit.hoan()` sau khi quyết toán.
    """
    return ChiPhi(
        vao_moi_mcredit=_mcredit(max(0, int(token_vao_uoc)), GIA_VAO_MOI_CREDIT_1M),
        ra_mcredit=_mcredit(max(0, int(max_tokens)), GIA_RA_CREDIT_1M),
    )


def bang_gia() -> dict:
    """Bảng giá để phơi ra `/v1/models` và tài liệu API.

    ⭐ Phơi giá ra API là có chủ ý: khách xây bot cần tính được chi phí **trước**
    khi gọi. Và nó buộc ta chỉ có một nguồn giá — trang tài liệu không thể lệch
    với thứ thật sự tính tiền, vì cả hai đọc cùng hàm này.
    """
    return {
        "don_vi": "credit / 1.000.000 token",
        "phien_ban_gia": PHIEN_BAN_GIA,
        "token_vao": GIA_VAO_MOI_CREDIT_1M,
        "token_vao_cache": GIA_VAO_CACHE_CREDIT_1M,
        "token_ra": GIA_RA_CREDIT_1M,
        # ⛔ Nói thẳng cả ba điều, đừng để khách phát hiện sau khi nhận hoá đơn.
        #    Cái thứ ba là quan trọng nhất: nó làm lượt gọi NHỎ đắt hơn giá niêm
        #    yết, và một khách gọi nhiều sẽ tự tính ra trong vòng một ngày.
        "lam_tron": "len credit nguyen, moi luot goi",
        "toi_thieu_moi_luot_credit": 1,
        "ghi_chu": ("Token reasoning tinh nhu token ra. "
                    "Token vao lay lai tu cache tinh 20% gia token vao. "
                    "Moi luot goi lam tron LEN credit nguyen, toi thieu 1 credit "
                    "(100d) — nen luot goi rat nho tra nhieu hon gia niem yet."),
    }

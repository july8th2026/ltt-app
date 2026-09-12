"""
gia_token.py — giá token của model nhà, MỘT chỗ duy nhất. (H38)

⭐ CHỐT 2026-08-22 (chủ dự án duyệt) cho **LTT-3.8**, đơn vị **credit trên 1
   triệu token**:

        Token vào (phải prefill thật)   ......   50 credit / 1M
        Token vào lấy lại từ cache      ......   10 credit / 1M
        Token ra (kể cả reasoning)      ......  400 credit / 1M

   Neo giá: **cùng model này trên OpenRouter là 105 / 789 credit/1M**
   ($0,40 / $3,00 ở tỉ giá 26.300đ/USD, 1 credit = 100đ). Ta rẻ hơn ~50 %.

⭐ TỪ 2026-09-12 (D07, dual-model 2.5): **HAI MODEL, HAI BẢNG GIÁ, MỘT MODULE.**

        ltt-3.8   50 / 10 / 400   nhãn `ltt-vlm-2026-08-22`   (RTX 3090)
        ltt-3.5   13 /  3 /  20   nhãn `ltt-3.5-2026-09-11`   (RTX 5060 Ti)

   LTT-3.5 theo **cùng luật định giá** với LTT-3.8 (D07 phương án A): neo vào
   OpenRouter `qwen/qwen3.5-9b` $0,10/$0,15 mỗi 1M (lấy 2026-09-11) ≈ 26/39
   credit/1M ⇒ ta rẻ hơn ~50 %; vào-cache giữ tỉ lệ 1/5 như 3.8.

   ⛔ Giá LTT-3.8 **không đổi một đồng** ở lượt cắt này, kể cả nhãn phiên bản.
      10.663 lượt `ltt_llm.chat` trong 28 ngày đã tính theo bảng ấy; đổi nó
      trong một task "thêm model thứ hai" là đổi hoá đơn của người khác.

   🔴 `tinh()` và `uoc_tran()` **BẮT BUỘC** nhận `model`. Không có mặc định ngầm
      — một mặc định ngầm ở đây nghĩa là ngày ai đó quên truyền, lượt LTT-3.5 bị
      thu theo giá LTT-3.8 (gấp **20 lần** ở token ra) và **không gì đỏ**.
      D07 hệ quả 4: mọi đường tiền tính theo **model thật đã phục vụ**.

⭐ CHI PHÍ ĐIỆN BIÊN — số ĐO được, không phải số ước (cổng G4, máy B, 12/09/2026).

   Đơn giá điện **3.000 đ/kWh** là con số kho này đã ghi sẵn và dùng ở mọi phép
   tính giá vốn khác (`tools/do_gia_von_voice.py::GIA_DIEN_VND_KWH`,
   `platform_core/gia_von.json`). ⚠️ Nó tự khai là **giả định** (bậc thang EVN,
   `docs/VLM_NOI_BO/GIA_TOKEN_DE_XUAT.md` §"Giả định phải xác minh") — chưa ai
   đối chiếu hoá đơn thật. Mọi số dưới đây tỉ lệ thuận với nó.

   Phép tính: J/token = W ÷ (token/s); 1M token ⇒ J × 1e6 ⇒ ÷ 3.600.000 = kWh
   ⇒ × 3.000 đ ⇒ ÷ 100 đ = credit.

        LTT-3.8 (3090, 314 W ở C1)
          ra      314 / 66,7    = 4,708  J/tok -> 1,308  kWh/1M -> 3.923 d ->  39 credit/1M
          vao@6,7K 314 / 1.239  = 0,2534 J/tok -> 0,0704 kWh/1M ->   211 d -> 2,1 credit/1M
          vao@163K 314 / 646    = 0,4861 J/tok -> 0,1350 kWh/1M ->   405 d -> 4,1 credit/1M

        LTT-3.5 (5060 Ti, 119 W ở C1)
          ra      119 / 73,0    = 1,630  J/tok -> 0,4528 kWh/1M -> 1.358 d -> 13,6 credit/1M
          vao@6,7K 119 / 2.238  = 0,0532 J/tok -> 0,0148 kWh/1M ->    44 d -> 0,44 credit/1M
          vao@163K 119 / 1.350  = 0,0881 J/tok -> 0,0245 kWh/1M ->    73 d -> 0,73 credit/1M

   ⇒ Biên gộp trên **điện** ở C1: 3.8 ≈ **10×** token ra, 3.5 ≈ **1,5×**.

   🔑 D07 ghi một rủi ro chủ dự án đã CHẤP NHẬN trước khi đo: *"ước chi phí điện
      biên LTT-3.5 ~31 credit/1M ra ở C1 [INFERRED] > giá ra 20 ⇒ có thể bán
      dưới giá vốn điện khi vắng khách"*. **Số đo bác bỏ nó**: 13,6 < 20, tức
      ngay cả ở C1 (một lượt duy nhất, trường hợp xấu nhất của phép chia công
      suất) giá ra vẫn trên chi phí điện. Số ước cao gấp ~2,3 lần số đo vì nó
      đoán công suất 5060 Ti theo 3090.

   ⛔ Đây là **báo cáo lại cho chủ dự án**, không phải cớ để tự đổi giá. Muốn
      đổi luật giá ⇒ REOPEN D07 (D07 hệ quả 1 nói đúng chữ đó).

   ⚠️ Và đừng đọc "biên 1,5×" thành "gần lỗ": C1 là **một** lượt. Cả hai card
      chạy nhiều slot, nên ở C≥2 cùng số W ấy chia cho nhiều luồng và chi phí
      mỗi token tụt xuống. Điện cũng không phải toàn bộ giá vốn (khấu hao card,
      điện nền, mạng) — `platform_core/gia_von.py` sở hữu phần còn lại.

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


@dataclass(frozen=True)
class BangGia:
    """Giá của **một** model, đơn vị credit / 1.000.000 token.

    `phien_ban` là nhãn đóng dấu lên báo giá và lên job. `public_api/pricing.py`
    nói rõ vì sao: *"reconciling a charge months later then means reading two
    facts that were both written at the time"*. Đổi giá ⇒ **nhãn mới**, không
    sửa nhãn cũ — và nhãn là **của model**, không phải của hệ thống: hai model
    đổi giá vào hai ngày khác nhau.
    """

    vao_moi_1m: int
    vao_cache_1m: int
    ra_1m: int
    phien_ban: str


#: ⭐ BẢNG GIÁ. Đây là những con số duy nhất được phép đại diện cho giá model nhà
#:   trong toàn bộ mã nguồn — kể cả trang bán hàng và tài liệu API.
#:
#: 🔑 KHOÁ LÀ **BÍ DANH CÔNG KHAI**, không phải id nội bộ. Khách mua `ltt-3.8`;
#:    id `qwen38-api` là chi tiết vận hành và có thể đổi mà giá không đổi.
#:
#: ⛔ Tập khoá ở đây phải **đúng bằng** `canonical.ALIAS_SANG_ID`. Không import
#:    `canonical` ở đây (nó kéo theo `registry`, và `registry` lại import ngược
#:    `canonical` — vòng import). Thứ ghép hai đầu lại là một **phép kiểm**,
#:    `test_1213::test_bang_gia_phu_dung_danh_muc_cong_khai`, không phải một
#:    câu `import`. Thêm model mà quên giá ⇒ phép kiểm ấy đỏ, chứ không phải
#:    khách bị thu giá của model bên cạnh.
BANG_GIA: dict[str, BangGia] = {
    "ltt-3.8": BangGia(vao_moi_1m=50, vao_cache_1m=10, ra_1m=400,
                       phien_ban="ltt-vlm-2026-08-22"),
    "ltt-3.5": BangGia(vao_moi_1m=13, vao_cache_1m=3, ra_1m=20,
                       phien_ban="ltt-3.5-2026-09-11"),
}

#: Model mà **ba hằng số cũ** dưới đây luôn luôn có nghĩa. Bằng
#: `canonical.MODEL_MAC_DINH` — chốt bằng phép kiểm, không bằng import (xem trên).
MODEL_GIA_MAC_DINH = "ltt-3.8"

#: 🔻 BÍ DANH CỦA BẢNG 3.8, giữ cho mã chưa truyền model đọc được **một hằng số**
#:    chứ không phải một con số gõ tay. Chúng **dẫn xuất** từ `BANG_GIA`, nên
#:    không có chỗ thứ hai để hai số lệch nhau.
#:
#: ⚠️ Chúng là **hằng số để ĐỌC**, không phải đường tắt để tính tiền. Tính tiền
#:    đi qua `tinh()`/`uoc_tran()` với `model` tường minh.
GIA_VAO_MOI_CREDIT_1M = BANG_GIA[MODEL_GIA_MAC_DINH].vao_moi_1m
GIA_VAO_CACHE_CREDIT_1M = BANG_GIA[MODEL_GIA_MAC_DINH].vao_cache_1m
GIA_RA_CREDIT_1M = BANG_GIA[MODEL_GIA_MAC_DINH].ra_1m

#: Nhãn phiên bản giá của model mặc định. Xem `BangGia.phien_ban`.
PHIEN_BAN_GIA = BANG_GIA[MODEL_GIA_MAC_DINH].phien_ban

_MOT_TRIEU = 1_000_000


def bang_cua(model: str) -> BangGia:
    """Bảng giá của `model`. **Không có model ⇒ `KeyError`, không có dự phòng.**

    🔴 VÌ SAO NÉM CHỨ KHÔNG RƠI VỀ MẶC ĐỊNH. Rơi về bảng 3.8 cho một model không
       có giá là thu **20 lần** giá đúng ở token ra — im lặng, đúng hướng có lợi
       cho ta, và không một phép kiểm nào nhìn thấy. Một `KeyError` ở đây nghĩa
       là bản khai tự mâu thuẫn (cửa đã nhận một tên mà bảng giá không biết) và
       nó phải nổ to ngay tại chỗ.
    """
    try:
        return BANG_GIA[model]
    except KeyError:
        raise KeyError(
            f"khong co bang gia cho model {model!r} — hop le: "
            f"{sorted(BANG_GIA)}. Them model thi them gia cung luot."
        ) from None


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


def tinh(su_dung: SuDung, model: str) -> ChiPhi:
    """Chi phí thật của một lượt đã chạy xong, theo giá của **`model` đã phục vụ**.

    ⛔ `model` BẮT BUỘC — xem docstring module. Tên lạ ⇒ `KeyError` (`bang_cua`).

    ⛔ Ném `KhongDoDuocError` khi `su_dung.dang_tin` là `False`.

    ⚠️ Thứ tự hai chốt là có chủ ý: **không đo được** xét TRƯỚC **model lạ**. Bên
       gọi bắt `KhongDoDuocError` để **hoàn trọn**; để một `KeyError` chen lên
       trước là biến một lượt đáng hoàn thành một lỗi 500 giữa đường tiền.
    """
    if not su_dung.dang_tin:
        raise KhongDoDuocError(
            "thuong nguon khong tra `usage` — khong co can cu tinh tien")

    g = bang_cua(model)
    return ChiPhi(
        vao_moi_mcredit=_mcredit(su_dung.token_vao_moi, g.vao_moi_1m),
        vao_cache_mcredit=_mcredit(su_dung.token_vao_cache, g.vao_cache_1m),
        ra_mcredit=_mcredit(su_dung.token_ra, g.ra_1m),
        phien_ban_gia=g.phien_ban,
    )


def uoc_tran(*, token_vao_uoc: int, max_tokens: int, model: str) -> ChiPhi:
    """Trần chi phí để **giữ chỗ trước khi chạy**, theo giá của `model` khách xin.

    ⛔ Cố ý ước CAO: giả định **không có token nào lấy từ cache**, và giả định
    model sinh đủ `max_tokens`. Giữ thiếu thì khách tiêu quá số dư — chiều sai đó
    đắt hơn nhiều so với việc giữ dư rồi hoàn lại.

    Phần dư trả về cho khách ở `credit.hoan()` sau khi quyết toán.

    🔴 `model` BẮT BUỘC, cùng lý do với `tinh()` — và ở đây nó còn là **cửa 402**:
       giữ theo giá 3.8 cho một lượt 3.5 là từ chối một khách có đủ tiền.
    """
    g = bang_cua(model)
    return ChiPhi(
        vao_moi_mcredit=_mcredit(max(0, int(token_vao_uoc)), g.vao_moi_1m),
        ra_mcredit=_mcredit(max(0, int(max_tokens)), g.ra_1m),
        phien_ban_gia=g.phien_ban,
    )


def bang_gia_moi_model() -> dict[str, dict]:
    """`{bí_danh: bảng_giá}` cho **mọi** model đang bán.

    ⭐ Trang giá và tài liệu developer đọc hàm này (D07 hệ quả 3). Khách không
       chọn được model nếu chỉ nhìn thấy giá của một model.
    """
    return {ten: bang_gia(ten) for ten in BANG_GIA}


def bang_gia(model: str = MODEL_GIA_MAC_DINH) -> dict:
    """Bảng giá để phơi ra `/v1/models` và tài liệu API.

    ⭐ Phơi giá ra API là có chủ ý: khách xây bot cần tính được chi phí **trước**
    khi gọi. Và nó buộc ta chỉ có một nguồn giá — trang tài liệu không thể lệch
    với thứ thật sự tính tiền, vì cả hai đọc cùng hàm này.

    ⚠️ `model` có mặc định ở ĐÂY (và **chỉ** ở đây): hàm này không tính tiền của
       ai, nó chỉ mô tả. Bên gọi muốn cả hai bảng thì gọi `bang_gia_moi_model()`.
    """
    g = bang_cua(model)
    return {
        "model": model,
        "don_vi": "credit / 1.000.000 token",
        "phien_ban_gia": g.phien_ban,
        "token_vao": g.vao_moi_1m,
        "token_vao_cache": g.vao_cache_1m,
        "token_ra": g.ra_1m,
        # ⛔ Nói thẳng cách làm tròn, đừng để khách phát hiện sau khi nhận hoá đơn.
        #
        # ⭐ ĐỔI 05/09/2026 (R2b): trước đây là *"làm tròn LÊN mỗi lượt gọi, tối
        #    thiểu 1 credit"* — và chính dòng này thừa nhận nó làm lượt nhỏ đắt
        #    hơn giá niêm yết. Đo ra: một hội thoại 20 lượt ngắn bị thu **20
        #    credit** trong khi giá niêm yết của chính ta là **~3**, và mọi lượt
        #    dưới ~1 credit đắt hơn cả giá bán lẻ ngoài thị trường.
        #
        #    Nay phần lẻ được **tích luỹ** (`users.mcredit_du`) và chỉ thu phần
        #    nguyên. Khách trả **đúng bảng giá**, không trả sàn.
        #    Xem `docs/CHATLTT_V3/04_ADR_R2B_TINH_TIEN_LUOT.md`.
        #
        # 🔴 Ba dòng dưới là ĐIỀU KHOẢN CÔNG BỐ (`public_api/dieu_khoan.py` đọc
        #    chính hàm này). Đổi cách tính mà quên đổi chúng là công bố một điều
        #    khoản không còn đúng — tệ hơn cả việc thu thừa.
        "lam_tron": _mo_ta_lam_tron(),
        "toi_thieu_moi_luot_credit": _toi_thieu_moi_luot(),
        # ⚠️ Tỉ lệ cache **tính ra**, không gõ "20%". Nó là 1/5 ở `ltt-3.8` và
        #    ~23 % ở `ltt-3.5`; một câu gõ cứng là một điều khoản công bố SAI ở
        #    đúng model thứ hai — cùng lớp lỗi ba dòng 🔴 ở trên cảnh báo.
        "ghi_chu": ("Token reasoning tinh nhu token ra. "
                    f"Token vao lay lai tu cache tinh {_phan_tram_cache(g)}% "
                    "gia token vao. " + _ghi_chu_lam_tron()),
    }


def _phan_tram_cache(g: BangGia) -> int:
    """Giá vào-cache bằng bao nhiêu phần trăm giá vào mới, làm tròn."""
    if g.vao_moi_1m <= 0:
        return 0
    return round(100 * g.vao_cache_1m / g.vao_moi_1m)


def _san_moi_luot() -> bool:
    """Có đang chạy C1 (làm tròn lên mỗi lượt gọi) không. **C1 là mặc định.**

    ⛔ Đọc cùng một biến môi trường mà `thanh_toan.py` đọc, **không** chép lại
       tên cờ — điều khoản công bố phải nói đúng thứ đang thật sự chạy. Hai
       bản đọc cờ là hai bản sẽ lệch, và chúng lệch ở chỗ tính tiền.
    """
    from platform_core.llm import thanh_toan
    return thanh_toan._san_moi_luot()


def _mo_ta_lam_tron() -> str:
    return ("len credit nguyen, moi luot goi" if _san_moi_luot()
            else "tich luy phan le, chi thu phan nguyen")


def _toi_thieu_moi_luot() -> int:
    return 1 if _san_moi_luot() else 0


def _ghi_chu_lam_tron() -> str:
    if _san_moi_luot():
        return ("Moi luot goi lam tron LEN credit nguyen, toi thieu 1 credit "
                "(100d) — nen luot goi rat nho tra nhieu hon gia niem yet.")
    return ("Phan le duoi 1 credit duoc GIU LAI va cong vao luot sau, nen ban "
            "tra dung bang gia chu khong tra san. Khong co muc toi thieu moi "
            "luot goi.")

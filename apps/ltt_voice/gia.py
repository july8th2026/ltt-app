"""
gia.py — giá một lượt tạo tiếng nói. **MỘT chỗ duy nhất, có phiên bản.**

Khuôn tầng 3 của `docs/KHUON_BAN_MODEL_NHA.md` đòi sáu thứ, và đây là chúng:

  3.1  bảng giá có PHIÊN BẢN + hàm `bang_gia()`
  3.2  số học SỐ NGUYÊN, làm tròn LÊN, tối thiểu 1 credit
  3.3  `uoc_tran()` giữ chỗ **>= giá thật, LUÔN LUÔN**
  3.4  quyết toán theo SẢN PHẨM THẬT (giây tiếng đo được), không theo phần đã giữ
  3.5  không đo được ⇒ **hoàn đủ, thu 0**
  3.6  giá lên trang công khai, lấy từ **chính hàm ra hoá đơn**

🔴 VÌ SAO DÙNG MILLI-CREDIT Ở ĐÂY, KHÁC `apps/anhnoibo/gia.py`:

   `anhnoibo` cố ý **không** dùng milli-credit, và lý do nó ghi ra là đúng: đơn vị
   của nó là **một ảnh**, vốn đã lớn hơn một credit, nên thêm một tầng số học chỉ
   là thêm chỗ sai.

   Ở đây đơn vị là **một giây tiếng**, và nó **nhỏ hơn** một credit hàng chục lần.
   Làm tròn lên ở từng giây sẽ biến một câu 3 giây thành 3 credit. Đó chính là
   tình huống `platform_core/llm/gia_token.py` đã giải bằng milli-credit. Cùng bài
   toán, cùng lời giải.

   ⇒ Cộng dồn bằng **milli-credit số nguyên**, làm tròn lên **đúng một lần** ở
      bước cuối.

⚠️ CON SỐ DƯỚI ĐÂY LÀ GIÁ TẠM, và file này không giấu điều đó. Chốt giá thật cần
   RTF và giây GPU đo được ở V1, rồi ghi giá vốn vào `platform_core/gia_von.json`
   ở V7. Cái file này làm được ngay bây giờ là khiến giá tạm ấy **nói ra được**:
   có tên, có phiên bản, công bố được, đối soát được.
"""
from __future__ import annotations

from platform_core.i18n import _ as _t

#: Đổi con số nào bên dưới thì **phải** đổi chuỗi này. Không có phiên bản thì
#: không đối soát được một hoá đơn cũ với bảng giá nào đã sinh ra nó.
PHIEN_BAN_GIA = "ltt-voice-2026-08-30a"

#: Số milli-credit trong một credit. Đừng đổi — `credit` nhận credit nguyên.
MCREDIT_MOI_CREDIT = 1_000

#: Giá một GIÂY tiếng nói sinh ra, tính bằng milli-credit.
#:
#: 200 mcredit = 0,2 credit = 20đ mỗi giây, tức **1 credit cho 5 giây**.
#:
#: Tham chiếu để biết con số này đứng ở đâu: ElevenLabs khoảng $0,18/1.000 ký tự;
#: 1.000 ký tự tiếng Việt đọc ra chừng 70 giây, tức ~47 credit. Cùng đoạn đó ở
#: đây là ~14 credit. Rẻ hơn ba lần, và đó là chỗ model nhà nên đứng.
#:
#: ⚠️ Chưa đối chiếu được với giá vốn vì **chưa có RTF đo thật** (V1). `test_261`
#:    sẽ chốt "bán >= vốn" ngay khi mục `ltt-voice-v3turbo` vào `gia_von.json`.
MCREDIT_MOI_GIAY = 200

#: Ghi danh một giọng: một lượt `encode_reference` + khử nhiễu, vài giây GPU.
#: Thu một lần, không thu theo độ dài clip — clip đã bị chặn ở 3–30 giây.
CREDIT_GHI_DANH = 2

#: 🔴 TỈ LỆ KÝ TỰ -> GIÂY DÙNG ĐỂ **GIỮ CHỖ**, và nó cố ý BI QUAN.
#:
#: ĐÃ ĐO THẬT trên 5060 Ti ngày 2026-08-30 (`docs/LTT_VOICE/do_v1.json`), và số
#: đo **không phải một con số mà là một dải**:
#:
#:     van ban thuong, 500-3.000 ky tu   ->  20,5 - 21,0 ky tu/giay
#:     cau ngan thuong (47 ky tu)        ->  14,0
#:     cau nhieu SO va NGAY (81 ky tu)   ->   9,9   <- day la day
#:
#: ⭐ Vì sao đáy lại là câu có số: "1.500.000 đồng" là 14 ký tự nhưng đọc ra
#:    "một triệu năm trăm nghìn đồng" — hơn hai giây. Chuẩn hoá văn bản **làm nở
#:    văn bản ra**, nên tỉ lệ tính trên đầu vào phải chịu được phần nở đó.
#:
#: ⭐ HAI SỬA, VÀ CÁI THỨ HAI DO CHÍNH TEST BẮT ĐƯỢC.
#:
#: **Sửa một — đếm trên văn bản ĐÃ CHUẨN HOÁ.** Đáy 9,9 không phải vì model đọc
#: chậm hơn, mà vì **văn bản nở ra**. Đếm sau khi chuẩn hoá thì phần nở đã nằm
#: trong số ký tự, và dải thu về quanh 20,5-21,0.
#:
#: **Sửa hai — một tỉ lệ phẳng vẫn SAI, và test đã đỏ đúng chỗ.** Câu 47 ký tự
#: chỉ đạt **14,0 ký tự/giây** trong khi bài 3.000 ký tự đạt 20,8. Không phải
#: nhiễu: khớp tuyến tính trên các bậc dài cho **0,048 giây/ký tự** (tức 20,8) và
#: các câu ngắn nằm cao hơn đường đó chừng 0,3-1,1 giây. Đó là **phí khởi động
#: cố định** của một lượt phát — khoảng lặng đầu/cuối và nhịp mở câu — và nó
#: không tỉ lệ với độ dài.
#:
#: ⇒ Mô hình đúng là `giây ≈ khởi_động + ký_tự / tốc_độ`, không phải một phép
#:   chia. Một phép chia buộc phải hạ mẫu số xuống dưới 14 để che câu ngắn, và
#:   khi đó **mọi bài dài** trả giá cho một hiện tượng chỉ xảy ra ở câu ngắn.
#:
#: Số lấy: khởi động **1,5 giây** (trên mức lệch lớn nhất đo được là 1,1) và tốc
#: độ **18 ký tự/giây** (dưới 20,8 khoảng 15%). Kết quả trên chính số đo:
#:
#:     47 ky tu   -> uoc 4,11s vs do 3,36s
#:    143 ky tu   -> uoc 9,44s vs do 8,16s
#:  1.500 ky tu   -> uoc 84,8s vs do 71,6s   (thua 1,18 lan, khong phai 2,5 lan)
#:  3.000 ky tu   -> uoc 168s  vs do 144,5s
#:
#: ⛔ Đừng nâng `KY_TU_MOI_GIAY_UOC` sát 20,8. Số đo là của MỘT bộ giọng trên MỘT
#:    card; một giọng đọc chậm hơn là hoàn toàn bình thường, và giữ thiếu thì
#:    khách tiêu quá số dư — một lỗi sổ sách, không phải một lỗi hiển thị.
GIAY_KHOI_DONG_UOC = 1.5
KY_TU_MOI_GIAY_UOC = 18


def _len_up(m: int) -> int:
    """Milli-credit -> credit, làm tròn LÊN bằng số nguyên, tối thiểu 1."""
    return max(1, -(-int(m) // MCREDIT_MOI_CREDIT))


def tinh_mcredit(giay: float) -> int:
    """Giá THẬT của một lượt, milli-credit, từ số giây **đã sinh ra được**.

    ⛔ Truyền vào đây thời lượng **thật sự đo được** (ffprobe), không phải thời
       lượng đã ước. Đó là khác biệt giữa chốt 3.3 và chốt 3.4.
    """
    g = max(0.0, float(giay))
    # Làm tròn LÊN tới milli-credit: một mẩu giây vẫn phải trả tiền.
    return int(-(-(g * MCREDIT_MOI_GIAY) // 1))


def tinh(giay: float) -> int:
    """Giá THẬT của một lượt, tính bằng credit."""
    return _len_up(tinh_mcredit(giay))


def giay_uoc(so_ky_tu: int) -> float:
    """Số giây tiếng ƯỚC từ số ký tự **đã chuẩn hoá**. Cố ý ước THỪA.

    Mô hình hai tham số, không phải một phép chia — xem chú thích dài ở
    `GIAY_KHOI_DONG_UOC`. Phần khởi động là thứ làm câu ngắn tốn nhiều giây trên
    mỗi ký tự hơn bài dài.
    """
    return GIAY_KHOI_DONG_UOC + max(1, int(so_ky_tu)) / float(KY_TU_MOI_GIAY_UOC)


def uoc_tran(*, so_ky_tu: int) -> int:
    """Trần ước CAO để giữ chỗ. **Luôn >= `tinh()` của lượt đó** (chốt 3.3)."""
    return _len_up(tinh_mcredit(giay_uoc(so_ky_tu)))


def uoc_tran_lo(*, cac_do_dai) -> int:
    """Trần ước cho một lô nhiều đoạn. Cộng **milli-credit** rồi mới làm tròn.

    ⛔ Đừng cộng kết quả của `uoc_tran()` từng đoạn: làm tròn lên N lần thì một
       bài 20 đoạn phải trả thừa tới 20 credit cho việc làm tròn, không phải cho
       tiếng nói.

    ⚠️ Phần khởi động cộng cho TỪNG đoạn, và đó là đúng: mỗi đoạn là một lượt
       phát riêng, nên nó thật sự trả phí khởi động riêng.
    """
    tong = sum(tinh_mcredit(giay_uoc(n)) for n in cac_do_dai)
    return _len_up(tong)


def tinh_lo(cac_giay) -> int:
    """Giá thật của một lô. Cộng milli-credit rồi làm tròn đúng một lần."""
    tong = sum(tinh_mcredit(g) for g in cac_giay)
    return _len_up(tong)


def bang_gia() -> dict:
    """Bảng giá công bố. Trang `/gia-api` đọc **hàm này**, không gõ lại số.

    Chốt 3.6: gõ lại số vào template là tạo bảng giá thứ hai, và hai bảng giá
    lệch nhau thì bảng nào cũng không đáng tin.
    """
    return {
        "phien_ban": PHIEN_BAN_GIA,
        "don_vi": "credit",
        "muc": [
            {
                "ten": _t("Tạo tiếng nói"),
                "cach_tinh": _t("theo giây tiếng nói sinh ra thật"),
                "mcredit_moi_giay": MCREDIT_MOI_GIAY,
                "credit_moi_phut": _len_up(tinh_mcredit(60)),
                "vi_du": [
                    {"mo_ta": _t("một câu ~10 giây"), "credit": tinh(10)},
                    {"mo_ta": _t("một đoạn ~60 giây"), "credit": tinh(60)},
                    {"mo_ta": _t("một bài ~5 phút"), "credit": tinh(300)},
                ],
            },
            {
                "ten": _t("Tạo giọng mới (nhân bản)"),
                "cach_tinh": _t("thu một lần cho mỗi lần ghi danh"),
                "credit": CREDIT_GHI_DANH,
            },
        ],
        "ghi_chu": [
            _t("Giữ chỗ tính theo số ký tự gửi lên; phần giữ dư được hoàn ngay "
               "khi job xong."),
            _t("Không đo được thời lượng tệp sinh ra thì hoàn đủ, thu 0."),
        ],
    }

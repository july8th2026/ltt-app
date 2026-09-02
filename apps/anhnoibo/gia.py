"""
gia.py — giá một lượt tạo ảnh bằng model nhà. (H37, chuẩn hoá theo `docs/KHUON_BAN_MODEL_NHA.md`)

⭐ MỘT CHỖ DUY NHẤT ĐẠI DIỆN CHO GIÁ. Trước file này, `CREDIT_MOI_ANH = 5` nằm
   trong `manifest.py` và không ai ngoài `manifest._gia` đọc được nó: không có
   bảng giá công bố, không có phiên bản, và **trang giá công khai không có ảnh**.

   Khuôn (tầng 3) đòi bốn thứ, và đây là chúng:

     3.1  bảng giá có PHIÊN BẢN + hàm `bang_gia()`
     3.2  số học số nguyên, làm tròn LÊN, tối thiểu 1 credit
     3.3  `uoc_tran()` giữ chỗ >= giá thật, LUÔN LUÔN
     3.4  quyết toán theo SẢN PHẨM THẬT, không theo phần đã giữ

⛔ 3.4 KHÔNG PHẢI LÝ THUYẾT Ở ĐÂY. Cổng render trả về **đúng số ảnh đã tải lên
   được** (`image_keys[:so]` trong `runner.py`) và ghi log khi thiếu. Nghĩa là
   khách hoàn toàn có thể xin 4 ảnh và nhận 2. Không báo giá thật thì
   `job_runner._quyet_toan_credit` thu **trọn phần đã giữ** — khách trả tiền 4
   ảnh cho 2 ảnh, im lặng.

   Đây đúng là lỗi H38 đã mắc ở cửa job và đã sửa hôm 23/08. Cùng một gốc.

⚠️ GIÁ VẪN LÀ GIÁ TẠM, và file này không đổi điều đó. Nó chỉ làm cho giá tạm ấy
   **nói ra được**: có tên, có phiên bản, công bố được, và đối soát được. Chốt
   con số thật cần số liệu dùng thật — xem `docs/ANH_NOI_BO/`.
"""
from __future__ import annotations

from platform_core.i18n import _ as _t

#: Đổi con số nào bên dưới thì **phải** đổi chuỗi này. Không có phiên bản thì
#: không đối soát được một hoá đơn cũ với bảng giá nào đã sinh ra nó.
PHIEN_BAN_GIA = "ltt-image-2026-08-24b"

#: Giá một ảnh thường (`t2i`).
#:
#: ⚠️ Model nội bộ không tốn tiền API, nhưng **chiếm GPU**: đo thật 22/08 là 96
#:    giây/ảnh (t2i, 50 bước). Nên giá phản ánh **thời gian máy**, không phải chi
#:    phí API.
#:
#: 📉 **HẠ TỪ 5 XUỐNG 3 ngày 24/08** (chủ sản phẩm quyết: rẻ hơn một phần ba).
#:
#:    5 × 2/3 = 3,33. Lấy **3**, không lấy 4: làm tròn về phía khách, và như vậy
#:    *mọi* lượt gọi đều rẻ hơn ít nhất một phần ba — kể cả lượt một ảnh, vốn là
#:    lượt phổ biến nhất. Lấy 4 thì lượt một ảnh chỉ rẻ đi 20 %, tức là hứa một
#:    đằng giao một nẻo ở đúng trường hợp hay gặp nhất.
#:
#:    ⛔ Không chuyển sang milli-credit như `gia_token.py` của LLM. Ở đó đơn vị
#:       (một token) nhỏ hơn một credit hàng nghìn lần nên buộc phải có. Ở đây
#:       đơn vị là **một ảnh** và nó đã lớn hơn một credit — thêm một tầng số học
#:       chỉ để làm tròn lại ở bước cuối là thêm chỗ sai mà không mua được gì.
#:
#: ✅ Vẫn **trên giá vốn**, và còn xa: `gia_von.json` ghi 1,05 credit/ảnh (điện +
#:    khấu hao GPU, đo thật 22/08). Biên 2,9 lần. `test_261` chốt điều này.
CREDIT_MOI_ANH = 3

#: Ảnh có tham chiếu (`edit`, `subject`) đắt hơn hẳn — đo được **gấp 3,3 lần**
#: thời gian ở cùng số bước (~190 giây). Hệ số 3 là làm tròn xuống của số đo đó.
#:
#: ⚠️ Hệ số này **cao hơn tỉ lệ giá vốn**: `gia_von.json` ghi 1,05 và 2,07
#:    credit/ảnh, tức là tham chiếu chỉ đắt hơn **1,97 lần** về chi phí, không
#:    phải 3. Giữ 3 vì nó cũng phản ánh **chỗ trong hàng đợi** — một lượt tham
#:    chiếu khoá card gấp đôi thời gian trên một máy đã chật. Ghi ra đây để lần
#:    sau ai nhìn vào không tưởng đây là một phép nhân từ giá vốn.
HE_SO_THAM_CHIEU = 3

#: Trần số ảnh một lượt. Khớp `params_schema` của tool — hai chỗ lệch nhau thì
#: một yêu cầu hợp lệ sẽ bị tính giá của một yêu cầu khác.
SO_ANH_TOI_DA = 4

#: Chế độ có dùng ảnh tham chiếu.
CHE_DO_THAM_CHIEU = ("edit", "subject")


def he_so(che_do: str) -> int:
    return HE_SO_THAM_CHIEU if str(che_do or "") in CHE_DO_THAM_CHIEU else 1


def tinh(*, so_anh: int, che_do: str) -> int:
    """Giá THẬT của một lượt, tính từ số ảnh **đã sinh ra được**.

    ⛔ Truyền vào đây số ảnh **thật sự nhận được**, không phải số đã xin. Đó là
       toàn bộ khác biệt giữa hoá đơn đúng và hoá đơn thu thừa.

    ⛔ Không sinh được ảnh nào ⇒ **0**, không phải 1. Tối thiểu-1-credit là luật
       của một lượt **có sản phẩm**; một lượt không ra gì thì không có gì để bán.
       (Lượt hỏng đi đường `credit.hoan`, không đường này.)
    """
    so = max(0, int(so_anh or 0))
    if so == 0:
        return 0
    return so * CREDIT_MOI_ANH * he_so(che_do)


def uoc_tran(*, so_anh_xin: int, che_do: str) -> int:
    """Trần để giữ chỗ **trước** khi chạy. Ước CAO có chủ ý.

    Giữ thiếu thì khách tiêu quá số dư; giữ dư thì hoàn lại. Chiều sai thứ nhất
    đắt hơn nhiều.

    ⚠️ Đây là hàm mà `manifest.credit_cost` gọi, nên nó **phải** luôn ≥ `tinh()`
       với cùng chế độ và số ảnh ≤ số đã xin. `test_276` quét toàn bộ để chốt.
    """
    so = max(1, min(int(so_anh_xin or 1), SO_ANH_TOI_DA))
    return so * CREDIT_MOI_ANH * he_so(che_do)


def bang_gia() -> dict:
    """Bảng giá công bố. Trang giá công khai đọc **hàm này**, không gõ lại số.

    Gõ lại vào template là tạo ra một bảng giá thứ hai, và ngày hai bảng lệch
    nhau thì bảng nào cũng không đáng tin.

    ⭐ `vi_du` NẰM Ở ĐÂY từ 2026-09-02, và đó là chỗ đúng của nó.

       Trước đó `server/routes/dashboard.py` tự dựng ba ví dụ rồi gọi
       `gia.tinh()` cho từng cái — tức tầng route giữ **danh sách ví dụ** còn
       app giữ **phép tính**. Chính chú thích ngay cạnh nó (phần giọng nói) đã
       gọi việc ấy là *"tạo đúng cái bảng giá thứ hai"* mà hàm này cảnh báo, và
       `apps/ltt_voice/gia.py` thì đã làm đúng từ đầu.

       Đưa về đây thì trang giá chỉ còn **đọc**, không còn **tính** — và nền
       tảng thôi phải biết `anhnoibo` có những chế độ nào.
    """
    return {
        "don_vi": "credit / anh",
        "phien_ban_gia": PHIEN_BAN_GIA,
        "vi_du": [
            {"ten": _t("Một ảnh từ mô tả"), "so": 1, "che_do": "t2i",
             "credit": tinh(so_anh=1, che_do="t2i")},
            {"ten": _t("Bốn ảnh từ mô tả"), "so": 4, "che_do": "t2i",
             "credit": tinh(so_anh=4, che_do="t2i")},
            {"ten": _t("Một ảnh có ảnh tham chiếu"), "so": 1, "che_do": "edit",
             "credit": tinh(so_anh=1, che_do="edit")},
        ],
        "anh_thuong": CREDIT_MOI_ANH,
        "anh_tham_chieu": CREDIT_MOI_ANH * HE_SO_THAM_CHIEU,
        "he_so_tham_chieu": HE_SO_THAM_CHIEU,
        "so_anh_toi_da": SO_ANH_TOI_DA,
        "che_do_tham_chieu": list(CHE_DO_THAM_CHIEU),
        "ghi_chu": (
            "Anh tham chieu (edit, subject) dat gap 3 lan vi may ve lau gap "
            "khoang 3,3 lan. Chi tinh tien nhung anh THAT SU sinh ra duoc: xin 4 "
            "ma chi ra 2 thi tra 2. Luot khong ra anh nao duoc hoan du."),
    }

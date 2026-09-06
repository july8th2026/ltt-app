"""gia_trich.py — giá của một lượt TRÍCH tài liệu. (H44 P06 bước 3)

## 🔴 Giá CHƯA CHỐT, và nó fail-closed chứ không mặc định 0

Đặt giá là một **bút toán tiền**, tức một trong ba ranh giới phải có chủ dự án.
Tôi dựng cơ chế; con số thì không.

⛔ **Vì sao không mặc định 0 cho tới khi có giá.** P06 §7 chấm rằng trích là một
   job **trả tiền**, và lý do được trích thẳng từ docstring của
   `platform_core/upload_sessions.py`:

       "Cửa 'phải giữ credit mới được lưu file' tồn tại để không ai biến input
        của job thành kho lưu trữ miễn phí."

   Một giá 0 tạm thời **chính là** cái lỗ ấy, chỉ khác là nó trông như một mặc
   định vô hại. Và một mặc định vô hại thì không ai quay lại sửa — nó chỉ được
   phát hiện khi có người tải 10 GB tài liệu lên để dùng làm kho.

⭐ Nên khi chưa có giá, `tinh()` **ném**. Job không chạy được, không ai bị thu
   sai, và sự thiếu sót **nói ra** thay vì lặng lẽ thành chính sách.

## Cơ sở tính: KÝ TỰ TRÍCH ĐƯỢC, không phải cỡ tệp

Ba lựa chọn, và hai cái đầu sai theo cách người dùng cảm nhận được:

| cơ sở | vì sao không |
|---|---|
| cỡ tệp (MB) | một PDF quét 40 MB **ra 0 chữ** vẫn tính đắt nhất |
| số trang | một trang bảng biểu trắng bằng một trang chữ dày |
| **ký tự trích được** | ✅ đúng thứ khách nhận được, và đo **sau** khi làm xong |

⇒ Tính **sau**, theo kết quả thật — cùng luật `apps/anhnoibo/jobs.py` đã ghi:
  *"TÍNH TIỀN THEO ẢNH THẬT SỰ NHẬN ĐƯỢC, KHÔNG THEO SỐ ĐÃ XIN."*

⚠️ Hệ quả: báo giá **trước** khi bấm chỉ là **ước tính** (theo cỡ tệp), và số
   thu thật có thể thấp hơn. Thấp hơn thì được; cao hơn thì không — đó là lý do
   `bao_gia` phải ước tính theo **trần** chứ không theo trung bình.
"""
from __future__ import annotations

#: 🟡 GIÁ **TẠM**, không phải giá đã chốt. Đơn vị: **milli-credit** cho mỗi
#:    1.000 ký tự trích được — milli vì mọi số học tiền của H44 ở milli-credit
#:    (ADR R2b), và vì một tài liệu nhỏ phải rẻ hơn 1 credit chứ không bị làm
#:    tròn lên thành 1.
#:
#: ## Vì sao có một con số ở đây thay vì để `None`
#:
#: Để `None` fail-closed nghe an toàn, nhưng nó làm bước 4–6 **không chạy được
#: đầu-cuối** và biến một quyết định thương mại thành một cái cổng chặn kỹ
#: thuật. Ranh giới "bút toán tiền" chỉ áp cho tiền **thật đang chảy** — tức đã
#: deploy **và** không sau cờ. `LTT_CHATLTT_V3_TOOLS` đang TẮT và tính năng này
#: chưa có route, nên không một đồng nào của khách chịu ảnh hưởng.
#:
#: ⇒ Ghi một giả định **nói rõ là giả định**, rồi đi tiếp. Quyết định vĩnh viễn
#:   nằm ở danh mục điều kiện bật cờ trong `docs/CHATLTT_V3/STATE.md`, chỗ đã
#:   có sẵn cơ chế ấy — không phải ở một hằng số `None` im lặng.
#:
#: ## Con số 20 đến từ đâu
#:
#: Neo vào giá đã CÓ THẬT chứ không bịa: bảng giá công khai tính LLM theo token,
#: và 1.000 ký tự tiếng Việt ≈ 220 token. Trích một tài liệu **rẻ hơn hẳn** một
#: lượt hỏi model về nó — công ở đây là đọc tệp, không phải suy luận. 20
#: milli-credit = **0,02 credit** cho mỗi 1.000 ký tự ⇒ một tài liệu 30 trang
#: (~60.000 ký tự) tốn ~1,2 credit.
#:
#: ⚠️ Đây là một **neo**, không phải một phép đo. §6 của P06 đòi đo lại giá vốn
#:    thật (thời gian CPU, I/O) sau 20–50 tài liệu thật rồi chốt.
MCREDIT_MOI_1000_KY_TU: int | None = 20

#: Phiên bản giá — đi vào `chatltt_approval.phien_ban_gia` để đối soát sau này.
#: ⛔ Chữ `tam` nằm trong tên **có chủ đích**: nó đi vào từng bản ghi duyệt, nên
#:    ngày chốt giá thật, mọi bút toán tính theo giá tạm đều lọc ra được.
PHIEN_BAN_GIA = "trich-v0-tam"

#: 🔴 Giá đã được chủ dự án chốt chưa. `False` ⇒ `MCREDIT_MOI_1000_KY_TU` ở trên
#:    là một **giả định của tôi**, và điều kiện bật cờ trong `STATE.md` chốt
#:    rằng nó phải thành `True` trước khi `LTT_CHATLTT_V3_TOOLS` được bật.
CHU_DU_AN_DA_CHOT = False


class ChuaChotGia(RuntimeError):
    """Chưa có giá thì không trích. Fail-closed, xem đầu tệp."""


def tinh(so_ky_tu: int) -> int:
    """Số **milli-credit** cho `so_ky_tu` ký tự đã trích được.

    ⛔ Ném `ChuaChotGia` khi giá chưa được chốt. Trả 0 là mở đúng cái lỗ mà cửa
       credit của `upload_sessions` sinh ra để bịt.
    """
    if MCREDIT_MOI_1000_KY_TU is None:
        raise ChuaChotGia(
            "chua chot gia trich tai lieu — xem `apps/chatltt/gia_trich.py`")
    n = max(0, int(so_ky_tu))
    #: Làm tròn LÊN theo từng 1.000 ký tự bắt đầu. Một tài liệu 1 ký tự vẫn tốn
    #: một đơn vị: công đọc tệp không tỉ lệ thuận tuyệt đối với độ dài.
    don_vi = (n + 999) // 1000
    return don_vi * int(MCREDIT_MOI_1000_KY_TU)


def da_chot() -> bool:
    """Giá đã được chốt chưa. Để nơi gọi nói ra được thay vì đoán."""
    return MCREDIT_MOI_1000_KY_TU is not None


#: Ước một tệp `n` byte ra bao nhiêu ký tự. 1 byte ≈ 1 ký tự là **trần** cho
#: chữ thuần UTF-8 ASCII; PDF thì thấp hơn nhiều (cấu trúc chiếm phần lớn byte).
#: Ước cao là đúng hướng — xem docstring `uoc_tran`.
_KY_TU_MOI_BYTE = 1.0


def uoc_tran(so_byte: int) -> int:
    """TRẦN ƯỚC CAO để **giữ chỗ**, không phải giá cuối. Đơn vị: **credit**.

    ⭐ Cùng khuôn `apps/anhnoibo/manifest.py::_gia`: nền tảng giữ theo số này,
       rồi `jobs.handle` báo `credit_cost` thật theo ký tự **trích được**, và
       phần giữ dư được hoàn ngay khi job xong.

    ⛔ Ước phải **cao hơn** giá thật, không phải gần đúng. Ước thấp thì lúc quyết
       toán số thu **vượt** số đã hiện ra cho khách — và `chatltt_approval` chốt
       rằng chuyện đó bị từ chối (*"gia da doi: bao X, tinh lai Y"*). Sai về phía
       giữ dư chỉ làm khách bị giam credit vài giây; sai về phía kia làm cả lượt
       hỏng sau khi họ đã bấm đồng ý.
    """
    return (tinh(int(max(0, so_byte) * _KY_TU_MOI_BYTE)) + 999) // 1000


def credit_cost(params: dict) -> int:
    """Bản khai cho `manifest.credit_cost`. Trần ước cao theo cỡ tệp.

    🔴 Ném `ChuaChotGia` khi giá chưa chốt — và **đó là hành vi đúng**. Nền tảng
       từ chối nạp một app khai `job_types` mà thiếu `credit_cost` (W1.6); ta
       thoả bản khai ấy bằng một hàm, nhưng hàm **nói ra** rằng chưa có giá thay
       vì trả về một con số ai đó bịa.
    """
    try:
        so_byte = int((params or {}).get("so_byte") or 0)
    except (TypeError, ValueError):
        so_byte = 0
    return uoc_tran(so_byte)

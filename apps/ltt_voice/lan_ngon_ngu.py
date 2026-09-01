"""
lan_ngon_ngu.py — LÀN của một giọng, và việc đối chiếu nó với văn bản.

## Làn là gì, và vì sao nó tồn tại khi engine đã song ngữ

VieNeu-TTS v3 Turbo **song ngữ thật**: model card khai `language: ["vi", "en"]`,
train from scratch trên ~10.000 giờ tiếng Anh–Việt, và có code-switching En–Vi
trong cùng một câu. Đo 01/09/2026 trên engine thật, ASR nghe lại:

    VAO : The quick brown fox jumps over the lazy dog.
    ASR : The quick brown fox jumps over the lazy dog.       [en 0,996]

Đúng từng chữ. Nên **làn KHÔNG phải một giới hạn kỹ thuật** — không có gì chặn
một giọng nguồn tiếng Anh đọc tiếng Việt.

Làn là một chốt **chất lượng**, chốt 01/09/2026 bởi chủ sản phẩm: clip nguồn
tiếng Việt phục vụ văn bản tiếng Việt, clip nguồn tiếng Anh phục vụ văn bản
tiếng Anh. Lý do đến từ cách kho giọng cũ được xây — F5-TTS train bằng giọng
Việt, XTTS bằng giọng Anh — và đó là kinh nghiệm mua bằng thời gian.

## ⛔ CẢNH BÁO, KHÔNG CHẶN. Và đây là chỗ dễ làm sai nhất.

Tiếng Việt **viết không dấu vẫn là tiếng Việt**, và nó chỉ gồm chữ cái ASCII —
tức không phân biệt được với tiếng Anh bằng bảng mã. "Ban co the mua ve o day"
và "Ban co the" là cùng một tập ký tự với một câu tiếng Anh.

Một cổng CHẶN theo phán đoán ngôn ngữ sẽ từ chối công việc hợp lệ của khách
đang gõ không dấu — và nó từ chối với một lý do khách không sửa được, vì họ
đang gõ đúng thứ họ định gõ.

⇒ Nên `doan_ngon_ngu` chỉ trả lời khi nó **chắc**, và trả `None` khi mập mờ.
  Và `doi_chieu` chỉ sinh **cảnh báo**. Không có đường nào ở đây ném lỗi.

⭐ Hệ quả thiết kế: thứ làm việc chính không phải cảnh báo mà là **bộ lọc ở
   danh sách giọng** — khách chọn đúng làn từ đầu thì không bao giờ chạm tới
   cảnh báo này.
"""
from __future__ import annotations

from platform_core.i18n import N_

#: Ký tự CHỈ có trong tiếng Việt (không kể chữ cái ASCII trần). Thấy một cái là
#: đủ kết luận `vi` — không ngôn ngữ nào khác trong phạm vi sản phẩm dùng chúng.
#:
#: ⛔ `đ`/`Đ` có mặt ở đây; `ê`, `ô`, `ơ`, `ư` cũng vậy. Nhưng `é`, `à`, `ù`…
#:    KHÔNG đủ một mình để kết luận (tiếng Pháp, tiếng Tây Ban Nha cũng có) —
#:    dù trong phạm vi hai làn vi/en của ta thì chúng vẫn chỉ có thể là tiếng
#:    Việt, nên chúng nằm trong danh sách. Ghi rõ ràng buộc ấy ở đây để ngày
#:    thêm làn thứ ba thì người sửa thấy ngay chỗ phải xem lại.
CHU_VIET = set(
    "àáảãạăằắẳẵặâầấẩẫậ"
    "èéẻẽẹêềếểễệ"
    "ìíỉĩị"
    "òóỏõọôồốổỗộơờớởỡợ"
    "ùúủũụưừứửữự"
    "ỳýỷỹỵ"
    "đ"
)
CHU_VIET |= {c.upper() for c in CHU_VIET}

#: Từ chức năng tiếng Anh — tập đóng, và được **sàng qua một phép đo**, không
#: chọn bằng cảm tính: mọi từ ở đây đã đối chiếu với danh sách âm tiết tiếng
#: Việt viết không dấu hay gặp. Kết quả sàng: `them` (thêm), `than` (thân),
#: `then`, `be` (bé), `me` (mẹ), `my` (Mỹ), `in`, `to`, `no`, `he` đều **bị
#: loại** vì trùng.
#:
#: ⚠️ Còn ĐÚNG MỘT từ trùng và nó ở lại có chủ ý: **`the`** — tiếng Việt không
#:    dấu của "thế"/"thể". Nó ở lại vì nó là tín hiệu tiếng Anh mạnh nhất; bỏ
#:    nó thì "The quick brown fox jumps over the lazy dog" chỉ còn **một** từ
#:    trúng và tụt xuống dưới ngưỡng. Thứ giữ cho nó an toàn là `TOI_THIEU_TU_ANH
#:    = 2`: một câu tiếng Việt không dấu muốn bị nhận nhầm thì phải trúng **hai**
#:    từ, mà "the" là từ trùng duy nhất.
#:
#: ⛔ Thêm từ vào đây thì phải chạy lại phép sàng ấy —
#:    `tests/test_384_lan_ngon_ngu.py::test_tu_chuc_nang_khong_trung_am_tiet_tieng_viet_khong_dau`.
#:    Một từ như "can", "co", "la", "ma" lọt vào là biến "Ban co the mua ve"
#:    thành tiếng Anh.
TU_ANH = frozenset("""
about after also because been before being between could does during each
even every first from give have having into just know last like make many
might more most much must need only other our over people please said says
shall should some still such take thank that the their there these they
think this those through time under upon very want were what when where
which while will with within would year your
""".split())

#: Cần ít nhất chừng này TỪ KHÁC NHAU trong `TU_ANH` mới dám nói `en`.
#: Một từ thì quá dễ trúng ngẫu nhiên trong một câu tiếng Việt có chèn thuật ngữ.
TOI_THIEU_TU_ANH = 2

NHAN_LAN = {"vi": N_('Tiếng Việt'), "en": N_('Tiếng Anh')}


def doan_ngon_ngu(text: str):
    """`"vi"` · `"en"` · `None` khi không chắc.

    ⛔ `None` là một câu trả lời ĐẦY ĐỦ, không phải một thất bại. Nó nói "văn
       bản này không đủ dấu hiệu", và tầng trên phải im lặng khi gặp nó. Trả
       bừa `"vi"` cho mọi thứ mập mờ sẽ đẻ ra cảnh báo sai ở mọi câu tiếng Anh
       ngắn — và một cảnh báo hay sai là một cảnh báo bị bỏ qua, kể cả lúc đúng.
    """
    t = (text or "").strip()
    if not t:
        return None
    if any(c in CHU_VIET for c in t):
        return "vi"
    tu = {w.strip(".,!?;:\"'()[]").lower() for w in t.split()}
    if len(tu & TU_ANH) >= TOI_THIEU_TU_ANH:
        return "en"
    return None


def doi_chieu(lan_giong: str, text: str) -> tuple:
    """Cảnh báo (dạng tuple chuỗi) khi văn bản lệch làn của giọng. Không ném.

    Trả tuple rỗng khi khớp, khi không đoán được, hoặc khi giọng chưa có làn.
    """
    lan = (lan_giong or "").strip().lower()
    if lan not in ("vi", "en"):
        return ()
    do = doan_ngon_ngu(text)
    if do is None or do == lan:
        return ()
    return (N_(
        'Giọng này thuộc làn {lan_giong}, nhưng văn bản có vẻ là {lan_text}. '
        'Bạn vẫn tạo được, chỉ là chất lượng có thể không bằng một giọng '
        'cùng làn.'),)


def dien_canh_bao(mau: str, lan_giong: str, lan_text: str) -> str:
    """Điền nhãn vào khuôn cảnh báo. Tách khỏi `doi_chieu` để chuỗi dịch được.

    ⛔ Đừng nối chuỗi bằng f-string ở `doi_chieu`: `N_()` phải nhìn thấy một
       chuỗi HẰNG thì bộ trích mới lấy được nó vào tệp `.po`. Một câu ghép động
       sẽ không bao giờ xuất hiện trong bản dịch, và nó hỏng **lặng lẽ** — trang
       tiếng Anh hiện một câu tiếng Việt.
    """
    return str(mau).replace("{lan_giong}", str(NHAN_LAN.get(lan_giong, lan_giong))) \
                   .replace("{lan_text}", str(NHAN_LAN.get(lan_text, lan_text)))

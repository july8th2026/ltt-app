"""
lan_ngon_ngu.py — LÀN của một giọng, và HỢP ĐỒNG tương thích văn bản ↔ giọng.

Đây là **thẩm quyền duy nhất** trả lời câu hỏi *"văn bản này có được đọc bằng
giọng kia không"*. Mọi cửa (Studio, Dự án, worker, Public API) đi qua
`quyet_dinh()`; không cửa nào được tự phán.

## Làn là gì, và vì sao nó tồn tại khi engine đã song ngữ

VieNeu-TTS v3 Turbo **song ngữ thật**: model card khai `language: ["vi", "en"]`,
train from scratch trên ~10.000 giờ tiếng Anh–Việt, và có code-switching En–Vi
trong cùng một câu. Đo 01/09/2026 trên engine thật, ASR nghe lại:

    VAO : The quick brown fox jumps over the lazy dog.
    ASR : The quick brown fox jumps over the lazy dog.       [en 0,996]

Đúng từng chữ. Nên làn **không phải một giới hạn kỹ thuật** — không có gì chặn
một giọng nguồn tiếng Anh đọc tiếng Việt.

Làn là một chốt **chất lượng**: clip nguồn tiếng Việt phục vụ văn bản tiếng
Việt, clip nguồn tiếng Anh phục vụ văn bản tiếng Anh. Lý do đến từ cách kho
giọng cũ được xây — F5-TTS train bằng giọng Việt, XTTS bằng giọng Anh — và đó là
kinh nghiệm mua bằng thời gian.

## 🔴 QUYẾT ĐỊNH ĐÃ ĐỔI — Q121 (2026-09-10): CHẶN, không còn chỉ cảnh báo

~~Chốt 01/09/2026: đối chiếu làn chỉ sinh **cảnh báo**, không có đường nào ở đây
ném lỗi.~~ **ĐÃ THAY bởi Q121 (2026-09-10).**

Vì sao đổi — ba thứ đo được trên chính cây này, không phải một sở thích kiến
trúc:

  ① Cảnh báo **không tới ai cả.** `giai_giong` trả tuple cảnh báo, và **cả hai**
     người gọi vứt nó đi (`ref_b64, preset, _ = …` ở `jobs.py` lẫn ở
     `routes/_p_tao.py`). Một cảnh báo không có người đọc là một cảnh báo không
     tồn tại.
  ② Ngay cả khi có người đọc, nó **không đọc được**: `doi_chieu` trả khuôn còn
     nguyên chỗ trống `{lan_giong}`/`{lan_text}`, và `dien_canh_bao` — hàm điền
     chỗ trống ấy — không có người gọi nào.

     ⚠️ ĐÚĐỢC Ở BASE `9e73bf1f`, **HẾT ĐÚNG TỪ 07/09**: trunk tự tìm ra và sửa
        độc lập trong lúc phiên này đang chạy. Bản hoà 10/09 giữ **bản sửa của
        trunk**, không giữ bản của tôi — vì bản của tôi (`return (MAU_LECH_LAN,)`)
        đã **tái tạo đúng lỗi ấy**: tôi trả một khuôn chưa điền, sau khi vừa
        viết ra chẩn đoán nói rằng trả khuôn chưa điền là sai.
  ③ Và ô `Ngôn ngữ` của khách **không xuống tới worker**: `routes/_p_tao.tao`
     nhận `ngon_ngu` rồi bỏ nó ra khỏi `params` lúc nộp job. Nên nhánh "khách
     tự khai" — nhánh mạnh nhất — chưa bao giờ chạy trong sản phẩm.

⇒ Ba tầng đều hỏng theo hướng **im lặng cho qua**. Một yêu cầu lệch làn tạo ra
  một job GPU hợp lệ, giữ credit của khách, chạy hết, và trả về một bản đọc
  chất lượng thấp mà khách vẫn phải trả tiền.

⭐ Và lý do CŨ vẫn đúng — nó không bị vứt đi, nó được **giữ bằng luật giải
   ngôn ngữ** dưới đây, không bằng cách bỏ cửa chặn. Xem `quyet_dinh` (nấc
   `NGUON_THEO_GIONG`, khi `doan_ngon_ngu` không chắc và khách không khai).

## ⛔ TIẾNG VIỆT KHÔNG DẤU — cái bẫy mà cửa chặn PHẢI đi vòng qua

Tiếng Việt viết không dấu vẫn là tiếng Việt, và nó chỉ gồm chữ cái ASCII — tức
không phân biệt được với tiếng Anh bằng bảng mã. *"Ban co the mua ve o day"* là
cùng một tập ký tự với một câu tiếng Anh.

Một cổng chặn theo phán đoán ngôn ngữ **thô** sẽ từ chối công việc hợp lệ của
khách đang gõ không dấu — và nó từ chối với một lý do khách không sửa được, vì
họ đang gõ đúng thứ họ định gõ.

⇒ Nên luật giải là: `doan_ngon_ngu` chỉ trả lời khi nó **chắc**; và khi nó không
  chắc, văn bản **nhận làn của chính giọng đang chọn** (`NGUON_THEO_GIONG`).
  Hệ quả là *sự mập mờ không bao giờ là thứ chặn* — chỉ bằng chứng dương mới
  chặn được. Phép kiểm chốt đúng mệnh đề đó ở
  `tests/test_355_hop_dong_lan_giong.py`.

## ⛔ GIỌNG chưa rõ làn thì KHÔNG cho đọc — và đây là chiều sai ngược lại

`voice_profile.ngon_ngu` là `String(16)` mặc định `"vi"`, nên một hàng mang
`""` hay `"xx"` là chuyện có thật (dữ liệu nhập từ kho cũ). Trước Q121, giá trị
lạ rơi vào nhánh *"chưa có làn ⇒ im lặng"* và đi thẳng tới GPU.

Đó là hướng sai **đắt hơn**: với văn bản ta chỉ mất một cảnh báo, còn với giọng
ta bán một bản đọc mà chính ta không biết nó thuộc làn nào. Nên hai chiều **cố ý
không cân nhau**: văn bản mập mờ ⇒ cho qua; giọng mập mờ ⇒ chặn.
"""
from __future__ import annotations

from dataclasses import dataclass

from platform_core.i18n import N_

#: Ba giá trị làn, và **chỉ** ba. `KHONG_RO` là chuỗi rỗng có chủ ý: nó là thứ
#: `str(x or "")` cho ra khi dữ liệu khuyết, nên không ai phải nhớ một hằng số
#: đặc biệt để biểu diễn "không biết".
LAN_VI = "vi"
LAN_EN = "en"
KHONG_RO = ""

#: Tập làn **hợp lệ**. Mọi nơi hỏi "giá trị này có phải một làn không" phải hỏi
#: tập này, đừng gõ lại `("vi", "en")` — gõ lại là chỗ làn thứ ba sẽ bị bỏ sót.
LAN_HOP_LE = (LAN_VI, LAN_EN)

#: Vùng miền của một giọng mẫu ⇒ bằng chứng làn. Xem `lan_tu_vung`.
VUNG_VI = frozenset(("bac", "trung", "nam"))

#: Mã lỗi ỔN ĐỊNH cho GUI và Public API. **Chuỗi, không phải số**, và tiếng Anh
#: không dấu: nó đi vào JSON, vào log, vào mã của khách tích hợp — ba nơi mà
#: một câu tiếng Việt có dấu là một gánh nặng chứ không phải một thông tin.
#:
#: ⛔ ĐỔI GIÁ TRỊ Ở ĐÂY LÀ MỘT THAY ĐỔI PHÁ VỠ. Khách bắt lỗi theo mã, không
#:    theo câu chữ — câu chữ còn đổi theo ngôn ngữ giao diện.
MA_LOI_LECH_LAN = "voice_language_mismatch"
MA_LOI_LAN_KHONG_RO = "voice_language_unknown"

#: Làn của văn bản đến TỪ ĐÂU. Đi kèm phán quyết vì nó là thứ duy nhất trả lời
#: được câu *"vì sao lượt này bị chặn còn lượt kia thì không"*.
NGUON_KHAI_BAO = "khai_bao"      # khách tự chọn ở ô Ngôn ngữ
NGUON_DOAN = "doan"              # máy đoán, và đoán CHẮC
NGUON_THEO_GIONG = "theo_giong"  # không đoán được ⇒ nhận làn của giọng
NGUON_KHONG_RO = "khong_ro"      # chưa giải được vì chính GIỌNG chưa rõ làn

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
#:
#: 🔴 VÀ TỪ Q121 TẬP NÀY CÒN CHẶN ĐƯỢC VIỆC, không chỉ cảnh báo được. Một từ
#:    thêm sai ở đây nay từ chối công việc của khách. Ngưỡng an toàn không đổi;
#:    cái đổi là **giá của việc sai**.
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

NHAN_LAN = {LAN_VI: N_('Tiếng Việt'), LAN_EN: N_('Tiếng Anh')}

#: Khuôn câu từ chối. Chỗ trống điền bằng `dien_canh_bao`, **không** bằng
#: f-string — xem docstring của `dien_canh_bao`.
MAU_LECH_LAN = N_(
    'Giọng này thuộc làn {lan_giong}, nhưng văn bản là {lan_text}. '
    'Hãy chọn một giọng cùng làn với văn bản, hoặc sửa ô Ngôn ngữ cho khớp.')

MAU_LAN_KHONG_RO = N_(
    'Giọng này chưa xác định được làn ngôn ngữ nên chưa dùng để đọc được. '
    'Hãy chọn một giọng đã ghi rõ Tiếng Việt hoặc Tiếng Anh.')


def chuan_lan(x) -> str:
    """Bất cứ thứ gì ⇒ `"vi"` · `"en"` · `""`.

    ⭐ MỘT chỗ chuẩn hoá cho cả cột CSDL, ô form, tham số API và trường JSON.
       Bốn nơi tự ép kiểu là bốn nơi sẽ ép khác nhau — và cái lệch đầu tiên gần
       như chắc chắn là hoa/thường (`"EN"` từ một khách tích hợp).
    """
    lan = str(x or "").strip().lower()
    return lan if lan in LAN_HOP_LE else KHONG_RO


def lan_tu_vung(vung: str) -> str:
    """Vùng miền của một giọng mẫu ⇒ làn của nó.

    🔴 VÌ SAO SUY TỪ `vung` CHỨ KHÔNG KHAI THÊM MỘT CỘT `language`.

       Ảnh chụp preset của engine (`giong_mau_engine.json`) **không có** trường
       ngôn ngữ, và nó không nên có: tệp ấy là ảnh chụp thứ engine nói, sinh ra
       bởi `tools/sinh_giong_mau_engine.py`, và engine không nói gì về ngôn ngữ.
       Thêm một trường mà máy sinh không sinh được là mời người ta sửa tay một
       tệp đã ghi rõ *"SINH RA, dung sua tay"*.

    ⭐ Nhưng dữ liệu để trả lời thì **đã có sẵn**: `vung ∈ {bac, trung, nam}` là
       ba miền của tiếng Việt. Một giọng mang giọng vùng Bắc Bộ là một giọng
       tiếng Việt — đó không phải một suy đoán, đó là đọc đúng thứ dữ liệu đang
       nói. Nên ở đây không có hệ metadata thứ hai, chỉ có một phép đọc.

    ⛔ Và ngày engine ship một preset KHÔNG thuộc ba miền ấy, hàm này trả
       `KHONG_RO` — tức preset đó bị **chặn** cho tới khi có người khai làn cho
       nó. Đó là hướng sai đúng: một giọng mới xuất hiện không được tự nhận là
       tiếng Việt chỉ vì mọi giọng trước nó đều thế.
    """
    return LAN_VI if str(vung or "").strip().lower() in VUNG_VI else KHONG_RO


# 🔴 HOÀ TRUNK 2026-09-10 — `_MAU_LECH_LAN` CỦA TRUNK ĐÃ GỠ Ở ĐÂY, có chủ ý.
#
#    Trunk (07/09) tách một hằng `_MAU_LECH_LAN` cho `doi_chieu`. Việc tách ấy
#    ĐÚNG và bản sửa đi kèm nó cũng đúng (xem `doi_chieu`). Nhưng nội dung câu
#    thì hết đúng từ Q121: nó kết bằng *"Bạn vẫn tạo được, chỉ là chất lượng có
#    thể không bằng một giọng cùng làn"* — trong khi cửa nộp nay **từ chối**.
#
# ⛔ Giữ cả hai hằng là giữ hai câu nói hai điều trái nhau về cùng một tình
#    huống, và câu sai lại là câu nói nhẹ nhàng hơn — thứ khó phát hiện hơn hẳn
#    một câu sai nói to. `MAU_LECH_LAN` ở trên là bản DUY NHẤT.


def doan_ngon_ngu(text: str):
    """`"vi"` · `"en"` · `None` khi không chắc.

    ⛔ `None` là một câu trả lời ĐẦY ĐỦ, không phải một thất bại. Nó nói "văn
       bản này không đủ dấu hiệu", và `quyet_dinh` xử lý nó bằng cách nhận làn
       của giọng (`NGUON_THEO_GIONG`) — chứ không bằng cách chặn.

    ⭐ TRỘN NGÔN NGỮ đi qua đây, và luật là **bằng chứng dương thắng**: chỉ cần
       một chữ có dấu tiếng Việt là `vi`, kể cả khi câu đầy thuật ngữ tiếng Anh
       (*"Xin chào, đây là bản demo của the new API"* ⇒ `vi`). Không đối xứng,
       và cố ý: dấu tiếng Việt là bằng chứng **không thể nhầm**, còn từ chức
       năng tiếng Anh thì có thể trùng âm tiết Việt không dấu.
    """
    t = (text or "").strip()
    if not t:
        return None
    if any(c in CHU_VIET for c in t):
        return LAN_VI
    tu = {w.strip(".,!?;:\"'()[]").lower() for w in t.split()}
    if len(tu & TU_ANH) >= TOI_THIEU_TU_ANH:
        return LAN_EN
    return None


@dataclass(frozen=True)
class PhanQuyet:
    """Câu trả lời đầy đủ cho *"có được đọc không"* — kèm **vì sao**.

    ⛔ Một `bool` trần thì không đủ. Cửa gọi cần mã lỗi để trả cho khách tích
       hợp, cần khuôn câu để dịch, và cần `nguon` để trả lời câu hỏi hỗ trợ hay
       gặp nhất: *"sao lượt này bị chặn còn lượt hôm qua thì không"*.
    """

    cho_phep: bool
    lan_giong: str = KHONG_RO
    lan_text: str = KHONG_RO
    nguon: str = NGUON_KHONG_RO
    ma_loi: str = ""
    #: Khuôn `N_()` chưa điền chỗ trống và **chưa dịch**. Dịch ở biên hiển thị,
    #: bằng `cau_cho_khach` — không dịch ở đây, vì hàm này chạy cả trong worker
    #: nơi không có ngôn ngữ của người dùng nào cả.
    mau: str = ""


def quyet_dinh(lan_giong: str, text: str, khai_bao: str = "") -> PhanQuyet:
    """🔴 THẨM QUYỀN DUY NHẤT của hợp đồng tương thích.

    ====================  ==========================================================
    Điều kiện              Phán quyết
    ====================  ==========================================================
    giọng chưa rõ làn      CHẶN ``voice_language_unknown``
    khai ≠ làn giọng       CHẶN ``voice_language_mismatch``, ``nguon=khai_bao``
    khai == làn giọng
      + đoán CHẮC ≠ làn giọng  CHẶN ``voice_language_mismatch``, ``nguon=doan`` (D002)
    còn lại, cùng làn      cho phép
    ====================  ==========================================================

    ⛔ Bảng này KHÔNG có ô "song ngữ". Engine đọc được cả hai làn, nhưng *đọc
       được* và *đọc hay* là hai câu khác nhau, và thứ khách trả tiền là câu thứ
       hai. Ngày có bằng chứng đo được rằng một giọng phục vụ tốt cả hai làn thì
       thêm làn thứ ba (`bilingual`) vào `LAN_HOP_LE` — **kèm phép đo**, không
       kèm một suy luận.

    ⚠️ KHÔNG NÉM. Trả phán quyết; việc dịch nó thành lỗi là của `features`. Tách
       vậy để chính hàm này gọi được từ chỗ chỉ muốn *hiện* trạng thái (bộ chọn
       giọng) mà không phải bọc `try`.
    """
    lan_g = chuan_lan(lan_giong)
    if not lan_g:
        # Giọng mập mờ ⇒ CHẶN. Chiều ngược với văn bản mập mờ, và cố ý —
        # xem docstring đầu tệp.
        return PhanQuyet(cho_phep=False, ma_loi=MA_LOI_LAN_KHONG_RO,
                         mau=MAU_LAN_KHONG_RO)

    khai = chuan_lan(khai_bao)
    if khai and khai != lan_g:
        return PhanQuyet(cho_phep=False, lan_giong=lan_g, lan_text=khai,
                         nguon=NGUON_KHAI_BAO, ma_loi=MA_LOI_LECH_LAN,
                         mau=MAU_LECH_LAN)
    # 🔴 D002 (2026-09-11): phép đoán CHẮC vẫn chạy khi khách đã khai. Lời khai
    #    chỉ được THÊM ràng buộc; nó không bao giờ là giấy miễn trừ cho một văn
    #    bản mà máy biết chắc là làn kia. Trước D002, khai `vi` rồi dán văn bản
    #    tiếng Anh CHẮC chắn lọt qua — giọng Việt đọc tiếng Anh, khách trả tiền
    #    cho đúng lỗi chất lượng mà Q121 dựng ra để chặn.
    doan = doan_ngon_ngu(text)
    if doan and doan != lan_g:
        return PhanQuyet(cho_phep=False, lan_giong=lan_g, lan_text=doan,
                         nguon=NGUON_DOAN, ma_loi=MA_LOI_LECH_LAN,
                         mau=MAU_LECH_LAN)
    if khai:
        return PhanQuyet(cho_phep=True, lan_giong=lan_g, lan_text=khai,
                         nguon=NGUON_KHAI_BAO)
    if doan:
        return PhanQuyet(cho_phep=True, lan_giong=lan_g, lan_text=doan,
                         nguon=NGUON_DOAN)
    return PhanQuyet(cho_phep=True, lan_giong=lan_g, lan_text=lan_g,
                     nguon=NGUON_THEO_GIONG)


def cau_cho_khach(pq: PhanQuyet) -> str:
    """Phán quyết ⇒ câu người dùng đọc, **đã dịch và đã điền chỗ trống**.

    ⭐ Đây là biên hiển thị, nên dịch ở đây chứ không sớm hơn. `quyet_dinh` chạy
       cả trong worker — dịch trong đó là ghim ngôn ngữ của tiến trình vào một
       thông điệp mà nhiều phiên cùng đọc (đúng cái bẫy `tuy_chon_preset` ghi).
    """
    from platform_core.i18n import _ as _t

    if not pq.mau:
        return ""
    return dien_canh_bao(str(_t(pq.mau)), pq.lan_giong, pq.lan_text)


def doi_chieu(lan_giong: str, text: str, khai_bao: str = "") -> tuple:
    """Cảnh báo (tuple chuỗi) khi văn bản lệch làn. **Không ném, không chặn.**

    ⚠️ TỪ Q121 ĐÂY KHÔNG CÒN LÀ CỬA QUYẾT ĐỊNH. Cửa quyết định là `quyet_dinh`;
       hàm này chỉ còn phục vụ những màn *hiển thị* trạng thái. Giữ nguyên chữ
       ký và ngữ nghĩa cũ để không nơi nào đang gọi nó phải sửa theo.

    ⛔ Và giữ nguyên cả điểm mù cũ, có chủ ý: giọng **chưa rõ làn** ở đây trả
       tuple rỗng (không có gì để *cảnh báo*), trong khi `quyet_dinh` **chặn**
       đúng ca ấy. Hai hàm trả lời hai câu khác nhau — "có gì đáng nói không"
       và "có được chạy không" — nên chúng được phép khác nhau. Nhập chúng làm
       một là mất đúng một trong hai câu.

    ⭐ DÙNG LẠI ĐÚNG KHUÔN CÂU của cửa chặn (`MAU_LECH_LAN`) chứ không giữ khuôn
       cảnh báo cũ. Khuôn cũ kết bằng *"Bạn vẫn tạo được, chỉ là chất lượng có
       thể không bằng…"* — một câu **hết đúng** từ Q121, và một câu sai nói với
       giọng nhẹ nhàng thì còn khó phát hiện hơn một câu sai nói to. Hai chỗ nói
       về cùng một tình huống thì phải nói cùng một điều.
    """
    pq = quyet_dinh(lan_giong, text, khai_bao)
    if pq.ma_loi != MA_LOI_LECH_LAN:
        return ()
    # 🔴 TRẢ CÂU ĐÃ ĐIỀN, KHÔNG TRẢ KHUÔN — bản sửa của trunk (07/09), giữ nguyên.
    #
    #    Trước 07/09/2026 hàm này trả về **khuôn còn chỗ trống**, và người gọi
    #    được kỳ vọng gọi `dien_canh_bao` sau. Không người gọi nào làm thế, nên
    #    nếu cảnh báo có bao giờ tới được màn hình thì khách đọc đúng chuỗi
    #    `"...làn {lan_giong}, nhưng văn bản có vẻ là {lan_text}"`.
    #
    # ⚠️ BẢN CỦA TÔI ĐÃ TÁI TẠO ĐÚNG LỖI ẤY: nó `return (MAU_LECH_LAN,)` — một khuôn
    #    chưa điền. Tôi viết nó sau khi đã đọc và ghi lại chính lỗi này trong phần
    #    chẩn đoán của mình. Trunk bắt được trước, và đây là bản của trunk.
    #
    # ⭐ `cau_cho_khach` là biên hiển thị: nó DỊCH khuôn rồi điền nhãn đã dịch qua
    #    `dien_canh_bao`. Nên `dien_canh_bao` vẫn là chỗ duy nhất điền, và không
    #    có f-string nào trong `doi_chieu` (`test_384` chốt bằng AST).
    return (cau_cho_khach(pq),)


def dien_canh_bao(mau: str, lan_giong: str, lan_text: str) -> str:
    """Điền nhãn vào khuôn. Tách khỏi `doi_chieu` để chuỗi dịch được.

    ⛔ Đừng nối chuỗi bằng f-string ở `doi_chieu` hay `quyet_dinh`: `N_()` phải
       nhìn thấy một chuỗi HẰNG thì bộ trích mới lấy được nó vào tệp `.po`. Một
       câu ghép động sẽ không bao giờ xuất hiện trong bản dịch, và nó hỏng
       **lặng lẽ** — trang tiếng Anh hiện một câu tiếng Việt.

    ⭐ Nhãn làn cũng dịch ở đây. Trước Q121 hàm này điền nhãn **thô** (`N_()`
       chưa qua `_()`), nên một câu tiếng Anh sẽ kẹp hai chữ tiếng Việt vào
       giữa. Nó không lộ ra vì hàm này **chưa từng được gọi**.
    """
    from platform_core.i18n import _ as _t

    def _nhan(lan: str) -> str:
        nhan = NHAN_LAN.get(lan)
        return str(_t(nhan)) if nhan else str(lan)

    return str(mau).replace("{lan_giong}", _nhan(lan_giong)) \
                   .replace("{lan_text}", _nhan(lan_text))

"""
text_pipeline.py — chuẩn hoá văn bản **cấp sản phẩm** cho VI/EN.

⛔ KHÔNG VIẾT LẠI G2P. `sea-g2p` (Rust, do chính tác giả VieNeu viết) lo phần âm
   vị. Việc ở đây chỉ là những thứ **nó không thể biết** vì chúng là quy ước sản
   phẩm chứ không phải quy tắc ngôn ngữ:

     · một ký hiệu (`%`, `₫`, `$`) không có cách đọc — phải thay bằng chữ
     · `12/08/2026` là ngày hay một phép chia — chỉ ngữ cảnh sản phẩm biết
     · `1.` đầu dòng là số thứ tự hay là "một chấm"
     · tên riêng của khách và các cặp `ch`/`tr` cần từ điển riêng

🔴 CÁI GÌ CỐ Ý **KHÔNG** LÀM, VÀ VÌ SAO.

   Đọc số trần (`27` -> "hai mươi bảy") **mặc định TẮT** (`doc_so_tran=False`).
   Không phải vì khó, mà vì **chưa đo**: nếu `sea-g2p` đã đọc số đúng thì ta đang
   sửa một thứ không hỏng, và tệ hơn là có thể sinh ra đọc hai lần. Ma trận khói
   V1 có đúng một ô cho việc này. Đo xong rồi mới bật, và bật bằng cách sửa mặc
   định ở đây chứ không rải cờ khắp nơi.

   ⭐ Đây là khác biệt giữa "chuẩn hoá" và "đoán": ký hiệu thì **chắc chắn** cần
      thay (không ai đọc được `%`), còn chữ số thì **có thể** đã đúng sẵn.

⚠️ GIỮ PHÉP BIẾN ĐỔI SOI ĐƯỢC. Lịch sử job ghi cả text gốc lẫn text đã chuẩn hoá
   (`ket_qua()` trả cả hai). Không có điều đó thì một lượt đọc sai không bao giờ
   truy được là do model hay do chính ta.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from . import tu_dien

# ── ký hiệu: chắc chắn phải thay, không ai đọc được một ký hiệu ───────────────
_KY_HIEU = [
    # 🔴 DẤU BA CHẤM — upstream issue #112, VÀ NÓ CHƯA ĐƯỢC SỬA Ở UPSTREAM.
    #
    #    Người báo lỗi: engine không ngắt hơi ở `...` như nó ngắt ở `,` hay `.`.
    #    Tác giả sửa `...` trong `sea-g2p` 0.6.8. Nhưng người báo lỗi chỉ ra
    #    tiếp: `…` (U+2026, MỘT ký tự) **khác** `...` (BA ký tự), và bản vá kia
    #    không chạm tới nó. Tác giả trả lời *"Will add normalization for it in
    #    the next patch"* — bản vá đó chưa có.
    #
    # ⭐ Nên `…` là của TA phải sửa, không chờ được. Đổi thành một dấu chấm:
    #    đó đúng là thứ `sea-g2p` 0.6.8 làm với `...`, nên ta chỉ đang đưa ký tự
    #    còn thiếu về cùng một chỗ.
    #
    # ⚠️ Đặt TRƯỚC luật `...`: nếu để sau, `…` vẫn còn nguyên khi luật kia chạy.
    #    `(?:…\s*)+` gộp cả chuỗi: "đã…… thế" cho MỘT dấu chấm, không phải
    #    hai. Hai dấu chấm cách nhau một khoảng trắng là hai câu rỗng.
    (re.compile(r"\s*(?:…\s*)+"), ". "),
    (re.compile(r"\s*\.{3,}\s*"), ". "),
    (re.compile(r"(?<=\d)\s*%"), " phần trăm"),
    # ⚠️ `₫` KHÔNG phải ký tự từ, nên `\b` sau nó không bao giờ khớp — test bắt
    #    được điều này. Tách hai luật: ký hiệu thì không cần biên từ; chữ `đ` thì
    #    cần (nếu không "50 đó" cũng bị nuốt).
    (re.compile(r"(?<=\d)\s*₫"), " đồng"),
    (re.compile(r"(?<=\d)\s*đ\b"), " đồng"),
    (re.compile(r"(?<=\d)\s*VNĐ\b", re.I), " đồng"),
    (re.compile(r"\$\s*(?=\d)"), "đô la "),
    (re.compile(r"(?<=\d)\s*°C\b"), " độ C"),
    (re.compile(r"(?<=\d)\s*km/h\b"), " ki lô mét trên giờ"),
    (re.compile(r"(?<=\d)\s*(?:kg|Kg|KG)\b"), " ki lô gam"),
    (re.compile(r"\s*&\s*"), " và "),
    # 🔴 KHÔNG áp cho GIỮA HAI CHỮ SỐ. `_NGAY` ở trên cố ý từ chối một ngày không
    #    hợp lệ (45/99/2026) và để nguyên cho `sea-g2p` quyết; nếu luật này nuốt
    #    tiếp thì "để nguyên" biến thành "45 trên 99 trên 2026" — tệ hơn hẳn.
    #    Một cặp số ngăn bởi `/` có quá nhiều nghĩa (ngày, phân số, mã số) để đoán.
    (re.compile(r"(?<=[^\W\d])\s*/\s*(?=[^\W\d])"), " trên "),
]

# ── phân cách hàng nghìn: 1.500.000 -> 1500000 (trước khi đụng tới ngày) ──────
#
# ⛔ `(?=\d{3}\b)` là SAI, và nó sai ở đúng cách viết giá thông dụng nhất.
#    `\b` đòi bên phải ba chữ số phải là ranh giới từ, mà `đ` LÀ ký tự chữ
#    trong Unicode — nên `990.000đ` không khớp, và khách nghe một chuỗi không
#    phải số cũng không phải chữ:
#
#        1.250.000        -> 1250000         (dung)
#        1.250.000 đồng   -> 1250000 đồng    (dung — co dau cach nen \b khop)
#        990.000đ         -> 990.000 đồng    (HONG)
#        1.250.000đ       -> 1250.000 đồng   (HONG — bo dau cham dau, giu cai sau)
#
#    Luật `đ` -> " đồng" nằm ở `_LUAT` phía trên và chạy TRƯỚC, nên nó tách
#    được dấu cách; nhưng chỉ ở lượt sau, khi `_NGAN` đã chạy xong rồi.
#
# ⭐ `(?!\d)` diễn đạt đúng điều cần: "ba chữ số và HẾT nhóm số", không quan tâm
#    cái đứng sau là chữ hay dấu. Nó là tập cha thực sự của hành vi cũ — chỉ
#    thêm khớp ở đúng chỗ `\b` trượt, không bỏ chỗ nào đang khớp.
_NGAN = re.compile(r"(?<=\d)\.(?=\d{3}(?!\d))")

# ── ngày và giờ ──────────────────────────────────────────────────────────────
_NGAY = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b")
_GIO = re.compile(r"\b(\d{1,2})[hg:](\d{2})\b")

# ── URL / email: đọc nguyên là rác, rút gọn thành thứ nghe được ───────────────
_URL = re.compile(r"https?://\S+|www\.\S+")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")

# ── số thứ tự đầu dòng: "1." -> "Một." ───────────────────────────────────────
#
# 🔴 Đây là một trong những ô hỏng mà pack V2 nêu đích danh ("numbered lists").
#    Không xử lý thì model đọc "một chấm" hoặc nuốt luôn dấu chấm rồi dính câu
#    sau vào — nghe như một câu dài vô tận.
_STT = re.compile(r"^\s*(\d{1,2})[.)]\s+", re.M)

_KHOANG = re.compile(r"[ \t ]+")
_XUONG_DONG = re.compile(r"\n{3,}")

_DON_VI = ["", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]


def _doc_so_nho(n: int) -> str:
    """0-999 sang chữ. Đủ cho ngày/tháng/giờ; số lớn dùng `_doc_so`."""
    if n == 0:
        return "không"
    ra = []
    tram, du = divmod(n, 100)
    if tram:
        ra += [_DON_VI[tram], "trăm"]
    chuc, dv = divmod(du, 10)
    if chuc == 0:
        if dv:
            if tram:
                ra.append("lẻ")
            ra.append(_DON_VI[dv])
    elif chuc == 1:
        ra.append("mười")
        if dv == 5:
            ra.append("lăm")
        elif dv:
            ra.append(_DON_VI[dv])
    else:
        ra += [_DON_VI[chuc], "mươi"]
        if dv == 1:
            ra.append("mốt")
        elif dv == 4:
            ra.append("tư")
        elif dv == 5:
            ra.append("lăm")
        elif dv:
            ra.append(_DON_VI[dv])
    return " ".join(x for x in ra if x)


_BAC = ["", " nghìn", " triệu", " tỷ"]


def _doc_so(n: int) -> str:
    """Số nguyên sang chữ tiếng Việt. Dùng cho ngày/giờ và cho `doc_so_tran`."""
    if n < 0:
        return "âm " + _doc_so(-n)
    if n < 1000:
        return _doc_so_nho(n)
    nhom = []
    while n > 0:
        n, du = divmod(n, 1000)
        nhom.append(du)
    if len(nhom) > len(_BAC):
        return " ".join(_doc_so_nho(int(c)) for c in str(n))
    phan = []
    for i in range(len(nhom) - 1, -1, -1):
        if nhom[i] == 0:
            continue
        phan.append(_doc_so_nho(nhom[i]) + _BAC[i])
    return " ".join(phan)


@dataclass
class KetQuaChuanHoa:
    goc: str
    da_chuan_hoa: str
    doan: list = field(default_factory=list)
    ghi_chu: tuple = ()

    @property
    def so_ky_tu(self) -> int:
        return len(self.da_chuan_hoa)


def _thay_ngay(m: re.Match) -> str:
    d, thang, nam = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not (1 <= d <= 31 and 1 <= thang <= 12):
        return m.group(0)          # không phải ngày — để nguyên, đừng đoán
    return f"ngày {_doc_so_nho(d)} tháng {_doc_so_nho(thang)} năm {_doc_so(nam)}"


def _thay_gio(m: re.Match) -> str:
    h, p = int(m.group(1)), int(m.group(2))
    if not (0 <= h <= 23 and 0 <= p <= 59):
        return m.group(0)
    if p == 0:
        return f"{_doc_so_nho(h)} giờ"
    return f"{_doc_so_nho(h)} giờ {_doc_so_nho(p)}"


#: Dấu thanh và dấu phụ tiếng Việt ở dạng TỔ HỢP (sau NFD). Dùng để trả lời một
#: câu hỏi duy nhất: chữ này có mang dấu tiếng Việt không.
_DAU_VIET_NFD = frozenset("̣̀́̃̉"  # huyền sắc ngã hỏi nặng
                          "̛̂̆")               # mũ, trăng, móc

#: Một TỪ (chỉ chữ cái, không số, không gạch dưới).
_TU_CHU = re.compile(r"[^\W\d_]+", re.UNICODE)

#: Khoảng ngăn giữa hai từ mà vẫn coi chúng là CÙNG một chuỗi viết hoa. Cố ý
#: hẹp: xuống dòng hay dấu chấm câu nặng thì đó là hai chuỗi khác nhau.
_NGAN_TRONG_CHUOI = re.compile(r"^[ 	.,:;/–-]*$")


#: Nguyên âm tiếng Việt, ở dạng CHỮ GỐC (sau khi bỏ dấu). `y` có mặt vì nó làm
#: âm chính trong "quý", "ly", "mỹ".
_NGUYEN_AM = frozenset("aeiouy")


def _co_nguyen_am(tu: str) -> bool:
    """Từ này có nguyên âm không.

    🔴 ĐÂY LÀ MỘT SỰ THẬT NGÔN NGỮ, KHÔNG PHẢI MỘT PHỎNG ĐOÁN, và đó là lý do
       nó được phép quyết định.

       Mọi âm tiết tiếng Việt đều có âm chính, và âm chính luôn là một nguyên
       âm. Nên một chữ **không có nguyên âm nào** thì không thể là một từ tiếng
       Việt — nó chỉ có thể là chữ viết tắt:

           HĐND · TNHH · THPT · ĐH · CĐ · QĐ · BĐS · VĐV

       Ngược lại không đúng: `CPU`, `RAM`, `ISO`, `ABC` có nguyên âm mà vẫn là
       viết tắt. Nên phép này chỉ dùng để **giữ lại**, không dùng để hạ xuống.
    """
    goc = unicodedata.normalize("NFD", tu.lower())
    return any(ch in _NGUYEN_AM for ch in goc)


def _co_dau_viet(tu: str) -> bool:
    """Từ này có mang dấu tiếng Việt không (kể cả dạng dựng sẵn như `Ư`, `Ạ`)."""
    return any(ch in _DAU_VIET_NFD for ch in unicodedata.normalize("NFD", tu))


def _ha_chuoi_viet_hoa(t: str) -> str:
    """VIẾT HOA TOÀN BỘ -> chữ thường, nhưng CHỈ khi chắc đó không phải viết tắt.

    🔴 NGUỒN: upstream `pnnbao97/VieNeu-TTS` **issue #119**. Tác giả trả lời
       nguyên văn:

           "hiện tại nếu viết hoa toàn bộ như CHƯƠNG thì hệ thống đang hiểu nhầm
            là từ viết tắt nên mới đọc từng chữ cái. Tạm thời bạn có thể chuyển
            về chữ thường trước khi dùng."

       Tức `"CHƯƠNG I"` được đọc thành *"xê hát u ơ en giê"*. Đây không phải ca
       hiếm: văn bản hành chính, pháp lý, hợp đồng tiếng Việt đầy chữ viết hoa —
       và đó đúng là thứ app này nhận. Khách dán một quyết định vào, nhận về một
       bản thu đánh vần, và **vẫn bị thu tiền** vì job `done` và `credit_cost`
       tính theo số giây thật sự sinh ra.

    ⛔ VÌ SAO KHÔNG HẠ TẤT CẢ VỀ CHỮ THƯỜNG.

       Đo thật: `"Xem mục CPU và RAM"` -> `"Xem mục xi pi diu và RAM"`. `CPU` có
       trong từ điển phát âm, `RAM` thì không. Hạ hết thành chữ thường thì `CPU`
       rơi khỏi từ điển, và `RAM` — vốn ĐANG được đánh vần **đúng** — thành chữ
       "ram". Sửa một lỗi bằng cách tạo ra lỗi ngược lại.

    ⭐ LUẬT, và vì sao nó an toàn:

       Trong một **chuỗi liên tiếp** các từ viết hoa, nếu có ít nhất một từ mang
       **dấu tiếng Việt** thì hạ cả chuỗi.

       Cơ sở: **từ viết tắt tiếng Việt không mang dấu.** Không có `TNHH`, `UBND`,
       `CPU`, `RAM`, `ISO` nào có dấu thanh. Nên một dấu trong chuỗi là bằng
       chứng đây là chữ VIẾT HOA, không phải viết tắt.

           "CHƯƠNG I. QUY ĐỊNH CHUNG"  -> hai chuỗi, mỗi chuỗi có một từ mang
                                          dấu (CHƯƠNG, ĐỊNH) -> hạ cả hai ✅
           "Xem mục CPU và RAM"        -> hai chuỗi một từ, không dấu -> giữ ✅

    ⚠️ PHẦN DƯ, ghi ra chứ không giấu: `"CÔNG TY TNHH ABC"` là **một** chuỗi, và
       `CÔNG` có dấu, nên `TNHH` bị hạ oan thành "tnhh". Luật này không che được
       ca đó. Cửa `/xem-truoc` (Xem trước cách đọc) tồn tại đúng để khách nhìn
       thấy và sửa — nhưng nó chỉ cứu người cẩn thận, không cứu người vội.

       Không mở rộng luật để bắt nốt ca đó: mọi cách mở rộng tôi thử đều phải
       đoán, và một phỏng đoán chạy ngầm ở tầng chuẩn hoá đúng là thứ sinh ra
       lớp lỗi này ngay từ đầu.
    """
    # ⛔ DUYỆT TỪNG TỪ, không dùng một regex bắt cả chuỗi.
    #
    #    Bản đầu dùng `[^\W\d_]{2,}(?:[\s.,:;/-]+[^\W\d_]{2,})*`, và nó THAM:
    #    với `"CÔNG TY TNHH ABC thông báo"` nó nuốt luôn "thông báo", rồi phép
    #    kiểm "cả chuỗi phải viết hoa" hỏng, nên **không làm gì cả**. Lỗi im
    #    lặng: hàm chạy, không ném, và trả về đúng thứ nó nhận.
    tu = [m for m in _TU_CHU.finditer(t) if len(m.group(0)) >= 2]
    if not tu:
        return t

    ra, i = [], 0
    while i < len(tu):
        if not tu[i].group(0).isupper():
            i += 1
            continue
        j = i
        while (j + 1 < len(tu) and tu[j + 1].group(0).isupper()
               and _NGAN_TRONG_CHUOI.match(t[tu[j].end():tu[j + 1].start()])):
            j += 1
        if any(_co_dau_viet(m.group(0)) for m in tu[i:j + 1]):
            # ⛔ Hạ TỪNG TỪ trong chuỗi, không hạ cả chuỗi một lượt: một chuỗi
            #    có thể trộn chữ viết hoa với viết tắt, và `HĐND TỈNH` là ca
            #    thật chứ không phải ca dựng ra. Chữ không có nguyên âm thì giữ
            #    nguyên — nó không thể là một từ tiếng Việt.
            ra.extend((m.start(), m.end()) for m in tu[i:j + 1]
                      if _co_nguyen_am(m.group(0)))
        i = j + 1

    if not ra:
        return t
    manh, truoc = [], 0
    for a, b in ra:
        manh.append(t[truoc:a])
        manh.append(t[a:b].lower())
        truoc = b
    manh.append(t[truoc:])
    return "".join(manh)


def _bo_ky_tu_vo_hinh(t: str) -> str:
    """Bỏ ký tự KHÔNG HIỂN THỊ. Phải chạy **trước mọi phép biến đổi khác**.

    🔴 NGUỒN: upstream `pnnbao97/VieNeu-TTS` **issue #177** (đã đóng). Người dùng
       báo *"xuất hiện các tiếng nước ngoài chèn giữa giọng đọc tiếng Việt"*.
       Tác giả trả lời, nguyên văn:

         *"khả năng cao lỗi này KHÔNG phải do model mà xuất phát từ ký tự Unicode
          ẩn hoặc định dạng văn bản đầu vào. Các văn bản dạng hành chính sao chép
          từ Word hoặc trang tin thường chứa các ký tự không hiển thị
          (zero-width characters). Khi đi qua bộ tokenizer, chúng tạo ra các
          token lạ (OOV), khiến mô hình sinh ra tiếng lạ trước khi đọc tiếp câu
          sau."*

       Người báo lỗi xác nhận đã sửa được bằng cách đổi hàm chia đoạn.

    ⛔ VÌ SAO NÓ LÀ LỖI **TIỀN**, không chỉ lỗi chất lượng: job vẫn `done`, và
       `credit_cost` tính theo **giây thật sự sinh ra** — nên khách trả tiền cho
       một bản thu có tiếng lạ chen vào, và **không lỗi nào báo**.

    ⭐ XOÁ THEO **CATEGORY**, không theo danh sách gõ tay. Mọi thủ phạm đều là
       `Cf` (format): ZWSP · ZWNJ · ZWJ · BOM · soft hyphen · word joiner · và
       cả directional mark `U+202A–202E` — thứ Word rải vào mà không ai thấy.
       Một danh sách gõ tay sẽ thiếu đúng cái chưa gặp bao giờ.
       `U+2028`/`U+2029` là `Zl`/`Zp` — chúng **là** ngắt dòng thật, nên đổi
       thành `\\n` chứ không xoá.

    ⛔ XOÁ, KHÔNG THAY BẰNG KHOẢNG TRẮNG. ZWSP và soft hyphen là **gợi ý chỗ
       ngắt dòng**, không phải dấu phân cách: `"Xin<ZWSP>chào"` nghĩa là
       `"Xinchào"` có thể xuống dòng ở giữa — không phải `"Xin chào"`. Thay bằng
       khoảng trắng là tự tạo ra một từ mới.

    ⚠️ ĐÁNH ĐỔI CÓ THẬT: xoá `U+200D` (ZWJ) sẽ **tách chuỗi emoji ghép** — một
       emoji gia đình thành bốn người rời rạc. Với một bộ đọc tiếng Việt thì vô
       hại (emoji không được đọc), nhưng nó là một cái giá, không phải một bước
       miễn phí. Ghi ra để phiên sau không tưởng là không mất gì.

    ⚠️ Nó làm **số ký tự giảm**, tức báo giá giảm. Đúng hướng: khách trả cho thứ
       được đọc, không trả cho thứ vô hình. `manifest._gia()` đã chuẩn hoá trước
       khi đếm nên nó tự khớp, không phải sửa gì thêm.

    ⭐ CHỖ ĐẶT QUAN TRỌNG HƠN BẢN THÂN PHÉP XOÁ. Nó phải chạy **trước**
       `tu_dien.ap_dung` và trước các regex số/ngày/giờ: một ZWSP nằm giữa một từ
       không chỉ làm model đọc lạ — nó còn **phá khớp từ điển** và phá `_NGAY` /
       `_GIO` / `_STT`. Cùng một ký tự ẩn gây ba loại lỗi, và hai loại sau im
       lặng hoàn toàn.

    🔴 CHẠY **TRƯỚC** `normalize("NFC")` — xem phép đo ở chính chỗ gọi. Cả hai
       thứ tự đều in ra `'á'`, nhưng chỉ một thứ tự cho **đúng một code point**.
    """
    if not t:
        return t
    ra = []
    for ch in t:
        loai = unicodedata.category(ch)
        if loai == "Cf":
            continue
        ra.append("\n" if loai in ("Zl", "Zp") else ch)
    return "".join(ra)


def chuan_hoa(text: str, *, doc_so_tran: bool = False,
              tu_dien_rieng: dict | None = None) -> str:
    """Một chuỗi vào, một chuỗi ra. Không trạng thái, test được từng phép."""
    # 🔴 XOÁ KÝ TỰ VÔ HÌNH **TRƯỚC** `NFC`, VÀ THỨ TỰ NÀY ĐÃ ĐƯỢC ĐO.
    #
    #    Ca khó: `'a'` + `U+200B` + dấu sắc tổ hợp `U+0301`.
    #      xoá SAU  NFC  ->  U+0061 U+0301   (rời)   — KHÔNG phải NFC
    #      xoá TRƯỚC NFC ->  U+00E1          (ghép)  — đúng NFC
    #    NFC không ghép được qua một ký tự chen giữa, nên xoá sau thì phép ghép
    #    đã lỡ mất chuyến. Hai chuỗi **nhìn giống hệt nhau** và in ra như nhau.
    #
    # ⛔ Và nó không phải chuyện thẩm mỹ: với tokenizer đó là **hai chuỗi khác
    #    nhau**, tức đúng loại token lạ (OOV) mà cả phép xoá này sinh ra để
    #    tránh. Sửa một nửa lỗi rồi để lại nửa kia ở dạng khó thấy hơn thì tệ
    #    hơn không sửa — vì lần sau sẽ không ai nghĩ tới nó nữa.
    t = _bo_ky_tu_vo_hinh(text or "")
    t = unicodedata.normalize("NFC", t)

    t = _URL.sub(" đường dẫn ", t)
    t = _EMAIL.sub(" địa chỉ email ", t)

    # Từ điển phát âm TRƯỚC khi đụng số: nó chứa tên riêng và cặp ch/tr, và một
    # số phép thay ở dưới có thể cắt mất ranh giới từ.
    t = tu_dien.ap_dung(t, them=tu_dien_rieng)

    # ⚠️ SAU từ điển, không phải trước. Từ điển bung `CPU` thành "xi pi diu"
    #    trước, nên tới đây không còn chữ hoa của viết tắt đã biết để hạ
    #    nhầm. Thứ tự ở đây là một phần của bản vá, không phải chi tiết.
    t = _ha_chuoi_viet_hoa(t)

    t = _STT.sub(lambda m: _doc_so_nho(int(m.group(1))).capitalize() + ". ", t)
    t = _NGAY.sub(_thay_ngay, t)
    t = _GIO.sub(_thay_gio, t)
    t = _NGAN.sub("", t)

    for mau, thay in _KY_HIEU:
        t = mau.sub(thay, t)

    if doc_so_tran:
        t = re.sub(r"\b\d+\b", lambda m: _doc_so(int(m.group(0))), t)

    t = _KHOANG.sub(" ", t)
    t = _XUONG_DONG.sub("\n\n", t)
    return t.strip()


# ── chia đoạn ────────────────────────────────────────────────────────────────
_CAU = re.compile(r"(?<=[.!?…])\s+|\n+")


def chia_doan(text: str, *, tran_moi_doan: int) -> list:
    """Chia theo RANH GIỚI NGỮ NGHĨA, không cắt giữa câu.

    ⛔ Đây không phải chia cho vừa bộ nhớ. Cắt giữa câu là cắt giữa một mệnh đề
       ngữ điệu, và model sẽ đọc nửa sau với ngữ điệu của một câu mới — nghe rõ
       ngay cả khi ghép lại liền mạch.

    Câu dài hơn cả trần thì mới cắt theo dấu phẩy, và cuối cùng mới cắt cứng —
    mỗi bậc là một sự nhượng bộ, và bậc sau chỉ chạy khi bậc trước không đủ.
    """
    tran = max(1, int(tran_moi_doan))
    ra: list = []
    dem = ""

    def day():
        nonlocal dem
        if dem.strip():
            ra.append(dem.strip())
        dem = ""

    for cau in (c for c in _CAU.split(text or "") if c and c.strip()):
        cau = cau.strip()
        if len(cau) > tran:
            day()
            ra.extend(_cat_cau_dai(cau, tran))
            continue
        if len(dem) + len(cau) + 1 > tran:
            day()
        dem = f"{dem} {cau}".strip()
    day()
    return ra


def _cat_cau_dai(cau: str, tran: int) -> list:
    ra, dem = [], ""
    for manh in re.split(r"(?<=[,;:])\s+", cau):
        if len(manh) > tran:
            if dem:
                ra.append(dem.strip())
                dem = ""
            for i in range(0, len(manh), tran):     # nhượng bộ cuối cùng
                ra.append(manh[i:i + tran].strip())
            continue
        if len(dem) + len(manh) + 1 > tran:
            ra.append(dem.strip())
            dem = ""
        dem = f"{dem} {manh}".strip()
    if dem.strip():
        ra.append(dem.strip())
    return [x for x in ra if x]


def chuan_bi(text: str, *, tran_moi_doan: int, doc_so_tran: bool = False,
             tu_dien_rieng: dict | None = None) -> KetQuaChuanHoa:
    """Đường đi đầy đủ. Trả cả text gốc lẫn text đã chuẩn hoá để ghi lịch sử."""
    da = chuan_hoa(text, doc_so_tran=doc_so_tran, tu_dien_rieng=tu_dien_rieng)
    return KetQuaChuanHoa(goc=text or "", da_chuan_hoa=da,
                          doan=chia_doan(da, tran_moi_doan=tran_moi_doan))

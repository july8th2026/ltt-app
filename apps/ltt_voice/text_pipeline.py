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


def _doc_so_nho(n: int, *, day_du: bool = False) -> str:
    """0-999 sang chữ. Đủ cho ngày/tháng/giờ; số lớn dùng `_doc_so`.

    `day_du` = nhóm này đứng SAU một nhóm bậc cao hơn, nên hàng trăm rỗng vẫn
    phải nói ra.

    ⛔ Thiếu nó là một lỗi MƠ HỒ, không phải một lỗi xấu xí — và mơ hồ thì tệ
       hơn nhiều:

           1.000.005  ->  "một triệu năm"    nghe y het "một triệu năm [trăm
                                             nghìn]", tuc 1.500.000
           1.000.001  ->  "một triệu một"

       Với một sản phẩm đọc bảng giá, hai câu trên là hai con số khác nhau gấp
       một trăm nghìn lần. Tìm ra 01/09/2026 khi đối chiếu với `num2words`.
    """
    if n == 0:
        return "không"
    ra = []
    tram, du = divmod(n, 100)
    if tram:
        ra += [_DON_VI[tram], "trăm"]
    elif day_du and du >= 10:
        # Dưới mười thì dùng "lẻ" (xử lý ngay bên dưới); từ mười trở lên thì
        # tiếng Việt nói "không trăm" — "một nghìn không trăm mười lăm".
        ra += ["không", "trăm"]
    chuc, dv = divmod(du, 10)
    if chuc == 0:
        if dv:
            if tram or day_du:
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
    cao_nhat = len(nhom) - 1
    for i in range(cao_nhat, -1, -1):
        if nhom[i] == 0:
            continue
        # `day_du` cho MỌI nhóm trừ nhóm cao nhất: chỉ nhóm cao nhất mới được
        # phép bỏ hàng trăm rỗng ("một triệu", không phải "không trăm một
        # triệu"). Xem docstring `_doc_so_nho` để biết vì sao chỗ này từng sai.
        phan.append(_doc_so_nho(nhom[i], day_du=i < cao_nhat) + _BAC[i])
    return " ".join(phan)


# ── số LỚN: bật theo số đo, không theo cờ ────────────────────────────────────
#
# Docstring đầu tệp viết: *"Đọc số trần mặc định TẮT. Không phải vì khó, mà vì
# **chưa đo**… Đo xong rồi mới bật, và bật bằng cách sửa mặc định ở đây chứ
# không rải cờ khắp nơi."*
#
# ⭐ 01/09/2026 đã đo (`tools/do_engine_doc_so_va_viet_tat.py`, sinh bằng engine
#    production rồi cho máy nghe lại). Câu "Giá … đồng":
#
#        99.000       -> "99 nghìn đồng"              DUNG
#        990.000      -> "990.000"                    DUNG
#        1.000.000    -> "1.0.0.0.0.0.0"              HONG — doc TUNG CHU SO
#        1.250.000    -> "1, 2, 5, 0, 0, 0, 0, 0"     HONG
#        2.000.000    -> "2-0-0-0-0-0-0-0"            HONG
#        12.500.000   -> "12.000.000.000"             HONG — sai ca gia tri
#
#    Ranh giới ở **một triệu**, tức đúng khoảng giá của mọi bảng giá tiếng Việt.
#    Dưới ngưỡng ấy `sea-g2p` đọc đúng ⇒ để yên. Đây chính là điều docstring
#    đòi: sửa một chỗ đã đo là hỏng, không sửa một chỗ chưa đo.
#
# 🔴 VÀ ĐÂY LÀ CÁI BẪY ĐẮT NHẤT — SỐ ĐIỆN THOẠI.
#
#        0912345678  ->  "chín trăm mười hai triệu ba trăm bốn mươi lăm nghìn
#                         sáu trăm bảy mươi tám"
#
#    Engine đang đọc số điện thoại **ĐÚNG** (từng chữ số — cùng lượt đo, bản
#    nhận dạng trả lại đủ mười chữ số đúng thứ tự). Nên một luật "≥ 7 chữ số thì
#    đổi" sẽ phá thứ đang chạy tốt. Hai điều kiện từ chối dưới đây không phải để
#    cho chặt — chúng là hai hình dạng ĐÃ ĐO là đang đúng.

#: Từ 7 chữ số (≥ 1 triệu) engine bắt đầu đọc rời từng chữ số.
_SO_LON_TU = 7
#: ⭐ DẤU PHÂN CÁCH LÀ TÍN HIỆU, và suýt nữa ta vứt nó đi trước khi dùng.
#:
#:    `1.250.000.000` (mười chữ số) là tiền; `19001234567` (mười một chữ số) là
#:    tổng đài. Thứ phân biệt chúng **không phải độ dài** mà là người viết đã
#:    nhóm ba chữ số hay chưa. Nhưng `_NGAN` gỡ dấu chấm ở dòng ngay trên, nên
#:    một luật đặt sau nó chỉ còn thấy hai dãy số trần giống hệt nhau.
#:
#:    ⇒ Luật này phải chạy **TRƯỚC** `_NGAN`. Đổi thứ tự hai dòng ấy là làm hỏng
#:      trở lại, và hỏng im lặng: số tiền tỷ quay về đọc rời từng chữ số.
_SO_CO_NHOM = re.compile(r"(?<![\d.,])(\d{1,3}(?:\.\d{3})+)(?![\d.,])")

#: Dãy TRẦN (không phân cách) — và ở đây phải dè dặt hơn hẳn.
#:
#: ⛔ "Mã đơn 1234567" mà đọc thành "một triệu hai trăm ba mươi tư nghìn năm
#:    trăm sáu mươi bảy" là sai, và sai theo kiểu tự tin. Không có cách nào phân
#:    biệt một mã đơn với một số tiền **chỉ bằng bản thân dãy số**.
#:
#: ⭐ Nên đòi thêm một BẰNG CHỨNG NGỮ CẢNH: dãy số phải đứng ngay trước một từ
#:    chỉ tiền hoặc đơn vị. `1250000 đồng` thì đọc; `1234567` trơ trọi thì không.
#:    Chính xác cao hơn, và ca bỏ sót chỉ quay về đúng hành vi hôm qua.
#: ⚠️ Dấu cách nằm TRONG lookahead, không nằm trong phần khớp. Bản đầu viết
#:    `(\d+)\s+(?=…)` — nó **nuốt** dấu cách, và nhánh "không đủ điều kiện đổi"
#:    trả về dãy số trần nên dấu cách biến mất: `990000 đồng` -> `990000đồng`.
#:    Một lỗi chỉ hiện ra ở ca KHÔNG đổi, tức ca mà ta tưởng là an toàn nhất.
_DAY_SO_TRAN = re.compile(
    r"(?<![\w.,])(\d+)(?=\s+(?:đồng|đô la|nghìn|triệu|tỷ|USD|VND)\b)",
    re.IGNORECASE)


def _doc_so_lon(text: str) -> str:
    """Đọc số LỚN thành chữ. Chạy TRƯỚC `_NGAN` — xem chú thích `_SO_CO_NHOM`."""
    def _co_nhom(m: re.Match) -> str:
        so = m.group(1).replace(".", "")
        # Đã nhóm ba chữ số ⇒ chắc chắn là một LƯỢNG, không phải định danh.
        # Nên không cần trần độ dài ở đây; chỉ cần ngưỡng "engine đọc hỏng".
        if len(so) < _SO_LON_TU:
            return so          # dưới ngưỡng: gỡ dấu chấm, để engine tự đọc
        return _doc_so(int(so)) or so

    def _tran(m: re.Match) -> str:
        s = m.group(1)
        # Số 0 đứng đầu: mọi đầu số di động Việt Nam. Không bao giờ là một lượng.
        #
        # ⚠️ KHÔNG còn trần độ dài ở đây, và việc gỡ nó là một BẢN SỬA chứ không
        #    phải nới lỏng. `_SO_LON_DEN = 9` sinh ra hồi luật này còn khớp MỌI
        #    dãy số trần — lúc ấy nó là thứ duy nhất loại được số điện thoại.
        #
        #    Nhưng luật nay đòi dãy số phải đứng ngay trước một TỪ CHỈ TIỀN, và
        #    điều kiện ấy loại số điện thoại chặt hơn nhiều. Trần độ dài thôi
        #    bảo vệ gì, và bắt đầu gây hại:
        #
        #        1.250.000.000 đồng  ->  "một tỷ hai trăm năm mươi triệu đồng"
        #        1250000000 đồng     ->  1250000000 đồng   (bi CHAN, roi engine
        #                                                   doc roi tung chu so)
        #
        #    Cùng một số tiền, hai cách viết, hai kết quả — chỉ vì một hằng số
        #    còn sót lại từ một thiết kế đã đổi.
        if s[0] == "0" or len(s) < _SO_LON_TU:
            return s
        return _doc_so(int(s)) or s

    t = _SO_CO_NHOM.sub(_co_nhom, text or "")
    return _DAY_SO_TRAN.sub(_tran, t)


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
    # 🔴 BA DÒNG NÀY PHỤ THUỘC THỨ TỰ, và cả ba lý do đều đã trả giá bằng một
    #    lần hỏng thật:
    #
    #    ① `_KY_HIEU` TRƯỚC — luật `đ` -> " đồng" dùng lookbehind `(?<=\d)`.
    #       Đặt nó sau `_doc_so_lon` thì chữ số đã thành chữ, lookbehind trượt,
    #       và `1.250.000đ` ra **"một triệu hai trăm năm mươi nghìnđ"** — một
    #       chữ `đ` mắc kẹt mà không luật nào còn nhặt được.
    #    ② `_doc_so_lon` GIỮA — nó cần dấu phân cách hàng nghìn CÒN NGUYÊN, vì
    #       đó là thứ duy nhất phân biệt tiền với số định danh.
    #    ③ `_NGAN` SAU CÙNG — dọn nốt dấu phân cách của những số không được đọc
    #       thành chữ (dưới một triệu), để engine tự đọc.
    for mau, thay in _KY_HIEU:
        t = mau.sub(thay, t)

    t = _doc_so_lon(t)
    t = _NGAN.sub("", t)

    if doc_so_tran:
        t = re.sub(r"\b\d+\b", lambda m: _doc_so(int(m.group(0))), t)

    t = _KHOANG.sub(" ", t)
    t = _XUONG_DONG.sub("\n\n", t)
    return t.strip()


# ── chia đoạn ────────────────────────────────────────────────────────────────
_CAU = re.compile(r"(?<=[.!?…])\s+|\n+")

#: Dấu kết câu. **Bản sao của `voice_sidecar.server._KET_CAU`**, và
#: `tests/test_338` chốt hai bên khớp nhau.
#:
#: 🔴 Vì sao phải có bản sao thay vì import: cùng lý do `tham_so_cong_khai.py`
#:    tồn tại — `apps/ltt_voice` chạy trong venv nền tảng, `voice_sidecar` chạy
#:    trong venv cách ly có torch. Một `import voice_sidecar.server` từ worker
#:    kéo cả cây phụ thuộc ấy vào đúng tiến trình mà venv cách ly sinh ra để
#:    tránh. Hai bản sao không có phép kiểm là hai bản sao sẽ lệch; hai bản sao
#:    **có** phép kiểm là một hợp đồng.
_KET_CAU = re.compile(r"[.!?…]+(?:\s|$)")


def dem_cau(text: str) -> int:
    """Số câu của một đoạn, tối thiểu 1.

    ⭐ Bộ ghép CẦN con số này: nó phân biệt ranh giới CÂU với hằng trăm khe TỪ
       khi đo nhịp nghỉ. `noi_dai.nhip_nghi` đã ghi lại cái giá của việc thiếu
       nó — trung vị mọi khoảng lặng cho 0,04 giây, tức khe giữa hai từ, và đặt
       0,04 s ở mối nối là nối gần như dính liền.

    ⚠️ Đường `/v1/speech-dai` đếm câu ở phía sidecar vì nó có sẵn văn bản. Đường
       đoạn-rời thì KHÔNG: `/v1/ghep-tep` chỉ nhận đường dẫn tệp, và một đoạn
       lấy lại từ kho sau khi máy chủ khởi động lại thì văn bản của nó chỉ còn ở
       phía worker. Nên phép đếm phải làm được ở đây.
    """
    return max(1, len(_KET_CAU.findall(text or "")) or 1)


def chia_doan(text: str, *, tran_moi_doan: int, can_bang: bool = False) -> list:
    """Chia theo RANH GIỚI NGỮ NGHĨA, không cắt giữa câu.

    ⛔ Đây không phải chia cho vừa bộ nhớ. Cắt giữa câu là cắt giữa một mệnh đề
       ngữ điệu, và model sẽ đọc nửa sau với ngữ điệu của một câu mới — nghe rõ
       ngay cả khi ghép lại liền mạch.

    Câu dài hơn cả trần thì mới cắt theo dấu phẩy, và cuối cùng mới cắt cứng —
    mỗi bậc là một sự nhượng bộ, và bậc sau chỉ chạy khi bậc trước không đủ.

    `can_bang=True` thì thêm một bước nữa — xem `_can_bang` ngay dưới. Mặc định
    TẮT, vì hai người gọi muốn hai thứ khác nhau và `du_an.py` đã ghi rõ điều đó:
    khối biên tập muốn **gói tới trần**, bản đọc muốn **các đoạn đều nhau**.
    """
    if can_bang:
        return _can_bang(text, max(1, int(tran_moi_doan)))
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


def _can_bang(text: str, tran: int) -> list:
    """Cùng số đoạn, nhưng các đoạn ĐỀU NHAU.

    🔴 VÌ SAO CẦN, VÀ ĐÂY LÀ MỘT SỐ ĐO CHỨ KHÔNG PHẢI MỘT LINH CẢM.

       Phép gói tới trần nhồi đầy đoạn trước rồi để phần thừa rơi vào đoạn cuối.
       Đo 03/09 trên corpus của `tools/do_bai_dai.py`, trần 1.500:

           bai 1.500 ky tu  ->  2 doan:  1462 + 128     (lech 11,4 lan)
           bai 3.000 ky tu  ->  3 doan:  1463 + ... + 133
           bai 5.000 ky tu  ->  4 doan:  1463 + ... + 698

       Đoạn đuôi 128 ký tự **vẫn là một lượt `infer` đầy đủ**: vẫn một lần vào
       GPU, vẫn một lần khởi động. `docs/LTT_VOICE/AUTONOMOUS_RUN/` đã đo RTF
       theo độ dài và nó tệ đi rõ rệt ở các câu ngắn (`cau_dai` 353 ký tự cho
       RTF 1,009 — tốt nhất bảng). Nên một đuôi cụt vừa **chậm hơn** vừa là một
       mối nối thừa, đổi lấy đúng con số không.

    ⭐ CÁCH LÀM: KHÔNG viết một bộ chia thứ hai.

       Một bộ chia thứ hai là hai cách hiểu "ranh giới câu là gì", và chúng sẽ
       lệch nhau — đúng cái bẫy `du_an.nhap_van_ban` đã cảnh báo. Thay vào đó
       gọi lại CHÍNH `chia_doan` với một trần NHỎ HƠN, và tìm trần nhỏ nhất còn
       cho ra đúng ngần ấy đoạn. Mọi luật cắt vẫn là một bộ luật duy nhất.

           gói ở trần 1.500  ->  2 đoạn        (k = 2)
           tìm trần nhỏ nhất còn ra <= 2 đoạn  ->  ~800
           gói ở trần ~800   ->  2 đoạn ~795   ✅

    ⚠️ Số đoạn KHÔNG BAO GIỜ tăng, và không đoạn nào vượt `tran`. Cả hai được
       kiểm lại ở cuối rồi mới trả — phép nhị phân dựa trên giả định "trần lớn
       hơn thì đoạn ít hơn", đúng trong mọi ca thật nhưng không phải một định
       lý. Sai giả định thì lui về bản gói tới trần, không trả một bản tệ hơn.

    ⛔ NÓI CHO ĐÚNG NÓ LÀM ĐƯỢC GÌ: phép này **cực tiểu hoá đoạn DÀI NHẤT**, và
       chỉ nhờ thế mà các đoạn đều ra. Khi bài gần lấp đầy `k × tran` thì không
       còn chỗ để đều: phần dư phải rơi vào một đoạn nào đó. Đo cùng lượt 03/09:

           bai  1.500 ky tu:  lech 1.334 -> 104   (con 7,8%)
           bai  3.000 ky tu:  lech 1.330 ->  26
           bai  5.000 ky tu:  lech   765 -> 130
           bai 50.000 ky tu:  lech   740 -> 740   (khong doi — da gan lap day)

       Tức nó xoá ca BỆNH LÝ (đuôi 128 ký tự cạnh một đoạn 1.462 — lệch 11,4
       lần) chứ không hứa mọi đoạn bằng nhau. Phần dư còn lại bị chặn trên bởi
       đúng MỘT đoạn, và một đoạn 724 ký tự thì không nằm trong vùng RTF xấu.
    """
    co_ban = chia_doan(text, tran_moi_doan=tran)
    k = len(co_ban)
    if k <= 1:
        return co_ban

    lo, hi = 1, tran
    while lo < hi:
        giua = (lo + hi) // 2
        if len(chia_doan(text, tran_moi_doan=giua)) <= k:
            hi = giua
        else:
            lo = giua + 1

    thu = chia_doan(text, tran_moi_doan=lo)
    if len(thu) <= k and thu and max(len(x) for x in thu) <= tran:
        return thu
    return co_ban


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
    # ⭐ `can_bang=True` CHỈ ở đường bản đọc. `du_an.nhap_van_ban` gọi thẳng
    #    `chia_doan` và giữ phép gói tới trần — hai người gọi, hai nhu cầu.
    return KetQuaChuanHoa(goc=text or "", da_chuan_hoa=da,
                          doan=chia_doan(da, tran_moi_doan=tran_moi_doan,
                                         can_bang=True))

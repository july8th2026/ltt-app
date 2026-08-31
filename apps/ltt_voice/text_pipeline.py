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
_NGAN = re.compile(r"(?<=\d)\.(?=\d{3}\b)")

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

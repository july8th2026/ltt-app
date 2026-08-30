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


def chuan_hoa(text: str, *, doc_so_tran: bool = False,
              tu_dien_rieng: dict | None = None) -> str:
    """Một chuỗi vào, một chuỗi ra. Không trạng thái, test được từng phép."""
    t = unicodedata.normalize("NFC", text or "")

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

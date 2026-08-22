"""
prompt_dich.py — dịch prompt sang tiếng Anh TRƯỚC khi gửi cho model sinh ảnh.

⭐ VÌ SAO CÓ TỆP NÀY — SỐ ĐO, KHÔNG PHẢI PHỎNG ĐOÁN (D-027, 22/08/2026):

   HiDream-O1 chạy trên máy B **gần như không hiểu prompt tiếng Việt**. Cùng model,
   **cùng seed**, cùng số bước — chỉ khác ngôn ngữ của prompt:

   | seed | prompt tiếng Việt | prompt tiếng Anh |
   |---|---|---|
   | 105 | *"con mèo tam thể ngủ trên bậu cửa sổ"* → **người phụ nữ trên giường** | **đúng con mèo tam thể ngủ cuộn tròn** |
   | 109 | *"bốn người bạn quanh bàn cà phê"* → **một** người | **đúng bốn người, thấy rõ cả bốn mặt** |
   | 110 | *"tám người xếp hai hàng cầm cúp"* → **một** người | **đúng cả đội hai hàng, cầm cúp** |
   | 112 | *"táo đỏ TRONG bát TRÊN tờ báo"* → người cầm hộp quà | **đúng cả hai quan hệ vị trí** |

   Ba trên ba, rồi bốn trên bốn. Bộ mã hoá văn bản của model bắt được "hơi hướng
   Việt Nam" từ ký tự có dấu rồi **vứt bỏ phần ngữ nghĩa**. Model **không yếu** —
   đường vào yếu.

⛔ HAI ĐIỀU TỆP NÀY LÀM KHÁC HẲN `apps/taovideo/translate.py`:

   ① **GIỮ NGUYÊN chuỗi trong ngoặc kép.** Với prompt ảnh, `"CƠM TẤM SƯỜN BÌ"`
      không phải câu cần dịch — nó là **chữ sẽ được vẽ vào ảnh**. Dịch nó đi là
      biển hiệu ra tiếng Anh, tức là giao sai hàng. Bản video không có ràng buộc
      này nên không xử lý.
   ② **CẢNH BÁO khi chuỗi cần vẽ có dấu tiếng Việt.** Đo thật: biển hiệu ra
      `CỜM TẤM` / `CỜM TÀM`, poster ra `KUIG MÂN`, `HỐM NAY`, bìa sách ra
      `NHỮNG NHUGẨN THỜ ẤU`. Cùng biển hiệu đó **viết không dấu** (`COM TAM SUON
      BI`) thì ra **đúng từng chữ**. Ranh giới nằm chính xác ở **dấu**, không ở
      tiếng Việt nói chung. Dịch prompt **không cứu được** điều này — chữ cần vẽ
      vẫn phải là chữ khách yêu cầu.

⛔ DỊCH HỎNG THÌ HỎNG JOB, KHÔNG GỬI BẢN TIẾNG VIỆT. Gửi nguyên bản tiếng Việt
   không phải "phương án dự phòng" — nó là **giao một tấm ảnh sai mà khách vẫn trả
   tiền**. Đúng tinh thần D-010 (chất lượng là tiêu chí duy nhất) và nguyên tắc
   không đánh tráo sản phẩm sau lưng khách.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Callable, Optional

from platform_core.i18n import _ as _t

log = logging.getLogger(__name__)

#: Ngôn ngữ mà model ảnh hiểu. Không phải lựa chọn thẩm mỹ — là số đo (D-027).
NGON_NGU_MODEL = "English"

#: ⭐ HAI thứ tiếng model THẬT SỰ hiểu, theo benchmark của chính nó:
#: `LongText-Bench-EN` (0,979) và `LongText-Bench-ZH` (0,978). **Không có thứ ba.**
#: Mọi ngôn ngữ khác phải dịch — kể cả thứ tiếng ta chưa từng thấy khách dùng.
MODEL_HIEU = ("en", "zh")

#: Ký tự chỉ có trong tiếng Việt (không có trong ASCII lẫn tiếng Anh). Dùng để
#: đoán "có cần dịch không" mà không phải gọi LLM.
_DAU_VIET = "ăâđêôơưĂÂĐÊÔƠƯáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"

#: Chuỗi trong ngoặc kép = chữ cần VẼ VÀO ẢNH. Bắt cả " ” “ ' và « ».
_NGOAC = re.compile(r'["“”«»\']([^"“”«»\']{1,120})["“”«»\']')

#: Thẻ giữ chỗ đặt vào chỗ chuỗi đã tách. Chọn dạng LLM không có lý do gì đụng vào.
_THE = "@@LTT_TEXT_{}@@"


class DichThatBai(Exception):
    """Không dịch được. Bên gọi phải HỎNG JOB, đừng gửi bản gốc."""


def _loi_nguoi_doc(ky_thuat: str) -> str:
    """Thông điệp cho NGƯỜI DÙNG, không phải cho log.

    ⛔ Một lời từ chối không kèm lối ra sẽ biến thành ngõ cụt: khách bấm lại, hỏng
    lại, rồi bỏ đi. Model chỉ hiểu tiếng Anh và tiếng Trung, nên khách **tự viết
    tiếng Anh là đi được ngay** — phải nói ra điều đó.
    """
    return _t("Không dịch được prompt sang tiếng Anh ({ly_do}). Model tạo ảnh nội bộ "
              "chỉ hiểu tiếng Anh và tiếng Trung. Bạn có thể thử lại, hoặc tự viết "
              "prompt bằng tiếng Anh để đi thẳng không cần dịch.").format(ly_do=ky_thuat)


@dataclass(frozen=True)
class KetQua:
    prompt_goc: str
    prompt_model: str
    da_dich: bool
    #: Các chuỗi được giữ nguyên vì chúng là chữ sẽ vẽ vào ảnh.
    chuoi_giu_nguyen: tuple = ()
    #: Cảnh báo hiện cho người dùng — KHÔNG chặn job, chỉ nói trước.
    canh_bao: tuple = ()

    def as_dict(self) -> dict:
        return {"prompt_model": self.prompt_model, "da_dich": self.da_dich,
                "chuoi_giu_nguyen": list(self.chuoi_giu_nguyen),
                "canh_bao": list(self.canh_bao)}


def co_dau_tieng_viet(s: str) -> bool:
    """Chuỗi có ký tự riêng của tiếng Việt không.

    ⛔ Dùng `unicodedata.normalize("NFC")` trước khi so: cùng một chữ "ế" có thể
    được gõ ở dạng tổ hợp (e + ˆ + ´) và khi đó phép so ký tự thô sẽ trượt.
    """
    return any(c in _DAU_VIET for c in unicodedata.normalize("NFC", s or ""))


def _la_han(c: str) -> bool:
    """Chữ Hán (CJK Unified Ideographs + phần mở rộng A + tương thích)."""
    n = ord(c)
    return (0x4E00 <= n <= 0x9FFF or 0x3400 <= n <= 0x4DBF or 0xF900 <= n <= 0xFAFF)


def nhan_dien_ngon_ngu(prompt: str) -> str:
    """Trả `"en"` · `"zh"` · `"khac"`. Chỉ để quyết định CÓ DỊCH HAY KHÔNG.

    ⛔ VÌ SAO KHÔNG CHỈ DÒ TIẾNG VIỆT: bản đầu chỉ bắt dấu tiếng Việt, nên một
    prompt tiếng Nhật, Thái, Hàn hay Nga sẽ **đi thẳng vào model và hỏng y hệt
    cách tiếng Việt đã hỏng** — mà không ai biết, vì không có lỗi nào báo. Model
    chỉ hiểu EN và ZH; mọi thứ khác phải dịch.

    Luật, theo đúng thứ tự:
      ① toàn ký tự Latin cơ bản  → `en`  (không dịch)
      ② có chữ Hán và KHÔNG có bảng chữ nào khác → `zh`  (không dịch)
      ③ còn lại → `khac`  (dịch)

    ⚠️ Tiếng Nhật viết gần như toàn Hán tự sẽ bị đoán nhầm là `zh`. Chấp nhận:
    kana xuất hiện là ③ bắt được ngay, và ca thuần Hán tự cực hiếm.
    """
    con_lai = _NGOAC.sub(" ", prompt or "")     # bỏ chữ-cần-vẽ ra khỏi phép đoán
    chu = [c for c in unicodedata.normalize("NFC", con_lai) if c.isalpha()]
    if not chu:
        return "en"                              # không có chữ nào ⇒ không cần dịch
    if all(ord(c) < 0x0250 for c in chu):        # Latin cơ bản + mở rộng A/B
        # ⛔ Tiếng Việt NẰM TRONG dải này (ế, ườ…), nên phải hỏi riêng.
        return "khac" if any(c in _DAU_VIET for c in chu) else "en"
    if any(_la_han(c) for c in chu) and all(_la_han(c) or ord(c) < 0x0250 for c in chu):
        return "zh"
    return "khac"


def can_dich(prompt: str) -> bool:
    """Có cần gọi LLM không. EN và ZH thì bỏ qua — đỡ một lượt gọi, đỡ một khoản
    credit, và đỡ một chỗ hỏng được."""
    return nhan_dien_ngon_ngu(prompt) not in MODEL_HIEU


def tach_chuoi_can_ve(prompt: str) -> tuple:
    """Thay chuỗi trong ngoặc kép bằng thẻ giữ chỗ.

    Trả `(prompt_co_the, danh_sach_chuoi)`. Chính chỗ này giữ cho biển hiệu
    `"CƠM TẤM SƯỜN BÌ"` không bị dịch thành `"BROKEN RICE WITH PORK"`.
    """
    chuoi = []

    def _thay(m):
        chuoi.append(m.group(1))
        return f'"{_THE.format(len(chuoi) - 1)}"'

    return _NGOAC.sub(_thay, prompt or ""), tuple(chuoi)


def ghep_chuoi_can_ve(prompt: str, chuoi) -> str:
    """Đặt lại các chuỗi vào chỗ thẻ giữ chỗ.

    ⛔ Thẻ nào KHÔNG còn trong bản dịch thì chuỗi đó **mất** — LLM đã nuốt nó.
    Ta không im lặng bỏ qua: nối lại vào cuối còn hơn giao một ảnh thiếu chữ mà
    không ai biết.
    """
    ra = prompt
    thieu = []
    for i, s in enumerate(chuoi):
        the = _THE.format(i)
        if the in ra:
            ra = ra.replace(the, s)
        else:
            thieu.append(s)
    if thieu:
        log.warning("ban dich lam mat %d chuoi can ve — noi lai vao cuoi", len(thieu))
        ra = ra.rstrip() + ", text: " + ", ".join(f'"{s}"' for s in thieu)
    return ra


def _canh_bao_chu_co_dau(chuoi) -> tuple:
    """Cảnh báo cho chuỗi cần vẽ có dấu tiếng Việt — model không dựng đúng dấu."""
    xau = [s for s in chuoi if co_dau_tieng_viet(s)]
    if not xau:
        return ()
    return (
        _t("Chữ cần vẽ vào ảnh có dấu tiếng Việt ({danh_sach}). Model dựng chữ "
           "Latin không dấu rất chính xác nhưng SAI DẤU tiếng Việt (đo thật: "
           "'CƠM TẤM' ra 'CỜM TÀM'). Cân nhắc bỏ dấu, hoặc để phần chữ ghép sau "
           "bằng phông chữ thật.").format(
               danh_sach=", ".join(f'"{s}"' for s in xau[:3])),
    )


def dich_prompt_anh(prompt: str, *, goi_llm: Optional[Callable] = None,
                    giu_nguoi_viet: bool = True) -> KetQua:
    """Chuẩn bị prompt cho model ảnh: dịch phần mô tả, giữ nguyên phần chữ-cần-vẽ.

    `goi_llm(text) -> str` được tiêm vào để test không cần mạng. Bên gọi thật
    truyền hàm gọi Gemini (category `chat`) qua `api_pool`.
    """
    goc = (prompt or "").strip()
    if not goc:
        raise DichThatBai("prompt rong")

    co_the, chuoi = tach_chuoi_can_ve(goc)
    canh_bao = _canh_bao_chu_co_dau(chuoi)

    if not can_dich(goc):
        # Đã là tiếng Anh (hoặc chỉ còn chữ-cần-vẽ là tiếng Việt) — không gọi LLM.
        return KetQua(goc, goc, False, chuoi, canh_bao)

    if goi_llm is None:
        raise DichThatBai("can dich nhung khong co duong goi LLM")

    try:
        ban_dich = (goi_llm(co_the, loi_nhac(giu_nguoi_viet=giu_nguoi_viet)) or "").strip()
    except Exception as e:                                        # noqa: BLE001
        raise DichThatBai(_loi_nguoi_doc(f"{type(e).__name__}: {e}")) from e

    if not ban_dich:
        raise DichThatBai(_loi_nguoi_doc("LLM tra ve rong"))
    if nhan_dien_ngon_ngu(ban_dich) not in MODEL_HIEU:
        # Dịch mà phần mô tả vẫn không phải EN/ZH nghĩa là nó chưa dịch. Gửi đi là
        # rơi đúng vào lỗi mà tệp này sinh ra để tránh.
        raise DichThatBai(_loi_nguoi_doc("ban dich khong phai tieng Anh"))

    return KetQua(goc, ghep_chuoi_can_ve(ban_dich, chuoi), True, chuoi, canh_bao)


def loi_nhac(*, giu_nguoi_viet: bool = True) -> str:
    """Lời nhắc hệ thống gửi LLM.

    ⭐ `giu_nguoi_viet` sinh ra từ một SỐ ĐO, không từ ý thích: bản tiếng Anh của
    *"đội bóng chuyền nữ"* cho ra **cầu thủ da trắng**, *"đầu bếp"* cho ra đầu bếp
    Âu — vì prompt gốc không nói sắc tộc và tiếng Anh không mang theo ngữ cảnh ấy.
    Nhưng khi chủ thể **tự nó bản địa** (ruộng bậc thang, người gánh lúa, phở, cơm
    tấm) thì bản dịch giữ rất tốt.

    ⇒ Khi prompt gốc là tiếng Việt mà **không nói sắc tộc**, thêm gợi ý *Vietnamese*
    cho chủ thể người. Tắt được, vì có khách cố ý muốn người nước ngoài.
    """
    ra = LOI_NHAC_NEN
    if giu_nguoi_viet:
        ra += (" If the source prompt is Vietnamese and mentions people without "
               "stating their ethnicity, describe them as Vietnamese - the original "
               "language carries that context and a bare translation loses it.")
    return ra


#: Phần nền của lời nhắc. Tách ra để test đọc được và để đổi một chỗ.
LOI_NHAC_NEN = (
    f"Translate the following image-generation prompt to {NGON_NGU_MODEL}. "
    "Return ONLY the translation - no quotes around the whole answer, no notes. "
    "Keep every @@LTT_TEXT_n@@ placeholder EXACTLY as it appears, including the "
    "surrounding quotation marks - they mark literal text that must be rendered "
    "inside the image and must not be translated. "
    "Keep camera, lighting and composition terms precise. "
    "Keep culturally specific subjects as they are (pho, com tam, ao dai, "
    "terraced rice fields) rather than replacing them with generic equivalents."
)

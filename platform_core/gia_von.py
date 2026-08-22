"""
gia_von.py — **giá vốn** của từng model, một chỗ duy nhất. (MVP đợt 0.1)

    from platform_core import gia_von
    gia_von.mot_anh("gemini-3-pro-image")        # -> 35242 mcredit
    gia_von.theo_token("gemini-2.5-flash", vao=2000, ra=500)

⛔ **GIÁ VỐN KHÔNG PHẢI GIÁ BÁN.** Giá vốn là thứ **ta trả** cho nhà cung cấp; giá
   bán nằm ở `credit_cost` của từng app. Hai số đó khác nhau và **phải** khác nhau —
   `tests/test_261_gia_ban_khong_duoi_gia_von.py` chốt chiều của hiệu số.

⭐ VÌ SAO TỆP NÀY TỒN TẠI. Đo 23/08/2026: nền tảng đang bán ảnh ở **45–57 % giá
   vốn**, cả bốn bậc model. Không ai chọn như vậy cả — `CREDIT_PER_IMAGE = 5` chỉ
   là một hằng số **không có cơ sở chi phí nào**, và nó chạy 22 ngày mà không ai
   thấy vì **không có gì để so với**. Tệp này là thứ để so.

📖 KHUÔN LẤY TỪ LiteLLM `model_prices_and_context_window.json` (MIT), bốn ý:

   ① **Tên trường.** `output_cost_per_image`, `input_cost_per_token`,
      `cache_read_input_token_cost`, `mode` — giữ nguyên tên của họ để ngày nào
      muốn nạp thẳng bảng của họ thì không phải viết lớp dịch tên.
   ② **Bản đồ giá cục bộ.** LiteLLM có `LITELLM_LOCAL_MODEL_COST_MAP=True` để chạy
      hoàn toàn ngoại tuyến từ một tệp đóng gói sẵn. Ta **chỉ có** chế độ đó: một
      tệp JSON trong repo, không gọi mạng lúc chạy. Giá là thứ phải xem lại bằng
      mắt, không phải thứ tự cập nhật sau lưng.
   ③ **Phép kiểm số mục tối thiểu.** LiteLLM từ chối bản đồ dưới 50 mục — chống một
      tệp rỗng/hỏng lặng lẽ làm mọi giá về 0.
   ④ **Mặc định fail-expensive.** LiteLLM gán $1 cho model lạ. Ta đi xa hơn: **ném
      lỗi**. Xem `KhongBietGiaVon` để biết vì sao.

🔧 KHÁC LiteLLM ba chỗ, mỗi chỗ một lý do:

   · **milli-credit số nguyên**, không phải USD float — quy tắc `llm/gia_token.py`;
   · **`nguon` + `ngay_tra` bắt buộc** mỗi mục — giá thị trường **hết hạn**, và một
     con số không có ngày là một con số không kiểm lại được;
   · **`chi_phi_may_nha`** cho model chạy trên máy ta — LiteLLM không mô hình hoá
     điện và khấu hao GPU vì nó không có khái niệm "model của chính bạn".
"""
from __future__ import annotations

import datetime as _dt
import json
import pathlib
from typing import Optional

TEP = pathlib.Path(__file__).with_name("gia_von.json")

#: Milli-credit trong một credit. Cùng đơn vị `llm/gia_token.py` đã chốt.
MCREDIT_MOI_CREDIT = 1_000

#: Bản đồ giá phải có ít nhất bằng này mục. 📖 Ý của LiteLLM: một tệp rỗng hoặc
#: hỏng mà vẫn nạp được sẽ làm **mọi** giá vốn về 0, và mọi phép so biên lợi nhuận
#: sẽ báo "lãi rất tốt". Con số ở đây thấp hơn số mục thật để không phải sửa mỗi
#: lần thêm model, nhưng đủ cao để bắt một tệp rỗng.
SO_MUC_TOI_THIEU = 6

#: Giá tra được bao lâu thì coi là cũ. Không phải hạn dùng — là mốc nhắc rà lại.
HAN_RA_LAI_NGAY = 180

_cache: Optional[dict] = None


class GiaVonError(Exception):
    """Bảng giá vốn hỏng — không nạp được, thiếu trường, sai kiểu."""


class KhongBietGiaVon(GiaVonError):
    """Không có giá vốn cho model này.

    ⛔ **Ném lỗi chứ không trả 0.** Giá vốn 0 nghĩa là *"phục vụ model này không tốn
    gì"* — đó là một **khẳng định**, và module này không có quyền khẳng định điều
    đó. Một số 0 lọt vào phép tính biên lợi nhuận sẽ biến một khoản lỗ thành một
    khoản lãi trông rất đẹp, và không ai đi tìm nữa.

    Bên gọi có hai lựa chọn hợp lệ: **từ chối phục vụ**, hoặc **tra giá rồi khai vào
    `gia_von.json`**. Không có lựa chọn thứ ba.
    """


def _nap() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    try:
        d = json.loads(TEP.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise GiaVonError(f"khong nap duoc {TEP.name}: {e}") from e

    model = d.get("model")
    if not isinstance(model, dict):
        raise GiaVonError("thieu khoi 'model'")
    tong = len(model) + len(d.get("chua_tra") or {}) + len(d.get("khai_o_noi_khac") or {})
    if tong < SO_MUC_TOI_THIEU:
        raise GiaVonError(
            f"bang gia von chi co {tong} muc (< {SO_MUC_TOI_THIEU}) — nghi tep rong/hong")
    for ten, m in model.items():
        for truong in ("nguon", "ngay_tra", "mode"):
            if not m.get(truong):
                raise GiaVonError(f"{ten}: thieu '{truong}'")
        for k, v in m.items():
            if k.endswith("_mcredit") and not isinstance(v, int):
                raise GiaVonError(f"{ten}.{k} phai la so nguyen (mcredit), gap {type(v).__name__}")
    _cache = d
    return d


def bang() -> dict:
    """Toàn bộ bảng, đã kiểm. Dùng cho test và cho trang admin."""
    return _nap()


def phien_ban() -> str:
    return str(_nap().get("phien_ban") or "")


def _muc(model_id: str) -> dict:
    d = _nap()
    ten = str(model_id or "").strip()
    m = (d.get("model") or {}).get(ten)
    if m:
        return m
    if ten in (d.get("khai_o_noi_khac") or {}):
        o = d["khai_o_noi_khac"][ten].get("o_dau", "?")
        raise KhongBietGiaVon(
            f"'{ten}' khong khai o day — gia von cua no o {o}. "
            "Hoi dung cho, dung tao mot bang gia thu hai.")
    if ten in (d.get("chua_tra") or {}):
        ly_do = d["chua_tra"][ten].get("ly_do", "")
        raise KhongBietGiaVon(f"'{ten}' CHUA TRA gia von. {ly_do}")
    raise KhongBietGiaVon(
        f"'{ten}' khong co trong bang gia von. Tra gia roi khai vao "
        f"{TEP.name}, hoac khai vao 'chua_tra' kem ly do.")


def co_gia(model_id: str) -> bool:
    """True nếu tra được giá vốn. Dùng để hỏi trước, không dùng thay `try`."""
    return str(model_id or "").strip() in (_nap().get("model") or {})


def chua_tra() -> dict:
    """Model đã biết là có, nhưng chưa ai tra giá — **miễn trừ CÓ HẠN**.

    Mỗi mục bắt buộc `ly_do` + `chu` + `han_ra_lai`. Miễn trừ không hết hạn chính
    là cách `CREDIT_PER_IMAGE = 5` sống được 22 ngày: nó không sai lúc đặt, nó chỉ
    không bao giờ được nhìn lại.
    """
    return dict(_nap().get("chua_tra") or {})


def mien_tru_qua_han(hom_nay: Optional[_dt.date] = None) -> list:
    """Miễn trừ đã quá `han_ra_lai`. Quá hạn ⇒ test đỏ ⇒ có người phải xử lý."""
    hom_nay = hom_nay or _dt.date.today()
    ra = []
    for ten, m in chua_tra().items():
        try:
            han = _dt.date.fromisoformat(str(m.get("han_ra_lai")))
        except ValueError:
            ra.append((ten, "han_ra_lai khong doc duoc"))
            continue
        if han < hom_nay:
            ra.append((ten, f"qua han {(hom_nay - han).days} ngay (chu: {m.get('chu', '?')})"))
    return ra


def khai_o_noi_khac() -> dict:
    return dict(_nap().get("khai_o_noi_khac") or {})


def mot_anh(model_id: str, *, tham_chieu: bool = False) -> int:
    """Giá vốn **một ảnh**, milli-credit.

    `tham_chieu=True` cho chế độ dùng ảnh tham chiếu — đắt hơn thật, không phải
    ước: đo trên máy B là **gấp ~3,3 lần thời gian**, nên với model nhà nó là một
    con số riêng chứ không phải cùng một con số.
    """
    m = _muc(model_id)
    if m.get("mode") != "image_generation":
        raise KhongBietGiaVon(f"'{model_id}' khong phai model sinh anh (mode={m.get('mode')})")
    if tham_chieu and "chi_phi_tham_chieu_mcredit" in m:
        return int(m["chi_phi_tham_chieu_mcredit"])
    gia = m.get("output_cost_per_image_mcredit")
    if gia is None:
        raise KhongBietGiaVon(f"'{model_id}' thieu output_cost_per_image_mcredit")
    return int(gia)


def theo_token(model_id: str, *, vao: int = 0, ra: int = 0, cache: int = 0) -> int:
    """Giá vốn một lượt gọi tính theo token, milli-credit.

    Chia **cuối cùng** rồi mới cộng, và chia số nguyên: cộng ba phân số rồi mới làm
    tròn sẽ ra một số khác, và khác ở đâu thì không truy được.
    """
    m = _muc(model_id)
    tong = 0
    for so, khoa in ((vao, "input_cost_per_1m_token_mcredit"),
                     (ra, "output_cost_per_1m_token_mcredit"),
                     (cache, "cache_read_input_1m_token_mcredit")):
        if not so:
            continue
        don_gia = m.get(khoa)
        if don_gia is None:
            raise KhongBietGiaVon(f"'{model_id}' thieu {khoa}")
        tong += int(so) * int(don_gia) // 1_000_000
    return tong


def muc_qua_han(hom_nay: Optional[_dt.date] = None) -> list:
    """Mục có `ngay_tra` cũ hơn `HAN_RA_LAI_NGAY`. Không phải lỗi — là việc phải làm.

    Giá thị trường đổi. Một bảng giá vốn không ai rà lại sẽ **âm thầm sai** đúng
    theo cách mà `CREDIT_PER_IMAGE = 5` đã sai.
    """
    hom_nay = hom_nay or _dt.date.today()
    ra = []
    for ten, m in (_nap().get("model") or {}).items():
        try:
            ngay = _dt.date.fromisoformat(str(m.get("ngay_tra")))
        except ValueError:
            ra.append((ten, "ngay_tra khong doc duoc"))
            continue
        so_ngay = (hom_nay - ngay).days
        if so_ngay > HAN_RA_LAI_NGAY:
            ra.append((ten, f"tra cach day {so_ngay} ngay"))
    return ra

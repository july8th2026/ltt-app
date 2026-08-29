"""
features.py — quy tắc nghiệp vụ của `ltt_llm`, dùng chung cho CẢ HAI cánh cửa. (H38)

    cua bat dong bo :  POST /api/v1/jobs  -> worker -> jobs.py::handle -> đây
    cua dong bo     :  POST /api/v1/chat/completions             -> đây

⭐ VÌ SAO GOM VÀO ĐÂY thay vì viết hai lần: nếu hai cửa tự xử lý riêng thì ngày
   chúng lệch nhau là ngày **cùng một yêu cầu bị tính hai giá khác nhau**, và
   không có cách nào nói cái nào đúng. `public_api/costing.py` gọi đó là
   "parallel engines" và cấm.

⛔ `routes.py` không phải chỗ chứa nghiệp vụ, và `jobs.py` cũng vậy — `AGENTS.md`
   mục 8. App này một miền nên nghiệp vụ ở `features.py`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

#: Thứ tự nhà cung cấp cho tool này. **Chỉ model nhà.**
#:
#: ⛔ KHÔNG thêm Gemini vào đây. Đây là hàng BÁN RA NGOÀI: khách trả tiền cho
#:    `ltt_llm` mà nhận về Gemini là bán sai hàng (D-010). Máy B bận thì báo bận,
#:    và để khách quyết định — khác hẳn `planner.py`, nơi cascade là hợp lệ vì
#:    đó là việc nội bộ và không có lời hứa nào với khách về model nào.
THU_TU_PROVIDER = ("ltt_llm",)

#: ⭐ ALIAS CÔNG KHAI -> ID NỘI BỘ. Đây là lớp đệm, và nó có lý do sống:
#:
#:    "Aliases exist so a vendor change is not a breaking change. If the raw id
#:     leaks anywhere a customer reads, integrations start pinning to it and the
#:     alias stops being a layer of insulation."   — test_212
#:
#: ⚠️ Bản đầu của tôi đặt alias TRÙNG HỆT id nội bộ (`ltt_llm` -> `ltt_llm`), tức
#:    là xoá sạch lớp đệm. `test_no_vendor_model_id_reaches_a_customer_surface`
#:    bắt được. Khách gọi `ltt_llm`; đằng sau là `qwen38-api`, và ngày ta đổi sang
#:    model khác thì **mã của khách không phải sửa một dòng nào**.
ALIAS_SANG_ID = {
    "ltt_llm": "qwen38-api",
    "ltt_llm_vision": "qwen38-vision",
}

MODEL_MAC_DINH = "ltt_llm"
MODEL_HOP_LE = tuple(ALIAS_SANG_ID)


#: ⛔ BÍ DANH, không phải định nghĩa — nguồn chân lý ở `ngan_sach.py`.
from apps.ltt_llm.ngan_sach import KY_TU_MOI_TOKEN

#: ⛔ BÍ DANH của `ngan_sach.mac_dinh_cho("sync")`.
#:
#:    Trước 30/08 đây là một hằng gõ tay `1_024`, và `_max_tokens()` của cửa
#:    **stream** lấy nhầm nó qua `executor.default_max_tokens` — mọi câu trả lời
#:    dài đều cụt ở đúng 1.024 token, không lỗi, không cảnh báo. Nay mỗi cửa
#:    phải **gọi tên cửa của mình**, nên nhầm lẫn đó không dựng lại được.
from apps.ltt_llm.ngan_sach import mac_dinh_cho as _mac_dinh_cho

SYNC_MAX_TOKENS_MAC_DINH = _mac_dinh_cho("sync")

#: Các số đo Q111 trên đúng RTX 3090/build đang phục vụ. Dùng tốc độ thấp hơn số
#: đo để admission nghiêng về phía an toàn: prefill chậm nhất đo được là
#: 756,49 tok/s ở 131K, decode là 41,57 tok/s.
SYNC_PREFILL_TOKEN_GIAY = 750
SYNC_DECODE_TOKEN_GIAY = 40
SYNC_DU_PHONG_NAP_MODEL_GIAY = 25
SYNC_DU_PHONG_HA_TANG_GIAY = 5
SYNC_LE_TOKEN_KHUON = 512


def uoc_giay_dong_bo(token_vao_uoc: int, max_tokens: int) -> float:
    """Ước thời gian xấu có kiểm soát cho một lượt trả JSON một cục.

    Prefill và decode là hai pha nối tiếp, nên phải cộng thời gian của cả hai.
    Chừa riêng 25 giây cho ca llama-swap phải nạp lại model và 5 giây cho tunnel,
    lập hoá đơn cùng sai số hệ thống. Đây là admission, không phải ETA hiển thị.
    """
    vao = max(0, int(token_vao_uoc or 0)) + SYNC_LE_TOKEN_KHUON
    ra = max(0, int(max_tokens or 0))
    return (
        SYNC_DU_PHONG_NAP_MODEL_GIAY
        + SYNC_DU_PHONG_HA_TANG_GIAY
        + vao / SYNC_PREFILL_TOKEN_GIAY
        + ra / SYNC_DECODE_TOKEN_GIAY
    )


def tran_token_ra_dong_bo(token_vao_uoc: int, ngan_sach_giay: int) -> int:
    """Số token ra tối đa còn vừa ngân sách sau khi tính thời gian prefill."""
    from apps.ltt_llm.manifest import MAX_TOKENS_TRAN

    giay_co_dinh = SYNC_DU_PHONG_NAP_MODEL_GIAY + SYNC_DU_PHONG_HA_TANG_GIAY
    vao = max(0, int(token_vao_uoc or 0)) + SYNC_LE_TOKEN_KHUON
    giay_con = float(ngan_sach_giay) - giay_co_dinh
    giay_con -= vao / SYNC_PREFILL_TOKEN_GIAY
    theo_thoi_gian = int(giay_con * SYNC_DECODE_TOKEN_GIAY)
    return max(0, min(MAX_TOKENS_TRAN, theo_thoi_gian))


def uoc_token_vao(messages, tools=None) -> int:
    """Ước số token đầu vào từ `messages` và schema `tools`. **Ước CAO có chủ ý.**

    ⭐ MỘT CHỖ DUY NHẤT. Cả `manifest._cost` (trần của cửa job) lẫn
       `server/api/chat.py` (giữ chỗ của cửa đồng bộ) đều gọi hàm này. Hai cửa
       ước khác nhau nghĩa là cùng một yêu cầu bị báo hai giá, và không có cách
       nào nói cái nào đúng — chính điều mà `public_api/costing.py` gọi là
       "parallel engines" và cấm.
    """
    ky_tu = 0
    for tin in messages or []:
        noi = (tin or {}).get("content")
        if isinstance(noi, str):
            ky_tu += len(noi)
        elif isinstance(noi, list):
            for p in noi:
                if isinstance(p, dict):
                    ky_tu += len(str(p.get("text") or ""))
    if isinstance(tools, list) and tools:
        # Tool schema được chèn vào prompt ở mỗi lượt. Codex/Claude agent thường
        # mang hàng chục schema; bỏ nó làm admission và phần giữ tiền cùng ước
        # thiếu đúng trên workload quan trọng nhất của API này.
        import json
        ky_tu += len(json.dumps(tools, ensure_ascii=False, separators=(",", ":")))
    return int(ky_tu / KY_TU_MOI_TOKEN) + 1


class ThamSoSai(ValueError):
    """Tham số khách gửi không hợp lệ. **Không phải lỗi hệ thống.**"""


@dataclass(frozen=True)
class KetQua:
    """Kết quả một lượt, đủ để trả cho cả hai cửa và để tính tiền."""

    noi_dung: str
    suy_nghi: str
    tool_calls: tuple
    finish_reason: str
    model: str
    token_vao: int
    token_ra: int
    token_vao_cache: int
    do_duoc: bool

    def gia_that_credit(self) -> int:
        """Giá THẬT của lượt này, tính từ token đã đo. Đơn vị: credit nguyên (C1).

        🔴 KHÔNG CÓ HÀM NÀY THÌ KHÁCH BỊ THU TRỌN PHẦN ĐÃ GIỮ.
           `job_runner._quyet_toan_credit` lấy giá cuối từ `result["credit_cost"]`;
           handler **không báo** thì nó dùng đúng phần đã giữ. Mà phần đã giữ là
           **trần ước cao** — xin `max_tokens=4096` mà model chỉ sinh 200 token
           thì khách vẫn trả đủ 4096. Đó là một lỗi tiền, im lặng.

        ⛔ KHÔNG ĐO ĐƯỢC THÌ KHÔNG THU. `dang_tin=False` ⇒ trả **0**, không trả
           phần đã giữ. Thu tiền mà không có bằng chứng còn tệ hơn mất một ít
           tiền — cùng luật với `thanh_toan.quyet_toan_hoac_hoan`.
        """
        from platform_core.llm import gia_token
        from platform_core.llm.cong_vlm import SuDung

        if not self.do_duoc:
            return 0
        cp = gia_token.tinh(SuDung(token_vao=self.token_vao,
                                   token_ra=self.token_ra,
                                   token_vao_cache=self.token_vao_cache,
                                   dang_tin=True))
        return cp.tong_credit_lam_tron_len

    def as_result(self) -> dict:
        """Hình dạng trả về cho cửa JOB (khớp `returns` của ToolSpec).

        ⭐ `usage` nằm trong kết quả là **có chủ ý**: `public_api/costing.py` ghi
           rõ *"A per-job token figure appears here only when a handler reports
           one in its result"*. Không báo thì nền tảng không quy được token về job.

        ⭐ `credit_cost` cũng vậy, và nó là **tiền thật** — xem `gia_that_credit`.
        """
        return {
            "content": self.noi_dung,
            "tool_calls": list(self.tool_calls),
            # Nền tảng đọc đúng khoá này để quyết toán. `credit.quyet_toan` đã
            # kẹp ở phần đã giữ, nên khách **không bao giờ** trả nhiều hơn báo giá.
            "credit_cost": self.gia_that_credit(),
            "usage": {
                "prompt_tokens": self.token_vao,
                "completion_tokens": self.token_ra,
                "total_tokens": self.token_vao + self.token_ra,
                "cached_prompt_tokens": self.token_vao_cache,
                "measured": self.do_duoc,
            },
        }


def kiem_tham_so(params: dict) -> dict:
    """Kiểm và chuẩn hoá tham số. Ném `ThamSoSai` — bên gọi dịch thành 400/422.

    ⛔ Kiểm TRƯỚC khi tiền chuyển. `server/api/jobs.py` nói cùng một câu:
       *"Validation first: a typo must never reach the ledger."*
    """
    p = dict(params or {})

    messages = p.get("messages")
    if not isinstance(messages, list) or not messages:
        raise ThamSoSai("`messages` phai la mot danh sach khong rong")
    for tin in messages:
        if not isinstance(tin, dict) or "role" not in tin:
            raise ThamSoSai("moi phan tu cua `messages` phai co `role`")

    model = str(p.get("model") or MODEL_MAC_DINH)
    if model not in MODEL_HOP_LE:
        raise ThamSoSai(f"`model` phai la mot trong {list(MODEL_HOP_LE)}")

    from apps.ltt_llm.manifest import MAX_TOKENS_MAC_DINH, MAX_TOKENS_TRAN
    xin_ra = p.get("max_tokens")
    xin_ra = int(xin_ra) if isinstance(xin_ra, (int, float)) else MAX_TOKENS_MAC_DINH
    if xin_ra < 1 or xin_ra > MAX_TOKENS_TRAN:
        raise ThamSoSai(f"`max_tokens` phai trong khoang 1..{MAX_TOKENS_TRAN}")

    sach = {"messages": messages, "model": model, "max_tokens": xin_ra}

    if p.get("temperature") is not None:
        try:
            t = float(p["temperature"])
        except (TypeError, ValueError):
            raise ThamSoSai("`temperature` phai la so") from None
        if not (0.0 <= t <= 2.0):
            raise ThamSoSai("`temperature` phai trong khoang 0..2")
        sach["temperature"] = t

    if p.get("tools") is not None:
        if not isinstance(p["tools"], list):
            raise ThamSoSai("`tools` phai la mot danh sach")
        sach["tools"] = p["tools"]

    if p.get("reasoning_effort") is not None:
        re_ = str(p["reasoning_effort"])
        if re_ not in ("low", "medium", "xhigh"):
            raise ThamSoSai("`reasoning_effort` phai la low|medium|xhigh")
        sach["reasoning_effort"] = re_

    return sach


def chay(db, params: dict, *, timeout_s: float = 300.0,
         on_dispatch=None, on_rejected=None) -> KetQua:
    """Chạy một lượt. Ném `ThamSoSai`, `BanError`, `VuotNganSachError`, `CongVlmError`.

    ⛔ KHÔNG tự trừ credit ở đây. Tiền do **cửa** lo:
         cửa job     — nền tảng giữ/quyết toán quanh `invocation.submit`
         cửa đồng bộ — `platform_core/llm/thanh_toan.py`
       Trộn việc trừ tiền vào đây là đường chắc nhất để một lượt bị thu hai lần.
    """
    from platform_core.llm import dieu_phoi

    sach = kiem_tham_so(params)
    kq = dieu_phoi.goi(
        db,
        messages=sach["messages"],
        thu_tu_provider=THU_TU_PROVIDER,
        # Dich alias -> id noi bo NGAY TRUOC KHI RA KHOI nen tang.
        model_theo_provider={"ltt_llm": ALIAS_SANG_ID[sach["model"]]},
        tools=sach.get("tools"),
        max_tokens=sach["max_tokens"],
        temperature=sach.get("temperature"),
        reasoning_effort=sach.get("reasoning_effort"),
        timeout_s=timeout_s,
        on_dispatch=on_dispatch,
        on_rejected=on_rejected,
    )
    su = kq.su_dung
    return KetQua(
        noi_dung=kq.noi_dung, suy_nghi=kq.suy_nghi,
        tool_calls=tuple(kq.tool_calls), finish_reason=kq.finish_reason,
        model=sach["model"],
        token_vao=su.token_vao, token_ra=su.token_ra,
        token_vao_cache=su.token_vao_cache, do_duoc=su.dang_tin,
    )

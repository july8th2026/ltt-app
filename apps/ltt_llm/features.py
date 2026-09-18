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

import logging
from dataclasses import dataclass
from typing import Any, Optional

log = logging.getLogger("apps.ltt_llm.features")

#: Thứ tự nhà cung cấp cho tool này. **Chỉ model nhà.**
#:
#: ⛔ KHÔNG thêm Gemini vào đây. Đây là hàng BÁN RA NGOÀI: khách trả tiền cho
#:    `ltt_llm` mà nhận về Gemini là bán sai hàng (D-010). Máy B bận thì báo bận,
#:    và để khách quyết định — khác hẳn `planner.py`, nơi cascade là hợp lệ vì
#:    đó là việc nội bộ và không có lời hứa nào với khách về model nào.
#: ⛔ BÍ DANH, không phải định nghĩa — nguồn chân lý nay ở
#:    `platform_core/llm/canonical.py` (chuyển lên ở pha 05 của AI CLEAN
#:    REBUILD V2). Tên ở đây **giữ nguyên**, nên hợp đồng công khai của app
#:    không đổi một chữ.
#:
#: ⭐ Vì sao phải chuyển: **ba bên** cần cùng bảng này và không bên nào được
#:    import `apps/ltt_llm` — `.importlinter` cưỡng chế cả ba:
#:      app khác          -> contract `app-doc-lap-voi-nhau`
#:      agent/planner.py  -> contract `nen-tang-khong-phu-thuoc-app`
#:      server/streaming  -> contract `server-khong-phu-thuoc-app-cu-the`
#:    Bốn dòng chú thích gốc (D-010, lý do lớp đệm, và lỗi alias-trùng-id đã
#:    mắc một lần) đi theo sang tệp mới, không bị bỏ lại.
from platform_core.llm.canonical import (ALIAS_SANG_ID,  # noqa: F401
                                         MODEL_HOP_LE, MODEL_MAC_DINH,
                                         THU_TU_PROVIDER)


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


def _ky_tu_noi_dung(noi_dung) -> int:
    """Đếm bảo thủ mọi chữ nằm trong một khối nội dung agent.

    Anthropic đặt ``tool_use``/``tool_result`` thành dict lồng trong ``content``.
    Chỉ đọc khóa ``text`` làm máy A ước thiếu đúng ở những phiên Claude Code dài,
    trong khi máy B vẫn đếm các chuỗi lồng và từ chối vì pool KV. Ảnh được giữ
    riêng theo ``AdmissionModel.token_giu_moi_anh`` nên không đếm chuỗi base64 ở đây.
    """
    if isinstance(noi_dung, str):
        return len(noi_dung)
    if isinstance(noi_dung, list):
        return sum(_ky_tu_noi_dung(phan) for phan in noi_dung)
    if not isinstance(noi_dung, dict):
        return 0

    loai = str(noi_dung.get("type") or "")
    if loai in ("image", "image_url", "input_image"):
        return 0
    if loai in ("text", "input_text", "output_text"):
        return len(str(noi_dung.get("text") or ""))
    return sum(_ky_tu_noi_dung(gt) for gt in noi_dung.values())


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
        ky_tu += _ky_tu_noi_dung(noi)
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

        🔴 GIÁ THEO `self.model` (D07, dual-model 2.5) — **model thật đã phục
           vụ**, không phải mặc định của cửa. `self.model` là bí danh khách xin
           và là chính bí danh `chay()` đã dịch sang id nội bộ để gọi máy B, nên
           không có khe nào cho "tính giá model này, chạy model kia".
        """
        from platform_core.llm import gia_token
        from platform_core.llm.cong_vlm import SuDung

        if not self.do_duoc:
            return 0
        cp = gia_token.tinh(SuDung(token_vao=self.token_vao,
                                   token_ra=self.token_ra,
                                   token_vao_cache=self.token_vao_cache,
                                   dang_tin=True),
                            self.model)
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


#: Tham so di THANG len may B, khong can nen tang dien giai gi them.
#:
#: ⛔ Chung da qua `kiem_tham_so`, nen day KHONG phai mot danh sach tu do — no
#:    la ban khai "nhung thu nen tang chi chuyen tiep". `messages`/`model`/
#:    `max_tokens`/`temperature`/`reasoning_effort`/`tools` KHONG nam o day vi
#:    chung co doi so co ten rieng va co lop dich (alias -> id noi bo).
THAM_SO_CHUYEN_THANG = ("response_format", "tool_choice", "parallel_tool_calls",
                        "top_p", "seed", "stop")




def kiem_tham_so_sinh(p: dict, sach: dict | None = None) -> dict:
    """Kiem CHI cac tham so SINH, dung chung cho MOI cua. Nem `ThamSoSai`.

    ## 🔴 Vi sao phai tach ra khoi `kiem_tham_so`

    Do 14/09/2026 tren production, cung mot gia tri sai `top_p=5`:

        POST /api/v1/chat/completions  (dong bo) -> 400 invalid_request
        POST /api/v1/messages          (stream)  -> 200, chay binh thuong

    Cua stream KHONG di qua `kiem_tham_so`: `runtime_noi_bo/luong.tien_kiem`
    lam `gui = dict(than)` — chep CA than request roi chuyen thang len may B.
    Nen mot hop dong cong bo, hai cua tra loi khac nhau.

    ⭐ Khuon chuan cua cong dong: vLLM khai MOT `ChatCompletionRequest` trong do
       `stream: bool | None = False` chi la **mot truong nhu moi truong khac**,
       va moi `@model_validator` chay tren ca request TRUOC khi re nhanh stream
       (`vllm/entrypoints/openai/chat_completion/protocol.py`). Kiem mot lan,
       cho moi cua — khong cua nao duoc di vong.

    ## ⛔ Nhung KHONG the goi thang `kiem_tham_so` o cua stream

    Hai cua stream noi giao thuc KHAC: `/messages` (Anthropic) mang `system`,
    `/responses` (OpenAI Responses) mang `input` co the la chuoi tran. Dua chung
    qua `kiem_tham_so` la tai dien dung loi 500 ma docstring `_tin_that` da ghi:
    *"moi phan tu cua messages phai co role"*.

    ⇒ Ham nay kiem DUNG phan tham so sinh, va **bo qua moi khoa no khong biet**.
       Bo qua chu khong tu choi la co chu y: client Anthropic gui `top_k`,
       `stop_sequences`, `metadata` — tu choi chung la be Claude Code va Codex
       dang chay that.
    """
    sach = dict(sach or {})

    if p.get("temperature") is not None:
        try:
            t = float(p["temperature"])
        except (TypeError, ValueError):
            raise ThamSoSai("`temperature` phai la so") from None
        if not (0.0 <= t <= 2.0):
            raise ThamSoSai("`temperature` phai trong khoang 0..2")
        sach["temperature"] = t

    # ── 🔴 MO LAI NHUNG THU HAM NAY TUNG VUT IM LANG (14/09/2026) ────────────
    #
    # Ham nay la mot DANH SACH TRANG: thu gi khong duoc chep vao `sach` thi
    # bien mat, va khach van nhan **200**. Do 14/09 tren chinh production, cung
    # mot request `response_format: json_schema` bat buoc `ten/tuoi/thanh_pho`:
    #
    #   qua may A   ->  {"id":10,"name":...,"age":...,"city":...}  boc trong ```json
    #   thang may B ->  {"ten":"...","tuoi":34,"thanh_pho":"Ha Noi"}    DUNG khuon
    #
    # Tuc engine LAM DUOC hoan hao; tang nen tang nem tham so di roi tra 200.
    # Do la cua gia te nhat: khach dat `response_format`, tin no chay, va bo
    # phan tich JSON cua ho vo **luc duoc luc khong**.
    #
    # ⛔ KHONG mo `grammar` tho (BNF) du engine co ho tro: no la mot truong TU DO
    #    di thang toi bo giai ma va khong cong nao kiem duoc — dung ly le kho nay
    #    da dung de hoan `refs` cua `video.generate`. `json_schema` kiem duoc
    #    hinh dang, nen no mo.
    #
    # ⛔ KHONG mo `n`: no NHAN chi phi sinh len n lan trong khi bao gia va giu
    #    cho deu tinh cho MOT chuoi. Mo no la ban duoi gia von.
    if p.get("response_format") is not None:
        rf = p["response_format"]
        if not isinstance(rf, dict):
            raise ThamSoSai("`response_format` phai la mot doi tuong")
        kieu = str(rf.get("type") or "")
        if kieu not in ("text", "json_object", "json_schema"):
            raise ThamSoSai(
                "`response_format.type` phai la text|json_object|json_schema")
        if kieu == "json_schema" and not isinstance(rf.get("json_schema"), dict):
            raise ThamSoSai("`response_format.json_schema` phai la mot doi tuong "
                            "khi type=json_schema")
        sach["response_format"] = rf

    if p.get("tool_choice") is not None:
        # ⛔ CHI nhan chuoi, du hop dong goc con co dang doi tuong (ep MOT ham
        #    cu the). Ly do nam o `manifest.params_schema`: he kieu cua Public
        #    API khong co kieu HOP, nen dang doi tuong khong CONG BO duoc. Nhan
        #    no o day ma khong khai o kia la dung cai bay ta vua di sua —
        #    mot nang luc chay that ma khong ai doc duoc trong hop dong.
        tc = p["tool_choice"]
        if not isinstance(tc, str) or tc not in ("none", "auto", "required"):
            raise ThamSoSai("`tool_choice` phai la none|auto|required")
        sach["tool_choice"] = tc

    if p.get("parallel_tool_calls") is not None:
        if not isinstance(p["parallel_tool_calls"], bool):
            raise ThamSoSai("`parallel_tool_calls` phai la true/false")
        sach["parallel_tool_calls"] = p["parallel_tool_calls"]

    if p.get("top_p") is not None:
        try:
            tp = float(p["top_p"])
        except (TypeError, ValueError):
            raise ThamSoSai("`top_p` phai la so") from None
        if not (0.0 < tp <= 1.0):
            raise ThamSoSai("`top_p` phai trong khoang (0..1]")
        sach["top_p"] = tp

    if p.get("seed") is not None:
        if isinstance(p["seed"], bool) or not isinstance(p["seed"], int):
            raise ThamSoSai("`seed` phai la so nguyen")
        sach["seed"] = int(p["seed"])

    if p.get("stop") is not None:
        st = p["stop"]
        if isinstance(st, str):
            st = [st]
        if (not isinstance(st, list) or not st
                or not all(isinstance(x, str) and x for x in st)):
            raise ThamSoSai("`stop` phai la chuoi hoac danh sach chuoi khong rong")
        # Tran 4 la cua chinh hop dong OpenAI ma ta dang bat chuoc, khong phai
        # mot con so ta tu dat.
        if len(st) > 4:
            raise ThamSoSai("`stop` toi da 4 chuoi")
        sach["stop"] = st

    return sach


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

    # ⭐ Suy nghĩ do MÁY CHỦ quyết (L-26) — CÙNG hàm với cửa stream
    #    (`runtime_noi_bo.luong.tien_kiem`/`chuan_bi`): gỡ trường ghi đè budget/
    #    bật-tắt và thẻ `<|think_*|>` trong nội dung, chuẩn hoá effort theo model
    #    (3.8: minimal→low, high|max→xhigh; 3.5: gỡ; none|off: 400 mọi model).
    #    Nguồn và lý do ở docstring của hàm; không viết lại luật ở đây.
    from platform_core.runtime_noi_bo.luong import ThamSoSai as _LoiLuong
    from platform_core.runtime_noi_bo.luong import chuan_hoa_suy_nghi
    try:
        p, _bo_qua = chuan_hoa_suy_nghi(p, model)
    except _LoiLuong as e:
        raise ThamSoSai(str(e)) from None
    messages = p["messages"]

    from apps.ltt_llm.manifest import MAX_TOKENS_MAC_DINH, MAX_TOKENS_TRAN
    xin_ra = p.get("max_tokens")
    xin_ra = int(xin_ra) if isinstance(xin_ra, (int, float)) else MAX_TOKENS_MAC_DINH
    if xin_ra < 1 or xin_ra > MAX_TOKENS_TRAN:
        raise ThamSoSai(f"`max_tokens` phai trong khoang 1..{MAX_TOKENS_TRAN}")

    sach = {"messages": messages, "model": model, "max_tokens": xin_ra}

    if p.get("tools") is not None:
        if not isinstance(p["tools"], list):
            raise ThamSoSai("`tools` phai la mot danh sach")
        sach["tools"] = p["tools"]

    if p.get("reasoning_effort") is not None:
        re_ = str(p["reasoning_effort"])
        # 🔴 `none` DA BI BO 14/09/2026, VA DAY LA MOT DINH CHINH CUA L-02.
        #
        #    L-02 (13/09) them `none` vao be mat cong khai lam "nut cho cau tra
        #    loi ngan". Y do dung; nhung tren HE NAY no hong, va ba nguon doc
        #    lap noi cung mot dieu:
        #
        #    1. Do 14/09 tren may B, cung prompt, `max_tokens=8000`:
        #         reasoning_effort=medium/low/khong khai -> ~1.180 token ra
        #         reasoning_effort=none                  ->      2 token ra
        #       Model noi "1" roi dung. `finish_reason=stop`.
        #
        #    2. `llama-swap.yaml` da ghi tu 12/09, kem bang do 60 bo de:
        #         "dung tat suy nghi: do la HONG, khong phai danh doi.
        #          Nhanh gap ~20 lan nhung tieng Viet con 10 %, sinh dai con 40 %."
        #
        #    3. Model card Qwen khai HAI bo tham so lay mau khac nhau:
        #         thinking      temp 0.6  top_p 0.95  top_k 20  min_p 0
        #         non-thinking  temp 0.7  top_p 0.80  top_k 20  min_p 0
        #       May B chay bo THINKING, va `llama-swap.yaml` ghi ro tham so lay
        #       mau dat o SERVER chu khong gui theo request (cache CUDA graph
        #       khoa theo bo tham so). Tuc `none` o day = chay non-thinking bang
        #       tham so cua thinking — mot to hop nha san xuat khong khuyen, va
        #       so do o tren cho thay hau qua.
        #
        # ⛔ Giu `none` trong hop dong la ban mot nut da do duoc la HONG. Va
        #    KHONG anh xa ngam `none` -> `low`: khach xin mot dang, ta lam mot
        #    dang khac, khong noi gi — dung lop "cua gia" ta di sua ca phien.
        #
        # ⭐ Loi bao phai NOI DUONG RA. Khach muon cau tra loi ngan van co duong:
        #    `low` nghi it nhat trong ba muc con lai (do 13/09: 3.5 = 206 token,
        #    3.8 = 63 token).
        #
        # ⭐ Từ 18/09 (L-26) luật đã chạy ở `chuan_hoa_suy_nghi` phía trên: tới
        #    đây `none|off` đã thành 400 và giá trị đã là mức của model.
        sach["reasoning_effort"] = re_

    sach = kiem_tham_so_sinh(p, sach)

    return sach


def kiem_san_token_ra(sach: dict) -> None:
    """Tu choi mot `max_tokens` thap den muc chac chan tra ve RONG. Nem `ThamSoSai`.

    ## Vi sao la mot ham RIENG, khong nam trong `kiem_tham_so`

    🔴 **413 dung truoc moi thu khac** (spec §6), va phep kiem nay khong phai
       kiem HINH DANG — no la mot phan doan ve NGAN SACH. `kiem_tham_so` chay
       truoc 413 o cua dong bo, nen de no o trong ay thi mot hoi thoai 65K token
       xin `max_tokens` thap se nhan **400 thay vi 413** — va Codex/Claude Code
       dua dung vao ma 413 de TU NEN hoi thoai. Chen mot loi khac len truoc no
       la lay mat duong tu chua cua client, doi lay mot loi khuyen ("nang
       max_tokens len") vo nghia voi mot yeu cau du sao cung qua dai.

    ⛔ Nen ben goi phai goi ham nay SAU khoi 413 cua minh. `server/api/chat.py`
       lam vay; `tests/test_1239` chot lai thu tu ay bang mot yeu cau vi pham
       CA HAI dieu cung luc.

    ## Vi sao tu choi thay vi cu chay

    🔴 KHONG DOT GPU ROI TRA RONG. Cung khuon 413 cua input qua dai: mot yeu cau
       khong the nao du cho thi se khong du KE CA khi may B ranh hoan toan, nen
       dung de no di vao hang doi roi thu tien cho mot chuoi rong (do:
       `mcredit_du` +4 cho mot luot khach khong nhan duoc gi).

    ⭐ Thong diep phai NOI DUONG RA, khong chi noi "sai". Khach muon cau tra loi
       ngan co hai duong, va duong dung la TAT SUY NGHI — khong phai bop tran.
       Mot loi bao chi noi "max_tokens qua thap" se day ho di dung huong nguoc
       lai.
    """
    from apps.ltt_llm.ngan_sach import san_token_ra

    xin_ra = int(sach.get("max_tokens") or 0)
    _san = san_token_ra(sach.get("model"), sach.get("reasoning_effort"))
    if xin_ra >= _san:
        return
    from apps.ltt_llm.ngan_sach import nghi_mac_dinh
    from platform_core.public_api.examples import CODEX_MODEL_REASONING_CO_DINH
    if sach.get("model") in CODEX_MODEL_REASONING_CO_DINH:
        # ⛔ Không chỉ sang `low`: model này không có nấc (L-26) — effort bị bỏ
        #    qua, suy nghĩ luôn tiêu tới budget engine. Đường ra thật là trần
        #    cao hơn, và nếu cửa đồng bộ không chứa nổi trần đó trong ngân sách
        #    thời gian của nó thì là stream hoặc job.
        raise ThamSoSai(
            f"`max_tokens` is {xin_ra}, below the {_san} `{sach.get('model')}` "
            f"needs: this model always thinks before answering (its thinking "
            f"budget is set by the server; reasoning_effort is accepted and "
            f"ignored), and thinking spends the same budget as the answer, so a "
            f"lower ceiling returns empty content with finish_reason='length'. "
            f"Set max_tokens to at least {_san}. If this synchronous endpoint "
            f"cannot fit that in its time budget, use POST /api/v1/messages or "
            f"/api/v1/responses with stream=true, or POST /api/v1/jobs.")
    _muc = sach.get("reasoning_effort") or nghi_mac_dinh(sach.get("model"))
    # 🔴 CÂU NÀY TỪNG MÁCH `reasoning_effort='none'` — một giá trị đã bị GỠ khỏi
    #    hợp đồng ngày 14/09/2026. Tức lỗi chỉ khách sang một thứ cửa sẽ từ chối:
    #    họ sửa đúng như lời ta bảo rồi nhận tiếp một 400 khác. Một lỗi chỉ sai
    #    đường còn tệ hơn một lỗi không chỉ đường nào.
    #
    # ⭐ `low` là mức thấp nhất còn phục vụ, nên sàn của nó là con số đúng để nêu.
    raise ThamSoSai(
        f"`max_tokens` is {xin_ra}, below the {_san} this model needs at "
        f"reasoning_effort={_muc!r}: thinking spends the same budget as the "
        f"answer, so a low ceiling returns empty content with "
        f"finish_reason='length'. Either raise max_tokens, or - for a short "
        f"answer - set reasoning_effort='low' (floor "
        f"{san_token_ra(sach.get('model'), 'low')}). Do not lower max_tokens "
        f"to get a shorter reply; that is the other switch.")


def chay(db, params: dict, *, timeout_s: float = 300.0,
         on_dispatch=None, on_rejected=None, ma_luot: str = "") -> KetQua:
    """Chạy một lượt. Ném `ThamSoSai`, `BanError`, `VuotNganSachError`, `CongVlmError`.

    `ma_luot` — mã của lượt, chuyển thẳng xuống `dieu_phoi`. Nó là cái tên để
    `huy_luot.huy()` cắt lượt này từ ngoài (cửa job dùng), và là `X-LTT-Request-Id`
    nối log hai máy. Rỗng ⇒ hành vi cũ y nguyên.

    ⛔ KHÔNG tự trừ credit ở đây. Tiền do **cửa** lo:
         cửa job     — nền tảng giữ/quyết toán quanh `invocation.submit`
         cửa đồng bộ — `platform_core/llm/thanh_toan.py`
       Trộn việc trừ tiền vào đây là đường chắc nhất để một lượt bị thu hai lần.
    """
    from platform_core.llm import dieu_phoi

    sach = kiem_tham_so(params)
    try:
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
            # ⭐ MOT cho duy nhat de mot tham so moi di het duong len may B. Truoc
            #    14/09 moi tham so phai duoc moc tay o BON tang (kiem_tham_so ->
            #    dieu_phoi.goi -> than -> may B), va chinh vi the `response_format`
            #    dung o tang mot roi bien mat. `tests/test_1255` chot rang moi khoa
            #    khai trong `params_schema` phai song sot.
            them={k: sach[k] for k in THAM_SO_CHUYEN_THANG if k in sach},
            timeout_s=timeout_s,
            on_dispatch=on_dispatch,
            on_rejected=on_rejected,
            ma_luot=ma_luot,
        )
    except dieu_phoi.KhongCoProviderNao as e:
        # `dieu_phoi` cascade qua moi provider khi mot cong tra 429. App nay co
        # dung MOT provider (D-010), nen ket cuc "het provider" van la cung tin
        # hieu BAN, khong phai loi 500. Giu quan he co kieu `busy_only`; khong
        # doc chu "ban" tu thong diep o cua HTTP.
        if e.busy_only:
            from platform_core.llm.cong_vlm import BanError
            raise BanError("model dang ban", retry_after_s=30) from e
        raise
    su = kq.su_dung
    return KetQua(
        noi_dung=kq.noi_dung, suy_nghi=kq.suy_nghi,
        tool_calls=tuple(kq.tool_calls), finish_reason=kq.finish_reason,
        model=sach["model"],
        token_vao=su.token_vao, token_ra=su.token_ra,
        token_vao_cache=su.token_vao_cache, do_duoc=su.dang_tin,
    )


def _dia_chi_cong() -> str:
    """Dia chi cong may B, giai theo ĐÚNG thu tu ma duong goi that dung.

    🔴 `luong_vlm.mo` lay `base_url` cua **KHOA** truoc, roi moi den registry
       (`luong_vlm.py:136-137`). Ban dau ham nay chi doc registry — va do LIVE
       03/09 cho thay hau qua: cong may B tra 200 o `/live`, nhung hook bao
       `chua_san_sang` vi registry rong tren may nay.

    ⛔ Mot chip "chua san sang" SAI lam o soan bi tat cho **moi** nguoi trong
       khi model chay tot. No la mat ngoai kia cua dung cai loi ma Phase 06
       sinh ra de chan (chip xanh noi doi) — chi khac chieu, va chieu nay lam
       mat ca san pham chu khong chi lam nguoi dung buc minh.

    Doc CSDL chi de lay `base_url` — **khong** giai ma credential.
    """
    from platform_core import providers

    prov = providers.get(THU_TU_PROVIDER[0])
    tu_registry = (getattr(prov, "base_url", "") or "").strip()
    if tu_registry:
        return tu_registry
    try:
        from platform_core.db import get_session
        from platform_core.models import ApiKey

        gen = get_session()
        db = next(gen)
        try:
            # Loc theo `provider` (mot cot that); `categories` la chuoi gop nen
            # khong loc trong SQL — va khong can: mot provider `ltt_llm` chi
            # phuc vu mot thu.
            hang = db.query(ApiKey.base_url).filter(
                ApiKey.provider == THU_TU_PROVIDER[0],
                ApiKey.base_url != "").first()
            return (hang[0] or "").strip() if hang else ""
        finally:
            try:
                next(gen)
            except StopIteration:
                pass
    except Exception as e:                                      # noqa: BLE001
        log.info("suc_khoe: khong doc duoc base_url tu khoa (%s)", type(e).__name__)
        return ""


def suc_khoe(timeout_s: float = 1.5) -> str:
    """Suc khoe cua `text.chat` cho catalog san pham khac (`AppManifest.suc_khoe`).

    Hoi `GET /live` cua cong may B — duong **khong can khoa** va co y khong noi
    gi them (xem `llm_gateway/api.py::live`). Khong bao gio nem: moi loi mang
    deu la "chua san sang", va do chinh la cau tra loi dung cho nguoi dung.

    Ban (429) khong nhin thay o `/live`; "ban" duoc cua stream bao luc goi that
    qua `DangBan` — catalog khong doan truoc dieu do.
    """
    base = _dia_chi_cong()
    if not base:
        return "chua_san_sang"
    import httpx

    try:
        r = httpx.get(base.rstrip("/") + "/live", timeout=timeout_s)
    except httpx.HTTPError as e:
        log.info("suc_khoe: cong LLM khong tra loi (%s)", type(e).__name__)
        return "chua_san_sang"
    return "san_sang" if r.status_code == 200 else "chua_san_sang"

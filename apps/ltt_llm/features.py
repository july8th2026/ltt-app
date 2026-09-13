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
        # 🔴 THEM `none` 13/09/2026 (L-02) — va day la mot NUT KHAC voi `max_tokens`.
        #
        #    Model card Qwen noi ro co HAI nut: `max_tokens` la tran DO DAI, con
        #    `enable_thinking=False` / `/no_think` la nut TAT SUY NGHI. Ta truoc
        #    nay chi mo nut thu nhat, nen mot khach muon cau tra loi NGAN khong
        #    co duong nao ngoai ha `max_tokens` — va do chinh la duong dan toi
        #    L-02: model tieu het tran vao suy nghi roi bi cat truoc khi tra loi
        #    (do: 5/5 luot RONG o `max_tokens` 150-250).
        #
        # ⛔ Ha `max_tokens` KHONG phai cach tat suy nghi. Nha san xuat khuyen
        #    `32.768` token ra cho hau het truy van; con duong cho cau tra loi
        #    ngan la tat thinking, khong phai bop tran.
        #
        #    Template froggeric v22.5 nhan `none`/`off` va anh xa `minimal` ->
        #    `low`. Ta mo dung `none` o be mat cong khai: mot ten cho mot y
        #    nghia, va `off` la bi danh de trung.
        if re_ not in ("none", "low", "medium", "xhigh"):
            raise ThamSoSai("`reasoning_effort` phai la none|low|medium|xhigh")
        sach["reasoning_effort"] = re_

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
    _muc = sach.get("reasoning_effort") or "medium"
    raise ThamSoSai(
        f"`max_tokens` is {xin_ra}, below the {_san} this model needs at "
        f"reasoning_effort={_muc!r}: thinking spends the same budget as the "
        f"answer, so a low ceiling returns empty content with "
        f"finish_reason='length'. Either raise max_tokens, or - for a short "
        f"answer - set reasoning_effort='none' (floor "
        f"{san_token_ra(sach.get('model'), 'none')}). Do not lower max_tokens "
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

"""
dieu_phoi.py — MỘT đường gọi model ngôn ngữ cho toàn nền tảng. (H38)

⭐ ĐÂY LÀ CÂY CẦU CÒN THIẾU. Trước nó, ba nơi tự gọi nhà cung cấp, mỗi nơi một kiểu:

     platform_core/agent/planner.py    ghi cứng `thu_tu_provider=["gemini"]` VÀ
                                       ghi cứng luôn HTTP của Gemini
                                       (cả hai đã gỡ ở pha 05.3 / 07)
     apps/autosubvideo/ai_workflows.py
     apps/<slug>/jobs.py

   Cascade đa-provider của H8 **có tồn tại**, nhưng chỉ ở tầng *cấp key*. Không ai
   bắc cầu nó sang tầng *gọi model*. Hệ quả: thêm một provider vào `REGISTRY`
   **không làm app nào dùng nó cả**. Module này là cây cầu đó.

⭐ CASCADE Ở ĐÂY LÀ HỢP LỆ — VÀ NÓ KHÁC HẲN CÁI D-010 CẤM.

   D-010 cấm **đổi model sau lưng khách**. Chỗ đó là API bán ra ngoài: khách trả
   tiền cho Qwen3.8-27B mà nhận về Gemini là bán sai hàng. `llm_gateway` và
   `cong_vlm.chat()` **không có** đường fallback, và có test soi chữ ký hàm để
   giữ nguyên như vậy.

   Module này phục vụ **việc nội bộ của nền tảng** (lập kế hoạch agent, tóm tắt,
   sinh phụ đề…). Ở đó không có lời hứa nào với khách về *model nào*, và bên gọi
   **tự khai thứ tự** trong `thu_tu_provider`. Khai ra thì không phải là lén.

⛔ BẬN KHÔNG PHẢI LỖI. `BanError` ⇒ **đi tiếp provider sau**, và **KHÔNG** gọi
   `api_pool.danh_dau_loi()`. Nếu lẫn, key `ltt_llm` bị cooldown rồi
   `disable` sau 5 lần — một tối máy B chạy video sẽ tự tắt vĩnh viễn model nhà.

⛔ VƯỢT NGÂN SÁCH KHÔNG PHẢI LỖI CỦA PROVIDER, VÀ KHÔNG ĐƯỢC CASCADE. Một yêu cầu
   quá to sẽ quá to với **mọi** provider. Thử lại ở nơi khác chỉ tốn thêm tiền và
   thêm thời gian, rồi vẫn hỏng.
"""
from __future__ import annotations

import contextvars
import logging
from contextlib import contextmanager
from typing import Any, Iterator, Optional, Sequence

from platform_core.llm.cong_vlm import (AmbiguousProviderError, BanError,
                                        CongVlm, CongVlmError, HuyError,
                                        YeuCauSaiError,
                                        KetQuaChat, ProviderOomError, SuDung,
                                        VuotNganSachError)

log = logging.getLogger(__name__)

#: Provider nói giao thức OpenAI (cổng VLM máy B). Thêm provider mới cùng loại
#: thì thêm vào đây, **không** viết thêm một nhánh `if` ở dưới.
PROVIDER_OPENAI = ("ltt_llm",)

#: Timeout MẶC ĐỊNH (giây) của một lần `goi()`, khi bên gọi không tự khai.
#:
#: 🔑 **Một số, MỘT chỗ khai — và chỗ khai này KHÔNG PHẢI chữ ký hàm.**
#:    Trước 25/09 hằng số này chỉ tồn tại như `default=` của tham số `timeout_s`
#:    ở `goi()` bên dưới, và `apps/auto_scan_video/ai.py::timeout_xau_nhat` đọc
#:    nó lại bằng `inspect.signature(goi).parameters["timeout_s"].default` — một
#:    kiểu "một số, một chỗ khai" ĐÚNG Ý nhưng SAI CHỖ: chữ ký hàm là thứ
#:    fixture/wrapper/mock THAY được (và một fixture kiểm E2E thật đã thay,
#:    N-52). `inspect` qua chữ ký một hàm ĐÃ BỊ THAY thì đọc chữ ký của BẢN
#:    THAY, không phải giá trị thật — `KeyError` khi bản thay thiếu tham số đó.
#:    ⇒ Hạ hằng số ra khỏi `default=`, để nó đứng một mình cạnh `goi()`. Sau đó
#:    thay `goi` bao nhiêu lần cũng không ảnh hưởng: không còn gì để soi bằng
#:    `inspect`, và không còn cách nào cho một giá trị sai lọt qua ÂM THẦM
#:    (⛔ đừng thêm `.get(...)`/fallback ở phía đọc — N-47, N-51 cùng họ "kẹp/
#:    fail-open im lặng").
TIMEOUT_GOI_MAC_DINH = 120.0

# 🔴 `PROVIDER_GEMINI` ĐÃ GỠ 09/09/2026 (AI CLEAN REBUILD V2 pha 07) cùng hàm
#    `_goi_gemini` và nhánh `if` của nó trong vòng lặp bên dưới.
#
# ⛔ Đừng thêm lại một hằng số nào có hình dạng ấy. Chú thích ngay trên đã nói
#    luật: *"thêm provider mới cùng loại thì thêm vào `PROVIDER_OPENAI`, KHÔNG
#    viết thêm một nhánh `if` ở dưới"*. Một họ giao thức thứ hai chỉ đáng có khi
#    nó **thật sự** khác giao thức — Gemini là họ duy nhất từng như vậy, và nó
#    không còn được phục vụ.


class KhongCoProviderNao(RuntimeError):
    """Mọi provider trong danh sách đều bận hoặc không cấp được key.

    ⛔ **Không phải lỗi provider.** Bên gọi nên báo "hệ thống đang bận, thử lại
       sau" chứ đừng đánh dấu lỗi cho key nào.
    """

    def __init__(self, chi_tiet: Sequence[str]):
        super().__init__("khong provider nao phuc vu duoc: " + "; ".join(chi_tiet))
        self.chi_tiet = list(chi_tiet)
        self.busy_only = bool(self.chi_tiet) and all(
            item.rstrip().endswith(": ban") for item in self.chi_tiet)


#: Số token ĐẶT CHỖ của lượt đang chạy trong ngữ cảnh này — đúng số lease máy A
#: đang giữ (`ExecutionLease.token_dat_truoc`). 0 = không có lease ngân sách KV.
#:
#: 🔴 PHƯƠNG ÁN C bước 1 (O-05, 17/09/2026). Cửa stream đã gửi số này lên máy B
#:    (`luong_vlm.mo` → `X-LTT-Token-Dat`) từ 15/09; cửa ĐỒNG BỘ và JOB đi qua
#:    đây thì không, nên máy B tự ước `in + out` (thiếu đệm ước) — hai sổ đếm
#:    HAI số cho cùng một lượt, và lượt A đã nhận có thể bị B 429.
#:
#: ⭐ Vì sao `ContextVar` chứ không thêm tham số: `executor.run(db, params, *,
#:    timeout_s)` là hợp đồng APP — cùng lý do `ngat.SO_DONG` (xem `ngat.py`).
#:    Cửa giữ lease bọc lời gọi trong `mang_dat_cho(so)`; `ngat.chay_canh_ngat`
#:    chép ngữ cảnh sang luồng gọi nên `_goi_openai` đọc được.
TOKEN_DAT_TRUOC: contextvars.ContextVar[int] = contextvars.ContextVar(
    "ltt_llm_token_dat_truoc", default=0)


@contextmanager
def mang_dat_cho(so_token: int) -> Iterator[None]:
    """Khai số token đặt chỗ của lượt sắp gọi — đi lên máy B trong `X-LTT-Token-Dat`."""
    moc = TOKEN_DAT_TRUOC.set(max(0, int(so_token or 0)))
    try:
        yield
    finally:
        TOKEN_DAT_TRUOC.reset(moc)


#: Trần thời gian cho lời gọi `POST /v1/huy` lên máy B. Ngắn có chủ ý — xem
#: `_bao_may_b_huy`: nó chặn một luồng canh, và luồng ấy đang giữ việc hoàn tiền.
HUY_TIMEOUT_S = 3.0


def _bao_may_b_huy(base_url: str, credential: str, ma_luot: str) -> None:
    """Bảo cổng máy B thôi sinh chữ cho lượt `ma_luot`. Best-effort, không ném.

    🔴 VÌ SAO ĐÓNG SOCKET A→B LÀ CHƯA ĐỦ. Thân của một endpoint `def` ở cổng chạy
       trong threadpool của uvicorn và **không** nhận tin khách đã đi — nó chỉ
       biết khi `upstream.json` trả về. Nên nếu máy A chỉ đóng kết nối của mình,
       lượt B→llama vẫn chạy tới hết cho một người đã đi: đúng cái GPU ta đang
       cố trả lại. `POST /v1/huy` là cách nói **bằng lời** điều mà một socket
       đóng không nói được.

    ⭐ Và nó dừng đúng một lượt, không hơn: cổng tra `ma_luot` trong sổ lượt của
       nó rồi đóng **cửa ra mạng của riêng lượt ấy**. llama.cpp nhả slot ≤1 s sau
       khi client rời (`server-context.cpp:39`). Không `taskkill`, không `/unload`
       của llama-swap (đường ấy không mang tên model nên nó nhả cả hai card,
       L-17), không chạm slot của ai khác.

    ⛔ NUỐT MỌI LỖI, VÀ TIMEOUT NGẮN. Hàm này chạy trên đường hủy, trong luồng
       canh, ngay trước khi worker hoàn tiền và nhả lease. Một máy B không trả lời
       **không được** làm việc hoàn tiền chậm lại hay hỏng — GPU chạy thừa vài
       chục giây là một khoản lãng phí; một khoản credit treo là một sai lệch sổ.
    """
    if not (base_url and ma_luot):
        return
    try:
        import httpx

        headers = {"Authorization": f"Bearer {credential}"} if credential else {}
        r = httpx.post(base_url.rstrip("/") + "/v1/huy",
                       json={"request_id": ma_luot}, headers=headers,
                       timeout=HUY_TIMEOUT_S)
        log.info("bao may B huy luot %s: %s", ma_luot, r.status_code)
    except Exception as e:  # noqa: BLE001 - duong huy khong duoc nem
        log.warning("khong bao duoc may B huy luot %s: %r", ma_luot, e)


def _goi_openai(base_url: str, credential: str, than: dict, timeout_s: float,
                *, ma_luot: str = "") -> KetQuaChat:
    import httpx

    from platform_core.llm import huy_luot, ngat

    # 🔴 MỘT `Client` CÓ TÊN, KHÔNG PHẢI `httpx.request`. Hai lý do, và lý do thứ
    #    hai mới là lý do đổi:
    #      1. dùng lại kết nối giữa hai lượt liên tiếp tới cùng máy B;
    #      2. **có thứ để đóng**. Khách ngắt giữa một lượt đồng bộ thì cửa phải
    #         cắt được kết nối tới máy B (spec §16) — `httpx.request` dựng client
    #         bên trong rồi vứt đi, nên không ai cầm được cái tay nắm ấy, và lượt
    #         vẫn chạy hết trên GPU cho một người đã đi.
    client = httpx.Client(timeout=timeout_s)

    def _dong() -> None:
        """Đường hủy **đầy đủ** của một lượt, và nó là MỘT hàm.

        Ba việc, theo thứ tự có lý do:
          1. bật cờ hủy — để nhánh `except httpx.HTTPError` dưới đây phân loại
             được "ta tự đóng" (⇒ `HuyError`) chứ không "mạng chập"
             (⇒ `AmbiguousProviderError`). Phải trước, vì bước 2 làm nó ném.
          2. đóng socket A→B — máy A thôi chờ ngay.
          3. bảo máy B thôi sinh chữ — vì bước 2 không nói được điều đó.

        ⛔ MỘT hàm ghi vào **hai** sổ (`ngat` theo ngữ cảnh, `huy_luot` theo mã).
           Hai hàm khác nhau cho hai sổ là cách chắc chắn để một đường hủy làm đủ
           ba việc và đường kia làm một — xem `huy_luot` đầu tệp.
        """
        if ma_luot:
            huy_luot.danh_dau(ma_luot)
        try:
            client.close()
        finally:
            if ma_luot:
                _bao_may_b_huy(base_url, credential, ma_luot)

    ngat.ghi_nhan(_dong)
    if ma_luot:
        huy_luot.ghi_nhan(ma_luot, _dong)

    def goi(method, path, *, json=None, timeout=None):
        headers = {"Authorization": f"Bearer {credential}"} if credential else {}
        # ⛔ HAI header nội bộ và KHÔNG GÌ KHÁC. Tuyệt đối **không**
        #    `X-Conversation-Id`: cộng đồng cảnh báo rõ (bằng chứng §1) và cổng
        #    máy B cũng không chuyển header nào lên llama-server.
        #    * `X-LTT-Request-Id` — hai máy nối được log, `/v1/huy` có tên để tra;
        #    * `X-LTT-Token-Dat`  — CÙNG số đặt chỗ với lease máy A (O-05), để
        #      rào vật lý của B đếm đúng số A đã đếm (`TOKEN_DAT_TRUOC`).
        if ma_luot:
            headers["X-LTT-Request-Id"] = ma_luot
        dat_cho = int(TOKEN_DAT_TRUOC.get() or 0)
        if dat_cho > 0:
            headers["X-LTT-Token-Dat"] = str(dat_cho)
        try:
            r = client.request(method, base_url.rstrip("/") + path, json=json,
                               headers=headers, timeout=timeout or timeout_s)
        except httpx.HTTPError as e:
            # 🔴 CÙNG NGOẠI LỆ, HAI NGHĨA — và phân loại sai ở đây tốn thật.
            #    `client.close()` giữa một request đang đọc ném đúng lớp ngoại lệ
            #    mà một lần mạng chập ném. Cờ của `huy_luot` là chỗ duy nhất biết
            #    ta có tự đóng hay không. Không hỏi nó thì mọi lượt hủy thành
            #    `AmbiguousProviderError` — không đánh dấu lỗi khoá (may), nhưng
            #    job sẽ bị `mark_ambiguous` và người đọc log đi tìm máy B.
            if ma_luot and huy_luot.da_huy(ma_luot):
                raise HuyError("luot bi huy theo yeu cau") from None
            raise AmbiguousProviderError(
                f"mat ket noi sau khi bat dau gui: {type(e).__name__}") from None
        try:
            return r.status_code, r.json()
        except ValueError:
            return r.status_code, {}

    try:
        return CongVlm(goi=goi, timeout_s=timeout_s).chat(**than)
    finally:
        client.close()


def goi(db, *, messages: list, thu_tu_provider: Sequence[str],
        category: Optional[str] = None, model: Optional[str] = None,
        model_theo_provider: Optional[dict] = None,
        tools: Optional[list] = None, max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        reasoning_effort: Optional[str] = None,
        them: Optional[dict] = None,
        timeout_s: float = TIMEOUT_GOI_MAC_DINH, on_dispatch=None,
        on_rejected=None, ma_luot: str = "") -> KetQuaChat:
    """Gọi model theo **thứ tự provider bên gọi khai**, bỏ qua provider đang bận.

    ⭐ `model_theo_provider` — vì **mỗi provider có id model riêng**. Gửi nhầm tên
       sang provider kia thì nó từ chối, và bên gọi sẽ tưởng provider đó "đang
       hỏng". Khai rõ:

           model_theo_provider={"ltt_llm": "qwen38-api"}

    🔴 VÍ DỤ TRÊN TỪNG GHI `{"ltt_llm": "ltt_llm"}`, VÀ NÓ ĐÃ DẠY SAI HAI NƠI.

       `ltt_llm` là **bí danh công khai** của app, không phải id model. Khoá của
       provider chỉ khai `qwen38-api` / `qwen38-vision`, nên `chon_key` với
       `model="ltt_llm"` **luôn** ném `ThieuKeyError` — và hàm này đọc đó là
       "provider không phục vụ được, đi tiếp", tức **im lặng bỏ qua provider**.

       Hai nơi chép theo ví dụ cũ và cả hai đều hỏng suốt nhiều tháng:
       `platform_core/agent/planner.py` (mọi lượt lập kế hoạch rơi xuống Gemini
       dù khai "model nhà đi trước") và `tools/kiem_ltt_llm.py` (không bao giờ
       xanh nổi, và đỏ về phía báo động). Tìm ra ở Prompt 08, 01/09.

    ⭐ Bài học đáng hơn cả hai lỗi: **một ví dụ trong docstring là mã mà người ta
       chép**. Nó sai thì nó không sai một mình.

    ⛔ Đừng gõ id nội bộ ở bên gọi — hỏi `providers.models_for(...)`. Ngày đổi
       GGUF bên dưới, registry đổi và bên gọi đi theo.

       Thiếu khai cho provider nào thì rơi về `model` chung.

    ⭐ `ma_luot` — MÃ CỦA LƯỢT NÀY, và nó làm hai việc không tách rời được:
       nó đi lên máy B trong `X-LTT-Request-Id` (nối log hai máy), và nó là cái
       **tên** để `huy_luot.huy(ma_luot)` cắt lượt này từ ngoài cây gọi. Rỗng thì
       lượt vẫn chạy bình thường, chỉ là không hủy được theo tên — đường hủy theo
       ngữ cảnh (`ngat`, khách ngắt cửa đồng bộ) vẫn nguyên.

    Ném `KhongCoProviderNao` khi cạn danh sách, `VuotNganSachError` ngay lập tức
    khi yêu cầu quá to (không cascade — nó sẽ quá to ở mọi nơi), `HuyError` ngay
    lập tức khi lượt bị hủy (cũng không cascade — xem dưới).
    """
    from platform_core import api_keys, api_pool, providers
    from platform_core.models import APIKEY_CAT_CHAT

    cat = category or APIKEY_CAT_CHAT
    ban_do = dict(model_theo_provider or {})
    ly_do: list[str] = []

    for pid in thu_tu_provider:
        # ⛔ AI CLEAN REBUILD V2 — CỔNG FAIL-CLOSED, ĐẶT TRƯỚC MỌI THỨ KHÁC.
        #
        #    Provider đã ngừng thì **không bao giờ** tới được `chon_key`, nên
        #    không có đường nào lọt xuống HTTP. Ghi vào `ly_do` để thông điệp
        #    lỗi cuối nói thật ra chuyện gì, thay vì đổ cho "bận".
        #
        # ⚠️ ĐÂY KHÔNG PHẢI `BanError`. "Bận" nghĩa *đi tiếp rồi quay lại sau*;
        #    "đã ngừng" nghĩa *không còn là một đường chạy*. Nếu ai đó về sau
        #    đổi nhánh này thành `BanError` thì đường lui legacy sống lại y
        #    nguyên — chỉ khác cái tên.
        #    ⚠️ Hỏi `providers.da_ngung()` chứ KHÔNG đọc `.is_active` trên vật
        #       thể `get()` trả về: `get()` bị monkeypatch ở nhiều phép kiểm và
        #       trả `SimpleNamespace` không có trường đó. Sự thật về retire nằm
        #       ở `REGISTRY`, nên hỏi đúng chỗ ấy.
        if providers.da_ngung(pid):
            ly_do.append(f"{pid}: da ngung phuc vu (khong phai ban)")
            log.info("provider %s da ngung, bo qua", pid)
            continue

        ten_model = ban_do.get(pid, model) or ""
        try:
            key = api_pool.chon_key(db, category=cat, model=ten_model or None,
                                    thu_tu_provider=[pid])
        except Exception as e:
            ly_do.append(f"{pid}: khong cap duoc key ({type(e).__name__})")
            continue

        prov = providers.get(pid)
        credential = api_keys.lay_credential(db, key)

        # ⭐ `base_url` CỦA KHOÁ ĐI TRƯỚC `base_url` CỦA REGISTRY.
        #
        #    Registry đọc `LTT_LLM_BASE_URL` từ biến môi trường — nó có mặt trong
        #    tiến trình web/worker nhưng **không** có trong một script chạy tay.
        #    Bản ghi khoá thì luôn mang theo địa chỉ, vì `api_keys.tao_key()` có sẵn
        #    trường đó chính để làm việc này.
        #
        #    ⚠️ Đã dính thật 22/08: `dieu_phoi` chỉ đọc registry ⇒ `base_url` rỗng ⇒
        #    HTTP 599 ⇒ `KhongCoProviderNao`, trông y như "máy B chết" trong khi máy
        #    B đang chạy tốt và khoá thì hoàn toàn đúng.
        base = (getattr(key, "base_url", "") or "").strip() \
            or (getattr(prov, "base_url", "") or "").strip()
        try:
            if pid in PROVIDER_OPENAI:
                than = {"model": ten_model, "messages": messages, "tools": tools,
                        "max_tokens": max_tokens, "temperature": temperature,
                        "reasoning_effort": reasoning_effort}
                # ⭐ `them` la duong cho nhung tham so KHAC ma cua cong khai da
                #    kiem xong (`response_format`, `tool_choice`, `top_p`,
                #    `seed`, `stop`, `parallel_tool_calls`). Mot tham so moi chi
                #    can them o MOT cho — `features.kiem_tham_so` — thay vi moc
                #    them mot doi so co ten qua bon tang.
                #
                # ⛔ Day KHONG phai mot truong tu do: moi khoa trong `them` da di
                #    qua `kiem_tham_so`, va `tests/test_1255` chot CO HOC rang
                #    moi khoa khai trong `params_schema` phai song sot qua do.
                #
                # 🔴 `than["them"] = ...`, KHONG PHAI `than.update(them)`.
                #
                #    `_goi_openai` o tren goi `CongVlm(...).chat(**than)` — no
                #    RAI ca `than` thanh doi so co ten. Tron sau khoa moi thang
                #    vao `than` nghia la goi `chat(seed=..., top_p=...)`, ma
                #    `CongVlm.chat` khong co nhung doi so ay:
                #
                #      CongVlm.chat() got an unexpected keyword argument 'seed'
                #
                #    Do la mot loi THAT da len production 14/09 va **moi** tham
                #    so moi deu 503; mot luot khong mang tham so nao van 200,
                #    nen no khong lo ra o bat cu phep kiem nao chi thu duong
                #    mac dinh. `CongVlm.chat` co san doi so `them` cho dung viec
                #    nay (`than_gui.update(them)` ben trong no) — dung cua ay.
                if them:
                    than["them"] = dict(them)
                if not base:
                    # Không có địa chỉ thì đừng gửi đi đâu cả và đừng đánh dấu lỗi
                    # cho khoá — đây là **thiếu cấu hình**, không phải provider hỏng.
                    ly_do.append(f"{pid}: thieu base_url (ca o khoa lan o registry)")
                    continue
                if on_dispatch is not None:
                    on_dispatch(pid)
                kq = _goi_openai(base, credential,
                                 {k: v for k, v in than.items() if v is not None},
                                 timeout_s, ma_luot=ma_luot)
            else:
                ly_do.append(f"{pid}: chua biet giao thuc cua provider nay")
                continue
        except BanError as e:
            if on_rejected is not None:
                on_rejected(pid)
            # ⛔ KHÔNG `danh_dau_loi`. Bận không phải hỏng — xem đầu tệp.
            log.info("provider %s dang ban, di tiep: %s", pid, e)
            ly_do.append(f"{pid}: ban")
            continue
        except VuotNganSachError:
            # ⛔ KHÔNG cascade. Quá to ở đây thì quá to ở mọi nơi.
            raise
        except HuyError:
            # ⛔ KHÔNG cascade, KHÔNG `danh_dau_loi`, KHÔNG `on_rejected`.
            #
            # 🔴 BA CÁI "KHÔNG" ẤY LÀ BA KHUYẾT TẬT KHÁC NHAU, không phải một:
            #
            #    cascade      -> provider này "không phục vụ được" ⇒ thử nơi
            #                    khác. Nhưng lượt đã bị **hủy**: thử lại là chạy
            #                    một lượt không ai chờ, và trả tiền cho nó.
            #                    Với model nội bộ còn tệ hơn — danh sách có MỘT
            #                    phần tử, nên cascade = `KhongCoProviderNao`, một
            #                    thông điệp che mất nguyên nhân thật.
            #    danh_dau_loi -> năm lần là `APIKEY_ERROR` (từ 19/09 có hạn rồi
            #                    thử lại; trước đó **không tự hồi**). Khách bấm
            #                    "dừng" năm lần = tắt model nhà, và mỗi lượt
            #                    dừng kế tiếp tắt lại ngay (D-005, cửa thứ ba).
            #    on_rejected  -> `jobq.mark_provider_rejected` nói *"provider đã
            #                    trả lời dứt khoát là không"*. Provider không hề
            #                    từ chối; chính ta cắt nó. Ghi nhầm ở đây làm
            #                    `_provider_failure_kind` đọc job thành
            #                    `rejected` ⇒ `fail(retry=False)` — tức một job
            #                    bị hủy sẽ mang trạng thái `error`.
            raise
        except AmbiguousProviderError:
            # Timeout sau POST có thể đã tạo side effect. Không cascade và đặc
            # biệt không chạm sổ phạt key: kết quả mơ hồ không chứng minh key hỏng.
            raise
        except YeuCauSaiError:
            # Gửi lại y hệt một yêu cầu sai chỉ tiêu thêm provider; đây cũng
            # không phải tín hiệu sức khỏe của key.
            raise
        except ProviderOomError as e:
            # Không cascade: OOM với nguyên request sẽ lặp lại y hệt ở sản phẩm
            # không cho fallback. Nhưng đây vẫn là tín hiệu sức khỏe provider.
            failure = getattr(e, "failure", None)
            if failure is not None and failure.penalizes_key:
                api_pool.danh_dau_loi(
                    db,
                    key,
                    http_status=failure.http_status,
                    retry_after_s=failure.retry_after_s,
                    message=(
                        f"HTTP {failure.http_status} "
                        f"code={failure.canonical_code}"
                    ),
                )
            raise
        except CongVlmError as e:
            if on_rejected is not None:
                on_rejected(pid)
            # 🔴 TRUYỀN MÃ. Thiếu nó thì `danh_dau_loi` đọc `http_status=None`
            #    thành "5xx hoặc lỗi mạng" ⇒ `error_count += 1` ⇒ năm lần là
            #    `APIKEY_ERROR` (có hạn từ 19/09, nhưng lỗi kế là tắt lại ngay;
            #    trước 19/09 KHÔNG TỰ HỒI). Chính `danh_dau_loi` đã có
            #    nhánh "400 ≤ s < 500: bad request CỦA TA, không phạt" — nhưng
            #    nhánh ấy chỉ chạy khi có người truyền mã vào (L-09).
            failure = getattr(e, "failure", None)
            if failure is None or failure.penalizes_key:
                api_pool.danh_dau_loi(
                    db,
                    key,
                    http_status=(failure.http_status if failure is not None else e.ma),
                    retry_after_s=(failure.retry_after_s if failure is not None else None),
                    message=(
                        f"HTTP {failure.http_status} code={failure.canonical_code}"
                        if failure is not None
                        else str(e)
                    ),
                )
            ly_do.append(f"{pid}: loi ({e})")
            continue
        finally:
            credential = ""

        api_pool.danh_dau_thanh_cong(db, key, tokens=kq.su_dung.token_ra)
        return kq

    raise KhongCoProviderNao(ly_do)

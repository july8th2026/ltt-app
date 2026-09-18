"""``POST /api/v1/messages`` và ``POST /api/v1/responses`` — cửa streaming (Q107).

Hai route, một đường ống. Chúng tồn tại vì **mọi CLI đáng phục vụ đều bắt buộc
streaming**, và mỗi CLI chỉ nói đúng một giao thức:

    /api/v1/messages    Anthropic Messages  <- Claude Code CLI, Claude Desktop
    /api/v1/responses   OpenAI Responses    <- Codex CLI, tiện ích Codex VS Code

⭐ ĐỊA CHỈ KHỚP SẴN, KHÔNG PHẢI THIẾT KẾ RA. Hai CLI ghép đuôi hai kiểu khác nhau,
   và chỗ ta đã mount `/api/v1` từ trước hứng đúng cả hai:

     Codex khai `…/api/v1`  + `/responses`     -> /api/v1/responses
     Claude khai `…/api`    + `/v1/messages`   -> /api/v1/messages

   Nên không cần tên miền mới, không cần proxy thứ hai.

⛔ CỔNG NÀY LÀ ỐNG, KHÔNG PHẢI BỘ DỊCH. Nó kiểm, giữ tiền, rồi **chuyển byte
   nguyên xi**. Việc dịch Responses ⇄ Chat là của `llama-server` ở máy B; việc
   nhìn qua để đếm token là của `dem_token_luong`, và nó cũng chỉ **nhìn**.

⛔ KHÔNG ĐÒI `Idempotency-Key` (Q107). Đo thật 23/08: **không CLI nào gửi nó**.
   Thứ giữ tiền thay nó là **thu theo token đã thật sự sinh ra** — khách ngắt
   giữa chừng thì trả phần đã sinh, không trả trọn phần đã giữ.
"""
from __future__ import annotations

import logging
import time
from typing import Iterator, Optional

import anyio
from fastapi import Body, Depends, Request
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, Response, StreamingResponse
from sqlalchemy.orm import Session

from platform_core.public_api import examples, limits, metrics, policy, sandbox
from platform_core.public_api.catalog import build_catalog, require_tool
from platform_core.public_api.executor import for_tool, for_tool_name
from platform_core.public_api.errors import (THIEU_CREDIT_LOI,
                                             insufficient_credit,
                                             invalid_request,
                                             model_not_found,
                                             service_unavailable,
                                             thieu_credit_chi_tiet,
                                             tran_bi_vuot)
from platform_core.public_api.principal import Principal
from platform_core.public_api.protocol import (STREAM, PublicOperationContract)
from platform_core.public_api.scopes import SCOPE_JOBS_CREATE
from server.api import su_kien_loi, tool_dich
from server.api.auth import require_scope
from server.deps import get_db
from apps.ltt_llm import ngan_sach
from platform_core.runtime_noi_bo import luong as cua_luong

log = logging.getLogger("server.api.streaming")

_SSE = {"Cache-Control": "no-store", "X-Accel-Buffering": "no"}
#: Khách gửi effort cho model chỉ có một chế độ (3.5) — đã nhận và bỏ qua (L-26).
HEADER_EFFORT_BO_QUA = "X-LTT-Effort-Bo-Qua"
_NO_STORE = {"Cache-Control": "no-store"}
TOOL_CHAT = "text.chat"

#: Tên tuyến **tương thích**, chỉ tồn tại vì một ràng buộc phía CLIENT.
#:
#: 🔴 VÌ SAO CÓ MỤC NÀY. Claude Desktop ở chế độ `gateway` **lọc danh sách model
#:    trước khi hiện picker**. Luật đọc được từ chính bản cài (1.34493.1.0, tệp
#:    `ce459c687-CEBp0mVy.js`):
#:
#:        Be = /…|gpt|gemini|glm|llama|minimax|mistral|qwen|…/     # CẤM
#:        qe = ["claude", …tên dòng Claude…, "anthropic"]          # PHẢI chứa
#:        Ke(t) = !Be.test(t) && (Ne.test(t) || qe.some(s => t.includes(s)))
#:
#: ⛔ HẬU QUẢ ĐO ĐƯỢC 24/08: `ltt_llm` không chứa chuỗi nào trong `qe` ⇒ bị **lọc
#:    khỏi mảng** ⇒ picker rỗng ⇒ **nút gửi vô hiệu, không một lời báo lỗi nào**.
#:    Cả Enter lẫn bấm nút đều im lặng: không log, không toast, không banner. Mất
#:    một buổi mới tìm ra, vì triệu chứng không hề chỉ về phía nguyên nhân.
#:    (`qwen` còn nằm trong danh sách CẤM, nên tên trung thực nhất cũng bị chặn.)
#:
#: ⭐ VÌ SAO TÊN NÀY CHỨ KHÔNG PHẢI `claude-sonnet-4-5`. Luật chỉ đòi tên **chứa**
#:    chuỗi `claude`; nó **không** đòi một model Anthropic có thật. Nên ta qua
#:    được cổng mà **không** mượn tên sản phẩm của hãng khác. Đây là **tên tuyến**
#:    của một cổng tương thích, không phải tên sản phẩm: catalog, bảng giá và
#:    `/api/v1/tools` vẫn chỉ nói `ltt_llm`, và model đứng sau vẫn là model nhà.
#:
#: ⚠️ ĐỪNG đưa tên này vào `features.ALIAS_SANG_ID`. Chỗ đó là **từ vựng sản phẩm**
#:    của app; mục này là **chi tiết giao thức của một client**. Trộn hai thứ là
#:    cách một hằng số tạm bợ trở thành thứ ta phải đỡ mãi mãi.
#: 🔴 ĐÍCH ĐỔI 11/09/2026 (D02): `ltt_llm` → `ltt-3.8`. **KHOÁ giữ nguyên** — nó
#:    là tên tuyến của giao thức, thứ Claude Desktop lọc theo chuỗi `claude`;
#:    đổi nó là đóng cửa với một client đang chạy, và `test_290` ghim đúng ranh
#:    giới ấy. Thứ bị cắt là *bí danh sản phẩm* ở vế phải.
#:
#: 🔑 12/09/2026 — BẢNG NÀY KHÔNG CÒN ĐỊNH NGHĨA Ở ĐÂY. Nguồn duy nhất là
#:    `examples.TUYEN_DESKTOP`, và việc đó sửa một khuyết tật đang mở chứ không
#:    phải dọn cho gọn: cùng một bảng từng được gõ hai lần — một bản ở đây để
#:    **giải tên**, một bản ở `examples.py` để **in ra trang hướng dẫn**. Hai bản
#:    ấy lệch nhau là khách chép đúng thứ trang dạy rồi nhận `model_not_found`,
#:    và không phép kiểm nào thấy gì sai vì mỗi bên tự nhất quán.
#:
#: ⭐ Chiều import đúng là chiều này: `platform_core` không được biết gì về
#:    `server`, còn `server` vốn đã đọc `platform_core.public_api`. Và tên tuyến
#:    là **từ vựng khách nhìn thấy**, nên nó thuộc về mô-đun bề mặt công khai.
#:
#: 📈 Từ 12/09 bảng có HAI mục: `ltt-3.5` trước đó không có cửa nào trên Claude
#:    Desktop — tên duy nhất qua được bộ lọc picker đều dẫn về `ltt-3.8`.
TUYEN_TUONG_THICH = dict(examples.TUYEN_DESKTOP)


def _giai_ten_model(ten: str) -> str:
    """Tên tuyến tương thích → alias thật. Tên khác giữ nguyên để lỗi ở chỗ cũ."""
    return TUYEN_TUONG_THICH.get(ten, ten)

#: 🔴 NGÂN SÁCH MỞ LUỒNG — 75 giây, và con số này có lý do.
#:
#:    Nó nằm **dưới** trần mặc định 125 giây của Cloudflare, nên khi máy B chậm quá thì
#:    **ta** trả 503 chứ không để Cloudflare trả 524. Một cái 503 của ta client
#:    đọc được; một cái 524 của Cloudflare thì không phân biệt được "hỏng" với
#:    "xong rồi nhưng mất kết nối".
#:
#:    Đủ rộng cho ca xấu đã đo: `llama-swap` nạp lại model ~25 giây.
#:
#: ⛔ NỚI SỐ NÀY KHÔNG MUA THÊM THỜI GIAN. Nó chỉ đổi 503 của ta lấy 524 của
#:    Cloudflare. Nạp từ đĩa lạnh lâu hơn thì giảm nhẹ bằng `ttl` của llama-swap
#:    (giữ model thường trú), không bằng đồng hồ này.
MO_LUONG_GIAY = cua_luong.MO_LUONG_GIAY   # 75.0 — một hằng, một chỗ

#: ⛔ TOKEN RA MẶC ĐỊNH KHÔNG CÒN Ở ĐÂY.
#:
#:    Nguồn chân lý là `apps/ltt_llm/ngan_sach.py`; gọi `mac_dinh_cho("stream")`.
#:    Trước 30/08 con số này nằm rải ba nơi với ba giá trị (4.096 / 1.024 / 8.192)
#:    và cửa stream lấy nhầm 1.024 của cửa đồng bộ — mọi câu trả lời dài cụt ở
#:    đúng 1.024 token, im lặng. Xem `docs/VLM_NOI_BO/RA_SOAT_THAM_SO_LTT_LLM.md`.


def _tran_giay() -> int:
    """Trần thời gian cho đường **không streaming**.

    Dùng lại đúng con số của `/chat/completions`: không stream nghĩa là không
    byte nào chảy cho tới khi xong, nên đồng hồ 125 giây của Cloudflare có hiệu
    lực ở cả hai chỗ, và vì cùng một lý do.
    """
    from server.api.chat import SYNC_BILLED_MAX_SECONDS
    return int(SYNC_BILLED_MAX_SECONDS)

#: Hợp đồng của hai route này, **khai ra để bộ kiểm chạy được**.
#:
#: ⭐ Dựng ở cấp module có chủ ý: `check_mode_rules` chạy ngay lúc nạp app, nên
#:    một bản sau lỡ bỏ mất một lời hứa của `STREAM` sẽ làm **app không khởi
#:    động được**, thay vì lặng lẽ phục vụ sai. Trước hôm nay
#:    `PublicOperationContract` chỉ được dựng trong test — hợp đồng có bộ kiểm mà
#:    bộ kiểm không bao giờ chạy trên đường thật.
HOP_DONG = PublicOperationContract(
    name="chat.stream",
    execution_mode=STREAM,
    chargeable=True,
    requires_quote=False,
    requires_idempotency_key=False,          # Q107
    scopes=(SCOPE_JOBS_CREATE,),
    extra={
        "event_types": ("message_start", "content_block_start",
                        "content_block_delta", "content_block_stop",
                        "message_delta", "message_stop",
                        "response.created", "response.output_text.delta",
                        "response.completed"),
        "heartbeat_seconds": 15,
        "usage_event": "message_delta | response.completed",
        "cancel_on_disconnect": True,
        "settles_from_measured_usage": True,
    },
)


def register_streaming_routes(api, config, tag: str) -> None:
    @api.post("/messages", tags=[tag],
              summary="Chat completion as an Anthropic Messages stream",
              description=(
                  "Anthropic Messages API over SSE, for Claude Code and Claude "
                  "Desktop. Point ANTHROPIC_BASE_URL at the /api parent of this "
                  "route. Requires \"stream\": true. Credit is held at a ceiling "
                  "and settled from the tokens actually produced."))
    def messages(request: Request, body: dict = Body(...),
                 principal: Principal = Depends(require_scope(SCOPE_JOBS_CREATE)),
                 db: Session = Depends(get_db)) -> Response:
        return _cua("/v1/messages", body or {}, principal, db, config, request)

    @api.post("/responses", tags=[tag],
              summary="Chat completion as an OpenAI Responses stream",
              description=(
                  "OpenAI Responses API over SSE, for the Codex CLI and its VS "
                  "Code extension. Set base_url to this route's parent and "
                  "wire_api = \"responses\". Requires \"stream\": true."))
    def responses(request: Request, body: dict = Body(...),
                  principal: Principal = Depends(require_scope(SCOPE_JOBS_CREATE)),
                  db: Session = Depends(get_db)) -> Response:
        return _cua("/v1/responses", body or {}, principal, db, config, request)


def _mot_cuc(duong: str, than: dict, tin: list, ten: str,
             principal: Principal, db: Session, config, tool=None,
             trang_thai=None, request=None) -> JSONResponse:
    """Tra loi **mot cuc** cho `/messages` va `/responses`, dung hinh dang
    Anthropic Messages.

    ⭐ DUNG LAI TOAN BO DUONG TINH TIEN da co (`giu_cho_luot` -> goi ->
       `quyet_toan_hoac_hoan`). Khong dung mot so tien thu hai o day: mot he
       thong hai cho tinh tien la mot he thong se lech, va lech ve tien thi khong
       ai phat hien cho toi khi khach doi soat.

    ⚠️ TRAN THOI GIAN. Khong stream nghia la khong co byte nao chay cho toi khi
       xong, nen dong ho 125 giay cua Cloudflare **co hieu luc** o day - khac han
       duong streaming. Vi vay `max_tokens` bi kep theo tran cua duong dong bo,
       cung con so ma `/chat/completions` dung, va vi cung mot ly do.
    """
    from platform_core import credit
    from platform_core.llm import admission, ngat, phong_cho, thanh_toan
    from platform_core.llm.cong_vlm import (BanError, CongVlmError, HuyError,
                                            SuDung, VuotNganSachError)
    from platform_core.runtime_noi_bo import luong as cua_luong
    from server.api.chat import (MA_KHACH_NGAT, _DA_HUY, _KHACH_NGAT, _con_lai_s,
                                 _tran_max_tokens)

    executor = for_tool(tool) if tool is not None else for_tool_name(TOOL_CHAT)

    if sandbox.is_test(principal.mode):
        return JSONResponse(_thu_mot_cuc(ten), status_code=200, headers=_NO_STORE)

    vao_uoc = executor.estimate_input(tin)
    # 🔴 "Quá dài" TRƯỚC mọi lỗi khác (spec §6, như `/chat/completions`): lời
    #    khuyên "giảm max_tokens / dùng stream" vô nghĩa với một hội thoại mà
    #    model không nhận nổi — và chỉ câu "prompt is too long" làm client tự nén.
    tran_vao = _tran_vao_cua_model(ten)
    if vao_uoc > tran_vao:
        return su_kien_loi.loi_qua_dai_json(duong, token=int(vao_uoc),
                                            tran=tran_vao, request=request)
    xin_ra = _max_tokens(than, vao_uoc)
    if not any(ten in than for ten in ("max_tokens", "max_output_tokens")):
        xin_ra = min(xin_ra, executor.mac_dinh_cho("sync"))
    tran = _tran_max_tokens(vao_uoc)
    if xin_ra > tran:
        raise invalid_request(
            f"This non-streaming request is estimated at {vao_uoc} input tokens, "
            f"leaving room for at most {tran} output tokens inside its "
            f"{_tran_giay()}s budget. Reduce the prompt or max_tokens, set "
            f"stream=true, or submit it to POST /api/v1/jobs.")
    # ── Sức chứa admission CỦA ĐÚNG MODEL NÀY (multijob 2.2) ────────────────
    #
    # 🔴 `ten` là bí danh khách xin, và từ 2.2 nó quyết định **pool nào**:
    #    `text.chat` phục vụ hai model trên hai pool KV khác nhau, nên bộ ba
    #    tĩnh của tool không còn tả nổi sức chứa. Phép đọc thuần, đặt trước mọi
    #    thứ chạm tiền — thứ tự cửa không đổi.
    try:
        suc = tool.admission_cho(ten) if tool is not None else None
    except KeyError as e:
        # Cùng mã với tên đã cắt ở `_cua` — D02, Step 2c.
        log.error("ban khai admission thieu model %r: %s", ten, e)
        raise _bao_400(
            f"`model` {ten!r} is not served here. Call GET /api/v1/models for "
            f"the names in service.", than, dung=model_not_found) from None
    tai_nguyen = str(suc.resource or "") if suc else ""
    pool = int(suc.token_pool or 0) if suc else 0

    request_id = thanh_toan.ma_luot("ms")
    # 🔴 ĐỒNG HỒ NGÂN SÁCH CỦA CỬA BẮT ĐẦU Ở ĐÂY, trước phòng chờ. Đặt mốc sau
    #    khi chờ xong là để một lượt chờ 60 giây rồi chạy thêm 90 giây nữa —
    #    150 giây, tức đúng cái 524 của Cloudflare mà trần này sinh ra để chặn.
    t0 = time.monotonic()

    # 🔴 402 TRƯỚC KHI XẾP HÀNG, và chỉ ĐỌC số dư. Cùng lý do với `/chat/
    #    completions`: một lượt đang chờ **không được** có dòng giữ tiền nào
    #    (INV-MJ-1), nên số dư phải kiểm được mà không giữ.
    if not thanh_toan.du_so_du(db, user_id=principal.user_id,
                               token_vao_uoc=vao_uoc, max_tokens=xin_ra,
                               model=ten):
        metrics.increment(metrics.CREDIT_EXHAUSTED)
        raise insufficient_credit(
            THIEU_CREDIT_LOI)

    # 🔴 CHỐT GIAO DỊCH CỦA REQUEST TRƯỚC KHI CHỜ (D04). Phòng chờ ghi dòng của
    #    nó ở một phiên MỚI; để giao dịch này còn mở là SQLite "database is
    #    locked", và trên PostgreSQL là giữ khoá hàng suốt lúc chờ.
    db.commit()

    try:
        suat = cua_luong.cho_suat_dong_bo(
            suc=suc,
            user_id=principal.user_id, request_id=request_id, cua="sync",
            token_vao_uoc=int(vao_uoc), xin_ra=int(xin_ra),
            so_anh=cua_luong.dem_anh(than),
            han_s=cua_luong.han_cho_dong_bo(
                ngan_sach_s=float(_tran_giay()),
                da_tieu_s=time.monotonic() - t0),
            # Id model **nội bộ** cho sổ lượt (dual-model 6.3). ⛔ Không ghi bí
            # danh khách: bí danh đổi được mà engine không đổi.
            model=cua_luong.id_model_noi_bo(executor, ten),
            ngat_chua=ngat.do_ngat(request))
    except phong_cho.HetCho as e:
        # Hết trần chờ: 0 khoản giữ (INV-MJ-2), 0 bút toán mồ côi.
        metrics.increment(metrics.CAPACITY_REFUSED)
        log.warning("HET CHO mot-cuc user=%s ly_do=%s",
                    principal.user_id[:8], e.ly_do)
        # `het_cho` la mot nguon BAN khac han `suat`: hang cho cua TA day, chu
        # khong phai GPU het suat. Cung ma HTTP, hai nguyen nhan.
        raise limits.execution_busy(
            tai_nguyen, retry_after=10, reason="het_cho") from None
    except phong_cho.KhachDi:
        return JSONResponse(_KHACH_NGAT, status_code=MA_KHACH_NGAT,
                            headers=_NO_STORE)
    except cua_luong.KhongMoDuoc as e:
        # Đặt chỗ vượt cả pool KV (phương án C bất biến 1) — quá dài, 0 khoản giữ.
        return su_kien_loi.loi_qua_dai_json(
            duong, token=e.token, tran=e.tran if e.tran is not None else pool,
            request=request)

    def _release_ticket(ket_qua: str = "loi") -> None:
        """Nhả suất + ghi KẾT CỤC THẬT vào sổ lượt 30 ngày.

        ⛔ Bản đầu ghi cứng `"xong"` ở mọi đường ra — kể cả bận, lỗi và khách
           ngắt. Một cuốn sổ chỉ biết nói một chữ không phân tích được gì, mà
           nó tồn tại chính để phân tích (chủ dự án 11/09).
        """
        if suat.lease_id:
            admission.release_by_id(suat.lease_id)
        if suat.waiter_id:
            phong_cho.ghi_ket_thuc(suat.waiter_id, ket_qua)

    # ── Được nhận ⇒ GIỮ TIỀN (và chỉ từ đây trở đi) ─────────────────────────
    try:
        da_giu = thanh_toan.giu_cho_luot(
            db, user_id=principal.user_id, request_id=request_id,
            token_vao_uoc=vao_uoc, max_tokens=xin_ra, model=ten)
    except credit.ThieuCreditError as e:
        db.rollback()
        _release_ticket("thieu_credit")
        raise insufficient_credit(
            THIEU_CREDIT_LOI, **thieu_credit_chi_tiet(e)) from None
    except BaseException:
        db.rollback()
        _release_ticket("loi")
        raise
    db.commit()

    # 🔴 LƯỚI AN TOÀN CHO TIỀN — VÀ NÓ ĐÃ PHẢI TRẢ GIÁ MỘT LẦN.
    #
    #    Bản đầu chỉ hoàn tiền cho **ba** loại ngoại lệ có tên. Mọi ngoại lệ khác
    #    thoát thẳng ra ngoài, thành `500` — và **để nguyên tiền trong hold**.
    #
    # ⛔ ĐO ĐƯỢC 25/08, tiền thật của khách: Claude Desktop gọi một lượt, ta ném
    #    một ngoại lệ không có trong danh sách, và sổ credit còn lại đúng một
    #    dòng mồ côi: `23:58:10  -1  hold  ms:84e9b…` — **không settle, không
    #    hoàn**. Đường đồng bộ này KHÔNG có Job row, nên `_hoan_credit` của
    #    worker không bao giờ chạm tới nó. Không ai quét. Khách mất tiền im lặng.
    #
    # ⭐ Nên cờ dưới đây đo đúng một điều: **tiền đã được định đoạt chưa** (quyết
    #    toán HOẶC hoàn). Đừng đổi nó thành "đã hoàn chưa" — hai nhánh except bên
    #    trong đã hoàn rồi mới ném tiếp, và hoàn lần hai là trả tiền thừa.
    try:
        # 🔴 ĐI ĐƯỜNG CHUNG, ĐỪNG TỰ DỰNG CLIENT.
        #
        #    Bản đầu gọi thẳng `CongVlm().chat(...)` và **500 ngay lượt đầu**:
        #    `CongVlm.__init__` đòi một tham số `goi`, nó không phải constructor
        #    rỗng. Nhưng lỗi cú pháp đó chỉ là triệu chứng.
        #
        # ⛔ Cái sai thật là **đi vòng qua `dieu_phoi`** — thứ mà chính tài liệu
        #    của nó gọi là *"MỘT đường gọi model ngôn ngữ cho toàn nền tảng"*.
        #    Đi vòng là mất: chọn khoá theo pool, bỏ qua provider đang bận, ánh
        #    xạ tên model theo từng provider, và cách đếm token thống nhất.
        #    Một client dựng tay sẽ **chạy được** trong ca sạch rồi lệch dần ở
        #    đúng những ca mà `dieu_phoi` sinh ra để xử.
        #
        #    `features.chay` là đúng cửa mà `/chat/completions` đã dùng.
        # ⚠️ `_tin_that`, KHÔNG phải `tin`. `tin` là danh sách **ước token** và
        #    các phần tử của nó cố ý không có `role` — xem `_tin_that`.
        #
        # ⭐ Rồi dịch sang giao thức OpenAI: máy B nói OpenAI, khách nói Anthropic.
        #    `sang_openai_messages` là thứ giữ được **vòng gọi tool** — khối
        #    `tool_use` thành `tool_calls`, khối `tool_result` thành các tin
        #    `role="tool"` riêng, đúng thứ tự.
        sach = {"model": ten, "max_tokens": xin_ra,
                "messages": tool_dich.sang_openai_messages(_tin_that(than))}
        # Effort đã chuẩn hoá ở `_cua` (L-26): cửa một cục giữ đúng mức khách chọn.
        _muc = than.get("reasoning_effort") or (
            (than.get("reasoning") or {}).get("effort")
            if isinstance(than.get("reasoning"), dict) else None)
        if _muc:
            sach["reasoning_effort"] = _muc
        cong_cu = tool_dich.sang_openai_tools(than.get("tools"))
        if cong_cu:
            sach["tools"] = cong_cu
        # ⭐ Spec §16: thăm `is_disconnected` ~1 s song song với lời gọi. Không
        #    stream nghĩa là không byte nào chảy, nên đây là cách DUY NHẤT biết
        #    khách đã đi trước khi GPU chạy trọn một lượt không ai đọc.
        # ⛔ NGÂN SÁCH **CÒN LẠI**, không phải trần nguyên. `t0` chạy từ trước
        #    phòng chờ, nên thời gian đã chờ bị trừ đi ở đây — hai chỗ (trần chờ
        #    và trần gọi) phải cùng ăn MỘT ngân sách, nếu không chúng chia nhau
        #    một ngân sách tưởng tượng và tổng vượt đồng hồ Cloudflare.
        # ⭐ Máy B 429 cho lượt đã nhận ⇒ xếp lại trong phần còn lại của ngân
        #    sách cửa (phương án C bước 1); mỗi lần gọi mang `X-LTT-Token-Dat`.
        #    `_release_ticket` đọc `suat.lease_id` lúc nhả ⇒ nhả đúng suất mới.
        kq = cua_luong.goi_dong_bo_co_xep_lai(
            lambda: ngat.chay_canh_ngat(
                lambda: executor.run(db, sach,
                                     timeout_s=_con_lai_s(t0, float(_tran_giay()))),
                ngat_chua=ngat.do_ngat(request)),
            suat,
            han_s=lambda: cua_luong.han_cho_dong_bo(
                ngan_sach_s=float(_tran_giay()), da_tieu_s=time.monotonic() - t0),
            ngat_chua=ngat.do_ngat(request))
    except ngat.KhachNgat as e:
        # Quyết toán theo `usage` nếu lời gọi kịp về; không thì hoàn trọn.
        if e.ket_qua is not None:
            thanh_toan.quyet_toan_hoac_hoan(
                db, user_id=principal.user_id, request_id=request_id,
                su_dung=SuDung(token_vao=e.ket_qua.token_vao,
                               token_ra=e.ket_qua.token_ra,
                               token_vao_cache=e.ket_qua.token_vao_cache,
                               dang_tin=e.ket_qua.do_duoc),
                model=ten)
        else:
            thanh_toan.hoan_luot(db, user_id=principal.user_id,
                                 request_id=request_id)
        db.commit()
        _release_ticket("khach_ngat")
        return JSONResponse(_KHACH_NGAT, status_code=MA_KHACH_NGAT,
                            headers=_NO_STORE)
    except executor.parameter_error as e:
        # Tham số sai là lỗi của **yêu cầu**, không phải của máy chủ: 400, không
        # phải 500. Hoàn tiền trước, vì hold đã đặt rồi.
        thanh_toan.hoan_luot(db, user_id=principal.user_id, request_id=request_id)
        db.commit()
        _release_ticket("tham_so_sai")
        raise invalid_request(str(e)) from None
    except BanError as e:
        thanh_toan.hoan_luot(db, user_id=principal.user_id, request_id=request_id)
        db.commit()
        _release_ticket("ban")
        # ⛔ BAN != HONG (D-005). 429/503 + Retry-After, va khach KHONG bi thu tien.
        # 🔴 ĐẾM VÀO `CAPACITY_REFUSED`, KHÔNG CHỈ ĐỂ NÓ RƠI VÀO 5xx.
        #
        #    `metrics.py` đã tách hai thứ này từ đầu: 5xx là "nền tảng hỏng",
        #    còn thiếu năng lực phía sau là "mất doanh thu" — khác nguyên nhân,
        #    khác cách sửa, nên khác ngưỡng cảnh báo. Nhưng bộ đếm năng lực chỉ
        #    được nuôi ở cửa job; ba nhánh bận đồng bộ/stream không nuôi gì.
        #
        # ⛔ Hệ quả đo 31/08: suốt một đợt bận kéo hơn năm giờ, thư gửi người
        #    trực nói `responses_5xx` — tức "nền tảng hỏng" — trong khi nền tảng
        #    làm đúng và thứ hết là năng lực máy B. Chẩn đoán sai ngay từ dòng
        #    tiêu đề, và `CAPACITY_REFUSED` đứng im ở 0 suốt sự cố.
        metrics.increment(metrics.CAPACITY_REFUSED)
        log.warning("BAN mot-cuc: user=%s duong=%s ly_do=%s",
                    principal.user_id[:8], duong, e)
        # 🔴 Chỗ rò THỨ TƯ, và không phép quét thủ công nào của tôi thấy nó —
        #    `test_than_tra_ve_KHONG_mang_chu_thuong_nguon` mới lôi ra, vì nó
        #    hỏi **quan hệ** (biểu thức nào của ngoại lệ chảy vào đối số đầu
        #    của hàm dựng lỗi) chứ không hỏi **nhãn** (câu này trông có nhạy
        #    cảm không). `ly_do=%s` ở dòng trên đã giữ đủ cho người trực.
        raise service_unavailable("The model is busy right now.",
                                  retry_after=getattr(e, "thu_lai_sau_s", 30)) from None
    except VuotNganSachError as e:
        # 🔴 TACH KHOI `CongVlmError` — hai loi nay KHAC LOAI, va gop chung la
        #    noi doi voi khach hai lan cung luc.
        #
        #    Ban cu tra **503 "The model could not serve this request."** cho
        #    ca hai. Voi `VuotNganSachError` thi ca hai nua deu sai:
        #
        #      · 503 noi "may dang ban, thu lai sau" — nhung yeu cau nay QUA
        #        LON, va thu lai mot nghin lan cung hong. Khach dot thoi gian
        #        cua ho va GPU cua ta vao mot vong lap khong bao gio thanh cong.
        #      · thong diep khong noi TRAN NAO bi vuot, tran BAO NHIEU, hay
        #        truong NAO — trong khi cong may B da gui du ca ba.
        #
        # ⇒ Day la **400**, `retry: never`, kem `field`/`limit`/`actual`.
        thanh_toan.hoan_luot(db, user_id=principal.user_id, request_id=request_id)
        db.commit()
        _release_ticket("tham_so_sai")
        log.info("mot cuc: yeu cau vuot tran user=%s: %s",
                 principal.user_id[:8], e)
        raise invalid_request(str(e),
                              **tran_bi_vuot(getattr(e, "chi_tiet", None))) from None
    except HuyError:
        # ⛔ TRUOC `CongVlmError`: `HuyError` khong ke thua no (co chu y), nen
        #    truoc 14/09 no thoat ra thanh 500. Huy khong phai loi cua ai.
        thanh_toan.hoan_luot(db, user_id=principal.user_id, request_id=request_id)
        db.commit()
        _release_ticket("huy")
        return JSONResponse(_DA_HUY, status_code=MA_KHACH_NGAT,
                            headers=_NO_STORE)
    except CongVlmError as e:
        thanh_toan.hoan_luot(db, user_id=principal.user_id, request_id=request_id)
        db.commit()
        _release_ticket("loi")
        log.warning("mot cuc that bai user=%s: %s", principal.user_id[:8], e)
        raise service_unavailable("The model could not serve this request.") from None
    except BaseException:
        # ⛔ ĐO ĐƯỢC 25/08, TIỀN THẬT CỦA KHÁCH. Ba nhánh trên chỉ bắt ngoại lệ
        #    **có tên**. Một ngoại lệ ngoài danh sách thoát thẳng ra thành `500`
        #    và **để nguyên tiền trong hold**: sổ credit còn đúng một dòng mồ côi
        #    `23:58:10  -1  hold  ms:84e9b…` — không quyết toán, không hoàn.
        #
        # ⚠️ Và KHÔNG AI QUÉT NÓ. Đường đồng bộ này không tạo `Job`, nên
        #    `_hoan_credit` của worker không bao giờ nhìn thấy. Khách mất tiền
        #    lặng lẽ, và không có báo cáo nào chỉ ra điều đó.
        #
        # ⭐ Vì sao `BaseException` chứ không phải `Exception`: khách ngắt kết nối
        #    giữa chừng có thể tới dưới dạng `CancelledError` — thứ **không** kế
        #    thừa `Exception`. Đó chính là ca hay xảy ra nhất ở một cửa đồng bộ.
        thanh_toan.hoan_luot(db, user_id=principal.user_id, request_id=request_id)
        db.commit()
        _release_ticket("loi")
        raise

    # `quyet_toan_hoac_hoan` nhan chinh doi tuong `SuDung` do cong tra ve - dung
    # tu boc token roi truyen so le: chinh no biet cach xu khi KHONG DO DUOC
    # (hoan du va ghi canh bao), va do la luat tien cua ca he thong.
    # ⚠️ `features.chay` tra ve `KetQua` cua app (token phang), khong phai
    #    `KetQuaChat` cua cong (co `.su_dung`). Boc y het `/chat/completions`,
    #    ke ca `dang_tin=kq.do_duoc` - do la co bao "co do duoc token khong", va
    #    `quyet_toan_hoac_hoan` dua vao no de HOAN DU khi khong do duoc.
    try:
        _thu = thanh_toan.quyet_toan_hoac_hoan(
            db, user_id=principal.user_id, request_id=request_id,
            su_dung=SuDung(token_vao=kq.token_vao, token_ra=kq.token_ra,
                           token_vao_cache=kq.token_vao_cache,
                           dang_tin=kq.do_duoc),
            model=ten)
        # ⛔ P08 F-01, NHANH KHONG-STREAM. Ban va dau chi cham `_quyet_toan` cua
        #    generator, nen cua nay van ghi `+0` — va do that tren production
        #    ngay sau khi deploy bat duoc: cung mot route `/api/v1/messages`,
        #    luot stream ghi `credit=-3` con luot mot-cuc ghi `+0`.
        #
        # ⭐ Dang nho: mot route, HAI duong tien. Sua mot duong roi doc dong log
        #    dau tien thay so dung la du de tin rang xong.
        if trang_thai is not None:
            trang_thai.api_credit_delta = -int(_thu.thu_credit)
    except BaseException:
        # Cùng một lý do với lưới ở trên: hold đã đặt rồi, nên đường thoát nào
        # cũng phải trả nó lại. Hỏng ở bước quyết toán mà bỏ chạy thì tiền kẹt.
        db.rollback()
        thanh_toan.hoan_luot(db, user_id=principal.user_id, request_id=request_id)
        db.commit()
        _release_ticket("loi")
        raise
    db.commit()
    _release_ticket("xong")
    metrics.increment("chat:mot_cuc")
    return JSONResponse(_dang_anthropic(kq, ten, request_id),
                        status_code=200, headers=_NO_STORE)


#: Ánh xạ lý do dừng: **kiểu OpenAI → kiểu Anthropic**.
#:
#: 🔴 KHÔNG ĐƯỢC TRUYỀN THẲNG. Máy B nói giao thức OpenAI nên trả `stop` /
#:    `length` / `tool_calls`; hợp đồng Anthropic Messages khai một tập **khác
#:    hẳn**: `end_turn`, `max_tokens`, `stop_sequence`, `tool_use`, `pause_turn`,
#:    `refusal`.
#:
#: ⛔ Bản đầu của tôi viết `kq.finish_reason or "end_turn"` — tức đưa thẳng chữ
#:    `stop` của OpenAI vào một trường mà client Anthropic đọc theo bảng trên.
#:    Client không vỡ ngay: nó chỉ **không nhận ra** giá trị, rồi xử lý sai ở chỗ
#:    quan trọng nhất — `length` (bị cắt vì hết token) trông y hệt một câu trả
#:    lời hoàn chỉnh, nên client sẽ không biết mà xin tiếp.
LY_DO_DUNG = {
    "stop": "end_turn",
    "length": "max_tokens",
    "tool_calls": "tool_use",
    "content_filter": "refusal",
}


def _dang_anthropic(kq, ten: str, request_id: str) -> dict:
    """Bọc kết quả thành hình dạng `message` của Anthropic Messages API.

    Trường bắt buộc, theo tài liệu chính thức: `id`, `type`, `role`, `model`,
    `content`, `stop_reason`, `stop_sequence`, `usage`.

    ⛔ `model` trả về là **alias của khách** (`ltt_llm`), không phải id nội bộ của
       máy B. Khách không bao giờ được nhìn thấy `qwen38-*` — `test_212` chốt.

    ⚠️ `stop_details` phải **có mặt và bằng `null`** khi không phải từ chối. Tài
       liệu nói nó chỉ được điền khi `stop_reason == "refusal"`, nhưng client đọc
       nó vô điều kiện; thiếu khoá và có khoá `null` là hai chuyện khác nhau với
       một bộ giải mã chặt.
    """
    ly_do = LY_DO_DUNG.get(kq.finish_reason or "", "end_turn")

    khoi = tool_dich.sang_anthropic_content(kq.noi_dung,
                                            getattr(kq, "tool_calls", ()))

    # 🔴 KHÔNG ĐƯỢC KHAI `tool_use` KHI KHÔNG CÓ KHỐI `tool_use` NÀO.
    #
    #    Hợp đồng Anthropic: `stop_reason: "tool_use"` là lời hứa rằng trong
    #    `content` có ít nhất một khối `{"type": "tool_use", …}`. Client đọc
    #    `stop_reason`, đi tìm khối đó để chạy tool — không thấy thì nó **treo**,
    #    chứ không báo lỗi.
    #
    # ✏️ CHÚ THÍCH CŨ Ở ĐÂY ĐÃ TRÔI. Nó viết *"`_mot_cuc` không truyền `tools`
    #    lên model, nên model không có gì để gọi"*. Việc dịch hai chiều **đã
    #    làm xong** từ lúc nào đó và chú thích không theo kịp.
    #
    #    Đo thật 01/09 qua Cloudflare, vòng khép kín:
    #        tool_use    -> tra_ton_kho {"ma_hang":"ABC-123"}
    #        tool_result -> "Ma hang ABC-123 hien co 42 cai trong kho."
    #    Con số 42 chỉ nói ra được nếu model thật sự đọc `tool_result`.
    #
    # ⭐ Cho tới lúc đó, thà nói `end_turn` còn hơn hứa một thứ không có. Một câu
    #    trả lời thiếu tool là chuyện khách thấy ngay; một client treo thì không.
    if ly_do == "tool_use" and not any(k.get("type") == "tool_use" for k in khoi):
        log.warning("upstream bao tool_calls nhung khong dung duoc khoi tool_use; "
                    "ha ve end_turn de client khong treo")
        ly_do = "end_turn"
    # Và chiều ngược lại: có khối `tool_use` thì `stop_reason` PHẢI nói `tool_use`,
    # dù thượng nguồn báo `stop`. Client dừng vòng lặp theo `stop_reason`; nói
    # `end_turn` trong khi vừa đưa ra một lời gọi tool là bảo nó **đừng chạy**.
    elif any(k.get("type") == "tool_use" for k in khoi):
        ly_do = "tool_use"

    return {
        "id": "msg_" + request_id,
        "type": "message",
        "role": "assistant",
        "model": ten,
        "content": khoi,
        "stop_reason": ly_do,
        "stop_sequence": None,
        "stop_details": None,
        "usage": {"input_tokens": kq.token_vao,
                  "output_tokens": kq.token_ra},
    }


def _thu_mot_cuc(ten: str) -> dict:
    """Che do thu: dung hinh dang, khong cham GPU, khong cham so tien."""
    return {
        "id": "msg_sandbox", "type": "message", "role": "assistant",
        "model": ten,
        "content": [{"type": "text", "text": "sandbox: khong goi model that"}],
        "stop_reason": "end_turn", "stop_sequence": None, "stop_details": None,
        "usage": {"input_tokens": 0, "output_tokens": 0},
    }


def _bao_400(detail: str, than: dict, *, dung=invalid_request):
    """Ghi lại LÝ DO + HÌNH DẠNG request mỗi khi ta trả 400 — để soi vì sao Codex
    bị vứt lượt. (Tạm; gỡ khi đã chẩn xong.) KHÔNG log nội dung nhạy cảm, chỉ
    khoá/kiểu.

    `dung` chọn **mã lỗi**, không đổi việc ghi log: 400 vì tên model đã cắt là
    `model_not_found` (D02), 400 vì hình dạng vẫn là `invalid_request`. Một
    hàm ghi log, hai mã — chép hàm này ra để đổi mỗi mã lỗi là dựng bản thứ hai
    của đúng đoạn log ta đang cần để chẩn.
    """
    tc = than.get("tool_choice")
    vao = than.get("input")
    log.warning(
        "400 /v1/responses: %s | stream=%s model=%r tc=%r input=%s(len=%s) "
        "tools=%s keys=%s",
        detail, than.get("stream"), than.get("model"),
        (tc.get("type") if isinstance(tc, dict) else tc),
        type(vao).__name__, (len(vao) if isinstance(vao, (list, str)) else "-"),
        len(than.get("tools") or []), sorted(than.keys()))
    return dung(detail)


#: Tiền tố của tên model **do chính client bịa ra** khi nó không biết model của
#: ta. Đây KHÔNG phải danh sách hãng — nó là danh sách **triệu chứng**.
_TIEN_TO_TEN_HANG = ("gpt-", "o1", "o3", "o4", "claude-", "gemini-", "grok-")


def _goi_y_ten_la(ten: str) -> str:
    """Thêm chỉ dẫn khi tên model là **tên sản phẩm của hãng khác**.

    🔴 VÌ SAO ĐÁNG MỘT HÀM RIÊNG. Ngày 29-30/08 mất nhiều giờ mới hiểu vì sao
       Codex gửi `model='gpt-5.6-luna'` — một tên không tồn tại ở chỗ ta. Gốc:
       Codex **không có metadata** cho `ltt_llm`, nên nó rơi vào đường
       `compact_model_fallback` và mượn tên một model OpenAI cho lượt phụ.
       Bằng chứng: khai `model_catalog_json` xong thì `model_context_window`
       của phiên đổi từ 84.127 sang **79.699 = 88.555 × 90 %** — đúng hai con
       số ta khai — và 400 hết hẳn.

    ⛔ VÀ VÌ SAO KHÔNG ÁNH XẠ TÊN ĐÓ VỀ `ltt_llm`. Nhận `gpt-5.6-luna` rồi lặng
       lẽ phục vụ Qwen là **mượn tên sản phẩm của hãng khác** — đúng thứ mà
       `TUYEN_TUONG_THICH` cố ý không làm (tên ở đó là tên TA tự đặt). Nó cũng
       giấu mất cấu hình sai: khách tưởng đang chạy đúng, còn ta thì không bao
       giờ biết máy nào khai thiếu catalog.

    ⇒ Nên ta **vẫn từ chối**, chỉ nói thẳng cách sửa.
    """
    thap = (ten or "").lower()
    if not any(thap.startswith(t) for t in _TIEN_TO_TEN_HANG):
        return ""
    return (
        f" NOTE: `{ten}` is another vendor's product name — your client "
        f"substituted it because it has no metadata for our model. Fix the "
        f"client, not the request: for Codex declare `model_catalog_json` in "
        f"~/.codex/config.toml (the `cam` command of our CLI tool does this "
        f"for you). We do not alias other vendors' model names.")


def _tran_vao_cua_model(alias: str) -> int:
    """Trần đầu vào thật của một alias. Lùi về trần chung khi tên lạ."""
    # ⭐ Pha 05.1 (AI CLEAN REBUILD V2): bảng bí danh nay ở `platform_core`, nên
    #    `server` không còn phải import một app cụ thể để lấy nó. Dòng
    #    `ignore_imports` tương ứng trong `.importlinter` đã được **xoá**, không
    #    phải nới — bánh cóc siết lại một nấc.
    #
    # ⚠️ Món nợ còn lại là `ngan_sach` (dòng 48): ngân sách token là **việc của
    #    app**, không phải của nền tảng, nên đẩy nó lên `platform_core` sẽ là
    #    một quyết định kiến trúc khác chứ không phải phần thừa của bản vá này.
    #    Nó vẫn nằm trong `.importlinter` dưới dạng một ngoại lệ CÓ TÊN.
    from platform_core.llm.canonical import ALIAS_SANG_ID
    try:
        return ngan_sach.tran_vao_cua(ALIAS_SANG_ID[alias])
    except KeyError:
        return ngan_sach.TOKEN_VAO_TRAN


def _cua(duong: str, than: dict, principal: Principal, db: Session,
         config, request=None) -> Response:
    # `text.chat` phải qua đủ ba cổng của Q92. Có route riêng KHÔNG cho nó đi
    # vòng qua công tắc người vận hành — cửa mới không được là cửa sau.
    tool = require_tool(build_catalog(config), TOOL_CHAT, principal)
    executor = for_tool(tool)


    ten = _giai_ten_model(str(than.get("model") or ""))
    aliases = executor.aliases()
    if ten not in aliases:
        # 🔴 `model_not_found`, KHÔNG `invalid_request` (D02, Step 2c). Tên cũ
        #    `ltt_llm` / `ltt_llm_vision` rơi vào đúng nhánh này từ 11/09/2026,
        #    và khách phải nghe cùng một câu ở mọi cửa: *tên model ấy không còn*,
        #    chứ không phải *yêu cầu của bạn sai hình dạng*.
        raise _bao_400(
            f"`model` must be one of {list(aliases)}"
            f"{' or ' + str(list(TUYEN_TUONG_THICH)) if TUYEN_TUONG_THICH else ''}. "
            f"Claude Code sends whatever ANTHROPIC_MODEL is set to, and Codex "
            f"sends `model` from its profile — set them to one of these."
            + _goi_y_ten_la(ten), than, dung=model_not_found)

    tin = _tin_nhan(than)
    if not tin:
        raise _bao_400("the request carries no input to answer", than)

    # 🔴 `tool_choice` — CHỈ TỪ CHỐI Ở ĐƯỜNG KHÔNG-STREAM.
    #
    #    Đường **không stream** đi qua `features.chay` → `dieu_phoi.goi`, nơi
    #    **không** nhận `tool_choice`; nuốt im lặng ở đó là để model trả lời bằng
    #    chữ khi khách **ép** gọi tool — nên phải từ chối, không bỏ qua.
    #
    #    Đường **stream** thì KHÁC: `gui = dict(than)` được chuyển **nguyên xi**
    #    tới máy B (llama-server, tương thích OpenAI, CÓ hỗ trợ `tool_choice`).
    #    Từ chối ở đây là bug thật đã chặn Codex: tiện ích Codex **ép** một tool
    #    (`tool_choice: {"type":"function","name":"..."}`) ở nhiều lượt agentic;
    #    ta trả 400 → lượt đó chết lặng (model đã chạy trên GPU nhưng bị vứt), và
    #    khách thấy "GPU dừng mà không có gì xảy ra". (Đo 2026-08-27.)
    #
    # ⭐ `auto` bỏ qua được ở cả hai vì nó **đã là** mặc định của thượng nguồn.
    _chon = than.get("tool_choice")
    if _chon is not None and not than.get("stream"):
        _loai = _chon if isinstance(_chon, str) else (_chon or {}).get("type")
        if _loai != "auto":
            raise _bao_400(
                f"`tool_choice` {_loai!r} is not supported on non-streaming "
                f"requests; only \"auto\" (the default) is honoured there. "
                f"Use streaming, or omit the field.", than)

    # Dịch alias -> id nội bộ NGAY TRƯỚC KHI ra khỏi nền tảng. Khách không bao
    # giờ nhìn thấy `qwen38-*`, và mã của khách không ghim vào nó (test_212).
    gui = dict(than)
    gui["model"] = executor.model_id(ten)


    # 🔴 KHONG STREAM CUNG PHAI PHUC VU DUOC, va day la mot lo hong THAT.
    #
    #    Ban dau route nay tu choi thang moi request khong co `stream: true`, voi
    #    ly do "nhan roi tra mot cuc la noi doi client". Ly do do dung cho mot
    #    client DA XIN streaming - nhung sai voi hop dong Anthropic Messages,
    #    thu ma **cho phep ca hai**.
    #
    # ⛔ HAU QUA DO DUOC 24/08: Claude Desktop **tham do model** bang mot request
    #    KHONG streaming toi `/v1/messages`. Ta tra 400, ung dung ket luan
    #    *"Gateway rejected model ltt_llm"* va **CHAN LUON o chat** - khong phai
    #    mot canh bao trang tri, ma la mot cua dong.
    #
    #    Tuc mot dong `if` giu cho hop dong "sach" da lam ca mot ung dung khach
    #    khong dung duoc, va trieu chung ma khach nhin thay ("model khong kha
    #    dung") **khong he chi ve phia nguyen nhan**.
    # 🔴 KHAI TOOL MÀ KHÔNG MỤC NÀO DÙNG ĐƯỢC ⇒ NÓI RA, ĐỪNG IM LẶNG BỎ.
    #
    #    Đặt ở ĐÂY, **trước** chỗ rẽ nhánh, nên nó che cả `stream:false`
    #    (`_mot_cuc`) lẫn nhánh luồng — hai đường đánh rơi `tools` ở hai nơi
    #    khác nhau, và một phép kiểm ở một nhánh sẽ bỏ lọt nhánh kia.
    #
    #    Đo 01/09: gửi `tools` khuôn **OpenAI** vào cửa Anthropic này cho ra
    #    `200` và model trả lời *"Xin lỗi, hiện tại tôi không có tool nào"*.
    #    Khách gõ sai hình dạng nhận một câu trả lời **hợp lý mà sai**, không
    #    phải một lỗi — và đó là nhầm lẫn dễ mắc nhất ở đây: hai giao thức, hai
    #    khuôn tool, cùng một tên trường `tools`.
    #
    # ⛔ Nó lệch chuẩn với chính khu API này, nơi lỗi gọi đúng tên scope thiếu
    #    và đính `retry: never`. Anthropic thật trả `400` cho tool schema sai.
    # 🔴 `invalid_request`, KHÔNG PHẢI `executor.parameter_error`.
    #
    #    Bản đầu ném `parameter_error` ở đây. Nhưng bộ bắt nó nằm trong `try`
    #    của `_mot_cuc` — **xa phía dưới**, và chỗ này ở NGOÀI khối đó. Ngoại lệ
    #    thoát thẳng ra và thành **500**.
    #
    # ⛔ Tức bản vá đó làm MỌI THỨ TỆ HƠN: từ "câu trả lời sai im lặng" thành
    #    "500 không nói gì" — mất luôn cả thông điệp lẽ ra phải giúp khách. Đo
    #    thật trên production 01/09 trước khi sửa lại.
    #
    # ⭐ Ở đây CHƯA giữ tiền nào (trước `policy.resolve`), nên không cần hoàn —
    #    khác hẳn nhánh `parameter_error` dưới kia, nơi hold đã đặt rồi.
    vi_tool = tool_dich.vi_sao_khong_dung_duoc(than.get("tools"))
    if vi_tool:
        raise invalid_request(vi_tool)

    if not than.get("stream"):
        # Suy nghĩ do máy chủ quyết (L-26) — cùng hàm với nhánh stream (`tien_kiem`).
        try:
            than, bo_qua = cua_luong.chuan_hoa_suy_nghi(than, ten)
        except cua_luong.ThamSoSai as e:
            raise _bao_400(str(e), than) from None
        tra = _mot_cuc(duong, than, tin, ten, principal, db, config, tool,
                       trang_thai=getattr(request, "state", None),
                       request=request)
        if bo_qua:
            tra.headers[HEADER_EFFORT_BO_QUA] = "1"
        return tra

    resolved = policy.resolve(db, config=config, principal=principal,
                              tool_name=TOOL_CHAT)

    # ── Chế độ thử: không chạm GPU, không chạm sổ tiền ───────────────────────
    # ⛔ ĐỪNG BỎ NHÁNH NÀY. Một khoá thử ai đăng ký cũng có; để nó chiếm GPU thật
    #    là mở một cách miễn phí để giữ card của máy B.
    if sandbox.is_test(principal.mode):
        limits.enforce_create_rate(key_id=principal.key_id, config=config,
                                   limits=resolved, user_id=principal.user_id)
        return StreamingResponse(_luong_thu(duong), media_type="text/event-stream",
                                 headers=_SSE)

    # ⛔ KHONG tu ghep chuoi o day: `credit_entries.job_id` la VARCHAR(36) va
    #    PostgreSQL ep do dai trong khi SQLite thi khong. Xem `thanh_toan.ma_luot`.
    # ── Từ đây là FACADE (H43 Phase 02): admission → giữ chỗ → commit → mở luồng.
    #
    #    Toàn bộ thứ tự cửa đã đo là đúng (Q107/Q114) nay sống ở
    #    `platform_core/runtime_noi_bo/luong.py`, để client nội bộ (ChatLTT) và
    #    cửa này đi MỘT đường đếm token và quyết toán. Ở đây chỉ còn việc của
    #    HTTP: dịch bốn lỗi trước-byte-đầu sang mã trạng thái + `problem+json`.
    # ── multijob D-06: tool khai ngân sách KV ⇒ tiền kiểm TRƯỚC 200, rồi chờ trong
    #    SSE (nhịp tim), được nhận mới giữ tiền và mở luồng máy B. Bốn lỗi dưới
    #    đây vẫn trả TRƯỚC 200 — riêng "quá dài" đi khuôn của từng giao thức
    #    (`su_kien_loi.loi_qua_dai`, R-08): đó là thứ Codex và Claude Code dò để
    #    TỰ NÉN hội thoại, không phải mã 413.
    try:
        tk = cua_luong.tien_kiem(
            db, user_id=principal.user_id, tool_name=TOOL_CHAT,
            than={**than, "model": ten}, duong=duong)
    except cua_luong.ThamSoSai as e:
        raise _bao_400(str(e), than) from None
    except cua_luong.ThieuCredit as e:
        raise insufficient_credit(
            THIEU_CREDIT_LOI, **thieu_credit_chi_tiet(e)) from None
    except cua_luong.DangBan as e:
        # Phòng chờ đã chạm trần (số người / token prefill) — không có hàng vô hạn.
        #
        # ⛔ `thu_lai_sau_s` và `nguon` đi KÈM lỗi; trước 14/09 cả hai bị vứt và
        #    cửa này luôn nói `Retry-After: 15`. Một `Retry-After` bịa ra tệ hơn
        #    không có — client lịch sự sẽ TIN nó, nên số sai đẩy cả đàn client
        #    quay lại sai nhịp.
        raise limits.execution_busy(
            e.tai_nguyen, retry_after=e.thu_lai_sau_s,
            reason=e.nguon) from None
    except cua_luong.KhongMoDuoc as e:
        # R-08: đúng khuôn + câu của TỪNG giao thức (`su_kien_loi.loi_qua_dai`) —
        # client nhận ra "quá dài" bằng câu chữ/khuôn, không bằng mã 413.
        return su_kien_loi.loi_qua_dai(
            duong, stream=True, token=e.token,
            tran=e.tran if e.tran is not None else _tran_vao_cua_model(ten),
            request=request)
    # Chỉ lượt qua tiền kiểm ngữ cảnh/credit/công suất mới tiêu hạn mức tạo.
    limits.enforce_create_rate(key_id=principal.key_id, config=config,
                               limits=resolved, user_id=principal.user_id)
    # ⛔ MỌI model của `text.chat` ĐỀU khai ngân sách KV ⇒ mọi lượt đi phòng chờ.
    #    Đo 13/09/2026 bằng chính bản khai:
    #        ltt-3.8 -> ltt_38_3090, 3 suất, pool 221.184
    #        ltt-3.5 -> ltt_35_5060, 3 suất, pool 262.144
    #
    # 🔴 TRƯỚC 13/09 Ở ĐÂY CÒN MỘT "ĐƯỜNG CŨ" cho tool không khai ngân sách —
    #    di tích của thời một card, một lượt, chưa có hàng đợi. Nó **không thể
    #    với tới được** từ cửa này, và ba bản vá liên tiếp của L-08 đều rơi đúng
    #    vào nó: đúng về kỹ thuật, và chưa một lần chạm vào lượt thật.
    #
    # ⇒ Đã gỡ. Một cửa thật, nên mọi lớp bảo vệ gắn MỘT lần là áp cho mọi lượt.
    #   `test_1248` chốt rằng chỉ còn một, và rằng nó đủ ba lớp.
    if not tk.dung_phong_cho:
        # Hỏng ỒN ÀO thay vì lặng lẽ rơi vào một đường không được bảo vệ.
        raise service_unavailable(
            "This model is not configured for admission control.")

    # 🔴 CHỐT GIAO DỊCH CỦA REQUEST TRƯỚC KHI STREAM. Generator mở phiên MỚI để
    #    ghi dòng chờ và giữ tiền; để giao dịch của request (rate-limit,
    #    idempotency) còn mở là SQLite "database is locked" và PostgreSQL giữ
    #    khoá hàng suốt lúc chờ.
    db.commit()

    from platform_core.llm import admission

    # 🔴 Ô NHỚ: `lease_id` và `luot` chỉ SINH RA BÊN TRONG generator, sau khi
    #    xếp hàng xong — mà `StreamingResponse` phải dựng TRƯỚC đó. Ba đường nhả
    #    dưới đây đọc qua ô này chứ không chụp sẵn được.
    so_tay: dict = {}

    def _dong_nguon() -> None:
        """Đóng cửa ra mạng tới máy B — bảo nó THÔI SINH, không chỉ thôi đọc."""
        luot = so_tay.get("luot")
        dong = getattr(luot, "dong_nguon", None) if luot is not None else None
        if callable(dong):
            dong()

    def _nha_suat() -> None:
        """LỚP 1: nhả suất theo tín hiệu đứt.

        ⛔ Khách cắt lúc còn XẾP HÀNG ⇒ `so_tay` rỗng ⇒ KHÔNG nhả gì. Chưa giành
           được suất nào thì nhả bừa là nhả **suất của người khác**.
        """
        cb = so_tay.get("cb")
        if cb is not None and cb.lease_id:
            admission.release_by_id(cb.lease_id)

    def _ket_thuc() -> None:
        """Hai việc phải chạy kể cả khi thân chưa từng được đọc: TIỀN và SUẤT."""
        luot = so_tay.get("luot")
        cb = so_tay.get("cb")
        try:
            if luot is not None:
                cua_luong.dam_bao_quyet_toan(luot)
            elif cb is not None:
                # 💰 Đã giành suất + giữ tiền mà luồng CHƯA từng mở (khách đi
                #    trong lúc xếp lại sau 429 của máy B — phương án C bước 1 —
                #    hoặc trong lúc đang mở). Generator có thể bị bỏ rơi giữa
                #    chừng nên `finally` của nó không phải đường chắc chắn; hoàn ở
                #    đây. Idempotent: đường nào đã kết sổ rồi thì là no-op.
                cua_luong.hoan(cb.user_id, cb.request_id)
        finally:
            _nha_suat()

    async def _ket_thuc_che_chan() -> None:
        """Che chắn `BackgroundTask` — bản vá cộng đồng, ta tự áp ở phía mình.

        `starlette/background.py` (1.3.1) KHÔNG bọc `CancelScope(shield=True)`.
        Với `BaseHTTPMiddleware` trong chuỗi — ta có bốn tầng — cancel scope bao
        quanh có thể đã bị huỷ, và `await run_in_threadpool(...)` vỡ ở checkpoint
        ĐẦU, trước khi luồng kịp khởi động: tiền chưa quyết toán, suất chưa nhả.
        Đúng cảnh `Kludex/starlette#1438` mô tả. Bản vá `shield` được đề xuất ở
        chính issue ấy nhưng chưa bao giờ được gộp (đóng qua PR #1715).
        """
        with anyio.CancelScope(shield=True):
            await run_in_threadpool(_ket_thuc)

    return StreamingResponse(
        cua_luong.bat_dong_bo_hoa(
            cua_luong.luong_co_cho(tk, loi_sse=su_kien_loi.loi_sse,
                                   nhip_sse=su_kien_loi.bo_nhip(duong),
                                   trang_thai=getattr(request, "state", None),
                                   timeout_s=MO_LUONG_GIAY, so_tay=so_tay),
            _dong_nguon, _nha_suat),
        media_type="text/event-stream",
        headers={**_SSE, HEADER_EFFORT_BO_QUA: "1"} if tk.effort_bo_qua else _SSE,
        background=BackgroundTask(_ket_thuc_che_chan))


# `_phat` / `_quyet_toan` / `_hoan` đã HẠ xuống
# `platform_core/runtime_noi_bo/luong.py` (H43 Phase 02). Giữ tên ở đây cho
# ai còn tra theo tên cũ; thân hàm chỉ có MỘT ở nơi mới.
_quyet_toan = cua_luong.quyet_toan
_hoan = cua_luong.hoan



# ── Đọc yêu cầu của hai giao thức ────────────────────────────────────────────

# Ước token đầu vào: một hàm, một chỗ — `runtime_noi_bo.luong.uoc_tin_nhan`.
_tin_nhan = cua_luong.uoc_tin_nhan



def _chu_trong(khoi) -> str:
    """Văn bản trong một trường có thể là chuỗi **hoặc** danh sách khối Anthropic."""
    if isinstance(khoi, str):
        return khoi
    if isinstance(khoi, list):
        return "\n".join(str((m or {}).get("text", "")) for m in khoi
                         if isinstance(m, dict))
    return ""


def _tin_that(than: dict) -> list:
    """`messages` **THẬT** để gửi cho model — khác hẳn `_tin_nhan`.

    🔴 HAI HÀM NÀY TRÔNG GIỐNG NHAU VÀ KHÔNG THỂ THAY NHAU. `_tin_nhan` chỉ để
       **ước token**, nên nó cố ý sinh ra những phần tử **không có `role`**:
       prompt hệ thống thành `{"content": …}`, và cả khối JSON của `tools` cũng
       được nhét vào như một "tin nhắn" để cộng token.

    ⛔ ĐO ĐƯỢC 25/08, TRÊN PRODUCTION. Bản đầu của `_mot_cuc` đem thẳng danh sách
       ước ấy đi gọi model. Hai hậu quả, và cái thứ hai tệ hơn:

       1. Request nào có `system` hoặc `tools` thì `kiem_tham_so` ném
          `ThamSoSai: moi phan tu cua messages phai co role` → **500**.
       2. Request nào **không** vỡ thì model nhận một hội thoại đã bị bóp méo:
          prompt hệ thống mất vai trò, và định nghĩa tool trở thành một lượt nói
          của người dùng. Nó **vẫn trả lời**, nên lỗi này không tự lộ ra — phép
          thử `8x7` vẫn đúng, và điều đó che mất chuyện ngữ cảnh đã sai.

    ⭐ Nên đường gọi model phải có hàm riêng, và `_tin_nhan` ở lại đúng việc của
       nó. Ước token được phép cẩu thả; thứ gửi cho model thì không.
    """
    ra: list = []
    he = _chu_trong(than.get("system"))
    if he.strip():
        ra.append({"role": "system", "content": he})

    for m in than.get("messages") or []:
        if isinstance(m, dict) and m.get("role"):
            ra.append(m)

    # `/responses` gọi nó là `input`, và nó có thể là chuỗi trần.
    vao = than.get("input")
    if isinstance(vao, str) and vao.strip():
        ra.append({"role": "user", "content": vao})
    elif isinstance(vao, list):
        ra.extend(m for m in vao if isinstance(m, dict) and m.get("role"))
    return ra


def _max_tokens(than: dict, token_vao_uoc: int = 0, executor=None) -> int:
    """Trần token ra cho lượt này, đã kẹp theo **chỗ còn lại trong ngữ cảnh**.

    ⚠️ `token_vao_uoc` mặc định 0 chỉ để không phá lời gọi cũ; đường thật luôn
       truyền số vào. Vào và ra chia nhau cùng một cửa sổ 65.536.
    """
    executor = executor or for_tool_name(TOOL_CHAT)
    # Theo cửa sổ của ĐÚNG model khách xin (O-24 cùng lớp), không cửa sổ hẹp nhất.
    tran = executor.context_output_cap(token_vao_uoc,
                                       str(than.get("model") or "") or None)
    for ten in ("max_tokens", "max_output_tokens"):
        gt = than.get(ten)
        if isinstance(gt, (int, float)) and not isinstance(gt, bool):
            return max(1, min(int(gt), tran))
    # 🔴 MẶC ĐỊNH CỦA CỬA STREAM, KHÔNG PHẢI CỦA CỬA ĐỒNG BỘ.
    #
    #    `executor.default_max_tokens` là `SYNC_MAX_TOKENS_MAC_DINH = 1024` —
    #    con số **cố ý nhỏ** cho cửa trả một cục, vì cửa đó bị trần 100 giây của
    #    Cloudflare. Cửa stream không có ràng buộc đó, và chú thích ngay tại
    #    `features.py` đã ghi rõ: *"Cửa stream và cửa job vẫn dùng mặc định
    #    4.096 / trần 32.768 của manifest"*. Mã thì lại lấy 1.024.
    #
    # ⛔ ĐO ĐƯỢC 30/08 — ĐÂY LÀ GỐC CỦA "HỎI DÀI THÌ IM LẶNG": một lượt KHÔNG
    #    khai giới hạn trả về đúng `output_tokens=1024`, `status=completed`, sau
    #    ~22 giây; tức câu trả lời **bị cắt cụt** chứ không phải mất kết nối.
    #    Codex không tự khai `max_output_tokens` nên lượt nào của nó cũng dính;
    #    câu ngắn (<1024 token) thì không ai thấy gì bất thường.
    #
    # ⭐ VÌ SAO ĐỂ RỘNG LÀ AN TOÀN: credit **giữ trước rồi hoàn** về đúng số token
    #    thật sinh ra (`_quyet_toan`), và model tự dừng khi trả lời xong. Nên số
    #    này chỉ quyết định *chỗ để thở*, không quyết định tiền khách trả.
    return min(int(executor.mac_dinh_cho("stream")), tran)


def _luong_thu(duong: str) -> Iterator[bytes]:
    """Luồng của chế độ thử: đúng hình dạng, không model, không tiền."""
    import json

    def sk(ten: str, goi: dict) -> bytes:
        return (f"event: {ten}\n".encode()
                + b"data: " + json.dumps(goi).encode() + b"\n\n")

    chu = "[test mode] no model was called and no credit moved."
    if duong.endswith("/responses"):
        item_id = "msg_test"
        item = {"id": item_id, "type": "message", "status": "in_progress",
                "role": "assistant", "content": []}
        yield sk("response.created", {"type": "response.created",
                                      "response": {"id": "resp_test",
                                                   "status": "in_progress",
                                                   "output": []}})
        yield sk("response.output_item.added", {"type": "response.output_item.added",
                                                "output_index": 0, "item": item})
        yield sk("response.content_part.added", {"type": "response.content_part.added",
                                                 "item_id": item_id, "output_index": 0,
                                                 "content_index": 0, "part": {
                                                     "type": "output_text", "text": "",
                                                     "annotations": []}})
        yield sk("response.output_text.delta",
                 {"type": "response.output_text.delta", "item_id": item_id,
                  "output_index": 0, "content_index": 0, "delta": chu})
        done_part = {"type": "output_text", "text": chu, "annotations": []}
        yield sk("response.output_text.done", {"type": "response.output_text.done",
                                               "item_id": item_id, "output_index": 0,
                                               "content_index": 0, "text": chu})
        yield sk("response.content_part.done", {"type": "response.content_part.done",
                                                "item_id": item_id, "output_index": 0,
                                                "content_index": 0, "part": done_part})
        done_item = {**item, "status": "completed", "content": [done_part]}
        yield sk("response.output_item.done", {"type": "response.output_item.done",
                                               "output_index": 0, "item": done_item})
        yield sk("response.completed", {
            "type": "response.completed",
            "response": {"id": "resp_test", "status": "completed",
                         "output": [done_item],
                         "usage": {"input_tokens": 0, "output_tokens": 0,
                                   "total_tokens": 0}}})
        return
    yield sk("message_start", {"type": "message_start", "message": {
        "id": "msg_test", "type": "message", "role": "assistant", "content": [],
        "usage": {"input_tokens": 0, "output_tokens": 0}}})
    yield sk("content_block_start", {"type": "content_block_start", "index": 0,
                                     "content_block": {"type": "text", "text": ""}})
    yield sk("content_block_delta", {"type": "content_block_delta", "index": 0,
                                     "delta": {"type": "text_delta", "text": chu}})
    yield sk("content_block_stop", {"type": "content_block_stop", "index": 0})
    yield sk("message_delta", {"type": "message_delta",
                               "delta": {"stop_reason": "end_turn"},
                               "usage": {"output_tokens": 0}})
    yield sk("message_stop", {"type": "message_stop"})

"""
api.py — hợp đồng HTTP của cổng VLM.

    GET  /health                  phien ban · model dang mo · trong tai · thuong nguon
    GET  /v1/models               danh muc THAT SU dang mo (fail-closed)
    POST /v1/chat/completions     OpenAI Chat      — moi thu khac
    POST /v1/responses            OpenAI Responses — CODEX CLI (bat buoc giao thuc nay)
    POST /v1/messages             Anthropic        — CLAUDE CODE (ANTHROPIC_BASE_URL)

⭐ BA GIAO THỨC, MỘT ĐƯỜNG ỐNG. Codex chỉ nói Responses (từ 02/2026 nó bỏ hẳn lựa
   chọn `chat`); Claude Code chỉ nói Anthropic Messages. `llama-server` **nói được
   cả ba**, nên cổng này không dịch gì cả — nó chỉ **kiểm rồi chuyển tiếp**.

⛔ BẬN THÌ TRẢ **429**, KHÔNG PHẢI 5xx. Máy A phân biệt hai thứ này: 429 là trạng
   thái bình thường của một máy chia GPU với việc ảnh và việc video. Nếu máy A hiểu
   nhầm thành lỗi, `api_pool` sẽ cooldown rồi `disable` key `ltt_llm` sau 5
   lần — và một tối chạy video sẽ **tự tắt vĩnh viễn model nhà** (D-005).

⛔ KHÔNG TỰ ĐỔI SANG MODEL KHÁC khi bận. Cổng này chỉ biết model nhà. Việc "bận thì
   dùng đám mây" là **quyết định của máy A** (D-010), không phải của cổng.

⛔ KHÔNG PHÂN TÍCH RỒI DỰNG LẠI SSE. Xem `upstream.stream`.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Optional

from fastapi import Body, Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse, Response, StreamingResponse
from starlette.background import BackgroundTask

from . import __version__
from . import ngan_sach as NS
from .catalog import KhongCoModel, ModelSpec, lay, nap_catalog, ten_la
from .config import Config
from .don_dep import DonDepGpu
from .gioi_han import GioiHan, boc_luong
from .nhip_tim import boc_nhip_tim
from .to_tien import ToTien
from .tren_gpu import kiem as kiem_gpu
from .trong_tai import TrongTai

log = logging.getLogger("llm_gateway.api")

#: Đường thượng nguồn tương ứng mỗi đường của cổng. llama-server phơi đúng các
#: đường này, nên ánh xạ là một-đối-một.
DUONG = {
    "chat": "/v1/chat/completions",
    "responses": "/v1/responses",
    "messages": "/v1/messages",
}


def create_app(cfg: Config, upstream, *, trong_tai: Optional[TrongTai] = None,
               don_dep: Optional[DonDepGpu] = None,
               gioi_han: Optional[GioiHan] = None,
               now=time.monotonic) -> FastAPI:
    app = FastAPI(title="LTT LLM Gateway", version=__version__)

    # Chup to tien MOT LAN o day, luc no chac chan con song. Sau khi vo boc
    # chet thi duong di len cay khong con nua -- do lai la muon. Xem bay #3
    # o `to_tien.py`.
    to_tien = ToTien()

    catalog: dict[str, ModelSpec] = nap_catalog(cfg.models_mo)
    la = ten_la(cfg.models_mo)
    if la:
        log.warning("LTT_LLM_MODELS co ten khong khop ho so nao: %s", ", ".join(la))

    # ⭐ `model_cua_ta_dang_chay` noi cho trong tai biet tai cao tren card la CUA
    #    TA hay cua nguoi khac. `_co_model_cua_ta_dang_chay` dinh nghia ben duoi;
    #    lambda giai ten luc GOI, nen thu tu dinh nghia khong thanh van de.
    #
    # ⛔ Va no duoc goi LUOI — chi khi nhanh tai thuc su can den, xem `phan_xu`.
    #    Goi `/running` moi yeu cau la them mot vong loopback vao duong nong.
    tt = trong_tai if trong_tai is not None else TrongTai(
        ram_trong_toi_thieu_gb=cfg.ram_trong_toi_thieu_gb, bat=cfg.trong_tai_bat,
        model_cua_ta_dang_chay=lambda: _co_model_cua_ta_dang_chay())

    gh = gioi_han if gioi_han is not None else GioiHan(
        max_dong_thoi=cfg.max_dong_thoi, rpm=cfg.rpm, now=now)

    if don_dep is not None:
        pass                                   # đã tiêm (test)
    elif cfg.don_dep_bat:
        don_dep = DonDepGpu(comfy_url=cfg.comfy_url,
                            nguong_sach_mb=cfg.vram_sach_mb)

    def _co_model_cua_ta_dang_chay() -> bool:
        """`llama-swap` có đang giữ **bất kỳ** model nào của ta không.

        🔴 PHẢI LÀ "BẤT KỲ", KHÔNG PHẢI "ĐÚNG MODEL NÀY". Đây là một lỗi thật đã
           xảy ra 22/08 và nó làm **hồ sơ vision gần như không bao giờ gọi được**:

             `qwen38-api` đang chạy, giữ 19.973 MiB
             khách xin `qwen38-vision`
             -> bản cũ hỏi "đúng model này chưa?" -> chưa -> đi dọn
             -> `don_dep` thấy VRAM cao, bảo COMFYUI nhả (nó chẳng giữ gì)
             -> chờ 18 giây, VRAM không đổi vì nó LÀ CỦA TA -> 429

           VRAM của chính ta thì **`llama-swap` tự đổi được** — nó dừng model cũ,
           bật model mới. Việc của `don_dep` chỉ là dọn phần **người khác** giữ.

        ⛔ Không biết thì trả `False` (⇒ đi dọn). Dọn thừa tốn vài giây; bỏ qua
           việc dọn khi cần thì phục vụ ở một phần tư tốc độ, âm thầm.
        """
        ma, than = upstream.json("GET", "/running", timeout=5.0)
        if ma != 200:
            return False
        try:
            import json as _json
            d = _json.loads(than or b"{}")
        except (ValueError, TypeError):
            return False
        return any(isinstance(m, dict) and m.get("model") for m in (d.get("running") or []))

    #: Nhớ tên hồ sơ đang nạp trong ít giây, để một phiên agent gửi liên tiếp
    #: không sinh một `/running` cho mỗi lượt.
    #:
    #: ⭐ 2 giây là đủ: thứ ta hỏi chỉ quyết định *đếm chính xác có rẻ không*.
    #:    Sai trong 2 giây thì hậu quả xấu nhất là một lần lùi về phép ước
    #:    (từ chối oan một yêu cầu lẽ ra vừa) hoặc một `/tokenize` bị llama-swap
    #:    trả lời bằng hồ sơ khác — cả hai đều không chạm tiền và không sai
    #:    chiều nguy hiểm.
    _nho_nap: dict = {"luc": None, "ten": ""}
    _TTL_NHO_NAP_S = 2.0

    def _ho_so_dang_nap(ten: str) -> bool:
        """Đúng **hồ sơ này** có đang nằm trong VRAM không.

        ⛔ KHÁC `_co_model_cua_ta_dang_chay()` ở trên, và khác một cách có chủ ý.
           Ở đó câu hỏi là *"llama-swap có đang giữ BẤT KỲ model nào của ta"* —
           để trọng tài biết tải cao trên card là của ai. Ở đây câu hỏi là
           *"đếm token bằng `/tokenize` có RẺ không"*, và nó chỉ rẻ khi **đúng
           hồ sơ này** đã nạp: hỏi `/tokenize` cho một hồ sơ khác thì llama-swap
           sẽ ĐỔI model để phục vụ nó — tức đánh thức GPU, mất 2,5 phút, và làm
           đúng cái điều mà phép ước sinh ra để tránh.

        ⚠️ `timeout=2.0`, KHÔNG phải 5. Lời gọi này nằm trên đường **từ chối**:
           nếu llama-swap chết thì bản cũ trả `413` tức thì, còn bản này sẽ chờ
           hết timeout trước khi từ chối. Năm giây cho một yêu cầu chắc chắn bị
           từ chối là một hồi quy; hai giây là cái giá tối thiểu còn đọc được.
        """
        luc = _nho_nap["luc"]
        if luc is not None and (now() - luc) < _TTL_NHO_NAP_S:
            return _nho_nap["ten"] == ten
        ma, than = upstream.json("GET", "/running", timeout=2.0)
        if ma != 200:
            return False
        try:
            import json as _json
            d = _json.loads(than or b"{}")
        except (ValueError, TypeError):
            return False
        dang = ""
        for m in (d.get("running") or []):
            if isinstance(m, dict) and str(m.get("state") or "") == "ready":
                dang = str(m.get("model") or "")
                break
        _nho_nap["luc"] = now()
        _nho_nap["ten"] = dang
        return dang == ten

    def _dem_token_that(ten: str, van: list) -> "int | None":
        """Số token THẬT của các đoạn văn bản, qua `/tokenize` của llama-server.

        Trả `None` khi không đếm được — hồ sơ chưa nạp, hoặc thượng nguồn không
        trả lời. `None` **không phải** 0: bên gọi phải lùi về phép ước, không
        được coi như một yêu cầu rỗng.

        ⭐ `/tokenize` KHÔNG chạy inference. Nó cần từ vựng của model đang nạp,
           không cần một lượt sinh. Đo 03/09: gọi hàng chục lần trên prompt
           130K–180K, không sinh một token nào.

        ⛔ MỘT LỜI GỌI CHO CẢ HỘI THOẠI, không phải một lời gọi mỗi đoạn. Nối
           bằng `chr(10)` rồi đếm một lần: `n` lời gọi cho `n` tin nhắn là `n`
           vòng loopback, và với một phiên agent thì `n` lên tới hàng trăm.
           Sai số của việc nối (vài token ranh giới) nhỏ hơn hai bậc so với
           chỗ `LE` đã chừa.

        🔴 ĐƯỜNG PHẢI LÀ `/upstream/<model>/tokenize`, KHÔNG PHẢI `/tokenize`.
           `llama-swap` định tuyến theo trường `model` **trong thân**; `/tokenize`
           không có trường đó nên nó trả **404**. Đo 03/09 trên máy B:

               POST /tokenize                        -> 404
               POST /upstream/qwen38-api/tokenize     -> 200 {"tokens":[...]}
               POST 127.0.0.1:8281/tokenize (thang)   -> 200

        ⛔ VÀ BẢN ĐẦU CỦA HÀM NÀY DÙNG `/tokenize`. Nó nhận 404, `ma != 200`,
           trả `None`, và cổng **lặng lẽ lùi về phép ước** — tức bản vá đã
           deploy lên production và **không làm gì cả**, không một dòng nào nói
           ra. Đúng lớp khuyết tật mà cả chương trình này đi sửa: một năng lực
           có, được nối dây, và im lặng không hoạt động.

        ⭐ Nên lần lùi bây giờ **kêu**. Phân biệt hai thứ khác hẳn nhau:
           *"chưa nạp nên không hỏi"* là đường bình thường, không log;
           *"đã hỏi mà thất bại"* là một khuyết tật, và nó phải ra log.
        """
        if not van:
            return None
        if not _ho_so_dang_nap(ten):
            return None                      # binh thuong: khong log
        ma, than = upstream.json(
            "POST", "/upstream/" + ten + "/tokenize",
            body={"content": chr(10).join(str(s) for s in van)},
            timeout=30.0)
        if ma != 200:
            log.warning("dem token that THAT BAI ma=%s model=%s - lui ve phep uoc "
                        "(neu thay dong nay lien tuc thi duong /tokenize da doi)",
                        ma, ten)
            return None
        try:
            import json as _json
            d = _json.loads(than or b"{}")
        except (ValueError, TypeError):
            return None
        toks = d.get("tokens")
        if not isinstance(toks, list):
            log.warning("dem token that: than khong co `tokens` (model=%s) - "
                        "lui ve phep uoc", ten)
            return None
        return len(toks)

    def auth(authorization: str = Header(default="")) -> None:
        if not cfg.token:
            return          # dev: chưa đặt token → không chặn (giống render_gateway)
        got = authorization.removeprefix("Bearer ").strip()
        if got != cfg.token:
            raise HTTPException(status_code=401, detail="token khong dung")

    # ── Đọc trạng thái ───────────────────────────────────────────────────────

    @app.get("/live")
    def live() -> dict:
        """Thăm dò SỐNG/CHẾT — **không cần bearer**, và cố ý không nói gì thêm.

        ⭐ VÌ SAO TÁCH KHỎI `/health`: `/health` trả danh sách model, trạng thái
           trọng tài, các trần — đó là thông tin vận hành và nó **phải** sau khoá.
           Nhưng một máy giám sát chỉ cần biết tiến trình còn thở, và bắt nó mang
           theo bí mật chỉ để hỏi câu đó là đặt bí mật vào một chỗ nữa.

        ⛔ KHÔNG thêm bất cứ thứ gì vào đây. Mỗi trường thêm vào là một thứ rò ra
           cho người chưa xác thực: model nào đang mở, máy có bận không, trần bao
           nhiêu — tất cả đều nói cho người ngoài biết hệ thống đang ở đâu.
        """
        return {"ok": True, "version": __version__}

    @app.get("/health")
    def health(_: None = Depends(auth)) -> dict:
        px = tt.phan_xu()
        ma, _th = upstream.json("GET", "/v1/models", timeout=5.0)
        return {
            "version": __version__,
            "models_mo": sorted(catalog),
            "models_la": list(la),
            "thuong_nguon": {"url": cfg.upstream_url, "ma": ma, "song": 200 <= ma < 300},
            "trong_tai": {
                "bat": tt.bat,
                "ban": px.ban,
                "ly_do": px.ly_do,
                "so_python_gpu": px.so_python_gpu,
                "ram_trong_gb": round(px.ram_trong_gb, 1) if px.ram_trong_gb else None,
            },
            "tran": {
                "input_tokens": cfg.max_input_tokens,
                "output_tokens": cfg.max_output_tokens,
                "images": cfg.max_images,
            },
            "gioi_han": gh.trang_thai(),
            "nhip_tim_giay": cfg.nhip_tim_giay,
            # 🔴 CHỐT DUY NHẤT NHÌN RA ĐƯỢC SỰ CỐ 23/08. Mọi trường khác ở trên
            #    vẫn XANH khi CUDA hỏng và model bò trên CPU. Xem `tren_gpu`.
            "gpu": _xem_gpu(),
            # 🔴 CHOT DUY NHAT NHIN RA DUOC "HEALTH XANH GIA" (do 01/09:
            #    /health tra 200 suot 99 giay trong khi Get-Service = Stopped).
            #    Moi truong khac o tren van XANH khi tien trinh nay da mo coi,
            #    vi chung noi ve suc khoe cua CHINH no -- va no that su khoe.
            #    Cau hoi dung khong phai "anh co khoe khong" ma "anh co NEN
            #    dang chay khong".
            "duoi_dich_vu": to_tien.trang_thai(),
        }

    def _xem_gpu() -> dict:
        """Model có thật sự nằm trên card không.

        ⛔ Không dùng để từ chối yêu cầu — chốt **quan sát**, không phải chốt vào
           cửa. Model chạy CPU vẫn trả lời đúng, chỉ chậm; từ chối phục vụ sẽ
           biến một sự cố hiệu năng thành một sự cố ngừng dịch vụ.
        """
        from .don_dep import doc_vram_dung_mb

        px = kiem_gpu(co_model_nap=_co_model_cua_ta_dang_chay(),
                      doc_vram=doc_vram_dung_mb)
        return {"tren_gpu": px.tren_gpu, "vram_dung_mb": px.vram_dung_mb,
                "co_model_nap": px.co_model_nap, "dang_lo": px.dang_lo,
                "ly_do": px.ly_do}

    @app.get("/v1/models")
    def models(_: None = Depends(auth)) -> dict:
        # Rỗng là **đúng**, không phải hỏng: `LTT_LLM_MODELS` rỗng ⇒ chưa mở gì.
        return {
            "object": "list",
            "data": [
                {"id": m.ten, "object": "model", "owned_by": "ltt",
                 "context_window": m.max_context, "vision": m.co_vision,
                 "description": m.mo_ta}
                for m in sorted(catalog.values(), key=lambda x: x.ten)
            ],
        }

    # ── Đường ống chung của ba giao thức ─────────────────────────────────────

    def _chuyen_tiep(giao_thuc: str, body: dict[str, Any]) -> Response:
        ten = str(body.get("model") or "").strip()
        try:
            spec = lay(catalog, ten)
        except KhongCoModel:
            # 404, không phải 400: model không mở là "không có ở đây", và fail-closed
            # nghĩa là ta **không** tiết lộ model nào tồn tại mà chưa mở.
            raise HTTPException(status_code=404,
                                detail={"ly_do": "model khong co hoac chua duoc mo",
                                        "model": ten, "co_the_dung": sorted(catalog)})

        try:
            do = NS.kiem_tra(
                body,
                max_input_tokens=min(cfg.max_input_tokens, spec.max_context),
                max_output_tokens=cfg.max_output_tokens,
                max_images=cfg.max_images,
                max_image_bytes=cfg.max_image_bytes,
                max_context=spec.max_context,
                co_vision=spec.co_vision,
                # ⭐ Chỉ được gọi khi phép ƯỚC đã vượt trần — xem `NS.kiem_tra`.
                #    Đường nhanh không thêm round-trip nào.
                dem_that=lambda van: _dem_token_that(ten, van),
            )
        except NS.VuotNganSach as e:
            # 413 chứ không phải 400: đây là "to quá", không phải "sai cú pháp".
            raise HTTPException(status_code=413, detail=e.as_dict())

        # ── Hàng rào đồng thời (V9) ──────────────────────────────────────────
        #
        # ⭐ ĐỨNG SAU NGÂN SÁCH, TRƯỚC TRỌNG TÀI VÀ VIỆC DỌN. Ba lý do, theo thứ tự:
        #
        #   1. Sau ngân sách, vì 413 phải dứt khoát (xem đoạn dưới) — một yêu cầu
        #      to quá thì to quá, dù cổng đang đầy hay rảnh.
        #   2. Trước việc dọn, vì `bao_dam_sach()` **chờ tới 18 giây**. Không chặn ở
        #      đây thì 50 yêu cầu cùng lúc là 50 lượt chờ dọn song song, mỗi lượt
        #      giữ một luồng của uvicorn. Cái phải chặn là chỗ tốn thời gian.
        #   3. Trước trọng tài, vì trọng tài đọc `nvidia-smi` và `psutil` — rẻ,
        #      nhưng không rẻ khi nhân 50.
        #
        # 🔴 CÓ SUẤT LÀ CÓ NỢ. Mọi đường ra từ đây trở xuống **phải** trả suất, kể
        #    cả đường ném HTTPException. Đó là việc của `try/finally` bên dưới, và
        #    của `boc_luong` với luồng SSE. Quên một nhánh thì cổng tự bóp
        #    cổ mình sau vài lần lỗi, và triệu chứng sẽ là "429 mãi mãi" — rất khó
        #    lần ra vì lúc đó GPU hoàn toàn rảnh.
        px_gh, suat = gh.cap_suat()
        if suat is None:
            raise HTTPException(
                status_code=429,
                detail={"ly_do": "cong dang day", "chi_tiet": px_gh.ly_do},
                headers={"Retry-After": str(px_gh.thu_lai_sau_s)})
        try:
            return _chay_that(giao_thuc, body, spec, do, suat)
        except BaseException:
            suat.tra()         # ⛔ kể cả HTTPException, kể cả Ctrl-C. Idempotent.
            raise

    def _chay_that(giao_thuc: str, body: dict[str, Any], spec: ModelSpec,
                   do, suat) -> Response:
        """Phần tốn thời gian, đã cầm suất trong tay.

        ⚠️ Nó **không** tự trả suất khi thành công: với phản hồi thường, bên gọi
           trả ngay sau khi hàm này về; với SSE, suất còn phải giữ tới khi luồng
           hết. Xem hai nhánh cuối hàm.
        """
        ten = str(body.get("model") or "").strip()

        # ⛔ Trọng tài đứng SAU ngân sách có chủ ý: một yêu cầu vượt trần phải bị từ
        #    chối dứt khoát (413) kể cả khi card đang rảnh. Nếu đảo thứ tự, cùng một
        #    yêu cầu hỏng sẽ lúc trả 429 lúc trả 413 tuỳ card bận hay rảnh — và bên
        #    gọi sẽ thử lại mãi một thứ không bao giờ chạy được.
        px = tt.phan_xu()
        if px.ban:
            raise HTTPException(
                status_code=429,
                detail={"ly_do": "may B dang ban", "chi_tiet": px.ly_do},
                headers={"Retry-After": "30"})

        # 🔴 DỌN CARD TRƯỚC KHI NẠP — số đo 22/08 (P6):
        #      card bẩn (ComfyUI giữ 6.211 MiB) -> 18,2 tok/s
        #      card sạch (sau /free)            -> 63,3 tok/s
        #    Chênh 3,5 lần, và llama.cpp **không báo lỗi** — nó tràn trọng số sang
        #    RAM chủ qua PCIe, `/health` vẫn xanh. Xem `don_dep.py`.
        #
        # ⛔ Chỉ dọn khi KHÔNG có model nào CỦA TA đang chạy. Nếu có, VRAM cao là
        #    **của chính ta**, và `llama-swap` tự đổi hồ sơ được — gọi `/free` của
        #    ComfyUI lúc đó vừa vô ích vừa chặn mất việc đổi model.
        if don_dep is not None and not _co_model_cua_ta_dang_chay():
            kq = don_dep.bao_dam_sach()
            if not kq.sach:
                raise HTTPException(
                    status_code=429,
                    detail={"ly_do": "card chua san sang de nap model",
                            "chi_tiet": kq.ly_do,
                            "vram_dung_mb": kq.vram_cuoi_mb},
                    headers={"Retry-After": "60"})

        duong = DUONG[giao_thuc]
        log.info("%s model=%s token_vao~%d anh=%d", duong, ten, do.token_vao, do.so_anh)

        if bool(body.get("stream")):
            ma, ct, luong = upstream.stream(
                "POST", duong, body=body, timeout=cfg.stream_timeout_s)
            if ma >= 500:
                than = b"".join(luong)
                suat.tra()
                return _loi_thuong_nguon(ma, than)
            # 🔴 SUẤT ĐƯỢC TRẢ KHI LUỒNG HẾT, KHÔNG PHẢI KHI HÀM NÀY VỀ.
            #    `StreamingResponse` trả về ngay lập tức; token còn chảy hàng chục
            #    giây sau đó. Trả suất ở đây là đo đồng thời bằng "số lần bấm nút"
            #    chứ không phải "số lượt đang chạy", và chốt thành vô nghĩa đúng
            #    lúc cần nó nhất.
            # 🔴 DON DEP KHONG DUOC PHU THUOC VAO VIEC GENERATOR CHAY.
            #
            #    `boc_luong` tra suat trong `finally`, va do la dung — nhung mot
            #    `finally` chi ton tai SAU khi generator chay dong dau tien. Neu
            #    Starlette khong bao gio lap qua no (khach da ngat truoc khi byte
            #    dau chay), khoi `try` chua tung duoc vao, `finally` khong chay,
            #    va suat bi giu VINH VIEN.
            #
            # ⛔ Do la nguyen nhan su co 31/08: mot suat treo, `max_dong_thoi=1`,
            #    cong tra 429 suot SAU GIO trong khi GPU ranh va model chua nap.
            #    89/117 luot cua mot khach hong. Ba phep kiem cua `boc_luong` deu
            #    goi `next(g)` truoc, nen khong phep nao cham trang thai nay.
            #
            # ⭐ `BackgroundTask` chay khi PHAN HOI ket thuc, ke ca khi than chua
            #    tung duoc doc — nen no phu dung khe ho ay. Day cung la khuon ma
            #    may A DA dung dung cho ve admission (`server/api/streaming.py`),
            #    chi la chua duoc mang sang day.
            #
            # `Suat.tra()` va `dong()` deu idempotent, nen lop nay CONG THEM chu
            # khong thay the `finally` — hai duong doc lap cho cung mot viec.
            dong_thuong_nguon = getattr(luong, "dong", None)

            def _don_dep() -> None:
                try:
                    suat.tra()
                finally:
                    if dong_thuong_nguon is not None:
                        dong_thuong_nguon()

            luong = boc_nhip_tim(luong, moi_giay=cfg.nhip_tim_giay)
            return StreamingResponse(boc_luong(luong, suat), status_code=ma,
                                     media_type=ct,
                                     headers={"X-LTT-Token-Vao": str(do.token_vao)},
                                     background=BackgroundTask(_don_dep))

        try:
            ma, thu = upstream.json("POST", duong, body=body,
                                    timeout=cfg.upstream_timeout_s)
        finally:
            suat.tra()
        if ma >= 500:
            return _loi_thuong_nguon(ma, thu)
        return Response(content=thu, status_code=ma, media_type="application/json",
                        headers={"X-LTT-Token-Vao": str(do.token_vao)})

    def _loi_thuong_nguon(ma: int, thu: bytes) -> JSONResponse:
        """llama-swap/llama-server hỏng hoặc không với tới được.

        ⚠️ Trả **502**, và **không** trả 429. Đây là hỏng thật, máy A **nên** đánh
        dấu lỗi cho key ở đây — khác hẳn trường hợp bận ở trên.
        """
        log.error("thuong nguon loi ma=%s: %s", ma, thu[:300])
        return JSONResponse(status_code=502,
                            content={"ly_do": "thuong nguon khong phuc vu duoc",
                                     "ma_thuong_nguon": ma,
                                     "chi_tiet": thu[:500].decode("utf-8", "replace")})

    @app.post("/v1/chat/completions")
    def chat(body: dict = Body(...), _: None = Depends(auth)) -> Response:
        return _chuyen_tiep("chat", body)

    @app.post("/v1/responses")
    def responses(body: dict = Body(...), _: None = Depends(auth)) -> Response:
        return _chuyen_tiep("responses", body)

    @app.post("/v1/messages")
    def messages(body: dict = Body(...), _: None = Depends(auth)) -> Response:
        return _chuyen_tiep("messages", body)

    return app

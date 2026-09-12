"""
api.py — hợp đồng HTTP của cổng render.

    GET  /health                    GPU · RAM · ComfyUI sống không · bận không · eta
    GET  /v1/models                 model + chế độ + bucket + trần ảnh tham chiếu
    POST /v1/images/generations     nhận việc, trả {job_id} NGAY
    GET  /v1/jobs/{job_id}          trạng thái + kết quả
    POST /v1/jobs/{job_id}/cancel   huỷ ĐÚNG job đó
    POST /v1/exclusive              chế độ độc chiếm cho lúc dự án video benchmark
    POST /v1/nha_comfy              dừng / chạy lại LTTComfyUI (lệnh residency 3090)

⭐ `/v1/nha_comfy` LÀ MỘT LỆNH, KHÔNG PHẢI MỘT QUYẾT ĐỊNH. Người quyết khi nào
   3090 thuộc về LLM và khi nào thuộc về ảnh là **trọng tài residency ở máy A**
   (Task 5.5, TD-D10) — nơi duy nhất thấy cùng lúc lease LLM, phòng chờ và hàng
   job ảnh. Cổng này chỉ thi hành và **báo lại sự thật đo được**. Đừng thêm một
   người quyết thứ hai ở đây: hai cơ chế cùng canh một card là hai chỗ khai cùng
   một điều, và chúng sẽ lệch nhau.

⛔ BẬN THÌ TRẢ **429**, KHÔNG PHẢI LỖI. Máy A phân biệt hai thứ này: 429 là trạng
   thái bình thường của một máy chia GPU với việc video; nếu máy A hiểu nhầm thành
   lỗi thì `api_pool` sẽ cooldown rồi `disable` key `ltt_local` sau 5 lần, và **một
   tối chạy video sẽ tự tắt vĩnh viễn model nhà**. Đó là cạm bẫy ghi ở D-005.

⛔ KHÔNG TỰ ĐỔI SANG MODEL KHÁC. Cổng này chỉ biết model nhà. Việc "bận thì dùng
   đám mây" là **quyết định của khách trên máy A** (D-010), không phải của cổng.

⛔ Đồng bộ hoá: chỉ MỘT việc chạy một lúc (`max_concurrent = 1`). Đó không phải
   tham số hiệu năng — video đã đo đỉnh VRAM 24.251/24.576 MiB, nên hai việc cùng
   lúc là OOM chắc chắn.
"""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import __version__, tren_gpu
from . import dich_vu_comfy as DV
from . import jobs as J
from .busy import BusyWatcher
from .catalog import ModelSpec, nap_catalog
from .comfy import ComfyClient
from .config import Config
from .runner import RenderRequest, Runner
from .storage_io import RefSpec

log = logging.getLogger("render_gateway.api")


class GenerateBody(BaseModel):
    job_id: str = Field(min_length=1, max_length=128)
    model: str
    mode: str = "t2i"
    prompt: str = ""
    negative_prompt: str = ""
    refs: list[dict] = Field(default_factory=list)
    put_urls: list[str] = Field(default_factory=list)
    image_keys: list[str] = Field(default_factory=list)
    content_type: str = "image/png"
    #: Ghi đè `defaults` của model. Thiếu thì lấy default — chất lượng-trên-hết
    #: nghĩa là default phải là cấu hình ĐẸP NHẤT, không phải cấu hình nhanh nhất.
    params: dict[str, Any] = Field(default_factory=dict)


class ExclusiveBody(BaseModel):
    on: bool
    reason: str = ""
    ttl_s: float = 7200.0


class NhaComfyBody(BaseModel):
    """Thân của `/v1/nha_comfy`. Thiếu thân ⇒ `dung` (dọn card cho LLM)."""
    #: `"dung"` = tắt ComfyUI để trả VRAM 3090; `"chay"` = bật lại trước cửa sổ ảnh.
    hanh_dong: str = "dung"


def create_app(cfg: Config, comfy: ComfyClient, *,
               workflow_dir: Optional[Path] = None,
               now=time.monotonic, sleep=time.sleep,
               fetcher=None, doc_vram_mb=None, dem_python_gpu=None,
               chay_dich_vu=None) -> FastAPI:
    app = FastAPI(title="LTT Render Gateway", version=__version__)

    store = J.JobStore(now=now)
    # Hai nguồn GPU tiêm được để test không đọc card của máy đang chạy test.
    # Cả hai mặc định hỏi `nvidia-smi` — KHÔNG phải `/system_stats`, vì nguồn đó
    # mù với tiến trình khác trên Windows/WDDM (đã đo, xem `busy.py`).
    #
    # ⭐ `co_ho_bao_duoc` KHÔNG còn được truyền, và đó là một quyết định: nó mở
    #    nhánh "card đang bị giữ nhưng ta lấy lại được, nên đừng báo bận". Từ
    #    Task 5.4 cổng render **không** còn cách nào lấy lại card — quyền ấy về
    #    trọng tài residency ở máy A. Để nhánh đó mở là báo rảnh trong khi 3090
    #    vẫn nằm dưới LTT-3.8, tức mời một lần OOM. Mặc định của `BusyWatcher` là
    #    `False`, tức chốt VRAM giữ nguyên hiệu lực — đúng chiều an toàn.
    watcher = BusyWatcher(comfy=comfy,
                          ram_trong_toi_thieu_gb=cfg.ram_trong_toi_thieu_gb, now=now,
                          **({"doc_vram_mb": doc_vram_mb} if doc_vram_mb else {}),
                          **({"dem_python_gpu": dem_python_gpu} if dem_python_gpu else {}))
    catalog: dict[str, ModelSpec] = nap_catalog(workflow_dir)
    slot = threading.BoundedSemaphore(max(1, cfg.max_concurrent))
    #: Bộ chạy lệnh dịch vụ, tiêm được để test không đụng SCM thật.
    chay_sc = chay_dich_vu or DV.chay_that

    # ── LỆNH RESIDENCY: dọn VRAM 3090 cho LLM ─────────────────────
    # Thân lệnh ở `dich_vu_comfy.py`; ở đây chỉ còn hai việc: nối nó vào HTTP và
    # **xác minh bằng VRAM của đúng card 3090** rồi báo lại số đo thật.
    def _vram() -> Optional[int]:
        return watcher.doc_vram_mb()

    #: Driver không trả VRAM lại **ngay** lúc tiến trình thoát — WDDM thu hồi sau
    #: một nhịp. Đọc một lần rồi kết luận "không tụt" là biến một độ trễ vài giây
    #: thành một báo lỗi sai, và trọng tài sẽ coi card là bẩn vĩnh viễn.
    VRAM_CHO_HA_GIAY = 15.0
    VRAM_NHIP_GIAY = 1.0

    def _cho_vram_ha(truoc: Optional[int]) -> Optional[int]:
        """Đọc lại VRAM 3090 tới khi nó **thấp hơn `truoc`**, có hạn.

        Trả về số đọc được cuối cùng (`None` = không đọc được lần nào). Hết hạn
        mà chưa tụt thì trả đúng số cuối — người gọi chịu trách nhiệm gọi đó là
        thất bại, chứ hàm này không tự nói dối theo chiều nào.
        """
        t0 = now()
        sau = _vram()
        while True:
            if sau is not None and (truoc is None or sau < truoc):
                return sau
            if now() - t0 >= VRAM_CHO_HA_GIAY:
                return sau
            sleep(VRAM_NHIP_GIAY)
            sau = _vram()

    if fetcher is None:                       # pragma: no cover - đường sản xuất
        from .http import HttpxFetcher
        fetcher = HttpxFetcher()

    runner = Runner(comfy, store, fetcher, input_dir=cfg.comfy_input_dir,
                    timeout_s=cfg.job_timeout_s, now=now, sleep=sleep,
                    workflow_dir=workflow_dir)

    def auth(authorization: str = Header(default="")) -> None:
        if not cfg.token:
            return           # dev: chưa đặt token → không chặn (giống codex_sidecar)
        if authorization != f"Bearer {cfg.token}":
            raise HTTPException(status_code=401, detail="render gateway: sai token")

    # ── sức khoẻ ─────────────────────────────────────────────────────────────
    @app.get("/live")
    def live() -> dict:
        """Sống/chết. **KHÔNG cần khoá**, và cố ý không nói gì thêm.

        Một phép thăm dò sống/chết không nên phải mang theo bí mật, và không nên
        đọc được trạng thái vận hành (VRAM, hàng đợi, model nào có). Cổng VLM đã
        làm đúng như vậy; đây là cùng một hợp đồng cho cổng ảnh.

        Vì sao cần: máy A không có cách nào biết cổng ảnh chết. Trước cái này,
        đường duy nhất là có khách thử vẽ rồi thấy hỏng.
        """
        return {"ok": True, "version": __version__}

    @app.get("/health")
    def health(_: None = Depends(auth)) -> dict:
        state = watcher.observe(store.active_prompt_ids())
        # ⭐ Cổng SỐNG mà model vẫn có thể đang bò trên CPU — hai câu hỏi khác
        #    nhau, nên hai chốt khác nhau. Xem `tren_gpu.py`.
        gpu = tren_gpu.kiem(giay_dang_chay=store.chay_lau_nhat_s(),
                            doc_vram=watcher.doc_vram_mb)
        return {
            "version": __version__,
            "comfy_alive": comfy.alive(),
            "models": sorted(catalog),
            "gpu": gpu.as_dict(),
            **state.as_dict(),
        }

    @app.get("/v1/models")
    def models(_: None = Depends(auth)) -> dict:
        # Khuôn `{"data": [...]}` để `providers_live.parse_models` của nền tảng đọc
        # được mà không phải thêm nhánh phân tích mới.
        return {"data": [m.public() for m in catalog.values()]}

    # ── nhận việc ────────────────────────────────────────────────────────────
    @app.post("/v1/images/generations")
    def generate(body: GenerateBody, _: None = Depends(auth)):
        spec = catalog.get(body.model)
        if spec is None:
            raise HTTPException(400, f"khong biet model {body.model!r}")
        mode = spec.modes.get(body.mode)
        if mode is None:
            raise HTTPException(
                400, f"model {body.model} khong co che do {body.mode!r} "
                     f"(co: {', '.join(sorted(spec.modes))})")
        if len(body.refs) > spec.max_refs:
            raise HTTPException(
                400, f"toi da {spec.max_refs} anh tham chieu cho model nay — "
                     f"them nua thi moi anh bi thu nho, chat luong giam")
        if not body.put_urls:
            raise HTTPException(400, "thieu put_urls: may A phai cap ve PUT")

        # Job đã biết → trả ngay, không xếp hàng lần hai (idempotency).
        co = store.get(body.job_id)
        if co is not None:
            return JSONResponse({"job_id": co.job_id, "status": co.status}, status_code=200)

        def ban(thong_diep: str, them: dict, retry_s: Optional[float] = None):
            """⛔ 429 = BẬN, KHÔNG PHẢI LỖI. Xem docstring đầu file (D-005)."""
            headers = {"Retry-After": str(int(max(1, retry_s)))} if retry_s else {}
            return JSONResponse(
                {"error": {"code": "busy", "message": thong_diep or "dang ban"},
                 **them},
                status_code=429, headers=headers)

        # ── HAI CHỐT, THEO THỨ TỰ NÀY ──────────────────────────
        #
        # ① giữ SUẤT trước — hai yêu cầu đồng thời không được cùng vào vẽ;
        # ② rồi mới hỏi BẬN.
        #
        # ⛔ CHỐT THỨ BA ĐÃ BỊ GỠ (Task 5.4): "xin card" — đuổi hộ đang giữ 3090
        #    rồi chờ VRAM xuống. Nó đi vì một lý do cơ học chứ không phải vì gọn hơn:
        #    đường đuổi của nó (`GET /unload` của llama-swap) **không mang tên model**
        #    và **không drain**, nên từ khi máy B có hai model nó nhả cả LTT-3.5 trên
        #    card không ai tranh, và giết một lượt đang sinh chữ (L-17, L-9).
        #
        # ⭐ Thay vào đó: **trọng tài residency ở máy A** mở cửa sổ ảnh trước, rồi mới
        #    gửi job tới đây. Khi lệnh vẽ tới, 3090 đã là của ảnh. Cổng này chỉ còn
        #    phải trả lời một câu — *bây giờ vẽ được không* — và 429 khi không.
        #
        # ⚠️ Mọi đường thoát từ đây trở xuống PHẢI `slot.release()`. Thiếu một chỗ
        #    thì mỗi lượt rò một suất, và sau `max_concurrent` lượt cổng **không
        #    nhận job nào nữa dù card rảnh** — hỏng lặng lẽ.
        if not slot.acquire(blocking=False):
            return ban("het suat dong thoi", {})

        state = watcher.observe(store.active_prompt_ids())
        if state.busy:
            slot.release()
            return ban(state.reason, dict(state.as_dict()), state.eta_s)

        gia_tri = dict(spec.defaults)
        gia_tri.update(body.params)
        gia_tri.setdefault("prompt", body.prompt)
        gia_tri.setdefault("negative", body.negative_prompt)
        gia_tri["prompt"] = body.prompt
        gia_tri["negative"] = body.negative_prompt

        req = RenderRequest(
            job_id=body.job_id, template=mode.template, values=gia_tri,
            refs=[RefSpec(str(r.get("url") or ""), str(r.get("role") or "edit"))
                  for r in body.refs],
            put_urls=list(body.put_urls), image_keys=list(body.image_keys),
            content_type=body.content_type, ref_slots=list(mode.ref_slots),
        )

        def chay() -> None:
            try:
                runner.run(req)
            finally:
                slot.release()

        threading.Thread(target=chay, name=f"render-{body.job_id}", daemon=True).start()
        return JSONResponse({"job_id": body.job_id, "status": J.QUEUED}, status_code=202)

    # ── trạng thái việc ──────────────────────────────────────────────────────
    @app.get("/v1/jobs/{job_id}")
    def job_status(job_id: str, _: None = Depends(auth)) -> dict:
        job = store.get(job_id)
        if job is None:
            raise HTTPException(404, "khong co job nay")
        return job.as_dict()

    @app.post("/v1/jobs/{job_id}/cancel")
    def job_cancel(job_id: str, _: None = Depends(auth)) -> dict:
        job = store.get(job_id)
        if job is None:
            raise HTTPException(404, "khong co job nay")
        if job.status in J.KET_THUC:
            return job.as_dict()
        # Huỷ ĐÚNG prompt của job này. `interrupt` không kèm id sẽ giết lượt đang
        # chạy — có thể là lượt video của dự án khác.
        try:
            comfy.interrupt(job.prompt_id)
        except Exception as e:                                   # noqa: BLE001
            log.warning("huy job %s that bai: %s", job_id, e)
        return (store.set_status(job_id, J.CANCELLED) or job).as_dict()

    # ── độc chiếm ────────────────────────────────────────────────────────────
    @app.post("/v1/exclusive")
    def exclusive(body: ExclusiveBody, _: None = Depends(auth)) -> dict:
        watcher.doc_chiem(bat=body.on, ly_do=body.reason, het_han_s=body.ttl_s)
        return {"exclusive": body.on, "reason": body.reason, "ttl_s": body.ttl_s}

    # ── lệnh residency: dọn / trả lại card cho ComfyUI ───────────────────────
    @app.post("/v1/nha_comfy")
    def nha_comfy(body: Optional[NhaComfyBody] = None, _: None = Depends(auth)):
        """Làm cho VRAM 3090 **sạch** cho LLM — hoặc bật ComfyUI trở lại.

        🔴 TÊN LỆNH GIỮ THEO PLAN, NGHĨA THÌ KHÔNG. Bản plan viết *"gọi ComfyUI
           `/free {unload_models, free_memory}`"*. Đo 12/09 (L-14 §3) nói `/free`
           **không** nhả 223,5 MiB ngữ cảnh CUDA của một ComfyUI ấm, và biên của
           LTT-3.8 ở `-c 221184` chỉ **445 MiB** — nên `/free` để lại **một nửa
           biên** trong tay một tiến trình không làm gì. Chỉ **dừng dịch vụ** mới
           trả nó về. Task 5.5 khớp **chuỗi** `free_comfy`, nên tên ở lại; việc
           nó làm là dừng `LTTComfyUI`.

        ⛔ VÀ NÓ KHÔNG GIẾT VIỆC CỦA AI. Chỉ thu hồi bộ nhớ **của chính ComfyUI**,
           và chỉ được phát ở trạng thái `TRA_ANH` — sau khi cửa nhận job ảnh đã
           đóng và không còn lượt vẽ nào chạy (L-9). Cổng này **không** tự quyết.

        ⛔ THÀNH CÔNG IM LẶNG LÀ KẾT CỤC TỆ NHẤT, nên mọi đường ra đều có bằng
           chứng: hoặc `da_dung=true` kèm VRAM 3090 **đo lại** và đã tụt, hoặc
           **503** kèm lý do đọc được. Một bước residency tưởng đã dọn card mà
           thật ra chưa dọn chính là hỏng mà D01 B sinh ra để chặn.
        """
        hd = ((body.hanh_dong if body else "") or "dung").strip().lower()
        if hd not in ("dung", "chay"):
            raise HTTPException(400, "hanh_dong phai la 'dung' hoac 'chay'")
        ten = DV.ten_dich_vu()

        def _loi(thong_diep: str, them: dict):
            # ⚠️ 5xx ở ĐÂY là đúng, khác hẳn `/v1/images/generations`. Cạm bẫy
            #    D-005 (5xx ⇒ `api_pool` disable key) nói về đường **khách** đi
            #    qua `api_pool`. Lệnh này do trọng tài residency gọi thẳng, và nó
            #    **cần** thấy thất bại: nuốt nó đi là để máy A tưởng card đã sạch.
            log.error("nha_comfy(%s) that bai: %s", hd, thong_diep)
            return JSONResponse(
                {"error": {"code": "nha_comfy_that_bai", "message": thong_diep},
                 "hanh_dong": hd, "dich_vu": ten, **them},
                status_code=503)

        if hd == "chay":
            px = DV.chay_lai(ten, chay=chay_sc, now=now, ngu=sleep)
            if not px.xong:
                return _loi(px.ly_do, {"dich_vu_trang_thai": px.as_dict()})
            return {"hanh_dong": "chay", "dich_vu": ten, "dang_chay": True,
                    "vram_3090_mib": _vram(),
                    "dich_vu_trang_thai": px.as_dict()}

        truoc = _vram()
        px = DV.dung(ten, chay=chay_sc, now=now, ngu=sleep)
        if not px.xong:
            return _loi(px.ly_do, {"dich_vu_trang_thai": px.as_dict(),
                                   "vram_3090_mib": truoc})

        # ── XÁC MINH BẰNG CARD, KHÔNG BẰNG LỜI CỦA SCM ──────────────────────
        # `cai_dat_dich_vu.ps1` đã ghi đúng cạm bẫy này: python launcher của máy B
        # là một **stub**, nên giết mỗi tiến trình cha thì SCM nói "Stopped" trong
        # khi ComfyUI thật vẫn sống và vẫn ôm VRAM (đo 22/08: 3,8 MB → 2.265 MB).
        # Lời dặn ở đó là *"KHONG TIN, HAY DO"* — đây là chỗ nó thành cơ chế.
        #
        # ⭐ Số đọc ra là VRAM của **đúng UUID 3090** (`busy._o_cua_card_3090` →
        #    `danh_tinh_gpu.uuid_38`), không phải `max()` của cả máy: LTT-3.5
        #    thường trú ~10 GB trên 5060 Ti, và một phép đo gộp sẽ luôn nói
        #    "card vẫn bẩn".
        if px.truoc == DV.DUNG:
            # Vốn đã dừng từ trước ⇒ không có gì để tụt. Vẫn báo số đo.
            return {"hanh_dong": "dung", "dich_vu": ten, "da_dung": True,
                    "vram_3090_mib": _vram(), "vram_3090_mib_truoc": truoc,
                    "dich_vu_trang_thai": px.as_dict()}

        sau = _cho_vram_ha(truoc)
        if sau is None:
            return _loi(
                f"da dung {ten} nhung KHONG doc duoc VRAM cua card 3090 — khong "
                f"the xac minh card da sach. Kiem `nvidia-smi` va "
                f"`gpu_may_b.json` tren may B.",
                {"dich_vu_trang_thai": px.as_dict(), "vram_3090_mib": None})
        if truoc is not None and sau >= truoc:
            return _loi(
                f"dich vu {ten} bao da dung nhung VRAM 3090 khong ha "
                f"({truoc} -> {sau} MiB). Gan nhu chac chan tien trinh ComfyUI "
                f"THAT van song (python launcher la stub — xem cai_dat_dich_vu.ps1).",
                {"dich_vu_trang_thai": px.as_dict(), "vram_3090_mib": sau,
                 "vram_3090_mib_truoc": truoc})

        log.info("nha_comfy: da dung %s, VRAM 3090 %s -> %s MiB", ten, truoc, sau)
        return {"hanh_dong": "dung", "dich_vu": ten, "da_dung": True,
                "vram_3090_mib": sau, "vram_3090_mib_truoc": truoc,
                "dich_vu_trang_thai": px.as_dict()}

    app.state.store = store
    app.state.watcher = watcher
    app.state.catalog = catalog
    return app

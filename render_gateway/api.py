"""
api.py — hợp đồng HTTP của cổng render.

    GET  /health                    GPU · RAM · ComfyUI sống không · bận không · eta
    GET  /v1/models                 model + chế độ + bucket + trần ảnh tham chiếu
    POST /v1/images/generations     nhận việc, trả {job_id} NGAY
    GET  /v1/jobs/{job_id}          trạng thái + kết quả
    POST /v1/jobs/{job_id}/cancel   huỷ ĐÚNG job đó
    POST /v1/exclusive              chế độ độc chiếm cho lúc dự án video benchmark

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

from . import __version__
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


def create_app(cfg: Config, comfy: ComfyClient, *,
               workflow_dir: Optional[Path] = None,
               now=time.monotonic, sleep=time.sleep,
               fetcher=None, doc_vram_mb=None, dem_python_gpu=None) -> FastAPI:
    app = FastAPI(title="LTT Render Gateway", version=__version__)

    store = J.JobStore(now=now)
    # Hai nguồn GPU tiêm được để test không đọc card của máy đang chạy test.
    # Cả hai mặc định hỏi `nvidia-smi` — KHÔNG phải `/system_stats`, vì nguồn đó
    # mù với tiến trình khác trên Windows/WDDM (đã đo, xem `busy.py`).
    watcher = BusyWatcher(comfy=comfy,
                          ram_trong_toi_thieu_gb=cfg.ram_trong_toi_thieu_gb, now=now,
                          **({"doc_vram_mb": doc_vram_mb} if doc_vram_mb else {}),
                          **({"dem_python_gpu": dem_python_gpu} if dem_python_gpu else {}))
    catalog: dict[str, ModelSpec] = nap_catalog(workflow_dir)
    slot = threading.BoundedSemaphore(max(1, cfg.max_concurrent))

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
    @app.get("/health")
    def health(_: None = Depends(auth)) -> dict:
        state = watcher.observe(store.active_prompt_ids())
        return {
            "version": __version__,
            "comfy_alive": comfy.alive(),
            "models": sorted(catalog),
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

        state = watcher.observe(store.active_prompt_ids())
        if state.busy or not slot.acquire(blocking=False):
            # ⛔ 429 = BẬN, KHÔNG PHẢI LỖI. Xem docstring đầu file.
            noi_dung = {"error": {"code": "busy", "message": state.reason or "dang ban"},
                        **state.as_dict()}
            headers = {}
            if state.eta_s:
                headers["Retry-After"] = str(int(max(1, state.eta_s)))
            return JSONResponse(noi_dung, status_code=429, headers=headers)

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

    app.state.store = store
    app.state.watcher = watcher
    app.state.catalog = catalog
    return app

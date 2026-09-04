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
import os
import threading
import time
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import __version__, nhuong_card, tren_gpu
from . import busy as busy_mod
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
    # ⚠️ `co_ho_bao_duoc` phải là một HÀM, không phải một giá trị: danh sách hộ
    #    được đọc **bên dưới**, nên một giá trị tính ở đây sẽ luôn là `False`.
    #    Tra cứu muộn cũng đúng hơn về nghĩa — nó hỏi "lúc này có ai bảo được
    #    không", không phải "lúc khởi động có ai".
    watcher = BusyWatcher(comfy=comfy,
                          ram_trong_toi_thieu_gb=cfg.ram_trong_toi_thieu_gb, now=now,
                          co_ho_bao_duoc=lambda: any(h.bao_duoc for h in ho_dung_card),
                          **({"doc_vram_mb": doc_vram_mb} if doc_vram_mb else {}),
                          **({"dem_python_gpu": dem_python_gpu} if dem_python_gpu else {}))
    catalog: dict[str, ModelSpec] = nap_catalog(workflow_dir)
    slot = threading.BoundedSemaphore(max(1, cfg.max_concurrent))

    # ⭐ Hộ dùng chung card, khai bằng `LTT_HO_DUNG_CARD` — **một dòng cấu hình
    #    cho mỗi hộ**, không phải một lần sửa mã. Chủ sản phẩm chốt 24/08 rằng dự
    #    án video sau này đi theo đúng khuôn LLM/ảnh, nên hộ thứ tư là chuyện
    #    *khi nào*, không phải *có hay không*. Xem `nhuong_card.py`.
    ho_dung_card = nhuong_card.doc_ho_tu_env(dict(os.environ))
    if ho_dung_card:
        log.info("ho dung chung card: %s",
                 ", ".join(f"{h.ten}{'' if h.bao_duoc else ' (chi cho duoc)'}"
                           for h in ho_dung_card))

    def _ho_khac_dang_tinh() -> bool:
        """Có hộ KHÁC đang tính trên card không — dùng để **không đuổi** họ.

        🔴 CÂU HỎI NÀY KHÁC "card có bận không". Ở đây ta đã quyết định muốn card;
           thứ cần biết là **đuổi bây giờ có cắt ngang việc của ai không**.

        ⭐ Hai tín hiệu, đúng như `llm_gateway/trong_tai.py` đã đo cho chiều ngược:

             python trên card >= 2      ⇒ có tiến trình khác đang tính
             ComfyUI của TA đang vẽ     ⇒ tải cao là của ta, KHÔNG tính là hộ khác
             còn lại, tải GPU cao       ⇒ `llama-server` đang trả lời ⇒ ĐANG TÍNH

        ⛔ `llama-server.exe` **không phải python**, nên phép đếm python một mình
           mù với nó — đúng lý do `trong_tai` phải ghép thêm mức tải. Không có vế
           tải thì ta sẽ đuổi Qwen ngay giữa một câu trả lời đang chảy.
        """
        so_py = watcher.dem_python_gpu()
        if so_py is not None and so_py >= busy_mod.TRAN_PYTHON_GPU:
            return True
        # ComfyUI của ta đang vẽ ⇒ tải cao là của chính ta, không phải hộ khác.
        if store.active_prompt_ids():
            return False
        tai = busy_mod.tai_gpu_phan_tram()
        return tai is not None and tai >= busy_mod.TAI_GPU_DANG_TINH

    def goi_nha(duong: str) -> bool:
        """Gọi endpoint nhả của một hộ. Hỏng thì trả False, KHÔNG ném.

        Bảo không được có thể chỉ là nó đã nhả sẵn — vòng chờ VRAM trong
        `xin_card` mới là thứ quyết định.
        """
        try:
            import httpx

            r = httpx.get(duong, timeout=20.0)
            return 200 <= r.status_code < 300
        except Exception as exc:                                # noqa: BLE001
            log.info("goi nha %s khong duoc: %s", duong, type(exc).__name__)
            return False

    goi_nha_ho = goi_nha

    # Sổ đuổi: nhớ lần đuổi gần nhất để KHÔNG đuổi liên tục.
    #
    # 🔴 Không có nó thì hai loại việc xen kẽ sẽ làm **mỗi prompt của khách LLM
    #    trả 18 giây nạp lại** — không phải chậm, mà là không dùng được. Xem
    #    `CACH_NHAU_TOI_THIEU_GIAY` trong `nhuong_card.py`.
    #
    # ⚠️ Và nó KHÔNG làm chậm việc thường: một lô ảnh liên tiếp thấy VRAM vẫn
    #    thấp nên đi qua ở nhánh đầu, không đuổi ai, không chạm sổ này.
    so_duoi = nhuong_card.SoDuoi()

    # ── TRẢ CARD (V3) ───────────────────────────────────────────────────────
    # Nhả VRAM của ComfyUI sau khi RẢNH một lúc, để hộ khác nạp được mà không
    # phải chờ ai. Không nhả thì ComfyUI ngồi im mà giữ ~16.600 MB (đo trên máy B
    # lúc GPU 0–1 % tải), và LLM cần 19.237 MB sẽ nạp đè → card lên 23.860 MB và
    # **cả hai** cùng chậm.
    #
    # ⛔ MẶC ĐỊNH TẮT (`LTT_TRA_CARD_GIAY` không đặt ⇒ 0 ⇒ không chạy).
    #    Một vòng nền tự nhả bộ nhớ của người khác là thứ phải được BẬT có chủ ý,
    #    không phải thứ bật sẵn rồi mới phát hiện. Và cài đặt dev không dùng chung
    #    card với ai thì không có gì để trả.
    try:
        _tra_giay = float(os.environ.get("LTT_TRA_CARD_GIAY") or 0)
    except ValueError:
        _tra_giay = 0.0

    if _tra_giay > 0:
        def _free_comfy() -> bool:
            try:
                import httpx

                r = httpx.post(f"{cfg.comfy_url.rstrip('/')}/free", timeout=30.0,
                               json={"unload_models": True, "free_memory": True})
                return 200 <= r.status_code < 300
            except Exception as exc:                            # noqa: BLE001
                log.info("goi ComfyUI /free khong duoc: %s", type(exc).__name__)
                return False

        tra = nhuong_card.TraCard(
            ranh_bao_lau_giay=_tra_giay,
            # ⚠️ Hỏi HÀNG ĐỢI THẬT, không hỏi một cờ nội bộ: một job có thể đang
            #    chạy trong luồng riêng mà cờ đã bị xoá.
            co_viec=lambda: bool(store.active_prompt_ids()),
            goi_free=_free_comfy)

        def _vong_tra_card():
            while True:
                time.sleep(min(10.0, max(1.0, _tra_giay / 6)))
                try:
                    tra.mot_luot()
                except Exception:                               # noqa: BLE001
                    log.exception("vong tra card loi — van chay tiep")

        threading.Thread(target=_vong_tra_card, name="tra-card",
                         daemon=True).start()
        log.info("vong tra card: nha VRAM ComfyUI sau %.0fs ranh", _tra_giay)

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

        # ── THỨ TỰ BA CHỐT DƯỚI ĐÂY LÀ MỘT QUYẾT ĐỊNH, KHÔNG PHẢI TÌNH CỜ ──
        #
        # ① giữ SUẤT trước — hai yêu cầu đồng thời không được cùng đi đuổi model;
        # ② XIN CARD — đuổi hộ bảo-được rồi **xác minh** VRAM đã xuống;
        # ③ mới hỏi BẬN.
        #
        # 🔴 Bản đầu của tôi đặt ② SAU ③, và nó **sai một cách im lặng**: chốt bận
        #    coi "VRAM còn ít" là bận, nên khi Qwen giữ 19 GB thì cổng trả 429
        #    ngay — **không bao giờ đi bảo Qwen nhả**. Tức là trọng tài không bao
        #    giờ chạy, và triệu chứng ("luôn 429") trông y hệt "máy đang bận thật".
        #
        #    Test đầu tiên tôi viết cho nó **xanh vì lý do sai**: nó chạy 0,58 giây
        #    trong khi hạn chờ là 45 giây — bằng chứng `xin_card` chưa hề được gọi.
        if not slot.acquire(blocking=False):
            return ban("het suat dong thoi", {})

        # ── XIN CARD (V1–V2) ────────────────────────────────────────────
        # Gọi nhả rồi nạp luôn là **giả định**; model mới sẽ âm thầm offload sang
        # RAM chủ trong khi mọi chốt vẫn xanh (P6, D-051). Nên `xin_card` **chờ và
        # đọc lại VRAM** trước khi cho qua.
        #
        # ⚠️ Mọi đường thoát từ đây trở xuống PHẢI `slot.release()`. Thiếu một chỗ
        #    thì mỗi lượt rò một suất, và sau `max_concurrent` lượt cổng **không
        #    nhận job nào nữa dù card rảnh** — hỏng lặng lẽ.
        px = nhuong_card.xin_card(ho_khac=ho_dung_card,
                                  doc_vram=watcher.doc_vram_mb,
                                  goi_nha=goi_nha_ho,
                                  dang_tinh=_ho_khac_dang_tinh,
                                  so_duoi=so_duoi)
        if not px.duoc:
            slot.release()
            log.warning("xin card khong duoc: %s", px.ly_do)
            return ban(px.ly_do, {"xin_card": px.as_dict()}, 30)

        # 🔴 GHI LẠI VIỆC ĐUỔI, KỂ CẢ KHI NÓ THÀNH CÔNG.
        #
        #    Bản đầu chỉ log lúc **thất bại**, nên hành động quan trọng nhất của
        #    trọng tài — lấy card khỏi tay một hộ khác — **không để lại dấu vết
        #    nào**. Thử thật 24/08: LLM bị đuổi đúng như thiết kế, và trong log
        #    không có một dòng nào về việc đó.
        #
        #    Hệ quả: khi ai đó hỏi *"vì sao phiên LLM của tôi chậm lúc 13:50"* thì
        #    không có gì chỉ ra được. Một hệ thống đuổi việc của người khác mà
        #    không ghi lại là một hệ thống không giải thích được chính nó.
        if px.da_bao_nha:
            log.info("job %s: da bao %s nha card, cho %.1fs, VRAM con %s MB",
                     body.job_id, ", ".join(px.da_bao_nha), px.giay_da_cho,
                     px.vram_mb)
        elif px.giay_da_cho >= 1.0:
            # Không đuổi ai mà vẫn phải chờ ⇒ có hộ chỉ-chờ-được vừa nhả. Cũng
            # đáng ghi: nó là bằng chứng cho việc tranh card mà ta không gây ra.
            log.info("job %s: khong duoi ai nhung cho %.1fs cho card trong "
                     "(VRAM con %s MB)", body.job_id, px.giay_da_cho, px.vram_mb)

        state = watcher.observe(store.active_prompt_ids())
        if state.busy:
            slot.release()
            return ban(state.reason, {**state.as_dict(), "xin_card": px.as_dict()},
                       state.eta_s)

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

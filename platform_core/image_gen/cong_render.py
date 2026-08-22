"""
cong_render.py — client phía MÁY A gọi cổng render trên máy B. (H37/G8)

⭐ Đây là phía đối diện của `render_gateway/api.py`. Nó **không** biết gì về
   ComfyUI, workflow hay GPU — chỉ biết một HTTP API nhỏ, và biết ba luật mà dự án
   đã trả giá để học.

⛔ LUẬT 1 — **429 LÀ BẬN, KHÔNG PHẢI HỎNG.** Máy B dùng chung GPU với dự án video.
   Một tối chạy video là hàng chục lượt 429. Nếu coi 429 là lỗi provider thì
   `api_pool.danh_dau_loi()` sẽ cooldown rồi **`disable` key sau 5 lần** — và model
   nhà tự tắt vĩnh viễn chỉ vì hàng xóm đang bận. Đây là cạm bẫy đã ghi thành cảnh
   báo thường trực trong `CLAUDE.md`.
   ⇒ `BanError` là một lớp NGOẠI LỆ RIÊNG, không phải `CongRenderError`.

⛔ LUẬT 2 — **KHÔNG TỰ CHUYỂN SANG ĐÁM MÂY.** Khi máy B bận, quyết định "chờ hay
   dùng Gemini" là của **khách**, không phải của tầng này (D-010: đổi model sau
   lưng khách là đánh tráo sản phẩm). Client chỉ báo bận **kèm ETA** rồi thôi.

⛔ LUẬT 3 — **JOB_ID LÀ CỦA MÁY A, VÀ PHẢI ỔN ĐỊNH.** Cổng dùng nó làm khoá
   idempotency: gửi lại cùng `job_id` thì cổng trả job cũ chứ không vẽ lần hai
   (D-018 — bản đầu thiếu chốt này và đốt ~100 giây GPU mỗi lần gửi lại).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

log = logging.getLogger(__name__)

#: Trạng thái job, khớp `render_gateway/jobs.py`. Máy A phân nhánh theo chuỗi này.
QUEUED = "queued"
PREPARING = "preparing"
GENERATING = "generating"
SAVING = "saving"
COMPLETED = "completed"
FAILED = "failed"
XONG = (COMPLETED, FAILED)

#: Không biết còn bao lâu thì coi như LÂU. Không bao giờ lạc quan (luật của busy.py).
ETA_KHONG_BIET = None


class CongRenderError(Exception):
    """Cổng render hỏng thật. Bên gọi ĐƯỢC quyền tính đây là lỗi provider."""


class BanError(Exception):
    """Máy B đang bận. **KHÔNG PHẢI LỖI** — đừng đánh dấu lỗi cho key.

    `eta_s` là ước tính còn bao lâu; `None` nghĩa là *không biết*, và không biết
    thì phải coi là lâu.
    """

    def __init__(self, ly_do: str, eta_s: Optional[float] = None, chi_tiet: Optional[dict] = None):
        super().__init__(ly_do or "may B dang ban")
        self.ly_do = ly_do
        self.eta_s = eta_s
        self.chi_tiet = chi_tiet or {}


@dataclass(frozen=True)
class TrangThaiJob:
    job_id: str
    status: str
    image_keys: tuple = ()
    error_code: str = ""
    error_message: str = ""

    @property
    def xong(self) -> bool:
        return self.status in XONG

    @property
    def thanh_cong(self) -> bool:
        return self.status == COMPLETED


@dataclass
class CongRender:
    """`goi` là hàm HTTP tiêm được: `goi(method, path, json=None) -> (status, body)`.

    Tiêm thay vì gọi thẳng `httpx` để test chạy được trên máy A **không cần máy B**
    — cùng cách `render_gateway` tự test chính nó.
    """
    goi: Callable[..., tuple]
    #: Trần thời gian cho một lượt HTTP. Không phải trần cho cả job.
    timeout_s: float = 30.0

    # ── đọc trạng thái máy ───────────────────────────────────────────────────
    def health(self) -> dict:
        ma, than = self._goi("GET", "/health")
        if ma != 200:
            raise CongRenderError(f"health tra {ma}")
        return than or {}

    def models(self) -> list:
        ma, than = self._goi("GET", "/v1/models")
        if ma != 200:
            raise CongRenderError(f"/v1/models tra {ma}")
        return list((than or {}).get("data") or [])

    def dang_ban(self) -> tuple:
        """`(ban, ly_do, eta_s)` — hỏi trước khi gửi việc, để UI nói được với khách.

        Không thay thế việc bắt `BanError`: giữa lúc hỏi và lúc gửi, dự án video
        có thể vừa bắt đầu một lượt.
        """
        try:
            h = self.health()
        except CongRenderError:
            return True, "khong lien lac duoc voi may B", ETA_KHONG_BIET
        return bool(h.get("busy")), str(h.get("reason") or ""), h.get("eta_s")

    # ── gửi việc ─────────────────────────────────────────────────────────────
    def gui(self, *, job_id: str, model: str, mode: str, prompt: str,
            put_urls, image_keys=(), negative_prompt: str = "",
            refs=(), params: Optional[dict] = None,
            content_type: str = "image/png") -> TrangThaiJob:
        """Gửi một job. Ném `BanError` khi máy bận, `CongRenderError` khi hỏng thật.

        ⛔ `put_urls` là **presigned PUT của máy A**. Máy B không giữ khoá R2 nào
        (Q102) — nó chỉ được đẩy ảnh lên đúng những URL này.
        """
        if not job_id:
            raise CongRenderError("thieu job_id — no la khoa idempotency")
        if not put_urls:
            raise CongRenderError("thieu put_urls — may B khong tu ghi duoc vao R2")

        than_gui = {
            "job_id": job_id, "model": model, "mode": mode, "prompt": prompt,
            "negative_prompt": negative_prompt,
            "put_urls": list(put_urls), "image_keys": list(image_keys),
            "refs": [dict(r) for r in refs], "params": dict(params or {}),
            "content_type": content_type,
        }
        ma, than = self._goi("POST", "/v1/images/generations", json=than_gui)

        if ma == 429:
            # ⛔ ĐÂY là chỗ luật 1 sống. Không nâng thành lỗi, không đổi provider.
            loi = (than or {}).get("error") or {}
            raise BanError(str(loi.get("message") or "dang ban"),
                           (than or {}).get("eta_s"), than or {})
        if ma in (200, 202):
            return TrangThaiJob(job_id, str((than or {}).get("status") or QUEUED))
        raise CongRenderError(f"gui job tra {ma}: {_gon(than)}")

    def trang_thai(self, job_id: str) -> TrangThaiJob:
        ma, than = self._goi("GET", f"/v1/jobs/{job_id}")
        if ma == 404:
            raise CongRenderError(f"may B khong biet job {job_id}")
        if ma != 200:
            raise CongRenderError(f"/v1/jobs tra {ma}")
        t = than or {}
        return TrangThaiJob(
            job_id=str(t.get("job_id") or job_id),
            status=str(t.get("status") or ""),
            image_keys=tuple(t.get("image_keys") or ()),
            error_code=str(t.get("error_code") or ""),
            error_message=str(t.get("error_message") or ""),
        )

    def huy(self, job_id: str) -> bool:
        ma, _ = self._goi("POST", f"/v1/jobs/{job_id}/cancel")
        return ma == 200

    # ── nội bộ ───────────────────────────────────────────────────────────────
    def _goi(self, method: str, path: str, json: Optional[dict] = None) -> tuple:
        try:
            return self.goi(method, path, json=json, timeout=self.timeout_s)
        except Exception as e:                                    # noqa: BLE001
            # Mạng LAN đứt, máy B tắt, tường lửa đổi — đều là "hỏng thật", nhưng
            # KHÔNG được để lọt ra dạng ngoại lệ lạ làm worker chết.
            raise CongRenderError(f"{method} {path}: {type(e).__name__}: {e}") from e


def _gon(than: Any) -> str:
    return str(than)[:200]

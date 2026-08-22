"""
comfy.py — client HTTP tới ComfyUI.

⭐ MỌI HỢP ĐỒNG DƯỚI ĐÂY ĐỌC TỪ MÃ NGUỒN ComfyUI 0.30.0 (commit ghim `6f7cd7f`),
   không phải suy đoán:

   POST /prompt              body {prompt, client_id, prompt_id}  → {prompt_id, number, node_errors}
                             (`script_examples/websockets_api_example.py` — **client
                             ĐƯỢC PHÉP tự đặt `prompt_id`**, đó là nền của idempotency)
   GET  /prompt              → {exec_info: {queue_remaining: N}}     (`server.py:747`)
   GET  /queue               → {queue_running: [...], queue_pending: [...]} (`server.py:1064`)
   GET  /history/{prompt_id} → {<prompt_id>: {outputs: {<node>: {images: [...]}}}}
   GET  /view?filename=&subfolder=&type=  → bytes ảnh
   POST /interrupt           body {prompt_id}  → **huỷ ĐÚNG một prompt** (`server.py:1160`)
   POST /free                body {unload_models, free_memory}       (`server.py:1192`)
   GET  /object_info         → mọi node đang có (dùng để kiểm workflow trước khi gửi)
   GET  /system_stats        → devices[].vram_total/vram_free, ram_total/ram_free

⛔ PHÁT HIỆN QUAN TRỌNG — vì sao KHÔNG dùng websocket:
   `progress`, `executing`, `executed`, `execution_error` đều gửi kèm
   `server.client_id` (`execution.py:436/496/536/578`, `main.py:450`) — tức **chỉ
   tới client đã gửi prompt đó**. Chỉ `status` là quảng bá (`server.py:1397`).
   ⇒ Cổng này **không thể** nghe tiến độ của việc VIDEO do dự án khác gửi.
   Thiết kế ước tính ETA bằng websocket (bản đầu của `CHIA_GPU_VOI_VIDEO.md` §3)
   KHÔNG chạy được. ETA cho việc lạ phải suy từ **lịch sử thời lượng**, xem `busy.py`.
   Ta cũng bỏ luôn websocket cho job của chính mình: `/history` là đủ, và bớt được
   một phụ thuộc cùng cả một lớp lỗi kết nối lại.

⛔ `POST /interrupt` có tham số `prompt_id` ⇒ **luôn truyền nó**. Gọi `/interrupt`
   trống sẽ giết lượt đang chạy — có thể là một lượt video 70 phút của dự án khác.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Optional, Protocol

#: Không gian tên cố định để `job_id` của nền tảng → `prompt_id` ổn định.
#: Ổn định là điều kiện của idempotency: gửi lại cùng job thì ComfyUI thấy cùng id,
#: và sau khi cổng khởi động lại ta vẫn tra được kết quả cũ trong `/history`.
PROMPT_NAMESPACE = uuid.UUID("6f2b9a1e-0d54-4c8f-9a3b-7e1c5d0a4b62")


def prompt_id_for(job_id: str) -> str:
    """`job_id` của nền tảng → `prompt_id` của ComfyUI, ổn định và lặp lại được."""
    return str(uuid.uuid5(PROMPT_NAMESPACE, str(job_id)))


class ComfyError(RuntimeError):
    """ComfyUI không phản hồi, trả mã lỗi, hoặc trả thân không đọc được."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class ComfyRejected(ComfyError):
    """ComfyUI TỪ CHỐI workflow (thiếu node, sai tham số) — lỗi của TA, không phải
    của máy chủ. Tách riêng vì cách xử lý khác hẳn: thử lại cũng vô ích."""


class Transport(Protocol):
    """Lớp vận chuyển tối thiểu — cho phép test chạy không cần ComfyUI thật."""

    def request(self, method: str, path: str, *, json: Any = None,
                params: Optional[dict] = None, timeout: float = 30.0) -> tuple[int, bytes]:
        ...


@dataclass(frozen=True)
class ImageRef:
    """Một ảnh trong `/history` — đủ để tải về qua `/view`."""
    filename: str
    subfolder: str
    type: str


class ComfyClient:
    def __init__(self, transport: Transport, *, client_id: Optional[str] = None):
        self._t = transport
        #: `client_id` của riêng ta. ComfyUI dùng nó để định tuyến websocket; ta
        #: không nghe websocket nhưng vẫn gửi để `/history` ghi đúng chủ.
        self.client_id = client_id or str(uuid.uuid4())

    # ── nền ──────────────────────────────────────────────────────────────────
    def _json(self, method: str, path: str, *, json: Any = None,
              params: Optional[dict] = None, timeout: float = 30.0) -> Any:
        import json as _json_mod
        status, body = self._t.request(method, path, json=json, params=params, timeout=timeout)
        if status == 400:
            # ComfyUI trả 400 kèm `node_errors` khi workflow sai. Đây là lỗi của ta.
            raise ComfyRejected(_tom_tat(body), status_code=status)
        if status >= 400:
            raise ComfyError(f"ComfyUI HTTP {status}: {_tom_tat(body)}", status_code=status)
        if not body:
            return None
        try:
            return _json_mod.loads(body.decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            raise ComfyError(f"ComfyUI tra JSON khong doc duoc: {e}") from None

    # ── gửi việc ─────────────────────────────────────────────────────────────
    def queue_prompt(self, workflow: dict, *, prompt_id: str) -> str:
        """Đẩy workflow vào hàng đợi ComfyUI. Trả `prompt_id` mà máy chủ xác nhận.

        Ta **tự đặt** `prompt_id` chứ không để ComfyUI sinh — xem `prompt_id_for`.
        """
        data = self._json("POST", "/prompt", json={
            "prompt": workflow,
            "client_id": self.client_id,
            "prompt_id": prompt_id,
        }, timeout=60.0)
        tra_ve = (data or {}).get("prompt_id") or prompt_id
        loi_node = (data or {}).get("node_errors") or {}
        if loi_node:
            raise ComfyRejected(f"ComfyUI tu choi workflow: {_tom_tat_dict(loi_node)}")
        return str(tra_ve)

    def interrupt(self, prompt_id: str) -> None:
        """Huỷ ĐÚNG một prompt.

        ⛔ `prompt_id` là bắt buộc ở đây dù ComfyUI cho phép bỏ trống. Bỏ trống sẽ
        giết lượt đang chạy — trên máy B đó có thể là một lượt video 70 phút của
        dự án khác.
        """
        if not prompt_id:
            raise ValueError("interrupt() phai co prompt_id — xem docstring")
        self._json("POST", "/interrupt", json={"prompt_id": prompt_id}, timeout=15.0)

    def free(self, *, unload_models: bool = True, free_memory: bool = True) -> None:
        """Bảo ComfyUI nhả model khỏi VRAM. Dùng sau OOM, hoặc khi nhường card."""
        self._json("POST", "/free", json={
            "unload_models": unload_models, "free_memory": free_memory}, timeout=30.0)

    # ── đọc trạng thái ───────────────────────────────────────────────────────
    def queue_remaining(self) -> int:
        data = self._json("GET", "/prompt", timeout=10.0) or {}
        return int(((data.get("exec_info") or {}).get("queue_remaining")) or 0)

    def queue_prompt_ids(self) -> tuple[list[str], list[str]]:
        """(đang chạy, đang chờ) theo `prompt_id`.

        Hình dạng một mục trong hàng đợi ComfyUI là **mảng vị trí**:
        `[number, prompt_id, prompt, extra_data, outputs_to_execute]` — nên
        `prompt_id` nằm ở chỉ số 1. Viết phòng thủ vì đây là hợp đồng ngầm.
        """
        data = self._json("GET", "/queue", timeout=10.0) or {}
        return (_ids(data.get("queue_running")), _ids(data.get("queue_pending")))

    def history(self, prompt_id: str) -> Optional[dict]:
        """Bản ghi lịch sử của một prompt, hoặc None nếu ComfyUI chưa/không có.

        ⛔ **CÓ BẢN GHI KHÔNG CÓ NGHĨA LÀ JOB CỦA TA ĐÃ XONG.** Đo thật trên máy B
        2026-08-21: một prompt **đang CHỜ trong hàng đợi, chưa chạy** vẫn trả về
        bản ghi `status_str: "success"` — vì `prompt_id` đó **đã từng chạy trước
        đó** (ta tự đặt id theo `job_id` nên nó lặp lại). Dùng `da_xong()` thay vì
        đọc thẳng hàm này để quyết định "xong hay chưa".
        """
        data = self._json("GET", f"/history/{prompt_id}", timeout=30.0) or {}
        muc = data.get(prompt_id)
        return muc if isinstance(muc, dict) else None

    def da_xong(self, prompt_id: str) -> bool:
        """Prompt này ĐÃ CHẠY XONG và thành công, **và không còn trong hàng đợi**.

        Hai điều kiện, không phải một:

        1. `/history` có bản ghi với `status_str == "success"`;
        2. `prompt_id` **không** nằm trong `queue_running` lẫn `queue_pending`.

        Điều kiện (2) là thứ bản đầu thiếu, và nó gây ra một lỗi thật: cổng thấy
        bản ghi cũ, tuyên bố "xong" sau 0,6 giây, **rồi vẫn xếp hàng lại** — vừa
        trả kết quả cũ vừa đốt thêm một lượt GPU 100 giây cho không.
        """
        muc = self.history(prompt_id)
        if not muc:
            return False
        if str(((muc.get("status") or {}).get("status_str")) or "") != "success":
            return False
        dang_chay, dang_cho = self.queue_prompt_ids()
        return prompt_id not in dang_chay and prompt_id not in dang_cho

    def images_of(self, prompt_id: str) -> list[ImageRef]:
        """Mọi ảnh mà prompt đã sinh, theo thứ tự node rồi thứ tự ảnh."""
        muc = self.history(prompt_id)
        if not muc:
            return []
        ra: list[ImageRef] = []
        for _node, out in sorted((muc.get("outputs") or {}).items()):
            for anh in (out.get("images") or []):
                ten = anh.get("filename")
                if not ten:
                    continue
                # `type` phân biệt output / temp / input. Ảnh xem trước là `temp`;
                # lấy nhầm nó là trả về ảnh mờ giữa chừng cho khách.
                if str(anh.get("type") or "output") != "output":
                    continue
                ra.append(ImageRef(ten, str(anh.get("subfolder") or ""), "output"))
        return ra

    def download(self, ref: ImageRef, *, timeout: float = 120.0) -> bytes:
        status, body = self._t.request("GET", "/view", params={
            "filename": ref.filename, "subfolder": ref.subfolder, "type": ref.type,
        }, timeout=timeout)
        if status >= 400:
            raise ComfyError(f"/view HTTP {status}", status_code=status)
        if not body:
            raise ComfyError("/view tra ve 0 byte")
        return body

    def object_info_keys(self) -> set[str]:
        """Tên mọi node ComfyUI đang có. Dùng để kiểm workflow TRƯỚC khi gửi —
        rẻ hơn nhiều so với gửi rồi nhận 400 sau khi đã xếp hàng."""
        data = self._json("GET", "/object_info", timeout=60.0) or {}
        return set(data.keys()) if isinstance(data, dict) else set()

    def system_stats(self) -> dict:
        return self._json("GET", "/system_stats", timeout=15.0) or {}

    def alive(self) -> bool:
        try:
            self.system_stats()
            return True
        except ComfyError:
            return False


# ── tiện ích riêng ───────────────────────────────────────────────────────────
def _ids(muc: Any) -> list[str]:
    ra: list[str] = []
    for m in (muc or []):
        if isinstance(m, (list, tuple)) and len(m) > 1 and isinstance(m[1], str):
            ra.append(m[1])
        elif isinstance(m, dict) and isinstance(m.get("prompt_id"), str):
            ra.append(m["prompt_id"])
    return ra


def _tom_tat(body: bytes) -> str:
    try:
        return body.decode("utf-8", errors="replace")[:300]
    except Exception:  # noqa: BLE001
        return "<khong doc duoc>"


def _tom_tat_dict(d: dict) -> str:
    return str(d)[:300]

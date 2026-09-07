"""Client gọi WanGP trên C-CLOUD — **mỏng nhất có thể**.

⛔ ĐÂY KHÔNG PHẢI một engine abstraction. Nó chuyển tiếp các thao tác và **không
   chuẩn hoá lại thứ WanGP đã chuẩn hoá**:

     · `apply_media_flag_defaults()`  tu dien co vai media (S/E/V/I/A/B)
     · `apply_video_length_duration()` nhan thang "10s", tu quy ra so khung
     · `merge_settings_with_defaults()` ghep voi mac dinh cua model

   Chuẩn hoá lần hai ở đây là dựng **bản sao thứ hai của sự thật** — có phép kiểm
   canh (`test_722::test_submit_KHONG_tu_them_tham_so_nao`).

⛔ Nó cũng **không** biết credit, người dùng, hay R2. Đó là việc của A-CONTROL.
   Cũng có phép kiểm canh.

📌 Vì sao ở `apps/lttvideo/` chứ không ở `platform_core/`: hợp đồng app
   (`AGENTS.md` §8.3) — việc dùng chung mới lên `platform_core`. Hiện chỉ một app
   dùng. Có app thứ hai thì mới chuyển, và lúc đó là **một quyết định**.

⚠️ Giao thức HTTP dưới đây là **hợp đồng LTT ↔ C-CLOUD**, chưa phải bề mặt native
   của WanGP: `shared/api.py` là API **trong tiến trình**, gọi qua mạng không
   được. Phía C-CLOUD sẽ có một service mỏng dịch sáu đường này sang lời gọi
   `WanGPSession` — dựng ở Phase E.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable

#: Chuỗi WanGP dùng để báo một lượt bị huỷ (đo được ở P01, `docs/API.md` mô tả).
DAU_HIEU_HUY = "cancelled"


class LoiWanGP(RuntimeError):
    """Mọi trục trặc khi nói chuyện với C-CLOUD.

    ⛔ Bọc lỗi mạng lại chứ **không nuốt**: người gọi không phải biết `urllib`,
       nhưng cũng không được nhận về một `None` im lặng.
    """


@dataclass(frozen=True)
class KetQua:
    thanh_cong: bool
    tep: list[str] = field(default_factory=list)
    loi: list[str] = field(default_factory=list)

    @property
    def da_huy(self) -> bool:
        """Phân biệt **huỷ** với **hỏng** — hai thứ khác nhau về tiền.

        Huỷ: người dùng bấm dừng ⇒ hoàn phần chưa dùng.
        Hỏng: lỗi thật ⇒ không trừ tiền.
        """
        return not self.thanh_cong and any(
            DAU_HIEU_HUY in str(x).lower() for x in self.loi
        )


#: Header mang khoá — để đường `GET` cũng xác thực được.
HEADER_KHOA = "X-LTTV-Key"


#: ⛔ **Bắt buộc.** Đường tới C-CLUD đi qua proxy của RunPod, mà proxy ấy nằm
#:   sau Cloudflare. Cloudflare chặn User-Agent mặc định của `urllib`
#:   (`Python-urllib/3.x`) và trả **HTTP 403 `error code: 1010`** — chặn theo
#:   chữ ký trình duyệt, trước khi yêu cầu chạm tới pod.
#:
#: 🔴 Đây là kiểu hỏng khó lần nhất trong cả tuyến: dịch vụ **đang chạy đúng**,
#:   log phía C-CLOUD **sạch không một dòng lỗi** (yêu cầu chưa từng tới nơi),
#:   `curl` từ cùng máy lại **200**. Đo được 06/09: bốn biến thể header xác thực
#:   đều 403, đổi mỗi User-Agent thì 200 ngay.
UA_TRINH_DUYET = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)


def _goi_that(method: str, duong: str, than=None, timeout: float = 30.0,
              khoa: str = "", du_lieu_tho: bytes | None = None):
    du_lieu = (du_lieu_tho if du_lieu_tho is not None else
               (json.dumps(than).encode("utf-8") if than is not None else None))
    req = urllib.request.Request(duong, data=du_lieu, method=method)
    req.add_header("Content-Type",
                   "application/octet-stream" if du_lieu_tho is not None
                   else "application/json")
    req.add_header("User-Agent", UA_TRINH_DUYET)
    if khoa:
        req.add_header(HEADER_KHOA, khoa)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        tho = r.read().decode("utf-8")
    return json.loads(tho) if tho else {}


class WanGPClient:
    """Chuyển tiếp, không diễn giải."""

    def __init__(self, *, goc: str, khoa: str,
                 goi: Callable[..., Any] | None = None) -> None:
        self.goc = goc.rstrip("/")
        self.khoa = khoa
        self._goi = goi or _goi_that

    def _hoi(self, method: str, duong: str, than=None, timeout: float = 30.0):
        try:
            return self._goi(method, f"{self.goc}{duong}", than,
                             timeout=timeout, khoa=self.khoa)
        except LoiWanGP:
            raise
        except Exception as e:  # noqa: BLE001 — boc lai, khong nuot
            raise LoiWanGP(f"{method} {duong}: {type(e).__name__}: {e}") from e

    # ── các thao tác ──

    def health(self) -> dict:
        return self._hoi("GET", "/health", timeout=10.0)

    def nap_media(self, du_lieu: bytes, *, duoi: str = "png") -> str:
        """Nạp một tệp media lên C-CLOUD, trả **đường dẫn trên máy đó**.

        ⭐ `docs/API.md` §*Accepted Input Shapes*: mọi đầu vào media của WanGP là
           **đường dẫn tệp trên chính máy chạy nó** — không URL, không base64.
           Ảnh của người dùng nằm ở R2 phía LTT, nên đây là mắt xích bắt buộc.

        ⛔ Gửi **byte thô**, không bọc JSON: base64 phồng 33% và một ảnh 8 MB
           thành 11 MB đi qua một proxy vốn đã có trần thời gian.
        """
        import urllib.parse  # noqa: PLC0415

        duong = f"{self.goc}/nap_media?duoi={urllib.parse.quote(duoi)}"
        try:
            dap = self._goi("POST", duong, None, timeout=180.0, khoa=self.khoa,
                            du_lieu_tho=du_lieu)
        except LoiWanGP:
            raise
        except Exception as e:  # noqa: BLE001
            raise LoiWanGP(f"POST /nap_media: {type(e).__name__}: {e}") from e
        d = (dap or {}).get("duong")
        if not d:
            raise LoiWanGP("/nap_media khong tra ve duong dan")
        return str(d)

    def submit(self, settings: dict) -> str:
        """Gửi **nguyên văn** bộ tham số. Không thêm, không bớt, không sửa."""
        dap = self._hoi("POST", "/submit", {"khoa": self.khoa, "settings": settings},
                        timeout=60.0)
        jid = dap.get("job_id")
        if not jid:
            raise LoiWanGP(f"/submit returned no job_id: {json.dumps(dap)[:200]}")
        return str(jid)

    def progress(self, job_id: str) -> dict:
        """Trả nguyên văn sự kiện tiến độ của WanGP (`phase`, `current_step`…)."""
        return self._hoi("GET", f"/progress/{job_id}", timeout=15.0)

    def cancel(self, job_id: str) -> dict:
        return self._hoi("POST", f"/cancel/{job_id}", {"khoa": self.khoa},
                         timeout=30.0)

    def result(self, job_id: str) -> KetQua:
        d = self._hoi("GET", f"/result/{job_id}", timeout=30.0)
        return KetQua(
            thanh_cong=bool(d.get("success")),
            tep=list(d.get("generated_files") or []),
            loi=[str(x) for x in (d.get("errors") or [])],
        )

    def cleanup(self, job_id: str) -> dict:
        """Dọn tệp tạm trên C-CLOUD sau khi đã kéo về R2."""
        return self._hoi("POST", f"/cleanup/{job_id}", {"khoa": self.khoa},
                         timeout=30.0)

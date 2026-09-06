"""Client gọi WanGP trên C-CLOUD — **mỏng nhất có thể**.

⛔ ĐÂY KHÔNG PHẢI một engine abstraction. Nó chuyển tiếp sáu thao tác và **không
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


def _goi_that(method: str, duong: str, than=None, timeout: float = 30.0):
    du_lieu = json.dumps(than).encode("utf-8") if than is not None else None
    req = urllib.request.Request(duong, data=du_lieu, method=method)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        tho = r.read().decode("utf-8")
    return json.loads(tho) if tho else {}


class WanGPClient:
    """Sáu thao tác, không hơn."""

    def __init__(self, *, goc: str, khoa: str,
                 goi: Callable[..., Any] | None = None) -> None:
        self.goc = goc.rstrip("/")
        self.khoa = khoa
        self._goi = goi or _goi_that

    def _hoi(self, method: str, duong: str, than=None, timeout: float = 30.0):
        try:
            return self._goi(method, f"{self.goc}{duong}", than, timeout=timeout)
        except LoiWanGP:
            raise
        except Exception as e:  # noqa: BLE001 — boc lai, khong nuot
            raise LoiWanGP(f"{method} {duong}: {type(e).__name__}: {e}") from e

    # ── sáu thao tác ──

    def health(self) -> dict:
        return self._hoi("GET", "/health", timeout=10.0)

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

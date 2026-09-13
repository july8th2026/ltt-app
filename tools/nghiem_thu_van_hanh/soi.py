"""soi.py — sáu sổ quan sát của bộ nghiệm thu vận hành thật.

Điểm vào của chương trình: `docs/VAN_HANH_THAT.md`.

⛔ **MỌI SỔ CHỈ ĐỌC.** Bộ đo không ghi vào CSDL, không sửa cấu hình, không dừng
   dịch vụ. Thứ duy nhất nó tạo ra là job qua **API công khai** — y như một khách.

🔴 **MỌI SỔ PHẢI TỰ KHAI KHI KHÔNG ĐỌC ĐƯỢC, thay vì trả một con số.**

   Ngày 13/09/2026 một phép dò trả `-1` suốt cả một lượt đo 16 kịch bản. Hai chi
   tiết, cả hai đều im lặng:

     · `/metrics` **không** ở cổng 8299 (gateway trả 404) mà ở cổng của chính
       `llama-server` — **8282** cho `ltt-3.8`, **8281** cho `ltt-3.5`
     · tên chỉ số mang **tiền tố**: `llamacpp:requests_processing`

   **`-1` trông y hệt `0`.** Một bộ đo mù một mắt vẫn in ra số, và cả lượt đo
   chạy xong rồi mới lộ ra. `MauSo.doc_duoc` tồn tại để điều đó không lặp lại.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
from dataclasses import dataclass
from typing import Any

#: Cổng `/metrics` của từng `llama-server` trên máy B. **Không phải** cổng gateway.
CONG_METRICS = {"ltt-3.8": 8282, "ltt-3.5": 8281}

#: Tiền tố bắt buộc của chỉ số llama.cpp. Lọc thiếu nó là khớp nhầm dòng khác.
TIEN_TO = "llamacpp:"

MAY_B = "lengo@192.168.2.66"


class SoMu(Exception):
    """Một sổ không trả lời được ⇒ **dừng**, không đo tiếp.

    ⛔ Một bộ đo tự nhận mình mù rồi vẫn đo là tệ hơn một bộ đo không chạy: nó
       sinh ra những con số trông như dữ liệu.
    """


@dataclass(frozen=True)
class MauSo:
    """Một lần chụp của một sổ. Bất biến — bản ghi quan sát không được sửa lại."""

    ten: str
    gia_tri: Any
    doc_duoc: bool
    ly_do: str = ""


# ── đường ra ngoài (bản giả thay được ở phép kiểm) ────────────────────────
def _ssh(lenh: str) -> tuple[bool, str]:
    """Chạy một lệnh trên máy B. Trả `(ssh_sống, đầu_ra)`.

    ⚠️ Máy B chạy Windows: `cmd` **không** hiểu `;` làm dấu phân cách. Truyền
       một chuỗi nhiều lệnh vào đây thì nó `echo` cả chuỗi thay vì chạy.
    """
    try:
        r = subprocess.run(
            ["ssh", "-i", str(pathlib.Path.home() / ".ssh" / "nexus_b"),
             "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", MAY_B, lenh],
            capture_output=True, text=True, timeout=90)
        return r.returncode == 0, (r.stdout or "")
    except Exception:  # noqa: BLE001 - sổ hỏng phải TỰ KHAI, không được ném lên
        return False, ""


def _curl_may_b(cong: int) -> str:
    """Kéo `/metrics` của một `llama-server`. Rỗng = không có server ở cổng ấy."""
    _ok, van = _ssh(f"curl.exe -s -m 10 http://127.0.0.1:{cong}/metrics")
    return van


def _may_b_voi_toi() -> bool:
    """Máy B có với tới được không — tách khỏi câu *"model có đang nạp không"*."""
    ok, van = _ssh("echo song")
    return ok and "song" in van


def _hoi_db(db_url: str, cau: str) -> Any:
    """Một truy vấn CHỈ ĐỌC. Ném thì người gọi biến nó thành `doc_duoc=False`."""
    from sqlalchemy import create_engine, text

    with create_engine(db_url).connect() as c:
        return c.execute(text(cau)).scalar()


def _http(goc: str, duong: str) -> str:
    import httpx

    return httpx.get(f"{goc.rstrip('/')}{duong}", timeout=15.0).text


# ── sáu sổ ────────────────────────────────────────────────────────────────
def so_slot(cong: int) -> MauSo:
    """Số lượt máy B **đang xử lý** trên một card.

    ⛔ Vế thứ hai của L-08: nhả lease mà **không** nhả slot là mới đi được nửa
       đường — sổ sách máy A sạch tinh, còn GPU thì vẫn bận.
    """
    van = _curl_may_b(cong)
    if not van.strip():
        # 🔴 PHÂN BIỆT HAI THỨ KHÁC HẲN NHAU — bản đầu lẫn chúng, và Pha 0 từ
        #    chối chạy vì một trạng thái hoàn toàn bình thường:
        #
        #      · SSH không với tới máy B      -> BỘ ĐO MÙ, phải dừng lượt đo
        #      · SSH sống nhưng cổng trống    -> `llama-swap` đã gỡ model vì lâu
        #                                        không ai gọi. Không có lượt nào
        #                                        đang xử lý, tức **0** — và kịch
        #                                        bản đầu tiên sẽ tự nạp lại.
        #
        # ⛔ Lẫn hai điều này là bắt cả chương trình dừng vì một cái card đang
        #    ngủ. Đo 13/09: `tasklist` trên máy B trả *"No tasks are running"*
        #    cho `llama-server.exe` trong khi SSH vẫn `echo` được.
        if _may_b_voi_toi():
            return MauSo("slot", 0, True, f"model chua nap o cong {cong}")
        return MauSo("slot", None, False,
                     f"KHONG voi toi may B (ssh hong) — cong {cong}")
    for dong in van.splitlines():
        d = dong.strip()
        if d.startswith("#"):
            continue
        if d.startswith(TIEN_TO + "requests_processing"):
            try:
                return MauSo("slot", int(float(d.split()[-1])), True)
            except (ValueError, IndexError):
                return MauSo("slot", None, False, f"khong doc duoc gia tri: {d!r}")
    return MauSo("slot", None, False,
                 f"khong thay `{TIEN_TO}requests_processing` o cong {cong}")


def so_lease(db_url: str) -> MauSo:
    """Số lease `mode='stream'` đang sống — thước đo trung tâm của L-08/L-11."""
    try:
        n = _hoi_db(db_url, "SELECT COUNT(*) FROM execution_leases "
                            "WHERE mode='stream'")
        return MauSo("lease", int(n or 0), True)
    except Exception as e:  # noqa: BLE001
        return MauSo("lease", None, False, f"{type(e).__name__}: {e}"[:120])


def so_jobs(db_url: str, *, nhan: str = "") -> MauSo:
    """Số job đang chạy/chờ. `nhan` lọc theo `tool` khi cần."""
    loc = f" AND tool = '{nhan}'" if nhan else ""
    try:
        n = _hoi_db(db_url, "SELECT COUNT(*) FROM jobs WHERE status IN "
                            f"('queued','running'){loc}")
        return MauSo("jobs", int(n or 0), True)
    except Exception as e:  # noqa: BLE001
        return MauSo("jobs", None, False, f"{type(e).__name__}: {e}"[:120])


def so_credit(db_url: str) -> MauSo:
    """Số khoản `hold` **CHƯA quyết toán** — tiền khách đang thực sự bị giữ.

    🔴 Đây là sổ mà một sự cố stream làm bẩn **âm thầm**: suất nhả rồi mà khoản
       giữ còn nằm lại thì không bộ quét nào của hàng đợi job nhìn thấy nó.

    ⛔ BẢN ĐẦU ĐẾM SAI, và chạy Pha 0 trên máy thật mới lộ ra: nó đếm **mọi**
       bút toán `hold` từng có — 4.328 dòng — thay vì những khoản còn treo. Một
       con số như thế **luôn tăng**, nên nó không bao giờ báo được điều gì; nó
       chỉ trông như một phép đo. Số đúng lúc ấy là **7**.

    ⇒ Một `hold` coi là đã kết khi có `settle` **hoặc** `refund` cùng `job_id`.
    """
    try:
        n = _hoi_db(db_url, """
            SELECT COUNT(*) FROM credit_entries h
            WHERE h.kind = 'hold' AND NOT EXISTS (
                SELECT 1 FROM credit_entries s
                WHERE s.job_id = h.job_id AND s.kind IN ('settle', 'refund'))""")
        return MauSo("credit", int(n or 0), True)
    except Exception as e:  # noqa: BLE001
        return MauSo("credit", None, False, f"{type(e).__name__}: {e}"[:120])


def so_residency(db_url: str) -> MauSo:
    """Số người đang xếp hàng — đại lượng duy nhất nói *"có ai phải chờ không"*."""
    try:
        n = _hoi_db(db_url, "SELECT COUNT(*) FROM llm_waiters "
                            "WHERE trang_thai = 'cho'")
        return MauSo("residency", int(n or 0), True)
    except Exception as e:  # noqa: BLE001
        return MauSo("residency", None, False, f"{type(e).__name__}: {e}"[:120])


def so_http(goc: str) -> MauSo:
    """Commit production đang chạy.

    ⚠️ Không có nó thì mọi con số đo được **không tái lập được** — ta sẽ có một
       bảng đẹp mà không biết nó nói về bản nào.
    """
    try:
        d = json.loads(_http(goc, "/health/version"))
        ma = str(d.get("commit") or "")
        if not ma:
            return MauSo("http", None, False, "/health/version khong co `commit`")
        return MauSo("http", ma, True)
    except Exception as e:  # noqa: BLE001
        return MauSo("http", None, False, f"{type(e).__name__}: {e}"[:120])


# ── Pha 0 ─────────────────────────────────────────────────────────────────
def tu_kiem(db_url: str, goc: str, *, cong_slot: int = 8282) -> list[MauSo]:
    """PHA 0 — hỏi cả sáu sổ một lần, **ném** nếu sổ nào không trả lời được.

    ⛔ Không cảnh báo rồi chạy tiếp. Một lượt đo bắt đầu bằng một sổ mù sẽ sinh
       ra những con số trông như dữ liệu, và người đọc không có cách nào biết.

    ⚠️ Thêm sổ thứ bảy mà quên nối vào đây thì nó **không bao giờ được kiểm** —
       `test_1251::test_tu_kiem_tra_DU_SAU_so_khi_lanh` chốt đúng điều đó.
    """
    ds = [
        so_lease(db_url),
        so_jobs(db_url),
        so_credit(db_url),
        so_residency(db_url),
        so_http(goc),
        so_slot(cong_slot),
    ]
    mu = [m for m in ds if not m.doc_duoc]
    if mu:
        raise SoMu("so khong doc duoc: "
                   + "; ".join(f"{m.ten} ({m.ly_do})" for m in mu))
    return ds


def _in(ds: list[MauSo]) -> None:
    for m in ds:
        print(f"  {m.ten:10s} {'OK ' if m.doc_duoc else 'MU '} {m.gia_tri!r}"
              + (f"  {m.ly_do}" if m.ly_do else ""))


if __name__ == "__main__":  # pragma: no cover - đường tay, chạy ở Pha 0
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    import argparse

    ap = argparse.ArgumentParser(description="Pha 0 — tu kiem sau so")
    ap.add_argument("--db", required=True)
    ap.add_argument("--goc", default="http://127.0.0.1:8100")
    a = ap.parse_args()
    try:
        _in(tu_kiem(a.db, a.goc))
        print("\n  PHA 0 DAT — bo do khong mu")
    except SoMu as e:
        print(f"\n  PHA 0 DO: {e}")
        raise SystemExit(2) from None

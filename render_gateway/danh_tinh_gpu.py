"""
danh_tinh_gpu.py — UUID của hai card máy B, cho phía **render**.

🔴 VÌ SAO TỆP NÀY TỒN TẠI THAY VÌ `from llm_gateway.gpu_uuid import ...`.
   Đây là câu hỏi Task 6.1 để mở, và nó **đo được** chứ không phải chuyện gu:

   1. **Gói `llm_gateway` KHÔNG có trong bản cài render trên máy B.**
      `render_gateway/deploy/deploy.ps1` chép **chỉ** `render_gateway` sang
      `E:\\AI\\ltt_render\\gateway\\render_gateway`, và dịch vụ chạy
      `-m render_gateway.main` với `AppDirectory = E:\\AI\\ltt_render\\gateway`
      (`deploy.ps1:28,91-104`, `cai_dat_dich_vu.ps1`). Bản cài LLM là một cây
      **khác** (`H:/LTT_LLM/gateway`, `llm_gateway/deploy/deploy.ps1:20,122`) và
      nó chép **cả hai** gói. ⇒ Một `import llm_gateway` ở đây nạp được trong
      kho và trong bản cài LLM, rồi **chết ở đúng chỗ nó phải sống**: dịch vụ
      render trên máy B. Không phải "có thể chết" — thư mục đó không có gói ấy.

   2. **Chiều phụ thuộc đã chốt đi hướng ngược.** `llm_gateway/trong_tai.py:89`
      và `:114` import `render_gateway.busy` (D-013/D-022: "dùng lại, không chép
      lại"), và `llm_gateway/deploy/kiem_import.py:41` chốt điều đó bằng một phép
      kiểm. Thêm `render_gateway → llm_gateway` là dựng một **vòng** giữa hai gói.

   3. `.importlinter` chỉ khai ba `root_packages` (`platform_core`, `server`,
      `apps`) ⇒ nó **không** nói gì về cặp này. Nên rào cơ học duy nhất cho quyết
      định trên là phép kiểm ở `tests/test_1230_busy_theo_uuid.py` — nó chốt
      rằng `render_gateway` không import `llm_gateway`, **và** chốt rằng hai bộ
      đọc trả về cùng UUID từ cùng một tệp.

⭐ NGUỒN CHÂN LÝ VẪN LÀ **MỘT TỆP**: `llm_gateway/deploy/gpu_may_b.json` (Task
   0.2, `tests/test_1200_ghim_gpu_may_b.py`). Tệp này **không** chép UUID vào mã —
   nó đọc đúng tệp ấy. Hai bộ đọc, một nguồn.

⚠️ TRÊN MÁY B TỆP JSON PHẢI ĐI THEO. Bản cài render không có `llm_gateway/`, nên
   `deploy.ps1` chép `gpu_may_b.json` (bản gốc trong `llm_gateway/deploy/`) tới
   `render_gateway/deploy/gpu_may_b.json` ở phía máy B. Trong **kho** không có
   bản sao ấy — có là hai chỗ khai một điều, đúng cơ chế "bảng chép tay" đã nói
   sai năm lần. Phép kiểm chốt cả hai nửa.

⛔ KHÔNG BIẾT ⇒ `None`, không bao giờ là một UUID đoán hay chuỗi rỗng. Chuỗi rỗng
   lọt qua mọi phép so sánh xuống dưới và biến "không biết card nào" thành "không
   card nào khớp" — một phép đo rỗng đội lốt một phép đo sạch.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

log = logging.getLogger("render_gateway.danh_tinh_gpu")

#: Hai vai trên máy B. Tên vai là thứ mã nguồn nói; UUID là thứ tệp json nói.
#: Cùng tên vai với `llm_gateway/gpu_uuid.py` — đổi một bên là hỏng đối chiếu.
VAI_38 = "ltt38"
VAI_35 = "ltt35"

#: Biến môi trường ghi đè đường dẫn tệp danh tính. Có mặt để vận hành gỡ được
#: một sự cố mà không phải deploy lại mã.
BIEN_MOI_TRUONG = "LTT_GPU_DANH_TINH"

_GOC_GOI = Path(__file__).resolve().parent


def cac_duong_ung_vien() -> list[Path]:
    """Các nơi có thể có `gpu_may_b.json`, theo **thứ tự ưu tiên**.

    1. `$LTT_GPU_DANH_TINH` — vận hành chỉ tay.
    2. `<cha của render_gateway>/llm_gateway/deploy/gpu_may_b.json` — **bản gốc**.
       Đúng trong kho, trong gate, và trong bản cài LLM (`H:/LTT_LLM/gateway/`
       có cả hai gói).
    3. `render_gateway/deploy/gpu_may_b.json` — bản `deploy.ps1` chép sang máy B,
       nơi bản cài render **không** có `llm_gateway/`.
    """
    ds: list[Path] = []
    env = (os.environ.get(BIEN_MOI_TRUONG) or "").strip()
    if env:
        ds.append(Path(env))
    ds.append(_GOC_GOI.parent / "llm_gateway" / "deploy" / "gpu_may_b.json")
    ds.append(_GOC_GOI / "deploy" / "gpu_may_b.json")
    return ds


def duong_danh_tinh() -> Optional[Path]:
    """Tệp danh tính đầu tiên **thực sự có**. `None` = không tệp nào."""
    for d in cac_duong_ung_vien():
        try:
            if d.is_file():
                return d
        except OSError:                                          # pragma: no cover
            continue
    return None


_nho: dict[str, list[dict]] = {}


def doc_danh_tinh(duong: Optional[Path] = None) -> Optional[list[dict]]:
    """Đọc `gpu_may_b.json`. `None` = không đọc được (thiếu tệp, JSON vỡ).

    ⚠️ `read_bytes().decode("utf-8-sig")` chứ không `read_text()`: quy tắc 1 của
       `CLAUDE.md` cấm **ghi** BOM, nhưng phía **đọc** phải sống được với một tệp
       ai đó đã ghi bằng `Out-File -Encoding utf8`. Chết vì ba byte vô hình là
       mất toàn bộ phép đo GPU.
    """
    d = duong or duong_danh_tinh()
    if d is None:
        log.warning("khong thay gpu_may_b.json (da thu: %s)",
                    ", ".join(str(x) for x in cac_duong_ung_vien()))
        return None
    khoa = str(d)
    if khoa not in _nho:
        try:
            du_lieu = json.loads(Path(d).read_bytes().decode("utf-8-sig"))
        except (OSError, ValueError) as e:
            log.warning("doc %s that bai: %s", d, e)
            return None
        if not isinstance(du_lieu, list):
            log.warning("%s khong phai mot danh sach", d)
            return None
        _nho[khoa] = du_lieu
    return _nho[khoa]


def xoa_nho() -> None:
    """Quên bộ nhớ đệm. Cho test đổi tệp danh tính giữa hai phép kiểm."""
    _nho.clear()


def uuid_cua(vai: str, *, duong: Optional[Path] = None) -> Optional[str]:
    """UUID của một vai. `None` = không biết — **không** chuỗi rỗng.

    UUID phải bắt đầu bằng `GPU-`: một giá trị lạ trong tệp là "không biết", chứ
    không phải một khoá lọc hợp lệ.
    """
    ds = doc_danh_tinh(duong)
    if ds is None:
        return None
    for x in ds:
        if str(x.get("vai") or "") == vai:
            uu = str(x.get("uuid") or "")
            if not uu.startswith("GPU-"):
                log.warning("vai %s khai uuid khong hop le: %r", vai, uu)
                return None
            return uu
    log.warning("vai %s khong co trong tep danh tinh", vai)
    return None


def vram_tong_mib(vai: str, *, duong: Optional[Path] = None) -> Optional[int]:
    """VRAM danh nghĩa của card theo tệp danh tính (không hỏi driver).

    ⭐ THAY CHO HẰNG SỐ `24_576` GÕ TAY trong `busy.py`. Hằng số ấy là một "bảng
       chép tay": nó đúng cho 3090 và **sai im lặng** cho mọi card khác.
    """
    ds = doc_danh_tinh(duong)
    if ds is None:
        return None
    for x in ds:
        if str(x.get("vai") or "") == vai:
            try:
                n = int(x.get("vram_mib") or 0)
            except (TypeError, ValueError):
                return None
            return n or None
    return None


def uuid_38(*, duong: Optional[Path] = None) -> Optional[str]:
    """UUID của **card tranh chấp** (RTX 3090: LTT-3.8 + model ảnh, D01 B).

    ⛔ Đây là card duy nhất cổng render được phép kết luận về. 5060 Ti chạy
       LTT-3.5 và **không ai tranh** nó — một tiến trình giữ VRAM ở đó không làm
       render "bận" (L-7: hai GPU là hai pool độc lập, không gộp 24+16).
    """
    return uuid_cua(VAI_38, duong=duong)


def vram_tong_mib_38(*, duong: Optional[Path] = None) -> Optional[int]:
    """VRAM danh nghĩa của card 3090, MiB. `None` = không biết."""
    return vram_tong_mib(VAI_38, duong=duong)

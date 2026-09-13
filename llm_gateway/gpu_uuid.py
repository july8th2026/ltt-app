"""
gpu_uuid.py — đo GPU máy B **theo UUID**, không theo chỉ số và không theo dòng đầu.

🔴 VÌ SAO FILE NÀY TỒN TẠI. Từ 09/2026 máy B có **hai** card:

      ltt38  RTX 3090     24.576 MiB   PCI 00000000:02:00.0   <- LTT-3.8 + ComfyUI
      ltt35  RTX 5060 Ti  16.311 MiB   PCI 00000000:81:00.0   <- LTT-3.5

   Mọi phép đo cũ trong kho này viết cho **một** card, và chúng hỏng theo cùng
   một cách: chúng gọi `nvidia-smi --query-gpu=memory.used` rồi lấy
   `splitlines()[0]`. Với hai card, dòng đầu là **một** trong hai — và cái nào
   thì phụ thuộc thứ tự liệt kê của driver, tức một thứ ta không kiểm soát.

   ⛔ Đây không phải "sai lệch nhỏ". Nó là một phép đo **lệch chiều**: chốt VRAM
      của `tren_gpu.py` sẽ đọc số của card KHÁC, nên một model thật sự rơi về
      CPU trên 3090 vẫn xanh nếu 5060 Ti đang giữ 13 GB. Cùng lớp khuyết tật mà
      `tren_gpu.py` sinh ra để chặn, chỉ là nó quay lại bằng cửa thứ hai.

⭐ VÀ VÌ SAO LỌC THEO CỘT `uuid` CHỨ KHÔNG CHỈ TRUYỀN `--id=<uuid>`:

   `--id=<uuid>` *nên* lọc đúng một card. Nhưng nó là một bảo đảm **đi mượn**:
   nếu driver không hiểu dạng UUID thì `nvidia-smi` trả mã khác 0 (ta mất số đo)
   hoặc, tệ hơn, trả toàn bộ card. Hỏi **cả hai card** rồi tự lọc theo cột
   `uuid` thì đúng trong cả hai trường hợp, và nó biến "dòng nào" thành một câu
   hỏi không còn tồn tại. Giá phải trả: một cột nữa trong truy vấn.

⛔ KHÔNG BAO GIỜ DÙNG CHỈ SỐ (`CUDA0`, `--id=0`, `dong[0]`). Thứ tự liệt kê đổi
   khi lắp/đổi khe card; UUID thì không. `tests/test_1200_ghim_gpu_may_b.py` đã
   chốt điều đó cho `llama-swap.yaml`; tệp này mang cùng luật sang phía đo đạc.

⭐ NGUỒN DANH TÍNH LÀ `deploy/gpu_may_b.json`, KHÔNG PHẢI HẰNG SỐ Ở ĐÂY. Một lần
   đo lại card chỉ được sửa **một** tệp. Chép UUID vào đây là dựng lại đúng cơ
   chế "bảng chép tay" đã nói sai năm lần trong dự án này.
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Optional

log = logging.getLogger("llm_gateway.gpu_uuid")

#: Nguồn chân lý danh tính GPU máy B. Cùng tệp mà `test_1200` đọc.
DUONG_DANH_TINH = Path(__file__).resolve().parent / "deploy" / "gpu_may_b.json"

#: Cùng trần với `don_dep.NVIDIA_SMI_TIMEOUT_S` và `render_gateway/busy.py`.
#: `nvidia-smi` **treo được** (driver lỗi, card kẹt) — không được chờ vô hạn.
NVIDIA_SMI_TIMEOUT_S = 8

#: Hai vai trên máy B. Tên vai là thứ mã nguồn nói; UUID là thứ tệp json nói.
VAI_38 = "ltt38"
VAI_35 = "ltt35"

#: Hồ sơ llama-swap → vai GPU. Cùng ánh xạ với `test_1200._vai_cho_model`.
#:
#: ⛔ Theo TIỀN TỐ, không theo danh sách đầy đủ: một hồ sơ `qwen35-*` mới thêm
#:    vào catalog mà quên khai ở đây sẽ lặng lẽ đo card sai.
def vai_cua_model(ten_ho_so: str) -> Optional[str]:
    """`qwen38-*` → `ltt38` (3090) · `qwen35-*` → `ltt35` (5060 Ti)."""
    t = (ten_ho_so or "").strip()
    if t.startswith("qwen38"):
        return VAI_38
    if t.startswith("qwen35"):
        return VAI_35
    return None


class VaiKhongCo(LookupError):
    """Vai không có trong `gpu_may_b.json`."""


_nho: dict[str, list[dict]] = {}


def doc_danh_tinh(duong: Optional[Path] = None) -> list[dict]:
    """Đọc `gpu_may_b.json`. Nhớ theo đường dẫn (tệp tĩnh, đọc một lần).

    ⚠️ `read_bytes().decode("utf-8-sig")` chứ không `read_text()`: quy tắc 1 của
       `CLAUDE.md` cấm **ghi** BOM, nhưng phía **đọc** thì phải sống được với một
       tệp ai đó đã ghi bằng `Out-File -Encoding utf8`. Chết vì một BOM ở đây là
       làm mất toàn bộ phép đo GPU vì ba byte vô hình.
    """
    d = (duong or DUONG_DANH_TINH).resolve()
    khoa = str(d)
    if khoa not in _nho:
        du_lieu = json.loads(d.read_bytes().decode("utf-8-sig"))
        if not isinstance(du_lieu, list):
            raise ValueError("gpu_may_b.json phai la mot danh sach")
        _nho[khoa] = du_lieu
    return _nho[khoa]


def uuid_cua(vai: str, *, duong: Optional[Path] = None) -> str:
    """UUID của một vai. Thiếu vai ⇒ `VaiKhongCo` — **không** trả chuỗi rỗng.

    ⛔ Chuỗi rỗng sẽ lọt qua mọi phép so sánh xuống dưới và biến "không biết
       card nào" thành "không card nào khớp", tức một phép đo rỗng đội lốt một
       phép đo sạch.
    """
    for x in doc_danh_tinh(duong):
        if str(x.get("vai") or "") == vai:
            uu = str(x.get("uuid") or "")
            if not uu.startswith("GPU-"):
                raise VaiKhongCo(f"vai {vai} khai uuid khong hop le: {uu!r}")
            return uu
    raise VaiKhongCo(vai)


def vram_tong_mib(vai: str, *, duong: Optional[Path] = None) -> int:
    """VRAM danh nghĩa của card, theo tệp danh tính (không hỏi driver)."""
    for x in doc_danh_tinh(duong):
        if str(x.get("vai") or "") == vai:
            return int(x.get("vram_mib") or 0)
    raise VaiKhongCo(vai)


# ── Hỏi driver ───────────────────────────────────────────────────────────────

def _chay_smi(doi_so: list[str], *, chay: Callable = subprocess.run) -> Optional[str]:
    """Gọi `nvidia-smi`. `None` = **không biết** (không có smi, lỗi, hết giờ).

    ⛔ `None` KHÁC 0 và khác chuỗi rỗng. Bên gọi phải phân biệt: "card đang trống"
       và "không hỏi được card" đòi hai hành động khác nhau.
    """
    smi = shutil.which("nvidia-smi") or "nvidia-smi"
    try:
        r = chay([smi, *doi_so], capture_output=True, text=True,
                 timeout=NVIDIA_SMI_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError):
        return None
    if getattr(r, "returncode", 1) != 0:
        return None
    return r.stdout or ""


def _o_cua_card(truong: str, uuid: str, *,
                chay: Callable = subprocess.run) -> Optional[list[str]]:
    """Các ô của **đúng** card `uuid`, đã lọc theo cột `uuid`.

    🔴 ĐÂY LÀ CHỖ BẢN CŨ HỎNG. Bản cũ lấy `splitlines()[0]`; với hai card, dòng
       đầu là card nào thì phụ thuộc driver. Ở đây cột đầu **luôn** là `uuid`,
       nên câu hỏi "dòng nào" không còn tồn tại.
    """
    ra = _chay_smi(["--query-gpu=uuid," + truong, "--format=csv,noheader,nounits"],
                   chay=chay)
    if ra is None:
        return None
    for dong in ra.splitlines():
        o = [x.strip() for x in dong.split(",")]
        if len(o) >= 2 and o[0] == uuid:
            return o[1:]
    return None


def doc_the(uuid: str, *, chay: Callable = subprocess.run) -> Optional[dict]:
    """Một lời gọi `nvidia-smi` cho cả ba con số của một card.

    ⭐ GỘP CÓ CHỦ Ý. `/health` đọc hai card; ba lời gọi mỗi card là sáu vòng
       `nvidia-smi` cho một lượt thăm dò mà máy giám sát gọi mỗi 15 giây. Một
       lời gọi mỗi card là hai.
    """
    o = _o_cua_card("memory.used,memory.free,utilization.gpu", uuid, chay=chay)
    if o is None or len(o) < 3:
        return None
    try:
        return {"vram_dung_mib": int(float(o[0])),
                "vram_trong_mib": int(float(o[1])),
                "util_pt": int(float(o[2]))}
    except ValueError:
        return None


def vram_mib(uuid: str, *, chay: Callable = subprocess.run) -> Optional[int]:
    """VRAM **đang dùng** trên đúng card `uuid`, MiB. `None` = không hỏi được."""
    the = doc_the(uuid, chay=chay)
    return None if the is None else the["vram_dung_mib"]


def vram_trong_mib(uuid: str, *, chay: Callable = subprocess.run) -> Optional[int]:
    """VRAM **còn trống** trên đúng card `uuid`, MiB. `None` = không hỏi được.

    ⭐ Đọc `memory.free` của driver, KHÔNG lấy `tong - dung` từ tệp danh tính:
       phần driver tự giữ (context, ECC) không nằm trong `memory.used`, nên phép
       trừ cho một con số **lạc quan hơn thực tế** — đúng chiều nguy hiểm cho
       một cái sàn.
    """
    the = doc_the(uuid, chay=chay)
    return None if the is None else the["vram_trong_mib"]


def util_pt(uuid: str, *, chay: Callable = subprocess.run) -> Optional[int]:
    """Phần trăm tải của đúng card `uuid`. `None` = không hỏi được."""
    the = doc_the(uuid, chay=chay)
    return None if the is None else the["util_pt"]


def tien_trinh(uuid: str, *,
               chay: Callable = subprocess.run) -> list[tuple[int, str, int]]:
    """Tiến trình đang tính **trên đúng card** `uuid`: `[(pid, ten, mib)]`.

    ⛔ `--query-compute-apps` KHÔNG lọc theo card nếu ta không xin cột
       `gpu_uuid`. Bản cũ (`don_dep._dem_toi_thieu`, `busy.py`) đếm tiến trình
       trên **mọi** card rồi kết luận về một card — nên một job ảnh trên 5060 Ti
       làm cổng LLM của 3090 tưởng card mình bẩn, và ngược lại.

    ⚠️ `used_memory` trả `[N/A]` trên WDDM/Windows ở nhiều driver. Không đọc
       được thì ghi 0 **và vẫn giữ dòng đó**: sự tồn tại của tiến trình là tin
       chắc chắn, chỉ dung lượng là không biết. Bỏ cả dòng vì thiếu một ô là
       biến "có việc đang chạy" thành "card rảnh".

    Không hỏi được ⇒ danh sách rỗng. Bên gọi muốn phân biệt "rỗng" với "không
    biết" thì hỏi `doc_the()` trước — nó trả `None` khi driver không trả lời.
    """
    ra = _chay_smi(["--query-compute-apps=pid,process_name,used_memory,gpu_uuid",
                    "--format=csv,noheader,nounits"], chay=chay)
    if ra is None:
        return []
    kq: list[tuple[int, str, int]] = []
    for dong in ra.splitlines():
        o = [x.strip() for x in dong.split(",")]
        if len(o) < 4 or o[3] != uuid:
            continue
        try:
            pid = int(o[0])
        except ValueError:
            continue
        try:
            mib = int(float(o[2]))
        except ValueError:
            mib = 0
        kq.append((pid, o[1], mib))
    return kq


def thay_du_hai_card(*, chay: Callable = subprocess.run,
                     duong: Optional[Path] = None) -> bool:
    """Driver có thấy **đủ** mọi UUID khai trong `gpu_may_b.json` không.

    🔴 FAIL-CLOSED, và đây là chỗ duy nhất trong tệp này fail-closed. Không hỏi
       được `nvidia-smi` ⇒ `False`. Lý do: một card **rụng** khỏi hệ thống là ca
       đã xảy ra thật ở dự án này (`test_329_chot_so_gpu`), và triệu chứng của nó
       giống hệt "không hỏi được". Với `/health/ready` thì hai thứ ấy đòi cùng
       một hành động: **đừng nhận lượt mới cho tới khi có người xem**.

    ⛔ Đừng dùng hàm này để từ chối một yêu cầu đang bay — xem `/health/ready`
       trong `api.py`: nó là chốt **sẵn sàng**, không phải chốt vào cửa.
    """
    ra = _chay_smi(["--query-gpu=uuid", "--format=csv,noheader"], chay=chay)
    if ra is None:
        return False
    thay = {d.strip() for d in ra.splitlines() if d.strip()}
    try:
        can = {str(x.get("uuid") or "") for x in doc_danh_tinh(duong)}
    except Exception:  # noqa: BLE001 - moi kieu doc hong deu cung mot huong xu
        # 🔴 DOC KHONG DUOC DANH TINH **CUNG LA** FAIL-CLOSED (cong N, 13/09).
        #
        #    Truoc 13/09 ngoai le nay bay thang ra ngoai, va `/health/ready`
        #    thanh **500** thay vi **503**. Spec §22 doi 503 cho ca "GPU khong
        #    thay (UUID thieu)", va RUNBOOK canh bao dung tinh huong ay: mot ban
        #    cai dat thieu `gpu_may_b.json` la **dung han** viec sinh anh.
        #
        # ⭐ Docstring cua chinh ham nay da noi ly do, chi la no viet cho mot ca
        #    khac: *"khong hoi duoc `nvidia-smi` => False ... hai thu ay doi
        #    CUNG MOT hanh dong: dung nhan luot moi cho toi khi co nguoi xem"*.
        #    "Khong doc duoc danh tinh" la mot the thu ba cua cung cau hoi ay.
        #
        # ⛔ Va khac biet 500/503 khong phai chuyen chu nghia o mot chot SAN
        #    SANG: 503 la "chua san sang, dung gui luot toi" — mot cau tra loi;
        #    500 la "chinh chot nay dang hong" — mot cau hoi moi.
        log.warning("khong doc duoc danh tinh GPU => coi nhu CHUA SAN SANG",
                    exc_info=True)
        return False
    thieu = can - thay
    if thieu:
        log.warning("driver KHONG thay card: %s (thay: %s)",
                    ", ".join(sorted(thieu)), ", ".join(sorted(thay)) or "khong card nao")
    return not thieu


# ── CLI nhỏ, cho script vận hành trên máy B ─────────────────────────────────
#
# ⭐ CÓ MẶT ĐỂ `chay_nghiem_thu.cmd` KHÔNG PHẢI GỌI `taskkill /im`. Dừng theo
#    tên ảnh là dừng **cả hai** engine, kể cả engine của card ta không thử —
#    tức giết việc đang chạy của model khác, và giết trong im lặng. Có danh sách
#    PID theo từng card thì script dừng đúng thứ nó nói nó dừng.
#
# ⛔ `python -m llm_gateway.gpu_uuid`, KHÔNG phải `python -c "..."` (quy tắc 3
#    của `CLAUDE.md`: không viết Python inline qua PowerShell/cmd).
def _main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("dung: python -m llm_gateway.gpu_uuid "
              "{uuid|vram|trong|util|pid} <vai>  |  kiem")
        return 2
    lenh = argv[1]
    if lenh == "kiem":
        du = thay_du_hai_card()
        print("DU" if du else "THIEU")
        return 0 if du else 1
    if len(argv) < 3:
        print("thieu <vai> (ltt38 | ltt35)")
        return 2
    vai = argv[2]
    try:
        uu = uuid_cua(vai)
    except VaiKhongCo as e:
        print(f"vai khong co trong gpu_may_b.json: {e}")
        return 2
    if lenh == "uuid":
        print(uu)
        return 0
    if lenh == "pid":
        for pid, ten, mib in tien_trinh(uu):
            print(f"{pid} {ten} {mib}")
        return 0
    the = doc_the(uu)
    if the is None:
        print("KHONG-HOI-DUOC")
        return 1
    if lenh == "vram":
        print(the["vram_dung_mib"])
    elif lenh == "trong":
        print(the["vram_trong_mib"])
    elif lenh == "util":
        print(the["util_pt"])
    else:
        print(f"lenh la: {lenh}")
        return 2
    return 0


if __name__ == "__main__":                                   # pragma: no cover
    import sys

    raise SystemExit(_main(sys.argv))

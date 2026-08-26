"""
gpu_claims.py — MẶT PHẲNG CHUNG CẤP MÁY cho việc giữ chỗ GPU.

MÃ Ở TRONG KHO, DỮ LIỆU Ở NGOÀI — và đó là chủ ý.

Bản đầu đặt cả tệp này trong thư mục dùng chung rồi cho mỗi hệ
sys.path.insert(0, ...) và import. Kiểm tra ACL cho thấy đó là lỗ hổng:
thư mục đó có quyền 'BUILTIN/Users : Write', nghĩa là BẤT KỲ tài khoản nào
trên máy cũng ghi đè được tệp này, và tiến trình dịch vụ (quyền cao, xử lý
thanh toán) sẽ nạp và chạy mã đó. insert(0) còn cho nó che khuất cả module
chuẩn.

Nên: MÃ nằm trong kho, đi qua git và deploy như mọi tệp khác. DỮ LIỆU
(claims/, policy.json) mới nằm ở thư mục chung — dữ liệu bị sửa thì tệ nhất
là xếp chỗ sai, không phải thực thi mã lạ.

═══════════════════════════════════════════════════════════════════════════════
 VẤN ĐỀ NÓ GIẢI
═══════════════════════════════════════════════════════════════════════════════
Máy này có nhiều hệ độc lập cùng dùng 2 card:

    LTTPlatform      sổ PostgreSQL, độc chiếm nguyên card, KHÁCH TRẢ TIỀN
    gpu_arbiter      sổ file, chia phần theo VRAM, 6 bot nội bộ
    Cut_only ver2    (trước đây không có sổ nào)

Cả hai hệ có sổ ĐỀU đã đọc `nvidia-smi` để kiểm VRAM thật, nên chúng không mù
nhau hoàn toàn. Nhưng còn đúng MỘT khoảng hở, và nó đủ để làm sập:

    CỬA SỔ NẠP MODEL — từ lúc một bên giành card tới lúc VRAM thật sự hiện ra
    trong nvidia-smi (20-60 giây). Trong khoảng đó `memory.free` NÓI DỐI với
    cả hai bên: bên kia nhìn vào vẫn thấy card trống và nhảy vào.

Module này KHÔNG thay thế sổ của ai. Nó chỉ công bố "tôi vừa giành chỗ" để bên
kia trừ ra khỏi VRAM đo được. Mỗi hệ giữ nguyên bộ não quyết định của mình.

═══════════════════════════════════════════════════════════════════════════════
 VÌ SAO MỖI CLAIM MỘT FILE (không phải một file JSON chung)
═══════════════════════════════════════════════════════════════════════════════
Một file JSON chung cần khoá ghi. Khoá giữa hai codebase khác nhau, khác
runtime, khác vòng đời là nguồn lỗi kinh điển — và chính dự án này đã dính:
nhiều tiến trình ghi chung một file tạm làm hỏng registry ("Extra data at
line N").

Ở đây mỗi claim là MỘT FILE RIÊNG trong thư mục `claims/`. Tạo file và xoá file
là thao tác nguyên tử trên NTFS. Không khoá, không tranh ghi, không hỏng file.
Đọc = liệt kê thư mục. Một claim hỏng cũng chỉ bỏ qua đúng claim đó.

═══════════════════════════════════════════════════════════════════════════════
 CÁCH DÙNG
═══════════════════════════════════════════════════════════════════════════════
    from platform_core import gpu_claims

    # Trước khi chọn card: xem chỗ người khác đã giữ mà nvidia-smi CHƯA thấy
    reserved = gpu_claims.reserved_mb_by_gpu(exclude_owner="lttplatform")
    free_thuc_te = g.free_mb - reserved.get(g.index, 0)

    # Card có được phép nhận job này không (luật màn hình/TDR)
    if not gpu_claims.gpu_allows(g.index, need_mb):
        continue

    # Sau khi giành được card, CÔNG BỐ ngay
    tok = gpu_claims.publish(owner="lttplatform", gpu_index=g.index,
                             mb=need_mb, job="abc123", exclusive=True)
    try:
        ...  # chạy việc
    finally:
        gpu_claims.release(tok)

AN TOÀN: mọi hàm đều nuốt lỗi và trả giá trị vô hại. Lớp này KHÔNG BAO GIỜ được
phép làm chết job của ai — hỏng claims thì tệ nhất là quay về hành vi cũ.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import time
from pathlib import Path

log = logging.getLogger(__name__)

_ROOT       = Path(r"C:\ProgramData\gpu_claims")
_CLAIM_DIR  = _ROOT / "claims"
_POLICY     = _ROOT / "policy.json"

# Claim quá hạn này coi như mồ côi (chủ chết mà không kịp dọn).
# Rộng hơn nhiều lần nhịp đập để một lần GC dài không cướp chỗ của job đang chạy.
CLAIM_STALE_S = 900.0

# Thứ tự ưu tiên — số NHỎ hơn = quan trọng hơn, được nhường.
PRIORITY = {
    "lttplatform": 1,     # khách trả tiền
    "gpu_arbiter": 2,     # bot sản xuất nội bộ
    "cut_only":    3,     # nền/lô
    "batch":       3,
}
DEFAULT_PRIORITY = 2


def _host() -> str:
    try:
        return socket.gethostname()
    except Exception as e:
        log.debug("gpu_claims bo qua loi: %s", e)
        return "?"


def _pid_alive(pid: int) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        if os.name == "nt":
            import ctypes
            h = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))
            if not h:
                return False
            try:
                code = ctypes.c_ulong()
                if ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code)):
                    return code.value == 259
                return False
            finally:
                ctypes.windll.kernel32.CloseHandle(h)
        os.kill(pid, 0)
        return True
    except Exception as e:
        log.debug("gpu_claims bo qua loi: %s", e)
        return False


def _ensure():
    try:
        _CLAIM_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        log.debug("gpu_claims bo qua loi: %s", e)


# ══════════════════════════════════════════════════════════════════════════════
# CHÍNH SÁCH CARD — luật tĩnh, áp cho MỌI hệ
# ══════════════════════════════════════════════════════════════════════════════

_DEFAULT_POLICY = {
    "_comment": "Luat cap may. Moi he dung GPU tren may nay phai tuan.",
    "gpus": {},
    "default_max_job_mb": 0,
}


def policy() -> dict:
    try:
        return json.loads(_POLICY.read_text(encoding="utf-8"))
    except Exception as e:
        log.debug("gpu_claims bo qua loi: %s", e)
        return dict(_DEFAULT_POLICY)


def gpu_allows(gpu_index: int, need_mb: int = 0) -> bool:
    """Card này có được phép nhận job cỡ `need_mb` không.

    Luật quan trọng nhất hiện nay: CARD MÀN HÌNH không nhận job nặng. Máy đã
    sập một lần với bugcheck 0x116 VIDEO_TDR_FAILURE vì một job ~12.6GB chạy
    100% suốt 9 phút trên card đang xuất hình — trình điều khiển hiển thị mất
    quyền điều khiển GPU quá hạn và reset thất bại.

    Trả True khi không có luật nào cấm (thiếu file chính sách → không chặn).
    """
    try:
        p = policy()
        g = (p.get("gpus") or {}).get(str(int(gpu_index)))
        if not g:
            cap = int(p.get("default_max_job_mb") or 0)
            return cap <= 0 or need_mb <= cap
        if not g.get("usable", True):
            return False
        cap = int(g.get("max_job_mb") or 0)
        return cap <= 0 or need_mb <= cap
    except Exception as e:
        log.debug("gpu_claims bo qua loi: %s", e)
        return True          # thiếu/hỏng chính sách → không chặn ai


def gpu_note(gpu_index: int) -> str:
    try:
        g = (policy().get("gpus") or {}).get(str(int(gpu_index))) or {}
        return str(g.get("note", ""))
    except Exception as e:
        log.debug("gpu_claims bo qua loi: %s", e)
        return ""


# ══════════════════════════════════════════════════════════════════════════════
# CLAIM — công bố / thu hồi / đọc
# ══════════════════════════════════════════════════════════════════════════════

def publish(owner: str, gpu_index: int, mb: int, job: str = "",
            exclusive: bool = False, ttl_s: float = CLAIM_STALE_S) -> str | None:
    """Công bố "tôi vừa giữ chỗ trên card này". Trả token để release. None nếu lỗi."""
    _ensure()
    try:
        tok = f"{_host()}-{os.getpid()}-{int(gpu_index)}-{int(time.time()*1000)%100000}"
        rec = {
            "owner": owner, "gpu": int(gpu_index), "mb": int(mb),
            "job": str(job)[:64], "exclusive": bool(exclusive),
            "pid": os.getpid(), "host": _host(),
            "since": time.time(), "ttl_s": float(ttl_s),
            "priority": PRIORITY.get(owner, DEFAULT_PRIORITY),
        }
        p = _CLAIM_DIR / f"{tok}.json"
        tmp = _CLAIM_DIR / f"{tok}.json.tmp"
        tmp.write_text(json.dumps(rec), encoding="utf-8")
        tmp.replace(p)                       # đổi tên = nguyên tử trên NTFS
        return tok
    except Exception as e:
        log.debug("gpu_claims bo qua loi: %s", e)
        return None


def heartbeat(token: str | None) -> bool:
    """Làm tươi claim cho job chạy dài (> CLAIM_STALE_S)."""
    if not token:
        return False
    try:
        p = _CLAIM_DIR / f"{token}.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        d["since"] = time.time()
        tmp = _CLAIM_DIR / f"{token}.json.tmp"
        tmp.write_text(json.dumps(d), encoding="utf-8")
        tmp.replace(p)
        return True
    except Exception as e:
        log.debug("gpu_claims bo qua loi: %s", e)
        return False


def release(token: str | None) -> bool:
    if not token:
        return False
    try:
        (_CLAIM_DIR / f"{token}.json").unlink(missing_ok=True)
        return True
    except Exception as e:
        log.debug("gpu_claims bo qua loi: %s", e)
        return False


def active(cleanup: bool = True) -> list[dict]:
    """Mọi claim còn sống. Tự dọn claim mồ côi (chủ chết / quá hạn)."""
    _ensure()
    out = []
    now = time.time()
    try:
        for f in _CLAIM_DIR.glob("*.json"):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except Exception as e:
                log.debug("gpu_claims bo qua loi: %s", e)
                continue                     # claim hỏng → bỏ qua đúng cái đó
            stale = (now - float(d.get("since", 0)) > float(d.get("ttl_s", CLAIM_STALE_S)))
            dead = (d.get("host") == _host() and not _pid_alive(int(d.get("pid", 0) or 0)))
            if stale or dead:
                if cleanup:
                    try:
                        f.unlink(missing_ok=True)
                    except Exception as e:
                        log.debug("gpu_claims bo qua loi: %s", e)
                continue
            d["_token"] = f.stem
            out.append(d)
    except Exception as e:
        log.debug("gpu_claims bo qua loi: %s", e)
    return out


def reserved_mb_by_gpu(exclude_owner: str | None = None,
                       only_unrealized_s: float | None = None) -> dict[int, int]:
    """Tổng MB đã được CÔNG BỐ trên mỗi card, theo claim của các hệ khác.

    exclude_owner      : bỏ qua claim của chính mình (mình đã tự tính rồi).
    only_unrealized_s  : chỉ tính claim mới hơn ngần này giây — dùng khi caller
                         ĐÃ trừ VRAM đo thật, để không tính hai lần. Claim cũ thì
                         VRAM của nó đã hiện trong nvidia-smi rồi.
    """
    agg: dict[int, int] = {}
    now = time.time()
    for c in active():
        if exclude_owner and c.get("owner") == exclude_owner:
            continue
        if only_unrealized_s is not None:
            if now - float(c.get("since", 0)) > only_unrealized_s:
                continue
        g = int(c.get("gpu", 0))
        agg[g] = agg.get(g, 0) + int(c.get("mb", 0))
    return agg


def exclusive_gpus(exclude_owner: str | None = None) -> set[int]:
    """Card đang bị một hệ đòi ĐỘC CHIẾM (vd LTTPlatform giữ nguyên card)."""
    out = set()
    for c in active():
        if exclude_owner and c.get("owner") == exclude_owner:
            continue
        if c.get("exclusive"):
            out.add(int(c.get("gpu", 0)))
    return out


def blocking_priority(gpu_index: int, my_owner: str) -> list[dict]:
    """Claim trên card này có ưu tiên CAO HƠN mình (mình phải nhường)."""
    mine = PRIORITY.get(my_owner, DEFAULT_PRIORITY)
    return [c for c in active()
            if int(c.get("gpu", -1)) == int(gpu_index)
            and c.get("owner") != my_owner
            and int(c.get("priority", DEFAULT_PRIORITY)) < mine]


def summary() -> str:
    cs = active()
    if not cs:
        return "(khong co claim nao)"
    lines = []
    for c in sorted(cs, key=lambda x: (x.get("gpu", 0), x.get("priority", 9))):
        age = int(time.time() - float(c.get("since", 0)))
        lines.append(f"  gpu{c.get('gpu')}  {c.get('owner'):<14} "
                     f"{c.get('mb'):>6}MB  p{c.get('priority')}  "
                     f"{'DOC-CHIEM' if c.get('exclusive') else 'chia-se':<9} "
                     f"{age}s  job={c.get('job','')[:16]}")
    return "\n".join(lines)


if __name__ == "__main__":
    print("Chinh sach card:")
    p = policy()
    for k, v in sorted((p.get("gpus") or {}).items()):
        print(f"  gpu{k}: usable={v.get('usable', True)} "
              f"max_job_mb={v.get('max_job_mb')} — {v.get('note','')}")
    print()
    print("Claim dang hoat dong:")
    print(summary())

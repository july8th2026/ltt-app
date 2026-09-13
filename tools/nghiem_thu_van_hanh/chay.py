"""chay.py — bộ chạy và **cổng nhiễu**.

Điểm vào của chương trình: `docs/VAN_HANH_THAT.md`.

## 🔴 Vì sao cổng nhiễu quan trọng hơn bộ chạy

Ngày 13/09/2026 một lượt đo bão hoà chạy trúng cửa sổ deploy của phiên khác. Cả
sáu job chết cùng một khắc ở giây 14,15, và kết quả trông **y hệt** một phát hiện
lớn: *"6 job đồng thời làm sập hệ"*. Nó sai hoàn toàn.

⛔ Một phép đo bị nhiễm cho ra kết luận **trông rất chắc chắn**. Nó không tự khai
   mình bẩn — người đọc phải tự biết. Cổng này làm việc tự-biết ấy thành cơ học.

## `None` ≠ `False`

| | nghĩa |
|---|---|
| `dat=True` | hệ hành xử đúng kỳ vọng |
| `dat=False` | hệ **hỏng** — đây là một phát hiện |
| `dat=None` | **ta chưa biết** — phép đo bị nhiễm, chạy lại |

Lẫn lộn hai dòng cuối là cách một bộ đo sinh ra kết luận sai mà rất tự tin.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from tools.nghiem_thu_van_hanh import soi
from tools.nghiem_thu_van_hanh.kich_ban import KichBan


@dataclass
class KetQuaKichBan:
    ma: str
    #: `None` = NHIỄU, không kết luận. Xem docstring module.
    dat: bool | None
    nhiem: bool
    mau: list[dict]
    truoc: dict
    sau: dict
    ly_do_nhiem: str = ""
    do_duoc: dict[str, Any] = field(default_factory=dict)


def co_nhiem(truoc: dict, sau: dict) -> tuple[bool, str]:
    """Lượt đo này có bị nhiễm không, và vì sao.

    Bốn tín hiệu dưới đây **đều là chuyện đã xảy ra**, không phải giả định
    phòng xa — xem `tests/test_1253_chay_va_cong_nhieu.py`.
    """
    # 1. Production đổi bản GIỮA lượt đo (một phiên khác deploy).
    c1 = (truoc.get("http").gia_tri if truoc.get("http") else None)
    c2 = (sau.get("http").gia_tri if sau.get("http") else None)
    if c1 and c2 and c1 != c2:
        return True, f"production doi commit giua luot do: {c1} -> {c2}"

    # 2. Nền không sạch lúc bắt đầu — đo một hệ đã đầy sẵn.
    t_lease = truoc.get("lease")
    if t_lease is not None and t_lease.doc_duoc and (t_lease.gia_tri or 0) > 0:
        return True, (f"nen KHONG sach: {t_lease.gia_tri} lease stream da song "
                      "truoc khi bat dau")

    # 3. Một sổ mù ở bất kỳ đầu nào.
    for nhan, chup in (("truoc", truoc), ("sau", sau)):
        for m in chup.values():
            if not m.doc_duoc:
                return True, f"so `{m.ten}` MU o dau {nhan}: {m.ly_do}"

    return False, ""


def tong_ket(ds: Iterable[KetQuaKichBan]) -> dict:
    """Đếm, và **đếm riêng** lượt nhiễm.

    ⛔ Lượt nhiễm không được vào mẫu số. Tính nó là "trượt" thì ta báo động giả;
       tính là "đạt" thì ta giấu một lượt chưa đo được.
    """
    ds = list(ds)
    dat = sum(1 for k in ds if k.dat is True)
    truot = sum(1 for k in ds if k.dat is False)
    nhiem = sum(1 for k in ds if k.nhiem)
    return {"dat": dat, "truot": truot, "nhiem": nhiem,
            "tong_ket_luan_duoc": dat + truot, "tong": len(ds)}


def chup_sau_so(db_url: str, goc: str) -> dict:
    """Chụp cả sáu sổ. **Không ném** — cổng nhiễu cần thấy cả sổ mù."""
    return {m.ten: m for m in (
        soi.so_lease(db_url), soi.so_jobs(db_url), soi.so_credit(db_url),
        soi.so_residency(db_url), soi.so_http(goc), soi.so_slot(8282))}


def chay_mot(kb: KichBan, *, db_url: str, goc: str,
             nop: Callable[[KichBan], dict],
             lay_mau: Callable[[], dict] | None = None,
             nhip_s: float = 1.0) -> KetQuaKichBan:
    """Chạy một kịch bản: chụp sổ → nộp tải → chụp lại → qua cổng nhiễu.

    `nop` là đường ra ngoài duy nhất; phép kiểm thay nó bằng bản giả nên bộ này
    **không bao giờ gọi production** trong test.
    """
    truoc = chup_sau_so(db_url, goc)
    mau: list[dict] = []
    t0 = time.monotonic()
    try:
        do_duoc = nop(kb)
    except Exception as e:  # noqa: BLE001
        do_duoc = {"loi": f"{type(e).__name__}: {e}"[:200]}
    if lay_mau is not None:
        mau.append({"t": round(time.monotonic() - t0, 2), **lay_mau()})
    sau = chup_sau_so(db_url, goc)

    nhiem, ly_do = co_nhiem(truoc, sau)
    if nhiem:
        return KetQuaKichBan(kb.ma, None, True, mau, _tho(truoc), _tho(sau),
                             ly_do, do_duoc)
    return KetQuaKichBan(kb.ma, _cham(kb, do_duoc), False, mau,
                         _tho(truoc), _tho(sau), "", do_duoc)


def _cham(kb: KichBan, do_duoc: dict) -> bool | None:
    """So kỳ vọng với số đo được.

    ⚠️ Trả `None` khi **chưa đủ dữ kiện để chấm** — vẫn là "ta chưa biết", không
       phải "hỏng". Chỉ trả `False` khi một kỳ vọng cụ thể bị bác.
    """
    if "loi" in do_duoc:
        return None
    co_cham = False
    for khoa, mong in kb.mong_doi.items():
        if khoa not in do_duoc:
            continue
        co_cham = True
        that = do_duoc[khoa]
        if isinstance(mong, bool):
            if bool(that) != mong:
                return False
        elif isinstance(mong, (int, float)):
            if khoa.endswith("_toi_da_s") or khoa.endswith("_toi_da"):
                if that > mong:
                    return False
            elif that != mong:
                return False
    return True if co_cham else None


def _tho(chup: dict) -> dict:
    return {t: {"gia_tri": m.gia_tri, "doc_duoc": m.doc_duoc, "ly_do": m.ly_do}
            for t, m in chup.items()}


def ghi_ban_ghi(ds: list[KetQuaKichBan], duong: str) -> dict:
    ban = {"tong_ket": tong_ket(ds),
           "kich_ban": [{"ma": k.ma, "dat": k.dat, "nhiem": k.nhiem,
                         "ly_do_nhiem": k.ly_do_nhiem, "do_duoc": k.do_duoc,
                         "truoc": k.truoc, "sau": k.sau, "mau": k.mau}
                        for k in ds]}
    with open(duong, "w", encoding="utf-8") as f:
        json.dump(ban, f, ensure_ascii=False, indent=2)
    return ban

# Bộ nghiệm thu vận hành thật — Kế hoạch triển khai

> **Cho người thực thi:** SUB-SKILL BẮT BUỘC — dùng `superpowers:subagent-driven-development`
> (khuyến nghị) hoặc `superpowers:executing-plans` để làm từng task một.
> Các bước dùng cú pháp checkbox (`- [ ]`) để theo dõi.

**Mục tiêu:** Dựng một bộ đo giả lập người dùng thật gọi vào production, đi xuyên
`API → job → admission → queue → runtime → GPU → stream/result → credit`, và trả
về một bảng 23 tham số đọc được.

**Kiến trúc:** Một **lớp quan sát dùng chung** (sáu sổ, mỗi sổ một hàm, tự kiểm
khi khởi động) + **ma trận kịch bản là dữ liệu**. Bộ chạy nộp tải theo khai báo,
lấy mẫu, ghi một bản ghi JSON; bộ báo cáo sinh bảng từ bản ghi ấy.

**Công nghệ:** Python 3.13 · `httpx` · SQLAlchemy (chỉ đọc) · `ssh` tới máy B ·
pytest.

**Spec:** `docs/superpowers/specs/2026-09-13-nghiem-thu-van-hanh-design.md`

## Ràng buộc toàn cục

Mọi task đều ngầm mang những điều này.

| | |
|---|---|
| **`tools/` NẰM TRONG tầm quét mypy** | `THU_MUC_QUET = ('apps','platform_core','server','tools','llm_gateway','render_gateway','sdk','nexus_agent')`. Chạy `py tools\check_mypy.py` **trước mỗi commit**, không đợi gate |
| `sys.stdout.reconfigure` | **phải** bọc `if hasattr(sys.stdout, "reconfigure"):` — gọi thẳng làm `union-attr` tăng và gate đỏ |
| Kết dòng | tệp mới dùng **LF**. Không bao giờ sửa kết dòng của tệp đã có |
| `git add` | **tường minh từng tệp**, không `-A`, không `.` |
| Lệnh nặng | `py tools\cua_so_yen.py trang-thai` trước; có phiên khác giữ thì **chờ**. Tối đa `-n 6` |
| Bí mật | không commit `data/config.json`, `data/*.enc`, `secrets/`, `cloudflare/*` |
| Sáu sổ | **CHỈ ĐỌC**. Bộ đo chỉ tạo/huỷ job qua API công khai |
| Phép kiểm của bộ đo | **không được gọi production**. Dùng bản giả; đường thật chỉ chạy ở Pha 0 |
| Bản giả | bên tiêu thụ phải **khoan dung** (`getattr`, `**kw`) — bản giả đóng vai *một việc*, không đóng vai *chữ ký* |

## Cấu trúc tệp

| tệp | trách nhiệm |
|---|---|
| `tools/nghiem_thu_van_hanh/__init__.py` | rỗng, đánh dấu gói |
| `tools/nghiem_thu_van_hanh/soi.py` | **sáu sổ** + `tu_kiem()`. Không biết gì về kịch bản |
| `tools/nghiem_thu_van_hanh/kich_ban.py` | **dữ liệu** 16 kịch bản + kiểm tính hợp lệ. Không gọi mạng |
| `tools/nghiem_thu_van_hanh/chay.py` | bộ chạy: nộp, lấy mẫu, cổng nhiễu, ghi bản ghi |
| `tools/nghiem_thu_van_hanh/bao_cao.py` | bản ghi JSON → bảng 23 tham số. **Hàm thuần** |
| `tests/test_1250_soi_sau_so.py` | phép kiểm cho `soi.py` |
| `tests/test_1251_kich_ban_hop_le.py` | phép kiểm cho `kich_ban.py` |
| `tests/test_1252_chay_va_cong_nhieu.py` | phép kiểm cho `chay.py` |
| `tests/test_1253_bao_cao.py` | phép kiểm cho `bao_cao.py` |

⚠️ Dải 1250–1253 chọn theo `docs/...dai-test-cap-cho-tung-chuong-trinh` — kiểm
lại dải còn trống trước khi tạo, đừng giả định.

---

## Task 1 — `soi.py`: sáu sổ và vòng tự kiểm

**Tệp:**
- Tạo: `tools/nghiem_thu_van_hanh/__init__.py`
- Tạo: `tools/nghiem_thu_van_hanh/soi.py`
- Kiểm: `tests/test_1250_soi_sau_so.py`

**Giao diện:**
- Tiêu thụ: không có (task đầu)
- Sản xuất:
  ```python
  @dataclass(frozen=True)
  class MauSo:
      ten: str            # "lease" | "jobs" | "credit" | "slot" | "residency" | "http"
      gia_tri: Any
      doc_duoc: bool      # False = sổ không trả lời được
      ly_do: str = ""

  def so_lease(db_url: str) -> MauSo
  def so_jobs(db_url: str, *, nhan: str) -> MauSo
  def so_credit(db_url: str) -> MauSo
  def so_slot(cong: int) -> MauSo          # 8282 = 3.8, 8281 = 3.5
  def so_residency(db_url: str) -> MauSo
  def so_http(goc: str) -> MauSo           # /health/version -> commit
  def tu_kiem(db_url: str, goc: str) -> list[MauSo]   # NÉM nếu sổ nào doc_duoc=False
  ```

- [ ] **Bước 1: Viết phép kiểm thất bại — sổ slot đọc đúng tên chỉ số**

```python
# tests/test_1250_soi_sau_so.py
"""test_1250 — sau so quan sat. Moi so phai TU KHAI khi no khong doc duoc.

🔴 Bo nay sinh ra tu mot loi that ngay 13/09: phep do `requests_processing`
   tra `-1` suot vi sai cong (8299 tra 404) va thieu tien to `llamacpp:`.
   **`-1` trong y het `0`** — mot phep do mu mot mat ma van bao so.
"""
from tools.nghiem_thu_van_hanh import soi

_METRICS = """\
# HELP llamacpp:requests_processing Number of requests processing
# TYPE llamacpp:requests_processing gauge
llamacpp:requests_processing 3
llamacpp:requests_deferred 1
"""


def test_so_slot_doc_dung_ten_co_TIEN_TO(monkeypatch):
    monkeypatch.setattr(soi, "_curl_may_b", lambda cong: _METRICS)
    m = soi.so_slot(8282)
    assert m.doc_duoc is True
    assert m.gia_tri == 3


def test_so_slot_KHONG_doc_duoc_thi_TU_KHAI_chu_khong_tra_so(monkeypatch):
    """⛔ Khong duoc tra -1. Mot so am se bi doc thanh 'slot da nha'."""
    monkeypatch.setattr(soi, "_curl_may_b", lambda cong: "")
    m = soi.so_slot(8282)
    assert m.doc_duoc is False
    assert m.ly_do
```

- [ ] **Bước 2: Chạy để chắc nó đỏ**

Chạy: `py -m pytest tests/test_1250_soi_sau_so.py -q`
Mong đợi: FAIL — `ModuleNotFoundError: tools.nghiem_thu_van_hanh`

- [ ] **Bước 3: Viết bản cài đặt tối thiểu**

```python
# tools/nghiem_thu_van_hanh/soi.py
"""soi.py — sau so quan sat cua bo nghiem thu van hanh.

⛔ MOI SO CHI DOC. Bo do khong ghi vao CSDL, khong sua cau hinh, khong dung
   dich vu. Thu duy nhat no tao ra la job qua API cong khai — y nhu mot khach.

🔴 MOI SO PHAI TU KHAI KHI KHONG DOC DUOC, thay vi tra mot so.
   Ngay 13/09 mot phep do tra `-1` suot vi sai cong va thieu tien to
   `llamacpp:`. `-1` trong y het `0`, nen ca mot luot do chay xong roi moi lo ra
   la mu mot mat. `MauSo.doc_duoc` ton tai de dieu do khong lap lai.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
from dataclasses import dataclass
from typing import Any

if hasattr(sys.stdout, "reconfigure"):      # loi cua kho; goi thang lam mypy tang
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MAY_B = "lengo@192.168.2.66"
CONG_38, CONG_35 = 8282, 8281


@dataclass(frozen=True)
class MauSo:
    ten: str
    gia_tri: Any
    doc_duoc: bool
    ly_do: str = ""


def _curl_may_b(cong: int) -> str:
    r = subprocess.run(
        ["ssh", "-i", str(pathlib.Path.home() / ".ssh" / "nexus_b"),
         "-o", "BatchMode=yes", MAY_B,
         f"curl.exe -s -m 10 http://127.0.0.1:{cong}/metrics"],
        capture_output=True, text=True, timeout=90)
    return r.stdout or ""


def so_slot(cong: int) -> MauSo:
    """So luot may B DANG XU LY tren mot cong.

    ⛔ Ten chi so mang TIEN TO `llamacpp:`. Mot phep loc
       `startswith("requests_processing")` khong bao gio khop.
    ⛔ `/metrics` KHONG o cong 8299 (gateway tra 404) ma o cong cua chinh
       `llama-server`: 8282 cho ltt-3.8, 8281 cho ltt-3.5.
    """
    ra = _curl_may_b(cong)
    for dong in ra.splitlines():
        d = dong.strip()
        if d.startswith("llamacpp:requests_processing"):
            try:
                return MauSo("slot", int(float(d.split()[-1])), True)
            except (ValueError, IndexError):
                return MauSo("slot", None, False, f"khong doc duoc so: {d!r}")
    return MauSo("slot", None, False,
                 f"cong {cong} khong tra `llamacpp:requests_processing`")
```

- [ ] **Bước 4: Chạy để chắc nó xanh**

Chạy: `py -m pytest tests/test_1250_soi_sau_so.py -q`
Mong đợi: PASS (2 vế)

- [ ] **Bước 5: Thêm năm sổ còn lại, mỗi sổ một cặp vế kiểm**

Cùng khuôn: một vế *"đọc đúng"*, một vế *"không đọc được thì tự khai"*.

```python
def so_lease(db_url: str) -> MauSo:
    """So suat may A DANG cap, theo `resource`."""
    cau = ("SELECT resource, COUNT(*) FROM execution_leases GROUP BY resource")
    try:
        hang = _truy_van(db_url, cau)
    except Exception as e:                                  # noqa: BLE001
        return MauSo("lease", None, False, f"{type(e).__name__}: {e}")
    return MauSo("lease", {str(r[0]): int(r[1]) for r in hang}, True)


def so_residency(db_url: str) -> MauSo:
    try:
        hang = _truy_van(db_url, "SELECT trang_thai FROM gpu_residency")
    except Exception as e:                                  # noqa: BLE001
        return MauSo("residency", None, False, f"{type(e).__name__}: {e}")
    if not hang:
        return MauSo("residency", None, False, "bang gpu_residency rong")
    return MauSo("residency", str(hang[0][0]), True)
```

- [ ] **Bước 6: Viết vế kiểm cho `tu_kiem` — thiếu một sổ thì NÉM**

```python
def test_tu_kiem_NEM_khi_thieu_mot_so(monkeypatch):
    """⛔ Chay tiep khi mot so cam la do mu mot mat. Phai dung ON AO."""
    monkeypatch.setattr(soi, "so_slot",
                        lambda cong: soi.MauSo("slot", None, False, "cam"))
    with pytest.raises(soi.SoCamError) as e:
        soi.tu_kiem("sqlite://", "https://x")
    assert "slot" in str(e.value)
```

- [ ] **Bước 7: Cài `tu_kiem` + `SoCamError`, chạy lại**

Chạy: `py -m pytest tests/test_1250_soi_sau_so.py -q`
Mong đợi: PASS, **≥ 13 vế** (6 sổ × 2 + tự kiểm)

- [ ] **Bước 8: Bánh cóc — ruff, mypy, kết dòng**

```bash
py -m ruff check tools/nghiem_thu_van_hanh/ tests/test_1250_soi_sau_so.py
py tools\check_mypy.py
```
Mong đợi: `All checks passed!` và `[mypy] dat moc`

⚠️ Nếu mypy **tăng**: sửa, đừng `--accept`. `tools/` nằm trong tầm quét, và một
`sys.stdout.reconfigure` gọi thẳng là đủ làm gate đỏ.

- [ ] **Bước 9: Commit**

```bash
git add tools/nghiem_thu_van_hanh/__init__.py tools/nghiem_thu_van_hanh/soi.py tests/test_1250_soi_sau_so.py
git commit -m "feat(nghiem thu): sau so quan sat, moi so TU KHAI khi khong doc duoc"
```

---

## Task 2 — `kich_ban.py`: ma trận là dữ liệu

**Tệp:**
- Tạo: `tools/nghiem_thu_van_hanh/kich_ban.py`
- Kiểm: `tests/test_1251_kich_ban_hop_le.py`

**Giao diện:**
- Tiêu thụ: không (dữ liệu thuần, không gọi `soi`)
- Sản xuất:
  ```python
  @dataclass(frozen=True)
  class KichBan:
      ma: str                  # "J1", "C3", "X2"
      mo_ta: str
      cua: str                 # "job" | "stream" | "dong_bo"
      tai: tuple[tuple[str, int], ...]   # (("ltt-3.8", 3), ("ltt-3.5", 3))
      mong_doi: dict[str, Any]
      can_tai_khoan_hai: bool = False

  MA_TRAN: tuple[KichBan, ...]      # 16 kịch bản
  def kiem_hop_le(ks: Iterable[KichBan]) -> list[str]   # danh sách lỗi khai báo
  ```

- [ ] **Bước 1: Viết phép kiểm thất bại**

```python
# tests/test_1251_kich_ban_hop_le.py
"""test_1251 — ma tran kich ban la DU LIEU, va du lieu phai tu nhat quan.

⭐ Nguyen tac spec: moi kich ban phai CO KHA NANG HONG theo mot cach noi len
   dieu gi do. Mot kich ban khong the do thi khong chung minh gi — dung lop
   "cua gia" trong so tay du an.
"""
from tools.nghiem_thu_van_hanh import kich_ban


def test_du_16_kich_ban():
    assert len(kich_ban.MA_TRAN) == 16


def test_ma_KHONG_trung():
    ma = [k.ma for k in kich_ban.MA_TRAN]
    assert len(ma) == len(set(ma)), f"ma trung: {ma}"


def test_moi_kich_ban_co_MONG_DOI_kiem_duoc():
    """Khong mong doi = khong the do. Mot dong khai suong."""
    for k in kich_ban.MA_TRAN:
        assert k.mong_doi, f"{k.ma} khong khai mong doi"


def test_tai_khong_vuot_tran_tru_khi_CO_Y():
    """Tran la 3 moi model. Vuot thi phai khai `mong_doi['queued']`."""
    for k in kich_ban.MA_TRAN:
        for model, n in k.tai:
            if n > 3:
                assert "queued" in k.mong_doi, (
                    f"{k.ma} nop {n} luot cho {model} (tran 3) ma khong khai "
                    "so luot phai xep hang")


def test_kich_ban_can_tai_khoan_hai_duoc_DANH_DAU():
    can = [k.ma for k in kich_ban.MA_TRAN if k.can_tai_khoan_hai]
    assert can == ["X2"], (
        "chi X2 can tai khoan thu hai; neu them cai khac phai sua ca spec")
```

- [ ] **Bước 2: Chạy để chắc nó đỏ**

Chạy: `py -m pytest tests/test_1251_kich_ban_hop_le.py -q`
Mong đợi: FAIL — `ModuleNotFoundError`

- [ ] **Bước 3: Viết `kich_ban.py` với đủ 16 dòng**

```python
# tools/nghiem_thu_van_hanh/kich_ban.py
"""kich_ban.py — MA TRAN la DU LIEU, khong phai ma.

Them mot tinh huong la them MOT DONG khai, khong phai mot tep moi. Do la ca
diem cua kien truc nay: lop quan sat viet DUNG MOT LAN, nen mot sai sot trong
no lo ra mot lan chu khong nhan len 16 lan.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

#: Tran moi model, doc tu `apps/ltt_llm/ngan_sach.py:415` (`SO_SLOT_MAY_B`).
TRAN_MOI_MODEL = 3
TRAN_TOAN_HE = TRAN_MOI_MODEL * 2


@dataclass(frozen=True)
class KichBan:
    ma: str
    mo_ta: str
    cua: str
    tai: tuple[tuple[str, int], ...]
    mong_doi: dict[str, Any] = field(default_factory=dict)
    can_tai_khoan_hai: bool = False


MA_TRAN: tuple[KichBan, ...] = (
    KichBan("J1", "mot job 3.8 — do nen sach", "job",
            (("ltt-3.8", 1),), {"chay_ngay": 1}),
    KichBan("J2", "hai job, moi model mot", "job",
            (("ltt-3.8", 1), ("ltt-3.5", 1)),
            {"chay_ngay": 2, "resource_khac_nhau": True}),
    # ... 14 dòng còn lại, mỗi dòng khai `mong_doi` kiểm được
)
```

- [ ] **Bước 4: Chạy lại tới khi cả 5 vế xanh**

Chạy: `py -m pytest tests/test_1251_kich_ban_hop_le.py -q`
Mong đợi: PASS (5 vế)

- [ ] **Bước 5: Bánh cóc + commit**

```bash
py -m ruff check tools/nghiem_thu_van_hanh/kich_ban.py tests/test_1251_kich_ban_hop_le.py
py tools\check_mypy.py
git add tools/nghiem_thu_van_hanh/kich_ban.py tests/test_1251_kich_ban_hop_le.py
git commit -m "feat(nghiem thu): ma tran 16 kich ban la du lieu, tu kiem nhat quan"
```

---

## Task 3 — `chay.py`: bộ chạy và cổng nhiễu

**Tệp:**
- Tạo: `tools/nghiem_thu_van_hanh/chay.py`
- Kiểm: `tests/test_1252_chay_va_cong_nhieu.py`

**Giao diện:**
- Tiêu thụ: `soi.MauSo`, `soi.tu_kiem`, `kich_ban.KichBan`, `kich_ban.MA_TRAN`
- Sản xuất:
  ```python
  @dataclass
  class KetQuaKichBan:
      ma: str
      dat: bool | None      # None = NHIỄU, không kết luận
      nhiem: bool
      mau: list[dict]       # mẫu lấy trong lúc chạy
      truoc: dict           # sáu sổ trước
      sau: dict             # sáu sổ sau

  def co_nhiem(truoc: dict, sau: dict) -> tuple[bool, str]
  def chay_mot(kb, *, khach, soi_mod, dong_ho) -> KetQuaKichBan
  def chay_tat_ca(...) -> dict          # bản ghi JSON đầy đủ
  ```

- [ ] **Bước 1: Viết phép kiểm cho cổng nhiễu**

```python
# tests/test_1252_chay_va_cong_nhieu.py
"""test_1252 — cong NHIEM. Mot phep do bi nhiem phai bi LOAI, khong duoc dien giai.

🔴 Bai hoc 13/09: mot phep do bi nhieu cho ra ket luan trong rat chac chan va
   hoan toan sai. L-08 do duoc "99 s" tren mot may chu chua mang ban va, va toi
   suyt ket luan ban va "chay cham" trong khi no CHUA HE CHAY.
"""
from tools.nghiem_thu_van_hanh import chay


def test_residency_roi_llm_la_NHIEM():
    truoc = {"residency": "llm", "job_nguoi_khac": 0}
    sau = {"residency": "anh", "job_nguoi_khac": 0}
    nhiem, ly_do = chay.co_nhiem(truoc, sau)
    assert nhiem is True
    assert "residency" in ly_do


def test_job_nguoi_khac_chen_vao_la_NHIEM():
    truoc = {"residency": "llm", "job_nguoi_khac": 0}
    sau = {"residency": "llm", "job_nguoi_khac": 2}
    nhiem, ly_do = chay.co_nhiem(truoc, sau)
    assert nhiem is True


def test_nen_sach_thi_KHONG_nhiem():
    truoc = sau = {"residency": "llm", "job_nguoi_khac": 0}
    assert chay.co_nhiem(truoc, sau)[0] is False


def test_kich_ban_NHIEM_tra_dat_None_chu_khong_False():
    """⛔ `False` nghia la 'do duoc va TRUOT'. `None` nghia la 'khong do duoc'.
       Gop hai cai lam mot la bien mot phep do hong thanh mot phat hien."""
    kq = chay.KetQuaKichBan(ma="J4", dat=None, nhiem=True, mau=[],
                            truoc={}, sau={})
    assert kq.dat is None and kq.nhiem is True
```

- [ ] **Bước 2: Chạy để chắc nó đỏ**

Chạy: `py -m pytest tests/test_1252_chay_va_cong_nhieu.py -q`
Mong đợi: FAIL — `ModuleNotFoundError`

- [ ] **Bước 3: Cài `co_nhiem` và `KetQuaKichBan`**

```python
def co_nhiem(truoc: dict, sau: dict) -> tuple[bool, str]:
    """Phep do co bi thu ngoai lam sai lech khong.

    ⛔ Pham vi la "chi LLM", nhung mot KHACH THAT co the nop job anh giua phep
       do va trong tai se lay 3090 di. Luc do `ltt-3.8` co 0 slot thay vi 3, va
       moi con so cua kich ban ay vo nghia.

    ⇒ Bo do KHONG ngan dieu do — no PHAT HIEN va danh dau, thay vi bao mot so
      sai. Danh dau roi chay lai; khong dien giai.
    """
    if truoc.get("residency") != "llm" or sau.get("residency") != "llm":
        return True, (f"residency {truoc.get('residency')} -> "
                      f"{sau.get('residency')}, khong o `llm` suot kich ban")
    if int(sau.get("job_nguoi_khac") or 0) > int(truoc.get("job_nguoi_khac") or 0):
        return True, "co job cua nguoi khac chen vao giua kich ban"
    return False, ""
```

- [ ] **Bước 4: Chạy lại**

Chạy: `py -m pytest tests/test_1252_chay_va_cong_nhieu.py -q`
Mong đợi: PASS (4 vế)

- [ ] **Bước 5: Viết vế kiểm cho ba điều kiện DỪNG**

```python
def test_ro_lease_thi_DUNG_chu_khong_chay_tiep(monkeypatch):
    """Ro chong ro thi kich ban gay ra bien mat trong dong."""
    with pytest.raises(chay.DungNgayError) as e:
        chay._kiem_sau_kich_ban({"lease": {"ltt_38_3090": 2}})
    assert "lease" in str(e.value)
```

- [ ] **Bước 6: Cài `DungNgayError` + `_kiem_sau_kich_ban`, chạy lại**

Mong đợi: PASS (≥ 6 vế)

- [ ] **Bước 7: Cài `chay_mot` và `chay_tat_ca` với bản giả**

⚠️ Phép kiểm **không** gọi production. Truyền `khach` và `soi_mod` vào để thay
bằng bản giả. Bên tiêu thụ đọc bằng `getattr(..., default)` — bản giả đóng vai
*một việc*, không đóng vai *chữ ký*.

- [ ] **Bước 8: Bánh cóc + commit**

```bash
py -m ruff check tools/nghiem_thu_van_hanh/chay.py tests/test_1252_chay_va_cong_nhieu.py
py tools\check_mypy.py
git add tools/nghiem_thu_van_hanh/chay.py tests/test_1252_chay_va_cong_nhieu.py
git commit -m "feat(nghiem thu): bo chay + cong nhiem + ba dieu kien dung ngay"
```

---

## Task 4 — `bao_cao.py`: bản ghi → bảng 23 tham số

**Tệp:**
- Tạo: `tools/nghiem_thu_van_hanh/bao_cao.py`
- Kiểm: `tests/test_1253_bao_cao.py`

**Giao diện:**
- Tiêu thụ: bản ghi JSON do `chay.chay_tat_ca` sinh
- Sản xuất:
  ```python
  def bang_chat_luong(ban_ghi: dict) -> str          # Markdown
  def tham_so_do_duoc(ban_ghi: dict) -> dict[str, Any]   # 23 khoá
  ```

- [ ] **Bước 1: Viết phép kiểm — hàm THUẦN, không I/O**

```python
# tests/test_1253_bao_cao.py
"""test_1253 — bao cao la HAM THUAN tu ban ghi sang bang.

⭐ Thuan co chu dich: mot bao cao goi mang la mot bao cao KHONG tai lap duoc tu
   ban ghi da luu, va luc do ban ghi mat gia tri lam bang chung.
"""
from tools.nghiem_thu_van_hanh import bao_cao

_BAN_GHI = {
    "commit_production": "6f1606267eaf",
    "kich_ban": [
        {"ma": "J4", "dat": True, "nhiem": False,
         "dinh": {"lease": 6, "slot": 6}},
        {"ma": "J5", "dat": None, "nhiem": True, "dinh": {}},
    ],
}


def test_kich_ban_NHIEM_khong_vao_bang():
    b = bao_cao.bang_chat_luong(_BAN_GHI)
    assert "J4" in b
    assert "J5" in b and "NHIỄU" in b, "kich ban nhiem phai HIEN nhung khong tinh diem"


def test_bang_mang_theo_COMMIT_PRODUCTION():
    """🔴 Mot con so khong gan voi ban sinh ra no thi khong tai lap duoc."""
    assert "6f1606267eaf" in bao_cao.bang_chat_luong(_BAN_GHI)


def test_lech_lease_va_slot_duoc_tinh():
    ts = bao_cao.tham_so_do_duoc(_BAN_GHI)
    assert ts["lech_lease_slot_tai_dinh"] == 0
```

- [ ] **Bước 2: Chạy để chắc nó đỏ** — `ModuleNotFoundError`

- [ ] **Bước 3: Cài `bao_cao.py`**

- [ ] **Bước 4: Chạy lại** — PASS (3 vế)

- [ ] **Bước 5: Bánh cóc + commit**

```bash
git add tools/nghiem_thu_van_hanh/bao_cao.py tests/test_1253_bao_cao.py
git commit -m "feat(nghiem thu): bang chat luong 23 tham so tu ban ghi, ham thuan"
```

---

## Task 5 — Pha 0: tự chứng minh bộ đo không mù

⚠️ Task này **chạy trên production**. Nó không có phép kiểm tự động — nó *là*
phép kiểm.

- [ ] **Bước 1: Chạy vòng tự kiểm sáu sổ**

```bash
py -m tools.nghiem_thu_van_hanh.chay --tu-kiem
```
Mong đợi: **6/6 sổ trả lời được**. Thiếu một sổ ⇒ dừng, sửa `soi.py`, không đi tiếp.

- [ ] **Bước 2: Chạy J1 và J2 — hai kịch bản hệ thống CHẮC CHẮN làm đúng**

```bash
py -m tools.nghiem_thu_van_hanh.chay --kich-ban J1,J2
```
Mong đợi: cả hai **ĐẠT**.

🔴 **Chúng đỏ ⇒ lỗi ở BỘ ĐO, không ở hệ thống.** Đây là điểm của Pha 0: không có
nó, lượt đo đầu tiên sẽ trộn lỗi hệ thống với lỗi bộ đo. Ngày 13/09 chuyện ấy
xảy ra **ba lần** — phép dò trả `-1`, gọi nhầm cửa stream, dựng prompt quá cỡ —
và cả ba đều trông như lỗi hệ thống ở lần đọc đầu.

- [ ] **Bước 3: Kiểm bộ đo không để lại rác**

```bash
py -m tools.nghiem_thu_van_hanh.chay --don-rac
```
Mong đợi: `execution_leases = 0`, không job nào mang nhãn bộ đo còn sống.

- [ ] **Bước 4: Commit bản ghi Pha 0**

```bash
git add test-results/nghiem-thu-van-hanh/<ten-ban-ghi>.json
git commit -m "chore(nghiem thu): ban ghi Pha 0 — sau so tra loi duoc, J1+J2 dat"
```

---

## Tự rà kế hoạch

**Phủ spec:** §3 kiến trúc → Task 1–4 · §3.2 tự kiểm → Task 1 bước 6–7 · §4 ma
trận → Task 2 · §4.4 cổng nhiễu → Task 3 bước 1–4 · §5 bảng 23 tham số → Task 4
· §6.2 sổ rác → Task 5 bước 3 · §6.3 ba điều kiện dừng → Task 3 bước 5–6 · §6.5
bản ghi gắn commit → Task 4 bước 1 · §7 Pha 0 → Task 5.

**Chưa phủ, cố ý:** §6.4 trần chi tiêu — cài trong Task 3 bước 7 cùng `chay_tat_ca`;
Pha 1–8 của §7 là **vận hành**, không phải mã, nên không thành task.

**Nhất quán kiểu:** `MauSo` dùng ở Task 1/3 · `KichBan` ở Task 2/3 ·
`KetQuaKichBan` ở Task 3/4 — tên trường khớp giữa các task.

**Ô còn trống có chủ ý:** ba ngưỡng *"chốt sau lượt đầu"* của spec §5 (chờ trung
vị, chờ p95, thông lượng theo mức) — điền sau Pha 1, không bịa trước.

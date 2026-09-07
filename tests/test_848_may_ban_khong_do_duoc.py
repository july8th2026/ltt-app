"""
test_848 — `may_ban` phải phân biệt "KHÔNG ĐO ĐƯỢC" với "ĐO RỒI, KHÔNG THẤY AI".

## 🔴 Đo 07/09: công cụ báo động giả trên một máy rảnh

```
python tools/may_ban.py
  [may ban] KHONG BIET - thieu `psutil`, khong dem duoc.

python -c "import psutil; print(psutil.__version__)"
  7.2.2                      <- psutil CO, cung trinh thong dich
```

Bản cũ trả `{}` cho **cả hai** trạng thái — thiếu `psutil`, và đo xong không thấy
cây nào khác — còn `main` in thông điệp "thiếu psutil" cho cả hai.

## Vì sao một báo động giả ở đây đắt hơn im lặng

Chủ dự án vừa dặn *"check CPU trước khi chạy gate"*. Một công cụ trả lời
*"không biết, hỏi phiên khác"* mỗi lần máy **rảnh** là một công cụ người ta học
cách bỏ qua — và ngày nó nói thật thì không ai nghe nữa.

⛔ `AGENTS.md` §4c câu 2 gọi đúng tên: *"**cố ý** phải phân biệt được với **tai
   nạn**: gộp chúng làm một thì hoặc báo động giả liên tục, hoặc phải nới cổng
   đến mức nó bỏ lọt chính thứ nó sinh ra để bắt."*

## ⭐ Hai phiên tìm ra CÙNG lỗi này, cách nhau 78 giây

Và hai bản vá khác nhau. Bản trên trunk được giữ vì nó là **tập cha**: nó có
thêm `quet()` — một vỏ tương thích cho mọi nơi gọi sẵn có — và nối `main` với
`khoa_dang_giu()`.

⛔ Tệp này vì thế đã được **viết lại** để hỏi cùng những mệnh đề ấy qua API được
   giữ. Mệnh đề là thứ đáng giữ; tên hàm thì không.

⭐ Và giữ **cả hai** tệp phép kiểm (`test_361` của phiên kia và tệp này) là có
  chủ đích: hai đường chốt cùng một mệnh đề, nên nếu mai có người sửa lại
  `_quet_thuc()` thì hai phép kiểm sẽ đỏ vì **hai lý do khác nhau** — đó là
  thông tin, không phải trùng lặp.
"""
from __future__ import annotations

import ast
import importlib
import pathlib
import subprocess
import sys

GOC = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC / "tools"))
may_ban = importlib.import_module("may_ban")


# ── 1. Hai trạng thái phải PHÂN BIỆT ĐƯỢC ─────────────────────────────────

def test_thieu_psutil_tra_NONE_chu_khong_tra_bang_rong(monkeypatch):
    """🔴 Mệnh đề trung tâm, và là đường **suy biến** phải giữ nguyên.

    Thiếu `psutil` vẫn phải là "không biết" — bản vá chỉ **tách** nó khỏi "đo
    rồi, không thấy ai", không xoá nó.
    """
    that = __import__("builtins").__import__

    def gia(ten, *a, **k):
        if ten == "psutil":
            raise ImportError("gia lap thieu psutil")
        return that(ten, *a, **k)

    monkeypatch.setattr("builtins.__import__", gia)
    assert may_ban._quet_thuc() is None


def test_do_duoc_thi_tra_MOT_DICT_du_khong_thay_ai():
    """⭐ Trên máy có `psutil`, `_quet_thuc()` phải trả **một dict** — kể cả rỗng.

    Rỗng ở đây là một **câu trả lời**: đã đo, không cây nào khác đang chạy.
    """
    import psutil                                    # noqa: F401 — chi de bo qua
    ra = may_ban._quet_thuc()
    assert ra is not None
    assert isinstance(ra, dict)


def test_vo_TUONG_THICH_luon_tra_dict_khong_bao_gio_tra_None(monkeypatch):
    """⛔ Bánh cóc cho hợp đồng CŨ.

    `quet()` tồn tại để mọi nơi gọi sẵn có không phải đổi. Nếu một ngày nó bắt
    đầu trả `None`, một bản sửa **nghĩa** biến thành một bản **phá hợp đồng** ở
    chỗ không liên quan — `test_361` gọi `may_ban.quet().get(...)`.
    """
    that = __import__("builtins").__import__

    def gia(ten, *a, **k):
        if ten == "psutil":
            raise ImportError("gia lap thieu psutil")
        return that(ten, *a, **k)

    monkeypatch.setattr("builtins.__import__", gia)
    assert may_ban.quet() == {}


# ── 2. Thông điệp in ra phải khác nhau ─────────────────────────────────────

def _chay(*them: str) -> str:
    r = subprocess.run([sys.executable, str(GOC / "tools" / "may_ban.py"), *them],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=str(GOC))
    return (r.stdout or "") + (r.stderr or "")


def test_may_RANH_khong_bao_la_KHONG_BIET():
    """🔴 Phép kiểm bắt đúng lỗi 07/09.

    ⛔ KHONG dat `assert` sau mot `if` doc chinh dau ra. Ban dau toi viet
       `if "KHONG cay nao khac" in ra:` — va doi chung cho thay no XANH RONG khi
       tiem lai ban cu, vi luc ay chuoi ay khong xuat hien nen than `if` khong
       chay lan nao. Bay 31 hinh thai 1, trong chinh phep kiem ve su trung thuc
       cua phep do.

    ⭐ Menh de dung KHONG phu thuoc may ban hay ranh: **da import duoc `psutil`
       thi khong bao gio duoc bao "thieu psutil"**.
    """
    import psutil                                    # noqa: F401

    ra = _chay()
    assert "thieu `psutil`" not in ra, (
        f"psutil CO ({psutil.__version__}) ma van bao thieu — bao dong gia."
        f"{chr(10)}{ra}")


def test_hai_thong_diep_KHONG_dung_chung_mot_cau():
    """Bánh cóc: gộp lại thành một câu là quay về đúng lỗi cũ."""
    van = (GOC / "tools" / "may_ban.py").read_bytes().decode("utf-8")
    assert "thieu `psutil`, khong dem duoc" in van
    assert "khong cay nao khac dang chay" in van


def test_im_van_khong_in_gi():
    """`--im` là hợp đồng của người gọi tự động — không được ồn thêm."""
    assert _chay("--im").strip() == ""


# ── 3. Người gọi phải phân biệt bằng `is`, không bằng truthiness ───────────

def test_main_dung_IS_NONE_chu_khong_dung_truthiness():
    """⛔ `if not bang:` gộp `None` với `{}` — đúng lỗi gốc. Chốt bằng AST để
    một lần "dọn dẹp" không lặng lẽ đưa nó về."""
    cay = ast.parse((GOC / "tools" / "may_ban.py").read_bytes().decode("utf-8"))
    main = next(f for f in ast.walk(cay)
                if isinstance(f, ast.FunctionDef) and f.name == "main")
    co_is_none = [n for n in ast.walk(main)
                  if isinstance(n, ast.Compare)
                  and any(isinstance(o, ast.Is) for o in n.ops)
                  and any(isinstance(c, ast.Constant) and c.value is None
                          for c in n.comparators)]
    assert co_is_none, "main khong phan biet `None` bang `is`"


def test_main_goi_QUET_THUC_chu_khong_goi_vo_tuong_thich():
    """🔴 Đối chứng cho phép kiểm trên — không có nó thì nó xanh rỗng.

    Một `main` gọi `quet()` (vỏ tương thích, luôn trả `dict`) thì **không bao
    giờ** thấy `None`, và lúc ấy một `is None` ở đó là mã chết: phép kiểm trên
    vẫn xanh trong khi công cụ đã quay về gộp hai trạng thái.
    """
    cay = ast.parse((GOC / "tools" / "may_ban.py").read_bytes().decode("utf-8"))
    main = next(f for f in ast.walk(cay)
                if isinstance(f, ast.FunctionDef) and f.name == "main")
    goi = {n.func.id for n in ast.walk(main)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "_quet_thuc" in goi, (
        "main khong goi `_quet_thuc` — mot `is None` o do se la ma chet")

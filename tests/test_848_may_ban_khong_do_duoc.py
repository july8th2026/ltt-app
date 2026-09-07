"""
test_848 — `may_ban` phải phân biệt "KHÔNG ĐO ĐƯỢC" với "ĐO RỒI, KHÔNG THẤY AI".

## 🔴 Đo 07/09: công cụ báo động giả trên một máy rảnh

```
python tools/may_ban.py
  [may ban] KHONG BIET - thieu `psutil`, khong dem duoc.

python -c "import psutil; print(psutil.__version__)"
  7.2.2                      <- psutil CO, cung trinh thong dich
```

`quet()` trả `{}` cho **cả hai** trạng thái — thiếu `psutil`, và đo xong không
thấy cây nào khác — còn `main` in thông điệp "thiếu psutil" cho cả hai.

## Vì sao một báo động giả ở đây đắt hơn im lặng

Chủ dự án vừa dặn *"check CPU trước khi chạy gate"*. Một công cụ trả lời
*"không biết, hỏi phiên khác"* mỗi lần máy **rảnh** là một công cụ người ta học
cách bỏ qua — và ngày nó nói thật thì không ai nghe nữa.

⛔ `AGENTS.md` §4c câu 2 gọi đúng tên: *"**cố ý** phải phân biệt được với **tai
   nạn**: gộp chúng làm một thì hoặc báo động giả liên tục, hoặc phải nới cổng
   đến mức nó bỏ lọt chính thứ nó sinh ra để bắt."*

## Bản vá hỏi QUAN HỆ, không hỏi HÌNH DẠNG

Mã cũ hỏi *"bảng có rỗng không"* — một **hình dạng**. Câu đúng là *"phép đo có
CHẠY không"* — một **trạng thái**. Nên `quet()` nay trả `KHONG_DO_DUOC` (khác
`{}`), và người gọi phân biệt bằng `is`, không bằng truthiness.
"""
from __future__ import annotations

import importlib
import pathlib
import subprocess
import sys

GOC = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC / "tools"))
may_ban = importlib.import_module("may_ban")


# ── 1. Hai trạng thái phải PHÂN BIỆT ĐƯỢC ─────────────────────────────────

def test_KHONG_DO_DUOC_khac_bang_RONG():
    """🔴 Mệnh đề quyết định. `{}` và `KHONG_DO_DUOC` phải là hai giá trị khác
    nhau — nếu chúng bằng nhau thì mọi phép kiểm dưới vô nghĩa."""
    assert may_ban.KHONG_DO_DUOC is not {}          # noqa: F632 — co y
    assert may_ban.KHONG_DO_DUOC != {}


def test_thieu_psutil_tra_KHONG_DO_DUOC(monkeypatch):
    """⛔ Đường suy biến phải GIỮ NGUYÊN: thiếu `psutil` vẫn là "không biết"."""
    that = __import__("builtins").__import__

    def gia(ten, *a, **k):
        if ten == "psutil":
            raise ImportError("gia lap thieu psutil")
        return that(ten, *a, **k)

    monkeypatch.setattr("builtins.__import__", gia)
    assert may_ban.quet() is may_ban.KHONG_DO_DUOC


def test_do_duoc_thi_tra_MOT_DICT_du_khong_thay_ai():
    """⭐ Trên máy có `psutil`, `quet()` phải trả **một dict** — kể cả rỗng.

    Rỗng ở đây là một **câu trả lời**: đã đo, không cây nào khác đang chạy.
    """
    import psutil                                    # noqa: F401 — chi de bo qua
    ra = may_ban.quet()
    assert ra is not may_ban.KHONG_DO_DUOC
    assert isinstance(ra, dict)


# ── 2. Thông điệp in ra phải khác nhau ─────────────────────────────────────

def _chay(*them: str) -> str:
    r = subprocess.run([sys.executable, str(GOC / "tools" / "may_ban.py"), *them],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=str(GOC))
    return (r.stdout or "") + (r.stderr or "")


def test_may_RANH_khong_bao_la_KHONG_BIET():
    """🔴 Phép kiểm bắt đúng lỗi 07/09.

    ⛔ Đây là ca **đo được**: `psutil` có mặt trong môi trường chạy test. Nếu
       một ngày nó vắng, phép kiểm này sẽ đỏ — và đó là đúng, vì lúc ấy con số
       của cả bộ test cũng không đáng tin.
    """
    import psutil                                    # noqa: F401

    # ⛔ KHONG dat `assert` sau mot `if` doc chinh dau ra. Ban dau toi viet
    #    `if "KHONG cay nao khac" in ra:` — va doi chung cho thay no XANH RONG
    #    khi tiem lai ban cu, vi luc ay chuoi ay khong xuat hien nen than `if`
    #    khong chay lan nao. Bay 31 hinh thai 1, trong chinh phep kiem ve su
    #    trung thuc cua phep do.
    #
    # ⭐ Menh de dung KHONG phu thuoc may ban hay ranh: **da import duoc
    #    `psutil` thi khong bao gio duoc bao "thieu psutil"**.
    ra = _chay()
    assert "thieu `psutil`" not in ra, (
        f"psutil CO ({psutil.__version__}) ma van bao thieu — bao dong gia.{chr(10)}{ra}")


def test_hai_thong_diep_KHONG_dung_chung_mot_cau():
    """Bánh cóc: gộp lại thành một câu là quay về đúng lỗi cũ."""
    van = (GOC / "tools" / "may_ban.py").read_bytes().decode("utf-8")
    assert "thieu `psutil`, khong dem duoc" in van
    assert "KHONG cay nao khac dang chay" in van


def test_im_van_khong_in_gi():
    """`--im` là hợp đồng của người gọi tự động — không được ồn thêm."""
    assert _chay("--im").strip() == ""


# ── 3. Người gọi phải phân biệt bằng `is`, không bằng truthiness ───────────

def test_main_dung_IS_chu_khong_dung_truthiness():
    """⛔ `if not bang:` gộp `None` với `{}` — đúng lỗi gốc. Chốt bằng AST để
    một lần "dọn dẹp" không lặng lẽ đưa nó về."""
    import ast

    cay = ast.parse((GOC / "tools" / "may_ban.py").read_bytes().decode("utf-8"))
    main = next(f for f in ast.walk(cay)
                if isinstance(f, ast.FunctionDef) and f.name == "main")
    co_is = [n for n in ast.walk(main)
             if isinstance(n, ast.Compare)
             and any(isinstance(o, ast.Is) for o in n.ops)
             and any(isinstance(c, ast.Name) and c.id == "KHONG_DO_DUOC"
                     for c in n.comparators)]
    assert co_is, "main khong phan biet KHONG_DO_DUOC bang `is`"

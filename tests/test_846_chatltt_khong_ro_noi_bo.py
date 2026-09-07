"""
test_846 — chi tiết NỘI BỘ không được ra tới người dùng. (H44 P10)

P10 liệt kê *"rò bí mật/ID nội bộ"* là hạng mục bảo mật. Đo 07/09 với một thân
lỗi `llama.cpp` **hình dạng bình thường** — bốn loại rò cùng một lúc, trên **cả
hai** đường ra:

```
duong dan tep may chu : D:/models/Qwen3-VL-30B-A3B-Instruct-Q6_K.gguf
id model noi bo       : "model":"qwen3-vl-30b-a3b-instruct-q6"
base_url noi bo       : "base_url":"http://192.168.1.50:8080/v1"
IP noi bo             : 192.168.1.50
```

Chuỗi:

```
luong_vlm  f"may B tra {code}: {than_loi[:600]}"
  -> luong.py  KhongMoDuoc(e.ly_do)
    -> luot.py    {"ly_do": str(e)}  -> SSE      -> TRINH DUYET
    -> jobs.py    LoiNghienCuu(str(e)) -> job.error
       -> _p_nghien_cuu.xem  ra["ly_do"]         -> JSON -> TRINH DUYET (VE RA MAN HINH)
```

⛔ Và nền tảng đã tự khai luật ngược lại (`runtime_noi_bo/luong.py`): *"Dịch
   alias → id nội bộ **ngay trước khi ra khỏi nền tảng**. Khách không bao giờ
   nhìn thấy id thật."*

## Vì sao phép kiểm này KHÔNG quét theo mẫu

`AGENTS.md` §4c câu 3: *"Nhãn thì rẻ và **sai im lặng**."* Một phép kiểm bắt
IP/đường dẫn sẽ **xanh** trước hình dạng rò tiếp theo — một tên máy không có IP,
một khoá API, một câu tiếng Anh kể tên tệp.

⇒ Nên phép kiểm hỏi một **quan hệ**: *"chữ cho người dùng có dựng từ MÃ không,
  hay dựng từ một chuỗi ngoại lệ?"* Nó chốt **nguồn**, không chốt hình dạng.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from apps.chatltt.services import loi_ra_ngoai as LRN

GOC = pathlib.Path(__file__).resolve().parents[1]

#: Thân lỗi thật của một máy chủ suy luận khi hỏng. Không phải ca dựng công.
THAN_LOI = (
    '{"error":{"message":"Failed to load model from '
    'D:/models/Qwen3-VL-30B-A3B-Instruct-Q6_K.gguf: out of device memory"},'
    '"model":"qwen3-vl-30b-a3b-instruct-q6",'
    '"base_url":"http://192.168.1.50:8080/v1"}'
)


# ── 1. Cửa duy nhất KHÔNG nhận nổi một chuỗi ngoại lệ ──────────────────────

def test_cau_KHONG_bao_gio_tra_lai_thu_duoc_truyen_vao():
    """🔴 Phép kiểm quyết định. Dù truyền cả thân lỗi vào, không byte nào của nó
    ra được — vì `cau()` tra một **bảng đóng**, không định dạng chuỗi."""
    ra = LRN.cau("may B tra 500: " + THAN_LOI)
    assert ra == LRN.MAC_DINH
    for manh in ("192.168", ".gguf", "base_url", "qwen3"):
        assert manh not in ra, manh


def test_ma_LA_ra_cau_chung_chu_khong_ra_chuoi_goc():
    """⛔ Fail-closed. Nhánh *"không biết"* là nhánh người ta hay để lọt về hành
    vi cũ, nên nó phải được chốt riêng."""
    assert LRN.cau("mot_ma_chua_ai_khai") == LRN.MAC_DINH
    assert LRN.cau("") == LRN.MAC_DINH
    assert LRN.cau(None) == LRN.MAC_DINH        # type: ignore[arg-type]


def test_moi_cau_deu_la_chu_TIENG_VIET_cho_nguoi_doc():
    for ma, c in LRN.CAU.items():
        assert c and c[0].isupper(), ma
        assert any("\u00c0" <= k <= "\u1ef9" for k in c), f"{ma}: khong co dau"


def test_hinh_dang_tra_TEN_LOP_chu_khong_tra_noi_dung():
    """⭐ Tên lớp là của **mã của ta**, không phải chữ thượng nguồn viết ra."""
    e = ValueError("may B tra 500: " + THAN_LOI)
    assert LRN.hinh_dang(e) == "ValueError"


# ── 2. Không cửa nào còn dựng `ly_do` từ một chuỗi ngoại lệ ────────────────

def _gan_ly_do(rel: str) -> list:
    """Mọi biểu thức được gán cho khoá/thuộc tính `ly_do`, đọc bằng AST."""
    cay = ast.parse((GOC / rel).read_bytes().decode("utf-8"))
    ra = []
    for n in ast.walk(cay):
        if isinstance(n, ast.Dict):
            for k, v in zip(n.keys, n.values, strict=True):
                if isinstance(k, ast.Constant) and k.value == "ly_do":
                    ra.append(v)
        elif isinstance(n, ast.Assign):
            for t in n.targets:
                if (isinstance(t, ast.Subscript)
                        and isinstance(t.slice, ast.Constant)
                        and t.slice.value == "ly_do"):
                    ra.append(n.value)
    return ra


#: Tệp có một cửa `ly_do` đi ra NGƯỜI DÙNG.
CUA_RA = ["apps/chatltt/services/luot.py",
          "apps/chatltt/services/tao_media.py",
          "apps/chatltt/routes/_p_nghien_cuu.py"]


@pytest.mark.parametrize("rel", CUA_RA)
def test_ly_do_dung_tu_MA_chu_khong_tu_chuoi_ngoai_le(rel):
    """🔴 Chốt **quan hệ**, không chốt hình dạng: mọi `ly_do` ra ngoài phải là
    một lời gọi `LRN.*`, hoặc một hằng chuỗi ta tự viết.

    ⛔ `str(e)`, `str(job.error)`, `f"...{e}"` — đều đỏ.
    """
    for nut in _gan_ly_do(rel):
        if isinstance(nut, ast.Constant):
            continue                      # hằng chuỗi ta tự viết
        assert isinstance(nut, ast.Call), ast.dump(nut)[:120]
        f = nut.func
        assert (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name)
                and f.value.id == "LRN"), (
            f"{rel}: `ly_do` dung tu {ast.dump(nut)[:120]} — phai qua LRN")


def test_bo_trich_TU_KIEM():
    """⛔ Bộ trích hỏng ⇒ danh sách rỗng ⇒ phép kiểm trên xanh trên hư không."""
    assert len(_gan_ly_do("apps/chatltt/services/luot.py")) >= 2


# ── 3. Hai bảng mã phải phủ cùng một tập ───────────────────────────────────

def test_bang_ma_cua_giao_dien_va_may_chu_KHONG_lech():
    """⚠️ Giao diện chat dịch mã sang câu của riêng nó (`MA_LOI` trong
    `App.tsx`). Một mã chỉ có ở một bên là một mã ra câu chung chung ở bên kia
    — im lặng, và chỉ lộ khi khách gặp đúng lỗi ấy.
    """
    import re

    van = (GOC / "frontend" / "chatltt" / "src" / "App.tsx").read_bytes().decode("utf-8")
    m = re.search(r"const MA_LOI[^=]*=\s*\{(.*?)\n\}", van, re.S)
    assert m, "khong trich duoc MA_LOI"
    fe = set(re.findall(r"^\s*(\w+):", m.group(1), re.M))
    assert fe, "bo trich MA_LOI hong"

    #: Mã chỉ có ở một bên, **kèm lý do**.
    chi_giao_dien = {"csrf"}          # loi cua tang HTTP, may chu khong sinh
    chi_may_chu = {"khong_co_nang_luc", "luong_cat", "loi_noi_bo"}
    thieu = (set(LRN.CAU) - chi_may_chu) - fe
    thua = (fe - chi_giao_dien) - set(LRN.CAU)
    assert thieu == set(), f"giao dien thieu ma: {sorted(thieu)}"
    assert thua == set(), f"may chu thieu ma: {sorted(thua)}"

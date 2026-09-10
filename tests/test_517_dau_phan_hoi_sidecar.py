r"""HEADER CỦA SIDECAR — tra cứu không phân biệt hoa/thường.

## Lỗi này đã sống bao lâu không ai biết, vì nó KHÔNG BAO GIỜ NỔ

`_goi` cũ trả `dict(r.headers)`. `r.headers` là `email.message.Message` — **đã**
không phân biệt hoa/thường — còn `dict()` **vứt mất** tính chất ấy. Starlette ghi
tên header **chữ thường** trên dây, nên khoá thật là `x-duration-s`.

Đo 10/09/2026, dựng đúng khuôn `Response(headers={"X-Duration-S": ...})` của
`voice_sidecar/server.py:298` rồi đọc lại bằng chính đường `_goi` dùng:

    khoa that su nhan duoc : 'x-duration-s' 'x-gen-s' 'x-rtf' 'x-sample-rate'
    .get('X-Duration-S')   -> None
    .get('x-duration-s')   -> '1.234'

## ⛔ Vì sao không ai thấy

| Chỗ đọc | Cách viết | Hậu quả |
|---|---|---|
| `tools/do_gia_von_voice.py` | `x-duration-s` | chạy được |
| `tools/do_lap_cau_v3.py` | `x-duration-s` | chạy được |
| `tools/do_bai_dai.py` | `x-gen-s` | chạy được |
| `tools/do_ho_so_giong.py` | `X-Duration-S` | **ném** `cong khong tra X-Duration-S` |
| `apps/ltt_voice/jobs.py` | `X-Gen-S` | **im lặng ra 0,0** |

Ba cái đầu là bằng chứng thực nghiệm rằng khoá là chữ thường. Cái thứ tư ném —
và đó là lý do nó **được phát hiện**. Cái thứ năm thì bọc trong `_so()`, thứ
được viết để dung thứ một sidecar bản cũ thiếu `X-Gen-S`; sự dung thứ ấy biến
một lỗi thành **số 0 im lặng**.

⇒ `gen_s` bằng 0 ở *mọi* lượt sinh, và phép đối chiếu `X-Duration-S` với ffprobe
  mà `server.py:301` hứa (*"có sẵn ở đây thì đối chiếu được ngay khi lệch"*)
  **chưa từng chạy một lần nào**.

## Vì sao chốt ở đây chứ không ở từng chỗ gọi

Hạ chữ thường ở mỗi chỗ tra là vá **ca**, không vá **hạng**: người sau viết hoa
thì lỗi quay lại, vẫn im lặng. `DauPhanHoi` làm cả hai cách đều đúng.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from apps.ltt_voice.sidecar_client import DauPhanHoi

GOC = pathlib.Path(__file__).resolve().parents[1]


def test_tra_duoc_bang_CA_HAI_cach_viet():
    """Đúng mệnh đề HTTP: tên header không phân biệt hoa/thường."""
    d = DauPhanHoi({"x-duration-s": "1.234", "X-Gen-S": "0.567"})
    for khoa in ("x-duration-s", "X-Duration-S", "X-DURATION-S", "x-DuRaTiOn-S"):
        assert d.get(khoa) == "1.234", f"tra bang {khoa!r} that bai"
        assert khoa in d
        assert d[khoa] == "1.234"
    assert d.get("X-Gen-S") == "0.567"
    assert d.get("x-gen-s") == "0.567"


def test_khoa_vang_mat_van_tra_mac_dinh_chu_khong_nem():
    d = DauPhanHoi({"x-rtf": "0.4"})
    assert d.get("X-Khong-Co") is None
    assert d.get("X-Khong-Co", "mac dinh") == "mac dinh"
    assert "X-Khong-Co" not in d
    with pytest.raises(KeyError):
        _ = d["X-Khong-Co"]


def test_van_la_dict_that_de_khong_pha_noi_tieu_thu_cu():
    """⛔ Đổi kiểu trả về là đổi hợp đồng của `_goi`.

    Không chỗ nào hiện serialize hay iterate headers, nhưng chốt vẫn giữ để bản
    sửa sau không lặng lẽ biến nó thành thứ không còn là `dict`.
    """
    d = DauPhanHoi({"X-A": "1", "x-b": "2"})
    assert isinstance(d, dict)
    assert sorted(d.keys()) == ["x-a", "x-b"], "khoa phai duoc chuan hoa ve thuong"
    assert sorted(d.items()) == [("x-a", "1"), ("x-b", "2")]
    assert len(d) == 2


def test_goi_KHONG_con_dung_dict_tho_len_headers():
    """🔑 Chốt CƠ CHẾ, không chốt tính chất.

    `dict(r.headers)` chính là dòng đã vứt mất tính không-phân-biệt-hoa-thường.
    Một bài chỉ assert `DauPhanHoi` cư xử đúng sẽ **vẫn xanh** nếu ai đó đưa
    `dict(...)` trở lại `_goi` — vì nó không đo `_goi`.
    """
    nguon = (GOC / "apps/ltt_voice/sidecar_client.py").read_text(encoding="utf-8")
    cay = ast.parse(nguon)
    ham = next((n for n in ast.walk(cay)
                if isinstance(n, ast.FunctionDef) and n.name == "_goi"), None)
    assert ham is not None, "khong con ham `_goi`?"

    gan = [n for n in ast.walk(ham) if isinstance(n, ast.Assign)]
    dong_headers = [n for n in gan
                    if any(isinstance(t, ast.Name) and t.id == "headers"
                           for t in n.targets)]
    assert dong_headers, "`_goi` khong con gan `headers`"
    for n in dong_headers:
        assert isinstance(n.value, ast.Call), "headers phai gan tu mot loi goi"
        ten = getattr(n.value.func, "id", None)
        assert ten == "DauPhanHoi", (
            f"`_goi` gan headers bang `{ten}(...)` — phai la `DauPhanHoi`. "
            f"`dict(...)` vut mat tinh khong-phan-biet-hoa-thuong cua HTTP.")


def test_jobs_va_cong_cu_doc_duoc_du_viet_hoa():
    """Hai chỗ đọc thật, một hoa một thường — sau bản vá thì cả hai phải chạy."""
    d = DauPhanHoi({"x-duration-s": "2.5", "x-gen-s": "1.0"})
    # nguyen van `apps/ltt_voice/jobs.py`
    assert d.get("X-Duration-S") == "2.5"
    assert d.get("X-Gen-S") == "1.0"
    # nguyen van `tools/do_ho_so_giong.py`
    assert d.get("X-Duration-S") is not None, (
        "day chinh la cho `do_ho_so_giong.py` nem `cong khong tra X-Duration-S`")
    # nguyen van `tools/do_gia_von_voice.py`
    assert d.get("x-duration-s") == "2.5"

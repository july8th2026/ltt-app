"""Đợt 5.2 — lược đồ cạnh v3 của **frontend** phải khớp **máy chủ**, từng chữ.

## 🔴 VÌ SAO PHÉP KIỂM NÀY PHẢI TỒN TẠI, VÀ VÌ SAO NÓ Ở ĐÂY

Cạnh v3 đi qua **ba** chỗ, viết bằng **hai** ngôn ngữ:

```
frontend/agent-canvas/src/workflowApi.ts   `edgeToV3`      SINH ra
platform_core/workflow/di_tru_m1.py        `_canh_v3`      SINH ra
platform_core/workflow/dinh_nghia.py       `_sinh_chi_muc` ĐỌC vào
```

Một chữ khác nhau giữa chúng **không gây lỗi biên dịch ở bên nào cả**. TypeScript
không biết Python; SQLAlchemy nhận `edge.get("source_port", "")` và trả chuỗi
rỗng một cách vui vẻ. Hậu quả là **cổng biến mất trong im lặng** — đúng cái mà
`M-1` được viết để cứu (`27_29 §27.2`: *"canvas_to_plan() VỨT NÓ ĐI"*).

⇒ `vitest` không nạp được `platform_core`; `pytest` không chạy TypeScript. Nên
  chỗ duy nhất kiểm được mệnh đề này là một bài Python **đọc nguồn TS**.

## `M9` — client ≡ server 100 %

Đây chính là hình dạng `M9` đòi. Không phải "hai bên nên giống nhau" mà là **một
phép đo trên cả hai bờ, so ra không lệch một phần tử nào**.

⛔ Và nó **không** được viết bằng cách chép danh sách trường vào một hằng số ở
   đây: một hằng số thứ ba chỉ là chỗ thứ ba để trôi. Cả hai vế đều **đọc từ
   nguồn thật**.
"""
from __future__ import annotations

import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent
TS = GOC / "frontend" / "agent-canvas" / "src" / "workflowApi.ts"


def _truong_tu_typescript() -> set[str]:
    """Trường của `CanvasEdgeV3`, đọc từ **khai báo kiểu** trong nguồn TS.

    Đọc kiểu chứ không đọc thân `edgeToV3`: kiểu là thứ hợp đồng, và nếu thân
    hàm lệch khỏi kiểu thì `tsc` đã bắt rồi (đã chạy `npm run typecheck`).
    """
    noi_dung = TS.read_text(encoding="utf-8")
    m = re.search(r"export type CanvasEdgeV3 = \{(.*?)\n\}", noi_dung, re.S)
    if m is None:
        pytest.fail("khong tim thay `export type CanvasEdgeV3` trong workflowApi.ts")
    return set(re.findall(r"^\s*([a-z_][a-z0-9_]*)\s*:", m.group(1), re.M))


def _truong_may_chu_SINH() -> set[str]:
    """Khoá thật mà `di_tru_m1._canh_v3` sinh ra — **gọi hàm**, không đọc mã.

    ⭐ Gọi thật là chỗ phép kiểm này mạnh hơn một lượt `grep`: nó đo **đầu ra**,
       nên một nhánh `if` nào đó thêm/bớt khoá cũng bị bắt.
    """
    from platform_core.workflow.di_tru_m1 import _canh_v3

    return set(_canh_v3({"id": "e", "source": "a", "target": "b",
                         "sourceHandle": "p", "targetHandle": "q"}))


def _truong_may_chu_DOC() -> set[str]:
    """Khoá mà `dinh_nghia._sinh_chi_muc` thật sự đọc khỏi một cạnh."""
    import ast

    nguon = (GOC / "platform_core" / "workflow" / "dinh_nghia.py").read_text(
        encoding="utf-8")
    cay = ast.parse(nguon)
    ham = [n for n in ast.walk(cay)
           if isinstance(n, ast.FunctionDef) and n.name == "_sinh_chi_muc"]
    assert ham, "khong tim thay `_sinh_chi_muc`"
    ra: set[str] = set()
    for n in ast.walk(ham[0]):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "get" and n.args
                and isinstance(n.args[0], ast.Constant)
                and isinstance(n.args[0].value, str)):
            ra.add(n.args[0].value)
    return ra


@pytest.fixture(scope="module")
def ts() -> set[str]:
    if not TS.exists():
        pytest.skip("cay nay khong co frontend/agent-canvas")
    return _truong_tu_typescript()


def test_frontend_va_may_chu_SINH_ra_dung_MOT_bo_truong(ts):
    """🔑 Mệnh đề trung tâm. Lệch một chữ ⇒ cổng biến mất trong im lặng."""
    may_chu = _truong_may_chu_SINH()
    assert ts == may_chu, (
        f"lech giua TypeScript va `di_tru_m1._canh_v3`:\n"
        f"  chi TS co     : {sorted(ts - may_chu)}\n"
        f"  chi may chu co: {sorted(may_chu - ts)}")


def test_thu_may_chu_DOC_deu_nam_trong_bo_frontend_SINH(ts):
    """Chiều còn lại: `_sinh_chi_muc` không được đọc một trường frontend không
    bao giờ gửi — đó là một chỉ mục luôn rỗng, và nó trông y hệt một chỉ mục
    đúng."""
    doc = _truong_may_chu_DOC() & {"source_node", "source_port",
                                   "target_node", "target_port", "kind", "id"}
    thieu = sorted(doc - ts)
    assert not thieu, (
        f"`_sinh_chi_muc` doc {thieu} nhung frontend khong sinh ra chung")


def test_cong_mac_dinh_HAI_BEN_giong_nhau(ts):
    """⚠️ `'out'`/`'in'` xuất hiện ở **cả hai** bờ như giá trị dự phòng.

    Lệch giá trị mặc định nguy hiểm hơn lệch tên trường: tên lệch thì cạnh rỗng
    và dễ thấy, còn mặc định lệch thì cạnh **có giá trị** — chỉ là sai — và nó
    chỉ lộ ra ở một đồ thị có nhiều cổng.
    """
    import inspect

    from platform_core.workflow import di_tru_m1

    than = inspect.getsource(di_tru_m1._canh_v3)
    noi_dung = TS.read_text(encoding="utf-8")
    for hang, ten in (("out", "DEFAULT_SOURCE_PORT"), ("in", "DEFAULT_TARGET_PORT")):
        assert f'or "{hang}"' in than, f"may chu khong con mac dinh {hang!r}"
        assert re.search(rf"{ten}\s*=\s*'{hang}'", noi_dung), (
            f"frontend khong con `{ten} = '{hang}'`")


def test_phep_kiem_nay_doc_duoc_ca_HAI_bo(ts):
    """🔑 Đối chứng cho chính phép kiểm.

    Nếu regex hụt, `ts` rỗng và ba bài trên **vẫn có thể xanh** khi vế kia cũng
    rỗng. Bài này chốt rằng cả hai vế đều thật sự đọc được thứ gì đó.
    """
    assert len(ts) == 6, f"doc duoc {len(ts)} truong tu TS: {sorted(ts)}"
    assert len(_truong_may_chu_SINH()) == 6

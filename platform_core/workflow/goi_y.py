"""Gợi ý cho trình soạn biểu thức §6 — **sinh từ nguồn**, không một bảng chép tay.

## Vấn đề nó giải

Người khai gõ `{{ ` vào một ô tham số của Inspector và cần biết *"ở đây tôi
viết được những gì"*. Câu trả lời có ba phần, và **cả ba đã tồn tại ở nơi
khác**:

    tên hàm          `ham_bieu_thuc.NHOM_HAM` / `BANG_HAM` — 49 hàm của §6.3
    gốc namespace    `chinh_sach.NAMESPACE`               — bảy tên của §6.2
    node + cổng      `bien_dich.cau_truc()`               — đồ thị × registry

⇒ Mô-đun này **không biết một cái tên nào**. Nó chỉ đi hỏi ba chỗ trên rồi xếp
lại. Đó là cả thiết kế: một bảng gợi ý gõ tay lệch ngay lần thêm hàm đầu tiên,
và kho này đã dựng hai bánh cóc (`test_1758`, `test_967`) đúng vì hạng lỗi ấy.

## 🔑 Vì sao KHÔNG tự tính lại quan hệ tổ tiên

Gợi ý một node **không phải tổ tiên** là mời người dùng viết một biểu thức mà
cổng publish (`bien_dich`, Task 7) sẽ ném lại vào mặt họ. Hai chỗ trả lời
*"node này đọc được của ai"* thì **sẽ có ngày lệch nhau**, và ngày ấy lỗi hiện
ra ở chỗ xa nhất: nút Publish. Nên luật tổ tiên chỉ có MỘT bản —
`bien_dich.cau_truc()` — và cả cổng publish lẫn cửa này cùng gọi nó.

## ⚠️ Mô-đun này KHÔNG nói được gì về

- **Ngữ cảnh của ô đang gõ.** `params` (§6.2) chỉ có mặt khi tính
  `timeout_expr`; `loop.*` chỉ có trong thân ForEach (P3). Cửa này trả cả bảy
  gốc, không biết ô nào đang được gõ.
- **Khoá con của `trigger`/`run`/`loop`/`workflow.input`.** Hôm nay **không có
  mã nào dựng các payload đó** (`moi_truong_wf` chỉ nhận chúng từ bên gọi, và
  chưa bên gọi nào tồn tại — kết luận âm, đo 24/09). Bịa ra `trigger.body`,
  `run.id`… ở đây là dựng đúng cái bảng chép tay mà mô-đun này từ chối dựng;
  chúng sẽ có nguồn ở P4 (trigger) và khi `graph.inputs` thôi rỗng.
- **`vars` có những biến nào.** §6.5 nói `vars` = output của các `core.set` tổ
  tiên; `core.set` là node của **P3** và `bien_dich` hôm nay còn từ chối nó
  (`loai_node_chua_ho_tro`). Nên `vars` ra đây như một gốc trống.
"""
from __future__ import annotations

import inspect
from typing import Any, Callable, Optional

from platform_core.workflow import bien_dich as _bd
from platform_core.workflow import chinh_sach as _cs
from platform_core.workflow import ham_bieu_thuc as _hbt
from platform_core.workflow.cong_cu import CongCu

__all__ = ["goi_y"]

#: `nodes` không ra danh sách gốc: nó được BUNG thành từng cổng có thật.
_GOC_BUNG = "nodes"


def _chu_ky(ten: str, ham: Callable[..., Any]) -> str:
    """Chữ ký đọc được, lấy từ **chữ ký Python thật** của hàm.

    `[x]` = tham số có mặc định, `…x` = nhận nhiều đối. ⛔ Không gõ tay: tên
    tham số nằm trong `ham_bieu_thuc.py`, và một bản chép sẽ trôi khỏi nó.
    """
    try:
        tham = inspect.signature(ham).parameters.values()
    except (TypeError, ValueError):          # C-function, callable lạ
        return f"{ten}(…)"
    phan: list[str] = []
    for p in tham:
        if p.kind is p.VAR_POSITIONAL:
            phan.append(f"…{p.name}")
        elif p.kind is p.VAR_KEYWORD:
            continue
        elif p.default is not p.empty:
            phan.append(f"[{p.name}]")
        else:
            phan.append(p.name)
    return f"{ten}({', '.join(phan)})"


def bang_ham() -> list[dict]:
    """49 hàm của §6.3, xếp nhóm — đọc thẳng `NHOM_HAM`, không chép."""
    ra: list[dict] = []
    for nhom, bang in _hbt.NHOM_HAM.items():
        for ten, ham in bang.items():
            ra.append({"ten": ten, "nhom": nhom,
                       "chu_ky": _chu_ky(ten, ham),
                       "qua_publish": _bd.cong_params_nhan(f"{ten}()")})
    return sorted(ra, key=lambda m: m["ten"])


def _goc() -> list[dict]:
    return [{"duong": ten, "loai": "goc", "qua_publish":
             _bd.cong_params_nhan(ten)}
            for ten in _cs.NAMESPACE if ten != _GOC_BUNG]


def tham_chieu_node(nid: str) -> str:
    """`nodes.<id>` khi `<id>` là định danh hợp lệ, ngược lại `nodes['<id>']`.

    ## 🔴 Lỗi CHẶN TÍNH NĂNG mà hàm này tồn tại để sửa (UI-11 tìm ra 28/09/2026)

    `editorState.ts::nextNode()` sinh id `` `n${Date.now().toString(36)}-${count}` ``
    — **LUÔN có gạch ngang** (vd `nmukpruo1-1`). Còn hàm gợi ý trước đây xây
    đường dạng có dấu chấm: `nodes.nmukpruo1-1.output.anh`.

    Ngôn ngữ §6 ⛔ **không** nhận một đoạn sau dấu chấm mà không phải định danh.
    Và **cả hai** bộ duyệt đồng ý với nhau — đo được:

        _bieu_thuc_s6_hop_le('nodes.nmukpruo1-1.output.x')    -> False
        trich_tham_chieu('nodes.nmukpruo1-1.output.x')        -> LoiBienDich
        _bieu_thuc_s6_hop_le("nodes['nmukpruo1-1'].output.x") -> True
        trich_tham_chieu("nodes['nmukpruo1-1'].output.x")     -> ThamChieu(...)

    ⇒ Đây ⛔ **KHÔNG** phải một tật của `ast.parse`: dạng dấu chấm với id chứa
      gạch ngang **thật sự không phải §6 hợp lệ**. Ngôn ngữ đã có sẵn dạng đúng
      cho khoá không-phải-định-danh — **subscript** — nên bản vá thuộc phía
      **SINH**. Sửa phía ĐỌC là sửa NGÔN NGỮ, và sẽ phải sửa **hai** bộ duyệt để
      chúng khỏi nói ngược nhau về cùng một chuỗi.

    ⚠️ Hậu quả trước bản vá: bất kỳ người dùng thật nào thêm ≥2 bước từ palette
       rồi dùng Data Picker đều nhận **422** ở `/publish`, kèm thông điệp **sai
       lạc** *"chỉ hỗ trợ đúng MỘT biểu thức"* — câu ấy ⛔ không liên quan gì tới
       nguyên nhân, nên nó còn dẫn người đi sai hướng.

    ⭐ CHỈ bọc khi CẦN, ⛔ không bọc luôn: `nodes.n1.output.anh` dễ đọc hơn
       `nodes['n1'].output.anh`, và chuỗi này **người dùng nhìn thấy** trong ô
       tham số. Một bản vá bọc-tất-cả cũng đúng về kỹ thuật nhưng trả giá bằng
       thứ mà người đọc phải chịu mỗi ngày.
    """
    return f"nodes.{nid}" if nid.isidentifier() else f"nodes[{nid!r}]"


def _cua_node(ct: _bd.CauTruc, node_id: str) -> list[dict]:
    """Mọi thứ node `node_id` đọc được của **tổ tiên** nó, và chỉ thế.

    ⛔ FAIL-CLOSED: `node_id` không có trong đồ thị ⇒ rỗng. Một danh sách
       "đoán đại" ở đây đi thẳng vào ô tham số của người dùng.
    """
    ra: list[dict] = []
    nhan = {n["id"]: n["type"] for n in ct.nodes}
    for nid in sorted(ct.to_tien.get(node_id) or ()):
        for cong in sorted(ct.cong_ra.get(nid) or ()):
            duong = f"{tham_chieu_node(nid)}.output.{cong}"
            ra.append({"duong": duong, "loai": "cong", "node": nid,
                       "cong": cong, "node_type": nhan.get(nid, ""),
                       "qua_publish": _bd.cong_params_nhan(duong)})
        for mat in _bd.MAT_NODE:
            if mat == "output":
                continue                    # đã bung thành từng cổng ở trên
            duong = f"{tham_chieu_node(nid)}.{mat}"
            ra.append({"duong": duong, "loai": "mat_node", "node": nid,
                       "cong": "", "node_type": nhan.get(nid, ""),
                       "qua_publish": _bd.cong_params_nhan(duong)})
    return ra


def goi_y(document: dict, node_id: str, *,
          cong_cu: Optional[dict[str, CongCu]] = None) -> dict:
    """Gợi ý cho ô biểu thức của node `node_id` trong `document` (draft v3).

    Trả `{"node_id", "muc": [...], "ham": [...], "loi": None | {ma, thong_diep}}`.

    ⚠️ `loi` khác rỗng ⇒ phần `nodes.*` **vắng mặt**, không phải "không có gợi
       ý nào". Bảng hàm và các gốc vẫn ra: chúng không phụ thuộc đồ thị, và
       một bản nháp chưa nối xong không phải lý do để tắt cả trình soạn.
    """
    ra: dict[str, Any] = {"node_id": node_id, "muc": _goc(),
                          "ham": bang_ham(), "loi": None}
    try:
        # ⚠️ `nghiem=False`: người dùng ĐANG GÕ. Đo trên trình duyệt 24/09,
        #    `"Vẽ: {{ nodes"` (biểu thức gõ dở) làm cả phần `nodes.*` biến
        #    mất — đúng giây họ mở hộp gợi ý. Cấu trúc đồ thị không phụ thuộc
        #    một chuỗi đã gõ xong hay chưa; cổng publish vẫn nghiêm.
        ct = _bd.cau_truc(document, cong_cu=cong_cu, nghiem=False)
    except _bd.LoiBienDich as loi:
        ra["loi"] = {"ma": loi.ma, "thong_diep": str(loi)}
        return ra
    if node_id not in ct.to_tien:
        ra["loi"] = {"ma": "node_khong_trong_do_thi",
                     "thong_diep": f"node {node_id!r} khong co trong do thi"}
        return ra
    ra["muc"] += _cua_node(ct, node_id)
    return ra

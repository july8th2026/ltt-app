"""P9b task 4 — phần KHÔNG cần cột lược đồ của *"chạy lại từ node"* (spec §14).

Spec: *"tạo run **mới** cùng version, sao output các node **không phải hậu
duệ** của node chọn từ run cũ (tham chiếu artifact, không chép byte), chạy từ
node đó. `workflow_run.chay_lai_tu_run_id` ghi nguồn gốc."*

Câu hỏi **"node nào không phải hậu duệ"** là một câu hỏi về ĐỒ THỊ — trả lời
được hôm nay, không cần một cột nào. Câu hỏi **"run này chạy lại từ run nào"**
mới cần cột `chay_lai_tu_run_id`, và cột ấy thuộc `platform_core/models.py` +
một migration — **ngoài ranh giới làn này** (làn `p6` sở hữu, và hôm nay `main`
đã có một lần **hai head alembic** chặn deploy của mọi phiên). Đặc tả cột nằm
trong `docs/superpowers/reports/p9b-quan-sat-2/task-4-report.md`.

## ⛔ Vì sao THÂN `foreach` không bao giờ nằm trong tập tái dùng

Ảnh chụp của một node thân không khoá theo `node_id` trần mà theo **đường thi
hành** (`f:0/x`, `f:1/x`… — `thi_hanh.khoa_node`), và đường ấy có thể bị **băm**
khi vượt 64 ký tự (`danh_thuc.duong_thi_hanh`, P9 task 3). "Sao output node x"
khi x chạy N lần dưới N khoá, mà có khoá không suy ngược được, là một phép sao
**không xác định**. Tái dùng sai một output là trả cho khách một kết quả của
lần chạy khác — nên ở đây chọn **chạy lại** (tốn thêm tiền, đúng) thay vì
**đoán** (rẻ hơn, có thể sai).
"""
from __future__ import annotations

import pytest


def _g(nodes, edges, thu_tu=None):
    return {"nodes": [{"id": n, "type": t} if isinstance(n, str) is False else
                      {"id": n, "type": "tool"} for n, t in
                      ((x, "tool") for x in nodes)],
            "edges": [{"source_node": a, "target_node": b, "kind": "DATA"}
                      for a, b in edges],
            "thu_tu": thu_tu or list(nodes)}


def test_hau_due_gom_CHINH_NO_va_moi_node_toi_duoc():
    from platform_core.workflow import bao_gia
    #   a ─► b ─► d
    #   c ─────────┘
    g = _g(["a", "b", "c", "d"], [("a", "b"), ("b", "d"), ("c", "d")])
    assert bao_gia.hau_due(g, "b") == frozenset({"b", "d"})
    # ⭐ `a` là TỔ TIÊN, `c` là nhánh SONG SONG — cả hai đều KHÔNG phải hậu duệ.
    assert bao_gia.hau_due(g, "d") == frozenset({"d"})
    assert bao_gia.hau_due(g, "a") == frozenset({"a", "b", "d"})


def test_node_khong_co_trong_do_thi_thi_nem():
    from platform_core.workflow import bao_gia
    with pytest.raises(bao_gia.KhongBaoGiaDuoc):
        bao_gia.hau_due(_g(["a"], []), "khong-co")


def test_chu_trinh_khong_treo():
    """Đối chứng cho `_lan`: đồ thị đã publish là DAG, nhưng hàm này cũng đọc
    đồ thị **chưa** qua validator (một run cũ, một bản nháp) — treo ở đây là
    treo cả cửa HTTP."""
    from platform_core.workflow import bao_gia
    g = _g(["a", "b"], [("a", "b"), ("b", "a")])
    assert bao_gia.hau_due(g, "a") == frozenset({"a", "b"})


def test_tai_dung_la_PHAN_BU_cua_hau_due_va_giu_thu_tu():
    from platform_core.workflow import bao_gia
    g = _g(["a", "b", "c", "d"], [("a", "b"), ("b", "d"), ("c", "d")],
           thu_tu=["a", "c", "b", "d"])
    # Chạy lại từ `b` ⇒ tái dùng `a` và `c`, theo ĐÚNG `thu_tu` của đồ thị.
    assert bao_gia.co_the_tai_dung(g, "b") == ("a", "c")
    # ⭐ ĐỐI CHỨNG: chạy lại từ node ĐẦU ⇒ KHÔNG tái dùng gì. Thiếu phép này,
    #    một cài đặt trả "mọi node trừ node chọn" vẫn xanh ở phép trên.
    assert bao_gia.co_the_tai_dung(g, "a") == ("c",)


def test_than_foreach_KHONG_BAO_GIO_duoc_tai_dung():
    """⛔ Xem docstring đầu tệp: ảnh chụp thân khoá theo ĐƯỜNG THI HÀNH."""
    from platform_core.workflow import bao_gia
    g = {"nodes": [{"id": "a", "type": "tool"},
                   {"id": "v", "type": "core.foreach",
                    "params": {"max_items": 3}},
                   {"id": "x", "type": "tool"},
                   {"id": "ve", "type": "core.foreach_end",
                    "params": {"foreach": "v"}},
                   {"id": "z", "type": "tool"}],
         "edges": [{"source_node": a, "target_node": b, "kind": "DATA"}
                   for a, b in (("a", "v"), ("v", "x"), ("x", "ve"),
                                ("ve", "z"))],
         "thu_tu": ["a", "v", "x", "ve", "z"]}
    # Chạy lại từ `z` ⇒ mọi node trước nó là ứng viên tái dùng, NHƯNG `x`
    # (thân vòng) bị loại — cùng với chính `v`/`ve` (trạng thái vòng lặp).
    assert bao_gia.co_the_tai_dung(g, "z") == ("a",)
    # Đối chứng: `x` vẫn nằm trong đồ thị và KHÔNG phải hậu duệ của `z`.
    assert "x" not in bao_gia.hau_due(g, "z")

"""UI-T (Q11) — `trigger.manual` phải CHẠY được, không chỉ publish được.

## Vì sao node này đáng một bản vá riêng

Đo trên palette thật 27/09/2026: **0/7 trigger dùng được**. Sáu trigger piece đòi
credential (chưa có giao diện gắn), còn `trigger.manual` — thứ duy nhất không đòi
gì — thì `publish_duoc=False`, nên palette vẽ nó **mờ** kèm nhãn *"Sắp có"* và
⛔ không kéo được.

⇒ Mọi workflow dựng trên Canvas đều **thiếu điểm bắt đầu**. Hai luồng nghiệm thu
UX-3 và UX-5 chặn ở đúng chỗ này.

## 🔴 Vì sao KHÔNG chỉ lật cờ

Đo 28/09 **sau khi** UI-0 sửa cổng biên dịch:

    publish_duoc=False  ->  LoiBienDich: loai_node_chua_ho_tro
    publish_duoc=True   ->  BIEN DICH DUOC, thi_hanh='inline'

Cờ là thứ duy nhất chặn ở **publish**. Nhưng `nut_loi.bo_thi_hanh('trigger.manual')`
trả `None`, và `dong_co._chay_mot_inline` xử ca đó bằng:

    mtt.chuyen_node(..., sang="FAILED",
                    error=f"loi_he_thong: {node['type']!r} khong co bo thi hanh")

⇒ Lật cờ một mình sẽ cho ra một node **publish sạch rồi FAILED lúc chạy** — tệ
hơn hiện trạng, vì hiện trạng ít ra chặn TRƯỚC khi khách bấm Chạy và giữ tiền.
Nên bản vá phải **đăng ký một bộ thi hành** rồi mới mở cờ.

## Hợp đồng của bộ thi hành

`trigger.manual` khai đúng một cổng ra `event` kiểu `event`. Nó ⛔ không đọc tham
số (lược đồ rỗng), ⛔ không gọi ra ngoài, ⛔ không tiêu tiền. Việc duy nhất của nó
là **thành công ngay** và phát một `event` để node sau tiêu thụ.
"""
from __future__ import annotations

import pytest

from platform_core.workflow import bien_dich, nut_loi


def _tai_lieu(nodes: list, edges: list | None = None) -> dict:
    return {"version": 3, "goal": "", "active_page_id": "p1",
            "pages": [{"id": "p1", "name": "Page 1",
                       "nodes": nodes, "edges": edges or []}]}


def _nut(nid: str, tool: str, params: dict | None = None) -> dict:
    """Hình dạng `editorState.nextNode()` sinh — node kéo từ palette."""
    return {"id": nid, "type": "tool", "position": {"x": 0, "y": 0},
            "data": {"tool": tool, "params": params or {}}}


def test_trigger_manual_publish_duoc():
    """Palette phải kéo được nó — `publish_duoc=False` làm thẻ bị vô hiệu."""
    assert nut_loi.tat_ca()["trigger.manual"].publish_duoc is True


def test_trigger_manual_co_bo_thi_hanh():
    """🔴 Thứ này quan trọng HƠN cái cờ.

    Không có nó, `_chay_mot_inline` chuyển node sang FAILED với
    `loi_he_thong: ... khong co bo thi hanh` — tức publish sạch rồi hỏng lúc
    chạy, sau khi run đã giữ tiền.
    """
    assert nut_loi.bo_thi_hanh("trigger.manual") is not None


def test_bien_dich_mot_do_thi_bat_dau_bang_trigger_manual():
    ct = bien_dich.cau_truc(_tai_lieu([_nut("n-tr", "trigger.manual")]))
    assert ct.nodes[0]["type"] == "trigger.manual"
    assert ct.nodes[0]["thi_hanh"] == "inline"


def test_trigger_manual_noi_duoc_sang_node_sau():
    """Cổng `event` phải đi tới được một node thật — nếu không nó vô dụng."""
    ct = bien_dich.cau_truc(_tai_lieu(
        [_nut("n-tr", "trigger.manual"),
         _nut("n-set", "core.set", {"bien": {}})],
        [{"id": "e1", "source_node": "n-tr", "target_node": "n-set",
          "source_port": "event", "target_port": "in", "kind": "DATA"}]))
    assert [n["id"] for n in ct.nodes] == ["n-tr", "n-set"]
    assert ct.edges[0]["source_port"] == "event"


def test_bo_thi_hanh_tra_ve_event_va_thanh_cong_ngay():
    """Hợp đồng `KetQua`: SUCCEEDED, có cổng `event`, ⛔ không dừng run."""
    ham = nut_loi.bo_thi_hanh("trigger.manual")
    kq = ham(None, None, {"id": "n1", "type": "trigger.manual", "params": {}})
    assert kq.sang == "SUCCEEDED"
    assert "event" in kq.output
    assert kq.dung_run == ""
    # ⛔ Không chọn nhánh: `trigger.manual` không có cổng CONTROL nào.
    assert kq.nhanh == ""


@pytest.mark.parametrize("thua", [{"gi_do": 1}, {"lich": "0 9 * * *"}])
def test_tham_so_thua_bi_tu_choi(thua):
    """Lược đồ là `additionalProperties: False` — một tham số lạ ⛔ không được
    đi lọt. Đây là cửa chặn người dùng tưởng nó hẹn giờ được."""
    with pytest.raises(bien_dich.LoiBienDich):
        bien_dich.cau_truc(_tai_lieu([_nut("n-tr", "trigger.manual", thua)]))

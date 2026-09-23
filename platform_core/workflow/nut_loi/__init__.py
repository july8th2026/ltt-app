"""Node LÕI (`core.*`, `trigger.*`, `ai.*`, `connector.*`) — spec §4.5 nguồn 1.

⭐ Đây là nơi DUY NHẤT khai chúng. Plan 02 chỉ khai `trigger.manual` để Canvas
   có một điểm bắt đầu vẽ được; if/switch/foreach ở plan 04, `ai.*` ở plan 10,
   `connector.*` ở plan 08 — mỗi plan thêm một tệp vào thư mục này.

⛔ `publish_duoc=False` cho tới khi `bien_dich._node` biết biên dịch `core.*`
   (plan 04). Palette hiện node ở trạng thái vô hiệu thay vì mời khách kéo một
   node mà publish sẽ từ chối `loai_node_chua_ho_tro`.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.workflow import he_kieu
from platform_core.workflow.nut import Gia, LoiNut, NodeDefinition

_SO: dict[str, NodeDefinition] = {}


def dang_ky(nd: NodeDefinition) -> NodeDefinition:
    if nd.type in _SO:
        raise LoiNut(f"trung type trong nut_loi: {nd.type!r}")
    _SO[nd.type] = nd
    return nd


def tat_ca() -> dict:
    return dict(_SO)


dang_ky(NodeDefinition(
    type="trigger.manual", type_version=1, kind="trigger", category="TRIGGERS",
    title=N_("Chạy thủ công"),
    description=N_("Người dùng bấm chạy. Không có lịch, không có webhook."),
    icon="▶",
    cong_vao=(),
    cong_ra=(("event", he_kieu.Cong(type="event", required=True, nhan="event")),),
    tham_so={"type": "object", "properties": {}, "required": [],
             "additionalProperties": False},
    thi_hanh="inline", gia=Gia.mien_phi(), quyen=frozenset(),
    cho=(), ma_loi=(), publish_duoc=False))


__all__ = ["dang_ky", "tat_ca"]

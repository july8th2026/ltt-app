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
#: `{type: hàm thi hành}` cho node `thi_hanh="inline"`. Động cơ tra Ở ĐÂY, không
#: có bảng thứ hai: một node khai `inline` mà không có bộ thi hành là một node
#: sẽ đứng READY mãi mãi, nên `dang_ky` từ chối nó ngay lúc dựng.
_CHAY: dict[str, object] = {}


def dang_ky(nd: NodeDefinition, chay=None) -> NodeDefinition:
    if nd.type in _SO:
        raise LoiNut(f"trung type trong nut_loi: {nd.type!r}")
    if nd.thi_hanh == "inline" and chay is None and nd.kind != "trigger":
        # ⛔ Ném lúc DỰNG, không đợi lúc chạy — `LoiNut` docstring: chỗ nó lộ ra
        #    lúc chạy là chỗ đang tiêu tiền của khách. Một node inline không có
        #    bộ thi hành thì động cơ sẽ để nó READY tới khi hết TTL 20 giờ.
        raise LoiNut(
            f"{nd.type!r} khai thi_hanh='inline' nhung khong co ham thi hanh")
    _SO[nd.type] = nd
    if chay is not None:
        _CHAY[nd.type] = chay
    return nd


def tat_ca() -> dict:
    return dict(_SO)


def bo_thi_hanh(loai: str):
    """Hàm thi hành của một node inline, hoặc `None`."""
    return _CHAY.get(str(loai))


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

# ── Node điều khiển (plan wf-v2 P3) ──────────────────────────────────────────
# Import ĐẶT CUỐI, sau `dang_ky`/`_SO`: các tệp node gọi ngược vào gói này.
from platform_core.workflow.nut_loi import dieu_huong as _dieu_huong  # noqa: E402

for _nd, _chay in _dieu_huong.DINH_NGHIA:
    dang_ky(_nd, _chay)


__all__ = ["bo_thi_hanh", "dang_ky", "tat_ca"]

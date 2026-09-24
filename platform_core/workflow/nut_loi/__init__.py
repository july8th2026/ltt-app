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

#: Node mà ĐỘNG CƠ tự thi hành (không qua hàng đợi job). `run_con` nằm ở
#: đây cùng `inline` vì nó cũng chạy trong vòng scheduler — nó chỉ khác ở
#: chỗ kết quả tới muộn (một `workflow_run` khác), không ở chỗ ai chạy nó.
THI_HANH_TRONG_DONG_CO = frozenset({"inline", "run_con"})

_SO: dict[str, NodeDefinition] = {}
#: `{type: hàm thi hành}` cho node `thi_hanh="inline"`. Động cơ tra Ở ĐÂY, không
#: có bảng thứ hai: một node khai `inline` mà không có bộ thi hành là một node
#: sẽ đứng READY mãi mãi, nên `dang_ky` từ chối nó ngay lúc dựng.
_CHAY: dict[str, object] = {}


def dang_ky(nd: NodeDefinition, chay=None) -> NodeDefinition:
    if nd.type in _SO:
        raise LoiNut(f"trung type trong nut_loi: {nd.type!r}")
    if nd.thi_hanh in THI_HANH_TRONG_DONG_CO and chay is None and nd.kind != "trigger":
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
from platform_core.workflow.nut_loi import du_lieu as _du_lieu  # noqa: E402
from platform_core.workflow.nut_loi import goi_wf as _goi_wf  # noqa: E402
from platform_core.workflow.nut_loi import vong_lap as _vong_lap  # noqa: E402

for _nd, _chay in (_dieu_huong.DINH_NGHIA + _du_lieu.DINH_NGHIA
                   + _vong_lap.DINH_NGHIA + _goi_wf.DINH_NGHIA):
    dang_ky(_nd, _chay)

# ── Node AI (plan wf-v2 P7) ─────────────────────────────────────────────
#
# ⭐ Ba tệp này gọi `dang_ky(...)` **lúc import**, nên chúng chỉ tồn tại khi
#    có người import. Làn p7 viết xong nhưng không được sửa tệp này; hậu quả
#    là ba node đầy đủ mà `nut_loi.tat_ca()` không thấy, palette không vẽ, và
#    `bien_dich._node_loi` báo `node_khong_ton_tai` cho một thứ đã có thật.
#    Một mô-đun đăng ký mà không ai import là một mô-đun CHẾT.
#
# ⚠️ `noqa: F401` là đúng chỗ ở đây: tác dụng của import là **hiệu ứng phụ**
#    (`dang_ky` chạy), không phải cái tên được dùng lại phía dưới.
from platform_core.workflow.nut_loi import ai_llm as _ai_llm  # noqa: E402,F401
from platform_core.workflow.nut_loi import ai_router as _ai_router  # noqa: E402,F401


__all__ = ["THI_HANH_TRONG_DONG_CO", "bo_thi_hanh", "dang_ky", "tat_ca"]

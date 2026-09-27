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


def _chay_trigger_thu_cong(db, run, node: dict, **_):
    """`trigger.manual` — điểm BẮT ĐẦU vẽ được của mọi workflow.

    Nó ⛔ không đọc tham số (lược đồ rỗng), ⛔ không gọi ra ngoài, ⛔ không tiêu
    tiền. Việc duy nhất: **thành công ngay** và phát một `event` để node sau
    tiêu thụ. Người dùng đã "kích hoạt" nó bằng chính cú bấm *Chạy*.

    🔴 VÌ SAO HÀM NÀY PHẢI TỒN TẠI, KHÔNG CHỈ LÀ CỜ `publish_duoc`.

       `dong_co._chay_mot_inline` xử ca thiếu bộ thi hành bằng:

           sang="FAILED", error=f"loi_he_thong: {type!r} khong co bo thi hanh"

       ⇒ Mở `publish_duoc` một mình sẽ cho ra một node **publish sạch rồi
       FAILED lúc chạy** — tệ hơn hiện trạng, vì hiện trạng ít ra chặn TRƯỚC
       khi khách bấm Chạy và giữ tiền. Đo 28/09 xác nhận cả hai vế.

    ⚠️ `output` chỉ mang cổng RA THẬT (`KetQua` docstring). `trigger.manual`
       khai đúng một cổng `event`, nên khoá ở đây là `event` — ⛔ không thêm
       `_meta`, `ts` hay thứ gì palette không công bố.
    """
    from platform_core.workflow.nut_loi.chay import KetQua

    return KetQua(output={"event": {"nguon": "thu_cong"}})


dang_ky(NodeDefinition(
    type="trigger.manual", type_version=1, kind="trigger", category="TRIGGERS",
    title=N_("Chạy thủ công"),
    description=N_("Người dùng bấm chạy. Không có lịch, không có webhook."),
    icon="▶",
    cong_vao=(),
    cong_ra=(("event", he_kieu.Cong(type="event", required=True, nhan="event")),),
    tham_so={"type": "object", "properties": {}, "required": [],
             "additionalProperties": False},
    # ⭐ MO 28/09 (Q11). Truoc do `False` voi ly do *"cho toi khi `bien_dich._node`
    #    biet bien dich `core.*`"* — UI-0 Task 1 da lam dung viec do, va phep do
    #    28/09 xac nhan no bien dich sach. Do la 0/7 trigger dung duoc truoc ban
    #    va nay; moi workflow tren Canvas deu thieu diem bat dau.
    thi_hanh="inline", gia=Gia.mien_phi(), quyen=frozenset(),
    cho=(), ma_loi=(), publish_duoc=True), _chay_trigger_thu_cong)

# ── Node điều khiển (plan wf-v2 P3) ──────────────────────────────────────────
# Import ĐẶT CUỐI, sau `dang_ky`/`_SO`: các tệp node gọi ngược vào gói này.
from platform_core.workflow.nut_loi import dieu_huong as _dieu_huong  # noqa: E402
from platform_core.workflow.nut_loi import du_lieu as _du_lieu  # noqa: E402
from platform_core.workflow.nut_loi import goi_wf as _goi_wf  # noqa: E402
from platform_core.workflow.nut_loi import vong_lap as _vong_lap  # noqa: E402

# ── Node CHỜ (plan wf-v2 P4) ─────────────────────────────────────────────────
# `core.delay` · `core.wait` · `core.human`. Cùng một tệp vì cả ba dùng CHUNG
# một cơ chế (waitpoint theo đường thi hành + wakeup + cửa resume) — tách ra là
# dựng ba lần rồi hoà, đúng lý do plan gộp phase gốc 5 và 6.
from platform_core.workflow.nut_loi import cho as _cho  # noqa: E402

for _nd, _chay in (_dieu_huong.DINH_NGHIA + _du_lieu.DINH_NGHIA
                   + _vong_lap.DINH_NGHIA + _goi_wf.DINH_NGHIA
                   + _cho.DINH_NGHIA):
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
# `ai.agent` (P8): mo-dun da san sang tu truoc, chi thieu DONG NAY - va no
# thieu vi `__init__.py` nam ngoai ranh gioi lan p8. Dieu phoi noi khi gop.
from platform_core.workflow.nut_loi import ai_agent as _ai_agent  # noqa: E402,F401

# ── Node HTTP (plan wf-v2 P5c) ───────────────────────────────────────────────
#
# 🔴 `core.http` bi GIU LAI tu 24/09 voi mot ly do CU THE, khong phai vi chua
#    xong: cho duy nhat mot workflow cat duoc header `Authorization` la
#    `params` cua node — tuc BEN TRONG `workflow_version`, mot ban ghi duoc
#    nhan ban khi khach "Save as" va tra nguyen ven cho trinh soan thao. Bat
#    node ma khong co kho credential la moi khach dan token vao do.
#
# ⭐ Ly do do het khi `platform_core/credential.py` ton tai (P5c/T1): ref duoc
#    kiem luc PUBLISH (`dinh_nghia._kiem_credential`), bi mat chi giai ma trong
#    tien trinh job, va no bi che o ca `output` lan `error`.
from platform_core.workflow.nut_loi import http as _http  # noqa: E402,F401

# ── Node connector (plan wf-v2 P6) ───────────────────────────────────────────
#
# ⭐ Import nay lam HAI viec, va ca hai deu la hieu ung phu:
#    1. `dang_ky(YOUTUBE_UPLOAD)` chay;
#    2. `nut.NGUON_PIECE` duoc gan sang ham doc `connector_runner/catalog.json`
#       — khe cam ma `nut._nguon_piece_rong` de san tu plan 02.
#    Khong co dong nay thi palette khong co mot connector nao, va
#    `bien_dich._node_loi` bao `node_khong_ton_tai` cho thu da co that.
from platform_core.workflow.nut_loi import connector as _connector  # noqa: E402,F401

# ── Node `core.code` (plan wf-v2 P-D mục 3) ─────────────────────────────────
#
# ⭐ Điều kiện tiên quyết ĐÃ ĐẠT (lan wfd, 25/09): lớp cách ly thứ hai
#    (isolated-vm trong AppContainer) đã port + bảy đường thoát D1–D7 đã có
#    phép "PHẢI THẤT BẠI" + phép TIÊM LỖI, xanh trên `main`. Trước đó
#    `code_sandbox.py` tồn tại nhưng KHÔNG node nào trỏ tới nó (docstring
#    module đó: *"CHƯA đăng ký"*) — dòng import dưới đây là chỗ nối duy nhất.
from platform_core.workflow.nut_loi import code as _code  # noqa: E402,F401


__all__ = ["THI_HANH_TRONG_DONG_CO", "bo_thi_hanh", "dang_ky", "tat_ca"]

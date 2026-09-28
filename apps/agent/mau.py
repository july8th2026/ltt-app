"""Danh mục MẪU (Templates, UI-9) — spec `09_TARGET_DESIGN.md` §1.

## Lời hứa sản phẩm mà module này phải giữ

`apps/agent/routes/trang.py::DAT_CHO` (trước 28/09) nói: *"Mẫu chạy được: mở
một mẫu ra là một workflow THẬT của bạn, sửa được ngay."* ⇒ một mẫu ở đây
**không phải** một ảnh chụp màn hình hay một đoạn JSON trưng bày — nó là một
tài liệu v3 hợp lệ mà `POST /agent/api/v3/workflows` nhận thẳng làm
`document`, y hệt luồng "Nhân bản" của `agent_workflows.html`.

## ⭐ Biên dịch NGAY LÚC IMPORT — fail-closed, không fail-open

Mỗi mẫu được biên dịch (`bien_dich.bien_dich`) và báo giá (`bao_gia.bao_gia_do_thi`)
**một lần khi module này nạp**, không đợi ai bấm "Dùng mẫu này". Một mẫu gãy
(node đã đổi tham số bắt buộc, `publish_duoc` bị tắt, thiếu tổ tiên…) làm CẢ
NỀN TẢNG không khởi động được — đúng ý "chặn trước lúc khách bấm Chạy", chỉ
sớm hơn một nấc: chặn trước cả lúc khách bấm "Dùng mẫu này". Một mẫu publish
sạch rồi mới hỏng lúc khách bấm là placeholder trá hình, đúng bẫy mà
`trigger.manual` (`test_5602`) đã trả giá.

## ⛔ Chỉ dùng node `publish_duoc=True` — và đây KHÔNG phải một lời hứa suông

Mọi mẫu ở đây chỉ dùng `trigger.manual`, `core.*` và `app.*` (registry
`ToolSpec`, đọc qua `cong_cu.tat_ca()`) — không node nào đòi `credential` của
khách (piece/connector). Không phải vì piece/connector "tệ hơn": biên dịch
CHÚNG cũng qua được `publish_duoc=True`, nhưng một mẫu cần **credential OAuth
người dùng chưa từng tạo** thì "sửa được ngay" chỉ đúng cho cấu hình, sai cho
việc CHẠY — và trang `/agent/connections` (UI-5) vẫn là DAT_CHO. `app.*` chạy
bằng khoá provider của chính nền tảng (`api_pool`, xem `nut.tu_toolspec`
docstring), nên một mẫu ở đây bấm "Chạy thử" được **ngay**, không cần cấu hình
gì thêm.

## Vì sao KHÔNG có mẫu nào khớp UX-1/UX-2/UX-4 (`00_SO_TIEN_DO.md`)

Đếm bằng `nut.tat_ca()` (28/09), không nhớ lại:

- UX-1 (Schedule → Sheets → … → YouTube): `trigger.schedule` **không tồn tại**
  trong registry — không có node nào đọc lịch hẹn giờ.
- UX-2 (Webhook → Phân tích → Clip → Phụ đề): `trigger.webhook` **không tồn
  tại** — `app.video.short_clips`/`app.video.subtitle` có thật, nhưng không
  điểm bắt đầu nào ngoài `trigger.manual`.
- UX-4 (Sheets → AI Router → nhánh → gộp): `ai.router` có đăng ký nhưng
  `publish_duoc=False` — biên dịch ném `loai_node_chua_ho_tro` ngay ở node
  đầu tiên của nhánh AI.

UX-3 (Manual → Ảnh → Video → Giọng → Render) **dựng được đầy đủ** từ 28/09
(Q11 mở `trigger.manual`) — `MAU_Y_TUONG_THANH_VIDEO` dưới đây là chính luồng
đó, không phải một luồng khác trông giống.

## ⭐ Vì sao module này nằm ở `apps/agent/`, KHÔNG phải `platform_core/workflow/`

Bản nháp đầu đặt tệp này ở `platform_core/workflow/mau.py` — và
`test_60_app_registry.py::test_no_app_slug_is_hardcoded_in_the_platform` đỏ
ngay: `"app.video_assembly.run"` chứa nguyên slug app `video_assembly`
(`apps/video_assembly/`). Chốt đó đúng, không phải một bánh cóc quá tay — MỘT
mẫu bắt buộc phải NÊU TÊN app cụ thể để ghép được một luồng thật (đây là
NỘI DUNG sản phẩm — "app nào ghép với app nào cho ra một demo hay" — không phải
LOGIC ĐỘNG CƠ). `platform_core/workflow/` là động cơ chạy ĐƯỢC mọi tài liệu
hợp lệ mà không cần biết trước một app cụ thể nào; `apps/agent/` là lớp sản
phẩm ĐÃ được phép biết về các app khác (nó là nơi đưa cả nền tảng ra một mặt
UI). Chuyển tệp là cách đúng, không phải xin miễn trừ `video_assembly` ở
`test_60` (ngoài phạm vi UI-9, và bánh cóc đó đã có lý do rõ để hẹp danh sách
miễn trừ, không mở rộng thêm cho tiện).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from platform_core.i18n import N_
from platform_core.workflow import bao_gia, bien_dich


def _tai_lieu(nodes: list[dict], edges: list[dict]) -> dict:
    return {"version": 3, "goal": "", "active_page_id": "p1",
            "pages": [{"id": "p1", "name": "Page 1",
                       "nodes": nodes, "edges": edges}]}


def _nut(nid: str, loai: str, params: dict | None = None,
        x: int = 0, y: int = 0) -> dict:
    """Một node — hình dạng "kéo từ palette" (`{type:'tool', data:{tool,params}}`),
    KHÔNG phải hình dạng "gọn" (`{type:'app.x', params}`).

    ⭐ `bien_dich._node()` chấp nhận CẢ HAI (xem nhánh `elif loai.startswith
       ("app."):` và nhánh `if loai == "tool":`) — nhưng Canvas (React) chỉ
       tự vẽ được hình dạng ĐẦU, vì nó đọc `node.data.tool` cho MỌI node
       (xem `editorState.nextNode()`, `frontend/agent-canvas`). Bản đầu của
       tệp này dùng hình dạng "gọn" — biên dịch sạch, báo giá đúng, nhưng mở
       trên trình duyệt thật (`preview_start` cổng 8207) thì Canvas ném
       `TypeError: Cannot read properties of undefined (reading 'tool')`
       ngay khi vẽ node đầu tiên. Publish sạch mà vỡ màn hình lúc mở là đúng
       cái bẫy `trigger.manual` (`test_5602`) đã trả giá — nên ở ĐÂY khớp
       ĐÚNG hình dạng Canvas thật sự đọc, không chỉ hình dạng biên dịch nhận.
    ⚠️ `tool` cho node `app.*` phải BỎ tiền tố `app.` — `_node()` tra
       `cong_cu.tat_ca()` bằng `CongCu.ten` (vd `"image.generate"`), không
       phải type đầy đủ. Node lõi/trigger thì giữ NGUYÊN type đầy đủ (vd
       `"core.output"`, `"trigger.manual"`) — nhánh `tool` fallback về
       `_node_loi` tra thẳng chuỗi đó.
    """
    tool = loai[4:] if loai.startswith("app.") else loai
    return {"id": nid, "type": "tool", "position": {"x": x, "y": y},
            "data": {"tool": tool, "params": params or {}}}


def _canh(nid: str, a: str, b: str, sp: str, tp: str, kind: str = "DATA") -> dict:
    return {"id": nid, "source_node": a, "target_node": b,
            "source_port": sp, "target_port": tp, "kind": kind}


@dataclass(frozen=True)
class Mau:
    """Một mẫu: tên + mô tả + tài liệu v3 + báo giá TẤT ĐỊNH của chính nó.

    ⭐ `toi_da`/`uoc_tinh` không phải số gõ tay: chúng tới từ
       `bao_gia.bao_gia_do_thi` chạy trên ĐÚNG `document` này lúc module nạp
       (xem docstring module). Một thay đổi giá ở registry tự động phản ánh
       vào đây lần import kế tiếp — không có bảng giá thứ hai để trôi.
    """

    id: str
    ten: str
    mo_ta: str
    document: dict
    loai_node: tuple[str, ...]
    toi_da: int
    uoc_tinh: int = field(default=0)


def _dung(id_: str, ten: str, mo_ta: str, nodes: list[dict],
         edges: list[dict]) -> Mau:
    doc = _tai_lieu(nodes, edges)
    # ⛔ KHÔNG bọc try/except: một mẫu không biên dịch được phải làm IMPORT
    #    của module này thất bại ồn ào (xem docstring "fail-closed").
    graph = bien_dich.bien_dich(doc)
    gia = bao_gia.bao_gia_do_thi(graph)
    # ⚠️ Đọc `type` từ GRAPH ĐÃ BIÊN DỊCH, không phải `nodes` thô: mọi node thô
    #    ở đây đều khai `type: "tool"` (hình dạng palette, xem `_nut`), nên đọc
    #    thô sẽ cho ra `("tool",)` cho MỌI mẫu — sai. `bien_dich` đã chuẩn hoá
    #    `type` thật (`"app.image.generate"`, `"core.output"`, …) cho từng node.
    loai = tuple(sorted({str(n["type"]) for n in graph["nodes"]}))
    return Mau(id=id_, ten=ten, mo_ta=mo_ta, document=doc, loai_node=loai,
              toi_da=gia.toi_da, uoc_tinh=gia.uoc_tinh)


# ── Mẫu 1 — Sinh ảnh nhanh ────────────────────────────────────────────────
#
# Mẫu rẻ nhất và đơn giản nhất: một bước duy nhất sau trigger. Dành cho người
# lần đầu mở Canvas — bấm Chạy thử là thấy kết quả ngay, không cấu hình gì.
def _mau_sinh_anh() -> Mau:
    nodes = [
        _nut("bat_dau", "trigger.manual", x=0, y=0),
        _nut("anh", "app.image.generate", {
            "prompt": N_("Một tấm ảnh minh hoạ đẹp cho ý tưởng của bạn — "
                        "sửa mô tả này rồi bấm Chạy thử."),
            "aspect_ratio": "16:9", "count": 1,
        }, x=240, y=0),
        _nut("ra", "core.output", {
            "ten": "anh", "gia_tri": "nodes.anh.output.image_keys",
        }, x=480, y=0),
    ]
    edges = [
        _canh("e1", "bat_dau", "anh", "event", "in"),
        _canh("e2", "anh", "ra", "image_keys", "in"),
    ]
    return _dung(
        "sinh-anh-nhanh", N_("Sinh ảnh nhanh"),
        N_("Bấm Chạy là có ngay một tấm ảnh từ một câu mô tả. Mẫu đơn giản "
           "nhất để làm quen với Canvas."),
        nodes, edges)


# ── Mẫu 2 — Ý tưởng thành video (UX-3: Manual → Ảnh → Video → Giọng → Render)
def _mau_y_tuong_thanh_video() -> Mau:
    nodes = [
        _nut("bat_dau", "trigger.manual", x=0, y=120),
        _nut("anh", "app.image.generate", {
            "prompt": N_("Ảnh mở đầu cho video của bạn — sửa mô tả cảnh ở đây."),
            "aspect_ratio": "16:9", "count": 1,
        }, x=240, y=0),
        _nut("giong", "app.speech.ltt", {
            "text": N_("Đây là lời dẫn cho video của bạn — sửa nội dung này "
                      "rồi chọn giọng đọc ở tab Cấu hình."),
            "language": "vi",
        }, x=240, y=240),
        _nut("video", "app.video.generate", {
            "prompt": N_("Biến ảnh trên thành một đoạn video ngắn, chuyển "
                        "động mượt, camera tĩnh."),
            "image_keys": "{{ nodes.anh.output.image_keys }}",
        }, x=480, y=0),
        _nut("ghep", "app.video_assembly.run", {
            "clips": "{{ [nodes.video.output.video_key] }}",
            "music": "{{ nodes.giong.output.audio_key }}",
        }, x=720, y=120),
        _nut("ra", "core.output", {
            "ten": "video_hoan_chinh", "gia_tri": "nodes.ghep.output.video",
        }, x=960, y=120),
    ]
    edges = [
        _canh("e1", "bat_dau", "anh", "event", "in"),
        _canh("e2", "bat_dau", "giong", "event", "in"),
        _canh("e3", "anh", "video", "image_keys", "image_keys"),
        _canh("e4", "video", "ghep", "video_key", "clips"),
        _canh("e5", "giong", "ghep", "audio_key", "music"),
        _canh("e6", "ghep", "ra", "video", "in"),
    ]
    return _dung(
        "y-tuong-thanh-video", N_("Ý tưởng thành video"),
        N_("Một câu mô tả ⇒ ảnh ⇒ video ngắn ⇒ lồng tiếng ⇒ ghép lại thành "
           "một video hoàn chỉnh. Bốn bước AI nối liền — luồng đầy đủ nhất "
           "trong danh mục này."),
        nodes, edges)


# ── Mẫu 3 — Viết rồi đọc thành giọng nói ──────────────────────────────────
def _mau_van_va_giong() -> Mau:
    nodes = [
        _nut("bat_dau", "trigger.manual", x=0, y=0),
        _nut("viet", "app.text.chat", {
            "messages": [{"role": "user", "content":
                         "Viết một đoạn giới thiệu ngắn (3-4 câu) về chủ đề "
                         "của bạn — sửa câu này rồi bấm Chạy thử."}],
        }, x=240, y=0),
        _nut("giong", "app.speech.ltt", {
            "text": "{{ nodes.viet.output.content }}", "language": "vi",
        }, x=480, y=0),
        _nut("ra", "core.output", {
            "ten": "ban_ghi_am", "gia_tri": "nodes.giong.output.audio_key",
        }, x=720, y=0),
    ]
    edges = [
        _canh("e1", "bat_dau", "viet", "event", "in"),
        _canh("e2", "viet", "giong", "content", "text"),
        _canh("e3", "giong", "ra", "audio_key", "in"),
    ]
    return _dung(
        "van-va-giong", N_("Viết rồi đọc thành giọng nói"),
        N_("AI viết một đoạn văn bản theo yêu cầu, rồi chuyển thẳng thành "
           "một bản ghi âm giọng đọc. Hai bước, rẻ, dùng lại được cho mọi "
           "chủ đề chỉ bằng cách sửa câu mô tả."),
        nodes, edges)


#: ⭐ Tính MỘT LẦN lúc nạp module — mọi request `/agent/templates` đọc lại
#: đúng tuple này, không biên dịch lại mỗi lần một khách mở trang.
_TAT_CA: tuple[Mau, ...] = (
    _mau_sinh_anh(), _mau_y_tuong_thanh_video(), _mau_van_va_giong(),
)


def tat_ca() -> tuple[Mau, ...]:
    return _TAT_CA


def theo_id(ma: str) -> Mau | None:
    for m in _TAT_CA:
        if m.id == str(ma or ""):
            return m
    return None


__all__ = ["Mau", "tat_ca", "theo_id"]

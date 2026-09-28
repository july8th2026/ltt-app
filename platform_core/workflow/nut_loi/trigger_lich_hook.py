"""`trigger.schedule` · `trigger.webhook` — hai điểm bắt đầu KHÔNG phải tay người.

## 🔴 Thứ thiếu ⛔ KHÔNG phải hạ tầng — nó đã chạy và đã có test

Đo 28/09/2026 trước khi viết tệp này. Toàn bộ đường thực thi **đã sống**:

| mảnh | ở đâu | trạng thái |
|---|---|---|
| bảng trigger (`kind`, `config`, `next_fire_at`) | `models.WorkflowTrigger` | có |
| bộ lịch cron thật | `trigger._TheoCron` qua **`cronsim`** | có, đã tra nguồn |
| vòng bắn trigger tới hạn | `dong_co._ban_trigger` → `ban_trigger.ban_den_han` | chạy đều |
| cửa webhook công khai | `POST /hooks/wf/{trigger_id}` (`server/routes/hooks.py`) | có |
| hạn mức mỗi trigger | `han_muc.vuot_han_webhook` | có |
| khử trùng | `khoa_idem.khoa_cron` / `khoa_webhook` | có |
| chính sách lỡ lịch | `ban_trigger.BO_LO` (`chay_mot_lan` · `bo_qua`) | có |
| tự tắt sau 5 lỗi | `ban_trigger` (spec §11.4) | có |

⇒ Thiếu **duy nhất** là **node trong registry** — tức thứ người soạn *thấy và kéo
  lên Canvas*. `apps/agent/mau.py` ghi *"`trigger.schedule` **không tồn tại**"*, và
  câu đó đúng **về node** nhưng dễ đọc thành *"tính năng chưa có"*.

⚠️ Đây là lần thứ **tư** trong một ngày gặp cùng hình dạng: `gate.ngan_sach_loi(
   tru_phien_khac=…)`, `ai_router.chon_nhanh()`, ba node `ai.*`, và nay bộ lịch
   cron. Mỗi lần: **đã xây, có test, ⛔ không ai nối**. ⇒ *"Có hàm + có test"* ⛔
   không trả lời *"tính năng có chạy không"* — câu trả lời nằm ở **ai gọi nó**.

## ⭐ Tên tham số PHẢI khớp `config` của trigger, ⛔ không phải một từ vựng mới

`cron` · `tz` · `bo_lo` — đọc thẳng từ `trigger._TheoCron._tz` (khoá `tz`) và
`ban_trigger` dòng ~104 (khoá `bo_lo`), ⛔ không tự đặt `mui_gio`/`khi_lo` cho
"dễ đọc". Một từ vựng thứ hai ở đây buộc phải có một lớp dịch, và lớp dịch ấy là
đúng nơi một trường bị **vứt im lặng** (ba lần cùng một chỗ nối, 24/09).

## ⛔ `trigger.webhook` KHÔNG có tham số token

Token webhook nằm ở `WorkflowTrigger.config` (`trigger.bam_token`/`token_khop`),
⛔ **không** ở `params` của node.

🔴 Vì sao đây là bảo mật chứ ⛔ không phải sở thích: `params` đi vào
   `workflow_version`, và `bien_dich._node_chung` đã ghi lại cái giá — bản ghi ấy
   **được nhân bản khi khách "Save as"** và trả nguyên văn cho trình soạn thảo.
   Một token trong đó là một bí mật đã rời khỏi tay chủ nó.

## 🔴 Bộ thi hành, ⛔ KHÔNG chỉ cờ `publish_duoc`

`trigger.manual` docstring ghi rõ, và nó đúng: `dong_co._chay_mot_inline` xử ca
thiếu bộ thi hành bằng `FAILED "loi_he_thong: … khong co bo thi hanh"`. ⇒ Mở cờ
một mình cho ra một node **publish sạch rồi FAILED lúc chạy** — tệ hơn hiện
trạng, vì hiện trạng chặn TRƯỚC khi khách bấm Chạy và giữ tiền.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.workflow import he_kieu
from platform_core.workflow.nut import Gia, NodeDefinition
from platform_core.workflow.nut_loi import dang_ky

#: Chính sách lỡ lịch — CÙNG tập với `ban_trigger.BO_LO`. Đọc tên hằng, ⛔ đừng
#: gõ lại hai chuỗi: lần `TRAN_N_GO_TAY` đổi 6→7 sửa một bên, bỏ bên kia, và
#: gate đỏ ở đúng phép kiểm đáng lẽ bảo vệ nó.
def _bo_lo() -> list:
    from platform_core.workflow.ban_trigger import BO_LO
    return list(BO_LO)


def _chay_trigger_lich(db, run, node: dict, **_):
    """`trigger.schedule` — thành công ngay, phát `event` mang mốc lịch.

    ⭐ `fired_at`/`bu` đọc từ `run.inputs` — đúng hai khoá `ban_trigger` đặt vào
       (`inputs={"fired_at": moc.isoformat(), "bu": la_bu}`). ⛔ Đừng tự sinh
       `datetime.now()` ở đây: mốc LỊCH và lúc BẮN là hai thứ khác nhau, và cả
       khoá khử trùng lẫn chính sách lỡ lịch đều dựa trên mốc lịch.
    """
    from platform_core.workflow.nut_loi.chay import KetQua

    vao = dict(getattr(run, "inputs", None) or {})
    return KetQua(output={"event": {
        "nguon": "lich",
        "fired_at": vao.get("fired_at", ""),
        # ⚠️ `bu` = *"lượt này là bù cho một mốc đã lỡ"*. Giữ nó ở cổng ra vì một
        #    workflow có quyền xử khác cho lượt bù (vd ⛔ không gửi thông báo).
        #    Vứt nó ở đây là vứt một thứ động cơ **đã tính** rồi.
        "bu": bool(vao.get("bu", False)),
    }})


def _chay_trigger_webhook(db, run, node: dict, **_):
    """`trigger.webhook` — thành công ngay, phát `event` mang thân + query.

    ⭐ `than`/`query` đọc từ `run.inputs` — đúng hai khoá `hooks.hook_workflow`
       đặt vào. `than` đã qua `_json_an_toan`, nên nó là JSON đã phân tích được
       hoặc `None`; ⛔ đừng phân tích lại ở đây.
    """
    from platform_core.workflow.nut_loi.chay import KetQua

    vao = dict(getattr(run, "inputs", None) or {})
    return KetQua(output={"event": {
        "nguon": "webhook",
        "than": vao.get("than"),
        "query": dict(vao.get("query") or {}),
    }})


TRIGGER_LICH = dang_ky(NodeDefinition(
    type="trigger.schedule", type_version=1, kind="trigger",
    category="TRIGGERS",
    title=N_("Chạy theo lịch"),
    description=N_("Tự chạy theo lịch bạn đặt, kể cả khi bạn không mở máy. "
                   "Mỗi lượt tiêu credit như một lần chạy tay."),
    icon="🕒",
    cong_vao=(),
    cong_ra=(("event", he_kieu.Cong(type="event", required=True, nhan="event")),),
    tham_so={
        "type": "object",
        "properties": {
            # ⭐ Tên khoá KHỚP `WorkflowTrigger.config` — xem docstring module.
            "cron": {"type": "string", "minLength": 1,
                     "description": N_("Biểu thức lịch, ví dụ `0 8 * * *` là "
                                      "8 giờ sáng mỗi ngày.")},
            "tz": {"type": "string", "default": "Asia/Ho_Chi_Minh",
                   "description": N_("Múi giờ tính lịch.")},
            "bo_lo": {"type": "string", "enum": _bo_lo(),
                      "default": "chay_mot_lan",
                      "description": N_("Nếu máy chủ ngừng và lịch bị lỡ: chạy "
                                       "một lần bù, hay bỏ qua.")},
        },
        "required": ["cron"], "additionalProperties": False,
    },
    thi_hanh="inline", gia=Gia.mien_phi(), quyen=frozenset(),
    cho=(), ma_loi=(), publish_duoc=True), _chay_trigger_lich)


TRIGGER_WEBHOOK = dang_ky(NodeDefinition(
    type="trigger.webhook", type_version=1, kind="trigger",
    category="TRIGGERS",
    title=N_("Nhận webhook"),
    description=N_("Một hệ thống khác gọi vào địa chỉ riêng của workflow này "
                   "để chạy nó. Địa chỉ và khoá lấy ở phần cấu hình trigger."),
    icon="🔗",
    cong_vao=(),
    cong_ra=(("event", he_kieu.Cong(type="event", required=True, nhan="event")),),
    # ⛔ RỖNG có chủ đích — token KHÔNG phải tham số node. Xem docstring module.
    tham_so={"type": "object", "properties": {}, "required": [],
             "additionalProperties": False},
    thi_hanh="inline", gia=Gia.mien_phi(), quyen=frozenset(),
    cho=(), ma_loi=(), publish_duoc=True), _chay_trigger_webhook)


__all__ = ["TRIGGER_LICH", "TRIGGER_WEBHOOK"]

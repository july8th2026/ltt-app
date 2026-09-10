"""App `prompt_canh` — kịch bản → khoá nhân vật → cảnh → JSON prompt.

Viết lại từ `bot_gem`, **bỏ hẳn** đường lái trình duyệt theo quyết định của chủ
dự án ngày 2026-09-09. Toàn văn + hệ quả:
`docs/migration/workflow_apps/09_QUYET_DINH_GEM_BO_TRINH_DUYET.md`.
"""
from __future__ import annotations

from platform_core.i18n import N_
from .services.kich_ban import TRAN_SO_CANH
from platform_core.registry import AppManifest, NavEntry, ToolSpec


def _gia(params: dict) -> int:
    """**0 — và số 0 này là một khẳng định, không phải một mặc định vô hại.**

    Mọi lượt model của App này chảy qua `runtime_noi_bo.luong`, nơi đã giữ credit
    theo trần token rồi hoàn về token thật. Khai thêm một giá ở tầng job là thu
    **hai lần** cho cùng một việc — đúng khuôn `apps/chatltt/gia_nghien_cuu.py`
    đã ghi, và đúng bài học *sàn làm tròn là một tầng khác với bảng giá*: bảng
    giá đúng mà tiền thu ra sai.

    ⚠️ Nhưng 0 mở một lỗ khác: job vào hàng đợi mà **không giữ chỗ**, nên một
       tài khoản 0 credit vẫn nộp được, worker vẫn chạy, rồi lượt model đầu tiên
       trả `ThieuCredit` — khách chờ vô ích. Cửa ấy là một **điều kiện trước khi
       nộp** ở `routes.py`, không phải một **giá**; nên nó không nằm trong sổ
       tiền và không tính hai lần thứ gì.
    """
    return 0


MANIFEST = AppManifest(
    slug="prompt_canh",
    display_name=N_('Kịch bản → prompt cảnh'),
    route_prefix="/prompt-canh",
    summary=N_('Từ một kịch bản, khoá đặc điểm nhân vật, chia thành danh sách '
               'cảnh, rồi sinh prompt JSON cho từng cảnh.'),
    icon="🎬",
    accent="#B45309",
    group="Workflow",

    nav=(NavEntry(label=N_('Kịch bản → prompt'), path="/prompt-canh", nav_key="prompt_canh"),),

    job_types=("prompt_canh.run",),
    # `api` — khong GPU, khong trinh duyet. Xem `09_QUYET_DINH_...`.
    requires=("api",),
    # 🔴 Trần thời gian phải KHỚP với `TRAN_SO_CANH`. Job này gọi model tuần tự
    #    qua máy B (MỘT suất đồng thời), và `runtime_noi_bo` thu tiền từng lượt
    #    — chết ở trần nghĩa là khách đã trả mà không nhận gì.
    #    250 cảnh = 76 lượt gọi; 3600 s / 76 = 47 s mỗi lượt.
    #    `tests/test_1105` chốt bất đẳng thức ấy để hai con số không trôi khỏi nhau.
    max_runtime_s={"prompt_canh.run": 3600},
    credit_cost=_gia,

    enabled=True,
    public=False,
    surface="customer",
    lifecycle="development",
    capabilities=("AI Text",),

    tools=(ToolSpec(
        name="prompt_canh.run",
        job_type="prompt_canh.run",
        description=N_('Sinh prompt cảnh từ một kịch bản.'),
        params_schema={
            "kich_ban": {"type": "text", "required": True, "max_length": 100000},
            "so_canh": {"type": "int", "min": 1, "max": TRAN_SO_CANH,
                        "default": 20},
            "batch_step2": {"type": "int", "min": 1, "max": 50, "default": 10},
            "batch_step3": {"type": "int", "min": 1, "max": 50, "default": 5},
            "visual_style": {"type": "string", "max_length": 200},
            "duration": {"type": "string", "max_length": 40},
            # `hidden` + `default` bat buoc di doi: mot tham so an ma thieu mac
            # dinh thi tang API bo trong, va handler tu chon mot thu khac — kho
            # nay da co mot tool storyboard chay VA TINH TIEN sai nhanh vi dung
            # loi ay.
            "model": {"type": "model_ref", "category": "text",
                      "providers": ["ltt_llm"], "default": "chat"},
        },
        returns={"ket_qua": "json"},

        # `none`, khong phai `external`: qua `runtime_noi_bo` moi luot la mot loi
        # goi co ke toan rieng, nen no luy dang duoc. Ban cu khai `external` vi
        # moi luot tieu mot suat trong han muc PHIEN cua mot tai khoan nguoi
        # that — dieu do khong con dung.
        # ⛔ CUA THU NHAT trong bon cua, va no dang MO khi khong nen mo.
        #
        # 🔴 Do o Phase 14: bo loc bang cong cu cua khach la
        #    `presentationAdapter.ts:65` — `tool.customer_visible!==false`, HET.
        #    Khong co bo loc `lifecycle` nao trong ca duong Agent.
        #
        #    Nen mot App khai `lifecycle="development"`, `public=False`, CHUA
        #    nghiem thu E2E, van hien trong palette cua khach va bam chay duoc.
        #    `public=False` chi giau trang web cua App; no khong giau tool.
        #
        # ⇒ Dong cua nay lai cho toi khi parity dong va nghiem thu E2E xong. Day
        #   la sua METADATA cua Tool, dung nhu Phase 14 yeu cau ("uu tien sua
        #   Tool metadata truoc planner; khong nhet luat App-specific vao Agent").
        #
        # ⚠️ `customer_visible=False` KHONG go nang luc: `discover_tools()` van
        #    thay, `runtime_noi_bo.bao_gia()` van tra duoc gia, va workflow da
        #    dung no van chay. Cung khuon `apps/chatltt` da dung.
        customer_visible=False,
        side_effect="external",
        idempotency={"key_fields": ("kich_ban", "so_canh")},
        # Khong tu khai suat: admission cua `text.chat` lo phan gianh cho.
        resource={"class": "api", "slots": 1, "est_duration_s": 600},

        api_exposed=False,
    ),),
)

"""
ChatLTT — sản phẩm hội thoại LTT-native trên ba model nhà. (H43, 2026-09)

## Vì sao là một APP mà không phải một platform capability

Nó là **một bề mặt khách ở một đường dẫn** (`/chatltt`, Q30). Nó không mount
ngoài `route_prefix`, không cấp credential toàn hệ thống — hai lý do khiến Public
API (Q92) và Nexus (Q93) phải là capability. Xem `docs/CHATLTT/00_PHUONG_AN_VA_LO_TRINH.md` D1.

## Vì sao KHÔNG có job_types / credit_cost / tools

ChatLTT là **client** của ba năng lực đã có giá, đã có job, đã có admission:
`text.chat` (`apps/ltt_llm`), `image.ltt` (`apps/anhnoibo`), `speech.ltt`
(`apps/ltt_voice`). Nó gọi qua `platform_core.runtime_noi_bo` — không tự tính
giá, không tự dựng hàng đợi, không import ba app kia (test_147/test_308 chốt).
Khai `job_types` ở đây là mời một sổ tiền thứ hai.

## Trạng thái

`enabled=True`, `public=True` từ **03/09/2026**, khi Phase 13 của H43 PASS.

Trước đó app chạy `enabled=False, public=False`: route vẫn được gắn (để trang
giữ chỗ trả 200 cho người đã đăng nhập — bẫy link 404 trong header,
`AGENTS.md` §8.2c) nhưng không lên catalog và không lên header.

⭐ Bằng chứng bật cờ, không phải "thấy chạy được": tám hành trình A–H chạy lại
   **tươi** trên trình duyệt thật (CSDL mới, hai người dùng, model và worker
   giả), `docs/CHATLTT/reports/13_nghiem_thu.md`. Hành trình B (vision) trượt ở
   lượt đầu và được xây xong trong chính pha đó — `MVP_ACCEPTANCE.md` ghi
   *"vision if advertised"*, và catalog thì đang quảng cáo `reads_images`.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.registry import AppManifest, ToolSpec

from apps.chatltt import gia as _gia
from apps.chatltt.services import hoi_thoai as _hoi_thoai, nghien_cuu as _NC

MANIFEST = AppManifest(
    slug="chatltt",
    display_name="ChatLTT",
    route_prefix="/chatltt",
    summary=N_('Trò chuyện với model của LTT: văn bản, ảnh và giọng nói trong một hội thoại.'),
    icon="💬",
    accent="#0F62FE",

    # ⚠️ CAP NHAT 06/09 (H44 P06 buoc 3). Truoc do la `()`: ChatLTT chi NOP job
    #    sang app khac (`anhnoibo`, `ltt_voice`) qua `tao_media`. `trich_tep` la
    #    viec DAU TIEN app nay tu chay trong worker — nen no them mot thu
    #    `job_runner` biet chay, tuc mot be mat moi cho `leases` va cho so tien.
    #
    # ⛔ No CHUA duoc mo cho model goi. `chinh_sach.CONG_CU_CHO_PHEP` va
    #    `chieu_tool.CHO_MODEL_GOI` van dong — buoc 6 moi mo, theo dung §4.
    #
    # ⚠️ CAP NHAT 07/09 (B6 buoc 3). `chatltt.nghien_cuu` — vong nghien cuu tren
    #    TAI LIEU CUA CHINH KHACH. No la job vi vong lap goi model nhieu luot va
    #    tran Cloudflare la 100 giay (`CLAUDE.md`).
    #
    # ⛔ Gia cua no la **0**, va do la mot khang dinh chu khong phai mot cho
    #    trong: moi luot model da duoc `runtime_noi_bo` giu-va-hoan theo token
    #    that. Xem `apps/chatltt/gia_nghien_cuu.py` — day dung la "so tien thu
    #    hai" ma chinh docstring o tren canh bao.
    job_types=("chatltt.trich_tep", "chatltt.nghien_cuu"),

    # ⚠️ CAP NHAT 06/09 (B1). `job_types` mot minh KHONG du: `bao_gia()` cua
    #    `runtime_noi_bo` tra gia qua `ToolSpec`, nen thieu khai nay thi khong
    #    HIEN duoc gia truoc khi khach bam — ma "gia phai hien TRUOC khi bam"
    #    la dieu P06 §7 da chot. Toi bo sot mat xich nay o buoc 3c.
    #
    # ⛔ `customer_visible=False`: day la cua thu NHAT trong bon cua. Tep nay
    #    chi noi "tool nay TON TAI va gia bao nhieu"; viec no co ra `/api/v1`
    #    hay khong la cua thu HAI (`api_exposed`), va ca hai deu KHONG mo.
    tools=(ToolSpec(
        name="chatltt.trich_tep",
        job_type="chatltt.trich_tep",
        description=N_('Trích văn bản từ tài liệu đã đính vào hội thoại.'),
        params_schema={
            # ⭐ KHOA PHAN LOAI (B6 buoc 3). `credit_cost` cua app la MOT ham cho
            #    ca app va chu ky khong mang `job_type`, nen viec phai duoc KHAI
            #    chu khong duoc suy tu hinh dang tham so. Cung tien le
            #    `autosubvideo._cost` doc `params["operation"]`.
            "viec": {"type": "enum", "values": ["trich_tep"],
                     "default": "trich_tep"},
            "tep_id": {"type": "string", "required": True, "max_length": 40},
            # ⭐ `so_byte` chi de UOC gia giu cho. Gia THAT tinh o
            #    `jobs.handle` theo ky tu trich duoc — cung luat
            #    `anhnoibo`: tinh theo thu THAT SU nhan duoc.
            "so_byte": {"type": "int", "min": 0, "max": 104_857_600,
                        "default": 0},
        },
        # ⭐ `returns` la ban khai cong RA. `bo_chay_tool._tep_cua` doc chinh
        #    no de biet job tra ve gi — doan gia ten cong da la mot loi that
        #    o P05 (`ket_qua_job` doan ten roi tra rong).
        # ⛔ `TOOL_PORT_TYPES` chi nhan kieu DUONG ONG (text/image/json/...),
        #    khong nhan `int`. Vi `returns` mo ta CONG NOI DUOC VOI TOOL KHAC,
        #    khong phai kieu du lieu cua ket qua. Toi khai `int` va registry
        #    tu choi nap ca app — dung huong, fail-closed.
        returns={"ket_qua": "json"},
        side_effect="external",
        resource={"class": "api", "slots": 0},
        idempotency={"key_fields": ("tep_id", "viec", "so_byte")},
        customer_visible=False,
    ), ToolSpec(
        # ⚠️ B6 buoc 3. Vong nghien cuu tren TAI LIEU CUA CHINH KHACH — nen
        #    tang nay KHONG co kha nang tim web (§1 cua ke hoach: khong mot tep
        #    nao khai tavily/serper/brave/searx). Mo `web.tim` la mot quyet dinh
        #    THUONG MAI, cung hang voi gia trich, nen no khong o day.
        name="chatltt.nghien_cuu",
        job_type="chatltt.nghien_cuu",
        description=N_('Nghiên cứu một câu hỏi trên tài liệu bạn đã đính vào hội thoại này.'),
        params_schema={
            "viec": {"type": "enum", "values": ["nghien_cuu"],
                     "default": "nghien_cuu"},
            # ⛔ Pham vi la MOT hoi thoai, khong phai ca kho tep cua nguoi dung:
            #    `tim_doan.tim` loc theo CA `user_id` va `conversation_id`. Khai
            #    `required` de khong ai nop mot lenh nghien cuu khong pham vi.
            "conversation_id": {"type": "string", "required": True,
                                "max_length": 40},
            "cau_hoi": {"type": "string", "required": True, "max_length": 2000},
            # ⭐ Tran do NGUOI DUNG chon trong khoang, nhung tran cung van la
            #    `nghien_cuu.TRAN_VONG` — mot tham so khong duoc nang tran cua
            #    chinh no. Cung luat `thi_hanh(boi_canh=…)`: model/khach de nghi
            #    DO BEN, khong de nghi DIA CHI.
            "tran_vong": {"type": "int", "min": 1, "max": _NC.TRAN_VONG,
                          "default": _NC.TRAN_VONG},
        },
        returns={"ket_qua": "json"},
        side_effect="external",
        resource={"class": "api", "slots": 0},
        idempotency={"key_fields": ("viec", "cau_hoi", "conversation_id",
                                    "tran_vong")},
        customer_visible=False,
    ),),
    requires=(),
    # ⛔ GIA CHUA CHOT cho `trich_tep` — `gia_trich.credit_cost` NEM cho toi khi
    #    chu du an dat so. Fail-closed co chu dich: mot gia 0 tam thoi CHINH LA
    #    cai lo ma cua credit cua `upload_sessions` sinh ra de bit, chi khac la
    #    no trong nhu mot mac dinh vo hai. Xem `apps/chatltt/gia_trich.py`.
    #
    # ⚠️ CAP NHAT 07/09 (B6 buoc 3): tro sang bo PHAN NHANH. `credit_for()` goi
    #    MOT ham cho ca app va khong truyen `job_type`, nen viec phai duoc khai
    #    o `params["viec"]`. Xem `apps/chatltt/gia.py`.
    credit_cost=_gia.credit_cost,

    enabled=True,
    public=True,
    surface="customer",
    lifecycle="development",
    group="Chat",
    badge=N_('MỚI'),
    capabilities=("Chat", "AI Text", "audio"),
    # Bảng CSDL riêng của app (Phase 07): `chatltt_conversations`, `chatltt_messages`,
    # `chatltt_executions` — trong `apps/chatltt/tables.py`.
    table_prefix="chatltt",

    # Viec dinh ky: don that nhung hoi thoai da xoa mem qua 30 ngay. Chay duoi
    # lease cua nen tang nen dung MOT lan tren ca cum (khuon `apps/vps/bao_tri`).
    bao_tri=_hoi_thoai.bao_tri,
    bao_tri_moi_giay=6 * 3600,
    notes=("Client noi bo cua text.chat / image.ltt / speech.ltt qua "
           "platform_core.runtime_noi_bo. Khong goi /api/v1, khong biet URL may B."),
)

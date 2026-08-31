"""
App `ltt_voice` — giọng nói tiếng Việt nhân bản, model chạy trên **máy A** (Q117).

⭐ VÌ SAO LÀ MỘT APP CHỨ KHÔNG PHẢI MỘT PROVIDER (khác Q102 với `ltt_image`):

   Q102 đúng cho máy B — ở đó model là một dịch vụ HTTP ở **máy khác**, có token
   phải cất và xoay, có thể chết độc lập. Đó đúng là việc của `api_pool`.

   Ở đây engine chạy **cùng máy, sau loopback**: không có khoá để xoay, không có
   hạn mức nhà cung cấp để đo, không có cooldown để áp. Đăng ký làm provider sẽ
   buộc mở rộng enum hạng mục khoá API — tức **sửa nền tảng cho một năng lực
   không dùng tới**.

   Và Voice Profile là **dữ liệu nghiệp vụ có chủ sở hữu, có vòng đời, có
   consent** — provider không sở hữu bảng. Hợp đồng app đã chừa `table_prefix`
   cho đúng việc này (tiền lệ `apps/vps/`).

⛔ BA CỔNG ĐỘC LẬP trước khi khách ngoài gọi được (Q92 fail-closed):
     ① `api_exposed=True` ở đây
     ② `LTT_PUBLIC_API` bật
     ③ tên tool có trong `LTT_PUBLIC_API_TOOLS`
   Quên một cái là tool không ra. Đó là chủ ý.

🔴 CỔNG THỨ TƯ của riêng app này: dịch vụ `LTTStudioVoice` phải đang chạy. App tự
   khai `blocker_titles` để nền tảng gắn badge "cần thiết lập" lên đúng thẻ này
   thay vì treo một banner toàn cục.

⛔ GIÁ KHÔNG Ở FILE NÀY. Nó ở `gia.py` — một chỗ duy nhất, có phiên bản, công bố
   được. `credit_cost` dưới đây chỉ là **trần ước cao** để giữ chỗ; giá cuối do
   `jobs.handle` báo về theo **thời lượng thật sự sinh ra** (khuôn 3.4 + 4.4).
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.registry import AppManifest, NavEntry, ToolSpec

from . import gia
from .tham_so_cong_khai import TRAN_KY_TU_CONG_KHAI


def _gia(params: dict) -> int:
    """TRẦN ƯỚC CAO để giữ chỗ, **không phải giá cuối**.

    Giá cuối do handler báo qua `credit_cost`, tính theo **giây tiếng thật sự
    sinh ra được** (đo bằng ffprobe). Phần giữ dư hoàn ngay khi job xong.
    """
    p = params or {}
    if str(p.get("_job_type") or "").endswith("enroll"):
        return gia.CREDIT_GHI_DANH

    # ⭐ Đếm trên văn bản ĐÃ CHUẨN HOÁ, không trên văn bản thô. "1.500.000 đồng"
    #    là 14 ký tự nhưng đọc ra "một triệu năm trăm nghìn đồng" — hơn hai giây.
    #    Ước trên bản thô thì phải hạ tỉ lệ để gánh hộ phần nở đó, và mọi văn bản
    #    thường phải trả giá cho khả năng ấy. Chuẩn hoá trước thì phần nở đã nằm
    #    trong số ký tự, và tỉ lệ về đúng thang đã đo.
    #
    #    Phép chuẩn hoá này chỉ là regex — vài chục micro giây, và nó chạy ở mọi
    #    lượt báo giá nên không được phép chạm mạng hay CSDL.
    from . import text_pipeline
    da = text_pipeline.chuan_hoa(str(p.get("text") or ""))
    return gia.uoc_tran(so_ky_tu=len(da))


MANIFEST = AppManifest(
    slug="ltt_voice",
    display_name=N_('Giọng nói LTT'),
    route_prefix="/ltt-voice",
    summary=N_('Chuyển văn bản thành giọng nói tiếng Việt tự nhiên. Tạo giọng '
               'riêng của bạn từ một clip ba tới tám giây.'),
    icon="🎙️",
    accent="#0F766E",
    group=N_('Âm thanh'),
    badge=N_('MỚI'),

    nav=(
        NavEntry(N_('Tạo tiếng nói'), "/ltt-voice", "🎙️", "ltt_voice"),
        NavEntry(N_('Giọng của tôi'), "/ltt-voice/giong", "🗣️", "ltt_voice_giong"),
        NavEntry(N_('Lịch sử'), "/ltt-voice/lich-su", "🕘", "ltt_voice_lich_su"),
    ),

    job_types=("ltt_voice.synthesize", "ltt_voice.enroll"),

    # 🔴 NĂNG LỰC RIÊNG `voice`, VÀ ĐÂY LÀ CHỖ DỄ HỎNG NHẤT KHI DEPLOY.
    #
    #    `platform_core/jobs.py` lọc bằng
    #        set(manifest.requires).issubset(capabilities)
    #    nên nếu production đã đặt `LTT_WORKER_POOLS` mà KHÔNG có làn `voice`
    #    thì job nằm `queued` **mãi mãi** — không lỗi, không cảnh báo,
    #    `/health/ready` vẫn 200.
    #
    #    Thêm `voice:1` vào `LTT_WORKER_POOLS` trước khi deploy. `4-nghiem-thu.ps1`
    #    có chốt cho việc này.
    requires=("voice",),

    # ĐO THẬT 2026-08-30 trên RTX 5060 Ti (`docs/LTT_VOICE/do_v1.json`):
    #   torch allocated dinh   641 MB
    #   torch reserved         1.288 MB
    #   nvidia-smi tien trinh  ~1.859 MB
    # Lấy 2.000 làm sàn xếp chỗ — trên số đo, dưới xa `upscalevideo` quality
    # (12.000 MB), nên hai app sống chung được trên một card 16 GB.
    #
    # ⚠️ Đây là sàn ĐỂ XẾP CHỖ, không phải hạn mức cứng. Khai thiếu thì job vẫn
    #    chạy nhưng có thể bị xếp vào card chật.
    gpu_vram_mb={"ltt_voice.synthesize": 2000, "ltt_voice.enroll": 2000},

    # Đo được: 3.000 ký tự mất 17,6 giây sinh. Trần 900 giây cho một job là rất
    # rộng, và nó tồn tại để bắt job **treo** chứ không để bắt job chậm: một job
    # treo mà vẫn đập nhịp sẽ giữ slot vô hạn và không ai được báo.
    max_runtime_s={"ltt_voice.synthesize": 900, "ltt_voice.enroll": 300},

    credit_cost=_gia,

    enabled=True,
    public=True,
    surface="customer",
    # PHAT HANH 2026-08-31, sau khi ba man hinh duoc kiem TREN URL CONG KHAI
    # bang trinh duyet that (CLAUDE.md quy tac 5b), khong chi bang test:
    #   · GET /ltt-voice, /giong, /lich-su -> 200, render dung, 0 loi console
    #   · bam nut Tao -> job that -> worker that -> 24 giay -> WAV 399 KB
    #   · so tien: 56 -> 55 credit, khop voi `credit_cost` handler bao ve
    # Vong kiem do tim ra ba loi ma toan bo bo test da bo qua: 422 (thieu chu
    # kieu o `Depends`), 500 (sai chu ky `TemplateResponse`), va `owner_id`
    # kieu so trong khi `User.id` la UUID chuoi.
    lifecycle="released",
    capabilities=("audio",),
    table_prefix="voice",

    blocker_titles=(N_('Dịch vụ giọng nói (LTTStudioVoice)'),),

    tools=(
        ToolSpec(
            name="speech.ltt",
            job_type="ltt_voice.synthesize",
            description=N_('Chuyển văn bản thành giọng nói tiếng Việt.'),
            params_schema={
                "text": {"type": "string", "required": True,
                         "max_length": TRAN_KY_TU_CONG_KHAI},
                # `voice_id` là danh tính CÔNG KHAI, ổn định qua mọi lần nâng
                # engine. Khách không bao giờ thấy speaker embedding.
                "voice_id": {"type": "string", "required": False,
                             "max_length": 40},
                "preset": {"type": "string", "required": False,
                           "max_length": 64},
            },
            returns={"audio_key": "audio", "text": "text"},

            # 🔴 MỘT GPU = MỘT VIỆC, và cả ba cửa (job/sync/stream) phải giành
            #    cùng một slot. Không khai thì cửa đồng bộ đi vòng qua hàng đợi
            #    và hai lượt cùng đập vào một card (Q114).
            admission_resource="vieneu_gpu",
            admission_slots=1,

            api_exposed=True,
            api_contract={
                "scopes": ("jobs:create",),
                "description": (
                    "Turn Vietnamese or English text into natural speech. Use a "
                    "built-in preset voice, or one of your own cloned voices by "
                    "its stable voice id."),
                # ⛔ KHÔNG lộ tham số sinh mẫu (Q119): cache CUDA graph của
                #    upstream khoá theo (batch, temperature, top_k, top_p), và
                #    temperature cao làm lệch tông giữa các đoạn.
                "hidden": (),
                "params": {
                    "text": {
                        "description": (
                            "What to say. Vietnamese, English, or both mixed. "
                            f"Up to {TRAN_KY_TU_CONG_KHAI} characters per call - "
                            "longer scripts should be split into several calls, "
                            "because voice consistency degrades on very long "
                            "single passes."),
                        "example": "Xin chào, đây là giọng đọc của LTT Studios.",
                    },
                    "voice_id": {
                        "description": (
                            "One of your own cloned voices, as returned when you "
                            "created it. Stays valid across engine upgrades. "
                            "Leave empty to use a built-in voice."),
                        # Vi du viet theo HINH DANG, khong phai mot ma that: mot chuoi 32 ky tu
                        # hex tran trong ma nguon bi `tools/check_secrets.py`
                        # bat la `bare_32_char_hex`, va bo doi bao dong do la
                        # sai — no dung viec, chi la o day khong phai bi mat.
                        "example": "vc_<32 ky tu hex>",
                    },
                    "preset": {
                        "description": (
                            "A built-in voice name. Ignored when voice_id is "
                            "given; sending both is rejected."),
                        "example": "Adam",
                    },
                },
            },
        ),
    ),
)

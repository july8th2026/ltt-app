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

from . import gia, nghe_thu
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
    # ⛔ BA MƯƠI, không phải tám. `audio_input.GIAY_TOI_DA = 30.0`, điều khoản
    #    và biểu mẫu đều nói 3–30; chỉ dòng văn xuôi này gõ tay nên nó trôi.
    #
    #    Và nó trôi về phía tệ nhất: nói THẤP hơn sự thật khiến khách **tự tay
    #    làm hỏng kết quả của chính họ**. Người có clip 20 giây đọc thẻ này rồi
    #    cắt còn 8 — trong khi bộ chọn vừa đo được là nó dùng đúng phần
    #    13,08–20,80s của một clip 29,58s. Họ vứt đi đúng phần tốt nhất, và
    #    không bao giờ biết là mình đã vứt.
    summary=N_('Chuyển văn bản thành giọng nói tiếng Việt tự nhiên. Tạo giọng '
               'riêng của bạn từ một clip ba tới ba mươi giây — hệ thống tự '
               'chọn đoạn tốt nhất trong đó.'),
    icon="🎙️",
    accent="#0F766E",
    group=N_('Âm thanh'),
    badge=N_('MỚI'),

    # ⭐ SÁU TAB, và từ P8 **cả sáu đều đã xây** — không tab nào còn
    #    `built=False`. Cơ chế badge "đang xây" của nền tảng vẫn còn nguyên và
    #    vẫn dùng được; thứ đã biến mất là những màn cần tới nó.
    #
    # ⛔ Nếu một ngày thêm tab thứ bảy chưa xây: đặt `built=False` chứ ĐỪNG giấu
    #    tab đi. Hai thứ đó nói hai điều khác nhau — giấu nói *"sản phẩm không
    #    có việc này"*, badge nói *"có, và chưa tới lượt"*. Và tab đã hiện thì
    #    bấm vào phải tới một chỗ nói được điều gì đó: một tab dẫn tới 404 tệ
    #    hơn không có tab, vì nó biến một lời hứa thành một lỗi. Cơ chế trang
    #    giữ chỗ cũ (`vo.CHUA_XAY` + `routes/_p_chua_xay.py`) đã gỡ khi màn cuối
    #    được xây — dựng lại nó rẻ hơn là để nó nằm đó không phục vụ ai.
    #
    # Thứ tự theo luồng làm việc thật, không theo thứ tự xây: viết → chọn giọng →
    # gom thành dự án → chạy hàng loạt → xem lại → tự động hoá.
    nav=(
        NavEntry(N_('Tạo tiếng nói'), "/ltt-voice", "🎙️", "ltt_voice"),
        NavEntry(N_('Giọng của tôi'), "/ltt-voice/giong", "🗣️", "ltt_voice_giong"),
        NavEntry(N_('Dự án'), "/ltt-voice/du-an", "📚", "ltt_voice_du_an"),
        NavEntry(N_('Lịch sử'), "/ltt-voice/lich-su", "🕘", "ltt_voice_lich_su"),
        NavEntry(N_('API'), "/ltt-voice/api", "🔌", "ltt_voice_api"),
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

    # Bận thì 3 giây sau hỏi lại, thay vì 20 giây mặc định của nền tảng.
    #
    # 🔴 ĐO THẬT 31/08/2026, năm job đồng thời trên một suất:
    #      làm việc thật : 4,75 – 5,42 giây
    #      xếp hàng      : 0,07 → 20,2 → 40,8 → 61,2 → 82,0 giây
    #    Bậc 20 giây KHÔNG phải thời gian job trước chiếm GPU — nó nhả sau ~5
    #    giây. Đó là thời gian job sau chưa quay lại hỏi. GPU nằm không ~15
    #    trong mỗi 20 giây.
    #
    # ⚠️ 3 chứ không phải 1: mỗi lượt hỏi là một vòng CSDL, và với nhiều job
    #    xếp hàng thì 1 giây thành một vòng lặp bận. 3 giây giữ phần lãng phí
    #    dưới ~40 % của một lượt 5 giây mà không biến hàng đợi thành máy bơm.
    cho_tai_nguyen_s={"ltt_voice.synthesize": 3, "ltt_voice.enroll": 3},

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

    # ── Việc định kỳ: dựng dần tệp NGHE THỬ cho hai mươi giọng dựng sẵn ──────
    #
    # 🔴 QUA HỢP ĐỒNG, KHÔNG TỰ DỰNG VÒNG LẶP. `_mot_luot_bao_tri` chạy dưới
    #    lease `bao_tri` nên việc này chạy **đúng một lần trên toàn cụm**; một
    #    vòng lặp app tự dựng sẽ chạy ở MỌI tiến trình worker, và với
    #    `LTT_WORKER_POOLS` nhiều làn thì cùng một tệp bị sinh N lần trên N card.
    #    Tiền lệ và lời cảnh báo: `apps/vps/bao_tri.py`.
    #
    # ⚠️ Mỗi lượt chỉ dựng tối đa `nghe_thu.MOI_LUOT_TOI_DA` giọng. Hai mươi
    #    giọng warm đủ sau bảy lượt — chậm có chủ ý, vì vòng bảo trì dùng chung
    #    tiến trình với worker job và một phút giữ GPU liền là một phút job của
    #    khách chờ mà không có gì giải thích.
    bao_tri=nghe_thu.bao_tri,
    bao_tri_moi_giay=3600,

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

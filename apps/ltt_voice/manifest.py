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

from . import gia, nghe_thu, sidecar_client
from .tham_so_cong_khai import (SO_LAN_THU_JOB, TRAN_KY_TU_CONG_KHAI,
                                TRAN_MOI_LUOT_SINH)


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
    # ⭐ `preset` LẤY TỪ `params`, KHÔNG TRA CSDL. Đó là thứ làm hồ sơ tốc độ
    #    theo từng giọng khả thi ở đúng đường này: tên preset đã nằm sẵn trong
    #    tham số, nên `gia.giay_uoc` chỉ tra một `dict` nạp lúc import.
    #
    # ⛔ Giọng nhân bản (`voice_id`) KHÔNG có hồ sơ và sẽ không bao giờ có —
    #    chúng sinh ra sau lượt đo. Truyền `""` là đúng: `giay_uoc` lùi về hai
    #    hằng số chung, y như trước 08/09.
    # 🔴 CHIA ĐOẠN RỒI MỚI TÍNH, và bỏ bước này là GIỮ THIẾU CREDIT.
    #
    #    `gia.giay_uoc` là mô hình **hai tham số**: `khoi_dong + n/toc_do`. Phần
    #    `khoi_dong` là khoảng lặng model thêm vào **mỗi lượt phát**, và một bản
    #    đọc dài là N lượt phát ghép lại — nên bản ghép thật mang N khoảng lặng,
    #    không phải một.
    #
    #    Bản trước gọi `uoc_tran(so_ky_tu=len(da))`, tức tính như thể cả bài là
    #    **một** lượt phát. Đo 08/09/2026 trong trần công khai hiện tại:
    #
    #        n =   5.000 ky tu ->  4 doan: giu 56 / gia neu that 57   (thieu 1)
    #        n = 100.000 ky tu -> 67 doan: giu 1112 / gia neu that 1132 (thieu 20)
    #
    # ⛔ Lệch nhỏ, nhưng lệch về **đúng phía cấm**: chốt 3.3 nói ước phải
    #    >= giá thật **LUÔN LUÔN**. Và hậu quả không phải "thu thiếu 20 credit"
    #    — quyết toán vượt phần giữ thì lượt chạy bị đánh hỏng **sau khi** đã
    #    tiêu hết GPU, tức khách chờ xong rồi nhận một lỗi.
    #
    # ⭐ `uoc_tran_lo` cộng **milli-credit** rồi mới làm tròn đúng một lần, nên
    #    một bài 67 đoạn không phải trả thừa 67 lượt làm tròn.
    #
    # ⚠️ `can_bang=True` để khớp `text_pipeline.chuan_bi` — chính hàm mà worker
    #    dùng. Chia kiểu khác cho số đoạn khác, và hai số đoạn khác nhau là hai
    #    hoá đơn khác nhau cho cùng một bài.
    #
    # ⛔ VẪN THUẦN TÍNH TOÁN: `chia_doan` chỉ là phép cắt chuỗi. Không CSDL,
    #    không mạng — điều kiện mà chú thích dài bên trên đặt ra vẫn giữ.
    from . import text_pipeline
    from .tham_so_cong_khai import TRAN_MOI_LUOT_SINH
    da = text_pipeline.chuan_hoa(str(p.get("text") or ""))
    doan = text_pipeline.chia_doan(da, tran_moi_doan=TRAN_MOI_LUOT_SINH,
                                   can_bang=True)
    return gia.uoc_tran_lo(cac_do_dai=[len(d) for d in doan] or [len(da)],
                           giong=str(p.get("preset") or ""))


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

    # ⭐ NĂM TAB, và từ P8 **cả năm đều đã xây** — không tab nào còn
    #    `built=False`. Cơ chế badge "đang xây" của nền tảng vẫn còn nguyên và
    #    vẫn dùng được; thứ đã biến mất là những màn cần tới nó.
    #
    # 🔴 TỪNG LÀ SÁU, VÀ TAB THỨ SÁU KHÔNG ĐƯỢC XÂY — có chủ ý.
    #
    #    "Chạy lô" được thiết kế khi một lượt sinh trần ở 1.500 ký tự: muốn
    #    đọc nhiều hơn thì phải nộp nhiều dòng. Đường tài liệu dài (03/09) lấy
    #    mất chính nhu cầu đó: một ô nhập duy nhất nay nhận `TRAN_KY_TU_CONG_KHAI`
    #    và tự chia, nên "nộp hai mươi dòng rồi ghép tay" không còn là việc
    #    khách phải làm. Phần còn lại — soạn nhiều khối, mỗi khối một giọng,
    #    sửa lại từng khối — là đúng định nghĩa của **Dự án**.
    #
    # ⛔ ĐỪNG DỰNG LẠI "Chạy lô" để một chú thích nói "sáu tab" thành đúng.
    #    Nó chỉ quay lại nếu có một năng lực lô THẬT khác cả Dự án lẫn tài liệu
    #    dài — ví dụ `infer_batch` của sidecar (xem `tables_du_an.py`), thứ gộp
    #    nhiều đoạn vào MỘT lượt GPU. Mô hình cũ — mỗi dòng một job — không
    #    phải năng lực đó, nó chỉ là một vòng lặp có giao diện.
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

    # Trần này tồn tại để bắt job **treo**, không để bắt job chậm: một job treo
    # mà vẫn đập nhịp sẽ giữ slot vô hạn và không ai được báo.
    #
    # 🔴 3600 CHO `synthesize`, VÀ CON SỐ ẤY ĐI CÙNG `TRAN_KY_TU_CONG_KHAI`.
    #
    #    Trước 03/09 nó là 900 giây, hợp lý khi trần yêu cầu là 1.500 ký tự
    #    (một lượt đọc ~75 giây). Nhưng nó là **ràng buộc thật** của trần mới:
    #    đo 03/09 cho 0,00763 giây GPU mỗi ký tự, nên 100.000 ký tự cần ~763
    #    giây ở tốc độ đo được — tức nó sẽ **vừa vặn chạm** 900 và hỏng ở đúng
    #    những tài liệu dài nhất, sau khi đã tiêu gần hết phần GPU của chúng.
    #
    # ⭐ 3600 cho biên ~4,7 lần so với tốc độ đo được, tức vẫn còn nguyên biên
    #    khi GPU chậm gấp đôi vì đang chia với một job khác. Đây là **chốt chặn
    #    cho job treo**, không phải hạn mức hiệu năng — nên nó phải rộng hơn ca
    #    xấu nhất hợp lệ, chứ không sát ca trung bình.
    #
    # ⛔ Đừng nâng nó mà không nâng `TRAN_KY_TU_CONG_KHAI` theo, và ngược lại.
    #    Hai con số này là hai đầu của cùng một ngân sách; lệch nhau thì hoặc
    #    job chết oan, hoặc một job treo giữ GPU lâu hơn cần thiết.
    max_runtime_s={"ltt_voice.synthesize": 3600, "ltt_voice.enroll": 300},

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

    # Số lần thử: nạp model lúc deploy mất 39,9–73,1 giây (đo trong
    # `tham_so_cong_khai.py`), cửa sổ 3 lượt mặc định ~30 giây là job chết mỗi
    # lần deploy. Khai ở đây để **mọi** cửa (web, `/api/v1`, client nội bộ) cùng
    # đọc một số — trước 02/09 chỉ bốn route web truyền tay, API thì không.
    so_lan_thu={"ltt_voice.synthesize": SO_LAN_THU_JOB,
                "ltt_voice.enroll": SO_LAN_THU_JOB},

    credit_cost=_gia,
    #: Trang gia cong khai `/gia-api` doc HAM NAY qua registry, khong
    #: import app nay theo ten. Xem `AppManifest.bang_gia`.
    bang_gia=gia.bang_gia,

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

    # 🔴 HAI TRẦN, KHAI RA CHO CHẨN ĐOÁN VẬN HÀNH.
    #
    #    Ngày 05/09/2026 bản deploy đứng ở một commit cũ hơn kho 94 lượt, nên
    #    trần công khai **đang chạy** là 1.500 trong khi mã nguồn ghi 100.000.
    #    Không ai phát hiện, vì không có chỗ nào hỏi được máy chủ *"hợp đồng mày
    #    đang thi hành là gì"*. `/health/version` nay trả lời được.
    #
    # ⛔ THAM CHIẾU HẰNG SỐ, KHÔNG GÕ LẠI SỐ. Một bản chép ở đây sẽ trôi — và nó
    #    trôi ngay bên trong công cụ dựng ra để phát hiện trôi, tức nó sẽ xác
    #    nhận trạng thái sai một cách rất thuyết phục.
    #
    # ⚠️ Chỉ những thứ ĐÃ công khai ở nơi khác: cả hai con số này đã in trên màn
    #    Studio và màn API cho mọi khách đọc. `/health/version` không có xác
    #    thực, nên đây không phải chỗ cho bất cứ thứ gì khác.
    hop_dong_cong_khai={
        "tran_ky_tu_cong_khai": TRAN_KY_TU_CONG_KHAI,
        "tran_moi_luot_sinh": TRAN_MOI_LUOT_SINH,
    },
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

    # Sức khoẻ cho catalog của sản phẩm khác (H43 Phase 06): hỏi sidecar THẬT
    # qua `trang_thai()` ba trạng thái — không phải `san_sang()` (chỉ kiểm biến
    # môi trường; đã hiện chip xanh trên một trang mọi lượt đều hỏng, 02/09).
    suc_khoe=lambda: ("san_sang" if sidecar_client.trang_thai() == "san_sang"
                      else "chua_san_sang"),

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
                #
                # 🔴 `exclusive_with`: gửi kèm `preset` là một yêu cầu hai nguồn
                #    giọng — không có câu trả lời đúng. `features.chuan_hoa` đã từ
                #    chối nó, NHƯNG chỉ ở worker: qua Public API lượt gọi đã được
                #    báo giá, giữ credit và xếp job trước khi hỏng (dù có hoàn).
                #    Khai ở đây để nền tảng từ chối NGAY tại `/quotes` — trước
                #    khi tiền động (`invocation.validate_public_input`). Cùng
                #    khuôn `depends_on`/`_check_model_constraints`: app khai bằng
                #    dữ liệu, nền tảng cưỡng chế chung, không route nào chép lại.
                "voice_id": {"type": "string", "required": False,
                             "max_length": 40,
                             "exclusive_with": ("preset",)},
                "preset": {"type": "string", "required": False,
                           "max_length": 64},
            },
            returns={"audio_key": "audio", "text": "text"},

            # 🔴 MỘT GPU = MỘT VIỆC, và cả ba cửa (job/sync/stream) phải giành
            #    cùng một slot. Không khai thì cửa đồng bộ đi vòng qua hàng đợi
            #    và hai lượt cùng đập vào một card (Q114).
            admission_resource="vieneu_gpu",
            admission_slots=1,

            # D007 (RC1 2026-09-11): tu choi loi so huu/lech lan NGAY tai
            # /quotes va /jobs, truoc khi tien dong -- cung cong
            # `features.chuan_hoa` + `features.giai_giong` ma web/worker dang
            # dung, khong phai mot ban kiem rieng cho Public API.
            kiem_truoc="apps.ltt_voice.kiem_truoc_api:kiem",

            # Giọng nhân bản CỦA NGƯỜI DÙNG cho palette/sản phẩm khác, không
            # import app này (H43 Phase 02). Gợi ý cho giao diện; sở hữu vẫn do
            # `features.giai_giong` kiểm lúc thi hành.
            tuy_chon_dong={
                "voice_id": "apps.ltt_voice.tham_chieu:tuy_chon_voice_id",
                # ⭐ Kho DUNG CHUNG. Khong co dong nay thi mot tai khoan chua
                #    nhan ban giong nao khong thay MOT lua chon nao ca — do la
                #    trang thai cua gan nhu moi khach moi.
                "preset": "apps.ltt_voice.tham_chieu:tuy_chon_preset",
            },

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
                    # 🔴 MÔ TẢ CŨ BẮT NGƯỜI TÍCH HỢP LÀM HỘ TA MỘT VIỆC TA ĐÃ
                    #    TỰ LÀM. Nó viết *"longer scripts should be split into
                    #    several calls"* — tức mỗi khách hàng phải tự viết lại
                    #    phép chia đoạn theo ranh giới câu, phép ghép, phép đo
                    #    nhịp nghỉ và phép cân mức. Bốn thứ đó nằm sẵn trong
                    #    `text_pipeline` và `noi_dai`, đã được đo, và không có
                    #    lý do gì để mỗi tích hợp có một bản riêng kém hơn.
                    #
                    # ⭐ Trần nay là NGÂN SÁCH TÀI NGUYÊN, không phải chỗ giọng
                    #    bắt đầu trôi — xem `tham_so_cong_khai.py`. Nên mô tả
                    #    phải nói đúng điều đó, và nói cả đường đi khi vượt.
                    "text": {
                        "description": (
                            "What to say. Vietnamese, English, or both mixed. "
                            f"Up to {TRAN_KY_TU_CONG_KHAI:,} characters per "
                            "call. You do NOT need to split long text yourself "
                            "- it is segmented on sentence boundaries, spoken "
                            "in several passes and joined back into one "
                            "continuous audio file. For anything longer, use "
                            "Projects, where each block is its own pass."),
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

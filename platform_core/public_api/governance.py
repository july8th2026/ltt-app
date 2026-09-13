"""Every store that holds customer data, how long it keeps it, and why.

The problem with retention rules that live in constants
-------------------------------------------------------

This platform already ages out job events, request logs and notifications. Each
rule lived next to the code that wrote the rows, which is the right place for
the rule and the wrong place for the *policy*: nobody could answer "what do we
hold about a customer, and for how long" without reading five modules and
hoping there was not a sixth.

There was a sixth. ``api_security_events`` shipped in EXT-16 with a
``purge_expired()`` that nothing ever called — a retention function nobody runs
is a comment, and the table would have grown forever.

So the classes are declared here, in one place, and a **ratchet test** fails when
a table appears without one. Forgetting becomes visible instead of silent.

The classes, and what they mean
-------------------------------

``EVIDENCE``
    Money and permission. Ledger entries, admin actions, pricing versions,
    developer keys. **Never deleted** — not by retention, not by an account
    closing. A refund dispute six months later is answered from these rows, and
    an audit that can be aged out is not an audit.

``OPERATIONAL``
    Useful while fresh, worthless when stale: request logs, job events,
    security events, cost observations, notifications. Aged out on a schedule.

``CONTENT``
    What the customer actually sent and received — uploads and artifacts. The
    largest by far, and the most sensitive. Lifecycle belongs to the storage
    layer and the upload sweeper, not to a row count here.

``DERIVED``
    Rebuildable from the others: the system dossier, generated docs, Postman.
    Losing them costs a command, not a fact.

What is deliberately *not* here
-------------------------------

Legal text. The site already has a privacy policy, terms and a data-deletion
page, and this module links to them rather than restating them — a second copy
of a legal promise is a second promise, and the two will differ.
"""
from __future__ import annotations

from dataclasses import dataclass

from platform_core.i18n import N_, _ as _t

EVIDENCE = "evidence"
OPERATIONAL = "operational"
CONTENT = "content"
DERIVED = "derived"
CLASSES = (EVIDENCE, OPERATIONAL, CONTENT, DERIVED)

#: Where the legal wording lives. Links, never copies (see the module docstring).
LEGAL_LINKS = {
    "privacy": "https://lttstudios.com/privacy-policy/",
    "terms": "https://lttstudios.com/terms/",
    "data_deletion": "https://lttstudios.com/data-deletion/",
}


@dataclass(frozen=True)
class Store:
    """One place customer data lives, and the promise made about it."""

    table: str
    klass: str
    #: ``None`` means "kept for as long as the account exists".
    retention_days: int | None
    #: Who can read it. Written for a person answering a privacy question.
    readable_by: str
    #: Why it is kept at all. A store nobody can justify is one to delete.
    reason: str
    #: How rows leave. Empty when nothing removes them, which is a claim the
    #: ratchet test checks rather than takes on trust.
    purged_by: str = ""


#: Every table that holds something about a customer. Ordered by class so the
#: page reads as a policy rather than a schema dump.
STORES: tuple = (
    # ── Evidence: never aged out ─────────────────────────────────────────────
    Store("credit_entries", EVIDENCE, None, N_("chủ tài khoản + vận hành"),
          N_("Sổ credit là chân lý thanh toán. Một tranh chấp hoàn tiền sáu tháng "
          "sau được trả lời từ đây.")),
    Store("nhat_ky_admin", EVIDENCE, None, N_("vận hành"),
          N_("Ai đã làm gì với tài khoản của khách. Một nhật ký kiểm toán xoá "
          "được thì không phải nhật ký kiểm toán.")),
    Store("api_pricing_versions", EVIDENCE, None, N_("vận hành + công khai"),
          N_("Chế độ giá nào đang có hiệu lực lúc một khoản tiền được tính.")),
    Store("developer_api_keys", EVIDENCE, None, N_("chủ tài khoản + vận hành"),
          N_("Khoá đã thu hồi vẫn giữ lại: nó là bằng chứng ai đã tiêu cái gì. "
          "Chỉ giữ dấu vân tay một chiều, không giữ bí mật.")),
    Store("api_projects", EVIDENCE, None, N_("chủ tài khoản + vận hành"),
          N_("Lưu trữ (archive) chứ không xoá — job và bút toán trỏ về nó.")),
    Store("payment_orders", EVIDENCE, None, N_("chủ tài khoản + vận hành"),
          N_("Chứng từ thanh toán: khách trả bao nhiêu, lúc nào, qua cổng nào. "
          "Đây là phía đối ứng của sổ credit — mất nó thì không đối soát được "
          "tiền thật với credit đã cấp.")),

    # ── Máy chủ ảo (H39) ─────────────────────────────────────────────────────
    #
    # ⚠️ PHÂN LOẠI TẠM, CHỦ H39 PHẢI XÁC NHẬN. Năm bảng này đến từ một hạng mục
    #    đang xây (`apps/vps`, app còn TẮT vì `LTT_VPS` chưa đặt), nên chưa có
    #    dòng dữ liệu thật nào. Nhưng bánh cóc `test_211` đòi **mọi** bảng phải
    #    được xếp loại, và để đỏ thì hai phiên đều tưởng là việc của bên kia.
    #
    #    Xếp theo đúng thứ docstring của chính các bảng đó nói, và nghiêng về
    #    phía **GIỮ** — vì hướng sai của việc này là xoá mất thứ khách sẽ hỏi,
    #    không phải giữ thừa một bảng chưa có dữ liệu.
    #
    # ⛔ Đặt hạn xoá cho `vps_ip` là việc CÓ HỆ QUẢ PHÁP LÝ: lịch sử "IP nào,
    #    của ai, lúc nào" là thứ duy nhất trả lời được một yêu cầu về lạm dụng.
    #    Đừng rút ngắn nó vì thấy bảng to.
    Store("vps_instance", EVIDENCE, None, N_("chủ tài khoản + vận hành"),
          N_("Máy khách đã thuê: gói, đĩa, hệ điều hành, vmid. Đây là phía đối "
          "ứng của hoá đơn — mất nó thì không đối soát được khách trả tiền cho "
          "cái gì.")),
    Store("vps_ip", EVIDENCE, None, N_("chủ tài khoản + vận hành"),
          N_("Địa chỉ IP đã cấp cho máy nào, từ lúc nào. Là thứ duy nhất trả lời "
          "được một yêu cầu về lạm dụng từ bên ngoài.")),
    Store("vps_event", EVIDENCE, None, N_("chủ tài khoản + vận hành"),
          N_("Nhật ký vòng đời một máy — thứ trả lời \"vì sao máy tôi bị tắt\". "
             "Chính bảng này ghi rằng nó tồn tại vì log xoay vòng rồi mất, còn câu "
             "hỏi của khách thì đến sau ba tháng.")),
    Store("vps_external_mutation", EVIDENCE, None, N_("vận hành"),
          N_("Ý định, đối chiếu và bù trừ cho từng thay đổi tài nguyên hạ tầng "
             "của máy khách. Mất nhật ký này thì không thể phân biệt thao tác đã "
             "thành công, cần thử lại hay cần con người xử lý.")),
    # `vps_thao_tac` là **OPERATIONAL, có hạn xoá** — khác hẳn `vps_event` ngay
    # trên nó, và khác biệt ấy là cả lý do hai bảng tồn tại riêng.
    #
    #   `vps_event` = **đã xảy ra rồi**. Nó là bằng chứng, không bao giờ xoá.
    #   `vps_thao_tac` = **đang xảy ra**. Nó có hạn chót, có UPID để nối lại,
    #     và nó KẾT THÚC. Một hàng đợi không dọn được là một hàng đợi phình mãi.
    #
    # 180 ngày, không phải 30: một thao tác hỏng là thứ khách hỏi lại sau vài
    # tháng ("hồi tháng trước bấm khởi động lại mà máy không lên"), và câu trả
    # lời nằm ở `ma_loi` của chính hàng này. Ngắn hơn thì ta xoá mất câu trả lời
    # trước khi câu hỏi tới.
    #
    # ⚠️ KHÔNG chứa bí mật: `upid` là mã tác vụ của Proxmox, `chi_tiet_loi` là
    #    thông điệp lỗi. Cả hai chỉ tới người vận hành — `suc_khoe.dong_thoi_gian`
    #    lọc chúng ra trước khi bất cứ thứ gì tới trang của khách.
    Store("vps_thao_tac", OPERATIONAL, 180, N_("chủ tài khoản + vận hành"),
          N_("Một thao tác dài đang chạy trên một máy: ai yêu cầu, muốn gì, tới "
          "đâu rồi, hỏng vì sao. Khác nhật ký vòng đời ở chỗ nó KẾT THÚC."),
          "thao_tac.don_cu (bao tri VPS)"),

    # ── LTT VOICE ────────────────────────────────────────────────────────────
    #
    # ⛔ BỐN BẢNG NÀY GIỮ THỨ NHẠY CẢM NHẤT TRONG CẢ NỀN TẢNG: **giọng nói của
    #    một con người thật**. Giọng là đặc điểm nhận dạng sinh trắc — nó không
    #    cùng hạng với một prompt hay một tấm ảnh sản phẩm.
    #
    # 🔴 Vì sao cả bốn đều EVIDENCE (không tự già đi), kể cả bảng nghe như
    #    "chỉ là kỹ thuật":
    #
    #    Nếu một ngày có tranh chấp *"ai cho phép các anh dùng giọng tôi"*, câu
    #    trả lời phải ghép được **ba** thứ và mất một thứ là mất cả câu trả lời:
    #    hồ sơ giọng (ai sở hữu), tệp nguồn (giọng nào), và bản cam kết (đồng ý
    #    lúc nào, với bản điều khoản nào). Đặt hạn xoá cho bất kỳ cái nào trong
    #    ba là tự bỏ khả năng tự bảo vệ.
    #
    # ⚠️ Đây KHÔNG phải lý do để giữ mãi mãi bất chấp. Khách xoá tài khoản thì cả
    #    bốn đi cùng tài khoản — `retention_days=None` nghĩa là *"giữ chừng nào
    #    tài khoản còn"*, không phải *"giữ vĩnh viễn"*.
    Store("voice_profile", EVIDENCE, None, N_("chủ tài khoản + vận hành"),
          N_("Danh tính công khai của một giọng: ai sở hữu, tên hiển thị, còn "
          "dùng được không. Là phía đối ứng của mọi lượt sinh tiếng đã tính "
          "tiền — mất nó thì lịch sử hoá đơn trỏ vào hư không.")),
    Store("voice_ref", EVIDENCE, None, N_("chủ tài khoản + vận hành"),
          N_("Clip mẫu GỐC khách tải lên, giữ nguyên không xử lý. Hai việc: dựng "
          "lại giọng khi nâng cấp model, và chứng minh giọng nhân bản đến từ "
          "đúng tệp mà khách đã cam kết là của họ.")),
    Store("voice_repr", EVIDENCE, None, N_("vận hành"),
          N_("Biểu diễn engine của một giọng, gắn với một phiên bản model cụ "
          "thể. KHÔNG BAO GIỜ ra API. Giữ lại để đối chiếu một tệp tiếng cũ với "
          "đúng bản model đã sinh ra nó.")),
    Store("voice_consent", EVIDENCE, None, N_("chủ tài khoản + vận hành"),
          N_("Cam kết sở hữu giọng: ai, lúc nào, bản điều khoản nào, hash tệp "
          "nào. Đây là bảng duy nhất trả lời được câu hỏi pháp lý, và nó là lý "
          "do consent phải là DỮ LIỆU chứ không phải một ô tick.")),
    # ⚠️ `nguoi_soat` giữ id của NGƯỜI VẬN HÀNH đã ra phán quyết, không phải của
    #    khách. Nhưng bảng vẫn xếp loại như bốn bảng trên, và có chủ ý: nó gắn
    #    một-một với `voice_profile`, và `ly_do_loai` nói vì sao một giọng biến
    #    mất — tức nó là nửa còn lại của câu trả lời cho khách hỏi *"giọng của
    #    tôi đâu"*. Xếp nó là "không phải dữ liệu khách" sẽ đúng về cột và sai
    #    về câu hỏi.
    Store("voice_quality_profile", EVIDENCE, None, N_("chủ tài khoản + vận hành"),
          N_("Phán quyết curate một giọng và LÝ DO LOẠI khi loại. Giữ chừng nào "
          "giọng còn: ngày nâng engine, một giọng loại vì rè đáng thử lại, một "
          "giọng loại vì thiếu consent thì không — cùng trạng thái, hai số phận.")),

    # ── Dự án và Chạy lô: bản thảo của khách, không phải kết quả một job ─────
    #
    # ⭐ Vì sao `retention_days=None` chứ không phải 30 như `jobs`: một dự án là
    #    thứ khách SOẠN — họ mở lại, sửa, đọc lại từng khối trong nhiều tuần.
    #    Cho nó hết hạn theo lịch là xoá bản thảo của người ta trong khi họ vẫn
    #    đang dùng. Nó đi khi khách xoá dự án, hoặc khi tài khoản đi.
    #
    # 🔴 HỆ QUẢ ĐÃ BIẾT, CHƯA SỬA. `voice_block.audio_key` trỏ vào tệp nằm trong
    #    vùng của một JOB, và job là CONTENT/30 ngày — nên sau 30 ngày
    #    `job_content.purge_expired` xoá tệp trong khi khối vẫn quảng cáo là có
    #    tiếng. Khách mở dự án cũ và thấy một trình phát 404. Không ai dính điều
    #    này hôm nay (tính năng chưa tới khách nào), nhưng nó có hạn: đúng 30
    #    ngày sau lượt đọc đầu tiên của khách đầu tiên. Ghi ở đây chứ không giấu
    #    trong một dòng TODO, vì đây là chỗ người ta sẽ đọc khi hỏi "dữ liệu này
    #    sống bao lâu".
    Store("voice_project", CONTENT, None, N_("chủ tài khoản"),
          N_("Một kịch bản dài hoặc một lô đang soạn: tên, giọng mặc định, "
          "trạng thái. Bản thảo của khách, không phải sản phẩm của một job.")),
    Store("voice_block", CONTENT, None, N_("chủ tài khoản"),
          N_("Từng khối/dòng trong một dự án: văn bản khách gõ, giọng đã chọn, "
          "và khoá tệp tiếng đã sinh. Văn bản là nội dung của khách; khoá tệp "
          "chỉ là con trỏ — tệp thật sống theo hạn của job sinh ra nó.")),

    # ⚠️ `retention_days=None` ở đây KHÔNG phải "giữ mãi bất chấp" mà là "sống
    #    theo vòng đời tài khoản" — cùng nghĩa với `voice_project`.
    #
    #    Và ở bảng này nó là một RÀNG BUỘC ĐÚNG chứ không phải một sự tiện tay:
    #    hết hạn từ điển sau N ngày nghĩa là một hôm nào đó tên riêng của khách
    #    **đọc khác đi** mà không ai báo, trên chính những kịch bản họ đã đọc
    #    đúng hàng trăm lần. Một thay đổi im lặng trong thứ khách nghe được.
    Store("voice_tu_dien", CONTENT, None, N_("chủ tài khoản"),
          N_("Từ điển phát âm riêng của khách: từ nào đọc thành gì. Do khách "
          "tự soạn cho tên công ty, tên nhân vật, tên sản phẩm — những thứ "
          "engine không đoán được. Áp cho MỌI lượt đọc của họ, kể cả khi gọi "
          "qua API, nên nó quyết định thứ khách nghe được.")),

    # ⭐ `retention_days=None` vì đây là trạng thái NGƯỜI DÙNG áp lên lịch sử —
    #    sống theo vòng đời tài khoản, đi khi tài khoản đi. KHÔNG có sweeper
    #    riêng, nên không có nghĩa vụ `purged_by` (khác các bảng CONTENT có hạn).
    # ⛔ Nó KHÔNG giữ nội dung — chỉ hai mốc "đã tải" / "đã xoá" trên một job.
    #    Xoá ở đây dọn TỆP qua `job_content.expire_content` (vòng đời của `jobs`),
    #    còn dòng này chỉ là dấu người dùng đặt lên, nên xếp cạnh các bảng lịch
    #    sử khác của khách chứ không phải EVIDENCE (mất nó không mất bằng chứng).
    Store("voice_lich_su", CONTENT, None, N_("chủ tài khoản"),
          N_("Dấu người dùng đặt lên một lượt lịch sử: đã tải về chưa, đã xoá "
          "chưa. Không chứa văn bản hay tệp — chỉ hai cột thời điểm. Xoá một lượt "
          "dọn TỆP theo vòng đời của job; dòng này chỉ ghi rằng khách đã xoá.")),

    # ── Operational: aged out on a schedule ──────────────────────────────────
    Store("public_api_requests", OPERATIONAL, 30, N_("chủ tài khoản + vận hành"),
          N_("Gỡ lỗi một tích hợp. Không chứa payload, chỉ metadata."),
          "request_log.purge_expired (worker)"),
    Store("job_events", OPERATIONAL, 365, N_("chủ tài khoản (dòng customer)"),
          N_("Dòng thời gian một job. Dòng nội bộ chỉ giữ 30 ngày."),
          "job_events.purge_expired (worker)"),
    Store("execution_leases", OPERATIONAL, 1, N_("vận hành"),
          N_("Quyền giữ slot thực thi tạm thời; chỉ giữ định danh vận hành để "
             "chẩn đoán và tự thu hồi tiến trình đã chết."),
          "admission.reclaim_expired (admission + worker)"),
    # 30 ngày chứ không 1 như `execution_leases`: bảng này còn là SỔ TỪNG LƯỢT
    # để phân tích sau khi mở vận hành (thời gian chờ, lý do nghẽn, whale) — chủ
    # dự án yêu cầu 11/09. Không chứa prompt/payload.
    Store("llm_waiters", OPERATIONAL, 30, N_("vận hành"),
          N_("Phòng chờ của cửa tương tác tới model nhà và sổ từng lượt: chờ bao "
             "lâu, vì sao, ngân sách token đặt chỗ. Không chứa nội dung hội thoại."),
          "phong_cho.don_het_han (worker)"),
    Store("api_notifications", OPERATIONAL, 90, N_("chủ tài khoản"),
          N_("Cảnh báo đã đọc rồi thì hết giá trị."),
          "notifications.purge_expired (worker)"),
    Store("api_security_events", OPERATIONAL, 90, N_("vận hành"),
          N_("Ai đang dò khoá. Chỉ lưu nửa CÔNG KHAI của khoá đã thử."),
          "security_log.purge_expired (worker)"),
    Store("api_metric_samples", OPERATIONAL, 14, N_("vận hành"),
          N_("Bộ đếm của từng tiến trình theo phút, để cộng lại khi đọc."),
          "metrics.purge_expired (worker)"),
    Store("api_cost_observations", OPERATIONAL, 400, N_("vận hành"),
          N_("Chi phí ƯỚC TÍNH để tính biên lợi nhuận. Không phải sổ sách."),
          "costing.purge_expired (worker)"),
    Store("public_api_webhook_deliveries", OPERATIONAL, 30, N_("chủ tài khoản"),
          N_("Đã gửi callback chưa, và bên nhận trả lời gì."),
          "outbox.purge_expired (worker)"),
    Store("public_api_idempotency", OPERATIONAL, 7, N_("không ai (nội bộ)"),
          N_("Chống tính tiền hai lần trong cửa sổ thử lại."),
          "idempotency.purge_expired (worker)"),
    Store("sessions", OPERATIONAL, 30, N_("không ai (nội bộ)"),
          N_("Phiên đăng nhập web. Lưu SHA-256 của token, không lưu token."),
          "auth sweeper"),
    # Vé sống 60 giây, và bị XOÁ ngay khi tiêu — không phải đánh dấu đã dùng.
    # Vẫn khai ở đây vì nó có `user_id`: một bảng "gần như luôn rỗng" vẫn là một
    # bảng có dữ liệu của khách, và ngoại lệ không viết ra là ngoại lệ không ai
    # rà lại.
    Store("vps_console_ve", OPERATIONAL, 1, N_("không ai (nội bộ)"),
          N_("Vé mở console máy ảo. Lưu SHA-256 của vé, không lưu vé. Hết hạn "
          "sau 60 giây và bị xoá ngay khi dùng."),
          "console.don_ve_het_han (bao_tri cua app)"),

    # ── Content: the customer's own material ─────────────────────────────────
    Store("upload_sessions", CONTENT, 7, N_("chủ tài khoản"),
          N_("Vé tải lên chưa dùng. Bytes ở staging bị quét dọn cùng lúc."),
          "upload_sessions.sweep (worker)"),
    Store("jobs", CONTENT, 30, N_("chủ tài khoản"),
          N_("`params`, `result` và file sinh ra là nội dung của chính khách, "
          "hết hạn sau 30 ngày. Hàng job thì Ở LẠI vĩnh viễn vì bút toán "
          "credit trỏ về nó — bằng chứng và nội dung là hai thứ khác nhau."),
          "job_content.purge_expired (worker)"),
    # ── Nexus: danh tính thiết bị và phiên điều khiển (Q93) ──────────────────
    #
    # Vì sao `nexus_sessions` là EVIDENCE chứ không phải OPERATIONAL: sau một sự
    # cố, câu hỏi duy nhất quan trọng là "ai đã vào máy tôi, lúc nào, từ đâu" —
    # và không ai hỏi nó trước khi cần. Một nhật ký phiên hết hạn sau 30 ngày sẽ
    # im lặng đúng lúc nó là thứ duy nhất trả lời được.
    Store("nexus_devices", EVIDENCE, None, N_("chủ tài khoản + vận hành"),
          N_("Máy nào đã từng được tin, ghép lúc nào, ai thu hồi. Thu hồi ghi "
          "`revoked_at` chứ không xoá dòng — xoá là xoá luôn câu trả lời. Chỉ "
          "giữ khoá CÔNG KHAI, không bao giờ có khoá riêng.")),
    Store("nexus_sessions", EVIDENCE, None, N_("chủ tài khoản + vận hành"),
          N_("Ai đã điều khiển máy nào, từ IP nào, bắt đầu và kết thúc lúc nào. "
          "Chỉ giữ dấu vân tay một chiều của vé, không giữ vé.")),
    Store("nexus_enrollments", OPERATIONAL, 365, N_("chủ tài khoản + vận hành"),
          N_("Mã ghép đã dùng là mẩu kiểm toán 'máy này ghép lúc nào, từ IP "
          "nào'; mã hết hạn không ai dùng thì không kiểm toán gì và rụng sau "
          "30 ngày. Chỉ giữ digest, không giữ mã."),
          "devices.don_ma_het_han (worker)"),

    Store("users", CONTENT, None, N_("chủ tài khoản + vận hành"),
          N_("Email, mật khẩu đã băm, vai trò. Vô hiệu hoá (`is_active=False`) "
          "chứ không xoá — sổ credit và nhật ký trỏ về đây bằng khoá ngoại "
          "RESTRICT, và xoá được thì bằng chứng mất theo.")),
    Store("public_api_webhooks", CONTENT, None, N_("chủ tài khoản"),
          N_("Địa chỉ nhận callback + secret ký, **đã mã hoá**. Xoá khi khách xoá "
          "đăng ký.")),
    Store("api_budgets", CONTENT, None, N_("chủ tài khoản"),
          N_("Trần chi khách tự đặt. Chỉ QUAN SÁT, không đổi sổ credit.")),
    Store("app_projects", CONTENT, None, N_("chủ tài khoản"),
          N_("Dự án của các editor có trạng thái. Vòng đời do app quản.")),

    # Bảng do APP sở hữu. Tất cả là nội dung của khách, vòng đời đi theo app —
    # nền tảng cố ý không đặt hạn cho chúng: app biết khi nào một cảnh, một
    # workflow hay một cuộc trò chuyện hết ý nghĩa, nền tảng thì không.
    Store("agent_runs", CONTENT, None, N_("chủ tài khoản"),
          N_("Một lần chạy agent: đầu vào, các bước, kết quả.")),
    Store("agent_workflows", CONTENT, None, N_("chủ tài khoản"),
          N_("Sơ đồ các bước tự động do người dùng dựng trên canvas.")),
    Store("agent_workflow_snapshots", CONTENT, None, N_("chủ tài khoản"),
          N_("Bản chụp một workflow để người dùng quay lại phiên bản cũ.")),
    Store("agent_workflow_shares", CONTENT, None, N_("chủ tài khoản"),
          N_("Link chia sẻ riêng tư tới một workflow: ai cầm link thì xem được.")),
    Store("chat_conversations", CONTENT, None, N_("chủ tài khoản"),
          N_("Hội thoại người dùng.")),
    Store("chat_messages", CONTENT, None, N_("chủ tài khoản"),
          N_("Nội dung tin nhắn — thứ nhạy cảm nhất trong nhóm này.")),
    # ── ChatLTT (H43) ────────────────────────────────────────────────────────
    #
    # ⚠️ BA BẢNG RIÊNG, không phải `chat_*` ở trên. `chat_*` là của Chat AI
    #    Studio (hội thoại tuyến tính qua sidecar Codex); ChatLTT lưu một CÂY
    #    hội thoại trên model của nhà. Hai sản phẩm, hai lời hứa — gộp bảng là
    #    gộp cả chính sách giữ dữ liệu của chúng.
    #
    # 🔴 `chatltt_execution` giữ `partial_text`: **đúng những chữ model đã sinh
    #    ra cho khách**, kể cả lượt bị ngắt. Nó cùng hạng nhạy cảm với nội dung
    #    tin nhắn, không phải một bản ghi kỹ thuật — nên CONTENT, không
    #    OPERATIONAL, và không tự già đi.
    Store("chatltt_conversation", CONTENT, None, N_("chủ tài khoản"),
          N_("Hội thoại ChatLTT: tiêu đề, model đang chọn, nhánh đang xem. Xoá "
             "là xoá mềm — dọn thật theo hạn giữ dữ liệu."),
          purged_by=N_("xoá mềm rồi dọn theo hạn giữ dữ liệu")),
    Store("chatltt_message", CONTENT, None, N_("chủ tài khoản"),
          N_("Từng lượt nói trong cây hội thoại, kèm khối nội dung (chữ, suy "
             "luận, ảnh, tiếng). Thứ nhạy cảm nhất của sản phẩm này."),
          purged_by=N_("theo hội thoại chứa nó")),
    Store("chatltt_execution", CONTENT, None, N_("chủ tài khoản"),
          N_("Một lượt thi hành: phần chữ đã sinh (kể cả khi bị ngắt), số token "
             "đo được và số credit đã giữ/thu — thứ đối chiếu được với sổ tiền."),
          purged_by=N_("theo hội thoại chứa nó")),
    # ── ChatLTT V3 — điều phối tool (H44) ────────────────────────────────────
    #
    # 🔴 Cả ba đều CONTENT, kể cả `chatltt_run` vốn chỉ chứa số đếm.
    #
    #    Với `step` và `approval` thì hiển nhiên: `doi_so` là câu hỏi của khách
    #    đã được model viết lại thành tham số ("tìm bệnh viện gần Cầu Giấy"), và
    #    `ket_qua` giữ tới 8 KB thứ tool trả về. Đó là nội dung, không phải một
    #    bản ghi kỹ thuật.
    #
    # ⭐ `chatltt_run` mới là cái đáng nói. Nó **không** chứa chữ của ai, nên
    #    xếp OPERATIONAL nghe hợp lý — và sẽ sai. OPERATIONAL tự già đi theo
    #    hạn riêng, nghĩa là một ngày các `run` bị dọn trong khi hội thoại chứa
    #    chúng vẫn còn: người dùng mở lại một lượt cũ và thấy các bước đã biến
    #    mất khỏi một tin nhắn vẫn nguyên vẹn. Một hội thoại phải có **một** lời
    #    hứa giữ dữ liệu, không phải hai lời hứa lệch nhau bên trong nó.
    Store("chatltt_run", CONTENT, None, N_("chủ tài khoản"),
          N_("Một lượt có dùng công cụ: số vòng đã chạy, lý do dừng, và tổng "
             "credit đã giữ/thu/hoàn của cả lượt."),
          purged_by=N_("theo hội thoại chứa nó")),
    Store("chatltt_step", CONTENT, None, N_("chủ tài khoản"),
          N_("Từng bước trong một lượt: công cụ nào được gọi, với tham số gì, "
             "và nó trả về gì. Tham số bắt nguồn từ câu hỏi của người dùng."),
          purged_by=N_("theo hội thoại chứa nó")),
    Store("chatltt_approval", CONTENT, None, N_("chủ tài khoản"),
          N_("Lần người dùng bấm duyệt cho một công cụ tốn credit: tham số đã "
             "duyệt, báo giá lúc đó, và quyết định. Bằng chứng của một lần "
             "đồng ý tiêu tiền."),
          purged_by=N_("theo hội thoại chứa nó")),
    # ── ChatLTT V3 — tệp đính vào hội thoại (H44 P06) ───────────────────────
    #
    # ⭐ Bảng này **không chứa byte nào** — byte nằm ở `storage`, vé vào là
    #    `upload_sessions`. Nó chỉ nói *tệp nào thuộc hội thoại nào*.
    #
    # 🔴 Và chính vì thế nó là cái bẫy. "Chỉ siêu dữ liệu" nghe như OPERATIONAL,
    #    nhưng OPERATIONAL **tự già đi**: một ngày liên kết bị dọn trong khi hội
    #    thoại và tệp đều còn, và người dùng thấy tài liệu mình đã đính biến mất
    #    khỏi một cuộc trò chuyện vẫn nguyên vẹn. Đây là lần **thứ ba** cùng ca
    #    ấy — P03 với `chatltt_run`, P06 §7 khi bác `Job.params` (vì `jobs` LÀ
    #    OPERATIONAL), và bây giờ.
    Store("chatltt_tep", CONTENT, None, N_("chủ tài khoản"),
          N_("Tài liệu người dùng đính vào một hội thoại để hỏi: tên tệp, kiểu, "
             "cỡ, và trạng thái trích văn bản. Nội dung tệp nằm ở kho lưu trữ, "
             "không nằm ở đây."),
          purged_by=N_("theo hội thoại chứa nó")),
    # ⚠️ Bảng dưới thì NGƯỢC LẠI: nó **giữ chữ của khách**. Đó là chủ đích, không
    #    phải rò rỉ — chỉ số tìm kiếm phải chạy trên chính chữ ấy. Nhưng nó làm
    #    bảng này thành thứ nhạy cảm nhất trong nhóm: nội dung tài liệu riêng
    #    của khách, đã tách nhỏ và đánh chỉ số để tìm được.
    Store("chatltt_doan", CONTENT, None, N_("chủ tài khoản"),
          N_("Văn bản đã trích từ tài liệu người dùng đính vào hội thoại, cắt "
             "thành từng đoạn kèm số trang để trích dẫn lại được. Đây là nội "
             "dung tài liệu của khách, không phải bản ghi kỹ thuật."),
          purged_by=N_("theo tệp và hội thoại chứa nó")),
    # ⚠️ H44 B4. CONTENT, và ở đây lời phân loại còn rõ hơn hai bảng trên: đây
    #    là những điều người dùng **cố ý dạy** cho hệ thống về chính họ. Một mẩu
    #    bị dọn mất nghĩa là máy quên một điều họ đã dặn — và họ sẽ không biết
    #    nó đã quên cho tới lúc câu trả lời sai.
    #
    # 🔴 Đây cũng là bảng `chatltt_*` **duy nhất không gắn với một hội thoại**:
    #    mẩu phạm vi `nguoi_dung` sống lâu hơn mọi hội thoại đã sinh ra nó. Nên
    #    `purged_by` của nó là **tài khoản**, không phải hội thoại — chép câu
    #    của bảng bên cạnh vào đây sẽ để lại một kho ghi nhớ mồ côi sau khi
    #    người dùng xoá hết hội thoại.
    Store("chatltt_ghi_nho", CONTENT, None, N_("chủ tài khoản"),
          N_("Những điều người dùng dặn hệ thống nhớ về mình (hoặc để trợ lý tự "
             "ghi lại), kèm phạm vi áp dụng: toàn tài khoản, một dự án, hay một "
             "hội thoại. Người dùng xem, sửa và xoá được từng mẩu."),
          purged_by=N_("theo tài khoản; mẩu thuộc phạm vi hội thoại thì theo "
                       "hội thoại chứa nó")),
    Store("ommi_resource", CONTENT, None, N_("chủ tài khoản"),
          N_("Tài nguyên (ảnh, tệp) người dùng tải lên PROMPT AI OMMI.")),
    Store("ommi_resource_variant", CONTENT, None, N_("chủ tài khoản"),
          N_("Biến thể (crop, upscale, đổi tỉ lệ) sinh ra từ một tài nguyên gốc.")),
    Store("ommi_resource_tag", CONTENT, None, N_("chủ tài khoản"),
          N_("Nhãn người dùng gắn lên một tài nguyên cụ thể.")),
    Store("ommi_resource_usage", CONTENT, None, N_("chủ tài khoản"),
          N_("Ghi nhận tài nguyên nào đã dùng ở cảnh nào, để tra ngược.")),
    Store("ommi_tag", CONTENT, None, N_("chủ tài khoản"), N_("Tên nhãn do người dùng tự đặt để sắp xếp tài nguyên.")),
    Store("ommi_style", CONTENT, None, N_("chủ tài khoản"), N_("Style người dùng lưu lại để tái dùng giữa các cảnh.")),
    Store("ommi_collection", CONTENT, None, N_("chủ tài khoản"), N_("Nhóm tài nguyên người dùng tự gom lại.")),
    Store("ommi_collection_item", CONTENT, None, N_("chủ tài khoản"),
          N_("Liên kết một tài nguyên vào một bộ sưu tập.")),
    Store("ommi_meta_prompt", CONTENT, None, N_("chủ tài khoản"),
          N_("Meta-prompt người dùng viết để sinh ra prompt khác.")),
    Store("ommi_prompt_snippet", CONTENT, None, N_("chủ tài khoản"),
          N_("Mẩu prompt người dùng lưu để chèn lại nhiều nơi.")),
    Store("ommi_prompt_version", CONTENT, None, N_("chủ tài khoản"),
          N_("Một phiên bản của prompt, giữ lại để so sánh và quay lui.")),
    Store("ommi_storyboard", CONTENT, None, N_("chủ tài khoản"), N_("Kịch bản hình của người dùng: khung sườn của một video.")),
    Store("ommi_scene", CONTENT, None, N_("chủ tài khoản"), N_("Một cảnh trong storyboard, kèm prompt và tham số của nó.")),
    Store("ommi_scene_version", CONTENT, None, N_("chủ tài khoản"),
          N_("Phiên bản một cảnh, kèm góp ý của người dùng.")),

    # ── Auto Scan Video ──────────────────────────────────────────────────────
    #
    # Cả ba đều là CONTENT, không phải EVIDENCE, và ranh giới đó đã có sẵn lời
    # giải thích ở mục `jobs` phía trên: *bằng chứng và nội dung là hai thứ khác
    # nhau*. Tiền của một lần chạy nằm ở `credit_entries` (EVIDENCE, giữ mãi);
    # ba bảng này chỉ giữ **tài liệu của khách** và trỏ tới tệp của họ.
    #
    # 🔑 Hạn 30 ngày KHỚP CỐ Ý với hạn của `jobs`, và đó là điều đáng nói nhất ở
    #    đây. LTT VOICE đã trả giá cho việc lệch: `voice_block.audio_key` sống
    #    mãi cùng dự án còn tệp nó trỏ tới sống 30 ngày theo `jobs`, nên sau 30
    #    ngày khách mở dự án cũ và thấy một trình phát 404 **không kèm lời giải
    #    thích nào**. Một hàng dữ liệu sống lâu hơn tệp nó trỏ tới không phải là
    #    "giữ được nhiều hơn" — nó là một lời hứa hỏng.
    Store("asv_run", CONTENT, 30, N_("chủ tài khoản"),
          N_("Một lần lồng tiếng: video nguồn của khách, ngôn ngữ, giọng đã "
          "chọn. Hết hạn cùng lúc với tệp mà nó trỏ tới."),
          "job_content.purge_expired (worker)"),
    Store("asv_stage", CONTENT, 30, N_("chủ tài khoản"),
          N_("Trạng thái từng giai đoạn và khoá kết quả của nó. Chứa bản chép "
          "lời và bản dịch — tức chính lời nói trong video của khách."),
          "job_content.purge_expired (worker)"),
    Store("asv_asset", CONTENT, 30, N_("chủ tài khoản"),
          N_("Sổ tài nguyên đã sinh ra: khoá lưu trữ, vân tay, và nó bắt nguồn "
          "từ tài nguyên nào. Không giữ bytes, chỉ giữ đường tới chúng."),
          "job_content.purge_expired (worker)"),
    Store("asv_work_item", CONTENT, 30, N_("chủ tài khoản"),
          N_("Checkpoint từng đoạn bên trong một giai đoạn: đoạn nào đã đọc "
          "thành tiếng, tốn bao nhiêu, thử mấy lần. Cùng hạn với giai đoạn "
          "chứa nó — một checkpoint sống lâu hơn kết quả nó trỏ tới là một "
          "lời hứa hỏng."),
          "job_content.purge_expired (worker)"),
    Store("asv_usage", CONTENT, 30, N_("chủ tài khoản"),
          N_("Sổ cái từng lượt gọi năng lực: năng lực nào đã chạy, đo bằng đơn "
          "vị gì, hết bao nhiêu credit. Đây là thứ trả lời câu hỏi \"tôi trả "
          "cho cái gì\" — nên nó phải sống đúng bằng lần chạy mà nó giải "
          "thích, không lâu hơn."),
          "job_content.purge_expired (worker)"),

    # ── Derived: rebuildable ─────────────────────────────────────────────────
    Store("sdk/postman/*", DERIVED, None, N_("công khai"),
          N_("Sinh từ OpenAPI.")),

    # ── LTT WORKFLOW V2 ──────────────────────────────────────────────────────
    #
    # ⭐ Ranh giới giữa ba lớp ở đây là một quyết định về TIỀN và về VIỆC CỦA
    #    KHÁCH, không phải về dung lượng:
    #
    #      EVIDENCE   trả lời được "vì sao khách bị trừ ngần ấy" sau sáu tháng
    #      CONTENT    thứ khách TẠO RA — xoá là mất việc của họ
    #      DERIVED    dựng lại được từ hai loại trên
    Store("workflow_run", EVIDENCE, None, N_("chủ tài khoản + vận hành"),
          N_("Một lượt chạy đã tính tiền. `actual_cost` và `hold_id` ở đây là "
             "câu trả lời cho một tranh chấp hoàn tiền sáu tháng sau.")),
    Store("node_run_snapshot", EVIDENCE, None, N_("chủ tài khoản + vận hành"),
          N_("Chuỗi ảnh chụp BẤT BIẾN của từng bước, kèm chi phí theo từng lượt "
             "thử. Xoá nó là mất khả năng nói VÌ SAO một lượt chạy tốn ngần ấy "
             "— kể cả lần chuyển bị từ chối cũng nằm ở đây.")),
    Store("workflow", CONTENT, None, N_("chủ tài khoản"),
          N_("Workflow là thứ khách DỰNG RA. Việc của họ, không phải dấu vết "
             "vận hành của ta.")),
    Store("workflow_draft", CONTENT, None, N_("chủ tài khoản"),
          N_("Bản đang soạn — mất nó là mất phần khách đang gõ dở.")),
    Store("workflow_version", CONTENT, None, N_("chủ tài khoản"),
          N_("Bản đã xuất bản, BẤT BIẾN. Một lượt chạy ghim vào đây, nên xoá nó "
             "là làm một lượt chạy đã tính tiền không còn tái dựng được.")),
    Store("workflow_trigger", CONTENT, None, N_("chủ tài khoản"),
          N_("Cấu hình khách đặt để workflow tự chạy.")),
    Store("artifact", CONTENT, None, N_("chủ tài khoản"),
          N_("Siêu dữ liệu tệp khách tạo ra. KHÔNG chứa byte nào; vòng đời thật "
             "do `ttl_class` quyết, và backend có lifecycle riêng thì ta không "
             "tự xoá."),
          "platform_core.workflow.artifact.het_han"),
    Store("node_run", DERIVED, None, N_("chủ tài khoản + vận hành"),
          N_("CON TRỎ tới ảnh chụp mới nhất — dựng lại được từ chuỗi ảnh chụp.")),
    Store("workflow_version_node", DERIVED, None, N_("chủ tài khoản"),
          N_("Chỉ mục dẫn xuất từ đồ thị của bản đã xuất bản.")),
    Store("workflow_version_edge", DERIVED, None, N_("chủ tài khoản"),
          N_("Chỉ mục dẫn xuất từ đồ thị của bản đã xuất bản.")),
    Store("waitpoint", DERIVED, None, N_("chủ tài khoản + vận hành"),
          N_("Trạng thái chờ trong một lượt chạy; chỉ có nghĩa khi lượt chạy "
             "còn sống.")),
    Store("waitpoint_signal", DERIVED, None, N_("chủ tài khoản + vận hành"),
          N_("Tín hiệu từng nhánh gửi tới một điểm chờ.")),
    Store("node_run_waitpoint", DERIVED, None, N_("chủ tài khoản + vận hành"),
          N_("Bảng nối nhiều-nhiều: waitpoint nào đang chặn node nào.")),
    Store("foreach_vong", DERIVED, None, N_("chủ tài khoản + vận hành"),
          N_("Một vòng ForEach đang chạy.")),
    Store("foreach_muc", DERIVED, None, N_("chủ tài khoản + vận hành"),
          N_("Kết quả từng phần tử của một vòng ForEach — thứ nói CHÍNH XÁC còn "
             "phải chạy gì sau một lần chết.")),
)


def translated(store: "Store") -> dict:
    """One row as the privacy page shows it, in the reader's language.

    Resolved here rather than in the template so there is one place that knows
    which fields are prose and which are identifiers — a table name is not
    translated, and translating it would break the only thing that lets a
    customer match this page against their export.
    """
    return {"table": store.table, "klass": store.klass,
            "retention_days": store.retention_days,
            "readable_by": _t(store.readable_by), "reason": _t(store.reason)}


def by_class(klass: str) -> tuple:
    return tuple(store for store in STORES if store.klass == klass)


def store_for(table: str) -> Store | None:
    for store in STORES:
        if store.table == table:
            return store
    return None


#: Tables that hold nothing about a customer, so they need no class. Listed
#: explicitly: "it is not customer data" is a claim worth writing down, because
#: the next person will assume the omission was an oversight.
NOT_CUSTOMER_DATA = frozenset({
    "alembic_version", "platform_info", "api_keys", "api_policies",
    "api_policy_assignments", "api_kill_switches", "app_access",
    "credit_packages", "gpu_leases",
    # Ai đang giữ vai trò chạy việc nền. Máy + pid, không có gì của khách.
    "singleton_leases",
    # Node hạ tầng của CHÍNH TA: IP công khai của gateway, bridge, subnet, dải
    # cổng. Không có `user_id` và không có gì của khách — máy của khách nằm ở
    # `vps_instance`, và bảng đó đã được xếp loại ở trên.
    "vps_gateway",
    # Cấu hình và phép đo sức khoẻ hạ tầng của chính nền tảng. Chúng không chứa
    # user_id hay nội dung khách; quan hệ với máy khách nằm ở vps_instance và
    # nhật ký mutation đã được xếp EVIDENCE ở trên.
    "vps_infrastructure_profile", "vps_profile_health",
    # Một lời hẹn giờ của scheduler: `run_id` + `kind` + `due_at`. Không có gì
    # của khách ở đây — nội dung lượt chạy nằm ở `workflow_run`, và bảng đó ĐÃ
    # được xếp loại.
    "wakeup",
    # Model nào đang cư trú trên một nhóm GPU của MÁY TA (D01 B). Cùng loại với
    # `gpu_leases` ở trên: tên nhóm + trạng thái + mốc thời gian, không `user_id`
    # và không nội dung nào của khách.
    #
    # Và không có hạn lưu trữ vì không có dòng nào để hết hạn: đúng **một** dòng
    # mỗi nhóm, ghi đè tại chỗ. Xếp nó OPERATIONAL sẽ buộc khai một hàm dọn, và
    # lời khai ấy sẽ trỏ vào một hàm không có việc gì làm — tức đúng thứ
    # `test_211` sinh ra để chặn.
    "gpu_residency",
})


def unclassified(tables) -> list:
    """Tables the inventory does not mention. The ratchet's whole job.

    A new table that holds customer data and slips in unlisted is exactly how a
    platform ends up unable to answer "what do you keep about me" — and the
    honest answer to that question is not one anybody wants to improvise.
    """
    known = {store.table for store in STORES} | set(NOT_CUSTOMER_DATA)
    return sorted(name for name in tables if name not in known)


__all__ = ["CLASSES", "CONTENT", "DERIVED", "EVIDENCE", "LEGAL_LINKS",
           "NOT_CUSTOMER_DATA", "OPERATIONAL", "STORES", "Store", "by_class",
           "store_for", "translated", "unclassified"]

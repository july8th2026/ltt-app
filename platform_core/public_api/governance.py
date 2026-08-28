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

    # ── Derived: rebuildable ─────────────────────────────────────────────────
    Store("ho_so_he_thong.txt", DERIVED, None, N_("nội bộ"),
          N_("Bản đồ mã nguồn, sinh lại được bằng một lệnh.")),
    Store("sdk/postman/*", DERIVED, None, N_("công khai"),
          N_("Sinh từ OpenAPI.")),
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

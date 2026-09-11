"""
registry.py — hợp đồng giữa nền tảng và từng app. Đây là file quan trọng nhất.

Nền tảng KHÔNG được biết tên app nào tồn tại. Nó quét `apps/*/manifest.py`,
đọc `MANIFEST`, rồi tự dựng trang chủ, gắn route, và phân job cho worker.

Vì sao phải làm vậy: nếu tên app nằm rải rác trong code nền tảng (trang chủ,
sidebar, bảng giá, phân job) thì thêm app thứ 10 là sửa 10 chỗ và chắc chắn
quên một chỗ. Với registry, thêm app = thêm một folder.

Thêm app mới cần đúng 3 việc:
    1. tạo `apps/<slug>/manifest.py` có biến MANIFEST
    2. tạo `apps/<slug>/routes.py` có biến `router` (APIRouter)
    3. xong. Không sửa file nào của nền tảng.

Bố cục bên trong một app (chuẩn từ 2026-08-06):

    manifest.py   bản khai — nền tảng chỉ đọc file này
    routes.py     CHỈ lo HTTP: đọc request, kiểm quyền/CSRF, gọi service, dựng
                  phản hồi. Không chứa quy tắc nghiệp vụ.
    jobs.py       handler chạy trong worker
    services/     quy tắc nghiệp vụ khi app có nhiều miền
    features.py   quy tắc nghiệp vụ khi app chỉ có một miền
    tables.py     bảng CSDL riêng (kèm `table_prefix` trong manifest)

Vì sao ghi rõ: trước đây hợp đồng không nói logic nghiệp vụ nằm ở đâu, nên
route thành chỗ mọi thứ rơi vào — hai file route đã vượt 1.300 dòng. Không có
chỗ mặc định thì mỗi người chọn một kiểu, và đó là điều đã xảy ra.
`tools/lint_app_contract.py` cảnh báo khi `routes.py` vượt ngưỡng.

⚠️ **Không còn app mẫu để copy.** `apps/demo/` — app khuôn tối thiểu — đã bị gỡ
2026-08-25 (Q109). Khuôn đầy đủ nằm trong `docs/03_THEM_APP_MOI.md`; muốn xem một
app THẬT nhỏ gọn thì đọc `apps/anhnoibo/` (chỉ job, không route) hoặc
`apps/thumbnail/` (có route + template).
"""
from __future__ import annotations

import importlib
import logging
import pathlib
import re
from dataclasses import dataclass, field
from typing import Callable, Optional

from platform_core.i18n import _ as _t

log = logging.getLogger(__name__)

APPS_DIR = pathlib.Path(__file__).resolve().parent.parent / "apps"

# ⭐ `json[]` THÊM 2026-08-23, và nó bịt một lỗ đã làm hỏng một tool thật.
#
#    Trước đó bảng này chỉ có `json`, và `json` phơi ra công khai là `object` —
#    rồi `invocation._validate_value` đòi một `dict`. Nghĩa là **không có cách
#    nào khai một tham số là MẢNG JSON.**
#
#    Hậu quả không hề trừu tượng: `text.chat` khai `messages` là `json`, và
#    `POST /api/v1/jobs` **từ chối mọi input hợp lệ** của nó — kể cả đúng ví dụ
#    mà trang tài liệu in ra. Cửa job của tool đó không dùng được kể từ lúc dựng,
#    và không có lỗi nào báo cho tới khi `test_199` đối chiếu ví dụ với bộ kiểm.
#
# ⛔ Đừng "sửa" bằng cách cho `object` nhận cả list: nó nới lỏng bộ kiểm cho MỌI
#    tool khác để chiều một tool. Thiếu từ vựng thì thêm từ vựng.
TOOL_PARAM_TYPES = frozenset({
    "string", "int", "number", "bool", "enum", "model_ref",
    "text", "image", "image[]", "video", "video[]", "audio", "json", "json[]",
})
#: Kiểu media mà ffprobe đọc được thời lượng. `image` không nằm đây — một tấm
#: ảnh không có thời lượng, và khai như thế là một lỗi hợp đồng chứ không phải
#: một phép đo trả 0.
MEASURABLE_TYPES = frozenset({"video", "audio"})
TOOL_PORT_TYPES = frozenset({
    "text", "image", "image[]", "video", "video[]", "audio", "json", "json[]",
    "model_ref",
})
APP_SURFACES = frozenset({"customer", "admin", "runtime"})
APP_LIFECYCLES = frozenset({
    "released", "development", "maintenance", "internal", "retired",
})
_TOOL_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
_PROMPT_SOURCE_RE = re.compile(r"^prompts/[a-zA-Z0-9_-]+$")
#: Tham chiếu `module:attribute` do app sở hữu (`sync_executor`, `tuy_chon_dong`).
_THAM_CHIEU_RE = re.compile(r"^[A-Za-z_][\w.]*:[A-Za-z_]\w*$")


def tai_tham_chieu(reference: str):
    """Resolve một tham chiếu `module:attribute` khai trong manifest.

    Chỉ import **khi được gọi** — không phải lúc `discover()` — để một tiến
    trình worker/CLI nạp registry không kéo mã của app vào bộ nhớ. Cùng cách
    `public_api.executor._load` đã làm cho `sync_executor`.
    """
    import importlib

    module_name, separator, attribute = str(reference or "").partition(":")
    if not separator or not module_name or not attribute:
        raise RegistryError(f"tham chieu phai la module:attribute, nhan {reference!r}")
    return getattr(importlib.import_module(module_name), attribute)


@dataclass(frozen=True)
class AdmissionModel:
    """Sức chứa admission của MỘT model trong một tool (multijob 2.1).

    Vì sao tách khỏi `ToolSpec.admission_resource/slots/token_pool`: bộ ba đó
    tả được đúng MỘT pool cho cả tool, còn `text.chat` sắp phục vụ hai model
    (`ltt-3.8`, `ltt-3.5`) trên hai pool KV khác nhau của CÙNG một tool. Khoá
    `"*"` trong `ToolSpec.admission_theo_model` nghĩa là "áp cho mọi model của
    tool" — dùng cho tool không phân biệt theo model (vd Task 5.5, ảnh trên
    3090: `{"*": AdmissionModel("anh_3090", 1, 0, "rtx3090", "theo_lo")}`).
    """
    #: Tên tài nguyên dùng chung phải giành trước khi chạm provider.
    resource: str
    #: Số lượt thực thi đồng thời tài nguyên trên cho phép.
    slots: int
    #: Ngân sách token KV dùng chung. 0 = không áp ngân sách.
    token_pool: int = 0
    #: Nhóm cư trú GPU để trọng tài residency (vd "rtx3090"). Rỗng = không
    #: trọng tài — chưa có tool nào dùng tới field này ở 2.1, nhưng nó là một
    #: phần của hợp đồng đã chốt (Task 5.5 sẽ dùng), không phải suy đoán.
    residency_group: str = ""
    #: "mac_dinh" | "theo_lo" | "" — vai trò của model trong nhóm cư trú.
    vai_tro: str = ""


@dataclass(frozen=True)
class ToolSpec:
    """Metadata tất định để Agent/Canvas gọi một job đã tồn tại.

    ToolSpec không chứa handler và không tạo runtime mới. ``params_schema`` và
    ``returns`` được sao chép/resolve trước khi đưa ra API; manifest chỉ giữ bản
    khai immutable ở cấp đối tượng.
    """

    name: str
    job_type: str
    description: str
    params_schema: dict
    returns: dict
    verifiable: tuple = ()
    # False = giữ runtime/schema để workflow cũ chạy, nhưng không mời khách
    # tạo node mới từ palette. Đây là soft-retire, không phải xoá capability.
    customer_visible: bool = True

    # ── Public API (Q92) ─────────────────────────────────────────────────────
    # MẶC ĐỊNH TẮT. `customer_visible` nói về palette của Agent trong giao diện
    # LTT; nó KHÔNG phải cờ public. Một tool chỉ ra `/api/v1` khi app tự khai
    # `api_exposed=True` VÀ hợp đồng công khai đủ (xem `api_contract`) VÀ operator
    # bật nó trong `LTT_PUBLIC_API_TOOLS`. Ba cổng độc lập: quên một cái thì hậu
    # quả là thiếu tính năng, không phải lộ năng lực nội bộ.
    api_exposed: bool = False

    # Hợp đồng công khai của tool. Rỗng khi `api_exposed=False`.
    #
    #   api_contract={
    #       "public_name": "<domain>.<action>",   # mặc định là `name`
    #       "description": "câu mô tả cho khách",  # mặc định là `description`
    #       "models": {"standard": "<model id nội bộ>"},   # alias → id thật
    #       "enums": {"text_style": ["bold", "clean"]},    # giá trị công khai
    #       "hidden": ("ngon_ngu",),              # tham số server tự quyết
    #       "scopes": ("jobs:create",),           # scope cần để gọi
    #       "deprecated": "",                     # thông điệp/ngày sunset
    #   }
    #
    # Vì sao phải có: `params_schema` nội bộ chứa `model_ref` (kèm tên provider
    # và id model thật) và `enum` lấy giá trị từ `prompts/...` — bê nguyên ra
    # ngoài là lộ nhà cung cấp và thư viện prompt nội bộ. Không khai đủ thì
    # registry TỪ CHỐI expose, chứ không im lặng publish một hợp đồng rò rỉ.
    # `description` cũng vậy: mô tả nội bộ hay nêu thẳng tên nhà cung cấp, nên
    # tool public phải viết lại một câu cho khách.
    api_contract: dict = field(default_factory=dict)

    # Tài nguyên thực thi dùng chung mà tool phải giành trước khi chạm provider.
    # Rỗng = dùng lớp tài nguyên của manifest. Tên do app khai; nền tảng không
    # suy từ slug/model/host, vì các tên đó đổi độc lập với năng lực thật.
    admission_resource: str = ""
    # Số lượt thực thi đồng thời mà tài nguyên trên cho phép. 0 = admission
    # không cấp execution lease (giữ tương thích tool hiện có).
    admission_slots: int = 0
    # Ngân sách token KV dùng chung của tài nguyên trên (llama.cpp `-kvu`).
    # 0 = không áp ngân sách token — mọi tool khác giữ nguyên hành vi. >0 thì
    # admission đặt chỗ `prompt + max_tokens + đệm` và chỉ nhận khi còn vừa
    # (multijob, `platform_core/llm/luat_nhan.py`).
    admission_token_pool: int = 0

    # ── Admission THEO MODEL (multijob 2.1) ─────────────────────────────────
    #
    # `{model_id | "*": AdmissionModel(...)}`. Rỗng (mặc định) = tool dùng ba
    # trường tĩnh ở trên — KHÔNG tool nào hiện có phải đổi để giữ hành vi cũ
    # (`admission_cho()` tự rơi về nhánh tương thích, xem bên dưới).
    #
    # 🔴 VÌ SAO CẦN. `text.chat` sắp phục vụ `ltt-3.8` VÀ `ltt-3.5` — hai model
    #    trên hai pool KV khác nhau của CÙNG một tool (`docs/.../ltt-llm-dual-
    #    model`). `admission_resource/slots/token_pool` tĩnh chỉ tả được MỘT
    #    pool; tool cần một ánh xạ theo model, không phải ba con số dùng chung.
    #
    # ⭐ Khoá `"*"` = áp cho MỌI model của tool (Task 5.5: ảnh trên 3090 khai
    #    `{"*": AdmissionModel("anh_3090", 1, 0, "rtx3090", "theo_lo")}` — tool
    #    đó không phân biệt sức chứa theo model).
    admission_theo_model: dict = field(default_factory=dict)

    # Optional adapter for protocol routes that must execute synchronously.
    # This is a dotted reference owned by the app; the platform resolves it
    # without knowing an app slug or importing app code directly.
    sync_executor: str = ""

    # ── Tuỳ chọn ĐỘNG theo người dùng (H43 Phase 02, 2026-09-02) ───────────
    #
    #   tuy_chon_dong={"voice_id": "apps.myapp.kho:tuy_chon_voice_id"}
    #
    # `module:callable(db, user_id) -> [{"value": ..., "label": ...}]`. Cùng
    # khuôn "tham chiếu dotted do app sở hữu, nền tảng resolve lúc CẦN, không
    # import lúc nạp" của `sync_executor` ở trên.
    #
    # 🔴 VÌ SAO CẦN. Ba cơ chế enum động đang có (`model_ref`, `source`,
    #    `depends_on`) đều thuần tiến trình — không cái nào biết NGƯỜI DÙNG là
    #    ai. Nên "giọng nhân bản của chính tôi" không có cách nào lên palette
    #    Agent hay một sản phẩm web khác mà không import `apps.ltt_voice` — thứ
    #    `test_147`/`test_308` cấm, và cấm đúng.
    #
    # ⚠️ Chỉ cho tham số kiểu `string`, và danh sách này là **gợi ý cho giao
    #    diện**, không phải phép kiểm: app vẫn kiểm sở hữu lúc thi hành (đường
    #    duy nhất chặn được một id đoán mò). Nền tảng không được biết giá trị
    #    nào là "của ai" — nó chỉ chuyển câu hỏi cho app.
    tuy_chon_dong: dict = field(default_factory=dict)

    # ── Làn scheduler theo tham số ──────────────────────────────────────────
    #
    # `job_type` ở trên là làn MẶC ĐỊNH. Một app có thể có nhiều làn cho cùng
    # một tool khi chi phí máy khác nhau hẳn theo một tham số công khai — làn
    # quyết định VRAM mà scheduler giữ chỗ (`gpu_vram_mb`), nên chọn sai làn là
    # giữ thừa GPU chứ không phải một chi tiết nội bộ.
    #
    # 🔴 VÌ SAO NÓ TỒN TẠI, đo được 2026-08-29. `apps/upscalevideo` khai ba làn
    #    (`render` 12.000 MB, `render.fast` 2.000, `render.quality` 12.000) và
    #    đường WEB chọn đúng làn theo preset. Đường API thì dùng thẳng
    #    `tool.job_type` — tức **mọi** job từ API xin 12.000 MB kể cả
    #    `preset=fast`, trong khi fast đo thật chỉ ăn 848 MB. Trên một máy có ba
    #    hộ dùng chung GPU, đó là khách trả tiền rồi nằm chờ một chỗ trống mà
    #    job của họ không hề cần.
    #
    # ⭐ KHAI BẰNG DỮ LIỆU chứ không phải một hàm, khác `sync_executor` ở trên
    #    và khác có chủ ý: một bảng ánh xạ thì registry **kiểm được lúc nạp**
    #    (tham số có thật không, làn có trong `job_types` không, đã phủ hết giá
    #    trị enum chưa). Một hàm thì không kiểm được gì cho tới khi nó chạy —
    #    và chỗ nó chạy là chỗ tiêu tiền của khách.
    #
    #: Tên tham số quyết định làn. Rỗng = luôn dùng `job_type`.
    job_type_by: str = ""
    #: `giá trị tham số -> job_type`. Phải phủ HẾT giá trị enum của tham số đó.
    job_type_lanes: dict = field(default_factory=dict)

    # ═══ HỢP ĐỒNG NODE V2 (`25_26 §2`) ═══════════════════════════════════════
    #
    # Sáu trường, tất cả CÓ MẶC ĐỊNH ⇒ **không app nào phải sửa để lên V2**.
    # Đó là ràng buộc thiết kế, không phải may mắn: `02 §3` chốt rằng V2 mở
    # rộng `ToolSpec` chứ không dựng một registry thứ hai, vì dự án này đã trả
    # giá nhiều lần cho mô hình hai nguồn chân lý.

    #: Tăng khi `params_schema`/`returns` đổi KHÔNG tương thích.
    #
    # 🔴 Lỗ hổng IM LẶNG (`G05`): node ghim `tool.name` nhưng **không** ghim
    #    version. Đổi `params_schema` của một tool ⇒ mọi `workflow_version` đã
    #    xuất bản trỏ tới nó **đổi ý nghĩa** mà không lỗi nào báo.
    #    Activepieces ghim `pieceName` **+** `pieceVersion` ngay trong node, và
    #    họ có 10.077 connector — quy mô mà quên ghim version là thảm hoạ.
    type_version: int = 1

    #: `"none"` | `"external"` | `"irreversible"` — chỗ neo của mô hình bảo đảm.
    #
    # ⭐ Ba giá trị là BA HÀNH VI KHÔI PHỤC khác nhau khi một attempt thành
    #    `ABANDONED` (provider **có thể** đã nhận việc):
    #
    #      none          thuần tính toán      -> thử lại tự do
    #      external      gọi provider          -> thử lại SAU KHI kiểm bằng
    #                                             `idempotency.key_fields`
    #      irreversible  gửi mail, tạo VPS     -> ⛔ KHÔNG BAO GIỜ tự thử lại
    #
    # 🔴 Đo được là cần: `AmbiguousProviderError` xảy ra **10 lần / 28 ngày**
    #    (`01 §A.4`), và `mark_ambiguous()` hôm nay xử lý **mọi job như nhau**.
    #    `vps.provision` (đã tạo máy thật, tính tiền thật) và `image.generate`
    #    (tốn một lượt gọi) không cùng loại rủi ro, nhưng đang cùng đường xử lý.
    side_effect: str = "external"

    #: `{"key_fields": ("prompt", "model", "seed")}` — khoá khử trùng TẤT ĐỊNH.
    #
    # Nền tảng dựng `dedupe_key` từ trường app chỉ định, thay vì băm TOÀN BỘ
    # params: một `request_id`/`callback_ts` lọt vào khoá làm khử trùng **không
    # bao giờ khớp**. Và nó sửa luôn `G31` — `_cached_result()` hôm nay so
    # params bằng nhau tuyệt đối rồi quét 50 job, nên một tool có `seed` ngẫu
    # nhiên nằm ngoài params sẽ **trả lại kết quả cũ cho khách**.
    idempotency: dict = field(default_factory=dict)

    #: Chạy thử workflow mà không chạm bước đắt tiền. `(params) -> returns`.
    #
    # 🔴 ĐIỀU KIỆN CẦN, không phải tiện nghi. `F4`: một node có thể là **20
    #    phút A100**. Không có `mock`, khách muốn thử workflow 8 bước phải đốt
    #    tám lượt GPU — và **ta** cũng không kiểm được `M6`/`M7` (chaos,
    #    ForEach 100 phần tử) mà không đốt tiền thật.
    mock_result: Optional[Callable[[dict], dict]] = None

    #: `{"class", "vram_min_mb", "slots", "est_duration_s"}` — gom bốn thứ đang
    #: rải rác ở `AppManifest` (`gpu_vram_mb`/`max_runtime_s`/`cho_tai_nguyen_s`
    #: /`so_lan_thu`), tất cả khoá theo `job_type` và tách rời khỏi `ToolSpec`
    #: khai ra job đó.
    #
    # ⭐ `est_duration_s` là trường MỚI, phục vụ `WF-202`: scheduler không xếp
    #    một việc 20 phút vào chỗ vừa nhả ra bởi một việc 5 giây. LTT đã có số
    #    đo cho đúng vấn đề này (job 5 giây mất **75 % thông lượng** vì hằng số
    #    20 giây) nhưng chỉ dùng nó cho **giãn cách thử lại**, không dùng để
    #    **xếp chỗ** (`G28`).
    resource: dict = field(default_factory=dict)

    #: Trần thời gian theo THAM SỐ, vd `"duration_s * 30 + 120"`. Rỗng ⇒ dùng
    #: `resource`/mặc định của manifest.
    #
    # Video 5 giây và video 60 giây đang chung một `max_runtime_s` tĩnh ⇒ hoặc
    # trần quá rộng (job treo giữ slot), hoặc quá chặt (job dài bị giết oan).
    #
    # ⚠️ `Q5`: tập toán tử CỐ ĐỊNH trên chính `params` của node — không đọc kết
    #    quả bước khác, không gọi hàm ngoài. Nó phải tính được **lúc validate**
    #    vì `WF-501` cần trần chi phí TRƯỚC khi chạy. Cưỡng chế ở
    #    `platform_core/workflow/bieu_thuc.py`, và bộ tính ở đó **không dùng
    #    `eval`** — nó duyệt AST rồi tự tính từng nút.
    timeout_expr: str = ""

    def lane_for(self, params: dict) -> str:
        """`job_type` thật cho một lượt gọi, theo tham số app đã khai.

        Không khai gì thì trả `job_type` — hành vi cũ, không đổi.
        """
        if not self.job_type_by:
            return self.job_type
        gia_tri = (params or {}).get(self.job_type_by)
        if gia_tri is None:
            spec = (self.params_schema or {}).get(self.job_type_by) or {}
            gia_tri = spec.get("default")
        return (self.job_type_lanes or {}).get(gia_tri, self.job_type)

    def admission_cho(self, model: str = "") -> "AdmissionModel | None":
        """Sức chứa admission cho một model cụ thể (multijob 2.1).

        Ba nhánh, fail-closed:

        1. Có `admission_theo_model`: khớp đúng `model` thì trả nó; không thì
           rơi về `"*"` nếu tool có khai; không có cả hai ⇒ `KeyError` — một
           model lạ không được âm thầm chạy KHÔNG có admission (tức không
           giành lease, không áp ngân sách token) trên một tool đã chủ động
           phân biệt theo model.
        2. Không có `admission_theo_model` nhưng có `admission_resource` +
           `admission_slots > 0`: tool cũ trước 2.1 — trả `AdmissionModel`
           tương đương, không phân biệt `model`. Hành vi giữ NGUYÊN.
        3. Không khai gì: tool không giành lease nào ⇒ `None`.
        """
        m = self.admission_theo_model
        if m:
            if model in m:
                return m[model]
            if "*" in m:
                return m["*"]
            raise KeyError(
                f"{self.name}: model {model!r} khong co trong admission_theo_model")
        if self.admission_resource and self.admission_slots > 0:
            return AdmissionModel(self.admission_resource, self.admission_slots,
                                  int(getattr(self, "admission_token_pool", 0) or 0))
        return None


@dataclass(frozen=True)
class NavEntry:
    """Một dòng trong sidebar của app."""
    label: str
    path: str
    icon: str = ""
    nav_key: str = ""          # để template biết dòng nào đang active
    built: bool = True         # False -> hiện nhãn "đang xây", không ẩn đi


@dataclass(frozen=True)
class AppManifest:
    """Bản khai của một app. Nền tảng chỉ đọc, không sửa.

    `slug` là khoá duy nhất và cũng là tên folder. `route_prefix` là đường dẫn
    dưới app.lttstudios.com — mỗi app một prefix riêng để không bao giờ đụng
    nhau.
    """

    slug: str
    display_name: str
    route_prefix: str
    summary: str = ""
    icon: str = "📦"
    accent: str = "#1565C0"

    # Sidebar. App đơn giản để trống, nền tảng tự tạo 1 dòng từ route_prefix.
    nav: tuple = ()

    # Loại job app này sinh ra, ví dụ ("seedance.t2v", "seedance.i2v").
    # Worker khai báo mình làm được loại nào; hàng đợi khớp theo đây.
    job_types: tuple = ()

    # Worker cần năng lực gì để chạy job của app này:
    #   "api"     - chỉ gọi API bên ngoài, chạy ở đâu cũng được
    #   "ffmpeg"  - cần ffmpeg cục bộ
    #   "gpu"     - cần VRAM
    #   "browser" - cần trình duyệt + IP dân dụng (bot đăng bài)
    # Phải có annotation kiểu, nếu không dataclass coi đây là biến lớp chứ
    # không phải field và constructor sẽ từ chối tham số `requires=`.
    requires: tuple = ("api",)

    # Hàm tính credit. Là HÀM chứ không phải số, vì giá phụ thuộc tham số
    # (Seedance tính theo giây video × độ phân giải, không tính theo lần gọi).
    # Nhận dict tham số job, trả về số credit. None = app chưa thu phí.
    credit_cost: Optional[Callable[[dict], int]] = None

    # True khi app đã chạy được thật. False -> trang chủ hiện nhãn "đang xây"
    # thay vì để người dùng bấm vào rồi gặp lỗi.
    enabled: bool = True

    # Hiện trong CATALOG CÔNG KHAI (khách chưa đăng nhập) không? (Q30/H6)
    #   True  - sản phẩm self-serve, hiện cho khách duyệt.
    #   False - app nội bộ/đặc cách (app test hạ tầng, app đóng băng cần OAuth) —
    #           ẩn khỏi trang chủ công khai, vẫn dùng được khi đã đăng nhập.
    # App tự khai qua cờ này; nền tảng KHÔNG hardcode tên app (test_60 chốt).
    public: bool = True

    # Bề mặt sản phẩm (Q69-Q72), độc lập với `enabled` và `public`.
    # customer: catalog/nav khách hàng; admin: chỉ operator; runtime: không có
    # bề mặt độc lập nhưng route/job/tool vẫn được mount để giữ tương thích.
    surface: str = "customer"

    # Vòng đời hiển thị (Q73), không dùng badge marketing để giả trạng thái.
    lifecycle: str = "development"

    # Taxonomy năng lực hiển thị trong Marketplace (Q74). Một app có thể nằm
    # trong nhiều nhóm; nền tảng chỉ đọc dữ liệu này, tuyệt đối không suy luận
    # từ slug/tên app. Phần tử đầu tiên là nhóm chính để chọn ảnh cover.
    capabilities: tuple = ()

    # 🔴 HẰNG SỐ HỢP ĐỒNG mà app muốn khai ra cho chẩn đoán vận hành.
    #
    #    Sinh ra 05/09/2026 từ một sự cố cụ thể: bản deploy đứng ở một commit cũ
    #    hơn kho 94 lượt, nên trần ký tự công khai của `ltt_voice` **đang chạy**
    #    là 1.500 trong khi mã nguồn ghi 100.000. Không ai phát hiện ra, vì
    #    không có chỗ nào hỏi được máy chủ *"hợp đồng mày đang thi hành là gì"*.
    #
    # ⭐ VÌ SAO NÓ NẰM Ở BẢN KHAI CHỨ KHÔNG PHẢI Ở `server/routes/health.py`.
    #
    #    Bản vá đầu import thẳng `apps.ltt_voice.tham_so_cong_khai` vào
    #    `health.py`. `tests/test_147_layering.py` đỏ ngay, và nó đúng:
    #    *"Nền tảng KHÔNG được biết tên app nào tồn tại."* Một endpoint chẩn
    #    đoán biết tên một app là một endpoint sẽ phải sửa mỗi lần thêm app —
    #    tức chính cái ràng buộc mà hợp đồng app sinh ra để gỡ.
    #
    # ⇒ App **khai**; nền tảng **đọc**. Cùng khuôn với `doctor_muc` và
    #   `capabilities` ngay trên đây.
    #
    # ⚠️ Chỉ đặt vào đây thứ ĐÃ công khai ở nơi khác. `/health/version` không có
    #    xác thực (reverse proxy dựa vào điều đó), nên một khoá bí mật hay một
    #    đường dẫn nội bộ đặt ở đây là một lượt rò, không phải một lượt chẩn đoán.
    #
    # ⛔ Và nó phải là GIÁ TRỊ TĨNH đọc từ chính hằng số app đang dùng, không
    #    phải một bản chép gõ tay. Một bản chép ở đây sẽ trôi — ngay trong công
    #    cụ dựng ra để phát hiện trôi.
    hop_dong_cong_khai: dict = field(default_factory=dict)

    # App con vẫn giữ route/job/history riêng nhưng không tạo card/nav độc lập.
    # Dùng khi hai executor cùng nằm dưới một sản phẩm customer-facing, ví dụ
    # một mode chuyên biệt trong shell của app cha. Route cũ vẫn được mount để
    # deep link và workflow cũ không gãy.
    catalog_parent: str = ""

    # Tiêu đề các mục kiểm tra (doctor) THUỘC app này (H6.6). Nền tảng dùng để
    # gắn badge "cần thiết lập" lên ĐÚNG thẻ app, thay vì treo một banner blocker
    # toàn cục ở trang chủ (mô hình cũ thời desktop-app). App tự khai danh sách
    # tiêu đề của mình → nền tảng khớp báo cáo doctor với app mà KHÔNG hardcode
    # tên app. Rỗng = app không có mục kiểm tra riêng.
    blocker_titles: tuple = ()

    # ── Việc nền định kỳ của app ─────────────────────────────────────────────
    #
    # `bao_tri` là một callable không tham số mà nền tảng gọi mỗi
    # `bao_tri_moi_giay` giây, TRONG vòng bảo trì của worker — tức **dưới lease**
    # `bao_tri`. Nhờ đó nó chạy đúng một lần trên toàn cụm dù có bao nhiêu tiến
    # trình worker.
    #
    # Vì sao phải nằm trong hợp đồng, thay vì app tự dựng vòng lặp riêng:
    # số tiến trình worker mặc định bằng số GPU (H36). Một app tự chạy vòng thu
    # tiền sẽ **trừ tiền khách N lần mỗi chu kỳ**, và không lỗi nào được ghi ra —
    # sổ credit vẫn cân, chỉ là khách bị trừ nhiều lần. Đúng lớp lỗi mà
    # `platform_core/leases.py` sinh ra để chặn.
    #
    # Trước 2026-08-24 hợp đồng KHÔNG có chỗ này, và hậu quả có thật: app `vps`
    # viết xong `billing.thu_phi_dinh_ky` kèm test, nhưng **không nơi nào gọi nó**
    # — máy hết hạn không bị treo, không bị xoá, IP không được trả. Một chính sách
    # có hàm mà không ai chạy đọc lên như một lời hứa (EXT-19).
    #
    # Hàm này KHÔNG được ném. Nền tảng bắt và ghi log, nhưng một app ném mỗi lượt
    # là một dòng log rác mỗi giờ, và nó che những lỗi thật.
    bao_tri: Optional[Callable[[], None]] = None
    #: Giãn cách giữa hai lượt `bao_tri`. Mặc định một giờ — đủ dày cho chu kỳ
    #: tính bằng ngày, đủ thưa để không thành tải nền.
    bao_tri_moi_giay: int = 3600

    #: Bảng giá CÔNG BỐ của app, cho trang giá công khai `/gia-api`.
    #:
    #: 🔴 VÌ SAO Ở ĐÂY chứ không để trang giá tự `import apps.<tên>`.
    #:
    #:    Trước 2026-09-02 `server/routes/dashboard.py` import thẳng
    #:    `apps.anhnoibo.gia` và `apps.ltt_voice.gia`. Hợp đồng app khai chiều
    #:    `app → server` (`SERVER_APP_CO_THE_DUNG`) và cả chiều `app → app`
    #:    (`APP_DUOC_DUNG_APP`), nhưng **không khai chiều `server → app`** —
    #:    nên nền tảng biết tên hai app cụ thể mà không hợp đồng nào nói tới.
    #:
    #: ⭐ Và việc import ấy KHÔNG phải cẩu thả: nó là lựa chọn có cân nhắc, để
    #:    tránh gõ lại số vào template — chính hai `bang_gia()` kia đã cảnh báo
    #:    rằng gõ lại là tạo "bảng giá thứ hai", và hai bảng lệch nhau thì bảng
    #:    nào cũng không đáng tin.
    #:
    #: ⇒ Nên cách sửa không phải bỏ lời gọi, mà là **bổ sung vào hợp đồng** thứ
    #:   nó đang thiếu (`CLAUDE.md`: *"buộc phải sửa nền tảng… là dấu hiệu hợp
    #:   đồng app còn thiếu, phải bổ sung vào hợp đồng chứ không đi vòng"*).
    #:   App vẫn sở hữu giá của mình; nền tảng chỉ còn **thu thập**.
    #:
    #: ⚠️ Hàm này KHÔNG được ném — cùng luật với `bao_tri`. Một app hỏng bảng
    #:    giá không được làm sập trang giá của mọi app khác.
    bang_gia: Optional[Callable[[], dict]] = None

    #: Sức khoẻ **của năng lực** app cung cấp, cho catalog của sản phẩm khác
    #: (H43 Phase 06, 2026-09-03). Callable không tham số, trả MỘT trong:
    #:     "san_sang" · "ban" · "chua_san_sang"
    #:
    #: 🔴 VÌ SAO CẦN. `apps/ltt_voice` từng hiện chip "Engine sẵn sàng" xanh trên
    #:    một trang mà mọi lượt tạo đều hỏng — vì chip đọc `san_sang()` (chỉ kiểm
    #:    biến môi trường có được đặt) chứ không hỏi sidecar. Một sản phẩm khác
    #:    (ChatLTT) muốn nói "giọng nói đang không sẵn sàng" thì chỉ có hai
    #:    đường: import `apps.ltt_voice` (cấm) hoặc app tự khai qua hợp đồng.
    #:
    #: ⚠️ Hàm này KHÔNG được ném và phải **nhanh** (thăm dò loopback/LAN với
    #:    timeout ngắn, ≤ 2 giây); nền tảng đệm kết quả vài giây. Không khai =
    #:    catalog chỉ biết `enabled`.
    suc_khoe: Optional[Callable[[], str]] = None

    # Ghi chú nội bộ, hiện trên trang chủ cho admin.
    notes: str = ""

    # Bố cục (UX Pha 2): nhóm hiển thị ở HEADER (dropdown theo nhóm) — vd "Ảnh",
    # "Video", "Đăng bài". App tự khai; nền tảng gom app theo `group`. Rỗng =
    # "Ứng dụng". Chỉ ảnh hưởng ĐIỀU HƯỚNG/hiển thị, không đụng logic app.
    group: str = "Ứng dụng"
    # Nhãn nhỏ trên thẻ catalog (vd "MỚI", "HOT", "PRO"). Rỗng = không hiện.
    badge: str = ""

    # Năng lực cho Agent/Canvas. Additive: app cũ không khai vẫn chạy nguyên.
    tools: tuple = ()

    # Tiền tố bảng CSDL của app. App nào cần bảng thật — không vừa trong
    # `AppProject` JSON — thì đặt model ở `apps/<slug>/tables.py` và khai tiền
    # tố ở đây; mọi `__tablename__` của app phải bắt đầu bằng `<table_prefix>_`.
    # Rỗng = app không sở hữu bảng nào (phần lớn app).
    #
    # Tên file là `tables.py`, KHÔNG phải `models.py`: `models.py` trong thư mục
    # app đã mang nghĩa "registry model AI của provider", không liên quan CSDL.
    #
    # Vì sao cần: không có đường này thì app cần bảng thật buộc phải đem model
    # bỏ vào `platform_core/` — đi vòng qua hợp đồng, đúng thứ AGENTS.md mục 60
    # cấm. Tiền tố cho phép app tự giữ model của mình mà hai app không bao giờ
    # đụng tên bảng nhau.
    table_prefix: str = ""

    # VRAM tối thiểu (MB) cho MỘT job của app này, theo từng `job_type`:
    #   gpu_vram_mb = {"autosub.transcribe": 6000, "autosub.render": 2000}
    # Bỏ trống = job không cần GPU riêng.
    #
    # Vì sao khai ở manifest chứ không hardcode trong nền tảng: từ 2026-08-06
    # máy chủ có hai GPU, và worker phải biết job sắp chạy cần bao nhiêu VRAM
    # thì mới chọn được card còn đủ chỗ. Nền tảng KHÔNG được biết tên app nào
    # (test_60 chốt), nên con số phải do chính app khai.
    #
    # Con số là **sàn để xếp chỗ**, không phải hạn mức cứng: nền tảng dùng nó
    # để loại các card không đủ trống, rồi giữ chỗ nguyên tử qua
    # `platform_core.gpu_lease`. Khai thiếu thì job vẫn chạy nhưng có thể bị
    # xếp vào card chật; khai thừa thì job phải chờ lâu hơn cần thiết.
    gpu_vram_mb: dict = field(default_factory=dict)

    # Trần thời gian chạy (giây) cho MỘT job, theo `job_type`:
    #   max_runtime_s = {"myapp.render": 3600}
    # Bỏ trống = dùng trần mặc định của nền tảng theo loại tài nguyên.
    #
    # Vì sao cần: nhặt job mồ côi chỉ bắt worker **chết** (mất đập nhịp). Một
    # job **treo** mà vẫn đập nhịp thì giữ slot vô hạn — và với đội hình vài
    # tiến trình, vài job như vậy là dừng cả nền tảng, im lặng, không ai được
    # báo. Khai ở manifest vì chỉ app biết việc của nó lâu nhất là bao lâu.
    max_runtime_s: dict = field(default_factory=dict)

    # Chờ bao lâu rồi thử lại, khi tài nguyên dùng chung đang bận, theo `job_type`:
    #   cho_tai_nguyen_s = {"myapp.render": 3}
    # Bỏ trống = dùng `job_runner.GPU_RETRY_DELAY_S` (20 giây) như trước.
    #
    # 🔴 VÌ SAO MỘT HẰNG SỐ TOÀN CỤC KHÔNG PHỤC VỤ ĐƯỢC MỌI APP.
    #
    #    20 giây được chọn cho job GPU dài hàng phút: nằm không 20 giây giữa hai
    #    lượt render là không đáng kể, còn quay vòng dày hơn thì đốt CPU và CSDL.
    #
    #    Nhưng job của LTT VOICE làm việc **5 giây**. Đo thật 31/08/2026, năm job
    #    đồng thời trên một suất:
    #
    #        làm việc thật : 4,75 – 5,42 giây (ổn định, không chậm đi khi tải lên)
    #        xếp hàng      : 0,07 → 20,2 → 40,8 → 61,2 → 82,0 giây
    #
    #    Bậc 20 giây đó **không phải** thời gian job trước chiếm tài nguyên — job
    #    trước nhả sau ~5 giây. Đó là thời gian job sau *chưa quay lại hỏi*. GPU
    #    nằm không ~15 trong mỗi 20 giây: mất **75 % thông lượng**, và mất ở chỗ
    #    không ai nhìn vì mọi job vẫn `done`, vẫn đúng tiền.
    #
    # ⚠️ Đừng hạ hằng số toàn cục để "sửa" việc này: nó sẽ bắt các app render
    #    quay vòng dày gấp bảy lần cho một tài nguyên mà chúng biết là sẽ bận
    #    hàng phút. Chỉ app biết việc của nó dài bao lâu — nên nó khai.
    cho_tai_nguyen_s: dict = field(default_factory=dict)

    # Số lần thử tối đa của MỘT job, theo `job_type` (H43 Phase 02, 2026-09-02):
    #   so_lan_thu = {"myapp.synthesize": 5}
    # Bỏ trống = mặc định 3 của `jobs.submit`.
    #
    # 🔴 VÌ SAO KHAI Ở MANIFEST. `apps/ltt_voice` đo được nạp model lúc deploy mất
    #    39,9–73,1 giây trong khi cửa sổ thử lại mặc định (3 lượt) chỉ ~30 giây
    #    ⇒ job chết ở MỌI lần deploy. Nó chữa bằng hằng `SO_LAN_THU_JOB=5` truyền
    #    tay ở bốn route web — nhưng `/api/v1` (`invocation.submit`) **không**
    #    biết hằng đó, nên cùng một job qua API vẫn chạy 3 lượt. Hai cửa, hai
    #    hành vi, cùng một sản phẩm.
    #
    # ⭐ Chỉ app biết việc của nó sống sót qua deploy cần mấy lượt — nên nó khai,
    #    và mọi cửa (web, API, client nội bộ) đọc **một** chỗ qua
    #    `so_lan_thu_for()`. Cùng hình dạng ba bảng ngay trên.
    so_lan_thu: dict = field(default_factory=dict)

    def cho_tai_nguyen_for(self, job_type: str, *, default: int = 20) -> int:
        """Giãn cách thử lại khi tài nguyên bận, giây. Kẹp sàn 1 giây."""
        khai = int((self.cho_tai_nguyen_s or {}).get(job_type, 0))
        return max(1, khai) if khai > 0 else max(1, int(default))

    def so_lan_thu_for(self, job_type: str, *, default: int = 3) -> int:
        """Số lần thử tối đa cho một `job_type`. Không khai ⇒ `default`. Sàn 1."""
        khai = int((self.so_lan_thu or {}).get(job_type, 0))
        return max(1, khai) if khai > 0 else max(1, int(default))

    def vram_for(self, job_type: str) -> int:
        """VRAM tối thiểu cho một `job_type`. 0 = không cần GPU riêng."""
        return int((self.gpu_vram_mb or {}).get(job_type, 0))

    def runtime_limit_for(self, job_type: str, *, default: int = 0) -> int:
        """Trần thời gian chạy cho một `job_type`, giây. 0 = không giới hạn.

        App khai được thì dùng của app; không thì dùng trần nền tảng truyền vào.
        Không bao giờ trả 0 khi nền tảng có mặc định — **không có trần mới là
        mặc định nguy hiểm**, vì nó im lặng cho tới ngày một job treo thật.
        """
        khai = int((self.max_runtime_s or {}).get(job_type, 0))
        return khai if khai > 0 else int(default)

    def needs_gpu(self) -> bool:
        return "gpu" in self.requires or bool(self.gpu_vram_mb)

    def nav_entries(self) -> list:
        """Sidebar của app. Không khai gì thì tạo mặc định 1 dòng."""
        if self.nav:
            return list(self.nav)
        return [NavEntry(label=self.display_name, path=self.route_prefix,
                         icon=self.icon, nav_key=self.slug)]


@dataclass
class LoadedApp:
    """Manifest + router đã import xong."""
    manifest: AppManifest
    router: object = None
    error: str = ""

    @property
    def slug(self) -> str:
        return self.manifest.slug


class RegistryError(Exception):
    pass


def _validate_tool(manifest: AppManifest, tool: ToolSpec,
                   seen_tool_names: set) -> None:
    if not isinstance(tool, ToolSpec):
        raise RegistryError(f"[{manifest.slug}] tools phải chứa ToolSpec")
    if not _TOOL_NAME_RE.fullmatch(tool.name or ""):
        raise RegistryError(
            f"[{manifest.slug}] tool name không hợp lệ: {tool.name!r}")
    if tool.name in seen_tool_names:
        raise RegistryError(f"[{manifest.slug}] tool name trùng: {tool.name!r}")
    if tool.job_type not in manifest.job_types:
        raise RegistryError(
            f"[{manifest.slug}] tool {tool.name!r} dùng job_type không thuộc app: "
            f"{tool.job_type!r}")
    if not (tool.description or "").strip():
        raise RegistryError(f"[{manifest.slug}] tool {tool.name!r} thiếu description")
    if not isinstance(tool.params_schema, dict) or not tool.params_schema:
        raise RegistryError(f"[{manifest.slug}] tool {tool.name!r} params_schema rỗng")
    if not isinstance(tool.returns, dict) or not tool.returns:
        raise RegistryError(f"[{manifest.slug}] tool {tool.name!r} returns rỗng")

    for param, schema in tool.params_schema.items():
        if not isinstance(param, str) or not param or not isinstance(schema, dict):
            raise RegistryError(
                f"[{manifest.slug}] tool {tool.name!r} schema tham số không hợp lệ")
        kind = schema.get("type")
        if kind not in TOOL_PARAM_TYPES:
            raise RegistryError(
                f"[{manifest.slug}] tool {tool.name!r} kiểu tham số lạ: {kind!r}")
        source = schema.get("source")
        if source is not None and not _PROMPT_SOURCE_RE.fullmatch(str(source)):
            raise RegistryError(
                f"[{manifest.slug}] tool {tool.name!r} source không hợp lệ: {source!r}")
        depends_on = schema.get("depends_on")
        if depends_on is not None:
            dependency = tool.params_schema.get(depends_on)
            if not isinstance(dependency, dict) or dependency.get("type") != "model_ref":
                raise RegistryError(
                    f"[{manifest.slug}] tool {tool.name!r} depends_on phải trỏ "
                    "tới tham số model_ref")
            if not schema.get("field"):
                raise RegistryError(
                    f"[{manifest.slug}] tool {tool.name!r} depends_on thiếu field")
        measured_from = schema.get("measured_from")
        if measured_from is not None:
            # `measured_from` nghĩa là: "máy chủ đo tham số này từ media kia,
            # đừng tin con số người gọi khai". Nó tồn tại vì giá phụ thuộc nó
            # (Q84) — nên một bản khai sai phải chặn lúc NẠP, không phải lúc
            # tính tiền.
            if kind not in ("number", "int"):
                raise RegistryError(
                    f"[{manifest.slug}] tool {tool.name!r} measured_from chỉ dùng "
                    f"cho tham số số, không phải {kind!r}")
            nguon = tool.params_schema.get(str(measured_from))
            if not isinstance(nguon, dict) or nguon.get("type") not in MEASURABLE_TYPES:
                raise RegistryError(
                    f"[{manifest.slug}] tool {tool.name!r} measured_from phải trỏ "
                    f"tới một tham số đo được ({'/'.join(sorted(MEASURABLE_TYPES))}): "
                    f"{measured_from!r}")
        if kind == "enum" and not any(
                key in schema for key in ("values", "source", "depends_on")):
            raise RegistryError(
                f"[{manifest.slug}] tool {tool.name!r} enum thiếu nguồn giá trị")
        # `exclusive_with`: hai tham số không được gửi cùng lúc. Cưỡng chế ở
        # `invocation.validate_public_input` (trước khi tiền động). Kiểm lúc NẠP
        # để một tên gõ sai không im lặng thành no-op — cùng ethos `depends_on`.
        exclusive_with = schema.get("exclusive_with")
        if exclusive_with is not None:
            if not isinstance(exclusive_with, (list, tuple)):
                raise RegistryError(
                    f"[{manifest.slug}] tool {tool.name!r} exclusive_with must be "
                    f"a list/tuple, got {type(exclusive_with).__name__}")
            for other in exclusive_with:
                if other == param or other not in tool.params_schema:
                    raise RegistryError(
                        f"[{manifest.slug}] tool {tool.name!r} exclusive_with points "
                        f"to an invalid param: {other!r}")

    # `tuy_chon_dong`: tham số phải có thật, phải là `string`, tham chiếu phải
    # đúng hình `module:attribute`. KHÔNG import module ở đây — `_validate` chạy
    # lúc `discover()`, và kéo mã app vào mọi tiến trình nạp registry là đúng
    # thứ `sync_executor` đã cố tránh.
    for param, ref in (tool.tuy_chon_dong or {}).items():
        spec = tool.params_schema.get(param)
        if not isinstance(spec, dict):
            raise RegistryError(_t(
                "[{slug}] tool {tool!r} tuy_chon_dong trỏ tới tham số không tồn "
                "tại: {param!r}").format(slug=manifest.slug, tool=tool.name,
                                          param=param))
        if spec.get("type") != "string":
            raise RegistryError(_t(
                "[{slug}] tool {tool!r} tuy_chon_dong chỉ hỗ trợ tham số `string`, "
                "{param!r} là {kind!r}").format(slug=manifest.slug, tool=tool.name,
                                                 param=param, kind=spec.get("type")))
        if not isinstance(ref, str) or not _THAM_CHIEU_RE.fullmatch(ref):
            raise RegistryError(_t(
                "[{slug}] tool {tool!r} tuy_chon_dong[{param!r}] phải là "
                "`module:attribute`, nhận {ref!r}").format(
                    slug=manifest.slug, tool=tool.name, param=param, ref=ref))

    _validate_lanes(manifest, tool)

    for output, port_type in tool.returns.items():
        if not isinstance(output, str) or not output or port_type not in TOOL_PORT_TYPES:
            raise RegistryError(
                f"[{manifest.slug}] tool {tool.name!r} kiểu output không hợp lệ: "
                f"{output!r}={port_type!r}")

    _validate_api_contract(manifest, tool)
    _validate_hop_dong_v2(manifest, tool)


#: `side_effect` — ba giá trị, ba hành vi khôi phục. Không có giá trị thứ tư:
#: một tên lạ ở đây nghĩa là app tưởng nó khai được một hành vi mà nền tảng
#: không có, và nó sẽ IM LẶNG rơi về `external` — tức "thử lại" cho một thứ
#: app định khai là không đảo được.
SIDE_EFFECT_VALUES = frozenset({"none", "external", "irreversible"})

#: Khoá được phép trong `resource`. Danh sách ĐÓNG: một khoá viết sai chính tả
#: trong một `dict` tự do không bao giờ báo lỗi — nó chỉ lặng lẽ không có tác
#: dụng, và scheduler xếp chỗ bằng một giá trị mặc định mà không ai biết.
RESOURCE_KEYS = frozenset({"class", "vram_min_mb", "slots", "est_duration_s"})


def _validate_hop_dong_v2(manifest: AppManifest, tool: ToolSpec) -> None:
    """Sáu trường V2 (`25_26 §2`) — kiểm lúc NẠP, không đợi lúc chạy.

    ⭐ Vì sao kiểm ở đây chứ không ở chỗ dùng: ba trong sáu trường quyết định
       **tiền** hoặc **khôi phục sau sự cố** (`side_effect`, `idempotency`,
       `timeout_expr`). Một khai báo sai chỉ lộ ra lúc chạy thì chỗ nó lộ ra là
       chỗ đang tiêu tiền của khách, hoặc chỗ vừa có một sự cố.
    """
    ten = f"[{manifest.slug}] tool {tool.name!r}"

    if not isinstance(tool.type_version, int) or isinstance(tool.type_version, bool) \
            or tool.type_version < 1:
        raise RegistryError(f"{ten} type_version phải là int >= 1, "
                            f"nhận {tool.type_version!r}")

    if tool.side_effect not in SIDE_EFFECT_VALUES:
        raise RegistryError(
            f"{ten} side_effect lạ: {tool.side_effect!r} "
            f"(chỉ {sorted(SIDE_EFFECT_VALUES)})")

    if not isinstance(tool.idempotency, dict):
        raise RegistryError(f"{ten} idempotency phải là dict")
    if tool.idempotency:
        thua = set(tool.idempotency) - {"key_fields"}
        if thua:
            raise RegistryError(f"{ten} idempotency có khoá lạ: {sorted(thua)}")
        khoa = tool.idempotency.get("key_fields")
        if not isinstance(khoa, (tuple, list)) or not khoa:
            raise RegistryError(f"{ten} idempotency.key_fields phải là tuple không rỗng")
        thieu = [k for k in khoa if k not in (tool.params_schema or {})]
        if thieu:
            # ⛔ Đây là phép kiểm đáng giá nhất trong hàm. Một `key_fields` trỏ
            #    tới tham số không tồn tại làm `dedupe_key` được dựng từ một
            #    tập RỖNG hoặc thiếu — nghĩa là **mọi lượt gọi khử trùng vào
            #    nhau**, hoặc **không lượt nào khử trùng**. Cả hai đều là lỗi
            #    về tiền, và cả hai đều im lặng.
            raise RegistryError(
                f"{ten} idempotency.key_fields trỏ tới tham số không có: "
                f"{thieu} (params: {sorted(tool.params_schema or {})})")

    if tool.mock_result is not None and not callable(tool.mock_result):
        raise RegistryError(f"{ten} mock_result phải callable hoặc None")

    if not isinstance(tool.resource, dict):
        raise RegistryError(f"{ten} resource phải là dict")
    thua = set(tool.resource) - RESOURCE_KEYS
    if thua:
        raise RegistryError(
            f"{ten} resource có khoá lạ: {sorted(thua)} "
            f"(chỉ {sorted(RESOURCE_KEYS)})")
    for k in ("vram_min_mb", "slots", "est_duration_s"):
        v = tool.resource.get(k)
        if v is None:
            continue
        if isinstance(v, bool) or not isinstance(v, int) or v < 0:
            raise RegistryError(f"{ten} resource[{k!r}] phải là int >= 0, nhận {v!r}")

    if tool.timeout_expr:
        # Nạp trễ: `bieu_thuc` không phụ thuộc gì trong `platform_core`, nhưng
        # nạp nó ở đầu tệp buộc mọi đường import `registry` phải kéo theo, và
        # `registry` là thứ được nạp sớm nhất trong tiến trình.
        from platform_core.workflow import bieu_thuc

        try:
            bieu_thuc.kiem_bieu_thuc(tool.timeout_expr, tool.params_schema or {})
        except bieu_thuc.LoiBieuThuc as loi:
            raise RegistryError(
                f"{ten} timeout_expr không hợp lệ: {loi}") from loi


def _validate_lanes(manifest: AppManifest, tool: ToolSpec) -> None:
    """Bảng làn phải khai đủ và trỏ vào thứ có thật — kiểm lúc NẠP.

    Đây là chỗ khai bằng dữ liệu trả công: mọi cách khai sai đều bắt được trước
    khi một job nào chạy, thay vì lộ ra dưới dạng "khách chờ mãi không tới lượt".
    """
    if not tool.job_type_by and not tool.job_type_lanes:
        return
    if not (tool.job_type_by and tool.job_type_lanes):
        raise RegistryError(_t(
            "[{slug}] tool {tool!r} khai nửa vời: `job_type_by` và "
            "`job_type_lanes` phải đi cùng nhau").format(
                slug=manifest.slug, tool=tool.name))

    spec = (tool.params_schema or {}).get(tool.job_type_by)
    if not isinstance(spec, dict):
        raise RegistryError(_t(
            "[{slug}] tool {tool!r} job_type_by trỏ tới tham số không tồn tại: "
            "{param!r}").format(slug=manifest.slug, tool=tool.name,
                                param=tool.job_type_by))

    for gia_tri, lane in tool.job_type_lanes.items():
        if lane not in manifest.job_types:
            raise RegistryError(_t(
                "[{slug}] tool {tool!r} làn {lane!r} không thuộc job_types của "
                "app").format(slug=manifest.slug, tool=tool.name, lane=lane))

    # Phủ HẾT giá trị enum. Thiếu một giá trị thì nó rơi âm thầm về làn mặc
    # định — đúng cái lỗi việc này sinh ra để sửa, chỉ khác là nay nó nấp trong
    # một bảng trông như đã đầy đủ.
    values = spec.get("values")
    if values:
        thieu = [v for v in values if v not in tool.job_type_lanes]
        if thieu:
            raise RegistryError(_t(
                "[{slug}] tool {tool!r} job_type_lanes thiếu giá trị: {thieu}"
            ).format(slug=manifest.slug, tool=tool.name, thieu=thieu))


def _validate_api_contract(manifest: AppManifest, tool: ToolSpec) -> None:
    """Chỉ cho phép expose khi hợp đồng công khai ĐỦ (Q92).

    Fail-closed có chủ ý: một tool khai `api_exposed=True` mà thiếu alias model
    hoặc thiếu giá trị enum công khai sẽ **bị từ chối nạp**, thay vì lặng lẽ
    publish một hợp đồng làm lộ tên provider hoặc thư viện prompt nội bộ.
    """
    contract = tool.api_contract or {}
    if not isinstance(contract, dict):
        raise RegistryError(_t(
            "[{slug}] tool {tool!r} api_contract phải là dict").format(
                slug=manifest.slug, tool=tool.name))
    if not tool.api_exposed:
        if contract:
            raise RegistryError(_t(
                "[{slug}] tool {tool!r} có api_contract nhưng api_exposed=False "
                "— bỏ hợp đồng hoặc bật cờ, đừng để nửa vời").format(
                    slug=manifest.slug, tool=tool.name))
        return

    from platform_core.public_api.scopes import KNOWN_SCOPES

    from platform_core.public_api.protocol import MODES_IN_USE, TOOL_MODES

    unknown_keys = set(contract) - {"public_name", "description", "models",
                                    "enums", "hidden", "scopes", "deprecated",
                                    "execution_mode", "aliases", "params",
                                    "output_counts"}
    if unknown_keys:
        raise RegistryError(_t(
            "[{slug}] tool {tool!r} api_contract có khoá lạ: {keys}").format(
                slug=manifest.slug, tool=tool.name, keys=sorted(unknown_keys)))

    # Absent means ASYNC_JOB: every tool the platform has runs on a worker and
    # charges credit. Declaring anything else is deliberate, and only the modes
    # whose semantics are already implemented and tested may be declared — a
    # manifest cannot opt into STREAM or BATCH before the platform can honour
    # what those modes promise (EXT-02, D5).
    mode = str(contract.get("execution_mode") or "ASYNC_JOB")
    if mode not in TOOL_MODES:
        raise RegistryError(_t(
            "[{slug}] tool {tool!r} execution_mode không hợp lệ: {value!r}"
        ).format(slug=manifest.slug, tool=tool.name, value=mode))
    if mode not in MODES_IN_USE:
        raise RegistryError(_t(
            "[{slug}] tool {tool!r} khai execution_mode {value!r} nhưng nền "
            "tảng chưa thi hành mode đó").format(
                slug=manifest.slug, tool=tool.name, value=mode))

    public_name = str(contract.get("public_name") or tool.name)
    if not _TOOL_NAME_RE.fullmatch(public_name):
        raise RegistryError(_t(
            "[{slug}] tool {tool!r} public_name không hợp lệ: {value!r}").format(
                slug=manifest.slug, tool=tool.name, value=public_name))

    scopes = tuple(contract.get("scopes") or ())
    unknown_scopes = sorted(set(map(str, scopes)) - set(KNOWN_SCOPES))
    if unknown_scopes:
        raise RegistryError(_t(
            "[{slug}] tool {tool!r} scope lạ: {scopes}").format(
                slug=manifest.slug, tool=tool.name, scopes=unknown_scopes))

    hidden = {str(name) for name in (contract.get("hidden") or ())}
    models = contract.get("models") or {}
    enums = contract.get("enums") or {}
    if not isinstance(models, dict) or not isinstance(enums, dict):
        raise RegistryError(_t(
            "[{slug}] tool {tool!r} models/enums phải là dict").format(
                slug=manifest.slug, tool=tool.name))

    for param, schema in tool.params_schema.items():
        if param in hidden:
            continue
        kind = schema.get("type")
        if kind == "model_ref" and not models:
            raise RegistryError(_t(
                "[{slug}] tool {tool!r} tham số {param!r} là model_ref nhưng "
                "api_contract thiếu alias `models` — không được để id model/nhà "
                "cung cấp thật lọt ra API công khai").format(
                    slug=manifest.slug, tool=tool.name, param=param))
        if kind == "enum" and "values" not in schema and param not in enums:
            raise RegistryError(_t(
                "[{slug}] tool {tool!r} enum {param!r} lấy giá trị từ nguồn nội "
                "bộ nhưng api_contract không khai `enums` cũng không đưa vào "
                "`hidden`").format(slug=manifest.slug, tool=tool.name, param=param))

    for param in hidden | set(enums):
        if param not in tool.params_schema:
            raise RegistryError(_t(
                "[{slug}] tool {tool!r} api_contract nhắc tham số không tồn "
                "tại: {param!r}").format(slug=manifest.slug, tool=tool.name,
                                          param=param))

    _validate_output_counts(manifest, tool, contract.get("output_counts") or {})
    _validate_model_aliases(manifest, tool, models)
    _validate_param_docs(manifest, tool, contract.get("params") or {}, hidden)

    for alias in (contract.get("aliases") or ()):
        if not _TOOL_NAME_RE.fullmatch(str(alias)):
            raise RegistryError(_t(
                "[{slug}] tool {tool!r} alias không hợp lệ: {value!r}").format(
                    slug=manifest.slug, tool=tool.name, value=alias))
        if str(alias) == public_name:
            raise RegistryError(_t(
                "[{slug}] tool {tool!r} alias trùng chính public_name").format(
                    slug=manifest.slug, tool=tool.name))


def _validate_output_counts(manifest: AppManifest, tool: ToolSpec,
                            counts) -> None:
    """Which input decides how long a list output is.

    Only the app knows that `count` multiplies `image_keys`, so it is declared
    here rather than guessed. Checked on both sides — a declaration naming an
    output that is not a list, or a parameter that does not exist, is a typo
    that would otherwise surface as a sandbox quietly returning one file
    (EXT-12).
    """
    if not isinstance(counts, dict):
        raise RegistryError(_t(
            "[{slug}] tool {tool!r} api_contract.output_counts phải là dict"
        ).format(slug=manifest.slug, tool=tool.name))
    for output, param in counts.items():
        if not str(tool.returns.get(output, "")).endswith("[]"):
            raise RegistryError(_t(
                "[{slug}] tool {tool!r} output_counts khai {output!r} nhưng đó "
                "không phải đầu ra dạng danh sách").format(
                    slug=manifest.slug, tool=tool.name, output=output))
        if param not in tool.params_schema:
            raise RegistryError(_t(
                "[{slug}] tool {tool!r} output_counts trỏ tới tham số không tồn "
                "tại: {param!r}").format(slug=manifest.slug, tool=tool.name,
                                         param=param))


def _validate_param_docs(manifest: AppManifest, tool: ToolSpec, params,
                         hidden: set) -> None:
    """Public prose about a parameter, checked against the parameter it describes.

    The docs live in the public contract rather than in ``params_schema``: the
    internal schema is written for the worker and routinely names providers and
    internal prompt sets, while this text is written for a customer and goes
    straight into the reference page (EXT-06).
    """
    if not isinstance(params, dict):
        raise RegistryError(_t(
            "[{slug}] tool {tool!r} api_contract.params phải là dict").format(
                slug=manifest.slug, tool=tool.name))
    for name, spec in params.items():
        if name not in tool.params_schema:
            raise RegistryError(_t(
                "[{slug}] tool {tool!r} params mô tả tham số không tồn tại: "
                "{param!r}").format(slug=manifest.slug, tool=tool.name,
                                    param=name))
        if name in hidden:
            # Documenting a parameter the caller cannot send is a promise the
            # API does not keep.
            raise RegistryError(_t(
                "[{slug}] tool {tool!r} params mô tả tham số đang ẩn: {param!r}"
            ).format(slug=manifest.slug, tool=tool.name, param=name))
        if not isinstance(spec, dict):
            raise RegistryError(_t(
                "[{slug}] tool {tool!r} params[{param!r}] phải là dict").format(
                    slug=manifest.slug, tool=tool.name, param=name))
        unknown = set(spec) - {"description", "example", "only_when"}
        if unknown:
            raise RegistryError(_t(
                "[{slug}] tool {tool!r} params[{param!r}] có khoá lạ: {keys}"
            ).format(slug=manifest.slug, tool=tool.name, param=name,
                     keys=sorted(unknown)))
        if "only_when" in spec:
            _validate_only_when(manifest, tool, name, spec["only_when"], hidden)
        if not str(spec.get("description") or "").strip():
            raise RegistryError(_t(
                "[{slug}] tool {tool!r} params[{param!r}] thiếu description"
            ).format(slug=manifest.slug, tool=tool.name, param=name))


def _validate_only_when(manifest: AppManifest, tool: ToolSpec, param: str,
                        dieu_kien, hidden) -> None:
    """`only_when` phải trỏ vào một tham số CÓ THẬT và những giá trị CÓ THẬT.

    🔴 VÌ SAO PHẢI KIỂM, chứ không chỉ chép ra. `only_when` là thứ trang tài liệu
       dùng để **lọc** tham số. Khai `{"mode": ["edti"]}` (gõ sai) thì điều kiện
       không bao giờ khớp, và tham số đó **biến mất** khỏi mọi chế độ — khách
       không bao giờ biết mình gửi được nó.

    ⛔ Một điều kiện không ai kiểm thì cũng vô dụng đúng như câu văn xuôi mà nó
       vừa thay thế. Khác biệt duy nhất là nó **trông** như dữ liệu.

    ⚠️ Không cho trỏ vào tham số **ẩn**: điều kiện đó khách không điều khiển
       được, nên hiển thị nó là bảo người ta xoay một cái nút không tồn tại.
    """
    if not isinstance(dieu_kien, dict) or not dieu_kien:
        raise RegistryError(_t(
            "[{slug}] tool {tool!r} params[{param!r}].only_when phải là dict "
            "không rỗng").format(slug=manifest.slug, tool=tool.name, param=param))
    for khoa, gia_tri in dieu_kien.items():
        if khoa not in tool.params_schema:
            raise RegistryError(_t(
                "[{slug}] tool {tool!r} params[{param!r}].only_when trỏ vào "
                "tham số không tồn tại: {k!r}").format(
                    slug=manifest.slug, tool=tool.name, param=param, k=khoa))
        if khoa in hidden:
            raise RegistryError(_t(
                "[{slug}] tool {tool!r} params[{param!r}].only_when trỏ vào "
                "tham số đang ẩn: {k!r}").format(
                    slug=manifest.slug, tool=tool.name, param=param, k=khoa))
        if not isinstance(gia_tri, (list, tuple)) or not gia_tri:
            raise RegistryError(_t(
                "[{slug}] tool {tool!r} params[{param!r}].only_when[{k!r}] phải "
                "là danh sách không rỗng").format(
                    slug=manifest.slug, tool=tool.name, param=param, k=khoa))
        # Giá trị phải nằm trong `enum` đã khai — nếu tham số đó có enum.
        hop_le = tool.params_schema[khoa].get("values")
        if hop_le is not None:
            la = [v for v in gia_tri if v not in hop_le]
            if la:
                raise RegistryError(_t(
                    "[{slug}] tool {tool!r} params[{param!r}].only_when[{k!r}] "
                    "có giá trị không nằm trong enum: {la}").format(
                        slug=manifest.slug, tool=tool.name, param=param,
                        k=khoa, la=sorted(map(str, la))))


def _validate_model_aliases(manifest: AppManifest, tool: ToolSpec,
                            models: dict) -> None:
    """A model alias is a public promise; check it says enough and no more."""
    from platform_core.public_api.catalog import STABILITIES

    for alias, target in models.items():
        spec = target if isinstance(target, dict) else {"id": target}
        if not str(spec.get("id") or "").strip():
            raise RegistryError(_t(
                "[{slug}] tool {tool!r} alias model {alias!r} thiếu `id` nội "
                "bộ").format(slug=manifest.slug, tool=tool.name, alias=alias))
        stability = str(spec.get("stability") or "stable")
        if stability not in STABILITIES:
            raise RegistryError(_t(
                "[{slug}] tool {tool!r} alias model {alias!r} có stability lạ: "
                "{value!r}").format(slug=manifest.slug, tool=tool.name,
                                    alias=alias, value=stability))
        if stability == "deprecated" and not str(spec.get("replaced_by") or ""):
            # A deprecated alias without a successor tells a caller their
            # integration is dying and nothing about where to go instead.
            raise RegistryError(_t(
                "[{slug}] tool {tool!r} alias model {alias!r} đánh dấu "
                "deprecated nhưng không nói thay bằng gì").format(
                    slug=manifest.slug, tool=tool.name, alias=alias))
        unknown = set(spec) - {"id", "stability", "description", "constraints",
                               "replaced_by"}
        if unknown:
            raise RegistryError(_t(
                "[{slug}] tool {tool!r} alias model {alias!r} có khoá lạ: "
                "{keys}").format(slug=manifest.slug, tool=tool.name,
                                 alias=alias, keys=sorted(unknown)))
        replacement = str(spec.get("replaced_by") or "")
        if replacement and replacement not in models:
            raise RegistryError(_t(
                "[{slug}] tool {tool!r} alias model {alias!r} trỏ tới alias "
                "không tồn tại: {value!r}").format(
                    slug=manifest.slug, tool=tool.name, alias=alias,
                    value=replacement))


def _validate(manifest: AppManifest, seen_slugs: set, seen_prefixes: set,
              seen_job_types: Optional[set] = None,
              seen_tool_names: Optional[set] = None,
              seen_table_prefixes: Optional[set] = None) -> None:
    """Chặn sớm những sai sót âm thầm gây khó hiểu về sau."""
    seen_job_types = seen_job_types if seen_job_types is not None else set()
    seen_tool_names = seen_tool_names if seen_tool_names is not None else set()
    seen_table_prefixes = (seen_table_prefixes
                           if seen_table_prefixes is not None else set())
    if not manifest.slug or not manifest.slug.replace("_", "").isalnum():
        raise RegistryError(
            f"slug không hợp lệ: {manifest.slug!r} — chỉ chữ, số và gạch dưới")
    if manifest.slug in seen_slugs:
        raise RegistryError(f"slug trùng: {manifest.slug!r}")
    if not manifest.route_prefix.startswith("/"):
        raise RegistryError(
            f"[{manifest.slug}] route_prefix phải bắt đầu bằng '/': "
            f"{manifest.route_prefix!r}")
    if manifest.route_prefix.rstrip("/") in seen_prefixes:
        # Hai app cùng prefix thì app nạp sau bị app trước che mất, và
        # FastAPI không báo gì cả — rất khó truy.
        raise RegistryError(
            f"[{manifest.slug}] route_prefix trùng: {manifest.route_prefix!r}")
    if manifest.surface not in APP_SURFACES:
        raise RegistryError(
            _t("[{slug}] surface không hợp lệ: {value!r}").format(
                slug=manifest.slug, value=manifest.surface))
    if manifest.lifecycle not in APP_LIFECYCLES:
        raise RegistryError(
            _t("[{slug}] lifecycle không hợp lệ: {value!r}").format(
                slug=manifest.slug, value=manifest.lifecycle))
    if (not isinstance(manifest.capabilities, tuple) or
            any(not isinstance(value, str) or not value.strip()
                for value in manifest.capabilities)):
        raise RegistryError(
            _t("[{slug}] capabilities phải là tuple chuỗi không rỗng").format(
                slug=manifest.slug))
    if manifest.catalog_parent:
        parent = manifest.catalog_parent
        if (parent == manifest.slug or
                not parent.replace("_", "").isalnum()):
            raise RegistryError(
                _t("[{slug}] catalog_parent không hợp lệ: {value!r}").format(
                    slug=manifest.slug, value=parent))
    # Fail SỚM ngay lúc discover (W1.6): app sinh job mà KHÔNG khai credit_cost
    # thì job không tra được giá — trước đây chỉ vỡ lúc submit (app đã hiện trên
    # catalog, khách bấm rồi mới lỗi). Đánh dấu app lỗi ngay để không lên catalog.
    if manifest.job_types and manifest.credit_cost is None:
        raise RegistryError(
            f"[{manifest.slug}] khai job_types nhưng thiếu credit_cost — "
            f"job sẽ không tra được giá, từ chối nạp")
    # job_type trùng giữa hai app: worker phân job theo job_type, trùng thì nhập
    # nhằng nguy hiểm (một app quyết toán theo giá app kia). Chặn ngay.
    for jt in manifest.job_types:
        if jt in seen_job_types:
            raise RegistryError(f"[{manifest.slug}] job_type trùng: {jt!r}")
    # `so_lan_thu` phải trỏ tới job_type CỦA app và là số nguyên ≥ 1. Một bản
    # khai lệch tên job_type thì im lặng vô hiệu — đúng loại lỗi phải bắt lúc nạp.
    for jt, so in (manifest.so_lan_thu or {}).items():
        if jt not in manifest.job_types:
            raise RegistryError(_t(
                "[{slug}] so_lan_thu khai job_type không thuộc app: {jt!r}"
            ).format(slug=manifest.slug, jt=jt))
        if not isinstance(so, int) or isinstance(so, bool) or so < 1:
            raise RegistryError(_t(
                "[{slug}] so_lan_thu[{jt!r}] phải là số nguyên ≥ 1: {so!r}"
            ).format(slug=manifest.slug, jt=jt, so=so))
    # Tiền tố bảng trùng nhau thì hai app ghi đè bảng của nhau và Alembic chỉ
    # thấy một cái — mất dữ liệu âm thầm. Chặn ngay lúc discover.
    if manifest.table_prefix:
        if not manifest.table_prefix.replace("_", "").isalnum():
            raise RegistryError(
                f"[{manifest.slug}] table_prefix không hợp lệ: "
                f"{manifest.table_prefix!r} — chỉ chữ, số và gạch dưới")
        if manifest.table_prefix in seen_table_prefixes:
            raise RegistryError(
                f"[{manifest.slug}] table_prefix trùng: {manifest.table_prefix!r}")
    local_tool_names: set = set()
    for tool in manifest.tools:
        _validate_tool(manifest, tool, seen_tool_names | local_tool_names)
        local_tool_names.add(tool.name)


def visible_on_surface(manifest: AppManifest, *, authenticated: bool,
                       operator: bool = False) -> bool:
    """Một nguồn chân lý cho catalog/header; không quyết định quyền route.

    Route của app ``runtime`` vẫn được mount. App ``admin`` chỉ xuất hiện với
    operator đã đăng nhập. App ``customer`` tuân theo cờ public khi ẩn danh.
    """
    if manifest.surface == "runtime" or manifest.catalog_parent:
        return False
    if manifest.surface == "admin":
        return bool(authenticated and operator)
    return bool(authenticated or manifest.public)


def discover(apps_dir: pathlib.Path = APPS_DIR) -> list:
    """Quét apps/*/manifest.py. Trả về danh sách LoadedApp đã sắp xếp.

    Một app lỗi KHÔNG làm sập nền tảng — nó được ghi lại kèm lý do và hiện
    trên trang chủ. Đó là điểm khác biệt quan trọng: bạn vẫn vào được hệ thống
    để xem app nào lỗi, thay vì cả site 500.
    """
    if not apps_dir.exists():
        return []

    loaded: list = []
    seen_slugs: set = set()
    seen_prefixes: set = set()
    seen_job_types: set = set()
    seen_tool_names: set = set()
    seen_table_prefixes: set = set()

    for entry in sorted(apps_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith(("_", ".")):
            continue
        if not (entry / "manifest.py").exists():
            continue

        try:
            mod = importlib.import_module(f"apps.{entry.name}.manifest")
            manifest = getattr(mod, "MANIFEST")
            if not isinstance(manifest, AppManifest):
                raise RegistryError("MANIFEST không phải AppManifest")
            _validate(manifest, seen_slugs, seen_prefixes, seen_job_types,
                      seen_tool_names, seen_table_prefixes)
        except Exception as exc:
            loaded.append(LoadedApp(
                manifest=AppManifest(
                    slug=entry.name, display_name=entry.name,
                    route_prefix=f"/{entry.name}", enabled=False,
                ),
                error=f"{type(exc).__name__}: {exc}",
            ))
            continue

        seen_slugs.add(manifest.slug)
        seen_prefixes.add(manifest.route_prefix.rstrip("/"))
        seen_job_types.update(manifest.job_types)
        seen_tool_names.update(tool.name for tool in manifest.tools)
        if manifest.table_prefix:
            seen_table_prefixes.add(manifest.table_prefix)

        router = None
        router_error = ""
        try:
            rmod = importlib.import_module(f"apps.{entry.name}.routes")
            router = getattr(rmod, "router", None)
            if router is None:
                router_error = "routes.py không có biến `router`"
        except ModuleNotFoundError:
            # App chỉ có job, không có UI riêng — hợp lệ.
            pass
        except Exception as exc:
            router_error = f"{type(exc).__name__}: {exc}"

        loaded.append(LoadedApp(manifest=manifest, router=router,
                                error=router_error))

    return loaded


def load_app_tables(apps_dir: pathlib.Path = APPS_DIR) -> list[str]:
    """Nạp `apps/<slug>/tables.py` để `Base.metadata` đầy đủ. Trả về slug đã nạp.

    Alembic gọi hàm này trong `env.py`, còn server gọi khi khởi động. Không đi
    qua `discover()` vì Alembic không cần router và không nên chạm tới chúng.

    Tên file là `tables.py` chứ KHÔNG phải `models.py`: trong thư mục app,
    `models.py` đã mang nghĩa "registry model AI của provider" và không liên
    quan CSDL. Dùng chung tên sẽ khiến Alembic import nhầm file cấu hình đó.

    App KHÔNG có `tables.py` là hợp lệ — phần lớn app chỉ cần `AppProject`.
    Nhưng app có `tables.py` mà thiếu `table_prefix`, hoặc đặt tên bảng sai tiền
    tố, thì bị từ chối NGAY: bảng lạc chỗ chỉ lộ ra khi Alembic sinh migration
    xoá nhầm bảng của app khác — quá muộn.
    """
    if not apps_dir.exists():
        return []

    # Import tại chỗ: `platform_core.db` kéo theo SQLAlchemy engine, còn
    # registry được import từ nhiều nơi nhẹ hơn (kể cả lúc chưa có CSDL).
    from platform_core.db import Base

    loaded: list[str] = []
    for entry in sorted(apps_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith(("_", ".")):
            continue
        if not (entry / "tables.py").exists():
            continue

        mod = importlib.import_module(f"apps.{entry.name}.manifest")
        manifest = getattr(mod, "MANIFEST")
        prefix = (manifest.table_prefix or "").strip()
        if not prefix:
            raise RegistryError(
                f"[{entry.name}] có tables.py nhưng manifest thiếu table_prefix")

        before = set(Base.metadata.tables)
        importlib.import_module(f"apps.{entry.name}.tables")
        for name in set(Base.metadata.tables) - before:
            if not name.startswith(f"{prefix}_"):
                raise RegistryError(
                    f"[{entry.name}] bảng {name!r} không bắt đầu bằng "
                    f"{prefix + '_'!r} — đổi tên hoặc đổi table_prefix")
        loaded.append(entry.name)
    return loaded


def mount_all(app, apps: Optional[list] = None) -> list:
    """Gắn router của mọi app vào FastAPI. Trả về danh sách đã nạp."""
    apps = discover() if apps is None else apps
    for item in apps:
        if item.router is not None and not item.error:
            app.include_router(item.router, prefix=item.manifest.route_prefix)
    return apps


def job_type_owners(apps: Optional[list] = None) -> dict:
    """job_type -> slug. Dùng để phân job và tra giá credit."""
    apps = discover() if apps is None else apps
    out: dict = {}
    for item in apps:
        for jt in item.manifest.job_types:
            out[jt] = item.manifest.slug
    return out


def viec_bao_tri(apps: Optional[list] = None) -> list[tuple[str, Callable, int]]:
    """`[(slug, hàm, giãn_cách_giây)]` của các app có khai việc nền định kỳ.

    Chỉ lấy app **đang bật**: một app tắt cờ mà việc nền vẫn chạy là app đã tắt
    một nửa — và nửa còn chạy là nửa động vào tiền và dữ liệu của khách.
    """
    apps = discover() if apps is None else apps
    ra = []
    for item in apps:
        m = item.manifest
        if m.bao_tri is not None and m.enabled:
            ra.append((m.slug, m.bao_tri, max(60, int(m.bao_tri_moi_giay or 0))))
    return ra


def bang_gia_cong_khai(apps: Optional[list] = None) -> dict[str, dict]:
    """`{slug: bảng_giá}` của các app **đang bật** có khai `bang_gia`.

    Để trang `/gia-api` dựng bảng giá mà **không phải biết tên app nào cả**.
    Trước 2026-09-02 nó `import apps.anhnoibo.gia` và `apps.ltt_voice.gia` —
    hai cạnh `server → app` mà không hợp đồng nào khai.

    ⛔ Một app hỏng bảng giá KHÔNG được làm sập trang giá của mọi app khác. Bắt
       và bỏ qua app đó, **có ghi log**, đúng luật của `bao_tri`.

    ⚠️ Chỉ lấy app đang bật: công bố giá của một app đã tắt là mời khách mua
       một thứ không bán.
    """
    apps = discover() if apps is None else apps
    ra: dict[str, dict] = {}
    for item in apps:
        m = item.manifest
        if m.bang_gia is None or not m.enabled:
            continue
        try:
            gia = m.bang_gia()
        except Exception:                      # noqa: BLE001 — xem docstring
            log.exception("[%s] bang_gia() nem loi — bo qua app nay", m.slug)
            continue
        if isinstance(gia, dict) and gia:
            ra[m.slug] = gia
    return ra


def credit_for(job_type: str, params: dict, apps: Optional[list] = None) -> int:
    """Credit cần cho một job. Raise nếu job_type không ai nhận.

    Cố tình raise thay vì trả 0: một job không tính được giá mà vẫn chạy là
    một job miễn phí ngoài ý muốn, và với $0,68/giây thì đó là mất tiền thật.
    """
    apps = discover() if apps is None else apps
    for item in apps:
        if job_type in item.manifest.job_types:
            fn = item.manifest.credit_cost
            if fn is None:
                raise RegistryError(
                    f"[{item.slug}] job_type {job_type!r} chưa khai credit_cost "
                    f"— từ chối chạy để không phát sinh chi phí không kiểm soát")
            return int(fn(params))
    raise RegistryError(f"không app nào nhận job_type {job_type!r}")

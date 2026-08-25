# Thêm một app mới

Thêm app = **thêm một thư mục**. Không sửa file nào của nền tảng.

Nếu bạn thấy mình phải sửa `platform_core/` hoặc `server/` để app mới chạy
được, thì **dừng lại** — đó là dấu hiệu hợp đồng app còn thiếu. Bổ sung vào
hợp đồng, đừng đi vòng, vì đi vòng một lần là app sau lại phải đi vòng.

---

## Ba file cần tạo

```
apps/<slug>/
├── __init__.py      (rỗng)
├── manifest.py      ★ bản khai — nền tảng đọc file này
├── routes.py        giao diện (bỏ qua nếu app chỉ chạy job nền)
├── jobs.py          phần xử lý thật
└── templates/       (tuỳ chọn) template RIÊNG của app — extends "base.html"
```

**Template của app (bổ sung hợp đồng từ H5):** đặt `.html` trong
`apps/<slug>/templates/`. Jinja tìm ở cả `server/templates/` LẪN
`apps/*/templates/`, nên `routes.py` gọi `templates.TemplateResponse(request,
"ten_file.html", {...})` như thường — KHÔNG phải bỏ file vào `server/`.
`server/templates/` được ưu tiên khi trùng tên (app không ghi đè được vỏ nền
tảng). Nhờ vậy "thêm app = thêm thư mục" đúng cho cả giao diện.

**File output cho người dùng tải:** app tự phục vụ qua route riêng đọc từ
`platform_core.storage` (xem `apps/thumbnail/routes.py` route `/image/{key}`) —
kiểm sở hữu theo key. KHÔNG dùng `storage.download_token` qua ranh giới
worker→web (token giữ trong RAM mỗi tiến trình).

⚠️ **Không còn app khuôn để copy.** `apps/demo/` — app mẫu tối thiểu — đã bị gỡ
2026-08-25 (Q109). Nó tồn tại để bốn bộ test hạ tầng có chỗ nộp job, và chính vai
trò đó biến nó thành thứ không xoá được; nay việc đó do một app THỬ tổng hợp
trong `tests/conftest.py::app_thu` đảm nhiệm.

⇒ Dùng **khuôn đầy đủ ngay bên dưới** (mục 1–4) — nó là nguồn chân lý, không phải
bản tóm tắt của một app. Muốn xem một app THẬT nhỏ gọn thì đọc `apps/anhnoibo/`
(chỉ job, không route) hoặc `apps/thumbnail/` (có route + template).

---

## App VIẾT MỚI vs App DI TRÚ từ BOT GEMINI (bắt buộc phân biệt)

- **Viết mới** (ta tự nghĩ ra): theo hợp đồng tối thiểu bên dưới.
- **Di trú** (đưa một module BOT GEMINI sang): PHẢI theo **`CONG_THUC_DI_TRU_APP.md`**
  (công thức 8 bước) và đạt **parity ≥ 90%** tính năng người dùng của bản gốc — KHÔNG
  được tự tối giản. Bài học `thumbnail` (xem `DOI_CHIEU_THUMBNAIL.md`): dựng lại tối
  giản = mất hệ lựa chọn của bản gốc.

**Quy ước tài nguyên prompt (`apps/<slug>/prompts/`):** app có nhiều lựa chọn
(style/phong cách/trend/ngôn ngữ…) để nguyên dạng **thư mục fragment** copy từ gốc:
```
apps/<slug>/prompts/
├── base_prompt.txt           # template {placeholder}
└── <nhóm>/_labels.json + <id>.txt
```
Ghép prompt bằng `platform_core.prompt_fragments` — **CẤM hardcode chuỗi prompt trong
`jobs.py`**. UI render lựa chọn ĐỘNG từ `_labels.json` (thêm/bớt = sửa tài nguyên,
không sửa code). Model chọn được khai ở `platform_core/providers.py` (registry).

---

## 1. `manifest.py`

```python
from platform_core.registry import AppManifest, NavEntry


def _cost(params: dict) -> int:
    """Giá credit. LÀ HÀM, không phải hằng số.

    Ví dụ thật: Seedance 2.0 tính theo GIÂY VIDEO × ĐỘ PHÂN GIẢI
    (720p ≈ 0,30 USD/giây, 1080p ≈ 0,68 USD/giây). Một con số cố định
    sẽ tính sai ngay từ job đầu tiên.
    """
    seconds = int(params.get("duration_s", 5))
    per_second = 100 if params.get("resolution") == "1080p" else 45
    return seconds * per_second


MANIFEST = AppManifest(
    slug="seedance",                       # = tên thư mục, chỉ chữ/số/gạch dưới
    display_name="Tạo video AI",
    route_prefix="/seedance",              # app.lttstudios.com/seedance
    summary="Sinh video từ mô tả bằng Seedance 2.0.",
    icon="🎬",
    accent="#6A0DAD",

    nav=(NavEntry("Tạo video", "/seedance", "🎬", "seedance"),),

    job_types=("seedance.t2v",),           # phải là duy nhất toàn hệ thống
    requires=("api",),                     # api | ffmpeg | gpu | browser
    credit_cost=_cost,

    enabled=True,
    public=True,                           # hiện trên trang chủ CÔNG KHAI (khách chưa đăng nhập)
    notes="",
)
```

### `slug` — quy ước đặt tên (H6/Q30)

`slug` vừa là **tên thư mục** `apps/<slug>/`, vừa là mặc định gợi ý cho
`route_prefix`. Quy ước:

- chỉ **chữ thường, số, gạch dưới** — không dấu, không khoảng trắng, không hoa;
- **ngắn, ổn định** — slug đi vào URL `app.lttstudios.com/<...>`, đổi về sau là
  gãy link người dùng đã lưu;
- **duy nhất toàn hệ thống** — trùng `route_prefix` bị `test_60` chặn.

`route_prefix` không bắt buộc trùng slug — một app có thể khai `nav` trỏ ra
ngoài prefix của nó vì lý do lịch sử. App mới nên đặt `route_prefix="/<slug>"`
cho nhất quán và dễ đoán.

### `public` — hiện trên trang chủ công khai hay không (H6/Q30)

Trang chủ `/` là **catalog công khai**: khách chưa đăng nhập xem được, mỗi app
là một thẻ, bấm vào thì bị đưa về `/login?next=<route_prefix>` rồi quay lại
đúng chỗ sau khi đăng nhập.

- `public=True` (mặc định) → app xuất hiện trên catalog công khai. Dùng cho tool
  thương mại muốn khách nhìn thấy để mua.
- `public=False` → app **ẩn khỏi catalog khách**, chỉ hiện trong sidebar sau khi
  đăng nhập và **được phân quyền** (`app_access`). Dùng cho công cụ nội bộ
  (`qualitylab` — đo chất lượng) hoặc app riêng chưa mở bán.

`public` chỉ chi phối **hiển thị trên catalog**. Chặn truy cập thật vẫn nằm ở
tầng route (`require_login`) + phân quyền `app_access` — một app `public=False`
gõ thẳng URL vẫn bị chặn đúng như app công khai.

### `requires` — quyết định app chạy ở máy nào

| Giá trị | Nghĩa là | Nên đặt ở đâu |
|---|---|---|
| `api` | chỉ gọi API bên ngoài | **cloud** — không cần máy bạn |
| `ffmpeg` | cần ffmpeg cục bộ | máy bạn |
| `gpu` | cần VRAM | máy bạn |
| `browser` | cần trình duyệt **và IP dân dụng** | **bắt buộc máy bạn** |

`browser` là trường hợp đáng chú ý: Meta và TikTok đánh dấu IP datacenter rất
nặng, nên bot đăng bài chạy từ IP nhà bạn an toàn hơn nhiều. Đây là lý do
chính đáng nhất để máy bạn tồn tại trong hệ thống.

Ngược lại, `api` nghĩa là **máy bạn không tham gia gì**. Seedance 2.0 là
API-only, không có open weights — GPU của bạn hoàn toàn không được dùng. Đừng
mua phần cứng cho những app loại này.

---

## 2. `jobs.py`

```python
def handle(params: dict, ctx=None) -> dict:
    """params đã được validate ở routes.py. ctx do worker cấp."""
    ...
    if ctx is not None:
        ctx.progress(50, "đang xử lý")
    ...
    return {"output_key": "...", "duration_s": 5}
```

Ba quy tắc, đều xuất phát từ chuyện tiền:

1. **Idempotent.** Worker có thể gọi lại cùng một job (mất mạng, worker chết
   rồi khoá job hết hạn). Gọi hai lần không được tính phí hai lần.
2. **Báo tiến độ.** Job dài mà im lặng thì người dùng tưởng treo, bấm lại, và
   bạn trả tiền API hai lần.
3. **Ném exception khi thất bại.** Nền tảng dựa vào exception để hoàn lại
   credit đã giữ. Trả về êm ru nghĩa là job "thành công" và tiền vẫn bị trừ.

---

## 2b. Lấy API key (H8) — KHÔNG đọc biến môi trường

App **không giữ khoá API**. Xin khoá từ bộ máy APIKEYS theo (provider, category,
model); admin quản khoá ở `/admin` → APIKEYS.

```python
from platform_core import api_keys, api_pool
from platform_core.db import get_session
from platform_core.models import APIKEY_CAT_IMAGE

gen = get_session(); db = next(gen)
try:
    key = api_pool.lay_key(db, "gemini", category=APIKEY_CAT_IMAGE, model=model)
    credential = api_keys.lay_credential(db, key)   # chỉ nơi gọi API mới giải mã
    db.commit()
finally:
    ...
# ... gọi API bằng credential ...
api_pool.danh_dau_thanh_cong(db, key)               # hoặc danh_dau_loi(db, key, http_status=...)
```

`lay_key` raise `ThieuKeyError` nếu không có khoá khả dụng → app báo lỗi rõ, KHÔNG
gọi API chùa. Provider mới (auth_style, base_url, model) khai ở
`platform_core/providers.py` — thêm một dòng, không sửa app. Khoá cookie/browser
(Veo, ChatGPT web) là loại KHÁC, chưa thuộc bộ máy này.

**Pha 2 — cascade + telemetry (khi cần bền hơn):** muốn một loại API tự rớt sang
provider khác khi provider chính cạn key, xin theo *category* thay vì cố định
provider:

```python
key = api_pool.chon_key(db, category=APIKEY_CAT_CHAT,
                        thu_tu_provider=["gemini", "apiai", "cheapkeyai"])
```

`chon_key` gom key mọi provider phục vụ category, tôn trọng thứ tự ưu tiên, bỏ key
cooldown/tắt/đã chạm `rpm_limit`/`tpm_limit`. Khi biết số token đã tiêu, báo lại để
kế toán tải: `api_pool.danh_dau_thanh_cong(db, key, tokens=<so_token>)`. Admin đặt
`rpm_limit`/`tpm_limit` cho từng key ở `/admin` → APIKEYS.

## 3. `routes.py`

```python
from fastapi import APIRouter, Depends, Request
from server.auth.session import require_login

router = APIRouter(tags=["seedance"])


@router.get("")                       # KHÔNG viết "/seedance" ở đây
def page(request: Request, user: str = Depends(require_login)):
    ...
```

Router **không tự viết prefix**. Nền tảng gắn prefix từ
`MANIFEST.route_prefix` lúc mount. Nhờ vậy đổi đường dẫn chỉ sửa manifest, và
không bao giờ xảy ra chuyện manifest khai một đường mà route nằm ở đường khác.

Mọi route hiển thị dữ liệu **phải có `Depends(require_login)`**.

---

## 4. Kiểm tra

```powershell
python -m pytest tests/test_60_app_registry.py -q
python -m pytest -q
```

`test_60` tự bắt các lỗi hay gặp:

| Lỗi | Test bắt được |
|---|---|
| Quên `manifest.py` | `test_every_apps_subfolder_has_a_manifest` |
| Trùng `route_prefix` | `test_route_prefixes_are_unique` |
| Trùng `job_types` | `test_job_types_are_unique_across_apps` |
| Khai `job_types` mà quên `credit_cost` | `test_job_type_without_price_is_refused` |
| Không có mục nav → không ai vào được | `test_every_enabled_app_is_reachable_from_the_sidebar` |
| Sửa nền tảng để app chạy | `test_no_app_slug_is_hardcoded_in_the_platform` |

Sau đó chạy uvicorn, mở `/` — app mới phải tự hiện trên trang chủ và sidebar
mà bạn **không sửa gì** ở giao diện.

---

## Ba lỗi hay gặp

**Quên `credit_cost` khi có `job_types`.** Nền tảng sẽ **từ chối chạy job**
đó. Đây là cố ý: job không tra được giá mà vẫn chạy là job miễn phí ngoài ý
muốn, và với API tính theo giây thì đó là mất tiền thật.

**Viết `@router.get("/seedance")` trong routes.py.** Thành ra
`/seedance/seedance`. Route trong app luôn viết đường dẫn tương đối.

**Chạy việc dài ngay trong request.** Cloudflare cắt ở **100 giây** (lỗi 524)
dù bot vẫn đang chạy tốt. Việc dài hơn vài giây phải đi qua hàng đợi job.
App cũ `apps/demo` từng chạy trực tiếp trong request được **chỉ vì** nó mất vài
mili-giây — đừng lấy đó làm mẫu cho app thật.

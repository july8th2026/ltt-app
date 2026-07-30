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
└── jobs.py          phần xử lý thật
```

Cách nhanh nhất: **copy `apps/demo/` rồi sửa**. Nó là khuôn mẫu tối thiểu và
luôn chạy được.

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
    notes="",
)
```

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
`apps/demo` chạy trực tiếp trong request được **chỉ vì** nó mất vài
mili-giây — đừng lấy đó làm mẫu cho app thật.

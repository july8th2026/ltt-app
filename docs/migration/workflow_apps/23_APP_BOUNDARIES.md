# 23 — RANH GIỚI APP (đóng băng)

Đóng băng 2026-09-09, trên hợp đồng app hiện hành (`platform_core/registry.py`
@ `05464239`). Không viết dòng App nào trước khi tệp này và `24_NODE_CONTRACTS.md`
đứng yên.

## Không va chạm — đo, không đoán

| Slug | Có sẵn? | `route_prefix` | Có sẵn? |
|---|---|---|---|
| `transcript` | **trống** | `/transcript` | **trống** |
| `audio_pause` | **trống** | `/audio-pause` | **trống** |
| `gem` | **trống** | `/gem` | **trống** |
| `video_assembly` | **trống** | `/video-assembly` | **trống** |

21 `route_prefix` đang dùng, không cái nào trùng.

## `group="Workflow"` — có sẵn, không cần sửa nền tảng

`AppManifest.group` (`registry.py:476`) đã tồn tại và **điều hướng đọc nó**:
*"nhóm hiển thị ở HEADER (dropdown theo nhóm) … nền tảng gom app theo `group`.
Chỉ ảnh hưởng ĐIỀU HƯỚNG/hiển thị, không đụng logic app."*

Giá trị đang dùng: `AI Studio`(2) · `Chat`(2) · `Video`(4) · `Ảnh`(2) · `AI` ·
`VPS`. Thêm `Workflow` là **thêm dữ liệu**, không phải thêm mã.

⇒ **Yêu cầu "một khu vực tên Workflow" của người dùng đạt được bằng bốn chữ
trong bốn bản khai.** Không Hub, không trang mới, không hardcode slug.

⛔ Hệ quả phải giữ: **không** build "Workflow Hub" ở V1. Pack cho phép build khi
*"UX hiện tại chưa tạo được tab/area Workflow đúng nghĩa"* — điều kiện ấy **không
đúng**, đo được ngay trên mã. Xem `26_WORKFLOW_UX.md`.

## Bốn App — bảng ranh giới

| | `transcript` | `audio_pause` | `gem` | `video_assembly` |
|---|---|---|---|---|
| `group` | `Workflow` | `Workflow` | `Workflow` | `Workflow` |
| `job_types` | `("transcript.run",)` | `("audio_pause.run",)` | `("gem.run",)` | `("video_assembly.run",)` |
| `requires` | `("gpu",)` | `("gpu",)` | **`("api",)`** | `("gpu","ffmpeg")` |
| `lifecycle` | `development` | `development` | `development` | `development` |
| `surface` | `customer` | `customer` | `customer` | `customer` |
| `public` | `False` | `False` | `False` | `False` |
| `enabled` | `True` | `True` | `True` | `True` |
| `api_exposed` | `False` | `False` | `False` | `False` |
| `capabilities` | `("audio",)` | `("audio",)` | `("AI Text",)` | `("AI Video",)` |

⛔ **Bốn cột cuối đóng ở V1 là chủ ý, không phải quên.** `public=False` +
`lifecycle="development"` giữ App khỏi catalog công khai trong khi parity chưa
đóng; `api_exposed=False` giữ nó khỏi `/api/v1` (và dù có bật thì vẫn còn hai
cổng nữa — `LTT_PUBLIC_API` và `LTT_PUBLIC_API_TOOLS`). Mở từng cổng **sau** khi
parity đóng, mỗi lần một cổng.

## Bố cục trong từng App

```
apps/<slug>/
├── manifest.py     bản khai — nền tảng CHỈ đọc tệp này
├── routes.py       CHỈ HTTP: đọc request · quyền/CSRF · gọi service · dựng phản hồi
├── jobs.py         handler chạy trong worker
├── services/       nghiệp vụ trích từ legacy theo SOURCE MAP
├── templates/
└── static/         khi cần
```

Trần cứng của `routes.py`: **900 dòng / 30 handler** (`tools/lint_app_contract.py`).
⛔ `routes.py` **không** chứa nghiệp vụ — kho này đã có một tệp route 1.799 dòng
vì hợp đồng cũ không nói nghiệp vụ nằm đâu.

**Không** `tables.py` cho cả bốn App ở V1: trạng thái của một lượt chạy là
`Job` + `Artifact`, và đó là điểm chính của việc bỏ máy trạng thái Sheet.

## Dùng lại của nền tảng — gọi, đừng chép

| Việc | Gọi cái này |
|---|---|
| kiểm tệp/ảnh tải lên | `platform_core.image_input.validate_reference` |
| ffmpeg / cắt / ghép / mã hoá | `platform_core.media` |
| lưu trữ + artifact | `platform_core.storage` · `workflow/artifact.py` |
| nộp job + giữ credit (một giao dịch) | `platform_core.job_submit.submit_with_credit` |
| giành job | `platform_core.jobs.claim` (`FOR UPDATE SKIP LOCKED`) |
| suất tài nguyên / GPU | `ToolSpec.admission_resource` + `admission_slots` · `gpu_lease` |
| đường dẫn bundle React | `platform_core.frontend_bundle.bundle_assets` |

⛔ **Đừng neo đường dẫn bằng `Path(__file__).parents[n]`** — đếm sai cấp là hỏng
**lặng lẽ**: trang vẫn trả 200, chỉ là vỏ trống.

## STT — một service, bốn hồ sơ

Theo `07_CROSS_BOT_SYNTHESIS.md` §2. Ba App cần STT với **ba hồ sơ tham số khác
nhau**, và khác biệt ấy quyết định đầu ra.

```
platform_core/  (hoặc thư viện dùng chung)
└── stt/
    ├── service.py       nạp model · cache theo hash audio · một điểm gọi
    └── ho_so.py         HO_SO = {"transcript": {...}, "pause": {...},
                                  "video": {...}, "video_eval": {...}}
```

⛔ **Không có "tham số mặc định hợp lý".** App khai tên hồ sơ; service từ chối
nếu tên không có. Một mặc định ngầm ở đây là một quyết định về **đầu ra** mà
không ai ký.

⚠️ Đây là **thay đổi Core duy nhất** mà bốn App được phép đòi ở V1, và nó qua
được cửa vì ≥2 App cần **và** ngữ nghĩa đã đo. Mọi thứ khác ở lại trong App.
Theo MASTER-GUARDRAILS #15, nó là **một changeset riêng**, không trộn vào App nào.

## Một trang sequence cho mỗi App

Cùng một hình dạng, vì bất biến #2 đòi thế:

```
GUI  POST /<prefix>/tao   ─┐
Node agent executor step  ─┼→ services/<domain>.py  →  job_submit.submit_with_credit()
API  (đóng ở V1)          ─┘        (CÙNG hàm)              job_type="<slug>.run"
                                                                   │
     jobs.claim() ──→ worker ──→ apps/<slug>/jobs.py::handle ──→ services/<domain>
                                                                   │
                                        Artifact ("<backend>:<key>") + credit_cost thật
```

`transcript` · `audio_pause` · `video_assembly`: xin suất GPU qua
`admission_resource`. `gem`: **không xin suất nào** — nó gọi `text.chat` qua
`runtime_noi_bo`, và admission của chính tool đó lo phần giành chỗ
(`09_QUYET_DINH_GEM_BO_TRINH_DUYET.md`).

⭐ Bất biến kiểm được: **GUI, Node và API gọi CÙNG một hàm service và tạo CÙNG
một `job_type`.** Đó là thứ phép kiểm hợp đồng chốt được, chứ không phải một lời
hứa trong tài liệu.

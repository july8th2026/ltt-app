# 03 — Kiến trúc đích

## 1. Lựa chọn kiến trúc

**Capability-preserving replatform:** giữ ≥90% năng lực có giá trị với khách,
nhưng viết lại ranh giới identity/data/job/credit/provider/storage theo LTT.

```text
Browser
  └─ /prompt-ai-ommi (Jinja + React/TS island khi state editor cần)
      ├─ session auth + CSRF + app access
      ├─ app service: schema, prompt composer, preflight, export
      ├─ AppProject: project/library/catalog/version metadata
      ├─ Storage: input/reference/output owner-scoped
      └─ Job queue: director/storyboard/batch/handoff
           ├─ credit hold → provider call → settle/refund
           ├─ APIKEYS/provider registry/model capability
           └─ artifacts + progress + retry/idempotency
```

Không có SQLite, task map trong web, API key app, file output trong source hay
import runtime từ `D:\BOT GEMINI`.

## 2. Cấu trúc app dự kiến

```text
apps/prompt_ai_ommi/
├── __init__.py
├── manifest.py
├── routes.py
├── schemas.py
├── jobs.py
├── cost.py
├── project_schema.py
├── services/
│   ├── prompt_composer.py
│   ├── preflight.py
│   ├── director.py
│   ├── consistency.py
│   ├── storyboard.py
│   ├── package_io.py
│   └── handoff.py
├── prompts/                 # fragment/template có provenance
├── templates/prompt_ai_ommi.html
└── frontend/                # chỉ khi editor state cần React island
```

Mặc định toàn bộ thay đổi nằm trong thư mục app. Nếu spike chứng minh cần sửa
`platform_core/` hoặc `server/`, dừng phase app và mở một contract-gap ticket
riêng; không đi vòng bằng cross-app/private import.

## 3. Mô hình dữ liệu

`AppProject` là container metadata JSON, binary luôn ở Storage:

| Record kind | Payload chính |
|---|---|
| `production` | title, brief, preferences, active scene/storyboard IDs |
| `scene_set` | ordered scenes, anchors, prompt state, schema version |
| `storyboard` | scene refs, layout, generation refs, selected versions |
| `snapshot` | immutable reference tới revision cần phục hồi |
| `user_library` | asset metadata/storage keys, private snippet/style refs |
| `published_catalog` | admin-owned, status/version/provenance; user read/clone |
| `preferences` | theme, locale, defaults; không chứa key/token/secret |

- Giới hạn mềm 750 KiB/record, trước trần AppProject 1 MiB.
- Media không base64 trong JSON; chỉ storage key + MIME/size/hash.
- Mọi mutation dùng `user_id + app_slug + revision`.
- Snapshot lớn tách record; không nhồi toàn bộ lịch sử vào một payload.
- Import luôn dry-run, schema allowlist, cap số record/file/bytes và owner mới.

## 4. Job/Tool contract đề xuất

| Job type | Công dụng | ToolSpec |
|---|---|---|
| `prompt_ai_ommi.direct` | brief/assets → prompt package/scenes | `text.prompt_package` |
| `prompt_ai_ommi.storyboard` | scene prompts → storyboard artifacts | `image.storyboard` |
| `prompt_ai_ommi.batch` | bounded multi-brief generation | không public v1 |

Handoff ảnh/video phải gọi ToolSpec/job đã đăng ký của app hiện có, không import
private handler của `taoanh`/`taovideo`. P0 phải spike khả năng submit ToolSpec
từ app. Nếu hợp đồng generic chưa tồn tại, đó là contract gap thật cần quyết
định nền tảng trước khi tiếp tục P7.

## 5. Pricing và provider

- Preview/bundle local deterministic: 0 credit, rate-limit chống abuse.
- Director/storyboard: giá theo model/token/output count, quote trước.
- Batch: reserve trần toàn batch; actual không vượt hold; item lỗi có quyết toán
  minh bạch, không chạy ngoài ngân sách.
- Model selector lấy từ provider registry, chỉ model active/capability phù hợp.
- Secret chỉ giải mã trong worker đúng lúc gọi provider; log/error phải redact.

## 6. Security invariants

1. Hai user không thể list/read/update/delete/clone/export asset của nhau.
2. Published item chỉ read/clone; chỉ admin publish hoặc sửa bản gốc.
3. Handoff chỉ nhận storage/artifact reference cùng owner.
4. Mọi generate cần CSRF, rate-limit, quote/hold và dedupe key.
5. Import chống ZIP bomb, path traversal, MIME spoof và entity explosion.
6. Export không chứa file path, secret, internal provider response hay PII.
7. Admin ops có dry-run/audit; destructive action chạy job, không request sync.
8. Telemetry không gửi prompt/media mặc định.


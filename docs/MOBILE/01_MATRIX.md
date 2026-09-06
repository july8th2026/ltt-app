# Mobile Capability Matrix — bề mặt khách hàng

Sinh 2026-09-05 từ `platform_core/registry.discover()` lúc **runtime**, không từ
`ls apps/`. Nhánh `phien/mobile-v1` @ `911cd142`.

⛔ Đừng chép số từ bảng này đi nơi khác. Cách dựng lại:

```powershell
python tools\mobile_qa.py kiem-ke
```

## Toàn bộ app trong registry — 16

| slug | surface | lifecycle | public | enabled | route | có UI khách? |
|---|---|---|---|---|---|---|
| `agent` | customer | development | ✅ | ✅ | `/agent` | ✅ React canvas |
| `anhnoibo` | customer | development | ✅ | ✅ | `/anhnoibo` | ❌ **404** — capability-only |
| `autosubvideo` | customer | development | ✅ | ✅ | `/autosubvideo` | ✅ React studio |
| `chataistudio` | customer | development | ✅ | ✅ | `/chataistudio` | ✅ template |
| `chatltt` | customer | development | ✅ | ✅ | `/chatltt` | ✅ React |
| `ltt_llm` | customer | development | ❌ | ✅ | `/ltt-llm` | ❌ 404 — capability-only |
| `ltt_voice` | customer | **released** | ✅ | ✅ | `/ltt-voice` | ✅ template |
| `nexus` | customer | released | ✅ | **❌** | `/nexus` | ❌ 404 — `enabled=False` |
| `prompt_ai_ommi` | customer | **released** | ✅ | ✅ | `/prompt-ai-ommi` | ✅ React |
| `qualitylab` | **admin** | internal | ❌ | ✅ | `/qualitylab` | ❌ 404 — nội bộ |
| `taoanh` | customer | development | ✅ | ✅ | `/taoanh` | ✅ template |
| `taoclipngan` | customer | development | ✅ | ✅ | `/taoclipngan` | ✅ template |
| `taovideo` | customer | **released** | ✅ | ✅ | `/taovideo` | ✅ template |
| `thumbnail` | customer | development | ✅ | ✅ | `/thumbnail` → `/taoanh/thumbnail` | ✅ template (308) |
| `upscalevideo` | customer | **released** | ✅ | ✅ | `/upscalevideo` | ✅ template |
| `vps` | customer | development | ✅ | **❌** | `/vps` | ❌ 404 — `enabled=False` |

**Loại khỏi phạm vi mobile — 5, đều có lý do đo được (HTTP 404 tại prefix):**
`anhnoibo` và `ltt_llm` là capability-only (không có `routes.py` phục vụ trang);
`nexus` và `vps` có `enabled=False` nên nền tảng dán nhãn "đang xây";
`qualitylab` là `surface=admin`. **Không tạo UI cho nhóm này** — pack cấm dựng
trang giả để đạt checklist.

## Bề mặt nền tảng (chrome) — 7 route

Lấy từ chính HTML trang chủ, không từ danh sách chép tay.

| route | vai trò | profile |
|---|---|---|
| `/` | catalog | STANDARD |
| `/jobs`, `/jobs/{id}` | lịch sử job | STANDARD |
| `/nap` | nạp credit | STANDARD_FORM |
| `/developers` | developer console | CONTROL_PANEL |
| `/gia-api` | bảng giá API | STANDARD |
| `/huong-dan` | tài liệu | STANDARD (**có `<code>` tràn**) |

## Phân loại theo behavior profile

| profile | app |
|---|---|
| CHAT | `chatltt`, `chataistudio` |
| AUDIO_STUDIO | `ltt_voice` |
| MEDIA_GENERATOR | `taovideo`, `taoanh`, `thumbnail`, `taoclipngan`, `upscalevideo` |
| TIMELINE_EDITOR | `autosubvideo` |
| CANVAS_EDITOR | `agent` (React Flow) |
| PROJECT_STORYBOARD | `prompt_ai_ommi` |
| STANDARD / CONTROL_PANEL | chrome nền tảng |
| CAPABILITY_ONLY / ADMIN | `anhnoibo`, `ltt_llm`, `qualitylab`, (+`nexus`,`vps` khi bật) |

## Công nghệ frontend

- **React (Vite)** — 4 gói ở `frontend/`: `agent-canvas`, `autosub-studio`,
  `chatltt`, `prompt-ai-ommi`. Bundle nằm ở `server/static/<ten>/` và **được
  theo dõi trong git** (worktree mới không cần build lại để chạy).
- **Jinja template + JS thuần** — mọi app còn lại; CSS chung ở
  `server/static/ltt.css` (3.183 dòng).

## Đường media — cột quyết định kiến trúc Phase B

| app | route media | Range | đọc toàn tệp vào RAM |
|---|---|:--:|:--:|
| `taovideo` | `routes.py:621` | ✅ tự viết | ✅ `f.read(length)` |
| `taoclipngan` | `routes.py:521` | ✅ tự viết | ✅ |
| `upscalevideo` | `routes.py:780` | ✅ tự viết | ✅ |
| `agent` | `routes/workspace.py:149` | ✅ tự viết | ✅ |
| `autosubvideo` | `routes.py:858` | ✅ tự viết | ❌ (có `_iter_storage_range`) |
| **`ltt_voice`** | `routes/_p_audio.py:90` | **❌ KHÔNG** | ✅ **toàn tệp** |
| **`chatltt`** | `routes/_p_media.py:143` | **❌ KHÔNG** | ✅ **toàn tệp** |

**5 bản chép của cùng một bộ phân tích Range + 2 app không có Range.**
Chi tiết khiếm khuyết ở `02_BASELINE.md` mục 1.

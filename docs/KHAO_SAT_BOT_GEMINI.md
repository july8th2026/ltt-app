# Khảo sát BOT GEMINI — kho module nguồn

> Lập ngày 2026-07-31. Chỉ đọc, không sửa gì bên `D:\BOT GEMINI`.
> Mục đích: sau này khi cần dựng một tool trên nền tảng, mở file này ra là biết
> **module nào có sẵn, nó làm gì, nằm ở đâu, cần gì để chạy, và có nên đưa lên
> nền tảng thương mại hay không.**
>
> **KHÔNG có giá trị bí mật nào trong file này.**

---

## 0. Quy tắc bất di bất dịch khi làm việc với BOT GEMINI

`D:\BOT GEMINI` **đang vận hành thật** (13 tài khoản người dùng, 6 hồ sơ Chrome,
32 lô batch trong dữ liệu). Vì vậy:

1. **Chỉ đọc. Không sửa, không tạo, không xoá, không chạy script ghi file.**
2. Muốn dùng một module → **copy tài nguyên liên quan sang `D:\LTTSTUDIOSAPP`**
   rồi làm việc trên bản copy.
3. Không bao giờ `import` trực tiếp từ `D:\BOT GEMINI` sang dự án này. Hai cây
   mã nguồn phải độc lập hoàn toàn — dính nhau là mai sau sửa một bên vỡ bên kia.
4. Bản copy nằm ở đâu, ngày nào, từ commit nào → ghi lại trong tài liệu của
   module tương ứng.

---

## 1. BOT GEMINI là gì

| Hạng mục | Nội dung |
|---|---|
| Tên tự đặt | **LTT AI Studio v5.1** (trùng tên với dự án này — cần đặt lại tên để khỏi nhầm) |
| Kiểu | Công cụ nội bộ, chạy trên máy cá nhân, nhiều nhân viên dùng chung |
| Nền | FastAPI + Uvicorn + Jinja2 + Alpine.js (không build, không framework JS) |
| Lưu trữ | **File JSON trong `data/`, không dùng database** — ghi nguyên tử (temp → rename) |
| Đăng nhập | bcrypt 12 vòng + JWT trong RAM, vai trò `admin`/`user`, trạng thái `pending`/`approved`/`rejected` |
| Chạy job | Hàng đợi asyncio trong tiến trình, worker pool, SSE đẩy tiến độ về trình duyệt |
| Điểm mạnh | **Đã có sẵn nhiều người dùng, hạn mức, hàng đợi, phân quyền theo module, kho artifact** |
| Điểm yếu với mục tiêu thương mại | Phụ thuộc Chrome/cookie, chạy trên máy để bàn có GPU, không thiết kế để mở ra Internet |

### Thứ đáng giá nhất của BOT GEMINI không phải là các module

Mà là **hạ tầng nhiều người dùng** — đúng phần `LTTSTUDIOSAPP` đang thiếu:

| Thành phần | Đường dẫn | Dùng để làm gì |
|---|---|---|
| Model người dùng | `app/models/user.py` (181 dòng) | vai trò, trạng thái duyệt, nhóm quyền, **hạn mức theo ngày** (browser/cookie/api) + số đã dùng |
| Model job | `app/models/job.py` (116 dòng) | `waiting/running/done/error/skipped`, `user_id`, tiến độ, retry, hash chống trùng |
| Hàng đợi job | `app/services/job_queue.py` (353 dòng) | worker pool, retry luỹ thừa, cửa sổ chống trùng, SSE, khôi phục job cũ từ store |
| Phân quyền module | `app/services/workspace_policy.py` (462 dòng) | mỗi user × mỗi module = `ENABLED` / `LOCKED` / `HIDDEN` |
| Nhóm quyền | `app/services/role_groups.py` (214 dòng) | gộp module thành gói (`video_pro`, `music`…) để gán hàng loạt |
| Chặn vượt hạn mức | `app/services/quota_guard.py` (15 dòng) | trừ 1 lượt + trả HTTP 429 — **một bản duy nhất, trước đó bị copy-paste ở 7 nơi** |
| Mô hình giá | `app/modules/seedance_video/cost.py` (134 dòng) | tính tiền theo token thật của nhà cung cấp, có **markup %**, quy ra VND, **giữ chỗ trước khi chạy** (`reserve_check`) |
| Kho artifact | `app/storage/artifact_store.py` (349 dòng) | quản lý file kết quả |
| Kho job | `app/services/job_store.py` + `app/storage/job_store.py` | ghi job xuống SQLite để sống qua restart |
| Cấu hình R2 | `app/services/r2_config.py` (100 dòng) | đã có sẵn đường sang object storage |
| Bộ lập lịch | `app/services/scheduler.py` (357 dòng) | APScheduler, dọn output + prune DB hàng ngày |

**Kết luận quan trọng nhất của cả cuộc khảo sát:** BOT GEMINI mạnh đúng chỗ
`LTTSTUDIOSAPP` yếu (người dùng, hàng đợi, hạn mức, giá), và yếu đúng chỗ
`LTTSTUDIOSAPP` mạnh (bảo mật khi mở ra Internet, kỷ luật test, bộ cài/rollback,
hợp đồng app có test chốt). Nên hướng đi hợp lý là **mang khái niệm hạ tầng từ
BOT GEMINI sang, viết lại theo hợp đồng chặt của LTTSTUDIOSAPP** — không phải
bê nguyên code, cũng không phải nghĩ lại từ đầu.

---

## 2. Danh mục module — đánh giá khả thi

Thang điểm: ⭐⭐⭐ nên làm sớm · ⭐⭐ làm được, để sau · ⭐ rủi ro cao · ⛔ không nên đưa lên nền tảng thương mại

### Nhóm A — Chỉ gọi API bên ngoài (`requires=("api",)`) → chạy được trên VPS

| Module | Dòng | Làm gì | Đánh giá |
|---|---|---|---|
| `seedance_video` | 5.508 | Sinh video AI qua BytePlus ModelArk (Seedance 2.0/fast/mini), text/ảnh/video/audio → video | ⭐⭐⭐ **Ứng viên số 1.** Đã có `cost.py` tính tiền theo token thật + markup + VND + giữ chỗ; `runner.py` có ngân sách poll; `errors.py` phân loại lỗi; có `tests/`. Đây là khuôn mẫu chuẩn cho mọi tool tính phí về sau. |
| `plenx` | 2.731 | Sinh video qua plenxai.com (Seedance + Kling 3.0) | ⭐⭐⭐ Bản sao song song của `seedance_video`, cùng cấu trúc → port hai cái một lượt rẻ hơn nhiều so với port rời. |
| `thumbnail_api` | 1.418 | Tạo thumbnail YouTube qua Gemini Image API | ⭐⭐⭐ Nhẹ, chạy nhanh (không đụng trần 100 giây), kết quả là ảnh nhỏ (không đụng trần 100 MB). **Ứng viên tốt nhất cho tool tính phí ĐẦU TIÊN.** |
| `gemini_video` | 908 | Sinh video qua Gemini API | ⭐⭐ |
| `gemini_api_chat` | 763 | Chat Gemini nhiều lượt qua pool API key | ⭐⭐ Chạy được nhưng giá trị thương mại thấp — khách có sẵn ChatGPT/Gemini miễn phí. |
| `gemini_image` | 310 | Sinh ảnh qua Gemini API (Imagen 3 / Flash) | ⭐⭐ Nhỏ, dễ port. |
| `youtube_script` | 139 | Sinh kịch bản video YouTube có cấu trúc | ⭐⭐ Rất nhỏ — hợp làm tool thứ hai để kiểm chứng hợp đồng app. |
| `seedance` (Prompt Studio) | **28.685** | Studio soạn prompt chuyên nghiệp: quản lý asset, brief/script, AI đạo diễn, biên tập nhiều cảnh, xuất bản, theo dõi chi phí, nhiều LLM (Gemini/OpenAI/Anthropic) | ⭐⭐ Giá trị cao nhưng **111 file, có database riêng, i18n riêng** → port nguyên là một dự án riêng, không phải một module. Để sau cùng. |

### Nhóm B — Cần FFmpeg (`requires=("ffmpeg",)`) → chạy được trên VPS nếu đủ CPU

| Module | Dòng | Làm gì | Đánh giá |
|---|---|---|---|
| `auto_sub_video` | 6.454 | Ghi phụ đề vào video từ transcript, xuất ASS/SRT, có kho template style, kiểm tra font | ⭐⭐⭐ **Không đụng điều khoản của ai** — thuần xử lý file, khác biệt rõ so với đối thủ. Nhưng file vào/ra lớn → **bắt buộc có hàng đợi job + object storage trước**. |
| `concat_pro` | 857 | Nối video theo thư mục, pipeline 3 tầng (FAST/SAFE/ULTRA-SAFE), mã hoá GPU, có worker riêng | ⭐⭐ |
| `video_chain` | 456 | Nối/chuỗi video T2V → I2V bằng FFmpeg | ⭐⭐ Nhỏ nhất trong nhóm — hợp làm tool đầu tiên chứng minh đường ống file lớn. |

### Nhóm C — Bắt buộc GPU (`requires=("gpu",)`) → **chỉ chạy trên máy có card, không chạy trên VPS**

| Module | Dòng | Làm gì | Đánh giá |
|---|---|---|---|
| `cut_clip_short` | 2.884 | Cắt short từ video dài bằng AI: Whisper medium (fp16) + YOLOv8 + mã hoá NVENC | ⭐⭐ Cấu hình ghi rõ trong `config.py`: tối ưu cho **i9-10900K + RTX 2060 6GB**, tối đa 2 job GPU đồng thời, upload tối đa **2 GB**. Đây là lý do chính đáng nhất để máy nhà tồn tại trong hệ thống. |
| `video_upscale` | 1.460 | Nâng 480/720p → 1080p bằng Real-ESRGAN NCNN-Vulkan (offline) | ⭐⭐ Kèm `vendor/upscale` **48 MB** binary — phải copy theo, không cài bằng pip được. |

### Nhóm D — Dùng cookie / trình duyệt → **KHÔNG đưa lên nền tảng thương mại**

| Module | Dòng | Vì sao không |
|---|---|---|
| `whisk_nano` | 800 | Sinh ảnh bằng **cookie tài khoản Google Whisk**. Bán dịch vụ dựa trên cookie của tài khoản cá nhân là vi phạm điều khoản, và tài khoản bị khoá thì mất luôn dịch vụ đã bán. |
| Đã archive: `veo3`, `flow_text2video`, `flow_img2video`, `taoanh_flow`, `flow_thumbnail_youtubePRO`, `chatgpt_chat`, `suno`, `clone_video`, `thumbnail_pro`, `story_browser`, `character_browser`, `prompt_pipeline`, `prompt_pro`, `publish_facebook`, `publish_tiktok`, `automation_openclow` | — | Đều là tự động hoá trình duyệt/cookie. Mỗi job chiếm một hồ sơ Chrome thật, cần phiên desktop, cần IP dân dụng. Không nhân bản được, không bán được, và là mặt rủi ro pháp lý lớn nhất. Giữ ở BOT GEMINI để dùng nội bộ là đúng chỗ của chúng. |

### Nhóm E — Rủi ro đặc biệt

| Module | Dòng | Ghi chú |
|---|---|---|
| `codex` | 2.404 | Coding agent OpenAI Codex, mỗi user một kho project riêng, sandbox `workspace-write`. **Cho người ngoài chạy code trên máy chủ của mình là bề mặt tấn công lớn nhất có thể tạo ra.** Nếu làm, phải cô lập bằng máy ảo/container riêng, không phải bằng quyền thư mục. Để sau cùng, hoặc không làm. |

---

## 3. Cấu trúc chuẩn của một module BOT GEMINI

Biết cấu trúc này để lúc copy không bỏ sót:

```
app/modules/<module_id>/
├── __init__.py
├── manifest.py      ← module_id, display_name, job_family, requires_browser,
│                       artifact_types, config_schema
├── schemas.py       ← Pydantic request/response
├── api.py           ← FastAPI router
├── service.py       ← nghiệp vụ
├── runner.py        ← điều phối chạy (module chạy dài)
├── validators.py
├── adapters/
│   ├── browser_adapter.py   ← thao tác Selenium (nếu có)
│   ├── job_adapter.py       ← nối vào hàng đợi job
│   └── output_adapter.py    ← lưu file, sinh URL
└── tests/
```

**Khi copy một module sang `LTTSTUDIOSAPP`, phải mang theo:**

1. cả thư mục `app/modules/<id>/`;
2. các service dùng chung mà nó gọi (xem `import` trong `api.py`/`service.py` —
   thường là `job_queue`, `quota_guard`, `artifact_store`, `user_manager`);
3. model liên quan trong `app/models/`;
4. template + static của nó (trong `ui/` hoặc `app/resources/`);
5. tài liệu riêng trong `docs/` nếu có (ví dụ `docs/seedance_video/`,
   `docs/CODEX_MODULE_PLAN.md`);
6. binary/vendor đi kèm (ví dụ `vendor/upscale` 48 MB cho `video_upscale`).

---

## 4. Tài liệu đáng đọc bên BOT GEMINI

| File | Dòng | Nội dung |
|---|---|---|
| `docs/LTT_AI_Studio_Architecture.txt` | **15.272** | Sinh tự động từ mã nguồn. Mục 6 = danh mục 24 module; mục 9 = hàng đợi job; mục 12 = phân quyền; mục 14 = các quy tắc kiến trúc; mục 15 = danh sách file dữ liệu. **Đọc mục 14 trước tiên.** |
| `docs/WHOLE_BOT_AUDIT_2026-07-24.md` | — | Audit toàn hệ thống |
| `docs/CODEX_MODULE_PLAN.md` | — | Thiết kế module Codex |
| `docs/seedance-multiuser.md` | — | Cách seedance xử lý nhiều người dùng |
| `CODEX_STUDIO_FULL_BUNDLE.md` | 456 KB | Bundle đầy đủ của Codex Studio |

---

## 5. Nhắc lại — ba con số quyết định module nào chạy được ở đâu

| Trần | Giá trị | Module nào đụng |
|---|---|---|
| Upload mỗi request | **100 MB** (Cloudflare Free/Pro) | mọi module video: `cut_clip_short` (2 GB), `auto_sub_video`, `concat_pro`, `video_upscale` |
| Chờ phản hồi | **100 giây** | mọi module sinh video, mọi module FFmpeg, `video_upscale` |
| Cần GPU | — | `cut_clip_short`, `video_upscale` |

Nghĩa là: **tool đầu tiên nên chọn loại API-only, kết quả nhỏ, chạy nhanh**
(`thumbnail_api` hoặc `youtube_script`) để chứng minh chuỗi người dùng → job →
credit trước; nhóm video lớn chỉ làm được sau khi có hàng đợi job + object storage.

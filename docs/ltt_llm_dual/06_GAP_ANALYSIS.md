# 06 — Gap analysis (Gate R5): CURRENT → TARGET → GAP → REUSE → CHANGE → TEST

> Không có mã nào được viết ở gate này. Nguồn: `00`–`05` trong thư mục này.
> **Ý định chủ dự án cập nhật 2026-09-11 (trong phiên):** (1) 5060 Ti vừa lắp, **chưa hạng mục nào triển
> khai** ⇒ trạng thái máy B ở `00` là điểm xuất phát đúng, không phải lỗi; (2) **model ảnh vẫn dùng
> 3090** ⇒ 3090 = LTT-3.8 **+** model ảnh (chia thời gian), không chuyên dụng tuyệt đối.

| # | Miền | CURRENT (đo/đọc) | TARGET | GAP | REUSE (có sẵn) | CHANGE (delta) | TEST |
|---|---|---|---|---|---|---|---|
| G1 | Nền tích hợp | Multi-Job trên `master` 07/09, sau trunk 450 commit | Trên trunk `admin-mvp-v3` (docs/16) | rebase 9 commit + WIP; test 950–956 trùng số; alembic multi-head; Scheduler V1 đổi `jobs.py`/`job_runner.py` | commit T1–T8 | đánh số lại test, nối migration vào head `20260910_1000_job_scheduler_envelope`, hợp nhất tay 8 tệp | chạy lại test T1–T8 + test Scheduler (`test_971`) trên cây hợp nhất |
| G2 | Danh tính GPU | llama-swap + ComfyUI **không ghim**; ~11 chỗ đọc `dong[0]`/max mọi card | Mọi binding theo UUID; đo VRAM/util **theo UUID** | T1 chưa deploy; render/llm gateway mù card | T1 (UUID 3090), `platform_core/gpu.py` (có UUID, máy A) | ghim ComfyUI + 2 hồ sơ llama theo UUID; `busy.py`/`trong_tai.py`/`don_dep.py`/`tren_gpu.py` lọc theo UUID | test tĩnh: không còn `splitlines()[0]`/index trong đường máy B; nạp thật: `nvidia-smi` thấy đúng tiến trình ở đúng UUID |
| G3 | Hai model đồng thời | llama-swap không `groups` ⇒ một model một lúc | LTT-3.8 (3090) và LTT-3.5 (5060) **cùng nạp** | nạp 3.5 sẽ gỡ 3.8 | llama-swap v250 `groups swap:false` + `env` theo model + `hooks.on_startup.preload` | yaml: group hai model | nạp cả hai, `/running` = 2, gọi xen kẽ không đổi hồ sơ |
| G4 | Chia 3090: LTT-3.8 ↔ model ảnh | Render `GET /unload` llama-swap (**unload thủ công giết lượt đang chạy**); LLM `/free` ComfyUI; không khoá chung | Chia có trật tự, **không bao giờ giết lượt đang chạy** | không có drain; hai bên chỉ quan sát nhau | `nhuong_card.py`/`don_dep.py` (khung), sổ lease Multi-Job (T5) | → **quyết định D01** | tải hỗn hợp ảnh + LLM: 0 lượt LLM chết giữa chừng, 0 ảnh hỏng vì OOM |
| G5 | LTT-3.5 | không có model, không hồ sơ | Qwen3.5-9B + mmproj trên 5060 Ti, C4 | model, hồ sơ, alias, giá, ngân sách | khuôn `ngan_sach.py` theo model, `CUA_SO_THEO_MODEL`, bench m1/m2 | tải GGUF (ứng viên §2 của `05`), hồ sơ yaml, manifest/alias, bảng giá theo model | C1/C4 text + ảnh; VRAM đỉnh; 0 tràn |
| G6 | Hợp đồng công khai | `ltt_llm` / `ltt_llm_vision` (khách tự chọn text/vision) | `LTT-3.8` / `LTT-3.5` do khách chọn, không tự đổi | tên mới + di trú tên cũ | manifest dẫn xuất `/v1/models`, ChatLTT picker | → quyết định | `/v1/models`, ChatLTT picker, client cũ vẫn gọi được (nếu giữ bí danh) |
| G7 | Admission hai miền | một resource `llm_remote`, `slots=1`; ~15 chỗ giả định một model | `ltt_38_3090` và `ltt_35_5060` độc lập, mỗi miền slot + ngân sách KV | tổng quát hoá | `luat_nhan.xet()` thuần theo `ThamSo`, `xet_va_giu` khoá theo resource, `admission_token_pool` | số theo model trong `ngan_sach.py`, manifest khai 2 tool/2 resource hoặc 1 tool định tuyến theo model | C4+C4: tải 3.8 không lấy suất 3.5 và ngược lại |
| G8 | Engine 3.8 | `-np 1`, 2 hồ sơ, pool 204.800, draft-mtp | `-np 4 -kvu`, hồ sơ gộp, đích **262.144** | chưa đo 262K ở b10883; MTP + `-np 4` có bug mở (#27572: trả lời rỗng, một xác nhận đúng cấu hình ta) | M-1/M-2 (b10689), T13 kế hoạch | đo lại ở b10883 | nạp 262K + đo VRAM/Shared Usage; phép kiểm đúng/sai MTP từng slot |
| G9 | Gateway máy B | một bộ đếm slot mọi model, `MAX_DONG_THOI=1`, catalog cứng | sổ theo model, chốt fail-closed | T10 chưa làm | `GioiHan`, `LuongUpstream.close` | sổ token + slot **theo model**; `/health` theo model/UUID | test gateway; 429 ≠ 502 |
| G10 | Hủy | stream truyền; job chỉ hợp tác | hủy thật mọi giai đoạn | T11 | chuỗi hủy stream | đóng HTTP tới máy B khi `is_cancelled()` | `/slots` trống ≤ 2 s sau hủy |
| G11 | Đầu vào tệp | ảnh ≤4; ChatLTT có đường tệp→chữ (pypdf+markitdown) nhưng thuộc app | cùng hợp đồng đầu vào cho hai model | chưa là năng lực nền tảng; không XLSX/OCR/bảng | `trich_van_ban.py`, `chia_doan`/`tim_doan`; Docling (cộng đồng) | → quyết định phạm vi | PDF/DOCX/XLSX/đa tệp/ảnh+tệp; ghi nguồn; không rò chéo người dùng |
| G12 | Kho ấm RAM | mmap mặc định; `test_637` chỉ chặn cờ đã bị gỡ | nạp lại nhanh có số đo | chưa đo; phép chốt mù `--load-mode none/dio` | standby list 224 GB, `--cache-ram` | chỉnh `--cache-ram`; sửa `test_637` | đo lạnh vs ấm (K) |
| G13 | Tiền | bất biến đúng; một bảng giá | giá theo model | `gia_token.tinh()` không nhận model | toàn bộ `thanh_toan`/`credit` | tham số model vào giá | test tiền hiện có + ca LTT-3.5 |
| G14 | Quan sát | `/metrics` llama có; không UUID/pool | correlation id + tách app queue/admission/residency/engine | T12 | `/metrics`, `/slots`, `job_metrics` | thêm pool/UUID/residency | vết một request xuyên A→B |
| G15 | Cửa đồng bộ | WIP T9 **không chờ** (lệch TD-7 đã khoá) | theo quyết định | cần REOPEN hoặc sửa WIP | WIP T9 | → quyết định | test_958 (đánh số lại) |
| G16 | Ưu tiên | D-03 (tương tác > nền) vs Scheduler V1 (internal > external) — hai thang trên cùng hàng | một thang nhất quán | chưa hợp nhất | cả hai | → quyết định (sau rebase) | test_971 + test luật nhận |

## Việc đã được giải bằng kỹ thuật (không hỏi — ghi vào DECISION_LOG dạng TD)

- **Nền tích hợp = trunk `admin-mvp-v3`** — quy trình của kho (`docs/16_CAP_NHAT_VA_DEPLOY.md`), không phải lựa chọn.
- **Chạy hai model cùng lúc bằng llama-swap `groups swap:false` + `env CUDA_VISIBLE_DEVICES=<UUID>` + preload** — upstream đã giải, không tự viết.
- **Admission theo ngân sách KV ở tầng LTT vẫn bắt buộc** — b10883 và upstream mới nhất vẫn giết mọi slot khi tràn pool.
- **LTT-3.5 khởi đầu không `draft-mtp`**; LTT-3.8 chỉ bật MTP ở `-np 4` sau khi qua phép kiểm đúng/sai từng slot (#27572).
- **Không dùng unload thủ công của llama-swap khi còn lượt đang chạy** — drain do LTT làm.
- **Tệp: community-first** — Docling/markitdown, không tự viết parser.
- `--mlock` vô ích cho nạp lại (chỉ sống theo tiến trình) ⇒ kho ấm = standby list, có số đo mới tuyên bố.

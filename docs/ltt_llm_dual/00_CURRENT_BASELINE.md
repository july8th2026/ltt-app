# 00 — Recovery snapshot + baseline (Gate R0 / R2)

> Chụp **2026-09-11 16:05–16:20 giờ máy (UTC+7)**, phiên recovery `claude/ltt-llm-recovery-multimodel-110f65`.
> Chỉ ĐỌC: không đổi production, không đổi nhánh nào, không chạm cây làm việc của phiên khác.
> Mọi con số dưới đây là **ảnh chụp** — hỏi lại máy trước khi dùng (CLAUDE.md "HỎI MÁY CHỦ").

## 1. Lịch sử phiên trước

`PREVIOUS SESSION HISTORY: AVAILABLE` — phiên `LTT_LLM multi-job production audit`
(`local_829259d5-…`, cây `.claude/worktrees/ltt-llm-api-http-guide-a3e123`). Transcript kết thúc
bằng một chuỗi `Edit` không lời rồi *"You've hit your session limit"* (08:18Z). Chỉ dùng để hiểu ý
định; bằng chứng lấy từ git + máy.

Phiên `LTT Voice system reconciliation` (`local_b4b77ef6-…`) **không chứa mã Multi-Job** — dấu
vết duy nhất là lời báo "đang dùng máy B 10:40–11:30 để đo nhiều slot".

## 2. Git

| | Giá trị |
|---|---|
| Nhánh phiên này | `claude/ltt-llm-recovery-multimodel-110f65` @ `9e73bf1f` (sạch, không upstream) |
| `master` = `origin/master` | `9e73bf1f` (2026-09-07 15:22) |
| **Trunk thật** (`docs/16_CAP_NHAT_VA_DEPLOY.md`) | `admin-mvp-v3` local `34b4626e` (09-11 15:41) · `origin/admin-mvp-v3` `3100c317` (local đi trước 59) |
| Production máy A (`/health/version`) | `4a894036` (build 09-11 01:41, `commit_nguon=marker`) — **có** trong trunk, **không** có trong `master` |
| Nhánh Multi-Job | `claude/ltt-llm-multijob-audit-43efd3` @ `b3b11dbc` = `9e73bf1f` + 9 commit |
| WIP Multi-Job (chưa commit, cây `ltt-llm-api-http-guide-a3e123`) | 5 tệp, +91/−16: `job_runner.py`, `llm/tham_so_da_luot.py`, `runtime_noi_bo/luong.py`, `server/api/chat.py`, `server/api/streaming.py` |

🔴 **TARGET ASSUMPTION CONFLICT — nền nhánh.** Multi-Job (và nhánh phiên này) cắt từ `master`
07/09, **đi sau trunk 450 commit** (390 commit tới bản production). Trong khoảng đó trunk đổi đúng
các tệp Multi-Job sửa: `apps/ltt_llm/manifest.py`, `platform_core/job_runner.py`, `models.py` (+530),
`public_api/governance.py`, `registry.py` (+171), `server/api/streaming.py`, `tests/test_313`,
`tools/restore_drill_schema.py`; và thêm **Scheduler V1** (`platform_core/job_scheduler.py`, `jobs.py`
xếp hạng `priority_class internal > external`, cột envelope trên `jobs`) — cùng lãnh thổ "một nguồn
chân lý hàng đợi" với Multi-Job.

🔴 **Xung đột cơ học đã đo:**
- **Dải test 950–969 đã bị chiếm trên trunk** (`test_950_wf_*` … `test_969_agent_draft_v3.py`, chương
  trình Workflow). Test Multi-Job `test_950`–`test_956` trùng số ⇒ phải đánh số lại khi hợp nhất.
- **Alembic multi-head:** migration Multi-Job `20260911_1200_llm_multijob_ngan_sach.py` nối vào head
  của `9e73`; trunk có 17 migration mới, head `20260910_1000_job_scheduler_envelope.py`.
- Nhánh Voice (`claude/ltt-voice-reconciliation-165a40`) cũng chạm 7 tệp trùng.

Worktree đang tồn tại (13): xem `git worktree list`. Nhánh phiên này **chưa** được fast-forward lên
Multi-Job — thao tác đó bị bộ phân loại quyền chặn và việc chọn nền tích hợp là quyết định của chủ
dự án (→ DECISION_LOG).

## 3. Máy B — phần cứng (đo 16:08)

| | RTX 3090 | RTX 5060 Ti |
|---|---|---|
| UUID | `GPU-26623278-4fa5-82db-4306-237651b03e78` | `GPU-ebecd0a4-a8a7-14a5-dad1-21565f6dc1df` |
| PCI Bus ID | `00000000:02:00.0` | `00000000:81:00.0` |
| nvidia-smi index / CUDA | 0 / CUDA0 | 1 / CUDA1 |
| VRAM tổng / đang dùng | 24.576 / **182 MiB** (không model nào nạp) | 16.311 / 54 MiB |
| `display_active` | Disabled | **Enabled** (1024×768) |
| Tiến trình đồ hoạ trên card | dwm, explorer, SearchHost, StartMenu, M365Copilot, PhoneExperienceHost, LGHUB, Taskmgr, LogonUI (C+G, 0 MiB báo được) | dwm, LogonUI |
| PCIe lúc rảnh | gen1 ×16 | gen1 ×8 |

Driver **610.88**, CUDA UMD **13.3**, Windows 11 Pro 26200, khởi động lần cuối **09-11 08:56**.
CPU 2× Xeon E5-2678 v3 (24 lõi / 48 luồng). **RAM 223,9 GB** (7 thanh = 224 GB), trống 162,4 GB,
commit limit 237,9 GB / commit trống 125,4 GB.

🔴 **TARGET ASSUMPTION CONFLICT — RAM.** Tài liệu Multi-Job ghi "máy B 128 GB RAM" (TD-11,
`00_BASELINE.md` §3). Đo thật: **224 GB**. Prompt của chủ dự án đúng; tài liệu cũ đã cũ.

⚠️ Màn hình đã sang 5060 Ti, nhưng phiên desktop vẫn mở ngữ cảnh đồ hoạ trên 3090 ⇒ "3090 chuyên
dụng" **chưa** đúng tuyệt đối; lượng VRAM thật của các ngữ cảnh này chưa đo được (`[N/A]`).

## 4. Máy B — dịch vụ & tiến trình

| Dịch vụ (nssm) | Tiến trình | Cổng | GPU |
|---|---|---|---|
| `LTTLlamaSwap` | `H:\LTT_LLM\bin\llamaswap\llama-swap.exe --config H:\LTT_LLM\gateway\llama-swap.yaml` | 127.0.0.1:8280 | **không ghim** (không env, yaml không `CUDA_VISIBLE_DEVICES`) |
| `LTTLlmGateway` | `python -m llm_gateway.main` (env file `C:\ProgramData\LTTLlm\gateway.env`) | 0.0.0.0:8299 | — |
| `LTTRenderGateway` | `python -m render_gateway.main` | 0.0.0.0:8199 | — |
| `LTTComfyUI` | `E:\AI\ComfyUI main.py --port 8188 --reserve-vram 3` | 127.0.0.1:8188 | **không ghim** ⇒ log 08:58: `Device: cuda:0 NVIDIA GeForce RTX 3090` |

🔴 **TARGET ASSUMPTION CONFLICT — ComfyUI vẫn ở 3090.** Prompt đặt ComfyUI lên 5060 Ti; thực tế nó
đang mặc định `cuda:0` = 3090 (thấy cả hai card). `gateway.env` vẫn có `LTT_LLM_COMFY_URL` và
`LTT_LLM_VRAM_SACH_MB=2500` ⇒ cơ chế "gọi `/free` ComfyUI rồi chờ VRAM sạch" vẫn đang là đường sống.

**Và chiều ngược lại cũng đang sống:** `C:\ProgramData\LTTRender\gateway.env` đặt
`LTT_HO_DUNG_CARD=llm=http://127.0.0.1:8280/unload;video=` và `LTT_TRA_CARD_GIAY=60` ⇒ render gateway
**đuổi Qwen** (gọi `/unload` của llama-swap) khi cần card, rồi trả card sau 60 s rảnh. Log:
`2026-09-09 23:35:49 GET http://127.0.0.1:8280/unload 200`. ⇒ **Hôm nay 3090 được CHIA THỜI GIAN giữa
ComfyUI và Qwen bằng đuổi lẫn nhau**, không có khoá/lease chung — chỉ quan sát nvidia-smi + `/queue`
+ `/running`. Bản đồ mã đầy đủ: `03_GPU_RESOURCE_MAP.md`.

`gateway.env` (giá trị bí mật đã che): `LTT_LLM_MODELS=qwen38-api,qwen38-vision`,
`LTT_LLM_MAX_IMAGES=4`, `LTT_LLM_VRAM_SACH_MB=2500`, `LTT_LLM_RAM_TRONG_GB=48`,
`LTT_LLM_MAX_DONG_THOI=1`. Render gateway: `LTT_RENDER_RAM_TRONG_GB=48`, `LTT_RENDER_JOB_TIMEOUT_S=900`.

## 5. Máy B — engine

| | Giá trị |
|---|---|
| llama-server production | **b10883 (`91f6a6cf3`)**, Clang 20.1.8 — `phien_ban_ghim.json` cập nhật 09-11 00:20 |
| Bản lùi trên máy | `H:\LTT_LLM\bin\llamacpp.b10689` (+ `b10580`, không nạp được draft-mtp) |
| llama-swap | **v250 (`60226b6`)**, build 2026-08-14 |
| `llama-swap.yaml` deploy | sha256 `8A9362F6…2E2113`, 09-09 18:35 = `9e73` + `--metrics` |
| Bản vá P0 ghim UUID (Multi-Job T1) | **CHƯA deploy** |
| Model đang nạp | không (`/running` rỗng) |

🔴 **TARGET ASSUMPTION CONFLICT — build.** R-1 (đọc mã), M-1 và M-2 (đo VRAM/tok/s) của Multi-Job
đều trên **b10689**. Production đã sang **b10883** cùng ngày (phiên P6, quyết định riêng). Mọi kết
luận engine của Multi-Job phải kiểm lại trên b10883 trước khi dùng (→ `05_COMMUNITY_EVIDENCE.md`).

`UNKNOWN`: lần nạp production nào kể từ khi lắp 5060 Ti có chia lớp sang CUDA1 không — log
llama-swap mức `info` không in dòng thiết bị (0 lần "CUDA1" trong 146.445 dòng).

### Hồ sơ model đang deploy

| Hồ sơ | Model | `-c` | KV | `-np` | Khác | ttl |
|---|---|---:|---|---:|---|---:|
| `qwen38-api` | `Qwen3.8-27B-UD-Q4_K_M.gguf` | 204.800 | q4_0/q4_0 | 1 | draft-mtp n-max 2, `--jinja`, template froggeric, reasoning deepseek, `-fa 1 -ngl 999`, `--metrics` | 1800 |
| `qwen38-vision` | + `mmproj-F16.gguf` | 131.072 | q4_0/q4_0 | 1 | như trên | 600 |

Không `groups` ⇒ llama-swap chạy **một model một lúc**; đổi hồ sơ giết lượt đang chạy (đã đo 03/09).

### Tệp model trên `H:\LTT_LLM\models`

| Tệp | Cỡ | mtime |
|---|---:|---|
| `Qwen3.8-27B-UD-Q4_K_M.gguf` | 15,33 GB | 08-22 17:33 |
| `mmproj-F16.gguf` | 0,86 GB | 08-22 17:29 |
| `chat_template.jinja` | — | 08-22 18:00 |

🔴 **Không có Qwen3.5-9B** ở bất kỳ đâu dưới `H:\LTT_LLM` hay `E:\AI` (độ sâu 3).

SHA256 (tính trên máy B 16:24–16:25 bằng `Get-FileHash`; kho **chưa từng** ghi hash GGUF trước đó):

| Tệp | Byte | SHA256 |
|---|---:|---|
| `Qwen3.8-27B-UD-Q4_K_M.gguf` | 16.464.440.224 | `322E194FF79741C7BAA497C240F677F54B201B0EFAB44CA8E50F122B39123482` (62,4 s ≈ 264 MB/s) |
| `mmproj-F16.gguf` | 927.607.488 | `CBB841A9EE0636B2EC172F5BB8DF2EA8DFEB01E90FE7C6126581D662A0B4E43E` |
| `chat_template.jinja` | 26.681 | `6E1439C913AD7DF4A966493AD70DE7E7FC5A548D41BBE417C1571F766603629B` |
| `bin\llamacpp\llama-server-impl.dll` (b10883) | 8.893.440 | `6BA36E363FBBDEB8BFA11010EB95A4681A973D231A93388D7E0F0F52ED452D58` |
| `bin\llamacpp\ggml-cuda.dll` (b10883) | 144.907.776 | `B326D5607349D99AC952A340A8BD6B678B56E88C191748E45FB67BC30E0E278F` |
| `bin\llamaswap\llama-swap.exe` (v250) | 23.958.016 | `B2F318C3432A90BF09DDF02399F3AA05B6173A4298D67D61894754D490C9DDE3` |

⚠️ `llama-server.exe` chỉ là vỏ 9.216 byte — hash của nó **không** định danh build; dùng `-impl.dll`.
⚠️ Phép băm đã **đọc toàn bộ GGUF lúc 16:24** ⇒ page cache Windows có thể đang ấm. Phép đo "nạp lạnh
từ NVMe" về sau phải xả cache hoặc đo sau khởi động lại, và ghi rõ đã làm gì.

## 6. Máy A — production

`api_prod_canary.py trang-thai` (16:07): `/health/ready` 200, trang chủ/`/vps`/`/gia-api` 200,
`/developers` 303. Khu `/api/v1` không kiểm (không có `--token-file` — fail-closed đúng ý).

## 7. Chưa làm ở R0 (và vì sao)

- Test Multi-Job **không chạy lại** trong phiên này (fast-forward nhánh bị chặn quyền; không chạy test
  trong cây của phiên khác). Trạng thái xanh/đỏ của T1–T8 là **UNKNOWN cho tới khi chạy lại**.
- `/props` của engine (không model nào nạp — tự nạp model là thay đổi production).

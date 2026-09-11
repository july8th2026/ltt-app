# LTT LLM Dual-Model (Spec 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hai model nhà `ltt-3.8` (Qwen3.8-27B, RTX 3090, chia luân phiên với model ảnh) và `ltt-3.5` (Qwen3.5-9B, RTX 5060 Ti), mỗi model C4 với admission slot + ngân sách KV, một trọng tài residency 3090, tiền theo model — trên trunk `admin-mvp-v3`.

**Architecture:** Admission plane máy A là quyền quyết duy nhất (ExecutionLease + `llm_waiters` + `luat_nhan.xet()` thuần của Multi-Job, tổng quát hoá theo model qua `ToolSpec.admission_theo_model`; thêm máy trạng thái `gpu_residency` cho nhóm `rtx3090`). Máy B chỉ thực thi + chốt fail-closed: `llm_gateway` sổ theo model + lệnh residency; `render_gateway` bỏ tự đuổi; llama-swap v250 group `swap:false` nạp cả hai model, ghim UUID.

**Tech Stack:** Python 3.13, FastAPI/Starlette, SQLAlchemy + Alembic (PostgreSQL prod, SQLite test), httpx, llama.cpp **b10883**, llama-swap **v250**, Windows 11 (máy B qua **Nexus**), nssm.

**Spec:** `docs/superpowers/specs/2026-09-11-ltt-llm-dual-model-design.md` · Quyết định: `docs/ltt_llm_dual/DECISION_LOG.md` (D01–D09, L-1…L-12, TD-D1…TD-D11) · Bằng chứng: `docs/ltt_llm_dual/00`–`06`.

## Global Constraints

- Nền triển khai = trunk **`admin-mvp-v3`** (TD-D1). Không code trên `master`.
- ID công khai **đúng hai**: `ltt-3.8`, `ltt-3.5`; `ltt_llm`, `ltt_llm_vision`, `qwen38-vision` ⇒ `model_not_found` (D02). Id nội bộ: `qwen38-api`, `qwen35-api`.
- UUID 3090 `GPU-26623278-4fa5-82db-4306-237651b03e78` (PCI `00000000:02:00.0`); UUID 5060 Ti `GPU-ebecd0a4-a8a7-14a5-dad1-21565f6dc1df` (PCI `00000000:81:00.0`). Không dùng chỉ số GPU ở bất kỳ đâu trên đường máy B.
- Ngữ cảnh engine cả hai model `262144`; slot `4`; `-kvu`. LTT-3.8 KV q4_0 + mmproj + `draft-mtp n-max 2` (qua cổng MTP). LTT-3.5 **Q6_K** + mmproj, KV q8_0, **không** MTP.
- Giá (credit/1M vào/cache/ra): `ltt-3.8` 50/10/400 nhãn `ltt-vlm-2026-08-22` (giữ); `ltt-3.5` 13/3/20 nhãn `ltt-3.5-2026-09-11` (D07).
- Việc LLM nội bộ: app khai model, mặc định `ltt-3.5`; dịch prompt ảnh **không bao giờ** `ltt-3.8` (D09).
- Không lượt nào bị giết để đổi residency; không gọi unload thủ công llama-swap khi còn in-flight (L-9, TD-D5).
- Giữ tiền **sau** khi được nhận ở MỌI cửa; bận ⇒ không thu; không đo được `usage` ⇒ hoàn trọn (INV-003/011/012/MJ-1/MJ-2).
- `platform_core` không import `apps/` (`.importlinter`); app → nền tảng chỉ qua `ToolSpec`/`AppManifest`.
- Cấu hình ghi **không BOM**; `.ps1` **ASCII thuần**; không Python inline qua PowerShell (CLAUDE.md 1–3).
- Dải test của chương trình: **1200–1249** (đăng ký ở Task 1.2). Một tệp test: `python -m pytest tests/<tệp> -q`. ≥ 3 tệp: chạy `python tools\cua_so_yen.py trang-thai` trước, rồi `python -m pytest -n 6 …`. Vòng lặp tĩnh: `python tools\gate.py --vong-lap`. Trước khi báo xong một pha: `python tools\gate.py`. Không `pytest` toàn kho.
- Mỗi phép kiểm bất biến có **đối chứng**: tiêm bản cũ ⇒ phải ĐỎ.
- Bảng mới: `Store(...)` trong `platform_core/public_api/governance.py` + hàm dọn (hoặc lý do không cần) + tên UNIQUE vào `tools/restore_drill_schema.py`.
- Máy B: kênh chính **OpenSSH** — `ssh -i "%USERPROFILE%\.ssh\nexus_b" lengo@192.168.2.66` (đo 2026-09-11: sshd `Running/Automatic`, đăng nhập khoá 0,47 s; `lengo` thuộc Administrators ⇒ khoá ở `C:\ProgramData\ssh\administrators_authorized_keys`). Deploy gateway/yaml bằng `llm_gateway/deploy/deploy.ps1` có sẵn (SSH/scp + chụp `releases/auto-<ts>`). **Nexus** là kênh dự phòng (khi sshd chết) và cho việc cần LocalSystem. Việc nặng/dài chạy bằng Scheduled Task SYSTEM + `pythonw` (khuôn `docs/multijob/artifacts/m1/khoi_dong.ps1`), xong trước 01:00 (Windows Update). Không đo khi phiên khác đang dùng máy B.
- Commit sau mỗi task (tin nhắn kết thúc bằng dòng `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`), đẩy nhánh lên `origin`.

## File map

| Tệp | Trách nhiệm | Task | Nhóm |
|---|---|---|---|
| `llm_gateway/deploy/deploy.ps1` (có sẵn, SSH/scp) | deploy gateway + yaml, chụp release trước khi đè | 0.1 và mọi task deploy | DEPLOYMENT |
| `llm_gateway/deploy/gpu_may_b.json` (mới) | danh tính hai GPU — nguồn duy nhất | 0.3 | MACHINE B |
| `llm_gateway/deploy/llama-swap.yaml` | ghim UUID (P0), rồi hai hồ sơ + group + preload (P3) | 0.3, 3.3 | 3090 / 5060 |
| `render_gateway/deploy/cai_dat_dich_vu.ps1` | env `CUDA_VISIBLE_DEVICES=<UUID 3090>` cho `LTTComfyUI` | 0.3 | 3090 |
| `docs/ltt_llm_dual/artifacts/bench/*` (mới) | khuôn đo tổng quát hoá từ m1/m2 | 0.4, 3.2 | TEST |
| `platform_core/registry.py` | `AdmissionModel`, `ToolSpec.admission_theo_model`, `ToolSpec.admission_cho()`, `AppManifest.model_llm_noi_bo` | 2.1, 2.4 | CONTROL PLANE |
| `platform_core/llm/luat_nhan.py` | luật 0 `CHO_RESIDENCY` (`ThamSo.residency_mo`) | 5.3 | CONTROL PLANE |
| `platform_core/llm/admission.py` | đọc residency trong khoá resource | 5.3 | CONTROL PLANE |
| `platform_core/llm/tham_so_da_luot.py` | `luat_cho()` (từ WIP T9) | 1.5 | CONTROL PLANE |
| `platform_core/llm/residency.py` (mới) | máy trạng thái thuần + `buoc(db)` | 5.2, 5.5 | CONTROL PLANE |
| `platform_core/models.py` + `alembic/versions/…` | `gpu_residency`; `llm_waiters.model`, `cho_residency_s` | 5.1, 6.3 | MACHINE A |
| `platform_core/llm/canonical.py` | bảng id mới, model theo app, resource theo model | 2.3, 2.4 | CONTROL PLANE |
| `platform_core/llm/gia_token.py` | hai bảng giá, `tinh(su_dung, model)` | 2.5 | MACHINE A |
| `apps/ltt_llm/{manifest,features,ngan_sach,executor}.py` | hai model, số theo model | 2.3, 2.6 | MACHINE A |
| `server/api/{chat,streaming}.py`, `platform_core/runtime_noi_bo/luong.py`, `platform_core/job_runner.py`, `platform_core/agent/planner.py` | cửa dùng `admission_cho(model)`; cửa đồng bộ chờ sau commit (D04) | 1.5, 2.2 | MACHINE A |
| `apps/{anhnoibo,taoanh,thumbnail}/manifest.py` | khai `anh_3090` + nhóm `rtx3090` | 5.5 | 3090 |
| `llm_gateway/{gpu_uuid,so_theo_model}.py` (mới), `api.py`, `config.py`, `catalog.py`, `tren_gpu.py`, `trong_tai.py`; gỡ `don_dep.py` | UUID, sổ theo model, lệnh residency | 4.1, 4.2, 5.4 | MACHINE B |
| `render_gateway/{busy,nhuong_card,api}.py` | bỏ đuổi Qwen/TraCard, đo theo UUID, lệnh `nha_comfy` | 5.4, 6.1 | MACHINE B |
| `tests/test_637_nha_ve_ram.py` | chặn `--load-mode none|dio` | 6.2 | TEST |
| `tools/soi_cong_llm.py` | báo động theo UUID/residency | 6.3 | MACHINE A |
| `docs/…` | Q mới, nhật ký, runbook | 7.1 | DEPLOYMENT |

---

## Thứ tự thực hiện

`0.1 → 1.1 → 1.2 → 1.3 → 0.2 → 0.3 → 0.4 → 1.4 → 1.5 → 2.1 → 2.2 → 2.3 → 2.4 → 2.5 → 2.6 → 3.1 → 3.2 → 3.3 → 4.1 → 4.2 → 4.3 → 5.1 → 5.2 → 5.3 → 5.4 → 5.5 → 6.1 → 6.2 → 6.3 → 7.1`.
Mọi commit của plan nằm trên nhánh `phien/ltt-llm-dual` (tạo ở 1.1, từ trunk) — vì vậy 1.1–1.3 đi trước phần có mã của Pha 0.
Số test 1207 để trống (dự trữ).

## Pha 0 — An toàn máy B (không đổi hành vi khách)

### Task 0.1: Kênh SSH + đường deploy có sẵn  `[DEPLOYMENT]`

**Files:** không mã mới (YAGNI — `llm_gateway/deploy/deploy.ps1` đã deploy qua SSH/scp và chụp `releases/auto-<ts>`).

- [ ] **Step 1:** `ssh -i "%USERPROFILE%\.ssh\nexus_b" -o BatchMode=yes lengo@192.168.2.66 "hostname & whoami"` ⇒ `DESKTOP-MR9CFK0` / `desktop-mr9cfk0\lengo`, exit 0.
- [ ] **Step 2:** đọc `llm_gateway/deploy/deploy.ps1` (bước 0 kiểm SSH, bước chụp `releases/auto-<ts>`, bước scp) và chạy phần kiểm-trước của nó ⇒ bước 0 "ssh … chay duoc" xanh. Ghi tên snapshot đầu tiên vào `docs/ltt_llm_dual/NHAT_KY_TRIEN_KHAI.md` (điểm lùi Pha 0).
- [ ] **Step 3:** sửa `C:\Users\Thang Tuong\Desktop\Ket_noi.md` bằng cách **sinh lại** (`py "D:\LTT Nexus\scripts\write_connection_guide.py"`) — bản 30/08 ghi sshd `DISABLED`, đo 11/09 là `Running/Automatic`. Không commit (tệp ngoài kho).

Lệnh một lần trên máy B trong các task dưới: `ssh … lengo@192.168.2.66 "<lệnh>"`; lệnh nhiều dòng: `scp` một `.ps1` ASCII sang `E:\AI\ltt_dual\` rồi `ssh … "powershell -NoProfile -ExecutionPolicy Bypass -File E:\AI\ltt_dual\<tệp>.ps1"`.
### Task 0.2: Danh tính GPU + ghim UUID trên máy B  `[MACHINE B] [3090]`

**Files:**
- Create: `llm_gateway/deploy/gpu_may_b.json`
- Modify: `llm_gateway/deploy/llama-swap.yaml` (lấy khối `env` của Multi-Job T1 `8dbedd13`), `render_gateway/deploy/cai_dat_dich_vu.ps1:101` (env ComfyUI)
- Test: `tests/test_1200_ghim_gpu_may_b.py` (đánh số lại từ `test_950`, Task 1.2 — ở pha này tạo luôn tên mới)

**Interfaces:**
- Produces: `gpu_may_b.json` = `[{"vai":"ltt38","uuid":"GPU-26623278-4fa5-82db-4306-237651b03e78","pci_bus_id":"00000000:02:00.0","ten":"NVIDIA GeForce RTX 3090","vram_mib":24576},{"vai":"ltt35","uuid":"GPU-ebecd0a4-a8a7-14a5-dad1-21565f6dc1df","pci_bus_id":"00000000:81:00.0","ten":"NVIDIA GeForce RTX 5060 Ti","vram_mib":16311}]` (ghi không BOM).

- [ ] **Step 1: Test** — mọi hồ sơ trong yaml có `CUDA_VISIBLE_DEVICES` = UUID lấy từ `gpu_may_b.json` theo vai (`qwen38-*` ⇒ `ltt38`); không chuỗi `CUDA_VISIBLE_DEVICES=[0-9]`; `cai_dat_dich_vu.ps1` của render đặt `CUDA_VISIBLE_DEVICES=` UUID vai `ltt38` cho `LTTComfyUI`. Đối chứng: xoá dòng env một hồ sơ ⇒ ĐỎ.
- [ ] **Step 2:** chạy ⇒ FAIL. **Step 3:** sửa ba tệp. **Step 4:** PASS.
- [ ] **Step 5: Deploy máy B (khi `/running` rỗng hoặc sau khi hỏi các phiên khác):** `deploy.ps1` (chụp `auto-<ts>` rồi scp yaml → `H:\LTT_LLM\gateway\llama-swap.yaml`); đặt env ComfyUI (registry `HKLM:\SYSTEM\CurrentControlSet\Services\LTTComfyUI\Parameters` `AppEnvironmentExtra` thêm `CUDA_VISIBLE_DEVICES=<UUID 3090>` — `.ps1` ASCII qua scp rồi ssh); `Restart-Service LTTComfyUI, LTTLlamaSwap`.
- [ ] **Step 6: Kiểm trên máy (bằng chứng):** log ComfyUI mới nhất có đúng MỘT dòng `Device: cuda:0 NVIDIA GeForce RTX 3090` và **không** có dòng `RTX 5060 Ti`; gọi một lượt `qwen38-api` qua gateway rồi `nvidia-smi --query-compute-apps=pid,process_name,gpu_uuid,used_memory --format=csv` ⇒ `llama-server.exe` chỉ ở UUID 3090. Ghi vào `docs/ltt_llm_dual/NHAT_KY_TRIEN_KHAI.md` (tạo mới).
- **Điểm lùi:** xcopy ngược từ `auto-<ts>`, xoá dòng env ComfyUI, restart hai dịch vụ.
- [ ] **Step 7: Commit.**

### Task 0.3: Dọn VRAM nền khỏi 3090 (L-12)  `[MACHINE B] [3090]`

**Files:** Create `docs/ltt_llm_dual/artifacts/bench/do_vram_nen.ps1` (ASCII)

- [ ] **Step 1: Đo** trên máy B: `Get-Counter "\GPU Process Memory(*)\Dedicated Usage"` + `nvidia-smi --query-compute-apps` lọc UUID 3090 ⇒ bảng tiến trình × MiB trên 3090 khi không model nào nạp. Ghi vào nhật ký.
- [ ] **Step 2: Quyết theo số:** tổng tiến trình ngoài {llama-server, python ComfyUI} ≤ 100 MiB ⇒ ghi "L-12 đạt bằng đo", xong task. Lớn hơn ⇒ **dừng, trình chủ dự án** đúng thay đổi đề xuất (đặt GPU ưu tiên của các ứng dụng desktop sang 5060 Ti trong Settings → Display → Graphics, rồi đăng xuất/đăng nhập) — đây là thay đổi cài đặt hệ thống, chủ dự án xác nhận tại chỗ.
- [ ] **Step 3: Kiểm lại** sau thay đổi: bảng Step 1 ⇒ chỉ còn tiến trình được phép. Commit script + nhật ký.

### Task 0.4: Mốc hồi quy b10883  `[TEST] [3090]`

**Files:** Create `docs/ltt_llm_dual/artifacts/bench/bench.py` (tổng quát hoá `docs/multijob/artifacts/m1/m2_bench.py` từ `origin/claude/ltt-llm-multijob-audit-43efd3`: tham số `--cong`, `--model`, `--uuid`, `--kich-ban c1|c4|whale|anh|mtp_gate|nap`), `khoi_dong.ps1` (khuôn Scheduled Task SYSTEM + `pythonw`).

- [ ] **Step 1:** chép `m1_bench.py`/`m2_bench.py` từ nhánh Multi-Job, thêm tham số trên; mỗi kết quả là một dòng JSONL có `build`, `sha_gguf`, `uuid`, `tham_so`, `vram_dinh`, `shared_usage_dinh` (`Get-Counter "\GPU Process Memory(pid_<pid>*)\Shared Usage"`), `power_w_tb` (lấy mẫu `nvidia-smi --id=<uuid> --query-gpu=power.draw`).
- [ ] **Step 2:** đẩy sang `E:\AI\ltt_dual\bench\`, chạy kịch bản `c1` trên **hồ sơ production hiện tại** (`qwen38-api`, `-np 1`, b10883) qua llama-swap loopback khi không ai dùng máy B.
- [ ] **Step 3:** ghi mốc (decode tok/s, TTFT, VRAM) vào `NHAT_KY_TRIEN_KHAI.md` — đây là mốc cho ngưỡng nghiệm thu B (≥ 90 %). Commit.

---

## Pha 1 — Tích hợp Multi-Job lên trunk

### Task 1.1: Nhánh tích hợp  `[CONTROL PLANE]`

- [ ] **Step 1:** `git fetch origin`; `git switch -c phien/ltt-llm-dual admin-mvp-v3` (trong worktree phiên này — nhánh docs hiện tại giữ nguyên).
- [ ] **Step 2:** `git cherry-pick 0209ffc4` (tài liệu + spec) và commit plan này.
- [ ] **Step 3:** cherry-pick lần lượt `b0666413 8dbedd13 ab4d998e fd9b41b3 1c5cb232 a2518468 739ba02d 0e3305a7 b3b11dbc`. Xung đột dự kiến (đo ở `00` §2): `apps/ltt_llm/manifest.py`, `platform_core/{models,registry}.py`, `public_api/governance.py`, `server/api/streaming.py`, `tests/test_313_llm_admission.py`, `tools/restore_drill_schema.py`, `platform_core/job_runner.py`. Luật giải: **giữ cả hai phía**; Scheduler V1 (`jobs.py`, `job_scheduler.py`, cột envelope) không đổi ngữ nghĩa.
- [ ] **Step 4:** `python tools\gate.py --vong-lap` ⇒ nhóm kiểm tĩnh xanh (import-linter, ruff, CRLF/LF, ASCII `.ps1`).
- **Điểm lùi:** xoá nhánh `phien/ltt-llm-dual`; không có gì trên trunk bị chạm.

### Task 1.2: Đánh số lại test + đăng ký dải  `[TEST]`

**Files:** `git mv tests/test_950_ghim_gpu_may_b.py tests/test_1200_…` … `test_956_uoc_token_moi.py → test_1206_uoc_token_moi.py`; Modify `docs/KE_HOACH_TRIEN_KHAI.md` (bảng cấp phát: dòng "**1200–1249** — LTT LLM Dual-Model (Spec 1+2)").

- [ ] **Step 1:** `git grep -n "test_95[0-6]"` ⇒ sửa **mọi** tham chiếu (kể cả chú thích mã sản xuất và tài liệu — memory "dải test": chú thích trỏ số test trôi lặng lẽ nhất).
- [ ] **Step 2:** `git grep -n "test_95[0-6]_\(ghim\|mot_nguon\|so_ngan\|luat_nhan\|admission_ngan\|phong_cho\|uoc_token\)"` ⇒ 0 dòng. Commit.

### Task 1.3: Migration một head  `[MACHINE A]`

**Files:** Modify `alembic/versions/20260911_1200_llm_multijob_ngan_sach.py` (`down_revision` = revision của `20260910_1000_job_scheduler_envelope.py`).

- [ ] **Step 1:** `python -m alembic heads` ⇒ trước sửa: 2 head. Sửa `down_revision`. Sau: **1 head**.
- [ ] **Step 2:** `python -m pytest tests/test_1202_so_ngan_sach_mo_hinh.py -q` (migration khớp mô hình, lên/xuống SQLite) ⇒ PASS. Commit.

### Task 1.4: Xanh lại di sản trên cây hợp nhất  `[TEST]`

- [ ] `python tools\cua_so_yen.py trang-thai` ⇒ rảnh. Rồi:
  `python -m pytest -n 6 -q tests/test_1200_ghim_gpu_may_b.py tests/test_1201_mot_nguon_so_slot.py tests/test_1202_so_ngan_sach_mo_hinh.py tests/test_1203_luat_nhan.py tests/test_1204_admission_ngan_sach.py tests/test_1205_phong_cho.py tests/test_1206_uoc_token_moi.py tests/test_272_cua_streaming.py tests/test_313_llm_admission.py tests/test_363_suat_khong_ro.py tests/test_389_planner_model_nha.py tests/test_971_priority_scheduler_v1.py tests/test_1001_canonical_llm.py tests/test_1002_di_tru_khong_con_loi_ra_legacy.py`
  Expected: 0 failed. Đỏ ⇒ `superpowers:systematic-debugging`, không chạy gate để dò. Ghi số passed vào nhật ký. (Đây là lần đầu T1–T8 được chạy lại sau phiên cũ.)

### Task 1.5: Hoàn tất Task 9 Multi-Job theo D04  `[MACHINE A] [CONTROL PLANE]`

**Files:**
- Modify: `platform_core/llm/tham_so_da_luot.py` (thêm `luat_cho` — nguyên văn từ `docs/ltt_llm_dual/artifacts/wip_task9_multijob.patch`), `platform_core/runtime_noi_bo/luong.py` (hai chỗ dùng `luat_cho`, theo patch), `platform_core/job_runner.py` (`_luat_cho_job` theo patch, đặt vào `_chay_mot_job` bản trunk), `server/api/chat.py`, `server/api/streaming.py` (`_mot_cuc`), `platform_core/agent/planner.py`
- Test: `tests/test_1208_cua_dong_bo_cho.py`

**Interfaces:**
- Consumes: `phong_cho.vao(db, …) / cho_nhan_chan(…)` (T6), `admission.xet_va_giu(…)` (T5), `tham_so_da_luot.luat_cho(pool, *, lop, token_vao_uoc, xin_ra, so_anh=0, token_prefill_moi=0, la_whale=False) -> dict`.
- Produces: trình tự cửa đồng bộ D04: `idempotency.begin` → `db.commit()` (nhả `pg_advisory_xact_lock`) → `phong_cho.cho_nhan_chan(… , tran_s=min(60, ngan_sach_con_lai))` → giữ tiền → gọi → quyết toán; hết giờ ⇒ `limits.execution_busy(...)` 429 + đóng bản ghi idempotency trạng thái lỗi-có-thể-thử-lại.

- [ ] **Step 1: Test HTTP thật qua `TestClient`** (khuôn `test_272`): (a) một lease giữ đủ slot ⇒ gọi `/api/v1/chat/completions` ⇒ trong lúc chờ **không có dòng giữ tiền nào** (INV-MJ-1); nhả lease ⇒ request hoàn tất 200; (b) không ai nhả ⇒ 429 sau trần (đồng hồ tiêm, không `sleep` thật), 0 khoản treo (INV-MJ-2), bản ghi idempotency không kẹt "đang xử lý"; (c) hai request cùng `Idempotency-Key` cùng chờ ⇒ đúng một lượt chạy model, lượt kia replay/409; (d) planner: lớp `noi_bo`, không chờ, hết chỗ ⇒ đi tiếp provider sau (hành vi F-06); (e) client ngắt **trong lúc gọi model** (spec §16): cửa đồng bộ thăm `await request.is_disconnected()` mỗi 1 s song song với lời gọi ⇒ đóng client httpx tới máy B, quyết toán theo `usage` nếu có, không thì hoàn trọn; lease nhả. Đối chứng: đặt điểm chờ **trước** commit ⇒ phép (a) phát hiện khoá idempotency bị giữ (PostgreSQL) — chạy phần PostgreSQL theo khuôn `test_73` (bỏ qua khi không có DB test, có dấu skip rõ lý do).
- [ ] **Step 2:** FAIL. **Step 3:** áp phần `luat_cho`/`_luat_cho_job` từ patch; viết lại khối admission của `chat.py:188` và `_mot_cuc` theo trình tự trên; planner truyền `lop=luat_nhan.NOI_BO`. **Step 4:** PASS + hồi quy `test_259_cua_dong_bo`, `test_285_messages_khong_stream`, `test_313`, `test_389`.
- [ ] **Step 5:** Ghi vào `DECISION_LOG.md` dưới D04: "đã hiện thực ở <sha>". Commit.

---

## Pha 2 — Hợp đồng hai model

### Task 2.1: `AdmissionModel` + `ToolSpec.admission_cho()`  `[CONTROL PLANE]`

**Files:** Modify `platform_core/registry.py` (cạnh `admission_slots`, trunk `:151-159`); Test `tests/test_1209_admission_theo_model.py`

**Interfaces — Produces:**

```python
@dataclass(frozen=True)
class AdmissionModel:
    """Sức chứa một model của tool. Khoá `"*"` = áp cho mọi model của tool."""
    resource: str
    slots: int
    token_pool: int = 0
    residency_group: str = ""   # vd "rtx3090"; rỗng = không trọng tài
    vai_tro: str = ""           # "mac_dinh" | "theo_lo" | ""

# trong ToolSpec (frozen dataclass):
    admission_theo_model: dict = field(default_factory=dict)   # {model_id|"*": AdmissionModel}

    def admission_cho(self, model: str = "") -> "AdmissionModel | None":
        m = self.admission_theo_model
        if m:
            if model in m:
                return m[model]
            if "*" in m:
                return m["*"]
            raise KeyError(f"{self.name}: model {model!r} khong co trong admission_theo_model")
        if self.admission_resource and self.admission_slots > 0:
            return AdmissionModel(self.admission_resource, self.admission_slots,
                                  int(getattr(self, "admission_token_pool", 0) or 0))
        return None
```

- [ ] **Step 1: Test:** tool có ánh xạ trả đúng pool theo model; `"*"` áp mọi model; model lạ ⇒ `KeyError`; tool cũ (chỉ `admission_resource/slots`) trả `AdmissionModel` tương đương (không đổi hành vi); tool không khai ⇒ `None`. Chiếu `catalog.py` **không** lộ `admission_theo_model` ra khách (khuôn `test_1201` cho `admission_token_pool`).
- [ ] **Step 2–4:** FAIL → viết → PASS. **Step 5:** Commit.

### Task 2.2: Mọi cửa dùng `admission_cho(model)`  `[MACHINE A]`

**Files:** Modify `server/api/chat.py`, `server/api/streaming.py`, `platform_core/runtime_noi_bo/luong.py`, `platform_core/job_runner.py` (`_chay_mot_job`: resource/slots/pool lấy từ `tool.admission_cho(params.get("model",""))`), `platform_core/llm/canonical.py` (`tai_nguyen_nha(model)`), `platform_core/agent/planner.py`, `platform_core/image_gen/dich_llm.py`. Test: mở rộng `tests/test_1209_admission_theo_model.py`.

- [ ] **Step 1: Test tĩnh (AST, không quét văn bản — memory "bộ dò phạt giải thích"):** trong các tệp trên, không còn truy cập `tool.admission_resource`/`admission_slots`/`admission_token_pool` trực tiếp ngoài `registry.py`; mọi chỗ gọi `admission.acquire`/`hold_persisted`/`xet_va_giu` nhận `resource` từ `admission_cho`. Test hành vi: job `model=ltt-3.5` giữ lease trên `ltt_35_5060`, `model=ltt-3.8` trên `ltt_38_3090` (SQLite).
- [ ] **Step 2–4:** FAIL → sửa → PASS; hồi quy `test_1204`, `test_1205`, `test_272`, `test_313`, `test_1001`, `test_1002`.
- [ ] **Step 5:** Commit.

### Task 2.3: Cắt tên cũ (D02)  `[MACHINE A]`

**Files:** Modify `platform_core/llm/canonical.py` (`ALIAS_SANG_ID = {"ltt-3.8": "qwen38-api", "ltt-3.5": "qwen35-api"}`), `apps/ltt_llm/manifest.py` (`params_schema.model.values = ["ltt-3.8", "ltt-3.5"]`, `default "ltt-3.8"`; `admission_theo_model = {"ltt-3.8": AdmissionModel("ltt_38_3090", SO_SLOT, POOL_38, "rtx3090", "mac_dinh"), "ltt-3.5": AdmissionModel("ltt_35_5060", SO_SLOT, POOL_35)}`; khối mô tả model `:235-262`), `apps/ltt_llm/features.py`, `platform_core/providers.py` (models `qwen38-api`, `qwen35-api`; bỏ `qwen38-vision`), `platform_core/public_api/examples.py` (`CHAT_MODEL="ltt-3.8"`, `CLI_MODEL="ltt-3.8"`), `server/api/streaming.py` (`ltt-llm-claude-compat` → `ltt-3.8`), trang `/developers` + `/gia-api` (template tương ứng), `frontend/chatltt` (bộ chọn đọc manifest — kiểm nhãn), migration dữ liệu `alembic/versions/20260912_…_ten_model_ltt.py`.
**Test:** `tests/test_1210_ten_model_cong_khai.py`

- [ ] **Step 1: Tìm mọi chỗ lưu tên cũ:** `git grep -n -E "ltt_llm_vision|\"ltt_llm\"|'ltt_llm'" -- apps platform_core server frontend alembic` ⇒ lập danh sách trong nhật ký; phân loại (a) mã (b) dữ liệu lưu (c) test ghim.
- [ ] **Step 2: Test:** `/api/v1/models` liệt kê **đúng** `{"ltt-3.8","ltt-3.5"}`; gọi `/chat/completions` với `model=ltt_llm` ⇒ `model_not_found`; mỗi cửa (sync/stream/job) từ chối tên cũ; migration dữ liệu: job `queued` có `params.model="ltt_llm"` ⇒ `"ltt-3.8"`, lựa chọn model đã lưu của ChatLTT tương tự; lịch sử usage/credit **không** bị viết lại. Đối chứng: bỏ một tên khỏi manifest ⇒ đỏ.
- [ ] **Step 3–4:** FAIL → sửa + migration → PASS; hồi quy `test_212` (lớp đệm bí danh), `test_1001`.
- [ ] **Step 5:** Commit.

### Task 2.4: Model cho việc nội bộ theo app (D09)  `[CONTROL PLANE]`

**Files:** Modify `platform_core/registry.py` (`AppManifest.model_llm_noi_bo: str = "ltt-3.5"`), `platform_core/llm/canonical.py`, `platform_core/image_gen/dich_llm.py`, `apps/{taovideo,autosubvideo,prompt_ai_ommi}` chỗ gọi `canonical`, `platform_core/agent/planner.py`. Test `tests/test_1211_llm_noi_bo_theo_app.py`.

**Interfaces — Produces:**

```python
# platform_core/llm/canonical.py
def model_noi_bo_cua(slug_app: str) -> str:
    """Model khai cho việc LLM nội bộ của app (D09). Không đọc được ⇒ "ltt-3.5" (và log cảnh báo)."""

def ban_do_model(model: str) -> dict[str, str]:          # {"ltt_llm": ALIAS_SANG_ID[model]}
def tai_nguyen_nha(model: str) -> AdmissionModel:        # tool text.chat .admission_cho(model); đổi kiểu trả so với trunk
                                                         # (tuple 2 phần tử) ⇒ sửa MỌI người gọi dùng .resource/.slots/.token_pool
```

- [ ] **Step 1: Test:** mọi app không khai ⇒ `ltt-3.5`; `dich_llm.goi_llm` giành lease trên `ltt_35_5060`; **chốt vòng chờ:** với mọi app có tool `residency_group="rtx3090"` + `vai_tro="theo_lo"`, `model_noi_bo_cua(app) != "ltt-3.8"` (đối chứng: khai `ltt-3.8` cho `anhnoibo` ⇒ ĐỎ); planner model nhà đầu tiên `ltt-3.5`, vẫn rơi Gemini khi bận.
- [ ] **Step 2–4:** FAIL → sửa → PASS; hồi quy `test_1001`–`test_1008`, `test_389`. **Step 5:** Commit.

### Task 2.5: Giá theo model (D07)  `[MACHINE A]`

**Files:** Modify `platform_core/llm/gia_token.py`, `platform_core/llm/thanh_toan.py`, `apps/ltt_llm/features.py` (`credit_cost`), trang giá. Test `tests/test_1212_gia_theo_model.py`.

**Interfaces — Produces:**

```python
@dataclass(frozen=True)
class BangGia:
    vao_moi_1m: int
    vao_cache_1m: int
    ra_1m: int
    phien_ban: str

BANG_GIA: dict[str, BangGia] = {
    "ltt-3.8": BangGia(50, 10, 400, "ltt-vlm-2026-08-22"),
    "ltt-3.5": BangGia(13, 3, 20, "ltt-3.5-2026-09-11"),
}
# giữ tên cũ làm bí danh HẰNG SỐ của bảng 3.8 cho mã chưa truyền model:
GIA_VAO_MOI_CREDIT_1M, GIA_VAO_CACHE_CREDIT_1M, GIA_RA_CREDIT_1M = 50, 10, 400
PHIEN_BAN_GIA = BANG_GIA["ltt-3.8"].phien_ban

def tinh(su_dung: SuDung, model: str) -> ChiPhi:   # model BẮT BUỘC — không mặc định ngầm
```

- [ ] **Step 1: Test:** 1M ra `ltt-3.5` = 20.000 mcredit, `ltt-3.8` = 400.000; nhãn đúng model; `tinh(..., "ltt_llm")` ⇒ `KeyError`; mọi chỗ gọi `tinh` truyền model thật đã phục vụ (AST); `dang_tin=False` vẫn ném `KhongDoDuocError`. Hồi quy `test_68`, `test_292`, `test_390`, `test_1003`.
- [ ] **Step 2–4:** FAIL → sửa → PASS. **Step 5:** Commit.

### Task 2.6: Số theo model trong `ngan_sach.py`  `[MACHINE A]`

**Files:** Modify `apps/ltt_llm/ngan_sach.py` (`CUA_SO_THEO_MODEL = {"qwen38-api": 262_144, "qwen35-api": 262_144}`; `CUA_SO_MODEL = CUA_SO_THEO_MODEL["qwen38-api"]`; xoá `CUA_SO_MODEL_VISION`; `SO_SLOT_MAY_B = 4`; `POOL_KV = dict(CUA_SO_THEO_MODEL)`; `NGUONG_WHALE = {"qwen38-api": 16_384, "qwen35-api": 32_768}`; trần vào/ra/công bố dẫn xuất **theo model** bằng cùng công thức), `apps/ltt_llm/executor.py` (`context_output_cap` theo model), `tests/test_334_ngan_sach_ltt_llm.py` (đối chiếu `-c`, `-np`, `-kvu`, `--mmproj`, UUID theo hồ sơ).

- [ ] **Step 1:** test_334 mở rộng ⇒ FAIL (yaml chưa đổi — sẽ xanh ở Task 3.3; đánh dấu `xfail(strict=True, reason="cho Task 3.3")` cho riêng phần yaml). **Step 2–4:** sửa → PASS phần số. **Step 5:** Commit.

**Điểm lùi Pha 2:** revert các commit pha 2 trên `phien/ltt-llm-dual` (chưa deploy).

---

## Pha 3 — Engine máy B

### Task 3.1: Tải Qwen3.5-9B Q6_K + mmproj  `[MACHINE B] [5060]`

**Files:** Create `docs/ltt_llm_dual/artifacts/bench/tai_model.ps1` (ASCII, Scheduled Task SYSTEM).

- [ ] **Step 1:** lấy oid sha256 LFS: `curl -s https://huggingface.co/api/models/unsloth/Qwen3.5-9B-MTP-GGUF/tree/main` và `…/lmstudio-community/Qwen3.5-9B-GGUF/tree/main` ⇒ ghi sha của `Q6_K` + `mmproj-F16` vào nhật ký.
- [ ] **Step 2:** script tải bằng `curl.exe -L --retry 5 -o H:\LTT_LLM\models\<tệp>.part https://huggingface.co/<repo>/resolve/main/<tệp>` rồi `Get-FileHash` ⇒ khớp mới đổi tên bỏ `.part`; ghi từng bước vào `E:\AI\ltt_dual\tai_model.log` (ghi ngay, không đợi cuối — Windows Update sau 01:00).
- [ ] **Step 3:** `ssh … "type E:\AI\ltt_dual\tai_model.log"` đọc log ⇒ hai tệp mỗi repo, hash khớp. Commit script + nhật ký.

### Task 3.2: Cổng đo trước khi chốt cấu hình  `[TEST] [3090] [5060]`

**Files:** Modify `docs/ltt_llm_dual/artifacts/bench/bench.py` (kịch bản), Create `docs/ltt_llm_dual/10_BENCHMARK_P3.md` (kết quả).

Chạy llama-server **cổng thử 8290/8291** (không đụng llama-swap), khi `/running` rỗng, desktop + tác vụ nền thật đang mở (D06):
- [ ] **G1 `qwen38-api` đầy đủ (D03):** `-c 262144 -np 4 -kvu --mmproj … draft-mtp n-max 2 KV q4_0` ⇒ nạp được? VRAM sau nạp, đỉnh (1 ảnh + 3 text), `Shared Usage` = 0? Biên ≥ 300 MiB? Không đạt ⇒ **dừng, báo chủ dự án kèm số; hướng dự phòng C (3 rồi 2 slot)** — không tự đổi.
- [ ] **G2 cổng MTP `-np 4` (#27572):** 200 lượt, 4 luồng đồng thời, mỗi prompt có dấu riêng `DAU-<slot>-<n>` (có prompt > ubatch 512, có ảnh) ⇒ 0 trả lời rỗng, 0 trả lời chứa dấu của slot khác, `spec_decode_num_accepted_tokens_total` tăng ở mọi slot. Trượt ⇒ `DECISION REOPEN REQUEST — D03` kèm dữ liệu.
- [ ] **G3 `qwen35-api` Q6_K 262K** (hai ứng viên tệp): VRAM đỉnh + chừa ≥ ~2 GiB trên 5060 Ti; C1/C4 text + ảnh; chấm chất lượng bằng bộ `danh_gia_llm` hiện có ⇒ chọn **một** tệp Q6_K. Không chừa đủ ⇒ `REOPEN D06`.
- [ ] **G4 tham số theo model:** `token_moi_anh` (đo `n_prompt_tokens` của 1 ảnh 1024×768), prefill tok/s ⇒ `NGUONG_WHALE` 3.5, `T_NAP_LLM` (nạp `qwen38-api` 262K từ ấm), W trung bình 5060 Ti ở C1/C4 ⇒ chi phí điện/1M token ra (D07 consequence 1).
- [ ] **G5 kho ấm:** nạp lạnh (sau `Clear-StandbyList`-tương đương: khởi động lại hoặc đọc tệp khác lớn hơn RAM trống không khả thi ⇒ ghi rõ cách đã làm) vs ấm, cả hai model.
- [ ] Ghi toàn bộ vào `10_BENCHMARK_P3.md` (gói tái hiện §23 spec). Cập nhật số khởi đầu trong `ngan_sach.py` theo đo (một commit, dẫn nguồn). Commit.

### Task 3.3: `llama-swap.yaml` hai model  `[MACHINE B] [3090] [5060]`

**Files:** Modify `llm_gateway/deploy/llama-swap.yaml`; `tests/test_334_ngan_sach_ltt_llm.py` (bỏ `xfail`), `tests/test_1200_ghim_gpu_may_b.py`.

Khối `models` + `groups` + `hooks` (giữ nguyên macro `BIN`, `MODELS`, `CHUNG` bỏ `--parallel 1`):

```yaml
macros:
  BIN: "H:/LTT_LLM/bin/llamacpp"
  MODELS: "H:/LTT_LLM/models"
  GGUF38: "H:/LTT_LLM/models/Qwen3.8-27B-UD-Q4_K_M.gguf"
  GGUF35: "H:/LTT_LLM/models/<tệp Q6_K chọn ở 3.2>"
  CHUNG: >-
    --jinja --reasoning-format deepseek -fa 1 -ngl 999 --metrics
    -np 4 -kvu -c 262144

models:
  qwen38-api:
    name: "LTT-3.8"
    cmd: |
      ${BIN}/llama-server.exe -m ${GGUF38} --mmproj ${MODELS}/mmproj-F16.gguf
      --chat-template-file H:/LTT_LLM/models/chat_template.jinja
      ${CHUNG} --cache-type-k q4_0 --cache-type-v q4_0
      --spec-type draft-mtp --spec-draft-n-max 2
      --cache-ram <số chốt ở 3.2>
      --host 127.0.0.1 --port ${PORT}
    env:
      - "CUDA_VISIBLE_DEVICES=GPU-26623278-4fa5-82db-4306-237651b03e78"
    proxy: "http://127.0.0.1:${PORT}"
    ttl: 0
    concurrencyLimit: 8
    unloadTimeout: 30
  qwen35-api:
    name: "LTT-3.5"
    cmd: |
      ${BIN}/llama-server.exe -m ${GGUF35} --mmproj ${MODELS}/<mmproj 9B>
      ${CHUNG} --cache-type-k q8_0 --cache-type-v q8_0
      --cache-ram <số chốt ở 3.2>
      --host 127.0.0.1 --port ${PORT}
    env:
      - "CUDA_VISIBLE_DEVICES=GPU-ebecd0a4-a8a7-14a5-dad1-21565f6dc1df"
    proxy: "http://127.0.0.1:${PORT}"
    ttl: 0
    concurrencyLimit: 8
    unloadTimeout: 30

groups:
  may_b:
    swap: false
    exclusive: true
    members: ["qwen38-api", "qwen35-api"]

hooks:
  on_startup:
    preload: ["qwen38-api", "qwen35-api"]
```

(`draft-mtp` chỉ còn nếu G2 qua; `preserve_reasoning`: thêm cờ tường minh theo thẻ model — chốt ở 3.2.)

- [ ] **Step 1:** test_334 + test_1200 (bỏ `xfail`) ⇒ FAIL với yaml cũ; sửa yaml ⇒ PASS; test mới: không hồ sơ `qwen38-vision`; hai hồ sơ trong một group `swap:false`; preload đủ hai; `concurrencyLimit ≥ 2 × SO_SLOT_MAY_B`.
- [ ] **Step 2: Deploy máy B:** `deploy.ps1` (snapshot + scp yaml) → `Restart-Service LTTLlamaSwap` → `/running` có **2** model; `nvidia-smi --query-compute-apps` ⇒ mỗi llama-server ở đúng UUID; VRAM từng card ghi vào nhật ký.
- **Điểm lùi:** xcopy yaml cũ từ snapshot + restart (≈ 20 s, như diễn tập 18,9 s).
- [ ] **Step 3:** Commit.

---

## Pha 4 — Gateway theo model

### Task 4.1: Đo theo UUID trên máy B  `[MACHINE B]`

**Files:** Create `llm_gateway/gpu_uuid.py`; Modify `llm_gateway/tren_gpu.py:63-83`, `llm_gateway/deploy/nghiem_thu.py:71-78`, `llm_gateway/deploy/chay_nghiem_thu.cmd:8-9,53-54`, `render_gateway/diagnostics/gpu_check.py`, `tools/bench_llm_hieu_nang.py:57-60`, `llm_gateway/api.py` (`/health/ready` fail-closed). Test `tests/test_1213_gpu_uuid_may_b.py`.

**Interfaces — Produces:**

```python
# llm_gateway/gpu_uuid.py
def doc_danh_tinh(duong: Path | None = None) -> list[dict]      # đọc gpu_may_b.json (không BOM)
def uuid_cua(vai: str) -> str                                    # "ltt38" | "ltt35"
def vram_mib(uuid: str, *, chay=subprocess.run) -> int | None    # nvidia-smi --id=<uuid> --query-gpu=memory.used --format=csv,noheader,nounits
def util_pt(uuid: str, *, chay=subprocess.run) -> int | None
def tien_trinh(uuid: str, *, chay=subprocess.run) -> list[tuple[int, str, int]]  # --query-compute-apps lọc gpu_uuid
def thay_du_hai_card(*, chay=subprocess.run) -> bool             # cả hai UUID có trong --query-gpu=uuid
```

- [ ] **Step 1: Test** (subprocess tiêm, đầu ra nvidia-smi mẫu 2 dòng đảo thứ tự): `vram_mib(uuid 3090)` trả dòng của 3090 kể cả khi 3090 ở dòng thứ hai; `tien_trinh` lọc đúng UUID; `thay_du_hai_card` False khi thiếu một UUID ⇒ `/health/ready` 503. **Chốt tĩnh AST:** trong `llm_gateway/` và `render_gateway/` không còn `.splitlines()[0]`/`dong[0]` trên đầu ra `nvidia-smi`, không `--query-compute-apps` thiếu lọc UUID, không `taskkill /im llama-server.exe`. Đối chứng: phục hồi một chỗ `dong[0]` ⇒ ĐỎ.
- [ ] **Step 2–4:** FAIL → sửa → PASS. **Step 5:** Commit.

### Task 4.2: Sổ slot/token/whale theo model  `[MACHINE B]`

**Files:** Create `llm_gateway/so_theo_model.py`; Modify `llm_gateway/{api,config,catalog}.py`; Test `tests/test_1214_gateway_so_theo_model.py` (+ hồi quy `test_250`, `test_363`).

**Interfaces — Produces:**

```python
# llm_gateway/so_theo_model.py
class SoTheoModel:
    """Một GioiHan cho MỖI model — tải 3.8 không bao giờ lấy suất 3.5."""
    def __init__(self, models: tuple[str, ...], *, max_dong_thoi: int, token_pool: int, rpm: int = 120): ...
    def cap_suat(self, model: str, token_dat_truoc: int, la_whale: bool) -> tuple[PhanXuGioiHan, Suat | None]: ...
    def dang_chay(self, model: str) -> int: ...
    def trang_thai(self) -> dict[str, dict]: ...   # {model: {dang_chay, max, token_dat, pool, whale}}
```
`GioiHan` (`gioi_han.py:95`) nhận thêm `token_pool: int = 0` và `cap_suat(token_dat_truoc=0, la_whale=False)`: từ chối khi `Σ token_dat + mới > pool` (pool>0) hoặc đã có một whale; `Suat` nhớ phần đặt chỗ và trả trong `tra()`. `config.py`: `LTT_LLM_MODELS=qwen38-api,qwen35-api`, `LTT_LLM_MAX_DONG_THOI=4`, `LTT_LLM_TOKEN_POOL=262144` áp **mỗi model** (ghi đè riêng qua `LTT_LLM_MAX_DONG_THOI__<model>`). `catalog.HO_SO` hai hồ sơ, cả hai `in: text,image`. Header vào: `X-LTT-Request-Id`, `X-LTT-Token-Dat`, `X-LTT-Whale`. `deploy.ps1` không còn ép `MAX_DONG_THOI=1` (`deploy.ps1:278-285`). **Chốt VRAM 5060 Ti (spec §22, D06):** trước khi cấp suất `qwen35-api`, gateway đọc `gpu_uuid.vram_mib(uuid ltt35)`; VRAM trống < `LTT_LLM_VRAM_TRONG_TOI_THIEU_MB__qwen35-api` (khởi đầu 512, chốt ở Task 3.2) ⇒ 429 `ban` (không nhận lượt mới, không giết lượt đang chạy).

- [ ] **Step 1: Test:** 4 lượt 3.8 đầy ⇒ lượt 3.8 thứ 5 bị 429 nhưng lượt 3.5 vẫn 200; VRAM 5060 Ti trống (tiêm) dưới ngưỡng ⇒ lượt 3.5 mới 429 `ban`, lượt 3.8 không bị ảnh hưởng; Σ token vượt pool ⇒ 429 (không 502); whale thứ hai ⇒ 429; `/health` có khối theo model; ảnh vào `qwen35-api` được nhận (không còn 413 "model không vision"); **không** gửi `X-Conversation-Id` lên thượng nguồn. Đối chứng: một `GioiHan` chung ⇒ phép đầu ĐỎ.
- [ ] **Step 2–4:** FAIL → viết → PASS. **Step 5:** Commit.

### Task 4.3: Log từng lượt + hủy cứng job (Multi-Job T10 phần log, T11)  `[MACHINE A] [MACHINE B]`

**Files:** Modify `llm_gateway/api.py` (một dòng JSON mỗi lượt: request id, model, uuid, token vào/cache/ra từ `usage`/`timings`, prefill & decode tok/s, TTFT, mã kết thúc, hủy), `platform_core/llm/cong_vlm.py` (499 ⇒ `HuyError`), `platform_core/llm/dieu_phoi.py` (không cascade, không đánh lỗi khoá khi hủy; gửi `X-LTT-Request-Id`), `apps/ltt_llm/jobs.py` (luồng canh `is_cancelled()` mỗi 1 s ⇒ đóng client httpx ⇒ `JobCancelled`). Test `tests/test_1215_huy_cung_job.py`.

- [ ] **Step 1: Test:** provider giả giữ kết nối; `POST /jobs/{id}/cancel` ⇒ kết nối tới provider giả **đóng ≤ 2 s**; job `cancelled`, credit hoàn trọn, lease nhả; log gateway có đúng một dòng với `huy=true`. Đối chứng: tắt luồng canh ⇒ kết nối sống tới hết ⇒ ĐỎ.
- [ ] **Step 2–4:** FAIL → sửa → PASS. **Step 5:** Deploy gateway lên máy B (`deploy.ps1` (snapshot + scp các tệp `.py` đã đổi + kiểm hash `.py` có sẵn) → `Restart-Service LTTLlmGateway` → `/health` 200 có khối theo model). Commit.

---

## Pha 5 — Residency 3090 (D01 B)

### Task 5.1: Bảng `gpu_residency`  `[MACHINE A]`

**Files:** Modify `platform_core/models.py` (`GpuResidency`: `nhom` PK/UNIQUE, `trang_thai` str, `tu_luc` datetime, `cua_so_bat_dau` datetime null, `lan_nap_loi` int, `phien_ban` int), `alembic/versions/20260912_…_gpu_residency.py` (nối head sau Task 2.3), `platform_core/public_api/governance.py` (`Store` OPERATIONAL, dọn: không cần — một dòng/nhóm ghi đè, ghi lý do), `tools/restore_drill_schema.py` (UNIQUE `nhom`). Test: thêm vào `tests/test_1216_residency_thuan.py` phần mô hình (migration khớp, governance, drill).

- [ ] Step 1–4 TDD như Task 1.3 (alembic 1 head, lên/xuống SQLite). Step 5 Commit.

### Task 5.2: Máy trạng thái thuần  `[CONTROL PLANE]`

**Files:** Create `platform_core/llm/residency.py`; Test `tests/test_1216_residency_thuan.py`.

**Interfaces — Produces (toàn bộ phần thuần):**

```python
from __future__ import annotations
from dataclasses import dataclass, replace

LLM, XA_LLM, NHA_LLM, ANH, TRA_ANH, NAP_LLM, LOI_NAP = (
    "llm", "xa_llm", "nha_llm", "anh", "tra_anh", "nap_llm", "loi_nap")
NHA_LLM_LENH, NAP_LLM_LENH, FREE_COMFY_LENH = "nha_llm", "nap_llm", "free_comfy"


@dataclass(frozen=True)
class ThamSoResidency:
    cua_so_anh_toi_da: int = 4        # D01
    cua_so_anh_s: float = 480.0       # D01
    t_nap_llm_s: float = 45.0         # chốt bằng đo Task 3.2 G4
    t_anh_uoc_s: float = 110.0        # docs/ANH_NOI_BO: 92–110 s/ảnh
    bien_s: float = 30.0
    vram_sach_mib: int = 2500
    lui_nap_loi_s: float = 30.0


@dataclass(frozen=True)
class TrangThai:
    ten: str = LLM
    tu_luc: float = 0.0
    cua_so_bat_dau: float = 0.0
    lan_nap_loi: int = 0


@dataclass(frozen=True)
class QuanSat:
    lease_llm: int                    # lease sống của thành viên "mac_dinh"
    lease_anh: int                    # lease sống của thành viên "theo_lo"
    job_anh_cho: int                  # job "theo_lo" đang queued
    anh_bat_dau_trong_cua_so: int     # job "theo_lo" đã được nhận kể từ cua_so_bat_dau
    nguoi_cho_llm: int                # waiter + job queued của "mac_dinh"
    han_chot_llm_s: float | None      # giây còn lại tới hạn chót sớm nhất của người chờ LLM
    gateway_inflight_llm: int | None  # None = không hỏi được máy B
    llm_da_nap: bool | None
    vram_3090_mib: int | None
    nap_ket_qua: str = ""             # "" | "ok" | "loi"


def mo_cho(ten: str, vai_tro: str) -> bool:
    """Admission của thành viên có vai trò này đang mở không (luật 0 của luat_nhan)."""
    return (ten == LLM and vai_tro == "mac_dinh") or (ten == ANH and vai_tro == "theo_lo")


def _dong_cua_so(tt: TrangThai, qs: QuanSat, ts: ThamSoResidency, bay_gio: float) -> bool:
    if qs.job_anh_cho == 0 and qs.lease_anh == 0:
        return True
    if qs.nguoi_cho_llm == 0:
        return False                                   # work-conserving
    if qs.anh_bat_dau_trong_cua_so >= ts.cua_so_anh_toi_da:
        return True
    if bay_gio - tt.cua_so_bat_dau >= ts.cua_so_anh_s:
        return True
    if qs.han_chot_llm_s is not None and \
            qs.han_chot_llm_s - ts.t_nap_llm_s - ts.t_anh_uoc_s - ts.bien_s <= 0:
        return True
    return False


def buoc_thuan(tt: TrangThai, qs: QuanSat, ts: ThamSoResidency,
               bay_gio: float) -> tuple[TrangThai, tuple[str, ...]]:
    """Một bước. KHÔNG bao giờ phát NHA_LLM khi còn lease/in-flight LLM (L-9)."""
    t = tt.ten
    if t == LLM:
        return (replace(tt, ten=XA_LLM, tu_luc=bay_gio), ()) if qs.job_anh_cho > 0 else (tt, ())
    if t == XA_LLM:
        if qs.job_anh_cho == 0 and qs.lease_anh == 0:
            return replace(tt, ten=LLM, tu_luc=bay_gio), ()
        if qs.lease_llm == 0 and qs.gateway_inflight_llm == 0:
            return replace(tt, ten=NHA_LLM, tu_luc=bay_gio), (NHA_LLM_LENH,)
        return tt, ()
    if t == NHA_LLM:
        if qs.llm_da_nap is False:
            return replace(tt, ten=ANH, tu_luc=bay_gio, cua_so_bat_dau=bay_gio), ()
        if qs.lease_llm == 0 and qs.gateway_inflight_llm == 0:
            return tt, (NHA_LLM_LENH,)             # lệnh idempotent, lặp tới khi thấy đã nhả
        return tt, ()
    if t == ANH:
        return (replace(tt, ten=TRA_ANH, tu_luc=bay_gio), ()) if _dong_cua_so(tt, qs, ts, bay_gio) else (tt, ())
    if t == TRA_ANH:
        if qs.lease_anh > 0:
            return tt, ()                              # lượt vẽ đang chạy chạy tới hết
        if qs.vram_3090_mib is not None and qs.vram_3090_mib <= ts.vram_sach_mib:
            return replace(tt, ten=NAP_LLM, tu_luc=bay_gio), (NAP_LLM_LENH,)
        return tt, (FREE_COMFY_LENH,)
    if t == NAP_LLM:
        if qs.nap_ket_qua == "ok" and qs.llm_da_nap:
            return replace(tt, ten=LLM, tu_luc=bay_gio, lan_nap_loi=0), ()
        if qs.nap_ket_qua == "loi":
            return replace(tt, ten=LOI_NAP, tu_luc=bay_gio, lan_nap_loi=tt.lan_nap_loi + 1), ()
        return tt, ()
    if t == LOI_NAP:
        cho = ts.lui_nap_loi_s * min(2 ** max(tt.lan_nap_loi - 1, 0), 16)
        return (replace(tt, ten=NAP_LLM, tu_luc=bay_gio), (NAP_LLM_LENH,)) if bay_gio - tt.tu_luc >= cho else (tt, ())
    raise ValueError(f"trang thai la: {t!r}")
```

- [ ] **Step 1: Test (không CSDL, đồng hồ tiêm):**

```python
from platform_core.llm import residency as R

def qs(**k):
    base = dict(lease_llm=0, lease_anh=0, job_anh_cho=0, anh_bat_dau_trong_cua_so=0, nguoi_cho_llm=0,
                han_chot_llm_s=None, gateway_inflight_llm=0, llm_da_nap=True, vram_3090_mib=20000)
    base.update(k); return R.QuanSat(**base)

TS = R.ThamSoResidency()

def test_khong_bao_gio_nha_llm_khi_con_luot_chay():
    tt = R.TrangThai(ten=R.XA_LLM)
    for lease, inflight in ((1, 0), (0, 1), (0, None), (2, 3)):
        moi, lenh = R.buoc_thuan(tt, qs(job_anh_cho=1, lease_llm=lease, gateway_inflight_llm=inflight), TS, 10)
        assert R.NHA_LLM_LENH not in lenh and moi.ten == R.XA_LLM

def test_chu_trinh_day_du():
    tt = R.TrangThai()
    tt, l = R.buoc_thuan(tt, qs(job_anh_cho=1), TS, 0);                      assert tt.ten == R.XA_LLM
    tt, l = R.buoc_thuan(tt, qs(job_anh_cho=1), TS, 1);                      assert (tt.ten, l) == (R.NHA_LLM, (R.NHA_LLM_LENH,))
    tt, l = R.buoc_thuan(tt, qs(job_anh_cho=1, llm_da_nap=False), TS, 2);    assert tt.ten == R.ANH
    tt, l = R.buoc_thuan(tt, qs(llm_da_nap=False), TS, 200);                 assert tt.ten == R.TRA_ANH
    tt, l = R.buoc_thuan(tt, qs(llm_da_nap=False, vram_3090_mib=9000), TS, 201); assert l == (R.FREE_COMFY_LENH,)
    tt, l = R.buoc_thuan(tt, qs(llm_da_nap=False, vram_3090_mib=1500), TS, 202); assert (tt.ten, l) == (R.NAP_LLM, (R.NAP_LLM_LENH,))
    tt, l = R.buoc_thuan(tt, qs(nap_ket_qua="ok"), TS, 250);                 assert tt.ten == R.LLM

def test_cua_so_dong_som_theo_han_chot_nguoi_cho_llm():
    tt = R.TrangThai(ten=R.ANH, cua_so_bat_dau=0)
    # 1 ảnh đã vào, còn ảnh chờ, người chờ LLM còn 150 s < 45 + 110 + 30
    moi, _ = R.buoc_thuan(tt, qs(job_anh_cho=3, lease_anh=1, anh_bat_dau_trong_cua_so=1,
                                 nguoi_cho_llm=1, han_chot_llm_s=150), TS, 60)
    assert moi.ten == R.TRA_ANH

def test_khong_ai_cho_llm_thi_ve_tiep_qua_tran():
    tt = R.TrangThai(ten=R.ANH, cua_so_bat_dau=0)
    moi, _ = R.buoc_thuan(tt, qs(job_anh_cho=9, anh_bat_dau_trong_cua_so=7), TS, 2000)
    assert moi.ten == R.ANH

def test_tra_anh_cho_luot_ve_dang_chay():
    tt = R.TrangThai(ten=R.TRA_ANH)
    moi, l = R.buoc_thuan(tt, qs(lease_anh=1, vram_3090_mib=100), TS, 5)
    assert moi.ten == R.TRA_ANH and l == ()

def test_nap_loi_lui_dan():
    tt = R.TrangThai(ten=R.NAP_LLM)
    tt, _ = R.buoc_thuan(tt, qs(nap_ket_qua="loi"), TS, 0);   assert (tt.ten, tt.lan_nap_loi) == (R.LOI_NAP, 1)
    tt2, l = R.buoc_thuan(tt, qs(), TS, 29);                  assert tt2.ten == R.LOI_NAP
    tt3, l = R.buoc_thuan(tt, qs(), TS, 30);                  assert (tt3.ten, l) == (R.NAP_LLM, (R.NAP_LLM_LENH,))

def test_mo_cho():
    assert R.mo_cho(R.LLM, "mac_dinh") and not R.mo_cho(R.XA_LLM, "mac_dinh")
    assert R.mo_cho(R.ANH, "theo_lo") and not R.mo_cho(R.TRA_ANH, "theo_lo")
```
  Đối chứng: đổi điều kiện `XA_LLM` thành chỉ kiểm `lease_llm == 0` ⇒ `test_khong_bao_gio_nha_llm_khi_con_luot_chay` ĐỎ.
- [ ] **Step 2–4:** FAIL → viết → PASS. **Step 5:** Commit.

### Task 5.3: Luật 0 `CHO_RESIDENCY` trong admission  `[CONTROL PLANE]`

**Files:** Modify `platform_core/llm/luat_nhan.py` (`CHO_RESIDENCY = "cho_residency"`; `ThamSo.residency_mo: bool = True`; đầu `xet()`: `if not ts.residency_mo: return PhanXu(False, CHO_RESIDENCY)`), `platform_core/llm/admission.py` (`xet_va_giu`: nếu `AdmissionModel.residency_group`, đọc dòng `gpu_residency` **trong** advisory lock của resource, `residency_mo = residency.mo_cho(tt.ten, am.vai_tro)`), `platform_core/llm/phong_cho.py` (lý do chờ `cho_residency` tính vào `cho_residency_s`). Test `tests/test_1217_residency_admission.py`.

- [ ] **Step 1: Test:** trạng thái `ANH` ⇒ lượt `ltt-3.8` bị `CHO_RESIDENCY`, lượt `ltt-3.5` vẫn được nhận; trạng thái `LLM` ⇒ job ảnh bị `CHO_RESIDENCY`; stream đang chờ vì residency nhận nhịp tim với mã lý do `cho_residency`; sync chờ quá ngân sách ⇒ 429 có `Retry-After`. PostgreSQL (khuôn `test_73`): chuyển `LLM→XA_LLM` đồng thời 50 lượt xin ⇒ sau khi chuyển, **0** lease `ltt_38_3090` mới được cấp.
- [ ] **Step 2–4:** FAIL → sửa → PASS; hồi quy `test_1203`, `test_1204`. **Step 5:** Commit.

### Task 5.4: Lệnh residency ở máy B; gỡ hai trọng tài cũ  `[MACHINE B] [3090]`

**Files:**
- Modify `llm_gateway/api.py`: `GET /v1/residency/trang_thai` ⇒ `{"llm_da_nap": bool (từ llama-swap /running), "inflight": {model: n} (SoTheoModel), "vram_mib": {uuid: n}, "nap_ket_qua": ""|"ok"|"loi"}`; `POST /v1/residency/nha {"model":"qwen38-api"}` ⇒ **409** nếu `inflight>0`, không thì `POST http://127.0.0.1:8280/api/models/unload/qwen38-api` ⇒ 200 `{"da_nha": true}`; `POST /v1/residency/nap {"model":"qwen38-api"}` ⇒ 409 nếu `vram_mib(uuid 3090) > VRAM_SACH`, không thì chạy nền: một lượt `max_tokens=1` qua llama-swap + chờ `/health` ⇒ `nap_ket_qua`. Cả ba cần token gateway như `/v1/*`.
- Modify `render_gateway/api.py`: `POST /v1/nha_comfy` ⇒ gọi ComfyUI `/free {unload_models, free_memory}`.
- Delete `llm_gateway/don_dep.py` + gọi của nó ở `api.py:396-434`; gỡ nhánh ComfyUI/util của `llm_gateway/trong_tai.py:219-285`; gỡ `xin_card`/`TraCard` khỏi `render_gateway/nhuong_card.py` + chỗ gọi `render_gateway/api.py:164-198,304-305`; bỏ `LTT_HO_DUNG_CARD`, `LTT_TRA_CARD_GIAY` khỏi `C:\ProgramData\LTTRender\gateway.env` (qua ssh).
- Test `tests/test_1218_gateway_residency.py`.

- [ ] **Step 1: Test:** `nha` khi còn một suất `qwen38-api` ⇒ 409, **không** gọi llama-swap (httpx giả ghi lại); `nha` khi rảnh ⇒ đúng một `POST /api/models/unload/qwen38-api`; `nap` khi VRAM 3090 (gpu_uuid tiêm) 9.000 MiB ⇒ 409; chốt tĩnh: không còn chuỗi `8280/unload` hay `GET /unload` trong `render_gateway/`, không còn `don_dep` trong `llm_gateway/`. Đối chứng: phục hồi `xin_card` ⇒ chốt tĩnh ĐỎ.
- [ ] **Step 2–4:** FAIL → sửa → PASS; hồi quy `test_250`, `test_363`, test render hiện có. **Step 5:** Deploy hai gateway lên máy B (`deploy.ps1` → restart) + sửa `LTTRender\gateway.env`. Commit.

### Task 5.5: Nối trọng tài + khai tài nguyên ảnh  `[MACHINE A] [3090]`

**Files:** Modify `platform_core/llm/residency.py` (thêm `buoc(db, *, may_b=MayBResidency(), bay_gio=time.time) -> TrangThai`: advisory lock `residency:rtx3090` + khoá hai resource theo thứ tự tên; dựng `QuanSat` từ `ExecutionLease`, `jobs` (queued theo resource), `llm_waiters` (hạn chót = `created_at + tran_cua_cua`), `GET /v1/residency/trang_thai`; ghi dòng `gpu_residency` với `phien_ban+1`; phát lệnh qua gateway), `platform_core/job_runner.py` (`_mot_luot_bao_tri`: gọi `residency.buoc` mỗi lượt — chu kỳ `POLL_INTERVAL_S=2 s`, `job_runner.py:39,1561-1603`), `apps/{anhnoibo,taoanh,thumbnail}/manifest.py` (`admission_theo_model={"*": AdmissionModel("anh_3090", 1, 0, "rtx3090", "theo_lo")}`), `platform_core/job_runner.py` (job ảnh không được nhận ⇒ `_tra_ve_hang_doi` như job LLM). Test `tests/test_1219_residency_noi.py`.

- [ ] **Step 1: Test (SQLite + máy B giả):** một job ảnh vào hàng khi có 1 lease 3.8 đang chạy ⇒ các bước: `XA_LLM` (lease 3.8 mới bị từ chối) → lease cũ nhả → `NHA_LLM` (đúng một lệnh `nha`) → `ANH` → job ảnh được nhận → xong → `TRA_ANH` → `free_comfy` → VRAM giả hạ → `NAP_LLM` → `ok` → `LLM` ⇒ người chờ 3.8 được nhận. Lỗi máy B (`trang_thai` ném) ⇒ bước **không** chuyển trạng thái nào (fail-closed), log cảnh báo. Chốt tĩnh: cả ba manifest ảnh có `anh_3090` + `rtx3090` + `theo_lo`; `platform_core` không chứa tên app (`test_147`).
- [ ] **Step 2–4:** FAIL → sửa → PASS. **Step 5:** Deploy máy A (quy trình `docs/16_CAP_NHAT_VA_DEPLOY.md`: đồng bộ trunk → gate → ff → `setup\2-cai-dat.ps1` cần UAC chủ dự án bấm) — hỏi các phiên khác trước deploy. Kiểm trên production: tạo một job ảnh thật ⇒ quan sát chu trình ở `/ops/jobs-metrics` + VRAM theo UUID. Commit.

**Điểm lùi Pha 5:** `app.previous` máy A; snapshot máy B (có `don_dep`/`xin_card` cũ + env cũ). Migration `gpu_residency` cộng thêm, vô hại với mã cũ.

---

## Pha 6 — Quan sát + phần GPU còn lại

### Task 6.1: `render_gateway/busy.py` theo UUID  `[MACHINE B]`

**Files:** Modify `render_gateway/busy.py:63-234,434-435` (dùng `llm_gateway.gpu_uuid` hoặc bản sao đọc cùng `gpu_may_b.json` — chọn import nếu `render_gateway` đã import `llm_gateway` ở đâu đó; không thì module riêng đọc cùng tệp + test đối chiếu); `VRAM_CAN_TOI_THIEU_MB` áp trên UUID 3090. Test: mở rộng `tests/test_1213_gpu_uuid_may_b.py`.
- [ ] TDD: đầu ra nvidia-smi 2 card ⇒ `busy` chỉ đọc UUID 3090; tiến trình python trên 5060 Ti không làm render "bận". Commit + deploy.

### Task 6.2: `test_637` chặn `--load-mode` hại  `[TEST]`

**Files:** Modify `tests/test_637_nha_ve_ram.py:57-76`.
- [ ] Thêm mẫu: `--load-mode\s+(none|dio)\b`, `-lm\s+(none|dio)\b`, `LLAMA_ARG_LOAD_MODE`; giữ mẫu cũ. Đối chứng: thêm `--load-mode none` vào một hồ sơ (bản tạm trong `tmp_path`, không ghi cây — memory "chốt không ghi vào cây") ⇒ ĐỎ. Commit.

### Task 6.3: Sổ lượt + metrics + báo động  `[MACHINE A]`

**Files:** Modify `platform_core/models.py` + migration (`llm_waiters.model`, `llm_waiters.cho_residency_s`), `platform_core/job_metrics.py` (khối `llm_theo_model`: độ sâu phòng chờ model × lớp, tuổi lâu nhất; khối `residency_3090`: trạng thái, thời gian trong trạng thái, số lần + thời gian nạp lại hôm nay), `tools/soi_cong_llm.py` (báo động: VRAM trống < ngưỡng hoặc `Shared Usage > 0` theo UUID; `requests_deferred > 0` qua `/upstream/<model>/metrics`; log "Context size has been exceeded"; `LOI_NAP`; tiến trình ngoài danh sách trên UUID 3090). Test `tests/test_1220_quan_sat_dual.py`.
- [ ] TDD mỗi báo động một ca + đối chứng; `/ops/jobs-metrics` có hai khối mới. Commit + deploy.

---

## Pha 7 — Tài liệu vận hành

### Task 7.1: Q mới + runbook + nhật ký  `[DEPLOYMENT]`

**Files:** Modify `docs/QUYET_DINH_NEN_TANG.md` (Q mới: hai model nhà, trọng tài 3090, cắt tên, giá theo model — trỏ `DECISION_LOG.md`), `docs/NHAT_KY.md`, `docs/KE_HOACH_TRIEN_KHAI.md` (trạng thái pha); Create `docs/ltt_llm_dual/RUNBOOK.md` (deploy A+B qua Nexus, restart llama-swap, đọc residency, xử lý `LOI_NAP`, đường lùi từng pha có lệnh cụ thể, truy vấn sổ lượt để phân tích).
- [ ] `python tools\cua_so_yen.py trang-thai` ⇒ rảnh; `findstr /C:"loi_cho_bo_test" tools\gate.py` ⇒ có; `python tools\gate.py` ⇒ `RESULT: PASS`. Commit + push.

---

## Sau plan này (không thuộc plan)

Spec 2 (Input Intelligence MVP) → brainstorming/spec/plan riêng → **nghiệm thu tích hợp A–Q một lần** (`docs/superpowers/specs/2026-09-11-ltt-llm-dual-model-design.md` §23) → bật + cắt tên cho khách (D08) → theo dõi 24 h.

## Phụ lục — ánh xạ spec → task

| Spec | Task |
|---|---|
| §2 hợp đồng, D02 | 2.3 · D09 | 2.4 |
| §3.1 `admission_theo_model` | 2.1, 2.2 |
| §5–6 vòng đời, D04 | 1.5, 2.2 |
| §7 dữ liệu | 1.3, 5.1, 6.3 |
| §8 admission theo model | 2.1, 2.2, 2.6, 5.3 |
| §10–11 danh tính + cách ly GPU | 0.2, 0.3, 4.1, 6.1 |
| §12 residency | 5.1–5.5 |
| §13 kho ấm | 3.2 (G5), 6.2 |
| §14 engine + cổng đo | 3.1–3.3 |
| §15 quan sát | 4.3, 6.3 |
| §16 hủy | 4.3 (+ D04 ở 1.5) |
| §17 tiền | 1.5, 2.5 |
| §19–21 triển khai, di trú, đường lùi | 0.1, 1.1, 2.3, điểm lùi từng pha, 7.1 |
| §22 trạng thái lỗi | 4.2, 5.4, 5.5, 6.3 |
| §23 nghiệm thu | sau plan (một lần) |

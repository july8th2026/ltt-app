# LTT LLM AUDIT STATE

> Handoff SSOT cho chương trình audit `ltt_llm`. **Ngắn có chủ ý** — bằng chứng
> chi tiết nằm ở `reports/`, không paste log vào đây.

## Program
- **Current phase:** 00 — Discovery & Frozen Baseline
- **Last completed phase:** (chưa có phase nào trước 00)
- **Repo revision / branch:** `2ed62d7` → nhánh `admin-mvp-v3`
  *(cây có 38 tệp chưa commit lúc chạy baseline — 34 của phiên `-e7`, xem §WIP)*
- **Machine A:** `DESKTOP-H9AGFUQ` · 192.168.2.17 · Python 3.13.12 ·
  `LTTStudioWeb` + `LTTStudioWorker` + `LTTStudioVoice` + `LTTStudioCodex` Running
- **Machine B:** `MAY-B` / `DESKTOP-MR9CFK0` · 192.168.2.66 · RTX 3090 24.576 MiB ·
  driver 610.88 · `LTTLlmGateway` + `LTTLlamaSwap` Running/Automatic
- **Runtime model/build:**
  - `Qwen3.8-27B-UD-Q4_K_M.gguf` 15,33 GB + `mmproj-F16.gguf` 0,86 GB
  - `llama-server` **0.3.0-dev build 10689 commit 57291f264** (Clang 20.1.8)
  - `llama-swap` **v250 (60226b6)** built 2026-08-14
  - cờ: `--jinja --reasoning-format deepseek -fa 1 -ngl 999 --parallel 1
    --spec-type draft-mtp --spec-draft-n-max 2 -c 131072`
    KV cache `--cache-type-k q8_0 --cache-type-v q8_0`
- **Live access available:** **YES** — máy B điều khiển đầy đủ qua LTT Nexus;
  máy A đọc được `secrets/` qua cầu hẹp `setup/chay_voi_env.ps1`

## Frozen baseline
- **Baseline commit:** `2ed62d7` (+ WIP của `-e7`, chưa commit)
- **Baseline test artifact:** `python tools/gate.py --phien a5` →
  **`RESULT: PASS`** kèm `[1 BUOC TU BO QUA: bat bien da tien trinh]`,
  `bo test (song song)` 293,8 s, 3 bộ frontend xanh
- **Bằng chứng bổ sung ngoài gate:** `test_214` (bất biến đa tiến trình) —
  **7 passed / 134,61 s**, chạy qua `chay_voi_env.ps1 -Viec cong-daluong` dưới
  Scheduled Task/SYSTEM. Đây là **lần đầu tiên** nó chạy trên máy này.
- **Baseline benchmark artifact:** ⛔ **PENDING LIVE** — chưa đo. Prompt 04
  không được tuyên bố performance gain nếu không có mốc so sánh tương đương.
- **Baseline score:** xem §Scores
- **Baseline confidence:** MEDIUM

🔴 **BASELINE NÀY LÀ CỦA MỘT HỆ THỐNG VỪA ĐƯỢC VÁ.** Sáng 31/08 cổng VLM rò suất
và ngừng dịch vụ **hơn sáu giờ**; bản vá ba lớp deploy lên cả hai máy lúc
18:1x–18:5x, **trước** khi baseline này được chụp. Trạng thái trước-vá **không
lấy lại được**. Mọi so sánh ở Prompt 04 phải neo vào mốc này, không vào bất kỳ
số đo nào trước 31/08. Xem `docs/VLM_NOI_BO/SU_CO_2026-08-31_RO_SUAT.md`.

## Architecture truth

| | |
|---|---|
| **Primary async path** | `POST /api/v1/quotes` → `/jobs` → worker → artifact (`server/api/jobs.py`) |
| **Primary sync path** | `POST /api/v1/chat/completions` — `SYNC_BILLED` (`server/api/chat.py`) |
| **Primary stream paths** | `POST /api/v1/messages` (Anthropic) · `POST /api/v1/responses` (OpenAI Responses) — cả hai ở `server/api/streaming.py` |
| **Machine B path** | máy A → `http://192.168.2.66:8299` → llama-swap `127.0.0.1:8280` → `llama-server` |
| **Admission owner** | `platform_core/llm/admission.py` — `acquire/heartbeat/release/reclaim_expired` |
| **Billing truth owner** | `platform_core/llm/thanh_toan.py` — `giu_cho_luot → quyet_toan_luot / hoan_luot / quyet_toan_hoac_hoan`; giá ở `gia_token.tinh/uoc_tran` |
| **Context SSOT owner** | `apps/ltt_llm/ngan_sach.py` (3 số gõ tay, phần còn lại dẫn xuất) — **có bản sao ở `llm_gateway/ngan_sach.py`** |
| **Busy/error semantic owner** | `llm_gateway/gioi_han.py` + `trong_tai.py` + `don_dep.py` (máy B) → `platform_core/llm/luong_vlm.py` (máy A dịch) |
| **Runtime config owner** | `C:\ProgramData\LTTLlm\gateway.env` — **do `deploy.ps1` sinh**, thắng cả `os.environ`; sửa tay là mất ở lần deploy sau |

### Thứ tự cửa stream (đo bằng đọc mã, `server/api/streaming.py`)

```
580  admission.acquire(...)        ve nhan vao
633  thanh_toan.giu_cho_luot(...)  giu tien
650  db.commit()                   CHOT GIAO DICH truoc khi cham model
655  luong_vlm.mo(...)             mo luong toi may B
690  StreamingResponse(_phat(...), background=BackgroundTask(release))
```

## Critical invariants

| ID | Invariant | Owner | Evidence | Status |
|---|---|---|---|---|
| INV-001 | Nhiều worker không gửi webhook trùng / không nhân đôi cảnh báo / credit khớp | `job_runner` + `leases` | `test_214` **7 passed 134,61 s** (31/08) | **VERIFIED-LIVE** |
| INV-002 | Suất của cổng VLM không rò; rò thì tự thu hồi và **kêu** | `llm_gateway/gioi_han.py` | `test_363` 13 phép kiểm; `/health` có `giu_lau_nhat_giay`/`da_thu_hoi` | **VERIFIED** |
| INV-003 | Bận ⇒ khách **không** bị thu tiền, có `Retry-After` | `streaming.py` · `chat.py` | sự cố 31/08: 89 lượt hỏng, `credit=+0` mọi dòng | **VERIFIED-LIVE** |
| INV-004 | Bận (429 của B) **không** bị hiểu là provider hỏng ⇒ không disable khoá | `luong_vlm.py` | khoá `ltt_llm` vẫn `active` sau 89 lượt hỏng | **VERIFIED-LIVE** |
| INV-005 | Ngân sách token có **một** nguồn chân lý, ba tầng không trôi | `apps/ltt_llm/ngan_sach.py` | `test_334` — `TestDoiChieuMayB` · `TestDoiChieuNenTang` · `TestDoiChieuKhoMayB` | **VERIFIED** |
| INV-006 | Giá không bao giờ suy ra từ con số **khách khai** | `gia_token` + `apply_server_measurements` | Q84 / H35.10 | UNSEEN *(Prompt 02)* |
| INV-007 | Tổ hợp tham số sai bị chặn **trước** `price()`/hold | `invocation.validate_public_input` | `test_336` | **VERIFIED** |
| INV-008 | Khoản giữ chỗ treo được tự hoàn | `credit.tu_hoan_treo` (H41.3) | có hàm + chạy dưới `_mot_luot_bao_tri` | INFERRED *(Prompt 02)* |

## Contradiction scan — Prompt 00 §5

| # | Mâu thuẫn | Bằng chứng | Ghi chú |
|---|---|---|---|
| **C-01** | **Trần input `65K` đã chết vẫn còn ở 6 chỗ, và TỚI TAY KHÁCH** | `llm_gateway/deploy/llama-swap.yaml:130` `description: "... input public 65K"` → phơi qua `llm_gateway/api.py:181` ở `/v1/models`. Trần thật `TOKEN_VAO_TRAN = 96_256`, công bố client `88_555` | Prompt 00 §5 gọi đích danh loại này. Còn ở `apps/ltt_llm/manifest.py:30`, `llm_gateway/catalog.py:32`, `llama-swap.yaml:111/117/130`, và `-c 65536` dòng 184 (hồ sơ vision) |
| **C-02** | `DONG_THOI_MAY_B = 1` ở máy A là **bản sao** của `max_dong_thoi = 1` ở máy B | `apps/ltt_llm/ngan_sach.py:167` vs `llm_gateway/gioi_han.py` | Hai nguồn cho một sự thật. `test_334` có đối chiếu — cần xác minh nó phủ **con số này** |
| **C-03** | Bộ lọc che bí mật của tôi che nhầm `MAX_INPUT_TOKENS`/`MAX_OUTPUT_TOKENS` | mẫu `TOKEN` khớp quá rộng | Không phải lỗi hệ thống, là lỗi công cụ đo của tôi. Giá trị thật: 96.256 / 32.768 |

## Decisions

| ID | Phase | Candidate | Decision | Why |
|---|---|---|---|---|
| D-00-1 | 00 | Chụp baseline **sau** bản vá rò suất | KEEP | Baseline = production hiện tại. Trạng thái trước-vá không lấy lại được; khai rõ tốt hơn giả vờ có mốc cũ |
| D-00-2 | 00 | `gate.py` chỉ có PASS/FAIL | **CHANGE** | Một bước tự bỏ qua trông y hệt một bước đạt ⇒ hai phiên đọc cùng dòng RESULT trái ngược nhau trong một ngày |
| D-00-3 | 00 | `check_multiproc.py` trả `return 0` khi bỏ qua | **KEEP** | Đúng: máy thiếu PostgreSQL vẫn phải chạy được gate. Chỗ sai là chỗ **đọc** |

## Changes kept

| Phase | Change | Files | Verification | Rollback |
|---|---|---|---|---|
| 00 | `gate.py` ba trạng thái `PASS/BOQUA/LOI` + dòng RESULT tự khai | `tools/gate.py` | `test_365` 10 phép kiểm; thấy `[BOQUA]` trong lượt gate thật | git revert |
| 00 | Cầu hẹp chạy việc kiểm với env production | `setup/chay_voi_env.ps1` | `test_214` 7 passed | xoá tệp |
| 00 | Ba phép kiểm đổi từ **đếm ký tự** sang **quan hệ cú pháp** | `test_362` · `test_365` | 22 phép kiểm xanh | git revert |

## Benchmark summary

| Metric | Baseline | Notes |
|---|---:|---|
| *(mọi mục)* | **PENDING LIVE** | Chưa đo. Máy B rảnh ⇒ đo được ở Prompt 04 |
| VRAM khi model nạp | 22.376 / 24.576 MiB | đo 31/08 sau một lượt gọi, GPU 0 % tải — **91 %** |
| Một lượt `/v1/responses` nguội | 33 s | gồm nạp model 27B từ nguội, 8 token ra |

## Scores — baseline

| Domain | Trọng số | Điểm | Confidence |
|---|---:|---:|---|
| Correctness & invariants | 20 | 16 | MEDIUM |
| Money/admission/failure semantics | 15 | 13 | HIGH *(INV-001/003/004 có bằng chứng sống)* |
| Model quality & tool/context fidelity | 15 | **6** | LOW — **không có bộ đánh giá nào** |
| Performance/resource efficiency | 15 | **7** | LOW — chưa đo |
| Reliability/recovery | 10 | 7 | MEDIUM |
| Security boundaries | 10 | 8 | MEDIUM |
| Observability/operations | 5 | 4 | MEDIUM |
| Tests/evidence/reproducibility | 5 | 4 | HIGH |
| Maintainability/SSOT/deployment | 5 | 4 | MEDIUM |
| **TOTAL** | **100** | **69** | **MEDIUM** |

⛔ **69 không phải "hệ thống tệ".** Phần lớn điểm trừ nằm ở **thiếu phép đo**, không ở
hỏng đã biết: G5 không có bộ đánh giá nào, và mọi số hiệu năng đều `PENDING LIVE`.
Hai phase 03+04 có thể nâng đáng kể mà không cần đổi một dòng mã nào.

## Open risks

| P | Risk | Phase | Cần bằng chứng gì | Status |
|---|---|---|---|---|
| P1 | **G5 không có chủ sở hữu** — không đo được chat/coding/tool/long-context/tiếng Việt/vision | 04 | phải **xây** bộ đánh giá | OPEN |
| P2 | `65K` chết tới tay khách qua `/v1/models` | 01 | sửa 6 chỗ + một nguồn chân lý | OPEN |
| P2 | `max_dong_thoi = 1` ⇒ một sự cố suất = **100 %** ngừng dịch vụ | 03 | không có mức suy giảm ở giữa | OPEN |
| P3 | VRAM 22,4/24,6 GiB khi model nạp; ba hộ dùng chung card | 03/04 | benchmark phải kèm ảnh chụp `trong_tai` | OPEN |
| P3 | Bước gate multiproc vẫn bỏ qua ở đường chạy thường | 06 | cần env production; đã có cầu | MITIGATED |

## Pending live canaries
- Benchmark Qwen (D30–D36) — máy B rảnh, chưa chạy
- Canary client thật: Codex CLI · Claude Code · VS Code (E15–E17) — cần một khoá API
- Recipe nối chuỗi artifact đầu-tới-cuối trên production

## User WIP — không chạm

`-e7` giữ 34 tệp chưa commit (LTT VOICE P1–P9). Trong phạm vi audit chỉ có
**một** tệp: `platform_core/public_api/governance.py` (khai hai bảng
`voice_project`/`voice_block`) — **không chạm đường thi hành `ltt_llm`**.

## Next phase
- **Prompt:** `03_MACHINE_B_GATEWAY_GPU_CONTROL.md`
  *(đổi thứ tự có chủ ý: 03+04 tự chủ 100 %, và máy B đang rảnh — điều kiện có
  thể mất bất cứ lúc nào khi dự án video chạy lại)*
- **Must read:** `llm_gateway/*` · `docs/VLM_NOI_BO/SU_CO_2026-08-31_RO_SUAT.md` ·
  `Ket_noi.md` (đường vào máy B)
- **Questions:** C16–C21 (dò bận/CPU degraded) đo được thật tới đâu? `don_dep`
  có dọn nhầm workload của người khác không?
- **Do not disturb:** 34 tệp WIP của `-e7`; `apps/ltt_voice/**`

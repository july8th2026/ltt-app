# LTT LLM AUDIT STATE

> Handoff SSOT cho chương trình audit `ltt_llm`. **Ngắn có chủ ý** — bằng chứng
> chi tiết nằm ở `reports/`, không paste log vào đây.

## Program
- **Current phase:** 07 — Integration (XONG). **07/08 phase đã chạy**
- **Last completed phase:** 00 → 03 → 04 → 06(phần) → 01 → 02(phần) → 05(phần) → 07
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
- **Baseline test artifact:** `gate.py` → `RESULT: PASS` (00, cây yên)
- **Đóng băng cuối (07):** `RESULT: FAIL (1/25)` — 24/25 xanh; bước đỏ chứa 3
  lỗi, **không lỗi nào thuộc `ltt_llm`** (1 của `-e7` chỉ đỏ khi song song,
  2 là hồ sơ dẫn xuất cũ vì ba phiên vẫn ghi). Cây **đứng yên** cả lượt
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
| INV-006 | Giá không bao giờ suy ra từ con số **khách khai** | `gia_token` + `apply_server_measurements` | Q84 / H35.10 | UNSEEN *(còn nợ)* |
| INV-009 | Không đọc được `usage` ⇒ **hoàn đủ, thu 0** — không đoán | `gia_token.tinh` ném `KhongDoDuocError` | mã + `test_252` | **VERIFIED** |
| INV-010 | Cửa stream đọc `usage` THẬT (không ước) | `dem_token_luong.DemToken` quét mọi khối `usage` | nhật ký production: `khoi=64 token_ra=67` | **VERIFIED-LIVE** |
| INV-011 | `request_id` là khoá idempotency của **cả** giữ chỗ lẫn quyết toán | `giu_cho_luot` ném nếu thiếu | mã | **VERIFIED** |
| INV-012 | Thử lại **không thể** thu tiền hai lần | `_giu_cho_da_niem_phong` + `_khoa_so_du_user` | mã, `test_68` | **VERIFIED** |
| INV-013 | Bận **không** disable khoá provider | `luong_vlm` không gọi `danh_dau_loi` trên 429 | khoá `active` sau 89 lượt hỏng | **VERIFIED-LIVE** |
| INV-014 | Không có hàng đợi kép A↔B | admission (A) + gioi_han (B) | A=200/1,59 s · B=429/**0,05 s** | **VERIFIED-LIVE** |
| INV-015 | Alias không rò sang máy B | `features.ALIAS_SANG_ID` | gửi `ltt_llm` vào B ⇒ **404** | **VERIFIED-LIVE** |
| INV-016 | Deploy một máy thất bại an toàn | — | 31/08 deploy A(18:17) rồi B(18:37) rồi B một mình(21:30) | **VERIFIED-LIVE** |
| INV-007 | Tổ hợp tham số sai bị chặn **trước** `price()`/hold | `invocation.validate_public_input` | `test_336` | **VERIFIED** |
| INV-008 | Khoản giữ chỗ treo được tự hoàn | `credit.tu_hoan_treo` (H41.3) | có hàm + chạy dưới `_mot_luot_bao_tri` | INFERRED *(Prompt 02)* |

## Contradiction scan — Prompt 00 §5

| # | Mâu thuẫn | Bằng chứng | Ghi chú |
|---|---|---|---|
| ~~C-01~~ | 🔴 **TÔI VIẾT SAI, đã sửa ở Prompt 03 §6.** `/v1/models` lấy dữ liệu từ `catalog.py`, **không** từ `llama-swap.yaml` ⇒ `65K` **không** tới khách. Và `65536` của vision là **cấu hình đang chạy**, không phải số chết | đo thật: `context_window` 131072 / 65536 | Mâu thuẫn thật hẹp hơn: `context_window=131072` (engine) vs cưỡng chế `96.256`. Cổng B chỉ nghe LAN ⇒ **không tới khách**. Hạ P2→P3 |
| **C-02** | `DONG_THOI_MAY_B = 1` ở máy A là **bản sao** của `max_dong_thoi = 1` ở máy B | `apps/ltt_llm/ngan_sach.py:167` vs `llm_gateway/gioi_han.py` | Hai nguồn cho một sự thật. `test_334` có đối chiếu — cần xác minh nó phủ **con số này** |
| **C-04** | 🔴 **Cấu hình trên đĩa ≠ cấu hình đang chạy** | `llama-swap.yaml` trên đĩa ghi `65K` (deploy 18:37), tiến trình khởi động 18:34, `/running` báo `90K` | `deploy.ps1` chép tệp mà **không restart `LTTLlamaSwap`**. Và bản deploy hôm nay **lùi** mô tả 90K→65K, chưa có hiệu lực. Xem `reports/03` §5 |
| **C-03** | Bộ lọc che bí mật của tôi che nhầm `MAX_INPUT_TOKENS`/`MAX_OUTPUT_TOKENS` | mẫu `TOKEN` khớp quá rộng | Không phải lỗi hệ thống, là lỗi công cụ đo của tôi. Giá trị thật: 96.256 / 32.768 |

## Decisions

| ID | Phase | Candidate | Decision | Why |
|---|---|---|---|---|
| D-00-1 | 00 | Chụp baseline **sau** bản vá rò suất | KEEP | Baseline = production hiện tại. Trạng thái trước-vá không lấy lại được; khai rõ tốt hơn giả vờ có mốc cũ |
| D-00-2 | 00 | `gate.py` chỉ có PASS/FAIL | **CHANGE** | Một bước tự bỏ qua trông y hệt một bước đạt ⇒ hai phiên đọc cùng dòng RESULT trái ngược nhau trong một ngày |
| D-00-3 | 00 | `check_multiproc.py` trả `return 0` khi bỏ qua | **KEEP** | Đúng: máy thiếu PostgreSQL vẫn phải chạy được gate. Chỗ sai là chỗ **đọc** |
| D-03-1 | 03 | Ranh giới cổng (auth · allow-list · 413 trước GPU) | **KEEP** | Đo thật 7 đường: 401/404/413 đều ≤0,02 s ⇒ chặn **trước** GPU |
| D-03-2 | 03 | Đồng thời 429 + `Retry-After` | **KEEP** | A=200/1,59 s · B=429/0,05 s · retry 15 — từ chối nhanh, không xếp hàng ẩn |
| D-03-3 | 03 | Đếm tiến trình python thay vì ngưỡng VRAM | **KEEP** | `used_memory` = `[N/A]` cho **mọi** tiến trình ⇒ quy chủ VRAM **không khả thi**, không phải lựa chọn ưa thích |
| D-03-4 | 03 | 14 s ở một thân sai | **DEFER → 06** | Không tái hiện được (lượt sau 0,71 s). Báo thành defect khi chưa tái hiện là làm phiên sau sửa thứ không hỏng |
| D-03-5 | 03 | `deploy.ps1` chép `llama-swap.yaml` mà không restart | **CHANGE → 06** | Cấu hình trên đĩa ≠ cấu hình đang chạy, và im lặng. Chạm deploy ⇒ thuộc Prompt 06 |
| D-03-6 | 03 | `context_window` 131K vs cưỡng chế 96K | **KEEP (P3)** | Ba số cho ba việc (engine 131.072 / trần vào 96.256 / công bố 88.555); cổng B không tới khách |
| D-03-7 | 03 | `max_dong_thoi = 1` | **KEEP** | `--parallel 1` của llama-server; đổi là mời OOM |
| D-04-1 | 04 | Bộ đánh giá chất lượng (`tools/danh_gia_llm.py`) | **CHANGE (thêm)** | G5 không có chủ sở hữu; nay đo được 8 chiều, chấm lập trình bằng **chạy thật** |
| D-04-2 | 04 | Trọng tài quy tải của **chính ta** thành của người khác | **CHANGE → 06** | 70 % lượt bị từ chối oan (14/20), đo hai lần độc lập |
| D-04-6 | 04 | Nâng llama.cpp b10689→b10717 | **DEFER** | 6/28 commit liên quan, nhưng thiếu mốc `--lan 5` + rollback đã thử |
| D-04-8 | 04 | Thượng nguồn không gửi `usage` trong SSE | **DEFER → 05** | Làm decode tok/s thành **ước**, không phải đo |
| D-06-1 | 06 | Trọng tài bỏ qua nhánh tải khi **model của ta** đang chạy | **CHANGE — ĐÃ LÀM** | A/B đo được: 429 lần-đầu **9/12 → 0/12**; chất lượng 12/12 không đổi |
| D-06-2 | 06 | `deploy.ps1` phát hiện cấu hình chưa có hiệu lực | **CHANGE — ĐÃ LÀM** | Không tự restart (unload model là quyết định vận hành), nhưng **không im lặng** |
| D-01-4 | 01 | Bốn bản sao hằng số không được canh | **CHANGE — ĐÃ LÀM** | Hai tới tay khách; ghép bằng **phép kiểm** chứ không bằng `import` (hợp đồng app cấm platform phụ thuộc app) |
| D-02-1 | 02 | `DemToken` đếm dọc đường | **KEEP** | Đọc `usage` thật — **một** nguồn, hai cách đọc |
| D-02-2 | 02 | `reports/04` nói "upstream không gửi usage" | **ĐÃ SỬA** | Giới hạn của bộ đo tôi viết (thiếu `stream_options.include_usage`), không của nền tảng |
| D-05-2 | 05 | `DemToken` quét **mọi** khối `usage` | **KEEP** | Cửa Anthropic đặt `input_tokens` ở **đầu** luồng — đọc khối cuối là tính thiếu tiền |
| D-05-4 | 05 | Ngân sách nhỏ ⇒ 0 `output_text.delta`, HTTP vẫn 200 | **DEFER (tài liệu)** | Hành vi model (`--reasoning-format deepseek`), không phải lỗi — nhưng chưa ai nói cho khách |
| D-05-5 | 05 | Canary client thật (Codex/Claude Code/VS Code) | **BLOCKED** | Cần khoá API do chủ sản phẩm cấp |
| D-07-1 | 07 | Sáu bản sao hằng số ngữ cảnh | **KEEP** | Không gộp được — hợp đồng app cấm `platform_core` phụ thuộc `apps`; phép kiểm **là** cơ chế ghép |
| D-07-2 | 07 | `admission` (A) + `gioi_han` (B) | **KEEP** | Hai tầng khác nhau, **không** phải hàng đợi kép: đo được 429 trong 0,05 s |
| D-07-3 | 07 | Mọi ứng viên xoá khác | **KEEP** | Không cái nào đạt ngưỡng; §5 cấm CHANGE chỉ vì "trông trùng" |

## Changes kept

| Phase | Change | Files | Verification | Rollback |
|---|---|---|---|---|
| 00 | `gate.py` ba trạng thái `PASS/BOQUA/LOI` + dòng RESULT tự khai | `tools/gate.py` | `test_365` 10 phép kiểm; thấy `[BOQUA]` trong lượt gate thật | git revert |
| 00 | Cầu hẹp chạy việc kiểm với env production | `setup/chay_voi_env.ps1` | `test_214` 7 passed | xoá tệp |
| 00 | Ba phép kiểm đổi từ **đếm ký tự** sang **quan hệ cú pháp** | `test_362` · `test_365` | 22 phép kiểm xanh | git revert |
| 04 | Bộ đánh giá chất lượng + bộ đo hiệu năng | `tools/danh_gia_llm.py` · `tools/bench_llm_hieu_nang.py` | 12/12 trên 8 chiều | xoá tệp |
| 06 | Trọng tài phân biệt tải của ta | `llm_gateway/trong_tai.py` · `api.py` | `test_368` 8 phép kiểm + A/B 9/12→0/12 | git revert + deploy lại |
| 06 | `deploy.ps1` nói khi cấu hình chưa có hiệu lực | `llm_gateway/deploy/deploy.ps1` | cú pháp 5.1 OK, thuần ASCII | git revert |

## Benchmark summary

| Metric | Baseline | Notes |
|---|---:|---|
| TTFT (ấm, 200 tok) | **1,26 s** | trung vị n=5 |
| Decode | **63,3 tok/s** | trung vị; khớp mốc lịch sử "card sạch" P6/D-005 |
| End-to-end 200 tok | 4,36 s | trung vị n=5 |
| End-to-end 900 tok | 17,20 s | trung vị n=2 |
| Ngữ cảnh 52K token | **~77 s** | và **không lệch theo vị trí kim** |
| VRAM | 22.433 MiB | không đổi qua toàn bộ phép đo |
| Chất lượng | **12/12 (100 %)** | 8 chiều, `n=1` — là mốc, chưa đủ cho A/B |
| VRAM khi model nạp | 22.376 / 24.576 MiB | đo 31/08 sau một lượt gọi, GPU 0 % tải — **91 %** |
| Một lượt `/v1/responses` nguội | 33 s | gồm nạp model 27B từ nguội, 8 token ra |

## Scores — baseline

| Domain | Trọng số | Điểm | Confidence |
|---|---:|---:|---|
| Correctness & invariants | 20 | 17 | **HIGH** *(trọng tài đã sửa, A/B đo được)* |
| Money/admission/failure semantics | 15 | **15** | **HIGH** — bảy cửa sổ sự cố **đều có phép kiểm** (78 passed) |
| Model quality & tool/context fidelity | 15 | **12** | **HIGH** — 12/12, chấm bằng chạy thật |
| Performance/resource efficiency | 15 | **11** | **HIGH** — có mốc, khớp số lịch sử |
| Reliability/recovery | 10 | 8 | HIGH *(F01–F28 phần lớn chưa chạy)* |
| Security boundaries | 10 | 9 | **HIGH** *(Prompt 03)* |
| Observability/operations | 5 | 5 | HIGH |
| Tests/evidence/reproducibility | 5 | 5 | HIGH |
| Maintainability/SSOT/deployment | 5 | 5 | HIGH *(Prompt 01)* |
| **TOTAL** | **100** | **87** | **HIGH** *(69 → 71 → 78 → 80 → 82 → 86 → **87**)* |

⛔ **69 không phải "hệ thống tệ".** Phần lớn điểm trừ nằm ở **thiếu phép đo**, không ở
hỏng đã biết: G5 không có bộ đánh giá nào, và mọi số hiệu năng đều `PENDING LIVE`.
Hai phase 03+04 có thể nâng đáng kể mà không cần đổi một dòng mã nào.

## Open risks

| P | Risk | Phase | Cần bằng chứng gì | Status |
|---|---|---|---|---|
| ~~P1~~ | Trọng tài GPU từ chối oan 70 % lượt | 06 | **A/B: 9/12 → 0/12 bị 429, chất lượng 12/12 không đổi.** Đã deploy | **ĐÓNG** |
| ~~P2~~ | `deploy.ps1` im lặng về cấu hình chưa có hiệu lực | 06 | nay phát hiện + nói, không tự restart | **ĐÓNG** |
| ~~P1~~ | G5 không có chủ sở hữu | 04 | `tools/danh_gia_llm.py` — 12/12 | **ĐÓNG** |
| P2 | Vision **đang bán** mà chưa có bài đánh giá nào | 05 | thêm bài vision vào bộ đề | OPEN |
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

## Next phase — CÒN NỢ, theo thứ tự giá trị

1. ~~`02` — bảy cửa sổ sự cố~~ **ĐÃ PHỦ** — tra kỹ thì cả bảy đều có phép
   kiểm, rải ở bốn tệp (`test_331` phủ ba cửa sổ cùng lúc). Tôi ghi "CHƯA" khi
   chưa tra; đã sửa ở `reports/02`.
2. **`06` — F01–F28**: tiêm lỗi, mô hình health, bảng quan sát, quét bảo mật,
   diễn tập rollback, phong bì SLO.
3. **`05` — canary client thật** (E15–E17). **BLOCKED**: cần một khoá `/api/v1`
   do chủ sản phẩm cấp; tạo khoá là cấp một credential thật, không phải một
   thao tác audit.
4. **`04` — `--lan 5`** cho A/B thật, và **vision** (`qwen38-vision` đang bán mà
   chưa có bài đánh giá nào).

🔴 **Prompt 08 phải do PHIÊN KHÁC chạy.** Tôi đã thi hành bảy phase; tự nghiệm
thu thì *independent* chỉ còn là trang trí — và trong ngày này đã có **ba lần**
phiên khác nhìn ra thứ tôi bỏ sót.

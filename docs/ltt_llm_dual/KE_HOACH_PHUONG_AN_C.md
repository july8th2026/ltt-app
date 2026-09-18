# KẾ HOẠCH PHƯƠNG ÁN C — nhận theo ngân sách token (giữ chỗ đầu ra) + trần chuỗi độc lập

> ⚠️ **ĐÃ THỰC THI 17/09 (L-23).** §1–§2 và các ô trống §4 là **ảnh chụp TRƯỚC khi sửa** (tên
> như `SO_SLOT_MAY_B`, `KY_TU_MOI_TOKEN`, `--no-cache-idle-slots`, `-np 3` cho 3.5 ở đó là lịch sử).
> §3 là mô hình hiện hành. Số sau đó: cache RAM **L-25** (24576/model, sàn 24), số slot **L-28**
> (3.5 `-np 4`, 3.8 `-np 3`), ước token **L-27** (đóng R-2 ở §6). Số theo model chỉ ở
> `apps/ltt_llm/ngan_sach.HO_SO`; đường đi: `BAN_DO_DUONG_DI.md`.

> Soạn 17/09/2026 trên `phien/llm-hang-cho-lon` (đỉnh `d635b695`), **chỉ đọc** — không
> đổi mã, không gate, không deploy. Mục tiêu: khi số đo `KET_QUA_DO_17_09.md` (nhánh
> `phien/bench-may-b`) về, áp **một lượt** theo §4–§5.
>
> Mốc so sánh:
> - production `https://app.lttstudios.com/health/version` → `commit 2d9b95a22743`
>   (build 17/09 12:44) — tổ tiên của `main`; `main` hơn nó 8 commit, **không** commit
>   nào chạm `platform_core/`, `apps/ltt_llm/`, `llm_gateway/`, `server/`.
> - `git diff main...HEAD`: L-12b (`b8cfe212`) chỉ đổi máy A
>   (`platform_core/llm/{admission,luat_nhan,phong_cho,residency,tham_so_da_luot}.py`,
>   `registry.py`, `runtime_noi_bo/luong.py`); `d635b695` đổi
>   `render_gateway/deploy/cai_dat_dich_vu.ps1` (máy B). **`llm_gateway/` không đổi.**
>   L-12b **chưa gate, chưa gộp, chưa deploy** (handoff `docs/NHAT_KY.md` 17/09).
> - `C:\LTTPlatform\secrets\app.env` production: **không** đặt biến `LTT_LLM_*` /
>   `LTT_ADMISSION_*` nào ngoài `LTT_LLM_BASE_URL` ⇒ mọi núm đang chạy ở **mặc định mã**.
> - Máy B `/running` 17/09 có `--no-cache-idle-slots`; `llm_gateway/deploy/llama-swap.yaml`
>   **không có** (ghi ở `bench_hang_cho/RUNBOOK_CUA_SO_DO.md`) ⇒ kho đang lệch máy thật.

---

## 0. Tóm tắt một trang

**Hôm nay có HAI bộ nhận chồng nhau**, cùng hỏi *"lượt này có vừa không"*:

| tầng | ở đâu | luật |
|---|---|---|
| máy A (chính sách) | `luat_nhan.xet` qua `admission.xet_va_giu` | slot ≤ 3 · Σ đặt chỗ ≤ pool=`-c` · ≤1 whale (cờ **tắt khi byte đầu về**) · nền nhường · trần tài khoản · backfill 120 s |
| máy B (cổng) | `llm_gateway/gioi_han.py:_xin_vao` | slot ≤ 3 · Σ đặt chỗ ≤ pool=catalog `max_context` · ≤1 whale (cờ giữ **tới hết lượt**) · RPM 120 · trần vào 186.368 cho **cả hai** model |

Chúng lệch nhau ở ít nhất 4 chỗ đo được bằng đọc mã (§2, O-01…O-04) và mỗi chỗ lệch biến
thành **429 sau 200** (khách đã chờ trong phòng chờ rồi nhận khối SSE `overloaded`)
hoặc **413 sau 200**.

**Mô hình C chuẩn hoá (§3):** máy A là **người quyết định duy nhất**; máy B chỉ giữ
**rào vật lý** (`seq ≤ -np`, `Σ đặt chỗ ≤ -c`, trần vào theo **từng** model) đọc thẳng
từ `llama-swap.yaml`, không có luật công bằng/nhịp riêng. Mọi số gõ tay còn lại nằm ở
`apps/ltt_llm/ngan_sach.py` (bảng `HO_SO` theo model) + `llama-swap.yaml`, một phép
kiểm parse YAML buộc hai bên khớp.

**Phát hiện quan trọng nhất cho chủ dự án (§4.3):** với giữ chỗ đầu ra mặc định
`max_tokens` = 32.768, **ví dụ chủ dự án không xảy ra**: 15K+100K đang chạy đặt chỗ
184.632 / 221.184; lượt 55K cần 89.816 ⇒ **không backfill được**. Ví dụ chỉ đúng nếu
giữ chỗ đầu ra ≤ ~14.300 token (3.8) hoặc ≤ ~25.000 (3.5). Phải chốt chính sách
`max_tokens` cho LTTCODE bằng số đo phép 4 (p99 đầu ra 13.502 / 11.605).

---

## 1. Bản đồ tham số — MỘT bảng

Ký hiệu cột "loại": **G** = gõ tay (nguồn) · **D** = dẫn xuất · **S** = bản sao gõ tay
(có test đối chiếu) · **S!** = bản sao **không** ai đối chiếu · **E** = env đọc lúc chạy.

### 1.1 Engine (máy B, vật lý)

| tham số | giá trị | nghĩa | nơi khai / đọc | test chốt | loại |
|---|---|---|---|---|---|
| `-c` 3.8 | 221.184 | cửa sổ; với `-kvu` = **bể KV chung** mọi slot | `llm_gateway/deploy/llama-swap.yaml:314`; A `apps/ltt_llm/ngan_sach.py:72` (`CUA_SO_THEO_MODEL`); B `llm_gateway/catalog.py:130` (`max_context`); A `platform_core/providers.py:287`; A `platform_core/public_api/examples.py:703` (chuỗi "221,184") | `tests/test_334_ngan_sach_ltt_llm.py:396-429,631`; `test_1214` | G (yaml) + S×4 |
| `-c` 3.5 | 262.144 | như trên | yaml `:401`; `ngan_sach.py:73`; `catalog.py:142`; `providers.py:321` | `test_334:396-420` | G + S×3 |
| `-np` (cả hai) | 3 | số chuỗi engine | yaml `:315,:402`; `ngan_sach.py:443` `SO_SLOT_MAY_B` (+ bí danh `DONG_THOI_MAY_B:447`, `SO_SLOT:463`); B `llm_gateway/config.py:214` `LTT_LLM_MAX_DONG_THOI` mặc định 3 | `tests/test_1201_mot_nguon_so_slot.py:54-102`; `tests/test_1215_llama_swap_hai_model.py:296-316`; `test_334:250-257,280` | G + S×2 + 2 bí danh |
| `-kvu` | bật | một bể `-c` cho mọi slot; một chuỗi dùng tới cả `-c` (`llama-context.cpp`: `if (cparams.kv_unified) n_ctx_seq = n_ctx`) | yaml `:231-236` macro `CHUNG` | `test_1215:320-335` | G |
| KV type | 3.8 `q4_0` · 3.5 `q8_0` | VRAM/token | yaml `:316,:403` | — | G |
| `-b` / `-ub` | **mặc định engine** (2048/512) | lô prefill; ảnh hưởng độ khựng decode của người khác | không khai; `ngan_sach._nguong_whale:591` giả định bước 512 = `-ub` | — | ngầm định |
| `--reasoning-budget` | 3.8 **4096** · 3.5 **2048** | trần token suy nghĩ, **nằm trong** `n_predict` (`server-context.cpp has_budget()` đếm `n_gen` — `SO_LOI_DO_TAI.md` §L-12b) | yaml `:312,:399` | `test_1215:64-70` (`CO_RIENG_Q131`) | G |
| `concurrencyLimit` | 8 | llama-swap chuyển vào tối đa 8 | yaml `:336,:410` | `test_1215:313` (≥ 2×np) | G — không bao giờ chạm (cổng B chặn ở 3) |
| `ttl` / `unloadTimeout` / `healthCheckTimeout` | 1800 / 30 / 600 | nhả model khi rảnh | yaml `:335,:337,:125` | `test_1215:221-293`; `tests/test_637_nha_ve_ram.py:142-207` | G (ngoài phạm vi C) |
| `--cache-ram` | ~~**mặc định 8192 MiB, chưa đo**~~ ĐÃ THAY: **24576 MiB/model** (L-25) | cache prompt trên RAM | cố ý không khai, yaml `:551-560` | — | chờ m6 |
| `--no-cache-idle-slots` | ~~**có trên máy thật, không có trong kho**~~ ĐÃ GỠ: phép đo tạm, đã hoàn nguyên (O-19 đóng 17/09) | không giữ cache slot rảnh trong bể `-kvu` | chỉ ở `/running` máy B | — | ⛔ lệch kho |
| `--reserve-vram` (ComfyUI) | 3 GB | chừa VRAM 3090 | `render_gateway/deploy/cai_dat_dich_vu.ps1:101`; `render_gateway/ngan_sach.py:61` `VRAM_CHUA_LAI_GB` | `tests/test_245_render_gateway.py:1458` | G + S |
| ComfyUI khởi động | `SERVICE_DEMAND_START` | theo nhu cầu (d635b695) | `render_gateway/deploy/cai_dat_dich_vu.ps1:138` | **không có** | G |
| biên VRAM 3.8 ở `-c 221184 -np 3` | 445 MiB | giả định cư trú 3090 | `platform_core/llm/residency.py:51,674` (chú thích); `ngan_sach.py:51-56` | — | ghi chú — **đổi `-np/-c` 3.8 là đổi giả định này** |

### 1.2 Trần mỗi lượt (máy A dẫn xuất từ engine)

| tham số | giá trị | công thức / nghĩa | nơi | test | loại |
|---|---|---|---|---|---|
| `TOKEN_RA_TRAN` | 32.768 | trần token ra cứng | `ngan_sach.py:104`; B `config.py:201` `LTT_LLM_MAX_OUTPUT_TOKENS`; B `deploy.ps1:299-311` ghi đè; `server/api/tools.py:33` `TOKEN_RA_TOI_DA`; `public_api/examples.py:672`; `tools/cam_cli.py:134` | `test_334:247,310,357,752` | G + S×5 |
| `LE` | 2.048 | biên ước token vào | `ngan_sach.py:108` | `test_334:30-39` | G |
| `tran_vao_cua(m)` | 3.8 **186.368** · 3.5 **227.328** | `-c − TOKEN_RA_TRAN − LE` → 413 trước 200 | `ngan_sach.py:164-173`; đọc `apps/ltt_llm/executor.py:95` → `luong.tien_kiem:328-333`; `server/api/streaming.py:687` | `test_334`, `test_604` | D |
| B trần vào | **186.368 cho CẢ HAI model** | `min(cfg.max_input_tokens, spec.max_context)` | `llm_gateway/api.py:842`; `config.py:200`; `deploy.ps1` ép 186368 | `tests/test_250_llm_gateway.py:41-47` | S — ⛔ **sai cho 3.5** (O-03) |
| `CONG_BO_CHO_CLIENT` / `cong_bo_cua(m)` | 171.458 · 209.141 | `tran_vao × 0,92` (lệch tokenizer client) | `ngan_sach.py:143,176-178`; `examples.py:671`; `cam_cli.py:132` | `test_334:87,578-623,1013` | D + S×2 |
| `NEN_CHO_CLIENT` / `nen_cua(m)` | 138.690 · 176.373 | `cong_bo − TOKEN_RA_TRAN` | `ngan_sach.py:200-224`; `examples.py:676`; `cam_cli.py:144`; `server/api/tools.py:98-100` tính lại `cua_so − ra` | `test_334:920-1060` | D + S×2 |
| `CUA_SO_CONG_BO_MAC_DINH` | 60.000 | lùi khi model không khai | `server/api/tools.py:30` (chú thích nói `-c 131072`, 65.000) | `test_334:623` | S! — tàn dư 29/08 |
| `canh_bao` 3.8 | "engine có cửa sổ 131K; input 96.256" | chuỗi hiển thị | `platform_core/providers.py` (khối `qwen38-api`, `9359d723` 01/09) | — | S! — **sai** |
| `BODY_BYTES_TOI_THIEU` | ~1.022.976 | `(max -c − ra − LE) × 4,5` | `ngan_sach.py:136-138`; `public_api/config.py:77` | `test_334:95,272` | D + S |
| `KY_TU_MOI_TOKEN` | 2,5 | ước token vào (ước CAO) | `ngan_sach.py:411`; B `llm_gateway/ngan_sach.py:102` | `test_334:304` | G + S |
| `TOKEN_MOI_ANH` (đo) | 770 | ảnh 1024×768 | `ngan_sach.py:526` | `tests/test_1214_so_theo_model.py:261` | G (chỉ tài liệu) |
| `token_moi_anh` (giữ chỗ) | **2.048** | đặt chỗ mỗi ảnh | A `platform_core/llm/tham_so_da_luot.py:106` env `LTT_LLM_TOKEN_MOI_ANH`; B `llm_gateway/ngan_sach.py:109` | `test_1214:267-275` (A ≥ 770); `tests/test_1208_cua_dong_bo_cho.py:895` | E + S — hai số cho "một ảnh" |
| `SO_ANH_TOI_DA` / byte | 4 / 12 MiB | B cưỡng chế, A công bố | `ngan_sach.py:544-545`; B `config.py:202-203` | `test_1259` | S |
| `TOKEN_RA_MAC_DINH` | sync 1.024 · stream 32.768 · job 32.768 | `max_tokens` khi khách không khai | `ngan_sach.py:245-291` | `test_334:105-125` | G |
| `SAN_TOKEN_RA_THEO_NGHI` | 3.5 {64,512,1024,1024} · 3.8 64 | sàn `max_tokens` theo mức nghĩ | `ngan_sach.py:349-386` | test_256 | G |
| `tran_theo_ngu_canh` | `min(32.768, -c − vào − LE)` | kẹp ra theo chỗ còn | `ngan_sach.py:480-501`; `executor.context_output_cap`; `luong.tran_token_ra:143-155` | `test_334:71` | D |

### 1.3 Nhận / hàng chờ (máy A)

| tham số | giá trị | nơi khai | ai đọc | test | loại |
|---|---|---|---|---|---|
| **đặt chỗ** `token_dat_truoc` | `vào_ước + xin_ra + dem_dat_truoc + ảnh×token_moi_anh`, kẹp ≤ pool | `tham_so_da_luot.luat_cho:74-92` | stream `luong.tien_kiem:342`; sync `luong.cho_suat_dong_bo:519` (chat.py:382, streaming.py:279); ChatLTT/`chuan_bi:718`; job `platform_core/job_runner.py:382`; planner `platform_core/agent/planner.py:163` | `test_1208:895`; `test_1203` | D (một phép tính, 5 cửa) |
| `dem_dat_truoc` | 2.048 | `tham_so_da_luot.py:103` env `LTT_LLM_DEM_DAT_TRUOC` | `luat_cho` | `test_1208:895` | E — **trùng nghĩa với `LE`** |
| pool (luật 2) | = `-c` | manifest `apps/ltt_llm/manifest.py:269-273` `AdmissionModel(TAI_NGUYEN_38, SO_SLOT, POOL_38, NHOM_CU_TRU_38, "mac_dinh")` | `registry.suc_chua_admission:148-160` → `ap_cau_hinh_admission:185-211` | `test_1201:26-47`; `test_1250:198-224` | D |
| `LTT_ADMISSION_POOL__<resource>` | không đặt | chỉ HẠ pool | `platform_core/registry.py:164-165,207-209` | `test_1250:198` | E (L-12b) |
| slot (luật 1) | = `-np` = 3 | manifest | `luat_nhan.xet:223` | `test_1203` | D |
| `LTT_ADMISSION_SO_SUAT__<resource>` | không đặt | chỉ HẠ slot | `registry.py:163,204-206` | `test_1250:198` | E (L-12b) |
| `nguong_whale` (**đang dùng**) | **16.384** chung | `tham_so_da_luot.py:97` env `LTT_LLM_NGUONG_WHALE` | `luong.tien_kiem:356` (chỉ cửa stream/ChatLTT) | `test_1214:219-226` (≤ min theo model) | E |
| `NGUONG_WHALE` (**không ai dùng**) | 3.8 **33.792** · 3.5 **56.832** | `ngan_sach.py:584-617` dẫn xuất từ `DUONG_PREFILL_TOK_S` + 30 s | chỉ test; chú thích `llm_gateway/api.py:1113-1118`, `gioi_han.py:280-283` **nói sai** là A đang dùng | `test_1214:180-256` | D (chết) |
| `WHALE_CHAN_TOI_DA_S` / `cho_whale_toi_da_s` | 30 s | `ngan_sach.py:560`; `tham_so_da_luot.py:98` env `LTT_LLM_CHO_WHALE_S`; mặc định trùng `luat_nhan.ThamSo:85`, `admission.xet_va_giu:300`, `phong_cho.cho_nhan:270` | luật 5 | `test_1214:210-215` | G + S×4 mặc định |
| `token_prefill_moi` | ước qua băm tiền tố | `platform_core/llm/uoc_moi.py` (LRU trong tiến trình) | chỉ để gắn cờ whale | — | D |
| `so_nguoi_cho_toi_da` | 32 | `tham_so_da_luot.py:101` env `LTT_LLM_SO_NGUOI_CHO` | `phong_cho.kiem_phong:150` (429 trước 200) | `test_1250:169` | E |
| `so_ca_voi_cho_toi_da` | 2 | `tham_so_da_luot.py:102` env `LTT_LLM_SO_CA_VOI_CHO`; mặc định trùng `phong_cho.kiem_phong:122` | 429 `phong_day_ca_voi` | `test_1250:156-166`; `test_1205:163-167` | E (L-12b) |
| `cho_backfill_toi_da_s` | 120 s | `tham_so_da_luot.py:110` env `LTT_LLM_CHO_BACKFILL_S`; mặc định trùng `luat_nhan.ThamSo:102` | luật 6a/6b; `admission.xet_va_giu:353-357` | `test_1203:153-205,373` | E + S mặc định |
| `lao_hoa_s` | 300 s | `tham_so_da_luot.py:108`; mặc định trùng `luat_nhan.ThamSo:86` | `sap_xep_cho:173` — ⚠️ `admission.xet_va_giu:358` **không truyền** ⇒ env không có hiệu lực | `test_1203` | E **chết** (O-09) |
| `chua_slot_tuong_tac` | 0 | `luat_nhan.ThamSo:89` | luật 3 (vế đầu không bao giờ chạy khi 0) | `test_1204` | G (không env) |
| `tran_tai_khoan` | ceil(N/2) = 2 | `luat_nhan.py:123-124` | luật 4 | `test_1203` | D |
| chờ stream thường / whale | 300 / 900 s | `tham_so_da_luot.py:99,109` env `LTT_LLM_CHO_STREAM_S`, `_WHALE_S` | `luong.luong_co_cho:583`, `mo_luong:1340`, `residency._nguoi_cho_llm:1223` | `test_1250:186` | E |
| chờ đồng bộ | 60 s, kẹp ngân sách cửa | `tham_so_da_luot.py:100`; `luong.han_cho_dong_bo:460-473` | chat.py, streaming.py sync | `test_1208` | E |
| nhịp SSE chờ (A) | 15 s | `tham_so_da_luot.py:107` env `LTT_LLM_NHIP_TIM_CHO_S` | `luong_co_cho:584,621` (`: ltt-cho …`) | — | E |
| nhịp SSE prefill (B) | 15 s | `llm_gateway/config.py:216` env `LTT_LLM_NHIP_TIM_S` | `llm_gateway/nhip_tim.py`, `api.py:1025` | — | E (bản song song của A) |
| hỏi lại luật | 0,5 s | `phong_cho.py:29` `MOI_NHIP_S` | `cho_nhan` | — | G |
| hạn nhịp dòng chờ | 10 s / mồ côi 10 phút / sổ 30 ngày | `phong_cho.py:80,84,87` | `chup_nguoi_cho`, `don_het_han` | test_1205 | G |
| mở luồng tới B (read timeout) | **75 s** | `luong.py:46` `MO_LUONG_GIAY`; `server/api/streaming.py:126` bí danh | `luong_vlm.mo` → `httpx.Client(timeout=75)` | test_272 | G — sống được nhờ nhịp 15 s của B |
| `luong_vlm.mo` mặc định | 900 s | `platform_core/llm/luong_vlm.py:127` | cửa không truyền `timeout_s` | — | G |
| `TRAN_IM_LANG_S` | 900 s | `admission.py:87` (chú thích dẫn `luong_vlm.mo(900)`, nhưng cửa stream dùng 75) | lớp 2 nhả suất | `tests/test_1247_nhip_tim_chung_minh_tien_trien.py:96-114` | G |
| lease nhịp / mồ côi | 60 s · chung 20 ph · stream 180 s · job 300 s | `admission.py:22-23,48,77` | `reclaim_expired` | `test_1250:46-65` | G |
| B thu hồi suất treo | 1.200 s | `llm_gateway/gioi_han.py:47` | cổng B | `tests/test_363_suat_khong_ro.py:180` (> 900) | G |
| B timeout thượng nguồn | 600 (thường) / 900 (stream) | `config.py:204-205` | `api.py:958,1033` | test_363 | E |
| B RPM | 120 / model / 60 s trượt | `config.py:215` | `gioi_han.py:195` → 429 | — | E — **A không có** |
| B whale lock | ≤1 **suốt lượt** | `gioi_han.py:225-233` | cổng B | `test_1221:433` | G |
| B pool | catalog `max_context`, env `LTT_LLM_TOKEN_POOL[__m]` | `config.py:263-281` | `gioi_han.py:200-223` | `test_1221` | S |
| B giữ chỗ | `max(in_B + out, X-LTT-Token-Dat)` | `llm_gateway/api.py:880-887`, `so_theo_model.py:195-208` | cổng B | `test_1221:144` | D (17e14391, 15/09) |
| B trọng tài 3090 | RAM ≥ 48 GB, ≤ 2 python trên 3090 | `config.py:206-207`, `trong_tai.py:67` | `api.py:933-939` → 429 | — | ngoài C |
| giá / giữ tiền | `du_so_du`, `giu_cho_luot` theo `max_tokens` | `platform_core/llm/thanh_toan.py`, `gia_token.py` | sau khi được nhận | — | ngoài C (đọc `xin_ra`) |

### 1.4 Client LTTCODE (`D:\LTTCODEAPP`, commit hiện tại)

| tham số | giá trị | nơi | nguồn | test | commit |
|---|---|---|---|---|---|
| cửa sổ lùi (catalog hỏng) | 3.8 171.458 · 3.5 209.141 | `plugins/llm-ltt/src/adapter.ts:143-146` `KNOWN_CONTEXT_WINDOWS` | S! của `cong_bo_cua(m)` | `test/adapter.test.mjs:167-174` | `96ce5dd` 17/09 |
| cửa sổ / `defaultMaxTokens` | từ `/api/v1/models` `context_window`, `max_output_tokens` | `adapter.ts:232-237` | server `server/api/tools.py:_dang_codex` | `adapter.test.mjs:146-152` | `77c181e` 16/09 |
| ⇒ `max_tokens` thật gửi đi | **32.768** (= `max_output_tokens` catalog) | `messages.ts:153` `options.maxTokens ?? FALLBACK_MAX_TOKENS` | catalog | — | — |
| `FALLBACK_MAX_TOKENS` | 4.096 (khi catalog hỏng) | `plugins/llm-ltt/src/messages.ts:26` | gõ tay | `adapter.test.mjs:262-267` | `5426225` 16/09 |
| ngưỡng nén | `thresholdRatio 0.808` × cửa sổ ⇒ 138.538 / 168.985 | `desktop/sidecar/presets/standard/agent.cordis.yml:210-219` | gõ tay, dẫn từ 32.768 | `adapter.test.mjs:176-192`; `tools/check_composition.mjs:263-321` (`WINDOWS`, `OUTPUT_RESERVE=32_768`, `MIN_THRESHOLD=130_000`) | `96ce5dd` |
| im lặng tối đa | 300 s; **dòng chú thích SSE đặt lại đồng hồ** | `adapter.ts:82,301-306`, `sse.ts:32-36` | gõ tay | A10 `:338-366`, A12 `:370-390` | `79bdc00`; `onComment` **`8354bd4` 17/09** |
| thử lại | 5 lần, trễ 1 s → 60 s, jitter 0,1 | `adapter.ts:159-162` | gõ tay | A2 `:116-130` | `77c181e` |
| phân loại lỗi | 429/`overloaded` → RATE_LIMIT (thử lại); 413/"context" → CONTEXT_WINDOW_EXCEEDED (nén) | `errors.ts:34-98` | bản sao mã lỗi server | A1–A3 | `1ec0872` 14/09 |
| catalog TTL / timeout | 10 ph / 10 s | `adapter.ts:149,151` | gõ tay | A11 | `77c181e`, `dd3cc85` |

Hệ quả cho C:
- ✅ Mục "còn mở 1" của `SO_LOI_DO_TAI.md` §L-12b (adapter không đếm chú thích SSE) **đã
  sửa** ở LTTCODE `8354bd4` — cập nhật sổ lỗi ở bước 7.
- `max_tokens` LTTCODE gửi = 32.768 ⇒ `out_giu` = 32.768 ⇒ vấn đề §4.3 là **thật** với
  client của chính ta.
- Chú thích `adapter.ts:222-226` còn dẫn *"57k queue prefill cap"* (đã gỡ ở L-12b) — tàn dư.
- Cửa sổ 171.458/209.141 gõ ở **bốn** nơi phía LTTCODE (`adapter.ts:143`,
  `check_composition.mjs:264`, `tools/do_prefix_luot.mjs:78-79`, chú thích preset); đổi
  `-c` (m2) ⇒ đổi cùng lượt, hoặc bỏ số lùi (catalog là nguồn).
- `0.808` chỉ đúng khi `ratio × W ≤ W − max_out`: đổi `max_out` hoặc cửa sổ phải tính lại.

---

## 2. Chồng chéo / logic cũ phải dẹp

Mỗi mục: **vị trí** · **commit sinh ra** · **vì sao có** · **L-12b đã gỡ?** · **việc làm**.

### A. Hai bộ nhận (A ↔ B) lệch nhau — gây lỗi sau 200

**O-01 — Cờ whale: A tắt khi byte đầu về, B giữ tới hết lượt.**
- A `platform_core/llm/admission.py:470-493` `xoa_co_whale`, gọi `luong.py:1128` — `1a8e3b08` 11/09 *multijob T5*.
- B `llm_gateway/gioi_han.py:225-236` (cờ nằm trong bộ `(t, token, whale)` tới `suat.tra()`) — `fcfd3404` 12/09 *dual 7.1*.
- Hệ quả: whale #1 đang **decode** (A đã tắt cờ) ⇒ A nhận whale #2 sau khi nó chờ tới 900 s ⇒ B 429 *"da co mot luot ca voi"* ⇒ `luong.mo_thuong_nguon:1051-1058` → `DangBan` → SSE `overloaded`. Khách mất cả lượt chờ.
- L-12b: **chưa**.
- Việc: **xoá khoá whale ở B** (A là nơi duy nhất quyết định công bằng prefill). Xoá `la_whale` khỏi `gioi_han._xin_vao`, `so_theo_model.cap_suat`, header `X-LTT-Whale` (`api.py:1190-1214`, `luong_vlm.py:166-167`) và `test_1221:433`.

**O-02 — Trần vào của B dùng 186.368 cho cả 3.5.**
- `llm_gateway/api.py:842` `min(cfg.max_input_tokens, spec.max_context)`. Nguồn: `config.py:200` (`920253ed`) và `deploy.ps1` ép `LTT_LLM_MAX_INPUT_TOKENS=186368`.
- A cho 3.5 tới `tran_vao_cua("qwen35-api")` = **227.328** và công bố 209.141. Lượt 3.5 có 186.369–227.328 token: A nhận, cho chờ, rồi B trả **413 sau 200**.
- L-12b: chưa.
- Việc: B tính trần vào **theo model** = `-c(yaml) − max_out − LE`. Xoá biến `LTT_LLM_MAX_INPUT_TOKENS` khỏi `config.py:200` và `deploy.ps1`. Sửa `test_250:41-47` để so theo model.

**O-03 — B RPM 120 mỗi model, A không có luật tương ứng.**
- `llm_gateway/config.py:215`, `gioi_han.py:195`, có từ `b81b1841` (24/08, thời `--parallel 1`).
- Lượt thứ 121 trong 60 s bị 429 sau 200. Tải LTTCODE (nhiều lượt tool ngắn) chạm được.
- Việc: xoá RPM ở cổng B (hạn mức theo khách đã có ở `public_api/limits.py` của A).

**O-04 — Hai sổ slot/pool nhả lệch nhịp.**
- A nhả lease ở `khi_dut` (~0,05 s). B nhả `suat` khi luồng đóng phía B. A có thể nhận lượt mới trước khi B nhả ⇒ 429 sau 200.
- B pool/slot: `gioi_han.py:186-223` (`fcfd3404`, `920253ed`).
- Việc: **giữ** rào vật lý ở B (slot ≤ `-np`, Σ ≤ `-c`) làm lưới — engine tràn `-kvu` giết mọi slot (b10689; m5 đo lại b10883). Nhưng A phải xử lý **429 của B = xếp hàng lại** thay vì lỗi: `mo_thuong_nguon` khi `e.ban` ⇒ nhả lease, **giữ nguyên dòng chờ** (không `ghi_ket_thuc`), quay lại `cho_nhan` với `tuoi` cũ, tối đa `K` lần/`T` giây. Phép kiểm mới: B giả trả 429 một lần ⇒ khách nhận nội dung, không nhận `overloaded`.

**O-05 — Cửa đồng bộ và job không gửi `X-LTT-Token-Dat`.**
- `platform_core/llm/dieu_phoi.py:159-164` chỉ gửi `X-LTT-Request-Id`, nên B tự ước `in + out` (không có đệm 2.048).
- Việc: gửi `X-LTT-Token-Dat` từ `dieu_phoi` (đã có `token_dat_truoc` ở `SuatDongBo`/lease), để hai sổ đếm **cùng một số** trên mọi cửa.

### B. Hai định nghĩa cho cùng một đại lượng ở máy A

**O-06 — Ngưỡng whale: 16.384 chung (đang chạy) vs `NGUONG_WHALE` theo model (chết).**
- `tham_so_da_luot.py:97` `LTT_LLM_NGUONG_WHALE` 16.384 — `f29a6e7c` 11/09 *multijob T4*. Lý do: spec multijob §12, 7,6 % lượt thật.
- `ngan_sach.py:584-617` `NGUONG_WHALE` 33.792 / 56.832 — `75ea1e81` 12/09 *dual 2.6*. Lý do: 30 s chặn prefill đo trên đường cong §G4.
- Cầu nối được hứa ở `test_1214:216-226` (*"cho tới khi admission theo model đi qua đó"*) chưa bao giờ làm. Chú thích `llm_gateway/api.py:1113-1118` và `gioi_han.py:280-283` nói A đang dùng số theo model: **sai**. `docs/VAN_HANH_THAT.md:104` cũng trỏ ngưỡng whale về `ngan_sach.py`.
- Việc: thêm `nguong_whale` vào `AdmissionModel` (manifest khai từ `ngan_sach.NGUONG_WHALE[m]`). `luong.tien_kiem` đọc `suc.nguong_whale`. **Xoá** `ThamSoDaLuot.nguong_whale` và env. Sửa `test_1214:216-226` thành "đường thật đọc số theo model". Sửa hai chú thích B (hoặc xoá hẳn nếu O-01 gỡ whale ở B).

**O-07 — Whale chỉ được gắn ở cửa stream/ChatLTT.**
- Cửa đồng bộ (`chat.py:382`, `streaming.py:279`) và job (`job_runner.py:382`) không truyền `la_whale`. Một job 150K prefill **không** là whale, nên chạy song song với whale stream.
- Có từ `7f0e6377` 11/09 *dual 1.5*: `luat_cho` có tham số `la_whale` nhưng chỉ stream truyền.
- Việc: gắn cờ whale ở `luat_cho` **một chỗ** (nhận `nguong_whale` + `token_prefill_moi`; job/sync dùng `vào_ước` vì không có lịch sử tiền tố).

**O-08 — Biên ước ở hai tên: `LE` 2.048 và `dem_dat_truoc` 2.048.**
- `ngan_sach.py:108` (`9fb351bf` 30/08, dùng trong trần vào) và `tham_so_da_luot.py:103` (`f29a6e7c` 11/09, dùng khi đặt chỗ; chú thích "≈ `n_batch`").
- Hai tên trả lời cùng một câu (*"ước lệch bao nhiêu"*). Đổi một cái thì bất biến `vào ≤ tran_vao ⇒ đặt chỗ ≤ -c` gãy **im lặng**: `luat_cho` kẹp về pool nên không đỏ.
- Việc: một hằng `DEM_UOC` trong hồ sơ model, manifest mang vào `AdmissionModel`. Xoá env `LTT_LLM_DEM_DAT_TRUOC`.

**O-09 — `lao_hoa_s` env không có hiệu lực.**
- `admission.xet_va_giu:358-360` dựng `luat_nhan.ThamSo(...)` nhưng **không** truyền `lao_hoa_s` ⇒ luôn là mặc định 300 của `luat_nhan.ThamSo:86`. Env `LTT_LLM_LAO_HOA_S` (`tham_so_da_luot.py:108`) không ai đọc trên đường thật.
- Có từ `1a8e3b08` 11/09.
- Việc: truyền đủ **mọi** tham số từ một `ThamSoDaLuot` vào `luat_nhan.ThamSo`, bỏ mặc định số trong `luat_nhan.ThamSo` (bắt buộc truyền). Phép kiểm: đổi env ⇒ `xet_va_giu` thấy.

**O-10 — Mặc định số trùng ở nhiều chữ ký.**
- `cho_whale_toi_da_s=30.0` ở `admission.py:300`, `phong_cho.py:270`, `luat_nhan.py:85`. `cho_backfill_toi_da_s=120.0` ở `luat_nhan.py:102` và `tham_so_da_luot.py:67`. `so_ca_voi_toi_da=2` ở `phong_cho.py:122`.
- L-12b thêm hai bản trong số này.
- Việc: bỏ mặc định số, chỉ `tham_so_da_luot.doc()` giữ.

**O-11 — Token mỗi ảnh: 770 (đo) / 2.048 (A env) / 2.048 (B hằng).**
- `ngan_sach.py:526` (`75ea1e81`), `tham_so_da_luot.py:106` (`f29a6e7c`), `llm_gateway/ngan_sach.py:109` (`b81b1841`).
- Việc: một hằng giữ chỗ `TOKEN_GIU_MOI_ANH` trong hồ sơ model (2.048 cho tới khi đo ảnh lớn nhất được phép). Giữ `TOKEN_MOI_ANH` 770 chỉ cho hoá đơn. B đọc số từ header A (O-05) thay vì tự đếm.

**O-12 — `DONG_THOI_MAY_B`, `POOL_KV_MAY_B`, `SO_SLOT` là bí danh.**
- `ngan_sach.py:447,454,463` (`75ea1e81`); `apps/auto_scan_video/pipeline.py:178` còn chú thích `DONG_THOI_MAY_B = 1`.
- Việc: gom vào `HO_SO[m].seq_cap`. Xoá bí danh sau khi `grep` hết người đọc (tests 1201/334).

### C. Bản sao gõ tay không ai canh / tàn dư

| # | vị trí | commit | việc |
|---|---|---|---|
| O-13 | `platform_core/providers.py` `canh_bao` 3.8: *"engine có cửa sổ 131K; API public giới hạn input 96.256"* | `9359d723` 01/09 | sửa thành chuỗi dẫn xuất hoặc xoá; thêm vào `test_334:1087` |
| O-14 | `server/api/tools.py:22-30` `CUA_SO_CONG_BO_MAC_DINH = 60_000` + chú thích `-c 131072`/65.000 | `556fb646` 29/08 | lùi về `0` ⇒ không khai `context_window` (model nào cũng tự khai, `test_334:519`) hoặc giữ số và sửa chú thích |
| O-15 | `server/api/tools.py:33` `TOKEN_RA_TOI_DA`, `public_api/examples.py:671-706` (chỉ số **3.8**, "Engine context 221,184" cho trang công khai của cả hai model), `tools/cam_cli.py:132-144` | `a5a2e5b4` 12/09 | giữ (lớp cấm import) nhưng test đã chốt; đổi `-c` ⇒ ba nơi này đổi trong cùng changeset |
| O-16 | `llm_gateway/catalog.py:130,142` `max_context` gõ tay; `catalog.py:48-59` chú thích 204.800/169.984 | `920253ed` | B đọc `-c`/`-np` **từ `llama-swap.yaml`** lúc khởi động (cùng thư mục deploy) — xoá số gõ tay |
| O-17 | `llm_gateway/config.py:113-117`, `gioi_han.py:10-13,41-42` "llama-server `--parallel 1`"; `config.py:62-66` 204.800; `config.py:209-213` "deploy.ps1 ghim =1"; `so_theo_model.py:118-121` (`don_dep`, L-18); `api.py:863` (`bao_dam_sach()` 18 s) | nhiều | sửa/xoá chú thích |
| O-18 | `llama-swap.yaml:545-549` "request thứ 4 … `SO_SLOT_MAY_B` là nguồn" — nay nguồn là hồ sơ theo model | `faf5e864` | sửa chú thích |
| O-19 | `llama-swap.yaml` thiếu `--no-cache-idle-slots` mà máy thật có | ngoài kho | đưa vào kho **hoặc** gỡ trên máy — theo m6 (§4); thêm test đối chiếu `/running` (thủ công, ghi NHAT_KY) |
| O-20 | `admission.py:79-87` chú thích `TRAN_IM_LANG_S` dẫn `luong_vlm.mo(900)` trong khi cửa stream mở với 75 s | `cb863464` 13/09 | sửa chú thích (con số đúng hướng: 900 ≥ mọi read timeout) |
| O-21 | `docs/superpowers/specs/2026-09-11-ltt-llm-multijob-design.md:144,173,177`, `docs/multijob/03_QUEUE_MAP.md:22` còn `TOKEN_PREFILL_CHO_TOI_DA` 57.000 và whale 16.384 | spec 11/09 | bản ghi có ngày ⇒ **giữ**, thêm một dòng "ĐÃ THAY bởi L-22/L-23" ở đầu |
| O-22 | `tham_so_da_luot.py:41` chú thích còn nhắc env `LTT_LLM_TOKEN_PREFILL_CHO` (đã gỡ ở L-12b) | `b8cfe212` | giữ (là ghi chú gỡ) — env không còn người đọc ✔ |
| O-23 | `docs/VAN_HANH_THAT.md:104` "ngưỡng whale → `ngan_sach.py`" | — | đúng **sau** O-06 |
| O-24 | `job_runner._luat_cho_job:381` `context_output_cap(vao)` **không** truyền alias ⇒ kẹp theo cửa sổ hẹp nhất cho cả 3.5; không đếm ảnh | `7f0e6377` | truyền alias + `dem_anh(params)` |

### D. Đã gỡ ở L-12b (chỉ xác nhận, không làm lại)

| luật cũ | commit sinh | gỡ ở |
|---|---|---|
| `token_prefill_cho_toi_da` 57.000 (`LTT_LLM_TOKEN_PREFILL_CHO`) | `f29a6e7c` 11/09 | `b8cfe212` |
| `phong_day_mot_mon_lon` (nới cho MỘT món lớn) | `81f2cad6` 13/09 | `b8cfe212` |
| FCFS chặt (`XEP_SAU` không backfill) | `f29a6e7c` | `b8cfe212` (6a/6b) |
| whale kẹt sau whale chặn mọi người | `f29a6e7c` | `b8cfe212` (`_ket_sau_whale`) |
| trần chờ stream chung 300 s cho whale | `f29a6e7c` | `b8cfe212` (900 s) |

---

## 3. Mô hình C chuẩn hoá

### 3.1 Định nghĩa (theo model `m`)

```
engine_ctx[m]   = -c  của hồ sơ m trong llama-swap.yaml           (VẬT LÝ, gõ tay ở YAML)
np[m]           = -np của hồ sơ m                                  (VẬT LÝ, gõ tay ở YAML)
seq_cap[m]      ≤ np[m]                                            (CHÍNH SÁCH, ngan_sach)
bien_pool[m]    ∈ [0, 0.10]                                        (CHÍNH SÁCH, từ m5 + tỉ lệ ước)
token_budget[m] = floor(engine_ctx[m] × (1 − bien_pool[m]))        (DẪN XUẤT)
max_out         = 32_768                                           (CHÍNH SÁCH, = LTT_LLM_MAX_OUTPUT_TOKENS)
DEM_UOC         = 2_048                                            (thay LE + dem_dat_truoc)
tran_vao[m]     = engine_ctx[m] − max_out − DEM_UOC                (413 trước 200; A và B cùng công thức)
out_giu(l)      = min(max_tokens(l) or mac_dinh_cho(cua), engine_ctx[m] − vao_uoc(l) − DEM_UOC)
dat_cho(l)      = vao_uoc(l) + out_giu(l) + DEM_UOC + so_anh(l) × TOKEN_GIU_MOI_ANH
                  (⛔ KHÔNG cộng reasoning_budget: suy nghĩ nằm TRONG n_predict — xem §6 R-1)
Nhận l  ⇔  residency mở ∧ |đang chạy| < seq_cap ∧ Σ dat_cho(đang chạy) + dat_cho(l) ≤ token_budget
           ∧ luật whale ∧ luật hàng (backfill có chặn, lão hoá, trần tài khoản, nền nhường)
whale(l)        ⇔  token_prefill_moi(l) ≥ nguong_whale[m]           (theo model, dẫn xuất §G4 + 30 s)
max_whale_chay  = 1 mỗi model (chỉ ở A)
lao_hoa_T       = 300 s  · backfill_T = 120 s · whale_nhuong_T = 30 s
tran_hang       = 32 người · 2 whale / tài nguyên
cho_toi_da      = stream 300 s · whale 900 s · đồng bộ min(60 s, ngân sách cửa)
nhip            = A `: ltt-cho` 15 s khi chờ · B `nhip_tim` 15 s khi prefill
```

Bất biến phải có phép kiểm:
1. `dat_cho(l) ≤ engine_ctx[m]` với mọi `l` qua `tran_vao` (không cần kẹp im lặng — kẹp
   trong `luat_cho:91` đổi thành `assert`/ném, vì kẹp là che lỗi O-08).
2. `Σ dat_cho(đang chạy) ≤ token_budget ≤ engine_ctx` — mô phỏng ngẫu nhiên đã có
   (`test_1203:287-373`), thêm `bien_pool`.
3. `reasoning_budget[m] (yaml) < sàn max_tokens hợp lệ` hoặc ghi rõ: lượt `max_tokens`
   nhỏ hơn budget bị cắt ở `max_tokens` — không tràn KV (vì cùng `n_predict`).
4. A ⊆ B: mọi lượt A nhận, rào vật lý B cũng nhận (cùng `engine_ctx`, `np`, công thức
   `tran_vao`, cùng số `dat_cho` qua header) — phép kiểm hợp đồng hai phía (§3.3).

### 3.2 Mỗi giá trị sống ở đâu — một nơi

| giá trị | nơi DUY NHẤT gõ | ai đọc (không gõ lại) |
|---|---|---|
| `engine_ctx`, `np`, `--reasoning-budget`, `-b/-ub`, `--cache-ram`, `--no-cache-idle-slots` | `llm_gateway/deploy/llama-swap.yaml` | B: cổng parse YAML lúc khởi động (thay `catalog.max_context`, `LTT_LLM_MAX_DONG_THOI`, `LTT_LLM_TOKEN_POOL`). A: **bản sao** `ngan_sach.HO_SO[m].engine_ctx/np` + `test_334`/`test_1201` parse YAML (đã có) |
| `seq_cap`, `bien_pool`, `max_out`, `DEM_UOC`, `TOKEN_GIU_MOI_ANH`, `nguong_whale` (qua đường cong + 30 s), `mac_dinh_cho(cua)`, sàn theo mức nghĩ | `apps/ltt_llm/ngan_sach.py` — **một** `dict HO_SO[model_id]` (dataclass đóng băng) | manifest → `AdmissionModel(resource, slots=seq_cap, token_pool=token_budget, residency_group, vai_tro, nguong_whale, dem_uoc, token_giu_moi_anh)`; `platform_core` chỉ đọc `AdmissionModel` |
| trần hạ khẩn cấp không deploy | env `LTT_ADMISSION_SO_SUAT__<res>`, `LTT_ADMISSION_POOL__<res>` (chỉ HẠ) | `registry.ap_cau_hinh_admission` |
| thời gian (chờ, backfill, lão hoá, whale nhường, nhịp, trần hàng) | env qua `platform_core/llm/tham_so_da_luot.doc()` — mặc định **chỉ ở đó** | `admission.xet_va_giu` truyền **đủ** vào `luat_nhan.ThamSo` (không mặc định số) |
| trần vào/ra cho B | **không có env**: B tự dẫn xuất `engine_ctx(yaml) − max_out − DEM_UOC`; `max_out`/`DEM_UOC` ghi trong `gateway.env` bởi `deploy.ps1` **từ** `ngan_sach` (script đọc Python) — hoặc gửi theo header | `test_334:363` đổi thành "deploy.ps1 không chứa số gõ tay" |

Loại bỏ hẳn: `LTT_LLM_NGUONG_WHALE`, `LTT_LLM_DEM_DAT_TRUOC`, `LTT_LLM_TOKEN_MOI_ANH`,
`LTT_LLM_MAX_INPUT_TOKENS`, `LTT_LLM_MAX_DONG_THOI[__m]`, `LTT_LLM_RPM`,
`LTT_LLM_TOKEN_POOL[__m]`, header `X-LTT-Whale`, `DONG_THOI_MAY_B`, `POOL_KV_MAY_B`,
`SO_SLOT` (bí danh), `CUA_SO_CONG_BO_MAC_DINH` (hoặc về 0).

### 3.3 Phép kiểm nhất quán A/B (mới)

`tests/test_12xx_phuong_an_c_hop_dong.py` (dải số theo `check_so_test`):
1. parse `llama-swap.yaml` ⇒ với mỗi model: `-c == HO_SO[m].engine_ctx`, `-np == HO_SO[m].np`,
   `HO_SO[m].seq_cap ≤ -np`, `--reasoning-budget < max_out`, cờ `-kvu` có mặt.
2. `llm_gateway` dựng cấu hình từ cùng YAML ⇒ `so_theo_model` pool/slot == `-c`/`-np`
   (không phải `token_budget` — B là rào vật lý).
3. Hàm `dat_cho` của A và hàm giữ chỗ của B cho **cùng số** trên một bộ thân mẫu
   (text, tool, ảnh, `/responses`) khi header có mặt; khi header vắng, B ≥ A − `DEM_UOC`.
4. `tran_vao[m]` của A == trần vào B dựng từ YAML, cho **cả hai** model (bắt O-02).
5. B **không** có luật whale/RPM (grep AST `gioi_han.py` không còn `la_whale`, `rpm`).
6. `AdmissionModel.nguong_whale == ngan_sach.NGUONG_WHALE[id]` và `luong.tien_kiem`
   đọc từ `AdmissionModel` (thay `test_1214:216-226`).

---

## 4. Chỗ chờ số đo (điền từ `KET_QUA_DO_17_09.md`)

### 4.1 Phép đo → tham số → luật quyết định

| phép (`do_b.py`) | đo gì | điền vào | luật quyết định | cần chủ dự án? |
|---|---|---|---|---|
| **m5** (3.5 `-c 16384 -np 3`, tràn cố ý) | b10883 tràn `-kvu` giết mọi slot hay chỉ lượt vượt; server sống sau? | `bien_pool[m]`; giữ/bỏ rào pool ở B | giết **mọi slot** hoặc server chết ⇒ rào B **giữ**, `bien_pool ≥ sai số ước p99` (bước dưới). Chỉ lượt vượt hỏng sạch ⇒ `bien_pool = 0`, rào B vẫn giữ (rẻ) | không |
| `ti_le_ky_tu` (trong mọi phép, `do_b.py:289`) | ký tự / token thật của prompt đo | `KY_TU_MOI_TOKEN` (A `ngan_sach.py:411` + B `llm_gateway/ngan_sach.py:102`) và `bien_pool` | nếu tỉ lệ thật **≥ 2,5** trên mọi loại nội dung ⇒ ước 2,5 là ước CAO ⇒ `bien_pool = 0`. Nếu có loại < 2,5 (tiếng Việt, JSON, mã) ⇒ `bien_pool = max(0, 2,5/tỉ_lệ_min − 1)` làm tròn lên 1 % | không |
| **m1** (3.5 `-np 3/4/6`) | VRAM dedicated+shared, tok/s từng luồng & tổng 1..6 luồng, trả rỗng, cặp slot {0,2} (#25840) | `np[qwen35-api]`, `seq_cap` | chọn `np` lớn nhất mà: shared không vượt nền (674 MiB) + 64; decode từng luồng ở k=np ≥ **40 tok/s** (mốc chủ dự án cần xác nhận); 0 trả rỗng. Nếu 4 hoặc 6 đạt ⇒ đề xuất nâng | ✅ **có** (đổi `-np` máy B) |
| **m2** (3.8 `-np 4/5`, `-c` hạ 16.384/slot thêm) | tràn VRAM, cổng decode đơn ≥ 60 tok/s, tok/s dưới tải | `np[qwen38-api]`, `engine_ctx[qwen38-api]` | đổi chỉ khi: không tràn (`shared ≤ gốc+64`, biên ≥ 300 MiB) **và** cổng 60 **và** tổng tok/s ở k=np > k=3 ít nhất 15 % **và** `tran_vao` mới ≥ 150K + 32.768 (phiên LTTCODE ~150K phải còn chạy — `-c` 204.800 ⇒ tran_vao 169.984 ✔; 188.416 ⇒ 153.600 ✔ sát) **và** biên VRAM với ComfyUI (residency, `residency.py:51`) còn đúng | ✅ **có** |
| **m3_35 / m3_38** (`-b 2048` vs `512`, prefill 32K/163K/128K) | tốc độ decode người khác trong lúc 1 lượt prefill | `-b/-ub` yaml; `nguong_whale` (đổi định nghĩa "chặn") | nếu `-b 512` giữ decode người khác ≥ 50 % tốc độ nền mà prefill chậm ≤ 15 % ⇒ khai `-b 512 -ub 512` ở yaml, **cập nhật** `DUONG_PREFILL_TOK_S` theo số mới; nếu decode người khác gần như không khựng ở cả hai ⇒ đề xuất **nới** whale (30 s → 60 s) | có (đổi yaml engine) |
| **hai_job** (a 1K / b 32K chen vào job đang decode) | khoảng lặng tối đa của job 1, TTFT job 2 | `whale_nhuong_T` (30 s), `nhip` 15 s đủ không | khoảng lặng job 1 trong prefill 32K > 15 s ⇒ nhịp B phải chèn trong **lượt đang decode** (hôm nay chỉ chèn khi im) — kiểm `nhip_tim.py` bao khoảng lặng giữa hai khối; > 100 s ⇒ Cloudflare cắt ⇒ bắt buộc `-b` nhỏ hơn | không (trừ khi đổi `-b`) |
| ~~**m6**~~ (ĐÃ THAY bởi L-24/L-25: `--cache-ram` 24576, O-19 đóng) (`--cache-ram` 8192 vs 0, tải 6 hội thoại tranh 3 slot) | tỉ lệ trúng cache `prompt_tokens_cached_total` | `--cache-ram`, `--no-cache-idle-slots` vào yaml; `uoc_moi` có ý nghĩa không | trúng cache với 8192 cao hơn 0 ≥ 10 điểm % ⇒ khai `--cache-ram 8192` tường minh; đồng thời đưa `--no-cache-idle-slots` (đang chạy thật) vào yaml nếu m6 dùng nó làm nền (O-19) | không |
| **am35 / am38** (ấm, lặp 3, 10 phút tải rồi đo lại) | prefill/decode ổn định, k=1..3, 1K/8K/32K | `DUONG_PREFILL_TOK_S` (`ngan_sach.py:515-520`) ⇒ `NGUONG_WHALE` tự dịch; `NAP_KHO_AM_S` | lệch > 10 % so với bảng §G4 ở bất kỳ điểm nào ⇒ thay điểm bằng số ấm (trung vị 3 lặp, **sau 10 phút tải**) | không |
| **ctrl35 / ctrl38** (song song hai card) | nhiễu chéo CPU/PCIe | chỉ xác nhận hai tài nguyên độc lập | tok/s song song ≥ 90 % cô lập ⇒ giữ hai tài nguyên độc lập; < 90 % ⇒ ghi rủi ro, **không** gộp hàng | không |
| **phép 4** (`do4_log_20260917.json`, đã có) | token ra p50/p95/p99/max: 3.5 1137/6815/13502/32768 · 3.8 1488/6000/11605/19267; `length` 2,8–2,9 % | `out_giu` mặc định cho **agent client** | xem §4.3 | ✅ **có** (hợp đồng API) |

### 4.2 Ô trống (điền đúng một lần)

| ô | hiện | số đo | giá trị mới | tệp:dòng sẽ đổi |
|---|---|---|---|---|
| `bien_pool[qwen38-api]` | 0 (ngầm) | m5 + ti_le_ky_tu | `____` | `ngan_sach.HO_SO` |
| `bien_pool[qwen35-api]` | 0 | m5 + ti_le_ky_tu | `____` | như trên |
| `KY_TU_MOI_TOKEN` | 2,5 | ti_le_ky_tu min | `____` | `apps/ltt_llm/ngan_sach.py:411`, `llm_gateway/ngan_sach.py:102` |
| `np` / `seq_cap` 3.5 | 3 / 3 | m1 | `__ / __` | yaml `:402` + `HO_SO` |
| `np` / `engine_ctx` / `seq_cap` 3.8 | 3 / 221.184 / 3 | m2 | `__ / ______ / __` | yaml `:314-315` + `HO_SO` + `providers.py:287` + `examples.py:671-706` + `cam_cli.py:132-144` |
| `-b` / `-ub` | mặc định | m3 | `____` | yaml `CHUNG` hoặc từng hồ sơ |
| `DUONG_PREFILL_TOK_S` | §G4 | am35/am38 | `____` | `ngan_sach.py:515-520` |
| `NGUONG_WHALE` | 33.792 / 56.832 | dẫn xuất | (tự) | — |
| `whale_nhuong_T` | 30 s | hai_job, m3 | `____` | `tham_so_da_luot.py:98` (+ `ngan_sach.WHALE_CHAN_TOI_DA_S:560` — gộp thành một) |
| `--cache-ram` / `--no-cache-idle-slots` | ngầm / chỉ máy thật | m6 | ĐÃ THAY: `24576` (L-25) / gỡ (O-19) | yaml |
| `out_giu` mặc định agent | 32.768 | phép 4 | `____` (§4.3) | `ngan_sach.TOKEN_RA_MAC_DINH` hoặc bộ cài LTTCODE |

### 4.3 Quyết định cần chủ dự án — giữ chỗ đầu ra (ví dụ 15K+100K / 110K / 55K)

Pool 3.8 = 221.184, `DEM_UOC` 2.048, `bien_pool` 0:

| `out_giu` mỗi lượt | 15K + 100K đang giữ | 110K cần | 55K cần | 55K backfill? |
|---|---|---|---|---|
| 32.768 (hôm nay, mặc định cửa stream) | 184.632 | 144.816 | 89.816 | ❌ (274.448 > 221.184) |
| 16.384 | 151.864 | 128.432 | 73.432 | ❌ (225.296, thiếu 4.112) |
| 12.288 | 143.672 | 124.336 | 69.336 | ✅ (213.008) |
| 3.5 (pool 262.144) ở 16.384 | 151.864 | 128.432 | 73.432 | ✅ (225.296) |

Ba lựa chọn (không có lựa chọn "giữ chỗ ít rồi hy vọng" — tràn `-kvu` là mất mọi slot):
1. **LTTCODE gửi `max_tokens` thật** (vd 16.384 hoặc 12.288) — p99 đầu ra đo được
   13.502 (3.5) / 11.605 (3.8), tức ~1 % lượt bị cắt `length`. Không đổi hợp đồng API.
2. **Máy A hạ `mac_dinh_cho("stream")`** cho lượt không khai `max_tokens` — đổi hợp
   đồng công khai (`/api/v1/tools` default, `tests/golden/`, CHANGELOG), đi ngược
   quyết định 14/09 (`ngan_sach.py:247-290`).
3. **Giữ 32.768**, chấp nhận backfill chỉ cho lượt nhỏ (≤ ~1.700 token prompt khi
   15K+100K đang chạy trên 3.8) — tức ví dụ chủ dự án **không** đạt trên 3.8.

Khuyến nghị: (1). LTTCODE là client ta sở hữu; khách API khác không đổi. Hôm nay LTTCODE
lấy `max_tokens` = `max_output_tokens` của catalog (32.768, `adapter.ts:235-237` →
`messages.ts:153`), nên (1) là một đổi **phía LTTCODE** (bước 5b), không phải phía server.

---

## 5. Kế hoạch triển khai từng bước

Nguyên tắc thứ tự A/B (thay R21 `RUNBOOK.md:62-70` bằng dạng tổng quát):
**GIẢM sức chứa ⇒ máy A trước** (env `LTT_ADMISSION_*` hạ được **không deploy mã**),
**TĂNG sức chứa ⇒ máy B trước**. Rào vật lý B (giữ nguyên ở mọi bước) bảo đảm engine
không tràn cả khi đi sai thứ tự; O-04 (A xếp hàng lại khi B 429) bảo đảm khách không
thấy lỗi trong khe chuyển tiếp.

| bước | việc | ai / máy | test thêm · sửa · xoá | gate | deploy · tương thích | lùi | ước |
|---|---|---|---|---|---|---|---|
| **0** | Khép L-12b như handoff: `gate.py --pham-vi core:provider`, `--pham-vi core:nen`; gộp `main`; deploy web A. (Hoặc gộp vào bước 2 nếu bước 2 xong cùng phiên.) | A | có sẵn (test_1203/1205/1250) | L2 `core:provider` + L2 `core:nen` | A một mình; B không đổi ⇒ an toàn (A chặt hơn B không đổi) | `app.previous\` | 1 h (gate) |
| **1** | **A chịu 429 của B** (O-04): `mo_thuong_nguon` `e.ban` ⇒ nhả lease, dòng chờ quay lại `cho` với `created_at` cũ, tối đa 3 lần / trong `han_cho_stream`; cửa đồng bộ/job tương tự. **Gửi `X-LTT-Token-Dat` ở `dieu_phoi`** (O-05). | A (`platform_core/runtime_noi_bo/luong.py`, `platform_core/llm/phong_cho.py`, `dieu_phoi.py`) | mới: B giả 429 một lần ⇒ nhận nội dung; B 429 mãi ⇒ `overloaded` sau hạn, 0 khoản giữ; header có mặt ở sync/job. Sửa `test_600`, `test_272` nếu chốt "429 ⇒ lỗi ngay" | L2 `core:provider` | A trước. Với B cũ: chỉ thêm thử lại ⇒ an toàn | revert commit | 3 h |
| **2** | **Một hồ sơ theo model ở A**: `ngan_sach.HO_SO` (engine_ctx, np, seq_cap, bien_pool, dem_uoc, token_giu_moi_anh, nguong_whale dẫn xuất); `AdmissionModel` thêm `nguong_whale`, `dem_uoc`, `token_giu_moi_anh` (`platform_core/registry.py` dataclass); manifest đọc `HO_SO`; `luat_cho` nhận chúng từ `AdmissionModel`; gắn whale ở `luat_cho` cho **mọi** cửa (O-06, O-07, O-08, O-11); `xet_va_giu` truyền đủ `ThamSo` (O-09, O-10); job truyền alias + ảnh (O-24); gỡ env `LTT_LLM_NGUONG_WHALE/DEM_DAT_TRUOC/TOKEN_MOI_ANH`; gỡ bí danh O-12; sửa O-13, O-14, O-20 | A (`apps/ltt_llm/`, `platform_core/llm/`, `platform_core/registry.py`, `platform_core/job_runner.py`, `platform_core/agent/planner.py`, `server/api/tools.py`, `platform_core/providers.py`) | mới: `test_12xx_phuong_an_c_hop_dong` mục 1,4,6 (§3.3); ví dụ chủ dự án chạy **qua `luat_cho` thật** với `out_giu` từ §4.3 (không phải `tok=` tự dựng như `test_1203:167`). Sửa `test_1214:216-226,261-275`, `test_1208:895`, `test_1201:21-47`, `test_334` (bí danh). Xoá phép kiểm env đã gỡ | L1 `gate.py --doi` (lan `app:ltt_llm`, `core:provider`, `core:nen`, `core:job`, `server:api`) | A trước B. Ngưỡng whale **tăng** (16.384 → 33.792/56.832) ⇒ ít whale hơn ⇒ với B cũ (khoá whale theo header) **ít** 429 hơn ⇒ an toàn. `dat_cho` không đổi số (2.048 = 2.048) | `app.previous\`; env không liên quan | 1 ngày |
| **3** | **Máy B thành rào vật lý**: cổng parse `llama-swap.yaml` lấy `-c`/`-np` từng model (O-16); trần vào theo model (O-02); xoá khoá whale + header (O-01), RPM (O-03), env `LTT_LLM_MAX_INPUT_TOKENS`, `LTT_LLM_MAX_DONG_THOI[__m]`, `LTT_LLM_TOKEN_POOL[__m]`, `LTT_LLM_RPM`; `deploy.ps1` thôi ghi số gõ tay; sửa chú thích O-17, O-18 | B (`llm_gateway/`) — mã sống ở kho A, deploy bằng `llm_gateway\deploy\deploy.ps1` | mới: §3.3 mục 2,3,5. Sửa `test_250:41-47`, `test_1221` (bỏ whale), `test_1201:97-102`, `test_334:241-257,363`. Xoá phần whale/RPM của `test_363` nếu có | L2 `gate:llm` | **Sau bước 1** (A đã chịu 429). B nới (bỏ whale/RPM, trần vào 3.5 lên 227.328) với A bước 0/2 ⇒ A vẫn quyết định ⇒ an toàn. ⛔ Không restart `LTTLlamaSwap` ở bước này (yaml không đổi) — chỉ restart `LTTLlmGateway` | `deploy.ps1` tự chụp bản đang chạy | 5 h |
| **4** | **Áp số đo** (§4.2) trong **một** changeset: yaml (`-np`, `-c`, `-b/-ub`, `--cache-ram`, `--no-cache-idle-slots`) + `HO_SO` + `DUONG_PREFILL_TOK_S` + `KY_TU_MOI_TOKEN` (A và B) + `bien_pool` + bản sao O-15. Mục cần chủ dự án (§4.1 ✅) chờ duyệt, phần còn lại áp luôn | A (mã) + B (yaml) | test hiện có tự đối chiếu (`test_334`, `test_1201`, `test_1215`, `test_1214`, §3.3) | L1 `--doi` | Theo hướng: **tăng** `np`/`-c` ⇒ B (yaml + restart `LTTLlamaSwap`, xác nhận ba chiều `RUNBOOK.md` §2.3) **trước**, rồi A. **Giảm** `-c` 3.8 (m2) ⇒ đặt `LTT_ADMISSION_POOL__ltt_38_3090=<-c mới>` + `setup\nap_lai_env.ps1` **trước**, rồi B, rồi mã A, rồi gỡ env. Đổi `KY_TU_MOI_TOKEN` **tăng** (ước thấp hơn) ⇒ B trước. Đổi `-np` 3.8 ⇒ kiểm lại residency (biên VRAM với ComfyUI) trước khi mở cửa sổ ảnh | yaml cũ trong bản chụp `deploy.ps1`; env | 4 h + cửa sổ bảo trì máy B 30 ph |
| **5** | **LTTCODE**: (a) ✅ đã có — `onComment` đặt lại đồng hồ (`8354bd4`); chỉ cần kiểm lại trên production ở bước 6; (b) gửi `max_tokens` theo §4.3 (đặt `defaultMaxTokens` tường minh cho ltt-3.8/3.5 thay vì lấy `max_output_tokens` của catalog) và tính lại `thresholdRatio` với `OUTPUT_RESERVE` mới; (c) xoá chú thích "57k" `adapter.ts:222-226`; (d) nếu m2 đổi `-c`: đổi bốn bản sao cửa sổ (§1.4) cùng lượt | LTTCODE (`D:\LTTCODEAPP`) | `adapter.test.mjs:176-192` + `check_composition.mjs` theo `OUTPUT_RESERVE` mới; test gửi đúng `max_tokens` | theo kho LTTCODE | Độc lập; (b) phải có **trước** kịch bản 1 bước 6 | bản LTTCODE trước | 2 h |
| **6** | **Nghiệm thu production** (sau khi 1–4 đã deploy) | A + B + LTTCODE | kịch bản thật, tài khoản thử `tools/tai_khoan_thu.py` | — | — | — | 2 h |
| **7** | **Tài liệu** (cùng changeset với bước tương ứng, không để cuối): `BAN_DO_DUONG_DI.md` §3–§6 (thêm "B = rào vật lý", "B 429 ⇒ xếp hàng lại"); `DECISION_LOG.md` **L-23** (phương án C; L-22 đã dùng cho L-12b); `SO_LOI_DO_TAI.md` (O-01…O-04 là lỗi đo/đọc được, đóng khi bước 1/3 xong); `docs/VAN_HANH_THAT.md:104`; `RUNBOOK.md` §2.1 (luật tăng/giảm), §2.3 (restart gateway), §6; dòng "ĐÃ THAY" cho O-21; `docs/NHAT_KY.md` mỗi phiên | A | — | — | — | — | 1,5 h |

Tổng ước: ~3 ngày làm việc, không kể chờ số đo và cửa sổ bảo trì máy B.

### 5.1 Kịch bản nghiệm thu bước 6 (production, `https://app.lttstudios.com`)

Chuẩn bị: prompt tổng hợp đúng độ dài bằng `/tokenize` của B (không ước), `max_tokens`
theo §4.3, `reasoning_effort=low` để lượt ngắn kết thúc nhanh; ghi `llm_waiters` +
`/ops/jobs-metrics` + `gateway_err.log` + `/slots` của B.

1. **Ví dụ chủ dự án** (3.8): A=15K và B=100K chạy; C=110K vào (phải `cho_ngan_sach`);
   D=55K vào 5 s sau (phải được nhận **trước** C nếu `dat_cho` vừa); C nhận khi A hoặc
   B xong. Đọc `llm_waiters.admitted_at` và `ly_do_cho`.
2. **Chặn backfill**: giữ C chờ > 120 s trong khi rải lượt 5K liên tục ⇒ sau 120 s mọi
   lượt 5K mới có `ly_do_cho = nhuong_luot_lon`; C được nhận khi pool rút.
3. **Không tràn**: suốt 1–2, `/slots` của B: Σ `n_ctx_used` ≤ `-c`; `gateway_err.log`
   không có `failed to find free space in the KV cache`/`context shift`; không lượt nào
   `content` rỗng do cắt.
4. **Không 429 sau 200**: số khối SSE `overloaded` = 0; nếu B 429 (khe nhả) thì
   `llm_waiters` ghi thử lại, khách vẫn nhận nội dung.
5. **Nhịp tim**: phiên LTTCODE thật (bản có `8354bd4`) ~150K (whale) chờ sau một whale
   khác > 300 s ⇒ LTTCODE không tự cắt; Cloudflare không 524 (dòng `: ltt-cho` mỗi 15 s, rồi nhịp B
   trong prefill).
6. **3.5 trên 186.368** (O-02): một lượt 3.5 ~200K token vào ⇒ 200 và trả lời (trước
   bước 3: 413 sau 200).
7. **Whale theo model**: lượt 3.8 ~25K mới (dưới 33.792) không còn là whale; ~40K là
   whale (đọc `llm_waiters.la_whale`).

---

## 6. Rủi ro và câu hỏi mở

| # | rủi ro / câu hỏi | cách chặn |
|---|---|---|
| R-1 | "Suy nghĩ nằm trong `max_tokens`" (không cộng `reasoning_budget`) dựa trên đọc `server-context.cpp` (L-12b), chưa đo trên bản b10883 đang chạy | Bước 4: một lượt `max_tokens=512`, `reasoning_effort=xhigh` (budget 4096) ⇒ `token_ra ≤ 512`. Nếu vượt ⇒ `out_giu = max(max_tokens, budget) + max_tokens` và cập nhật §3.1 |
| R-2 | ✅ ĐÃ ĐÓNG ở L-27 (`uoc_token.py`, cận trên có chứng minh). ~~Ước 2,5 ký tự/token có thể **thấp** với một số nội dung (base64, CJK) ⇒ đặt chỗ thiếu ⇒ tràn `-kvu`~~ | rào B giữ; `bien_pool` từ số đo; B đã `/tokenize` khi ước vượt trần — cân nhắc `/tokenize` thật cho lượt > `nguong_whale` (thêm ~1 round-trip cho lượt lớn, không cho lượt nhỏ) |
| R-3 | Đổi `-np`/`-c` 3.8 đổi biên VRAM mà residency/ComfyUI giả định (445 MiB, `residency.py:51,674`) | bước 4 chạy lại kiểm cư trú (một job ảnh sau khi 3.8 nạp) trước khi mở cửa sổ ảnh |
| R-4 | `uoc_moi` nhớ trong tiến trình (nhiều worker web) ⇒ cờ whale lệch giữa worker | chỉ lệch thứ tự (đã ghi `uoc_moi.py:9-13`); sau O-01 B không còn dùng cờ ⇒ không thành 429 |
| R-5 | Khe nhả lease A/B (O-04) có thể thành vòng thử lại nếu B kẹt suất (rò) | trần 3 lần + hạn chờ; `CAPACITY_REFUSED` + log lý do B; B thu hồi 1.200 s vẫn còn |
| R-6 | Bỏ RPM ở B mất một lớp chống bão từ tiến trình gọi thẳng `:8299` (eval, `tools/soi_troi_may_b.py`) — không qua A | chấp nhận: đó là công cụ nội bộ; hoặc giữ RPM **chỉ** cho khoá không phải của nền tảng |
| R-7 | Sau khi gộp L-12b, `test_1203` ví dụ chủ dự án dùng `tok=` tự dựng ⇒ xanh dù đường thật (với `out_giu` 32.768) không backfill | bước 2 thêm phép kiểm qua `luat_cho` thật |
| R-8 | `--no-cache-idle-slots` có trên máy mà không có trong kho: deploy yaml từ kho sẽ **gỡ** nó âm thầm | trước bước 3/4: đối chiếu `/running` với yaml, đưa cờ vào kho (O-19) |
| R-9 | Nhánh đang mang `d635b695` (ComfyUI theo nhu cầu, máy B) — gộp `main` rồi deploy B sẽ kéo thay đổi dịch vụ | deploy render gateway là một việc riêng, có người vận hành xác nhận `LTTComfyUI` khởi động theo nhu cầu |
| Q-1 | Mốc decode tối thiểu mỗi luồng để chấp nhận `-np` lớn hơn (§4.1 m1 dùng 40 tok/s tạm) | chủ dự án chốt |
| Q-2 | §4.3 chọn (1)/(2)/(3) | chủ dự án chốt |
| Q-3 | Có muốn `seq_cap < np` (vd giữ một slot engine cho nội bộ/kiểm tra sức khoẻ) không | mặc định `seq_cap = np` |
| Q-4 | Có giữ trần tài khoản `ceil(N/2)` khi N tăng lên 4–6 không | mặc định giữ công thức |

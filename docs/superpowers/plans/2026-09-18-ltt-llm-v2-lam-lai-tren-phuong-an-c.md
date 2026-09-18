# LTT LLM v2 — làm lại trên nền Phương án C · Implementation Plan (bản 2, đã rà)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sửa các lỗi và chồng chéo còn sống trong hệ thống LTT LLM đang chạy, và đưa những việc còn giá trị của phiên "Serving v2" (đã xoá) lên production — làm lại trên cấu trúc Phương án C, không hồi sinh cơ chế đã gỡ.

**Architecture:** Mỗi task là một nhánh ngắn từ `main` trong worktree riêng, TDD (test đỏ trước), commit nhỏ, L1/L2 rồi deploy theo đúng chiều. Số theo model chỉ ở `apps/ltt_llm/ngan_sach.HO_SO` (và hàm suy ra: `tran_vao_cua`, `cong_bo_cua`, `nen_cua`); công thức giữ chỗ chỉ ở `platform_core/llm/tham_so_da_luot.luat_cho(suc: AdmissionModel, …)` gọi qua `platform_core/runtime_noi_bo/luong._dat_cho`; máy B là rào vật lý đọc `-c/-np` từ `llama-swap.yaml` và giữ `max(X-LTT-Token-Dat, token_vao_do_B, 1)` (`llm_gateway/vat_ly.token_giu`).

**Tech Stack:** Python 3.13 (FastAPI, SQLAlchemy), pytest (-n ≤ 6), llama.cpp (ghim 91f6a6cf3) sau llama-swap v250 trên máy B, PowerShell deploy.

**Spec / nguồn chân lý (đọc trước):** `docs/ltt_llm_dual/KE_HOACH_PHUONG_AN_C.md` (§3, §6 R-2), `BAN_DO_DUONG_DI.md`, `RUNBOOK.md` (§2.1 chiều deploy, §2.3b), `DECISION_LOG.md` (L-23, L-24, L-25 khi gộp), `docs/QUYET_DINH_NEN_TANG.md` (Q131). Ba bản rà 18/09 làm căn cứ cho bản plan này được tóm ở mục "Căn cứ".

## Global Constraints

- Hợp đồng `docs/00_LTT_OPERATING_CONTRACT.md`: trong phiên chỉ test nhắm + L1/L2; **không L3 giữa pha**; deploy chỉ sau L1/L2 xanh trên đúng SHA, qua `setup\deploy_nang_quyen.ps1` từ PowerShell; báo phiên khác trước deploy. `core:provider` có 112 tệp test ⇒ là lệnh nặng: `python tools\cua_so_yen.py trang-thai` + `python tools\tai_may.py` trước.
- Không gộp nhánh `llm-v2/*`. Commit cũ được giữ bằng tag `luu-tru/serving-v2/*`. Chỉ cherry-pick commit được nêu tên; còn lại viết lại.
- Không đưa lại tên ĐÃ GỠ ở L-23: `LE`, `SO_SLOT_MAY_B`, `DONG_THOI_MAY_B`, `POOL_KV*`, `SO_SLOT`, `LE_NGU_CANH`, `X-LTT-Whale`, env `LTT_LLM_NGUONG_WHALE|DEM_DAT_TRUOC|TOKEN_MOI_ANH|MAX_INPUT_TOKENS|MAX_DONG_THOI|TOKEN_POOL|RPM`, `luat_cho(pool, …)`, `dem_dat_truoc`, `token_moi_anh`.
- Số theo model chỉ ở `HO_SO`: `engine_ctx` 221184/262144, `np` 3, `seq_cap` 3, `bien_pool_token` 8192, `dem_uoc` 2048, `token_giu_moi_anh` 2048, `nguong_whale` 8192/16384. Bản sao khác phải được test đối chiếu.
- Chiều deploy (RUNBOOK §2.1): **tăng** sức chứa hoặc **nới** A ⇒ B trước; **giảm**/siết ⇒ A trước; nếu A giữ ít hơn B đếm ⇒ vi phạm "A ⊆ B" ⇒ B trước hoặc đồng thời.
- Máy B: đổi `llama-swap.yaml` chỉ qua kho + `llm_gateway/deploy/deploy.ps1`; `-watch-config` nạp lại **cả hai** model mỗi lần lưu (mất cache); mọi deploy B phải tách nhánh **sau** khi Task 1 gộp (nếu không sẽ kéo B về cache 12288 / sàn 48).
- Quyết định mới đánh số từ **L-25** (L-25 = cache 24G/sàn 24G, gộp ở Task 1).
- Không in khoá/token; khoá thử ở `secrets\keyltt_thu_nghiem.txt` chỉ đọc trong script; token máy B chỉ qua `chay_voi_may_b.py`.

---

## Căn cứ (ba bản rà 18/09)

**Rà plan bản 1 (NO-GO → sửa):** R-04 tái hiện được (38 mới + 9.844 cache ⇒ 0 credit); ảnh bị llama.cpp chặn sẵn ở 4.096 token (`tools/mtmd/clip.cpp`, QWEN2VL/25VL/3VL: `set_limit_image_tokens(8, 4096)`) ⇒ task ảnh cũ sai tiền đề; ước token: văn xuôi Anh ×2,25, **code ×0,74**, CJK ×0,42, hex ×0,45, emoji ×0,16; lỗi sau 200 đã đúng giao thức, chỉ thiếu trước 200; danh sách trường ghi đè suy nghĩ đúng là của 026f52dd.

**Suy nghĩ của model:** Qwen3.5-9B chính thức chỉ bật/tắt; Qwen3.8-27B có `low|medium|xhigh` (mặc định xhigh, không có `high`). Template v22.5 dùng chung: `medium` = prompt chính thức; `low/xhigh` chèn câu 3.5 chưa được dạy. llama.cpp cho mỗi request ghi đè budget (`server-common.cpp:1366-1369`); Anthropic `thinking` không ghi số ⇒ budget 10.000 (`server-chat.cpp:586-591`).

**Rà thông số:** B chạy nhánh `phien/cache-24g` chưa gộp (DRIFT); catalog `/v1/models` khai 3.8 mặc định `medium` và 3.5 có 3 mức (CONFLICT với Q131); client ghi đè được suy nghĩ ở cửa stream (CONFLICT); `providers.py:288` khai 3.8 `vision: False` (CONFLICT, `auto_scan_video` dùng sai model); B thu suất sau 1.200 s tính từ lúc nhận (CONFLICT tiềm ẩn với lượt dài); các bản sao gõ tay không test; tài liệu cũ.

---

## File Structure

| Tệp | Trách nhiệm | Task |
|---|---|---|
| `llm_gateway/deploy/llama-swap.yaml`, `llm_gateway/config.py`, `llm_gateway/deploy/deploy.ps1` | cấu hình B (gộp từ `phien/cache-24g`) | 1 |
| `platform_core/llm/dem_token_luong.py` | usage mọi giao thức về một nghĩa `token_vao` = tổng prompt | 2 |
| `server/api/tools.py` | catalog `/v1/models` đọc mức suy nghĩ theo model từ `examples` | 3 |
| `platform_core/runtime_noi_bo/luong.py` (`tien_kiem`, `chuan_bi`), `server/api/streaming.py` | gỡ trường ghi đè suy nghĩ ở **mọi** cửa; chuẩn hoá effort theo model | 4 |
| `apps/ltt_llm/ngan_sach.py` (sàn `max_tokens`, `_SAN_NHE`, ghi chú `none`), `apps/ltt_llm/manifest.py:442` | sàn ra ≥ budget + trả lời; xoá `none` | 4 |
| `platform_core/providers.py:288,326` | 3.8 đọc ảnh; bản sao `-c` có test | 5 |
| `llm_gateway/gioi_han.py:44,230` | gia hạn suất theo tiến triển, không theo lúc nhận | 6 |
| `platform_core/llm/uoc_token.py` (mới) hoặc hàm ước hiện có (`KY_TU_MOI_TOKEN` ở `apps/ltt_llm/ngan_sach.py:642`, `llm_gateway/ngan_sach.py:102`) | cận trên chứng minh được + overhead template | 7 |
| `server/api/streaming.py:302` | 413 trước 200 đúng câu từng giao thức | 8 |
| `sdk/ltt_cai_dat_cli.py:89,136`, `tools/cam_cli.py`, `CLAUDE_CONFIG_MATRIX.md` | tách ngưỡng nén Claude Code khỏi Codex | 9 |
| `tools/kiem_co_lap_llm.py`, `tools/cong_mtp.py`, test ghim `/slots`, bộ chấm A/B | công cụ kiểm định kỳ | 10 |
| tài liệu cũ, `llm_gateway/ngan_sach.py:109`, `tools/do_ngan_sach_chuyen_loi_thoai.py` | dọn bản sao + tài liệu sai | 11 |

---

### Task 0: Dọn phiên cũ — ĐÃ XONG 18/09

- [x] Chép 6 tệp đo thô (C0 + C1) vào `docs/ltt_llm_dual/artifacts/serving_v2_luu_tru/` (commit 4074dc02).
- [x] Huỷ phép gộp dở ở worktree `llm-v2-p2-token` (nhánh về 7d443461, sạch).
- [x] Đổi tên `H:\LTT_LLM\gateway\llama-swap.yaml.goc_s1` thành `llama-swap.yaml.LOI_THOI_17-09_khong-dung-de-khoi-phuc`.
- [x] Tag giữ commit: `luu-tru/serving-v2/llm-v2-p1-cache` (631be161), `…/llm-v2-p2-token` (7d443461), `…/claude-ltt-llm-duo-serving-v2-a1c85c` (10ac1f81).
- [x] Xoá phiên "LTT LLM Duo agent serving v2".

---

### Task 1: Gộp cấu hình máy B đang chạy vào `main` (hết DRIFT) — CHẶN mọi deploy B khác

**Files:** nhánh `phien/cache-24g` (c3b08e3c, 96314e56 + commit cuối của agent đang chạy); `DECISION_LOG.md` (L-25); `KE_HOACH_PHUONG_AN_C.md:68`.

- [ ] **Step 1:** Chờ agent cache-24G báo cáo xong (đo 30 hội thoại, không từ chối, chuyển card ảnh nếu an toàn). Đọc báo cáo; nếu sàn 24 GB không an toàn khi chuyển card sang ảnh, agent phải đã thêm biện pháp an toàn (xả cache khi chuyển) — kiểm trong diff.
- [ ] **Step 2:** Test nhắm `gateway:llm` trên nhánh:
  `python tools\thanh_phan.py --test gateway:llm` → chạy các tệp đó `-n 6`. Kỳ vọng: xanh.
- [ ] **Step 3:** Kiểm hash `llama-swap.yaml` của nhánh == hash trên B (`Get-FileHash H:\LTT_LLM\gateway\llama-swap.yaml`).
- [ ] **Step 4:** L2 `gateway:llm`; gộp `main` (`git merge --ff-only` nếu được, nếu không thì merge thường sau khi hoà `main`).
- [ ] **Step 5:** Làm mới ảnh chụp env của dịch vụ trên B bằng `llm_gateway/deploy/cai_dat_dich_vu.ps1` (nssm nướng env lúc cài) — lúc vắng khách, chỉ restart `LTTLlmGateway`.
- [ ] **Step 6:** Sửa `KE_HOACH_PHUONG_AN_C.md:68` ("cache-ram mặc định 8192, chưa đo") thành dẫn chiếu L-25; commit.

---

### Task 2: R-04 — `/messages` có cache không còn tính token mới bằng 0 (lỗi tiền đang sống)

**Files:** `platform_core/llm/dem_token_luong.py` (`DemToken._gop`, dòng ~140); Test: `tests/test_1410_usage_theo_giao_thuc.py` (từ e0bd36b9), `tests/test_271_dem_token_luong.py`.

**Interfaces:** Produces `DemToken.su_dung() -> SuDung` với bất biến: `token_vao` = tổng prompt (gồm cache) cho mọi giao thức; `token_vao_cache <= token_vao`.

- [ ] **Step 1: Test đỏ trước.** Worktree `git worktree add D:\LTTSTUDIOSAPP-r04 -b phien/llm-r04 main`. Lấy riêng tệp test: `git checkout e0bd36b9 -- tests/test_1410_usage_theo_giao_thuc.py`. Thêm ca:

```python
def test_messages_cache_hit_van_tinh_token_moi():
    from platform_core.llm.dem_token_luong import DemToken
    d = DemToken()
    d.nhin(b'data: {"type":"message_start","message":{"usage":{"input_tokens":38,"cache_read_input_tokens":9844,"output_tokens":1}}}\n\n')
    d.nhin(b'data: {"type":"message_delta","usage":{"output_tokens":120}}\n\n')
    su = d.su_dung()
    assert su.token_vao == 38 + 9844
    assert su.token_vao_cache == 9844
    assert su.token_vao - su.token_vao_cache == 38
```

- [ ] **Step 2:** `python -m pytest tests/test_1410_usage_theo_giao_thuc.py -q` → kỳ vọng **FAIL** (4 ca cũ + ca mới).
- [ ] **Step 3:** `git cherry-pick -n e0bd36b9` (chỉ còn thay đổi ở `dem_token_luong.py` và `test_271`).
- [ ] **Step 4:** Chạy lại `test_1410` + `test_271` → PASS. Đối chứng: tạm bỏ dòng `gt += cache_a` → ca mới phải đỏ; khôi phục.
- [ ] **Step 5:** Kiểm máy; test nhắm `core:provider` (-n 6); ruff/mypy tệp chạm; commit.
- [ ] **Step 6:** L2 `core:provider`; gộp; deploy A. Sau deploy: một lượt `/v1/messages` lặp lại (trúng cache) bằng khoá thử; bút toán credit phải > 0 và khớp giá token mới.

---

### Task 3: Catalog `/v1/models` khai đúng mức suy nghĩ theo từng model

**Files:** `server/api/tools.py:40-43,70-71` (`_MUC_SUY_LUAN`, `_dang_codex`); nguồn: `platform_core/public_api/examples.py` (`CODEX_MODEL_REASONING`, `CODEX_MODEL_REASONING_LEVELS`, dòng ~810–821); Test: mở rộng test catalog hiện có (`grep -rln "default_reasoning_level" tests/`).

- [ ] **Step 1: Test đỏ:** gọi hàm dựng catalog (tên thật trong `tools.py`), kiểm `ltt-3.8.default_reasoning_level == "xhigh"`, mức = `["low","medium","xhigh"]`; `ltt-3.5` mức = `["medium"]` (hoặc danh sách Task 4 chốt), mặc định `"medium"`.
- [ ] **Step 2:** Chạy → FAIL (hiện khai `medium` + 3 mức cho mọi model).
- [ ] **Step 3:** `_dang_codex` đọc từ `examples`; xoá `_MUC_SUY_LUAN` gõ cứng.
- [ ] **Step 4:** PASS; cập nhật golden `tests/golden/public_api_catalog_v1.json` (bỏ `none`); commit; L2 `server:api`; deploy A. Kiểm live `/api/v1/models`.

---

### Task 4: Suy nghĩ do máy chủ quyết — gỡ ghi đè ở mọi cửa; chuẩn hoá effort theo model

**Quyết định cần chủ dự án chốt trước (đề xuất, lấy từ bản rà):**
- **3.5:** chỉ một chế độ, **suy nghĩ BẬT**. Nhận `low|medium|high|xhigh` không trả 400 (Codex luôn gửi), nhưng **gỡ `reasoning_effort` trước khi gửi B** (⇒ template dùng nhánh mặc định = prompt chính thức) và trả header `X-LTT-Effort-Bo-Qua: 1`. Tắt suy nghĩ: cấm (đã đo hỏng).
- **3.8:** `low|medium|xhigh`, mặc định `xhigh`; `high`/`max` ⇒ `xhigh`; `minimal` ⇒ `low`.
- Budget suy nghĩ do engine (`--reasoning-budget` 4096/2048) — client không đổi được.

**Files:** `platform_core/runtime_noi_bo/luong.py` (`tien_kiem`, `chuan_bi`, chỗ `gui = dict(than)` ~dòng 333), `server/api/streaming.py:757`, `apps/ltt_llm/features.py:382-424` (dùng chung một hàm chuẩn hoá), `apps/ltt_llm/ngan_sach.py` (sàn `max_tokens` 3.5 ~dòng 583; `_SAN_NHE`; ghi chú `:552-554`), `apps/ltt_llm/manifest.py:442`.

**Interfaces:** Produces `chuan_hoa_suy_nghi(than: dict, model_id: str) -> tuple[dict, bool]` (thân đã gỡ/chuẩn hoá, cờ "đã bỏ qua effort") — một chỗ, mọi cửa gọi.

- [ ] **Step 1: Test đỏ (danh sách trường theo 026f52dd):** với thân chứa `reasoning_budget_tokens`, `thinking_budget_tokens`, `reasoning_budget_message`, `reasoning_control`, `thinking: {"type":"enabled","budget_tokens":10000}`, `chat_template_kwargs: {"enable_thinking": false, "preserve_thinking": true}`, `reasoning: {"effort":"none"}` và nội dung tin nhắn chứa `<|think_off|>` → thân gửi B ở **cả ba cửa** (`/chat/completions`, `/messages`, `/responses`) không còn các trường/thẻ đó.
- [ ] **Step 2: Test đỏ effort:** 3.5 + `xhigh` ⇒ thân gửi B không có `reasoning_effort`, header bỏ qua = 1; 3.8 + `high` ⇒ `xhigh`; 3.8 + `none` ⇒ 400 (cả ba cửa, kể cả `reasoning.effort` của Responses).
- [ ] **Step 3: Test đỏ sàn:** sàn `max_tokens` của 3.5 ≥ `reasoning_budget` 2048 + 512 (đọc budget từ yaml qua test, không gõ số).
- [ ] **Step 4:** Cài `chuan_hoa_suy_nghi` (viết lại từ 026f52dd + 941badbf phần effort, trên `luong.py` hiện tại); gọi ở ba cửa; sửa sàn; xoá `none` ở `manifest.py:442`, `_SAN_NHE`, ghi chú `ngan_sach.py:552-554`.
- [ ] **Step 5:** PASS; test nhắm `core:provider`, `app:ltt_llm`, `server:api`; commit; L2 từng thành phần; deploy A.
- [ ] **Step 6: Kiểm client thật:** Claude Code gửi `thinking` ⇒ lượt trả lời bình thường, budget không vượt 4096 (đếm token suy nghĩ trong log B).

---

### Task 5: `providers.py` — 3.8 đọc ảnh; bản sao `-c` có test

**Files:** `platform_core/providers.py:287-288,326`; Test: mở rộng `tests/test_334_ngan_sach_ltt_llm.py`.

- [ ] **Step 1: Test đỏ:** với mỗi model trong `HO_SO`, mục tương ứng trong `providers` có `context_window == HO_SO[m].engine_ctx` và `vision is True` (cả hai nạp mmproj).
- [ ] **Step 2:** FAIL (3.8 `vision: False`; ca 3.5 hiện không được test).
- [ ] **Step 3:** Sửa `vision: True`; kiểm `apps/auto_scan_video/ai.py:216` — nếu việc ảnh cần giữ 3.5 thì chỉ định tường minh ở đó (ghi lý do).
- [ ] **Step 4:** PASS; test nhắm `core:provider`, `app:auto_scan_video`; commit; L2; deploy A.

---

### Task 6: Máy B gia hạn suất theo tiến triển (không thu suất đang chạy thật)

**Files:** `llm_gateway/gioi_han.py:44,230`; Test: mới trong nhóm `gateway:llm`.

- [ ] **Step 1: Test đỏ:** một suất nhận lúc t=0, luồng chuyển chunk đều tới t=1.300 s (giả lập đồng hồ) ⇒ **không** bị thu; một suất im lặng (không chunk) ⇒ bị thu sau hạn im lặng.
- [ ] **Step 2:** FAIL (hiện thu theo lúc nhận, `han_giu_s` 1.200).
- [ ] **Step 3:** Mỗi chunk/nhịp tim gia hạn `lan_cuoi`; thu khi `now - lan_cuoi > han_im_lang` (đặt ≥ `stream_timeout_s` 900 của B). Đổi tên trường `/health` `max_dong_thoi` thành tên theo `-np` nếu không phá client đọc nó (grep trước).
- [ ] **Step 4:** PASS; test nhắm `gateway:llm`; commit; L2; deploy B (chỉ mã cổng, `-BoQuaYaml`, restart `LTTLlmGateway` lúc vắng khách).

---

### Task 7: Ước token là cận trên thật (R-2 của Phương án C)

**Files:** hàm ước hiện có (`grep -rn "def uoc_token_vao\|KY_TU_MOI_TOKEN" apps platform_core llm_gateway`), `llm_gateway/ngan_sach.py:355` (nhánh đếm thật); fixture có sẵn `tests/fixtures/ngu_lieu_token/*` (từ 9cc80640 — kiểm tồn tại; nếu chưa có trên `main`, `git checkout 9cc80640 -- tests/fixtures/ngu_lieu_token`).

- [ ] **Step 1: Test đỏ cận trên:** với mọi mẫu (en_prose, vi_markdown, code_py, cjk_zh, hex, emoji…) và mọi model, `uoc(x) + overhead_template(x) >= that(x)`, với `overhead_template` = 256 + 16/tin nhắn + 64/tool (số đo 9cc80640). Hiện đỏ ở code_py (0,74), cjk (0,42), hex (0,45), emoji (0,16).
- [ ] **Step 2: Test đỏ không quá tay:** `uoc(en_prose) <= 1,5 × that`, `uoc(vi_markdown) <= 1,5 × that`.
- [ ] **Step 3: Cài ước theo byte UTF-8 có trần** (dạng cận trên của 9cc80640: token ≤ số byte với tokenizer BPE byte-level; dùng hệ số theo lớp chỉ để **hạ** xuống nhưng không dưới số đo lớn nhất của lớp đó) + overhead template. Ghi chứng minh cận trên trong docstring.
- [ ] **Step 4:** A và B dùng cùng một hàm (B đang có bản sao ở `llm_gateway/ngan_sach.py:102` — thay bằng import chung hoặc test đối chiếu byte-for-byte như test_1223).
- [ ] **Step 5: Deploy theo chiều:** ước **tăng** cho code/CJK/emoji = A giữ nhiều hơn ⇒ an toàn deploy A trước; phần **giảm** cho văn xuôi Anh = nới ⇒ deploy B trước. Nếu một commit làm cả hai: deploy B trước rồi A ngay sau (B chấp nhận cả hai vì B lấy `max(khai, đo)`).

---

### Task 8: 413 trước 200 đúng câu từng giao thức (R-08)

**Files:** `server/api/streaming.py:302` (`payload_too_large` chung); tái dùng `server/api/su_kien_loi.py` (đã đúng cho lỗi sau 200).

- [ ] **Step 1: Test đỏ:** thân vượt `tran_vao_cua` gửi tới `/v1/messages` ⇒ HTTP 400/413 với thân `{"type":"error","error":{"type":"invalid_request_error","message":"prompt is too long: …"}}`; `/v1/responses` ⇒ lỗi `context_length_exceeded` đúng schema Responses; `/v1/chat/completions` ⇒ `code: "context_length_exceeded"`.
- [ ] **Step 2: Test đỏ nhịp chờ Responses:** luồng `/v1/responses` chờ hàng đợi lâu hơn `nhip_tim_cho_s` (đọc từ `tham_so_da_luot`, không gõ 15) phát sự kiện `response.in_progress`, không chỉ comment `: ltt-cho`.
- [ ] **Step 3:** Cài bằng cách dùng lại bộ dựng lỗi của `su_kien_loi.py`.
- [ ] **Step 4:** Kiểm với Claude Code thật: prompt quá dài ⇒ client tự nén, không kẹt. Commit; L2 `server:api`; deploy A.

---

### Task 9: Tách ngưỡng nén Claude Code khỏi Codex (R-05)

**Files:** `sdk/ltt_cai_dat_cli.py:89` (`NEN_HOI_THOAI = 138690`), `:136` (`CUA_SO_NEN_CLAUDE = NEN_HOI_THOAI`); `tools/cam_cli.py:144,231,1784`; `docs/.../CLAUDE_CONFIG_MATRIX.md`, `docs/PUBLIC_API/HUONG_DAN_CAM_CLI.md`.

- [ ] **Step 1: Đo:** Claude Code thật với cửa sổ 138.690 nén ở bao nhiêu token (log `/context` lúc nén) — kỳ vọng ~105.690 (tự trừ `min(maxOut,20000) + 13000`).
- [ ] **Step 2: Test đỏ:** `CUA_SO_NEN_CLAUDE − min(TOKEN_RA_CLIENT, 20000) − 13000 == NEN_HOI_THOAI` (điểm nén thực bằng ngưỡng Codex), và `CUA_SO_NEN_CLAUDE <= cong_bo_cua(m)` (không vượt cửa sổ công bố). Test so hằng trong SDK (tệp đứng riêng, không import `ngan_sach`) với số suy từ `ngan_sach`.
- [ ] **Step 3:** Thêm hằng riêng cho Claude; Codex giữ `model_auto_compact_token_limit` = `NEN_HOI_THOAI`.
- [ ] **Step 4:** Kiểm lại client thật; cập nhật hai tài liệu; commit; L2; deploy (nội dung bộ cài CLI tải từ nền tảng).
- [ ] **Step 5 (R-13):** Bộ cài hiện **giữ nguyên** profile Codex/Claude cũ của người đã cài ⇒ thêm bước cập nhật khoá do LTT quản lý (chỉ các khoá LTT sở hữu), có test không đè khoá của người dùng.

---

### Task 10: Công cụ kiểm định kỳ trên cấu hình hiện tại

**Files:** `tools/kiem_co_lap_llm.py` + `tests/test_1407*` (0bb171ca), ghim `/slots` (a538a12b), bộ chấm A/B (467832cd), `tools/cong_mtp.py` + `tests/test_1408*` (fb492568) — cả bốn gộp sạch (đã mô phỏng).

- [ ] **Step 1:** Cherry-pick từng commit; chạy test đi kèm → PASS.
- [ ] **Step 2:** Canary cô lập 200 lượt/model: gọi thẳng engine `127.0.0.1:8280` trên B (không tốn credit) — **giờ vắng khách**, sau Task 1. Đạt: 0 rò rỉ giữa phiên.
- [ ] **Step 3:** `cong_mtp.py` một lượt **không đối chứng E3** (ghi rõ: E3 cần 1 slot, không MTP — phải đổi cờ nên không chạy); không đổi cờ MTP.
- [ ] **Step 4:** Ghi lịch chạy lại vào RUNBOOK (sau mỗi lần nâng llama.cpp).

---

### Task 11: Dọn bản sao gõ tay và tài liệu sai

- [ ] `llm_gateway/ngan_sach.py:109` đổi `TOKEN_MOI_ANH` → `TOKEN_GIU_MOI_ANH` + test đối chiếu với `HO_SO[m].token_giu_moi_anh` (hết trùng tên với `TOKEN_MOI_ANH = 770` của hoá đơn).
- [ ] `platform_core/providers.py` `nap_model_s: 18` → dẫn chiếu `ngan_sach.NAP_KHO_AM_S` hoặc bỏ.
- [x] `tools/do_ngan_sach_chuyen_loi_thoai.py:187,210` — lời khuyên `DONG_THOI_MAY_B=1` ĐÃ GỠ (a749d1ea).
- [ ] `platform_core/public_api/examples.py:841-842` sửa chú thích "LTT dùng 3" → khớp giá trị 10; `server/api/tools.py:36` chú thích `MAX_TOKENS_TRAN` → `TOKEN_RA_TRAN`.
- [ ] `docs/VLM_NOI_BO/CAM_CLI.md:255`, `docs/QUYET_DINH_NEN_TANG.md:304-326` gắn "ĐÃ GỠ (L-23)".
- [ ] LTTCODE `plugins/llm-ltt/src/adapter.ts` `KNOWN_CONTEXT_WINDOWS`: thêm kiểm chéo kho (so với `/api/v1/models` live trong phép kiểm bản cài) — việc ở kho LTTCODEAPP.
- [ ] Mỗi mục một test hoặc grep-check; commit; test nhắm; gộp (không cần deploy riêng — đi cùng lần deploy kế).

---

### Task 12: Chất lượng 3.5 — đo đúng chỗ lệch model card (sau Task 4)

- [ ] **Step 1:** Dựng bộ đề cố định (coding + tiếng Việt + gọi công cụ, dùng bộ chấm A/B của Task 10).
- [ ] **Step 2:** Ba phép A/B riêng, mỗi phép một biến: `presence_penalty` 0 ↔ 1,5; temp coding 1,0 ↔ 0,6; `--reasoning-budget` 2048 ↔ 4096. Mỗi đổi cờ engine = một lần nạp lại model ⇒ gom vào một cửa sổ vắng khách, dùng `POST /api/models/unload/qwen35-api` để không đụng 3.8.
- [ ] **Step 3:** Chỉ đổi cấu hình production khi thắng rõ trên bộ đề; ghi L-mới.

---

### Task 13: Chọn mức suy nghĩ trong LTTCODE theo từng model (chủ dự án yêu cầu 18/09)

**Mục tiêu:** như Claude — người dùng thấy danh sách mức của **đúng model đang chọn**, lấy từ catalog `/api/v1/models` (Task 3), không gõ cứng trong app. 3.8: `low · medium · xhigh` (mặc định xhigh). 3.5: một mức "Suy nghĩ" cố định (không có nấc giả). Thông số lấy mẫu mỗi mức theo **khuyến nghị model card** (Task 12 Step 0).

**Files (kho D:\LTTCODEAPP):** `plugins/llm-ltt/src/adapter.ts` (đọc `default_reasoning_level` + danh sách mức từ catalog, gửi `reasoning_effort` chỉ khi model có mức), preset/UI chọn effort của DSH (tra `node_modules` DSH xem có sẵn điều khiển effort/`reasoningEffort` trong composer không — dùng cái có sẵn trước khi tự làm), test adapter.

- [ ] **Step 1:** Tra DSH 0.1.6-alpha.1: composer có ô chọn effort không, lấy danh sách từ đâu (model metadata của adapter?). Ghi nguồn.
- [ ] **Step 2: Test đỏ adapter:** model `ltt-3.8` ⇒ khai 3 mức, mặc định xhigh, gửi đúng mức người chọn; `ltt-3.5` ⇒ khai 0 mức chọn được (hoặc 1 mức cố định), **không** gửi `reasoning_effort`.
- [ ] **Step 3:** Cài; kiểm giao diện trên bản cài (ảnh chụp); build theo quy trình phát hành LTTCODE (bản 0.1.8), dev trước, stable sau.

### Task 12 Step 0 (bổ sung): áp thông số lấy mẫu theo model card

- [ ] Tra model card Qwen3.5-9B và Qwen3.8-27B (Hugging Face) — bảng khuyến nghị theo chế độ (suy nghĩ / không; chung / coding): `temperature`, `top_p`, `top_k`, `min_p`, `presence_penalty`, `repetition_penalty`, độ dài ra khuyến nghị. So với cờ engine trong `llama-swap.yaml` (`--temp 1.0 --top-p 0.95 --top-k 20 --min-p 0`, không có presence penalty). Lập bảng lệch; đổi cấu hình theo card **trong một cửa sổ bảo trì**, xả từng model bằng `POST /api/models/unload/<model>`, rồi chạy bộ đề Task 12 để xác nhận không tụt (giữ nếu ≥ cũ, trả lại nếu tụt).

## Đối soát các mục R của phiên cũ

| Mục | Trạng thái |
|---|---|
| R-01 | Thay bằng canary cô lập (Task 10) |
| R-03, R-08, R-12 | Task 8 (phần trước 200 + nhịp Responses); phần sau 200 đã có |
| R-04 | Task 2 |
| R-05 | Task 9 |
| R-09 | Thay bằng Task 4 (khuyến nghị theo model card) |
| R-13 | Task 9 Step 5 |
| R-15 | Task 7 (overhead template) |
| R-19 | **Bỏ** — llama.cpp chặn ảnh ở 4.096 token; `token_giu_moi_anh` 2.048 chỉ ước thấp ảnh > ~2 MP, dư biên 8.192 ⇒ ghi rủi ro nhỏ, có thể đặt `--image-max-tokens` tường minh ở lần bảo trì sau (đo 1 ảnh 12 MP trước) |
| R-20 | **Bỏ** — "MTP trả rỗng" thực ra là hết `max_tokens` (Task 4 Step 3 sửa sàn) |
| R-21 | Task 7 |
| R-22 | Task 4 |
| R-06, R-07 | **Hoãn** (xác minh 18/09 chiều) — chưa đọc header phiên của client (grep 0); sổ B cho stream chỉ có TTFT + mã kết thúc (`llm_gateway/so_luot.py:50-54`, cố ý). Việc sau plan: A ghi id phiên vào sổ lượt (không chuyển xuống B) + nối sổ B với usage của A qua `X-LTT-Request-Id` |
| R-10 | **Cần đo** — vẫn `base_instructions: ""` (`sdk/ltt_cai_dat_cli.py:264`, `tools/cam_cli.py:682`, `examples.py:988`). Đo A/B ở Task 12, kết quả ghi L-xx |
| R-11 | Bổ sung Task 9 (giao cùng Task 11) — profile Codex thêm `web_search = "disabled"` (SDK + `cam_cli`), kiểm bằng request bắt thật |
| R-14 | **Hoãn** (dự án riêng) — `ENABLE_TOOL_SEARCH=false`, chưa xử lý `defer_loading`/`tool_reference` |
| R-16 | Task 10 — công cụ p95 TTFT từ sổ lượt + cảnh báo nạp lạnh (`ttl: 1800`) |
| R-17 | **Cần đo** — Task 12: `preserve_thinking:false` cho `qwen35-api` (template mặc định `true`); so chất lượng, token, tỉ lệ trúng cache |
| R-18 | Một phần đã làm ở LTTCODE (trần in-flight `146d479`, nay theo model ở Task 14; retry riêng); tương quan phiên làm cùng R-06 |
| R-23 | **Đã làm** — `b1593e3` là tổ tiên của `main` (merge `30f1acbb`) |

## Thứ tự và song song

```
Task 1 (gộp cache-24G)  ── chặn mọi deploy B ─┐
Task 2 (R-04 tiền) ──────────── deploy A  [NGAY, song song Task 1]
Task 3 (catalog) ── Task 4 (suy nghĩ) ── deploy A
Task 5 (vision) ─────────────── deploy A
Task 6 (B gia hạn suất) ─── sau Task 1 ── deploy B
Task 7 (ước cận trên) ─── sau Task 1 ── deploy theo chiều
Task 8 (413 trước 200) ── sau Task 4 (cùng tệp streaming.py)
Task 9 (nén Claude/Codex) ─ độc lập
Task 10 ── Step 2–3 sau Task 1, giờ vắng
Task 11 ── rải theo các task trên
Task 12 ── sau Task 4 + Task 10
```

Ước: T1 1 giờ · T2 1 giờ · T3 1 giờ · T4 3 giờ · T5 0,5 giờ · T6 2 giờ · T7 3 giờ · T8 2 giờ · T9 2 giờ · T10 2 giờ · T11 1,5 giờ · T12 3 giờ ⇒ ~22 giờ công; song song còn ~9–10 giờ.

## Nghiệm thu mỗi task

1. Test đỏ trước, xanh sau, có đối chứng đảo sửa.
2. `git diff main... | grep -E "<tên đã gỡ L-23>"` rỗng.
3. L1/L2 xanh trên đúng SHA; `nghiem_thu_deploy.py` khớp tuyệt đối; đo sau deploy bằng khoá thử.
4. DECISION_LOG (L-25…), RUNBOOK, BAN_DO_DUONG_DI cập nhật cùng commit khi đổi hành vi.

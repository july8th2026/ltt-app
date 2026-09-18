# LTT LLM v2 — làm lại trên nền Phương án C · Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đưa những việc còn giá trị của phiên "LTT LLM Duo agent serving v2" lên production, làm lại trên cấu trúc Phương án C đang chạy — không gộp nhánh cũ, không hồi sinh cơ chế đã gỡ.

**Architecture:** Mỗi việc là một nhánh ngắn từ `main` (worktree riêng), TDD, cherry-pick nguyên khi sạch, viết lại khi đụng tệp Phương án C đã đổi. Mọi con số theo model đi qua **một** chỗ: `apps/ltt_llm/ngan_sach.HO_SO`; mọi giữ chỗ đi qua **một** công thức: `luong._dat_cho` → `luat_cho(AdmissionModel)`; máy B chỉ là rào vật lý đọc `-c/-np` từ `llama-swap.yaml` và `X-LTT-Token-Dat` từ A.

**Tech Stack:** Python 3.13 (FastAPI, SQLAlchemy), pytest (-n ≤ 6), llama.cpp server qua llama-swap v250 trên máy B, PowerShell deploy.

**Spec (nguồn chân lý, đọc trước):**
- `docs/ltt_llm_dual/KE_HOACH_PHUONG_AN_C.md` (§3 mô hình hợp nhất, §6 rủi ro — R-2 còn mở)
- `docs/ltt_llm_dual/BAN_DO_DUONG_DI.md`, `RUNBOOK.md` (§2, §2.3b), `DECISION_LOG.md` (L-23, L-24; L-25 đang được phiên cache-24G viết)
- Đối soát phiên cũ (18/09): kết quả nằm trong mục "Đối soát" dưới đây — thay thế plan `docs/superpowers/plans/…-p0…p10` của nhánh `llm-v2/*` (KHÔNG dùng các plan đó).

## Global Constraints

- Hợp đồng vận hành `docs/00_LTT_OPERATING_CONTRACT.md`: trong phiên chỉ test nhắm + L1/L2; **không L3 giữa pha**; deploy chỉ sau L1/L2 xanh trên đúng SHA; deploy qua `setup\deploy_nang_quyen.ps1` từ PowerShell; báo phiên khác trước deploy.
- Không gộp `llm-v2/p1-cache`, `llm-v2/p2-token`, `claude/ltt-llm-duo-serving-v2-a1c85c`. Chỉ cherry-pick commit được nêu tên dưới đây, hoặc viết lại.
- Không thêm lại tên đã gỡ ở L-23: `LE`, `SO_SLOT_MAY_B`, `DONG_THOI_MAY_B`, `POOL_KV*`, `SO_SLOT`, `LE_NGU_CANH`, `X-LTT-Whale`, env `LTT_LLM_NGUONG_WHALE|DEM_DAT_TRUOC|TOKEN_MOI_ANH|MAX_INPUT_TOKENS|MAX_DONG_THOI|TOKEN_POOL|RPM`, tham số `luat_cho(pool, …)`, `dem_dat_truoc`, `token_moi_anh`.
- Số theo model chỉ ở `HO_SO`: `engine_ctx` 221184/262144, `np` 3, `seq_cap` 3, `bien_pool_token` 8192, `dem_uoc` 2048, `token_giu_moi_anh` 2048, `nguong_whale` 8192/16384. Không sao chép số này sang tệp khác.
- Quyết định mới đánh số **L-26 trở đi** (L-23 = Phương án C, L-24 = bảo trì B 18/09, L-25 = cache 24G/sàn RAM 24G đang viết).
- Máy B: đổi `llama-swap.yaml` chỉ qua kho + `llm_gateway/deploy/deploy.ps1`; `-watch-config` đang bật nhưng **mỗi lần lưu yaml nạp lại cả hai model** (mất cache); đổi `-c/-np` phải khởi động lại `LTTLlmGateway` **và** sửa `HO_SO` cùng lúc.
- Không in khoá/token; khoá thử ở `secrets\keyltt_thu_nghiem.txt` chỉ đọc trong script; token máy B chỉ qua `chay_voi_may_b.py`.

---

## Đối soát phiên "Serving v2" (18/09) — kết luận khoá

| Việc cũ | Kết luận | Lý do (bằng chứng) |
|---|---|---|
| P0 kiểm nền production | **Bỏ** | production nay là `2b3977ad` |
| P1 T2 ma trận cache C0–C3 | **Bỏ** | C1 (`--no-cache-idle-slots`) cho 3.8 trúng 0,3 %; cấu hình hiện tại 99,6–99,7 % (`KET_QUA_CACHE_18_09`, `KET_QUA_BAO_TRI_18_09`) |
| P1 T7 đo sống sót cache | **Đã làm khác** | `KET_QUA_CACHE_18_09` §2b, `KET_QUA_BAO_TRI_18_09` |
| Quyết định bật/tắt MTP | **Bỏ** | MTP đang chạy (`--spec-type draft-mtp --spec-draft-n-max 2`) và là thứ cho phép lùi cache một phần (upstream #28425); 13 lượt "rỗng" của C1 đều `finish=length` = hết `max_tokens`, không phải lỗi engine |
| Kế hoạch deploy DG1–DG4, số L-23/L-24 của nhánh | **Bỏ** | hợp đồng vận hành thay thế; số đã dùng |
| P2 T1 R-04 (e0bd36b9) | **Giữ — Task 1** | lỗi tính tiền đang sống |
| P2 T2 R-19 ảnh theo kích thước thật (6a084b23) | **Làm lại — Task 2** | 2.048/ảnh chỉ đúng tới ~2,1 MP; ảnh điện thoại 12 MP ≈ 11.970 token, vượt cả biên 8.192 |
| P2 T3 R-21 cận trên + đếm thật (9cc80640) | **Làm lại — Task 3** | R-2 của Phương án C còn mở; ước có thể thấp 5× (ZH 0,23, emoji 0,20, hex 0,46) |
| P2 T4 413 phía A theo số thật (140ae523) | **Gộp vào Task 3** | viết lại trên `luong.py` mới; không thêm header song song với `X-LTT-Token-Dat` |
| P2 T5 lỗi tràn theo giao thức + `response.in_progress` (f0fad274) | **Làm lại — Task 4** | `main` chưa có |
| P3 T1b R-22 gỡ trường ghi đè ngân sách suy nghĩ (026f52dd) | **Làm lại — Task 5** | `main` chưa gỡ |
| P3 T3 ngưỡng nén Claude Code R-05 | **Làm — Task 6** | khác C5b của LTTCODE; Claude Code nén sớm ~33K |
| P1 T1 canary cô lập, T5 ghim `/slots`, P3 T1c bộ chấm A/B | **Giữ công cụ — Task 7** | chạy lại trên cấu hình hiện tại (upstream #28286, #26425 còn mở) |
| P1 T3 cổng MTP `cong_mtp.py` | **Giữ làm phép kiểm định kỳ — Task 7** | không dùng để quyết bật/tắt |
| P3 T1/T2 thang năng lực R-09 + catalog Codex | **Chờ quyết định — Task 8** | xung đột Q131 (3.5 mặc định `medium`) đang ở `main` |

---

## File Structure

| Tệp | Trách nhiệm | Task |
|---|---|---|
| `platform_core/llm/dem_token_luong.py` | chuẩn hoá usage mọi giao thức về một nghĩa `token_vao` = tổng prompt | 1 |
| `platform_core/llm/anh_token.py` (mới) | đếm token ảnh theo kích thước thật, một hàm thuần | 2 |
| `platform_core/runtime_noi_bo/luong.py` | `_dat_cho` nhận tổng token ảnh thay vì đếm số ảnh | 2, 3 |
| `apps/ltt_llm/ngan_sach.py` | `luat_cho` công thức giữ chỗ (`token_giu_moi_anh` thành giá trị lùi) | 2 |
| `platform_core/llm/uoc_token.py` (mới, nếu chưa có hàm tương đương — tìm trước) | cận trên ước lượng theo lớp ký tự | 3 |
| `llm_gateway/ngan_sach.py`, `llm_gateway/vat_ly.py` | B: đếm thật cả khi ước **dưới** trần nhưng sát biên | 3 |
| `server/api/streaming.py` + bộ dịch lỗi theo giao thức | lỗi tràn đúng định dạng Anthropic/Responses/Chat; nhịp `response.in_progress` | 4 |
| `platform_core/llm/tham_so_da_luot.py` hoặc nơi dựng thân request lên B | gỡ trường ghi đè ngân sách suy nghĩ | 5 |
| `sdk/ltt_cai_dat_cli.py`, `docs/.../CLAUDE_CONFIG_MATRIX.md` | ngưỡng nén Claude Code tính từ `tran_vao_cua` | 6 |
| `tools/llm/kiem_co_lap_llm.py`, `tools/llm/cong_mtp.py`, test ghim `/slots` | công cụ kiểm định kỳ | 7 |

---

### Task 0: Dọn phiên cũ an toàn (không mất dữ liệu)

**Files:** không sửa mã; chỉ lưu trữ dữ liệu đo.

- [ ] **Step 1: Chép dữ liệu thô C1 ra ngoài worktree**

```powershell
$src = "D:\LTTSTUDIOSAPP\.claude\worktrees\ltt-llm-dual-model-4dfcf4"
$dst = "D:\LTTSTUDIOSAPP\docs\ltt_llm_dual\artifacts\serving_v2_luu_tru"
New-Item -ItemType Directory -Force $dst | Out-Null
Get-ChildItem $src -Recurse -Filter "s1_C1_*.jsonl" | Copy-Item -Destination $dst
Get-ChildItem $dst | Measure-Object | Select-Object Count   # kỳ vọng 5
```

- [ ] **Step 2: Huỷ phép gộp dở trong worktree p2-token** — chỉ sau khi chủ dự án xác nhận phiên kia không chạy tiếp.

```powershell
git -C "D:\LTTSTUDIOSAPP\.claude\worktrees\llm-v2-p2-token" merge --abort
git -C "D:\LTTSTUDIOSAPP\.claude\worktrees\llm-v2-p2-token" status --short   # kỳ vọng: sạch
```

- [ ] **Step 3: Đổi tên bản "gốc" lỗi thời trên máy B** để không ai khôi phục nhầm (bản này thiếu `--cache-ram`, `--ctx-checkpoints`, `-b 512`).

```powershell
ssh -i $env:USERPROFILE\.ssh\nexus_b lengo@192.168.2.66 "powershell -NoProfile -Command \"if (Test-Path H:\LTT_LLM\gateway\llama-swap.yaml.goc_s1) { Rename-Item H:\LTT_LLM\gateway\llama-swap.yaml.goc_s1 llama-swap.yaml.LOI_THOI_17-09_khong-dung-de-khoi-phuc }\""
```

- [ ] **Step 4: Commit dữ liệu lưu trữ**

```bash
git add docs/ltt_llm_dual/artifacts/serving_v2_luu_tru/
git commit -m "docs(ltt-llm): luu tru du lieu tho C1 cua phien Serving v2 truoc khi dong nhanh"
```

---

### Task 1: R-04 — `/messages` có cache không còn tính token mới bằng 0 (ưu tiên 1, lỗi tiền đang sống)

**Files:**
- Modify: `platform_core/llm/dem_token_luong.py` (hàm nhận khối usage, quanh dòng 150–180)
- Test: `tests/test_1410_usage_theo_giao_thuc.py` (mới, lấy từ e0bd36b9), `tests/test_271_dem_token_luong.py`

**Interfaces:**
- Produces: `DemToken.su_dung() -> SuDung` với bất biến `token_vao` = tổng prompt (gồm cache) cho **mọi** giao thức, `token_vao_cache <= token_vao`.

- [ ] **Step 1: Cherry-pick commit gốc (sạch trên main hiện tại)**

```bash
git worktree add D:\LTTSTUDIOSAPP-r04 -b phien/llm-r04 main
cd D:\LTTSTUDIOSAPP-r04
git cherry-pick e0bd36b9
```
Nếu xung đột: dừng, viết lại tay đúng khối dưới (không ép).

- [ ] **Step 2: Chạy test mới — phải xanh; đối chứng: đảo sửa thì phải đỏ**

```bash
python -m pytest tests/test_1410_usage_theo_giao_thuc.py tests/test_271_dem_token_luong.py -q
```
Đối chứng: tạm đảo khối `if la_anthropic and ten == "input_tokens": gt += cache_a` → `test_1410` phải đỏ ở ca Anthropic (input 4 + cache 8.826 ⇒ `token_vao_moi` 4, không phải 0); khôi phục.

- [ ] **Step 3: Thêm ca hồi quy tiền** — trong `tests/test_1410_usage_theo_giao_thuc.py`:

```python
def test_messages_cache_hit_van_tinh_token_moi():
    from platform_core.llm.dem_token_luong import DemToken
    d = DemToken()
    d._gop({"input_tokens": 38, "cache_read_input_tokens": 9844, "output_tokens": 120})
    su = d.su_dung()
    assert su.token_vao == 38 + 9844
    assert su.token_vao_cache == 9844
    assert su.token_vao - su.token_vao_cache == 38      # 38 token mới vẫn bị tính tiền
```
(`DemToken._gop(u: dict)` là chỗ gộp một khối usage — `dem_token_luong.py:140`; đường thật đi qua `nhin(khoi: bytes)` → `_mot_dong` → `_quet` → `_gop`. Thêm một ca qua `nhin(b'data: {...}\n\n')` với cùng số để chắc đường thật cũng đúng.)

- [ ] **Step 4: Test nhắm thành phần + ruff/mypy**

```bash
python tools/thanh_phan.py --test core:provider   # lấy danh sách tệp, chạy -n 6
python -m ruff check platform_core/llm/dem_token_luong.py
```

- [ ] **Step 5: Commit, L2 `core:provider`, gộp main, deploy** (theo Global Constraints). Sau deploy: một lượt `/v1/messages` có cache bằng khoá thử, đối chiếu bút toán credit ≥ giá token mới.

---

### Task 2: Giữ chỗ ảnh theo kích thước thật (R-19)

**Files:**
- Create: `platform_core/llm/anh_token.py`
- Modify: `apps/ltt_llm/ngan_sach.py` (`luat_cho`), `platform_core/runtime_noi_bo/luong.py` (`_dat_cho` dòng ~290, các lời gọi dòng ~378, ~588, ~994)
- Test: `tests/test_12xx_anh_token_that.py` (số lấy theo `tools/check_so_test.py`)

**Interfaces:**
- Produces: `anh_token.dem_token_anh(than: dict) -> int` — tổng token ảnh theo kích thước đọc được; ảnh không đọc được kích thước tính `HO_SO[m].token_giu_moi_anh`.
- `luat_cho(suc: AdmissionModel, *, token_vao_uoc: int, xin_ra: int, token_anh: int, …)` — **thay** `so_anh`.

- [ ] **Step 1: Tra nguồn trước** — công thức token ảnh của mmproj Qwen3.5/3.8 (patch size, merge, giới hạn pixel mặc định trong llama.cpp mtmd) qua GitHub MCP (`search_code` repo ggml-org/llama.cpp "mtmd" "n_tokens"); ghi nguồn vào docstring. Đối chiếu số đo của nhánh cũ: 1920×1080 = 2.040; 2560×1440 = 3.600; 4032×3024 ≈ 11.970.

- [ ] **Step 2: Test đỏ**

```python
import pytest
from platform_core.llm.anh_token import token_theo_kich_thuoc

@pytest.mark.parametrize("w,h,ky_vong", [(1920, 1080, 2040), (2560, 1440, 3600)])
def test_token_theo_kich_thuoc_khop_so_do(w, h, ky_vong):
    assert token_theo_kich_thuoc(w, h) == ky_vong

def test_anh_to_vuot_bien_duoc_giu_du():
    assert token_theo_kich_thuoc(4032, 3024) > 8192
```

- [ ] **Step 3: Cài `anh_token.py`** theo công thức đã tra (Step 1), đọc kích thước từ header ảnh base64 (PNG/JPEG/WebP) bằng Pillow `Image.open(...).size` không giải mã toàn ảnh.

- [ ] **Step 4: Đổi `luat_cho`/`_dat_cho`** nhận `token_anh`; xoá tham số `so_anh`; `HO_SO.token_giu_moi_anh` chỉ còn là giá trị lùi. Grep bảo đảm không còn `so_anh=` ở mọi cửa (stream, sync, job, planner).

- [ ] **Step 5: Máy B** — khi thiếu `X-LTT-Token-Dat`, `llm_gateway/vat_ly.py` dùng cùng hàm đếm (import chung hoặc bản sao có test đối chiếu byte-for-byte như `test_1223` đã làm cho ước chữ).

- [ ] **Step 6: Test nhắm `core:provider`, `app:ltt_llm`, `gateway:llm`; commit; L2 từng thành phần; deploy A trước, B sau** (tăng giữ chỗ = giảm sức chứa ⇒ A trước theo RUNBOOK §2.1).

---

### Task 3: Cận trên ước lượng + đếm thật khi sát biên (R-21 / R-2)

**Files:**
- Modify: nơi ước token hiện tại (tìm: `grep -rn "KY_TU_MOI_TOKEN" platform_core apps llm_gateway`), `llm_gateway/ngan_sach.py:355` (nhánh đếm thật)
- Test: mở rộng `tests/test_1229_phuong_an_c_hop_dong.py`

**Interfaces:**
- Produces: `uoc_can_tren(van_ban: str) -> int` dùng hệ số theo lớp ký tự (Latin, CJK, emoji, hex) lấy từ 13 mẫu × 2 model của 9cc80640; `token_vao_uoc` ở A = `uoc_can_tren`.
- B: đếm thật khi `uoc >= tran - bien_pool_token` (không chỉ khi vượt trần).

- [ ] **Step 1: Test đỏ từ 13 mẫu đo** (lấy bảng mẫu trong 9cc80640, đưa vào `tests/fixtures/uoc_token_mau.json`): với mọi mẫu `uoc_can_tren(x) >= that(x)`.
- [ ] **Step 2: Test đỏ thứ hai — không ước quá tay cho Latin:** `uoc_can_tren(latin) <= 1,3 × that(latin)` (nghiệm thu 17/09 ghi A đang ước gấp ~2 lần chữ Latin — sửa luôn chiều này).
- [ ] **Step 3: Cài hệ số; nối vào `_dat_cho`; nhánh B đếm thật khi sát biên.**
- [ ] **Step 4: Test nhắm ba thành phần; commit; L2; deploy B trước rồi A** (B đếm thật là chặn an toàn).

---

### Task 4: Lỗi tràn đúng định dạng từng giao thức + `response.in_progress`

**Files:** `server/api/streaming.py`, bộ dịch lỗi (tìm: `grep -rn "413" server/api/streaming.py platform_core/public_api`); test mới.

- [ ] **Step 1: Test đỏ** — gửi thân vượt `tran_vao_cua` qua ba cửa: `/v1/messages` phải trả khối `{"type":"error","error":{"type":"invalid_request_error","message":"prompt is too long…"}}` (câu Claude Code nhận để tự nén); `/v1/responses` trả `response.failed` đúng schema; `/v1/chat/completions` trả `context_length_exceeded`.
- [ ] **Step 2: Test đỏ** — luồng `/v1/responses` chờ hàng đợi > 15 s phát `response.in_progress` (không chỉ comment SSE).
- [ ] **Step 3: Viết lại từ ý tưởng f0fad274 trên `streaming.py` hiện tại** (không cherry-pick: tệp đã đổi).
- [ ] **Step 4: Kiểm với client thật:** Claude Code (`claude -p` qua cấu hình LTT) và Codex CLI — thân quá lớn phải dẫn tới tự nén, không kẹt.
- [ ] **Step 5: Commit; L2 `server:api`; deploy A.**

---

### Task 5: Gỡ trường ghi đè ngân sách suy nghĩ (R-22)

- [ ] **Step 1: Test đỏ** — request mang `thinking.budget_tokens`, `reasoning_budget`, `chat_template_kwargs.reasoning_budget` (liệt kê đủ theo 026f52dd) thì thân gửi lên B **không** còn các trường đó; hồ sơ model quyết định.
- [ ] **Step 2: Viết lại trên nơi dựng thân request hiện tại** (tìm: `grep -rn "chat_template_kwargs" platform_core`).
- [ ] **Step 3: Test nhắm; commit; L2; deploy A.**

---

### Task 6: Ngưỡng nén cho người dùng Claude Code (R-05)

- [ ] **Step 1: Đo thật** công thức Claude Code: với `CLAUDE_CODE_AUTO_COMPACT_WINDOW` hiện tại (138.690), điểm nén thực tế là bao nhiêu (log `/context` hoặc số token lúc nén) trên một client thật.
- [ ] **Step 2: Test đỏ** — `sdk/ltt_cai_dat_cli.py` sinh cửa sổ sao cho điểm nén thực = `tran_vao_cua(m) − max_out_client − DEM_UOC` (đọc từ `ngan_sach`, không gõ số).
- [ ] **Step 3: Sửa; cập nhật `CLAUDE_CONFIG_MATRIX.md`; kiểm lại với client thật; commit; L2; deploy.**

---

### Task 7: Công cụ kiểm định kỳ trên cấu hình hiện tại

- [ ] **Step 1: Cherry-pick** `0bb171ca` (canary cô lập `kiem_co_lap_llm.py` + test_1407), `a538a12b` (ghim `/slots`), `467832cd` (bộ chấm A/B), `fb492568` (`cong_mtp.py`) — từng cái, dừng khi xung đột.
- [ ] **Step 2: Chạy canary cô lập 200 lượt mỗi model trên production hiện tại** (cache 24G sau L-25, `--ctx-checkpoints 8`, `-b 512` ở 3.8) giờ vắng khách, khoá thử, ≤ 600 credit. Đạt: 0 rò rỉ.
- [ ] **Step 3: Chạy `cong_mtp.py` một lượt** làm phép kiểm đúng/sai của MTP với `-np 3`; ghi kết quả; **không** đổi cờ MTP.
- [ ] **Step 4: Ghi vào RUNBOOK** lịch chạy định kỳ (sau mỗi lần nâng llama.cpp).

---

### Task 8: Thang năng lực R-09 vs Q131 — CHỜ CHỦ DỰ ÁN

Không làm cho tới khi có quyết định: giữ Q131 (3.5 mặc định suy nghĩ `medium`) hay chuyển R-09 (3.5 `always_on`, bỏ qua effort). Đề xuất: giữ Q131 (đang sống, đã nghiệm thu), chỉ lấy phần catalog Codex của 7d443461 nếu còn thiếu.

---

## Thứ tự và song song

```
Task 0 (dọn) ─┬─ Task 1 (R-04, tiền)  ──► deploy A   [làm NGAY]
              ├─ Task 5 (R-22)        ──► deploy A
              ├─ Task 7 Step 1 (cherry-pick công cụ)
              └─ Task 2 (ảnh) ─► Task 3 (ước cận trên) ─► deploy A/B theo thứ tự đã ghi
Task 4 (lỗi theo giao thức) sau Task 3 (cùng đường 413)
Task 6 sau Task 3 (dùng tran_vao_cua mới)
Task 7 Step 2–3 sau khi L-25 (cache 24G) đã deploy
Task 8 chờ quyết định
```

Ước thời gian: Task 0 · 20 phút; T1 · 1 giờ; T5 · 1 giờ; T2 · 3 giờ; T3 · 3 giờ; T4 · 3 giờ; T6 · 2 giờ; T7 · 2 giờ. Tổng ~15 giờ công, song song còn ~7–8 giờ.

## Nghiệm thu chung (mỗi task)

1. Test đỏ trước, xanh sau, có đối chứng.
2. Không tên nào trong danh sách "đã gỡ" quay lại (`grep` trong diff).
3. L1/L2 xanh trên đúng SHA deploy; `nghiem_thu_deploy.py` khớp tuyệt đối; đo sau deploy bằng khoá thử.
4. DECISION_LOG mục mới (L-26…), RUNBOOK và BAN_DO_DUONG_DI cập nhật cùng commit.

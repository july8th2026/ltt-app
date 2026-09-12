# LTT LLM Dual-Model — Spec 1: Runtime hai model

> **Trạng thái:** CHỜ CHỦ DỰ ÁN DUYỆT (viết 2026-09-11).
> **Nhánh viết:** `claude/ltt-llm-recovery-multimodel-110f65` @ `9e73bf1f`. **Nền triển khai:** trunk `admin-mvp-v3` (TD-D1).
> **Quyết định:** `docs/ltt_llm_dual/DECISION_LOG.md` (D01–D08, L-1…L-12, TD-D1…TD-D11) — spec này **không** tự
> đổi quyết định nào; chỗ nào spec phải chọn một chi tiết mà quyết định chưa nói, nó ghi **[CHI TIẾT SPEC]** để
> chủ dự án duyệt cùng.
> **Bằng chứng:** `docs/ltt_llm_dual/00`–`06`. Di sản Multi-Job: `01_MULTI_JOB_INHERITANCE.md`.
> **Spec 2** (Input Intelligence MVP — tệp, đa tệp) có chu trình riêng (D05). Spec này chỉ phủ **text + nhiều ảnh**.
> Mọi con số dưới đây là **tham số khởi đầu**; nguồn chân lý khi code là `apps/ltt_llm/ngan_sach.py` và cấu hình,
> không phải tài liệu này.

---

## 0. ĐÍNH CHÍNH SAU KHI ĐO (2026-09-12) — đọc trước mọi con số bên dưới

Spec này viết **trước** khi có phép đo trên card thật. Cổng G1 (Task 3.2,
`docs/ltt_llm_dual/10_BENCHMARK_P3.md`) đã đo, và ba chỗ dưới đây **hết đúng**.
Chủ dự án đã quyết lại — xem **L-14** trong `DECISION_LOG.md`.

| Spec viết | Đo được / chốt lại |
|---|---|
| LTT-3.8: ngữ cảnh engine **262.144** | **221.184** — 262.144 × 4 slot tràn ~400 MiB sang RAM chủ, kể cả khi bỏ mmproj khỏi GPU |
| LTT-3.8: **C4** (`-np 4`, 4 slot) | **C3** (`-np 3`) — chủ dự án bỏ mục tiêu C4 cho model này |
| `pool` LTT-3.8 = 262.144 | `POOL_38` = **221.184** |

Cụ thể: `-c 221184 -np 3`, mmproj **trên GPU**, `-ub` mặc định ⇒ VRAM 24.131 MiB,
`Shared Usage` 568 (trong dải sàn, **không tràn**), biên **445 MiB**.

**Ba hệ quả cho phần còn lại của spec:**

1. Mọi chỗ viết **"C4"** cho LTT-3.8 (mục 1, §11 bảng `pool`, nghiệm thu **D**, **F**,
   **H**) đọc lại là **C3**. Ngưỡng của cổng D (`tổng ≥ 100 tok/s`) phải tính lại theo
   3 luồng, không phải 4 — số cụ thể chốt khi chạy kịch bản `c4` (nay là `c3`).
2. **LTT-3.5 chưa bị đính chính:** nó nằm trên card 16 GB khác hẳn, và cổng **G3** mới
   đo. Con số 262.144 của nó trong bảng §2 vẫn là **đích chưa kiểm**, không phải số đo.
3. **Ràng buộc cứng mới cho P5:** biên 445 MiB là biên lúc ComfyUI **chưa** nạp ngữ cảnh
   CUDA. ComfyUI ấm giữ 223,5 MiB và `/free` không nhả ⇒ trọng tài residency phải **dừng
   hẳn dịch vụ LTTComfyUI** trong cửa sổ LLM. Đây không còn là tối ưu tùy chọn.

⚠️ Đính chính này **không** đổi quyết định kiến trúc nào (D01–D09 giữ nguyên): nó chỉ
thay những con số spec tự nhận là *"tham số khởi đầu"* bằng con số đo được, đúng như
dòng cuối của khối trạng thái ở đầu tệp đã dặn.

---

## 1. Mục tiêu, phi mục tiêu

**Mục tiêu.** Hai model nhà, khách chọn tường minh, mỗi model một GPU của máy B, cùng một hợp đồng đầu vào (text +
nhiều ảnh), mỗi model C4 thật với admission theo slot **và** ngân sách KV, hủy thật, tiền đúng, không lượt nào bị
giết để đổi residency, RTX 3090 chia có trật tự giữa LTT-3.8 và model ảnh.

**Phi mục tiêu.** Model thứ ba · auto-router · fallback 3.8→3.5 · tensor-parallel 3090+5060 · vLLM/SGLang · vá C++
llama.cpp · 500K/1M/YaRN · tệp/đa tệp/video (Spec 2) · khung N-GPU tổng quát · canary theo phần trăm (D08).

## 2. Hợp đồng công khai (D02)

| | LTT-3.8 | LTT-3.5 |
|---|---|---|
| ID API (chấp nhận **đúng** chuỗi này) | `ltt-3.8` | `ltt-3.5` |
| Tên hiển thị | LTT-3.8 | LTT-3.5 |
| Id nội bộ (máy B, không rời máy A — INV-015) | `qwen38-api` (giữ tên, nay là hồ sơ gộp text+vision) | `qwen35-api` (mới) |
| Model | Qwen3.8-27B `UD-Q4_K_M` + mmproj F16 | Qwen3.5-9B `Q6_K` + mmproj F16 |
| GPU (UUID) | 3090 `GPU-26623278-4fa5-82db-4306-237651b03e78` | 5060 Ti `GPU-ebecd0a4-a8a7-14a5-dad1-21565f6dc1df` |
| Ngữ cảnh engine | **221.184** (đo 12/09, L-14 — xem §0) | 262.144 (D06, **chưa đo**, cổng G3) |
| Đầu vào | text + ≤ 4 ảnh | text + ≤ 4 ảnh |
| Giá (credit/1M: vào / cache / ra) | 50 / 10 / 400 (`ltt-vlm-2026-08-22`, giữ) | ≈ 13 / 3 / 20 (`ltt-3.5-<ngày chốt>`, D07) |

- `ltt_llm`, `ltt_llm_vision`, `qwen38-vision` và mọi biến thể ⇒ `model_not_found`. Không bảng bí danh ẩn.
- Mọi danh mục (`/v1/models`, `/tools`, bộ chọn ChatLTT) tiếp tục **dẫn xuất từ manifest** `apps/ltt_llm/manifest.py`.
- Tool công khai giữ `text.chat`, job `ltt_llm.chat`; model chọn bằng tham số `model`.
- Trần vào/ra/công bố cho client dẫn xuất **theo model** từ cùng công thức hiện có (`ngan_sach.py`:
  `TOKEN_VAO_TRAN = CUA_SO − TOKEN_RA_TRAN − LE`, `CONG_BO_CHO_CLIENT = 0,92 × …`) qua `CUA_SO_THEO_MODEL`.
- Route Claude Desktop `ltt-llm-claude-compat` trỏ `ltt-3.8`.
- **Việc LLM nội bộ (D09):** điểm nối trên trunk là `platform_core/llm/canonical.py`. Bảng `ALIAS_SANG_ID` đổi sang
  `{"ltt-3.8": "qwen38-api", "ltt-3.5": "qwen35-api"}`; `MODEL_MAC_DINH` bị thay bằng **khai báo từng app** (trường hợp
  đồng app mới, mặc định `ltt-3.5`); `tai_nguyen_nha()` trả resource **theo model** (`ltt_38_3090` / `ltt_35_5060`).
  Người gọi: `image_gen/dich_llm.py` (từ job của `anhnoibo`, `taoanh`, `thumbnail`), `taovideo/translate`,
  `autosubvideo/ai_workflows.py`, `prompt_ai_ommi`, `agent/planner.py`. Phép kiểm: đường dịch prompt ảnh không bao giờ
  trỏ `ltt-3.8` (vòng chờ với cửa sổ ảnh).

## 3. Hướng tiếp cận đã cân nhắc

**3.1 Admission theo model.**
(a) **Một tool + ánh xạ admission theo model trong `ToolSpec`** — *chọn*. (b) Hai tool `text.chat` / `text.chat.fast`
— đổi bề mặt `/tools` và job type, nhân đôi mọi chỗ gọi. (c) Để gateway máy B tự chia pool — trái TD-D10 (quyền quyết
nghiệp vụ phải ở máy A).
⇒ Bổ sung **hợp đồng app** (đúng luật CLAUDE.md "thiếu hợp đồng thì bổ sung hợp đồng"): `ToolSpec.admission_theo_model:
Mapping[str, AdmissionModel]` với `AdmissionModel(resource, slots, token_pool, residency_group="", vai_tro="")` và
resolver `admission_cho(tool, model)`. Trường cũ `admission_resource/slots/token_pool` giữ cho tool khác (không đổi hành vi).

**3.2 Trọng tài residency 3090 (D01 B).**
(a) **Máy trạng thái ở admission plane máy A**, gateway máy B chỉ thực thi — *chọn* (TD-D10: chỉ máy A thấy cùng lúc
lease LLM, phòng chờ, hàng job ảnh). (b) llama-swap `matrix` + ComfyUI làm "model" `comfyui_auto` — community, drain
khi swap, **nhưng** ComfyUI nhận prompt bất đồng bộ (HTTP trả ngay, việc chạy tiếp) ⇒ llama-swap đếm in-flight sai và
có thể đuổi ComfyUI giữa lượt vẽ; không biết trần chờ nghiệp vụ. (c) Trọng tài cục bộ trong gateway máy B — không thấy
phòng chờ/hàng job ở máy A.

**3.3 Hai model cùng nạp.** llama-swap v250 `groups` `swap:false` + `env` UUID + `hooks.on_startup.preload` (TD-D2) —
không tự viết quản lý tiến trình.

## 4. Kiến trúc

```
MÁY A (quyền quyết nghiệp vụ duy nhất)
 cửa: ChatLTT stream · /messages /responses (stream + không stream) · /chat/completions · POST /jobs · planner
   │  model = ltt-3.8 | ltt-3.5  → admission_cho(tool, model)
   ▼
 ADMISSION PLANE (CSDL, liên tiến trình)
   resource ltt_38_3090 (4 slot, pool 262.144)   resource ltt_35_5060 (4 slot, pool 262.144)
   resource anh_3090 (1 slot)  ─┐
   sổ ExecutionLease + phòng chờ llm_waiters + luat_nhan.xet() (thuần)  │
   TRỌNG TÀI RESIDENCY nhóm "rtx3090" = {ltt_38_3090 (mac_dinh), anh_3090 (theo_lo)} ◄┘
   │ nhận ⇒ giữ tiền ⇒ gọi (X-LTT-Request-Id)
   ▼
MÁY B (thực thi + chốt fail-closed, KHÔNG xếp hàng nghiệp vụ)
 llm_gateway :8299 — sổ slot + token + whale THEO MODEL; lệnh residency 3090 (nhả/nạp qwen38-api)
 render_gateway :8199 — vẽ; lệnh nhả ComfyUI (/free) theo trọng tài; không còn tự đuổi Qwen
 llama-swap :8280 — group swap:false {qwen38-api, qwen35-api}, preload cả hai
   qwen38-api  llama-server -np 4 -kvu -c 262144 --mmproj … draft-mtp   CUDA_VISIBLE_DEVICES=<UUID 3090>
   qwen35-api  llama-server -np 4 -kvu -c 262144 --mmproj …  (không MTP) CUDA_VISIBLE_DEVICES=<UUID 5060 Ti>
 ComfyUI :8188 — CUDA_VISIBLE_DEVICES=<UUID 3090>
 Desktop Windows + mọi tác vụ nền → 5060 Ti (L-12)
```

Ba tầng không lẫn nhau: **nghiệp vụ** (lớp, tài khoản, công bằng, tiền, chờ, residency) ở máy A; **an toàn** (sức chứa
token thật, VRAM theo UUID) ở gateway; **thực thi** (slot, batching, KV) ở engine. Không hàng đợi ẩn ở gateway (Multi-Job
D-07-2); llama-swap `concurrencyLimit` đặt ≥ 2×slot để nó **không** thành hàng đợi thứ hai.

## 5. Đường đi của từng model

**LTT-3.5.** `model=ltt-3.5` → `admission_cho` ⇒ `ltt_35_5060` → luật nhận (§8) → giữ tiền giá 3.5 → gateway sổ `qwen35-api`
→ llama-swap `qwen35-api` (5060 Ti) → quyết toán theo `usage` đo. **Luôn nóng**: preload lúc llama-swap khởi động,
`ttl: 0`; không trọng tài (5060 Ti không có model AI nào khác — L-11/L-12).

**LTT-3.8.** `model=ltt-3.8` → `ltt_38_3090` → luật nhận + **điều kiện residency** (nhóm `rtx3090` phải ở trạng thái `LLM`)
→ giữ tiền giá 3.8 → gateway sổ `qwen38-api` → llama-swap `qwen38-api` (3090) → quyết toán. Nóng mặc định; chỉ nhả trong
cửa sổ ảnh do trọng tài mở (§12).

Không lượt nào được chuyển model: yêu cầu `ltt-3.8` khi 3090 đang vẽ ⇒ **chờ** (stream/sync theo §6) hoặc 429/503 — không
bao giờ âm thầm chạy trên `ltt-3.5` (L-2).

## 6. Vòng đời theo cửa

Chung cho mọi cửa: kiểm `model` (đúng hai ID) → kiểm tham số + ảnh → ước token (`executor.estimate_input`, theo model)
→ **413 trước mọi thứ khác** nếu vượt trần vào của model → kiểm số dư đủ (**409 `insufficient_credit`** — mã thật của nền tảng, `public_api/errors.py`; bản đầu của spec ghi 402, sai; không giữ tiền) → admission theo cửa → giữ
tiền **sau khi được nhận** → gọi máy B → quyết toán theo `usage` đo → nhả lease (`finally` + BackgroundTask).

| Cửa | Khi hết chỗ / đang chờ residency | Nguồn |
|---|---|---|
| **Stream** (`/messages`, `/responses`, ChatLTT) | 200 + SSE ngay; chờ trong phòng chờ, nhịp tim `: ltt-cho` 15 s, mã lý do; hết trần ⇒ sự kiện lỗi đúng khuôn (Anthropic `event: error overloaded_error`, OpenAI Responses `response.failed`, ChatLTT `response.failed code="ban"`) | Multi-Job D-06 (KEEP) |
| **Đồng bộ** (`/chat/completions`, `_mot_cuc`) | `idempotency.begin` → **commit "đang xử lý" (nhả khoá)** → chờ phòng chờ ≤ `min(60 s, ngân sách thời gian cửa)` → nhận ⇒ giữ tiền ⇒ gọi; hết giờ ⇒ 429 + `Retry-After` (ước tới lúc cửa sổ ảnh đóng nếu lý do là residency), đóng bản ghi, 0 khoản giữ | D04 B |
| **Job** (`POST /jobs`, job app) | hàng `jobs` bền (Scheduler V1 xếp giữa các job) → worker claim → `hold_persisted` lớp `nen` + đặt chỗ token (`luat_cho`) → không nhận ⇒ `_tra_ve_hang_doi` (không tính attempt) | Multi-Job T9 WIP (KEEP) + TD-D11 |
| **Planner** (nội bộ) | lớp `noi_bo`, thử **một lần**, không chờ, không lấy slot chừa; hết chỗ ⇒ `PlannerError`. ⚠️ **Đính chính 2026-09-11 (Task 1.5):** bản đầu ghi "rơi sang Gemini như F-06" — cascade đó **đã bị gỡ 08/09** (`platform_core/agent/planner.py:18-20`; `canonical.THU_TU_PROVIDER = ("ltt_llm",)`). Mã sống là nguồn chân lý. | Multi-Job D-03 |

**Gateway máy B từ chối** (sổ token/slot của nó, VRAM theo UUID) khi máy A đã nhận ⇒ máy A coi là **bận**: nhả lease, đưa
lượt về phòng chờ (tối đa `SO_LAN_QUAY_LAI`), không đánh dấu khoá hỏng (INV-004/013).

## 7. Mô hình dữ liệu

Tái dùng Multi-Job T3 (**rebase lên trunk**, migration nối vào head `20260910_1000_job_scheduler_envelope`):
`ExecutionLease` + `lop`, `token_dat_truoc`, `token_prefill_moi`, `la_whale`; bảng `llm_waiters` (phòng chờ + sổ lượt,
OPERATIONAL 30 ngày). **Thêm:**

- `llm_waiters.model` (id công khai phục vụ) và `llm_waiters.cho_residency_s` (tách thời gian chờ residency khỏi chờ slot).
- Bảng **`gpu_residency`** (một dòng mỗi nhóm): `nhom` (UNIQUE), `trang_thai`, `thanh_vien_dang_giu`, `tu_luc`,
  `so_anh_trong_cua_so`, `cua_so_bat_dau`, `lan_nap_loi`, `phien_ban` (khoá lạc quan). Đủ ba nghĩa vụ của bảng mới
  (memory "bảng mới 3 nghĩa vụ"): `Store` trong `public_api/governance.py`, hàm dọn (không cần — một dòng/nhóm, ghi đè),
  tên UNIQUE vào `tools/restore_drill_schema.py`.

## 8. Admission — một hàm cho hai pool

`luat_nhan.xet(yc, dang_giu, dang_cho, ThamSo)` giữ nguyên (T4); `admission.xet_va_giu()` giữ nguyên (T5) — advisory lock
theo `resource` ⇒ hai pool là **hai khoá độc lập**, tải 3.8 không bao giờ lấy suất/ngân sách 3.5 và ngược lại (L-7).
Thay đổi duy nhất: `ThamSo` lấy theo `AdmissionModel` của model được yêu cầu, và thêm một luật **trước** luật 1:

0. `residency_group` khác rỗng ⇒ nhóm phải đang giữ thành viên này và ở trạng thái mở (`LLM` cho `ltt_38_3090`,
   `ANH` cho `anh_3090`); không thì từ chối lý do **`CHO_RESIDENCY`** (mã ổn định, vào sổ lượt).

Tham số khởi đầu **theo model** (cấu hình trong `ngan_sach.py`, `platform_core` không import app — đi qua `ToolSpec`):

| Tham số | LTT-3.8 | LTT-3.5 | Căn cứ |
|---|---:|---:|---|
| `so_slot` | 4 | 4 | L-3 |
| `pool` (token) | **221.184** (L-14) | 262.144 (chưa đo) | D03, D06, §0 |
| Slot tối đa lớp `nen` | N−1 = 3 | 3 | D-03 |
| Trần tài khoản khi có người chờ | 2 | 2 | TD-8 |
| `NGUONG_WHALE` (token prefill mới) | 16.384 | [CHI TIẾT SPEC] đo ở P3 — khởi đầu 32.768 (9B prefill nhanh hơn) | TD-6 |
| `CHO_WHALE_TOI_DA` | 30 s | 30 s | D-05 |
| Đệm đặt chỗ | `n_batch` 2.048 | 2.048 | patch 0011 |
| `token_moi_anh` | đo P3 | đo P3 | mmproj khác nhau |

Đặt chỗ = `prompt_ước (dư) + max_tokens_hiệu_lực + đệm + ảnh × token_moi_anh`, **một** phép tính (`tham_so_da_luot.luat_cho`,
T9 WIP — KEEP). Kẹp về `pool`. Ước sai ⇒ engine hoãn ẩn ⇒ `requests_deferred > 0` ⇒ báo động (§15).
`--kv-unified-per-slot` **không** dùng: nó chặn một lượt dài dùng trọn 262.144 (trái mục tiêu ngữ cảnh dài); sổ ngân sách
của LTT là thứ ngăn đường "giết mọi slot" (TD-D3).

## 9. Chủ hàng đợi

Máy A là quyền duy nhất về: ưu tiên (D-03 × Scheduler V1, TD-D11), công bằng, tiền, hủy, backpressure, residency.
Hàng bền: `jobs` (job) + `llm_waiters` (lượt tương tác đang chờ). Gateway: chốt fail-closed, trả 429 nhanh, không giữ
request thứ hai. llama-swap: `concurrencyLimit` ≥ 8 mỗi model. llama-server: `-np 4` — hoãn ở engine chỉ xảy ra khi có
lỗi ước ⇒ báo động.

## 10. Danh tính GPU

Nguồn duy nhất: `llm_gateway/deploy/gpu_may_b.json` [CHI TIẾT SPEC] — `{vai: "ltt38"|"ltt35", uuid, pci_bus_id, ten,
vram_mib}` cho hai card. `llama-swap.yaml` (env mỗi hồ sơ), dịch vụ ComfyUI, và mọi bộ đọc VRAM/util đều **dẫn xuất
hoặc được test đối chiếu** với tệp này (khuôn `test_334`). Gateway khởi động: `nvidia-smi --query-gpu=uuid,pci.bus_id`
phải thấy đúng hai UUID; thiếu ⇒ `/health/ready` 503 (fail-closed).
Mọi phép đo trên máy B chuyển sang `nvidia-smi --id=<UUID> …` — sửa 11 chỗ ở `03_GPU_RESOURCE_MAP.md` §1 (a–m); các bộ
đọc "max mọi card", "dòng 0", `--query-compute-apps` không lọc đều bị thay.

## 11. Cách ly GPU

| Card | Được phép | Cơ chế |
|---|---|---|
| 3090 | `qwen38-api`, ComfyUI (model ảnh) — **chỉ model AI** | `CUDA_VISIBLE_DEVICES=<UUID 3090>` ở hồ sơ llama + env dịch vụ `LTTComfyUI` |
| 5060 Ti | `qwen35-api`, màn hình, desktop, tác vụ nền | `CUDA_VISIBLE_DEVICES=<UUID 5060>` ở hồ sơ llama |

**Dọn VRAM nền khỏi 3090 (L-12) — Pha 0, runbook vận hành:** hôm nay 11 tiến trình đồ hoạ desktop mở ngữ cảnh trên 3090
(`00` §3). Cách làm dự kiến: đặt 5060 Ti là GPU ưu tiên của Windows (Settings → Display → Graphics / chính sách GPU
mặc định) cho phiên người dùng, rồi khởi động lại phiên; kiểm lại bằng `nvidia-smi --query-compute-apps` lọc UUID 3090 ⇒
chỉ còn llama-server/ComfyUI. ⚠️ Đây là **thay đổi cài đặt hệ thống** — chủ dự án tự làm hoặc cho phép tường minh; spec
chỉ định nghĩa **phép kiểm** (0 tiến trình ngoài danh sách cho phép trên UUID 3090).

## 12. Residency 3090 — trọng tài duy nhất (D01 B)

Hai trọng tài cũ bị **gỡ**: `render_gateway/nhuong_card.py` (`xin_card` đuổi Qwen bằng `GET /unload` — lệnh này giết lượt
đang chạy), `TraCard`, và `llm_gateway/don_dep.py` (`/free` ComfyUI trước khi nạp) cùng nhánh ComfyUI/util của
`trong_tai.py`. `LTT_HO_DUNG_CARD`, `LTT_TRA_CARD_GIAY` bị bỏ khỏi `C:\ProgramData\LTTRender\gateway.env`.

Máy trạng thái nhóm `rtx3090` (dòng `gpu_residency`), bước bằng một hàm `residency.buoc(db)` gọi từ vòng bảo trì của worker
máy A mỗi ~2 s và khi có sự kiện (nhả lease, job ảnh vào hàng), trong advisory lock `residency:rtx3090`:

```
 LLM ──(có job anh_3090 đang xếp)──► XA_LLM ──(0 lease ltt_38_3090 VÀ gateway báo 0 in-flight)──► NHA_LLM
  ▲                                     (admission ltt_38 đóng: CHO_RESIDENCY;                       │ POST gateway /v1/residency/nha
  │                                      lượt đang chạy chạy tới hết — L-9)                          │ (gateway: llama-swap unload qwen38-api
  │                                                                                                  │  CHỈ khi in-flight=0; kiểm VRAM UUID giảm)
 NAP_LLM ◄──(ComfyUI /free xong, VRAM 3090 ≤ VRAM_SACH)── TRA_ANH ◄──(điều kiện đóng cửa sổ)── ANH ◄┘
  │ POST gateway /v1/residency/nap (nạp qwen38-api + 1 lượt khởi động + /health)                (admission anh_3090 mở, 1 slot)
  └─ ok ⇒ LLM (mở admission ltt_38) · hỏng ⇒ LOI_NAP (thử lại lùi dần, báo động, admission ltt_38 vẫn đóng)
```

**Điều kiện đóng cửa sổ ảnh** (`ANH → TRA_ANH`, không cắt lượt vẽ đang chạy):
- hết job ảnh đang xếp; **hoặc**
- có người chờ LTT-3.8 **và** một trong: đã vẽ `CUA_SO_ANH_TOI_DA` ảnh (4) · đã qua `CUA_SO_ANH_S` (480 s) · **vẽ thêm một
  ảnh nữa sẽ đẩy người chờ LLM lâu nhất quá hạn chót của cửa họ** (`hạn chót − T_NAP_LLM − T_ANH_UOC − 30 s`).

[CHI TIẾT SPEC] Vế cuối là cách spec giải xung đột tham số: một ảnh mất 92–110 s, nên cửa sổ tối đa (4 ảnh ≈ 6–7 phút) dài
hơn trần chờ stream 300 s (D-06). Không đổi quyết định nào: trần của D01 vẫn là **trần trên**; khi có người chờ LLM, cửa sổ
đóng sớm hơn để họ không chết vì hết trần chờ. Không có người chờ LLM ⇒ ảnh chạy tiếp (work-conserving).

**Thời gian chờ tối đa của ảnh** = thời gian drain lượt LLM đang chạy (không giết — L-9). Lượt LLM dài nhất bị chặn bởi
`max_tokens` và timeout hiện có; con số thật ghi vào báo cáo. Với ~38 ảnh/ngày (log 28 ngày), phần lớn cửa sổ là **một ảnh**
⇒ chu kỳ ≈ drain + ~100 s vẽ + nạp lại LTT-3.8.

**Phía máy B** là thực thi fail-closed: `/v1/residency/nha` từ chối nếu sổ gateway còn lượt `qwen38-api`; `/v1/residency/nap`
từ chối nếu VRAM UUID 3090 > `VRAM_SACH` (2.500 MiB, cấu hình). render gateway chỉ gửi prompt khi admission `anh_3090` đã
nhận (máy A giữ lease). Không còn chỗ nào trên máy B tự quyết đuổi ai.

Ba app vẽ trên 3090 qua `platform_core/image_gen/cong_render` (`anhnoibo`, `taoanh`, `thumbnail`) cùng khai
`admission_resource="anh_3090"`, `admission_slots=1`, `residency_group="rtx3090"`, `vai_tro="theo_lo"` (hôm nay cả ba
**không** khai admission); `apps/ltt_llm` khai `ltt_38_3090` với `vai_tro="mac_dinh"`. Nền tảng chỉ biết **vai trò**, không biết
tên app (test_147 layering).

## 13. Kho ấm RAM (224 GB) — TD-D8

- Trọng số: mmap mặc định (`--load-mode auto`); sau khi tiến trình nhả, trang GGUF nằm ở **standby list** Windows. Không
  dùng `--mlock` (chỉ sống theo tiến trình). Không tuyên bố "GPU sleep to RAM".
- `--cache-ram` (cache prompt/KV ở RAM): [CHI TIẾT SPEC] khởi đầu 32.768 MiB cho `qwen38-api`, 16.384 MiB cho `qwen35-api`;
  chốt theo đo, giữ ≥ 48 GB RAM trống cho render (`LTT_RENDER_RAM_TRONG_GB=48`).
- `tests/test_637_nha_ve_ram.py` sửa: chặn `--load-mode none|dio`, `-lm none|dio`, `LLAMA_ARG_LOAD_MODE` (bản cũ chỉ chặn
  cờ đã bị gỡ ở b10875).
- Đo bắt buộc (nghiệm thu K): nạp lạnh (sau khởi động lại hoặc xả standby) vs ấm, cho cả hai model; và standby có sống qua
  một cửa sổ ảnh không (chính là thời gian `NAP_LLM`).

## 14. Engine

**`qwen38-api`** (3090): cờ production hiện có (`--jinja`, template froggeric, `--reasoning-format deepseek`, `-fa 1 -ngl 999`,
`--metrics`, KV q4_0) + `--mmproj mmproj-F16.gguf` + `-np 4 -kvu -c 262144` + `--spec-type draft-mtp --spec-draft-n-max 2`
(qua cổng MTP ở §23.H) + `--cache-ram` + `env CUDA_VISIBLE_DEVICES=<UUID 3090>`, `ttl: 0`, `aliases` rỗng.
Hồ sơ `qwen38-vision` bị xoá (không còn đổi hồ sơ).

**`qwen35-api`** (5060 Ti): `-m Qwen3.5-9B-Q6_K.gguf --mmproj <mmproj 9B> -np 4 -kvu -c 262144`, KV q8_0, `-fa 1 -ngl 999`,
`--jinja` (template chính thức của model — đo tool-call trước khi chốt), `--metrics`, **không** MTP, `env` UUID 5060, `ttl: 0`.

**Chung:** `groups: may_b: {swap: false, members: [qwen38-api, qwen35-api]}`, `hooks.on_startup.preload: [qwen38-api, qwen35-api]`,
`concurrencyLimit` ≥ 8. `preserve_reasoning` (mặc định BẬT ở b10883): [CHI TIẾT SPEC] đặt **tường minh** mỗi hồ sơ theo
khuyến nghị thẻ model, và đưa phần lịch sử suy luận vào công thức ước token. Không gửi `X-Conversation-Id`.

**Cổng đo trước khi chốt (P3):**
1. Tải Qwen3.5-9B Q6_K + mmproj, kiểm SHA256 với HF LFS.
2. Đo VRAM đỉnh + `GPU Process Memory … Shared Usage` (tràn WDDM) cho từng hồ sơ, **với desktop + tác vụ nền thật đang mở**.
3. `qwen38-api` cấu hình đầy đủ (D03) phải: nạp được, chừa ≥ biên an toàn [CHI TIẾT SPEC 300 MiB, như TD-12] tính cả đỉnh
   khi 1 ảnh + 3 luồng text; không vừa ⇒ báo chủ dự án kèm số, hướng dự phòng C (3 rồi 2 slot) — không tự đổi.
4. `qwen35-api` Q6_K + 262K phải chừa ~2 GiB trên 5060 Ti; không được ⇒ `REOPEN D06`.

## 15. Quan sát

Một mã `X-LTT-Request-Id` xuyên suốt: cửa máy A → lease/waiter → job → gateway → dòng log từng lượt ở gateway → id task/slot
llama.cpp (`/slots`). Ghi **tách** các đoạn thời gian: xếp hàng app · chờ admission (slot/ngân sách) · **chờ residency** ·
nạp model · prefill · TTFT · decode — không gộp thành "latency".

| Nguồn | Thêm |
|---|---|
| Sổ lượt `llm_waiters` (bền 30 ngày) | `model`, cửa, lớp, token đặt/đo, whale, `ly_do_cho`, `cho_residency_s`, kết quả |
| Gateway `/health` | theo **model**: `dang_chay/N`, `token_dat/pool`, whale, `vram_trong` + `shared_usage` theo UUID, residency 3090 |
| Dòng log từng lượt (gateway) | request id, model, UUID, token vào/cache/ra, prefill & decode tok/s, TTFT, hủy, mã lỗi |
| `/ops/jobs-metrics` | độ sâu phòng chờ theo model × lớp, tuổi lâu nhất, trạng thái + lịch sử residency, số lần/thời gian nạp lại LTT-3.8 |
| Engine `/metrics` (qua `/upstream/<model>/metrics`) | `requests_deferred` (**phải = 0**), `n_busy_slots_per_decode`, `prompt_tokens_cached_total`, `spec_decode_*` |
| Tiền | giữ/quyết toán theo model + nhãn giá |

Báo động (`LTT_Soi_CongLLM` mở rộng): VRAM trống < ngưỡng hoặc `shared_usage > 0` theo UUID · `requests_deferred > 0` · log có
"Context size has been exceeded" · `LOI_NAP` · tiến trình lạ trên UUID 3090.

## 16. Hủy (Multi-Job TD-9, KEEP)

| Giai đoạn | Cơ chế |
|---|---|
| Đang chờ (stream/sync) | client ngắt ⇒ ghi nhịp tim thất bại / `is_disconnected` ⇒ `roi`; chưa giữ tiền ⇒ không có gì hoàn |
| Stream đang chạy | chuỗi hiện có: `luong_vlm` đóng httpx → gateway nhả sổ → `upstream.close()` ⇒ llama.cpp nhả ≤ 1 s |
| Sync đang chạy | [CHI TIẾT SPEC] thăm `request.is_disconnected()` trong lúc gọi; ngắt ⇒ đóng httpx (cùng chuỗi trên) |
| Job | luồng canh `is_cancelled()` ~1 s đóng kết nối HTTP tới máy B (T11); tiền: hủy ⇒ hoàn trọn |
| Worker/dịch vụ khởi động lại | lease mồ côi ⇒ `ORPHAN_TIMEOUT`; waiter hết nhịp ⇒ dọn; khoản giữ treo ⇒ quét 6 h / tự hoàn 24 h (có sẵn) |

Sau hủy: slot trống lại ≤ 2 s (`/slots`), lease + đặt chỗ nhả, không khoá residency nào bị giữ.
Kiểm thêm (nghi vấn audit, [INFERRED]): `planner.acquire` có thể để lease mồ côi (lease trong session caller chưa commit) — xác
minh trên PostgreSQL ở P1.

## 17. Tiền (bất biến giữ nguyên)

Chờ miễn phí; ngân sách KV không phải tiền; giữ tiền **chỉ sau khi được nhận** (mọi cửa, kể cả đồng bộ — D04). Bất biến:
INV-003 (bận ⇒ không thu) · INV-011/012 (idempotency theo `request_id`) · INV-MJ-1 (đang chờ ⇒ không có dòng giữ tiền) ·
INV-MJ-2 (hết trần chờ ⇒ 0 khoản treo) · không đo được `usage` ⇒ hoàn trọn · **mới:** giá theo **model đã phục vụ thật**
(`gia_token.tinh(su_dung, model)`), hai bảng giá trong **một** module, nhãn giá theo model.

## 18. Đầu vào (Spec 1)

Text + ≤ 4 ảnh (data URL, ≤ 12 MB/ảnh) cho **cả hai** model, cùng kiểm tra ở cùng một chỗ (`llm_gateway/ngan_sach.py`,
`features.kiem_tham_so`). Không còn lỗi "ảnh vào model không vision" (cả hai hồ sơ đều có mmproj). Tệp/đa tệp: Spec 2.

## 19. Triển khai (thứ tự pha — chi tiết ở plan)

| Pha | Nội dung | Máy |
|---|---|---|
| P0 an toàn | ghim UUID `qwen38-api` + ComfyUI; dọn VRAM nền khỏi 3090 (L-12, chủ dự án làm/cho phép); đo **baseline b10883** (C1, VRAM) làm mốc hồi quy | B |
| P1 tích hợp | rebase 9 commit Multi-Job lên trunk (đánh số lại test 950–956 theo bảng cấp phát, nối migration), hoàn tất T9 theo D04 | A |
| P2 hợp đồng | `ToolSpec.admission_theo_model` + resolver; hai ID công khai + cắt tên cũ + di trú dữ liệu nội bộ; giá theo model | A |
| P3 engine | tải 3.5; hai hồ sơ + group + preload; cổng đo §14 | B |
| P4 gateway | sổ slot/token/whale theo model; `/health` theo model; hủy cứng job (T11); log từng lượt | A+B |
| P5 residency | bảng `gpu_residency`, máy trạng thái, lệnh gateway, gỡ hai trọng tài cũ, anhnoibo khai resource | A+B |
| P6 quan sát + GPU | sửa 11 bộ đọc theo UUID, `test_637`, metric/báo động | A+B |
| P7 tài liệu | Q mới trong `QUYET_DINH_NEN_TANG.md`, `NHAT_KY.md`, runbook máy B | A |

Sau P7 → Spec 2 → **nghiệm thu tích hợp A–Q một lần** (D05) → bật + cắt tên (D08).
Deploy trung gian lên production tự do (chưa có khách — D08), giữ: gate xanh, sổ sách đúng, hỏi phiên khác, UAC.

## 20. Di trú

- Tên (D02): dữ liệu nội bộ mang `ltt_llm`/`ltt_llm_vision` — job còn trong hàng, lựa chọn model đã lưu của ChatLTT/agent —
  di trú sang `ltt-3.8` **trong cùng lần deploy** bằng migration dữ liệu (không phải bí danh). Lịch sử usage/credit giữ nguyên.
- Resource `llm_remote` → `ltt_38_3090`/`ltt_35_5060`: drain lease trước deploy (không có khách ⇒ đơn giản).
- `qwen38-vision` biến mất khỏi gateway (`LTT_LLM_MODELS=qwen38-api,qwen35-api`).

## 21. Đường lùi (D08 — cơ học)

Máy A: `C:\LTTPlatform\app.previous` (+ `dau_van_tay.json`). Máy B: `H:\LTT_LLM\releases\auto-<ts>` (gateway + yaml) +
`nang_llamacpp.ps1 -Ban <build trước>` + env ComfyUI cũ. Migration chỉ cộng thêm (cột/bảng mới vô hại với mã cũ).
Nghiệm thu có mục **kiểm cơ học đường lùi** (chạy thử lùi + tiến trên máy B, đo thời gian).

## 22. Trạng thái lỗi

| Tình huống | Hành vi |
|---|---|
| llama-server model X chết | gateway 503 ⇒ stream: sự kiện lỗi đúng khuôn; sync: 503 + Retry-After; job: `resource_wait` thử lại. **Không** đổi sang model kia |
| Gateway / llama-swap khởi động lại | lease hết nhịp ⇒ nhả; waiter chờ tiếp tới trần; residency đọc lại trạng thái thật (`/running`, VRAM UUID) trước khi bước tiếp |
| Nạp lại LTT-3.8 hỏng | `LOI_NAP`: thử lại lùi dần, báo động; người chờ 3.8 nhận lỗi khi hết trần; ảnh vẫn chạy được |
| ComfyUI hỏng trong cửa sổ | job ảnh lỗi theo đường hiện có; cửa sổ đóng; LTT-3.8 nạp lại |
| VRAM 5060 Ti thấp / `shared_usage > 0` | báo động; gateway đánh `ban` cho model 3.5 khi vượt ngưỡng cứng (không nhận lượt mới) — không giết lượt đang chạy |
| GPU không thấy (UUID thiếu) | `/health/ready` 503; không nạp gì |
| Tệp ảnh hỏng | lỗi riêng slot đó (engine), 4xx ở máy A — không lan sang slot khác |
| Ước token sai ⇒ engine hoãn | `requests_deferred > 0` ⇒ báo động; sổ gateway (ước dư + biên) là lớp chặn thứ hai |

## 23. Nghiệm thu (chạy MỘT lần sau Spec 1 + Spec 2)

| Mục | Nội dung | Ngưỡng |
|---|---|---|
| A | Tĩnh: đúng hai ID, 0 tên cũ chấp nhận được, UUID khớp `gpu_may_b.json`, 0 bộ đọc "dòng 0", hash model/engine khớp | 0 lệch |
| B | C1 LTT-3.8 | decode ≥ 90 % mốc b10883 đo ở P0 |
| C | C1 LTT-3.5 text + ảnh | trả lời đúng; mốc ghi lại |
| D | C4 LTT-3.8 | tổng ≥ 100 tok/s; TTFT ngắn p95 ≤ 3 s khi còn chỗ |
| E | C4 LTT-3.5 | tổng ≥ [CHI TIẾT SPEC] 2 × C1 của chính nó |
| F | C4 + C4 đồng thời | mỗi bên ≥ 85 % số E/D đo riêng (ảnh hưởng CPU/RAM/PCIe chung được **đo** và ghi) |
| G | Ngữ cảnh hỗn hợp ngắn/vừa/dài | 0 "Context size has been exceeded", 0 OOM, 0 cắt ngầm, `requests_deferred` = 0 |
| H | LTT-3.8 262.144 | nạp + kim-trong-đống-cỏ đúng ở ≥ 5 độ sâu tới ~250K; ghi token vào, prefill tok/s, TTFT, decode, VRAM đỉnh; **cổng MTP `-np 4`**: 200 lượt đồng thời có dấu riêng từng slot (kể cả prompt > ubatch và có ảnh) ⇒ 0 trả lời rỗng, 0 trộn dấu, tỉ lệ nhận nháp > 0 mỗi slot |
| I | Residency 3090: ảnh + LLM xen kẽ | 0 lượt LLM chết giữa chừng, 0 ảnh OOM, cửa sổ đóng đúng luật §12, số lần/thời gian nạp lại ghi |
| J | LTT-3.5 chạy trong lúc 3090 vẽ | ≥ 90 % số C4 LTT-3.5 riêng |
| K | Kho ấm | nạp lạnh vs ấm cả hai model, có số |
| L | Đa tệp | (Spec 2) |
| M | Hủy: đang chờ / đã nhận / prefill / decode / ngắt stream / job | slot trống ≤ 2 s; tiền đúng |
| N | Lỗi: llama-server chết, gateway/llama-swap khởi động lại, mất mạng A↔B, ảnh hỏng, UUID thiếu, ComfyUI hỏng, nạp lại hỏng | hành vi đúng §22 |
| O | Tiền: thành công, bận, hủy, retry, mất mạng, request sai, model chết | 0 thu hai lần, 0 khoản treo, bận không thu, giá đúng model |
| P | Rò slot generator: bắt đầu / chưa bắt đầu / ngắt / lỗi trước yield đầu / sau yield đầu | 0 lease rò |
| Q | Soak tải hỗn hợp thật (hai model + ảnh), sau khi A–P qua | 0 OOM/crash, `requests_deferred` = 0, bộ nhớ/handle/lease/khoản giữ không trôi, độ trễ không trôi |
| + | Đường lùi | chạy thử lùi + tiến trên máy B; ghi thời gian |

Mỗi phép kiểm bất biến có **đối chứng**: tiêm bản cũ/luật bỏ vế ⇒ phải đỏ (memory "số 0 cần đối chứng").
Gói tái hiện (prompt §19): nhánh + SHA + hash diff bẩn, trạng thái phần mềm A/B, UUID/PCI, driver/CUDA, build llama.cpp +
llama-swap, hash model/mmproj/cấu hình/fixture/script, RAM nền, thời điểm.

## 24. Rủi ro còn lại

| Rủi ro | Biện pháp |
|---|---|
| Cấu hình đầy đủ LTT-3.8 không vừa 24 GB (cộng đồng: 262K + MTP không nạp) | cổng đo §14; hướng dự phòng C do chủ dự án chốt; không tự đổi |
| MTP + `-np 4` trả lời rỗng (#27572, chưa sửa upstream) | cổng H; trượt ⇒ REOPEN D03 |
| 5060 Ti chừa ~2 GiB mỏng (D06 B) | telemetry VRAM + Shared Usage theo UUID, `ban` khi vượt ngưỡng cứng |
| Giá LTT-3.5 có thể dưới chi phí điện ở tải thấp (D07 A, đã chấp nhận) | đo W/token ở P3 + nghiệm thu, ghi báo cáo |
| Rebase 450 commit chạm `jobs.py`/`job_runner.py`/`models.py` | P1 tách riêng, chạy lại test Multi-Job + Scheduler V1 trên cây hợp nhất trước khi đi tiếp |
| Nạp lại LTT-3.8 sau mỗi cửa sổ ảnh (~34 s+, chưa đo ở 262K) | đo ở P3; đưa vào `T_NAP_LLM` của luật đóng cửa sổ |
| Desktop quay lại 3090 sau cập nhật Windows/khởi động lại | báo động "tiến trình lạ trên UUID 3090" |

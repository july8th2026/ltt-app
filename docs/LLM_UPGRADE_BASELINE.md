# LLM_UPGRADE_BASELINE — trạng thái THẬT của LTT LLM, đo từ mã nguồn

Phase 0 của chương trình MASTER SUPER PROMPT (2026-09-09).
Tài liệu này là **ảnh chụp có bằng chứng**, không phải kế hoạch. Kế hoạch ở
`LLM_UPGRADE_MASTER_PLAN.md`; điểm ở `LLM_QUALITY_LEDGER.md`.

> ⛔ Mọi con số dưới đây đều dẫn nguồn tới **tệp:dòng**. Đừng gõ lại một con số
> nào từ đây vào tài liệu khác — đó chính là cơ chế đã hỏng năm lần ở dự án này.

---

## 1. HEAD đã xác minh

```
kho      : giaitritruyenthongltt-spec/LTTSTUDIOSAPP
cây      : D:/LTTSTUDIOSAPP/.claude/worktrees/ltt-llm-api-http-guide-a3e123
nhánh    : claude/ltt-llm-master-upgrade-ddcfc9
HEAD     : 99017910  (day du: `git rev-parse HEAD`)
git status: sạch (không có tệp sửa, không có `??`)
```

`99017910` **bằng đúng** tip của `admin-mvp-v3` (cây chính `D:/LTTSTUDIOSAPP`)
tại thời điểm đo. Tức nhánh này xuất phát từ trunk, không tụt lại.

Bảy worktree khác đang tồn tại (`git worktree list`). Cây này **không phải của
riêng phiên nào** — luật 12/13/14 của `CLAUDE.md` áp dụng.

### 1.1 Một mục ĐÃ CŨ trong `~/.claude/CLAUDE.md` (đo lại 09/09)

Tệp cấp người dùng nói cây `ltt-llm-api-http-guide-*` chạy bản `gate.py` cũ và
truyền `-n 14`. **Không còn đúng.** Đo trực tiếp:

```
grep -c "loi_cho_bo_test" tools/gate.py   ->  6      (bản cũ: 0)
TRAN_WORKER_BO_TEST = 6                   tools/gate.py:252
LOI_DE_DANH_VAT_LY  = 3                   tools/gate.py:242
```

Cây này đã đồng bộ khi nó nhận trunk `99017910`. Ghi ở đây để phiên sau không
tự giới hạn theo một dòng cảnh báo đã hết hạn. (Tệp cấp người dùng là của chủ
dự án; tôi không sửa nó.)

---

## 2. Kiến trúc — tái dựng từ mã, không từ tài liệu

```
MÁY A  (LTTSTUDIOSAPP, cổng 8100)
  apps/ltt_llm/{manifest,features,executor,jobs,ngan_sach}.py
  platform_core/llm/{dieu_phoi,cong_vlm,thanh_toan,gia_token,admission,
                     luong_vlm,dem_token_luong}.py
  platform_core/{api_pool,api_keys,providers,credit}.py
        |
        |  LAN riêng — bearer token, chỉ 192.168.2.17 được vào
        v
MÁY B
  [3] llm_gateway            :8299   nghe LAN   (llm_gateway/*.py, 2.352 dòng)
        |  loopback
  [2] llama-swap             :8280   vòng đời model, ttl nhả VRAM
        |  loopback
  [1] llama-server           :8281   CHỈ 127.0.0.1, KHÔNG xác thực
        v
  Qwen3.8-27B-UD-Q4_K_M.gguf  (H:/LTT_LLM/models/)   RTX 3090 24 GB
```

Nguồn: `llm_gateway/__init__.py:1-30`, `llm_gateway/deploy/llama-swap.yaml:82-84`.

### 2.1 Model — tên và lượng tử THẬT

`llama-swap.yaml:83-84` (macro `GGUF`):

```
H:/LTT_LLM/models/Qwen3.8-27B-UD-Q4_K_M.gguf
```

⇒ Baseline của prompt (`Qwen3.8-27B`, `UD-Q4_K_M`) **khớp mã nguồn**. Cảnh báo
"đừng gọi là Wan3.8 37B" là đúng và không có chỗ nào trong kho gọi sai.

### 2.2 Hai hồ sơ phục vụ — số ĐO, không phải số mong muốn

| hồ sơ | `-c` engine | vision | nguồn |
|---|---|---|---|
| `qwen38-api` | **204 800** | không | `llama-swap.yaml:155` |
| `qwen38-vision` | **131 072** | có (`mmproj-F16.gguf`) | `llama-swap.yaml:197,199` |

`llm_gateway/catalog.py:HO_SO` khai đúng hai số đó (204 800 / 131 072).
`apps/ltt_llm/ngan_sach.py:CUA_SO_MODEL=204_800`, `CUA_SO_MODEL_VISION=131_072`.

⭐ **Ba tầng đồng ý.** Đây là kết quả đáng kể — nó là thứ mà `test_334` và
`test_250` cưỡng chế, không phải may mắn.

### 2.3 Dẫn xuất ngân sách — một nguồn, có phép kiểm

`apps/ltt_llm/ngan_sach.py:103-120`:

```
TOKEN_VAO_TRAN      = CUA_SO_MODEL - TOKEN_RA_TRAN - LE   = 169_984
BODY_BYTES_TOI_THIEU= TOKEN_VAO_TRAN * 4.5               ≈ 747 KB
CONG_BO_CHO_CLIENT  = TOKEN_VAO_TRAN * 0.92              = 156_385
```

Bản sao ở máy B: `llm_gateway/config.py:124` `max_input_tokens=169_984`.
**Có phép kiểm buộc hai đầu**: `tests/test_250_llm_gateway.py:45`

```python
assert cfg.max_input_tokens == ngan_sach.TOKEN_VAO_TRAN
```

---

## 3. Hợp đồng runtime đã xác minh

### 3.1 Bề mặt HTTP của cổng (`llm_gateway/api.py`)

| đường | auth | ghi chú |
|---|---|---|
| `GET /live` | **không** | cố ý trần trụi, chỉ `{ok, version}` (api.py:263-276) |
| `GET /health` | có | model mở, trọng tài, trần, giới hạn, gpu, `duoi_dich_vu` |
| `GET /v1/models` | có | fail-closed, rỗng là ĐÚNG |
| `POST /v1/chat/completions` | có | OpenAI Chat |
| `POST /v1/responses` | có | Codex CLI |
| `POST /v1/messages` | có | Claude Code |

Ba giao thức đi **chung một đường ống** `_chuyen_tiep` → `_chay_that`; cổng
không dịch gì, chỉ kiểm rồi chuyển tiếp (`api.py:20-24`).

### 3.2 Mã trạng thái — hợp đồng đã cưỡng chế

| tình huống | cổng trả | máy A đọc thành | có `danh_dau_loi`? |
|---|---|---|---|
| cổng đầy suất (`max_dong_thoi`) | **429** + `Retry-After` | `BanError` | **không** |
| trọng tài: máy B bận | **429** + `Retry-After: 30` | `BanError` | **không** |
| card chưa dọn sạch | **429** + `Retry-After: 60` | `BanError` | **không** |
| vượt trần token/ảnh | **413** | `VuotNganSachError` | **không**, và **không cascade** |
| model không mở | **404** | `CongVlmError` | có |
| thượng nguồn ≥500 hoặc 599 | **502** | `CongVlmError`/OOM | có |
| mất kết nối SAU khi POST | — | `AmbiguousProviderError` | **không cascade** |

Nguồn: `api.py:377-475`, `platform_core/llm/cong_vlm.py:200-245`,
`platform_core/llm/dieu_phoi.py:206-232`.

⭐ **`AmbiguousProviderError` là thứ đáng khen nhất của tầng này.** Timeout sau
POST **không** được cascade sang provider khác, vì lượt đầu có thể đã tạo tác
dụng phụ. Đó chính là cạm bẫy "retry duplicate side effect" mà rubric phạt tới
Reliability ≤ 90 — và ở đây nó **đã được xử đúng**, có chú thích lý do
(`dieu_phoi.py:228-231`).

### 3.3 Bất biến đã có phép kiểm bảo vệ

* **429 ≠ lỗi.** `BanError` là lớp ngoại lệ **riêng**, không kế thừa
  `CongVlmError` (`cong_vlm.py:57`). Nếu lẫn: `api_pool` cooldown → `disable`
  key `ltt_llm` sau 5 lần → một tối máy B chạy video tự tắt vĩnh viễn model nhà.
* **Không fallback sau lưng khách.** `CongVlm.chat()` **không có** tham số
  `fallback`, có chủ ý (`cong_vlm.py:196-199`). Cascade chỉ tồn tại ở
  `dieu_phoi.goi()` cho **việc nội bộ**, và bên gọi phải tự khai
  `thu_tu_provider` — khai ra thì không phải là lén (`dieu_phoi.py:24-33`).
* **Không đo được thì không thu.** `usage` thiếu ⇒ `SuDung.dang_tin=False` ⇒
  `quyet_toan_hoac_hoan()` hoàn đủ + cảnh báo (`thanh_toan.py:44-48`).
* **Suất là nợ.** Mọi đường ra khỏi `_chuyen_tiep` phải trả suất, kể cả đường
  ném ngoại lệ. Với SSE, suất trả khi **luồng hết** — và có **hai** đường độc
  lập cho việc đó (`finally` của `boc_luong` + `BackgroundTask`), vì sự cố
  31/08 chứng minh một đường là không đủ (`api.py:430-455`).

---

## 4. Bao phủ phép kiểm hiện có

77 tệp test chạm `llm_gateway`/`ltt_llm`, **26 490 dòng**. Các tệp lõi:

```
test_250_llm_gateway.py         679   hợp đồng cổng, 401, trần một nguồn
test_334_ngan_sach_ltt_llm.py  1109   ngân sách + hai bản sao deploy
test_259_cua_dong_bo.py         867   cửa đồng bộ
test_272_cua_streaming.py       655   cửa streaming
test_313_llm_admission.py       801   admission plane
test_363_suat_khong_ro.py       336   rò suất (sự cố 31/08)
test_269_nhip_tim.py                  nhịp tim SSE (Codex/Claude Code 300 s)
test_270_tren_gpu.py                  model có thật trên card không
test_373_ssrf_anh_tu_xa.py            SSRF ảnh từ xa
test_604_q120_...py                   trần công bố là số dẫn xuất
```

⭐ Đây **không** phải một hệ thống thiếu test. Nó là một hệ thống có test
**dẫn dắt bởi sự cố thật** — đúng thứ rubric §29 nói là đáng giá.

---

## 5. GAP MATRIX ban đầu — chỉ những gì đã XÁC MINH

Ký hiệu: **[X]** đã xác minh bằng mã · **[?]** cần đo runtime mới kết luận được.

### G-01 · W7 · Auth fail-open — **[X] CÓ THẬT**

```python
# llm_gateway/api.py:255
def auth(authorization: str = Header(default="")) -> None:
    if not cfg.token:
        return          # dev: chưa đặt token → không chặn
```

`main.py:118-120` chỉ **log cảnh báo** khi token rỗng; tiến trình vẫn khởi động.
Không có chỗ nào nối `host` với `token`.

* `deploy.ps1:301,303` ghi `LTT_LLM_HOST=127.0.0.1` + token sinh ra ⇒ **đường
  deploy mặc định an toàn**.
* Nhưng máy A phải gọi được ⇒ ai đó **phải** đổi host thành `0.0.0.0` bằng tay
  trong `gateway.env`. Từ giây đó, một dòng `LTT_LLM_TOKEN=` rỗng (hoặc bị xoá)
  biến model nhà thành dịch vụ mở cho cả LAN, và **triệu chứng duy nhất là một
  dòng log**.
* `nap_env` (`main.py:32-56`) đặt bất kỳ khoá `LTT_LLM_*` nào, kể cả giá trị
  rỗng ⇒ `token=""`.

⚠️ **ĐÃ ĐO TRÊN MÁY B (09/09, từ máy A, chỉ đọc)** — và kết quả làm nhẹ mức độ:

```
GET http://192.168.2.66:8299/live    -> 200  {"ok":true,"version":"0.1.0"}
GET http://192.168.2.66:8299/health  -> 401  {"detail":"token khong dung"}
```

`/health` trả **401 khi không kèm bearer** ⇒ `LTT_LLM_TOKEN` **đang được đặt**
trên production. Đây là **rủi ro tiềm tàng, không phải lỗ hổng đang mở**.

⭐ Phép đo này làm được hai việc cùng lúc: nó ngăn một báo cáo nói quá, **và** nó
   chứng minh bản vá P2-01 an toàn để deploy — vì chốt mới đòi đúng cái đang có.
   Không đo thì bản vá này là một canh bạc: nếu token rỗng thật, lần deploy kế
   tiếp sẽ **không khởi động lại được** và model nhà tắt giữa giờ chạy.

**Vì sao vẫn đáng sửa dù hôm nay có thể đang an toàn:** ranh giới hiện tại là
một **giao ước** ("nhớ đặt token khi mở host"), và `CLAUDE.md` của chính dự án
này đã ghi bài học *"ranh giới CƠ HỌC thắng giao ước"*. Bản sửa đúng là một
điều kiện khởi động, không phải thêm một dòng cảnh báo nữa.

### G-02 · W10 · llama-swap KHÔNG được ghim, KHÔNG được ghi lại — **[X] CÓ THẬT**

Không tệp nào trong kho ghi phiên bản llama-swap đang chạy trên máy B:

```
grep -rniE "dau_van_tay|VERSION_FILE|api/version"  llm_gateway/  ->  0 kết quả
deploy.ps1  chỉ chép llama-swap.yaml, không chép/không kiểm binary
/health     báo thuong_nguon.{url,ma,song} — KHÔNG có phiên bản
```

⇒ Từ kho, **không ai trả lời được** "máy B đang chạy llama-swap bản nào".
Đây không phải chuyện thẩm mỹ: nó **chặn** mọi thiết kế W2 (§6 dưới đây).

### G-03 · W10 · `nang_llamacpp.ps1` mặc định lấy bản MỚI NHẤT — **[X] CÓ THẬT**

`nang_llamacpp.ps1:107-118`: không truyền `-Ban` thì script hỏi GitHub API và
lấy release đầu tiên có gói `win-cuda-$Cuda-x64`. Trái §25 của prompt
("không `git pull latest` → production").

⭐ **Nói công bằng:** script này **đã có** rollback (`$saoLuu` + nhánh
`HOAN NGUYEN`, dòng 95-101), có in phiên bản trước/sau, và có chốt
`if ($Ban -eq $cu) { exit 0 }`. Nó cũng chỉ chạy khi người vận hành gõ tay.
Khuyết tật là **không có bản được chúc phúc nào được ghi trong kho** để so.

### G-04 · W2 · Cổng không có bề mặt đo lường — **[X] CÓ THẬT**

`grep -rn "metrics|prometheus" llm_gateway/` ⇒ **rỗng**. Máy A **có** đếm
(`platform_core/public_api/metrics` dùng ở `llm/admission.py:53,97,103,123`),
máy B thì không. Không có TTFT, không có tok/s, không có phân loại lỗi theo
nhóm, không có lịch sử.

Thứ **đang** có ở `/health` là **trạng thái tức thời**, và nó khá tốt:
`trong_tai`, `gioi_han.trang_thai()`, `gpu.tren_gpu`, `duoi_dich_vu`. Thiếu là
**chuỗi thời gian** và **số đếm cộng dồn**.

### G-05 · W12 · Chú thích đã hết đúng và vẫn sống — **[X] CÓ THẬT, 3 chỗ**

1. `llm_gateway/config.py:121` — *"`tests/test_312` đỏ ngay khi hai bên lệch"*.
   `tests/test_312_vps_khoa_dich_vu.py` là **khoá dịch vụ VPS**, không liên quan.
   Phép kiểm thật là `tests/test_250_llm_gateway.py:45`.
   `docs/VLM_NOI_BO/RA_SOAT_THAM_SO_LTT_LLM.md:559` **đã ghi nhận** vụ trùng số
   test này rồi — nhưng chỉ sửa tệp docs, không sửa chú thích trong mã.
   (`platform_core/public_api/config.py:76` dính đúng lỗi ấy, chỗ thứ hai.)

2. `apps/ltt_llm/ngan_sach.py:66` — văn nói `qwen38-vision` nạp `-c 65536`;
   giá trị gán ngay dưới là `131_072`, và `llama-swap.yaml:199` cũng là
   `131072`. **Runtime đúng, chỉ văn sai** (đợt 03/09 đổi giá trị, bỏ quên văn).

3. `apps/ltt_llm/manifest.py:32,42-46,94` — nói trần vào là **96 256**, engine
   `-c 131072`, công bố **89K**, vision *"trần vào 30 720, công bố 28K"*.
   Số thật hôm nay: **169 984** / `-c 204800` / **156 385**.

⚠️ Cả ba **không chạm runtime** — tôi đã kiểm đường thật cho từng cái. Nhưng
chỗ (3) mang một vị đắng đáng ghi: đoạn văn sai ấy **chính là một thông báo
đính chính** ("🔴 SỬA 01/09 — BA CON SỐ Ở ĐOẠN NÀY ĐỀU ĐÃ TRÔI"). Một bản vá
sửa **giá trị** thì lần trôi sau sẽ trôi y hệt. Đây đúng mẫu mà chính tệp đó
tự đặt tên: *"Sửa giá trị không phải sửa hình dạng."*

### G-06 · W5 · TIMEOUT lẫn với UNREACHABLE ở tầng cổng — **[X] CÓ THẬT, tác động HẸP**

`upstream.py:37-40` bắt `httpx.HTTPError` (bao gồm `TimeoutException`) → trả
`599` → `api.py` map mọi `ma>=500` thành **502**.

⇒ "llama-swap chết" và "prefill 200K vượt `upstream_timeout_s`" ra **cùng một
mã**. Máy A `danh_dau_loi` cho cả hai.

⚠️ **Đo trước khi kêu to:** `upstream_timeout_s = 600 s`, `stream_timeout_s =
900 s` (`config.py:126-127`), trong khi prefill 180K đo được ~640 tok/s
(`catalog.py:44-46`) ⇒ ~280 s. Tức timeout nằm **hơn gấp đôi** thời gian tệ
nhất đã đo. Đây là lỗ hổng **phân loại**, chưa phải lỗ hổng **đang chảy máu**.

### G-07 · W1 · Số `169984` xuất hiện gõ tay ở 4 chỗ deploy — **[?] cần đối chiếu**

`deploy.ps1:274,283,309` và `llama-swap.yaml:123` (chú thích). `ngan_sach.py:59-62`
**đã cảnh báo đúng chuyện này**. `test_334:277,283` có nhắc `llm_gateway/config.py`
— phải đọc kỹ để biết nó chốt được **mấy** bản sao trong số đó. Việc của Phase 1.

---

## 6. Điều CHẶN, phải giải trước khi thiết kế W2

**Không thể thiết kế quan trắc mà không biết llama-swap bản nào đang chạy.**

Upstream `mostlygeek/llama-swap` @ `8fa85899` (2026-09-07) đã phơi sẵn:

```
GET  /metrics                  Prometheus
GET  /api/metrics/activity     kho hoạt động (SQLite, bền)
GET  /api/metrics/stats
GET  /api/hardware             telemetry GPU/hệ thống
GET  /api/performance
GET  /api/events               SSE: nạp/nhả/đổi model
GET  /api/version
GET  /running                  ← LTT ĐANG dùng cái này
POST /api/inflight/{id}/cancel
POST /api/models/unload
```

(nguồn: `internal/server/*.go`, đã liệt kê bằng grep trên bản sao đã ghim SHA.)

⇒ Câu hỏi bắt buộc của O1 — *"LTT đang tự làm thứ gì mà llama-swap đã làm tốt
hơn?"* — **không trả lời được từ kho**, vì G-02: kho không biết bản nào đang
chạy. Nếu bản trên máy B cũ hơn, những đường trên **không tồn tại**, và mọi
thiết kế dựa vào chúng là thiết kế trên giấy.

⛔ Đây đúng cạm bẫy *"đọc thứ đại diện thay vì đọc thứ thật"*. Nên **Phase 2
không được bắt đầu trước khi hỏi máy B `GET /api/version`** (hoặc, nếu bản cũ
không có đường đó, đọc dấu vân tay binary).

---

## 7. Điểm khởi đầu — TẠM, và tôi nói rõ vì sao chúng bị chặn trần

Rubric §14 chặn trần: chưa chạy final gate ⇒ **không** được gắn nhãn VERIFIED;
chỉ có mã mà chưa targeted verification ⇒ Implementation ≤ 95.

| # | Hệ con | Trước (tạm) | Trần đang bị chặn bởi | Ghi chú |
|---|---|---|---|---|
| W1 | Model identity / config | 93 | G-07 chưa đối chiếu | ba tầng đã đồng ý + có test |
| W2 | Quan trắc | 72 | G-04 + **CHẶN** ở §6 | `/health` tốt, không có chuỗi thời gian |
| W3 | Baseline hiệu năng | 80 | chưa có bộ chạy lại được | có số đo thật 03/09, chưa tái lập được |
| W4 | Vòng đời cổng | 92 | — | sự cố 31/08 đã sửa hai đường độc lập |
| W5 | Phân loại lỗi | 90 | G-06 | trần Reliability 94 của rubric |
| W6 | Điều phối máy A | 95 | — | `AmbiguousProviderError` xử đúng |
| W7 | Bảo mật | **88** | G-01 fail-open ⇒ rubric ép Security ≤ 90 | phần còn lại mạnh |
| W8 | Token/ngữ cảnh | 94 | G-05(2)(3) | runtime một nguồn; văn trôi |
| W9 | Tính tiền | 95 | chưa soát hết đường stream/job | giữ→chạy→quyết toán đúng |
| W10 | Deploy/ghim | **78** | G-02, G-03 | có snapshot + rollback |
| W11 | Cổng phát hành | 88 | — | `tools/gate.py` khoẻ hơn CI thường |
| W12 | Bảo trì | 85 | G-05 (3 chỗ) | mã rất tốt, văn trôi |
| W13 | Corpus hồi quy | 90 | — | 26 490 dòng, dẫn dắt bởi sự cố |

⛔ **Không con số nào ở trên là VERIFIED.** Chúng là điểm *thiết kế/đọc mã* ở
Phase 0 và sẽ được chấm lại sau từng phase.

---

## 8. Kết luận Phase 0

**Đây không phải một hệ thống yếu.** Mã lõi có mật độ kỹ thuật cao bất thường,
mỗi hằng số quan trọng đều mang theo phép đo và ngày đo, và nhiều lớp phòng thủ
tồn tại vì một sự cố có thật đã trả giá cho chúng. Rubric "fitness for actual
purpose" (§1) áp vào đây cho điểm **cao**, không thấp.

Khoảng trống thật tập trung ở **ba chỗ**, và cả ba đều là *vận hành*, không phải
*kiến trúc*:

1. **G-01** — một ranh giới bảo mật đang dựa vào giao ước thay vì cơ chế.
2. **G-02/G-03** — kho không biết máy B đang chạy phần mềm phiên bản nào.
3. **G-04** — không có chuỗi thời gian nào để nói "hôm nay có chậm hơn hôm qua
   không", trong khi thứ sinh ra nó (llama-swap) có thể đã sẵn sàng cho không.

Ba khoảng trống này **liên kết**: (2) chặn (3). Nên thứ tự phase phải đổi so
với prompt: **giải G-02 trước, rồi mới thiết kế W2.**

Không phát hiện **P0** nào. Không phát hiện lỗi tính tiền nào. Không phát hiện
đường fallback lén nào. Không phát hiện chỗ nào cascade một request có thể đã
tạo tác dụng phụ.

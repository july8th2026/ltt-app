# PROMPT 08 — Independent Final Acceptance & Red Team

> **Phiên:** nghiệm thu độc lập, chạy trên máy A **vừa khởi động lại** (`15:51:28`, 01/09).
> **Chế độ:** REVIEWER. Mọi báo cáo 00–07 được coi là **lời khai cần kiểm chứng**.
> **Không** bắt đầu tối ưu hoá hay refactor mới.
>
> ⚠️ Đây **là** máy production, đang bán thật qua `/api/v1`. Mọi phép đo dưới
> đây chạy trên hệ thống đang phục vụ khách, bằng một khoá canary `.local` tự
> phát (`setup\chay_voi_env.ps1 -Viec khoa-canary`) tiêu **tiền thật** của tài
> khoản thử. Khoá không xuất hiện ở bất kỳ đâu trong tài liệu này.

---

## 0. VERDICT

# `CONDITIONAL PASS`

**Không có P0.** G1–G4 không có gate nào hỏng nghiêm trọng. Nhưng:

- **G6 (protocol truthfulness) HỎNG** — ta công bố cho khách một năng lực
  không có thật (`ltt_llm_vision` "same 89K usable input context"; trần thật
  **65.536**). Xem F-02.
- **G7/G8 có lỗ đo được** — bộ dò "health xanh giả" **không ai chạy**, và một
  bất biến tiền quan trọng được đánh dấu `VERIFIED-LIVE` dựa trên **một cột
  luôn bằng 0**. Xem F-01, F-07.
- **Bằng chứng sống quan trọng vẫn thiếu**: canary bằng **client thật**
  (Codex CLI / Claude Code / VS Code), benchmark GPU D30–D36, và diễn tập
  rollback trên **máy A**.

Theo luật §7 của Prompt 08 — *"important live/client evidence unavailable →
normally CONDITIONAL PASS, not FINAL PASS"* — và vì một tuyên bố năng lực sai
đang tới tay khách, verdict là `CONDITIONAL PASS`, không phải `FINAL PASS`.

⛔ **Không có gì ở đây đòi dừng bán.** Mọi phát hiện đều sửa được mà không
chạm kiến trúc; ba trong tám là **sửa một dòng**.

---

## 1. Identity & change audit (H01)

| | |
|---|---|
| Nhánh / HEAD | `admin-mvp-v3` @ `c31b1ae` |
| Baseline đóng băng (Prompt 00) | `2ed62d7` |
| Trôi kể từ baseline | **81 commit** (gồm cả 7 phase audit lẫn lane LTT VOICE) |
| Trôi kể từ MỐC BÀN GIAO (`707e403`, 15:25) | **4 commit** — `18dc6af`, `ce9e2c1`, `6e74bdd`, `c31b1ae` |
| Bốn commit đó có chạm đường thi hành `ltt_llm` không? | **KHÔNG** — chỉ `tools/do_sau_khoi_dong.py`, LTT VOICE, `ho_so_he_thong.txt`, template VPS |
| Kho ↔ production máy A | **KHỚP 7/7 tệp** trên đường `ltt_llm` (SHA256, đo dưới LocalSystem) |
| Cấu hình máy B: trên đĩa ↔ đang chạy | **KHỚP** — `llama-swap.yaml` ghi `-c 131072`, tiến trình `llama-server.exe` đang chạy `-c 131072` |
| Rollback máy A | `app.previous` **có** (13:26, 4.036 tệp) + `rollback.ps1` đọc qua thấy mạch lạc |

⭐ **Mâu thuẫn C-04 của Prompt 03 nay đã TỰ ĐÓNG.** Nó ghi *"cấu hình trên đĩa
≠ cấu hình đang chạy"* (đĩa 65K, tiến trình 90K). Đo lại 01/09: cả hai đều
`131072`. Con số `65536` còn lại là của **`qwen38-vision`**, và đó là cấu hình
cố ý cho model đó, không phải một vệt trôi. *(Nhưng nó đẻ ra F-02 — xem dưới.)*

⚠️ **Có hai phiên Claude khác đang ghi vào cây ngay lúc nghiệm thu.** Đo nhịp
ghi tệp lúc 16:24: `tools/do_chon_cua_so_bieu_cam.py` **16:22**,
`docs/auto_scan_video/STATE.md` **16:18**. Cả hai **đang sống** — không suy ra
"ai đó bỏ việc" từ sự vắng mặt.

---

## 2. Acceptance ladder

### L1 — Static / unit (H02, H04, H05)

`python tools\gate.py` — **`RESULT: FAIL (3/26)`**, 5,6 phút.

Bước đỏ **duy nhất**: `test_306_banh_coc_bo_qua_va_dich.py::test_bo_qua_hien_tai_dat_moc`,
vì đúng **một** phép kiểm bị bỏ qua mà chưa khai:

```
test_388_chan_doan.py::test_KHONG_luat_nao_co_dung_sai_VUOT_DAI_gia_tri
    <- chua ghim baseline lech
```

⛔ `test_388` là tệp của **lane LTT VOICE**, đang được một phiên khác sửa dở
(ghi lúc 16:12–16:22, đo được). Đây **không** phải khuyết tật của `ltt_llm`, và
tôi **không** chạm vào nó.

⭐ Hai điều đáng ghi so với lượt gate ở MỐC BÀN GIAO:

1. Bước đỏ cũ (`nuot loi lang le 64 | moc 63`) nay **XANH** — phiên chủ sở hữu đã sửa.
2. **Không** có dòng `[CAY DA DOI GIUA CHUNG]` ở lượt này.

⚠️ **Một bước tự khai bỏ qua, và nó thuộc phạm vi này:**
`test_334_ngan_sach_ltt_llm.py::_health` bỏ qua vì thiếu `LTT_LLM_TOKEN` — tức
tầng **đối chiếu SỐNG với máy B** của INV-005 **không chạy** trong lượt gate.

✅ Tôi đóng nó bằng đường khác, **không sửa gì trong cây**: `/health` của máy B
lấy qua `chay_voi_env.ps1 -Viec soi-su-co` cho `input_tokens=96256`,
`output_tokens=32768`, `max_dong_thoi=1` — khớp đúng ba hằng số
`TOKEN_VAO_TRAN` / `TOKEN_RA_TRAN` / `DONG_THOI_MAY_B`. Cả ba assert của
`TestDoiChieuMayB` đứng vững trên runtime thật.

### L2 — Integration, đo trên production qua Cloudflare (H03)

| Bài | Kết quả | Ghi chú |
|---|---|---|
| `/messages` không stream, tools khuôn Anthropic | **200**, `usage.input_tokens=366` | đối chứng |
| `/messages`, tools khuôn OpenAI | **400** `invalid_request`, thông điệp chỉ đúng khuôn | **hồi quy 500 ĐÃ SỬA** |
| `/messages` model sai | **400**, thông điệp nêu đúng ba tên hợp lệ | |
| `/models`, `/tools` | **200** | |
| `/credits/balance` | **200** | dùng làm thước đo tiền |
| `/usage` | **403** `missing_scope: usage:read` | đúng — khoá canary không có scope đó |

### L3 — Failure injection (H06)

| Tiêm | Kết quả đo được | Tiền |
|---|---|---|
| **3 request đồng thời** | 1× **200**, 2× **429** `concurrency_limited` trong **0,83 s** và **1,34 s** | **−1** (chỉ lượt thành công) |
| `Retry-After` trên 429 | **CÓ** — header `retry-after: 15` + thân `"retry_after": 15, "retry": "after_delay"` | |
| **Quá ngữ cảnh, cửa đồng bộ** (510 KB) | **400**, nói rõ *"estimated at 204001 input tokens"* | **0** |
| **Quá ngữ cảnh, cửa stream** | **413**, kèm nguyên văn máy B: `{"tran":96256,"thay":204001}` | **0** |
| **Model không tồn tại** | **400** | **0** |
| **Ngắt kết nối giữa luồng** (đọc 15.872 byte rồi đóng socket) | luồng dừng | **−1** — thu phần đã sinh |

⭐ **Không có silent truncation ở bất kỳ đường nào.** Cả hai cửa đều từ chối,
nêu **con số thật** và **trần thật**. G3 đạt ở điểm quan trọng nhất của nó.

⭐ **Không có hàng đợi ẩn.** 429 trả về trong **dưới 1,4 giây**, không phải sau
khi xếp hàng chờ suất. INV-014 đứng vững.

### L4 — GPU canary

⛔ **KHÔNG CHẠY.** Benchmark D30–D36 là nợ của Prompt 04, và Prompt 08 cấm mở
việc tối ưu mới. Con số hiệu năng trong STATE **vẫn là của một lượt**, chưa
phải một phép thống kê.

### L5 — Client thật

⛔ **VẪN BLOCKED, và tôi phải nói rõ để không ai đọc nhầm.** Tôi gọi
`/api/v1` bằng `urllib` — đó **không phải** canary client thật. E15–E17 hỏi
*"Codex CLI / Claude Code / VS Code có chạy được không"*, và câu đó chỉ trả lời
được bằng chính chúng. `test_290` tồn tại đúng vì một bộ lọc **phía client** đã
khoá cả ô chat trong khi API vẫn trả 200.

---

## 3. Kiểm chứng BỐN chỗ phiên trước tự nêu

### ① *"Mọi số đo đều do tôi tự dựng dụng cụ, tám lần dụng cụ là thứ bị hỏng"*

**XÁC NHẬN, và con số phải tăng.** Tôi tìm thêm **ba** dụng cụ hỏng (F-05, F-08),
và **tự làm hỏng hai phép đo của chính mình** trong phiên này:

| Của tôi | Triệu chứng | Nguyên nhân thật |
|---|---|---|
| "429 **thiếu** `Retry-After`" | header vắng mặt | `dict(msg.headers)` **mất** tính không-phân-biệt-hoa-thường. Header có thật, tên là `retry-after` |
| "Một lượt bị từ chối **có thu** 1 credit" | số dư 1981→1980 qua hai lượt 400/413 | đọc số dư **trước khi** quyết toán của request trước kịp hạ cánh. Đo lại có `sleep(3)`: cả ba đường từ chối đều **+0** |

⭐ Cả hai đều bị bắt bởi **đối chứng**, không phải bởi suy nghĩ kỹ hơn. Cảnh báo
của phiên trước **đúng và phải giữ**.

### ② *"`test_385` xanh trong khi mã hỏng — còn phép kiểm nào cùng hình dạng?"*

**CÓ — ít nhất ba.** Và chúng canh đúng những lỗi đau nhất, loại mà *triệu chứng
không chỉ về phía nguyên nhân*:

| Tệp | Canh điều gì | Kiểm bằng gì |
|---|---|---|
| `test_285_messages_khong_stream` | Claude Desktop **khoá cả ô chat** vì `/messages` từ chối request không stream | `importlib` + đọc thuộc tính module |
| `test_290_ten_tuyen_claude_desktop` | picker model **rỗng**, nút gửi vô hiệu, không log nào | `re` trên mã nguồn |
| `test_360_ban_co_ly_do` | sự cố 31/08, 89 lượt hỏng, không một dòng nói vì sao | `inspect.getsource` |

⛔ Nhưng phải nói cho **hẹp và đúng**: kho này **có** giàn kiểm HTTP thật —
`test_272_cua_streaming` (23 phép kiểm qua `TestClient`, phủ tiền, admission,
cắt giữa luồng, hoàn tiền) và `test_259_cua_dong_bo` (820 dòng). Nên đây
**không** phải "không ai kiểm HTTP"; nó là *"giàn có sẵn mà hồi quy cụ thể vẫn
được chốt ở tầng hàm thuần"*. Cái giá đã trả: một lượt **500 trên production**.
Thuốc rẻ — thêm một ca vào `test_272`.

✅ Và bản thân hồi quy **đã sửa thật**: đo sống 01/09 cho **400** kèm đúng lý do,
đối chứng khuôn Anthropic cho **200**.

### ③ *"F05 là SUY RA, không phải QUAN SÁT"*

✅ **ĐÃ ĐÓNG BẰNG QUAN SÁT.** Máy A reboot thật lúc `15:51:28`. Xem §5 và
`reports/06` §12 (bảng đã viết lại).

### ④ *"`--lan 5` A/B chưa chạy"*

⛔ **VẪN CHƯA.** Đó là nợ của Prompt 04/06 và nằm ngoài quyền của reviewer mode.
Con số `9/12 → 0/12` vẫn phải đọc là **một lượt**.

---

## 4. Phát hiện MỚI — tám mục phiên trước không liệt kê

> Danh sách bốn chỗ của phiên trước **không đầy đủ**, đúng như cảnh báo trong
> chính lời bàn giao. Tám mục dưới đây đều là quan sát trên runtime hoặc mã sống.

### 🔴 F-01 (P2) — Một bất biến TIỀN được đánh dấu `VERIFIED-LIVE` bằng một cột **luôn bằng 0**

`request.state.api_credit_delta` **chỉ** được gán ở `server/api/jobs.py:391,475`.
`server/api/streaming.py` và `server/api/chat.py` **không gán nó lần nào** —
đếm được: `0` lần trong mỗi tệp. Nên cột `credit_delta` của `ApiRequestLog`
**luôn** là `0` cho cửa stream và cửa đồng bộ, bất kể có thu tiền hay không.

STATE chứng minh INV-003 bằng: *"sự cố 31/08: 89 lượt hỏng, `credit=+0` mọi
dòng"*. 89 lượt đó là `/api/v1/responses` — **cửa stream**. Cột ấy sẽ đọc `+0`
**kể cả khi mọi lượt đều bị thu tiền**. Đó là một bằng chứng **không thể sai**,
và bằng chứng không thể sai thì không chứng minh gì.

**Hệ quả rộng hơn cột đó:**

- `platform_core/public_api/anomalies.py` cộng `credit_delta` để dò **bất thường
  tiền** ⇒ mù với hai cửa khách dùng nhiều nhất (F15).
- `platform_core/public_api/admin_console.py` báo credit theo khoá ⇒ **báo thiếu**.

✅ **INV-003 vẫn ĐÚNG — tôi đo lại bằng sổ thật, không bằng cột đó:**

```
3 request dong thoi -> 1x 200, 2x 429 concurrency_limited
so du: 1982 -> 1981   (dung -1: chi luot thanh cong bi thu)
429 kem header retry-after: 15
```

⇒ Kết luận đúng, **bằng chứng cũ phải thay**.

### 🔴 F-02 (P2, và là chỗ làm G6 hỏng) — Ta công bố cho khách một ngữ cảnh không có thật

`GET /api/v1/models` trả về, cho `ltt_llm_vision`:

> *"Same model plus image reading, **same 89K usable input context**."*

Trần thật là **65.536**. Đo sống, cùng một thân request:

```
ltt_llm_vision  -> 413  {"tran":65536,"thay":71281}
ltt_llm         -> 200  (input_tokens that = 52.810)
```

Chuỗi nguyên nhân, cả ba mắt đều kiểm được:

1. `llm_gateway/catalog.py:72` — `qwen38-vision` có `max_context=65_536`;
2. `llm_gateway/api.py:222` — máy B cưỡng chế `min(cfg.max_input_tokens, spec.max_context)`;
3. **máy A không đọc `max_context` theo model ở đâu cả** — `grep` toàn
   `platform_core/`, `server/`, `apps/` cho **0** kết quả. Máy A chỉ biết **một**
   trần chung `96.256`.

⭐ **Phòng thủ nhiều lớp thì ĐẠT** — máy B từ chối sạch, không cắt trộm ngữ cảnh.
Hỏng là ở **lời hứa**: khách dựng client theo 89K sẽ ăn 413 ở khoảng 65K, với
một thông điệp không nói rằng model **này** hẹp hơn model kia.

### 🔴 F-03 (P2) — Bản sao ngữ cảnh **thứ năm**, tới tay khách, không ai canh

`server/api/tools.py:30` — `CUA_SO_CONG_BO_MAC_DINH = 60_000` — đi thẳng ra
`context_window` và `max_context_window` của `/api/v1/models`.

Ba điều cùng lúc:

1. **Một phản hồi, hai con số khác nhau cho khách**: phần chữ nói `89K`, trường
   máy đọc được nói `60000`.
2. **Chính chú thích của nó đã lỗi thời**: nó viết *"cổng của B chặn ở
   `LTT_LLM_MAX_INPUT_TOKENS` (65.000 lúc đo 29/08)"* — nay là **96.256**. Và
   nó tự đặt ra luật *"Đổi trần bên B thì đổi luôn số này"*; luật đó **đang bị
   vi phạm**.
3. **Bánh cóc bỏ sót đúng nó.** `test_334::TestBanSaoConLai` canh
   `TOKEN_RA_TOI_DA` **trong cùng tệp ấy**, cách 20 dòng — nhưng không canh
   hằng số này. Nên D-01-4 (*"bốn bản sao... hai tới tay khách, ghép bằng phép
   kiểm"*) còn một lỗ, và lỗ đó **cũng** tới tay khách.

⭐ Hướng lệch là **an toàn** (công bố thấp hơn trần thật), nên đây không phải P1.
Cái giá là khách dùng Codex bị nén ngữ cảnh sớm hơn cần, mất ~36K token đã trả tiền.

### 🔴 F-04 (P2) — `planner` hứa "model nhà đi trước" nhưng **chưa bao giờ dùng được model nhà**

`platform_core/agent/planner.py` khai:

```python
PLANNER_PROVIDERS = ("ltt_llm", "gemini")
PLANNER_MODEL_THEO_PROVIDER = {"ltt_llm": "ltt_llm", "gemini": PLANNER_MODEL}
```

và tự chú thích: *"⭐ MODEL NHÀ ĐI TRƯỚC. Nó rẻ hơn nhiều."*

Nhưng `"ltt_llm"` là **bí danh công khai**, không phải id model nội bộ.
`apps/ltt_llm/features.py:39` — `ALIAS_SANG_ID = {"ltt_llm": "qwen38-api", ...}`
— và đường khách thật (`features.py:260`) gửi đi **`qwen38-api`**. Registry chỉ
khai `['qwen38-api', 'qwen38-vision']`.

Đo được trong **một tiến trình, một phiên DB** (`tools/kiem_ltt_llm.py`):

```
2. So khoa
  [DAT ] api_pool cap duoc khoa             <- hoi KHONG kem model
3. Goi that qua dieu_phoi
  [HONG] khong cap duoc key (ThieuKeyError) <- hoi KEM model="ltt_llm"
```

⇒ Nhánh `ltt_llm` của planner **luôn** ném `ThieuKeyError`, `dieu_phoi` đọc đó
là *"provider này không phục vụ được, đi tiếp"* và **mọi** lượt lập kế hoạch rơi
xuống **Gemini** — một provider ngoài, trả tiền. Không một dòng log nào nói.

Đường sống: `apps/agent/routes/assistant.py:39,105` và
`apps/agent/routes/legacy_runs.py:63`.

⭐ **Gốc rễ là một chú thích.** Docstring của chính `dieu_phoi.goi` dạy sai quy
ước:

```
model_theo_provider={"ltt_llm": "ltt_llm", "gemini": "gemini-2.5-flash"}
```

Hai nơi chép theo nó (`planner.py`, `kiem_ltt_llm.py`) và **cả hai đều hỏng**.
Sửa docstring là sửa nguồn, không phải sửa triệu chứng.

### 🟡 F-05 (P3) — `tools/kiem_ltt_llm.py` **không bao giờ có thể xanh**, và nó đỏ về phía báo động

Cùng lỗi bí danh với F-04. Công cụ này nằm trong danh sách trắng của
`chay_voi_env.ps1` (`-Viec kiem-llm`), tức được trình bày như một dụng cụ nghiệm
thu. Nó in `[HONG] goi duoc` — đọc lên y hệt *"nền tảng không gọi được máy B"*,
trong khi production đang phục vụ bình thường (đo cùng lúc: `/messages` trả 200).

✅ Nó **không** làm hỏng kết luận nào: `grep` toàn `docs/audit_ltt_llm/` cho **0**
lần trích dẫn. Đây là **cái bẫy cho phiên sau**, không phải một kết quả đã nhiễm.

### 🔴 F-06 (P2) — Có MỘT đường tới máy B **không đi qua admission** (trả lời red-team Q1)

`planner.py:63` gọi thẳng `dieu_phoi.goi(...)`. Không `admission.acquire`.
Ba đường còn lại đều có: `streaming.py:213,614`, `chat.py:188`,
`job_runner.py:226,1250`.

- **Hiện tại vô hại** vì F-04 làm nhánh `ltt_llm` không bao giờ đi tới B.
- ⛔ **Sửa F-04 sẽ KÍCH HOẠT nó.** Hai lỗi đang che nhau, và cái che sắp được gỡ.
- Tài nguyên vẫn an toàn: `gioi_han` của máy B (`max_dong_thoi=1`) là lớp chặn
  cuối. Nhưng sổ admission **của máy A** sẽ không thấy lưu lượng planner ⇒ một
  request khách trả tiền có thể ăn 429 vì một lượt lập kế hoạch nội bộ, và
  không ô đếm nào giải thích được vì sao.

### 🔴 F-07 (P1 — đề nghị **mở lại**, STATE đang ghi `MITIGATED`) — bộ dò "health xanh giả" **không ai chạy**

`tools/soi_cong_llm.py` phát hiện được ca `/health` xanh trong khi tiến trình
cổng đã mồ côi. Tìm khắp kho: **không** scheduled task, **không** mục trong
`_mot_luot_bao_tri`, **không** caller nào ngoài `test_370`.

Đo trên máy thật:

```
Get-ScheduledTask  ->  LTTStudioBackup · LTT_Audit_multiproc · LTT_Audit_test214
                       (khong co muc nao goi soi_cong_llm.py)
```

⛔ **`MITIGATED` là một từ quá mạnh cho việc này.** Một bộ dò không ai chạy thì
giảm nhẹ được **0**. Năng lực thì có, **chốt kiểm soát** thì chưa.

⭐ Và lane này **biết** cách đặt lịch — nó đã tạo hai task audit ở trên. Nên
thiếu sót là **cụ thể**, và thuốc là **một task nữa theo đúng khuôn đã có**.

### 🟡 F-08 (P3) — `tools/do_sau_khoi_dong.py`: một câu sai và một nhãn sai

Chi tiết + bằng chứng: `docs/audit_ltt_llm/evidence/N7_N9_SAU_KHOI_DONG_2026-09-01.md`.

- **§3** kết luận `"KHONG DOC DUOC (can Administrator)"` khi truy vấn trả rỗng.
  Chạy lại **bằng LocalSystem** cho kết quả **y hệt**: Windows máy này không ghi
  sự kiện 7036, `3` sự kiện SCM tổng cộng, `0` khớp. Công cụ tránh bẫy
  "rỗng đọc lên như không-có-sự-kiện" bằng cách nói **một câu sai khác**.
- **§4** nhan đề *"Bao lâu tới khi `/health/ready` xanh"* nhưng đặt `t0` lúc
  **gọi công cụ**. Ở boot+7 phút in `0,5 s`; ở boot+15 phút in `0,6 s`. Cả hai
  là độ trễ một request, không phải thời gian phục hồi.

---

## 5. N7 / N9 — reboot máy A, đo bằng quan sát

Máy A khởi động lại **15:51:28.500** (`Win32_OperatingSystem.LastBootUpTime`).

| Mốc | Từ lúc boot | Nguồn |
|---|---:|---|
| 5 vỏ bọc NSSM sinh ra (cả 5 cùng lúc) | **+15,7 s** | `Win32_Process.CreationDate` |
| Worker báo `chay 2 tien trinh worker: da nang x2` | **+19,7 s** | `logs/ltt-job-worker.jsonl` |
| cloudflared precheck PASS toàn bộ | +19,5 s | `logs/cloudflared-nssm-err.log` |
| cloudflared đăng ký **4** tunnel connection | **+20,5 s** | cùng trên |
| Dịch vụ phải nhờ `FAILURE_ACTIONS` dựng dậy | **0** | toàn bộ System log từ boot |

- **N7 ĐẠT.** 5/5 `StartMode=Auto`, `Status=Running`, không ai can thiệp.
- **N8 ĐÓNG — và dòng cũ đã SAI.** `sc.exe qfailure` dưới LocalSystem: **cả 5**
  dịch vụ đều có `reset=86400` + `RESTART`. `bat_tu_dung_day.ps1` đã chạy rồi.
- **N9 ĐẠT nhưng KHÔNG bằng đường đã định** — xem F-08.
- ⚠️ **Một số vĩnh viễn mất ở lượt boot này:** *boot → `/health/ready` xanh lần
  đầu*. Chặn trên đã biết: **+19,7 s**.

---

## 6. Mười lăm câu red-team

| # | Câu hỏi | Trả lời (evidence-first) |
|---:|---|---|
| 1 | Đường GPU/provider nào lách admission? | **CÓ MỘT** — `planner.py` (F-06). Hiện vô hại vì F-04; sửa F-04 là kích hoạt |
| 2 | Thu tiền nào không dựa trên sự thật đo được? | **KHÔNG** — `gia_token.tinh` ném `KhongDoDuocError`; đo sống: thành công −1, mọi đường từ chối +0 |
| 3 | Thử lại / thu hai lần? | **KHÔNG** — `_giu_cho_da_niem_phong` + khoá số dư; replay idempotency đo được (phiên trước): cùng job id, trừ 0 |
| 4 | Hàng đợi ẩn? | **KHÔNG** — 429 trả trong **0,83 s / 1,34 s** |
| 5 | Cắt ngữ cảnh im lặng / trôi ngữ cảnh? | **Cắt: KHÔNG.** **Trôi: CÓ** — F-02 và F-03, cả hai tới tay khách |
| 6 | Tuyên bố năng lực vượt bằng chứng? | **CÓ** — F-02 (`89K` cho vision, thật `65.536`) |
| 7 | Bí mật thừa trên máy B? | **KHÔNG** — `gateway.env` có đúng 12 biến `LTT_LLM_*`, một token là của chính nó. Không mật khẩu DB, không khoá R2, không `LTT_TOKEN_ENCRYPTION_KEY` |
| 8 | Health xanh khi dịch vụ vi phạm SLO? | **CÓ, và không ai dò** — F-07 |
| 9 | Ngắt kết nối có đốt tiền trái hợp đồng? | **KHÔNG** — thu **−1**, đúng phần đã sinh |
| 10 | Bận có đầu độc health/cooldown của provider? | **KHÔNG** — khoá `ltt_llm` vẫn `active` sau các lượt 429 của tôi (`soi-su-co`: `trang_thai=active`) |
| 11 | Đổi model có hại workload người khác? | Không quan sát được lượt đổi nào trong phiên này — **giữ nguyên kết luận Prompt 03** |
| 12 | Khởi động lại có dùng cấu hình cũ? | **KHÔNG** — đĩa `-c 131072` == tiến trình `-c 131072`; máy A boot lại và khớp kho 7/7 |
| 13 | Deploy lệch một máy có gây bất tương thích câm? | Không đo mới; INV-016 (`VERIFIED-LIVE` 31/08) giữ nguyên |
| 14 | Rollback thi hành được hay chỉ trên giấy? | **Máy B: CÓ** (diễn tập 18,9 s, Prompt 06). **Máy A: CHƯA** — tài sản đủ (`app.previous` 13:26 + `rollback.ps1` đọc qua thấy mạch lạc) nhưng **chưa diễn tập**; diễn tập là cắt production |
| 15 | Phép kiểm nào còn mock đi chính thứ nó tuyên bố? | **Ba** — `test_285`, `test_290`, `test_360` (§3②) |

---

## 7. MVP gates & score

| Gate | Kết luận |
|---|---|
| **G1** Execution correctness | ⚠️ **ĐẠT CÓ ĐIỀU KIỆN** — một đường lách admission (F-06), hiện vô hại, máy B là lớp chặn cuối |
| **G2** Money correctness | ✅ **ĐẠT** — đo lại trên **sổ thật**: thành công −1, bận/từ chối/quá ngữ cảnh +0, ngắt kết nối thu đúng phần đã sinh |
| **G3** Context correctness | ⚠️ **MỘT PHẦN** — không cắt im lặng (đạt phần khó nhất), nhưng trần công bố sai ở **hai** chỗ (F-02, F-03) |
| **G4** Machine B correctness | ✅ **ĐẠT** — auth/allow-list/413 trước GPU, bận ≠ hỏng, cấu hình đĩa == đang chạy, không bí mật thừa |
| **G5** Model usefulness | ⏸️ **KHÔNG ĐO LẠI** — giữ 12/12 của Prompt 04, confidence hạ xuống MEDIUM (n=1) |
| **G6** Protocol truthfulness | ❌ **HỎNG** — F-02 |
| **G7** Operations | ⚠️ **MỘT PHẦN** — F-01 (mù tiền ở 2 cửa), F-07 (bộ dò không lịch chạy) |
| **G8** Evidence | ⚠️ **MỘT PHẦN** — một bất biến critical dựa trên bằng chứng vô hiệu (F-01); ba phép kiểm mock đi thứ chúng tuyên bố |

*G1–G4 không có gate nào hỏng ⇒ `NOT READY` không được kích hoạt.*

| Domain | Trọng số | Trước (STATE) | **Sau (P08)** | Vì sao đổi |
|---|---:|---:|---:|---|
| Correctness & invariants | 20 | 17 | **16** | F-06 + F-04 |
| Money/admission/failure | 15 | 15 | **14** | tiền ĐÚNG, nhưng thứ canh nó mù (F-01) |
| Model quality & context fidelity | 15 | 12 | **12** | không đo lại |
| Performance/resource | 15 | 11 | **11** | không đo lại |
| Reliability/recovery | 10 | 8 | **9** | F05 nay là quan sát (+), F-07 (−) |
| Security boundaries | 10 | 9 | **9** | xác minh lại bí mật máy B |
| Observability/operations | 5 | 5 | **3** | F-01 + F-07 |
| Tests/evidence/reproducibility | 5 | 5 | **3** | F-01 + ba phép kiểm cùng hình dạng |
| Maintainability/SSOT/deployment | 5 | 5 | **4** | F-03 — bản sao thứ năm |
| **TOTAL** | **100** | 87 | **81** | |

**Confidence: HIGH** cho phần tôi đo (G1–G4, G6–G8); **MEDIUM** tổng thể, vì
G5 và toàn bộ hiệu năng không được đo lại trong phiên này.

⛔ **81 không phải "tụt hạng".** 87 và 81 **không so được trực tiếp** — 87 do
người thi hành tự chấm, 81 do người nghiệm thu chấm sau khi loại một bằng chứng
vô hiệu và tìm thêm tám mục. Phần lớn chênh lệch nằm ở **quan sát**, không ở
hỏng mới sinh.

---

## 8. Nợ còn lại

| P | Nợ | Bằng chứng | Tác động | Thí nghiệm tiếp | Điều kiện / không-trước-khi |
|---|---|---|---|---|---|
| **P1** | F-07 — bộ dò health xanh giả không có lịch chạy | `Get-ScheduledTask`: 0 mục | ca đã đo thật 01/09 kéo 99 s không ai biết | thêm 1 Scheduled Task theo khuôn `LTT_Audit_*` | làm được ngay |
| **P2** | F-02 — công bố `89K` cho vision, thật `65.536` | 413 sống, `{"tran":65536}` | khách dựng client theo số sai | máy A đọc `max_context` **theo model**; sửa `description` | cần quyết: hạ công bố hay nâng `-c` của vision |
| **P2** | F-01 — `credit_delta` không được ghi ở 2/3 cửa | `grep`: 0 lần trong `streaming.py`, `chat.py` | dò bất thường tiền mù ở 2 cửa đông nhất | gán `api_credit_delta` ở hai cửa; rồi chạy lại `anomalies` | làm được ngay |
| **P2** | F-04 — planner không bao giờ dùng model nhà | `ThieuKeyError` đo được | mọi lượt lập kế hoạch tiêu quota Gemini | sửa docstring `dieu_phoi.goi` **trước**, rồi hai caller | ⛔ **KHÔNG sửa trước F-06** |
| **P2** | F-06 — planner lách admission | `grep`: không `acquire` | sẽ kích hoạt khi F-04 được sửa | bọc planner trong admission | **không-trước-khi**: cùng lượt với F-04 |
| **P2** | F-03 — bản sao ngữ cảnh thứ năm không ai canh | `test_334` bỏ sót | khách nhận 2 số khác nhau trong 1 phản hồi | thêm 1 assert vào `TestBanSaoConLai` | làm được ngay |
| **P2** | Ba phép kiểm cùng hình dạng `test_385` | §3② | hồi quy client-facing lọt lưới | thêm ca HTTP vào `test_272` (giàn đã có) | làm được ngay |
| **P3** | F-05 — `kiem_ltt_llm.py` không thể xanh | step 2 vs step 3 | bẫy cho phiên sau | sửa cùng F-04 | |
| **P3** | F-08 — `do_sau_khoi_dong.py` §3 sai lý do, §4 sai nhãn | evidence file | chẩn đoán sai sau lần reboot tới | §3 nói "không có sự kiện"; §4 đổi tên hoặc đo từ boot | trước lần reboot kế |
| **P3** | E15–E17 canary client **thật** | chưa chạy | `test_290` chứng minh API-200 ≠ client-chạy-được | chạy Codex CLI + Claude Code thật | cần chủ sản phẩm cấp khoá cho máy khách |
| **P3** | Benchmark D30–D36 · `--lan 5` | chưa chạy | hiệu năng vẫn n=1 | nợ Prompt 04/06 | ngoài quyền reviewer mode |
| **P3** | Diễn tập rollback **máy A** | chưa chạy | rollback A vẫn là lý thuyết | `rollback.ps1` trên root cô lập trong `tmp` | diễn tập thật cắt production |

---

## 9. Tóm tắt một trang

**Hệ thống `ltt_llm` đang phục vụ khách trả tiền, và phần khó nhất của nó
đúng.** Tiền đúng tới từng credit trên sổ thật; không có hàng đợi ẩn; không có
lần cắt ngữ cảnh im lặng nào; máy B từ chối sạch trước khi chạm GPU và giữ đúng
một suất; máy A khởi động lại sau 20,5 giây mà không ai chạm vào. Hồi quy 500
mà phiên trước tự khai đã **thật sự** được sửa — tôi kiểm bằng một lượt gọi thật
và một đối chứng.

**Thứ không đúng, gần như tất cả, là những gì hệ thống *nói về chính nó*.** Ta
công bố cho khách một cửa sổ ngữ cảnh vision không tồn tại. Ta đưa hai con số
ngữ cảnh khác nhau trong cùng một phản hồi. Một bất biến tiền quan trọng được
đóng dấu `VERIFIED-LIVE` dựa trên một cột **luôn bằng 0** ở đúng cái cửa mà bằng
chứng nói tới. Một bộ dò sự cố được viết, được kiểm, rồi **không ai gọi**. Một
module hứa dùng GPU nhà và **chưa từng gọi được nó một lần**, âm thầm tiêu quota
của nhà cung cấp ngoài — vì một **docstring** dạy sai quy ước, và hai nơi chép
theo.

**Đó là một dạng nợ dễ chịu hơn nợ kiến trúc: ba trong tám mục sửa bằng một
dòng, và không mục nào đòi chạm tới hình dạng hệ thống.** Nhưng nó cũng là dạng
nợ nguy hiểm nhất cho phiên sau, vì nó **đọc lên như sự thật**.

⭐ **Bài học sắc nhất của lượt nghiệm thu này lặp lại đúng cảnh báo của phiên
trước, chỉ ở một tầng cao hơn.** Phiên trước phát hiện *dụng cụ đo* của mình
hỏng tám lần. Tôi tìm thêm ba dụng cụ hỏng — và **tự làm hỏng hai phép đo của
chính mình** trong vài giờ, cả hai đều cho ra một *khuyết tật nghe rất thuyết
phục* mà không có thật (một header "thiếu", một lượt từ chối "có thu tiền").
Cả hai bị bắt bởi **đối chứng**, không bởi cẩn thận hơn.

⇒ Khuyến nghị vận hành, không phải khẩu hiệu: **mọi phép đo trong chương trình
này phải có một đối chứng chạy trước, và đối chứng trượt thì phép đo phải DỪNG
thay vì báo một con số.** Lane này đã làm đúng điều đó ở `do_duong_tien_api.py`
(`ct-00`); nó nên là luật cho mọi dụng cụ, không phải cho một dụng cụ.

**Verdict: `CONDITIONAL PASS`** — không P0, G1–G4 đứng vững, nhưng một tuyên bố
năng lực sai đang tới tay khách và ba loại bằng chứng sống quan trọng vẫn chưa
có. Điều kiện để lên `FINAL PASS`: đóng F-02 và F-07, thay bằng chứng của F-01,
rồi chạy **một** canary bằng client thật.

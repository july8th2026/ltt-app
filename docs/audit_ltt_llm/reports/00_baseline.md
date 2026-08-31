# Prompt 00 — Discovery & Frozen Baseline

**31/08/2026.** Chế độ: **ĐỌC / ĐO / BÁO CÁO**. Không sửa mã sản phẩm.

> Bản tóm tắt bàn giao ở `../STATE.md`. Tệp này giữ bằng chứng chi tiết.

---

## 1. Cổng ra

**`BASELINE FROZEN`** — với hai điều kiện khai rõ, không làm tròn lên:

* **Benchmark hiệu năng: `PENDING LIVE`.** Chưa đo một con số nào. Prompt 04
  không được tuyên bố "nhanh hơn/chậm hơn" nếu không dựng mốc tương đương.
* **Baseline là ảnh chụp của một hệ thống vừa được vá vài giờ trước** (§7).

---

## 2. Hệ thống thực tế — bản đồ đo được, không theo tên tệp

`apps/ltt_llm` chỉ **810 dòng**. Gần như toàn bộ đường thi hành nằm nơi khác:

| Tầng | Dòng | Tệp chính |
|---|---:|---|
| App | 810 | `features` 276 · `manifest` 251 · **`ngan_sach` 181** · `executor` 54 · `jobs` 47 |
| Miền dùng chung | 1.542 | `luong_vlm` 282 · `cong_vlm` 269 · `dieu_phoi` 237 · `admission` 201 · `thanh_toan` 183 · `dem_token_luong` 180 · `gia_token` 163 |
| HTTP công khai | 3.877 | `streaming` 947 · `jobs` 479 · `chat` 320 · `auth` 273 · `guard` 229 |
| Cổng máy B | 1.987 | `api` 366 · `gioi_han` 258 · `ngan_sach` 255 · `trong_tai` 206 · `don_dep` 199 |

⇒ **Phạm vi thật ~8.200 dòng trên hai máy.** Audit chỉ `apps/ltt_llm` sẽ bỏ sót
gần hết đường thi hành.

**Bộ test hiện có: 215 phép kiểm / 11 tệp** — `test_250` 35 · `test_251` 22 ·
`test_254` 15 · `test_256` 22 · `test_257` 8 · `test_258` 22 · `test_259` 35 ·
`test_272` 23 · `test_313` 20 · `test_334` (8 lớp) · `test_363` 13.

---

## 3. Định danh runtime (D01–D06)

```
Qwen3.8-27B-UD-Q4_K_M.gguf   15,33 GB
mmproj-F16.gguf               0,86 GB
llama-server   0.3.0-dev build 10689 commit 57291f264 (Clang 20.1.8)
llama-swap     v250 (60226b6) built 2026-08-14T15:46:44Z
GPU            RTX 3090, driver 610.88, 24.576 MiB
```

Cờ đang chạy (`H:\LTT_LLM\gateway\llama-swap.yaml`):

```
--jinja --chat-template-file .../chat_template.jinja --reasoning-format deepseek
-fa 1 -ngl 999 --parallel 1 --spec-type draft-mtp --spec-draft-n-max 2
-c 131072 --cache-type-k q8_0 --cache-type-v q8_0
healthCheckTimeout: 600
```

⚠️ **`--spec-type draft-mtp` đang bật.** Đó là speculative decoding (D23) — một
biến chưa được đo, và nó ảnh hưởng cả tốc độ lẫn chất lượng. Prompt 04 phải đo
nó **một biến một lần**, không gộp với knob khác.

---

## 4. Bốn cửa, và thứ tự thật của cửa stream

```
POST /api/v1/quotes -> /jobs        ASYNC_JOB     server/api/jobs.py
POST /api/v1/chat/completions       SYNC_BILLED   server/api/chat.py
POST /api/v1/messages               STREAM        server/api/streaming.py
POST /api/v1/responses              STREAM        server/api/streaming.py
```

Thứ tự trong cửa stream (`streaming.py`), đo bằng đọc mã:

```
580  admission.acquire(...)         ve nhan vao
633  thanh_toan.giu_cho_luot(...)   giu tien
650  db.commit()                    CHOT GIAO DICH truoc khi cham model
655  luong_vlm.mo(...)              mo luong toi may B
690  StreamingResponse(_phat(...), background=BackgroundTask(release))
```

⭐ Thứ tự này **đúng**: nhận vào → giữ tiền → chốt giao dịch → mới chạm model.
Giữ giao dịch mở suốt lượt gọi sẽ giữ luôn một kết nối CSDL, và tiến trình chết
giữa chừng sẽ cuộn mất phần giữ chỗ.

---

## 5. Mâu thuẫn tìm được (§5 của Prompt 00)

### C-01 — Trần `65K` đã chết, còn ở 6 chỗ, và **tới tay khách**

```
llm_gateway/deploy/llama-swap.yaml:130
    description: "Coding, chat, agent, tom tat. Engine 131K; input public 65K."
                                                            ^^^^^^^^^^^^^^^^^
llm_gateway/api.py:181        "description": m.mo_ta      <- phoi qua /v1/models
```

Trần thật: `TOKEN_VAO_TRAN = 96_256`; công bố cho client `88_555`.

Sáu chỗ: `apps/ltt_llm/manifest.py:30` · `llm_gateway/catalog.py:32` ·
`llama-swap.yaml:111, 117, 130` · và `-c 65536` dòng 184 (hồ sơ vision — đây là
một **cấu hình thật**, không phải chữ, nên nó là câu hỏi riêng cho Prompt 03).

⛔ Prompt 00 §5 gọi đích danh *"stale 65K/other historical caps"*. Đây là nó.
**Không sửa ở phase này** — ghi nhận, để Prompt 01 quyết.

### C-02 — Đồng thời máy B có hai nguồn

`apps/ltt_llm/ngan_sach.py:167` `DONG_THOI_MAY_B = 1` là **bản sao** của
`max_dong_thoi = 1` bên `llm_gateway/gioi_han.py`. `test_334` có ba lớp đối
chiếu; Prompt 01 phải xác minh chúng phủ **đúng con số này**.

### C-03 — Lỗi ở công cụ đo của tôi, không ở hệ thống

Bộ lọc che bí mật của tôi dùng mẫu `TOKEN` nên che nhầm `LTT_LLM_MAX_INPUT_TOKENS`
và `MAX_OUTPUT_TOKENS` — hai giá trị **không phải bí mật** (96.256 / 32.768).
Ghi ra để bản đọc sau không tưởng chúng bị giấu.

---

## 6. Bằng chứng test đóng băng

### 6.1 Cổng chất lượng đầy đủ

```
python tools/gate.py --phien a5
RESULT: PASS  [1 BUOC TU BO QUA, KHONG PHAI BANG CHUNG: bat bien da tien trinh]
  [BOQUA] bat bien da tien trinh          0.7s
  [PASS]  bo test (song song)           293.8s
  + 3 bo frontend xanh, 20 buoc tinh xanh
```

Không có khối `CAY DA DOI` ⇒ đo trên cây đứng yên.

### 6.2 `test_214` — bất biến đa tiến trình, **lần đầu chạy trên máy này**

```
7 passed in 134.61s (0:02:14)
```

Đường đi, vì nó tái dùng được:

1. `secrets\app.env` bị ACL + lớp quyền phiên chặn ⇒ cầu hẹp
   `setup/chay_voi_env.ps1` (nạp env vào riêng tiến trình, **bốn việc trong danh
   sách trắng**, không in giá trị nào).
2. Chạy nó bằng **Nexus trên máy A** — agent chạy LocalSystem, đọc được `secrets\`.
3. ⛔ **`Start-Process` tách rời từ một lượt `exec` Nexus chết theo phiên.** Tôi
   để nó "chạy" 40 phút rồi mới đo CPU: tất cả ≈ 0 giây, không có `python.exe`
   nào. Nó chưa bao giờ chạy. Phải dùng **Scheduled Task**.

### 6.3 🔴 Hai tầng bỏ qua chồng lên nhau — số đo đắt nhất của phase này

`gate.py` chỉ đọc **mã thoát**. `check_multiproc.py` không tạo được CSDL test,
in một đoạn giải thích rất tử tế, rồi `return 0` ⇒ gate in `[PASS]` trong 0,7 s.

**Hệ quả đo được: hai phiên đọc cùng một dòng `RESULT` theo hai cách trái ngược
trong cùng một ngày, và cả hai đều tưởng mình đúng.**

Nhưng sửa tầng đó **chưa lộ ra tầng dưới**. Chạy `pytest` thẳng vào `test_214`
với env production đầy đủ:

```
sssssss    7 skipped in 0.26s
```

Bảy phép kiểm, bảy chữ `s` — chúng đòi `LTT_TEST_DATABASE_URL`, một **CSDL test
riêng**, và **từ chối chạy trên CSDL production**. Nó đúng khi từ chối.

⛔ ⇒ **Đừng thay `check_multiproc.py` bằng một lệnh `pytest` "tương đương".**
Công cụ ấy không phải lớp bọc — nó là thứ **tạo ra** CSDL test. Gọi pytest thẳng
trông như đường tắt sạch hơn và trả về bảy chữ `s` trong 0,26 giây: **nhanh,
xanh, và rỗng.**

---

## 7. 🔴 Baseline này là ảnh chụp của một hệ thống vừa được vá

Sáng 31/08 cổng VLM **rò một suất** và ngừng phục vụ **hơn sáu giờ** (89/117 lượt
của một khách hỏng). Bản vá ba lớp deploy lên cả hai máy lúc 18:1x–18:5x —
**trước** khi baseline này được chụp.

Trạng thái trước-vá **không lấy lại được**. Baseline vẫn hợp lệ vì nó *là*
production hiện tại, nhưng mọi so sánh hiệu năng ở Prompt 04 phải neo vào mốc
này, **không** vào bất kỳ số đo nào trước 31/08.

Chi tiết: `docs/VLM_NOI_BO/SU_CO_2026-08-31_RO_SUAT.md`.

---

## 8. Điểm baseline: **69/100**, confidence **MEDIUM**

Bảng đầy đủ ở `../STATE.md`. Hai điều cần đọc kèm:

⛔ **69 không có nghĩa "hệ thống tệ".** Phần lớn điểm trừ là **thiếu phép đo**,
không phải hỏng đã biết:

* **G5 (chất lượng model) — 6/15, không có chủ sở hữu nào.** Kho có
  `bench_llm_admission.py`, `nghiem_thu.py`, `cham_mu.py`, nhưng **không có bộ
  đánh giá chất lượng LLM nào**. Không đo được chat · coding · tool calling ·
  long-context · tiếng Việt · vision. Đây là khoảng trống lớn nhất, và nó là thứ
  phải **xây**, không phải thứ để audit rồi ghi KEEP.
* **Hiệu năng — 7/15, mọi số `PENDING LIVE`.**

⭐ Ngược lại, **tiền được 13/15 với confidence HIGH**, và đó là điểm có bằng
chứng sống chứ không phải bằng chứng giấy: trong sự cố 89 lượt hỏng, `credit=+0`
ở **mọi dòng**, `Retry-After` gửi đủ, và khoá `ltt_llm` vẫn `active` (bẫy D-005
đã tránh được).

---

## 9. Việc phase sau phải làm, theo thứ tự đề nghị

**00 → 03 → 04 → 01 → 02 → 05 → 06 → 07 → 08**, đổi so với gói.

Lý do: 03 và 04 tự chủ **100 %** (máy B điều khiển đầy đủ qua Nexus), **máy B
đang rảnh** — một điều kiện có thể mất bất cứ lúc nào khi dự án video chạy lại —
và G5 là khoảng trống lớn nhất. Gói cấm chạy song song và cấm bỏ 00/08: giữ
nguyên cả hai.

🔴 **Prompt 08 phải do một phiên khác chạy.** Gói gọi nó là *independent final
acceptance*; nếu cùng một phiên thi hành 00–07 rồi tự nghiệm thu thì chữ
"independent" chỉ còn là trang trí.

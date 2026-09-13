# 09 — QUYẾT ĐỊNH: `gem` bỏ hẳn lái trình duyệt, đi qua `runtime_noi_bo`

Chủ dự án quyết ngày **2026-09-09**, nguyên văn:

> *"bỏ hẳn đường lái trình duyệt. chỉ sử dụng qua API. vấn đề API này với hệ
> thống LTTstudiosapp của ta sẽ đi theo đường gọi nội bộ `runtime_noi_bo` của
> hệ thống, không cần cài API riêng"*

Đóng `S2`. Kéo theo `S3` (tài khoản chạy E2E) **không còn tồn tại**.

---

## 1. Điều phải nói thẳng trước khi làm

⛔ Quyết định này **thay provider giữa lúc migrate**, đúng thứ MASTER-GUARDRAILS
#6 cấm. Tôi đã nêu; chủ dự án đã quyết. Ghi lại **hệ quả**, không phải để phản
đối, mà để không ai về sau đọc bản audit này rồi tưởng parity của `gem` được đo
như ba App kia:

| | Ba App kia | `gem` sau quyết định này |
|---|---|---|
| Nguồn chân lý hành vi | mã legacy đang chạy | **prompt template + schema đầu ra** |
| Parity đo được không | có — cùng engine, cùng tham số | **không** — đổi cả provider lẫn giao thức |
| Chuẩn nghiệm thu | 100% P0/P1 + ≥95% có trọng số | **hợp đồng đầu ra**, không phải parity |

🔑 Nói cho gọn: `gem` **không còn là một cuộc migrate**. Nó là **viết lại** một
workflow ba bước trên hạ tầng của LTT, giữ lại đúng phần tài sản còn giá trị.

## 2. Cái gì giữ, cái gì bỏ

### GIỮ — đây là tài sản thật, và nó không dính gì tới trình duyệt

| Giữ | Vì sao |
|---|---|
| `data/prompts/step1_character_lock.txt` · `step2_scene_list.txt` · `step3_json_prompt.txt` | **tài sản, không phải mã**. Ba template này là thứ tạo ra giá trị |
| Cấu trúc **ba bước** và thứ tự của chúng | khoá nhân vật → liệt kê cảnh → sinh JSON prompt |
| `HISTORY_SCENES_COUNT = 5` | *"bug cũ: chỉ giữ 2 scene cuối → qua 100+ scenes drift character/style"*. Đây là chống trôi **ngữ cảnh**, không phải chống throttle — nó sống sót qua việc đổi provider |
| Kích thước lô `STEP2=10` / `STEP3=5` | vẫn có nghĩa: kích thước lô đổi chất lượng đầu ra, không chỉ đổi tốc độ |
| Schema JSON đầu ra của bước 3 | hợp đồng với bước sau |

### BỎ — chúng chỉ tồn tại vì phía kia là một trình duyệt

| Bỏ | Vì sao nó vô nghĩa sau quyết định |
|---|---|
| `gemini_client.py` (2.864) · `gemini_automation.py` (2.583) · `chatgpt_automation.py` (1.432 ×2) | ~8.300 dòng lái Selenium |
| `undetected_chromedriver` · `ProfileRotator` · xoay hồ sơ trình duyệt | không còn thứ gì để tránh bị phát hiện |
| `STEP_BATCH_DELAY=8s` · `BATCH_PROGRESSIVE_STEP=+3s` · `BATCH_PROGRESSIVE_CAP=60s` | nhịp chống throttle của **phiên web**. API có hạn mức riêng, và `runtime_noi_bo` đã có **admission** lo việc đó |
| `BATCH_REST_INTERVAL=12` lô / `BATCH_REST_DURATION=45s` | như trên — *"Gemini cho phép ~15-20 prompt/session trước khi throttle"* nói về **session web** |
| `BATCH_NEW_CONV_INTERVAL=25` | "hội thoại mới" là khái niệm của giao diện web. Với API, ngữ cảnh là thứ ta **tự dựng** mỗi lời gọi |
| `test_phase2_stale_element.py` · `inspect_gemini_dom.py` · `dom_inspect_results.json` | DOM không còn tồn tại trong bài toán |
| `S7` — so `gemini_automation` với `gemini_client` | **đóng luôn**: cả hai đều bỏ |

⭐ **Sáu hằng số nhịp bị bỏ, nhưng KHÔNG phải vì chúng vô giá trị.** Chúng là
bản ghi của một cuộc chiến với hệ thống chống bot. Chúng chết cùng chiến trường
ấy. `HISTORY_SCENES_COUNT` thì khác — nó nói về **ngữ cảnh của mô hình**, nên nó
sống tiếp. Phân biệt được hai loại hằng số này là toàn bộ việc của mục §2 này.

## 3. Đường đi mới — bằng mã có thật

`platform_core/runtime_noi_bo/` là **cửa gọi năng lực AI từ bên trong nền tảng,
không cần khoá API** (H43 Phase 02). Đúng thứ chủ dự án chỉ định.

```
apps/gem/jobs.py::handle(params, ctx)
  └ services/workflow.py            ← ba bước, giữ 5 cảnh lịch sử, lô 10/5
      └ runtime_noi_bo.luong.chuan_bi(db, user_id=..., tool_name="text.chat",
                                      than={...}, duong=...)
         · kiểm alias model → giành suất (admission) → ước token
         · GIỮ CHỖ credit → commit → mở luồng → đếm → quyết toán
      └ luong.mo_luong(...)          ← tiêu tới hết, lấy văn bản
```

⭐ Ba điều đi kèm miễn phí, và cả ba đều là thứ bot legacy **không có**:

1. **Admission** — `runtime_noi_bo` giành suất trước khi chạm model. Đó chính là
   thứ mà `STEP_BATCH_DELAY` đang mô phỏng một cách thô sơ, chỉ khác là nó **đo
   được** và **dùng chung** với mọi sản phẩm khác.
2. **Kế toán token thật** — giữ chỗ, đếm, quyết toán, kẹp không vượt phần đã
   giữ. Bot legacy không tính tiền lần gọi nào.
3. **Không lộ id model** — alias dịch sang id nội bộ **ngay trước khi ra khỏi
   nền tảng**; mã của khách không ghim vào tên model thật.

## 4. Hợp đồng `gem.run` — SỬA so với `24_NODE_CONTRACTS.md`

```
job_type      gem.run                 type_version  1
requires      ("api",)                       ⇐ was ("browser",)
side_effect   none                           ⇐ was "external"
idempotency   key_fields=("kich_ban", "so_canh")   ⇐ was {} (co y de rong)
resource      admission cua `text.chat` lo — App KHONG tu khai suat GPU/browser
```

| Tham số | Kiểu | Bắt buộc |
|---|---|---|
| `kich_ban` | `text` | ✅ |
| `so_canh` | `int` | |
| `batch_step2` / `batch_step3` | `int` | mặc định 10 / 5 |
| `model` | `model_ref` | category `text`, `hidden`, phải có `default` |

`returns` = `{"ket_qua": "json"}`.

🔑 **`side_effect` đổi `external` → `none` là thay đổi có thật, không phải dọn
dẹp.** Bản cũ khai `external` vì mỗi lượt tiêu một suất trong hạn mức phiên của
một tài khoản người thật, và chạy lại **không** miễn phí. Qua `runtime_noi_bo`,
mỗi lượt là một lời gọi có kế toán riêng — nên nó luỹ đẳng được, và `key_fields`
khai được thật thay vì phải để rỗng cho trung thực.

⚠️ `model` phải có `default` vì nó `hidden`: tham số ẩn mà thiếu mặc định thì
tầng API bỏ trống và handler tự chọn — kho này đã có tiền lệ một tool
**storyboard chạy và tính tiền sai nhánh** vì đúng lỗi ấy.

## 5. Nghiệm thu — thay parity bằng hợp đồng

Vì không so được với legacy, chuẩn nghiệm thu của `gem` là:

| # | Mệnh đề | Đo thế nào |
|---|---|---|
| G1 | ba bước chạy đúng thứ tự, đúng template | so prompt gửi đi với tệp `.txt`, từng ký tự |
| G2 | giữ đúng **5** cảnh lịch sử ở lô thứ n | đọc prompt lô n |
| G3 | lô 10 / 5 | đếm mục mỗi lời gọi |
| G4 | đầu ra bước 3 hợp schema | so schema |
| G5 | mỗi lời gọi có giữ chỗ và quyết toán | bút toán credit khớp số lượt |
| G6 | hết credit ⇒ dừng sạch, không nợ | `ThieuCredit` → job lỗi, giữ chỗ được hoàn |
| G7 | máy bận ⇒ về hàng đợi, **không** tính lượt | `DangBan` → `resource_wait` |

⛔ **Không** đòi văn bản do model sinh ra giống bản cũ. Bản cũ đến từ một mô
hình khác qua một giao thức khác; đòi thế là đòi một thứ không tồn tại.

## 6. Thứ tự build

`gem` vẫn đi **cuối** trong bốn App — nhưng lý do đã đổi. Trước: nó bị chặn bởi
ba câu hỏi chưa có lời đáp. Nay cả ba đã đóng, và nó đi cuối vì nó là App **duy
nhất phải viết lại** thay vì port, nên nó hưởng lợi nhiều nhất từ việc ba App
kia đã chứng minh xong hợp đồng App + Macro Node.

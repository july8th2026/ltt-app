# Phase 03 — `video.generate` (Seedance) ra Public API

**Thi hành 2026-08-30.** Trạng thái: **`TECHNICALLY_READY`**, hợp đồng đóng
băng, **operator chưa bật**. Nghiệm thu bằng credential thật: `BLOCKED_EXTERNAL`.

---

## 1. Observed design

Rào cản trong hồ sơ: *"tập tuỳ chọn hợp lệ đổi theo model, chưa publish được một
hợp đồng đúng"*. Đo thật thì `api_contract` **rỗng hoàn toàn**.

Và hai nửa của lời giải **đã tồn tại**, chưa ai nối lại:

| Nửa | Ở đâu | Ai dùng trước đây |
|---|---|---|
| Dữ liệu ràng buộc theo model | `apps/taovideo/models.py` — `aspects`, `durations`, `resolutions`, `supports_seed`, `prompt_controls` | chỉ `routes.py` (form web) |
| Ô công bố ràng buộc | `PublicModel.constraints` — `catalog.py:173,187,347` | **không app nào** |
| Ánh xạ trường ↔ tham số | `params_schema[p] = {"depends_on": "model", "field": "..."}` | registry kiểm lúc đăng ký |

⇒ Việc phải làm không phải *thiết kế một representation*, mà là **nối ba thứ đã
có** rồi thi hành chúng trước khi tiền chuyển.

---

## 2. Chosen implementation

### 2.1 Hợp đồng **sinh** từ `models.py`

`_hop_dong_api()` trong `apps/taovideo/manifest.py` đọc `MODELS` và dựng
`api_contract`. Không con số nào gõ tay. Thêm một model ⇒ hợp đồng đổi theo,
`contract_hash` chuyển — đúng thứ `contract_hash` sinh ra để làm.

**Ba thứ đi ba đường khác nhau**, và phân biệt được chúng là cả bài toán:

| Trường | Đi đâu | Vì sao |
|---|---|---|
| `constraints` | **công bố** qua `PublicModel` | khách cần biết tổ hợp nào hợp lệ **trước khi gọi** |
| `id` | **khai, không công bố** | `ToolView.to_public_dict` là danh sách trắng nên nó không có đường ra; và khai nó chính là cách `test_212::test_no_vendor_model_id_reaches_a_customer_surface` **biết phải săn chuỗi nào** |
| `endpoint` | **không đi đâu** | địa chỉ hạ tầng, không phải thuộc tính sản phẩm |

⭐ Điểm phản trực giác đáng ghi: với `id`, **khai ra thì an toàn hơn giấu đi**.
Giấu thì phép kiểm rò mất mục tiêu, và `test_212:623` từ chối chạy nếu không
alias nào khai id — *"no aliases declared, so this proves nothing"*.

### 2.2 `enums` là **hợp**, `constraints` là **theo model**

Registry đòi một danh sách phẳng cho mỗi enum lấy giá trị từ nguồn nội bộ. Nên:

* `enums` trả lời *"giá trị nào tồn tại"* → qua được cổng registry;
* `constraints` trả lời *"model này nhận giá trị nào"* → là thứ khách thật sự cần.

Thiếu vế thứ hai thì khách phải thử rồi ăn lỗi — chính là rào cản cũ.

### 2.3 Thi hành **trước khi tiền chuyển**

`platform_core/public_api/invocation.py::_check_model_constraints`, gọi ở cuối
`validate_public_input`.

```
validate_public_input  ->  price()  ->  quote  ->  hold  ->  job  ->  provider
        ^ tu choi o day
```

Cả `/quotes` lẫn `/jobs` gọi `validate_public_input` **trước** `price()`, nên
một tổ hợp sai bị từ chối trước khi có báo giá, trước khi giữ chỗ, trước khi
quay số tới nhà cung cấp.

```
400  resolution: model 'seedance-2.0-mini' does not accept '4k'.
     Allowed: 480p, 720p. See constraints in GET /api/v1/models.
```

⛔ **Và nó không phát minh bề mặt hợp đồng mới.** Cả hai nửa của luật đều đã
được kiểm lúc đăng ký: `depends_on`/`field` bởi `registry._validate_tool`, giá
trị bởi chính `constraints` mà khách đọc. Luật thi hành **đúng bằng** luật công
bố — không có chỗ thứ hai để chúng lệch nhau.

⚠️ **Đây là chỗ chạm `platform_core`, và CLAUDE.md bảo phải nói vì sao.** Lý do:
mọi phép kiểm trước đó nhìn **một trường một lần**, nên không có chỗ nào diễn
đạt được ràng buộc chéo theo model. Đó là **thiếu sót của hợp đồng app**, không
phải chuyện riêng của Seedance — mọi tool nhiều model đều cần. Prompt 03 §1 cho
phép mở rộng, và phần thêm là **generic**: app nào khai `depends_on` + đặt
`constraints` là được hưởng.

### 2.4 Media hoãn **có ghi**

`image_key` (một ảnh tham chiếu) **mở**. Bốn đường còn lại — `image_keys`,
`video_key`, `audio_key`, `refs` — vào `hidden`, vì chưa chứng minh được
ownership + vòng đời qua `upload_sessions` ở đường API.

⛔ Hoãn ≠ bỏ qua kiểm. Một ref mở mà chưa kiểm ownership là đường để khách A đọc
tệp của khách B.

### 2.5 Giá: **không** đụng

Dùng nguyên `apps/taovideo/cost.py` qua `credit_cost`. Không có bảng giá thứ hai
ở tầng API.

---

## 3. Contract changes

| Thay đổi | Loại |
|---|---|
| `video.generate` vào danh mục đóng băng | ADDED |
| 3 model mới ở `/api/v1/models` kèm `constraints` | ADDED |
| `PublicModel.constraints` có người dùng đầu tiên | ADDED |
| `_check_model_constraints` ở `validate_public_input` | ADDED *(generic)* |

`check_api_compat.py`: **0 phá vỡ tương thích**. Thêm một tool chưa từng mở là
thay đổi rẻ nhất có thể có — không có tích hợp nào để phá.

---

## 4. Tests and evidence

`tests/test_336_seedance_public_api.py` — 7 phép kiểm, ba nhóm:

1. hợp đồng **sinh** từ `models.py` (lệch = một trong hai đã bị gõ tay);
   mỗi model mang tập của **riêng** nó (`seedance-2.0` có `4k`, `mini` không);
   không rò `dreamina` / `provider_model_id` / `endpoint` / `byteplus`.
2. tổ hợp sai bị từ chối, thông điệp **nói ra giá trị nào được nhận**; tổ hợp
   đúng đi qua; và `validate_public_input` chạy **trước** `price()` — kiểm bằng
   cách đọc thứ tự trong `server/api/jobs.py`.
3. bốn ref hoãn **không** lọt ra hợp đồng công khai.

`tests/test_188` — phép kiểm cũ chốt `api_exposed is False` đã **đảo có chủ ý**.
Lý do cũ (*"publishing their union would let a caller pay for a combination the
provider then refuses"*) vẫn đúng nguyên; thứ đổi là ta thôi phải publish hợp
nhất.

```
python tools\gate.py   ->  RESULT: PASS
```

---

## 5. Money / security

| | |
|---|---|
| Credit | không đường mới; `credit_cost` cũ, giữ chỗ → quyết toán → hoàn |
| Tổ hợp sai | từ chối **trước** quote ⇒ không bút toán nào phát sinh |
| Id nhà cung cấp | không ra bất kỳ bề mặt nào; có test ở 5 đường |
| Ownership | 4 ref chưa chứng minh được ⇒ **hoãn**, không mở |
| Idempotency | như mọi tool job khác |

---

## 6. Deviations

**`DEVIATION_WITH_EVIDENCE`** — hồ sơ mô tả rào cản là *"chưa publish được một
hợp đồng đúng"*, nghe như bài toán thiết kế. Sự thật: hợp đồng **rỗng**, và cấu
trúc để publish thì **đã có sẵn nhưng chưa ai dùng**.

**`BLOCKED_EXTERNAL`** — chưa chạy canary bằng credential BytePlus thật. Không
giả PASS.

---

## 7. Rollback

Bỏ `api_exposed=True` và `api_contract=_hop_dong_api()` khỏi ToolSpec, chạy lại
`check_api_compat.py --accept` và sinh lại golden. Tool chưa từng mở cho khách
nên **không có tích hợp nào để phá**.

---

## 8. Còn lại trước khi mở cho khách

| # | Việc | Ai làm |
|---|---|---|
| 1 | Canary bằng credential thật, một video ngắn nhất có nghĩa | cần khoá BytePlus sống |
| 2 | Bật `LTT_PUBLIC_API_TOOLS` qua `setup\cong_tac_tool_api.ps1` **rồi mới** deploy | chủ sản phẩm |
| 3 | Mở dần 4 ref khi chứng minh được ownership | phiên sau |

⚠️ Thứ tự ở mục 2 **không đảo được**: bật cờ sau khi deploy thì cờ không có tác dụng.

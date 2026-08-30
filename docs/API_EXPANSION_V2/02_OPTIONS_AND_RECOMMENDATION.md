# Phase 01 — Options và khuyến nghị

Dựa trên `01_CURRENT_TRUTH.md`. Mỗi mục: quan sát → phương án → khuyến nghị →
vì sao → rủi ro.

---

## 1. Seedance / `video.generate`

**Quan sát.** `api_contract` rỗng. Nhưng `apps/taovideo/models.py` **đã giữ**
ràng buộc theo từng model (`aspects`, `durations`, `resolutions`,
`supports_seed`, `prompt_controls`) cạnh hai trường **nội bộ**
(`provider_model_id`, `endpoint`).

### Option A — công bố dữ liệu đã có qua `models` của ToolSpec

Khai `api_contract["models"]` cho ba model, mỗi model mang **tập giá trị hợp lệ
của riêng nó**, sinh từ `MODELS` chứ không chép.

* ➕ Không phát minh cấu trúc mới; catalog/model system hiện tại đã hiểu `models`
  (`text.chat` và `image.generate` đang dùng).
* ➕ Tài liệu **sinh ra** từ đó — `tools/build_public_api_docs.py` đã đọc
  `api_contract`.
* ➕ Kiểm tra đọc cùng một nguồn ⇒ không có chỗ để hai nơi lệch.
* ➖ Phải lọc `provider_model_id` + `endpoint`, và phải **có test** cho việc lọc.

### Option B — một schema hợp nhất + resolver riêng

Publish một `params_schema` chung, rồi một tầng resolver kiểm tổ hợp.

* ➕ Schema công khai đơn giản hơn nhìn từ ngoài.
* ➖ **Khách không thấy được ràng buộc trước khi gọi** — họ phải thử rồi ăn lỗi.
* ➖ Sinh ra một nguồn chân lý thứ hai (schema nói một đằng, resolver một nẻo).
* ➖ Playground/tài liệu không dựng được ví dụ hợp lệ nếu chỉ đọc schema.

### ⭐ Khuyến nghị: **Option A**

Vì `USER_DECISIONS.md` §7 và Prompt 03 §6 đều đòi tài liệu **sinh từ contract**,
mà Option B làm điều đó bất khả thi. Và vì công đã có sẵn — Option A là **công
bố** thứ đang có, không phải xây mới.

**Rủi ro:** rò `provider_model_id`. ⇒ Chặn bằng test *"no provider id reaches a
customer surface"* đã có sẵn (`test_212` họ hàng), mở rộng cho `video.generate`.

---

## 2. Thứ tự kiểm tra và tiền

**Quan sát.** Ba tool video trước đã dính **Q84**: giá theo `duration_s` **khách
khai**, worker đo lại rồi nâng giữ chỗ ⇒ báo giá đã ký vẫn quyết toán cao hơn.
H35.10a+b đóng nó bằng cách **máy chủ đo** thời lượng lúc báo giá.

### ⭐ Khuyến nghị

`video.generate` theo **cùng luật đó ngay từ đầu**, và tổ hợp sai bị từ chối
**trước** quote:

```
kiem tham so (theo model)  ->  quote  ->  hold  ->  job  ->  provider
        ^ tu choi o day, chua cham toi tien
```

**Vì sao ngay từ đầu:** ba tool kia phải sửa **sau** khi đã mở, và việc đó tốn
một vòng H35.10a+b. Ở đây ta chưa mở nên chưa có ai để làm hỏng.

---

## 3. Media đầu vào

**Quan sát.** ToolSpec có **năm** đường tham chiếu: `image_key`, `image_keys`,
`video_key`, `audio_key`, `refs`.

### ⭐ Khuyến nghị: mở theo bậc, hoãn có ghi

Chỉ mở loại đã có **ownership + vòng đời** chứng minh được qua
`upload_sessions`. Loại nào chưa ⇒ **hoãn và ghi rõ**, không bỏ qua kiểm.

⛔ Prompt 03 §3 nói thẳng điều này, và nó đúng: một loại tham chiếu mở mà chưa
kiểm ownership là đường để khách A đọc tệp của khách B.

---

## 4. Codex bridge

**Quan sát.** Hợp đồng `STREAM` **đã có và đã sống**; sidecar có sẵn
`/account`, `/rate-limits`, `/capabilities`. Giá đã là giá bán phẳng có căn cứ.

### Option A — bridge thẳng từ public stream service tới sidecar
* ➕ Ít tầng nhất.
* ➖ Trộn hai việc trong `streaming.py`; mất ranh giới tiến trình của sidecar.

### Option B — một ToolSpec `STREAM` mới, đi qua `require_tool` như `text.chat`
* ➕ **Dùng lại nguyên ba cổng Q92** — tắt cờ là biến mất, đúng fail-closed.
* ➕ Giữ nguyên cô lập tiến trình của sidecar.
* ➕ Không hàng đợi/sổ tiền thứ hai.
* ➖ Phải khai thêm một tool.

### Option C — provider API-key thay cho Auth
* ⛔ **Không phải target chính** (`USER_DECISIONS.md` §2). Chỉ là phương án B
  nếu chủ sản phẩm đổi hướng.

### ⭐ Khuyến nghị: **Option B**

Vì nó là con đường **duy nhất** dùng lại được cả ba cổng fail-closed mà không
đụng vào `streaming.py`, và vì nó giữ ranh giới tiến trình — thứ đang bảo vệ
token ChatGPT khỏi mọi thứ khác trong web app.

⚠️ **Nhưng đừng viết dòng nào trước khi có quyết định chính sách.** Xem §6.

---

## 5. Developer API Center

**Quan sát.** Cả cụm `/developers/*` trả **303 về `/login`**.

### ⭐ Khuyến nghị

Một trang danh mục **công khai**, sinh từ **cùng builder** với trang sau đăng
nhập. Ranh giới giữ nguyên: *thứ giúp người ta quyết định mua thì công khai;
thứ gắn với một tài khoản thì sau đăng nhập.*

Tiền lệ: `/vps` hồi 25/08 — thẻ app trong catalog trỏ tới trang đòi đăng nhập,
và chốt hồi đó là **trang bán phải phục vụ cả khách chưa đăng nhập**.

---

## 6. Ranh giới chính sách — điều kiện tiên quyết của §4

`TECHNICALLY_READY` ≠ `COMMERCIAL_RELEASE_ALLOWED`.

Mô hình đích của Codex bridge là bán quyền gọi runtime của **một tài khoản
ChatGPT cá nhân** cho khách bên ngoài. Điều khoản của OpenAI hạn chế việc chia
sẻ/bán lại quyền truy cập tài khoản. `EXTERNAL_POLICY_NOTE.md` của chính gói đã
nêu, và gói dựng sẵn khuôn đúng để xử.

**Theo nguyên văn gói:** không tự đổi kiến trúc Auth vì lý do chính sách, không
làm xoay tài khoản, và nếu chính sách chưa rõ thì ghi `BLOCKED_POLICY` chứ không
tự nhận PASS.

⇒ **Câu cần chủ sản phẩm trả lời trước khi thi hành §4:** *ta có được phép bán
quyền gọi một tài khoản ChatGPT cá nhân cho khách bên ngoài không?* Nếu không,
phần kỹ thuật vẫn làm được cho **nội bộ** — nhưng đó là một sản phẩm khác, và
nên biết điều đó **trước** khi đầu tư.

*(Ý kiến kỹ thuật, không phải tư vấn pháp lý.)*

---

## 7. Bảng quyết định

| Quyết định | Khuyến nghị | Bằng chứng | Phương án khác | Vì sao không chọn |
|---|---|---|---|---|
| Biểu diễn ràng buộc Seedance | công bố `models` đã có trong `models.py` | `MODELS` giữ đủ `aspects`/`durations`/`resolutions`/`supports_seed` | schema hợp nhất + resolver | khách không thấy ràng buộc trước khi gọi; sinh nguồn chân lý thứ hai |
| Thứ tự kiểm | kiểm theo model **trước** quote | Q84 + H35.10a+b | kiểm ở worker | báo giá đã ký vẫn quyết toán cao hơn — lỗi đã trả giá |
| Media đầu vào | mở theo bậc, hoãn có ghi | 5 đường ref, ownership qua `upload_sessions` | mở hết | ref chưa kiểm ownership = khách A đọc tệp khách B |
| Hình dạng Codex | ToolSpec `STREAM` qua `require_tool` | `streaming.py:486`, `MODES_IN_USE` | bridge thẳng trong `streaming.py` | mất ba cổng fail-closed + mất cô lập tiến trình |
| Backend Codex | **giữ Auth** | `USER_DECISIONS.md` §2 | provider API-key | không phải target chính; chỉ là phương án B nếu chủ sản phẩm đổi hướng |
| Trang tài liệu | trang công khai, **cùng builder** | `/developers/*` 303; tiền lệ `/vps` | viết trang riêng | sinh danh sách thứ hai — `USER_DECISIONS.md` §7 cấm |

---

## 8. Thứ tự thi hành đề nghị

| Đợt | Nội dung | Chờ gì |
|---|---|---|
| **A** | Seedance ra công khai (§1–§3) | không chờ gì |
| **B** | Developer API Center (§5) | chạy song song được |
| **C** | Codex bridge (§4) | **một quyết định** (§6), không chờ code |

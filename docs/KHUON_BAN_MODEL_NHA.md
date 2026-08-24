# Khuôn mẫu: bán một model chạy trên máy nhà qua API công khai

**2026-08-24.** Rút ra từ H38 (LLM) sau khi đi hết một vòng có khách trả tiền.
Dùng để chấm H37 (ảnh) và mọi model nhà sau này.

---

## 0. Vì sao cần một khuôn, thay vì mỗi dự án tự nghĩ

H37 và H38 giải **cùng một bài toán**: một model chạy trên máy B, bán qua
`app.lttstudios.com`, tính tiền theo lượng dùng. Hai dự án đi song song và mỗi
dự án tự học lại một lần.

Cái giá của việc đó không phải thời gian — nó là **những bài học không truyền
được**. H38 vấp và sửa bảy chỗ; nếu H37 không được chấm lại theo bảy chỗ đó thì
nó sẽ vấp lần thứ hai, ở production, với tiền thật.

⚠️ **Và tôi vào việc này với một giả định sai.** Tôi tưởng H37 "đi lệch hướng"
nên đi tìm chỗ lệch. Đọc kỹ thì tầng khoá của nó **đã đúng**: `http_cong.py`
dùng `api_pool.thu_lan_luot` + `danh_dau_thanh_cong` + `danh_dau_loi`, và **không**
đánh dấu lỗi khi 429 — đúng D-005. Cổng render cũng đã có `max_concurrent=1`,
429-khi-bận, và `busy.py` đọc VRAM thật qua `nvidia-smi`.

Chỗ lệch nằm ở **ba tầng ngoài cùng**: giá, quyết toán, và quan sát.

---

## 1. Sáu tầng, và chốt của từng tầng

### Tầng 1 — Cổng trên máy B

| # | Chốt | Vì sao |
|---|---|---|
| 1.1 | Chỉ nghe LAN, tường lửa mở cho **một** IP, bearer token | máy B không giữ bí mật nào của nền tảng (Q102) |
| 1.2 | Ngân sách kiểm **trước khi chạm GPU**, vượt trần ⇒ `413` | từ chối một yêu cầu hỏng phải rẻ và dứt khoát |
| 1.3 | Bận ⇒ **`429`**, không bao giờ `5xx` | 🔴 D-005: máy A coi 5xx là *hỏng* và `disable` khoá sau 5 lần |
| 1.4 | Giới hạn đồng thời **khớp năng lực thật của engine** | engine chạy một luồng thì 50 request đồng thời chỉ thành 50 kết nối treo |
| 1.5 | Dọn card trước khi nạp model | P6: card bẩn ⇒ 18 tok/s thay vì 63, **không lỗi nào báo** |
| 1.6 | Chốt **"đang chạy trên GPU hay CPU"** đọc từ VRAM | sự cố 23/08: mọi chốt sống/chết đều xanh trong hơn một giờ |
| 1.7 | `/live` **không cần khoá** · `/health` **cần khoá** | phép thăm dò sống/chết không nên phải mang bí mật |
| 1.8 | Deploy bằng script trong repo, **không sửa tay trên máy B** | lần deploy sau là mất trắng, mất âm thầm |

### Tầng 2 — Điều phối trên máy A

| # | Chốt | Vì sao |
|---|---|---|
| 2.1 | Khoá lấy qua **`api_pool`**, mã hoá trong CSDL | biến môi trường không có telemetry, không cooldown, không xoay được |
| 2.2 | `base_url` của **khoá** đi trước của registry | registry đọc biến môi trường — vắng mặt trong script chạy tay, và làm mọi thứ trông như "máy B chết" |
| 2.3 | **429 KHÔNG đánh dấu lỗi cho khoá** | xem 1.3 |
| 2.4 | **Không cascade sang đám mây** cho hàng bán ra ngoài | khách trả tiền cho model nhà mà nhận Gemini là bán sai hàng (D-010) |
| 2.5 | Thăm dò **sống/chết** + thăm dò **GPU**, mỗi cái một ngưỡng riêng | cổng sống mà model bò trên CPU là hai chuyện khác nhau |

### Tầng 3 — Giá

| # | Chốt | Vì sao |
|---|---|---|
| 3.1 | Bảng giá có **phiên bản** và một hàm `bang_gia()` | đổi giá mà không có phiên bản thì không đối soát được hoá đơn cũ |
| 3.2 | Số học **số nguyên**, làm tròn **LÊN**, tối thiểu 1 credit | số thực làm tiền lệch dần và không ai tìm ra |
| 3.3 | `uoc_tran()` giữ chỗ **≥** giá thật, luôn luôn | giữ thiếu ⇒ khách tiêu quá số dư |
| 3.4 | 🔴 Quyết toán theo **sản phẩm thật**, không theo phần đã giữ | xin 4 ảnh mà nhận 2 thì trả 2. Đây là lỗi H38 đã mắc |
| 3.5 | **Không đo được ⇒ hoàn đủ, thu 0** | thu tiền không bằng chứng tệ hơn mất một ít tiền |
| 3.6 | Giá lên **trang công khai**, lấy từ **chính hàm ra hoá đơn** | gõ lại số vào template là tạo bảng giá thứ hai |

### Tầng 4 — App

| # | Chốt | Vì sao |
|---|---|---|
| 4.1 | Nghiệp vụ ở **`features.py`**, dùng chung mọi cửa | hai cửa tự xử lý riêng ⇒ ngày chúng lệch nhau là ngày một yêu cầu bị tính hai giá |
| 4.2 | **Alias công khai ≠ id nội bộ** | id nội bộ lộ ra là tích hợp ghim vào nó (`test_212`) |
| 4.3 | Ba cổng Q92 độc lập: `api_exposed` · `surface` · công tắc vận hành | bật một cờ không bao giờ được mở thêm năng lực |
| 4.4 | Handler **phải báo `credit_cost`** trong result | không báo ⇒ `job_runner` thu trọn phần đã giữ, **im lặng** |

### Tầng 5 — Cửa API

| # | Chốt | Vì sao |
|---|---|---|
| 5.1 | Khai đúng `execution_mode`, và bộ kiểm **chạy lúc nạp app** | hợp đồng có bộ kiểm mà bộ kiểm không chạy thì là trang trí |
| 5.2 | **Chế độ thử không chạm GPU, không chạm sổ tiền** | khoá thử ai cũng có; để nó chiếm card là mở một cách miễn phí để giữ GPU |
| 5.3 | Giữ chỗ → **commit** → chạy → quyết toán ở **phiên CSDL mới** | giao dịch trùm lên lượt gọi giữ khoá và giữ kết nối suốt thời gian đó |
| 5.4 | Mã giữ chỗ **vừa cột CSDL** | `VARCHAR(36)`: SQLite không ép, PostgreSQL ép |

### Tầng 6 — Khách

| # | Chốt | Vì sao |
|---|---|---|
| 6.1 | Trang giá **công khai**, không sau đăng nhập | không ai đăng ký một dịch vụ tính tiền để xem nó tính bao nhiêu |
| 6.2 | Ví dụ **sinh từ hợp đồng**, và **chạy thử được** | biên dịch được ≠ chạy được (QT-14) |
| 6.3 | Công cụ tự ghi cấu hình | thứ chặn khách là điền cấu hình, không phải giao thức |
| 6.4 | Giám sát **khách**: hết credit, lỗi lặp lại của một khoá | hôm nay ta giám sát *máy*, không giám sát *khách gọi có được không* |

---

## 2. Chấm H37 theo khuôn

| Tầng | Đạt | Ghi chú |
|---|---|---|
| **1 — cổng máy B** | **6/8** | thiếu **1.6** (chốt GPU/CPU) và một phần **1.5** |
| **2 — điều phối** | **4/5** | thiếu **2.5** — **không có phép thăm dò nào cho cổng render** |
| **3 — giá** | **2/6** | 🔴 thiếu 3.1, 3.4, 3.5, 3.6 |
| **4 — app** | **3/4** | thiếu **4.1** (`features.py`) và **4.4** (`credit_cost`) |
| **5 — cửa API** | **2/4** | chưa mở; 5.3/5.4 chưa áp dụng vì chỉ đi cửa job |
| **6 — khách** | **1/4** | chỉ có ví dụ tự sinh |

**Tổng: 18/31.** Và điểm thấp **không** nằm ở chỗ tôi tưởng lúc đầu.

---

## 3. Bảy chỗ lệch thật, xếp theo mức nguy hiểm

### 🔴 L1 — Quyết toán theo phần đã giữ, không theo ảnh thật (3.4 · 4.4)

`apps/anhnoibo/jobs.py` trả `image_keys` nhưng **không** trả `credit_cost`. Mà
`job_runner._quyet_toan_credit` không thấy khoá đó thì **thu trọn phần đã giữ**.

Nghĩa là: xin 4 ảnh, máy B trả về 2, **khách vẫn trả tiền 4 ảnh**. Im lặng.

Đây **đúng là lỗi H38 đã mắc và đã sửa** hôm 23/08. Cùng một gốc, cùng một hình
dạng, ở một dự án khác.

### 🔴 L2 — Không có phép thăm dò nào cho cổng render (2.5)

`job_runner` có `_tham_cong_vlm()` và `_tham_gpu_may_b()` cho LLM. Cho ảnh:
**không có gì**. Cổng render chết lúc 2 giờ sáng thì cách duy nhất biết là có
khách thử rồi thấy hỏng.

### 🔴 L3 — Không phát hiện được "model rơi về CPU" ở phía ảnh (1.6)

`busy.py` đã có `vram_dung_mb_qua_smi()` — nguyên liệu có sẵn — nhưng không có
chốt "có model đang nạp mà VRAM lại thấp". Sự cố 23/08 nếu xảy ra ở phía ảnh thì
triệu chứng sẽ là **ảnh ra chậm gấp hàng chục lần**, và mọi chốt vẫn xanh.

### 🟠 L4 — Giá không được công bố (3.1 · 3.6)

`CREDIT_MOI_ANH = 5` nằm trong manifest. Không phiên bản, không `bang_gia()`,
**không lên trang `/gia-api`**. Khách không có cách nào biết giá ảnh trước khi
đăng ký.

### 🟠 L5 — Chưa mở trên API công khai (4.3)

`api_exposed=True` nhưng `LTT_PUBLIC_API_TOOLS` trên bản chạy thật chỉ có
`text.chat`. Fail-closed đang làm đúng việc; chỉ là chưa ai bật.

### 🟡 L6 — Nghiệp vụ nằm trong `jobs.py`, không có `features.py` (4.1)

Hôm nay chỉ một cửa nên chưa đau. Ngày thêm cửa thứ hai là phải chép logic — và
`public_api/costing.py` gọi đó là "parallel engines" và cấm.

### 🟡 L7 — Không có tài liệu/công cụ cho khách dùng ảnh (6.1 · 6.3)

`/developers/cli` chỉ nói LLM. Ảnh đi cửa job nên cần một hướng dẫn khác hẳn:
báo giá → nộp → hỏi trạng thái → lấy ảnh.

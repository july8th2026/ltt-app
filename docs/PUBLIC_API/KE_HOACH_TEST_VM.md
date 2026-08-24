# Kế hoạch thử vận hành trên VM sạch (P4 / U8)

**2026-08-24.** Chủ sản phẩm cấp một VM nội bộ để thử toàn bộ đường khách đi.

| | |
|---|---|
| Máy | `VM105` · `192.168.2.136` · Windows 10 Enterprise LTSC |
| Vào bằng | SSH **khoá riêng** `ltt_vm_test` (mật khẩu chỉ dùng **một lần** để đẩy khoá lên, sau đó không dùng nữa) |

---

## 0. Vì sao VM này trả lời được thứ máy A không trả lời được

Máy A có node, git, VS Code, npm, `pywebview`, **và toàn bộ mã nguồn**. Mọi phép
thử ở đó chỉ chứng minh *"chạy trên máy đã có đồ nghề"*.

Trạng thái thật của VM, đo 24/08:

| | VM105 | Ý nghĩa cho phép thử |
|---|---|---|
| VS Code + 2 tiện ích | ✅ **chưa đăng nhập** | đúng tình huống khách mới |
| WebView2 Runtime | ✅ 151.0.4129.101 | GUI chạy được |
| Python | 3.13.2 | ⚠️ **không** thử được ca "khách không có Python" — xem T2b |
| `pywebview` | ❌ **không có** | ⭐ thử được **đường lùi** (U5) và bản đóng gói tự mang thư viện |
| node | ❌ | Codex **CLI** không có; chỉ có tiện ích VS Code |
| `~/.codex`, `~/.claude` | ✅ **đã tồn tại** | ⭐ phép "hợp nhất chứ không ghi đè" được thử **thật**, không phải trên thư mục trống |
| Mã nguồn LTTSTUDIOSAPP | ❌ | đúng như khách |

⭐ **Hai dòng có sao là lý do VM này đáng giá.** Trên máy A, `cam_cli` luôn ghi
vào thư mục **do chính nó tạo**; ở đây nó ghi vào thư mục **do tiện ích VS Code
tạo trước**. Đó là ca duy nhất có thể phá cấu hình của khách, và cho tới hôm nay
nó chỉ được thử bằng test đơn vị.

---

## 1. Bảng ca thử

| # | Ca | Đạt khi | Tự động? |
|---|---|---|---|
| **T1** | Cài installer trên máy chưa có gì của ta | mã 0, có lối tắt, `--tu-kiem` đủ tài sản | ✅ |
| **T2** | Mở GUI khi máy **không có** `pywebview` | bản đóng gói **tự mang** thư viện ⇒ vẫn mở | ✅ |
| **T2b** | Chạy khi **ẩn Python khỏi PATH** | vẫn chạy — chứng minh nó không mượn Python của máy | ✅ |
| **T3** | 🔴 Cắm khi `~/.codex` + `~/.claude` **đã có sẵn** | nội dung cũ **còn nguyên**, chỉ thêm khối của ta | ✅ |
| **T4** | Cắm bằng khoá thật | 3 tệp/biến được đặt, khoá **không nằm trong tệp nào** | ✅ |
| **T5** | `kiem` — gọi thật qua Cloudflare | `/tools`, `/credits/balance`, `/messages` đều 200 | ✅ |
| **T6** | Chạy `claude.exe` **của tiện ích VS Code trên VM** | trả lời đúng, tức cấu hình công cụ ghi ra **dùng được thật** | ✅ |
| **T7** | Mở VS Code, dùng tiện ích bằng tay | người thật nhìn thấy nó chạy | ⛔ **cần người** |
| **T8** | 🔴 `go` — gỡ ra | tệp trở về **bằng từng byte** so với trước T3 | ✅ |
| **T9** | Gỡ cài | thư mục hết, lối tắt hết, **cấu hình khách không bị đụng** | ✅ |

### Vì sao T3 và T8 in đậm

Đó là hai ca **hỏng lặng lẽ**. T1/T2/T4/T5 sai thì thấy ngay — có lỗi, có mã
thoát. T3 và T8 sai thì công cụ vẫn báo thành công, và thứ mất đi là **cấu hình
riêng của khách**; không có triệu chứng nào cho tới lần sau họ mở Codex.

⇒ Cả hai phải đo bằng **băm nội dung trước/sau**, không phải bằng mắt.

### ⛔ T7 không tự động hoá được, và đó không phải thiếu sót

Tôi không nhìn thấy màn hình VM (công cụ điều khiển màn hình chỉ tác dụng lên
máy A). Điều khiển qua RDP thì được, nhưng nó chỉ thêm một lớp bấm chuột lên
**đúng thứ T6 đã chứng minh bằng dây**: tiện ích Claude Code **gói chính**
`claude.exe` mà T6 chạy, và tiện ích Codex đọc **chính** `config.toml` mà T3 kiểm.

⇒ T7 là để **người thật xác nhận trải nghiệm**, không phải để chứng minh giao thức.

---

## 2. ⛔ Cái không làm trên VM này

| Không làm | Vì sao |
|---|---|
| Cài node/codex CLI lên VM | Máy A đã đo Codex CLI rồi. Cài thêm để lấy số trùng là làm bẩn một bàn thử sạch |
| Đăng nhập tài khoản Anthropic/OpenAI thật | Cả mục đích là thử **đường của ta**; đăng nhập nhà khác làm nhiễu |
| Giữ mật khẩu VM để dùng tiếp | Đã đẩy khoá lên; mật khẩu **thôi không cần** |
| Để lại khoá API trên VM sau khi thử | Thu hồi khoá **và** chạy `go` ở T8 |

---

## 3. Kết quả — chạy 24/08 bằng **chính bản `.exe`** đã dựng

| # | Ca | Kết quả |
|---|---|---|
| **T1** | Cài installer | ✅ mã 0, SHA256 khớp tệp đã dựng, 2 lối tắt, cài vào `%LOCALAPPDATA%` **không cần admin** |
| **T2** | Máy **không có** `pywebview` | ✅ `[OK] co pywebview` — bản đóng gói **tự mang** thư viện |
| **T2b** | Ẩn Python khỏi `PATH` | ✅ `Du tai san`, mã 0 — **không mượn Python của máy** |
| **T3** | Cắm khi khách **đã có** cấu hình riêng | ✅ giữ `model`, `[model_providers.cong_ty]`, chú thích cuối tệp; chỉ **thêm** khối của ta |
| **T4** | Khoá không nằm trong tệp nào | ✅ |
| **T5** | Gọi thật qua Cloudflare | ✅ `/tools` `/credits/balance` `/messages` đều **200** |
| **T6** | `claude.exe` của **tiện ích VS Code trên VM** | ✅ trả lời `72` (9×8), 39,6 s — cấu hình công cụ ghi ra **dùng được thật** |
| **T8** | Gỡ ra | ✅ `config.toml` **bằng từng byte**; `settings.json` **nội dung giống hệt**; **mọi** biến môi trường bị dọn |
| **T9** | Gỡ cài | ✅ thư mục hết, lối tắt hết, **cấu hình khách không bị đụng** |
| **T7** | Chat thật trong VS Code | ✅ **ĐẠT 24/08** — Codex trả `144`, Claude Code trả `7 x 9 = 63`, số dư 1041 → **1034** |

---

## 4. 🔴 Bốn lỗi VM tìm ra mà **không test đơn vị nào thấy**

Đây là lý do phép thử này tồn tại. Cả bốn đều **hỏng lặng lẽ**.

### ① `go` để lại **một khoá API còn sống**

`LTT_API_KEY` bị bỏ sót khỏi danh sách dọn, vì nó "thuộc về Codex" còn hàm dọn
tên là `go_claude`. Công cụ vẫn in *"da go"* và **mọi dòng đều `[OK]`**.

⚠️ Test đơn vị không thấy vì chúng vá `_xoa_env` thành một hàm giả trả `True` —
tức chúng đo *"ta có gọi hàm không"*, chứ không đo *"biến nào được gọi"*. Test
mới ghi lại **tên** từng biến đã yêu cầu xoá.

### ② Đổi **cả tệp** từ CRLF sang LF

`Set-Content` của PowerShell ghi CRLF. Ta đọc rồi ghi lại bằng kiểu LF là
**viết lại từng dòng** — `go` không trả về bằng từng byte nữa, và khách mở
`git diff` lên thấy **toàn bộ tệp** thay đổi.

Test đơn vị không thấy vì chính chúng ghi fixture bằng kiểu LF — tức chúng đo
**một thế giới chỉ có LF**.

### ③ Bản sửa thứ nhất **cũng sai**, và VM lại bắt được

Tôi sửa thành *"tệp có CRLF thì ghi CRLF"*. Nhưng tệp thật **lẫn lộn**: nội dung
LF, dòng cuối CRLF. Thấy **một** CRLF là ép cả tệp thành CRLF ⇒ **147 byte phình
thành 154**.

⭐ Cách đúng là **không hỏi câu đó**: đọc thô, mổ đúng khối có dấu mốc, ghi thô.
Phần ngoài khối không bị đụng tới thì không có gì để hỏng — kể cả khi nó lẫn lộn.

### ④ Bản đóng gói in ra một câu lệnh **khách không có**

Nó bảo *"Kiem lai: python tools\cam_cli.py kiem"* — nhưng khách cài `.exe`,
**không có mã nguồn**. Một hướng dẫn sai còn tệ hơn không có, vì khách sẽ đi tìm
thứ không tồn tại rồi tưởng mình cài hỏng. Nay nó in
`LTTStudios-CamCLI.exe kiem`.

---

## 4b. ✅ T7 — hai tiện ích VS Code **chạy được**, và ba điều kiện phải đúng cả ba

Điều khiển VM qua RDP, gõ trực tiếp vào bảng chat của từng tiện ích:

| Tiện ích | Câu hỏi | Trả lời |
|---|---|---|
| **Codex** | `12 x 12 = ?` | **144** |
| **Claude Code** | `7 x 9 = ?` | **7 x 9 = 63** *(kèm "Thought for 1s")* |

⭐ **Bằng chứng nó đi qua API của ta, không phải nhà khác:** số dư credit
**1041 → 1034**. Không có tiền bị trừ thì không có gì chứng minh cả.

### Ba điều kiện, thiếu một là hỏng

| | Điều kiện | Vì sao |
|---|---|---|
| ① | Codex khai ở **GỐC** `config.toml` (`cam --vscode`) | tiện ích **không có cách truyền `--profile`**, và Codex 0.145 từ chối thẳng `profile = "..."` trong tệp |
| ② | `claudeCode.disableLoginPrompt: true` ở `settings.json` **cấp người dùng** | tiện ích Claude Code **không đọc biến môi trường** như CLI (lỗi đã biết từ v2.0.0). Thiết lập khai `scope: "machine"` nên đặt ở workspace là vô hiệu, **không báo lỗi** |
| ③ | Phiên Windows có **môi trường mới** | xem dưới — đây là cái khó nhất |

### 🔴 Cái bẫy môi trường: ba lần tôi tưởng đã sửa mà chưa

Đây là chỗ tốn nhiều thời gian nhất, và nó **không có triệu chứng nào** ngoài một
dòng `Missing environment variable: LTT_API_KEY`.

| Đã thử | Kết quả |
|---|---|
| `setx` rồi **mở lại VS Code** | ❌ vẫn thiếu |
| Thêm **khởi động lại explorer** | ❌ vẫn thiếu |
| **Đăng xuất rồi đăng nhập lại** | ✅ `$env:LTT_API_KEY.Length` = **83** |

⭐ **Vì sao khởi động lại explorer không đủ:** tôi giết explorer rồi khởi động nó
**từ một `cmd` do explorer CŨ sinh ra** — nên explorer mới **kế thừa đúng môi
trường cũ**. Một vòng luẩn quẩn không nhìn thấy được.

⚠️ Khách thật chạy công cụ **trong phiên của họ** nên `setx` phát được thông báo
`WM_SETTINGCHANGE` tới explorer và thường chỉ cần mở lại VS Code. Tôi dính vì cắm
qua **SSH (session 0)**. Nhưng đã dính một lần thì phải nói ra — nên lời nhắc của
công cụ nay có thêm câu *"nếu vẫn báo thiếu biến thì đăng xuất rồi đăng nhập lại"*.

⛔ **Và đừng đọc `Missing environment variable` thành "cấu hình sai".** Nó là
bằng chứng ngược lại: Codex **đã đọc được** `config.toml` của ta và đã đi tới
bước tra `env_key`. Cấu hình đúng; chỉ môi trường thiếu.

---

## 5. Một giới hạn **nói thẳng**, không giấu

`settings.json` **không** được hứa bằng-từng-byte, chỉ hứa **không mất dữ liệu và
không đổi kiểu xuống dòng**.

| | `config.toml` | `settings.json` |
|---|---|---|
| Cách xử | **mổ một khối** có dấu mốc | **parse rồi sinh lại** |
| Hứa được | ✅ **bằng từng byte** | nội dung giống hệt, tệp được định dạng lại |

Lý do: TOML có **chú thích** và **thứ tự khoá** mà một vòng parse-rồi-ghi-lại sẽ
xoá sạch, nên phải mổ văn bản. JSON **không có chú thích** — ta buộc phải parse
để biết khoá nào của khách, khoá nào của ta, vì đó là điều kiện để làm đúng việc
*"trả về giá trị cũ"*.

⛔ **Đừng viết một test đòi bằng-từng-byte cho JSON rồi nới code cho nó xanh** —
như vậy là hứa một điều ta không giữ được.

Số đo trên VM: `{"env":{"CUA_KHACH":"giu nguyen"},"permissions":{"allow":["Read"]}}`
**giống hệt** trước và sau, 84 byte → 107 byte (thụt lề 2 khoảng trắng).

---

## 6. Dọn dẹp sau phép thử

| | |
|---|---|
| Công cụ | đã gỡ cài (T9) |
| Cấu hình thử trên VM | đã xoá, kể cả `*.truoc-ltt` và tệp trạng thái |
| Biến môi trường | không còn cái nào |
| Tệp `.ps1` tạm + installer trong `Temp` | đã xoá |
| Khoá API thử | **đã thu hồi** (`con song: 0`) |
| Mật khẩu VM | dùng **một lần** để đẩy khoá; từ đó vào bằng `ltt_vm_test` |

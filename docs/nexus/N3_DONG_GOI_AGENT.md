# N3.3b — đóng gói agent cho máy khách, và cái giá của Q95

> Lập 2026-08-18. Phần **vòng đời** (`nexus_agent/service.py`) đã xong và có
> test. Phần **đóng gói** là quyết định còn lại, ghi ở đây vì nó đắt hơn vẻ
> ngoài và vì Q95 làm nó khó hơn.

---

## 1. Bài toán

Khách không có Python. Agent viết bằng Python. Nên phải có một thứ khách tải về
và chạy được ngay.

## 2. Quyết định đã chốt: Scheduled Task, không phải Windows Service

| | Cần admin? | Chạy trước khi đăng nhập? |
|---|---|---|
| Windows Service | **có** | có |
| **Scheduled Task (user)** ← chọn | **không** | không |

Lý do gắn thẳng với Q95: bản cài chưa ký mã đã làm Windows cảnh báo rồi. Thêm
một lời xin quyền admin nữa là dựng đúng màn hình mà kịch bản lừa đảo T1 cần
khách bấm qua. **Bỏ được UAC là bỏ được một nửa kịch bản đó.**

**Cái giá, có thật:** agent chỉ chạy khi người dùng đã đăng nhập; máy ở màn hình
khoá thì không vào được. Với v1 — khách tự ghép máy của chính mình — đó là đánh
đổi đúng. Khi nào cần vào trước lúc đăng nhập thì đổi sang service, và **đổi kèm
quyền admin**, không phải một cờ nhỏ.

## 3. Đóng gói: PyInstaller **one-dir**, không one-file

Ba lựa chọn đã cân:

| | Vì sao không |
|---|---|
| Ship Python embeddable + script | Khách phải giải nén đúng chỗ; hỏng là hỏng lặng lẽ |
| PyInstaller **one-file** | Nó **giải nén ra thư mục tạm rồi chạy từ đó** mỗi lần khởi động — đúng hành vi mà phần mềm diệt virus coi là đáng ngờ |
| **PyInstaller one-dir** ← chọn | Chạy thẳng từ thư mục đã cài, không có bước giải nén lúc chạy |

## 4. Nghiên cứu 2026: SmartScreen và Defender đã đổi luật chơi

> Kiểm chứng ngày 2026-08-18 từ tài liệu Microsoft và nhà cung cấp. **Ba điều
> dưới đây lật ngược lời khuyên cũ**, kể cả lời khuyên tôi đưa trong Q95.

### 4.1 Không có cách "bỏ qua" SmartScreen — kể cả EV

Câu hỏi ban đầu là "thay chữ ký để không hiện cảnh báo". Sự thật kỹ thuật: **từ
2024, không chứng thư nào tắt được cảnh báo SmartScreen tức thì nữa.** Microsoft
đã bỏ đặc quyền đó của chứng thư **EV** khi cập nhật Trusted Root Program.

- SmartScreen giờ xây danh tiếng **theo hash của từng file**, tích luỹ theo lượt
  tải và chạy không có dấu hiệu độc hại;
- EV và OV **được đối xử như nhau** — nên chứng thư EV đắt tiền không còn lợi thế
  nào ở đây;
- **mỗi bản build mới là một hash mới, danh tiếng về không.** Bản cũ chạy sạch
  sáu tháng cũng không giúp bản mới; nó phải tự kiếm lại uy tín từ đầu.

Hệ quả cho cách hỏi: **không "thay chữ ký để giấu cảnh báo" được.** Ký là để
*chứng thực danh tính LTT*, không phải để *tắt cảnh báo*. Cảnh báo chỉ mờ dần khi
đủ người tải, và điều đó đúng cho mọi chứng thư.

### 4.2 Nhưng ký vẫn đáng — nó giảm mạnh việc Defender XOÁ file

SmartScreen (cảnh báo lúc tải) và Defender (quét/xoá sau khi cài) là hai thứ
khác nhau, và ký giúp cái thứ hai **ngay lập tức**, không cần chờ danh tiếng:

- binary đã ký **hiếm khi** bị heuristic Defender gắn cờ; chưa ký thì binary
  PyInstaller nằm đúng trong nhóm bị gắn cờ nhiều nhất, vì mã độc cũng hay đóng
  gói kiểu đó;
- nên rủi ro tệ nhất của "chưa ký" không phải một hộp thoại mà là **Defender xoá
  file sau khi cài**, và triệu chứng phía khách là *"phần mềm tự biến mất"*.

### 4.3 Chi phí ký đã rẻ đi ~20 lần — điều này ảnh hưởng Q95

Con số tôi đưa trong Q94/Q95 (~200–400 USD/năm) là **giá cũ**. Từ 11/2024
Microsoft mở **Azure Trusted Signing** (nay tên **Artifact Signing**) cho **cá
nhân**:

| | Giá | |
|---|---|---|
| Azure Artifact Signing | **9,99 USD/tháng** (~120 USD/năm), tối đa 5.000 chữ ký | Cá nhân đăng ký được từ 11/2024; cần xác minh danh tính |
| Chứng thư OV truyền thống | 200–400 USD/năm + token phần cứng | Không còn lý do chọn nếu đã có Azure |
| Chứng thư EV | đắt hơn | **Hết lợi thế** sau 2024 (mục 4.1) |

**Đây là thông tin để chủ sản phẩm quyết lại, không phải để tôi đảo Q95.** Q95
(phát hành khi chưa ký) vẫn hiệu lực và vẫn hợp lệ. Nhưng lý do gốc của nó là
"chứng thư đắt"; với 9,99 USD/tháng thì đánh đổi đã khác, và **danh tiếng
SmartScreen mất hàng tuần để xây — bắt đầu càng sớm càng tốt**, kể cả khi lượng
khách còn ít.

Nguồn kiểm chứng: [Trusted Signing pricing (Azure)](https://azure.microsoft.com/en-us/pricing/details/trusted-signing/),
[EV certs no longer grant instant reputation (ToDesktop)](https://www.todesktop.com/blog/posts/windows-apps-psa-ev-certs-do-not-grant-immediate-reputation-anymore),
[SmartScreen reputation is per-file-hash (Microsoft Learn)](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation).

## 4b. Giảm Defender gắn cờ mà KHÔNG cần ký (làm được ngay)

Ba cách, độc lập với việc ký, xếp theo công sức tăng dần:

| Cách | Hiệu quả | Cái giá |
|---|---|---|
| **one-dir, không one-file** ← đã chọn | one-file giải nén ra thư mục tạm rồi chạy — đúng hành vi Defender nghi | không |
| **Không dùng UPX nén** | UPX là dấu hiệu gắn cờ kinh điển vì mã độc hay nén để giấu | file to hơn |
| **Dựng lại bootloader PyInstaller từ nguồn** | bootloader mặc định đã bị gắn cờ hàng nghìn lần; bản tự dựng là duy nhất | cần trình biên dịch C, thêm bước build |
| **Đổi sang Nuitka** | biên dịch Python → C → binary thật, nên ít bị gắn cờ hơn hẳn bundle | đổi toàn bộ công cụ đóng gói, build lâu hơn |

Nếu sau khi ký mà vẫn bị gắn cờ (hiếm), đường cuối là **gửi mẫu cho Microsoft
qua Defender submission** để họ gỡ nhầm — đây là kênh chính thức cho false
positive, không phải mẹo.

## 5. Việc phải làm khi bắt tay đóng gói

- [ ] Thêm PyInstaller vào **môi trường dựng**, không vào `requirements.txt` của
      máy chủ — nó là công cụ dev, và một phụ thuộc thừa trên production là một
      thứ nữa phải vá khi có CVE.
- [ ] Dựng **one-dir**, không one-file (mục 3), và **không UPX** (mục 4b).
- [ ] Công bố **SHA-256** của bản cài trên trang tải (Q95 yêu cầu).
- [ ] Trang tải **nói trước** cảnh báo khách sẽ thấy — để chính LTT là người
      giải thích, chứ không phải kẻ gọi điện cho họ.
- [ ] Thử trên **một máy Windows sạch**, không phải máy đã có Python. Loại lỗi
      của bước này chỉ xuất hiện ở đó.
- [ ] Ghim `RELEASE_PUBLIC_KEY` trước khi dựng bản đầu tiên — chưa ghim thì
      agent từ chối mọi bản cập nhật (đúng thiết kế, nhưng sẽ khó hiểu nếu
      không biết).

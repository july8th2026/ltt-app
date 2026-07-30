# Quy tắc làm việc trong dự án này

Áp dụng cho mọi phiên làm việc trên `D:\LTTSTUDIOSAPP`, cho cả người và Claude.

---

## 1. Bắt buộc đọc trước khi thay đổi bất cứ thứ gì

Theo đúng thứ tự, không bỏ bước:

1. `docs/QUYET_DINH_NEN_TANG.md` — **nguồn chân lý**. Tài liệu nào mâu thuẫn
   với nó thì nó đúng.
2. `docs/KE_HOACH_TRIEN_KHAI.md` — hạng mục đang làm và tiêu chí hoàn thành.
3. `docs/NHAT_KY.md` — hai mục gần nhất.
4. Đọc chính các file sắp sửa, **trước khi** sửa.
5. `git status` — biết cây làm việc đang sạch hay bẩn.

`docs/_luutru/` là tài liệu lịch sử. Đọc để hiểu *vì sao*, **không bao giờ làm
theo hướng dẫn trong đó**.

---

## 2. Ranh giới không được vượt

1. **`D:\BOT GEMINI` chỉ đọc.** Đang phục vụ người dùng thật. Không sửa, không
   tạo, không xoá, không chạy script ghi file bên đó. Muốn dùng lại thì **copy
   sang** `D:\LTTSTUDIOSAPP` rồi làm trên bản copy.
2. **Không import chéo** giữa hai cây mã nguồn.
3. **Thêm app = thêm một thư mục trong `apps/`.** Không sửa `platform_core/`
   hay `server/`. Nếu thấy buộc phải sửa → **dừng lại và giải thích vì sao**;
   đó là dấu hiệu hợp đồng app còn thiếu, phải bổ sung vào hợp đồng chứ không
   đi vòng.
4. **Không triển khai lên máy chủ, không đổi DNS** trừ khi được yêu cầu rõ ràng.
5. **App socialbot đã đóng băng.** Không tối ưu, không thêm tính năng. Sửa chỉ
   khi nó chặn hạ tầng.
6. Cổng của nền tảng là **8100**. Cổng 8000 thuộc về hệ thống khác trên cùng máy.

---

## 3. Bí mật

- Không bao giờ đưa giá trị bí mật (token, khoá, mật khẩu, nội dung file
  service-account) vào code, tài liệu, git, log, ảnh chụp màn hình hay tóm tắt
  hội thoại. Chỉ được ghi **tên** biến, nơi lưu, trạng thái xoay vòng.
- Bí mật sống ngoài mã nguồn, nạp từ biến môi trường hoặc thư mục được bảo vệ.
- Chạy `python tools/scan_source_secrets.py` trước mỗi lần commit. Phải 0 finding.
- Nếu phát hiện bí mật lọt vào file được theo dõi: che đi, báo người dùng xoay
  vòng khoá, ghi vào nhật ký — **không chép giá trị đó đi đâu cả**.

---

## 4. Kỷ luật thay đổi

- Làm **thay đổi nhỏ nhất còn trọn nghĩa** cho hạng mục đang mở.
- Mỗi thay đổi hành vi phải có test đi kèm.
- Không xoá test đang xanh, trừ khi có quyết định sản phẩm được ghi lại.
- Trước khi báo xong, bắt buộc chạy:
  ```powershell
  python -m pytest -q                    # phải xanh hết
  python tools\scan_source_secrets.py    # phải 0 finding
  ```
- Ghi **đúng lệnh đã chạy và kết quả thật** vào nhật ký. Phân biệt rõ
  `đã chạy` / `chưa chạy` / `pass` / `fail`.
- **Không bao giờ tuyên bố hoàn thành dựa trên kế hoạch hay số test thu thập
  được.** Chỉ dựa trên kết quả chạy thật.
- Thay đổi rủi ro: viết trước cách lùi lại, rồi mới làm.

### Kiểm tra bằng trình duyệt

Test xanh **không** chứng minh trang hiển thị đúng. Sau mỗi thay đổi giao diện
hoặc luồng người dùng: mở trình duyệt, tái hiện luồng, xem console error, xem
request hỏng, xác minh trên giao diện thật. Việc này đã hai lần bắt được lỗi mà
test không thấy.

---

## 5. Quy tắc bắt buộc trên Windows

Bốn điều dưới đây đều **đã thực sự gây sự cố** trong dự án này:

1. **Ghi file cấu hình phải KHÔNG BOM.**
   ```powershell
   [IO.File]::WriteAllText($path, $text, (New-Object Text.UTF8Encoding($false)))
   ```
   `Out-File -Encoding utf8` và `Set-Content -Encoding utf8` của PowerShell 5.1
   chèn BOM → `json.load()` vỡ → `/health/ready` trả 503 trong khi dịch vụ vẫn
   chạy bình thường. Có test chốt (`tests/test_61_setup_scripts.py`).

2. **File `.ps1` phải thuần ASCII.** PowerShell 5.1 đọc `.ps1` không BOM theo
   bảng mã ANSI; một dấu tiếng Việt làm hỏng cả câu lệnh và báo lỗi ở dòng khác.

3. **Không viết Python inline qua PowerShell.** PowerShell nuốt dấu ngoặc kép
   khi truyền cho `.exe`, nên `r"C:\path"` tới Python thành `rC:\path`. Ghi ra
   file `.py` rồi chạy.

4. **Mọi đường dẫn dữ liệu đi qua `core.runtime_paths.data_path()`.** Chuỗi
   `os.path.join("data", ...)` là tương đối theo thư mục làm việc; trên máy chủ
   nó rơi vào `app\data\` — thư mục **bị xoá và thay toàn bộ mỗi lần cập nhật**.
   Có test chốt (`tests/test_62_khoa_logic.py`).

---

## 6. Quy tắc cập nhật memory

Memory ở đây gồm ba tầng, mỗi tầng một nhiệm vụ. **Đừng trộn lẫn.**

| Tầng | File | Chứa gì | Cập nhật khi nào |
|---|---|---|---|
| **Quyết định** | `docs/QUYET_DINH_NEN_TANG.md` | Điều đã chốt và **vì sao**. Ít thay đổi. | Khi có quyết định kiến trúc/sản phẩm mới, hoặc đổi hướng |
| **Kế hoạch** | `docs/KE_HOACH_TRIEN_KHAI.md` | Việc cần làm, tiêu chí hoàn thành, tiến độ | Khi xong một hạng mục, hoặc khi phát hiện việc mới |
| **Nhật ký** | `docs/NHAT_KY.md` | Đã làm gì, lệnh nào chạy, kết quả thật | Cuối mỗi phiên có thay đổi code |

### Sau khi xong MỘT hạng mục — làm đủ bốn việc

Không được bỏ việc nào. Bỏ một việc là lần sau phải đoán.

1. **Đánh dấu `[x]`** hạng mục đó trong `KE_HOACH_TRIEN_KHAI.md`, ghi kèm ngày
   và kết quả test thật.
2. **Ghi một mục vào `NHAT_KY.md`** theo mẫu ở cuối file đó.
3. **Nếu trong lúc làm phát sinh quyết định mới** → thêm dòng vào bảng quyết
   định (xem giao thức bên dưới).
4. **`git commit`** với thông điệp nói rõ *vì sao*, không chỉ *cái gì*.

### Giao thức đổi quyết định — chống chồng chéo quy tắc

Đây là phần dễ sinh nhầm lẫn nhất, nên làm đúng từng bước:

1. **Không sửa đè lên dòng quyết định cũ.** Mất lý do là mai sau lặp lại đúng
   cuộc tranh luận đã xong.
2. Đánh dấu dòng cũ là **`~~ĐÃ THAY~~`**, ghi rõ *thay bởi quyết định nào*
   và *ngày nào*.
3. Thêm dòng mới với số thứ tự kế tiếp, ghi **vì sao đổi** — không chỉ ghi
   quyết định mới là gì.
4. **Truy ngược mọi nơi đang nói theo quyết định cũ** và sửa cùng lúc:
   ```powershell
   git grep -n "<gia tri cu>"
   ```
   Sót một chỗ là tạo ra hai quy tắc mâu thuẫn — đúng thứ đang phải đi dọn.
5. Nếu quyết định cũ có **test chốt** trong `tests/test_62_khoa_logic.py` thì
   sửa hoặc gỡ test đó **trong cùng một commit**. Một test khoá quy tắc đã chết
   sẽ chặn việc đúng.
6. Ghi vào `NHAT_KY.md`: đổi gì, vì sao, đã dọn những đâu.

**Nguyên tắc gốc:** tại một thời điểm, mỗi câu hỏi chỉ được có **đúng một câu
trả lời đang hiệu lực**. Câu trả lời cũ được phép tồn tại, nhưng phải mang nhãn
"đã chết" rõ ràng để không ai làm theo nhầm.

---

## 7. Khi không chắc

Nói thẳng là không chắc, kèm cách kiểm chứng. Không đoán rồi trình bày như sự
thật. Nếu phát hiện người dùng hiểu sai điều gì, hoặc cách làm đang có vấn đề,
**nói trước khi làm** chứ đừng lặng lẽ làm theo.

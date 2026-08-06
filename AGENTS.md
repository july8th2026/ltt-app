# Quy tắc làm việc trong dự án này

Áp dụng cho mọi phiên làm việc trên `D:\LTTSTUDIOSAPP`, cho cả người và Claude.

---

## 0. Preflight bắt buộc khi mở hoặc khôi phục phiên

Mỗi phiên mới, và mỗi lần VS Code/máy vừa reset, phải tự kiểm tra trước khi tiếp
tục hạng mục đang dở:

1. Đọc mục mới nhất của `docs/NHAT_KY.md` và hạng mục mở trong
   `docs/KE_HOACH_TRIEN_KHAI.md`; **không khởi động lại từ đầu**.
2. Chạy `git status --short`; không đụng `test-results/`, `tmp/` hoặc thay đổi
   không thuộc hạng mục hiện tại.
3. Kiểm tra công cụ/browser session cần cho hạng mục và các cổng/dịch vụ liên
   quan. Dịch vụ bị tắt do reset thì khởi động lại trong đúng phạm vi đã được
   người dùng giao; không tự mở rộng sang hệ thống khác.
4. Kiểm tra permission profile thực tế. **Không được tuyên bố đã có full quyền
   chỉ vì VS Code chạy Administrator.** Sandbox/approval do host của Codex cấp,
   repo không thể tự sửa hoặc tự bấm hộp thoại `Allow once/always`.
5. Ưu tiên lệnh trong workspace và quyền hiện có. Nếu host bắt escalation, gom
   thành yêu cầu nhỏ, đúng mục tiêu và dùng auto-review/prefix hẹp khi được phép;
   không hỏi lặp cho từng file/lệnh và không tìm cách lách sandbox.
6. Gửi một cập nhật ngắn: checkpoint khôi phục, thứ đang chạy và blocker thật
   (nếu có), rồi tiếp tục tự động. Chỉ dừng hỏi người dùng khi thiếu một lựa chọn
   sản phẩm hoặc quyền ngoài repo mà agent thực sự không thể tự cấp.

**Cấu hình phía người dùng nếu muốn không hiện hộp thoại:** chọn permission
profile không cần approval cho workspace tin cậy hoặc `Allow always` cho prefix
hẹp trong UI Codex. Đây là cấu hình host, không phải file repo và agent không
được giả vờ đã bật nó.

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
- Viết code mới thì đặt đúng chỗ ngay từ đầu — xem **mục 8 (Bố cục mã nguồn)**.
  Đó là nơi ghi logic nghiệp vụ nằm ở đâu, ngưỡng phình của `routes.py`, và
  những việc dùng chung phải gọi `platform_core` chứ không chép lại.
- Không xoá test đang xanh, trừ khi có quyết định sản phẩm được ghi lại.
- Trước khi báo xong, bắt buộc chạy **một lệnh duy nhất**:
  ```powershell
  python tools\gate.py            # pytest + test 3 frontend + 2 scanner
  python tools\gate.py --quick    # bỏ full pytest, cho vòng lặp ngắn
  ```
  `python -m pytest -q` KHÔNG chạy test frontend. Chạy mỗi nó rồi báo "full
  regression xanh" là bỏ sót 77 test vitest — `tools/gate.py` sinh ra để không
  ai phải nhớ điều đó. Thêm frontend mới thì khai vào `FRONTENDS`;
  `test_145` sẽ đỏ nếu quên.
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

---

## 8. Bố cục mã nguồn — nơi từng thứ phải nằm

Chốt 2026-08-06 sau khi rà soát hệ điều hành. **Lý do có mục này:** hợp đồng app
quy định `manifest.py` / `routes.py` / `jobs.py` nhưng chưa từng nói **logic
nghiệp vụ nằm ở đâu**. Không có chỗ mặc định thì route thành chỗ để mọi thứ rơi
vào — kết quả đo được: hai file route vượt 1.300 dòng, một file 1.799 dòng
(lớn nhất repo). Debug một lỗi nhỏ phải cuộn qua sáu miền không liên quan.

### 8.1 Trong một app

```
apps/<slug>/
  manifest.py   bản khai. Nền tảng CHỈ đọc file này.
  routes.py     CHỈ lo HTTP: đọc request, kiểm quyền/CSRF, gọi service, dựng
                phản hồi. KHÔNG chứa quy tắc nghiệp vụ.
  jobs.py       handler chạy trong worker.
  services/     quy tắc nghiệp vụ khi app có NHIỀU miền (mỗi miền một file).
  features.py   quy tắc nghiệp vụ khi app chỉ có MỘT miền.
  cost.py       quy tắc tính giá, nếu tách riêng được.
  tables.py     bảng CSDL riêng của app (kèm `table_prefix` trong manifest).
```

`tables.py` chứ không phải `models.py`: `apps/taovideo/models.py` đã tồn tại và
là **sổ đăng ký model AI**, không phải bảng CSDL. Trùng tên gây hiểu nhầm ngay.

### 8.2 Ngưỡng máy kiểm — `tools/lint_app_contract.py`

| Ngưỡng | Giá trị | Vượt thì |
|---|---|---|
| `routes.py` số dòng | 900 | WARN — tách theo miền ra `services/` |
| `routes.py` số handler | 30 | WARN — như trên |
| ≥12 handler mà không có tầng nghiệp vụ | — | WARN — logic đang nằm sai chỗ |

Ngưỡng chọn theo phân bố thật: file route lớn nhất **còn đọc được** trong repo là
~870 dòng / 23 handler. Không phải con số cảm tính.

Tách `routes.py` thành package thì giữ nguyên bề mặt: `routes/__init__.py` chỉ
export `router` và import các module miền để handler kịp đăng ký.

### 8.3 Việc dùng chung thì ở `platform_core`, không ở app

App gọi vào ruột app khác = gỡ hay đổi tên app đó làm gãy app không liên quan.
Đã dính hai lần, nay có test chặn.

| Việc | Dùng | Đừng tự viết lại |
|---|---|---|
| Kiểm ảnh người dùng tải lên | `platform_core.image_input.validate_reference` | |
| Đường dẫn bundle React đã build | `platform_core.frontend_bundle.bundle_assets` | |

**Không neo đường dẫn bằng `Path(__file__).parents[n]`.** Đếm cấp thư mục sai
ngay khi file đổi chỗ, và hỏng **lặng lẽ**: tách `routes.py` thành package làm
file sâu thêm một cấp, `parents[2]` trỏ nhầm, manifest không đọc được, trang
**vẫn trả 200** với vỏ trống. Neo bằng tên thư mục (`platform_core/frontend_bundle.py`
làm mẫu). `test_148` chặn cả lớp lỗi này.

### 8.4 `platform_core` không được biết tên app nào

Kể cả trong chú thích và docstring. Đã vi phạm hai lần, cả hai đều do
`test_no_app_slug_is_hardcoded_in_the_platform` bắt.

### 8.5 Trước khi báo xong

```powershell
python tools\gate.py
```

Gate gồm: quét bí mật → lint hợp đồng app → **quét tên chưa định nghĩa** → test
3 frontend → pytest. Bước "tên chưa định nghĩa" thêm 2026-08-06 sau khi phát
hiện `POST /upscalevideo/queue` — đường nộp việc **chính** của app đó — gọi
`get_session()` mà không import: mọi lần nộp đều 500, lỗi nằm trong repo từ
2026-08-02, và không test nào chạm route đó. Test không phủ hết mọi nhánh
route; một cái tên chưa định nghĩa thì đọc tĩnh là thấy.

---

## 9. Trình duyệt và lệnh cần tương tác

Chốt 2026-08-06 sau khi mất mấy lượt dò.

### 9.1 Mở trình duyệt

Hồ sơ Chrome của dự án — **giữ đăng nhập giữa các phiên**:

```bash
playwright-cli -s=ltt open --browser=chrome --headed \
  --profile="C:\LTTBrowserProfiles\PlenXResearch" <url>
```

Ba điều bắt buộc:

- **`--headed`** — không có nó thì cửa sổ chạy **ẩn**, chủ sản phẩm không nhìn
  thấy Claude đang làm gì. Mặc định là ẩn.
- **`--profile=...`** — trỏ đúng hồ sơ đó. `--persistent` không kèm đường dẫn sẽ
  tạo hồ sơ TRẮNG, phải đăng nhập lại mọi trang.
- **`-s=ltt`** — phiên đặt tên, để không đụng phiên khác.

Hồ sơ này đang đăng nhập sẵn: Google (`vicentetuber@gmail.com`), GitHub
(`giaitritruyenthongltt-spec`).

`attach --cdp=chrome` chỉ dùng khi chủ sản phẩm đã tự bật "Allow remote
debugging" — không phải đường mặc định.

### 9.2 Lệnh cần nhập mật khẩu / xác thực

Shell của Claude **không tương tác được**. Mọi lệnh cần nhập (git push lần đầu,
đăng nhập cloud) sẽ chết với:

```
fatal: Cannot prompt because user interactivity has been disabled.
bash: line 1: /dev/tty: No such device or address
```

Mở cửa sổ mới **thôi chưa đủ** — nó kế thừa môi trường đã tắt tương tác. Phải
kèm **`-UseNewEnvironment`**:

```powershell
Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass',
  '-File','"<script>.ps1"' -UseNewEnvironment
```

Và cho script **ghi log ra file** (`Tee-Object`) để Claude đọc được lỗi thật thay
vì đoán. Không có bước này thì mọi chẩn đoán chỉ là phỏng đoán.

Ghi chú: PowerShell coi stderr của `git` là `NativeCommandError` — **không phải
lỗi**. Chỉ tin `EXITCODE`.

### 9.3 Chạy lệnh vừa cần quyền Administrator vừa cần đọc log

`Start-Process` **không cho dùng `-Verb RunAs` cùng với `-RedirectStandardOutput`**.
Hai tham số loại trừ nhau, và nó **hỏng im lặng**: không log, không thông báo
lỗi, tiến trình thoát sau một giây như thể đã chạy xong.

Đúng cách là tách hai lớp:

```powershell
# Lớp NGOÀI — nâng quyền, KHÔNG chuyển hướng
Start-Process powershell -ArgumentList '-File','"<wrapper>.ps1"' -Verb RunAs

# Lớp TRONG (trong wrapper, đã có quyền) — chuyển hướng, KHÔNG -Verb
$p = Start-Process powershell -ArgumentList '-File','"<script>.ps1"' `
       -RedirectStandardOutput $out -RedirectStandardError $err -Wait -PassThru
"EXITCODE=$($p.ExitCode)" | Add-Content $sum
```

Wrapper phải ghi `EXITCODE` ra file. `EXITCODE` **rỗng** nghĩa là tiến trình
không chạy — khác hẳn `EXITCODE=0`. Không phân biệt được hai thứ đó thì sẽ báo
"đã deploy xong" trong khi chưa có gì xảy ra.

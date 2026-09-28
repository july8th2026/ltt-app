# Quy tắc chạy lệnh nặng — máy dùng chung là máy production

> **Chủ của**: lệnh nào là nặng, bộ kiểm trước khi chạy, ngân sách lõi, hộp đen khi
> máy treo. *Khi nào* được chạy gate thuộc `docs/00_LTT_OPERATING_CONTRACT.md` §4.
> Chuyện hai lần treo máy 03/09 và số liệu điều tra: `docs/_luutru/QUY_TAC_CHAY_LENH_NANG_truoc_2026-09-16.md`.

🔑 **Dùng công cụ HẸP NHẤT trả lời được câu hỏi.** Tìm một byte trong tệp là
`read_bytes()`, không phải một lượt gate.

## 1. Phân loại

🔑 **Phân loại theo KHẢ NĂNG ĐỐT CPU, ⛔ không theo số tệp test** (chủ dự án chốt
24/09/2026). Số tệp chỉ là **một** trong ba cửa vào nhóm nặng.

| Loại | Ví dụ | Được chạy |
|---|---|---|
| **Nhẹ** | `git`, `grep`, đọc tệp, `ast.parse`, `python -c` · kiểm tĩnh/AST · **gọi máy B** | tự do |
| **Vừa** | pytest **nối tiếp** 1–2 tệp **dưới 30 giây** · một `tools\check_*.py` | tự do, một lần một |
| **Nặng** | pytest có **`-n`**, **hoặc** ≥ 3 tệp, **hoặc** > 30 giây · `gate.py` (**mọi** chế độ, kể cả `--quick`) · `test_nhanh.py` · ffmpeg / demucs / ASR / TTS / VMAF / suy luận trên card máy A · `build_system_profile.py` · đột biến (`cosmic-ray`) · nạp model thật | theo §2 |
| **Build** | `cargo` · `npm run build` · `tauri build` · `release.ps1` | **§4b** — ngoài khoá, nhưng **bắt buộc chặn lõi** |

⭐ **Không biết nó thuộc nhóm nào ⇒ ĐO một lần**: `tai_may.py` trước và sau. Quá
**30 giây** hoặc quá **2 lõi** ⇒ từ lần sau nó là **nặng**, và **ghi con số đo được
vào báo cáo** để lần sau không ai phải đo lại.

⚠️ **Ba cửa, không phải một.** Một tệp test duy nhất chạy `-n 7` vẫn là lệnh nặng;
một tệp test gọi ffmpeg 3 phút vẫn là lệnh nặng. Ngược lại, một phép kiểm `grep`
trên 1.000 tệp tài liệu là **kiểm tĩnh** — chạy thẳng, ⛔ đừng bọc `chay_nang.py`
(giữ khoá cho một việc không đốt CPU là làm cả máy đứng chờ vô cớ; xem `⭐ NHẢ
KHOÁ NGAY KHI TÍNH XONG` ở `CLAUDE.md` toàn cục).

## 2. Trước lệnh nặng — MỘT bộ kiểm, hai lệnh

```powershell
python tools\cua_so_yen.py trang-thai     # ai đang GIỮ KHOÁ
python tools\tai_may.py                   # máy có đang ĐỐT tài nguyên không
```

| Kết quả | Làm gì |
|---|---|
| có phiên khác giữ khoá (không kèm `CANH BAO: TREO`) | **chờ** — `gate.py` cũng tự xếp hàng |
| `QUÁ TẢI` | **chờ** |
| `BẬN` | thu hẹp (ít tệp hơn) hoặc chờ |
| rảnh + không ai giữ | chạy |

⚠️ **Vì sao hai lệnh chứ không một.** Chúng trả lời hai câu khác nhau:

| Lệnh | Thấy | KHÔNG thấy |
|---|---|---|
| `cua_so_yen trang-thai` | ai **đã xin khoá** | việc nặng không xin khoá: `pytest` gõ tay, bot, `demucs` rời, dịch vụ production |
| `tai_may.py` | máy đang **đốt** CPU/RAM | một lượt đang giữ khoá nhưng lúc ấy ít CPU (chờ CSDL, pha tuần tự) |

Khi chạy `gate.py`, nó tự in dòng `[tai may] … -> RANH/BAN/QUA TAI` trước khi chạy —
đọc dòng đó thay cho `tai_may.py`.

⚠️ `pid` chủ khoá vừa biến mất **chưa** có nghĩa là khoá treo — có thể đang đổi chủ.
Chỉ khi `trang-thai` in `CANH BAO: TREO` thì lượt sau tự đoạt; đừng `nha --ep`.
⛔ `cua_so_yen.py nha --ep` **không kèm `--tai-nguyen`** gỡ **mọi** khoá trên máy — kể
cả khoá của một lượt gate đang chạy. Buộc phải gỡ tay thì gỡ từng tài nguyên, và chỉ
khoá đã báo `TREO`.

Không cần: báo trước và chờ xác nhận, bọc lệnh qua `nhat_ky_chay.py`, luật "ai bấm
sau thì lùi". (`nhat_ky_chay.py` vẫn dùng được khi bạn **muốn** để lại vết.)

## 2b. HAI cửa vào khoá — chỉ cần MỘT cửa mở là phải xin

🔴 **`§2b` CỘNG THÊM một lý do xin khoá. Nó KHÔNG gỡ lý do của `§1`.**

```
Cua 1 — CO DOT CPU KHONG?      (§1: >= 2 loi hoac > 30 giay)   -> KHOA
Cua 2 — CON SO CO HONG KHI BI TRANH KHONG?  (do DO TRE)        -> KHOA
ca hai deu DONG                                                 -> chay tu do
```

⚠️ **Bẫy đã mắc thật (25/09):** một lượt E2E đo **độ trôi** (tất định ⇒ cửa 2 đóng) nhưng
**đốt ~3 lõi suốt một giờ** (cửa 1 **mở**). Đọc `§2b` một mình rồi thả khoá là sai — cửa 1
vẫn mở. ⇒ Lượt kiểu đó đi đường **`§4b`**: **ngoài khoá, nhưng chặn lõi**, chứ không phải
khoá độc quyền và cũng không phải thả tự do.

| Bạn đang đo | Tranh chấp làm gì | Cửa 2 |
|---|---|---|
| **độ trễ** — giây mỗi giai đoạn, tốc độ sản xuất | **sai số** | mở ⇒ khoá |
| **đại lượng tất định** — số đoạn, độ trôi, chrF++, CER, độ phủ | chỉ **chậm** | đóng |

⭐ **Nâng cấp: đo bằng `giây CPU` thay cho `đồng hồ tường`, rồi câu hỏi trên biến mất.**
Máy bận thì lượt chạy kéo dài, nhưng nó **không tiêu thêm chu kỳ** — nên `giây CPU` trả
lời đúng câu ta cần (*thuật toán này tốn bao nhiêu sức tính*) và miễn nhiễm với hàng xóm.

```powershell
# cong ca CAY tien trinh con (ffmpeg, worker OpenCV), don vi 100 ns
Get-CimInstance Win32_Process -Filter "ProcessId=$pid" |
  Select-Object KernelModeTime, UserModeTime
```

Báo **cả hai cột**, mỗi cột một việc:

- **`giây CPU`** ⇒ phán quyết *đáng làm không*.
- **`đồng hồ tường` + CPU nền lúc đo** ⇒ điều kiện đo, và nó bắt được ca **tường dài mà
  CPU thấp = đang CHỜ, không phải đang tính**. Một lượt gate đã lộ nguyên hình theo cách
  này: `11,7 phút tường / 7 giây CPU` — nó nghẽn ở một dịch vụ, không ở phép tính.

⛔ Đừng trung bình hai cột. Chúng trả lời hai câu khác nhau.

## 3. Bốn điều không làm

1. **Không chạy lại lệnh nặng để "xem đã sửa chưa".** Sửa xong kiểm bằng công cụ
   hẹp — hợp đồng §4.6.
2. **Không chạy nặng khi phiên khác đang chạy nặng** (§2).
3. **Không để phép đo thành nghi can.** Lấy mẫu thưa, đọc tổng máy; quét
   `process_iter` qua trăm tiến trình mỗi giây là tự đo chính mình.
4. **Viết tệp `.py` rồi chạy tệp, thay cho `python -c "..."`.** Hộp đen chỉ ghi được
   `nhan='-c inline'` ⇒ đo được mức CPU nhưng **không lần ra chủ**. Ngày 25/09 bảy tiến
   trình `-c inline` chạy cùng lúc và không ai truy được chúng của phiên nào.

## 4. Ngân sách lõi — một hàm, không chép số

`tools/gate.py::loi_cho_bo_test()` là **hàm duy nhất** quyết số worker của bộ test
trong gate. Hằng số ở ngay trong tệp đó (`LOI_DE_DANH_VAT_LY`,
`TRAN_WORKER_BO_TEST`) — đọc ở đó, đừng chép vào đây. Lý do từng số:
`docs/KE_HOACH_NGAN_SACH_LOI.md`.

- Đơn vị là **lõi vật lý** (xdist đọc lõi vật lý; `os.cpu_count()` trả lõi logic).
- `chiem = max(KHAI BÁO, ĐO ĐƯỢC)` — `max` chứ không `+`, để một phiên vừa khai vừa
  dùng không bị trừ hai lần.
- pytest **gõ tay** ≥ 3 tệp: `-n` tối đa `gate.TRAN_N_GO_TAY` (**7** lúc viết dòng
  này; chủ dự án đổi 6 → 7 ngày 23/09). ⛔ Đừng chép con số — đọc hằng số ấy trong
  `tools/gate.py`. `chay_nang.py` ép trần này, `gate.py` in lệnh gợi ý theo nó, và
  `tests/test_1280_nhip_mot_l3.py` chốt cả hai đọc cùng một chỗ (lần đổi 6 → 7 sửa
  một bên, bỏ bên kia, và gate đỏ ở đúng phép kiểm đáng lẽ bảo vệ nó).

🔴 **Windows Defender ăn tới 5,45 lõi, và nó nằm ngoài mọi khoá của ta.** Nó phản ứng
với chính cơn bão tệp tạm do bộ test sinh ra. Đo được 25/09 lúc máy chạm 100 % CPU:
`MsMpEng.exe 545 %` cạnh bảy worker python. ⇒ Trần `-n` phải **chừa biên cho nó**; một
`-n` nằm đúng trong luật vẫn làm máy đứng khi Defender đang quét. Ngoại lệ Defender cho
thư mục tệp tạm là **cấu hình bảo mật** — chỉ chủ dự án đặt (`Add-MpPreference
-ExclusionPath`), Claude không tự đặt.

⚠️ **Tiến trình cháu không nằm trong `-n`.** Một worker gọi model thật (`demucs`,
`whisper`, TTS) thành ~10 luồng torch. ⇒ Test nạp model thật nằm sau rào
`LTT_TEST_NANG` (`tests/rao_chan_nang.py`, marker `nang`).

## 4c. ⭐ BA tầng canh CPU — và vì sao thiếu một tầng thì hai tầng kia vô dụng

**Chuẩn hoá 28/09/2026** sau lần treo máy thứ ba. Ba tầng, mỗi tầng bắt một loại hộ
tiêu thụ mà hai tầng kia **không thể** thấy:

| tầng | ai bắt | thứ nó thấy | thứ nó KHÔNG thấy |
|---|---|---|---|
| **1. khai báo** | `cua_so_yen` (`so_loi`) | phiên đã **XIN khoá** | pytest gõ tay, build, tiến trình mồ côi |
| **2. trần tại hộ** | `torch.set_num_threads`, `chan_loi()`, `-n`, `--maxWorkers` | hộ ta **biết tên** | thư viện mới mặc-định-lấy-hết-lõi |
| **3. van ĐỘNG** | `gate._chay_theo_lich._do_lai_tran`, `tai_may.do()` | **CPU thật**, bất kể ai đốt | — (nhưng chỉ *phản ứng*, không ngăn trước) |

🔴 **Tầng 3 vừa được lắp 28/09; trước đó nó chỉ tồn tại một nửa.** `loi_dang_ban()`
có từ 03/09 và đo đúng — nhưng nó được lấy mẫu ở **đúng hai chỗ, cả hai lúc khởi
động**. Nên ngân sách lõi là một **hằng số suốt lượt**, và mọi tải **đến sau** đi
qua miễn phí: Windows Defender (5,45 lõi), một `RapidOCR` 15,2 lõi nằm trong một
worker pytest (`docs/auto_scan_video_final/B12_...md`), một tiến trình mồ côi.

### Bốn lỗ đã vá, và hình dạng chung của chúng

| # | lỗ | tệp |
|---|---|---|
| 1 | `_chay_theo_lich` lấy ngân sách **per-RUN**: `tru_phien_khac` là **mã chết** từ 03/09 — có tài liệu, có phép kiểm riêng, **không nơi nào truyền `True`** ⇒ hai lượt gate song song đều lấy 8 lõi trên một máy 10 lõi | `tools/gate.py` |
| 2 | bộ đếm lõi là hằng số ⇒ tải đến sau không ai trừ | `tools/gate.py` (van động + `SAN_LOI_DONG`) |
| 3 | `tai_may.do()` phán quyết **chỉ theo RAM**, mà `chay_nang.py` chờ theo đúng hàm này ⇒ máy bị chiếm 9,5/10 lõi vẫn trả `RANH` | `tools/tai_may.py` |
| 4 | `conftest` xin `cpu_nhieu` mà **không khai `so_loi`** ⇒ `loi_da_hua` rơi về mặc định **8**, nên một `pytest -n 2` gõ tay làm mọi phiên khác tụt ngân sách về sàn | `tests/conftest.py` |

⭐ **Không lỗ nào sai một con số.** Cả bốn sai ở chỗ **ai đọc con số ấy**: một hàm đo
đúng tải rồi không ai gọi, một phép đo đúng rồi không lấy mẫu lại, một phán quyết
đúng về RAM rồi bị hỏi về CPU, một con số biết rõ rồi không khai. ⇒ Khi rà một cơ
chế an toàn, câu hỏi đắt nhất **không** phải *"con số này đúng chưa?"* mà là
***"ai đọc nó, và họ đọc lúc nào?"***

### Vận hành — thứ tự rẻ dần, dùng từ trên xuống

1. **`--ho-so doi` (L1)** cho mọi lượt trong phiên. Khi hạ cấp nó **bỏ** `bo test`
   — tức bỏ đúng bước chiếm ~85 % thời gian và 7 worker. Lượt nhẹ nhất.
2. **`-j 2..3`** khi cần chạy nhóm tĩnh mà máy đang có phiên khác.
3. **`--noi-tiep`** khi cần một con số **không bị nhiễu**: một bước một lúc, MỘT
   tiến trình pytest.
4. ⛔ **`--ho-so day-du` chỉ ở cuối plan, và chỉ khi `tai_may` nói `RANH`.** Số học
   của lần treo 28/09: `7` worker + `-j 8` bước tĩnh + `~5,4` Defender trên **10**
   lõi vật lý.

### Đọc dòng `[tai may]` thế nào

```
[tai may] 0.8/10 loi VAT LY dang ban -> RANH
```

⚠️ Dòng này **từng trộn ba đơn vị** (vá 28/09): ngưỡng so với hằng số 20-thang,
mẫu số in ra là 20 trong khi tử số tối đa là 10. Hậu quả: một máy bận **60 %** in ra
`RANH`, và `6.0/20` đọc như 30 %. ⇒ Bản ghi gate cũ hơn 28/09 có dòng `[tai may]`
**không so sánh được** với bản mới.

### Ngưỡng của `tai_may` — đơn vị LÕI, không phải phần trăm

`tai_may.py` **cố ý** không có ngưỡng CPU theo phần trăm (nền máy này dao động gần
mười lần trong ngày). Cửa mới là một phép trừ **có đơn vị**: *còn bao nhiêu lõi vật
lý rảnh*. `< 3` ⇒ `BAN`, `< 2` ⇒ `QUA TAI`. Con số 3 chọn để Defender **một mình**
(5,45 lõi ⇒ còn 4,55) ⛔ **không** chặn được lệnh nặng — `chay_nang.py` chờ 30 phút
rồi *thoát 3 = không chạy*, nên mỗi lần bắt oan là một lệnh nặng bị huỷ ở **mọi**
phiên. Cùng họ *"báo động giả làm người ta TẮT cổng"*.

⭐ `chay_nang.py` nằm **ngoài kho** (`~/.claude/ltt/`) nhưng vòng chờ của nó đọc
`tools/tai_may.py`, nên nó **tự hưởng** cửa mới — ⛔ không cần sửa tệp ngoài kho, và
mọi phiên của mọi dự án được che cùng lúc.

Phép kiểm: `tests/test_5610_van_dong_cpu_va_cua_loi_ranh.py` (có tiêm lỗi đối chứng
cho cả bốn lỗ).

## 4b. Build (`cargo` / `npm` / `tauri`) — chạy NGOÀI khoá, NHƯNG phải bị chặn lõi

**Chủ dự án chốt 23/09:** một lượt build phần lớn thời gian chỉ ăn vài lõi mà **chặn cả hàng**
15–20 phút, nên build **không đi qua khoá `cpu_nhieu`** nữa.

⚠️ **Nhưng tiền đề "build chỉ 2 lõi" KHÔNG đúng với số đo.** Đo lượt dựng
`LTTCODE 0.2.7` (23/09, cây tiến trình `cargo`/`rustc`/`link`/`node`/`makensis`, mẫu 5 giây):

| | Lõi |
|---|---|
| Trung vị | **2,99** |
| Trung bình | 3,95 |
| **Đỉnh** | **18,67** ← gần cả máy 20 lõi |

Build **không có một con số**: dài và mỏng (npm, link, đóng gói NSIS 293 MB) xen những đợt
codegen ngắn ăn gần hết máy. Thả một build **không giới hạn** ra ngoài khoá là mời lại đúng
sự cố 23/09 (gate + agent cộng dồn 14/20 lõi rồi CPU quá tải ngắt).

⇒ **Luật: build chạy ngoài khoá KHI VÀ CHỈ KHI nó bị chặn lõi tường minh.**

```bash
# Windows / Git Bash
CARGO_BUILD_JOBS=3 npm_config_jobs=3 pwsh -NoProfile -File tools/release.ps1 ...
```

- `CARGO_BUILD_JOBS` chặn pha codegen — **pha duy nhất** từng chạm 18 lõi.
- Không đặt biến này ⇒ **phải đi qua khoá** như cũ. Không có đường thứ ba.
- Vẫn kiểm `tai_may.py` trước: `QUÁ TẢI` ⇒ chờ, dù có chặn lõi.

### ✅ ĐÃ KIỂM CHỨNG (24/09, dựng LTTCODE 0.2.8) — chặn lõi ăn thật, và KHÔNG tốn thêm thời gian

Lượt dựng đầu tiên có `CARGO_BUILD_JOBS=3`, đo **trọn** (bộ đo bám theo tiến trình build chứ không
theo đồng hồ — 379 mẫu, 18,9 phút, phủ ~100 %):

| | Không chặn (0.2.7) | **Chặn `=3` (0.2.8)** |
|---|---|---|
| Đỉnh | **18,67 lõi** | **2,01 lõi** |
| p50 | 2,99 | **1,00** |
| Trung bình | 3,95 | **0,80** |
| Số mẫu vượt 3 lõi | có | **0 / 379** |
| **Thời gian tường** | **18,6 phút** (giữ khoá cả máy) | **18,9 phút** (ngoài khoá) |

🔑 **Hai kết luận, cái thứ hai quan trọng hơn:**

1. `CARGO_BUILD_JOBS` **khống chế được thật** — 0/379 mẫu vượt 3 lõi. Điều kiện của luật 4b đứng vững.
2. **Chặn lõi gần như không tốn thời gian: 18,6 → 18,9 phút (+1,6 %).** Tức những đợt codegen
   18,67 lõi ở bản không chặn **không mua được tốc độ nào** — chúng chỉ cướp máy của phiên khác.
   Đổi 15 lõi rảnh lấy 18 giây là món hời hiếm thấy.

⇒ Không còn lý do gì để build chạy không chặn lõi. Luật 4b **không phải sự thoả hiệp**, nó là
lựa chọn tốt hơn ở cả hai chiều.

**Độ phủ của phép đo CŨ (bản không chặn): chỉ 2,5 / 18,6 phút ≈ 13 %** (bộ đo phần lớn thời gian đang đếm một
lượt build **xếp hàng** rồi chết vì cây bẩn). ⇒ Con số 18,67 là **sàn của đỉnh**, không phải
đỉnh thật. Lượt build tới phải đo **trọn**, và đo **bản đã chặn lõi**, để xác nhận đỉnh thật sự
nằm dưới số đã chặn. Chưa có phép đo đó thì đừng nâng `CARGO_BUILD_JOBS` lên quá 3.

### Kiểm tiền đề TRƯỚC khi xếp hàng

Cùng ngày: một lượt build chờ khoá **15,2 phút**, đến lượt rồi **chết sau 0,1 phút** vì
`git status` bẩn — một phép kiểm **không tốn lõi nào** và biết được từ trước. Lệnh nặng phải
kiểm hết tiền đề rẻ (cây sạch, tệp tồn tại, biến môi trường, khoá ký) **trước khi xin khoá**.
Chiếm một chỗ trong hàng rồi trả lại mà không tính phép nào cũng là một dạng lãng phí khoá,
ngang với giữ khoá lúc chờ.

## 5. Máy vừa treo — hộp đen

Chạy **đầu tiên** sau một lần treo/reset:

```
C:\Users\Thang Tuong\Desktop\HOP DEN\KHAM.bat      (= python giam_sat_may.py --kham 3)
```

Hộp đen ghi liên tục CPU/RAM/swap/đĩa + GPU/VRAM/nhiệt/điện + tiến trình nặng nhất,
`fsync` từng dòng, tự chạy khi đăng nhập. Nó tìm chỗ log **đứt**, xếp hạng tiến
trình ở các mẫu ngay trước đó và so với nền của chính máy. ⛔ Nó **không kết luận
nguyên nhân** — phần đó của người đọc.

⚠️ Hộp đen ghi giờ **UTC**; máy ở **UTC+7**. ⇒ 02:00 giờ máy nằm ở tệp **hôm sau**.

⭐ **Đọc `so_tien_trinh` cạnh `cpu`.** CPU một mình không giải thích được mọi sự cố: ngày
25/09 PostgreSQL chết lúc CPU chỉ **19,6 %** — máy rảnh. Tín hiệu thật là `so_tien_trinh`
**sụt 347 → 308 trong 15 giây**: ~45 tiến trình biến mất cùng lúc, tức một cú giết cây
tiến trình, không phải quá tải.

🔴 **Giết tiến trình — bốn luật, luật cuối là hàng rào.** Một cú giết cây làm
**PostgreSQL production sập 4 phút** (25/09):

1. In `CommandLine` của **từng** pid trước khi giết, để người đọc thấy mình sắp giết gì.
2. `taskkill /T /PID <một pid ĐÃ XÁC MINH>`.
3. Một pid làm gốc duyệt — **`Where-Object` trả về mảng** thì mỗi phần tử phải kiểm riêng.
4. ⭐ **Từ chối mọi pid có cha là `services.exe`.** Ba luật đầu dựa vào ta cẩn thận; luật
   này làm cả lớp sự cố **không thể xảy ra** dù ta cẩu thả.

Đối chiếu thêm: nhật ký sự kiện Windows (`Kernel-Power 41` + `BugCheckCode = 0` =
mất nguồn/reset cứng, không phải quá tải phần mềm) · `ListAgents` (phiên khác).

⭐ Trước khi dựng một phép đo mới, tìm xem phép đo đó **đã tồn tại** chưa.

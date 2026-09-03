# KẾ HOẠCH — ngân sách lõi cho `gate.py` / `test_nhanh.py`

Đo 2026-09-03 trên máy production (20 lõi logic / 10 vật lý, 32 GiB, 4 dịch vụ đang phục vụ khách).
Trạng thái: **chưa sửa mã**. Đây là kế hoạch, không phải báo cáo.

## Vì sao có kế hoạch này

Ba phép đo, mỗi cái phủ nhận một giả định đang được dùng:

| Đo được | Giả định bị phủ nhận |
|---|---|
| `gate` truyền `-n 11`, xdist `auto` = **10** | "ngân sách lõi làm giảm tải" — trên máy này nó **tăng** |
| 2 lượt gate + nền = **33/20 lõi** | "cửa sổ yên đủ để chống nghẽn" — ngân sách là per-RUN |
| `cua_so_yen` báo RẢNH khi CPU 65% | "khoá thấy được tải" — nó chỉ thấy ai *xin* khoá |

Nguyên nhân gốc của cái thứ nhất: `ngan_sach_loi()` tính trên lõi **logic** (`os.cpu_count()` = 20),
xdist `auto` tính trên lõi **vật lý** (`psutil.cpu_count(logical=False)` = 10). Hai đơn vị khác
nhau bị trừ cùng một hằng số `LOI_DE_DANH_CHO_MAY = 6`.

⭐ Trên máy không siêu phân luồng, hai số trùng nhau và lỗi **không tồn tại**. Nó chỉ lộ ra ở
máy có SMT — tức đúng loại máy này.

## Nguyên tắc, theo thứ tự ưu tiên

1. **Đặt trần, đừng gán.** `min(ngân_sách_ta, câu_trả_lời_của_công_cụ)`. Một ngân sách là
   *giới hạn trên*. Gán thẳng thì khi công cụ tự đo ra số nhỏ hơn, "trần" lại thành sàn.
2. **Không bao giờ từ chối chạy.** Cổng từ chối chạy vì bận là cổng sẽ bị vô hiệu bằng một cờ
   `--bo-qua`. Chen thì chạy **nhỏ**, không phải không chạy.
3. **Không đợi thứ mình không kết thúc được, trong lúc đang giữ khoá.** Mọi phép đo tải đặt
   **trước** khi xin khoá.
4. **Đơn vị phải khớp.** Mọi hằng số ghi rõ nó đo bằng lõi logic hay vật lý.

## Bốn bước, theo thứ tự phụ thuộc

### B0 — `min` với câu trả lời của công cụ  ⟵ **làm trước, độc lập, sửa lỗi đang sống**

```python
def loi_cong_cu_tu_do() -> int:
    """Số worker xdist `auto` sẽ tự chọn. Cùng nguồn với `xdist/plugin.py:32`."""
    try:
        import psutil
        return psutil.cpu_count(logical=False) or psutil.cpu_count() or 1
    except ImportError:
        return os.cpu_count() or 1
```

`loi_bo_test = min(<ngân sách>, loi_cong_cu_tu_do())`

- **Chốt:** `test_ngan_sach_khong_bao_gio_vuot_auto` — với mọi `cpu_count` giả lập (2, 4, 10,
  20, 64), số truyền cho `-n` phải `<= loi_cong_cu_tu_do()`. Kèm self-test chứng minh bộ dò
  bắt được một bản gán thẳng.
- **Rủi ro:** `psutil` vắng ⇒ rơi về `os.cpu_count()` (logic) ⇒ lại lệch đơn vị. Nhánh fallback
  phải chia đôi hoặc dùng `-n auto` thay vì một số.

### B1 — ghi `so_loi` vào bản ghi khoá  ⟵ *cần cho B2, tự nó không đổi hành vi*

`cua_so_yen.thu_giu(..., so_loi=N)`; `CuaSoYen.__init__` nhận và truyền xuống.

- ⛔ **`so_loi` vắng ≠ 0 lõi.** Bản ghi cũ đọc ra 0 nghĩa là *"không khai"*. Tính nó bằng 0 là
  **fail-open** — đúng cái quá tải cần chặn, chỉ khác là im lặng. Đọc 0 mà bản ghi có tài
  nguyên `cpu_nhieu` ⇒ tính bằng một giá trị dè dặt (fail-**closed**).
- **Chốt:** một bản ghi không có khoá `so_loi` phải làm ngân sách **giảm**, không phải giữ nguyên.

### B2 — ngân sách per-MÁY

`ngan_sach_loi()` trừ Σ `so_loi` của các phiên **khác** đang giữ (bỏ qua khoá treo). Giữ
`max(2, …)`.

- ⚠️ **Phải lấy số SAU khi giữ khoá.** `gate.py:224` tính `loi_bo_test` **trước**
  `CuaSoYen.__enter__`, và `argv` đã cố định `-n <số>`. Tính lại con số mà không dựng lại `argv`
  thì nó trừ đúng và **vẫn chạy 11 worker**. ⇒ `Step` phải giữ một **hàm dựng argv trễ**.
- **Chốt:** hai bản ghi khoá giả → ngân sách giảm đúng bằng tổng; khoá treo không được trừ.

### B3 — chen thì chạy nhỏ

Hết `--cho` mà vẫn chạy (`cua_so_yen.py:270-277`): ngân sách = **phần còn lại**, không phải full.

- **Chốt:** chốt vào **con số thật sự truyền cho `-n`**, không vào một cờ báo rằng nó đã thu nhỏ.

## Hai hằng số cần đo lại — việc riêng, không gộp vào bản sửa

| Hằng số | Vấn đề |
|---|---|
| `LOI_DE_DANH_CHO_MAY = 6` | đo từ CPU nền 27% ≈ 5,4 lõi **logic** ≈ 2,7 **vật lý**. Chuyển ngân sách sang đơn vị vật lý mà giữ 6 thì trừ gấp đôi |
| `LOI_TOI_DA_MOI_CONG_CU = 12` | trần của **vitest** (`min(12, n-1)`), theo đơn vị của vitest. Dùng chung cho xdist là mượn qua biên đơn vị lần thứ hai |

⚠️ Nền CPU biến động ~10× trong ngày (27% lúc 13h, 3% lúc 21h — đo bởi `lttstudiosapp-73`).
Nên mọi hằng số suy từ một lần đo đều là hằng số của *một thời điểm*. Đó là lý do B0–B3 ưu tiên
**đo lúc chạy** hơn là chỉnh hằng số.

## Điều KHÔNG làm, và vì sao

- **Không nối `tai_may.py` vào gate.** Gate đã có hai lớp CPU (ngân sách + `BELOW_NORMAL_PRIORITY_CLASS`).
  `tai_may.py` phán quyết theo **RAM**, thứ hai lớp kia không che. Hai công cụ, hai câu hỏi.
- **Không sửa "hết chờ thì vẫn chạy"** thành dừng. Đó là quyết định thiết kế có luận cứ; B3 giải
  quyết cùng vấn đề mà không đảo ngược nó.
- **Không đặt `PYTHON_CPU_COUNT`** để gò xdist. Đo thật: nó đổi `os.cpu_count()`, nhưng
  `xdist/plugin.py:32` hỏi **psutil**, không hỏi `os` — nên nó không với tới. (Suýt kết luận
  ngược; phép đo đúng, đo nhầm thứ.)

## 🔴 CẬP NHẬT 03/09 — máy vẫn reset SAU KHI B0–B3 đã áp dụng

Chủ dự án phải reset máy trong lúc gate chạy với B0–B3 đã có. **Cơ chế đúng phạm vi,
nhưng phạm vi đó là thiểu số.** Số đo lấy ngay trước khi reset:

```
cây gate (pid 12720):  13 tiến trình  — 1 test_nhanh + 2 pytest + 10 worker  ✓ đúng ngân sách
CPU cây gate:          41–48% máy
CPU toàn máy:          58–69%, có mẫu 95–100%
python toàn máy:       58 tiến trình      <- gate chỉ là 13/58
```

⇒ B0–B3 điều tiết đúng 13 tiến trình đó. **45 cái còn lại không đi qua cơ chế nào.**

⛔ **Ba ứng viên, và tôi KHÔNG phân biệt được** — máy reset nên bằng chứng mất hết:
   gate (13 tiến trình, đúng ngân sách) · 45 tiến trình python ngoài gate · **chính phép đo
   của tôi** (`process_iter` quét 58 tiến trình, `cpu_percent` từng cái, lặp 5 lần).

⇒ Đoán bây giờ là vô ích. Thêm `tai_may.py --ai` để **lần sau có dữ liệu** thay vì một giả
  thuyết. Chạy nó TRƯỚC mỗi lượt nặng và giữ kết quả.

⚠️ Và một số đo mới, sau reset, khi không chạy gì: **19 tiến trình python nền, CPU 37%**.
   `LOI_DE_DANH_CHO_MAY = 6` được đặt từ giả định nền 27% ≈ 5 lõi. 37% ≈ 7,4 lõi. Nếu con số
   này giữ khi máy ổn định thì hằng số 6 đang **thiếu** — nhưng một phép đo ngay sau reset là
   phép đo của một máy đang khởi động lại dịch vụ, chưa kết luận được.

## Điều tra 03/09 — bot của `D:\FULL AUTO VIDEO`

Chủ dự án nghi bot ở kho tham chiếu chiếm CPU. Kiểm (read-only):

**CÓ chạy** — 8 tiến trình `FULL AUTO VIDEO` + 22 `BOT GEMINI`, tự khởi động lại lúc 13:55
sau reset:
```
cmd.exe /c D:\FULL AUTO VIDEO\start_gui.bat
python.exe run_master_g...        (DUNGVIDEO-FULLenv)
pythonw.exe D:\FULL AUTO VIDEO\...
D:\BOT GEMINIenv\...\python.exe main.py      <- bot production cong 8000
```

**Nhưng lúc reset nó đang NGỦ** — `DUNGVIDEO-FULL/logs/dungvideo_debug.log`:
```
13:46:37  NO JOB (no row matched conditions across all tabs)
13:46:37  SLEEP 300s (khong job)
13:48:37  SLEEP 300s — con 180s        <- log dung o day, may reset ~13:52
```
Cac bot khac (`Bot_PausePipeline`, `CUT CLIP SHORT`, `Phantichvideo`) **khong co log nao sau
13:00** ⇒ khong chay. `master_gui/crash.log` sua luc 13:59, tuc SAU reset.

⇒ Theo nhat ky, bot **khong phai thu pham lan nay**. Nhung:

### 🔴 Bot KHONG kiem tai truoc khi chay — rui ro nay la THAT va co CAU TRUC

`grep cpu_percent|virtual_memory` trong `DUNGVIDEO-FULL/engine`, `master_gui`, `bot_logger.py`
⇒ **khong co dong nao**. Bot nhan job tu Google Sheet va chay ngay.

Nen kich ban chu du an mo ta la co that: **bot nhan job dung luc gate chay thi khong co gi
ngan ca hai cung chay.** Bot khong biet gate ton tai; gate khong biet bot ton tai;
`cua_so_yen` khong nhin thay ca hai. Lan nay chi la bot tinh co dang ngu.

### Va buc tranh that: gate chi la mot trong RAT NHIEU

Dem duoc luc dieu tra: 4 phien Claude · Codex · playwright-mcp · node · pwsh ·
`BOT GEMINI` (22 tien trinh) · `FULL AUTO VIDEO` (8) · 4 dich vu `LTTPlatform` · gate (13).

⇒ Ngan sach loi B0-B3 dieu tiet **13**. Do la thiet ke dung cho pham vi cua no, va pham vi
  do la thieu so. Khong co co che nao o tam MAY.

## 🔴 ĐÍNH CHÍNH — bot CÓ `ResourceGuard`, nhưng nó gần như vô hiệu

Tôi kết luận *"không một dòng nào"* sau khi quét **hẹp** (`DUNGVIDEO-FULL/engine`,
`master_gui`, `bot_logger.py`). Một lượt quét **rộng** tìm ra `bot_coordination.py`:

```python
bot_coordination.py:429   cpu = psutil.cpu_percent(interval=0.1)
bot_coordination.py:436   free_gb = psutil.virtual_memory().available / 1024**3
```

⛔ Lần thứ chín của cùng một lỗi: **một kết quả rỗng từ phép quét hẹp không phải bằng chứng
   vắng mặt.** Ghi lại vì nó đúng bằng lỗi `lttstudiosapp-73` mắc (`0/15`) và lỗi tôi mắc ở
   Phase 02 (đọc import list mà không kiểm bề mặt khai báo).

### Nhưng cơ chế đó gần như không đóng — và lý do đã được ghi ngay trong mã

```python
CPU_MAX_PERCENT = 98   # [Phase F3] 92→98: nguong cu chan job khi DEMUCS/Whisper
                       # burst CPU >92% (DUNGVIDEO chi chay duoc 2 job/4h).
RAM_MIN_FREE_GB = 2.0  # may 32 GiB
```

⭐ **Đây chính xác là kịch bản plan này đã cảnh báo**, xảy ra thật ở một hệ thống khác: một
   cửa chặn quá chặt thì người ta không gỡ nó — họ **nới ngưỡng** cho tới khi nó không còn
   chặn gì. 92 → 98 không phải tinh chỉnh, nó là vô hiệu hoá bằng con số.

### Và bot đang chạy KHÔNG gọi nó

`DUNGVIDEO-FULL/bot/worker.py:41` chỉ import `GpuSlot, VramBudget`; dòng 1099 thêm
`PhaseRegistry`. **`ResourceGuard` không xuất hiện.** Bot giành GPU slot và VRAM budget —
không hỏi CPU/RAM.

## Cộng đồng: xdist KHÔNG có cơ chế tự co giãn theo tải

Tra `pytest-dev/pytest-xdist` — 6 issue về `numprocesses`/load, **không cái nào** là
load-aware scaling. `-n auto` = số lõi vật lý, **cố định lúc khởi động**, không đọc lại.

⇒ Lời giải "worker tự co giãn theo CPU rảnh" **không tồn tại ở tầng xdist**. Ai muốn nó phải
  tự viết — và tự viết một bộ điều tiết là tự nhận một bài toán điều khiển.

⭐ Lời giải "auto" thật sự **đã có sẵn, ở tầng hệ điều hành**: `BELOW_NORMAL_PRIORITY_CLASS`.
  Nó không đếm, không đoán, không cần ngưỡng — OS nhường CPU **đúng lúc có ai cần**. Đó là
  auto-scaling đúng nghĩa, và nó miễn phí trên máy rảnh.

  ⚠️ Trần của nó: chỉ xếp hàng CPU. Không nhường RAM, và **không phân xử giữa hai tiến trình
     cùng ưu tiên thấp** — hai lượt gate, hoặc gate với một bot cũng chạy ưu tiên thường.

## Điều tra "gate ⨯ pytest xung đột" — BÁC BỎ, và cái thật nằm chỗ khác

Chủ dự án nghi gate và pytest giẫm nhau. Đo hai mặt:

**Mặt 1 — tranh lõi trong nội bộ gate: KHÔNG.** Đo luồng thực tế của 6 bước tĩnh bằng cách
chạy chính `argv` của chúng và đếm tiến trình con:

```
buoc                   khai  that   CPU dinh
secret scan               1     1        5%
ky tu dieu khien          1     1        5%
system profile            1     1        5%
chuoi chua dich           1     1        5%
bien dich duoc            1     1        5%
ten chua dinh nghia       1     1        5%
```

Khai báo **trung thực**. Bộ đếm `_chay_theo_lich` giữ tổng ≤ 14: `bo test` lấy 10, còn 4 cho
các bước tĩnh xếp hàng. Nhóm `sau_test` (5 bước) chạy **sau** `bo test`, không tranh.

**Mặt 2 — tranh tệp: đã có cơ chế.** `TEP_KHONG_DUOC_DOC_SONG_SONG` khai 4 tệp mà bộ test ghi
và bước tĩnh đọc, sau sự cố `Errno 22` ngày 29/08 (hai phiên mất gần trọn một ngày, và cả hai
đều đổ cho nguyên nhân sai).

### ⇒ Cái thật: ngân sách TĨNH, nền ĐỘNG

```
                               lõi
nền thật (đo 03/09 14:2x)      1.7
LOI_DE_DANH_CHO_MAY (giả định)   6
bo test                         10
bước tĩnh (tối đa còn lại)       4
─────────────────────────────────
TỔNG khi gate chạy            15.7 / 20   -> OK
```

Nhưng nền **biến động ~10 lần trong ngày**, đo được ở bốn thời điểm khác nhau:

```
 3%  lúc 21h        1.7 lõi  ->  tổng 15.7/20   OK
 8%  lúc 14h        1.7 lõi  ->  tổng 15.7/20   OK
27%  lúc 13h        5.4 lõi  ->  tổng 19.4/20   sát trần
37%  ngay sau reset 7.4 lõi  ->  tổng 21.4/20   VƯỢT 1.4 lõi
```

⇒ **`LOI_DE_DANH_CHO_MAY = 6` là một hằng số cho một nền động.** Nó đúng ở phần lớn thời
  điểm và sai ở đúng lúc quan trọng nhất — khi máy đang bận, tức khi bảo vệ mới có nghĩa.

⭐ Đây chính là câu hỏi chủ dự án đặt từ đầu ("có phương án tự co giãn theo CPU rảnh không"),
  và giờ nó có bằng chứng: **có, và nó cần thiết**. Lời giải đã tồn tại ở nhánh của
  `lttchat-…-49`: `loi_dang_ban()` + `ngan_sach_loi(do_tai=True)` trừ phần tải **vượt nền**.
  Việc còn lại là hợp nhất nó với `tru_phien_khac` của B2 thành **một** tham số.

## Nghiệm thu

1. `-n` truyền cho pytest **≤** `psutil.cpu_count(logical=False)` trong mọi cấu hình.
2. Hai lượt gate song song: tổng worker ≤ ngân sách máy, chứng minh bằng bản ghi khoá.
3. Bản ghi khoá cũ (không có `so_loi`) làm ngân sách **giảm**.
4. Mỗi bộ dò kèm self-test hai chiều (một mẫu phải bắt, một mẫu phải im).
5. `tools/gate.py` đầy đủ xanh, và **thời gian không tăng** — nếu B0 làm gate chậm hơn thì trần
   đang đặt sai chỗ, không phải máy đang được bảo vệ tốt hơn.

## Phối hợp

`lttchat-…-49` đang mở `tools/gate.py` (thêm `--noi-tiep`, `loi_dang_ban()`). Họ commit trước,
tôi sửa trên nền sạch. Cả hai không chạm `tools/` + `tests/` khi có lượt gate đang chạy —
`_anh_chup_cay()` soi cả hai thư mục.

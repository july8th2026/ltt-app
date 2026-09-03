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

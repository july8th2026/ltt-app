# Quy tắc chạy lệnh nặng — máy dùng chung là máy production

> **Chủ của**: lệnh nào là nặng, bộ kiểm trước khi chạy, ngân sách lõi, hộp đen khi
> máy treo. *Khi nào* được chạy gate thuộc `docs/00_LTT_OPERATING_CONTRACT.md` §4.
> Chuyện hai lần treo máy 03/09 và số liệu điều tra: `docs/_luutru/QUY_TAC_CHAY_LENH_NANG_truoc_2026-09-16.md`.

🔑 **Dùng công cụ HẸP NHẤT trả lời được câu hỏi.** Tìm một byte trong tệp là
`read_bytes()`, không phải một lượt gate.

## 1. Phân loại

| Loại | Ví dụ | Được chạy |
|---|---|---|
| **Nhẹ** | `git`, `grep`, đọc tệp, `ast.parse`, `python -c` | tự do |
| **Vừa** | một–hai tệp test, một `tools\check_*.py` | tự do, một lần một |
| **Nặng** | `gate.py` (**mọi** chế độ, kể cả `--quick`) · `test_nhanh.py` · ≥ 3 tệp test · `build_system_profile.py` · đột biến (`cosmic-ray`) · nạp model thật | theo §2 |

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

## 3. Ba điều không làm

1. **Không chạy lại lệnh nặng để "xem đã sửa chưa".** Sửa xong kiểm bằng công cụ
   hẹp — hợp đồng §4.6.
2. **Không chạy nặng khi phiên khác đang chạy nặng** (§2).
3. **Không để phép đo thành nghi can.** Lấy mẫu thưa, đọc tổng máy; quét
   `process_iter` qua trăm tiến trình mỗi giây là tự đo chính mình.

## 4. Ngân sách lõi — một hàm, không chép số

`tools/gate.py::loi_cho_bo_test()` là **hàm duy nhất** quyết số worker của bộ test
trong gate. Hằng số ở ngay trong tệp đó (`LOI_DE_DANH_VAT_LY`,
`TRAN_WORKER_BO_TEST`) — đọc ở đó, đừng chép vào đây. Lý do từng số:
`docs/KE_HOACH_NGAN_SACH_LOI.md`.

- Đơn vị là **lõi vật lý** (xdist đọc lõi vật lý; `os.cpu_count()` trả lõi logic).
- `chiem = max(KHAI BÁO, ĐO ĐƯỢC)` — `max` chứ không `+`, để một phiên vừa khai vừa
  dùng không bị trừ hai lần.
- pytest **gõ tay** ≥ 3 tệp: `-n` tối đa **6** (hợp đồng §4.1).

⚠️ **Tiến trình cháu không nằm trong `-n`.** Một worker gọi model thật (`demucs`,
`whisper`, TTS) thành ~10 luồng torch. ⇒ Test nạp model thật nằm sau rào
`LTT_TEST_NANG` (`tests/rao_chan_nang.py`, marker `nang`).

## 5. Máy vừa treo — hộp đen

Chạy **đầu tiên** sau một lần treo/reset:

```
C:\Users\Thang Tuong\Desktop\HOP DEN\KHAM.bat      (= python giam_sat_may.py --kham 3)
```

Hộp đen ghi liên tục CPU/RAM/swap/đĩa + GPU/VRAM/nhiệt/điện + tiến trình nặng nhất,
`fsync` từng dòng, tự chạy khi đăng nhập. Nó tìm chỗ log **đứt**, xếp hạng tiến
trình ở các mẫu ngay trước đó và so với nền của chính máy. ⛔ Nó **không kết luận
nguyên nhân** — phần đó của người đọc.

⚠️ Hộp đen ghi giờ **UTC**; máy ở **UTC+7**.

Đối chiếu thêm: nhật ký sự kiện Windows (`Kernel-Power 41` + `BugCheckCode = 0` =
mất nguồn/reset cứng, không phải quá tải phần mềm) · `ListAgents` (phiên khác).

⭐ Trước khi dựng một phép đo mới, tìm xem phép đo đó **đã tồn tại** chưa.

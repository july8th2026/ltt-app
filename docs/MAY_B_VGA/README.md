# MAY_B_VGA — mod card máy B (lưu trữ để dò tìm và khôi phục)

Mod chỉ xung NHỚ, áp ngày 22/09/2026: RTX 3090 +750 MHz, RTX 5060 Ti +1000 MHz; xung nhân, điện áp,
power limit và VBIOS giữ mặc định. Nhật ký: `docs/NHAT_KY.md`, mục 2026-09-22 (tối).

**Có sự cố VGA trên máy B ⇒ đọc `Setup_VGA.md` trước** (mục 5 kiểm tra, mục 6 khôi phục). Bản đang chạy của
sổ tay và script nằm trên máy B; thư mục này là bản lưu để dò tìm từ máy A và để dựng lại khi máy B mất tệp.

| Tệp | Là gì | Bản đang chạy trên máy B |
|---|---|---|
| `Setup_VGA.md` | Sổ tay vận hành + khôi phục (đọc đầu tiên) | `C:\Users\lengo\OneDrive\Desktop\Setup_VGA.md` và `C:\Tools\ModCard\Setup_VGA.md` |
| `kiem_vga.py` | Kiểm cấu hình (chỉ đọc, ~2 s) | `C:\Tools\ModCard\kiem_vga.py` |
| `dat_offset.py` | Đặt offset nhớ qua NVML (`1500 2000` = chốt, `0 0` = mặc định) | `C:\Tools\ModCard\dat_offset.py` |
| `tao_task_boot.ps1` | Tạo lại tác vụ SYSTEM `LTT_ModCard_NVML_KhoiDong` | `C:\Tools\ModCard\tao_task_boot.ps1` |
| `KET_QUA_22_09.md` | Số đo từng bậc, soak, đối chứng | — |
| `KE_HOACH_TEST_22_09.md` | Kế hoạch test và điều kiện dừng đã dùng | — |

Dựng lại khi máy B mất `C:\Tools\ModCard\` (chạy từ máy A):

```bash
ssh -i "C:\Users\Thang Tuong\.ssh\nexus_b" lengo@192.168.2.66 "mkdir C:\Tools\ModCard"
scp -i "C:\Users\Thang Tuong\.ssh\nexus_b" docs/MAY_B_VGA/*.py docs/MAY_B_VGA/*.ps1 docs/MAY_B_VGA/Setup_VGA.md lengo@192.168.2.66:C:/Tools/ModCard/
```

Rồi làm theo `Setup_VGA.md` mục 6 kịch bản A (tạo venv + `pip install nvidia-ml-py`, chạy `tao_task_boot.ps1`,
kiểm bằng `kiem_vga.py`). Đơn vị NVML = 2 × đơn vị Afterburner.

Dữ liệu thô của phiên thử nghiệm (không đưa vào kho): máy B `H:\LTT_MOD_CARD\`.

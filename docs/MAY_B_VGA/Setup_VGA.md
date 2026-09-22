# Setup_VGA — máy B (DESKTOP-MR9CFK0, 192.168.2.66)

Thiết lập ngày 22/09/2026 (phiên Claude, chủ dự án duyệt). Tệp này đủ để **một người hoặc một phiên Claude**
hiểu cấu hình VGA đang áp, kiểm nó còn đúng không, và khôi phục khi có sự cố.
Bản kết quả chi tiết (số đo từng bước) nằm trên máy A: `C:\Users\Thang Tuong\.claude\ltt\mod_card_may_b\KET_QUA.md`.

> Claude đọc tệp này: làm theo mục 5 (kiểm) rồi mục 6 (khôi phục). Máy B là **production** (LLM cho khách +
> cụm Proxmox lồng chứa VPS khách). ⛔ Không bật WSL2/Hyper-V (làm sập VPS), không OC xung nhân/điện áp,
> không flash VBIOS, không khởi động lại máy nếu chủ dự án chưa đồng ý.

---

## 1. Tóm tắt một dòng

Chỉ tăng xung **BỘ NHỚ**: **RTX 3090 +750 MHz**, **RTX 5060 Ti +1000 MHz**. Xung nhân, điện áp, power limit
(3090 370 W / 5060 Ti 180 W), quạt, VBIOS: **mặc định nhà sản xuất**. Áp bằng API NVML lúc khởi động (tác vụ SYSTEM),
không cần ai đăng nhập. Offset **không nằm trong VBIOS** ⇒ xoá tác vụ + khởi động lại = về mặc định hoàn toàn.

## 2. Phần cứng

| | GPU0 | GPU1 |
|---|---|---|
| Card | MSI RTX 3090 **Gaming X Trio** 24 GB (subsys 38841462, bus 2) | MSI RTX 5060 Ti **Ventus 2X OC Plus** 16 GB (subsys 53511462, bus 129) |
| Model AI | LTT-3.8 = Qwen3.8-27B (llama-server, qua llama-swap :8280) | LTT-3.5 = Qwen3.5-9B |
| Nhớ | GDDR6X, chạy CUDA ở **P2** | GDDR7, chạy CUDA ở **P1** |
| Xung nhớ khi tải — mặc định | 9501 MHz (nvidia-smi) | 13801 MHz |
| Xung nhớ khi tải — ĐANG ÁP | **10251 MHz** | **14801 MHz** |
| Power limit | 370 W (mặc định; max 380) | 180 W (mặc định = max) |

Máy: 2 × Xeon E5-2678 v3, bo HUANANZHI X99-T8D, PCIe 3.0 (hai card x8, ở hai socket CPU khác nhau),
192 GB RAM, Windows 11 Pro, driver NVIDIA **610.88**.

## 3. Cơ chế áp (đang dùng)

| Thành phần | Đường dẫn / tên |
|---|---|
| Tác vụ khởi động | Task Scheduler: **`LTT_ModCard_NVML_KhoiDong`** — chạy bằng SYSTEM, "At startup", trễ 60 s, thử lại 3 lần mỗi 1 phút |
| Lệnh của tác vụ | `C:\Tools\ModCard\venv\Scripts\python.exe C:\Tools\ModCard\dat_offset.py 1500 2000` |
| Script đặt offset | `C:\Tools\ModCard\dat_offset.py` (NVML `nvmlDeviceSetClockOffsets`, P0/P1/P2, chỉ BỘ NHỚ; kiểm tên card trước khi đặt; chặn trần 2000/3000) |
| Script kiểm (chỉ đọc) | `C:\Tools\ModCard\kiem_vga.py` |
| Script tạo lại tác vụ | `C:\Tools\ModCard\tao_task_boot.ps1` |
| Log mỗi lần áp | `C:\Tools\ModCard\dat_offset.log` (6 dòng "OK" mỗi lần) |
| venv riêng | `C:\Tools\ModCard\venv` (Python 3.12 hệ thống + gói `nvidia-ml-py` 13.610.43 của NVIDIA) — KHÔNG phải venv production `H:\LTT_LLM\venv` |

⚠ **ĐƠN VỊ NVML = 2 × đơn vị Afterburner.** NVML `1500` = Afterburner `+750` = +750 MHz trên nvidia-smi.
NVML `2000` = Afterburner `+1000`. Gõ nhầm 750/1000 vào dat_offset.py chỉ được nửa mức (an toàn, chậm hơn).

**MSI Afterburner** (vẫn cài, tự chạy khi đăng nhập) **KHÔNG còn dùng để OC**: mục `[Startup]` trong
`C:\Program Files (x86)\MSI Afterburner\Profiles\VEN_10DE*.cfg` để rỗng (như gốc). Các `[Profile1..5]` trong đó là
di tích thử nghiệm: Profile1 = mặc định, Profile3 = đúng mức chốt. ⛔ Đừng áp profile Afterburner khi tác vụ NVML
còn hoạt động (hai công cụ có thể chồng offset). Afterburner khởi động lại KHÔNG xoá offset NVML (đã thử).
Bản cfg gốc: `H:\LTT_MOD_CARD\afterburner_goc\` và `MSIAfterburner.cfg.truoc_claude`.

## 4. Số đo mốc (để biết "bình thường" là gì)

Đo qua llama-swap (cấu hình production nguyên vẹn), 1 luồng, greedy, prompt ~1K → 512 token ra.
Máy đã nóng (soak), hai card tải cùng lúc:

| | Mặc định | Đang áp | |
|---|---|---|---|
| LTT-3.8 decode (3090) | 68,4 tok/s | **69,6** | +1,8 % |
| LTT-3.5 decode (5060 Ti) | 72,9 tok/s | **76,2** | +4,5 % |
| Prefill 3.8 / 3.5 (12K token) | 1.186 / 2.152 | 1.189 / 2.164 | không đổi |
| 3090 VRAM junction max / hot spot max | 86 / 94 °C | 86 / 94,5 °C | |
| 5060 Ti hot spot max | 98,9 °C | 98,9 °C | do tản nhiệt card, có cả ở mặc định |

Kiểm chất lượng: output greedy phải **trùng hash** với mốc — 3.8 `d38871a80a678a85`, 3.5 `8859c154a4b89940`
(prompt cố định trong `H:\LTT_MOD_CARD\do_toc.py` phép `t1`). Soak 30 phút: 292 lượt, 0 lệch, 0 lỗi.
3090 khi chạy LLM **luôn chạm trần điện 370 W** — đó là lý do OC nhớ chỉ thêm ~2 %; hạ 300 W mất 3,3 %.

Ngưỡng an toàn đã dùng: 3090 VRAM junction < 96 °C; hot spot < 95 °C (5060 Ti vượt ở CẢ mặc định — vấn đề tản
nhiệt, xem mục 8); không có sự kiện nvlddmkm / Display 4101 / WHEA / Kernel-Power 41.

## 5. Kiểm nhanh (làm đầu tiên khi nghi có sự cố)

PowerShell trên máy B (hoặc từ máy A: `ssh -i "C:\Users\Thang Tuong\.ssh\nexus_b" lengo@192.168.2.66`):

```powershell
# 1) Cấu hình còn đúng không (chỉ đọc, 2 giây) — phải in "KET LUAN: DUNG CAU HINH CHOT"
C:\Tools\ModCard\venv\Scripts\python.exe C:\Tools\ModCard\kiem_vga.py

# 2) Xung nhớ thật (CHỈ có nghĩa khi model đang chạy; lúc nghỉ card ở P8 = 405 MHz)
nvidia-smi --query-gpu=index,pstate,clocks.mem,power.draw,temperature.gpu --format=csv
#    đúng: GPU0 P2 10251 MHz · GPU1 P1 14801 MHz

# 3) Lỗi GPU/phần cứng gần đây trong nhật ký Windows
Get-WinEvent -FilterHashtable @{LogName='System'; StartTime=(Get-Date).AddDays(-1)} -EA SilentlyContinue |
  ? { $_.ProviderName -match 'nvlddmkm|Display|WHEA|Kernel-Power|BugCheck' } |
  select TimeCreated, ProviderName, Id -First 20
```

Đo lại tốc độ + hash (máy B, ~2 phút, gọi model thật qua llama-swap):
`H:\LTT_LLM\venv\Scripts\python.exe H:\LTT_MOD_CARD\do_toc.py --nhan kiem --model qwen38-api --phep t1`
(đổi `qwen35-api` cho card 5060 Ti). So với mục 4.

## 6. Khôi phục — theo kịch bản

**A. Sau khởi động lại, kiem_vga báo offset = 0 (tác vụ không chạy)**
1. `Get-ScheduledTaskInfo LTT_ModCard_NVML_KhoiDong` (xem LastTaskResult) và `Get-Content C:\Tools\ModCard\dat_offset.log -Tail 10`.
2. Chạy tay: `Start-ScheduledTask LTT_ModCard_NVML_KhoiDong` → chờ 10 s → chạy lại kiem_vga.
3. Tác vụ mất: `powershell -ExecutionPolicy Bypass -File C:\Tools\ModCard\tao_task_boot.ps1` (tạo lại + chạy luôn).
4. venv hỏng: `C:\Users\lengo\AppData\Local\Programs\Python\Python312\python.exe -m venv C:\Tools\ModCard\venv`
   rồi `C:\Tools\ModCard\venv\Scripts\python.exe -m pip install nvidia-ml-py`.
5. Log báo "khong trong danh sach": tên card đổi (driver mới đổi chuỗi tên?) — sửa `MUON`/`TRAN` trong dat_offset.py.

**B. Nghi OC gây lỗi (TDR, llama-server chết, màn hình xanh, output lạ) ⇒ VỀ MẶC ĐỊNH NGAY**
```powershell
Disable-ScheduledTask LTT_ModCard_NVML_KhoiDong
C:\Tools\ModCard\venv\Scripts\python.exe C:\Tools\ModCard\dat_offset.py 0 0
C:\Tools\ModCard\venv\Scripts\python.exe C:\Tools\ModCard\kiem_vga.py    # offset phải = 0 (báo LECH là đúng lúc này)
```
Theo dõi 1–2 ngày. Lỗi vẫn còn ở mặc định ⇒ không phải do OC (nhiệt, nguồn, RAM ECC, driver). Hết lỗi ⇒ bật lại ở
mức thấp hơn: `dat_offset.py 1000 1000` (= +500/+500), rồi `Enable-ScheduledTask` sau khi sửa tham số trong tác vụ.

**C. Driver NVIDIA được cập nhật**
Chạy kiem_vga. Offset NVML không bị driver mới xoá vĩnh viễn (tác vụ đặt lại mỗi lần khởi động), nhưng driver mới có thể
đổi hành vi — đo lại mục 5 (tốc độ + hash). Hash lệch ⇒ kịch bản B.

**D. Card bị thay / thêm card / đổi khe**
`dat_offset.py` chỉ đặt cho đúng tên "NVIDIA GeForce RTX 3090" và "NVIDIA GeForce RTX 5060 Ti"; card khác bị bỏ qua.
Card MỚI cùng tên (thay bảo hành) ⇒ mức OC chưa được kiểm trên chip đó: về mặc định (kịch bản B) rồi test lại
từng bậc + soak như `KET_QUA.md` trước khi áp.

**E. Gỡ hoàn toàn mod**
```powershell
Unregister-ScheduledTask LTT_ModCard_NVML_KhoiDong -Confirm:$false
C:\Tools\ModCard\venv\Scripts\python.exe C:\Tools\ModCard\dat_offset.py 0 0
```
(hoặc xoá tác vụ rồi khởi động lại). Không có gì trong VBIOS/registry cần hoàn tác.

## 7. Những thứ KHÔNG làm, và vì sao

- **Không OC xung nhân / undervolt:** rủi ro lỗi tính toán; chưa được chủ dự án duyệt. Nếu muốn thử là phiên riêng.
- **Không hạ power limit 3090:** 300 W mất 3,3 % decode, 5,8 % prefill.
- **Không flash VBIOS:** VBIOS NVIDIA ký số, không nhúng được offset; cross-flash BIOS power cao chỉ thêm ~2 % mà
  thêm nhiệt và rủi ro "chết" card.
- **Không bật WSL2/Hyper-V trên máy B:** VMware mất VT-x lồng ⇒ cụm Proxmox chứa VPS khách không khởi động được
  (Broadcom KB 389469). ⇒ HyperQwen/vLLM không chạy trên máy B (đã đánh giá 22/09: không triển khai).
- **Không dùng Afterburner để OC** (xem mục 3).

## 8. Việc bảo trì phần cứng nên làm (không phải do mod)

- 5060 Ti: hot spot 98,9 °C khi tải kéo dài ở CẢ mặc định (nhân 77 °C, quạt ~100 %) ⇒ kiểm luồng gió thùng máy,
  thay keo tản nhiệt.
- 3090: hot spot 94 °C, lệch nhân 22 °C ⇒ thay keo khi bảo trì. VRAM junction 86 °C — ổn.

## 9. Công cụ và dữ liệu thử nghiệm (tham khảo)

- `H:\LTT_MOD_CARD\` — toàn bộ script và dữ liệu phiên 22/09: `do_toc.py` (đo tốc + hash), `soak.py`,
  `ket_qua\do_toc.jsonl`, `ket_qua\soak.jsonl`, `hwinfo\gpu.csv`, `evtx_truoc_mod\` (nhật ký sự kiện trước 18:08 22/09).
- HWiNFO 8.52 portable: `C:\Tools\HWiNFO` (đang TẮT). Đọc nhiệt VRAM từng chip: bật `SensorsSM=1` (đã có trong INI),
  mở HWiNFO trong phiên người dùng, đọc bằng `H:\LTT_MOD_CARD\doc_cam_bien.ps1 -Liet`. Bản miễn phí chỉ cho dùng phi
  thương mại.
- Mở GUI trong phiên lengo từ SSH: tác vụ `schtasks /create ... /ru DESKTOP-MR9CFK0\lengo /it` chạy một tệp .cmd có
  `start ""` (UAC tự nâng quyền).

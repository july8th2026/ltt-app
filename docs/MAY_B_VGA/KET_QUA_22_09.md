# Mod card máy B — kết quả (22/09/2026)

Kế hoạch: `KE_HOACH.md` cùng thư mục. Dữ liệu thô trên B: `H:\LTT_MOD_CARD\ket_qua\do_toc.jsonl`,
`soak.jsonl`, cảm biến `H:\LTT_MOD_CARD\hwinfo\gpu.csv` (HWiNFO shared memory, 2 s).

## Phần cứng đo được
- 3090 = MSI RTX 3090 **Gaming X Trio** (có nhiệt từng chip nhớ trước/sau). 5060 Ti = MSI **Ventus 2X OC Plus**.
- Khi chạy CUDA, 3090 ở **P2**: xung nhớ 9501 (không phải 9751). Offset Afterburner CÓ tác dụng trong P2.
- 3090 decode 1 luồng chạm **trần điện 370 W** gần như liên tục ⇒ nghẽn là điện năng, không phải băng thông nhớ.
- Hot spot khi tải ở mặc định: 3090 ~93 °C (nhân 71 °C, chênh 22 °C), 5060 Ti ~95 °C (nhân 74 °C, quạt 100 %).

## Phép đo
Qua llama-swap (cấu hình production nguyên vẹn), greedy. T1 = ngữ cảnh 1K → 512 token ra (5 lượt, hash output
phải trùng mốc). T2 = prefill 12,4K (3 lượt). T3 = ngữ cảnh 50K. Nhiễu lặp lại mốc < 1 %.

| Bước | 3.8 decode T1 | 3.8 prefill | 3090 junction max | Ghi chú |
|---|---|---|---|---|
| mốc | 67,4–67,9 | 1.181–1.186 | 76–80 | T3: prefill 1.003, decode 45,4 |
| PL 300 W | 65,2 (−3,3 %) | 1.113 (−5,8 %) | 78 | hot spot 93→88 · BỎ (mất tốc) |
| nhớ +250 | 68,2 | 1.191 | 78 | xung nhớ 1219 |
| nhớ +500 | 68,2 | 1.185 | 82 | 1250 |
| nhớ +750 | 68,8 (+1,7 %) | 1.187 | 82 | 1281 · **CHỌN** (lùi 1 bậc) |
| nhớ +1000 | 69,1 (+2,2 %) | 1.187 | 84 | 1313 |

| Bước | 3.5 decode T1 | 3.5 prefill | 5060 hot spot max | Ghi chú |
|---|---|---|---|---|
| mốc | 74,3–74,6 | 2.170 | 94,6 | T3: prefill 1.881, decode 60,0 |
| nhớ +500 | 76,2 (+2,4 %) | 2.177 | 94,2 | xung nhớ 1788 |
| nhớ +1000 | 78,0 (+4,8 %) | 2.179 | 96,2 | 1850 · chạm ngưỡng hot spot 95 ⇒ DỪNG tăng |

Mọi bước: hash T1 trùng mốc (chất lượng giữ nguyên từng byte), 0 sự kiện lỗi (nvlddmkm/WHEA/Kernel-Power).

## Soak (hai card tải cùng lúc)
- Mod (3090 +750 / 5060 Ti +1000), 30 phút: 292 lượt T1 **0 lệch hash**, 0 lỗi gọi, 0 sự kiện lỗi.
- Đối chứng MẶC ĐỊNH 12 phút ngay sau, so với 12 phút cuối của soak mod (máy đã nóng như nhau):

| | mặc định | mod | |
|---|---|---|---|
| 3.8 decode | 68,4 | **69,6** | +1,8 % |
| 3.5 decode | 72,9 | **76,2** | +4,5 % |
| prefill 3.8 / 3.5 | 1.186 / 2.152 | 1.189 / 2.164 | ~0 |
| 3090 junction max / hot spot max | 86 / 94,0 | 86 / 94,5 | |
| 5060 hot spot max | **98,9** | **98,9** | do tản nhiệt card, KHÔNG do OC |

## Đang áp (chốt) — cập nhật 22/09 tối: chuyển từ Afterburner sang NVML
- Offset xung NHỚ: 3090 **+750 MHz** (P2: 9501 → 10251), 5060 Ti **+1000 MHz** (P1: 13801 → 14801).
  Nhân, điện áp, power limit (370/180 W) mặc định. Không đụng VBIOS.
- Cơ chế: tác vụ **`LTT_ModCard_NVML_KhoiDong`** chạy bằng **SYSTEM lúc khởi động** (trễ 60 s, thử lại 3 lần) ⇒
  `C:\Tools\ModCard\venv\Scripts\python.exe C:\Tools\ModCard\dat_offset.py 1500 2000` (API NVML chính thức,
  gói `nvidia-ml-py` 13.610.43). **Không cần ai đăng nhập.** Log: `C:\Tools\ModCard\dat_offset.log`.
- ĐƠN VỊ NVML = 2 × đơn vị Afterburner (NVML 1500 = Afterburner +750 = +750 MHz trên nvidia-smi). Script kiểm tên
  card trước khi đặt (thứ tự GPU đổi ⇒ không đặt nhầm) và chặn trần 2000/3000.
- Afterburner: [Startup] trả về rỗng như gốc, tác vụ áp Profile3 khi đăng nhập ĐÃ XOÁ. Afterburner khởi động lại
  không xoá offset NVML (đã thử). NVML `GetClockOffsets` KHÔNG thấy offset do Afterburner đặt (đọc ra 0).
- Đã xác minh (chạy tác vụ SYSTEM bằng tay, chưa khởi động lại máy thật): xung 10251/14801 khi tải, hash T1 trùng
  mốc, 69,5 / 78,2 tok/s, 0 sự kiện lỗi.
- Kiểm nhanh sau khi khởi động lại: `Get-Content C:\Tools\ModCard\dat_offset.log -Tail 6` (6 dòng OK mới) và
  khi đang chạy model: `nvidia-smi --query-gpu=index,pstate,clocks.mem --format=csv` ⇒ 10251 / 14801.
- Lùi về mặc định: `Unregister-ScheduledTask LTT_ModCard_NVML_KhoiDong` + chạy `dat_offset.py 0 0`
  (hoặc xoá tác vụ rồi khởi động lại máy — offset không nằm trong VBIOS, mất khi khởi động lại).

## Còn tồn (phần cứng, ngoài OC)
- 5060 Ti hot spot 98,9 °C ở mặc định khi tải kéo dài (nhân 77 °C, quạt ~95–100 %): kiểm luồng gió thùng máy /
  thay keo tản nhiệt. 3090 hot spot 94 °C (chênh nhân 22 °C) — cân nhắc thay keo khi bảo trì.
- Hạ power limit 3090 mất tốc (300 W: −3,3 % decode, −5,8 % prefill) ⇒ không áp.
- Muốn thêm tốc 3090: chỉ còn đường chỉnh đường cong điện áp/xung nhân (undervolt) — ngoài phạm vi đã chốt,
  cần chủ dự án duyệt riêng.
- HWiNFO 8.52 portable ở `C:\Tools\HWiNFO` (bản miễn phí: giấy phép cho dùng phi thương mại) — đã tắt.

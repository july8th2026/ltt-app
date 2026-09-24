# B0 — kiểm kê 4 video thật

Đo bằng chính đường sản phẩm: `ffprobe` (cơ bản) · `apps/auto_scan_video/tach_tieng.py`
+ `demucs_runner.py` + `cao_do.py` (tách giọng, F0, âm lượng) · `apps/auto_scan_video/
nguon_loi.py:dinh_tuyen` (RapidOCR + định tuyến thật, không suy luận) · `apps/
auto_scan_video/canh.py` (PySceneDetect `ContentDetector`, ngưỡng 35). Bốn tệp ở
`C:\Users\Thang Tuong\Desktop\TEST VIDEO`. Lệnh demucs/OCR/cắt cảnh đều đi qua
`chay_nang.py --phien asvf-b0`, mỗi lượt nhả khoá ngay khi tính xong.

| phim | dài | có tiếng nói | F0 trung vị | % khung có chữ | % chữ Hán | `dinh_tuyen` chọn | số cảnh | phụ đề nhúng |
|---|---|---|---|---|---|---|---|---|
| món ăn (廉价的牛肠…) | 4:25 (265,0s) | **CÓ** | 160,0 Hz | 95,0% | 100,0% | `ocr` | 125 | không |
| cắm trại (暴雨天野外露营…) | 3:10 (190,0s) | **CÓ** | 166,7 Hz | 97,5% | 100,0% | `ocr` | 100 | không |
| PUBG (深度解析丨跳伞慢了…) | 1:47 (106,8s) | **CÓ** | 188,2 Hz | 67,5% | 98,8% | `ocr` | 18 | không |
| súng hơi (真人气枪游戏…) | 4:35 (275,0s) | **không chắc** | 170,2 Hz | 65,0% | 99,5% | `ocr` | 127 | không |

Cơ bản chung cả bốn: video H.264, âm AAC 2 kênh 44,1 kHz ~128 kbps (riêng cắm trại
~55 kbps), fps 30 (súng hơi 29,97). Không tệp nào có luồng phụ đề (`s`) trong
container — `nguon_loi.dinh_tuyen` tự xác nhận qua `ly_do: ["khong_co_phu_de_nhung"]`
ở cả bốn, không phải suy luận từ tên tệp.

## Chi tiết "có tiếng nói không" — đo trên stem `vocals` (demucs `htdemucs`, CPU)

LUFS đo bằng `tach_tieng.do_am_luong` (loudnorm phân tích) trên `vocals.wav` so với
bản nền trộn `tach_tieng.tron_nen(drums+bass+other)`:

| phim | LUFS vocals | LUFS nền (no_vocals) | chênh lệch | F0 |
|---|---|---|---|---|
| món ăn | −7,93 | −13,91 | **+5,98 dB** (vocals to hơn) | 160,0 Hz |
| cắm trại | −10,72 | −13,64 | **+2,92 dB** | 166,7 Hz |
| PUBG | −12,39 | −16,15 | **+3,76 dB** | 188,2 Hz |
| súng hơi | −17,29 | −14,39 | **−2,90 dB** (nền to hơn) | 170,2 Hz |

- **Món ăn, cắm trại, PUBG: CÓ tiếng nói người**, độ tin cậy cao — cả hai bằng
  chứng độc lập đồng thuận: F0 khác 0 (có khung giọng vượt cửa năng lượng, đủ
  ≥50 khung) **và** stem `vocals` to hơn nền rõ rệt (voice-over kiểu Douyin đè lên
  nhạc/nền). PUBG khớp tiêu đề "深度解析" (giải thích chi tiết) — dạng có bình luận.
- **Súng hơi: không chắc.** F0 khác 0 (170,2 Hz) — có khung nào đó được nhận là
  giọng — nhưng `vocals` **nhẹ hơn** nền 2,9 dB, ngược hướng với ba phim kia. Đây
  đúng là "lỗi quang tâm" mà `cao_do.py` cảnh báo: một âm tuần hoàn không phải
  tiếng nói (tiếng súng hơi, nhạc nền game) cũng có thể lọt qua cửa năng lượng và
  cho một trung vị F0 hợp lệ. ⛔ Không đủ căn cứ để chốt CÓ hay KHÔNG — cần nghe
  trực tiếp `sung_hoi_stems/vocals.wav` (đã lưu ở scratchpad phiên này) mới kết
  luận được.

## Chi tiết "có hardsub không" — `nguon_loi.dinh_tuyen` (RapidOCR PP-OCRv6 small)

Cả bốn phim đều **có hardsub chữ Hán** và `dinh_tuyen` (chế độ `auto`) đều chọn
`ocr` — không phim nào rơi vào `asr`:

| phim | dải chữ dò được (y0–y1) | % khung có băng chữ | % chữ Hán | số dòng OCR |
|---|---|---|---|---|
| món ăn | 495–576 | 95,0% | 100,0% | 102 |
| cắm trại | 463–576 | 97,5% | 100,0% | 107 |
| PUBG | 413–496 | 67,5% | 98,8% | 95 |
| súng hơi | 477–576 | 65,0% | 99,5% | 119 |

Ngưỡng nhận OCR của `nguon_loi` là `TI_LE_HAN_TOI_THIEU = 0,8` (80%). Cả bốn phim
đều **vượt xa** ngưỡng (98,8%–100%) — quyết định `ocr` không nằm sát biên, rất chắc.

## ⚠️ Số cảnh — dữ liệu cho N-07, không kết luận

`canh.phan_tich` (chính module sản phẩm, không phải bộ đếm tự viết) cho:

| phim | số cảnh (đã gộp) | mốc thô trước gộp |
|---|---|---|
| món ăn | 125 | 167 |
| cắm trại | 100 | 107 |
| PUBG | 18 | 22 |
| súng hơi | 127 | 161 |

Bốn con số này đều **xa** `so_canh=1` mà N-07 ghi lượt A/B từng cho ra trên video
thật — gọi trực tiếp `canh.py` không tái hiện được lỗi `so_canh=1`. Đây là dữ liệu
cấp cho N-07 (khả năng lỗi nằm ở đường gọi trong job, không phải bản thân bộ tách
cảnh); ⛔ không tự kết luận nguyên nhân N-07 ở đây.

## Phim nào dùng để bench bước nào

- **Bench nghe chép (ASR):** không phim nào phù hợp làm bench ASR "sạch" —
  cả bốn đều bị `dinh_tuyen` định tuyến sang `ocr` (không đi nhánh ASR trong vận
  hành thật). Muốn bench riêng nhánh ASR phải ép `che_do=asr` thủ công trên một
  trong ba phim CÓ tiếng nói (món ăn/cắm trại/PUBG), hoặc xin thêm một mẫu không
  có hardsub — **cần báo chủ dự án xin thêm mẫu** cho bench ASR-thuần.
- **Bench OCR:** cả bốn đều có hardsub Hán rõ (≥98,8% chữ Hán), dùng được hết.
  Món ăn và cắm trại có tỉ lệ khung phủ chữ cao nhất (95–97,5%) — ưu tiên hai
  phim này nếu chỉ chọn một.
- **Bench tự khớp giọng (N-06, đòi nguồn có tiếng nói):** dùng món ăn, cắm trại,
  hoặc PUBG (ba phim CÓ tiếng nói, độ tin cậy cao). ⛔ Không dùng súng hơi — F0
  của nó không chắc là giọng người.
- **Bench cắt cảnh:** PUBG ít cảnh nhất (18) phù hợp kiểm nhanh; món ăn/cắm
  trại/súng hơi nhiều cảnh (100–127) phù hợp kiểm tải và đối chiếu N-07.

## Chỗ không chắc, ghi lại để không quên

- Kết luận "súng hơi có tiếng nói" — **không chắc**, xem chi tiết ở trên.
- F0 trung vị của cả bốn phim rơi gần/trong vùng xám giới tính (165±15 Hz của
  `cao_do.NGUONG_GIOI_HZ`) — `gioi_tu_f0` sẽ trả `""` (không khai giới) cho món
  ăn (160,0, trong xám 150–180) và súng hơi (170,2, trong xám); cắm trại (166,7)
  cũng trong xám. Chỉ PUBG (188,2) ra ngoài xám, khai "nữ". Đây không phải lỗi đo,
  là đặc tính dữ liệu — ghi lại để bước sau (nếu dùng bốn phim này cho AUTO_MATCH)
  không ngạc nhiên khi thấy giới tính rỗng.
- Số cảnh đo được KHÔNG giải thích được vì sao lượt A/B từng ra `so_canh=1`
  trên video thật — chỉ là dữ liệu, chưa phải câu trả lời cho N-07.

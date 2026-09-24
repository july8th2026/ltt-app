# L-KỸ THUẬT — bộ đo kỹ thuật/thị giác tất định của Auto Scan Video

> Làn `ky-thuat` của phiên ASV final (22–23/09/2026). Tệp này là **bảng đo**, không
> phải quy trình. Luật vận hành ở `docs/00_LTT_OPERATING_CONTRACT.md`; cổng nghiên
> cứu license ở `docs/auto_scan_video_final/OPEN_SOURCE_METRIC_AUDIT.md`.
>
> Bốn video nghiệm thu thật (Douyin, tiếng Trung, 576p, 107–275 s, chỉ đọc):
> v1 烤牛肠 265 s · v2 暴雨露营 190 s · v3 跳伞 107 s · v4 气枪 275 s.
> Mọi phép đo dưới đây chạy trên **máy A, 2 luồng** (`-threads 2`,
> `cv2.setNumThreads(2)`) vì máy đang phục vụ production — số giây là CHẶN TRÊN
> của chi phí thật khi chạy với nhiều lõi hơn.

## 0. Đổi gì (mã)

| Trước | Sau | Tệp |
|---|---|---|
| T13 = YAVG trung bình 12 khung < 2/255 (tự đặt) | T13 = `blackdetect` + `freezedetect` của ffmpeg, **so với nguồn** | `apps/auto_scan_video/qc.py` |
| (không có) | **T17** — giải mã cả tệp, không một dòng `[error]` | `qc.py`, `giai_doan_qc.py` |
| (không có) | **T18** — VMAF của lần mã hoá lại (chỉ preset cắt) | `qc.py`, `giai_doan_qc.py` |
| Cắt cảnh = ffmpeg `select=gt(scene,0.4)`, ngưỡng "CHƯA ĐO" | PySceneDetect `ContentDetector(threshold=35)` | `apps/auto_scan_video/canh.py` |
| `tools/do_watermark.py` (heuristic vùng tĩnh, không ai gọi) | **đã xoá** cùng `test_470` và `PHA13_NHAN_DIEN_WATERMARK.md` | — |
| `PHIEN_BAN_QC = 3` · cache cảnh khoá bằng `NGUONG_DOI_CANH` | `PHIEN_BAN_QC = 4` · `canh.PHIEN_BAN_CANH` (bộ tách + tham số) | `qc.py`, `thi_hanh.py` |

⛔ Không có `old_score`/`new_score`: mã cũ bị xoá hẳn (`test_2010`, `test_2013`
chốt sự vắng mặt của `signalstats`/`DO_SANG_TOI_THIEU`/`select='gt(scene`).

## 1. T13 — khung đen / hình đóng băng, và T17 — giải mã

**Tham số = mặc định trong tài liệu ffmpeg** (`ffmpeg-filters`, mục *blackdetect*,
*freezedetect*), không chỉnh: `blackdetect=d=2.0:pic_th=0.98:pix_th=0.10` +
`freezedetect=n=-60dB:d=2`. Hai bộ lọc chạy trong **một** lượt giải mã, cùng lượt
đó trả lời T17 (`-loglevel level+info` ⇒ đếm dòng `[error]`/`[fatal]`).

**Quy tắc HỎNG: so với NGUỒN, không so với một tỉ lệ tuyệt đối.**
Bản ra là tập con thời gian của nguồn ở cả hai preset, nên render đúng thì số giây
đen/đóng băng của bản ra không vượt của nguồn. HỎNG khi phần vượt > 0,5 s
(`DEN_DONG_DU_S`) — mọi khoảng ffmpeg báo ra đều dài ≥ 2 s (`d`), nên **một khoảng
MỚI bất kỳ đều làm hỏng**, còn 0,5 s chỉ hấp thụ rung mốc ở biên.

Vì sao không dùng ngưỡng tuyệt đối: một nguồn hợp lệ có thể đóng băng cả video
(podcast một ảnh tĩnh, slide) hoặc mở đầu bằng màn đen — một ngưỡng "≥ X % đen/
đóng băng thì hỏng" sẽ đánh hỏng chính những lần chạy đó.

| Video | nguồn đen / đóng băng | bản mã hoá lại crf23 đen / đóng băng | giây đo (nguồn / bản ra) | dòng lỗi giải mã |
|---|---|---|---|---|
| v1 (265 s) | 0,0 / 0,0 | 0,0 / 0,0 | 5,6 / 5,2 | 0 |
| v2 (190 s) | 0,0 / 0,0 | 0,0 / 0,0 | 2,8 / 2,1 | 0 |
| v3 (107 s) | 0,0 / 0,0 | 0,0 / 0,0 | 1,7 / 1,5 | 0 |
| v4 (275 s) | 0,0 / 0,0 | 0,0 / 0,0 | 6,4 / 6,1 | 0 |

⇒ **Lần mã hoá lại không tự sinh ra khoảng đen/đóng băng nào**, nên phần vượt của
một lần chạy lành mạnh là 0,0 s — ngưỡng 0,5 s không nằm sát dữ liệu thật.

Chiều dương (bộ đo NỔ được), `test_2010` trên clip lavfi có chân lý nền:
3 s hình + 4 s đen ⇒ `den_s` 3,5–4,5 s · `tpad=stop_mode=clone` 4 s ⇒ `dong_s`
≥ 3,5 s · tệp bị cắt mất một khúc giữa ⇒ T17 HỎNG (T1/T2 vẫn xanh vì ffprobe chỉ
đọc đầu container).

Chi phí: một lượt giải mã cả tệp ≈ **2–6 s cho 107–275 s video** (2 luồng), và ở
preset giữ hình khi băm T3 khớp thì **bỏ hẳn** lượt đo nguồn (luồng hình ra chính
là luồng hình nguồn).

## 2. T18 — VMAF cho preset `smart_localize` (mã hoá lại)

### Thiết kế: tham chiếu là CHÍNH chuỗi lọc render

Bản ra khác nguồn **có chủ đích** (cắt, che, logo, chữ, phụ đề) ⇒ VMAF
nguồn-vs-ra là một phép đo sai câu hỏi. QC dựng lại **đúng** chuỗi lọc của
`ket_xuat.dung_lenh` (`qc.loc_tham_chieu`, `test_2012` chốt hai bên bằng nhau với
cả bốn biến đổi điểm ảnh) rồi so trong **một** lệnh ffmpeg:

```
[0:v] <chuỗi lọc render> [ra] -> setpts, scale 1080 -> [ref]
[1:v] (bản đã mã hoá)         -> setpts, scale 1080 -> [dist]
[dist][ref] libvmaf=model=version=vmaf_v0.6.1:n_subsample=5:shortest=1:ts_sync_mode=nearest
```

Không ghi tệp tham chiếu ra đĩa (một bản FFV1 1080p 2 giờ là hàng chục GB).
Thứ tự đầu vào giữ nguyên hợp đồng của render (`0` nguồn, `2..` logo) nên chuỗi
lọc dùng lại nguyên văn; `1` là bản ra thay cho bản phối âm (chuỗi lọc hình không
đọc đầu vào 1).

**Chiều âm của thiết kế** (bằng chứng phép đo đúng chứ không phải trùng hợp): mã
hoá tham chiếu bằng **FFV1 không mất mát** rồi chấm bằng đúng đường trên cho
**98,2 – 100,0** điểm. Nếu ghép khung lệch một nhịp, con số này sẽ sụp.

### Mô hình và độ phân giải (theo tài liệu, không tự nghĩ)

`Netflix/vmaf → resource/doc/faq.md`: `vmaf_v0.6.1` dự đoán chất lượng **video
1080p xem ở 3H**; tính ở độ phân giải gốc thấp hơn tương đương xem xa hơn (576p ⇒
~5,6H) và **giấu lỗi**, FAQ khuyên co giãn cả hai phía lên 1080. Ta co giãn vừa
khung 1920×1080 (giữ tỉ lệ, bicubic) — con số đo được cho thấy chính xác hiệu ứng
FAQ mô tả: cùng một tệp, **gốc 576p cho 92,0–95,5 còn 1080p cho 86,3–90,1**.
Cạnh ngắn ≥ 2160 ⇒ `vmaf_4k_v0.6.1` ở độ phân giải gốc. **Không** bật
`phone_model`: sản phẩm chưa khai mục tiêu điện thoại, mô hình TV là phía nghiêm hơn.

### Số đo (4 video thật, chuỗi lọc cắt 3 khoảng + phụ đề `.ass` thật)

| Bản mã hoá | v1 | v2 | v3 | v4 | ý nghĩa |
|---|---|---|---|---|---|
| **libx264 veryfast crf23** (đường sản xuất) | **87,05** | **86,25** | **88,63** | **90,08** | phải ĐẠT |
| crf30 | 62,58 | 68,88 | 68,24 | 67,66 | hỏng nhẹ, phải TRƯỢT |
| crf36 | 36,67 | 47,78 | 45,50 | 43,13 | hỏng nặng |
| crf45 | 11,67 | 17,60 | 15,24 | 16,38 | hỏng nặng |
| FFV1 (không mất mát) | 99,96 | 98,22 | 99,62 | 99,82 | chiều âm |
| crf23 ở **độ phân giải gốc** | 94,38 | 91,98 | 94,59 | 95,47 | (vì sao co giãn lên 1080) |

**Ngưỡng `VMAF_TOI_THIEU = 75,0` trên điểm TRUNG BÌNH.** Nó nằm giữa hai đám mây
đã đo: cách bản sản xuất tệ nhất (86,25) **11,3 điểm** về phía dưới và cách bản
hỏng tốt nhất (68,88) **6,1 điểm** về phía trên. Không chốt trên `nho_nhat`: khung
tệ nhất của một bản crf23 bình thường xuống tới **70,2**, chốt ở đó sẽ đánh hỏng
lần chạy lành mạnh — báo cáo vẫn GHI `nho_nhat` và `p5` để người đọc thấy phần
đuôi.

### Chi phí, và vì sao `n_subsample = 5`

| Video (thời lượng ra) | sub1 | sub5 | lệch điểm trung bình |
|---|---|---|---|
| v1 (210 s) | 318,9 s | **97,2 s** | 87,05 → 87,15 (+0,10) |
| v2 (150 s) | 212,6 s | **66,6 s** | 86,25 → 86,20 (−0,05) |
| v3 (84 s) | 96,1 s | **30,4 s** | 88,63 → 88,62 (−0,01) |
| v4 (218 s) | 318,8 s | **99,9 s** | 90,08 → 90,13 (+0,05) |

⇒ rẻ hơn ~3,2 lần, lệch ≤ 0,10 điểm (≪ khoảng cách 11 điểm tới ngưỡng). Chi phí
thật ≈ **0,45× thời lượng bản ra** trên 2 luồng (cộng lượt giải mã T13/T17).

⛔ Preset `localize_preserve_picture` ⇒ T18 `khong_ap_dung` **có lý do**: luồng
hình được `-c:v copy`, T3 (băm MD5 luồng hình) và T14 đã chứng minh giống nguồn
từng bit — VMAF không có gì để đo. Không đo được (thiếu libvmaf, ffmpeg lỗi) ⇒
`khong_ap_dung` kèm `khong_kha_dung`, **không** lùi về một ước lượng tự chế.

## 3. Cắt cảnh — benchmark thay cho một ngưỡng chưa đo

### Bộ dữ liệu

* **Tổng hợp (9 clip, ffmpeg lavfi, mốc cắt BIẾT TRƯỚC, mã hoá crf23):** cắt cứng
  giữa các cảnh khác hẳn · cắt cứng giữa hai cảnh **giống nhau** · hoà hình
  (xfade 1 s + 1,5 s) · **quay lia/zoom không cắt** · cảnh động nhanh (life/cellauto) ·
  **talking head** (nền tĩnh, chuyển động nhỏ) · chuyển tối (fade ra đen → fade vào) ·
  **chớp trắng 3 khung** (bẫy báo động giả) · cắt giữa hai cảnh tối.
  17 sự kiện chân lý nền; hoà hình/fade tính là **khoảng** `[bắt, kết]`.
* **Thật:** v2 gắn nhãn tay **toàn bộ** (116 ứng viên → 105 cắt), v1 gắn nhãn tay
  60 ứng viên đầu (0,5–66,6 s → 42 cắt). Ứng viên = **hợp** của mọi cấu hình ở
  ngưỡng thấp (select 0,2 · scdet 5 · content 20 · adaptive 2,0 · hash 0,3), gom
  cụm 0,3 s; mỗi ứng viên xem hai khung t±0,06 s rồi gắn nhãn cắt/không.
* Khớp ở **±0,2 s**, ghép một-một tham lam.

⚠️ **Giới hạn phải nói ra:** chân lý nền trên video thật dựng từ ứng viên của các
bộ tách, nên một cắt mà **mọi** bộ đều bỏ sót sẽ không có trong chân lý ⇒ recall
trên video thật là chặn trên. Bộ tổng hợp không có giới hạn này (mốc do ta cấy) và
chính nó tách được các bộ tách. v3/v4 (cảnh game) **bị loại khỏi chân lý nền**:
camera trong game cắt liên tục, mắt người không phân biệt được "cắt dựng" với
"chuyển camera" ở ±0,2 s — gắn nhãn ở đó là bịa số.

### Kết quả

Tổng hợp (17 sự kiện × 9 clip):

| bộ tách | TP | FP | FN | P | R | F1 |
|---|---|---|---|---|---|---|
| **psd ContentDetector 35** | 16 | 4 | 1 | 0,80 | 0,94 | **0,86** |
| psd AdaptiveDetector 3,0 (mặc định) | 16 | 4 | 1 | 0,80 | 0,94 | 0,86 |
| psd ContentDetector 27 (mặc định) | 15 | 10 | 2 | 0,60 | 0,88 | 0,71 |
| ffmpeg `scdet` 10 (mặc định) | 11 | 8 | 6 | 0,58 | 0,65 | 0,61 |
| **ffmpeg `select=gt(scene,0.4)` (bản cũ)** | 8 | 7 | 9 | 0,53 | 0,47 | **0,50** |
| psd HashDetector 0,395 | 15 | 44 | 2 | 0,25 | 0,88 | 0,39 |

Video thật (147 cắt gắn nhãn tay trên v1+v2):

| bộ tách | TP | FP | FN | P | R | F1 | giây/837 s video |
|---|---|---|---|---|---|---|---|
| **psd ContentDetector 35** | 144 | 10 | 3 | 0,94 | 0,98 | **0,96** | 16,4 |
| psd AdaptiveDetector 3,0 | 143 | 15 | 4 | 0,91 | 0,97 | 0,94 | 16,1 |
| psd ContentDetector 27 | 144 | 15 | 3 | 0,91 | 0,98 | 0,94 | 16,5 |
| ffmpeg `select` 0,3 | 142 | 11 | 5 | 0,93 | 0,97 | 0,95 | 11,3 |
| **ffmpeg `select` 0,4 (bản cũ)** | 128 | 6 | 19 | 0,96 | 0,87 | **0,91** | 11,3 |
| ffmpeg `select` 0,5 | 83 | 1 | 64 | 0,99 | 0,56 | 0,72 | 11,3 |

**Quyết định: thay bằng `ContentDetector(threshold=35, min_scene_len=15)`.** Gộp
hai bộ: TP 160 / FP 14 / FN 4 ⇒ P 0,92 · R 0,98 · **F1 0,95**, đứng đầu cả hai bảng
(Adaptive 0,93; bản cũ 0,73). Ngưỡng 35 là **số đo**, không phải mặc định thư
viện: so với 27 nó bỏ 11 báo động giả (quay lia, cảnh động nhanh) mà không mất
thêm cắt nào.

Vì sao bản cũ thua ở chỗ quan trọng nhất: `select=gt(scene,0.4)` **bỏ sót cả 2/2
cắt giữa hai cảnh talking-head** và cắt giữa hai cảnh tối trong bộ tổng hợp — đúng
hình dạng cảnh mà một video lồng tiếng hay gặp. Không giữ lai ghép: không cấu hình
lai nào cho F1 cao hơn bộ đơn tốt nhất trên dữ liệu này, và một bộ lai là hai
ngưỡng phải bảo trì.

Chi phí + trí nhớ: **52× thời gian thực trên 2 luồng** (837 s video / 16,4 s), đọc
từng khung qua OpenCV và tự thu nhỏ (`auto_downscale`) ⇒ bộ nhớ không đổi theo độ
dài video. Hai bẫy cũ vẫn được canh: `phan_tich` gọi bộ tách **đúng một lần** cho
cả video (`test_436`), và huỷ/quá hạn dừng được giữa chừng (`SceneManager.stop()`
từ một luồng canh — `test_2013`).

⚠️ Bàn giao cho điều phối: `canh.PHIEN_BAN_CANH` đã vào vân tay giai đoạn
`EDIT_PLAN` nên cache cảnh trượt đúng cách; nhưng `hieu_canh.van_tay_canh` khoá
theo `ma_canh` + ngữ cảnh lời thoại chứ **không** theo mốc `[bắt, kết]` — một
`canh_0003` sinh bởi bộ tách mới có thể trùng vân tay với `canh_0003` cũ ở một
khoảng thời gian khác. Tệp đó thuộc làn khác; đã báo, chưa sửa ở đây.

## 4. Xoá `tools/do_watermark.py`

Heuristic lưới độ lệch tự chế, **không app nào gọi**, pha 13 đã để tắt vì nó dò
*vùng tĩnh* chứ không dò *watermark*. Đã xoá cùng `tests/test_470_asv_v6_watermark.py`
(22 bài chỉ bảo vệ nó) và `docs/auto_scan_video_v6/PHA13_NHAN_DIEN_WATERMARK.md`;
hai bảng V6 (`MA_TRAN_TINH_NANG_V6.md`, `TRANG_THAI_V6.md`) trỏ sang lịch sử git.
Không còn tham chiếu nào (`voice_sidecar/do_chat_luong.do_watermark` là watermark
**âm thanh**, khác hệ, không đụng).

## 5. Phép kiểm

| Tệp | Bài | Hỏi gì |
|---|---|---|
| `tests/test_2010_asv_qc_den_dong_giai_ma.py` | 10 | T13/T17: đọc stderr (hàm thuần) + ffmpeg thật trên clip có chân lý nền; vắng mặt mã YAVG cũ |
| `tests/test_2011_asv_qc_cho_noi_ky_thuat.py` | 2 | CHỖ NỐI: chạy hết chuỗi, bản ra preset cắt phải có **số VMAF thật** (không `khong_kha_dung`) |
| `tests/test_2012_asv_qc_vmaf_hop_dong_loc.py` | 14 | tham chiếu VMAF **trùng khớp** chuỗi lọc render với cả 4 biến đổi; thứ tự đầu vào; chọn mô hình; ngưỡng nổ hai chiều |
| `tests/test_2013_asv_tach_canh_pyscenedetect.py` | 7 | bộ tách thật: talking head + cắt; quay lia không báo cắt; tất định; huỷ; vắng mặt đường `select` cũ |

Đã cập nhật: `test_420` (tập hợp T1–T18, `PHIEN_BAN_QC ≥ 4`), `test_436` (bỏ phần
đọc stderr ffmpeg, thay bằng bộ tách giả), `test_438`/`test_444`/`test_473`.

## 6. Việc còn lại

* GPU: bản ra thật có thể dùng `h264_nvenc cq 28` khi job được cấp card — **chưa
  đo VMAF cho nhánh nvenc** (máy A đang phục vụ production, GPU không rảnh). Ngưỡng
  75 dựng trên `libx264 crf23`; nhánh nvenc cần một bảng đo riêng trước khi tin.
* Chưa đo trên video **dọc** và **≥ 1080p** thật (bốn video nghiệm thu đều 576p
  ngang); đường `vmaf_4k` mới chỉ được chốt ở mức chọn mô hình, chưa có số.
* Chân lý nền cắt cảnh cho video **cảnh game** (v3/v4) vẫn để trống — cần quy ước
  gắn nhãn khác (xem §3).

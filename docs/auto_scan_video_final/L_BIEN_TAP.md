# Làn `bien-tap` — cắt khung · phóng to · tỉ lệ khung · tốc độ (asv-final, 22/09/2026)

Nhánh `phien/asv-final-bien-tap`. Quyết định sản phẩm: `ADR_BIEN_TAP.md`.
Test mới: `test_2060` (hồ sơ + hình học) · `test_2061` (bản dựng + chuỗi lọc + QC) ·
`test_2062` (engine thật, đo trên tệp ra) · `test_2063` (HTTP + khối giao diện).

## 1. Đường đi của một điều khiển

```
studio (asv/bien_tap.js) ── ô ẩn `bien_tap` (JSON, rỗng khi mặc định)
  → routes.tao → bien_tap.tu_form(preset=…)      tầng 1: từ chối ở cửa, trước credit
  → cai_dat["bien_tap"]  (KHOA_THUA — vắng mặt khi không dùng)
  → COMPOSE: ban_dung.dung(bien_tap=…) → hinh.bien_tap + hinh.khung_ra,
             ra.thoi_luong_giay = tổng / toc_do; ban_dung.kiem TÍNH LẠI khung_ra
  → RENDER: che_do_render.loc_cat_noi → MỘT -filter_complex, MỘT -c:v
             ket_xuat.kiem_tep_ra đo lại kích thước + thời lượng tệp ra
  → QC: T2 mong đợi = bản đồ / toc_do; T15 mốc phụ đề / toc_do (PHIEN_BAN_QC 4)
```

Có sẵn trước làn (không đổi): trim `cat_dau_cuoi`, `logo`, `lop_phu`, `vung_che`.

## 2. Thứ tự chặng trong chuỗi lọc (và vì sao)

```
trim/concat → vùng che → KHUNG (crop · scale · crop tỉ lệ | split+nền mờ) → logo → chữ → ass → setpts (tốc độ)
[1:a] atempo  ─ cùng filter_complex
```

- Vùng che **trước** khung: toạ độ nguồn, bám nội dung. L3 của `vung_che` (loại,
  không kẹp) đúng theo cấu trúc — đo: vùng ngoài cửa sổ cắt ⇒ PSNR `inf` so với
  bản không vùng; vùng trong cửa sổ ⇒ khác (đối chứng).
- Logo/chữ/phụ đề **sau** khung: toạ độ bản ra. Logo px, viền chữ, `PlayRes` của
  `.ass` lấy `ban_dung.khung_ra` (đã sửa `giai_doan_ket_xuat`).
- Tốc độ **cuối cùng**: `.ass`, lời lồng, nền đều trên trục biên tập; `setpts` và
  `atempo` nén cùng một hệ số. Nguồn → bản ra = `BanDoThoiGian.ra(t) / toc_do`
  (`bien_tap.moc_ban_ra`, một chỗ).

## 3. Số đo (engine thật, `test_2062`)

Khung — FFV1 không mất mát, so với phép biến đổi độc lập trên nguồn 640×360:

| điều khiển | khung ra | trùng phép độc lập | khác nguồn |
|---|---|---|---|
| 9:16 cắt quanh tâm | 202×360 | PSNR inf | (khác cỡ) |
| 1:1 tâm trái | 360×360 | PSNR inf | (khác cỡ) |
| cắt khung 25–75% | 320×360 | PSNR inf | (khác cỡ) |
| phóng 2× | 640×360 | PSNR inf | PSNR < 40 dB |
| 9:16 nền mờ | 360×640 | hình giữa = nguồn thu nhỏ, PSNR inf | dải trên YAVG > 20 (không viền đen) |

Tốc độ — `dung_lenh` thật (libx264 + AAC), chớp sáng ở hình và tiếng bíp ở bản phối
cùng tại 4,0 s trục biên tập:

| toc_do | mong đợi | hình | tiếng | lệch A/V |
|---|---|---|---|---|
| 1,0 | 4,000 | 4,000 | 4,000 | 0 |
| 1,1 | 3,636 | 3,64 | 3,618 | 22 ms |
| 1,25 | 3,200 | 3,20 | 3,184 | 16 ms |
| 1,5 | 2,667 | 2,68 | 2,656 | 24 ms |

Tiếng sớm ~16 ms là cửa sổ WSOLA của `atempo` (bản 1,0 lệch 0) — dưới một khung,
dưới ngưỡng phát hiện lệch tiếng/hình. Trên tệp 1,25×: T1/T2/T7/T11/T15/T16 ĐẠT
(`qc.kiem` trên ffprobe của tệp ra).

🔴 **Bắt được khi đo, không phải khi viết:** mặc định mp4 giữ CFR 25 của đường vào và
BỎ khung sau `setpts` — hình trễ tới +40 ms (3,24 thay vì 3,20). Sửa: `-fps_mode
passthrough` khi có tốc độ (VFR 31,25 fps ở 1,25×). `test_2061` chốt cờ này.

## 4. Kiểm tra phía máy chủ + preset

- `bien_tap.chuan_hoa`: trường lạ (`mirror`, …) bị từ chối; `toc_do` ∈ [1; 1,5]
  (chậm lại = video dài ra, trái `DUNG_SAI_DO_DAI_S`); `zoom` ≤ 3×; cạnh cắt ≥ 20 %;
  tỉ lệ ∈ {16:9, 9:16, 1:1, 4:5}; cách ∈ {cat, nen_mo}. Sai ⇒ TỪ CHỐI, không kẹp.
- Preset giữ hình: câu cùng khuôn "Kiểu “Giữ nguyên hình ảnh” …" — riêng cho tốc độ
  (lời hứa độ dài) và cho điều khiển điểm ảnh.
- `routes.py` 861 dòng (≤ 900): route chỉ gọi `bien_tap.tu_form`.

## 5. Trình duyệt thật (Playwright, Chromium, máy chủ dev cô lập `tools/asv_browser_server.py` cổng 8199)

Phiên dev tạo thẳng trong CSDL dev (không gõ mật khẩu). Kết quả:

- `asv/bien_tap.js?v=…` được nạp; 0 lỗi console, 0 request ≥ 400.
- Preset giữ hình: khối ẩn, câu chặn hiện; preset cắt: ngược lại.
- Mặc định: "Cách đổi tỉ lệ" và hai ô tâm **bị khoá** (không ô chết); chọn 9:16 cắt
  ⇒ mở.
- Chọn 1,25× · 9:16 cắt · tâm 30 % · cắt dưới 10 % ⇒ ô ẩn
  `{"toc_do":1.25,"cat_khung":{…"y1":0.9},"khung":{"ti_le":"9:16","cach":"cat","tam_x":0.3}}`,
  dòng trạng thái "Sẽ áp dụng: 1.25× · cắt mép · 9:16."
- Đổi sang preset giữ hình ⇒ ô ẩn về rỗng (không gửi giá trị bị ẩn).
- Gửi form thật (1,25× · 9:16 nền mờ) ⇒ 303 về `/run/…`, trang chi tiết hiện
  "Khung hình và tốc độ: 1.25× · 9:16".

Giới hạn: máy chủ dev không có worker/máy B, nên "đầu ra đổi" được chứng minh ở
tầng engine (§3), không qua một lần chạy trọn chuỗi AI.

## 6. Việc còn lại / quyết định tự chốt

- **Tự chốt:** tốc độ chỉ tăng (1–1,5×); một tâm dùng chung cho phóng và cắt-tỉ-lệ;
  khung nền mờ giữ cạnh ngắn của nguồn (1280×720 → 720×1280); tốc độ nhân đều, KHÔNG
  lập lại kế hoạch/TTS (lời lồng cũng nhanh theo, giữ cao độ).
- Sửa kèm: `logo + phụ đề` không lớp phủ chữ từng sinh `[ra]ass…[ra]`;
  `_co_khung` đổi chiều khi nguồn `rotation=90/270`. `PHIEN_BAN_CHE_DO` 6 → 7.
- Giao diện tối giản (xếp dọc); xem trước trên khung (`xem_truoc.js`) CHƯA vẽ cửa sổ
  cắt/tỉ lệ — làn GUI.
- `messages.po/.mo` thêm 35 mục (bản dịch EN); `check_dich_thieu` báo "đã dịch thêm
  8 mục" — chưa `--accept` (việc điều phối). Làn `phu-de` cũng nối vào `.po` ⇒ xung đột
  gộp `.po`/`.mo` dự kiến: gộp `.po` rồi `python tools\i18n.py bien-dich`.

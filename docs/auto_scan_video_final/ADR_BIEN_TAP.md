# ADR-ASVF-BIEN-TAP — Mở cắt khung, phóng to, đổi tỉ lệ, tốc độ

**Trạng thái:** CHẤP NHẬN · 22/09/2026 · làn `bien-tap` của phiên `asv-final`.
**Thay thế:** dòng `reframe`/`crop`/`zoom` trong `hop_dong_v4.CAM_TRONG_MVP` và
`reframe`/`zoom` trong `HAU_MVP` (khai từ V4, `ADR-V4-001`).

## Bối cảnh

`hop_dong_v4.CAM_TRONG_MVP` ghi: *"một mục rời khỏi đây là một quyết định sản
phẩm, và nó cần một ADR"*. Chủ dự án đã quyết trong đề bài asv-final: *"Hoàn thiện
… speed, zoom, crop, aspect ratio, reframe"*. Tệp này ghi lại quyết định đó để
bảng hợp đồng và lý do đi cùng nhau.

## Quyết định

1. `crop`, `zoom`, `reframe` **rời** `CAM_TRONG_MVP` (và `reframe`/`zoom` rời
   `HAU_MVP`), rồi **vào** `NANG_LUC_DOI_DIEM_ANH` cùng `speed`. Một mục chỉ ở
   đúng một bảng (`_kiem_tra_hop_dong` chốt).
2. Chỉ ở preset `smart_localize`. `localize_preserve_picture` phát `-c:v copy`:
   không có khung nào được giải mã để cắt/phóng, và preset hứa độ dài ra bằng độ
   dài vào ⇒ tốc độ cũng bị từ chối ở cửa, cùng khuôn câu với vùng che/lớp phủ.
3. Phạm vi của từng điều khiển (`apps/auto_scan_video/bien_tap.py`):
   - `toc_do` ∈ (1,0; 1,5] — **chỉ tăng tốc**: `DUNG_SAI_DO_DAI_S` hứa không preset
     nào làm video dài ra; trần 1,5 giữ lời lồng còn nghe được.
   - `cat_khung` — cửa sổ phân số trên khung nguồn, mỗi cạnh ≥ 20 %.
   - `zoom` — phóng **tĩnh** 1–3× quanh một tâm. Không camera path/motion.
   - `khung` — tỉ lệ `16:9 · 9:16 · 1:1 · 4:5`, cắt quanh tâm **hoặc** giữ trọn
     hình trên nền mờ.
4. Tốc độ nhân **đều** ở cuối chuỗi (`setpts` hình + `atempo` bản phối), sau khi
   lời lồng, nền, phụ đề đã đặt trên trục biên tập. Ánh xạ nguồn → bản ra là
   `BanDoThoiGian.ra(t) / toc_do`. Không lập lại kế hoạch thời gian hay TTS.
5. Vẫn **cấm**: `reorder`, `broll`, `upscale`, `music_replace`, `transition`.
   Và **không thuộc sản phẩm** (không phải "hoãn"): lật gương (mirror), đổi màu/
   dịch màu, nhiễu/"vân tay" để né nhận diện nội dung. Hồ sơ lạ (`mirror`, …) bị
   từ chối ở cửa như mọi trường lạ.

## Hệ quả

- Vùng che áp **trước** khung (toạ độ nguồn), logo/chữ/phụ đề áp **sau** (toạ độ
  bản ra). Luật L3 của `vung_che` (loại, không kẹp) đúng theo cấu trúc: vùng ngoài
  cửa sổ cắt không còn trong khung — không cần ánh xạ toạ độ.
- Kích thước bản ra tính MỘT lần (`hinh_hoc.khung_bien_tap`), ghi vào bản dựng
  (`khung_ra`), `ban_dung.kiem` tính lại để đối chiếu, `ket_xuat.kiem_tep_ra`
  đo lại trên tệp ra.
- `PHIEN_BAN_CHE_DO` 6 → 7, `PHIEN_BAN_QC` 3 → 4 (T15 đổi mốc phụ đề theo tốc độ).

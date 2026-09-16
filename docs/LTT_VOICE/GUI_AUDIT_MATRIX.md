# GUI_AUDIT_MATRIX — LTT Voice (16/09/2026)

Khuôn §31 của prompt GUI. Nhãn trạng thái: `PROVEN` · `LIKELY` · `PARTIAL` ·
`BLOCKED` · `NOT TESTED`. Cột **Status** ghi trạng thái THẬT tại thời điểm viết —
mục cần bản code mới chạy trên máy chủ ghi `NOT TESTED (P10)` cho tới lượt E2E
sau deploy (`GUI_DOI_SOAT_VA_PLAN_V2.md` §F0).

Nguồn bằng chứng: `GUI_RUNTIME_DIAGNOSIS.md` (đo 15/09) · `GUI_BROWSER_ACCEPTANCE.md` (dev 16/09) · `GUI_DOI_SOAT_VA_PLAN_V2.md`
(đo 16/09) · commit trên `phien/ltt-voice-gui-v2`.

| Area | Current | Problem | Severity | Evidence | Decision | Fix | Test | Status |
|---|---|---|---|---|---|---|---|---|
| Worker nhặt job Voice | pools `api:6, gpu:1, voice:1` | 13–16/09 thiếu làn `voice` ⇒ job `queued` 3 ngày, 0 event | P0 | env nssm + `jobs`/`job_events` 15/09; 2 job kẹt → `done` 16:23 sau khi thêm làn | GUI-D006 | `voice:1` (16/09, production) | G01 Chrome thật 16:37: queued 0,9 s → done 21 s, WAV/MP3 thật | PROVEN |
| Quan sát app vô hình | chỉ `do_sau_khoi_dong` hỏi riêng `voice` | không phát hiện app khác không có làn (5 app cần `ffmpeg`) | P1 | `app_vo_hinh('api:6, gpu:1')` ⇒ `ltt_voice` + 5 app | GUI-D006 | `job_worker.app_khong_lan_nao_nhat` + tool (`07e72360`); pools `gpu+ffmpeg:1` áp ở deploy | test_216 D006 | PROVEN (mã) · NOT TESTED (P8 production) |
| Phân loại giọng | 3 luật ở 3 chỗ | thẻ Giọng gắn "Giọng của tôi" cho mọi hồ sơ; bộ chọn gắn "Kho chung" theo cờ bỏ qua license | P0 | đọc HEAD `_voice_the.html:24`, `_voice_chon.html:185`, `tham_chieu.py:53` | GUI-D001 / D001-A | `tham_chieu.loai_giong` theo chủ sở hữu, route truyền `loai_giong` (`476f9539`) | test_532 (đối chứng HEAD 5 đỏ); `studio_dev` nhãn thẻ đúng 2 loại | PROVEN (dev) · NOT TESTED (P10) |
| Quyền trên giọng người khác | khối Tắt/Xoá/clip gốc mở cho mọi giọng không phải mẫu | khách thấy nút Tắt/Xoá + khoá kho mang UUID chủ | P1 | `voice.js:812`, `doc_man_giong.py:138` | GUI-D001 / V06 | khối quản lý chỉ `loai == 'toi'`; không gửi clip/UUID người khác | test_532; `studio_dev` giọng người khác: 0 Tắt/Xoá, 0 UUID | PROVEN (dev) · NOT TESTED (P10) |
| 25 giọng kho chung — hiển thị | 0 với tài khoản thường | 25/25 `license_status=cho_soat` ⇒ cổng kho chung loại | P0 | CSDL 16/09 + Chrome thật tài khoản thường: Kho chung = 0 | D002-A | duyệt license SAU khi dựng lại tệp (P9) | V03 | PROVEN (nguyên nhân) · BLOCKED→P9 |
| 25 giọng kho chung — tệp | `repr`/`source` mất trên R2 | bucket xoá object ~7 ngày | P0 | R2 HEAD 56/58 khoá mất (15/09); bucket 37 obj/46 MB (16/09) | D002-A · W-KHO | clip gốc 25/25 khớp SHA → `data\voice_goc\kho_chung`; `RoutedStorage` `voice/` về đĩa (`d1f92afa`); `dung_lai_giong_kho_chung` (`279ea391`) | test_83; chạy thử production 25/25 khớp | PROVEN (clip) · NOT TESTED (P8–P9) |
| Sao lưu dữ liệu giọng | `backup.ps1` chỉ gom tệp cấp đầu `data\` | clip gốc + `data\files\voice` không vào bản sao lưu | P1 | đọc `backup.ps1:73` | W-KHO | gom `voice_goc` + `files\voice` (trừ `out\`) | chạy thử trên thư mục tạm (bắt lỗi đường dẫn 8.3) | PROVEN (thư mục tạm) · NOT TESTED (Task SYSTEM) |
| Cổng ngôn ngữ — Studio `/tao` | chặn trước credit | — | — | `features.giai_giong` → `quyet_dinh` | D003-A | không đổi | test_355/384/522 | PROVEN |
| Cổng ngôn ngữ — Nghe ngay `/phat-dan` | bỏ `ngon_ngu` đã khai | khai EN + giọng VI lọt tới giữ credit (402) | P1 | đối chứng HEAD trả 402 | D003-A | nhận `ngon_ngu` + `ma_loi` (`8c510816`) | test_533 | PROVEN (mã) · NOT TESTED (P10) |
| Cổng ngôn ngữ — Nghe thử văn bản | vẫn phát khi lệch (D006 cũ) | trái luật BLOCK mọi cửa | P1 | `_p_nghe_thu.py` HEAD | D003-B (chủ dự án duyệt) | 400 trước lượt + GPU (`6699b23f`) | test_526 (đối chứng HEAD 200); `studio_dev` fetch thật 400 | PROVEN (dev) — cửa không có nút GUI |
| Cổng ngôn ngữ — Dự án đọc tất cả | lỗi không mang `ma_loi` | JS không phân loại được | P2 | `_p_du_an.py:544` | D012 | `ma_loi` (`5fdbbd43`) | test_350/357 | PROVEN (mã) |
| Cổng ngôn ngữ — ChatLTT `speech.ltt` | giữ credit trước khi kiểm | hoàn tiền sau khi worker từ chối | P1 | audit W4' | ngoài phạm vi Voice | task riêng (nhánh `claude/compassionate-ptolemy-41c12c`) | test_1263 (phiên đó) | PARTIAL (phiên khác) |
| Cổng ngôn ngữ — ASV lồng tiếng | kiểm bằng `text="."` | không bao giờ so văn bản thật | P1 | `giong_noi.py:141` | ngoài phạm vi Voice | task riêng | — | PARTIAL (phiên khác) |
| Mô tả `language` API | "overrides detection" | sai từ D002 | P2 | manifest HEAD | chủ dự án duyệt | câu đúng + golden + CHANGELOG + `check_api_compat --accept` (`6203f9ae`) | test_181/190/530/524 | PROVEN |
| Bộ lọc nhãn (giới/vùng/phong cách) | màn Giọng ẩn, bộ chọn giữ | cùng giọng lọc "Nam" mất ở màn này còn ở màn kia; 29/29 `gioi` rỗng | P1 | `voice.js:681` vs `:1790` | GUI-D004 Option B | màn Giọng giữ + câu giải thích (`12334f61`) | test_532 D004; `studio_dev` lọc Nam giữ 3 thẻ thiếu nhãn + câu | PROVEN (dev) · NOT TESTED (P10) |
| Số đếm loại giọng | nút lọc không có số | V01 đòi số thật | P2 | template HEAD | V01 | đếm từ `giong_mau` + `loai_giong` (`0ea493fd`) | test_532 V01; `studio_dev` Chrome: 21/20/0/1 | PROVEN (dev) · NOT TESTED (P10) |
| Hàng đợi Studio | "Đang xếp hàng…" vô hạn | không phân biệt 3 giây với 3 ngày | P0 | GUI 13–16/09 | GUI-D005 | `tuoi_hang_doi_s` + `muc_cho`; cảnh báo >60 s + trang việc (`292d6ffb`) | test_347 D005; `studio_dev` `/ket-qua` thật, job 3 phút ⇒ câu + liên kết | PROVEN (dev) · NOT TESTED (P10) |
| Hàng đợi Lịch sử | badge "Đang chờ" tĩnh | job 3 ngày trông như job mới | P1 | template HEAD | GUI-D015 | badge "Chờ lâu bất thường", ngưỡng chung `hang_doi.py` (`f4c527c1`) | test_348 D015; `studio_dev` badge đúng một hàng | PROVEN (dev) |
| Tốc độ đọc | 6 nút rời | chủ dự án muốn thanh kéo 0,05 | P2 | yêu cầu 16/09 | W5' | range 0,5–2,0 bước 0,05, hằng số chung API (`0fccc341`) | test_347/392/530; Chrome thật bàn phím 1→1,25→1→2 | PROVEN (dev) · NOT TESTED (P10) |
| Nghe ngay × tốc độ | bỏ qua tốc độ | Web Audio đổi `playbackRate` đổi cả cao độ | P2 | `voice.js ganPhatDan` | W5' | nói rõ phát 1× khi thanh kéo ≠ 1 (`8c510816`) | test_533 JS | PROVEN (mã) |
| Kết quả ngoài khung nhìn | không tự cuộn | 996×943: khung kết quả ở scrollY≈1010 | P2 | Chrome thật 16/09 | W5' | cuộn khi ngoài khung, tôn trọng reduced-motion (`741757e6`) | node --check; cụm studio | PARTIAL · NOT TESTED (P10) |
| Responsive + a11y | — | — | — | `studio_dev` 6 kích thước × Studio/Giọng | D010/D011 | — | 0 tràn ngang, CTA trong khung nhìn ở cả 6, 0 console error, 0 request hỏng, 0 điều khiển thiếu nhãn | PROVEN (dev) · NOT TESTED (URL công khai, P10) |
| Tràn ngang ~1000 px | header nền tảng `.hdr-right` | 1066 > 996 px | P3 | Chrome thật 16/09 | ngoài phạm vi Voice | — | — | LIKELY (nền tảng) |
| Nút Tạo dính đáy | che khối Tốc độ khi cuộn | thiết kế có chủ ý (§12 CTA luôn thấy) | — | CSS `.lv-st-nut sticky` | D007 | không đổi | W8' CTA trong khung nhìn 6/6 | PROVEN |
| Tải WAV | không `Content-Disposition` | thẻ đã có `download`, cùng origin | — | template `id="lv-tai" download` | — | không đổi | fetch thật 200 `audio/wav` | PROVEN |
| Bánh cóc `main` đỏ sẵn | nuốt lỗi 66/62 · trùng số 1261/1262 · mypy 108/107 | chặn L3 mọi nhánh | P1 | cây tạm ở `10839479` | sửa thật, không nâng mốc | tools/* (`f5106ad0`) + gộp governance (`ae7271d4`) | 5 công cụ PASS trên cây gộp | PROVEN |
| Nút "Chi tiết" trên thẻ giọng | bấm chuột không mở khung | `<button>` bên trong thẻ bị `BEN_TRONG` nuốt — có sẵn trên `main` | P1 | Browser pane `studio_dev` 16/09 | V06 | miễn trừ `.lv-the-xem` (`0821cd52`) | test_532 (HEAD 0 khớp); Playwright chuột/Enter/Space | PROVEN (dev) · NOT TESTED (P10) |

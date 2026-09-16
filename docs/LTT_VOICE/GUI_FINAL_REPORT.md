# GUI_FINAL_REPORT — LTT Voice GUI V2 (16/09/2026)

Nhánh `phien/ltt-voice-gui-v2` → `main` = production = **`d5bd7b07`** (deploy 22:47, đẩy GitHub).
Chi tiết: `GUI_DOI_SOAT_VA_PLAN_V2.md` (đối soát + plan + sổ nợ) · `GUI_AUDIT_MATRIX.md` ·
`GUI_BROWSER_ACCEPTANCE.md` · `GUI_DECISION_LOCK.md`.

## A. Hai sự cố P0 ban đầu — trạng thái

| Sự cố | Nguyên nhân (đã chứng minh) | Xử lý | Bằng chứng production |
|---|---|---|---|
| Job Voice "Xếp hàng" mãi | worker không có làn `voice` | pools `api:6, gpu+ffmpeg:1, voice:1` | job Studio 16/09 23:2x xong sau 11 s; worker log đủ 3 làn |
| 25 giọng kho chung không hiện | `license=cho_soat` + tệp `source`/`repr` bị R2 tự xoá (~7 ngày) | clip gốc bền `data\voice_goc` → dựng lại 25 giọng; `voice/` định tuyến về đĩa máy A; duyệt license | tài khoản thường thấy **Kho chung 25** |

## B. Thay đổi đã lên production

- **Catalog:** phân loại giọng theo chủ sở hữu (của tôi / kho chung / mẫu) ở mọi màn; số đếm trên nút lọc; khối quản lý (Tắt/Xoá/clip gốc) chỉ cho giọng của chính người xem; không lộ khoá kho/UUID người khác.
- **Bộ lọc nhãn (D004):** màn Giọng giữ giọng thiếu nhãn như bộ chọn Studio, kèm câu giải thích.
- **Hàng đợi (D005/D015):** câu chờ theo tuổi hàng đợi thật; > 60 s báo "lâu hơn bình thường" + liên kết trang việc; badge "Chờ lâu bất thường" ở Lịch sử.
- **Ngôn ngữ:** Nghe ngay tôn trọng ô Ngôn ngữ đã khai; Nghe thử văn bản CHẶN khi lệch làn (D003-B); Dự án trả `ma_loi`; mô tả `language` của API sửa đúng (+ golden, CHANGELOG).
- **Tốc độ:** thanh kéo 0,5–2,0 bước 0,05 dùng chung hằng số với API; Nghe ngay nói rõ phát 1×.
- **Lưu trữ:** `RoutedStorage` + `LTT_STORAGE_LOCAL_PREFIXES=voice/`; `backup.ps1` gom dữ liệu giọng; công cụ `chep_tien_to_r2_ve_dia.py`, `dung_lai_giong_kho_chung.py`.
- **Worker:** phát hiện app không có làn nào nhặt (`app_khong_lan_nao_nhat`), thêm làn `ffmpeg`.
- **Sửa lỗi có sẵn trên `main`:** nút "Chi tiết" trên thẻ giọng bấm chuột không mở gì.

## C. Cổng chất lượng

- Trong phiên chỉ test nhắm; **L3 một lần** trên `180bc8fc`: đỏ 2/33 bước (luật vận hành + 5 test: 394, 1006, 1259, 1260, 975 — 3 trong đó đỏ sẵn trên `main`). Sửa `71dee01c`, chạy lại đúng từng phép → xanh. Lượt khép `--doi --tu` tự nâng lên đầy đủ và lần đầu kẹt `-n 1` (máy bận lúc khởi động) ⇒ **chủ dự án chốt các phép đỏ xanh là PASS**.
- Sau khi hoà `origin/main` `80319d0a`: bánh cóc tĩnh PASS, test giao nhau VPS/CLI 339 passed.
- `scan_source_secrets` 0 · alembic 1 head · `nghiem_thu_deploy` 0 lệch/thiếu/thừa.

## D. E2E production (tài khoản thường) — 7/7 PASS

Cache-bust `aa4194b6` · số đếm 45/20/25/0 · chi tiết kho chung không quản lý · lọc Nam giữ 25 giọng thiếu nhãn · Studio tạo thật giọng kho chung tốc độ 1,25 (WAV + MP3 200) · Nghe ngay lệch làn 400 · console/network sạch.

## E. Vận hành / sổ tiền đã chạm

- `C:\LTTPlatform\secrets\app.env`: 2 dòng (bản sao `app.env.bak-voice-v2-20260916`).
- R2 → đĩa: 30 tệp, 19,1 MB; **không xoá gì trên R2**.
- Tài khoản thử `thu.giongnoi@lttstudios.local` (chủ 25 giọng): `grant +24` (ghi lý do) để nộp enroll; 1 job trùng đã huỷ + `refund 2`. Số dư cuối nằm trong sổ, không sửa tay.
- Máy B (LLM) **không bị chạm** ngoài một `GET /health` chỉ đọc (đọc token qua SSH, chủ dự án cho phép).

## F. Còn lại / rủi ro

| # | Việc | Ghi chú |
|---|---|---|
| 1 | E2E góc nhìn **chủ 25 giọng** trên production | cần chủ dự án đăng nhập tài khoản `.local` (đặt lại mật khẩu bằng `tai_khoan_thu.py --dat-lai-mat-khau`) — đã PROVEN trên dev |
| 2 | Phiên VPS phải **hoà `main` `d5bd7b07`** trước khi đẩy/deploy nhánh của họ | đã nhắn; nếu không, deploy của họ lùi bản Voice |
| 3 | `dung_lai_giong_kho_chung --chay` chạy lại sẽ nộp trùng giọng đã `done` | dedupe chỉ khớp job chưa kết thúc; thêm cờ lọc/kiểm repr trước khi nộp nếu cần chạy lại |
| 4 | Worker khởi động tải `yolov8s.pt` từ GitHub | có sẵn trước V2, ngoài phạm vi Voice |
| 5 | Cửa `/nghe-thu-van-ban` không có nút GUI nào gọi | ghi nhận |

## G. Điểm (§32, tự chấm có căn cứ)

| Tiêu chí | Điểm | Căn cứ |
|---|---|---|
| Đúng nhu cầu ban đầu (2 P0) | 10/10 | cả hai hết trên production, đo bằng trình duyệt thật |
| Tính đúng dữ liệu/sổ tiền | 8/10 | sổ khớp, nhưng lượt dựng lại nộp trùng 1 job (đã hoàn) |
| Kiểm chứng | 8/10 | test nhắm + L3 + E2E công khai; thiếu góc nhìn chủ giọng trên production |
| An toàn vận hành | 9/10 | 0 job/lease trước cài, sao lưu env, không xoá R2, không chạm LLM |
| **Tổng** | **35/40** | |

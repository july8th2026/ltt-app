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
| 1 | ~~E2E góc nhìn chủ 25 giọng~~ | **XONG 23:5x** — chủ thấy 29 "Của tôi" + Tắt/Xoá; khách thứ hai thấy 25 kho chung, không quản lý |
| 2 | Phiên VPS phải **hoà `main` `d5bd7b07`** trước khi đẩy/deploy nhánh của họ | đã nhắn; nếu không, deploy của họ lùi bản Voice |
| 3 | ~~Chạy lại `dung_lai_giong_kho_chung` nộp trùng~~ | **ĐÃ SỬA** — bỏ qua giọng đã có job `done` cùng khoá dựng lại (đối chứng production: bỏ qua 25/25) |
| 4 | ~~`yolov8s.pt` tải lại từ GitHub~~ | **ĐÃ SỬA 17/09 (`dc555d41`)** — thật ra tải ở job `taoclipngan` đầu tiên sau MỖI deploy (cwd `app\` bị thay); trọng số nay ở `data\models\yolo\`, tải một lần |
| 5 | ~~Cửa `/nghe-thu-van-ban` không có nút GUI~~ | **ĐÃ SỬA 17/09 (`bba7f7b1`)** — nút "Nghe thử câu đầu (miễn phí)" trong Studio, chỉ giọng mẫu, ≤160 ký tự; kiểm dev Playwright; production kiểm sau deploy |

## G. Điểm (§32, tự chấm có căn cứ)

| Tiêu chí | Điểm | Căn cứ |
|---|---|---|
| Đúng nhu cầu ban đầu (2 P0) | 10/10 | cả hai hết trên production, đo bằng trình duyệt thật |
| Tính đúng dữ liệu/sổ tiền | 8/10 | sổ khớp, nhưng lượt dựng lại nộp trùng 1 job (đã hoàn) |
| Kiểm chứng | 9/10 | test nhắm + L3 + E2E công khai 3 tài khoản (thường, chủ giọng, khách thứ hai) |
| An toàn vận hành | 9/10 | 0 job/lease trước cài, sao lưu env, không xoá R2, không chạm LLM |
| **Tổng** | **36/40** | |

## H. Tài khoản thử dùng chung (16/09, chủ dự án cho phép)

`khach1/2/3.thu@lttstudios.local` (5.000 credit mỗi tài khoản, bút toán `grant`) + `thu.giongnoi@…local`.
Mật khẩu chỉ ở `C:\LTTPlatform\secrets\tai_khoan_thu.json`; phiên nào cần đăng nhập gọi
`tools/tai_khoan_thu.py --cookie <email>`. Hướng dẫn: `docs/TAI_KHOAN_THU.md`.

## I. Đợt 17/09 — hai hạng mục "ngoài phạm vi" + hai lỗi bắt được trên đường

| # | Việc | Kết quả |
|---|---|---|
| 1 | `yolov8s.pt` tải lại từ GitHub | `dc555d41` — trọng số ở `data\models\yolo\`, tải một lần (tra mã ultralytics 8.4.115) |
| 2 | Nút cho cửa `/nghe-thu-van-ban` (U-13) | `bba7f7b1` — Studio, chỉ giọng mẫu, ≤160 ký tự, báo lượt còn lại |
| 3 | **Lỗi E2E production:** nút không phát — CSP `media-src 'self' blob:` chặn `data:` | `9e07fbf2` — phát qua `blob:`; đối chứng dưới CSP thật: `data:` MediaError 4, `blob:` 2,4 s |
| 4 | **Lỗi công cụ:** `test_nhanh.py` pha 2 chạy LẠI cả danh sách tệp ⇒ L2 `--pham-vi` lâu hơn L3 | `935f9bba` + `test_537` |

Cổng: L2 `engine:cutclipshort,app:ltt_voice,server:web,cong_cu` trên `935f9bba` — bộ test PASS (464 tệp);
bước `check_multiproc` đỏ vì một gate khác chạy `--khong-khoa` cùng CSDL `postgres_test`, chạy lại
có khoá: 7 passed. Deploy `935f9bba` 03:14 — `nghiem_thu_deploy` 0/0/0, `/health/ready` 200.

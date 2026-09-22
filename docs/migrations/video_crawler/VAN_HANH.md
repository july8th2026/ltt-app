# Vận hành video_crawler (lane vcm-suckhoe, W1-L4)

> Phạm vi tệp này: đọc trang sức khoẻ, tắt/bật nền theo vận hành, cập nhật `yt-dlp`, xử lý yêu cầu gỡ.
> Luật gate/deploy/worktree chung: `docs/00_LTT_OPERATING_CONTRACT.md` — không chép lại ở đây.

## 1. Trang sức khoẻ `/video-crawler/van-hanh`

- Chỉ operator (`require_operator` — admin env hoặc user CSDL `role=admin`); người dùng thường ⇒ 403,
  chưa đăng nhập ⇒ 303 `/login`; cờ `LTT_VIDEO_CRAWLER` tắt ⇒ 404 (giống mọi route khác của app, xem
  `routes.py:_cong_co`).
- Nguồn số liệu: **đọc thẳng bảng `jobs`** trong 24 giờ gần nhất (`suc_khoe.thong_ke`), KHÔNG có bảng
  riêng — không có việc "đồng bộ" hay "trễ số liệu" cần lo, số luôn mới nhất tính tới lúc tải trang.
- Đọc bảng theo từng cột:
  - **Job tải** — tổng số job `video_crawler.tai` của nền đó trong cửa sổ (không tính job khám phá,
    khám phá miễn phí và không phản ánh "tải được hay không").
  - **Mục tải xong** — số video đã lưu tệp thành công (kể cả job chỉ tải được một phần).
  - **Mục lỗi / Lỗi theo mã** — số video lỗi trong các job tải MỘT PHẦN thành công, gộp theo mã lỗi
    (`apps/video_crawler/loi.py` là nơi tra nghĩa từng mã: `yt_403`, `yt_bot`, `can_dang_nhap`,
    `nen_chan`, `chi_la_anh`, `rieng_tu`, `khong_ton_tai`, `mang`, `loi_khac`…).
  - **Job lỗi toàn phần** — job không tải được MỤC nào (mọi mục đều lỗi, hoặc lỗi trước khi vào vòng
    tải). Không có chi tiết theo mã ở mức này: `jobs.py:_tai_voi` ném exception trước khi trả `result`
    trong ca này, nên thông tin từng mục không được lưu — chỉ đếm được ở mức job. Muốn biết lý do cụ
    thể của một job lỗi toàn phần, mở job đó ở `/jobs/{id}` (cột `error` có câu lỗi, xem operator).
  - **Tỉ lệ thành công** = mục tải xong / (mục tải xong + mục lỗi + job lỗi toàn phần). Job "bỏ qua vì
    đã tải trước" (`bo_qua_trung`, không tính tiền) KHÔNG tính vào tử số cũng không tính vào mẫu số —
    nó không phải thành công cũng không phải lỗi.
  - **Khuyến nghị** = "Nên tắt" khi tỉ lệ thành công < 80% VÀ có ≥ 10 mục trong cửa sổ (mẫu quá nhỏ thì
    không đủ tin — một job lỗi mạng tạm thời không nên làm nền bị đề nghị tắt).
- Trang **chỉ khuyến nghị**, không tự tắt gì. Người vận hành đọc rồi quyết, xem mục 3.

## 2. Cập nhật `yt-dlp`

`yt-dlp` là gói thay đổi nhanh nhất trong app này (mỗi lần nền tảng nguồn đổi giao diện là một bản vá
mới); coi lịch cập nhật như một việc định kỳ, không chỉ khi có lỗi.

1. **Kiểm phiên bản mới**: `pip index versions yt-dlp` hoặc trang release GitHub
   (`yt-dlp/yt-dlp`). Đọc changelog — ưu tiên bản vá cho nền đang lỗi nhiều ở trang sức khoẻ.
2. **Cài vào venv thử** (KHÔNG cài trực tiếp production trước khi có smoke xanh):
   `pip install --upgrade "yt-dlp==<version>"` trong một venv/worktree tách biệt.
3. **Chạy smoke mạng thật** (luật brief chung: một smoke ngoài bộ test, thư mục tạm, xoá sau, báo kết
   quả trung thực): thử tải 5–10 URL công khai mỗi nền đang `bat=True`, ưu tiên các nền có lịch sử lỗi
   ở trang sức khoẻ. `yt-dlp -F <url>` (chỉ liệt kê format, không tải) là bước rẻ trước khi tải thật.
4. **Chạy bộ test không đọc mạng**: `python -m pytest tests/test_190*_video_crawler_*.py -q` (mọi test
   video_crawler dùng DNS/adapter giả — xem `test_1905` — nên không phải chờ mạng, chỉ xác nhận
   nâng cấp không đổi hành vi mà mã đang giả định, ví dụ tên field trong `info_dict`).
5. **Đổi `requirements-server.txt`** (dòng `yt-dlp>=...`) — ĐÂY LÀ TỆP `DUNG_CHUNG`: đổi nó thì
   không được deploy giữa phiên, chỉ sau L3 (hợp đồng §4, dòng "requirements-server.txt thuộc
   DUNG_CHUNG" trong PLAN_MVP §A). Điều phối là người chạm tệp này lúc gộp.
6. **Deploy + nghiệm thu**: theo `docs/16_CAP_NHAT_VA_DEPLOY.md`; sau deploy, chạy lại smoke thật của
   bước 3 trên chính máy production (khác venv thử, có thể khác kết quả vì IP/DNS/impersonate).
7. **Đo lại trang sức khoẻ** 24 giờ sau deploy — tỉ lệ thành công phải bằng hoặc tốt hơn trước khi
   nâng; nếu xấu hơn, đó là dấu hiệu bản mới có regression cho nền đó, xét hạ lại phiên bản.

Nếu smoke cho thấy YouTube tụt dưới ~95% vì bot-check (mã `yt_bot`) dù đã nâng `yt-dlp`, đó là tín hiệu
cho Q3 (PLAN_MVP §B) — cân nhắc dịch vụ PO token — KHÔNG phải việc tự quyết ở lane này.

## 3. Tắt / bật một nền (vận hành, không đụng mã)

- **Tắt mềm một hoặc nhiều nền**: đặt biến môi trường `LTT_VIDEO_CRAWLER_TAT` = danh sách id nền cách
  nhau bằng dấu phẩy, ví dụ `LTT_VIDEO_CRAWLER_TAT=douyin,bilibili`. Id đúng như cột "Nền" ở trang sức
  khoẻ / `apps/video_crawler/nen_tang.py` (`douyin`, `bilibili_tv`, `bilibili`, `xiaohongshu`, `weibo`,
  `tiktok`, `youtube`, `facebook`, `instagram`, `twitter`).
- Hiệu lực: nền trong danh sách biến mất khỏi lưới chọn ở trang chính (`cac_nen_bat()`) và job mới
  nhắm nền đó bị chặn ở validate (`lay_nen_bat()` ném `NenKhongHopLe` → khách thấy "chưa được hỗ trợ").
  Đọc env **mỗi lần gọi**, không cache — đổi biến rồi **không cần khởi động lại** worker/web để có
  hiệu lực (khác hầu hết cờ khác của nền tảng vốn đọc lúc nạp module).
- Job đang CHẠY của nền vừa tắt không bị huỷ — tắt mềm chỉ chặn job MỚI, không động vào job đang xử lý
  (đúng luật "sổ sách": không hoàn tiền một job đang chạy chỉ vì vận hành đổi cờ giữa chừng).
- **Bật lại**: xoá id đó khỏi danh sách (hoặc xoá hẳn biến môi trường nếu không còn nền nào cần tắt).
- Đây LÀ khuyến nghị của trang sức khoẻ, không phải hành động tự động — không có việc nào tự đọc trang
  sức khoẻ rồi tự ghi biến này.

## 4. Yêu cầu gỡ nội dung

Văn bản cam kết quyền, điều khoản bảo đảm/bồi hoàn và kênh báo vi phạm (thời hạn xử lý 72 giờ) do lane
L1 PHÁP LÝ soạn ở `docs/migrations/video_crawler/PHAP_LY_NHAP.md` (Q2, PLAN_MVP §B) — tệp này chỉ trỏ
tới quy trình VẬN HÀNH khi nhận được yêu cầu gỡ, không lặp lại nội dung pháp lý:

1. Yêu cầu gỡ đến qua kênh báo vi phạm hiển thị trên UI (L1 dựng) — ghi lại: người gửi, nội dung/link
   bị yêu cầu gỡ, lý do, thời điểm nhận.
2. Tra job đã tạo ra tệp đó: tìm theo `params` (`nen_tang`, `dau_vao`/`muc[*].id`) trong `jobs` của
   `app_slug=video_crawler`, `job_type=video_crawler.tai` — hoặc theo storage key
   `video_crawler/<owner_id>/<job_id>/<video_id>.mp4` nếu người báo cáo có link tải trực tiếp.
3. Xoá tệp khỏi storage (`platform_core/storage.py:get_storage().delete(key)`), KHÔNG xoá dòng `jobs`
   (dòng job là bằng chứng bút toán credit — luật "giữ đúng sổ sách" ở `CLAUDE.md` dự án).
4. Nếu người dùng còn khả năng tải lại đúng video đó (không trùng theo `da_tai_ids` chỉ chặn trong
   phạm vi MỘT user — Q4/L6 chưa gộp ở thời điểm viết tệp này), ghi lại video_id vào danh sách chặn
   tạm (chưa có bảng chặn toàn nền tảng trong MVP — đây là CONTRACT GAP nếu tần suất gỡ cao, báo chủ
   dự án chứ không tự thêm bảng ở lane vận hành).
5. Phản hồi người báo cáo trong 72 giờ (thời hạn L1 cam kết) — mẫu thư do L1 soạn.
6. Ghi vào `docs/NHAT_KY.md` cuối phiên có xử lý yêu cầu gỡ: nguồn, hành động, thời điểm.

## 5. Liên quan

| Câu hỏi | Trỏ tới |
|---|---|
| Mã lỗi nghĩa là gì | `apps/video_crawler/loi.py` |
| Registry nền + tắt mềm | `apps/video_crawler/nen_tang.py` |
| Số liệu trang sức khoẻ tính thế nào | `apps/video_crawler/suc_khoe.py` (docstring đầu tệp) |
| Văn bản pháp lý, kênh báo vi phạm | `docs/migrations/video_crawler/PHAP_LY_NHAP.md` (lane L1) |
| Sổ lỗi + độ phủ toàn app | `docs/migrations/video_crawler/SO_LOI.md` |
| Deploy | `docs/16_CAP_NHAT_VA_DEPLOY.md` |

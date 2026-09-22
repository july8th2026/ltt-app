# Phiên đăng nhập nền tảng + cào theo kênh — phân tích & kế hoạch (`video_crawler`, 23/09/2026)

> Chủ của: (1) ai đăng nhập các nền cần phiên và job của khách dùng phiên nào; (2) khách chọn kênh để cào thế nào.
> Chưa có mã. Sự thật hiện trạng đọc từ nhánh `phien/vcm-tich-hop` @ `8121b5a7`; phép đo ghi ngày 23/09.
> Quyết định cần chủ dự án: §6.

## 1. Hiện trạng (đọc mã, không suy)

| Điều | Sự thật | Dẫn chứng |
|---|---|---|
| Ai đăng nhập | **Từng khách tự đăng nhập**: dán `cookies.txt` (Netscape) của chính họ ở mục "Đăng nhập nền tảng" | `apps/video_crawler/phien.py:1-9` |
| Admin đăng nhập một lần, khách kế thừa? | **KHÔNG.** Bảng `vc_phien` khoá UNIQUE `(owner_id, nen_tang)`; worker chỉ nạp phiên của **chủ job** | `tables.py:28`, `jobs.py:61` (`_phien(adapter, owner_id, nen_id)`) |
| Lưu cookie | Chỉ giữ cookie đúng tên miền, bắt buộc có cookie xác thực, mã hoá `secretbox`; worker nhận tệp tạm quyền 600 trong thư mục job, xoá khi xong | `phien.py` |
| Nền cần phiên | Douyin (mọi chế độ), Bilibili (mọi chế độ — HTTP 412 ẩn danh), Instagram (link), Xiaohongshu (tìm + kênh), TikTok (từ khoá), Kuaishou (tìm + kênh, đang tắt) | `nen_tang.py` |
| Đăng nhập QR | Mới **thiết kế**, chưa mã; cần làn worker `browser` (production chưa có) | `THIET_KE_QR.md` |
| Cào theo kênh | Chế độ `kenh` = **dán link/handle kênh**; không có tìm kênh theo tên, không có tuỳ chọn trong kênh (tab, sắp xếp, khoảng ngày) | `adapters/youtube.py:75-80` |

Hệ quả thực tế: khách thường **không có** cookies.txt ⇒ 6 nền cần phiên gần như không dùng được. Đó là lỗ hổng
sản phẩm lớn nhất còn lại.

## 2. "Admin đăng nhập một lần, khách kế thừa" — phân tích

### 2.1 Ba phương án

| | A. Mỗi khách tự đăng nhập (hiện tại) | B. Chỉ tài khoản hệ thống (admin) | C. **Lai** — kho tài khoản hệ thống + phiên riêng tuỳ chọn |
|---|---|---|---|
| Khách phải làm gì | Tự xuất cookies.txt (khó) | Không gì | Không gì; ai muốn thì thêm phiên riêng |
| Tỉ lệ dùng được nền cần phiên | Thấp | Cao tới khi tài khoản bị khoá | Cao, có đường lui |
| Rủi ro khoá tài khoản | Rải trên tài khoản khách | **Dồn** vào vài tài khoản LTT: N khách × M video/giờ trên một tài khoản ⇒ nền phát hiện tự động (N7) | Kiểm soát bằng lease + trần + nghỉ theo **tài khoản** |
| Trách nhiệm pháp lý | Khách đứng tên phiên | **LTT đứng tên** mọi lượt tải | LTT đứng tên với lượt dùng kho ⇒ cần cam kết quyền (đã có, L1) + nhật ký |
| Riêng tư | Khách thấy nội dung theo tài khoản của họ | Kết quả tìm theo tài khoản LTT (gợi ý cá nhân hoá lẫn giữa khách) | Như B cho khách dùng kho |
| Vận hành | Không | Theo dõi hạn cookie, thay tài khoản | Như B + chọn nguồn phiên |

**Khuyến nghị: C.** B thuần là một điểm hỏng duy nhất: tài khoản bị khoá thì mọi khách mất nền cùng lúc. A thuần
làm nền cần phiên chết về mặt sản phẩm.

### 2.2 Cách C vận hành

1. **Admin** vào trang vận hành `/video-crawler/van-hanh/tai-khoan` (chỉ `require_operator`), thêm **nhiều** tài khoản
   phụ cho mỗi nền (dán cookies.txt ngay; QR cho admin ở giai đoạn sau). Mỗi tài khoản: nhãn, trạng thái
   (`song`/`het_han`/`bi_chan`/`tam_nghi`), hạn cookie, lỗi gần nhất, số lượt đã dùng trong giờ.
2. **Job** chọn nguồn phiên theo thứ tự:
   - khách có phiên riêng còn hạn cho nền đó ⇒ dùng phiên riêng;
   - chưa có ⇒ **mượn** một tài khoản kho còn khoẻ qua `ExecutionLease` (resource `vc_tk:<id>`, UNIQUE sẵn có của nền
     tảng): một tài khoản phục vụ **một job một lúc**, nghỉ giữa lượt, trần lượt/giờ theo nền;
   - kho hết chỗ ⇒ job **chờ** (`jobs.DangBan`, về hàng đợi, không tiêu lượt, không chạm tiền); kho không còn tài
     khoản sống ⇒ báo khách "nền tạm không khả dụng" + hoàn tiền.
3. **Sức khoẻ tự động**: lỗi `can_dang_nhap` / `nen_chan` trên tài khoản kho ⇒ đánh dấu tài khoản đó, thử tài khoản
   khác một lần; cookie sắp hết hạn ⇒ cảnh báo trên trang vận hành (không tự gửi ra ngoài).
4. **Cô lập**: khách không bao giờ thấy, tải về hay biết tài khoản nào; `params`/`result`/log chỉ ghi
   `nguon_phien = rieng | kho` (không ghi id tài khoản vào phần khách đọc được; id nằm ở sự kiện INTERNAL).
5. **Trần theo khách khi dùng kho** (chống một khách vét kho): ví dụ ≤ 20 video/giờ qua kho, cộng với trần chung 60/giờ.

### 2.3 Điều C KHÔNG làm

- Không dùng tài khoản **chính** của LTT/chủ dự án — chỉ tài khoản phụ (nền khoá thì mất tài khoản phụ).
- Không profile trình duyệt chung (donor Viral dùng profile Chromium chung — cấm ở SaaS, SUPER PROMPT §P).
- Không dùng kho cho nội dung **riêng tư theo tài khoản** (danh sách theo dõi, video đã thích) — cái đó chỉ phiên riêng.

## 3. "Mở popup/nền tảng rồi chọn kênh" — cái gì làm được

### 3.1 Phép đo 23/09: nhúng trang nền vào LTT bị chặn

`curl -I` trang chủ/kênh (header chặn nhúng):

| Nền | Header | Nhúng được? |
|---|---|---|
| YouTube | `X-Frame-Options: SAMEORIGIN` | ✗ |
| Douyin | `X-Frame-Options: DENY` + `frame-ancestors` chỉ miền ByteDance | ✗ |
| Instagram | `X-Frame-Options: DENY` | ✗ |
| Facebook | `X-Frame-Options: DENY` | ✗ |
| X/Twitter | `SAMEORIGIN` + `frame-ancestors 'self' x.com twitter.com` | ✗ |
| Xiaohongshu, TikTok, Bilibili | không có header trên phản hồi HEAD | kể cả tải được khung cũng vô dụng (dưới) |

Kể cả nền không chặn, khung iframe **vẫn không giải được bài toán**:
- trang LTT không đọc được khung khác nguồn đang ở kênh nào (same-origin policy);
- cookie bên thứ ba bị trình duyệt chặn ⇒ đăng nhập trong khung không giữ được.

Mở **popup/tab mới** (`window.open`) thì khách duyệt được, nhưng LTT cũng không đọc được URL của tab đó ⇒ khách vẫn
phải chép link về. Popup chỉ là **lối tắt mở trang tìm kiếm của nền**, không phải cơ chế chọn kênh.

### 3.2 Các đường thật

| Đường | Trải nghiệm | Chi phí | Khuyến nghị |
|---|---|---|---|
| **P1. Tìm kênh ngay trong LTT** | Gõ tên ⇒ thẻ kênh (ảnh, tên, số theo dõi) ⇒ bấm ⇒ "trang kênh" trong LTT với các chế độ ⇒ xem trước ⇒ chọn ⇒ tải | Vừa; theo nền | **Làm — đường chính** |
| P2. Dán link kênh (đã có) + nhận mọi dạng link | Chép link từ app nền (kể cả link rút gọn `v.douyin.com`, `xhslink.com`) | Thấp | **Làm** (link rút gọn hiện bị từ chối) |
| P3. Nút "Mở trên nền tảng" | Mở tab tìm kiếm của nền với từ khoá; khách chép link về | Rất thấp | Làm kèm P2 |
| P4. Tiện ích trình duyệt "LTT Crawler" | Đang xem kênh trên nền ⇒ bấm "Cào kênh này" ⇒ LTT mở sẵn trang kênh; có thể kiêm "gửi phiên của tôi" (khách đồng ý rõ, chỉ cookie đúng tên miền) | Cao: phát hành Chrome/Edge store, duyệt, bảo trì | Sau MVP — đúng nhất với ý "mở nền, tìm kênh, chọn" |
| P5. Trình duyệt từ xa phát hình về LTT | Như duyệt thật | Rất cao; rủi ro bảo mật | Không làm |

Đo 23/09: yt-dlp tìm **kênh** YouTube ẩn danh được —
`https://www.youtube.com/results?search_query=lofi+girl&sp=EgIQAg%3D%3D` trả thẻ kênh `YoutubeTab` có
`channel_follower_count` và ảnh (Lofi Girl 15,8 triệu). Các nền khác: cần spike (§5 L10).

### 3.3 Trang kênh trong LTT — các chế độ

| Tuỳ chọn | YouTube | TikTok/Douyin | XHS | Bilibili | Ghi chú |
|---|---|---|---|---|---|
| Tab: Video / Shorts / Live / Playlist | ✓ (`/videos`, `/shorts`, `/streams`, `/playlists`) | Video | Ghi chú video | Video / tuyển tập | |
| Sắp xếp mới nhất | ✓ | ✓ | ✓ | ✓ | mặc định |
| Sắp xếp phổ biến | spike | spike | spike | ✓ (API `order=click`) | |
| Khoảng ngày đăng | ✓ nhưng danh sách phẳng không có ngày ⇒ phải trích từng video (chậm) | có trong API | có trong API | có trong API | đặt trần số mục quét |
| Thời lượng (ngắn/dài) | ✓ | ✓ | ✓ | ✓ | lọc sau khi có metadata |
| Số lượng, không trùng | ✓ (đã có) | ✓ | ✓ | ✓ | |

## 4. Luồng khách sau khi làm

```
Chọn nền ─┬─ "Tìm kênh": gõ tên ─► thẻ kênh ─► bấm ─┐
          ├─ "Dán link kênh" (kể cả link rút gọn) ───┼─► Trang kênh: tab · sắp xếp · khoảng ngày · thời lượng · số lượng
          └─ "Mở trên nền tảng" (tab mới, chép link) ┘        │
                                                              ▼
                                  Xem trước (miễn phí) ─► chọn video ─► cam kết quyền ─► tải (giá theo thời lượng)
Nền cần phiên: job tự dùng phiên riêng của khách, không có thì mượn kho tài khoản hệ thống (khách không phải làm gì).
```

## 5. Kế hoạch làn (đợt W4 — mỗi làn một worktree, TDD, không hai làn cùng tệp)

| Làn | Model | Tệp sở hữu | Việc | Xong khi |
|---|---|---|---|---|
| L9 KHO TÀI KHOẢN | Opus | MỚI `kho_tai_khoan.py`, `tables.py` (bảng `vc_tai_khoan`), migration, `governance.py` (1 hàng), `jobs.py::_phien` | bảng tài khoản kho mã hoá; chọn nguồn phiên (riêng > kho); lease `vc_tk:<id>`; trần/giờ + nghỉ theo tài khoản; đánh dấu hỏng + thử tài khoản khác một lần; kho đầy ⇒ `DangBan`; kho chết ⇒ lỗi người gọi + hoàn tiền | test: 2 job cùng lúc không dùng chung tài khoản; tài khoản hỏng bị loại; khách không đọc được id/cookie ở bất kỳ route nào |
| L9b TRANG VẬN HÀNH TÀI KHOẢN | sonnet | MỚI `routes_tai_khoan.py`, `templates/vc_tai_khoan.html` | thêm/xoá/tạm nghỉ tài khoản (dán cookies.txt), trạng thái, hạn, lượt/giờ; `require_operator` | kiểm GUI; khách thường 403 |
| L10 TÌM KÊNH | Opus | `adapters/base.py` (`KenhItem`, `tim_kenh`), `adapters/youtube.py`, `bilibili.py`, `douyin_web.py`, `xhs_web.py`, `tiktok.py` | spike từng nền trước (ghi kết quả thật vào PLATFORM_MATRIX), rồi `tim_kenh(tu_khoa, n)` cho nền làm được; ảnh đại diện qua proxy `anh_bia` | YouTube + ≥ 2 nền cần phiên chạy thật với kho |
| L11 TRANG KÊNH + CHẾ ĐỘ | sonnet | `features.py`, `routes.py`, `templates/*` | chế độ mới `tim_kenh`; thẻ kênh; trang kênh với tab/sắp xếp/khoảng ngày/thời lượng; truyền tuỳ chọn vào `kham_pha` | kiểm GUI luồng §4 trên bản dev |
| L12 LINK RÚT GỌN | sonnet | `an_toan_url.py`, `nen_tang.py` | theo redirect CÓ KIỂM từng bước (allowlist tên miền + chặn IP nội bộ, ≤ 3 bước) cho `v.douyin.com`, `xhslink.com`, `v.kuaishou.com`, `b23.tv`, `vt.tiktok.com`; nút "Mở trên nền tảng" | test SSRF: redirect sang IP nội bộ / miền lạ bị chặn |
| L13 QR CHO ADMIN | Opus | theo `THIET_KE_QR.md`, thu hẹp: chỉ operator | cần làn worker `browser` trên production | chờ quyết định D6 |
| L14 TIỆN ÍCH TRÌNH DUYỆT | — | repo/thư mục riêng | P4 | chờ quyết định D5 |

Thứ tự: L12 và L9 song song (không chung tệp) → L9b + L10 → L11 → nghiệm thu thật (tài khoản kho do chủ dự án cấp)
→ L13/L14 nếu duyệt. Gate: test nhắm từng làn; L1/L2 trước deploy giữa phiên; L3 một lần cuối phiên.

## 6. Quyết định cần chủ dự án

| # | Câu hỏi | Khuyến nghị |
|---|---|---|
| D1 | Làm kho tài khoản hệ thống (phương án C)? Cho nền nào? | Có; Douyin, XHS, Bilibili, TikTok trước; Instagram sau (khoá tài khoản mạnh nhất) |
| D2 | Ai cung cấp tài khoản phụ, bao nhiêu mỗi nền? | ≥ 3 tài khoản phụ/nền; chủ dự án tạo và tự dán cookies.txt (tác tử không tạo/đăng nhập tài khoản) |
| D3 | Giá khi dùng kho | Giữ bảng giá hiện tại; thêm trần 20 video/giờ/khách qua kho |
| D4 | Pháp lý: LTT đứng tên phiên khi khách dùng kho | Bổ sung một đoạn vào `PHAP_LY_NHAP.md`; giữ cam kết quyền + nhật ký; cần chủ dự án duyệt |
| D5 | Làm tiện ích trình duyệt (P4)? | Sau MVP, khi P1 đã đo được tỉ lệ dùng |
| D6 | QR cho admin (thêm `browser:1` vào `LTT_WORKER_POOLS`, cài Playwright) | Sau L9; chỉ admin ⇒ rủi ro QRLJacking nhỏ hơn bản cho khách |

## 7. Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Tài khoản kho bị khoá hàng loạt | nhiều tài khoản, lease một job/tài khoản, trần + nghỉ theo tài khoản, đánh dấu hỏng sớm, trang vận hành |
| IP datacenter máy A làm nền nghi ngờ | đo tỉ lệ thật theo nền (trang sức khoẻ L4); cân nhắc định tuyến qua máy IP dân dụng nếu < 80% |
| Rò cookie kho | mã hoá `secretbox`, tệp tạm 600 trong thư mục job, không vào params/result/log; test route không trả |
| Một khách vét kho | trần theo khách qua kho |
| Nền đổi API tìm kênh | adapter riêng từng nền + `trich_xuat_hong` + trang sức khoẻ + tắt mềm `LTT_VIDEO_CRAWLER_TAT` |

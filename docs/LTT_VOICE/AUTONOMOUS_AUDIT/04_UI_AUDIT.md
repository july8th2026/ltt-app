# 04 — UI AUDIT (2026-09-05)

Đo trên trình duyệt thật (Playwright, Chromium), server dev từ **cây nguồn**
(`127.0.0.1:8127`).

⛔ **Vì sao không đo trên `127.0.0.1:8100` hay URL công khai.** Cả hai đang phục
vụ bản deploy **cũ** (xem `00_RUNTIME_TRUTH.md`). Đo ở đó thì mọi kết quả nói về
mã của `master`, không nói gì về thay đổi trong lượt này. Đây là lý do lượt kiểm
GUI phải dựng server riêng trước, và là lý do quy tắc 5b của `CLAUDE.md` (chốt
trên URL công khai) chỉ áp dụng **sau** khi deploy — xem `07_RELEASE_REPORT.md`.

## Studio

| hạng mục | trước | sau |
|---|---|---|
| ô đếm | `0 / 1500 ký tự` | `0 / 100.000 ký tự` |
| `maxlength` ô nhập | `1500` | **không có** (đếm điểm mã trong JS) |
| ước thời lượng / số đoạn | — | `≈ 1h 32m — 67 đoạn, ghép liền mạch` |
| vượt trần | ô nhập lặng lẽ chặn phím | nút Tạo **tắt** + `role="alert"` nói thừa bao nhiêu |
| nhập TXT quá dài | cắt mất phần đuôi | **giữ nguyên**, báo, để khách tự cắt |
| bố cục | *(đã sửa trước lượt này)* | `page--immersive`, ba cột |

⭐ Ô đếm nay nói **ba** điều thay vì một: bao nhiêu ký tự, bài dài bao lâu, chia
mấy đoạn. Con số ký tự/giây lấy từ `gia.KY_TU_MOI_GIAY_UOC` — **cùng** hằng số
mà phần giữ credit dùng, nên giao diện và hoá đơn không nói hai con số khác nhau
về cùng một văn bản. Số đoạn ở đây là **ước**; số chính xác do `/xem-truoc` trả
về vì nó chạy đúng `chia_doan`.

### Khả năng tiếp cận

- Khối vượt trần là `role="alert"` chứ không phải một dòng chữ mờ. Đây là lý do
  **duy nhất** nút Tạo bị tắt; một nút tắt không nói vì sao là một ngõ cụt, và
  người dùng trình đọc màn hình không "thấy" nút vừa đổi màu.
- Nút tắt có `opacity: 0.55` + `cursor: not-allowed` — quy ước sẵn có của nền tảng.
- Ô nhập giữ `aria-labelledby` + `aria-describedby` trỏ vào ô đếm.

### Đáp ứng

| khổ | tràn ngang | bố cục | nút Tạo trong viewport |
|---|---|---|---|
| 1920×1080 | không | `max-width:1800px` | ✅ |
| 1366×768 | không | ba cột `318/555/416` | ✅ |
| 390×844 | không (`scrollWidth` 375) | một cột | ✅ |

Khối cảnh báo ở 390 px rộng 322 px, không tràn.

## API

| hạng mục | trước | sau |
|---|---|---|
| "Mỗi lượt gọi" | `100000 ký tự` | `100.000 ký tự` |
| số 4+ chữ số không định dạng | có | **không còn** |
| dấu vết `1500` | không | không |

## Nav

Năm tab, đo trên trình duyệt: *Tạo tiếng nói · Giọng của tôi · Dự án · Lịch sử ·
API*. Khớp `manifest.nav`. Không tab nào 404. Không tab Chạy lô.

## Console

| trang | lỗi |
|---|---|
| Studio | 0 ngoài dự kiến (một lỗi 400 là **của chính phép kiểm biên**) |
| API | 0 |

## Điều KHÔNG đo được trong lượt này

⚠️ Màn **Lịch sử** và **Dự án** có trình phát + sóng âm, nhưng lượt này **không
có bản thu nào** (không có sidecar GPU để sinh tiếng). Nên:

- `songDeu()` — track phẳng cho bản đọc dài — **chưa chạy trên một tệp thật**.
- Ngưỡng `TRAN_GIAY_SONG` **chưa** được kích hoạt bởi một bản thu > 600 giây.

Cả hai đã chốt bằng phép kiểm đọc mã (`test_397`), tức bản sửa không thể lặng lẽ
biến mất — nhưng đó là điều kiện **cần**, không phải **đủ**. Ghi ở đây để không
ai đọc bản báo cáo này thành "đã kiểm sóng âm trên bài dài".

## STATUS

✅ Studio, API: đo thật, đạt.
⚠️ Lịch sử / Dự án: chỉ kiểm dựng trang, không kiểm trình phát (thiếu bản thu).

# Backlog mobile P0 / P1 / P2

Mỗi mục trỏ tới bằng chứng trong `02_BASELINE.md`. Không có mục nào ở đây là suy
đoán — mục nào chưa đo được thì ghi rõ là **chưa đo**.

## P0 — chặn công việc chính, có người dùng thật đang gặp

| # | Vấn đề | Bằng chứng | Phase | trạng thái |
|---|---|---|---|---|
| P0-1 | `ltt_voice` phục vụ audio **không có Range** → Safari/WebKit không phát được dù tải được | §1a | C | ✅ **đã sửa** `bec5643d` |
| P0-2 | `chatltt` phục vụ media không có Range, cùng hình dạng | §1a | C | ✅ **đã sửa** `bec5643d` |

⚠️ P0-1 chỉ được gọi là **đã sửa ở phía máy chủ**. Vế *"vì thế Safari phát được"*
**chưa đo được** — Playwright WebKit trên máy này không giải mã nổi audio (xem
`CHECKPOINT.md`). Phát thật đã chứng minh trên **Chromium**; Safari phải chờ
thiết bị thật.

⚠️ P0-1 mới chốt được vế *"máy chủ không phát ra Range"*. Vế *"vì thế Safari không
phát"* **phải đo bằng phát thật trên WebKit ở Phase C** trước khi được gọi là root
cause. Một giải thích khớp hoàn hảo mà chưa đo là cách kết thúc điều tra quá sớm.

## P1 — hỏng trải nghiệm trên mọi trang, hoặc rủi ro dữ liệu

| # | Vấn đề | Bằng chứng | Phase |
|---|---|---|---|
| P1-1 | 5 bản chép bộ phân tích Range, **không bản nào trả 416**, suffix range trả sai dữ liệu | §1b | D | ✅ `fab506e6` — còn **0** bản |
| P1-2 | `bytes=0-` nuốt cả tệp vào RAM ở 4/5 app | §1b | D | ✅ `fab506e6` |
| P1-3 | **Mọi** ô nhập < 16px → iOS auto-zoom khi focus | §3 | C | ✅ `bec5643d` — 55 → **0** trên cảm ứng |
| P1-4 | Không có `viewport-fit=cover` ⇒ safe-area **không thể** hoạt động | §2 | B | ✅ `bec5643d` |
| P1-5 | 4 thanh hành động dính đáy không chừa safe-area | §2 | B | ✅ `bec5643d` |
| P1-6 | Luật `pointer:coarse` thiếu `a` | §4 | B | ✅ `bec5643d` — 468 → **200** |
| P1-7 | Vỏ ChatLTT mobile là một **trang dài**, composer dưới màn hình | `03_BACKLOG` §mới | C | ✅ `4cc11f14` |
| P1-8 | Vẽ sóng tải + giải mã **165 MB** cho canvas `display:none` | `05_SONG_AM.md` | C | ✅ `5e3e2cc8` |
| P1-9 | 5 vòng hỏi job không biết tab đang ẩn | — | D | 🟡 `7a65a6ad` — còn 3 vòng trong React |

## P2 — cục bộ, một route hoặc một app

| # | Vấn đề | Bằng chứng | Phase |
|---|---|---|---|
| P2-1 | `/huong-dan` tràn ngang | §5 | F | ✅ `bec5643d` + `76bb448b` (320px) |
| P2-2 | `<video>` thiếu `playsinline` | §6 | D | ✅ `fab506e6` — **7** thẻ, không phải 1 |
| P2-3 | `start > end` xử lý khác nhau giữa `agent` và 4 app kia | §1b | D | ✅ `fab506e6` |
| P2-4 | Nút **thật** < 44px trong app React (`run-primary`, `blank-flow`, `canvas-home`…) — cùng bẫy `:where()` độ đặc hiệu 0 | sweep | **E** | ⬜ |
| P2-5 | `songDeu` tự gọi lại chính nó — đệ quy vô hạn | `05_SONG_AM.md` §6 | C | ✅ `5e3e2cc8` |

⭐ P2-2 đáng chú ý: lượt quét trình duyệt chỉ thấy **1** thẻ, vì nó đếm thẻ đã
render trên các trang ghé qua. Đọc mã tìm ra **7** — sáu thẻ kia nằm trong nhánh
template có điều kiện. Trình duyệt và mã nguồn bắt được hai tập khác nhau; cần cả hai.

## Chưa đo — không được viết vào bất kỳ báo cáo nào là PASS hay FAIL

- Waveform Voice: mức tiêu thụ bộ nhớ/thời gian khi decode audio dài.
- Bàn phím ảo che composer (`chatltt`, `chataistudio`) — Playwright không dựng
  được OSK thật.
- Vòng đời job dài khi ẩn tab / tải lại / quay lại.
- Kéo-thả trong `autosubvideo` (timeline) và `prompt_ai_ommi` (sắp xếp cảnh):
  có đường thay thế bằng chạm hay không.
- React Flow trong `agent`: nối node bằng chạm.
- Thiết bị thật: iPhone Safari, Android Chrome.

## Thứ tự thi công

```
B  hợp đồng shared  ──►  C  media transport + Voice/Chat P0
                          │
                          ├─►  D  media generator (migrate 5 bản chép)
                          ├─►  E  editor phức tạp
                          └─►  F  bề mặt chuẩn
                                   └─►  G  harness + ma trận  ──►  H  cổng cuối
```

P1-4/P1-5/P1-6 nằm ở Phase B vì cả ba đều là **một** sửa chữa ở chrome nền tảng
phục vụ **mọi** app — đúng định nghĩa shared layer của pack.

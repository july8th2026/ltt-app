# Backlog mobile P0 / P1 / P2

Mỗi mục trỏ tới bằng chứng trong `02_BASELINE.md`. Không có mục nào ở đây là suy
đoán — mục nào chưa đo được thì ghi rõ là **chưa đo**.

## P0 — chặn công việc chính, có người dùng thật đang gặp

| # | Vấn đề | Bằng chứng | Phase |
|---|---|---|---|
| P0-1 | `ltt_voice` phục vụ audio **không có Range** → Safari/WebKit không phát được dù tải được | §1a | C |
| P0-2 | `chatltt` phục vụ media không có Range, cùng hình dạng | §1a | C |

⚠️ P0-1 mới chốt được vế *"máy chủ không phát ra Range"*. Vế *"vì thế Safari không
phát"* **phải đo bằng phát thật trên WebKit ở Phase C** trước khi được gọi là root
cause. Một giải thích khớp hoàn hảo mà chưa đo là cách kết thúc điều tra quá sớm.

## P1 — hỏng trải nghiệm trên mọi trang, hoặc rủi ro dữ liệu

| # | Vấn đề | Bằng chứng | Phase |
|---|---|---|---|
| P1-1 | 5 bản chép bộ phân tích Range, **không bản nào trả 416**, suffix range trả sai dữ liệu | §1b | B+D |
| P1-2 | `bytes=0-` nuốt cả tệp vào RAM ở 4/5 app | §1b | B+D |
| P1-3 | **Mọi** ô nhập < 16px → iOS auto-zoom khi focus (55 ô ở 390px) | §3 | C+F |
| P1-4 | Không có `viewport-fit=cover` ⇒ safe-area **không thể** hoạt động | §2 | B |
| P1-5 | 4 thanh hành động dính đáy không chừa safe-area | §2 | B |
| P1-6 | Luật `pointer:coarse` thiếu `a` ⇒ `a.hdr-logo` 40×30 và liên kết nav 200×37 lọt, trên **mọi** trang | §4 | B |

## P2 — cục bộ, một route hoặc một app

| # | Vấn đề | Bằng chứng | Phase |
|---|---|---|---|
| P2-1 | `/huong-dan` tràn ngang 12px (Chromium) / 28px (WebKit) do khối `<code>` | §5 | F |
| P2-2 | `/taoclipngan` có 1 `<video>` thiếu `playsinline` | §6 | D |
| P2-3 | `start > end` xử lý khác nhau giữa `agent` và 4 app kia | §1b | B |

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

# 06 — TEST MATRIX (2026-09-05)

Hai cột **ĐO** và **TÍNH** tách riêng có chủ ý. Trộn chúng lại là cách một bản
báo cáo nói quá thứ nó biết.

## A. Biên trần ký tự — ĐO trên trình duyệt thật

Cửa `POST /ltt-voice/xem-truoc`, server dev từ cây nguồn (`127.0.0.1:8127`),
đăng nhập bằng tài khoản dev. Cột "ô đếm" là số hiện trên màn hình lúc gõ.

| ký tự | ô đếm (JS) | máy chủ `so_ky_tu_tho` | HTTP | số đoạn | nút Tạo |
|---|---|---|---|---|---|
| 0 | 0 | — | — | — | bật |
| 11 (ascii) | 11 | 11 | 200 | 1 | bật |
| 1.499 | — | — | 200 | 1 | bật |
| 1.500 | — | — | 200 | 1 | bật |
| **1.501** | — | **1.501** | **200** | **2** | bật |
| 3.000 | — | 3.000 | 200 | 2 | bật |
| 10.000 | — | — | 200 | — | bật |
| 100.000 | 100000 | 100.000 | 200 | **67** | **bật** |
| 100.001 | 100001 | — | **400** | — | **tắt** |
| 100.050 (từ TXT) | 100050 | — | — | — | **tắt** |

⭐ Mốc **1.501 → 200, hai đoạn** là mốc quan trọng nhất bảng này. Trước 31/08 nó
trả về một lời từ chối, và thông điệp từ chối lại nhắc tới một đường long-form
chưa ai xây.

Thông điệp ở 100.001: *"Văn bản dài 100.001 ký tự, vượt giới hạn 100.000 cho một
lượt đọc."* — có dấu phân cách, khớp ô đếm trên cùng màn hình.

## B. Unicode — ĐO, hai phía so trực tiếp

| mẫu | ô đếm (JS mới) | máy chủ `len()` | JS cũ `.length` | khớp |
|---|---|---|---|---|
| `Hello world` | 11 | 11 | 11 | ✅ |
| `Xin chào Việt Nam` (NFC) | 17 | 17 | 17 | ✅ |
| `Xin cha`+U+0300+`o` (tổ hợp) | 9 | 9 | 9 | ✅ |
| `Chào ❤` (BMP) | 6 | 6 | 6 | ✅ |
| `Chào 😀` (ngoài BMP) | **6** | **6** | *7* | ✅ |
| `Xin chào 😀 hello` | **16** | **16** | *17* | ✅ |
| 😀 × 50.001 | **50.001** | **50.001** | *100.002* | ✅ |
| `a\nb\nc` | 5 | 5 | 5 | ✅ |

⛔ Ba dòng đậm là ba dòng mà bản cũ **sai**. Dòng cuối là dòng nguy hiểm: 50.001
emoji = 100.002 đơn vị mã, nên `maxlength="100000"` **cắt mất một nửa** một văn
bản mà máy chủ hoàn toàn chấp nhận.

## C. Nhập TXT — ĐO, tệp thật qua `DataTransfer`

Tệp: 100.051 ký tự, có BOM UTF-8, xuống dòng CRLF.

| kiểm | kết quả |
|---|---|
| BOM bị bỏ | ✅ `charCodeAt(0) !== 0xFEFF` |
| CRLF → LF | ✅ |
| **văn bản bị cắt** | ✅ **KHÔNG** — ô nhập giữ đủ 100.050 ký tự |
| ô đếm | `100050` |
| dòng báo nhập | *"Tệp dài 100.050 ký tự, vượt giới hạn 100.000… Văn bản được giữ nguyên — bạn tự cắt, hoặc đưa sang Dự án."* |
| dòng vượt trần | *"Đang thừa 50 ký tự — 100.050 / 100.000…"* |
| nút Tạo | **tắt** |

⭐ Bản cũ ở đúng ca này **vứt 50 ký tự cuối** và chỉ báo lại sau khi đã vứt.

## D. Bố cục — ĐO ở bốn khổ

| khổ | tràn ngang | cột | nút Tạo trong viewport |
|---|---|---|---|
| 1920×1080 | không | `max-width: 1800px`, `page--immersive` | ✅ (top 971 / 1080) |
| 1366×768 | không | `318px 555px 416px` — ba cột | ✅ (top 721 / 768) |
| 390×844 | không (`scrollWidth` 375) | một cột | ✅ |

Khối cảnh báo vượt trần ở 390 px: rộng 322 px, **không** tràn ra ngoài.

⛔ Lỗi `.page{max-width:1180px}` bó màn Studio đã **không còn** — `page--immersive`
đang có hiệu lực.

## E. Console / mạng

| trang | lỗi console | ghi chú |
|---|---|---|
| Studio | 0 ngoài dự kiến | một lỗi 400 là **của chính phép kiểm biên** ở mục A |
| API | 0 | |

## F. Bộ test tự động

| tệp | số phép kiểm | chốt gì |
|---|---|---|
| `tests/test_397_ltt_voice_bien_ky_tu.py` | 32 | biên, Unicode, và **giao diện không quay lại cách đếm cũ** |
| `tests/test_398_dau_van_tay_ban_chay.py` | 7 | dấu vân tay runtime; marker hỏng không được ném |

## G. TÍNH TOÁN — không phải đo

⚠️ Bảng bộ nhớ sóng âm ở `03_LONGFORM_FRONTEND.md` là **suy ra** từ định dạng
đầu ra (48 kHz mono 16-bit ⇒ 96 KB/giây) và hành vi tài liệu hoá của
`decodeAudioData`. **Chưa** đo trên một bản đọc dài thật — lượt kiểm này không có
sidecar GPU.

⚠️ Số ký tự/giây (19,86) và RTF (0,152) lấy từ phép đo 03/09 ghi trong
`tham_so_cong_khai.py`, **không** đo lại trong lượt này.

## Điều KHÔNG kiểm được trong lượt này

- Sinh tiếng thật đầu-cuối (không có sidecar GPU) ⇒ đường ghép nhiều đoạn, đo
  thời lượng, quyết toán credit, dọn tệp **chưa chạy thật** ở lượt này. Chúng có
  bộ test riêng đã tồn tại (`test_342_ltt_voice_noi_dai.py` v.v.) và chạy trong
  gate đầy đủ.
- Sóng âm ở một bản đọc > 600 giây (cần tệp tiếng thật).
- Hành vi qua Cloudflare (URL công khai) — xem `07_RELEASE_REPORT.md`.

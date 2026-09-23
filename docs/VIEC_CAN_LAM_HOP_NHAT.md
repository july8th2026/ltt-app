# Việc cần làm — hợp nhất hai kho (ảnh chụp 2026-09-23, ~18:00)

> **Tệp này là BẢNG QUYẾT ƯU TIÊN, không phải nguồn chân lý.** Chi tiết + bằng chứng của từng
> mục nằm ở sổ gốc; sửa trạng thái thì sửa ở sổ gốc trước, rồi chụp lại bảng này.
>
> | Loại | Sổ gốc |
> |---|---|
> | Lỗi LTTCODE đã xảy ra, có bằng chứng | `D:\LTTCODEAPP\docs\LTTCODE\reports\self-improve\SO_LOI_VAN_HANH.md` (**V-NN**) |
> | Việc chưa làm phía LTTCODE (nghiên cứu, năng lực thiếu) | `D:\LTTCODEAPP\docs\LTTCODE\HANG_MUC_BAN_SAU.md` (**N-NN**) |
> | Nợ nền tảng cũ (từ 01/08) | `docs/KE_HOACH_TON_DONG.md` |
> | Quyết định sản phẩm | `docs/QUYET_DINH_NEN_TANG.md` |
>
> Nguồn của hầu hết mục mới: **lượt diễn tập vận hành thật D1** (23/09), chạy LTTCODE 0.2.6 đã
> cài trên `DESKTOP-H9AGFUQ`, việc thật = chứng minh bản sao lưu khôi phục được.

## 1. Chặn đường, làm trước

| # | Việc | Kho | Sổ gốc | Vì sao gấp |
|---|---|---|---|---|
| 1.1 | Lỗi hạ tầng tạm thời (502/503/504 tầng cổng) bị xếp `UPSTREAM_UNKNOWN` ⇒ **không thử lại, giết lượt khách** | LTTCODE | V-19 | Do chính Task 13 siết fail-closed. Một cú 502 của Cloudflare khi origin đứt là mất lượt, dù lỗi mang sẵn `retryAfter 60s` |
| 1.2 | `409 insufficient_credit` **không kèm `can`/`con`** | Nền tảng | V-22 | `luong.py:1307` viết `except ThieuCredit:` (bắt mà không giữ ngoại lệ). Hợp đồng v1 có sẵn chỗ chứa `limit`/`actual`. Chính lỗi này làm phiên chẩn đoán 23/09 quy nhầm tài khoản, mất ~20 phút |
| 1.3 | Quá tải kéo dài ⇒ lượt khách **chết** thay vì xếp hàng | Cả hai | V-23 | Bản đồ đường đi hứa "người thứ tám xếp hàng, không bị từ chối". Hai lối: client đợi theo `providerRetryAfterMs`, hoặc A xếp hàng thật khi hết suất |

## 2. Giám sát — hiện đang mù đúng chỗ nguy hiểm

| # | Việc | Kho | Sổ gốc | Bằng chứng |
|---|---|---|---|---|
| 2.1 | `/live` cổng máy B không nói gì về GPU/model | Nền tảng | N-05 | 23/09 16:20 hai card rớt bus PCIe (lỏng dây PSU): `/live` vẫn 200, bề mặt vẫn khớp cây, ping và cổng đều mở — **mọi phép đo tầng HTTP đều xanh** trong khi không model nào chạy |
| 2.2 | Không có cảnh báo khi dịch vụ suy giảm | Nền tảng | (mới) | Sự cố khoá pool 19/09 và mất GPU 23/09 đều do người phát hiện. Hiện chỉ có `canh_bao_ttft_b.py` và `giam_sat_may.py` |

## 3. Thông tin tài khoản trong LTTCODE — cùng một họ thiếu sót

| # | Việc | Kho | Sổ gốc |
|---|---|---|---|
| 3.1 | Hiện **số dư credit** và **mức tiêu mỗi lượt** trong app | Cả hai | N-04 |
| 3.2 | Quyết: đổi `SCOPES_KHOA` (thêm `credits:read`) thì khách đang đăng nhập phải đăng nhập lại, hay nền tảng nâng quyền khoá cũ | Nền tảng | N-04 §hệ quả |

> App biết tên tài khoản, biết token, **không biết gì về tiền**: không số dư, không mức tiêu,
> và khi hết tiền thì lỗi cũng không nói thiếu bao nhiêu (1.2). Ba thứ này nên làm cùng đợt.

## 4. Sao lưu và khôi phục — phát hiện của chính lượt diễn tập

| # | Việc | Kho | Trạng thái |
|---|---|---|---|
| 4.1 | **Đường khôi phục thiếu bước nâng cấp lược đồ.** Bản sao 02:30 hôm nay chứa alembic `e4a19c07b5d2`, CSDL đang chạy ở `5e1a9c46b2d7` ⇒ khôi phục xong sẽ có CSDL **cũ hơn mã đang chạy**; `restore.ps1` không có bước nào chạy `alembic upgrade head` | Nền tảng | agent D1 đang kết luận |
| 4.2 | `restore.ps1` **không có đường diễn tập thật**: không `-Live` thì chỉ giải nén, không nạp CSDL; có `-Live` thì ghi đè production. Agent D1 đang dựng `dien_tap_khoi_phuc.ps1` | Nền tảng | đang làm |
| 4.3 | Bản sao lưu nằm **trên chính máy production** (`D:\LTTBackups`) — máy hỏng là mất cả CSDL lẫn secrets lẫn mirror mã | Nền tảng | mục 6.3 backlog từ 01/08, chưa làm |
| 4.4 | Diễn tập rollback chưa từng chạy thật (mục cuối chưa tick của plan lỗi LLM) | Nền tảng | mở |

## 5. Phát hành và cửa vào

| # | Việc | Kho | Sổ gốc |
|---|---|---|---|
| 5.1 | `notes` rỗng ở manifest **dev** 0.2.5/0.2.6 ⇒ hộp thoại cập nhật không hiện "có gì mới". Bản stable 0.2.6 đã có notes (sửa 23/09). Quy trình phát hành nên **bắt buộc** `-Notes` | LTTCODE | V-20 |
| 5.2 | Cloudflare chặn User-Agent mặc định của `urllib` (403 `error code: 1010`); `curl`, `requests`, UA trình duyệt đều lọt | Nền tảng | N-06 |
| 5.3 | Bộ cài 279 MB phục vụ với `Cache-Control: no-store`, `cf-cache-status: BYPASS` ⇒ **mỗi lượt tải kéo trọn 279 MB qua tunnel từ máy nhà**. `/nexus/dl/` đã được mở ngoại lệ cache với đúng lập luận này (cho 26 MB) | Nền tảng | đo 23/09; sửa một dòng ở `server/app.py`, **chờ chủ dự án duyệt** vì đụng tệp dùng chung |

## 6. Plugin và năng lực agent

| # | Việc | Sổ gốc |
|---|---|---|
| 6.1 | Agent không tự cài/bật plugin trong phiên được; nếu mở phải kèm cổng duyệt (plugin là mã tuỳ ý, đọc được `LTT_API_KEY`) | N-01 |
| 6.2 | Khách không cài được plugin npm: `dsh plugin add` cần **pnpm**, bản cài chỉ có `node.exe` | N-02 |
| 6.3 | **CHỜ ĐO:** bật một suite có ăn vào lượt đang chạy không | N-03 |
| 6.4 | Agent cha giao việc chạy lệnh cho trợ lý CHỈ ĐỌC rồi bị guard chặn, **lặp lại y nguyên** thay vì đổi đường (23/112 dòng đỏ `pwsh` trong 7 ngày) | V-21 |
| 6.5 | **Khoá `tools:` trong tệp agent người dùng bị BỎ QUA ÂM THẦM** — `~/.agents/agents/*.md` nhận `tools: [...]`, `parseAgentRole` không đọc khoá đó, **không lỗi không cảnh báo**. Người dùng tưởng đã khoá agent con thành chỉ-đọc, thực tế nó có **toàn bộ công cụ của host**. Nặng thêm vì `lib/runtime/user-panels.js:12-14` mô tả khuôn là "Claude Code agents frontmatter" — tức mời người ta viết `tools:` rồi lặng lẽ vứt. Tối thiểu: cảnh báo khi gặp khoá không hỗ trợ | V-25 |
| 6.6 | **Tiêu đề cửa sổ lấy nguyên dòng đầu của prompt.** Bản 0.2.7 đo được `document.title` = `"# ============================================================ # SUPER PROMPT - LTTCODE"` — tiêu đề phiên sinh từ một prompt mở đầu bằng dải `# ====`. `H12_session_title_caps` (chặn độ dài) **xanh**, nên không phép nào bắt được: thiếu bước **lọc nhiễu markdown/banner** trước khi đặt tiêu đề. Khách thấy rác trên thanh cửa sổ | V-26 |
| 6.7 | **Phép `P08_document_title` giả định máy sạch.** Nó chốt `document.title == "LTTCODE"`, nhưng app **khôi phục phiên cũ** lúc khởi động ⇒ tiêu đề thành tên phiên ⇒ **ĐỎ trên mọi máy đã dùng**, bất kể bản build tốt hay xấu. Đây là phép đo lệch chiều: nó đỏ vì môi trường, và đỏ vì môi trường là thứ dạy người ta bỏ qua màu đỏ. Sửa: so với tên phiên đang mở, hoặc chạy trên hồ sơ sạch | (mới) |

## 7. Nợ cũ còn mở (không sinh ra hôm nay)

| # | Việc | Sổ gốc |
|---|---|---|
| 7.1 | **Một worker duy nhất**, không định tuyến theo năng lực ⇒ job GPU dài chặn mọi job nhanh. Mã đã có `capabilities`, hàng đợi đã `SKIP LOCKED`, H44.3 đã kiểm hai worker PASS — chỉ là chưa bật | `KE_HOACH_TON_DONG.md` 2.2/4.2 |
| 7.2 | FK constraints (toàn vẹn dữ liệu) | 7.1 backlog |
| 7.3 | E2E đa tiến trình (web + worker) | 7.2 backlog |
| 7.4 | V-01 sidecar thoát `0xffffffff` · V-02 boot timeout 60s · V-06 subagent fail giữa chừng · V-14 `dsh-tool-search` nuốt `isError` (nháp issue chờ gửi) · V-16 `subagent run was cancelled` chờ kiểm lại | SO_LOI_VAN_HANH |

## 8. Việc của chủ dự án (không ai làm thay được)

| # | Việc |
|---|---|
| 8.1 | Chạy `verify_installed` trên bản 0.2.6 đã cài (hôm nay đã bỏ qua theo quyết định của chủ dự án) |
| 8.2 | Canary 5 kịch bản + kiểm lại V-16 |
| 8.3 | Chứng chỉ Authenticode (B2) và E2E máy sạch (B-VM) — mở từ đầu, đang là ngoại lệ ghi nhận khi phát stable |
| 8.4 | Kiểm dây nguồn PCIe **cả hai** card máy B: WHEA ghi ba lỗi ở *PCI Express Root Port* và mất cả hai card cùng lúc |

## 9. Đang chạy ngay lúc chụp bảng này

Lượt diễn tập D1, phiên `session-dd80eaf3` trong `D:\LTTSTUDIOSAPP-d1-khoi-phuc`
(nhánh `phien/d1-khoi-phuc`, từ `main 9af53af2`), LTTCODE 0.2.6, model ltt-3.8, agent con ltt-3.5.

- Lượt 7 · 129 bước · 37 tok/s · 0 thẻ xin duyệt · 11 lỗi công cụ.
- Chặng 1 xong; chặng 2–3 đang làm; chặng 4–5 chưa.
- Bảy lần gián đoạn tới giờ **không lần nào do agent**: chủ dự án tắt nguồn (×2) · phiên khác
  restart PostgreSQL · 502 không retry (V-19) · hết credit tài khoản thử (V-22) · mất GPU máy B
  (V-23) · bị cắt giữa lượt khi khởi động lại.
- Ba tệp agent đã viết, chưa commit: `deploy/windows/dien_tap_khoi_phuc.ps1` (22 KB),
  `deploy/windows/dien_tap_kiem.py`, `tests/test_2200_dien_tap_khoi_phuc.py`.

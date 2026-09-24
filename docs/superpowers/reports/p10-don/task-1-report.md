# Task 1 — `liveQuotes`: MỘT cửa báo giá cho CẢ đồ thị

Nợ §5 của `docs/superpowers/plans/2026-09-24-wf-v2-MASTER.md`. Lằn `p10-don`, nhánh
`phien/p10-don`.

## Nguồn

| | |
|---|---|
| Bệnh | `frontend/agent-canvas/src/CanvasShell.tsx:394` (bản cũ) — `page.nodes.map(quoteTool)`, một request **mỗi node**, effect chạy lại mỗi lần `page.nodes` đổi |
| Cửa cũ | `apps/agent/routes/workspace.py:165` `POST /agent/api/tools/{ten}/quote` → `credit_for(...) * fanout * (1 + max_retry)` |
| Nguồn giá THẬT | `platform_core/workflow/bao_gia.py:76 _gia_node` — cái `bao_gia_do_thi` ghi vào `node["gia_tran"]`, và `platform_core/workflow/cau_noi.py:235` từ chối job khi `gia_that > gia_tran` |

🔴 **Tra trước khi viết mới.** `bao_gia_do_thi` đã có sẵn nhưng không dùng thẳng được cho
bản nháp đang gõ: nó **ném cho cả đồ thị** khi một node thiếu tham số (đúng, vì nó đứng ở
cổng publish) và nó **GHI** `gia_tran`/`bang_gia`/`he_so_lap` vào tài liệu nó nhận. Nên
thêm `bao_gia.bang_gia_song()` — **gọi thẳng `_gia_node`**, khác đúng hai điểm ấy, ⛔ không
một phép nhân giá nào viết lần hai.

🔴 **Cửa cũ lệch giá, không chỉ tốn request.** `fanout`/`max_retry` **không tồn tại ở bất kỳ
chỗ nào** trong `platform_core/workflow/` hay `apps/agent/` ngoài chính route đó
(`grep`) — Inspector đang hiển thị một con số mà nền tảng không giữ tiền theo.

## Đỏ trước → xanh sau

```
vitest  tests/BaoGiaMotCua.test.tsx
  ĐỎ   AssertionError: expected 12 to be 1   (12 node = 12 request)
  XANH Test Files 1 passed · Tests 2 passed

pytest tests/test_3520_wf_bao_gia_mot_cua.py -q -p no:randomly
  ĐỎ   10 failed, 1 warning in 11.94s
  XANH 10 passed, 1 warning in 9.48s
```

⛔ **Debounce không phải bản vá.** `setTimeout(...,450)` đã có sẵn từ trước bản này; nó giảm
**tần suất** bung, không giảm **độ lớn** một lần bung. Bài vitest đo đúng độ lớn ấy.

## Số request THẬT — trình duyệt, cổng 8199 (⛔ không đụng 8100)

`tools/agent_browser_server.py` + Playwright MCP, `agent-a@example.com`, CSDL scratchpad.
Cùng một đồ thị **12 node** `image.generate`, cùng một thao tác.

| | bundle `main-Dz1BRE6L.js` (TRƯỚC) | bundle `main-DhDF-1uI.js` (SAU) |
|---|---|---|
| Nạp trang | **12** request `/tools/image.generate/quote` | **1** request `/v3/workflows/{id}/bao-gia` |
| Gõ 12 ký tự vào ô `prompt` | **+12** | **+1** |
| Tổng một phiên | **24** | **2** |

⭐ Hai con số đo trên **cùng máy chủ, cùng CSDL, cùng đồ thị** — chỉ đổi bundle (lùi hai tệp
nguồn về `HEAD`, `vite build`, đo, rồi khôi phục và dựng lại).

**Đối chứng giá sống**: đổi `count` 1 → 4 trong Inspector ⇒ ô giá đổi **3 → 12 credit**. Không
có vế này thì "1 request" cũng đúng với một cửa trả rỗng.

**Console / mạng**: 0 error, 0 warning, 0 request hỏng (mọi lượt 200).
(Hai `[ERROR] … about:blank … Content Security Policy` trong lượt đo bản CŨ là của chính lệnh
`fetch('about:blank')` tôi gõ để ép flush console, không phải của trang.)

## Thay đổi

- `platform_core/workflow/bao_gia.py` — `BangGiaSong` + `bang_gia_song()`.
- `apps/agent/routes/bao_gia_v3.py` (mới) + đăng ký ở `routes/__init__.py`.
- `frontend/agent-canvas/src/workflowApi.ts` — `quoteTool` → `baoGiaDoThi`.
- `frontend/agent-canvas/src/CanvasShell.tsx` — một cửa, cùng debounce 450 ms.
- `tests/test_969_agent_draft_v3.py` — sổ route v3: **15 → 16**.

## Bộ test đã chạy

| Phép | Kết quả |
|---|---|
| `core:wf_soan` (75 tệp) + 5 bánh cóc canvas, `-n 7` | **1392 xanh, 45 skip, 2 đỏ** (cả hai ĐỎ SẴN, xem dưới) |
| `npm test` (agent-canvas) | **134 xanh / 10 tệp** |
| `npm run build` (typecheck + vite) | xanh, bundle dựng lại |

## ⚠️ Chưa làm được / khai ra

1. **Hai bài đỏ SẴN trên nhánh, không thuộc lằn này** — chứng minh bằng `git show HEAD`:
   - `test_970::test_trinh_soan_CO_dung_duong_chay_v3` đòi `CanvasShell` gọi `loadRunV3`;
     `git show HEAD:…/CanvasShell.tsx | grep -c loadRunV3` = **0** (lằn P9 đã đổi sang SSE
     `theoDoiRunV3`). Diff của tôi không chạm vùng đó.
   - `test_1757::test_node_loi_chua_publish_duoc_thi_bao_ra_chu_khong_giau` đỏ vì palette có
     thêm `trigger.piece.google_sheets.new_spreadsheet` — lằn connector, không phải tôi.
2. **Cửa `/agent/api/tools/{ten}/quote` VẪN MỞ** nhưng nay **không ai gọi từ GUI**. Nó là chỗ
   tính giá thứ hai và **lệch** (nhân `fanout × (1+max_retry)`). Đóng nó là một quyết định
   riêng (khuôn `test_2934`), không nằm trong nợ §5 ⇒ **để lại, khai ở đây**.
3. **Phạm vi cửa mới**: trả `gia_tran` của **MỘT lượt chạy** từng node — đúng thứ Inspector
   hiện. Nó **không** nhân `he_so_lap` của `foreach`; tổng của cả run vẫn là việc của
   `/publish` (`credit_max`). Có một bài khẳng định điều đó.
4. **Một node lõi gõ dở (`core.foreach` thiếu `items`) làm CẢ bảng giá trống**, vì
   `bien_dich.cau_truc` ném ở node đầu tiên sai — `nghiem=False` chỉ tha hình dạng *biểu
   thức*, không tha *thiếu tham số bắt buộc*. Cửa trả `loi_do_thi` và GUI xoá bảng giá thay
   vì hiện số cũ. Khoan dung theo từng node cho node lõi là việc của `cau_truc`, ngoài lằn này.

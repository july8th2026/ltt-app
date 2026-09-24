# P6 · Task 5 — Chốt tên action bằng `xuat_catalog` (§11.6)

**Kết quả: ĐẠT.** `node connector_runner/src/xuat_catalog.js --liet-ke` chạy
trên đúng các bản đã ghim. Spec §11.6 đã được **ghi đè bằng danh sách đã xác
minh** (chính spec yêu cầu điều đó), và bảng đối chiếu đầy đủ nằm trong
`connector_runner/allowlist.json → doi_chieu_spec_11_6` để nó **đọc được trong
diff**.

## Con số

**8 trong 13** tên mà spec đoán **không tồn tại** ở bản đã ghim.

| Đoán | Thật |
|---|---|
| `slack.send_message_to_a_channel` | không có → `send_channel_message` |
| `slack.upload_file` | không có (`uploadFile`; prop `FILE`) |
| `github.create_issue` | không có → `github_create_issue` |
| `github.create_comment_on_issue` | không có → `createCommentOnAIssue` |
| `google-sheets.get_rows` / `clear_row` | không có (`get-many-rows`, `clear-rows`) |
| `google-sheets` trigger `new_row` | **không tồn tại loại ấy** — xem dưới |
| `google-sheets.find_rows`/`insert_row`/`update_row`, `slack.send_direct_message`, `telegram.send_text_message` | **có** |

## Hai điều bảng cũ không thể nói, và chỉ `xuat_catalog` nói được

1. **`insert_row` / `update_row` có thật nhưng bị LOẠI.** Tham số bắt buộc
   `values` kiểu `DYNAMIC` (form sinh lúc chạy) không ánh xạ được sang từ vựng
   `luoc_do`. Luật của `xuat_catalog`: prop không ánh xạ được thì **bỏ**; nếu
   nó **bắt buộc** thì **bỏ cả action**. ⛔ Bỏ im lặng một tham số bắt buộc là
   dựng một form thiếu ô mà khách không biết.
2. 🔴 **Không có trigger POLLING nào về dòng mới.**
   `google-sheets-new-or-updated-row` là `WEBHOOK`, và trigger WEBHOOK của
   piece **ngoài phạm vi** (§11.4). POLLING duy nhất: `new-spreadsheet`,
   `new-worksheet`. `slack` 14/14 APP_WEBHOOK, `github` 14/14 WEBHOOK,
   `telegram` 1/1 WEBHOOK. ⇒ *"trigger poll Sheets"* của FLOW D (§18.5)
   **không thực hiện được** với tập piece này.

## Phép kiểm tĩnh đi kèm

`xuat_catalog` loại action dùng `createWaitpoint` / `run.pause` bằng cách đọc
**mã nguồn hàm `run`** — runner ta không chạy engine Activepieces nên những
action ấy sẽ treo im lặng. Lưới thứ hai: `ctx.run.pause` **ném** lúc chạy (đo
được trong diễn tập: `waitpoint_khong_ho_tro`).

`catalog.json` hiện có **7 node** (6 action + 1 trigger POLLING), và
`test_3503` chốt cơ học rằng nó khớp `allowlist.json` **và** `package-lock.json`.

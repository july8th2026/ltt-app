# P5c / Task 4 — Nối `Authorization` của `core.http` vào kho credential

**Lý do node bị khoá, nay đã hết.** Token nằm trong `params` ⇒ trong
`workflow_version` ⇒ trong mọi bản nhân bản/xuất. Nay `core.http` đọc bí mật từ
kho, **chỉ trong tiến trình job** (spec §9.4).

**Đã làm.**

- `_credential(db, run, node)`: `kiem_ref` (đúng chủ, còn hiệu lực, đúng kiểu)
  rồi `lay_de_dung`. Kiểu nhận: `api_key | bearer | basic`. ⛔ **Không
  `oauth2`** — một access token Google đi vào một URL người soạn tự gõ là đúng
  hình dạng của một lần rò token sang bên thứ ba; `oauth2` là việc của
  connector, nơi **đích đã cố định**.
- Credential **ghi đè** header người soạn tự gõ (không `setdefault`): nếu hai
  thứ cùng khai `Authorization` thì thứ đi ra dây phải là thứ nền tảng quản lý
  được và **thu hồi được**.
- Che **hai lớp**, và cả hai đều cần: theo **TÊN** (`HEADER_PHAI_CHE`: bắt được
  `Set-Cookie` của đích mà ta không hề gửi) và theo **GIÁ TRỊ** (bắt được bí
  mật dội lại ở một header mang tên khác — đích chọn được tên đó). `error`
  cũng bị che trước khi vào `node_run_snapshot`, bảng **CHỈ THÊM**: lọt vào đó
  là lọt **vĩnh viễn**.
- Ref đã thu hồi ⇒ `FAILED credential_bi_thu_hoi` và **chưa gửi gì** (máy chủ
  giả đếm 0 request).

🔴 **Một lỗ có sẵn, đo được.** `chay_http` gọi `ngon_ngu.tinh` lên **cả** chuỗi,
nên một URL viết thẳng — `"https://vi.du/api"` — ném `invalid syntax`. Tức node
chỉ chạy được khi mọi tham số là biểu thức, ngược với §6. Lớp đúng là
`noi_suy.noi_suy`: `{{ }}` **đánh dấu** phần biểu thức trong một chuỗi thường.
Đã sửa. Lỗ này chưa từng lộ vì `test_2912` gọi thẳng `thuc_thi`, bỏ qua
`chay_http`.

```
ĐỎ    13 failed, 1 passed in 67.90s
XANH  14 passed in 90.62s     tests/test_2921_credential_gan_node.py
```

**Chưa làm được.** Che bí mật ở `job_events.redact_details` cho **mọi** node
(spec §9.4, "5 đường lỗi") — bản này che ở `core.http`, chưa phải ở tầng
chung.

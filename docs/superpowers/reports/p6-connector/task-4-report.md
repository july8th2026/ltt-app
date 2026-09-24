# P6 · Task 4 — Store + poll + `connector.youtube.upload`

## Store (spec §11.4) — ĐẠT

Bảng `connector_store(owner_id, pham_vi, khoa, gia_tri, updated_at)`, migration
`7f2b91d4c8ae`, khoá duy nhất `(owner_id, pham_vi, khoa)`.
`pham_vi` là một **ĐƯỜNG** (`trigger:<id>` / `run:<id>`), ⛔ không phải id
trần — đúng bài học đã lặp ba lần ở phase 4 (`wakeup`, `node_run`,
`dedupe_key`). Trần 200 khoá / 256 KiB mỗi giá trị, chạm trần ⇒ **ném**, ⛔
không bỏ ghi im lặng (một `put` bị nuốt = con trỏ poll không bao giờ tiến).
Đã khai ở `public_api/governance.py` (OPERATIONAL, hạn theo **vòng đời
trigger**, ⛔ không theo đồng hồ).

## Poll (`PIECE_POLL`) — ĐẠT, và **sửa hai lỗ trên đường đi**

`poll_connector.py`: chu kỳ tối thiểu **300 s** từ chối **lúc tạo**; trần 100
bản ghi một lượt; hai lớp khử trùng (store của piece **và** khoá
`poll:<trigger>:<ban_ghi>`). `ban_trigger.ban_mot` nay hỏi mô-đun loại *"anh
có tự bắn không"* thay vì mọc nhánh `if kind ==` — một mốc lịch ra **N** run
là một **hình dạng** khác, không phải một tham số khác.

🔴 **Lỗ 1 — hạn mức run đồng thời làm hỏng cả lượt poll.** Đo: 125 bản ghi ⇒
`QuaHanMuc: toi da 5 run dong thoi` ném ra ngoài ⇒ `ban_den_han` đếm là **một
lần lỗi của trigger** ⇒ **5 lượt poll đông là trigger TỰ TẮT**. Nay `QuaHanMuc`
là một điểm **dừng**: tạo được bao nhiêu thì tạo.

🔴 **Lỗ 2 — thứ tự áp `store_ops` làm MẤT bản ghi của khách.** Bản đầu áp
`store_ops` (*"tôi đã thấy r1, r2"*) **trước** khi tạo run. Dừng giữa chừng ⇒
store nói "đã thấy" cho những bản ghi **chưa bao giờ** có run, và chúng không
bao giờ quay lại. Nay `store_ops` chỉ áp khi đã xử **trọn** danh sách.

🔴 **Lỗ 3 (ngoài phạm vi poll) — `ban_trigger._moc_ban` so sánh naive với
aware.** `next_fire_at` khai `DateTime(timezone=True)`; PostgreSQL trả
**aware**, mọi thứ ta tính là **naive** ⇒ `TypeError` ở **mọi** loại trigger có
lịch, chỉ khi một tiến trình **khác** đọc hàng lên. Không lộ trên SQLite, không
lộ trong cùng phiên đã ghi. Đã bịt bằng `_tho()`.

## `connector.youtube.upload` — mã ĐÃ VIẾT, lượt thật **CHƯA CHẠY**

Piece YouTube của Activepieces **không có** action upload (tra lại 24/09:
`download-caption, get-channel, get-video, list-captions, list-comments,
list-playlist-items, list-playlists, search`) ⇒ đây là ca *"dùng lại trước, tự
viết sau"* trả lời **có được tự viết**. `side_effect = irreversible`: URL phiên
resumable **lưu trước khi gửi byte đầu**, nên thử lại **nối tiếp**; 404/410/5xx
⇒ `ket_qua_mo_ho`, ⛔ không tự mở phiên mới; `privacy` mặc định `private`;
`publish_at` + `public` bị **từ chối** (luật YouTube: nó bị bỏ qua im lặng).

⛔ **Chưa upload thật** — xem `task-6-report.md`, mục chặn.

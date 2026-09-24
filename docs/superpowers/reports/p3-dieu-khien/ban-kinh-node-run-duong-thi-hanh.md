# Bán kính ảnh hưởng — khoá `node_run` theo ĐƯỜNG THI HÀNH

Đo ngày 24/09 trên cây `D:\LTTSTUDIOSAPP-p3`. ⛔ Chưa sửa một dòng mã nào; đây
là **bằng chứng để quyết định**, không phải một kế hoạch đã thi hành.

Câu hỏi: đổi ý nghĩa cột `node_id` của `node_run` / `node_run_snapshot` /
`node_run_waitpoint` từ *"id node trần"* (`"a"`) sang *"đường thi hành"*
(`"f1:0/a"`, đúng `danh_thuc.duong_thi_hanh` của Task 1) thì **cái gì vỡ**?

## 0. Ba cột, và tin tốt về lược đồ

| Bảng | Dòng | Cột | Vai |
|---|---|---|---|
| `node_run` | `models.py:1311` | `node_id` `String(64)` | **một phần khoá chính** |
| `node_run_snapshot` | `models.py:1337` | `node_id` `String(64)` | cột thường |
| `node_run_waitpoint` | `models.py:1441` | `node_id` `String(64)` | **một phần khoá chính** |

⭐ Cả ba **cùng bề rộng** với `Wakeup.node_run_id`, nên cách của Task 1 dùng lại
được **y nguyên**: giữ `String(64)`, **băm** khi đường thi hành tràn
(`danh_thuc.TRAN_NODE_RUN_ID`, tiền tố `#` không nằm trong tập id hợp lệ).
⇒ **KHÔNG CẦN MIGRATION.** Không phát minh cách thứ hai.

## 1. Tổng số điểm chạm — và vì sao con số thô gây hiểu lầm

Kiểm kê thô: **≈38 tệp / ≈184 điểm gọi**. Nhưng con số đó là *"mọi nơi truyền
một node_id"*, không phải *"mọi nơi phải sửa"*.

🔑 **Nếu tham số mới có mặc định = id trần thì mọi điểm gọi hiện tại giữ nguyên
nghĩa.** Đồ thị không có `foreach` sinh ra **đúng** những khoá như hôm nay.
⇒ ~120 khẳng định trong `tests/**` (`filter_by(node_id="a")`,
`anh_chup_hien_tai(db, run.id, "a")`) **không vỡ**, không phải sửa.

## 2. Điểm nghẽn — sửa một chỗ, che nhiều chỗ

| # | Chỗ | Che được |
|---|---|---|
| 1 | `thi_hanh.py:42` `ghi_chuyen` · `:92` `anh_chup_hien_tai` | **mọi** lượt đọc/ghi ba bảng (~53 điểm trong `platform_core`) |
| 2 | `may_trang_thai.py:89` `trang_thai_node` · `:95` `chuyen_node` | cổng nghiệp vụ DUY NHẤT gọi `ghi_chuyen` (trừ test) |
| 3 | `cho_doi.py:42/52/59` | bọc trọn `node_run_waitpoint` |
| 4 | `apps/agent/routes/runs_v3.py:151` `_nodes_json` | **điểm DUY NHẤT** phơi `node_id` ra client |

## 3. Chỗ THẬT SỰ vỡ, và mỗi chỗ vỡ ra sao

1. **`runs_v3.py:151-179` `_nodes_json`** — duyệt `graph["nodes"]` rồi tra bằng
   **id trần**. Với thân `foreach`, ảnh chụp nằm dưới `f:0/x` ⇒ mọi node thân
   báo `PENDING` **mãi mãi** trên giao diện.
   ⇒ Sửa tại chỗ: tra id trần trước, không có thì **gộp** các đường thi hành của
   node đó. Giữ nguyên khoá `node_id` trong JSON ⇒ **frontend không phải sửa**.
2. **`frontend/agent-canvas/src/CanvasShell.tsx:557, :595`** — so
   `item.node_id === node.id` để tô màu node/cạnh. **Không vỡ** nếu (1) giữ
   `node_id` là id trần như trên. Đây là lý do (1) phải làm theo cách ấy.
3. **`dong_co.py:92`** — `tt = {n["id"]: trang_thai_node(...) for n in g["nodes"]}`.
   Dict khoá theo id trần. **Không vỡ** nếu thân `foreach` **không** đi qua vòng
   lan truyền cấp run (xem §4).
4. **`moi_truong.py:51` `anh_chup_nodes`** — trả `{id: ...}`, tra bằng id trần.
   Cần một tham số `vong` để node thân đọc đúng vòng đang chạy.
5. **`nut_loi/vong_lap.py:75-77` `_chot`** — hiện **cố ý** ghi đè mỗi vòng.
   Đây chính là khiếm khuyết cần sửa; nó vỡ nếu đổi nửa vời.
6. 🔴 **`cau_noi.py:72-80` `_khoa_idem` — CHỖ NGUY HIỂM NHẤT, và nó KHÔNG hiện
   ra trong bảng kiểm kê.**

   ```python
   if cc.side_effect == "none" or not cc.idempotency_fields:
       goc = [run.id, node["id"], lan]
   else:
       goc = [run.id, node["id"], {k: params.get(k) for k in cc.idempotency_fields}]
   ```

   Cả hai nhánh đều **thiếu chỉ số vòng lặp**. Một node thân có tham số không
   phụ thuộc `loop.item` sẽ sinh **cùng một `dedupe_key`** ở mọi vòng, và
   `jobs.submit` trả lại **job của vòng 1**. Kết quả: `foreach` 5 phần tử chạy
   **một** job, 4 vòng còn lại nhận lại kết quả của vòng 1 — **im lặng**, không
   lỗi, không cảnh báo.

   ⭐ Đây **đúng hạng lỗi Task 1 vừa sửa cho `wakeup`**, ở một bảng thứ ba mà
   plan chưa ai nhìn tới. `duong` phải vào `goc` của **cả hai** nhánh.
7. **`dong_co.py:235, :353`** — quét `g["nodes"]` để SKIP/CANCEL. Bỏ sót các
   đường thi hành con ⇒ một run bị huỷ để lại hàng `node_run` của thân ở trạng
   thái không kết thúc. Sửa: quét theo `run_id`, không theo `graph`.

## 4. Chỗ KHÔNG vỡ — đã kiểm, không đoán

- `may_trang_thai.py:161` `tong_chi_phi_hop_le` gom theo **`run_id`**, không
  theo `node_id` ⇒ chi phí từng vòng tự cộng đúng. **Không vỡ, và có lợi.**
- `server/api/workflows.py:276` chỉ đọc `NodeRunSnapshot.id` theo `run_id`.
- `platform_core/public_api/governance.py:535,554,565` chỉ là metadata.
- `apps/agent/routes/runs_v3.py:216` `node_id` của `WorkflowEvent` — **bảng khác**.
- **Không có** route nào nhận `node_id` từ client rồi tra ba bảng này (đã đọc
  `runs_v3.py` hết; `RunScope` chỉ sống ở frontend).
- Migration cũ (`20260908_1200`, `20260908_1300`) chỉ khai cột; không có
  `CHECK`/`FOREIGN KEY` nào ràng `node_id` vào `graph`.

## 5. Ước lượng công việc — và vì sao nó VỪA một làn

Đường đi nhỏ nhất **không** đụng vòng lan truyền của động cơ: để `core.foreach`
tiếp tục **tự lái thân nó**, nhưng lái **bền** thay vì đồng bộ — mỗi vòng nộp
job qua `cau_noi.nop_job(..., duong="f:i/x")`, node `foreach` vào `WAITING`,
wakeup của job đưa run về, `vong_lap` đọc trạng thái **path-keyed** để biết vòng
nào xong. `parallelism` rơi ra tự nhiên (nộp tối đa P job một lượt).

⇒ `_lan_truyen` **không cần biết** node thân tồn tại. Điểm vỡ (3) biến mất.

Tệp phải sửa: `thi_hanh.py` · `may_trang_thai.py` · `cho_doi.py` · `cau_noi.py`
· `moi_truong.py` · `nut_loi/vong_lap.py` · `dong_co.py` · `bien_dich.py` (bỏ
`than_foreach_co_node_job`) · `runs_v3.py` = **9 tệp**, tất cả có mặc định
tương thích ngược.

## 6. Kết luận

**Bán kính VỪA một làn** — với ba điều kiện, và cả ba đều đo được:

1. tham số mới **mặc định là id trần** ⇒ ~120 khẳng định test và mọi đồ thị
   không-foreach không đổi;
2. `runs_v3._nodes_json` giữ `node_id` **trần** trong JSON ⇒ frontend không sửa;
3. `_khoa_idem` phải mang `duong` — ⛔ bỏ sót chỗ này thì `foreach` chạy một
   job cho mọi vòng, **im lặng**, và mọi phép kiểm khác vẫn xanh.

⚠️ Điều tôi **chưa** đo: hiệu năng của `_lan_truyen`/`_nodes_json` khi một
   `foreach` 1000 phần tử sinh 1000 hàng `node_run`. `M1` nói chi phí phải là
   `O(node đổi)`; con số ấy cần một phép đo riêng trước khi mở `max_items` lớn.

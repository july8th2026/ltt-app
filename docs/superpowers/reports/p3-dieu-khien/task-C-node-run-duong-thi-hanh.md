# P3 · Việc C — khoá `node_run` theo ĐƯỜNG THI HÀNH (FLOW C đóng)

## Bước 1 đã đo trước khi sửa

`ban-kinh-node-run-duong-thi-hanh.md` — bán kính đo được **trước** khi viết một
dòng mã nào, theo yêu cầu điều phối. Kết luận: **vừa một làn**, và ba điều kiện
đều đã giữ được:

1. tham số `vong` **mặc định rỗng** ⇒ khoá = `node_id` trần ⇒ ~120 khẳng định
   test và mọi đồ thị không-foreach **không đổi một bit**;
2. `runs_v3._nodes_json` giữ `node_id` **trần** trong JSON ⇒ frontend không sửa;
3. `_khoa_idem` mang `duong`.

## Đỏ trước — trên PostgreSQL THẬT, bằng FLOW C thật

```
$ pytest -v tests/test_1787_wf_flow_acf_pg.py     # CSDL scratch that
test_FLOW_C_than_co_node_JOB_chay_du_moi_vong                 FAILED
test_FLOW_C_moi_vong_MOT_hang_node_run_rieng                  FAILED
2 failed, 11 passed in 12.95s

E  LoiBienDich: than_foreach_co_node_job: than cua 'f' co node khong chay
   inline: ['x']. Than co node job phai di qua run con — chua ho tro o ban nay.
```

## Xanh sau

```
$ pytest -v tests/test_1787_wf_flow_acf_pg.py
13 passed in 13.51s
$ …chay_nang.py --phien p3 -- pytest <36 tep wf> -q -n 6
496 passed, 6 warnings in 58.71s
$ ruff check platform_core/workflow/ apps/agent/routes/runs_v3.py tests/test_178*.py
All checks passed!
```

## ⭐ KHÔNG MIGRATION — dùng lại nguyên Task 1

`thi_hanh.khoa_node(node_id, vong)` gọi thẳng `danh_thuc.duong_thi_hanh`: cùng
hình dạng khoá (`f:0/x`), cùng phép **băm** khi vượt 64 ký tự. Ba cột `node_id`
(`node_run` `models.py:1311`, `node_run_snapshot` `:1337`, `node_run_waitpoint`
`:1441`) đều `String(64)` y như `Wakeup.node_run_id` ⇒ vừa khít.
⛔ Không viết một bộ sinh khoá thứ hai.

## 🔴 Chỗ nguy hiểm nhất — và nó không nằm trong bảng kiểm kê

`cau_noi._khoa_idem` thiếu chỉ số vòng ở **cả hai** nhánh. Một node thân có tham
số không phụ thuộc `loop.item` sinh **cùng một `dedupe_key`** ở mọi vòng, và
`jobs.submit` trả lại **job của vòng 1**: `foreach` 3 phần tử chạy **một** job,
hai vòng còn lại nhận lại kết quả cũ. Không lỗi, không cảnh báo.

⇒ `duong` **THAY** `node["id"]` trong `goc` (không phải thêm vào): với `vong=()`
thì `duong == node["id"]`, nên khoá của mọi job đang chạy trên production
**không đổi**. Phép kiểm ghim `len({j.dedupe_key}) == 3`.

## Hai chỗ vỡ chỉ lộ ra khi CHẠY THẬT

1. **Thân bị chạy HAI lần.** Node thân vẫn nằm trong vòng lan truyền cấp run ⇒
   `_pha_inline` chạy nó **thêm một lần nữa** ở khoá id trần, ngoài mọi vòng lặp
   ⇒ `bieu_thuc_loi: ten 'loop' khong doc duoc`. Vá: `dong_co._than_foreach`
   loại thân khỏi `tt` — chúng do `core.foreach` lái, không do lan truyền.
2. **`foreach_end` thành node mồ côi.** Loại thân đi thì cạnh `x → fe` biến mất,
   `fe` không còn cạnh vào nào và được lan truyền cho READY **ngay lượt đầu**.
   Vá: `fe` **ở lại** `tt` (node sau nó phải đọc được trạng thái) nhưng lan
   truyền không chuyển nó — `core.foreach` chốt nó: SUCCEEDED khi vòng xong,
   SKIPPED khi vòng hỏng (`_bo_dong`).

## Vòng lặp nay chạy BỀN

`_lai_vong` luỹ đẳng: mọi trạng thái nằm trong `foreach_vong`/`foreach_muc`/
`node_run`, không trong biến cục bộ — vì một thân có node job **sống qua nhiều
lượt động cơ**. `tiep_vong` là cửa RESUME (job xong ⇒ wakeup ⇒ đẩy vòng tiếp);
thiếu nó, vòng lặp đứng `WAITING` tới hạn 20 giờ. `parallelism` rơi ra tự nhiên:
tối đa `P` chỉ số có job đang chờ cùng lúc.

Phần tử hỏng ghi vào `ForeachMuc.ket_qua` (`_loi` cho `collect`, `_bo` cho
`skip`) — **trong CSDL**, vì giữa hai lượt động cơ chỉ còn bảng.

## Giao diện không phải sửa

`runs_v3._gop_than_foreach` gộp `f:0/x`, `f:1/x`… về đúng `node_id` **trần**:
còn lượt chưa xong ⇒ `RUNNING`; có lượt hỏng ⇒ `FAILED` (⛔ không giấu);
`cost_credit` cộng mọi lượt; `attempt` là **số lượt** (nói ra, vì dễ đọc nhầm
thành số lần thử). `CanvasShell.tsx:557,595` so `item.node_id === node.id` —
vẫn so được.

`thi_hanh.anh_chup_theo_khoa` cho bên đã cầm khoá trong tay; `anh_chup_hien_tai`
vẫn **từ chối** một chuỗi có `:`/`/`, vì nhận cả hai kiểu ở một cửa là cách để
một khoá dựng sai đi lọt.

## Chưa làm được

- ⚠️ **Đường thi hành bị BĂM không gộp được trên giao diện.** `foreach` lồng sâu
  với id dài ⇒ khoá là `#<sha>` ⇒ không khớp hậu tố `/<node_id>` ⇒ node hiện
  `PENDING` dù đang chạy. Khoảng trống ĐÃ BIẾT, chưa vá, đã ghi trong docstring.
- **Hiệu năng chưa đo.** `foreach` 1000 phần tử sinh 1000 hàng `node_run`, và
  `_lan_truyen`/`_gop_than_foreach` quét chúng. `M1` đòi `O(node đổi)` — con số
  ấy cần một phép đo riêng **trước khi** mở `max_items` lớn.
- `foreach` **lồng nhau** chạy thật chưa có phép kiểm (khoá hỗ trợ sẵn nhiều
  tầng; `he_so_lap` có kiểm, đường chạy thì chưa).
- `huy_run` nay quét theo hàng `node_run` (`_moi_khoa_node`) nên dọn cả thân —
  nhưng ca "huỷ giữa lúc một job của thân đang chạy" chưa có phép kiểm riêng.

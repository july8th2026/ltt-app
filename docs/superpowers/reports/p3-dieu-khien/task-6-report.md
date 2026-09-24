# P3 · Task 6 — `set` · `transform` · `filter` · `aggregate` · `output`

## Nguồn đã tra

- **Mã của P2 trước hết.** `ham_bieu_thuc.BANG_HAM` (49 hàm, §6.3 đóng),
  `bien_vars.gop_vars` + `kiem_ghi_xung_dot` (§6.5), `chinh_sach.moi_truong_wf`.
  ⇒ Kết luận âm: **không cần thư viện nào và không cần hàm mới nào** — bốn node
  này là dây nối, không phải logic mới.
- Spec §4.5 bảng DÙNG LẠI: `core.set/transform/filter/aggregate/output` đều
  `BUILD_NATIVE`, và §6.5 cho `vars`.
- ⚠️ Phát hiện khi đọc mã: `bien_vars.kiem_ghi_xung_dot` **đã có và đã được
  test ở P2 nhưng CHƯA AI GỌI**. Một cổng không có người gọi là một cổng mở —
  cùng hạng lỗi với *"xoá `canvas_to_plan` hoá ra là cổng an ninh"*.

## Đỏ trước

```
$ python -m pytest tests/test_1785_wf_nut_du_lieu.py -q
19 failed, 3 passed in 2.64s
```

## Xanh sau

```
$ python -m pytest tests/test_1785_wf_nut_du_lieu.py -q
22 passed in 4.19s
$ …chay_nang.py --phien p3 -- pytest <20 tep wf> -q -n 6
332 passed, 6 warnings in 31.14s
```

## Bánh cóc CẮN THẬT (tiêm lỗi rồi đo)

`test_banh_coc_aggregate_khong_tu_viet_phep` đòi **mọi** phép của `PHEP_GOP` là
một khoá của `BANG_HAM` §6.3.

```
# them "trung_binh" vao PHEP_GOP
$ pytest …::test_banh_coc_aggregate_khong_tu_viet_phep -q
1 failed in 0.87s
# phuc hoi
1 passed in 0.72s
```

Đối chứng nằm trong chính phép (`len(PHEP_GOP) >= 8`): một `PHEP_GOP` rỗng thì
phép hiệu số tập cũng rỗng và nó xanh mà không đo gì.

Bánh cóc thứ hai, `test_banh_coc_tham_so_bieu_thuc_deu_di_qua_cong_to_tien`,
đọc AST `bien_dich.py` và đòi `_tham_chieu_node_loi` gọi `trich_tham_chieu` —
chặn ca Task 5 vừa đo (tham số biểu thức **trần** đi lọt cổng tổ tiên) tái phát.
Nó nêu tên hàm, nên đổi tên hàm làm nó đỏ chứ không làm nó im.

## Việc đã làm

- `nut_loi/du_lieu.py`: `core.set` · `core.transform` (chuyển từ `vong_lap.py`
  về đúng nhà) · `core.filter` · `core.aggregate` · `core.output`.
  `core.filter` dùng lại namespace `loop` cho phần tử — ⛔ không đặt một
  namespace `item` thứ hai cho cùng ý nghĩa.
- `bien_dich.KIEU_BANG_BIEU_THUC`: `core.set.bien` là `{tên: biểu thức}`, và
  **những biểu thức đó cũng đi qua cổng tổ tiên §6.2**. Tên biến kiểm bằng
  `bien_vars._thay_duoc` — khoá `_` là VÔ HÌNH với §6, nên nhận nó rồi lặng lẽ
  không thấy nó là cách tệ nhất.
- `bien_dich._kiem_ghi_bien` (gọi `kiem_ghi_xung_dot` — **nối dây cho một cổng
  chưa ai gọi**) và `_kiem_ten_output` (`trung_ten_output`).
- `ket_qua_run.py` (mới, đã khai `core:wf_dong_co`): kết quả run **DẪN XUẤT** từ
  ảnh chụp các node `core.output`. ⛔ Không thêm cột `output_data` trên
  `workflow_run`: một cột thứ hai giữ cùng sự thật là một chỗ để hai câu trả lời
  lệch nhau sau một lần chạy lại.

## Chưa làm được

- `graph.outputs` cấp workflow (spec §4.1 `outputs[].from`) chưa nối vào
  `core.output` — tầng API vẫn chưa đọc `ket_qua_run.doc`.
- `core.aggregate` mới mở 9 phép; `join`/`sort_by` cần tham số thứ hai nên để
  lại (`sort_by` cần khoá, `join` cần dấu ngăn) — **chưa đo** cách khai chúng.
- `core.filter` gọi `ngon_ngu.tinh` một lần cho MỖI phần tử: với mảng 10 000
  phần tử đó là 10 000 lần phân tích cú pháp. Chưa đo, chưa tối ưu, chưa có
  chặn trên riêng (`chinh_sach.do_gioi_han` chặn theo từng lần tính).
- Chưa chạy trên PostgreSQL thật (Task 8).

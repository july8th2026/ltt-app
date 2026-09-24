# P3 · Task 4 — `core.if` · `core.switch` · `core.stop`

## Nguồn đã tra

- **Spec của ta trước, vì đây là đồ thị của ta.** §5.4 chốt hình dạng và nói rõ
  vì sao: *"Node `core.if` xuất nhánh `true`/`false`… Cạnh CONTROL mang
  `condition = "<tên nhánh>"`; chỉ cạnh khớp nhánh được kích hoạt. (Chốt `Q1`
  của ADR-WF-001 … **Một nơi viết biểu thức, một nơi hiện trên Canvas**.)"*
  ⇒ ⛔ Không có `condition` là biểu thức trên cạnh.
- `activepieces/activepieces@17e2ac0b` — router/branch của họ nằm trong
  `packages/pieces/community/…` và ràng vào runtime Node của họ; không port
  được và cũng không cần: quyết định ở đây là quy ước cạnh của **đồ thị ta**.
  Thứ đã PORT được từ họ là `shouldReleaseBarrier` (Task 5).
- Mã của chính ta: `dieu_khien.py` đã ghi con số — *"một job là một bút toán.
  Rẽ nhánh tạo một dòng trong sổ tiền, dù nó chỉ so sánh hai giá trị"* — và
  `may_trang_thai` đã có sẵn `RETRY_SCHEDULED`/`SKIPPED`. P2 đã có
  `ngon_ngu.tinh` + `chinh_sach.moi_truong_wf`. Không viết lại gì.

## Đỏ trước

```
$ python -m pytest tests/test_1783_wf_nut_dieu_huong.py -q
12 failed, 4 passed in 3.54s
```

⚠️ **Ba trong bốn phép "passed" lúc đỏ là xanh GIẢ** — chúng đòi publish từ chối
một node lõi sai, và lúc đó publish từ chối *mọi* `core.*`. Chúng chỉ có nghĩa
sau khi `core.*` biên dịch được; điều đó được nói ra ở đây thay vì đếm chúng là
đối chứng. Đối chứng thật là `test_doi_chung_do_thi_app_khong_doi`.

## Xanh sau

```
$ python -m pytest tests/test_1783_wf_nut_dieu_huong.py -q
16 passed in 4.22s
$ …chay_nang.py --phien p3 -- pytest <16 tep wf> -q -n 6
250 passed, 6 warnings in 26.77s
```

## Một lỗi ĐO ĐƯỢC khi dựng, đáng ghi

Lượt xanh đầu vẫn đỏ với `cong_cu_khong_con: '.if'`. Nguyên nhân:
`NODE_CHUYEN["READY"]` **không có** `SUCCEEDED`, nên `chuyen_node` từ chối
**im lặng** (nó trả `False`, và `_pha_inline` không đọc giá trị trả về), node
đứng READY, rồi vòng nộp job gửi `core.if` vào registry công cụ — nơi
`type[4:]` biến nó thành `".if"`. Hai vá, cả hai có lý do riêng:

1. `may_trang_thai`: mở `READY → SUCCEEDED` — node inline chạy **trong** động cơ
   nên không đi qua `QUEUED`.
2. `dong_co`: vòng nộp job bỏ qua mọi node `thi_hanh != "job"` — fail-closed,
   để một node inline thiếu bộ thi hành ngã ở `_chay_mot_inline` với một mã lỗi
   rõ thay vì ngã ở registry với một tên công cụ vô nghĩa.

⚠️ Đây cũng là bằng chứng cho việc coordinator giao thêm (việc **B**): số cứng
`[4:]` trong `cau_noi.py` **sai im lặng**, đúng như đã báo.

## Hai phép kiểm của người khác phải sửa — và vì sao không phải là "dọn cho xanh"

- `test_954::test_lan_chuyen_bi_tu_choi_KHONG_doi_con_tro` dùng `READY →
  SUCCEEDED` làm ví dụ "nhảy cóc". Nó **hết là nhảy cóc**. Thay bằng đúng ca mà
  `chuyen_node` docstring vốn nói: *worker chậm chân quay lại tiến một node đã
  xong* (`SUCCEEDED → READY`), vẫn bị từ chối, con trỏ vẫn đứng yên.
- `test_1714::test_node_core_chua_bien_dich_duoc…` là **cái chuông** tác giả
  treo sẵn cho đúng hôm nay. Đã trả lời **một phần**: ba node rẽ đường không có
  thân, `loop.*` không tồn tại quanh chúng, luật tổ tiên §6.2 áp y nguyên.
  Chuông **vẫn treo cho `core.foreach`** — phép kiểm nay khẳng định
  `"core.foreach" not in nut_loi.tat_ca()` kèm câu *"Task 5 phải trả lời ở đây,
  không được chỉ xoá phép kiểm này"*.

## Việc đã làm

- `nut_loi/chay.py` (`KetQua`), `nut_loi/dieu_huong.py` (3 NodeDefinition +
  3 bộ thi hành), `nut_loi/__init__.py` (`dang_ky(nd, chay)` **từ chối lúc dựng**
  một node `inline` không có bộ thi hành; `bo_thi_hanh`).
- `moi_truong.py` (mới, khai `core:wf_dong_co`): cầu CSDL → §6.2 —
  `anh_chup_nodes`, `to_tien_cua`, `moi_truong_run(db, run, g, node_id)`.
  `vars` đi qua `bien_vars.gop_vars` với tổ tiên THẬT của node đang tính.
- `bien_dich`: `_node_loi` + `_kiem_tham_so_loi` (thiếu khoá · khoá lạ · enum
  ngoài tập — chặn ở **publish**); `cau_truc.cong_ra` đọc `NodeDefinition` cho
  node lõi.
- `dong_co`: `TRAN_BUOC_INLINE = 500` (§5.1), `_pha_inline` chạy liên tiếp
  **hai lần một vòng** (trước và sau vòng nộp job), `_kich_hoat` xét `condition`,
  `_dung_run` cho `core.stop` (SKIPPED chứ không CANCELLED — `_ket_run` đếm
  CANCELLED là "hỏng", và một nhánh không chạy thì không hỏng).

## Chưa làm được

- `settings.on_error ∈ {fail, route, continue}` và `skip_if` cấp node (§5.4) —
  chưa làm, không thuộc ba node này.
- `core.switch` so khớp bằng `str(giá trị)`; một nhánh tên `"1"` khớp cả số `1`.
  Đã cân nhắc là chấp nhận được (tên nhánh là chuỗi trên Canvas) nhưng **chưa đo**.
- `moi_truong.KHOA_NOI_BO` là một danh sách, tức một chỗ có thể quên. Chưa có
  bánh cóc nào đếm nó.
- Chưa chạy trên PostgreSQL thật (Task 8).

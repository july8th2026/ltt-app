# P2 Task 1 — Máy duyệt AST + chính sách

Cây `D:\LTTSTUDIOSAPP-p2`, nhánh `phien/p2-bieu-thuc`, nền `fb5c93e7`.

## Đã làm

- **Mới** `platform_core/workflow/chinh_sach.py` — máy duyệt AST (`kiem_cay`,
  `tinh_cay`, `ten_duoc_doc`) + `ChinhSach` (frozen dataclass): nút AST nào cho
  phép · kiểu hằng số · bảng toán tử nhị phân/một ngôi/so sánh/logic · bảng hàm ·
  có cho tham số có tên không · toán tử nào chặn chia 0 · **lớp lỗi** · **nguyên
  văn câu lỗi**. Máy chỉ biết đi trên cây; mọi lệnh cấm nằm trong bảng.
- **Sửa** `platform_core/workflow/bieu_thuc.py` — giữ nguyên API công khai
  (`LoiBieuThuc`, `kiem_bieu_thuc`, `tinh_bieu_thuc`, `tham_so_dung`), ruột gọi
  máy chung với `NGHIEM` — bản khai đầy đủ của ba điều cấm `timeout_expr`.
- **Chưa làm** (task sau): chính sách ĐẦY ĐỦ cho ngôn ngữ §6.

## Bằng chứng: hợp đồng `timeout_expr` KHÔNG ĐỔI

Không dùng "tôi refactor cẩn thận". Quy trình:

1. **Chụp cơ học TRƯỚC khi sửa**: 75 biểu thức × 3 cửa (`kiem_bieu_thuc`,
   `tinh_bieu_thuc`, `tham_so_dung`) = **225 phép**, ghi cả giá trị trả về lẫn
   **tên lớp ngoại lệ + nguyên văn câu lỗi** → `snapshot_cu.json`.
   Tập ca gồm mọi thứ bị cấm: gọi hàm (`__import__`, `open`, `len`, `abs`,
   lambda gọi ngay), tên ngoài `params`, thuộc tính `_`, comprehension, `**`,
   bitwise, `not`/`in`/`is`, walrus, f-string, list/tuple/dict/set, subscript,
   hằng str/bytes/None/Ellipsis, cú pháp sai, rỗng, chia 0, trị không phải số.
2. Refactor.
3. **Chạy lại cùng script** → `diff` với snapshot cũ: **0 dòng khác**. Byte-identical.
4. `tests/test_1761_wf_bieu_thuc_chinh_sach.py` sinh **từ chính snapshot đó**
   (`repr`, không gõ tay) → chạy trên **mã CŨ** (worktree tạm ở `fb5c93e7`, chưa
   có `chinh_sach.py`): **76 passed** (75 ca + bánh cóc đếm ca), 3 bài máy bị
   deselect; 3 bài đó chạy trên mã cũ thì **ĐỎ** (`ImportError`) — chúng là bài
   mới thật, không phải bài luôn xanh.
   Trên mã MỚI: **79 passed**.

## Bằng chứng tiêm lỗi (chính sách có được cưỡng chế thật không)

| Tiêm | Kết quả |
|---|---|
| Thêm `if isinstance(nut.op, ast.Pow): raise` vào `kiem_cay` (máy tự cấm, bỏ qua bảng) | `test_may_doc_CHINH_SACH...` **ĐỎ**, 78 bài khác xanh ⇒ bài đó đo đúng thứ nó nói |
| Nới `NGHIEM`: `_HAM = {min, max, len}` | **7 ĐỎ** — 5 ca hợp đồng (`__import__(...)`, `open(...)`, `len(a)`, `abs(a)`, `(lambda: 1)()`) + 2 bài chính sách |
| Khôi phục cả hai | 79 passed, snapshot lại khớp 100 % |

Bài `test_neu_ai_do_noi_NGHIEM_thi_hop_dong_DO` đi qua **đường công khai**
(`kiem_bieu_thuc`), chứng minh `BANG` canh đúng bảng đang chạy chứ không canh
một bản sao.

⭐ Một phát hiện: nới `nut_cho_phep` thêm `ast.Attribute` **vẫn bị từ chối** —
máy chưa biết đi vào nút đó. Hai lớp phải cùng đồng ý thì một dạng nút mới sống.

## Test bốn nơi gọi

`registry.py` là **nơi gọi thật duy nhất** (`kiem_bieu_thuc`, nạp trễ, dòng
1183–1189). `am_master.py` và `tool_noi_bo.py` **không** import mô-đun này —
chúng có `bieu_thuc_*`/`tinh_bieu_thuc` **của riêng chúng** (trùng tên, khác
việc); `bien_dich.py` chỉ có mã lỗi chuỗi `"bieu_thuc_chua_ho_tro"`.

18 tệp test của cả bốn vùng, chạy qua `chay_nang.py --phien p2-t1` (khoá
`cpu_nhieu`, nhả sau 0,4 phút): **390 passed, 6 skipped, 0 failed**.
`ruff` + `mypy` trên ba tệp: sạch.

## ⛔ Phép đo này KHÔNG phủ

- **Không phủ ngôn ngữ §6** — chính sách đầy đủ chưa tồn tại.
- **Không phủ `tinh_cay` gọi thẳng với cây chưa qua `kiem_cay`.** Đường công
  khai luôn duyệt trước, nhưng ở nhánh nội bộ đó hành vi CÓ đổi: `UnaryOp` với
  toán tử ngoài bảng trước kia rơi vào `-gt`, nay ném lỗi. Chặt hơn, và không
  tới được từ API công khai — nhưng là một thay đổi, không phải không.
- **Không phủ hiệu năng / độ sâu đệ quy.** `RecursionError` với ngoặc lồng sâu
  vẫn thô như cũ (spec §6.4 giao việc bọc cho Task 5).
- **Không phủ đường `registry._validate_hop_dong_v2`** — `test_964` phủ, và nó
  xanh, nhưng `test_1761` gọi thẳng hàm.
- **Không đo ai khác đọc câu lỗi.** Nguyên văn câu lỗi được ghim, nhưng nếu có
  nơi nào *khớp chuỗi* trên câu lỗi thì phép đo này không thấy.

## Việc để lại cho người sau

`test_964::test_bo_tinh_KHONG_dung_eval` chỉ đọc AST của `bieu_thuc.py`. Ruột
đã chuyển tệp, nên cái canh gác đó **không còn nhìn vào chỗ có mã** — đúng hạng
lỗi "bánh cóc chỉ quét `print()` trực tiếp". `test_1761` có bản quét **cả hai**
mô-đun; `test_964` vẫn nên được nới ra khi ai đó sờ tới tệp đó (không sửa ở đây
để tránh đụng việc đang dở của phiên khác).

⚠️ Trong cây có `tests/test_1762_wf_noi_suy.py` **chưa commit của phiên khác** —
không đụng, không commit.

# P2 Task 3 + 5 — namespace §6.2 (chỉ đọc) + ép kiểu/giới hạn/lỗi §6.4

Cây `D:\LTTSTUDIOSAPP-p2`, nhánh `phien/p2-bieu-thuc`, nền `87067e8d`.
Gộp hai task vì cả hai **cài cùng một bảng** (`chinh_sach.DAY_DU`) — tách ra là
hai người sửa một tệp.

## Đã làm

- `platform_core/workflow/chinh_sach.py`
  - **Máy** học thêm bốn dạng nút (`Attribute`, `Subscript`, `List`, `Dict`),
    cắt mạch `and`/`or`, và lỗi mang **cột**.
  - **Bảng** `ChinhSach` thêm sáu ô *năng lực*, mặc định TẮT: `doc_thuoc_tinh`,
    `doc_khoa`, `cho_ghep`, `cat_mach`, `goc_phai_tinh`, `tran_sau`/`tran_nut`,
    `loi_mang_vi_tri`.
  - **Phương ngữ mới** `DAY_DU` (+ `chinh_sach_day_du(ham=…)`), namespace §6.2
    (`moi_truong_wf`, `KhongGianNodes`), bảng ép kiểu §6.4, giới hạn, và ba cửa
    vào `phan_tich` / `kiem_ngon_ngu` / `tinh_ngon_ngu`.
- `tests/test_1766_wf_ngon_ngu_day_du.py` — **158 phép**.

⛔ Không đụng `ham_bieu_thuc.py` (Task 4 đang làm), `noi_suy.py`, `bien_dich.py`.
Bảng hàm §6.3 đi **vào qua tham số** (`DAY_DU.ham == {}`), nên hai làn không
chạm nhau và tầng này test được bằng bảng giả.

## Quyết định phải ghi lý do

### 1. `nodes.b-2` — id node có dấu `-`

**Viết `nodes["b-2"].output.text`.** Lý do, theo thứ tự sức nặng:

1. **Không phải lựa chọn.** `ast.parse("nodes.b-2")` cho `BinOp(op=Sub)` — Python
   không có cách nào đọc nó thành một tên. (Phép kiểm ghim chính `ast` nói câu
   này, không ghim trí nhớ của tôi.)
2. **Cổng publish đã chốt hình dạng đó trước.** `bien_dich._chuoi_doan`
   (Task 7, đã commit) đọc `Subscript` với hằng `str`/`int` thành một đoạn:
   `nodes["b-2"].output.text` → `["nodes","b-2","output","text"]`. Nếu lúc chạy
   tôi chọn cú pháp khác thì có một chuỗi **publish được mà chạy không nổi**.
3. `nodes[vars.k]` (đoạn ĐỘNG) bị **cả hai cửa** từ chối, cùng một lý do: cổng
   publish không kiểm được quan hệ tổ tiên của một id chỉ biết lúc chạy. Một
   phép kiểm bắt khớp hai cửa trên **cùng một chuỗi**.
4. `nodes.b-2` không im lặng: nó báo *không có node `'b'`* — câu đúng sự thật,
   dẫn người gõ tới `nodes["b-2"]`.

### 2. `"a" == 1` ⇒ `false`; `1 + 1.5` ⇒ `2.5`

Căn cứ spec §6.4, nguyên văn: *"So sánh khác kiểu ⇒ `false` với `==`, lỗi với
`<`"* và *"Không ép ngầm **giữa chuỗi và số** trong `+`"*. int/float đều là "số"
⇒ `1 + 1.5 = 2.5`.

Nguồn đối chiếu (⭐ và nó **lật ngược một câu trong brief**):

- `google/cel-spec` `doc/langdef.md` §Equality nói CEL có **hai** hành vi:
  *"Type-checking asserts that arguments to equality operators must be the same
  type. If the argument types differ, the type-checker will raise an error"* —
  nhưng *"the runtime uses heterogeneous equality"*, công thức của chính họ:
  `type(x) == type(y) ? x == y : false`. ⇒ "CEL ném" đúng **về type-checker**,
  không đúng về runtime. Ta lấy luật runtime của CEL, bỏ luật type-checker.
- Lý do họ ghi ngay dưới đó cũng là lý do của ta: **dữ liệu JSON**, số có thể là
  `double` hay `int` tuỳ runtime.
- §Numbers: `int`/`uint`/`double` so *"as though they exist on a continuous
  number line"* ⇒ `1 == 1.0` là `true`. `bool` **không** nằm trong danh sách đó
  ⇒ `true == 1` là `false`.

⚠️ Python nói ngược ở hai chỗ, **đo được** chứ không nhớ: `1 == True` → `True`,
`True + 1` → `2` (vì `bool` kế thừa `int`). JSON có `true`/`false` riêng. Ta
theo JSON/CEL: `bool` là một lớp riêng, và **không phải số** trong số học
(`true + 1` ⇒ `kieu_khong_khop`).

⛔ `"a" * 3` cũng là `kieu_khong_khop`. `simpleeval` phải có
`MAX_STRING_LENGTH = 100000` + `safe_mult` (`b * len(a) > MAX_STRING_LENGTH`)
**vì** ngôn ngữ của họ cho `"x" * n`. Cấm phép đó rẻ hơn dựng một cái phanh.

### 3. Giới hạn: 10 000 nút · 1 MB · sâu 32, đo **trước** khi đệ quy

`do_gioi_han` đi bằng **vòng lặp**, không đệ quy — một cái phanh cho bộ duyệt
đệ quy mà tự nó cũng đệ quy thì chết đúng lúc cần nhất.

`cel-go` `parser/alias.go` có cả `MaxRecursionDepth(limit)` lẫn
`MaxExpressionNodeCount(limit)` — hai trần ở tầng **parser**, không ở tầng eval.
Ta làm cùng thế.

## Bằng chứng: trần sâu chặn TRƯỚC `RecursionError`

Đo trên máy này (Python **3.13.12**, `sys.getrecursionlimit() == 1000`) — và
phép đo **sửa lại điều spike đã ghi** (*"lồng ngoặc sâu ~200 ném `RecursionError`
thô"*). Ba đường chết, ba hành vi khác nhau:

| Nguồn | CPython làm gì | Ta làm gì |
|---|---|---|
| `"(" * 300 + "1" + ")" * 300` | `SyntaxError: too many nested parentheses` — **không phải** `RecursionError`. Chặn ở tokenizer: `Parser/lexer/lexer.c`, `if (tok->level >= MAXLEVEL)`; đo: 200 qua, 300 đỏ | bọc thành `LoiNgonNgu` có cột |
| `"1" + "+1" * 5000` | `RecursionError: maximum recursion depth exceeded **during ast construction**` — chính `ast.parse` chết, **trước** khi ta nhìn thấy cây | bọc; ⛔ trần sâu của ta **không** chặn được ca này |
| `"not " * 2000 + "1"` | parse **TỐT**, cây sâu 2002 > `getrecursionlimit()` | `do_gioi_han` từ chối ở nút 33 |

`test_tran_sau_chan_TRUOC_khi_Python_het_ngan_xep` giữ ca thứ ba và **tiêm lỗi
ngay trong bài**: bỏ `tran_sau` ⇒ `pytest.raises(RecursionError)` trên đúng cây
đó. ⛔ Không dùng `sys.setrecursionlimit` để "chứng minh" — đó là đổi luật chơi.

## Bằng chứng tiêm lỗi

Tiêm vào **mã đang chạy**, chạy lại cả tệp, rồi khôi phục:

| Tiêm | Kết quả |
|---|---|
| Bỏ luật `_` ở **bộ duyệt** (Attribute + Subscript) | **1 ĐỎ** (`(1).__class__`) |
| Bỏ luật `_` ở **tầng đọc dữ liệu** | 🔴 **157 passed — KHÔNG ĐỎ** |
| `ast.Eq` → `lambda a, b: a == b` (bỏ lớp JSON) | **3 ĐỎ**: `true == 1`, `false == 0`, `[1] == [true]` |
| `_cong` ép ngầm chuỗi↔số | **2 ĐỎ**: `"1" + 1`, `1 + "1"` |
| `TRAN_SAU` 32 → 10000 | **5 ĐỎ** |
| Khôi phục | 158 passed (+ `test_1761` 79 passed) |

⭐ Dòng đỏ đậm là **kết quả thật của phép đo, không phải sự cố**: luật `_` sống
ở hai tầng, và bộ test lúc ấy chỉ chạm tầng trên. Lỗ hổng thật: khoá **ĐỘNG** —
`vars[trigger.body.ten]` với `ten = "_bi_mat"` — bộ duyệt tĩnh không nhìn thấy
gì, chỉ tầng đọc còn canh. Đã thêm
`test_khoa_DONG_van_khong_doc_duoc_khoa_bat_dau_gach_duoi`; tiêm lại cùng chỗ
⇒ **1 ĐỎ** đúng bài đó.

Ngoài ra 5 ô trong bảng có **bài tiêm lỗi tự động** thường trú
(`test_TIEM_LOI_go_mot_o_trong_bang_thi_cai_rao_bien_mat`): gỡ `tran_sau`,
`tran_nut`, `doc_thuoc_tinh`, `doc_khoa`, `cho_ghep` ⇒ hành vi phải đổi.

## Hợp đồng `timeout_expr` KHÔNG ĐỔI

`tests/test_1761_*`: **79 passed** — đúng con số trong báo cáo Task 1, không
lệch một ca.

Chỗ suýt vỡ, và cách giữ: `test_1761::test_may_doc_CHINH_SACH...` ghim rằng mở
`ast.Attribute` trong `nut_cho_phep` của `NGHIEM` **vẫn** bị từ chối — lúc ấy vì
máy *chưa biết* đi vào nút đó. Nay máy biết. Nên "lớp thứ hai" chuyển thành một
**ô khai báo được** (`doc_thuoc_tinh=None` ⇒ không có `Attribute`, dù bảng có
mở). Bất biến giữ nguyên, và nó không còn dựa vào một lỗ hổng trong hiểu biết
của máy. `test_1766::test_NGHIEM_KHONG_duoc_mo_ra_boi_viec_may_hoc_them_nut_moi`
kiểm đúng điều đó cho cả bốn dạng nút mới.

Cả thành phần `core:wf_soan` (19 tệp, qua `chay_nang.py --phien p2-t35`, khoá
`cpu_nhieu` giữ 0,7 phút): **496 passed**. `ruff` + `mypy`: sạch.

## ⛔ Phép đo này KHÔNG phủ

- **Không phủ bảng hàm §6.3.** `DAY_DU.ham == {}`; các ca gọi hàm dùng bảng
  **giả** (`{"len": len}`). Ngày `ham_bieu_thuc.BANG_HAM` cắm vào, phải đo lại
  rằng không hàm nào trong 49 hàm mở thêm một dạng giá trị (ví dụ trả về vật gọi
  được) — tầng này chỉ cấm **cú pháp** gọi, không kiểm **giá trị trả về**.
- **Không phủ `{{ }}`** (`noi_suy.py`) và **không phủ đường động cơ**: chưa ai
  nối `tinh_ngon_ngu` vào `thi_hanh.py`/`dong_co.py`. `moi_truong_wf` nhận một
  **ảnh chụp** `{id: {status, output, error}}`; chưa đo rằng động cơ thật sinh
  ra đúng hình dạng đó.
- **Không phủ cổng publish** ngoài đúng một phép bắt khớp `nodes[…]` động.
- **Trần 1 MB là ƯỚC LƯỢNG** (ký tự + số ô), không phải `sys.getsizeof`. Một
  `dict` 100 khoá trỏ cùng một chuỗi 20 KB bị tính 100 lần — chặt hơn sự thật,
  và lệch về phía **từ chối**, không lệch về phía cho qua.
- **Không phủ 10 000 nút lúc TÍNH.** Spec nói *"nút được thăm mỗi lần tính"*; ta
  đếm **tĩnh** trước khi tính. Không có vòng lặp/comprehension trong ngôn ngữ
  nên số thăm ≤ số nút tĩnh — nhưng nếu một ngày có `map()` thật sự lặp, phép
  đếm tĩnh này **không còn là trần** và không có gì ở đây kêu lên.
- **Không phủ Python khác 3.13.12.** Ba ngưỡng ở bảng trên (`MAXLEVEL` 200,
  `RecursionError` ở ~5000 phép cộng, ngăn xếp 1000) là số đo của **máy này**.
  Trần 32 thì độc lập với chúng; phần **bọc lỗi thô** thì không.
- **Không đo ai khớp chuỗi trên câu lỗi.** Câu lỗi §6 là mới hoàn toàn, chưa nơi
  nào đọc; nếu Canvas/API sau này khớp chuỗi thì phép đo này không thấy.

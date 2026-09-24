# P2 — Mối nối `BANG_HAM` × bộ tính + Task 6 (`vars` §6.5)

Cây `D:\LTTSTUDIOSAPP-p2`, nhánh `phien/p2-bieu-thuc`, nền `e410dc4a`.

Hai việc, một lượt, vì cả hai đều là **chỗ hai làn song song chạm nhau**:
`vars` chỉ đọc được khi bảng hàm đã cắm vào bộ tính (`keys(vars)`, `get(vars, …)`).

## Việc A — nối bảng hàm thật vào chính sách đầy đủ

### Đã làm

- **`platform_core/workflow/ngon_ngu.py` (mới)** — tầng **lắp**, và là chỗ duy
  nhất hai nửa gặp nhau: `NGON_NGU = chinh_sach_day_du(ham=BANG_HAM, …)`, hai
  cửa `ngon_ngu.tinh` / `ngon_ngu.kiem`.
  ⛔ Không cắm `BANG_HAM` thẳng vào `chinh_sach.DAY_DU`: `DAY_DU.ham == {}` là
  điều `test_1766` ghim, và `ham_bieu_thuc` nạp trễ `public_api.projects` (kéo
  SQLAlchemy) cho `slugify` — một phụ thuộc tầng máy không được có.
- **`chinh_sach.py`** — nhánh `ast.Call` của bộ tính đi qua `_goi_ham()`: hỏi
  chữ ký **trước** khi gọi, rồi bọc mọi ngoại lệ. Ô khai báo mới
  `ChinhSach.loi_nguoi_dung` nói lớp lỗi nào của bảng được **dẫn nguyên văn**.
- **`bieu_thuc.py`** — `NGHIEM` nhận ba câu lỗi mới. Nó có `ast.Call` + `min`/
  `max` nên đi qua **cùng đoạn mã**; trước đó `min()` ném `TypeError` **thô**
  xuyên qua `tinh_bieu_thuc` — trên đường `timeout_expr`, tức trên đường tính
  trần tiền.
- **`tests/test_1767_wf_noi_bang_ham.py` — 169 phép.**

### 49/49 hàm gọi được qua bộ tính

Bảng ca kiểm so **hai chiều** với `set(BANG_HAM)`
(`test_bang_phep_kiem_khop_BANG_HAM_ca_hai_chieu`) ⇒ thêm một hàm vào bảng mà
không gọi nó qua bộ tính là **đỏ**. Mỗi hàm còn bị soi giá trị trả về: không
vật gọi được, không kiểu ngoài JSON — đúng chỗ báo cáo Task 3+5 ghi là *"chưa
phủ"* (tầng chính sách cấm **cú pháp** gọi, không kiểm **giá trị** trả về).

### 🔴 Ba lỗi THẬT ở mối nối — không nửa nào tự thấy được

Hai nửa đều đúng theo hợp đồng của riêng nó:

| | |
|---|---|
| `chinh_sach.py` (§6.2) | bày ra `Mapping` — đọc lười, câu lỗi riêng |
| `ham_bieu_thuc.py` (§6.3) | hỏi `isinstance(x, dict)` |

`Mapping` **không phải** `dict`. Hậu quả đo được lúc cắm bảng vào lần đầu:

1. `keys(vars)` ⇒ `"keys: can object, gap khong_ho_tro"` — hỏng ồn ào;
2. `get(nodes.a.output, "text")` ⇒ **lặng lẽ trả mặc định**. Tệ hơn (1): một
   câu trả lời sai đi tiếp vào node sau;
3. `get(nodes.a.output, "khong_co", 0)` ⇒ **ném**, thay vì lùi về `0`. Gốc:
   `Mapping.__contains__` mặc định gọi `self[khoa]` và chỉ bắt `KeyError`, còn
   các namespace §6.2 ném `LoiNgonNgu` — nên `in` **ném**.

Sửa: `ham_bieu_thuc` khai một chỗ *"object là gì"* (`_OBJECT = Mapping`) và mọi
cửa đọc object hỏi chỗ đó; bốn lớp namespace (`_CongRa`, `_MatNode`,
`KhongGianNodes`, `KhongGianVars`) có `__contains__` riêng. `json.dumps` nhận
`default=_json_object` (chỉ mở cho `Mapping`, không rộng hơn).

⚠️ Không phép kiểm nào của hai làn nhìn thấy được ba điều này: một bên chỉ có
bảng **giả** (`dict` thuần), bên kia chỉ có dữ liệu JSON thuần.

### Lỗi có chỗ · số tham số sai

`json_parse('{bad')` ⇒ `LoiNgonNgu` có `vi_tri` + `bieu_thuc`, **không** phải
`LoiHam` (lớp lỗi của tầng dưới) và không rò `JSONDecodeError`/traceback.
`upper()`, `range()`, `substring("abc",1,2,3)` ⇒ *"goi ham … sai so tham so"*,
⛔ không `TypeError` thô.

⭐ Đo được, không phải nhớ: `inspect.signature(min)` **ném `ValueError`**
(builtin không có `__text_signature__`). Nên có hai đường: hỏi chữ ký trước
(49 hàm của bảng) và bắt `TypeError` sau (`min`/`max` của `NGHIEM`). Và chỉ
đường **thứ hai** được phép gọi một `TypeError` là "sai số tham số" — khi đã
bind được thì `TypeError` chắc chắn đến từ **thân hàm**, gọi nó là "sai tham
số" sẽ đẩy người gõ đi sửa một chỗ không sai.

## Việc B — Task 6: `vars` §6.5

**`platform_core/workflow/bien_vars.py` (mới)** + `tests/test_1768_wf_vars_6_5.py`
(**28 phép**).

### Luật ghi xung đột, nguyên văn §6.5

> `vars` = gộp output của mọi `core.set` là **tổ tiên** của node đang tính, theo
> thứ tự `graph.thu_tu`. Hai `core.set` ghi cùng khoá mà **không có quan hệ tổ
> tiên** ⇒ validator từ chối (`ghi_bien_xung_dot`).

⇒ Hai nửa dùng **cùng một quan hệ tổ tiên**:

- `gop_vars(anh_chup, *, nguoi_ghi, to_tien, thu_tu)` — lúc chạy. Hàm **thuần**:
  cùng ba đầu vào ⇒ cùng kết quả, kể cả khi replay. Người đi **sau** trong
  `thu_tu` ghi đè (và họ có quan hệ tổ tiên nên điều đó tất định).
- `kiem_ghi_xung_dot(khoa_ghi, to_tien)` — lúc publish, ném
  `LoiBienDich("ghi_bien_xung_dot", …)`.

⛔ Có một cách đọc **lỏng hơn** — chỉ từ chối khi có một node thật sự đọc `vars`
và nhìn thấy cả hai — và tôi **không** lấy: nó không phải cái spec viết, và nó
làm tính hợp lệ của một đồ thị đã publish phụ thuộc vào việc ai đó *có đọc*
`vars` hay không (sửa node đọc ⇒ đồ thị cũ thành bất hợp lệ).

Ba quyết định spec **không** nói, ghi ra để ai đó lật được:
- người ghi là tổ tiên nhưng **chưa `SUCCEEDED`** ⇒ không đóng góp; câu lỗi khi
  đọc hụt nêu đích danh họ (`KhongGianVars.cho_xong`). Output chưa tồn tại,
  không phải "rỗng" — cùng luật `_MatNode` đang dùng;
- khoá bắt đầu `_` **vô hình** ở `vars` — một luật, mọi cửa;
- người ghi **không có trong `thu_tu`** ⇒ **ném**, không bỏ qua (bỏ qua là đổi
  một giá trị trong im lặng).

### ⛔ Không cài node `core.set` — và chỗ móc là một bánh cóc

`core.set` là node P3; hôm nay `bien_dich` từ chối mọi loại ngoài `tool`/`app.*`
(`loai_node_chua_ho_tro`). Nối `kiem_ghi_xung_dot` vào `bien_dich` bây giờ là
dựng **một cổng không ai đi qua** — đúng hạng lỗi kho này đã ghi. Nên thay vì
nối, `test_1768` giữ một **bánh cóc hai chiều**: hôm nay nó khẳng định `core.set`
*chưa* biên dịch được **và** cổng publish *chưa* gọi validator; ngày P3 mở node
ấy ra, vế trái sai và bài đỏ, bắt người mở phải nối validator vào.

## Bằng chứng TIÊM LỖI (tiêm vào mã đang chạy, chạy lại, khôi phục)

Nền: `test_1767` + `test_1768` + `test_1761` = **276 passed**.

| Tiêm | Kết quả |
|---|---|
| A1 bỏ kiểm **tên hàm** ở bộ tính (`tinh_cay`) | **10 đỏ** |
| A2 bỏ hỏi **chữ ký** trước khi gọi | **6 đỏ** |
| A3 bỏ lớp bọc lỗi của hàm | **12 đỏ** |
| A4 `object = dict` (trạng thái trước khi ghép) | **15 đỏ** |
| A5 bỏ `__contains__` của `_CongRa` | **2 đỏ** |
| B1 bỏ lọc **tổ tiên** trong `gop_vars` | **6 đỏ** |
| B2 gộp theo tên thay vì theo `thu_tu` | **4 đỏ** |
| B3 bỏ phép hỏi tổ tiên ở validator | **2 đỏ** |
| khôi phục | **276 passed** |

⚠️ A2 **lần đo đầu ra XANH** — phép kiểm chữ ký là trang trí, vì nhánh bắt
`TypeError` ở sau nuốt luôn. Đó là kết quả thật của phép đo: nó chỉ ra rằng hai
hạng lỗi (*gọi sai* vs *thân hàm hỏng*) đang bị gộp làm một. Đã tách hai nhánh
và thêm `test_TypeError_TRONG_THAN_ham_khong_bi_goi_nham_la_sai_tham_so`; tiêm
lại ⇒ **6 đỏ**. (Cùng cách Task 3+5 tìm ra lỗ "khoá động".)

## Hợp đồng `timeout_expr` KHÔNG ĐỔI

`tests/test_1761_*`: **79 passed** — đúng con số của Task 1/Task 3+5, không lệch
một ca. Điều duy nhất đổi ở `NGHIEM` là **thêm** ba câu lỗi cho đường trước đây
ném `TypeError` thô; không ca nào trong 79 ca chạm đường đó (đã đọc bảng
snapshot: bốn ca `min`/`max` đều đúng số tham số).

Thành phần `core:wf_soan` (23 tệp, sau khi đăng ký 5 mô-đun §6 vào
`tools/thanh_phan.toml`): **812 passed**. Thêm năm tệp bánh cóc công cụ
(`test_145`, `test_308`, `test_309`, `test_505`, `test_954`): **89 passed**.
`ruff` + `mypy`: sạch. Lệnh nặng qua `chay_nang.py --phien p2-t6`.

🔴 Một bánh cóc bắt đúng ngay: `test_1765::test_module_khong_co_cua_thi_hanh`
cấm **mọi** thuộc tính dunder trong `ham_bieu_thuc.py` — `type(x).__name__`
trong một câu lỗi mới làm nó đỏ. Đã thay bằng `_ten_kieu(x)`.

## ⛔ Phép đo này KHÔNG phủ

- **Không phủ node `core.set`, và không phủ đường publish của `vars`.**
  `kiem_ghi_xung_dot` **chưa có một đường gọi nào trong sản phẩm** — chỉ phép
  kiểm gọi nó. Bánh cóc ở trên là thứ duy nhất giữ cho điều đó không bị quên;
  nó đo một sự **vắng mặt**, và một sự vắng mặt thì "xoá cũng xanh".
- **Không phủ đường động cơ.** Chưa ai gọi `gop_vars` hay `ngon_ngu.tinh` lúc
  chạy: `thi_hanh.py`/`dong_co.py` chưa nối. Cả §6.2 vẫn là một ảnh chụp do
  phép kiểm dựng tay — **chưa đo** rằng động cơ thật sinh đúng hình dạng đó.
- **Không phủ `{{ }}`.** `noi_suy.py` (Task 2) nhận bộ tính qua tham số và
  **chưa ai truyền `ngon_ngu.tinh` vào**. Bánh cóc `test_BANH_COC_khong_module_nao_goi_tinh_ngon_ngu_ma_quen_bang_ham`
  chỉ bắt lời gọi thiếu `cs=`; nó **không** bắt được một tầng nhận bộ tính qua
  tham số rồi được truyền nhầm thứ khác.
- **Ngữ nghĩa từng hàm vẫn là của `test_1765`.** 1767 chỉ hỏi *"gọi được"* và
  *"trả về giá trị JSON"*, không hỏi *"trả về đúng"*.
- **`_khong_phai_vat_python` chỉ soi giá trị trả về của ĐÚNG 49 biểu thức mẫu.**
  Một hàm trả vật lạ chỉ trên một nhánh khác (ví dụ `date_*` với `tz` lạ) không
  bị nhìn tới.
- **Bánh cóc `core.set`** đọc `bien_dich.py` bằng AST và tìm **tên lời gọi**
  `kiem_ghi_xung_dot`. Nối validator bằng một tên khác (alias, gọi gián tiếp)
  thì nó không thấy.
- **`loi_nguoi_dung` là một danh sách trắng.** Hôm nay `(LoiHam, LoiNgonNgu)`.
  Một lớp lỗi mới của tầng bảng sẽ rơi vào nhánh "hàm hỏng" và **mất câu chữ**
  — đúng, nhưng không có gì kêu lên rằng có một câu vừa bị nuốt.
- **Số đo là của máy này** (Python 3.13.12): `inspect.signature(min)` ném
  `ValueError`. Trên một bản Python cho `min` một chữ ký, nhánh A2 đổi.

# Phase 12 — Tra tấn: đồng thời, bảo mật, dữ liệu, hiệu năng

*H43, 2026-09-03.*

Bốn nhóm phép kiểm ép ChatLTT vào những trạng thái mà đường đi hạnh phúc không
bao giờ tới. Cộng thêm một sự cố cổng chất lượng mà chính pha này gây ra, và
điều nó dạy được thì đắt hơn cả bốn nhóm kia.

---

## 1. Bốn nhóm phép kiểm

| Tệp | Nhóm | Số phép kiểm |
|---|---|---|
| `tests/test_627_chatltt_torture_dong_thoi_tien.py` | đồng thời + tiền | 9 |
| `tests/test_628_chatltt_torture_bao_mat.py` | bảo mật | 8 |
| `tests/test_629_chatltt_torture_du_lieu_hieu_nang.py` | dữ liệu + hiệu năng | 8 |
| `tests/test_630_suc_khoe_giai_dia_chi_nhu_duong_goi_that.py` | sức khoẻ cổng | 6 |

### Đồng thời + tiền (`test_627`)

Bất biến neo ở đây: **mọi đường thoát của một lượt đều quyết toán đúng một
lần.** Hoàn thành, bị huỷ, bị bán, hết credit giữa chừng, người dùng đóng
trình duyệt — năm đường, một sổ.

### Bảo mật (`test_628`)

Chủ sở hữu là điều kiện của *mọi* thao tác, không phải của thao tác đọc. Đã
bắt được một lỗ đi qua hình dạng khoá lưu trữ: `anhnoibo/<uid>/../../secrets/app.env`
qua được phép kiểm hình dạng ban đầu. Nay mọi đoạn thuộc `("", ".", "..")` và
mọi dấu `\` đều bị từ chối.

### Dữ liệu + hiệu năng (`test_629`)

Dọn hội thoại xoá mềm quá 30 ngày (`hoi_thoai.don_da_xoa`, chạy qua
`MANIFEST.bao_tri` mỗi 6 giờ dưới lease nền tảng). Ngưỡng hiệu năng đặt rộng có
chủ ý — chúng bắt **độ phức tạp bậc hai**, không đo tốc độ máy: cây 400 nút,
một lượt 5.000 delta, một hội thoại 60 lượt.

### Sức khoẻ cổng (`test_630`)

Sinh ra từ một phép đo LIVE: `GET http://192.168.2.66:8299/live` trả **200**
trong khi hook `suc_khoe` trả `chua_san_sang`. Nguyên nhân: hook đọc
`providers.get(...).base_url` (biến môi trường) còn đường gọi thật
`luong_vlm.mo` lấy `base_url` của **khoá** trước. Một chip "chưa sẵn sàng" sai
làm ô soạn tắt cho **mọi** người trong khi model chạy tốt.

---

## 2. Sự cố: 16 phép kiểm đỏ, và một giả thuyết khớp quá vừa

### Triệu chứng

Lượt gate đầy đủ sau Phase 12 đỏ với 16 phép kiểm rải trên **bảy tệp không liên
quan gì nhau**: 112, 122, 157, 172, 220, 305, 606. Mọi tệp đều XANH khi chạy một
mình. Thông điệp giống hệt nhau ở mọi chỗ:

```
sqlite3.OperationalError: no such table: users
```

### Giả thuyết sai, và vì sao nó sống lâu

**"Máy quá tải."** Nó khớp *hoàn hảo* với mọi dữ kiện có lúc đó:

- đỏ khi chạy cả bộ, xanh khi chạy cụm nhỏ → giống hệt tranh chấp tài nguyên;
- máy **thật sự** đang bận — một phiên khác đang chạy gate, và chính phiên này
  đã chạy `pytest -n auto` gõ tay **ba lần** ngoài mọi ngân sách;
- một đồng nghiệp báo độc lập rằng hai lượt `-n auto` = 40 worker trên 20 lõi
  đã làm máy treo phải reset cứng **hai lần**.

Ba mẩu bằng chứng, tất cả đều thật, tất cả đều trỏ sai hướng. Mất gần một giờ.

⭐ Đây là bản **thứ sáu** của cùng một cơ chế trên máy này trong một ngày (xem
bộ nhớ `gia-thuyet-khop-qua-vua-ket-thuc-dieu-tra`): **một giải thích SAI mà
khớp HOÀN HẢO thì kết thúc cuộc điều tra đúng lúc cuộc điều tra mới bắt đầu.**

### Nguyên nhân thật

`tests/test_630::test_khong_co_CSDL_thi_tra_rong_chu_khong_nem` gọi
`importlib.reload(platform_core.db)` để dọn dẹp.

`reload` dựng một lớp `Base` **mới** mang một `MetaData` **rỗng**. Mọi tệp chạy
**sau** nó trên cùng worker gọi `Base.metadata.create_all()` tạo **không bảng
nào** — im lặng, không ném, mã thoát 0 — rồi chết ở dòng đầu tiên chạm CSDL.

Tái hiện được 100%, hai tệp, một lệnh:

```
pytest tests/test_630_*.py tests/test_606_*.py   ->  5 failed
(bo `reload`)                                    -> 11 passed
```

⛔ Lỗi không thể tự lộ ra ở tệp gây ra nó. Nó chỉ hiện ở **nạn nhân**, nên ai
đọc dấu vết cũng bị dẫn đi sai chỗ. Và tập nạn nhân đổi theo số worker, nên
cùng một cây cho ra hai tập lỗi khác nhau ở hai lượt — thứ khiến "quá tải"
trông như một lời giải thích đúng.

### Hai lỗi thứ cấp cùng loại, có sẵn từ trước

`test_112`, `test_174`, `test_90` gọi `create_all` **trước** khi
`platform_core.models` được nạp. Chúng xanh nhiều tháng chỉ vì `--dist loadfile`
xếp chúng sau một tệp khác đã nạp `models` hộ; chúng đỏ khi bị xếp lên **đầu**
một worker. Đã sửa cả ba.

⭐ Một phép kiểm xanh nhờ hàng xóm thì không phải một phép kiểm xanh.

---

## 3. Chốt: `tests/test_631_cach_ly_bo_test.py`

Hai luật, quét **AST** toàn bộ tệp test:

1. **Không `reload` module giữ `Base`** (`platform_core.db`, `platform_core.models`).
2. **`create_all` phải đứng sau khi bảng đã đăng ký.**

192 phép kiểm, xanh, mốc bằng 0 trên cây chung.

### Vì sao phải là AST, không phải grep

Kho **đã có ba đoạn chú thích cấm `importlib.reload`**, và một trong đó
(`tests/test_378:192`) mô tả *chính xác* triệu chứng này, kể cả chi tiết "nó
chạy xanh". Một bộ dò quét văn bản sẽ làm đỏ đúng ba chỗ đã ghi bài học.

⛔ **Một bộ dò đọc văn xuôi thì trừng phạt việc giải thích** — và cách sửa rẻ
nhất cho người sau là xoá phần giải thích đi. Đọc AST thì tự khắc chừa, vì chú
thích không phải `ast.Call`.

### Vì sao chú thích không đủ, dù đã có ba chỗ

Ba chỗ ghi, đều đúng, đều kèm lý do — và vẫn không ngăn được lần thứ ba. Vì một
bài học trong docstring của `test_287` **không với tới người đang viết
`test_630`**.

⇒ Ranh giới giữa **chú thích** và **chốt**: chú thích tới được người mở đúng tệp
ấy; chốt tới được mọi người, vì nó làm gate đỏ.

---

## 4. Cổng chất lượng: chế độ nối tiếp

Sự cố trên phơi ra một lỗ thật, độc lập với nó: **một lượt đo có thể bị nhiễu mà
không ai thấy.**

`tools/cua_so_yen.py` chỉ thấy ai **xin khoá**. Nó không thấy `pytest` gõ tay,
không thấy deploy, không thấy bốn dịch vụ production. Đo được 03/09:
`cua_so_yen trang-thai` báo **RẢNH** trong khi CPU **65%**.

### Ba thay đổi

**`tools/gate.py` — hồ sơ `--noi-tiep`.** MỘT bước một lúc **và**
`test_nhanh.py --noi-tiep` (một tiến trình pytest, không xdist), frontend
`--maxWorkers=1`.

⛔ `--tuan-tu` một mình **không đủ**, và đây là chỗ dễ đọc nhầm nhất: nó xếp
hàng các **bước**, nhưng bước `bo test` vẫn tự mở 10-14 worker bên trong nó.
"Tuần tự" ở mức lịch chạy không có nghĩa là một tiến trình.

⛔ Và `--noi-tiep` **không phải** `-n 1`: `-n 1` vẫn đi qua xdist. Chế độ này có
giá trị đúng ở chỗ nó là phép đo duy nhất **không đi qua lớp đang bị nghi ngờ**.

**`tools/gate.py` — `loi_dang_ban()`.** In `[tai may] N/20 loi dang ban ->
RANH/BAN/QUA TAI` ở đầu **mọi** lượt, và `ngan_sach_loi(do_tai=True)` trừ thêm
phần tải vượt nền.

**`tests/conftest.py` — `pytest_xdist_auto_num_workers`.** `-n auto` bị kẹp
bằng `min(cpu_count - 6, xdist tự đề xuất)`.

⭐ Ranh giới là **mặc định chứ không phải mệnh lệnh**: `auto` không phải một lựa
chọn của người gõ, nó là "công cụ tự quyết", và công cụ này quyết sai vì nó
không biết gì về bốn dịch vụ bên cạnh. Một con số gõ tay thì ngược lại — đó là
một ý định, và ta không đạp ý định của người khác.

⚠️ Bản đầu của vá này trả thẳng `cpu_count() - 6` = 14. Sai, và chỉ lộ ra khi
đo: xdist tự trả lời bằng `psutil.cpu_count(logical=False)` = **10** lõi vật lý
trên máy này. Một "cái trần" 14 đặt lên câu trả lời 10 thì **nâng** số worker
lên — đúng chiều ngược lại với lý do vá này tồn tại. Nên nó phải là một phép
`min`, không phải một phép gán.

---

## 5. Nợ còn lại

- Chưa có phép kiểm a11y tự động (axe). Ma trận UX Phase 10 kiểm bằng tay.
- Thanh credit ở đầu trang nền tảng vẫn cũ cho tới khi tải lại trang.

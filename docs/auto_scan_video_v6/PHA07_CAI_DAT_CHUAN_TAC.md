# PHA 07 — ProductSettings chuẩn tắc + RenderManifest v3

> `apps/auto_scan_video/cai_dat.py`. Nhánh `phien/asv-v6`.
>
> ⛔ Pha này **không tạo ra** ProductSettings. `AsvRun.settings` đã là nó từ V4.
> Pha này làm nó **tự khai**, **băm được**, và — quan trọng nhất — **có một chỗ
> đọc**.

## 1. 🔴 Lỗi đã có sẵn, và nó là lý do pha này tồn tại

Cùng một khoá `timing_mode`, **hai** mặc định khác nhau ở hai tệp:

```
giai_doan_thoi_gian.py:95   str(... .get("timing_mode") or "fit_original")
giai_doan_qc.py:154         str(... .get("timing_mode") or "")
```

⇒ Một lần chạy thiếu khoá đó sẽ **chạy** ở chế độ `fit_original` trong khi
**bằng chứng QC ghi rỗng**. Không chỗ nào báo lỗi: cả hai bên đều tìm thấy một
giá trị hợp lệ của riêng mình.

Và chuỗi `"fit_original"` ở dòng trên là một bản **chép cứng** của
`gia.CHE_DO_MAC_DINH` — tức bản thứ ba của cùng một hằng số.

⭐ Đây đúng hình dạng `su-that-doc-lap-chan-suy-luan-sai`: **một câu hỏi phải có
một chỗ trả lời.**

Và một lỗi thứ hai cùng họ, ở chỗ khách nhìn thấy: template `asv_chi_tiet.html`
đọc `run.settings.get("timing_mode")` **không kèm mặc định** rồi so với bảng
nhãn — hồ sơ thiếu khoá thì không nhãn nào khớp, và dòng *"Cách khớp thời gian"*
hiện ra **trống**.

## 2. Hai chế độ đọc, và vì sao chúng phải khác nhau

| | `chuan_hoa` (GHI) | `tu_ho_so` / `doc` (ĐỌC) |
|---|---|---|
| khoá không dùng tới | **vắng mặt** | có, mang mặc định |
| vì sao | `thi_hanh.van_tay` băm cả `settings`; một mảng rỗng ghi vào **mọi** lần chạy làm hồ sơ của những lần **không** dùng tính năng đó khác đi mà không vì lý do gì | để không ai phải chép lại một mặc định |

Đây là luật `cat_dau_cuoi` L4 đã viết ra từ V6 pha 10 — pha 07 chỉ đưa nó thành
cơ chế thay vì một ghi chú ở bốn chỗ.

## 3. Schema

```
SCHEMA      = "asv.cai_dat.v3"
PHIEN_BAN   = 3
```

`v3` không phải "lần sửa thứ ba" — nó là thứ tự **hợp đồng**: V4 lưu settings
phẳng không khai gì (v1), V5/V6 thêm vùng/cắt/lớp phủ/logo vẫn không khai gì
(v2), và đây là bản đầu tiên **tự khai** (v3).

⚠️ Hồ sơ **không** có khoá `schema` là hồ sơ **trước v3, không phải hồ sơ hỏng**
— có thật hàng nghìn hồ sơ như thế, và `phien_ban_ho_so` trả **`0`** chứ không
`None`: một hồ sơ cũ là một hồ sơ có thật và đọc được, không phải một hồ sơ
thiếu dữ liệu. Trả `None` sẽ mời mọi người đọc viết một nhánh `is None` cho một
trường hợp hoàn toàn bình thường.

## 4. Vân tay

`van_tay(tho)` băm **toàn bộ** cấu hình khách chọn, tính **tại chỗ**.

⛔ **Không lưu xuống.** Một vân tay được lưu là một vân tay sẽ cũ đi trong khi
thứ nó đại diện thì đổi — và nó cũ **im lặng**, vì một chuỗi băm trong không
khác gì một chuỗi băm đúng.

⛔ Và nó **không** `sorted()` các phần tử list. Thứ tự lớp phủ là thứ tự vẽ
chồng; thứ tự logo là thứ tự các `<input type=file>` đi trong multipart. Một
`sorted()` **thừa** nguy hiểm hơn thiếu: nó làm hai cấu hình **khác nhau** dùng
chung một vân tay (`sap-xep-list-trong-van-tay-hai-chieu-hong`).

## 5. Mười nơi đọc → một

| trước | sau |
|---|---|
| `giai_doan_ban_bien_tap` · `ban_dung` (×5) · `chep_loi` (×2) · `giong` (×2) · `noi_dung` · `qc` · `thoi_gian` (×2) | `cai_dat.doc(run)` |
| `routes.tao` ghi `dict(cai_dat)` ×2 + `_gan_logo_vao_run` ghi lại | `cai_dat_mod.chuan_hoa(...)` ×3 |
| template tự `run.settings.get(...)` ×4 | `cai.preset` / `cai.timing_mode` / … |

⭐ `co_sua_diem_anh` gộp một câu từng phải hỏi riêng ba danh sách ở ba chỗ.

## 6. Bánh cóc + đối chứng

`test_469` — 25 bài. Bài có răng nhất đọc **AST** và hỏi mệnh đề **dương**:
*"không `giai_doan_*` nào còn tự đọc một khoá của `settings`"*. Một phép kiểm chỉ
đòi *"`cai_dat.py` tồn tại"* sẽ xanh ngay cả khi mười chỗ đọc cũ còn nguyên.

Bốn đối chứng đã tiêm, **cả bốn đỏ đúng chỗ**:

| tiêm | bài đỏ |
|---|---|
| trả một chỗ đọc thẳng `settings` về `giai_doan_qc` | `test_KHONG_giai_doan_nao_con_TU_doc...` |
| trả đường lui `or "fit_original"` | `test_KHONG_ai_con_dung_fit_original_lam_DUONG_LUI` |
| thêm một `sorted()` thừa vào vân tay | `test_THU_TU_PHAN_TU_trong_list_CO_doi_van_tay` |
| lưu thưa → lưu đầy (mảng rỗng vẫn ghi) | 4 bài §4 |

### ⚠️ Một bài kiểm của tôi từng rộng hơn mệnh đề của nó

Bản đầu của `test_KHONG_ai_con_dung_fit_original...` cấm chuỗi `"fit_original"`
xuất hiện ở bất cứ đâu ngoài `gia.py`. Nó báo động trên **ba chỗ không phải
lỗi**: hai **mặc định tham số** của module miền (`qc.kiem`, `thoi_gian.lap_ke_hoach`)
và một **phép kiểm tư cách** (`if che_do not in (...)`).

Một mặc định tham số của module miền là hợp đồng của chính nó, không phải một
bản đọc hồ sơ khách. Bản viết lại đọc AST và hỏi đúng hình dạng đã hỏng:
`<gì đó> or "fit_original"`.

## 7. Hai bánh cóc kiến trúc bắt đúng việc

Chạy dải 4xx lần đầu sau khi di trú: **1524 passed, 2 failed** — và cả hai đều
là bánh cóc làm đúng việc của chúng.

- `test_427` — bản đồ rebase phải phủ **hết** module. Tôi thêm `cai_dat.py` mà
  chưa khai. ⇒ đã khai.
- `test_453` — `phien_ban_ho_so` bị bắt là **năng lực mồ côi**: một hàm công
  khai mà chỉ bài kiểm gọi (`nang-luc-co-nhung-khong-ai-di-tren-duong`).

⭐ Cách sửa **không** phải xoá hàm đi: một hồ sơ có phiên bản mà không ai đọc
được phiên bản đó thì việc đánh số nó không mua được gì. ⇒ Mở đường thật: màn
*"Cài đặt đã dùng"* nay in `v{phiên bản} · {vân tay}` cho người vận hành.

⛔ Và mở đường xong vẫn chưa đủ. Jinja render một biến không tồn tại thành
**rỗng, im lặng**, nên một phép kiểm đọc *văn bản template* vẫn xanh khi tên
biến ở context bị gõ sai. `test_469` §6 render **thật** qua HTTP và chốt hai giá
trị có mặt trong HTML trả về.

## 8. Hệ quả phải biết

**Mọi vân tay giai đoạn của run MỚI đều đổi.** `thi_hanh.van_tay` băm cả
`settings`, và settings nay mang thêm khoá `schema`. Đó chính là việc một số
hiệu schema tồn tại để làm, và ASV chưa deploy (`enabled=False`, 404 ở
production) nên không lần chạy nào của khách bị ảnh hưởng.

**Bằng chứng QC của run thiếu `timing_mode` nay ghi khác trước** — nó ghi giá
trị mà đường ống **thực sự** dùng. Đó là sửa lỗi, không phải tác dụng phụ.

## 9. Còn nợ

| mục | vì sao chưa đóng |
|---|---|
| `rang_giong.tu_thiet_lap` vẫn nhận `dict` | `cai_dat` đọc `CHE_DO_GIONG_MAC_DINH` của `rang_giong`, nên chiều ngược lại là vòng tròn import. Người gọi chuẩn hoá trước rồi đưa vào — đúng, nhưng chưa gọn |
| `qc.kiem` / `thoi_gian.lap_ke_hoach` giữ mặc định tham số riêng | Hợp đồng của module miền, không phải bản đọc hồ sơ. Để nguyên có chủ đích; nếu gộp thì phải gộp vào `gia.py` chứ không vào `cai_dat.py` |
| `RenderManifest` chưa mang vân tay hồ sơ | `ban_dung` có `SCHEMA_BAN_DUNG` riêng. Nối `van_tay(settings)` vào manifest là việc của pha 26 (renderer fusion), nơi manifest được đọc lại |

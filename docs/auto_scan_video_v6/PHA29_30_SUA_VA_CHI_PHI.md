# Pha 29 + 30 — hai năng lực có sẵn mà không ai đi trên đường

Ngày 11/09/2026. Hai pha gộp một tài liệu vì chúng mắc **cùng một bệnh**, và cả
hai đều không lộ qua bộ dò mồ côi.

## Pha 29 — Targeted RepairPlan: **MỘT PHẦN, chặn ở pha 28**

### Đo trước

`sua_chua.py` (V4/V5) đã có đúng thứ đề bài gọi tên: mỗi hạng khiếm khuyết ánh xạ
tới **giai đoạn sớm nhất mà nội dung của nó là nguyên nhân**; `gon_theo_don_vi` ép
*đơn vị nhỏ nhất*; `jobs._advance` mở lại **riêng** các đơn vị hỏng (`mo_lai_don_vi`),
giữ artifact của đơn vị lành; trần một vòng, ghi sổ cái trước khi đặt lại.

Nhưng vòng sửa chỉ được nối **2 trong 4** nguồn:

| nguồn | hạng | nối vào `jobs._advance`? |
|---|---|---|
| `cac_nan` | không vừa khe | ✔ |
| `qc_ngu_nghia` | dịch sai | ✔ (khi QC bằng AI bật) |
| `qc_giong` | **đọc sai** | ✘ — không bộ phận nào sinh ra dữ liệu này |
| `qc_hinh` | cắt sai theo hình | ✘ — như trên |

`tu_qc_giong` và `tu_qc_hinh` có mã, có test đơn vị, và **không bao giờ chạy trong
sản phẩm**. `test_453` không thấy vì nó khớp theo **tên hàm**, mà tên ấy có người
gọi: chính `lap_ke_hoach`.

### Làm được gì

`test_482` chốt **tập** nguồn đã nối (`{cac_nan, qc_ngu_nghia}`) và **tập** chưa nối
kèm lý do (`qc_giong` → ASR lượt cuối, `qc_hinh` → VLM kiểm cảnh — cả hai là pha 28).
Hợp hai tập phải bằng chữ ký của `lap_ke_hoach`. Pha 28 nối thêm một nguồn thì
**phải** sửa bài này — khoảng trống không thể lặng lẽ quay lại. Đối chứng: nối
`qc_giong=[]` mà không sửa danh sách ⇒ **đỏ**.

### Không làm — và vì sao không phải "chưa kịp"

Đề bài còn gọi tên *vùng che* và *phụ đề*. Hai hạng này sinh ra từ các giai đoạn
**tất định** (`compose`, `render`): chạy lại cho ra **đúng byte cũ**. Một vòng sửa
tự động cho chúng là một tính năng giả — nó trả tiền để nhận lại đúng lỗi ấy. Sửa
chúng cần **đầu vào đổi**, tức khách sửa vùng/phụ đề trên một lần chạy **đã quyết
toán** rồi chỉ dựng lại `compose` → `render`. Mở lại một lần chạy đã quyết toán là
một luật tiền (ai trả cho lượt dựng lại và lượt QC bằng AI?) — việc của pha 30 phần
luật giá, ranh giới tiền giữ nguyên.

## Pha 30 — Billing + cost explainability: **MỘT PHẦN — phần chỉ đọc XONG**

### Đo trước

`quan_sat.tom_tat_cho_khach` tính sẵn chi phí cho khách từ V4 — giữ chỗ, đã tính,
chi phí **theo năng lực** (không theo tên nhà cung cấp), có test (`test_446`) — và
**không route nào gọi nó** (chỉ còn dấu trong `.pyc`). Khách trả tiền mà không thấy
mình trả cho việc gì; chỉ người vận hành thấy *"giữ · tính"*.

### Làm được gì — không một bút toán nào

* Trang chi tiết có khối **Chi phí**: *đã giữ khi tạo* · *đã tính* · *hoàn lại* +
  bảng *việc · khối lượng · credit*.
* **Hoàn lại chỉ hiện sau quyết toán**, cùng công thức `features.quyet_toan`
  (thu `min(thực tế, giữ)`); trước đó: *"phần chưa dùng được hoàn lại khi lần chạy
  kết thúc"* — một con số hoàn lại tính giữa chừng là một lời hứa sai.
* Nhãn tiếng Việt cho mọi năng lực tính tiền (`NHAN_NANG_LUC`); năng lực chưa có
  nhãn hiện *"Việc khác"*, **không** lộ mã nội bộ. `test_482` quét mã để mọi
  `nang_luc="..."` và mọi `ai.ThaoTac` đều có nhãn.

```
375 px, trình duyệt thật (lần chạy có sổ cái, đã quyết toán):
  Đã giữ khi tạo lần chạy: 5 credit · Đã tính: 5 credit · Hoàn lại: 0 credit
  Đọc lời lồng tiếng   420 ký tự    3
  Dịch                 1800 token   2
  Việc khác            1 lượt       0          không tràn ngang
```

Năm lần tiêm, năm lần đỏ; tệp trả nguyên byte.

### Không làm

*Luật giá* cho đa đích / đa người nói / cache / thử lại — mỗi cái là một **quyết
định tiền**, không phải một lượt code. Hai điểm đã có dữ liệu để quyết: pha 25 dùng
lại tách nguồn + chép lời mà vẫn giữ chỗ như lần tính; pha 29 cần luật cho lượt dựng
lại trên lần chạy đã quyết toán.

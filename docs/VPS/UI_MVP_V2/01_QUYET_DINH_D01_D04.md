# Bốn quyết định D-01…D-04 — phương án và căn cứ

**2026-08-26.** Chủ sản phẩm yêu cầu: *"những hạng mục cần quyết cần nghiên cứu
xây dựng logic thật tối ưu, tự đề xuất phương án tối ưu nhất, tham khảo từ
Vultr."*

Ba trong bốn hạng mục đã **quyết xong ở đây**. Một hạng mục còn lại chạm bút toán
credit và một hành động không đảo được trên hạ tầng đang trả tiền, nên nó ở lại
với chủ sản phẩm — đó là ranh giới đã chốt, không phải sự do dự.

---

## D-01 · Đặt tên máy — **LÀM**, theo mô hình *nhãn* của Vultr

### Vultr làm gì, và vì sao họ tách làm hai thứ

Vultr có **hai** trường, không phải một:

| Trường | Nó là gì | Ai đặt | Đổi được sau? |
|---|---|---|---|
| **Hostname** | tên **trong hệ điều hành** — Vultr ghi nó vào máy lúc dựng, qua cloud-init | Vultr ghi, khách chọn | đổi được, **nhưng phải khởi động lại** máy |
| **Label** | tên **trong bảng điều khiển** — thuần hiển thị | khách | đổi bất cứ lúc nào, **không chạm máy** |

Bỏ trống thì Vultr tự sinh (`vultr-guest`). DigitalOcean sinh dài hơn và mô tả
hơn (`ubuntu-s-1vcpu-1gb-nyc1-01` = ảnh + gói + vùng + số thứ tự).

### 🔑 Với ta, **chỉ có một nửa mô hình đó tồn tại** — và điều đó quyết định thiết kế

Khách **tự cài Windows từ đĩa ISO** (chốt 24/08). Không cloud-init, không
Cloudbase-Init, không sysprep. ⇒ Nền tảng **không có cách nào** đặt hostname bên
trong máy, và sẽ không bao giờ có chừng nào mô hình bán còn là "máy trống + đĩa cài".

⇒ **`VpsInstance.ten` là `label` của Vultr, và chỉ là thế.** Ghi thẳng điều đó
vào docstring của cột, vì cái tên `ten` không tự nói ra nó không phải hostname —
và một phiên sau sẽ đoán rằng nó là hostname rồi đi tìm chỗ ghi nó vào máy.

### Vì sao phải làm bây giờ, chứ không hoãn như một "tính năng"

Cột `ten` **đã tồn tại**, `nav.py` **đã hiện nó**, và ba ô xác nhận phá huỷ
**đã đòi gõ đúng nó**:

```python
if str(xac_nhan).strip() != (may.ten or may.id[:8]):     # cai_lai · khoi_phuc · xoa
```

Nhưng **không có đường nào đặt nó**, nên `may.ten` luôn rỗng và nhánh thật đang
chạy là `may.id[:8]` — **một chuỗi hex 8 ký tự**. Nghĩa là hôm nay, để xoá máy
của mình, khách phải chép tay `a3f9c1d0`.

Đó không phải một tính năng còn thiếu. Đó là **một cơ chế an toàn đang chạy ở
dạng tệ nhất của nó**: khuôn "gõ đúng tên" của GitHub hiệu quả vì cái tên **có
nghĩa với người gõ** — gõ `may-ban-hang` là một khoảnh khắc dừng lại để nhận ra
mình đang xoá cái gì. Chép một chuỗi hex thì không có khoảnh khắc đó; nó chỉ là
một thao tác chép–dán, tức đúng thứ mà rào chắn này sinh ra để ngăn.

⇒ **Sửa nó là làm cho rào chắn hiện có hoạt động đúng thiết kế**, không phải mở
rộng phạm vi.

### Phương án chốt

**1. Tên tự sinh, không bắt buộc nhập.** Bỏ trống ⇒ `vps-01`, `vps-02`… theo
**từng khách**, đánh số theo máy chưa xoá của chính họ.

Vì sao không chép khuôn DigitalOcean (`win2022-vpsvua-sg-01`): tên đó dài 20+ ký
tự và khách sẽ phải **gõ lại nó** trong ô xác nhận phá huỷ. Một tên xác nhận dài
là một tên bị chép–dán, và chép–dán thì rào chắn mất tác dụng. `vps-01` gõ được
bằng tay trong hai giây — **đó là lý do kỹ thuật để chọn tên ngắn, không phải gu
thẩm mỹ.**

**2. Ràng buộc, kiểm ở máy chủ:**

| Luật | Con số | Vì sao |
|---|---|---|
| độ dài | 2 … 40 | cột là `String(80)`; 40 là thừa chỗ, và giữ tên vừa một dòng thẻ máy |
| ký tự | chữ · số · `-` · `_` · khoảng trắng · dấu tiếng Việt | tên là **dữ liệu của khách**, không đi qua gettext (`test_304` đã chốt) |
| duy nhất | trong phạm vi **một khách**, tính trên máy **chưa xoá** | hai máy trùng tên làm ô xác nhận phá huỷ mơ hồ — đó là lý do an toàn, không phải lý do gọn gàng |
| chuẩn hoá | cắt khoảng trắng hai đầu, gộp khoảng trắng liên tiếp | `"may  A "` và `"may A"` phải là **một** tên, nếu không thì ô xác nhận từ chối một tên trông đúng |

**3. Đổi tên sau:** `POST /vps/{id}/doi-ten`, CSRF, chủ sở hữu, cùng khuôn
validate. **Không** đòi gõ xác nhận — đổi nhãn là việc đảo được, và đặt rào chắn
ở việc đảo được thì rào chắn ở việc không đảo được bị nhờn.

**4. Ô xác nhận phá huỷ:** giữ nguyên `may.ten or may.id[:8]`. Fallback ở lại cho
những máy tạo trước đợt này — nhưng sau đợt này **mọi máy mới đều có tên**, nên
nhánh hex thành đường chết chứ không phải đường chính.

⚠️ **Tên do khách đặt nên khách có thể đặt `a`.** Chấp nhận, và Vultr · GitHub ·
DigitalOcean đều chấp nhận: rào chắn này chống **bấm nhầm**, không chống một
người cố tình tự làm hại mình. Độ dài tối thiểu 2 là để tên còn là một cái tên.

**Thi hành:** ô nhập ở Đợt 3 (biểu mẫu tạo máy), nút đổi tên ở Đợt 4 (trang máy).

---

## D-02 · Một máy thật cho các hành trình vàng — **VẪN LÀ QUYẾT ĐỊNH CỦA CHỦ SẢN PHẨM**

Không đổi. Nó trừ credit thật (bút toán append-only, không xoá được) và tạo một
VM + một Reserved IP trên hạ tầng đang trả tiền — hai ranh giới đã chốt.

**Nhưng phạm vi cần tới nó đã hẹp lại**, nhờ D-03 dưới đây: sau khi bỏ nhu cầu
ảnh chụp màn hình, D-02 chỉ còn chặn **GJ3 · GJ4 · GJ5** (cài → nối → vận hành →
phục hồi). Đợt 1–7 chạy đủ mà không cần nó, và **D-03 không còn phụ thuộc nó**.

---

## D-03 · Ảnh chụp màn hình trình cài Windows — **KHÔNG DÙNG ẢNH. Dùng sơ đồ dựng từ dữ liệu**

Ảnh 4 có một ảnh chụp hộp thoại *"Where do you want to install Windows?"*.
Phương án ban đầu là chụp thật trên một máy thật ⇒ phụ thuộc D-02.

**Đó là câu trả lời sai, và nó sai theo bốn hướng cùng lúc:**

| Vấn đề của một ảnh bitmap | Hệ quả |
|---|---|
| Phải chụp trên máy thật | phụ thuộc D-02, tức phụ thuộc tiền |
| Mỗi bản Windows một giao diện khác (2016 · 2022 · 10 LTSC) | **năm** ảnh, hoặc một ảnh sai với bốn bản còn lại |
| Ảnh mang số liệu **cứng** (`80.0 GB`) | khách gói Nhỏ thấy `80.0 GB` trong khi máy họ có `40 GB` — sai đúng ở con số họ cần đối chiếu |
| Tài sản tĩnh mới | phải thêm vào `TAI_SAN_CO_VERSION`; quên là dính bẫy cache Cloudflare |

**Phương án tối ưu: dựng lại hộp thoại đó bằng HTML/CSS, lấy số từ `plan`.**

```
┌ Where do you want to install Windows? ──────────────┐
│  Name                         Total size  Free space│
│  ▸ Drive 0 Unallocated Space     40.0 GB    40.0 GB │   ← plan.disk_gb
└──────────────────────────────────────────────────────┘
```

Nó **đúng hơn một ảnh chụp**, không chỉ rẻ hơn:

- con số là **đĩa thật của khách** (`plan.disk_gb + dia_them_gb`), nên dòng
  *"Gói của bạn có 1 ổ NVMe 40 GB. Hệ thống sẽ hiển thị là Drive 0 Unallocated
  Space"* trỏ vào đúng thứ họ sắp nhìn thấy;
- không cần máy thật, không cần D-02;
- không tài sản tĩnh ⇒ không có gì để quên cache-bust;
- đọc được bằng trình đọc màn hình, và **dịch được** — một ảnh bitmap thì không,
  và `test_305` đòi bản EN sạch tiếng Việt.

⚠️ **Ràng buộc:** sơ đồ phải trông là **sơ đồ**, không giả làm ảnh chụp. Giữ chữ
tiếng Anh đúng như Windows hiện (`Drive 0 Unallocated Space`, `Next`, `Format`)
vì đó là thứ khách phải nhận ra trên màn hình, nhưng đóng khung nó bằng kiểu của
trang, không bắt chước khung cửa sổ Windows.

⇒ **D-03 đóng. Không cần chủ sản phẩm quyết, không cần D-02.**

---

## D-04 · Route *Ảnh chụp* và *Băng thông* — **KHÔNG MỞ. Nhưng bắt đầu ghi lịch sử NGAY HÔM NAY**

### Vultr có hai trang đó vì họ **có dữ liệu** cho chúng

| Trang của Vultr | Dữ liệu đứng sau |
|---|---|
| Bandwidth | đồ thị theo **ngày**, giữ nhiều chu kỳ — họ lấy mẫu và **lưu** |
| Snapshots | khách **tự chụp** bất cứ lúc nào, giữ **nhiều** bản, đặt tên, khôi phục theo bản |

### Ta có gì

| | Ta |
|---|---|
| Băng thông | **một** số cộng dồn cho chu kỳ hiện tại (`bang_thong_byte`), **về 0** mỗi lần thu tiền. **Không có bảng lịch sử.** |
| Ảnh chụp | **đúng một** bản, tự động **hằng tuần**, `sao_luu.GIU = 1`, khách không tự chụp được |

⇒ Một trang *"Chi tiết băng thông"* hôm nay sẽ hiện **đúng con số đã có trên
trang máy**. Một trang *"Quản lý snapshot"* sẽ hiện **một hàng**, với một nút đã
có sẵn trong khối Nguy hiểm. Cả hai là **trang trống mặc bộ trang**.

### 🔴 Nhưng có một việc phải làm ngay, và nó không phải giao diện

```python
# billing.thu_mot_chu_ky  — thứ tự hiện tại
may.paid_until = _moc_ke_tiep(may, thoi_diem)
_dat_lai_bang_thong(may)          # ← bang_thong_byte = 0
ghi_su_kien(db, may.id, "thu_phi", credit=gia, den=...)
```

**Mỗi chu kỳ trôi qua là một chu kỳ băng thông bị xoá vĩnh viễn.** Không có bản
sao, không có bảng, không có log. Ngày ta muốn dựng trang băng thông, lịch sử của
mọi khách sẽ bắt đầu từ **con số 0 của hôm đó** — và không có cách nào lấy lại.

Chi phí để không mất nó: **một dòng**. Sự kiện `thu_phi` đã được ghi ở đúng thời
điểm đúng, và `chi_tiet` là một `dict` tự do.

```python
da_dung = int(may.bang_thong_byte or 0)   # ĐỌC TRƯỚC khi đặt lại
...
ghi_su_kien(db, may.id, "thu_phi", boi="he_thong",
            credit=gia, den=may.paid_until.isoformat(),
            bang_thong_byte=da_dung)      # ← lịch sử, miễn phí
```

Không bảng mới, không di trú, không route mới, không đổi gì khách nhìn thấy.
Đổi lại: sau vài chu kỳ ta **có** dữ liệu thật để dựng trang đó — và trang đó khi
ra đời sẽ nói được điều duy nhất đáng nói: *"chu kỳ trước bạn dùng bao nhiêu"*.

⭐ **Đây là hình mẫu nên lặp lại: dữ liệu không chụp là dữ liệu mất vĩnh viễn,
còn giao diện thì lúc nào dựng cũng được.** Thứ tự đúng là ghi trước, vẽ sau.

### Chốt cho `nav.SAP_CO_MAY`

```python
SAP_CO_MAY = (
    ("bang_thong", N_("Băng thông")),     # GIỮ — từ nay có lịch sử để dựng
)
```

**Bỏ `anh_chup`.** Một bản ảnh chụp tự động hằng tuần **không cần một trang**;
nó cần một dòng trên trang máy (đã có) và một nút khôi phục (đã có). Để nó ở
dạng "sắp có" là hứa một trang mà chính ta không có lý do nào để xây — và
`nav.py` đã tự đặt luật cho mình: *"Bốn mục dưới đây có thật trong kế hoạch,
không phải chỗ giữ chỗ cho vui."*

Ngày nào cho khách **tự chụp** và giữ **nhiều bản** thì mục đó quay lại, cùng
với lý do của nó.

---

## Tổng kết

| # | Quyết định | Ai quyết | Vào đợt nào |
|---|---|---|---|
| **D-01** | Làm, theo mô hình *label* của Vultr; tự sinh `vps-01`; đổi tên được, không cần xác nhận | **đã quyết** | ô nhập → Đợt 3 · đổi tên → Đợt 4 |
| **D-02** | Một máy thật cho GJ3–GJ5 | ⏳ **chủ sản phẩm** | sau Đợt 7 |
| **D-03** | Không dùng ảnh; sơ đồ HTML/CSS lấy số từ `plan` | **đã quyết — đóng** | Đợt 5 |
| **D-04** | Không mở hai route; **ghi lịch sử băng thông ngay**; bỏ `anh_chup` khỏi "sắp có" | **đã quyết** | ghi lịch sử → **Đợt 1** · nav → Đợt 1 |

# BASELINE — App VPS tại `05464239` (Prompt 00)

> Ảnh chụp **đóng băng** hiện trạng trước khi chương trình VPS V2 sửa bất cứ dòng nào.
> Mọi khẳng định ở đây đọc được từ mã nguồn, kèm `tệp:dòng`. Không suy diễn.

## 1. Kiểm chứng snapshot của pack

```
master              = 9e73bf1f402c26525f1643761652cd5346359a9c   ← đúng SHA pack quan sát
HEAD (nhánh này)    = 05464239980c25de4cb316755efd41b27da7ddce   (288 commit sau master)
git diff 9e73bf1f..HEAD -- apps/vps   →  RỖNG
```

⇒ `apps/vps` tại HEAD **giống hệt** thứ pack đã quan sát. Mọi giả thuyết của pack còn nguyên.

## 2. Kiểm kê

**28 tệp Python, 6.457 dòng** trong `apps/vps/`:

| Tầng | Tệp | Dòng |
|---|---|---:|
| HTTP | `routes.py` | 900 |
| Worker | `jobs.py` | 686 |
| Việc nền | `bao_tri.py` | 394 |
| Driver Proxmox | `services/proxmox.py` | 360 |
| Điều khoản bán | `dieu_khoan.py` | 317 |
| Bảng CSDL | `tables.py` | 315 |
| Cấp phát | `services/provisioning.py` | 303 |
| Sức chứa | `services/capacity.py` | 284 |
| Router | `services/router.py` | 263 |
| Sổ sách | `services/billing.py` | 236 |
| Vultr | `services/vultr.py` | 205 |
| Cổng vào | `services/gateway.py` | 194 |
| Nhãn UI | `nhan.py` | 168 |
| Bảng giá | `cost.py` | 170 |
| Catalog OS | `os_images.py` | 160 |
| Mạng | `services/mang.py` | 174 |
| Tên máy | `ten_may.py` | 148 |
| Console | `services/console.py` | 154 |
| Ảnh chụp | `services/sao_luu.py` | 152 |
| Điều khiển | `services/dieu_khien.py` | 150 |
| Đối chiếu | `doi_chieu.py` | 139 |
| Định danh | `services/dinh_danh.py` | 127 |
| Điều hướng | `nav.py` | 124 |
| SSH | `services/ssh_lenh.py` | 105 |
| Băng thông | `bang_thong.py` | 101 |
| Manifest | `manifest.py` | 88 |
| còn lại | `__init__.py` ×2 | 40 |

**Bảng:** `VpsGateway` · `VpsIp` · `VpsInstance` · `VpsConsoleVe` · `VpsEvent` (`tables.py`).
**Job:** `vps.provision` · `vps.rebuild` · `vps.destroy` (`manifest.job_types`).
**Việc nền:** `bao_tri.chay` mỗi 3600 giây, dưới lease của nền tảng.
**Giao diện:** 7 template `server/templates/vps*.html` + `server/static/vps/`.
**Migration đã có:** 10 tệp `alembic/versions/20260822_1900_vps_tables` → `20260824_2500_vps_sao_luu`.
**Test đã có:** 18 tệp — `test_251,252,279,280,282,286,287,288,289,293,295,296,297,298,304,305,311,312`.

## 3. Truy vết mười hai luồng

| # | Luồng | Đường đi | Chờ tác vụ Proxmox? | Có khoá? |
|---|---|---|---|---|
| 1 | Tạo máy | `routes.tao_may` → job `vps.provision` → `jobs._tao_may` | ✅ cho `tao_may`; ❌ **không** cho `client.bat()` ở bước 5 | ✅ `_khoa_may` |
| 2 | Bật | `routes.bat_may` → `dieu_khien.bat` → `client.bat` | ❌ ghi `dang_chay` ngay | ❌ **không** |
| 3 | Tắt | `routes.tat_may` → `dieu_khien.tat` → `client.tat_mem` | ❌ ghi `da_tat` ngay | ❌ **không** |
| 4 | Khởi động lại | `routes.khoi_dong_lai_may` → `dieu_khien.khoi_dong_lai` → **`tat()`** | ❌ và **không bật lại** | ❌ **không** |
| 5 | Chụp ảnh | `bao_tri.chay` → `sao_luu.chup_va_don` | ❌ prune ngay sau POST | ✅ lease bảo trì |
| 6 | Khôi phục | `routes.khoi_phuc_may` → `client.tat_cung` + `client.khoi_phuc_anh` | ❌ cả hai | ❌ **không** |
| 7 | Cài lại | `routes.cai_lai_may` → job `vps.rebuild` → `jobs._dung_lai` → `_tao_may` | ✅ | ✅ |
| 8 | Xoá | `routes.xoa_may` → job `vps.destroy` → `jobs._xoa_may` | ✅ | ✅ |
| 9 | Treo / gia hạn / xoá quá hạn | `bao_tri.chay` → `billing.*` + `dieu_khien.treo` | ❌ `tat_cung` không chờ | ✅ lease bảo trì |
| 10 | Mạng / DHCP / NAT / IP công khai | `jobs._cap_ip_cong_khai`, `_tra_ip_cong_khai`, `_go_cho_dhcp` | n/a | ✅ (trong job) |
| 11 | Console | `routes.trang_console` + `cau_console` → `services/console.py` | n/a | n/a |
| 12 | Đối chiếu | `doi_chieu.quet` — **chỉ nói ra, không tự sửa** | n/a | n/a |

### Kết luận của bảng trên

Ranh giới rõ ràng: **thứ gì đi qua hàng đợi job thì đã chờ tác vụ và đã có khoá;
thứ gì chạy thẳng từ route thì không có cả hai.** Đó là một câu duy nhất giải thích
V-02, V-04 và V-07 cùng lúc — và nó nói rằng bản sửa đúng không phải là vá từng chỗ,
mà là **đưa bốn thao tác chạy thẳng vào cùng cái khuôn mà job đã có**.

## 4. Bảy phát hiện — bằng chứng

### V-01 · P0 · `khoi_dong_lai()` không khởi động lại

`services/dieu_khien.py:91-99` — toàn bộ thân hàm:

```python
def khoi_dong_lai(db, may, client, *, boi): 
    return tat(db, may, client, boi=boi)
```

Docstring nói *"tắt mềm rồi để khách tự bật lại"*. Nhưng nút trên giao diện tên là
**Khởi động lại**, và `nhan.SU_KIEN["khoi_dong_lai"]` ghi *"Máy khởi động lại"*.
Máy không bật lại, nhật ký nói nó đã khởi động lại.

Thêm một hệ quả: `_lam` được gọi với `ten_thao_tac="tat"`, nên nhật ký ghi **`tat`**
chứ không phải `khoi_dong_lai` — tức nhãn `SU_KIEN["khoi_dong_lai"]` **không bao giờ
được dùng tới**. Một chuỗi dịch chết trong catalog.

### V-02 · P0 · Ghi trạng thái ổn định ngay sau khi POST được nhận

`services/dieu_khien.py:63-70`:

```python
upid = goi(int(may.vmid))     # Proxmox mới NHẬN việc
...
may.trang_thai = trang_thai_moi    # ← ghi "đã xong" ngay tại đây
```

`upid` được ghi vào sự kiện nhưng **không ai đọc lại nó**. `grep trang_thai_tac_vu`
toàn kho chỉ ra **một** chỗ dùng: `jobs.py:157`.

Cùng khuôn ở `jobs.py:286-292`: `client.bat(may.vmid)` rồi `may.trang_thai = "dang_chay"`.

### V-03 · P0 · Ảnh chụp chưa xác minh đã được dọn và đã được ghi sổ

`services/sao_luu.py:122-131`:

```python
client.chup_anh(may.vmid, ten, ...)          # trả UPID, không ai chờ
cu = sorted(... client.danh_sach_anh(may.vmid) ...)   # hỏi ngay
for thua in cu[GIU:]: client.xoa_anh(...)             # xoá ngay
```

Ảnh mới chưa chắc đã hiện trong `danh_sach_anh`. Nếu chưa hiện: `cu` chỉ có bản cũ,
`GIU=1` giữ lại nó, nên **lượt này không mất gì**. Nhưng nếu chụp **thất bại** sau đó,
`bao_tri.py:213` vẫn ghi `may.sao_luu_luc = now` ⇒ máy khoe một ảnh **không tồn tại**,
và `den_han_chup` sẽ không chụp lại trong 7 ngày.

### V-04 · P0 · Khôi phục không chờ máy tắt

`routes.py:620-630`:

```python
try:
    client.tat_cung(may.vmid)
except ProxmoxError:
    pass                                 # ← nuốt cả lỗi thật
client.khoi_phuc_anh(may.vmid, ten_anh)  # ← gọi ngay
```

Cùng loại bẫy mà `jobs._xoa_may:616-620` **đã ghi rõ và đã sửa**: *"`tat_cung` là tác vụ
NỀN: gọi `xoa` ngay sau đó thì Proxmox trả 500"*. Đường khôi phục không học bài đó.

`except ProxmoxError: pass` còn nuốt luôn 401/403/500 — mọi lý do thật khiến máy chưa tắt.

### V-05 · P1 · Một cột gánh năm khái niệm

`tables.py:186` — `trang_thai: String(16)`, giá trị `dang_tao|dang_chay|da_tat|bi_treo|loi|da_xoa`.

Không biểu diễn được: *"nghiệp vụ đang hoạt động · mong muốn tắt · quan sát thấy đang chạy ·
tác vụ đang tắt"* — tổ hợp mà `CORE/TARGET_ARCHITECTURE.md` bắt buộc phải biểu diễn được.

Và không có mốc **quan sát lần cuối lúc nào**, nên "đang chạy" ghi tuần trước trông
giống hệt "đang chạy" đo một giây trước.

### V-06 · không phải lỗi

`manifest.py` — `lifecycle="development"` + `notes="Proxmox chạy LỒNG trong VMware"`.
Cả hai **đúng sự thật**. Giữ tới khi Prompt 11 có bằng chứng.

### V-07 · P0 · Bốn thao tác chạy thẳng không có khoá

`jobs.py:_khoa_may` giữ lease `vps-may:{id}` — nhưng nó chỉ bọc `handle()`, tức chỉ
job. `routes.py:462,469,476,586` gọi thẳng service, **không xin lease**.

Đường thật: khách bấm **Khôi phục** đúng lúc job `vps.rebuild` đang xoá VM cũ.
`_dung_lai` vừa gọi `client.xoa(vmid)`; route gọi `khoi_phuc_anh` trên cùng vmid.
Docstring của `_khoa_may` mô tả **đúng cảnh này** cho hai job — nhưng route không đi
qua cửa đó.

### V-08 · đã đạt — không sửa

`services/sao_luu.py` (docstring đầu tệp) và `proxmox.py:330-343` đã viết rõ ảnh chụp
nằm cùng kho, pool hỏng là mất cả hai, và crash-consistent — kèm phép đo thật 24/08.
Pack liệt kê cái này như một finding cần sửa; **HEAD đã đúng**.

## 5. Phụ thuộc nền tảng mà VPS thật sự dùng

| Dùng gì | Ở đâu | Ai gọi trong VPS |
|---|---|---|
| Hàng đợi job | `platform_core/jobs.py` | `routes.tao_may`, `cai_lai_may`, `xoa_may` |
| Lease singleton | `platform_core/leases.py` | `jobs._khoa_may`, `bao_tri` |
| Credit / sổ sách | `platform_core/credit.py` | `services/billing.py` |
| CSRF / phiên | `server/auth/csrf.py`, `session.py` | mọi route POST |
| Template | `server/templating.py` | mọi route GET |
| i18n | `platform_core/i18n.py` | `nhan.py`, template |
| Registry app | `platform_core/registry.py` | `manifest.py` |

Không tệp nào của VPS ghi vào `platform_core/`. Hợp đồng app còn nguyên.

## 6. Rủi ro đã thấy trước khi sửa

1. **Chuyển 4 thao tác sang hàng đợi job đổi hợp đồng UI.** Route đang trả 303 về trang máy với trạng thái đã đổi; sau khi đổi, trạng thái sẽ là "đang …" và trang phải tự làm mới. 4 template + `nhan.py` bị ảnh hưởng.
2. **18 tệp test đọc `trang_thai`.** Giữ cột chiếu (ADR-01) là điều kiện để không phải viết lại cả 18.
3. **Migration chạm bảng đang có dữ liệu production thật.** Phải backfill xác định, có `downgrade`.
4. **`String(16)`** — mọi giá trị trạng thái mới phải ≤16 ký tự, hoặc phải nới cột.
5. **Máy dùng chung 10 lõi.** Gate cuối (~11,4 phút) phải xin cửa sổ yên.

## 7. Prompt 01 cần gì

- Danh sách **mọi** chỗ đọc/ghi `trang_thai` (route, service, job, bảo trì, nhãn, template, test).
- Quy ước migration của kho: `alembic/versions/YYYYMMDD_HHMM_<ten>.py`, head hiện tại `20260908_1600_voice_license_va_curate`.
- Quyết định dải test: **550–599** (đo được là trống hoàn toàn).

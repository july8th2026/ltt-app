# B6 — CHUẨN HOÁ GĐ1/GĐ2: luật một trục thời gian

> Chủ dự án chốt 27/09: *"Nghiên cứu kỹ logic vận hành và các vận hành của Viral cho
> giai đoạn 2. Lấy tinh tuý."* → *"Triển khai kỹ #6"* → **"Cần nghiên cứu logic các
> bước của GĐ2 cho chuẩn luôn lần này. Chuẩn hoá logic GĐ1 và GĐ2."**

Tệp này là **hợp đồng** chia việc GĐ1/GĐ2. Dời `toc_do` (#6) là **hệ quả** của hợp
đồng, ⛔ không phải một quyết định riêng.

---

## 1. Chẩn đoán: kho có HAI phép đổi trục, và chúng SAI THỨ TỰ

Trong cả đường ống chỉ có **hai** phép làm `t_ra ≠ t_vao`:

| Phép đổi trục | Ở đâu hôm nay | Mang theo bản đồ nào |
|---|---|---|
| **CẮT** (`concat` các khoảng giữ) | GĐ2 | ⭐ `KeCat.ban_do()` — một **đối tượng bản đồ** tường minh, có test |
| **TỐC ĐỘ** (`setpts=PTS/toc`) | **GĐ1** | ⛔ ba lời gọi `moc_ban_ra` rải rác, ⛔ không bản đồ |

🔴 **Bệnh ⛔ không phải "tốc độ sai chỗ" — bệnh là tốc độ chạy TRƯỚC cắt.** GĐ1 đổi
trục **trước**, nên bản đồ của phép cắt (GĐ2) làm việc trên một trục mà **⛔ không
một kẻ quyết định nào nói**. Hệ quả: ba chỗ phải tự đổi trục bằng tay.

| Chỗ đổi trục bằng tay | Tệp | Đã sinh ra con bọ nào |
|---|---|---|
| `_ban_ghi_truc_ban_giao` | `giai_doan_ban_bien_tap.py:607` | `ci.canh` so với `ban_ghi` trên hai trục |
| `_khe_thoai_truc_ban_giao` | `giai_doan_hinh_anh.py:176` | cắt vào giữa câu thoại |
| `_thoi_luong_mong_doi` · `loc_tham_chieu(toc_do=)` | `giai_doan_qc.py` · `qc.py` | **T2** (chia `toc_do` hai lần) |

Cộng **T17** (mốc DTS trùng) — cũng sinh ra vì `setpts` ở GĐ1 ⛔ không khai nhịp ra.
⇒ **Bốn con bọ, MỘT bệnh.** Vá từng cái là vá triệu chứng.

---

## 2. HỢP ĐỒNG — hai luật, và mọi thứ khác suy ra từ chúng

### ⭐ Luật 1 (TRỤC) — mọi bước QUYẾT ĐỊNH ở trục NGUỒN; đổi trục là việc CUỐI

> Phép đổi trục phải **xếp sau** mọi phép đọc mốc thời gian, và mỗi phép đổi trục
> phải mang một **đối tượng bản đồ** tường minh — ⛔ không đổi trục bằng lời gọi rải.

Suy ra ngay: `edit_plan`, `ke_cat`, khe thoại, phụ đề, `ci.canh`, bản chép lời — tất
cả nói **trục nguồn**. Cắt rồi tốc độ là hai phép cuối, đúng thứ tự đó.

⇒ **`toc_do` thuộc cuối GĐ2.** Ba phép đổi trục bằng tay ở §1 **biến mất**, ⛔ không
phải chuyển chỗ.

### ⭐ Luật 2 (CHỖ ĐỨNG) — GĐ1 nói toạ độ NGUỒN, GĐ2 nói tệp ĐÃ XONG

> Một bước thuộc **GĐ1** khi và chỉ khi nó cần **từng khoảng nguồn, TRƯỚC `concat`**.
> Mọi bước khác thuộc **GĐ2**, và GĐ2 mã hoá lại **đúng MỘT lượt**.

| Bước | Thuộc | Vì sao — **kiểm được**, ⛔ không phải lịch sử |
|---|---|---|
| bản phối âm, chuẩn LUFS | GĐ1 | đã chuẩn âm một lần; cho qua `concat` lần nữa là trộn hai quyết định âm ở hai chỗ |
| `vung` (làm mờ/điền nền) | GĐ1 | toạ độ **NGUỒN**, đặt **trước** `concat`, trên **từng** khoảng |
| cắt cảnh (`ke_cat`) | GĐ2 | cắt trên tệp đã xong ⇒ giây hình 15 và giây tiếng 15 biến mất **cùng nhau** |
| `khung`/`zoom`/`cat_khung` | GĐ2 | hình học trên khung tệp đã xong (dời 25/09) |
| `diem_anh`/lật gương/dịch màu | GĐ2 | dời 25/09 |
| logo · lớp phủ · phụ đề | GĐ2 | dời 25/09 |
| **`toc_do`** | **GĐ2, CUỐI** | **#6 — nó là phép đổi trục, Luật 1 buộc nó xếp cuối** |

🔑 `toc_do` là **kẻ lạc đàn duy nhất**: cả họ `khung`/`zoom`/`lật gương`/logo/phụ đề
đã dời xuống GĐ2 hôm 25/09, riêng nó bị để lại ở GĐ1.

### Thứ tự trong chuỗi GĐ2 — mỗi mũi có một lý do kiểm được

```
trim/atrim + concat   ← CẮT (đổi trục #1, mang ban_do)
   ↓ khung            crop/scale/pad — TRƯỚC lật, để ⛔ không phải ánh xạ toạ độ crop qua gương
   ↓ diem_anh         lật gương, dịch màu — TRƯỚC logo, để ⛔ không lật logo của khách
   ↓ logo             chèn đè
   ↓ lop_phu          chữ
   ↓ phu_de (ass)     SAU CÙNG trong lớp nhìn: khách ĐỌC nó, logo/chữ chỉ trang trí
   ↓ TOC DO           ⭐ SAU CÙNG TUYỆT ĐỐI (đổi trục #2) — mọi bước trên đã đọc mốc xong
```

⭐ **Viral chốt đúng hình dạng này**: `xu_ly_video.py:1140` nối
`setpts=PTS/{speed}` **ngay sau** zoom + hflip trong **cùng** chuỗi, `atempo` ở chuỗi
tiếng (dòng 1179), ⛔ không bước cắt riêng. Ta có thêm phép cắt, nên tốc độ xuống
đuôi — cùng nguyên tắc, một nấc xa hơn.

---

## 3. Hai dữ kiện làm phép dời thành phép XOÁ RÒNG

1. **GĐ2 đã có cả hai dòng trong một `filter_complex`** — `loc_cat_hai_dong` xuất
   `[NHAN_HINH_RA]` + `[NHAN_TIENG_RA]`, `chay()` map cả hai
   (`giai_doan_hinh_anh.py:653`). Áp tốc độ = **nối vào đuôi**, ⛔ không dựng gì mới.
2. **GĐ2 đã tự soi tệp vào** — `nhap_media.soi(duong_vao)` (`:306`), mà `soi` chính
   là chỗ ghi `fps`/`fps_tb`/`vfr`. ⇒ `-r` của T17 lấy nhịp **miễn phí từ chính đầu
   vào**, ⛔ không phải luồn `fps_nguon` qua bản dựng như GĐ1 buộc phải làm.

---

## 4. Bản thay đổi

### Xoá
| Tệp | Xoá gì |
|---|---|
| `ket_xuat.py` | cả khối `ve_tieng` (`setpts` · `atempo` · `-r`) |
| `ban_dung.py` | `thoi_luong_ra = moc_ban_ra(...)` → `= tong_giay`; `hinh.bien_tap`; `fps_nguon` |
| `giai_doan_ban_dung.py` | `_bt_gd1`; `fps_nguon=`; ba trường nhịp của `NguonHinh` |
| `giai_doan_ban_bien_tap.py` | `_ban_ghi_truc_ban_giao` |
| `giai_doan_hinh_anh.py` | `_khe_thoai_truc_ban_giao` |
| `qc.py` | tham số `loc_tham_chieu(toc_do=)` (thêm 27/09, nay vô nghĩa) |

### Thêm
| Tệp | Thêm gì |
|---|---|
| `che_do_render.loc_cat_hai_dong` | nhận `toc_do`, nối `setpts`/`atempo` vào **đuôi** |
| `giai_doan_hinh_anh.dung_lenh` | `-r = fps_vao * toc`; `-t = thoi_luong_ra / toc` |
| `giai_doan_hinh_anh.chay` | `co_diem_anh` gồm `toc_do != 1` (⛔ để remux không nuốt tốc độ) |
| `giai_doan_hinh_anh.loc_bien_tap_gd2` | **giữ** `toc_do` thay vì bỏ |
| `giai_doan_hinh_anh.van_tay` | `toc_do` vào vân tay (⛔ để đổi tốc không dùng lại tệp cũ) |
| `giai_doan_qc` | thời lượng mong đợi = `ban_do().thoi_luong_ra / toc` — MỘT phép chia, MỘT chỗ |

---

## 5. Rủi ro đã biết, và phép đo bắt được nó

| Rủi ro | Phép đo |
|---|---|
| ⭐ **Remux nuốt tốc độ**: `khong_cat` true + `toc_do != 1` ⇒ `-c copy` ⇒ khách nhận tệp **⛔ không đổi tốc** | `khong_cat` phải false khi `toc_do != 1`; và đo thời lượng tệp ra |
| `-t` ⛔ không chia ⇒ tệp ra **cắt cụt** đúng hệ số tốc độ | thời lượng ra = `thoi_luong_ra / toc` ± 1 khung |
| T17 quay lại ở chỗ mới | khẳng định hợp chuẩn (`test_2064`) chuyển sang đo tệp **GĐ2** |
| `atempo` sau khi đã chuẩn LUFS | `atempo` ⛔ không đổi độ to; T4 (`lufs_giao`) vẫn đo |
| Vân tay thiếu `toc_do` ⇒ dùng lại tệp cũ | test vân tay đổi khi `toc_do` đổi |

---

## 6. Thi hành — đã xong, và nó là MỘT commit nguyên tử

⛔ **Không thể dời nửa trục.** Nếu GĐ2 áp tốc độ mà GĐ1 chưa thôi áp thì tệp bị đổi
tốc **hai lần**; nếu xoá phép đổi trục trước khi dời thì mọi mốc lệch. Nên năm bước
dưới đây là **một** commit, mỗi rủi ro một phép kiểm + một lần tiêm đỏ.

| Bước | Trạng thái |
|---|---|
| `loc_cat_hai_dong` nhận `toc_do`, áp ở **đuôi** (cả hai dòng) | ✅ |
| `dung_lenh` khai `-r = fps_vao × toc`, `-t = thoi_luong_ra / toc` | ✅ |
| GĐ1 thôi áp tốc độ; `loc_cat_noi` **NÉM** nếu bị truyền `toc_do` | ✅ |
| Xoá ba phép đổi trục bằng tay | ✅ |
| QC: một phép chia, một chỗ, cho **cả hai** nhánh | ✅ |
| Job thật trên worker, `toc_do = 1.25` | ⏳ |

## 7. Ba hệ quả ⛔ KHÔNG lường trước — cả ba đều là lỗ IM LẶNG

⭐ Đáng ghi lại vì cả ba cùng một hình dạng: **dời một phép đi để lại một chỗ vẫn
nhận dữ liệu mà ⛔ không còn ai dùng.**

1. **GĐ1 im lặng bỏ qua `bien_tap`.** `ban_dung.dung` vẫn *nhận* tham số ấy mà ⛔
   không làm gì ⇒ khách xin một phép mà ⛔ KHÔNG giai đoạn nào thực thi (GĐ2 đọc
   `cai_dat`, ⛔ không đọc bản dựng). ⇒ `dung()` **NÉM**.
2. **QC mất hệ số.** Nó đọc `toc_do` từ *artifact bản dựng GĐ1*, mà GĐ1 thôi ghi ⇒
   T15 so mọi dòng phụ đề với một độ dài ngắn hơn đúng hệ số tốc độ, T2 mong đợi
   sai. ⇒ `giai_doan_qc` + `giai_doan_qc_ai` đọc từ **`cai_dat.doc(run)`**, qua
   **cùng** `loc_bien_tap_gd2` mà GĐ2 dùng — một nguồn, một hàm lọc.
3. **Remux nuốt tốc độ.** Đường `-c copy` ⛔ không có bộ lọc nào ⇒ một lần chạy lọt
   vào đấy với `toc_do != 1` giao tệp **CHƯA đổi tốc** — ⛔ không lỗi, ⛔ không log.
   `co_diem_anh` đã chặn, nhưng đó là phép chặn ở **chỗ gọi**, và một phép chặn ở
   chỗ gọi là phép chặn ai cũng có thể quên. ⇒ `dung_lenh` **NÉM** khi cả hai sự
   thật cùng tới: bất biến thuộc về **BIÊN**.

## 8. Phép đo

### Chuỗi hai giai đoạn, ffmpeg thật (`test_2064`)

```
GĐ1: 8,000 s · chớp sáng 4,00 s              ⇐ GĐ1 ⛔ KHÔNG đổi mốc
GĐ2: 6,400 s · chớp 3,20 s · bíp 3,20 s · A/V 0,00 ms · 0 mốc trùng
QC : T1 T2 T7 T11 T15 T16 = DAT
```

### Ca CẮT **và** ĐỔI TỐC cùng lúc — ca `test_2064` ⛔ không phủ

Bài trên giữ `[0, 8)`, tức bản đồ cắt là phép **đồng nhất** ⇒ nó ⛔ không thể phát
hiện một phép hợp thành sai giữa *cắt* và *đổi tốc*. Đo riêng (nguồn 12 s / 25 fps,
chớp 9,0–9,4 s, giữ `[0,4)` + `[8,12)`):

| trường hợp | dài | chớp | lệch | lỗi DTS |
|---|---|---|---|---|
| ⛔ không đổi tốc | 8,000 s | 5,000 s | **+0,0 ms** | **0** |
| `toc_do = 1,25` | 6,400 s | 4,000 s | **+0,0 ms** | **0** |

⇒ Đã thành phép kiểm thật (`test_CAT_VA_DOI_TOC_cung_luc__...`).

### Bảng `-r`, đo trên fixture 25 fps (chớp phải ra 3,200 s)

| nhịp khai (`-r`) | lệch chớp | trôi A/V | lỗi DTS | khung |
|---|---|---|---|---|
| `passthrough` | 15,9 ms | 15,9 | 40 | 199 |
| ⛔ không khai (`auto`) | 40,0 ms | 55,9 | 0 | 159 |
| 25 = nhịp vào | 80,0 ms | 95,9 | 0 | 159 |
| **31,25 = vào × toc** | **0,0** | **15,9** | **0** | **199** |
| 30 | 66,7 ms | 82,5 | 0 | 191 |

⚠️ Đề xuất *"fps đầu vào = đầu ra"* bị **bác**: `-r 25` làm nội dung **trễ 80 ms**
— tệ hơn cả việc ⛔ không khai gì — vì CFR buộc phải **bỏ khung**.

## 9. Một bài ĐỎ SẴN trên `main`, ⛔ không phải của B6

`test_2011::test_preset_CAT_do_that_VMAF_den_dong_va_giai_ma` đỏ (`QC: pending`).
Đo bằng cây tạm: đỏ ở **cả `270a659f` và `cff52e84`** — cũ hơn cả T17. ⛔ Chưa truy
nguyên; ghi lại làm một mục riêng.

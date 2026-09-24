# L_FIX_AUTO_MATCH — R-01: AUTO_MATCH từ đường CHẾT thành đường CHẠY

Làn `fix-auto-match`, nhánh `phien/asv-final-fix-auto-match`, gốc `29aaacd8` · 23/09/2026.
Bằng chứng mở lỗi: `bang_chung/NEN_V3.md` lượt A — `localize_preserve_picture` +
`AUTO_MATCH` + phim khách thật, chết ở `content_process` với `ChuaRangError` **sau
133 giây demucs + ASR đã trả tiền**.

## 1. Lỗ hổng, đo lại cho đúng

Ba tầng, và bản vá phải chạm cả ba:

1. **Không ai sinh `HoSoNoiDung`.** `hieu_canh.doc_ho_so` / `loi_nhac_ho_so` tồn tại
   từ pha 11 nhưng **chưa bao giờ có người gọi** — `test_453.MO_COI_DA_BIET` ghi đúng
   điều đó. Nên `dac_diem_giong` luôn rỗng ⇒ `co_du_de_khop` sai ⇒ `CHUA_RANG` ⇒
   `ma_giong()` ném.
2. **Preset giữ hình không có chỗ nào để sinh nó.** `edit_plan` của
   `localize_preserve_picture` là một đường rẻ tiền có chủ đích (0,0 s trong lượt
   thật): một chỉ mục một-cảnh, không khung hình, không gọi model. Mọi bản vá đi
   qua VLM sẽ xanh ở `smart_localize` và vẫn chết ở preset **mặc định**.
3. **"Hoãn lại" chưa bao giờ tồn tại.** `can_cho_ho_so` — hàm mô tả việc điều phối
   hoãn một lần chạy `AUTO_MATCH` — **không có người gọi nào trong `apps/`**, chỉ
   trong test. Không có logic hoãn nào ở `jobs.py`/`thi_hanh.py` cả. Hành vi thật
   là một lần chết cứng ở `content_process`, không phải một lần hoãn.

Và hai lỗi nữa lộ ra khi nối mạch (không giai đoạn nào từng chạy nên không ai thấy):

* `ai.HO_SO_NOI_DUNG` khai `can_thi_giac=True` — nhưng `loi_nhac_ho_so` **không gửi
  một khung hình nào**. Một thao tác thuần văn bản đòi model thị giác: đắt hơn,
  hiếm hơn, và không bao giờ dùng được ở preset không đọc cảnh.
* `doc_ho_so(noi_dung: str)` bóc `noi_dung` bằng tay ⇒ mất `finish_reason` — đúng
  lỗi `doc_hieu_canh` đã chịu ngày 09/09. `test_434` bắt được ngay khi người gọi
  đầu tiên xuất hiện.
* `giai_doan_noi_dung` báo cáo `nguon_giong` từ `can_cu["nguon"]`, nhưng `nguon` là
  một **trường** của `KetQua`. Cột đó rỗng ở **mọi** lần chạy từ trước tới nay.

## 2. Hồ sơ được dựng từ cái gì — nói thẳng

Hai nguồn, cả hai nằm **trước** `edit_plan`, nên hai preset đi đúng một đường:

| Mặt | Nguồn | Loại |
|---|---|---|
| `gioi` | **F0 trung vị** của stem `vocals` (demucs) | **đo được** |
| `phong_cach` | một lần gọi model **văn bản** trên bản chép lời | suy đoán |
| `vung` | (nt) — gần như luôn rỗng, xem dưới | suy đoán |
| `the_loai`, `giong_dieu`, `khan_gia`, `nhip`, `tom_tat` | (nt) | mô tả, không dùng để lọc |

* **`gioi` đo, không đoán.** Đo bằng `torchaudio.functional.detect_pitch_frequency`
  (bản cài sẵn của thư viện) — không tự viết bộ đo cao độ. Ngưỡng nam/nữ 165 Hz kèm
  **vùng xám ±15 Hz** (khoảng nam ~85–180 và nữ ~165–255 chồng nhau; Baken &
  Orlikoff 2e). Trong vùng xám: **không khai gì**.
* **Đo ở tiến trình con demucs**, không ở worker: `torch` đã nằm sẵn trong bộ nhớ
  tiến trình đó, và `giai_doan_am_thanh` **xoá** `vocals` ngay khi nó trả về. Thứ đi
  lên là **một con số** (`f0_trung_vi` trong JSON của runner → `tom_tat` của
  `audio_prepare`), không phải một tệp tiếng.
* **Một lần gọi model VĂN BẢN**, không VLM, không khung hình, không cảnh. Preset giữ
  hình không phải trả thêm một giây `edit_plan` nào — có phép kiểm chốt
  (`so_canh_da_doc == 0`).
* **`vung` gần như luôn rỗng** và đó là đúng: nó là giọng vùng miền **tiếng Việt**;
  một phim tiếng Trung không mang thông tin nào về nó.

### Giới hạn đã biết (viết ra để không ai tưởng nó không có)

1. **Lỗi quãng tám.** Bộ đo là họ tự tương quan; trên một âm **không phải tiếng nói**
   nó có thể bắt vào chu kỳ bội — đo được: sin 440 Hz + hoạ âm → ~219 Hz, rơi vào
   khoảng "nữ". Cái chặn nó là **đầu vào**: thứ đi vào là stem `vocals`, nên video
   không có giọng người cho ra stem gần như im lặng ⇒ cửa năng lượng trả `0.0`.
   `test_2009` chốt hành vi này bằng tên bài nói rõ đây là một **giới hạn**.
2. **Một con số cho cả video.** Hai người nói cho ra trung vị ở giữa. Hợp đồng sản
   phẩm 22/09 là **một giọng thuyết minh mỗi lần chạy**, nên một con số là đúng đơn
   vị — nhưng nó không trả lời được "ai nói câu nào".
3. **Bịt dải tìm làm hỏng phép đo.** Ép `freq_low`/`freq_high` về đúng khoảng tiếng
   nói nghe hợp lý nhưng đo 23/09 cho kết quả ngược: 240 Hz sai, 440 Hz → 147 Hz
   (chia ba), 500 Hz lọt vào khoảng người. Giữ dải mặc định, **lọc kết quả** sau.

## 3. D-V4-04 không bị nới một chút nào

`CHUA_RANG` vẫn là một trạng thái thật: không đo được **và** model không trả lời
được ⇒ hồ sơ rỗng ⇒ lần chạy **dừng lại**, không rơi về giọng mặc định.
`test_2008::test_khong_du_can_cu_thi_DUNG_LAI...` dựng đúng cảnh đó trên chuỗi thật
và chốt rằng không một mã giọng nào được ghi lên lần chạy.

Cái đổi là **câu lỗi**: `rang_giong.vi_sao_chua_rang` phân biệt "không giọng nào
khớp" với "chưa nhận ra giọng người nói", cả hai đều chỉ khách lối ra (tự chọn một
giọng) — thay cho một câu nói về "hồ sơ nội dung", thứ khách không biết là gì.

### Nới lỏng — và vì sao nó không phải "lấy đại một cái"

20 giọng mẫu phủ 13 tổ hợp, nên một hồ sơ ba mặt đúng tuyệt đối ("nữ, miền Trung,
tin tức") vẫn có thể ra không ứng viên nào. `rang_noi_long` bỏ dần mặt **ít cứ**
nhất, theo `THU_TU_NOI_LONG = ("phong_cach", "vung")`:

* `phong_cach` bỏ trước — `giong_mau` ghi rõ nó là *nhãn mô tả giọng, không phải nút
  vặn* (*"Style is deprecated on v3 Turbo"*), và là mặt model đoán yếu nhất;
* `vung` bỏ sau — xem trên;
* ⛔ **`gioi` không bao giờ bị bỏ.** Bỏ nốt nó thì phép lọc trả về cả catalog, và
  "lấy cái đầu tiên của cả catalog" chính là giọng mặc định đổi tên.

Hết mặt mà vẫn không khớp ⇒ `CHUA_RANG`, `can_cu` ghi `mat_da_noi_long` để màn hỗ
trợ nói được đã bỏ gì.

## 4. Lỗ hổng thứ hai: ghi hồ sơ suýt đốt lại đúng 133 giây ấy

Hồ sơ được ghi vào `run.settings["dac_diem_giong"]` — chỗ `dich_vu_tao.KHOA_NHAN`
đã chừa sẵn (*"chưa cửa nào sinh ra nó"*) — để giọng **ổn định qua các lượt chạy
lại**: vân tay của `content_process` có `ma_giong` trong đó, nên một hồ sơ sinh lại
mỗi lượt có thể chọn ra giọng khác ⇒ **mọi** điểm chốt đã trả tiền hết tính.

Nhưng `thi_hanh.van_tay` gộp **cả** `run.settings` vào vân tay giai đoạn, và
`jobs._vo_hieu_giai_doan_da_lech` đặt lại mọi giai đoạn lệch. Bản nháp đầu in ra:

```
WARNING asv: run asvr_706 dat lai 5 giai doan do lech van tay:
        audio_prepare,content_process,edit_plan,media_prepare,transcribe
```

Tức demucs + ASR chạy lại từ đầu — đúng khoản NEN_V3 lượt A đã đốt, đốt theo một
cách khác. `cai_dat.KHOA_DAN_XUAT` loại `dac_diem_giong` + `ho_so_noi_dung` khỏi vân
tay giai đoạn. Không mất phép vô hiệu nào: giọng đã chốt đi vào vân tay **của bản
lồng tiếng** (`long_tieng.van_tay_long_tieng`), và `giai_doan_giong` đọc giọng từ
chính bản lồng tiếng chứ không đọc `settings`.
`test_2008::test_ghi_ho_so_KHONG_dat_lai_demucs_va_ASR` chốt bằng một lần chạy thật.

## 5. Tệp đã đổi

**Mới:** `apps/auto_scan_video/cao_do.py` (đo F0 + ngưỡng giới) ·
`apps/auto_scan_video/ho_so_noi_dung.py` (dựng hồ sơ, từ vựng catalog, ghi xuống
`settings`).

**Sửa:** `rang_giong.py` (`rang_noi_long`, `THU_TU_NOI_LONG`, `vi_sao_chua_rang`) ·
`giai_doan_noi_dung.py` (dựng hồ sơ ngay trước khi viết lời, trả `nguon` riêng) ·
`hieu_canh.py` (`loi_nhac_ho_so` chạy được khi **không có cảnh nào**, khai từ vựng
`phong_cach`; `doc_ho_so` nhận cả `kq`) · `ai.py` (`HO_SO_NOI_DUNG.can_thi_giac` →
`False`) · `cai_dat.py` (`KHOA_DAN_XUAT`, `cho_van_tay`) · `thi_hanh.py` (vân tay
dùng `cho_van_tay`) · `demucs_runner.py` + `giai_doan_am_thanh.py` (đo và mang
`f0_trung_vi` lên) · `gia.py` (bỏ câu "đang được hoàn thiện") · `loi.py` (chú thích
phân loại `ChuaRangError` đã cũ) · `locale/en` (4 msgid mới, dịch tay).

**Bộ đỡ:** `tests/fixtures/asv_media.py` (`phan_hoi_ngoai_dich` trả lời
`HO_SO_NOI_DUNG` bằng **từ vựng catalog**) · `tests/fixtures/asv_e2e.py` (nhận ra
thao tác theo **hình dạng gói tin**; bản cũ trả ba mặt **phẳng** ở gốc và
`phong_cach: "than_mat"` — hai lỗi im lặng, cả hai không lộ vì thao tác chưa có
người gọi).

## 6. Phép kiểm

| Tệp | Đo gì |
|---|---|
| `test_2006` | dựng hồ sơ: từ vựng catalog, bằng chứng tất định, **đo thắng đoán**, model hỏng vẫn còn phần đo được, hỏng cả hai ⇒ hồ sơ **rỗng** |
| `test_2007` | `rang_noi_long`: tổ hợp không có trong catalog vẫn chốt; thứ tự nới lỏng; `gioi` không bao giờ bỏ; `CHUA_RANG` vẫn thật; `can_cho_ho_so` luỹ đẳng |
| `test_2008` | **chuỗi thật, hai preset** — giọng được chốt, `nguon_giong == tu_khop`, mã giọng thuộc catalog; preset giữ hình **không** trả tiền một lượt đọc cảnh; không đủ căn cứ ⇒ dừng; không gọi model lần hai; **không đặt lại demucs/ASR** |
| `test_2009` | phép đo F0: đúng trong khoảng tiếng nói, gộp kênh, im lặng ⇒ `0.0`, tệp hỏng ⇒ `0.0`, vùng xám, **lỗi quãng tám được khai thật**, con số đi từ tiến trình con lên `outputs` |

Đã sửa theo bánh cóc: `test_453` (ba tên **ra khỏi** `MO_COI_DA_BIET` bằng cách được
nối vào mạch) · `test_447` (**lật chiều**: mô tả `AUTO_MATCH` không còn được nói là
chưa xong) · `test_427` (`REBASE_MAP_V4.md` + `cao_do.py`) · `test_437` (`doc_ho_so`
nhận `kq`) · `test_2050` (chữ ký `_giong_da_chot`).

Chạy `pytest -k asv -n 6`: **1929 xanh**, 4 đỏ — cả 4 **đã có sẵn ở `29aaacd8`**,
xác minh bằng một worktree ở gốc, cùng thông điệp từng chữ:
`test_2021::test_CHO_CAM_metricx_mot_module_la_du` ·
`test_432::test_chi_MOT_cho_trong_app_goi_giu_cho` (`thi_hanh.py` đã gọi
`cache_chung.giu_cho` từ trước) · `test_448` hai bài (báo cáo nghiệm thu cũ:
thiếu `qc_do_luong`, `chep_loi/1` vs `/2`).

## 7. Còn lại cho điều phối

* `tools/check_i18n.py` đỏ ở `apps/auto_scan_video/ngon_ngu.py` và `phu_de.py` — **hai
  tệp làn này không chạm**, đỏ sẵn ở gốc.
* `tools/check_dich_thieu.py` **PASS** (319/327). Không hạ mốc: `check_dich_thieu.moc`
  là tệp dùng chung, và làn khác có thể đang thêm chuỗi.
* Hồ sơ hiện **không** dùng `tom_tat_chi_muc` và **không** đọc cảnh, kể cả ở
  `smart_localize` — nơi bằng chứng cảnh đã được trả tiền rồi. Đó là một lựa chọn
  **đối xứng hai preset**, không phải một giới hạn kỹ thuật: nếu muốn hồ sơ giàu hơn
  ở preset cắt, truyền `cac_canh` vào `ho_so_noi_dung.dung` là đủ — nhưng khi đó hai
  preset sẽ chọn giọng theo hai bộ bằng chứng khác nhau, và điều đó phải là một
  quyết định của chủ sản phẩm chứ không phải một dòng mã.
* Chưa đo trên phim khách thật. Lượt `NEN_V3` lượt A cần chạy lại để đóng R-01 bằng
  bằng chứng vận hành, không chỉ bằng bộ đỡ.

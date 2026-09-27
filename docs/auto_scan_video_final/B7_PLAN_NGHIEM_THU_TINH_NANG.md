# B7 — Nghiệm thu TÍNH NĂNG trên job thật: bậc thang 3 tầng

> Chủ dự án chốt 27/09: *"Thực tế logic vận hành, code của ta đã có hết những hạng
> mục đó rồi, giờ cần test thực tế vận hành thực sự… Nên làm full 1 video hay chia
> ra các video khác skill?"* → chọn **C. bậc thang 3 tầng** · **chỉ phim Trung thật**.

---

## 1. 🔴 Ràng buộc chặn mọi thứ: worker chỉ nạp mã ĐÃ DEPLOY

```
nssm get LTTStudioWorker AppDirectory  ->  C:\LTTPlatform\app
grep -c loc_toc_do_hinh C:\LTTPlatform\app\...\che_do_render.py  ->  0
grep -c loc_toc_do_hinh D:\LTTSTUDIOSAPP\...\che_do_render.py    ->  2
```

⇒ **Một job "thật" đo bản ĐÃ DEPLOY, ⛔ không đo cây đang làm.** Đo được 27/09 bằng
một sai sót thật: tôi chạy `asvr_7e55f87c` tưởng là nghiệm thu B6, nó đo mã cũ.

⭐ Nên thứ tự **buộc phải** là: `deploy` → `job test`, ⛔ không phải ngược lại. Và
mọi lần sửa mã cần nghiệm thu chạy-thật đều phải deploy lại. Đây là **trần cứng**
cho mọi pha nghiệm thu qua hàng đợi job, ⛔ không riêng ASV.

⚠️ Hệ quả thứ hai: **deploy khởi động lại worker** ⇒ nó **phá phép đo đang bay**.
Một job đang chạy khi deploy là một phép đo **biến mất**, ⛔ không phải đỏ.

---

## 2. Bề mặt tính năng — đọc từ mã, ⛔ không kể từ trí nhớ

| Trục | Giá trị | Nguồn |
|---|---|---|
| `preset` | `smart_localize` · `localize_preserve_picture` | `hop_dong_v4.PRESET` |
| `bien_tap` | `toc_do` (≤1,5) · `cat_khung` · `zoom` · `khung` · `lat_guong` · `dich_mau` | `bien_tap._TRUONG` |
| `khung` | tỉ lệ `16:9`/`9:16`/`1:1`/`4:5` × cách `cat`/`nen_mo` | `bien_tap.TI_LE`, `CACH_KHUNG` |
| `vung` | `lam_mo` (làm mờ chữ cũ) · `dien_nen` · `danh_dau_phu_de` | `vung_che.LOAI_*` |
| `logo` | `x`,`y`,`rong`,`do_mo` (phân số) | `logo.chuan_hoa_mot` |
| `lop_phu` | `chu`,`x`,`y`,`co_chu`,`mau`,`do_mo`,`vien` | `lop_phu.chuan_hoa_mot` |
| `phu_de` | chế độ · kiểu · đốt vào hình (`.ass`) hay `.srt` rời | `phu_de.chuan_hoa` |
| `cat` | cửa sổ cắt đầu/cuối của khách | `cat_dau_cuoi` |
| giọng | `che_do_giong` · `giong` | `dich_vu_tao` |

⛔ **⛔ Không phải 2⁹ tổ hợp.** Hai ràng buộc thu hẹp mạnh:
- `localize_preserve_picture` **cấm** mọi biên tập (hứa sao chép nguyên vẹn);
- `cat_khung` / `zoom` / `khung` là **hình học**, chồng nhau về ý nghĩa.

---

## 3. Vì sao bậc thang, ⛔ không phải "một job một tính năng"

🔑 **Chín trục ấy ⛔ không độc lập — chúng dùng CHUNG một chuỗi lọc GĐ2:**

```
cắt → khung → điểm ảnh (lật/màu) → logo → chữ → phụ đề → tốc độ
```

⇒ *"Một job một tính năng"* chứng minh **từng bước** chạy, nhưng ⛔ **không** chứng
minh **hợp thành**. Mà `T2`, `T17`, `B6` — cả ba con bọ đắt nhất — **đều là lỗi hợp
thành**: mỗi bước đúng riêng, sai khi xếp cạnh nhau.

⭐ Và thứ tự ấy có **lý do kiểm được**, nên nó là thứ đáng đo nhất: `khung` trước
`lật` (⛔ để không phải ánh xạ toạ độ crop qua gương) · `lật` trước `logo` (⛔ để
không lật logo của khách) · phụ đề sau cùng trong lớp nhìn · **tốc độ sau tuyệt
đối** (B6).

---

## 4. Ba tầng

### T1 — HỢP THÀNH (2 job)

**T1a · `smart_localize`, bật HẾT những gì bật được cùng lúc** — 9 trục, 1 job:

```json
{ "preset": "smart_localize",
  "bien_tap": { "toc_do": 1.25, "khung": {"ti_le": "9:16", "cach": "cat"},
                "lat_guong": true, "dich_mau": {...} },
  "vung":  [ {"loai": "lam_mo", ...} ],
  "logo":  [ {"x": 0.04, "y": 0.04, "rong": 0.18, "do_mo": 0.9} ],
  "lop_phu": [ {"chu": "LTT", "x": 0.5, "y": 0.9, "vien": true} ],
  "phu_de": { "che_do": "tu_dong", "dot_vao_hinh": true },
  "cat": { "tu": 0.05, "den": 0.95 } }
```

⭐ **Vì sao "đỏ thì nhiều nghi phạm" ⛔ không phải phản bác:** chín trục này **phân
biệt được bằng chính đầu ra** — logo ở góc, làm mờ ở vùng, chữ ở đáy, tỉ lệ ở
`ffprobe`, tốc độ ở thời lượng, màu ở histogram. Một lượt đỏ thường **tự chỉ ra**
trục nào.

**T1b · `localize_preserve_picture`** — trục T1a ⛔ không phủ nổi (preset này **cấm**
biên tập). Nó đo đường `-c copy`: hình **nguyên vẹn từng byte**, phụ đề ra `.srt`
rời, và `-shortest` ⛔ không được có.

### T2 — CÁC TRỤC LOẠI TRỪ NHAU VỚI T1a (2 job)

- **T2a**: `cat_khung` + `zoom` (thay `khung`) — hình học kiểu khác.
- **T2b**: `vung.dien_nen` + `vung.danh_dau_phu_de` — hai loại vùng còn lại;
  `dien_nen` đổi **bố cục khung** nên ⛔ không đứng cùng `khung` được.

### T3 — CHỈ chạy khi T1 đỏ

Chia đôi theo chuỗi lọc: bỏ nửa sau (logo/chữ/phụ đề/tốc độ) → còn đỏ thì lỗi ở
nửa trước. `log₂(9) ≈ 4` job xấu nhất, thường 1–2.

⇒ **Giá: 4 job nếu xanh. Chỉ trả giá chẩn đoán KHI có lỗi.**

---

## 5. Phim: chỉ phim Trung THẬT — và cách bù nhược điểm của nó

Chủ dự án chọn **chỉ phim thật** (`tests/fixtures/asv_e2e_that/`). Nó **bắt buộc**
cho: làm mờ **chữ cũ thật** · ASR/dịch/TTS · độ to trên tiếng thật · phụ đề trên
thoại thật. Một video dựng ⛔ không trả lời được những thứ đó.

⚠️ Nhược điểm: ⛔ không có mốc dựng sẵn ⇒ hình học dễ "trông có vẻ đúng".

⭐ **Bù bằng cách chọn ĐẠI LƯỢNG, ⛔ không bằng cách đổi phim** — đo **bất biến dẫn
xuất** thay cho mốc:

| Trục | Đo gì (chính xác, trên phim thật) |
|---|---|
| `khung` / `cat_khung` / `zoom` | `ffprobe` kích thước ra — **số nguyên**, ⛔ không phán đoán |
| `cat_khung` đúng vùng | băm vùng đã cắt so với **đúng vùng ấy trích độc lập từ nguồn** |
| `lat_guong` | so khung ra với khung nguồn **đã lật bằng ffmpeg** |
| `dich_mau` | histogram / `signalstats` trung bình từng kênh |
| `vung.lam_mo` | phương sai Laplace **trong** vùng so **ngoài** vùng, cùng khung |
| `logo` | vị trí + bề rộng logo bằng khớp mẫu trên khung ra |
| `lop_phu` | OCR hay khớp mẫu chữ ở đúng `(x, y)` |
| `phu_de` | số dòng + mốc trong `.srt`; nếu đốt: OCR đáy khung |
| `toc_do` | thời lượng + **vị trí nội dung** + mốc DTS (như B6) |
| độ to | `ebur128` trên tệp giao |

---

## 6. Thứ tự thi hành

```
1. deploy (bắt buộc TRƯỚC, luật §1)     -> /health/version khớp SHA
2. T1a + T1b                             -> 2 job, đo theo bảng §5
3. T2a + T2b                             -> 2 job
4. T3 chỉ khi T1 đỏ                      -> chia đôi
5. ghi sổ lỗi + nhật ký; lỗi nào sửa được thì sửa -> deploy lại -> chạy lại ĐÚNG job đã đỏ
```

⛔ **Một job đang chạy khi deploy là một phép đo BIẾN MẤT** (§1). Nên ⛔ không bao
giờ deploy giữa lúc một job nghiệm thu đang bay.

⭐ Và **đối chứng trước-B6 đã có**: `asvr_7e55f87c` (phim Trung 190 s, `toc_do=1.25`)
chạy trên bản deploy `3c90e775` — tức **trước** B6. Sau khi deploy B6, chạy lại
**cùng phim cùng cấu hình** cho một phép so trước/sau like-for-like.

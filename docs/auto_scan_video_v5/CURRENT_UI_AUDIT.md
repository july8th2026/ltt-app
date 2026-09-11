# CURRENT_UI_AUDIT — giao diện Auto Scan Video hôm nay

> Artifact 1/5 của chương trình **GUI V5**. READ-ONLY: không dòng mã sản phẩm nào
> bị sửa để viết tệp này.
>
> - Cây đo: `D:\LTTSTUDIOSAPP\.claude\worktrees\auto-scan-video-v4-mvp-7173d9`
> - Nhánh: `phien/asv-v4` · SHA `9d7f7044`
> - Ngày đo: 2026-09-07

---

## 0. Kích thước thật của bề mặt đang có

Đây là con số quan trọng nhất trong tệp này, vì nó định lại quy mô của cả
chương trình V5:

| | dòng |
|---|---|
| `templates/asv_trang_chinh.html` | 103 |
| `templates/asv_chi_tiet.html` | 55 |
| `templates/asv_tien_do.html` | 59 |
| **Tổng HTML của toàn bộ sản phẩm** | **217** |
| `routes.py` | 428 (7 handler — trần hợp đồng là 900 dòng / 30 handler) |

Không có tệp JS riêng. Không có CSS riêng của app. Tương tác động duy nhất là
một thuộc tính `hx-trigger="every 3s"` của htmx trong `asv_tien_do.html:12`.

⇒ **GUI V5 không phải một lần tái cấu trúc. Nó là lần đầu tiên app này có giao
diện.** Mọi câu trong prompt V5 nói "refactor GUI shell" nên đọc là "xây".

---

## 1. Bảng bề mặt

Cột **Hoạt động thật?** được chấm bằng cách lần đủ chuỗi
`control → form → route → service → job/stage → output`, không chấm bằng sự có
mặt của thẻ HTML.

| Surface | Hiện có | Backend | Hoạt động thật? | UX problem |
|---|---|---|---|---|
| **Create run** | `asv_trang_chinh.html` form POST | `routes.tao` (`routes.py:170`) → `features.tao_run_tu_ve` / `tao_run_tu_tai_len` | ✅ đủ chuỗi | Toàn bộ form là 4 fieldset radio + 1 select xếp dọc. Không có phân tầng basic/advanced, không ước giá, không ước thời gian. |
| **Upload — đường bền** | `upload_id` (hidden) | `routes.cap_ve` (`routes.py:139`) → `platform_core.upload_sessions` presigned PUT | ⚠️ **route sống, UI không gọi** | `asv_trang_chinh.html` chỉ có `<input type="file" name="video">`. Không có JS nào xin vé, nên **mọi khách hôm nay đi đường multipart 90 MB**, còn đường R2 bền vững thì không ai với tới. Đây là gap P0 số một. |
| **Upload — multipart** | `<input type=file>` | `routes.tao` nhánh dưới | ✅ | Trần 90 MB chỉ hiện dưới dạng câu chữ tĩnh; không kiểm phía client, nên khách chọn tệp 2 GB vẫn bấm Bắt đầu rồi mới bị từ chối. Không có thanh tiến độ tải lên. |
| **Preset** | 2 radio | `gia.PRESET_BANG` → `hop_dong_v4.PRESET` | ✅ | Chỉ 2 lựa chọn (`localize_preserve_picture`, `smart_localize`), không kèm minh hoạ hay hệ quả. Khách không biết "cắt thông minh" sẽ cắt gì. |
| **Timing mode** | 3+ radio | `gia.CHE_DO_THOI_GIAN` | ✅ | Đây là **thuật ngữ kỹ thuật đưa thẳng cho khách** ("Cách khớp thời gian"). Nó là hệ quả của preset, không phải một lựa chọn độc lập — bày ngang hàng là bắt khách quyết một việc họ không có cơ sở để quyết. |
| **Voice mode** | 2 radio | `hop_dong_v4.CHE_DO_GIONG` | ✅ | `AUTO_MATCH` và `USER_SELECTED` hiện đồng thời với ô select giọng luôn bật — khi chọn `AUTO_MATCH` thì ô select vẫn `required`, tức UI mâu thuẫn với chính nó. |
| **Voice picker** | `<select>` phẳng | `gia.giong_chon_duoc` → `ltt_voice` | ⚠️ một phần | Không nghe thử. Không lọc theo giới/vùng/phong cách — dù `ltt_voice/giong_mau.py` **có** `NHAN_GIOI`/`NHAN_VUNG`/`NHAN_PHONG_CACH` và hàm `loc(...)`. Năng lực đã có, GUI không dùng. |
| **Cost estimate** | ❌ | `gia.py` có bảng giá | ❌ | Chỉ một câu văn "được ước theo độ dài video". Không hiện số. Khách bấm Bắt đầu mà không biết mất bao nhiêu credit. |
| **Time estimate** | ❌ | — | ❌ | Không có ở bất cứ đâu. |
| **Preview** | ❌ | — | ❌ | Không có khung hình nào. Khách không thấy video mình vừa chọn. |
| **Progress** | `<ol>` 11 bước | `quan_sat.dong_thoi_gian` | ✅ | Nhãn đã là tiếng Việt sản phẩm (`routes.NHAN_GIAI_DOAN`) — điểm mạnh, giữ. Nhưng: không có `%`, không elapsed, không ETA, và **11 bước hiện cùng lúc** nên màn hình dài và đọc như log. |
| **History** | `<table>` 3 cột | `features.lich_su` | ⚠️ | Cột `Trạng thái` in **`r.status` thô** (`asv_trang_chinh.html:88`) — khách thấy `queued`/`running`/`error` bằng tiếng Anh, không dịch. Không phân trang, không lọc, không thumbnail, không tên tệp gốc. |
| **Detail** | `asv_chi_tiet.html` | `routes.chi_tiet` | ✅ | Không có tên video, không có so sánh nguồn↔kết quả, không có cài đặt đã dùng. Khách xem lại một lần chạy cũ không biết mình đã chọn gì. |
| **Retry** | nút, chỉ khi lỗi | `features.thu_lai_giai_doan` | ✅ | Nhãn "Thử lại bước này" không nói bước nào sẽ chạy lại hay có tốn thêm credit không. |
| **Cancel** | nút | `features.huy_run` | ✅ | Không hỏi xác nhận. Không nói credit giữ chỗ sẽ ra sao. |
| **Download** | nút | `routes.tai_ket_qua` (stream) | ✅ | Chỉ tải. Không phát thử trong trang, không copy link, không tải SRT. |
| **Error** | 1 `<div class="alert">` | `quan_sat.tom_tat_loi_cho_khach` | ⚠️ | Chỉ in **tên bước** hỏng, không nói *chuyện gì đã xảy ra* và *khách làm gì tiếp*. Đúng một nửa yêu cầu §13. |
| **Operator details** | `<details>` | `quan_sat.dong_thoi_gian(cho_van_hanh=True)` | ✅ | Đúng thiết kế (mặc định ẩn, chỉ admin). Nhưng thiếu hẳn số liệu render: tốc độ ×realtime, encoder, GPU, lý do chậm. |
| **Mobile** | ❌ | — | ❌ | Không một `@media` nào cho `asv-*`. Bảng lịch sử 3 cột sẽ tràn ngang. |
| **Empty state** | ⚠️ | — | ⚠️ | Có đúng **một** câu ("Bạn chưa có lần chạy nào"). Không có empty state cho ô chọn video hay danh sách giọng rỗng. |
| **Loading state** | ❌ | — | ❌ | Bấm "Bắt đầu lồng tiếng" → trang đứng im cho tới khi 303. Với tệp 90 MB đi multipart, đó là hàng chục giây **không phản hồi gì**. Nút không disable ⇒ bấm hai lần tạo hai lần chạy. |
| **Disabled state** | ❌ | — | ❌ | Không control nào từng bị disable. Ô giọng vẫn bật khi `AUTO_MATCH` (xem trên). |

---

## 2. Bốn khiếm khuyết P0 rút ra

**P0-1 — Đường tải lên bền vững không có mặt trong UI.**
`routes.cap_ve` + `platform_core.upload_sessions` đã sống và đã có người dùng
thật ở `autosubvideo/services/source_drafts.py`. ASV có route nhưng không có
client. Hệ quả: trần thật của sản phẩm là **90 MB**, không phải 2 GiB.

**P0-2 — Không có preview, nên không có cách nào kiểm chứng lựa chọn.**
Đây là điều kiện tiên quyết của mọi thứ trong §10 và §6B: không có khung hình
thì không có vùng che, không có trim marker, không có safe area.

**P0-3 — Không có ước giá / ước thời gian trước khi bấm.**
Credit bị giữ ở `features.tao_run` mà khách không thấy số. Với một sản phẩm bán
theo credit, đây là khiếm khuyết niềm tin, không phải khiếm khuyết tiện nghi.

**P0-4 — Không có loading state và nút không chống bấm kép.**
Rẻ nhất để sửa, và là lỗi duy nhất trong bảng này có thể tạo ra **hai lần trừ
tiền** cho một ý định của khách.

---

## 3. Điều đang làm ĐÚNG — và V5 phải giữ

Không phải mọi thứ đều là gap. Bốn thứ sau là tài sản:

1. **`routes.NHAN_GIAI_DOAN` lấy khoá TỪ `pipeline`**, không gõ tay. Đổi tên một
   giai đoạn mà quên sửa nhãn thì `test_423` đỏ. Giữ nguyên cơ chế này khi
   thêm bước.
2. **Lọc chủ sở hữu ở TẦNG DỊCH VỤ** (`features.lay_run(db, id, owner)` ném khi
   không phải của họ), không ở handler. Một handler quên mệnh đề `where` vẫn
   không rò rỉ. Mọi route V5 mới phải đi qua `_run_cua_toi`.
3. **404 chứ không 403** ở cả cờ tính năng và quyền sở hữu — không xác nhận sự
   tồn tại của thứ khách không được xem.
4. **Cờ `LTT_AUTO_SCAN_VIDEO` đặt TRƯỚC `require_login`** trong mọi chuỗi
   `Depends`. `routes.py:63` ghi rõ lý do: `Depends` chạy theo thứ tự khai báo,
   đặt sau thì route "đã đóng" vẫn 303 về `/login` — tức vẫn thừa nhận mình tồn
   tại. Mọi handler V5 mới phải giữ thứ tự này.

---

## 4. Ràng buộc nền tảng mà GUI V5 không được vượt

- `MANIFEST.enabled=False`, `public=False`, `lifecycle="development"`. App **chưa
  mở cho khách**. V5 không được đổi ba cờ này — đó là quyết định phát hành, và
  `STATE_V4.md` ghi điều kiện còn lại là *footage khách thật*.
- Trần hợp đồng app: **900 dòng / 30 handler** cho `routes.py`
  (`tools/lint_app_contract.py` cưỡng chế). Hiện 428/7. V5 thêm route phải nằm
  trong ngân sách đó, hoặc tách sang `services/`.
- Cloudflare: **100 MB/request**, **100 giây/response**. Mọi việc dài hơn vài
  giây phải đi qua hàng đợi job.
- `apps/asv_media` chỉ khai `gpu_vram_mb` cho **`render`**. Bất kỳ bước GUI mới
  nào cần GPU (dò vùng, dò dải phụ đề, sinh preview) **không được** lén dùng GPU
  trong một job không khai.

---

## 5. Cái đã có mà prompt V5 tưởng là chưa

Ghi ở đây để §5 (parity matrix) không kết luận `BUILD NEW` cho thứ đã tồn tại:

| Prompt V5 nói | Thực tế trong kho |
|---|---|
| §19 "mọi option phải hội tụ vào một canonical RenderManifest" | **Đã có.** `apps/auto_scan_video/ban_dung.py`, `SCHEMA_BAN_DUNG = 1`, mô tả *cái gì* chứ không phải *làm thế nào*, không chứa đường dẫn tuyệt đối, không chứa bí mật. `ket_xuat.dung_lenh(ban, ...)` là trình render đọc nó. V5 **mở rộng schema**, không tạo cái thứ hai. |
| §6H "GUI/operator surface nên có encoder/GPU/slow reason" | Một nửa đã có: `ket_xuat.bo_ma_hoa_thuc_te(ban, co_gpu=)` và `ket_xuat.ho_so_chan_doan(...)`. Chưa có đường đưa nó lên UI. |
| §6E "speaker → male/female → candidate voices" | Năng lực phân vai **đã khai công khai**: `autosubvideo.ai_workflows.diarize_file` + `assign_speakers` (pha 07). Nhãn giọng mẫu cũng có: `ltt_voice/giong_mau.py::loc(gioi=, vung=, phong_cach=)`. Chưa nối vào GUI. |
| §6D "ưu tiên reuse autosubvideo" | Đúng, và mạnh hơn thế: `hop_dong_v4.CAM_TRONG_MVP` **cấm** `subtitle_burn` trong ASV *vì* `apps/autosubvideo` đã làm việc đó. |
| §6G "shared artifact cache" | `platform_core` có `upload_sessions`, `storage`, `jobs` với lease. Chưa có cache artifact theo khoá nội dung. Đây là gap thật — xem parity matrix. |

---

## 6. Bằng chứng

Mọi dòng trong bảng §1 lần được tới mã tại `9d7f7044`:

```
apps/auto_scan_video/routes.py:139   cap_ve        — route vé tải lên, KHÔNG có client
apps/auto_scan_video/routes.py:170   tao           — hai đường upload
apps/auto_scan_video/routes.py:81    TRAN_TAI_LEN  — 90 MB
apps/auto_scan_video/routes.py:96    NHAN_GIAI_DOAN
apps/auto_scan_video/routes.py:63    _cong_co      — trước require_login
apps/auto_scan_video/ban_dung.py:47  SCHEMA_BAN_DUNG = 1
apps/auto_scan_video/ket_xuat.py:122 bo_ma_hoa_thuc_te
apps/auto_scan_video/ket_xuat.py:314 ho_so_chan_doan
templates/asv_trang_chinh.html:88    r.status in thô
templates/asv_tien_do.html:12        hx-trigger every 3s
apps/autosubvideo/__init__.py        BE_MAT_CONG_KHAI — diarize_file, assign_speakers
```

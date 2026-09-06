# KIẾN TRÚC TỐI GIẢN LTT ↔ WanGP — BẢN KHOÁ A–Z

Chốt sau lượt trích xuất WanGP. Mỗi bước ghi đủ bảy trường:
`OWNER` · `SOURCE OF TRUTH` · `API/SYMBOL` · `PERSISTENT` · `TRANSIENT` ·
`SECRET BOUNDARY` · `FAILURE`.

⛔ Nguyên tắc: **LTT chỉ sở hữu thứ WanGP không có khái niệm.** Mọi thứ khác là
gọi lại.

---

## Sơ đồ

```
NGUOI DUNG
   v
LTT GUI (phang)                          [1]
   v
AUTH / VAI TRO                           [2]
   v
SO HUU MEDIA / LUU TRU                   [3]
   v
YEU CAU + UOC PHI                        [4]
   v
HANG DOI JOB CUA LTT                     [5]   <- nguon chan ly san pham
   v
WanGP CLIENT                             [6]
   v
CHUYEN MEDIA (gallery upload ngan han)   [7]
   v
C-CLOUD: WanGP + profile da duyet        [8]
   v
GPU                                      [9]
   v
TIEN DO / PREVIEW / HUY                  [10]
   v
KET QUA -> tai ve -> R2 -> XAC MINH      [11]
   v
LICH SU + QUYET TOAN CREDIT              [12]
   v
NGUOI DUNG
```

---

## [1] LTT GUI — composer phẳng

- **OWNER:** LTT
- **SOURCE OF TRUTH:** `apps/lttvideo/` (hợp đồng app `AGENTS.md` §8)
- **API/SYMBOL:** `server.templating.templates` · `platform_core.i18n` · `ltt.css`
- **PERSISTENT:** không
- **TRANSIENT:** nội dung form chưa gửi
- **SECRET BOUNDARY:** trình duyệt **không** nhận khoá nào
- **FAILURE:** lỗi hiển thị tại chỗ, không mất bản nháp

Người dùng gửi: `prompt` · `media[]` · `aspect_ratio` · `duration_s` · `quality` ·
`seed`. **Không có tab mode.**

## [2] Auth / vai trò

- **OWNER:** LTT — WanGP **không có khái niệm người dùng**
- **SOURCE OF TRUTH:** phiên + CSDL nền tảng
- **API/SYMBOL:** `server.auth.session.require_login` · `server.auth.csrf`
- **PERSISTENT:** người dùng, vai trò, quyền dùng app
- **TRANSIENT:** cookie phiên
- **SECRET BOUNDARY:** ⛔ khoá ký phiên **không bao giờ** rời máy A
- **FAILURE:** 303 về `/login`

⚠️ Cờ quyền phải đặt **trước** `require_login` trong `Depends` — nếu không, route
"đã đóng" vẫn 303 về login thay vì 404.

## [3] Sở hữu media / lưu trữ

- **OWNER:** LTT
- **SOURCE OF TRUTH:** bảng sở hữu media của nền tảng
- **API/SYMBOL:** `platform_core.storage` (R2) ·
  `platform_core.image_input.validate_reference`
- **PERSISTENT:** khoá R2 + chủ sở hữu + thời điểm
- **TRANSIENT:** tệp đang tải lên
- **SECRET BOUNDARY:** ⛔ **khoá R2 gốc không rời máy A**
- **FAILURE:** từ chối trước khi tính tiền; ≤100 MB *(trần Cloudflare)*

## [4] Yêu cầu + ước phí

- **OWNER:** LTT
- **SOURCE OF TRUTH:** `apps/lttvideo/cost.py` + sổ đăng ký profile
- **API/SYMBOL:** `platform_core.credit` giữ chỗ
- **PERSISTENT:** bút toán giữ chỗ
- **TRANSIENT:** ước tính
- **FAILURE:** thiếu credit ⇒ chặn **trước** khi chạm GPU

⭐ Ở đây LTT chọn `profile_id`, **không** chọn `model_type`. Ánh xạ
`profile_id → (tệp settings, SHA WanGP)`.

## [5] Hàng đợi job LTT — nguồn chân lý sản phẩm

- **OWNER:** LTT
- **SOURCE OF TRUTH:** `platform_core.job_runner` + `leases`
- **PERSISTENT:** job, trạng thái, chủ sở hữu, lịch sử
- **TRANSIENT:** lease
- **FAILURE:** job kẹt ⇒ lease hết hạn ⇒ nhận lại

⚠️ **Khác** hàng đợi thực thi của WanGP (§2.A). Bỏ cái nào cũng sai.

## [6] WanGP client

- **OWNER:** LTT *(mã mới — B2)*
- **SOURCE OF TRUTH:** `shared/api.py` phía C-CLOUD
- **API/SYMBOL:** `health · submit · progress · cancel · result · cleanup`
- **PERSISTENT:** không
- **TRANSIENT:** phiên HTTP
- **SECRET BOUNDARY:** chỉ mang **khoá endpoint của job đó**
- **FAILURE:** hết giờ ⇒ trả job về hàng đợi, **không** trừ credit

## [7] Chuyển media

- **OWNER:** WanGP
- **API/SYMBOL:** `wangp_create_gallery_upload(filename)` → PUT ·
  `wangp_create_gallery_download(media_id)` → GET
- **PERSISTENT:** không — **URL dùng một lần, sống ngắn**
- **TRANSIENT:** tệp trong gallery C-CLOUD
- **SECRET BOUNDARY:** ✅ đúng thứ kiến trúc §5 đòi, **có sẵn**
- **FAILURE:** upload lỗi ⇒ job fail trước khi tốn GPU

## [8] WanGP trên C-CLOUD

- **OWNER:** WanGP
- **SOURCE OF TRUTH:** `defaults/*.json` + settings file đã duyệt
- **API/SYMBOL:** `init()` → `submit_task()`; `apply_media_flag_defaults()` ·
  `apply_video_length_duration()` tự chuẩn hoá
- **PERSISTENT:** model trên volume
- **TRANSIENT:** VRAM, gallery, outputs
- **SECRET BOUNDARY:** ⛔ **không** DB / phiên / R2 gốc
- **FAILURE:** `GenerationError`; nếu `init()` hỏng thì worker chết **trước** khi
  nhận job

🔴 `init()` **một lần/tiến trình** ⇒ **một worker phục vụ đúng một cấu hình**.
Chốt `profile 3` (`P01-D-12`).

## [9] GPU

- **OWNER:** RunPod
- **SOURCE OF TRUTH:** `GET /pods` · `/billing/pods`
- **PERSISTENT:** volume
- **TRANSIENT:** pod
- **FAILURE:** ⚠️ **hết GPU là chuyện có thật** — `US-KS-2` cạn A100 lúc 06/09.
  Job phải quay về hàng đợi, **không** báo lỗi cho người dùng ngay.

## [10] Tiến độ / preview / huỷ

- **OWNER:** WanGP sinh · LTT chuyển tiếp
- **API/SYMBOL:** `job.events.iter()` → `ProgressUpdate` · `PreviewUpdate` ·
  `job.cancel()`
- **PERSISTENT:** không
- **TRANSIENT:** dòng sự kiện
- **FAILURE:** mất dòng sự kiện ⇒ **không** đồng nghĩa job chết; hỏi lại
  `job.result()`

**Đo được:** 786 `progress` + 20 `preview` mỗi lượt 20 bước; huỷ trả
`success=False` + `"Generation was cancelled"`.

## [11] Kết quả → R2 → xác minh

- **OWNER:** LTT
- **SOURCE OF TRUTH:** R2
- **API/SYMBOL:** `result.generated_files` → tải về → `platform_core.storage`
- **PERSISTENT:** tệp trong R2 + khoá + chủ sở hữu
- **TRANSIENT:** tệp trên C-CLOUD *(mất khi xoá pod)*
- **FAILURE:** job **chưa `done`** cho tới khi tệp nằm trong R2 và xác minh được

🔴 **Bẫy đã đo:** tên tệp WanGP **chứa nguyên văn prompt** ⇒ LTT **phải đặt lại
tên**; tên gốc làm hỏng khoá đối tượng và **rò rỉ prompt người dùng**.

## [12] Lịch sử + quyết toán

- **OWNER:** LTT
- **SOURCE OF TRUTH:** sổ credit + lịch sử job
- **PERSISTENT:** bút toán, liên kết tệp
- **FAILURE:** quyết toán **idempotent** — chạy lại không trừ hai lần

---

## Ranh giới bí mật — bất biến

| LTT giữ | C-CLOUD được nhận |
|---|---|
| auth · người dùng · quyền | khoá endpoint của **chính job đó** |
| sổ job · credit | URL media **có phạm vi, sống ngắn** |
| khoá R2 gốc | tham số sinh video |
| khoá phiên · mật khẩu CSDL | — |
| khoá nhà cung cấp cloud | — |

⛔ Ba thứ **không bao giờ**: mật khẩu CSDL · khoá ký phiên · khoá R2 gốc.

## Deepy — chưa nằm trong bản khoá này

`D-V2-007` khoá: Deepy trước, **nhưng chỉ sau khi có phép đo**. Và
`DEEPY_UNKNOWN_GAPS.md` còn hai ô `NEEDS_LIVE_TEST`. Baseline chạy **không có
Deepy**; LTT gửi `profile_id` đã duyệt.

⭐ Điều này **không** thu hẹp kiến trúc: khi Deepy vào, nó thay bước chọn
`profile_id` ở [4] — **không** đổi [1]–[3] hay [5]–[12].

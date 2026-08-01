# Công thức di trú một app từ BOT GEMINI (desktop/LAN) sang LTTSTUDIOSAPP (internet)

> Lập 2026-08-01. Tài liệu nền tảng cho MỌI lần đưa một module BOT GEMINI thành
> một app web. Đọc cùng `KHAO_SAT_BOT_GEMINI.md` (module nào đáng port) và
> `03_THEM_APP_MOI.md` (hợp đồng app). Ví dụ đối chiếu cụ thể:
> `DOI_CHIEU_THUMBNAIL.md`.

## 0. Nguyên lý gốc: "cùng workflow, khác mức đảm bảo"

Hai bot khác nhau ở **mô hình triển khai**, không phải ở việc tool làm gì:

- **BOT GEMINI** = desktop/LAN, người dùng tin được, 1 tiến trình, trạng thái ở
  RAM + file JSON, tiền = đếm lượt/ngày, file cục bộ.
- **LTTSTUDIOSAPP** = internet SaaS, người dùng KHÔNG tin, nhiều worker, trạng
  thái ở Postgres bền, tiền = sổ credit kế toán được, file qua storage (→R2).

Domain workflow (các BƯỚC nghiệp vụ) **gần như y hệt**. Cái khác là **ĐẢM BẢO**
bọc quanh mỗi bước: LAN được phép cẩu thả (in-RAM, in-proc, tin client); internet
bắt buộc chặt (bền, kế toán, cô lập, zero-trust). **Các tầng "thêm" của LTT không
phải tính năng mới — là cùng workflow gói trong đảm bảo mạnh hơn.**

→ Di trú = **giữ lõi + tài nguyên, thay lớp đảm bảo, bỏ lớp desktop.**

## 1. Bản đồ 7 lớp của một module (biết để không nhầm lớp nào đi đâu)

| Lớp | Là gì | Ví dụ thumbnail_api |
|---|---|---|
| L1 Tài nguyên | dữ liệu tĩnh | `prompts/thumbnail_youtube/*`, `_labels.json`, model registry |
| L2 Lõi nghiệp vụ | thuật toán tool | prompt-builder, hình gọi Gemini, parse ảnh, phân loại lỗi/retry |
| L3 Điều phối | chạy job dài | runner (vòng count, xoay key, poll) |
| L4 UI | giao diện | `_thumbnail_api.html` + `thumbnail-api.js` (Alpine) |
| L5 Route/API | đường vào | `api.py` (`/api/thumbnail-api/*`, poll JSON) |
| L6 Hạ tầng | dịch vụ chung | auth, user, quota, key-pool, storage, DB |
| L7 Desktop | ràng buộc máy | Selenium/Chrome/cookie/PyQt/GPU/đường dẫn cục bộ |

## 2. Bốn rổ: mỗi lớp đi đâu

- 🟢 **COPY NGUYÊN** — **L1 + L2**. Tài nguyên là dữ liệu (copy thẳng). Lõi nghiệp
  vụ chuyển được, chỉ đổi `import` sang dịch vụ nền tảng. *Đây là "workflow giống nhau".*
- 🟡 **VIẾT LẠI THEO HỢP ĐỒNG** — **L4 + L5 + phần vỏ của L3**. `manifest.py`,
  `routes.py` (`require_login`/CSRF/credit), `jobs.py` (idempotent/`ctx.progress`/
  raise), template (`extends base.html`, HTMX thay Alpine). Cấu trúc map 1:1, code
  là của nền tảng.
- 🔴 **THAY BẰNG DỊCH VỤ NỀN TẢNG** — **L6**. KHÔNG copy. Gọi cái mới:

  | BOT GEMINI | → | LTTSTUDIOSAPP |
  |---|---|---|
  | `api_allocator` pool key | → | `platform_core.api_pool` / `api_keys` (APIKEYS) |
  | `OUTPUT_DIR/user/…` | → | `platform_core.storage` |
  | user JSON + JWT RAM | → | Postgres `User` + session cookie |
  | quota/ngày | → | sổ credit (`credit` giữ chỗ→quyết toán→hoàn) |
  | asyncio queue in-proc | → | hàng đợi Postgres + worker (`jobs`) |
  | model registry code | → | `platform_core/providers.py` |

- ⚫ **BỎ** — **L7**. Với module api-only: không có gì để bỏ. Với module browser/
  cookie: **workflow CHÍNH LÀ L7 → không di trú lên internet được** (ToS + không
  nhân bản + rủi ro pháp lý). Giữ ở BOT GEMINI.

## 3. Ma trận tận dụng (module API-only, đo theo LỚP)

| Lớp | % tận dụng | Ghi chú |
|---|---:|---|
| L1 Tài nguyên | **~100%** | copy dữ liệu |
| L2 Lõi nghiệp vụ | **~60–70%** | đổi import, giữ thuật toán |
| L3 Điều phối | **~30%** | giữ vòng count + xoay key; bỏ asyncio → hàng đợi job |
| L4 UI | **spec 100% / code ~25%** | field+option dùng lại; template viết lại HTMX |
| L5 Route | **~15%** | viết lại theo hợp đồng |
| L6 Hạ tầng | **0% copy** | THAY bằng dịch vụ nền tảng |
| L7 Desktop | **bỏ** | api-only: không có |

**Ba con số phải tách riêng** (gộp là hiểu sai):
- **Giá trị chuyển sang ≈ 90%** — giữ trọn năng lực tool.
- **Mã copy-dán ≈ 40–50%** — phần còn lại là "đấu nối lại", cơ học.
- **Tài nguyên = 100%**.

## 4. Khả năng di trú theo NHÓM (quyết định CÓ nên di trú không)

| Nhóm (`requires`) | Ví dụ | Di trú | Điều kiện trước |
|---|---|---|---|
| A `api` | seedance_video, plenx, gemini_image, thumbnail_api | ✅ tốt | không |
| B `ffmpeg` | auto_sub_video, concat_pro | ⚠️ được | **R2 + hàng đợi file lớn (H10)** trước |
| C `gpu` | cut_clip_short, video_upscale | ⚠️ hoãn | máy có card + R2 |
| D `browser/cookie` | whisk_nano, các flow_* | ⛔ **không** | workflow = desktop, để nội bộ |

## 5. CÔNG THỨC 8 BƯỚC di trú một app (áp cho mọi app sau)

**B0. Phân loại** — đọc `requires` của module. Nhóm D → dừng (không di trú). Nhóm
B/C → kiểm điều kiện R2/GPU trước.

**B1. Kiểm kê parity** — lập bảng như `DOI_CHIEU_THUMBNAIL.md`: mọi nhóm điều
khiển UI + mọi lựa chọn (từ `_labels.json`), model list, cấu hình, luồng backend.

**B2. Copy tài nguyên (L1)** — `prompts/<module>/` → `apps/<slug>/prompts/`; model
registry → thêm dòng vào `platform_core/providers.py`. Ghi rõ copy từ commit nào.

**B3. Port lõi nghiệp vụ (L2) vào `jobs.py`** — prompt-builder **ghép từ fragment**
(cấm hardcode chuỗi prompt), hình gọi provider, parse, phân loại lỗi. Giữ thuật
toán, đổi import.

**B4. Thay hạ tầng (L6)** — key→`api_pool`, storage→`platform_core.storage`,
tiền→credit qua submit job, không chạm auth/user/DB (dùng sẵn của nền tảng).

**B5. Dựng lại UI (L4)** — `apps/<slug>/templates/*.html` extends `base.html`, đủ
nhóm điều khiển + xem-trước-prompt + hiển thị kết quả; HTMX thay Alpine.

**B6. Nối route (L5)** — `routes.py` theo hợp đồng: `require_login`, CSRF,
`credit_cost` trong manifest, submit job (không chạy dài trong request).

**B7. Nghiệm thu parity** — test xanh + scan 0 + **chụp ảnh 2 UI đối chiếu** +
bảng parity đạt mốc (đề xuất **≥ 90%** nhóm tính năng người dùng, trừ phần được
phép lược bỏ có ghi lý do: desktop, và phần gốc chưa hoàn thiện).

## 6. Ví dụ đã đo — thumbnail_api

Bản dựng H5 chỉ đạt **~30%** tính năng người dùng vì làm tối giản (đúng mục tiêu
H5 lúc đó, nhưng KHÔNG đạt chuẩn di trú). Chi tiết + catalog gốc cần port:
`DOI_CHIEU_THUMBNAIL.md`. Đây là app đầu tiên sẽ nâng lên đúng công thức này để
làm khuôn cho các app sau.

## 7. Bẫy hay gặp khi di trú (đã gặp thật)

1. **Hardcode prompt** thay vì ghép fragment → mất toàn bộ hệ lựa chọn. (thumbnail).
2. **Lấy nhầm nhãn** từ thư mục cũ không phục vụ (vd `thumbnail_pro` vs
   `thumbnail_youtube`) → luôn lấy từ file `_labels.json` đang được route dùng.
3. **Bê hạ tầng LAN sang** (JWT RAM, file JSON, quota/ngày) thay vì dùng dịch vụ
   nền tảng → vỡ đảm bảo internet.
4. **Chạy việc dài trong request** (di sản asyncio) → 524 sau 100s; phải qua hàng đợi.
5. **Coi "chạy được" là "xong"** → phải đối chiếu parity + ảnh 2 UI mới là xong.

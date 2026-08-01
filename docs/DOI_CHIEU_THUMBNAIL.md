# Đối chiếu app THUMBNAIL: BOT GEMINI (gốc) vs LTTSTUDIOSAPP (bản dựng lại)

> Lập 2026-08-01. Mục tiêu: đo độ trung thành của bản di trú, tìm nguyên nhân, và
> đề xuất chuẩn di trú để áp cho các app tiếp theo. Nguồn BOT GEMINI **chỉ đọc**.
>
> **CẬP NHẬT 2026-08-01 — Đợt R ĐÃ NÂNG PARITY:** bản LTT đã port đủ 6 style chữ +
> 11 phong cách + 9 kiểu trend + 5 ngôn ngữ (copy `apps/thumbnail/prompts/`), chọn
> model (3 model ảnh qua registry), phụ đề, tỉ lệ 5, **xem-trước-prompt**, và
> prompt-builder **ghép fragment** (`platform_core/prompt_fragments.py`) thay hardcode.
> **Tạm bỏ có lý do:** ảnh tham chiếu + Imagen (gốc cũng chưa hoàn thiện) + Batch
> (fast-follow). Parity nhóm người dùng: ~30% → **~93%**. Bảng A dưới là hiện trạng
> TRƯỚC Đợt R (giữ làm lịch sử/đối chiếu).

## Nguồn đối chiếu

| Phía | File chính |
|---|---|
| **Gốc (BOT GEMINI)** | `app/modules/thumbnail_api/` (api/service/runner/adapters, 1418 dòng) · UI `app/ui/templates/partials/_thumbnail_api.html` (454) + `static/js/modules/thumbnail-api.js` (271) · catalog prompt `prompts/thumbnail_youtube/` · registry model `app/models/image_model_registry.py` |
| **Bản dựng lại (LTT)** | [apps/thumbnail/](../apps/thumbnail/) — manifest (53) + jobs (221) + routes (141) + `templates/thumbnail.html` (75). Tổng ~490 dòng, prompt **hardcode inline** |

**Đính chính nhãn trước khi đọc:** một số tên trong yêu cầu ("Cinematic Gold",
"Blend Ảnh", "IGH36H Realistic", "Minecraft" ở mục Trend) là từ thư mục CŨ
`prompts/thumbnail_pro/` **không được tool web dùng**. Bản đang phục vụ thật đọc
từ `prompts/thumbnail_youtube/*/_labels.json`. Bảng dưới dùng **nhãn thật đang phục vụ**.

---

## A. Bảng đối chiếu tổng (theo hạng mục)

Cột **Giống**: độ trung thành của bản LTT so với gốc (0–100%). **Nguyên nhân**:
🎯 = lược bỏ CÓ CHỦ ĐÍCH (dựng khung H5 tối giản) · ⚠️ = thiếu nên-có (dễ làm mà bỏ)
· ✅ = LTT cố ý LÀM KHÁC/TỐT HƠN · ⛔ = gốc cũng chưa có/chưa hoàn thiện.

### A1. Nhóm tính năng NGƯỜI DÙNG (giao diện tạo ảnh)

| # | Hạng mục | BOT GEMINI (gốc) | LTT (hiện tại) | Giống | NN |
|---|---|---|---|---:|:--:|
| 1 | Ô ý tưởng / chủ đề | textarea, bắt buộc, đếm ký tự | input `topic`, bắt buộc | 90% | ✅ |
| 2 | Tiêu đề trên ảnh | input `title` | input `title` | 100% | — |
| 3 | Phụ đề (subtitle) | input `subtitle` → prompt | **không có** | 0% | 🎯 |
| 4 | **Style chữ** | **6 lựa chọn** (fragment .txt) | **không có** | 0% | 🎯 |
| 5 | **Phong cách ảnh** | **11 lựa chọn** | **không có** | 0% | 🎯 |
| 6 | **Kiểu Thumbnail Trend** | **9 lựa chọn** | **không có** | 0% | 🎯 |
| 7 | **Chọn Model AI** | **6 model** (3 active) + badge tier | **1 model cứng** `gemini-2.5-flash-image` | 5% | ⚠️ |
| 8 | Tỉ lệ khung hình | 5 (`16:9,9:16,1:1,4:3,3:4`), **động theo model** | 4 (`16:9,1:1,9:16,4:3`), tĩnh | 55% | 🎯 |
| 9 | **Ngôn ngữ trong ảnh** | **5** (Việt/Anh/Nhật/Hàn/Trung) | **không có** | 0% | 🎯 |
| 10 | Số lượng ảnh 1–4 | nút 1/2/3/4 | input số 1–4 | 100% | — |
| 11 | Ảnh tham chiếu (upload) | có UI (⛔ chưa wire backend) | **không có** | 0% | ⛔ |
| 12 | **Batch Mode** (≤20 prompt) | có + tiến độ | **không có** | 0% | 🎯 |
| 13 | **Xem trước Prompt** + Sao chép | có (`/preview-prompt`) | **không có** | 0% | 🎯 |
| 14 | **Prompt-builder** | ghép **fragment .txt** (base + phong_cach + trend + text_style + ngôn ngữ + title/subtitle) | **hardcode 1 chuỗi tiếng Anh** | 10% | 🎯 |
| 15 | Hiển thị kết quả | grid 3 cột, overlay prompt, tải, xoá, click phóng to | gallery cơ bản + link tải | 55% | 🎯 |
| 16 | Tiến độ + log | %, step, log dòng thời gian | % job (poll trang /jobs) | 45% | 🎯 |

**Trung bình nhóm người dùng ≈ 30%.**

### A2. Nhóm HẠ TẦNG / VẬN HÀNH (nơi LTT cố ý khác)

| # | Hạng mục | BOT GEMINI | LTT | Nhận định |
|---|---|---|---|---|
| 17 | Tính tiền / credit | **không có** | **có** (giữ chỗ→quyết toán→hoàn, 5cr/ảnh) | ✅ LTT hơn — đúng mục tiêu thương mại |
| 18 | Hàng đợi job | asyncio trong tiến trình | **Postgres + worker riêng** (bền qua restart) | ✅ LTT hơn |
| 19 | Nguồn API key | pool key server-side | **bộ máy APIKEYS** (mã hoá, cascade, telemetry) | ✅ LTT hơn |
| 20 | Bảo mật | key qua `?key=` | key qua header + sanitize + CSRF + require_login | ✅ LTT hơn |
| 21 | Registry model (tier/badge/aspect/max) | có, render UI | có `providers.py` nhưng **app không dùng để render** | ⚠️ hạ tầng có, chưa nối UI |
| 22 | Phụ thuộc desktop | **không** (đã bỏ) | **không** | — cả hai đều API-only |

**Kết luận hai mặt:** LTT **hơn hẳn về hạ tầng** (tiền, hàng đợi, key, bảo mật)
nhưng **chỉ đạt ~30% bộ tính năng người dùng** của bản gốc. Đúng như nhận xét: về
trải nghiệm tạo thumbnail, đây là **viết mới tối giản**, không phải port trung thành.

---

## B. Catalog gốc cần tái hiện (đây cũng là SPEC để port)

Toàn bộ nhãn lấy từ `prompts/thumbnail_youtube/<nhóm>/_labels.json`; mỗi lựa chọn
là một file `.txt` chèn nguyên văn vào prompt. **Port = copy các thư mục này sang
`apps/thumbnail/prompts/` và ghép lại theo `base_prompt.txt`.**

- **Style chữ (6):** Bold Impact · Clean Minimal · Dramatic Gold · Neon Glow · Street Art · Thư pháp
- **Phong cách ảnh (11):** Chuyên nghiệp tối giản *(mặc định)* · Hoạt hình/Cartoon · Cinematic · Flat Design · 3D Render · Collage · Retro/Vintage · Lego (Mạnh) · Tranh thủy mặc (Mạnh) · KHANH-Realistic · Minecraft (Lâm)
- **Kiểu Trend (9):** Khuôn mặt cảm xúc lớn *(mặc định)* · So sánh trước/sau · Bí ẩn/Gây tò mò · Listicle/Numbered · Hướng dẫn/Tutorial · Reaction · Storytelling · Mũi tên/Chỉ dẫn · Text-Heavy/Chữ lớn
- **Ngôn ngữ (5):** Tiếng Việt *(mặc định)* · English · 日本語 · 한국어 · 中文
- **Model AI (6; 3 active):** Gemini 2.5 Flash *(mặc định)* · Gemini 3.1 Flash · Gemini 3 Pro · ~~Imagen 4 / 4 Ultra / 4 Fast~~ (SOON, endpoint Vertex chưa làm)
- **`base_prompt.txt` gốc:**
  ```
  YouTube thumbnail {aspect_ratio}.
  Topic: {user_input}
  {phong_cach_style}
  {kieu_trend_layout}
  {text_style_directive}
  {title_text}
  {subtitle_text}
  {ngon_ngu_directive}
  Professional thumbnail design, eye-catching and click-worthy, high resolution, sharp details.
  ```

> **Được phép lược bỏ (ghi rõ):** ảnh tham chiếu (gốc **cũng chưa wire** backend) ·
> Imagen SOON (chưa implement ở gốc). **Không nên lược bỏ:** style chữ / phong cách /
> trend / ngôn ngữ / chọn model / xem-trước-prompt — đây là phần làm nên giá trị tool.

---

## C. Nguyên nhân gốc — vì sao lệch

Không phải bug rời rạc. **90% chỗ lệch là một quyết định chủ đích:** ở H5, mục
tiêu là "chứng minh chuỗi user→job→credit→tải về" rẻ và nhanh, nên tôi dựng UI/
prompt tối giản (docstring `jobs.py` ghi thẳng *"Viết mới, gọn… Tham chiếu logic…
(chỉ đọc)"*). Vấn đề **không nằm ở lần dựng đó** mà ở **quy trình**:

1. **`03_THEM_APP_MOI.md`** chỉ mô tả *hợp đồng tối thiểu* để app gắn vào nền tảng
   (manifest/jobs/routes/credit). Nó **không phân biệt** "viết app MỚI" với "DI TRÚ
   app đã có", và **không có ràng buộc parity** nào. Làm đúng nó vẫn ra bản tối giản.
2. **`KHAO_SAT_BOT_GEMINI.md`** dừng ở mức *"module nào đáng port, giá trị hạ tầng"*.
   Nó **không có checklist kiểm kê + tái hiện đầy đủ UI/tính năng/tài nguyên prompt**
   của module khi thực sự port.
3. Không có bước **đối chiếu ảnh chụp 2 UI** trong định nghĩa "xong" của một app di trú.

→ Thiếu chuẩn "di trú trung thành" là lỗ hổng thật sự; nó sẽ lặp lại ở mọi app sau
(seedance_video, plenx, gemini_image…) nếu không vá.

---

## D. ĐỀ XUẤT sửa 2 file quy tắc (chờ bạn duyệt — chưa áp dụng)

### D1. Thêm vào `03_THEM_APP_MOI.md`: phân biệt 2 loại app

- **App VIẾT MỚI** (do ta nghĩ ra): theo hợp đồng tối thiểu như hiện tại.
- **App DI TRÚ từ BOT GEMINI**: PHẢI đạt **Checklist parity** trước khi gọi là xong.
- Thêm quy ước thư mục tài nguyên: `apps/<slug>/prompts/` (copy nguyên catalog gốc);
  prompt-builder **ghép từ fragment**, cấm hardcode chuỗi prompt trong `jobs.py`.

### D2. Thêm vào `KHAO_SAT_BOT_GEMINI.md`: "Quy trình DI TRÚ trung thành"

Checklist parity bắt buộc cho mỗi module port:
1. **Kiểm kê UI đầy đủ**: liệt kê mọi nhóm điều khiển + mọi lựa chọn (từ
   `_labels.json`), model list, cấu hình — lập bảng như tài liệu này.
2. **Copy tài nguyên**: thư mục `prompts/<module>/` → `apps/<slug>/prompts/`; registry
   model → map vào `platform_core/providers.py`.
3. **Tái hiện prompt-builder** theo đúng fragment gốc (test: cùng input → prompt trùng ý).
4. **Tái hiện UI**: đủ nhóm điều khiển + xem-trước-prompt + hiển thị kết quả tương đương.
5. **Chỉ được lược bỏ**: desktop/browser/cookie, và phần **gốc chưa hoàn thiện** —
   mọi lược bỏ khác phải **ghi lý do** trong tài liệu module.
6. **Cổng "xong"**: chụp ảnh 2 UI đối chiếu + bảng parity đạt ≥ mốc thống nhất
   (đề xuất **≥ 90%** nhóm tính năng người dùng) + full test xanh.

### D3. Định nghĩa "xong một app di trú"

Thêm dòng vào bảng tiêu chí: *app di trú chỉ 'xong' khi bảng parity ≥ 90% (trừ phần
được phép lược bỏ có ghi lý do) và đã kiểm trình duyệt đối chiếu.*

---

## E. Việc kế tiếp (sau khi bạn duyệt bảng này)

1. Bạn xác nhận: (a) mốc parity mục tiêu (đề xuất 90%), (b) có port ảnh-tham-chiếu +
   Imagen không (gốc chưa có), (c) đồng ý quy ước `apps/<slug>/prompts/`.
2. Tôi sửa 2 file quy tắc theo D1–D3.
3. Tôi **nâng cấp app thumbnail đạt parity** (port 6+11+9+5 catalog + chọn model +
   subtitle + ngôn ngữ + xem-trước-prompt + prompt-builder theo fragment), theo đúng
   chuẩn vừa chốt — làm mẫu cho các app sau.

# Kế hoạch tổng: di trú module BOT GEMINI → LTTSTUDIOSAPP

> Lập 2026-08-01. Chương trình lớn: đưa MỌI module phù hợp (nhóm A/B/C) thành app
> web trung thành 100% chức năng/workflow/UI — chỉ khác vỏ + hạ tầng. Nhóm D loại
> bỏ. Đọc cùng `CONG_THUC_DI_TRU_APP.md` (công thức 8 bước) + `DOI_CHIEU_THUMBNAIL.md`.
> **Tài liệu để DUYỆT — chưa thực thi.**

## 1. Đánh giá đề nghị + tính khả thi

**Kết luận: khả thi CAO, nhưng là một CHƯƠNG TRÌNH nhiều đợt, không phải một sprint.**

- Phần cứng: máy chủ = máy chạy BOT GEMINI → có GPU + ffmpeg → **A/B/C đều chạy được tại chỗ**.
- Trung thành 100% khả thi nhờ công thức: **L1 tài nguyên + L2 lõi copy được; L4 UI tái hiện theo spec; chỉ L5/L6 (vỏ + hạ tầng) viết lại**.
- Rào chắn thật: (a) **H10 R2** chưa có → B/C bị chặn; (b) **định tuyến job GPU** chưa có → C bị chặn; (c) khối lượng lớn (13 module, ~24k dòng chưa kể Prompt Studio 28k) → phải làm theo đợt + "nhà máy di trú" để rẻ dần.
- Rủi ro lớn nhất: **làm ồ ạt → parity kém, khó nghiệm thu**. Trị bằng: chuẩn parity ≥90% + nghiệm thu từng app + một app tham chiếu khoá pattern trước.

## 2. Danh sách module đầy đủ (backlog di trú)

Giá trị TM: ⭐⭐⭐ cao · ⭐⭐ vừa · ⭐ thấp. Effort: S/M/L/XL (tương đối). Prereq = điều kiện hạ tầng trước.

| Module | Nhóm | Dòng | Giá trị | Prereq | Effort | Đợt | Ghi chú |
|---|---|---:|:--:|---|:--:|:--:|---|
| thumbnail_api | A | 1.418 | ⭐⭐⭐ | — | M | **R** | App tham chiếu — khoá "nhà máy" + nâng lên parity |
| gemini_image | A | 310 | ⭐⭐ | — | S | A1 | Giống thumbnail, rẻ |
| youtube_script | A | 139 | ⭐⭐ | — | S | A1 | Text out, rất nhỏ |
| seedance_video | A | 5.508 | ⭐⭐⭐ | cost model | L | A2 | Cỗ máy doanh thu; có `cost.py` mẫu |
| plenx | A | 2.731 | ⭐⭐⭐ | cost model | M* | A2 | **Sinh đôi** seedance → làm chung rẻ hơn nhiều |
| gemini_video | A | 908 | ⭐⭐ | — | M | A2 | Video async qua Gemini |
| gemini_api_chat | A | 763 | ⭐ | — | M | (hoãn) | Giá trị thấp (khách có ChatGPT free) — quyết sau |
| video_chain | B | 456 | ⭐⭐ | **H10 R2** | M | B | Nhỏ nhất nhóm B → mở đường file lớn |
| auto_sub_video | B | 6.454 | ⭐⭐⭐ | **H10 R2** | L | B | Không đụng ToS ai, khác biệt rõ |
| concat_pro | B | 857 | ⭐⭐ | H10 + GPU route | M | B | Mã hoá GPU |
| video_upscale | C | 1.460 | ⭐⭐ | H10 + GPU route | M | C | Kèm vendor 48MB (copy theo) |
| cut_clip_short | C | 2.884 | ⭐⭐ | H10 + GPU route | L | C | Whisper+YOLO, upload tới 2GB |
| seedance (Prompt Studio) | A | 28.685 | ⭐⭐⭐ | DB+i18n riêng | XL | S(cuối) | **Dự án riêng**, 111 file — đánh giá lại, không gộp vào đợt thường |
| ⛔ whisk_nano + mọi flow_*/browser | D | — | — | — | — | **BỎ** | Cookie/trình duyệt — giữ nội bộ ở BOT GEMINI |

\* plenx effort M vì tái dùng phần lớn từ seedance_video.

## 3. Các phương án chiến lược (chấm điểm)

Thang 1–10 (Rủi ro: cao điểm = ít rủi ro). Trọng số: Chất lượng/parity 30% · Khả thi 25% · Ra giá trị sớm 20% · Rủi ro 15% · Rẻ-dần-mỗi-app 10%.

| Phương án | Parity | Khả thi | Giá trị sớm | Rủi ro | Rẻ dần | **Tổng** |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| **1. Big-bang** (port hết một đợt) | 4 | 3 | 2 | 3 | 5 | **3.4** |
| **2. Theo nhóm A→B→C tuần tự** | 8 | 8 | 7 | 7 | 7 | **7.5** |
| **3. Tham chiếu-trước + Nhà máy + ưu tiên giá trị** | 9 | 9 | 8 | 8 | 9 | **8.7** |
| **4. Thuần ưu tiên ROI** (giá trị cao trước bất kể nhóm) | 6 | 6 | 8 | 5 | 6 | **6.3** |

- **PA1** vỡ vì B/C bị chặn H10, và parity 12 app cùng lúc không kiểm nổi.
- **PA2** tốt, nhưng chưa tối ưu: không tách "nhà máy" nên app đầu mỗi nhóm vẫn đắt.
- **PA4** kéo hạ tầng vào sớm ngoài kiểm soát (chase giá trị làm rối thứ tự phụ thuộc).
- **PA3 thắng:** làm **một app tham chiếu** để khoá pattern + dựng scaffolding dùng chung ("nhà máy di trú"), rồi port phần còn lại **rẻ dần**, theo **thứ tự phụ thuộc + giá trị**, xen kẽ 2 "cửa hạ tầng" (H10, GPU-route) đúng lúc cần.

## 4. PHƯƠNG ÁN ĐỀ XUẤT (PA3) — lộ trình theo đợt

**Đợt R — Tham chiếu + Nhà máy di trú** (nền cho mọi app sau)
- Nâng `thumbnail` lên **parity ≥90%** theo công thức 8 bước.
- Dựng scaffolding dùng lại: quy ước `apps/<slug>/prompts/`, helper prompt-builder ghép-fragment, "UI kit" trang tool (form nhóm điều khiển + xem-trước-prompt + lưới kết quả) trong `ltt.css`/macro Jinja, mapping model registry → `providers.py`, **test parity tự động**.
- *Xong đợt = có khuôn; app sau chỉ điền tài nguyên + lõi.*

**Đợt A1 — API quick wins:** ✅ **XONG 2026-08-01** — `taoanh` (gemini_image) +
`kichban` (youtube_script, app văn bản đầu tiên). Nhà máy chạy tốt; chỉ cần 1 sửa
dùng chung (`prompt_fragments.build` giữ literal braces). Slug đặc trưng (không
dùng từ phổ biến). Full suite 1634, kiểm URL công khai + kichban chạy thật.

**Đợt A2 — API doanh thu:** ✅ **Pha 1 XONG 2026-08-01** — `taovideo` (seedance_video):
text→video async + cost token→credit (reserve→settle), serve video theo Range. Kiểm
chuỗi async THẬT trên production (104s, 40.594 token→37 credit). Người dùng **BỎ plenx
+ gemini_video** (gemini UI đã trôi sang cookie=nhóm D). **Pha 2 (còn):** asset:// +
face-moderation + refs → đạt parity ~90%.

**Cửa H10 — R2 + file lớn** (xen giữa): `Storage.url_for` + presigned + upload thẳng browser→R2 (vượt trần 100MB). Bắt buộc trước B/C.

**Đợt B — ffmpeg:** video_chain (mở đường) → auto_sub_video (giá trị cao) → concat_pro.

**Cửa GPU-route** (xen giữa): worker nhận job theo năng lực (`requires=gpu`) chạy trên máy có card (chính máy chủ này).

**Đợt C — GPU:** video_upscale → cut_clip_short.

**Đợt S (cuối/tuỳ chọn):** seedance Prompt Studio — đánh giá lại như một dự án riêng.

**Xuyên suốt:** nhóm D loại bỏ; gemini_api_chat hoãn (quyết sau theo nhu cầu).

## 5. "Nhà máy di trú" — vì sao rẻ dần

Chi phí một app = (chi phí nhà máy, trả MỘT lần ở đợt R) + (điền tài nguyên L1 + lõi L2 + spec UI). Sau đợt R, mỗi app nhóm A chủ yếu là **copy `prompts/` + viết `jobs.py` lõi + khai manifest + ráp UI từ kit** → effort giảm mạnh. Đây là lý do PA3 thắng ô "rẻ dần".

## 6. Định nghĩa "xong" mỗi app di trú
Bảng parity ≥ 90% tính năng người dùng (trừ phần được phép lược bỏ có ghi lý do) · full pytest xanh · scan 0 · **kiểm trình duyệt + chụp ảnh 2 UI đối chiếu** · deploy + nghiệm thu credit/tính phí (nếu là tool tính tiền).

## 7. Rủi ro + cách trị
| Rủi ro | Trị |
|---|---|
| Parity kém khi làm nhiều | Chuẩn ≥90% + app tham chiếu khoá pattern + test parity |
| B/C tràn trần 100MB/100s | Bắt buộc H10 trước; upload thẳng R2; job async |
| GPU 2060 6GB nghẽn khi nhiều job | Giới hạn job GPU đồng thời (như cấu hình gốc: tối đa 2) |
| Prompt Studio 28k dòng nuốt tiến độ | Tách hẳn thành dự án riêng, không nhồi vào đợt thường |
| Đổi tài nguyên gốc (BOT vẫn chạy) | Chỉ đọc; copy kèm commit-id; hai cây mã độc lập |

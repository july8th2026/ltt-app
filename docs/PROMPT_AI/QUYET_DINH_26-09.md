# PROMPT AI — quyết định của chủ dự án, phiên 26/09/2026

Sổ ghi quyết định cho việc thiết kế lại `apps/prompt_ai_ommi`. Bằng chứng đối chiếu:
[`DOI_CHIEU_PROMPT_SEEDANCE_STUDIO.md`](DOI_CHIEU_PROMPT_SEEDANCE_STUDIO.md).

⚠️ Trạng thái: **đang brainstorm, CHƯA có spec, CHƯA viết mã.**

## Đã chốt

| # | Quyết định | Ghi chú / cái giá nếu sai |
|---|---|---|
| Q-1 | **Kho chung đặt TRONG app, mở qua ToolSpec** (phương án A). Bảng `ommi_*` giữ nguyên; app khác đọc kho qua Public API/ToolSpec của PROMPT AI | Không đụng `platform_core`. Giá: PROMPT AI thành phụ thuộc cứng của mọi app dùng kho |
| Q-2 | **Hợp đồng liên kết = "giao bài"**: nạp reference vào form app đích, khách sửa rồi tự bấm chạy | Cần endpoint "nhận reference" ở `taovideo`. Khách kiểm soát được, ít khiếu nại trừ tiền oan |
| Q-3 | **Lối vào mặc định = 2-pane Studio Kịch bản** (danh sách Brief ⟷ khung soạn) | Buộc nâng Brief thành thực thể riêng, không còn nhúng trong `AppProject.payload` |
| Q-4 | **Gộp `character_lock` của `prompt_canh` vào PROMPT AI, rồi mới xoá `apps/prompt_canh`** | Giữ bản gốc làm đối chứng tới khi bước khoá nhân vật chạy đúng |
| Q-5 | **Một spec cho cả 5 pha** (điều phối đã nêu lo ngại 4–5 dự án con; chủ dự án chốt vậy) | Spec chia 5 pha có ranh giới deploy rõ bên trong, để vẫn đóng được từng pha |
| Q-6 | **Bundle mở, MIỄN PHÍ** — khách xem/copy meta-prompt đã render để tự dán sang LLM riêng | Giá: không thu credit bước LLM đắt nhất, và công khai bí quyết meta-prompt |
| Q-7 | **Iterate: 2 lượt đầu miễn phí mỗi KỊCH BẢN, sau đó thu** | Đếm theo kịch bản (không theo user/ngày), bộ đếm **phải nằm trong CSDL** — nếu không sẽ thành LLM miễn phí vô hạn |
| Q-8 | **Pha đầu chỉ giao bài cho `taovideo`** (Tạo Video Seedance, app sinh video duy nhất đang `released`) | `taoanh` còn `lifecycle="development"` |
| Q-9 | **Chuyển toàn bộ mẫu meta prompt từ Studio sang PROMPT AI** | 12 mẫu (9 `gemini_style` + 3 `storyboard`), kèm 21 `image_gen_template` thật và 13 snippet. **Bắt buộc kèm bảng quy đổi placeholder + bộ kiểm** (§8.3) |
| Q-10 | **Khách chia sẻ kho cho nhau bằng MÃ/LINK — KHÔNG có danh mục công khai** | Đủ ý "chia sẻ cho nhau" mà ta không thành nền tảng phát hành nội dung ⇒ nghĩa vụ kiểm duyệt nhỏ nhất. Mở danh mục công khai sau nếu cần |
| Q-11 | **Bật rollout production luôn** (`LTT_PROMPT_AI_OMMI_ROLLOUT`) — chưa có khách thật, không lo dữ liệu | Đã đo 26/09: biến chưa đặt ⇒ app đang trả `503` |
| Q-12 | **Storyboard chỉ để THAM CHIẾU trong PROMPT AI — KHÔNG đẩy sang Seedance Video** | Khớp với bản gốc: `to-video` của nguồn cũng chỉ tạo bản ghi nội bộ, và `videos_v2` chỉ 2 dòng |
| Q-13 | **Giao bài sang video: MỘT bài MỘT lần, y như bản gốc** | Không làm hàng đợi nhiều bài ở `taovideo`. Giá: kịch bản 12 cảnh là 12 lần đi qua lại |
| Q-14 | **8 tính năng đo được là "xây mà chưa ai dùng" VẪN xây** (Profiles, `characters`/`outfits`/`poses`/`backgrounds`, `face_embeddings`, kế thừa style, budget cap) | Điều phối đã nêu bằng chứng 0 dòng (§8.2) và khuyến nghị bỏ; chủ dự án chốt vẫn cần. Giá: thêm mặt phải bảo trì không có bằng chứng ai cần |
| Q-15 | **Ảnh khách TỰ TẢI LÊN đi sang `taovideo` bằng đường D**: khai cạnh `("prompt_ai_ommi","taovideo")` trong `tools/lint_app_contract.py:85 APP_DUOC_DUNG_APP`, dùng lại `apps/taovideo/refs.py` | ⛔ KHÔNG sửa `platform_core`/`server`. Ảnh **sinh bằng AI** đã đi được sẵn qua artifact id (`server/api/uploads.py:314` cố ý không khoá theo app). Giá: hai app dính vào nhau; app thứ ba muốn nhận ảnh phải khai thêm một cạnh. Giảm thiểu: cạnh giới hạn ở **đúng một module** `apps.taovideo.refs` |

## Hệ quả kỹ thuật buộc phải có (không phải lựa chọn)

| # | Việc | Vì sao |
|---|---|---|
| H-1 | Bảng **bindings** `thẻ ↔ variant` (`@IMG_k`/`@VID_k`) | Q-2 không thể đúng nếu không biết thẻ nào là ảnh nào (N-2) |
| H-2 | Truyền ảnh tham chiếu + `camera`/`lighting`/`mood` thật khi giao bài | Đang vứt sạch (N-1) |
| H-3 | **Phép kiểm ở BIÊN**: prompt có `@IMAGE_k` mà không có reference tương ứng ⇒ **đỏ** | Thuốc cho dạng lỗi `cho-noi-hai-module-vut-truong-im-lang` |
| H-4 | Bảng quy đổi placeholder CHỮ HOA ⟷ bộ hiện tại + bộ kiểm "mọi placeholder đều có người cấp giá trị" | Q-9 (§8.3) |
| H-5 | Thêm **cột mức chia sẻ** cho `ommi_meta_prompt`/`ommi_style`/`ommi_prompt_snippet`/… (riêng / chia sẻ bằng mã / catalog) | Q-10 — mô hình hiện tại chỉ có 2 mức |
| H-6 | Đường ống giao bài dựng trên `platform_core/storage.py` + `phat_media.py`, **không** import app→app, **không** path đĩa | §9 — bản gốc chạy được vì cùng tiến trình cùng đĩa |
| H-7 | Bộ đếm lượt iterate miễn phí nằm trong CSDL, gắn với kịch bản | Q-7 |

## Còn chờ chủ dự án

- Danh sách tối ưu hoá logic vận hành mà chủ dự án nói sẽ liệt kê.

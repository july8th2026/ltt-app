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
| Q-16 | **Mang cơ chế CHIA LÔ của `prompt_canh` sang `prompt_ai_ommi`** — chia lô sinh cảnh + lịch sử chống trôi ngữ cảnh — rồi MỚI xoá `prompt_canh`. ⇒ thêm **pha 6** vào plan; **E5 bị chặn cho tới khi pha 6 xong** | Đo thật **2 lần** ở `scene_count=20` (làn E, 27/09): cả hai lần trả **19/20 cảnh**, và độ dài trường `prompt` **co dần theo thứ tự cảnh** (159→87 và 165→~90 ký tự) khi chỉ dùng 67 %/69 % của `_MAX_TOKENS = 8192` ⇒ **chất lượng suy TRƯỚC khi chạm trần cứng**, nên nâng trần token ⛔ không phải thuốc. App cũ chia lô (`LO_BUOC2=10`, `LO_BUOC3=5`, `LICH_SU_CANH=5`) đỡ tới **250 cảnh**. Giá: mỗi job gọi LLM **2–5 lượt** thay vì 1 ⇒ giá vốn tăng thật, bảng giá phải tính theo số lô; thêm một pha vào plan. ⛔ Không chọn "giữ cả hai app": hai đường làm cùng một việc là đúng thứ chủ dự án yêu cầu loại bỏ |
| Q-17 | **Giữ trần bán 20 cảnh, KHÔNG hạ tạm về 15** — thêm cảnh báo trên giao diện rằng kịch bản trên 15 cảnh có thể phải chạy lại từng cảnh | ⛔ **Không có khoản thu sai**: bậc giá `2 + ceil(n/3)*2` thô nên **19 và 20 cảnh CÙNG giá 16 credit** (đo bằng `manifest._director_cost`, không suy từ số lượng). Cảnh thiếu thì `jobs.py:34` chèn một cảnh **tự khai** *"Cảnh chưa được AI tạo; cần chỉnh hoặc tạo lại."* ⇒ ⛔ không phải cắt âm thầm. Hạ 20→15 rồi nâng lại sau pha 6 là công thừa. Giá: khách chọn 20 vẫn có thể nhận một cảnh placeholder cho tới khi pha 6 xong |

⚠️ **Một kết luận đã bị RÚT LẠI, ghi ở đây để không ai dùng lại nó.** Làn E báo
*"khách trả tiền cho 20 cảnh mà nhận 19 cảnh thật + 1 placeholder"*. Sai: kiểm
bằng chính hàm tính giá cho **0 credit lệch**. ⭐ Một câu về **tiền** phải kiểm
bằng **hàm tính giá**, ⛔ không suy từ số lượng — một bậc giá thô làm hai số
lượng khác nhau cùng giá. Làn E đã tự rút lại sau khi tôi đưa số.


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

## Q-18 — HÌNH DẠNG của pha 6 (chốt 28/09/2026)

**Chốt: MỘT job, chia lô bên trong worker, THÊM một cờ huỷ mà worker kiểm ở đầu
mỗi lô.** Khách dừng được ở **ranh lô**, ⛔ không phải giữa một lô.

### ⚠️ Đính chính một dữ kiện tôi đã nói sai khi đặt câu hỏi

Tôi trình bày *"nhiều lô nhỏ"* như thứ **`prompt_canh` đã chạy thật nên có mã để
port"*. Đọc mã thì ⛔ **KHÔNG**:

| | `prompt_canh` thật sự làm gì |
|---|---|
| Job | **MỘT** — `job_types=("prompt_canh.run",)` |
| Chia lô | **bên trong worker**: `services/kich_ban.py::chay()` lặp `LO_BUOC2 = 10`, `LO_BUOC3 = 5`, báo qua `tien_do(pt, mo_ta)` |
| Tiền | `credit_cost=_gia` trả **0** ở tầng job; tiền thu **từng lượt gọi model** qua `runtime_noi_bo.luong` |
| Dừng giữa đường | ⛔ **không có** — chạm trần `3600 s` thì, theo đúng chú thích trong `manifest.py`, *"khách đã trả mà không nhận gì"* |

Nên nó là *một job chia lô bên trong* **cộng** thu tiền theo lượt gọi — có cái hay
của "nhiều lô" về **tiền**, ⛔ không có cái hay về **dừng giữa đường**.

⇒ Sau khi biết điều đó, chủ dự án chốt lại: port hình dạng đã chạy thật, rồi thêm
đúng phần còn thiếu (cờ huỷ). ⭐ Ghi lại cả lần nói sai này vì nó là lý do câu hỏi
phải hỏi **hai lần**, và vì một quyết định dựa trên một dữ kiện sai thì không phải
một quyết định.

### Vì sao hình dạng này, nói theo cái giá

| | Port `prompt_canh` + cờ huỷ (CHỐT) | Nhiều job nhỏ |
|---|---|---|
| Mã để port | `kich_ban.chay` + `tien_do` **đã chạy thật tới 250 cảnh** | ⛔ không có, phải tự dựng |
| Sổ credit | **MỘT** bút toán, tiền theo lượt gọi — khuôn `_gia() -> 0` đã giải | nhiều bút toán cho một lượt ⇒ đụng `credit.py`, tệp **có tiền thật** |
| `jobs.py` | ⛔ không đụng | phải dựng sổ gom tiến độ nhiều job |
| Khách dừng | ở **ranh lô** (`LO_BUOC3 = 5` cảnh) | ở từng cảnh |
| Rủi ro | thấp | cao — hai tệp có bút toán thật |

⇒ Chênh lệch **duy nhất** khách thấy được là hạt dừng: ranh lô 5 cảnh so với từng
cảnh. Cái giá để đi từ 5 xuống 1 là chạm hai tệp giữ sổ tiền. ⛔ Không đáng.

### Ba điều bản port PHẢI mang theo, ⛔ không được bỏ

1. **`credit_cost` trả 0 kèm lý do.** Khai một giá ở tầng job là **thu hai lần**
   cho cùng một việc (`runtime_noi_bo.luong` đã giữ credit theo trần token rồi hoàn
   về token thật). Cùng khuôn `apps/chatltt/gia_nghien_cuu.py`.
2. **Điều kiện TRƯỚC KHI NỘP ở `routes.py`**, vì `0` mở một lỗ: job vào hàng đợi mà
   **không giữ chỗ**, nên tài khoản 0 credit vẫn nộp được, worker vẫn chạy, rồi lượt
   model đầu trả `ThieuCredit` — khách chờ vô ích. Đó là một **điều kiện**, ⛔ không
   phải một **giá**, nên nó không nằm trong sổ tiền.
3. **Trần thời gian phải KHỚP trần số cảnh, và có phép kiểm chốt bất đẳng thức đó.**
   `prompt_canh` làm điều này ở `tests/test_1105`: `250 cảnh = 76 lượt gọi`,
   `3600 s / 76 = 47 s` mỗi lượt. Hai con số ấy trôi khỏi nhau thì khách trả tiền
   rồi chết ở trần.

### Cờ huỷ — phần DUY NHẤT là mã mới

- Worker kiểm cờ **ở đầu mỗi lô**, ⛔ không kiểm giữa lô: một lô đã gọi model là đã
  tiêu tiền, cắt giữa lô làm khách trả mà không nhận.
- Huỷ ⇒ job kết thúc **THÀNH CÔNG một phần**, mang theo số cảnh đã sinh. ⛔ Không
  phải `FAILED`: khách chủ động dừng thì đó không phải một lỗi, và một `FAILED`
  mang dữ liệu dùng được là đúng hình dạng `hai-trang-thai-gop-thanh-mot-gia-tri`.
- Tiền tự đúng, ⛔ không cần hoàn: `runtime_noi_bo.luong` đã thu theo từng lượt gọi
  nên lô chưa chạy thì chưa thu.

## Còn chờ chủ dự án

- Danh sách tối ưu hoá logic vận hành mà chủ dự án nói sẽ liệt kê.

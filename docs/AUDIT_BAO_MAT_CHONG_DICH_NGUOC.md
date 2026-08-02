# AUDIT BẢO MẬT — Chống dịch ngược (anti-reverse-engineering) từ phía web

> Lập 2026-08-02. Câu hỏi: web đưa cho công chúng → dev có đọc được code/workflow?
> UI chỉ hiển thị, bộ máy xử lý ngầm đúng không? Họ truy ngược tự xây bot được không?
> Audit sâu, liệt kê lỗ hổng dev khai thác + phương án vận hành để KHÔNG truy ngược được.

## 0. TRẢ LỜI THẲNG (sự thật kỹ thuật)

**Q: Dev đọc được code/workflow đang vận hành không?**
→ **KHÔNG đọc được code server.** Nền tảng render HTML ở máy chủ (Jinja + HTMX);
`jobs.py`, ghép prompt, gọi model, engine (cutclipshort/codex), khóa API, sổ credit
**chạy trong tiến trình web/worker — KHÔNG BAO GIỜ gửi xuống trình duyệt**. Dev chỉ
thấy: HTML/CSS/JS-nội-tuyến, danh sách endpoint + hình dạng payload (tab Network),
phản hồi, file `/static/`. Họ **không** lấy được: prompt (trừ chỗ rò bên dưới), khóa,
logic jobs, mã engine, logic credit, DB.

**Q: UI chỉ hiển thị, bộ máy xử lý ngầm — đúng không?**
→ **ĐÚNG.** Đây là mô hình "thin client, fat server" — client là lớp mỏng hiển thị,
mọi giá trị + cưỡng chế nằm ở server. `/openapi.json` + `/docs` **đã TẮT ở production**
(chỉ bật ở DEVELOPMENT) → không công bố toàn bộ hợp đồng API.

**Q: Truy ngược từ web để tự xây bot được không?**
→ **Không dựng lại được backend của bạn** (nó không nằm ở client). NHƯNG dev tinh có thể:
(a) **sao chép prompt engineering** NẾU bạn lộ (endpoint xem-trước prompt); (b) **biết
bạn dùng AI nào** qua model ID trong UI; (c) **script API của bạn** để lạm dụng nền tảng
như một backend rẻ (bulk, bán lại). Họ **không** lấy được khóa hay mã engine.

**Sự thật cứng:** KHÔNG thể làm code client "vô hình" (trình duyệt phải chạy nó);
obfuscate/minify chỉ làm chậm, không chặn. Phòng thủ đúng = **không để gì giá trị ở
client + mọi thứ server cưỡng chế + chặn scripting/lạm dụng**.

## 1. CÁI GÌ CLIENT THẤY vs CÁI GÌ ẨN

| Lộ ra trình duyệt (không tránh được) | Ẩn hoàn toàn server-side |
|---|---|
| HTML/CSS/JS nội tuyến, `/static/*` (ltt.css, htmx) | `apps/*/jobs.py` (gọi model, xử lý) |
| URL endpoint + field form + JSON/SSE shape | Ghép prompt + **fragment prompt** (IP) |
| Model ID nếu hiển thị (đang LỘ — xem V2) | Khóa API (APIKEYS mã hoá) |
| Prompt đã ghép NẾU có endpoint preview (đang LỘ — V1) | Engine cutclipshort / sidecar codex |
| Presigned URL R2 (có hạn giờ) | Sổ credit, DB, telemetry |
| Thông báo lỗi (nếu verbose) | Orchestration/hàng đợi/worker |

## 2. DANH MỤC LỖ HỔNG + theo APP + mức độ + dev khai thác thế nào

### Nhóm A — Rò rỉ IP (mất "bí kíp")
- **V1 [CAO] `thumbnail /preview` trả về PROMPT ĐÃ GHÉP** (`routes.py:125`
  `<pre>{prompt}</pre>`). Dev bấm "xem trước" → thấy trọn prompt engineering (fragment
  phong cách/trend/text-style ghép lại) → **đối thủ copy bí kíp prompt**. Đây là rò rỉ
  IP lớn nhất. (Các app khác không có preview-prompt.)
- **V2 [TRUNG] Model ID thật lộ trong UI:** chataistudio hiện `gpt-5.6-sol…`
  (`chataistudio.html:16-17,44`), taoanh/taovideo/thumbnail hiện `gemini-*`/`seedance-2.0`
  qua option value. → Dev biết chính xác **stack provider** (Google Gemini + BytePlus
  Seedance + OpenAI Codex) → dễ tự dựng đối thủ / mặc cả.
- **V3 [THẤP] Cấu trúc trong JS/template** (tên endpoint, luồng upload→queue→poll,
  asset://) — lộ HÌNH DẠNG workflow, không lộ code. Giá trị thấp.

### Nhóm B — Lạm dụng / script API (dùng nền tảng làm backend rẻ)
- **V4 [TRUNG-CAO] KHÔNG rate-limit ở endpoint tạo + endpoint MIỄN PHÍ.** Chỉ login có
  limiter (5/60s, `server/auth/rate_limit.py`). `/estimate`, `/translate` (đốt quota
  Gemini!), `/preview`, `/upload-url` gọi được **không tốn credit** → script để: đốt
  quota dịch, mint presigned PUT vô hạn, dò giá. `/queue`,`/send` có credit chặn nhưng
  script vẫn bulk-dùng nhanh hơn UI. (Audit chức năng đã ghi: taoanh/kichban bỏ
  rate-limit của nguồn, chỉ dựa credit.)
- **V5 [TRUNG] User đăng nhập script thẳng endpoint trả phí** (bỏ qua UI) → bulk/tự động
  hoá + **bán lại dịch vụ**. Không phải lỗi (credit chặn) nhưng là hành vi cần phát hiện.

### Nhóm C — Client-trust (tin client sai)
- **V6 [OK] Không tìm thấy lỗ hổng tin-client về TIỀN.** Giá credit tính server
  (`manifest._cost`); thời lượng đọc client chỉ để ước tính (worker đo lại thật). Tốt.

### Nhóm D — Lộ dữ liệu / hạ tầng
- **V7 [THẤP] Presigned R2 URL** chia sẻ được trong TTL. TTL ngắn → thấp.
- **V8 [THẤP] Lỗi verbose** — phần lớn đã ẩn (kichban vừa sửa); còn vài chỗ P2.
- **V9 [OK] /openapi.json + /docs TẮT ở prod.** Tốt — không công bố hợp đồng API.

## 3. BỐN PHƯƠNG ÁN vận hành chống dịch ngược — chấm điểm (1–10)

| Tiêu chí | PA-1 Obfuscate client | PA-2 Thin-client hardening | PA-3 API-gateway ký request | PA-4 PA-2 + watermark + anti-abuse |
|---|---|---|---|---|
| Chặn đọc IP thật | 3 (client vẫn đọc được) | **9** (dời/ẩn IP khỏi client) | 9 | **9** |
| Chống script/lạm dụng | 2 | 8 | **9** (ký request khó giả) | **9** |
| Chống dựng bot đối thủ | 3 | 8 | 8 | **9** (+răn đe pháp lý/watermark) |
| Công sức | **8** (thấp) | 7 | 3 (nặng) | 5 |
| Rủi ro vỡ UX | 6 | **9** | 5 (dễ chặn nhầm) | 8 |
| Giá trị thực (ROI) | 2 (an toàn giả) | **9** | 6 | 8 |
| **Tổng** | 24 | **50** | 40 | 48 |

- **PA-1 Obfuscate/minify client**: an toàn GIẢ — dev vẫn đọc được logic client (vốn
  không chứa gì giá trị). Không khuyến nghị làm chính.
- **PA-2 Thin-client hardening (ĐỀ XUẤT)**: đánh đúng lỗ hổng thật — dời/ẩn IP khỏi
  client + rate-limit + Turnstile + lỗi chung + WAF biên. ROI cao, ít vỡ UX.
- **PA-3 API-gateway ký request (HMAC/nonce/device)**: chống script mạnh nhất nhưng
  nặng + dễ chặn nhầm người thật; quá mức ở giai đoạn này.
- **PA-4 PA-2 + watermark output + phát hiện lạm dụng + ToS**: PA-2 cộng răn đe — tối
  ưu DÀI HẠN khi có doanh thu.

**ĐỀ XUẤT: PA-2 ngay** (đóng lỗ hổng + rate-limit + WAF), tiến tới **PA-4** khi mở rộng.

## 4. BIỆN PHÁP CỤ THỂ (PA-2 → ánh xạ lỗ hổng)

1. **Bỏ/khoá endpoint xem-trước prompt** (V1): bỏ `thumbnail /preview` trả prompt thô;
   nếu giữ "xem trước" thì chỉ hiện MÔ TẢ (không hiện chuỗi prompt ghép). *Ưu tiên cao.*
2. **Ẩn/alias model ID** (V2): UI dùng tên thân thiện ("Ảnh Nhanh/Chuẩn/Cao", "Video
   Chuẩn"), map alias→model thật ở SERVER; không render `m.id` provider. Áp mọi app.
3. **Rate-limit per-user mọi endpoint** (V4/V5): mở rộng `RateLimiter` sang /queue,
   /send, /translate, /estimate, /preview, /upload-url (vd 30/phút/user; endpoint tốn
   quota ngoài như /translate siết chặt hơn). + **Turnstile** cho hành động nhạy cảm.
3b. **/translate tính credit nhỏ hoặc gộp vào lượt** (V4): đừng để gọi Gemini miễn phí.
4. **WAF / rate-limit ở biên Cloudflare** (trùng backlog 7.3): chặn bot/scan trước origin.
5. **Lỗi chung cho user** (V8): không lộ nội bộ/provider (kichban đã làm — rà nốt).
6. **Giữ nguyên "fat server"** (đang đúng): tuyệt đối không đẩy prompt/logic/giá xuống JS.
7. **(PA-4 sau)** watermark ẩn trên ảnh/video output; phát hiện hành vi bất thường
   (một user tạo job dày đặc như script) → cảnh báo/khoá; ToS cấm scrape/bán lại.

## ĐÃ LÀM (2026-08-02) — PA-2, người dùng chốt: GIỮ tên model thật (bỏ V2 alias)

- **V1 đóng:** `thumbnail /preview` KHÔNG còn trả prompt ghép — chỉ hiện **tóm tắt lựa
  chọn** (Chủ đề/Kiểu chữ/Phong cách/Trend/Ngôn ngữ/Tỉ lệ, nhãn thân thiện). Verify THẬT
  trên browser: preview ra "Kiểu chữ: Bold Impact · Phong cách: Chuyên nghiệp tối giản…",
  KHÔNG lộ chuỗi prompt.
- **V4/V5 đóng (một phần):** middleware `server/usage_rate_limit.py` — rate-limit
  per-user cho MỌI POST app (general 120/phút; endpoint miễn-phí/đốt-quota
  translate/preview/estimate/upload-url siết 30/phút); 429 khi vượt. Trung tâm ở
  middleware → tự áp mọi app + tương lai. test_86 chốt. (Trước đó taovideo /translate đã
  thêm CSRF + threadpool ở đợt audit chức năng.)
- **V8:** lỗi provider đã ẩn (kichban) ở đợt trước.
- **V2 GIỮ NGUYÊN theo quyết định người dùng** (hiện tên model thật — minh bạch/thương hiệu).

### WAF / edge Cloudflare — BẠN thao tác (dashboard, không làm từ code)
Vào Cloudflare `app.lttstudios.com`:
1. **Bot Fight Mode**: bật (Security → Bots) — chặn bot/scraper cơ bản.
2. **Rate limiting rules** (Security → WAF → Rate limiting):
   - Rule 1: path chứa `/queue` hoặc `/send` → >20 req/phút/IP → Block/Challenge.
   - Rule 2: path kết `/translate|/estimate|/preview|/upload-url` → >40 req/phút/IP → Challenge.
3. **Managed WAF ruleset**: bật (chặn SQLi/XSS/scan phổ biến trước origin).
Middleware per-user (đã làm) + WAF per-IP (bạn bật) bổ trợ nhau.

## 5. CÂU HỎI CẦN CHỐT
1. **Phương án** — PA-2 (đề xuất) / PA-4 (PA-2 + watermark + anti-abuse) / PA-3 / PA-1?
2. **Phạm vi làm ngay** — nhóm rò-rỉ-IP (V1 preview + V2 alias model) trước, hay gồm cả
   rate-limit (V4/V5) + WAF trong đợt này?
3. **Model alias** — bạn muốn UI hiện tên thương mại thế nào (vd "Ảnh Nhanh/Chuẩn/Cao")?

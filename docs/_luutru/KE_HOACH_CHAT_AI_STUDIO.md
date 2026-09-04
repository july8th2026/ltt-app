# Kế hoạch xây App CHAT AI STUDIO (từ AI Creative Studio / module `codex` — BOT GEMINI)

> Lập 2026-08-01. Quy trình mới: user chỉ định app←module, Claude phân tích sâu +
> lập phương án + chấm điểm + hỏi để chốt. **Chưa build.** Nguồn: kiểm kê module
> `codex` (BOT GEMINI) + rà nền tảng (APIKEYS, provider OpenAI-compat, mẫu chat).

## 0. PHÁT HIỆN CỐT LÕI (đọc kỹ — nó đổi cả cách làm)

"AI Creative Studio" trong BOT GEMINI thực chất là module **`codex`**. Nó **KHÔNG**
gọi OpenAI SDK hay HTTP thường. Nó **chạy một tiến trình `codex.exe` (Codex CLI)
cục bộ** làm "app-server", nói chuyện qua SDK `openai-codex`, và **xác thực bằng
phiên đăng nhập ChatGPT (OAuth device-code)** — hoặc tuỳ chọn API key.

Ba sự thật quyết định:
1. **Auth = phiên đăng nhập ChatGPT, MỘT tài khoản sống tại một thời điểm**, dùng
   chung cho mọi user, chỉ xoay khi hết quota. **Không multiplex được cho nhiều
   khách trả tiền**, và **bán lại phiên ChatGPT consumer nhiều khả năng vi phạm
   ToS**. → Đây là **rào cản lớn nhất** cho app "hướng tới khách hàng".
2. **`codex.exe` là binary Windows cục bộ** (có cả đường dẫn npm hardcode theo máy),
   chạy sandbox Windows nâng quyền. Ràng buộc desktop nặng.
3. **Codex bản chất là AGENT LẬP TRÌNH**; chat + tạo ảnh là tính năng CỦA agent đó
   (ảnh do agent tự gọi "image tool" giữa lượt). Tính năng "code" đan xen qua
   `mode` (chat/work/plan) + sandbox + file ops + MCP.

→ **Không thể "kế thừa triệt để cách gọi Codex" theo nghĩa đen** cho một SaaS
internet đa khách: cái "cách gọi" đó = codex.exe cục bộ + login ChatGPT dùng chung.
Nhưng **có thể kế thừa TRỌN VẸN phần đáng giá**: *workflow + trải nghiệm* (chat
streaming SSE, mô hình hội thoại per-user, tạo ảnh hiện thẳng trong phiên, đo credit),
chỉ **thay tầng vận chuyển** (Codex CLI → OpenAI API bằng API key) — hợp pháp,
multiplex được, tính tiền được.

## 1. Bản đồ lớp: kế thừa gì / thay gì

| Phần | Ở BOT GEMINI | Quyết định |
|---|---|---|
| 🟢 UX streaming SSE token | `api.py:707` StreamingResponse + `codex.js:551-673` fetch reader | **KẾ THỪA** (viết lại theo nền tảng, giữ giao thức) |
| 🟢 Mô hình hội thoại per-user | project→thread, SQLite, mọi route check `user_id` (`store.py`) | **KẾ THỪA** → Postgres (bảng mới) per-user |
| 🟢 Ảnh hiện thẳng trong chat | agent phát `imageGeneration` → server lưu file → SSE `image` → blob proxy | **KẾ THỪA mẫu** (đổi nguồn ảnh) → lưu R2 |
| 🟢 Đo credit theo user | `_consume_quota_or_raise` + `token_usage` từ stream | **KẾ THỪA** → sổ credit H3 (theo token + theo ảnh) |
| 🔴 Tầng gọi model | `runtime.py` PlusRuntime + `thread.turn` (Codex CLI) | **THAY** bằng OpenAI API client (streaming) |
| 🔴 Auth/pool | login ChatGPT + `pool.py`/`auth_store.py` (1 account chung) | **THAY** bằng API key trong APIKEYS (đã có category `chat`/`image`) |
| ⚫ Code/sandbox/file/MCP | mode work/plan, `files.py`, diff, `mcp_store.py` | **BỎ** (user yêu cầu không xây code) |
| ⚫ codex.exe + sandbox Windows | `runtime.py:121-224` | **BỎ** |

Nền tảng đã có sẵn để đỡ: APIKEYS category `chat`+`image`; provider OpenAI-compat
**apiai** + **cheapkeyai** (Bearer, `/chat/completions`, `/images/generations`);
mẫu gọi model qua httpx + `api_pool.lay_key`; app ảnh **taoanh** (tái dùng cho ảnh).

## 2. Vấn đề kiến trúc riêng của CHAT (khác mọi app đã làm)

Mọi app tới giờ theo **job-queue async** (submit→poll). **Chat cần tương tác/độ trễ
thấp + streaming token**, chạy trong **tiến trình WEB** (không phải worker). Hệ quả:
- **SSE streaming** trong web process: web gọi OpenAI `stream=True`, chuyển tiếp token
  về trình duyệt. Giữ đúng UX gốc. Lưu ý: **trần Cloudflare 100s** — chat thường
  <100s; đặt **giới hạn token đầu ra + timeout** để không chạm 524. Quyết toán credit
  **sau khi stream xong** (đếm token thật).
- Ảnh: gọi image API (vài giây) → chèn vào transcript. Có thể chạy ngay trong request
  chat hoặc như một bước nhỏ; **không cần worker** nếu < ~30s.

→ Đây là **năng lực mới của nền tảng**: một route streaming trong web. Sẽ làm gọn,
có cap token + timeout, và tách "chat client" thành lớp dùng lại được.

## 3. BA PHƯƠNG ÁN cho tầng lõi (tích hợp + auth) — chấm điểm

Thang 1–10 (cao = tốt). Trọng số nghiêng về **khách-hàng + hợp pháp + vận hành**.

| Tiêu chí | PA-1 OpenAI trực tiếp (API key) | PA-2 Gateway OpenAI-compat | PA-3 Giữ Codex CLI + login ChatGPT |
|---|---|---|---|
| Kế thừa "cách gọi Codex" đúng nghĩa đen | 6 | 5 | **10** |
| Kế thừa workflow/UX (chat+ảnh+per-user) | 9 | 9 | 9 |
| Khả thi SaaS đa khách / scale | **10** | **10** | 2 |
| Hợp pháp (ToS) | **10** | 8 | 2 |
| Chi phí vận hành | 6 | **9** | 5 |
| Công sức build | 6 | **8** | 4 |
| UX khách (streaming + ảnh sáng tạo) | **9** | 8 | 9 |
| Độ bền/không phụ thuộc máy | **10** | **10** | 2 |
| **Tổng (thô)** | **66** | **67** | 43 |

- **PA-1 — OpenAI trực tiếp bằng API key (Responses API)**: gọi thẳng OpenAI bằng key
  lưu trong APIKEYS. Giữ được **GPT-5 family + "image tool" tự động giữa lượt** (đúng
  chất "AI Creative Studio"). Hợp pháp, multiplex, tính tiền theo token. Đắt hơn.
- **PA-2 — Gateway OpenAI-compat (apiai/cheapkeyai, ĐÃ tích hợp)**: rẻ hơn (đại lý),
  dùng `/chat/completions` (Chat Completions, không phải Responses) → **ảnh = bước
  tường minh** (nút 🎨 → gọi image API), không phải agent tự quyết. Tái dùng nhiều
  code sẵn có (provider + taoanh image). Rẻ + nhanh làm, kém "tự động" một chút.
- **PA-3 — Giữ Codex CLI + login ChatGPT**: kế thừa đúng nghĩa đen nhưng **một tài
  khoản dùng chung cho mọi khách**, ToS rủi ro, không scale, trói Windows/sandbox.
  **Không hợp cho app bán cho khách.** Chỉ dùng được cho nội bộ/1 tenant.

**ĐỀ XUẤT: PA-1 làm xương sống** (đúng chất "Creative Studio", hợp pháp, bền), **kiến
trúc provider-abstracted để cắm được PA-2 (gateway) như đòn bẩy chi phí**. Tức: viết
một `chat client` trừu tượng; admin chọn dùng key OpenAI (Responses, ảnh tự động) hay
key gateway (Chat Completions, ảnh tường minh). Bắt đầu MVP với một đường, mở đường kia
sau.

## 4. Hai cách "tạo ảnh trong phiên chat"

- **4A. Image tool tự động (Responses API)**: model tự quyết tạo ảnh giữa câu trả lời
  (đúng gốc Codex). Chỉ OpenAI, đắt hơn, luồng stream phức tạp hơn (bắt event tool).
- **4B. Tường minh 🎨 (khuyến nghị MVP)**: nút/lệnh "🎨 tạo ảnh" trong khung chat →
  gọi image API → **chèn ảnh thẳng vào transcript**, lưu R2. Rẻ, **tái dùng code
  taoanh** (Gemini image đã dựng+kiểm), độc lập provider chat. Vẫn đúng yêu cầu "tạo
  ảnh trực tiếp trong phiên chat". (Chính BOT GEMINI cũng có nút 🎨 chèn tiền tố.)

## 5. Cá nhân hóa + lưu trữ (per-user)

- Postgres: bảng `chat_conversation` (id, user_id, title, custom_instructions,
  model, created/updated) + `chat_message` (conversation_id, role, content, image_key,
  tokens, created). Mọi truy vấn lọc `user_id` (bất biến A-không-đọc-được-B).
- Ảnh sinh ra → **R2** (`chatai/{user}/{conv}/{id}.png`), hiện inline + tải được.
- **Custom instructions per hội thoại** (system prompt riêng) = phần personalization
  chính, kế thừa `developer_instructions` của gốc. (Tuỳ chọn: 1 "custom instruction"
  mặc định cấp user.)
- Nén lịch sử khi dài (tóm tắt) — kế thừa ý tưởng compaction, làm sau nếu cần.

## 6. Credit (đề xuất, admin chỉnh được — tỉ giá Q31: 1 credit = 100đ)

- **Chat**: theo token thật provider trả (input+output). Đề xuất quy đổi
  `credit = ceil(chi_phí_token_VND / 100)` + markup %. Giữ chỗ ước tính theo độ dài
  prompt, quyết toán theo `usage` thật (giống seedance token-based).
- **Ảnh**: giá cố định theo model/kích thước (như taoanh) — vài chục credit/ảnh.
- Con số cụ thể để bạn chốt (mục Câu hỏi).

## 7. Lộ trình build (sau khi bạn chốt)

1. **Nền tảng**: thêm provider `openai` (Responses) và/hoặc dùng gateway sẵn; lớp
   `chat client` streaming trừu tượng; route SSE trong web (cap token+timeout).
2. **DB**: migration `chat_conversation` + `chat_message`.
3. **App `chataistudio`**: manifest (không job_types nếu chat chạy trong web; hoặc
   job cho ảnh nếu cần) + routes (page, /send SSE, /image, /conversations CRUD) +
   template chat (khung hội thoại, streaming, 🎨, custom instructions) + credit.
4. **Nghiệm thu THẬT** trình duyệt + public URL (chat stream, ảnh inline, per-user,
   trừ credit) — theo lệ đã thành công ở 2 app trước.

## 8. Rủi ro & cách chặn

| Rủi ro | Chặn |
|---|---|
| Cần **API key OpenAI có billing** (hoặc key gateway) | Bạn cấp key → nhập APIKEYS (như R2/ModelArk đã làm) |
| Streaming chạm trần CF 100s | Cap token đầu ra + timeout; đa số reply <100s |
| SSE trong web process tốn thread | Giới hạn phiên đồng thời/user; reply có cap |
| Chi phí token khó lường | Giữ chỗ→quyết toán theo `usage` thật; markup % |
| Lạm dụng (spam chat tốn tiền) | Trừ credit mỗi lượt + rate-limit/user |

## 9. CÂU HỎI CẦN BẠN CHỐT (đưa sẵn lựa chọn)

1. **Tầng lõi/auth** — PA nào? (đề xuất PA-1 OpenAI trực tiếp; PA-2 gateway rẻ hơn;
   PA-3 giữ Codex login — không khuyến nghị cho khách).
2. **Cách tạo ảnh trong chat** — 4B tường minh 🎨 (rẻ, tái dùng taoanh — khuyến nghị)
   hay 4A image-tool tự động (OpenAI Responses, đắt, "sáng tạo" hơn)?
3. **Model chat** — GPT-5 family (flagship, đắt) / GPT-4o-class (rẻ, nhanh) / để admin
   cấu hình nhiều model cho user chọn?
4. **Phạm vi lưu trữ MVP** — danh sách hội thoại phẳng + custom instructions (khuyến
   nghị) hay đủ "project → thread" như Codex?
5. **API key**: bạn sẽ cấp key OpenAI (và/hoặc gateway) để nhập APIKEYS chứ? (chat
   không chạy được nếu chưa có key).

## 10. QUYẾT ĐỊNH ĐÃ CHỐT (2026-08-01, người dùng)

1. **Tầng lõi = PA-3**: giữ **Codex CLI** (port module `codex` gần nguyên trạng).
2. **Auth = đăng nhập ChatGPT (OAuth)** — người dùng **xác nhận hiểu rủi ro** ToS/ban.
3. **Ảnh = image-tool tự động** của agent Codex (đúng gốc).
4. **Model = admin cấu hình nhiều, user chọn** (Codex enumerate model live).
5. **Lưu trữ = đầy đủ project → thread** (per-user).
6. **Runtime = sidecar riêng** (dịch vụ NSSM giữ codex app-server sống).

**Khuyến nghị tối ưu (không phải quyết định, ghi để nhớ):** dùng **tài khoản ChatGPT
RIÊNG**, TÁCH khỏi tài khoản BOT GEMINI (13 user thật) để ban không lan; chuẩn bị
**pool nhiều tài khoản** đỡ trần quota dùng-chung.

## 11. KIẾN TRÚC CHỐT (PA-3 + sidecar)

```
Trình duyệt ──HTTP/SSE──► LTTStudioWeb (app chataistudio: UI + project/thread +
                            credit + proxy)  ──HTTP/SSE localhost──►
                          LTTStudioCodex (SIDECAR): bọc AsyncCodex(openai-codex SDK)
                            → spawn codex.exe, giữ app-server sống, pool tài khoản,
                              login device-code, start/resume thread, turn(stream),
                              history, image event. CODEX_HOME riêng của nền tảng.
```

- **Sidecar `LTTStudioCodex`** (dịch vụ NSSM mới, cổng loopback riêng): port
  `runtime.py`+`pool.py`+`auth_store.py`+`admin_auth.py` của BOT GEMINI thành **một
  service localhost** (FastAPI nhỏ) expose: `POST /login/device`, pool admin,
  `POST /thread`, `POST /thread/{id}/turn` (SSE), `GET /thread/{id}/history`,
  `GET /models`, image passthrough. CODEX_HOME = `C:\LTTPlatform\data\codex-home`
  (riêng, KHÔNG đụng BOT GEMINI). Ép **sandbox read-only** + bỏ tool code/mcp/network.
- **App `chataistudio`** (trong `apps/`): UI chat (SSE), project→thread trong
  **Postgres** (bảng mới, per-user), ảnh sinh ra copy sang **R2** + hiện inline,
  **credit** theo `token_usage` sidecar trả (giữ chỗ→quyết toán) + theo ảnh. Route web
  **proxy SSE** từ sidecar tới trình duyệt (cap token/timeout né CF 100s).
- **Admin**: trang nhập/đăng nhập tài khoản ChatGPT (device-code) + xem pool/quota —
  đặt trong khu admin nền tảng (không lộ cho khách).
- **Bỏ**: mode work/plan, files/diff, MCP, sandbox-write, project import zip.

## 12. LỘ TRÌNH PHÂN PHA (có điểm dừng kiểm tra)

- **Pha C0 — Hạ tầng sidecar**: cài `openai-codex`+`codex_cli_bin` vào LTT venv;
  dựng service `LTTStudioCodex` (skeleton FastAPI) + resolve codex.exe + CODEX_HOME
  riêng; smoke: khởi động app-server, `GET /models`. (Chưa cần login.)
- **Pha C1 — Auth pool**: port login device-code + auth_store pool; admin UI nhập
  tài khoản; smoke: đăng nhập 1 tài khoản, `activate`, gọi thử 1 turn ngắn.
- **Pha C2 — Chat lõi**: bảng Postgres project/thread; app `chataistudio` UI chat +
  route proxy SSE; gửi/nhận token streaming; history; per-user isolation. Credit chat.
- **Pha C3 — Ảnh trong chat**: bắt event imageGeneration → lưu R2 → hiện inline;
  credit ảnh. Multi-model chọn trong UI.
- **Pha C4 — Nghiệm thu THẬT** trình duyệt + public URL (stream, ảnh, per-user, credit)
  + docs + memory + test.

**Điều kiện tiên quyet vận hành (user):** đăng nhập 1 tài khoản ChatGPT riêng qua UI
admin (giống nhập R2/ModelArk trước) — build không cần, chỉ cần khi nghiệm thu live.

## 13. TRẠNG THÁI: XONG + NGHIỆM THU THẬT (2026-08-02)

Tất cả C0→C4 **XONG + verified live** (xem NHAT_KY 2026-08-02). Full E2E trên
app.lttstudios.com: chat streaming + **tạo ảnh trong phiên** (mèo phi hành gia inline)
+ persist per-user (Postgres) + credit (100→71) + đa model GPT-5.x.
- Sidecar `LTTStudioCodex` (NSSM) + `codex_sidecar/` + `apps/chataistudio/`.
- Đăng nhập ChatGPT Plus THẬT (device-code) — tài khoản `aka...@gmail.com`.
- Credit giá phẳng: 3/lượt + 20/ảnh (admin chỉnh trong `apps/chataistudio/cost.py`).
- **Còn (chưa gấp)**: pool nhiều tài khoản ChatGPT (đỡ trần quota tuần dùng-chung);
  custom instructions per-hội-thoại đã có cột DB nhưng UI nhập chưa gắn (fast-follow);
  đổi danh xưng trợ lý (đang tự xưng "Codex") qua developer_instructions nếu muốn.

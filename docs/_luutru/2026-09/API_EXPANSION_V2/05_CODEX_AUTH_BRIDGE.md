> LƯU TRỮ 2026-09-19 — không còn đúng hệ thống hiện tại; thay bằng: docs/PUBLIC_API/. Chỉ đọc để hiểu lịch sử.

# Phase 04 — Codex Auth bridge: **kiểm định, chưa thi hành**

**Trạng thái: `BLOCKED_POLICY`.** Kiến trúc đã khảo sát và có đường đi rõ; **mã
chưa viết một dòng**, và đó là quyết định có chủ ý — xem §6.

---

## 1. Architecture hiện tại — đo được

```
Admin  --device-code/api-key-->  codex_sidecar (127.0.0.1, bearer)
                                      |
apps/chataistudio/routes.py  --------->|  thread/turn SSE, trong tien trinh web
   (595 dong, job_types=(), khong qua hang doi)
```

`codex_sidecar/server.py` — 302 dòng, **13 endpoint**, mọi cái sau `_auth`
(bearer `LTT_CODEX_SIDECAR_TOKEN`) trừ `/health`:

| Nhóm | Endpoint | Dùng được cho bridge |
|---|---|---|
| Auth | `/login/api-key` · `/login/device/start` · `/login/device/wait` · `/logout` | ✅ đã có cả hai đường |
| Trạng thái | `/account` · `/rate-limits` · `/capabilities` · `/models` · `/health` | ✅ đủ dựng máy trạng thái sức khoẻ **và** admission |
| Hội thoại | `/thread` · `/thread/{tid}/turn` (SSE) · `/thread/{tid}/history` | ✅ |

---

## 2. Bốn thứ đã sẵn sàng hơn hồ sơ nói

### 2.1 Hợp đồng chạy streaming — **đã có** (hồ sơ nói chưa)

`APP_API_COVERAGE_FINAL.md` ghi *"cần một hợp đồng chạy mới"*. Viết **trước
H38**. Nay `STREAM` nằm trong `MODES_IN_USE`, và `server/api/streaming.py:486`
gác luồng bằng **chính ba cổng của tool**:

```python
tool = require_tool(build_catalog(config), TOOL_CHAT, principal)
```

⇒ Khai một ToolSpec `STREAM` là đủ. **Không cần hợp đồng mới, không cần route
mới.**

### 2.2 Cô lập hội thoại — **đã có mầm**

`start_thread(user_id, conv)` — thread khoá theo `(user_id, conv)`. Việc còn lại
là ánh xạ `user_id` sang **principal của Public API** (khoá API thuộc project
nào) thay vì user web. Đó là một phép ánh xạ, không phải một cơ chế mới.

### 2.3 Giá — **đã đúng khuôn gói đòi**

Prompt 04 §5 cấm *"giả token count để thu tiền"*. `apps/chataistudio/cost.py`
đã nói thẳng vì sao nó không làm thế:

> *Đăng nhập ChatGPT Plus ⇒ **KHÔNG có chi phí USD theo token** (chỉ giới hạn
> quota tuần). Vì vậy credit ở đây là **GIÁ BÁN do mình đặt**.*

```
giu cho  = 3 credit / luot
quyet toan = 3 + so_anh x 20,  cap 4 anh/luot
```

Trung thực, có căn cứ, và đã chạy. **Không phải xây lại.**

### 2.4 Admission — có dữ liệu thật để dùng

`/rate-limits` của sidecar trả trạng thái quota của tài khoản. Prompt 04 §3 muốn
*"fail trước money/provider call khi biết không còn capacity"* — dữ liệu đã có,
chỉ cần nối vào admission plane hiện tại.

---

## 3. Đường đi kỹ thuật, nếu được phép làm

| # | Việc | Ước lượng |
|---|---|---|
| C1 | ToolSpec `STREAM`, qua `require_tool` như `text.chat` | nhỏ |
| C2 | Máy trạng thái Auth: `NOT_AUTHENTICATED` / `READY` / `RATE_LIMITED` / `REAUTH_REQUIRED` / `DOWN` | nhỏ — `/account` + `/rate-limits` đã trả đủ |
| C3 | Ánh xạ thread theo **principal Public API**, kèm luật dọn/lưu giữ | vừa |
| C4 | Admission từ `/rate-limits`, fail **trước** tiền | vừa |
| C5 | Chống rò: token ChatGPT, `CODEX_HOME`, bearer sidecar, đường dẫn tệp | nhỏ, nhưng **bắt buộc có test** |
| C6 | Giá: dùng nguyên `cost.py` | ~0 |
| C7 | Ảnh: promote sang artifact, hoặc `CODEX_IMAGE_DEFERRED` | vừa |

⭐ Tổng thể **rẻ hơn hồ sơ gợi ý**, vì bốn thứ ở §2 đã có sẵn.

---

## 4. Isolation — chỗ nguy hiểm nhất nếu làm ẩu

Public API có nhiều khách và nhiều project. Nếu `user_id` truyền xuống sidecar
không phân biệt được **khách A với khách B**, thread của họ sẽ lẫn nhau — và
điều đó không hỏng ồn ào, nó hỏng bằng cách khách A đọc được hội thoại khách B.

⇒ Nếu làm, đây là phép kiểm phải viết **trước**, không phải sau.

---

## 5. Streaming event mapping

Sidecar phát SSE; `_serialize_event` (server.py:74) đã chuẩn hoá. Cần ánh xạ
sang giao thức công khai đã chọn ở Phase 02: text delta · final · usage *(nếu
runtime cho — **không bịa**)* · tool/function · image · error · disconnect.

`server/api/streaming.py` đã làm đúng việc này cho `ltt_llm`, nên có khuôn để
theo.

---

## 6. 🔴 Vì sao dừng ở đây

`TECHNICALLY_READY` ≠ `COMMERCIAL_RELEASE_ALLOWED`.

Mô hình đích: bán quyền gọi runtime của **một tài khoản ChatGPT cá nhân** cho
khách bên ngoài, thu tiền bằng credit LTT. Điều khoản của OpenAI hạn chế việc
chia sẻ/bán lại quyền truy cập tài khoản và việc lách giới hạn sử dụng —
`EXTERNAL_POLICY_NOTE.md` của chính gói đã nêu và bảo kiểm lại tại thời điểm
phát hành.

**Theo nguyên văn gói:**

* ❌ không tự đổi kiến trúc Auth vì lý do chính sách (`USER_DECISIONS.md` §2);
* ❌ không làm xoay tài khoản / lách quota (`USER_DECISIONS.md` §8);
* ✅ ghi trạng thái tách rời, không tự nhận PASS.

⇒ **Đây là lý do tôi kiểm định mà không viết mã.** Bảy việc ở §3 đều làm được,
nhưng chúng chỉ có giá trị nếu câu trả lời cho câu hỏi dưới đây là "có". Viết
trước rồi mới hỏi là đầu tư vào thứ có thể phải bỏ.

### Câu cần chủ sản phẩm trả lời

> **Ta có được phép bán quyền gọi một tài khoản ChatGPT cá nhân cho khách bên
> ngoài không?**

| Trả lời | Hệ quả |
|---|---|
| **Có** *(đã kiểm điều khoản cho đúng loại tài khoản)* | thi hành §3, mở sau kill switch + allowlist operator |
| **Không** | §3 vẫn làm được cho **nội bộ** — nhưng đó là một sản phẩm khác, và nên biết trước khi đầu tư |
| **Chưa rõ** | giữ `BLOCKED_POLICY`; ưu tiên Phase 06 |

*(Ý kiến kỹ thuật, không phải tư vấn pháp lý.)*

---

## 7. Deviations

**`BLOCKED_POLICY`** — kiểm định xong, thi hành hoãn chờ quyết định.

**`DEVIATION_WITH_EVIDENCE`** — hồ sơ nói cần *"một hợp đồng chạy mới"*; đo thật
thì hợp đồng `STREAM` đã tồn tại và đã sống từ H38.

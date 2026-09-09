# MIGRATION MAP — pha 03

> **Pha 03 — MAP ONLY. Không sửa một dòng mã thực thi nào.**
> Nguồn: `LEGACY_SURFACE_MATRIX.csv` · `OUTBOUND_EGRESS_MATRIX.csv` ·
> `PRODUCT_DEPENDENCY_MAP.md` · đo log worker production 28 ngày.

## 1. Quy tắc ánh xạ

```
TEXT / VLM   ->  LTT_LLM
IMAGE        ->  LTT_IMAGE
khong map duoc ->  GO TINH NANG.  ⛔ Khong fallback external.
```

## 2. Bảng ánh xạ

| Sản phẩm | Động cơ hôm nay | → Động cơ sau | UX giữ? | Lối ra phải chết |
|---|---|---|---|---|
| **taoanh** | Gemini Image | `LTT_IMAGE` | ✅ giữ | `apps/taoanh/jobs.py:20` |
| **thumbnail** | Gemini Image | `LTT_IMAGE` | ✅ giữ | `apps/thumbnail/jobs.py:25` |
| **anhnoibo** | máy B + `dich_gemini` | `LTT_IMAGE` thuần | ✅ giữ | `apps/anhnoibo/jobs.py:110` |
| **autosubvideo** | Gemini Text | `LTT_LLM` | ✅ giữ | `ai_workflows.py:140` |
| **taovideo** | Gemini Text | `LTT_LLM` | ✅ giữ | `translate.py:11` |
| **prompt_ai_ommi** | Gemini Text | `LTT_LLM` | ✅ giữ | `provider.py:10` |
| **chataistudio** | Codex sidecar (ChatGPT OAuth) | 🔴 **GỠ HẲN** (xem §7) | — | cả app + `codex_sidecar/` |
| **agent planner** | `("ltt_llm","gemini")` | **`("ltt_llm",)`** | — | `planner.py:20` |
| `tools/doi_chung_gemini.py` | Gemini | **GỠ HẲN** | — | `:163` |

⚠️ `doi_chung_gemini.py` là công cụ **đối chứng mù** với Gemini. Cuộc so mù đã
kết thúc (14-4, phần có nghĩa) và kết luận **bỏ đối chứng Gemini** — nên đây
không phải mất mát năng lực, mà là dọn một việc đã xong.

## 3. 🔑 Phép đo trả lời câu treo từ pha 02

**Câu hỏi:** gỡ fallback Gemini của `planner` có biến thất bại thành **mặc định**
không? (Máy B chỉ có **một** suất đồng thời — `DONG_THOI_MAY_B=1`.)

**Đo:** `C:\LTTPlatform\logs\ltt-job-worker*.jsonl`, **41.622 dòng**, cửa sổ
**2026-08-11 → 2026-09-08** (28 ngày).

| Đại lượng | Giá trị |
|---|---|
| `ltt_llm.chat` | **3.435** job |
| `anhnoibo.generate` | 3.369 |
| `taoclipngan.render` · `ltt_voice.*` · `vps.*` | 81 · 108 · 38 |
| **`taoanh.generate`** | **2** |
| `thumbnail` · `autosubvideo` · `taovideo` · `prompt_ai_ommi` | **0 · 0 · 0 · 0** |
| *"provider đang bận, đi tiếp"* | 81 dòng — **38 job** riêng biệt |
| *"không provider nào phục vụ được"* | 82 dòng — **38 job** riêng biệt |
| dòng có nhắc `gemini` | **1** |

### 3.1 Trả lời: KHÔNG — thất bại đã là mặc định sẵn rồi

Thông điệp lỗi thật ghi nguyên văn:

```
KhongCoProviderNao: khong provider nao phuc vu duoc: ltt_llm: ban
```

Danh sách provider ở đó **chỉ có `ltt_llm`** — Gemini **không hề nằm trong**
cascade của những lượt hỏng ấy. Tức fallback Gemini **không** đang đỡ 1,1% kia
(38/3.435 job chat hỏng vì máy B bận). Gỡ nó **không tạo ra** một chế độ hỏng
mới; nó chỉ xoá một đường lui **đang không được dùng**.

⇒ `PLANNER_PROVIDERS` rút về `("ltt_llm",)` là **an toàn theo lưu lượng đo được**.

### 3.2 ⛔ Nhưng con số 0 kia KHÔNG phải bằng chứng Gemini vô dụng

Đối chứng nói ngược: **các app dùng Gemini gần như không chạy.** `taoanh` chạy
**2 lượt** trong 28 ngày; `thumbnail`, `autosubvideo`, `taovideo`,
`prompt_ai_ommi` **không chạy lượt nào**. Nên *"1 dòng nhắc gemini"* chủ yếu đo
**sự vắng mặt của người dùng**, không đo sự vắng mặt của đường gọi.

🔑 **Hai mệnh đề khác nhau, và chỉ mệnh đề đầu được chứng minh:**

```
DUOC CHUNG MINH : fallback Gemini khong dang do luu luong chat that
KHONG chung minh: chuyen taoanh/thumbnail sang LTT_IMAGE la khong rui ro
```

⇒ **Rủi ro di trú của 4 app ảnh/dịch là CHƯA ĐO, không phải ĐÃ ĐO BẰNG 0.**
Pha 05/06 phải tự dựng phép đo của chúng (so sánh đầu ra trên một bộ mẫu), không
được viện dẫn bảng này.

### 3.3 Một cái bẫy đếm đã tránh được

82 dòng log ≠ 82 sự cố. Chúng là **38 job**, trong đó một job (`210110e8`) chiếm
**12 dòng** vì được thử lại nhiều lần. Đọc theo dòng sẽ thổi phồng tần suất hỏng
lên **2,2 lần**.

## 4. Lỗi bí danh phải sửa TRƯỚC khi di trú

`platform_core/llm/dieu_phoi.py` docstring dạy sai:

```python
model_theo_provider={"ltt_llm": "ltt_llm"}      # ⛔ SAI
```

`ltt_llm` là **bí danh app**, không phải id model — khoá provider chỉ khai
`qwen38-api` / `qwen38-vision`. Nên `chon_key(model="ltt_llm")` **luôn** ném
`ThieuKeyError`, và `dieu_phoi.goi()` đọc đó thành *"provider không phục vụ
được, đi tiếp"* ⇒ **bỏ qua model nhà trong im lặng** rồi xuống Gemini, dù bên
gọi khai "model nhà đi trước". Docstring ấy **đã dạy sai hai nơi chép theo**.

⚠️ **Thứ tự bắt buộc:** sửa bí danh **trước**, rồi mới gỡ Gemini. Làm ngược lại
thì mọi lượt đang lặng lẽ đi Gemini sẽ chuyển thẳng thành **lỗi**, và ta sẽ đọc
nhầm đó là "LTT_LLM không đủ năng lực" trong khi thật ra là một chuỗi sai tên.

🔑 Đây là ca `AGENTS.md` §4c câu 2 (*đường suy biến*) ở dạng cụ thể nhất:
**một lỗi im lặng khi bị gỡ mất đường lui sẽ trở thành một lỗi ồn ào bị quy sai
nguyên nhân.**

## 5. Ranh giới KHÔNG được vượt khi di trú

⛔ **`llm_gateway` và `cong_vlm.chat()` không được thêm cascade.** Quyết định
**D-010**: đổi model sau lưng khách là **bán sai hàng** — khách trả tiền cho
Qwen3.8-27B mà nhận Gemini. Hai chỗ đó cố ý **không có** fallback và có test soi
chữ ký hàm để giữ vậy.

Cascade của `dieu_phoi` hợp lệ vì nó phục vụ **việc nội bộ** (lập kế hoạch, tóm
tắt, sinh phụ đề) — nơi không có lời hứa nào với khách về *model nào*, và bên
gọi **tự khai** thứ tự. ⇒ Di trú sản phẩm phải đi qua `dieu_phoi`, **không** nới
`llm_gateway`.

⛔ **`BanError` không phải lỗi provider.** Không được gọi
`api_pool.danh_dau_loi()` khi bận — lẫn một lần thì khoá `ltt_llm` bị cooldown,
5 lần thì `disable`, và **một tối máy B chạy video sẽ tự tắt model nhà vĩnh viễn**.

⛔ **Vượt ngân sách không được cascade.** Một yêu cầu quá to thì quá to với mọi
provider; thử lại nơi khác chỉ tốn tiền rồi vẫn hỏng.

## 6. Ba tính năng phải trả lời "map hay gỡ" ở pha 05/06

| Tính năng | Vấn đề | Đề xuất |
|---|---|---|
| `gemini-2.5-flash-preview-tts` | model TTS trong `REGISTRY`, **không nơi nào gọi** | **GỠ** — mục catalog chết, không phải tính năng |
| `taoanh` bậc `gemini-3-pro-image` | đã `is_active=False` từ 23/08 vì **lỗ tiền** | **GỠ** — đã đóng, nay xoá luôn |
| `chataistudio` lịch sử hội thoại | `codex_thread_id` trong DB | **HISTORY_ONLY** — giữ cột, đọc được, không resume được |

## 7. Trạng thái

Pha 03 **chỉ ánh xạ**, chưa sửa mã. Chưa chạy lệnh nặng nào. Bảng này là đầu vào
cho pha 04 (fail-closed) và 05/06 (di trú).


---

## 7. 🔴 ĐẢO QUYẾT ĐỊNH 09/09/2026 — `chataistudio` **GỠ HẲN**, không di trú

Pha 05.7 chạy theo phương án **(a) di trú sang LTT_LLM**. Chủ sản phẩm xem lại
ngày 09/09 và chỉ ra điều tôi đã bỏ sót khi trình bày hai phương án ấy:

> *"chataistudio vốn dĩ là 1 chat dùng để gọi codex pool phản hồi. Bản chất cơ
> chế vận hành là CLI và code từ codex. Theo tôi là xóa thẳng app này đi luôn
> mới đúng thay vì sửa chữa."*

⛔ **Thiếu sót của tôi:** khi hỏi *"di trú hay retire"*, tôi không nói ra rằng
   nền tảng **đã có** `chatltt` làm đúng việc ấy và làm đầy đủ hơn. Câu hỏi vì
   thế trông như *"giữ hay bỏ một tính năng"*, trong khi nó thật ra là *"có nên
   nuôi bản sao thứ hai của một app đang chạy không"*.

### Bằng chứng — đo 09/09/2026

| Đo | `chataistudio` | `chatltt` |
|---|---|---|
| Số tệp `.py` | **7** | **47** |
| `group` trong catalog | `Chat` | `Chat` |
| Năng lực | văn bản (sau khi mất Codex) | văn bản + **ảnh** + **giọng nói** |
| `job_types` / bảng giá riêng | không / không | có / có |
| Dòng trong `ltt-server.jsonl` (1.107 dòng) | **0** | **213** |
| `chat_conversations` (CSDL production) | **3** | — |
| `chat_messages` | **8** (3 người dùng) | — |
| Tin nhắn mới nhất | **25/08/2026** — 15 ngày im lặng | — |

⭐ Con số **0** ở dòng log có đối chứng: cùng tệp ấy ghi **213** dòng của
   `chatltt`, nên nó đo *"không ai dùng"* chứ không đo *"tệp này không ghi app"*.

⭐ Và **8 tin nhắn / 3 người / im từ 25/08** là dấu vết **thử nghiệm**, không
   phải sử dụng.

### Lập luận quyết định — không phải "mất động cơ", mà là **trùng lặp**

Sau khi Gemini và Codex bị xoá, `chataistudio` còn lại đúng một thứ: *một khung
chat văn bản trên LTT_LLM*. Đó chính là `chatltt`, đã `public=True` từ 03/09 sau
khi H43 Phase 13 PASS. Nuôi hai app cùng nhóm, cùng model, cùng cửa runtime là
nuôi hai bản sẽ trôi khỏi nhau.

⚠️ `summary` của nó còn hứa hai thứ **đều đã chết**: *"Trò chuyện với AI (GPT-5)
   và **tạo ảnh** trực tiếp"*. GPT-5 chết vì xoá Codex; ảnh chết vì LTT_LLM là
   model văn bản.

🔑 Và một bằng chứng nữa, tình cờ: lượt gate 09/09 cho thấy đường chat của app
   này **chưa từng chạy được** sau 05.7 — mọi lượt gửi `500` vì `UNIQUE
   constraint failed: chat_messages.id`. Nếu có ai dùng thật, lỗi ấy đã được
   báo trong 15 ngày.

### Việc phải làm, và thứ tự

| Pha | Việc |
|---|---|
| **07** | Xoá `apps/chataistudio/` (toàn bộ) · `codex_sidecar/` · `codex_sidecar_main.py` |
| **09** | Chứng minh bảng `chat_conversations`/`chat_messages` là `HISTORY_ONLY` |
| **13** | ⚠️ **Gỡ dịch vụ Windows `LTTStudioCodex`** — nó **đang chạy** trên máy chủ, và xoá mã KHÔNG gỡ một dịch vụ |

### ⛔ Dữ liệu: GIỮ, không xoá

8 bản ghi của 3 người dùng. Ít, nhưng *"xoá dữ liệu không đảo được"* là một
trong bốn ranh giới `CLAUDE.md` giữ lại kể cả khi chưa có khách. Hai bảng ở lại
dưới nhãn **`HISTORY_ONLY`**: không route, không ghi mới, không tra khoá, không
lối ra mạng. Rẻ hơn một migration `DROP`, và đảo lại được.

### Cái gì của 05.7 còn sống

`platform_core/loi_ra_ngoai.py` (nay `chatltt` dùng) · `tests/gia_dieu_phoi_anh.py`
· và hai lỗi sản phẩm mà lượt gate tìm ra. `luong_chat.py` đi theo app — công bỏ
ra mất phần lớn, và **đó không phải lý do để giữ một app trùng lặp**.

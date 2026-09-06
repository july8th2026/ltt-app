# PLAN TỔNG — ba làn, lắp ghép có căn cứ

> Viết 06/09/2026 theo yêu cầu chủ dự án: *"nghiên cứu tài liệu từ cộng đồng để
> xây và hoàn thiện plan, tăng tốc độ triển khai"*.
>
> Tệp này **thay** phần lộ trình của `00_KE_HOACH_V3.md` từ làn B trở đi. Kế
> hoạch cũ không sai — nó được viết trước khi có phép đo, và nó tự nói điều đó.
>
> Mọi con số đo ngày 06/09 bằng GitHub API / PyPI / npm registry / CSDL
> production. Không con số nào lấy từ trí nhớ.

---

## §0 — Luật quyết định: NƠI CHẠY, không phải số sao

Đây là thứ tôi thiếu suốt hai pha, và nó giải thích vì sao "lắp cho nhanh" lúc
đúng lúc sai.

| Thứ mượn chạy ở đâu | Ngưỡng chấp nhận | Vì sao |
|---|---|---|
| **Runtime production** | **rất cao** | mỗi phụ thuộc là bề mặt tấn công, một chu kỳ cập nhật phải theo, và một giấy phép phải tuân |
| **Test-time / CLI** | **thấp** | chạy rồi thoát, không ship, không chạm khách, không nằm trong ảnh deploy |
| **Đặc tả / tài liệu** | **gần như không có** | chỉ nhận phần đã được nhiều người thử sai hộ |

⭐ Ba mức này giải thích mọi quyết định dưới đây, và chúng khớp với thứ đã hiệu
   quả một lần ở kho này: H43 lấy `convoStructure.spec.ts` của LibreChat làm
   **đặc tả** cho `test_619` — mượn ở mức ba, không mức một.

⛔ **Và một câu phải hỏi TRƯỚC cả ba mức:** *thứ đã xây xong đã tới khách chưa?*

```
grep -c LTT_CHATLTT_V3  C:/LTTPlatform/secrets/app.env  ->  0
chatltt_conversation 220 hang    ·    agent_runs 4 hang
```

Làn A xong 100 % mã, P06 xong 6/6 bước, **không một dòng nào chạm một người dùng
nào**. Còn `LTT Agent AI` — một sản phẩm **đã phát hành** — có **4** lượt chạy
trong khi ChatLTT có **220** hội thoại. Đó là dữ kiện mạnh nhất trong cả tệp
này, và nó nói: **tốc độ không đến từ xây nhanh hơn, mà từ đưa ra dùng sớm hơn.**

---

## §1 — Bảng tra cộng đồng, đo ngày 06/09

```
                          sao      giay phep     phu thuoc bat buoc   noi chay
mem0ai 2.0.20           64.765     Apache-2.0     8 (qdrant, openai, posthog)  runtime
letta 0.16.8            24.627     Apache-2.0    69 (clickhouse, datadog)      runtime
zep-python 2.0.2         4.890     Apache-2.0     3 (chi la CLIENT)            runtime
gpt-researcher 0.16.0   29.308     Apache-2.0   140                            runtime
markitdown 0.1.7       178.407     MIT            6 (nhe)                      runtime
langchain-text-splitters   —       MIT            1 (keo ca langchain-core)    runtime
LibreChat               42.850     MIT             —                           dac ta
Open WebUI             151.085     NOASSERTION     —                           dac ta
assistant-ui            12.026     MIT             —                           dac ta (React)
promptfoo 0.122.2       24.852     MIT           80                            TEST-TIME
garak 0.16.0             9.121     Apache-2.0    45                            TEST-TIME
```

⛔ **Loại thẳng, có lý do đo được:**

* `Azure/PyRIT` — 116 sao, cập nhật gần nhất **03/2026**. Không phải kho chính.
* `protectai/rebuff` — cập nhật gần nhất **08/2024**. Chết.
* `vercel/ai` — giấy phép `NOASSERTION`, phải đọc kỹ trước khi chạm mã.

🔴 **Sửa 06/09 (B4 §0.1): dòng `letta` trong bảng trên là một phép đo TRỘN.**
Số phụ thuộc (69) đo từ gói PyPI `letta 0.16.8`; số sao (24.627) đo từ kho
GitHub `letta-ai/letta`. Đo lại cây tệp thì kho ấy có đúng **15 mục, toàn tệp
meta** — README nói nó *"nay chỉ là trang giới thiệu"*, mã V1 đã lui về nhánh
`archive`, và mã sống chuyển sang `letta-ai/letta-code` (**3.217** sao,
**TypeScript**).

⇒ Kết luận "loại letta" không đổi, nhưng **căn cứ đổi hẳn**: không phải *"nặng
69 phụ thuộc"* mà là *"gói Python ấy đã ngừng, bản kế nhiệm không phải Python"*.
⭐ Luật rút ra, áp cho mọi §0 sau: **đếm mục trong cây gốc trước khi trích số
sao** — một kho rỗng vẫn trả về số sao rất đẹp.

---

## §2 — Ba chặn cứng của nền tảng này

Mọi quyết định "lắp hay không" đều va vào ít nhất một trong ba:

1. **`pgvector` KHÔNG có** trên PostgreSQL 17.10 này (đo ở P06: 0 phần mở rộng
   tên chứa `vector`). ⇒ mem0 / letta / zep đều cần kho vector ⇒ lắp chúng là
   dựng **Qdrant hoặc ClickHouse** trên máy Windows **đang chạy production**.
2. **`posthog` là phụ thuộc BẮT BUỘC của mem0** — gọi về bên thứ ba theo mặc
   định. Một nền tảng bán cho khách không được im lặng gửi dữ liệu sử dụng đi.
3. **Một máy, 10 lõi vật lý, dùng chung bốn phiên.** Thêm một dịch vụ thường trú
   là thêm một thứ tranh lõi với chính bộ test.

---

## §3 — Làn B còn lại: lắp ở đâu, tự viết ở đâu

### B1 · Route đính tệp + giao diện tối thiểu — **1,5 ngày** 🔴 ĐẨY LÊN ĐẦU

Không có nó thì toàn bộ P06 (4.034 dòng, 101 phép kiểm) **vô hình**.

* **Đặc tả mượn:** LibreChat `Files` — luồng chọn tệp → upload → gắn hội thoại →
  hiện chip đính kèm. Mượn **thứ tự bước và trạng thái**, không mượn mã.
* Tự viết: route, vì nó phải đi qua `upload_sessions` + `kho_tep` đã có.

### B2 · `markitdown` cho docx/pptx/xlsx/outlook — **0,5 ngày** ✅ LẮP

Thay ~3 ngày tự viết bốn bộ đọc. 6 phụ thuộc nhẹ, MIT, kèm `magika` giải bài
*"`content_type` do trình duyệt khai là một lời khai, không phải sự thật"*.

🔴 **Nhưng giữ `pypdf` cho PDF.** Đọc mã `_pdf_converter.py`: nó duyệt **theo
trang** bên trong nhưng API công khai trả về **một khối markdown** — số trang
không ra tới ngoài, mà `(tep_id, doan_id, trang)` là toàn bộ lý do bước 5 tồn
tại. Các định dạng không có khái niệm trang rơi vào nhánh `trang = 0` đã có sẵn.

### B3 · Điều kiện bật cờ — **0,5 ngày**

Danh mục đã có ở `STATE.md` (5 điều kiện). Còn thiếu: kiểm URL công khai với cờ
bật, và chủ dự án chốt giá trích.

### B4 · Memory CRUD + ba tầng — **2,5 ngày** ⚠️ TỰ VIẾT, có lý do

* **Không lắp** mem0/letta/zep — xem §2. Và chúng giải bài **ghi nhớ ngữ nghĩa
  qua embedding**; bài của bước này là *"người dùng thấy và sửa được"* — một bài
  về **quyền và giao diện**.
* **Đặc tả mượn:** ⚠️ **sửa 06/09** — kế hoạch chi tiết ở
  `10_KE_HOACH_B4_GHI_NHO.md`. Câu cũ ở đây (*"phân loại kiểu ghi nhớ của mem0
  (fact / preference / episode)"*) **sai**: đọc `mem0/configs/prompts.py` thì
  bộ ba ấy không tồn tại — tôi đã nhớ một bộ ba quen tai rồi viết ra như một
  phép đo. Thứ đáng mượn là `DEFAULT_UPDATE_MEMORY_PROMPT`: **bốn** phép
  `Add / Update / Delete / No Change`, trong đó *"mâu thuẫn ⇒ XOÁ"* là cả giá
  trị — một kho chỉ biết thêm sẽ tích luỹ mâu thuẫn và tệ dần đi **im lặng**.
  Cộng với lược đồ + hành vi của Open WebUI. Đọc tài liệu, không cài.
* ⛔ Open WebUI giấy phép `NOASSERTION` (có điều khoản thương hiệu) ⇒ **không
  chạm mã**, chỉ đọc hành vi.

### B5 · Project dùng `app_projects` — **2 ngày**

Đã chấm ở `07_KE_HOACH_P07.md` D1: cấu hình ở `payload`, liên kết ở cột
`project_id` **nullable** trên bảng nội dung. Nullable vì 220 hội thoại đang
sống không thuộc project nào.

### B6 · Deep research — **3 ngày** ⚠️ TỰ VIẾT trên `job_runner`

⛔ **Không** lắp `gpt-researcher` (140 phụ thuộc bắt buộc). Và kế hoạch tổng đã
tự nói: *"`job_runner` + `leases` đã có — **dùng**, không dựng hàng đợi thứ hai"*.

* **Đặc tả mượn:** vòng của gpt-researcher (mục tiêu → kế hoạch → thu nguồn →
  trích → tổng hợp → kiểm trích dẫn) — đọc kiến trúc, không cài.

### — · `agents` · `skills` — **CHƯA CHẤM**

`apps/agent` đang công khai với đúng lời hứa P07 định hứa, và có **4** lượt
chạy. Điều kiện để làm không phải "tới lượt" mà là trả lời được **vì sao khách
sẽ dùng nó trong khi họ không dùng `apps/agent`**.

**Làn B còn lại ≈ 10 ngày** (kế hoạch cũ ~20).

---

## §4 — Làn C: đây mới là chỗ lắp ghép thắng đậm

### P09 · UX V3 — **4 ngày** (cũ: 1 tuần)

🔴 Việc cụ thể lớn nhất đã đo được: **khối `tool_call` hiện không được vẽ gì
cả.** `LOAI_KHOI` khai nó ở backend, `KhoiLa.test.tsx` chốt rằng khối lạ không
vỡ và không lộ raw — đúng A5, nhưng nghĩa là vòng lặp tool chạy mà **không ai
nhìn thấy**.

* **Đặc tả mượn:** `assistant-ui` (MIT, 12k sao) có bộ vẽ `tool_call` /
  streaming / approval đã qua nhiều lượt thử. Mượn **cấu trúc trạng thái và
  cách bày**, không mượn mã — frontend này đã có hệ riêng.

### P10 · Gia cố sản xuất — **3 ngày** (cũ: 1 tuần)

Kế hoạch tổng đã nêu ràng buộc quyết định: *"kết quả tool là **dữ liệu không tin
được** — injection từ web/tệp là kịch bản kiểm **bắt buộc**"*.

⭐ Và đây là chỗ **test-time tooling** trả công gấp: thay vì tự viết một bộ
   corpus tấn công, chạy hai bộ đã có.

### P11 · Red team — **1,5 ngày** (cũ: 3 ngày) ✅ LẮP MẠNH

| Công cụ | Vì sao lắp được dù nặng |
|---|---|
| **`promptfoo`** MIT, chạy `npx`, có chế độ `redteam` | **không cài vào dự án**, chạy rồi thoát |
| **`garak`** Apache-2.0, CLI Python | cài ở môi trường test, không vào ảnh deploy |

⇒ 80 và 45 phụ thuộc **không quan trọng ở đây**: chúng không ship, không chạm
  khách, không nằm trong bề mặt tấn công của dịch vụ. Đó chính là §0 mức hai.

⛔ Vẫn giữ luật cũ: P11 chạy ở **phiên MỚI, cây MỚI**. Một người tự kiểm mình thì
   kiểm những chỗ mình đã nghĩ tới.

### P12 · Phát hành — **1 ngày** · cần chủ dự án bấm UAC

**Làn C ≈ 9,5 ngày** (kế hoạch cũ 14).

---

## §5 — Tổng, và phần rút ngắn đến từ đâu

| Làn | Cũ | Mới | Chênh |
|---|---|---|---|
| A (P00–P05) | 17 | ✅ xong | — |
| B (P06–P08) | ~20 | **10** | −10 |
| C (P09–P12) | 14 | **9,5** | −4,5 |
| | **51** | **36,5** | **−14,5 ngày** |

⭐ **Không một ngày nào rút ra từ "làm nhanh hơn".** Bốn nguồn, đo được:

1. **−3 ngày** — `markitdown` thay bốn bộ đọc tự viết.
2. **−4 ngày** — bỏ `agents` (chưa có căn cứ) và không nhận nuôi
   `gpt-researcher`.
3. **−1,5 ngày** — `promptfoo` + `garak` thay corpus tấn công tự viết.
4. **−6 ngày** — mượn **đặc tả** (LibreChat · assistant-ui · mem0 · Open WebUI)
   thay vì tự thiết kế bốn lần.

⚠️ Con số 36,5 là **ngày công**, không phải ngày lịch, và nó giả định không có
   pha nào bị chặn bởi một quyết định thương mại. Hai quyết định đang chờ: **giá
   trích tài liệu** và **bật cờ V3**.

---

## §6 — Quy trình mới, áp từ pha kế tiếp

Mỗi tệp `0x_KE_HOACH_Pxx.md` phải mở bằng **§0 — Đối chiếu cộng đồng**:

1. **Ai đã làm rồi?** — tra GitHub API + PyPI/npm. Ghi sao · giấy phép · **số
   phụ thuộc bắt buộc** · lần cập nhật gần nhất.
2. **Nó chạy ở đâu?** — runtime / test-time / đặc tả. Ngưỡng theo §0.
3. **Nó có va vào ba chặn của nền tảng không?** (§2)
4. **Nếu tự viết: cái gì làm nó khác?** — phải là một **yêu cầu đo được**, không
   phải "để chủ động". Ví dụ đúng: `chia_doan` tự viết vì cần **chồng lấn** và
   cắt **trong từng trang**, hai thứ bộ chia của TTS không có.

⛔ Kế hoạch pha không có §0 là kế hoạch **chưa viết xong**. Luật này tồn tại vì
   tôi **đã có** nguyên tắc đối chiếu cộng đồng trong bộ nhớ và vẫn bỏ qua nó ở
   hai pha liền — một nguyên tắc không tự chạy, một **bước** thì có.

# Lộ trình sửa lại: LẮP GHÉP thay vì tự suy

> Viết 06/09/2026 sau khi chủ dự án chỉ ra rằng tôi đang tự thiết kế mọi thứ
> thay vì đối chiếu cộng đồng. Nhận xét ấy **đúng**, và nó là một luật **đã có
> trong bộ nhớ của tôi** — *"đối chiếu cộng đồng trước mỗi pha: tra GitHub +
> bản cập nhật mới nhất trước khi tự thiết kế"*. Chính kho này từng làm đúng:
> H43 dùng `convoStructure.spec.ts` của LibreChat làm **đặc tả** cho `test_619`.
> Tôi bỏ thói quen ấy ở P06 và P07.
>
> Mọi con số dưới đây đo ngày 06/09, không lấy từ trí nhớ.

---

## §1 — Đo trước: bốn thứ tôi tự xây mà cộng đồng đã có

| Tôi đã tự viết | Có sẵn | Giấy phép | Kết luận đo được |
|---|---|---|---|
| `chia_doan.py` (chia đoạn có chồng lấn) | `langchain-text-splitters` 1.1.2 | MIT | ⚠️ kéo theo `langchain-core` — **một** phụ thuộc, nhưng là một cây lớn |
| `trich_van_ban.py` (PDF + chữ thuần) | `markitdown` 0.1.7 | MIT | ✅ **nên lắp** — xem §2 |
| hệ ghi nhớ (P07 b1, đang viết) | `mem0` · `letta` · `zep` | Apache-2.0 | ⛔ **không lắp được** — xem §3 |
| deep research (P08) | `gpt-researcher` 0.16.0 | Apache-2.0 | ⛔ **140 phụ thuộc bắt buộc** |

---

## §2 — `markitdown`: lắp, nhưng chỉ ở đúng chỗ nó mạnh

```
markitdown 0.1.7  MIT  ·  6 phu thuoc bat buoc (nhe)
   beautifulsoup4 · charset-normalizer · defusedxml · magika · markdownify · requests
extras theo dinh dang: pdf · docx · pptx · xlsx · xls · outlook · audio · youtube
```

Nó cho ba thứ tôi sẽ mất nhiều ngày để tự làm:

1. **docx · pptx · xlsx · outlook** — định dạng khách chắc chắn gửi, mà
   `trich_van_ban.py` của tôi **không đọc được cái nào**.
2. **Trích bảng biểu** (`pdfplumber`) — bảng trong PDF hiện ra thành bảng
   markdown, thay vì một dòng chữ dính liền vô nghĩa.
3. **`magika`** (bộ nhận diện kiểu tệp của Google) — giải đúng bài
   *"`content_type` do trình duyệt khai là một lời khai, không phải một sự thật"*.

### 🔴 Nhưng có một ràng buộc quyết định, và nó bác việc thay toàn bộ

Đọc mã: `_pdf_converter.py` duyệt **theo trang** bên trong, nhưng API công khai
trả về **một khối markdown**. Số trang **không ra tới ngoài**.

⇒ Mà `(tep_id, doan_id, trang)` là toàn bộ lý do bước 5 của P06 tồn tại. Thay
  đường PDF bằng `markitdown` là **mất trích dẫn theo trang** — đổi một tính
  năng đã chốt lấy một tính năng chưa cần.

**Quyết định:**

| định dạng | đường |
|---|---|
| PDF | **giữ** `pypdf` theo trang — trích dẫn cần số trang |
| docx · pptx · xlsx · outlook · html | **`markitdown`**, `trang = 0` (không có khái niệm trang) |
| chữ thuần | giữ (không phụ thuộc) |

⭐ Đây không phải thoả hiệp. `trang = 0` đã là *"không biết"* trong hợp đồng từ
   P06 — nên các định dạng không có trang rơi vào đúng nhánh đã có sẵn.

---

## §3 — Vì sao KHÔNG lắp mem0 / Letta / Zep, và đây là phép đo chứ không phải sở thích

```
mem0ai 2.0.20   8 phu thuoc:  qdrant-client (kho VECTOR) · openai · posthog
letta  0.16.8   69 phu thuoc: clickhouse-connect · datadog · ddtrace · black[jupyter]
zep-python      3 phu thuoc — nhung no chi la CLIENT; may chu Zep la mot dich vu Go rieng
```

Ba chặn, mỗi cái đủ một mình:

1. **`pgvector` KHÔNG có trên Postgres này** (đo ở P06: 0 phần mở rộng tên chứa
   `vector`). Cả ba đều cần một kho vector ⇒ lắp chúng nghĩa là dựng **Qdrant
   hoặc ClickHouse** trên máy Windows đang chạy production.
2. **`posthog` là phụ thuộc BẮT BUỘC của mem0** — nó gọi về máy chủ của bên thứ
   ba theo mặc định. Một nền tảng bán cho khách không được im lặng gửi dữ liệu
   sử dụng đi.
3. **69 và 140 phụ thuộc** (letta, gpt-researcher) không phải "một thư viện".
   Đó là nhận nuôi một nền tảng khác, với chu kỳ cập nhật và bề mặt bảo mật của
   nó.

⛔ Và ba cái đó giải bài **ghi nhớ ngữ nghĩa qua embedding**. Bài của P07 bước
   1–2 là *"người dùng thấy và sửa được"* — một bài về **quyền và giao diện**,
   không phải về truy hồi. Lắp một cỗ máy vector vào để giải một bài CRUD là
   thêm một hệ phải bảo trì cho một nhu cầu chưa đo được.

---

## §4 — Thứ ĐÁNG mượn từ cộng đồng: ĐẶC TẢ, không phải RUNTIME

Đây là phần tôi bỏ sót, và nó rẻ hơn hẳn:

| Nguồn | Mượn cái gì |
|---|---|
| **LibreChat** (MIT, 42.850 sao, cập nhật 06/09) | đã dùng ở H43 cho cây hội thoại. Còn: **bộ test** cho fork/branch, và mô hình `Agents`/`Files` của họ |
| **Open WebUI** (151.085 sao) | phân loại **ba tầng memory** và giao diện quản lý ghi nhớ — mượn **cách chia**, không mượn mã (giấy phép `NOASSERTION` = có điều khoản thương hiệu riêng, phải đọc kỹ trước khi chạm mã) |
| **mem0** | **phân loại** kiểu ghi nhớ (fact / preference / episode) — đọc tài liệu, không cài |

⭐ Luật rút ra, và nó khớp với thứ đã hiệu quả một lần ở kho này:

> **Mượn RUNTIME thì phải nhận cả hạ tầng, giấy phép và telemetry của nó.
> Mượn ĐẶC TẢ thì chỉ nhận phần đã được nhiều người thử sai hộ.**

Với một nền tảng chạy trên **một máy Windows**, không có pgvector, đang phục vụ
khách thật — vế thứ hai gần như luôn là vế đúng.

---

## §5 — 🔴 Đòn bẩy lớn nhất KHÔNG phải một thư viện

Đo lại hôm nay, hai lần:

```
grep -c LTT_CHATLTT_V3  C:/LTTPlatform/secrets/app.env   ->  0
chatltt_conversation   220 hang     agent_runs   4 hang
```

**Làn A xong 100 % mã. P06 xong 6/6 bước. Không một dòng nào chạm một người
dùng nào.** Và `LTT Agent AI` — một sản phẩm đã phát hành — có **4** lượt chạy
trong khi ChatLTT có **220** hội thoại.

⇒ Thứ rút ngắn lộ trình nhiều nhất không phải lắp thêm thư viện, mà là **bật cờ
  và mở route cho thứ đã xây xong**. Mỗi tuần xây tiếp mà chưa bật là một tuần
  ta không biết mình đang xây đúng hay sai.

⛔ Đây là một khuyến nghị, không phải một hành động tự làm: bật cờ trên
   production là **deploy**, một trong ba ranh giới cần chủ dự án.

---

## §6 — Lộ trình sửa lại

| # | Việc | Ngày | Đổi so với kế hoạch cũ |
|---|---|---|---|
| **A** | Route đính tệp + giao diện tối thiểu cho P06 | 1,5 | **MỚI, đẩy lên đầu** — không có nó thì P06 vô hình |
| **B** | `markitdown` cho docx/pptx/xlsx (giữ `pypdf` cho PDF) | 0,5 | **thay 3 ngày tự viết** bằng nửa ngày lắp |
| **C** | Điều kiện bật cờ: kiểm URL công khai + chốt giá trích | 0,5 | đã có danh mục ở `STATE.md` |
| **D** | P07 b1–b3 memory (CRUD + ba tầng), mượn **phân loại** của Open WebUI/mem0 | 2,5 | giữ tự viết — §3 |
| **E** | P07 b4–b6 project (dùng `app_projects`) | 2 | giữ, đã chấm ở `07_KE_HOACH_P07.md` |
| **F** | P08 research: **workflow bền trên `job_runner` đã có** | 3 | **không** lắp `gpt-researcher` (140 phụ thuộc) |
| — | `agents`, `skills` | — | **chưa chấm** — xem `07_KE_HOACH_P07.md` D2 |

**Tổng ≈ 10 ngày công** cho phần còn lại của làn B, so với ~20 ngày ước ban đầu.
Phần rút ngắn đến từ ba chỗ, và **không chỗ nào là "làm nhanh hơn"**: bỏ
`agents` (chưa có căn cứ), lắp `markitdown` thay vì tự viết bốn bộ đọc, và
không nhận nuôi `gpt-researcher`.

---

## §7 — Cái tôi làm sai, ghi để không lặp

1. **Tôi có luật đối chiếu cộng đồng trong bộ nhớ và không chạy nó** ở cả P06
   lẫn P07. Luật không tự chạy; nó phải là một **bước trong kế hoạch pha**, và
   từ nay nó là §0 của mọi tệp `0x_KE_HOACH_Pxx.md`.
2. **Tôi tự viết bộ chia đoạn và bộ trích văn bản** mà không hỏi ai đã làm.
   Bộ chia đoạn thì vẫn đúng (yêu cầu chồng lấn + theo trang là riêng), nhưng
   **bộ trích thì sai** — `markitdown` phủ rộng hơn hẳn với 6 phụ thuộc nhẹ.
3. **Tôi để "xây tiếp" thắng "đưa ra dùng"** suốt cả ngày, trong khi phép đo
   `0` cờ bật và `220` hội thoại thật đã nằm sẵn trước mắt.

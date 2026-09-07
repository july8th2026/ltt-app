# B6 — Nghiên cứu sâu (deep research)

> Đo ngày 07/09/2026. §0 lấy từ GitHub API + mã tải về (`scratchpad/b6/`); §1 từ
> chính mã kho này.

---

## §0 — Đối chiếu cộng đồng

### §0.1 Đo kho

| Kho | Sao | Đẩy | Giấy phép | Mục cây gốc |
|---|---:|---|---|---:|
| `assafelovic/gpt-researcher` | 29.317 | 2026-08-27 | Apache-2.0 | 48 |

Có mã thật (999 mục trong cây đầy đủ). ⛔ **Không lắp** — kế hoạch tổng đã chấm:
140 phụ thuộc bắt buộc, và nó chạy ở **runtime sản xuất** tức ngưỡng cao nhất.
Mượn ở **mức ba: đặc tả**.

### §0.2 🔴 Thứ quý nhất trong cả §0: một LỖI THẬT họ ghi lại, cùng hình dạng với lỗ P09 của ta

`gpt_researcher/retrievers/base.py` (61 dòng, gần như toàn docstring) kể lại
issue #1846 và #1892 của chính họ:

> *Historically nothing recorded which kind a retriever was, so
> `_search_relevant_source_urls` inferred it from the length of any
> `raw_content`:*
> ```python
> if url and raw_content and len(raw_content) > 100:
> ```
> *That guess is wrong whenever a snippet happens to exceed the threshold: the
> result is treated as already-fetched, its URL is never scraped, and the report
> ends up with **no verifiable citation for it**.*

Bản vá của họ: `requires_scraping` — **một lời KHAI thay cho một phép đoán**.

⭐ **Đây chính xác là lỗ tôi vừa vá ở P09 bước 1**, ba ngày trước, trên một hệ
   khác: khối `tool_call` phân biệt *"đang chạy"* với *"đã xong"* bằng
   `tom_tat == ""` — một **độ dài** đứng thay cho một **trạng thái**. Hai đội
   khác nhau, hai sản phẩm khác nhau, cùng một sai lầm, và cùng một bản vá:
   **thay phép suy từ hình dạng dữ liệu bằng một trường khai tường minh.**

⚠️ Và cái giá của họ đắt hơn của ta: hệ quả không phải một nhãn sai mà là **một
   báo cáo không có trích dẫn kiểm được**. Trong một sản phẩm nghiên cứu, đó là
   hỏng đúng thứ duy nhất khách mua.

⇒ Luật cho B6, viết trước dòng mã đầu tiên: **mọi nguồn mang một trường khai
  loại của nó. Không hàm nào được suy loại từ độ dài, từ rỗng, hay từ sự vắng
  mặt của một trường khác.**

### §0.3 "Nguồn lấy từ đâu" là một GIAO DIỆN, không phải một lời gọi

`gpt_researcher/retrievers/` có **21** cài đặt: `arxiv · bing · bocha · brave ·
crw · custom · duckduckgo · exa · getxapi · google · groundroute · mcp ·
openalex · pubmed_central · searchapi · searx · semantic_scholar · serpapi ·
serper · tavily · xquik`.

⭐ Con số 21 là lời khuyên, không phải khoe: họ **không** nhúng một nhà cung cấp
   vào vòng lặp. Ta có **không** nhà cung cấp web và **một** kho tài liệu —
   nhưng hình dạng phải giống: một giao diện, một cài đặt hôm nay.

---

## §1 — 🔴 Chặn cứng: nền tảng này KHÔNG CÓ khả năng tìm web

Đo 07/09, không đọc tài liệu mà hỏi mã:

```
chinh_sach.danh_muc()  ->  text.chat · image.ltt · speech.ltt     (het)
provider ngoai duy nhat trong platform_core  ->  "gemini"
khong mot tep nao khai tavily/serper/brave/searx/duckduckgo/bing
```

`httpx`/`requests` có, nên **tải một URL** thì làm được. Nhưng *"nghiên cứu
sâu"* cần **tìm** trước khi tải, và tìm cần một nhà cung cấp: một khoá API, một
hoá đơn, một điều khoản.

⇒ **Mở một `web.tim` là một QUYẾT ĐỊNH THƯƠNG MẠI**, cùng hạng với giá trích
  tài liệu (`gia_trich.CHU_DU_AN_DA_CHOT`) và `V-018` của LTT VIDEO. Nó không
  phải một hạng mục kỹ thuật để tôi tự quyết.

### Vậy B6 làm gì hôm nay

Vòng lặp nghiên cứu **không phụ thuộc vào việc nguồn đến từ đâu** — đó chính là
điều §0.3 chỉ ra. Và ta đã có sẵn một kho nguồn thật:

```
P06: chatltt_doan  — tai lieu cua chinh khach, da trich, da chia doan,
                     da co chi so FTS tieng Viet, da co trich dan
                     (tep_id, doan_id, trang) dinh lien
```

⇒ **B6 = vòng lặp nghiên cứu trên tài liệu của chính khách**, với bước "thu
  nguồn" nằm sau một giao diện để một `web.tim` cắm vào sau này mà **không phải
  thiết kế lại**.

⛔ Và phải nói thẳng ra ở giao diện: sản phẩm này đọc **tài liệu của bạn**,
   không đọc Internet. Một tính năng tên là *"nghiên cứu sâu"* mà im lặng về
   phạm vi của nó là một lời hứa hỏng — khách sẽ hỏi một câu cần web, nhận một
   câu trả lời tự tin dựng từ ba tài liệu kế toán, và không có gì báo cho họ.

---

## §2 — Năm quyết định

### D1. Nguồn KHAI loại của nó, không ai suy (từ §0.2)

```
Nguon(loai="doan_tai_lieu", tep_id=…, doan_id=…, trang=…, chu=…)
```

⛔ Không hàm nào được viết `if len(chu) > N` để đoán đây là nội dung thật hay
   một đoạn xem trước. `test_838` chốt bằng AST.

### D2. Là một JOB, không phải một request

Vòng lặp gọi model nhiều lượt. Trần Cloudflare là **100 giây**, và `CLAUDE.md`
viết: *"việc dài hơn vài giây bắt buộc đi qua hàng đợi job"*. `job_runner` +
`leases` đã có — **dùng**, không dựng hàng đợi thứ hai.

### D3. Báo giá TRƯỚC, và giá theo LƯỢT MODEL THẬT

Nghiên cứu sâu tốn nhiều lượt model. Cùng khuôn `gia_trich`: ước trần **trước**
khi bấm, quyết toán theo số lượt **thật sự chạy**, hoàn phần giữ dư.

⚠️ Và cùng luật đã trả giá: ước phải **cao hơn** giá thật. Sai về phía giữ dư
   làm khách bị giam credit vài phút; sai về phía kia làm cả lượt hỏng **sau
   khi** họ đã đồng ý.

#### ⚠️ SỬA D3 — 07/09, sau khi đo (bước 3)

Nửa sau của D3 (*"quyết toán theo số lượt thật sự chạy, hoàn phần giữ dư"*)
**không thi hành**, và không phải vì khó. Đo được:

```
platform_core/runtime_noi_bo/luong.py
  moi loi goi model GIU credit theo tran token roi HOAN ve token that
  -> su kien `billing.updated {credit_giu, credit_thu, credit_hoan}`
```

Vòng nghiên cứu không tốn gì **ngoài** những lượt model ấy — nó đọc
`chatltt_doan` của chính người hỏi (một truy vấn CSDL) rồi ghép chữ. Nên một
tầng giữ-và-thu ở job là **thu hai lần cùng một lượt**, đúng cái
`apps/chatltt/manifest.py` cảnh báo từ H43: *"Khai `job_types` ở đây là mời một
sổ tiền thứ hai."*

⇒ Thay bằng:

| D3 viết | thi hành |
|---|---|
| ước trần trước khi bấm | ✅ `gia_nghien_cuu.uoc_tran()` — số **hiện ra**, và là ngưỡng số dư route đòi |
| job giữ credit | ❌ `credit_cost = 0`, có chủ đích và có bánh cóc |
| job quyết toán theo lượt | ❌ `runtime_noi_bo` đã làm, chính xác hơn (theo token, không theo lượt) |

⭐ Nửa đầu của D3 **giữ nguyên và quan trọng hơn trước**: vì job không giữ chỗ,
  một tài khoản 0 credit vẫn nộp được job rồi chết ở lượt model đầu. Cửa ấy
  chuyển thành **điều kiện trước khi nộp** ở route (bước 4) — một điều kiện,
  không phải một giá, nên nó không tính hai lần thứ gì.

---

### D4. Không có trích dẫn thì KHÔNG có câu

Mỗi khẳng định trong báo cáo phải trỏ về `(tep_id, doan_id, trang)`. `P06 bước
5` đã dựng `tim_doan.cho_tool` với trích dẫn **dính liền** chữ, cố ý để không ai
tách được chúng ra. B6 giữ nguyên bất biến ấy.

🔴 Đây là chỗ lỗi #1846 của họ đắt nhất, và ta phải kiểm bằng một phép đo dương:
   một báo cáo có `n` khẳng định phải có `n` trích dẫn phân giải được về một
   `chatltt_doan` **có thật của chính người hỏi**.

### D5. Vòng lặp có TRẦN, và trần nói ra khi chạm

Mượn vòng của gpt-researcher: **mục tiêu → kế hoạch → thu nguồn → trích → tổng
hợp → kiểm trích dẫn**. Nhưng mỗi vòng là tiền, nên trần vòng và trần nguồn phải
tường minh, và chạm trần phải **hiện ra trong báo cáo** — không cắt im lặng.

---

## §3 — Sáu bước

| # | Việc | Cửa |
|---|---|---|
| 1 | `services/nguon.py` — giao diện nguồn + cài đặt `doan_tai_lieu` | không |
| 2 | `services/nghien_cuu.py` — vòng lặp, trần, kiểm trích dẫn | không |
| 3 | `gia_nghien_cuu.py` + job `chatltt.nghien_cuu` | không |
| 4 | route + cờ `_RESEARCH` | cờ **mới** |
| 5 | giao diện: báo giá → chạy → báo cáo có trích dẫn | vẽ thật |
| 6 | nói rõ PHẠM VI ở giao diện (§1) | vẽ thật |

Dải test: **838–840**.

---

## §4 — Phép đo nghiệm thu (viết TRƯỚC)

1. **Không suy loại từ độ dài**: bánh cóc AST trên `services/nguon.py`.
2. **Mọi khẳng định có trích dẫn phân giải được** về một đoạn có thật **của
   chính người hỏi**. *(Đối chứng: một `doan_id` của người khác phải bị loại.)*
3. **Chạm trần thì nói ra** trong báo cáo, không cắt im lặng.
4. **Không có nguồn nào thì KHÔNG bịa**: kho rỗng ⇒ báo cáo nói *"không tìm thấy
   tài liệu nào"*, không phải một bài viết trôi chảy không trích dẫn.
5. **Là job**: bánh cóc chốt rằng route không gọi thẳng vòng lặp.
6. **Phạm vi nói ra**: chuỗi "tài liệu của bạn" có mặt ở giao diện, và bánh cóc
   giữ nó — §1 nói vì sao im lặng về phạm vi là một lời hứa hỏng.

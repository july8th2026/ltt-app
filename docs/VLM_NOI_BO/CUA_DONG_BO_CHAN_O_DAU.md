# V3 vấp một chốt của chính nền tảng — cần một quyết định, không phải thêm mã

**Ngày:** 2026-08-23 · **Bối cảnh:** Đợt C của `RA_SOAT_VA_KE_HOACH.md` (V3 + V4)

---

## 1. Việc định làm, và chỗ nó dừng

V3 là *"route `POST /api/v1/chat/completions` + inventory + OpenAPI"* — cửa đồng bộ
để khách trỏ thẳng SDK OpenAI vào.

Mọi route công khai phải khai một **chế độ thi hành** (`execution_mode`, EXT-02).
Hôm nay chỉ có **hai** chế độ được phép dùng:

```python
MODES_IN_USE = (ASYNC_JOB, SYNC)          # platform_core/public_api/protocol.py:58
```

Và `SYNC` được định nghĩa hẹp có chủ ý:

> *"Answered in the request. Must be **free**, must **not** enqueue a job, must
> **not call a provider or the GPU**, must finish within **5s** and return at most
> 1024KiB."*

`check_mode_rules` không chỉ ghi lời hứa đó ra giấy, nó **chặn**:

```python
if mode == SYNC and contract.chargeable:
    raise ProtocolError("SYNC operations must be free — anything worth "
                        "charging for is worth quoting and queueing")
```

Một lượt chat vi phạm **cả ba** vế: nó thu tiền, nó gọi GPU, và nó chạy 20–60 giây
chứ không phải 5. Nên `POST /api/v1/chat/completions` **không có chế độ hợp lệ để
khai** ở trạng thái hiện tại. Đây không phải chuyện thiếu mã — đây là chỗ hợp đồng
nền tảng chưa có câu trả lời, và `CLAUDE.md` bảo dừng lại đúng lúc này:

> *"Nếu thấy buộc phải sửa nền tảng thì **dừng lại và nói rõ vì sao** — đó là dấu
> hiệu hợp đồng app còn thiếu, phải bổ sung vào hợp đồng chứ không đi vòng."*

⚠️ **Đi vòng được, và đó chính là cái bẫy.** Khai bừa `SYNC` rồi đặt
`chargeable=False` sẽ **qua được** `check_mode_rules` — và nền tảng sẽ không giữ
chỗ, không quyết toán, không có `Idempotency-Key`. Nghĩa là một lượt gọi tốn GPU
mà **không ai bị tính tiền**, hoặc bị tính hai lần khi khách thử lại. Chốt này
đang làm đúng việc của nó; đừng lách.

---

## 2. Vì sao lý do gốc của `STREAM` không còn đúng

`STREAM` **đã được đặc tả đầy đủ** trong `protocol.py`, chỉ là chưa ai dùng. Lý do
nó bị khoá được ghi rõ:

> *"Reserved and fully specified, but no operation uses it (**D5**): the only
> streaming capability the platform has runs through a **consumer-account
> sidecar**, and **reselling that** is a different class of risk from a customer
> using it themselves."*

Câu đó nói về `chataistudio` + sidecar `LTTStudioCodex` — đăng nhập bằng tài khoản
ChatGPT Plus của người thật. Bán lại thứ đó cho khách là rủi ro ToS.

**`ltt_llm` không phải thứ đó.** Nó là model của nhà, chạy trên phần cứng của nhà,
không có tài khoản của ai ở giữa. Sự thật nền của D5 **không áp cho nó**. Đó đúng
là tình huống mà giao thức đổi quyết định (`AGENTS.md` §6) tồn tại để xử lý: dòng
cũ không bị xoá, nó được đánh dấu và ghi rõ *vì sao đổi*.

---

## 3. Ba đường đi

### A. Chỉ mở `STREAM`, và **bắt buộc** `stream: true`

Mở `MODES_IN_USE`, khai route là `STREAM`, từ chối lượt không streaming.

- ✅ Không phải sửa một dòng nào trong lời hứa của các chế độ hiện có.
- ✅ `STREAM` đã đòi sẵn đúng sáu thứ mà việc bán token cần: kiểu sự kiện được
  khai, nhịp tim, **một sự kiện `usage` cuối mang số credit THẬT SỰ bị thu**,
  huỷ-khi-ngắt, và tiếp-nối-không-thu-hai-lần.
- ❌ SDK OpenAI mặc định **không** streaming. `client.chat.completions.create(...)`
  không có `stream=True` sẽ hỏng. Với một API bán ra ngoài, đó là một cái hố lớn
  ngay bậc cửa.

### B. Thêm một chế độ mới `SYNC_BILLED` *(khuyến nghị)*

Một chế độ thứ ba, khai rõ lời hứa của nó:

> Trả lời trong request. **Có thu tiền**, nên bắt buộc `Idempotency-Key`; giữ chỗ
> trước khi chạm nhà cung cấp và quyết toán theo **số đo thật**; phải xong trong
> **90 giây** (dưới trần 100s của Cloudflare); không đẩy vào hàng đợi.

- ✅ Đúng hình dạng thứ khách cần: SDK OpenAI chạy được ngay, không sửa gì.
- ✅ Chỗ giữ tiền đã có sẵn và đã có test: `platform_core/llm/thanh_toan.py`
  (`giu_cho_luot` → `quyet_toan_luot` → `hoan_luot`, luật C1).
- ✅ Nói thật ra điều đang xảy ra, thay vì gán nhãn sai lên một chế độ có sẵn.
- ❌ Là một **sửa đổi hợp đồng nền tảng** ⇒ cần một số quyết định (Q106), cần
  `check_mode_rules` mọc thêm nhánh, và cần `test_194` mở rộng.
- ⚠️ Trần 90 giây là **thật và không nới được**: Cloudflare cắt ở 100 giây bất kể
  máy B còn đang sinh chữ hay không. `max_tokens` phải bị kẹp theo tốc độ đã đo
  (63 tok/s ⇒ **khoảng 4.000 token** là trần an toàn cho một lượt đồng bộ). Lượt
  dài hơn **phải** đi cửa job.

### C. Không mở cửa đồng bộ; chỉ bán cửa job

Bỏ V3/V4, để khách nộp job rồi hỏi kết quả.

- ✅ Không tốn gì, chạy được ngay hôm nay (V1 đã nối xong phần tiền).
- ❌ Không tương thích SDK OpenAI. Khách phải viết vòng lặp hỏi trạng thái. Với
  một API bán ra ngoài để *"cắm vào xây bot"*, đây là điểm trừ nặng nhất.

---

## 4. Khuyến nghị

**B, rồi A ngay sau đó** — `SYNC_BILLED` cho lượt thường, `STREAM` cho lượt dài,
và cửa job vẫn còn nguyên cho lượt rất dài. Ba cửa, ba dải thời gian, mỗi cửa nói
thật về thứ nó làm.

Lý do chọn B trước A: cái chặn khách thật sự không phải "chưa có streaming", mà là
**dòng lệnh đầu tiên trong tài liệu OpenAI không chạy được**.

Việc phải làm nếu chọn B:

| | Việc | Ước |
|---|---|---:|
| 1 | Q106 vào `QUYET_DINH_NEN_TANG.md`, đánh dấu phần D5 bị thay | 0,25 ngày |
| 2 | `SYNC_BILLED` trong `protocol.py` + nhánh `check_mode_rules` + `test_194` | 0,5 ngày |
| 3 | Route + inventory + OpenAPI + kẹp `max_tokens` theo trần 90 giây | 1,0 ngày |
| 4 | Nối `thanh_toan` vào route (giữ chỗ → quyết toán → hoàn) | 0,5 ngày |
| 5 | `Idempotency-Key` cho cửa đồng bộ | 0,5 ngày |

**Tổng ≈ 2,75 ngày**, so với ước ban đầu 1,5 ngày cho V3 — chênh lệch chính là
phần hợp đồng, thứ mà ước ban đầu chưa nhìn thấy.

---

## 5. Trạng thái

⏸️ **Chờ chủ sản phẩm chọn A / B / C.** Không viết mã của V3 trước khi có câu
trả lời: cả ba đường đều chạm vào hợp đồng công khai, và làm sai đường thì không
phải sửa lại mã — mà là **rút lại một lời hứa đã công bố**.

# Prompt 01 — Machine A Core, Context & Model Contract

**31/08/2026.** Ownership: A01–A23.

**Kết quả một dòng:** hợp đồng ngữ cảnh **mạnh hơn tôi tưởng** — mọi con số dẫn
xuất từ một nguồn, và chính sách "không đoán usage" là thật. Nhưng W4 tìm ra
**bốn bản sao không ai canh**, hai trong đó **tới tay khách**.

---

## W1 — Hợp đồng model/app

```
alias cong khai -> id noi bo   {'ltt_llm': 'qwen38-api',
                                'ltt_llm_vision': 'qwen38-vision'}
model mac dinh                 ltt_llm
model hop le                   ('ltt_llm', 'ltt_llm_vision')
```

⭐ **Lớp alias làm đúng việc của nó.** Khách gọi `ltt_llm`; đằng sau là
`qwen38-api`. Ngày đổi model không thành một thay đổi phá vỡ tương thích. Và
`test_KHONG_ro_id_nha_cung_cap` (test_336) đã canh chiều ngược lại: id thật
không rò ra hợp đồng công khai.

⚠️ **Một điều đã tự chứng minh trong Prompt 04:** tôi gửi `model: "ltt_llm"`
thẳng vào máy B và nhận **404** kèm danh sách `["qwen38-api","qwen38-vision"]`.
Máy B **không biết alias** — ánh xạ nằm ở máy A (`features.py:39`). Đó là biên
giới đúng, và cái 404 ấy là **lớp alias đang làm việc**, không phải lỗi.

**KEEP** — không có duplicate rule, không có wrapper thừa.

---

## W2 — Mô hình ngữ cảnh: một phương trình, một nguồn

```
CUA_SO_MODEL        131.072   go tay   <- engine (-c cua llama-server)
TOKEN_RA_TRAN        32.768   go tay
LE                    2.048   go tay
--------------------------------------------------------------
TOKEN_VAO_TRAN       96.256   = CUA_SO - RA - LE          (dan xuat)
CONG_BO_CHO_CLIENT   88.555   = TOKEN_VAO_TRAN x 0,92     (dan xuat)
BODY_BYTES_TOI_THIEU 433.152  = TOKEN_VAO_TRAN x 4,5      (dan xuat)
TOKEN_RA_MAC_DINH    sync 1.024 | stream 32.768 | job 4.096
```

**Ba số gõ tay, phần còn lại dẫn xuất.** Kiểm bằng phép đo, không bằng đọc:
`96256` và `88555` xuất hiện **0 lần** dưới dạng số nguyên trong mã sống.

⭐ Sáu phân biệt mà `OPERATING_CONTRACT §10` đòi đều có mặt và **khác nhau**:
engine 131.072 · trần vào cứng 96.256 · công bố cho client 88.555 · trần ra
32.768 · mặc định theo cửa · trần body 433 KB.

⚠️ `mac_dinh_cho("stream") == TOKEN_RA_TRAN` — có `test_cua_stream_KHONG_co_tran_an_duoi_tran_cong_bo`
canh riêng, vì đã từng có sự cố: cửa stream mượn ngân sách 1.024 của cửa đồng
bộ và **mọi câu trả lời dài cụt ở đúng 1.024 token, im lặng**.

**KEEP.**

---

## W3 — Sự thật về `usage`: chính sách **không đoán** là THẬT

```
cong_vlm.doc_su_dung()   thieu/hong  -> SuDung(dang_tin=False)
gia_token.tinh()         dang_tin=False -> NEM KhongDoDuocError
thanh_toan.quyet_toan_hoac_hoan()      -> bat, va HOAN
```

⭐ Đây là chỗ dễ viết sai nhất trong một hệ thống tính tiền, và nó viết đúng:
**không có nhánh nào ước lượng token rồi thu tiền.** Thượng nguồn không nói thì
khách được hoàn.

🔴 **Nhưng cửa STREAM đi đường khác, và Prompt 04 vô tình chứng minh điều đó.**
Đo hiệu năng cho thấy `usage` **không có trong luồng SSE** (`token_ra_la_uoc:
true`). Cửa stream đếm token bằng `dem_token_luong.DemToken` ngay tại chỗ, rồi
`_phat` quyết toán theo con số **của chính ta**, không theo con số thượng nguồn.

⇒ Hai cửa, hai nguồn sự thật cho cùng một đại lượng tính tiền. Không kết luận ở
đây — **chuyển Prompt 02** với câu hỏi cụ thể: *`DemToken` đếm có khớp `usage`
của thượng nguồn không, và nếu lệch thì lệch về phía nào?*

---

## W4 — 🔴 Bốn bản sao không ai canh

Quét toàn kho (kể cả dạng `131_072` có gạch dưới — dạng này đã **lọt** lần quét
đầu của tôi):

| Nơi | Số | Được canh? |
|---|---|---|
| `apps/ltt_llm/ngan_sach.py` | 131.072 · 32.768 · 2.048 | **nguồn chân lý** |
| `llm_gateway/config.py` | 96.256 · 32.768 | ✅ `TestDoiChieuKhoMayB` |
| `manifest.py` · `features.py` · `executor.py` | bí danh | ✅ `TestKhongConChongCheo` |
| `platform_core/public_api/examples.py:557` | 32.768 | ❌ → **nay có** |
| `server/api/tools.py:33` | 32.768 | ❌ → **nay có** |
| `llm_gateway/catalog.py:60,72` | 131.072 · 65.536 | ❌ → **nay có** |
| `platform_core/providers.py:228,251` | 131.072 · 65.536 | ❌ → **nay có** |

**Hai trong đó tới tay khách:**

* `examples.py` sinh ra `CLAUDE_CODE_MAX_OUTPUT_TOKENS` trong **đoạn cấu hình ta
  đưa cho khách dán vào máy họ**. Lệch ở đây là phát cho khách một cấu hình sai,
  và họ gặp lỗi **ở máy họ** — kiểu lỗi đắt nhất để lần ra.
* `tools.py:TOKEN_RA_TOI_DA` là trần **thật trên đường sống** (giá trị lùi khi
  client không khai `max_tokens`).

### ⭐ Và gõ tay ở đây là THIẾT KẾ ĐÚNG — đừng "sửa" bằng `import`

`platform_core/` và `server/` **không được** phụ thuộc vào `apps/` — đó là hợp
đồng app của kho này (CLAUDE.md: *"Thêm app mới… **Không sửa** `platform_core/`
hay `server/`"*). Nên thứ ghép hai đầu lại **phải là một phép kiểm**, không phải
một câu `import`.

`TestBanSaoConLai` (4 phép kiểm) chính là cái ghép ấy. Trước 31/08 nó không tồn
tại — bánh cóc cũ chỉ soi **4 tệp** và **5 cái tên**.

⇒ **CHANGE, đã làm.** `test_334` nay 40 phép kiểm (3 bỏ qua = đối chiếu **sống**
với máy B, cần `LTT_LLM_TOKEN`).

---

## Quyết định

| ID | Ứng viên | Quyết định | Vì sao |
|---|---|---|---|
| D-01-1 | Lớp alias công khai ↔ id nội bộ | **KEEP** | Làm đúng việc; 404 của máy B chứng minh nó đang hoạt động |
| D-01-2 | Ba số gõ tay + phần còn lại dẫn xuất | **KEEP** | `96256`/`88555` = 0 lần trong mã sống |
| D-01-3 | Không đoán `usage`, ném rồi hoàn | **KEEP** | Chỗ dễ sai nhất, viết đúng |
| D-01-4 | Bốn bản sao không được canh | **CHANGE — ĐÃ LÀM** | Hai tới tay khách; ghép bằng phép kiểm chứ không bằng import |
| D-01-5 | Cửa stream đếm token tại chỗ | **DEFER → 02** | Hai nguồn sự thật cho một đại lượng tính tiền |
| D-01-6 | `context_window` 131K công bố cạnh trần 96K | **KEEP** | Ba số cho ba việc; cổng B không tới khách (Prompt 03 §6) |

---

## Điểm sau Prompt 01

| Chiều | Trước | Sau | Vì sao |
|---|---:|---:|---|
| Maintainability/SSOT | 4 | **5** | bốn bản sao cuối cùng nay có bánh cóc |
| Tests/evidence | 5 | 5 | — |
| **TỔNG** | 80 | **81** | |

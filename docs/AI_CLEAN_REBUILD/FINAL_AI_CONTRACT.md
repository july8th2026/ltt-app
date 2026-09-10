# FINAL AI CONTRACT — hợp đồng xoá dứt điểm

> **Pha:** 01 · **Lập:** 2026-09-08 · **Nhánh:** `phien/aiclean` · **Nền:** `0d1ffe5a`
> Nguồn: `LTT_AI_CLEAN_REBUILD_CLAUDE_PACK_V2/policies/HARD_DELETE_POLICY.md`

## 1. Năm họ PHẢI BIẾN MẤT khỏi runtime

| # | Họ | Bao gồm |
|---|---|---|
| 1 | **Gemini Image** | `gemini-*-image`, đường sinh ảnh qua Google |
| 2 | **Gemini Text / VLM / Vision** | `generateContent`, `generativelanguage`, `vertexai` |
| 3 | **ChatGPT / OpenAI external** | `chat/completions`, `images/generations`, `responses` |
| 4 | **Codex external execution** | `codex_sidecar/`, `tools/cam_cli.py`, đường chạy Codex ngoài |
| 5 | **apiai.vn** · **cheapkeyai** | mọi provider trung gian bán khoá |

…cùng **mọi fallback / direct HTTP cũ** cho Text/VLM/Image.

### Bề mặt sống phải chết theo

`direct HTTP/SDK client` · `adapter` · `provider registry` + `model catalog`
đang hoạt động · route tạo request mới · worker/service/helper · `retry`/
`fallback` · tra bí mật + phụ thuộc biến môi trường · health-check riêng
provider · hành động *test provider* ở admin · bộ chọn provider/model trên giao
diện · cron/webhook/callback chỉ phục vụ provider đã retire · tài liệu **hướng
dẫn sử dụng** còn hiệu lực.

## 2. Chỉ có BA nhãn. Không có `KEEP` cho legacy execution

| Nhãn | Nghĩa |
|---|---|
| `MIGRATE_PRODUCT_THEN_DELETE_ENGINE` | Giữ **sản phẩm** cho khách, thay **động cơ** sang LTT, rồi xoá động cơ cũ |
| `DELETE` | Xoá thẳng khỏi runtime |
| `HISTORY_ONLY` | Còn lại, nhưng **không chạy được** — §4 |

⛔ **Không có nhãn thứ tư**, và không có ngoại lệ vì: fallback · tương thích ·
dùng sau · đã có sẵn khoá API · dễ rollback · tiện cho admin.

🔑 **Rollback bằng Git SHA/tag, không bằng legacy fallback.** Nền của chiến dịch
là `0d1ffe5a`; mọi trạng thái trước bất kỳ pha nào đều lấy lại được bằng một
`git checkout`. Một đường mã sống "để phòng khi" **không phải** cơ chế rollback —
nó là một đường chạy mà không ai kiểm, và nó sẽ được gọi vào lúc không ai xem.

## 3. Được phép sống

`LTT_LLM` (TEXT/VLM) · `LTT_IMAGE` (IMAGE) · `Voice/VieNeu` · `Seedance/BytePlus`
(VIDEO) · `LTT Public API` · `runtime_noi_bo` · `jobs`/`credit`/`storage`/worker
canonical · `api_pool` **đúng vai trò** kho khoá/provider.

⚠️ *"`api_pool` đúng vai trò"* nghĩa là: **cơ chế** kho khoá sống; **các hàng dữ
liệu** provider `gemini`/`apiai`/`cheapkey` trong đó là `CONFIG_DELETE` +
`SECRET_DELETE_LATER`. Giữ cái ngăn kéo, bỏ những chiếc chìa đã retire.

## 4. `HISTORY_ONLY` — năm điều kiện, thiếu một là không đạt

Chỉ được giữ cho: dữ liệu DB lịch sử · nhãn model/provider quá khứ · nhật ký
kiểm toán · migration **đã chạy production** · tài liệu phát hành đã lưu trữ ·
fixture kiểm đọc lịch sử.

```
1. khong callable        khong ham/lop/route nao goi toi duoc
2. khong selectable      khong xuat hien trong bat ky bo chon nao
3. khong secret lookup   khong doc mot bien moi truong / khoa nao
4. khong network egress  khong mot byte nao ra ngoai
5. khong fallback        khong duong lui nao dan toi no
```

⭐ Mỗi điều kiện phải có **một phép kiểm** ở dải `1000–1099` (dải cấp cho cây
này), không phải một câu khẳng định trong tài liệu.

⚠️ Và phép kiểm phải hỏi **HÀNH VI**, không hỏi **hình dạng** (`AGENTS.md` §4c).
Câu tự hỏi: *thứ tôi đang khẳng định có tồn tại được nếu chương trình không chạy
không?* Nếu có ⇒ nó không kiểm hành vi. Một bánh cóc AST hỏi *"còn `import
google.generativeai` không"* vẫn xanh khi ai đó gọi cùng endpoint bằng
`httpx.post` — nên điều kiện 4 phải đo **lối ra mạng**, không đo tên gói.

## 5. Nhãn thứ tư TỒN TẠI, và nó không phải ngoại lệ của §2

```
NOT_A_LEGACY_SURFACE
```

Một tệp khớp mẫu tìm kiếm nhưng **không hề là** bề mặt legacy. Đây không phải
"giữ lại legacy" — đây là **sửa phép đo**. Quét pha 02 tìm ra hai lớp:

| Lớp | Ví dụ đo được | Vì sao KHÔNG được xoá |
|---|---|---|
| **Tên gói cục bộ** | `cutclipshort/adapters/whisper.py` — **12 dòng mã** khớp `openai` | `openai-whisper` là gói pip **chạy cục bộ** (`import whisper`, `load_model`). Không một byte ra mạng. Đây là phiên âm của ASV/taoclipngan |
| **Tên thư mục tham chiếu** | `apps/upscalevideo/engine.py` | *"BOT GEMINI"* là thư mục kho chỉ-đọc `D:\BOT GEMINI`, không phải API Gemini |

🔑 **Một chiến dịch chạy bằng `grep` sẽ xoá cả hai, và cả hai đều nằm trong danh
sách giữ sống.** Đây là lý do pha 02 phân loại bằng `tokenize` + xem tận nơi,
không phải bằng số lần khớp.

## 6. Ba câu bắt buộc của `AGENTS.md` §4c — trả lời TRƯỚC dòng mã đầu tiên

Chiến dịch sửa `platform_core/` ⇒ §4c áp dụng.

### 1. Nếu chỉ MỘT SỐ cây nhận bản vá, chuyện gì xảy ra?

Bảy cây khác vẫn giữ nguyên đường Gemini/OpenAI của chúng — **và điều đó đúng**,
vì chúng ở nhánh khác. Chế độ hỏng thật không nằm ở đó mà ở **thứ tự trong một
cây**: xoá động cơ trước khi chuyển người gọi ⇒ mọi caller nổ.

⇒ Đó chính là lý do thứ tự pack là `03 MAP → 04 BLOCK → 05/06 MIGRATE → 07/08
DELETE`. **Thứ tự này là câu trả lời cho §4c câu 1, không phải nghi thức.**
Gộp 07 vào 05 là tạo ra đúng chế độ hỏng "tệ hơn trước khi vá".

### 2. Đường suy biến là gì?

Khi một sản phẩm **không map được** sang LTT_LLM/LTT_IMAGE: pack nói
*disable/remove feature, không fallback external*. Đường suy biến vì vậy là
**tính năng biến mất**, không phải **tính năng lặng lẽ quay về Gemini**.

⚠️ Và **cố ý phải phân biệt được với tai nạn**: một tính năng bị gỡ có chủ đích
phải nói ra điều đó (thông báo/404 rõ ràng), không được trông giống một lỗi.

### 3. Tôi đang hỏi một NHÃN hay một QUAN HỆ?

Quét theo tên (`gemini`, `openai`) là hỏi **NHÃN** — rẻ và **sai im lặng**, đúng
như hai dương tính giả ở §5. Câu hỏi đúng là **QUAN HỆ**: *dòng này có dẫn tới
một byte đi ra ngoài không?* ⇒ pha 02 phải dựng `OUTBOUND_EGRESS_MATRIX.csv`
theo **lối ra mạng**, và `DELETE_DEPENDENCY_GRAPH.md` theo **ai gọi ai** — hai
thứ đó là quan hệ, không phải nhãn.

## 7. Ngoài phạm vi — ghi report, không tự mở rộng

scheduler · priority · GPU fairness · runtime V2 · Public API V2.
Thấy khiếm khuyết ở đó ⇒ ghi vào `OUT_OF_SCOPE_FINDINGS.md`, **không sửa**.

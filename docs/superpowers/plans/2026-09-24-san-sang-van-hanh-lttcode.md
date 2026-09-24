# Sẵn sàng vận hành LTTCODE 0.2.12 — kế hoạch

> **Mục tiêu của chủ dự án:** dùng 0.2.12 làm việc thật, rồi **lấy bản ghi phiên về phân tích
> lỗi và nâng cấp**. Kế hoạch này làm cho điều đó khả thi.

**Nguyên tắc chi phối (chủ dự án chốt 24/09):** *"phân tích logic vận hành để xử lý cho thông
suốt, không chắp vá gây bug chồng chéo"*. ⇒ Mỗi mục dưới đây sửa **một vòng đời trọn vẹn**, không
vá từng triệu chứng. Chỗ nào cần dọn dẹp thì **một cơ chế duy nhất**, không ba cái chạy song song.

---
## Pha 0 — PHẢI XONG TRƯỚC KHI VẬN HÀNH

Ba việc này không phải "nên làm". Thiếu chúng thì việc vận hành **tự phá hỏng bằng chứng của
chính nó**.

### 0.1 — Điểm khôi phục ăn hết đĩa (đang làm)

**Đo được:** 102 GB cho 5 điểm khôi phục của **một** kho. Đã dọn (C: 411,9 → 512,6 GB).

Bốn chỗ rò, phải bịt cả bốn — bịt ba cái đầu thì nó vẫn phình, chỉ chậm hơn:

| # | Rò | Cách bịt |
|---|---|---|
| 1 | Một bản chụp chép cả `target/` (build Rust) | khai `excludeGlobs` — gói **không đọc `.gitignore`**, phải liệt tay |
| 2 | 100 bản mỗi phiên | hạ `maxSnapshots` |
| 3 | **Tích luỹ qua các phiên** — sàn `keepNewestPerSession` giữ bản mới nhất của **mỗi** phiên ⇒ N phiên cộng dồn thẳng | trần **tổng**, đuổi cũ nhất trước |
| 4 | **Thư mục của workspace ĐÃ CHẾT** — tên là băm đường dẫn; worktree xoá rồi thì không ai chụp tiếp nên cơ chế dọn của gói không bao giờ chạm tới | quét lúc khởi động |

⚠️ Và chỗ rò thứ năm, khác loại: **không ai nhìn thấy nó lớn lên.** 102 GB chỉ lộ ra vì tình cờ
dọn. ⇒ **in một dòng tổng dung lượng lúc khởi động**.

⛔ **MỘT lượt quét lúc khởi động** làm cả bốn việc, thứ tự xác định, mỗi bước ghi rõ đã xoá gì.
Ba cơ chế dọn rời nhau trên cùng một thư mục **là** bug chồng chéo: chúng đua nhau và không ai
truy được cái nào xoá cái gì. Hỏng ở bất kỳ bước nào ⇒ ghi log rồi **đi tiếp**, không chặn khởi động.

### 0.2 — Bản ghi bị xoay vòng nuốt mất

| Sự thật | Nguồn |
|---|---|
| `lttcode.log` trần **5 MB** | `sidecar.rs:59-60` |
| Chỉ kiểm xoay vòng **lúc khởi động**, không xoay giữa phiên | `sidecar.rs:222-227` |
| Giữ **đúng một** thế hệ cũ: `lttcode.1.log`, mỗi lần xoay **ghi đè** bản trước | `sidecar.rs:1313` |
| 🔴 `collect_session_errors.ps1:16` lọc `lttcode.log*` — **không khớp** `lttcode.1.log` | — |

⇒ **Hai lần khởi động lại là bằng chứng biến mất**, và công cụ thu thập **vốn đã không đọc** thế
hệ cũ. Đợt vận hành dài chắc chắn vượt 5 MB.

**Việc:** sửa bộ lọc; nâng trần và số thế hệ giữ lại **cho kỳ vận hành**; ghi rõ con số chọn và vì sao.

### 0.3 — 🔴 Lượt THÀNH CÔNG không ghép được với máy chủ

Máy chủ sinh `request_id` (`llm_gateway/api.py:155-169`), trả qua header `X-LTT-Request-Id`, và
**chính nó là `credit_entries.job_id`** (`platform_core/llm/thanh_toan.py:105`).

🔴 Nhưng client **chỉ gắn `requestId` vào đường LỖI** (`plugins/llm-ltt/src/adapter.ts:623,630,644,646`).
**Lượt thành công không bao giờ mang `requestId`** vào sự kiện đã phát.

⇒ **Chỉ ghép được client↔server khi lượt đó LỖI.** Với ~95 % lượt chạy trót lọt, ta **không biết**
lượt nào tốn bao nhiêu credit, chờ suất bao lâu, TTFT bao nhiêu — dù **máy chủ đã ghi đủ cả ba**.

Đây là lỗ hổng đắt nhất trong ba mục Pha 0: nó không làm hỏng gì hôm nay, nhưng nó **cắt mất một
nửa giá trị của toàn bộ đợt vận hành**. Và nó rẻ: một trường đi kèm sự kiện usage.

---
## Pha 1 — công cụ phân loại (sau khi có dữ liệu thật)

**Không viết trước khi có bản ghi thật.** Viết công cụ cho dữ liệu tưởng tượng là cách nhanh nhất
có một công cụ không ai dùng.

| Có sẵn | Thiếu |
|---|---|
| `collect_session_errors.ps1` — đọc `lttcode.log`, gom cặp spawn/exit, mã thoát, độ trễ boot | Không đọc **bản ghi phiên** (`sessions/*/session.v3.jsonl.zstd`) |

**Dấu hiệu một phiên ĐÁNG xem** (thay vì đọc hết):
1. có sự kiện `ltt_error` / `canonical_code`;
2. có `step` thiếu `step/end` — **sập giữa chừng**;
3. có `TOOL_OUTCOME_UNKNOWN` — công cụ chạy mà không biết kết quả;
4. có lượt lỗi mang `requestId` — **lượt duy nhất ghép được sang máy chủ** (cho tới khi 0.3 xong).

⚠️ Các làn tối nay đã viết **nhiều script rời** đọc bản ghi phiên rồi bỏ đi. Việc ở đây là gom
thành **một** công cụ dùng lại được, không phải viết cái thứ mười.

---
## Pha 2 — vòng nâng cấp

1. Vận hành thật → 2. phân loại bằng công cụ Pha 1 → 3. lỗi vào `docs/VIEC_CAN_LAM_HOP_NHAT.md`
→ 4. sửa → 5. dựng bản mới → 6. **đo lại trên bản ĐÃ CÀI**.

⚠️ Bước 6 không được bỏ. Bài học 24/09: **ba lần "đã vá" đều có phép kiểm xanh** mà bản vá
chưa bao giờ tới tay người dùng. Với mọi thứ đi qua đóng gói, phép kiểm phải chạy trên **cây đã
dựng** hoặc **bản đã cài** — cây phát triển nói dối rất thuyết phục.

---
## Những gì KHÔNG làm

- ⛔ **Không tắt checkpoint-rewind** để cho nhẹ đĩa. Nó là lưới an toàn thật khi agent sửa hỏng.
  Sửa `excludeGlobs` giữ được cả hai.
- ⛔ **Không viết công cụ phân loại trước khi có dữ liệu thật.**
- ⛔ **Không đổi `sessions/` sang tự xoá.** Giữ vô hạn là **đúng** cho mục tiêu nâng cấp; cái cần
  là **nhìn thấy** dung lượng, không phải tự xoá bằng chứng.

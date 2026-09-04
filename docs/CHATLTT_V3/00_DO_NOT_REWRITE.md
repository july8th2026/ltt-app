# P00 — DANH SÁCH KHÔNG ĐƯỢC VIẾT LẠI

*Mỗi mục ghi **vì sao** nó bất khả xâm phạm và **cái gì sẽ hỏng** nếu vượt rào.
Một danh sách cấm không có lý do là một danh sách sẽ bị bỏ qua.*

⛔ Muốn đụng bất kỳ mục nào ở đây: **dừng lại, viết ADR riêng, đưa bằng chứng
một khiếm khuyết thật**. "Tôi thấy cách khác gọn hơn" không phải bằng chứng.

---

## 1. Đường tiền — 🔴 tuyệt đối

| Không đụng | Vì sao | Hỏng gì nếu vượt |
|---|---|---|
| `platform_core/credit.py` (`giu_cho`/`quyet_toan`/`hoan`) | sổ cái **là** sự thật tính tiền; `quyet_toan` không bao giờ thu quá phần đã giữ (Q84); `hoan` idempotent theo job | hai đường tính tiền = tiền lệch hai chỗ, và lệch âm thầm |
| `platform_core/llm/gia_token.py` | **ba con số duy nhất** được đại diện cho giá model nhà trong toàn bộ mã; toàn số nguyên milli-credit, không float | dấu phẩy động trong đường tiền = hai lần cộng ra hai kết quả |
| `platform_core/llm/thanh_toan.py` — *phần quy đổi* | nó **chỉ** dịch token→credit rồi gọi ba nguyên hàm; không ghi bút toán, không đụng số dư | dựng sổ tiền thứ hai |
| `PHIEN_BAN_GIA` cũ | *"đối soát một khoản tiền vài tháng sau nghĩa là đọc hai sự thật đều được ghi lúc đó"* | không đối soát được hoá đơn cũ |

⭐ **Ngoại lệ được phép, và chỉ một:** phương án **C2** (sổ tích luỹ phần lẻ)
trong `thanh_toan.py`. Chính tệp đó để ngỏ và ghi rõ *"nó chỉ đụng module này,
**không** đụng `gia_token.py`. Ranh giới đó là có chủ ý."* Đây là lối đi đã
được vẽ sẵn cho §D4 — dùng đúng lối ấy, đừng mở lối khác.

---

## 2. Bốn bước của luồng — 🔴 thứ tự đã đo đúng trên production

`platform_core/runtime_noi_bo/luong.py`:

```
chuan_bi()  →  mo_thuong_nguon()  →  LuotLuong.luong  →  quyet_toan trong finally
```

| Bất biến | Vì sao | Hỏng gì nếu vượt |
|---|---|---|
| `chuan_bi` **commit trước khi chạm model** | generator chạy **sau khi** phản hồi đã bắt đầu; lúc đó phiên CSDL của request đã đóng | giữ chỗ không được ghi ⇒ chạy model không có tiền bảo chứng |
| Quyết toán trong **`finally`**, không phải "sau vòng lặp" | khách đóng kết nối ⇒ `GeneratorExit` ném ngay chỗ `yield`; nhánh sau vòng lặp **không bao giờ chạy** | khách ngắt = không thu tiền, âm thầm |
| `response.started` phát **trước** khi mở luồng | prompt dài prefill > 100 s; byte đầu sớm là thứ giữ kết nối không bị Cloudflare 524 | 524 hàng loạt với prompt dài |
| Alias→id nội bộ **ngay trước khi rời nền tảng** | khách không bao giờ thấy id thật, mã của khách không ghim vào nó (`test_212`) | đổi GGUF = breaking change cho khách |
| Kẹp `max_tokens` **và ghi lại vào thân gửi** | kẹp cái mình thu tiền mà không kẹp cái mình gửi ⇒ máy B trả 413 (H38/L2) | 413 với prompt dài |

**20 tệp test** ghim tầng này. Sửa nó là sửa thứ đã trả giá để đúng.

---

## 3. Hàng đợi job, lease, admission — 🔴

| Không đụng | Vì sao |
|---|---|
| `platform_core/job_runner.py`, `leases.py`, `job_submit.submit_with_credit` | validate/giá/giữ chỗ/queue trong **một** giao dịch; `so_lan_thu` từ manifest; `owner_id` bị **ép** bằng `user_id` |
| `platform_core/llm/admission.py` | `ORPHAN_TIMEOUT` 20 phút; `release_by_id` idempotent; savepoint pysqlite không đáng tin nên đã có lưới đỡ tường minh |
| `platform_core/jobs.PROVIDER_REJECTED` / `DangBan` | **bận ≠ hỏng**: không chạm sổ tiền, không tiêu lượt thử |

⚠️ **R1 có thể buộc chạm `admission.py`** (phương án B của ADR P02). Nếu ADR
chọn B thì đó là một ngoại lệ **có ADR**, không phải một lần sửa tiện tay — và
nó phải kèm test cho `ORPHAN_TIMEOUT`, cho đua hai phiên, cho lease mồ côi.

---

## 4. Registry, ToolSpec, ba cổng — 🔴

| Không đụng | Vì sao |
|---|---|
| **Ba cổng độc lập**: `customer_visible` (palette Agent) · `api_exposed`+`LTT_PUBLIC_API_TOOLS` (bán qua `/api/v1`) · allowlist sản phẩm (`chinh_sach.CONG_CU_CHO_PHEP`) | quên một cổng ⇒ **thiếu tính năng**; gộp cổng ⇒ **lộ năng lực nội bộ ra bề mặt không ai duyệt** |
| `public_api/catalog.project_tool` | đã làm đúng việc khó: bỏ id model nội bộ, ẩn tham số máy chủ tự quyết, giữ đúng kiểu enum |
| `ToolSpec.api_contract` bắt buộc khi `api_exposed` | không khai đủ ⇒ registry **từ chối** expose, chứ không im lặng publish hợp đồng rò rỉ |

⛔ V3 **thêm một dòng** vào allowlist là thêm một **quyết định sản phẩm**, không
phải một dòng mã. `chinh_sach.py` đã ghi: D8 chốt `image.generate` (model đám
mây) **không** được mời cho tới khi chủ sản phẩm duyệt.

---

## 5. Dữ liệu ChatLTT — 🟡 mở rộng được, không đổi hình dạng

| Không đổi | Vì sao |
|---|---|
| `chatltt_message` là **cây** dựng lại từ `parent_id`; không cột `children`, không `siblingIdx` | LibreChat cũng vậy; 5 test `convoStructure.spec.ts` của họ là đặc tả cho `test_617` |
| `created_at(con) > created_at(cha)` ép ở **tầng ghi** | LibreChat phải vá muộn ở `fork.js:46-56` vì không ép lúc ghi |
| Mọi truy vấn có `user_id`; không hàm nào đọc theo `id` trần | IDOR chặn ở tầng service — route **không có cách nào** "quên" |
| `owner`/`user_id` là `String(36)` | `apps/ltt_voice/tables.py:66-75`: khai số ⇒ **mọi khách thành chủ số 0** |
| `blocks` là **mảng khối typed** | khối mới = **phần tử mới trong mảng cũ**; đổi hình dạng = hội thoại cũ vỡ |
| `chatltt_execution` = **một lần gọi model/job** | ba cột tiền vô hướng của nó **đúng** cho việc đó; `run` là khái niệm **mới ở trên**, không phải đổi nghĩa cái cũ |

---

## 6. Kiến trúc — 🔴 bất biến của gói prompt, và LTT đã cưỡng chế sẵn

| Bất biến | LTT cưỡng chế ở đâu |
|---|---|
| ChatLTT **không bao giờ** gọi máy B trực tiếp | `test_147`/`test_308`: `apps/chatltt/` không import `ltt_llm`/`anhnoibo`/`ltt_voice`, không biết URL máy B |
| ChatLTT **không** dùng `/api/v1` làm đường thi hành nội bộ | `runtime_noi_bo` là facade nội bộ riêng (D3) |
| Model **đề nghị** dùng tool; **nền tảng** cho phép thi hành | phải giữ khi mở vòng lặp (§C5 ma trận khoảng trống) |
| Hành động có phí/ra ngoài/phá huỷ **không** được LLM tự cho phép | duyệt là một **hàng CSDL** do route có phiên đăng nhập + CSRF ghi |
| Không cắt xén âm thầm, thi hành âm thầm, tính tiền âm thầm, hàng đợi ẩn | `su_kien.ap_dung` **ném** với loại sự kiện lạ — fail-closed đã là thói quen của mã này |
| Giao diện **không** là sự thật của thi hành/tiền/duyệt | D6: sự thật ở CSDL |

⛔ **Bộ kiểm P01 chọc thẳng `llama-server` phải nằm NGOÀI `apps/chatltt/`** —
đặt ở `docs/CHATLTT_V3/harness/`. Đặt trong app là làm đỏ `test_147`/`test_308`
ngay lượt gate đầu tiên.

---

## 7. Cổng chất lượng — 🔴 đừng nới bánh cóc, hãy sửa mã

| Bất biến | Vì sao |
|---|---|
| `_chung.kiem_csrf` là **một cửa duy nhất** cho mọi route ghi | `test_628` đọc mã nguồn từng route và đòi thấy đúng tên hàm — nó bắt được đúng chuyện này ở lượt gate đầu sau khi cửa tải ảnh ra đời |
| Test **không** được sửa tệp trong cây (dùng `tmp_path`) | test sửa tạm tệp trong repo tự phá lượt gate chứa nó |
| **Không** `importlib.reload(platform_core.db)` trong test | `test_630` từng làm 16 phép kiểm đỏ ở **bảy tệp khác**; `test_631` (AST) chốt lại |
| `-n 6` là trần cứng | máy 10 lõi vật lý, nhiều phiên dùng chung |
| Ghi tệp cấu hình **không BOM** | PS 5.1 chèn BOM ⇒ `json.load()` vỡ ⇒ `/health/ready` 503 trong khi dịch vụ vẫn chạy. **Đã thực sự làm sập production**; `test_61` chốt |
| `.ps1` thuần ASCII | PS 5.1 đọc `.ps1` không BOM theo ANSI; một dấu tiếng Việt hỏng cả câu lệnh và báo lỗi ở **dòng khác** |
| Đổi static ⇒ **cache-bust** | CF có TTL; đổi tệp mà URL không đổi ⇒ khách nhận bản cũ |

---

## 8. Câu một dòng để phiên sau đọc

> Kiến trúc hiện tại **không có khiếm khuyết nào** buộc phải viết lại.
> V3 là **bốn điểm cắt trong `apps/chatltt/`** (`00_CALL_GRAPH.md` §4) cộng ba
> bảng mới, đứng trên các nguyên hàm đã trả giá để đúng.
> Ai thấy mình đang sửa `platform_core/` ngoài §3-ngoại-lệ: **dừng lại và hỏi vì sao.**

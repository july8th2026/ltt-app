# Kế hoạch tự triển khai phần còn lại

> ⚠️ **Ảnh chụp 01/09/2026** (cả thư mục `docs/audit_ltt_llm/`) — không phải hiện trạng. Số đồng thời LLM ở đây
> (`DONG_THOI_MAY_B=1`, `parallel=1`, một suất máy B…) **đã cũ** → `apps/ltt_llm/ngan_sach.HO_SO`
> (L-23, L-28 trong `docs/ltt_llm_dual/DECISION_LOG.md`).

**01/09/2026.** Chủ dự án cấp quyền chạy đầy đủ và yêu cầu **dọn các cơ chế cần
họ hỗ trợ**. Tài liệu này làm hai việc: rà xem cái gì *thật sự* cần người, và
xếp phần còn lại theo thứ tự chạy.

---

## 1. Dọn cơ chế chặn — bốn trong sáu không thật sự cần người

Rà lại từng thứ tôi đã ghi là *"cần chủ dự án"*. Bốn cái trong đó tôi ghi vì
**chưa tra đủ**, không phải vì chúng thật sự chặn.

| Cơ chế | Trước | Sự thật sau khi tra |
|---|---|---|
| Quyền Administrator | "cần UAC" | ✅ **Đã gỡ.** `NexusAgent` chạy `LocalSystem`. Đo: `sc failure` trực tiếp trả `Access is denied (5)`; qua Nexus thì **5/5 dịch vụ** đặt được |
| Khoá `/api/v1` cho E15–E17 | "chủ sản phẩm phải cấp" | ✅ **Đã gỡ.** `tools/khoa_thu_api.py` phát khoá cho tài khoản đuôi `.local`, dùng đúng `issue()` mà cổng nhà phát triển gọi |
| Tài khoản thử | ngầm định cần người | ✅ `tools/tai_khoan_thu.py` |
| Canary qua Cloudflare | ngầm định cần người | ✅ `tools/api_prod_canary.py` (chỉ-đọc, chạy trên máy thật) |
| **Nới trần ghim `pillow`** | "cần quyết định" | ⚠️ **Vẫn nên hỏi** — nới `<12` → `12.3.0` chạm **mọi app ảnh**, và cái giá của một hồi quy ở đó lớn hơn cái giá của một câu hỏi |
| **Prompt 08 nghiệm thu độc lập** | "phiên khác chạy" | 🔒 **Giữ nguyên, và đây không phải một cơ chế** — nó là một nguyên tắc. Tôi đã thi hành bảy phase; tự nghiệm thu thì chữ *độc lập* chỉ còn là trang trí |

⭐ Bài học của mục này không phải *"đã gỡ được bốn"*. Là: **bốn lần tôi ghi
"cần chủ dự án" mà công cụ đã nằm sẵn trong `tools/`.** "Cần người" là một kết
luận, và tôi đã đưa ra nó mà không tra — đúng cái lỗi cả phiên này đi săn, chỉ
là ở tầng quy trình thay vì tầng đo đạc.

⛔ Và một ranh giới **không** dọn: `khoa_thu_api.py` chỉ nhận đuôi `.local`. Một
   khoá API là chứng danh sống và **tiêu tiền thật** của chủ sở hữu; phát khoá
   cho tài khoản khách — kể cả để "thử giúp họ" — là mượn danh tính và ví của
   họ. Chốt đó ở lại.

---

## 2. Thứ tự chạy

Xếp theo **giá trị / (rủi ro × công)**, không theo số hiệu.

### A. E15–E17 — canary client thật qua Cloudflare *(mở khoá cả Prompt 05)*

```
tai_khoan_thu.py  →  khoa_thu_api.py  →  api_prod_canary.py
```

Đây là điều kiện §11 mục 1 của `API_PLATFORM_FULL_RELEASE_READINESS.md`:
*"gọi thật qua Cloudflare bằng khoá thật"*. `public_api_load_test.py` **cố ý
không** trỏ production, nên nó không thay được.

⚠️ Nó **tiêu credit thật** của tài khoản thử. Đó là ý muốn — một canary không
tiêu tiền là một canary không đi qua đường tính tiền.

### B. Deploy bản sửa `khoi_tao()`

Bản đang chạy có `duoi_dich_vu` nhưng `khoi_tao()` nằm trong mã chết, nên nó
khai *"chưa gọi"*. Cần một lượt deploy nữa để phép thăm mồ côi thật sự làm việc.

### C. Prompt 04 — `--lan 5` và **vision**

`qwen38-vision` **đang bán** mà chưa có bài đánh giá nào. Đây là món nợ lớn nhất
còn lại về chất lượng, và `tools/danh_gia_llm.py` hiện **không có** chiều vision
(đã tra: `grep vision` trả rỗng).

### D. Prompt 02 — bằng chứng sống

Phase tự khai "chưa đóng" vì kiểm bằng đọc mã + bằng chứng sẵn có. Sau khi A
xong thì có khoá thật, nên phần lớn đo được.

---

## 3. Việc còn lại thật sự cần người

| # | Việc | Vì sao không tự làm |
|---|---|---|
| N7 + N9 | Reboot máy A + đọc nhật ký khởi động Windows | Reboot **cắt luôn phiên đang làm**. Phải là cửa sổ chủ dự án chọn |
| — | Nới trần ghim `pillow` | Chạm mọi app ảnh; giá của hồi quy > giá của một câu hỏi |
| Prompt 08 | Nghiệm thu độc lập | Nguyên tắc, không phải cơ chế |

Ba dòng. Trước khi rà là sáu.

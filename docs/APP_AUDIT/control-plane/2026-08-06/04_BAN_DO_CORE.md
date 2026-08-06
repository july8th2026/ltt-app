# 04 — Bản đồ `core/`: phần nào còn sống, phần nào chỉ còn test giữ lại

Hạng mục #8 của đợt rà soát 2026-08-06. **Phiên này chỉ đo, chưa xoá gì.**

`core/` là 15.668 dòng / 70 module thừa kế từ thời sản phẩm còn là bot Facebook
+ TikTok. Nền tảng hiện bán công cụ AI theo credit. Câu hỏi cần trả lời trước
khi đụng vào: *bao nhiêu trong đó còn phục vụ người dùng hôm nay?*

## Cách đo

Không đếm `grep`. Đếm **khả đạt bắc cầu** (transitive reachability) qua đồ thị
import, từ các điểm vào thật:

- `server.app` (tiến trình web), `worker_main`, `job_worker`;
- `apps/<slug>/routes.py` và `apps/<slug>/jobs.py` của cả 12 app.

Lý do: một module có người `import` chưa chắc còn sống — nếu chỉ `tests/` import
nó thì nó là **code chết được test của chính nó giữ cho ấm**. Phép đo dưới đây
cố tình **loại `tests/` khỏi tập điểm vào**.

## Kết quả

| Nhóm | Module | Dòng | Ý nghĩa |
|---|---:|---:|---|
| Đạt được từ **mọi app đang bán** | 1 | 89 | hạ tầng thật sự dùng chung |
| Đạt được **chỉ qua** `server.app` / `worker_main` | 64 | 15.044 | bảng điều khiển FB/TikTok cũ |
| Không đạt được từ bất kỳ điểm vào nào | 5 | 535 | chết hẳn |

Module duy nhất mọi app dùng: **`core.runtime_paths`** (89 dòng).

Nói cách khác: **99,4% của `core/` không phục vụ app nào đang bán.**

### 5 module không ai gọi tới

| Dòng | Module |
|---:|---|
| 357 | `core.insights_fetcher` |
| 176 | `core.tiktok.token_refresher` |
| 1 | `core.facebook` (chỉ là `__init__`) |
| 1 | `core.tiktok` (chỉ là `__init__`) |
| 0 | `core` (chỉ là `__init__`) |

> **Đính chính khi thực hiện (2026-08-06):** ba file `__init__.py` là **dấu hiệu
> package**, không phải code chết — xoá chúng là gãy `core.facebook.commenter`
> và `core.tiktok.*` đang sống. Thực tế xoá được **2 module / 533 dòng**, không
> phải 5/535.

`core.tiktok.token_refresher` đáng chú ý: có `core.token_refresher` ở tầng trên
vẫn sống, nên đây nhiều khả năng là bản trùng bị bỏ quên chứ không phải tính
năng còn dở.

## Phần đáng lo hơn con số: 62% route công khai là của sản phẩm đã đóng băng

`core/` không nằm im. Nó được gắn vào **HTTP route đang chạy**, vô điều kiện,
trong `server/app.py`:

```python
app.include_router(accounts_routes.router)   #  8 route
app.include_router(workers_routes.router)    #  4
app.include_router(settings_routes.router)   #  7
app.include_router(sheet_routes.router)      #  7
app.include_router(manual_routes.router)     #  6
app.include_router(monitor_routes.router)    #  6
app.include_router(oauth_routes.router)      #  5
```

| | Route | Tỉ lệ |
|---|---:|---:|
| Bảng điều khiển FB/TikTok cũ (bản port từ GUI desktop) | 43 | **62%** |
| Nền tảng đang bán (auth, đăng ký, job, credit, thanh toán, health) | 26 | 38% |

`settings` / `oauth` / `monitor` không phải ngoại lệ: đọc docstring của chúng
thì đều ghi rõ là bản port của `gui/monitor_tab.py`, của kho token FB/TikTok,
của trang sửa cấu hình Sheet — tức cùng một sản phẩm cũ.

Trạng thái của app đó trong `CLAUDE.md`: **"⏸️ đóng băng — không phát triển thêm"**.

## Vì sao điều này quan trọng

1. **Bề mặt tấn công.** 43 route đang phục vụ cho nghiệp vụ không còn bán. Phần
   lớn có `require_operator`, nhưng "ít rủi ro" khác "không rủi ro", và mỗi
   route là một chỗ phải xét lại mỗi lần rà bảo mật.
2. **Chi phí nhận thức.** Người mở repo lần đầu thấy `core/` to gấp đôi
   `platform_core/` và tưởng đó là lõi nền tảng. Tên thư mục nói dối.
3. **Đè nặng mọi lần kiểm.** 15k dòng này nằm trong mọi lần chạy linter, mọi
   lần quét bí mật, mọi lần đọc để tìm lỗi.

Nhưng **không** phải chi phí runtime đáng kể: phần lớn `core.*` được import
trễ (trong thân hàm), nên chúng không làm chậm khởi động.

## Đề xuất — chưa làm trong phiên này

Xếp theo tỉ lệ lợi ích trên rủi ro:

| # | Việc | Rủi ro | Lợi |
|---|---|---|---|
| C1 | ✅ **XONG 2026-08-06** — xoá 2 module (533 dòng) + 10 test chỉ phục vụ chúng | rất thấp | dọn sạch, đo được ngay |
| C2 | Đưa 43 route legacy vào **một cờ bật/tắt** (`LTT_SOCIALBOT_ROUTES`), mặc định TẮT ở production | thấp | bề mặt công khai giảm 62% mà không xoá code |
| C3 | Chuyển `core.runtime_paths` sang `platform_core/` rồi cắt phụ thuộc `core/` khỏi app | thấp | app không còn dính gì tới `core/` |
| C4 | Sau C2 chạy ổn định một thời gian: tách hẳn `core/` + 43 route ra repo riêng | trung bình | repo còn đúng phần đang bán |

**C1 và C3 đã làm xong 2026-08-06.** C2 cần người dùng xác nhận, vì tắt route nghĩa là
bảng điều khiển cũ biến mất khỏi web — cần biết có ai còn dùng không.

## Điều phép đo này KHÔNG chứng minh

- Không chứng minh 64 module "legacy" là code chết. Chúng **đạt được** từ
  `server.app`; nếu còn người vào bảng điều khiển cũ thì chúng vẫn chạy thật.
  Cái đo được là chúng **không phục vụ app nào đang bán**.
- Không đo được đường gọi động (`importlib`, chuỗi tên module). Đã soát tay:
  `core/` không dùng kiểu đó, nhưng đây là giới hạn của phương pháp, ghi ra
  cho đúng.
- Không đo lưu lượng thật. Muốn biết 43 route kia có ai gọi không thì phải đọc
  log truy cập — chưa làm.

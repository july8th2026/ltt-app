# Quyết định nền tảng — chốt ngày 2026-07-31

> Đây là **nguồn chân lý** cho hướng đi của `D:\LTTSTUDIOSAPP`.
> Khi tài liệu khác mâu thuẫn với file này, file này đúng.
>
> Muốn đổi một quyết định: **thêm dòng mới vào bảng, ghi rõ lý do**. Không sửa
> đè lên dòng cũ — mất lý do là mai sau lặp lại đúng cuộc tranh luận đã xong.
>
> Không có giá trị bí mật nào trong file này.

---

## 0. Dự án này là gì

**Nền tảng SaaS đa người dùng bán công cụ AI theo credit.** Mỗi công cụ là một
app cắm vào nền tảng.

| Khái niệm | Từ dùng thống nhất |
|---|---|
| `app.lttstudios.com` | **control plane** — trang tổng quan: đăng nhập, danh sách app, credit, lịch sử job |
| Từng công cụ | **app** (không gọi là "bot") |
| `app.lttstudios.com/<slug>` | **route prefix** của app |
| Tiến trình chạy job | **worker** |

Không gọi các công cụ là "bot". "Bot" gợi ý thứ tự chạy không người điều khiển;
cái đang xây là cửa hàng công cụ, người dùng bấm nút và trả tiền.

---

## 1. Mười hai quyết định đã chốt

| # | Vấn đề | Quyết định | Lý do / hệ quả |
|---|---|---|---|
| Q1 | Thứ tự xây | **Hạ tầng trước, tool sau** | Xong user + hàng đợi job + sổ credit, nghiệm thu bằng `apps/demo` (0 đồng), rồi mới port tool thật. Mỗi tool sau đó chỉ cần viết phần xử lý. |
| Q2 | Kho dữ liệu | **PostgreSQL ngay từ đầu** | Đổi lại: thêm một dịch vụ phải trông và sao lưu riêng (`pg_dump`, không copy file). Được lại: **mở khoá kiến trúc nhiều worker** — điều kiện tiên quyết của Q6. |
| Q3 | Nguồn code hạ tầng | **Viết mới trong LTTSTUDIOSAPP, chỉ tham chiếu BOT GEMINI** | Học cách làm và các lỗi họ đã vá, nhưng không kéo theo JSON-store và cách đăng ký module thủ công (sẽ phá hợp đồng app đang có test bảo vệ). |
| Q4 | Cổng mạng | **Nền tảng mới ở `127.0.0.1:8100`** | BOT GEMINI giữ nguyên 8000 (đang phục vụ 13 người dùng thật). Phải sửa cổng mặc định trong `setup/*.ps1` trước khi cài. |
| Q5 | Mô hình tiền | **Credit trả trước** | Nạp tiền → credit → mỗi job **giữ chỗ trước, trừ thật sau, hoàn đủ khi lỗi**. Hợp đồng app đã thiết kế sẵn cho cách này (`credit_cost` là hàm). |
| Q6 | Kiến trúc worker | **Tiến trình riêng, cùng máy** | Hai dịch vụ Windows: `LTTWeb` (:8100) và `LTTWorker`. Nói chuyện qua bảng job trong Postgres. Job FFmpeg/GPU không làm chậm web; cập nhật web không giết job đang chạy. |
| Q7 | Đăng ký người dùng | **Tự đăng ký dùng được ngay + credit dùng thử** | **Hệ quả bắt buộc:** chống lạm dụng trở thành một phần của giai đoạn hạ tầng, không phải việc để sau. Xem Q9. |
| Q8 | Tài liệu cũ | **Chuyển vào `docs/_luutru/`, giữ nguyên nội dung** | Kèm `README.md` giải thích từng file là gì và vì sao ngừng dùng. Không xoá — thư mục này **chưa có git**, xoá là mất vĩnh viễn. |
| Q9 | Chống lạm dụng đăng ký | **Xác thực email + chặn tên miền mail rác + giới hạn số tài khoản mới trên mỗi IP mỗi ngày** | Credit dùng thử chỉ được cấp **sau khi xác thực email**. Cần dựng đường gửi mail (SMTP hoặc dịch vụ gửi mail). |
| Q10 | App socialbot (FB/TikTok) | **Đóng băng** | Giữ chạy trong danh sách app, không sửa, không tối ưu. Giữ luôn `core/` (15.489 dòng) vì ~700 test đang dựa vào các phần dùng chung. |
| Q11 | Tool thật đầu tiên | **`thumbnail_api`** | API thuần, ~5-15 giây, kết quả ảnh vài MB. Không đụng trần 100 MB, không đụng trần 100 giây → chứng minh được đủ chuỗi user → job → credit → tải về mà **chưa cần object storage**. |
| Q12 | Tên gọi hai hệ thống | **Không đổi tên** — phân biệt bằng đường dẫn | Quy ước bắt buộc để bù lại: trong mọi tài liệu **luôn viết đủ đường dẫn** (`D:\BOT GEMINI` hoặc `D:\LTTSTUDIOSAPP`), không bao giờ chỉ viết "LTT AI Studio" trống không. |

---

## 2. Ràng buộc bất biến

Những điều dưới đây **không được vi phạm**, kể cả khi tiện tay:

1. **`D:\BOT GEMINI` chỉ đọc.** Không sửa, không tạo, không xoá, không chạy
   script ghi file bên đó. Nó đang phục vụ 13 người dùng thật.
2. **Không import chéo** giữa hai cây mã nguồn. Muốn dùng lại thì copy sang.
3. **Thêm app = thêm một thư mục trong `apps/`.** Không sửa `platform_core/`
   hay `server/`. Nếu thấy buộc phải sửa → **dừng lại và nói rõ vì sao**; đó là
   dấu hiệu hợp đồng app còn thiếu.
4. **Job không tra được giá thì bị từ chối chạy**, không chạy miễn phí.
5. **Việc dài hơn vài giây phải đi qua hàng đợi job** — không làm đồng bộ trong
   một request. Trần 100 giây của Cloudflare là bắt buộc, không phải lựa chọn.
6. **Ghi file cấu hình phải không BOM.** `Out-File -Encoding utf8` của
   PowerShell 5.1 chèn BOM và đã từng hạ production dự án này.
7. **File `.ps1` phải thuần ASCII.**
8. **Không viết Python inline qua PowerShell** — ghi ra file `.py` rồi chạy.

---

## 3. Việc phải làm ở giai đoạn hạ tầng (chưa bắt đầu)

Thứ tự dưới đây là thứ tự phụ thuộc, không phải thứ tự ưu tiên cảm tính.

### H0 — Dọn nền trước khi xây

- [ ] `git init` + commit đầu tiên. **Hiện chưa có version control** — đây là
      rủi ro vận hành lớn nhất hiện tại, lớn hơn mọi lỗi kỹ thuật đã tìm thấy.
- [ ] `pip install -r requirements-server.txt` (thiếu `itsdangerous` → 7 module
      test không nạp được, `python -m pytest -q` đang đỏ ngay từ khâu collect).
- [ ] Sửa lỗi ranh giới đường dẫn: `TokenStore`, `content_history.db`,
      `audit_log.jsonl` … đang ghi theo thư mục làm việc chứ không theo
      `LTT_DATA_DIR` → rơi vào `app\data\` là thư mục **bị xoá mỗi lần cập nhật**.
- [ ] Chuyển cổng mặc định trong `setup/*.ps1` sang 8100 (Q4).
- [ ] Dọn tài liệu vào `docs/_luutru/` (Q8) + viết lại bộ tài liệu gốc cho đúng
      thực tế (xem mục 4).

### H1 — Người dùng

- [ ] Bảng `users` trong Postgres: vai trò, trạng thái, thời điểm tạo.
- [ ] Đăng ký → xác thực email → mới được cấp credit dùng thử (Q7 + Q9).
- [ ] Chặn tên miền mail dùng-một-lần; giới hạn tài khoản mới trên mỗi IP.
- [ ] Phiên đăng nhập phía máy chủ (hiện đang là cookie ký, không thu hồi được).
- [ ] Phân quyền từng app cho từng user (tham chiếu `workspace_policy.py` của
      BOT GEMINI: ENABLED / LOCKED / HIDDEN).

### H2 — Hàng đợi job

- [ ] Bảng `jobs`: trạng thái, chủ sở hữu, tham số, tiến độ, kết quả, lỗi.
- [ ] Cơ chế **giữ chỗ job** để hai worker không cùng nhặt một job.
- [ ] Dịch vụ `LTTWorker` riêng (Q6), khai báo năng lực `api`/`ffmpeg`/`gpu`.
- [ ] Retry luỹ thừa + cửa sổ chống trùng (tham chiếu `job_queue.py`).
- [ ] Đẩy tiến độ về trình duyệt (SSE hoặc polling).
- [ ] Job phải sống sót qua restart máy chủ.

### H3 — Sổ credit

- [ ] Bảng ghi thêm (append-only), **có giao dịch** — không bao giờ sửa số dư
      trực tiếp, số dư là tổng của sổ.
- [ ] Ba thao tác: **giữ chỗ** → **quyết toán** → **hoàn lại khi lỗi**.
- [ ] Chặn đường lách: nút "Tạo lại" phải qua đúng cổng kiểm tra như lần chạy
      đầu. BOT GEMINI **đã từng bị đúng lỗi này** và phải vá (xem `P0-5` trong
      `app/modules/seedance_video/api.py` của họ).
- [ ] Trang admin: cấp/thu credit tay, xem lịch sử.

### H4 — Nghiệm thu bằng `apps/demo`

- [ ] Chạy đủ chuỗi: đăng ký → xác thực → nhận credit → tạo job → worker nhận →
      xử lý → trả kết quả → trừ credit đúng → xem lịch sử.
- [ ] Thử hỏng có chủ ý: worker chết giữa chừng → credit phải được hoàn.
- [ ] Chỉ khi chuỗi này xanh mới sang H5.

### H5 — Tool thật đầu tiên

- [ ] Copy `app/modules/thumbnail_api/` từ BOT GEMINI sang (Q11) — theo đúng
      danh sách "phải mang theo" trong `docs/KHAO_SAT_BOT_GEMINI.md` mục 3.
- [ ] Dựng lại theo hợp đồng app; **không sửa** `platform_core/` hay `server/`.

---

## 4. Bộ tài liệu sau khi chuẩn hoá

Đích đến: **ai mở `docs/` ra cũng biết đọc file nào, và không có hai file nói
hai chuyện khác nhau.**

```
docs/
├── 00_BAT_DAU_TU_DAY.md      bố cục, nguyên tắc, trạng thái thật
├── QUYET_DINH_NEN_TANG.md    ★ file này — nguồn chân lý
├── KHAO_SAT_BOT_GEMINI.md    kho module nguồn + đánh giá khả thi
├── 01_CAI_DAT_MAY_CHU.md     cài đặt + Cloudflare Tunnel + cập nhật
├── 02_THEM_APP_MOI.md        hợp đồng app
├── 03_VAN_HANH.md            sao lưu, rollback, xử lý sự cố
├── NHAT_KY.md                nhật ký từng phiên (thay PROJECT_MEMORY.md)
└── _luutru/                  tài liệu đã ngừng dùng + README giải thích
```

### Sáu chỗ tài liệu hiện đang SAI so với thực tế — phải sửa khi viết lại

| # | Tài liệu nói | Thực tế đo được 2026-07-31 |
|---|---|---|
| 1 | `AGENTS.md` — "desktop CustomTkinter vẫn là đường production, không được xoá" | `gui/` và `main.py` **đã bị xoá** |
| 2 | `PROJECT_MEMORY.md` đầu file — "Current product mode: Windows desktop application" | web-only |
| 3 | `PROJECT_MEMORY.md` — "entry point `main.py`, CustomTkinter" | không còn tồn tại |
| 4 | Bảng phase — P4/P5 PARTIAL (read-only) | manual publish + OAuth web **đã xong** (W3/W5) |
| 5 | "31 file test, 962 test" | 55 file, ~1.350 test |
| 6 | `CLAUDE.md` + `docs/00` + `docs/04` — vào Internet qua Cloudflare Tunnel | production **đang chạy Caddy trực tiếp**, DNS trỏ thẳng vào máy chủ, không qua Tunnel |

Nguyên nhân gốc của cả sáu: `PROJECT_MEMORY.md` dài 1.540 dòng, phần *nhật ký*
được cập nhật rất kỷ luật nhưng phần *tóm tắt trạng thái* ở đầu file thì không
ai sửa. **Người đọc mới luôn đọc phần tóm tắt trước.** Bộ tài liệu mới phải
tách hẳn "nhật ký" khỏi "trạng thái hiện tại", và trạng thái hiện tại phải ngắn
đủ để không ai ngại sửa.

---

## 5. Còn để mở — chưa cần chốt bây giờ

| Vấn đề | Khi nào phải chốt |
|---|---|
| Cổng thanh toán (nạp credit thật) | Trước khi có khách trả tiền đầu tiên |
| Object storage R2 cho file lớn | Trước tool đầu tiên của nhóm FFmpeg/GPU |
| Ngôn ngữ giao diện (Việt / song ngữ) | Trước khi có khách ngoài Việt Nam |
| Quy ước đặt slug cho từng app | Khi port tool thứ hai |
| Giấy phép Windows Server (bản Evaluation hết ~giữa 12/2026) | Trước tháng 11/2026 |
| Có làm `codex` (chạy code người dùng trên máy chủ) không | Sau cùng, hoặc không làm |

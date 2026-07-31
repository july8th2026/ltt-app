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

## 1. Quyết định đã chốt (Q1–Q25; Q14 đã thay bởi Q24)

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
| Q13 | Hàng đợi job | **procrastinate** — hàng đợi chạy trên chính PostgreSQL | Không cần Redis, không thêm dịch vụ nào. Job và dữ liệu nghiệp vụ nằm trong **cùng một giao dịch** → trừ credit và tạo job không bao giờ lệch nhau. Celery bị loại vì cần broker riêng *và* chạy kém trên Windows (prefork không hoạt động). Đổi lại: cộng đồng nhỏ hơn Celery nhiều. |
| ~~Q14~~ | ~~Đăng nhập / đăng ký~~ | ~~**fastapi-users**~~ **ĐÃ THAY bởi Q24 (2026-07-31)** | ~~Token xác thực email/reset dùng thư viện đã soi kỹ.~~ Lý do thay: khi bắt tay H1.2 mới thấy `fastapi-users` (DB adapter) **bắt buộc `sqlalchemy[asyncio]`** — async-only từ v10 — trong khi nền H1.1 vừa xây là đồng bộ và phần auth đang chạy production cũng đồng bộ. Nó còn thay luôn cơ chế session hiện có. Cái giá lớn hơn nhiều so với ước tính lúc chốt, còn lợi ích (logic token) thì `itsdangerous` đã có sẵn làm được. Xem Q24. |
| Q15 | Trang quản trị | **sqladmin** | Sinh trang xem/lọc/sửa trực tiếp từ model SQLAlchemy. Trang quản trị không phải thứ khách nhìn thấy, không đáng viết tay. Bắt buộc: chỉ vai trò admin vào được, có test chốt. |
| Q16 | ORM + di trú CSDL | **SQLAlchemy 2.0 + Alembic** | Với Postgres sẽ đổi schema hàng chục lần. Tự viết script di trú là tự tạo sự cố mất dữ liệu. Không phải tuỳ chọn. |
| Q17 | Chốt phiên bản thư viện | **Mọi thư viện phải có cận trên (`<`)** | Ngày 2026-07-31 chuyện này đã xảy ra thật: `requirements` chỉ ghi `>=` nên `pip install` kéo về Starlette 1.3 (bản major mới), làm hỏng việc liệt kê route. Ứng dụng vẫn chạy nhưng **hai lần cài cùng một mã nguồn cho ra hai môi trường khác nhau**. Nâng major phải là hành động có ý thức. |
| Q18 | Giao diện động (tiến độ job) | **HTMX** — máy chủ trả HTML, trang tự cập nhật | Không cần Node.js, không có bước build, không thêm hệ sinh thái nào lên Windows. Quan trọng hơn: **mọi logic ở lại phía máy chủ**, trình duyệt không bao giờ nhìn thấy quy tắc nghiệp vụ hay cách tính tiền. Cùng phong cách với Jinja2 đang dùng. Đổi lại: việc tương tác phức tạp (kéo thả, editor nhiều bước) sẽ gượng — lúc đó mới cân nhắc thêm Alpine.js cho riêng trang đó. |
| Q19 | Gửi email (xác thực tài khoản, đặt lại mật khẩu) | **Resend** | Không tự dựng SMTP: thư vào hộp thư hay rơi vào spam là chuyện **danh tiếng IP**, không phải chuyện code — IP dân dụng gần như chắc chắn bị Gmail chặn. Hạn mức miễn phí thừa cho nhu cầu vài chục thư/ngày. Công sức thật không nằm ở code mà ở **3 bản ghi DNS** (SPF, DKIM, DMARC). |
| Q20 | Chống đăng ký ảo | **Cloudflare Turnstile** | Miễn phí không giới hạn lượt, đa số người dùng không phải giải câu đố, không theo dõi người dùng như reCAPTCHA. **Chạy được ngay, không phụ thuộc việc DNS có nằm ở Cloudflare hay không** — nó chỉ là widget JS + một lệnh gọi API xác minh phía máy chủ. |
| Q21 | Bắt lỗi production | **Sentry**, gói miễn phí | Khi có người trả tiền, phải biết lỗi **trước khi khách gọi điện**; không ai đọc log lúc 2 giờ sáng. **Bắt buộc kèm theo: bật lọc dữ liệu cá nhân trước khi gửi đi** — email, token, nội dung job không được rời máy chủ. GlitchTip (tự host) bị hoãn vì cần Docker → trên Windows phải qua WSL2. |
| Q22 | DNS cho `app.lttstudios.com` | **Giữ DNS ở inet.vn, uỷ quyền riêng subdomain `app` sang Cloudflare** | Trang giới thiệu đang chạy ở `lttstudios.com` không bị đụng tới — rủi ro thấp nhất cho thứ đang hoạt động. **⚠️ ĐIỀU KIỆN CHƯA XÁC MINH:** Cloudflare theo truyền thống chỉ cho quản lý cả zone ở gói miễn phí; zone cấp subdomain là tính năng gói trả phí. **Phải kiểm chứng trước khi làm bất cứ việc gì khác** — xem H0.1 trong kế hoạch. Nếu gói miễn phí không hỗ trợ: quay lại chọn giữa "chuyển cả zone sang Cloudflare" và "bỏ Tunnel, mở cổng + Caddy", và ghi quyết định thay thế theo đúng giao thức đổi quyết định. |
| Q23 | Tài khoản CSDL của ứng dụng | **Role riêng `ltt_app`, không bao giờ dùng superuser `postgres`** | Một lỗ hổng SQL injection với quyền superuser đọc được **mọi** database trên máy và ghi được cả file hệ thống; với role riêng thì thiệt hại giới hạn trong đúng database của ứng dụng. Mật khẩu superuser chỉ dùng lúc cài, lưu ở `secrets/postgres-superuser.txt` để còn vào bảo trì CSDL sau này. Có test chốt. |
| Q24 | Đăng nhập / đăng ký (thay Q14) | **Tự viết trên nền đồng bộ, mượn `itsdangerous` cho token** | Giữ `server/auth/` đồng bộ đã test và đang chạy; thêm bảng `users` + đăng ký; token xác thực email/reset dùng `URLSafeTimedSerializer` (đã có sẵn, là mẫu chuẩn dùng-một-lần-có-hạn). **Vì sao không fastapi-users:** nó async-only từ v10, kéo async engine vào nền đồng bộ vừa xây ở H1.1, và thay luôn cơ chế session đang chạy production — cái giá lớn, lợi ích trùng với thứ `itsdangerous` đã làm được. Đổi lại: tự viết logic đăng ký (đều là mẫu chuẩn, viết test kỹ). |
| Q25 | Mặc định phân quyền app | **Mặc định MỞ (enabled) — admin khoá/ẩn khi cần** | Chỉ lưu bản ghi khi KHÁC mặc định; không có bản ghi = mở. Rào chắn tiền đã là credit (không credit thì không chạy job, dù thấy app), nên "mặc định mở" không gây rủi ro mất tiền. Phân quyền app dùng để **ẩn app đang xây** hoặc **app riêng cho nhóm khách**, không phải để chặn tiền. Đổi lại: thêm một app mới thì mọi user thấy ngay — đúng ý ở giai đoạn này; nếu sau cần "mặc định ẩn cho app cụ thể" thì thêm cờ trong manifest, không đổi mặc định toàn cục. Admin luôn thấy hết (ngoài bảng phân quyền). |

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

## 3. Việc phải làm

Danh sách chi tiết, tiêu chí hoàn thành và test bắt buộc của từng hạng mục nằm
ở **`docs/KE_HOACH_TRIEN_KHAI.md`**. Đây chỉ là bản đồ tổng.

```
H0 Dọn nền          ✅ XONG 2026-07-31
   └─► H1 Người dùng ──┐
       H2 Hàng đợi job ├─► H4 Nghiệm thu bằng apps/demo ─► H5 Tool thật đầu tiên
       H3 Sổ credit  ──┘
```

H1, H2, H3 phụ thuộc lẫn nhau (job cần chủ sở hữu, credit cần job) nên làm
theo thứ tự đó, nhưng cả ba phải xong mới nghiệm thu được ở H4.

---

## 4. Bộ tài liệu — đã chuẩn hoá xong 2026-07-31

Đích đến: **ai mở `docs/` ra cũng biết đọc file nào, và không có hai file nói
hai chuyện khác nhau.**

```
docs/
├── 00_BAT_DAU_TU_DAY.md      đọc gì trước, bố cục, TRẠNG THÁI THẬT
├── QUYET_DINH_NEN_TANG.md    ★ file này — nguồn chân lý
├── KE_HOACH_TRIEN_KHAI.md    việc cần làm, tiêu chí hoàn thành, tiến độ
├── NHAT_KY.md                nhật ký từng phiên
├── KHAO_SAT_BOT_GEMINI.md    kho module nguồn + đánh giá khả thi
├── 01_COPY_LEN_SERVER.md     đưa lên máy chủ, cập nhật, rollback
├── 02_LENH_CHO_CLAUDE.md     câu lệnh mẫu giao việc cho Claude
├── 03_THEM_APP_MOI.md        hợp đồng app
├── 04_CLOUDFLARE_TUNNEL.md   dựng Tunnel, xử lý sự cố mạng
├── SECURITY_CHECKLIST.md     bảng kiểm bảo mật kèm lệnh xác minh
├── DATA_RETENTION_POLICY.md  giữ dữ liệu bao lâu, ai dọn
├── tiktok-submission/        tài nguyên CODE ĐANG ĐỌC (audit_checklist)
├── lttstudios-website/       mã nguồn trang giới thiệu công khai — không phải tài liệu
└── _luutru/                  tài liệu đã ngừng dùng + README giải thích từng file
```

> Giữ nguyên tên `00`–`04` thay vì đổi số như bản phác thảo ban đầu: có test
> khoá năm tên file đó (`tests/test_61_setup_scripts.py`), và đổi tên chỉ để
> cho đẹp là tạo ra thay đổi không mang lại gì.

### Sáu chỗ tài liệu từng SAI so với thực tế — đã sửa xong

Giữ bảng này để nhớ **kiểu lỗi**, không phải để nhớ sáu lỗi cụ thể.

| # | Tài liệu từng nói | Thực tế | Đã xử lý |
|---|---|---|---|
| 1 | `AGENTS.md` — "desktop CustomTkinter vẫn là đường production, không được xoá" | `gui/` và `main.py` đã bị xoá | ✅ viết lại `AGENTS.md` |
| 2 | `PROJECT_MEMORY.md` — "Current product mode: Windows desktop application" | web-only | ✅ chuyển vào `_luutru/` |
| 3 | `PROJECT_MEMORY.md` — "entry point `main.py`, CustomTkinter" | không còn tồn tại | ✅ như trên |
| 4 | Bảng phase — P4/P5 PARTIAL (read-only) | manual publish + OAuth web đã xong | ✅ như trên |
| 5 | "31 file test, 962 test" | 55 file, 1.424 test | ✅ `docs/00` ghi số thật |
| 6 | Cả `CLAUDE.md`, `docs/00`, `docs/04` mô tả ba hạ tầng khác nhau | — | ✅ thống nhất một hướng: Cloudflare Tunnel, cổng 8100 |

**Nguyên nhân gốc của cả sáu, và là thứ phải phòng về sau:**
`PROJECT_MEMORY.md` dài 1.540 dòng. Phần *nhật ký* được cập nhật rất kỷ luật,
nhưng phần *tóm tắt trạng thái* ở đầu file thì không ai sửa — trong khi người
đọc mới luôn đọc phần tóm tắt trước.

Cách phòng: **tách hẳn ba tầng** (quyết định / kế hoạch / nhật ký — xem
`AGENTS.md` mục 6), và giữ phần trạng thái ngắn đủ để không ai ngại sửa.

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

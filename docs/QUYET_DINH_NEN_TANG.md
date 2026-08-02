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

## 1. Quyết định đã chốt (đến Q45; Q13→Q26, Q14→Q24, Q18→Q38, Q22→Q27 đã thay)

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
| ~~Q13~~ | ~~Hàng đợi job~~ | ~~**procrastinate**~~ **ĐÃ THAY bởi Q26 (2026-07-31)** | ~~Hàng đợi trên chính Postgres, job+credit cùng giao dịch.~~ Lý do thay: khi thiết kế H2 mới thấy procrastinate giữ hàng đợi trong **bảng riêng của nó**, tách khỏi bảng `jobs` nghiệp vụ → **hai kho phải đồng bộ**; và để job+credit atomic phải cho `defer` chung transaction với SQLAlchemy (chia sẻ connection, tài liệu mỏng). Chính cái lý do chọn nó (atomic) lại **dễ hơn** khi tự quản một bảng. Xem Q26. |
| ~~Q14~~ | ~~Đăng nhập / đăng ký~~ | ~~**fastapi-users**~~ **ĐÃ THAY bởi Q24 (2026-07-31)** | ~~Token xác thực email/reset dùng thư viện đã soi kỹ.~~ Lý do thay: khi bắt tay H1.2 mới thấy `fastapi-users` (DB adapter) **bắt buộc `sqlalchemy[asyncio]`** — async-only từ v10 — trong khi nền H1.1 vừa xây là đồng bộ và phần auth đang chạy production cũng đồng bộ. Nó còn thay luôn cơ chế session hiện có. Cái giá lớn hơn nhiều so với ước tính lúc chốt, còn lợi ích (logic token) thì `itsdangerous` đã có sẵn làm được. Xem Q24. |
| Q15 | Trang quản trị | **sqladmin** | Sinh trang xem/lọc/sửa trực tiếp từ model SQLAlchemy. Trang quản trị không phải thứ khách nhìn thấy, không đáng viết tay. Bắt buộc: chỉ vai trò admin vào được, có test chốt. |
| Q16 | ORM + di trú CSDL | **SQLAlchemy 2.0 + Alembic** | Với Postgres sẽ đổi schema hàng chục lần. Tự viết script di trú là tự tạo sự cố mất dữ liệu. Không phải tuỳ chọn. |
| Q17 | Chốt phiên bản thư viện | **Mọi thư viện phải có cận trên (`<`)** | Ngày 2026-07-31 chuyện này đã xảy ra thật: `requirements` chỉ ghi `>=` nên `pip install` kéo về Starlette 1.3 (bản major mới), làm hỏng việc liệt kê route. Ứng dụng vẫn chạy nhưng **hai lần cài cùng một mã nguồn cho ra hai môi trường khác nhau**. Nâng major phải là hành động có ý thức. |
| ~~Q18~~ | ~~Giao diện động (tiến độ job)~~ | ~~**HTMX**, không Node.js/build~~ **ĐÃ THAY bởi Q38 (2026-08-02)** | HTMX vẫn đúng cho form/progress thông thường, nhưng không đáp ứng mục tiêu mới: Canvas kéo-thả hoàn chỉnh là sản phẩm bắt buộc, không còn hoãn. Xem Q38. |
| Q19 | Gửi email (xác thực tài khoản, đặt lại mật khẩu) | **Resend** | Không tự dựng SMTP: thư vào hộp thư hay rơi vào spam là chuyện **danh tiếng IP**, không phải chuyện code — IP dân dụng gần như chắc chắn bị Gmail chặn. Hạn mức miễn phí thừa cho nhu cầu vài chục thư/ngày. Công sức thật không nằm ở code mà ở **3 bản ghi DNS** (SPF, DKIM, DMARC). |
| Q20 | Chống đăng ký ảo | **Cloudflare Turnstile** | Miễn phí không giới hạn lượt, đa số người dùng không phải giải câu đố, không theo dõi người dùng như reCAPTCHA. **Chạy được ngay, không phụ thuộc việc DNS có nằm ở Cloudflare hay không** — nó chỉ là widget JS + một lệnh gọi API xác minh phía máy chủ. |
| Q21 | Bắt lỗi production | **Sentry**, gói miễn phí | Khi có người trả tiền, phải biết lỗi **trước khi khách gọi điện**; không ai đọc log lúc 2 giờ sáng. **Bắt buộc kèm theo: bật lọc dữ liệu cá nhân trước khi gửi đi** — email, token, nội dung job không được rời máy chủ. GlitchTip (tự host) bị hoãn vì cần Docker → trên Windows phải qua WSL2. |
| ~~Q22~~ | ~~DNS cho `app.lttstudios.com`~~ | ~~**Uỷ quyền riêng subdomain `app`**~~ **ĐÃ THAY bởi Q27 (2026-07-31)** | ~~Giữ DNS ở inet.vn, chỉ uỷ quyền subdomain.~~ Lý do thay: **đã xác minh** — tài liệu chính thức Cloudflare khẳng định tạo subdomain thành **zone riêng là Enterprise-only**, gói Free/Pro/Business đều không có. Nên không uỷ quyền riêng `app` được. Xem Q27. |
| Q27 | DNS cho `app.lttstudios.com` (thay Q22) | **Chuyển cả zone `lttstudios.com` sang Cloudflare (Free); trang chủ để "DNS only", `app` để "Proxied" + Tunnel** | Đổi nameserver **không** chuyển hosting: inet.vn OnePanel vẫn chứa và phục vụ trang chủ; Cloudflare chỉ quản DNS. Bản ghi `@`/`www` để **DNS-only (mây xám)** → Cloudflare đứng ngoài, trang chủ chạy y hệt. Chỉ `app` để **Proxied (mây cam)** → Tunnel về máy chủ. Free đủ, không cần Enterprise. **Rủi ro:** đổi NS mà sót bản ghi → trang chủ/email chết; giảm bằng cách kiểm đủ trước khi đổi (DNS hiện chỉ ~3 bản ghi web, **không có MX/TXT** nên rủi ro thấp). Quy trình đầy đủ: `docs/05_LEN_MANG_CLOUDFLARE.md`. |
| Q23 | Tài khoản CSDL của ứng dụng | **Role riêng `ltt_app`, không bao giờ dùng superuser `postgres`** | Một lỗ hổng SQL injection với quyền superuser đọc được **mọi** database trên máy và ghi được cả file hệ thống; với role riêng thì thiệt hại giới hạn trong đúng database của ứng dụng. Mật khẩu superuser chỉ dùng lúc cài, lưu ở `secrets/postgres-superuser.txt` để còn vào bảo trì CSDL sau này. Có test chốt. |
| Q24 | Đăng nhập / đăng ký (thay Q14) | **Tự viết trên nền đồng bộ, mượn `itsdangerous` cho token** | Giữ `server/auth/` đồng bộ đã test và đang chạy; thêm bảng `users` + đăng ký; token xác thực email/reset dùng `URLSafeTimedSerializer` (đã có sẵn, là mẫu chuẩn dùng-một-lần-có-hạn). **Vì sao không fastapi-users:** nó async-only từ v10, kéo async engine vào nền đồng bộ vừa xây ở H1.1, và thay luôn cơ chế session đang chạy production — cái giá lớn, lợi ích trùng với thứ `itsdangerous` đã làm được. Đổi lại: tự viết logic đăng ký (đều là mẫu chuẩn, viết test kỹ). |
| Q25 | Mặc định phân quyền app | **Mặc định MỞ (enabled) — admin khoá/ẩn khi cần** | Chỉ lưu bản ghi khi KHÁC mặc định; không có bản ghi = mở. Rào chắn tiền đã là credit (không credit thì không chạy job, dù thấy app), nên "mặc định mở" không gây rủi ro mất tiền. Phân quyền app dùng để **ẩn app đang xây** hoặc **app riêng cho nhóm khách**, không phải để chặn tiền. Đổi lại: thêm một app mới thì mọi user thấy ngay — đúng ý ở giai đoạn này; nếu sau cần "mặc định ẩn cho app cụ thể" thì thêm cờ trong manifest, không đổi mặc định toàn cục. Admin luôn thấy hết (ngoài bảng phân quyền). |
| Q26 | Hàng đợi job (thay Q13) | **Tự quản một bảng `jobs` + `SELECT … FOR UPDATE SKIP LOCKED`** | Một nguồn chân lý duy nhất; job+credit cùng session cùng transaction (đúng thứ Q13 muốn, mà lại hiển nhiên). Postgres lo phần nhiều-worker-không-nhặt-trùng bằng `SKIP LOCKED`. Không thêm phụ thuộc, một hệ migration. **Đổi lại:** tự viết vòng poll của worker + retry/backoff (mẫu chuẩn ~50 dòng, có test) và tự lo job mồ côi khi worker chết giữa chừng (nhịp tim + nhặt lại). Khi nào job nền đủ nhiều loại/phức tạp để cần scheduling/lock nâng cao thì cân nhắc lại procrastinate — giao diện `JobQueue` giữ đủ hẹp để đổi được. |
| Q30 | Mô hình vận hành nền tảng (UX + định tuyến app) | **Đa-app PATH-BASED trên MỘT host: `app.lttstudios.com/<slug>`. Trang chủ `/` = catalog CÔNG KHAI (khách xem app không cần đăng nhập). SSO tự nhiên qua MỘT phiên. Đăng nhập có return-to (`?next=`). slug thường-gạch-nối.** socialbot giữ path gốc (đặc cách Q10), hiện như 1 app trong catalog; chỉ đổi `/socialbot` khi tách bán riêng (kèm đổi Redirect URI OAuth). | Vì sao path-based 1 host: mọi app chung 1 cookie phiên → **"1 tài khoản cho mọi app" MIỄN PHÍ**, không cần cookie-cha/subdomain/OIDC. Vì sao catalog công khai: khách duyệt app trước khi đăng nhập (giảm ma sát, chuẩn "app launcher" Google/MS 365). Vì sao return-to: click app khi chưa đăng nhập → đăng nhập xong về ĐÚNG app. **Rủi ro:** open-redirect qua `next` → chặn (chỉ nhận đường dẫn tương đối `/...`, từ chối `//` và `://`). Không chọn subdomain/OIDC: thừa phức tạp cho app first-party cùng nhà; giữ đường nâng cấp mở nếu sau có bên thứ ba. Kế hoạch chi tiết: H6 trong `KE_HOACH_TRIEN_KHAI.md`. |
| Q29 | Đường admin-env (thay ghi chú "gỡ" ở H1.2) | **Giữ làm break-glass, VÔ HIỆU ở production.** Từ H3-admin đã có admin thật trong CSDL (`tools/create_admin.py`) → admin chính là user role=admin trong DB. Đường admin-env (`LTT_ADMIN_USERNAME`/`LTT_ADMIN_PASSWORD_HASH`) **giữ lại code** làm đường lui khi CSDL hỏng/rỗng, nhưng ở production **xoá `LTT_ADMIN_PASSWORD_HASH`** để nó không còn đăng nhập được (auth.py: hash rỗng → từ chối). Khi cần cứu hộ, operator đặt lại hash qua env. | Vì sao không gỡ hẳn (khác kế hoạch H1.2 gốc): (a) mất đường vào khi CSDL hỏng/rỗng là rủi ro vận hành thật; (b) blast radius test lớn. Vì sao không giữ nguyên: mật khẩu admin-env tĩnh, dùng chung → yếu; vô hiệu ở production loại bỏ đăng nhập yếu mà vẫn giữ DR. Đổi lại: phải nhớ admin-env chỉ là cứu hộ, không phải đường thường. |
| Q28 | Bố trí ổ đĩa + sao lưu chống mất dữ liệu | **Bản chạy ở `C:\LTTPlatform` (ổ C = Disk 0). Nguồn/bộ cài ở `D:\LTTSTUDIOSAPP` (ổ D = Disk 1). Backup TỰ ĐỘNG state (`pg_dump -Fc` + `secrets\app.env` + `data\*.enc` + `config.json` + `audit_log`) sang `D:\LTTBackups` (ổ vật lý KHÁC) mỗi ngày, giữ 14 bản. Giai đoạn thương mại: thêm bản off-site (R2/máy khác).** | C và D là **hai ổ vật lý riêng** → một ổ hỏng hoặc cài lại Windows không mất cả hai. Không dời gì: giữ mô hình chuẩn "nguồn (D:) → cài đặt (C:)". An toàn thật đến từ **bản sao ở ổ kia**, không phải từ việc tách chỗ. Backup **bắt buộc gồm `secrets\app.env`** — mất `LTT_TOKEN_ENCRYPTION_KEY` là mất sạch token FB/TikTok đã mã hoá dù DB còn nguyên. Backup phải **tự động + định kỳ + restore thử** (backup chưa từng restore = niềm tin, không phải backup). Cùng một máy vẫn là **một điểm chết chung** (cháy/trộm/sét/ransomware) → off-site là bắt buộc khi có tiền thật. Công cụ: `deploy\windows\backup.ps1 -IncludeSecrets -BackupDir D:\LTTBackups` chạy qua Task Scheduler (`deploy\windows\5-lich-backup.ps1`). |
| Q31 | Thanh toán / nạp credit (H9) | **Cổng PayOS (VietQR + webhook có chữ ký), kiến trúc AGNOSTIC (đăng ký cổng, đổi/thêm cổng không sửa app). Tỉ giá 1 credit = 100đ (100.000đ = 1.000 credit). Gói nạp có BONUS theo %, admin sửa được. MỌI tiền vào đều qua `credit.nap` (sổ credit H3), không có đường tắt.** | Vì sao PayOS: cổng VN, tạo link/QR theo đơn, webhook khớp 1-1, onboarding nhẹ (dùng được tài khoản cá nhân/hộ KD), phí thấp — hợp giai đoạn đầu. Vì sao agnostic: sau muốn thêm VNPAY/MoMo chỉ viết adapter, không đụng nghiệp vụ (giống Provider Registry ở H8). Vì sao mọi tiền qua sổ credit: một nguồn chân lý về số dư, idempotent, kiểm toán được. Credential cổng để ở `secrets\app.env` (`LTT_PAYOS_*`), vắng thì adapter tắt mềm (dev/test chạy được). Đơn hàng idempotent: đã trả rồi thì webhook lặp không cộng credit hai lần. |
| Q38 | Kiến trúc giao diện động (thay Q18) | **Hybrid.** Jinja + HTMX tiếp tục cho trang/form/progress thông thường. Riêng LTT Agent Canvas dùng **React + TypeScript + `@xyflow/react`**, build bằng **Vite** thành asset tĩnh do FastAPI phục vụ. Node.js chỉ là công cụ dev/build, **không có Node runtime/SSR/Next.js trên production**. Mọi validation, giá, quyền, credit và execution vẫn ở server. | Người dùng chốt Canvas là sản phẩm bắt buộc, không hoãn. React Flow cung cấp sẵn node editor/drag/zoom/pan và MIT; Vite tạo bundle static nên cô lập độ phức tạp front-end mà không tạo server thứ hai. Đổi lại: thêm lockfile, bước build/release, frontend test và CSP/static cache contract. |
| Q39 | Phạm vi LTT Agent AI | **Xây hoàn chỉnh trong một lộ trình: Agent + Canvas + toàn bộ 7 tool job-based ảnh/text/video/GPU. Không cắt v1 chỉ còn ảnh/text.** Canvas là một cách soạn/hiển thị Plan; executor server-side là cơ chế chạy duy nhất. `chataistudio` SSE/sidecar không bị ép thành ToolSpec v1; `socialbot` vẫn đóng băng. | Người dùng chọn sản phẩm đầy đủ và chấp nhận thời gian/rủi ro cao hơn. Giữ một nguồn chân lý Plan/ToolSpec tránh Canvas trở thành runtime thứ hai; bao gồm video/GPU buộc kiểm R2, capability worker, resume, provider idempotency và E2E thật. |
| Q40 | Kiến trúc Agent | **PA-1+: planner sinh/sửa Plan hữu hạn; validator tất định; executor là phần duy nhất được lặp và chỉ lặp trong `max_retry` đã báo giá.** Không có vòng agent tự trị vô hạn và không tạo queue/runtime thứ hai. | Tận dụng hàng đợi PostgreSQL, worker, credit và app contract đã có; giữ hành vi có thể kiểm thử, resume và giải trình chi phí. |
| Q41 | Hợp đồng công cụ cho Agent | **Mở rộng additive `AppManifest.tools: tuple = ()` bằng `ToolSpec` immutable.** Nền tảng discover metadata động, không hardcode slug; app cũ không khai tool tiếp tục chạy nguyên. | Agent cần schema vào/ra và khả năng kiểm chứng, nhưng không được phá hợp đồng app hiện hành. ToolSpec chỉ mô tả job đã có, không thay handler hay tạo runtime mới. |
| Q42 | Tiền và cổng duyệt Agent | **Plan phải có báo giá trần; chưa duyệt không giữ chỗ/ghi bút toán credit và tuyệt đối không chạy tool. Khi duyệt, giữ chỗ toàn bộ trần trong cùng transaction với run; quyết toán theo chi phí thật, hoàn phần dư.** Chi phí provider của lượt lập plan trước duyệt do nền tảng hấp thụ; chỉ được tính vào giá sau khi người dùng duyệt, kèm rate-limit để chống lạm dụng. | Không thể vừa cho khách xem Plan/báo giá trước duyệt vừa tránh hoàn toàn chi phí provider ở phía nền tảng. Quy tắc này giữ lời hứa “không trừ credit trước duyệt”, đồng thời làm rõ ai chịu chi phí plan bị bỏ. |
| Q43 | Ranh giới tái sử dụng cho Agent | **Internal-first:** dùng LTTSTUDIOSAPP L1/L2/L3 trước; chỉ tham chiếu/copy L1/L2 còn thiếu từ nguồn ngoài vào repo, không import chéo và không copy runtime/GUI/bí mật. `D:\BOT GEMINI` vẫn chỉ đọc. | Kho hiện tại đã có registry, jobs, credit, provider, prompt fragments, storage/R2, media/GPU và app handlers. Xây lại các phần này sẽ tạo hai nguồn chân lý và tăng rủi ro vận hành. |
| Q44 | Rollout tạo run LTT Agent | **Một cờ bốn mức** `LTT_AGENT_CANVAS_RUN_ROLLOUT=off/admin/allowlist/public`; production mặc định `off`, giá trị sai cũng về `off`. `allowlist` dùng ID tài khoản trong `LTT_AGENT_CANVAS_RUN_USER_IDS`; admin luôn qua ở mức `admin`/`allowlist`. Cờ boolean cũ chỉ giữ tương thích. | Cờ bật/tắt cũ không thể thực hiện P13 theo nấc và có nguy cơ mở cho mọi user ngay sau deploy. Bốn mức cho phép migration feature-off, canary admin, nhóm nội bộ rồi public mà không đổi binary; rollback tức thời về `off`. |
| Q45 | Thiết kế lại app từ ảnh tham khảo | **Dùng pipeline UI-RD R0–R10 và gate G0–G7 trong `docs/QUY_TRINH_THIET_KE_LAI_GIAO_DIEN_APP.md`. Ảnh là đích thị giác + nguồn giả thuyết, không thay contract nghiệp vụ. Tính năng trong ảnh chỉ được đưa vào sau ma trận KEEP/RESTYLE/EXTEND/BUILD/REJECT/DECORATIVE/DEFER và phải có logic/test thật.** | Ảnh tĩnh không thể hiện ownership, credit, failure hay backend. Quy trình cho phép bám sát bố cục mà không tạo nút giả, xây trùng năng lực sẵn có hoặc phá ranh giới nền tảng; phát hiện mới được chuyển thành regression/quy tắc có bằng chứng. |

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

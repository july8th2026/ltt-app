# LTT NEXUS — Forensic audit nền tảng hiện tại

> Lập 2026-08-17, theo `00_MASTER_ORCHESTRATOR.md` + prompt `01`/`02` của
> `LTT_NEXUS_CLAUDE_BUILD_PACK_V2_ADAPTIVE`.
>
> File này ghi **nền tảng đang có gì** và **Nexus va vào đâu**. Nó không thiết
> kế target — thiết kế nằm ở `EXECUTION_PLAN.md`, và chỉ được chốt sau khi chủ
> sản phẩm trả lời ba câu hỏi ở mục 6.
>
> Nguồn chân lý vẫn là `docs/QUYET_DINH_NEN_TANG.md`. File này đứng dưới nó.

---

## 0. Nexus là gì, theo pack

Chuỗi end-to-end mà pack đặt ra (mục *Definition of success*):

```
Tài khoản LTT → quyền dùng sản phẩm → danh tính thiết bị tin cậy → điều khiển
từ mobile/controller → phiên điều khiển từ xa có uỷ quyền → máy Windows đầu kia
→ truyền trực tiếp hoặc qua relay → thu hồi / kiểm toán / cập nhật / vận hành
```

Nói ngắn: **sản phẩm điều khiển máy tính từ xa + quản lý thiết bị**, bán cho
khách của LTT Studios.

Đây **không cùng loại** với 15 app đang có trong `apps/`. Mọi app hiện tại là
*người dùng bấm nút → job chạy trên máy chủ LTT → trả file về*. Nexus là *hai
thiết bị của khách nói chuyện với nhau, máy chủ LTT chỉ môi giới*. Khác biệt đó
là nguồn của cả ba xung đột ở mục 4.

---

## 1. Nền tảng hiện tại — sự thật đo được

Đo ngày 2026-08-17 trên nhánh `public-api-v2`, cây làm việc sạch, commit
`057789f`.

| Hạng mục | Thực tế | Bằng chứng |
|---|---|---|
| Runtime | Python 3.13.12 | `python --version` |
| Web | FastAPI `>=0.141.1,<1.0` trên Starlette 1.3, uvicorn | `requirements-server.txt` |
| CSDL | PostgreSQL, SQLAlchemy 2.0 + Alembic, **41 revision** | `alembic/versions/` |
| Hàng đợi | Bảng `jobs` tự quản + `FOR UPDATE SKIP LOCKED` (Q26) | `platform_core/jobs.py` |
| Worker | Tiến trình riêng (`LTTWorker`), đội hình khai bằng `LTT_WORKER_POOLS` (H36) | `platform_core/job_runner.py` |
| Tiền | Sổ credit giữ-chỗ → quyết toán → hoàn (Q5), trần thu = phần đã hold (Q84) | `platform_core/credit.py` |
| Đăng nhập | Tự viết, đồng bộ, cookie phiên, bảng `sessions` băm token (Q24) | `server/auth/` |
| Phân quyền app | Mặc định mở, chỉ lưu bản ghi khi khác mặc định (Q25) | `platform_core/app_access.py` |
| Object storage | R2 qua boto3, `Storage.url_for()` presigned (H10) | `platform_core/storage.py` |
| Vòng đời file tải lên | `UploadSession` staging → promote sau khi hold credit (Q85/Q89) | `platform_core/upload_sessions.py` |
| Credential máy-gọi-máy | Public API `/api/v1`, key băm + pepper, scope, sandbox mode (Q92) | `platform_core/public_api/` |
| Admin | sqladmin + tài khoản admin trong CSDL (Q15/Q29) | `server/admin.py` |
| Vào Internet | **Chỉ** Cloudflare Tunnel, cổng 8100 loopback, không mở cổng, không IP tĩnh | `CLAUDE.md`, `cloudflare/config.yml.example` |
| Máy chủ | Windows, hai dịch vụ NSSM `LTTWeb` + `LTTWorker`, cài ở `C:\LTTPlatform` | `setup/`, `deploy/windows/` |
| Test | 234 file trong `tests/`, cổng duy nhất là `python tools\gate.py` | `tests/`, `tools/gate.py` |
| Bảng CSDL lõi | `users, sessions, app_access, app_projects, jobs, job_events, upload_sessions, credit_entries, api_keys, payment_orders, gpu_leases, singleton_leases`, … | `platform_core/models.py` |

**Không có bất kỳ khái niệm nào về *thiết bị*.** Không bảng `devices`, không
enrollment, không presence, không session broker. Grep `nexus` trong repo: 0 kết
quả. Đây là greenfield hoàn toàn về mặt domain.

---

## 2. Cái gì tái dùng được — và tái dùng ở mức nào

Pack yêu cầu ưu tiên tái dùng pattern sẵn có. Đây là bản đồ thật:

| Nexus cần | Nền tảng đã có | Mức tái dùng |
|---|---|---|
| Tài khoản, đăng nhập, phiên web | `server/auth/`, bảng `users`/`sessions` | **Dùng nguyên**, không sửa |
| Quyền dùng sản phẩm (entitlement) | `app_access` (Q25) + sổ credit (Q5) | **Dùng nguyên** cho quyền *thấy app*; thuê bao theo tháng thì chưa có — xem mục 3 |
| Thanh toán | PayOS agnostic + gói bonus (Q31) | **Dùng nguyên** cho nạp credit |
| Credential cho tiến trình không phải browser | Hai mẫu đã chạy: `apps/upscalevideo/watch_auth.py` (token bearer băm, phạm vi hẹp, 90 ngày) và `platform_core/public_api/keys.py` (key + pepper + scope + mode) | **Mẫu để chép cách làm**, không dùng lại nguyên — xem mục 3 |
| Kiểm quyền theo chủ sở hữu | `platform_core/public_api/principal.py` — 401/403/404 đã suy nghĩ kỹ, ownership lấy từ credential chứ không từ tham số | **Dùng nguyên tư duy**, có thể dùng lại code |
| Việc nền chạy trên nhiều tiến trình | `platform_core/leases.py` (`SingletonLease`, H36) | **Dùng nguyên** — mọi vòng dọn/cảnh báo của Nexus phải nằm sau lease |
| Job dài | Bảng `jobs` + worker (Q26) | **Dùng nguyên** cho việc *bất đồng bộ* (build installer, gửi lệnh, thu hồi); **KHÔNG dùng** cho phiên điều khiển thời gian thực |
| Kiểm toán | `job_events`, `nhat_ky_admin`, `security_log` của public API | **Dùng nguyên** làm mẫu; Nexus cần bảng sự kiện riêng |
| Cập nhật có ký | Chưa có gì | **Gap thật** |
| Giao diện khách | LTT Carbon Red + hợp đồng bề rộng trang (Q52/Q61) | **Dùng nguyên** |

Điểm quan trọng: **`apps/upscalevideo/watch_agent.py` (148 dòng) là tiền lệ đã
chạy production của "một tiến trình cục bộ trên máy khách, cầm token phạm vi
hẹp, gọi ngược về nền tảng"**. Nó chứng minh mẫu này hợp với kiến trúc hiện
tại. Nhưng nó cắm token vào bảng `sessions` chung với cờ `user_agent` — mẹo đó
đủ cho một agent copy file, **không đủ** cho danh tính thiết bị (không có khoá
riêng, không có thu hồi theo thiết bị, không chống nhân bản).

---

## 3. Gap thật — thứ nền tảng chưa có

| # | Gap | Vì sao không tránh được |
|---|---|---|
| G1 | **Danh tính thiết bị** (`devices`): khoá công khai của máy, fingerprint, chủ sở hữu, trạng thái tin cậy, thu hồi | Không thể lấy `user_id` làm danh tính: một khách có N máy, và mất một máy phải thu hồi đúng máy đó |
| G2 | **Enrollment + vòng đời khoá**: ghép máy vào tài khoản, sinh khoá trên máy, không bao giờ gửi khoá riêng lên server | Invariant #2 của pack, và Q23 (nguyên tắc quyền tối thiểu) |
| G3 | **Presence**: máy nào đang online, cập nhật vài giây một lần | Bảng `jobs` không phải kênh presence; poll DB mỗi 2 giây × N máy là sai công cụ |
| G4 | **Session broker**: cấp vé ngắn hạn cho một phiên điều khiển, ghi ai điều khiển máy nào lúc nào | Đây là chỗ *duy nhất* server được phép quyết định uỷ quyền (invariant #3) |
| G5 | **Đường truyền của phiên** (direct/relay) | Xem mục 4.1 — đây là blocker lớn nhất |
| G6 | **Sản phẩm endpoint Windows** (dịch vụ + UI + installer + updater có ký) | Chưa có bất kỳ sản phẩm cài trên máy khách nào ngoài 33 dòng `install_watch_agent.ps1` |
| G7 | **Ứng dụng mobile** | Repo chưa có một dòng code mobile nào |
| G8 | **Thuê bao theo tháng** | Sổ credit là *trả theo lượt dùng*. Remote desktop bán theo lượt là mô hình lạ; theo tháng thì cần đăng ký định kỳ, gia hạn, ân hạn — Q53 đã cố ý hoãn `recurring auto-charge` |

---

## 4. Ba xung đột cứng — phải giải trước khi viết dòng code nào

### 4.1 Mạng: Cloudflare Tunnel **không** chở được phiên điều khiển

Sự thật đã ghi trong `CLAUDE.md` và Q ràng buộc bất biến #5:

| Giới hạn Tunnel | Giá trị | Hệ quả với Nexus |
|---|---|---|
| Chờ phản hồi | 100 giây | Một phiên remote kéo dài hàng chục phút → 524 |
| Upload mỗi request | 100 MB | Không liên quan trực tiếp, nhưng cho thấy đường này không thiết kế cho stream |
| Serve video lớn ngoài Cloudflare | hạn chế ToS | Stream màn hình qua `app.lttstudios.com` là **vi phạm ToS** |

Và điều kiện gốc của máy chủ hiện tại: **không mở cổng, không có IP tĩnh** —
đó chính là lý do Tunnel được chọn ngay từ đầu.

Trong khi đó rendezvous/relay của bất kỳ engine remote nào cũng cần **cổng công
khai tiếp nhận được từ Internet** (RustDesk: TCP 21115–21119 + UDP 21116).

→ **Nexus không thể chạy hết trên hạ tầng hiện tại.** Bắt buộc có một máy chủ
thứ hai có IP công khai (VPS). Control plane (`app.lttstudios.com`) giữ vai trò
tài khoản/tiền/uỷ quyền; data plane (relay) là hạ tầng **tách hẳn**. Đây đúng
là invariant #5 của pack, và nó là một khoản **chi phí vận hành mới hằng tháng**,
không phải chi tiết kỹ thuật.

Độ tin cậy: **HIGH** — cả ba giới hạn đều đã ghi trong tài liệu nội bộ và một
trong số đó (100s) đã được nêu là "bắt buộc, không phải lựa chọn".

### 4.2 Hợp đồng app: Nexus không vừa `apps/<slug>`

`AGENTS.md` mục 2.3 và ràng buộc bất biến #3: *thêm app = thêm một thư mục
trong `apps/`, không sửa `platform_core/` hay `server/`; nếu buộc phải sửa thì
**dừng lại và nói rõ vì sao***.

Đây chính là lúc phải dừng lại và nói rõ. Nexus cần:

- bảng `devices` + `device_sessions` ở tầng nền tảng (app được có bảng riêng,
  nhưng danh tính thiết bị không thuộc về một app — nó thuộc về tài khoản);
- cấp phát credential cho tiến trình bên ngoài (`AGENTS.md` 8.4: app không được
  cấp credential toàn hệ thống);
- một bề mặt HTTP **không nằm dưới `route_prefix` của app** để máy endpoint và
  relay gọi vào (giống hệt lý do Public API phải là adapter layer);
- biết về một hạ tầng thứ hai (relay), thứ mà không app nào được biết.

→ Tiền lệ đúng đã có: **Q92 (Public API)**. Nó cũng không vừa hợp đồng app, và
cách xử lý là *bổ sung công khai vào bảng quyết định* chứ không đi vòng. Nexus
phải đi cùng đường: **một dòng quyết định mới (Q93)** định nghĩa Nexus là
platform capability, domain ở `platform_core/nexus/`, HTTP ở `server/nexus/`,
và `apps/nexus/` chỉ là bề mặt khách hàng (danh sách máy, nút kết nối).

Độ tin cậy: **HIGH**.

### 4.3 Giấy phép: engine remote OSS đều là copyleft mạnh

Đã kiểm chứng ngày 2026-08-17 trực tiếp trên repo nguồn:

| Thành phần | Giấy phép | Nguồn |
|---|---|---|
| `rustdesk/rustdesk` (client) | **AGPL-3.0** | github.com/rustdesk/rustdesk |
| `rustdesk/rustdesk-server` (hbbs/hbbr, bản OSS) | **AGPL-3.0** | github.com/rustdesk/rustdesk-server |
| RustDesk Server Pro | thương mại, trả phí, license riêng | cùng repo, mục pricing |

AGPL-3.0 là copyleft **mạnh nhất trong nhóm phổ biến**: nó kích hoạt nghĩa vụ
mở nguồn ngay cả khi phần mềm chỉ được *cung cấp qua mạng*, không cần phân phối
binary. Với một sản phẩm thương mại đóng, đây là quyết định pháp lý thật, không
phải chi tiết kỹ thuật. Pack cũng đặt nó thành invariant #6.

Ba đường đi, không có đường nào miễn phí:

| Đường | Được | Mất |
|---|---|---|
| **A. Dùng RustDesk AGPL, giữ ranh giới tiến trình sạch** | Nhanh nhất tới sản phẩm chạy được; engine đã trưởng thành | Ranh giới "tiến trình riêng đủ để tránh lây AGPL hay không" là câu hỏi **luật sư**, không phải câu hỏi kỹ thuật. Rủi ro phải mở nguồn phần LTT nếu ranh giới bị đánh giá sai |
| **B. Mua license thương mại** (RustDesk Server Pro và/hoặc thoả thuận riêng cho client) | Xoá rủi ro AGPL, có hỗ trợ | Chi phí định kỳ; vẫn phải xác minh phạm vi license phủ tới đâu (server Pro không tự động cấp quyền đóng nguồn cho client AGPL) |
| **C. Chọn engine giấy phép dễ hơn** — MeshCentral (Apache-2.0), Apache Guacamole (Apache-2.0), hoặc tự viết trên WebRTC | Không vướng copyleft | Guacamole cần RDP/VNC bật sẵn ở đầu kia (khác mô hình "cài agent"); MeshCentral mạnh về quản lý thiết bị nhưng chất lượng điều khiển màn hình thua RustDesk; tự viết = tăng nhiều tháng |

Độ tin cậy giấy phép: **HIGH** (đã fetch trực tiếp). Độ tin cậy đánh giá pháp
lý về ranh giới AGPL: **LOW** — cần luật sư, tôi không thể kết luận thay.

---

## 5. Rủi ro về thời điểm — không thuộc kỹ thuật Nexus nhưng chặn thật

Nhánh hiện tại là `public-api-v2`, **chưa deploy**. Theo `CLAUDE.md`:

- H35/H36 code xong nhưng còn **4 việc chứng minh chưa làm** (H36.9–12);
- `test_214` (bằng chứng đa tiến trình) **chưa nằm trong gate**, phải chạy tay;
- điều kiện nặng nhất trước khi deploy: **sao lưu `LTT_API_KEY_PEPPER` tách khỏi
  CSDL** — mất pepper là mất toàn bộ khoá của khách, không khôi phục được.

Mở một chương trình mới cỡ Nexus trong khi một nhánh chưa deploy đang treo là
cách chắc chắn để cả hai cùng chậm. Khuyến nghị ở `EXECUTION_PLAN.md` mục 1.

---

## 6. Assumption và mức tin cậy

| # | Assumption | Tin cậy | Cách kiểm chứng |
|---|---|---|---|
| A1 | Nexus bán cho **khách bên ngoài**, không phải công cụ nội bộ để LTT hỗ trợ máy khách | **LOW** | Chủ sản phẩm trả lời |
| A2 | Máy được điều khiển là **Windows**; máy điều khiển gồm cả mobile | **MEDIUM** | Pack nói vậy (prompt 09/10/23–28) |
| A3 | Chưa có VPS/IP công khai nào sẵn sàng cho relay | **MEDIUM** | Memory ghi "server cũ Vultr" trong danh sách dọn dẹp — cần xác nhận còn hay đã huỷ |
| A4 | Mô hình tiền là **thuê bao tháng**, không phải credit theo lượt | **LOW** | Chủ sản phẩm trả lời; ảnh hưởng trực tiếp G8 |
| A5 | Nền tảng chấp nhận thêm một dòng quyết định Q93 cho Nexus | **MEDIUM** | Tiền lệ Q92 đã làm đúng như vậy |
| A6 | Ranh giới tiến trình đủ để dùng RustDesk AGPL trong sản phẩm đóng | **LOW** | **Luật sư.** Không được tự kết luận |

---

## 7. Kết luận

**Status: PASS-WITH-RISK** (theo thang của pack).

Phần PASS: nền tảng đã được đo đủ để không phải đoán kiến trúc. Tài khoản, tiền,
job, storage, credential máy-gọi-máy, lease đa tiến trình, gate test — tất cả
đều dùng lại được, và có sẵn một tiền lệ đúng (Q92) cho việc thêm một capability
không vừa hợp đồng app.

Phần RISK, và là lý do chưa thể IMPLEMENT: **ba xung đột ở mục 4 đều cần quyết
định của chủ sản phẩm, không phải của kỹ thuật.** Chọn sai đường giấy phép hoặc
sai mô hình hạ tầng ở bước này thì hàng tháng công sức sau đó phải làm lại.

Bước kế tiếp: `EXECUTION_PLAN.md`.

# Public API — sẵn sàng phát hành, bản chốt cuối

Ngày **2026-08-15**. Nhánh `public-api-v2`. Đây là văn bản duy nhất được phép
đưa ra kết luận sẵn sàng, và kết luận nằm ở §12.

**Pack này không deploy.** Deploy là lệnh riêng của chủ sản phẩm. Mọi phép đo
dưới đây chạy **trong tiến trình**, trên SQLite tạm, không qua Cloudflare,
không tiêu credit thật, không gọi nhà cung cấp nào.

---

## 1. Kiến trúc

Một sub-app FastAPI gắn tại `/api/v1`, **24 route đóng băng** trong
`server/api/inventory.py`. Route thật ↔ inventory ↔ OpenAPI được so **hai
chiều** (`test_178::test_mounted_routes_match_the_declared_inventory_exactly` và
`::test_public_openapi_lists_only_declared_public_routes`, cộng
`test_192::test_inventory_has_no_undeclared_route`): thêm một route mà quên khai
là test đỏ, và khai một route không tồn tại cũng đỏ.

Ba lớp, ranh giới có test canh:

- `platform_core/` — nghiệp vụ, worker, sổ credit. **Không được** import
  `server/` hay `apps/` (`test_147`).
- `server/` — HTTP, phiên đăng nhập, trang quản trị.
- `apps/` — công cụ. Nền tảng chỉ đọc `manifest.py`.

API dùng lại **đúng** bộ máy mà web đang dùng: một sổ credit, một hàng đợi job,
một kho lưu trữ, một registry. Không có engine song song — đây là ràng buộc
được nhắc lại ở mọi prompt, và nó giữ được.

## 2. Bề mặt đang mở

**5 operation**, cả năm đều `ASYNC_JOB`:

| Operation | App | Giá | Vào | Ra |
|---|---|---|---|---|
| `image.thumbnail` | thumbnail | 5/ảnh | văn bản | ảnh |
| `image.generate` | taoanh | 5/5/8/16 theo alias | văn bản + 1 ảnh tuỳ chọn | ảnh |
| `image.upscale` | upscalevideo | 2 (fast) / 4 (quality) | ảnh **bắt buộc** | ảnh |
| `text.prompt_package` | prompt_ai_ommi | theo `scene_count` | văn bản | dữ liệu |
| `story.storyboard` | prompt_ai_ommi | theo `scene_count` | văn bản | dữ liệu |

16 ToolSpec còn lại và 9 app còn lại **đóng, có lý do ghi rõ** — bảng đầy đủ ở
[`APP_API_COVERAGE_FINAL.md`](APP_API_COVERAGE_FINAL.md), máy kiểm bằng
`test_212`.

**4 alias model**, tất cả thuộc `image.generate`. Id thật của nhà cung cấp
không lọt ra bất kỳ surface nào khách đọc được — có test quét.

## 3. Cách xác thực

| Kiểu | Định dạng | Tiêu tiền được | Cấp ở đâu |
|---|---|---|---|
| Khoá thật | `ltt_sk_<key_id>_<secret>` | có | portal, có phiên đăng nhập |
| Khoá thử | `ltt_tk_<key_id>_<secret>` | **không bao giờ** | như trên |

Bí mật **không được lưu ở đâu cả** — chỉ lưu HMAC-SHA256 với pepper nằm ngoài
CSDL. Không có đường nào đọc lại một khoá, kể cả từ trang quản trị.

Quản lý khoá **không** nằm trên `/api/v1`: một khoá tự cấp khoá khác là leo
thang quyền không cần thiết cho V1.

**OAuth: hoãn, có ADR** (D1/D7). Đã kiểm: **0 dòng** `oauth`/`pkce` trong
`platform_core/public_api/` và `server/api/`, không bảng, **không endpoint dở
dang** — hoãn sạch, không để lại nửa vời.

## 4. Bằng chứng — bốn hành trình chạy thật

`tests/test_213_full_platform_release.py`, **10 test**. Viết dài và có thứ tự
một cách cố ý: mỗi bước trao thứ gì đó cho bước sau, và **chỗ trao tay là chỗ
không hệ nào nhận trách nhiệm**.

| Hành trình | Kiểm cái gì |
|---|---|
| **§B lập trình viên** | đăng nhập → 14 trang → tạo project → khoá gắn project → docs → báo giá → webhook → chạy → tải file → **quote = charge = biến động số dư** → usage → nhật ký → job hiện trong portal → delivery vào hàng đợi |
| **§C máy chủ ngoài** | xoá cookie, chỉ còn base URL + khoá: health → tools → models → upload → quote → **tạo job idempotent (gọi lại 2 lần = 1 job)** → poll → artifact → usage. Thu hồi khoá là mất quyền ngay |
| **§E người vận hành** | 12 trang admin → từ tài khoản khách tới khoá của họ → job → trace theo `request_id` → kill switch. **Trang khoá không bao giờ hiện lại khoá.** Khách chạm vào trang admin đều bị chặn |
| **§F chỗ các hệ giao nhau** | một job đi qua pricing + budget + log + trace: **năm phép đọc cùng một sự kiện phải khớp**. Cộng: provider 429 → hoàn tiền, không lộ host nhà cung cấp; webhook không nhân đôi khi worker chạy lại; trang status không rò gì |

## 5. Bằng chứng — hỗn loạn và bảo mật

Phần này phần lớn **đã có từ V2** và vẫn xanh; EXT-21 bổ sung chỗ còn trống.

| Kịch bản | Ở đâu |
|---|---|
| 839 request trùng khoá idempotency | `test_193` → **1 job, 1 hold** |
| Sập giữa hold và hàng đợi | `test_193` → sổ sạch |
| Worker chết giữa job | `test_193` → thu hồi, không quyết toán hai lần |
| Provider timeout | `test_193` → hoàn tiền, reconcile ok |
| **Provider 429** | `test_213` → hoàn tiền, **không lộ host nhà cung cấp** |
| Kho lưu trữ hỏng | `test_193` → khách không mất tiền |
| Webhook chết | `test_193` → không đổi tiền |
| **Webhook nhân đôi** | `test_213` → chạy worker lần hai không sinh event thứ hai |
| SSRF | `test_192` → chặn ở đúng chỗ duy nhất nhận URL |
| Giả mạo header IP | `test_192` → IP ghi log không đổi được |
| Đọc chéo tài khoản | `test_192`, `test_213` |
| Khoá sai / thu hồi / hết hạn | `test_180`, `test_213` |
| Trần nhịp, quota, ngân sách | `test_184`, `test_203`, `test_206` |
| Kill switch | `test_206` (36 test) |
| Lẫn sandbox/live | `test_204` |
| Stream / batch | **NOT_APPLICABLE** — không operation nào khai; registry từ chối khai mode nền tảng chưa thi hành được |

## 6. Bằng chứng — tải

Harness: `tools/public_api_load_test.py`, **8 kịch bản**. Chạy 2026-08-15,
6 giây/kịch bản, 6 worker, trong tiến trình, SQLite, một máy để bàn.

**Đây là chi phí control-plane, KHÔNG phải sức chứa production.** Không có
Cloudflare, không có mạng, không có PostgreSQL, không có GPU thật.

| Kịch bản | RPS | p50 | p95 | p99 | Ghi chú |
|---|---|---|---|---|---|
| `reads` | 146,9 | 34,9 ms | 55,2 ms | 107,5 ms | 884 request, toàn 200 |
| `creates` | 10,6 | 396,6 ms | 1.369,7 ms | 2.276,1 ms | có tính tiền, ghi hold |
| `budgeted` | 9,5 | 377,2 ms | 1.655,3 ms | 2.315,9 ms | **có ngân sách + 3 ngưỡng cảnh báo** |
| `duplicates` | 40,4 | 150,0 ms | 286,5 ms | 456,7 ms | 248 request → **1 job, 1 hold** |
| `uploads` | 22,1 | 210,1 ms | 615,2 ms | 1.019,5 ms | 72 ticket rồi trần 12-ticket-mở bật |
| `abusive` | — | 23,2 / 34,7 ms | — | — | kẻ lạm dụng ăn 250 lần 429; **khách ngoan: 0 lần 429** |
| `worker` | 8,93 job/s | admission 62,0 ms | job 102,4 ms | — | 47/47 **thành công** |
| `webhooklag` | 7,9 job/s | **lag 4,71 ms** | 10,1 ms | 17,2 ms | 50/50 delivery vào hàng đợi |

Ba điều đọc ra được:

1. **Ngân sách gần như miễn phí.** `budgeted` so `creates` chênh trong khoảng
   nhiễu. Sổ sách ngân sách + cảnh báo không phải thứ phải cân nhắc khi bật.
2. **Cách ly trần nhịp có thật.** Một khoá quay vòng ăn 429, khoá ngoan bên
   cạnh **không dính lần nào**.
3. **`creates` p99 > 2 giây** trên SQLite trong tiến trình. Với PostgreSQL thật
   con số sẽ khác, nhưng **phải đo lại trên máy chủ thật** trước khi hứa SLA —
   đo ở đây rồi đem đi hứa là hứa về máy khác.

### Hai lần harness suýt nói dối

- Kịch bản `uploads` xin ticket cho một **trường văn bản**, nên **mọi** request
  là 400: con số throughput từng báo là tốc độ của một lỗi validate.
- Kịch bản drain stub lời gọi provider nhưng **không** đặt credential mà handler
  kiểm trước — nên nó đo tốc độ job **hỏng**, một con số trông rất khoẻ.

Cả hai đã sửa, và `test_213` giờ **chốt lại**: ticket phải thật sự được cấp,
`jobs_succeeded == jobs_drained`, delivery phải thật sự vào hàng đợi. Không
chốt ngưỡng thời gian — ngưỡng chỉ là một test hay đỏ trên máy người khác.

## 7. Hợp đồng — bốn bề mặt, một nguồn

Đều nằm trong `tools/gate.py`, nên lệch là gate đỏ chứ không phải người phát
hiện:

| Bước gate | Canh cái gì |
|---|---|
| `hop dong API` | hợp đồng công khai vs baseline; đổi phải chạy `--accept` |
| `SDK khop hop dong` | 23 route được SDK Python và TypeScript phủ, 1 chỗ bỏ qua **có lý do viết ra** |
| `postman` | collection sinh từ OpenAPI trong tiến trình, không chép tay |

Cộng: OpenAPI tải về được (kèm `servers`, thiếu nó thì generator sinh client
không có base URL), `RECIPES.md`, `CHANGELOG.md`, `MIGRATION.md`, header
`Deprecation`/`Sunset` theo RFC 8594.

## 8. Dữ liệu

`platform_core/public_api/governance.py` — **42 store**, mỗi store khai lớp,
hạn giữ, ai đọc được và **vì sao**. `test_211` chốt rằng mỗi `purged_by` trỏ
tới một hàm **có thật và được worker gọi**.

- **Bằng chứng** (sổ credit, nhật ký admin, lịch sử giá, khoá) — bị **cấm** có
  hạn xoá. Nghiệm thu: già hoá CSDL 10 năm, chạy mọi vòng dọn, kiểm còn nguyên.
- **Vận hành** (nhật ký request, sự kiện bảo mật, delivery, idempotency, quan
  sát chi phí) — tự hết hạn, và nghiệm thu kiểm chúng **thật sự sạch** (một
  vòng dọn giữ lại tất cả thì chẳng dọn gì).
- **Không bao giờ lưu**: bí mật khoá, bí mật webhook, URL presigned. Có test
  quét **mọi dòng của mọi bảng**.

Bản xuất `/developers/privacy/export` dùng lại đúng hàm che của support trace —
một định nghĩa duy nhất về "thứ không được rời khỏi hệ thống", áp cả hai chiều.

## 9. Migration và cấu hình

**17 migration, một head duy nhất**: `e7f8a9b0c1d2`. Không có nhánh song song.

Biến môi trường của khu API (đặt trong `secrets/app.env`):

| Biến | Ý nghĩa | Mặc định |
|---|---|---|
| `LTT_PUBLIC_API` | bật khu API | tắt |
| `LTT_PUBLIC_API_TOOLS` | danh sách tool được publish | **rỗng = không publish gì** |
| `LTT_API_KEY_PEPPER` | pepper băm khoá, **ngoài CSDL** | bắt buộc |
| `LTT_PUBLIC_API_RPM` / `_CREATE_RPM` | trần nhịp đọc / ghi | có mặc định an toàn |

Mặc định của công tắc tool là **rỗng**, nghĩa là bật `LTT_PUBLIC_API=1` một mình
**không** mở tool nào. Đây là mặc định đúng, và nó cũng chính là thứ làm vòng
quét rò rỉ đầu tiên của EXT-20 trở nên vô nghĩa cho tới khi mở công tắc ra.

## 10. Lùi lại

| Mức | Cách |
|---|---|
| Tắt cả khu API | `LTT_PUBLIC_API=0` → web thường **không đổi gì** (có test) |
| Đóng một tool | bỏ khỏi `LTT_PUBLIC_API_TOOLS` |
| Chặn một khách / một khoá / một project | kill switch trong trang admin, có ghi lý do |
| Lùi mã nguồn | `app.previous\` trên máy chủ; migration **chỉ tiến**, và không migration nào của pack này xoá dữ liệu |

## 11. Trước khi bật cho khách trả tiền

Những việc này **không** làm được từ kho mã, nên chúng là điều kiện chứ không
phải hạng mục đã xong:

1. **Đo lại tải trên máy chủ thật**, PostgreSQL thật, qua Cloudflare. Số ở §6 là
   chi phí control-plane trên SQLite trong tiến trình.
2. **Trần Cloudflare**: upload 100 MB, chờ phản hồi 100 giây. Cả 5 operation
   hiện đều async nên không đụng trần 100 giây, nhưng phải xác nhận trên tunnel
   thật.
3. **Theo dõi và cảnh báo**: `metrics.snapshot()` đã đếm sẵn thứ đáng cảnh báo —
   `responses_5xx`, `auth_failure`, `rate_limited`, `kill_switch_refused`,
   `capacity_refused`, `webhook_failed`, và độ trễ `queue_pickup_ms`. Nối chúng
   vào chỗ nào là việc vận hành.
4. **Pepper khoá API** phải được sinh riêng cho production và **sao lưu tách
   khỏi CSDL** — mất pepper là mất toàn bộ khoá của khách.
5. **Xoay khoá provider** và xác nhận `capacity.check` thấy pool thật.

## 12. Kết luận

Ba câu hỏi của prompt, trả lời bằng bằng chứng chứ không bằng ý định:

- **100% năng lực đã phân loại?** Có. 14 app, 21 tool, 4 alias, 5 operation —
  máy kiểm hai chiều với registry.
- **100% operation đang mở đã nghiệm thu?** Có. Cả năm chạy thật từ ngoài vào,
  đủ 13 mục checklist, cộng bốn hành trình liền mạch.
- **Có gì lọt ra ngoài ý muốn?** Không. Quét với công tắc mở rộng nhất hợp lệ:
  16 tool đóng và 4 id vendor không xuất hiện ở 9 surface nào; gọi tên một tool
  đóng nhận 404.

Ba việc hoãn (**CLI, OAuth, 3 tool video**) đều có ADR, đều nói rõ điều kiện mở
lại, và **không cái nào để lại endpoint dở dang**.

### `API_PLATFORM_FULL_READY_FOR_CONTROLLED_DEPLOY`

Điều kiện của chữ **controlled**: §11 phải làm trên máy chủ thật trước khi mở
cho khách trả tiền. Đặc biệt là mục 1 và mục 4 — số đo ở §6 là số của máy này,
và một pepper không sao lưu là một sự cố chưa xảy ra.

**Pack này không deploy.**

# Phương án nâng phần thi hành lên >9/10

Nối tiếp [`AUDIT_API_2026-08-15.md`](AUDIT_API_2026-08-15.md). Bản audit chấm
nửa hợp đồng 8–9 và nửa thi hành 3–6. File này là **thiết kế** để đưa mọi hạng
mục lên trên 9, không phải danh sách việc.

Mọi lựa chọn dưới đây đều nêu **phương án bị loại và vì sao** — một thiết kế
không nói mình đã bỏ gì thì không kiểm lại được.

---

## 1. Ràng buộc định hình mọi thứ

Không phải sở thích, mà là sự thật của môi trường này:

1. **Một máy chủ Windows**, dịch vụ chạy qua NSSM, ra Internet bằng Cloudflare
   Tunnel. Không có Kubernetes, không có hạ tầng điều phối.
2. **Không thêm dịch vụ nếu không thiếu tính chất nào** (COMMON_RULES §6). Redis
   giữ hộ bộ đếm mà PostgreSQL đã giữ đúng là thêm một thứ để cài, giám sát, sao
   lưu và **mất lúc 2 giờ sáng**.
3. **PostgreSQL ở production, SQLite ở test.** Cơ chế nào chỉ chạy trên một
   trong hai là cơ chế không test được ở nơi nó quan trọng nhất.
4. **Nền tảng không được biết tên app** (`AGENTS.md` 8.4). Mọi phân lớp phải suy
   ra từ `manifest.requires`.
5. **Không sửa `apps/` để chữa lỗi nền tảng.**

---

## 2. Chẩn đoán gốc: một giả định duy nhất sai

Ba lỗi P0 trong bản audit trông như ba lỗi. Chúng là **một**:

> Toàn bộ vòng nền được viết với giả định **"chỉ có một tiến trình chạy nó"** —
> trong khi số tiến trình mặc định là số GPU.

Không ai viết giả định đó ra, nên không ai kiểm nó. `jobs.claim()` thì đúng, vì
hàng đợi job được thiết kế *có ý thức* cho nhiều worker. Mọi thứ viết sau đó —
outbox, cảnh báo, dọn dữ liệu, metrics — thừa hưởng ngầm một giả định ngược lại.

Vì vậy phương án này **không vá ba lỗi**. Nó làm hai việc:

- **đặt tên cho giả định** và biến nó thành cơ chế có thật (mục 3.1);
- **dựng cách kiểm** khiến giả định sai không sống sót lần sau (mục 4).

Nếu chỉ làm phần vá, code sẽ đúng hôm nay và mục nền thứ bảy viết sang năm sẽ
lặp lại đúng lỗi này.

---

## 3. Sáu thay đổi

### T1 — Lease singleton + vòng bảo trì chạy luồng riêng

**Vấn đề.** Mọi tiến trình worker chạy trọn vòng bảo trì. Và ngay cả khi chỉ một
tiến trình chạy, vòng bảo trì vẫn **xen giữa các job** — nên một job 5 phút làm
webhook của mọi khách khác chờ 5 phút. Con số "độ trễ webhook 4,71 ms" đo được
trước đó là **của một hàng đợi rỗng**, không phải của hệ thống đang làm việc.

**Thiết kế.**

1. Tổng quát hoá `gpu_lease` thành **lease có tên**: bảng
   `singleton_leases(name UNIQUE, holder, acquired_at, heartbeat_at)`. Giành
   bằng INSERT; `IntegrityError` nghĩa là "người khác đang giữ" — **đường chạy
   bình thường, không phải sự cố**, đúng như `gpu_lease.acquire()` đã làm. Quá
   hạn heartbeat thì thu hồi.
2. Tiến trình nào giành được lease `"maintenance"` sẽ chạy vòng bảo trì **trong
   một luồng riêng**, song song với vòng job của chính nó. Các tiến trình khác
   chỉ chạy job.
3. Luồng bảo trì tự đập nhịp. Tiến trình giữ lease chết thì lease hết hạn và
   tiến trình khác nhận trong một chu kỳ — **tự lành, không cần ai can thiệp**.

**Vì sao lease chứ không phải `pg_advisory_lock`.** Advisory lock sạch hơn trên
PostgreSQL và tự nhả khi mất kết nối, nhưng **SQLite không có** — nghĩa là đường
chạy quan trọng nhất sẽ không có test nào chạy qua nó. Lease bằng bảng chạy
giống hệt trên cả hai, và mẫu này đã được `gpu_lease` chứng minh trong production.

**Vì sao luồng chứ không phải một dịch vụ NSSM riêng.** Dịch vụ riêng là thứ
phải cài, giám sát và **có thể chết âm thầm** — webhook ngừng gửi mà không ai
biết, vì không có job nào hỏng để báo. Luồng nằm trong tiến trình đang giữ lease
thì tự lành theo cơ chế lease, và **không đổi gì trong `setup/2-cai-dat.ps1`**.
Bảo trì là I/O chờ mạng và chờ CSDL nên luồng là đúng hình dạng; job nặng gọi
CUDA giữ GIL thì đã nằm ở tiến trình riêng rồi.

**Được gì.** Bảo trì chạy đúng một lần. Webhook không còn xếp sau job dài. Không
thêm dịch vụ nào.

---

### T2 — Outbox claim đúng chuẩn của hàng đợi job

**Vấn đề.** `claim_due()` là SELECT trần, và `deliver_due()` gọi HTTP **trước
khi** ghi bất cứ gì.

**Thiết kế.** Áp đúng khuôn hàng đợi job, vì bài toán giống hệt:

| Hàng đợi job (đã đúng) | Outbox (sẽ thành) |
|---|---|
| `FOR UPDATE SKIP LOCKED` | như vậy |
| `status = running` + `worker_id` **trước** khi chạy | `status = sending` + `holder` **trước** khi gửi |
| heartbeat + `reclaim_orphans` khi worker chết | delivery kẹt `sending` quá hạn → trả về `pending` |
| `attempts` tăng đúng một lần mỗi lượt | như vậy |

Và **đổi tên**: một hàm tên `claim_due` mà không claim là thứ khiến người đọc
sau tin rằng nó an toàn.

**Vì sao vẫn làm dù T1 đã chặn.** Đây là lớp thứ hai, độc lập. T1 là **chính
sách** (ai được chạy bảo trì); T2 là **tính đúng đắn** (chạy hai lần thì sao).
Chính sách sẽ bị người tương lai chỉnh — bật lại bảo trì ở nhiều tiến trình để
gỡ lỗi, chạy tay `deliver_due` trong shell. Tính đúng đắn thì không phụ thuộc ai
nhớ điều gì. Tiền đã bị bảo vệ hai lớp như vậy rồi (quote ký số **và**
idempotency); webhook xứng đáng như thế.

**Thêm.** Trạng thái `dead` hiện được giữ lại nhưng không ai được báo. Nối vào
`notifications` (kind `webhook.dead`) để khách biết endpoint của họ đã bị bỏ —
im lặng sáu lần rồi thôi hẳn là kiểu hỏng tệ nhất cho một tích hợp.

---

### T3 — Worker phân lớp theo tài nguyên, không theo GPU

**Vấn đề.** Số worker = số GPU. Nhưng 4/5 operation đang mở khai
`requires=('api',)` — chúng **ngồi chờ mạng Gemini**, không đụng GPU. Một job
thumbnail chờ 8 giây đang chiếm trọn một slot đáng lẽ dành cho việc dùng card.

**Thiết kế.** Toàn bộ cơ chế đã có, chỉ chưa nối:

- `limits.resource_class(manifest)` đã suy ra `{gpu, ffmpeg, browser, api}` từ
  `manifest.requires`;
- `jobs.claim(db, worker_id, capabilities=...)` đã lọc theo `manifest.requires`.

Việc cần làm là truyền tham số qua ba tầng (`job_worker` → `run_forever` →
`_chay_mot_job` → `claim`) và cấu hình đội hình:

```
LTT_WORKER_POOLS = "api:8, gpu:2"
```

Mặc định giữ nguyên hành vi cũ (một pool đa năng) để không ai bị đổi ngầm.

**Vì sao không tự động suy đội hình.** Số worker `api` tối ưu phụ thuộc độ trễ
nhà cung cấp và băng thông — hai thứ code không đo được lúc khởi động. Đoán một
con số rồi gọi là "tự động" là giấu một tham số chứ không phải bỏ nó đi.

**Được gì.** Đồng thời tách khỏi số phần cứng. Job GPU không còn xếp sau một
loạt job chờ mạng, và ngược lại.

---

### T4 — Trần thời gian chạy một job

**Vấn đề.** `reclaim_orphans` chỉ bắt worker **chết** (mất heartbeat). Job
**treo** mà vẫn đập nhịp thì giữ slot vô hạn. Với pool 2 worker, hai job như vậy
là **dừng cả nền tảng**, và không ai được báo.

**Thiết kế.** `max_runtime_s` khai trong manifest theo `job_type` — cùng chỗ và
cùng kiểu với `gpu_vram_mb` đang có, nên nền tảng vẫn không biết tên app. Vòng
heartbeat kiểm thời gian đã chạy; vượt trần thì huỷ theo **đúng đường fail đang
có** (hoàn tiền, sự kiện job, webhook), với mã lỗi riêng để khách phân biệt
"quá giờ" với "nhà cung cấp hỏng".

Trần mặc định của nền tảng: khai bảo thủ theo `resource_class`, app khai lại
được. App không khai thì vẫn có trần — **không có trần mới là mặc định nguy
hiểm**.

---

### T5 — Metrics sống qua khởi động lại và cộng được nhiều tiến trình

**Vấn đề.** Bộ đếm chỉ trong tiến trình, mất khi khởi động lại, không có đường
đọc từ ngoài, và mỗi tiến trình một bản riêng.

**Thiết kế.** Hai tầng, giữ nguyên đường nóng:

1. **Đường nóng không đổi**: vẫn là tăng một số trong dict dưới khoá. Không có
   lượt ghi CSDL nào trên đường phục vụ request.
2. **Xả định kỳ**: mỗi ~60 giây, mỗi tiến trình ghi *phần tăng thêm* của mình
   vào `api_metric_samples(process, name, window_start, value)` rồi reset delta
   cục bộ. Một lượt ghi gộp mỗi tiến trình mỗi phút.
3. **Đọc thì cộng**: trang admin và một endpoint chỉ dành cho người vận hành
   `SUM` theo cửa sổ thời gian. Nhiều tiến trình cộng lại đúng vì mỗi dòng có
   `process`.
4. **Có hạn lưu trữ**: khai một store trong `governance` (14 ngày) — bảng ghi
   theo phút thì phải có người dọn, đó chính là bài học EXT-19.

**Vì sao không Prometheus.** Ràng buộc 2. Hình dạng `tên → số nguyên` này ánh xạ
thẳng sang exporter về sau **mà không phải sửa chỗ gọi** — điều kiện để đổi ý
sau này rẻ, đã ghi sẵn trong docstring của `metrics.py`.

**Vì sao không ghi thẳng mỗi request.** Nó biến mọi request thành một lượt ghi
CSDL để đếm — trả bằng độ trễ của khách cho một tiện nghi của người vận hành.

---

### T6 — Tách *bằng chứng* khỏi *nội dung*, và cho file một vòng đời

**Vấn đề.** `jobs` được xếp lớp `content` với `retention=None` (giữ vĩnh viễn),
còn file kết quả **không có store nào**. Hai lỗi, một nguyên nhân: một hàng
`jobs` chứa **cả hai thứ cùng lúc** —

- **bằng chứng**: ai, khi nào, tool gì, tính bao nhiêu credit → phải giữ mãi để
  trả lời tranh chấp hoá đơn;
- **nội dung**: prompt khách viết, payload kết quả, file sinh ra → **không có lý
  do gì để giữ mãi**, và giữ mãi là một khoản nợ về riêng tư lẫn chi phí.

Chính bảng phân loại của `governance` đã nói phải tách hai thứ này. Hàng `jobs`
thì không tách.

**Thiết kế.**

1. Giữ hàng `jobs` như **bằng chứng**, vĩnh viễn, đúng như hiện nay.
2. Sau N ngày, **xoá phần nội dung**: `params`, `result`, và **file trong
   storage**. Job vẫn còn, vẫn truy được, vẫn đối chiếu được hoá đơn — chỉ nội
   dung là hết hạn, và trạng thái đó hiện ra rõ ràng (`content_expired_at`) chứ
   không phải trường rỗng khó hiểu.
3. **Công bố cửa sổ tải về** trong hợp đồng tool. Một API sinh file mà không nói
   giữ bao lâu là để khách tự đoán, rồi trách khi đoán sai.
4. **Mở rộng bánh cóc kiểm kê để soi cả kho file**, không chỉ bảng CSDL.

**Điểm 4 là quan trọng nhất.** Nếu chỉ thêm sweep mà không sửa bánh cóc, thì
`governance` vẫn sẽ tự tin là đầy đủ trong khi nó chỉ nhìn một nửa — và lần sót
tiếp theo cũng sẽ im lặng đúng như lần này.

---

## 4. Cách chứng minh: bộ khung chạy nhiều tiến trình

**Đây là hạng mục quan trọng nhất của cả phương án**, hơn bất kỳ thay đổi nào ở
mục 3.

Cả ba lỗi P0 đều lọt qua một bộ test 3.560 bài vì **chưa từng có gì chạy hai
tiến trình worker cùng lúc trên một CSDL**. Test webhook chống trùng thì có, và
nó *đúng* — nhưng nó chạy worker tuần tự trong một tiến trình, nên nó khẳng định
một điều không ai nghi ngờ.

**Thiết kế.** `tests/test_214_multi_process_runtime.py`: đẻ N tiến trình worker
thật (không phải luồng, không phải giả lập) trên một CSDL PostgreSQL tạm, chạy
một khối lượng việc, rồi khẳng định **không thứ gì xảy ra hai lần**:

| Bất biến | Vì sao ở đây, không ở test khác |
|---|---|
| mỗi job chạy đúng một lần | `claim` đã đúng, nhưng đây là chỗ chứng minh |
| mỗi delivery gửi đúng một lần | T2; hôm nay **đỏ** |
| mỗi cảnh báo sinh đúng một lần | index dedupe không unique; hôm nay **đỏ** |
| đúng một tiến trình giữ lease bảo trì | T1 |
| sổ credit khớp sau khi chạy đồng thời | `usage.reconcile` |
| metrics cộng lại bằng tổng thực tế | T5 |
| lease bảo trì chuyển chủ khi giết tiến trình đang giữ | T1 tự lành |

Chạy trên **PostgreSQL**, vì SQLite khoá cả CSDL khi ghi và **che mất đúng những
lỗi này** — đó chính là lý do lỗi outbox trông như vô hại khi chạy thử: SQLite
đã chặn lượt ghi thứ hai, và tôi suýt đọc nó thành "có bảo vệ".

Dự án đã có sẵn đường chạy test trên PostgreSQL (`LTT_TEST_DATABASE_URL`), nên
đây là mở rộng chứ không phải hạ tầng mới.

---

## 5. Đưa các hạng mục 8 điểm lên trên 9

Bốn hạng mục đang 8 không hỏng — chúng thiếu **một tính chất cụ thể**, không
thiếu tính năng.

| Hạng mục | Đang thiếu đúng cái gì | Thay đổi |
|---|---|---|
| **Giới hạn & chính sách** (8) | Bộ đếm RPM chỉ đúng khi có **một** tiến trình web. Ràng buộc này chỉ nằm trong docstring — người mở tiến trình web thứ hai sẽ không đọc chỗ đó. | Dùng lại **lease của T1**: tiến trình web giành lease `"web"`. Không giành được thì ghi log mức lỗi và báo trên `/health/ready`. Ràng buộc ngầm thành ràng buộc **nhìn thấy được**, không tốn cơ chế mới. |
| **Bảo mật bề mặt** (8) | Chống được tấn công đã biết, nhưng **không phát hiện** bất thường. Khoá bị lộ vẫn dùng bình thường cho tới khi hết tiền. | `security_log` và `request_log` đã có đủ dữ liệu. Thêm ba tín hiệu và đưa lên trang admin: khoá dùng từ IP chưa từng thấy, chi tiêu vọt gấp N lần trung vị, chuỗi 403 do thiếu scope. Không cần bảng mới. |
| **Trải nghiệm lập trình viên** (8) | Có đủ thứ cho đường chạy thuận, thiếu cho **đường hỏng**: tiến trình khách chết giữa chừng thì làm gì. | `Retry-After` và cờ "thử lại được" trên **mọi** lỗi; một recipe *đối chiếu sau sự cố* có test (khôi phục bằng `Idempotency-Key`, đối chiếu qua `/usage`); công bố cửa sổ tải artifact (T6). |
| **Vận hành / admin** (8) | Xem được mọi thứ, nhưng không nói **phải làm gì** khi thấy. | Runbook gắn thẳng vào từng chế độ hỏng có thật trong bản audit này: webhook dồn, hàng đợi tăng, provider 429, margin âm, lease bảo trì đổi chủ liên tục. Mỗi mục: dấu hiệu → truy vấn → hành động → cách xác nhận đã hết. |

---

## 6. Điểm dự kiến sau khi làm

| Hạng mục | Nay | Sau | Nhờ |
|---|---|---|---|
| Xác thực & khoá | 9 | 9,5 | tín hiệu bất thường (mục 5) |
| Hợp đồng & phiên bản | 9 | 9 | giữ nguyên |
| Tính tiền & idempotency | 9 | 9,5 | recipe đối chiếu sau sự cố + bất biến sổ tiền trong test đa tiến trình |
| Giới hạn & chính sách | 8 | 9,5 | lease `web` |
| Bảo mật bề mặt | 8 | 9 | ba tín hiệu bất thường |
| Trải nghiệm lập trình viên | 8 | 9 | ngữ nghĩa đường hỏng + cửa sổ tải về |
| Vận hành / admin | 8 | 9,5 | runbook + metrics đọc được |
| Dữ liệu & riêng tư | 7 | 9,5 | **T6** |
| Webhook | 6 | 9,5 | **T1 + T2** + báo khi `dead` |
| Vòng đời job & hàng đợi | 5 | 9,5 | **T3 + T4** |
| Quan sát được | 4 | 9 | **T5** |
| Đa tiến trình & mở rộng | 3 | 9 | **T1 + T2 + T5 + mục 4** |

Không hạng mục nào đặt 10. Thang này để so hệ thống với **cái nó có thể là**,
và mọi hạng mục đều còn chỗ tốt hơn — cho 10 là bảo rằng không còn.

---

## 7. Thiết kế này KHÔNG giải quyết cái gì

Ghi ra để không ai đọc nhầm:

- **Không phải kiến trúc nhiều máy.** Lease, bộ đếm RPM và metrics đều đúng cho
  *nhiều tiến trình trên một máy*. Khi cần máy thứ hai: lease vẫn chạy (nó ở
  trong CSDL), nhưng RPM trong tiến trình thì phải chuyển xuống CSDL, và **đó
  mới là lúc** cân nhắc Redis — khi có tính chất thật sự thiếu.
- **Không tăng thông lượng job nặng.** T3 chia đúng chỗ nghẽn; nó không làm GPU
  chạy nhanh hơn.
- **Không thay việc đo tải trên máy chủ thật.** Mọi số hiện có là SQLite trong
  tiến trình.
- **Không mở stream/batch/OAuth/CLI.** Đều hoãn có ADR, không đổi bởi phương án
  này.

---

## 8. Thứ tự thi công

**Đợt 1 — làm bộ khung trước.** Viết `test_214` với các bất biến ở mục 4 **trước
khi** sửa gì. Ba trong số đó sẽ **đỏ**, và đó là mục đích: có một phép đo khách
quan cho "đã sửa xong", thay vì niềm tin rằng đã sửa.

**Đợt 2 — T1 + T2 + index unique cho cảnh báo.** Cùng một nguyên nhân gốc, cùng
khu code, và làm ba bất biến kia chuyển sang xanh.

**Đợt 3 — T5 rồi T3.** Metrics trước, vì sau khi chia pool thì cần đọc được số
mới biết đội hình đặt đúng chưa. Chia pool trước rồi mới đo là chỉnh mù.

**Đợt 4 — T6 và T4.** Độc lập với nhau, làm song song được.

**Đợt 5 — bốn việc nâng 8→9 ở mục 5.** Đều nhỏ và không phụ thuộc nhau.

Sau mỗi đợt: full gate. Sau đợt 2 và 3: chạy `test_214` trên **PostgreSQL**, vì
trên SQLite nó sẽ xanh vì lý do sai.

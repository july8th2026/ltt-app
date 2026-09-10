# P03 — KẾ HOẠCH CHẶN CHI PHÍ VÀ THOÁT HIỂM

> `NON_NEGOTIABLE_GATES` P04: *"không create paid GPU workload cho tới khi
> emergency path + budget ledger PASS"*. Tệp này là phần "emergency path", và nó
> phải **chạy thử được trước khi có Pod thật** — bằng dry-run.

---

## 0. Con số biện minh cho toàn bộ tệp này

```
max_workers = 1  ⇒  $2,72/giờ liên tục
$150 ÷ $2,72     =  55 giờ  =  2,3 NGÀY
```

> 🔴 **Một vòng lặp hỏng tiêu trọn ngân sách tháng trong hai ngày rưỡi.**
> Với `max_workers = 3` (mặc định của RunPod) thì là **18 tiếng**.

Đây không phải rủi ro lý thuyết: nền tảng **đã** có một lỗi đúng loại này — bản
đầu của cổng render thiếu chốt idempotency và **đốt ~100 giây GPU mỗi lần gửi
lại** (D-018). Trên card nhà đó là điện; trên GPU thuê đó là **tiền mặt**.

---

## 1. Năm lớp chặn — xếp từ ngoài vào trong

| # | Lớp | Đặt ở đâu | Chặn được gì | Không chặn được gì |
|---|---|---|---|---|
| ① | `max_workers = 1` | endpoint RunPod | nhiều worker cùng cháy — **và hỏng dữ liệu volume** (xem dưới) | một worker cháy liên tục |
| ② | `Execution timeout` | endpoint RunPod | **một job** chạy vô hạn | nhiều job nối tiếp |
| ③ | `idle timeout = 5 s` | endpoint RunPod | trả tiền cho lúc rảnh | — |
| ④ | `admission_slots = 1` | **máy A**, manifest app (Q114) | máy A nộp nhiều job song song | job nộp tuần tự |
| ⑤ | **Cầu dao ngân sách** | **máy A**, `bao_tri` của app | tiêu quá envelope | ⚠️ độ trễ một chu kỳ |

⛔ **Lớp ① còn chặn một thứ khác, mới đọc được:** *"Writing to the same volume from
multiple workers simultaneously **may cause data corruption**"*
(`docs.runpod.io/storage/network-volumes.md`). Nâng `max_workers` không chỉ là
quyết định ngân sách — nó là quyết định **toàn vẹn dữ liệu** trên volume 300 GB.

⭐ Lớp ④ và ⑤ nằm ở **máy A**, và đó là điểm mấu chốt: ba lớp đầu là cấu hình của
nhà cung cấp — ta không kiểm thử được chúng, không phiên bản hoá được chúng, và
không có phép kiểm nào giữ chúng. Hai lớp cuối là **mã của ta, có test**.

### 🔴 ⑤ Cầu dao ngân sách — **bản đầu có một lỗ chết người**

`docs.runpod.io/accounts-billing/billing.md`:

> *"If your balance stays at $0 and these charges can't be covered, the network
> volume **may eventually be terminated, and its data can't be recovered**."*
>
> *"Runpod is **not designed for long-term data storage**."*

Bản đầu của cầu dao ngắt khi **chạm envelope**. Nhưng nếu số dư về **$0** thì
**volume 220 GB model bị xoá, không khôi phục được** — nạp lại là nhiều giờ.

**Sửa: thêm SÀN CREDIT.**

```
SÀN = chi phí lưu trữ 30 ngày × 1,5      (300 GB ⇒ $21,00 × 1,5 = $31,50)

ngắt COMPUTE khi:   số dư ≤ SÀN           ← KHÔNG đợi tới $0
cảnh báo khi:       số dư ≤ SÀN × 2
```

⇒ Tiền còn lại **chỉ đủ nuôi ổ đĩa**. Mất khả năng sinh video là **phiền**; mất
220 GB model là **nhiều giờ làm lại**. Đây là đánh đổi đúng chiều.

⚠️ Và nó đổi cách đọc `D08`: **$150 không phải thứ được tiêu tới đồng cuối.**

### ⑤ Cầu dao ngân sách — thiết kế

Chạy trong `manifest.bao_tri` của `apps/lttvideo` ⇒ **dưới lease**, tức đúng một
lần trên toàn cụm dù có bao nhiêu tiến trình worker (`platform_core/leases.py`).

```
mỗi chu kỳ (đề xuất 15 phút):
    đọc chi tiêu tháng này từ COST_LEDGER
    nếu  chi tiêu ≥ 90 % envelope tháng:
        ghi cảnh báo vận hành
    nếu  chi tiêu ≥ 100 % envelope tháng:
        đặt provider `ltt_video` về không phục vụ  (fail-closed)
        job mới nhận `DangBan` → nằm hàng đợi, KHÔNG tiêu attempt, KHÔNG mất tiền khách
```

⛔ **Ngắt bằng `DangBan`, KHÔNG bằng lỗi.** Hết ngân sách là **trạng thái tạm**,
không phải hỏng. Ném lỗi sẽ tiêu lượt thử và làm job chết hẳn kèm hoàn tiền cho
một việc chưa từng chạy — đúng lớp lỗi mà `jobs.DangBan` sinh ra để chặn.

⛔ **Và tuyệt đối không dùng `api_pool.danh_dau_loi()`** để tắt. Cơ chế đó
`disable` khoá sau 5 lần và **không tự bật lại** — hết ngân sách tháng này sẽ tắt
provider **vĩnh viễn**. Đây đúng cạm bẫy Q102 đã ghi cho `ltt_image`.

---

## 2. Thoát hiểm — ba mức, thời gian tăng dần

| Mức | Làm gì | Ai làm được | Bao lâu |
|---|---|---|---|
| **1. Ngắt phía ta** | tắt provider `ltt_video` ở máy A | Claude, tự động hoặc tay | **tức thì**, job mới không đi ra |
| **2. Dừng endpoint** | `max_workers = 0` qua API RunPod | Claude (có khoá ①) | giây, job **đang chạy** vẫn chạy nốt |
| **3. Xoá endpoint** | xoá qua console/API | Claude, hoặc chủ dự án | giây |

⚠️ **Mức 2 không giết job đang chạy.** Trần thật của thiệt hại còn lại =
`Execution timeout` × số worker đang chạy. Đó là lý do thứ hai để đặt
`Execution timeout` có ý thức (§2.1 của `CLOUD_RESOURCE_PLAN.md`).

⛔ **Không mức nào xoá network volume.** Volume giữ ~200 GB model đã nạp; xoá nó
là ném đi nhiều giờ tải lại. Dừng chi tiêu **không** cần chạm volume — và tài liệu
RunPod cảnh báo hành vi xoá là chỗ dễ mất dữ liệu nhất.

---

## 3. Chạy thử **trước khi** có Pod — dry-run

`NON_NEGOTIABLE_GATES` đòi cost guard PASS **trước** workload trả tiền đầu tiên.
Ba phép thử, không cái nào cần GPU:

| Thử | Cách | Đạt khi |
|---|---|---|
| Cầu dao ngân sách | bơm một sổ giả đã tiêu 100 % envelope, chạy `bao_tri` | provider về không phục vụ; job mới nhận `DangBan`, **không** tiêu attempt, **không** chạm sổ credit |
| Đường dừng endpoint | gọi API RunPod đặt `max_workers = 0` trên một endpoint **chưa có worker** | trả 2xx, đọc lại thấy `max_workers = 0` |
| Kiểm kê mồ côi | liệt kê tài nguyên qua API, lọc tiền tố `lttvideo-` | khớp đúng danh sách trong `CLOUD_RESOURCE_PLAN.md` §1 |

Cả ba nằm dải test **700–799**. ⛔ Phép thử thứ nhất **phải chạy được không cần
mạng** — nó là mã của ta, và một chốt an toàn phụ thuộc mạng thì không phải chốt.

---

## 4. Thứ **không** có ở V1, và vì sao không cần

Pack V3 dành cả P14 cho máy trạng thái vòng đời GPU. Với serverless thì phần lớn
không còn việc (`Q121`, `NGHIEN_CUU_CLOUD_GPU.md` §2):

| Pack đòi | Vì sao V1 không cần |
|---|---|
| Máy trạng thái `OFF→PROVISIONING→…→DRAINING` | nhà cung cấp làm; ta chỉ gọi `/run` |
| Single-flight tạo Pod | **không có Pod nào để tạo** |
| Đối soát Pod mồ côi | không có Pod ⇒ không mồ côi được. Chỉ còn kiểm kê **endpoint + volume** (§3) |
| Đồng hồ nhàn rỗi tự viết | `idle timeout = 5 s` của nhà cung cấp |
| Trần thời gian phiên | `Execution timeout` của nhà cung cấp |

⭐ Cái **còn lại** của P14, và nó không nhỏ: ghi `billed_seconds` thật cho từng
job (`V-003` cần), chính sách **gộp lô**, và cầu dao ở §1⑤.

---

## 5. Sổ tay sự cố

| Triệu chứng | Nghĩ tới | Làm gì |
|---|---|---|
| Chi tiêu tăng mà không ai bấm gì | job lặp vô hạn (thiếu idempotency) | **Mức 1** ngay, rồi đọc `job_events` xem cùng `job_id` gửi mấy lần |
| Job nằm `queued` mãi, `/health` xanh | ⭐ hết A100 ở DC đã khoá volume | kiểm tồn kho DC; **không** tự đổi DC (nạp lại model + trả lưu trữ hai lần) |
| 429 liên tục | endpoint chạm `max_workers = 1` | đúng thiết kế; job đợi. Nâng `max_workers` là **quyết định ngân sách** |
| Job hỏng ngay sau khởi động nguội | model thiếu trên volume, hoặc sai DC | đối chiếu `BANG_KE.json` với `MODEL_BOM_FINAL.csv` |
| Hoá đơn không khớp sổ | ước tính của ta sai, hoặc có tài nguyên ngoài tiền tố `lttvideo-` | kiểm kê (§3), lấy **hoá đơn** làm chuẩn |
| Máy A không gọi được endpoint | khoá ③ hỏng/hết hạn | ⛔ **KHÔNG** `danh_dau_loi` nếu là 429 — 429 là **bận** |

---

## 6. Điều kiện đóng của P04 *(chép ra đây để P04 không phải tìm)*

- [ ] Giá hỏi lại **ngay lúc đó**, không dùng bảng của P03
- [ ] A100 80GB **có hàng** ở một DC thuộc 15 DC có API S3
- [ ] Volume tạo ở đúng DC đó, đặt tên `lttvideo-models-v1`
- [ ] Ghi lại **ID volume** và DC vào `COST_LEDGER.csv`
- [ ] Endpoint đặt `max_workers = 1`, `active_workers = 0`, idle 5 s
- [ ] Trả lời được: trần `Execution timeout`? khởi động nguội có tính vào đó không?
- [ ] Ba phép thử dry-run (§3) **PASS**
- [ ] Bốn loại bí mật vào đúng bốn chỗ (`CLOUD_RESOURCE_PLAN.md` §4)
- [ ] Ghi ngân sách còn lại của tháng
- [ ] ⛔ **Chưa tạo worker GPU nào**

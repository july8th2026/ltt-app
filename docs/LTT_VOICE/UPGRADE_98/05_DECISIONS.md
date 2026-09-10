# 05_DECISIONS — quyết định thiết kế, kèm căn cứ và đường lùi

Khuôn §15 STEP 4: ID · vấn đề · bằng chứng · phương án · phương án bị loại ·
thiết kế chọn · lợi ích kỳ vọng · đường lùi.

---

# QĐ-V01 — U-20: công bằng GPU giữa việc NGẮN và việc DÀI

**Trạng thái:** ĐỀ XUẤT, chờ chủ dự án chốt · 09/09/2026 · hạng mục **13, 14, 15**

## 1. Vấn đề — đo được, không suy

Bảng RTF thật (30/08, RTX 5060 Ti, `01_KHOA_UPSTREAM.md §2.2`): 3.000 ký tự
sinh hết 17,55 s. Ngoại suy tuyến tính trên chính bảng ấy:

| độ dài | giữ GPU |
|---:|---:|
| 200 ký tự | 1,2 s |
| 1.500 (`TRAN_MOI_LUOT_SINH`) | 8,8 s |
| 10.000 | 58,5 s |
| **100.000** (`TRAN_KY_TU_CONG_KHAI`) | **585 s ≈ 9,8 phút** |

`admission_slots=1` ⇒ một job giữ suất tới lúc xong. Nên:

```
job 200 ky tu dung sau mot job 100k:
    viec that     1,17 giay
    thoi gian cho 9,8 phut
    ty le         500x
```

**500 lần** là con số của quyết định này. Không phải "hơi chậm" — là một khách
gõ một câu và chờ mười phút.

## 2. Thứ ĐÃ CÓ, và vì sao nó không giải bài này

`platform_core/jobs.py:claim()` xếp:

```python
.order_by(aged_first, never_served_first, last_account_claim, Job.created_at, Job.id)
```

⇒ **đã có** aging + fair-share **theo tài khoản** + FIFO. Nhiều hơn hẳn FIFO trần.

⛔ Nhưng nó công bằng giữa **các tài khoản**, không giữa **việc ngắn và việc
dài**. Hai job của **cùng một khách** vẫn thuần FIFO. Và xếp thứ tự chỉ chạm job
**chưa bắt đầu** — job đang chạy không có điểm nhả.

## 3. Ba ràng buộc cứng phải tôn trọng

**(a) `phat_dan()` giữ suất suốt generator — CÓ LÝ DO.**
`voice_sidecar/engine.py:355`: *"Suất chạy được giữ **suốt cả generator** — nhả
sớm là để lượt thứ hai chen vào giữa lúc lượt đầu còn đang chiếm engine."*
Mọi phương án nhả-giữa-chừng phải giải thích vì sao dòng ấy hết đúng.

**(b) `Job` KHÔNG có cột `priority`.** Đếm cột lớp `Job` trong `models.py`:
không có. (Dòng `models.py:723` là của `ApiKey`, và `api_pool.py:192` đọc nó
thật.) ⇒ thêm trục ưu tiên là **đổi lược đồ + migration** trên CSDL đang chạy,
không phải "nối một cột sẵn có".

**(c) Lớp giành thật là `ExecutionLease UNIQUE(resource, slot)`.** Bộ lọc trong
`claim()` chỉ là **cơ hội**, chính docstring khai vậy. Phương án nào cũng phải
đi qua lease, không được tự dựng khoá thứ hai.

## 4. Bốn phương án

### A — nhả suất theo ĐOẠN (bản tương ứng của preemption vLLM)

vLLM (`v1/core/sched/scheduler.py:746`) dùng **một** khoá cho hai chiều:

```python
preempted_req = max(self.running, key=lambda r: (r.priority, r.arrival_time))
```

`min` chọn ai chạy, `max` chọn ai nhường. vLLM nhường được vì sinh LLM phục hồi
ở mức **token**. TTS của ta phục hồi ở mức **ĐOẠN**, và nguyên thuỷ ấy đã có
sẵn: `text_pipeline.chia_doan` chia theo ranh giới câu, `noi_dai`/`ghep_tep`
ghép lại.

| | |
|---|---|
| lợi | công bằng thật; job dài vẫn tiến; không cần card thứ hai |
| hại | **vi phạm thẳng ràng buộc (a)**; cần cột `priority` + migration; trạng thái nhả-rồi-tiếp phải bền qua restart worker; sổ sách phải chịu được một job chạy làm nhiều chặng |
| rủi ro | cao nhất trong bốn phương án — chạm cả engine, lịch, **và** sổ sách |

### B — ưu tiên việc ngắn + aging

Thêm `priority` suy từ `so_ky_tu`, cộng aging để job dài không chết đói.

| | |
|---|---|
| lợi | không đụng engine; giữ nguyên (a) |
| hại | cần migration; và **không giải bài**: nó chỉ đổi *thứ tự vào*, job dài đã chạy vẫn giữ card 9,8 phút. Job ngắn tới sau vẫn chờ |
| rủi ro | trung bình, lợi ích **thấp** — sai chỗ |

### C — hai làn admission trên MỘT card

`vieneu_gpu_nhanh` và `vieneu_gpu_dai`, chia theo `so_ky_tu`, mỗi làn 1 suất.

| | |
|---|---|
| lợi | không migration (làn khai ở `manifest`, không ở lược đồ); không đụng engine |
| hại | **hai suất trên một card** ⇒ hai lượt inference cùng lúc trên cùng GPU. VRAM chịu được (2×1,86 GB / 16 GB) nhưng phá đúng lời `manifest.py` ghi: *"MỘT GPU = MỘT VIỆC"*. Hai lượt tranh nhau làm **cả hai** chậm đi |
| rủi ro | trung bình; và nó đổi một bất biến đã ghi ra chữ |

### D — hai làn trên HAI CARD ⭐ **ĐỀ XUẤT**

`vieneu_gpu_nhanh` ghim card 0, `vieneu_gpu_dai` ghim card 1.

🔴 **Phương án này BẤT KHẢ THI cho tới hôm nay.** Hồ sơ cũ ghi GPU thứ hai lỗi
Code 43. Đo 09/09 13:42: `nvidia-smi` liệt kê **cả hai** RTX 5060 Ti 16 GB với
bộ nhớ và mức dùng thật (card 1 đang 23 %). Card đã sống ⇒ phương án mở lại.

Nền tảng **đã có sẵn** máy móc, không phải xây:

```
platform_core/gpu.py:94    visible_devices_value(uuid)  -> ghim tien trinh con
                            vao DUNG mot card, khoa theo UUID chu khong theo
                            index (index xe dich, UUID thi khong)
platform_core/gpu_claims.py  gpu_allows(gpu_index, need_mb) · publish(...) ·
                            blocking_priority(...)  -> da la lop phan xu theo CARD
```

Và không có app nào tranh: đếm toàn `apps/`, chỉ **hai** ToolSpec khai
`admission_resource` — `ltt_llm` → `llm_remote`, `ltt_voice` → `vieneu_gpu`.

| | |
|---|---|
| lợi | **giữ trọn cả ba ràng buộc**: không đụng `phat_dan()` · **không migration** · vẫn đi qua lease. Giữ nguyên "một GPU = một việc". Job ngắn không bao giờ đứng sau job dài |
| hại | cần **một dịch vụ sidecar thứ hai** (nssm) ghim card 1; VRAM ×2 (1,86 → 3,7 GB, thừa sức); `4-nghiem-thu.ps1` phải chốt cả hai làn trong `LTT_WORKER_POOLS` |
| rủi ro | **thấp nhất** — thay đổi nằm ở **cấu hình và triển khai**, không ở lịch, không ở engine, không ở sổ sách |

## 5. Chọn D — và ranh giới của lời khuyên này

Lý do chọn không phải "D hay hơn", mà là: **A/B/C đều trả giá bằng migration
hoặc bằng một bất biến đã ghi ra chữ, còn D không trả giá nào trong hai thứ đó**
kể từ khi card thứ hai sống lại.

⚠️ D **không** làm A thành sai. Ngày nào có đủ khách để cả hai card đều bận,
bài toán quay lại và A là câu trả lời đúng. D mua thời gian bằng phần cứng đang
rảnh — ghi ra đây để lượt sau không tưởng bài đã đóng vĩnh viễn.

### Phải đo TRƯỚC khi thi hành — chưa đo thì chưa chốt

1. ~~**Card 1 có thật sự rảnh cho giọng nói không?**~~ ✅ **ĐÃ ĐO 09/09**, và
   câu trả lời đỡ cho D:

   ```
   card 1: 781 MiB dung, 16 % util
   tien trinh compute: explorer.exe · StartMenuExperienceHost · SearchApp
   ```

   Toàn tiến trình **màn hình**, không một tải ML nào. 781 MiB là chi phí
   desktop; còn **~15,5 GB** trống cho compute. Không `upscalevideo`, không
   `anhnoibo`, không app LTT nào giữ nó.

   ⚠️ Nhưng nó là card **gắn màn hình**, và điều đó thêm hai thứ phải cân:
   (i) compute nặng trên card hiển thị làm giao diện giật — trên máy chủ không
   ai nhìn thì không sao, trên máy này thì chủ máy sẽ thấy; (ii) Windows WDDM có
   **TDR** (mặc định 2 s) reset driver khi một kernel chạy quá lâu. Kernel của
   TTS ngắn nên nhiều khả năng không chạm, **nhưng chưa đo** — và nếu chạm thì
   nó hỏng giữa một job dài, tức đúng loại job ta định đẩy sang đó.

   ⇒ Đề xuất tinh chỉnh: làn **DÀI** đặt ở card **0** (không gắn màn hình), làn
   **NGẮN** ở card 1. Ngược với trực giác, và đó là chủ ý: việc chạy lâu nên
   tránh xa card có TDR và có người đang nhìn.
2. **Ngưỡng chia làn**: `so_ky_tu` bao nhiêu thì vào làn dài? Phải rút từ phân
   bố **thật**, không đặt tay. ⚠️ Đo 7 ngày: 29 lượt, **0 lượt từ 05/09** — mẫu
   quá mỏng để rút phân bố. Đây là một `DATA_GAP`, không phải một chỗ để đoán.
3. **Job dài có thật sự cần cả card không**, hay `/v1/lo-ra-tep` gộp lô đã làm
   nó đủ nhanh để bài toán nhỏ hơn ta tưởng.

⛔ Câu 1 **đã trả lời** (không cần bí mật — `nvidia-smi` là đủ). Câu 2 và 3 thì
**chặn ở B-04** (thiếu `LTT_VOICE_SIDECAR_TOKEN`), và câu 2 còn chặn thêm bởi
một thứ token không gỡ được: **lưu lượng thật quá mỏng để rút phân bố**.

⇒ QĐ-V01 dừng ở **ĐỀ XUẤT**, không chuyển sang thi hành.

⭐ Nhưng ghi rõ mức độ chín, kẻo lượt sau đọc "ĐỀ XUẤT" rồi tưởng nó còn mơ hồ:
phương án đã chọn, ba ràng buộc đã kiểm, máy móc nền tảng đã xác nhận có sẵn, và
câu hỏi phần cứng đã đo xong. Thứ còn thiếu là **một ngưỡng**, và ngưỡng ấy phải
đến từ dữ liệu chứ không từ một lượt bàn nữa.

## 6. Đường lùi

D lùi bằng **một dòng cấu hình**: gộp hai làn về lại `vieneu_gpu`, tắt sidecar
thứ hai. Không có migration để đảo, không có cột để bỏ, không có dữ liệu nào
đổi hình dạng. Đó là lý do mạnh thứ hai để chọn nó.

A thì không có đường lùi rẻ: một khi `priority` vào lược đồ và trạng thái
nhả-giữa-chừng vào job đang chạy, gỡ ra là một migration nữa.

---

# QĐ-V02 — `voice_sidecar` không đặt trần luồng torch

**Trạng thái:** ĐỀ XUẤT · hạng mục **11**

**Vấn đề, đo 09/09:** lõi vật lý **10**; `torch.get_num_threads()` trong
`vieneu-venv` = **10**; `voice_sidecar` không gọi `set_num_threads` ở đâu cả.
⇒ một lượt sinh lấy **trọn** số lõi cho phần CPU. Cùng khuyết tật CLAUDE.md ghi
cho `apps/auto_scan_video/demucs_runner.py`.

Sidecar hiện ngủ (pid 6712, 112 luồng OS, CPU tích luỹ **0 s**) nên chưa ai thấy
đau. **Một lỗi chưa bao giờ nổ vẫn là một lỗi** — và nó sẽ nổ đúng lúc ai đó
chạy benchmark 15 phút cạnh năm cây khác.

**Đề xuất:** đặt trần trong `engine.nap()`, đọc từ biến môi trường với mặc định
an toàn. **Chưa chốt con số** — trần đúng phụ thuộc câu "máy này còn phục vụ ai
nữa", và đó là câu của chủ dự án chứ không phải của tôi.

⚠️ Trên một máy chủ **chỉ** chạy giọng nói, lấy trọn 10 lõi cho một job là
**đúng** — `admission_slots=1` nên chỉ có một job. Máy này thì vừa là production
vừa là máy phát triển của bảy cây. Nên đây là `OPS_GAP` của **môi trường**, và
bản vá không được giả định môi trường ấy là vĩnh viễn.

---

# QĐ-V03 — U-07: nối `/v1/stream` vào sản phẩm

**Trạng thái:** CHẶN Ở MỘT QUYẾT ĐỊNH THƯƠNG MẠI · 09/09/2026 · hạng mục **20**

## 1. Bốn trên tám lớp đã xong

| lớp | trạng thái |
|---|---|
| SDK `infer_stream` trên `V3TurboVieNeuTTS` (PyTorch — đúng đường ta chạy) | ✅ |
| `engine.co_streaming()` — dò năng lực **lúc chạy** | ✅ |
| `engine.phat_dan()` — generator float32, giữ suất suốt generator | ✅ |
| sidecar `POST /v1/stream` — cờ, kiểm năng lực, WAV header + PCM16 | ✅ |
| cờ `LTT_VOICE_STREAM` trên production | ❌ không đặt |
| `sidecar_client` bọc | ❌ |
| route web + JS | ❌ |
| hợp đồng Public API | ❌ |

## 2. Vận chuyển — ĐỀ XUẤT: giữ nguyên chunked HTTP

Sidecar đã trả `StreamingResponse(media_type="audio/wav")`: WAV header rồi
PCM16. Thẻ `<audio src>` phát thẳng được.

⇒ **Không** SSE (buộc base64 + tự ghép ở client), **không** WebSocket (thêm hạ
tầng, thêm một đường không đi qua middleware sẵn có). Thứ đã dựng là thứ đơn
giản nhất chạy được, và nó chạy được với thẻ `<audio>` trần — tức tăng cường
dần vẫn giữ.

⭐ Một lợi ích phụ đáng ghi: Cloudflare cắt ở **100 giây chờ phản hồi**
(CLAUDE.md luật 19). Streaming gửi byte đầu trong ~2 giây, nên nó **đi qua**
được giới hạn ấy — trong khi một lượt sinh đồng bộ 3.000 ký tự (17,5 s) thì
được, còn 20.000 ký tự (117 s) thì không.

## 3. 🔴 THỨ CHẶN: KHÔNG CÓ MÔ HÌNH TÍNH TIỀN CHO MỘT CỬA ĐỒNG BỘ

Đo: đường tiền hôm nay là **sinh → `ffprobe` đo giây thật → thu**
(`jobs.py`, khuôn 3.4). Nó cần một **tệp đã xong** để đo.

Streaming không có tệp đã xong lúc bắt đầu. Và cửa đồng bộ duy nhất đang tồn
tại — `/xem-truoc` — **không phải tiền lệ**: chú thích của nó ghi *"THUẦN TÍNH
TOÁN. Không chạm CSDL, không chạm mạng, không chạm GPU, không giữ credit."*

⇒ Streaming sẽ là **cửa đầu tiên vừa tiêu GPU vừa phải thu tiền ngoài hàng đợi
job**. Bốn câu chưa có câu trả lời:

| # | câu hỏi | vì sao không tự quyết được |
|---|---|---|
| 1 | Giữ chỗ trước khi phát? | `uoc_tran()` có sẵn và làm được. Nhưng giữ chỗ rồi **quyết toán bằng gì** khi không có tệp để `ffprobe`? |
| 2 | Khách **ngắt giữa chừng** thì thu bao nhiêu? | GPU đã tiêu thật. Thu đủ thì khách trả cho thứ không nghe hết; thu 0 thì có một đường tiêu GPU **miễn phí không giới hạn** |
| 3 | Đếm giây từ đâu? | Đếm mẫu PCM đã phát là đo được — nhưng nó là một **nguồn chân lý thứ hai** cạnh `ffprobe`, và hai nguồn thì có ngày lệch |
| 4 | Có ghi vào Lịch sử không? | Không có `job_id` ⇒ không có bản ghi, không hoàn tiền được, không truy được |

⛔ Câu 2 là câu thật sự khó, và nó **không phải câu kỹ thuật**. Nó hỏi: *một
lượt GPU đã tiêu mà khách bỏ giữa chừng thì ai chịu?* Đó là chính sách thương
mại. §36 xếp tiền của khách ở bậc 2; §37 nói dừng khi cần quyết định của chủ
sản phẩm. Cả hai chỉ về cùng một chỗ.

## 4. Vì sao tôi KHÔNG viết mã trước rồi hỏi sau

Bốn câu trên **đổi hình dạng mã**, không phải đổi một hằng số:

- câu 1 quyết có `credit.giu()` trước generator hay không;
- câu 2 quyết có cần `try/finally` quanh generator để quyết toán phần đã phát;
- câu 3 quyết `engine.phat_dan()` có phải đếm mẫu và trả về hay không —
  tức **đổi chữ ký** của một hàm trong sidecar;
- câu 4 quyết có tạo `Job` cho lượt stream hay không, và nếu có thì "cửa đồng
  bộ" không còn đồng bộ.

Viết trước rồi sửa là viết hai lần, và bản thứ nhất sẽ để lại chú thích sai.

## 5. Ba mô hình để chủ sản phẩm chọn

| | mô hình | thu khi ngắt giữa chừng | phức tạp |
|---|---|---|---|
| **α** | **Nghe thử mở rộng** — miễn phí, trần ngắn (vd 300 ký tự), có hạn mức/giờ | 0 | **thấp nhất** — không chạm tiền, không cần `Job` |
| β | Giữ chỗ + quyết toán theo **số mẫu PCM đã phát** | theo phần đã nghe | trung bình — cần nguồn chân lý thứ hai |
| γ | Tạo `Job` thật, stream là **một cửa xem** của job ấy | như job thường | cao — nhưng thống nhất tiền, lịch sử, hoàn tiền |

⭐ **α đủ để đóng U-07 như bản kiểm toán mô tả nó**: mục tiêu ghi ở
`VIRAL_VOICE_AUDIT` là *"nghe được câu đầu trong ~2 s thay vì chờ cả bài"* — đó
là bài toán **chọn giọng**, không phải bài toán sản xuất. Và nghe thử đã có tiền
lệ không tính tiền (`nghe_thu.py`).

⇒ Nếu chủ sản phẩm không muốn quyết chính sách hoàn tiền hôm nay, **α mở khoá
phần lớn giá trị với rủi ro tiền bằng không**.

## 6. Đường lùi

Cả ba mô hình lùi bằng cờ `LTT_VOICE_STREAM=0` — cửa trả 404 và sản phẩm quay
về đúng hành vi hôm nay. Cờ đã có sẵn trong sidecar, không phải thêm.

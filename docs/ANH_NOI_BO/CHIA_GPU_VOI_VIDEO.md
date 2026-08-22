# Chia một card 3090 giữa việc VIDEO và việc ẢNH

**2026-08-21.** Người dùng xác nhận: **máy B có chạy video**. Tài liệu này giải
bài toán đó. Nó là phụ lục bắt buộc của [`KE_HOACH_H37.md`](KE_HOACH_H37.md) §10.2.

> ## ⚠️ ĐÍNH CHÍNH 2026-08-22 — TIÊU ĐỀ TÀI LIỆU NÀY ĐÃ HẸP
>
> Không phải hai hộ, mà **ba**. Đo lúc 22:27 ngày 22/08: một dự án thứ ba —
> **`H:\LTT_LLM`**, dịch vụ `LTTLlamaSwap` + `LTTLlmGateway`, cổng 8280/8299 —
> chạy `llama-server.exe` nạp `Qwen3.8-27B-UD-Q4_K_M.gguf` và **giữ 15,9 GB VRAM
> trong khi GPU 0 % tải**. Nó tự nhả sau `ttl: 1800` (30 phút không dùng).
>
> **Hai điều tài liệu này nói vẫn đúng nhưng không đủ:**
>
> 1. Mọi phân tích dưới đây giả định hộ kia là **video, chạy qua chính ComfyUI đó**,
>    nên hàng đợi ComfyUI nhìn thấy. Hộ LLM **không đi qua ComfyUI** — hàng đợi mù
>    hoàn toàn với nó.
> 2. Chốt dò bận từng dựa vào *"tiến trình lạ trên card đều là python"*.
>    `llama-server.exe` **không phải python**, và điều đó làm cổng render báo
>    **rảnh** trong khi card chỉ còn 4,6 GB. Đã sửa — xem **D-037**.
>
> Bài học chung: **đừng đếm tên tiến trình.** Chốt hiện tại lấy hiệu giữa
> `nvidia-smi` (thấy toàn card) và ComfyUI `/system_stats` (chỉ thấy chính nó), nên
> nó không cần biết hộ thứ tư sẽ tên là gì.

Mọi số dưới đây **đọc thẳng từ mã và nhật ký sự cố của dự án video trên máy B**
(`E:\LTT AI`), không phải giả định.

---

## 1. Việc video trên máy B thật ra là gì

Không phải vài script rời. Đó là một dự án hoàn chỉnh: `E:\LTT AI` với **37
chương tài liệu**, `src/ltt/` (workflow engine, executor, VLM), thư mục `jobs/`
có job chạy đêm 21/08, và một bộ quy tắc riêng (`QUY_TAC.md`, `cap_quyen.md`).

Sáu sự thật quyết định thiết kế:

| # | Sự thật | Nguồn |
|---|---|---|
| 1 | **Video dùng CHUNG đúng ComfyUI đó** — `COMFY_HOST = http://127.0.0.1:8188` | `src/ltt/executor.py:25` |
| 2 | **Một lượt video từng chạy 72,5 phút**, ComfyUI báo `success`, ra đủ 77 khung | chú thích `executor.py:193` |
| 3 | Hàng rào chờ tối đa **3600 giây** + watchdog phát hiện ComfyUI chết ở tầng native | `executor.py:201–219`, sinh ra sau sự cố 11/08 |
| 4 | **Đỉnh VRAM đo được: 24.251 MiB / 24.576** — video ăn **98,7 %** card | nhật ký sự cố 19/08 trong `cong_gpu.py` |
| 5 | Đã có sẵn hàm **bảo ComfyUI nhả model khỏi VRAM** (`/free`) | `executor.py:160` |
| 6 | **Chưa có scheduler.** Chương `23_Queue_And_Scheduler` ghi *"CHƯA VIẾT"*, phạm vi dự kiến: *"hàng đợi job, chọn worker, gom job theo model, ưu tiên preview"* | `docs/23_Queue_And_Scheduler/_README.md` |

Và ba con số RAM rút từ **sự cố thật**, không phải phỏng đoán — chép nguyên từ
`cong_gpu.py` vì chúng ràng buộc luôn cả phía ảnh:

```
còn ~85 GB trống  → mọi lượt lành
còn ~23 GB trống  → VRAM bị đẩy lên 98 %, lượt hỏng          (D30)
còn ~8,6 GB trống → mất điều khiển từ xa                      (20/08)
còn ~4 GB trống   → WINDOWS SẬP                               (19/08)
⇒ ngưỡng chặn hiện hành: RAM CÒN TRỐNG ≥ 48 GB mới cho tiêu GPU
```

Thủ phạm vụ sập 19/08 là một máy ảo VMware giữ 37 GB — **không liên quan gì tới
GPU**. Bài học họ tự rút, và nó áp dụng luôn cho ta: *nếu không chốt mốc đo trước
khi phóng lượt thì vụ sập chỉ còn là "tự nhiên sập" và ta sẽ đi sửa nhầm chỗ.*

### Ba đính chính của chủ dự án (21/08) — và chúng đổi thiết kế thế nào

**(a) RAM đã 192 GB, sắp lên 256 GB.**
Đo lại lúc 17:54 hôm nay: `total 196.488 MB · dùng 84.296 · còn 112.191`. Đây
không phải chuyện thoải mái hơn — nó **xoá hẳn một rủi ro**. Xem §6.1.

**(b) Con số 72,5 phút là của giai đoạn THỬ NGHIỆM, không phải của sản phẩm.**
Đây là đính chính quan trọng nhất. Nó có nghĩa là **mọi ngưỡng trong tài liệu này
không được viết cứng theo 72 phút** — phải viết theo *thời gian còn lại ước tính*,
đo sống. Xem §3 và §4, đã sửa lại theo hướng đó.

**(c) Sau này sẽ hợp nhất cơ chế kiểm VRAM + RAM cho toàn bộ ứng dụng.**
Phần lớn hạ tầng cho việc đó **đã tồn tại** và tôi vừa xác minh trên cả hai máy.
Xem §10.

---

## 2. Vì sao "xếp chung một hàng đợi" — hiểu theo nghĩa FIFO — là sai

Cách hiểu tự nhiên nhất: một hàng đợi, ai đến trước chạy trước. Đặt vào số thật:

> Khách bấm "Tạo ảnh". Trước đó 2 phút bạn phóng một lượt video.
> **Khách chờ 72 phút.**

Không sửa được bằng cách chỉnh hàng đợi, vì:

- **Không cắt ngang được lượt video.** Nó đã tiêu 40 phút GPU; giết nó là ném đi
  40 phút và một job hỏng. Ampere không có preemption ở mức mà việc này an toàn.
- **Không chạy song song được.** Video đã đo đỉnh **24.251 MiB / 24.576**. Không
  còn chỗ cho một model ảnh 9–20 GB. Đây là sự thật vật lý, không phải chính sách.
- **Hai loại việc lệch nhau ba bậc độ lớn về thời gian**: ảnh ~30 giây, video
  ~30–72 phút. Bất kỳ hàng đợi FIFO nào trộn hai thứ này cũng sinh ra thời gian
  chờ nhìn như hệ thống hỏng.

**Kết luận: không xếp chung theo FIFO. Xếp chung theo *quyền dùng GPU*, và cho
việc ảnh một đường thoát khi không giành được quyền.**

Đường thoát đó **đã tồn tại sẵn và không phải viết mới**: `api_pool.chon_key(
category=..., thu_tu_provider=[...])` — cascade đa-provider của H8 Pha 2.

---

## 3. Thiết kế: bốn tầng, tầng nào hỏng thì tầng dưới đỡ

```
Tầng 1  CỬA SỔ GIỜ        video ban đêm · ảnh ban ngày        (chính sách, rẻ nhất)
Tầng 2  TRỌNG TÀI         một giấy phép dùng GPU, video ưu tiên
Tầng 3  RƠI VỀ GEMINI     B bận → cascade sang cloud, khách KHÔNG chờ, KHÔNG mất tiền
Tầng 4  COMFYUI TỰ NỐI ĐUÔI  chạy tuần tự sẵn — lưới an toàn cuối, chống OOM
```

Tầng 4 quan trọng hơn vẻ ngoài: **ComfyUI vốn chỉ chạy một prompt một lúc.** Nên
ngay cả khi ba tầng trên hỏng hết, hậu quả xấu nhất là *chờ*, không phải *OOM*.
Đó là lý do chọn **một instance ComfyUI duy nhất** (xem §6).

### Luật quyết định: KHÔNG phải "bận/rảnh", mà là "còn bao lâu"

Đây là chỗ đính chính (b) đổi thiết kế. Một cổng chỉ biết *bận* hay *rảnh* sẽ
**lỗi thời ngay khi lượt video nhanh lên** — nó đẩy job sang Gemini cả khi chỉ cần
chờ 8 giây. Luật đúng là:

```
job ảnh tới
   │
   ├─ GPU rảnh                          → chạy ngay
   ├─ bận, ETA ≤ NGƯỠNG_CHỜ (mặc định 45 s)  → CHỜ, rồi chạy ở nhà (rẻ)
   └─ bận, ETA >  NGƯỠNG_CHỜ            → cascade sang Gemini (nhanh)
```

**Một tham số duy nhất, `NGƯỠNG_CHỜ`, và nó tự thích nghi.** Hôm nay lượt video
kéo dài thì gần như mọi job rơi sang Gemini. Ngày video xuống còn 30 giây thì gần
như mọi job ở lại nhà — **không sửa một dòng mã nào**. Đó là lý do phải viết theo
ETA thay vì theo trạng thái nhị phân.

Lấy ETA ở đâu, mà không đụng vào dự án video: **ComfyUI phát tiến độ qua
websocket** (`progress` mang `value/max` theo bước, `executing` mang node đang
chạy). Cổng render chỉ **nghe**, không gửi gì. Từ nhịp bước suy ra thời gian còn
lại. Khi chưa đủ dữ liệu để suy (mới bắt đầu, hoặc node không báo bước), lùi về
**trung vị lịch sử** của các lượt lạ đã quan sát — cổng render tự ghi, tự học,
không cần ai khai báo.

Ba điều bắt buộc kèm theo:

- **Không bao giờ ước tính lạc quan.** Thà báo ETA dài hơn thật và đẩy sang
  Gemini, còn hơn hứa 20 giây rồi bắt khách chờ 4 phút.
- **`NGƯỠNG_CHỜ` là cấu hình, không phải hằng số trong mã** — bạn sẽ chỉnh nó
  nhiều lần khi video nhanh dần.
- **Đo lại sau mỗi lần đổi**: tỉ lệ job ở nhà / rơi Gemini là một chỉ số vận hành,
  và nó chính là **đồng hồ đo tiền** — mỗi phần trăm rơi sang Gemini là tiền thật.

### Tầng 3 là mấu chốt — và nó lật ngược bài toán

Câu hỏi sai: *"làm sao xếp hàng job ảnh sau job video?"*
Câu hỏi đúng: **"khi GPU nhà đang bận thì tấm ảnh này nên đi đâu?"**

Trả lời: **đi Gemini**. Khách nhận ảnh sau 10 giây, không biết gì đã xảy ra.
Bạn trả 500–1.600 đồng cho tấm đó thay vì ~20 đồng tiền điện. Đổi 1.500 đồng lấy
việc không có ai chờ 72 phút là một cuộc đổi chác dễ.

Hệ quả kiến trúc: **card 3090 là một cách để RẺ ĐI, không phải một chỗ dựa để
CHẠY ĐƯỢC.** Sản phẩm không bao giờ phụ thuộc vào việc B rảnh. Điều này cũng giải
luôn hai rủi ro khác trong `KE_HOACH_H37.md` §8: "B tắt/mất điện" và "ComfyUI đang
chạy tay" — cả hai rơi từ *sự cố* xuống *tốn thêm tiền*.

---

## 4. Trọng tài GPU: hai bản, chọn một

### Bản A — **Không đụng gì vào dự án video** *(khuyến nghị làm trước)*

Cổng render tự suy ra máy có bận không, bằng thứ ComfyUI đã trả lời sẵn:

```
cổng render nghe websocket ComfyUI + hỏi GET /queue mỗi 2 giây
  ├─ có prompt chạy/chờ mà KHÔNG PHẢI của mình  → BẬN (video) + ước tính ETA
  ├─ VRAM đang dùng > 4 GB mà mình không giữ job → BẬN, ETA chưa biết
  ├─ RAM còn trống < 48 GB                       → BẬN (đúng ngưỡng của họ)
  └─ ngược lại                                   → RẢNH
```

Phân biệt việc của ai rất đơn giản: cổng render biết `prompt_id` của chính nó.
**Cái gì trong hàng đợi mà không phải của mình thì là của video.**

`/health` trả `busy`, **`eta_s`** và lý do. Máy A đọc trước khi giao job; theo luật
ở §3: chờ nếu `eta_s ≤ NGƯỠNG_CHỜ`, ngược lại `api_pool` cascade sang Gemini.

| Được | Mất |
|---|---|
| Không sửa một dòng nào của `E:\LTT AI` | Có cửa sổ đua ~2 giây: hai bên cùng gửi trong cùng một nhịp |
| Không cần dự án kia đồng ý | Nếu đua, hậu quả là **lượt video chờ thêm ~30–60 giây** sau một lượt ảnh |
| Triển khai trong nửa ngày | Không có hàng đợi thật, chỉ có "bận/rảnh" |

Cửa sổ đua đó **chấp nhận được**: một lượt video 72 phút bị đẩy lùi 40 giây là
0,9 %. Chiều ngược lại — ảnh chờ video — mới là thứ không chấp nhận được, và tầng 3
đã xử lý.

### Bản B — **Giấy phép thật, hai bên cùng tôn trọng** *(làm sau, nếu bản A không đủ)*

Một tiến trình trọng tài bé trên B (hoặc chỉ một tệp khoá + nhịp đập, không cần
service):

```
POST   /lease            {chu, loai: video|anh, ttl, uu_tien}  → cap | tu_choi + vi_tri_cho
POST   /lease/{id}/nhip  giữ chỗ trong lúc chạy
DELETE /lease/{id}       trả chỗ
GET    /trang_thai       ai đang giữ, từ bao giờ, ai đang chờ
```

Luật:

- **Một người giữ tại một thời điểm.**
- **Video luôn thắng khi tranh chấp.** Nó dài, tốn kém, có người ngồi canh.
- **Việc ảnh giành theo cụm, không theo từng job**: giành được thì **vét hết** job
  ảnh đang chờ (tối đa T giây hoặc N job) rồi mới nhả. Chống đổi model liên tục.
- **Hết hạn tự nhả** (mồ côi) — đúng khuôn `platform_core/leases.py` đã chạy ổn ở H36.

Điểm chạm phía video: `src/cong_gpu.py` **đã là chốt bắt buộc trước mọi lượt GPU**
— thêm giấy phép vào đó là tự nhiên nhất. Nhưng phải nói thẳng hai điều:

1. **Đó là sửa dự án khác.** `E:\LTT AI` có quy tắc riêng (`cap_quyen.md`,
   `QUY_TAC.md`). Việc này cần bạn cho phép, và nên do phiên làm việc của chính
   dự án đó thực hiện, không phải tôi thò tay sang.
2. **`cong_gpu.py` cấm thêm câu hỏi vì "nghe hợp lý"** — docstring của nó viết:
   *"Mỗi câu hỏi phải trỏ về MỘT SỰ CỐ THẬT."* Nên chỉ thêm khi đã có một lần va
   chạm thật giữa hai loại việc. **Bản A trước, bản B khi có sự cố** — đó chính là
   cách dự án đó tự đặt ra.

Lưu ý kỹ thuật: `cong_gpu.py` là *kiểm tra trước*, còn lượt chạy kéo dài suốt sau
đó. Nên giấy phép phải do **`ltt/chay_job.py` giữ suốt lượt**, không phải do cổng
kiểm lấy rồi nhả ngay. Đây là chi tiết dễ làm sai và làm hỏng cả cơ chế — và nó
đúng bất kể lượt video dài 72 phút hay 2 phút.

---

## 5. Chế độ độc chiếm — yêu cầu đến từ chính quy tắc của dự án video

Dự án đó rất khắt khe về tính toàn vẹn của số đo: *"nếu không chốt mốc đo TRƯỚC khi
phóng lượt, vụ sập này chỉ còn là 'tự nhiên sập'"*. Một job ảnh chen vào giữa lượt
benchmark video sẽ **làm bẩn số đo VRAM/RAM/nhiệt** của họ.

Vì vậy phải có một công tắc:

```
POST /doc_chiem  {bat: true, ly_do: "benchmark cohort G09", het_han: "2h"}
```

Bật → cổng render từ chối mọi job mới, `/health` báo `busy: exclusive`, máy A
cascade sang Gemini toàn bộ. Tự tắt khi hết hạn để không ai quên bật lại.

Chiều ngược lại cũng đúng và cũng phải tôn trọng: khi **ta** đang chạy benchmark
ảnh ở giai đoạn G4/G9 (30 prompt × nhiều profile, đo VRAM đỉnh), lượt video chen
vào cũng làm bẩn số của ta y hệt.

---

## 6. Một instance ComfyUI hay hai?

| | **Một instance (khuyến nghị)** | **Hai instance (8188 video, 8189 ảnh)** |
|---|---|---|
| Chống OOM | **Miễn phí** — ComfyUI chạy tuần tự sẵn | **Mất** — hai tiến trình cùng đòi VRAM, video đã ăn 98,7 % ⇒ OOM thật |
| Đổi model | ComfyUI tự nhả/nạp; RAM 192 GB nên là chuyển RAM→VRAM, không đọc đĩa | Mỗi bên giữ cache riêng, đỡ đổi hơn |
| Hàng đợi | Một, dùng chung | Hai, phải tự đồng bộ |
| Trọng tài | Tuỳ chọn (bản A là đủ) | **Bắt buộc** phải có bản B trước khi bật |
| Rủi ro với việc video đang chạy | Thấp | Cao — chạm vào thứ đang hoạt động |

### 6.1 RAM 192 GB đã xoá bài toán "đổi model tốn kém" — trước cả khi lên 256 GB

Tôi đã lo chuyện đổi qua lại giữa model video và model ảnh làm hao thời gian. Đọc
kỹ `comfy/cli_args.py` thì thấy **lo thừa**, và chính bản nâng RAM của bạn là thứ
xoá nó.

ComfyUI đang chạy với `--cache-ram 24 64`. Hai số đó là **ngưỡng RAM còn trống
phải giữ lại**, không phải dung lượng cache:

| Tham số | Ý nghĩa thật | Trên máy 192 GB | Trên máy 256 GB |
|---|---|---|---|
| số thứ nhất `24` | giữ ≥ 24 GB trống cho cache **đang hoạt động** | — | — |
| số thứ hai `64` | giữ ≥ 64 GB trống cho **model ghim trong RAM** | ghim được tới **~128 GB** | ghim được tới **~192 GB** |

Đối chiếu với thứ cần ghim: model video lớn nhất trên máy là
`wan2.1_vace_14B_fp16` **32,3 GB**; bộ model ảnh Klein ước **~26 GB**. Cộng lại
~58 GB — **nằm gọn trong 128 GB ngay hôm nay**.

Hệ quả: khi đổi giữa việc video và việc ảnh, ComfyUI **không đọc lại đĩa**. Nó chỉ
chuyển trọng số từ RAM sang VRAM. Chi phí đổi model rút về đúng một phép tính
PCIe (§6, bảng dưới) — vài giây, không phải vài phút.

Ba điều rút ra:

- **Nâng lên 256 GB là để thoải mái, không phải để chạy được.** 192 GB đã đủ cho
  cả hai bộ model cùng ghim. Nếu nâng, cái được là chỗ cho model thứ ba (SDXL bậc
  rẻ, hoặc một model video nữa) mà vẫn giữ nguyên biên an toàn.
- **`--cache-ram 24 64` đang đặt đúng** và tình cờ khớp với ngưỡng an toàn 48 GB
  của `cong_gpu.py` (64 > 48). **Đừng hạ hai số này xuống** để "ghim được nhiều
  hơn" — làm vậy là ăn vào chính biên đã cứu máy khỏi lần sập 19/08.
- **Khi lên 256 GB thì hai số này KHÔNG cần đổi**, vì chúng là ngưỡng tuyệt đối
  (GB), không phải tỉ lệ. Đây đúng là bài học ở §10.

**Chọn một instance.** Lý do quyết định: nó biến "trọng tài" từ *thứ bắt buộc phải
đúng* thành *thứ để tối ưu độ trễ*. Sai trọng tài với một instance = chờ lâu hơn;
sai trọng tài với hai instance = OOM giữa job của khách **và** giết luôn lượt video
72 phút của bạn.

Giá phải trả: đổi model qua lại. Ước tính ~20 GB qua PCIe — **và đây đúng là chỗ
con số PCIe chưa đo ở G1 trở nên quan trọng**:

| PCIe link | Băng thông thực | Đổi model một chiều |
|---|---|---|
| 3.0 x16 | ~11–12 GB/s | **~2 giây** — không đáng kể |
| 3.0 x8 | ~6 GB/s | ~3,5 giây — vẫn ổn |
| 3.0 x4 | ~3 GB/s | ~7 giây mỗi chiều — bắt đầu đau, phải gom cụm mạnh hơn |

Xeon E5-2678 v3 là PCIe 3.0. **Chạy `E:\AI\tools\pcie_check.py` là việc đầu tiên
của G1.** Nếu ra x4 thì thời gian vét cụm (T ở §4 bản B) phải kéo dài ra.

---

## 7. Ảnh hưởng tới sản phẩm — và một câu hỏi cho bạn

Nếu model nhà chỉ rảnh **một phần thời gian**, thì "chọn model" hiện ra trước mặt
khách như thế nào? Hai đường, khác nhau thật sự:

**Đường 1 — Khách chọn BẬC, hệ thống chọn model.** Khách thấy "Tiêu chuẩn / Cao
cấp". Bận thì đi Gemini, rảnh thì đi model nhà. Khách không bao giờ gặp lỗi.
*Rủi ro*: cùng một bậc mà hai lần cho ra hai phong cách ảnh khác nhau — khách tinh
mắt sẽ nhận ra và khó chịu.

**Đường 2 — Khách chọn model, thấy rõ trạng thái.** "Model nhà — đang bận, còn
khoảng 40 giây" và một nút *"Dùng đám mây ngay"*. Trung thực, nhất quán về phong
cách. *Rủi ro*: lộ ra rằng hệ thống có lúc bận, và thêm một quyết định cho khách
phải nghĩ. Lưu ý: đường này chỉ dùng được **vì** đã có `eta_s` ở §3 — hiện một con
số đếm ngược thì chấp nhận được, hiện chữ "đang bận" trơ trọi thì không.

Tôi nghiêng về **đường 2 cho giai đoạn đầu** (trung thực, dễ gỡ lỗi, hợp câu
*"nếu một khả năng không đủ ổn định, ghi rõ thay vì che giấu bằng UI"* trong bộ
build pack), rồi chuyển sang đường 1 khi đã đo được model nhà đủ gần Gemini về
chất lượng — tức là **sau G11**.

---

## 8. Thêm vào lộ trình

| Bước | Thêm gì so với `KE_HOACH_H37.md` |
|---|---|
| **G1** | Chạy `pcie_check.py` — giờ nó quyết định cả thời gian vét cụm, không chỉ tốc độ nạp |
| **G4 / G9** | Chỉ chạy khi **không có lượt video nào**. Ghi vào biên bản đo: máy có độc chiếm không |
| **G6** (cổng render) | Bộ dò bận (§4 bản A) · **nghe websocket ComfyUI để ước tính `eta_s`** · `/health` trả `busy` + `eta_s` + lý do · `POST /doc_chiem` · vét theo cụm · **phát báo cáo tài nguyên theo khuôn §10** |
| **G7** | `kiem_tra.ps1` thêm: gọi thử lúc video đang chạy, phải trả `busy` kèm `eta_s` hợp lý chứ không nhận job |
| **G8** | Provider `ltt_image` khai `busy`+`eta_s` để `api_pool` quyết chờ-hay-cascade — **không** đánh dấu key lỗi/cooldown, vì bận không phải hỏng |
| **G9** | Kịch bản: phóng một lượt video giả **10 phút và một lượt 20 giây**, gửi 20 job ảnh vào giữa. Lượt 20 giây → job **chờ rồi chạy ở nhà**; lượt 10 phút → **rơi về Gemini trong 60 giây**. Đo tỉ lệ ở-nhà / rơi-cloud |
| **G10** | Giao diện theo đường 1 hay đường 2 ở §7 — chờ bạn chốt |

**Một cạm bẫy phải tránh ngay từ G8:** khi B bận, `image_gen` **không được** gọi
`api_pool.danh_dau_loi()` cho key của `ltt_image`. Bận là trạng thái bình thường,
không phải sự cố. Đánh dấu lỗi sẽ đẩy key vào cooldown rồi `disable` sau 5 lần —
và một buổi tối chạy video sẽ **tự tắt vĩnh viễn** model nhà mà không ai hiểu vì sao.

---

## 9. Cần bạn chốt

1. **Cửa sổ giờ (tầng 1)** — có muốn đặt luôn không? Job video gần nhất chạy
   00:52–01:10, có vẻ bạn đã quen chạy video ban đêm. Nếu chốt "video 22h–8h, ảnh
   8h–22h" thì tranh chấp gần như biến mất và ba tầng dưới chỉ còn là lưới an toàn.
2. **Có cho phép sửa `E:\LTT AI` không** (bản B, thêm giấy phép vào `cong_gpu.py`
   + `chay_job.py`)? Tôi khuyến nghị **chưa** — làm bản A trước, chỉ nâng lên bản B
   khi có va chạm thật, đúng như quy tắc của chính dự án đó.
3. **Đường 1 hay đường 2** ở §7 — khách thấy gì.
4. **Ai chạy video?** Nếu chỉ mình bạn và luôn chạy tay, tầng 1 + tầng 3 là đủ, có
   thể bỏ hẳn trọng tài. Nếu sau này video cũng thành dịch vụ tự động thì phải làm
   bản B ngay từ đầu — và lúc đó chương `23_Queue_And_Scheduler` của dự án kia nên
   được viết **một lần cho cả hai loại việc**, thay vì mỗi bên một hàng đợi.
5. **`NGƯỠNG_CHỜ` khởi điểm** (§3) — tôi đề xuất **45 giây**. Khách chờ 45 giây cho
   một tấm ảnh là chấp nhận được; hơn nữa thì nên trả tiền cho Gemini.

---

## 10. Hợp nhất kiểm tra VRAM + RAM cho toàn hệ (điểm 3 của bạn)

Đây là ý đúng, và tin tốt: **phần khó đã có sẵn.** Tôi vừa xác minh trên cả hai máy
lúc 17:54 hôm nay.

### 10.1 Cái đã có: một khuôn đo duy nhất, đã chạy trên cả hai máy

`GET /api/v1/metrics` của Nexus trả **đúng cùng một cấu trúc** trên máy A và máy B:

```
cpu     percent · per_core · physical/logical_cores · freq_mhz
memory  total_mb · used_mb · available_mb · percent · swap_total_mb · swap_used_mb
volumes drive · filesystem · total_gb · free_gb · used_percent
gpus    uuid · name · vram_total_mb · vram_used_mb · vram_free_mb ·
        compute_capability · utilization_gpu_pct · temperature_c ·
        power_draw_w · power_limit_w · throttle_reasons · process_count
```

Bằng chứng, hai lời gọi thật:

| Máy | Kết quả |
|---|---|
| A | RAM 9.667 / 32.617 MB · `RTX 5060 Ti` uuid `GPU-ebecd0a4…` 259/16.311 MB · `RTX 5060 Ti` uuid `GPU-6df3a5c5…` 1.024/16.311 MB, util 23 % |
| B | RAM 84.296 / 196.488 MB · `RTX 3090` uuid `GPU-26623278…` 794/24.576 MB, 35 °C, 19,4 W |

Ba tính chất khiến nó đúng là nền cho việc hợp nhất:

- **Neo bằng UUID, không bằng index** — trùng đúng nguyên tắc `platform_core/gpu.py`
  đã chốt: *"index do driver đánh theo thứ tự bus và ĐỔI khi cắm thêm/bớt card"*.
  Hai hệ độc lập đi tới cùng một kết luận là dấu hiệu kết luận đó đúng.
- **Đi qua kênh có phân quyền và có nhật ký** — `gpu.read`, mọi lời gọi vào audit log.
- **Đọc được từ xa** — máy A hỏi được tài nguyên máy B mà không cần cài gì thêm ở B.

### 10.2 Cái còn thiếu: "ai đang giữ", chứ không phải "đang dùng bao nhiêu"

Đây là ranh giới mà một hệ hợp nhất phải phân biệt rõ, nếu không nó sẽ sai theo
kiểu khó thấy:

| | Câu hỏi | Ai trả lời được hôm nay |
|---|---|---|
| **Đo** | *"VRAM còn trống bao nhiêu?"* | ✅ Nexus `/metrics` — cả hai máy |
| **Giữ chỗ** | *"Ai đã đặt chỗ, tới khi nào?"* | ⚠️ chỉ máy A, chỉ cho GPU của máy A (`platform_core/gpu_lease.py`) |
| **Ngưỡng** | *"Bao nhiêu là đủ để phóng lượt?"* | ⚠️ chỉ máy B, chỉ cho việc video (`cong_gpu.py`, 48 GB) |

**Đo không thay được giữ chỗ.** Hai tiến trình cùng đọc thấy "còn 23 GB trống",
cùng kết luận "đủ", cùng nạp model, cùng OOM. Đây chính là cuộc đua mà
`gpu_lease.py` sinh ra để chặn, và docstring của nó đã mô tả đúng nguyên văn.

Điều đáng chú ý: **`gpu_lease` đã có `host` trong khoá `UNIQUE(host, gpu_uuid)`.**
Nghĩa là bảng lease hiện tại **về mặt lược đồ đã đỡ được nhiều máy** — không phải
sửa CSDL, chỉ chưa có ai ghi vào đó thay cho máy B.

### 10.3 Đề xuất: ba mảnh, không phải một hệ mới

```
        ĐO                     GIỮ CHỖ                  NGƯỠNG
   Nexus /metrics    +    gpu_lease (host, uuid)   +   ngưỡng TUYỆT ĐỐI
   (đã có, 2 máy)         (đã có, mở rộng host)         (rút từ sự cố thật)
```

- **Đo**: giữ nguyên Nexus. Cổng render **không tự chế bộ đọc GPU thứ tư** — nó
  phát lại đúng khuôn trên trong `/health`. Đây là điều tôi đã đưa vào G6 để nó
  không trở thành mảnh vụn thứ tư ngay từ ngày đầu.
- **Giữ chỗ**: lease của máy B do **phía máy A** ghi hộ trước khi giao việc — máy B
  vẫn không chạm CSDL, không giữ bí mật nào. Nhưng phải trung thực về giới hạn:
  **lease do A ghi không chặn được dự án video trên B**, vì dự án đó không đọc CSDL
  của A. Nên vẫn cần hai tầng: lease của A cho việc của A, và trọng tài trên B cho
  tranh chấp giữa hai dự án (§4).
- **Ngưỡng**: gom về **một bảng duy nhất**, và mỗi dòng phải **trỏ về một sự cố
  thật** — đúng kỷ luật mà `cong_gpu.py` tự đặt ra:

| Ngưỡng | Giá trị | Sự cố sinh ra nó |
|---|---|---|
| RAM còn trống tối thiểu để phóng lượt GPU | **48 GB** | 19/08 Windows sập ở ~4 GB; ~23 GB đẩy VRAM lên 98 % |
| VRAM còn trống tối thiểu để nhận job ảnh | *chưa đo* — G4 sẽ chốt | — |
| Cảnh báo nhiệt GPU | *chưa đặt* — 3090 tiết lưu ~83 °C, đã quan sát 71 °C | — |

### 10.4 Một cạm bẫy sẽ cắn lần thứ ba khi bạn lên 256 GB

`cong_gpu.py` từng dùng ngưỡng **theo tỉ lệ** (`nền RAM < 40 %`). Khi RAM lên
96 → 192 GB, cùng một con số đổi hẳn ý nghĩa:

```
trên  96 GB → chặn khi còn trống < 58 GB
trên 192 GB → chặn khi còn trống < 115 GB
trên 256 GB → chặn khi còn trống < 154 GB   ← sẽ xảy ra nếu ai đó quay lại dùng tỉ lệ
```

Và nó sinh ra **chặn oan**: một máy ảo 100 GB trên máy 192 GB đẩy mức dùng lên
52 % ⇒ cổng chặn, **trong khi vẫn còn 91 GB trống**. Họ đã sửa thành ngưỡng tuyệt
đối (48 GB) đúng vì lý do đó.

> **Luật cho hệ hợp nhất: mọi ngưỡng tài nguyên phải là LƯỢNG TUYỆT ĐỐI (GB), không
> phải tỉ lệ.** Bạn đang chuẩn bị nâng RAM lần nữa — đây là lúc luật này đáng tiền
> nhất. Ngoại lệ duy nhất: một trần tỉ lệ rất cao làm lưới an toàn cho máy RAM nhỏ,
> để nó nói "máy này không đủ RAM" thay vì chặn im lặng mãi mãi.

Cùng lý do đó, `--cache-ram 24 64` của ComfyUI **không cần đổi** khi lên 256 GB —
nó đã là GB tuyệt đối (§6.1).

### 10.5 Khi nào làm

**Không phải bây giờ.** H37 chỉ cần cổng render **phát đúng khuôn** ở §10.1 và
**tôn trọng ngưỡng 48 GB** ở §10.3. Việc hợp nhất thật (một bảng ngưỡng, lease đa
máy, một trang nhìn toàn cụm) là một hạng mục riêng — đề xuất **H38**, làm sau khi
H37 đã chạy thật, vì lúc đó mới có đủ **ba** người dùng thật của cơ chế đó (worker
máy A, cổng render máy B, dự án video máy B) để thiết kế không phải đoán.

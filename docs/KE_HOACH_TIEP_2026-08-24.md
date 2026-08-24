# Kế hoạch xây dựng tiếp — chốt 2026-08-24

Viết sau khi D-057 đóng đường "dùng máy A sinh ảnh". Đây là **một danh sách duy
nhất, xếp theo thứ tự làm**, gộp việc còn treo của H37, H38, hạ tầng GPU và nợ kỹ
thuật — vì trước tài liệu này chúng nằm rải ở sáu chỗ và không ai đọc được thứ tự.

⚠️ **Cột "Ai" là phần quyết định đọc được hay không.** Ba việc cần chủ sản phẩm, và
chúng **chặn** phần còn lại — nên chúng ở trên cùng.

---

## 0. Trạng thái lúc chốt

| | |
|---|---|
| Ảnh (H37) | G4 · G5 · G9 **đóng**; L1–L7 **xong**; 4 cổng **mở trong mã**; cờ `image.ltt` **đã bật trong `app.env`** |
| Ảnh — còn | **chưa deploy**, nên chưa có job nào đi thật từ ngoài vào |
| LLM (H38) | **đang bán**, ba cửa chạy thật, tiền khớp từng credit |
| Card 3090 máy B | HiDream **và** Qwen vẫn dùng chung — 18.450 + 19.237 = **37.687 MB / 24.576 MB** |
| Card máy A | 2 × 5060 Ti, cả hai khoẻ, **card thứ hai nằm không** |
| Gate đầy đủ | vòng 3 đang chạy; vòng 2 được **14/15**, pytest **1 lỗi đã sửa** |

---

## 1. 🔴 Chặn — cần chủ sản phẩm

| # | Việc | Vì sao nó chặn |
|---|---|---|
| **P1** | **Deploy.** Cần Administrator + bấm UAC. Cờ `image.ltt` đã bật, deploy sẽ nướng lại env. | Không deploy thì toàn bộ H37 hôm nay **chưa tới khách**: mã sửa lỗi tiền, hai phép thăm dò, giá mới, `/gia-api` — đều chỉ nằm ở thư mục nguồn. |
| **P2** | **Chạy đè với dự án video một lượt** để xác minh cổng render báo *bận* chứ không báo *hỏng* | Chốt duy nhất của Đợt B chưa đóng. **Không** đóng được bằng lô đo của riêng ta — cần dự án video chạy thật cùng lúc. |
| **P3** | **Luật WAF Cloudflare** cho `/api/v1/*`: bỏ kiểm bot | Đã đo 24/08: `User-Agent` mặc định của `urllib` bị CF trả **403** trước khi tới máy chủ. Khách dùng thư viện chuẩn sẽ dính. |

⛔ **P1 phải xong trước mọi việc ở mục 2.**

---

## 2. Đóng H37 — nghiệm thu thật

| # | Việc | Đạt khi | Ai |
|---|---|---|---|
| **A1** | Chạy `tools/nghiem_thu_anh_e2e.py chuan_bi` rồi `chay` — **một job ảnh thật đi từ ngoài vào** qua `https://app.lttstudios.com/api/v1` | job `succeeded`, có `image_keys` tải về được, và **credit trừ khớp từng đơn vị** với `credit_cost` | tôi |
| **A2** | Đối soát tay: báo giá → giữ chỗ → quyết toán → hoàn | `charged` ≤ báo giá, và bằng số ảnh **thật sự** nhận | tôi |
| **A3** | Điền một dòng vào mục 4 của `APP_API_COVERAGE_FINAL.md` | có bằng chứng E2E, không còn "chưa nghiệm thu" | tôi |
| **A4** | Thu hồi khoá nghiệm thu (`... don`) | khoá tiêu tiền không nằm lại | tôi |

⚠️ **A1 không thay được bằng test.** H38 có 739 test xanh và vẫn để lọt lỗi
`VARCHAR(36)` tới đúng lượt gọi thật đầu tiên — SQLite không ép độ dài, PostgreSQL
ép. Đường ảnh **chưa từng** chạy thật từ ngoài vào bao giờ.

---

## 3. 🔴 Trọng tài VRAM — nay là việc BẮT BUỘC

D-057 đóng đường tách hai model ra hai máy. Nên chúng **vẫn dùng chung một card**,
và phép cộng vẫn vượt trần. Chi tiết + số đo ở
[`ANH_NOI_BO/CHIA_GPU_HAI_MODEL.md`](ANH_NOI_BO/CHIA_GPU_HAI_MODEL.md).

| # | Việc | Trạng thái |
|---|---|---|
| **V1** | Gọi `llama-swap /unload` **trước** khi gửi prompt | ✅ **XONG, đã đo thật**: đuổi mất **4,0 giây** |
| **V2** | **Chờ và XÁC MINH** VRAM xuống dưới ngưỡng mới gửi | ✅ **XONG.** Không đọc được VRAM ⇒ **từ chối**, không chạy mù |
| **V3** | Sau job, chờ 60 giây rảnh rồi `POST ComfyUI /free` | ✅ **XONG, đã đo thật**: 17,5 GB → **811 MB** |
| **V4** | Số đo VRAM **và RAM** *trong lúc* job chạy | ✅ **XONG** — nằm trong `do_duoc` của kết quả job |
| **V5** | ~~Hạ `ttl` của Qwen 1.800 → 600~~ | 🔴 **BỊ BÁC (D-058)** — xem dưới |

**Đã xác minh trên máy B**, hai chu kỳ lặp lại được (D-058):

```
778 MB (rỗng) → 19.491 MB (Qwen giữ) → "da bao llm nha card, cho 4.0s"
             → 17.5xx MB (HiDream vẽ 111 s) → 60 s rảnh → 811 MB (trả card)
```

### 🔴 V5 bị bác, và chính việc xây xong cho thấy vì sao

`ttl` từng là **cơ chế duy nhất** trả card cho ảnh — nên nó phải ngắn. Nay cổng
render **chủ động đuổi** khi cần. Cho nên `ttl` chỉ còn quyết định *"Qwen giữ card
bao lâu khi KHÔNG ai cần"* — và khi không ai cần thì giữ **không tốn gì**.

Hạ `ttl` chỉ đổi được một thứ: khách LLM trả **18 giây nạp lại** thường xuyên hơn,
để đổi lấy một card rỗng mà không ai xin.

⇒ **Một cơ chế tốt hơn làm một cơ chế cũ thành vô nghĩa. Đừng làm cả hai.**

### Hai chỗ hỏng tìm được nhờ **chạy thật**, không nhờ test

| | Hỏng gì | Đã sửa |
|---|---|---|
| **①** | Đuổi **thành công** không để lại dấu vết nào trong log — hỏi *"vì sao phiên LLM của tôi chậm lúc 13:50"* thì không có gì chỉ ra | ✅ nay ghi `da bao llm nha card, cho 4.0s, VRAM con 778 MB` |
| **②** | Cổng **không đọc được** `gateway.env` mới: nssm nướng env lúc cài. Bẫy này đã cắn dự án **hai lần** | ✅ `main.nap_env()` — cổng tự đọc, không ghi đè biến cấp cao hơn |

⚠️ **Một bẫy về THỨ TỰ đã dính, ghi lại để không ai xếp lại như cũ.** Bản đầu đặt
`xin_card` **SAU** chốt bận. Chốt bận coi *"VRAM còn ít"* là bận, nên khi Qwen giữ
19 GB thì cổng trả 429 ngay và **không bao giờ đi bảo Qwen nhả** — trọng tài thành
mã chết. Thứ tự đúng: **giữ suất → xin card → hỏi bận**.

Và test đầu tiên cho nó **xanh vì lý do sai**: chạy 0,58 giây trong khi hạn chờ là
45 — bằng chứng `xin_card` chưa hề được gọi.

Số đo để cân chính sách (đo 24/08):

| | Nhả | Nạp lại |
|---|---|---|
| HiDream | 0,2 s | **0,8 s** (0,7 % một job) |
| Qwen | 0,7 s | **18 s** (card sạch) |

Bất đối xứng **22 lần** ⇒ chính sách **không đối xứng**: ảnh nhả sau mỗi job; LLM
giữ thường trú và chỉ bị đuổi khi có job ảnh.

---

## 4. GPU máy A — vẫn còn việc, chỉ không phải cho ảnh

D-057 dừng việc **sinh ảnh** trên máy A. Nhưng `taoclipngan` (whisper + YOLO) và
`upscalevideo` **đã** dùng GPU ở đó, và **card thứ hai đang nằm không**.

H23 (bộ nhớ dự án) đã chỉ ra bốn chỗ **hỏng ngầm** khi có 2 GPU, tất cả còn nguyên:

| # | Chỗ | Hỏng thế nào |
|---|---|---|
| **G1** | `apps/upscalevideo/autotune.py` | `splitlines()[0]` ⇒ **chỉ thấy GPU 0**; `_TOTAL_MB_FALLBACK` viết cứng 16311 |
| **G2** | `apps/autosubvideo/whisperx_runner.py` | `device="cuda"` ⇒ **luôn `cuda:0`** |
| **G3** | `job_worker.py` | một tiến trình ⇒ một job một lúc ⇒ **GPU 2 nằm không** |
| **G4** | — | **không có cơ chế giữ chỗ GPU nào** |

🔴 **Điểm thiết kế, đừng phát minh lại:** *đọc "VRAM còn trống" thôi là SAI* — hai
worker cùng thấy trống, cùng nhận GPU 0, cùng OOM. Phải **giữ chỗ nguyên tử trong
CSDL** theo khuôn `claim → đập nhịp → reclaim_orphans` của hàng đợi job. **Giữ chỗ
trước, chạy song song sau.**

| # | Việc | Đạt khi |
|---|---|---|
| **G5** | Chốt `nvidia-smi -L` **phải thấy 2 GPU**, chạy trong vòng bảo trì | liên kết driver card 2 mong manh (`oem3.inf` không liệt kê nó) — mất nó là mất nửa năng lực, **im lặng** |
| **G6** | Làm G4 (giữ chỗ nguyên tử) rồi G1/G2 | hai app trên dùng được cả hai card |

⚠️ Mục này **không chặn** H37 và H38. Nó là năng lực đang bỏ không, không phải một
sự cố.

---

## 5. H38 — việc còn nợ, chủ sản phẩm đã hoãn có chủ ý

| # | Việc | Ghi chú |
|---|---|---|
| **L1** | Đi hết luồng bằng **một tài khoản mới toanh**: trang giá → đăng ký → nạp credit → tạo khoá → gọi lần đầu | ⛔ **không** được làm bằng tài khoản admin — admin có sẵn credit, sẵn quyền, sẵn hiểu biết |
| **L2** | Phiên thật **Claude Code CLI** + **Claude Desktop** có gọi tool | máy này không có hai công cụ đó |
| **L3** | **Điều khoản sử dụng** cho API | chủ sản phẩm quyết nội dung; tôi soạn nháp |
| **L4** | Thu tường lửa máy B về **một** IP | thiết lập bảo mật |
| **L5** | Xoay khoá provider | đã có quy trình, chưa chạy định kỳ |

---

## 6. Nợ kỹ thuật — trả khi đi ngang qua, không lập đợt riêng

| # | Việc | Vì sao chưa làm ngay |
|---|---|---|
| **N1** | Đổi tên `apps/ltt_llm` → `apps/chatnoibo` (đối xứng với `anhnoibo`) | Đó là **migration**, không phải rename: slug nằm trong `job_type` **đã lưu**, và app **đang bán**. Hiện đang được miễn trừ trong `test_60` với lý do viết rõ. |
| **N2** | `apps/vps`: xếp loại lưu trữ 5 bảng là **TẠM**, chủ H39 phải xác nhận | Hạn của `vps_ip` có **hệ quả pháp lý** — lịch sử "IP nào, của ai, lúc nào" là thứ duy nhất trả lời được yêu cầu về lạm dụng. |
| **N3** | `test_221` trên một bucket R2 vứt đi | Chặn bởi một quyết định hạ tầng, không bởi code. |
| **N4** | G5b (chuỗi nâng chất ảnh: upscale/restore + VLM tự loại) | Chỉ làm khi có khách và có phàn nàn cụ thể. |
| **N5** | G11 (giám sát chất lượng ảnh thường trực) | Sau khi có khách thật. |

---

## 7. ⛔ Cái KHÔNG làm, và lý do

| Không làm | Vì sao |
|---|---|
| Tải bản model thấp hơn (FP8/GGUF) cho ảnh | **D-057.** Chủ sản phẩm quyết không hạ độ chính xác. |
| Chuyển sinh ảnh sang máy A | **D-057.** `bf16` không vừa 16 GB, và Llama-3.1-8B trong bộ mã hoá đã lấp kín một card. Mở lại cần **phần cứng ≥ 24 GB**, không phải một cách xếp encoder khác. |
| Chuyển Qwen sang máy A | 3090 nhanh gấp ~2 lần (băng thông 936 so với 448 GB/s), và 64K đã vừa trên 3090. Trả một nửa tốc độ cho thứ không cần. |
| Chạy thêm lô đấu Gemini | **D-046.** Không còn lựa chọn nào để đổi ⇒ điểm số không mua được gì. |
| Mở lại phép so 36 bước | **D-054.** Muốn mở lại phải là **phép kiểm tương đương**, không phải chạy lại phép cũ. |
| Cascade sang đám mây khi máy B bận | **D-010.** Khách trả tiền cho `image.ltt` mà nhận Gemini là bán sai hàng. |
| Đưa việc có chữ tiếng Việt sang `image.ltt` | **D-048.** Ngoài phạm vi, đã chấp nhận. |

---

## 8. Thứ tự làm, một dòng

```
V1..V4 trọng tài VRAM  ✅ XONG (D-058)
        ↓
P1 deploy (chủ sản phẩm)  →  A1..A4 nghiệm thu ảnh thật
        ↓
P2 (chủ sản phẩm) đóng Đợt B của H37
        ↓
G5..G6 (GPU máy A)  ·  L1..L5 (H38)
```

**P3 (WAF)** làm được bất cứ lúc nào và nên làm sớm — nó rẻ và nó đang chặn khách
dùng thư viện chuẩn.

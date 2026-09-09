# KẾ HOẠCH THỰC THI P01 — model, dung lượng ổ đĩa, và ma trận đo

Viết 2026-09-06, trả lời hai câu của chủ dự án và dựng kế hoạch chạy **một lượt
là đủ**.

⛔ Mọi con số dưới đây đo từ **HuggingFace API**, **RunPod S3** và **mã nguồn
WanGP tại SHA ghim** — không con số nào chép từ tài liệu.

---

## 1. Câu hỏi 1 — WanGP dùng model đầy đủ hay bản rút gọn?

**Dùng model ĐẦY ĐỦ. Bản rút gọn là một lựa chọn riêng, không phải mặc định.**

`defaults/t2v_2_2.json` tại SHA ghim khai đúng **`Wan2.2 Text2video 14B`** —
chính model V3 dùng. Và danh sách `URLs` xếp **bf16 (đầy đủ) TRƯỚC**, rồi mới
tới hai biến thể INT8:

```
wan2.2_text2video_14B_high_mbf16.safetensors              <- day du
wan2.2_text2video_14B_high_quanto_mbf16_int8.safetensors  <- INT8
wan2.2_text2video_14B_high_quanto_mfp16_int8.safetensors  <- INT8
```

⇒ **Bản đầy đủ luôn có sẵn.** `--quantize-transformer` mặc định `True`, nhưng
tắt được.

### Ba tầng "rút gọn" khác nhau — đừng gộp làm một

| Tầng | Là gì | Ảnh hưởng chất lượng | Ở WanGP |
|---|---|---|---|
| **Lượng tử hoá INT8** | cùng trọng số, nén lại | nhỏ — **phải đo** | mặc định, tắt được |
| **LoRA tăng tốc** (Lightning 4–8 bước thay vì 20+) | đổi chất lượng lấy tốc độ — **thật sự mất** | đáng kể | **định nghĩa RIÊNG** (`i2v_2_2_Enhanced_Lightning_v2.json`), không phải mặc định |
| **Model 1.3B / chưng cất** | trọng số khác hẳn | lớn | **định nghĩa RIÊNG** (`t2v_1.3B.json`) |

⇒ Mặc định `t2v_2_2` là **nhánh chất lượng**, không phải nhánh nhanh. Khớp với
`V-013` của V3: chọn 20 bước, bác đường fp8 4 bước.

### ⭐ Và một món quà không ngờ: tham số chuẩn đã có sẵn

`defaults/t2v_2_2.json` chứa nguyên bộ tham số sản xuất:

```json
"guidance_phases": 2, "switch_threshold": 875,
"guidance_scale": 4, "guidance2_scale": 3, "flow_shift": 12
```

🔴 **`flow_shift: 12`.** V3 phải đào ra con số này bằng tay và ghi lại:
*"shift lấy của **tác giả model** (T2V **12,0**, không phải 5,0 của template)"*.
WanGP **đã mã hoá sẵn** đúng giá trị đó. (`i2v_2_2` thì `flow_shift: 5` — khác
nhau theo tác vụ, đúng như V3 phát hiện.)

⇒ **Phần lớn "Verified Baseline Profile" của P02 đã có sẵn, miễn phí, trong
`defaults/`.** Một mảng việc của P02 bị xoá trước khi bắt đầu.

---

## 2. Câu hỏi 2 — anh nghi ngờ con số 66 GB, và anh ĐÚNG

Con số 66,58 GB tôi đưa ra **chỉ đúng cho INT8, hai chế độ**. Đó là một **lựa
chọn chưa ai chốt**, và tôi đã trình bày nó như thể là con số duy nhất. Sai của
tôi.

### Bảng dung lượng thật (HuggingFace API, 06/09)

| Thành phần | bf16 đầy đủ | INT8 |
|---|---:|---:|
| t2v 2.2 (high + low) | **57,90** | 29,80 |
| i2v 2.2 (high + low) | **57,90** | 29,80 |
| VACE Fun A14B — control (high + low) | **71,04** | 37,34 |
| umt5-xxl encoder | 11,36 | 6,73 |
| Wan2.1 VAE | 0,25 | 0,25 |

### Năm kịch bản, đối chiếu với chỗ trống hiện có

Ổ đĩa: 300 GB cấp · **183,1 GB đang dùng** · **116,9 GB trống**.
Cộng thêm chi phí cố định: WanGP + venv torch trên `/workspace` **~15 GB**, kết
quả + tệp tạm **~10 GB**.

| # | Kịch bản | Model | + 25 GB | Vừa 116,9 GB? |
|---|---|---:|---:|---|
| 1 | INT8, t2v + i2v | 66,58 | 91,6 | ✅ vừa |
| 2 | INT8, t2v + i2v + control | 103,92 | 128,9 | ❌ **thiếu 12 GB** |
| 3 | **bf16, t2v + i2v** | 127,41 | 152,4 | ❌ **thiếu 35 GB** |
| 4 | **bf16, t2v + i2v + control** | 198,45 | 223,5 | ❌ **thiếu 107 GB** |
| 5 | cả bf16 lẫn INT8, cả ba chế độ | 302,12 | 327,1 | ❌ **không vừa cả ổ 300 GB** |

🔴 **Chỉ kịch bản hẹp nhất mới vừa.** Ngay khi muốn chất lượng đầy đủ, hoặc thêm
chế độ control, chỗ trống hiện có **không đủ**.

⇒ Câu *"không cần xoá"* của tôi ở lượt trước đứng trên giả định INT8 hai chế độ.
Anh bác đúng chỗ.

### Xoá xong thì được gì

300 GB trống ⇒ **kịch bản 4** (bf16, cả ba chế độ) = 223,5 GB, **còn dư 76,5 GB**
cho LoRA, upscaler, prompt enhancer và kết quả.

⚠️ Kịch bản 5 vẫn không vừa **kể cả khi xoá sạch**. Nên vẫn phải chọn: bf16
**hoặc** INT8 làm bản chính, không giữ cả hai cho cả ba chế độ.

---

## 3. Quyết định: XOÁ — và ba điều kiện an toàn đã thoả

Lý lẽ của chủ dự án đứng vững: *"code vận hành ComfyUI ta chưa làm gì, sau này
chỉ mất time tải"*. Kiểm lại thì còn nhẹ hơn thế.

| Điều kiện | Trạng thái |
|---|---|
| ① Tái tạo được chính xác | ✅ `BANG_KE_MONG_DOI.json` có đủ **`repo` + `revision` ghim + `sha256` + `byte`** cho cả 8 tệp |
| ② Công cụ tải lại còn nguyên | ✅ `tools/video_nap_model.py` — `tao`/`theo-doi`/`xoa`/`doi-chieu`, đã chạy thật 8/8 tệp, 0 lỗi |
| ③ Bên dùng nó đã dừng | ✅ V3 dừng phát triển 06/09 (`P00-D-07`) |

**Giá của một lần sai:** tải lại ≈ **63 phút + ~$0,20** (Pod CPU, không GPU).
Đó là mức rủi ro chấp nhận được cho **107 GB** chỗ trống.

⛔ **Nhưng xoá tệp KHÔNG tiết kiệm tiền.** RunPod tính theo **dung lượng cấp**
(300 GB), không theo dung lượng dùng — ổ rỗng vẫn $21/tháng. Ta xoá để lấy
**chỗ**, không phải để tiết kiệm. Việc tiết kiệm tiền là `O-007` (thu nhỏ hoặc
bỏ hẳn volume), quyết ở P06.

### ✅ Phép kiểm B1 đã chạy (đọc mã, $0) — KHÔNG dùng lại được

Câu hỏi: WanGP có nạp được thẳng tệp ComfyUI đang nằm trên ổ đĩa không, để khỏi
tải lại 127 GB?

**Trả lời: không, và lý do rất cụ thể.**

`wgp.py::download_models` (dòng 3638) **có** tìm tệp cục bộ trước khi tải:

```python
local_model_filename = fl.get_local_model_filename(model_filename, extra_paths=force_path)
if local_model_filename is None and len(model_filename) > 0:
    ...  # chi tai khi KHONG tim thay
```

Nhưng `shared/utils/files_locator.py::get_local_model_filename` (dòng 229) khớp
**theo TÊN TỆP** lấy từ URL, không theo nội dung. Mà hai bên đặt tên khác hẳn:

| | Tên tệp |
|---|---|
| ComfyUI (đang có trên ổ) | `wan2.2_t2v_high_noise_14B_fp16.safetensors` |
| WanGP mong đợi | `wan2.2_text2video_14B_high_mbf16.safetensors` |

⇒ Không khớp ⇒ WanGP sẽ **tải mới**, bỏ qua 183 GB đang nằm đó.

Và kể cả đổi tên cũng chưa chắc chạy: tiền tố **`m`** là định dạng đóng gói của
**`mmgp`** (đọc bằng `safetensors2`, không phải `safetensors` chuẩn), mang theo
siêu dữ liệu lượng tử hoá mà bản ComfyUI không có.

⭐ Ghi lại cho phiên sau: **`extra_paths` / `force_path` có tồn tại** — tức WanGP
*có* cửa để trỏ vào thư mục model ngoài. Cửa đó dùng được khi tên tệp đúng chuẩn
của nó. Không phải trường hợp này, nhưng đáng nhớ.

🔴 **Kết luận: 183 GB tệp ComfyUI là chỗ chết trên ổ đĩa với WanGP.** Quyết định
xoá của chủ dự án là đúng, và giờ có bằng chứng chứ không phải phỏng đoán.

---

## 4. Kế hoạch thực thi — sáu bước

| # | Việc | Máy | Tiền | Chặn bởi |
|---|---|---|---|---|
| **B1** | Đọc mã nạp model WanGP: có dùng lại được safetensors của ComfyUI không | máy A | **$0** | — |
| **B2** | Chốt kịch bản model (bf16 hay INT8; hai hay ba chế độ) → sinh bảng kê mới | máy A | **$0** | B1 |
| **B3** | **Xoá 8 tệp ComfyUI** khỏi volume qua S3, sau khi lưu bảng kê cũ vào kho | máy A | **$0** | B2 |
| **B4** | **Pod CPU** tải bộ model mới vào volume (dùng lại `video_nap_model.py`) | 4 vCPU | **~$0,20** | B3 · **duyệt chi** |
| **B5** | **Pod A100** chạy ma trận đo (mục 5) | A100 80 GB | **~$2,20** | B4 · **duyệt chi** |
| **B6** | Đọc kết quả qua S3 · xoá pod · `kiem-ke` phải trả `pods: []` | máy A | $0 | B5 |

**Tổng chi: ~$2,40. Trần cứng đề nghị $6,00** *(nâng từ $5 vì thêm bước tải)*.

### Điều kiện DỪNG

- không thuê được GPU ở `US-KS-2` (tồn kho **Low**) → dừng, báo, **không** đổi
  sang card đắt hơn nếu chưa hỏi;
- cài WanGP hỏng hai lần liên tiếp → dừng, mang log về, sửa ở máy A;
- chi chạm **$6,00** → xoá pod ngay, báo cáo bằng số đã có.

---

## 5. Ma trận đo — chạy một lượt là đủ

Nguyên tắc: **mọi thứ làm được miễn phí phải xong trước khi đồng hồ GPU chạy.**
Script đo viết sẵn ở máy A, đẩy lên `/workspace` qua S3, Pod chạy bằng
`dockerStartCmd`, kết quả ghi ra `/workspace` — **không cần shell**.

### Nhóm A — Lắp đặt (đầu ra: `Dockerfile`)

| Mã | Đo gì | Cách | Xong khi |
|---|---|---|---|
| A1 | ảnh gốc + CUDA + Python | `nvidia-smi`, `nvcc --version`, `python -V` | ghi vào `moi_truong.json` |
| A2 | **từng lệnh cài + thời gian + mã thoát** | bọc mọi lệnh, ghi `install.log` | log đủ để chép thành `Dockerfile` |
| A3 | dung lượng sau cài | `du -sh` | có số |
| A4 | WanGP khởi động lần đầu mất bao lâu | dấu thời gian quanh `init()` | có số |

### Nhóm B — Model (quyết số phận volume)

| Mã | Đo gì | Xong khi |
|---|---|---|
| B1 | WanGP đặt model ở thư mục nào, tên gì | có cây thư mục |
| B2 | dung lượng tải thật, **đối chiếu dự đoán ở mục 2** | lệch < 5% hoặc giải thích được |
| B3 | thời gian tải trong datacenter | có số |
| B4 | **có nạp được safetensors của ComfyUI không** *(nếu chưa xoá)* | có/không, kèm thông báo lỗi |

### Nhóm C — VRAM: `O-006`, con số đắt nhất

| Mã | Đo gì | Cách |
|---|---|---|
| C1 | VRAM **đỉnh**, profile 4 (mặc định), 1280×720 × 81 khung | `nvidia-smi --query-gpu=memory.used --format=csv -l 1` ghi CSV suốt lượt, lấy **max** |
| C2 | VRAM đỉnh, **profile 3** (nạp trọn) | như trên |
| C3 | VRAM đỉnh, **profile 2** (giữ model ở RAM) | như trên |
| C4 | **RAM hệ thống đỉnh** ở profile 2 | lấy mẫu `MemAvailable` 1 Hz |

🔴 Đích của nhóm này là **một câu**: WanGP chạy 720P trong bao nhiêu GB VRAM?
48 GB thì mọi giờ GPU về sau rẻ đi ~2,2 lần.

### Nhóm D — Thời gian và giá vốn

| Mã | Đo gì | Ghi chú |
|---|---|---|
| D1 | thời gian **nạp model vào VRAM** (lượt nguội) | tách khỏi D2 — gộp là con số vô dụng |
| D2 | thời gian **sinh** 1 video 720P/81 khung/20 bước | chạy **2 lượt, seed KHÁC nhau** |
| D3 | **lượt lặp cùng seed** → phát hiện cache | xem bẫy ① |
| D4 | thời gian **đổi model** t2v → i2v (`O-008`) | đo ở profile 4 **và** profile 2 |

### Nhóm E — Hợp đồng engine (nghiệm thu P01/P02)

| Mã | Đo gì | Mang về |
|---|---|---|
| E1 | `list_model_defs()` | `models.json` |
| E2 | `get_default_settings()` cho `t2v_2_2`, `i2v_2_2` | **chính là Baseline Profile** |
| E3 | `submit_task()` chạy được; `GenerationResult` có gì | `ket_qua.json` |
| E4 | `job.cancel()` giữa chừng | VRAM có nhả? `success == False`? |
| E5 | sự kiện tiến độ có thật | chuỗi event ghi lại |
| E6 | MCP server bật được (`--mcp --mcp-transport streamable-http`) | có/không |
| E7 | khởi động lại tiến trình → model còn trên đĩa | không phải tải lại |

---

## 6. Sáu cái bẫy làm hỏng phép đo

| # | Bẫy | Chặn bằng |
|---|---|---|
| ① | **Cache theo prompt.** V3 mất **$1,29** vì chạy hai lượt đồ thị y hệt, lượt 2 trả cache và ra 0 giây | D3 là **phép đối chứng có chủ đích**: chạy lặp cùng seed để *biết* cache có tồn tại không. Mọi lượt khác **đổi seed**. |
| ② | Đo VRAM sau khi tiến trình chạy | `nvidia-smi -l 1` phải bật **TRƯỚC** |
| ③ | Ghi log vào ổ container → pod xoá là mất sạch | **mọi thứ ghi vào `/workspace`** |
| ④ | `minRAMPerGPU` mặc định **8 GB** làm C3/C4 vô nghĩa | đặt **64 GB** lúc tạo pod |
| ⑤ | Gộp ba pha thời gian (tải · nạp · sinh) làm một | dấu thời gian tách từng pha |
| ⑥ | Đo bằng cấu hình khác V3 ⇒ không so sánh được | ghim **1280×720 · 81 khung · 20 bước · flow_shift 12** |

## 7. Thứ phải mang về

`install.log` · `moi_truong.json` · `vram.csv` · `ram.csv` · `timing.csv` ·
`models.json` · `settings_t2v_2_2.json` · `settings_i2v_2_2.json` ·
`ket_qua.json` · 2–3 tệp mp4 mẫu · `hoa_don.json` (đọc lại sau 60 phút).

⇒ Tất cả nằm trên `/workspace`, đọc về qua S3 **sau khi pod đã xoá**.

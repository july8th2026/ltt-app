# KẾ HOẠCH ĐO LƯỜNG — mượn bộ đo của cộng đồng, không tự dựng

> Chủ dự án, 05/09/2026: *"Bộ đo cần được tối ưu danh sách công cụ đo, nên lấy
> bộ đo từ cộng đồng đã xây dựng thay vì tự suy"*.
>
> Tệp này chốt **đo cái gì · bằng công cụ nào · chạy ở máy nào · tốn bao nhiêu**,
> và quan trọng không kém: **cái gì không đo**.

---

## 0. Sai lầm mà tệp này sửa

`P07`/`P08` của bản kế hoạch cũ nói *"đo chất lượng từng mode"* và *"so mù bf16
vs fp8"* nhưng **không nói đo bằng gì**. Một phép đo không nêu công cụ thì đến
lúc chạy sẽ thành **tôi tự chấm bằng mắt** — và đó chính là *"tự suy"*.

⭐ Hai lỗi cùng một gốc, đã gặp thật ở kho này:

- `docs/model-nha-thua-gemini-trong-so-mu` — so mù cần một **bộ chấm**, và bộ
  chấm tự dựng thì chỉ đo được thứ người dựng nghĩ tới.
- `docs/BAY_TRONG_CONG_CHAT_LUONG.md` — một phép đo tự viết hay đo **chính giả
  định của nó**.

⇒ Luật cho V1: **mọi con số chất lượng phải ra từ một bộ đo công khai, có bài
báo, có người khác dùng.** Nếu không có bộ đo công khai cho một câu hỏi thì
**không đặt câu hỏi đó ở V1**.

---

## 1. 🔑 Tách hẳn hai loại đo — chúng khác nhau về máy, về tiền, về công cụ

| | **Đo vận hành** | **Đo chất lượng** |
|---|---|---|
| Trả lời | nhanh bao nhiêu, tốn bao nhiêu | video có đẹp/ổn định không |
| Chạy ở | **C-CLOUD** (bắt buộc, GPU thuê) | **A-CONTROL** (miễn phí) |
| Tốn | tiền thật theo giây | **$0** |
| Công cụ | ComfyUI `/history` + RunPod `/billing` | **VBench** |
| Cần GPU thuê? | có | **không** |

⭐ **Đây là ý quan trọng nhất của cả tệp: chấm điểm KHÔNG cần A100.**

Video sinh ra là tệp `.mp4`. Chấm nó chỉ cần các model đánh giá cỡ nhỏ (CLIP,
DINO, RAFT, aesthetic predictor) — máy A chạy được. Trước đây tôi ngầm gộp
"sinh" và "chấm" vào cùng một envelope GPU thuê; tách ra thì **toàn bộ phần
chất lượng rơi khỏi ngân sách cloud**.

⇒ Hệ quả bắt buộc: **lưu nguyên video và nguyên tham số của mọi lượt sinh**, rồi
mới chấm. Chấm lại thì miễn phí; sinh lại thì **~$2,08 một lượt** (`V-012`).

### ⚠️ Giới hạn của mẹo này — một phiên khác đã đo được, chép về đây

Phiên H44 (ChatLTT V3) dùng đúng cách tách này cho bộ đo tool-calling: lưu nguyên
văn phản hồi rồi mới chấm. Khi một chỉ số FAIL 77,9 %, họ mở lại **90 phản hồi
đã lưu**, soi từng lượt trượt **hết 0 giây GPU**, và thấy cả 8 lượt trượt là lỗi
**của phép đo**, không của model.

Nhưng lần đó **chính câu hỏi** sai (viết tiếng Việt không dấu, model đọc
`"dong dat"` thành *"đồng yên"* — một cách đọc hợp lệ), nên vẫn phải **sinh lại**.

⭐ ⇒ Tách "sinh" khỏi "chấm" cứu được **chẩn đoán**, **không** cứu được **bản
sửa** khi lỗi nằm ở đầu vào. Với ta: prompt và seed của Đ2 phải được rà kỹ
**trước** khi đốt 2,3 giờ GPU, vì một prompt tồi thì mọi lượt chấm lại đều vô
nghĩa và tiền đã tiêu rồi. ⭐ Và nay mỗi lượt sinh tốn ~$2,08 chứ không phải
~$0,07 — cùng một sai sót, cái giá gấp ba mươi lần.

---

## 2. Bộ đo chất lượng — **VBench**, không tự dựng

| | |
|---|---|
| Kho | `Vchitect/VBench` |
| Giấy phép | **Apache-2.0** ✅ bán được |
| Uy tín | **CVPR 2024 Highlight**, 1.759 ★, cập nhật **2026-08-21** |
| Cài | `pip install vbench` (có trên PyPI) |
| Hỗ trợ video của mình | ✅ `--mode=custom_input` — đúng thứ ta cần |
| Có bản I2V riêng | ✅ `vbench2_beta_i2v` |

### Chọn 7 trong 16 chiều — và lý do chọn đúng bảy chiều đó

VBench có 16 chiều T2V. **Chín** chiều trong đó đo *độ khớp với prompt*
(`object_class`, `color`, `human_action`, `spatial_relationship`, `scene`,
`multiple_objects`, `temporal_style`, `appearance_style`, `overall_consistency`)
và chúng **bắt buộc dùng bộ prompt chuẩn của VBench** để công bằng giữa các model.

Ta **không** xếp hạng model — Wan2.2 đã được xếp hạng rồi. Ta hỏi *"đường ống của
ta có dựng đúng không"*. Câu đó chỉ cần **bảy chiều nội tại video**, chạy được
trên **bất kỳ** video nào ta sinh, với **prompt của chính ta**:

| Chiều | Bắt lỗi gì của đường ống |
|---|---|
| `subject_consistency` | chủ thể biến hình giữa các khung — sai LoRA, sai shift |
| `background_consistency` | nền trôi |
| `temporal_flickering` | nhấp nháy — dấu hiệu kinh điển của sai VAE hoặc sai bước |
| `motion_smoothness` | chuyển động giật |
| `dynamic_degree` | 🔑 **video đứng im** — lỗi im lặng nguy hiểm nhất, mắt người lướt qua vẫn thấy "đẹp" |
| `aesthetic_quality` | chất lượng thẩm mỹ |
| `imaging_quality` | mờ, nhiễu, artefact nén |

⛔ **Không dùng bảy số này để so với model khác.** Chúng chỉ có nghĩa khi so
**ta với chính ta**: cùng prompt, cùng seed, đổi một tham số. Dùng chúng để xếp
hạng là dùng sai bộ đo — VBench nói rõ điều đó ở mục *"A Side Note"* trong README.

### ⚠️ Ba ràng buộc cài đặt, không được bỏ

1. **KHÔNG cài `vbench` vào venv sản phẩm.** README VBench chỉ CUDA ≤ 12.1;
   máy A đang chạy torch **cu128**. Cài chồng là hỏng cả `apps/taoclipngan`
   (whisper/YOLO) lẫn `render_gateway`. ⇒ **venv riêng**, ví dụ
   `C:\LTTVBench\venv`, ngoài cây kho.
2. **Sau rào `LTT_TEST_NANG`.** VBench nạp model thật; theo luật ở
   `CLAUDE.md` toàn cục, test nạp model thật phải nằm sau rào đó.
3. **Hỏi `python tools\cua_so_yen.py trang-thai` trước mỗi lượt chấm.** Máy này
   10 lõi vật lý dùng chung cho mọi phiên.

---

## 3. Bộ đo vận hành — **không cài gì thêm**

Cả hai nguồn đã có sẵn và đều là nguồn chính chủ:

| Số cần | Đọc ở đâu | Ghi chú |
|---|---|---|
| Thời gian từng node | ComfyUI `GET /history/{prompt_id}` | có sẵn trong ComfyUI, không cần gói ngoài |
| Thời gian cả lượt | chênh lệch dấu thời gian của job | |
| **Tiền thật** | RunPod `GET /v1/billing/endpoints` → `amount`, `timeBilledMs` | `cloud_api.chi_tieu_compute_thang` đã viết |
| Khởi động nguội | `timeBilledMs` trừ thời gian thực thi | phần chênh **chính là** cold start |
| Đỉnh VRAM | `torch.cuda.max_memory_allocated()` in ra log worker | một dòng trong handler |

⛔ **Đừng thêm Prometheus/Grafana/W&B cho V1.** Bốn phép đo, mỗi phép chạy một
lần — một tệp CSV là đủ, và một hệ giám sát dựng cho bốn điểm dữ liệu là công cụ
tự nó thành việc.

---

## 4. Bảng phép đo cuối cùng — bốn phép, và chỉ bốn

| # | Đo gì | Bằng gì | Máy | GPU thuê |
|---|---|---|---|---|
| **Đ1** | Khởi động nguội: nạp `cau_hinh_san_xuat.chuoi_nap_gb(mode)` từ volume US-KS-2 | `timeBilledMs` − thời gian thực thi | C-CLOUD | ~0,2 h |
| **Đ2** | Wall-clock **ba mode × một lượt**, cấu hình sản xuất | ComfyUI `/history` + `/billing` | C-CLOUD | ~2,3 h |
| **Đ3** | **Đỉnh VRAM thật của fp16 ở 720P** trên 80GB | `torch.cuda.max_memory_allocated()` | C-CLOUD | gộp vào Đ2 |
| **Đ4** | Bảy chiều VBench trên video của Đ2 | `vbench evaluate --mode=custom_input` | **A-CONTROL** | **0** |

**Tổng GPU thuê ≈ 2,3 giờ** (envelope `P07` = 3,0 kể cả biên). So với 16,2 giờ
mà `P07 + P08` từng chiếm — nhưng xem cảnh báo ngay dưới: con số này **không**
giảm vì cắt gọt, và nó **tăng** so với bản ba bậc.

### Đ2 đo **một** cấu hình × ba mode — `V-012`

⛔ Bản trước của mục này đo **ba bậc** (Nháp / Cân bằng / Chất lượng). `V-012` gỡ
hẳn hai bậc dưới: *"Hệ thống của ta chỉ tồn tại 1 đường duy nhất là mạnh nhất so
với cấu hình máy."* Không còn bậc để so.

Tham số lấy từ `platform_core/video_gen/cau_hinh_san_xuat.py` — **không chép lại
vào đây**, vì chép lại chính là cơ chế đã hỏng ba lần trong hai ngày.

**3 mode × 1 lượt.** Một lượt ở cấu hình sản xuất (1280×720, 40 bước, không LoRA)
ước ~46 phút ⇒ **≈ 2,3 giờ**, cộng biên thành 3,0 (`ngan_sach.ENVELOPE_PHA_GIO`).

⭐ Ghi rõ vì nó phản trực giác: **bỏ hai bậc làm phép đo ĐẮT LÊN**, không rẻ đi.
Ít hạng mục hơn, nhưng mỗi hạng mục nặng gấp ~30 lần đường chưng cất.

⛔ **Đ3 không còn hỏi "L40 48GB có đủ không".** `V-010` giết giả thuyết đó: fp16
ở 720P đỉnh **59,8 GB**, không vừa 48 GB. Câu hỏi mới là fp16/720P có vừa 80 GB
thật không — đọc miễn phí từ chính lượt chạy của Đ2, không tốn thêm giờ nào.

### Đ4 chạy thế nào

```bash
# venv RIENG, khong phai venv san pham
vbench evaluate \
  --videos_path <thu muc mp4 tai ve tu R2> \
  --dimension subject_consistency background_consistency temporal_flickering \
              motion_smoothness dynamic_degree aesthetic_quality imaging_quality \
  --mode=custom_input
```

Đầu ra ghi vào `docs/VIDEO_AI/DO_LUONG_KET_QUA.csv`, một dòng mỗi video, cột
`mode · gpu · seed · giay_chay · usd · <7 chiều>`.

⭐ **Cùng một bảng chứa cả tiền lẫn chất lượng.** Đó là điều kiện để trả lời câu
hỏi thật của `V-003`: *"mỗi giây video bán ra tốn bao nhiêu, và đổi lại được chất
lượng nào"* — hai con số nằm hai tệp thì không ai ghép lại.

---

## 5. Cái **không** đo ở V1, và vì sao

| Không đo | Vì |
|---|---|
| ~~bf16 vs fp8~~ | 🔴 **Lý do cũ đã sai** — tôi viết *"template chính chủ là fp8 nên so bf16 là so đường ta không đi"*. `V-010` lật lại: sản xuất chạy **fp16**, nên nay chính **fp8** mới là đường ta không đi. Không đo, nhưng vì lý do **ngược lại**. |
| Quét tham số (bước, cfg, shift) | template đã chốt; đổi là rời khỏi đường cộng đồng |
| Xếp hạng với Kling / Runway / Veo | ta không bán "model tốt nhất", ta bán **năng lực sản xuất**; và bộ đo cho việc đó là **khách hàng**, không phải benchmark |
| 9 chiều VBench cần prompt suite | cần bộ prompt chuẩn + nhiều video; không trả lời câu hỏi của ta |
| VBench-2.0 (18 chiều, suy luận vật lý) | dành cho nghiên cứu model, không cho kiểm đường ống |
| Chấm điểm bằng mắt tôi | ⛔ đó đúng là thứ tệp này sinh ra để chặn |

---

## 6. Điều kiện đóng

| | |
|---|---|
| Đ1–Đ3 | có số thật trong `DO_LUONG_KET_QUA.csv`, có `usd` đọc từ hoá đơn |
| Đ4 | bảy chiều VBench có số cho **cả ba mode** |
| Giá vốn | `V-003` thay ước tính $0,0135/giây bằng **số đo** |
| Chốt GPU | `V-008` giữ A100 hay đổi sang L40 — **quyết bằng Đ3**, không bằng suy luận |

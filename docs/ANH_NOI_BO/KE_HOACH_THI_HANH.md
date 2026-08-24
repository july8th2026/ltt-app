# H37 — Kế hoạch thi hành, có cổng chất lượng ≥ 9/10

**Bản 2 — 2026-08-21.** Viết lại sau khi chủ dự án chốt: **"tập trung về chất lượng
ảnh, không đánh về số lượng"** (D-010), và sau khi G2 loại Klein 9B rồi G-nghiên-cứu
đưa **HiDream-O1-Image** lên làm model đích (D-009).

Kiến trúc và lý do: [`KE_HOACH_H37.md`](KE_HOACH_H37.md) · chấm bộ build pack:
[`PHAN_TICH_BUILD_PACK.md`](PHAN_TICH_BUILD_PACK.md) · chia GPU với video:
[`CHIA_GPU_VOI_VIDEO.md`](CHIA_GPU_VOI_VIDEO.md) · giấy phép:
[`LICENSE_NOTES.md`](LICENSE_NOTES.md) · quyết định: [`DECISIONS.md`](DECISIONS.md) ·
sổ chấm: [`CHAM_DIEM.md`](CHAM_DIEM.md).

**Đã xong:** G0 (9,5/10) · G2 (10/10) · **G6** (9,55/10) · **G1** (10/10).
**G3 — KHÔNG QUA lần 1:** trung bình 9,25 nhưng **C4 = 7 < 8** (bốn dấu chân ngoài
dự định trên máy dùng chung, đã khắc phục hết). Số đo cấu hình đích: **92–97 s/ảnh**,
VRAM **16,8 GB**, nhiệt **82–83 °C kèm SW Thermal Slowdown**, **tái lập byte-identical**.
Còn lại: kết luận chất lượng về độ phân giải chuyển sang G4 (1 prompt không đủ).
**Đã làm sẵn phần máy A của G7:** ba script deploy, thuần ASCII, không BOM.

---

## 0. Chất lượng là trên hết — điều đó đổi những gì

Bản 1 của kế hoạch này viết cho một sản phẩm cân bằng chi phí/tốc độ/chất lượng.
Chủ dự án đã chốt khác. Sáu thay đổi, tất cả đều có hệ quả thật:

| | Bản 1 | **Bản 2 — chất lượng trên hết** |
|---|---|---|
| Cấu hình đích | profile cân bằng, chọn theo 5 tiêu chí | **cấu hình đẹp nhất chạy được**: `base` bf16, bucket ~4 MP |
| Thời gian/ảnh | **tiêu chí chọn** | **ràng buộc khả thi** — ghi lại, đặt trần, không dùng để loại cấu hình đẹp hơn |
| Bậc FAST | mục tiêu sản phẩm | chỉ đo để biết bỏ lỡ gì; **chỉ mở nếu so mù không phân biệt được** với `base` |
| Khi GPU bận | **tự động** cascade sang Gemini | **khách tự chọn**. Thay model sau lưng khách là đánh tráo sản phẩm |
| Độ phân giải | tuỳ yêu cầu | **luôn sinh ở bucket huấn luyện ~4 MP**, rồi thu nhỏ về kích thước giao |
| Đối chứng chất lượng | bước cuối (G11), để xác nhận | **kéo lên trước khi mở bán** — nó *quyết định*, không phải *xác nhận* |

**Hệ quả kinh tế phải nói thẳng:** ở ~3 phút/ảnh, máy B ra khoảng **20 ảnh/giờ**, và
còn chia với việc video. Tiền điện vẫn không đáng kể (~50 đồng/ảnh). Cái mất thật là
**khách phải chờ, hoặc phải tự chọn đám mây**. Đó là cái giá của việc không đánh tráo
sản phẩm, và nó được chấp nhận có ý thức ở D-010.

---

## 1. Bộ chấm điểm — và vì sao nó được thiết kế để chống chính tôi

### 1.1 Vấn đề

Tự chấm điểm là cơ chế dễ gian lận nhất trong mọi cơ chế bảo đảm chất lượng. Không
phải vì cố ý, mà vì người chấm là người vừa làm — họ chấm cái họ *định làm*, không
phải cái *đã ra*.

Máy B có sẵn bài học về đúng chuyện này. `scripts/live_check_control_b.py` ghi lại
một phép kiểm từng **báo đạt** trong khi tự in ra bằng chứng ngược lại:

> *"That is the Gate 0 failure this project banned: a verdict that does not read
> what it printed."*

Ba tính chất bắt buộc: **mỗi điểm phải trích một bằng chứng mở ra xem lại được · mỗi
phase phải tự tìm cách bác bỏ chính nó · và blocker thì không chấm điểm, chỉ có đạt
hoặc chặn.**

### 1.2 Sáu chiều chấm

| # | Chiều | Câu hỏi thật |
|---|---|---|
| **C1** | Hoàn thành phạm vi | Đã làm đủ việc đã hứa chưa? Cái nào bỏ, và có nói ra không? |
| **C2** | Bằng chứng | Mỗi khẳng định có trỏ được vào một tệp / dòng log / số đo không? |
| **C3** | Đúng đắn | Số đo lặp lại được không? Test xanh không? Có chỗ nào đúng do may không? |
| **C4** | Không phá thứ đang chạy | Production máy A và việc video máy B còn nguyên không? |
| **C5** | Vận hành được | Khởi động lại thì sao? Hỏng thì báo gì? Log ở đâu? Lùi lại thế nào? |
| **C6** | Tài liệu & quyết định | `DECISIONS.md` có ghi không? Tài liệu 3 tầng có cập nhật không? |

### 1.3 Thang điểm

| Điểm | Nghĩa |
|---|---|
| **10** | Đạt đầy đủ **và** có ít nhất một phép kiểm độc lập xác nhận (test tự động, script kiểm, hoặc quan sát trên trình duyệt thật) |
| **9** | Đạt đầy đủ, có bằng chứng, nhưng phép kiểm do chính tôi chạy tay |
| **8** | Đạt, còn một điểm nhỏ đã biết và đã ghi ra |
| **6** | Đạt trên lời nói — **thiếu bằng chứng trích dẫn được** |
| **4** | Đạt một phần |
| **0** | Không làm, hoặc làm sai |

**Trần điểm cứng, không thương lượng:**

- Khẳng định **không trích được bằng chứng** → chiều đó **tối đa 6**.
- Số đo **chỉ chạy một lần** → C3 **tối đa 8**. Một lần không phải đo.
- Không thử bác bỏ (§1.6) → C3 **tối đa 8**.
- Sửa file trực tiếp trên máy B ngoài đường deploy → C5 **tối đa 4**.
- **Chấm chất lượng ảnh mà không mù** → C3 **tối đa 5**. *(mới ở bản 2)*

### 1.4 Ngưỡng qua phase

```
① trung bình có trọng số ≥ 9,0
② KHÔNG chiều nào < 8      (không cho bù trừ — một chiều yếu là một lỗ thật)
③ KHÔNG blocker nào đỏ     (blocker là nhị phân, không chấm điểm)
```

Điều kiện ② quan trọng ngang ①. Không có nó thì một phase có C4 = 3 ("đã làm gián
đoạn production nửa tiếng") vẫn qua nhờ năm chiều kia 10 điểm.

**Chiều không áp dụng** *(bổ sung 2026-08-21, do chính lần chấm G0 phát hiện)*: nếu
một phase không chạm tới một chiều — ví dụ G0 không sinh mã nên không có C3/C5 —
thì phải **ghi rõ "không áp dụng" kèm lý do** và chia lại trọng số. Không được để
một chiều biến mất im lặng làm mẫu số nhỏ đi. Và: **nếu một phase có từ 3 chiều trở
lên không áp dụng thì điểm của nó không có nhiều ý nghĩa** — nó là bước chuẩn bị,
không phải phase thật. Ghi điều đó ra thay vì khoe một con số cao dễ dãi.

### 1.5 Luật riêng cho việc chấm CHẤT LƯỢNG ẢNH *(mới ở bản 2)*

Vì chất lượng nay là tiêu chí chọn duy nhất, cách chấm nó phải chặt hơn mọi thứ khác.

1. **Luôn mù.** Ảnh đưa ra chấm phải **đổi tên thành mã ngẫu nhiên**, không mang tên
   model/profile/độ phân giải. Lộ nhãn trước khi vote ⇒ **vứt toàn bộ lượt vote đó**.
2. **So từng cặp, không chấm điểm tuyệt đối.** "Ảnh này 7/10" không lặp lại được
   giữa hai ngày. "A hay B hay hoà" thì lặp lại được.
3. ~~**Người chấm là chủ dự án, không phải tôi.** Tôi dựng bộ so sánh, xáo trộn,
   thu phiếu, tính toán. Tôi **không** bỏ phiếu về thẩm mỹ.~~
   🔴 **ĐÃ THAY ngày 24/08 bởi D-052.** Chủ sản phẩm quyết: **máy chấm**, không
   chờ người. Lý do đứng vững: luật cũ biến thời gian ngồi chấm của một người
   thành **đường găng của cả dự án**, và trên thực tế nó đã bị bỏ qua từ lô G6b
   (D-045 ghi rõ *"người chấm: Opus 5"*) — tức là luật đang nằm trên giấy trong
   khi việc thật đi đường khác.

   ⚠️ Nhưng **rủi ro mà luật cũ phòng thì không biến mất**: một mô hình chấm sản
   phẩm của chính mình có động cơ nói rằng nó tốt. Nên đổi cách chặn thay vì bỏ
   chặn — xem D-052. Ba thứ giữ nguyên hiệu lực và **quan trọng hơn trước**:
   mù (§1.5.1), cặp bẫy đo sàn nhiễu (§1.5.4), và đủ mẫu mới kết luận (§1.5.5).
   Thêm một thứ mới: **mỗi lá phiếu quyết đoán phải viết lý do**, và
   `tools/cham_mu.py` **từ chối tính** nếu thiếu.
4. **Cặp bẫy bắt buộc:** trộn vào **10 % cặp A-đấu-A** (cùng model, khác seed).
   *(Làm rõ sau khi viết `tools/cham_mu.py`)* — cặp bẫy **không phải phép đậu/rớt,
   nó là THƯỚC ĐO**. Tỉ lệ người chấm *dám chọn* trên cặp bẫy chính là **sàn nhiễu
   `f`**: mức quyết đoán khi không có gì để quyết. Nếu trên cặp thật họ cũng chỉ
   quyết đoán ngang mức đó (`d ≤ f`) thì **khác biệt giữa hai model nhỏ hơn khác
   biệt giữa hai lần chạy cùng một model** — và mọi con số thắng-thua khi ấy vô
   nghĩa. Công cụ tự tính và tự chặn kết luận.
5. **Đủ mẫu mới được kết luận.** Với 30 cặp, chênh lệch dưới **65/35** là nhiễu.
   Muốn phân biệt hai cấu hình gần nhau cần **≥ 50 cặp**. Nếu không đủ mẫu thì kết
   luận phải ghi là **"chưa phân biệt được"** — đó là một kết quả hợp lệ, không phải
   thất bại.
6. **Kèm bảng lỗi khách quan** bên cạnh phiếu thẩm mỹ, vì có thứ không cần vote:
   chữ sai chính tả · tay/ngón hỏng · vật thể thừa · sai tỉ lệ khung · không bám
   prompt · **mất nhân dạng** (chế độ `subject`) · **đổi phần không được đụng**
   (chế độ `edit`). Những lỗi này **đếm được** và phải đếm.

### 1.5b ⭐ BẮT BUỘC: ĐỌC ẢNH ĐỐI CHIẾU PROMPT trước khi báo bất kỳ số đo nào

*(thêm 22/08 sau D-027 — luật này sinh ra từ một thất bại thật của chính quy trình)*

Trước D-027, quy trình này đã chạy **tám lượt đo, hàng nghìn giây GPU, ba mục quyết
định** về VRAM/nhiệt/số bước — mà **không ai nhìn một tấm ảnh nào**. Khi cuối cùng
có người nhìn, hoá ra **đa số ảnh không liên quan gì đến prompt**: model không hiểu
tiếng Việt. Mọi số đo trước đó vẫn đúng, nhưng chúng đo một thứ **vô dụng**.

Nguyên nhân gốc: luật §1.5.3 ("người chấm là chủ dự án, không phải tôi") bị dùng
như cái cớ để **không nhìn ảnh chút nào**. Luật đó chỉ áp cho **chấm thẩm mỹ**.

*(Từ 24/08, §1.5.3 đã bị D-052 thay và **máy chấm cả thẩm mỹ**. Cái cớ đó nay không
còn tồn tại — nhưng mục 1.5b này thì vẫn nguyên hiệu lực, và còn cần hơn: nó là chốt
duy nhất phân biệt "đã mở ảnh ra nhìn" với "đoán".)*
"Ảnh có bám prompt không" là câu hỏi **khách quan** — đếm được, kiểm được, và không
cần ai bỏ phiếu.

**Nên từ nay, mọi lô benchmark phải qua bước này TRƯỚC khi báo cáo:**

| Bước | Việc | Ai làm |
|---|---|---|
| ① | Mở **từng ảnh** cạnh **đúng prompt của nó** | tự động dựng ảnh ghép |
| ② | Trả lời một câu **có/không**: ảnh có chứa thứ prompt yêu cầu không | Claude |
| ③ | Đếm: **bao nhiêu / tổng số** ảnh bám prompt | Claude |
| ④ | Chỉ khi tỉ lệ ấy chấp nhận được thì mới báo cáo thời gian/VRAM/nhiệt | — |

**Bốn dấu hiệu phải soi riêng, vì chúng lặng lẽ:**

- **Chủ thể chính vắng mặt** (prompt đòi con mèo → ra người). Đây là kiểu hỏng
  *dễ thấy nhất khi nhìn, khó thấy nhất khi không nhìn*.
- **Đếm sai số lượng** (đòi bốn người → ra một).
- **Quan hệ vị trí bị bỏ** (A **trong** B, B **trên** C).
- **Chữ trong ảnh**: phải soi **1:1**, không soi bản thu nhỏ. Bản thu nhỏ của cùng
  một biển hiệu đọc ra `CƠM TÂM`, ở 1:1 mới thấy là `CỜM TẤM`.

⛔ **Số đo của một lô mà ảnh không bám prompt thì KHÔNG được đưa vào bảng kết quả
như thể nó là số đo chất lượng.** Nó vẫn dùng được cho thời gian/VRAM/nhiệt, nhưng
phải ghi kèm dòng: *"lô này ảnh không bám prompt — số đo chỉ nói về tốc độ máy"*.

### 1.6 Nghi thức chấm — đúng thứ tự này

Sau mỗi phase, ghi vào `CHAM_DIEM.md` một mục sáu phần:

```
Phase / Ngày / Lần chấm
Bằng chứng:  đường dẫn tệp · lệnh đã chạy · số đo
Điểm:        C1..C6 kèm trọng số → trung bình
Blocker:     [ ] ... [ ] ...
BÁC BỎ:      kết luận quan trọng nhất là "___". Tôi thử bác bỏ bằng ___. Kết quả: ___
Phán quyết:  QUA / KHÔNG QUA + lý do một câu
```

Phần **BÁC BỎ** là phần chống Gate 0. Mỗi phase chọn **kết luận quan trọng nhất** của
mình rồi cố tình đi tìm bằng chứng ngược. Phase không có phần BÁC BỎ thì **chưa được
chấm**, không phải "chấm thấp".

### 1.7 Khi không đạt

```
lần 1 không đạt → sửa đúng chiều bị điểm thấp, chấm lại
lần 2 không đạt → sửa, chấm lại
lần 3 không đạt → DỪNG. Báo cáo vì sao phase này không đóng được,
                  đề xuất đổi phạm vi hoặc đổi cách làm.
```

Không có lần 4. Ba lần trượt cùng một phase nghĩa là **kế hoạch sai, không phải việc
làm ẩu** — lúc đó việc đúng là quay lại bàn với chủ dự án.

### 1.8 Hai quy tắc của repo là blocker vĩnh viễn

Từ `CLAUDE.md`, áp cho **mọi** phase chạm máy A:

- **`python tools\gate.py` phải xanh** — không phải `pytest -q`, vì nó bỏ qua 77
  test frontend.
- **Đổi giao diện phải kiểm trên `https://app.lttstudios.com`**, không chỉ loopback
  — loopback bỏ qua Cloudflare (cache, CSP biên, minify).

---

## 2. Toàn cảnh 14 phase

```
 G0 ✅ khung ─┬─ G1 đo phần cứng ─┐
              └─ G2 ✅ giấy phép ─┤     (G1 ∥ G2)
                                  ▼
                    G3 baseline @2560×1440, base bf16
                                  │
                    G4 quét cấu hình CHẤT LƯỢNG (mù)
                                  │
                    G5 edit + reference (3 chế độ, 1–2 ảnh ref)
                                  │
                    G5b chuỗi nâng chất: upscale/restore + VLM tự loại
                                  │
                    G6b ĐỐI CHỨNG TRẦN ⛔  Klein 9B · Gemini 3 Pro · (GPT Image 2)
                                  │        ← cổng quyết định "có đáng bán không"
     ┌────────────────────────────┴─── G6 cổng render (máy A, song song từ đầu) ┐
     │                                                                           │
     └── G7 deploy sang B + service + trọng tài ◄────────────────────────────────┘
                                  │
                    G8 nối nền tảng (provider + image_gen), KHÔNG cascade ngầm
                                  │
                    G9 độ bền: 100 ảnh 4 MP · nhiệt · tranh chấp video
                                  │
                    G10 mở cho khách ⛔ gate.py + trình duyệt thật
                                  │
                    G11 giám sát chất lượng thường trực
                                  │
                    G12 (tuỳ chọn) trả nợ kiến trúc
```

**Đường găng:** G1 → G3 → G4 → G5 → G5b → **G6b** → G7 → G8 → G9 → G10.
**Song song:** G6 (viết cổng render ở máy A, test bằng ComfyUI giả lập) chạy song
song với toàn bộ G3–G6b.

**Thay đổi lớn nhất so với bản 1: G6b — đối chứng trần — là một CỔNG CHẶN**, đặt
*trước* khi nối vào nền tảng. Nếu model nhà thua Gemini quá xa trên chính bộ prompt
của bạn thì **không mở bán**, và ta biết điều đó **trước** khi bỏ công viết provider,
đặt giá, làm giao diện.

| Phase | Thời lượng | Máy | Chạm production? |
|---|---|---|---|
| G0 ✅ | 1 giờ | A | không |
| G1 | nửa buổi | B | không |
| G2 ✅ | nửa buổi | — | không |
| G3 | 1 buổi | B | không |
| G4 | 2 ngày | B | không |
| G5 | 1,5 ngày | B | không |
| G5b | 1 ngày | B | không |
| **G6b** | 1 ngày | B + API | không |
| G6 | 1,5 ngày | A | không |
| G7 | nửa ngày | B | không |
| G8 | 1 ngày | A | **có** — thêm provider, chưa lộ ra khách |
| G9 | 1 ngày | A+B | không |
| G10 | 1 ngày | A | **CÓ — khách nhìn thấy** |
| G11 | thường trực | A | không |

Tổng: **11–12 ngày làm việc**, chưa kể thời gian tải model và thời gian **bạn** ngồi
chấm ảnh — mà ở kế hoạch này, thời gian bạn chấm ảnh là đường găng thật.

---

## 3. G1 — Đo nốt phần cứng *(song song với việc chuẩn bị G3)*

**Mục tiêu:** lấp hai lỗ hổng số liệu. Chúng đổi kết luận về cấu hình và về thời
gian đổi model khi chia card với video.

**Việc:**

1. `E:\AI\tools\pcie_check.py` — **đã có sẵn trên B**. Cần link width hiện tại và
   link width tối đa của khe.
2. Đo tốc độ đọc tuần tự E: (đọc một file model ~15 GB đã có, tính giây).
3. `render_gateway/diagnostics/gpu_check.py`: tên GPU · VRAM · CUDA khả dụng · torch
   · CUDA runtime · compute capability · khả năng BF16 · **một phép tensor thật** ·
   cấp phát rồi giải phóng và kiểm VRAM có trả về.
4. Đọc `GET /api/v1/metrics` của Nexus trên **cả hai máy**, lưu làm mốc gốc.
5. **Mới ở bản 2 — đo nhiệt và trần công suất.** Chất lượng-trên-hết nghĩa là job
   dài 3 phút chạy liên tục. Ghi: `power_limit_w` hiện tại (task
   `LTTAI_GPU_PowerLimit` đang **Disabled**, cần biết card đang chạy ở 250 W hay
   370 W), nhiệt khi nghỉ, và `throttle_reasons` — trường này có sẵn trong metrics
   của Nexus.

**Bằng chứng:** `bench/G1_phan_cung.json` + `bench/G1_gpu_check.txt`.

**Blocker:**
- ⛔ PCIe link **x4 hoặc thấp hơn** → dừng, báo, tính lại thời gian đổi model.
- ⛔ Phép tensor thật **không chạy được** → môi trường hỏng, không đi tiếp.

**Chấm:** C2 40 % · C3 40 % · C1 20 %.
**Bác bỏ:** chạy `gpu_check.py` hai lần, một lần khi ComfyUI đang nạp model — số
VRAM có phản ánh đúng không, hay đọc ra số cũ?

---

## 4. G3 — Baseline: `base` bf16 ở 2560×1440

**Mục tiêu:** một tấm ảnh thật ở **cấu hình cao nhất**, tái lập được theo seed. Và
chứng minh bằng số cái cảnh báo "off-distribution" có thật hay không.

**Tải về — chỉ một loại file, không có text encoder rời:**

| File | GB | Vai |
|---|---|---|
| `hidream_o1_image_bf16.safetensors` | 16,4 | **cấu hình đích** |
| `hidream_o1_image_fp8_scaled.safetensors` | 8,07 | để so precision ở G4 |
| `hidream_o1_image_dev_fp8_scaled.safetensors` | 8,07 | bản distilled, để biết bỏ lỡ gì |
| **Tổng** | **32,5** | |

Vào `E:\AI\models\checkpoints\`. Ghi bảng kê `(tên, nguồn, sha256, ngày, dung lượng)`
vào `E:\AI\ltt_render\scripts\tai_model.ps1`.

> ⚠️ **Trang tài liệu ComfyUI liệt kê `gemma4_e4b_it_fp8_scaled.safetensors` 9,06 GB
> làm text encoder — SAI với model này.** Mã trên máy B:
> *"HiDream-O1-Image **tokenizer-only** text encoder. The real Qwen3-VL backbone runs
> inside `diffusion_model.*` **every step**."* Chữ "gemma" duy nhất trong mã
> HiDream-O1 là `q_norm/k_norm: "gemma3"` — tên kiểu chuẩn hoá.
> **Nếu G3 phát hiện vẫn cần file đó thì ghi lại ngay** — đó sẽ là bằng chứng mã tôi
> đọc sai, và phải sửa D-009.

**Việc:**

1. Workflow `t2i` ở `render_gateway/workflows/hidream_o1_t2i.json` (API format, tham
   số hoá). Node: `CheckpointLoaderSimple` → `EmptyHiDreamO1LatentImage(2560×1440)` →
   sampler (`shift 3.0`, `noise_scale 8.0` theo `sampling_settings`) → lưu ảnh.
   **Không cần `VAELoader`** — model pixel-space, VAE đi kèm checkpoint.
2. Chạy **5 ca** của bước 04 build pack: portrait · cinematic · landscape · product ·
   cảnh phức tạp có chữ. Ở **2560×1440**, `base`, bf16, 50 bước, CFG 5,0.
3. **Thí nghiệm độ phân giải** — cái này riêng của bản 2, và nó quyết định công thức
   giao hàng. Cùng prompt, cùng seed, ba nhánh:
   - (a) sinh thẳng **1920×1080**
   - (b) sinh **2560×1440** → thu nhỏ về 1920×1080
   - (c) sinh **2048×2048** → cắt về 16:9
   Chấm mù (§1.5). Nếu (b) không thắng rõ thì cảnh báo "off-distribution" của node
   là sai với ca dùng thật, và ta tiết kiệm được ~44 % token mỗi ảnh.
4. Mỗi lượt ghi: prompt · seed · độ phân giải · bước · CFG · sampler · **thời gian
   nạp · thời gian sinh · VRAM đỉnh · RAM đỉnh · nhiệt độ · `throttle_reasons`** ·
   đường dẫn ảnh.

**Bằng chứng:** `bench/G3_baseline.json` · 5 + 15 ảnh · bảng kê sha256 ·
`bench/G3_do_phan_giai.md`.

**Blocker:**
- ⛔ OOM ở `base` bf16 @ 2560×1440 → **không âm thầm hạ xuống fp8**. Ghi lại, báo,
  rồi mới quyết. Đây đúng là quy tắc build pack: *"không hy sinh chất lượng trước
  khi đo"*.
- ⛔ Ghi/sửa bất cứ thứ gì trong `E:\AI\ComfyUI` hoặc `E:\AI\venv` → C4 = 0.
- ⛔ Cùng seed ra hai ảnh khác nhau → tính tái lập hỏng, **mọi số của G4 sẽ vô
  nghĩa**, phải sửa trước.

**Chấm:** C1 20 % · C2 25 % · C3 30 % · C4 25 %.
**Bác bỏ:** khởi động lại ComfyUI (máy nguội), chạy lại đúng seed — ra đúng ảnh cũ
không?

---

## 5. G4 — Quét cấu hình chất lượng

**Mục tiêu:** tìm **cấu hình đẹp nhất chạy được**, bằng so mù. Không phải cấu hình
cân bằng.

**Bộ prompt: ĐÃ CÓ** — `bench/prompts_30.json`, 30 prompt cố định, seed cố định,
12 hạng mục: portrait · ảnh thật · điện ảnh · nhiều người · đặt vật thể ·
**sản phẩm** · **chữ tiếng Việt** (3 prompt) · chữ tiếng Anh · kiến trúc · anime ·
fantasy · **thumbnail YouTube** (3 prompt, ca dùng thật của bạn) · bố cục khó.
⛔ **Không đổi nội dung bộ này giữa các phase** — đổi là mọi số đo trước đó thành
vô nghĩa.

**Bộ so mù: ĐÃ CÓ** — `tools/cham_mu.py`, 17 test ở `tests/test_247_cham_mu.py`.
Nó **cưỡng chế bằng mã** bốn luật ở §1.5 thay vì để chúng nằm trên giấy:

```
py tools/cham_mu.py tao  --a <thu_muc_A> --b <thu_muc_B> --ra <lo> --bay 0.1
py tools/cham_mu.py tinh --lo <lo>
```

- Chép ảnh sang tên mã `c001_trai.png` — **tên tệp không mang dấu vết nguồn nào**;
  bảng đối chiếu ghi riêng ra `KHONG_MO_TRUOC_KHI_CHAM.json`.
- Xáo trái/phải để không phía nào cố định.
- Dưới 50 cặp thật ⇒ **tự động ghi "chưa phân biệt được"**, không cho kết luận non.
- Khoảng tin cậy **Wilson** (không dùng công thức chuẩn: với n nhỏ nó cho khoảng
  hẹp giả tạo và sẽ tuyên bố "khác biệt có ý nghĩa" khi thật ra không).
- **Bắt lệch vị trí**: người chấm luôn chọn một phía thì báo ngay.

**Bốn trục quét — mỗi trục một câu hỏi:**

| Trục | Các mức | Câu hỏi |
|---|---|---|
| ~~Precision~~ | ~~bf16 · fp8_scaled~~ | ✅ **ĐÃ XONG — fp8 BỊ LOẠI** (D-021): trên máy này nó **chậm hơn 6 %** *và* **tốn VRAM hơn 42 %** (23,99 GB so với 16,86 GB). Không thắng trục nào |
| Bản | `base` (50 bước, CFG 5,0) · `dev` (28 bước, CFG 1,0) | chênh 3,6× thời gian có đổi lấy được chất lượng không? |
| Số bước | 30 · 50 · 70 · 90 | bao nhiêu bước là **bão hoà**? *(thời gian đã đo: 58 · 96 · 133 · 173 giây — **cả bốn đều dưới trần 6 phút**, nên thời gian không loại được cấu hình nào; chất lượng phải chấm mù)* |

⭐ **Thiết kế thí nghiệm HAI ĐẦU MÚT cho trục số bước.** Thay vì so cả bốn mức
(6 cặp so sánh, tốn 4 giờ GPU), sinh cả 30 prompt ở **s30** và **s90** — hai đầu mút.
- Không phân biệt được ⇒ **số bước không quan trọng**, lấy s30 (nhanh nhất, mát nhất).
- Phân biệt được ⇒ mới chia đôi tiếp (s50 hoặc s70).
Rẻ hơn, và kết luận chặt hơn: nếu hai đầu mút đã như nhau thì các mức giữa cũng vậy.
| Sampler/scheduler | ≥ 3 tổ hợp | có tổ hợp nào hơn hẳn mặc định không? |
| ~~Trần công suất~~ | ~~370 W · 250 W~~ | **ĐÃ BỎ** — chủ dự án chốt giữ 370 W (**D-020**) |

⭐ **Vì sao bỏ trục công suất** (D-020): hạ W là đánh đổi chất lượng lấy nhiệt độ,
trong khi D-010 chốt chất lượng là tiêu chí duy nhất — ở 250 W ảnh **chậm hơn và
không đẹp hơn**. Quyết định này đứng vững nhờ **trần 6 phút** của D-011: ở 92 giây/ảnh,
kể cả tiết lưu làm chậm gấp đôi vẫn còn ~3 phút, **vẫn dưới trần**.
⛔ Đổi lại, **G9 đổi câu hỏi**: không hỏi "có tiết lưu không" (đã biết là có), mà hỏi
"chạy 100 lượt liên tiếp thì thời gian phình bao nhiêu, có chạm trần 6 phút không,
và có hỏng gì NGOÀI việc chậm đi không".

**Đo mỗi cấu hình** (≥ **3 lần**, lấy trung vị): thời gian nạp · độ trễ lần đầu · độ
trễ khi nóng · **VRAM đỉnh · RAM đỉnh · nhiệt độ · `throttle_reasons`** · tỉ lệ hỏng/OOM.

**Chấm chất lượng theo §1.5:** ảnh đổi tên thành mã, so từng cặp, **bạn** vote, 10 %
cặp bẫy A-đấu-A, ≥ 50 cặp cho bất kỳ kết luận nào, cộng bảng đếm lỗi khách quan.

**Quy tắc chọn — khác hẳn bản 1:**

```
1. LOẠI mọi cấu hình OOM hoặc tỉ lệ hỏng > 2 %.
2. LOẠI mọi cấu hình vượt TRẦN THỜI GIAN (đề xuất 6 phút/ảnh — chờ bạn chốt).
3. Trong số còn lại: CHỌN CẤU HÌNH THẮNG SO MÙ. Thời gian KHÔNG được dùng để loại.
4. Nếu hai cấu hình KHÔNG PHÂN BIỆT ĐƯỢC (< 65/35 trên ≥50 cặp) → chọn cái nhanh hơn.
   Chỉ ở bước này tốc độ mới được nói.
```

**Sản phẩm:** `configs/profile_quality.yaml` · `docs/ANH_NOI_BO/BENCHMARK.md`.
`profile_fast.yaml` **chỉ tạo nếu** bước 4 nói `dev` không phân biệt được với `base`.

**Blocker:**
- ⛔ Có lượt video chạy xen vào → **số bẩn, đo lại**. Bật chế độ độc chiếm và ghi
  vào biên bản là đã bật.
- ⛔ Chỉ đo một lần mỗi cấu hình → C3 tối đa 8, không qua ngưỡng.
- ⛔ Chấm chất lượng mà không mù → C3 tối đa 5.
- ⛔ Kết luận từ dưới 50 cặp mà không ghi "chưa phân biệt được".

**Chấm:** C3 45 % · C2 25 % · C1 20 % · C6 10 %.
**Bác bỏ:** đảo thứ tự chạy các cấu hình. Nếu thứ hạng đổi thì đang đo trạng thái
nhiệt/cache chứ không đo cấu hình. Và kiểm cặp bẫy: bạn có "phát hiện khác biệt" ở
các cặp A-đấu-A không?

> **Nhớ:** 3090 là SM 8.6, **không có FP8 tensor core**. fp8 ở đây để **vừa VRAM**,
> không phải để nhanh. Nếu bf16 vừa 24 GB thì bf16 vừa đẹp nhất vừa nhanh nhất.

---

## 6. G5 — Edit và reference (ba chế độ)

**Mục tiêu:** ba chế độ bạn chốt phải chạy được, và phải biết chế độ nào **chưa đủ
tốt để bán**.

### ⛔ G5 ĐỔI CÁCH CHẠY — vì cấu hình tham chiếu chưa ai đo (D-024/D-025)

Bản đầu của G5 định chạy thẳng `edit`/`subject` ở `ref_mp = 4.0`, trong một **chuỗi
tự động không người canh**. *(Máy B khởi động lại hôm 22/08 là do **Windows Update**,
không do cấu hình này — xem D-025. Nhưng số dưới đây vẫn nói rằng cấu hình đó không
chạy được, và đó là lý do đủ.)*

| Cấu hình | Token | So với đã đo (4.096) |
|---|---|---|
| khung 2560×1440, không ref | 3.600 | trong vùng |
| `edit`, 1 ảnh @ 4 MP | **7.506** | **×1,8** |
| `subject`, 2 ảnh @ 4 MP | **11.412** | **×2,8** |

Ảnh tham chiếu đi vào `reference_latents` của conditioning, tức là **nối thêm token
vào chính chuỗi mà attention phải xử lý**. Ở cấu hình đã chiếm 97,5 % VRAM, thêm
gấp đôi token là chắc chắn vỡ.

**Nên G5 chạy theo THANG, có người ngồi canh**, bằng
`render_gateway/deploy/thang_do_tham_chieu.ps1`:

1 ảnh @ 0,4 MP → 1 MP → 2 MP → 4 MP → 2 ảnh @ 1 MP → 2 ảnh @ 2 MP

Mỗi bậc đo VRAM và **dừng thẳng** khi chạm 21.000 MB (chừa ~3,6 GB cho hệ điều hành
và dự án video). Bậc dùng được là bậc **ngay trước** bậc chạm ngưỡng.

Thang là script **duy nhất** được phép vượt `TOKEN_DA_DO_TOI_DA`, và vì thế nó là
script **an toàn nhất**: chạy ở tiền cảnh, không tách khỏi phiên, mỗi bậc phải gỡ
`--tran-token` ra tường minh. Có test chốt cả ba điều đó.

**Điều kiện tiên quyết:** ComfyUI phải đang chạy với `--reserve-vram 3`.

**Việc:**

1. Workflow **đã viết sẵn** cho `edit` (1 ảnh) và `subject` (2 ảnh) — dựng từ schema
   đọc trong mã, **chưa chạy thật**. G5 xác minh y như đã làm với `t2i`.
   ⚠️ Lược đồ `/object_info` khai `images` kiểu gộp `COMFY_AUTOGROW_V3`, nhưng khuôn
   dây API là **phẳng**: `image_1`…`image_10` (đọc `comfy_api/latest/_io.py`
   §`_expand_schema_for_dynamic`, dòng 1143–1156). `image_1` bắt buộc, phần còn lại
   tuỳ chọn. Bản mẫu hiện tại **viết đúng**.
   ⛔ **Không có template `structure`**: HiDream-O1 **không hỗ trợ ControlNet**
   (đã grep, không dòng nào — **D-017**). G5 phải thử đạt nó bằng `edit` + lời nhắc
   giữ bố cục. Ba đường nếu không đạt: (a) bỏ chế độ và **nói thẳng**;
   (b) thêm Qwen-Image-Edit-2511 riêng cho chế độ đó; (c) đổi kỳ vọng sản phẩm.
   **Quyết sau khi có số, không quyết trước.**
2. **Giới hạn 1–2 ảnh tham chiếu** — `ref_max_size()` tự thu nhỏ ảnh ref theo số
   lượng: 1 ảnh giữ nguyên · 2 ảnh ×0,75 · 3 ảnh ÷2 · 4 ảnh ×0,375 · ≥5 ảnh ÷4.
   Nhồi 5 ảnh là mỗi ảnh chỉ còn ¼ độ phân giải. **Chất lượng-trên-hết ⇒ mặc định
   1 ảnh, tối đa 2**, và giao diện phải nói rõ vì sao.
3. Pipeline ảnh vào: kiểm MIME · phát hiện hỏng · chuẩn hoá EXIF · resize/crop ·
   **giữ bản gốc, làm việc trên bản sao**. Phía máy A dùng lại
   `platform_core.image_input.validate_reference` — **không viết mới**.
4. Bộ test build pack, **10 ca mỗi loại**: đổi màu · đổi trang phục · đổi nền · giữ
   nhân dạng · sửa vật thể · ghép nhiều tham chiếu. Gallery before/after.
5. **Bảng đếm lỗi riêng cho edit** (§1.5.6): mất nhân dạng · đổi phần không được
   đụng · vết ghép · sai màu vùng giữ nguyên.

**Sản phẩm:** `docs/ANH_NOI_BO/EDIT_REFERENCE.md` ghi **thẳng** chế độ nào đủ ổn
định để bán, chế độ nào chưa.

**Blocker:**
- ⛔ Một chế độ hỏng > **20 %** số ca → **không mở chế độ đó cho khách** ở G10.
  *(bản 1 để 30 %; chất lượng-trên-hết siết xuống 20 %)*
- ⛔ Che một chế độ yếu bằng cách giấu nó trong UI thay vì ghi ra.

**Chấm:** C3 35 % · C1 25 % · C2 25 % · C6 15 %.
**Bác bỏ:** đưa ảnh tham chiếu **cố tình xấu** — mờ, xoay EXIF, có alpha, 1 px, file
`.png` thật ra là `.txt`. Hệ báo lỗi rõ hay sinh rác im lặng?

---

## 7. G5b — Chuỗi nâng chất lượng *(mới ở bản 2)*

**Mục tiêu:** chất lượng-trên-hết mở ra những việc trước đây không đáng làm. Máy B
đã có sẵn công cụ; câu hỏi là chúng có **thật sự** nâng điểm so mù không.

**Ba nhánh, mỗi nhánh một thí nghiệm:**

1. **Hậu xử lý nâng phân giải/phục hồi.** Máy B đã có `seedvr2_3b_int8_convrot`
   (3,2 GB) và `models/upscale_models`. So mù: ảnh 4 MP thô ↔ ảnh 4 MP + SeedVR2.
2. **Tự loại bằng VLM.** Nền tảng đã có `verifiable=("vlm_judge",)` trong `ToolSpec`
   và `platform_core/agent/verifier.py`; máy B có 48 GB model VLM +
   `E:\AI\tools\vlm_worker.py`. Thí nghiệm: sinh 2 ảnh, VLM chấm, trả ảnh tốt hơn.
   Đo: VLM chọn có trùng với **bạn** chọn không? Nếu tỉ lệ trùng < 70 % thì VLM đang
   đoán, **bỏ**.
3. **Nhiều seed rồi chọn.** Đơn giản nhất và có thể mạnh nhất: sinh 3 ảnh khác seed,
   khách chọn. Đổi 3× thời gian GPU lấy 3× cơ hội có ảnh đẹp.

**Quy tắc chống làm màu:** nhánh nào **không** nâng điểm so mù thì **bỏ hẳn**,
không giữ lại "cho có". Chất lượng-trên-hết không phải là cớ để chồng thêm bước.

**Blocker:**
- ⛔ Kết luận "có cải thiện" mà không có so mù ≥ 50 cặp.

**Chấm:** C3 50 % · C2 30 % · C6 20 %.
**Bác bỏ:** với nhánh VLM, trộn vào các cặp mà **hai ảnh gần như giống hệt**. VLM có
vẫn "tự tin chọn" không? Nếu có thì nó đang chấm ngẫu nhiên.

---

## 8. G6b — ĐỐI CHỨNG TRẦN ⛔ *(cổng quyết định, mới ở bản 2)*

> 🔴 **KẾT QUẢ VÒNG 1 (2026-08-23) — đọc D-045 trước khi làm gì với mục này.**
> 30 cặp thật đấu Gemini 3 Pro Image: **Gemini 24 – nhà 4 – hoà 2** (điểm nhà 0,167,
> KTC [0,073 ; 0,336]). Nhà **0 thắng / 16** ở `photoreal` + `portrait` +
> `multi-person` + `thumbnail` + `text-vi` + `text-en`; chỉ **ngang 1–1** ở `anime`,
> `fantasy`, `architecture` — mà mỗi loại chỉ có **2 cặp**, tức chưa là bằng chứng.
> Bẫy nhận đúng 3/3; quyết đoán 0,93 trên cặp thật so với 0,33 trên cặp bẫy.
>
> ⛔ **VÀ MỤC NÀY ĐÃ ĐÓNG LẠI — xem D-046.** Chủ sản phẩm quyết **bỏ hẳn đối chứng
> ngoài**: D-042 đã bỏ định tuyến, nên điểm số so với Gemini không đổi được lựa chọn
> nào, trong khi mỗi lô tốn tiền API thật. Klein 9B và GPT Image 2 **bỏ**, không phải
> hoãn. Bảng cổng quyết định bên dưới **không còn được kích hoạt**; giữ lại làm hồ sơ.
> Việc đo từ đây là **nội bộ, HiDream đấu HiDream, một lô một biến** — D-046 §"Việc đo
> nội bộ thay vào".

**Mục tiêu:** trả lời **trước khi bỏ công nối vào nền tảng**: model nhà có đủ tốt để
bán không, và loại yêu cầu nào nên đi đâu.

Ở bản 1 việc này là G11, làm **sau** khi đã mở bán. Với chất lượng là tiêu chí duy
nhất, làm sau là làm ngược: ta sẽ đã đặt giá, viết giao diện và mở cửa **trước khi**
biết mình đứng ở đâu.

**Ba đối thủ, cùng 30 prompt của G4 + 30 ca edit của G5:**

| Đối thủ | Vì sao |
|---|---|
| **Klein 9B** | trần trọng số mở (Elo sửa ảnh 1165). **Chỉ để đo** — giấy phép NC cấm bán. Ảnh sinh ra **không** được dùng vào bất cứ việc gì khác |
| **Gemini 3 Pro Image** | **thứ bạn đang bán**. Đây là đối chứng quan trọng nhất |
| GPT Image 2 | trần thương mại (Elo sửa ảnh 1256), nếu có key |

**Cách làm:** so mù từng cặp theo §1.5 — ảnh đổi tên mã, xáo trộn, 10 % cặp bẫy,
≥ 50 cặp mỗi đối thủ. **Lộ tên model trước khi vote ⇒ vứt toàn bộ dữ liệu, làm lại.**

**Đầu ra là một bảng định tuyến**, không phải một điểm số:

```
loại yêu cầu → nên đi model nhà / nên đi Gemini / hoà (để khách chọn)
```

**Cổng quyết định:**

| Kết quả so với Gemini | Hành động |
|---|---|
| Thắng hoặc hoà ở đa số loại | **mở bán**, đi tiếp G7 |
| Thua ở đa số nhưng thắng rõ ở vài loại | **mở bán hẹp** — chỉ những loại thắng, ghi rõ trong giao diện |
| Thua ở mọi loại | **DỪNG.** Báo cáo, và đề xuất: đổi model, hoặc mua giấy phép Klein 9B, hoặc bỏ hạng mục |

**Blocker:**
- ⛔ Lộ tên model trước khi vote.
- ⛔ Dùng ảnh Klein 9B vào bất cứ việc gì ngoài chấm điểm.
- ⛔ Kết luận từ dưới 50 cặp.

**Chấm:** C3 45 % · C2 35 % · C6 20 %.
**Bác bỏ:** cặp A-đấu-A đã nói ở §1.5. Thêm: đảo thứ tự trái/phải của cùng một cặp
ở hai chỗ khác nhau trong phiếu — bạn có vote nhất quán không?

---

## 9. G6 — Cổng render *(máy A, song song từ đầu)*

**Mục tiêu:** một dịch vụ HTTP làm cho GPU máy B trông như một API bên ngoài.

```
render_gateway/
├── main.py              uvicorn entry
├── api.py               5 endpoint (KE_HOACH_H37.md §3)
├── comfy.py             client ComfyUI: /prompt · /history · /view · /free · websocket
├── busy.py              dò bận + ước tính eta_s (CHIA_GPU_VOI_VIDEO.md §3–4)
├── jobs.py              trạng thái job + idempotency theo job_id
├── workflows.py         nạp template JSON, thay tham số, kiểm đủ node
├── storage_io.py        tải ref từ presigned GET · đẩy ảnh lên presigned PUT
├── config.py            đọc env, không hardcode đường dẫn
├── diagnostics/gpu_check.py
└── workflows/*.json
```

**Điểm bắt buộc:**

- **Async submit → poll.** Trạng thái dùng đúng bộ tên build pack: `queued ·
  preparing · generating · saving · completed · failed · cancelled`.
- **`idempotency_key = job_id`** — chạy lại trả kết quả cũ, không vẽ lần hai. Với
  ảnh 3 phút thì đây không còn là tối ưu, mà là bắt buộc.
- **Trần thời gian phải rộng.** *(mới ở bản 2)* Bản 1 ngầm giả định job vài chục
  giây. Nay một ảnh mất 3–6 phút ⇒ timeout, nhịp poll, TTL presigned URL và
  `max_runtime_s` đều phải đặt lại theo thang phút.
- **`/health` trả `busy` + `eta_s` + lý do** + báo cáo tài nguyên theo khuôn
  `CHIA_GPU_VOI_VIDEO.md` §10.1 (đừng đẻ ra bộ đọc GPU thứ tư).
- **429 + `Retry-After`** khi đã đủ `N` việc song song. **`N = 1`.**
- **`POST /doc_chiem`** cho chế độ độc chiếm, tự hết hạn.
- **Chính sách hỏng** phân biệt: yêu cầu sai · ref hỏng · ComfyUI không phản hồi ·
  model nạp lỗi · OOM · quá giờ · lỗi đẩy R2. OOM: ghi metric, gọi `/free`, **tối đa
  một lần thử lại**, rồi dừng.

**Test:** `tests/test_245_render_gateway.py` — ComfyUI giả lập, **chạy trên máy A,
không cần GPU**. Phủ: đường thành công · 429 khi bận · idempotency · ref hỏng ·
ComfyUI chết giữa chừng · OOM · huỷ · độc chiếm · `eta_s` tính đúng từ chuỗi progress
giả · **job chạy 5 phút không bị timeout nhầm**.

**Blocker:**
- ⛔ `python tools\gate.py` không xanh.
- ⛔ Bí mật nào của nền tảng lọt vào `render_gateway/` (khoá R2, chuỗi kết nối CSDL,
  khoá mã hoá) → vi phạm ranh giới kiến trúc, C4 = 0.

**Chấm:** C3 35 % · C1 20 % · C5 25 % · C2 10 % · C6 10 %.
**Bác bỏ:** cho ComfyUI giả lập trả những thứ ác ý — 200 kèm thân rỗng · treo 10
phút · ảnh 0 byte · `prompt_id` lạ. Cổng có chết sạch sẽ và báo đúng loại lỗi không?

---

## 10. G7 — Deploy sang B, dịch vụ, tường lửa, trọng tài

**Mục tiêu:** cổng render sống sót qua một lần khởi động lại máy, và chỉ máy A gọi
được nó.

1. `scripts/deploy_render_gateway.ps1` — đẩy từ repo sang `E:\AI\ltt_render\gateway`
   qua SSH. **Thuần ASCII** (quy tắc 2). Ghi cấu hình **không BOM** (quy tắc 1 — lỗi
   này đã từng làm sập production dự án này).
2. Venv **riêng**: `E:\AI\ltt_render\venv`. **Tuyệt đối không** `pip install` vào
   `E:\AI\venv`.
3. Hai service NSSM: `LTTComfyUI` + `LTTRenderGateway` — tự khởi động, tự bật lại
   khi chết, **có trần số lần restart**.
4. Tường lửa: mở TCP 8199 **chỉ cho 192.168.2.17**. ComfyUI **giữ nguyên**
   `--listen 127.0.0.1`.
5. **Ghim commit ComfyUI** `6f7cd7f`. Ghi vào `DECISIONS.md`.
6. Token bearer sinh trên B, cất ở `C:\ProgramData\LTTRender\gateway.env`.
7. Đo tốc độ LAN A↔B.
8. `kiem_tra.ps1`: so hash gateway với repo · hai service · `NexusClockSync` · tường
   lửa · `/health`.

**Blocker:**
- ⛔ Sau `Restart-Computer` mà một service không tự lên.
- ⛔ Gọi được 8199 từ máy khác trong LAN (không phải .17).
- ⛔ ComfyUI bị đổi sang nghe ngoài loopback.
- ⛔ Tệp trong `gateway/` khác hash so với repo (đã sửa tay).

**Chấm:** C5 40 % · C4 30 % · C2 20 % · C1 10 %.
**Bác bỏ:** **thật sự khởi động lại máy B**, không phải chỉ restart service. Và
**thật sự gọi 8199 từ máy thứ ba** trong LAN.

---

## 11. G8 — Nối vào nền tảng

**Mục tiêu:** máy A gọi được model nhà qua đúng đường đang gọi Gemini — **nhưng
không bao giờ thay model sau lưng khách**.

1. `platform_core/providers.py`: thêm **một** `Provider("ltt_image", ...)` —
   `AUTH_BEARER`, `base_url` từ env, `categories=(APIKEY_CAT_IMAGE,)`,
   `async_poll=True`, `list_models_path="/v1/models"`, kèm `ModelInfo` từ G4.
2. `platform_core/image_gen/` — adapter dùng chung. Giai đoạn này **chỉ** phục vụ
   `ltt_image`; **không đụng một dòng nào** của đường Gemini.
3. Token cổng render cất vào APIKEYS (mã hoá), không để trong env.
4. `secrets/app.env`: `LTT_RENDER_ENDPOINT` · `LTT_RENDER_TIMEOUT_S` (thang **phút**).
5. `LTT_WORKER_POOLS`: thêm pool `render`.
6. **Luật chờ — sửa theo D-010:** không cascade ngầm. Khi B bận, adapter trả trạng
   thái **"bận + eta_s"** lên tầng trên; **khách quyết định** chờ hay dùng đám mây.
   Ngưỡng tính theo **thời gian chờ THÊM so với thời gian chạy**, không phải hằng số
   45 giây của bản 1 (một ảnh vốn đã mất 3 phút).

**Test:** `tests/test_246_provider_local.py` — provider có trong registry · adapter
dispatch đúng · **bận không bị coi là lỗi** · **bận KHÔNG tự cascade** · idempotency ·
ảnh vào R2 đúng khoá.

**Blocker — cạm bẫy chết người:**
- ⛔ Khi B bận, adapter gọi `api_pool.danh_dau_loi()` cho key `ltt_image`. Bận là
  trạng thái bình thường; đánh dấu lỗi → cooldown → `disable` sau 5 lần ⇒ **một tối
  chạy video sẽ tự tắt vĩnh viễn model nhà** mà không ai hiểu vì sao.
- ⛔ Có đường nào tự đổi sang Gemini mà khách không bấm.
- ⛔ `gate.py` không xanh.
- ⛔ Đường Gemini đổi hành vi (so bằng test cũ).

**Chấm:** C3 35 % · C4 30 % · C1 15 % · C5 10 % · C6 10 %.
**Bác bỏ:** **tắt hẳn máy B**, gửi một job. Khách phải nhận **thông báo rõ ràng kèm
lựa chọn**, không phải một ảnh Gemini lặng lẽ và cũng không phải một lỗi cụt. Key
`ltt_image` phải còn `active` sau đó.

---

## 12. G9 — Độ bền dưới tải dài

**Mục tiêu:** phát hiện thứ chỉ lộ ra sau vài trăm lượt. Ở bản 2 trọng tâm dời từ
*thông lượng* sang *ổn định khi chạy job dài*.

1. **100 ảnh liên tiếp ở cấu hình đích** (4 MP, `base`, bf16) — đo **memory drift**:
   VRAM và RAM sau ảnh thứ 100 so với ảnh đầu.
2. **Nhiệt và tiết lưu** *(mới ở bản 2)*. Mỗi ảnh là ~3 phút tải nặng liên tục. Ghi
   nhiệt độ và `throttle_reasons` theo thời gian. Dự án video đã quan sát **71 °C ở
   trần 250 W**, và 3090 tiết lưu quanh **83 °C**. Nếu card tiết lưu thì **chất lượng
   không đổi nhưng thời gian phình** — và ta phải biết điều đó trước khi hứa với khách.
3. Đường hỏng: prompt rất dài · ảnh ref hỏng · OOM · restart worker giữa chừng ·
   restart cổng render giữa chừng.
4. **Kịch bản tranh chấp với video:** phóng lượt video giả ngắn và dài, gửi job ảnh
   vào giữa. Với D-010: job ảnh **không được tự nhảy sang Gemini** — nó phải báo
   "bận + eta" và chờ lệnh.
5. Đo: độ trễ trung vị · **P95** · VRAM/RAM đỉnh · util · nhiệt · tỉ lệ hỏng · OOM.

**Sản phẩm:** `docs/ANH_NOI_BO/PERFORMANCE.md`.

**Blocker:**
- ⛔ **Memory drift rõ rệt** → không mở bán, sửa trước.
- ⛔ Cổng render chết mà không tự sống lại.
- ⛔ Nhiệt chạm ngưỡng tiết lưu ở lượt thứ N → phải xử lý (trần công suất, quạt,
  giãn cách job) trước khi mở bán.

**Chấm:** C3 40 % · C5 35 % · C2 25 %.
**Bác bỏ:** giết tiến trình ComfyUI **giữa lúc đang sinh ảnh**. Job đó có hỏng sạch
sẽ, hoàn credit, báo đúng lỗi không — hay treo tới hết timeout?

---

## 13. G10 — Mở cho khách ⛔

**Mục tiêu:** người dùng thật sinh được ảnh bằng model nhà, trả credit đúng, và
**biết mình đang dùng model nào**.

1. Thêm model nội bộ vào `model_ref` của `taoanh` — **một dòng manifest**. Chỉ
   **thêm lựa chọn**.
2. **Giao diện đường 2** (chốt ở D-010): khách thấy rõ *"Model nhà — đang bận, còn
   khoảng X phút"* kèm nút *"Dùng đám mây ngay"*. **Không** thay model ngầm.
3. Giao diện phải nói rõ: **1–2 ảnh tham chiếu** cho kết quả tốt nhất, và **vì sao**.
4. Giá credit tính từ số đo G4 + kết quả định tuyến G6b. Ghi cách tính vào
   `DECISIONS.md` — giá phải truy được về số đo, không phải "thấy hợp lý".
5. Chế độ nào G5 đánh trượt thì **không mở**.
6. Cảnh báo `LTT_OPS_ALERT_EMAIL` khi B chết · vòng đời `work\` · `RUNBOOK.md` ·
   `live_check_render.py`.

**Blocker:**
- ⛔ `python tools\gate.py` không **toàn** xanh.
- ⛔ Chưa kiểm trên **`https://app.lttstudios.com`** bằng trình duyệt thật. Loopback
  không tính — repo này đã dính một lần: CSS đúng ở origin nhưng Cloudflare phục vụ
  bản cũ 4 tiếng.
- ⛔ Đổi CSS/JS mà không cache-bust (quy tắc 6).
- ⛔ `live_check_render.py` **không fail** khi rút máy B ra.
- ⛔ Mở một chế độ mà G5 đã đánh trượt.

**Chấm:** C4 25 % · C3 25 % · C5 20 % · C1 15 % · C6 15 %.
**Bác bỏ:** đăng nhập bằng **tài khoản khách thật** (không phải admin), sinh một ảnh,
kiểm sổ credit trước/sau, rồi **tắt máy B giữa chừng** và làm lại. Khách phải luôn
biết ảnh của mình do model nào sinh ra.

---

## 14. G11 — Giám sát chất lượng thường trực *(đổi vai ở bản 2)*

Ở bản 1 đây là bước đối chứng, nay đã chuyển lên G6b. Vai mới: **chất lượng không
phải việc đo một lần**.

- Mỗi tháng lấy mẫu ngẫu nhiên N ảnh thật, chấm mù lại với Gemini.
- Theo dõi tỉ lệ khách bấm "dùng đám mây" — nếu tăng, đó là tín hiệu chất lượng
  hoặc thời gian chờ đang xấu đi.
- Model mới ra thì đưa vào bộ đối chứng, không đổi mặc định trước khi so mù.

---

## 15. G12 *(tuỳ chọn)* — Trả nợ kiến trúc

Rút đường Gemini của `taoanh`/`thumbnail` vào `image_gen` chung, xoá bản sao L2.

**Blocker:** ⛔ bất kỳ test cũ nào của hai app đổi kết quả · ⛔ `gate.py` không xanh.
**Bác bỏ:** chạy lại **toàn bộ** test của hai app ở bản trước và bản sau, so từng
kết quả. Không so bằng cảm giác "vẫn chạy".

---

## 16. Định nghĩa "H37 xong"

Mỗi dòng phải trỏ được vào một bằng chứng:

- [x] Giấy phép model đã xác minh, ghi rõ được bán *(G2 — 10/10)*
- [ ] Phần cứng đã đo hết: PCIe, đĩa, nhiệt, trần công suất *(G1)*
- [ ] Model chạy ở **cấu hình cao nhất**, tái lập được theo seed *(G3)*
- [ ] Công thức độ phân giải đã chứng minh bằng so mù, không bằng lời khuyên *(G3)*
- [ ] Cấu hình chọn bằng **so mù ≥ 50 cặp có cặp bẫy**, đo lặp ≥ 3 lần *(G4)*
- [ ] Ba chế độ đã đo, chế độ chưa đạt đã **ghi ra và không mở** *(G5)*
- [ ] Mỗi bước nâng chất lượng đều **chứng minh được là có tác dụng**, không thì bỏ *(G5b)*
- [ ] **Biết khoảng cách tới Gemini và tới trần trọng số mở, TRƯỚC khi mở bán** *(G6b)*
- [ ] Cổng render có test tự động, chạy trên máy A không cần GPU *(G6)*
- [ ] Khởi động lại máy B → dịch vụ tự lên; máy thứ ba trong LAN bị chặn *(G7)*
- [ ] Tắt máy B → khách nhận **thông báo + lựa chọn**, không bị đánh tráo model *(G8)*
- [ ] 100 ảnh 4 MP liên tiếp: không memory drift, không tiết lưu bất ngờ *(G9)*
- [ ] `gate.py` toàn xanh **và** đã kiểm trên `https://app.lttstudios.com` *(G10)*
- [ ] Khách luôn biết ảnh do model nào sinh *(G10)*
- [ ] `DECISIONS.md` · `CHAM_DIEM.md` · tài liệu 3 tầng đã cập nhật *(mọi phase)*

---

## 17. Cần bạn chốt

| # | Cần chốt | Chặn |
|---|---|---|
| 1 | **Trần thời gian mỗi ảnh** — đề xuất **6 phút**. Trên mức đó thì loại, dù đẹp hơn | G4 |
| 2 | **Kích thước giao hàng** — 1920×1080 là 16:9. Còn tỉ lệ nào nữa (1:1, 9:16, 4:3)? Mỗi tỉ lệ cần một bucket huấn luyện tương ứng | G3 |
| 3 | **Bạn chấm ảnh khi nào** — đây là đường găng thật của kế hoạch này, không phải việc máy | G4, G5b, G6b |
| 4 | **Có key GPT Image 2 không** — nếu không thì G6b chỉ đấu Klein 9B + Gemini | G6b |
| 5 | Cửa sổ giờ video/ảnh, hoặc "không đặt" | G7 |

Câu 1–3 chặn sớm nhất. Câu 4–5 chốt dần cũng kịp.

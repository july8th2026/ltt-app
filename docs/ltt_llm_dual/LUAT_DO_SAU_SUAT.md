# Luật đo "sáu suất + hàng chờ" — 14/09/2026

> Chương trình mẹ: `docs/VAN_HANH_THAT.md`. Bộ đo chuẩn: `BO_DO_CHUAN.md`.
>
> Tệp này **chỉ** đặt luật cho một câu hỏi: *ba suất mỗi card, sáu suất hai
> card, và job thứ bảy có vào đúng chỗ khi một suất nhả ra không.*

---

## 1. Ba mệnh đề phải chứng minh, và mỗi cái phải CÓ THỂ SAI

| # | Mệnh đề | Đỏ khi |
|---|---|---|
| **M1** | Mỗi card đạt **3** suất khi đủ tải | đỉnh một tài nguyên ≠ 3 |
| **M2** | Hai card song song, tổng **6** (một card: 3) | đỉnh tổng thiếu, hoặc chỉ một `resource` xuất hiện |
| **M3** | Job chờ **vào ngay** khi một suất nhả | không có cặp (job xong → job chờ được nhận) trong 20 s |
| **M4** | Kết quả trả về **có thật và đầy đủ** | rỗng, < 200 ký tự, hoặc < 20 tok/s tính trên khoảng SINH |
| **M5** | GPU **liền mạch** | < 60 % số mẫu `nvidia-smi` có util ≥ 50 % |

### 🔴 M1 đi một vòng rồi quay lại 3 — ghi cả vòng, vì cái vòng mới là bài học

Lượt đầu đo được **2 suất/card**. Tôi xếp nó vào ngăn *"hệ đúng, kỳ vọng sai"*
và hạ kỳ vọng xuống 2, vì `luat_nhan.py:170` có một luật trông rất cố ý:

```
if sum(1 for g in giu if g.lop != TUONG_TAC) >= tran_nen(so_slot)
tran_nen(so_slot) = max(1, so_slot - 1)
```

⛔ **Xếp ngăn sai.** Hằng số `1` ấy nằm **chết** trong hàm — không ai khai nó,
không ai đo nó, và không cửa nào nói ra rằng mình đang mất một suất. Một hằng số
không khai ra thì *không* phải một quyết định; nó là một mặc định chưa ai xét.
Chủ sản phẩm bác bỏ ngay: *"không trở slot về 2, vì ta đã có hàng chờ job rồi."*

Nay nó là `ThamSo.chua_slot_tuong_tac`, **mặc định 0** ⇒ nền dùng hết slot. Muốn
hành vi cũ thì đặt `1`, và khi ấy nó là một lựa chọn **khai ra**.

📐 Giá phải trả, đo được: `NEN_NHUONG` vẫn chặn mọi lượt nền **mới** khi có người
tương tác đang chờ, nên suất vừa nhả vẫn về tay họ trước hàng job. Thứ mất đi là
suất chờ **sẵn** — họ nay đợi hết một lượt đang chạy thay vì vào ngay.

### 🔴 M3 và M4 từng TRƯỢT vì BỘ ĐO, không vì hệ — và đây là cách phân biệt

Lượt 14/09 sau khi sửa: M1 và M5 xanh, M3 và M4 đỏ. Cả hai đều là lỗi bộ đo:

| | bộ đo làm sai | sửa thành |
|---|---|---|
| **M4** | chia token cho thời gian tính từ lúc **nộp** ⇒ job xếp hàng 170 s cho "17,0 tok/s" trong khi nó sinh ở 35 | chia cho `finished_at − admitted_at` |
| **M3** | ghép cặp bàn giao từ nhịp lấy mẫu **2 giây**; bàn giao thật xảy ra trong vài trăm mili-giây nên không mẫu nào bắt được | đọc thẳng `admitted_at`/`finished_at` trong CSDL |

⛔ **Một phép đo không thấy thì không được phép kết luận "không xảy ra".** CSDL đã
ghi sẵn mốc; đi hỏi nó rẻ hơn nhiều so với tăng tần số lấy mẫu.

⭐ Và M3 phải **có thể sai**: cặp chỉ được tính khi job vào sau thực sự đã **xếp
hàng** (`admitted_at − started_at > 5 s`). Thiếu điều kiện ấy thì hai job chạy
song song từ đầu cũng thành một "cặp", và M3 sẽ xanh ở mọi lô — kể cả lô không
hề có hàng đợi nào.

---

## 1b. Đọc GPU bằng gì — và vì sao Task Manager làm lạc hướng cả một buổi

📐 Đo 14/09 trên máy B, **hai nguồn cùng một khoảnh khắc**, trong lúc 3 job chạy:

```
nvidia-smi GPU0: 67 % · 61 °C · 356 W
bộ đếm Windows:  96,1 %  pid_12480 … phys_0 eng_0 engtype_3d
```

Ba điều rút ra, và cả ba đều đã từng làm tôi kết luận sai trong cùng một buổi:

1. **RTX 3090 không có node `Compute_0`.** Danh sách engine của nó chỉ có
   `3D · Copy · Video Encode · Video Decode · Overlay · Security · OFA_0 · VR ·
   Copy 1-5`. Công việc CUDA của llama.cpp nằm trong ô **`3D`**. Ai bảo "đổi
   dropdown sang Compute_0 đi" — tôi đã bảo thế — là bảo một thứ không tồn tại.
2. **Số `Utilization` ở đáy bảng là giá trị TỨC THỜI**, không phải trung bình của
   đồ thị. Chụp ngay sau khi một lô job xong sẽ ra `0 %` trong khi nhiệt còn
   76–77 °C — card đang nguội, không phải đang chạy nhỏ giọt.
3. **`display_active` KHÔNG nói card nào đang vẽ desktop** — và tôi đã tưởng
   nó nói. Đo được: 3090 `display_active=Disabled`, 5060 Ti `Enabled`; nhưng
   `nvidia-smi --query-compute-apps` lại liệt `dwm.exe`, `explorer.exe`,
   `StartMenuExperienceHost.exe`, `Taskmgr.exe` **trên UUID của 3090**. Màn hình
   cắm ở 5060 Ti, còn desktop **render** ở 3090. Hai câu hỏi khác nhau, và chỉ
   câu thứ hai mới liên quan tới VRAM.

### 🔴 ĐÃ BÁC BỎ: "desktop đang render trên 3090" — kết luận sai của chính tôi

Chiều 14/09 tôi báo động: `nvidia-smi --query-compute-apps` liệt `dwm.exe`,
`explorer.exe`, `Taskmgr.exe` **dưới UUID của 3090**, card chỉ còn 341 MiB — đúng
cấu hình đã gây sự cố 13/09 trên card kia. Tôi suýt tách neo `&ttl_nha` để cho
3090 `ttl: 0`, rồi hoàn nguyên vì lập luận dựa trên `display_active`.

**Cả hai lần tôi đều hỏi sai câu.** Số thật, đo bằng bộ đếm dung lượng:

```
\GPU Adapter Memory(*)\Dedicated Usage      vs   nvidia-smi
luid_0x0038cc5f -> 24.241 MiB                 GPU0 RTX 3090    24.235 MiB
luid_0x0037fdf5 -> 15.425 MiB                 GPU1 RTX 5060 Ti 15.418 MiB
luid_0x00015289 -> không xuất hiện (< 100 MB)      <- dwm.exe nằm ở đây
```

Hai luid của `llama-server` khớp **tuyệt đối** với hai card. `dwm.exe` ở một
**adapter thứ ba gần như không có VRAM riêng** — máy B có hai tiến trình `dwm`
(hai phiên hiển thị), cái đang chạy nằm trên adapter ảo ấy.

⇒ Desktop **không** ở 3090. Biên 341 MiB là do ngân sách `-c 221184` của chính
  ta, không ai tranh.

⛔ **Bài học, và nó tổng quát hơn cái sai:** `--query-compute-apps` trả lời *"ai
   CHẠM vào card"*; `GPU Adapter Memory` / `GPU Process Memory` trả lời *"ai ĂN
   VRAM của nó"*. Tôi dùng câu trả lời thứ nhất cho câu hỏi thứ hai, hai lần,
   và lần nào cũng suýt đổi một tham số production vì nó.

⚠️ `ttl` của `qwen38-api` **vẫn giữ `1800`**. Sự cố 13/09 (`VRAM trống 536 MiB <
   sàn 600 MiB` ⇒ `ltt-3.5` trả 503) xảy ra trên **5060 Ti**, card thật sự cắm
   màn hình — nên lý lẽ ấy không còn áp cho 3090. Nhưng muốn cho 3090 `ttl: 0`
   thì phải chứng minh **trọng tài residency thật sự tháo `3.8`** khi model ảnh
   cần card. Chưa đo ⇒ chưa đổi.

### ✅ Task Manager hiện ĐÚNG cho CẢ HAI card — đo song song 14/09

Ép 3 job `ltt-3.8` + 3 job `ltt-3.5` cùng lúc, đọc hai nguồn cùng khoảnh khắc:

```
mẫu 4   smi  GPU0 86 % 65 °C 348 W      GPU1 72 % 57 °C 124 W
        đếm  96,2 %  pid_12480 luid_0x0038cc5f engtype_3d   (3.8 / 3090)
             68,4 %  pid_20972 luid_0x0037fdf5 engtype_3d   (3.5 / 5060 Ti)
              3,9 %  pid_20972 …               engtype_copy
```

⇒ Giả thuyết *"Task Manager chỉ in ở card xuất hình"*: **bác bỏ**. 3090 có
  `display_active=Disabled` mà vẫn hiện 96,2 %, cùng lúc với card kia.

Sáu job xong sạch: `3.8` ~187 s/job, `3.5` ~141 s/job, ~18.000 ký tự mỗi bài.

⇒ Triệu chứng *"3090 chạy nhỏ giọt"* có **hai nguồn, chỉ một là bug**:

| nguồn | trạng thái |
|---|---|
| `tran_nen` chôn cứng `so_slot − 1` ⇒ card 3 suất chạy 2 ⇒ mỗi lô vỡ làm hai đợt, giữa hai đợt GPU tụt về 0 | **đã sửa + deploy** |
| ảnh chụp Task Manager lấy **sau** khi lô job vừa xong: `Utilization 0 %` là giá trị tức thời, 76–77 °C là card đang nguội | không phải lỗi |

  mọi model" bằng cú pháp YAML chứ không bằng trí nhớ.

⇒ **Nguồn chân lý về GPU là `nvidia-smi`**, và khi cần đối chứng thì lấy bộ đếm
  `\GPU Engine(*)\Utilization Percentage` — cả hai đều hỏi được qua SSH. Đừng
  kết luận từ một ảnh chụp Task Manager, của mình hay của người khác.

⚠️ Và đừng kết luận "bộ đếm không thấy tiến trình" từ **một** mẫu: tôi đã báo
   đúng câu ấy, rồi phát hiện mẫu đó rơi ra ngoài cửa sổ job đã chạy xong. Mẫu
   đơn lẻ về một đại lượng biến thiên không phải bằng chứng.

---

## 2. Job phải DÀI — và đây là ràng buộc, không phải sở thích

Đo 14/09: sáu job `max_tokens=1500` cho đỉnh **3**, không phải 6 — vì chúng kết
thúc **lệch nhau**, không bao giờ chồng đủ. Hàng đợi chỉ quan sát được khi nó
**kịp hình thành**.

⇒ Mỗi job phải dài hơn **tổng thời gian nộp cả lô** ít nhất vài lần. Primitive
đã đo: `ltt-3.8` sinh 8.000 token trong **106 giây**.

---

## 3. Đo CẢ HAI MÁY, cùng lúc, và chúng trả lời hai câu khác nhau

| máy | nguồn | trả lời câu |
|---|---|---|
| **A** | `execution_leases`, `jobs.status` | ta **cấp phát** thế nào |
| **B** | `llamacpp:requests_processing`, `requests_deferred`, `nvidia-smi` | máy B **thật sự làm** gì |

🔑 **Chỉ đo một bên là đo một nửa.** Ngày 14/09 tôi đã kết luận sai hai lần vì
chỉ nhìn máy A: lần đầu đổ cho hồ worker, lần sau bảo `worker-1` chết (nó là
tiến trình cha). Nguyên nhân thật — `reasoning_effort=none` — chỉ lộ ra khi hỏi
máy B.

⭐ **`requests_deferred` là đối chứng.** Nếu máy B **không** hoãn lượt nào mà
máy A vẫn xếp hàng ⇒ hàng đợi là của **máy A**, đúng thiết kế. Nếu máy B hoãn
⇒ ta đang gửi quá sức nó, và con số của máy A vô nghĩa.

---

## 4. Nền phải SẠCH, và phải chứng minh là sạch

Bắt đầu khi `execution_leases` **rỗng** và cả hai `requests_processing` = **0**.

⛔ Nền bẩn thì mọi số sau đó thuộc về một kịch bản **khác**, và nó **không tự
khai** điều đó. Đo được 13/09: một lượt đo bão hoà chạy trúng cửa sổ deploy của
phiên khác, cả sáu job chết cùng một khắc, và kết quả trông **y hệt** một phát
hiện lớn.

---

## 5. Bốn ngăn — phân loại TRƯỚC khi sửa

| ngăn | xử |
|---|---|
| lỗi hệ thống | ghi sổ, gom sửa một lượt |
| lỗi bộ đo | sửa ngay, chạy lại đúng kịch bản ấy |
| nhiễu | chạy lại, **không diễn giải** |
| hệ đúng, kỳ vọng sai | sửa **kỳ vọng**, ghi rõ vì sao |

---

## 6. Điều kiện để nói "PASS"

Cả **năm** mệnh đề đạt, **trên một lượt nền sạch**, với:

- đỉnh mỗi `resource` = **3**; đỉnh tổng = **6** (lô một card: 3);
- ít nhất một **cặp bàn giao** đọc từ CSDL: job xong → job **đã xếp hàng** được
  nhận trong vòng **20 giây**;
- mọi job trả về **có nội dung**, và tốc độ trên khoảng **sinh** ≥ 20 tok/s;
- GPU của card đang đo: ≥ **60 %** số mẫu có util ≥ 50 %;
- `requests_deferred` = **0** suốt lượt ở cả hai cổng;
- **0** job `failed`, **0** mã `429`.

⛔ Thiếu **một** dòng ⇒ **chưa pass**. Không có "pass một phần".

📐 Lượt PASS đầu tiên — 14/09/2026, `--model ltt-3.8 --so-job 5 --ra 6000`:

```
M1 {'ltt_38_3090': 3}   M2 tổng 3   M3 xong 196,2s → vào 198,2s (trễ 2,0s)
M4 5/5 job: 6.000 token · ~21.000 ký tự · 31,3–36,3 tok/s
M5 bận 92 % mẫu · mạch liền 169,5 s · 316 W
đối chứng: deferred 0 · job hỏng 0 · đỉnh hàng chờ 2
```

⚠️ Và một lượt pass **không** chứng minh hệ luôn đúng — nó chứng minh hệ đúng
**ở lượt ấy, ở tải ấy**. Ghi lại tải đã dùng, đừng ghi "hệ ổn".

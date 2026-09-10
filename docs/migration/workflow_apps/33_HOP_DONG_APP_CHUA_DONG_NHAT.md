# 33 — Hợp đồng App chưa đồng nhất: đo, một hướng sai, và chỗ hổng thật

**Ngày:** 2026-09-10 · **Đo trên:** `platform_core.registry.discover()` — 25 App
/ 19 tool, và log worker production (chỉ đọc) ·
**Bằng chứng:** `tests/test_1112_phase13_hai_ban_khai_vram.py`

Câu hỏi: *"cơ chế các App chưa đồng nhất với nhau à?"* — **Đúng**, và chỗ không
đồng nhất ấy đang gây một khiếm khuyết thật. Nhưng nó **không** nằm ở chỗ tôi
đoán lúc đầu, và tài liệu này ghi cả hướng sai vì nó tốn thật.

---

## 1. Đo trước

| Trường hợp đồng ToolSpec v2 | Khai | Không khai |
|---|---:|---:|
| `resource` (`class` · `vram_min_mb` · `slots` · `est_duration_s`) | **4/19** | 15 |
| `admission_resource` + `admission_slots` | 5/19 | 14 |
| `idempotency.key_fields` | **4/19** | 15 |
| `side_effect` | 19/19 | 0 |

⭐ Cả bốn App khai `resource` và `idempotency` đều là bốn App vừa dựng trong
chương trình này. Mười lăm tool còn lại chạy trên tập con v1.

---

## 2. ⛔ Hướng SAI tôi đã đi — ghi lại vì nó tốn thật

Tôi gọi thẳng `jobs.claim()`, thấy hai job cùng `admission_resource="gpu_stt",
slots=1` **đều được nhặt**, và kết luận *"cửa job không giành suất"*. Đã viết một
bản vá cho `platform_core/jobs.py`.

**Sai.** `job_runner.py:226` **có** gọi `admission.hold_persisted(...)` ngay sau
khi nhặt job, và `_tra_ve_hang_doi(...)` khi hết suất. Phép tái hiện của tôi đi
**vòng qua `job_runner`** — đường mà production không bao giờ đi. Bản vá đã hoàn
nguyên (`git checkout -- platform_core/jobs.py`).

⚠️ **Bài học: tái hiện phải đi đúng đường production đi.** Gọi thẳng một hàm ở
   tầng dưới cho ra một hành vi **có thật**, nhưng là hành vi của một đường
   **không ai dùng** — và nó trông y hệt một con bọ.

⭐ Thứ cứu tôi không phải đọc kỹ hơn, mà là một phép đo **ngoài giả thuyết**:
   đọc log worker production. Ở đó có dòng *"job X (ltt_llm.chat) hoãn 20s: tài
   nguyên llm_remote đang bận"* — nếu không ai giành suất thì dòng đó không tồn
   tại được.

---

## 3. Nền tảng thực ra có BA tầng, và cả ba đều đúng

| | Tầng | Ở đâu | Bảo vệ gì |
|---|---|---|---|
| 1 | lọc khi nhặt | `jobs._con_cho_tai_nguyen` | không nhặt job mà tài nguyên đã hết suất |
| 2 | suất tài nguyên **từ xa** | `job_runner:226` `admission.hold_persisted` | máy B, GPU giọng — theo **suất đếm được** |
| 3 | GPU **cục bộ** | `job_runner:284` `gpu_lease.acquire(need_mb=…)` | card thật, theo **dung lượng VRAM** |

Tầng 2 trước tầng 3 là một quyết định có chú thích: *"nếu máy B đang bận, không
được giữ card trên worker chỉ để ngồi chờ một tài nguyên khác."*

⇒ Nền tảng **có** xếp chỗ theo VRAM — lời tôi viết ở bản nháp trước
(*"không ai đọc `vram_min_mb`"*) là **sai**, và §4 nói rõ sai ở đâu.

---

## 4. 🔴 Chỗ hổng THẬT: hai chỗ khai VRAM, chỉ một chỗ được đọc

```
AppManifest.gpu_vram_mb[job_type]      <- `job_runner._vram_can` DOC
ToolSpec.resource["vram_min_mb"]       <- khong ai doc
```

Đo trên registry, trước bản vá:

| App | `gpu_vram_mb` | `resource.vram_min_mb` |
|---|---:|---:|
| `asv_gpu.transcribe` · `autosubvideo.transcribe` · `taoclipngan.render` | 6000 | — |
| `upscalevideo.render` | 12000 | — |
| `ltt_voice.synthesize` | 2000 | — |
| **`transcript.run`** | **0** | 5000 |
| **`audio_pause.run`** | **0** | 5000 |
| **`video_assembly.run`** | **0** | 8000 |

Ba App tôi vừa dựng khai ở chỗ **thứ hai** — nó nằm ngay cạnh `class="gpu"` nên
đọc tự nhiên hơn — và để trống chỗ thứ nhất.

⇒ `need_mb = 0` ⇒ `_giu_gpu` trả `(None, False)` ngay ⇒ **ba App GPU chạy không
  có lease nào**, đè thẳng lên `taoclipngan`/`upscalevideo` trên cùng một card.

### Vì sao không phép kiểm nào bắt được

Cả hai bản khai đều **hợp lệ**: một cái rỗng, một cái đầy, và **không có gì nói
chúng phải khớp**. `_validate_hop_dong_v2` kiểm *hình dạng* của `resource` rất
kỹ — khoá lạ, kiểu sai, giá trị âm — nhưng không hỏi câu duy nhất quan trọng:
**ai đọc con số này?**

⭐ Bài học rộng hơn con bọ: **một trường được kiểm kỹ vẫn có thể là một trường
   không ai đọc.** Kiểm hình dạng và kiểm có-người-tiêu-thụ là hai việc khác nhau.

---

## 5. Bản vá — một phép hợp nhất, không phải một luật mới

**① `vram_for()` hợp nhất hai bản khai** (`platform_core/registry.py`):
`gpu_vram_mb` thắng khi có (theo `job_type`, mịn hơn); không có thì lấy
`ToolSpec.resource["vram_min_mb"]` của tool sinh ra `job_type` ấy. Sau đó hai
chỗ khai **không thể lệch nhau nữa**.

**② Ba App khai thêm `gpu_vram_mb` + `cho_tai_nguyen_s`** — để bản khai mịn theo
`job_type` là nguồn chính, đúng như mọi App GPU khác.

**③ Bánh cóc:** mọi tool khai `class="gpu"` phải cho `vram_for() > 0`.

Đây là **bất biến**, không phải danh sách — App mới thêm cũng phải qua. Đối chứng
đã có sẵn: trước bản vá, ba App của tôi làm bài này **đỏ**.

⚠️ Nếu bài ấy đỏ thì App vừa thêm đang **đè lên card của App khác**, và triệu
   chứng ở production sẽ là OOM ở một App **thứ ba** không liên quan, vào lúc hai
   job tình cờ trùng nhau. Đó là lý do nó đáng chốt ở đây.

---

## 6. Đối chiếu cộng đồng: Kubernetes

Hai điểm thẳng vào ca này (`manage-resources-containers`, `scheduling-gpus`):

**① Bản khai LÀ đầu vào của bộ xếp lịch, luôn luôn.** *"kube-scheduler uses this
information to decide which node to place the Pod on… the scheduler still refuses
to place."* Trong K8s **không tồn tại** trạng thái "khai mà không ai đọc":
`requests` là đầu vào của bộ xếp lịch, `limits` của kubelet. Hai người tiêu thụ,
cả hai đều thật.

**② Một tài nguyên, một chỗ khai.** K8s phơi `nvidia.com/gpu` là **một** khoá
đếm được; tài liệu ghi rõ *"You cannot specify GPU `requests` without specifying
`limits`"* — nó **cưỡng chế sự nhất quán giữa hai bản khai** thay vì để chúng
trôi. Đó chính xác là thứ §5-① vừa làm.

⇒ Bài học mượn được: chỗ nguy hiểm không phải "thiếu một trường" mà là **hai
  trường nói cùng một điều mà không ai bắt chúng khớp**.

---

## 7. Còn "đồng nhất hoá" 15 tool cũ thì sao

**Không đề xuất làm ngay**, và lý do là phép đo chứ không phải sở thích:

* 14/19 tool **không dùng tài nguyên dùng chung** — khai thêm là thêm chữ, không
  thêm ràng buộc;
* `idempotency.key_fields` chỉ có nghĩa khi job **nộp trùng** được — với App sinh
  ảnh theo prompt tự do thì hai lượt giống hệt vẫn là hai đơn hàng;
* mỗi lần khai thêm một trường **đang được cưỡng chế** là một lần đổi hành vi của
  một App đang bán thật.

⇒ Tiêu chí đúng không phải *"mọi App khai mọi trường"* mà là **"mọi App dùng tài
  nguyên dùng chung đều khai, và mọi thứ đã khai đều có người đọc"**. Sau §5 thì
  vế thứ hai đúng cho VRAM; các trường còn lại chưa kiểm — nói ra chứ không nhận
  là đã xong.

---

## 8. Số đo phụ, đáng để lại

Log worker production, toàn bộ lịch sử:

```
so JOB bi hoan it nhat mot lan : 102
tong so luot hoan             : 10.008
hoan nhieu nhat cho MOT job   : 554 lan
trung vi luot hoan / job      : 49
theo loai: ltt_llm.chat 9.935 · ltt_voice.synthesize 73
theo ly do: llm_remote dang ban 9.935 · vieneu_gpu dang ban 73
```

Cơ chế chờ tài nguyên **đang chạy đúng** — nhưng một job bị đánh thức 554 lần
trong đời nó là một vòng bận, không phải một hàng đợi. Giãn cách của `ltt_llm`
là 20 giây; 554 × 20 s ≈ **3 giờ** chỉ để chờ.

⚠️ Đây là quan sát, **không** phải đề xuất sửa: nó thuộc `ltt_llm` và máy B, ngoài
   phạm vi chương trình này. Ghi ra để người phụ trách nó có con số.

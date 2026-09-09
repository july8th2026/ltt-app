# 07 — TỔNG HỢP CHÉO BỐN BOT

Đóng băng **trước khi viết một dòng App nào**. Nguồn: `03`–`06` cùng thư mục.

| Bot | SHA | `.py` | dòng |
|---|---|---:|---:|
| `bot_transcript` | `278ed8d7` | 54 | 17.251 |
| `bot_pause` | `97a021a1` | 29 | 10.423 |
| `bot_gem` | `0bc47735` | 146 | 52.811 |
| `bot_dungvideo` | `b0e25ed4` | 165 | 40.328 |

---

## 1. Trùng lặp — đo bằng md5, không đoán bằng tên

### 1a. Bảy module dùng chung: **byte-identical ở cả ba kho**

| Tệp | transcript | pause | dungvideo |
|---|---|---|---|
| `bot_coordination.py` (1.055) | `15d1abd0` | `15d1abd0` | `15d1abd0` |
| `bot_logger.py` (383) | `dd969a42` | `dd969a42` | `dd969a42` |
| `drive_utils.py` | `358a73c5` | `358a73c5` | `358a73c5` |
| `gpu_arbiter.py` (1.520) | `c22466bd` | `c22466bd` | `c22466bd` |
| `gpu_claims.py` (340) | `48fded47` | `48fded47` | `48fded47` |
| `gpu_recorder.py` (691) | `21914128` | `21914128` | `21914128` |
| `job_claimer.py` | `e45de859` | `e45de859` | `e45de859` |

`SHARED_MODULES.md` trong mỗi kho tự khai cơ chế: bản gốc ở `D:\FULL AUTO VIDEO\`,
mỗi kho giữ **một bản sao thật, không phải symlink**, và nghĩa vụ đồng bộ là
*"sửa gốc → copy đè ba nơi → commit cả ba"*.

⇒ **Cả bảy: `DROP_LEGACY`.** Không phải vì trùng lặp, mà vì LTT **đã có** thứ
thay thế, tốt hơn, và đang chạy thật:

| Legacy | LTT thay bằng |
|---|---|
| `job_claimer.py` (khoá bằng ô Sheet) | `platform_core/jobs.py::claim()` — `FOR UPDATE SKIP LOCKED` |
| `gpu_arbiter` · `gpu_claims` · `gpu_recorder` | `platform_core/gpu_lease.py` · `leases.py` · `ToolSpec.admission_*` |
| `bot_coordination` (VramBudget/GpuSlot) | như trên |
| `drive_utils` | `platform_core/storage.py` |
| `bot_logger` | `platform_core/observability.py` |

⭐ **Đây là phần thắng lớn nhất của cả chương trình, và nó đo được:**
1.055 + 1.520 + 340 + 691 + 383 = **~4.000 dòng × 3 kho = ~12.000 dòng biến mất**,
đổi lấy các trường trong bản khai manifest.

### 1b. `bot_gem` tự trùng với chính nó

`core/chatgpt_automation.py` và `chatgpt_automation.py` — **md5 `2929b1f7` khớp
hoàn toàn**, 1.432 dòng ×2 trong cùng một kho.

---

## 2. 🔴 STT: bốn hồ sơ, không phải một năng lực dùng chung

Ba bot "cùng gọi whisper". Đo lời gọi thật:

| | `word_timestamps` | `vad_filter` | `beam_size` | `condition_on_prev` |
|---|---|---|---|---|
| **transcript** `engine/stt.py:303` | **`True`** *(chú thích: "HARD RULE")* | **không có** | 1 | `False` |
| **pause** `engine/stt.py:337` | tham số | **`True`** `min_silence=500` `pad=200` | config | config |
| **dungvideo** `engine/stt.py:48` | **`False`** | **`True`** `min_silence=500` `threshold=0.5` | 5 | `False` |
| **dungvideo/evaluation** `adapters/whisper.py:361` | `False` | **`False`** | — | — |

⛔ **Bốn hồ sơ này KHÔNG hoà được thành một mặc định.** Ba lý do, mỗi lý do đủ
để một mình chặn:

1. `transcript` **cấm** `vad_filter` vì nó chạy VAD riêng (`engine/vad.py`) ở
   tầng trên; bật thêm là VAD hai lần.
2. `pause` **dùng chính ranh giới đoạn** của `vad_filter` (kèm `speech_pad_ms=200`)
   để quyết định cắt ở đâu. Đổi ranh giới là đổi vị trí chèn lặng.
3. `transcript` cần `word_timestamps=True` (có phép kiểm ném lỗi nếu thiếu);
   `dungvideo` cố ý **tắt** nó vì không cần và nó đắt.

🔑 **Quyết định đóng băng**: **một** service STT, **bốn** hồ sơ tham số đã đặt
tên, mỗi App khai hồ sơ của mình. **Không có "tham số mặc định hợp lý".**

⭐ Đây chính là ca mà MASTER-GUARDRAILS #12 mô tả: cùng một *cái tên* năng lực,
khác *ngữ nghĩa*. Gộp trước khi audit ngữ nghĩa là đẻ ra một `common_utils.py`
làm hỏng ba bot cùng lúc — và hỏng **im lặng**, vì cả ba vẫn chạy và vẫn ra file.

---

## 3. Điều phối legacy — cùng một hình dạng ở cả bốn bot

```
vòng lặp vô hạn → quét Google Sheet từng dòng → lọc theo cột trigger/status
→ ghi khoá vào ô → tải từ Drive → CHẠY ENGINE → upload Drive → ghi link về ô
```

| Mảnh legacy | Số phận | LTT thay bằng |
|---|---|---|
| vòng quét + lịch (`schedule_col`) | `DROP` | hàng đợi job |
| khoá bằng ô Sheet | `DROP` | `jobs.claim()` |
| Drive làm kho trạng thái | `DROP` | `platform_core/storage.py` + Artifact |
| máy trạng thái cột `status` | `DROP` | `Job.status` |
| trọng tài GPU cục bộ | `DROP` | admission + lease |
| GUI Tkinter (≥13.000 dòng cả bốn) | `REWRITE_LTT` | GUI web-native |
| `state_manager` / `recovery` / `progress_tracker` | `DROP` | job events |

---

## 4. Ranh giới đã đóng băng

### 4a. Macro Node đi qua **Agent**, không qua Canvas V2

Theo `02_LTT_RUNTIME_BASELINE.md`: `WorkflowRun` **không dispatch job** (cạnh ấy
chưa tồn tại), còn Agent executor thì đủ mắt xích và đang sống.
⇒ Macro Node của bốn App = **một `ToolSpec` trong manifest**.

### 4b. Cái gì được nâng xuống Core, cái gì không

| Năng lực | Ở đâu | Vì sao |
|---|---|---|
| STT (một service, bốn hồ sơ) | **dùng chung** — `platform_core` hoặc thư viện | ba App cần; ngữ nghĩa đã đo |
| ffmpeg / cắt / ghép / mã hoá | `platform_core/media.py` (**đã có**) | dùng chung sẵn |
| kiểm ảnh/tệp tải lên | `platform_core/image_input.py` (**đã có**) | |
| VAD | **của App transcript** | chỉ một App dùng |
| khớp mốc mờ · lập kế hoạch chèn · dịch mốc | **của App pause** | |
| lái trình duyệt · nhịp lô · lịch sử cảnh | **của App gem** | |
| khớp clip · lọc · phụ đề · trộn tiếng | **của App video** | |

⛔ Không tạo `common_utils.py`. Một năng lực chỉ xuống Core khi **≥2 App** cần
**và** ngữ nghĩa đã được so — hôm nay đúng một mục qua được cửa đó: STT.

### 4c. Thứ tự build — `pause` TRƯỚC, không phải `transcript`

| # | App | Vì sao thứ tự này |
|---|---|---|
| 1 | **pause** | nhỏ nhất (10.423), 5 module engine **thuần hàm**, không model ngoài whisper, parity đo được bằng số. Lát cắt dọc rẻ nhất để chứng minh hợp đồng App+Node. |
| 2 | **transcript** | mang theo hồ sơ STT thứ hai ⇒ ép service STT lộ ra đúng hình dạng ở App thứ hai, không phải ở App thứ tư |
| 3 | **dungvideo** | nặng nhất về tài nguyên; đi sau khi admission/lease đã chạy thật hai lần |
| 4 | **gem** | có điều kiện DỪNG chưa gỡ (nhánh nào, provider nào, tài khoản nào) |

⭐ Prompt pack xếp `transcript` trước. Đổi thứ tự có lý do đo được: `pause` ít
phụ thuộc hơn ở **mọi** trục — dòng mã, số model, số kho ngoài, độ khó parity.
Đây là một đề xuất, **chờ chủ dự án duyệt** vì nó lệch pack.

---

## 5. Bảng nợ mở

| # | Hạng mục | Chặn ai | Trạng thái |
|---|---|---|---|
| S1 | ~~`bot_gem` nhánh nào~~ | — | **ĐÓNG 09/09**: chủ dự án chọn `master` |
| S2 | ~~giữ trình duyệt hay đổi API~~ | — | **ĐÓNG 09/09**: bỏ hẳn trình duyệt, đi `runtime_noi_bo` — xem `09` |
| S3 | ~~tài khoản chạy E2E cho gem~~ | — | **KHÔNG CÒN** — hệ quả của S2 |
| S4 | ~~`matcher.py` chưa đọc~~ | — | **ĐÓNG 09/09** — `06` §S4 |
| S5 | ~~`find_silence_point` chưa đo~~ | — | **ĐÓNG 09/09** — `04` §S5 |
| S6 | ~~`word_scene_builder.py` chưa đọc~~ | — | **ĐÓNG 09/09** — `03` §S6 |
| S7 | ~~`gemini_automation` vs `gemini_client`~~ | — | **KHÔNG CÒN** — cả hai bị bỏ theo S2 |
| S8 | ~~`configs/` thật~~ | — | **ĐÓNG 09/09** — đọc từ `D:\FULL AUTO VIDEO`, xem `08` |
| S9 | ~~đổi thứ tự build~~ | — | **ĐÓNG 09/09**: giữ thứ tự pack, `transcript` trước |
| **S10** | `engine/music/mood.py` **chỉ có ở bản chạy**, không có trong kho git | Phase 11 | đọc trước khi viết service |
| **S11** | sửa parity matrix `03`/`04`/`06` theo bảng đính chính `08` §1 | 08·09·11 | **mở** |
| **S12** | `smart_silence.default` vs `timeline.silence_text` — hai chuỗi khác nhau | Phase 08 | đo đường nào dùng chuỗi nào |
| **S13** | hồ sơ STT của `pause` là **hàm của `language`** (vi=5/3, en=1/1) | Phase 09 | sửa §2 tệp này |
| **S14** | production chạy `timeline.mode=sequential`, **không** phải `semantic` | Phase 11 | đảo thứ tự ưu tiên trong `06` |

✅ **S4–S6 đóng ngày 09/09, TRƯỚC khi viết một dòng service nào** — đúng thứ tự
mà MASTER-GUARDRAILS đòi. Cả ba trả về một thứ mà một bản port hợp lý sẽ làm sai
và **không phép kiểm nào kêu**:

| | Thứ suýt mất |
|---|---|
| S4 | khớp clip **tham lam, phụ thuộc thứ tự** — một bản "tốt hơn" cho kết quả khác |
| S5 | nới vùng tìm **+300 ms** khi `gap < 0.10`, vì mốc Whisper sớm hơn thực tế 100–200 ms |
| S6 | **hai** tầng giới hạn độ dài, tình cờ trùng số (6.0) ở cấu hình mặc định |

⭐ Cả ba đều cùng một hạng: **một hằng số trông tuỳ tiện, thật ra là một lần hỏng
đã trả giá.** Đó là lý do "đọc mã trước khi viết service" không phải một nghi
thức — nó là chỗ duy nhất ba thứ này còn được ghi lại.

⛔ Còn lại: `S1`–`S3` (chủ dự án quyết) và `S8` (`configs/` thật trên máy chủ).

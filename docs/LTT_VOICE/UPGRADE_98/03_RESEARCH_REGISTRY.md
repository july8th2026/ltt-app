# 03_RESEARCH_REGISTRY — nguồn ngoài, và thứ RÚT RA được từ mỗi nguồn

Kho nghiên cứu: `D:\LTT_VOICE_RESEARCH\repos\` — **ngoài** cây LTT, đúng §1.
SHA ghim ở `D:\LTT_VOICE_RESEARCH\RESEARCH_SOURCES.lock.json`.
Clone 09/09/2026, `--depth 1`, **không tải trọng số** (§12).

## 1. Bảy kho đã lấy — 254 MB, giấy phép đều permissive

| kho | SHA (rút gọn) | giấy phép **mã** | cỡ | mở khoá hạng mục |
|---|---|---|---|---|
| `pnnbao97/VieNeu-TTS` | `3206ed96` (09/09) | Apache-2.0 | 9,5 M | 04, 20, 39 |
| `k2-fsa/OmniVoice` | `08be0b4c` (24/08) | Apache-2.0 | 2,0 M | 04 (U-19) |
| `SWivid/F5-TTS` | — | MIT | 3,7 M | 04, 20 |
| `resemble-ai/chatterbox` | — | MIT | 3,4 M | 20, 75 |
| `wavlab-speech/versa` | — | Apache-2.0 | 26 M | 27, 30, 31, 32 |
| `vllm-project/vllm` | — | Apache-2.0 | 167 M | **13, 14, 15 (U-20)** |
| `NVIDIA/NeMo-text-processing` | — | Apache-2.0 | 42 M | 21–26 |

⚠️ Cột giấy phép là của **MÃ NGUỒN**. §35.17: giấy phép mã ≠ giấy phép trọng số
≠ nguồn gốc dữ liệu ≠ quyền với giọng người. `giay_phep_trong_so` trong tệp
khoá ghi `CHUA KIEM` cho sáu kho — chỉ VieNeu đã kiểm (Apache-2.0 cả hai, ghi ở
`01_KHOA_UPSTREAM.md §1`).

---

## 2. VieNeu-TTS — thu hoạch lớn nhất, và nó đổi điểm của hạng mục 20

### 2.1 Bản ta ghim đã đi sau upstream 20 ngày

```
LTT ghim   : 36c4b50  (v3.3.0, 20/08/2026)
upstream   : 3206ed96 (09/09/2026)
```

Ghim revision là **đúng** (`01_KHOA_UPSTREAM` §1 nêu lý do: bản v3 full sắp ra
và sẽ đổi hành vi mà không đổi tên repo). Ghi khoảng cách ra đây để nó là một
quyết định có ý thức, không phải một sự trôi.

### 2.2 `infer_stream` CÓ trên đường GPU của ta

Đo trên mã upstream, không suy:

```
src/vieneu/v3turbo.py:47   class V3TurboVieNeuTTS   """VieNeu-TTS v3 Turbo (PyTorch)."""
src/vieneu/v3turbo.py:514  def infer_stream(...) -> Generator[np.ndarray, None, None]
```

`infer_stream` được định nghĩa trên **bảy** lớp, gồm `V3TurboVieNeuTTS` — đúng
model ta ghim (`pnnbao-ump/VieNeu-TTS-v3-Turbo`) — và `TurboGPUVieNeuTTS`.
Thân hàm ưu tiên streaming **mức khung** của engine, lùi về một `infer` đầy đủ
mỗi đoạn khi không có.

### 2.3 Cái bẫy: `supports_streaming: False`

`apps/gradio_main.py` khai `"supports_streaming": False` cho **mọi** backbone,
kể cả v3 Turbo. Đó là cờ của **app demo**, không phải năng lực của SDK.

⭐ **Một phiên trước đã tự tìm ra đúng điều này và xử lý đúng.**
`voice_sidecar/engine.py:256`:

```python
def co_streaming(self) -> bool:
    """Dò NĂNG LỰC LÚC CHẠY, không đọc `config.yaml`.
    ⛔ `config.yaml` của upstream khai `supports_streaming: false` cho **mọi**
       backbone trong khi `infer_stream` chạy thật trên cả hai engine. Đọc
       trường metadata đó là tự khai sai năng lực của chính mình.
    """
    return callable(getattr(getattr(self._tts, "engine", None), "infer_stream", None))
```

Nghiên cứu upstream **xác nhận** lời khai ấy đúng. Đây là giá trị thật của lượt
tải kho này: một câu khẳng định trong docstring nay có bằng chứng ngoài.

### 2.4 ⇒ Hạng mục 20 phải chấm lại

Baseline chấm **20/100** cho streaming. Sai lệch về phía quá khắt khe. Đo lại:

| lớp | trạng thái ĐO ĐƯỢC |
|---|---|
| SDK upstream `infer_stream` | ✅ có, trên đúng lớp PyTorch ta chạy |
| `engine.co_streaming()` | ✅ dò lúc chạy |
| `engine.phat_dan()` | ✅ generator float32, **giữ suất suốt generator** |
| sidecar `POST /v1/stream` | ✅ đủ: cờ, kiểm năng lực, `_wav_header_mo` + `_pcm16`, `StreamingResponse` |
| cờ `LTT_VOICE_STREAM` trên production | ❌ **không đặt** (`nssm get` không thấy) |
| `sidecar_client` bọc | ❌ không có (`test_504` ghim) |
| route web / JS / player | ❌ không có |
| hợp đồng Public API | ❌ chưa — cửa tự khai *"chưa phải hợp đồng STREAM của Public API (Q119/QĐ-5)"* |

⇒ Điểm đúng: **55**, không phải 20. Bốn trong tám lớp đã xong, và lớp khó nhất
(engine + sidecar + an toàn admission) là bốn lớp đã xong đó. Trần vẫn **75**
(§7.1: có code chưa nối runtime) cho tới khi nối tới khách.

⇒ Và U-07 **không phải** "xây streaming". Nó là **nối bốn lớp còn lại**.

---

## 3. vLLM — khuôn cho U-20 (hạng mục 13, 14)

### 3.1 Hai thứ rút ra được, nguyên văn từ mã

**(a) Khoá xếp thứ tự.** `vllm/config/scheduler.py:146`:

> *"priority" means requests are handled based on given priority (lower value
> means earlier handling) and time of arrival deciding any ties*

**(b) Chọn nạn nhân khi phải nhường.** `vllm/v1/core/sched/scheduler.py:746`:

```python
preempted_req = max(self.running, key=lambda r: (r.priority, r.arrival_time))
```

⇒ Cùng một khoá `(priority, arrival_time)` dùng cho **cả hai** chiều: `min` để
chọn ai được chạy, `max` để chọn ai bị nhường. Một khoá, hai đầu — không có
bảng luật thứ hai để lệch.

### 3.2 Áp vào ta như thế nào — và chỗ nó KHÔNG áp được

`claim()` của ta hiện xếp:

```python
.order_by(aged_first, never_served_first, last_account_claim, Job.created_at, Job.id)
```

Ta **đã có** thứ vLLM không có: fair-share theo tài khoản + aging. Ta **thiếu**
thứ vLLM có: một trục ưu tiên, và một cơ chế **nhường giữa chừng**.

🔴 Nhưng chỗ khác biệt mới là chỗ đáng tiền, và nó chặn việc chép thẳng:

> vLLM nhường được vì sinh LLM **phục hồi lại được ở mức token** (tính lại KV
> cache). Sinh TTS của ta **không** phục hồi ở mức token — nó phục hồi ở mức
> **ĐOẠN**, và ta đã có sẵn nguyên thuỷ ấy: `text_pipeline` chia theo ranh giới
> câu, `noi_dai`/`ghep_tep` ghép lại.

⇒ Phương án A của §20 (*chunk-level cooperative scheduling*) **chính là** bản
tương ứng của preemption vLLM trong bài của ta. Ta không phải phát minh nó; ta
phải quyết có nhận nó không.

### 3.3 ⛔ Và nó đâm thẳng vào một quyết định đã có lý do

`voice_sidecar/engine.py:355`:

```python
def phat_dan(...):
    """Suất chạy được giữ **suốt cả generator** — nhả sớm là để lượt thứ hai
    chen vào giữa lúc lượt đầu còn đang chiếm engine."""
```

Nhả suất giữa chừng là **đúng thứ dòng đó cấm**. Nên phương án A không phải một
bản vá; nó là một **đổi hợp đồng** giữa lịch và engine, và phải đi qua
`05_DECISIONS.md` với phương án B/C/D đặt cạnh, không được lặng lẽ sửa.

---

## 4. Ba kho còn lại — dùng vào đâu

| kho | rút cái gì | hạng mục |
|---|---|---|
| `versa` | Khuôn đo hợp nhất: CER/WER + UTMOS/DNSMOS + speaker similarity trên **cùng một corpus**, có cấu hình khai báo. Ta đã có bộ đo riêng dày (`do_chat_luong.py` 782 dòng); giá trị ở đây là **phương pháp corpus và cách báo phân bố**, không phải thay bộ đo | 27, 30, 31, 32 |
| `NeMo-text-processing` | WFST cho TN/ITN — tách "số/ngày/tiền" khỏi "phiên âm", đúng ý U-15. Đọc **cấu trúc phân tầng**, không chép luật tiếng Anh vào tiếng Việt | 21–26 |
| `OmniVoice` (k2-fsa) | Ứng viên engine thứ hai. 10.794 sao, Apache-2.0 mã. ⛔ Chỉ vào sau khi benchmark chứng minh một gap engine THẬT (§13), và sau khi **giấy phép trọng số** được kiểm riêng | 04 (U-19) |
| `F5-TTS`, `chatterbox` | Đối chiếu kiến trúc + `resemble-perth` (watermark ta đang dùng, ghim `1.0.1`) | 04, 20, 75 |

---

## 5. `D:\Viral` — kết luận pháp lý, chốt lại

Không phải kho mã TTS: là thư mục cài của app Electron đóng gói. Mã đọc được ở
`resources\app-src\`.

| tài sản | phán quyết |
|---|---|
| `MediaCrawler/` | fork NanmiCoder — **phi thương mại** ⇒ không đụng |
| `capcut_tts.py` / `capcut_asr.py` | endpoint dịch ngược ⇒ **NGHIÊN CỨU THÔI** |
| `giong_11labs/` | tài sản ElevenLabs ⇒ **KHÔNG IMPORT** |
| `giong_piper.py` | ⭐ đã dùng đúng cách rồi: bài học "lùi nam → nữ" của nó được **trích nguyên văn** vào `lui_giong.py` làm căn cứ cấm nới giới. Đó là tái dùng ở mức **KHÁI NIỆM** — đúng loại |
| phần còn lại | UNLICENSED/private |

⇒ Không có tài sản nào của `D:\Viral` được nhập vào sản phẩm. LTT không cần:
engine riêng đã có, và giấy phép của nó sạch hơn.

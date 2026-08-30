# LTT VOICE — phương án kiến trúc và lộ trình triển khai

> Ngày lập: **2026-08-30**. Nhánh: `admin-mvp-v3`.
> Nguồn yêu cầu: `LTT_VOICE_VIENEU_PROMPT_PACK_V2` (20 prompt, 00–19) — bản
> "adaptive / evidence-first".
> Trạng thái: **KẾ HOẠCH — chưa có một dòng mã nào được viết.**

Tài liệu này là kết quả của **Pha 01 + 02** trong pack (forensic baseline +
upstream due diligence), cộng với phương án và lộ trình. Mọi khẳng định được gán
nhãn **[V]** (verified — đọc được từ mã/API/tài liệu upstream hôm nay), **[S]**
(suy ra), **[Đ]** (đề xuất).

---

## 0. Điều pack yêu cầu ta làm trước tiên, và kết quả

Pack V2 có một luật trung tâm: *"Đừng bắt mã nguồn vừa với prompt. Hãy bắt lời
giải vừa với mã nguồn và mục tiêu sản phẩm."* Nó liệt kê một danh sách giả định
của V1 và **cấm coi chúng là chân lý** cho tới khi kiểm.

Đã kiểm hết, ngày 30/08:

| Giả định V1 mà pack bắt kiểm lại | Kết quả trên kho này |
|---|---|
| `platform_core/` là nơi đặt hạ tầng dùng chung | **[V] ĐÚNG** — 40+ module, là authority thật |
| PostgreSQL là nguồn chân lý | **[V] ĐÚNG** — job/credit trong Postgres (`ho_so_he_thong.txt` §1) |
| Cổng cố định | **[V] ĐÚNG** — nền tảng 8100; ComfyUI 8188; render gw 8199; llama-swap 8280; llm gw 8299 |
| Jinja2 + CSS một tệp | **[V] ĐÚNG MỘT NỬA** — Jinja + `ltt.css` (có `?v={{ asset_ver }}`) là mặc định; **ba** app nặng dùng bundle React/Vite qua `platform_core/frontend_bundle.py` (`agent-canvas`, `autosub-studio`, `prompt-ai-ommi`) |
| `core/` đóng băng | **[V] LỖI THỜI** — `core/` đã bị xoá gần hết (Q108/Q109, 2026-08-25) |
| Worker topology cố định | **[V] ĐÚNG VÀ QUAN TRỌNG HƠN PACK BIẾT** — worker là tiến trình riêng, **số tiến trình mặc định bằng số GPU**, việc nền phải nằm dưới lease (H36) |

⭐ Kết luận đáng ghi: **cảnh báo của pack đúng về phương pháp nhưng lệch mục
tiêu.** Các giả định topology của V1 gần như đều còn đúng. Thứ pack **không biết**
mới là thứ làm đổi kế hoạch — xem §1.

---

## 1. Năm thứ pack không biết, và chúng đổi kế hoạch thế nào

Pack được soạn ngoài kho này, nên nó thiếu năm sự thật lớn. Mỗi cái xoá hoặc thu
nhỏ hẳn một pha của nó.

### 1.1 [V] Đã có **khuôn bán model nhà** — 6 tầng, 31 chốt

`docs/KHUON_BAN_MODEL_NHA.md`. Nó ra đời sau khi H37 (model ảnh nhà) bị chấm
**18/31** *sau khi đã chạy*, và cuộc chấm đó tìm ra **một lỗi tiền đang sống**:
khách xin 4 ảnh, máy trả 2, vẫn bị thu tiền 4 — vì handler không báo
`credit_cost`.

⇒ **LTT VOICE phải được chấm theo khuôn này từ ngày đầu, không phải sau.** Đây là
lưới nghiệm thu thật, thay cho `templates/PHASE_REPORT.md` của pack (giữ phần
VERIFIED/INFERRED và Decision Table của pack, nhưng cột "đạt / không đạt" lấy từ
khuôn).

### 1.2 [V] Pha 13 của pack ("API access, keys, usage control") **đã xong ~90%**

Nền tảng đã có: khoá API có scope, `upload_sessions`, `Idempotency-Key`, quota,
rate-limit, usage attribution, webhook, sandbox mode, và **cổng ba lớp fail-closed**
(`api_exposed` × `LTT_PUBLIC_API` × `LTT_PUBLIC_API_TOOLS`).

⇒ Pha 13 của pack co lại thành **một tệp manifest và một dòng trong
`APP_API_COVERAGE_FINAL.md`**. Không được dựng identity hay billing thứ hai.

### 1.3 [V] Public API **đã nói được `audio`** — không cần sửa nền tảng để nhận/trả tiếng

`platform_core/public_api/media.py`:

```
"audio": (("audio/mpeg", "audio/mp4", "audio/wav", "audio/x-m4a"), 64 MB)
```

và `catalog.py` đã ánh xạ kiểu tham số `audio` → `string`, kiểu đầu ra `audio` →
`artifact`.

⚠️ **Nhưng `audio[]` thì KHÔNG** — `invocation._MEDIA_TYPES` chỉ có
`{image, image[], video, video[], audio}`. ⇒ Hợp đồng công khai của LTT VOICE là
**một tệp tiếng vào, một tệp tiếng ra** cho mỗi lượt gọi. Đừng thiết kế một tool
trả mảng audio rồi phát hiện điều này ở cuối.

### 1.4 [V] Máy B có **ba hộ đang tranh một card**, và đó là rủi ro số một của mọi dự án model nhà

RTX 3090 24 GB: dự án video từng ăn **98,7 %** VRAM trong 72,5 phút;
`llama-server` ghim **15,9 GB**; model ảnh đỉnh **20,1 GB**. Máy A thì chỉ có
2× 16 GB VRAM **và đang phục vụ khách trả tiền trên 32 GB RAM** (Q102).

⇒ §2 dưới đây cho thấy vì sao đây lại là **tin tốt** cho VOICE, khác hẳn ảnh và LLM.

### 1.5 [V] Đã có sẵn hạ tầng để đo chất lượng tiếng Việt

- `apps/qualitylab/` (operator-only) — đo hợp đồng + chất lượng bằng **bằng chứng
  có phiên bản**, đã có tài liệu hiệu chuẩn và A/B người.
- Sidecar **WhisperX / faster-whisper** đã chạy thật trong `apps/autosubvideo/` ⇒
  có ngay ASR để tính CER/WER cho tiếng Việt mà **không phải thêm phụ thuộc nào**.
- `platform_core/media.py` có `ffprobe` / `duration_seconds` ⇒ đo thời lượng thật
  của tệp sinh ra (thứ dùng để **quyết toán tiền**).

⇒ Pha 15 của pack không phải xây từ đầu; nó là **một bộ đo mới trong Quality Lab**.

---

## 2. Sự thật upstream VieNeu — đo ngày 2026-08-30

Pack tự nói: *"Đừng tin pack này, VieNeu đi rất nhanh."* Đúng. Đã kiểm trực tiếp.

| Hạng mục | Sự thật hôm nay |
|---|---|
| Kho chính thức | **[V]** `pnnbao97/VieNeu-TTS` — Apache-2.0, 2.453 ★ |
| Commit mới nhất | **[V]** `36c4b50` (2026-08-20) |
| Tag mới nhất | **[V]** `v3.3.0` (`f49d70246f18`) |
| Gói PyPI | **[V]** `vieneu==3.3.0`, Python ≥ 3.10, Apache-2.0 |
| Mặc định SDK | **[V]** **v3 Turbo, 48 kHz** (v2 là 24 kHz — mô tả kho vẫn ghi 24 kHz, đó là v2) |
| Cài tối thiểu | **[V] KHÔNG CÓ TORCH**: `onnxruntime`, `sea-g2p`, `soxr`, `kaldi-native-fbank`, `tokenizers`, `soundfile`, `librosa`, `perth` |
| Codec / G2P | **[V]** `OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano`; `pnnbao97/sea-g2p` |
| Nhân bản giọng | **[V]** clip **3–8 giây**, tự khử nhiễu, `add_voice()` → hồ sơ giọng; `save_voices()` theo spec `vieneu.voice.presets v1.0` |
| Giọng dựng sẵn | **[V]** 20 giọng, 3 vùng (Bắc / Trung / Nam) |
| `style` | **[V] ĐÃ BỎ** trên v3 Turbo — vẫn nhận tham số nhưng **bị bỏ qua** |
| Cảm xúc | **[V] THỬ NGHIỆM** — thẻ `[cười] [thở dài] [hắng giọng]` chèn thẳng vào text |
| Chia đoạn | **[V]** `max_chars_per_chunk: 256`, `max_total_chars_streaming: 3000` |
| Batch | **[V]** tới 32, kèm chế độ hội thoại nhiều người nói |

### 2.1 🔴 Phát hiện quyết định toàn bộ kiến trúc

> **[V] Đường CPU/ONNX là đường CHÍNH, không phải đường dự phòng.**
> README nói thẳng: với **văn bản ngắn**, đường CPU/ONNX **nhanh hơn GPU** (không
> có batch để lấp, không có phí khởi động kernel). GPU chỉ thắng khi **batch văn
> bản dài**.
>
> **[V] Streaming CHỈ chạy trên ONNX/CPU.** `infer_stream` phát theo frame, âm
> thanh đầu tiên ~**300 ms**, RTF < 1 trên CPU. Engine GPU/PyTorch dựng cho
> **thông lượng batch**, không cho streaming — README bảo ghim `backend="onnx"`
> nếu muốn realtime.

Hệ quả: **LTT VOICE không phải tranh card 3090 cho đường chính.** Đây là điểm
khác biệt lớn nhất so với H37 (ảnh) và H38 (LLM), nơi GPU là nút thắt của mọi
quyết định. Máy B có **192 GB RAM** và CPU tương đối rảnh trong lúc GPU bị ba hộ
kia chiếm.

### 2.2 🔴 Ba cái bẫy upstream, đã xác minh **đang mở** hôm nay

| Issue | Nội dung | Hệ quả bắt buộc |
|---|---|---|
| **#191** (21/08) | Phụ thuộc `perth` **sai gói** ⇒ **watermark không bao giờ được áp**, dù giao diện khẳng định là có | ⛔ **Không được công bố "có đóng dấu chìm"** cho tới khi tự đo được dấu trên tệp ra. Một lời hứa provenance sai còn tệ hơn không hứa |
| **#173** (07/07) | Giọng nhân bản **lệch tông giữa các câu** trong bài dài | Giới hạn phạm vi long-form; đo trôi tông trước khi bán |
| **#168** (04/07) | v3-preview **phát âm chưa ổn định** | Đây là early access. Cổng chất lượng phải là **cổng chặn**, không phải hình thức |

### 2.3 [V] Metadata upstream tự mâu thuẫn — đúng như pack cảnh báo

`config.yaml` khai `supports_streaming: false` cho **mọi** backbone, trong khi
README và SDK có `infer_stream` chạy thật.

⇒ **Năng lực phải đọc từ phép thử lúc chạy, không đọc từ một trường metadata.**
Cổng của ta phải tự dò và tự công bố `native | chunked | none`.

---

## 3. PHƯƠNG ÁN — bảng quyết định

### QĐ-1. LTT VOICE là app hay provider? → **CẢ HAI, và đó không phải thoả hiệp**

| Phương án | Tái dùng | Tốc độ MVP | Rủi ro | Phán quyết |
|---|---|---|---|---|
| **A. Chỉ là provider** (như Q102 với `ltt_image`) | Cao | Cao | 🔴 **Không có chỗ để cất Voice Profile.** Provider không sở hữu bảng, không sở hữu quyền, không sở hữu consent | ❌ |
| **B. Chỉ là app**, gọi thẳng VieNeu trong worker máy A | Cao | Rất cao | 🔴 Nạp model + suy luận CPU **trong chính hộp đang phục vụ khách** trên 32 GB RAM | ❌ (trừ khi V1 đo ra chi phí CPU không đáng kể) |
| **✅ C. Provider `ltt_voice` (engine) + app `apps/ltt_voice/` (nghiệp vụ)** | Cao | Trung bình | Thấp | ✅ **CHỌN** |

Vì sao C: Q102 đã chốt *"model là một provider"* — đúng cho **engine**. Nhưng
Voice Profile là **dữ liệu nghiệp vụ có chủ sở hữu, có vòng đời, có consent**, và
hợp đồng app đã chừa sẵn `table_prefix` cho đúng việc đó (tiền lệ `apps/vps/`, 5
bảng). Tách hai vai giữ được lời hứa dài hạn của pack: *đổi engine không đổi
`voice_id`*.

### QĐ-2. Engine chạy ở đâu? → **Máy B, mặc định CPU/ONNX**

| Phương án | Chống chọi GPU | MVP | Rủi ro | Phán quyết |
|---|---|---|---|---|
| **A. `voice_gateway` trên máy B, CPU/ONNX** | ✅ **Không tranh card với ba hộ kia** | Trung bình (phải deploy đích thứ hai — nhưng khuôn đã có sẵn hai lần) | Thấp | ✅ **CHỌN** |
| B. Trong tiến trình worker máy A | — | Cao nhất | 🔴 32 GB RAM, đang phục vụ khách; CPU là tài nguyên **chung** với ffmpeg/WhisperX | ❌ mặc định; giữ làm dự phòng nếu V1 đo ra rẻ |
| C. Máy B, GPU/PyTorch | ❌ **tranh đúng thứ đang khan hiếm** | Trung bình | Cao | ⚠️ **Chỉ mở làn riêng cho batch long-form**, không bao giờ là mặc định |

⭐ Đây là chỗ phương án này **khác hẳn** việc chép lại hình dạng H37. H37 buộc phải
lên GPU. VOICE thì không — và nếu ai đó mặc định đưa nó lên GPU "cho giống", họ
vừa mua lại toàn bộ bài toán tranh chấp card mà **không đổi được gì**.

### QĐ-3. Định danh giọng công khai → **`vc_<uuid4-hex>`, sinh bởi nền tảng**

- **[V]** Quy ước kho: UUID chuỗi (`apps/vps/tables.py` dùng `str(uuid.uuid4())`),
  và Public API đã có tiền lệ id **có tiền tố** (`upl_…` cho upload).
- ⛔ Không bao giờ là: tên hiển thị, khoá trong `voices.json` của VieNeu, đường dẫn
  checkpoint, chỉ số preset, hay speaker embedding.
- **Hồ sơ giọng** và **biểu diễn engine** là **hai bảng khác nhau**. Nâng cấp
  v3 Turbo → v3 full = thêm một dòng biểu diễn mới, `voice_id` **không đổi**. Đây
  chính là bất biến dài hạn mà pack đặt lên hàng đầu, và nó chỉ giữ được bằng
  schema, không giữ được bằng thiện chí.

### QĐ-4. Tiền → tính theo **giây tiếng nói sinh ra thật**

- Giữ chỗ (`uoc_tran`) theo **số ký tự đầu vào** × tỉ lệ ký tự→giây **đã đo**,
  luôn ≥ giá thật (khuôn 3.3).
- Quyết toán theo **thời lượng thật** của tệp ra, đo bằng
  `platform_core.media.duration_seconds` (khuôn 3.4); handler **phải** báo
  `credit_cost` trong result (khuôn 4.4 — đây đúng là lỗi H37/H38 đã mắc).
- Không đo được ⇒ **hoàn đủ, thu 0** (khuôn 3.5).
- Giá ở **một tệp duy nhất** `apps/ltt_voice/gia.py`, có `PHIEN_BAN_GIA`, có
  `bang_gia()`, công bố ở `/gia-api` (khuôn 3.1 / 3.6).
- Giá vốn vào `platform_core/gia_von.json` (mcredit / giây tiếng), tính từ **giây
  CPU đo thật** × điện + khấu hao. `test_261` giữ giá bán ≥ giá vốn.

### QĐ-5. Streaming → **xây đường nối, không bán trong MVP**

Lý do có bằng chứng, không phải ngại việc:

1. **[V]** Streaming chỉ chạy trên ONNX/CPU ⇒ nó **không** dùng lại được đường GPU
   batch, tức là một làn riêng chứ không phải một cờ.
2. **[V]** Chế độ `STREAM` của nền tảng bắt khai **bốn** lời hứa
   (`STREAM_PHAI_KHAI`: `event_types`, `heartbeat_seconds`, `usage_event`,
   `cancel_on_disconnect`) và phải xin lease từ admission plane (Q114).
3. Không có chứng minh sản phẩm nào phụ thuộc streaming ở MVP.

⇒ MVP: preview trên web = job → artifact → `<audio>`. Cổng máy B **vẫn** dựng sẵn
`/v1/audio/stream` sau cờ, và **công bố năng lực bằng phép dò lúc chạy** (§2.3).

### QĐ-6. ⚠️ Một thay đổi nền tảng buộc phải nói ra: `APIKEY_CAT_AUDIO`

**[V]** `platform_core/models.py:647-650` chỉ có bốn hạng mục khoá:
`model_control`, `chat`, `image`, `video`. `api_keys.py:43` chặn mọi giá trị khác.
Token của `voice_gateway` cất trong APIKEYS (khuôn 2.1) thì **cần một hạng mục
`audio`** — chạm `platform_core/models.py`, `platform_core/api_keys.py`,
`server/admin.py` (nhãn).

CLAUDE.md nói: *"Nếu thấy buộc phải sửa nền tảng thì dừng lại và nói rõ vì sao."*
Đây là chỗ dừng lại:

- Đường vòng khả dĩ: nhét khoá vào `model_control`. ❌ **Bác** — đó là nói dối về
  thứ mà khoá đó là, và bảng phân loại khoá là thứ operator đọc để xoay khoá.
- ⇒ **Cần một quyết định nền (Q-số mới)**: mở rộng enum hạng mục khoá thêm
  `audio`. Nhỏ, thuần dữ liệu, đúng chỗ mở rộng mà `providers.py` tự nhận là có.
  Nhưng nó **phải được ghi**, không được lặng lẽ thêm.

---

## 4. Kiến trúc chốt

```
KHÁCH ─┬─ Web Studio  /ltt-voice         (Jinja + ltt.css, cache-bust asset_ver)
       └─ /api/v1     tool `speech.ltt`  (ASYNC_JOB, cổng 3 lớp fail-closed)
                 │
         MÁY A ──┼── apps/ltt_voice/
                 │     manifest.py       khai job_types, giá, ToolSpec, table_prefix
                 │     features.py       NGHIỆP VỤ — dùng chung mọi cửa (khuôn 4.1)
                 │     jobs.py           handler mỏng, dịch lỗi, báo credit_cost
                 │     gia.py            MỘT bảng giá, có phiên bản
                 │     tables.py         voice_profile · voice_ref · voice_repr · voice_consent
                 │     routes.py         CHỈ HTTP
                 │     text_pipeline.py  chuẩn hoá VI/EN cấp sản phẩm
                 │
                 ├── platform_core/  jobs · credit · storage(R2) · upload_sessions
                 │                   api_pool · leases · media(ffprobe)
                 │                   [MỚI] audio_input.py   (soi ảnh → soi tiếng)
                 │
                 └── voice_gateway/  ← MÃ VIẾT Ở MÁY A, CHẠY Ở MÁY B
                       api.py  config.py  ngan_sach.py  runner.py  deploy/deploy.ps1
                 ▼ HTTP LAN, bearer, tường lửa chỉ mở cho 192.168.2.17
         MÁY B ── LTTVoiceGateway  :8399 (đề xuất — netstat kiểm trước khi chốt)
                    └── vieneu 3.3.0
                        ├── LÀN CPU/ONNX  ← mặc định: ngắn, tương tác, streaming
                        └── LÀN GPU/torch ← chỉ batch long-form, xin gpu lease
```

Ranh giới sở hữu (pack Pha 04 đòi ghi rõ):

| Việc | Chủ |
|---|---|
| Định danh giọng công khai | `apps/ltt_voice/tables.py` (máy A, Postgres) |
| Biểu diễn engine (embedding, ref codes) | bảng riêng ở máy A + tệp ở máy B; **không bao giờ ra ngoài** |
| Chuẩn hoá text cấp sản phẩm | `apps/ltt_voice/text_pipeline.py` |
| Âm vị / G2P | **upstream `sea-g2p`** — không viết lại |
| Chất lượng & provenance audio nguồn | `platform_core/audio_input.py` + bảng consent |
| Hàng đợi, trạng thái, huỷ | `platform_core/jobs.py` — **không dựng hàng đợi thứ hai** |
| Tiền | `platform_core/credit.py` + `apps/ltt_voice/gia.py` |
| Tài nguyên máy B | `voice_gateway` (max đồng thời, ngân sách, 429) |

⛔ **Máy B không giữ bí mật nào của nền tảng** (Q102): không mật khẩu CSDL, không
khoá R2. Audio vào bằng presigned GET, ra bằng presigned PUT.

---

## 5. LỘ TRÌNH — 11 cổng (V0 → V10)

Ánh xạ sang 20 prompt của pack ở cột cuối. **Vạch MVP nằm sau V6.**

| # | Cổng | Việc chính | Cổng qua (bằng chứng, không phải cảm nhận) | Prompt |
|---|---|---|---|---|
| **V0** | Quyết định nền | Ghi Q-số mới: app+provider (QĐ-1), CPU-mặc-định (QĐ-2), `APIKEY_CAT_AUDIO` (QĐ-6). Cập nhật `QUYET_DINH_NEN_TANG.md` | Quyết định có trong `QUYET_DINH_NEN_TANG.md` kèm lý do | 00, 04 |
| **V1** | **Khoá upstream + lô đo trên máy B** | Ghim `vieneu==3.3.0` + revision HF của v3-Turbo + MOSS tokenizer + sea-g2p. Chạy ma trận khói: VI · EN · trộn VI/EN · nhân bản · số/ngày/tiền · đoạn dài · lặp lại · dò streaming. Đo trên **cả CPU và GPU** | Bảng số **thật**: RTF, TTFA, RAM, VRAM, thời gian nạp model, kích thước tệp. Trả lời được: CPU có đủ nhanh không? Watermark `perth` (#191) **có áp không**? | 02, 03 |
| **V2** | **`voice_gateway` trên máy B** | Dựng theo khuôn `render_gateway`: chỉ nghe LAN, bearer, `/live` không khoá + `/health` có khoá, **bận ⇒ 429 không bao giờ 5xx**, `ngan_sach.py` từ chối cấu hình **chưa đo** trước khi chạm engine, chốt "đang chạy CPU hay GPU" đọc từ số đo, `deploy.ps1` đối chiếu hash | Khuôn tầng 1 **8/8**. ⚠️ Đọc `render_gateway/deploy/deploy.ps1` trước: nó từng có **hai lỗi khiến chưa deploy thành công lần nào** | 03, 12 |
| **V3** | **Lát cắt dọc + tiền đúng ngay từ đầu** | Một job `ltt_voice.synthesize`, giọng dựng sẵn, `features.py` mỏng, tệp lên R2, hold→settle theo **thời lượng thật**. Chưa UI, chưa bảng | Sinh được tiếng VI và EN qua đúng đường job của nền tảng; **restart máy chủ vẫn phát lại được**; hoá đơn khớp từng credit; xin dài nhận ngắn ⇒ **thu theo ngắn** | 03, 08 |
| **V4** | **Voice Profile + ghi danh** | Bốn bảng `voice_*`; `vc_*` id; upload tham chiếu qua `upload_sessions`; `platform_core/audio_input.py` (MIME thật, thời lượng, clipping, im lặng); giữ **nguyên bản bất biến** + bản dẫn xuất; consent + provenance; job `ltt_voice.enroll` **idempotent** | Tạo giọng → restart → gọi lại bằng `voice_id` vẫn ra đúng giọng. Ghi danh hỏng **không để lại trạng thái rác**. Khách A **không** đọc được giọng khách B (test IDOR) | 05, 06 |
| **V5** | **Ống văn bản VI/EN** | Chuẩn hoá cấp **sản phẩm** trên nền `sea-g2p` (không viết lại G2P): số/thập phân/tiền/%, ngày giờ, viết tắt kỹ thuật, đánh số danh sách, URL/email, từ điển phát âm riêng, chia đoạn theo câu tôn trọng trần 256 ký tự của engine | Bộ fixture hồi quy từ **kịch bản sáng tạo thật** của người dùng; lịch sử job ghi được **cả text gốc lẫn text đã chuẩn hoá** | 07 |
| **V6** | **Voice Studio (web)** | Bốn màn: Tạo tiếng · Giọng của tôi · Tạo giọng mới · Lịch sử. Jinja + `ltt.css`, **cache-bust bắt buộc**. Không React trừ khi chứng minh được cần | ✅ **VẠCH MVP.** Kiểm bằng trình duyệt **trên `https://app.lttstudios.com`**, không chỉ loopback (CLAUDE.md 5b). Không lộ một điều khiển VieNeu nào ở mặc định | 11, 16 |
| **V7** | **Giá công bố + giá vốn** | `gia.py` có phiên bản; mục trong `gia_von.json`; đăng lên `/gia-api` **lấy từ chính hàm ra hoá đơn** | Khuôn tầng 3 **6/6**; `test_261` xanh (bán ≥ vốn) | 13 |
| **V8** | **Mở `/api/v1` — tool `speech.ltt`** | `api_exposed=True`, `ASYNC_JOB`, `api_contract` đủ, cập nhật `inventory.py` + `APP_API_COVERAGE_FINAL.md` (`test_212` đọc bảng đó **cả hai chiều**), sandbox **không chạm engine, không chạm sổ tiền** | Gọi thật qua Cloudflare bằng khoá thật. ⚠️ `User-Agent` **không** được bắt đầu bằng `Python-urllib/` (chữ P hoa) — Cloudflare trả 403 trông y hệt khoá sai | 13, 16 |
| **V9** | **Long-form + batch** | Bài dài = việc **có thể tiếp tục**: chia đoạn giữ ranh giới ngữ nghĩa, trạng thái từng đoạn, thử lại **không sinh lại đoạn đã xong**, ghép tất định bằng ffmpeg. Làn GPU batch qua `job_type_lanes` + `gpu_vram_mb` + `admission_resource` | Giết worker giữa chừng ⇒ chạy lại **không bắt đầu từ 0**. Nộp trùng **không** sinh việc trùng. ⚠️ Đo trôi tông (#173) trước khi bán | 10, 12 |
| **V10** | **Cổng chất lượng trong Quality Lab** | Bộ đo mới: CER/WER qua **WhisperX sẵn có**, tương đồng người nói, thời lượng/clipping/độ ồn, tỉ lệ hỏng, TTFA/RTF. A/B mù, **mỗi phiếu quyết đoán phải viết lý do** (tiền lệ D-052) | Có **baseline ghim theo phiên bản**. Nâng cấp VieNeu (v3 full sắp ra) **không được lên** chỉ vì "nghe hay hơn" | 15, 18 |

Sau V10: **V11 bảo mật / giấy phép / consent**, **V12 streaming**, **V13 vận hành
+ tổng kiểm theo 31 chốt** — tương ứng prompt 14, 09, 17 / 19.

---

## 6. Định nghĩa MVP (bản hợp kho này, thay `specs/MVP_DEFINITION_V2.md`)

MVP **XONG** khi một lần cài mới làm được, có bằng chứng:

1. Người dùng đã đăng nhập tạo được **giọng của chính mình** từ clip 3–8 giây.
2. `voice_id` **sống qua restart và qua deploy**.
3. Sinh được tiếng **Việt**, tiếng **Anh**, và **trộn VI/EN** ở mức chất lượng đã đo.
4. Nghe / tải được kết quả qua giao diện, đúng ngôn ngữ thiết kế LTT.
5. **Tiền khớp từng credit**, quyết toán theo thời lượng thật.
6. Ranh giới sở hữu chặt: đoán `voice_id` **không** mở được giọng người khác.
7. Có đường cài / deploy / khởi động lại / **lùi bản** viết ra được.

**Ngoài MVP có chủ ý:** streaming · long-form/batch · chợ giọng công khai · nhân
bản giọng người thứ ba · engine TTS thứ hai · pipeline huấn luyện riêng.

---

## 7. Sổ rủi ro

| # | Rủi ro | Mức | Cách chặn |
|---|---|---|---|
| R1 | **v3 full sắp ra** (roadmap upstream) ⇒ nền đang di chuyển | 🔴 P0 | Ghim tag + revision HF; cổng đề bạt của V10 là điều kiện duy nhất để nâng |
| R2 | **#191 watermark không áp** nhưng UI upstream nói có | 🔴 P0 | V1 phải tự đo dấu trên tệp ra. Chưa đo được ⇒ **không công bố** |
| R3 | **#173 trôi tông bài dài** | 🟠 P1 | Đo ở V9 trước khi bán long-form; giới hạn độ dài công bố theo số đo |
| R4 | **#168 phát âm chưa ổn định (early access)** | 🟠 P1 | V10 là cổng chặn thật; V5 làm từ điển phát âm riêng cho tên riêng |
| R5 | CPU máy B tưởng rảnh nhưng ffmpeg / encode video cũng ăn CPU | 🟠 P1 | V1 đo **khi máy B đang chạy việc video**, không đo lúc máy rảnh |
| R6 | Nhân bản giọng ⇒ **quyền nhân thân** ở VN | 🟠 P1 | Chỉ giọng tự sở hữu; clickwrap consent lưu thành **dữ liệu**, không phải ghi chú (tiền lệ `apps/vps/dieu_khoan.py` + `test_298`) |
| R7 | Cloudflare: **100 MB/request**, **125 giây** | 🟡 P2 | Audio dài đi presigned R2; việc dài đi `ASYNC_JOB` — nền tảng đã đúng sẵn |
| R8 | `audio[]` **không có** trong Public API | 🟡 P2 | Hợp đồng công khai: một tệp vào, một tệp ra. Biết từ đầu |
| R9 | Sửa `platform_core` cho `APIKEY_CAT_AUDIO` | 🟡 P2 | QĐ-6: ghi thành quyết định nền, không lặng lẽ thêm |

---

## 8. Việc đầu tiên nên làm

**V1, và chỉ V1.** Lý do: hai quyết định lớn nhất của phương án này (QĐ-2
CPU-mặc-định và QĐ-5 hoãn streaming) đều **treo vào một số đo chưa có** — VieNeu
v3 Turbo chạy nhanh cỡ nào trên CPU của máy B, **trong lúc máy B đang bận việc
video**.

Nếu số đo nói CPU đủ nhanh: lộ trình trên đúng, và LTT VOICE là dự án model nhà
**đầu tiên không phải tranh card 3090**.

Nếu số đo nói CPU không đủ: QĐ-2 lật sang làn GPU, và toàn bộ bài toán tranh chấp
GPU của H37/H38 quay lại — lúc đó `docs/ANH_NOI_BO/CHIA_GPU_HAI_MODEL.md` (trọng
tài VRAM) trở thành phụ thuộc bắt buộc chứ không phải tham khảo.

⇒ **Đừng viết `apps/ltt_voice/` trước khi có bảng số của V1.**

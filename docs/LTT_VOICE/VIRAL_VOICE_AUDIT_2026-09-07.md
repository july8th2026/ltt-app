# LTT VOICE × VIRAL VOICE — DEEP ARCHITECTURE & UPGRADE AUDIT

**Ngày:** 2026-09-07 · **Chế độ:** READ / ANALYZE / BENCHMARK / DESIGN — **không sửa một dòng mã nào**
**Nhánh LTT:** `admin-mvp-v3` @ `9d7f7044` · **Bản đang chạy production:** `9d7f7044073d`
(`GET https://app.lttstudios.com/health/version`, hỏi lúc 21:15 ngày 07/09/2026 — kho và production **khớp**)
**Nguồn Viral:** `D:\Viral` (bản Electron đã đóng gói, 2,6 GB, mtime 04/09/2026) — **nguồn chân lý cho Viral**

---

## 🔴 ĐỐI CHIẾU 10/09/2026 — BẢNG `U-` DƯỚI ĐÂY LÀ ẢNH CHỤP 07/09, KHÔNG PHẢI DANH SÁCH VIỆC

**Đọc khối này trước khi đọc bảng 19 mục ở §18.** Bảng ấy đúng **lúc nó được
viết** và chưa bao giờ được đối chiếu lại với thứ đã ship. Ba ngày sau, phần lớn
đã xong — nhưng bảng vẫn liệt kê chúng như việc còn mở, và một mục (`U-06`) là
**phát hiện sai** do chính tác giả đính chính ở §19.0.

⇒ Ai đọc bảng ấy theo mặt chữ sẽ **làm lại việc đã xong**. Đó là hạng lỗi
`CLAUDE.md` luật 5 gọi tên: *một bảng chép tay không có cách nào tự biết nó đã
cũ*.

### Trạng thái ĐO ĐƯỢC, 10/09/2026

| U- | Việc | Trạng thái đo được | Bằng chứng |
|---|---|---|---|
| U-01 | `VoiceRuntimeProfile` | **CƠ CHẾ XONG · DỮ LIỆU RỖNG** | `ho_so_giong.py` đủ; `ho_so_giong.json` có `"giong": {}` ⇒ hạng mục 39 = 30/75 |
| U-02 | Fallback có kiểm soát | **XONG** | `lui_giong.py` bậc thang 4 nấc, cấm nới giới/làn, bắt sinh cảnh báo |
| U-03 | Facet lọc giọng | **XONG 09/09** | P7 — vùng + phong cách nay lọc được; `test_352` ghim cả năm trục |
| U-04 | `VoiceQualityProfile` | **XONG** | 6 bảng tách bạch; `ly_do_loai` bắt buộc khi `rejected` |
| U-05 | Cổng license | **CƠ CHẾ XONG · DỮ LIỆU CHẶN** | `LICENSE_CHO_PHEP=("ok",)` + `_dieu_kien_kho_chung()` ở **cả hai** cửa đọc; số dòng thật chặn ở B-01 |
| ~~U-06~~ | ~~Gộp lô GPU~~ | **PHÁT HIỆN SAI** | §19.0 — đã xong từ trước khi bản này được viết |
| U-07 | Nối streaming vào Studio | **MÃ XONG · CỜ TẮT** | P2 — `/phat-dan` + `sidecar_client.phat_dan` + trình phát Web Audio; chờ `LTT_VOICE_STREAM=1` |
| U-08 | Kiểm model theo nội dung | **XONG** | `kiem_model.kiem()` gọi ở `engine.nap()` **trước** `self._tts = tts`; log production 09/09 `snapshot lanh` |
| U-09 | Preview đóng gói | **XONG** | Dựng sẵn một lần, phục vụ như tệp tĩnh; không tính tiền nghe thử |
| U-10 | Benchmark VI/EN cùng corpus | ⛔ **CHƯA** | Corpus 6 câu; hạng mục 30/31/32 vẫn trần 85 |
| U-11 | ETA hiển thị cho khách | ⛔ **CHƯA** | Phụ thuộc U-01; hạng mục 40 = `UNKNOWN` |
| U-12 | Xếp giọng theo mức dùng thật | **XONG** | `muc_dung.py`, gọi thật từ `nghe_thu.py:300` (`_dem_muc_dung`) |
| U-13 | Nghe thử văn bản của khách | **XONG** | `nghe_thu_cua_toi.py`, `TRAN_KY_TU = 160`, đứng sau admission |
| U-14 | Chỉ số theo giọng | **XONG** | `chi_so_giong.py`; có người gọi thật ở `routes/_p_chi_so.py:52` |
| U-15 | Khuôn chuẩn hoá theo cỡ engine | **XONG** | `KhuonChuanHoa` tách phiên âm khỏi đọc số; hạng mục 24 = 95 |
| U-16 | Bổ sung giọng VI | **XONG** | 20 preset + 8 kho chung = **28 VI**, chạm mục tiêu 20–30 |
| U-17 | Soát a11y + mobile | **MỘT PHẦN** | P6 sửa 5 nhãn; quét lại 0 nút thiếu tên. Thiếu **thiết bị thật** ⇒ hạng mục 81 chưa chấm |
| U-18 | Dọn bề mặt chết | **XONG — phán quyết là GIỮ** | Đo: **0** hàm bọc mồ côi; `/v1/stream` có test ghim ⇒ "để sẵn có chủ đích", không phải rác |
| U-19 | Benchmark OmniVoice | ⛔ **CHƯA** | Chờ license trọng số rõ (R-11) |

    XONG               : 11      (U-02,03,04,08,09,12,13,14,15,16,18)
    XONG CO CHE, chan  :  3      (U-01 du lieu · U-05 du lieu · U-07 co)
    MOT PHAN           :  1      (U-17)
    CHUA               :  3      (U-10, U-11, U-19)
    PHAT HIEN SAI      :  1      (U-06)

⚠️ **Ba nhóm giữa quan trọng hơn hai nhóm ngoài.** *"Cơ chế xong, dữ liệu rỗng"*
và *"mã xong, cờ tắt"* đọc ra giống **CHƯA** với người quét nhanh, nhưng việc
phải làm khác hẳn: không phải viết mã, mà là **chạy một phép đo** hoặc **bật một
cờ**. Gộp chúng vào "chưa" là cách một lượt soát sau sẽ ước lượng sai công việc
còn lại.

🔒 Khối này được ghim bằng `tests/test_516_doi_chieu_u_viral.py`: mỗi mục khai
**XONG** phải còn mô-đun/hàm mà nó viện dẫn. Bảng nói sai thì gate đỏ.

---

## ⛔ ĐỌC DÒNG NÀY TRƯỚC MỌI DÒNG KHÁC

Kết luận nặng nhất của cả lượt soát này **không phải** về chất lượng giọng, kiến trúc hay UX.
Nó là một chuyện pháp lý, và nó có bằng chứng máy đọc được:

> Bộ 16 giọng Việt của Viral (`resources/vendor/piper_models/*.onnx`) đến từ kho
> `doof-ferb/nghitts-copy` trên Hugging Face. Kho đó **còn chứa** `mytam2.onnx`,
> `mytam2794.onnx`, `tranthanh3870.onnx` — và Viral **đang đóng gói và bán**
> `ngocngan3701.onnx` dưới tên hiển thị **"Ngọc Ngạn"**.
>
> Đây là tên của **người thật, nổi tiếng, còn sống** ở Việt Nam. Nhãn `apache-2.0`
> trên trọng số **không** cấp quyền hình ảnh/giọng nói (likeness / personality rights).

⇒ **Không một giọng Piper nào của Viral được phép sang LTT.** Không phải "chưa", mà là **không**.
Chi tiết + bằng chứng: §13.

---

## 1. EXECUTIVE SUMMARY

### 1.1 Hai hệ thống này không cùng loại, và đó là điều quan trọng nhất

| | **LTT Voice** | **Viral (ViralCrawl)** |
|---|---|---|
| Hình dạng | **Sản phẩm SaaS đa người dùng**, bán theo credit | **App desktop một máy**, tính năng phụ của một công cụ cào/dịch video |
| Voice là gì ở đó | **Sản phẩm chính** — có sở hữu, consent, vòng đời, hoá đơn | **Bộ phận của khâu lồng tiếng**; tab "Tạo Voice" là đường vòng dựng trên chính khâu ấy |
| Engine | **MỘT** — VieNeu-TTS v3 Turbo (48 kHz, VI+EN, clone) | **BỐN** đang chạy + 1 chết (piper · edge · omnivoice · capcut; supertonic đã chết) |
| Trách nhiệm pháp lý | Thu tiền thật ⇒ phải chịu được kiểm tra | Chạy trên máy khách ⇒ né được bằng "khách tự chịu" |

⭐ Vì vậy **phần lớn thứ Viral "có nhiều hơn" là thứ LTT cố ý không có**, chứ không phải thiếu sót.
9.437 giọng ElevenLabs trong `giong_11labs/*.json` không phải một kho giọng — nó là một **danh mục
đi mượn**, không có model, không có quyền, và nó tới qua một cửa API bị dịch ngược.

### 1.2 Bảy điều đo được, xếp theo mức quan trọng

1. **Viral có 22 model `.onnx` đóng gói (1,7 GB), 16 trong đó là giọng Việt** — TYPE A thật, chạy
   offline thật, mỗi giọng một model riêng (`num_speakers: 1`, config **byte-identical** cho cả 16).
   Nhưng provenance của chúng **hỏng ở gốc** (§13) ⇒ giá trị sử dụng cho LTT = **0**.
2. **ElevenLabs trong Viral hoàn toàn không có model local.** 9.437 mục JSON / 29 ngôn ngữ, mỗi mục
   là `{id, ten, vung, url, gioi, dung}` với `url` trỏ thẳng vào `storage.googleapis.com/eleven-public-prod`.
   **Không có file `vi.json`** — ElevenLabs library của Viral **không có tiếng Việt**.
3. **CapCut TTS là một API bị dịch ngược**, có ký RSA payload, giả chữ ký client, và **tự xoay
   `device_id` để né cơ chế chống lạm dụng** ("shark block"). Không mang sang được — không phải vì
   khó, mà vì nó là thứ một SaaS thu tiền không được đứng lên.
4. **Supertonic là engine CHẾT**: `README.md` khai `--tts supertonic`, nhưng trong toàn bộ mã Python
   **không có một dòng nào** thực thi nó (`grep -rn supertonic --include=*.py` → 2 kết quả, cả hai
   đều là **chú thích**). 90 tệp MP3 nghe thử của nó vẫn nằm trong bundle — **13 MB tài sản mồ côi**.
5. **Viral có ba thứ về phương pháp mà LTT nên học ngay**: bảng tốc-độ-đọc-đo-được cho từng giọng
   (`TOC_DOC`, 61 giọng), bộ kiểm tính hợp lệ của model đã tải (`_onnx_hop_le` — bắt ca "HTTP 200 kèm
   HTML"), và tách **chuẩn hoá số** khỏi **phiên âm Anh→Việt** theo cỡ engine.
6. **LTT mạnh hơn Viral ở gần như mọi tầng kỹ thuật nghiêm túc**: QC âm học thật (LUFS/true-peak/ASR
   ngược/speaker-similarity/F0-drift/watermark) so với **một tỉ lệ phủ câu** ở Viral; long-form
   **đọc tiếp được sau khi chết**; giá có phiên bản, đối soát được; sở hữu + consent có bảng riêng.
7. **LTT có năm bề mặt đã xây mà chưa nối vào sản phẩm**: `/v1/stream`, `/v1/batch`, `/v1/speech-dai`,
   `/v1/voices`, `/v1/capabilities` — bốn trong năm chỉ có công cụ đo gọi tới (§5.3). Đây là nợ có
   thật, và là chỗ P0/P1 của lộ trình.

### 1.3 Câu trả lời ngắn cho câu hỏi lớn nhất

> *"Viral có gì tốt hơn để mang sang?"*

**Về tài sản (voice/model): KHÔNG CÓ GÌ.** Không một byte nào của `D:\Viral` đủ điều kiện provenance
để vào một sản phẩm thu tiền.

**Về ý tưởng: có sáu thứ đáng lấy**, và cả sáu đều là **phương pháp**, không phải mã:
per-voice runtime profile · fallback giữ giới tính · validate model đã tải theo **nội dung** ·
preview đóng gói sẵn theo bản phát hành · chuẩn hoá theo cỡ engine · và **ASR-ngược làm thước đo
chấp nhận giọng** (Viral đã dùng nó để chấm clone xuyên ngôn ngữ: vi 100% · en 100% · ja 94% ·
ko 70% · th 51%).

---

## 2. ARCHITECTURE — LTT VOICE (đo từ mã, không từ tài liệu)

### 2.1 Đường đi của một lượt tạo tiếng

```
Trình duyệt  (templates/ltt_voice_studio.html + server/static/voice.js, 100.784 B)
   │
   ├─ POST /ltt-voice/tao ──────────────────► routes/_p_tao.py (439 dòng)
   │                                             ├─ CSRF + require_login
   │                                             ├─ features.chuan_hoa()  -> YeuCau
   │                                             ├─ features.giai_giong() -> kiểm SỞ HỮU
   │                                             └─ lan_ngon_ngu.doi_chieu() -> CẢNH BÁO (không chặn)
   │
   ├─ manifest.credit_cost = _gia(params)
   │      └─ text_pipeline.chuan_hoa() TRƯỚC khi đếm ký tự  ← nở số/ngày nằm trong giá
   │      └─ gia.uoc_tran(so_ky_tu)  =  ceil( (1,5 + n/18) × 200 mcredit )
   │
   ├─ platform_core/jobs.py  -> GIỮ CHỖ credit + hàng đợi
   │      requires=("voice",)   ← thiếu làn `voice` trong LTT_WORKER_POOLS = job treo VĨNH VIỄN
   │      admission_resource="vieneu_gpu", slots=1   ← job/sync/stream giành CÙNG một suất
   │
   ├─ worker: apps/ltt_voice/jobs.py::handle
   │      ├─ so_doan == 1  -> sidecar_client.noi()          -> POST /v1/speech
   │      └─ so_doan  > 1  -> ban_doc_dai.dung()
   │             ├─ lo_ra_tep()  -> POST /v1/lo-ra-tep   (mỗi đoạn -> 1 tệp trên đĩa)
   │             ├─ artifact mỗi đoạn: voice/seg/{owner}/{job_id}/{i}.wav   ← ĐỌC TIẾP ĐƯỢC
   │             └─ ghep_tep()   -> POST /v1/ghep-tep
   │
   ├─ voice_sidecar/ (venv CÁCH LY, có torch + vieneu)
   │      server.py  -> engine.CongGiong (một thực thể ẤM, cả tiến trình)
   │      ├─ _Cong: BoundedSemaphore KHÔNG chờ -> hết chỗ = 429 + Retry-After (không bao giờ 5xx)
   │      ├─ chốt GPU đọc từ SỐ ĐO (torch memory_allocated), không đọc cờ cấu hình
   │      ├─ TỪ CHỐI KHỞI ĐỘNG nếu watermark không áp được (upstream #191 nuốt lỗi này)
   │      └─ chot_sinh.py  = K1: 4 chốt trước khi WAV rời sidecar
   │             im lặng · quá ngắn · quá dài · LẶP ĐUÔI (tương quan cửa sổ 0,6 s > 0,92)
   │
   ├─ toc_do.py   time-stretch atempo — CHẠY SAU khi đo thời lượng (nếu trước = lỗ tính tiền)
   ├─ ffprobe -> giây THẬT -> gia.tinh(giay) -> credit_cost báo về -> HOÀN phần giữ dư
   └─ storage.put -> lịch sử -> /ltt-voice/lich-su
```

### 2.2 Bảng dữ liệu (5 bảng, `table_prefix="voice"`)

| Bảng | Vai trò |
|---|---|
| `voice_profile` | Danh tính CÔNG KHAI ổn định (`vc_<32 hex>`), chủ sở hữu, làn, trạng thái, `dung_chung` |
| `voice_ref` | Clip nguồn đã ghi danh (khoá kho, sha256) |
| `voice_repr` | Biểu diễn giọng theo **phiên bản engine** — `speaker_emb` + `codes`, `.npz` nén base64 |
| `voice_consent` | Bằng chứng đồng ý dùng giọng |
| `voice_tu_dien` | Từ điển phát âm **riêng của từng khách** |

⭐ Việc tách `voice_profile` (danh tính) khỏi `voice_repr` (biểu diễn theo engine) là **quyết định
kiến trúc quan trọng nhất của cả hệ**: nó cho phép **nâng engine mà `voice_id` của khách không đổi**.
Viral không có khái niệm này — ở đó "giọng" *là* tên file `.onnx` hoặc *là* `voice_id` của nhà cung cấp.

### 2.3 Hai trần, và chúng nói hai điều khác nhau

| Hằng số | Giá trị | Bản chất | Nguồn |
|---|---|---|---|
| `TRAN_MOI_LUOT_SINH` | **1.500** | trần **CHẤT LƯỢNG** — chỗ giọng bắt đầu trôi (upstream #168) | `tham_so_cong_khai.py` |
| `TRAN_KY_TU_CONG_KHAI` | **100.000** | trần **NGÂN SÁCH TÀI NGUYÊN** — một job giữ GPU bao lâu thì còn công bằng | idem |

Đo 03/09 (`tools/do_bai_dai.py`): 19,86 ký tự/giây audio · RTF 0,152 ⇒ **0,00763 giây GPU / ký tự**.
Ràng buộc chọn con số 100.000 **không** phải định dạng tệp (WAV tràn ở ~444.000 ký tự) mà là
**chưa có bộ xếp lịch ưu tiên** — 100.000 ký tự giữ GPU ~13 phút và chặn mọi người khác.

Và bản ghép **tốt hơn** bản một lượt trên **mọi** chỉ số ASR ở **mọi** độ dài (CER 0,1121 → 0,0897;
WER 0,2037 → 0,1905). Đó là bằng chứng cơ chế: đường sinh **không mang trạng thái giữa các đoạn**.

---

## 3. ARCHITECTURE — VIRAL VOICE

### 3.1 Sự thật cấu trúc: Voice ở Viral là **phái sinh của khâu lồng tiếng video**

```
Tab "Tạo Voice (TTS)"  (web/index.html §v-ttsdoclap, dòng 3515)
   │  POST /api/tts_doc_lap
   ▼
localize.tts_doc_lap(text, engine, voice, lang, ref_audio)      (localize.py:14882)
   │
   │  ⛔ DỰNG segs_vi GIẢ — một "timeline video" không có video:
   │       dur = max(1.5, len(dòng)/8.0)          ← khe RỘNG có chủ ý
   │       segs_vi.append((t, t+dur, ("", dòng)))
   │       t += dur + TTS_DL_NGHI(0.35)
   │
   ├─ engine == piper      -> long_tieng_piper(...)     (localize.py:13368)
   ├─ engine == edge       -> long_tieng_edge(...)      (localize.py:12003)
   ├─ engine == omnivoice  -> long_tieng_omnivoice(...) (localize.py:10705)
   ├─ engine == capcut     -> long_tieng_capcut(...)    (localize.py:10985)
   └─ else                 -> "Engine không hợp lệ"     ← supertonic rơi vào đây
   │
   ▼
_nen_im_lang(out, nghi)   ← ffmpeg silenceremove, DỌN chính khoảng câm mà bước trên vừa tạo ra
```

🔴 **Đây là một vòng lặp có giao diện, không phải một kiến trúc TTS.** Nó cấp phát một dòng thời gian
theo **ước lượng ký tự**, đổ tiếng thật vào các khe đó, rồi **cắt bỏ** phần dư bằng ffmpeg.
Chú thích của chính Viral thừa nhận: khách báo *"xuống dòng không đọc mà khoảng 5s mới hết"*, và
cách đúng đã được ghi ra ngay tại chỗ (*"tổng hợp trước, GHÉP lại, chèn khoảng nghỉ CỐ ĐỊNH"*) nhưng
**không được thực hiện** — vì làm thế thì phải rời khỏi `long_tieng_*`.

### 3.2 Trần và ràng buộc

| | Viral | LTT |
|---|---|---|
| Ký tự / lượt | **20.000** | **100.000** |
| Dòng / lượt | **500** | không có khái niệm (chia theo câu) |
| Đọc tiếp sau lỗi | ❌ không | ✅ artifact từng đoạn theo `job_id` |
| Hàng đợi / công bằng | ❌ không (in-process, khoá module `_TTS_DICH_LOCK`) | ✅ jobs + admission + lease GPU |
| Tính tiền | ❌ không có | ✅ giữ chỗ → quyết toán theo giây thật |

### 3.3 Ba khuyết tật kiến trúc lộ ra ngay trong chú thích của chính Viral

1. **`_TTS_DICH_EP` là biến MODULE + khoá** — hai lượt TTS song song khác ngôn ngữ phải **xếp hàng**.
   Chú thích giải thích vì sao không dùng `os.environ` (job render sẽ dịch nhầm cả video) và vì sao
   không dùng thread-local (thread con trong `long_tieng_edge` không với tới). Cả hai đều đúng — và
   cả hai đều là hệ quả của việc đặt trạng thái ngôn ngữ ở tầng module.
2. **`import ngon_ngu` thiếu ở nhánh `edge`** (commit `458bb51`, 23/08) ⇒ `NameError` bị
   `except Exception` nuốt ⇒ **nút Nghe thử giọng edge chưa bao giờ chạy** khi khách không chọn giọng.
   Một lỗi sống nhiều tháng vì lớp bắt lỗi quá rộng.
3. **`web_app.py` 22.935 dòng · `localize.py` 20.644 dòng** — không có ranh giới route/nghiệp vụ.
   Đối chiếu trần hợp đồng app của LTT: **900 dòng / 30 handler** mỗi `routes.py`.

---

## 4. VOICE ASSET FORENSIC — `D:\Viral`

### 4.1 Quét toàn bộ (không nạp binary vào ngữ cảnh)

```
find /d/Viral -type f (*.onnx|*.pt|*.pth|*.ckpt|*.safetensors|*.bin|*.gguf)
  -> 22 × .onnx   (tất cả trong resources/vendor/piper_models)
  -> 2  × .bin    (snapshot_blob.bin, v8_context_snapshot.bin — Chromium/V8, KHÔNG phải model)
  -> 0  × .pt/.pth/.ckpt/.safetensors/.gguf

find /d/Viral -type f (*.wav|*.mp3|*.m4a|*.ogg)
  -> 277  resources/app-src/web/giong_thu/     (preview MP3)
  -> 4    resources/app-src/giong_mau/         (clip THAM CHIẾU clone)
  -> 1    resources/app-src/trending_audio.mp3 (80 KB, không liên quan voice)
```

**Viral chưa từng chạy trên máy này** — `%APPDATA%\ViralCrawl` và `%LOCALAPPDATA%\ViralCrawl`
đều không tồn tại. ⇒ Mọi thứ có ở local **chính là** bundle; OmniVoice/Whisper/Demucs tải lúc chạy.

### 4.2 Bảng nguồn giọng

| Nguồn giọng | Đường dẫn | Số | Định dạng | Local/Remote | Dung lượng | Model hay mẫu | Chạy độc lập? |
|---|---|---|---|---|---|---|---|
| **NghiTTS (VI)** | `resources/vendor/piper_models/*.onnx` | **16** | ONNX VITS 22,05 kHz | **LOCAL** | 16 × 63.516.050 B ≈ **969 MB** | **MODEL** (TYPE A) | ✅ có (`piper` + `onnxruntime`) |
| **Piper chính chủ (non-VI)** | idem | **6** | ONNX VITS "high" | **LOCAL** | ≈ **705 MB** | **MODEL** (TYPE A) | ✅ có |
| **Edge (Azure)** | không có file | 74 ngôn ngữ | — | **REMOTE** | 0 | `voice_id` (TYPE C) | ❌ cần mạng |
| **CapCut / ByteDance** | không có file | ~392 mã | — | **REMOTE** | 0 | `voice_id` (TYPE C) | ❌ cần mạng + API dịch ngược |
| **ElevenLabs (qua CapCut)** | `giong_11labs/*.json` | **9.437** mục / 29 ngôn ngữ | JSON | **REMOTE** | **2,4 MB** | **CATALOG** (TYPE E) + `voice_id` (TYPE C) | ❌ |
| **ElevenLabs curated** | `giong_tuyen/*.json` | ~26/ngôn ngữ × 29 | JSON | REMOTE | 256 KB | CATALOG (TYPE E) | ❌ |
| **OmniVoice** | không có file | 1 model, clone tự do | — | tải lúc chạy vào `userData/runtime/.venv_omnivoice` | 0 tại chỗ | MODEL (TYPE B/F) | ✅ sau khi cài (GPU NVIDIA) |
| **Preview** | `web/giong_thu/*.mp3` | **277** | MP3 | LOCAL | **13 MB** | **MẪU** (TYPE D) | — |
| **Clip clone dựng sẵn** | `giong_mau/{nam,nu}.wav` + `*_omnicut.wav` | 4 (+1 `.txt`) | WAV | LOCAL | **8,1 MB** | **NGUỒN CLONE** (TYPE F) | — |

### 4.3 Trả lời chính xác từng câu hỏi đã đặt

**Piper — mỗi giọng có phải một model riêng?**
✅ **Đúng.** 22 tệp `.onnx`, `sha256sum` cho **22 giá trị khác nhau** — không có bản sao trùng.
Mỗi VI voice khai `"num_speakers": 1`, `"espeak": {"voice": "vi"}`, `"num_symbols": 256`,
`sample_rate: 22050`, `piper_version: "1.3.0"`.

**Config chung hay riêng?**
**CHUNG.** 16 tệp `<tên>.onnx.json` của giọng Việt **đều 3.705 byte** và `cmp config.json chieuthanh.onnx.json`
báo **IDENTICAL**. Sáu giọng chính chủ thì có config **riêng** (4.166–7.248 B) kèm khối `language`
và `dataset` mà bản Việt không có — dấu hiệu rõ ràng của hai xuất xứ khác nhau.

**Giọng nào VI?** 16: `ngochuyen` · `ngochuyennew` · `ngocngan3701` · `maiphuong` · `phuongtrang` ·
`thanhphuong2` · `calmwoman3688` · `yannew` · `lacphi` · `manhdung` · `minhkhang` · `minhquang` ·
`duyoryx3175` · `adam1` · `chieuthanh` · `taian4`. Giới tính khai ở `giong_piper.GIOI`: 8 nữ / 8 nam.

**ElevenLabs — có model local không?**
❌ **KHÔNG.** Chỉ JSON. Mỗi mục: `{"id","ten","vung","url","gioi","dung"}` với `url` là
`https://storage.googleapis.com/eleven-public-prod/...mp3` — **preview nằm trên hạ tầng ElevenLabs**,
không tải về. `dung` = số lượt dùng (dùng để **xếp hạng phổ biến**).

**Có MP3 sample local của ElevenLabs không?** ❌ Không. `web/giong_thu/` chỉ có edge · supertonic · piper.

**voice_id ElevenLabs dùng ở đâu?** Chỉ ở nhánh CapCut: `capcut_tts._nen_tang_giong()` trả `"11labs"`
⇒ `req_key = 11labs_text_to_speech` thay vì `sami_text_to_speech`. Tức Viral **không** gọi ElevenLabs;
nó gọi CapCut, và CapCut bán lại ElevenLabs.

**⛔ Và có một sự thật quan trọng: `giong_11labs/` KHÔNG CÓ `vi.json`.** 29 ngôn ngữ, không có
tiếng Việt. Nói cách khác: **kho ElevenLabs của Viral hoàn toàn vô dụng cho tiếng Việt.**

**CapCut — giọng có tồn tại local không?** ❌ Không. Chỉ `voice_type` (chuỗi mã) trong `capcut_tts.GIONG`.
Preview cho giọng CapCut **cũng không có** trong `web/giong_thu/` ⇒ khách CapCut không nghe thử được
trước khi gọi mạng.

**Kho `giong_thu` là gì?**
**PREVIEW dựng sẵn theo bản phát hành** (TYPE D), không phải cache, không phải dữ liệu huấn luyện,
không phải output. Bằng chứng: đặt tên tất định `<lang>_<engine>_<voiceid>.mp3`; nằm trong bundle
read-only; phục vụ tĩnh qua `web_app.py:19406` cùng nhóm với `/flags/` và `/fonts/`.
Phân bố: **171 edge · 90 supertonic · 16 piper**. VI có 28, EN có 29.

**⛔ 90 tệp supertonic là TÀI SẢN MỒ CÔI.** Engine tương ứng **không tồn tại trong mã**.

**`giong_mau/{nam,nu}.wav` là gì?**
**Clip THAM CHIẾU để clone** (TYPE F) — dùng làm giọng mặc định cho OmniVoice/F5.
`nu.txt` (1.927 B) là **transcript ASR** của clip, cache cho bước clone. Nội dung đọc là một đoạn
truyện (*"Đây là lần đầu tiên bác sĩ gặp phải vết thương như vậy…"*) với lỗi ASR nguyên vẹn
(`POWG`, `viết thương`, `nghỉ ngươi`) ⇒ đây là **âm thanh lấy từ nơi khác rồi ASR lại**,
**không có nguồn gốc, không có consent, không có giấy tờ**.

---

## 5. ENGINE INVENTORY

### 5.1 Bảng đầy đủ engine Voice trong Viral

| Engine | Local/Remote | VI | EN | Model | Số giọng | Clone | Stream | Batch | Tốc độ | Cao độ | Preview | License | Phụ thuộc |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Piper / NghiTTS** | LOCAL | ✅ | ⚠️(6 non-VI, không nối UI) | ONNX VITS 22,05 kHz | 16 VI (+6) | ❌ | ❌ | ✅ lô nội bộ | ✅ `length_scale` | ❌ | ✅ 16 MP3 | ⛔ **BLOCKED** (§13) | `piper`, `onnxruntime`, CUDA DLL |
| **Edge (Azure read-aloud)** | REMOTE | ✅ 2 giọng | ✅ 19 giọng | không | 74 ngôn ngữ | ❌ | ✅ (nội bộ lib) | ✅ nhóm câu | ✅ SSML rate | ✅ | ✅ 171 MP3 | ⛔ **BLOCKED** — ToS Microsoft | `edge_tts`, mạng |
| **CapCut / ByteDance (SAMI)** | REMOTE | ✅ 22 | ✅ | không | ~392 mã, 15 ngôn ngữ | ❌ (`voice_clone` có định tuyến, **chưa mở**) | ❌ | ✅ **bắt buộc** (né shark-block) | ❌ **server bỏ qua `rate`** (đã đo 2 lần) | ❌ | ❌ | ⛔ **BLOCKED** — API dịch ngược + né chống-lạm-dụng | RSA ký payload, `device_id` xoay |
| **ElevenLabs (qua CapCut)** | REMOTE | ⚠️ có mã trong `TOC_DOC` nhưng **không có `vi.json`** | ✅ 4.977 mục | không | 9.437 mục / 29 ngôn ngữ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ (URL remote) | ⛔ **BLOCKED** | như CapCut |
| **OmniVoice (k2-fsa)** | LOCAL (cài lúc chạy) | ✅ | ✅ | Qwen3-0.6B + flow, 24 kHz | 1 model, clone tự do | ✅ **điểm mạnh nhất** | ❌ | ✅ theo lô + sort độ dài + FP16 | ❌ | ❌ | ❌ | ⚠️ code **Apache-2.0**; **trọng số KHÔNG khai license** trên HF | venv riêng, **GPU NVIDIA bắt buộc** |
| **Supertonic** | — | — | — | — | 0 | — | — | — | — | — | ✅ 90 MP3 mồ côi | — | ⛔ **KHÔNG TỒN TẠI TRONG MÃ** |

### 5.2 Engine nào **thật sự** đang chạy — trace call graph, không đếm file

| Engine | UI "Tạo Voice" | Lồng tiếng video | Mã chết | Đường lùi | Kết luận |
|---|---|---|---|---|---|
| Piper | ✅ `Model 1` | ✅ mặc định cho `vi` + 6 `_PIPER_HIGH` | — | ✅ (khi CapCut hỏng) | **LIVE** |
| Edge | ✅ `Model 2` | ✅ mặc định cho ngôn ngữ không có Piper/CapCut | — | ✅ đường lùi cuối | **LIVE** (nhưng nút Nghe thử **hỏng**, §3.3) |
| OmniVoice | ✅ `Model 3` (kèm box Clone) | ✅ khi GPU đủ | — | ❌ | **LIVE (có điều kiện GPU)** |
| CapCut | ✅ `Model Vip` ×3 (capcut/azure/11labs) | ✅ ưu tiên cho 15 ngôn ngữ | — | ❌ | **LIVE, chỉ tier UNLIMITED** |
| Supertonic | ❌ | ❌ | ✅ **toàn bộ** | — | **DEAD** |
| 6 giọng Piper non-VI | ❌ (`/api/tts_ngon_ngu` trả `["vi"]` cho piper) | ✅ chỉ khi đích ∈ `_PIPER_HIGH` | ⚠️ | — | **CHỈ dùng ở lồng tiếng, không ở Tạo Voice** |

⭐ "Model Vip" tách làm **ba** mục UI (`capcut` / `azure` / `11labs`) nhưng cả ba đi **cùng một engine**
`capcut` — `web_app._tts_engine_that()` gộp lại. Đây là **tách theo NHÀ CUNG CẤP ở tầng trình bày**, và
nó là một ý tưởng UX tốt (§10.2).

### 5.3 Engine / bề mặt của LTT — và năm thứ đã xây mà **chưa nối**

| Bề mặt sidecar | Có client ở app? | Ai gọi | Trạng thái |
|---|---|---|---|
| `POST /v1/speech` | ✅ `noi()` | `jobs.py`, `nghe_thu.py` | ✅ **E2E WORKING** |
| `POST /v1/lo-ra-tep` | ✅ `lo_ra_tep()` | `ban_doc_dai.py` | ✅ **E2E WORKING** |
| `POST /v1/ghep-tep` | ✅ `ghep_tep()` | `ban_doc_dai.py` | ✅ **E2E WORKING** |
| `POST /v1/enroll` | ✅ `ghi_danh()` | `jobs.py::_ghi_danh` | ✅ **E2E WORKING** |
| `POST /v1/batch` | ✅ `noi_lo()` | **chỉ `tools/do_lo_giong.py`** | ⚠️ **PARTIAL — không nối sản phẩm** |
| `POST /v1/speech-dai` | ✅ `noi_dai()` | **chỉ `tools/do_troi_tong.py`** | ⚠️ **PARTIAL — bị `ban_doc_dai` thay thế** |
| `POST /v1/enroll-kho` | ✅ `ghi_danh_kho()` | **chỉ `tools/do_nhan_ban_tu_kho_cu.py`** | ⚠️ **công cụ vận hành, không phải sản phẩm** |
| `GET /v1/voices` | ✅ `giong_dung_san()` | **0 nơi gọi** | ⛔ **DEAD** (cố ý — thay bằng ảnh chụp tĩnh) |
| `GET /v1/capabilities` | ✅ `nang_luc()` | **0 nơi gọi** | ⛔ **DEAD** |
| `POST /v1/stream` | ❌ **không có client** | — | ⛔ **DEAD — chưa từng nối** |

⇒ **LTT không có streaming ở tầng sản phẩm**, dù sidecar đã có. Và `infer_batch` — thứ gộp nhiều đoạn
vào **MỘT lượt GPU** — cũng chưa được dùng, dù `manifest.py` nêu đích danh nó là **lý do duy nhất**
để một ngày nào đó dựng lại màn "Chạy lô".

---

## 6. SO SÁNH TIẾNG VIỆT (VI)

### 6.1 Bảng năng lực (đo được / suy ra / chỉ metadata)

| Tiêu chí | LTT (VieNeu v3 Turbo) | Viral (Piper/NghiTTS) | Viral (CapCut) | Viral (OmniVoice) | Loại bằng chứng |
|---|---|---|---|---|---|
| Sample rate | **48.000 Hz** | 22.050 Hz | (mp3 nhà cung cấp) | 24.000 Hz | **MEASURED** — đọc config/mã |
| Kiến trúc | LLM tự hồi quy + codec neural, **train from scratch ~10.000 h EN–VI** | VITS đơn giọng, phoneme espeak-vi | không rõ (ByteDance) | Qwen3-0.6B + flow matching | **MEASURED** (model card) / METADATA |
| Clone giọng | ✅ `encode_reference` → `speaker_emb` + `codes` | ❌ (một model = một giọng) | ⛔ có định tuyến, **chưa mở** | ✅ | **MEASURED** |
| Số giọng dựng sẵn | **20 preset + 25 dùng chung (8 VI + 17 EN) = 45** | 16 | 22 (+ mục ElevenLabs) | ∞ (clone) | **MEASURED** |
| Metadata giọng | giới · **vùng (Bắc/Trung/Nam)** · phong cách | giới **(bảng tay, chép 2 nơi)** | giới (**có ca đo F0 vì nhãn nhà cung cấp sai**) | — | **MEASURED** |
| Điều khiển tốc độ | ✅ **post time-stretch `atempo`**, 6 nấc 0,75–1,50 | ✅ `length_scale` (tham số engine) | ❌ **server bỏ qua** | ❌ | **MEASURED** |
| Chuẩn hoá số/ngày/tiền | ✅ `text_pipeline.chuan_hoa` | ✅ `tts_chuan_hoa` (port NghiTTS JS) | ✅ dùng chung | ✅ dùng chung | **MEASURED** |
| Phiên âm Anh→Việt | ❌ **cố ý không** (model lớn tự đọc) | ✅ **bắt buộc** (model nhỏ đọc sai) | ❌ | ❌ | **MEASURED** |
| Từ điển phát âm của khách | ✅ `voice_tu_dien` | ❌ | ❌ | ❌ | **MEASURED** |
| Long-form | ✅ 100.000 ký tự, **đọc tiếp được** | 20.000 ký tự / 500 dòng, không đọc tiếp | idem | idem | **MEASURED** |
| Trôi giọng dài | **đo**: CER 0,0897–0,1077 ở 3.000–10.000 ký tự, **không xấu đi** | không đo | không đo | không đo | **MEASURED** (LTT) / **KHÔNG CÓ** (Viral) |
| Naturalness / MOS | **NOT YET BENCHMARKED** trên cùng corpus | **NOT YET BENCHMARKED** | **NOT YET BENCHMARKED** | **NOT YET BENCHMARKED** | — |

### 6.2 Điều duy nhất có thể kết luận về chất lượng — và nó không phải một điểm số

⛔ **Không có benchmark cùng corpus nào giữa hai hệ.** Tôi **không bịa điểm âm thanh**.

Nhưng có ba sự thật **cấu trúc** đủ để định hướng, không cần nghe:

1. **48 kHz so với 22,05 kHz.** Băng thông của Piper dừng ở ~11 kHz. Với giọng đọc thì đủ hiểu,
   nhưng nó **không thể** có phần âm sắc trên 11 kHz mà tai nghe được là "trong".
2. **Piper VI dùng phoneme espeak-vi.** espeak-ng cho tiếng Việt là bộ luật đơn giản; nó **không**
   mô hình hoá thanh điệu như một hệ thống — chất lượng thanh điệu phụ thuộc hoàn toàn vào việc
   model học được từ dữ liệu.
3. **Piper không clone được.** Đây không phải chuyện chất lượng, mà là **chuyện sản phẩm**: toàn bộ
   giá trị bán được của LTT Voice ("giọng của bạn") không tồn tại trên Piper.

⇒ Piper **không phải** một đường nâng cấp chất lượng cho LTT. Nó chỉ có thể là một đường **rẻ** (CPU).

---

## 7. SO SÁNH TIẾNG ANH (EN)

| Tiêu chí | LTT | Viral | Bằng chứng |
|---|---|---|---|
| Engine đọc được EN | ✅ VieNeu song ngữ thật | ✅ nhiều đường | **MEASURED** cả hai |
| Phép đo EN của LTT | `tools/do_engine_co_noi_tieng_anh.py`, 01/09: `"The quick brown fox jumps over the lazy dog."` → ASR **đúng từng chữ**, `[en 0,996]` | — | **MEASURED** |
| Giọng nguồn EN | **17 giọng dùng chung làn `en`** (kho XTTS cũ) — Alex, Bella, Harry, Roger, Giffen… | `en_US-ryan-high` (1 giọng Piper, **không nối UI Tạo Voice**) + 19 Edge + 4.977 mục ElevenLabs | **MEASURED** |
| Giọng EN chạy offline được | ✅ 17 (qua VieNeu, giọng nguồn EN) | ⚠️ 1 (Piper ryan) — nhưng `/api/tts_ngon_ngu` trả `["vi"]` cho piper ⇒ **khách không chọn được** | **MEASURED** |
| Bộ lọc làn EN trong UI | ✅ nút "Tiếng Anh" ở bộ chọn giọng | ⚠️ dropdown ngôn ngữ theo engine | **MEASURED** |
| Chất lượng EN | **NOT YET BENCHMARKED** | **NOT YET BENCHMARKED** | — |

🔴 **Nghịch lý đáng ghi:** Viral có **4.977 mục ElevenLabs tiếng Anh** — con số lớn nhất trong cả
hai hệ. Nhưng chúng **không phải giọng của Viral**: không model, không quyền, và đường tới chúng đi
qua một API dịch ngược. Trong khi đó **17 giọng EN của LTT là tài sản thật, chạy trên engine của ta.**

⇒ Về EN, **LTT hơn Viral** ở thứ duy nhất đếm được: **số giọng ta thật sự sở hữu và phục vụ được**.

---

## 8. VOICE LIBRARY — SO SÁNH

| | LTT hôm nay | Viral hôm nay |
|---|---|---|
| Số lựa chọn thật cho khách VI | **45** (20 preset + 25 dùng chung) + giọng khách tự clone | 16 Piper + 22 CapCut + 2 Edge = **40** (không clone lưu được) |
| Số lựa chọn thật cho khách EN | **17** + clone | 19 Edge + 1 Piper + (4.977 mục đi mượn) |
| Danh tính giọng | **`vc_<32 hex>` ổn định qua nâng engine** | tên file `.onnx` / `voice_id` nhà cung cấp |
| Sở hữu | ✅ `owner_id`, tách `dung_chung` | ❌ không có khái niệm |
| Consent | ✅ bảng `voice_consent` | ❌ |
| Xuất xứ | ✅ sha256 clip nguồn | ❌ |
| Nghe thử | ✅ dựng sẵn, **0 GPU, 0 credit**, theo phiên bản tham số | ✅ **đóng gói kèm bản phát hành** (277 MP3) + nghe-thử-động (gọi engine thật) |
| Tìm kiếm | ✅ ô tìm | ✅ ô tìm (chỉ hiện khi thư viện lớn) |
| Bộ lọc | loại (mẫu/của tôi) · **làn ngôn ngữ** | nhà cung cấp · ngôn ngữ · **giới (2 dropdown)** |
| Lọc theo giới / vùng / phong cách | ❌ **hiện dưới dạng chữ, KHÔNG phải bộ lọc** | ⚠️ chỉ giới |
| Xếp theo độ phổ biến | ❌ | ✅ trường `dung` từ ElevenLabs |
| Không có JS vẫn chọn được | ✅ radio thật trong form thật | ❌ |
| Curation người thật | ✅ bảng tay 25 mục + DNSMOS + ASR (`tools/soi_kho_giong_cu.py`) | ✅ chủ dự án nghe rồi **loại 9 giọng** (ghi rõ trong `giong_piper.py`) |

⭐ **Cả hai đều đã curate bằng tai người.** Viral ghi lại quyết định loại ngay trong mã
(*"bỏ deepman3909 — nghe trùng calmwoman + tên 'nam trầm' sai — F0 178 Hz"*); LTT ghi trong
`tools/nhap_kho_giong_cu.py::TEN` + `KHO_GIONG/00_KIEM_KE.md`. Cách của Viral **rõ hơn** ở một điểm:
nó ghi cả **lý do loại**, không chỉ danh sách giữ.

---

## 9. RUNTIME — SO SÁNH

| Hạng mục | LTT | Viral | Bằng chứng |
|---|---|---|---|
| Nạp model | **giữ ấm một thực thể cả tiến trình** | Piper: `_piper_shared` giữ ấm; OmniVoice: **daemon warm nếu VRAM ≥ 6 GB**, không thì one-shot | MEASURED |
| Cold start | **39,9 – 73,1 s** (đo, dẫn tới `SO_LAN_THU_JOB = 5`) | OmniVoice ~10 s/lần nếu không daemon | MEASURED |
| Warm latency | 4,75 – 5,42 s cho một lượt ngắn (5 job đồng thời) | NOT MEASURED | MEASURED (LTT) |
| RTF | **0,152 – 0,214** | OmniVoice ~**0,227** (4,4× realtime, RTX 3050, ns16 batch8) | MEASURED cả hai (khác card ⇒ **không so trực tiếp được**) |
| VRAM | **641 MB allocated / 1.288 MB reserved / ~1.859 MB tiến trình**; khai `2000` để xếp chỗ | OmniVoice ~2,2 GB; ngưỡng daemon 6 GB | MEASURED |
| Đồng thời | **1 suất** (`admission_slots=1`, `vieneu_gpu`), 429 + Retry-After | khoá liên tiến trình `VC_GPU_SERIALIZE` + `_omni_khoa_gpu` | MEASURED |
| Batch | ⚠️ `/v1/batch` **có nhưng chưa nối** | ✅ **bắt buộc** ở CapCut (né shark-block): 1.619 câu → **27 request / 3,5 phút** | MEASURED |
| Streaming | ⛔ sidecar có, app **chưa nối** | ❌ | MEASURED |
| Xếp hàng công bằng | ✅ jobs + lease + `defer_resource` | ❌ | MEASURED |
| Phục hồi sau lỗi | ✅ 5 lần thử, backoff 10→20→40→80 s (~150 s > cold start chậm nhất) | ✅ **lùi ENGINE** (capcut → piper → edge) | MEASURED |
| Đọc tiếp sau restart | ✅ artifact từng đoạn theo `job_id` | ❌ | MEASURED |
| Offline | ✅ **toàn bộ** (model chạy tại máy A) | ⚠️ **chỉ Piper + OmniVoice**; edge/capcut cần mạng | MEASURED |
| Chống tải model hỏng | ⚠️ **không có** (model do `setup` đặt sẵn) | ✅ **`_onnx_hop_le`** — bắt "HTTP 200 kèm HTML" (size < 1 MB, byte đầu là `<` hoặc `{`) | MEASURED |
| Ghi/nhận model | — | `.part` → **verify** → `os.replace` (atomic), xoá bản hỏng | MEASURED |

🔴 **`_onnx_hop_le` là thứ kỹ thuật hay nhất trong toàn bộ Viral.** Nó giải một lớp lỗi mà LTT
**cũng có** ở chỗ khác: *ghi nhớ một thất bại rồi coi là sự thật*. Chi tiết ở §11 (T-03).

---

## 10. UX — SO SÁNH

### 10.1 Màn chính

| | LTT Studio (`ltt_voice_studio.html`, 611 dòng) | Viral "Tạo Voice" (`index.html` §v-ttsdoclap, ~48 dòng) |
|---|---|---|
| Bố cục | Bảng làm việc: **văn bản trái · giọng phải · nâng cao trong `<details>`** | **Một panel phẳng**, mọi điều khiển trên một hàng cuộn ngang |
| Điều khiển chính | text · ngôn ngữ (auto/vi/en) · giọng · tốc độ (6 nấc) · định dạng · **Tạo** | text · Model · giọng (2 dropdown) · ngôn ngữ · **Tạo** · **Nghe thử** |
| Nâng cao | ✅ **từ điển phát âm thêm ngay tại chỗ** · **"Xem trước cách đọc"** (soi phép chuẩn hoá) · nhập `.txt` · lưu vào Dự án · `<details>` "Cách tính tiền" | ❌ không có |
| Nghe thử | ✅ **dựng sẵn**, tệp tĩnh, 0 GPU / 0 credit, **câu CỐ ĐỊNH** để so sánh được | ⚠️ **gọi engine thật mỗi lần bấm**; đọc **dòng đầu của khách** nếu đã nhập, không thì câu mẫu |
| Lịch sử | ✅ màn riêng + "Gần đây" ngay trong Studio | ❌ chỉ file `.wav` mới nhất |
| Không có JS | ✅ chọn giọng + gửi form vẫn chạy | ❌ |
| Tiếp cận (a11y) | ✅ `role="radiogroup"`, `aria-pressed`, `aria-label`; có `test_352_ltt_voice_tiep_can.py` | ❌ không có thuộc tính ARIA nào trong khối này |
| Mobile | ✅ có pha Mobile B+C (commit `bec5643d`) | ❌ app desktop |

### 10.2 Bốn thứ Viral làm tốt hơn ở tầng UX — và cả bốn đều nhỏ

1. **Tách theo NHÀ CUNG CẤP thay vì trộn chung.** Chú thích 03/09 nói thẳng vì sao: *"giọng Việt có
   74 mục thì 52 là Azure, CapCut thật chỉ 22 ⇒ khách phải cuộn qua một rừng giọng Microsoft"*.
   ⇒ **Bài học chuyển được cho LTT:** khi kho giọng vượt ~50 mục, **một danh sách phẳng là hỏng**.
2. **Nghe thử đọc CHÍNH văn bản của khách.** LTT cố định câu để so sánh được — đúng, và LTT ghi rõ
   lý do. Nhưng Viral trả lời một câu hỏi **khác**: *"giọng này đọc BÀI CỦA TÔI thế nào?"*
   Hai câu hỏi đều thật (§18, T-06).
3. **Lọc theo giới bằng hai dropdown riêng.** Thô, nhưng nó cắt kho làm đôi bằng một cú bấm.
   LTT hiện giới dưới dạng **chữ**, không phải bộ lọc.
4. **Ẩn tên engine sau nhãn sản phẩm** ("Model 1/2/3/Vip"). Đúng nguyên tắc.
   ⚠️ Nhưng Viral làm quá tay: *"Nhanh Chất Lượng 8/10"* là **một điểm số không có phép đo nào đứng sau**.
   Lấy nguyên tắc, **không lấy cách thực hiện**.

---

## 11. THÀNH PHẦN VIRAL CÓ THỂ TÁI SỬ DỤNG

⛔ **Không có dòng mã nào của Viral được `REUSE DIRECT`.** Lý do không phải chất lượng mã, mà là
**hình dạng**: mọi hàm voice của Viral nhận `segs_vi` (timeline video) và ghi thẳng ra đĩa bằng
`log_fn=print`. Chúng không có ranh giới để cắt ra.

⇒ Mọi thứ dưới đây là **ADAPT** (mượn thuật toán) hoặc **REWRITE** (mượn ý tưởng).

| # | Thành phần Viral | Nguồn | LTT đã có? | Viral tốt hơn? | Hành động | Lợi ích | Rủi ro |
|---|---|---|---|---|---|---|---|
| T-01 | **`TOC_DOC`** — tốc độ đọc **đo được** cho từng giọng (61 mục, từ/giây) | `capcut_tts.py:1280` | ❌ chỉ có một hằng số toàn cục (18 ký tự/s) | ✅ **rõ ràng** | **ADAPT** | Ước thời lượng · credit · thời gian chờ **đúng theo giọng**, không phải theo trung bình | Phải **đo lại** trên engine của ta; mượn con số của Viral là vô nghĩa |
| T-02 | **Fallback GIỮ GIỚI TÍNH** — `gioi_cua()` + `mac_dinh_theo_gioi()` + `_giong_edge_theo_gioi()` | `giong_piper.py`, `localize.py:10344` | ❌ (LTT chưa có đường lùi giọng) | ✅ | **ADAPT** | Không bao giờ âm thầm đổi nam→nữ | Nếu chép cả bảng tay thì thừa kế luôn lỗi "hai bản sao lệch nhau" |
| T-03 | **`_onnx_hop_le`** — validate model theo **NỘI DUNG** (size < 1 MB, byte đầu `<`/`{`) | `giong_piper.py` | ❌ | ✅ **rõ ràng** | **ADAPT** | Bắt lớp lỗi "proxy/captive-portal trả HTML kèm 200" mà `os.path.isfile` không thấy | Rất thấp |
| T-04 | **`.part` → verify → `os.replace`** (atomic, xoá bản hỏng) | idem | ⚠️ một phần ở nơi khác | ✅ ở đường model | **ADAPT** | Không để lại bản dở sau khi đứt mạng | Thấp |
| T-05 | **Preview ĐÓNG GÓI theo bản phát hành** (277 MP3, 13 MB, tên tất định) | `web/giong_thu/` | ⚠️ LTT dựng **dần**, 3 giọng/giờ ⇒ **7 giờ** mới đủ 20 giọng | ✅ ở lượt đầu sau deploy | **ADAPT** | Không còn cửa sổ "đang chuẩn bị" sau mỗi lần đổi `PHIEN_BAN` | Tăng cỡ bản deploy; phải gắn phiên bản vào tên tệp |
| T-06 | **Nghe thử đọc văn bản CỦA KHÁCH** | `ttsDlNgheThu()` | ❌ (cố định, có lý do) | ✅ cho một câu hỏi khác | **REWRITE** | Trả lời *"giọng này đọc bài của tôi thế nào"* | ⛔ Tốn GPU thật + phải tính tiền hoặc giới hạn — **đây là lý do LTT chọn cố định** |
| T-07 | **Tách chuẩn-hoá-số khỏi phiên-âm theo CỠ ENGINE** | `localize._chuan_hoa_tts` | ⚠️ LTT chỉ có một chế độ (đúng cho một engine) | ✅ về mặt **khuôn** | **ADAPT** | Ngày thêm engine thứ hai, khuôn đã sẵn | Thấp |
| T-08 | **Lọc theo giới ở bộ chọn giọng** | `ttsDlVoiceNam/Nu` | ❌ | ✅ | **REWRITE** | Cắt kho làm đôi bằng một cú bấm | Thấp |
| T-09 | **Tách danh sách theo NHÓM khi kho lớn** | dropdown 6 mục | ⚠️ có "mẫu/của tôi", chưa có nhóm khác | ✅ | **REWRITE** | Kho 45→100 giọng vẫn duyệt được | Thấp |
| T-10 | **ASR ngược làm THƯỚC ĐO CHẤP NHẬN giọng** (vi/en/zh 100 % · ja 94 % · ko 70 % · th 51 %) | `omnivoice_synth.py` docstring | ✅ **LTT đã có, mạnh hơn** (`do_de_hieu`: CER/WER có chuẩn hoá dấu thanh) | ❌ | **KEEP LTT** | — | — |
| T-11 | **Xếp giọng theo ĐỘ PHỔ BIẾN** (trường `dung`) | `giong_11labs/*.json` | ❌ | ✅ về ý tưởng | **REWRITE** | Giọng hay dùng lên đầu; dữ liệu ta **tự có** (đếm job) | ⛔ **Không lấy dữ liệu `dung` của ElevenLabs** — đó là dữ liệu của họ |
| T-12 | **Ghi LÝ DO LOẠI giọng ngay trong mã** | `giong_piper.py` chú thích GIONG | ⚠️ LTT ghi danh sách giữ, không ghi lý do loại | ✅ | **ADAPT** | Phiên sau không "khôi phục" một giọng đã bị loại có lý do | Thấp |
| T-13 | **Gộp lô để né rate-limit** (1.619 câu → 27 request) | `capcut_tts._nhom_gop_capcut` | ⚠️ `/v1/batch` có, chưa nối | ⚠️ (ta không có rate-limit ngoài) | **BENCHMARK** | Có thể giảm chi phí khởi động/đoạn | Chỉ đáng nếu `infer_batch` thật sự tiết kiệm GPU-giây |
| T-14 | Toàn bộ engine CapCut / Edge / ElevenLabs | — | — | — | ⛔ **REJECT** | — | §12 |
| T-15 | Toàn bộ model Piper/NghiTTS | — | — | — | ⛔ **REJECT** | — | §13 |
| T-16 | Dựng `segs_vi` giả + `_nen_im_lang` | — | — | ❌ | ⛔ **REJECT** | — | §12 |

---

## 12. THÀNH PHẦN PHẢI TỪ CHỐI

| # | Thành phần | Lý do từ chối | Mức |
|---|---|---|---|
| R-01 | **CapCut TTS toàn bộ** (`capcut_tts.py`, 143 KB) | API **dịch ngược**, ký RSA giả chữ ký client, **tự xoay `device_id` để né chống-lạm-dụng** ("shark block"). Đây là **né phát hiện**, không phải tích hợp. Một SaaS thu tiền không đứng lên được trên nó. | ⛔ **TUYỆT ĐỐI** |
| R-02 | **Edge TTS** | Dùng endpoint read-aloud của Microsoft Edge ngoài mục đích, không hợp đồng, không SLA. Viral đã dính `throttle` đủ nhiều để **chủ động bỏ edge ở 15 ngôn ngữ**. | ⛔ **TUYỆT ĐỐI** |
| R-03 | **Danh mục + `voice_id` ElevenLabs** | Quét bằng API key (`license_server/dong_bo_11labs.py`) rồi phục vụ qua CapCut. Là **dữ liệu và tài sản của bên thứ ba**. Thêm nữa: **không có `vi.json`** ⇒ vô dụng cho ta. | ⛔ **TUYỆT ĐỐI** |
| R-04 | **16 model NghiTTS** | Likeness rights (§13). Nhãn `apache-2.0` **không** cấp quyền giọng của người thật. | ⛔ **TUYỆT ĐỐI** |
| R-05 | **`giong_mau/{nam,nu}.wav`** làm clip clone | Không nguồn gốc, không consent. `nu.txt` là transcript ASR của một đoạn **truyện của người khác**. LTT có bảng `voice_consent` **chính là để không làm việc này**. | ⛔ **TUYỆT ĐỐI** |
| R-06 | **Kiến trúc `segs_vi` giả + `_nen_im_lang`** | Tạo khoảng câm rồi cắt lại bằng ffmpeg. Sai về nguyên tắc và Viral **đã tự ghi ra** cách đúng ngay trong chú thích. | ⛔ **REJECT** |
| R-07 | **`localize.py` / `web_app.py`** làm mẫu tổ chức mã | 20.644 và 22.935 dòng, route + nghiệp vụ + I/O trộn lẫn. Ngược hoàn toàn hợp đồng app (900 dòng / 30 handler). | ⛔ **REJECT** |
| R-08 | **Nhãn chất lượng bịa** ("Chất Lượng 8/10") | Không phép đo nào đứng sau. Với sản phẩm thu tiền, đây là mô tả sai. | ⛔ **REJECT** |
| R-09 | **90 preview Supertonic** | Engine không tồn tại. Mang sang là mang một lời hứa không có gì đằng sau. | ⛔ **REJECT** |
| R-10 | **6 model Piper non-VI** (de/es/pl/uk/kk) | Ngoài phạm vi VI/EN. `en_US-ryan-high` (MIT, sạch) — xem §17.3, và câu trả lời vẫn là **không cần**. | ⛔ **REJECT (ngoài phạm vi)** |
| R-11 | **OmniVoice làm engine thứ hai — NGAY BÂY GIỜ** | Code Apache-2.0 ✅ nhưng **trọng số không khai license** trên HF. Và VieNeu đã bao trùm VI+EN với 48 kHz > 24 kHz. | ⚠️ **BENCHMARK FIRST**, không REJECT |

---

## 13. MA TRẬN LICENSE / PROVENANCE

### 13.1 Bảng phán quyết

| Nguồn | CODE | MODEL | WEIGHT | DATA PROVENANCE | LIKENESS RIGHTS | COMMERCIAL | REDISTRIBUTE | CAN HOST | CAN CLONE | CAN SYNTH | **PHÁN QUYẾT** |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **VieNeu-TTS v3 Turbo** (LTT hiện tại) | Apache-2.0 | Apache-2.0 | Apache-2.0 (`pnnbao-ump/VieNeu-TTS-v3-Turbo`) | dataset khai: `pnnbao-ump/VieNeu-TTS-10k-ENVI` | ⚠️ **UNKNOWN** (dataset 10k h — nguồn giọng chưa kiểm) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ **ĐANG DÙNG** — nhưng xem ⚠️ ở §13.3 |
| **NghiTTS (16 giọng VI)** | Apache-2.0 (repo `nghimestudio/nghitts`) | Apache-2.0 (khai bởi **người mirror**, không phải chủ gốc) | apache-2.0 khai ở `doof-ferb/nghitts-copy` | base `rhasspy/piper-voices` (MIT) + `rhasspy/piper-checkpoints`; **giọng huấn luyện KHÔNG khai** | ⛔ **VI PHẠM RÕ** — kho chứa `mytam2`, `mytam2794`, `tranthanh3870`; Viral **ship** `ngocngan3701` | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ **BLOCKED FOR PRODUCTION** |
| **Piper chính chủ (6 non-VI)** | MIT | MIT | MIT (`rhasspy/piper-voices`) | ✅ khai công khai theo dataset | ✅ sạch | ✅ | ✅ | ✅ | n/a | ✅ | ✅ **SẠCH** — nhưng **ngoài phạm vi VI/EN×chất lượng** |
| **CapCut / ByteDance** | ⛔ không có license — **dịch ngược** | n/a | n/a | n/a | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ **BLOCKED** |
| **ElevenLabs (catalog + preview URL)** | n/a | n/a | n/a | quét bằng API key | ⛔ giọng của người thật, license của ElevenLabs | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ **BLOCKED** |
| **Edge / Azure read-aloud** | n/a | n/a | n/a | n/a | ⛔ | ⛔ | ⛔ | ⛔ | n/a | ⛔ | ⛔ **BLOCKED** |
| **OmniVoice (k2-fsa)** | **Apache-2.0** ✅ (GitHub API xác nhận) | base `Qwen/Qwen3-0.6B` (Apache-2.0) | ⚠️ **KHÔNG KHAI** trên HF card | dataset không khai đầy đủ (`OmniVoice-Emilia` là repo riêng) | ⚠️ **UNKNOWN** | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ **UNKNOWN — phải xác minh trước production** |
| **`giong_mau/{nam,nu}.wav`** | n/a | n/a | n/a | ⛔ **KHÔNG CÓ** — transcript ASR của một đoạn truyện | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ **BLOCKED** |
| **277 preview MP3** | n/a | n/a | n/a | sinh bởi engine bên thứ ba | ⛔ (edge/supertonic) | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ **BLOCKED** |

### 13.2 Bằng chứng cho phán quyết NghiTTS — nguyên văn, kiểm lại được

```
$ curl -s https://huggingface.co/api/models/doof-ferb/nghitts-copy?full=true
  cardData.license      = "apache-2.0"
  cardData.base_model   = "rhasspy/piper-voices"
  cardData.repo         = "https://github.com/nghimestudio/nghitts"
  siblings (piper-tts/):
      adam1 · banmai · calmwoman3688 · chieuthanh · deepman3909 · duyoryx3175 ·
      lacphi · maiphuong · manhdung · minhkhang · minhquang · minhthu ·
      mytam2 · mytam2794 · ngochuyen · ngochuyennew · ngocngan3701 ·
      phuongtrang · taian2 · taian4 · thanhphuong2 · thientam ·
      tranthanh3870 · vietthao3886 · yannew
```

Và trong `giong_piper.py` (Viral, đã đóng gói):

```python
GIONG = { ..., "ngocngan3701": "Ngọc Ngạn", ... }
```

⇒ Ba tên trong danh sách trên là **người nổi tiếng có thật ở Việt Nam**. `apache-2.0` là license của
**mã và trọng số**; nó không, và không thể, cấp quyền dùng **giọng của một cá nhân**. Ở Việt Nam
Bộ luật Dân sự 2015 (Điều 32/34) và Luật An ninh mạng đều đứng về phía cá nhân đó.

⛔ **"Tải được ≠ dùng thương mại được."** Đây là ca mẫu của chính câu ấy.

### 13.3 ⚠️ Và ta phải soi CHÍNH TA bằng cùng thước đo

`VieNeu-TTS v3 Turbo` là Apache-2.0 và LTT đang bán trên nó. Nhưng:

- dataset khai là `pnnbao-ump/VieNeu-TTS-10k-ENVI` (~10.000 giờ EN–VI);
- **nguồn của 10.000 giờ ấy không được khai công khai**;
- và **20 giọng preset** của LTT (`Ngọc Huyền`, `Minh Đức`, `Xuân Vĩnh`…) là preset **của model**,
  tức chúng đến từ đúng dataset đó.

⇒ **CÂU HỎI MỞ Q-01 (§21):** ta chưa bao giờ hỏi tác giả VieNeu về **provenance của giọng preset**.
Đây không phải lý do dừng bán — nó là lý do **phải hỏi**, và phải hỏi trước khi có khách trả tiền
thật ở quy mô. Áp thước đo cho Viral mà không áp cho mình là một lượt soát không trung thực.

---

## 14. CHẤM ĐIỂM 0–100

**Quy tắc:** điểm phải có bằng chứng. Không đủ bằng chứng ⇒ **N/A**, không bịa.
Cột **Best target** = mức hợp lý đạt được sau lộ trình §19, **không phải 100**.

| # | Hạng mục | LTT hiện tại | Viral | Best target | Gap LTT | Bằng chứng |
|---|---|---|---|---|---|---|
| 1 | Architecture (tầng, ranh giới) | **92** | 28 | 95 | 3 | MEASURED — hợp đồng app vs 20k-dòng file |
| 2 | Voice engine (năng lực kỹ thuật) | **85** | 55 | 90 | 5 | MEASURED — 48 kHz + clone vs 22 kHz không clone |
| 3 | VI quality (nghe) | **N/A** | **N/A** | — | — | **NOT YET BENCHMARKED** — không corpus chung |
| 4 | EN quality (nghe) | **N/A** | **N/A** | — | — | **NOT YET BENCHMARKED** |
| 5 | Mixed VI/EN | **N/A** | **N/A** | — | — | **NOT YET BENCHMARKED** (LTT có 1 phép đo ASR đơn câu) |
| 6 | Voice catalog (số + chất) | **72** | 58 | 88 | 16 | MEASURED — 45 curate vs 40 + 9.437 đi mượn |
| 7 | Voice discovery (tìm/lọc) | **68** | 62 | 90 | 22 | MEASURED — thiếu facet giới/vùng/phong cách |
| 8 | Preview | **80** | 70 | 92 | 12 | MEASURED — LTT rẻ hơn nhưng ấm chậm (7 giờ) |
| 9 | Clone | **90** | 45 | 92 | 2 | MEASURED — có profile/ref/repr/consent vs không lưu |
| 10 | Speaker consistency | **82** | **N/A** | 88 | 6 | MEASURED (LTT: `do_giu_giong_nhieu_luot`, sàn nhiễu) |
| 11 | Long-form | **90** | 30 | 93 | 3 | MEASURED — 100k + đọc tiếp vs 20k + không |
| 12 | Text pipeline | **86** | 68 | 90 | 4 | MEASURED — LTT có "xem trước cách đọc" + từ điển khách |
| 13 | Pronunciation (từ điển) | **85** | 20 | 90 | 5 | MEASURED — `voice_tu_dien` + `tu_dien_rieng` vs không có |
| 14 | QC tự động | **93** | 22 | 95 | 2 | MEASURED — LUFS/peak/ASR/similarity/F0/watermark vs tỉ lệ phủ câu |
| 15 | Runtime (nạp/ấm/latency) | **80** | 60 | 88 | 8 | MEASURED |
| 16 | GPU (đo thật, xếp chỗ) | **90** | 55 | 92 | 2 | MEASURED — chốt GPU đọc từ số đo |
| 17 | Batch | **35** | 72 | 78 | 43 | MEASURED — LTT có API, **chưa nối**; Viral bắt buộc dùng |
| 18 | Streaming | **10** | 15 | 65 | 55 | MEASURED — cả hai đều gần như không có |
| 19 | Fallback | **30** | 78 | 80 | 50 | MEASURED — LTT **không có** đường lùi giọng |
| 20 | Model lifecycle (tải/verify/cache) | **40** | 82 | 85 | 45 | MEASURED — `_onnx_hop_le` + atomic rename |
| 21 | Storage | **88** | 25 | 90 | 2 | MEASURED — kho có khoá, có dọn, có `Range` |
| 22 | Jobs / hàng đợi | **92** | 10 | 94 | 2 | MEASURED |
| 23 | Retry / phục hồi | **88** | 55 | 92 | 4 | MEASURED — 5 lần, backoff đo theo cold start |
| 24 | Credit / hoá đơn | **92** | **0** | 95 | 3 | MEASURED — Viral không có khái niệm tiền |
| 25 | Security | **85** | 15 | 90 | 5 | MEASURED — Viral né chống-lạm-dụng, ký giả client |
| 26 | Ownership | **93** | **0** | 95 | 2 | MEASURED |
| 27 | Consent | **88** | **0** | 95 | 7 | MEASURED — bảng `voice_consent` vs không có |
| 28 | Public API | **85** | 20 | 90 | 5 | MEASURED — 3 cổng fail-closed + `api_contract` |
| 29 | Projects | **85** | **0** | 90 | 5 | MEASURED — dự án + khối + **phiên bản khối** |
| 30 | History | **82** | 15 | 88 | 6 | MEASURED |
| 31 | UI (màn chính) | **80** | 58 | 90 | 10 | MEASURED |
| 32 | Mobile | **70** | **0** | 85 | 15 | MEASURED — pha Mobile B+C đã có |
| 33 | Accessibility | **78** | 10 | 90 | 12 | MEASURED — ARIA + test riêng vs không có |
| 34 | Observability | **75** | 45 | 88 | 13 | MEASURED — `/health/version` 3 trường; **thiếu chỉ số/giọng** |
| 35 | Maintainability | **88** | 25 | 90 | 2 | MEASURED — 20 tệp test voice; 13.116 dòng có ranh giới |
| 36 | License / provenance | **72** | **8** | 95 | 23 | MEASURED §13 — LTT sạch ở engine, **hở ở Q-01** |
| 37 | Per-voice runtime profile | **20** | **75** | 88 | 68 | MEASURED — `TOC_DOC` 61 giọng vs 1 hằng số toàn cục |
| 38 | Human curation (quy trình) | **70** | 72 | 92 | 22 | MEASURED — Viral ghi **lý do loại**, LTT chỉ ghi danh sách giữ |

### Tổng hợp

| | Điểm | Cách tính |
|---|---|---|
| **LTT hiện tại** | **74 / 100** | trung bình 35 hạng mục có điểm (bỏ 3 hạng mục N/A) |
| **Viral** | **37 / 100** | idem |
| **LTT sau lộ trình §19** | **88 / 100** | idem, dùng cột Best target |

⛔ **Ba hạng mục N/A (VI quality · EN quality · mixed VI/EN) là ba hạng mục quan trọng nhất với khách,
và không hạng mục nào trong đó có điểm.** Bất kỳ ai đọc con số 74 mà quên điều này là đang đọc sai.

---

## 15. GAP ANALYSIS — LTT thiếu gì

Xếp theo **gap** giảm dần (cột cuối §14):

| Gap | Hạng mục | Điều thiếu, nói cụ thể |
|---|---|---|
| **68** | Per-voice runtime profile | Mọi ước lượng dùng **một** hằng số 18 ký tự/giây cho **cả 45 giọng**. Giọng chậm nhất và nhanh nhất trả cùng một dự báo. |
| **55** | Streaming | `/v1/stream` tồn tại ở sidecar, **không có client**. Khách chờ toàn bộ bài rồi mới nghe được tiếng đầu tiên. |
| **50** | Fallback | Giọng hỏng ⇒ **job lỗi**. Không có đường lùi cùng giới / cùng làn / cùng phong cách. |
| **45** | Model lifecycle | Không có bước kiểm model theo **nội dung**. Bản deploy hỏng nửa chừng ⇒ sidecar chết ở lúc nạp. |
| **43** | Batch | `infer_batch` — thứ gộp nhiều đoạn vào **một lượt GPU** — chưa dùng. `ban_doc_dai` gọi `lo_ra_tep` từng lô nhưng không tận dụng batch thật. |
| **23** | License / provenance | Q-01: chưa hỏi provenance giọng preset của VieNeu. |
| **22** | Voice discovery | Không có facet giới / vùng / phong cách, dù **dữ liệu đã có sẵn** trong `giong_mau_engine.json`. |
| **22** | Human curation | Không ghi **lý do loại**. Phiên sau có thể "khôi phục" một giọng đã bị loại có căn cứ. |
| **15** | Mobile | Đã có pha B+C, chưa soát toàn màn Voice trên thiết bị thật. |
| **13** | Observability | `/health/version` trả hợp đồng, **không** trả chỉ số theo giọng (RTF, tỉ lệ hỏng, CER). |
| **12** | Preview | Ấm mất **7 giờ** sau mỗi lần đổi `nghe_thu.PHIEN_BAN` — và không ai được báo là đang trong cửa sổ đó. |
| **12** | Accessibility | Có ARIA + test, chưa soát bàn phím/đọc màn hình cho **màn Dự án** và **thẻ giọng**. |

---

## 16. TARGET ARCHITECTURE

### 16.1 Nguyên tắc — ba điều không đổi

1. **MỘT engine cho VI/EN.** VieNeu v3 Turbo giữ nguyên vị trí trung tâm.
   Engine thứ hai chỉ vào sau **BENCHMARK** (§18, U-19) và chỉ với vai trò đã định trước.
2. **Danh tính giọng không bao giờ cột vào engine.** `voice_profile` ↔ `voice_repr(phien_ban_engine)`
   đã đúng — mọi thứ thêm vào phải đi qua đó.
3. **Không tầng nào đi vòng qua `jobs` / `credit` / `storage`.**

### 16.2 Kiến trúc mục tiêu

```
                            ┌──────────────────────────────────────────┐
                            │  VOICE CATALOG (mới)                     │
   Studio ───────────────►  │   VoiceProfile      danh tính công khai  │
   Dự án                    │   VoiceRuntimeProfile ◄── U-01 (MỚI)     │
   Public API               │     chars_per_second_measured            │
                            │     rtf_measured · avg_startup_s         │
                            │     cer/wer · dnsmos · stability         │
                            │     benchmark_version · sample_key       │
                            │   VoiceQualityProfile ◄── U-04 (MỚI)     │
                            │     trang_thai_curate: accepted|rejected │
                            │     ly_do_loai (chuỗi) ◄── T-12          │
                            │   VoiceLicense       ◄── U-05 (MỚI)      │
                            │     provenance · consent_id · commercial │
                            └───────────────┬──────────────────────────┘
                                            │
       ┌────────────────────────────────────┼────────────────────────────────┐
       ▼                                    ▼                                ▼
 ƯỚC LƯỢNG (U-01)                  ĐỊNH TUYẾN (U-02)                 QC & CHẤP NHẬN
 giay_uoc(text, voice_id)           chọn giọng thật:                  chot_sinh (K1) giữ nguyên
   = f(profile CỦA GIỌNG ĐÓ)          giọng yêu cầu                    + do_chat_luong (K2)
   -> credit đúng hơn                 -> nếu hỏng: CÙNG làn            + U-04 ghi lại vào
   -> ETA đúng hơn                       CÙNG giới                        VoiceQualityProfile
                                         CÙNG phong cách
                                      -> BÁO CHO KHÁCH, không âm thầm

                     ┌──────────────── VOICE CORE (không đổi) ────────────────┐
                     │ features.chuan_hoa · giai_giong (SỞ HỮU)               │
                     │ text_pipeline · ban_doc_dai · toc_do                   │
                     │ jobs -> credit hold -> worker -> settle                │
                     │ admission "vieneu_gpu" slots=1                         │
                     └───────────────────────┬───────────────────────────────┘
                                             ▼
                     ┌──────────── voice_sidecar (venv cách ly) ─────────────┐
                     │ /v1/speech  /v1/lo-ra-tep  /v1/ghep-tep  /v1/enroll   │
                     │ /v1/lo-ra-tep ── DA noi (U-06 XONG, xem dinh chinh)   │
                     │ /v1/stream  ◄── U-07 NỐI VÀO Studio (SSE/chunked)     │
                     │ engine.CongGiong ấm · chốt GPU theo SỐ ĐO             │
                     │ + U-08 kiểm model theo NỘI DUNG lúc khởi động (T-03)  │
                     └───────────────────────────────────────────────────────┘
```

### 16.3 `VoiceRuntimeProfile` — bảng mới, khai đầy đủ

| Trường | Kiểu | Nguồn | Ghi chú |
|---|---|---|---|
| `voice_public_id` | str | `voice_profile.public_id` hoặc tên preset | khoá |
| `engine_version` | str | `PHIEN_BAN_THAM_SO` | ⛔ đo lại khi đổi |
| `benchmark_version` | str | ví dụ `rt-2026-09-15a` | không có phiên bản = không đối soát được |
| `ngon_ngu` | `vi`\|`en` | làn của giọng | |
| `ky_tu_moi_giay` | float | **ĐO** — corpus chuẩn | thay hằng số toàn cục 18 |
| `giay_khoi_dong` | float | **ĐO** — chặn tuyến tính | hiện là 1,5 chung cho mọi giọng |
| `rtf` | float | **ĐO** | dùng cho ETA |
| `cer` / `wer` | float | `do_chat_luong.do_de_hieu` | thước chấp nhận |
| `dnsmos` | float | `voice_sidecar/dnsmos.py` | đã có bộ đo |
| `on_dinh` | float | `do_on_dinh.py` | |
| `giu_giong_nhieu_luot` | float | `do_giu_giong_nhieu_luot.py` | so với **sàn nhiễu của chính nó** |
| `khoa_nghe_thu` | str | `nghe_thu.khoa_mau()` | |
| `do_lech_chuan` | float | từ N lượt đo | ⛔ **một lượt không phải một phép đo** |

⛔ **Bảng này KHÔNG được điền bằng tay và KHÔNG được chép từ Viral.** `TOC_DOC` của Viral là
**từ/giây trên engine của họ**; con số ấy vô nghĩa ở đây. Lấy **khuôn**, đo **số của ta**.

### 16.4 Fallback — thiết kế, và một ranh giới cứng

```
yêu cầu: voice_id = X
   │
   ├─ X active + repr khớp engine_version  ────────────►  DÙNG X
   │
   ├─ X hỏng / repr lỗi thời
   │     ├─ TÌM: cùng làn ∧ cùng giới ∧ cùng phong cách ∧ cùng vùng
   │     ├─ không có: nới VÙNG   (giữ làn + giới + phong cách)
   │     ├─ không có: nới PHONG CÁCH (giữ làn + giới)
   │     └─ không có: ⛔ DỪNG — KHÔNG BAO GIỜ nới GIỚI hay LÀN
   │
   └─ mọi đường lùi PHẢI:
        · ghi vào `job.ket_qua.giong_thuc_te` ≠ `giong_yeu_cau`
        · hiện MỘT dòng cho khách: "Giọng A đang không dùng được, đã đọc bằng B (cùng nữ, miền Bắc)"
        · KHÔNG âm thầm  ◄── đây chính là bug Viral đã dính 26/08 ("giọng nam bị biến thành giọng nữ")
```

🔴 Ranh giới cứng: **không nới GIỚI, không nới LÀN.** Viral học điều này bằng một khiếu nại thật.
Ta học nó **miễn phí** — bằng cách đọc chú thích của họ.

---

## 17. TARGET VOICE LIBRARY (chỉ VI + EN)

### 17.1 Ba tầng, và khách chỉ thấy hai

| Tầng | Nguồn | Ai thấy | Số mục mục tiêu |
|---|---|---|---|
| **ENGINE PRESET** | 20 preset của VieNeu | mọi khách | **20** (giữ nguyên) |
| **PLATFORM VOICE** | kho dùng chung, đã curate | mọi khách | **VI 20–30 · EN 20–30** |
| **MY VOICE** | khách tự clone | chỉ chủ sở hữu | ∞ |

Khách **không cần biết** một giọng là preset hay platform — cả hai đều là "giọng có sẵn".
Phân biệt chỉ tồn tại **bên trong** để quản vòng đời và quyền.

### 17.2 Trường bắt buộc cho mỗi giọng

```
public_id          vc_<32hex> | tên preset            ổn định qua nâng engine
display_name       "Ngọc Huyền"                       KHÔNG dịch (đi thẳng vào infer nếu là preset)
ngon_ngu           vi | en                            LÀN — bộ lọc chính
gioi               nam | nu                           ◄── PHẢI thành BỘ LỌC, không chỉ là chữ
vung               bac | trung | nam | (en: us|gb)    ◄── PHẢI thành BỘ LỌC
phong_cach         tin_tuc | tu_nhien | doc_truyen    ◄── PHẢI thành BỘ LỌC (nhãn, không phải nút vặn)
nguon_goc          engine_preset | kho_cu(sha256) | khach_clone(ref_id)
nghe_thu_khoa      khoá kho tệp nghe thử               dựng SẴN theo bản phát hành (T-05)
kha_dung           active | dang_dung | ngung          ⛔ ngừng thì ẨN, không xoá voice_id
runtime_profile    -> VoiceRuntimeProfile              §16.3
quality_profile    -> VoiceQualityProfile              cer/wer/dnsmos/on_dinh + trạng thái curate
license_status     ok | unknown | blocked              ⛔ chỉ `ok` mới hiện ra cho khách
```

### 17.3 Mục tiêu số lượng — và vì sao **không** thêm giọng từ Viral

> *"20–30 VI cực tốt + 20–30 EN cực tốt hơn 5.000 giọng không curate."*

LTT hôm nay: **20 preset + 8 VI + 17 EN dùng chung = 45**. Tức đã **rất gần** mục tiêu.

Việc còn thiếu **không phải thêm giọng**, mà là:
1. **chấm điểm từng giọng** bằng bộ đo đã có (DNSMOS + CER/WER + ổn định) và **công bố** nó;
2. **loại** những giọng không đạt, **ghi lý do loại** (T-12);
3. **bổ sung 12–22 giọng VI** để lên 20–30 VI — nguồn phải là **clip có consent**, không phải mirror.

⛔ Và `en_US-ryan-high` (Piper, MIT, sạch) **cũng không** vào: nó là engine khác, 22 kHz, không clone,
và nó sẽ nghe **khác hẳn** 17 giọng EN hiện có. Một giọng lạc tông trong một kho đã đồng nhất là
một mất mát, không phải một bổ sung.

---

## 18. TOP 20 NÂNG CẤP (ROI cao nhất trước)

| # | ID | Nâng cấp | ROI | Nguồn |
|---|---|---|---|---|
| 1 | **U-01** | `VoiceRuntimeProfile` — đo ký tự/giây · RTF · khởi động cho **từng giọng**; thay hằng số 18 toàn cục | ⭐⭐⭐⭐⭐ | T-01 |
| 2 | **U-02** | **Fallback giọng có kiểm soát** — cùng làn ∧ giới ∧ phong cách, **báo cho khách**, không bao giờ âm thầm | ⭐⭐⭐⭐⭐ | T-02 |
| 3 | **U-03** | **Facet lọc giọng**: giới · vùng · phong cách (dữ liệu **đã có**, chỉ chưa thành nút) | ⭐⭐⭐⭐⭐ | T-08, T-09 |
| 4 | **U-04** | `VoiceQualityProfile` + **quy trình curate có LÝ DO LOẠI**, công bố điểm | ⭐⭐⭐⭐⭐ | T-12 |
| 5 | **U-05** | **Cổng license/provenance** — trường `license_status`, chỉ `ok` mới hiện; và **hỏi Q-01** | ⭐⭐⭐⭐⭐ | §13.3 |
| 6 | ~~**U-06**~~ | ✅ **ĐÃ XONG TỪ TRƯỚC — mục này là một PHÁT HIỆN SAI.** Đường bài dài đã gộp lô trên GPU qua `/v1/lo-ra-tep`. Xem §19.0 | — | §19.0 |
| 7 | **U-07** | Nối `/v1/stream` vào Studio (nghe được câu đầu trong ~2 s thay vì chờ cả bài) | ⭐⭐⭐⭐ | §5.3 |
| 8 | **U-08** | **Kiểm model theo NỘI DUNG** lúc sidecar khởi động (size + magic byte), từ chối nạp bản hỏng | ⭐⭐⭐⭐ | T-03 |
| 9 | **U-09** | **Preview đóng gói theo bản phát hành** — dựng lúc build, không dựng dần 7 giờ | ⭐⭐⭐⭐ | T-05 |
| 10 | **U-10** | **Benchmark VI/EN cùng corpus** — lấp ba ô N/A của §14 | ⭐⭐⭐⭐ | §6.2, §7 |
| 11 | **U-11** | **ETA hiển thị cho khách** (dùng U-01): "khoảng 2 phút 40" thay vì thanh chạy vô định | ⭐⭐⭐⭐ | T-01 |
| 12 | **U-12** | **Xếp giọng theo mức dùng THẬT CỦA TA** (đếm từ `jobs`), không lấy dữ liệu bên thứ ba | ⭐⭐⭐ | T-11 |
| 13 | **U-13** | **Nghe thử văn bản của khách** — có trần (1 câu / N lần một giờ), đứng **sau** admission | ⭐⭐⭐ | T-06 |
| 14 | **U-14** | **Chỉ số theo giọng ở `/health/version`** hoặc trang admin: RTF, tỉ lệ hỏng, CER trung vị | ⭐⭐⭐ | §15 |
| 15 | **U-15** | **Khuôn chuẩn-hoá theo cỡ engine** — tách "số/ngày/tiền" khỏi "phiên âm", sẵn cho engine 2 | ⭐⭐⭐ | T-07 |
| 16 | **U-16** | **Bổ sung 12–22 giọng VI có consent** để chạm mục tiêu 20–30 VI | ⭐⭐⭐ | §17.3 |
| 17 | **U-17** | **Soát a11y + mobile** cho màn Dự án và thẻ giọng trên thiết bị thật | ⭐⭐⭐ | §15 |
| 18 | **U-18** | **Dọn bề mặt chết**: `/v1/voices` · `/v1/capabilities` · `/v1/speech-dai` — gỡ hoặc nối, **không để lửng** | ⭐⭐ | §5.3 |
| 19 | **U-19** | **BENCHMARK OmniVoice** làm engine dự phòng (chỉ sau khi license trọng số rõ) | ⭐⭐ | R-11 |
| 20 | **U-20** | **Bộ xếp lịch ưu tiên** — điều kiện đã ghi để nâng `TRAN_KY_TU_CONG_KHAI` quá 100.000 | ⭐⭐ | §2.3 |

---

## 19.0 ĐÍNH CHÍNH 08/09/2026 — U-06 ĐÃ XONG TỪ TRƯỚC KHI BẢN NÀY ĐƯỢC VIẾT

**Bản kiểm toán này nói sai về U-06.** Nó xếp *"nối `infer_batch` vào
`ban_doc_dai`"* vào P3 như một việc chưa làm. Đo lại 08/09/2026:

```
ban_doc_dai._sinh_mot_lo(8 doan)          SO_DOAN_MOI_LO = 8
  -> sidecar_client.lo_ra_tep(...)
  -> POST /v1/lo-ra-tep                    voice_sidecar/server.py:397
  -> c.noi_lo(texts[i:i+n], ...)           TRAN_SO_VAN_BAN_BATCH = 8
  -> self._tts.infer_batch(...)            voice_sidecar/engine.py:349
```

Tức đường bài dài **đã** gộp nhiều đoạn vào một lượt forward trên GPU, và đã
làm vậy từ trước.

### 🔴 Vì sao phép rà soát bỏ sót — và đây mới là phần đáng giữ

Tôi tìm **một cái tên** (`/v1/batch`) thay vì tìm **một tính chất** (*"đường bài
dài có chạm `infer_batch` không"*). `/v1/batch` thật sự không có ai gọi ngoài
công cụ đo — kết luận ấy **đúng**. Nhưng nó không phải câu hỏi cần trả lời.

⭐ Cùng hình dạng lỗi với ba ca khác ghi trong `DECISIONS.md::DV-013`: **phạm vi
   phép đo hẹp hơn phạm vi kết luận.** Ở đây phép đo có một trục (*tên endpoint*)
   còn kết luận có một trục khác (*đường tới GPU*), và hai trục ấy tình cờ nghe
   giống nhau.

### ⭐ Và cửa đang dùng TỐT HƠN cửa bản kiểm toán đề nghị

`/v1/batch` trả base64 của từng WAV trong JSON. Với một cuốn sách thì worker
phải giữ chúng, giải base64, rồi ghi ra đĩa — hàng chục lần.
`/v1/lo-ra-tep` để sidecar ghi thẳng: **không byte âm thanh nào đi qua HTTP**,
và nó ghi float32 thay vì PCM16 (một ràng buộc đã chốt bằng phép kiểm — mẫu
vượt 1,0 lưu PCM16 là kẹp **ngay lúc ghi**, trước khi bộ hạ trần đỉnh kịp chạy).

⇒ Nếu ai đó đã "thi hành U-06" theo đúng chữ của bản gốc, họ sẽ **thay một cửa
  tốt bằng một cửa tệ hơn** — và đo bằng thông lượng GPU thì không thấy gì,
  vì cả hai cùng gọi `infer_batch`.

⛔ `tests/test_510` chốt tính chất chứ không chốt tên cửa: *đường bài dài phải
   gửi **nhiều hơn một** đoạn trong một lượt gọi sidecar.*

---

## 19. IMPLEMENTATION ROADMAP

### P0 — bug / thiếu E2E

---
**ID:** `P0-1` · **Ưu tiên:** P0
**Vấn đề:** Năm bề mặt sidecar đã xây nhưng không nối sản phẩm; `/v1/stream` **không có client**.
**Bằng chứng:** §5.3 — `giong_dung_san()` và `nang_luc()` có **0 nơi gọi**; `noi_lo`/`noi_dai`/`ghi_danh_kho` chỉ có công cụ đo gọi.
**Tệp nguồn:** `apps/ltt_voice/sidecar_client.py`, `voice_sidecar/server.py`
**Tệp đích:** như trên + `apps/ltt_voice/routes/_p_tao.py`
**Giải pháp:** Quyết định **từng** bề mặt: nối (U-06/U-07) hoặc gỡ (U-18). Không để trạng thái thứ ba.
**Rủi ro:** Gỡ nhầm một bề mặt đang phục vụ ai đó → tra `GOI_TAI`/`BUILT_PAGES`/registry trước khi xoá.
**Test:** một phép kiểm chốt "mọi hàm public của `sidecar_client` có ≥1 nơi gọi ngoài `tools/`".
**Chấp nhận:** `RESULT: PASS` gate đầy đủ + phép kiểm mới đỏ khi tiêm lại trạng thái cũ.
**Độ phức tạp:** M · **Phụ thuộc:** —

---
**ID:** `P0-2` · **Ưu tiên:** P0
**Vấn đề:** Giọng hỏng ⇒ job lỗi. Không có đường lùi nào.
**Bằng chứng:** §15 (gap 50); `features.giai_giong` ném khi không giải được.
**Tệp nguồn:** `apps/ltt_voice/features.py`
**Tệp đích:** `features.py` + `giong_mau.py` + template thông báo
**Giải pháp:** U-02 theo sơ đồ §16.4. **Không nới giới, không nới làn.**
**Rủi ro:** Lùi âm thầm = đúng bug Viral. Bắt buộc `giong_thuc_te` trong kết quả + dòng báo.
**Test:** `test_xxx_lui_giong` — giả lập repr lỗi thời, chốt (a) có lùi, (b) **cùng giới**, (c) có dòng báo.
**Chấp nhận:** Đối chứng: bỏ điều kiện "cùng giới" ⇒ test phải **ĐỎ**.
**Độ phức tạp:** M · **Phụ thuộc:** U-04 (trạng thái giọng)

---
**ID:** `P0-3` · **Ưu tiên:** P0
**Vấn đề:** Sidecar nạp model mà không kiểm tính hợp lệ của tệp.
**Bằng chứng:** T-03 — lớp lỗi "HTTP 200 kèm HTML" đã xảy ra thật ở Viral 07/08.
**Tệp đích:** `voice_sidecar/engine.py` (đường `nap()`)
**Giải pháp:** U-08 — kiểm size tối thiểu + magic byte trước khi gọi loader; từ chối bằng `LoiEngine` có thông điệp rõ.
**Rủi ro:** Rất thấp (thêm một cổng, không đổi đường thành công).
**Test:** ghi một tệp 5 KB nội dung `<html>` vào đường model tạm ⇒ chốt `LoiEngine`.
**Chấp nhận:** Test đỏ khi gỡ cổng.
**Độ phức tạp:** S · **Phụ thuộc:** —

---

### P1 — chất lượng

---
**ID:** `P1-1` · **Ưu tiên:** P1 · **(U-01, ROI cao nhất toàn lộ trình)**
**Vấn đề:** Một hằng số 18 ký tự/giây dùng cho **cả 45 giọng**.
**Bằng chứng:** `gia.KY_TU_MOI_GIAY_UOC = 18`; §14 hạng mục 37 gap **68**.
**Tệp nguồn:** `apps/ltt_voice/gia.py`, `tools/do_gia_von_voice.py`
**Tệp đích:** bảng mới `voice_runtime_profile` + `gia.giay_uoc(so_ky_tu, voice_id=None)`
**Giải pháp:** §16.3. Đo **N ≥ 3 lượt** mỗi giọng trên corpus cố định; ghi `do_lech_chuan`.
**Rủi ro:** ⛔ **Ước THIẾU là lỗi sổ sách.** Giữ chỗ phải dùng cận trên: `ky_tu_moi_giay − 2σ`.
**Test:** `test_xxx` chốt `uoc_tran(voice) >= tinh(giay_thật)` cho **mọi** giọng trong bảng.
**Chấp nhận:** Bảng có ≥ 40/45 giọng; giọng thiếu profile **lùi về hằng số cũ**, không lỗi.
**Độ phức tạp:** L · **Phụ thuộc:** cửa sổ yên GPU

---
**ID:** `P1-2` · **Ưu tiên:** P1 · **(U-10)**
**Vấn đề:** Ba hạng mục quan trọng nhất với khách đều **N/A**.
**Bằng chứng:** §14 hàng 3/4/5.
**Tệp đích:** `tools/cong_chat_luong_voice.py` (mở rộng) + `docs/LTT_VOICE/BENCHMARK_VI_EN.md`
**Giải pháp:** Corpus cố định: 30 câu VI + 30 câu EN + 15 câu **trộn VI/EN**; đo CER/WER/DNSMOS/similarity/F0; ≥ 3 lượt để rút σ.
**Rủi ro:** ⛔ Một lượt **không phải** một phép đo — chính `tham_so_cong_khai.py` đã tự ghi cảnh báo này.
**Chấp nhận:** Có σ cho mọi chỉ số; ba ô N/A của §14 được thay bằng số **có σ**.
**Độ phức tạp:** L · **Phụ thuộc:** P1-1 (dùng chung corpus)

---
**ID:** `P1-3` · **Ưu tiên:** P1 · **(U-04, U-05)**
**Vấn đề:** Không có trạng thái curate, không có lý do loại, không có trạng thái license trên từng giọng.
**Tệp đích:** bảng `voice_quality_profile` + cột `license_status` trên `voice_profile`
**Giải pháp:** §16.3 + §17.2. Chỉ `license_status == "ok"` mới ra bộ chọn giọng.
**Rủi ro:** Nếu đặt cổng ở **template** thay vì ở **truy vấn**, một màn khác sẽ lộ giọng bị chặn.
**Test:** chốt truy vấn danh sách giọng **không bao giờ** trả mục `license_status != "ok"`.
**Chấp nhận:** Đối chứng: tiêm một giọng `blocked` ⇒ test **ĐỎ** nếu cổng bị gỡ.
**Độ phức tạp:** M · **Phụ thuộc:** Q-01

---

### P2 — kho giọng

- **`P2-1` (U-03)** Facet giới/vùng/phong cách ở `_voice_chon.html`. **S.** Dữ liệu đã có; giữ nguyên tắc **chạy được khi không có JS**.
- **`P2-2` (U-12)** Xếp theo mức dùng thật, đếm từ `jobs`. **S.** ⛔ Không lấy dữ liệu bên thứ ba.
- **`P2-3` (U-16)** Bổ sung 12–22 giọng VI **có consent**. **L.** Chặn bởi P1-3.
- **`P2-4` (U-09)** Preview dựng lúc build. **M.** Tên tệp mang `PHIEN_BAN` + `PHIEN_BAN_THAM_SO`.

### P3 — engine / runtime

- ~~**`P3-1` (U-06)**~~ ✅ **RÚT — việc đã có sẵn.** Xem §19.0.
- **`P3-2` (U-07)** Streaming. **L.** Phải giành **cùng** `vieneu_gpu` slot; tính tiền theo giây đã phát.
- **`P3-3` (U-15)** Khuôn chuẩn hoá theo cỡ engine. **S.**
- **`P3-4` (U-19)** Benchmark OmniVoice. **M.** ⛔ Chặn cứng bởi license trọng số.
- **`P3-5` (U-20)** Bộ xếp lịch ưu tiên. **XL.** Điều kiện để nâng trần quá 100.000.

### P4 — UX

- **`P4-1` (U-11)** ETA thật cho khách. **S.** Chặn bởi P1-1.
- **`P4-2` (U-13)** Nghe thử văn bản của khách, có trần. **M.**
- **`P4-3` (U-17)** Soát a11y + mobile màn Dự án/thẻ giọng. **M.**

### P5 — production hardening

- **`P5-1` (U-14)** Chỉ số theo giọng. **M.**
- **`P5-2` (U-18)** Dọn bề mặt chết. **S.** ⛔ Tra `GOI_TAI`/`BUILT_PAGES`/registry **trước** khi xoá.
- **`P5-3`** Cảnh báo khi kho nghe thử chưa ấm sau deploy (thay vì im lặng 7 giờ). **S.**

---

## 20. ACCEPTANCE GATES

```
CODE PASS            tools/gate.py --vong-lap  xanh
  ↓
UNIT PASS            20 tệp test_*ltt_voice*/voice_sidecar xanh
  ↓
INTEGRATION PASS     tools/gate.py ĐẦY ĐỦ xanh  (⛔ --quick KHÔNG phải bằng chứng)
  ↓
REAL BROWSER PASS    https://app.lttstudios.com (CÔNG KHAI, không loopback) — 0 lỗi console,
                     0 request hỏng; kiểm cả sau khi asset_ver đổi
  ↓
REAL WORKER PASS     job THẬT qua hàng đợi, làn `voice` có trong LTT_WORKER_POOLS
  ↓
REAL GPU PASS        engine.chốt-GPU đọc từ torch memory_allocated, không đọc cờ
  ↓
REAL AUDIO PASS      chot_sinh K1 (4 chốt) + do_chat_luong K2 phán quyết "dat"
  ↓
HUMAN LISTENING PASS chủ sản phẩm nghe; ⛔ mọi giọng LOẠI phải có LÝ DO ghi lại (T-12)
  ↓
REAL CREDIT PASS     giữ chỗ >= giá thật ở MỌI giọng; hoàn dư đúng; không đo được -> thu 0
  ↓
OWNER ISOLATION PASS tài khoản A không thấy/không dùng được voice_id của B
  ↓
FAILURE/RETRY PASS   giết sidecar giữa job -> 5 lần thử, backoff ~150 s -> job SỐNG
  ↓
RESTART/RESUME PASS  reboot giữa bài 100.000 ký tự -> đọc TIẾP từ đoạn dở, không từ đoạn 1
  ↓
PRODUCTION PASS      /health/version: commit + asset_ver + hop_dong KHỚP kho
                     và nghiệm thu deploy hỏi BA CHIỀU (thiếu · lệch · THỪA)
```

⛔ **Không gọi một tính năng là DONE trước `REAL CREDIT PASS`.** Với app này credit **là** sản phẩm.
⛔ Và không gọi DONE dựa vào unit test — `manifest.py` đã ghi lại lần vòng kiểm trình duyệt tìm ra
**ba lỗi mà toàn bộ bộ test bỏ qua** (422 / 500 / `owner_id` sai kiểu).

---

## 21. OPEN QUESTIONS / BẰNG CHỨNG CÒN THIẾU

| # | Câu hỏi | Vì sao quan trọng | Cách trả lời |
|---|---|---|---|
| **Q-01** | Provenance của **20 giọng preset VieNeu** — giọng của ai, có consent không? | Ta vừa chặn Viral vì đúng lý do này. Không hỏi mình là soát không trung thực. | Hỏi tác giả `pnnbao-ump`; đọc model card của `VieNeu-TTS-10k-ENVI` |
| **Q-02** | License **trọng số** OmniVoice | Card HF **không khai**; repo code Apache-2.0 | Hỏi k2-fsa / mở issue |
| **Q-03** | VI/EN/mixed quality **so với ElevenLabs, CapCut, Piper** trên cùng corpus | Ba ô N/A của §14 là ba ô khách quan tâm nhất | P1-2 |
| **Q-04** | Provenance **25 giọng dùng chung** (kho F5/XTTS cũ) | Cùng lớp câu hỏi Q-01, và đây là giọng **của ta** | Tra `voice_ref.sha256` ngược về clip nguồn + `voice_consent` |
| **Q-05** | `infer_batch` có thật sự tiết kiệm GPU-giây không? | ⚠️ Câu hỏi **vẫn còn giá trị** nhưng đã đổi ý nghĩa: nó không còn quyết định *có làm U-06 không* mà quyết định *có nên GIỮ phép gộp lô đang chạy không* | Đo `tools/do_lo_giong.py` mở rộng: 1 lượt N đoạn vs N lượt 1 đoạn |
| **Q-06** | Streaming có giữ chất lượng bằng non-stream không? | Nếu drift tăng thì U-07 đổi chất lượng lấy độ trễ | Đo CER/WER trên bản stream vs bản thường |
| **Q-07** | Có phải **mọi** giọng đều dùng chung `giay_khoi_dong = 1,5`? | Nếu không, P1-1 phải đo hai tham số/giọng chứ không một | Khớp tuyến tính riêng từng giọng |
| **Q-08** | Cửa sổ 7 giờ ấm preview có ảnh hưởng khách thật không? | Quyết định U-09 đáng làm hay không | Đếm lượt bấm "nghe thử" gặp `co_san == False` trong log |
| **Q-09** | Kiểm GUI Studio bằng trình duyệt thật ở lượt soát này | Lượt này **chưa làm** — không có mật khẩu tài khoản test | Chạy Playwright với `--cdp` vào Chrome đã đăng nhập |

### ⚠️ Giới hạn của chính báo cáo này — nói ra để không ai đọc quá

1. **Không có phép nghe nào được thực hiện.** Mọi so sánh chất lượng âm thanh là **N/A**.
2. **Không kiểm GUI bằng trình duyệt thật** (Q-09) — phần §10 dựa trên template + JS + tài liệu UI audit.
3. **`ViralCrawl.exe` (181 MB) và `app.asar` (2,4 MB) chưa được giải nén.** Mã Python ở `app-src`
   là mã thật đang chạy (Electron spawn Python), nhưng **lớp Electron chưa được soát**.
4. **Không chạy Viral.** Mọi kết luận về hành vi runtime của Viral là **đọc mã + đọc chú thích của
   chính họ**, không phải quan sát. Chú thích của Viral rất chi tiết và tự phê — nhưng nó vẫn là
   **lời khai**, không phải phép đo của ta.
5. `license_server/` của Viral (thư mục có `dong_bo_11labs.py`) **không có trong bundle này** — chỉ
   được nhắc trong chú thích. Đường quét ElevenLabs vì vậy là **INFERRED**, không phải MEASURED.

---

## PHỤ LỤC A — 10 KẾT LUẬN QUAN TRỌNG NHẤT

1. **16 giọng Việt của Viral có vấn đề likeness rights.** Kho gốc chứa `mytam2`, `tranthanh3870`;
   Viral **ship** `ngocngan3701` dưới tên "Ngọc Ngạn". `apache-2.0` không cấp quyền giọng người thật.
   **Không giọng nào sang LTT được.**
2. **ElevenLabs trong Viral không có model, không có quyền, và KHÔNG CÓ TIẾNG VIỆT** (`giong_11labs/`
   có 29 ngôn ngữ, **không có `vi.json`**). 9.437 mục ấy là danh mục đi mượn qua một API dịch ngược.
3. **CapCut TTS là API dịch ngược có né chống-lạm-dụng** (ký RSA giả client, xoay `device_id` khi
   dính "shark block"). Một SaaS thu tiền không đứng lên được trên nó.
4. **Supertonic là engine chết**: README khai, mã không có, **90 MP3 preview mồ côi** vẫn nằm trong bundle.
5. **Tab "Tạo Voice" của Viral là đường vòng qua khâu lồng tiếng video**: dựng timeline giả từ ước
   lượng ký tự, rồi cắt lại khoảng câm bằng ffmpeg. Chính chú thích của họ ghi ra cách đúng và ghi
   luôn lý do không làm.
6. **LTT hơn Viral ở mọi tầng kỹ thuật nghiêm túc**: QC âm học thật vs một tỉ lệ phủ câu; long-form
   đọc-tiếp-được vs không; sở hữu + consent + credit vs **không có khái niệm nào**.
7. **Khoảng cách lớn nhất của LTT là per-voice runtime profile (gap 68).** Một hằng số 18 ký tự/giây
   đang phục vụ cả 45 giọng — ước lượng credit và ETA đều thô theo đúng mức đó.
8. **LTT có năm bề mặt sidecar đã xây mà chưa nối sản phẩm**, trong đó `/v1/stream` chưa từng có client.
   Đây là nợ có thật, không phải "tính năng tương lai".
9. **Ba hạng mục quan trọng nhất với khách — VI quality, EN quality, mixed VI/EN — đều là N/A ở CẢ HAI
   hệ.** Không có benchmark cùng corpus. Mọi kết luận "hay hơn" về âm thanh, của ai nói cũng vậy,
   hiện đang không có căn cứ.
10. **Và ta phải soi chính ta bằng cùng thước đo**: provenance giọng preset của VieNeu **chưa từng
    được hỏi** (Q-01). Chặn Viral vì likeness mà không hỏi mình là một lượt soát không trung thực.

## PHỤ LỤC B — ĐIỂM LTT HIỆN TẠI

**74 / 100** — trung bình 35 hạng mục có bằng chứng (§14). Ba hạng mục về chất lượng nghe: **N/A**.

## PHỤ LỤC C — ĐIỂM VIRAL

**37 / 100** — cùng thang, cùng 35 hạng mục.
Điểm bị kéo xuống chủ yếu bởi: license/provenance **8**, credit **0**, ownership **0**, consent **0**,
Projects **0**, mobile **0**, jobs **10**, security **15**.

## PHỤ LỤC D — ĐIỂM LTT SAU UPGRADE

**88 / 100** — theo cột *Best target* của §14, tức sau khi hoàn thành P0 + P1 + P2 + phần lớn P3/P4.
⛔ Không đặt mục tiêu 95+: ba ô N/A phải có số trước, và một mục tiêu đặt trên chỗ chưa đo là một
mục tiêu không kiểm được.

## PHỤ LỤC E — TOP 10 THỨ NÊN LẤY TỪ VIRAL

| # | Thứ | Dạng | Vì sao |
|---|---|---|---|
| 1 | **Per-voice measured runtime profile** (`TOC_DOC`) | ADAPT khuôn, đo lại số | ROI cao nhất; sửa đúng gap lớn nhất |
| 2 | **Fallback giữ GIỚI TÍNH, không âm thầm** | ADAPT | Họ trả giá bằng một khiếu nại thật; ta lấy miễn phí |
| 3 | **Validate model theo NỘI DUNG** (`_onnx_hop_le`) | ADAPT | Bắt lớp lỗi mà `isfile()` không thấy |
| 4 | **`.part` → verify → `os.replace`** | ADAPT | Không để lại bản dở sau đứt mạng |
| 5 | **Preview đóng gói theo bản phát hành** | ADAPT | Xoá cửa sổ 7 giờ "đang chuẩn bị" của LTT |
| 6 | **Ghi LÝ DO LOẠI giọng ngay trong mã** | ADAPT | Chống việc phiên sau khôi phục một giọng đã bị loại có căn cứ |
| 7 | **Tách nhóm khi kho lớn** (bài học "rừng giọng Microsoft") | REWRITE | Kho 45→100 vẫn duyệt được |
| 8 | **Lọc theo giới bằng một cú bấm** | REWRITE | Cắt kho làm đôi; dữ liệu LTT đã có |
| 9 | **Khuôn chuẩn hoá theo CỠ ENGINE** | ADAPT | Sẵn khuôn cho ngày có engine thứ hai |
| 10 | **ASR ngược làm thước chấp nhận giọng** | **KEEP LTT** (đã mạnh hơn) — lấy **cách công bố** kết quả | Viral công bố số; LTT đo mà không công bố |

## PHỤ LỤC F — TOP 10 THỨ TUYỆT ĐỐI KHÔNG NÊN LẤY

| # | Thứ | Lý do một dòng |
|---|---|---|
| 1 | **16 model NghiTTS** | Likeness rights của người thật, nổi tiếng, còn sống |
| 2 | **CapCut TTS** | API dịch ngược + **né cơ chế chống lạm dụng** |
| 3 | **Edge TTS** | Dùng endpoint Microsoft ngoài mục đích, không hợp đồng, hay bị throttle |
| 4 | **Danh mục + voice_id ElevenLabs** | Tài sản bên thứ ba — và **không có tiếng Việt** |
| 5 | **`giong_mau/{nam,nu}.wav`** làm nguồn clone | Không nguồn gốc, không consent; ta có `voice_consent` chính vì việc này |
| 6 | **Kiến trúc `segs_vi` giả + `_nen_im_lang`** | Tạo lỗi rồi dọn lỗi bằng ffmpeg |
| 7 | **`localize.py` / `web_app.py`** làm mẫu tổ chức | 20.644 / 22.935 dòng, không ranh giới |
| 8 | **Nhãn "Chất Lượng 8/10"** | Điểm số không có phép đo — với sản phẩm thu tiền là mô tả sai |
| 9 | **90 preview Supertonic** | Lời hứa không có gì đằng sau |
| 10 | **6 model Piper non-VI** | Ngoài phạm vi VI/EN; và một giọng lạc tông làm hỏng một kho đã đồng nhất |

## PHỤ LỤC G — CÓ NÊN THÊM PIPER/NGHITTS LÀM ENGINE THỨ HAI?

# ⛔ **NO.**

**Không phải "BENCHMARK FIRST". Là NO** — vì nó bị chặn ở một cổng đứng **trước** cổng chất lượng.

**Bằng chứng, theo thứ tự tính quyết định:**

1. **LICENSE (chặn cứng).** Kho nguồn chứa `mytam2`, `mytam2794`, `tranthanh3870`; Viral ship
   `ngocngan3701`. Không có benchmark nào đi qua cổng này được. §13.2.
2. **Không clone được.** `num_speakers: 1` cho **mọi** model. Toàn bộ giá trị bán được của LTT Voice
   — "giọng của bạn" — **không tồn tại** trên Piper. Thêm nó là thêm một sản phẩm khác.
3. **22,05 kHz so với 48 kHz.** Băng thông dừng ở ~11 kHz; không có cách nào bù.
4. **Phoneme espeak-vi** — bộ luật đơn giản, không mô hình hoá thanh điệu như một hệ thống.
5. **Chi phí biên thật là kiến trúc, không phải model.** Engine thứ hai kéo theo: chọn engine, ánh
   xạ giọng↔engine, `voice_repr` theo engine, chuẩn hoá theo cỡ engine, QC hai đường, giá hai đường,
   fallback giữa engine. `manifest.py` đã ghi: *"buộc mở rộng enum … tức sửa nền tảng cho một năng
   lực không dùng tới"*.

**Piper chỉ đáng xem lại nếu — và chỉ nếu — cả bốn điều sau cùng đúng:**
(a) có nhu cầu **CPU-only** thật (khách self-host / máy không GPU);
(b) dùng model `rhasspy/piper-voices` **chính chủ MIT**, không dùng mirror NghiTTS;
(c) chấp nhận nhánh đó **không có clone**;
(d) đã có bộ xếp lịch nhiều engine (P3-5).

Hôm nay **không** điều nào đúng.

**Nếu một ngày cần engine thứ hai thật, ứng viên là OmniVoice, không phải Piper** — Apache-2.0 (code),
clone được, đã có số ASR-ngược xuyên ngôn ngữ. Nhưng **BENCHMARK FIRST**, và **chặn cứng** cho tới khi
license **trọng số** rõ ràng (Q-02).

## PHỤ LỤC H — CÓ MODEL/VOICE LOCAL NÀO TRONG `D:\Viral` ĐÁNG SANG LTT?

# ⛔ **KHÔNG CÓ.**

Liệt kê đầy đủ, chính xác, kèm phán quyết:

| Path | Định dạng | Số | Dung lượng | License | Provenance | Phán quyết |
|---|---|---|---|---|---|---|
| `resources/vendor/piper_models/{ngochuyen,ngochuyennew,ngocngan3701,maiphuong,phuongtrang,thanhphuong2,calmwoman3688,yannew,lacphi,manhdung,minhkhang,minhquang,duyoryx3175,adam1,chieuthanh,taian4}.onnx` | ONNX VITS 22,05 kHz | **16** | 16 × 63.516.050 B ≈ **969 MB** | `apache-2.0` **khai bởi người mirror** | ⛔ **BLOCKED** — kho gốc chứa giọng người nổi tiếng; `ngocngan3701` ship dưới tên "Ngọc Ngạn" | ⛔ **KHÔNG LẤY** |
| `resources/vendor/piper_models/{en_US-ryan,de_DE-thorsten,es_AR-daniela,pl_PL-bass,uk_UA-tetiana,kk_KZ-issai}-high.onnx` | ONNX VITS | **6** | ≈ **705 MB** | **MIT** ✅ (`rhasspy/piper-voices`) | ✅ **SẠCH** | ⛔ **KHÔNG LẤY** — ngoài phạm vi; 22 kHz, không clone, lạc tông với kho hiện có |
| `resources/vendor/piper_models/*.onnx.json` + `config.json` | JSON | 23 | 3.705–7.248 B | theo model | — | ⛔ không có model thì vô nghĩa |
| `resources/app-src/giong_mau/{nam,nu}.wav`, `{nam,nu}_omnicut.wav` | WAV | **4** | **8,1 MB** | **KHÔNG CÓ** | ⛔ transcript ASR của truyện người khác; **không consent** | ⛔ **TUYỆT ĐỐI KHÔNG** |
| `resources/app-src/giong_mau/nu.txt` | text | 1 | 1.927 B | — | ⛔ như trên | ⛔ **KHÔNG** |
| `resources/app-src/web/giong_thu/*.mp3` | MP3 | **277** | **13 MB** | — | ⛔ sinh bởi Edge/Supertonic/Piper — tài sản bên thứ ba hoặc mồ côi | ⛔ **KHÔNG** |
| `resources/app-src/giong_11labs/*.json` | JSON | **31 tệp / 9.437 mục** | **2,4 MB** | — | ⛔ dữ liệu ElevenLabs, quét bằng API key; **không có `vi`** | ⛔ **KHÔNG** |
| `resources/app-src/giong_tuyen/*.json` | JSON | 29 | 256 KB | — | ⛔ như trên | ⛔ **KHÔNG** |
| `.pt` / `.pth` / `.ckpt` / `.safetensors` / `.gguf` | — | **0** | 0 | — | — | **không tồn tại trong `D:\Viral`** |

⇒ Thứ duy nhất có license sạch (6 model Piper MIT) lại là thứ **ngoài phạm vi VI/EN chất lượng cao**.
Thứ duy nhất trong phạm vi (16 giọng VI) lại là thứ **bị chặn cứng về quyền**.
**Giao của hai tập là rỗng.**

## PHỤ LỤC I — KIẾN TRÚC CUỐI CÙNG ĐỀ XUẤT

### I.1 Vietnamese

```
Văn bản VI
  │
  ├─ text_pipeline.chuan_hoa()      ký hiệu · ngày · giờ · tiền · số có nhóm
  │    + tu_dien (chung) + tu_dien_rieng (của khách)
  │    ⛔ KHÔNG phiên âm Anh→Việt — VieNeu đọc chữ Latin đúng, phiên âm làm hỏng giọng
  │
  ├─ chia_doan() theo ranh giới CÂU, mỗi đoạn <= TRAN_MOI_LUOT_SINH (1.500)
  │
  ├─ chọn giọng: LÀN vi × [giới] × [vùng] × [phong cách]     ◄── U-03
  │    fallback: cùng làn ∧ cùng giới ∧ cùng phong cách, CÓ BÁO   ◄── U-02
  │
  ├─ ước lượng: VoiceRuntimeProfile CỦA GIỌNG ĐÓ            ◄── U-01
  │    credit giữ chỗ = f(ky_tu_moi_giay − 2σ)   ⛔ cận TRÊN, không cận giữa
  │
  ├─ VieNeu v3 Turbo · 48 kHz · một suất `vieneu_gpu`
  │    (bài dài: lo_ra_tep -> artifact/đoạn -> ghep_tep, ĐỌC TIẾP ĐƯỢC)
  │
  ├─ K1 chot_sinh (im lặng · quá ngắn · quá dài · lặp đuôi)
  ├─ K2 do_chat_luong (LUFS · true-peak · DC · khoảng lặng · CER/WER · similarity · F0 · watermark)
  ├─ toc_do.ap_dung()  ⛔ SAU khi đo giây (tính tiền) và SAU K1/K2 (F0)
  └─ ffprobe -> gia.tinh(giay THẬT) -> hoàn phần giữ dư
```

### I.2 English

**Cùng một đường**, khác đúng bốn chỗ:

1. `lan_ngon_ngu` = `en` ⇒ bộ chọn giọng lọc **17 giọng nguồn EN** (+ preset song ngữ).
2. `text_pipeline` bỏ qua nhánh **đọc số tiếng Việt**; ký hiệu vẫn thay (`%` → `percent`, `$` → `dollars`).
3. `do_de_hieu` chạy ASR **`language="en"`**, và ⛔ **không** dùng bộ chuẩn hoá dấu thanh tiếng Việt
   (`_DAU_THANH`, `_chi_dau`) — nó vô nghĩa cho EN và sẽ **thổi phồng** điểm khớp.
4. `VoiceRuntimeProfile` đo **riêng cho EN** — ký tự/giây tiếng Anh khác tiếng Việt về bản chất.

### I.3 Mixed VI/EN

```
⭐ KHÔNG chia câu theo ngôn ngữ. KHÔNG chuyển engine giữa chừng.

  VieNeu v3 Turbo train code-switching En–Vi TRONG CÙNG MỘT CÂU (model card).
  Chia câu ra rồi ghép lại sẽ TẠO RA một ranh giới ngữ điệu mà model vốn không có.

  ⇒ Đưa NGUYÊN câu trộn vào một lượt infer.

  Vai trò của `lan_ngon_ngu`:
     · giọng làn vi + văn bản có vẻ en  -> CẢNH BÁO (không chặn)
     · khách khai `Ngôn ngữ = Tự động`  -> doan_ngon_ngu(); None = IM LẶNG, đó là câu trả lời ĐÚNG
     · khách khai vi/en rõ              -> lời khai THẮNG phép đoán

  ⛔ Không bao giờ CHẶN: tiếng Việt viết không dấu KHÔNG phân biệt được với tiếng Anh
     bằng bảng mã. Một cổng chặn sẽ từ chối công việc hợp lệ của khách gõ không dấu.

  Chuẩn hoá cho câu trộn:
     · thay ký hiệu (chắc chắn cần, cả hai ngôn ngữ)
     · số: theo NGÔN NGỮ KHAI của lượt, không theo từng token
       (⛔ đoán ngôn ngữ ở mức token sẽ đọc "iPhone 15" thành "iPhone mười lăm" giữa câu tiếng Anh)
     · từ điển riêng của khách: áp cho CẢ HAI — đó là chỗ khách sửa tên riêng

  Đo (P1-2): 15 câu trộn trong corpus chuẩn, CER tính RIÊNG cho phần vi và phần en.
```

---

## PHỤ LỤC J

# STOP.

**Không implement gì cho tới khi báo cáo này được duyệt.**

Lượt này **không sửa một dòng mã nào**. Thay đổi duy nhất trên đĩa là **chính tệp này**.

Ba thứ nên duyệt **trước** mọi thứ khác, vì chúng chặn phần còn lại:
1. **Q-01** — hỏi provenance giọng preset VieNeu (chặn P1-3, chặn U-16).
2. **P0-2** — fallback giọng (đang là một lỗ hổng trải nghiệm thật, không phải một cải tiến).
3. **P1-1** — `VoiceRuntimeProfile` (ROI cao nhất, và P4-1 + P1-2 đều đứng sau nó).

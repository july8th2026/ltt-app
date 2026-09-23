# L-TOC-DO-GPU — Ra soat nut co chai duong chay that + day viec sang GPU

> Lan `toc-do-gpu` cua phien `asv-final`. Nhanh `phien/asv-final-toc-do-gpu`.
> Moi con so do 23/09/2026 tren may A (RTX 5060 Ti 16 GiB, driver 616.92, 20 loi),
> tren **dung phim khach that** cua `NEN_V3` (106,835 s, tieng Trung), qua
> `chay_nang.py` (khoa `cpu_nhieu`), may ranh (CPU 13%, RAM trong 41 GiB).
> Du lieu tho: scratch cua phien (`tdg/ra/ket_qua.json`, `doi_chieu.json`).

## 0. Bang xep hang — doc cai nay truoc

Cot "giay mat" = tren MOT phim 107 giay, so voi duong chay tot nhat da chung minh.

| # | Phat hien | Giay mat | Loai | Cach sua | Trang thai |
|---|---|---|---|---|---|
| 1 | **`audio_prepare` chay CPU vi bo nghiem thu KHONG cap lease GPU** — `test_448._chay_hang_doi` dung `JobContext(job.id)`, khong `gpu_uuid`, khong `_giu_gpu` | **29,8** | 1+2 | bo nghiem thu phai di qua `job_runner._giu_gpu` nhu worker that | ĐỀ XUẤT (tep cua lan `nghiem-thu`) |
| 2 | `edit_plan`: 4 loi goi VLM doc canh chay **lan luot** | **~79** (uoc tu 163,8 s / 2) | 3 | song song 2 luong, tran ≤ 2/model cua may B | ĐỀ XUẤT (rui ro: `lat_cat` + so cai + phien CSDL) |
| 3 | **Thoi gian chet giua 21 luot job** — moi giai doan la mot job rieng, xen 11 job `advance`, cac lan nang luc khac nhau, worker ngu `POLL_INTERVAL_S = 2 s` | **~16–20 trung binh, ≤ 40 xau nhat** | 1 | danh thuc lan dich khi xep job (LISTEN/NOTIFY), hoac ha poll | ĐỀ XUẤT (tep nen tang) |
| 4 | Duong lui faster-whisper **trong tien trinh** mac dinh `cuda` nhung tut xuong `cpu/int8` IM LANG | **203** khi no chay | 2 | chi dung card khi co lease VA ghim duoc; moi lan lui deu ghi log + tra ly do | ✅ ĐÃ SỬA |
| 5 | `asv_gpu.transcribe` khai **6.000 MiB**, do that **6.334 MiB** — khai THIEU ⇒ nguy co OOM | 0 s (rui ro) | 4 | 7.600 MiB (dinh + 20%), ca `autosubvideo.transcribe` | ✅ ĐÃ SỬA |
| 6 | `demucs_runner.chon_thiet_bi` lay card khi **khong co lease** (~1,1 GiB ngoai so sach) | 0 s (tranh card voi Voice) | 4 | hoi lease TRUOC, roi moi hoi `is_available()` | ✅ ĐÃ SỬA |
| 7 | `tools/nang_quyen.py` **khoa dong stdout** ⇒ log rong suot luot chay | 0 s (mu chan doan) | cong cu | `PYTHONUNBUFFERED` | ✅ ĐÃ GỘP (`e130e1d4`) |
| 8 | `cho_tai_nguyen_s = 20 s` — luong tu cho dai hon can, trong khi giai doan GPU chi 42–65 s | **0** mot phim · **~30** khi 2 lan chay chong | 1 | ha xuong 5 s | ĐỀ XUẤT (loi ich chua do) |
| 9 | `content_process` song song 2 luong | **0** — do that: `so_lo = 1` (6 doan, `DOAN_MOI_LO = 20`) ⇒ **MOT** loi goi, khong co gi de song song | 3 | khong lam | ❌ KHONG |
| 10 | `cache_chung.giu_cho` hoan 15 s | **0** mot phim (khong ai tranh) | 1 | khong lam | ❌ KHONG |
| 11 | `platform_core/leases.py` gia han | **0** — chi dung cho lease BAO TRI, khong nam tren duong chay ASV | 1 | khong lam | ❌ KHONG |
| 12 | OCR len GPU | am | 2 | giu CPU (da do 1,6x, phai them CUDA 13 + gianh card voi Voice) | ❌ KHONG |
| 13 | VMAF len GPU | khong lam duoc | 2 | ban ffmpeg nay **khong co** `libvmaf_cuda` | ❌ KHONG |

**Tong co the lay lai ngay (da sua hoac de xuat re):** ~30 s (demucs GPU) + ~16–20 s
(thoi gian chet) = **~46–50 s tren 1.333 s**, tuc ~3,7% ca lan chay nhung **~40% cua
phan viec CUC BO** (115 s: media+audio+transcribe+timing+compose+render+qc).
Them `edit_plan` song song thi ~125–130 s.

⛔ `voice_synthesis` 937–943 s (70–79% ca lan chay) **khong nam trong lan nay** va
khong duoc dong toi. Ghi ra vi moi phan tram o day chi la phan tram cua 21% con lai.

---

## 1. 🔴 Phat hien lon nhat: bang co so `NEN_V3` do NHAM moi truong

`NEN_V3.md` ghi "Whisper chay CPU/int8" va `audio_prepare 72,2 s`. Ca hai deu la
**tinh chat cua bo nghiem thu**, khong phai cua san pham.

Bang chung, doc thang tu ban ghi cua chinh luot chay
(`nen_v3_us_smart_localize.json` → `giai_doan`):

```
audio_prepare  tom_tat: {"thiet_bi": "cpu", "gpu_cap": "", "ten_card": "", ...}
transcribe     tom_tat: {"engine": "whisperx", "canh_chinh": "aligned", ...}
```

- `gpu_cap: ""` ⇒ **khong lease GPU nao duoc cap cho ca lan chay**.
  `tests/test_448_asv_v4_e2e_nghiem_thu.py:201` dung `JobContext(job.id)` — khong
  `gpu_uuid`, va khong goi `job_runner._giu_gpu`. Worker that thi goi
  (`job_runner.py:291-299`). Nen moi giai doan GPU cua luot nghiem thu deu chay
  voi `gpu_uuid=""`.
- `engine: "whisperx"` ⇒ **transcribe chua bao gio di qua duong faster-whisper**,
  nen `LTT_AUTOSUB_WHISPER_DEVICE=cpu` ma bo do dat **khong co tac dung gi**. Cau
  "Whisper chay CPU/int8" trong `NEN_V3.md` suy ra tu mot bien moi truong bo do
  TU dat, khong tu ban ghi.

⭐ **Bai hoc, va no lap lai mot bai hoc cu cua kho:** *mot cua gia chi tra loi
duoc nhung cau khong phu thuoc thu no thay the.* `_chay_hang_doi` thay **worker**,
roi duoc dung de tra loi cau *"giai doan nay chay tren card hay tren CPU"* — dung
cai no thay. Cung hinh dang voi ghi chu o dau chinh ham do (05/09, `_provider_failure_kind`).

**Cach sua (de xuat, khong tu lam — `test_448` la tep cua lan `nghiem-thu`):**

```python
from platform_core.job_runner import JobContext, _giu_gpu, _vram_can
...
with _giu_gpu("w-nghiem-thu", job.id, job.job_type,
              _vram_can(job.job_type)) as (lease, _het):
    ctx = JobContext(job.id, gpu_uuid=(lease.gpu_uuid if lease else ""))
    ...
```

⛔ Va du khong sua duoc ngay thi bao cao nghiem thu **phai in `gpu_cap`** cua tung
giai doan, de mot lan chay khong card khong bao gio doc giong mot lan chay co card.

---

## 2. Bang do — moi con so tren dung mot phim 107 s

Dau vao dung hai lenh ffmpeg cua san pham (`nhap_media.tach_tieng_cho_asr` 16 kHz
mono; `tach_tieng.rut_ban_day_du` 44,1 kHz stereo). Moi phep chay trong **tien
trinh rieng** cua `C:\LTTPlatform\venv` (venv cua WORKER), card ghim bang
`CUDA_VISIBLE_DEVICES=<UUID>`, VRAM lay mau 0,25 s/lan bang `nvidia-smi`.

| Phep | Thiet bi | Giay (ca tien trinh) | Nap model | Tinh | VRAM dinh (+ so voi nen) | RSS dinh |
|---|---|---|---|---|---|---|
| demucs htdemucs | **GPU** | **42,15** | — | — | **+1.083 MiB** | 1.781 MB |
| demucs htdemucs | CPU, 4 luong | 71,99 | — | — | +3 MiB | 1.909 MB |
| faster-whisper large-v3 | **GPU fp16** | **47,25** | 5,78 | **37,66** | **+5.221 MiB** | 3.737 MB |
| faster-whisper large-v3 | CPU int8 | 250,64 | 7,58 | 240,96 | +27 MiB | 3.656 MB |
| **WhisperX** (duong san pham) | **GPU fp16** | **64,64** | (2 model) | — | **+6.334 MiB** | 3.777 MB |

Tham so ASR chep dung ban san pham (`transcription._transcribe_faster`):
`language="zh"`, `beam_size=5`, `vad_filter=True`, `word_timestamps=True`.
Sau VAD con **83,72 s** tieng.

⚠️ Cot "CPU %" **khong co trong bang**, va do la mot han che cua bo do chu khong
phai mot so 0: `psutil.Process.cpu_percent(interval=None)` tra 0,0 o lan goi dau
cua moi doi tuong, va bo lay mau tao lai doi tuong con moi vong — nen so thu ve
la 0,0 o ca nam phep. Khong bao cao mot so ma minh biet la rac. Phep do CPU% dung
da co san o cho khac: `demucs_runner.LUONG_TORCH` ghi lai 413% CPU cho demucs tren
CUDA (03/09), va tran 4 luong van giu.

### 2.1 Do chinh xac — KHONG danh doi

| Phep so | Ket qua | Nguong |
|---|---|---|
| CER(ASR GPU fp16 ↔ ASR CPU int8) | **0,0015** | `sua_chua.NGUONG_DOC_SAI` vi CER 0,23 · en chi khai WER |
| CER(ASR CPU ↔ ban ghi `NEN_V3`) | 0,0155 | — |
| CER(ASR GPU ↔ ban ghi `NEN_V3`) | 0,0139 | — |

⇒ Khac biet **thiet bi** (0,15%) nho hon khac biet **engine** whisperx↔faster-whisper
(1,4–1,6%) gan muoi lan. Doi fp16/GPU khong dung toi do doc.

Stem demucs GPU so voi CPU (4.711.424 mau moi stem):

| Stem | Ty so tin/lech | Tuong quan | RMS lech | Dinh lech |
|---|---|---|---|---|
| vocals | 59,04 dB | 0,999999 | 0,00018 | 0,0012 |
| drums | 54,37 dB | 0,999998 | 0,00016 | 0,0017 |
| other | 36,58 dB | 0,999890 | 0,00062 | 0,0081 |
| bass | 28,67 dB | 0,999321 | 0,00122 | 0,0157 |

⭐ Va phep so QUAN TRONG hon ba cot tren: **ban nen thuc su di tiep** la
`drums+bass+other` (`stem_giu` cua `audio_prepare`). Tron ba stem roi do EBU R128:

```
CPU:  I = -17,1 LUFS · LRA 11,1 LU · Peak 1,3 dBFS
GPU:  I = -17,1 LUFS · LRA 11,1 LU · Peak 1,3 dBFS
```

Trung khit. Khong co dich chuyen do to nao di xuong ha nguon.

⚠️ `bass` 28,67 dB nam gan con so **27,1 dB** ma `demucs_runner.buoc_phan_doan`
goi la hong. Hai cai **khong cung loai**: 27,1 dB do la lech PHA he thong (luoi
phan doan khong ghim), con day la sai so nhan fp32 CPU↔CUDA tren stem **im nhat**
(RMS 0,033 — nho nhat trong bon), voi tuong quan 0,9993 va RMS chi lech 0,07%.
Phep do quyet dinh la ban nen o tren, va no bang nhau tung chu so.

### 2.2 Ngan sach VRAM — xau nhat dong thoi

| Nguoi dung card | Do that | Nguon |
|---|---|---|
| Nen (desktop/driver, may ranh) | 331–364 MiB | `nvidia-smi` truoc moi phep |
| **LTT VOICE** (VieNeu-TTS) | 641 MiB dinh | CLAUDE.md (da do) |
| `asv_gpu.audio_prepare` (demucs) | +1.083 MiB | lan nay |
| `asv_gpu.transcribe` (WhisperX) | **+6.334 MiB** | lan nay |
| `asv_gpu.qc_do_luong` | +4.265 (ASR) / +2.256 (SQUIM) | lan `giong`, 23/09 |

Ba giai doan GPU cua ASV dung **chung mot suat** `tach_nguon_cuc_bo`
(`pipeline.CHUOI`, `tai_nguyen_suat=1`) ⇒ **khong bao gio chay chong nhau**.

    Xau nhat hom nay  = 364 (nen) + 641 (Voice) + 6.334 (transcribe)
                      = 7.339 MiB / 16.311 MiB  →  con trong 8.972 MiB (55%)

Neu sau nay tach suat (xem §5): + demucs 1.083 = **8.422 MiB**, van con 7.889 MiB.
⇒ Khach cua LTT VOICE khong phai cho vi ban khai nao o day.

Ban khai sau khi sua: `audio_prepare` 2.200 (dinh 1.083 — du rong),
`transcribe` **7.600** (dinh 6.334 + 20%), `qc_do_luong` 5.200 (giu).

---

## 3. Loai 1 — CHO, khong TINH

### 3.1 Thoi gian chet giua cac luot job (~16–20 s/phim)

Ban ghi `nhat_ky_job` cua `NEN_V3` cho thay **21 job** cho mot lan chay, trong do
**11 job `auto_scan_video.advance`** moi cai ton 0,01–0,04 s viec that:

```
advance 0,02 · media_prepare 0,28 · advance 0,01 · audio_prepare 66,47 ·
advance 0,02 · transcribe 27,08 · advance 0,02 · edit_plan 163,78 · advance 0,01 ·
content_process 84,09 · advance 0,02 · voice_synthesis 942,65 · advance 0,03 ·
timing_align 10,96 · advance 0,02 · compose 0,43 · advance 0,02 · render 4,85 ·
advance 0,02 · qc 4,61 · advance 0,04
```

Trong bo nghiem thu cac luot noi nhau **tuc thi** (mot vong `for`, mot tien trinh).
O production thi khong: moi app khai `requires` khac nhau
(`asv_media`→`ffmpeg`, `asv_gpu`→`gpu`, `auto_scan_video`→`api`,
`asv_voice`→`voice`), `job_worker._doi_hinh` chia lan theo dung cac nang luc do, va
`job_runner.run_forever` ngu `POLL_INTERVAL_S = 2.0` khi lan cua no khong co viec.

⇒ Moi luot **doi lan** phai doi phan con lai cua giac ngu cua lan dich:
0–2 s, trung binh 1 s. Trong 20 luot chuyen, ~16 luot doi lan.

    thoi gian chet ~ 16 x 1 s = 16 s trung binh   (≤ 32–40 s xau nhat)

⚠️ **Day la so SUY RA tu hang so + ban do lan, khong phai so do dau-cuoi.** Do that
no doi mot doi hinh worker that dang chay; toi khong chay duoc no o day vi may nay
LA production. Cach do dung: bat `job_events`, lay hieu `finished_at` cua job truoc
va `started_at` cua job sau, tren 20 luot chuyen cua mot lan chay that.

**De xuat (khong tu lam — `platform_core/job_runner.py` la tep nen tang):**
1. Re nhat: ha `POLL_INTERVAL_S` 2,0 → 0,5 ⇒ chet trung binh 16 s → 4 s. Gia:
   4x so luot `jobs.claim` cua moi lan ranh. **Chua do gia do.**
2. Dung hon: PostgreSQL `LISTEN/NOTIFY` luc xep job ⇒ chet ~0. Thay doi lon hon.
3. Khong giai quyet duoc bang cach bo `advance`: no la cho dieu phoi, va day
   dieu phoi vao handler la doi mot loi kien truc lay mot giay.

### 3.2 `cho_tai_nguyen_s = 20 s` — luong tu cho qua tho

`asv_gpu/manifest.py` khai 20 s, bien minh bang *"hop ly cho viec dai hang phut"*.
Do that hom nay: `audio_prepare` **42 s**, `transcribe` **65 s** — khong phai
"hang phut", va 20 s la 31–48% do dai mot giai doan. Mot job co the bat dau 1 giay
sau khi suat trong lai nam cho du 20 giay.

**Tren MOT phim thi mat 0 giay** — ba giai doan GPU noi tiep nhau, suat luon trong.
Chi mat khi co ≥ 2 lan chay chong: ~10 s trung binh × 3 cua = ~30 s/phim.

⇒ **De xuat 5 s**, khong tu sua: loi ich tren chi so duoc giao (mot phim) bang 0,
va gia (tan suat `jobs.claim`) chua do. Dung luat cua kho: chua do thi chua doi.

### 3.3 Hai cho KHONG phai nut co chai (do roi, ghi lai de khoi ai do lai)

- **`cache_chung.giu_cho`** (`CHO_LAI_KHI_BAN_S = 15`): chi ban khi mot lan chay
  KHAC dang tinh cung `khoa_chung`. Mot phim, mot lan chay ⇒ **0 s**.
- **`platform_core/leases.py`** (`DEFAULT_TTL` 2 phut, `LEASE_RETRY_S` 20 s): chi
  phuc vu lease **bao tri** (`leases.MAINTENANCE`) trong `_vong_bao_tri`. Khong mot
  giai doan ASV nao cham vao no ⇒ **0 s**.
- Cac `time.sleep` con lai tren duong chay: `ket_xuat.py:480` va
  `asv_gpu/do_luong/venv.py:83`, ca hai 0,5 s cho tien trinh con ⇒ khong dang ke.

### 3.4 Cong cu chan doan cung la nut co chai

Hai cai gap trong chinh lan nay, ca hai deu lam "dang cho" trong giong "da chet":

1. `tools/nang_quyen.py` khoa dong stdout khi bi chuyen huong ⇒ log rong suot luot
   chay. **Da sua** (`PYTHONUNBUFFERED`, `e130e1d4`) va **da gop vao nhanh nay**.
2. `tools/cua_so_yen.py trang-thai` **nem `UnicodeEncodeError`** (cp1252) ngay sau
   khi in dong dau, khi mo ta lenh dang giu khoa co ky tu ngoai Latin-1. Nguoi doc
   thay mot `Traceback` ke ben thong tin minh can va de tuong cong cu hong.
   ⇒ Chua sua: `tools/` khong thuoc lan nay. Sua mot dong: dat
   `PYTHONIOENCODING=utf-8` hoac `errors="replace"` cho `stdout`.

⭐ Va bai hoc chung cua ca hai, dung nhu dieu phoi noi: **mot cong cu chan doan im
lang duoi tai chinh la mot nut co chai** — no khong lam cham may, no lam cham
nguoi dang tim cho cham.

---

## 4. Loai 2 — SAI THIET BI

### 4.1 `transcribe` — CTranslate2 khong phai torch

Gia thuyet trong brief: faster-whisper tut xuong CPU vi CTranslate2 thieu
CUDA/cuDNN. **Da kiem, va ket qua khac gia thuyet:**

```
venv worker (C:\LTTPlatform\venv):
  ctranslate2 4.8.1 · get_cuda_device_count() = 1   (ca khi KHONG import torch truoc)
  cublas64_12.dll   nap duoc  <- C:\LTTPlatform\venv\Lib\site-packages\torch\lib\
  cudnn64_9.dll     nap duoc  <- ctranslate2/ mang theo ban cua no
  WhisperModel("large-v3", device="cuda", compute_type="float16")  -> CHAY, 47 s
```

⇒ Tren venv worker, duong CUDA cua CTranslate2 **thoa man duoc**. Ghi chu o
`san_sang.py:98` (*"pha 24 do duoc rang duong tut xuong do hong tren may nay —
`cublas64_12.dll` khong nap duoc"*) **da cu**: luc do torch la ban `+cpu` va khong
co `torch/lib/cublas64_12.dll`; nay torch la `2.11.0+cu128` va no mang theo ca
cuBLAS lan cuDNN 9.

⚠️ Nhung su phu thuoc do la **ngam va mong manh**: CTranslate2 tim `cublas64_12.dll`
trong thu muc DLL ma **torch** dang ky. Nen tep nay nay `import torch` **truoc**
`faster_whisper` mot cach tuong minh, va `test_2150::test_torch_import_TRUOC_faster_whisper`
chot thu tu do bang AST. Dung bay ma `asv_gpu/do_luong/giong_runner.py` da ghi lai.

**Loi that o day khong phai thu vien thieu — la CHINH SACH:**

```python
device = os.environ.get("LTT_AUTOSUB_WHISPER_DEVICE", "cuda")  # "cuda" BAT KE co lease
...
except Exception:          # nuot MOI loi
    ... WhisperModel(model_name, device="cpu", compute_type="int8")
```

Hai hau qua, ca hai da sua:

1. **Lay card khi khong co lease** ⇒ tranh card voi LTT VOICE ma `gpu_lease` khong
   ghi so. Nay: card chi dung khi nen tang DA CAP (`gpu_uuid`) VA ghim duoc bang
   `device_index`. Ghim hoi **torch** theo UUID chu khong hoi
   `platform_core.gpu.by_uuid().index` — `index` cua `nvidia-smi` la so thu tu
   TOAN MAY, con `device_index` cua CTranslate2 la so thu tu trong tap card CUDA
   **nhin thay duoc**; hai so bang nhau khi tien trinh thay moi card va khac nhau
   khi khong. Duong nay chay TRONG worker nen khong ghim bang `CUDA_VISIBLE_DEVICES`
   duoc (`gpu.env_for` chi ghim duoc tien trinh CON).
2. **Lui ve CPU im lang** ⇒ 203 giay bay hoi ma bao cao van doc giong "chay GPU".
   Nay: moi lan lui deu `log.warning` VA tra `asr_device` / `asr_compute` /
   `asr_cpu_reason` ra hop dong ket qua.

⚠️ Duong nay la **duong LUI**: production co `LTT_WHISPERX_PYTHON` nen
`transcribe_file` di qua sidecar WhisperX (da tren GPU). 203 giay la so tiet kiem
**khi sidecar hong** — tuc no bien mot su co "cham 5 lan" thanh mot su co "cham
1,4 lan", va bien mot su co im lang thanh mot su co noi ra.

### 4.2 `audio_prepare` (demucs) — 29,8 s, va tran 4 luong GIU NGUYEN

GPU 42,15 s vs CPU 71,99 s ⇒ **−29,8 s (−41%)**, stem tuong duong (§2.1).

⛔ `LUONG_TORCH = 4` **khong doi**. `demucs_runner` da ghi ro tran nay an ca khi
chay CUDA (do 03/09: 413% CPU tren card), va no la nguyen nhan gan nhat cua mot lan
may chet. Mo no ra la mo lai dung cai lo do; phep do hom nay khong noi gi de bien
minh cho viec do.

Da sua kem: `chon_thiet_bi` hoi **lease truoc**, `is_available()` sau. Ban cu hoi
nguoc, nen mot lan goi khong lease van chiem ~1,1 GiB VRAM ngoai so sach.

🔴 Va cho nay khong lo ra suot 20 ngay vi mot ly do dang ghi lai:
`test_406::test_torch_o_may_nay_la_ban_CPU` **hoi nham trinh thong dich**. No
`assert not torch.cuda.is_available()` tren python chay test
(`…\Programs\Python\Python313`, `2.11.0+cpu`), trong khi demucs chay o venv worker
(`C:\LTTPlatform\venv`, `2.11.0+cu128`). Phep nhac xanh mai mai vi no tra loi mot
cau khac. Da thay bang phep kiem ghi lai dung bai hoc do.

### 4.3 OCR va VMAF — giu CPU, va day la ly do

- **OCR**: `L_OCR.md` §5 da do — GPU chi nhanh **1,6 lan** o pha ton thoi gian
  nhat, doi lai phai cai CUDA 13 va gianh card voi Voice/VLM. Phep do hom nay
  **cung co** quyet dinh do chu khong lat no: mot lan `transcribe` da an 6,3 GiB
  VRAM, va OCR chay CUNG LAN voi no se doi ngan sach card len. Khong dung.
- **VMAF**: ban ffmpeg dang dung **khong co** bo loc CUDA.

```
ffmpeg 8.0.1-full_build-www.gyan.dev
-filters   ->  libvmaf (VV->V)      ... KHONG co libvmaf_cuda
-h filter=libvmaf_cuda  ->  Unknown filter 'libvmaf_cuda'
-buildconf ->  --enable-libvmaf --enable-cuda-llvm --enable-ffnvcodec --enable-nvenc
              (khong co --enable-cuda-nvcc, khong co libvmaf ban CUDA)
```

  ⇒ Muon VMAF tren GPU thi phai **doi ban ffmpeg**, khong phai doi mot co. Va no
  cung khong dang: `qc` chi ton 4,6 s ca giai doan, va `VMAF_N_SUBSAMPLE = 5` da
  lam no re hon 3 lan roi.

---

## 5. Loai 3 — TUAN TU MA KHONG CAN

### 5.1 `content_process` — khong co gi de song song (do that)

Ban ghi `NEN_V3`: `content_process` `tom_tat: {"so_doan": 6, "so_lo": 1}`.
`long_tieng.DOAN_MOI_LO = 20` ⇒ 6 doan nam gon trong **MOT** lo ⇒ **MOT** loi goi
may B. 84–100 giay do la do tre cua mot luot goi, khong phai do xep hang.

⇒ Song song 2 luong o day tiet kiem **0 giay** tren phim nay. No chi bat dau co y
nghia tu ~21 doan tro len (2 lo). ❌ Khong lam.

### 5.2 `edit_plan` — 4 loi goi VLM doc canh, chay lan luot (~79 s)

Ban ghi: `{"so_canh": 6, "so_canh_da_doc": 4, "so_co_bang_chung": 4}`, 163,78 s.
`giai_doan_ban_bien_tap.py:250` la mot vong `for i, c in enumerate(canh)` va moi
vong goi `ai.goi_tinh_tien(... DOC_CANH ...)` **dong bo**.

May B cho `qwen38-api` **3 suat engine** (`ltt_llm.ngan_sach.HO_SO[...].np = 3`),
va tran van hanh chung cho tac tu la **≤ 2 request/model** (CLAUDE.md muc ⭐).
⇒ Hai luong la an toan theo ca hai ban khai.

    uoc tiet kiem = 163,8 s x (1 - 1/2) ≈ 79 s      (bo qua phan rut khung ffmpeg)

⛔ **De xuat, khong tu lam.** Ba vat can that, khong phai ngai ngung:
1. `lat_cat.kiem(vi_tri=i)` gia dinh tien do **theo thu tu**; hai luong lam
   `vi_tri` khong con don dieu, va diem chot se ghi lui.
2. `su_dung.mo_don_vi` / `danh_dau_xong` ghi so cai theo tung canh tren **cung mot
   `Session` cua SQLAlchemy** — doi tuong nay **khong an toan da luong**.
3. `ai.goi_tinh_tien` giu cua ngan sach + so cai; chay chong can mot phep do rang
   hai luong khong lam doi but toan.

⇒ Duong lam dung: giu vong `for` tuan tu cho phan GHI (chot, so cai), chi day
phan **goi mang** ra mot `ThreadPoolExecutor(max_workers=2)` + `Semaphore(2)`, roi
thu hoach theo dung thu tu canh. Can mot ADR ngan vi no cham so cai — chu du an
hoac lan `bien-tap` quyet.

### 5.3 `tach_nguon_cuc_bo` — tach suat thi duoc gi

`pipeline.py` da dat san phep do: *"chay `audio_prepare` va `transcribe` dong thoi
… neu dinh CPU < 70% va RAM trong > 8 GiB thi tach ten tai nguyen ra"*. Phep do do
**chua chay** (no doi demucs + whisper, khong phai demucs + demucs).

Phan VRAM thi hom nay da tra loi: 1.083 + 6.334 + 641 (Voice) + 364 (nen) =
**8.422 MiB / 16.311** — thua. Con thieu ve CPU/RAM.

⇒ Nhung **tren MOT phim van la 0 giay**: `TRANSCRIBE` khai `sau=(AUDIO_PREPARE,)`,
hai giai doan khong bao gio dong thoi trong cung mot lan chay. Tach suat la viec
cua **thong luong nhieu lan chay** (~1,3x theo do 03/09), khong phai cua do tre
mot phim. Ghi ra de khong ai nham hai thu nay voi nhau.

---

## 6. Da lam gi trong lan nay

| Tep | Doi gi |
|---|---|
| `apps/autosubvideo/transcription.py` | `_thiet_bi_asr` + `_chi_so_card`: chi dung card khi co lease va ghim duoc; `import torch` truoc `faster_whisper`; moi lan lui ve CPU deu ghi log va tra ly do (`asr_device`, `asr_compute`, `asr_cpu_reason`); `gpu_uuid` chay xuong duong lui |
| `apps/auto_scan_video/demucs_runner.py` | `chon_thiet_bi` hoi lease TRUOC `is_available()` — khong lease thi khong cham card |
| `apps/asv_gpu/manifest.py` | xoa ghi chu "torch la ban CPU-only" (dung cho venv test, sai cho venv worker); `transcribe` 6.000 → **7.600** MiB (do that 6.334); ghi bang do |
| `apps/autosubvideo/manifest.py` | `autosubvideo.transcribe` 6.000 → **7.600** MiB (cung engine, cung phep do) |
| `tests/test_406_asv_tach_tieng.py` | thay `test_torch_o_may_nay_la_ban_CPU` (hoi nham venv, xanh 20 ngay) bang phep kiem ghi lai bai hoc |
| `tests/test_439_asv_v4_am_thanh_tai_nguyen.py` | tach lam hai: co card VA duoc cap → `cuda`; co card ma KHONG duoc cap → `cpu` |
| `tests/test_2150_asv_toc_do_gpu.py` | **moi** — 13 phep kiem, khong cai nao nap model that |
| `tools/nang_quyen.py` | gop `e130e1d4` (PYTHONUNBUFFERED) |

## 7. Con lai — ai quyet

| Viec | Ai | Vi sao khong tu lam |
|---|---|---|
| Bo nghiem thu cap lease GPU (§1) | lan `nghiem-thu` | `test_448` la tep cua lan do |
| `edit_plan` song song 2 luong (§5.2) | ADR / lan `bien-tap` | cham so cai va diem chot |
| `POLL_INTERVAL_S` / LISTEN-NOTIFY (§3.1) | chu du an | tep nen tang, anh huong moi app |
| `cho_tai_nguyen_s` 20 → 5 (§3.2) | chu du an | loi ich tren mot phim = 0; gia chua do |
| Tach suat `tach_nguon_cuc_bo` (§5.3) | chu du an | con thieu phep do CPU/RAM khi demucs + whisper chay chong |
| `cua_so_yen.py` in duoc tieng Viet (§3.4) | lan `cong-cu` | `tools/` ngoai pham vi lan nay |

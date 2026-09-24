# GPU_MAY_A — card may A thay CPU: da dung gi, chuyen duoc gi

> May A: MOT RTX 5060 Ti 16 GiB / 20 loi. Phim PUBG 106,8 s. Moi luot qua
> `chay_nang.py`; `tai_may` ghi truoc tung luot (may RANH, CPU 4–35%). Bo do
> `tools/bench_gpu_may_a.py`, JSON tho `bang_chung/gpu_may_a/`. Nen:
> `L_TOC_DO_GPU.md`, `L_OCR.md` §5.

## 1. Kiem ke 12 giai doan

| Giai doan | Thu vien | Hien tai | Lease | Tep:dong |
|---|---|---|---|---|
| media_prepare | ffmpeg | CPU | — | `nhap_media.py` |
| audio_prepare | demucs (torch) | **GPU** | 2.200 | `demucs_runner.py:346` |
| transcribe | WhisperX sidecar / CT2 | **GPU** fp16 | 7.600 | `transcription.py:152,251` |
| edit_plan | PySceneDetect + ffmpeg khung + VLM **may B** | CPU cuc bo | — | `canh.py:131,297` |
| content_process | LLM **may B** | — | — | `giai_doan_noi_dung.py` |
| voice_synthesis | VieNeu-TTS :8120 | **GPU** (641 MiB) | — co y | `asv_voice/manifest.py:19` |
| timing_align | ffmpeg | CPU | — | `am_master.py:241` |
| compose | JSON | CPU | — | `giai_doan_ban_dung.py` |
| render | `h264_nvenc` / `libx264` | **GPU** khi co lease | 500 | `che_do_render.py:94`; `ket_xuat.py:104` |
| qc | ffmpeg blackdetect/freeze/libvmaf | CPU | — | `qc.py:77,284,372` |
| qc_do_luong | ASR + SQUIM + MetricX-24 (tien trinh con) | **GPU** ghim `CUDA_VISIBLE_DEVICES` | 5.200 | `venv.py:53`; `bo_do.py:95` |
| qc_ai | VLM **may B** | — | — | `giai_doan_qc_ai.py` |

Ngoai duong chay (`tools/do_gioi_giong*.py`): ECAPA **GPU** (`gioi_runner.py:77`),
Distill-MOS **GPU**, DNSMOS **CPU ghim cung** (`dnsmos.py:90`).

## 2. Ung vien: (a) chuyen duoc · (b) VRAM · (c) dang?

| Ung vien | (a) chuyen duoc? | (b) VRAM | (c) dang? |
|---|---|---|---|
| RapidOCR | can `onnxruntime-gpu`+CUDA 13+cuDNN 9; giay phep OK | chua do | **khong** — 1,6x, tranh card |
| CT2/faster-whisper | da chay | 5.221 | **co** — 5,3x |
| demucs | da chay | 1.083 | **co** — 1,7x |
| ffmpeg | `h264_cuvid`/`scale_cuda`/`nvenc` co, **`libvmaf_cuda` khong** | ≤ 162 | ma hoa lai **co**; giai ma/loc **khong** |
| PySceneDetect | khong co nhanh GPU | — | **khong** — 4,5 s |
| SQUIM / ECAPA | da chay | +774 / +315 | **co** — 2,4x / 2,5x |
| MetricX-24 | da chay | +2.602 | **khong dang** — 0,98x |
| TTS | da chay (CUDA graph) | 641 | **co**, xong |

## 3. Bang do — 3 luot moi ben

| Buoc | CPU (trung vi · dai) | GPU (trung vi · dai) | Tang toc | VRAM dinh (nen 1.298) | Khop? | KHUYEN NGHI |
|---|---|---|---|---|---|---|
| SQUIM 6x8 s | 9,38 · 0,08 | **3,87** · 0,17 | 2,4x | 2.072 | co (≤ 0,0001) | GPU |
| ECAPA 6x8 s | 13,58 · 0,57 | **5,33** · 6,23 | 2,5x | 1.613 | co (≤ 0,0002) | GPU |
| MetricX 6 cap | **10,31** · 0,18 | 10,49 · 0,14 | 0,98x | 3.900 | ⚠️ lech ≤ 0,031 (bf16↔fp32) | giu CPU |
| Ma hoa lai 107 s | 3,91 · 0,77 · VMAF **88,69** (min 80,5) · 21,58 MB | **1,59** · 0,02 · VMAF **90,60** (min 77,6) · 21,38 MB | 2,45x | 1.460 | khac diem anh; ca hai DAT 75 | GPU |
| PySceneDetect | **4,54** · 0,76 (22 moc) | khong co | — | — | — | giu CPU |
| Rut 36 khung | **3,22** · 0,16 | chua do | — | — | — | giu CPU |
| Giai ma ca tep | **0,65** · 0,08 | 0,59 · 0,06 | 1,1x | 1.461 | — | giu CPU |
| T13 black+freeze | **0,67** · 0,04 | **1,76** · 0,03 | 0,38x | — | ca hai rong ⚠️ phep so yeu | giu CPU |
| ffmpeg `scdet` | **0,67** · 0,07 (24 moc) | 1,83 · 0,06 | 0,37x | — | ⛔ 24 ≠ 22 | khong doi |

⭐ Moi: **`VMAF_TOI_THIEU=75` DAT tren nhanh `nvenc`** (90,60 · p5 83,63 · te nhat
77,60), hon `libx264` ve trung binh, **bang** kich thuoc; chi khung te nhat sat
nguong hon. Va **cham libvmaf ton 62 s** — 39 lan lan ma hoa — ma ban ffmpeg nay
khong co `libvmaf_cuda`.

⚠️ Lease luu SQLite cuc bo (`LTT_DATABASE_URL` trong `secrets\app.env`, ACL chan):
card van xin qua `gpu_lease.acquire` + `gpu_claims`, nhung khong thay lease
PostgreSQL. 🔴 Bay da vap: `CUDA_VISIBLE_DEVICES=""` bi Windows **xoa han** qua
`subprocess` ⇒ nhanh "CPU" dau bao `thiet_bi: cuda`. Phai dung `-1`. Bang tren
do lai sau khi sua, ca hai ben **nong**.

## 4. De xuat (⛔ chua sua ma)

1. **Cap lease GPU cho bo nghiem thu** (`test_448…:201`) — hom nay `gpu_cap: ""`
   nen `audio_prepare` chay CPU (+29,8 s) VA `render` lui `libx264` (+2,3 s).
   Rui ro 0. Bang chung moi: `tom_tat` cua `render` **khong ghi bo ma hoa**.
2. **Ghi bo ma hoa + VMAF vao `tom_tat`** (`giai_doan_ket_xuat.py`,
   `giai_doan_qc.py`). Rui ro 0.
3. **MetricX ve `thiet_bi="cpu"` khi lo nho** (`metricx.py:44`) — tra lai
   **2,6 GiB** VRAM, mat 0,2 s. Rui ro: diem lech ≤ 0,031 ⇒ phai bump
   `PHIEN_BAN` bo do. Can do o lo LON truoc khi chot nguong.
4. **Khong lam**: nvdec cho T13/`scdet`, OCR GPU, VMAF GPU, PySceneDetect.

**VRAM cong don** — ba giai doan GPU dung chung suat `tach_nguon_cuc_bo`, khong
chay chong. Xau nhat do duoc: nen 1.298 + Voice 641 + transcribe 6.334 =
**8.273 / 16.311 MiB**. Trong `qc_do_luong` dinh cao nhat van la ASR (+4.265) ⇒
khai 5.200 dung. Tach suat thi + demucs 1.083 = 9.356, van thua.

## 5. Buoc NEN GIU CPU, va vi sao

| Buoc | Vi sao |
|---|---|
| PySceneDetect | 4,54 s ca phim, khong co nhanh GPU. Bo tach ffmpeg co GPU cho **moc KHAC** (24 ≠ 22) va F1 thap hon (L_KY_THUAT §3) ⇒ doi ket qua, khong phai toi uu |
| Rut khung · giai ma · T13 · timing_align · compose · media_prepare | moi buoc 0,3–3,3 s; nvdec do duoc **cham 2,6x** o T13 (tai khung ve RAM cho bo loc CPU) |
| MetricX lo nho | GPU khong nhanh hon ma an 2,6 GiB cua card dung chung voi Voice |
| VMAF (T18) | 62 s, la nut thuc — nhung ffmpeg nay khong co `libvmaf_cuda` |
| OCR hardsub | 1,6x, doi lai CUDA 13 + tranh card; `nguon_loi.py:224` ghi `gpu_uuid=""` co chu y |
| DNSMOS | onnxruntime `qc-venv` la ban CPU, chay ngoai duong san pham |

⛔ Nguyen tac: **card chi thang khi buoc dai hon phi khoi dong CUDA**. Do that,
nguong o **3–4 giay**: duoi no CPU thang hoac bang (T13 0,67 · giai ma 0,65 ·
MetricX-cham 0,82); tren no card thang ro (SQUIM 9,4 · ECAPA 13,6 · demucs 72 ·
ASR 251).

# 00 — CURRENT TRUTH (Upscale Video V2)

> Lập 2026-09-26 · nhánh `claude/upscale-video-v2-correction-5fa61a` · gốc `dff24d4b`.
> **Nguồn chân lý: MÃ + RUNTIME.** `docs/UPSCALE_V2/*` chỉ là *lời khai* của phiên
> trước, không phải sự thật. Mỗi dòng dưới có `tệp:dòng`. Không có bằng chứng ⇒
> ghi thẳng `CHƯA ĐO`, không ngoại suy.

## Phần cứng thật (đo 2026-09-26)

| | |
|---|---|
| GPU | **1 ×** NVIDIA RTX 5060 Ti · 16311 MiB · driver 616.92 (`nvidia-smi`) |
| iGPU | Intel — **có** ⇒ buộc phải ghim Vulkan device |
| CPU | Intel 10700K (8C/16T) |
| Lúc đo | GPU **100 %** util, 4642 MiB đang dùng bởi phiên khác (`asv-b3`) |

⇒ Máy dùng chung **và là máy production**. Mọi phép đo hiệu năng phải qua khoá
`cpu_nhieu` và **phải ghi tải nền**, nếu không con số vô nghĩa.

## Bộ video test thật — 4 tệp, KHÔNG phải một ma trận

`C:\Users\Thang Tuong\Desktop\TEST VIDEO` (chỉ đọc, không sửa/xoá):

| tệp (rút gọn) | nguồn | fps | thời lượng | khung |
|---|---|---|---|---|
| 廉价的牛肠… | 1024×576 h264 yuv420p | 30/1 | 265,0 s | 7950 |
| 暴雨天野外露营… | 864×576 | 30/1 | 190,0 s | 5699 |
| 深度解析丨跳伞… | 836×576 | 30/1 | 106,8 s | 3205 |
| 真人气枪游戏… | 1024×576 | 2997/100 (29,97) | 275,0 s | 8242 |

Cả 4: h264 · yuv420p · audio aac 44,1 kHz stereo · **ngang** · **~576p** · **CFR**.

⛔ **Không có** nguồn dọc (portrait) · **không có** nguồn 1080/1440/2160 ·
**không có** VFR · **không có** clip mặt người riêng · **không có** clip nhiễu
nặng riêng. Ma trận truyền thông §20 của lời nhắc **không thể phủ bằng bộ này** —
những ô đó sẽ ghi `KHÔNG CÓ MẪU`. "1080/1440/2160" chỉ đo được ở phía **đích**
(`target_height`), vì ×4 từ 576p lên tới 2304p.

---

## ISSUE A — "4 → 12 concurrent" là SAI. Sự thật: **1**

**Đồng thời thật = 1 job GPU trên máy này**, độc lập hoàn toàn với `gpu_vram_mb`:

- `platform_core/models.py:1037` — `UniqueConstraint("host","gpu_uuid")` trên
  `GpuLease`: một GPU trên một máy tối đa **một** lease sống.
- `platform_core/gpu_lease.py:130-134` `busy_uuids()` + `:179`
  `ung_vien = [g for g in gpus if g.uuid not in taken and _con_cho(g)]` — GPU đã
  có lease bị **loại khỏi ứng viên**, không xét `need_mb`.
- `platform_core/job_runner.py:517-527` `_giu_gpu` → `gl.acquire(need_mb=…)`;
  không giành được ⇒ `het_gpu=True` ⇒ job xếp lại hàng.

⛔ SAI — `apps/upscalevideo/manifest.py:60` ghi: *"This enables 4→12 concurrent fast jobs, improves GPU utilization to ~90%"*.
Kiến trúc **không cho phép** điều đó.

⭐ **Nặng nhất: docstring của chính bảng đã cấm việc này trước khi nó xảy ra.**
`platform_core/models.py:1028-1031`:

> *"Quy ước v1: **một job một GPU**, không chia sẻ. Cố ý chọn vậy … kế toán VRAM
> theo hứa hẹn sẽ lệch so với thực tế rồi OOM. Muốn chia sẻ thì đổi UNIQUE thành
> kế toán tổng `vram_mb`, **nhưng đừng làm khi chưa đo được là cần**."*

Phiên trước hạ `gpu_vram_mb` rồi tuyên bố đồng thời tăng — đúng cái mà docstring
nói sẽ lệch. `UNIQUE` **không** bị đổi, nên **không có OOM**; chỉ có lời khai sai.

`gpu_vram_mb.fast` 2000→1000 đổi **đúng một** thứ: sàn nhận job trong `_con_cho`
(`gpu_lease.py:166` `free - reserved >= need_mb + HEADROOM_MB`), tức 3024 → 2024
MB trống cho **một** job đang xin. `HEADROOM_MB = 1024` (`gpu_lease.py:100`).
`gpu_claims.publish(..., exclusive=True)` (`gpu_lease.py:201-203`) vẫn công bố
độc quyền **bất kể** `mb` khai bao nhiêu.
⇒ **Không consumer nào cộng `gpu_vram_mb` để suy ra số job đồng thời.**

Lời khai sai nằm ở **9 chỗ**: `apps/upscalevideo/manifest.py:60` ·
`docs/UPSCALE_V2/01_HARDWARE_TRUTH.md:157` · `02_PIPELINE_MAP.md:591` ·
`04_BOTTLENECKS.md:103` · `05_GPU_OPTIMIZATION.md:53,130` ·
`08_ARCHITECTURE_V2.md:174,201,485` · `09_IMPLEMENTATION_PLAN.md:248` ·
`UPSCALE_BASELINE_REPORT.md:83`. Docs còn **tự mâu thuẫn**:
`08_ARCHITECTURE_V2.md:485` ghi *"Max 8 concurrent (not 12 theoretical)"*.

## ISSUE B — VRAM reservation: đổi sổ sách, không đổi throughput

Xem ISSUE A. Giảm reserve **không** mua được job thứ hai. Với `UNIQUE` còn đó,
con số `gpu_vram_mb` chỉ là **sàn nhận một job**. Không có lợi ích throughput nào
để thu; rủi ro OOM cũng ~nil vì `exclusive=True` vẫn giữ cả card.

## ISSUE C — ngưỡng autotune: chú thích nói dối chính hàm chứa nó

- Thật: `autotune.py:99` `est_alloc = 1000`, dùng ở `:103` `if budget < est_alloc`.
- `autotune.py:101` (cách mã **2 dòng**): *"VRAM budget threshold: 750 MB (not 1000)"*.
- `autotune.py:87` docstring: *"budget threshold 750 MB for full threads"*.
- `docs/UPSCALE_V2/05_GPU_OPTIMIZATION.md:98` đề nghị 800 MB — **chưa triển khai**.
- `autotune.py:120-121`: dải `budget >= 5000` nhưng khai `est = 5095` — **vượt sàn
  dải của chính nó 95 MB**.
- `autotune.py:95` chú thích *"large frames need larger tiles to avoid border
  artifacts"*, mã `:96-97` làm **ngược lại**:
  `tile = 256 if long_edge >= 1100 else 384`.
- `05_GPU_OPTIMIZATION.md:76-84` đưa bộ số tile/alloc thứ ba, **khớp không cái
  nào** trong mã (mã: 3513/5095/7025/9314/10024).

Giá trị **đang có hiệu lực** (tất cả hardcode trong `autotune.py`, lái bởi
`query_vram` sống — **không** phải manifest, **không** phải request):
Fast tile 256 (long_edge ≥ 1100) / 384, threads `4:4:4`, tụt về 200 + `2:2:2` khi
budget < 1000 (`:96-98,104`). Quality tile 512/448/384/320/256 theo dải budget,
threads luôn `1:2:2` (`:111-127`).

## ISSUE D/E/F — warmup không giữ được gì, và không ghim card

- `engine.py:75-76` warmup `subprocess.run(...)` — **chờ tiến trình con thoát hẳn**.
- `engine.py:115-117` job thật `subprocess.Popen(...)` — **tiến trình MỚI**.
  ⇒ Model **không thể** còn trong VRAM; OS/driver đã thu hồi context. Không IPC,
  không shared memory nối hai tiến trình.
- `engine.py:31` `_model_warmup_cache` — **chỉ ghi, không bao giờ đọc** (`:103`).
  Khoá `f"{model}_tile{tune.tile}_j{tune.threads}"` phụ thuộc autotune theo VRAM
  **sống** ⇒ đổi theo từng job ⇒ trên thực tế **gần như không bao giờ trúng**.
- `engine.py:28` `_model_cache = {}` — khai rồi **không đọc không ghi**: mã chết.
- ⭐ **Warmup KHÔNG ghim GPU.** `engine.py:72-76`: không `-g`, không `env=`.
  Job thật `engine.py:109-112`: có `-g <vulkan_index>` + `env=`
  (`jobs.py:31-54` → `vulkan_device.vulkan_index_for`). Máy **có iGPU Intel** ⇒
  warmup **có thể chạy sai card**. Đây đúng lớp sự cố `vulkan_device.py:9-19` ghi
  ngày 2026-09-11, và commit `7cde3c9d` đã phải sửa một lần
  (*"`-g` là chỉ số Vulkan, không phải chỉ số nvidia-smi"*).
- `engine.py:63,68` import `numpy` + `cv2` **chỉ** để tạo PNG xám 512×512 — hai
  import numpy/cv2 **duy nhất** trong cả app. `vulkan_device.py:83-97` đã tạo PNG
  tương đương bằng `struct`+`zlib` thuần ⇒ dependency **thừa**.
- `P3_WARMUP_REPORT.md` mô tả API (`model_exists()`, `_model_name`) **không khớp**
  mã hiện tại (`model_available()`, `tune.model`) ⇒ tài liệu tả một thiết kế chưa
  từng tồn tại.
- Test: **không** test nào chạm `_warmup_model`, khoá cache, hay việc ghim GPU.

## ISSUE G — checkpoint là GHI SỔ, không phải RESUME

- Ghi: `checkpoint.py:28-52` → `LTT_UPSCALE_TEMP|tmp/upscale/<job_id>/<stage>.json`.
  Gọi ở `jobs.py:226,323,341,396` — **bỏ kết quả**, fire-and-forget.
- ⭐ Đọc: `load_checkpoint` (`checkpoint.py:55`) và `get_job_checkpoints` (`:75`)
  **không có caller nào trong cả kho**. **Không một `if`** nào chặn stage theo
  checkpoint.
- Thứ duy nhất thật sự skip là `jobs.py:303` `if storage.exists(out_key)` — kiểm
  **đầu ra cuối trên R2**, tức idempotency **cả-job**, không liên quan
  `checkpoint.py`.
- Retry (`job_runner.py:786-800`) giữ **nguyên `job_id`** ⇒ checkpoint cũ **vẫn
  còn đó** nhưng vì không ai đọc, job **làm lại 100 %**: tải lại nguồn, probe lại,
  tách khung lại, upscale lại mọi batch. Tệp checkpoint cũ bị ghi đè âm thầm.
- **Không fingerprint** (params / model / preset / pipeline version) ⇒ dù có đọc
  cũng **không an toàn** để tái dùng.
- ⭐ Rác: `cleanup_job_checkpoints` (`checkpoint.py:94-101`) **không có caller**.
  Không TTL, không sweeper, không quota. Job xong / lỗi / sập đều để lại
  `tmp/upscale/<job_id>/*.json` **vĩnh viễn** (mỗi tệp vài trăm B–1 KB: rò rỉ
  chậm nhưng **không bao giờ thu hồi**).
- ⚠️ Hai gốc temp **khác nhau**: `jobs.py:280` dùng
  `tempfile.mkdtemp(prefix="ltt_upscale_")` (theo `%TEMP%` hệ thống) còn
  `checkpoint.py:24` dùng `LTT_UPSCALE_TEMP` mặc định `tmp/upscale` **tương đối
  theo CWD** ⇒ checkpoint không nằm cùng chỗ với dữ liệu nó mô tả.
- Lời khai sai: `checkpoint.py:2,4-5` *"stage-based resume … can resume from the
  last completed stage"* · `PROGRESS_REPORT.md:81` *"Resume logic: implemented in
  jobs.py"* · `13_FINAL_REPORT.md:63-64` cho điểm *"Resume/Recovery 9/10 — Full
  stage recovery"*. `P3_CHECKPOINT_PLAN.md:37-55` đặc tả `resume_if_partial(job_id)`
  — **chưa bao giờ được viết**; chỉ nửa `save_` được xây.
- Test: **không** test nào import `apps.upscalevideo.checkpoint`.

## ISSUE H — quality gate: 5 khuyết tật độc lập, chạy trên MỌI job khách

Chạy **vô điều kiện**, **không cờ**, mặc định **BẬT**: `jobs.py:411`
`run_quality_gates(out_key, preset)` tại progress 98.

1. `quality_gate.py:82-86` gọi **`ffprobe`** để lấy PSNR/SSIM/VMAF. ffprobe
   **không có filter graph** — PSNR/SSIM/VMAF là filter của **ffmpeg**
   (`-lavfi psnr|ssim|libvmaf`). Cú pháp `-show_frame stats_psnr:ssim:vmaf`
   cũng **không tồn tại**.
2. **Không có video tham chiếu**: `quality_gate.py:80`
   `video_key = test_video if test_video else output_key`, và `jobs.py:411`
   **không truyền** `test_video` ⇒ đo full-reference **với chính nó**.
3. `quality_gate.py:84-86` truyền **khoá R2** (`out_key`, `jobs.py:278`) vào
   `subprocess` như **đường dẫn tệp local**. Không materialize, không download.
4. `quality_gate.py:135,138` `image_data = f.read()` (**đọc toàn bộ MP4 vào RAM**)
   rồi `Image.open(image_data)` — PIL cần path/file-like, **bytes không có
   `.read()`** ⇒ `AttributeError`. Mà PIL **không giải mã được MP4** dù có sửa.
5. ⭐ `quality_gate.py:35-56` `_ffprobe`: `psnr/ssim/vmaf` **có thể chưa gán** khi
   `return psnr, ssim, vmaf` (`:52`) — và `except` (`:54`) chỉ bắt
   `TimeoutExpired, ValueError, IndexError`, **không bắt `UnboundLocalError`** ⇒
   lỗi tiềm ẩn thoát ra ngoài. Annotation `-> Tuple[float,float,float]` sai (trả
   `None`). `blur_score = min(variance,100)` rồi `if blur_score < 100`
   (`:148-152`) khiến điểm mờ **vô nghĩa** (chỉ đạt khi variance ≥ 100 đúng bằng cap).

**Hệ quả runtime mỗi job**: `check_quality` **luôn** trả
`error="ffprobe failed to parse quality metrics"`; `check_blur` **luôn** trả chuỗi
exception; ngưỡng `:100-113` là **mã chết**. Job **không đỏ**
(`jobs.py:415-420`, `raise` đã bị chú thích) nhưng:

- **mọi** job thành công mang `res["quality_warning"]` + `res["quality_log"]` báo
  kiểm chất lượng thất bại (`jobs.py:413,442`), trả về API/UI qua `routes.py:872`;
- mỗi job **đọc toàn bộ tệp đầu ra từ R2 vào RAM** rồi ném đi — tốn thời gian,
  RAM (4K ⇒ hàng trăm MB) và **egress R2 thật**.

⇒ **Không phải "vô hại".** Đây là **thuế trên mọi job khách + nhiễu lời khai**.

- Test: **không có**. `P4_QUALITY_PLAN.md:44` khai `tests/test_quality_gate.py` —
  tệp **không tồn tại**. `tests/test_4900_tcn_quality_gate.py` là app khác
  (`taoclipngan`).

## ISSUE I/J — encoder: hai chỗ rơi âm thầm, và HEVC trả H.264 mà vẫn khai HEVC

Producer `jobs.py:143-161` `_resolve_encoder(codec)` dựa trên
`platform_core/media.py:213-227` `detect_gpu_encoder()`, hàm này **chỉ dò 3 tên
H.264** (`media.py:220`: `h264_nvenc, h264_qsv, h264_amf`) — **không bao giờ dò
`hevc_*`**, tức giả định năng lực HEVC = năng lực H.264 (chưa kiểm chứng).

| producer trả | consumer `ff.py:196-203` | `-c:v` **thật** |
|---|---|---|
| `h264_nvenc` | nhánh nvenc | `h264_nvenc` |
| `hevc_nvenc` | nhánh nvenc + `-tag:v hvc1` | `hevc_nvenc` |
| `h264_qsv` / `hevc_qsv` | **rơi xuống `else`** (`:202-203`) | **`libx264`** |
| `h264_amf` / `hevc_amf` | **rơi xuống `else`** | **`libx264`** |
| `"libx264"` (`jobs.py:162` — **bỏ luôn `codec`**) | `else` | `libx264` |

- ⭐ **HEVC bug**: rơi CPU ⇒ mã hoá `libx264` (`ff.py:203`) nhưng `jobs.py:427`
  ghi `"codec": codec.value` — **enum người dùng YÊU CẦU**, không phải codec thật.
  `"encoder": encoder` ngay cạnh giữ giá trị thật (`libx264`).
  ⇒ API/UI nhận `{"codec":"hevc","encoder":"libx264"}`. **Trường `codec` nói dối.**
- `libx265` **không xuất hiện một lần nào** trong `apps/upscalevideo/` ⇒ HEVC trên
  CPU **không hề được thử**; CPU luôn nghĩa là H.264.
- Máy này (`ffmpeg -encoders`): có đủ `h264_nvenc, hevc_nvenc, h264_qsv, hevc_qsv,
  h264_amf, hevc_amf, libx264, libx265`. NVENC h264 dò thấy **trước** ⇒ **hôm nay**
  cả hai codec đều tới NVENC và bug **đang ngủ**. Nó **thức** khi NVENC vắng
  (driver lỗi, host chỉ có iGPU) — tức đúng lúc đang có sự cố khác.
- API khai `codec: enum[h264,hevc]` (`manifest.py:74,148-152`) **không một cảnh
  báo** rằng fallback đổi codec.
- Test: `test_82_upscalevideo.py:121-122` chỉ kiểm `"zz"`→`"h264"` lúc phân tích
  tham số; `test_171_upscale_h32.py:48-54` chỉ dùng codec cho **bảng giá**.
  **Không test nào** chạm `_resolve_encoder` / `_venc_args` / codec đầu ra.

## ISSUE K — smooth motion vẫn là `minterpolate` (CPU), RIFE chỉ là chú thích

- `ff.py:141-143`:
  `minterpolate=fps={interpolate_fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1`
  — **CPU**, nhập luôn vào cùng lệnh ffmpeg tách khung (`ff.py:122-151`).
- RIFE chỉ tồn tại dưới dạng: `ff.py:127` docstring *"RIFE interpolation… requires
  rife-ncnn-vulkan.exe"* · `ff.py:138-140` `# TODO: When rife-ncnn-vulkan.exe is
  bundled…` + `# filters.append("rife=0")` (mã chết).
- **Không** binary, **không** vendor reference, **không** lớp trừu tượng.

## ISSUE L — rò rỉ khi job bị hết giờ (MỚI, không nằm trong danh sách A–L)

⭐ `platform_core/job_runner.py:641-672` `_het_gio`: khi vượt `RUNTIME_LIMIT_S`
(2 h cho làn gpu/ffmpeg, `job_runner.py:114`), nó **giết cả worker** bằng
`os._exit(3)`.

`os._exit` **bỏ qua** `finally` ⇒ `jobs.py:444` `shutil.rmtree(tmp)` **không chạy**.
Không có `atexit`, không Job Object (đã grep, không có). Hệ quả trên Windows:

- thư mục temp khung/segment (**cỡ GB**) **còn lại**;
- tiến trình con `realesrgan-ncnn-vulkan.exe` / `ffmpeg.exe` (`engine.py:115`,
  `ff.py:41`) **thành mồ côi** — và tiến trình mồ côi giữ GPU.

Huỷ **hợp tác** (`cancel_check`) thì ổn: `engine.py:118-141` và `ff.py:36-58` đều
poll rồi kill+wait; `job_runner.py:745-800` xét lại trạng thái DB nên
`ff.ProcessingCancelled` được coi là huỷ, không phải lỗi. **Chỉ đường hết-giờ-cứng
rò rỉ.**

## ISSUE M — không hề xác minh nội dung đầu ra (MỚI)

Thành công chỉ dựa `os.path.isfile(out_path)` (`ff.py:220,235,260`) sau exit code
của ffmpeg — **không** kiểm kích thước, thời lượng, số khung, độ phân giải so với
nguồn. Cộng với ISSUE H (cổng chất lượng vô dụng): một đầu ra **hỏng mà khác rỗng**
vẫn báo `SUCCEEDED`.

## PNG I/O — sự thật, chưa phải bottleneck đã đo

- Khung là PNG `f%05d.png` (`ff.py:146`), **không** đặt `-compression_level` ⇒
  mặc định ffmpeg.
- Tách khung **KHÔNG chunk**: cả video ra một lượt (`ff.py:122-151`).
- Chỉ **tầng upscale** chunk, `_BATCH_SIZE = 360` khung (`jobs.py:27,177-235`), cố
  ý để chặn đỉnh đĩa của PNG đã ×4 diện tích; `_guard_disk` (`jobs.py:130-140`).
- Với 265 s @30 fps ≈ 7950 PNG nguồn **cùng tồn tại** với ≤ 360 PNG đã upscale mỗi
  batch. `smooth_motion` nhân số khung nguồn lên.
- **CHƯA ĐO** tỉ lệ thời gian I/O so với tầng SR. Không tối ưu trước khi đo (§22).

## Bảng phán quyết

| Issue | Lời khai | Sự thật | Mức |
|---|---|---|---|
| A concurrency | 4→12 đồng thời | **1** (UNIQUE lease) | lời khai sai, 9 chỗ |
| B VRAM reserve | giảm ⇒ throughput | chỉ đổi sàn nhận 1 job | tối ưu ảo |
| C autotune | 750 MB | **1000 MB**; 3 chú thích lệch + 1 dải tự vượt | drift |
| D warmup | giữ model nóng | tiến trình thoát; cache chỉ-ghi; 1 dict chết | tính năng giả |
| E warmup GPU | — | **không ghim card**, máy có iGPU | **rủi ro thật** |
| F numpy/cv2 | — | thừa; đã có cách stdlib thuần | rác dep |
| G checkpoint | resume | ghi sổ; 0 caller đọc; rác vĩnh viễn | tính năng giả |
| H quality gate | PSNR/SSIM/VMAF | 5 khuyết tật; luôn fail; thuế mỗi job | **hỏng + tốn** |
| I encoder | hỗ trợ QSV/AMF | rơi âm thầm về libx264 | hợp đồng sai |
| J HEVC | trả HEVC | trả **H.264** mà **khai HEVC** | **bug ngữ nghĩa** |
| K smooth motion | (RIFE trong chú thích) | `minterpolate` CPU | lời khai mờ |
| L hết giờ cứng | — | `os._exit` bỏ `finally` ⇒ rò GB + mồ côi | **rò rỉ thật** |
| M xác minh ra | — | chỉ `isfile()` | lưới an toàn vắng |

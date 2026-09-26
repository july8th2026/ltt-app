# 06 — BASELINE (SAU bản cập nhật hỏng) — mọi ô `CHƯA ĐO`

> Lập 2026-09-26 09:31 UTC (16:31 giờ máy, UTC+7) · nhánh
> `claude/upscale-video-v2-correction-5fa61a` · gốc `dff24d4b`.
> Nguồn chân lý phần cứng/ISSUE: `docs/UPSCALE_V2_CORRECTION/00_CURRENT_TRUTH.md`.
> Bộ đo: `tools/bench_upscale.py` (`--dry-run` đã chạy và dán ở cuối tệp này).

🔴 **Không một số hiệu năng nào trong tệp này là thật.** Mọi ô ghi `CHƯA ĐO` vì
lý do DUY NHẤT: **GPU vật lý duy nhất của máy đang chạy một video KHÁCH THẬT**
qua `D:\BOT GEMINI` lúc lập tài liệu này (xem mục 2). Đo hiệu năng trên một GPU
tranh chấp cho ra số **vô nghĩa và nguy hiểm** (số méo được dùng để ra quyết
định) — nên bài tập ở đây là **đo cái gì đo được (metadata)** và **khoanh
đúng cái gì CHƯA đo được**, không phải bịa một con số.

## 1. Phần cứng — không đổi so với `00_CURRENT_TRUTH.md`

| | |
|---|---|
| GPU | 1× NVIDIA GeForce RTX 5060 Ti · 16311 MiB · driver 616.92 |
| CPU | Intel 10700K (8C/16T) |
| iGPU | Intel — có, buộc ghim Vulkan device (`vulkan_device.py`) |

## 2. Tải nền ĐO ĐƯỢC lúc lập tài liệu (2026-09-26 09:31 UTC, `nvidia-smi`)

| Trường | Giá trị |
|---|---|
| `utilization.gpu` | **100 %** |
| `memory.used` | 4 980 MiB |
| `memory.free` | 11 071 MiB |
| `temperature.gpu` | 71 °C |
| Tiến trình compute lạ | `D:\BOT GEMINI\vendor\upscale\engine\realesrgan-ncnn-vulkan.exe` (PID đổi mỗi lần đọc — tiến trình khách thật, đang chạy) |

⇒ `tools/bench_upscale.py --dry-run` (mục 7 của nó) tự đọc đúng snapshot này
và tự in `BAN — KHONG duoc do that luc nay`. Bộ đo có **fairness guard** chặn
đo trên GPU tranh chấp — không dựa vào người vận hành nhớ kiểm tay.

## 3. Provenance engine/model (SHA256 đo thật, đọc-only)

Đọc từ `C:\LTTPlatform\app\apps\upscalevideo\vendor\engine\` (bản production
đang cài) — worktree này KHÔNG có `vendor/engine` (bị `.gitignore`, xem
`apps/upscalevideo/engine.py` dòng đầu). SHA256 của bản `D:\BOT GEMINI\vendor\
upscale\engine\realesrgan-ncnn-vulkan.exe` (đang chạy job khách) đã đối chiếu
**khớp tuyệt đối** với bản `C:\LTTPlatform` — cùng một binary.

| Tệp | SHA256 |
|---|---|
| `realesrgan-ncnn-vulkan.exe` (cả 2 bản cài) | `07e49f7cbb4ede01ae4dd4c399d3a7e5846e3d2085c3128eff881e55cb7b1a0c` |
| `realesr-general-x4v3.param` (Fast) | `33950f36822fd37786502db9bd6a3638f677c13b23814c8e5a6e8fd9bcea2163` |
| `realesr-general-x4v3.bin` (Fast) | `bfdfaebf0b26be9442faa30b8cec617fe04a808ae2aa3616ece85b92d81ae0ce` |
| `realesrgan-x4plus.param` (Quality) | `35330ececcea33b6c397a72548e788d5d53becee4734c50b7fada36e89f10a86` |
| `realesrgan-x4plus.bin` (Quality) | `713ee713b0353afaa27976f0563a64a5043bd70b9bd8936c2e26e25ebcdbcddf` |

ffmpeg: `ffmpeg version 8.0.1-full_build-www.gyan.dev` (winget `Gyan.FFmpeg`),
`libavcodec 62.11.100`. Có đủ `h264_nvenc, hevc_nvenc, h264_qsv, hevc_qsv,
h264_amf, hevc_amf, libx264, libx265` (đối chiếu ISSUE I/J của `00_CURRENT_TRUTH.md`).

## 4. 4 input thật — đặc trưng bằng `ffprobe` (đọc trực tiếp, không suy diễn)

| id | tên tệp (rút gọn) | kích thước | fps | thời lượng | khung | audio | codec | bitrate |
|---|---|---|---|---|---|---|---|---|
| v1 | 廉价的牛肠… | 1024×576 | 30/1 (CFR) | 265,0 s | 7950 | AAC 44,1kHz stereo, 128 kbps | h264 High yuv420p | ~2,38 Mbps |
| v2 | 暴雨天野外露营… | 864×576 | 30/1 (CFR) | 190,0 s | 5699 | AAC HE-AACv2 44,1kHz stereo | h264 High yuv420p | ~1,05 Mbps |
| v3 | 深度解析丨跳伞… | 836×576 | 30/1 (CFR) | 106,8 s | 3205 | AAC 44,1kHz stereo, 128 kbps | h264 High yuv420p | ~1,51 Mbps |
| v4 | 真人气枪游戏… | 1024×576 | 2997/100 = 29,97 (CFR) | 275,0 s | 8242 | AAC 44,1kHz stereo, 128 kbps | h264 High yuv420p | ~2,56 Mbps |

Cả 4: `is_vfr=False` (r_frame_rate == avg_frame_rate — CFR thật), ngang
(16:9 / 3:2 / 209:144), ~576p, `yuv420p`, `mov,mp4` container, không rotation.
Đường dẫn thật: `C:\Users\Thang Tuong\Desktop\TEST VIDEO\*.mp4` (chỉ đọc —
`tools/bench_upscale.py` không bao giờ ghi vào thư mục này).

## 5. `KHÔNG CÓ MẪU` — liệt kê tường minh để không ai nhầm "vắng" thành "đã qua"

Ma trận truyền thông của mandate (§20) đòi hỏi các trục sau; bộ 4 video test
hiện có **không phủ được** các ô này — chúng sẽ **mãi mãi** là `KHÔNG CÓ MẪU`
cho tới khi có sample mới, không phải một điều `tools/bench_upscale.py` có thể
tự sửa:

| Trục thiếu mẫu | Lý do |
|---|---|
| Portrait (dọc) | cả 4 video đều NGANG (16:9/3:2/209:144) |
| Nguồn 1080p/1440p/2160p | cả 4 đều ~576p — chỉ đo được ở phía **TARGET** (`target_height`), không đo được ở phía **SOURCE** |
| VFR (variable frame rate) | cả 4 đều CFR thật (`r_frame_rate == avg_frame_rate`, chênh lệch 0%) |
| Clip mặt người riêng (face-heavy) | không clip nào trong bộ 4 tập trung mặt người làm nội dung chính (ẩm thực, cắm trại, gameplay bắn súng, gameplay dù lượn) |
| Clip nhiễu hạt/thiếu sáng riêng (noisy/low-light) | không có clip quay đêm/ISO cao riêng trong bộ 4 |

⇒ Bảng kết quả mục 6 chỉ biến thiên đúng MỘT trục media thật sự đo được:
`target_height {1080,1440,2160}`, nhân với `preset {fast,quality}` và
`feature {normal,stabilize,smooth_motion,preview}` của chính app.

## 6. Bảng kết quả — ma trận `preset × feature × video`, mọi ô `CHƯA ĐO`¹

¹ Lý do DUY NHẤT cho toàn bộ bảng: **GPU đang bận bởi job khách thật** (mục 2)
— `tools/bench_upscale.py`'s fairness guard từ chối đo trên GPU tranh chấp.
Không một ô nào trong bảng này được suy luận, ước lượng hay copy từ nguồn
khác; tất cả đợi lượt chạy thật đầu tiên khi GPU rảnh (xem
`08_BENCHMARK_RESULTS.md` — đó là bộ khung JSONL→Markdown mà lượt chạy thật
sẽ điền vào).

| Preset | Feature | Video | 1080p | 1440p | 2160p |
|---|---|---|---|---|---|
| fast | normal | v1 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| fast | normal | v2 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| fast | normal | v3 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| fast | normal | v4 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| fast | stabilize | v1 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| fast | stabilize | v2 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| fast | stabilize | v3 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| fast | stabilize | v4 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| fast | smooth_motion | v1 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| fast | smooth_motion | v2 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| fast | smooth_motion | v3 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| fast | smooth_motion | v4 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| fast | preview | v1 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| fast | preview | v2 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| fast | preview | v3 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| fast | preview | v4 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| quality | normal | v1 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| quality | normal | v2 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| quality | normal | v3 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| quality | normal | v4 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| quality | stabilize | v1 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| quality | stabilize | v2 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| quality | stabilize | v3 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| quality | stabilize | v4 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| quality | smooth_motion | v1 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| quality | smooth_motion | v2 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| quality | smooth_motion | v3 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| quality | smooth_motion | v4 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| quality | preview | v1 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| quality | preview | v2 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| quality | preview | v3 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| quality | preview | v4 | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |

96 ô (2 preset × 4 feature × 4 video × 3 target). Lệnh chạy thật cho MỘT ô,
khi GPU rảnh (qua khoá lệnh nặng — xem `tools/bench_upscale.py --help` mục
"Giao thức lệnh nặng"):

```
python "C:\Users\Thang Tuong\.claude\ltt\chay_nang.py" --phien bench-upscale -- ^
  python tools\bench_upscale.py --mode matrix --preset fast --target 1080 ^
  --feature normal --video v1 --repeat 3
```

Chạy CẢ 96 ô một lượt (không lọc `--preset/--target/--feature/--video`):

```
python "C:\Users\Thang Tuong\.claude\ltt\chay_nang.py" --phien bench-upscale -- ^
  python tools\bench_upscale.py --mode matrix --repeat 3
```

⚠️ Với `v1/v4` (~265-275 s @ 30fps, 7950-8242 khung) và `v4` (~275 s), pha
`smooth_motion` NHÂN ĐÔI số khung nguồn (nội suy 2×) trước khi upscale — đây
là ô NẶNG nhất ma trận và nên chạy riêng, không gộp `--repeat 3` cho `quality`
+ `smooth_motion` + `2160p` trong lần đầu (chưa biết thời lượng — `CHƯA ĐO`).

## 7. Output `--dry-run` đã chạy thật (dán nguyên văn, không sửa)

```
==============================================================================
bench_upscale.py --dry-run — KHONG chay GPU, KHONG goi engine that.
==============================================================================

[1] Provenance (doc that, chi doc):
    timestamp_utc: 2026-09-26T09:30:20.452567+00:00
    git_head: dff24d4bfed093d50f22ad68b94e9c92223307a0
    engine_dir: C:\LTTPlatform\app\apps\upscalevideo\vendor\engine
    engine_dir_la_that_trong_worktree_nay: False
    engine_sha256: 07e49f7cbb4ede01ae4dd4c399d3a7e5846e3d2085c3128eff881e55cb7b1a0c
    ffmpeg_version: ffmpeg version 8.0.1-full_build-www.gyan.dev ...
    model_fast_ten: realesr-general-x4v3
    model_fast_param_sha256: 33950f36822fd37786502db9bd6a3638f677c13b23814c8e5a6e8fd9bcea2163
    model_fast_bin_sha256: bfdfaebf0b26be9442faa30b8cec617fe04a808ae2aa3616ece85b92d81ae0ce
    model_quality_ten: realesrgan-x4plus
    model_quality_param_sha256: 35330ececcea33b6c397a72548e788d5d53becee4734c50b7fada36e89f10a86
    model_quality_bin_sha256: 713ee713b0353afaa27976f0563a64a5043bd70b9bd8936c2e26e25ebcdbcddf
    background_load_at_provenance: {gpu util 100%, vram 4973/16311 MiB, temp 71C,
      tien_trinh_compute goi ca realesrgan-ncnn-vulkan.exe cua D:\BOT GEMINI}

[2] 4 video test that (ffprobe truc tiep, chi doc):
    v1: 1024x576 30/1 265.0s 7950 khung audio=True vfr=False
    v2: 864x576 30/1 190.0s 5699 khung audio=True vfr=False
    v3: 836x576 30/1 106.8s 3205 khung audio=True vfr=False
    v4: 1024x576 2997/100 275.0s 8242 khung audio=True vfr=False

[3] Muc ma tran KHONG CO MAU: portrait, nguon 1080p+, VFR, face-heavy, noisy
    (chi tiet trong than tai lieu nay, muc 5)

[4] Ma tran (mode=matrix) — 96 o, --repeat 1 (liet ke day du trong bo do)

[5] Lenh 'demo' o dau tien (khong chay):
    engine: ...\realesrgan-ncnn-vulkan.exe -i <in_dir> -o <out_dir>
      -n realesr-general-x4v3 -s 4 -m models -f png -t 384 -j 4:4:4 -g <gpu_index>
    extract: ...\ffmpeg.EXE -y -i <src.mp4> <out_dir>\f%05d.png

[6] Giao thuc lenh nang: chay_nang.py --phien bench-upscale -- ... (xem tools/bench_upscale.py --help)

[7] Tinh trang GPU ngay bay gio: gpu_util_pct=99-100%%, tien_trinh_tranh_gpu=
    ['... D:\BOT GEMINI\vendor\upscale\engine\realesrgan-ncnn-vulkan.exe ...']
    => BAN — KHONG duoc do that luc nay

[8] Thoi gian tuong uoc luong: CHUA_DO (khong bia so).

[9] Cai bo do KHONG the do duoc: xem `08_BENCHMARK_RESULTS.md` muc cuoi.
```

(Bản đầy đủ, không rút gọn: chạy lại `python tools\bench_upscale.py --dry-run`
— output xác định (deterministic) ngoại trừ timestamp/PID/tải GPU tức thời.)

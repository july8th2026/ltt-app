# 08 — BENCHMARK RESULTS — bộ khung rỗng, mọi ô `CHƯA ĐO`

> Lập 2026-09-26 · nhánh `claude/upscale-video-v2-correction-5fa61a`.
> Bộ đo: `tools/bench_upscale.py`. Đặc trưng input + hardware + provenance +
> ma trận `preset×feature×video×target`: `06_BASELINE_AFTER_BAD_UPDATE.md`.
> Tệp này là bộ khung **CÁC PHÉP ĐO CHUYÊN SÂU** (warmup on/off, tile sweep,
> thread sweep) mà `tools/bench_upscale.py` sẽ ĐIỀN vào khi GPU rảnh — mỗi
> lần chạy thật, dán lại output `--report` vào đúng bảng tương ứng bên dưới
> (không sửa tay các con số — luôn dán nguyên từ `--report`).

🔴 GPU duy nhất của máy đang bận (job khách thật qua `D:\BOT GEMINI`, xem
`06_BASELINE_AFTER_BAD_UPDATE.md` mục 2) lúc lập tài liệu này. **Không một số
nào dưới đây được đo, ước lượng hay bịa** — mọi ô ghi `CHƯA ĐO`.

## Cách điền bảng khi GPU rảnh

```
# 1) Kiem GPU ranh (bo do tu lam, nhung xem truoc cho chac):
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv

# 2) Chay MOT thi nghiem qua khoa lenh nang (vi du warmup):
python "C:\Users\Thang Tuong\.claude\ltt\chay_nang.py" --phien bench-upscale -- ^
  python tools\bench_upscale.py --mode warmup --preset fast --video v3 --repeat 5

# 3) NGOAI khoa (sau khi tien trinh tren da thoat va khoa da nha): render bang
python tools\bench_upscale.py --report %TEMP%\ltt_bench_upscale\results.jsonl
```

Dán nguyên output `--report` (bảng Markdown) vào đúng mục bên dưới, thay
`CHƯA ĐO`. Không trộn kết quả của các lần chạy khác GPU/driver/engine SHA256
khác nhau vào cùng một bảng — mỗi bảng phải đồng nhất provenance (xem JSONL
`provenance.engine_sha256` / `driver_version`).

---

## A. Warmup ON vs OFF — phép đo CHỐT

⭐ Câu hỏi: `engine._warmup_model` (`engine.py:55-89`) chạy một `subprocess.run`
CHỜ THOÁT HẲN trước khi job thật spawn một `Popen` MỚI (`engine.py:127-129`) —
tức warmup **không thể** giữ model trong VRAM. Bảng này đo xem nó có mua được
GÌ khác không (cache tệp OS / shader cache driver) qua time-to-first-frame và
tổng thời gian, on vs off, nhiều lần lặp.

Lệnh (đổi `--preset` cho cả 2 preset):

```
python "C:\Users\Thang Tuong\.claude\ltt\chay_nang.py" --phien bench-upscale -- ^
  python tools\bench_upscale.py --mode warmup --preset fast --video v3 --repeat 5
python "C:\Users\Thang Tuong\.claude\ltt\chay_nang.py" --phien bench-upscale -- ^
  python tools\bench_upscale.py --mode warmup --preset quality --video v3 --repeat 5
```

| Preset | Warmup | N | time_to_first_frame_s (median) | min | max | total_s (median) | min | max | CPU-giây (median) |
|---|---|---|---|---|---|---|---|---|---|
| fast | on | — | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| fast | off | — | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| quality | on | — | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| quality | off | — | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |

**Kết luận (điền SAU khi có đủ 4 dòng trên, không trước):** CHƯA ĐO.
⚠️ Nếu `on` và `off` không khác nhau quá sai số lặp (`max-min` của từng
trạng thái), đó là bằng chứng ISSUE D (`00_CURRENT_TRUTH.md`) đúng như dự
đoán — ghi rõ độ lệch quan sát được, không chỉ "giống nhau".

---

## B. Tile sweep — tách riêng tầng upscale

Fast: tile ∈ {200, 256, 384}. Quality: tile ∈ {256, 320, 384, 448, 512}.
Threads cố định theo mặc định autotune của từng preset (Fast `4:4:4`, Quality
`1:2:2`) — chỉ `tile` biến thiên. Dùng `--max-frames` để sweep nhanh (khung đã
tách được TÁI SỬ DỤNG giữa các tile, không tách lại mỗi lần).

```
python "C:\Users\Thang Tuong\.claude\ltt\chay_nang.py" --phien bench-upscale -- ^
  python tools\bench_upscale.py --mode tile-sweep --preset fast --video v3 --max-frames 200 --repeat 3
python "C:\Users\Thang Tuong\.claude\ltt\chay_nang.py" --phien bench-upscale -- ^
  python tools\bench_upscale.py --mode tile-sweep --preset quality --video v3 --max-frames 200 --repeat 3
```

### Fast (threads `4:4:4`, video v3, `--max-frames 200`)

| Tile | N | total_s (median) | min | max | time_to_first_frame_s (median) | VRAM đỉnh (MiB) | GPU util % (avg) | CPU-giây (median) |
|---|---|---|---|---|---|---|---|---|
| 200 | — | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| 256 | — | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| 384 | — | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |

### Quality (threads `1:2:2`, video v3, `--max-frames 200`)

| Tile | N | total_s (median) | min | max | time_to_first_frame_s (median) | VRAM đỉnh (MiB) | GPU util % (avg) | CPU-giây (median) |
|---|---|---|---|---|---|---|---|---|
| 256 | — | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| 320 | — | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| 384 | — | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| 448 | — | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| 512 | — | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |

⚠️ Đối chiếu `autotune.py` (ISSUE C, `00_CURRENT_TRUTH.md`): Quality tile 512
chỉ được autotune CHỌN khi `budget >= FAST_ALLOC(10024) + SAFETY(500)` MiB —
tức máy gần như rảnh hoàn toàn. Sweep này ép tile thủ công (bỏ qua
`autotune.pick`) nên có thể tạo ra tổ hợp autotune THẬT SẼ KHÔNG BAO GIỜ chọn
(vd tile 512 khi VRAM hẹp) — đây là CHỦ Ý (đo giới hạn kỹ thuật của tile, không
phải mô phỏng autotune), ghi rõ khi diễn giải kết quả.

---

## C. Thread sweep — tách riêng tầng upscale

`threads ∈ {"1:2:2", "2:2:2", "4:4:4"}` (cú pháp NCNN `load:proc:save`), tile
cố định (chọn tile mặc định của autotune cho preset đang test ở VRAM lúc đo —
ghi lại giá trị `--tile` dùng thật vào cột đầu bảng, vì nó phụ thuộc VRAM rảnh
tại thời điểm chạy).

```
python "C:\Users\Thang Tuong\.claude\ltt\chay_nang.py" --phien bench-upscale -- ^
  python tools\bench_upscale.py --mode thread-sweep --preset fast --tile 384 --video v3 --max-frames 200 --repeat 3
python "C:\Users\Thang Tuong\.claude\ltt\chay_nang.py" --phien bench-upscale -- ^
  python tools\bench_upscale.py --mode thread-sweep --preset quality --tile 384 --video v3 --max-frames 200 --repeat 3
```

### Fast (tile = CHƯA ĐO — điền tile thật đã dùng, video v3, `--max-frames 200`)

| Threads | N | total_s (median) | min | max | VRAM đỉnh (MiB) | GPU util % (avg) | CPU-giây (median) |
|---|---|---|---|---|---|---|---|
| 1:2:2 | — | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| 2:2:2 | — | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| 4:4:4 | — | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |

### Quality (tile = CHƯA ĐO — điền tile thật đã dùng, video v3, `--max-frames 200`)

| Threads | N | total_s (median) | min | max | VRAM đỉnh (MiB) | GPU util % (avg) | CPU-giây (median) |
|---|---|---|---|---|---|---|---|
| 1:2:2 | — | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| 2:2:2 | — | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |
| 4:4:4 | — | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO | CHƯA ĐO |

---

## D. Ma trận đầy đủ `preset×feature×video×target`

96 ô — bảng đầy đủ + lệnh từng ô: `06_BASELINE_AFTER_BAD_UPDATE.md` mục 6.
Khi có kết quả thật, dán bảng do `tools/bench_upscale.py --report` sinh ra
(nhóm theo `kind=matrix`) TẠI ĐÂY, thay vì sửa tay bảng ở tệp 06 (tệp 06 là
baseline "trước khi đo" — giữ nguyên làm mốc; tệp NÀY là nơi kết quả thật
sống).

```
(CHƯA ĐO — chưa có tệp results.jsonl nào để render)
```

---

## E. Những gì bộ đo KHÔNG BAO GIỜ đo được (không phải "CHƯA ĐO", mà là giới hạn thiết kế)

Ghi rõ để không ai sau này cố "sửa" bộ đo để lấy các con số này bằng cách suy
diễn thay vì đo:

1. **Thời gian riêng của "interpolation".** `smooth_motion` chèn filter
   `minterpolate` vào CÙNG lệnh ffmpeg tách khung (`ff.py:137-143`, ISSUE K
   của `00_CURRENT_TRUTH.md`) — không phải tiến trình riêng. Cột
   `frame_extraction` trong JSONL GỘP cả hai khi `feature=smooth_motion`.
2. **CPU-giây chia theo từng pha.** `LayMauTaiNguyen` (trong
   `tools/bench_upscale.py`) lấy mẫu cho TOÀN BỘ lượt chạy (probe → encode),
   không reset giữa các pha — tách theo pha cần một sampler mới quanh mỗi
   `DoPha` block, tăng overhead lấy mẫu; chưa làm.
3. **Egress R2 thật.** Bộ đo là công cụ độc lập, không có thông tin đăng nhập
   storage production — pha "upload" trong JSONL là một COPY ĐĨA LOCAL đứng
   vai, không phải thời gian ghi R2 thật (khác đáng kể vì mạng + egress).
4. **`gpu_index` (chỉ số Vulkan) trong `--dry-run`.** `vulkan_device.
   vulkan_index_for()` tự chạy MỘT LƯỢT `realesrgan-ncnn-vulkan.exe` thật
   trên ảnh 16×16 để liệt kê thiết bị (`vulkan_device.py:100-109`) — bị cấm
   trong nhiệm vụ lập baseline này vì GPU đang bận. Chỉ số Vulkan thật chỉ
   được xác định trên đường chạy THẬT (không phải `--dry-run`).
5. **Nguồn 1080p+/portrait/VFR/face-heavy/noisy.** Không có mẫu — xem
   `06_BASELINE_AFTER_BAD_UPDATE.md` mục 5 (`KHÔNG CÓ MẪU`, không phải
   `CHƯA ĐO`: thêm phép đo sẽ không lấp được ô này, chỉ thêm SAMPLE MỚI mới
   lấp được).

---

# F. ⭐ ĐÃ ĐO (2026-09-26) — phân rã theo pha: **PNG I/O KHÔNG phải nút thắt**

Phép đo thật đầu tiên của đợt sửa, sau khi chủ dự án dừng bot GEMINI và một
tiến trình `realesrgan` **mồ côi** bị dọn (ISSUE L tận mắt).

**Xuất xứ:** `git_head=ab094099` · engine SHA256 `07e49f7c…b1a0c` · driver 616.92
· RTX 5060 Ti · ffmpeg 8.0.1 · video **v3** (836×576, 30 fps) · `--max-frames 200`
· preset **fast** · autotune chọn thật: `tile=384 threads=4:4:4 est=1000
budget=11560 fast_path=True`.

| Pha | giây | % tổng |
|---|---:|---:|
| **upscale + encode (tầng SR)** | **335,09** | **96,7 %** |
| frame_extraction | 10,58 | 3,1 % |
| concat | 0,51 | 0,15 % |
| upload (đĩa local thay R2) | 0,07 | 0,02 % |
| probe | 0,05 | 0,01 % |
| source_copy | 0,02 | 0,01 % |
| **tổng** | **346,67** | 100 % |

## Quyết định rút ra: ⛔ KHÔNG viết lại đường PNG

Mandate §22: *"Không rewrite pipeline nếu SR stage chiếm >90 % và I/O không đáng
kể."* Đo được **96,7 %** ⇒ điều kiện thoả.

Kể cả khi **xoá sạch** mọi chi phí I/O (bất khả), tổng chỉ giảm **≤ 3,3 %**.
So với rủi ro viết lại một đường đang chạy cho khách, đây là việc **không đáng
làm** — và nó là một quyết định *không làm gì*, dựa trên số.

⛔ Điều này **bác** hạng mục ưu tiên P1 của báo cáo cũ:
`docs/UPSCALE_V2/04_BOTTLENECKS.md` xếp *"PNG Disk I/O — 2-3x faster extraction,
⭐⭐⭐⭐"*. Trần lợi ích thật là **3,3 %**, không phải "2-3×".

⚠️ **Phạm vi của kết luận này** (⛔ đừng đọc rộng hơn): preset **fast**, nguồn
**836×576**, **200 khung**, đích mặc định, ⛔ không stabilize, ⛔ không
smooth_motion. `smooth_motion` nhân số khung nguồn lên nên tỉ lệ I/O **có thể**
khác — `CHƯA ĐO`. Preset `quality` chậm hơn nhiều ở tầng SR nên tỉ lệ I/O chỉ
còn nhỏ hơn, không lớn hơn.

## Tải nền trong lúc đo — vì sao vẫn tin được con số này

`gpu_util` trung bình 76,2 % · nhiệt trung bình 66,7 °C (đỉnh 74) · VRAM đỉnh
2 410 MiB · `cpu_giay_process_tree` 159,9 s · 839 mẫu.

Đây là con số **tỉ lệ giữa các pha trong CÙNG một lượt chạy**, nên tranh chấp
bên ngoài kéo dài **cả** tử số lẫn mẫu số — tỉ lệ 96,7 % bền với nhiễu, khác
với con số **tuyệt đối** (xem mục A, đã bị nhiễu làm hỏng).

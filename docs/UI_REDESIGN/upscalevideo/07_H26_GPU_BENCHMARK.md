# H26.5 - benchmark va gate hai GPU Upscale Video

## Ket luan

**PASS cho Fast/Quality, 1080p/1440p/4K va hai worker tren hai GPU rieng.**
Worker nay ghim Real-ESRGAN NCNN theo GPU UUID lease: UUID duoc map sang index
Vat ly cho tham so `-g`, dong thoi FFmpeg/NVENC nhan moi truong GPU cua lease.
Neu GPU da cap bien mat, job fail ro rang thay vi am tham chay tren card khac.

Nguon test la `video (10).mp4` trong folder test do chu san pham chi dinh. Evidence
chi luu ten file, khong luu duong dan ca nhan. Moi case deu probe output that va
kiem chieu resolution, FPS, audio, duration va file khac rong.

## Full video 10,054 giay, dau vao benchmark 836x480 / 24 FPS / co audio

| GPU | Preset | Output | Runtime | Ket qua |
|---:|---|---|---:|---|
| 0 | Fast | 1882x1080, 24 FPS, audio | 21,270s | PASS |
| 1 | Fast | 1882x1080, 24 FPS, audio | 20,867s | PASS |
| 0 | Quality | 1882x1080, 24 FPS, audio | 327,454s | PASS |
| 1 | Quality | 1882x1080, 24 FPS, audio | 309,938s | PASS |

Quality cham hon Fast khoang **15 lan** tren clip nay. Vi vay UI khong con mo ta
Quality la "can bang toc do"; no duoc mo ta trung thuc la chi tiet cao hon va cham
hon nhieu. Don gia hien tai van giu theo quyet dinh san pham cu; day la du lieu
can theo doi cost/output o Phase 4, khong tu y doi gia trong ve UI H26.5.

## Ma tran mau ngan 1 giay

| GPU | Preset | 1440p | 4K | FPS/audio |
|---:|---|---:|---:|---|
| 0 | Fast | 4,144s | 4,276s | PASS |
| 0 | Quality | 36,841s | 37,136s | PASS |
| 1 | Fast | 4,042s | 4,259s | PASS |
| 1 | Quality | 34,183s | 34,563s | PASS |

Tat ca output 1440p/4K dung chieu cao, giu 24 FPS va audio. Mau ngan dung de phu
nhanh scale/encode theo resolution; benchmark full 1080p o tren phu runtime dai.

## Soak hai worker dong thoi

Hai process Fast 1080p chay cung luc tren cung clip 10,054 giay:

| Chi so | GPU 0 | GPU 1 |
|---|---:|---:|
| Runtime worker | 26,158s | 23,630s |
| GPU utilization toi da | 100% | 100% |
| Nhiet do toi da | 64 C | 64 C |
| VRAM used toi da | 2.141 MB | 852 MB |
| Thermal slowdown | khong | khong |
| Output probe | PASS | PASS |

Wall time 27,990 giay; ca hai worker va ca hai output PASS. Day la bang chung hai
card cung xu ly that, khong phai hai lease cung roi vao GPU 0.

## Evidence va lenh tai lap

- `evidence/h26-gpu{0,1}-{fast,quality}-1080-full.json`
- `evidence/h26-gpu{0,1}-{fast,quality}-{1440,2160}-short.json`
- `evidence/h26-dual-gpu-soak.json` va hai worker evidence lien quan

```powershell
python tools\upscale_gpu_smoke.py <video> --gpu-index 0 --preset fast `
  --target-height 1080 --output <evidence.json>
python tools\upscale_dual_gpu_soak.py <video> --output <soak-evidence.json>
```

## Rollback

Revert app-only GPU pinning va hai tool benchmark. Khong co migration hay thay doi
du lieu. Neu rollback trong khi co job active, dung nhan job moi va drain job truoc;
khong quay ve ban khong pin GPU khi chay hai worker.

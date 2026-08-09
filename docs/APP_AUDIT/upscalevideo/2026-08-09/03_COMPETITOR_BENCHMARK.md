# 03 — Competitor Benchmark: Upscale Video

## Competitor set

| Sản phẩm | Loại | Persona/JTBD | Plan/region/device | Snapshot date | Nguồn/evidence | Giới hạn bằng chứng |
|---|---|---|---|---|---|---|
| Topaz Video | Direct leader | Pro/creator, restore/upscale | Desktop + cloud, global | 2026-08-09 | [Official product](https://www.topazlabs.com/topaz-video), [official enhancement docs](https://docs.topazlabs.com/video-ai/filters/enhancement) | E1 docs, không mua/chạy |
| TensorPix | Direct cloud leader | Non-tech creator, enhance online | Web/mobile, global | 2026-08-09 | [Official product](https://tensorpix.ai/), [official pricing/capability](https://tensorpix.ai/pricing) | E1 docs, không trả phí |
| AVCLabs Video Enhancer AI | Direct leader | Creator/restoration | Desktop, global | 2026-08-09 | [Official product](https://www.avclabs.com/video-enhancer-ai.html), [official settings](https://www.avclabs.com/user-guide/video-enhancer/settings.html) | E1 docs, marketing claims chưa blind-test |
| HitPaw VikPea | Direct consumer leader | Non-tech consumer/creator | Desktop/web/mobile | 2026-08-09 | [Official product](https://www.hitpaw.com/vikpea-video-enhancer.html), [official API](https://developer.hitpaw.com/enhance/video-enhancement) | E1 docs/API |
| Krea Video Upscaling | Innovator/adjacent | AI creator | Web, global | 2026-08-09 | [Official product](https://www.krea.ai/) | E1 landing, chi tiết UI sau login chưa chạy |
| CapCut AI Video Enhancer | Low-friction adjacent | Social creator | Desktop/web/mobile | 2026-08-09 | [Official enhancer](https://www.capcut.com/tools/ai-video-enhancer) | E1 docs, nằm trong editor lớn |

## Capability matrix

Điểm `0` không có/không chứng minh; `1` tối thiểu; `2` dùng được; `3` mạnh.
Dấu `?` là chưa đủ evidence và không được tính như PASS.

| Capability/JTBD | Loại | Trọng số | LTT 0–3 | Topaz | TensorPix | AVCLabs | HitPaw | Krea | CapCut | Best observed | Gap | Quyết định |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| Web/mobile upload dễ dùng | TABLE_STAKES | 7 | 3 | 1 | 3 | 1 | 3 | 3 | 3 | 3 | Không | KEEP |
| 1080p/2K/4K output | TABLE_STAKES | 8 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | Không | KEEP |
| Preview/before-after trước full render | TABLE_STAKES | 5 | 2 | 3 | 2 | 3 | 3 | 3 | 2 | 3 | Preview LTT chưa chọn đoạn/zoom | FIX |
| Batch, queue, history, retry | TABLE_STAKES | 6 | 2 | 3 | 2 | 3 | 2 | 2 | 2 | 3 | Thiếu full history/retry/live state | FIX |
| Denoise/compression artifact | TABLE_STAKES | 7 | 0 | 3 | 3 | 3 | 3 | 2 | 2 | 3 | Trống | BUILD |
| Deblur/focus/detail recovery | TABLE_STAKES | 6 | 0 | 3 | 2 | 3 | 3 | 2 | 2 | 3 | Trống | BUILD |
| Temporal model/flicker consistency | TABLE_STAKES | 7 | 0 | 3 | 2 | 3 | 2 | 2 | 1 | 3 | Engine hiện spatial frame-by-frame | BUILD |
| AI frame interpolation | TABLE_STAKES | 5 | 1 | 3 | 3 | 3 | 3 | 3 | 2 | 3 | LTT mới dùng FFmpeg interpolation | EXTEND |
| Stabilization | TABLE_STAKES | 4 | 2 | 3 | 3 | 3 | 3 | ? | 3 | 3 | Ít control, copy kỹ thuật | RESTYLE |
| Codec/FPS/audio/output control | TABLE_STAKES | 5 | 2 | 3 | 3 | 3 | 2 | 2 | 3 | 3 | Thiếu bitrate/output size/compatibility | EXTEND |
| Restore suite: face/HDR/color/deinterlace | TABLE_STAKES | 10 | 0 | 3 | 2 | 3 | 3 | 1 | 2 | 3 | Trống nhưng không nên nhồi tất cả MVP | DEFER |
| Handoff trực tiếp từ Seedance | DIFFERENTIATOR | 10 | 3 | 0 | 0 | 0 | 0 | 1 | 1 | 3 | Lợi thế LTT | KEEP |
| Watch Folder/operator flow | NICHE | 5 | 3 | 3 | 0 | 3 | 2 | 0 | 0 | 3 | Chỉ phù hợp operator | KEEP |
| Customer-first progressive disclosure | DIFFERENTIATOR | 8 | 2 | 1 | 2 | 2 | 3 | 3 | 3 | 3 | Technical copy/status còn nhiều | RESTYLE |
| Quote credit + refund/cancel minh bạch | DIFFERENTIATOR | 7 | 3 | 1 | 2 | 1 | 2 | 2 | 2 | 3 | Thiếu confirm cuối và cleanup artifact | FIX |
| Object removal/blur/colorize như editor | ANTI_FEATURE | 0 | 0 | 0 | 0 | 3 | 1 | 0 | 3 | 3 | Làm loãng JTBD upscale | REJECT |
| 8K output ngay | DELIBERATE_OMISSION | 0 | 0 | 3 | 0 | 3 | 3 | 3 | 3 | 3 | Không phù hợp VRAM/cost hiện tại | DEFER |

## Kết luận thị trường

- Table-stakes coverage: **43/100** theo phần 70% — mạnh ở upload/resolution,
  yếu ở chất lượng temporal, denoise/deblur và recovery.
- Differentiation: **91/100** theo phần 30% — handoff Seedance, Watch Folder và
  credit flow là tài sản thật, nhưng UX customer còn rò kỹ thuật.
- Deliberate omissions: 8K, colorize, object removal, full professional editor.
- Feature thừa/anti-feature: đưa Watch/GPU/engine jargon cho customer; gom mọi
  công cụ restoration vào một form.
- **Market Score: 57/100** (`0,7 × 43 + 0,3 × 91`).

Khuyến nghị không sao chép Topaz 1:1. Đích hợp lý là “một lần bấm cho creator”:
Auto/Fast/Quality với ba năng lực chất lượng lõi (detail, denoise, deblur), còn
tham số model chuyên sâu giữ ở operator/preset nội bộ.


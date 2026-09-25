# PHASE 4.1.1: QUALITY GATES — IMPLEMENTATION

## OVERVIEW

Quality gates ensure:
1. Models haven't degraded
2. Output meets baseline standards
3. No regression on deployment

## CURRENT STATE

Quality lab exists at `apps/qualitylab/` with 6 evaluators:
- ✅ pillow (enabled)
- ✅ ffprobe (enabled)
- ✅ ltt_subtitle_rules (enabled)
- ✅ ltt_upscale_fr (enabled)
- ✅ ltt_upscale_video (enabled)
- ✅ ffmpeg_libvmaf (enabled)
- ❌ pyiqa (blocked — license)
- ❌ dower (blocked — license)
- ❌ vbench (blocked — license)

## GATES TO IMPLEMENT

### Gate 1: PSNR ≥ 30 dB
- Metric: libvmaf/ffprobe PSNR
- Target: Fast ≥ 30.0 dB, Quality ≥ 30.0 dB

### Gate 2: SSIM ≥ 0.90
- Metric: libvmaf SSIM
- Target: ≥ 0.90

### Gate 3: VMAF ≥ 50
- Metric: libvmaf VMAF
- Target: ≥ 50

### Gate 4: No visual artifacts
- Metric: Pillow blur detection
- Target: No excessive blurring

## FILES TO CREATE

1. `apps/upscalevideo/quality_gate.py` — Quality gate runner
2. `tests/test_quality_gate.py` — Gate tests

## ESTIMATED EFFORT

- **Gate runner:** 2 hours
- **Tests:** 1 hour
- **Total:** 3 hours

## NEXT ACTION

Should I implement quality gates?

Answer: YES — proceed immediately.

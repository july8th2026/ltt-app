# UP7 — AI Detail benchmark gate

## Kết luận hiện tại

**DEFER, không bật control AI Detail.** Engine đang cài chỉ có Fast
`realesr-general-x4v3` và Quality `realesrgan-x4plus`; vì vậy đổi nhãn Quality
thành AI Detail sẽ là tính năng giả. JSON benchmark tái lập nằm ở
`evidence/ai-detail-benchmark.json` sau khi chạy gate GPU.

Kết quả RTX 5060 Ti, 10 frame lấy từ video Downloads ngày 2026-08-02: Fast
36,3057 dB / 7,692 fps / temporal error 2,4388; Quality 36,4011 dB / 1,602 fps /
temporal error 2,5518. Quality chỉ tăng 0,0954 dB ở benchmark này và chậm khoảng
4,8 lần; không model nào là ứng viên AI Detail temporal riêng. Vì vậy gate chưa
đạt và control tiếp tục bị khóa là hành vi đúng.

## Acceptance để được mở

Một engine temporal riêng phải đồng thời:

1. cải thiện PSNR ít nhất 0,30 dB so với Quality trên tập degraded giữ lại;
2. temporal error không cao hơn Quality quá 5%;
3. không có artifact nghiêm trọng trong kiểm tra mắt người ở cảnh chuyển động,
   mặt và chữ;
4. chạy được trên GPU production trong giới hạn VRAM, runtime không quá 4 lần
   Quality và có fallback;
5. license cho phép phân phối/vận hành thương mại và dependency được khóa.

## Ứng viên đã nghiên cứu

- Real-ESRGAN hiện tại là baseline spatial. Upstream mô tả x4plus cho ảnh tổng
  quát; x4v3 nhỏ hơn, ít VRAM/thời gian hơn nhưng năng lực deblur/denoise yếu hơn.
  Nguồn: https://github.com/xinntao/Real-ESRGAN và
  https://github.com/xinntao/Real-ESRGAN/blob/master/docs/model_zoo.md
- RealBasicVSR và BasicVSR++ là ứng viên temporal, đều có repo chính thức và
  Apache-2.0, nhưng cần stack inference/model mới và chưa có trong release này.
  Nguồn: https://github.com/ckkelvinchan/RealBasicVSR và
  https://github.com/ckkelvinchan/BasicVSR_PlusPlus

## Lệnh tái lập

```powershell
python tools\benchmark_upscale_ai_detail.py `
  "C:\Users\Thang Tuong\Downloads\eeae72a7_seedance_f56d2de3_1080p.mp4" `
  --output docs\UI_REDESIGN\upscalevideo\evidence\ai-detail-benchmark.json
```

Script chỉ giữ JSON tổng hợp; frame tạm và output ảnh bị dọn trong `finally`.

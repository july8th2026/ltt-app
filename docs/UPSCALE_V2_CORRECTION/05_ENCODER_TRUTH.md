# 05 — ENCODER TRUTH

> Nguồn: `apps/upscalevideo/jobs.py::_resolve_encoder`, `apps/upscalevideo/ff.py::_venc_args`,
> `apps/upscalevideo/schemas.py`, `platform_core/media.py::detect_gpu_encoder`.

## Producer → Consumer, TRƯỚC sửa

`_resolve_encoder(codec)` (producer) chọn một chuỗi tên encoder dựa trên
`media.detect_gpu_encoder()` (dò 3 tên H.264: `h264_nvenc, h264_qsv, h264_amf`
— `media.py:220` — **không bao giờ dò `hevc_*`**, tức giả định năng lực HEVC =
năng lực H.264, chưa từng kiểm chứng). `ff._venc_args(encoder)` (consumer) diễn
dịch tên đó thành tham số `-c:v` thật.

| producer trả | consumer hiểu? | `-c:v` THẬT chạy |
|---|---|---|
| `h264_nvenc` | có | `h264_nvenc` |
| `hevc_nvenc` | có (+ `-tag:v hvc1`) | `hevc_nvenc` |
| `h264_qsv` / `hevc_qsv` | **không** — rơi `else` | **`libx264`** |
| `h264_amf` / `hevc_amf` | **không** — rơi `else` | **`libx264`** |
| `"libx264"` (đường CPU cũ, bỏ luôn `codec`) | có | `libx264` |

Hai chỗ rơi âm thầm: (1) bốn tên QSV/AMF không được `ff._venc_args` (cũ) nhận
diện, rơi về `libx264` mà không ai biết; (2) đường CPU trả cứng chuỗi
`"libx264"` cho **mọi** `codec` — một khách xin HEVC mà không có GPU encoder
nhận **H.264** trong khi kết quả job vẫn khai `"codec": codec.value` (enum
khách **yêu cầu**, không phải codec thật) ⇒ `{"codec":"hevc","encoder":"libx264"}`
gửi ra API/UI. **Trường `codec` nói dối.**

Vì máy production có NVENC (`h264_nvenc` dò thấy trước), cả hai bug ngủ yên
**hôm nay** — chúng thức khi NVENC vắng (driver lỗi, host chỉ có iGPU), đúng
lúc đang có sự cố khác chồng lên.

## Producer → Consumer, SAU sửa

Chốt sản phẩm 2026-09-26: **app này hỗ trợ NVENC hoặc CPU, không QSV/AMF.**
Máy production là NVIDIA; dựng đường QSV/AMF thật sẽ là mã không ai chạy và
không ai test được ở đây. `platform_core.media` vẫn dò cả ba loại cho các app
khác dùng chung — `upscalevideo` chỉ **không nhận** hai loại nó không nói được.

```python
# jobs.py::_resolve_encoder (rút gọn)
gpu = media.detect_gpu_encoder()
if gpu == "h264_nvenc":
    return ENCODER[codec]              # h264_nvenc | hevc_nvenc
if gpu in ("h264_qsv", "h264_amf"):
    log.info(...)                      # nói ra, rồi đi CPU đúng codec
return ENCODER_CPU[codec]              # libx264 | libx265 — schemas.py
```

`ENCODER_CPU = {Codec.h264: "libx264", Codec.hevc: "libx265"}` (`schemas.py:33`)
— đường CPU giờ **tôn trọng** `codec` thay vì trả cứng H.264. `ff._venc_args`
thêm nhánh `libx265` (`-preset medium -crf 20 -tag:v hvc1`, `ff.py:209-213`)
và **ném `ValueError`** cho mọi tên nó không biết (`ff.py:214-218`) thay vì rơi
âm thầm — bất biến producer↔consumer giờ được khoá bằng test, không chỉ bằng
lời hứa (`tests/test_4904_upscale_correction.py::test_resolve_encoder_luon_tra_ten_ma_venc_args_hieu`,
`test_venc_args_nem_valueerror_cho_encoder_la`).

| producer trả (sau sửa) | `-c:v` THẬT |
|---|---|
| `h264_nvenc` / `hevc_nvenc` | như cũ |
| `libx264` (CPU, khách xin H.264) | `libx264` |
| `libx265` (CPU, khách xin HEVC) | `libx265` |
| GPU trả `*_qsv`/`*_amf` | log rồi rơi về `libx264`/`libx265` **đúng theo `codec` khách xin** |

## `codec` trong kết quả job: NGHĨA MỚI

```python
res["codec"] = quality_gate.HO_CODEC.get(encoder, codec.value)   # jobs.py:449
res["codec_requested"] = codec.value                              # jobs.py:450
res["encoder"] = encoder
```

- **`codec`** = họ codec THẬT của luồng vừa encode (tra từ `encoder` qua bảng
  `HO_CODEC` trong `quality_gate.py` — `h264_nvenc→h264`, `libx265→hevc`, …).
- **`codec_requested`** = ý muốn ban đầu của khách (enum họ gửi lên).
- Nếu hai trường lệch nhau, đó là bằng chứng của một fallback đã xảy ra — API/UI
  đối soát được thay vì bị `codec` nói dối như bản cũ.
- Cổng kỹ thuật (`quality_gate.kiem_tra_dau_ra`, mục 4) còn bắt runtime: nếu
  `expect_encoder` không khớp `vcodec` thật đọc từ `ffprobe`, job **đỏ** trước
  khi upload — lưới cuối cùng nếu chỗ nối producer/consumer lại lệch trong
  tương lai.

## Quyết định: NVENC + CPU, không QSV/AMF thật

Đã ghi ở trên và trong `jobs.py::_resolve_encoder` docstring. Lý do lặp lại rõ:
máy production không có phần cứng QSV/AMF để chạy thật hay viết test thật cho
đường đó — dựng nó bây giờ là mã chết mang rủi ro (một nhánh không ai chạy qua
là chính xác loại lỗi ISSUE I). Mở lại khi có host QSV/AMF thật để đo và test
(`07_CORRECTION_PLAN.md`).

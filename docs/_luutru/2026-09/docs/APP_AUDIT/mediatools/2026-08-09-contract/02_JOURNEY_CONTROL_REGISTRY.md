# 02 — Journey & Control Registry

| Tool/control | Action/state | Credit/recovery | Verdict |
|---|---|---|---|
| asset.image/images/video/audio | owned key passthrough | 0 credit; Job vẫn có thể tạo | PARTIAL |
| audio.generate | text/model/voice/style → WAV | 2 credit/1000 chars; provider error | LIVE/PARTIAL |
| extract frames | video + interval/max | 1 credit; FFmpeg progress | LIVE |
| merge image | 2–12 + layout | 1 credit | LIVE |
| merge video | 2–12, cut only | 1 credit | LIVE/PARTIAL |
| social import | rights + URL → video | 2 credit; download limits | **BROKEN security** |
| node standalone run | Agent composer | orchestration bug audit Agent | PARTIAL |
| output library/delete/retention | không có control chuẩn | orphan risk | MISSING |
| `/mediatools` | 308 Agent | đúng internal surface | LIVE |

Loading/error/progress cơ bản nằm ở Job/Agent; cancel cooperative trong FFmpeg/
download/TTS không được chứng minh đầy đủ.


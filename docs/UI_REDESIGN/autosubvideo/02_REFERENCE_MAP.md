# UI-RD Auto Sub Video — giải phẫu ảnh tham chiếu

Ảnh 1680×935. Mọi tỷ lệ dưới đây là gần đúng, dùng làm target chứ không khóa pixel.

## Bố cục

- Header 56 px (~6% cao): brand/app, stepper Upload→Transcript→Style→Render,
  help/notification/account, output aspect/resolution và Export.
- Left rail x=16..320 (~19% rộng): project, files, transcript/search/actions, cue
  theo speaker, jobs.
- Center x=334..1304 (~58%): video preview; transport; thumbnail + waveform timeline;
  cue cards; editor nội dung/timing.
- Right inspector x=1315..1663 (~21%): tabs Templates/Style/Animation, preset cards,
  Brand Kit, typography, color, stroke, highlight, shadow, karaoke, animation.
- Desktop mật độ cao, radius 3–6 px, border đỏ rất mảnh, nền #050505/#101010,
  CTA đỏ. Target LTT giữ màu/brand nhưng phải tăng focus/contrast nơi cần.

## Map control → logic

| Vùng/control ảnh | Độ chắc | Hiện trạng | Quyết định sơ bộ |
|---|---|---|---|
| Stepper 4 bước | V | form một màn | BUILD state thật; không khóa editor khi quay lại bước |
| Project dropdown | V | không project | BUILD, phụ thuộc project contract |
| Drag/drop + file card | V | input file/R2 | EXTEND drop/progress/probe/retry/Q48 |
| Transcript auto language | V | parser file | BUILD ASR + import |
| Translate | V | không có | BUILD có quote; không dịch giả bằng client |
| Speaker Labels | V | không có | BUILD tùy chọn; anonymous labels + rename |
| Search transcript | V | không editor | BUILD local index trên project state |
| Cue list text/timing | V | data chỉ ở job params | BUILD edit/split/merge/delete/validation |
| Video overlay subtitle | V | chỉ output sau render | BUILD preview parity từ cùng project/style |
| Transport/fullscreen/volume | V | browser video cơ bản | BUILD/RESTYLE |
| Thumbnail timeline | V | không có | EXTEND; thumbnail strip có thể DEFER nếu tốn tài nguyên |
| Waveform + playhead | V | không có | BUILD wavesurfer Regions/Timeline hoặc peaks server |
| Cue cards/timeline regions | V | không có | BUILD một track; drag resize có snapping/conflict guard |
| Edit Subtitle + Sync/Timing | V | không có | BUILD; timing validation server-side |
| Templates | V | 8 preset registry | EXTEND preset preview + owner template store |
| Style controls | V | schema/ASS hỗ trợ phần lớn | EXTEND, chỉ control có render parity |
| Karaoke/Word Pop | V | highlight mode có một phần | EXTEND word timestamps → ASS karaoke |
| Animation Pop In | V | chưa có contract | BUILD subset fade/pop/slide có ASS parity; arbitrary DEFER |
| Brand Kit | V | không có | DEFER generic brand contract; app template thay thế trước |
| 16:9/1080p | V | giữ source | EXTEND output profile, preserve aspect mặc định |
| Export | V | submit burn + download rời | EXTEND quote/confirm + video/SRT/ASS/ZIP |
| Job panel | V | 12 job cards | EXTEND status/cancel/retry/artifact owner-scoped |

## Responsive target suy ra

- ≥1280: ba cột như ảnh; rail 280–310 px, inspector 320–350 px, center min 560 px.
- 768–1279: left và right thành drawer; center/timeline chiếm chính.
- ≤640: preview → cue editor → style; timeline chỉ waveform/cue list giản lược,
  không cố nhồi ba cột hay drag chính xác; CTA sticky và touch target ≥44 px.


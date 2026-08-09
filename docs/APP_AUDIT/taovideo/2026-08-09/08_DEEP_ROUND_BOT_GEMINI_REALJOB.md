# 08 — Deep round: parity với Bot Gemini và job thật

**Ngày:** 2026-08-09  
**Mode:** `DEEP` theo `docs/quy_tac_audit.md`  
**Phạm vi:** app đang deploy `https://app.lttstudios.com/taovideo`, đối chiếu
read-only với `D:\BOT GEMINI\app\modules\seedance_video` và tài liệu
`docs/seedance_video/`. Không sửa code, không chạy test trong cây Bot Gemini.

## A0/A1 — Scope và current truth

- Persona/JTBD: creator nhập prompt, tùy chọn model/preset, đính kèm ảnh/video
  tham chiếu, nhận một MP4 có thể tải hoặc chuyển sang Upscale.
- Preset kiểm chứng: `seedance-2.0-mini`, `4s`, `16:9`, `480p`, 1 output,
  audio bật.
- Dữ liệu test: `server/static/home-covers/video.png` (ảnh 1024×576) và
  `G:\My Drive\AI\Tool AI\Video seedacne\video (10).mp4` (H.264/AAC,
  864×496, 10,054s, 3.005.870 bytes). Đây là file người dùng chỉ định cho
  kiểm thử, không ghi vào repo ngoài evidence ảnh đã lọc.
- Môi trường fixture 8112 **không có** BytePlus/APIKEYS, ModelArk AK/SK hoặc
  R2 (đã kiểm tra chỉ trạng thái boolean, không đọc giá trị). Vì vậy fixture chỉ
  dùng cho UI; job provider phải chạy trên tài khoản test đang đăng nhập ở
  staging/deploy theo yêu cầu kiểm thử.

## A2 — Journey/control đã chạy

| Journey | Kết quả thật | Evidence |
|---|---|---|
| Chọn Mini → 4s → 480p → prompt | PASS; preset giữ sau reload | EV-BR-007 |
| Upload ảnh | PASS; FileReader preview 1024×576, role `reference_image` | EV-BR-007 |
| Upload video | PASS; video preview readyState=4, 864×496; blob range 206 | EV-BR-007 |
| @handle cho ảnh/video | PASS ở request/job; prompt `@style/@motion` được chuẩn hóa theo vị trí ref trong `refs.build_content` | EV-SRC-007 + EV-RJ-001 |
| Quote trước submit | PASS về hiển thị, nhưng **MISLEADING**: 47 hold trên UI không phản ánh input video (canonical rate 22 → 29 hold) | EV-RJ-001 |
| Submit một job có 2 ref | PASS; redirect về `/taovideo`, history ghi queued/running | EV-RJ-001 |
| Progress/log/reload | PASS; 3% asset → 5% submit → 10–17% poll → 92% download → 100% done, support ID ổn định | EV-RJ-002 |
| Output player | PASS; browser readyState=4, 864×496, 4,096s, không media error | EV-RJ-003 |
| Tải output | PARTIAL; link chuyển thẳng sang signed R2 player (không `Content-Disposition: attachment`) | EV-RJ-004 |
| Saved asset reuse | PASS cho picker sau job (ảnh + video hiện lại); không có asset lifecycle/delete riêng | EV-RJ-002 |
| Remix/“Biến thể” | **MISLEADING**; tự đặt `count=2` nhưng không tick lại saved refs và không dựng lại handle binding | EV-BR-008 |
| Mobile 390×844 | PASS overflow=0, output playable, drawer đóng ban đầu; keyboard focus trap/Escape vẫn chưa đạt từ vòng trước | EV-BR-009 |

## A3 — Real-job evidence

Job canary `121eb14b…` đã hoàn tất trên tài khoản test đang đăng nhập.
Số dư hiển thị thay đổi **520 → 491 khi submit → 442 sau settle**: tổng trừ
78 credit. UI trước chạy hiển thị 47 credit tạm giữ; với video input, manifest
canonical estimate đáng ra là 22, hold ×1,25 = 28 (làm tròn 29). Actual 78
vượt hold 49 credit — tái hiện trực tiếp G3/P0, không phải suy đoán từ source.

`ffprobe` của file tải về:

```json
{"duration":"4.096000","size":1192985,
 "video":{"codec":"h264","width":864,"height":496,"fps":"24/1"},
 "audio":{"codec":"aac"}}
```

Frame strip cho thấy chủ thể đỏ/đen từ ảnh tham chiếu được giữ, camera tiến gần
và vật thể nâng lên theo prompt. Đây là E4 cho core outcome và asset image+video;
không phải bằng chứng cho audio-reference hoặc mọi model/resolution.

## A4 — Matrix đối chiếu Bot Gemini

| Capability | Bot `seedance_video` (source/docs) | LTT `taovideo` | Verdict |
|---|---|---|---|
| Prompt + positional tags | sanitize, mask/restore tags, `@IMG/@VID/@AUD` | normalize tag theo thứ tự, không có lớp sanitize đầy đủ | `FIX` |
| Image ref | ≤8MB inline; normalize magic/image | ≤8MB inline; route tin `content_type`, normalize worker | `FIX` |
| Video ref | magic sniff, ≤50MB, asset service | UI/route ≤60MB; asset tạo thật PASS nhưng MIME/container chưa sniff | `FIX` |
| Audio ref | allowlist sniff, asset type audio | `assets.to_asset("audio", .m4a)` lại gửi `Image` + `image/png` | `BUILD` (P1) |
| Limits | 9 image + 3 video + 3 audio, total 12 | total 4, không tách quota theo loại | `PARITY` sau blocker |
| Asset registry | content-hash cache, owner, remote reconcile, 50-slot quota, LRU/grace, pin in-flight, delete sync | blob suy ra từ 60 job gần nhất; mỗi worker tạo remote asset mới; không cache/reconcile/quota UI | `BUILD` (P1) |
| Privacy/face heal | proactive video asset; reactive image privacy auto-heal ≤2 | image face heal có; không có audio guard; lifecycle remote chưa có | `FIX` |
| Job recovery | persisted remote task, retry/re-poll, cancel provider, `needs_review` | remote task persisted; poll retry/cancel provider/lifecycle còn hạn chế | `FIX` |
| Output verification | ffprobe + metadata + thumbnail | lưu MP4 và metadata params; không ffprobe/thumbnail trong handler | `FIX` |
| Billing | provider usage/reconcile, no hidden variance | actual token settle nhưng variance không cap; real canary vượt hold | `BLOCKER` |
| UX library | upload/preview/role/handle/reuse/delete rõ | upload/preview/reuse; không remove/replace/delete độc lập; remix mất refs | `FIX` |

## A5–A6 — Findings mới/điều chỉnh

1. **F-001 nâng P1 → P0 (G3):** real canary trừ 78 credit trong khi hold 29
   theo video-rate; balance variance 49. Điều kiện mở: customer charge cap không
   vượt hold, hoặc quote canonical được xác nhận lại trước submit; ledger variance
   chỉ là platform risk và phải có alert.
2. **F-020 P1 (input contract):** audio reference bị biến thành ModelArk
   `AssetType=Image`, `content-type=image/png` trong `apps/taovideo/assets.py`;
   UI quảng cáo MP3/WAV/M4A nhưng chưa có đường audio đúng. Acceptance: sniff +
   `AssetType=Audio`/MIME đúng, provider canary audio pass hoặc lỗi rõ và refund.
3. **F-021 P1 (privacy/ops):** LTT không có hash cache, remote list/reconcile,
   pin/grace/LRU hoặc xóa asset remote như Bot Gemini; job thật đã tạo ít nhất
   một image và một video asset nhưng không có bằng chứng cleanup. Acceptance:
   remote count không tăng vô hạn, cleanup idempotent, không xóa asset đang chạy.
4. **F-019 P2 (honest UX):** nút “Biến thể” tự đặt 2 output và không tái chọn hai
   saved refs/handles; user có thể trả thêm tiền nhưng tạo text-only biến thể.
5. **F-022 P2 (delivery):** link “Tải video” redirect signed R2 và mở player;
   thiếu attachment semantics/filename. Acceptance: download có tên ổn định,
   range/resume và owner check.

## A7–A10 — Decision và roadmap gate

Khuyến nghị ghép `REPAIR → PARITY chọn lọc → DIFFERENTIATED`; **không chạy thêm
job trả phí** trước khi đóng F-001/F-020. Phase bắt buộc:

1. **P0 Credit/quote:** canonical quote nhận biết video/audio refs; charge cap,
   idempotent settle, variance metric/alert; test concurrency và âm số dư.
2. **P1 Asset/input:** staging TTL trước hold, magic/container sniff, audio asset
   type đúng, hash cache + remote reconcile/quota/pin/grace/LRU, cleanup.
3. **P1 Recovery/delivery:** retry/cancel/re-poll, preserve form/locale, output
   ffprobe/thumbnail, download attachment.
4. **P2 UX parity:** reference manager remove/replace/reorder; remix giữ refs và
   binding; đưa technical control vào advanced; keyboard/mobile WCAG.
5. **P2 capability parity:** chỉ sau provider capability probe + cost/SLO: edit,
   extend, first/last frame và sequence đơn giản; không build full timeline.
6. **Release:** `tools/gate.py`, browser A-Z trên staging, canary có log/metric,
   rồi mới canary production. Hiện tại vẫn `BLOCKED`.


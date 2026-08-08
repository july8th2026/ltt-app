# 01 - Current truth

## 1. Inventory bề mặt

| App | Trạng thái manifest | Bề mặt/lịch sử hiện có | Kết luận |
|---|---|---|---|
| `agent` | public, enabled | AgentRun, activity, child jobs | giữ; audit riêng sau shell chung |
| `autosubvideo` | public, enabled | 12 job gần nhất; React Studio có rollout flag | giữ; production có thể đang rơi về legacy |
| `chataistudio` | public, enabled | lịch sử hội thoại sidecar, không dùng Job | giữ; cần operation trace riêng, không giả chat thành job |
| `demo` | non-public, enabled | redirect sang job chung | giữ runtime kiểm thử, ẩn tuyệt đối với customer |
| `kichban` | public, enabled | 12 job gần nhất | bỏ app customer; chưa được xóa runtime ngay |
| `mediatools` | non-public, enabled | không có UI, redirect Agent Canvas | bỏ bề mặt customer; giữ capability nội bộ |
| `prompt_ai_ommi` | public, enabled | H26.8: Prompt AI; project/resource/library/storyboard/job/credit dashboard | giữ slug/job/provider; chưa deploy |
| `socialbot` | non-public, enabled, frozen | log/manual job riêng, route sau feature flag | trạng thái bảo trì; không mở feature mới |
| `taoanh` | public, enabled | H26.9: shell canonical General + Thumbnail, history hai mode | giữ; chưa deploy |
| `taoclipngan` | public, enabled | clip history | giữ; yêu cầu folder hiện UNKNOWN |
| `taovideo` | public, enabled | H26.7: Tạo Video Seedance; filter/history/assets/jobs + responsive Studio PASS | giữ slug/provider; chưa deploy |
| `thumbnail` | public, enabled, catalog child | H26.9: executor/job/history/fragment tương thích | `/thumbnail` 308 về `/taoanh/thumbnail`; chưa deploy |
| `upscalevideo` | public, enabled | 12 job, queue, compare, batch | giữ; ưu tiên sửa đầu tiên |

## 2. Vì sao không được xóa thẳng ba tool

- `kichban` đang sở hữu `text.generate`, là Text capability đa dụng của Agent,
  ngoài `text.script` dành riêng cho YouTube.
- `mediatools` đang sở hữu asset Image/Images/Video/Audio, Audio generate,
  Extract Frames, Merge Image/Video và Social Video import của Agent.
- `demo` là đường test rẻ cho chuỗi domain -> web -> job -> worker -> storage ->
  credit; tài liệu nền tảng yêu cầu giữ để nghiệm thu hạ tầng.

Do đó, “Bỏ/Ẩn” ở Phase 0 phải có nghĩa: **gỡ khỏi catalog, header, search và
đường customer**, nhưng giữ runtime nội bộ cho tới khi dependency đã được di trú
và regression chứng minh không gãy.

## 3. Gap jobs/log đo được

`platform_core.models.Job` hiện lưu trạng thái hiện tại (`status`, `progress`,
`progress_msg`), kết quả cuối, lỗi, số lần thử, worker và timestamps. Không có
bảng append-only ghi chuỗi sự kiện của một job. Vì vậy:

- progress cũ bị ghi đè; không trả lời được job đã đi qua bước nào;
- retry/cancel/reclaim/provider latency không có timeline thống nhất;
- mỗi app tự dựng lịch sử theo cách khác nhau;
- log process có thể xoay vòng và không phải hồ sơ hỗ trợ theo job.

Nguồn chân lý `Job` đang đúng và phải giữ; cần bổ sung `JobEvent`, không tạo một
bảng job riêng cho từng app.

## 4. Evidence folder

| Folder | Mô tả/ảnh | Mức đầy đủ |
|---|---|---|
| `Chung` | 3 yêu cầu, 2 ảnh | đủ để lập plan shell |
| `UpscaleVideo` | 7 yêu cầu, 4 ảnh | đầy đủ nhất |
| `TaoVideoAI` | 2 yêu cầu, 1 ảnh | đủ để lập audit UI phase |
| `PromptAIOmmi` | 3 yêu cầu, 1 ảnh | H26.8 đã khóa bằng H19/Q77/Q81 và browser audit |
| `AutoSubVideo` | 1 yêu cầu, không ảnh | chỉ đủ điều tra version drift |
| `ChatAIStudio` | không `MoTa.txt` | UNKNOWN |
| `TaoAnhAI` | không `MoTa.txt` | UNKNOWN ngoài yêu cầu merge chung |
| `TaoClipNgan` | không `MoTa.txt` | UNKNOWN |
| `LTTAgentAI` | file mẫu trống | UNKNOWN |
| `DangBaiFacebookTiktok` | file mẫu trống | chỉ có trạng thái bảo trì từ `Chung` |

## 5. Bằng chứng browser/hardware

- E3-01: local 8100, Chrome desktop, catalog public render 10 card; console 0
  error/0 warning, không có failed request bất ngờ.
- E3-02: Kịch bản YouTube vẫn xuất hiện ở catalog public và header `Kịch bản`.
- E1-01: authenticated catalog lấy mọi app nạp được rồi chỉ lọc AppAccess;
  `public=False` không ẩn app khỏi user đã đăng nhập.
- E1-02: card chỉ có CTA `Mở app`; toàn card chưa là link và cover/title dùng
  icon lặp.
- E1-03 — **đã sửa tại H26.6 (2026-08-08):** AutoSub Studio là giao diện public
  mặc định sau AS9; biến rollout thiếu/rỗng không còn làm production âm thầm
  quay về legacy. `off` vẫn là rollback chủ ý và bundle thiếu vẫn fail-safe về
  form cũ trong một release.
- E1/E3-04: máy có 2 RTX 5060 Ti, mỗi card 16.311 MiB. Tổng khoảng 32 GB nhưng
  một job chỉ lease một GPU; không được tính thành một vùng VRAM 32 GB.

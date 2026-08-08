# Nhật ký

> File này ghi **sự thật đã xảy ra**. `KE_HOACH_TRIEN_KHAI.md` ghi *ý định*,
> `QUYET_DINH_NEN_TANG.md` ghi *điều đã chốt*. Khi kế hoạch và nhật ký mâu
> thuẫn, **nhật ký đúng** và phải sửa lại kế hoạch cho khớp.
>
> Mục mới thêm **lên trên cùng**. Mẫu ghi ở cuối file.
>
> **Không bao giờ ghi giá trị bí mật vào đây** — chỉ ghi tên biến, nơi lưu,
> trạng thái xoay vòng.
>
> Nhật ký của giai đoạn desktop → web (2026-07-29 đến 2026-07-30) nằm ở
> `_luutru/PROJECT_MEMORY.md`. Vẫn đáng đọc: nó ghi từng lỗi thật và cách sửa.

---

## 2026-08-09 — H26.10A: Clip Studio customer-first PASS

- **Mục tiêu:** audit và sửa UX Clip ngắn theo hành vi khách hàng; không viết
  lại engine hay bịa tính năng từ folder desktop trống.
- **Hạng mục:** H26.10A — hoàn thành; parent H26.10 còn Chat/Agent/Socialbot.
- **Trạng thái:** xong development; chưa deploy.

### Đã làm

- Xác minh `TaoClipNgan` chỉ có `desktop.ini`; ghi UNKNOWN, không tạo feature từ
  suy đoán.
- Giữ số clip+tỉ lệ ở bề mặt chính; gom tier/brand/platform/genre/language/
  min-max vào Advanced mặc định đóng. Đổi nhãn engine thành Best/Balanced/Fast.
- Thêm source preview/filename/duration/size/clear cho file local và summary cho
  asset library. Browser bắt CSS làm `[hidden]` mất hiệu lực; đã sửa và khóa test.
- Localize copy Python/Jinja/JS, estimate, status/progress và lỗi customer;
  English catalog 967 chuỗi, 0 thiếu, 0 fuzzy.
- Mọi job card có Activity log; giữ raw kỹ thuật trong job detail phục vụ debug,
  không phơi ở Studio.
- Browser fixture 8116 với MP4 thật 7,2 MB/52 giây: Fast quote 20, fake worker
  tạo 2 clip, settle 15 (100→85), history/compare/package revision 1/log PASS;
  mobile 390 và desktop 1920 không overflow, console 0 error/0 warning, request
  app 200/206.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `tests/test_161_clip_customer_workflow_h26.py` trước sửa | FAIL 2/2 đúng gap |
| Targeted Clip cuối | PASS 16/16 trong 9,04 giây |
| `python tools\\gate.py --quick` | PASS 8/8 trong 26,6 giây |
| `python tools\\gate.py` | PASS 9/9 trong 1.670,8 giây; pytest 1.645,4 giây |

### Quyết định mới

Không có quyết định kiến trúc mới: triển khai theo Q52/Q77/H26 option A; giữ
engine/job/cost hiện hữu và sửa presentation/customer workflow.

### Cách lùi lại

Revert commit H26.10A. Không migration, không xóa job/output/project/package.

### Việc tiếp theo

1. H26.10B audit rồi xử lý Chat AI Studio.
2. Không deploy trước H26.12.

## 2026-08-09 — H26.9: hợp nhất Tạo ảnh AI + Thumbnail PASS

- **Mục tiêu:** biến hai full page cùng nhóm ảnh thành một product khách hàng,
  giữ nguyên executor/job/credit/storage/history và mọi deep link cần tương thích.
- **Hạng mục:** H26.9 — hoàn thành.
- **Trạng thái:** xong development; chưa deploy.

### Đã làm

- Tạo shell canonical `/taoanh` với mode General và Thumbnail; `/thumbnail`
  redirect 308 về `/taoanh/thumbnail`.
- Tách Thumbnail thành fragment được bảo vệ bởi session/CSRF, nạp qua HTMX route
  công khai. Không import Python internals giữa `taoanh` và `thumbnail`; hai
  manifest/executor/job type/cost/storage/history vẫn độc lập.
- Giữ form, 31 preset, Brand Kit, reference, preview cấu hình, technical score,
  compare và remix. Queue HTMX tạo job thật rồi điều hướng toàn shell; lỗi input
  trả fragment đúng scope.
- Folder desktop `TaoAnhAI` chỉ có `desktop.ini`, không có `MoTa.txt` hay ảnh;
  đã ghi UNKNOWN và không tự bịa thêm tính năng.
- Browser fixture owner-scoped: desktop 1920×1080 và mobile 390×844 không
  overflow; quote ×2, submit 500→490 credit, history/compare/remix/edit chạy;
  console 0 error/0 warning, request app 200/204.
- Dọn drift i18n phát hiện trong lượt extract: English 907 chuỗi, 0 thiếu,
  0 fuzzy; cập nhật PO/MO và kiểm nhãn mới trên browser.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| Targeted image/thumbnail ban đầu | PASS 31 test |
| Targeted sau cập nhật marketplace contract | PASS 32 test trong 20,17 giây |
| `python tools\\gate.py --quick` lượt sạch | PASS 8/8 trong 27 giây |
| Full gate lượt đầu có kết quả | FAIL 8/9: 2.564 pass, 1 test H26.4 còn kỳ vọng redirect ngược |
| Targeted test H26.4 sau sửa | PASS |
| `python tools\\gate.py` lượt cuối | PASS 9/9 trong 1.673,8 giây; pytest PASS trong 1.648,3 giây |

Một lượt full gate trước đó bị lớp shell timeout 300 giây làm mất kênh output;
đã xác minh và dừng đúng gate/pytest PID của lượt đó trước khi chạy lại, không
để hai bộ regression tranh CPU.

### Quyết định mới

- Q82: một shell/IA canonical nhưng composition qua authenticated HTTP fragment;
  không import ruột app và không gộp executor hay dữ liệu.

### Cách lùi lại

Revert commit H26.9. Không có migration/xóa dữ liệu; hai executor và history
cũ còn nguyên nên presentation có thể quay lại hai trang độc lập.

### Còn tồn đọng

- Chưa deploy/canary; G8 khóa đến H26.12.
- Không có đầu vào chi tiết từ folder desktop ngoài yêu cầu merge đã chốt.

### Việc tiếp theo

1. H26.10: audit tuần tự Clip ngắn, Chat, Agent và trạng thái maintenance
   Socialbot; không build từ folder trống.
2. Không deploy trước H26.12.

## 2026-08-09 — H26.8: Phase 3.4 Prompt AI PASS

- **Mục tiêu:** áp dụng folder `PromptAIOmmi`, đổi public copy và hoàn thiện UX
  khách hàng; chỉ khảo sát read-only tài nguyên Prompt Seedance, không import
  chéo hoặc mang dữ liệu người dùng từ `D:\BOT GEMINI` sang.
- **Hạng mục:** H26.8 — hoàn thành.
- **Trạng thái:** xong; chưa deploy.

### Đã làm

- Đổi tên public thành **Prompt AI** nhưng giữ nguyên slug
  `/prompt-ai-ommi`, job `prompt_ai_ommi.generate`, provider, bảng và công thức
  credit để không phá deep link/dữ liệu/job cũ.
- Thêm catalog tích hợp bất biến theo Q81: 8 style, 4 meta và 4 snippet. Catalog
  phát hành cùng code, không đọc DB/file user/BOT lúc runtime; user phải clone
  thành bản riêng trước khi sửa. Catalog do admin publish trong DB vẫn giữ.
- Nâng tổng quan từ card rỗng thành dashboard dùng dữ liệu owner-scoped thật:
  credit chi hôm nay/tháng, sáu nhóm tài nguyên, project gần đây và hoạt động
  cá nhân; người mới nhận empty state ba bước thay vì số liệu giả.
- Sửa fixture browser đăng ký bảng `ommi_*` trước `create_all`; lỗi overview 500
  đầu phiên được tái hiện, truy traceback và đóng bằng regression test.
- Nén app vừa viewport desktop; sửa mobile rail thành một hàng cuộn ngang 60px,
  target 44px. Browser A-Z tạo resource thật, duyệt đủ catalog, clone Meta thành
  bản private có lịch sử; desktop 1920×1080 và mobile 390×844 không overflow,
  console cuối 0 error/0 warning, request mới 200/201.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| Targeted backend H26.8 | PASS 41 test; 1 warning TestClient cũ |
| Frontend `npm test -- --run` | PASS 22 test |
| Frontend `npm run build` | PASS typecheck + Vite + build-meta |
| `python tools/gate.py --quick` lượt đầu | FAIL 5 chuỗi i18n mới; đã bọc `_t()` |
| `python tools/gate.py --quick` sau sửa | PASS 8/8 trong 25,5 giây |
| `python tools/gate.py` lượt đầu | FAIL 8/9: 3 kỳ vọng catalog cũ; 2.557 test khác pass |
| Targeted test catalog sau sửa | PASS 3/3 |
| `python tools/gate.py` lượt sạch cuối | PASS 9/9 trong 1.630,2 giây; pytest PASS trong 1.604,5 giây |

### Quyết định mới

- Q81: catalog tích hợp Prompt AI là dữ liệu code bất biến; catalog quản trị vẫn
  ở DB; user chỉ sửa bản clone riêng. Lý do là cần tài nguyên dùng ngay nhưng
  không được phụ thuộc runtime hay dữ liệu người dùng của BOT GEMINI.

### Cách lùi lại

Revert commit H26.8. Không có migration; không xóa project/resource/library/job/
ledger. Bundle cũ quay lại cùng code và catalog tích hợp biến mất an toàn.

### Còn tồn đọng

- Chưa deploy; release vẫn khóa tới H26.12.
- Không dựng team, USD, folder, video gần đây hoặc số liệu minh họa chưa có
  contract backend.

### Việc tiếp theo

1. H26.9 Phase 3.5: audit rồi triển khai shell Tạo ảnh AI hợp nhất Thumbnail.
2. Không chạy song song H26.10.

## 2026-08-09 — H26.7: Phase 3.3 Tạo Video Seedance PASS

- **Mục tiêu:** áp dụng folder `TaoVideoAI`, đổi tên public và hoàn thiện UX
  khách hàng mà không làm sai model/options/provider/job/credit hiện hữu.
- **Hạng mục:** H26.7 — hoàn thành.
- **Trạng thái:** xong; chưa deploy.

### Đã làm

- Đổi tên manifest/nav/title/CTA thành **Tạo Video Seedance**; giữ nguyên slug
  `/taovideo`, ToolSpec và `taovideo.generate` để không phá deep link/job cũ.
- Giữ camera/motion/style/seed nhưng chuyển vào vùng tùy chọn sáng tạo mặc định
  đóng. Ba picker ảnh/video/audio dùng chung contract backend, có preview local,
  role/handle và cap bốn tài sản thật.
- Thư viện owner-scoped bổ sung filter status/model/aspect/sort, trạng thái
  cancelled, grid/list lưu local, model/time, progress/error và link nhật ký cho
  mọi job. Không thêm retry/delete/bulk/template khi chưa có contract retention.
- Sửa lỗi tiền: estimate trước đây luôn hiện giá một video dù quantity=2. Nay
  hiện tổng hold server tính và thông báo settle theo token thật.
- Browser phát hiện preview ảnh blob bị CSP chặn. Sửa ảnh sang FileReader data
  URL; video/audio vẫn dùng blob theo `media-src`, không nới CSP nền tảng.
- Fixture cô lập 8112: Standard/Fast option đúng registry; quote ×2 = 94 credit;
  submit thật hai queued job nhưng không chạy worker/provider, credit 1000→906,
  asset history và ba link log; filter/cancelled empty; Upscale quote 3 credit.
  Desktop 1920 và mobile 390 PASS, drawer 375,2 px, không overflow, console
  0 error/0 warning, request app 200/206.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| Targeted Taovideo H26 | PASS 41 test |
| Vận hành/adaptive/layering | PASS 35 test; 1 warning TestClient cũ |
| `python tools/gate.py --quick` lượt đầu | FAIL 1 i18n mới; đã bọc `_t()` |
| `python tools/gate.py --quick` sau sửa | PASS 8/8 trong 25,6 giây |
| Playwright fixture 8112, 1920×1080 + 390×844 | PASS A-Z không provider; console/network sạch |
| `python tools/gate.py` lượt sạch | PASS 9/9 trong 1.616,1 giây; pytest 1.590,7 giây |

### Sự cố vận hành trong phiên

Tin nhắn mới và timeout của shell làm hai gate trước mất kênh theo dõi nhưng
không dừng pytest con, dẫn tới hai bộ regression tranh CPU. Đã kiểm command line
và quan hệ parent/PID, dừng đúng hai gate/pytest do phiên này tạo, đóng browser/
fixture 8112, xác nhận 0 gate process rồi chạy một lượt sạch duy nhất PASS.

### Quyết định mới

Không có. Thực thi Q79 và Decision Gate H13.taovideo; không đổi provider/cost
formula/worker và không mở tính năng lifecycle chưa có contract.

### Cách lùi lại

Revert commit H26.7. Không có migration; job/ledger/artifact đã có vẫn giữ nguyên.
Không xóa lịch sử hay output để rollback giao diện.

### Còn tồn đọng

- Chưa deploy; release vẫn khóa tới H26.12.
- Retry/delete/bulk/template tiếp tục DEFER theo retention/idempotency gate.
- Không chạy render BytePlus trong browser fixture; provider path đã được chốt
  bằng test registry/modelark và code worker hiện hữu, tránh đốt credit ngoài.

### Việc tiếp theo

1. H26.8 Phase 3.4: đổi tên + UX Prompt AI theo khảo sát read-only đã có.
2. Không chạy song song H26.9.

## 2026-08-08 — H26.6: Phase 3.2 Auto Sub Studio PASS

- **Mục tiêu:** loại version drift làm khách hàng thấy form AutoSub cũ, audit
  luồng A-Z và bổ sung lịch sử job/log phục vụ khôi phục, debug.
- **Hạng mục:** H26.6 — hoàn thành.
- **Trạng thái:** xong; chưa deploy.

### Đã làm

- Xác định root cause không nằm ở bundle: rollout thiếu/rỗng mặc định legacy dù
  AS9/Q50 đã chốt Studio public. Đổi default sang public; `off` và bundle thiếu
  vẫn rollback form cũ trong một release.
- Tách `renderJob` khỏi `auxJob`; render không còn tạo tiến độ giả cho công cụ
  diarize/translate. Trạng thái job hiển thị bằng tiếng Việt.
- Thêm `GET /autosubvideo/api/jobs` owner-only, lọc project, giới hạn kết quả;
  React Studio lưu danh sách, cập nhật khi poll và khôi phục render gần nhất sau
  reload. Mỗi row dẫn tới trang nhật ký job chung.
- Thêm thuộc tính download cho video/ASS/ZIP và test regression tương ứng.
- Browser fixture cô lập dùng video 10 giây thật: upload, import SRT, style,
  quote/hold 1 credit, reload recovery, worker FFmpeg/NVENC, download ZIP. ZIP
  mở được và đủ năm artifact. Desktop/mobile sạch, không overflow; console
  0 error/0 warning, không có request ứng dụng thất bại.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `npm test -- --run` | PASS 13 test |
| `npm run build` | PASS typecheck + Vite + build-meta |
| `python -m pytest tests/test_81_autosubvideo.py tests/test_103_autosub_projects.py tests/test_148_frontend_bundle.py -q` | PASS 44 test; 3 warning cũ |
| Playwright 1920×1080 + 390×844, render/download/reload | PASS; console sạch, không overflow |
| `python tools/gate.py --quick` | PASS 8/8 trong 28,7 giây |
| `python tools/gate.py` | PASS 9/9 trong 1.644,9 giây; pytest 1.617,2 giây |

### Quyết định mới

Không có. Thực thi Q50: Studio đã public sau AS9; biến rollout chỉ còn phục vụ
rollback có chủ ý, không phải điều kiện để khách hàng nhìn thấy bản đã phát hành.

### Cách lùi lại

Đặt `LTT_AUTOSUB_STUDIO_ROLLOUT=off` hoặc revert commit H26.6. Bundle thiếu tự
fail-safe về legacy. Không có migration dữ liệu.

### Còn tồn đọng

- Chưa deploy; release vẫn bị khóa tới H26.12 Phase 5.
- Hai warning thread giả trong test media và một deprecation TestClient là nợ
  cũ, không phát sinh từ H26.6.

### Việc tiếp theo

1. H26.7 Phase 3.3: đổi tên + UX Tạo Video Seedance, giữ provider/options thật.
2. Không chạy song song H26.8.

## 2026-08-08 — H26.5: Phase 3.1 Upscale Video PASS

- **Mục tiêu:** hoàn thiện trải nghiệm Upscale theo ảnh/yêu cầu đã khóa, loại bỏ
  UI nghiên cứu khỏi khách hàng và chứng minh hai worker dùng đúng hai GPU 16 GB.
- **Hạng mục:** H26.5 — hoàn thành.
- **Trạng thái:** xong; chưa deploy.

### Đã làm

- Đổi tên public thành **Upscale Video**. Giữ Fast/Quality, 1080p/1440p/4K,
  codec, FPS/audio, preview, chống rung, mượt chuyển động và batch là control có
  contract thật; `smooth_motion` luôn loại `preserve_fps` cả UI lẫn service.
- Rebuild compare bằng divider kéo được và semantic slider dùng chuột/pointer/
  phím; nguồn là master player, output theo play/pause/seek/rate/end và tự sửa
  drift trên 0,12 giây. Browser đo drift thật 0,014 giây.
- Queue có filter 5 trạng thái, sort mới/cũ, list/grid lưu theo browser, thumbnail
  video thật, chip trạng thái có chữ, download attachment owner-only. Watch Agent
  và telemetry chỉ admin; AI Detail/HDR và jargon nội bộ không còn ở customer UI.
- Sửa lỗi concurrency nghiêm trọng tìm được khi audit: worker đã lease GPU theo
  UUID nhưng Real-ESRGAN NCNN không nhận GPU, nên hai worker có thể cùng dùng GPU
  0. Nay UUID được map sang index vật lý cho `-g`; FFmpeg/NVENC nhận `gpu_env()`;
  GPU đã lease biến mất thì fail rõ ràng, không tự chạy nhầm card.
- Nâng tool smoke nhận GPU/preset/resolution/duration và thêm soak hai process có
  telemetry. Lưu ma trận tái lập trong `docs/UI_REDESIGN/upscalevideo/evidence/`
  và báo cáo `07_H26_GPU_BENCHMARK.md`; evidence không lưu đường dẫn cá nhân.
- Full video 10,054 giây: Fast GPU0/GPU1 lần lượt 21,270/20,867 giây; Quality
  327,454/309,938 giây. Mẫu ngắn 1440p/4K đều đúng resolution/FPS/audio. Soak
  đồng thời: hai card cùng đạt 100%, max 64°C, không thermal slowdown, hai output
  PASS. UI đổi mô tả Quality vì thực đo chậm khoảng 15 lần Fast trên clip này.
- Browser cuối customer/admin và mobile 390 px: customer không có Watch/research,
  admin có Watch/telemetry; touch target 44 px, không overflow; trạng thái VI/EN
  dịch đúng tại render; console 0 error/0 warning và request app 200/206.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `python -m pytest tests/test_82_upscalevideo.py tests/test_114_upscale_ui.py tests/test_115_upscale_feature_benchmark.py tests/test_116_upscale_motion_features.py tests/test_151_worker_gpu.py tests/test_157_upscale_h26.py -q` | PASS, 50 test; 1 warning deprecation TestClient |
| `python tools/upscale_gpu_smoke.py ...` — 12 case tuần tự | PASS 2 GPU × Fast/Quality × 1080p/1440p/4K; full + short evidence |
| `python tools/upscale_dual_gpu_soak.py ...` | PASS; 2 worker, max 64°C, không thermal slowdown |
| Playwright fixture `127.0.0.1:8111` customer/admin, 1920×1080 và 390×844 | PASS compare/filter/grid/upload quote/download/admin boundary/i18n; không overflow |
| Playwright console/network | 0 error, 0 warning; request ứng dụng 200/206 sau redirect locale |
| `python tools/gate.py --quick` lượt đầu | FAIL đúng 1 chuỗi GPU chưa bọc `_()`; đã sửa và dịch |
| `python tools/gate.py --quick` sau sửa | PASS 8/8 |
| `python tools/gate.py` | PASS 9/9 trong 1.663,3 giây; pytest PASS trong 1.637,3 giây |

### Quyết định mới

Không có. Thực thi Q47 và roadmap H26.5. Không đổi đơn giá Quality trong vé UI;
chênh lệch runtime/cost được đưa sang H26.11 để đo cost trên successful output.

### Cách lùi lại

Revert commit H26.5; không có migration dữ liệu. Khi lùi bản worker phải dừng
nhận job mới và drain/cancel + settle/refund job active trước. Không được quay về
bản không pin GPU trong lúc chạy hai worker.

### Còn tồn đọng

- Chưa deploy; release vẫn bị khóa tới H26.12 Phase 5.
- Progress message đã lưu trong job lịch sử giữ nguyên ngôn ngữ lúc worker ghi;
  nhãn trạng thái/ETA mới dịch tại render. Chuẩn hóa event msgid toàn bộ app nằm
  trong H24/H26.11, không sửa ngược log cũ.
- Price multiplier Quality hiện thấp hơn tỷ lệ runtime đo trên một clip; cần đo
  nhiều loại video và cost/output ở Phase 4 trước khi đổi giá sản phẩm.

### Việc tiếp theo

1. H26.6 Phase 3.2 AutoSub: đối chiếu bundle/hash/build-meta và nguyên nhân legacy.
2. Canary React Studio qua Upload → Transcribe → Style → Render → Download.
3. Giữ legacy rollback một release; không chạy song song H26.7.

## 2026-08-08 — H26.4: Phase 2 Marketplace/design system PASS

- **Mục tiêu:** chuẩn hóa marketplace theo lifecycle/capability và hợp nhất bề
  mặt Tạo ảnh AI/Thumbnail mà không phá executor, history hay link cũ.
- **Hạng mục:** H26.4 — hoàn thành.
- **Trạng thái:** xong; chưa deploy.

### Đã làm

- Mở rộng `AppManifest` bằng `capabilities` và `catalog_parent`; customer
  catalog/header không hiển thị child Thumbnail nhưng registry/job/backend vẫn
  nạp bình thường. Category, lifecycle, sort và workspace label được dựng từ
  manifest thay vì bảng app hardcode.
- Sửa root cause click card bị hiểu nhầm thành lọc category: listener chỉ còn
  gắn vào button filter. Toàn card trở thành một link có focus ring; bỏ icon
  cover lặp và metadata API/GPU hướng dev; filter capability/lifecycle độc lập.
- Thêm responsive 1/2/4/5 cột cho 390/768/1366/1920, touch target 44 px,
  lifecycle token, empty-state đúng thuộc tính `hidden` và mask chữ marketing
  có sẵn trong cover. Không tạo ảnh mới.
- Tạo ảnh AI có hai mode General/Thumbnail. `/taoanh/thumbnail` redirect 308
  sang `/thumbnail`; form `/thumbnail/queue`, job `thumbnail.generate`, history
  và output cũ được giữ. Browser đã nộp một job Thumbnail qua fake provider và
  nhận output thành công.
- Sửa lỗi build i18n tiềm ẩn: PO update không còn bỏ header làm catalog fuzzy;
  catalog English hiện 873 chuỗi, 0 thiếu, 0 fuzzy và `.mo` được compile thật.
- Full gate đầu phát hiện đúng một regression accessibility do đổi aria-label
  từ “nhóm” sang “thể loại”. Đã giữ nhãn UI “Thể loại” và dùng aria-label rõ
  nghĩa “Lọc theo nhóm ứng dụng”, thêm bản dịch và test lại trước full gate cuối.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `python -m pytest tests/test_60_app_registry.py tests/test_72_vanhanh.py tests/test_71_thumbnail.py tests/test_78_a1_migration.py tests/test_156_marketplace_h26.py -q` | PASS, 82 test |
| `python tools\gate.py --quick` trước fix i18n | FAIL đúng i18n ratchet; đã sửa PO header/fuzzy |
| `python tools\gate.py --quick` sau sửa | PASS 8/8 |
| Playwright fixture `127.0.0.1:8111` tại 390/768/1366/1920 | PASS 1/2/4/5 cột, không overflow, filter độc lập, card click/keyboard/focus, hai mode ảnh, legacy Thumbnail job/output |
| Playwright console/network | 0 error, 0 warning; request ứng dụng 200/304 |
| `python tools\gate.py` lượt đầu | FAIL 1 accessibility assertion; 2.539 pass, 8 skip, 23 subtest |
| `python -m pytest tests/test_109_home_shell_ui.py::test_home_filter_va_progress_co_accessible_state tests/test_156_marketplace_h26.py -q` | PASS, 7 test |
| `python tools\gate.py` sau sửa | PASS 9/9 trong 1.626,1 giây; pytest PASS trong 1.598,9 giây |

### Quyết định mới

Không có. Thực thi Q70, Q73 và Q78; Phase 2 chỉ hợp nhất presentation, chưa xóa
owner/executor Thumbnail.

### Cách lùi lại

Revert commit H26.4. Không có migration dữ liệu; route `/thumbnail`, job type,
history và output cũ vẫn còn nên catalog có thể trở lại hai entry mà không đổi dữ
liệu production.

### Còn tồn đọng

- H26.9 vẫn cần một history shell chung có filter theo mode; Phase 2 mới khóa
  entry point/tabs và compatibility contract.
- Chưa deploy; production chưa đổi giao diện.

### Việc tiếp theo

1. H26.5 Phase 3.1 Upscale: controls, compare sync, queue/download.
2. Benchmark/autotune từng GPU 16 GB; chỉ tăng concurrency sau soak không OOM.
3. Giữ AutoSub ở H26.6, không triển khai song song.

## 2026-08-08 — H26.3: Phase 1 Job History/Support PASS

- **Mục tiêu:** mọi tool tiếp tục dùng một nguồn job nhưng có lịch sử vòng đời,
  log debug, quyền support và giao diện theo dõi an toàn cho khách hàng.
- **Hạng mục:** H26.3 — hoàn thành.
- **Trạng thái:** xong; chưa deploy.

### Đã làm

- Thêm migration `JobEvent` append-only và ba cột trace trên `Job`:
  `correlation_id`, `retry_of_id`, `event_sequence`. Sequence cấp bằng update
  nguyên tử; unique sequence/event-key chặn trùng và đã đưa vào PostgreSQL
  restore drill.
- Xây `platform_core.job_events`: event customer/internal, idempotency key,
  allowlist metadata khách, redaction PII/secret đệ quy, size cap và purge
  customer 365 ngày/internal 30 ngày. Worker tự purge mỗi 6 giờ.
- Nối vòng đời dùng chung: submit, claim/start, progress, retry, orphan reclaim,
  cancel, done/error, resource wait, credit settle/refund. Settle/refund đặt tại
  `credit.py` nên mọi route tool hiện có đều ghi event, không chỉ global Jobs.
- Tạo History read contract/API chỉ trả trường an toàn, không trả `params`,
  `result`, `error` hoặc event nội bộ; hỗ trợ owner isolation và cursor.
- Nâng Jobs toàn cục: filter app/status/date, cursor, timeline cập nhật HTMX,
  retry lineage, artifact opaque download, cancel/retry và Support ID.
- Thêm operator endpoints cho event kỹ thuật đã redacted và metrics: success
  rate, queue wait/runtime P50/P95, retry, refund, stale job, event-write failure.
- Bổ sung bản dịch English. Browser vòng đầu phát hiện message bị đóng băng theo
  locale lúc ghi; đã đổi sang lưu msgid bằng `N_()` rồi dịch khi render.
- Browser cũng dẫn tới việc dời event settle/refund vào tầng credit chung, nhờ
  vậy cancel từ Upscale/AutoSub/global Jobs đều có lịch sử hoàn tiền nhất quán.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `python -m pytest tests/test_68_credit.py tests/test_67_hang_doi_job.py tests/test_69_web_jobs.py tests/test_107_jobs_ui.py tests/test_151_job_events.py -q` | PASS, 50 test |
| `python -m pytest tests/test_155_ommi_metrics.py::test_moi_rang_buoc_unique_song_con_deu_nam_trong_drill tests/test_151_job_events.py -q` | PASS, 8 test |
| `python tools\gate.py --quick` | PASS 8/8 |
| Alembic SQLite mới: `upgrade head -> downgrade e3f4a5b6c7d8 -> upgrade head` | PASS restore migration |
| Playwright fixture `127.0.0.1:8111`, desktop 1366x900 + mobile 390x844 | PASS create image job, app/status/date filter, customer timeline/API, Support ID, artifact, operator event+metrics; user khác 404; mobile không overflow |
| Playwright phiên sạch sau negative ownership flow | console 0 error/0 warning; không có failed application request |
| `python tools\gate.py` lượt đầu | FAIL đúng 1 test restore drill: thiếu hai tên UNIQUE mới; 2531 pass |
| `python tools\gate.py` sau sửa restore drill | PASS 9/9; pytest PASS trong 1.636,9 giây |

### Quyết định mới

Không có. Thực thi đúng Q75 (365/30 ngày) và Q76 (timeline khách đã sanitize,
technical log chỉ operator/support). Artifact và credit ledger không bị purge
theo policy event.

### Cách lùi lại

Revert commit H26.3 để UI/service quay lại đọc snapshot `Job`. Chỉ chạy Alembic
downgrade khi bảng `job_events` chưa chứa dữ liệu cần giữ; nếu đã có production
data thì giữ migration/table và tắt phần đọc mới, không xoá lịch sử support.

### Còn tồn đọng

- Chưa chạy PostgreSQL restore drill thật vì hạng mục này không có mật khẩu/
  phiên PostgreSQL superuser; SQLite migration restore và contract test đã PASS.
- Chưa deploy; production chưa đổi schema/runtime.
- SLO/ngưỡng alert chính thức và load/soak nằm ở H26.11 Phase 4.

### Việc tiếp theo

1. H26.4 Phase 2: Marketplace card/taxonomy/lifecycle/design system.
2. Hợp nhất bề mặt Thumbnail vào Tạo ảnh AI nhưng giữ job/history/redirect cũ.
3. Chỉ chuyển Upscale Phase 3.1 sau browser matrix Phase 2 PASS.

## 2026-08-08 — H26.2: Phase 0 surface/lifecycle PASS

- **Mục tiêu:** bỏ/ẩn ba tool theo quyết định A mà không phá runtime, workflow
  cũ hay khả năng debug.
- **Hạng mục:** H26.2 — hoàn thành.
- **Trạng thái:** xong; chưa deploy.

### Đã làm

- Mở rộng `AppManifest` bằng enum `surface=customer|admin|runtime` và
  `lifecycle=released|development|maintenance|internal|retired`, validate fail
  sớm và một helper visibility dùng chung cho catalog/header/sidebar.
- Kịch bản YouTube thành `runtime/retired`, landing 308 sang Agent Canvas;
  `text.script` vẫn resolve được cho workflow cũ nhưng `customer_visible=False`
  nên không còn trong palette khách. `text.generate` tiếp tục phục vụ block Text.
- Media Tools thành `runtime/internal`, landing 308 sang Canvas; toàn bộ asset,
  audio và transform ToolSpec vẫn giữ nguyên.
- Demo thành `admin/internal`; user thường gõ URL nhận 404, database admin vẫn
  thấy card và chạy được pipeline test.
- Gắn lifecycle thật cho toàn portfolio theo Q73/Q78 và build lại bundle Canvas.
- Bổ sung test registry, surface, access-control, soft-retire palette và cập
  nhật fixture browser có operator riêng.
- Full gate phát hiện lỗi baseline WEB-001: `route-map.json` có canonical
  WordPress `/en/` nhưng không có file legacy. Đã khai tường minh
  `source_exists:false`; production audit vẫn giữ target, test coverage legacy
  không còn coi route ảo là file.
- Hai lượt gate đầu bị shell timeout để lại hai pytest chạy song song. Đã xác
  định và dừng đúng bốn PID do phiên này tạo, không đụng dịch vụ/BOT khác; lượt
  cuối chạy một tiến trình và PASS.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `python -m pytest -q tests/test_60_app_registry.py tests/test_66_phan_quyen_app.py tests/test_69_web_jobs.py tests/test_97_agent_workflow_api.py` | PASS, 64 test |
| `npm test -- --run tests/presentationAdapter.test.ts` tại `frontend/agent-canvas` | PASS, 4 test |
| `npm run build` tại `frontend/agent-canvas` | PASS; typecheck + Vite build, bundle mới được ghi vào `server/static/agent-canvas` |
| `python tools\gate.py --quick` | PASS 8/8 trong 27,8 giây |
| Playwright server cô lập `127.0.0.1:8111` | PASS anonymous/customer/operator; customer Demo 404; Kịch bản/Media 308; palette không còn Kịch bản; console 0 error/0 warning; request app 200 sau locale redirect |
| `python -m pytest -q tests/test_125_website_route_contract.py` | PASS, 3 test |
| `php deploy/wordpress/tests/route-contract-test.php` | Chưa chạy: máy không có PHP CLI |
| `python tools\gate.py` | PASS 9/9; pytest PASS trong 1.509,3 giây |

### Quyết định mới

Không có. Triển khai đúng Q69-Q73 và Q78 đã khóa ở H26.1; sửa WEB-001 chỉ làm
rõ dữ kiện nguồn tồn tại, không đổi ownership hay canonical URL.

### Cách lùi lại

Revert commit H26.2. Không có migration dữ liệu; bundle cũ quay lại cùng commit.
Runtime Kịch bản/Media chưa bị xoá nên rollback không cần khôi phục dữ liệu.

### Còn tồn đọng

- H26.3 Phase 1 JobEvent/History/log chung chưa triển khai.
- PHP contract test chưa chạy vì thiếu executable; không chặn Phase 0 app.
- Chưa deploy; production chưa thay đổi.

### Việc tiếp theo

1. Thiết kế migration `JobEvent`, redaction và retention theo Q75-Q76.
2. Viết service append event + lifecycle coverage trước khi nối UI History.
3. Chỉ chuyển Phase 2 sau khi Phase 1 full gate và browser ownership PASS.

## 2026-08-08 — H26.1: khóa decision gate

- **Mục tiêu:** chuyển 12 lựa chọn audit thành quyết định có hiệu lực trước BUILD.
- **Hạng mục:** H26.1 — hoàn thành.
- **Trạng thái:** xong; chưa sửa runtime ở checkpoint này.

### Đã làm

Chủ sản phẩm chọn toàn bộ phương án A. Đã ghi Q69-Q80: soft-retire, redirect 308,
Demo admin-only, Media runtime-only, lifecycle trung thực, hai trục filter,
retention/log theo role, Prompt single-user, Socialbot frozen, thứ tự H26 và
AutoSub canary.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `python tools\scan_source_secrets.py` | PASS, 0 finding trên 1.053 file |

### Cách lùi lại

Revert commit H26.1 trước khi có runtime phụ thuộc Q69-Q80.

### Việc tiếp theo

H26.2 Phase 0 audience/lifecycle và soft-retire ba bề mặt.

## 2026-08-08 — H26.0: audit portfolio và lập roadmap update app

- **Mục tiêu:** áp dụng `quy_tac_audit.md` cho kho ứng dụng, ba tool cần bỏ/ẩn,
  lịch sử job/log và bộ ảnh/MoTa update.
- **Hạng mục:** H26.0 — hoàn thành phần audit/plan; chưa BUILD, chưa deploy.
- **Trạng thái:** xong.

### Đã làm

- Đọc toàn bộ 10 folder, 7 file mô tả có nội dung/mẫu và 8 ảnh trong
  `AppLttStudio_Update_08082025`; các folder trống được ghi UNKNOWN.
- Kiểm browser local 8100: catalog public render thật, console 0 error/0 warning,
  không có failed request bất ngờ; Kịch bản YouTube vẫn public.
- Phát hiện không thể xóa thẳng Kịch bản/Media: chúng sở hữu các ToolSpec Text,
  asset, audio và transform của Agent. Chọn đưa ra decision gate soft-retire.
- Phát hiện `Job` chỉ lưu snapshot hiện tại, chưa có durable event timeline dùng
  chung. Roadmap dùng `JobEvent`, không nhân bảng job theo app.
- Xác định AutoSub production mặc định rơi về legacy nếu thiếu
  `LTT_AUTOSUB_STUDIO_ROLLOUT=public`.
- Đo hardware thật: 2 RTX 5060 Ti, mỗi card 16.311 MiB; ghi rõ không cộng thành
  một pool VRAM 32 GB cho một job.
- Tạo hồ sơ 8 phần tại
  `docs/APP_AUDIT/platform/2026-08-08-app-update/`; baseline tạm
  `Q58 · M UNKNOWN · E31 · G4/G8 FAIL`.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| Playwright local 8100 catalog + console/requests | PASS trong phạm vi public; 0 console error/warning, 0 failed request bất ngờ |
| `python tools\gate.py --quick` | PASS 8/8 bước trong 26,8 giây: secret, contract, undefined names, silent-except, i18n và 3 frontend |

### Quyết định mới

Chưa có quyết định nền mới: 12 lựa chọn đang chờ khóa trong audit dossier, không
tự ghi thành Q khi chủ sản phẩm chưa duyệt.

### Cách lùi lại

Revert commit tài liệu H26.0; không có migration/runtime/deploy cần lùi.

### Còn tồn đọng

H26.1-H26.12; competitor benchmark và authenticated A-Z từng app chưa chạy.

### Việc tiếp theo

1. Khóa decision gate H26.1 theo phương án khuyến nghị.
2. Thực hiện Phase 0 soft-retire/visibility và browser regression.
3. Chỉ sau Phase 0 PASS mới xây JobEvent/History chung.

## 2026-08-07 — Nhân viên không tạo được tài khoản: trần 3/IP/ngày

- **Trạng thái:** xong (đã deploy 17:59)

### Hiện tượng

Nhân viên vào tạo tài khoản để test, được vài người thì báo *"Đã đạt giới hạn tạo
tài khoản hôm nay. Thử lại sau."*

### Nguyên nhân

`platform_core/antifraud.py:29` — `GIOI_HAN_IP_MOI_NGAY` mặc định **3**, và
`app.env` chưa đặt `LTT_MAX_DANGKY_IP_NGAY` nên đang chạy mặc định.

Đo trên CSDL production:

```
14.177.12.60     3 tai khoan   13:24 -> 17:43   <- cham tran
27.79.167.173    1 tai khoan   21:39
```

Nhân viên ngồi **cùng mạng văn phòng** nên ra Internet bằng **một IP công cộng**.
Người thứ 4 bị chặn.

**Cơ chế chạy đúng, nhưng giả định sai.** Nó xây để chặn một người tạo hàng loạt
tài khoản ăn credit dùng thử (mỗi tài khoản 20 credit sau xác thực email) — giả
định "nhiều người lạ, mỗi người một IP". Giả định đó sai với một đội sau một NAT.

### Đã làm

`LTT_MAX_DANGKY_IP_NGAY=5` vào `app.env` (chủ sản phẩm chốt), chạy lại bộ cài.

⚠️ **NSSM giữ bản chụp `app.env`** — sửa file thôi thì dịch vụ vẫn đọc giá trị cũ.
Đã xác minh sau deploy: `nssm get AppEnvironmentExtra` có dòng đó, và ứng dụng
đọc ra `GIOI_HAN_IP_MOI_NGAY = 5`.

### Giới hạn của cách sửa này — đã nói rõ với chủ sản phẩm

- IP văn phòng **đã dùng 3/5 slot**, nên hôm nay chỉ thêm được **2 tài khoản**.
  Slot đầu mở lại 13:24 ngày mai (cửa sổ 24 giờ **trượt**, không phải theo ngày).
- Quá 5 người trên cùng mạng thì vẫn chặn.
- Trần này nới cho **cả Internet**, không riêng văn phòng.

### Còn tồn đọng

Phương án đúng hình dạng vấn đề là **miễn trừ theo IP văn phòng** (mọi IP khác
giữ trần cũ), hoặc **admin tạo tài khoản thay** thay vì tự đăng ký. Chưa làm.

---

---

## 2026-08-06 — Đăng nhập: bỏ khoá tài khoản, thay bằng leo thang thách đố

- **Mục tiêu:** vá chỗ hở ở `/login` cho đúng, trước khi sang việc khác.
- **Trạng thái:** xong

### Bài toán thật, khác với bài toán tôi tưởng

Ban đầu tôi đề xuất "thêm Turnstile cho `/login` vì `/register` có mà login
không có". **Đề xuất đó sai chỗ.** Đọc mã thì `/login` đã có CSRF, đo hai chiều
theo IP *và* theo tài khoản, IP thật sau Cloudflare, và bắt buộc xác thực email.
Nó không hề trống.

Lỗ thật nằm ở chỗ khác, và nặng hơn:

**1. Khoá theo tài khoản chính là một lỗ từ chối dịch vụ.** `lim.allow(acct_key)`
chạy **trước** khi kiểm mật khẩu, nên mọi lần thử mang email đó đều tiêu hạn mức
của tài khoản đó. Ai biết email của khách chỉ cần bắn 5 lần thử rác mỗi phút là
khách **không bao giờ đăng nhập được**, dù gõ đúng mật khẩu. Không cần biết mật
khẩu, không cần botnet.

**2. Trần 5/60 giây theo IP quá chặt với CGNAT.** Nhà mạng di động Việt Nam dùng
CGNAT — rất nhiều người thật chung một IP công cộng. Vài người gõ nhầm là cả
nhóm bị khoá.

**3. Giả định thiết kế đã hết hạn.** Chú thích module ghi rõ nó dành cho "bảng
điều khiển một người dùng, không phải dịch vụ nhiều người dùng công khai". Từ hôm
nay đã có khách trả tiền.

### Nghiên cứu

OWASP Credential Stuffing Prevention + Authentication Cheat Sheet + Top 10:2025
A07. Điểm chốt: lockout "có thể vô tình thành tấn công từ chối dịch vụ nhắm vào
người dùng hợp lệ"; nên dùng **đường cong lùi dần** và **thách đố sau một ngưỡng
thất bại** thay vì khoá; CAPTCHA nên "chỉ bật cho lần đăng nhập khả nghi"; và
chặn theo IP "không bao giờ được là phòng thủ duy nhất" vì bộ công cụ stuffing đi
qua mạng proxy.

### Thiết kế đã chọn — leo thang, không khoá

| Số lần sai | Trước | Sau |
|---|---|---|
| 1–2 | cho thử | cho thử |
| ≥3 (IP **hoặc** tài khoản) | — | **hiện Turnstile** |
| ≥5 theo tài khoản | **khoá cứng 429** | ~~bỏ~~ — chính là lỗ DoS |
| ≥20 theo IP | — | 429 |

Tính chất then chốt: người thật quên mật khẩu chỉ mất một cú click (Turnstile
thường vô hình); bot không giải được. **Tài khoản không còn bị người khác khoá.**

Giải hụt thách đố **cố ý không tính** là một lần thử — nếu tính, người thật giải
hụt vài lần sẽ tự đẩy mình tới trần chặn cứng. Bot chẳng lợi gì vì không qua
được thách đố thì không tới bước kiểm mật khẩu.

**Đường lui khi thiếu Turnstile.** Bản đầu của tôi có lỗ: không cấu hình Turnstile
thì không có gì để leo thang tới, nên trần tự nới từ 5 lên 20 — quên một biến môi
trường = nới phòng thủ gấp bốn mà không ai hay. Một test cũ (`test_37`) đổ và chỉ
đúng chỗ đó. Sửa: thiếu Turnstile thì lùi về trần 5 như cũ.

Gate bắt tiếp một test nữa: `test_72::test_khoa_theo_tai_khoan_du_khac_ip` —
khoá đúng cái hành vi vừa bỏ. Nó có lý riêng: dò một tài khoản từ **nhiều IP** là
thứ đo-theo-IP không thấy được. Nên thiết kế cuối là **hai chế độ**:

| | Có Turnstile (production) | Không Turnstile (dev/test) |
|---|---|---|
| Theo tài khoản | chỉ leo thang sang thách đố | khoá cứng ở 5 (như cũ) |
| Theo IP | chặn cứng ở 20 | chặn cứng ở 5 |
| Lỗ DoS khoá tài khoản | **không còn** | vẫn còn (chấp nhận) |

Mất thách đố thì khoá tài khoản là đường phòng thủ **duy nhất** còn lại — thà
giữ phòng thủ thô còn hơn không có gì. Nhờ vậy `test_37` và `test_72` **đều
không phải sửa**: chúng chạy ở chế độ không-Turnstile và giữ nguyên kỳ vọng cũ.

Tức Turnstile giờ là **cấu kiện chịu lực**, không còn là thứ trang trí cho trang
đăng ký. Production bắt buộc phải có nó.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `pytest test_157` (mới, 13) | 13 pass |
| `pytest test_157 + test_37 + test_64 + test_86` | 57 pass, `test_37` **không phải sửa** |
| Trồng lại hành vi khoá cũ | **3 fail** đúng chỗ |
| `python tools/gate.py` | (ghi khi xong) |

⚠️ Bài học về test: bản trồng bug **đầu tiên** của tôi vẫn để test DoS xanh — vì
nó chưa tái hiện đúng mã cũ (mã cũ đếm *mọi* lần thử **trước** thách đố, bản
trồng thì không). Suýt nữa nhận một test trông như canh lỗ DoS nhưng thực ra
không canh gì. Trồng bug phải trung thực với mã cũ, không chỉ "na ná".

### Còn tồn đọng

- Bộ đếm vẫn trong bộ nhớ. Chỉ đúng khi web chạy **một** tiến trình; thêm
  `--workers N` sẽ chia bộ đếm thành N phần và **nới trần lên N lần một cách
  lặng lẽ**. Đã ghi cảnh báo trong `server/auth/rate_limit.py`. Khi cần nhiều
  tiến trình web thì phải chuyển bộ đếm xuống PostgreSQL.
- MFA là phòng thủ mạnh nhất theo OWASP (Microsoft: chặn 99,9% vụ chiếm tài
  khoản) — **chưa làm**, phạm vi lớn (TOTP + mã khôi phục + giao diện).
- Kiểm mật khẩu rò rỉ (Pwned Passwords, k-anonymity) lúc đăng ký — chưa làm.

---

## 2026-08-06 — Đồng tiền thật đầu tiên, và con bug nó lôi ra

- **Mục tiêu:** deploy H19/H22/H23, đăng ký webhook PayOS, chạy một giao dịch thật.
- **Hạng mục:** H9 — hoàn thành (lần đầu có tiền thật chạy hết vòng)
- **Trạng thái:** xong

### Đã làm

**Deploy hai nhịp.** Nhịp 1a (`LTT_WORKER_PROCESSES=1`) để migration và mã mới
lên trước mà worker vẫn một tiến trình như cũ — nếu hỏng thì biết chắc lỗi
không đến từ đa tiến trình. Ba migration vào CSDL production (`gpu_leases` +
`uq_gpu_lease_host_uuid`, `ommi_scene_version.feedback`,
`ommi_meta_prompt.deprecated_at/note`), head `e5f6a4b5c6d7`. Nhịp 1b bỏ biến
đó, worker tự chọn theo số GPU → log `chay 2 tien trinh worker song song`, cả
hai PID sống.

**Webhook PayOS.** Gọi `POST api-merchant.payos.vn/confirm-webhook`, trả
`code: "00" success` — PayOS đã gọi thử vào `https://app.lttstudios.com/webhooks/payment/payos`
và nhận phản hồi hợp lệ. Trước deploy endpoint trả 503 (`GatewayChuaCauHinh`),
sau deploy trả 400 (`ChuKyKhongHopLe`) cho POST rỗng — đó là bằng chứng ba khoá
đã thực sự nạp vào tiến trình dịch vụ, không chỉ nằm trong `app.env`. NSSM giữ
**bản chụp** env nên chỉ chạy lại bộ cài mới đồng bộ.

**Giao dịch thật 50.000đ** (gói rẻ nhất; không có gói 10.000đ như dự tính ban
đầu). Đơn `#7565780319`: tạo 21:43:15 → `paid` + `credited=True` lúc 21:44:53.
Webhook về sau ~40 giây. Sổ credit thêm đúng **một** bút toán `topup +500`,
số dư 20 → 520. `gateway_ref` đổi từ mã link PayOS sang mã ngân hàng
`FT26218577466709`.

**Bug lộ ra ngay sau đó — và chỉ giao dịch thật mới lộ được.** Trả tiền xong,
khách bị ném vào một trang trắng có đúng một dòng chữ *"Không thấy đơn."*
Nguyên nhân ở `server/routes/billing.py`: `return_url` gửi cho PayOS là chuỗi
`f"{base}/nap/don/PLACEHOLDER"`, kèm chú thích tự trấn an *"đơn giản: bỏ qua,
PayOS vẫn về trang chủ"*. Giả định đó sai — cổng đưa người dùng về **đúng** URL
nhận được, kể cả khi URL đó vô nghĩa. Không test nào bắt được vì không test nào
đi qua cổng thật.

Sửa ba lớp:
1. `platform_core.billing.tao_don` thay `{order_id}` bằng id thật sau `flush()`
   (id chỉ có sau khi tạo đơn, nhưng URL phải gửi ngay lúc gọi cổng);
2. `/nap/don/{id}` hụt id thì tra tiếp bằng `?orderCode=` cổng đính kèm — cứu
   được các đơn đã tạo bằng URL hỏng;
3. trang hụt đơn thành trang thật (`nap_khong_thay.html`) mở đầu bằng câu người
   vừa mất tiền cần đọc: **tiền không mất, credit cộng theo báo có của ngân
   hàng chứ không theo trang này**.

**Giao diện phản hồi.** Trạng thái `paid` thành biên lai đủ (credit đã cộng, số
dư mới, thời điểm, mã giao dịch để đối soát) thay cho một dòng alert. Thêm
trạng thái *"đang xác nhận với ngân hàng"* riêng cho lúc vừa từ cổng về mà
webhook chưa tới — 40 giây im lặng là chỗ khách dễ tưởng hỏng rồi **chuyển tiền
lần hai**. Đơn đã trả thì giấu nút mở cổng, cùng lý do.

**Một lỗ quyền tiện tay bịt.** Cả hai handler đơn viết
`if order is None or (u is not None and order.user_id != u.id)` — khi `u is
None` thì vế kiểm chủ sở hữu bị bỏ qua, tức một phiên không có người dùng trong
CSDL xem được đơn của bất kỳ ai. Đổi thành `u is None` → từ chối.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `pytest tests/test_156_nap_trang_phan_hoi.py` | 11 pass |
| `pytest tests/test_156 + test_76_billing.py` | 28 pass |
| Trồng lại bug cũ rồi chạy test_156 | **2 fail** đúng chỗ — test có tính bác bỏ |
| `python tools/gate.py` | (ghi kết quả khi xong) |

Bánh cóc `test_ma_nguon_khong_con_chuoi_giu_cho` soi bằng **AST**, chỉ xét giá
trị truyền vào `return_url`/`cancel_url`. Bản đầu tìm chuỗi cả file thì dính
vào chính đoạn chú thích kể lại con bug này — báo động giả vĩnh viễn.

### Quyết định mới

**KHÔNG bật Bot Fight Mode.** Bản Free không cho loại trừ theo đường dẫn, nên nó
áp lên cả `POST /webhooks/payment/payos` — cú gọi server-tới-server không có dấu
vết trình duyệt, đúng hình dạng bị chặn. Hỏng ở đó nghĩa là **khách trả tiền
nhưng không nhận credit**, và chỉ lộ khi có người khiếu nại. Đổi lại nó bảo vệ
gần như bằng không, vì endpoint đã tự kiểm chữ ký HMAC.

Thay bằng **WAF custom rule** (chủ sản phẩm chốt 2026-08-06):

```
Ten       : Managed Challenge - trang xac thuc chua co Turnstile
Bieu thuc : (http.request.uri.path in {"/login" "/forgot-password" "/reset-password"})
Hanh dong : Managed Challenge          Trang thai: Active
```

Đường dẫn lấy từ mã nguồn chứ không đoán — `/register` và `/forgot-password`, KHÔNG
phải `/dang-ky`, `/quen-mat-khau`. Và **`/register` cố ý nằm ngoài luật vì nó đã
có Turnstile; `/login` thì KHÔNG có** — đó chính là chỗ hở, mà login mới là đích
của tấn công dò mật khẩu. (Đáng cân nhắc bổ sung Turnstile cho `/login`.)

Đo sau khi bật: `/login` và `/forgot-password` trả 403 (trang thách đố) cho
client không phải trình duyệt — không đều, vì Managed Challenge có tính thích
ứng. Trình duyệt thật vào `/login` bình thường, form nguyên vẹn, **không thấy
trang thách đố**. `/`, `/register`, `/nap`, `/health/ready` không đổi. Quan
trọng nhất: `POST /webhooks/payment/payos` vẫn trả **400** — tức qua được WAF và
tới ứng dụng.

### Cách lùi lại

Mã: `git revert` commit của phiên này. Deploy: `C:\LTTPlatform\app.previous\`.
CSDL: `C:\LTTPlatform\backups\ltt_data_20260806_204202.zip` (chụp trước deploy).
Env: `C:\LTTPlatform\secrets\app.env.bak-1b`.

### Còn tồn đọng

- Bản vá trang phản hồi **chưa deploy** — production vẫn đang chạy bản có bug.
- Bot Fight Mode chờ quyết.
- Đơn `#5864454177` (02/08, pending, `checkout_url` rỗng) là rác từ thời chưa có
  khoá; `het_han_don()` sẽ dọn.

### Việc tiếp theo

1. Gate xanh → deploy bản vá → kiểm trên URL công khai bằng trình duyệt thật.
2. Chốt Bot Fight Mode hoặc WAF theo đường dẫn.
3. H21.8 (cần 5 người dùng thật), H15.S15, H13.taovideo R8–R10, H19.10.

---

## 2026-08-06 — Kích hoạt WordPress integration DEFERRED-WP-001

- **Mục tiêu:** kích hoạt plugin từ nguồn chân lý trong repo, khép 29 alias
  `.html` cũ và nối CTA marketing sang app mà không chạm dữ liệu WordPress hay
  hai OAuth callback.
- **Backup trước thay đổi:** 7.779 file/501,57 MiB; database gzip 21 bảng,
  13.603 dòng; đã kiểm gzip/DDL/INSERT và ghi manifest cùng danh sách 7 plugin
  active. Backup nằm ngoài repo trong vùng local giới hạn ACL.
- **Deploy:** plugin 1.0.2 từ commit `5671435`; ZIP có đúng thư mục gốc
  `lttstudios-integration/`; SHA-256 package
  `ee76aa6d991c72ae07ea719bae86bc3693733310979709eb2f44463bf1b74c29`;
  SHA-256 file PHP local/host cùng là
  `dc0666098e2c66793e7e68607dc389c7ff564c266532cf37985a265c0ca84413`.
  Upload vào thư mục incoming rồi đổi tên atomically; purge object cache và
  LiteSpeed thành công.
- **Audit định lượng:** `python tools/audit_public_web.py` từ **30 fail / 0
  pass** về **0 fail**. Ba alias trình duyệt `/about.html`, `/products.html`,
  `/legal/privacy.html` chuyển tới pretty URL và trả 200.
- **Trình duyệt thật:** Chromium desktop 1366×900 và mobile 390×844 đều trang
  chủ 200, không tràn ngang, console 0 lỗi, request hỏng 0. CTA Header V2 tới
  `https://app.lttstudios.com/`; trang login app 200 và form hiển thị.
- **OAuth:** `/auth/fb-callback.html` và `/legal/callback.html` giữ nguyên HTTP
  200 và SHA-256 so với trước deploy.
- **Gate:** PHP lint, contract test 3 pass, secret scan và `tools/gate.py
  --quick` 7/7 pass. Full gate trong venv kiểm tra độc lập không collect được
  do thiếu dependency runtime của toàn control-plane; đây là thiếu môi trường,
  không phải lỗi plugin, và các gate bắt buộc riêng của Q60 đều pass.
- **Rollback:** đổi thư mục plugin hiện tại ra ngoài và đưa
  `lttstudios-integration.__rollback-658ad41-20260806` trở lại tên
  `lttstudios-integration`, sau đó purge cache. Plugin không tạo bảng/option và
  không sửa bài viết/người dùng.

---

## 2026-08-06 — Rà soát hệ điều hành: chốt bố cục mã nguồn, tách 2 file route khổng lồ, 2 lỗi thật

- **Mục tiêu:** thực hiện các đề xuất của đợt audit control-plane 2026-08-06
  (`docs/APP_AUDIT/control-plane/2026-08-06/`).
- **Trạng thái:** 4 commit. `tools/gate.py` xanh. Đã kiểm trình duyệt thật.
  **Chưa deploy.**

### Vấn đề gốc: hợp đồng app chưa từng nói logic nghiệp vụ nằm ở đâu

`manifest.py` / `routes.py` / `jobs.py` đều có quy định. Nhưng không chỗ nào nói
quy tắc nghiệp vụ đặt ở đâu. Đo được hậu quả: 5 app dùng `features.py`, 5 app
dùng `cost.py`, 1 app dùng `services/`, còn lại nhét thẳng vào route. Không có
chỗ mặc định thì route là chỗ để mọi thứ rơi vào.

Chốt vào **`AGENTS.md` mục 8** (mới) + bản rút gọn trong `CLAUDE.md`:
`routes.py` chỉ lo HTTP; nghiệp vụ ở `services/` (nhiều miền) hoặc `features.py`
(một miền); trần **900 dòng / 30 handler** do `tools/lint_app_contract.py` gác.
Ngưỡng chọn theo phân bố thật (file route lớn nhất còn đọc được là ~870 dòng),
không theo cảm tính.

Rồi tách hai file vi phạm:

| File | Trước | Sau | Route |
|---|---:|---|---:|
| `apps/prompt_ai_ommi/routes.py` | 1.799 dòng / 64 handler | 9 module, lớn nhất 551 | 64 → 64 |
| `apps/agent/routes.py` | 1.308 dòng / 48 handler | 9 module, lớn nhất 237 | 48 → 48 |

Với agent, so khớp `(path, method, tên handler)` với bản HEAD: **giống hệt**.
`lint_app_contract`: lần đầu ERROR 0, **WARN 0**.

### Hai lỗi thật, cả hai đều loại "test không thể bắt"

**1. `POST /upscalevideo/queue` gọi `get_session()` mà không import.** Đường nộp
việc **chính** của app đó. Mọi lần nộp đều NameError → 500. Lỗi nằm trong repo
từ 2026-08-02 (3ea1f2c) và **không test nào chạm route đó**.

Sửa xong thì chặn cả lớp: `tools/check_undefined_names.py` vào gate. Test không
phủ hết mọi nhánh route, nhưng một cái tên chưa định nghĩa thì đọc tĩnh là thấy.
Đã chứng minh công cụ bắt được bằng cách trồng lại đúng lỗi đó.

**2. Presign R2 nuốt lỗi thật.** 15 chỗ gọi `url_for`/`put_url` đều bọc
`except Exception:  # noqa: BLE001`, kèm chú thích *"local storage has no direct
URL"*. Chú thích **sai**: backend cục bộ **trả None**, không ném. Nên khối except
ấy không bảo vệ thứ nó tự nhận — nó chỉ giấu lỗi thật của R2 (thiếu cấu hình,
sai khoá, mất mạng) rồi lặng lẽ quay về phục vụ file qua tunnel. Đúng thứ H10
sinh ra để tránh: mọi thứ vẫn "chạy" cho tới khi ai đó tải file lớn và đâm trần
100 MB của Cloudflare, không log nào chỉ ra vì sao.

Thêm `Storage.try_url_for()` / `try_put_url()`: vẫn degrade để sự cố tạm thời
không làm vỡ trang, **nhưng ghi log mức exception**. Lợi ích thấy ngay trong
cùng phiên: gate đỏ một test, và chính dòng log mới chỉ thẳng ra nguyên nhân —
stub trong `test_103` là `lambda _key:` không nhận `ttl_s` trong khi chữ ký thật
có. Stub sai hình đó vẫn xanh suốt vì route gọi không truyền `ttl_s`.

### Gom việc dùng chung về nền tảng

- **`platform_core/frontend_bundle.py`** — ba app đều tự đọc manifest của Vite
  và tự neo gốc repo bằng `Path(__file__).parents[2]`. Đếm cấp thư mục sai ngay
  khi file đổi chỗ: lúc tách package, file sâu thêm một cấp, `parents[2]` trỏ
  vào `apps/`, manifest không đọc được, và trang **vẫn trả 200** với vỏ trống.
  Nay neo bằng tên thư mục.
- **`core.runtime_paths` → `platform_core/runtime_paths.py`.** Đây là sợi dây
  **duy nhất** khiến mọi app dính `core/` (15.668 dòng legacy FB/TikTok). Cắt
  xong: `platform_core/` và toàn bộ app **không còn dây nào** tới `core/`.
  Production an toàn vì bộ cài đặt `LTT_DATA_DIR`/`LTT_SECRETS_DIR`/`LTT_LOGS_DIR`
  ghi đè, và đường fallback mới vẫn cho đúng gốc cũ (đã kiểm cả hai nhánh).

### Bản đồ `core/` — hạng mục #8

`docs/APP_AUDIT/control-plane/2026-08-06/04_BAN_DO_CORE.md`. Đo khả đạt bắc cầu
từ điểm vào thật, **cố ý loại `tests/`** (module chỉ test dùng là code chết được
test của chính nó giữ cho ấm):

| Nhóm | Module | Dòng |
|---|---:|---:|
| Mọi app đang bán dùng | 1 | 89 |
| Chỉ qua `server.app`/`worker_main` (bảng điều khiển FB/TikTok cũ) | 64 | 15.044 |
| Không ai gọi tới | 5 | 535 |

**99,4% của `core/` không phục vụ app nào đang bán.** Và 43/69 = **62% route
công khai** thuộc sản phẩm đã đóng băng, gắn vô điều kiện trong `server/app.py`.
Đề xuất C1–C4 ghi trong hồ sơ; **C2 (đưa 43 route legacy vào cờ tắt/bật) cần
chủ sản phẩm quyết** vì tắt là bảng điều khiển cũ biến mất khỏi web.

### Kiểm thật

- `python tools\gate.py` — quét bí mật · lint hợp đồng · tên chưa định nghĩa ·
  3 bộ test frontend · pytest. **2.280 pass / 8 skip.**
- Trình duyệt (Playwright, server cách ly cổng 8121, **không chạm production**):
  `/agent/canvas`, `/prompt-ai-ommi`, `/autosubvideo` đều nạp đúng bundle,
  **0 lỗi console**, không request hỏng. 10 route lấy mẫu từ các module vừa
  tách đều 200. Mobile 390×844: **không tràn ngang** trên cả ba.

### Test mới chốt các cách hỏng vừa gặp

Mọi test dưới đây đã được **chứng minh là bắt được** bằng cách trồng lại đúng lỗi:

- `test_148` — đường dẫn bundle (2 lỗi trồng thử, cả hai đỏ đúng).
- `test_149` — presign không được bọc bằng `except` rỗng.
- `test_147` — module miền phải được import trong `routes/__init__.py` (quên là
  route **biến mất lặng lẽ**, server vẫn khởi động bình thường); và
  nền tảng/app không được phụ thuộc `core/`.

### Cách lùi lại

Bốn commit độc lập, lùi được riêng: `67e3a3e` (tầng nghiệp vụ + tách OMMI +
frontend_bundle + lỗi upscalevideo) · `be5331b` (tách agent) · `9f40b18`
(presign) · commit C3 (runtime_paths).

### Còn tồn đọng

- **C2 chờ chủ sản phẩm quyết:** có ai còn dùng bảng điều khiển FB/TikTok cũ
  trên web không? Nếu không, đưa 43 route đó vào cờ mặc định TẮT.
- **C1:** xoá 5 module `core/` không ai gọi (535 dòng) — chưa làm vì xoá code
  của một sản phẩm *đóng băng chứ chưa khai tử* là quyết định sản phẩm.
- 145 chỗ `except` rộng nuốt lỗi lặng lẽ trên toàn repo (đã đo, chưa sửa). Phiên
  này chỉ xử lý nhóm presign vì nhóm đó có hại rõ ràng và sửa được cùng một chỗ.
- `tools/lint_app_contract.py` mới đo `routes.py`; chưa đo `routes/` dạng package.

### Việc tiếp theo

1. Hỏi chủ sản phẩm về C2, rồi làm C1 + C2.
2. Cho linter hiểu `routes/` dạng package (hiện app đã tách thì linter không đo nữa).
3. Deploy.

---

## 2026-08-05 — PROMPT AI OMMI: audit lại rồi xây Kho tài nguyên, Thư viện, Storyboard

- **Mục tiêu:** chủ sản phẩm báo bản codex "triển khai sai hoàn toàn"; audit lại
  bằng số đo, rồi xây phần còn thiếu với yêu cầu **mỗi người một kho riêng, một
  bộ prompt meta riêng**.
- **Hạng mục:** H19.5 và H19.6 làm lại trên bảng thật; H19.7 giữ nguyên.
- **Trạng thái:** backend + giao diện chạy thật trên browser. Chưa deploy.

### Đo được, không phải cảm tính

| | Module nguồn | Bản codex |
|---|---:|---:|
| Dòng code | 29.541 | 1.428 |
| Router · endpoint | 22 · 261 | 1 · ~20 |
| Bảng dữ liệu | 49 | **0** |

Nhưng codex **không làm sai, nó làm thiếu**: phần đã làm chạy sạch và khớp đúng
H19.3–H19.4. Chỗ chứa Kho tài nguyên/Thư viện là **H19.6, vẫn đang `[ ]`**.

### Phát hiện quan trọng nhất

`D:\BOT GEMINI\app\modules\seedance\service\scoping.py:32` nhận tham số `user`
rồi **bỏ qua nó**, luôn lọc theo một `master_user_id` dùng chung. Tầng
"PERSONAL" ghi trong docstring là giả. Nghĩa là yêu cầu "kho riêng, meta riêng"
**không phải port một tính năng có sẵn** — chép nguyên module sang là bê thẳng
một lỗ rò rỉ dữ liệu giữa các khách hàng trả tiền.

### Hai thay đổi nền tảng

**1. Hợp đồng app cho phép app sở hữu bảng CSDL.** `AppManifest` không có chỗ
khai bảng, nên app trước cần bảng thật đã nhét model vào `platform_core/models.py`
— đi vòng, đúng thứ `AGENTS.md` mục 60 cấm. Nay app khai `table_prefix` và đặt
model ở `apps/<slug>/tables.py`; registry từ chối bảng sai tiền tố hoặc hai app
trùng tiền tố (hai lỗi này nếu lọt chỉ lộ khi Alembic sinh migration **xoá nhầm
bảng app khác**). Tên file là `tables.py` chứ không phải `models.py` vì trong
thư mục app, `models.py` đã mang nghĩa "registry model AI".

**2. Q65 KHÔNG cần thay.** Chủ sản phẩm chọn "OMMI tự sinh ảnh riêng". Nhưng hai
lựa chọn tôi đưa ra là một nhị phân sai: 3.269 dòng `image_gen` của nguồn thực
chất là **điều phối** (batch theo cảnh, ảnh tham chiếu giữ nhất quán, phiên bản),
không phải engine. Nên OMMI sở hữu điều phối + giao diện + dữ liệu, còn lời gọi
provider dùng lại `taoanh.generate`. Kiểm được: worker phân việc theo `job_type`
chứ không theo `app_slug`, giá tra theo `job_type`. Người dùng không rời OMMI,
mà tích hợp Gemini/xoay khoá/retry/bảng giá vẫn ở đúng một chỗ.

### Đã xây

- **14 bảng `ommi_*`**, 2 migration, đều chạy `upgrade → downgrade → upgrade`.
- **Kho tài nguyên**: 14 endpoint, upload 2 bước (presigned R2 hoặc multipart),
  sinh ảnh qua `taoanh.generate`, giao diện React/Vite.
- **Thư viện**: một service + một màn cho meta/snippet/style, tầng catalog admin,
  clone-thành-bản-riêng, version.
- **Storyboard**: cảnh, thứ tự, phiên bản theo cảnh, chạy lại từng cảnh có báo
  giá riêng.
- Giao diện nền carbon + đỏ LTT theo `DESIGN_SYSTEM_LTT.md`; màn chưa xây bị
  **vô hiệu và gắn nhãn "đang xây"**, không phải nút chết.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `pytest` OMMI (135→143) | 138 test riêng của app |
| `npm test` (prompt-ai-ommi) | 10 passed |
| `npm run build` + `verify_frontend_bundle` | PASS |
| `python -m pytest -q` | 2.212 passed/8 skip/23 subtest (mốc R2) |
| `scan_source_secrets.py` | 0 finding |
| `lint_app_contract.py` | 12 app, 0 ERROR |

### Sáu lỗi chỉ browser tìm ra

Không lỗi nào test bắt được:

1. Fixture gọi `create_all` mà không nạp bảng app → mọi truy vấn trúng bảng
   không tồn tại. **Chỗ nào `create_all` thì phải `load_app_tables()`.**
2. `_resource_error` map mọi exception thành 400 → lỗi máy chủ bị báo là "yêu
   cầu không hợp lệ", người dùng đi sửa thứ họ gõ còn log không ghi gì.
3. Khoá lưu trữ ~145 ký tự **vượt giới hạn 260 của Windows**, báo
   `FileNotFoundError` chứ không nói là quá dài. Production gốc ngắn nên chưa vỡ
   — đó là may, không phải thiết kế.
4. URL ảnh dùng `download_token`, mà token sống trong RAM **một tiến trình**,
   web và worker là hai — mọi ảnh 404.
5. Ô tìm kiếm `flex:1` đẩy chip lọc sang mép phải, đúng chỗ panel chi tiết phủ
   lên → chip không bấm được khi panel mở.
6. `/api/projects` trả `{items: [...]}` chứ không phải mảng trần → màn Storyboard
   báo "chưa có dự án" ngay sau khi vừa tạo. **Test không bắt được vì mock của
   tôi mã hoá đúng cái giả định sai đó.**

### Quyết định mới

Không có Q mới. Q65 giữ nguyên (xem lý do ở trên). Hợp đồng app được **mở rộng**
chứ không đổi quyết định nào.

### Cách lùi lại

Revert từ `f1246f5` tới `4a0c9fd`. Migration có `downgrade` đã kiểm. Production
hiện có **0 project OMMI** nên không có dữ liệu người dùng nào bị ảnh hưởng.

### Còn tồn đọng

- ~~Chưa xây: Tổng quan, Dự án, Brief & Director, Xuất prompt, Chi phí, Cài đặt.~~
  **Đã xong cùng ngày** — 10/10 mục sidebar đều dẫn tới màn chạy được, không còn
  mục nào `đang xây`. "Xuất prompt" cố ý KHÔNG làm màn riêng: nút tải .json/.md/
  .zip nằm ngay trong Dự án, một màn chỉ để có tên trong menu là màn rỗng.
- **Cửa vào đã đổi**: `/prompt-ai-ommi` render workspace; wizard 5 bước cũ giữ ở
  `/classic` để lùi lại được mà không phải sửa mã; `/workspace` là bí danh.
  Chủ sản phẩm xác nhận app chưa công khai nên đổi được an toàn; production có
  0 project OMMI. Kiểm browser: cả ba đường đúng, console 0 lỗi.
- ~~Chưa deploy. Chưa kiểm trên URL công khai.~~ **Đã deploy 2026-08-05**, lần
  này chạy thẳng không sự cố — installer đã vá sau lần treo trước đó. Hai
  migration OMMI chạy trên Postgres production. Nghiệm thu trên **URL công
  khai**: `/health/ready` 200; asset `main-BFGwVhzt.js` và `main-CBfD4L_n.css`
  đều 200; `/prompt-ai-ommi` redirect đăng nhập đúng; catalog công khai có OMMI;
  console 0 error; mọi request 2xx/3xx.

### Gate Node: từ gate rỗng thành gate thật

`write-build-meta.mjs` ghi một chuỗi phiên bản viết tay, còn `build_release.py`
so với một chuỗi cứng khác — nên câu báo *"built with the wrong Node"* **không
bao giờ kích hoạt được**. Canvas khai 22.12.0 trong khi mọi bản build trên máy
này chạy 24.17.0, và không ai biết. Ngoài ra bundle `prompt-ai-ommi` **chưa hề
được kiểm**: một bundle production không có kiểm cũ/mới, lỗ do chính tôi tạo ra
khi thêm frontend thứ ba.

Đã sửa: cả ba script ghi `process.versions.node` thật; `PINNED_NODE` trong
`build_release.py` là nguồn duy nhất; canvas về 24.17.0 thay vì cài thêm một
runtime nữa lên máy chủ chỉ để thoả một con số vốn chưa từng được kiểm; OMMI vào
danh sách verify. Hai test chốt: ba chỗ khai Node của mỗi frontend phải khớp
`PINNED_NODE`, và không script nào được ghi số phiên bản viết tay — cấy lại
chuỗi cứng thì test đỏ. Làm lệch digest bundle OMMI thì `verify_frontend_bundle`
từ chối; đã thử cả hai.

---

## 2026-08-05 — H21.9 deploy production + SỰ CỐ ngưng dịch vụ 2 lần

- **Mục tiêu:** đưa H21.7a + H21.7b lên production theo yêu cầu của chủ sản phẩm.
- **Hạng mục:** H21.9 deploy xong. **H21.8 vẫn OPEN** — chủ sản phẩm chủ động
  cho deploy trước controlled beta, khác điều kiện ghi trong kế hoạch.
- **Trạng thái:** deploy PASS sau 4 lần chạy. Production đã ngưng **2 lần**.

### Sự cố — ghi lại đầy đủ vì đây là ngưng dịch vụ thật

`setup/2-cai-dat.ps1` dừng cả ba dịch vụ ở đầu script rồi mới copy. Nghĩa là
**mọi lỗi từ đó trở đi đều xảy ra khi production đang tắt.** Hai nguyên nhân
độc lập cùng lộ ra hôm nay:

**1. robocopy treo vô hạn (lỗi thật của installer).** Lệnh chạy không có `/R`
`/W`, tức mặc định **retry 1.000.000 lần, chờ 30 giây mỗi lần**. Copy đứng
giữa `frontend/agent-canvas/node_modules` (3.180/4.762 file), CPU đóng băng ở
3,80 giây suốt nhiều phút. Đo được: mỗi lần deploy đang copy ~723 MB rác chỉ
phục vụ phát triển — `tmp/` 427 MB, `.playwright-cli/` 188 MB,
`node_modules/` 108 MB — trong khi chính script ghi chú *"production does not
run Node/Vite"*. Càng nhiều file càng nhiều cơ hội dính khoá.
**Ngưng lần 1: 18:38 → 19:02, khoảng 24 phút.** Khôi phục tay bằng cách
chuyển `app.previous` về `app` rồi khởi động lại dịch vụ.

**2. Wrapper ghi log của tôi làm hỏng deploy (lỗi của tôi, không phải sản
phẩm).** Tôi chạy installer qua `*>&1 | Tee-Object` để bắt output. Với
`$ErrorActionPreference = 'Stop'`, PowerShell biến **mọi dòng stderr của lệnh
native** thành lỗi kết thúc. Hai bước chết vì lý do này chứ không phải vì
chúng hỏng: bước WhisperX sidecar, rồi bước `alembic upgrade head` — bằng
chứng là `deploy.err.log` chỉ chứa đúng hai dòng
`INFO [alembic.runtime.migration]`. Lần abort ở alembic bỏ qua luôn khâu đăng
ký và khởi động dịch vụ. **Ngưng lần 2: khoảng 13 phút.** Sửa bằng cách cho
tiến trình con ghi thẳng ra file ở mức OS (`Start-Process
-RedirectStandardOutput/-RedirectStandardError`), không đụng tới stream của
PowerShell. Lần chạy sau đó qua sạch, alembic báo *"Luoc do CSDL da o ban moi
nhat"* — xác nhận không hề có migration nào chờ.

### Đã làm

- `setup/2-cai-dat.ps1`: thêm `/R:2 /W:2`; thêm `node_modules
  .playwright-cli .playwright-mcp .claude test-results tmp` vào `/XD`. Copy
  giảm từ **9.733 file / 464 MB (còn chưa xong)** xuống **1.129 file / 97 MB
  trong vài giây**.
- Bọc bước WhisperX trong `try/catch`: sidecar tuỳ chọn chỉ phục vụ
  autosubvideo, không được phép làm sập cả bản cài khi dịch vụ đã tắt. Vẫn
  `throw` nếu `app.env` chưa có `LTT_WHISPERX_PYTHON` (máy cài mới), để
  auto-sub không hỏng âm thầm.
- Hai test chốt mới trong `test_61_setup_scripts.py`, đã **kiểm chứng fail khi
  gỡ fix**. Trước đó không có test nào bảo vệ khâu copy.

### Nghiệm thu sau deploy

| Kiểm tra | Kết quả |
|---|---|
| Loopback `127.0.0.1:8100/health/ready` | 200 `ready / production / database ok` |
| **Public `https://app.lttstudios.com/health/ready`** | 200 `ready / production / database ok` |
| Dịch vụ Web / Worker / Codex | Running |
| `alembic upgrade head` | đã ở bản mới nhất |
| Asset mới `main-DbE16SG4.js`, `main-D_pcwDG7.css` | 200 công khai |
| Asset cũ `main-D3g0feTj.js` | **404** — bản cũ đã bị thay hẳn |
| Trang chủ công khai trên Chrome | render đúng, console **0 error / 0 warning**, không request nào hỏng |

Asset đặt tên theo hash nội dung và HTML để `Cache-Control: no-store`, nên
Cloudflare không thể phục vụ bản cũ — không cần chờ hết TTL.

### Quyết định mới

Không có quyết định nền tảng. Nhưng ghi rõ: **H21.9 đã chạy trước khi H21.8
PASS**, trái điều kiện ghi trong kế hoạch, theo chỉ đạo trực tiếp của chủ sản
phẩm. Hệ quả: controlled beta nếu chạy sẽ đo trên production thật.

### Cách lùi lại

`C:\LTTPlatform\app.previous` là bản trước deploy. Đổi tên `app` → `app.bad`,
`app.previous` → `app`, rồi khởi động lại ba dịch vụ (đúng cách đã làm lúc
19:02 hôm nay).

### Còn tồn đọng

- ~~`C:\LTTPlatform\app.partial-808081872` — 464 MB rác của lần copy treo.~~
  ~~`frontend/agent-canvas/.pytest_cache` ACL hỏng.~~ **Đã dọn cùng ngày**: xoá
  bản copy dở (464 MB trên ổ C), giành lại quyền sở hữu rồi xoá `.pytest_cache`
  (`Get-Acl` cũng không đọc nổi — nghi phạm của lần robocopy treo), và 22 file
  DB fixture. `git status` hết cảnh báo `Permission denied`. Kiểm sau khi dọn:
  public `/health/ready` 200, ba dịch vụ Running.
- Gate Node vẫn là gate giả (xem mục H21.7b).
- H21.8 controlled beta vẫn chưa có E4.

---

## 2026-08-05 — H21.7b customer-first hardening theo Q68

- **Mục tiêu:** hoàn tất phần triển khai Q68 đang dở trong cây làm việc, chạy đủ
  gate mà chính H21.7b tự đặt, và nghiệm thu bằng browser thật.
- **Hạng mục:** H21.7b hoàn thành; H21.8 vẫn OPEN vì chưa có 5 người dùng thật.
- **Trạng thái:** frontend/build/browser/full regression/secret scan đều PASS.
  Không deploy production.

### Đã làm

- Tiếp nhận thay đổi Q68 đang dở (prompt và CTA báo giá/chạy nằm trong block,
  panel `Chi tiết` chỉ còn nhãn nghiệp vụ, bỏ Fan-out và upload asset khỏi
  Inspector, nền `#000`, tab mobile đổi `Inspector` → `Chi tiết`) và chạy nốt gate.
- **Sửa một lỗi thật do chính H21.7b tạo ra:** picker `@ Thêm nội dung từ block
  khác` trong node chỉ lọc theo kiểu, không lọc chu trình. Chọn một block đang
  cấp dữ liệu cho block hiện tại thì `connectGraph` từ chối, **không có gì xảy
  ra và không báo gì** — khách gặp một điều khiển chết. Picker `+` đầu ra
  (`quickOptions`) đã lọc `connectionCreatesCycle` từ trước, nên đây là lệch
  nhất quán trong cùng một sản phẩm. Đã thêm cùng guard vào `referenceOptions`
  và bổ sung `page.edges` vào deps. Lỗi này rơi đúng tiêu chí P3 “Prevent cycle”
  mà H21.4 đã tick — nếu lọt sang H21.8 nhiều khả năng ăn P1 và phải làm lại vòng.
- Test chốt `hides reference options that would loop back into the current block`.
  Đã **kiểm chứng test fail khi gỡ guard** rồi mới khôi phục; lần viết đầu dùng
  cặp Hình ảnh→Nâng cấp ảnh thì pass cả khi không có guard (palette mock không
  cho ảnh quay ngược), phải đổi sang cặp Văn bản↔Hình ảnh mới tái hiện đúng.
- Vá `tools/agent_browser_server.py`: fake handler kichban trả shape của
  `text.script` cho cả `text.generate`, làm `/tick` trả 500 và chuỗi mở đầu của
  Q68 (`Prompt thành hình ảnh`) không chạy nổi trong fixture. Đây là thiếu sót
  của fixture, không phải lỗi sản phẩm — handler thật có nhánh riêng trả `text`.
- Sửa tiêu đề mục H21 trong kế hoạch từ `theo Q67` thành `theo Q67 → Q68` theo
  giao thức đổi quyết định. Các chỗ nhắc Q67 trong nhật ký giữ nguyên vì đó là
  ghi chép đúng tại thời điểm đó.

### Browser evidence

Fixture cô lập `127.0.0.1:8119`, SQLite `agent-browser-test` trong scratchpad,
provider giả, không chạm production/Postgres/quota.

- Desktop 1366×900: nền `rgb(0,0,0)`; sau Fit View rail phải 62px và node trái
  62px — không đè. Prompt nằm trong block; footer có `Chi tiết` và
  `5 credit · Chạy`; panel `Chi tiết` chỉ hiện Model/Tỷ lệ/Số lượng, không có
  tên ToolSpec, không có Fan-out, lịch sử chạy thu trong `details`.
- Picker `+` đầu ra hiện `BƯỚC TIẾP THEO TỪ Bộ ảnh` và chỉ gợi ý bước tương
  thích; sau fix, block Văn bản không còn chào mời `@Hình ảnh` (`refs: []`).
- Chuỗi chi tiêu: báo giá 8 credit → `Đã dùng trước xác nhận: 0 credit` →
  xác nhận → **Hoàn tất, đã dùng 8/8 credit, 2 bước**, artifact ảnh và văn bản
  hiện trong node. Reload giữ nền đen, node và nội dung đã nhập.
- Mobile 390×844: tab `Canvas / Công cụ / Chi tiết`, panel `Chi tiết` mở đúng,
  `scrollWidth == clientWidth == 390`, không tràn ngang.
- Console cuối **0 error / 0 warning**; toàn bộ request 2xx.

### Test đã chạy

| Lệnh/kiểm tra | Kết quả |
|---|---|
| `npm test -- --run` | 51 passed (6 file) |
| `npm run build` | typecheck + Vite PASS; `main-DbE16SG4.js` gzip 143,30 kB |
| `verify_frontend_bundle` | PASS; không còn asset cũ trong thư mục build |
| Playwright Chrome local | desktop 1366 + mobile 390, quote→approve→done 8/8, console 0 |
| `python -m pytest -q` | **2.092 passed, 8 skipped, 23 subtests, 1 warning; 672,24 s** |
| `python tools\scan_source_secrets.py` | 930 file; 142.430 dòng; 0 finding; PASS |

### Quyết định mới

Không có. Q68 đã chốt trước đó; phiên này chỉ thực thi. Runtime, credit,
provider và ownership không đổi.

### Cách lùi lại

Revert commit H21.7b hoặc đặt `LTT_AGENT_CANVAS_PRESENTATION=legacy` để về
renderer H20. Không đổi schema; dữ liệu workflow/run/credit giữ nguyên.

### Còn tồn đọng

- **Gate Node là gate giả.** `write-build-meta.mjs` ghi chuỗi cứng
  `node: '22.12.0'` còn `build_release.py` so với đúng chuỗi đó, nên câu báo
  `built with the wrong Node` không bao giờ kích hoạt được — bundle này thực tế
  build bằng Node 24.17.0 vẫn PASS. `autosub-studio` đã khai 24.17.0, tức repo
  đang giữ hai chuẩn Node mà không kiểm cái nào. Phương án đề xuất: ghi
  `process.versions.node` thật và thống nhất canvas về 24.17.0 (sửa kèm
  `.nvmrc`, `engines`, `build_release.py`, assert trong `test_95`). Chưa làm vì
  nằm ngoài phạm vi H21.7b và chạm gate release.
- 22 file DB fixture rác ở `data/` và `tmp/` từ các phiên trước.
- H21.8 vẫn cần đúng 5 người dùng thật; browser agent không thay E4.
- H21.9 chưa được phép deploy trước khi H21.8 PASS và có yêu cầu deploy rõ ràng.

### Việc tiếp theo

1. Chủ sản phẩm chạy H21.8 controlled beta theo `07_CONTROLLED_BETA_PROTOCOL.md`.
2. Quyết định phương án Node rồi làm thành hạng mục riêng có full gate.
3. H21.9 chỉ sau khi 1 PASS.

---

## 2026-08-05 — H21.7a hardening bằng thao tác Chrome như người dùng

- **Mục tiêu:** tái hiện các luồng Canvas vừa triển khai trên browser render
  thật, sửa triệt để lỗi hành vi trước controlled beta; không giả lập E4 và
  không deploy production.
- **Hạng mục:** H21.7a hoàn thành; H21.8 vẫn OPEN vì chưa có 5 người dùng thật.
- **Trạng thái:** source/build/local browser/full regression PASS.

### Đã làm

- Sửa nút `•••` của node để mở đúng menu thao tác thay vì chỉ chọn node; menu
  block có quote node/run-from-here/duplicate/move/delete và dùng được sau run
  terminal.
- Cho phép tạo báo giá mới sau run `done/error/cancelled`, mở lại scope/cache và
  thêm CTA `Tạo bản chạy mới`; không còn mắc kẹt ở run cũ.
- Tăng safe-area composer, sticky CTA nhưng không che Model; auto-fit node khi
  composer mở; ảnh/video preview giữ trong node; ẩn input port kỹ thuật ở trạng
  thái nghỉ và chỉ hiện khi đang kéo dây.
- Sửa validate scope giữ cả issue toàn cục (`step_id` rỗng). Image→Video tối đa
  59 credit với budget 50 nay dừng đúng ở preflight, hiển thị “vượt ngân sách”
  và CTA mở thiết lập; không gọi `/runs`, không gắn nhầm thành `Lỗi lưu`.
- Qua giao diện quản trị append-only, cấp 200 credit cho tài khoản fixture
  `h21-browser-audit`; chạy duy nhất node asset nội bộ 0 credit để kiểm tra
  quote→approve→tick→done→artifact. Không chạy provider ảnh/video.

### Browser evidence

- T1 Text→Image và T2 Image→Text tạo quote rồi hủy trước approve; actual 0.
- T3 Image→Video: budget 50 bị chặn đúng; nâng 60 tạo quote 59/actual 0 rồi hủy.
- Tháo dây làm sạch tham chiếu; kéo chuột output ảnh→input ảnh nối lại đúng chip;
  kéo output Video ra khoảng trống mở quick-create và tạo đúng Text downstream
  với `Video đầu vào`; edge insert Upscale tạo 3 node/2 edge rồi undo sạch.
- Offline đổi tên node không gửi save; online tự lưu; reload giữ dữ liệu; sau đó
  đã trả tên về `Video`. Theme light/dark giữ qua reload và kết thúc ở dark.
- Mobile 390×844 chỉ-xem, Canvas/Công cụ/Inspector PASS, không crop node; desktop
  1366×900 full-width. Console cuối 0 error/0 warning; request mới đều 2xx.
- Trace: `.playwright-cli/traces/trace-1785857879039.trace`; video:
  `.playwright-cli/videos/h21-user-audit.webm`; ảnh cuối desktop/mobile trong
  `.playwright-cli/`.

### Test đã chạy

| Lệnh/kiểm tra | Kết quả |
|---|---|
| `npm test -- --run` | 49 passed |
| `npm run build` | typecheck + Vite build PASS; gzip JS 142,64 kB |
| `npm audit --omit=dev` | 0 vulnerability |
| Playwright Chrome local | T1/T2/T3, edge/quick-create/insert, offline/reload/theme/mobile/run asset PASS |
| `python -m pytest -q` | 2.092 passed, 8 skipped, 23 subtests passed; 1 warning; 635,02 s |
| `python tools\scan_source_secrets.py` | 930 file; 142.388 dòng; 0 finding; PASS |

### Quyết định mới

Không có. Giữ nguyên credit guard, provider/runtime/ownership và Q67; lỗi 59/50
được xử lý bằng hướng dẫn tăng budget có chủ đích, không tự nâng giới hạn ngầm.

### Cách lùi lại

Revert commit H21.7a hoặc đặt `LTT_AGENT_CANVAS_PRESENTATION=legacy`; dữ liệu
workflow/run/credit không đổi schema. Bút toán test credit là append-only và chỉ
thuộc fixture cục bộ.

### Còn tồn đọng

- H21.8 vẫn cần đúng 5 người dùng thật theo protocol; browser agent không thay E4.
- H21.9 chưa được phép deploy trước H21.8 PASS và yêu cầu deploy rõ ràng.

## 2026-08-04 — Chuẩn bị H21.8 controlled beta (chưa nghiệm thu)

- **Mục tiêu:** biến gate “5 người dùng thật” thành kịch bản đo có thể lặp lại,
  không để moderator dẫn dắt hoặc agent tự giả lập kết quả.
- **Hạng mục:** chỉ hoàn tất bộ công cụ đo; H21.8 vẫn OPEN.
- **Trạng thái:** READY TO RUN; chưa có E4, chưa deploy production.

### Đã làm

- Tạo `07_CONTROLLED_BETA_PROTOCOL.md`: cohort, 5 task, luật moderator, công thức
  success/time/help/clarity, credit guard, điều kiện dừng P0/P1 và vòng rework.
- Tạo `08_CONTROLLED_BETA_RESULTS.csv` chỉ có schema dữ liệu; không chèn participant
  hoặc kết quả giả.
- Khóa ngưỡng: 25 task, success ≥80%, median valid chain ≤120 giây, help trung
  bình ≤1/task, UX/UI ≥75, Q≥80 và không P0/P1 mở.

### Test đã chạy

Không chạy lại pytest vì đây là thay đổi tài liệu sau full gate H21.7.

| Lệnh | Kết quả |
|---|---|
| `python tools\\scan_source_secrets.py` | 930 file; 142.311 dòng; 0 finding; PASS |

### Quyết định mới

Không có; cụ thể hóa blueprint P7 đã khóa.

### Còn tồn đọng

- Cần môi trường beta an toàn và 5 người dùng thật để tạo E4.
- H21.8/H21.9 chưa PASS; không deploy production.

## 2026-08-04 — H21.7 Browser/regression/a11y/performance/recovery gate

- **Mục tiêu:** nghiệm thu UX Reset trên browser render thật, tải graph lớn,
  keyboard/accessibility, mất mạng/xung đột và toàn bộ regression nền tảng trước
  khi cho người dùng beta thật.
- **Hạng mục:** H21.7 hoàn thành; H21.8 là bước kế tiếp.
- **Trạng thái:** source/build/local browser/full regression PASS; chưa deploy
  production.

### Đã làm

- Đưa CTA phục hồi `Tải bản mới`/`Thử lưu lại` vào toolbar creative đang hiển
  thị; bỏ cây accessibility trùng từ save-state legacy. Revision conflict không
  còn là trạng thái cụt không có đường thoát.
- Khóa `Chạy` ở mobile đúng contract viewer read-only. Khi mở workflow desktop
  trên mobile, Canvas tự fit toàn graph và ẩn minimap để không còn màn hình trống
  hoặc lớp overview che nội dung.
- Thêm regression test cho conflict 409, chỉnh sửa khi offline, tự lưu sau khi
  online lại và mobile read-only.
- Stress local Page 2 bằng 1/10/50 block, không approve run, không gọi provider,
  không tiêu credit; sau test đã xóa toàn bộ 50 block và trả Page 2 về blank.

### Test đã chạy

| Lệnh/kiểm tra | Kết quả |
|---|---|
| `npm test -- --run` | 48 passed |
| `npm run build` | typecheck + Vite build PASS; gzip JS 142,34 kB |
| `npm audit --omit=dev` | 0 vulnerability |
| Playwright tải 1/10/50 block | 1 block 129 ms; thêm 9 block 219 ms; thêm 40 block 1.028 ms; save PASS |
| Playwright 1366/1720/1920 | 50 block; shell/stage full-width; overflow 0 ở cả ba viewport |
| Playwright mobile 390×844 | auto-fit 50 block; minimap ẩn; Run disabled; overflow 0 |
| Playwright keyboard/a11y | Ctrl+K/Escape PASS; 0 button hiển thị thiếu accessible name |
| Playwright recovery/network | offline→online PASS; console 0; request bất ngờ 4xx/5xx 0 |
| Visual QA desktop/mobile | PASS sau khi sửa mobile viewport/minimap |
| `python -m pytest -q` | 2.092 passed, 8 skipped, 23 subtests passed; 1 warning; 649,43 s |
| `python tools\\scan_source_secrets.py` | 928 file; 142.116 dòng; 0 finding; PASS |

### Quyết định mới

Không có; thực thi Q67 và blueprint P6 đã khóa.

### Cách lùi lại

Đặt `LTT_AGENT_CANVAS_PRESENTATION=legacy` và restart Web; document/runtime
không đổi schema. Riêng mobile fit/minimap có thể lùi bằng commit H21.7 mà không
đụng dữ liệu workflow.

### Còn tồn đọng

- H21.8 bắt buộc beta có kiểm soát với 5 người dùng thật; không được dùng test
  tự động hay agent đóng vai để giả lập tiêu chí task success.
- H21.9 chưa được phép deploy production trước khi H21.8 PASS và có yêu cầu
  deploy rõ ràng.

### Việc tiếp theo

1. Chuẩn bị kịch bản/phiếu đo H21.8 cho 5 người chưa biết kiến trúc.
2. Thu task success/time/misclick/help/abandon/clarity và re-audit Q/M/E.
3. Chỉ mở H21.9 nếu H21.8 đạt toàn bộ ngưỡng đã khóa.

## 2026-08-04 — H21.6 First-run và progressive disclosure

- **Mục tiêu:** giúp người mới tạo chuỗi hợp lệ đầu tiên mà không phải hiểu
  ToolSpec/Inspector, đồng thời giấu công cụ nâng cao cho tới khi thực sự cần.
- **Hạng mục:** H21.6 hoàn thành; H21.7 là bước kế tiếp.
- **Trạng thái:** source/build/local browser PASS; chưa deploy production.

### Đã làm

- Blank page hiển thị ba bước: chọn mẫu → nhập/tải nội dung → kiểm tra chi phí.
  Ba mẫu được đặt theo kết quả: Prompt thành hình ảnh, Hiểu nội dung hình ảnh,
  Ảnh thành video; vẫn có đường bắt đầu Canvas trống.
- Mẫu dựng trực tiếp 2 block + 1 dây tương thích, cập nhật reference đúng contract
  và chọn block upstream để mở composer. Text→Image và Image→Text không cần mở
  Inspector.
- Fresh workflow ẩn Assistant, phiên bản/chia sẻ, Layers/Note/Comment và vô hiệu
  Run khi page chưa có block. Sau khi bắt đầu, các vùng này xuất hiện lại; upload
  vẫn nằm trong chính block media, History vẫn ở drawer riêng.
- Workspace được đổi tên thành `Mẫu & thiết lập`; palette dùng thuật ngữ `block`
  nhất quán với trình bày creative.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `npm test -- --run` | 46 passed |
| `npm run build` | typecheck + Vite build PASS; gzip JS 142,25 kB |
| Playwright desktop Image→Text | 2 block; 1 edge; composer Hình ảnh mở; Inspector không cần |
| Playwright mobile 390×844 blank page | 1 first-run region; 4 CTA; Run disabled; overflow 0 |
| Playwright console/network | console error 0; request 4xx/5xx bất ngờ 0 |

### Quyết định mới

Không có; thực thi Q67 và blueprint P5 đã khóa.

### Cách lùi lại

Đặt `LTT_AGENT_CANVAS_PRESENTATION=legacy` và restart Web; document/runtime
không thay schema.

### Còn tồn đọng

- H21.7 cần full browser/regression/a11y/performance/recovery gate.
- H21.8 cần beta thật với 5 người; agent không được tự giả lập để tuyên bố PASS.
- H21.9 chưa deploy production.

### Việc tiếp theo

1. H21.7 chạy browser matrix, keyboard/a11y, 1/10/50 node và recovery.
2. Chỉ chạy full pytest một lần ở gate cuối, tránh lặp gần 2.000 test giữa phase.

## 2026-08-04 — H21.5 Luồng chạy và credit thống nhất

- **Mục tiêu:** bỏ bảng chạy lẫn thao tác biên tập và khóa một hành trình an
  toàn từ kiểm tra phạm vi đến xác nhận, hủy hoặc chạy lại.
- **Hạng mục:** H21.5 hoàn thành; H21.6 là bước kế tiếp.
- **Trạng thái:** source/build/local browser PASS; chưa deploy production.

### Đã làm

- Bảng Chạy creative chỉ còn phạm vi, cache, preview số block, lỗi validation,
  quote, xác nhận, trạng thái, hủy và chạy lại. Nhân bản/xóa/layout/lưới/lớp
  không còn chen vào hành trình chi phí; mode legacy vẫn giữ đường rollback.
- CTA tại composer và menu node cùng đi qua một `prepareScope`: lưu → validate
  → quote server → tạo run chờ xác nhận. Scope được khóa sau quote và hiển thị
  đúng nhãn duy nhất như `Hình ảnh 2`, không bị quay về “Toàn workflow”.
- Nút xác nhận bị khóa nếu `actual != 0`; UI luôn nêu rõ số credit đã dùng trước
  xác nhận. Có thể hủy cả run đang chờ duyệt và retry run kết thúc.
- Browser local đã tạo quote 5 credit/1 bước với actual 0, không bấm approve,
  rồi hủy qua UI; network chỉ có create-run 201 và cancel 200.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `npm test -- --run` | 45 passed |
| `npm run build` | typecheck + Vite build PASS; gzip JS 141,77 kB |
| Targeted budget pytest | 3 passed: quote chưa giữ credit; cancel trước duyệt 0 credit; provider guard |
| Playwright validation lỗi | 4 lỗi hiển thị theo block; không tạo run |
| Playwright quote/cancel | scope `Hình ảnh 2`; 1 bước; max 5; actual 0; cancel 200; không approve |
| Playwright console/network | console error 0; không có request 4xx/5xx liên quan |

### Quyết định mới

Không có; thực thi Q67 trên contract credit/runtime Q62 hiện hữu.

### Cách lùi lại

Đặt `LTT_AGENT_CANVAS_PRESENTATION=legacy` và restart Web; run API, credit và
document không đổi.

### Còn tồn đọng

- H21.6 cần first-run, template và progressive disclosure cho assets/history/
  Assistant; chưa mở rộng model breadth.
- H21.7–H21.9 chưa hoàn tất; chưa deploy production.

### Việc tiếp theo

1. H21.6 đưa người mới từ blank canvas đến workflow đầu tiên bằng template.
2. H21.7 chạy browser matrix, a11y, recovery và full regression một lần cuối.

## 2026-08-04 — H21.4 Connection grammar theo intent

- **Mục tiêu:** biến đường nối từ chi tiết kỹ thuật khó hiểu thành hành vi theo
  ý định, đồng thời ngăn graph sai và cho phép chèn bước ngay trên dây.
- **Hạng mục:** H21.4 hoàn thành; H21.5 là bước kế tiếp.
- **Trạng thái:** source/build/local browser PASS; chưa deploy production.

### Đã làm

- Đích nối nhanh hiển thị intent + nhãn block duy nhất; block trùng loại được
  đánh số ổn định như `Văn bản 2`, không lộ tên field/backend.
- Chặn self-loop/cycle trước khi thay document; reconnect xóa tham chiếu cũ và
  tạo tham chiếu mới trong cùng một lần cập nhật graph.
- Dây có mũi tên và màu theo text/image/video/audio; trạng thái chạy dùng nét
  đứt. Midpoint `+` chỉ liệt kê block có primary output tương thích và chèn node
  giữa source/target bằng một cập nhật nguyên tử.
- Browser thực tế đã chèn Văn bản giữa một dây: 4→5 node và 1→2 dây; reload giữ
  đúng document. Không approve run và không gọi provider tốn credit.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `npm test -- --run` | 44 passed |
| `npm run build` | typecheck + Vite build PASS; gzip JS 141,22 kB |
| Playwright 1366/1720/1920 | 5 node; 2 edge; 2 midpoint CTA; overflow 0 |
| Playwright connection menu | đích `Văn bản 2` duy nhất; edge có arrowclosed + `edge-text` |
| Playwright console/network | console error 0; API liên quan 200/201 |

### Quyết định mới

Không có; thực thi Q67 và contract H21 đã khóa.

### Cách lùi lại

Đặt `LTT_AGENT_CANVAS_PRESENTATION=legacy` và restart Web; document/runtime
không đổi schema.

### Còn tồn đọng

- H21.5 cần hợp nhất preflight → quote → approve → cancel/retry trong một luồng.
- H21.6–H21.9 chưa triển khai; chưa deploy production.

### Việc tiếp theo

1. H21.5 rút gọn run drawer và thống nhất CTA theo phạm vi chạy.
2. Xác minh actual credit bằng 0 trước confirm và không gọi provider trước approve.

## 2026-08-04 — H21.3 Creative node shell và composer safe-area

- **Mục tiêu:** bỏ box H20 quá lớn/CTA trùng và chặn palette/composer/node đè
  lên nhau trước khi sửa grammar đường nối.
- **Hạng mục:** H21.3 hoàn thành; H21.4 là bước kế tiếp.
- **Trạng thái:** source/build/local browser PASS; chưa deploy production.

### Đã làm

- Giữ `ToolNode` H20 cho mode `legacy`; thêm `CreativeToolNode` riêng cho mode
  `creative`, không rewrite document đã lưu.
- Creative node rộng 300 px, preview 170 px, status gọn trong header, footer chỉ
  báo chi phí/kết quả; bỏ nút Báo giá/Chạy lặp trong từng node.
- Chỉ render một output `+` chính; input port ẩn mặc định và hiện khi hover/chọn.
- Composer chỉ hiện tối đa bốn field nghiệp vụ. Khi chọn node, Canvas dành vùng
  219 px cho composer nên Fit View không đặt node phía sau panel.
- Mở palette sẽ đóng selection/composer; thêm block sẽ đóng palette. Browser đã
  bắt overlap cũ và xác minh lại ba desktop viewport không còn overlap.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `npm test -- --run` | 43 passed |
| `npm run build` | typecheck + Vite build PASS; gzip JS 139,97 kB |
| Playwright 1366×768 | 4 node; composer 680×205; overlap 0; overflow 0 |
| Playwright 1720×940 | 4 node; overlap 0; overflow 0 |
| Playwright 1920×1080 | 4 node; overlap 0; overflow 0 |
| Playwright console/network | console error 0; API liên quan 200/201 |

### Quyết định mới

Không có; thực thi Q67. Cờ `legacy` giữ renderer H20 để rollback.

### Cách lùi lại

Đặt `LTT_AGENT_CANVAS_PRESENTATION=legacy` và restart Web; document/runtime giữ
nguyên nên không lùi schema.

### Còn tồn đọng

- H21.4 còn edge arrow/type/midpoint insert/reconnect và matrix intent đầy đủ.
- H21.5–H21.9 chưa triển khai; chưa deploy production.

### Việc tiếp theo

1. H21.4 thay destination bằng intent duy nhất và thêm edge insert.
2. Chạy matrix Text/Image/Video/Audio và cycle validation trên browser.

## 2026-08-04 — H21.1–H21.2 Presentation Adapter và bốn block chuẩn

- **Mục tiêu:** bắt đầu UX Reset tuần tự, khóa đường migration/rollback trước
  khi thay node shell và đưa fresh user về đúng bốn block sáng tạo.
- **Hạng mục:** H21.1 và H21.2 hoàn thành; H21.3 là bước kế tiếp.
- **Trạng thái:** source/build/local browser PASS; chưa deploy production.

### Đã làm

- Thêm `presentationAdapter.ts` phiên bản `creative-v1`, phủ 21 ToolSpec và
  chuyển chúng thành Text/Image/Video/Audio + core/secondary/internal.
- Thêm env `LTT_AGENT_CANVAS_PRESENTATION=legacy` làm đường lùi H20; template
  phát mode cho frontend, không đổi Canvas document, executor hay credit.
- Preference H20 chưa version được đọc về catalog simple; lựa chọn nâng cao mới
  được lưu cùng presentation version. `audio.generate` trở thành core thứ tư.
- Palette fresh user và pane context menu không còn tạo `asset.*`; upload vẫn
  chuyển block media sang asset state nội bộ và ownership test giữ nguyên.
- Loại tên ToolSpec/field khỏi accessible name chính, palette và Layers; menu
  nối nhanh dùng intent + tên block đích, mỗi node đích một lựa chọn.
- Browser fixture 8118 từng giữ backend cũ trong RAM; restart đúng PID fixture
  rồi kiểm lại fresh user: đúng bốn block, creative mode, overflow 0.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `npm test -- --run tests/presentationAdapter.test.ts tests/nodePresentation.test.ts tests/CanvasShell.test.tsx` | 20 passed |
| `npm run build` | typecheck + Vite build PASS; gzip JS 139,19 kB |
| Targeted pytest palette/preferences/flag | 4 passed, 1 warning test harness |
| Targeted pytest asset ownership | 1 passed, 1 warning test harness |
| Playwright local 8118 | creative; chỉ 4 core block; console 0; API 200/201; overflow 0 |

### Quyết định mới

Không có quyết định nền tảng mới; đây là thực thi Q67. Contract triển khai ở
`docs/APP_AUDIT/agent/2026-08-04-ux-reset/06_PRESENTATION_CONTRACT.md`.

### Cách lùi lại

Đặt `LTT_AGENT_CANVAS_PRESENTATION=legacy` và restart Web. Document/schema/runtime
không đổi nên không có migration dữ liệu phải lùi.

### Còn tồn đọng

- H21.3 node shell/composer vẫn là H20, còn lớn và có CTA chạy trùng.
- H21.4–H21.9 chưa triển khai; chưa deploy production.

### Việc tiếp theo

1. H21.3 tạo CreativeToolNode riêng, giữ LegacyToolNode cho rollback.
2. Cap node/composer và browser gate 1366/1720/1920 trước H21.4.

## 2026-08-04 — Agent Canvas UX Reset sau production task 3/10

- **Mục tiêu:** audit lại trải nghiệm Agent Canvas bằng user-role production,
  đối soát PlenX và tài liệu chính thức, rồi khóa logic/phase mới trước khi sửa.
- **Hạng mục:** H20.10b hoàn thành runtime smoke; H21.0 hoàn thành UX reset audit.
- **Trạng thái:** audit/decision/roadmap xong; implementation H21.1 chưa bắt đầu.

### Đã làm

- Dùng canary role `user` vào production Canvas; không hiển thị credential,
  không approve job và actual credit 0. Tạo Text→Image rồi kiểm Image→Text,
  quick-connect, composer, palette và Run hierarchy ở 1280×720/1920×1080.
- Production API/save/quote đều 200/201, console 0, failed request bất ngờ 0;
  runtime smoke PASS nhưng UX có bằng chứng cụ thể: node/composer quá lớn, nhiều
  surface đồng thời, destination trùng nhãn và field/type nội bộ lộ ra khách.
- Thao tác PlenX: add menu, Image empty Upload/Generate, contextual composer,
  blank/node context menu. Node audit đã xóa, workflow hoàn nguyên `Saved` đúng
  13 node/13 connection; không tiêu credit benchmark.
- Nghiên cứu tài liệu chính thức FLORA, React Flow, ComfyUI, Langflow và n8n.
  Lập hồ sơ `docs/APP_AUDIT/agent/2026-08-04-ux-reset/`: current truth,
  benchmark, blueprint, scorecard và P0–P7.
- Score hiệu lực mới `Q58 · M42 · E93 · BLOCKED`; UX/UI 2,8/10. Gắn nhãn
  score Q87/Q93 cũ hết hiệu lực cho release vì thiếu E4 owner task.
- Q66 đã đánh dấu ĐÃ THAY bởi Q67. Q67 chọn Presentation Adapter bốn creative
  block Text/Image/Video/Audio trên runtime typed hiện có; H21.1→H21.9 được thêm
  tuần tự, không deploy từ hồ sơ audit.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `python -m pytest -q tests\\test_61_setup_scripts.py tests\\test_62_khoa_logic.py` | 95 passed |
| `python -m pytest -q` | 2.091 passed, 8 skipped, 1 warning, 23 subtests; 635,86 s |
| `python tools\\scan_source_secrets.py` | 925 file, 141.493 dòng, 0 finding |
| Playwright production LTT | Auth Canvas PASS; console 0; API 200/201; credit 0 |
| Playwright PlenX | 13 node/13 connection restored; Saved; credit 0 |

### Quyết định mới

Q67 đã thêm; Q66 đã đánh dấu ĐÃ THAY và các hồ sơ H20 hiện hành đã gắn nhãn
lịch sử. H20/Q66 trong nhật ký cũ không sửa vì là bằng chứng thời điểm đã xảy ra.

### Cách lùi lại

Revert commit audit UX Reset. Không có code/schema/deploy để rollback; canary
workflow chỉ thuộc tài khoản test production và không có run trả phí.

### Còn tồn đọng

- H21.1–H21.9 chưa triển khai.
- Chưa có controlled beta 5 người; chưa được mở public launch gate.

### Việc tiếp theo

1. H21.1 khóa Presentation Adapter/migration/feature flag/rollback contract.
2. H21.2 xây bốn canonical block trước mọi Assistant/template/model breadth.
3. Đi tuần tự đến H21.8 beta task; chỉ deploy H21.9 khi pass.

## 2026-08-04 — Deploy production H20.9 Agent Canvas multimodal

- **Mục tiêu:** phát hành release candidate H20.9 đã qua full gate và để sẵn
  PlenX/production LTT cho chủ sản phẩm nghiệm thu.
- **Hạng mục:** H20.10a hoàn thành; H20.10b chờ session người dùng.
- **Trạng thái:** production deployed và healthy; authenticated Canvas chưa ký PASS.

### Đã làm

- Commit phát hành `6dbc347`; archive 1.165 file, 78,0 MB, secret scan 0. Release
  builder đã chứng minh không mang `tmp/`, `test-results/` hoặc browser profile.
- `update.ps1` backup PostgreSQL + data (3 entry/3 file), giữ `app.previous`,
  cập nhật dependency, giữ WhisperX CUDA sidecar, chạy migration và restart.
- `4-nghiem-thu.ps1`: Web/Worker/cloudflared running, loopback/edge ready, chỉ
  listen 127.0.0.1:8100, `/docs` 404, secrets ACL/config không BOM, 13 app OK,
  service log không có error. LTTStudioCodex cũng running.
- Manifest và build-meta Canvas trong `C:\LTTPlatform\app` khớp source SHA-256.
- Browser production 1720×940 vào `/agent/canvas` chuyển đúng tới login; console
  0, failed request 0. Không tự đăng nhập/tạo canary production. Tab PlenX,
  production login và Canvas fixture authenticated vẫn được giữ mở.

### Test/health đã chạy

| Gate | Kết quả |
|---|---|
| `python -m pytest -q` | 2.091 pass, 8 skip, 23 subtests |
| `python tools\\scan_source_secrets.py` | 0 finding |
| `python tools\\build_release.py` | 1.165 file, 78,0 MB, archive scan 0 |
| `deploy/windows/update.ps1` | backup/update/migration/ready PASS |
| `setup/4-nghiem-thu.ps1` | 0 lỗi, 1 cảnh báo legacy Google Sheet |
| Production file parity | manifest + build-meta MATCH |
| Playwright production login | console 0, failed request 0 |

### Quyết định mới

Không có. Không dùng production data khi chưa có session/quyền dữ liệu cụ thể.

### Cách lùi lại

Chạy `deploy/windows/rollback.ps1`; release trước còn ở
`C:\LTTPlatform\app.previous`, backup mới ở thư mục backup production.

### Còn tồn đọng

- `sheet_id`/`google_credentials_path` legacy chưa cấu hình; không chặn Agent.
- H20.10b cần chủ sản phẩm đăng nhập tab production đang mở để smoke Canvas auth.

### Việc tiếp theo

1. Chủ sản phẩm đăng nhập production trong tab đã mở.
2. Reload `/agent/canvas`, kiểm bundle/console/network và đóng H20.10b.

## 2026-08-04 — H20.9 purchased-workflow parity và multimodal Canvas

- **Mục tiêu:** đối chiếu workflow PlenX mua sẵn theo thao tác người dùng thật,
  đóng các khoảng trống node đa phương thức và interaction trước khi phát hành.
- **Hạng mục:** H20.9 — hoàn thành local release candidate.
- **Trạng thái:** xong code/audit/test; H20.10 production deploy là bước kế tiếp.

### Đã làm

- Khảo sát Lookbook PlenX 13 node/13 edge/1 frame, không chạy generation và
  không tiêu credit. Dựng lại nhánh đại diện LTT 8 node/9 edge với ba ảnh thật:
  Asset Image → Image tổng hợp → Image cận cảnh → Text phân tích → hai Video.
- Mở typed input Image/Video/Text hai chiều; collection nhận nhiều scalar theo
  thứ tự; disconnect/copy/remap không để reference mồ côi. Image worker verify
  owner, JPEG/PNG/WebP, 8 ảnh, 8 MB/ảnh và 20 MB/node trước Gemini inlineData.
- Bổ sung Social Video bounded, transform media thật, run-node quote đúng,
  clipboard graph/multi-select/context-menu/quick-create và cleanup edge params.
- Browser local 1920×1080 validate graph và báo tối đa 132 credit; budget fixture
  50 chặn đúng trước run, actual 0. Console error 0, request API liên quan 200/201.
- Audit vòng 3 chấm `Q87 · M85 · E89 · BETA`; output provider trả phí và E4 user
  task vẫn không được tuyên bố là đã xác minh.
- Bắt và sửa release boundary: `tmp/`, `test-results/` và profile Playwright bị
  loại khỏi release/source scan. Profile Chromium đang đăng nhập vẫn giữ nguyên.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `npm test -- --run` | **40 passed** |
| `npm run typecheck && npm run build` | PASS; bundle hashed, sourcemap off |
| Targeted media/multimodal/validator/API | **92 passed**, 1 warning |
| `python -m pytest -q tests\\test_33_secret_scanner.py tests\\test_44_release_build.py` | **46 passed** |
| `python -m pytest -q` | **2.091 passed, 8 skipped, 23 subtests**, 1 test-harness deprecation warning, 632,80 s |
| `python tools\\lint_app_contract.py` | 12 app, 0 error, 0 warning |
| `npm audit --omit=dev` | 0 vulnerability |
| `python tools\\scan_source_secrets.py` | 919 file, **0 finding** |
| Playwright local | 8 node/9 edge; validate 200; console 0; failed request 0 |

### Quyết định mới

Không có quyết định nền tảng mới. H20.9 thực thi Q62/Q66; release exclusion cho
runtime temp là invariant bảo mật đã có, nay được khóa thêm bằng test.

### Cách lùi lại

Revert commit H20.9; bundle cũ vẫn được git giữ. Không cần migration dữ liệu.
Social import có dependency `yt-dlp` mới nhưng không thay schema hay provider key.

### Còn tồn đọng

- Chưa có E4 beta task/telemetry; chưa tuyên bố output parity provider trả phí.
- AG-AST-01/AG-URL-02/AG-BAT-03/AG-OUT-04 vẫn là vé riêng có security/lineage gate.
- H20.10 chưa deploy tại thời điểm ghi mục này.

### Việc tiếp theo

1. Commit release candidate H20.9.
2. Build archive, backup/update production, chạy health/canary.
3. Mở PlenX và production LTT cạnh nhau để người dùng nghiệm thu.

## 2026-08-04 — Deploy production H20.8 Agent Canvas

- **Mục tiêu:** đưa bản re-audit/interaction polish lên `app.lttstudios.com` để
  người dùng trải nghiệm, có backup và rollback trước khi nghiệm thu.
- **Hạng mục:** H20.7b hoàn thành.
- **Trạng thái:** production deployed và healthy.

### Đã làm

- Đóng gói từ đúng commit `b02e2eb`, không lấy untracked `tmp/`/`test-results/`:
  1.042 file, 7,1 MB, archive secret scan 0.
- Chạy `deploy/windows/update.ps1`: `pg_dump` + archive data 3 entry thành công,
  giữ release trước ở `C:\LTTPlatform\app.previous`, cập nhật dependency, giữ
  WhisperX CUDA sidecar khỏe, Alembic upgrade head và restart dịch vụ.
- `setup/4-nghiem-thu.ps1`: Web/Worker/cloudflared running; chỉ listen
  `127.0.0.1:8100`; loopback/edge ready; `/docs` 404; secret ACL/config không BOM;
  13 app registry OK; recent service log không có error.
- Browser production bằng session đã đăng nhập, tab mới sạch: desktop 1720×940
  và mobile 390×844 đều tải Canvas/bundle H20.8; API liên quan 200, console 0,
  request 4xx/5xx mới 0. Không tạo/chạy node, không tiêu credit.

### Kết quả thật

| Gate | Kết quả |
|---|---|
| Backup | `ltt_data_20260804_151228.zip`, 3 entry, PASS |
| Update/migration | PASS; health environment `production` |
| Services | LTTStudioWeb/Worker/Codex + cloudflared running |
| Loopback/Cloudflare | `ready` / `ready` |
| Browser authenticated desktop/mobile | PASS; console 0; fresh failed request 0 |
| Rollback target | `C:\LTTPlatform\app.previous` tồn tại |

### Cảnh báo không chặn

Google Sheet legacy chưa điền `sheet_id` và `google_credentials_path`; Agent
Canvas không phụ thuộc hai cấu hình này. Không có rollback.

### Cách lùi lại

Chạy `C:\LTTPlatform\app\deploy\windows\rollback.ps1`; dữ liệu runtime không
rollback tự động. Nếu phát hiện lỗi credit/provider thì đặt rollout Agent về
`off` trước khi đổi release.

---

## 2026-08-04 — H20.8 re-audit PlenX vòng 2 và Canvas interaction polish

- **Mục tiêu:** thao tác sâu thêm trên PlenX, tìm control còn thiếu và chỉ đưa
  capability có vận hành thật vào LTT Agent Canvas.
- **Hạng mục:** H20.8 hoàn thành local; H20.7b production release chưa chạy.
- **Trạng thái:** code/audit/regression/browser/secret gate xanh; đã tạo bundle,
  chưa deploy production.

### Đã làm

- Kiểm trực tiếp 11 node active, toolbar, shortcut, node context, title edit,
  manual Text, source chooser, connected input, output actions, pages và conflict
  trên workflow audit PlenX; không chạy generation và không tiêu credit.
- Node LTT sửa tên trực tiếp nhưng label nằm ngoài executable `data`; Text soạn
  trực tiếp trong node; Image/Video/Audio nhận drop file qua upload hiện có.
- Composer hiện input chip theo edge thật; tháo chip xóa đồng thời edge và tham
  số `$source.handle`. Thêm direct shortcut I/V/T/A/N/F/D, Ctrl+A và arrow nudge,
  có guard không chiếm bàn phím khi người dùng đang nhập.
- Artifact output có mở, chép URL, tải xuống, nhân bản node. Asset Catalog, URL
  ingest, batch reorder và lineage được tách thành vé có security/owner/credit
  gate; không dựng UI giả.
- Báo cáo delta: `docs/APP_AUDIT/agent/2026-08-04-deep-ux/08_REAUDIT_PLENX_GAPS.md`.
  Scorecard vòng mới: `Q85 · M82 · E84 · BETA`.

### Test đã chạy

| Lệnh/flow | Kết quả thật |
|---|---|
| `npm test -- --run` | **29 passed** |
| `npm run build` | typecheck + Vite build **PASS** |
| `python -m pytest -q tests/test_95_agent_canvas_build.py tests/test_97_agent_workflow_api.py` | **22 passed**, 1 deprecation warning |
| `python -m pytest -q` | **2.063 passed, 8 skipped, 23 subtests**, 630,75 giây |
| `python tools/lint_app_contract.py` | 12 app, **0 ERROR, 0 WARN** |
| `python tools/scan_source_secrets.py` | 1.563 file/206.052 dòng, **0 finding** |
| `npm audit --audit-level=high` | **0 vulnerability** |
| Browser local desktop 1720×940 | rename/text autosave PUT 200; shortcut I 5→6 node; input chip đúng edge; console 0 |
| Browser local mobile 390×844 | render PASS; console 0 error/warning |

### Quyết định mới

Không có. H20.8 triển khai tiếp Q66, không thay runtime, ToolSpec, provider,
ownership, credit hoặc nguyên tắc production release.

### Cách lùi lại

Revert commit H20.8. Label node là metadata tùy chọn nên workflow cũ/mới không
cần migration; executable data và run snapshot không đổi.

### Còn tồn đọng

- H20.7b production backup/update/health/canary/rollback chưa chạy.
- AG-AST-01, AG-URL-02, AG-BAT-03, AG-OUT-04, AG-MDL-05 và AG-E4-06 mở theo
  acceptance trong báo cáo re-audit; không mở control trước contract.
- Starlette/httpx TestClient còn một cảnh báo deprecation đã biết.

---

## 2026-08-04 — H20 Agent Canvas node-native deep UX

- **Mục tiêu:** đưa Canvas từ vỏ ToolSpec kỹ thuật thành trải nghiệm node-native,
  học capability/interaction từ PlenX nhưng giữ runtime, ownership và credit LTT.
- **Hạng mục:** H20.0–H20.7a hoàn thành; H20.7b production release chưa chạy.
- **Trạng thái:** release candidate local xanh; chưa deploy production.

### Đã làm

- Q64 đã được đánh dấu ĐÃ THAY bởi Q66; dark/advanced trở thành mặc định nhưng
  lựa chọn user đã lưu vẫn được tôn trọng.
- Thêm presentation layer theo modality cho Text/Image/Video/Audio/Batch/Input/
  Transform, empty/configured/output state, upload/generate/manual và contextual
  composer; thông số kỹ thuật giữ trong Inspector.
- Thêm context menu pane/node, copy/delete/move page, run node/run-from-here,
  quick-create compatible khi kéo connection ra khoảng trống và `@node` typed
  reference. Một input chỉ giữ một source đang hiệu lực.
- Browser bắt và đóng ba lỗi ngoài phạm vi unit test: node/edge chưa initialized
  làm graph vô hình; edge cùng input bị nhân đôi; scoped run bị validation của
  node không liên quan chặn. Viewport change cũng không còn làm bẩn undo history.
- Chạy audit DEEP mới tại `docs/APP_AUDIT/agent/2026-08-04-deep-ux/`, kết quả
  `Q83 · M80 · E82 · BETA`. Không tái dùng điểm H17/H18.

### Test đã chạy

| Lệnh/flow | Kết quả thật |
|---|---|
| `npm test -- --run` | **27 passed** |
| `npm run build` | typecheck + Vite build **PASS** |
| `python -m pytest -q tests\test_95_agent_canvas_build.py tests\test_97_agent_workflow_api.py` | **22 passed**, 1 deprecation warning |
| `python -m pytest -q` (bundle cuối) | **2.063 passed, 8 skipped, 23 subtests**, 649,97 giây |
| `npm audit --audit-level=high` | **0 vulnerability** |
| `python tools\lint_app_contract.py` | 12 app, **0 ERROR, 0 WARN** |
| `python tools\scan_source_secrets.py` (sau cập nhật docs) | 1.493 file/196.292 dòng, **0 finding** |
| Browser 1366/1720/1920 + mobile 390 | overflow 0; edge state/renderer khớp; console 0; fresh failed request 0 |
| Scoped node run local | `awaiting_approval`, quote 10 credit, actual 0; **không approve** |

### Quyết định mới

Q66 đã thêm và Q64 đã được dọn theo giao thức thay quyết định. Không thay runtime
Agent, ToolSpec contract, provider, ownership hoặc credit.

### Cách lùi lại

Revert commit H20. Dữ liệu workflow v2 và run hiện có không cần migration; đặt
preference user về theme/catalog cũ nếu cần presentation fallback.

### Còn tồn đọng

- H20.7b production backup/update/health/canary/authenticated smoke chưa chạy.
- Chưa có E4 beta user task/telemetry; mobile authoring vẫn deliberate omission.
- Test harness còn cảnh báo deprecation Starlette/httpx, không ảnh hưởng runtime.

### Việc tiếp theo

1. Chỉ deploy H20 khi có lệnh production rõ ràng; chạy backup/health/smoke/rollback.
2. Thu beta task completion, time-to-first-run, validation error và approval drop.
3. Dùng closed loop LTT-AQA trước khi mở thêm capability mới.

---

## 2026-08-04 — H19 xây core PROMPT AI OMMI và nghiệm thu browser

- **Mục tiêu:** replatform Prompt Seedance Studio thành app tenant-safe dùng
  toàn bộ Job/Credit/Storage/APIKEYS/ToolSpec nội tại LTT.
- **Hạng mục:** H19.2–H19.4 và H19.7 hoàn thành; H19.5/H19.6/H19.8/H19.9 dở;
  H19.10 chưa release/deploy.
- **Trạng thái:** core app chạy và full regression xanh; chưa deploy.

### Đã làm

- Tạo `apps/prompt_ai_ommi/`: manifest, 2 ToolSpec public, schema project v1,
  prompt resource/composer, Gemini adapter qua APIKEYS, durable Director worker,
  owner-scoped API và Carbon Red immersive UI mặc định nền sáng.
- Project có CRUD/revision/clone/archive/unarchive/snapshot/restore; asset đi qua
  Storage owner key; preference theme lưu server theo user.
- Preflight không gọi provider; quote server; submit giữ credit nguyên tử. Handoff
  ảnh/video dùng ToolSpec public, chuẩn hóa capability và popup xác nhận chi phí;
  batch frame bounded 20 item trong cùng transaction.
- Export/import JSON/Markdown/ZIP, xóa storage key khi import; catalog publish chỉ
  admin; health chỉ trả aggregate không PII/secret; production rollout mặc định
  `off`, hỗ trợ admin/allowlist/public.
- Browser fixture thật phát hiện và sửa hai lỗi: empty state ghi đè `hidden` làm
  workspace bị đẩy xuống; inspector vẫn hiện ở mobile. Đồng thời thay fixed wait
  khi save bằng `await saveCurrent()` để không chạy AI trước khi project lưu xong.
- Thêm parity ledger, threat model và runbook. `D:\BOT GEMINI` chỉ được đọc,
  không sửa/copy runtime/data/secret.

### Test đã chạy

| Lệnh/flow | Kết quả thật |
|---|---|
| `python -m pytest -q tests/test_60_app_registry.py tests/test_130_prompt_ai_ommi.py` | **27 passed** |
| Release/ToolSpec/API/OMMI targeted + secret scan | **122 passed**; secret **0 finding** |
| Browser desktop 1280×781: create→brief→Director→preflight→theme reload | PASS; console 0; failed network 0 |
| Browser mobile 390×844 | overflow 0; inspector hidden khi đóng; console 0 |
| `python -m pytest -q` sau sửa cuối | **2.063 passed, 8 skipped, 23 subtests**, 690,84 giây |
| `python tools/scan_source_secrets.py` | 1.447 file/194.014 dòng, **0 finding**, PASS |

### Quyết định mới

Không thêm quyết định kiến trúc; triển khai theo Q65. Rollout production `off`
mặc định là chốt vận hành của roadmap Q65, không thay quyết định cũ.

### Cách lùi lại

Revert commit H19 PROMPT AI OMMI. Trước deploy có thể đặt
`LTT_PROMPT_AI_OMMI_ROLLOUT=off`; dữ liệu project vẫn đọc/export được.

### Còn tồn đọng

- Iteration feedback/compare/reorder, catalog version/deprecate/clone UI.
- Retry/cancel UX, metrics P95/cost, retention operator dry-run, backup drill.
- Keyboard/axe/visual regression; canary và production deploy chưa thực hiện.

### Việc tiếp theo

1. Hoàn tất tuần tự H19.5, H19.6, H19.8, H19.9.
2. Chạy post-build LTT-AQA và parity gate H19.10.
3. Chỉ deploy khi có lệnh production rõ, backup/health/rollback sẵn sàng.

---

## 2026-08-04 — H19 khảo sát PROMPT AI OMMI từ Prompt Seedance Studio

- **Mục tiêu:** kiểm kê sâu module nguồn chỉ đọc, tách Admin/User và thiết kế
  lộ trình di trú năng lực thành app SaaS độc lập trên hạ tầng LTT.
- **Hạng mục:** H19.0–H19.1 hoàn thành; H19.2–H19.10 chưa triển khai.
- **Trạng thái:** hồ sơ audit/kế hoạch xong; chưa sửa code app, chưa deploy.

### Đã làm

- Đọc nguồn chân lý, kế hoạch, nhật ký, `KHAO_SAT_BOT_GEMINI.md`, LTT-AQA và
  code module/contract liên quan; `D:\BOT GEMINI` giữ read-only.
- Đo snapshot 194 file/47.665 dòng, 112 Python module, 22 router/261 endpoint,
  40 service, 14 JS, 16 HTML, 31 test và 49 bảng.
- Phát hiện blocker single-tenant: shared master namespace, ownership/admin
  guard bị vô hiệu ở nhiều đường; thêm API key/budget/job/data runtime riêng.
- Đối chiếu AppProject, Job, credit, Storage, APIKEYS/provider và ToolSpec LTT;
  chốt Q65 “giữ năng lực, thay hạ tầng”.
- Tạo hồ sơ `docs/APP_AUDIT/prompt-ai-ommi/2026-08-04/` gồm charter, inventory,
  role/capability matrix, target architecture, score/options, roadmap và
  Decision Gate.

### Test đã chạy

| Lệnh/flow | Kết quả thật |
|---|---|
| Read-only inventory/`rg` source và LTT contract | PASS; không ghi BOT GEMINI |
| Benchmark tài liệu chính thức web | PASS; LTX/Google/Runway/Freepik |
| `python -m pytest -q tests/test_61_setup_scripts.py tests/test_62_khoa_logic.py` | **95 passed**, 0,67 giây |
| `python -m pytest -q` | Chưa chạy; phiên này chỉ thay tài liệu, không runtime |
| `python tools/scan_source_secrets.py` | 1.419 file, 190.714 dòng, **0 finding**, PASS |

### Quyết định mới

Q65 đã thêm vào nguồn chân lý. Không thay quyết định cũ; cụ thể hóa Q3/Q43 cho
PROMPT AI OMMI.

### Cách lùi lại

Revert commit tài liệu H19; không có code/schema/data/runtime cần rollback.

### Còn tồn đọng

- Chưa có browser E2/E3 cho module nguồn hoặc app đích.
- P0 phải xác minh public contract submit ToolSpec từ app; thiếu thì dừng và
  mở contract gap, không import private handler app khác.
- Chưa copy tài nguyên; provenance/license/secret/data scan là gate bắt buộc.

### Việc tiếp theo

1. Khóa Decision Gate mặc định A hoặc nhận lựa chọn dev.
2. Thực hiện H19.2 tuần tự; chưa viết feature trước khi parity ledger/threat
   model/handoff spike PASS.

---

## 2026-08-04 — H18 sửa presentation Agent Canvas theo nghiệm thu thực tế

- **Mục tiêu:** biến Canvas từ “đủ capability” thành giao diện người mới hiểu
  được; mặc định sáng, ba hành động chính, nhưng không làm mất tool nâng cao.
- **Hạng mục:** H18.0–H18.4 hoàn thành/deploy; authenticated production browser
  là manual handoff còn mở vì phiên đăng nhập production đã hết hạn.
- **Trạng thái:** code, full gate, commit, release, deploy và health xong.

### Đã làm

- Thêm Q64: catalog simple/advanced và light/dark lưu server theo user; palette
  ưu tiên Tạo văn bản/Ảnh/Video, node bỏ app_slug/requires khỏi nội dung chính.
- API preferences dùng AppProject owner-scoped, CSRF và allowlist giá trị.
- Playwright so PlenX/LTT và bắt thêm hai lỗi: node chồng do spacing 260 px;
  toolbar bị CSS cũ ép dọc làm che nút drawer. Đã sửa spacing/lề và flex row.
- Lưu preflight reset phiên vào `AGENTS.md`; ghi rõ repo không thể tự tắt lớp
  approval của host hoặc giả vờ đã có full quyền.

### Test đã chạy

| Lệnh/flow | Kết quả thật |
|---|---|
| `npm test -- --run` | **21 passed** (lượt cuối) |
| `npm run build` | typecheck + production bundle PASS |
| `python -m pytest -q tests/test_97_agent_workflow_api.py tests/test_95_agent_canvas_build.py` | **22 passed**, 1 warning |
| Playwright local 1720×940/390×844 | theme/catalog reload PASS; node/layout/palette PASS; overflow 0; console 0 |
| `python -m pytest -q` | **2.051 passed, 8 skipped, 23 subtests**, 1 warning, 652,23 giây |
| `python tools/scan_source_secrets.py` | 1.410 file, 189.941 dòng, **0 finding**, PASS trước full gate; chạy lại trước commit |
| `tools/build_release.py` | 1.206 file, 174,8 MB, archive secret scan 0 |
| `deploy/windows/update.ps1` | pg_dump/data backup, migration, services và production ready PASS |
| `setup/4-nghiem-thu.ps1` | services/loopback/Cloudflare/security/12 app/log PASS; 1 cảnh báo Google legacy |
| Playwright production login 1720×940/390×844 | redirect auth đúng; overflow 0; console 0 |

### Quyết định mới

Q64 đã thêm vào nguồn chân lý; tinh chỉnh presentation Q63, không thay Q62.

### Cách lùi lại

Revert commit H18; preferences dùng AppProject riêng nên có thể bỏ đọc mà không
ảnh hưởng workflow/run/credit. Bundle H17 vẫn có trong lịch sử release.

### Còn tồn đọng

- Authenticated production Canvas chưa browser-smoke do không có credential;
  tab production giữ ở `/login?next=/agent/canvas`.
- External 5-user task study vẫn chặn tuyên bố GA.

### Việc tiếp theo

1. Chủ sản phẩm đăng nhập tab production nếu muốn đóng manual auth handoff.
2. Chạy controlled launch và đo task success với người dùng ngoài nhóm dev.

---

## 2026-08-04 — H17 Agent Canvas launch UX, audit độc lập và deploy

- **Mục tiêu:** sửa triệt để Canvas bị co/bí, đưa interaction hierarchy gần
  chuẩn PlenX nhưng giữ safety LTT; sau nghiệm thu chạy DEEP audit riêng để xác
  định khả năng trình làng.
- **Hạng mục:** H17.0–H17.7 — hoàn thành/deploy; authenticated production
  browser là handoff còn mở vì session hết hạn.
- **Trạng thái:** code, audit, full gate, release, deploy và health xong.

### Đã làm

- Q63 khóa shell riêng toàn viewport: topbar 48 px, rail icon 48 px, drawer theo
  ngữ cảnh, palette search, node visual-first, composer dưới và Inspector nâng
  cao. Không đổi quote/approve/credit/provider của Q62.
- Connector typed có hit-zone 44×44, hover `+`, picker chỉ liệt kê input tương
  thích; edge interaction 18 px. Node không còn form nhồi trong card.
- Playwright local desktop đo document 1720×940, stage 1720×892, rail 48 px,
  không page overflow; mobile 390×844 không overflow; palette/composer/picker
  hoạt động, console 0, request lượt reload mới 200.
- Audit độc lập theo LTT-AQA tại `docs/APP_AUDIT/agent/2026-08-04-launch/`:
  Q 92,3, M 89, E 97; P0 = 0. Khuyến nghị controlled launch, chưa gọi GA khi
  chưa có external usability metric và authenticated production smoke H17.
- Commit `b3a0df4`; release đã backup, xoay `app.previous`, migrate và deploy.
  Manifest production khớp source; giữ tab PlenX và LTT fixture để đối soát.

### Test/deploy đã chạy

| Lệnh/flow | Kết quả thật |
|---|---|
| `npm test` Agent Canvas | **20 passed** |
| `npm run typecheck && npm run build` | PASS; bundle hash production |
| `npm audit --audit-level=high` | 0 vulnerability |
| `python -m pytest tests/test_95_agent_canvas_build.py -q` | **8 passed** |
| `python -m pytest -q` | **2.050 passed, 8 skipped, 23 subtests**, 1 warning, 647,87 giây |
| `python tools/scan_source_secrets.py` | 0 finding |
| `python tools/lint_app_contract.py` | 11 app, ERROR 0/WARN 0 |
| `tools/build_release.py` | 1.203 file, 174,6 MB, archive scan 0 |
| `update.ps1` | pg_dump/data backup, migration, services, health PASS |
| `setup/4-nghiem-thu.ps1` | loopback/Cloudflare/catalog/security/12 app/log PASS; 1 cảnh báo legacy config |
| Playwright production login desktop/mobile | redirect auth đúng, overflow 0, console 0 |

### Quyết định mới

Q63: Agent Canvas dùng workspace full viewport với contextual UI và typed
connector 44 px; lý do và ranh giới ghi trong nguồn chân lý.

### Cách lùi lại

Run: đặt `LTT_AGENT_CANVAS_RUN_ROLLOUT=off`. Release: chạy
`C:\LTTPlatform\app\deploy\windows\rollback.ps1`; bản trước còn ở
`app.previous`, backup mới ở `C:\LTTPlatform\backups`.

### Còn tồn đọng

- Authenticated production Canvas H17 chưa browser-smoke vì phiên hết hạn; tab
  production đang ở login với `next=/agent/canvas`.
- External 5-user task study và telemetry không chứa prompt/media là backlog
  measurement trước GA; không phải bằng chứng được suy ra từ unit test.
- Cảnh báo legacy `sheet_id`/`google_credentials_path` không chặn Agent.

### Việc tiếp theo

1. Chủ sản phẩm đăng nhập tab production để đóng AG-LAUNCH-001.
2. Chạy controlled launch; đo time-to-first-valid-graph/rage-click/task success.
3. Chỉ mở VLM/realtime collaboration sau dữ liệu launch, không thêm nút giả.

## 2026-08-04 — Hoàn tất và deploy Agent Canvas parity H16

- **Mục tiêu:** triển khai tuần tự P14.1–P14.10 theo Q62, đối soát PlenX định
  kỳ, release một lần sau full gate và giữ hai giao diện mở để nghiệm thu.
- **Hạng mục:** H16.2–H16.10 — hoàn thành/deploy.
- **Trạng thái:** code, migration, test, deploy và health xong; production
  authenticated browser chờ chủ sản phẩm đăng nhập lại do session hết hạn.

### Đã làm

- Canvas document v2 lossless với page/frame/note/comment/view, migration v1,
  optimistic revision, snapshot/restore; immersive editor, layers, shortcuts,
  inline composer và catalog/quote server-authoritative.
- Ánh xạ thật 11/11 nhóm node đã quan sát ở PlenX: asset/text/image/batch/video/
  video upscale/audio/extract frames/merge video/merge image/image upscale;
  thêm upload owner-scoped, SSRF/privacy/file validation và GPU smoke thật.
- Run node/selection/frame/full với upstream closure, cache same-owner/exact
  params, frame export/ZIP bundle; vẫn quote→approve→hold→settle.
- Assistant SSE analyze/improve dùng proposal ký + preview diff + validator;
  private share/clone/revoke, activity và snapshot. Không mô tả sai thành VLM
  video hoặc realtime multi-user.
- Canvas tăng có kiểm soát lên 512 KiB/100 bước; planner vẫn 64 KiB, fan-out 4,
  retry 2. Thêm metrics, rollout/kill switch và runbook.
- Đối soát PlenX nhiều checkpoint; snapshot cuối vẫn đủ 11 node, Page/Frame/
  Layers/History/Share/Assistant. Không đọc/lưu cookie, token hay request secret.

### Test và release đã chạy

| Lệnh/flow | Kết quả thật |
|---|---|
| Agent/workflow/scale targeted | 19 passed |
| `npm test -- --run` (Agent Canvas) | 20 passed |
| `npm audit --audit-level=high` | 0 vulnerability |
| `python tools/lint_app_contract.py` | 12 app runtime sau deploy; source lint trước release 11 app, ERROR 0/WARN 0 |
| `python -m pytest -q` | **2.049 passed, 8 skipped, 23 subtests**, 1 warning, 621,08 giây |
| `python tools/scan_source_secrets.py` | 0 finding; snapshot Playwright tạm gây 2 finding đã chuyển khỏi workspace rồi scan lại PASS |
| `python tools/build_release.py --output C:\Temp\ltt-release` | 1.187 file, 174,2 MB, release scan 0 |
| `update.ps1` | pg_dump/data backup PASS; migrations `e5f6…` và `f6a7…`; services healthy production |
| `setup/4-nghiem-thu.ps1` | services/loopback/Cloudflare/catalog/docs/security/12 app PASS; 1 cảnh báo legacy config |
| Playwright production login 1440×900 | redirect auth đúng, overflow 0, console 0, requests quan sát thành công |
| Playwright authenticated Canvas 1440×900 + 390×844 | overflow 0, console 0; palette/workflow/run/API mới 200/201 |

### Quyết định mới

Không có quyết định kiến trúc mới; thực thi Q62. Giữ công khai các khoảng trống:
VLM video, realtime multi-user/comment lifecycle, music generation và paid TTS
production smoke là backlog, không phải tính năng đã hoàn tất.

### Cách lùi lại

Đặt `LTT_AGENT_CANVAS_RUN_ROLLOUT=off`, restart web; nếu cần chạy
`C:\LTTPlatform\app\deploy\windows\rollback.ps1`. Release cũ còn tại
`C:\LTTPlatform\app.previous`; backup trước deploy nằm trong
`C:\LTTPlatform\backups`. Migration additive, chỉ downgrade sau backup.

### Còn tồn đọng

- `sheet_id` và `google_credentials_path` chưa điền trong config production;
  đây là cảnh báo legacy, không chặn Agent.
- Phiên production browser đã hết hạn; tab LTT được để ở login→Canvas để chủ
  sản phẩm đăng nhập, tab PlenX và Canvas fixture vẫn giữ mở.

### Việc tiếp theo

1. Chủ sản phẩm đăng nhập tab LTT và nghiệm thu trực quan cùng tab PlenX.
2. Mở backlog nâng cao chỉ sau khi nghiệm thu: VLM video, realtime collaboration,
   music generation và provider paid canary.

## 2026-08-04 — Audit sâu Agent AI so với PlenX Workflow

- **Mục tiêu:** kiểm kê hands-on Workflow PlenX và đối soát code/tài nguyên
  Agent LTT để lập lộ trình functional parity; phiên này không build/deploy.
- **Đã làm:** tạo workflow audit riêng; thêm 11 node active; kiểm tra typed/
  invalid edge, model composer ảnh/video/text/audio, autosave, page, frame,
  sticky, comment, history, share, logs và shortcut. Share audit đã được tắt
  lại sau khi kiểm tra. Mở Canvas local 1720×940, kiểm tra palette 7 ToolSpec,
  layout và các request app chính.
- **Kết luận:** PlenX mạnh hơn về breadth/direct-manipulation; LTT mạnh hơn về
  typed validation, cycle guard, quote/approval/atomic credit, bounded retry,
  ownership/conflict và restore. Đích đúng là ghép UX parity lên runtime LTT,
  không thay runtime theo PlenX.
- **Hồ sơ:** `docs/APP_AUDIT/agent/2026-08-04/` gồm charter, current truth,
  control registry, benchmark, scorecard, findings, options/decisions, roadmap
  P14.0–P14.10 và 37 vé tuần tự.
- **Điểm audit:** `Q 67 · M 52 · E 76 · INTERNAL` cho bản parity mới.
- **Browser:** PlenX và local console 0 error/warning tại flow quan sát; local
  palette/workflows/runs/detail HTTP 200. Không lưu cookie, header hay token vào
  repo/tài liệu. Một URL notification bên thứ ba có credential phiên tạm thời
  xuất hiện trong output terminal khi kiểm tra request; giá trị không được chép
  vào file nào.
- **Đã chạy:** `python -m pytest tests/test_61_setup_scripts.py -q` — 71 passed;
  `python tools/scan_source_secrets.py` — 0 finding; `git diff --check` cho hồ
  sơ/kế hoạch/nhật ký — PASS.
- **Chưa chạy:** full pytest, frontend suite, provider/GPU trả phí,
  load/CWV/a11y scanner và production canary; đây là audit-only và giữ checkpoint
  release chung đã ghi ở H15.S15.1.

## 2026-08-04 — Checkpoint LAYOUT-001, hoãn full gate để tiếp tục debug

- **Mục tiêu:** bỏ container 1180 px dùng chung khiến workspace nhiều cột bị
  co hẹp; chuẩn bị tiếp tục trao đổi/debug trước khi gom release gate.
- **Hạng mục:** H15.S15.1 / Q61.
- **Trạng thái:** code và browser validation cục bộ hoàn tất; **chưa commit,
  chưa deploy, chưa full regression**.

### Đã làm

Thêm bốn page mode `standard/catalog/wide/immersive` ở base template và CSS.
Seedance, Upscale, Auto Sub và Agent Canvas dùng `immersive`; Thumbnail, Image,
Chat, Kịch bản và Clip ngắn dùng `wide`. Bỏ margin âm của Upscale/Auto Sub và
build lại bundle Auto Sub. Không thay logic job, provider hoặc credit.

Playwright fixture cô lập trên 8118 xác minh 9 app tại 1920, 1720, 1440, 1280,
1024, 768 và 390 px: không overflow toàn trang. Ở 1720 px, vùng root immersive
đạt 1.657 px và wide đạt 1.552 px; desktop/mobile render đúng; console 0 lỗi,
0 cảnh báo và không request 4xx/5xx. Phiên Chrome PlenX được giữ để dùng cho
lượt debug kế tiếp.

### Kiểm tra đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| `python -m pytest -q tests/test_129_adaptive_page_layouts.py` | **3 passed** |
| `npm test` tại `frontend/autosub-studio` | **11 passed** |
| `npm run build` tại `frontend/autosub-studio` | typecheck + Vite build **PASS** |
| Playwright 9 app × 7 viewport | overflow 0; console/network sạch |
| `python -m pytest -q` | **ĐÃ DỪNG chủ động, chưa có kết quả** |
| `python tools\scan_source_secrets.py` | **Chưa chạy** |

### Gate còn lại trước deploy

Hoàn tất chuỗi debug/UI tiếp theo rồi chạy đúng một lần: full pytest, secret
scan, cập nhật checkpoint, commit, build release, deploy và smoke production.
Không chạy lại gần 2.000 test sau từng chỉnh sửa nhỏ.

## 2026-08-04 — Hoãn WordPress plugin thành backlog không chặn

- **Mục tiêu:** lưu chính xác phần plugin để hoàn thiện sau theo yêu cầu chủ
  sản phẩm, không làm mất đầu việc và không báo nhầm đã deploy.
- **Hạng mục:** Q60 / `DEFERRED-WP-001`.
- **Trạng thái:** source và hướng dẫn bàn giao đã sẵn; production WordPress
  **chưa upload/kích hoạt**; H15.S15 được phép tiếp tục.

### Đã làm

Ghi Q60, tách activation WordPress khỏi WEB-003 và lưu checklist mở lại trong
`deploy/wordpress/README.md`. Checklist khóa đủ backup, quyền truy cập ngoài
repo, crawler 0 failure, Playwright desktop/mobile và bảo toàn OAuth callback.
Không thay đổi code runtime, dữ liệu hoặc production trong hạng mục này.

### Kiểm tra đã chạy

| Lệnh | Kết quả |
|---|---|
| `python -m pytest -q tests/test_127_wordpress_deploy_contract.py` | **3 passed** trong 0,06 giây |
| `python -m pytest -q` | **1.994 passed**, 8 skipped, 23 subtests, 1 warning trong 578,89 giây |
| `python tools\scan_source_secrets.py` | **0 finding — PASS** |

### Quyết định mới

Q60: hoãn WordPress plugin thành backlog không chặn release control plane.

## 2026-08-03 — H15.S14.3: WEB-003 deploy một phần, WordPress bị chặn quyền

- **Mục tiêu:** deploy control plane và website marketing, sau đó crawl toàn bộ
  redirect/SEO/a11y production.
- **Hạng mục:** WEB-003 dở; phần control plane hoàn thành, WordPress chưa deploy.
- **Trạng thái:** bị chặn tại quyền ghi WordPress, không phải lỗi code.

### Đã làm

Build release 1.0.0 gồm 1.149 file/173,2 MB, secret scan trong archive 0. Script
update production đã backup PostgreSQL, giữ `app.previous`, cập nhật dependency,
giữ WhisperX CUDA sidecar, chạy Alembic và khởi động lại ba dịch vụ. Health local
và Cloudflare đều ready. Ba public URL trong config production được đổi bằng
script giới hạn key, không in config/bí mật và xác minh UTF-8 không BOM.

Production browser ẩn danh xác nhận footer/link contract đã live trên catalog và
login; desktop/mobile overflow 0, console và request failure 0. Web/Worker/Codex/
cloudflared đều Running Automatic.

Đã tạo plugin WordPress data-free cho 33 alias redirect, `/vi/`, login/register/
Open Tool/Pricing và giữ nguyên hai OAuth callback. Gói cài sẵn ở
`C:\Temp\lttstudios-integration-1.0.0.zip`; rollback chỉ deactivate/remove plugin.
Crawler đọc-only kiểm canonical target, alias, callback, robots, sitemap, 404,
SEO shell và control-plane CTA.

### Test/deploy đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| `python -m pytest -q tests/test_127_wordpress_deploy_contract.py` | **3 passed** |
| `python -m pytest -q` | **1.994 passed**, 8 skipped, 23 subtests, 1 warning trong 574,14 giây |
| `tools/build_release.py` | 1.149 file; 173,2 MB; archive secret scan **PASS** |
| `deploy/windows/update.ps1` | backup/migration/restart/ready **PASS** |
| Playwright production catalog/login | 200; footer live; desktop/mobile overflow 0; console/network sạch |
| `python tools\\audit_public_web.py` | **FAIL đúng thực tế:** 29 alias sai/404; homepage thiếu app CTA và còn WP login |

### Quyết định mới

Không phát sinh; tuân thủ Q59, không upload đè WordPress bằng gói static.

### Cách lùi lại

Control plane: chạy `C:\LTTPlatform\app\deploy\windows\rollback.ps1`.
WordPress plugin chưa cài nên chưa có gì cần rollback trên marketing site.

### Còn tồn đọng

Không có browser quản trị đang mở và không có WordPress credential/API token hay
Cloudflare zone token trong môi trường. Cần một phiên `wp-admin` đã đăng nhập để
upload/activate ZIP; sau đó chạy crawler tới 0 failure và browser QA production.

### Việc tiếp theo

Mở khóa quyền WordPress → hoàn tất WEB-003 → H15.S15 DEEP release gate.

## 2026-08-03 — H15.S14.2: Website WEB-002

- **Mục tiêu:** đồng nhất liên kết Brand/App/Support/Legal/Commerce giữa
  control plane và website trước khi deploy WordPress.
- **Hạng mục:** WEB-002 hoàn thành; WEB-003 chưa bắt đầu.
- **Trạng thái:** code/contract/test/browser xong; chưa deploy production.

### Đã làm

Thêm `PUBLIC_LINKS` làm nguồn URL runtime duy nhất và footer dùng chung trên ba
shell public, authenticated app và auth. Footer nối Hệ sinh thái, Ứng dụng, FAQ,
Liên hệ, Credit/thanh toán, Privacy, Terms và Xóa dữ liệu với semantic nav.

Config default/example/current chuyển Privacy và Terms sang pretty URL đang
sống. Hai OAuth callback không bị đổi vì provider phụ thuộc exact URL. Contract
WordPress khóa catalog/login/register/commerce của control plane cùng bốn nhóm
CTA cần thay khi deploy; production WordPress chưa bị sửa ở vé này.

### Test/browser đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| Regression link contract + public/auth/home | **36 passed**, 1 warning trong 45,95 giây |
| `python -m pytest -q` | **1.991 passed**, 8 skipped, 23 subtests, 1 warning trong 573,38 giây |
| Playwright fixture 8118 desktop 1440×1000 | catalog + footer đủ 8 link; overflow 0 |
| Playwright fixture 8118 mobile 390×844 | login/footer legal render đúng; overflow 0 |
| Console/network phiên 8118 | **0 error, 0 warning, 0 request failed** |

### Quyết định mới

Không phát sinh; áp dụng Q59 và giữ ngoại lệ callback OAuth đã khóa.

### Cách lùi lại

Revert commit WEB-002. Không migration và chưa thay WordPress.

### Việc tiếp theo

H15.S14.3 WEB-003 — deploy, crawl redirect/SEO/a11y production.

## 2026-08-03 — H15.S14.1: Website WEB-001

- **Mục tiêu:** chốt một route contract giữa gói static trong repo và website
  WordPress đang chạy trước khi sửa link hoặc deploy.
- **Hạng mục:** WEB-001 hoàn thành; WEB-002 chưa bắt đầu.
- **Trạng thái:** contract/test/browser xong; chưa deploy production.

### Đã làm

Browser production và WordPress REST API xác nhận `lttstudios.com` là website
động với pretty URL, không phải gói static trong repo. Tạo `route-map.json` phủ
đủ 40/40 HTML legacy: canonical/redirect, locale fallback, server error page và
OAuth callback. Chỉ `/auth/fb-callback.html` và `/legal/callback.html` tiếp tục
giữ `.html`; cả hai đang trả 200. Ba legal URL legacy đang redirect 301 đúng.

Phát hiện `/vi/` production đang redirect nhầm sang Video Auto Publisher; map
khóa fallback đúng về `/` cho đến khi có locale WordPress thật. README được gắn
nhãn legacy rõ ràng để ngăn upload đè `public_html`. Q59 khóa WordPress là nguồn
chân lý production và route map là hợp đồng tích hợp.

### Test/browser đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| `python -m pytest -q tests/test_125_website_route_contract.py` | **3 passed** trong 0,07 giây |
| `python -X utf8 docs\\lttstudios-website\\tests\\run_tests.py` | **761 passed**, local reference bundle |
| `python -m pytest -q` | **1.988 passed**, 8 skipped, 23 subtests, 1 warning trong 601,79 giây |
| Playwright `https://lttstudios.com/` | 200; WordPress ecosystem/pretty URLs render thật |
| WordPress REST page inventory | 15 published pages; canonical Legal/About/Product/FAQ/Contact xác nhận |
| Live route probe | canonical pages 200; 2 callback 200; 3 legal legacy 301; `/vi/` sai đích được ghi nhận |

### Quyết định mới

Q59: WordPress là nguồn chân lý website production; static bundle chỉ là legacy
reference và không được deploy đè; route-map là contract duy nhất.

### Cách lùi lại

Revert commit WEB-001. Không thay WordPress hay production data.

### Việc tiếp theo

H15.S14.2 WEB-002 — đồng nhất brand/content/link App/Support/Legal/Commerce.

## 2026-08-03 — H15.S13: Admin/operator ADM-001

- **Mục tiêu:** đồng nhất toàn bộ bề mặt vận hành với Carbon Red và làm cho
  điều hướng/bảng quản trị dùng được trên mobile mà không đổi nghiệp vụ.
- **Hạng mục:** ADM-001 và H15.S13 hoàn thành.
- **Trạng thái:** code/test/browser xong; chưa deploy production.

### Đã làm

Custom console có semantic sidebar, skip link, trạng thái hệ thống, active state
và menu mobile chứa đủ 11 đích quản trị. Emoji điều hướng được thay bằng ký hiệu
operator gọn, nhất quán và không phụ thuộc font màu.

SQLAdmin nạp design token chung, đổi toàn bộ primary từ xanh Tabler sang Carbon
Red, đưa nội dung vào `main`, thêm quick navigation có accessible name và giữ
bảng dày trong scroll container. Sau visual QA đã sửa tiếp nền navy do
`.theme-dark` ghi đè biến root, về đúng surface đen/đỏ của nền tảng.

Không thay route, model, phân quyền, mutation credit hay credential contract.

### Test/browser đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| `python -m pytest -q tests/test_124_admin_ui.py tests/test_70_admin_h3.py` | **10 passed**, 1 warning trong 19,40 giây |
| `python -m pytest -q` | **1.985 passed**, 8 skipped, 23 subtests, 1 warning trong 566,58 giây |
| Playwright fixture 8117 desktop 1440×1000 | custom APIKEYS + SQLAdmin user list render đúng Carbon Red; overflow 0 |
| Playwright fixture 8117 mobile 390×844 | menu 11 link mở được; bảng cuộn trong container; page overflow 0 |
| Console/network phiên 8117 | **0 error, 0 warning, 0 request failed** |
| `python tools\\scan_source_secrets.py` | **0 finding**, PASS (1.181 file / 165.401 dòng) |

### Quyết định mới

Không phát sinh quyết định nền; đây là áp dụng design system và accessibility
contract đã khóa.

### Cách lùi lại

Revert commit ADM-001. Không migration và không thay dữ liệu vận hành.

### Việc tiếp theo

H15.S14.1 WEB-001 — chốt route map source website ↔ production pretty URL.

## 2026-08-03 — H15.S12.2: Tạo Clip ngắn CLIP-FEAT-001

- **Mục tiêu:** mở score rationale, brand render và social package bằng năng
  lực engine/Storage/AppProject đang có, không tạo phí GPU lặp.
- **Hạng mục:** CLIP-FEAT-001 và H15.S12 hoàn thành.
- **Trạng thái:** code/test/browser xong; chưa deploy production.

### Đã làm

Worker serialize CandidateScore, lý do chọn, intent và risk từ engine cho từng
clip. UI hiện breakdown và nói rõ đây là xếp hạng nội bộ, không dự đoán lượt xem.

Bốn preset auto/LTT Red/Creator Clean/Cinematic được map vào color/caption
`user_overrides` của `run_editorial`, nên preset ảnh hưởng render thật. TikTok,
YouTube Shorts và Instagram Reels dùng chung video 9:16; mỗi nền tảng có title,
description và hashtag riêng trong package.

Title/transcript package được lưu AppProject owner-scoped với optimistic
revision. ZIP được stream qua file spool, không giữ toàn bộ video trong RAM;
gồm video, SRT, package JSON và README. Chỉnh SRT không được mô tả là thay caption
đã cháy sẵn trong video. Download/package không tạo job và không trừ credit.

### Test/browser đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| Regression Clip UI/feature/package/ownership | **14 passed**, 1 warning trong 6,13 giây |
| `python -m pytest -q` | **1.983 passed**, 8 skipped, 23 subtests, 1 warning trong 565,36 giây |
| Playwright fixture 8116 + `video (10).mp4` | LTT Red; 2 clip; score breakdown; sửa title/SRT; revision 1→2; reload giữ dữ liệu; ZIP tải thành công |
| Playwright mobile 390×844 | viewport/scroll 390 px, overflow 0 |
| Console/network phiên 8116 | **0 error, 0 warning**; save/ZIP 200; video Range 206 |
| `python tools\\scan_source_secrets.py` | **0 finding**, PASS (1.171 file / 164.231 dòng) |

### Quyết định mới

Q58 khóa ý nghĩa score, brand preset nối render thật, package dùng chung video
không thêm phí và persistence AppProject/optimistic revision.

### Cách lùi lại

Revert commit CLIP-FEAT-001. Không migration; Job và video gốc không đổi.

### Việc tiếp theo

H15.S13 ADM-001 — Admin/operator shell và dense components Carbon Red.

## 2026-08-03 — H15.S12.1: Tạo Clip ngắn CLIP-UI-001

- **Mục tiêu:** thay form Clip cũ bằng workspace Carbon Red có library nguồn,
  transcript/range editor và compare output thật.
- **Hạng mục:** CLIP-UI-001 hoàn thành; CLIP-FEAT-001 chưa bắt đầu.
- **Trạng thái:** code/test/browser xong; chưa deploy production.

### Đã làm

Studio mới cho upload hoặc chọn lại tối đa 8 nguồn gần đây, suy từ Job đúng
owner và chỉ hiện object còn tồn tại trong Storage. Tên nguồn được lưu cùng Job;
backend vẫn kiểm prefix owner + tồn tại trước khi nhận source tái sử dụng.

Worker đưa timestamp và caption segments thật của mỗi output vào result. Output
library hiện source range, score hiện có, transcript và range editor. Bản chỉnh
sửa được ghi rõ chỉ sống trong local workspace; persistence/package thuộc phase
feature kế tiếp. Compare chọn tối đa hai video đã render, không dùng demo asset.

### Test/browser đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| Regression Clip engine/UI/library ownership | **11 passed**, 1 warning trong 3,80 giây |
| `python -m pytest -q` | **1.980 passed**, 8 skipped, 23 subtests, 1 warning trong 578,87 giây |
| Playwright fixture 8115 + `video (10).mp4` | duration 10s; quote/settle 12 credit; 2 output; credit 100→88; library reuse/transcript edit/compare PASS |
| Playwright mobile 390×844 | viewport/scroll 390 px, overflow 0 |
| Console/network phiên 8115 | **0 error, 0 warning**; upload/queue/estimate 200, hai video Range 206 |
| `python tools\\scan_source_secrets.py` | **0 finding**, PASS (1.167 file / 163.748 dòng) |

### Quyết định mới

Không phát sinh quyết định nền. UI chỉ mở editor local và nói rõ ranh giới;
persistence/brand/package chờ CLIP-FEAT-001.

### Cách lùi lại

Revert commit CLIP-UI-001. Không migration; Job/Storage/credit contract giữ nguyên.

### Việc tiếp theo

H15.S12.2 CLIP-FEAT-001 — score rationale, brand preset và package đa nền tảng.

## 2026-08-03 — H15.S11.2: Kịch bản SCRIPT-FEAT-001

- **Mục tiêu:** hoàn thiện source/research, lưu phiên bản và shot list trên
  contract nội tại, không tạo runtime hay chi phí ẩn.
- **Hạng mục:** SCRIPT-FEAT-001 và H15.S11 hoàn thành.
- **Trạng thái:** code/test/browser xong; chưa deploy production.

### Đã làm

Form nhận source và research, giới hạn 8.000 ký tự/trường. Worker ghép context
với chỉ thị không bịa citation hay tự nhận đã kiểm chứng ngoài nguồn người dùng
cung cấp. Kết quả có shot list tất định từ hook, sections và outro.

Job gốc giữ bất biến. Editor lưu snapshot vào AppProject owner-scoped, nối bằng
`source_job_id`; mỗi lần lưu dùng optimistic revision để ngăn ghi đè giữa hai
tab. Result ưu tiên revision mới nhất đúng owner và vẫn fallback về Job gốc.

Trong browser đã phát hiện HTTP 500 ở result do route thiếu import `select`;
đã sửa và chạy lại toàn bộ flow tới khi console/network sạch. Bổ sung regression
cho create/update, stale revision 409 và owner khác 404.

### Test/browser đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| Regression migration/Script UI/feature/ownership | **13 passed**, 1 warning trong 4,07 giây |
| `python -m pytest -q` | **1.976 passed**, 8 skipped, 23 subtests, 1 warning trong 559,10 giây |
| Playwright fixture 8114 | job DONE; source/research/3 shot; lưu revision 1→2; reload giữ title/source; credit 100→97 |
| Playwright mobile 390×844 | viewport/scroll 390 px, overflow 0 |
| Console/network phiên sạch sau sửa | **0 error, 0 warning**; status/save đều 200 |
| `python tools\\scan_source_secrets.py` | **0 finding**, PASS (1.161 file / 163.065 dòng) |

### Quyết định mới

Q57 khóa Job bất biến, AppProject owner-scoped/optimistic revision, giới hạn
source/research và shot list tất định không có phí ẩn.

### Cách lùi lại

Revert commit SCRIPT-FEAT-001. Không migration; AppProject chung và Job gốc
không bị thay schema.

### Việc tiếp theo

H15.S12.1 CLIP-UI-001 — library/transcript selection/editor/compare.

## 2026-08-03 — H15.S11.1: Kịch bản SCRIPT-UI-001

- **Mục tiêu:** biến form Kịch bản cũ thành workspace Carbon Red có outline,
  section editor, export và history thật mà chưa giả lưu phiên bản.
- **Hạng mục:** SCRIPT-UI-001 hoàn thành; SCRIPT-FEAT-001 chưa bắt đầu.
- **Trạng thái:** code/test/browser xong; chưa deploy production.

### Đã làm

Composer mới có topic counter, bốn lựa chọn từ prompt fragment hiện hữu, output
outline và quote 3 credit từ manifest. History lấy 12 Job đúng owner, hiện title/
topic/time/status và mở result thật.

Result dùng workspace editable theo title, hook, từng section, outro, description,
tags. Copy và download Markdown dựng từ giá trị đang chỉnh; pending có progressbar
semantics, error được announce. UI nói rõ chỉnh sửa hiện chỉ trong phiên và lưu
version thuộc SCRIPT-FEAT, tránh tạo cảm giác đã persist khi backend chưa có.

### Test/browser đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| Regression migration/Script UI/design contract | **14 passed** trong 0,92 giây |
| `python -m pytest -q` | **1.972 passed**, 8 skipped, 23 subtests, 1 warning trong 552,36 giây |
| Playwright fixture 8113 | counter 36; job DONE; editor thật; sửa title; tải `kich-ban.md`; history 1; credit 100→97 |
| Playwright mobile 390×844 | layout 342 px, overflow 0 |
| Console/network phiên 8113 | **0 error, 0 warning**; queue/result/status/history/CSS đều 200/303/304 |
| `python tools\\scan_source_secrets.py` | **0 finding**, PASS (1.152 file / 162.311 dòng) |

### Quyết định mới

Không phát sinh quyết định nền. UI local editor không được gọi là version đã lưu;
AppProject/source/research/shot-list chỉ mở ở SCRIPT-FEAT sau contract gate.

### Cách lùi lại

Revert commit SCRIPT-UI-001. Không migration; worker/prompt/result JSON/credit giữ
nguyên, chỉ template/CSS/history view và fixture regression thay đổi.

### Việc tiếp theo

H15.S11.2 SCRIPT-FEAT-001 — source/research/version/shot-list dùng AppProject
owner-scoped, có schema/optimistic revision và export gate.

## 2026-08-03 — H15.S10.2: Chat AI Studio CHAT-FEAT-001

- **Mục tiêu:** hoàn thiện project/file/search/export/branch theo capability thật
  của sidecar, có ownership/privacy/cost/rollback và không dựng File Search giả.
- **Hạng mục:** CHAT-FEAT-001 và H15.S10 hoàn thành.
- **Trạng thái:** code/test/browser xong; chưa deploy production.

### Đã làm

Conversation bền vững được dùng làm project Chat. Composer nhận tối đa 3 tệp,
8 MB/tệp: ảnh PNG/JPEG/WebP được decode, chuẩn hóa PNG, gửi sidecar vision và
lưu Storage owner-scoped; TXT/MD/CSV/JSON/PDF được kiểm loại, decode/trích chữ,
cap 12.000 ký tự/tệp rồi ghép vào context và transcript. UI công khai data flow.

Search server-side lọc title hoặc nội dung message nhưng luôn theo owner. Export
Markdown/JSON versioned có Content-Disposition/nosniff. Branch clone toàn bộ
message/ảnh trong cùng owner nhưng không copy `codex_thread_id`, nên lượt tiếp
theo tạo thread sidecar độc lập. Hosted File Search/vector store DEFER vì sidecar
chưa có contract/cost/retention tương ứng.

### Test/browser đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| Regression Chat UI/feature/ownership | **13 passed**, 1 warning trong 5,27 giây |
| `python -m pytest -q` | **1.970 passed**, 8 skipped, 23 subtests, 1 warning trong 585,30 giây |
| Playwright fixture 8112 | TXT + ảnh cùng lượt; note 2 tệp; transcript/ảnh còn sau reload; MD export 200; branch giữ 3 message; search nội dung thấy 2 nhánh; mobile overflow 0 |
| Console/network phiên 8112 | **0 error, 0 warning**; send/image/export/branch/search đều 200/303/304, không request ứng dụng lỗi |
| `python tools\\scan_source_secrets.py` | **0 finding**, PASS (1.148 file / 162.269 dòng) |

Đã thêm OpenAI Developer Docs MCP vào cấu hình Codex toàn cục; phiên hiện tại
chưa hot-load nên capability spike dùng fallback web chỉ trên domain tài liệu
OpenAI chính thức. Fixture cô lập, không gọi OpenAI/production.

### Quyết định mới

Q56 khóa conversation-as-project, attachment limits/data flow, search/export/
branch ownership và DEFER hosted File Search.

### Cách lùi lại

Revert commit CHAT-FEAT-001. Không migration; message/conversation cũ giữ nguyên.
Ẩn attachment/search/export/branch, route chat text/SSE cũ tiếp tục chạy.

### Việc tiếp theo

H15.S11.1 SCRIPT-UI-001 — audit Kịch bản rồi xây workspace/outline/section editor/
export trên Carbon Red trước khi mở source/research/version/shot-list.

## 2026-08-03 — H15.S10.1: Chat AI Studio CHAT-UI-001

- **Mục tiêu:** đồng nhất Chat với Carbon Red và sửa shell/composer/message/a11y
  mà không giả attachment hoặc thay runtime sidecar/credit đang hoạt động.
- **Hạng mục:** CHAT-UI-001 hoàn thành; CHAT-FEAT-001 chưa bắt đầu.
- **Trạng thái:** code/test/browser xong; chưa deploy production.

### Đã làm

Thay template inline cũ bằng layout Chat Studio scoped: header capability thật,
sidebar tạo/tìm/chọn/xóa hội thoại, empty state và thread header. Message text/ảnh,
composer, counter 20.000 ký tự, Enter/Shift+Enter, status/error live và mobile
stack có semantics đầy đủ. Luồng SSE phía client dựng node bằng `textContent`,
không còn `innerHTML`; transcript mới vẫn đi qua route hold/settle và DB cũ.

Nút đính kèm hiện ở trạng thái disabled có accessible name + giải thích sẽ mở ở
CHAT-FEAT-001 vì route hiện chưa nhận/persist file. Fixture browser thay riêng
sidecar ngoài tiến trình nhưng giữ thật web route, SSE, credit và PostgreSQL/SQLite
contract; không gọi production.

### Test/browser đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| `python -m pytest -q tests\\test_83_chataistudio.py tests\\test_118_chataistudio_ui.py tests\\test_104_design_system_contract.py` | **15 passed**, 1 warning trong 3,17 giây |
| `python -m pytest -q` | **1.967 passed**, 8 skipped, 23 subtests, 1 warning trong 547,82 giây |
| Playwright fixture 8111 desktop | AI ready; tạo conversation; counter 26; SSE trả “Xin chào từ LTT Studio.”; 2 message; attachment disabled; reload còn dữ liệu; credit 100→97 |
| Playwright fixture 8111 mobile 390×844 | layout 342 px, composer 320 px, overflow 0 |
| Console/network phiên 8111 | **0 error, 0 warning**; login/new/send/reload/CSS đều 200/303/304 |
| `python tools\\scan_source_secrets.py` | **0 finding**, PASS (1.143 file / 161.935 dòng) |

### Quyết định mới

Không phát sinh quyết định nền. Tiếp tục Q49/Q52: Jinja + JS cho luồng chat
thường; capability chưa có phải disabled/DEFER thay vì nút giả.

### Cách lùi lại

Revert commit CHAT-UI-001. Không migration; route/SSE/DB/credit/sidecar không đổi,
chỉ template, CSS scoped, regression và browser fixture thay đổi.

### Việc tiếp theo

H15.S10.2 CHAT-FEAT-001 — audit capability rồi xây project/file/search/export/
branch có ownership, privacy, cost và rollback gate.

## 2026-08-03 — H15.S9.2: Tạo ảnh IMG-FEAT-001

- **Mục tiêu:** mở reference/edit thật cho Image Studio sau khi khóa provider,
  giá, privacy, ownership và rollback; không dựng precision editor giả.
- **Hạng mục:** IMG-FEAT-001 và H15.S9 hoàn thành.
- **Trạng thái:** code/test/browser xong; chưa deploy production.

### Đã làm

Provider Registry dùng ID Gemini Image ổn định và giữ hai ID preview cũ làm
alias bất hoạt. Worker resolve alias trước khi gọi provider. Quote/hold/settlement
dùng một bảng đơn giá model: 5/5/8/16 credit mỗi ảnh.

Image Studio nhận source/style PNG, JPEG hoặc WebP tối đa 8 MB, kiểm MIME thật,
kích thước tối thiểu và trần 24 triệu pixel trước khi ghi Storage owner-scoped.
Worker chỉ đọc key đúng owner, gửi tối đa hai ảnh bằng Gemini `inlineData`, kèm
vai trò rõ. Đã mở edit, semantic replace theo mô tả, outpaint và style transfer;
UI công khai việc gửi ảnh tới Gemini và nói rõ semantic replace không phải mask
chính xác từng pixel. Output DONE có handoff owner-only trở lại Studio; file upload
mới được dọn nếu validation/submit thất bại.

### Test/browser đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| Regression provider/migration/Image UI+feature | **41 passed**, 1 warning trong 25,45 giây |
| `python -m pytest -q` | **1.965 passed**, 8 skipped, 23 subtests, 1 warning trong 556,84 giây |
| Playwright fixture 8109 desktop | Gemini 3.1 Flash ×2 báo 16 credit; upload source+style; job DONE tạo 2 output và 2 edit handoff; trang edit nạp đúng prompt/source |
| Playwright fixture 8109 mobile 390×844 | controls rộng 342 px; overflow 0; action/control của app có vùng tương tác ≥44 px (radio ẩn dùng label 44 px) |
| Console/network phiên 8109 | **0 error, 0 warning**; login/app/queue/edit/image/CSS đều 200/303/304, không request lỗi |
| `python tools\\scan_source_secrets.py` | **0 finding**, PASS (1.140 file / 161.899 dòng) |

Fixture dùng SQLite/user/data cô lập và worker giả chỉ tạo output nội bộ; không
gọi provider hay dữ liệu production. Full suite và scan chạy song song, đều exit 0.

### Quyết định mới

Q55 khóa model ID/legacy alias, đơn giá theo model, giới hạn reference, privacy
disclosure và ranh giới semantic edit so với precision mask.

### Cách lùi lại

Revert commit IMG-FEAT-001. Không migration DB; xóa control edit/reference khỏi
UI, worker trở về text-only và bảng model/alias cũ. Job/output cũ vẫn là JSON/Storage
owner-scoped nên không cần chuyển đổi dữ liệu.

### Việc tiếp theo

H15.S10.1 CHAT-UI-001 — audit code/runtime Chat AI Studio rồi đồng nhất shell,
composer, message, attachment và accessibility trước khi mở CHAT-FEAT-001.

## 2026-08-03 — H15.S9.1: Tạo ảnh IMG-UI-001

- **Mục tiêu:** đưa app Tạo ảnh về cùng Carbon Red contract, dùng lịch sử và
  compare từ output thật mà không trộn feature reference/edit của phase sau.
- **Hạng mục:** IMG-UI-001 hoàn thành; IMG-FEAT-001 chưa bắt đầu.
- **Trạng thái:** code/test/browser xong; chưa deploy production.

### Đã làm

Giữ nguyên Gemini worker, quote/credit, Storage và owner image route. Thay UI
inline cũ bằng Image Studio hai vùng: prompt composer, model/tỉ lệ/số lượng,
counter 4.000 ký tự, cost lấy từ manifest, cấu hình preview dựng bằng DOM an
toàn; workspace chứa compare tối đa hai output thật.

History lấy 12 job đúng owner, chuẩn hóa count legacy và hiện prompt, aspect,
requested count, thời điểm, status/progress live semantics, progress message,
error và output. Image card có alt mô tả, nút compare `aria-pressed` và mở ảnh;
không có ảnh demo hoặc năng lực edit giả. CSS `.im-*` scoped, responsive và
giữ target tối thiểu 44 px.

### Test/browser đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| Regression migration/UI/operation/Agent tool spec | **65 passed**, 1 warning trong 152,60 giây |
| `python -m pytest -q` | **1.959 passed**, 8 skipped, 23 subtests, 1 warning trong 585,04 giây |
| Playwright fixture 8108 desktop | prompt counter 56; preview đúng prompt/16:9/2 ảnh; cost 10 credit; tạo 2 output 1024 px; compare và aria-pressed PASS |
| Playwright fixture 8108 mobile 390×844 | controls/history/compare rộng 327 px; overflow 0; không target visible nào dưới 44×44 px |
| Console/network phiên 8108 | console hiện tại 0 lỗi; trang/CSS và hai image request đều 200/304 |
| `python tools\scan_source_secrets.py` | **0 finding**, PASS (1.136 file / 161.462 dòng) |

Regression đầu tiên có 64 pass và một assertion test đỏ vì cấm mọi inline style,
trong khi progress width động là trường hợp an toàn cần thiết. Guard đã được sửa
để chỉ cho phép đúng style width tiến độ; regression cuối xanh. Full suite đầu bị
ngắt khi sandbox đổi lượt, nên không dùng làm bằng chứng; đã chạy lại từ đầu và
ghi kết quả PASS ở trên. Fixture dùng DB/user/data cô lập, không gọi production.

### Quyết định mới

Không phát sinh quyết định nền. Tiếp tục Q52 và Q54: UI trước feature; compare
output thật, không gọi score/edit khi engine chưa qua gate.

### Cách lùi lại

Revert commit IMG-UI-001. Không migration; job/result/storage và đường tạo ảnh
cũ giữ nguyên contract, chỉ metadata view và template/CSS thay đổi.

### Việc tiếp theo

H15.S9.2 IMG-FEAT-001 — audit/spike provider cho style/structure reference và
edit/inpaint/outpaint, khóa cost/privacy/rollback trước khi hiện control.

## 2026-08-03 — H15.S8.2: Thumbnail TH-FEAT-001

- **Mục tiêu:** khép vòng sáng tạo Thumbnail bằng reference, Brand Kit, score
  minh bạch và remix mà không tạo kho/runtime/editor giả.
- **Hạng mục:** TH-FEAT-001 và H15.S8 hoàn thành.
- **Trạng thái:** code/test/browser xong; chưa deploy production.

### Đã làm

Ảnh reference nhận PNG/JPEG/WebP tối đa 8 MB, kiểm cả MIME khai báo, nội dung
decode, kích thước tối thiểu và trần 24 triệu pixel trước khi ghi Storage. Key
luôn owner-scoped; file upload mới được dọn khi submit thiếu credit/registry lỗi.
Worker đọc reference từ Storage và gửi inline Gemini cùng prompt; không đưa key
hoặc dữ liệu người khác qua client.

Brand Kit chuẩn hóa tên, hai màu hex, font và tone; lưu owner-scoped bằng generic
AppProject có optimistic revision, rồi tự nạp lại ở phiên sau. Worker ghép brand
directive vào prompt nội bộ. Mỗi output hợp lệ được chấm `technical-v1` từ chính
pixel ảnh: contrast, entropy, detail và exposure; UI ghi rõ “Kỹ thuật”, không gọi
là CTR/AI score. Payload legacy/không decode được vẫn hoàn job nhưng score mang
`unavailable`, không bịa điểm.

Mỗi output có “Tạo biến thể”: server xác minh job DONE + owner + index, khôi phục
snapshot params và đưa output thật về Studio làm saved reference. Queue kiểm key
nằm trong lịch sử output của đúng owner trước khi worker đọc. Đây là handoff remix
thật; pixel editor/inpaint DEFER tới IMG-FEAT-001 theo Q54.

### Test/browser đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| Regression Thumbnail/operation/parity/Agent tool spec | **75 passed**, 1 warning trong 88,93 giây |
| `python -m pytest -q` (lần cuối sau fix cleanup) | **1.957 passed**, 8 skipped, 23 subtests, 1 warning trong 551,03 giây |
| Playwright fixture 8107 desktop | upload reference nội bộ thật; tạo 2 output; Brand Kit còn sau reload; mỗi ảnh score 44/100, 1024×576; remix khôi phục đúng topic/title/reference |
| Playwright fixture 8107 mobile 390×844 | overflow 0; feature/control vừa viewport; mọi action output đạt 44×44 px |
| Console/network phiên 8107 | console hiện tại 0 lỗi; request trang/CSS/HTMX đều 200; ảnh output/remix tải thành công |
| `python tools\scan_source_secrets.py` | **0 finding**, PASS trước cập nhật tài liệu (1.135 file / 161.336 dòng) |

Browser bắt link “Mở” cao 44 nhưng chỉ rộng khoảng 37 px trên mobile; đã thêm
min-width 44 px và reload kiểm lại. Fixture dùng DB/user/data cô lập trong `tmp`,
không gọi Gemini/ImageGen và không dùng production. Diff review sau gate còn bắt
cleanup thiếu credit có thể xóa saved output dùng để remix; đã tách key upload mới,
thêm regression “submit fail không xóa output gốc”, rồi chạy lại full suite xanh.

### Quyết định mới

Q54: score v1 là kỹ thuật tất định, không dự đoán CTR; handoff v1 là remix qua
reference owner-scoped; pixel editor phải chờ IMG-FEAT-001 đủ engine/cost gate.

### Cách lùi lại

Revert commit TH-FEAT-001. Không migration: Brand Kit dùng AppProject và reference
dùng Storage hiện có; job cũ không có brand/reference/scores vẫn render bình thường.

### Việc tiếp theo

H15.S9.1 IMG-UI-001 — audit app Tạo ảnh rồi làm Studio/history/compare tuần tự.

## 2026-08-03 — H15.S8.1: Thumbnail TH-UI-001

- **Mục tiêu:** đồng nhất giao diện Thumbnail theo Carbon Red và chỉ hiển thị
  lịch sử/so sánh dựa trên output vận hành thật.
- **Hạng mục:** TH-UI-001 hoàn thành; TH-FEAT-001 chưa bắt đầu.
- **Trạng thái:** code/test/browser xong; chưa deploy production.

### Đã làm

Thay bố cục một cột bằng Thumbnail Studio hai vùng: nhóm điều khiển semantic,
workspace xem cấu hình, lịch sử output và compare. Giá trên nút tạo lấy trực tiếp
từ manifest rồi cập nhật theo số lượng, tránh hardcode lệch contract. Các chip,
field và action responsive; vùng chạm visible đạt tối thiểu 44 px và page không
tràn ngang ở 390 px.

Lịch sử lấy tối đa 12 job đúng owner, chuẩn hóa an toàn dữ liệu legacy, hiện
title/topic, tỉ lệ, số ảnh, thời điểm, tiến độ/thông báo/lỗi và output thật. Người
dùng chọn/bỏ chọn tối đa hai ảnh để so sánh; nhãn dựng bằng DOM `textContent`,
không đưa dữ liệu người dùng qua HTML động. Không tạo ảnh demo và không gọi
ImageGen. Browser fixture chỉ sao chép asset nội bộ vào storage owner-scoped để
kiểm thử đường vận hành thật của route/job/image.

### Test/browser đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| Regression Thumbnail/operation/parity/Agent tool spec | **73 passed**, 1 warning trong 65,47 giây |
| `python -m pytest -q` | **1.955 passed**, 8 skipped, 23 subtests, 1 warning trong 582,38 giây |
| Playwright fixture 8106 desktop | preview đúng topic/title/style/tỉ lệ; tạo 2 ảnh, cost 10 credit; history metadata và hai ảnh 1024 px tải thành công; compare/aria-pressed PASS |
| Playwright fixture 8106 mobile 390×844 | overflow 0; controls/history/compare vừa viewport; mọi target visible ≥44 px |
| Console/network phiên 8106 | console hiện tại 0 lỗi; mọi request ứng dụng và hai image request đều 200 |
| `python tools\scan_source_secrets.py` | **0 finding**, PASS (1.134 file / 160.974 dòng) |

Browser lần đầu bắt fieldset/chip làm panel tràn sang workspace và hai nút phụ
chỉ cao 35 px trên mobile. Đã khóa `min-width: 0`, scroll nội bộ chip và target
44 px, sau đó reload và kiểm tra lại mới ghi PASS. Fixture dùng DB/user/data cô
lập trong `tmp`, không dùng production.

### Quyết định mới

Không phát sinh quyết định nền. Tiếp tục Q52: UI app dùng Carbon Red, UI trước
feature và không mở control dựa trên năng lực giả.

### Cách lùi lại

Revert commit TH-UI-001. Không migration; dữ liệu Job/storage cũ không đổi và
route tạo/preview/image giữ nguyên contract.

### Việc tiếp theo

H15.S8.2 TH-FEAT-001 — audit contract hiện có rồi triển khai reference/brand kit,
variant scoring và editor handoff theo provider/cost/privacy gate; không song song.

## 2026-08-03 — H15.S7.3: Agent Canvas AG-FEAT-002

- **Mục tiêu:** cho Agent chạy nền theo lịch và khôi phục version bằng contract
  nội tại, vẫn giữ snapshot/approval/credit/server execution.
- **Hạng mục:** AG-FEAT-002 và H15.S7 hoàn thành.
- **Trạng thái:** code/test/browser xong; chưa deploy production.

### Đã làm

Đăng ký job app-owned `agent.advance` giá 0 credit cho chính orchestration; chi phí
tool vẫn do quote/hold/settle của AgentRun. Approval HTML cũ và Canvas API đều
enqueue job bền vững; chạy ngay dùng thời điểm hiện tại, lịch một lần dùng
`Job.next_run_at` tối đa 30 ngày. Handler advance một tick, rồi tạo follow-up
idempotent khi DAG còn chạy, nên browser có thể đóng và worker restart/reclaim vẫn
tiếp tục. Cancel hủy các orchestration job liên quan; cả endpoint tick HTML/API
đều khóa server-side, không cho client ép chạy trước lịch.

Run Inspector thêm thời điểm/trạng thái đã lên lịch. Approval cho chọn local
datetime rồi gửi ISO có timezone; polling xa lịch giảm còn tối đa một lần/phút.
Snapshot run bất biến có action khôi phục thành workflow mới, giữ nguyên goal,
Plan và Canvas nhưng không ghi đè workflow đang sửa. Đồng thời sửa converter để
`after_error` chỉ nằm ở edge condition, không bị nhân đôi trong node data.

Không mở webhook public/recurring trong v1: hai đường này cần token scope,
rate-limit, replay protection và consent/cap tự động riêng trước khi được quyền
tiêu credit. Manual trigger và one-time scheduled trigger đã vận hành thật.

### Test/browser đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| `npm test` (Agent Canvas, cuối) | **17 passed** |
| `npm run build` | typecheck + Vite production build **PASS** |
| Regression Agent mở rộng | **111 passed**, 1 warning trong 76,52 giây |
| `python -m pytest -q` | **1.955 passed**, 8 skipped, 23 subtests, 1 warning trong 547,42 giây |
| Playwright fixture 8105 desktop | plan→quote→schedule; sau 4 giây vẫn Đã lên lịch/step Đang chờ; recovery tạo workflow mới đúng goal; console 0 lỗi; request ứng dụng đều 200/201 |
| `python tools\scan_source_secrets.py` | **0 finding**, PASS (1.134 file / 160.886 dòng) |

Browser lần đầu bắt hai lỗi thật: toolbar fixed-height bị Canvas chặn click khi có
datetime control; và API tick cũ cho chạy sớm dù queue đã hẹn đúng. Đã sửa toolbar
thành một hàng cuộn ngang và khóa lịch tại cả hai server endpoint, rồi chạy lại
browser mới ghi PASS. Fixture dùng DB/user cô lập, không dùng production.

### Quyết định mới

Q53 đã thêm vào `QUYET_DINH_NEN_TANG.md`: schedule v1 một lần, duyệt/hold trước;
recovery tạo bản mới; webhook/recurring phải qua security + consent gate riêng.

### Cách lùi lại

Revert commit AG-FEAT-002. Không migration; job orchestration là additive và run/
workflow cũ không có decision `scheduled` vẫn chạy ngay như trước.

### Việc tiếp theo

H15.S8: audit app kế tiếp đúng backlog rồi làm UI trước, feature sau; không song song.

## 2026-08-03 — H15.S7.2: Agent Canvas AG-FEAT-001

- **Mục tiêu:** hoàn thiện replay/debug/template và nhánh xử lý lỗi trên contract
  Agent hiện có, không tạo runtime client-side hay bỏ qua quote/approval/credit.
- **Hạng mục:** AG-FEAT-001 hoàn thành; AG-FEAT-002 chưa bắt đầu.
- **Trạng thái:** code/test/browser xong; chưa deploy production.

### Đã làm

Mở API owner-scoped cho 20 run mới nhất và chi tiết run; summary không phát lộ
Plan. Run Inspector hiển thị checkpoint error/reason, lịch sử, lựa chọn run cũ và
replay từ snapshot bất biến qua contract `/again` đã có. Canvas tái sử dụng clone,
export và import workflow làm template thay vì xây kho template song song.

Plan v1 bổ sung `after_error` và Canvas edge `condition=error`. Bộ chuyển đổi hai
chiều, validator và cycle guard hiểu cả nhánh success/error. Executor chỉ chạy
nhánh khi điều kiện dependency tương ứng đạt, đánh dấu nhánh không thể tới là
`skipped`, ghi decision `branch_skipped`/`error_handled`, và chỉ kết thúc `done`
khi lỗi nguồn đã được một nhánh lỗi hoàn tất. Lỗi không được xử lý vẫn giữ hành vi
`error`; mọi step, kể cả error branch, vẫn nằm trong báo giá server-side ban đầu.

UI phân biệt cạnh lỗi bằng nhãn/màu/nét đứt, cho đổi điều kiện khi chọn cạnh; thêm
template controls và lịch sử/replay vào responsive Inspector. Không thêm scheduler
hay trigger trong vé này.

### Test/browser đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| `npm test` (Agent Canvas) | **17 passed** |
| `npm run build` | typecheck + Vite production build **PASS** |
| Lệnh Agent hẹp đầu tiên | **FAIL thao tác:** gọi nhầm hai tên file không tồn tại; 0 test chạy |
| Lệnh Agent hẹp đúng 9 module | **54 passed**, 1 warning trong 62,78 giây |
| `python -m pytest -q` | **1.954 passed**, 8 skipped, 23 subtests, 1 warning trong 580,70 giây |
| Playwright fixture 8105 desktop + mobile | plan→quote→run→approve→done→replay PASS; lịch sử có run gốc/replay; template controls và mobile tabs hiện đúng; request 8105 đều 200/201; console phiên hiện tại 0 lỗi |
| `python tools\scan_source_secrets.py` | **0 finding**, PASS (1.134 file / 160.638 dòng) |

Fixture dùng user/DB cô lập trong `tmp`, không dùng production. Console `all=true`
có một lỗi lịch sử từ host 8102 của phiên browser trước; phép kiểm tra phiên 8105
`all=false` trả 0 lỗi và network filter 8105 không có request thất bại.

### Quyết định mới

Không phát sinh quyết định nền. Triển khai tiếp tục Q39/Q49: Canvas là authoring,
runtime/quote/credit ở server; reuse snapshot và workflow contract nội tại.

### Cách lùi lại

Revert commit AG-FEAT-001. Thay đổi schema Plan/Canvas là additive, không migration;
workflow/run cũ không có `after_error` vẫn chạy theo nhánh success như trước.

### Việc tiếp theo

H15.S7.3 AG-FEAT-002 — audit gate rồi triển khai trigger/schedule/version recovery
tuần tự, không mở năng lực giả khi chưa có contract vận hành.

## 2026-08-03 — H15.S7.1: Agent Canvas AG-UI-001

- **Mục tiêu:** đồng nhất Canvas với shared shell, mở run inspector và responsive
  controls mà không đổi executor/Plan/ToolSpec/credit.
- **Hạng mục:** AG-UI-001 hoàn thành; hai vé feature chưa bắt đầu.
- **Trạng thái:** code/test/browser xong; chưa deploy production.

### Đã làm

React island chuyển surface/border/accent/focus sang semantic Carbon Red và nâng
toàn bộ control, React Flow controls cùng attribution target lên 44 px. Giữ server
validation, autosave, read-only mobile và reduced motion như cũ.

Mobile không còn mất palette/inspector: ba tab Canvas/Công cụ/Inspector chuyển
panel responsive, vẫn giữ mobile chỉ xem theo contract hiện tại. Run Inspector
đọc trực tiếp `AgentRun` đã có, hiển thị trạng thái, estimated/actual credit,
version, checkpoint từng step, artifact owner URL và decision log; empty state
không dựng run giả. Không thêm replay/debug/schedule dưới vé UI.

### Test/browser đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| `npm test` (Agent Canvas) | **15 passed** |
| `npm run build` | typecheck + Vite production build **PASS** |
| Lệnh Agent hẹp đầu tiên | **FAIL thao tác:** sai tên `tests\\test_102_agent_workflows.py`; 0 test chạy |
| Lệnh Agent hẹp chạy lại đúng 7 module | **34 passed**, 1 warning trong 61,20 giây |
| `python -m pytest -q` | **1.952 passed**, 8 skipped, 23 subtests, 1 warning trong 564,70 giây |
| Playwright canary 8103 desktop + 390×844 | Carbon Red; Canvas/Công cụ/Inspector mở được; Run Inspector thật; overflow 0; control dưới 44 px = 0; console/request fail 0 |
| `python tools\\scan_source_secrets.py` | **0 finding**, PASS (1.134 file / 160.401 dòng) |

Canary dùng user/DB cô lập, không dùng production. Lỗi tên test được sửa bằng cách
liệt kê file thật qua `rg --files tests | rg agent` rồi chạy đúng module.

### Quyết định mới

Không phát sinh quyết định nền. Responsive panel không thay Q39/Q49 và không biến
Canvas thành runtime; execution vẫn chỉ server-side.

### Cách lùi lại

Revert React source/CSS/bundle AG-UI-001. Không migration, API hay dữ liệu mới.

### Việc tiếp theo

H15.S7.2 AG-FEAT-001 — execution replay/debug/error branch/template, chỉ mở phần
đạt contract/credit/rollback gate.

## 2026-08-03 — H15.S6.2: Auto Sub AS-FEAT-001

- **Mục tiêu:** bổ sung brand template, transcript QA và speaker workflow bằng
  contract nội tại, không tạo provider/job mới và không phá render parity.
- **Hạng mục:** AS-FEAT-001 và H15.S6 hoàn thành.
- **Trạng thái:** code/test/browser xong; chưa deploy production.

### Đã làm

Thêm preset server-driven `ltt_brand`: Montserrat trắng, Carbon Red word highlight,
nền/safe area/line budget xác định đầy đủ bằng `SubtitleStyleConfig`, nên dùng cùng
renderer ASS hiện có thay vì CSS preview-only. API style nay có 9 preset typed.

Thêm transcript QA tất định trên selected track: phát hiện cue trống, cue chồng
timing, dưới 0,5 giây, tốc độ đọc trên 20 ký tự/giây và vượt line budget đang chọn;
điểm trừ phân biệt error/warning, từng issue dẫn tới đúng cue để Dev sửa. QA không
tự sửa/xóa transcript và không gửi nội dung sang provider.

Speaker workflow lấy ID ẩn danh đã có từ Pyannote/cue, cho đặt alias tối đa 80 ký
tự trong `payload.speakers`, autosave theo revision và hiển thị alias trên cue list.
Schema giới hạn tối đa 100 speaker và từ chối key/tên sai; không suy đoán danh tính.

### Test/browser đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| `npm test` (Auto Sub) | **11 passed** |
| `npm run build` | typecheck + Vite production build **PASS** |
| `python -m pytest -q tests\\test_103_autosub_projects.py tests\\test_81_autosubvideo.py` | **35 passed**, 1 warning |
| `python -m pytest -q` | **1.952 passed**, 8 skipped, 23 subtests, 1 warning trong 572,85 giây |
| Playwright canary 8103 desktop/mobile | QA 60/100 từ corpus lỗi; alias Host/Khách mời autosave và còn sau reload; overflow 0; control dưới 44 px = 0; console/request fail 0 |
| Style API contract từ process mới | 9 preset; `ltt_brand` màu `#EF3731`, line budget 34 — PASS |
| `python tools\\scan_source_secrets.py` | **0 finding**, PASS (1.134 file / 160.328 dòng) |

Canary 8103 đang chạy module registry cũ nên danh sách template của process đó chưa
hot-reload; không dùng danh sách 8 preset cũ làm PASS. Contract API/TestClient từ
source mới và frontend production build là bằng chứng cho preset mới; rollout cần
process restart theo release gate bình thường. Dữ liệu browser chỉ nằm ở DB cô lập.

### Quyết định mới

Không phát sinh quyết định nền. Speaker alias là metadata project, không phải nhận
dạng danh tính; tiếp tục đúng Q50. Brand template dùng renderer hiện có nên không có
provider/cost/privacy mới.

### Cách lùi lại

Revert preset/component/schema additive và asset build. Project cũ không có alias
vẫn hợp lệ; project đã có alias vẫn là payload v1 hợp lệ trước khi revert UI.

### Việc tiếp theo

H15.S7 Agent/Canvas: AG-UI-001 trước, rồi AG-FEAT-001/002 tuần tự.

## 2026-08-03 — H15.S6.1: Auto Sub AS-UI-001

- **Mục tiêu:** đồng nhất Auto Sub với Carbon Red và sửa accessibility/capability
  mà không phá editor/render parity AS0–AS9.
- **Hạng mục:** AS-UI-001 hoàn thành; AS-FEAT-001 chưa bắt đầu.
- **Trạng thái:** code/test/browser xong; chưa deploy production.

### Đã làm

React island chuyển token màu/surface/font sang semantic token dùng chung, giữ
fallback để asset độc lập vẫn render đúng. Workflow step có `aria-current`, trạng
thái autosave/job là live status, cue timeline có tên và pressed state. Mọi control
visible được nâng interaction target 44 px, có focus ring thống nhất và reduced
motion cũ được giữ nguyên.

Thay hai cảnh báo cấu hình rời bằng capability list server-driven cho WhisperX,
Pyannote và Gemini: mỗi công cụ nói rõ chức năng và trạng thái Sẵn sàng/Chưa cấu
hình/Đang kiểm tra. Control provider thiếu vẫn disabled và giải thích thật; không
tạo dữ liệu minh họa hay bật năng lực giả.

### Test/browser đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| `npm test` (Auto Sub) | **10 passed** |
| `npm run build` | typecheck + Vite production build **PASS** |
| `python -m pytest -q tests\\test_81_autosubvideo.py tests\\test_103_autosub_projects.py` | **35 passed**, 1 warning |
| `python -m pytest -q` | **1.952 passed**, 8 skipped, 23 subtests, 1 warning trong 707,91 giây |
| Playwright canary 8103 desktop + 390×844 | overflow 0; mobile 39/39 control visible đạt ≥44×44; capability đúng; console warning/error 0; request ứng dụng fail 0 |
| `python tools\\scan_source_secrets.py` | **0 finding**, PASS (1.134 file / 160.243 dòng) |

Canary dùng DB/storage/process cô lập; không dùng dữ liệu production. Hai input
file ẩn 1 px được loại khỏi phép đo vì label tương tác tương ứng đều ≥44 px.

### Quyết định mới

Không phát sinh quyết định nền. Tiếp tục Q49/Q52 và giữ nguyên contract/job/render.

### Cách lùi lại

Revert asset/source AS-UI-001; không migration, không đổi API hay dữ liệu project.

### Việc tiếp theo

H15.S6.2 AS-FEAT-001 — audit rồi triển khai brand template, transcript QA và
speaker workflow theo năng lực nội tại hiện có.

## 2026-08-03 — H15.S5.3: motion/HDR UP-FEAT-002

- **Mục tiêu:** chỉ mở stabilization/interpolation/HDR khi engine và cost gate
  tương ứng đạt; không buộc cả ba dùng chung kết luận AI Detail.
- **Hạng mục:** UP-FEAT-002 và H15.S5 hoàn thành.
- **Trạng thái:** code/test/browser xong; chưa deploy production.

### Đã làm

FFmpeg production build có libvidstab two-pass và minterpolate. Benchmark 8 giây
file `video (10).mp4`: chống rung 1,34 giây, giữ 24 FPS/192 frame; interpolation
25,29 giây, xuất 48 FPS/381 frame. Chốt multiplier server-side 1,2× và 2,2×.

Hai flag additive đi xuyên quote, hold, service dùng chung Seedance, batch,
ToolSpec, worker, output result và card. Worker chống rung trong temp dir bằng
`motion.trf` tương đối để không vỡ filter parser trên Windows; smooth nội suy
trước Real-ESRGAN, nhân rational FPS, nhân disk guard và tách ETA sample theo
đúng tổ hợp flag. Output key mang suffix để resume không nhầm artifact thường.

HDR giữ DEFER: filter hiện có giải HDR→SDR, không chứng minh được SDR→HDR đúng
color primaries/transfer/mastering metadata. UI nói rõ không nâng SDR giả HDR.
Thêm `tests/test_116_upscale_motion_features.py` và báo cáo
`docs/UI_REDESIGN/upscalevideo/06_MOTION_HDR_GATE.md`.

### Test/browser đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| Targeted final docs/vận hành/Upscale/UI/motion | **125 passed**, 1 warning trong 45,57 giây |
| `python -m pytest -q` | **1.952 passed**, 8 skipped, 23 subtests, 1 warning trong 546,26 giây |
| Motion benchmark thật | libvidstab 1,34s; minterpolate 25,29s; probe 24→48 FPS PASS |
| CPU pipeline smoke 0,625s | actual libvidstab/minterpolate/probe/scale/encode + stub riêng Real-ESRGAN để không tranh GPU production; 1882×1080, 48 FPS, 27 frame PASS |
| Playwright canary 8103 desktop | quote 5→6→14; submit giữ 14 credit; card queued có Chống rung/FPS 2×; overflow 0 |
| Playwright canary 375 px | workspace-first; drawer/control mới visible; overflow 0; console warning/error 0; dynamic request fail 0 |
| `python tools\scan_source_secrets.py` | **0 finding**, PASS (1.134 file / 160.227 dòng) |

Canary dùng DB/storage/process riêng trong `tmp/`. Lượt browser đầu tại 8102
dùng route process cũ nên quote không đổi; không coi đó là PASS. Đã dựng fixture
8103 từ source mới rồi mới ghi kết quả. Không đụng DB/credit production.

### Quyết định mới

Không phát sinh quyết định nền. Thực thi Q47/Q52: feature đạt engine/cost gate
được BUILD; phần chưa đạt tiếp tục DEFER có lý do, không bị gọi là “đóng băng”.

### Cách lùi lại

Ẩn hai checkbox/ngừng nhận flag mới rồi revert commit UP-FEAT-002. Params additive
cũ được worker trước bỏ qua; không migration hay core change.

### Việc tiếp theo

H15.S6 Auto Sub — audit vé UI/feature hiện có rồi triển khai tuần tự theo roadmap.

## 2026-08-03 — H15.S5.2: benchmark enhancement UP-FEAT-001

- **Mục tiêu:** đánh giá AI Detail/denoise/deblur bằng capability và số đo thật,
  không suy diễn từ tên model.
- **Hạng mục:** UP-FEAT-001 hoàn thành với kết luận DEFER có bằng chứng.
- **Trạng thái:** benchmark/test/document xong; không đổi runtime, chưa deploy.

### Đã làm

Audit thấy engine có ba cặp model gồm `general`, `general-wdn` và `x4plus`, trong
khi báo cáo cũ mới đo hai model. Binary NCNN thực tế không có tham số `-dn`;
theo upstream, DNI điều chỉnh denoise-strength thuộc pipeline Python. Vì vậy
không được biến model WDN đơn lẻ thành control denoise giả.

Nâng `tools/benchmark_upscale_ai_detail.py` lên schema 2: kiểm kê model theo đủ
`.param`/`.bin`, hash engine/model, lưu driver GPU, tạo deterministic matrix
bicubic/noise/blur, đo PSNR/SSIM/temporal error/runtime cho từng model và xuất
feature gate riêng cho AI Detail, denoise, deblur. Frame nguồn/output vẫn bị dọn
trong `finally`; JSON không ghi đường dẫn nguồn.

Nghiên cứu primary source xác nhận BasicVSR++/RealBasicVSR là ứng viên temporal
Apache-2.0 đáng spike; MMagic hỗ trợ Windows nhưng cần PyTorch/MMCV/MMEngine tách
khỏi runtime NCNN hiện tại. Chưa cài dependency/model mới khi chưa có benchmark
window và cost/rollback gate.

Sau khi process GPU production kết thúc, đã chạy schema 2 trên 12 frame file
`video (10).mp4`: 3 model × bicubic/noise/blur, tổng 9 inference trong 134,8 giây.
WDN thắng bicubic (31,5096 dB; temporal 4,732) nhưng thua noise rõ (28,7073 dB;
temporal 9,4589), nên không thể đổi nhãn thành AI Detail/denoise. General-x4v3
tốt nhất ở noise và blur của tập này nhưng vẫn là spatial upscale x4.

Preflight temporal sidecar: Python 3.11 có torch 2.5.1+cu121 nhưng wheel không
hỗ trợ `sm_120`; Python 3.13 chỉ có torch CPU. Spike BasicVSR++ cần venv cô lập
với CUDA 13.0/12.8 hỗ trợ Blackwell và compatibility gate MMCV/MMagic; không
nâng đè môi trường worker. Báo cáo và evidence schema 2 đã cập nhật.

### Test đã chạy

| Lệnh/kiểm tra | Kết quả |
|---|---|
| `python -m pytest -q tests/test_115_upscale_feature_benchmark.py tests/test_82_upscalevideo.py` | **20 passed** trong 1,79 giây |
| `python -m py_compile tools\benchmark_upscale_ai_detail.py` | PASS |
| GPU/process preflight | BOT GEMINI có `realesrgan-ncnn-vulkan.exe` đang chạy, GPU 99–100%; không chạy benchmark cạnh tranh |
| Benchmark schema 2 | PASS; 12 frame, 9 inference, 134,8 giây; JSON evidence đã lưu |
| PyTorch GPU preflight | 3.11: 2.5.1+cu121 thiếu `sm_120`; 3.13: CPU-only |
| `python -m pytest -q` sau thay đổi harness/evidence | **1.946 passed**, 8 skipped, 23 subtests, 1 warning trong 583,17 giây |
| `python tools\scan_source_secrets.py` | **0 finding**, PASS (1.131 file / 159.874 dòng) |

### Quyết định mới

Không phát sinh quyết định nền. Tuân thủ ranh giới BOT GEMINI chỉ đọc và Q47:
không tác động process production, không mở feature trước benchmark/cost gate.

### Cách lùi lại

Revert commit benchmark matrix; runtime Upscale không thay đổi.

### Việc tiếp theo

Chạy full gate rồi chuyển UP-FEAT-002; stabilization/interpolation/HDR phải có
engine/cost gate riêng, không được suy từ kết quả AI Detail.

## 2026-08-03 — H15.S5.1: Upscale UP-UI-001

- **Mục tiêu:** thống nhất shell responsive, compare, queue/status và a11y của
  Upscale trước khi đánh giá thêm engine enhancement.
- **Hạng mục:** UP-UI-001 hoàn thành; H15.S5 còn UP-FEAT-001/002.
- **Trạng thái:** code/test/browser xong; chưa deploy production.

### Đã làm

Mobile mở thẳng workspace và dùng nút disclosure có `aria-expanded` để bung
bảng thiết lập, thay vì buộc người dùng cuộn qua toàn bộ control trước. Desktop
giữ bố cục studio hai cột hiện có.

Compare được gom thành một surface trước/sau: video nguồn điều khiển playback,
video kết quả đồng bộ play/pause/seek/rate; range có label điều khiển đường chia.
Nút So sánh của job tải đúng source/output vào surface chung, bỏ cặp video ẩn
trùng cho từng card. Queue có nhãn trạng thái theo state, progressbar đầy đủ
min/max/current và article gắn accessible title. AI Detail tiếp tục disabled,
ghi rõ chỉ mở sau benchmark engine thật; không dùng Quality để giả lập.

Thêm `tests/test_114_upscale_ui.py`. File video người dùng chỉ định được browser
đọc metadata và quote trên canary cô lập; không submit job, không trừ credit.

### Test/browser đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| Targeted vận hành/Upscale/UI | **45 passed**, 1 warning trong 48,68 giây |
| `python -m pytest -q` | **1.943 passed**, 8 skipped, 23 subtests, 1 warning trong 746,61 giây |
| `python tools\scan_source_secrets.py` | **0 finding**, PASS (1.130 file / 159.476 dòng) |
| Playwright 1440 px | upload `video (10).mp4` → metadata 2,9 MB, quote 5 credit; overflow 0; telemetry 200 |
| Playwright 375 px | settings mặc định đóng, workspace ở đầu; mở/đóng + `aria-expanded` PASS; overflow 0 |
| Console/network Upscale | warning/error mới 0; request động hỏng 0 |

### Quyết định mới

Không phát sinh quyết định nền. UP-UI-001 giữ nguyên năng lực đã xây; AI Detail
và nhóm enhancement vẫn chịu engine/cost gate đã khóa trong Q47/Q52.

### Cách lùi lại

Revert commit UP-UI-001. Không có migration hoặc dữ liệu production cần rollback.

### Việc tiếp theo

H15.S5.2 UP-FEAT-001 — audit lại benchmark hiện có và chỉ mở feature nào có
engine thật đạt acceptance/cost gate; nếu chưa đạt phải giữ DEFER có bằng chứng.

## 2026-08-03 — H15.S4.3: Prompt/variation TV-FEAT-002

- **Mục tiêu:** thêm prompt assist, variation/remix và camera control theo đúng
  capability provider; không giả camera native.
- **Hạng mục:** TV-FEAT-002 hoàn thành; H15.S4 hoàn thành đủ ba vé.
- **Trạng thái:** code/test/browser xong; chưa deploy production.

### Đã làm

Model registry khai rõ `supports_seed` và ba prompt control. Camera/motion/style
được ghép thành prompt guidance tất định ở server; UI nói rõ đây không phải cơ
khí camera native. `/prompt-assist` preview bằng chính helper queue dùng, không
gọi provider và không tốn credit. Seed được validate 0..2147483647, truyền qua
adapter ModelArk; hai biến thể dùng seed N/N+1. ToolSpec Agent được mở rộng additive.

Mỗi job lưu raw prompt, prompt final và control đã chuẩn hóa. Nút Biến thể trên
card phục hồi model/prompt/thời lượng/tỉ lệ/độ phân giải, đặt count=2 và mở
composer; mobile dùng chung luồng. Thêm `tests/test_113_taovideo_prompt_controls.py`.

### Test/browser đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| Targeted taovideo/ToolSpec/UI/prompt | **89 passed**, 1 warning trong 58,54 giây |
| Targeted lượt đầu | **1 fail**, 88 pass: test cũ khóa nhãn “Số lượng”; cập nhật theo “Số lượng/biến thể” |
| `python -m pytest -q` | **1.940 passed**, 8 skipped, 23 subtests, 1 warning trong 563,75 giây |
| `python tools\scan_source_secrets.py` | **0 finding**, PASS (1.129 file / 159.370 dòng) |
| Playwright desktop | preview đủ tracking/dynamic/cinematic; submit +2 job; remix phục hồi prompt/count; console/network sạch |
| DB canary | hai job có seed 100/101, control chuẩn hóa và prompt final chứa Direction |
| Playwright 390 px | remix mở drawer/expanded; count=2; field thiếu nhãn 0; overflow 0; console/network sạch |

Browser/DB/credit đều cô lập trong `tmp/`; không có worker/provider call và không
dùng dữ liệu hay tiền production.

### Quyết định mới

Không phát sinh quyết định nền. Camera là prompt guidance vì adapter hiện chỉ có
native seed; capability UI lấy từ model registry thay vì hardcode phỏng đoán.

### Cách lùi lại

Revert commit TV-FEAT-002. Không có migration/dữ liệu production cần rollback.

### Việc tiếp theo

H15.S5 Upscale Video — bắt đầu UP-UI-001; không mở engine feature trước UI gate.

---

## 2026-08-03 — H15.S4.2: Asset library TV-FEAT-001

- **Mục tiêu:** cho phép tái sử dụng reference đã tải mà không tạo kho asset hay
  nguồn quyền thứ hai.
- **Hạng mục:** TV-FEAT-001 hoàn thành; H15.S4 còn TV-FEAT-002.
- **Trạng thái:** code/test/browser xong; chưa deploy production.

### Đã làm

Asset library được suy ra từ tối đa 60 job Tạo video gần nhất của đúng owner;
dedupe theo `storage_key`, hiển thị tối đa 40 asset. Upload mới lưu metadata tên,
MIME, size, kind, role và handle trong params job hiện có. User chọn lại asset qua
`saved_ref_keys`; server chỉ resolve key đã xuất hiện trong lịch sử job của đúng
user, kiểm object còn tồn tại và chuẩn hóa kind/role/handle.

Tổng asset cũ+mới bị giới hạn 4 ở cả browser và server. MIME/empty/size được
validate cho toàn batch trước khi ghi storage, nên file sau lỗi không để file
trước thành orphan. Nav Tài sản nay dẫn tới library thật; empty state giải thích
asset xuất hiện sau job đầu tiên. Thêm `tests/test_112_taovideo_saved_assets.py`.

### Test/browser đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| Targeted vận hành/taovideo/UI/assets | **53 passed**, 1 warning trong 74,43 giây |
| `python -m pytest -q` | **1.935 passed**, 8 skipped, 23 subtests, 1 warning trong 597,98 giây |
| `python tools\scan_source_secrets.py` | **0 finding**, PASS (1.128 file / 159.140 dòng) |
| Playwright file thật desktop | upload `video (10).mp4` → job local → asset 2,9 MB/reference_video → chọn lại → job thứ hai giữ cùng key |
| Playwright 390/1280 px | asset list render; overflow 0; field thiếu nhãn 0; console/network sạch |
| Browser abuse/limit | key không thuộc owner trả 400; 1 asset cũ + 4 file mới bị browser chặn tổng-4 |

Browser dùng SQLite, data dir và credit canary cô lập trong `tmp/`; không gọi
provider/worker, không dùng dữ liệu hoặc tiền production.

### Quyết định mới

Không phát sinh quyết định nền. Storage và params job hiện có là nguồn dữ liệu;
owner scope từ DB là nguồn quyền. Không tạo bảng asset hoặc filesystem index mới.

### Cách lùi lại

Revert commit TV-FEAT-001. Không có migration/dữ liệu production cần rollback.

### Việc tiếp theo

H15.S4.3 TV-FEAT-002 — prompt assist/variation/camera theo capability provider.

---

## 2026-08-03 — H15.S4.1: Tạo video TV-UI-001

- **Mục tiêu:** chuẩn hóa shell/control/a11y/empty/job card của Seedance trước
  khi mở rộng asset và prompt workflow.
- **Hạng mục:** TV-UI-001 hoàn thành; H15.S4 còn TV-FEAT-001/002.
- **Trạng thái:** code/test/browser xong; chưa deploy production.

### Đã làm

Composer được cấu trúc lại bằng fieldset/legend/label; drawer có scrim,
`aria-expanded`, Escape và focus vào control đầu. User thường không còn thấy link
Cấu hình operator-only; Mẫu prompt/Tài sản chưa có backend là button disabled có
lý do. Filter, error, empty state, job progress và dialog upscale có semantics.

File tham chiếu tạo DOM bằng `textContent`, không chèn filename qua HTML; role và
handle sinh động đều có label. Sửa `_render` để nhánh validation/credit nhận dict
workspace đúng cách thay vì lặp qua key; textarea sau dịch giữ id/required/hint.
Thêm `tests/test_111_taovideo_ui.py`.

### Test/browser đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| Targeted vận hành/taovideo/UI | **48 passed**, 1 warning trong 63,95 giây |
| `python -m pytest -q` | **1.930 passed**, 8 skipped, 23 subtests, 1 warning trong 645,75 giây |
| `python tools\scan_source_secrets.py` | **0 finding**, PASS (1.127 file / 158.863 dòng) |
| Playwright 390/1280 px | 200; overflow 0; field thiếu nhãn 0; drawer/Escape/empty PASS; console/network lỗi 0 |
| Playwright file thật `video (10).mp4` | 1 reference row; filename an toàn; role/handle/label PASS; không submit/provider call |

File test chỉ được đọc từ thư mục người dùng đã chỉ định. Browser dùng canary/DB
cô lập; không dùng dữ liệu production và không tạo job tính credit.

### Quyết định mới

Không phát sinh quyết định nền. TV-UI-001 thực thi Q46/Q52; asset library và
prompt capability giữ đúng phạm vi hai vé tiếp theo.

### Cách lùi lại

Revert commit TV-UI-001. Không có migration hay dữ liệu production cần rollback.

### Việc tiếp theo

H15.S4.2 TV-FEAT-001 — tái dùng storage/job/owner contract, không tạo kho asset
thứ hai nếu năng lực nội tại đã đủ.

---

## 2026-08-03 — H15.S3.2: Khóa IA trang chủ HOME-002

- **Mục tiêu:** mọi mục điều hướng Home phải dẫn tới năng lực thật hoặc thể hiện
  DEFER rõ; My Apps phải phản ánh đúng lịch sử owner.
- **Hạng mục:** HOME-002 hoàn thành; H15.S3 hoàn thành đủ HOME-001/002.
- **Trạng thái:** code/test/browser xong; chưa deploy production.

### Đã làm

Sửa `used_slugs` bằng truy vấn distinct trên toàn bộ job của user, không còn suy
ra từ 5 hoạt động gần nhất. Rail recent vẫn giới hạn 5 nên không tăng tải/render.
Lối “Workspace” được đặt đúng tên năng lực đang có là Agent Canvas và giữ route
`/agent/canvas`. Mẫu, Tài nguyên và Cộng đồng chưa có backend global được chuyển
thành control disabled có `aria-disabled`, nhãn “Chưa có” và lý do; không còn
Templates giả trỏ chung vào Canvas. My Apps có empty state riêng.

Thêm `tests/test_110_home_information_architecture.py`, gồm regression 6 job để
chứng minh app cũ ngoài recent-5 vẫn nằm trong My Apps.

### Test/browser đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| Targeted home/IA | **31 passed**, 1 warning trong 46,93 giây |
| `python -m pytest -q` | **1.925 passed**, 8 skipped, 23 subtests, 1 warning trong 845,97 giây |
| `python tools\scan_source_secrets.py` | **0 finding**, PASS (1.126 file / 158.656 dòng) |
| Playwright canary local 390/1280 px | My Apps PASS; Agent Canvas route thật; 3 mục defer disabled/no href/có lý do; overflow 0; console/network lỗi 0 |

Browser dùng DB/canary cô lập trong `tmp/`, không dùng production.

### Quyết định mới

Không phát sinh quyết định nền. Đây là thực thi HOME-002 theo Q46: chưa có
backend thì DEFER rõ, không tạo UI giả hoặc kho dữ liệu thứ hai.

### Cách lùi lại

Revert commit HOME-002. Không có migration hay dữ liệu production cần rollback.

### Việc tiếp theo

H15.S4 Tạo video AI, bắt đầu TV-UI-001 rồi đi tuần tự các vé còn lại của stage.

---

## 2026-08-03 — H15.S3.1: Marketplace shell HOME-001

- **Mục tiêu:** hợp nhất Home authenticated với Carbon Red và sửa các control
  shell đang hiển thị nhưng chưa vận hành đầy đủ trên mobile.
- **Hạng mục:** HOME-001 hoàn thành; H15.S3 còn HOME-002.
- **Trạng thái:** code/test/browser xong; chưa deploy production.

### Đã làm

Marketplace authenticated dùng semantic token chung cho surface/border/text/
brand/status/motion. Mobile menu giờ là drawer thật có scrim, trạng thái
`aria-expanded`, trả lời Escape và tự đóng sau khi chọn view. Menu tài khoản
không còn biến mất trên mobile. Search/sort/filter có accessible name, filter và
My Apps đồng bộ `aria-pressed`, số kết quả dùng live region; running job dùng
progressbar được clamp 0–100. Thuật ngữ “Jobs đang chạy” đổi thành “Việc đang
chạy”; trạng thái empty/error và nút/form được bổ sung semantics.

Thêm `tests/test_109_home_shell_ui.py` để khóa drawer, filter/progress và token.

### Test/browser đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| Targeted foundation/jobs/home/design/UI | **68 passed**, 1 warning trong 76,12 giây |
| Full suite lượt đầu | **1 fail**, 1.921 pass: đổi chữ đầu badge blocker thành hoa làm vỡ contract hiển thị cũ |
| Test blocker + HOME-001 sau sửa | **4 passed**, 1 warning trong 2,40 giây |
| `python -m pytest -q` lượt xác nhận | **1.922 passed**, 8 skipped, 23 subtests, 1 warning trong 539,05 giây |
| `python tools\scan_source_secrets.py` | **0 finding**, PASS (1.125 file / 158.511 dòng) |
| Playwright canary local 390 px | drawer mở/đóng/Escape/My Apps PASS; account hiện; overflow 0; field thiếu nhãn 0; console/network lỗi 0 |
| Playwright canary local 1280 px | search empty + sort PASS; overflow 0; console/network lỗi 0 |

Regression badge được sửa bằng cách giữ nguyên chuỗi chữ thường đã có; không đổi
logic blocker. Browser dùng DB/canary cô lập trong `tmp/`, không dùng production.

### Quyết định mới

Không phát sinh quyết định nền. HOME-001 chỉ thực thi Q46/Q52; chưa thay contract
My Apps/Workspace/Templates/Resources của HOME-002.

### Cách lùi lại

Revert commit HOME-001. Không có migration hay dữ liệu production cần rollback.

### Việc tiếp theo

H15.S3.2 HOME-002; chỉ đóng H15.S3 và mở app Tạo video sau khi gate này PASS.

---

## 2026-08-03 — H15.S2.3: Ranh giới operator và Settings/Status

- **Mục tiêu:** khóa quyền vận hành và làm rõ kiến trúc thông tin trước khi
  chuyển sang Home authenticated.
- **Hạng mục:** SET-001 hoàn thành; H15.S2 hoàn thành đủ BILL/JOBS/SET.
- **Trạng thái:** code/test/browser xong; chưa deploy production.

### Đã làm

Thêm một nguồn kiểm tra quyền operator dùng chung cho dependency route và
template: tài khoản admin cấu hình hoặc user có role `admin`. Toàn bộ route
`/settings`, thao tác cấu hình và `/status` trả 403 cho user thường; các liên kết
operator cũng không xuất hiện trong header, marketplace side nav hoặc account
menu của user thường.

Settings được chia thành nhóm `details` có điều hướng nhanh, chỉ mở một nhóm ban
đầu; bổ sung mô tả operator, nhãn upload CSV, announced state và semantic status.
Status dùng token Carbon Red chung. Cả hai trang có target cảm ứng/mobile ổn định;
form Content Vault không còn gây tràn ngang ở 390 px. Thêm
`tests/test_108_settings_boundary_ui.py` và test hành vi 403 trong
`tests/test_69_web_jobs.py`.

### Test/browser đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| Targeted foundation/settings/content/jobs/UI | **78 passed**, 1 warning trong 41,29 giây |
| `python -m pytest -q` | **1.919 passed**, 8 skipped, 23 subtests, 1 warning trong 543,39 giây |
| `python tools\scan_source_secrets.py` | **0 finding**, PASS (1.124 file / 158.317 dòng) |
| Playwright SQLite/canary local `/settings` + `/status`, 390/1280 px | operator 200; user thường 403; overflow 0; trường thiếu nhãn 0; console error/request fail 0 |

Lượt targeted đầu có 14 lỗi 422 do dependency mới thiếu annotation `Request`;
đã sửa annotation và chạy lại xanh 78/78. Browser dùng DB/canary cô lập ở
`tmp/`; không đọc hoặc ghi dữ liệu production.

### Quyết định mới

Không phát sinh quyết định nền. Phân quyền giao diện và route cùng gọi helper
`is_operator`, tránh hai định nghĩa admin lệch nhau.

### Cách lùi lại

Revert commit SET-001. Không có migration hay dữ liệu production cần rollback.

### Việc tiếp theo

H15.S3 Home authenticated — xử lý HOME-001 rồi HOME-002 theo thứ tự, không song
song; chỉ mở H15.S4 sau khi toàn bộ gate Home PASS.

---

## 2026-08-03 — H15.S2.2: Job Center

- **Mục tiêu:** biến trang Việc thành trung tâm theo dõi/hành động an toàn.
- **Hạng mục:** JOBS-001 hoàn thành; H15.S2 còn SET-001.
- **Trạng thái:** code/test/browser xong; chưa deploy production.

### Đã làm

Thêm filter trạng thái/app, nhãn trạng thái Việt hóa, progressbar/live region và
mobile table. Detail có cancel owner-only + refund nguyên tử; job lỗi/đã hủy có
retry tạo job mới và giữ credit lại theo contract. Kết quả lưu trữ được suy ra
chỉ từ `result` field hậu tố `_key/_keys`, tải qua index mờ owner-only; raw result
JSON/storage key không còn render cho khách. Filename download được sanitize.

Thêm `tests/test_107_jobs_ui.py` và test hành vi trong `test_69_web_jobs.py` cho
cancel/refund/retry và chặn user khác hủy job.

### Test/browser đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| Targeted jobs/queue/UI | **28 passed**, 1 warning |
| `python -m pytest -q` | **1.915 passed**, 8 skipped, 23 subtests, 1 warning trong 546,55 giây |
| `python tools\scan_source_secrets.py` | **0 finding**, PASS |
| Playwright SQLite/canary local 390 px | queued → cancel → retry ID mới; filter `queued/demo` đúng; overflow 0; label đủ; console/network sạch |

Không dùng dữ liệu production. DB/log browser nằm trong `tmp/`, không commit.

### Quyết định mới

Không phát sinh quyết định nền. Generic Job Center tái dùng `jobs.cancel`,
`credit.hoan` và `submit_with_credit`; không tạo hàng đợi/ledger thứ hai.

### Cách lùi lại

Revert commit JOBS-001. Không có migration hoặc dữ liệu production cần rollback.

### Việc tiếp theo

H15.S2.3 SET-001; sau khi PASS mới đóng H15.S2 và mở Home authenticated.

---

## 2026-08-03 — H15.S2.1: Billing UI và lịch sử đơn

- **Mục tiêu:** hoàn thiện money state trước Job Center và Settings.
- **Hạng mục:** BILL-001 hoàn thành; H15.S2 còn JOBS-001 và SET-001.
- **Trạng thái:** code/test/browser xong; chưa deploy production.

### Đã làm

`/nap` hiển thị báo giá trọn gói, credit base/bonus/tổng và CTA có số tiền.
Route tải tối đa 10 đơn mới nhất theo đúng `user_id`; trang có lịch sử mã đơn,
thời gian, tiền, credit và trạng thái Việt hóa. Chi tiết đơn có tóm tắt/hạn đơn,
PayOS external-link rõ và HTMX status dùng live region. Enum nội bộ không còn
hiện thẳng cho khách.

Thêm `tests/test_106_billing_ui.py`. Không đổi ledger, idempotency, webhook,
package snapshot hay transaction boundary.

### Test/browser đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| `python -m pytest tests\test_76_billing.py tests\test_106_billing_ui.py -q` | **20 passed**, 1 warning |
| Full suite lượt đầu | **2 fail**, 1.908 pass: release scanner bắt đúng fixture local tạm; không phải lỗi billing |
| Hai release gate sau khi xóa fixture tạm | **2 passed** |
| `python -m pytest -q` lượt xác nhận | **1.910 passed**, 8 skipped, 23 subtests, 1 warning trong 545,59 giây |
| `python tools\scan_source_secrets.py` | **0 finding**, PASS |
| Playwright SQLite/canary local `/nap` + tạo/xem đơn tại 390/1280 | 200; overflow 0; tạo đơn/history/pending poll PASS; console error 0 |

Browser dùng DB SQLite cô lập và cổng 8102. PayOS không cấu hình, không gọi cổng
thật và không đọc/ghi credit hoặc đơn production. Fixture script chứa mật khẩu
local giả đã bị xóa ngay sau kiểm thử; DB/log tạm nằm trong `tmp/`, không commit.

### Quyết định mới

Không phát sinh quyết định nền. Lịch sử đơn dùng hàm nội tại `liet_ke_don` đã có,
không xây kho dữ liệu hay API mới.

### Cách lùi lại

Revert commit BILL-001. Không có migration/dữ liệu/provider state cần rollback.

### Việc tiếp theo

H15.S2.2 JOBS-001; chỉ sau khi ticket đó PASS mới mở SET-001.

---

## 2026-08-03 — H15.S1: Public catalog và Auth

- **Mục tiêu:** hoàn thiện bề mặt vào hệ thống trước khi sửa trang có dữ liệu/tiền.
- **Hạng mục:** PLAT-001 và AUTH-001 hoàn thành; H15.S2 là bước kế tiếp.
- **Trạng thái:** code/test/browser xong; chưa deploy production.

### Đã làm

Sửa shared mobile header để co đúng tại 390 px; catalog public từ overflow 13 px
về 0 và search/menu có accessible name. Tạo `_auth_brand.html`, đồng nhất
login/register/forgot/reset/verify theo LTT Carbon Red. Mọi input nhìn thấy có
label liên kết; error dùng `role=alert`, success dùng `role=status`; control cao
tối thiểu 44 px và focus state giữ nguyên design contract.

Thêm `tests/test_105_public_auth_ui.py` và mở rộng design regression cho mobile
header. Không đổi contract auth, CSRF, rate limit, token hoặc dữ liệu tài khoản.

### Test/browser đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| `python -m pytest tests\test_104_design_system_contract.py tests\test_105_public_auth_ui.py tests\test_65_dang_ky.py tests\test_72_vanhanh.py -q` | **43 passed**, 1 warning |
| `python -m pytest -q` | **1.907 passed**, 8 skipped, 23 subtests, 1 warning trong 552,41 giây |
| `python tools\scan_source_secrets.py` | **0 finding**, PASS |
| Playwright local `/`, `/login`, `/register`, `/forgot-password` tại 390/1280 | 200; overflow 0; label đủ; console error 0; failed request 0 |
| Playwright local reset/verify token giả | error state đúng, HTTP 400 chủ ý |
| Playwright local đăng nhập sai | alert “Sai tên đăng nhập hoặc mật khẩu”, HTTP 401 chủ ý, không ghi dữ liệu production |

### Quyết định mới

Không phát sinh quyết định nền. PLAT-001 hoàn tất riêng trước AUTH-001; không mở
Stage 2 khi Stage 1 chưa qua full gate.

### Cách lùi lại

Revert commit H15.S1. Thay đổi chỉ là template/CSS/test, không có migration,
provider, credit ledger hay dữ liệu người dùng.

### Việc tiếp theo

H15.S2 theo đúng thứ tự: BILL-001 → JOBS-001 → SET-001, mỗi ticket được browser
check trước khi chuyển ticket kế.

---

## 2026-08-03 — H15.S0: LTT Carbon Red design contract

- **Mục tiêu:** tạo một nguồn style và gate dùng chung trước khi sửa từng trang/app.
- **Hạng mục:** DS-001..005 hoàn thành; H15.S1 là bước kế tiếp.
- **Trạng thái:** code/docs/test/browser xong; chưa deploy production.

### Đã làm

Tạo `docs/DESIGN_SYSTEM_LTT.md`, khóa semantic token, shell, component,
accessibility, icon/type/content vocabulary và gate phase. Chuyển token runtime
trong `server/static/ltt.css` sang LTT Carbon Red, giữ alias tương thích để các
app được migrate lần lượt. Gỡ palette xanh lặp trong base template và đổi nền
public/auth sang Carbon Red.

Bổ sung focus-visible 2 px, reduced-motion, touch target 44 px trên coarse
pointer. Menu header đóng bằng Escape và trả focus. Thêm
`tests/test_104_design_system_contract.py` để chặn palette xanh/token hai nguồn
quay lại.

### Test/browser đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| `python -m pytest tests\test_104_design_system_contract.py tests\test_31_audit_readiness.py tests\test_37_p3_web_foundation.py tests\test_70_admin_h3.py -q` | **70 passed**, 1 warning |
| `python -m pytest -q` | **1.901 passed**, 8 skipped, 23 subtests, 1 warning trong 566,49 giây |
| `python -m pytest tests\test_104_design_system_contract.py -q` sau chỉnh cuối | **4 passed** |
| `python tools\scan_source_secrets.py` | **0 finding**, PASS |
| Playwright local desktop 1280 + mobile 390: public/login | token `#ef3731`; login overflow 0; focus 2 px; Escape/focus-return PASS; console error 0; failed app request 0 |

Catalog public ở 390 px còn overflow 13 px trên local. Đây là finding đã định
danh PLAT-001 của H15.S1, không coi là PASS giả trong H15.S0.

### Quyết định mới

Không phát sinh quyết định nền mới; thực thi Q52 bằng compatibility alias để
rollback/migrate tuần tự, không big-bang.

### Cách lùi lại

Revert commit H15.S0. Không có migration, dữ liệu hay thay đổi provider. Alias
cũ nằm cùng token source nên rollback CSS không yêu cầu đổi template/app state.

### Việc tiếp theo

1. H15.S1/PLAT-001: sửa catalog public mobile overflow và thêm regression.
2. H15.S1/AUTH-001: đồng nhất toàn bộ auth state theo contract, đủ label/focus.

---

## 2026-08-03 — H15.AUDIT: baseline toàn nền tảng

- **Mục tiêu:** kiểm kê/audit full app, trang và website; khóa style/roadmap tuần tự.
- **Hạng mục:** H15.AUDIT hoàn thành; H15.S0 là bước kế tiếp.
- **Trạng thái:** audit/source/browser/benchmark/plan xong; chưa sửa UI/runtime/deploy.

### Đã làm

Chạy LTT-AQA DEEP cho 11 module, control plane và gói website. Dùng Playwright
production anonymous và canary admin tạm; canary đã deactivate/revoke sau audit.
Mọi bề mặt authenticated/app đã kiểm render 200, desktop không overflow và không
có console/app request failure. Phát hiện public catalog mobile tràn 48 px; touch
target nhỏ và field thiếu accessible name xuất hiện rộng.

Xác nhận bốn style layer: base public/auth/shared xanh, Marketplace/Studio đỏ local,
React/Admin riêng. Domain `lttstudios.com` không phục vụ gói website trong repo;
nhiều URL source trả 404. Đối chiếu official docs theo họ sản phẩm, chấm baseline
Q70/M50/E86 và khóa Q52: LTT Carbon Red, system-first, triển khai tuần tự.

Tạo hồ sơ `docs/APP_AUDIT/platform/2026-08-03/` gồm inventory, truth, journey/
control, benchmark, scorecard, findings, quyết định, roadmap, 38 vé và evidence.

### Test đã chạy

| Lệnh/flow | Kết quả |
|---|---|
| Playwright anonymous/authenticated production desktop/mobile | PASS render; findings F-001..F-014 được ghi |
| `python -m pytest tests\test_61_setup_scripts.py tests\test_62_khoa_logic.py -q` | **94 passed** trong 0,64 giây |
| `python -m pytest -q` | **1.896 passed**, 8 skipped, 23 subtests, 1 warning trong 588,17 giây |
| `python tools\scan_source_secrets.py` | **0 finding**, PASS |

Full suite được chạy trong tiến trình redirect log vào `tmp/h15-audit-pytest.*.log`
để tránh giới hạn thời gian/đầu ra của kênh lệnh; đã theo dõi tới trạng thái
`FINISHED` và exit code 0. Log tạm không đưa vào commit.

### Quyết định mới

Q52 đã thêm: LTT Carbon Red, system-first, mỗi app PASS rồi mới sang app kế;
Socialbot giữ đóng băng Q10.

### Cách lùi lại

Revert commit H15.AUDIT; không có migration/runtime/production UI cần lùi. Canary
audit đã bị vô hiệu hóa, session revoke; audit rows được giữ theo runbook.

### Còn tồn đọng

Stage 0–15 chưa triển khai. Field Core Web Vitals và competitor hands-on trial
chưa có; Market Score là baseline official-docs.

### Việc tiếp theo

1. H15.S0 DS-001..005: design contract + regression harness.
2. H15.S1 sửa public mobile overflow và Auth theo contract mới.

---

## 2026-08-03 — H14.0: chuẩn hóa LTT-AQA v1.0

- **Mục tiêu:** lưu lâu dài bộ quy tắc audit toàn diện app và hồ sơ dùng lại.
- **Hạng mục:** H14.0 — hoàn thành.
- **Trạng thái:** tài liệu/quy trình xong; không sửa runtime, không deploy.

### Đã làm

Tạo `docs/quy_tac_audit.md` làm nguồn chuẩn cho audit nội tại, tính năng, mọi
control, UX/UI, accessibility, hiệu năng, security/credit, AI/provider, vận hành
và benchmark sản phẩm thế giới. Chuẩn tách Quality Score, Market Score, Evidence
Confidence và Release Gate để điểm cao không che blocker tiền/bảo mật/dữ liệu.

Tạo bộ hồ sơ `docs/APP_AUDIT/_MAU/` gồm charter, current truth, journey/control,
competitor benchmark, scorecard, findings, decision gate và roadmap. Liên kết
LTT-AQA đứng trước UI-RD, bổ sung tài liệu vào trang bắt đầu, khóa quyết định Q51
và đồng bộ kế hoạch H14.0.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `python -m pytest tests\test_61_setup_scripts.py tests\test_62_khoa_logic.py -q` | **94 passed** trong 0,62 giây |
| `python -m pytest -q` | **1.896 passed**, 8 skipped, 23 subtests, 1 warning trong 567,74 giây |
| `python tools\scan_source_secrets.py` | **0 finding**, PASS |

Hai lượt full suite trực tiếp qua kênh lệnh trước đó bị timeout 120/300 giây;
lượt thứ hai còn làm stdout pytest báo `OSError 22`. Đây là lỗi giới hạn kênh
thu output, không phải test fail. Lượt cuối chạy cùng lệnh trong tiến trình ẩn,
redirect log vào `tmp/h14-pytest.*.log`, theo dõi đến exit và có summary PASS ở
trên; log thuộc `tmp/` không đưa vào commit.

### Quyết định mới

Q51 đã thêm vào `docs/QUYET_DINH_NEN_TANG.md`: mọi audit app toàn diện dùng
LTT-AQA; gate critical không được bù bằng điểm.

### Cách lùi lại

Revert commit H14.0; không có migration, dữ liệu hoặc production state cần lùi.

### Còn tồn đọng

Chưa áp dụng LTT-AQA cho một app cụ thể trong hạng mục chuẩn hóa này.

### Việc tiếp theo

1. Khi nhận lệnh `AUDIT <MODE> -- app: <slug>`, sao chép mẫu và chạy A0–A10.
2. Chỉ gọi UI-RD nếu finding/Decision Gate kết luận cần redesign.

---

## 2026-08-03 — H13.autosubvideo AS9: production public PASS

- **Mục tiêu:** khóa toàn bộ release gate, deploy có backup/rollback và chứng minh
  workflow Studio thật qua Cloudflare bằng dữ liệu canary.
- **Hạng mục:** AS9 hoàn thành; Auto Sub AS0–AS9 đóng.
- **Trạng thái:** production public, health/worker/GPU/browser PASS.

### Đã làm

Full suite đầu 1.890 test xanh. Dependency Python, npm của Auto Sub/Canvas, strict
app contract, secret scan, frontend typecheck/test/build đều sạch. Migration rehearsal
SQLite `upgrade -> downgrade base -> upgrade head` PASS. Tạo backup off-drive có
secrets + `pg_dump`, mở archive, bung restore cô lập và `pg_restore --list` PASS.

Lượt update đầu dừng sau khi stop service vì luôn tạo lại sidecar WhisperX nhiều GB
ở ổ C dù sidecar CUDA hợp lệ đã cấu hình ở ổ D. Dữ liệu và release trước vẫn nguyên;
release mới đã extract. Chạy migration PostgreSQL tới `d4e5f6a7b8c9`, dùng sidecar
đã kiểm CUDA, khởi động web/worker/Codex và health phục hồi. Sửa `update.ps1` để ưu
tiên sidecar cấu hình khỏe; sửa env loader tìm NSSM dưới Root và bỏ qua placeholder
optional rỗng thay vì chặn rollout.

Operator canary khi Studio còn off: project create/list/update revision/archive đều
PASS. Sau chuyển public, Playwright bắt thêm hai lỗi Q48: `/upload-url` vẫn trả vé R2
khi cờ direct unset, và preview redirect R2 bị CORS; khi proxy thì R2 StreamingBody
không seek được gây 500. Nay upload mặc định multipart <=90 MB, preview proxy Range
theo iterator hỗ trợ stream không seek; chỉ redirect/direct khi flag Q48 bằng 1.

Canary cuối dùng video 10,054 giây do Dev cho phép + SRT 3 cue: upload/import/preview
206, quote 1 credit, submit 202, worker GPU done 100%, balance 100 -> 99, tạo sáu
nhóm key video/ASS/SRT/VTT/JSON/ZIP. Video Range trả 206/1.024 byte, ZIP trả 200
`application/zip`. 1440/1280/390/360 đều overflow 0; browser cuối console 0 và
network sạch. Canary user/session đã vô hiệu, cookie state cục bộ đã xóa; project/
job/artifact audit được giữ. Rollout `public` đang hiệu lực.

Phát hiện release builder từng đóng gói `.playwright-cli` (301 file evidence vào
release đã deploy). Đã xóa thư mục đó khỏi production, thêm exclusion + regression,
rebuild archive cuối còn 1.040 file; không còn browser evidence trong release.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `python -m pytest -q` trước canary | **1.890 passed**, 8 skipped, 23 subtests, 1 warning |
| `python -m pytest -q` sau toàn bộ hotfix | **1.894 passed**, 8 skipped, 23 subtests, 1 warning |
| `npm test -- --run && npm run build` (`frontend/autosub-studio`) | **9 passed**, typecheck/Vite PASS |
| `npm audit --audit-level=high` (Auto Sub + Canvas) | **0 vulnerability** cả hai |
| `python -m pip check` | không có dependency vỡ |
| `python tools\\lint_app_contract.py --strict` | 10 app, **0 ERROR/0 WARN** |
| `python tools\\scan_source_secrets.py` | **0 finding**, PASS |
| migration rehearsal SQLite | upgrade/downgrade/upgrade **PASS** |
| backup + restore rehearsal + `pg_restore --list` | **PASS** |
| `python tools\\build_release.py --output D:\\LTTReleases` | 1.040 file, 125,9 MB, secret gate PASS |
| `setup\\4-nghiem-thu.ps1` | PASS; 1 cảnh báo Google/social cũ không liên quan |
| Playwright production + canary GPU | full workflow PASS; 4 viewport overflow 0; console/network cuối sạch |

### Quyết định mới

Không có. Các sửa đổi thực thi đúng Q48–Q50; browser R2 direct vẫn off cho tới khi
bucket CORS được cấu hình và kiểm thật.

### Cách lùi lại

Đặt `LTT_AUTOSUB_STUDIO_ROLLOUT=off`, nạp lại env và restart web để về form legacy.
Nếu cần lùi binary: drain/cancel/settle job rồi chạy `deploy\\windows\\rollback.ps1`;
`C:\\LTTPlatform\\app.previous` còn release trước AS9. Không xóa project/job/ledger/audit.

### Còn tồn đọng

- Q48: bucket R2 chưa có CORS browser; direct upload >90 MB vẫn bị khóa đúng thiết kế.
- Pyannote soft-disabled vì production chưa có `LTT_HF_TOKEN`; editor/import/render
  và WhisperX vẫn hoạt động.
- Cảnh báo `sheet_id`/`google_credentials_path` thuộc app Google/social cũ.

### Việc tiếp theo

1. Theo dõi error rate, queue/GPU và credit settlement Auto Sub sau public rollout.
2. Khi có quyền cấu hình R2 CORS, chạy browser gate rồi mới bật Q48.

---

## 2026-08-03 — H13.autosubvideo AS8: hardening/GPU/corpus PASS

- **Mục tiêu:** phá lỗi ở biên bảo mật, tiến trình AI, tải lớn, GPU thật, offline
  và responsive trước full release gate.
- **Hạng mục:** AS8 hoàn thành; AS9 bắt đầu tiếp theo.
- **Trạng thái:** code/backend/frontend/browser/GPU PASS trên dữ liệu cô lập.

### Đã làm

Benchmark A/B WhisperX phát hiện sidecar có thể deadlock vì `stderr=PIPE` không
được drain. Đổi sang log tạm, thêm timeout cấu hình và dừng cả process tree khi
hủy/timeout. Security fuzz phát hiện cue `{\\p1}` được giữ như ASS override; đổi
sanitizer để toàn bộ brace người dùng thành fullwidth trước khi thêm tag nội bộ.

Thêm tool benchmark tái lập cho GPU end-to-end, ASR metrics-only và project lớn.
Ba video Dev chỉ định đã render qua job/credit thật ở 720p, 1080p, 4K bằng NVENC;
giữ FPS/audio, đủ video/ASS/SRT/VTT/JSON/ZIP. A/B tiếng Anh tiny/large-v3 aligned,
WER 0 trên mẫu tổng hợp; giữ rõ giới hạn đây không phải field accuracy. 3.000 cue
xuất artifact trong 0,438s, peak 8,98 MB. Thêm owner/range/traversal/limit fuzz.

UI autosave offline nay báo tiếng Việt và không nói sai đã lưu. Playwright xác
minh bốn viewport không overflow, accessible name đầy đủ; offline tạo đúng failed
PUT dự kiến, phục hồi/reload xong console và network sạch.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `python -m pytest tests\\test_81_autosubvideo.py tests\\test_103_autosub_projects.py tests\\test_61_setup_scripts.py tests\\test_62_khoa_logic.py tests\\test_85_app_contract_lint.py tests\\test_86_usage_rate_limit.py tests\\test_95_agent_canvas_build.py tests\\test_44_release_build.py -q` | **170 passed**, 1 warning |
| `npm test -- --run` (`frontend/autosub-studio`) | **9 passed** |
| `npm run build` (`frontend/autosub-studio`) | typecheck + Vite **PASS**, JS 224,35 kB, CSS 15,27 kB |
| GPU smoke 720p/1080p/4K bằng `tools/autosub_gpu_smoke.py` | **3/3 PASS**, NVENC, credit/artifact/probe đúng |
| A/B bằng `tools/autosub_asr_benchmark.py` | tiny + large-v3 **PASS**, aligned, timing monotonic |
| `python tools/autosub_load_benchmark.py --cues 3000 ...` | **PASS**, 0,438s, 8,98 MB |
| `python tools\\scan_source_secrets.py` | **0 finding**, PASS |
| Playwright fixture 1440/1280/390/360 + offline/recovery | overflow 0; accessibility PASS; sau reload console 0, network sạch |

### Quyết định mới

Không có. AS8 thực thi Q49–Q50; không đổi contract sản phẩm.

### Cách lùi lại

Revert commit AS8. Có thể đặt `LTT_AUTOSUB_STUDIO_ROLLOUT=off` để quay về legacy;
timeout sidecar và sanitizer chỉ harden, không đổi schema/database.

### Còn tồn đọng

AS9 full suite, dependency/release/migration/backup rehearsal và production canary.

### Việc tiếp theo

1. Chạy toàn bộ release gate AS9.
2. Backup, deploy theo quy trình hiện hành, smoke/canary rồi mới bật public.

---

## 2026-08-03 — H13.autosubvideo AS7: render/export/job control PASS

- **Mục tiêu:** xuất project Studio bằng snapshot bất biến, báo đúng chi phí
  trước khi giữ credit và đóng đủ vòng đời job/artifact.
- **Hạng mục:** AS7 hoàn thành; AS8 bắt đầu tiếp theo.
- **Trạng thái:** backend/UI/browser PASS trên fixture cô lập.

### Đã làm

Thêm quote và submit render owner-scoped theo ETag/revision. Server chuẩn hóa output,
chụp toàn payload, ký SHA-256 và đặt snapshot vào job; sửa project sau submit không
đổi nội dung worker. Chỉ sau popup xác nhận mới giữ credit. Hủy queued/running hoàn
credit idempotent; retry chỉ nhận render terminal có snapshot/source còn toàn vẹn.

Worker render đúng track visible/được chọn, layer theo z-index, đặt track phụ lên trên,
giữ aspect và hỗ trợ source/720p/1080p/4K cùng MP4/MKV/WebM. Artifact gồm video,
ASS kết hợp, SRT/WebVTT/JSON từng track và ZIP manifest; route tải owner-scoped.
Job status có elapsed/ETA từ tiến độ đo. Đã sửa lỗi cleanup: exception cancel từ
progress callback nay kill FFmpeg trước khi thoát, tránh job đã hoàn tiền nhưng GPU
vẫn chạy. UI có render panel, output/track/export controls, popup credit, progress,
cancel/retry/download; payload cũ được normalize additive khi đọc.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `python -m pytest tests\test_81_autosubvideo.py tests\test_103_autosub_projects.py -q` | **29 passed**, 1 warning |
| `npm test -- --run` (`frontend/autosub-studio`) | **8 passed** |
| `npm run build` (`frontend/autosub-studio`) | typecheck + Vite **PASS**, JS 224,29 kB, CSS 15,27 kB |
| `python tools\scan_source_secrets.py` | **0 finding**, PASS |
| Playwright 1440 và 390 px, video `video (10).mp4` + SRT fixture | quote 200, popup/submit 202/cancel 200, overflow 0, console 0, request ứng dụng không lỗi |

### Quyết định mới

Không có. Triển khai theo Q49–Q50 và contract AS7 đã khóa.

### Cách lùi lại

Tắt `LTT_AUTOSUB_STUDIO_ROLLOUT` để về form legacy; revert commit AS7; giữ nguyên
project, ledger và artifact đã tạo. Khi drain, hủy job đang chạy để hoàn hold.

### Còn tồn đọng

AS8 phải chạy corpus render/ASR, fuzz, long/load, GPU thật, accessibility và parity.

### Việc tiếp theo

1. AS8 hardening/security/performance/GPU end-to-end.
2. AS9 full release gate; chỉ deploy production vì người dùng đã yêu cầu rõ.

---

## 2026-08-02 — H13.autosubvideo AS6: auxiliary AI workflow PASS

- **Mục tiêu:** nối phân vai Pyannote và dịch Gemini thành job 0-credit có kiểm
  soát, không tạo kết quả giả khi môi trường thiếu credential/model.
- **Hạng mục:** AS6 hoàn thành; AS7 chưa bắt đầu.
- **Trạng thái:** contract/backend/UI PASS; local soft-disabled do thiếu token/key.

### Đã làm

Thêm job types diarize/translate, quota lần lượt 6/20 mỗi ngày, user row lock,
dedupe, owner 404, revision snapshot, cooperative cancel, JSON status và artifact
riêng. Pyannote Community-1 chạy trong sidecar; audio preload bằng WhisperX/FFmpeg
thành tensor 16 kHz để né TorchCodec DLL không tương thích, rồi gán speaker theo
overlap thời gian lớn nhất. Telemetry Pyannote tắt trong runner.

Gemini dùng APIKEYS pool/category chat, structured JSON, chunk 60 cue/12.000 ký tự,
kiểm đúng ID/thứ tự/không rỗng trước khi tạo translation track; lỗi không apply
partial. UI đọc capability thật, có language picker/progress/cancel; thiếu cấu hình
thì disable và nói rõ lý do.

### Test đã chạy

- `python -m pytest tests\test_103_autosub_projects.py tests\test_81_autosubvideo.py tests\test_61_setup_scripts.py tests\test_85_app_contract_lint.py tests\test_86_usage_rate_limit.py -q`
  → **102 passed**, 1 warning.
- `npm test` → **7 passed**; `npm run build`/typecheck → **PASS**; JS 218,42 kB,
  CSS 13,55 kB.
- Sidecar `import pyannote.audio` → PASS; `LTT_HF_TOKEN` local không có,
  `GEMINI_API_KEY` env local không có. Không gọi mạng/model bằng credential giả.
- Playwright fixture video+3 cue: capability endpoint 200, hai action disabled,
  hiện đúng hai lý do thiếu cấu hình; overflow 0, console 0, network sạch.

### Cách lùi lại

Revert commit AS6; job đang chạy cancel hợp tác. Không đặt `LTT_HF_TOKEN` hoặc
không có Gemini key thì capability tự off, editor/import/render khác vẫn dùng được.

### Còn tồn đọng

Không thể smoke model gated Pyannote tại máy dev khi operator chưa cấp token đã
accept Community-1. Translation sẽ dùng key pool production nếu có; local không
có key nên chỉ test adapter bằng mock có validate schema.

### Việc tiếp theo

AS7: render từ immutable project snapshot, quote/credit popup, multi-track output,
resolution source/720p/1080p/4K, job progress/cancel/retry/download bundle.

## 2026-08-02 — H13.autosubvideo AS5: style/animation parity PASS

- **Mục tiêu:** cho Dev chỉnh toàn bộ hình thức phụ đề và bảo đảm preview/render
  đọc cùng một contract.
- **Hạng mục:** AS5 hoàn thành; AS6 chưa bắt đầu.
- **Trạng thái:** local browser/backend PASS; production chưa deploy.

### Đã làm

Đổi `style` project từ dict mở sang model có kiểu/forbid extra, kiểm hex và giới
hạn mọi field. API trả đúng 8 preset nội tại. React có tabs template/style/animation,
font/size/colors/outline/shadow/background/position/bold/italic/karaoke/keyword và
duration. Preview hiển thị word highlight theo playhead.

Animation chỉ gồm none/fade/pop/slide-up vì đây là tập React CSS và ASS/libass đều
render xác định được. ASS builder sinh `fad`, scale+t hoặc move tương ứng; không có
hiệu ứng UI-only. Mobile không còn giấu inspector mà đặt nó dưới editor.

### Test đã chạy

- `python -m pytest tests\test_103_autosub_projects.py tests\test_81_autosubvideo.py -q`
  → **23 passed**, 1 warning; gồm style injection reject, preset API và ASS pop tag.
- `npm test` → **7 passed**; `npm run build`/typecheck → **PASS**; JS 215,07 kB
  (gzip 67,60), CSS 12,84 kB (gzip 3,58).
- Playwright desktop: TikTok Bold → size 70 → karaoke word → pop; autosave PASS,
  overlay có đúng animation + một word active; overflow 0, console 0, requests sạch.
- Playwright 390×844: inspector Style truy cập được, size 60 autosave PASS,
  document overflow 0, console/network sạch.

### Cách lùi lại

Revert commit AS5; project payload cũ `{preset}` vẫn đọc được nhờ defaults. Flag
production vẫn off.

### Còn tồn đọng

AS6–AS9: diarization/translation, render/job control, hardening và release.

### Việc tiếp theo

AS6: pyannote diarization tùy token, Gemini translation theo track, quota/dedupe/
cancel và UI trạng thái auxiliary 0-credit.

## 2026-08-02 — H13.autosubvideo AS4: cue editor và timeline PASS

- **Mục tiêu:** biến shell thành editor transcript thực, dùng được trên desktop
  và mobile với nhiều track, không mất revision khi autosave dồn.
- **Hạng mục:** AS4 hoàn thành; AS5 chưa bắt đầu.
- **Trạng thái:** local browser PASS; production chưa deploy.

### Đã làm

Thêm cue list/search/editor, chỉnh text/timing/speaker, add/delete/split/merge,
multi-track/visibility, preview overlay, seek/playhead và timeline cue blocks. Pointer
drag/resize dùng cùng một logic cho mouse/touch; mobile giữ timeline cuộn nội bộ,
không làm tràn document. Waveform decode audio thật bằng WebAudio; codec browser
không hỗ trợ thì hiện fallback trung tính và editor vẫn hoạt động.

Undo/redo giữ 80 snapshot và có Ctrl/Cmd+Z/Y. Autosave được sửa thành hàng đợi
tuần tự/coalesced: edit tới trong khi PUT đang chạy không abort request đã có thể
commit ở server, nhờ đó không tự tạo revision conflict.

### Test đã chạy

- `npm test` → **7 passed**.
- `npm run build` (gồm typecheck) → **PASS**; JS 208,50 kB/gzip 65,83;
  CSS 10,91 kB/gzip 3,13.
- Playwright với video user 10s + `browser_sample.srt`: import 3 cue, sửa nội dung,
  tách thành 4 cue, undo/redo, autosave revision và desktop pointer drag → PASS.
- Playwright 390×844: reload persistence + pointer drag → PASS; document overflow
  0 (timeline cuộn nội bộ 580px); console 0; mọi API/media request 2xx/206.

### Cách lùi lại

Revert commit AS4; AS3 shell/project/upload vẫn hoạt động. Production flag vẫn off.

### Còn tồn đọng

AS5–AS9: style/animation parity, auxiliary AI, render/job, hardening và release.

### Việc tiếp theo

AS5: schema style có kiểu, preset inspector và animation/karaoke preview-render parity.

## 2026-08-02 — H13.autosubvideo AS3: React Studio shell PASS

- **Mục tiêu:** thay form đơn bằng production React island nhưng giữ đường lùi
  legacy và nối project/upload thật, không dựng trạng thái giả.
- **Hạng mục:** AS3 hoàn thành; AS4 chưa bắt đầu.
- **Trạng thái:** code/local browser đã chạy; production chưa deploy.

### Đã làm

Thêm frontend Vite/React/TypeScript pin phiên bản, hashed bundle và build-meta được
release/setup gate kiểm tra. Studio shell bám ảnh tham khảo: stepper, ba cột,
preview/transport/timeline state và responsive mobile. Project load/create/name/
autosave dùng revision/ETag; upload file thật nối storage/project source, import
transcript và tạo WhisperX job thật. Production flag thiếu bundle tự lùi form cũ.

Cache static chỉ immutable cho file hash. Fixture browser có hai guard và database/
storage riêng; không đọc/ghi production. Video test do Dev chỉ định được đọc từ
`G:\My Drive\AI\Tool AI\Video seedacne\video (10).mp4`, bản upload nằm trong
storage fixture cô lập.

### Test đã chạy

- `npm test` trong `frontend/autosub-studio` → **5 passed**.
- `npm run typecheck && npm run build` → **PASS**; JS 198,75 kB (gzip 62,74),
  CSS 7,95 kB (gzip 2,38), manifest/build-meta hợp lệ.
- `python -m pytest tests\test_103_autosub_projects.py tests\test_81_autosubvideo.py tests\test_95_agent_canvas_build.py tests\test_44_release_build.py tests\test_61_setup_scripts.py -q`
  → **128 passed**, 1 warning.
- Playwright fixture thật 1440×1000 và 390×844 → upload 3,0 MB PASS; metadata
  10s/864×496; reload persistence PASS; overflow ngang 0; console 0; request
  API/media đều 2xx/206.

### Cách lùi lại

Đặt `LTT_AUTOSUB_STUDIO_ROLLOUT=off`; router tự render form legacy. Dữ liệu project
additive không ảnh hưởng render cũ.

### Còn tồn đọng

AS4–AS9: cue editor/timeline, style parity, AI auxiliary, render/job UI, hardening
và deploy production.

### Việc tiếp theo

AS4: editor cue + multi-track timeline/waveform + undo/redo + mobile drag.

## 2026-08-02 — H13.autosubvideo AS2: WhisperX/import/quota PASS

- **Mục tiêu:** tạo transcript từ import hoặc ASR mặc định mà không thu credit/
  phá môi trường GPU chung.
- **Hạng mục:** AS2 hoàn thành; AS3 chưa bắt đầu.
- **Trạng thái:** code + sidecar dev đã chạy; production chưa deploy.

### Đã làm

Manifest nhận `autosubvideo.transcribe`; callback chỉ miễn phí bốn operation
server allowlist, render không có default-free. API import ghi track vào đúng revision.
API transcribe kiểm owner/source/revision, khóa user khi check quota, giới hạn 12
lượt/ngày và 120 phút/job, dedupe, tạo job 0-credit. Worker WhisperX-first lưu
artifact transcript, chỉ apply khi revision khớp; conflict không làm mất kết quả.

WhisperX 3.8.6 buộc Torch 2.8 nên được cài ở `D:\LTTWhisperX`, không downgrade
Torch 2.11 của app khác. Installer idempotent tạo sidecar production riêng và ghi
chỉ tên biến/path `LTT_WHISPERX_PYTHON` vào app.env. Main Python `pip check` sạch.

### Test đã chạy

- `python -m pytest tests\test_103_autosub_projects.py tests\test_81_autosubvideo.py tests\test_61_setup_scripts.py tests\test_85_app_contract_lint.py tests\test_86_usage_rate_limit.py -q`
  → **96 passed**, 1 warning.
- Sidecar: Torch **2.8.0+cu128**, CUDA=True, RTX 5060 Ti, WhisperX import PASS,
  `pip check` → no broken requirements.
- WhisperX tiny smoke 30s VI → aligned, 10 segment/64 word.
- WhisperX `large-v3` smoke 30s VI → aligned, 1 segment/15 word, 19,36 giây,
  RTF **0,645**. Không ghi transcript người dùng vào log/tài liệu.
- `python -m pip check` main env → no broken requirements.
- `python tools\scan_source_secrets.py` lượt gate → **1016 file, 146132 dòng**;
  lượt cuối sau nhật ký → **1016 file, 146184 dòng**; đều **0 finding**.
- `git diff --check` → PASS.

### Cách lùi lại

Tắt Studio; auxiliary job đang chạy được cancel; import cũ vẫn dùng. Xóa cấu hình
`LTT_WHISPERX_PYTHON` để fallback faster-whisper; sidecar độc lập không chạm main venv.

### Còn tồn đọng

- TorchCodec phát cảnh báo tương thích nhưng runner nạp audio qua WhisperX/FFmpeg và
  cả hai smoke vẫn aligned; tiếp tục theo dõi ở AS8.
- Corpus WER/DER đầy đủ chạy ở AS8 sau khi editor/render đã nối end-to-end.

### Việc tiếp theo

AS3: production React island, Studio shell và project/autosave/preview states.

## 2026-08-02 — H13.autosubvideo AS1: AppProject runtime PASS

- **Mục tiêu:** xây persistence generic và API owner-scoped cho Auto Sub Studio.
- **Hạng mục:** AS1 hoàn thành; AS2 chưa bắt đầu.
- **Trạng thái:** code/migration local đã có, production chưa deploy.

### Đã làm

Thêm model/migration `app_projects`, service generic giới hạn 1 MiB/độ sâu/bí mật,
optimistic revision và archive mềm. Thêm schema Auto Sub v1 với source, track/cue/
word timing, speaker/style/output; API create/list/get/save/archive có CSRF, ETag,
owner khác 404 và conflict 409. Logic app không nằm trong core.

### Test đã chạy

- `python -m pytest tests\test_103_autosub_projects.py tests\test_81_autosubvideo.py tests\test_62_khoa_logic.py tests\test_63_lop_csdl.py -q`
  → **56 passed**, 1 warning; gồm upgrade→downgrade base→upgrade migration.
- `python -m pytest tests\test_85_app_contract_lint.py tests\test_61_setup_scripts.py -q`
  → **71 passed**.
- `python tools\scan_source_secrets.py` → **1012 file, 145510 dòng, 0 finding**.
- `git diff --check` → PASS.

### Cách lùi lại

Giữ Studio off; backup rồi downgrade `d4e5f6a7b8c9` khi không còn writer. Form/render
cũ không phụ thuộc `AppProject`, nên vẫn hoạt động.

### Việc tiếp theo

AS2: upload/import vào project và auxiliary transcription job 0-credit có quota.

## 2026-08-02 — H13.autosubvideo AS0: contract và rollback PASS

- **Mục tiêu:** khóa ranh giới generic/app, fixture và rollback trước khi sửa runtime.
- **Hạng mục:** AS0 hoàn thành; AS1 chưa bắt đầu.
- **Trạng thái:** docs/fixture only, chưa migration, chưa deploy.

### Đã làm

Tạo `05_CONTRACT.md`: `AppProject` chỉ là container owner/app/version/revision;
Auto Sub tự validate payload v1. Khóa multi-track, auxiliary job 0-credit có quota,
render có credit, rollout off/public và rollback. Tạo fixture 11 state × 4 viewport.

### Test đã chạy

- `python -m pytest tests\test_62_khoa_logic.py tests\test_85_app_contract_lint.py -q`
  → **25 passed**.
- `python tools\scan_source_secrets.py` → **1009 file, 144995 dòng, 0 finding**.
- `git diff --check` → PASS.

### Cách lùi lại

Revert commit AS0; không có state runtime/CSDL/production.

### Việc tiếp theo

AS1: model/migration/service/API `AppProject` và schema Auto Sub v1.

## 2026-08-02 — H13.autosubvideo: khóa Decision Gate Q49–Q50

- **Mục tiêu:** ghi nhận 12 lựa chọn của Dev, dọn xung đột quyết định kiến trúc
  và cập nhật scope/phase trước khi bắt đầu BUILD.
- **Hạng mục:** H13.autosubvideo — R3.5 Decision Gate hoàn thành; AS0–AS9 chưa làm.
- **Trạng thái:** logic đã khóa; chỉ thay tài liệu, chưa sửa code/chưa deploy.

### Đã làm

Dev chọn 1C/2A/3B/4A/5A/6A/7A/8B/9A/10C/11C/12B. Q38 được đánh dấu
ĐÃ THAY và Q49 mở React/TypeScript island cho editor nhiều state, đồng thời chốt
hợp đồng PostgreSQL generic `AppProject`. Q50 khóa Quick + Full Editor, WhisperX
mặc định, pyannote tùy chọn, Gemini translation, multi-track, full mobile drag,
style/animation có render parity, output source/720p/1080p/4K và chỉ render thu credit.

Lựa chọn public được diễn giải thành: feature giữ off trong lúc build, operator
canary bằng test data, rồi chuyển thẳng public sau AS0–AS9 và G0–G7 PASS; không
có rollout sản phẩm qua admin/allowlist. ASR/diarization/translation là job 0-credit
do nền tảng tài trợ nhưng bắt buộc quota, rate-limit, dedupe và admission control.
Các tài liệu Agent đang dẫn Q38 đã được truy ngược sang Q49; nhật ký lịch sử cũ
giữ nguyên để không viết lại sự thật tại thời điểm trước.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `python -m pytest tests\test_62_khoa_logic.py tests\test_85_app_contract_lint.py -q` | **25 passed** |
| `python tools\scan_source_secrets.py` | lượt đầu **1007 file, 144814 dòng**; lượt cuối sau nhật ký **1007 file, 144866 dòng**; cả hai **0 finding — PASS** |
| `python -m pytest -q` | **1869 passed, 8 skipped, 23 subtests, 1 warning**, 489,47 giây |

### Quyết định mới

- Q49 thay Q38: hybrid theo độ phức tạp, React island cho Canvas/Auto Sub và
  `AppProject` generic; server vẫn là nguồn chân lý.
- Q50: khóa toàn bộ scope, mô hình chi phí và release của Auto Sub Studio.

### Cách lùi lại

Revert commit tài liệu của lượt này. Không có migration, code, service hay production
state để lùi; Q38 chỉ được phục hồi bằng một quyết định mới theo giao thức.

### Còn tồn đọng

- AS0–AS9 chưa triển khai; chưa có migration/API/React island/WhisperX mới.
- Cần benchmark corpus VI/EN, 1/2 speaker, noise/music/long-form tại AS0–AS2.
- Q48 CORS vẫn giới hạn browser upload >90MB.

### Việc tiếp theo

Bắt đầu AS0: thiết kế `AppProject` contract/migration/API/version/revision, React
island boundary, fixture/corpus/baseline và rollback; chỉ sang AS1 khi gate PASS.

## 2026-08-02 — H13.autosubvideo: ANALYZE và kế hoạch AS0–AS9

- **Mục tiêu:** audit ảnh Auto Sub 1680×935, app đang chạy và năng lực nội tại;
  lập ma trận/phase nâng cấp sâu trước Decision Gate, không sửa code sản phẩm.
- **Hạng mục:** H13.autosubvideo — R0–R4 ANALYZE hoàn thành; R3.5 chờ Dev.
- **Trạng thái:** nghiên cứu xong; chưa BUILD, chưa deploy.

### Đã làm

Tạo `docs/UI_REDESIGN/autosubvideo/` đủ brief, current state, reference map,
feature matrix, plan AS0–AS9 và evidence. Browser fixture cô lập xác minh UI form
hiện tại ở 1440×900 và 390×844 không overflow, console 0, `/estimate` 200.

Audit cho thấy backend đáng tái sử dụng: parser/normalizer/segmenter, 8 preset,
custom style schema, ASS/SRT builder, preview function, FFmpeg/libass/NVENC,
job/credit/R2/ownership. Khoảng trống là ASR/project/editor/timeline/autosave/
speaker/translation/style UI/cancel cooperative. `D:\BOT GEMINI` được đọc-only:
Auto Sub v3 đã có phần lớn editor/template/preview/cancel/retry; không import chéo.

Nghiên cứu nguồn gốc xác nhận faster-whisper hiện có hỗ trợ word timestamp/VAD;
WhisperX phù hợp benchmark alignment; pyannote Community-1 chạy local nhưng model
gated/token và không đồng nghĩa nhận dạng tên; wavesurfer.js có Regions/Timeline.
Máy có RTX 5060 Ti 16GB, faster-whisper/CTranslate2 và model cache. Video test
user chỉ được ffprobe đọc metadata, không sửa. Decision Gate gồm 12 lựa chọn;
project persistence và React editor có thể tạo quyết định nền tảng mới nên chưa BUILD.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| Playwright fixture 1440×900 + 390×844 | PASS; overflow 0, console 0, estimate 200 |
| `python -m pytest tests\test_61_setup_scripts.py tests\test_62_khoa_logic.py tests\test_81_autosubvideo.py tests\test_85_app_contract_lint.py -q` | **106 passed** |
| `python tools\scan_source_secrets.py` | **1007 file, 144737 dòng, 0 finding — PASS** |
| `python -m pytest -q` lượt đầu | wrapper timeout 5 giây; tiến trình bị dừng, không phải test fail |
| `python -m pytest -q` chạy lại | **1869 passed, 8 skipped, 23 subtests, 1 warning**, 491,32 giây |

### Quyết định mới

Chưa có. Chờ Dev trả lời Decision Gate; nếu chọn React island/generic AppProject
thì phải ghi quyết định mới và contract gap trước code.

### Cách lùi lại

Revert commit tài liệu của lượt này; không có code/migration/service/production để lùi.

### Còn tồn đọng

- Chưa có corpus multi-speaker/long-form/noise để benchmark AS0.
- Q48 CORS vẫn giới hạn browser upload >90MB, không riêng Auto Sub.
- R3.5 chưa khóa, toàn bộ AS0–AS9 chưa triển khai.

### Việc tiếp theo

Dev trả lời 12 lựa chọn trong `UI_REDESIGN/autosubvideo/00_BRIEF.md`; cập nhật
quyết định/ma trận rồi mới bắt đầu AS0.

## 2026-08-02 — H13.upscalevideo UP8: release và production PASS

- **Mục tiêu:** nghiệm thu đầy đủ, deploy có backup/rollback và xác minh GPU thật
  trên production thay vì dừng ở test local.
- **Hạng mục:** H13.upscalevideo — UP8 hoàn thành; UP0–UP8 đóng.
- **Trạng thái:** đã deploy production.

### Đã làm

GPU smoke local dùng nội dung video Downloads dẫn xuất tạm 480p: output thật
1882×1080, 24 fps, audio state giữ đúng, hoàn tất 11,756 giây trên RTX 5060 Ti;
mọi frame/artifact tạm được dọn. Benchmark AI Detail và GPU smoke chỉ lưu JSON
tổng hợp, không tạo artwork mới.

Trước deploy tạo backup off-drive có secrets + `pg_dump`; mở archive và chạy
`pg_restore --list` PASS. Production Alembic đã ở head. Lần update đầu bị dừng
trước rotate vì shell không elevated và script cũ nuốt lỗi stop service; production
vẫn chạy bản cũ. Sửa `update.ps1` bắt buộc admin, đợi từng service dừng thật rồi
mới rotate; 82 test deploy PASS. Hai lượt update elevated sau đó đều exit 0,
`app.previous` được giữ và các service trở lại Automatic/Running.

Canary production admin nộp hai video 480p qua UI, cả hai job GPU `done`, credit
giảm đúng 3/job, compare source/output thật hoạt động. Lượt đầu phát hiện R2 CORS
thiếu; multipart fallback vẫn hoàn tất nhưng console đỏ. Thêm Q48: browser direct
R2 chỉ bật sau CORS gate, deploy hotfix; lượt hai không còn PUT CORS lỗi, console
0, desktop/mobile không overflow. Canary đã bị vô hiệu, session thu hồi; cookie,
video và restore extract tạm đã xóa, audit job được giữ.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `python -m pytest -q` trước release | **1868 passed**, 8 skipped, 23 subtests, 1 warning |
| `python -m pytest -q` sau hotfix Q48 | **1869 passed**, 8 skipped, 23 subtests, 1 warning |
| `python tools\scan_source_secrets.py` | **0 finding** |
| `python -m pip check` | **No broken requirements** |
| backup off-drive + archive open + `pg_restore --list` | **PASS** |
| `setup\4-nghiem-thu.ps1` | PASS, 1 cảnh báo cấu hình cũ: `sheet_id`/`google_credentials_path` chưa điền |
| Production Playwright 1440×900 + 360×800 | PASS; console 0; overflow 0; 2 GPU job done |
| Health loopback + Cloudflare | `ready`, `production`, database `ok` |

### Quyết định mới

Q48: cờ browser R2 direct mặc định off đến khi CORS bucket được kiểm thật. Watch
Agent direct R2 không đổi vì client ngoài browser không bị CORS.

### Cách lùi lại

`C:\LTTPlatform\app.previous` chứa release ngay trước hotfix. Nếu có regression:
thu hồi Watch token/disable task, dừng nhận job mới, drain/cancel + settle/refund,
rồi chạy `deploy\windows\rollback.ps1`; không xóa ledger/job/artifact audit.

### Còn tồn đọng

- Bucket R2 chưa có CORS browser. Cấu hình rule đã ghi ở Q48/kế hoạch tồn đọng,
  browser kiểm PASS rồi mới bật `LTT_R2_BROWSER_UPLOAD_ENABLED=1`.
- Cảnh báo nghiệm thu cũ `sheet_id` và `google_credentials_path` không thuộc
  Upscale, không chặn release này.

### Việc tiếp theo

Chờ ảnh/tên app tiếp theo để bắt đầu pipeline UI-RD mới.

## 2026-08-02 — H13.upscalevideo UP4–UP7: batch, Watch, telemetry và benchmark PASS

- **Mục tiêu:** triển khai toàn bộ tính năng mới đã khóa ở Q47 trước release,
  không biến control trong ảnh thành mock.
- **Hạng mục:** H13.upscalevideo — UP4, UP5, UP6, UP7 hoàn thành.
- **Trạng thái:** xong local; chưa deploy production.

### Đã làm

Batch nhận tối đa ba video, quote tổng server-side, preflight toàn bộ và tạo
job/hold credit trong một transaction; request id chống double-submit. Watch
Agent chạy local, chờ size+mtime ổn định, xử lý tối đa ba, dùng token bearer
tách miền có rotate/revoke, R2 direct hoặc local fallback, archive success,
quarantine lỗi vĩnh viễn và giữ nguyên source khi offline/thiếu credit/token lỗi.

Telemetry admin đọc GPU model/util/temp/VRAM, queue/heartbeat và storage khi
backend cung cấp; payload không có filename/storage key. User chỉ thấy progress,
vị trí và ETA sau tối thiểu ba mẫu lịch sử; nếu thiếu ghi “Đang ước tính”.

Benchmark Fast/Quality trên video Downloads bằng RTX 5060 Ti hoàn tất. Quality
chỉ hơn Fast 0,0954 dB trong bộ degraded, chậm khoảng 4,8 lần và không phải model
temporal riêng. AI Detail tiếp tục DEFER; Pause/Delete/retention không bị ghép lén.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `python -m pytest tests\test_72_vanhanh.py tests\test_82_upscalevideo.py tests\test_85_app_contract_lint.py -q` | **43 passed**, 1 warning |
| `python tools\benchmark_upscale_ai_detail.py ... --samples 12` | PASS; 10 frame; JSON evidence đã lưu |
| Playwright user Watch token rotate/revoke | PASS; raw token không in vào log/evidence |
| Playwright admin desktop/mobile | PASS; telemetry thật; console 0; overflow 0 |
| `python -m pytest -q` | chưa chạy; bắt buộc tại UP8 |

### Quyết định mới

Không đổi Q47. Bộ cài Watch dùng Scheduled Task tại logon vì Python agent không
phải Windows Service native; token nằm trong user environment, không nằm repo/log.

### Cách lùi lại

Thu hồi Watch token và uninstall task trước; ẩn batch/telemetry controls. Job đã
nộp vẫn drain/cancel/settle theo UP1. AI Detail vốn đang tắt.

### Còn tồn đọng

UP8 full regression, GPU smoke end-to-end, backup/release/deploy production.

### Việc tiếp theo

1. GPU smoke nguồn video Downloads trên derivative hợp lý.
2. Full pytest/secret scan/browser gates và deploy có rollback.

## 2026-08-02 — H13.upscalevideo UP2–UP3: Studio và compare thật PASS

- **Mục tiêu:** thay UI thử nghiệm bằng Upscale Studio theo ảnh tham khảo, nhưng
  mọi control phải nối vào hành vi thật và compare không được lộ storage key.
- **Hạng mục:** H13.upscalevideo — UP2, UP3 hoàn thành.
- **Trạng thái:** xong local; chưa deploy production.

### Đã làm

Xây Studio shell responsive gồm settings, dropzone, compare và queue. Fast/
Quality, target, codec, preserve FPS/audio và preview đều truyền đến handler;
AI Detail ghi rõ đang nghiên cứu, batch và Watch Folder giữ đúng phase. Upload
R2/local, probe metadata và quote server-side tiếp tục dùng contract hiện có.

Compare lấy source theo `job_id` đã kiểm owner/app, hỗ trợ cả video upload trực
tiếp và nguồn Seedance, LocalStorage Range 206 hoặc redirect presigned của R2;
output/download giữ owner scope. File thiếu và job người khác trả 404.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `python -m pytest tests\test_67_hang_doi_job.py tests\test_72_vanhanh.py tests\test_82_upscalevideo.py tests\test_85_app_contract_lint.py -q` | **53 passed**, 1 warning |
| Playwright 1440×900 và 390×844 với video Downloads | PASS; không overflow; console 0; upload/estimate 200; source/output 206 |
| `python -m pytest -q` | chưa chạy; bắt buộc tại UP8 trước deploy |

### Quyết định mới

Không có quyết định mới; triển khai Q47. Không tạo ảnh mới.

### Cách lùi lại

Tắt compare và template Studio; giữ UP1/backend tương thích và download output.

### Còn tồn đọng

UP4–UP8: batch tối đa 3, Watch Agent, telemetry/ETA, benchmark AI Detail và
nghiệm thu/deploy.

### Việc tiếp theo

1. UP4 batch tối đa 3 với preflight/transaction/dedupe.
2. UP5 Watch Agent dùng cùng batch contract.

## 2026-08-02 — H13.upscalevideo UP0b–UP1: lifecycle và cầu Seedance PASS

- **Mục tiêu:** đóng contract Cancel/refund và dùng chung workflow Upscale từ
  Seedance trước khi thiết kế thêm Studio UI.
- **Hạng mục:** H13.upscalevideo — UP0b, UP1 hoàn thành.
- **Trạng thái:** xong local; chưa deploy production.

### Đã làm

Giữ trạng thái `cancelled` additive trong bảng job hiện có. `jobs.cancel()` chỉ
nhận queued/running. Worker có `is_cancelled()` bền vững; exception của subprocess
sau cancel không còn đi qua `fail()` để retry job đã hủy. NCNN nhận `cancel_check`;
FFmpeg probe/extract/encode/concat dùng subprocess polling và kill khi hủy; copy
input cũng có checkpoint. Refund được gọi ở web và worker nhưng ledger idempotent.

Seedance quote/confirm chỉ nhận job done của đúng owner, giá do server tính và nộp
qua `submit_upscale_job()`. Duration dùng result rồi fallback params. Thêm fixture
browser cô lập sử dụng video Downloads qua biến `LTT_UPSCALE_BROWSER_VIDEO`; không
đọc/sửa dữ liệu production.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `python -m pytest tests\test_67_hang_doi_job.py tests\test_72_vanhanh.py tests\test_79_taovideo.py tests\test_82_upscalevideo.py -q` | **67 passed**, 1 warning |
| `python -m pytest tests\test_67_hang_doi_job.py tests\test_72_vanhanh.py tests\test_82_upscalevideo.py -q` | **50 passed**, 1 warning |
| Playwright isolated Seedance quote/confirm + Upscale cancel | PASS; console 0; app requests 200/206 |
| `python -m pytest -q` | chưa chạy; bắt buộc tại UP8 trước deploy |

### Quyết định mới

Không có quyết định mới; triển khai Q47.

### Cách lùi lại

Ẩn nút/route nhận Upscale mới, để job active drain hoặc cancel/settle; revert commit
UP1 sau khi không còn job active. Không xóa ledger, job hoặc artifact audit.

### Còn tồn đọng

UP2–UP8: Studio UI, compare gate đầy đủ, batch 3, Watch Agent, telemetry, benchmark
AI Detail và release production.

### Việc tiếp theo

1. UP2 Studio shell + upload/quote/options thật.
2. UP3 compare owner-scoped và browser đa nguồn.

## 2026-08-02 — Recovery UI-RD Upscale: audit lại hội thoại và khóa Q47/UP0–UP8

- **Mục tiêu:** sửa sai lệch quy trình, khẳng định full phạm vi Upscale và lập
  phase triển khai có PASS gate/rollback trước khi viết tiếp.
- **Hạng mục:** H13.upscalevideo — UP0a hoàn thành; UP0b–UP8 chưa hoàn thành.
- **Trạng thái:** kế hoạch xong; code hiện tại vẫn WIP, chưa deploy.

### Đã làm

Audit lại ảnh `UPSCALE.png`, lịch sử quyết định Dev, app `upscalevideo`, engine,
FFmpeg, storage/R2, jobs/credit và diff chưa commit. Đính chính: không đóng băng
tính năng mới. Dev đã khóa full scope gồm compare thật, batch tối đa 3, Cancel
(Pause hoãn), Watch Folder làm ngay, telemetry chi tiết admin-only, delete/retention
hoãn, AI Detail chỉ bật khi có engine thật, rollout sau gate; Seedance dùng chung
`submit_upscale_job()` với popup quote/confirm credit.

Thêm Q47 và hồ sơ `UI_REDESIGN/upscalevideo/` gồm brief, current state, reference
map, feature matrix và kế hoạch UP0–UP8. Đồng bộ H13.taovideo: Decision Gate đã
khóa và cầu Seedance→Upscale nằm chung contract UP1/UP3. Kế hoạch hiện phản ánh
đúng sự thật: code cancel/compare/studio đang WIP, không đánh dấu hoàn thành.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| Đối chiếu source/diff + ảnh tham khảo | PASS, phát hiện plan cũ còn ghi “chờ Decision Gate” |
| `python -m pytest tests\test_61_setup_scripts.py tests\test_62_khoa_logic.py -q` | **92 passed** |
| `python tools\scan_source_secrets.py` | **947 file, 137.274 dòng, 0 finding — PASS** |
| `python -m pytest -q` | chưa chạy; dành cho gate code/release UP8 |

### Quyết định mới

Q47 đã thêm vào `QUYET_DINH_NEN_TANG.md`. Không thay quyết định cũ; Q47 cụ thể
hóa UI-RD và mở rộng sản phẩm Upscale đã được Dev chọn.

### Cách lùi lại

Revert riêng các thay đổi docs Q47/H13/upscalevideo của lượt này. Không rollback
code WIP bằng lệnh phá hủy; code đó phải được phân lát và audit ở UP0b.

### Còn tồn đọng

- Worktree code Seedance/Upscale/core vẫn bẩn và chưa commit.
- UP0b chưa có baseline đa viewport/state; UP1 lifecycle chưa đủ race/subprocess
  cancellation tests; batch/Watch Agent/telemetry chưa được xây.

### Việc tiếp theo

1. UP0b: baseline browser + phân loại WIP/rollback.
2. UP1: đóng contract cancel/refund và Seedance bridge bằng test failure/ownership.
3. Chỉ khi UP1 PASS mới triển khai UP2 studio shell.

## 2026-08-02 — H13.taovideo: audit UI-RD Seedance, chờ khóa logic

Đã phân tích ảnh `seedance.png` và code app hiện hành. Ảnh là mục tiêu cho
`/taovideo` (tên hiển thị Tạo video AI), không phải căn cứ tạo app/slug `seedance`
mới. Hồ sơ `UI_REDESIGN/taovideo/` đã ghi layout 3 vùng, map control, ma trận feature
và ranh giới dữ liệu thật. Engine sẵn có gồm model capability, refs image/video/audio,
asset://, translate, estimate/reserve/settle credit, polling/resume và output
owner-scoped; UI hiện chỉ là form + 12 job gần nhất.

Không đổi code, không tạo asset, không gọi ImageGen. Không dùng hình video trong ảnh
tham khảo làm thumbnail giả cho output của user. Các thao tác delete/bulk/retry,
prompt history và asset/template library bị để DEFER vì hiện chưa có lifecycle,
retention, audit hay route thật. Đã đưa Decision Gate cho Dev khóa trước BUILD.

**Bằng chứng thật:** Playwright Cloudflare `GET /taovideo` chuyển đúng tới
`/login?next=/taovideo`; console 0 error/0 warning, request động RUM 204. Đã đối
chiếu `apps/taovideo/routes.py`, template, jobs, models, cost và regression hiện có.

**Rollback:** docs-only, revert commit audit; không ảnh hưởng production/code/data.

## 2026-08-02 — H13 Home: marketplace workspace từ ảnh tham khảo

Đã chốt Q46 theo tám lựa chọn của Dev và hoàn thành lại trang chủ theo UI-RD.
Khách chưa đăng nhập vẫn thấy catalog công khai; user đã đăng nhập thấy workspace
marketplace với sidebar desktop, search Ctrl+K, category/sort, card app, recent
activity/running jobs owner-scoped và credit thật. `Popular` chỉ xếp bằng aggregate
job theo slug, không hiển thị số giả. Community vẫn disabled và Pro membership không
được giả lập vì chưa có backend/entitlement thật.

Theo yêu cầu mới, đã dừng ImageGen: năm cover giao diện được crop trực tiếp từ
`TRANGCHU.png` do Dev cung cấp; quy trình UI-RD cũng được bổ sung thứ tự ưu tiên
asset LTT → crop ảnh user cho phép → CSS/SVG → ImageGen khi thật sự cần. Không có
migration, không đổi dữ liệu production trong hạng mục này. Regression bổ sung xác
nhận user không thấy activity/running job của người khác.

**Lệnh/kết quả thật trước deploy:**

- `python -m pytest -q` → **1852 passed, 8 skipped, 23 subtests passed**, 1 warning,
  474,54s.
- `python tools\scan_source_secrets.py` → 929 file, 135.777 dòng, **0 finding**.
- `python tools\lint_app_contract.py --strict` → 10 app, **0 ERROR, 0 WARN**.
- Playwright local desktop/mobile: artwork tải từ `server/static/home-covers/`,
  grid mobile `scrollWidth=390` tại viewport 390, Ctrl+K/search/category/sort PASS;
  console 0 lỗi và không có request ứng dụng thất bại.

**Rollback:** `deploy\windows\rollback.ps1`; vì không có migration, chỉ phục hồi
release trước đó, không đụng dữ liệu runtime.

**Deploy/production:** backup độc lập `D:\LTTBackups\ltt_data_20260802_174125.zip`
đã đọc được và có `pg_dump` PASS. Release `ltt-release-1.0.0.zip` (1.169 file,
79,4 MB, SHA-256 `8f2cac…c75da44e`) đã được giải nén vào `C:\LTTPlatform\app`;
`app.previous` vẫn được giữ. Phiên update bị ngắt sau khi dừng service nhưng trước
bước khởi động; không chạy lại nguyên script để tránh thay bản rollback. Đã khởi
động lại web/worker/Codex sidecar, chạy `alembic upgrade head` trên release mới
(no-op) và health production `ready`, database `ok` PASS. Playwright qua
Cloudflare với catalog public: 200, console 0 error/0 warning, request động RUM
204; phiên browser chưa dùng tài khoản production nên kiểm authenticated workspace
ở local test environment, không tạo/đọc dữ liệu người dùng production.

## 2026-08-02 — H13.0: chuẩn hóa redesign app từ ảnh

Đã nghiên cứu UI hiện hành và chốt Q45: ảnh tham khảo là mục tiêu thị giác cùng
nguồn giả thuyết, không phải contract nghiệp vụ. Tạo quy trình UI-RD v1.0 với
R0–R10, hồ sơ bằng chứng, ma trận KEEP/RESTYLE/EXTEND/BUILD/REJECT/DECORATIVE/
DEFER, gate G0–G7 và ba chế độ ANALYZE/BUILD/FULL. Quy trình ưu tiên tái dùng
registry/jobs/credit/provider/storage/media/Canvas hiện có, bắt buộc logic thật
trước khi bật control mới và đưa phát hiện lặp lại vào test/token/quy tắc.

Playwright production catalog desktop 1440×1000 và mobile 390×844: desktop có
header 56 px, grid ba cột; console 0, failed request 0. Mobile đổi nav thành
burger nhưng page rộng 438 px trong viewport 390 px, card rộng 390 px tại x=24:
có overflow ngang baseline. Chưa sửa vì phiên này chỉ nghiên cứu/quy trình.
Canary authenticated dừng trước khi tạo user do credential PostgreSQL workspace
không khớp dịch vụ; không sửa secret/DB và không tạo session. H13.2 phải baseline
lại trang authenticated bằng môi trường test/canary hợp lệ.

**Lệnh/kết quả thật:** đọc source truth/plan/log và map manifest/routes/templates/
jobs của ba họ UI; Playwright desktop/mobile console 0, network 0 lỗi;
`prepare_agent_canary.py` FAIL an toàn trước tạo user do PostgreSQL auth.
`python -m pytest -q` → **1851 passed, 8 skipped, 23 subtests passed**, 1 warning
deprecation, 493,84s. `python tools\scan_source_secrets.py` → **0 finding**.

**Rollback:** docs-only; revert commit H13.0. Không đổi production/code/DB.

## 2026-08-02 — Audit sau rollout và redeploy production

Đã audit lại source sạch tại commit `baf06e9` và production đang chạy. Dependency
Python `pip check` không vỡ; npm production audit 0 vulnerability; 10 app strict
lint 0/0; secret scan 0. Script nghiệm thu xác nhận web/worker/tunnel chạy, cổng
8100 chỉ nghe loopback, health local + Cloudflare `ready`, `/docs` 404, 11 app
nạp `ok`, config không BOM và admin-env bị vô hiệu đúng Q29.

Log web còn một traceback lịch sử ở Chat AI Studio: route từng truyền boolean
`is_admin` vào context, che mất Jinja global `is_admin(request)` của header và gây
`TypeError: 'bool' object is not callable`. Source/release hiện tại đã dùng tên
`user_is_admin` nên production không còn lỗi; Playwright tái hiện trang
`/chataistudio` trả 200, console/network sạch. Đã bổ sung regression test render
trọn trang bằng admin DB thật để lỗi shadow global không quay lại. Lượt full suite
đầu fail 2 test release vì placeholder session trong test mới bị secret scanner
chặn; đổi sang placeholder test chuẩn, chạy lại release gate và full suite xanh.

Playwright production trước deploy còn chạy một Canvas `text.script` thật tới
`done`, actual 7, toàn API 2xx. Sau deploy kiểm lại Chat AI Studio và Canvas qua
Cloudflare: console 0 error/0 warning, không failed request. Canary đã bị vô hiệu,
session thu hồi và file browser state ngoài repo đã xóa; audit data được giữ.

**Lệnh đã chạy và kết quả thật:**
- `python -m pip check` → không có broken requirement.
- `npm audit --omit=dev` → 0 vulnerability; typecheck + 13 frontend test PASS.
- `python -m pytest tests\test_44_release_build.py tests\test_83_chataistudio.py -q`
  → 39 passed.
- Full suite lượt đầu → **2 fail, 1848 pass** do scanner chặn placeholder test;
  không deploy ở trạng thái đỏ.
- Full suite cuối `python -m pytest -q` → **1850 passed, 8 skipped,
  23 subtests passed**, 1 warning deprecation, 467,18s.
- `python tools\scan_source_secrets.py` → 909 file, 133.850 dòng, 0 finding.
- `python tools\lint_app_contract.py --strict` → 10 app, 0 ERROR, 0 WARN.
- Backup đầy đủ `D:\LTTBackups\ltt_data_20260802_161249.zip` → archive đọc được,
  `pg_dump` production PASS.
- Release 1.0.0 → 1.138 file, 75,5 MB, secret scan 0; deploy update + Alembic
  + health PASS; `app.previous` được giữ.
- Playwright production trước/sau deploy → Chat AI + Agent Canvas PASS,
  console 0/0, network 0 lỗi không mong đợi.

**Cảnh báo không chặn:** `sheet_id` và `google_credentials_path` trong config
chung chưa điền; đây là cấu hình app Google/social cũ, không ảnh hưởng các app
Agent/Canvas vừa audit.

**Rollback:** `deploy\windows\rollback.ps1`; với Agent có run active thì đặt
rollout `off`, drain/cancel/settle trước khi đổi binary.

## 2026-08-02 — H12 P13 hoàn tất production, rollout public

Người dùng đã cấp quyền production rõ ràng. Đã backup đầy đủ sang
`D:\LTTBackups` gồm `pg_dump` và secret archive được bảo vệ, build release 1.0.0
qua secret gate rồi cập nhật `C:\LTTPlatform`. Migration AgentRun + workflow
Canvas chạy thành công trên PostgreSQL production; web/worker/Codex sidecar và
Cloudflare Tunnel đều chạy, cổng 8100 chỉ nghe loopback, health loopback và edge
đều `ready`. Script update được sửa để dừng/khởi động cả `LTTStudioCodex`, vì
sidecar từng giữ khóa thư mục release làm lượt deploy đầu dừng an toàn trước khi
đổi binary. Script nghiệm thu được đồng bộ Q29/Q30: production phải vô hiệu
admin-env và trang `/` là catalog công khai.

Đã thêm rollout bốn mức theo Q44 và thực thi đủ `off → admin → allowlist →
public`. Feature-off trả 503 đúng mong đợi. Admin canary production qua Cloudflare
tạo Canvas `text.script`, validate, quote 7, approve, executor chạy `done`, actual
7. Một user thường trong allowlist và một user thường không allowlist ở mức public
đều tạo run thành công; hai run kiểm quyền được cancel, settlement/refund giữ đúng.
Metrics production cuối: 3 run (1 done, 2 cancelled), estimated 21, actual 15,
refund 6. Không dùng dữ liệu người dùng thật.

Playwright phát hiện CSP chặn Cloudflare Web Analytics; đã chỉ mở đúng
`static.cloudflareinsights.com` cho script và `cloudflareinsights.com` cho
connect, có regression test. Endpoint metrics trực tiếp còn làm browser gọi
`/favicon.ico` 404; đã redirect về asset SVG có sẵn và thêm test. Lượt browser
cuối trên Canvas public và metrics admin: console 0 error/0 warning, network 0
failed request không mong đợi. Các file storage state chứa cookie nằm ngoài repo
và được xóa sau nghiệm thu.

**Lệnh đã chạy và kết quả thật:**
- `powershell ... backup.ps1 -IncludeSecrets -BackupDir D:\LTTBackups` → PASS,
  archive đọc được, `pg_dump` production PASS.
- `python tools\build_release.py` → release 1.0.0, 1.127 file, 75,5 MB,
  secret scan trong archive 0.
- `deploy\windows\update.ps1 ...` → migration production PASS, health production
  `ready`; previous release được giữ tại `C:\LTTPlatform\app.previous`.
- `setup\4-nghiem-thu.ps1` → 0 lỗi; 1 cảnh báo cấu hình Google cũ không chặn
  Agent; 11 app nạp `ok`, `/docs` 404, tunnel/loopback PASS.
- Playwright CLI production edge → rollout và Canvas E2E như trên; lượt cuối
  console **0/0**, network **0 failed request**.
- Frontend: typecheck/build PASS, 13 test PASS; strict app lint 10 app 0/0.
- `python -m pytest -q` → **1849 passed, 8 skipped, 23 subtests passed**,
  1 warning deprecation, 474,97s.
- `python tools\scan_source_secrets.py` → **0 finding, PASS**.

**Rollback:** đặt `LTT_AGENT_CANVAS_RUN_ROLLOUT=off`, nạp lại env và restart web;
drain/cancel/settle run active trước khi dùng `app.previous`. Schema và audit giữ
nguyên để forward-fix.

## 2026-08-02 — H12 P13: hardening dev/staging PASS, production còn khóa

Đã harden phần được phép triển khai: plan/approve/create-run dùng limiter chặt;
giới hạn 3 run active/user được serialize bằng row lock; caps sẵn có giữ 32 step,
fanout 4, retry 2, JSON 64 KiB/depth 20. Validator chặn URL/protocol, path và
command/shell do plan cấp. Production mặc định không cho tạo run Canvas nếu chưa
bật rõ `LTT_AGENT_CANVAS_RUN_ENABLED`; tick/cancel vẫn hoạt động để drain an toàn.
Request POST/PUT/PATCH dưới `/agent/` còn bị chặn sớm ở 128 KiB trước endpoint;
cap kiểm cả `Content-Length` lẫn số byte body thực, không phụ thuộc client khai đúng.

Correlation ID của request được ghi vào workflow-source decision rồi nối tự nhiên
qua run/step/child job. Admin audit chỉ trả user hash, status, cost, step count và
tên event; không trả goal/plan/params/PII. Metrics tổng hợp status, verify/retry,
estimated/actual ratio và refund. Admin cancel cần login admin + CSRF và dùng chính
budget settlement. Sentry boundary deny-by-default lọc request/body, prompt/goal,
email, token, cookie, credential và giới hạn chuỗi trước khi gửi; app factory đã
nối SDK khi có `LTT_SENTRY_DSN`, luôn đặt `send_default_pii=False`. Metrics live
bổ sung planning latency/error và approval rate; metrics bền bổ sung run success
và worker wait theo capability.

Failure/load drill cô lập: 10 run của 10 user tick đồng thời tạo đúng 10 dedupe key;
không submit trùng. PostgreSQL thật migration head→down→up, 6 concurrency test và
dump/restore AgentRun + workflow PASS. Các gate R2/provider/retry/GPU starvation
được chạy lại trong bộ P13 hẹp. Feature-off drill trả 503 cho run mới nhưng workflow
vẫn đọc được; đường cancel/settle được test.

**Lệnh đã chạy và kết quả thật:**
- `python -m pytest -q <18 file gate P13>` → **212 passed, 6 skipped**.
- `powershell -ExecutionPolicy Bypass -File tools\test_agent_p3_postgres.ps1`
  → **PASS**, migration up/down/up, 6 concurrency test, workflow/run restore.
- Playwright CLI canary cô lập sau middleware/telemetry: prompt→Canvas→approve→done,
  node `Hoàn tất`, console **0 error/0 warning**, API toàn 2xx; fixture đã dừng.
- `python -m pytest -q` → **1847 passed, 8 skipped, 23 subtests passed**,
  1 warning deprecation, 465.22s.
- `python tools\scan_source_secrets.py` → **869 file, 129.362 dòng,
  0 finding, PASS**.
- `python tools\lint_app_contract.py --strict` → **10 app, 0 ERROR, 0 WARN, PASS**.
- Frontend P13: typecheck/build PASS, **13 test**, npm audit 0; bundle
  386,48 KiB raw / 122,53 KiB gzip.

**Chưa chạy / không được tuyên bố PASS production:** migration production,
health ready production, browser qua Cloudflare edge, canary/internal/public rollout
và DNS. Đây là hành động production bị quy tắc dự án khóa khi chưa có yêu cầu rõ
ràng; vì vậy P13 vẫn 🟡 và H12 chưa được tuyên bố hoàn tất/public.

**Rollback đang sẵn sàng:** để `LTT_AGENT_CANVAS_RUN_ENABLED=0`, chặn run mới,
drain/cancel/settle run active, giữ schema/workflow/run audit; chỉ rollback binary
sau khi không còn run active.

**Việc tiếp theo:** khi có lệnh production rõ ràng, chạy canary theo thứ tự migration
→ ready health → admin-only account → browser Cloudflare → metrics → internal → public.

## 2026-08-02 — H12 P12: Canvas nối executor, đủ video/GPU

Đã nối prompt tiếng Việt → Canvas draft → sửa/validate/requote → snapshot đúng
revision thành AgentRun bất biến → phê duyệt đúng version + SHA-256 quote hash →
hold credit → tick executor → trạng thái node/artifact/actual/refund. Stale revision
hoặc quote trả 409; ownership chéo 404; thiếu credit 402. “Chạy lại” luôn tạo run
mới từ Plan snapshot của run cũ, không đọc draft đã sửa. Cancel quyết toán phần đã
dùng. Output storage key không đưa thành URL tuỳ ý: API artifact kiểm ownership,
R2 redirect sang presigned GET ngắn hạn, local stream private/no-store.

Test production-like dựng một Canvas duy nhất có đủ 7 ToolSpec đang chạy:
`text.script`, hai tool ảnh, `video.generate`, `video.subtitle`, `video.upscale`,
`video.short_clips`; có fan-out và ba nhánh video/GPU. Lặp tick như worker restart
không tạo child trùng, đủ bảy tool hoàn tất, actual không vượt quote và refund khớp.
Gate hẹp còn chạy R2 presigned PUT/GET, GPU capability routing và verifier retry.

Playwright fixture cô lập tại `127.0.0.1:8118`: prompt → AI dựng Canvas → quote
→ approve 7 credit → run done, node hiện “Hoàn tất”, actual 7; Chạy lại tạo run
mới; cancel giữa run trả `cancelled`, actual 4. User 3 credit bị chặn đúng 402.
Browser đã phát hiện và sửa hai lỗi thật: nút approve bị Palette che do toolbar
tràn; frontend mới làm trắng Canvas khi backend rolling cũ chưa có `artifacts`.
Luồng hợp lệ cuối console **0 error/0 warning**, network toàn 2xx; 402 chỉ xuất
hiện trong ca thiếu credit cố tình. Fixture/browser đã dừng; không production/DNS.

**Lệnh đã chạy và kết quả thật:**
- `python -m pytest -q tests/test_80_r2_storage.py tests/test_88_agent_toolspec_apps.py tests/test_92_agent_executor.py tests/test_93_agent_verifier.py tests/test_97_agent_workflow_api.py tests/test_98_agent_canvas_run.py`
  → **64 passed**.
- `npm run typecheck`, `npm test -- --run`, `npm run build` → PASS; **4 file,
  13 test PASS**; bundle 386,48 KiB raw / 122,53 KiB gzip.
- `npm audit --omit=dev` → **0 vulnerability**.
- `python -m pytest -q` → **1835 passed, 8 skipped, 23 subtests passed**,
  1 warning deprecation, 453.42s.
- `python tools\scan_source_secrets.py` → **855 file, 128.052 dòng,
  0 finding, PASS**.
- `python tools\lint_app_contract.py` → **10 app, 0 ERROR, 0 WARN, PASS**.

**Rollback:** tắt nút/API tạo run từ Canvas; drain/cancel/settle run active; giữ
workflow xem/export và các run audit. Chưa commit riêng vì worktree liên phase
đang bẩn, tránh gom nhầm thay đổi ngoài phạm vi.

**Việc tiếp theo:** P13 hardening, failure/load/restore drills và rollout gate.
Không triển khai production/DNS nếu chưa có yêu cầu rõ ràng.

## 2026-08-02 — H12 P11: node editor Canvas đầy đủ

Đã hoàn thiện editor React Flow dùng palette động từ ToolSpec: drag/drop, node
tuỳ biến, typed handles, Inspector sinh từ schema và biến thể phụ thuộc model,
pan/zoom/minimap, đa chọn, copy/paste/duplicate/delete, connect/disconnect,
undo/redo giới hạn 50, auto-layout, autosave optimistic revision, conflict,
offline retry và lưu viewport. Mobile <=640px là viewer read-only có chủ đích.
Giá và trạng thái validation lấy từ server; browser không chạy tool hay giữ
provider/storage secret. Bundle cuối 383,64 KiB raw / 121,83 KiB gzip, dưới
ngưỡng 500/150 KiB.

Playwright fixture cô lập trên `127.0.0.1:8118` đã kiểm tra desktop/mobile dark,
keyboard-only tạo và nối graph, add/config/connect/move/delete/undo/redo,
save/reload giữ đúng viewport, hai tab stale revision trả 409, offline tự lưu lại,
và graph 100 node/150 edge vẫn tương tác trong 100 ms đo tại client. Drag palette
tạo node thật. Browser gate cuối phát hiện lựa chọn cạnh còn giữ node selection;
đã sửa ưu tiên cạnh và tái hiện đúng 3 node/1 cạnh → xóa thành 3/0 → undo 3/1.
Lượt hợp lệ cuối console **0 error/0 warning**, network API đều 2xx. Fixture và
mọi browser session đã dừng; không dùng production, provider thật hoặc DNS.

**Lệnh đã chạy và kết quả thật:**
- `npm run typecheck`, `npm test -- --run`, `npm run build` → PASS; **4 file,
  12 test PASS**; production build PASS.
- `npm audit --omit=dev` → **0 vulnerability**.
- `python -m pytest -q tests/test_95_agent_canvas_build.py tests/test_96_agent_workflows.py tests/test_97_agent_workflow_api.py`
  → **16 passed**.
- `python -m pytest -q` → **1832 passed, 8 skipped, 23 subtests passed**,
  1 warning deprecation, 444.25s.
- `python tools\scan_source_secrets.py` → **824 file, 124.308 dòng,
  0 finding, PASS**.
- `python tools\lint_app_contract.py` → **10 app, 0 ERROR, 0 WARN, PASS**.

**Rollback:** tắt điều hướng/feature Canvas về viewer P8; giữ nguyên workflow
JSON và API P10. Chưa commit riêng vì worktree liên phase đang bẩn, tránh gom
nhầm thay đổi ngoài phạm vi.

**Việc tiếp theo:** P12 Agent↔Canvas↔Executor và E2E đủ video/GPU; chỉ mở vì
toàn bộ gate P11 đã PASS.

## 2026-08-02 — H12 P10: Canvas model, versioning và API

Đã thêm migration additive `agent_workflows` với owner, tên/goal, Plan schema
version, nodes/edges/viewport, draft/validated/approved/archived, budget/quote,
revision, nguồn clone và timestamp. Canvas chỉ lưu layout + config ToolSpec;
server dựng lại Plan v1 rồi chạy chính validator P4. Chuyển Plan↔Canvas giữ đủ
linear/fan-out/join/video/GPU semantics. JSON trên 64 KiB, sâu quá 20 tầng,
NaN, node/edge sai, tool/cycle/type sai, credential/storage/owner/giá do client
khai đều bị schema hoặc validator server từ chối.

API `/agent/api` có palette động từ AppManifest/ToolSpec và quyền user; list,
create/get/save, validate/requote, clone/version, archive, import/export. Không có
hard-delete endpoint. Mọi write bắt CSRF; ownership chéo trả 404. Save dùng
`revision` + `If-Match` và một câu UPDATE có điều kiện; stale trả 409, không ghi
đè. Sửa workflow approved/validated luôn về draft và xóa quote cũ. Frontend có
typed API client, conflict riêng và autosave debounce; không gửi estimated/price.

**PostgreSQL thật cô lập:** migration head → downgrade đúng về P9 head → upgrade;
6 concurrency test PASS, gồm hai editor cùng revision chỉ đúng một save thành
công và một conflict. Dump/restore xác minh cả AgentRun và `agent_workflows` probe;
database tạm đã cleanup, không dùng production.

**Browser thật qua Playwright CLI:** bundle production trên `127.0.0.1:8118`,
session user test lấy CSRF từ Canvas rồi gọi palette (7 tool, 200), create (201),
validate (200, valid, estimated=3, revision=2). Console **0 error/0 warning**;
không có failed request. Fixture/server đã dừng.

**Lệnh đã chạy và kết quả thật:**
- `python -m pytest -q tests/test_96_agent_workflows.py tests/test_97_agent_workflow_api.py tests/test_90_agent_planner_validator.py tests/test_61_setup_scripts.py`
  → **99 passed**.
- Node 22.12.0: typecheck/build PASS; Vitest **4 passed**.
- `tools\test_agent_p3_postgres.ps1` (đã mở rộng gate tới P10) → migration
  up/down/up, **6 passed**, dump/restore workflow PASS.
- `python -m pytest -q` → **1831 passed, 8 skipped, 23 subtests passed**,
  1 warning deprecation, 449.63s.
- `python tools\scan_source_secrets.py` → **778 file, 119.310 dòng,
  0 finding, PASS**.
- `python tools\lint_app_contract.py --strict` → **10 app, 0 ERROR, 0 WARN**.
- Freshness gate từng bắt `.pytest_cache` làm input hash trôi sau một lệnh chạy
  sai CWD; đã đồng bộ loại tool cache ở Node/Python và thêm regression test.

**Rollback:** tắt write API/Canvas flag, giữ JSON đã lưu. Migration downgrade đã
PASS trước dữ liệu thật; sau dữ liệu thật chỉ forward-fix. Chưa commit riêng vì
worktree liên phase/app đang bẩn, tránh gom nhầm thay đổi ngoài phạm vi.

**Việc tiếp theo:** P11 node editor đầy đủ; chỉ mở vì tất cả gate P10 đã PASS.

## 2026-08-02 — H12 P9: nền build production cho Agent Canvas

Đã tạo `frontend/agent-canvas/` bằng React 19, TypeScript, Vite và
`@xyflow/react`; mọi dependency pin exact trong lockfile, Node build pin đúng
22.12.0. Vite xuất JS/CSS hash vào `server/static/agent-canvas`, không source map,
không CDN/runtime Node production. Route đăng nhập `/agent/canvas` chỉ đọc
manifest production. Asset hash cache một năm immutable; HTML và metadata
`no-store`; CSP không mở `unsafe-eval`.

Build ghi SHA-256 của toàn bộ input frontend. `build_release.py` tính lại độc lập
và từ chối bundle stale, sai Node, thiếu/hash sai asset hoặc có source map; source,
lockfile, manifest và build metadata đều bắt buộc có trong archive. `setup/2` chỉ
kiểm bundle đã đóng gói, không cài/chạy Node trên server. Hai build sạch liên tiếp
cho cùng bốn file và SHA-256 giống hệt. Release thử ở thư mục tạm PASS, không triển
khai production/DNS.

**Browser thật qua Playwright CLI:** đăng nhập fixture cô lập rồi mở bundle do
FastAPI phục vụ tại `127.0.0.1:8118`. React Flow render, 3 control, trạng thái tải
chuyển `aria-busy=false`; HTML/CSS/JS/favicon đều 200; script duy nhất là asset
hash production; console **0 error, 0 warning**. Không có Vite dev server/client.

**Lệnh đã chạy và kết quả thật:**
- Node 22.12.0: `npm ci`, `npm run typecheck`, `npm test`, `npm run build`,
  `npm audit --audit-level=high` → PASS; **1 unit test**, **0 vulnerability**.
- `python -m pytest -q tests/test_95_agent_canvas_build.py tests/test_94_agent_app.py tests/test_61_setup_scripts.py tests/test_43_web_hardening.py`
  → **98 passed**.
- `python -m pytest -q` lượt cuối sau regression scanner → **1821 passed,
  7 skipped, 23 subtests passed**, 1 warning deprecation, 419.69s.
- Secret scan lượt đầu sau `npm ci` → **FAIL 16 false positive** vì scanner đi
  vào dependency vendored. Đã loại `node_modules`, thêm regression test; lượt cuối
  → **772 file, 118.411 dòng, 0 finding, PASS**.
- `python tools\lint_app_contract.py` → **10 app, 0 ERROR, 0 WARN, PASS**.
- `python tools\build_release.py --output <thu-muc-tam>` → **998 file, 75,3 MB,
  secret scan 0, PASS**.

**Rollback:** tắt nav/route Canvas và dùng archive release trước đó; không có
migration/dữ liệu P9. Browser fixture đã dừng. Chưa commit riêng vì worktree liên
phase/app đang bẩn; không gom nhầm thay đổi ngoài phạm vi.

**Việc tiếp theo:** P10 Canvas data model, versioning, API, round-trip Plan và
optimistic locking; chỉ bắt đầu vì toàn bộ gate P9 đã có bằng chứng PASS.

## 2026-08-02 — H12 P8: app LTT Agent AI và UX nghiệp vụ

Đã thêm độc lập `apps/agent/` theo hợp đồng app: manifest public `/agent`, routes,
jobs seam và template form/plan/run/progress. Người dùng nhập goal 10–8.000 ký tự
và budget; planner/validator tạo Plan, trang duyệt ghi rõ “tối đa N credit”. Các
POST plan/approve/tick/cancel đều CSRF; run/API khóa ownership và trả 404 chéo.
Progress HTMX self-host hiển thị waiting/submitted/done/error, attempt/fan-out,
result, actual/refund và decision log. Approval thiếu tiền dùng PRG về URL run,
không để refresh gửi lại POST. Mobile 390px không tràn ngang, focus keyboard đúng.

Executor được nối qua POST tick có CSRF, nên không cần runtime/queue thứ hai và
reopen trang tiếp tục từ checkpoint. Worker hiện hữu xử lý child. Settlement thêm
decision event append-only để UI giải thích actual/reserved/refunded. Slug `agent`
trùng thuật ngữ kiến trúc Q39/Q40 nên test substring chống hardcode loại riêng
`agent` khỏi heuristic; manifest/mount/ownership tests vẫn bảo vệ wiring app.

**Browser thật qua Playwright CLI:** server `127.0.0.1:8118`, SQLite có tên
`agent-browser-test`, planner/provider giả và worker thật; không dùng production,
DNS hay quota. Đã PASS 9 flow: anonymous→login return-to; plan/giá/0 hold;
approve→progress→result→settle; invalid; thiếu credit; cancel; verifier fail→
regenerate→pass (attempt 2/2); user B nhận 404 run/API của A; reload giữ `done`.
Các flow hợp lệ console 0 error/warning và POST tick 200. Hai GET chéo 404 sinh
console failed-resource đúng dự kiến của flow bảo mật. CSP không chặn HTMX.

**Lệnh đã chạy và kết quả thật:**
- `python -m pytest -q tests/test_94_agent_app.py tests/test_93_agent_verifier.py tests/test_92_agent_executor.py tests/test_91_agent_budget.py tests/test_60_app_registry.py tests/test_85_app_contract_lint.py`
  → **57 passed**.
- Lượt full đầu → **1813 pass, 2 fail** vì fixture browser tên `_test.py` bị
  collect/release scanner bắt chuỗi session giả. Đã đổi tên và nạp secret test từ env.
- `python -m pytest -q tests/test_44_release_build.py tests/test_94_agent_app.py`
  → **39 passed**.
- `python -m pytest -q` lần cuối → **1815 passed, 7 skipped, 23 subtests passed**,
  1 warning deprecation, 416.43s.
- `python tools\scan_source_secrets.py` → **751 file, 114.988 dòng, 0 finding, PASS**.
- `python tools\lint_app_contract.py --strict` → **10 app, 0 ERROR, 0 WARN, PASS**.

**Rollback:** đặt `apps/agent/manifest.py enabled=False`; không xóa AgentRun/
decision log/credit entries. Browser fixture và server đã dừng. Chưa commit riêng
vì worktree liên phase/app đang bẩn.

## 2026-08-02 — H12 P7: verifier và bounded retry

Đã thêm `platform_core.agent.verifier` với một kết quả chung gồm pass/score/
fault/reason/check/model/key_ref/credit. Pipeline luôn chạy `technical` →
`face_identity` → `vlm_judge`, dừng ngay ở lỗi rẻ. Technical kiểm tồn tại, MIME,
kích thước và metadata ffprobe. VLM ép schema JSON/fault hợp lệ. Lỗi provider,
timeout, JSON rác hoặc thiếu adapter thành `inconclusive`, không tự coi là đạt.

Đã kiểm kê bản nội tại `D:\BOT GEMINI\app\modules\seedance_video\face_detect.py`
ở chế độ chỉ đọc: có insightface `buffalo_sc` detection và Haar fallback nhưng
không có recognition embedding. Vì vậy `face_identity` dùng adapter recognition;
chưa cấu hình thì inconclusive, không đánh tráo detection thành identity.

Executor ghi từng lần verify/retry vào decision log đã redact email/token/secret,
policy dừng ngay, structural/inconclusive retry tối đa `max_retry`; refine và
switch_model thiếu adapter thì dừng có lý do. Validator cộng verifier credit vào
trần từng fan-out/attempt. Trước submit attempt kế tiếp, executor dự báo tool +
verifier cost và dừng trước provider nếu vượt hold. Test E2E mock: hai generation
tool (2 credit/lần) + hai VLM (1/lần) + planning 4 = actual 10.

**Lệnh đã chạy và kết quả thật:**
- `python -m pytest -q tests/test_93_agent_verifier.py tests/test_92_agent_executor.py tests/test_91_agent_budget.py tests/test_90_agent_planner_validator.py tests/test_89_agent_runs.py`
  → **55 passed**.
- `python -m pytest -q` → **1807 passed, 7 skipped, 23 subtests passed**,
  1 warning deprecation, 404.27s.
- `python tools\scan_source_secrets.py` → **707 file, 112.387 dòng, 0 finding, PASS**.
- `python tools\lint_app_contract.py --strict` → **9 app, 0 ERROR, 0 WARN, PASS**.
- VLM/provider thật: **chưa chạy**, test mặc định mock không tiêu quota; smoke thật
  là opt-in. Browser/PostgreSQL: **N/A** — P7 không thêm route/migration.

**Rollback:** với plan mới bỏ trường verify/tắt verifier; run đang chạy drain hoặc
cancel/settle, không xóa decision log đã ghi. P7 không có migration. Chưa commit
riêng vì worktree liên phase/app đang bẩn.

## 2026-08-02 — H12 P6: executor DAG, resume, fan-out và capability

Đã thêm `platform_core.agent.executor`: khóa AgentRun, đồng bộ child hiện hữu vào
checkpoint, chỉ submit step có đủ dependency, resolve `$input/$step` server-side,
fan-out theo dedupe key ổn định và join chỉ mở khi toàn bộ upstream done. Tick lặp
sau restart không tạo lại step submitted/done; child terminal được dùng để phục
hồi checkpoint nếu worker chết sau complete nhưng trước khi orchestration ghi.

Executor không giữ credit ở child. Actual được tính bằng planning cost cộng giá
tool theo đúng số attempt terminal (test P6: 4 + 1×2 = 6), luôn qua chốt
`actual <= estimated` trước settlement. Child error ghi decision event rồi settle phần đã dùng. `jobs.claim`
nhận thêm capability filter dựa trên `manifest.requires`; `None` giữ tương thích
worker đa năng hiện tại.

**Lệnh đã chạy và kết quả thật:**
- `python -m pytest -q tests/test_92_agent_executor.py tests/test_91_agent_budget.py tests/test_89_agent_runs.py tests/test_67_hang_doi_job.py`
  → **36 passed** (riêng P6: 6 passed).
- `tools\test_agent_p3_postgres.ps1` → **PASS**: Alembic up/down/up, **5 test
  concurrency passed** (gồm hai scheduler = một child), dump/restore PASS.
- `python -m pytest -q` → **1795 passed, 7 skipped, 23 subtests passed**,
  1 warning deprecation, 410.79s.
- `python tools\scan_source_secrets.py` → **705 file, 111.924 dòng, 0 finding, PASS**.
- `python tools\lint_app_contract.py --strict` → **9 app, 0 ERROR, 0 WARN, PASS**.
- Browser: **N/A** — executor chưa có UI/route.

**Rollback:** tắt nơi nhận run mới; để run active drain hoặc cancel/settle bằng
service hiện tại, sau đó gỡ executor và capability argument additive. Không có
migration P6. Chưa commit riêng vì worktree liên phase/app đang bẩn.

## 2026-08-02 — H12 P5: báo giá, approval và credit nguyên tử

Đã thêm `platform_core.agent.budget`: báo giá trần tách riêng 4 credit planning
và tổng execution theo fan-out/retry; plan sửa trước chạy tăng version và vô hiệu
approval cũ. Trước approval không có bút toán. `approve()` khóa AgentRun theo
owner/version, kiểm ngân sách/số dư, giữ toàn bộ trần đúng một lần rồi mới chuyển
`running`. State machine công khai không còn cho chuyển thẳng sang `running`.

Chốt chi phí kiểm tra `actual <= estimated` trước lần gọi trả phí; done/cancel/
error quyết toán đúng phần đã dùng và hoàn phần dư qua sổ append-only. Approval,
cancel và settlement lặp lại idempotent; owner khác không thao tác được. P5 chưa
có HTTP route nên CSRF route là N/A; P8 bắt buộc thêm test CSRF cùng endpoint.

**Lệnh đã chạy và kết quả thật:**
- `python -m pytest -q tests/test_89_agent_runs.py tests/test_91_agent_budget.py tests/test_90_agent_planner_validator.py`
  → **37 passed** (riêng P5: 8 passed).
- `tools\test_agent_p3_postgres.ps1` → **PASS**: Alembic up/down/up, **4 test
  concurrency passed** (gồm 2 approve đồng thời = 1 hold), dump/restore schema và
  probe data PASS; database tạm đã cleanup.
- `python -m pytest -q` → **1789 passed, 6 skipped, 23 subtests passed**,
  1 warning deprecation, 394.19s.
- `python tools\scan_source_secrets.py` → **703 file, 111.505 dòng, 0 finding, PASS**.
- `python tools\lint_app_contract.py --strict` → **9 app, 0 ERROR, 0 WARN, PASS**.
- Browser: **N/A** — P5 chưa có UI/route; kiểm GUI bắt buộc từ P8.

**Rollback:** chặn nơi gọi approval mới; mọi run đã hold phải được `settle()`/
`cancel()` bằng service hiện tại trước, sau đó mới gỡ export và `budget.py`.
Chưa commit riêng vì worktree chứa chuỗi phase/app untracked có sẵn, tránh gom
nhầm thay đổi ngoài phạm vi.

## 2026-08-02 — H12 P4: planner, normalizer và validator tất định

Đã thêm `normalizer.py` bóc Plan từ plain/fenced/tool arguments, chuẩn hoá alias
phẳng và chặn output >64 KiB, JSON lồng >20 tầng, rác/truncated. `planner.py`
dựng prompt có nhãn từ ToolSpec/schema/input/budget; mặc định lấy Gemini credential
qua `api_pool`/`api_keys`, không đọc env key. P4 test dùng `llm_call` mock nên không
tiêu quota và không tạo job/credit.

`validator.py` thực hiện tất định: Plan v1, 1–32 step, tool/quyền app, params,
reference `$input/$step`, kiểu cổng, dependency/cycle, cap fan-out=4/retry=2,
on_fail, giá và budget/số dư. Cấm planner đặt owner/storage key/credential/CSRF/
callback/webhook URL; artifact phải là tham chiếu, không nhận path literal. Kết quả
lỗi có `code/message/step_id/field`; báo giá cùng fixture cho kết quả giống nhau.

**Lệnh đã chạy và kết quả thật:**
- `python -m pytest -q tests/test_90_agent_planner_validator.py tests/test_88_agent_toolspec_apps.py tests/test_89_agent_runs.py tests/test_60_app_registry.py`
  → **81 passed**.
- `python -m pytest -q` → **1781 passed, 5 skipped, 23 subtests passed**,
  1 warning deprecation, 393.93s.
- `python tools\scan_source_secrets.py` → **701 file, 111.148 dòng, 0 finding, PASS**.
- `python tools\lint_app_contract.py --strict` → **9 app, 0 ERROR, 0 WARN, PASS**.
- Provider thật/browser/PostgreSQL: **N/A** — mock đủ cho P4; không route/migration.

**Rollback:** gỡ `planner.py`, `normalizer.py`, `validator.py` và export tương ứng;
P4 không có migration/dữ liệu. Chưa commit riêng vì worktree chứa chuỗi phase/app
untracked có sẵn, không gom thay đổi ngoài phạm vi.

## 2026-08-02 — H12 P3: AgentRun, checkpoint, fan-out và migration PostgreSQL

Đã thêm additive ba cột `jobs.parent_id/plan_id/step_id` (default chuỗi rỗng,
job cũ giữ nguyên) và bảng `agent_runs`: owner, goal, Plan, checkpoint JSON,
state, ngân sách/ước tính/thực tế, approval audit, decision log, version và
timestamps. Migration `b2c3d4e5f6a7` chain sau migration Chat AI Studio hiện có.

Thêm `platform_core.agent.runs`: create/get-owned có cô lập user, state machine
không cho chuyển lùi, checkpoint không làm mất step cũ, append decision log,
submit child chỉ khi run=`running`, truy vấn/tổng hợp fan-out. `jobs.submit()` mở
rộng additive để ghi liên kết plan/step/parent; queue Q26 và worker cũ không đổi.
Chưa có route production nào tạo AgentRun.

**Restore/migration thật trên PostgreSQL tạm, không dùng dữ liệu production:**
- `tools\restore_drill_agent.ps1` → **PASS**: `pg_dump -Fc` database probe cô lập,
  `pg_restore` sang database tạm thứ hai, xác minh 1 dòng rồi cleanup.
- Lượt P3 đầu với role `ltt_app` → **FAIL xác thực**; database tạm đã cleanup.
  Chỉ cho thấy `secrets\app.env` trong workspace không khớp role cục bộ hiện tại;
  không thay credential và không kết luận credential bản cài production bị lỗi.
- `tools\test_agent_p3_postgres.ps1` → **PASS** bằng database test cô lập:
  Alembic upgrade head → downgrade về `a1b2c3d4e5f6` → upgrade head; 3 concurrency
  test PASS; dump/restore toàn schema P3 và hàng AgentRun probe PASS; cleanup đủ.
- Rehearsal bắt được fixture concurrency chủ động `drop_all()` sau test khiến
  Alembic version còn nhưng bảng mất; script đã sửa để tái tạo DB sạch và migrate
  lại trước restore, tránh bằng chứng giả.

**Lệnh/test và kết quả thật:**
- `python -m pytest -q tests/test_89_agent_runs.py tests/test_67_hang_doi_job.py tests/test_88_agent_toolspec_apps.py tests/test_60_app_registry.py`
  → **74 passed**.
- PostgreSQL `python -m pytest -q tests/test_73_dong_thoi_pg.py` trong rehearsal
  → **3 passed** (credit race, queue race, 4 child Agent không claim trùng).
- `python -m pytest -q` → **1759 passed, 5 skipped, 23 subtests passed**,
  1 warning deprecation, 388.14s.
- `python tools\scan_source_secrets.py` → **697 file, 110.555 dòng, 0 finding, PASS**.
- `python tools\lint_app_contract.py --strict` → **9 app, 0 ERROR, 0 WARN, PASS**.
- Browser: **N/A** — chưa có route/UI production.

**Rollback:** migration downgrade P3 đã PASS trên PostgreSQL test. Production chỉ
downgrade trước khi có AgentRun thật; sau đó forward-fix. Chưa áp migration lên
production. Commit riêng chưa tạo vì migration head trước và các app liên quan
đang nằm trong worktree untracked có sẵn; không gom thay đổi ngoài phase.

## 2026-08-02 — H12 P2: ToolSpec cho đủ 7 app job-based

Đã khai ToolSpec bám code vận hành thật cho `kichban`, `taoanh`, `thumbnail`,
`taovideo`, `autosubvideo`, `upscalevideo`, `taoclipngan`. Không ép `demo`,
`socialbot` hoặc `chataistudio` SSE/sidecar vào mô hình job tool.

Mở rộng resolver model theo category/provider và capability theo model; Seedance
mini/fast không nhận 4K, bản đầy đủ nhận 4K. Thêm `validate_tool_params()` fail-fast
cho required/type/enum/range/model/unknown params trước submit. Schema không cho
Agent đặt `owner_id`, CSRF, credential hoặc field runtime nội bộ. Các input video
được mô tả bằng cổng `video`; executor P6 sẽ phân giải tham chiếu artifact thành
storage key thuộc đúng user.

Đã đối chiếu params Form → handler, giá giữ chỗ `credit_cost`, và result fixture →
returns. `taoclipngan.clips` khai `json` vì handler thật trả danh sách object chứa
`video_key`, title, score, duration — không khai sai thành danh sách chuỗi video.

**Lệnh đã chạy và kết quả thật:**
- `python -m pytest -q tests/test_88_agent_toolspec_apps.py tests/test_87_agent_toolspec.py tests/test_60_app_registry.py tests/test_81_autosubvideo.py tests/test_82_upscalevideo.py tests/test_84_taoclipngan.py`
  → **92 passed**.
- Nhóm test trực tiếp 7 app + ToolSpec (`test_71`, `77`, `78`, `79`, `81`, `82`,
  `84`, `87`, `88`) → **113 passed**, 1 warning deprecation, 5.69s.
- `python -m pytest -q` → **1752 passed, 4 skipped, 23 subtests passed**,
  1 warning deprecation, 377.69s.
- `python tools\scan_source_secrets.py` → **692 file, 110.005 dòng, 0 finding, PASS**.
- `python tools\lint_app_contract.py --strict` → **9 app, 0 ERROR, 0 WARN, PASS**.
- Browser/PostgreSQL: **N/A** — P2 chỉ metadata/validation, không UI/migration.

**Commit:** chưa tạo riêng P2 vì bốn app video đang là các cây untracked lớn có
sẵn từ phiên trước. Commit chúng lúc này sẽ gom cả thay đổi ngoài P2; giữ nguyên để
không vi phạm kỷ luật worktree. Rollback P2: gỡ `tools=` từng manifest và helper
validation/capability; handler/dữ liệu không đổi.

## 2026-08-02 — H12 P0–P1: quyết định Agent + ToolSpec core

Người dùng cấp toàn quyền bắt đầu xây dựng. Đã đóng P0 bằng Q40–Q43: PA-1+
(planner hữu hạn, executor lặp có trần), ToolSpec additive, tiền/cổng duyệt và
ranh giới internal-first. Q42 làm rõ chưa duyệt không có bút toán credit/tool job;
chi phí provider để lập plan xem trước do nền tảng hấp thụ và phải rate-limit.

P1 thêm `ToolSpec` immutable + `AppManifest.tools=()` vào hợp đồng registry. Validation
fail-fast chặn tên tool trùng/sai dạng, job type không thuộc app, schema rỗng/kiểu
lạ, prompt source path traversal, dependency không trỏ `model_ref`, output type sai.
Thêm `platform_core/agent/tools.py` để discover tool qua registry và resolve enum
từ `_labels.json`/capability model mà không import hoặc hardcode app. `ModelInfo`
được mở rộng additive bằng `capabilities`; app cũ tiếp tục chạy nguyên. Không thêm
queue/runtime, migration, UI hoặc thay đổi job/credit/storage.

**Lệnh đã chạy và kết quả thật:**
- Baseline `python -m pytest -q` → **1710 passed, 4 skipped, 23 subtests passed**,
  1 warning deprecation, 368.09s.
- `python -m pytest -q tests/test_60_app_registry.py tests/test_85_app_contract_lint.py`
  → **23 passed**.
- P1 `python -m pytest -q tests/test_87_agent_toolspec.py tests/test_60_app_registry.py tests/test_85_app_contract_lint.py`
  → **34 passed**.
- Sau P1 `python -m pytest -q` → **1721 passed, 4 skipped, 23 subtests passed**,
  1 warning deprecation, 420.66s.
- `python tools\scan_source_secrets.py` → **691 file, 109.645 dòng, 0 finding, PASS**.
- `python tools\lint_app_contract.py --strict` → **9 app, 0 ERROR, 0 WARN, PASS**.
- `git diff --check` → **FAIL do trailing whitespace có sẵn trong `server/app.py`**;
  P0–P1 không sửa file này, nên không trộn sửa ngoài phạm vi.
- Browser/PostgreSQL: **N/A** — P0 docs và P1 metadata thuần, không UI/migration.

**Rollback P1:** revert `ToolSpec`, field `tools`, capability field, module
`platform_core/agent/` và test mới; không có dữ liệu cần phục hồi.

## 2026-08-02 — Chốt Q38–Q39: full LTT Agent AI + Canvas + video/GPU

Người dùng quyết định xây hoàn chỉnh, **không hoãn Canvas** và không cắt phạm vi
Agent còn ảnh/text. Đã nghiên cứu tài liệu chính thức React Flow/Vite và đổi hướng
giao diện từ Q18 sang **Q38 hybrid**: Jinja/HTMX giữ cho trang thường; riêng Canvas
dùng React + TypeScript + `@xyflow/react`, Vite build asset tĩnh do FastAPI phục vụ;
Node.js chỉ dùng dev/build, không có Node runtime/SSR/Next.js production.

**Q39** chốt sản phẩm cuối gồm Agent + Canvas + cả 7 tool job-based ảnh/text/video/
GPU. Canvas chỉ soạn/hiển thị cùng Plan JSON; validator/giá/credit/executor vẫn ở
server và vẫn chỉ có một runtime job PostgreSQL.

Đã cập nhật:
- `QUYET_DINH_NEN_TANG.md`: Q18 mang nhãn ĐÃ THAY, thêm Q38–Q39.
- `KE_HOACH_TRIEN_KHAI.md`: thêm H12 P0→P13.
- `AGENT_LTT/02_LO_TRINH.md`: kế hoạch chi tiết P0–P13; thêm P9 build React/Vite,
  P10 model/API/versioning Canvas, P11 node editor, P12 Agent↔Canvas↔Run + video/GPU,
  P13 hardening/rollout; mỗi phase có PASS gate/test/rollback.
- Đồng bộ `AGENT_LTT/00/01/04/06`; gắn nhãn lịch sử cho `PHUONG_AN_AGENT.md` và
  `KIEM_KE_VA_LO_TRINH_AGENT.md` để không ai làm theo kết luận “hoãn Canvas” cũ.

**Lệnh đã chạy và kết quả thật:**
- `python -m pytest -q` → **1710 passed, 4 skipped, 23 subtests passed**, 1 warning
  deprecation, 366.87s.
- `python tools\scan_source_secrets.py` → **688 file, 109.352 dòng, 0 finding, PASS**.
- `python tools\lint_app_contract.py --strict` → **9 app, 0 ERROR, 0 WARN, PASS**.

---

## 2026-08-02 — App TẠO CLIP NGẮN (`taoclipngan`) — di trú engine CUT CLIP SHORT

App thứ 4 (quy trình mới). Nguồn **NGOÀI BOT GEMINI**: `D:\FULL AUTO VIDEO\CUT CLIP
SHORT` (desktop PySide6 ~50k LOC, coi là kho CHỈ ĐỌC). Chỉ lấy **làm-file-trực-tiếp**
(bỏ tự-động-từ-sheet, GUI, license). Người dùng chốt **PA-A: vendor FULL engine
tier-gated** + tier mặc định **high_quality** + cài torch cu128 + đơn giá gợi ý.

Video dài → 6 engine phân tích (whisper+YOLO+scene+audio+motion+content) → editorial
brain (hook/payoff, chấm điểm — KHÔNG cần LLM) → render (crop bám người + phụ đề ASS +
NVENC) → nhiều clip ngắn dọc.

- **K0 (hạ tầng, rủi ro nhất)**: cài **torch 2.11+cu128** (Blackwell RTX 5060 Ti) —
  `torch.cuda.is_available()=True` ✓; faster-whisper + ultralytics(YOLO) + scenedetect
  + demucs. requirements-server.txt thêm ML dep (pin `<`); setup/2 thêm bước torch
  cu128 **có điều kiện** (chỉ cài khi CUDA chưa sẵn — tránh tải lại 2.5GB mỗi deploy).
- **K1 (vendor)**: copy `cutclipshort/` (chỉ core/analysis/editorial/render/adapters/
  presets/storage/types — BỎ gui/license/tests) vào **gốc repo** (import tuyệt đối
  `cutclipshort.*`). ~1.1MB code. Import OK trong venv nền tảng.
- **K2 (app)**: `apps/taoclipngan/` — jobs.py bọc **3 hàm lõi** (blueprint
  `test_local_run.py`): run_full_analysis → run_editorial → render_segment; +
  ctx.progress + credit (giữ chỗ→đo phút thật→quyết toán) + upload N clip R2. cost.py
  (~phút×tier + clip). manifest requires=gpu+ffmpeg. routes (upload→job) + template
  (tuỳ chọn tier/tỉ lệ/thể loại/ngôn ngữ/số clip; lưới clip).
- **K2b smoke headless GPU**: video TTS 47s → engine chạy 39s → **2 clip** (whisper
  base + YOLO auto-download) → R2. Xác nhận engine chạy trên GPU nền tảng.
- **K3 nghiệm thu THẬT browser**: upload → job → **worker GPU chạy engine** → 1 clip
  (19.4s) → **phát 206 thẳng từ R2** → credit 9. Full E2E production OK.

**Bug thật bắt được**: engine tự dò ffmpeg qua PATH (nhiều `FFmpegAdapter()` không
truyền path) → worker LocalSystem KHÔNG có ffmpeg trên PATH → job lỗi. Sửa: jobs.handle
**prepend thư mục ffmpeg (LTT_FFMPEG) vào PATH tiến trình** trước khi gọi engine (phủ
mọi adapter). (Smoke qua vì shell có ffmpeg PATH; worker thì không — đúng bài học
"test trên worker/URL thật".) Secret scan: loại trừ dir `cutclipshort` (ví dụ sha256
rút gọn trong tài liệu làm trip).

**Còn (chưa gấp)**: tiêu đề/điểm clip trống (map candidate↔clip_spec theo clip_id lệch
— cosmetic); **P3 worker đa tiến trình** (job GPU dài — nối tiếp backlog); CORS R2 cho
upload file lớn; stage whisper large-v3 sẵn cho tier high (lần đầu tải ~3GB).

## 2026-08-02 — App CHAT AI STUDIO (`chataistudio`) — di trú AI Creative Studio (Codex)

App thứ 3 theo quy trình mới. Di trú từ **module `codex`** BOT GEMINI (AI Creative
Studio). Người dùng chốt PA-3 (**giữ Codex CLI** + **đăng nhập ChatGPT OAuth**, đã
xác nhận hiểu rủi ro ToS) + ảnh tự động (image-tool của agent) + đa model + project→
thread + **sidecar riêng**. Bỏ tính năng code/files/MCP.

**Kiến trúc: sidecar `LTTStudioCodex`** (dịch vụ NSSM mới, loopback :8110, bearer
token) bọc `AsyncCodex` (SDK `openai-codex` + binary bundled `codex_cli_bin`, KHÔNG
phụ thuộc npm/BOT GEMINI). CODEX_HOME riêng `data/codex-home`. Web app `chataistudio`
gọi sidecar qua HTTP, stream SSE về trình duyệt.

- **C0**: cài `openai-codex` (pin <0.145) vào venv; `codex_sidecar/` (runtime chat-only
  read-only + server FastAPI) + `codex_sidecar_main.py`; NSSM service trong setup/2 +
  token/port/CODEX_HOME vào app.env. Kiểm: /models trả **7 model GPT-5.x**, 401 guard.
- **C1**: `apps/chataistudio/sidecar_client.py` + trang admin đăng nhập **device-code**
  ChatGPT + xem model/quota. Kiểm: sinh mã thật + web↔sidecar thông.
- **Đăng nhập THẬT**: người dùng authorize từ máy khác → tài khoản Plus
  (`aka.thanhtrungcomputer@gmail.com`), `auth.json` ghi vào CODEX_HOME.
- **C2**: bảng Postgres `chat_conversations` + `chat_messages` (per-user, migration
  a1b2c3d4e5f6); route chat + **/send SSE** proxy streaming; credit **giá phẳng**
  (3 credit/lượt) — vì Plus login KHÔNG có chi phí USD/token, credit = GIÁ BÁN + điều
  tiết quota. Template chat streaming (sidebar hội thoại, chọn model, xoá).
- **C3**: ảnh agent sinh → sidecar lưu file → web copy **R2** → hiện **inline** trong
  transcript; credit +20/ảnh. Multi-model chọn khi tạo hội thoại.
- **Nghiệm thu THẬT trên app.lttstudios.com**: tạo hội thoại → chat streaming trả lời
  → **yêu cầu vẽ → ảnh mèo phi hành gia hiện inline** → reload giữ nguyên (persist
  Postgres) → credit 100→71. test_83 (7).

**Bug thật bắt được khi nghiệm thu (đều CSP — nối tiếp bài học app video):**
- 500 do biến context `is_admin` che hàm global Jinja `is_admin()` → đổi tên `user_is_admin`.
- setup/2 Move-Item khóa `app\` vì service `LTTStudioCodex` giữ thư mục → **dừng
  LTTStudioCodex trước khi swap** (nối tiếp fix Web/Worker).
- **CSP `img-src 'self' data:` chặn ảnh R2** (route /img redirect presigned) → thêm
  `https://*.r2.cloudflarestorage.com` vào img-src (song song media-src/connect-src).

**Rủi ro đã ghi (người dùng chấp nhận):** 1 tài khoản ChatGPT Plus dùng chung mọi
khách = ToS-risk + trần quota tuần dùng-chung (không scale). Khuyến nghị: tài khoản
RIÊNG (đã tách khỏi BOT GEMINI qua CODEX_HOME riêng) + pool nhiều tài khoản sau.

## 2026-08-01 — App UPSCALE VIDEO (`upscalevideo`) — di trú Đợt C (GPU) + verified live

App thứ 2 theo quy trình mới (user chỉ định). Nâng video ×4 bằng Real-ESRGAN NCNN
(Vulkan) — di trú từ BOT GEMINI `video_upscale`. **Ta chạy Windows nên copy THẲNG
vendor engine** (`realesrgan-ncnn-vulkan.exe` + 3 model ~47.5MB) vào
`apps/upscalevideo/vendor/engine/` (gitignored qua `apps/*/vendor/`).

- **Port đồng bộ**: `engine.py` (NCNN subprocess + STALL watchdog 5' + fallback tile),
  `ff.py` (probe/extract/encode/segment/concat — dùng `platform_core.media` định vị
  ffmpeg, **fallback CPU libx264** nếu không có NVENC), `autotune.py` (chọn tile/thread
  theo VRAM qua nvidia-smi), `schemas.py` (Preset fast/quality, Codec).
- `jobs.py`: probe → **đảm bảo giữ chỗ theo duration thật** → guard đĩa → tách frame →
  autotune → NCNN upscale (**chunk 360 frame** nếu dài) → encode → R2. Idempotent.
- `cost.py`: ~30 credit/phút @1080p Fast (×1.8@1440, ×4@4K, ×2.5 Quality); preview 8s.
- `service.py`: **`submit_upscale_job()`** — điểm DÙNG LẠI cho taovideo/seedance ("Nâng
  cấp 4K" gọi thẳng, không nhân đôi code) theo yêu cầu người dùng.
- `requires=("gpu","ffmpeg")`; test_82 (14 test).

**Bug thật bắt được (ảnh hưởng CẢ 2 app video):** `media._test_encoder` dùng nullsrc
**64×64** → NVENC từ chối ("Frame Dimension less than the minimum") → báo nhầm "không
có GPU" → encode 4K lùi về CPU **rất chậm**. Sửa: test bằng `testsrc 256×256 yuv420p`.
Sau sửa `detect_gpu_encoder()` trả **h264_nvenc**.

**Nghiệm thu THẬT app.lttstudios.com:** catalog card 🔍 · form đúng (Fast/Quality +
1080/2K/4K chips) · smoke GPU (Real-ESRGAN chạy, VRAM 16311MiB) · E2E trình duyệt:
480×270 → **1920×1080, encoder h264_nvenc** (NVENC fix xác nhận LIVE trên worker) ·
credit giữ-chỗ→quyết-toán · **phát video 206 thẳng từ R2**. Scan 0.

**Chặn trước tải thật (ghi backlog, chưa gấp):** **P3 — worker đa tiến trình + định
tuyến GPU**. Worker hiện 1 tiến trình → 1 job upscale (hàng chục phút GPU) CHẶN mọi
job khác (kể cả thumbnail/taoanh nhanh). `claim()` đã `SKIP LOCKED` nên chạy N worker
AN TOÀN — chỉ cần NSSM chạy 2-3 worker. Làm trước khi có tải thật.

## 2026-08-01 — App AUTO SUB VIDEO (`autosubvideo`) + hạ tầng Chặng 0 (P1/P4/P5)

Quy trình mới (user chỉ định app←module, Claude phân tích+lập kế hoạch): user yêu
cầu 2 app từ BOT GEMINI — **UPSCALE VIDEO** (`video_upscale`) + **AUTO SUB VIDEO**
(`auto_sub_video`). Lập kế hoạch `docs/KE_HOACH_2APP_UPSCALE_AUTOSUB.md`, user duyệt:
AUTO SUB trước · giữ nguyên (transcript nạp sẵn, KHÔNG Whisper) · làm P1 ngay · đơn
giá gợi ý (~5 credit/phút sub).

**Chặng 0 (hạ tầng chung cho mọi app video):**
- **P1 — presigned PUT**: `Storage.put_url()` + `UploadTarget` (R2 trả presigned PUT,
  ràng buộc Content-Type; Local trả None → app nhận multipart). Browser tải video
  LỚN thẳng R2, né trần 100MB Cloudflare. Test trong test_80.
- **P4/P5 — `platform_core/media.py`**: định vị ffmpeg/ffprobe (env `LTT_FFMPEG`/
  `LTT_FFPROBE` → PATH → thư mục phổ biến), `probe()`/`duration_seconds()` (đo thời
  lượng để giữ chỗ credit), `detect_gpu_encoder()` (nvenc>qsv>amf, fallback CPU),
  `run_with_progress()` (chạy ffmpeg đồng bộ, đọc `-progress pipe:1`). **Đồng bộ** —
  đúng mô hình worker 1-tiến-trình-1-job (song song = nhiều worker, P3 sau).

**App `autosubvideo` (Đợt B, nhóm ffmpeg):**
- L1/L2 copy trung thành từ BOT GEMINI (schemas, style_registry 8 preset,
  transcript_normalizer, segmenter, ass_builder, font_checker, subtitle_adapter,
  parsers) — chỉ đổi `app.core.logger`→`logging` và prefix import. IMPORT OK.
- `cost.py`: ~5 credit/phút (draft ×0.6/standard ×1.0/high ×1.5), sàn 1 credit.
- `burn.py`: khắc ASS bằng ffmpeg `-vf ass=` (bản đồng bộ, dùng `media`), fallback CPU.
- `jobs.py`: **luồng tiền an toàn** — giữ chỗ theo duration client khai (ước tính) →
  worker ĐO duration THẬT → **nâng giữ chỗ nếu thiếu TRƯỚC khi encode** (chặn khai
  gian, không tốn GPU cho job không trả nổi) → quyết toán đúng giá thật.
- `routes.py`: `/upload-url` (mint presigned PUT), `/queue` (nhận video_key hoặc
  multipart Local fallback + transcript, parse, submit), `/v` `/f` serve output.
- Template: upload thẳng R2 qua XHR (báo %), transcript nạp kèm, 8 preset chips.
- **Bản chất**: KHÔNG nghe-chép — người dùng nạp transcript. UI ghi rõ.
- test_81 (12 test): cost, registry, parse SRT/JSON, media locate/probe/progress.
- **Còn hoãn**: bake font .ttf preset (Montserrat… thiếu → fallback Arial + cảnh báo);
  Whisper tự tạo phụ đề (fast-follow); tuỳ biến style sâu (WYSIWYG) — MVP dùng preset.
- Cấu hình máy chủ: thêm `LTT_FFMPEG`/`LTT_FFPROBE` (Gyan full-build có libass+NVENC)
  vào `secrets\app.env` — dịch vụ LocalSystem không thấy WinGet của user nếu không khai.

**3 bug THẬT bắt được khi nghiệm thu (không test nào thấy trước):**
1. **Escape đường dẫn ASS trên Windows** — `ass=C:\...` làm vỡ bộ phân tích filter
   (ổ đĩa `:` bị coi là dấu tách option). Sửa: chạy ffmpeg với `cwd`=thư mục chứa
   .ass rồi truyền TÊN FILE TRẦN (`ass=sub.ass`). Bản gốc BOT GEMINI cũng dính lỗi
   escape này (chưa lộ vì luồng khác).
2. **Deadlock ống stderr** — `run_with_progress` chỉ đọc stdout, để stderr đầy 64KB
   → ffmpeg treo với video dài. Sửa: thread rút stderr song song (giữ 12 dòng cuối).
3. **CSP chặn app video** — `default-src 'self'` (thiếu media-src/connect-src) chặn:
   (a) `blob:` đọc thời lượng client, (b) phát video R2 presigned, (c) XHR PUT thẳng
   R2. Đây là **hợp đồng chung nhóm app video** (taovideo cũng cần — phát R2 chưa
   từng kiểm trên trình duyệt). Sửa `server/app.py`: thêm
   `media-src 'self' blob: https://*.r2.cloudflarestorage.com` +
   `connect-src 'self' https://*.r2.cloudflarestorage.com`. Chốt bằng test_43.

**Nghiệm thu THẬT trên app.lttstudios.com (Playwright, tài khoản user test):**
catalog hiện card 💬 · form render đúng (8 preset chips) · đọc thời lượng client
(blob:) → ước tính 1 credit · nộp job · **worker LocalSystem (LTT_FFMPEG) burn xong
5s** · kết quả video+srt+ass trên R2 · **billing 100→99** (giữ chỗ→quyết toán 1) ·
**phát video 206 THẲNG từ R2 presigned** (né trần 100MB). Full suite 1675 pass, scan 0.

**Chặn còn lại (user thao tác):** upload THẲNG browser→R2 (presigned PUT) cần **bật
CORS bucket R2** (token nhập từ BOT GEMINI là object-scoped, `PutBucketCors` bị
AccessDenied → phải bật ở Cloudflare dashboard hoặc token admin). Hiện app **tự lùi
về multipart qua máy chủ** (hợp file ≤90MB do trần 100MB CF); file lớn cần CORS.

## 2026-08-01 — seedance Pha 2 (refs + asset:// + moderation) — XONG (~90% parity)

Nâng `taovideo` lên đầy đủ. Người dùng chọn "làm đầy đủ, cài insightface" — cài
được opencv/Pillow/volcengine; **insightface bị chặn MSVC C++ Build Tools** → dùng
**Haar (opencv)** làm bộ nhận diện mặt (chính là fallback của bản gốc). Creds R2 +
ModelArk AK/SK đã import từ BOT GEMINI (H10).

- **P2a**: `refs.py` (build_content + role reference_image/first_frame/last_frame/
  mask + remap; ảnh ≤8MB inline chuẩn hoá Pillow; @handle→@IMG_n) · ×2 (submit N job)
  · `translate.py` (dịch EN/中/VI qua Gemini chat) · **output-moderation retry** (đổi
  seed, block bill 0 token, ≤5).
- **P2b**: `assets.py` — pipeline **asset://** trung thành (volcengine SignerV4:
  CreateAssetGroup/CreateAsset/GetAsset poll Active/DeleteAsset; shared group; host
  tạm R2 presigned 1h → xoá sau) + `has_face` (Haar). jobs: ảnh>8MB/video/audio →
  asset://; **heal người-thật** (privacy block → chuyển ref có mặt sang asset://,
  ≤2 pass, pass1 faces-only). routes: nhận ref ảnh/video/audio (mime-detect).

**Nghiệm thu THẬT trên production** (deploy `setup\2`, full suite **1659 pass**, scan 0):
- P2a: **video có ảnh tham chiếu** — 73s, refs:1, 40.594 token→37 credit (ModelArk
  chấp nhận content có image_url).
- P2b: **asset:// live** — `asset://asset-20260801194151-…` tạo trong 9s (R2 temp →
  volcengine CreateAsset → GetAsset Active → xoá), ký AK/SK đúng.

**Còn (không chặn):** insightface (cần MSVC) để nhận mặt chính xác hơn Haar; **upscale
1080p là MODULE RIÊNG** (Real-ESRGAN NCNN Vulkan, local GPU) → thuộc Đợt C, không phải
ModelArk. Coi seedance ~90% parity (đủ dùng thương mại).

---

## 2026-08-01 — H10: R2 object storage — XONG (nút cổ chai đã mở)

Mở nút cổ chai chặn Đợt B/C + serve file lớn. Người dùng cho phép **lấy creds R2 +
ModelArk AK/SK từ BOT GEMINI**.

- `platform_core/storage.py`: **R2Storage** (S3-compat, boto3 nạp lười) +
  `Storage.url_for()` (presigned GET). `get_storage()` chọn R2 khi `LTT_STORAGE=r2`
  + đủ `LTT_R2_*`; lỗi → fallback Local (có log).
- Serve: taovideo/thumbnail/taoanh **ưu tiên `url_for` → RedirectResponse** (tải
  thẳng R2 CDN, né trần 100MB); Local vẫn serve như cũ.
- `tools/import_r2_modelark_from_botgemini.py`: đọc `data/r2_storage.json` +
  `data/modelark_asset.json` của BOT GEMINI, **giải mã Fernet** (khoá của BOT
  GEMINI) → ghi `secrets\app.env` (`LTT_R2_*`, `LTT_MODELARK_*`, `LTT_STORAGE=r2`)
  — KHÔNG BOM, KHÔNG in giá trị, idempotent. Đã sao lưu app.env trước khi ghi.
- `boto3` thêm vào requirements-server; `setup\2` đọc CẢ app.env → NSSM env mỗi lần
  chạy nên biến mới tự vào dịch vụ.

**Nghiệm thu THẬT trên production**: `setup\2` (boto3 1.43.62 cài xong, health 200);
script kiểm R2: backend=R2Storage, **put→url_for presigned→HTTP GET 200 khớp→delete**
trên bucket `fb-video-storage` thật. Full suite **1649 pass**, scan 0.

**Hệ quả mở khoá:** Đợt B (ffmpeg file lớn) + serve video 4K/dài + (sau) agent-video.
ModelArk AK/SK giờ đã có → **asset:// của seedance Pha 2 hết chặn** (còn face-moderation
cần insightface).

---

## 2026-08-01 — Đợt A2 Pha 1: `taovideo` (seedance_video) — video async + cost thật — XONG

App VIDEO đầu tiên. Người dùng chốt: **làm full seedance, BỎ plenx + gemini_video**
(gemini_video UI đã trôi sang Veo3 cookie = nhóm D). Dùng hạ tầng nền tảng (job
queue/credit/storage/APIKEYS) thay runner/worker/store riêng của BOT GEMINI.

- **cost.py** (port): token=(w×h×fps×dur)×hệ-số-hiệu-chỉnh, rate USD/1M theo model,
  →VND→credit (1cr=100đ). **Reserve = ước tính** (manifest.credit_cost) → **Settle =
  token thật** provider trả (handler trả credit_cost) → worker hoàn phần dư. Khớp
  hoàn hảo sổ credit H3.
- **models.py**: registry 3 model (endpoint ep-... + độ phân giải/thời lượng/tỉ lệ).
- **modelark.py**: adapter BytePlus (submit `POST /contents/generations/tasks` Bearer,
  poll `GET .../{id}`, download stream cap 200MB). Che key trong lỗi.
- **jobs.py**: ASYNC submit→poll; **mỗi nhịp gọi `ctx.progress` = heartbeat** <
  ORPHAN_TIMEOUT(5') nên job dài 1–5' KHÔNG bị nhặt lại. Resume-safe.
- **routes.py**: form + ước tính giá (HTMX) + gallery `<video>` + **serve video theo
  HTTP Range** (`/v/{key}`) → player tải từng đoạn <100MB → né trần Cloudflare, KHÔNG
  cần R2 cho clip ngắn.
- **Slug `taovideo`** (không "seedance": brand model có trong providers.py → test_60).

**Nghiệm thu:** test_79 parity (cost math, estimate=settle, registry); full suite
**1643 pass**; scan 0; deploy `setup\2`. **Kiểm CHUỖI ASYNC THẬT trên production**
(gọi thẳng handler, key byteplus thật): submit→poll(heartbeat 13%→92%→100%)→tải→
lưu, **104 giây**, video **1,64MB**, **40.594 token → 37 credit** (reserve 38 →
settle 37 đúng). Đã dọn video test.

**Pha 2 (còn lại, để đạt parity ~90%):** asset:// (ảnh/video lớn + người thật, cần
ModelArk AK/SK), face-moderation auto-retry, refs (ảnh/video/audio), ×2, dịch prompt,
upscale. Ghi rõ hoãn có lý do.

**2 phát hiện phụ (không thuộc A2, đề xuất fix sau):**
1. **Phiên hết hạn → app path trả 404** (trang 404 của ta) thay vì chuyển về
   `/login`. Access-middleware nên redirect thay vì 404 — khách sẽ tưởng app biến mất.
2. Trình duyệt tự-điền "admin" (admin-env) đè username khi đăng nhập lại — phiền khi
   test; không ảnh hưởng người dùng thật.

---

## 2026-08-01 — Đợt A1: di trú `taoanh` + `kichban` (kiểm chứng nhà máy) — XONG

Áp công thức di trú (`CONG_THUC_DI_TRU_APP.md`) cho 2 app nhỏ — 1 ảnh, 1 văn bản —
để kiểm chứng "nhà máy" dựng ở Đợt R rẻ/đúng tới đâu.

- **`taoanh`** (từ `gemini_image`): sinh ảnh từ prompt tự do (không catalog) + chọn
  model (3) + tỉ lệ (5) + số ảnh; tái dùng pattern thumbnail. **`kichban`** (từ
  `youtube_script`): app **văn bản** đầu tiên — prompt ghép từ fragment (copy
  `prompts/youtube_script`: 5 độ dài + 6 giọng văn + 6 đối tượng + 2 ngôn ngữ), gọi
  Gemini TEXT (category chat), parse JSON, render hook/sections/outro/description/
  tags + copy/tải; luồng form → `/r/{job}` HTMX poll.
- **Nhà máy sinh lời ngay:** thêm app = thêm thư mục, KHÔNG sửa platform/server.
  Chỉ **1 sửa nhà máy dùng chung** (đáng giá): `prompt_fragments.build()` chuyển từ
  `str.format` sang **thay từng placeholder** — vì base_prompt kịch bản chứa **khối
  JSON mẫu `{ }`** làm `.format` vỡ. Lỗi này chỉ lộ ở app thứ 2 → đúng giá trị của
  việc kiểm chứng nhà máy trên nhiều app.
- **Bài học slug:** đặt `image`/`script` làm slug khiến `test_60` (chống hardcode
  slug) báo nhầm vì đó là **từ phổ biến** trong code nền tảng (`image/png`,
  `script-src`). Đổi thành **slug đặc trưng** `taoanh`/`kichban`. Ghi vào manifest.

**Nghiệm thu:** `test_78` parity A1; full suite **1634 pass / 4 skip**; scan 0;
deploy `setup\2`; **kiểm URL công khai thật** (rule 5b): cả 2 app render đúng
(chip/select/design), header hiện nhóm mới "Kịch bản"; **kichban chạy THẬT
end-to-end** — sinh kịch bản có cấu trúc, credit trừ đúng 45→42 (3cr/kịch bản),
0 lỗi console (trừ beacon CF).

---

## 2026-08-01 — Đợt R: nâng thumbnail đạt PARITY + "nhà máy di trú" — XONG

Khởi động chương trình di trú module BOT GEMINI (PA3, xem `KE_HOACH_DI_TRU_MODULE.md`).
Đợt R = app tham chiếu + scaffolding dùng chung, khoá công thức cho mọi app sau.

**Bối cảnh:** audit `DOI_CHIEU_THUMBNAIL.md` phát hiện bản thumbnail H5 chỉ đạt ~30%
tính năng người dùng của bản gốc (dựng lại tối giản, prompt hardcode). Nguyên nhân
gốc = quy trình thiếu chuẩn "di trú trung thành" (`CONG_THUC_DI_TRU_APP.md`).

- **Nhà máy** `platform_core/prompt_fragments.py`: ghép prompt từ FRAGMENT
  (`.txt` + `_labels.json`), an toàn path-traversal — năng lực nền tảng tái dùng;
  **cấm hardcode prompt** trong `jobs.py`.
- **Registry** `providers.py`: 3 model ảnh gemini active + `display_name` → UI chọn
  model từ registry.
- **thumbnail parity**: copy nguyên catalog gốc `apps/thumbnail/prompts/` (6 style
  chữ + 11 phong cách + 9 kiểu trend + 5 ngôn ngữ); `build_prompt` ghép fragment;
  chọn model; UI mới (chip group + phụ đề + ngôn ngữ + tỉ lệ 5 + **xem-trước-prompt
  HTMX** + result grid); CSS kit tái dùng trong `ltt.css`. Parity ~30% → **~93%**.
- **Tạm bỏ (ghi lý do):** ảnh tham chiếu + Imagen (gốc chưa hoàn thiện) + Batch
  (fast-follow).
- **Quy tắc chốt:** `03_THEM_APP_MOI.md` + `KHAO_SAT_BOT_GEMINI.md` phân biệt
  viết-mới vs di-trú, cổng **parity ≥ 90%**, quy ước `apps/<slug>/prompts/`.

**Nghiệm thu:** `test_77` parity gate; full suite **1625 pass / 4 skip**; scan 0;
deploy `setup\2` (598 file); `/health/ready` 200; **kiểm trình duyệt**: UI đủ 4 nhóm
lựa chọn + chọn model + xem-trước-prompt ghép ĐÚNG từ fragment (base + phong cách +
trend + style chữ + directive tiếng Việt), 0 lỗi console.

**Bẫy bắt được:** `test_60` chặn hardcode slug app trong platform — docstring
`prompt_fragments.py` lỡ ghi chữ "thumbnail" → đã đổi thành mô tả chung. Test này
giữ đúng bất biến "nền tảng không biết tên app cụ thể".

**Bug web thật (sau deploy, người dùng báo) + FIX:** trên `app.lttstudios.com` các
nhóm lựa chọn hiện thành **radio thô** thay vì chip. Nguyên nhân: **Cloudflare cache
`ltt.css` CŨ** (TTL 4h, `cf-cache-status: HIT`, thiếu `.chip-opt`) — origin/loopback
đã đúng nên kiểm loopback KHÔNG thấy. Fix: **cache-bust** `ltt.css?v=<md5 nội dung>`
(`templating.py:ASSET_VER`, dùng ở base*/admin) → đổi CSS = đổi URL = tải mới ngay
(HTML đã `no-store` nên link version tới user tức thì). Đã kiểm **trên URL công khai
thật**: chip hiển thị đúng, versioned CSS qua CF có `.chip-opt`. Bổ sung **quy tắc
5b + 6** vào CLAUDE.md (kiểm URL công khai, không chỉ loopback; đổi static phải
cache-bust).

---

## 2026-08-01 — H9: Thanh toán / nạp credit (PayOS agnostic) — XONG

Quyết định Q31 (`QUYET_DINH_NEN_TANG.md`): cổng **PayOS** (VietQR + webhook chữ
ký), kiến trúc **agnostic**, tỉ giá **1 credit = 100đ**, gói **bonus %**, admin
sửa được, **mọi tiền qua `credit.nap` (sổ H3)**, đơn **idempotent**.

- **H9.1** `CreditPackage` + `PaymentOrder` (cờ `credited` = chống cộng đôi);
  `billing_math` (base/bonus/tổng, tỉ giá 100đ) — một chỗ. Migration `f0a1b2c3d4e5`.
- **H9.2** `platform_core/payments` (registry cổng) + adapter `payos.py`: tạo
  payment link + verify webhook HMAC-SHA256 checksumKey; **tắt mềm** khi thiếu
  `LTT_PAYOS_*` (dev/test chạy).
- **H9.3** `billing.py`: `tao_don` + `ghi_nhan_tra` **idempotent** (khoá dòng đơn
  + cờ credited → webhook lặp/mark-paid lại KHÔNG cộng đôi) + `het_han` + `doanh_thu`.
- **H9.4** `/nap` (gói + bonus + tổng) → `/nap/don/{id}` (nút PayOS + HTMX poll
  trạng thái); wire header **Bảng giá/Nạp thêm → /nap**.
- **H9.5** `POST /webhooks/payment/payos` — miễn CSRF (API) nhưng **bắt buộc chữ
  ký**; đơn không tồn tại vẫn ack 200 (ping xác minh của PayOS).
- **H9.6** Admin sâu: **Doanh thu** (VND/credit/đơn) + **Gói nạp** (CRUD + bật/tắt)
  + **Đơn hàng** (lọc trạng thái + **Đã trả** tay dự phòng, vẫn idempotent).
- `tools/seed_credit_packages.py` seed 5 gói (50K→1tr, bonus 0→20%).

**Nghiệm thu (production):** deploy `setup\2`; migration `f0a1b2c3d4e5`;
`/health/ready` 200; seed 5 gói; **kiểm trình duyệt**: `/nap` hiện 5 gói đúng
bonus (1tr→12.000cr), tạo đơn ra trang đơn (báo "cổng chưa cấu hình" đúng vì chưa
nhập `LTT_PAYOS_*`), admin **Gói/Đơn/Doanh thu** hoạt động, bấm **Đã trả** cộng
credit + doanh thu lên đúng (50.000đ/500cr/1 đơn), 0 lỗi console. Full suite
**1615 pass / 4 skip**, scan 0. Test H9: 17. Dữ liệu nghiệm thu đã **dọn sạch**
(bù -500 credit + xoá đơn test → sổ về 0).

**Bật PayOS thật (khi có tài khoản):** thêm vào `secrets\app.env`:
`LTT_PAYOS_CLIENT_ID`, `LTT_PAYOS_API_KEY`, `LTT_PAYOS_CHECKSUM_KEY` rồi
`Restart-Service LTTStudioWeb`. Khai webhook ở dashboard PayOS trỏ về
`https://app.lttstudios.com/webhooks/payment/payos`. Trước đó cổng **tắt mềm**:
khách vẫn tạo được đơn, admin cộng credit tay ở **Đơn hàng → Đã trả**.

---

## 2026-08-01 — H8 Pha 2: telemetry · cascade · làm mới model — XONG

Nối tiếp H8 Pha 1 (bộ máy APIKEYS). Ba năng lực theo kế hoạch, mỗi bước có test.

- **H8.8 Telemetry rpm/tpm/token.** `ApiKey` thêm `rpm_limit`/`tpm_limit`
  (0 = không giới hạn), `total_tokens`, và cửa sổ cố định 60s ngay trong hàng
  (`window_start`/`window_requests`/`window_tokens`) — không lập bảng time-series.
  `api_pool._cuon_cua_so` reset cửa sổ khi quá hạn; allocator **bỏ qua** key đã
  chạm rpm/tpm; `danh_dau_thanh_cong(tokens=)` kế toán token. Migration
  `e9f0a1b2c3d4` (additive, có server_default).
- **H8.9 Cascade đa-provider.** `chon_key(category=, model=, thu_tu_provider=)` gom
  key MỌI provider phục vụ category, xếp theo (thứ tự provider → priority → health →
  tải). `lay_key(provider, ...)` giữ nguyên chữ ký (gọi `chon_key` với 1 provider) —
  tương thích ngược, thumbnail không phải sửa. Một provider cạn key không còn làm
  chết cả loại API.
- **H8.10 Làm mới model tự động.** `providers_live.lay_models_song` gọi
  `list_models_path` sống, parse cả OpenAI `{data:[id]}` lẫn Gemini
  `{models:[name]}` (bỏ tiền tố `models/`); `api_keys.cap_nhat_supported_models`
  ghi vào key. Admin: cột **Tải** (rpm·token) + nút **Làm mới** per-key (ghi
  supported_models) + ModelsView hiện model sống per-provider.

**Nghiệm thu (production):** deploy qua `setup\2` (đã vá: dừng dịch vụ TRƯỚC khi
đụng `app\`, xem dưới); migration `e9f0a1b2c3d4` chạy; `/health/ready` 200
(database ok); **kiểm trình duyệt** `/admin/apikeys` hiện cột Tải + nút Làm mới
đúng (video byteplus/plenx không có nút — đúng vì không có `list_models_path`);
`/admin/api-models-refresh?provider=gemini` gọi Gemini thật → **50 model sống**,
0 lỗi console. Full suite **1598 pass / 4 skip**, scan 0. Test H8: 26.

**Bẫy đã vá — `setup\2` khi CHẠY LẠI trên máy đang phục vụ:** script `Move-Item
app -> app.previous` TRƯỚC khi dừng dịch vụ → `python.exe` của service khoá file
trong `app\` → lỗi "being used by another process". Đã thêm `Stop-Service` (web +
worker) ngay đầu bước copy (script vẫn khởi động lại ở cuối). Lần đầu cài không
ảnh hưởng (chưa có service).

---

## 2026-08-01 — UX Pha 2: bố cục HEADER (bỏ sidebar) theo PLENX — XONG

Từ phân tích `docs/PHAN_TICH_PLENX.md` (quan sát PLENX qua trình duyệt). Người
dùng chốt: **điều hướng bằng HEADER ngang, bỏ sidebar trái**; nav app **dropdown
theo NHÓM**; tài khoản gom vào **avatar-menu**; **vào app full-width, không sidebar**.
Chỉ đổi BỐ CỤC/chrome — KHÔNG đụng tính năng/logic app.

- **L1** `AppManifest` thêm `group` (nhãn nhóm header) + `badge` (nhãn thẻ). Gán:
  thumbnail→"Ảnh"(badge MỚI), socialbot→"Đăng bài", demo→"Khác". Data-only.
- **L2** templating: `nav_groups` (app gom theo nhóm, lọc quyền, sắp thứ tự — tool
  thật trước, "Khác" cuối), `tai_khoan` (dữ liệu avatar-menu), `app_tabs` (nav nội
  bộ app đang mở nếu >1 trang).
- **L3** `_header.html` dùng chung: logo · dropdown theo nhóm (`<details>`) · phải
  Bảng giá/💎credit/avatar-menu (Việc của tôi/Cài đặt/Tình trạng/Quản trị nếu
  admin/Credit+Nạp/Đăng xuất CSRF). CSS header/dropdown/avatar/apptabs/cover vào
  `ltt.css`.
- **L4** `base.html` **BỎ sidebar** → include `_header`; nội dung full-width; app
  nhiều trang → thanh **apptabs** đầu nội dung (thay sub-nav sidebar). Giữ block
  topbar_title/right qua capture cho trang con.
- **L5** `base_public.html` dùng `_header` (bản anon: Đăng nhập/Đăng ký).
- **L7** catalog: thẻ **cover gradient + icon lớn + badge** + search + filter theo
  nhóm (client-side JS).
- **L8** sửa `test_31` (nav từ registry: base.html include _header, _header dùng
  nav_groups) — bất biến "nav sinh từ registry" vẫn giữ.

**Test:** full suite **1586 passed, 4 skipped**; scan 0. **Audit trực quan Chrome
(loopback 127.0.0.1:8100** — tránh IPv6 máy chủ): catalog ẩn danh, login, home
authed (header 3 nhóm + credit + avatar), avatar-menu, vào socialbot (tab nội bộ +
full-width), vào thumbnail (không tab), admin console (vỏ riêng dark). Tất cả khớp
tiêu chí + cơ chế PLENX, **không lỗi bố cục**. Deploy production OK.

## 2026-08-01 — UX Pha 1: nâng tầm giao diện (catalog/login/admin/APIKEYS) — XONG

Từ đánh giá `docs/UX_DANH_GIA_VA_PHUONG_AN.md` (phương án D, có mockup artifact
duyệt trước). Vấn đề gốc: BA ngôn ngữ thị giác rời rạc (dark nền tảng / sáng
sqladmin / trắng-trơn view tự viết).

- **`server/static/ltt.css`** — design system dùng chung (token + component:
  btn/badge/chip/health/card/table/form/hero/appcard/admin-shell). Hết lặp CSS.
- **Console APIKEYS custom dark** (`/admin/apikeys`, `ApiKeysConsole`): tab lọc 4
  loại + số đếm; bảng badge trạng thái màu + thanh health + chips loại + provider
  dot; nút **Test/Bật‑Tắt/Reset ngay tại dòng** (form CSRF). Bề mặt quản trị
  chính giờ đồng bộ theme.
- **4 view trắng → vỏ dark** (`_admin_shell`): Cấp credit, Thêm key, Models, Test.
- **Khoác dark sqladmin**: override `sqladmin/base.html` qua `templates_dir`
  (bản trung thành + `data-bs-theme="dark"` + accent nền tảng + thanh LTT). Bảng
  User/Credit/Job/Session giờ dark.
- **Polish**: catalog hero + thẻ app icon/accent hover nhấc; login logo mark +
  gradient nhẹ. base.html/base_public/base_plain link ltt.css.
- **Cam kết một-theme dark** (sản phẩm dark, chọn có chủ đích); font hệ thống +
  type-scale + tabular-nums (đúng ràng buộc tự-host, CSP chặn webfont).

**Test:** thêm `test_apikeys_console_render` + `test_admin_session/grant` vẫn xanh.
Full suite **1585 passed, 4 skipped**; scan 0. Deploy production + verify edge:
console 200 (đủ 6 preview, 0 secret, tabs/badges), sqladmin `data-bs-theme=dark`,
catalog/login link ltt.css + hero + mark. (Trình duyệt máy chủ chập IPv6 nên
verify bằng curl edge — authoritative cho HTML/CSS.)

## 2026-07-31 — H8 Pha 1: bộ máy APIKEYS (quản trị nguồn API) — XONG

Từ khảo sát `docs/KHAO_SAT_APIKEYS.md` (4 luồng đọc D:\BOT GEMINI). Phương án D
(nền tảng theo pha), model **provider + tập category**.

- **H8.1** bảng `ApiKey` (SQLAlchemy) + `platform_core/api_keys.py` (CRUD) +
  `platform_core/secretbox.py` (Fernet, salt riêng, khoá từ `LTT_TOKEN_ENCRYPTION_KEY`)
  + migration `d8e9f0a1b2c3`. Chỉ lộ `key_preview` (4 số cuối), không bao giờ trả
  credential thô.
- **H8.2** `platform_core/providers.py` — Provider Registry MỘT chỗ: gemini
  (query_key), apiai/cheapkeyai (bearer OpenAI-compat), byteplus (bearer, video
  async), plenx (x_api_key, video async). Tách 3 ID model.
- **H8.3** `platform_core/api_pool.py` — `lay_key(provider,category,model)` chọn
  theo priority, bỏ cooldown/disabled; `danh_dau_thanh_cong/loi` (401→disable sau
  5, 429→cooldown, 4xx→không phạt). Key chia sẻ được → không cần khoá độc quyền.
- **H8.4** menu **APIKEYS** ở `/admin` (`/admin/api-key/...`, slug sqladmin =
  "api-key"): list (chỉ preview), Thêm key (mã hoá), **Test key** (probe sống),
  bật/tắt/reset, view Models (registry).
- **H8.5** import **6 key** từ BOT GEMINI: `tools/import_api_keys_from_botgemini.py`
  giải mã bằng module security của BOT GEMINI (nạp riêng lẻ, khoá từ BG/.env) →
  mã hoá lại → INSERT. categories suy từ Provider Registry. Idempotent theo
  (provider, preview). Đã chạy: 6/6 OK.
- **H8.6** thumbnail `jobs.py` lấy key qua `api_pool.lay_key("gemini", image)` +
  đánh dấu thành công/lỗi (GeminiError mang status). Fallback env cho dev.
- **Phát hiện lúc verify:** key gemini `...B3sk` import từ BOT GEMINI CHÍNH LÀ
  GEMINI_API_KEY đang chạy (cùng 4 số cuối), nhưng BOT GEMINI để enabled=False →
  đã bật lại để thumbnail dùng qua engine.

**Test:** `test_75_api_keys.py` (secretbox, CRUD, registry, allocator — 401/429/
4xx) + test_70 (admin APIKEYS không lộ credential, Add view mã hoá) + test_71
(thumbnail dùng key engine). Full suite **1583 passed, 4 skipped**; scan 0.
**Sửa 2 test khoá logic:** bỏ từ "socialbot" trong comment secretbox (test_60);
miễn trừ script di-trú-một-lần khỏi test_62 (cố ý trỏ BOT GEMINI, không phải
phụ thuộc runtime).

**Nghiệm thu production:** migration `d8e9f0a1b2c3` áp dụng; import 6/6 key;
`/admin/api-key/list` hiện 6 preview, **0 secret thô**; **Test key gemini → HTTP
200 OK** (giải mã + probe Gemini live). Pha 2 (sau): telemetry rpm/tpm/token,
cascade đa-provider, làm mới model tự động.

## 2026-07-31 — H7 Wave 1 + Wave 2: hoàn tất củng cố MVP

**Wave 1 (P1) — commit 5f00302, full suite 1562 pass:**
- thumbnail tính tiền theo ảnh THÀNH CÔNG (`credit_cost` trong result) + loop
  resume-safe (bỏ qua ảnh đã lưu khi retry → không trả tiền Gemini hai lần; lỗi
  1 ảnh không hỏng cả job).
- Handler `Exception` tổng: 500 có style + `no-store` + correlation id.
- CSRF cho GrantCreditView + dropdown enabled/locked/hidden cho AppAccess.level.
- Auth: khoá theo TÀI KHOẢN (chống stuffing nhiều IP) + rate-limit forgot-password
  + CSRF logout (global `phien_csrf`, KHÁC tên biến context `csrf_token`) + chặn
  login khi `is_verified=False`.
- Siết ACL thư mục backup off-drive (icacls SID `*S-1-5-18`/`*S-1-5-32-544`).
- `_validate` fail SỚM: job_types thiếu credit_cost / trùng job_type → app lỗi
  ngay lúc discover. (Mở rộng scan slug sang server/ BỎ — "thumbnail" trùng từ.)
- Scanner thêm rule session_secret/token_encryption_key/encryption_key.

**Wave 2 (P2) — commit 3ff3315, full suite 1564 pass:**
- API key Gemini qua header `x-goog-api-key` (không URL query).
- Test HTTP kiểm sở hữu `/image/{key}` (A đọc ảnh B → 404).
- `reclaim_orphans` SKIP LOCKED + index `ix_jobs_claim` (migration c7d8e9f0a1b2,
  đã áp production — lần đầu lệnh bị lỗi escaping PowerShell, chạy lại rc=0, xác
  minh index tồn tại + alembic ở head).
- Log rotation theo kích thước: AppRotateBytes 10MB + AppRotateOnline (setup/2 +
  setup/3), áp cả 3 dịch vụ đang chạy qua nssm.
- Smoke Playwright opt-in `test_74` (skip nếu chưa cài / chưa đặt LTT_SMOKE_URL).

**Hoãn có chủ đích (ghi rõ trong AUDIT + KE_HOACH):** `url_for`/R2 → H9; FK
constraints (rủi ro migration + FK `job_id` bất khả vì sentinel `""`);
`CHECK(delta<>0)` SAI (settle ghi delta=0 hợp lệ); đánh dấu ~929 test socialbot.

**Bài học:** nested PowerShell `-Command` với `$Matches`/`$env` qua Bash bị mất
escaping → lệnh alembic "im lặng" không chạy (alembic version không đổi mới lộ).
Luôn kiểm chứng migration bằng truy vấn thật (index/version), không tin exit code
của lệnh lồng.

## 2026-07-31 — H7 Wave 0: sửa 6 lỗ hổng P0 (củng cố MVP trước khách trả tiền)

Từ audit toàn diện (`docs/AUDIT_MVP_2026-07-31.md`, điểm tổng ~73/100). Sửa 6 lỗ
hổng P0 tiền/bảo mật/khôi phục, MỖI lỗ kèm test:

- **W0.1 Race double-spend credit** — `credit.giu_cho` thêm `pg_advisory_xact_lock`
  theo user (chỉ Postgres; SQLite bỏ qua). Test **đồng thời trên PostgreSQL thật**
  (`test_73_dong_thoi_pg.py`, cần `LTT_TEST_DATABASE_URL`): 8 request song song
  giữ 10/10 credit → đúng 1 thành công, số dư 0 (không âm). + test claim SKIP LOCKED
  không nhặt trùng. **Cả 2 PASS trên DB `lttplatform_test`.**
- **W0.2 Dedupe không đấu dây** — thêm `job_submit.dedupe_key_for()`; đấu vào route
  `apps/demo` + `apps/thumbnail`. Test: POST /demo/queue 2 lần cùng nội dung → 1 job.
- **W0.3 IP thật sau Tunnel** — `session.client_ip()` đọc `CF-Connecting-IP`; dùng ở
  `auth.py` + `register.py`. Test: 5 sai từ IP A khoá A, IP B không vạ lây.
- **W0.4 Restore không khôi phục DB** — `restore.ps1` thêm `pg_restore --clean
  --if-exists --no-owner -1` (parse LTT_DATABASE_URL như backup.ps1). Test guard
  tĩnh + backup.ps1 pg_dump đã chạy thật lúc deploy.
- **W0.5 Lộ token phiên ở admin** — **băm token khi lưu** (`users._bam_sid`, SHA-256):
  cookie giữ token thô, DB giữ hash; `Session.id` String(43)→(64) + migration
  `b1c2d3e4f5a6` (xoá phiên cũ → đăng nhập lại). SessionAdmin bỏ cột id. Test:
  `/admin/session/list` không chứa token.
- **W0.6 update.ps1 bỏ migration** — thêm `alembic upgrade head` trước `Start-Service`.
  Test guard: có lệnh + đứng trước start.
- **W0.7 CLAUDE.md drift** — bảng "Việc còn dở" sửa lại (PostgreSQL/job/credit ✅),
  thêm H7 Hardening; đồng bộ mô hình admin (Q29).

**Kiểm chứng:** full suite **1547 passed, 3 skipped** (2 skip là test PG khi không
có env), scan 0. Deploy production + chạy migration (rc=0, sau khi pg_dump backup) +
restart. Verify edge: login token-băm 303, /jobs không lặp 200, /admin/session/list
không lộ token, health 200. Trình duyệt: /admin ẩn danh → /login (cổng auth đúng).

**Hạ tầng test:** DB `lttplatform_test` (owner ltt_app) trên PostgreSQL máy chủ,
dùng cho `test_73` khi đặt `LTT_TEST_DATABASE_URL`. Suite thường vẫn portable (tự
skip khi không có env).

## 2026-07-31 — H6.6: vỏ app launcher hai tầng + lối vào quản trị + sửa bug vòng lặp

- **Vấn đề người dùng nêu:** đăng nhập admin thấy sidebar bị 8 mục của socialbot
  (Sheet/Manual/Tài khoản FB+TikTok/Monitor/Audit) chiếm kín → tưởng "chưa tách
  app FB/TikTok". Thực ra socialbot ĐÃ là 1 app; lỗi là **cách vẽ sidebar** gộp
  phẳng mọi trang con của mọi app.
- **Sửa (thuần nền tảng, KHÔNG đụng socialbot):** sidebar thành **hai tầng** —
  tầng 1 mỗi app một dòng (launcher); tầng 2 (trang con) chỉ bung khi đang Ở
  TRONG app đó (`active_app()` dùng `app_cho_path`). socialbot co còn 1 dòng.
- **Lối vào quản trị:** thêm global `is_admin(request)` → link **🛡️ Quản trị**
  (`/admin/`) chỉ hiện cho admin CSDL. Chốt: admin về trang chủ + dùng được mọi
  app, KHÔNG ép vào panel (theo lựa chọn người dùng).
- **Banner FB/TikTok:** bỏ banner blocker TOÀN CỤC ở trang chủ; blocker doctor
  gắn vào ĐÚNG thẻ app qua field mới `AppManifest.blocker_titles` (socialbot tự
  khai "Tài khoản Facebook/TikTok") → badge "cần thiết lập" trên thẻ. Nền tảng
  KHÔNG hardcode tên app (test_60 vẫn xanh). Chi tiết vẫn ở /status.
- **BUG THẬT phát hiện khi kiểm trình duyệt (ERR_TOO_MANY_REDIRECTS):**
  `login_form` chỉ kiểm sid CÓ MẶT (`current_sid`) trong khi `require_login`
  XÁC THỰC sid với CSDL. Phiên có sid nhưng đã bị thu hồi (đổi mật khẩu/hết hạn)
  → `/login` đá sang trang, route đá về `/login` → **lặp vô tận**. Sửa:
  `login_form` dùng `current_identity_optional` (resolve sid) — đồng nhất với
  require_login. Thêm regression `test_phien_thu_hoi_khong_gay_vong_lap_redirect`.
  Ảnh hưởng mọi user bị đổi mật khẩu/hết hạn phiên, không riêng phiên này.
- **Test:** sửa `test_dashboard_surfaces_blockers` (banner→badge); thêm 4 test
  test_72 (launcher gọn / sub-nav bung / link admin / redirect loop). Full suite
  **1534 passed, 1 skipped**; scan 0.
- **Kiểm chứng production (curl edge, đăng nhập admin):** trang chủ launcher gọn
  (sub "Sheet TikTok"=0), link Quản trị hiện, badge "cần thiết lập" trên thẻ
  socialbot, banner cũ=0; trong /facebook sub-nav bung; /jobs sau login=200
  (không lặp); /login khi đã đăng nhập=303. Trình duyệt trên MÁY CHỦ chập vì
  IPv6 hỏng (curl -6 fail) — lỗi mạng máy, không phải app; xem [[don-dep-sau-h6]].

## 2026-07-31 — H6: cốt lõi vận hành (catalog công khai + SSO + login return-to) — XONG

- **Xây xong H6.1–H6.4** đúng kế hoạch Q30:
  - `current_identity_optional()` + `safe_next()` (chống open-redirect) trong
    `server/auth/session.py`; `require_login` giờ 303 về `/login?next=<path>`.
  - Trang chủ `/` **CÔNG KHAI**: `dashboard.home()` bỏ `require_login`, khách xem
    catalog (app `enabled and public`), authed thấy launcher + blockers + credit.
  - Vỏ công khai mới `base_public.html` (không sidebar); `home.html` `extends` động
    theo `authed`. `login.html` mang `next` ẩn; POST/GET login về `safe_next(next)`.
  - Trường **`public`** thêm vào `AppManifest` (mặc định True). `demo`+`socialbot`
    đặt `public=False` → ẩn khỏi catalog khách, vẫn vào được qua sidebar+phân quyền.
  - `so_du_credit(request)` global → topbar badge credit. socialbot giữ path gốc.
- **Sửa comment `registry.py`** bỏ tên slug (test_60 quét slug hardcode trong nền).
- **Test:** thêm `test_72_vanhanh.py` (6); sửa các test cũ giả định `/`→/login khi
  ẩn danh (nay `/` công khai 200) ở test_37/41/47/64/66. Full suite **1530 passed,
  1 skipped**; `scan_source_secrets` 0 finding.
- **Kiểm trình duyệt thật (Playwright, qua Cloudflare):** khách `/` → catalog chỉ
  hiện `thumbnail`; bấm → `/login?next=/thumbnail`; đăng nhập → về đúng `/thumbnail`;
  vỏ authed hiện `💳 45 credit` + `[Đăng xuất (admin@lttstudios.com)]`. DNS máy đã
  trỏ đúng Cloudflare (104.21.58.244/172.67.166.73), hết cache server cũ Vultr.
- **Lỗi test-harness ghi lại để khỏi mắc lại:** curl trong Git-Bash **path-mangle**
  `--data-urlencode "next=/thumbnail"` thành `C:/Program Files/Git/thumbnail` →
  tưởng app sai. Thực ra `safe_next` từ chối đúng chuỗi méo. Trình duyệt thật đúng.
- **Còn nợ (không phải code):** Cloudflare tự tiêm `beacon.min.js`, CSP chặn đúng →
  1 console error vô hại; tắt ở Cloudflare dashboard. Server cũ Vultr 45.32.104.192
  vẫn chạy nền (không còn trong DNS) — dọn sau.

## 2026-07-31 — Q30 + H6: chốt mô hình vận hành nền tảng (kế hoạch, chưa code)

- **Làm rõ thuật ngữ với người dùng:** mỗi app = 1 thư mục `apps/<slug>/` chạy tại
  `app.lttstudios.com/<slug>` (path-based, KHÔNG subdomain). "1 tài khoản cho mọi
  app" = SSO tự nhiên vì cùng 1 host, 1 cookie phiên — không cần thêm hạ tầng.
- **Nghiên cứu thị trường + chấm điểm 4 phương án** (path-based / subdomain+cookie-cha
  / subdomain+OIDC / hybrid). Path-based 1 host thắng: khớp ý người dùng, SSO miễn
  phí, công sức thấp, rủi ro thấp, hiện đại (mô hình "app launcher").
- **Chốt Q30:** đa-app path-based; trang chủ `/` = catalog CÔNG KHAI; đăng nhập có
  return-to (`?next=`, chống open-redirect); slug thường-gạch-nối. socialbot giữ
  path gốc (đặc cách Q10), là 1 box trong catalog; đổi `/socialbot` để sau.
- **Viết H6 chi tiết** trong KE_HOACH (H6.1 trang chủ công khai → H6.2 login next →
  H6.3 vỏ account/credit/launcher → H6.4 hai app đúng path → H6.5 slug+tài liệu+
  test), kèm sơ đồ vận hành + file/hàm cụ thể + tiêu chí + rủi ro. Dời 3 mốc tương
  lai: Thanh toán H6→H7, R2 H7→H8, Thêm tool H8→H9.
- **Phiên này CHỈ phân tích + viết kế hoạch (không sửa code)** theo yêu cầu.

## 2026-07-31 — H5: app thumbnail (tool tính phí đầu tiên) — dựng xong, chờ khoá

- **Dựng `apps/thumbnail/`** theo hợp đồng app (manifest/jobs/routes/templates),
  viết mới từ tham chiếu `D:/BOT GEMINI/.../thumbnail_api` (chỉ đọc): gọi
  `gemini-2.5-flash-image` bằng httpx sync (bỏ api-pool/cascade của họ), lưu ảnh
  qua `platform_core.storage`, `GEMINI_API_KEY` phía máy chủ + che khoá ở lỗi.
- **Hai lỗ hổng hợp đồng lộ ra (H5 = phép thử hợp đồng) & đã lấp:**
  (1) template app — `server/templating.py` ChoiceLoader tìm `apps/*/templates/`;
  (2) tải file output — app tự phục vụ `/image/{key}` (kiểm sở hữu theo key);
  download_token storage KHÔNG dùng được qua worker→web (RAM mỗi tiến trình).
  Ghi vào `docs/03`. KHÔNG đụng `platform_core/`.
- **Test:** `test_71` (5, Gemini mock) + `test_60` registry xanh; full suite
  **1523 pass, 1 skip**; scan 0 (thêm `.playwright-mcp`/`.claude` vào loại trừ
  của cả `scan_source_secrets.py` lẫn `build_release.py`).
- **Nghiệm thu render (Cloudflare edge):** `/thumbnail` hiện form + gallery, app
  **tự lên trang chủ/sidebar** không sửa giao diện nền tảng.
- **✅ CHẠY THẬT — H5 KHÉP:** người dùng nạp `GEMINI_API_KEY` vào app.env; nạp lại
  env dịch vụ + restart. Cấp 50 credit cho `admin@lttstudios.com`, tạo 1 thumbnail
  qua Cloudflare edge → job **done**, ảnh **1.8 MB PNG thật** (magic `89 50 4e 47`)
  lưu ở `data/files/thumbnail/<uid>/<job>/0.png`, số dư **50 → 45** (trừ đúng 5).

- **🔴 LỖI BẢO MẬT phát hiện & VÁ khi test chặn truy cập:** ẩn danh gọi
  `/thumbnail/image/<key>.png` vẫn nhận ảnh (HTTP 200) dù origin chặn (303) —
  vì **Cloudflare cache file .png** theo đuôi (`cf-cache-status: HIT`,
  `max-age=14400`) rồi phục vụ cho người KHÔNG đăng nhập, bỏ qua auth. Middleware
  cũ chỉ `no-store` cho text/html. **Vá:** `server/app.py` đặt `Cache-Control:
  no-store` cho MỌI response ngoài `/static/` (chặn cả lớp lỗi). Deploy + purge
  cache → ẩn danh giờ **303 /login, cf-cache-status: BYPASS**; chủ vẫn 200. Thêm
  test khoá `test_43::test_dynamic_responses_are_not_cacheable`. Full suite
  **1524 pass**. BÀI HỌC: sau CDN, nội dung riêng-tư phải no-store; đừng để đuôi
  file quyết định cache.

## 2026-07-31 — Resend + Turnstile (điều khiển trình duyệt) — đăng ký sẵn sàng

- **Turnstile:** tạo widget "LTT app" (Managed) cho `app.lttstudios.com` trong
  Cloudflare. Site key `0x4AAAAAAECt29NR1TKkMFDx` (công khai), Secret key đặt vào
  app.env (`TURNSTILE_SITE_KEY`/`TURNSTILE_SECRET_KEY`). Kiểm: `/register` render
  `cf-turnstile` + api.js.
- **Resend:** thêm domain **`mail.lttstudios.com`** (subdomain riêng để không đụng
  SPF trang chủ iNET). DNS (DKIM/SPF/MX) áp qua **Cloudflare Domain Connect** —
  chuẩn one-time, Cloudflare ghi rõ "không cấp Resend quyền sửa về sau" (least-
  privilege, hơn OAuth token). Domain **verified**. Bản ghi đã kiểm sống qua
  8.8.8.8. API key **Sending access** (`re_...`) đặt vào `RESEND_API_KEY`;
  `LTT_MAIL_FROM="LTT AI Studio <no-reply@mail.lttstudios.com>"`.
- **Chú ý chép DKIM:** trang Resend cắt giữa giá trị (`[…]`) → chép tay sai. Domain
  Connect (URL query `domainKey=...`) mang giá trị đầy đủ → dùng đường đó, chính xác.
- **Nạp khoá:** cả 4 khoá vào `C:\LTTPlatform\secrets\app.env` + `nssm set
  AppEnvironmentExtra` cho Web+Worker + restart. health ready. mailer → ResendMailer.
- **Còn lại (người dùng tự kiểm khi muốn):** đăng ký thử bằng email thật → nhận
  mail xác thực → +credit dùng thử. Chưa test end-to-end vì không có hộp thư kiểm.

## 2026-07-31 — H3-admin đợt 2: admin trong DB + credit dùng thử + test

- **`tools/create_admin.py`**: tạo/nâng user role=admin (băm PBKDF2, idempotent,
  mật khẩu qua getpass hoặc `LTT_NEW_ADMIN_PASSWORD`, không in ra). Đã tạo
  `admin@lttstudios.com`. **Nghiệm thu production thật** (curl ép Cloudflare edge):
  login bằng email → 303, `/admin` với phiên đó → 200 → admin DB vào được, KHÔNG
  cần admin-env.
- **Credit dùng thử**: `/verify-email` gọi `credit.cap_tay` một lần đúng lần
  verify đầu (idempotent theo `was_verified`); lượng `LTT_TRIAL_CREDIT` mặc định 20.
- **Test `test_70_admin_h3.py`** (3): trial-credit idempotent, /admin đá ẩn danh,
  chỉ role=admin vào /admin. Full suite **1518 pass, 1 skip**; scan 0 finding.
- **Phát hiện thêm:** dashboard hiện `[email protected]` do **Cloudflare "Email
  Obfuscation" (Scrape Shield)** tự sửa HTML động (cùng họ beacon) — bug hiển thị
  thật, cần tắt Scrape Shield/beacon trong dashboard cho host proxied.
- **admin-env: chốt Q29 (giữ break-glass, vô hiệu production).** Xoá
  `LTT_ADMIN_PASSWORD_HASH` khỏi app.env + nạp lại env dịch vụ. LỖI GẶP: web
  service chết (Paused, 502) vì `settings.py` bắt buộc hash ở production →
  `MissingServerSecretError`. Sửa: bỏ ADMIN_USERNAME/HASH khỏi danh sách secret
  bắt buộc (chỉ còn SESSION_SECRET), deploy settings.py, restart → web sống lại.
  Nghiệm thu: admin-env → 401; DB admin → 303 + /admin 200. → **H3-admin XONG.**
  BÀI HỌC: xoá secret bắt buộc mà không sửa validator = tự sập app.

## 2026-07-31 — H3-admin: trang quản trị sqladmin (MVP xong)

- **Kiểm tương thích trước:** app chạy Starlette 1.3.1; `pip install --dry-run`
  cho thấy `sqladmin 0.20.1` chấp nhận Starlette 1.3 (không hạ version) → Q15
  giữ nguyên. Thêm `sqladmin>=0.20.1,<0.21` + `wtforms>=3.1.2,<4.0` (Q17).
- **`server/admin.py`:** `AdminAuth(AuthenticationBackend)` dùng CHUNG phiên nền
  tảng (truyền `session_secret` → cùng cookie "session"); admin = admin-env
  (`session["user"]`) hoặc user DB role=admin. Không admin → 303 /login. 7 view:
  User (sửa role/active/verified, không sửa email/hash, không xoá), CreditEntry
  **read-only (append-only H3)**, AppAccess CRUD, Job read-only, Session xoá-để-
  thu-hồi, PlatformInfo read-only, và `GrantCreditView` /admin/grant-credit gọi
  `credit.cap_tay`.
- **Gắn ở `create_app` CÓ GUARD:** `try/except` quanh import+setup — thiếu
  sqladmin (test chạy system python) hoặc chưa có CSDL → `admin_ready=False`,
  bỏ qua, KHÔNG vỡ app. Đã cài sqladmin vào cả venv (bản chạy) lẫn system python
  (môi trường test).
- **Nghiệm thu browser thật:** đăng nhập admin → `/admin` hiện đủ 7 view, đọc
  PostgreSQL thật OK; chưa đăng nhập → 303 /login. curl `/admin/` (ẩn danh) → 303.
- **Test:** full suite **1512 pass, 1 skip** sau khi sửa 3 chỗ do thay đổi hôm
  nay: (1) `test_41` assert wording home "đang chặn bot"→"việc cần thiết lập";
  (2)(3) `test_44` release scanner bắt `.playwright-mcp/*.yml` → thêm
  `.playwright-mcp` vào `EXCLUDED_DIRS` của `build_release.py` + `.gitignore` +
  xoá rác. `scan_source_secrets` = 0 finding.
- **Còn lại H3-admin:** tạo admin trong DB → gỡ admin-env; cấp credit dùng thử
  sau verify email (nối H1.3); test tự động cho admin.py.

---

## 2026-07-31 — Dọn branding + fix Cache-Control + phát hiện DNS resolver cũ

### Dọn nợ H0.1 (mục A — "socialbot chỉ là 1 app")

- `base.html` + `home.html` vốn ĐÃ đúng: sidebar/danh sách app sinh từ
  `apps/*/manifest.py` (không viết cứng). socialbot là 1 nav-group hợp lệ.
- Sửa branding platform-level: `login.html` "đăng bài Facebook & TikTok" →
  "Nền tảng công cụ AI — dùng theo credit"; `home.html` "việc đang chặn bot
  đăng bài" → "việc cần thiết lập". Thêm favicon SVG (`server/static/favicon.svg`
  + link ở base/base_plain) → hết 404.
- **Nợ SÂU chưa động (cần quyết định, mâu thuẫn Q10 freeze):** route + template
  socialbot (sheet/manual/accounts/monitor/oauth/workers) nằm trong `server/`,
  không ở `apps/socialbot/`. Tách ra là refactor lớn code đóng băng → để sau.

### Fix bảo mật: Cache-Control cho HTML

- `server/app.py`: HTML response nay gửi `Cache-Control: no-store` (file tĩnh
  không đụng). Trước đó không có → proxy/CDN có thể cache trang động (rủi ro
  phục vụ trang người này cho người khác). Đã xác minh qua Cloudflare edge:
  `cf-cache-status: DYNAMIC` (không cache). `test_43`+`test_37` xanh (41).

### Phát hiện: máy chủ tự thấy nội dung CŨ do DNS resolver, KHÔNG phải lỗi nền tảng

- curl/local trên máy chủ trỏ `app.lttstudios.com` → **45.32.104.192** (máy Vultr
  CŨ vẫn chạy Caddy+bản LTT cũ) vì **DNS resolver của router/ISP còn cache A record
  cũ** từ iNET trước khi đổi NS; `ipconfig /flushdns` không xoá được cache router.
- **Public đúng:** ép curl qua Cloudflare edge 104.21.58.244 → tagline MỚI,
  `Server: cloudflare`, `Cache-Control: no-store`, favicon 200, health ready.
  Trình duyệt (IPv6→Cloudflare) cũng hiện bản mới. → **Người dùng thật thấy app
  mới**; chỉ máy chủ thấy cũ tới khi cache resolver hết TTL (hoặc đổi DNS máy sang
  1.1.1.1). **Lưu ý:** có một máy chủ CŨ ở 45.32.104.192 vẫn chạy — cân nhắc gỡ.
- Còn 1 lỗi console: Cloudflare tự chèn `static.cloudflareinsights.com/beacon.min.js`,
  bị CSP chặn (đúng — không nhận JS bên thứ ba). Vô hại; tắt auto-inject trong
  dashboard sau nếu muốn.

---

## 2026-07-31 — ✅ H0.1 HOÀN TẤT: app.lttstudios.com sống, nghiệm thu thật

- **Tunnel:** sửa `setup/3` cài `cloudflared` **qua NSSM** (`--config ... tunnel
  run`) thay `cloudflared service install` (bản 2026.x cho ImagePath trần → không
  kết nối). Hardened: kill process + `sc delete` thay `Stop-Service` (tránh treo
  StopPending). Ổn định: curl **8/8 = 200**, `tunnel info` có active connection.
- **Quyền Admin:** shell Claude không elevated → không cài dịch vụ được. Người
  dùng **relaunch VS Code as administrator** → Claude tự chạy nốt (kill service
  kẹt, `sc delete`, chạy `setup/3`, đặt mật khẩu, nghiệm thu).
- **Mật khẩu admin:** đặt `admin` / (mật khẩu người dùng cấp, tạm, sẽ đổi) qua
  hash + nạp vào env cả 2 dịch vụ + restart. Lưu ở memory cục bộ (ngoài git).
- **Nghiệm thu browser thật:** đăng nhập admin → control plane hiện "2 app đã
  nạp" (demo, socialbot). Demo "chạy qua hàng đợi" trả 400 **đúng thiết kế**
  (admin bootstrap không có sổ credit; cần user đăng ký thật). `setup/4`: mọi
  mục ĐẠT (3 dịch vụ Running, chỉ nghe 127.0.0.1, /docs 404, secrets siết, 2 app).
- **Test:** `test_45` + `test_61` = 73 pass; `scan_source_secrets` = **0 finding**
  (sau khi dọn rác `.playwright-mcp/`).
- **Nợ để lại (không chặn):** control plane còn branding socialbot cũ + route gốc;
  lỗi console Cloudflare beacon (CSP); favicon 404. Cần cấu hình Resend/Turnstile
  trước khi mở đăng ký cho khách.

---

## 2026-07-31 — Q28: bố trí ổ đĩa + sao lưu chống mất dữ liệu; setup/2 đã cài xong

### Bối cảnh — làm rõ hiểu lầm về bố trí

- Người dùng lo mất dữ liệu nếu ổ C:/Windows hỏng. Ban đầu tưởng muốn dời bản
  chạy sang D:, nhưng làm rõ lại: **giữ mô hình chuẩn** — bản chạy `C:\LTTPlatform`
  (ổ C = Disk 0), nguồn/bộ cài `D:\LTTSTUDIOSAPP` (ổ D = Disk 1) — và **thêm cơ
  chế backup C: → `D:\LTTBackups`** (ổ vật lý khác). Chốt thành **Q28**.
- Ổ: C = Lexar 1TB (645GB trống, Disk 0), D = Samsung 970 EVO Plus 500GB (114GB
  trống, Disk 1) — hai ổ vật lý riêng. PostgreSQL data ở `C:\Program Files\
  PostgreSQL\17\data`.

### Đã làm

- **Q28** thêm vào `QUYET_DINH_NEN_TANG.md`: bản chạy C:, nguồn/backup D:,
  off-site khi thương mại. Nhấn: backup PHẢI gồm `secrets\app.env` (mất
  `LTT_TOKEN_ENCRYPTION_KEY` = mất token dù DB còn); tự động + định kỳ + restore
  thử; cùng máy vẫn là điểm chết chung → off-site bắt buộc khi có tiền.
- `deploy\windows\backup.ps1`: thêm tham số `-BackupDir` (mặc định `$Root\backups`,
  cho phép trỏ sang ổ khác). Đã có sẵn `pg_dump -Fc` + gói `*.enc`/config/audit +
  `-IncludeSecrets` + giữ 14 bản + kiểm zip đọc được.
- `deploy\windows\5-lich-backup.ps1` (MỚI): đăng ký Scheduled Task chạy backup
  mỗi ngày, tài khoản SYSTEM, ghi sang `D:\LTTBackups`; cảnh báo nếu BackupDir
  cùng ổ với bản chạy; chạy thử một lần để kiểm.
- Kiểm: cả 2 `.ps1` thuần ASCII + không BOM; PowerShell parse OK; `test_61` xanh
  (49 passed).

### setup/3 (Tunnel) — LỖI dịch vụ cloudflared + đã sửa bằng NSSM

- Người dùng chạy `setup\3`: bước 5 (route dns) từng CRASH vì cloudflared ghi log
  ra stderr → dưới `ErrorActionPreference='Stop'` + `2>&1` thành NativeCommandError.
  Sửa bằng hàm `Invoke-Cf` (chuyển stderr ra file tạm rồi gộp, không thành error
  record). Bản ghi `app.lttstudios.com` (CNAME → tunnel) đã tạo.
- **Lỗi thật hơn:** `cloudflared service install` bản **2026.7.3** tạo dịch vụ
  Windows với **ImagePath TRẦN** (`cloudflared.exe`, không tham số) → dịch vụ chạy
  nhưng không biết chạy tunnel/config nào → `tunnel info` báo **"no active
  connection"** → `app.lttstudios.com` trả **530/1033**. (Lúc script vừa cài, health
  check thoáng qua `status=ready` rồi rớt — gây hiểu nhầm là đã xong.)
- **Sửa:** viết lại bước 6 của `setup\3` — cài dịch vụ `cloudflared` **qua NSSM**
  với đúng dòng lệnh `--config C:\LTTPlatform\cloudflare\config.yml tunnel run`
  (giống cách setup\2 cài Web/Worker); tự gỡ bản dịch vụ cũ (kể cả ImagePath trần)
  trước khi cài lại. ASCII + không BOM + parse OK + test_61 xanh.
- **CHẶN:** cần người dùng chạy LẠI `setup\3` trong PowerShell Admin để áp bản sửa
  (idempotent: dùng lại tunnel + cert, chỉ cài lại dịch vụ cho đúng).

### setup/2 — người dùng đã tự chạy, THÀNH CÔNG

- `C:\LTTPlatform\` nay có đủ `app\ venv\ secrets\app.env tools\nssm.exe data\ logs\`.
- Dịch vụ `LTTStudioWeb` + `LTTStudioWorker`: **Running**. `:8100/health/ready` →
  **200**. DB nối đúng (nhờ `postgres-superuser.txt` đã stage trước → setup/2 tự
  tạo/khớp `LTT_DATABASE_URL` + migration).
- ⚠️ setup/2 in mật khẩu admin MỘT LẦN — cần xác nhận người dùng đã lưu.

### CHẶN — cần Admin (shell Claude không elevated)

1. `deploy\windows\5-lich-backup.ps1` — cài lịch backup sang `D:\LTTBackups`.
2. `setup\3-cloudflare.ps1` — dựng Tunnel (zone đã Active); có bước
   `cloudflared tunnel login` chọn zone `lttstudios.com`.
3. `setup\4-nghiem-thu.ps1` + kiểm `app.lttstudios.com` trên trình duyệt thật.

---

## 2026-07-31 — H0.1: thêm zone lttstudios.com vào Cloudflare + dọn DNS (điều khiển trình duyệt)

- **Mục tiêu:** đưa `app.lttstudios.com` lên mạng qua Cloudflare (Q27 — chuyển
  cả zone), giữ trang chủ `lttstudios.com` ở inet.vn OnePanel không đứt.
- **Hạng mục:** H0.1 — đã tới bước cuối cùng: đổi nameserver (CHẶN, chờ người dùng).

### Đã làm (điều khiển 2 tab qua Playwright)

- **Thêm site `lttstudios.com` vào Cloudflare, gói Free.** Tài khoản Cloudflare
  `Giaitritruyenthongltt@gmail.com` (account id 3530f3e5...).
- **Phát hiện quan trọng — IP gốc thật vs IP biên OneShield.** Quét tự động của
  Cloudflare chỉ thấy IP biên OneShield (rải: 103.166.183.10, 103.216.118.10,
  103.56.163.10; và 1 AAAA). Panel iNET mới cho IP gốc thật: **103.57.220.210**.
- **Đã kiểm chứng bằng curl:** gọi thẳng `103.57.220.210` (Host lttstudios.com,
  HTTPS) trả 200 và đúng trang chủ ("LTT Studios | Digital Products, Automation
  & Media Systems"), kích thước gần khớp bản qua OneShield. HTTP → 301 lên HTTPS.
  → Trỏ thẳng vào IP gốc DNS-only là **an toàn**, không cần OneShield.
- **Dọn DNS trên Cloudflare còn đúng bộ chuẩn (đều DNS only / mây xám):**
  - `A  lttstudios.com  103.57.220.210`  (DNS only)
  - `A  www            103.57.220.210`  (DNS only)
  - Đã xoá: bản ghi `app A 45.32.104.192` (Tunnel sẽ tạo lại CNAME sau), toàn bộ
    bản ghi IP-biên-OneShield của @ và www, và 1 bản ghi AAAA của www.
- **Lấy được nameserver Cloudflare cấp:** `elsa.ns.cloudflare.com` +
  `kipp.ns.cloudflare.com`.
- **ĐÃ ĐỔI NAMESERVER Ở iNET** (người dùng xác nhận "đổi ngay"): trang Chi tiết
  tên miền iNET nay hiện `elsa.ns.cloudflare.com` + `kipp.ns.cloudflare.com`.
  Đã BỎ TRỐNG checkbox "Tự động bật OneShield" (ta rời OneShield). Đã bấm "I
  updated my nameservers" ở Cloudflare → zone trạng thái **pending** ("Waiting
  for registrar to propagate", ~1–2 giờ, tối đa 24 giờ, Cloudflare tự kiểm).
- **Kiểm ngay sau đổi:** trang chủ vẫn 200 (còn qua IP biên OneShield do resolver
  công cộng chưa hết cache NS cũ). Khi NS mới lan tới, sẽ chạy thẳng 103.57.220.210.

### ZONE ĐÃ ACTIVE (2026-07-31, chỉ sau ít phút)

- NS mới lan tới resolver công cộng rất nhanh (8.8.8.8 + 1.1.1.1 trả `elsa`/`kipp`,
  `@` → 103.57.220.210). Cloudflare xác minh xong → zone **Active**: trang overview
  hiện đủ tính năng (CDN/cache, DDoS, SSL/TLS, WAF mặc định; có "Pause Cloudflare",
  đang cấp Universal SSL). **Phần zone/DNS Cloudflare COI NHƯ XONG.**
- Còn lại để `app.lttstudios.com` sống = **dựng Tunnel** (setup/3), cần app chạy
  `:8100` trước (setup/2). Cả hai cần Administrator.

### Đã chuẩn bị sẵn cho lần cài (Admin) — giảm rủi ro

- DB đã có sẵn từ dev H1–H4: role `ltt_app` + database `lttplatform` tồn tại,
  mật khẩu superuser trong `secrets/postgres-superuser.txt` khớp PostgreSQL 17
  đang chạy (đã kiểm bằng psql -w, auth OK).
- Đã copy `postgres-superuser.txt` vào `C:\LTTPlatform\secrets\` để `setup/2` tự
  tạo/khớp `LTT_DATABASE_URL` + chạy migration, không phải làm tay.
- CỐ Ý KHÔNG copy `app.env` dev sang (nó thiếu hash admin/session/token) — để
  `setup/2` tự sinh `app.env` đầy đủ + in mật khẩu admin mới đúng một lần.

### CHẶN — cần quyền Admin (shell của Claude không elevated)

1. `setup\2-cai-dat.ps1` (PowerShell **Run as administrator**) — cài nền tảng,
   in mật khẩu admin MỘT LẦN.
2. `setup\3-cloudflare.ps1` (Admin) — dựng Tunnel; có bước `cloudflared tunnel
   login` mở trình duyệt chọn zone `lttstudios.com`.
2. **Cài nền tảng:** `C:\LTTPlatform` hiện chỉ có thư mục `data` (rác từ test
   H1–H4). PostgreSQL 17 đang chạy, nhưng CHƯA có dịch vụ LTTStudioWeb/Worker/
   cloudflared, chưa có app/venv/secrets. Phải chạy `setup\2-cai-dat.ps1` trong
   **PowerShell Administrator** (shell hiện tại của Claude KHÔNG elevated).
   Script in mật khẩu admin đúng MỘT LẦN — lưu lại ngay.
3. **Dựng Tunnel:** sau khi zone Active + đã cài, chạy `setup\3-cloudflare.ps1`
   (Admin). Có một bước `cloudflared tunnel login` mở trình duyệt để cấp cert.
- **Lưu ý:** khi rời DNS iNET, OneShield (CDN/WAF của iNET) ngừng cho tên miền
  này; trang chủ chạy thẳng từ IP gốc 103.57.220.210 (đã kiểm chứng OK).

---

## 2026-07-31 — H0.1: kiện toàn script Cloudflare cho Q22 (phần chuẩn bị)

- **Mục tiêu:** chuẩn bị dựng Tunnel; người dùng chọn "đưa lên mạng trước H5".
- **Hạng mục:** H0.1 — phần code/tài liệu xong; phần thao tác chờ người dùng.
- **Trạng thái:** dở — chặn ở thao tác người dùng (Cloudflare + inet.vn + Admin).

### Đã làm (phía tôi)

- `setup/3-cloudflare.ps1`: sửa khớp Q22 (uỷ quyền subdomain). Bước đăng nhập
  nay hướng dẫn chọn zone `app.lttstudios.com` (không phải `lttstudios.com`
  gốc); bước trỏ DNS bắt lỗi "không tìm thấy zone" và giải thích điều kiện tiên
  quyết thay vì để một lỗi mờ mịt.
- `docs/04_CLOUDFLARE_TUNNEL.md`: thêm phần "Điều kiện tiên quyết — uỷ quyền
  subdomain (Q22)" với các bước cụ thể + hai đường lui nếu gói miễn phí không
  cho tạo zone subdomain.
- Kiểm cú pháp + ASCII + không-BOM cho script; test khoá `test_61` xanh.

### Chặn — cần người dùng (không code nào thay được)

1. **Kiểm Cloudflare zone subdomain (Q22 điều kiện chưa xác minh):** thử Add
   site `app.lttstudios.com` — gói miễn phí có thể từ chối.
2. Nếu được: uỷ quyền NS `app` ở inet.vn.
3. Cài hệ thống lên `C:\LTTPlatform` (setup/2, cần Administrator) — máy này
   CHƯA cài (`C:\LTTPlatform` chưa tồn tại).
4. Chạy `setup/3-cloudflare.ps1` (cần đăng nhập Cloudflare bằng trình duyệt).

### Lưu ý vận hành: máy phát triển == máy chủ

Máy này đang là máy phát triển và sắp thành máy chủ. Database `lttplatform`
hiện dev dùng (chỉ có schema, data nghiệm thu đã dọn). Khi `setup/2` cài
production, nó dùng lại chính PostgreSQL + database đó; schema đã sẵn. `setup/2`
sẽ đặt lại mật khẩu `ltt_app` → `secrets/app.env` của dev (ở `D:`) lệch, nhưng
không sao vì sau khi thành máy chủ chỉ chạy bản `C:\LTTPlatform`.

### Việc tiếp theo

1. **Người dùng:** kiểm Cloudflare zone subdomain (bước 1 ở trên) — báo kết quả.
2. Tuỳ kết quả: uỷ quyền NS rồi cài, hoặc đổi Q22 theo giao thức.
3. Sau khi lên mạng: H5 (thumbnail_api).

---

## 2026-07-31 — H3 (sổ credit) + H2.3 (web submit) + H4 (nghiệm thu): KHÉP HẠ TẦNG

- **Mục tiêu:** sổ credit không bao giờ sai; submit job qua web + tiến độ; nghiệm
  thu toàn chuỗi bằng demo.
- **Hạng mục:** H3 (trừ trang admin) + H2.3 + H4 — **hoàn thành**.
- **Trạng thái:** xong chuỗi chính. Giai đoạn hạ tầng (H1→H4) đã khép.

### Sổ credit (H3)

- Bảng `credit_entries` **chỉ ghi thêm**; số dư = tổng của sổ, không ô sửa đè.
  Với tiền, truy được nguồn gốc quan trọng hơn tiết kiệm vài dòng.
- `platform_core/credit.py`: nạp / cấp-tay / giữ-chỗ / quyết-toán / hoàn.
  Giữ chỗ kiểm số dư TRƯỚC (không đủ → không tạo job, không gọi API). Quyết
  toán/hoàn **idempotent theo job** (worker retry không trừ/hoàn hai lần).
- `platform_core/job_submit.py`: tạo job + giữ chỗ credit trong CÙNG transaction.
  Dedupe → giữ chỗ đúng một lần (chặn "Tạo lại"/F5 — đúng lỗi P0-5 của BOT GEMINI).
- Nối worker: complete → quyết toán; error hẳn → hoàn (job_runner).

### Web submit + tiến độ (H2.3)

- `server/routes/jobs.py`: danh sách + chi tiết + fragment tiến độ, **lọc theo
  user** (A xem job B → 404).
- Tiến độ đẩy về trình duyệt bằng HTMX (Q18). **Self-host** `htmx.min.js` trong
  `server/static/` + mount StaticFiles — CSP chặn CDN nên không dùng unpkg.
- `apps/demo` thêm nút "Chạy qua hàng đợi" → khuôn cho app thật.

### Nghiệm thu toàn chuỗi (H4) — browser + PostgreSQL + worker thật

Đăng nhập (user CSDL) → /demo → "Chạy qua hàng đợi" → job tạo + giữ chỗ credit
→ worker process nhặt → xử lý → **trang HTMX tự cập nhật** queued→done → kết quả
đúng ("nghiem thu toan chuoi H4" đảo ngược). Console 0 lỗi.

Sổ credit sau đó (đọc thật từ Postgres):
    topup  +100
    hold   -1    giu cho job
    settle +0    giu 1, that 1
    -> so du 99. Dau vet append-only day du, dung tuyet doi.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `python -m pytest -q` | **1.513 passed**, 1 skipped, 23 subtests |
| `tests/test_68_credit.py` | 13 passed |
| `tests/test_69_web_jobs.py` | 6 passed (gồm A-không-đọc-job-B) |
| Nghiệm thu H4 browser + Postgres + worker | chuỗi đầy đủ, sổ đúng, console sạch |
| `python tools/scan_source_secrets.py` | 0 finding |

### Đã tách/dời có lý do

- **H3-admin** (trang quản trị credit/quyền qua sqladmin, tạo admin trong DB,
  gỡ đường admin-env): gom vào một mốc riêng — cả cụm là mặt admin, dùng chung
  sqladmin, không phải mặt khách.
- Hai mục H4 phụ (giết worker giữa job dài; tắt CSDL báo lỗi UI): cần tình huống
  chạy-lâu hoặc thuộc observability, không chặn H5.

### Cách lùi lại

Xoá `platform_core/{credit,job_submit}.py`, `server/routes/jobs.py`,
`server/static/`, 3 template job, `tests/test_68_credit.py`,
`tests/test_69_web_jobs.py`, migration `..._credit_entries`; hoàn
`platform_core/{models,job_runner}.py`, `server/{app,deps,templating}.py`,
`server/templates/{base,demo}.html`, `apps/demo/routes.py`.

### === GIAI ĐOẠN HẠ TẦNG (H1→H4) ĐÃ KHÉP ===

Nền tảng giờ chạy được toàn chuỗi: người dùng → phân quyền → hàng đợi job →
worker → sổ credit → tiến độ web. Mọi mắt xích nghiệm thu trên PostgreSQL thật,
phần lớn có cả browser. Sẵn sàng cắm tool tính phí đầu tiên (H5).

### Việc tiếp theo

1. H5 — port `thumbnail_api` từ BOT GEMINI thành app đầu tiên tính phí (Q11).
2. H3-admin — trang quản trị (sqladmin) khi cần vận hành thật.
3. (người dùng) H0.1 Cloudflare + khoá Resend/Turnstile.

---

## 2026-07-31 — H2.1+H2.2: hàng đợi job + worker (bỏ procrastinate)

- **Mục tiêu:** việc dài chạy ngoài vòng đời request, sống sót restart, không
  bao giờ hai worker làm trùng.
- **Hạng mục:** H2.1 (hàng đợi) + H2.2 (worker) — **hoàn thành**. H2.3 (web UI +
  tiến độ) tách ra, làm cùng H3.
- **Trạng thái:** xong phần lõi, nghiệm thu trên PostgreSQL thật.

### Quyết định đổi hướng: bỏ procrastinate (Q13 → Q26)

Khi thiết kế H2 mới thấy procrastinate giữ hàng đợi trong **bảng riêng của
nó**, tách khỏi bảng `jobs` nghiệp vụ → hai kho phải đồng bộ. Và để job+credit
atomic (chính lý do chọn nó) phải cho `defer` chung transaction với SQLAlchemy —
chia sẻ connection, tài liệu mỏng. Nghịch lý: cái lý do chọn nó lại **dễ hơn**
khi tự quản một bảng. Đưa lựa chọn cho chủ dự án → chọn tự viết. Dọn Q13 đúng
giao thức (đánh dấu ĐÃ THAY, thêm Q26, gỡ procrastinate khỏi venv, sửa kế hoạch).

### Đã làm

- Bảng `jobs` (nguồn chân lý duy nhất) + `platform_core/jobs.py`:
  - `submit` không commit (caller commit cùng credit — atomic hiển nhiên);
  - `claim` dùng `FOR UPDATE SKIP LOCKED` (nhiều worker không nhặt trùng);
  - `fail` retry luỹ thừa có giới hạn rồi mới thành `error`;
  - `reclaim_orphans` nhặt lại job của worker chết (tính một lượt đã tiêu);
  - `dedupe_key` chống double-submit/F5;
  - `resolve_handler` qua registry, không hardcode slug.
- `platform_core/job_runner.py` + `job_worker.py`: vòng chạy + entry. Mỗi bước
  (claim/tiến độ/complete) là transaction ngắn RIÊNG — không giữ khoá dòng suốt
  thời gian chạy handler.
- Dịch vụ `LTTStudioWorker` riêng (Q6) trong `setup/2-cai-dat.ps1`;
  `update.ps1`/`rollback.ps1`/`4-nghiem-thu.ps1` biết về nó.

### Nghiệm thu trên PostgreSQL thật (không phải suy luận)

- **SKIP LOCKED:** 5 worker (thread) × 30 job → mỗi job chạy ĐÚNG MỘT LẦN,
  không trùng, tất cả done. Đây là rủi ro lớn nhất (job làm hai lần trên API
  tính tiền) — chứng minh, không giả định.
- **Worker process thật:** chạy `job_worker.py`, submit job demo → worker nhặt →
  complete với kết quả đúng (`"worker process that"` → đảo ngược).

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `python -m pytest -q` | **1.495 passed**, 1 skipped, 23 subtests |
| `tests/test_67_hang_doi_job.py` (SQLite) | 15 passed |
| SKIP LOCKED 5 worker × 30 job trên PostgreSQL | không trùng, tất cả done |
| Worker process thật end-to-end | job nhặt → complete đúng |
| `python tools/scan_source_secrets.py` | 0 finding |

### Quyết định mới

Q26 — hàng đợi tự quản bảng jobs + SKIP LOCKED (thay Q13 procrastinate).

### Hoãn có lý do

- Lọc capability worker (Q6): claim chưa lọc theo `requires` vì một worker đa
  năng. Chỗ lọc đã ghi sẵn trong `claim()`, thêm khi có nhiều máy.
- H2.3 (web submit + tiến độ + trang jobs): tách ra làm cùng H3, vì đường
  submit job và trừ credit là cùng một giao dịch — viết một lần có cả hai.

### Cách lùi lại

Xoá `platform_core/{jobs,job_runner}.py`, `job_worker.py`,
`tests/test_67_hang_doi_job.py`, migration `..._them_bang_jobs.py`; hoàn
`platform_core/models.py`, `setup/2-cai-dat.ps1`, `deploy/windows/*.ps1`,
`setup/4-nghiem-thu.ps1`.

### Việc tiếp theo

1. H3 — sổ credit (append-only, giữ chỗ → quyết toán → hoàn) + H2.3 (web submit
   + tiến độ) cùng lúc: submit job và trừ credit là một giao dịch.
2. (người dùng, độc lập) H0.1 Cloudflare + khoá Resend/Turnstile.

---

## 2026-07-31 — H1.4: phân quyền app + KHÉP H1 (Người dùng)

- **Mục tiêu:** mỗi (user × app) mở/khoá/ẩn; chặn ở tầng route, không chỉ ẩn nút.
- **Hạng mục:** H1.4 — **hoàn thành**. Cùng đó **khép toàn bộ H1**.
- **Trạng thái:** xong.

### Đã làm

- Bảng `app_access` + `platform_core/app_access.py`: mức `enabled`/`locked`/
  `hidden`, mặc định mở (Q25), chỉ lưu ngoại lệ (đặt về mặc định thì XOÁ dòng).
- `server/access_middleware.py`: chặn ở tầng route qua middleware đọc registry
  → ánh xạ path → app → kiểm quyền. Phủ **mọi** đường vào kể cả gõ thẳng URL,
  và không phải sửa từng app (giữ hợp đồng: nền tảng không biết trước app nào).
  - `hidden` → 404 (không xác nhận app tồn tại), `locked` → 403.
  - Fail-open có chủ ý: chưa có DB / admin-env / lỗi → cho qua (mặc định mở,
    chốt chặn tiền vẫn là credit).
  - Add TRƯỚC SessionMiddleware để chạy SAU nó (đọc được session).
- Trang chủ **và** sidebar cùng lọc app `hidden` theo user (`nav_apps(request)`).
- `tests/test_66_phan_quyen_app.py` — 10 test.

### Nghiệm thu chặn route trên PostgreSQL thật

Tạo user tạm → đăng nhập → `/demo` mặc định 200 → admin đặt `hidden` → `/demo`
404 → đặt `locked` → 403 → dọn. Đúng cả ba mức.

### Lỗi tiềm ẩn sửa kèm: CSP sẽ chặn Turnstile

CSP cũ chỉ cho script `'self'`. Turnstile (H1.3) nạp script + iframe từ
`challenges.cloudflare.com` → sẽ bị CSP chặn ngay khi bật, một lỗi chỉ lộ lúc
production bật chống-bot. Đã thêm domain đó vào `script-src` + `frame-src`.

### Test đã sửa (không làm yếu)

`test_31::test_g2_navigation_links_every_page` grep chuỗi cứng `nav_apps()`.
H1.4 đổi thành `nav_apps(request)` (thêm lọc theo user). Bất biến — "sidebar
sinh từ registry" — vẫn đúng; đổi assertion sang khớp `nav_apps(`.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `python -m pytest -q` | **1.480 passed**, 1 skipped, 23 subtests |
| `tests/test_66_phan_quyen_app.py` | 10 passed |
| Nghiệm thu chặn route trên PostgreSQL thật | 200 / 404 / 403 đúng |
| `python tools/scan_source_secrets.py` | 0 finding |

### Quyết định mới

Q25 — mặc định phân quyền app là MỞ; chỉ lưu ngoại lệ; admin luôn thấy hết.

### Cách lùi lại

Xoá `platform_core/app_access.py`, `server/access_middleware.py`,
`tests/test_66_phan_quyen_app.py`, migration `..._them_bang_app_access.py`;
hoàn `platform_core/models.py`, `server/app.py`, `server/routes/dashboard.py`,
`server/templating.py`, `server/templates/base.html`, `tests/test_31...`.

### KHÉP H1 — còn tồn đọng chuyển sang H2/H3

- Chờ khoá người dùng (H1.3): Resend (`RESEND_API_KEY`, `LTT_MAIL_FROM`, 3 DNS)
  và Turnstile (`TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET_KEY`).
- Nối ở H3: cấp credit dùng thử sau xác thực; trang admin đặt quyền + tạo admin
  trong DB (qua sqladmin) — đó cũng là lúc gỡ đường admin-env (H1.2).

### Việc tiếp theo

1. **H2 — hàng đợi job** (procrastinate trên Postgres, Q13): bảng jobs, worker
   tiến trình riêng, giữ chỗ job, retry, tiến độ.
2. (người dùng, độc lập) H0.1 Cloudflare + các khoá Resend/Turnstile.

---

## 2026-07-31 — H1.3: đăng ký, xác thực email, chống lạm dụng

- **Mục tiêu:** cho tự đăng ký an toàn (Q7) — không để credit dùng thử bị hút
  cạn bằng tài khoản ảo (Q9).
- **Hạng mục:** H1.3 — **xong phần code**; phần cần khoá thật để lại cho người dùng.
- **Trạng thái:** xong (code), có 2 việc chờ khoá của người dùng + 1 việc nối ở H3.

### Đã làm

- `platform_core/mailer.py`: tầng gửi mail tách khỏi nghiệp vụ. `ResendMailer`
  (production, gọi API qua httpx — không thêm SDK) và `ConsoleMailer` (dev/test,
  giữ thư trong RAM để test đọc lại link). Chọn theo biến môi trường. Nhờ tách
  này, toàn bộ luồng đăng ký test được **không cần khoá Resend**.
- `platform_core/tokens.py`: token xác thực email + đặt lại mật khẩu bằng
  `itsdangerous` (đây là chỗ Q24 thay fastapi-users). Ký + hết hạn + mỗi loại
  một salt riêng nên không dùng lẫn được.
- `server/auth/turnstile.py`: xác minh Turnstile phía máy chủ (Q20). Bỏ qua có
  kiểm soát khi chưa cấu hình; lỗi mạng tới Cloudflare thì TỪ CHỐI (an toàn
  mặc định), không cho qua.
- `platform_core/antifraud.py`: chặn tên miền mail dùng-một-lần (danh sách tĩnh,
  không thêm phụ thuộc) + giới hạn số tài khoản/IP/ngày (đếm qua cột
  `registration_ip` mới).
- `server/routes/register.py` + 5 template: đăng ký, xác thực email, quên/đặt
  lại mật khẩu. Đặt lại mật khẩu **thu hồi mọi phiên**.
- Migration thêm cột `registration_ip`.
- `tests/test_65_dang_ky.py` — 8 test.

### Không lộ email nào đã đăng ký — ở ba chỗ

- Đăng ký trùng email → trả trang "đã gửi thư" GIỐNG HỆT lần đầu (không báo
  "email đã tồn tại").
- Quên mật khẩu với email không tồn tại → phản hồi giống hệt email có tồn tại.
- (từ H1.2) xác thực sai không phân biệt email-không-có với sai-mật-khẩu.

### Nghiệm thu

- 8 test trên SQLite.
- **PostgreSQL thật + browser (Playwright):** mở /register → điền form → submit
  → user vào Postgres với `is_verified=False`, `registration_ip=127.0.0.1` →
  bấm link xác thực → trang báo thành công → DB đổi `is_verified=True`. Dọn
  user tạm sau đó. Console chỉ có 1 lỗi favicon 404 (vô hại).

### Lỗi thật phát hiện: migration chỉ-Postgres làm vỡ round-trip SQLite

Migration `registration_ip` dùng `ALTER COLUMN ... DROP DEFAULT` (bỏ default sau
khi backfill hàng cũ). PostgreSQL chạy được (đã nghiệm thu), nhưng SQLite không
hỗ trợ `ALTER COLUMN` → test round-trip trên SQLite vỡ. Bọc bước đó theo
`dialect.name == "postgresql"`: production là Postgres nên vẫn đúng ý định, còn
SQLite (chỉ dùng test bộ máy migration) không cần bỏ default. Test round-trip
SQLite chính là thứ bắt được — nó chạy MỌI migration nên tự bảo vệ chống lỗi
này tái diễn.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `python -m pytest -q` | **1.470 passed**, 1 skipped, 23 subtests |
| `tests/test_65_dang_ky.py` | 8 passed |
| Round-trip migration trên SQLite + PostgreSQL thật | sạch cả hai |
| Nghiệm thu đăng ký→xác thực trên PostgreSQL + browser | thành công |
| `python tools/scan_source_secrets.py` | 0 finding |

### Còn chờ người dùng (code đã sẵn sàng)

1. Resend: đặt `RESEND_API_KEY` + `LTT_MAIL_FROM` + 3 bản ghi DNS (Q19) → thư
   xác thực tới hộp thư thật (giờ đang ghi vào log qua ConsoleMailer).
2. Turnstile: đặt `TURNSTILE_SITE_KEY` + `TURNSTILE_SECRET_KEY` (Q20) → form
   đăng ký có ô chống bot thật.

### Nối ở H3

- Cấp credit dùng thử sau xác thực: `/verify-email` đã có đúng chỗ nối (ghi chú
  trong code), chờ bảng credit ở H3.

### Cách lùi lại

Xoá `platform_core/{mailer,tokens,antifraud}.py`, `server/auth/turnstile.py`,
`server/routes/register.py`, 5 template mới, `tests/test_65_dang_ky.py`,
migration `..._them_cot_registration_ip.py`; hoàn `platform_core/models.py`,
`platform_core/users.py`, `server/app.py`, `server/templates/{login,base_plain}.html`.

### Việc tiếp theo

1. H1.4 — phân quyền app cho từng người dùng (mở/khoá/ẩn), chặn ở tầng route.
2. (người dùng, độc lập) H0.1 Cloudflare, và các khoá Resend/Turnstile ở trên.

---

## 2026-07-31 — H1.2: người dùng, phiên đăng nhập phía máy chủ

- **Mục tiêu:** hệ thống biết "ai đang dùng"; dữ liệu người này người kia tách nhau.
- **Hạng mục:** H1.2 — **hoàn thành**.
- **Trạng thái:** xong (bước "gỡ đường admin-env" dời sang H3 — có lý do bên dưới).

### Quyết định đổi hướng: bỏ fastapi-users (Q14 → Q24)

Khi bắt tay H1.2 mới thấy `fastapi-users` (DB adapter) **bắt buộc
`sqlalchemy[asyncio]`** — async-only từ v10. Nền H1.1 vừa xây là đồng bộ, và
phần auth đang chạy production cũng đồng bộ. Đưa nó vào sẽ kéo async engine vào
codebase đồng bộ, **thay luôn cơ chế session đang chạy production**, mà vẫn phải
tự viết trang HTML. Lợi ích chính (logic token xác thực email) thì `itsdangerous`
đã có sẵn làm được.

Lúc chốt Q14 tôi chưa nhìn code thật. Đưa lựa chọn cho chủ dự án, chọn Q24: tự
viết trên nền đồng bộ. Đã dọn Q14 theo đúng giao thức (đánh dấu ĐÃ THAY, thêm
Q24, truy mọi nơi nhắc fastapi-users và sửa).

### Đã làm

- `platform_core/models.py`: bảng `users` (khoá chính UUID — không lộ quy mô,
  không đoán được id người khác; email chuẩn hoá chữ thường; `is_verified` tách
  khỏi `is_active`) và `sessions` (phiên phía máy chủ).
- `platform_core/users.py`: nghiệp vụ tách khỏi HTTP — tạo user, xác thực,
  tạo/thu hồi phiên, đổi mật khẩu. Băm mật khẩu **tái dùng** PBKDF2 của
  `server/auth/password_hashing.py`, không phát minh cách băm thứ hai.
- `server/deps.py`: `get_db` (bắt buộc, commit-khi-xong) và `mo_db_optional`
  (trả None khi CSDL chưa cấu hình — để đường admin-env vẫn chạy khi không có DB).
- `server/auth/session.py`: hai đường song song — admin-env (cookie, không chạm
  DB, đường lui) và user CSDL (cookie mang `sid` trỏ bảng sessions). Đường CSDL
  thất bại im lặng khi chưa có DB. `require_login` giữ nguyên chữ ký nên không
  route nào phải đổi.
- `server/routes/auth.py`: login thử user CSDL trước, admin-env sau.

### Ba tính chất bảo mật, có test

- **Mật khẩu không lưu thô** — chỉ hash PBKDF2.
- **Xác thực sai không tiết lộ email nào đã đăng ký** — email-không-tồn-tại và
  sai-mật-khẩu đều trả None, và vẫn băm-rồi-so với hash giả để thời gian phản
  hồi không làm timing oracle.
- **Phiên thu hồi được** — đăng xuất xoá dòng ở DB; đổi mật khẩu đá mọi phiên.
  Đây là điểm khác biệt cốt lõi so với cookie ký thuần (không có id để thu hồi).

### Điều chỉnh có lý do — CHƯA gỡ đường admin-env

Kế hoạch gốc ghi "đường mới xanh thì gỡ session.py cũ". Nhưng gỡ admin-env bây
giờ là sai: chưa có cách tạo admin **trong CSDL** (trang quản trị tới H3 mới có
qua sqladmin). Gỡ trước = một CSDL trống thì không ai đăng nhập được. Giữ
admin-env làm đường lui chính thức tới H3.

### Hai lỗi thật phát hiện trong lúc làm

1. **So sánh datetime naive vs aware.** SQLite không giữ tzinfo nên `expires_at`
   đọc ra là naive, so với thời gian aware thì ném TypeError. PostgreSQL không
   bị, nhưng code nên chịu được cả hai backend (test SQLite, production Postgres).
   Thêm `_aware()` chuẩn hoá tại điểm so sánh.
2. **Ký tự điều khiển tái diễn trong chính nhật ký H1.1** — đoạn văn mô tả lỗi
   `\b`/`\a` lại chứa đúng ký tự đó (heredoc nuốt escape). Lần thứ hai trong một
   phiên. `test_61` bắt được. Đã sửa và ghi lại như bằng chứng nó âm thầm cỡ nào.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `python -m pytest -q` | **1.462 passed**, 1 skipped, 23 subtests, 256s |
| `tests/test_64_nguoi_dung.py` (SQLite) | 18 passed |
| Nghiệm thu đăng nhập trên **PostgreSQL thật** | 303→200→303, phiên bị thu hồi (0 dòng còn lại), user tạm đã dọn |
| `python tools/scan_source_secrets.py` | 0 finding |

### Cách lùi lại

Xoá `platform_core/users.py`, `server/deps.py`,
`tests/test_64_nguoi_dung.py`, migration `..._them_bang_users_va_sessions.py`;
hoàn `platform_core/models.py`, `server/auth/session.py`,
`server/routes/auth.py` về commit trước.

### Việc tiếp theo

1. H1.3 — đăng ký + xác thực email (Resend) + Turnstile chống lạm dụng. Đây là
   phần bắt buộc trước khi cho tự đăng ký (Q7): không có nó, credit dùng thử bị
   hút cạn bằng tài khoản ảo.
2. (người dùng, độc lập) H0.1 — kiểm tra Cloudflare zone subdomain.

---

## 2026-07-31 — H1.1 đóng: nghiệm thu trên PostgreSQL thật

- **Mục tiêu:** đóng nốt H1.1 sau khi có PostgreSQL.
- **Hạng mục:** H1.1 — **hoàn thành**.
- **Trạng thái:** xong.

### Đã làm

Người dùng cài PostgreSQL 17 qua winget và uỷ quyền tôi tự tạo + lưu mật khẩu
(sẽ đổi sau khi hoàn tất). Trình cài winget đặt mật khẩu superuser mặc định là
`postgres` — yếu, nên việc đầu tiên là thay.

- Đổi mật khẩu `postgres` → mật khẩu ngẫu nhiên 28 ký tự, lưu
  `secrets/postgres-superuser.txt` (đã gitignore, đọc bằng `utf-8-sig`).
- Tạo role `ltt_app` + database `lttplatform` (Q23 — ứng dụng không dùng
  superuser). Ghi `LTT_DATABASE_URL` vào `secrets/app.env`.
- `alembic upgrade head` chạy trên **PostgreSQL thật** — không còn là SQLite
  tạm. Bảng `platform_info` + `alembic_version` đúng, phiên bản
  `0001_platform_info`.
- `/health/ready` → `{"status":"ready","database":"ok"}` với CSDL thật.

### Nghiệm thu khôi phục thật — mảnh quan trọng nhất

Một bản sao lưu chưa từng thử khôi phục thì chưa phải bản sao lưu. Đã chạy đủ
chu trình bằng chính công cụ mà `backup.ps1` dùng:

1. ghi một dòng nhận biết được vào `lttplatform`;
2. `pg_dump -Fc` ra file (3.952 bytes);
3. tạo database mới `lttplatform_restore_test`, `pg_restore` vào đó;
4. đọc lại dòng vừa ghi từ database khôi phục → **KHỚP**;
5. dọn sạch: xoá database test, file dump, dòng nhận biết.

### Cách kiểm chứng mật khẩu

Toàn bộ thiết lập chạy bằng script Python (tránh bẫy quoting của PowerShell),
mật khẩu **không bao giờ đi qua khung chat**: sinh bằng `secrets`, ghi thẳng
vào `secrets/`, và chỉ in ra URL đã che mật khẩu để đối chiếu.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `alembic upgrade head` trên Postgres thật | thành công, bảng đúng |
| `/health/ready` với CSDL thật | 200, `database: ok` |
| Chu trình `pg_dump` → `pg_restore` → đọc lại | KHỚP |
| `git check-ignore secrets/app.env, postgres-superuser.txt` | cả hai IGNORED |

Bộ test đầy đủ đã 1.450 pass ở lần chạy trước đó (không đổi code kể từ đó).

### Còn tồn đọng

- Mật khẩu CSDL hiện do tôi tạo trong quá trình xây; **đổi lại khi hoàn tất**
  (người dùng đã dặn).
- Trên máy chủ thật, bộ cài `setup/2-cai-dat.ps1` sẽ tự làm lại đúng chuỗi này
  — nhưng chuỗi đó **chưa chạy trên một máy chủ thật**, mới chạy tương đương
  bằng tay trên máy phát triển này.

### Việc tiếp theo

1. H1.2 — bảng người dùng + `fastapi-users` dựng **song song** với auth hiện
   có, chỉ gỡ cũ khi phần mới đã xanh.
2. (người dùng, độc lập) H0.1 — kiểm tra Cloudflare cho tạo zone subdomain.

---

## 2026-07-31 — H1.1: lớp CSDL PostgreSQL + Alembic

- **Mục tiêu:** dựng lớp CSDL và bộ máy di trú lược đồ.
- **Hạng mục:** H1.1 — **dở, bị chặn**.
- **Trạng thái:** phần code xong và đã kiểm chứng; phần cần quyền
  Administrator chưa làm được.

### Đã làm

**1. `platform_core/db.py`** — engine dùng chung, session factory, và
`che_mat_khau()` áp cho **mọi** đường lỗi. Lý do tồn tại của hàm che: thông báo
lỗi của driver PostgreSQL thường nhúng nguyên chuỗi kết nối, `/health/ready`
thì cố ý không yêu cầu đăng nhập (để reverse proxy thăm dò được), và người ta
hay dán nguyên thông báo lỗi vào chat để hỏi. Ba điều đó cộng lại là một đường
rò rất thật.

**2. Alembic** — `alembic.ini` **cố ý không có dòng `sqlalchemy.url`** (file đó
nằm trong git); `env.py` đọc từ `LTT_DATABASE_URL`. Migration đầu tiên tạo bảng
`platform_info`.

*Lệch so với kế hoạch, có chủ ý:* kế hoạch ghi "migration đầu tiên tạo bảng
rỗng". Một migration không tạo gì thì **không kiểm chứng được** — vòng
`upgrade` → `downgrade` → `upgrade` không chứng minh được điều gì. Đổi thành
một bảng nhỏ có thật (ghi lược đồ này dựng khi nào, bởi bản nào), vừa hữu ích
khi hỗ trợ vừa làm việc kiểm chứng có nghĩa.

**3. `/health/ready` kiểm tra CSDL bằng `SELECT 1` thật**, không phải kiểm tra
"đã cấu hình chuỗi kết nối chưa". Một CSDL đã cấu hình nhưng không với tới được
chính là trạng thái khiến ứng dụng trông khoẻ mạnh trong khi mọi request đều
hỏng.

Tạm thời **chưa cấu hình CSDL chưa bị coi là lỗi** — chưa phần nào của ứng dụng
phụ thuộc vào nó, và bắt trả 503 ngay bây giờ sẽ làm trình quản lý dịch vụ khởi
động lại liên tục vì một phụ thuộc chưa ai dùng tới. **Phải đổi cùng lúc với
H1.2**, test đã ghi rõ điều đó.

**4. Bộ cài và sao lưu** — `setup/2-cai-dat.ps1` cài PostgreSQL, tạo role +
database riêng, ghi `LTT_DATABASE_URL`, rồi chạy `alembic upgrade head`
**trước** khi khởi động dịch vụ. `backup.ps1` thêm `pg_dump`.

### Hai lỗi thật phát hiện trong lúc làm

**Lỗi 1 — kết nối treo 130 giây.** Một test nối tới cổng chết mất 130 giây mới
bỏ cuộc. Đây không phải lỗi của test mà là lỗi của lớp CSDL: trên production,
một lần kết nối treo sẽ **giữ luôn worker phục vụ request** hai phút. Người
dùng chỉ thấy trang treo, và trình quản lý dịch vụ không thấy gì bất thường để
khởi động lại. Đã đặt `CONNECT_TIMEOUT_S = 5` → còn 5,16 giây, có test chốt
ngưỡng.

**Lỗi 2 — ký tự điều khiển vô hình lọt vào script (lỗi của tôi).** Khi chèn
đoạn PowerShell bằng chuỗi Python không phải raw-string, đường dẫn kết thúc
bằng "backslash-b-i-n" bị biến thành ký tự chr(8) rồi "in", và
"backslash-a-p-p" thành chr(7) rồi "pp". Năm chỗ, hai file. (Đúng lỗi này còn
tái diễn ngay trong chính đoạn nhật ký mô tả nó — lần thứ hai trong một phiên,
đủ để thấy nó âm thầm cỡ nào.)

Hậu quả nếu lọt qua:
- bộ cài không tìm thấy PostgreSQL rồi báo "cài thất bại" — **sai nguyên nhân**;
- `backup.ps1` không thấy `app.env` nên **âm thầm bỏ qua CSDL**, cho ra một bản
  sao lưu trông y hệt bản đầy đủ và chỉ lộ ra đúng lúc cần khôi phục.

Đáng chú ý: kiểm tra ASCII sẵn có **không** bắt được (các ký tự này < 128), và
kiểm tra cú pháp PowerShell cũng không (chúng nằm trong chuỗi). Dự án đã có
test ký tự điều khiển cho **tài liệu** từ một lần vấp trước, nhưng không có cho
**script** — mà script mới là chỗ nguy hiểm hơn vì không ai đọc bằng mắt. Đã bổ
sung vào `test_62_khoa_logic.py`.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `python -m pytest -q` | **1.450 passed**, 1 skipped, 23 subtests, 277s |
| `python -m pytest tests/test_63_lop_csdl.py -q` | 17 passed |
| Vòng di trú thật `upgrade` → `downgrade` → `upgrade` | sạch cả ba lần (SQLite tạm) |
| Kiểm tra cú pháp + ASCII + BOM cho 2 script `.ps1` | OK |
| `python tools/scan_source_secrets.py` | **0 finding** |

1.422 → 1.450 = +28 test (17 ở `test_63`, 11 ở `test_62` gồm 5 ca kiểm ký tự
điều khiển cho script).

### Quyết định mới

Q23 — ứng dụng dùng role `ltt_app`, **không bao giờ** dùng superuser
`postgres`. Lý do và cái giá ghi ở `QUYET_DINH_NEN_TANG.md`.

### Cách lùi lại

Xoá `platform_core/db.py`, `platform_core/models.py`, `alembic.ini`,
`alembic/`, `tests/test_63_lop_csdl.py`; hoàn `server/routes/health.py`,
`requirements-server.txt`, `setup/2-cai-dat.ps1`, `deploy/windows/backup.ps1`
về commit trước.

### Bị chặn — cần người dùng

**PostgreSQL chưa cài được: không có quyền Administrator.**
Cài PostgreSQL dạng dịch vụ Windows cần quyền đó, và tôi không tự nâng quyền
được (UAC là hộp thoại tương tác).

Hệ quả: ba việc chưa kiểm chứng được trên PostgreSQL thật —
1. migration chạy trên Postgres (mới chỉ chứng minh trên SQLite tạm);
2. bộ cài tạo được role/database;
3. **khôi phục thật** từ file `pg_dump`.

Việc thứ 3 quan trọng nhất: một bản sao lưu chưa từng được khôi phục thử thì
chưa phải là bản sao lưu.

### Việc tiếp theo

1. **Người dùng:** cài PostgreSQL (xem lựa chọn tôi đưa ra cuối phiên).
2. Sau khi có PostgreSQL: chạy migration thật + thử khôi phục `pg_dump` →
   đóng nốt H1.1.
3. H1.2 — bảng người dùng + đăng nhập, dựng `fastapi-users` **song song** với
   phần auth hiện có, chỉ gỡ cũ khi phần mới đã xanh.

---

## 2026-07-31 — H0: dọn nền, đưa vào git, chuẩn hoá tài liệu

- **Mục tiêu:** dọn sạch nền trước khi xây hạ tầng nhiều người dùng; chuẩn hoá
  tài liệu; chốt hướng đi thành một nguồn chân lý duy nhất.
- **Hạng mục:** H0 — hoàn thành.
- **Trạng thái:** xong.

### Đã làm

**1. Lần đầu đưa dự án vào git.** Trước đó ~45.000 dòng không hề có version
control, trong khi đã có một bản production đang chạy. Đây là rủi ro vận hành
lớn nhất, lớn hơn mọi lỗi kỹ thuật tìm được, vì nó làm mọi lỗi khác khó sửa và
không lùi được. Commit gốc: `44f36d6`.

**2. Vá lỗi ranh giới đường dẫn (nghiêm trọng).**
`TokenStore`, `content_history.db`, `page_health.db`, `audit_log.jsonl` và các
cache đều dùng `os.path.join("data", ...)` — tương đối theo **thư mục làm
việc**, không theo `LTT_DATA_DIR`. Trên máy chủ, dịch vụ chạy tại
`C:\LTTPlatform\app` nên chúng rơi vào `app\data\` — đúng thư mục bị chuyển
sang `app.previous` rồi tạo mới ở **mỗi lần cập nhật**.

Hậu quả nếu không sửa: token Facebook/TikTok biến mất sau lần cập nhật kế tiếp,
và biến mất **âm thầm** — `_save()` có `os.makedirs(exist_ok=True)` nên nó tạo
thư mục rồi ghi bình thường, không báo lỗi gì.

Kiểm chứng: đặt `LTT_DATA_DIR=C:/LTTPlatform/data` rồi đổi CWD sang `C:\Users`
- trước: `C:\Users\data\tokens.enc`
- sau: `C:\LTTPlatform\data\tokens.enc`

Lỗi này từng được phát hiện và sửa cho `core/session_lock.py` nhưng chỉ sửa
đúng một module. Nay gom về một chỗ: `core.runtime_paths.data_path()`.

**3. Ba lỗi phụ lộ ra trong lúc sửa lỗi trên** — không cái nào từng có ai thấy:

- `tests/conftest.py` gán đè `_DEFAULT_DB_PATH` để cách ly test khỏi CSDL thật,
  nhưng vì đó là **giá trị mặc định của tham số** (gán một lần lúc import) nên
  việc gán đè không bao giờ có tác dụng — bộ test vẫn ghi vào CSDL thật.
- `core/i18n.py` đọc bản dịch cạnh **mã nguồn**, trong khi bộ cài cố ý chép bản
  dịch vào thư mục **dữ liệu**. Trên máy chủ không nạp được bản dịch nào, và
  `t()` lặng lẽ rơi về tiếng Anh rồi về chính khoá.
- `audit_checklist` tìm logo TikTok theo đường dẫn tương đối, nên người dùng
  tải logo về đúng chỗ tài liệu chỉ mà cảnh báo vẫn không bao giờ tắt.

**4. Chốt cận trên phiên bản thư viện.** `pip install` kéo về Starlette 1.3
(bản major mới) làm việc liệt kê route không còn hoạt động. Ứng dụng vẫn chạy
đúng, nhưng **hai lần cài cùng một mã nguồn cho ra hai môi trường khác nhau**.
Đã thêm `<` cho mọi thư viện (Q17).

**5. Đổi cổng mặc định 8000 → 8100** (Q4). Máy này còn chạy `D:\BOT GEMINI`
trên cổng 8000, phục vụ 13 người dùng thật — bộ cài cũ sẽ giành cổng với nó.

**6. Chuẩn hoá tài liệu.** 19 file cũ chuyển vào `docs/_luutru/` kèm README
giải thích từng file là gì và vì sao ngừng dùng. Viết lại `AGENTS.md`,
`CLAUDE.md`, `docs/00`. Thêm `QUYET_DINH_NEN_TANG.md` (nguồn chân lý),
`KE_HOACH_TRIEN_KHAI.md`, `KHAO_SAT_BOT_GEMINI.md`, và file này.

Trước đó có **bốn hệ đánh số kế hoạch song song** (P0–P11, PA–PE, W1–W6, 00–04)
và không hệ nào tuyên bố mình đã bị thay thế. Từ nay chỉ còn một hệ: `H`.

**7. Bộ khoá logic** `tests/test_62_khoa_logic.py` (11 test): biến các ràng
buộc bất biến thành test, để lần sau ai vi phạm là biết ngay chứ không phải nhớ
đã đọc ở đâu. Khoá: đường dẫn dữ liệu, không import chéo sang BOT GEMINI, cổng
8100, cận trên phiên bản, ba tầng tài liệu, một hệ đánh số, quyết định không
trùng số.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `python -m pytest -q` (mốc chuẩn đầu phiên) | 1.424 passed, 1 skipped |
| `python -m pytest -q` (cuối phiên) | **1.422 passed**, 1 skipped, 23 subtests, 238s |
| `python -m pytest tests/test_62_khoa_logic.py -q` | 11 passed |
| `python tools/scan_source_secrets.py` | **0 finding**, PASS |
| Kiểm chứng đường dẫn với `LTT_DATA_DIR` + đổi CWD | đúng như mong đợi |

**Vì sao tổng số test giảm 1424 → 1423 mà không mất test nào:**
`test_61::test_doc_has_no_invisible_control_characters` được sinh theo **số file
`.md` trong `docs/`**. Chuyển 12 file sang `_luutru/` → giảm 12 ca; thêm 11 ca
mới ở `test_62` → tổng giảm đúng 1. Đã kiểm chứng bằng cách đếm lại, không phải
suy đoán. Hệ quả chấp nhận được: tài liệu trong `_luutru/` không còn được quét
ký tự điều khiển nữa — chúng đã đóng băng, không ai đọc.

### Quyết định mới ghi trong phiên này

Q13 procrastinate · Q14 fastapi-users · Q15 sqladmin · Q16 SQLAlchemy+Alembic ·
Q17 chốt cận trên phiên bản · Q18 HTMX · Q19 Resend · Q20 Cloudflare Turnstile ·
Q21 Sentry · Q22 uỷ quyền subdomain `app` (có điều kiện chưa xác minh).
Chi tiết và lý do ở `QUYET_DINH_NEN_TANG.md`.

Tổng chi phí dịch vụ ngoài khi bắt đầu: **0 đồng/tháng** (đều dùng gói miễn phí).

### Hai test đã sửa — và vì sao không phải là làm yếu test đi

- `test_51_oauth_web.py::test_callback_paths_match_the_routes` đổi từ soi nội
  bộ router sang **thăm dò bằng HTTP**. Cách cũ vỡ khi nâng thư viện; cách mới
  chứng minh được đường dẫn **thực sự gọi tới được** — đúng thứ mà callback URL
  khai ở Meta/TikTok Portal cần.
- `test_45_deploy_scripts.py` đổi từ khoá cứng `127.0.0.1:8000` sang khoá bất
  biến "chỉ được proxy địa chỉ loopback". Khoá con số làm một lần đổi cổng hợp
  lệ trông giống lỗi bảo mật.

### Đo được về hạ tầng mạng — và một quyết định bị chặn

`nslookup` cho thấy `lttstudios.com` đang dùng nameserver của inet.vn
(`hoian/danang.vclouddns.com`), **không phải Cloudflare**. Cloudflare Tunnel
cần một CNAME trỏ tới `<tunnel-id>.cfargotunnel.com`, mà tên miền đó chỉ phân
giải được qua chính hệ thống Cloudflare — nên `setup/3-cloudflare.ps1` sẽ hỏng
ở khâu gần cuối, sau khi đã tải cloudflared, đăng nhập và tạo tunnel.

Chủ dự án chọn hướng **uỷ quyền riêng subdomain `app`** (Q22) để không đụng vào
trang giới thiệu đang chạy. Hướng này phụ thuộc một điều **tôi không xác minh
được từ đây**: gói miễn phí của Cloudflare có cho tạo zone cấp subdomain không.
Đã ghi rõ điều kiện đó ngay trong Q22 và tách thành hạng mục **H0.1** đứng
trước mọi việc khác, kèm hai đường lui nếu câu trả lời là không.

Cũng đo được: tên miền **không có bản ghi MX hay TXT nào** → thêm SPF/DKIM cho
Resend sẽ sạch, không đụng gì đang chạy.

### Còn tồn đọng

- Chưa dựng Cloudflare Tunnel trên máy này.
- `app.lttstudios.com` hiện vẫn trỏ vào máy chủ cũ chạy Caddy trực tiếp (đo
  được: `45.32.104.192`, không qua Cloudflare). Khi chuyển sang Tunnel phải
  quyết định số phận máy đó.
- Bộ test có gọi mạng thật ra `api.telegram.org` (in ra `[Telegram] HTTP 401`).
  Không chặn gì, nhưng test không nên phụ thuộc mạng.

### Việc tiếp theo

1. **Người dùng — H0.1:** kiểm tra trên bảng điều khiển Cloudflare xem gói miễn
   phí có cho tạo zone cấp subdomain `app.lttstudios.com` không. **Chưa biết kết
   quả thì chưa chạy `setup/3-cloudflare.ps1`.**
2. H1.1 — dựng PostgreSQL + SQLAlchemy + Alembic, migration đầu tiên. Không phụ
   thuộc việc 1, làm song song được.
3. Bổ sung cài Postgres vào `setup/2-cai-dat.ps1` và `pg_dump` vào `backup.ps1`
   **trong cùng lần đó**.

---

## Mẫu ghi — chép nguyên phần này lên đầu file cho mỗi phiên

```markdown
## YYYY-MM-DD — <tiêu đề ngắn>

- **Mục tiêu:**
- **Hạng mục:** H<x> — <đang làm / hoàn thành>
- **Trạng thái:** xong | dở | bị chặn

### Đã làm
<Cái gì và VÌ SAO. Nếu sửa lỗi, ghi lỗi đó gây hậu quả gì nếu không sửa.>

### Test đã chạy
| Lệnh | Kết quả |
|---|---|
| `python -m pytest -q` | ... |
| `python tools/scan_source_secrets.py` | ... |

<Phân biệt rõ: đã chạy / chưa chạy / pass / fail. Không bao giờ ghi "xong"
dựa trên kế hoạch hay số test thu thập được.>

### Quyết định mới
<Nếu có: số Q, và đã thêm vào QUYET_DINH_NEN_TANG.md chưa.
Nếu ĐỔI một quyết định cũ: đã đánh dấu ĐÃ THAY và dọn hết chỗ nói theo cái cũ
chưa — xem giao thức ở AGENTS.md mục 6.>

### Cách lùi lại
<Commit nào, hoặc xoá file nào.>

### Còn tồn đọng

### Việc tiếp theo
1.
2.
3.
```

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

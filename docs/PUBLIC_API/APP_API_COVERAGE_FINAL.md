# Coverage cuối cùng — 100% app, tool, model, chế độ chạy

**Đây là bảng chốt sau cùng của Public API V1.** Nó trả lời đúng hai câu hỏi,
và hai câu hỏi này kéo về hai phía ngược nhau:

- **Có bỏ sót năng lực nào không?** Một app không ai phân loại là một app không
  ai quyết định — và quyết định đó rồi sẽ do người kế tiếp sửa manifest đưa ra,
  một cách tình cờ.
- **Có publish nhầm cái gì không?** Một tool với ra được bằng API key thì tiêu
  credit thật, gọi provider thật, và **không rút lại được** khi đã có tích hợp
  phụ thuộc vào nó.

**Tài liệu này không tự chứng minh được.** `tests/test_212_coverage_certification.py`
đọc chính các bảng dưới đây như **dữ liệu**: thêm app/tool/model mà không có
dòng ở đây thì test đỏ; ghi ở đây một thứ không còn tồn tại cũng đỏ; và mỗi
operation đang mở phải **chạy thật từ ngoài vào** mới được coi là đã nghiệm thu.

Cơ sở: `platform_core.registry.discover()`, ngày 2026-08-22 —
**15 app, 22 ToolSpec, 4 alias model, 5 operation đang mở**.
*(`apps/vps` chưa được phân loại và chưa từng commit — xem ghi chú ở mục 1.)*

Phân loại ở mức *app* còn có một bánh cóc thứ hai độc lập ở
[`APP_DISPOSITION_V1.md`](APP_DISPOSITION_V1.md) + `tests/test_190`. File này đi
xuống một tầng: **từng tool, từng alias model, từng chế độ chạy**.

---

## 1. 17/17 app

Cột **Nhà mới** chỉ bắt buộc với `MIGRATE_*`: một năng lực bị chặn mà không nói
được nó sẽ về đâu thì chưa phải một kế hoạch, chỉ là một mục backlog đội lốt.

| App | Disposition | Nhà mới | Chế độ chạy | Lý do |
|---|---|---|---|---|
| `thumbnail` | EXPOSE_V1 | — | ASYNC_JOB | Giá phẳng theo số ảnh, chốt được trước khi chạy. Đã nghiệm thu E2E. |
| `anhnoibo` | EXPOSE_V1 | — | ASYNC_JOB | Bán model ảnh **nội bộ** trên máy B (H37/Q102). Giá chốt trước khi chạy nên hợp đồng job áp được: theo số ảnh, nhân 3 khi có ảnh tham chiếu vì đo thật là gấp ~3,3 lần thời gian máy. **Chưa nghiệm thu E2E** và chưa có trong công tắc người vận hành. |
| `taoanh` | EXPOSE_V1 | — | ASYNC_JOB | Giá theo alias model công khai; một ảnh tham chiếu đi qua upload. |
| `ltt_llm` | EXPOSE_V1 | — | ASYNC_JOB **và** SYNC | Bán model **ngôn ngữ nội bộ** trên máy B (H38/Q102), anh em với `anhnoibo`. Khác mọi app trên ở một điểm: **giá phụ thuộc số token RA, chỉ biết sau khi sinh xong**. Nên `credit_cost` là **trần ước cao** và nền tảng quyết toán theo số thật — `credit.quyet_toan` vốn không bao giờ thu quá phần đã giữ, nên lời hứa của quote (Q84) vẫn nguyên: khách **không bao giờ trả nhiều hơn** số đã báo. Đã nghiệm thu E2E trên phần cứng thật 22/08 (19/19), nhưng **chưa có trong công tắc người vận hành**. |
| `upscalevideo` | EXPOSE_V1 | — | ASYNC_JOB | Giá phẳng theo preset; đường GPU thật, có hàng đợi và trần đồng thời. |
| `prompt_ai_ommi` | EXPOSE_V1 | — | ASYNC_JOB | Giá theo `scene_count`; kết quả là dữ liệu nên trả thẳng trong `result`. |
| `taovideo` | MIGRATE_CAPABILITY_THEN_EXPOSE | `upscalevideo` (đã có hợp đồng video ổn định) | ASYNC_JOB | Tập giá trị hợp lệ của `resolution/duration/aspect_ratio` đổi theo model, publish hợp nhất sẽ để khách trả tiền cho tổ hợp provider từ chối. |
| `autosubvideo` | MIGRATE_CAPABILITY_THEN_EXPOSE | `upscalevideo` (cùng đường media đã chốt giá) | ASYNC_JOB | Giá theo `duration_s` do client khai và worker nâng hold khi đo thật — phá lời hứa của một quote đã ký (Q84). |
| `taoclipngan` | MIGRATE_CAPABILITY_THEN_EXPOSE | `upscalevideo` (đã có trần GPU và huỷ-hoàn) | ASYNC_JOB | Cùng nguyên nhân nâng hold, cộng thêm GPU nên trần đồng thời phải chốt trước. |
| `chataistudio` | DEFER | — | không có hợp đồng job | Không sinh Job: credit giữ theo id tin nhắn và chạy streaming qua sidecar, nên toàn bộ hợp đồng quote/settle không áp được. |
| `agent` | DEFER | — | không có hợp đồng job | Là runtime điều phối chứ không phải một tool; mở nó là mở cả một cơ chế chạy. |
| `mediatools` | INTERNAL_ONLY | — | ASYNC_JOB nội bộ | `surface=runtime` (Q72), và có đường nhận URL từ người gọi nên public là mở SSRF. |
| `qualitylab` | INTERNAL_ONLY | — | ASYNC_JOB nội bộ | `surface=admin`, chỉ dành cho người vận hành (Q83). |
| `demo` | INTERNAL_ONLY | — | ASYNC_JOB nội bộ | App thử hạ tầng; khách phải nhận 404 chứ không phải một tool tính tiền (Q71). |
| `socialbot` | INTERNAL_ONLY | — | không có hợp đồng job | Đã đóng băng (Q10/Q78); cần browser và OAuth, chưa có threat model cho tự động hoá credential. |
| `nexus` | DEFER | — | không có hợp đồng job | Không sinh Job và không có `ToolSpec`: đây là bề mặt **quản lý thiết bị** (ghép máy, thu hồi, nhật ký phiên) chứ không phải một tool tính tiền. Mở nó ra API nghĩa là công bố một hợp đồng về **danh tính thiết bị**, và điều đó phải chờ hạ tầng relay (D2) cùng legal review AGPL — xem `docs/nexus/`. Q93. |
| `kichban` | RETIRED_NO_EXPOSE | — | ASYNC_JOB nội bộ | App đã nghỉ (Q69); muốn năng lực sinh text thì migrate sang app được hỗ trợ chứ không hồi sinh app cũ. |

## 2. 22/22 ToolSpec

`customer_visible=True` **không** làm một tool public — đó là cờ palette của
Agent. `kichban` là bằng chứng sống, và có test riêng chốt điều đó.

| Tool | App | Trạng thái | Lý do |
|---|---|---|---|
| `image.thumbnail` | thumbnail | **EXPOSE_V1** | Giá phẳng 5/ảnh, chốt trước khi chạy; `model` bị ẩn vì giá không theo model. |
| `image.ltt` | anhnoibo | **EXPOSE_V1 — chưa mở** | Model nhà, không tốn tiền provider nhưng chiếm GPU nên giá tính theo **thời gian máy**. `image_keys` ẩn vì tầng API chỉ giải được một tệp cho một tham số; `model` ẩn vì mới có một model và giá không theo model. Vắng ở mục 4 là **đúng**: nó chưa chạy thật từ ngoài vào bao giờ. |
| `image.generate` | taoanh | **EXPOSE_V1** | Bốn alias model có giá riêng; `image_keys` ẩn vì mảng chưa được hỗ trợ. |
| `image.upscale` | upscalevideo | **EXPOSE_V1** | Giá phẳng 2/4 theo preset; ảnh vào qua upload đã kiểm magic-byte. |
| `text.prompt_package` | prompt_ai_ommi | **EXPOSE_V1** | Giá theo `scene_count`; `operation/model/resources` ẩn vì là đường định tuyến nội bộ. |
| `text.chat` | ltt_llm | **EXPOSE_V1 — chưa mở** | Hai alias `ltt_llm` / `ltt_llm_vision` cùng giá, khác ở chỗ bản vision nạp thêm bộ chiếu ảnh. Không ẩn tham số nào: hợp đồng đúng bằng hình dạng OpenAI mà khách đã biết. Alias **cố ý trùng tên với id nội bộ** — ta không hứa gì về model nền, nên đổi nó sau này không phá mã khách. Vắng ở mục 4 là **đúng**: chưa có lượt nào đi từ ngoài vào qua `/api/v1`. |
| `story.storyboard` | prompt_ai_ommi | **EXPOSE_V1** | Cùng hợp đồng, khác đầu ra; tách làm hai operation logic thay vì một cờ. |
| `image.batch_generate` | taoanh | ĐÓNG | Trùng năng lực với `image.generate` vì tham số `count` đã làm được việc đó. |
| `video.generate` | taovideo | ĐÓNG | Tập tuỳ chọn hợp lệ đổi theo model, chưa publish được một hợp đồng đúng. |
| `video.subtitle` | autosubvideo | ĐÓNG | Giá theo thời lượng khách khai, worker nâng hold nên quote đã ký không giữ được. |
| `video.short_clips` | taoclipngan | ĐÓNG | Cùng vấn đề nâng hold, thêm ràng buộc GPU chưa chốt được trần đồng thời. |
| `video.upscale` | upscalevideo | ĐÓNG | Video dài vượt trần 100 giây của Cloudflare, cần hợp đồng chạy khác. |
| `text.script` | kichban | ĐÓNG | Thuộc app đã nghỉ; muốn năng lực này thì migrate chứ không hồi sinh app cũ. |
| `text.generate` | kichban | ĐÓNG | Cùng app đã nghỉ; cờ `customer_visible` ở đây là palette Agent, không phải public. |
| `asset.image` | mediatools | ĐÓNG | Là bước đưa file vào workflow nội bộ, không phải một năng lực bán được. |
| `asset.images` | mediatools | ĐÓNG | Là bước đưa file vào workflow nội bộ, không phải một năng lực bán được. |
| `asset.video` | mediatools | ĐÓNG | Là bước đưa file vào workflow nội bộ, không phải một năng lực bán được. |
| `asset.audio` | mediatools | ĐÓNG | Là bước đưa file vào workflow nội bộ, không phải một năng lực bán được. |
| `audio.generate` | mediatools | ĐÓNG | App `surface=runtime` nên chưa có giá và hợp đồng cho khách gọi thẳng. |
| `video.extract_frames` | mediatools | ĐÓNG | Mảnh ghép FFmpeg nội bộ mà các app khác gọi, không có hợp đồng riêng. |
| `media.merge_image` | mediatools | ĐÓNG | Mảnh ghép FFmpeg nội bộ mà các app khác gọi, không có hợp đồng riêng. |
| `media.merge_video` | mediatools | ĐÓNG | Mảnh ghép FFmpeg nội bộ mà các app khác gọi, không có hợp đồng riêng. |
| `video.social_import` | mediatools | ĐÓNG | Nhận URL từ người gọi nên publish là mở thẳng một đường SSRF. |

## 3. 6/6 alias model

Alias tồn tại để **đổi nhà cung cấp không thành breaking change**. Có test quét
mọi surface khách đọc được: id thật của vendor lọt ra một chỗ là tích hợp bắt
đầu ghim vào nó, và alias hết còn là lớp đệm.

| Alias | Tool | Đằng sau | Trạng thái | Lý do |
|---|---|---|---|---|
| `standard` | `image.generate` | `gemini-2.5-flash-image` | công khai | Điểm khởi đầu cân bằng giữa chất lượng và giá. |
| `ltt_llm` | `text.chat` | `qwen38-api` | công khai | Model ngôn ngữ **chạy tại nhà** (máy B). Alias cố ý khác id nội bộ: ngày đổi GGUF bên dưới, mã của khách không phải sửa. |
| `ltt_llm_vision` | `text.chat` | `qwen38-vision` | công khai | Cùng model, nạp thêm bộ chiếu ảnh (+1,1 GB VRAM đo thật). |
| `standard-lite` | `image.generate` | `gemini-3.1-flash-lite-image` | công khai | Cùng giá với `standard`, đổi chi tiết lấy tốc độ. |
| `enhanced` | `image.generate` | `gemini-3.1-flash-image` | công khai | Bám prompt và chi tiết tốt hơn `standard`, giá cao hơn. |

Bốn tool còn lại **không** publish model: `image.thumbnail` ẩn `model` vì giá
không theo model, `image.upscale` chạy engine tại chỗ, và hai tool dữ liệu ẩn
`model` cùng `resources` vì đó là đường định tuyến nội bộ. Quy tắc chốt từ
wave 1 vẫn nguyên: **chỉ publish lựa chọn model ở nơi giá đi theo nó** — bắt
khách chọn một thứ không đổi giá và không đổi hợp đồng là bắt họ đoán.

> ⛔ **Alias `pro` ĐÓNG 2026-08-23 — lý do kinh tế, không phải kỹ thuật.**
> Giá vốn `gemini-3-pro-image` là **35,2 credit** (`platform_core/gia_von.json`);
> nền tảng bán **16** ở `taoanh` và **5** ở `thumbnail` ⇒ lỗ **1.924đ** và
> **3.024đ** mỗi ảnh. Chủ dự án chốt: giữ giá các bậc rẻ như chi phí thu hút
> khách, **đóng đúng bậc lỗ nặng nhất**. Model đặt `is_active=False` nên nó biến
> khỏi **cả** bộ chọn của giao diện web — đó mới là chỗ lỗ thật sự chạy.
> Xem `CHANGELOG.md` (BREAKING 2026-08-23) và `tests/test_261`.

## 4. Nghiệm thu từng operation

Cả 5 operation được **chạy thật từ ngoài vào** bằng **khoá test-mode**: quote →
submit → worker → poll → lấy artifact/result → usage → webhook. Nhờ EXT-12, một
lần nghiệm thu đầy đủ **không tốn credit, không cần provider, không cần GPU** —
kể cả với operation chạy GPU.

| Operation | Chế độ | Schema + mô tả từng tham số | Scope | Quote trước khi tính tiền | Idempotency | Upload | Artifact | Usage | Webhook | Playground | Sandbox | Admin |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `image.thumbnail` | ASYNC_JOB | ✅ | `jobs:create` | ✅ | ✅ | — | ✅ ảnh | ✅ | ✅ | ✅ | ✅ | ✅ |
| `image.generate` | ASYNC_JOB | ✅ | `jobs:create` | ✅ | ✅ | ✅ ảnh tham chiếu | ✅ ảnh | ✅ | ✅ | ✅ | ✅ | ✅ |
| `image.upscale` | ASYNC_JOB | ✅ | `jobs:create` | ✅ | ✅ | ✅ bắt buộc | ✅ ảnh | ✅ | ✅ | ✅ | ✅ | ✅ |
| `text.prompt_package` | ASYNC_JOB | ✅ | `jobs:create` | ✅ | ✅ | — | — dữ liệu | ✅ | ✅ | ✅ | ✅ | ✅ |
| `story.storyboard` | ASYNC_JOB | ✅ | `jobs:create` | ✅ | ✅ | — | — dữ liệu | ✅ | ✅ | ✅ | ✅ | ✅ |

Các cột không đánh theo tài liệu mà theo **kết quả chạy**: `test_212` gọi thật
từng ô. Ô "Playground/Admin/Sandbox" quan trọng hơn vẻ ngoài của nó — mỗi surface
do một đoạn code khác nhau dựng từ **cùng một catalog**, nên chúng là phép thử
xem catalog có thật sự là nguồn duy nhất hay không. Một tool đã publish mà vắng
mặt ở playground thì mới chỉ publish trên danh nghĩa.

**Sandbox lấy hình dạng từ hợp đồng, không viết tay theo tool.** Nhờ vậy một
operation mới được sandbox hỗ trợ ngay khi khai hợp đồng, và không có đường nào
để hình dạng sandbox lệch khỏi production.

Chính lần nghiệm thu này tìm ra một chỗ chế độ thử **chưa** làm được điều nó
hứa: luật "chưa giữ credit thì không được lưu file" — sinh ra để không ai biến
input của job thành kho lưu trữ miễn phí — chặn luôn mọi job chế độ thử, vì một
khoá thử **không bao giờ** giữ credit. Hệ quả: mọi tool nhận file đều không thử
được, mà `image.upscale` thì bắt buộc có file. Đã sửa ở gốc
(`upload_sessions.promote`), giữ nguyên luật cho job thật, và có test cho **cả
hai** chiều — vì nới một hàng rào mà không chốt lại phía bên kia là cách hàng
rào biến mất.

## 5. Chế độ chạy

Cả 5 operation đang mở đều là `ASYNC_JOB`, và hôm nay **không** có gì khác. Điều
đáng nói không phải con số mà là chỗ nó được canh: `execution_mode` là một khai
báo trong manifest, registry từ chối giá trị nền tảng chưa thi hành được, và
`test_212` chốt lại lần nữa.

Nghĩa là operation `SYNC`, `STREAM` hay `BATCH` đầu tiên **không thể lọt vào**:
nó phải khai, và lời khai đó sẽ bị từ chối cho tới khi nền tảng thật sự làm được
— chứ không phải chạy được rồi mới phát hiện hợp đồng job không mô tả nổi nó.
Đây đúng là chỗ `chataistudio` mắc: nó streaming, giữ credit theo id tin nhắn,
và **không** sinh Job — nên nó DEFER chứ không phải "chưa kịp làm".

## 6. Không có gì lọt ra ngoài ý muốn

Ba cổng độc lập, đã có từ V1 và vẫn nguyên:

1. **disposition của app** — `catalog.app_may_be_public()` chặn theo lifecycle và
   surface, không phụ thuộc cờ nào trong manifest;
2. **khai báo của tool** — `api_exposed` cộng một hợp đồng công khai đủ;
3. **công tắc của người vận hành** — `LTT_PUBLIC_API_TOOLS`, rồi `allowed_tools`
   của từng khoá.

`test_212` mở công tắc **rộng hết mức hợp lệ** rồi mới quét — vì một vòng quét
trên catalog rỗng thì luôn xanh và chẳng chứng minh gì. Với catalog rộng nhất có
thể, nó kiểm:

- 16 tool đóng **không xuất hiện** ở OpenAPI, `/capabilities`, trang docs,
  playground, trang giá, trang status, `/tools`, `/models`;
- gọi thẳng tên một tool đóng thì nhận **404**, không phải 403 — tên đó không
  tồn tại với khách;
- **không id vendor nào** lọt ra bất kỳ surface nào khách đọc được;
- mọi alias model publish ra đều thuộc về một tool đang publish.

## 7. Việc đã ghi nợ, có chủ

| Việc | Chặn cái gì | Sửa ở đâu |
|---|---|---|
| Phân loại `apps/vps` | `test_190` + `test_212` (cả hai đỏ vì nó) | App **đang được xây dở ở một dự án/phiên khác** nên cố ý chưa commit (chủ dự án xác nhận 22/08). Nó khai **không ToolSpec nào** và `app_may_be_public()` trả `False` ⇒ **không lọt ra API được**. Phân loại nó là việc của phiên đang làm `vps`, làm khi app đó commit. Tới lúc đó, hai test này còn đỏ đúng một test mỗi tệp — **đã biết, không phải hồi quy**. |
| Nghiệm thu E2E `image.ltt` + chốt giá | mở `image.ltt` cho khách | Chạy thật một job qua `/api/v1` khi model qua cổng chất lượng, rồi điền một dòng ở mục 4 và thay giá tạm bằng số đo thật. |


| Việc | Chặn cái gì | Sửa ở đâu |
|---|---|---|
| Đo thời lượng phía server lúc báo giá | 3 tool video (`video.subtitle`, `video.short_clips`, `video.upscale`) | Một chỗ: đọc metadata từ file đã upload rồi khoá giá. Sửa một chỗ mở được cả ba. |
| Hợp đồng tuỳ chọn theo model | `video.generate` | Cho `models` khai luôn tập giá trị hợp lệ riêng, thay vì publish hợp nhất. |
| Hợp đồng streaming | `chataistudio` | Cần một hợp đồng chạy mới, không phải một tool mới. |
| Ranh giới chi phí cho runtime điều phối | `agent` | Cần sandbox và trần chi phí riêng trước khi bàn tới hợp đồng. |

Ba dòng đầu **cùng một hình dạng**: hợp đồng job hiện tại giả định giá chốt được
trước khi chạy. Chỗ nào giả định đó sai thì năng lực bị chặn — và chặn như vậy
là **đúng**, vì cái mất khi sai không phải một job hỏng mà là một lời hứa về giá
đã ký với khách.

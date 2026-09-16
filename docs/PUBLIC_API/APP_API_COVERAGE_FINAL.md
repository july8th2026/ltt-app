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

## 1. 20/20 app

Cột **Nhà mới** chỉ bắt buộc với `MIGRATE_*`: một năng lực bị chặn mà không nói
được nó sẽ về đâu thì chưa phải một kế hoạch, chỉ là một mục backlog đội lốt.

| App | Disposition | Nhà mới | Chế độ chạy | Lý do |
|---|---|---|---|---|
| `thumbnail` | EXPOSE_V1 | — | ASYNC_JOB | Giá phẳng theo số ảnh, chốt được trước khi chạy. Đã nghiệm thu E2E. |
| `anhnoibo` | EXPOSE_V1 | — | ASYNC_JOB | Bán model ảnh **nội bộ** trên máy B (H37/Q102). Giá chốt trước khi chạy nên hợp đồng job áp được: theo số ảnh, nhân 3 khi có ảnh tham chiếu vì đo thật là gấp ~3,3 lần thời gian máy. **Chưa nghiệm thu E2E** và chưa có trong công tắc người vận hành. Từ H37/L1 (24/08) giá **quyết toán theo số ảnh thật sự sinh ra được**, không theo số đã xin — `credit_cost` do handler báo về, giá ở `apps/anhnoibo/gia.py` (phiên bản `ltt-image-2026-08-24`) và công bố ở `/gia-api`. |
| `taoanh` | EXPOSE_V1 | — | ASYNC_JOB | Giá theo alias model công khai; một ảnh tham chiếu đi qua upload. |
| `ltt_llm` | EXPOSE_V1 | — | ASYNC_JOB **và** SYNC | Bán model **ngôn ngữ nội bộ** trên máy B (H38/Q102), anh em với `anhnoibo`. Khác mọi app trên ở một điểm: **giá phụ thuộc số token RA, chỉ biết sau khi sinh xong**. Nên `credit_cost` là **trần ước cao** và nền tảng quyết toán theo số thật — `credit.quyet_toan` vốn không bao giờ thu quá phần đã giữ, nên lời hứa của quote (Q84) vẫn nguyên: khách **không bao giờ trả nhiều hơn** số đã báo. Đã nghiệm thu E2E trên phần cứng thật 22/08 (19/19), nhưng **chưa có trong công tắc người vận hành**. |
| `ltt_voice` | EXPOSE_V1 | — | ASYNC_JOB | Bán model **giọng nói nội bộ**, và khác hai app model nhà ở trên đúng một chỗ đáng kể: engine chạy **trên máy A**, sau loopback `127.0.0.1:8120`, không phải trên máy B (Q117). Nên không có provider, không có khoá trong `api_pool` — token sidecar đi đúng đường `LTT_CODEX_SIDECAR_TOKEN` đã chạy thật. Giá theo **giây tiếng nói sinh ra thật** (đo bằng `ffprobe`), giữ chỗ theo ký tự đã chuẩn hoá; `credit_cost` do handler báo về, giá ở `apps/ltt_voice/gia.py` (phiên bản `ltt-voice-2026-08-30a`). **Chưa nghiệm thu E2E qua Cloudflare** (xem `speech.ltt` ở mục 2: **Mở 01/09/2026**). **D007 (11/09):** `speech.ltt` từ chối lỗi sở hữu giọng / lệch làn ngôn ngữ NGAY tại `POST /quotes` và `POST /jobs` qua `ToolSpec.kiem_truoc` (`apps.ltt_voice.kiem_truoc_api:kiem`), TRƯỚC khi có giá và trước khi giữ tiền. |
| `upscalevideo` | EXPOSE_V1 | — | ASYNC_JOB | Giá phẳng theo preset; đường GPU thật, có hàng đợi và trần đồng thời. |
| `prompt_ai_ommi` | EXPOSE_V1 | — | ASYNC_JOB | Giá theo `scene_count`; kết quả là dữ liệu nên trả thẳng trong `result`. |
| `taovideo` | **EXPOSE_V1** *(30/08, was MIGRATE_CAPABILITY_THEN_EXPOSE)* | `upscalevideo` (đã có hợp đồng video ổn định) | ASYNC_JOB | ~~Tập giá trị hợp lệ của `resolution/duration/aspect_ratio` đổi theo model, publish hợp nhất sẽ để khách trả tiền cho tổ hợp provider từ chối.~~ Lý do đó **vẫn đúng nguyên** — thứ đổi là ta thôi phải publish hợp nhất. Mỗi model công bố `constraints` của riêng nó, và tổ hợp sai bị chặn **trước** `price()`. Xem dòng `video.generate` ở mục dưới. |
| `autosubvideo` | EXPOSE_V1 | — | ASYNC_JOB | ~~Giá theo `duration_s` do client khai và worker nâng hold khi đo thật — phá lời hứa của một quote đã ký (Q84).~~ **MỞ 2026-08-29 (H35.10a+b).** Hai việc, không một: (a) máy chủ **đo** thời lượng từ chính tệp đã tải lên trước khi tính giá (`measured_from` trong manifest), nên `duration_s` vào `hidden` và khách không gửi nó được nữa; (b) giữ chỗ của job đến từ API bị **niêm phong** ở con số đã ký — worker đòi nâng thì nền tảng **hấp thụ** phần chênh, không thu thêm và cũng không giết job. Chỉ (a) là chưa đủ: worker chạy ffprobe riêng và `math.ceil` có thể lệch một credit. |
| `taoclipngan` | MIGRATE_CAPABILITY_THEN_EXPOSE | `upscalevideo` (đã có trần GPU và huỷ-hoàn) | ASYNC_JOB | Cùng nguyên nhân nâng hold, cộng thêm GPU nên trần đồng thời phải chốt trước. |
| `agent` | DEFER | — | không có hợp đồng job | Là runtime điều phối chứ không phải một tool; mở nó là mở cả một cơ chế chạy. |
| `qualitylab` | INTERNAL_ONLY | — | ASYNC_JOB nội bộ | `surface=admin`, chỉ dành cho người vận hành (Q83). |
| `nexus` | DEFER | — | không có hợp đồng job | Không sinh Job và không có `ToolSpec`: đây là bề mặt **quản lý thiết bị** (ghép máy, thu hồi, nhật ký phiên) chứ không phải một tool tính tiền. Mở nó ra API nghĩa là công bố một hợp đồng về **danh tính thiết bị**, và điều đó phải chờ hạ tầng relay (D2) cùng legal review AGPL — xem `docs/nexus/`. Q93. |
| `chatltt` | DEFER | — | có **một** hợp đồng job, không bán | Sản phẩm hội thoại trên ba model nhà (H43). ⚠️ **CẬP NHẬT 06/09 (H44 B1a).** Câu *"không khai `ToolSpec` nào"* ở đây đã **hết đúng**: `chatltt.trich_tep` được khai để `runtime_noi_bo.bao_gia()` tra được giá — thiếu nó thì **không hiện được giá trước khi khách bấm**, điều P06 §7 đã chốt. Nhưng lý do DEFER thì **không đổi**, và đó mới là phần quan trọng: nó là nó là **khách hàng nội bộ** của `text.chat` / `image.ltt` / `speech.ltt` qua `platform_core/runtime_noi_bo`, không phải một năng lực mới để bán. Mở nó ra `/api/v1` sẽ là bán lại đúng ba tool đã bán, qua một hợp đồng thứ hai — và hợp đồng thứ hai là chỗ hai bảng giá bắt đầu lệch nhau. App còn **TẮT** (`enabled=False`) tới khi H43 Phase 13 PASS. |
| `lttvideo` | INTERNAL_ONLY | — | không khai `ToolSpec` nào | Video AI chạy bằng **WanGP** trên C-CLOUD (V2.1). Lý do đóng ở đây **không phải kế hoạch mà là GIẤY PHÉP**: `WanGP Community License 2.0` §5.2(g) cấm *"exposing the Software to customers or end users as a paid feature, add-on, or monetized backend component"* nếu không có giấy phép thương mại riêng — liên hệ cấp phép ghi ở §5.4 của chính giấy phép. ⇒ Mở tool ở đây là một quyết định **pháp lý**, chưa được đưa ra. Bằng chứng đầy đủ: `docs/VIDEO_AI_V2/P01_UPSTREAM_PIN.md` mục 2. |
| `vps` | WEB_ONLY · WONT_BUILD_PUBLIC_API | — | không có hợp đồng job | Q124/D01 khóa VPS là tính năng web first-party: không ToolSpec, `/api/v1/vps`, API-key provisioning, reseller API hay SDK công khai. |

| `auto_scan_video` | DEFER | — | chuỗi 11 giai đoạn, không phải một lượt gọi | **Lồng tiếng Việt cho video** (pha 00–14). Một lần chạy là **mười một giai đoạn**, mỗi giai đoạn một job riêng, bốn trong số đó chạy lại độc lập được. Ép vào `ToolSpec` một-vào-một-ra thì hoặc mất khả năng chạy lại một giai đoạn, hoặc bịa ra một hợp đồng mà chuỗi thật không có. ⛔ App còn `enabled=False` và `surface="runtime"` (chưa có `routes.py`) — chưa mở cho khách trên web, nên bàn mở qua API là bàn trước một bước. |
| `asv_media` | DEFER | — | không phải app bán được | Vỏ thi hành làn `ffmpeg` của `auto_scan_video`. Khai `catalog_parent`, không `ToolSpec`, không thẻ catalog. Tồn tại vì quyền nhặt job lọc theo **APP** chứ không theo `job_type` (`platform_core/jobs.py:158-164`). |
| `asv_gpu` | DEFER | — | không phải app bán được | Như trên, làn `gpu`. |
| `asv_voice` | DEFER | — | không phải app bán được | Như trên, làn `voice`. |

| `transcript` | **DEFER** | — | ASYNC_JOB | **Phiên âm có dòng thời gian** (Phase 08). DEFER vì chưa nghiệm thu E2E qua worker và chưa kiểm trên URL công khai. Đã đối chiếu parity trên **1.932 lượt job thật** của bot legacy (`docs/migration/workflow_apps/30_...`): bản chuyển 95,50 % so với 95,76 % của **chính engine gốc** đo trên đầu ra của nó — engine gọi `random.uniform` có chủ ý nên trùng khớp từng byte là bất khả. |
| `audio_pause` | **DEFER** | — | ASYNC_JOB | **Chèn khoảng lặng theo lời** (Phase 09). DEFER cùng lý do với `transcript`, cộng một điều nặng hơn: bot gốc **không để lại hiện vật nào** trên máy (workdir rỗng, kết quả nằm trên Drive), nên mệnh đề *"kết quả như bot đã giao"* hiện **không kiểm được** — chỉ đối chứng vi sai với hàm gốc là khả dĩ. |
| `prompt_canh` | **DEFER** | — | ASYNC_JOB | **Kịch bản → prompt cảnh** (Phase 10). DEFER vì **hình dạng giá**: nó thu tiền theo **từng lượt gọi model** qua `runtime_noi_bo`, nên `credit_cost` ở tầng job là **0 có chủ đích**. Hợp đồng quote/settle một-vào-một-ra không mô tả được giá của nó — mở ra `/api/v1` là công bố một hợp đồng giá mà đường thật không đi theo. |
| `video_assembly` | **DEFER** | — | ASYNC_JOB | **Dựng video từ clip** (Phase 11). DEFER vì nó là một **chuỗi nhiều giai đoạn** trên GPU (STT, khớp clip, tách nhạc, trộn tiếng, cháy phụ đề), giống `auto_scan_video` ở trên: ép vào một `ToolSpec` một-vào-một-ra thì mất khả năng chạy lại một giai đoạn. Và `vram_min_mb` **chưa đo thật**, nên scheduler chưa xếp chỗ đúng được. |
| `lttcode` | INTERNAL_ONLY | — | không có hợp đồng job | Kênh phát hành + đăng nhập + tìm web của **ứng dụng desktop LTTCODE** (kho `D:\LTTCODEAPP`). Không sinh Job, không khai `ToolSpec`: LTTCODE gọi `/api/v1` bằng khoá `ltt_sk_` của chính người dùng như mọi client khác, nên mở app này ra API là công bố lại một hợp đồng đã có. `surface="runtime"`, `public=False`. |

## 2. 28/28 ToolSpec

`customer_visible=True` **không** làm một tool public — đó là cờ palette của
Agent. `kichban` (gỡ 2026-08-25, Q109) từng là bằng chứng sống của điều đó.

| Tool | App | Trạng thái | Lý do |
|---|---|---|---|
| `image.thumbnail` | thumbnail | **EXPOSE_V1** | Giá phẳng 5/ảnh, chốt trước khi chạy; `model` bị ẩn vì giá không theo model. |
| `chatltt.trich_tep` | chatltt | **DEFER — không bán** | Trích văn bản từ tài liệu khách đính vào **hội thoại của chính họ** (H44 P06). Khai `ToolSpec` **chỉ** để `runtime_noi_bo.bao_gia()` tra được giá — thiếu nó thì không hiện được giá **trước** khi khách bấm, điều P06 §7 đã chốt. ⛔ `customer_visible=False` — và nó là tool **ĐẦU TIÊN trong kho** đặt cờ ấy, tức cổng thứ nhất chưa từng chịu lực trước hôm nay. Đã đo trước khi dựa vào: `frontend/agent-canvas/src/presentationAdapter.ts` lọc `customer_visible!==false` ở hai chỗ, nên nó không hiện trong palette Agent. ⛔ `api_exposed=False`: bán nó ra `/api/v1` là bán một thao tác chỉ có nghĩa **bên trong một hội thoại** — không có hội thoại thì không có phạm vi, và phạm vi là ranh giới quyền. Giá còn **TẠM** (`gia_trich.CHU_DU_AN_DA_CHOT = False`), và cả nhóm nằm sau cờ `LTT_CHATLTT_V3_FILES` **mặc định tắt**. |
| `chatltt.nghien_cuu` | chatltt | **DEFER — không bán** | Vòng nghiên cứu trên **tài liệu khách đã đính vào chính hội thoại đó** (H44 B6). ⛔ Nền tảng này **không có khả năng tìm web** — đo 07/09: không một tệp nào khai `tavily`/`serper`/`brave`/`searx`, và provider ngoài duy nhất trong `platform_core` là `gemini`. Mở một `web.tim` là một **quyết định thương mại**, cùng hạng với giá trích, nên nó không nằm trong hạng mục kỹ thuật này. ⛔ `customer_visible=False` và `api_exposed=False`: cùng lý lẽ `chatltt.trich_tep` — thao tác này chỉ có nghĩa **bên trong một hội thoại**, và không có hội thoại thì không có phạm vi, mà phạm vi là ranh giới quyền (`params_schema.conversation_id` khai `required`). 🔴 Giá của job là **0 có chủ đích**, không phải chưa chốt: mọi credit của nó chảy qua `runtime_noi_bo` theo từng lượt model (giữ rồi hoàn theo token thật), nên một số dương ở tầng job là **thu hai lần**. Cả nhóm nằm sau cờ `LTT_CHATLTT_V3_RESEARCH` **mặc định tắt**. |
| `image.ltt` | anhnoibo | **EXPOSE_V1 — MỞ 24/08** | Model nhà, không tốn tiền provider nhưng chiếm GPU nên giá tính theo **thời gian máy**. `image_keys` ẩn vì tầng API chỉ giải được một tệp cho một tham số; `model` ẩn vì mới có một model và giá không theo model. ~~Vắng ở mục 4 là **đúng**: nó chưa chạy thật từ ngoài vào bao giờ.~~ **Đã có mặt ở mục 4 từ 24/08** (tiền thật), và **25/08 thêm một lượt từ MÁY KHÁC** qua Cloudflare bằng thư viện chuẩn — lượt đó tìm ra lỗi tài liệu `outputs[]`. H37/L1–L7 (24/08) đã đóng các chỗ lệch so với khuôn bán model nhà (`docs/KHUON_BAN_MODEL_NHA.md`): quyết toán theo ảnh thật, thăm dò sống/chết + GPU cho cổng render, giá công bố. **Bốn cổng đã mở cùng ngày** (D-053 + G10). Giá **hạ một phần ba**: 5 → 3 credit/ảnh, tham chiếu 15 → 9. ⛔ Mở **không phải** vì nó đẹp hơn — G6b đã chấm và nhà thua rõ (D-045); nó là một mặt hàng riêng, rẻ hơn. Việc có chữ tiếng Việt vẫn đi `image.thumbnail` (D-048). |
| `speech.ltt` | ltt_voice | **EXPOSE_V1 — MỞ 01/09** | Văn bản thành giọng nói. Giá theo **giây tiếng thật**, nên `credit_cost` là trần ước cao và nền tảng quyết toán theo số đo — cùng hình dạng `text.chat`. Hai tham số công khai: `text` và `voice_id` (mã giọng **ổn định qua mọi lần nâng engine**; biểu diễn engine là hai mảng numpy của nền tảng, không bao giờ ra ngoài). ⛔ **Tham số sinh mẫu `temperature`/`top_k`/`top_p` cố ý KHÔNG có trong hợp đồng** (Q119): cache CUDA graph của upstream khoá theo `(batch, temperature, top_k, top_p)` nên mỗi tổ hợp mới tốn một graph trên card, và temperature cao làm lệch tông giữa các đoạn (upstream #173). Trần **1.500 ký tự** mỗi lượt là trần **chất lượng** chứ không phải hiệu năng — đo 30/08 cho thấy 3.000 ký tự vẫn sinh được trong 17,6 giây, nhưng upstream #168 báo giọng trôi vùng miền từ khoảng ngưỡng đó.  ✅ **MỞ 01/09/2026** sau khi đóng V7 (giá vốn đo thật: 2,83 mcredit/giây tiếng ở bậc đắt nhất, bán 200 — biên hơn 98%), V9 (trôi tông **đã đo và không có**, ba lượt độc lập trên bài 12 đoạn; nộp trùng và chạy lại đã có bánh cóc) và V10 (**cổng chất lượng có baseline ghim theo phiên bản** — đổi `tham_so.py` là `test_376` đỏ, và cách duy nhất làm nó xanh là đo lại). ⚠️ Mở cửa này lộ ra **hai lỗi của chính nền tảng**, cả hai đã sửa cùng ngày: chế độ thử trả **PNG cho mọi loại** vì `catalog` làm phẳng `audio`/`video`/`image` thành một `artifact` duy nhất (vô hình suốt vì mọi tool mở trước đó đều trả ảnh — và điều đó nghĩa là `video.upscale` cùng `video.subtitle` **đã phát PNG trong sandbox từ trước**, xem `CHUA_CO_MAU`), và cửa văn bản dài áp trần 8 đoạn của một lượt gộp lô lên chính người gọi. |
| `image.generate` | taoanh | **EXPOSE_V1** | Bốn alias model có giá riêng; `image_keys` ẩn vì mảng chưa được hỗ trợ. |
| `image.upscale` | upscalevideo | **EXPOSE_V1** | Giá phẳng 2/4 theo preset; ảnh vào qua upload đã kiểm magic-byte. |
| `text.prompt_package` | prompt_ai_ommi | **EXPOSE_V1** | Giá theo `scene_count`; `operation/model/resources` ẩn vì là đường định tuyến nội bộ. |
| `text.chat` | ltt_llm | **EXPOSE_V1 — MỞ** | Hai alias `ltt-3.8` / `ltt-3.5`, hai model trên hai card, **hai bảng giá**. ~~Không ẩn tham số nào: hợp đồng đúng bằng hình dạng OpenAI mà khách đã biết.~~ 🔴 **CÂU ẤY ĐÃ SAI, VÀ SAI THEO CÁCH TỆ NHẤT — sửa 14/09/2026.** Hợp đồng chỉ khai sáu tham số, còn `features.kiem_tham_so` là một **danh sách trắng**: mọi thứ ngoài danh sách bị vứt **im lặng** và khách vẫn nhận **200**. Đo trên chính production: cùng một `response_format: json_schema` bắt buộc `ten/tuoi/thanh_pho`, **máy B trả đúng khuôn** `{"ten":…,"tuoi":34,"thanh_pho":"Ha Noi"}`, còn **qua máy A** thì khuôn bị bỏ qua và JSON bị bọc trong ```` ```json ````. Engine làm được; nền tảng ném đi rồi báo thành công. ⇒ Mở thêm **sáu** tham số đã kiểm: `response_format` (json_object + json_schema, ràng buộc bằng ngữ pháp), `tool_choice`, `parallel_tool_calls`, `top_p`, `seed`, `stop`. ⛔ **Không** mở `grammar` thô (BNF): trường tự do đi thẳng tới bộ giải mã, không cổng nào kiểm được — đúng lý lẽ đã dùng để hoãn `refs` của `video.generate`. ⛔ **Không** mở `n`: nó nhân chi phí sinh lên n lần trong khi báo giá và giữ chỗ đều tính cho một chuỗi. ⭐ Bản vá thật không phải sáu dòng mã mà là `tests/test_1255`: nó lấy danh sách từ **chính `params_schema`** rồi đòi từng khoá phải sống sót qua `kiem_tham_so` **và** nằm trong `THAM_SO_CHUYEN_THANG` — thêm khoá vào hợp đồng mà quên đẩy nó đi thì gate đỏ, không cần ai nhớ viết test. 🔴 CẮT 11/09/2026 (D02): tên cũ `ltt_llm` / `ltt_llm_vision` trùng hệt slug app nên lớp đệm alias chỉ tồn tại trên giấy; nay không tên công khai nào trùng slug hay id nội bộ, và tên cũ trả `model_not_found` ở mọi cửa. ~~Vắng ở mục 4 là **đúng**: chưa có lượt nào đi từ ngoài vào.~~ **Đã mở và đã chạy thật**: Codex CLI, Claude Code CLI, hai tiện ích VS Code và Claude Desktop đều đã gọi qua `/api/v1` và bị thu tiền đúng (24–25/08). |
| `story.storyboard` | prompt_ai_ommi | **EXPOSE_V1** | Cùng hợp đồng, khác đầu ra; tách làm hai operation logic thay vì một cờ. |
| `image.batch_generate` | taoanh | ĐÓNG | Trùng năng lực với `image.generate` vì tham số `count` đã làm được việc đó. |
| `video.generate` | taovideo | **EXPOSE_V1 — HỢP ĐỒNG ĐÓNG BĂNG 30/08, operator CHƯA BẬT** | ~~Tập tuỳ chọn hợp lệ đổi theo model, chưa publish được một hợp đồng đúng.~~ Đóng bằng cách **giải**, không phải hạ tiêu chuẩn: mỗi model công bố `constraints` của **riêng nó** qua `PublicModel.constraints` — ô đã có sẵn trong `catalog.py` mà chưa app nào dùng. Hợp nhất sẽ nói `seedance-2.0-mini` + `4k` là hợp lệ, rồi khách trả tiền để bị từ chối. Tổ hợp sai nay bị chặn ở `invocation._check_model_constraints`, chạy **trước** `price()` ⇒ trước báo giá, trước giữ chỗ, trước khi chạm nhà cung cấp. Hợp đồng **sinh từ** `apps/taovideo/models.py`, không chép. ~~Bốn ref hoãn có ghi vì chưa chứng minh ownership.~~ **30/08: mở ba** — `image_keys`, `video_key`, `audio_key`. Bằng chứng ownership nay **là đường mã**: mọi id qua `resolve_upload_reference`, đòi đủ hai cổng (chủ sở hữu + danh sách trắng hợp đồng đầu ra), và **mảng không phải đường vòng** — mỗi phần tử qua đúng hàm đó, kèm trần 8. Việc này mở khoá một giới hạn của **nền tảng** chứ không của app: `image_keys` bị ẩn ở **ba** tool vì *"tầng API chỉ giải được một tệp cho một tham số"*. ⛔ `refs` **vẫn hoãn**, lý do khác hẳn: nó là `json`, không cổng nào kiểm được — mở nó là mở một trường tự do đi thẳng tới nhà cung cấp. ⚠️ Chưa nghiệm thu bằng credential thật — `BLOCKED_EXTERNAL`. |
| `video.subtitle` | autosubvideo | **EXPOSE_V1 — MỞ 29/08** | ~~Giá theo thời lượng khách khai, worker nâng hold nên quote đã ký không giữ được.~~ Máy chủ đo thời lượng lúc báo giá và giữ chỗ bị niêm phong ở con số đã ký (H35.10a+b). Khách phải tự mang transcript tới — tool này **không** phiên âm hộ, và mô tả công khai nói thẳng điều đó. `duration_s` ẩn vì khách không khai nó nữa. |
| `video.short_clips` | taoclipngan | ĐÓNG | Cùng vấn đề nâng hold, thêm ràng buộc GPU chưa chốt được trần đồng thời. |
| `video.upscale` | upscalevideo | **EXPOSE_V1 — MỞ 29/08** | ~~Video dài vượt trần 100 giây của Cloudflare, cần hợp đồng chạy khác.~~ ⚠️ Lý do cũ **nói sai vấn đề**: trần 100 giây của Cloudflare áp cho một request đồng bộ, còn tool này là `ASYNC_JOB` — khách nộp job rồi hỏi lại, đúng thứ hợp đồng job sinh ra để làm. Vấn đề thật là Q84 (giá theo `duration_s` khách khai + worker nâng hold), và nó đã đóng bằng H35.10a+b. `duration_s` ẩn; `preview` cho khách thử 8 giây đầu trước khi trả tiền cho cả video. |

| `transcript.run` | transcript | **DEFER — chưa bán** | Một tệp âm thanh vào, một dòng thời gian ra. `api_exposed=False`, disposition DEFER. |
| `audio_pause.run` | audio_pause | **DEFER — chưa bán** | Bản thu + danh sách mốc vào, bản thu đã chèn lặng ra. `api_exposed=False`, disposition DEFER. |
| `prompt_canh.run` | prompt_canh | **DEFER — chưa bán** | Kịch bản vào, prompt JSON từng cảnh ra. `credit_cost=0` **có chủ đích** — tiền thu ở tầng `runtime_noi_bo` theo từng lượt gọi model, nên thu ở tầng job nữa là thu **hai lần**. `api_exposed=False`, disposition DEFER. |
| `video_assembly.run` | video_assembly | **DEFER — chưa bán** | Clip thô + nhạc vào, một video hoàn chỉnh ra. `api_exposed=False`, disposition DEFER. |

## 3. 6/6 alias model

Alias tồn tại để **đổi nhà cung cấp không thành breaking change**. Có test quét
mọi surface khách đọc được: id thật của vendor lọt ra một chỗ là tích hợp bắt
đầu ghim vào nó, và alias hết còn là lớp đệm.


⛔ **`image.generate` thôi công bố bí danh model từ 09/09/2026.** Ba bí danh
`standard` · `standard-lite` · `enhanced` trỏ tới ba model Gemini và tồn tại
được nhờ đúng một điều kiện: **giá đi theo lựa chọn** (5 · 5 · 8 credit/ảnh).
Tool nay chạy một model nội bộ duy nhất, giá theo số ảnh — nên lựa chọn không
mua được gì, và công bố nó là bán ba tên cho một món. Xem `CHANGELOG.md`
mục **BREAKING 2026-09-09**.

| Alias | Tool | Đằng sau | Trạng thái | Lý do |
|---|---|---|---|---|
| `ltt-3.8` | `text.chat` | `qwen38-api` | công khai | Model ngôn ngữ **chạy tại nhà** (máy B, RTX 3090). Alias cố ý khác id nội bộ **và khác slug app**: ngày đổi GGUF bên dưới, mã của khách không phải sửa. |
| `ltt-3.5` | `text.chat` | `qwen35-api` | công khai | Model thứ hai, chạy trên card 5060 Ti: nhanh hơn, rẻ hơn nhiều, cùng khuôn tin nhắn, cũng đọc ảnh. |
| `seedance-2.0-mini` | `video.generate` | `dreamina-seedance-2-0-mini-260615` | công khai | Rẻ nhất. **480p/720p** — không có 1080p/4k. Alias đầu tiên của nền tảng công bố `constraints` riêng. |
| `seedance-2.0` | `video.generate` | `dreamina-seedance-2-0-260128` | công khai | Bản đầy đủ: thêm **1080p và 4k**. Đây chính là lý do không publish được một tập hợp nhất — hợp nhất sẽ nói với khách rằng `mini` + `4k` hợp lệ. |
| `seedance-2.0-fast` | `video.generate` | `dreamina-seedance-2-0-fast-260128` | công khai | Đổi chi tiết lấy tốc độ; cùng tập độ phân giải với `mini`. |

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

⭐ **`image.ltt` là dòng DUY NHẤT ở bảng này được nghiệm thu bằng TIỀN THẬT**, 24/08 sau khi deploy. Cố ý: model nhà chạy trên máy B, và test-mode (EXT-12) trả kết quả giả nên **không** chạm tới GPU — tức nó chứng minh được đường ống HTTP nhưng **không** chứng minh được job thật vẽ ra ảnh thật và thu đúng tiền.

**Bổ sung 25/08 — một phép thử KHÁC LOẠI, và nó tìm ra lỗi.**
`nghiem_thu_anh_e2e.py` do ta viết, chạy trên **máy A**, và biết trước hình dạng
phản hồi. Ngày 25/08 chạy `tools/khach_gia_lap_anh.py` từ **một máy khác**
(VM Windows sạch), qua Cloudflare, bằng **thư viện chuẩn**, chỉ biết những gì
tài liệu nói: job `fbefed09`, **138 giây**, tải **5.583.155 byte**, đối soát tay
`hold −3 → settle giữ 3 / thu 3 / variance 0`.

⛔ **Và nó dừng lại ở bước lấy ảnh** — vì tài liệu nói artifact nằm trong
`result`, còn thật ra chúng ở `outputs[]`. Job xong, tiền đã thu, ảnh đã có, mà
mã của khách không lấy được. Đã sửa cùng ngày.

⭐ Bài học: hai phép thử **cùng gọi một API và cùng xanh** vẫn có thể chứng minh
hai điều khác nhau. Cái do ta viết chứng minh **máy chủ chạy đúng**; cái chỉ đọc
tài liệu chứng minh **khách dùng được**.

Số đo, ba lượt liên tiếp qua `https://app.lttstudios.com/api/v1` (`tools/nghiem_thu_anh_e2e.py`):

```
GET  /tools            -> 200, thay ['image.ltt']
POST /quotes           -> 200, credit = 3
POST /jobs             -> 202, chay 120 giay tren may B
GET  /jobs/{id}        -> succeeded, credit {held: 3, charged: 3}
GET  /artifacts/{id}/content -> 200, 5.519.918 byte, dung chu ky PNG
so du 30 -> 27 -> 24 -> 21   (moi luot dung 3)
```

⚠️ Bước tải ảnh về (`/artifacts/{id}/content`) **ban đầu bị bỏ sót** khỏi script nghiệm thu. `status == "succeeded"` chỉ nói worker chạy xong — nó **không** nói ảnh lấy về được. Khoá trỏ sai, URL hết hạn, hoặc quyền đọc sai đều cho ra đúng một job xanh với `outputs` trông đẹp. Khách trả tiền để **lấy được ảnh**, nên phép nghiệm thu phải kiểm đúng thứ đó.

🔑 Khoá nghiệm thu đã **thu hồi** ngay sau đó (A4) — nó tiêu được tiền thật.

| Operation | Chế độ | Schema + mô tả từng tham số | Scope | Quote trước khi tính tiền | Idempotency | Upload | Artifact | Usage | Webhook | Playground | Sandbox | Admin |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `image.thumbnail` | ASYNC_JOB | ✅ | `jobs:create` | ✅ | ✅ | — | ✅ ảnh | ✅ | ✅ | ✅ | ✅ | ✅ |
| `image.generate` | ASYNC_JOB | ✅ | `jobs:create` | ✅ | ✅ | ✅ ảnh tham chiếu | ✅ ảnh | ✅ | ✅ | ✅ | ✅ | ✅ |
| `image.upscale` | ASYNC_JOB | ✅ | `jobs:create` | ✅ | ✅ | ✅ bắt buộc | ✅ ảnh | ✅ | ✅ | ✅ | ✅ | ✅ |
| `text.prompt_package` | ASYNC_JOB | ✅ | `jobs:create` | ✅ | ✅ | — | — dữ liệu | ✅ | ✅ | ✅ | ✅ | ✅ |
| `image.ltt` | ASYNC_JOB | ✅ | `jobs:create` | ✅ | ✅ | — | ✅ ảnh | ✅ | ✅ | ✅ | ✅ | ✅ |
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
Đây đúng là chỗ `chataistudio` đã mắc: nó streaming, giữ credit theo id tin
nhắn, và **không** sinh Job — nên nó DEFER chứ không phải "chưa kịp làm".

⚠️ **App ấy đã bị xoá cứng ngày 09/09/2026** (chiến dịch AI CLEAN REBUILD V2,
pha 07): bản chất nó là một chat gọi ra pool Codex bên ngoài, nên nó đi theo
cả họ nhà cung cấp bị gỡ. **Bài học thì ở lại**, và nó không phụ thuộc vào app:
hợp đồng job hiện tại **không mô tả nổi** một đường streaming. Người kế tiếp
muốn bán streaming vẫn phải viết hợp đồng chạy mới — xem `runtime_noi_bo`.

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
| Hợp đồng streaming | *(không còn app nào)* | `chataistudio` đã xoá 09/09; rào vẫn đứng đó cho đường streaming tiếp theo. |
| Ranh giới chi phí cho runtime điều phối | `agent` | Cần sandbox và trần chi phí riêng trước khi bàn tới hợp đồng. |

Ba dòng đầu **cùng một hình dạng**: hợp đồng job hiện tại giả định giá chốt được
trước khi chạy. Chỗ nào giả định đó sai thì năng lực bị chặn — và chặn như vậy
là **đúng**, vì cái mất khi sai không phải một job hỏng mà là một lời hứa về giá
đã ký với khách.

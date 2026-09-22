# Public API V1 — Disposition CHỐT của 100% app và tool

**Bản này thay bản Prompt 01** (bản đầu là *ý định* trước khi đọc chi tiết từng
app; bản này là *kết quả* sau khi đã xây kernel và chạy 3 wave thật).

Nguồn: `platform_core.registry.discover()` + code app thật, ngày 2026-08-13 —
**15 app, 22 ToolSpec, 18 job_type** *(chưa tính `vps` — xem ghi chú cuối mục 1)*.

**Không tài liệu nào tự chứng minh được.** Bảng dưới đây được máy kiểm bằng
`tests/test_190_public_api_coverage.py`: thêm một app mà chưa quyết định thì
test đỏ; đánh EXPOSE_V1 mà không publish đúng tool đó thì test đỏ; đánh bất kỳ
trạng thái nào khác mà app vẫn publish thì test đỏ.

---

## 1. Bảng chốt (15/15 app)

| App | Disposition | Đang public | Lý do |
|---|---|---|---|
| `thumbnail` | **EXPOSE_V1** | `image.thumbnail` | Giá phẳng theo số ảnh, chốt trước khi chạy. Đã E2E qua worker (wave 1). |
| `anhnoibo` | **EXPOSE_V1** | `image.ltt` | Model ảnh **nội bộ** trên máy B (H37/Q102). Giá chốt trước khi chạy: theo số ảnh, nhân 3 khi có ảnh tham chiếu. ⚠️ *EXPOSE_V1 ở đây nghĩa là **được phép** publish, chưa phải **đang** publish* — công tắc `LTT_PUBLIC_API_TOOLS` vẫn chưa có tên nó, và model vẫn `is_active=False` tới khi qua cổng chất lượng. Chưa E2E. |
| `ltt_llm` | **EXPOSE_V1** | `text.chat` | Model **ngôn ngữ nội bộ** trên máy B (H38/Q106), anh em với `anhnoibo`. Khác ở một điểm: **giá phụ thuộc số token RA, chỉ biết sau khi sinh xong**, nên `credit_cost` là **trần ước cao** và nền tảng quyết toán theo số đo thật. Ngoài cửa job nó còn bán qua hai cửa **không phải job** (`/chat/completions` — `SYNC_BILLED`, Q106; và `/messages` + `/responses` — `STREAM`, Q107); hai cửa đó là **route**, không phải `ToolSpec`, nên chúng đóng băng ở `server/api/inventory.py` chứ không ở bảng này. |
| `ltt_voice` | **EXPOSE_V1** | `speech.ltt` | Model **giọng nói nội bộ** (Q117/Q118) — thứ ba trong nhóm model nhà, và là cái **đầu tiên chạy trên chính máy A** thay vì máy B: một sidecar ấm sau loopback `127.0.0.1:8120`, trong venv cách ly. Vì engine cùng máy nên **không có provider, không có khoá trong `api_pool`, và không sửa `platform_core/` dòng nào** — token đi đúng đường `LTT_CODEX_SIDECAR_TOKEN` đã chạy thật. Giá theo **giây tiếng nói sinh ra thật** (đo bằng `ffprobe`), giữ chỗ theo ký tự **đã chuẩn hoá**. ⚠️ *EXPOSE_V1 ở đây nghĩa là **được phép** publish, chưa phải **đang** publish* — `LTT_PUBLIC_API_TOOLS` vẫn chưa có tên nó. ⛔ Và nó có một cổng thứ tư mà hai app kia không có: **dịch vụ `LTTStudioVoice` phải đang chạy**; cổng đó không nằm trong mã nguồn nên không test nào thấy được — `setup/4-nghiem-thu.ps1` là chỗ kiểm nó. Chưa E2E qua Cloudflare. |
| `taoanh` | **EXPOSE_V1** | `image.generate` | Giá theo model qua alias công khai; 1 ảnh tham chiếu qua upload (wave 1). |
| `upscalevideo` | **EXPOSE_V1** | `image.upscale` | Giá phẳng 2/4 theo preset; đường GPU thật (wave 2). |
| `prompt_ai_ommi` | **EXPOSE_V1** | `text.prompt_package`, `story.storyboard` | Giá theo `scene_count`; kết quả là dữ liệu, trả qua `result` (wave 3). |
| `taovideo` | **MIGRATE_CAPABILITY_THEN_EXPOSE** | — | `resolution/duration/aspect_ratio` phụ thuộc model, tập hợp lệ khác nhau theo model → publish hợp nhất sẽ để khách trả tiền cho tổ hợp provider từ chối. |
| `autosubvideo` | **MIGRATE_CAPABILITY_THEN_EXPOSE** | — | Giá theo `duration_s` do client khai + worker **nâng hold** khi đo thật (`_dam_bao_giu_cho`) → phá lời hứa quote đã ký (Q84). Ngoài ra 3 job 0-credit (Q50) không được mở khi chưa có quota chống lạm dụng. |
| `taoclipngan` | **MIGRATE_CAPABILITY_THEN_EXPOSE** | — | Cùng nguyên nhân: giá theo `duration_s` + nâng hold; thêm GPU. |
| `chataistudio` | **DEFER** | — | **Không có Job**: credit giữ theo id tin nhắn, chạy streaming qua sidecar. Toàn bộ hợp đồng job/quote/settle không áp dụng được. Mở cần thiết kế async riêng + quyết định ToS về sidecar. |
| `agent` | **DEFER** | — | Là **runtime điều phối**, không phải một tool: public nó là public cả một cơ chế chạy. Cần ranh giới chi phí/sandbox riêng trước khi bàn. |
| `qualitylab` | **INTERNAL_ONLY** | — | `surface=admin`, operator-only (Q83). |
| `lttcode` | **INTERNAL_ONLY** | — | Trang web công khai `/lttcode` (giới thiệu, hướng dẫn, tải — `surface=customer`, `public=True`) + kênh phát hành, đăng nhập và tìm web của ứng dụng desktop LTTCODE. Về **API** vẫn nội bộ: không `ToolSpec`, không Job; LTTCODE gọi `/api/v1` bằng khoá `ltt_sk_` của chính người dùng. |
| `nexus` | **DEFER** | — | **Quản lý thiết bị, không phải một tool có giá.** Không có `ToolSpec` và không sinh Job, nên toàn bộ hợp đồng quote/settle không áp được. Public nó nghĩa là công bố một hợp đồng về **danh tính thiết bị** — phải chờ quyết định hạ tầng relay (D2) và legal review ranh giới AGPL. Q93, xem `docs/nexus/`. |
| `auto_scan_video` | **DEFER** | — | **Lồng tiếng Việt cho video** (pha 00–14). DEFER vì **hình dạng sản phẩm**, không phải vì "chưa làm xong": một lần lồng tiếng là **chín giai đoạn**, mỗi giai đoạn một job riêng, và bốn trong số đó chạy lại độc lập được. Ép vào `ToolSpec` một-vào-một-ra thì hoặc mất khả năng chạy lại một giai đoạn, hoặc bịa ra một hợp đồng mà chuỗi thật không có. ⛔ App còn `enabled=False` — chưa mở cho khách trên web, nên bàn mở qua API là bàn trước một bước. |
| `transcript` | EXPOSE_V1 | — | **MỞ 2026-09-22 (chủ dự án chốt).** Quy tắc đã đối soát với `bot_transcript` (sửa chữ V5 + từ điển, 1.5 s, kiểm legacy — `tests/test_1114_*`; khớp tuyệt đối 98/98 đoạn EN trên audio thật của chủ dự án). Giá **2 credit/phút audio** (`apps/transcript/gia.py`), `duration_s` do máy chủ đo (`measured_from=audio`, `hidden`), worker quyết toán `min(giá thật, đã giữ)` — không vượt quote (Q84). Trước đó: **Phiên âm có dòng thời gian** (Phase 08). DEFER vì chưa nghiệm thu E2E qua worker và chưa kiểm trên URL công khai. Đã đối chiếu parity trên **1.932 lượt job thật** của bot legacy (`docs/migration/workflow_apps/30_...`): bản chuyển 95,50 % so với 95,76 % của **chính engine gốc** đo trên đầu ra của nó — engine gọi `random.uniform` có chủ ý nên trùng khớp từng byte là bất khả. |
| `audio_pause` | **DEFER** | — | **Chèn khoảng lặng theo lời** (Phase 09). DEFER cùng lý do với `transcript`, cộng một điều nặng hơn: bot gốc **không để lại hiện vật nào** trên máy (workdir rỗng, kết quả nằm trên Drive), nên mệnh đề *"kết quả như bot đã giao"* hiện **không kiểm được** — chỉ đối chứng vi sai với hàm gốc là khả dĩ. |
| `prompt_canh` | **DEFER** | — | **Kịch bản → prompt cảnh** (Phase 10). DEFER vì **hình dạng giá**: nó thu tiền theo **từng lượt gọi model** qua `runtime_noi_bo`, nên `credit_cost` ở tầng job là **0 có chủ đích**. Hợp đồng quote/settle một-vào-một-ra không mô tả được giá của nó — mở ra `/api/v1` là công bố một hợp đồng giá mà đường thật không đi theo. |
| `video_assembly` | **DEFER** | — | **Dựng video từ clip** (Phase 11). DEFER vì nó là một **chuỗi nhiều giai đoạn** trên GPU (STT, khớp clip, tách nhạc, trộn tiếng, cháy phụ đề), giống `auto_scan_video` ở trên: ép vào một `ToolSpec` một-vào-một-ra thì mất khả năng chạy lại một giai đoạn. Và `vram_min_mb` **chưa đo thật**, nên scheduler chưa xếp chỗ đúng được. |
| `asv_media` · `asv_gpu` · `asv_voice` | **DEFER** | — | **Không phải app bán được**: ba vỏ thi hành của `auto_scan_video`, khai `surface="runtime"` + `catalog_parent`. Không thẻ catalog, không mục nav, không `ToolSpec`. Chúng tồn tại vì quyền nhặt job lọc theo **APP** chứ không theo `job_type` (`platform_core/jobs.py:158-164`), nên mỗi làn worker buộc phải là một thư mục riêng. |
| `chatltt` | **DEFER** | — | **Khách hàng nội bộ, không phải một năng lực mới.** Sản phẩm hội thoại của H43 gọi `text.chat` / `image.ltt` / `speech.ltt` qua `platform_core/runtime_noi_bo` — cùng ba tool đã bán, cùng một sổ tiền, cùng một hàng đợi. Nó **không khai `ToolSpec`** nào và đó là chủ đích: mở nó ra `/api/v1` là bán lại đúng ba năng lực ấy qua một hợp đồng thứ hai, và hợp đồng thứ hai là chỗ hai bảng giá bắt đầu lệch nhau. App còn **TẮT** (`enabled=False`) tới khi H43 Phase 13 PASS. Xem `docs/CHATLTT/`. |
| `lttvideo` | **INTERNAL_ONLY** | — | **Cổng đóng vì GIẤY PHÉP, không phải vì kế hoạch.** Video AI chạy bằng **WanGP** trên C-CLOUD (V2.1). `WanGP Community License 2.0` §5.2(g) cấm *"exposing the Software to customers or end users as a paid feature, add-on, or monetized backend component"* nếu không có giấy phép thương mại riêng; §7.2 nhắc lại cho đường API. Dùng **nội bộ** thì §1.8 và §3.3 cho phép rõ ràng. ⇒ App **không khai `ToolSpec`** nào, và mở tool ở đây sẽ là một quyết định **pháp lý** chứ không phải quyết định sản phẩm — nó chưa được đưa ra. Trích dẫn điều khoản đầy đủ: `docs/VIDEO_AI_V2/P01_UPSTREAM_PIN.md` mục 2; liên hệ cấp phép ghi ở §5.4 của chính giấy phép. |
| `vps` | **DEFER · WEB_ONLY · WONT_BUILD_PUBLIC_API** | — | Q124/D01 khóa VPS là tính năng web first-party. Không ToolSpec, `/api/v1/vps`, API-key provisioning, reseller API hay SDK công khai. Internal infrastructure API vẫn được phép. |

> ⚠️ **`apps/vps` chưa có trong bảng này — CÓ CHỦ ĐÍCH, không phải bỏ sót.**
> App đó **đang được xây dở ở một dự án/phiên khác** nên cố ý chưa commit (chủ
> dự án xác nhận 22/08). Hệ quả: `test_190` và `test_212` mỗi tệp đỏ **đúng một
> test** cho tới khi app đó xong và được phân loại. **Đã biết, không phải hồi
> quy** — đừng đi tìm nguyên nhân trong H37.
>
> Không có rủi ro lọt ra API: nó khai **không ToolSpec nào** và
> `app_may_be_public()` trả `False`.

## 2. Tool đang public (5/22 ToolSpec)

| Tool | App | Giá | Ghi chú hợp đồng |
|---|---|---|---|
| `image.thumbnail` | thumbnail | 5/ảnh | ẩn `model` (giá không theo model), enum style là tập chắt lọc |
| `image.generate` | taoanh | 5/5/8/16 theo alias | 4 alias model; ẩn `image_keys` (mảng chưa hỗ trợ) |
| `image.upscale` | upscalevideo | 2 (fast) / 4 (quality) | GPU; input qua upload |
| `text.prompt_package` | prompt_ai_ommi | theo `scene_count` | ẩn `operation`/`model`/`resources` |
| `story.storyboard` | prompt_ai_ommi | theo `scene_count` | như trên |

🔴 **SỬA 2026-08-30 — CÂU DƯỚI ĐÂY ĐÃ LỖI THỜI, và nó lỗi về phía nguy hiểm.**

~~5 ToolSpec còn lại **không** public: `video.generate`, `video.upscale`,
`video.subtitle`, `video.short_clips` (chờ migrate), `image.batch_generate`.~~

Ba trong năm cái đó **đã có hợp đồng công khai**:

| Tool | Thay đổi |
|---|---|
| `video.upscale` · `video.subtitle` | **mở 29/08** (H35.10) — máy chủ đo thời lượng lúc báo giá, đóng lại Q84 |
| `video.generate` | **hợp đồng đóng băng 30/08** (API Expansion V2 Phase 03); operator **chưa bật** |

⇒ Còn **hai** chưa có hợp đồng: `video.short_clips` (thiếu trần đồng thời GPU,
H35.10c) và `image.batch_generate` (trùng năng lực với `image.generate`).

⛔ **Vì sao nó lỗi về phía nguy hiểm:** một phiên sau đọc câu cũ sẽ tin ba tool
đó là mã chết và sửa chúng như mã chết. Hai trong ba **đang phục vụ khách trả
tiền**.

⭐ Đây là **lần thứ ba** trong dự án một tài liệu trạng thái nói sai theo cùng
hướng đó (hai lần trước ở hàng H35 của `CLAUDE.md`, sửa 26/08 và 30/08). Bài học
đã ghi ở đó và áp luôn ở đây: **đừng đọc con số trong tài liệu, hỏi máy chủ.**

```powershell
Invoke-RestMethod https://app.lttstudios.com/api/v1/tools -Headers @{Authorization="Bearer $env:LTT_API_KEY"; "User-Agent"="ltt/1.0"} | ForEach-Object items | Select-Object name
```

hoặc, cho trạng thái trong cây (kể cả tool đã khai mà chưa bật):

```powershell
python tools\do_current_truth.py
```

## 3. Ba việc chặn, một nguyên nhân gốc

`video.upscale`, `video.subtitle`, `video.short_clips` bị chặn bởi **cùng một
thứ**: giá dựa trên thời lượng **do người gọi khai**, và worker nâng hold khi đo
được thời lượng thật. Với người dùng chọn file trên giao diện thì chấp nhận
được; với máy gọi máy thì mâu thuẫn với lời hứa của một quote đã ký (Q84).

**Sửa một chỗ là mở được cả ba:** đo thời lượng phía server từ chính file đã
upload lúc báo giá (file đã nằm trong `upload_sessions`, đã qua magic-check),
rồi khoá giá; hoặc cấm top-up cho job đến từ API và để job fail-refund nếu vượt.

Cần quyết định sản phẩm: cách một tốn thêm một lần đọc metadata; cách hai làm
một số job dài bị từ chối giữa chừng.

## 4. Endpoint family V1 (đang chạy)

```
GET    /api/v1/health            GET    /api/v1/capabilities
GET    /api/v1/me
GET    /api/v1/tools             GET    /api/v1/tools/{tool_name}
GET    /api/v1/models            GET    /api/v1/models/{model_name}
POST   /api/v1/quotes
POST   /api/v1/jobs              GET    /api/v1/jobs
GET    /api/v1/jobs/{job_id}     POST   /api/v1/jobs/{job_id}/cancel
POST   /api/v1/uploads           POST   /api/v1/uploads/{id}/content
POST   /api/v1/uploads/{id}/confirm
GET    /api/v1/artifacts/{id}    GET    /api/v1/artifacts/{id}/content
POST   /api/v1/webhooks          GET    /api/v1/webhooks
GET    /api/v1/webhooks/deliveries
DELETE /api/v1/webhooks/{webhook_id}
GET    /api/v1/credits/balance   GET    /api/v1/usage
GET    /api/v1/openapi.json
```

Quản lý developer key **không** nằm trên `/api/v1`: tạo/thu hồi khoá làm ở portal
có phiên đăng nhập (Prompt 15). Một khoá tự cấp khoá khác là leo thang quyền
không cần thiết cho V1.

## 5. Vẫn đúng sau 3 wave

- `customer_visible=True` **không** làm một tool public — `kichban` (đã gỡ 2026-08-25) từng là bằng chứng
  sống, và có test.
- App `retired/internal/maintenance` hoặc `surface` `admin/runtime` **không bao
  giờ** public: chặn ở `catalog.app_may_be_public()`, không phụ thuộc cờ trong
  manifest.
- Ba cổng độc lập vẫn nguyên: disposition app → khai báo tool → công tắc
  operator (`LTT_PUBLIC_API_TOOLS`), rồi `allowed_tools` của từng khoá.

## `video_crawler` — DEFER (22/09/2026)

Cào video nguồn (YouTube, TikTok, Douyin, Bilibili, …). Chưa mở qua Public API: app còn `enabled=False`, và cổng pháp lý (khách cam kết quyền với nội dung ở MỖI lượt tải, trần tải theo tài khoản — `docs/migrations/video_crawler/PHAP_LY_NHAP.md`) đang thi hành ở route web; một `ToolSpec` bây giờ sẽ đi vòng qua nó. Mở khi cổng được chuyển xuống `features.nop` và điều khoản đã chốt.

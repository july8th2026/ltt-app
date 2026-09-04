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
| `nexus` | **DEFER** | — | **Quản lý thiết bị, không phải một tool có giá.** Không có `ToolSpec` và không sinh Job, nên toàn bộ hợp đồng quote/settle không áp được. Public nó nghĩa là công bố một hợp đồng về **danh tính thiết bị** — phải chờ quyết định hạ tầng relay (D2) và legal review ranh giới AGPL. Q93, xem `docs/nexus/`. |
| `chatltt` | **DEFER** | — | **Khách hàng nội bộ, không phải một năng lực mới.** Sản phẩm hội thoại của H43 gọi `text.chat` / `image.ltt` / `speech.ltt` qua `platform_core/runtime_noi_bo` — cùng ba tool đã bán, cùng một sổ tiền, cùng một hàng đợi. Nó **không khai `ToolSpec`** nào và đó là chủ đích: mở nó ra `/api/v1` là bán lại đúng ba năng lực ấy qua một hợp đồng thứ hai, và hợp đồng thứ hai là chỗ hai bảng giá bắt đầu lệch nhau. App còn **TẮT** (`enabled=False`) tới khi H43 Phase 13 PASS. Xem `docs/CHATLTT/`. |
| `vps` | **DEFER** | — | Bán **máy chủ ảo** (H39). Không khai `ToolSpec` nào, và đó không phải thiếu sót: một máy ảo là một **hợp đồng thuê** có thời hạn, không phải một lượt chạy tính tiền một lần — quote → giữ chỗ → quyết toán không mô tả được nó. ⚠️ Dòng này ghi lại **trạng thái thật** (không có `ToolSpec`), không phải một quyết định sản phẩm; chủ H39 muốn bán qua `/api/v1` thì phải nói được hợp đồng là gì trước. App vẫn **TẮT** (`LTT_VPS` chưa đặt). |

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

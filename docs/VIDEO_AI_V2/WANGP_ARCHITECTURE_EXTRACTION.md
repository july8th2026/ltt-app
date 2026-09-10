# WANGP ARCHITECTURE EXTRACTION REPORT

Đọc theo chiều **WanGP → abstraction thật → LTT còn thiếu gì**, không ép WanGP
vào taxonomy tự nghĩ.

⛔ Mọi kết luận đều kèm `EVIDENCE`. Chỗ nào chưa có bằng chứng thì ghi thẳng là
chưa có, không dùng *"có vẻ"* / *"chắc là"*.

---

## 1. Exact upstream SHA

```
deepbeepmeep/Wan2GP @ 1e1dd2757f24923f008593d9d4ec09062234be20
WanGP_version = "12.71"
```

> **EVIDENCE** · file `wgp.py:159` · symbol `WanGP_version` · behavior: hằng số
> phiên bản trong mã · **confidence: CHẮC CHẮN** (`git rev-parse HEAD` trên bản
> clone tại `E:\WANGP\Wan2GP` khớp đúng SHA ghim ở `P01-D-04`).

## 2. Các subsystem chính

| Subsystem | Nơi ở |
|---|---|
| Runtime + GUI Gradio | `wgp.py` (14.000 dòng, 1.053 lời gọi `gr.*`) |
| API Python | `shared/api.py` |
| API cho CLI / WebUI | `shared/api_cli.py`, `shared/api_webui.py` |
| MCP server | `shared/mcp_server.py` (1.609 dòng) |
| Định vị tệp model | `shared/utils/files_locator.py` |
| Quản lý bộ nhớ | thư viện ngoài `mmgp` 3.7.14 |
| Định nghĩa model | `defaults/*.json` (**225 tệp**) |
| Preset theo họ model | `profiles/` |
| Agent | `wangp-agent/` (`SKILL.md` + `agents/`) |
| Plugin | `plugins/`, `plugins.json` |
| Tiền/hậu xử lý | `preprocessing/`, `postprocessing/` |

> **EVIDENCE** · `ls` cây tại SHA ghim + `wc -l` · **confidence: CHẮC CHẮN**

## 3. Unified media/input abstraction **thật** — CÓ

WanGP khai **modality đầu vào** ngay trong metadata của từng model:

```python
"inputs":  ["text", "image", "video", "audio"],
"outputs": ["video", "audio"],
"main_output": ["video"],
```

> **EVIDENCE** · file `docs/API.md` mục *Model Metadata* · symbol
> `session.list_model_metadata()` / `get_model_metadata()` · behavior: mỗi model
> trả về `metadata.inputs` liệt kê modality nó nhận · **confidence: CAO**
> (tài liệu + symbol tồn tại ở `shared/api.py:59,80`).

⇒ Trừu tượng *"prompt + ảnh + video + âm thanh"* mà LTT định tự dựng **đã tồn
tại**, và còn **truy vấn được**.

## 4. Media-role representation **thật** — CÓ, chi tiết hơn thiết kế của ta

```python
"media_inputs": {
    "image": {"start": True, "end": True, "reference": True,
              "background": False, "injected_frames": False},
    "video": {"continue": True, "control": True},
    "audio": {"prompt": True, "output": True},
}
```

> **EVIDENCE** · `docs/API.md` mục *Model Metadata* · behavior: **từng model tự
> khai vai media nào nó nhận**, dạng bool · **confidence: CAO**

Và ở tầng settings, vai được mã hoá bằng **cờ chữ cái**:
`image_prompt_type` (`S` start, `E` end, `V` video-continue, `I`/`KI` reference),
`video_prompt_type`, `audio_prompt_type` (`A`/`B`).

> **EVIDENCE** · `docs/API.md`: *"start images add `S`, end images add `E`
> without removing `S`, source-video continuation adds `V`, reference images use
> the first declared reference mode containing `I`, and audio guides use declared
> `A`/`B` source modes"* · **confidence: CAO**

⇒ **Media-role schema của LTT là bản trùng lặp.** Bảng 8 vai tôi đề xuất
(`khung_dau`/`khung_cuoi`/`nhan_vat`/…) chính là `media_inputs` dịch sang tiếng
Việt.

## 5. Capability / schema system **thật** — CÓ, và đầy đủ hơn resolver của ta

```python
"capabilities": {"text_to_video": True, "image_to_video": True, "audio_output": True}
```

Và **truy vấn được theo năng lực**:

```python
session.list_model_defs(main_output="video", inputs="image")
```

> **EVIDENCE** · `shared/api.py:31` `list_model_defs(...)` với tham số
> `main_output`, `inputs`, `family`, `base_model_type`, `finetune`, `model_type`,
> `name`, `query`, `limit`, `offset` · behavior: lọc model theo năng lực, hỗ trợ
> glob `*`/`?` · **confidence: CHẮC CHẮN** (đọc chữ ký hàm trong mã).

Bốn phép kiểm mà *Capability Resolver* của tôi định dựng, WanGP đã có ba:

| Phép kiểm của tôi | WanGP đã có |
|---|---|
| engine hỗ trợ kiến trúc? | `list_model_defs(...)` lọc theo `inputs`/`main_output` |
| tệp model có trên đĩa chưa? | **`get_model_availability(model_type)`** · `list_model_availability(**filters)` |
| có hồ sơ đã kiểm chưa? | `get_model_settings(model_type, setting_id)` · `get_default_settings` |
| ngân sách? | ❌ **không có — đây là của LTT** |

> **EVIDENCE** · `shared/api.py:178,192,100,91` · **confidence: CHẮC CHẮN**

Thêm: `get_model_schema(model_type)` trả về *"generic capabilities and media
roles plus name, model_type, description, **FPS/frame limits**, infos,
prompt_infos, and sliding-window support"*.

> **EVIDENCE** · `docs/API.md`; symbol `shared/api.py:201` · **confidence: CAO**

## 6. Settings / template system **thật** — CÓ, và LTT Quality Profile trùng nó

WanGP có **user settings file** (JSON) lưu được, chọn được từ dropdown
`Lora / Settings`, và **link được vào công cụ của Deepy**:

- *"Deepy reads the linked WanGP settings file directly, so changes to that file
  are picked up automatically"*
- *"If the linked file disappears, Deepy falls back to that tool's default template"*
- *"Deepy can still override width, height, frame count, audio duration, FPS,
  inference steps, and LoRAs"*

> **EVIDENCE** · `docs/DEEPY.md` mục *Linking WanGP Settings to Deepy Tools* +
> *Important behavior* · **confidence: CAO**

Kèm API xuất/nhập: `prepare_settings_for_export()`,
`get_exported_default_settings()`, `merge_settings_with_defaults()`.

> **EVIDENCE** · `shared/api.py:146,160,129` · **confidence: CHẮC CHẮN**

⇒ **LTT không cần một định dạng profile mới.** `profile_id` chỉ cần trỏ tới
**một tệp settings JSON của WanGP, có phiên bản trong kho LTT**.

## 7. Generation normalization **thật** — CÓ

Hai hàm chuẩn hoá chạy **tự động lúc nhận job**:

| Hàm | Việc |
|---|---|
| `apply_media_flag_defaults(settings, model_def)` | điền cờ vai media còn thiếu **theo đúng thứ model đó khai nhận** |
| `apply_video_length_duration(settings, model_def)` | nhận `video_length` dạng `"10s"`, quy ra số khung theo `force_fps` hoặc FPS của model |
| `_model_frames_maximum(...)` | trần số khung của model |

> **EVIDENCE** · `shared/api.py:74,122,110` · behavior: chữ ký hàm + mô tả trong
> `docs/API.md` · **confidence: CHẮC CHẮN**

Thêm: đường dẫn tương đối tự quy về tuyệt đối; **virtual media path**
`file.mp4|start_frame=123,end_frame=456[,audio_track_no=2]` để lấy một đoạn của
video mà không cần cắt trước.

> **EVIDENCE** · `docs/API.md` mục *Accepted Input Shapes* · **confidence: CAO**

⇒ Tầng *"dịch vai media sang tham số engine"* của LTT là **trùng lặp**.

## 8. API lifecycle **thật**

```
init(root, cli_args)  ->  WanGPSession
   .list_model_defs / list_model_metadata / get_model_schema      # kham pha
   .get_model_availability / list_model_availability              # san sang chua
   .get_default_settings / get_model_settings                     # tham so
   .submit_task(settings) -> SessionJob                           # gui
       job.events.iter(timeout)  -> progress | preview | stream   # tien do
       job.cancel()                                               # huy
       job.result() -> GenerationResult(success, generated_files, errors, artifacts)
   .submit_media_postprocessing / submit_audio_remux / submit_audio_postprocessing
   .submit_manifest([...])                                        # lo nhieu task
   .cancel() / .active_job / .close()
```

> **EVIDENCE** · `shared/api.py:222,226,231,235,239,243,269,276,283`; lớp
> `SessionStream.iter` (`:379`), `ProgressUpdate` (`:179`), `PreviewUpdate`
> (`:190`), `GenerationResult.cancelled` (`:248`) · **confidence: CHẮC CHẮN**

**Đã chạy thật, không chỉ đọc:** 786 sự kiện `progress`, 20 `preview`, 217
`stream` trong một lượt 20 bước; huỷ trả `success=False` + `"Generation was
cancelled"`.

> **EVIDENCE** · `do_luong_P01/ket_qua_luot1.json`, `ket_qua2_luot2.json` — đo
> trên Pod `bly29qwp5bum3r` 06/09 · **confidence: CHẮC CHẮN**

## 9. MCP lifecycle **thật** — 20+ công cụ

```
wangp_models · wangp_model · wangp_list_models · wangp_search_models
wangp_list_model_defs · wangp_get_model · wangp_get_model_metadata
wangp_get_model_availability · wangp_list_model_availability
wangp_get_default_settings · wangp_model_settings · wangp_get_model_schema
wangp_list_loras · wangp_list_gallery · wangp_get_media_settings
wangp_artifact · wangp_io · wangp_notify
wangp_create_gallery_upload · wangp_create_gallery_download
wangp_list_deepy_templates · wangp_get_deepy_template_settings
wangp_postprocess · wangp_toolbox · wangp_agent (prompt)
```

> **EVIDENCE** · `shared/mcp_server.py` dòng 1172–1509, các `@mcp.tool` ·
> **confidence: CHẮC CHẮN**

Transport: `stdio` hoặc `streamable-http` tại `/mcp`; giữ **một
`WanGPSession` ấm** giữa các lượt.

> **EVIDENCE** · `docs/API.md` mục *MCP Server* · **confidence: CAO**

⚠️ Tài liệu của chính nó cảnh báo **không có xác thực**: *"Use `--mcp-host
0.0.0.0` only on a trusted network or behind an authenticated reverse proxy."*

## 10. Deepy orchestration **thật**

| Câu hỏi | Trả lời có bằng chứng |
|---|---|
| Nhận biết media bằng cách nào | ngôn ngữ tự nhiên (`selected`, `this image`, `last video`, `the current frame` → dùng **thời điểm đang phát** của video), hoặc id nội bộ `image_1`/`video_3` |
| Dùng Gallery thế nào | ưu tiên mục **đang chọn**; giải được tham chiếu tới **kết quả cũ** |
| Dùng model metadata/schema thế nào | **Deepy Prime** *"can perform the same work while also **selecting among compatible models**"* |
| Khi nào dùng template mặc định | mỗi công cụ có template; link được tới user settings file; mất tệp thì **rơi về template mặc định** |
| Có tự hiểu vai ảnh/video không | ⚠️ **chưa có bằng chứng trực tiếp**. Có bằng chứng nó chọn **model** tương thích và điều phối nhiều bước; vai media thì `apply_media_flag_defaults` lo ở tầng dưới |
| Có hỏi lại khi mơ hồ không | ✅ *"**ask for clarification instead of inventing a result** when a reference is ambiguous"* |
| "Ảnh nhân vật + video chuyển động + prompt" | ⚠️ **chưa có bằng chứng** cho đúng tổ hợp này. Tài liệu nêu *"generate talking videos from a still image plus speech audio"* — tổ hợp khác |
| Chưa làm gì | **không có** ngân sách/credit, **không có** quyền sở hữu theo người dùng, **không có** lưu trữ bền ngoài Gallery cục bộ |

> **EVIDENCE** · `docs/DEEPY.md` mục *How Deepy Interprets Media References*,
> *What You Can Ask Deepy To Do*, *Tool Templates* · **confidence: CAO** cho các
> ô ✅; **THẤP / chưa đủ** cho hai ô ⚠️ — cần đọc `wangp-agent/agents/` hoặc chạy
> thử mới kết luận được.

Bảy công cụ sinh của Deepy: `Media Generator` · `Video With Speech` ·
`Image Generator` · `Image Editor` · `Song Generator` ·
`Speech From Description` · `Speech From Sample`.

⭐ **Đáng chú ý: đây là taxonomy theo VIỆC, không phải theo t2v/i2v.** Chính
WanGP ở tầng agent cũng **không** dùng taxonomy mode kỹ thuật.

## 11. Gallery / media flow **thật**

`wangp_create_gallery_upload(filename)` → trả URL **dùng một lần, sống ngắn** →
PUT byte thô → WanGP kiểm tra media, đưa vào Visual Gallery (ảnh/video) hoặc
Audio Gallery, và **chọn nó**. Chiều ngược lại: `wangp_create_gallery_download`.

> **EVIDENCE** · `shared/mcp_server.py:1424,1430`; `docs/API.md` mục *MCP Server*
> · **confidence: CHẮC CHẮN** (symbol tồn tại) / **CAO** (hành vi, theo tài liệu)

⇒ Yêu cầu *"scoped, short-lived transfer"* của kiến trúc V2.1 §5 **đã có sẵn**.

## 12. Preprocess / postprocess **thật**

Hậu xử lý đi qua **cùng một hàng đợi**: `submit_media_postprocessing` (temporal /
spatial upsampling, film grain), `submit_audio_remux`, `submit_audio_postprocessing`.
Tiền xử lý: `preprocessing/` (pose, depth, edge, mask…).

> **EVIDENCE** · `shared/api.py:231,235,239`; thư mục `preprocessing/`,
> `postprocessing/` · **confidence: CHẮC CHẮN**

## 13. Queue / cancel / progress **thật**

Một hàng đợi nội bộ C-CLOUD; `submit_manifest` gửi lô. Sự kiện phát qua
`SessionStream` (`put`/`get`/`iter`/`close`). Huỷ **hợp tác** ở hai mức:
`job.cancel()` và `session.cancel()`.

> **EVIDENCE** · `shared/api.py:344–389, 226, 243, 276` · **confidence: CHẮC CHẮN**

⚠️ Đây là hàng đợi **thực thi cục bộ của C-CLOUD**, không phải hàng đợi sản phẩm.
Kiến trúc V2.1 §2.A đã chốt: **hàng đợi của LTT là nguồn chân lý**.

## 14. Model switching / VRAM **thật**

*"WanGP loads models on demand and can switch without restarting… the previous
model is unloaded as needed to recover memory."* Năm hồ sơ bộ nhớ (1–5) do
`mmgp` 3.7.14 thi hành.

> **EVIDENCE** · `docs/MODELS.md` mục *Model switching and custom models*;
> `docs/CLI.md` mục *Performance Profiles*; `wgp.py:158` `target_mmgp_version` ·
> **confidence: CAO**

🔴 **Nhưng có một ràng buộc đo được, không nằm trong tài liệu:** `init()` chỉ gọi
được **một lần mỗi tiến trình** — đổi `profile`/`attention`/`root` phải đổi tiến
trình.

> **EVIDENCE** · lỗi thật `"WanGP runtime already loaded with different
> root/config/cli args"`, `do_luong_P01/ket_qua2_luot2.json` · **confidence:
> CHẮC CHẮN** · ghi ở `P01-D-13`.

---

## 15. Những gì WanGP ĐÃ GIẢI QUYẾT

1. Trừu tượng đầu vào đa modality (`inputs`)
2. Khai báo **vai media theo từng model** (`media_inputs`)
3. Khai báo **năng lực** (`capabilities`) + **truy vấn theo năng lực**
4. **Model schema**: FPS, trần khung, sliding-window, mô tả
5. **Sẵn sàng hay chưa** (`get_model_availability`)
6. **Tham số mặc định theo model** (`get_default_settings`) — đã bắt được thật
7. **Tệp settings lưu được** = hệ profile, link được vào công cụ agent
8. **Chuẩn hoá job**: điền cờ vai media, quy `"10s"` ra số khung, trần khung
9. Vòng đời job: submit · progress · **preview mỗi bước** · cancel · result
10. Truyền media **có phạm vi, dùng một lần** (gallery upload/download)
11. Tiền/hậu xử lý qua cùng hàng đợi
12. Nạp/đổi model + quản lý VRAM (`mmgp`, 5 hồ sơ)
13. **MCP server 20+ công cụ** cho agent
14. **Deepy Prime**: chọn model tương thích, điều phối nhiều bước, **hỏi lại khi mơ hồ**

## 16. Những gì LTT KHÔNG NÊN XÂY LẠI

| Thứ tôi đã đề xuất | Trùng với |
|---|---|
| Media-role schema (8 vai) | `metadata.media_inputs` + cờ `S/E/V/I/A/B` |
| Capability Resolver (3 trong 4 phép kiểm) | `list_model_defs(inputs=, main_output=)` + `get_model_availability` |
| Bộ dịch vai media → tham số engine | `apply_media_flag_defaults()` |
| `duration_s` → `video_length` | `apply_video_length_duration()` |
| Định dạng Quality Profile mới | tệp user settings JSON của WanGP |
| Router ý định bằng luật | truy vấn theo năng lực + Deepy Prime |
| Cơ chế hỏi lại khi mơ hồ | Deepy đã có |
| Truyền media có phạm vi | gallery upload/download |
| Tiến độ / xem trước / huỷ | `SessionStream` + `job.cancel()` |

## 17. Những gì LTT THỰC SỰ CÒN THIẾU

Không thứ nào trong danh sách này tồn tại trong WanGP — **kiểm bằng cách tìm
symbol, không phải bằng cảm nhận**:

1. **Auth / vai trò / quyền dùng app** — WanGP không có khái niệm người dùng
2. **Sổ credit + định giá** — không có bất kỳ khái niệm tiền nào
3. **Quyền sở hữu media theo người dùng** — Gallery là cục bộ, không có chủ sở hữu
4. **Lưu trữ bền (R2) + lịch sử** — Gallery nằm trên máy sẽ bị xoá
5. **Hàng đợi job của LTT** (nguồn chân lý sản phẩm) — khác hàng đợi thực thi
6. **Vòng đời cloud + ngân sách** — bật/tắt/tồn kho/hoá đơn
7. **Chính sách năng lực**: WanGP nói *"model này làm được gì"*; LTT phải nói
   *"khách hạng này được dùng gì"* — đó là **allowlist**, không phải resolver
8. **Nguồn gốc profile**: WanGP đọc tệp settings; LTT phải quyết **tệp nào được
   duyệt**, có phiên bản trong git, ai đổi và vì sao
9. **GUI tiếng Việt, phẳng, theo hợp đồng app LTT** (`ltt.css`, i18n, catalog/nav)
10. **Ranh giới bí mật** — không đưa khoá R2/CSDL/phiên lên C-CLOUD

## 18. Abstraction trong thiết kế trước của ta LÀ TRÙNG LẶP

- ❌ `media role schema` 8 vai → trùng `media_inputs`
- ❌ `intent/task taxonomy` 8 task → trùng một phần *tool template* của Deepy +
  `capabilities`; và **nguy hiểm hơn**: nó tạo **bản sao thứ hai của sự thật**
  phải đồng bộ tay mỗi lần WanGP thêm model
- ❌ `rule-based router` → trùng truy vấn năng lực
- ❌ `capability resolver` → trùng 3/4
- ❌ `quality profile format` mới → trùng settings file
- ❌ cơ chế hỏi lại → Deepy đã có

⭐ **Bài học gọi tên:** tôi thiết kế từ **taxonomy tự nghĩ** rồi định ép WanGP
vào. Chiều đúng là **trích abstraction thật trước**. Cùng lỗi với lần hỏi
"V1 chọn T2V hay I2V" — cả hai đều là **áp một bản đồ có sẵn trong đầu lên một
lãnh thổ chưa đo**.

## 19. Abstraction VẪN cần giữ ở A-CONTROL

Đúng `D-V2-004`, không hơn:

`auth` · `vai trò` · `hàng đợi job` · `quyền sở hữu media` · `R2/lịch sử` ·
`sổ credit + giá` · `allowlist năng lực` · `sổ đăng ký profile (git)` ·
`vòng đời cloud + ngân sách` · `GUI + i18n`

Và **một thứ mới phát hiện trong lượt audit này**: `profile_id` phải neo vào
**cặp (tệp settings, SHA WanGP)** — vì tham số chỉ có nghĩa với đúng phiên bản
engine sinh ra chúng.

## 20. Kiến trúc tối giản đề xuất SAU KHI trích WanGP

```
GUI LTT (phang: prompt + media + 3 dieu khien)
        |
A-CONTROL
   auth · so huu · credit · hang doi LTT · R2
   allowlist nang luc      <- CHINH SACH, khong phai resolver
   so dang ky profile      <- tro toi tep settings JSON + SHA WanGP
        |  chuyen media qua gallery upload (co pham vi, dung mot lan)
        v
WanGP tren C-CLOUD
   list_model_defs(inputs=, main_output=)    <- kham pha nang luc
   get_model_availability()                  <- san sang chua
   settings file da duyet + override toi thieu
   apply_media_flag_defaults()               <- TU dien vai media
   submit_task -> progress/preview -> result
        |
     tep ra  ->  A-CONTROL tai ve  ->  R2 cua nguoi dung  ->  xac minh  ->  DONE
```

**LTT viết mới đúng bốn thứ:** GUI phẳng · client gọi API WanGP · allowlist
năng lực · sổ đăng ký profile. Mọi thứ khác là **gọi lại**, không phải xây lại.

⚠️ Deepy **chưa** nằm trong sơ đồ này. `D-V2-007` khoá: Deepy trước, nhưng chỉ
sau khi có phép đo. Và hai ô ⚠️ ở mục 10 chưa đủ bằng chứng để giao cho nó việc
suy vai media.

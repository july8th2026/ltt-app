# Public API — nhật ký thay đổi

Ghi **thay đổi mà một tích hợp có thể cảm nhận được**, không phải mọi commit.
Ai muốn biết code đổi gì thì đọc git; trang này trả lời một câu khác: *"tôi có
phải sửa gì không, và khi nào?"*

Mỗi mục nói ba điều: **cái gì đổi**, **có phá vỡ tương thích không**, và **phải
làm gì**. Mục nào không trả lời được cả ba thì chưa đáng viết ra.

Bề mặt công khai được đóng băng trong `CONTRACT_BASELINE.json` và
`tools/check_api_compat.py` chạy trong gate. Một thay đổi phá vỡ tương thích
**không thể** lên tàu mà không có người ghi lại nó ở đây và chạy `--accept` —
lần ghi lại đó hiện ra trong diff.

## Phân loại

| Nhãn | Nghĩa |
|---|---|
| **BREAKING** | Tích hợp đang chạy sẽ hỏng. Chỉ được phép kèm phiên bản mới hoặc lịch ngừng hỗ trợ đã công bố. |
| **ADDED** | Thứ mới. Client không hỏi tới thì không thấy. |
| **DEPRECATED** | Vẫn chạy, đã có ngày kết thúc. Header `Deprecation` + `Sunset` (RFC 8594) xuất hiện trên phản hồi. |
| **FIXED** | Hành vi đã sai so với tài liệu, nay đúng. |

## 2026-09-04 — bộ cài `1.6.0`: Claude Code cũng nén đúng lúc

**FIXED · Thêm `CLAUDE_CODE_AUTO_COMPACT_WINDOW` và `MAX_MCP_OUTPUT_TOKENS`.**

Nếu bạn dùng **Claude Code**, hãy cài lại bộ cài `1.6.0`.

**Vì sao bản trước chưa đủ.** Chúng tôi đã khai `CLAUDE_CODE_MAX_CONTEXT_TOKENS`
và tưởng thế là xong. Nhưng biến đó chỉ sửa con số Claude **giả định** — nó
**không** đặt ngưỡng nén. Tài liệu chính thức của Claude Code nói rõ: không đặt
cửa sổ nén thì Claude nén khi hội thoại **chạm đúng** cửa sổ ấy, tức **100%**.

Với số của chúng tôi, điều đó chừa lại **13.599** token trước trần cứng, trong
khi một lượt trả lời dài nhất là **32.768**. Và Claude chỉ kiểm ngưỡng **giữa
hai lượt**. Nên một lượt có kết quả công cụ lớn vẫn có thể vượt trần và nhận
`413` — đúng triệu chứng chúng tôi vừa sửa cho Codex, chỉ khác tên khoá.

Bản `1.6.0` đặt cửa sổ nén ở **123.617**, cùng con số Codex đang dùng.

**`MAX_MCP_OUTPUT_TOKENS`:** mặc định của Claude là 25.000 token cho một phản
hồi MCP — chiếm 76% khoảng trống. Hai phản hồi trong một lượt là tràn. Bản này
hạ về **16.384**, cùng con số với trần kết quả công cụ của Codex.

**Bạn phải làm gì:** cài lại rồi chạy `cam` như cũ. Nếu bạn tự đặt tay
`CLAUDE_CODE_MAX_CONTEXT_TOKENS` mà **không** đặt `CLAUDE_CODE_AUTO_COMPACT_WINDOW`,
hãy thêm biến thứ hai — biến thứ nhất một mình **không** đủ.

## 2026-09-04 — `GET /api/v1/models` nay Codex đọc được

**FIXED · Thêm ba trường bắt buộc vào mục model: `truncation_policy`,
`support_verbosity`, `experimental_supported_tools`. Kèm `auto_compact_token_limit`.**

**Ai bị ảnh hưởng:** người cấu hình Codex **bằng tay** theo tài liệu, hoặc dùng
tiện ích VS Code, tức không đi qua bộ cài `cam` của chúng tôi. Ai dùng bộ cài
thì **không** bị — nó ghi một catalog cục bộ thay hẳn cho endpoint này.

**Triệu chứng cũ:** Codex không parse nổi **một mục nào** ở đây (`ModelInfo` có
ba trường bắt buộc không phải `Option`, thiếu là hỏng cả mục), nên nó im lặng
rơi về metadata dự phòng của chính nó — **272.000** token ngữ cảnh và **không
nén**. Con số đó lớn hơn trần thật của chúng tôi, nên phiên dài **chắc chắn**
kết thúc bằng `413`, và không có thông báo nào giải thích vì sao.

**Bạn phải làm gì:** không gì cả. Nhưng nếu bạn từng gõ tay `model_context_window`
để đối phó, hãy bỏ nó đi — nay endpoint tự khai đúng, và một con số gõ tay lệch
với máy chủ là cách nhanh nhất để gặp lại `413`.

## 2026-09-04 — bộ cài `1.5.0`: chặn một kết quả tool nuốt trọn ngữ cảnh

**FIXED · Trần cho MỘT kết quả tool: cả cửa sổ (156.385) → 16.384 token.**

Nếu bạn dùng `cam` hoặc `ltt_cai_dat_cli.py` để cấu hình Codex, **hãy cài lại
bộ cài `1.5.0`**. Bản `1.4.0` khai `truncation_policy.limit` bằng cả cửa sổ ngữ
cảnh, tức cho phép **một** kết quả lệnh (đọc tệp, chạy test, `grep` một kho lớn)
chiếm trọn ngữ cảnh trong một lượt.

**Vì sao điều đó dẫn tới `413`:** Codex chỉ kiểm ngưỡng nén **giữa hai lượt**,
không kiểm giữa các lần gọi công cụ trong cùng một lượt
([openai/codex#16033](https://github.com/openai/codex/issues/16033)). Khi một
lượt phình ra, `truncation_policy` là hàng phòng thủ duy nhất còn lại. Để so
sánh: mặc định của chính Codex là 10.000 byte ≈ **2.500 token**.

**Bạn sẽ thấy gì khác:** kết quả một lệnh dài hơn ~64 KB nay bị cắt ở giữa
(giữ đầu và cuối) kèm dòng báo đã cắt, thay vì vào trọn ngữ cảnh. Đọc tệp lớn
thì chia nhỏ — và đó vốn là cách làm việc rẻ hơn.

**Muốn nới:** đặt `tool_output_token_limit` trong `config.toml` của bạn; nó
**đè** giá trị trong catalog của chúng tôi. Nới cao thì bạn nhận lại rủi ro
`413` giữa phiên.

## 2026-09-03 (khuya) — `ltt_llm_vision` lên 88K ngữ cảnh dùng được

**ADDED · Cửa sổ ngữ cảnh dùng được của `ltt_llm_vision`: 28K → 88K.**

Bạn **không phải sửa gì**. Nếu bạn đang tự giới hạn số ảnh hoặc độ dài hội thoại
vì cửa sổ 28K thì nay có thể nới.

```diff
  ltt_llm_vision  context_window   28262  ->  88555
  ltt_llm_vision  auto_compact         -  ->  55787
  ltt_llm         context_window  156385      (KHONG doi)
```

⭐ **Và trường `auto_compact_token_limit` của `ltt_llm_vision` nay mới xuất hiện
lần đầu.** Trước đây nó bị bỏ hẳn khỏi catalog Codex, và việc bỏ đó là **có chủ
ý, không phải sót**: cửa sổ công bố cũ (28.262) **hẹp hơn** một lượt trả lời dài
nhất (32.768), nên không ngưỡng nén nào giữ được lời hứa "nén trước khi chạm
trần" — và ghi một con số bịa vào đó thì Codex sẽ tin nó.

Nâng cửa sổ là thứ làm cho ngưỡng ấy **định nghĩa được trở lại**.

⚠️ **Vision vẫn là một hồ sơ khác `ltt_llm`, và hai con số vẫn độc lập.** Hôm nay
`88.555` tình cờ bằng con số của `ltt_llm` **hôm qua** — đừng đọc sự trùng hợp
đó thành "hai model dùng chung một cửa sổ". Chúng chạy hai `-c` khác nhau và sẽ
lệch lại ở lần nâng kế tiếp.

### `contract_hash` của `text.chat`: `dcf6aa9d…` → `5699a45f…`

Cùng loại với lần đổi trước trong ngày: thứ đổi là **một chuỗi mô tả**
(`smaller 28K` → `smaller 89K`). Không trường nào bị bỏ, không ràng buộc nào
siết vào — một tích hợp đang chạy không hỏng, nó chỉ được phép gửi nhiều hơn.

⚠️ **Hai lần đổi hash trong một ngày là nhiều.** Nếu bạn ghim `contract_hash`
để phát hiện thay đổi hợp đồng thì hôm nay bạn sẽ thấy hai lần báo — cả hai đều
là **nới rộng**, không có lần nào thu hẹp.

## 2026-09-03 (tối) — trần đầu vào nay đếm token **thật**, không phải token ước

**FIXED · `413` từng xảy ra ở khoảng một nửa cửa sổ chúng tôi công bố.**

Bạn **không phải sửa gì**. Nhiều yêu cầu trước đây bị từ chối nay được nhận.

Cổng của chúng tôi từ chối một yêu cầu **trước khi** nó chạm GPU — đánh thức
model chỉ để đếm token thì đã chạm GPU rồi. Phép chặn ấy dùng một phép **ước**
(`số ký tự / 2,5`), và phép ước đó lệch nhiều hơn chúng tôi tưởng:

| nội dung | ước/thật |
|---|---:|
| tiếng Anh văn xuôi | **2,00×** |
| trộn — gần một phiên agent | **1,55×** |
| JSON kiểu Codex gửi | 1,42× |
| mã nguồn | 1,27× |
| tiếng Việt có dấu | 1,26× |

⛔ **Và vì sao nó là một lỗi, không chỉ một sự lãng phí:** chúng tôi cưỡng chế
bằng token **ước**, còn client của bạn đếm token **thật**. Nên con số chúng tôi
công bố — và ngưỡng nén Codex/Claude Code tính ra từ nó — **nằm ở một đơn vị
khác** với thứ chúng tôi từ chối. Không ngưỡng nén nào ở phía bạn ngăn được
`413` khi hai bên đếm bằng hai đơn vị khác nhau.

⇒ Nay khi phép ước vượt trần, cổng hỏi tokenizer **thật của model** rồi mới
quyết. Đo trên production, **cùng một thân request**:

```
truoc:  uoc 175.005  ->  413
sau :   uoc 175.005, that 85.613  ->  200
```

Và chiều còn lại vẫn khoá: một yêu cầu **thật sự** vượt trần vẫn `413`, và con
số trong lỗi nay là con số bạn đối chiếu được với tokenizer của mình:

```
uoc 360.001, that 176.092  ->  413  limit_value 169.984
```

⭐ **Hệ quả cho ai đọc `413`:** trường `thay` trong thân lỗi bây giờ là số token
**thật**, không phải số ước — nên nó khớp với thứ client của bạn đếm được.

⚠️ **Một ca còn lại:** nếu model vừa bị dỡ khỏi GPU (sau ~30 phút không ai gọi),
lượt kế tiếp vẫn được phán xử bằng phép ước — hỏi tokenizer lúc đó sẽ phải nạp
lại model, tức 2,5 phút cho một yêu cầu đang định từ chối. Trong thực tế lượt
đầu của một phiên là lượt nhỏ, nên ca này hiếm; nhưng nó có thật.

## 2026-09-03 — `ltt_llm` lên 156K ngữ cảnh dùng được, và ngưỡng nén đổi công thức

**ADDED · Cửa sổ ngữ cảnh dùng được của `ltt_llm`: 89K → 156K.**

Cửa sổ engine lên `204.800` (đo thật trên card đang phục vụ; bằng chứng ở
`docs/VLM_NOI_BO/NGU_CANH_DAI_2026-09-03.md`). Bạn **không phải sửa gì** — trần
cũ vẫn hợp lệ, chỉ là bạn được nhét vào nhiều hơn.

```diff
  ltt_llm         context_window   88555  ->  156385
  ltt_llm         tran dau vao     96256  ->  169984
  ltt_llm_vision  context_window   28262      (KHONG doi)
```

⚠️ **`ltt_llm_vision` giữ nguyên 28K.** Nó chạy trên một hồ sơ khác, cửa sổ
engine `65.536`, và chưa được đo lại. Đừng suy con số của nó từ con số của
`ltt_llm` — đó đúng là lỗi đã sửa ở mục 01/09 ngay dưới.

> 🔄 **Câu trên đã được thay thế cùng ngày.** Vision *đã* được đo lại vài giờ
> sau và lên `88.555` — xem mục **03/09 (khuya)** ở trên. Giữ nguyên câu cũ vì
> nhật ký ghi *lịch sử*, không ghi *trạng thái*; nhưng đừng hành động theo nó.

**FIXED · Ngưỡng nén (`auto_compact_token_limit`) nay là `cửa sổ − token ra tối
đa`, không còn là `0,8 × cửa sổ`.**

Nếu bạn tự cấu hình Codex/Claude Code bằng tay thay vì dùng công cụ `cam`, hãy
đọc mục này. Công thức `0,8` chừa lại **ít hơn một lượt trả lời dài nhất** giữa
ngưỡng nén và cửa sổ công bố — mà client chỉ kiểm ngưỡng **giữa hai lượt**. Đo
được trên production: một lượt ăn `413` với **101.938** token vào trên trần
**96.256** khi đó, dù client có bật auto-compact.

```diff
- auto_compact_token_limit = 0.8 * cua_so
+ auto_compact_token_limit = cua_so - max_output_tokens
```

Với cấu hình hiện tại: `156385 − 32768 = 123617`.

**FIXED · Bộ cài khai `ltt_llm_vision` bằng cửa sổ của model text.** Cả bản
Windows lẫn bản một-tệp đều ghi `88555` cho **cả hai** model vào catalog của
Codex — tức hứa cho vision gấp **3,1 lần** thật. Nay mỗi model khai cửa sổ của
nó. Cùng lớp lỗi với mục 01/09, chỉ ở một tệp khác.

**FIXED · Bản một-tệp (macOS/Linux) nay đặt `CLAUDE_CODE_MAX_CONTEXT_TOKENS`.**
Bản Windows đã đặt từ 30/08; bản một-tệp thì không, nên khách macOS/Linux nhận
một bộ cài yếu hơn mà không có gì nói ra.

⇒ **Chạy lại công cụ `cam` (hoặc `ltt_cai_dat_cli.py`) rồi mở phiên mới.** Cấu
hình được đọc lúc khởi động, nên phiên đang chạy không tự nhận số mới.

### Về `contract_hash` của `text.chat`: `126dc382…` → `dcf6aa9d…`

`check_api_compat.py` gắn nhãn **BREAKING** cho mọi lần `contract_hash` đổi, và
ở đây nhãn đó **rộng hơn sự thật**. Thứ đổi trong schema là **một chuỗi mô tả**:

```diff
- "`ltt_llm` for text (89K usable input context). ..."
+ "`ltt_llm` for text (156K usable input context). ..."
```

Không trường nào bị bỏ, không `enum` nào hẹp lại, không ràng buộc nào siết vào.
Một tích hợp đang chạy **không hỏng** — nó chỉ được phép gửi nhiều hơn.

⭐ Nhưng chốt vẫn đúng khi bắt phải khai báo: hash phủ cả mô tả **có chủ ý**, vì
mô tả là thứ khách đọc rồi cấu hình theo. Một lần đổi mô tả mà không ai ghi lại
chính là cách `89K` sống sót nhiều ngày sau khi nó hết đúng.

## 2026-09-01 — `ltt_llm_vision` KHÔNG có 89K ngữ cảnh, và chưa bao giờ có

**FIXED · Ngữ cảnh công bố nay đúng theo TỪNG model.**

Trước hôm nay `/api/v1/models` nói với bạn rằng `ltt_llm_vision` có
*"same 89K usable input context"* như `ltt_llm`. **Điều đó sai.** Model đọc ảnh
chạy trên một cửa sổ engine nhỏ hơn một nửa (`65.536` thay vì `131.072`), nên
phần bạn thật sự nhét vào được là **~28K**, không phải 89K.

```diff
  ltt_llm         context_window  88555     (khong doi)
- ltt_llm_vision  context_window  88555     <- LOI HUA SAI
+ ltt_llm_vision  context_window  28262     <- so that
```

**ADDED · Mỗi alias nay tự khai `constraints.context_window` và
`constraints.max_output_tokens`.** Trước đây không alias nào khai, nên trường
`context_window` trong `/api/v1/models` rơi về một hằng số lùi chung là
`60000` — và bạn nhận **hai con số khác nhau trong cùng một phản hồi**: phần
chữ nói `89K`, trường máy đọc được nói `60000`. Nay hai chỗ luôn khớp.

*Có phải sửa gì không?*

- **Nếu bạn dùng `ltt_llm` (văn bản):** **không**. Không con số nào của nó đổi.
- **Nếu bạn dùng `ltt_llm_vision`:** **không cần sửa để chạy tiếp** — hành vi
  của máy chủ **không đổi một chút nào**. Nó vẫn luôn từ chối ở `65.536` như
  trước, và vẫn trả `413` kèm `limit_value` đúng. Thứ đổi là **con số chúng tôi
  công bố**. Nếu bạn từng chỉnh client theo `89K` cho model này thì bạn đã gặp
  `413` rồi; nay bạn có con số đúng để chỉnh lại.

⚠️ Bộ kiểm tương thích của chúng tôi đánh dấu thay đổi này là **BREAKING** vì
`contract_hash` của `text.chat` đổi. Chúng tôi giữ nguyên nhãn đó thay vì hạ
xuống cho đẹp: một con số công bố đổi **là** thứ tích hợp cảm nhận được. Nhưng
hướng của nó là **sửa một lời hứa sai**, không phải thu hẹp một năng lực — không
có lượt gọi nào từng thành công mà nay hỏng.

## 2026-09-01 — `speech.ltt` MỞ, và `output_schema` nói ra loại tệp

**ADDED · `speech.ltt` phục vụ thật.** Văn bản tiếng Việt thành giọng nói, chế
độ `ASYNC_JOB`. Giá theo **giây tiếng thật sự sinh ra**, không theo ký tự gửi
lên: nền tảng giữ một trần ước cao rồi hoàn phần dư khi job xong — cùng hình
dạng `text.chat`. Trần **1.500 ký tự** mỗi lượt là trần **chất lượng**, không
phải hiệu năng.

**ADDED · `output_schema` của mọi trường artifact nay có `media`.**

```diff
  "audio_key": {
    "type": "artifact",
+   "media": "audio"
  }
```

Giá trị: `"image"`, `"video"`, `"audio"`.

*Có phải sửa gì không?* **Không.** Đây là một trường **thêm vào**; client đang
đọc `type` không bị ảnh hưởng, và không trường nào bị bỏ hay đổi nghĩa.

*Vì sao vẫn nằm ở đây?* Vì nó đổi `contract_hash` của **tám** tool — mọi tool
trả về artifact. Ai đang lưu hash để phát hiện hợp đồng dịch chuyển sẽ thấy nó
dịch, và **đó là đúng ý**: hợp đồng có dịch thật, chỉ là dịch theo hướng nới ra.
Đã chạy `check_api_compat --accept`.

*Vì sao thêm?* `{"type": "artifact"}` không nói được nên chờ WAV hay PNG. Nó
không thành vấn đề chừng nào mọi tool đều trả ảnh — và điều đó đúng cho tới
`speech.ltt`. Cùng chỗ thiếu ấy khiến **chế độ thử trả PNG cho mọi loại**:
người tích hợp bật sandbox cho một tool âm thanh sẽ tải về một tệp `.png` phục
vụ dưới `image/png` từ một trường lược đồ gọi là audio, rồi viết tích hợp quanh
nó — và chỉ phát hiện khi đổi sang khoá thật, tức đúng lúc bắt đầu trả tiền.

**FIXED · chế độ thử của tool âm thanh trả WAV thật.** Mẫu được **dựng** bằng
`wave`, không nhúng byte.

⚠️ **Chưa sửa cho video.** `video.upscale` và `video.subtitle` đã mở từ 29/08 và
chế độ thử của chúng **vẫn** phát PNG — đây là một lỗi **có từ trước**, không
phải lỗi mới. Một MP4 tối thiểu hợp lệ cần `ftyp` + `moov` với sample entry
thật, nên nó là một việc riêng. Đã khai vào `media.CHUA_CO_MAU` kèm lý do, và
`tests/test_377` từ chối mọi loại media không có mẫu **và** không được khai —
nên chỗ thiếu này ở lại chỗ nhìn thấy được thay vì mục ra thành "sandbox nó vốn
thế".

## 2026-08-30 (b) — nhiều tệp cho một tham số, và ba tham chiếu Seedance mở

**ADDED — tham số media dạng mảng, và `video.generate` nhận thêm ba đường tham
chiếu.** Client không hỏi tới thì không thấy gì đổi; không phá vỡ tương thích.

### Nhiều tệp cho một tham số

Trước đây tầng API chỉ giải được **một** tệp cho một tham số. Đó là một giới hạn
của **nền tảng**, không của app — nó khoá `image_keys` ở **ba** tool cùng lúc.

Nay một tham số dạng mảng nhận tối đa **8** id:

```json
{"tool": "video.generate",
 "input": {"prompt": "...", "image_keys": ["up_a", "job_x.image_keys.0"]}}
```

Mỗi phần tử có thể là **upload id hoặc artifact id**, trộn được.

⛔ **Mảng không phải đường vòng qua kiểm quyền.** Mỗi phần tử đi qua **đúng**
đường mà một tham số đơn đi: cùng hàm giải, cùng hai cổng (chủ sở hữu + danh
sách trắng hợp đồng đầu ra). Có test chốt đúng điều đó.

⚠️ **Trần 8 là có chủ ý.** Mỗi phần tử là một lượt tra CSDL chạy **trước** khi có
bất kỳ khoản tiền nào; không có trần thì một danh sách nghìn id là cách bắt máy
chủ làm việc miễn phí — và nó không hiện ra như một cuộc tấn công, nó hiện ra
như một request chậm.

### `video.generate` mở ba tham chiếu

`image_keys` · `video_key` · `audio_key` — trước đó hoãn vì chưa chứng minh được
ownership. Bằng chứng nay **là đường mã**, không phải lời hứa: mọi id đi qua
`resolve_upload_reference`, và hàm đó đòi đủ hai cổng.

⛔ **`refs` vẫn hoãn, và lý do khác hẳn ba cái kia.** Nó là `json`, không phải
kiểu media — không cổng nào kiểm nó được, vì không ai biết trong đó có gì. Mở
`refs` là mở một trường tự do đi thẳng tới nhà cung cấp; đó là một hợp đồng khác,
không phải một bậc tiếp theo.

*Phải làm gì:* không gì cả. Nếu bạn từng phải tải một artifact về rồi tải lên lại
để dùng nó ở tool sau, giờ không cần nữa.

## 2026-08-30 — `speech.ltt`: giọng nói tiếng Việt, có hợp đồng công khai

### ADDED

Tool **`speech.ltt`** (app `ltt_voice`, `ASYNC_JOB`) — chuyển văn bản thành
giọng nói tiếng Việt hoặc tiếng Anh, bằng giọng dựng sẵn hoặc bằng **giọng của
chính khách** đã nhân bản.

Chưa mở trong công tắc người vận hành (`LTT_PUBLIC_API_TOOLS`). Ba cổng
fail-closed của Q92 nguyên vẹn; mục này chỉ nói rằng **hợp đồng đã có**.

Hai tham số công khai:

| Tham số | Ý nghĩa |
|---|---|
| `text` | Nội dung cần đọc. Việt, Anh, hoặc trộn. Tối đa **1.500 ký tự** một lượt. |
| `voice_id` | Mã giọng của khách, dạng `vc_…`. Bỏ trống thì dùng giọng dựng sẵn. |

### `voice_id` là một lời hứa, không phải một khoá tra cứu

Mã giọng **ổn định qua mọi lần nâng cấp engine**. Biểu diễn engine (speaker
embedding + reference codes) là dữ liệu nội bộ của nền tảng, nằm ở một bảng
khác, và **không bao giờ đi ra API**. Nâng model = thêm một dòng biểu diễn mới
và đổi cờ; `voice_id` của khách không đổi, tích hợp không phải sửa gì.

⇒ Đây là điều kiện để một ngày nào đó thay engine mà không phá khách. Nếu
`voice_id` từng là một khoá trỏ thẳng vào dữ liệu của model thì ngày nâng cấp là
ngày mọi tích hợp gãy, vì một lý do hoàn toàn nội bộ.

### 🔴 Trần 1.500 ký tự là trần CHẤT LƯỢNG, không phải trần kỹ thuật

Đo thật ngày 30/08 trên phần cứng của nhà: **3.000 ký tự vẫn sinh ra được**,
trong 17,6 giây, không lỗi. Trần thấp hơn thế vì chất lượng, không vì năng lực —
upstream báo giọng bắt đầu **trôi vùng miền** từ khoảng ngưỡng đó
(`pnnbao97/VieNeu-TTS#168`, người thử xác nhận sau khi tác giả đã sửa một lượt).

Văn bản dài hơn thì **chia thành nhiều lượt gọi**. Đó không phải một hạn chế kỹ
thuật ta chưa gỡ được — đó là cách giữ giọng đồng nhất.

### Tham số sinh mẫu cố ý KHÔNG có trong hợp đồng

`temperature`, `top_k`, `top_p` và họ hàng **không** là tham số công khai, và sẽ
không trở thành. Hai lý do độc lập:

1. Engine cache CUDA graph theo `(batch, temperature, top_k, top_p)`. Mỗi tổ hợp
   mới là một graph mới cộng một bộ đệm tĩnh trên card — tức một khách chỉnh ba
   con số đó có thể làm nở bộ nhớ GPU của cả hệ thống.
2. `temperature` cao làm **lệch tông giữa các đoạn** trong một bài dài.

Đây là tham số chất lượng sản phẩm, và đổi chúng phải qua cổng đo như đổi model.

### Tiền: theo giây tiếng nói **thật sự sinh ra**

Giữ chỗ theo số ký tự (sau chuẩn hoá), quyết toán theo **thời lượng đo bằng
`ffprobe`** trên chính tệp đã sinh. Phần giữ dư hoàn ngay khi job xong. Không đo
được thời lượng ⇒ **hoàn đủ, thu 0** — thu tiền không bằng chứng tệ hơn mất một
ít tiền.

### Đóng dấu chìm: có, và đã đo lại được

Mọi tệp ra mang một watermark không nghe thấy. Đây là một lời hứa **đã kiểm**:
dấu được lấy lại từ chính sóng âm của tệp đã sinh, kể cả tệp dùng giọng nhân
bản.

⚠️ Ghi ra vì nó suýt là một lời hứa sai: gói `perth` mà SDK upstream khai trên
PyPI **không phải** thư viện watermark (nó là một tiện ích threading), và
upstream nuốt lỗi đó trong im lặng, nên mặc định `apply_watermark=True` mà không
có dấu nào được áp. Bộ cài của nhà thay bằng `resemble-perth` và dịch vụ **từ
chối khởi động** nếu watermarker không nạp được.

---

## 2026-08-30 — `video.generate` (Seedance) có hợp đồng công khai

**ADDED — tool `video.generate`, và model đầu tiên công bố `constraints` riêng.**
Client không hỏi tới thì không thấy gì đổi; không có thay đổi nào phá vỡ tương
thích.

⚠️ **Có hợp đồng ≠ gọi được.** Ba cổng fail-closed của Q92 vẫn nguyên: tool này
chỉ phục vụ khi operator thêm nó vào `LTT_PUBLIC_API_TOOLS`. Hiện **chưa bật**.

### Cái mới: ràng buộc **theo từng model**, không phải một tập hợp nhất

`GET /api/v1/models` nay trả `constraints` cho mỗi model:

```json
{
  "name": "seedance-2.0-mini",
  "constraints": {
    "resolutions": ["480p", "720p"],
    "durations": [4, 5, 6, 8, 10, 12, 15],
    "aspect_ratios": ["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"],
    "supports_seed": true,
    "prompt_controls": ["camera", "motion", "visual_style"]
  }
}
```

`seedance-2.0` nhận thêm `1080p` và `4k`; hai model kia thì không.

⭐ **Vì sao không publish một tập hợp nhất.** Hợp nhất sẽ nói với bạn rằng
`seedance-2.0-mini` + `4k` là hợp lệ. Bạn gọi, trả tiền, rồi nhà cung cấp từ
chối. Đó chính là lý do tool này bị đóng suốt từ đầu — và nó được mở bằng cách
**giải** vấn đề đó, không phải bằng cách hạ tiêu chuẩn.

### Tổ hợp sai bị từ chối **trước khi tiền chuyển**

```
POST /api/v1/quotes   {"model": "seedance-2.0-mini", "resolution": "4k"}
400  resolution: model 'seedance-2.0-mini' does not accept '4k'.
     Allowed: 480p, 720p. See constraints in GET /api/v1/models.
```

Trước `quotes`, trước giữ chỗ, trước khi chạm nhà cung cấp. Bạn **không** bị thu
tiền cho một lượt sẽ bị từ chối.

### Bốn tham chiếu media hoãn có ghi

`image_keys`, `video_key`, `audio_key`, `refs` **không** có trong hợp đồng công
khai đợt này — chúng chưa chứng minh được ownership + vòng đời qua
`upload_sessions` ở đường API. Mở từng cái khi có bằng chứng, chứ không mở rồi
kiểm sau. `image_key` (một ảnh tham chiếu) **có** trong hợp đồng.

*Phải làm gì:* không gì cả, trừ khi bạn muốn dùng tool này khi nó mở. Lúc đó:
đọc `constraints` của model trước khi dựng request.

## 2026-08-30 — cửa sổ ngữ cảnh công bố: sửa một con số nói sai

**FIXED — mô tả model `ltt_llm` / `ltt_llm_vision` nói `131K` / `64K`, nay nói
`89K`.** Không có gì trong hành vi máy chủ đổi; thứ đổi là **con số chúng tôi
nói với bạn**, và con số cũ sai theo hướng gây hại.

*Cái gì đổi:* `contract_hash` của `text.chat` chuyển từ `44dc637a5e4cc643` sang
`0f21e0c6522a0ac8`. Chỉ phần **mô tả** đổi — không tham số nào thêm, bớt hay đổi
kiểu; không mã lỗi nào đổi; giá không đổi.

*Có phá vỡ tương thích không:* **Không.** Nếu bạn ghim `contract_hash` để phát
hiện thay đổi hợp đồng thì bạn sẽ thấy nó chuyển — đó chính là việc của nó. Mã
đang chạy không phải sửa một dòng nào.

*Phải làm gì:* **Nếu bạn đang lấy giới hạn ngữ cảnh từ mô tả model, hãy đọc lại
con số.**

### Vì sao con số cũ sai, và sai theo hướng nào

`131.072` là cửa sổ của **engine**. Trần đầu vào mà `/api/v1` thực thi là
**96.256** — thấp hơn, vì phải chừa chỗ cho câu trả lời dài nhất (32.768) và cho
sai số của phép **ước** token. Con số chúng tôi công bố cho client còn thấp hơn
nữa, **88.555**, chừa thêm 8 %.

⛔ Nên "131K context" là một **lời hứa vượt quá thực tế 42 nghìn token**. Khách
đọc nó, nhét 120K token vào, và ăn **413** giữa hội thoại — không có gì trên
trang nói cho họ biết vì sao. Còn `64K` cho `ltt_llm_vision` thì không khớp con
số nào cả; nó chưa bao giờ đúng.

⭐ Cùng lúc, năm chỗ khác trong tài liệu nói `model_context_window = 65000` —
tức bắt bạn **tự giới hạn thấp hơn thật 24 nghìn token**. Tất cả nay sinh ra từ
một nguồn duy nhất (`apps/ltt_llm/ngan_sach.py`), và có phép kiểm đối chiếu; một
con số gõ tay ở tài liệu bán hàng là một lời hứa, nên nó không được phép tồn tại
ở chỗ thứ hai.

### Hai thiết lập client **nên thêm** (không bắt buộc, nhưng bạn sẽ muốn)

Cả hai client phổ biến đều **đoán sai** cửa sổ của chúng tôi nếu bạn không khai:

| Client | Khai gì | Không khai thì sao |
|---|---|---|
| **Codex** | `model_catalog_json` trỏ tới tệp catalog | Codex cảnh báo *"Model metadata for `ltt_llm` not found"*, rồi mượn **tên một model OpenAI** cho các lượt phụ; cổng của chúng tôi từ chối tên lạ (fail-closed) và bạn thấy hội thoại dài **im lặng** |
| **Claude Code** | `CLAUDE_CODE_MAX_CONTEXT_TOKENS=88555` | Claude Code giả định **200.000** token, nên auto-compact **không bao giờ nén kịp** và bạn ăn 413 giữa chừng |

Chi tiết và đoạn cấu hình đầy đủ ở `HUONG_DAN_CAM_CLI.md` §2.1–§2.4, hoặc dùng
công cụ cắm 1.3.0 — nó đặt sẵn cả hai.

## 2026-08-29 — hai tool video mở ra `/api/v1` (H35.10)

**ADDED — `video.upscale` và `video.subtitle`.** Client không hỏi tới thì không
thấy gì đổi; không có thay đổi nào phá vỡ tương thích.

- `video.upscale` — nâng video lên 1080p/1440p/4K. 30 credit mỗi phút ở 1080p
  preset `fast`; 1440p ×1,8, 4K ×4, preset `quality` ×2,5, `stabilize` ×1,2,
  `smooth_motion` ×2,2. `preview` render 8 giây đầu và **chỉ thu tiền 8 giây
  đó** — dùng nó để thử cấu hình trước khi trả cho cả video.
- `video.subtitle` — khắc transcript **bạn đã có** vào video. 5 credit mỗi phút
  ở `standard`; `draft` ×0,6, `high` ×1,5. ⚠️ Tool này **không phiên âm hộ**;
  bạn phải gửi transcript.

⭐ **`duration_s` không còn là tham số của bạn.** Trước đây hai tool này đóng
đúng vì lý do đó: giá phụ thuộc thời lượng **do người gọi khai**, còn worker đo
lại thật rồi nâng giữ chỗ — nghĩa là một báo giá đã ký vẫn có thể quyết toán
cao hơn (Q84). Nay máy chủ **đo** thời lượng từ chính tệp bạn tải lên, trước khi
tính giá.

*Phải làm gì:* **đừng gửi `duration_s`** — nó đã bị ẩn khỏi hợp đồng và sẽ bị từ
chối. Lấy giá từ `POST /quotes` như mọi tool khác. Nếu tệp không đọc được thời
lượng, `/quotes` trả `400` thay vì đoán một con số.

⭐ Và một bảo đảm mới, áp cho **mọi** tool: giữ chỗ của một job đến từ `/api/v1`
nay **niêm phong** ở con số trên báo giá. Nếu worker tính ra giá cao hơn, phần
chênh là variance nội bộ của nền tảng — bạn không bị thu thêm, và job của bạn
**không** bị huỷ vì chênh lệch đó.

`video.short_clips` **vẫn đóng**: nó còn cần một trần đồng thời GPU (H35.10c).

---

## 2026-08-28 — public input cap 65K (Q116)

**BREAKING — hạ trần input public của `ltt_llm` từ 81.000 xuống 65.000 token.**

Arm 81K không ổn định với payload code-like (80K ước lượng thành 88.224 token,
120,322s). Mốc 65K đã lặp lại trên RTX 3090, quality PASS, khoảng 82,3 giây.
Engine vẫn giữ context `131072`, output `32768`, `parallel=1`.

*Phải làm gì:* cập nhật client profile `model_context_window = 65000`; request
trên 65K phải chuyển sang stream/job hoặc bị từ chối trước GPU/credit.

---

## 2026-08-28 — public input cap 81K

**BREAKING — hạ trần input public của `ltt_llm` từ 90.000 xuống 81.000 token.**

Q115 chốt mốc 81K sau benchmark warm/cold trên RTX 3090. Engine vẫn giữ context
`131072`, output `32768`, và `parallel=1`; đây là hàng rào vận hành để giữ biên
Cloudflare, không phải thay đổi cửa sổ engine.

*Phải làm gì:* cập nhật client profile `model_context_window = 81000`; request
trên 81K phải chuyển sang stream/job hoặc bị từ chối trước GPU/credit.

---

## 2026-08-27

**BREAKING — nâng cửa sổ text Qwen lên 131K, public input cap 90K.**

*Có phá vỡ tương thích không:* request hợp lệ trước đây vẫn chạy; chỉ các client
đang tự giả định trần 64K cần cập nhật profile lên 90K. Model vision giữ 64K.

*Cái gì đổi:* `qwen38-api` dùng engine `-c 131072`, KV `q8_0/q8_0`, output cap
`32768`; gateway từ chối input trên `90000` bằng 413. Mốc được xác nhận bằng
warm/combined benchmark trên RTX 3090 (Nexus job
`job_01M11M0DQXMFFNNAM6JJ8RBGQ2`).

*Phải làm gì:* cập nhật client profile `model_context_window = 90000`; không gửi
request full 131K qua public API. Ops LAN và vision không thay đổi.

---

## 2026-08-26

**ADDED — ba phương thức cắm Codex/Claude, CamCLI 1.1.0.**

*Có phá vỡ tương thích không:* **không.** API `/api/v1` và các URL tải EXE cũ
không đổi. Bản 1.0 tiếp tục chạy được; trang web chỉ ưu tiên bản mới nhất.

*Cái gì đổi:* khu Dev API nay công bố ba đường dùng chung một lõi cấu hình:

1. EXE có giao diện, cho chọn riêng từng bề mặt;
2. ZIP + BAT tự xin Administrator, chạy console thật và không cần Python/GUI;
3. hướng dẫn thủ công đầy đủ.

Bản 1.1 đọc lại file, biến môi trường và registry để xác nhận từng hạng mục;
không còn coi nút đã chạy hay cờ trạng thái cũ là bằng chứng thành công. GUI có
đồng hồ tiến độ, bắt lỗi cầu nối và hỗ trợ riêng Codex CLI/Codex VS Code.

*Phải làm gì:* tải lại bản 1.1.0 từ `/developers/cli` hoặc
`/huong-dan/cong-cu`. Nếu chính sách máy chặn EXE GUI chưa ký số, dùng gói ZIP +
BAT hoặc làm tay. Sau khi cắm biến môi trường, đóng và mở lại VS Code/terminal.

## 2026-08-25

**ADDED — cổng lập trình viên: điều hướng gom nhóm, trang cắm chọn-một-bề-mặt,
danh mục công cụ gập được.**

*Có phá vỡ tương thích không:* **không.** `/api/v1` không đổi một byte. Đây
hoàn toàn là bề mặt HTML của `/developers` và `/huong-dan`.

*Phải làm gì:* **không gì cả.** Mọi URL cũ vẫn trả `200` — sáu trang bị hạ khỏi
thanh điều hướng (`projects`, `playground`, `jobs`, `quickstart`, `privacy`,
`notifications`) **vẫn còn nguyên route** và tìm lại được từ dải mục con của
trang cha. `test_303` chốt cả hai chiều.

Ba việc, mỗi việc có một số đo đứng sau:

| Đổi gì | Trước | Sau |
|---|---|---|
| Điều hướng | 16 mục phẳng, cuộn ngang | 10 mục, 3 nhóm, thanh bên |
| Trang cắm | 5 bề mặt xếp chồng, 133 dòng | 1 ô chọn → 1 địa chỉ + 1 tên model trên màn hình |
| Danh mục công cụ | bảng phẳng, phải mở trang khác mới thấy tham số | thẻ gập, bảng tham số **sinh từ `input_schema`** ngay trong thẻ |

⛔ Cái thứ hai là **sửa một cái bẫy**, không phải làm đẹp. Bản xếp chồng đặt hai
giá trị dễ sai nhất của cả khu API cạnh nhau, không có gì nói cái nào của ai:
địa chỉ `/api/v1` (Codex) và `/api` (Claude Code, Desktop) lệch **đúng bốn ký
tự**; tên model `ltt_llm` và `ltt-llm-claude-compat` chỉ khác nhau ở **một bề
mặt duy nhất**. Chép nhầm thì Codex nhận `404`, hoặc nút gửi của Claude Desktop
**im lặng không làm gì cả**.

**ADDED — công cụ cắm `.exe` nay có mặt trong khu đã đăng nhập.**

Bộ cài đã nằm trên máy chủ từ 25/08 và `/tai/cong-cu-cam` vẫn trả `200`, nhưng
**không một trang nào trong `/developers` trỏ tới nó** — nên với người đã đăng
nhập, công cụ coi như không tồn tại. Nay nó đứng trên cùng `/developers/cli`,
kèm số phiên bản, dung lượng và SHA-256 lấy từ **chính tệp đang phục vụ**.

---


**FIXED — `image.ltt`: tài liệu nói SAI hành vi của `image_key`.**

*Có phá vỡ tương thích không:* **không.** Mã máy chủ không đổi một dòng. Thứ đổi
là **lời mô tả** — nó đang nói sai.

*Cái gì sai:* mô tả công khai ghi *"ignored for t2i"*. Máy chủ **không bỏ qua** —
nó **từ chối**:

```python
if che_do == "t2i" and refs:
    raise LoiTaoAnh('Chế độ t2i không nhận ảnh tham chiếu.')
```

*Phải làm gì:* nếu mã của bạn gửi kèm `image_key` ở chế độ `t2i` vì tin rằng nó
được bỏ qua — **bỏ trường đó đi**. Lượt gọi đó đang hỏng, và nó hỏng ngay từ
lượt đầu chứ không phải mới hỏng.

⛔ Vì sao đáng ghi thành một mục: một tài liệu nói *"bị bỏ qua"* trong khi máy
chủ **từ chối** không phải một câu chữ chưa chuẩn — nó là một chỉ dẫn khiến khách
viết mã hỏng, và họ sẽ đi tìm nguyên nhân ở phía họ.

---

**ADDED — `x-ltt-only-when`: khai điều kiện dùng của tham số bằng DỮ LIỆU.**

*Có phá vỡ tương thích không:* **không.** Nó là khoá mở rộng theo quy ước `x-`
của JSON Schema; mọi bộ kiểm tra schema **bỏ qua** khoá lạ.

```json
"image_key": {
  "type": "string",
  "x-ltt-only-when": {"mode": ["edit", "subject"]}
}
```

*Phải làm gì:* không phải làm gì. Nếu bạn sinh client từ đặc tả, bạn **có thể**
đọc khoá này để biết trường nào chỉ hợp lệ ở chế độ nào.

*Vì sao thêm:* điều kiện đó trước nay chỉ nằm trong một câu tiếng Anh giữa
`description`. Trang tài liệu không có cách nào lọc theo, và **bộ sinh ví dụ
không biết mà tránh** — nó đã dựng ra một thân tự mâu thuẫn (`mode: "t2i"` kèm
`image_key`) mà máy chủ sẽ từ chối. Một ví dụ mẫu dạy sai thì mọi người chép
theo.

⚠️ `contract_hash` của `image.ltt` đổi `93dbcde993e11c2b` → `fb38cff7d6272b32`.
Nếu bạn đang lưu dấu vân tay để phát hiện hợp đồng đổi thì đây là lý do.

---

## 2026-08-24

**ADDED — `text.chat`: trần `max_tokens` 16.384 → 32.768.**

*Có phá vỡ tương thích không:* **không.** Đây là **nới rộng**. Mọi giá trị hợp lệ
trước đây vẫn hợp lệ; chỉ có thêm giá trị mới được chấp nhận.

*Phải làm gì:* không phải làm gì. Nếu bạn đang tự kẹp `max_tokens` xuống 16.384
để tránh lỗi thì nay bỏ được.

*Vì sao đổi:* **Claude Code gửi `max_tokens: 32000` mặc định**, và người dùng gần
như không có cách nào đổi con số đó. Với trần cũ, Claude Code **hoàn toàn không
cắm được** — phát hiện 24/08 khi cắm thật lần đầu (H38/L2).

*Vì sao an toàn:* `llama.cpp` cấp KV cache cho **toàn bộ** cửa sổ `-c 65536` ngay
lúc nạp model, nên VRAM **không đổi** dù trần token ra là 16K hay 32K. Số đo 19,4
GB vốn đã là số của một cửa sổ 64K đầy.

⚠️ **Vào và ra vẫn chia nhau cùng cửa sổ 65.536.** Nên trần thật của một lượt là
`min(32.768, 65.536 − token_vào − 2.048)`. Một lượt có 50.000 token vào chỉ còn
~13.400 token ra, và nền tảng **tự kẹp** thay vì từ chối — `max_tokens` là một
**trần**, không phải một lượng đặt hàng, và tiền vẫn tính theo token **thật sự
sinh ra**.

⛔ Trần của `POST /api/v1/chat/completions` **không** đổi và vẫn **từ chối** thay
vì kẹp. Lý do của nó khác hẳn: trần 100 giây của Cloudflare cho một lượt gọi đồng
bộ. Kẹp `max_tokens` không cứu được một lượt chạy quá lâu.

🔴 **Bổ sung 25/08 — ảnh chụp hợp đồng vàng bị bỏ quên mất một ngày.**
`tests/golden/public_api_catalog_v1.json` vẫn ghi `maximum: 16384` cho tới
25/08, nên `test_181` và `test_187` **đỏ trên nhánh** suốt thời gian đó mà không
ai thấy — vì `gate --quick` **không chạy pytest**, và cả hai phiên đang làm đều
chạy `--quick` trước khi deploy.

⭐ Bài học, và nó không phải "nhớ chạy gate đầy đủ": **thay đổi hợp đồng có ba nơi
phải khớp** — mã (`MAX_TOKENS_TRAN`), tài liệu (mục này), và ảnh chụp vàng. Ghi
được hai, quên một, thì phần bị quên chính là phần *duy nhất* biết tự la lên.
Đã chốt lại bằng `python tools\sinh_golden_api.py --ghi`; `contract_hash` của
`text.chat` đổi `32d617ca0c0130d2` → `9d866077c00f7e90`.

---

## v1 — chưa phát hành ra ngoài

Toàn bộ bề mặt `v1` được xây trong Public API V2 + Extension Pack và **chưa mở
cho khách bên ngoài**, nên không có mục BREAKING nào ở đây: chưa có tích hợp nào
để phá. Danh sách dưới đây là những gì `v1` **hứa** kể từ khi đóng băng.

### ADDED — 2026-08-24 · `image.ltt` mở cho khách, và giá **giảm một phần ba**

**Cái gì đổi.** Tool `image.ltt` (model ảnh chạy trên máy của chúng tôi) nay có
trong `LTT_PUBLIC_API_TOOLS` và gọi được. Cùng lúc, giá giảm:

| | Trước | Nay |
|---|---|---|
| Ảnh từ mô tả (`t2i`) | 5 credit | **3 credit** |
| Ảnh có ảnh tham chiếu (`edit`, `subject`) | 15 credit | **9 credit** |

Phiên bản bảng giá: `ltt-image-2026-08-24b`. Giá công bố ở `/gia-api`, và kết quả
job kèm `phien_ban_gia` để bạn đối chiếu đúng bảng đã sinh ra hoá đơn đó.

**Có phá vỡ tương thích không.** Không. Thêm một tool và **giảm** giá.

**Phải làm gì.** Không phải làm gì. Nhưng hai điều nên biết trước khi dùng:

1. **Bạn trả cho ảnh nhận được, không phải ảnh đã xin.** Xin `count: 4` mà chỉ
   sinh được 2 thì trả tiền 2 — phần chênh hoàn ngay khi job xong. Trước bản này
   trường hợp đó **thu trọn phần đã giữ**; đó là một lỗi, và nó đã được sửa.
2. **`subject` giữ được *ai/cái gì*, không dựng lại được *đang làm gì*.** Model
   chép cả tư thế của ảnh tham chiếu. Prompt kiểu *"người ở ảnh 1 đang bế con mèo
   ở ảnh 2"* sẽ ra đúng người và đúng con mèo, nhưng có thể giữ nguyên tư thế cũ.

⚠️ **Nó không phải model đẹp nhất chúng tôi có, và chúng tôi không nói thế.** Nó
là model **của nhà**: rẻ hơn, chạy trên phần cứng của chúng tôi. Ảnh cần **chữ
tiếng Việt có dấu** thì dùng `image.thumbnail` — `image.ltt` vẽ sai dấu, và đó là
giới hạn đã biết chứ không phải lỗi sẽ sửa.

---

### ADDED — 2026-08-23 · hai cửa streaming cho CLI viết mã

**Cái gì đổi.** Bề mặt có thêm **hai route** và chế độ thi hành thứ tư,
`STREAM` (Q107):

| Route | Giao thức | Client |
|---|---|---|
| `POST /api/v1/messages` | Anthropic Messages (SSE) | Claude Code CLI, Claude Desktop |
| `POST /api/v1/responses` | OpenAI Responses (SSE) | Codex CLI, tiện ích Codex VS Code |

`GET /api/v1/capabilities` nay liệt kê thêm hai khu vực `messages` và `responses`.

**Có phá vỡ tương thích không.** **Không.** Client không hỏi tới thì không thấy,
và cả hai vẫn đứng sau đúng ba cổng của Q92.

**Phải làm gì.** Trỏ công cụ của bạn vào — **hai địa chỉ khác nhau bốn ký tự**:

```
Codex          base_url = https://app.lttstudios.com/api/v1   (no ghep them /responses)
Claude Code    ANTHROPIC_BASE_URL = https://app.lttstudios.com/api   (no ghep them /v1/messages)
```

Cấu hình sẵn cho cả ba công cụ ở **`/developers/cli`**.

**Ba điều khác cửa `chat/completions`:**

1. **Bắt buộc `"stream": true`.** Muốn một cục JSON thì dùng
   `POST /api/v1/chat/completions`.
2. **Không đòi `Idempotency-Key`.** Đo thật: không CLI nào gửi nó — Codex không,
   Claude Code không, SDK OpenAI tự sinh rồi vứt đi. Đòi nó nghĩa là tính năng
   không tồn tại.
3. **Không có trần `max_tokens` theo thời gian.** Trần 4.095 của cửa đồng bộ
   sinh ra từ giới hạn 100 giây của Cloudflare, mà đồng hồ đó đếm thời gian chờ
   **byte đầu tiên** — luồng đang chảy thì không bị đếm.

⚠️ **Tính tiền khác, và bạn nên biết trước.** Không có khoá idempotency thì thứ
giữ tiền là **thu theo token đã thật sự sinh ra**: bỏ luồng giữa chừng thì trả
đúng phần đã sinh, và **thử lại là sinh mới, tức là trả thêm**. Đó là cách OpenAI
và Anthropic tính. Hàng rào còn lại là hạn mức chi tiêu ngày và trần ngân sách
của chính bạn.

---

### ADDED — 2026-08-23 · cửa đồng bộ `POST /api/v1/chat/completions`

**Cái gì đổi.** Bề mặt có thêm một route và một **chế độ thi hành thứ ba**,
`SYNC_BILLED` (Q106): trả lời ngay trong request, **có thu tiền**, **bắt buộc
`Idempotency-Key`**, **không có quote**, không đẩy vào hàng đợi, trần 90 giây.
`GET /api/v1/capabilities` nay liệt kê thêm khu vực `chat`.

**Có phá vỡ tương thích không.** **Không.** Client không hỏi tới thì không thấy.
Route đứng sau đúng ba cổng của Q92 như mọi thứ khác — `LTT_PUBLIC_API_TOOLS`
chưa có `text.chat` thì gọi vào vẫn bị từ chối.

**Phải làm gì.** Không ai phải làm gì. Ai muốn dùng thì trỏ `base_url` của SDK
OpenAI vào `/api/v1` và thêm header `Idempotency-Key` cho **từng lượt gọi** —
SDK của OpenAI **không tự gửi** nó. Chi tiết ở `DEVELOPER_GUIDE.md` §1b.

---

### FIXED — 2026-08-23 · `text.chat` khai `messages` là mảng, không phải object

**Cái gì đổi.** `contract_hash` của `text.chat` đổi từ `f6ff632ee8371fa9` sang
`32d617ca0c0130d2`. Trong lược đồ công khai, `messages` và `tools` đổi kiểu từ
`object` sang `array`, và `tool_calls` ở đầu ra cũng vậy.

**Có phá vỡ tương thích không.** Nhãn hình thức là BREAKING vì `contract_hash`
đổi, nhưng thực chất đây là **sửa một thứ chưa từng dùng được**. Cửa job của
`text.chat` **từ chối mọi input hợp lệ** kể từ lúc dựng — kể cả đúng ví dụ mà
trang tài liệu in ra:

    POST /api/v1/jobs  {"tool": "text.chat", "input": {"messages": [...]}}
    -> 400 invalid_request: messages must be an object.

**Vì sao.** Bảng kiểu của `ToolSpec` không có cách nào nói *"một mảng JSON"*:
chỉ có `json`, và `json` phơi ra công khai là `object`, rồi bộ kiểm đòi một
`dict`. `messages` là một **list**. Đã thêm kiểu `json[]` vào bảng, **không** nới
lỏng `object` cho nhận cả list — nới lỏng sẽ làm yếu bộ kiểm của **mọi** tool
khác để chiều một tool.

**Phải làm gì.** Không ai phải làm gì: `LTT_PUBLIC_API_TOOLS` trên production vẫn
rỗng, nên chưa từng có khách gọi được `text.chat`. Lỗi này lọt qua vì không có
test nào đối chiếu **ví dụ đã công bố** với **bộ kiểm thật**; nay `test_199` và
`test_256` làm đúng việc đó.

---

### BREAKING — 2026-08-23 · alias model `pro` của `image.generate` bị gỡ

**Cái gì đổi.** `image.generate` không còn nhận `model: "pro"`. Ba alias còn lại
(`standard`, `standard-lite`, `enhanced`) không đổi.

**Có phá vỡ tương thích không.** Về hình thức **có** — `contract_hash` của
`image.generate` đổi từ `f6fd70a8e5a91489` sang `d8d957479035c7c8`. Trên thực tế
**không có tích hợp nào hỏng**: `LTT_PUBLIC_API_TOOLS` trên production vẫn rỗng,
nên chưa từng có khách gọi được `image.generate`. Ghi nhãn BREAKING vì hình thức
mới là thứ bánh cóc đo được, và hạ nhãn cho vừa hoàn cảnh là cách một lần sau
người ta hạ nhãn cho một thứ **có** khách.

**Phải làm gì.** Không ai phải làm gì hôm nay. Khi mở `image.generate` cho khách,
tài liệu sẽ chỉ liệt kê ba alias.

**Vì sao gỡ — lý do kinh tế, không phải kỹ thuật.** Đo 23/08/2026: giá vốn
`gemini-3-pro-image` là **$0,134/ảnh = 35,2 credit**, trong khi nền tảng bán
**16 credit** ở `taoanh` và **5 credit** ở `thumbnail` (app đó tính giá phẳng bất
kể model). Lỗ **1.924đ** và **3.024đ** mỗi ảnh, và lỗ lớn dần theo doanh số.

Chủ dự án chốt: **giữ giá các bậc rẻ như chi phí thu hút khách, đóng đúng bậc lỗ
nặng nhất.** Ba bậc còn lại vẫn dưới giá vốn và điều đó nay được **khai tường
minh** trong `tests/test_261_khong_ban_duoi_gia_von.py`, kèm hạn rà lại 15/09.

Model bị đặt `is_active=False` trong `platform_core/providers.py` nên nó biến khỏi
**cả** bộ chọn model của giao diện web — đó mới là chỗ lỗ thật sự chạy, vì đường
API của `thumbnail` đã ẩn tham số `model` từ trước.

⭐ Mở lại được: ngày nào giá bán ≥ giá vốn thì bật lại `is_active`.
`tests/test_261` kiểm hộ điều kiện đó.

### ADDED — 2026-08-15 (EXT-17)

- `CONTRACT_BASELINE.json` + bước gate `hop dong API`. Từ nay mọi thay đổi hợp
  đồng phải đi qua đây.
- Payload webhook có `payload_version` (bắt đầu từ `1`) và danh sách trường được
  khai tường minh. Trong một phiên bản, trường có thể **thêm** nhưng không được
  bỏ hay đổi tên.
- Trang trạng thái công khai `/status/api`, nhóm theo **năng lực** chứ không
  theo hạ tầng.

### ADDED — 2026-08-15 (EXT-15)

- Báo giá và job mang `pricing_version`. Giá vẫn do công thức của app tính;
  nhãn ghi lại chế độ giá đang có hiệu lực để đối soát về sau.
- `GET /api/v1/quotes` trả thêm trường `pricing_version`.

### FIXED — 2026-08-15 (EXT-15)

- Job giữ **đúng** số credit đã báo giá. Trước đó khoản giữ được tính lại từ
  công thức app và **bỏ qua sàn/trần đã công bố**, nên khách có thể được báo một
  số rồi bị trừ một số khác.

### ADDED — 2026-08-14 (EXT-12)

- Chế độ **test**: khoá tiền tố `ltt_tk`, chạy hết chuỗi thật nhưng không gọi
  nhà cung cấp và **không chạm sổ credit**.
- Mọi job và mọi payload webhook mang trường `mode` (`live` | `test`).
- `GET /api/v1/me` trả thêm `mode`.

### ADDED — 2026-08-14 (EXT-09 … EXT-11)

- Nhật ký request cho khách, console webhook (gửi lại, xoay secret, test), ngân
  sách + cảnh báo.

### ADDED — 2026-08-13 (EXT-02 … EXT-08)

- Bảng mã lỗi ổn định kèm ngữ nghĩa thử lại; `execution_mode` công bố trên mọi
  operation; project cho khoá; catalog model/tool; playground.

---

## Cách một thay đổi phá vỡ tương thích được phép xảy ra

1. Đặt cho nó một **phiên bản mới** (`/api/v2`), **hoặc** công bố lịch ngừng hỗ
   trợ trên bề mặt cũ (`deprecated_on` + `sunset_on` trong
   `server/api/inventory.py` — hai header sẽ tự xuất hiện).
2. Viết một mục **BREAKING** ở đây, kèm việc khách phải làm.
3. Cập nhật `docs/PUBLIC_API/MIGRATION.md`.
4. Chạy `python tools/check_api_compat.py --accept`.

Bỏ bước nào cũng được — gate sẽ chặn ở bước 4, và đó là chủ ý.

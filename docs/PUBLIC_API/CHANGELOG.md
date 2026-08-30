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

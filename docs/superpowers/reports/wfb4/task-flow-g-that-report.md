# wfb4 — FLOW G thật (plan P-B, `2026-09-25-wf-v2-VAN-HANH.md`)

> Việc: làm `tests/test_2935_flow_g.py` (tự chấm điểm mình, chưa gọi model
> thật, không biên dịch thật) trở thành thật.

## 0. Trước khi gọi model: sáu thành phần hôm nay là gì

`ke_hoach_v3.danh_muc()` (đúng danh mục prompt gửi cho model, chỉ node
`publish_duoc`) + `nut.tat_ca()`:

| Thành phần §18.5 | Trạng thái hôm nay | Vì sao |
|---|---|---|
| filter | ✅ `core.filter` | trong danh mục |
| foreach | ✅ `core.foreach` + `core.foreach_end` | trong danh mục |
| video | ✅ `app.video.generate` | trong danh mục |
| human | ✅ `core.human` | trong danh mục |
| **sheets** | ⚠️ **có trong registry, KHÔNG publish_duoc** | `nut.py::tu_piece()` khoá cứng `publish_duoc=False` cho MỌI node `piece.*` — bình luận tại chỗ: cổng publish `cau_noi.nop_job` còn từ chối `piece.*`, chờ "plan 08" (P-C) mở đường runner Node riêng |
| **cron** | ⛔ không phải node | P4 làm trigger thành **hàng** `workflow_trigger` (`kind`/`config`/`next_fire_at`, không có `node_id`) — thiết kế khác §18.5, đã chốt là ĐÚNG (test_2935), không phải thiếu |

`test_2935_flow_g.py` bản hiện tại (5 passed) đã NÂNG từ "4/6, Sheets chưa có"
lên "Sheets có trên palette" — nhưng phép đó chỉ hỏi `nut.tat_ca()`, không hỏi
`publish_duoc`. Sheets **có tên**, **không dùng được** — khác nhau, và tệp
mới `test_4190` đo đúng khác biệt đó.

## 1. Lượt gọi model THẬT (25/09/2026, MỘT lượt, không mock)

Đường thật: `ke_hoach_v3.soan_draft(db, goal=CAU, ngan_sach_credit=200,
cong_cu=cc)` không `llm_call` ⇒ `planner.goi_model` → `admission.acquire`
(lease thật, giải phóng ngay sau) → `dieu_phoi.goi` → máy B.

```
model:      ltt-3.5 (Qwen3.5-9B-Q6_K, 5060 Ti) — rẻ nhất trong 2 model nội bộ,
            đúng canonical.MODEL_NOI_BO_MAC_DINH, không chỉ định tay
thời gian:  53,25 s
token vào:  6 632 (cache=0)   token ra: 2 990
danh mục:   35 node (chỉ publish_duoc)
```

⚠️ Không tính được credit bằng `gia_token.tinh()` trong lượt đo: `kc.model`
trả về **đường dẫn GGUF** (`H:/LTT_LLM/models/Qwen3.5-9B-Q6_K-unsloth.gguf`),
không phải alias `ltt-3.5` mà bảng giá tra theo — lỗi ở **script đo của tôi**
(gọi thẳng `dieu_phoi.goi` để bắt `KetQuaChat`, không đi qua lớp map alias
của `apps/ltt_llm`), KHÔNG phải lỗi tính tiền thật của nền tảng (khách qua
`apps/ltt_llm/features.py` luôn gửi alias, không gửi đường dẫn GGUF).

## 2. Draft thật KHÔNG biên dịch được — và đúng hai lý do, đo được

Cho `document` model trả về đi thẳng qua `bien_dich.bien_dich()` (cổng
publish thật): `LoiBienDich(ma="node_khong_ton_tai", node_id="fetch_sheet")`.

Đào tới gốc — KHÔNG phải model kém, là **prompt cũ có hai lỗ**, cả hai chỉ lộ
ra khi model thật gõ, không lộ ra ở dữ liệu vàng do người viết:

1. Danh mục cũ ghi dính `type@type_version` (`- core.http@1 (job): ...`).
   Model chép NGUYÊN chuỗi hiển thị vào trường `type` của **cả 8 node**
   (`"type": "core.http@1"` thay vì `"core.http"`). Đúng bài học "ví dụ
   trong lời nhắc là mệnh lệnh ngầm" — model học HÌNH THỨC, không học lược đồ.
2. Mẫu JSON cũ liệt `"kind"` như một khoá rỗng, không nói giá trị hợp lệ
   (`bien_dich._KIND = {DATA, CONTROL, ERROR}`). Model đoán `"json"` cho cả
   7 cạnh — hợp lý về ngữ nghĩa (đang tả định dạng dữ liệu), sai Ô cần điền.

## 3. Đã sửa — tại nguồn prompt, không vá đầu ra

`platform_core/agent/ke_hoach_v3.py::build_prompt`:
- Dòng danh mục tách `type=... type_version=... kind=...`, không còn dính `@`.
- Thêm `[QUY_UOC_KIND]` liệt đúng 3 giá trị hợp lệ.
- `[DAU_RA]` nói thẳng: không được nối `@version` vào `type`.

`tests/test_4190_flow_g_goi_model_that.py` khoá lại bằng máy:
- đóng băng `document` NGUYÊN VĂN của lượt gọi thật, chứng minh nó bị từ chối
  đúng mã/đúng node đã đo (không phải lời kể lại);
- áp ĐÚNG hai phép sửa mà prompt mới đòi (không sửa gì khác, không gọi lại
  model) ⇒ draft thật đi qua `bien_dich.bien_dich()`, `thu_tu` tô-pô thật
  (`fetch_sheet → … → output_result`), có `{filter, foreach, foreach_end,
  video, human}`, `bao_gia_do_thi` ra trần > 0;
- khoá lại chính bản vá (`[QUY_UOC_KIND]` có mặt, danh mục không còn `@` dính);
- khoá lại lý do Sheets vẫn không publish_duoc (không lặp lại nhầm "có tên =
  dùng được").

⛔ **Ở LƯỢT ĐẦU: chưa gọi lại model để xác nhận prompt mới THẬT SỰ khiến nó
viết đúng** — mục 3 (bản đầu của báo cáo này) chỉ suy luận từ việc vá tay
draft đã đông băng. Điều phối viên chỉ ra đúng lỗ hổng đó: kiểm bản vá trên
một draft đã đông băng là kiểm trên **bản đại diện**, không phải model thật
— và cấp thêm MỘT lượt gọi để đo cho đúng. Mục 5 dưới đây là lượt đó.

## 4. Chưa làm được (tính tới lượt gọi đầu) — nói thẳng

1. **FLOW G đủ 6/6 theo đúng tinh thần §18.5 (Sheets THẬT, không phải
   `core.http` tay) vẫn CHƯA đạt.** `piece.*` còn bị khoá `publish_duoc=False`
   cứng trong mã, và cổng chạy (`cau_noi.nop_job`) còn từ chối `piece.*` bằng
   `LoiTienTo` — việc đó thuộc P-C (port `pollingHelper`), không phải P-B.
2. Test `test_2935_flow_g.py` (dữ liệu vàng) và `test_4190` (dữ liệu thật)
   SONG SONG tồn tại — không hợp nhất, vì chúng đo hai thứ khác nhau
   (dữ liệu vàng đo cổng biên dịch + báo giá; dữ liệu thật đo model + prompt).

## 5. LƯỢT GỌI THẬT THỨ HAI (25/09/2026, sau khi sửa `build_prompt()`)

Cùng câu `CAU`, cùng model `ltt-3.5`, cùng đường thật (`soan_draft` không
`llm_call`). **40,00 s, 6 919 token vào / 2 746 token ra.**

### 5.1 Câu hỏi của điều phối viên: bản vá có đúng không?

**Đúng — đo trực tiếp trên lượt gọi sống, không suy diễn.** Không node nào
trong 6 node lượt 2 có hậu tố `@version` trong `type`. Mọi cạnh dùng đúng
`kind ∈ {DATA, CONTROL}` — model còn tự phân biệt đúng ngữ nghĩa: cạnh nhánh
`true` của `core.if` được gắn `CONTROL`, các cạnh còn lại `DATA`. Hai lỗ đã
sửa **ở lượt trước** không còn xuất hiện ở lượt này.

### 5.2 Nhưng draft lượt 2 VẪN không biên dịch được — lý do KHÁC, không phải bản vá

`create_video` dùng `"{{ nodes.fetch_sheet.output.json.prompt }}"` —
`bien_dich.bien_dich()` từ chối bằng `LoiBienDich(ma="bieu_thuc_chua_ho_tro",
node_id="create_video")`.

Gốc rễ: `_THAM_CHIEU` (`platform_core/workflow/bien_dich.py`, regex
`^\{\{\s*nodes\.ID\.output\.CONG\s*\}\}$`) chỉ nhận **đúng một đoạn** sau
`.output.`. `nodes.fetch_sheet.output.json.prompt` có đoạn lồng (`json` rồi
`prompt`) ⇒ không khớp. Xác nhận trực tiếp bằng hàm compiler:
`la_tham_chieu("{{ nodes.fetch_sheet.output.json.prompt }}")` → `None`;
`la_tham_chieu("{{ nodes.fetch_sheet.output.json }}")` → `("fetch_sheet",
"json")`.

**Đoạn regex này KHÔNG nằm trong bản vá vừa rồi** — `build_prompt()` chỉ đổi
cách hiển thị danh mục và thêm khối `[QUY_UOC_KIND]`, không đụng
`_THAM_CHIEU`/`la_tham_chieu`. Lượt 1 không lộ ra giới hạn này vì tham số
lượt 1 dùng chuỗi trần (`"item.title"`, không bọc `{{ }}`), nên `_doi()`
chưa từng xét nhánh kiểm tra tham chiếu. Lượt 2 mới thật sự thử cú pháp
`{{ nodes... }}` mà `[DAU_RA]` yêu cầu từ đầu — và lộ ra một giới hạn CHƯA
TỪNG ĐO của cổng biên dịch (không hỗ trợ truy cập lồng sau `output.<cổng>`),
độc lập với bản vá.

### 5.3 Regression thật sự cần hỏi: draft lượt 2 mất `core.filter`/`core.foreach`

Lượt 2 chỉ có 6 node: `core.http`, `core.if`, `app.video.generate`,
`core.human`, `core.output`, `core.stop` — xử MỘT bản ghi bằng nhánh điều
kiện, không lọc-rồi-lặp nhiều dòng như lượt 1 (8 node, có
`core.filter`+`core.foreach`+`core.foreach_end`).

`build_prompt()` không đổi gì về hướng dẫn lọc/lặp, và `core.filter`/
`core.foreach` vẫn nằm nguyên trong danh mục gửi cho model (khoá lại bằng
`test_danh_muc_van_co_filter_va_foreach`). **Không đủ căn cứ để nói bản vá
"làm tụt" kiến trúc filter+foreach, và cũng không đủ căn cứ để loại trừ.**
N=1 mỗi phía (một lượt trước vá, một lượt sau vá) — không so sánh được;
draft lượt 2 còn không biên dịch được vì lý do KHÁC (5.2) nên không tính
được báo giá để so bất kỳ con số nào giữa hai lượt.

Đây đúng là bài học sổ tay: *"ví dụ trong lời nhắc là mệnh lệnh ngầm — sửa
lời nhắc phải đo lại CẢ TẬP"*. Một cặp before/after không phải một tập.
⛔ **Không tự ý gọi lượt 3** để "thử sửa cho ra filter+foreach" — đúng điều
điều phối viên đã cấm (vá lần hai rồi gọi lần ba là điều chỉnh theo nhiễu,
không phải đo). Muốn tách tín hiệu khỏi nhiễu lấy mẫu của chính model cần
nhiều mẫu mỗi phía (before/after) hoặc đổi cách khai danh mục thay vì vá văn
bản — cả hai đều cần chủ trì quyết định, ghi lại ở đây để hỏi.

## 6. Chưa làm được (tính tới lượt gọi thứ hai) — nói thẳng

1. Mục 4.1 vẫn đúng nguyên — Sheets thật vẫn thuộc P-C.
2. **Draft lượt 2 vẫn không biên dịch được**, vì một giới hạn compiler khác
   (5.2), độc lập với bản vá — bản vá xác nhận đúng, nhưng KHÔNG đủ để làm
   FLOW G biên dịch trên một lượt gọi sống mới.
3. **Chưa xác định được** việc mất `core.filter`/`core.foreach` ở lượt 2 có
   phải hệ quả của bản vá hay không (5.3) — cần đo nhiều mẫu, không phải một
   lượt gọi thứ ba đơn lẻ.

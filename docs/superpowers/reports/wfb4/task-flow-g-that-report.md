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

⛔ **Chưa gọi lại model để xác nhận prompt mới THẬT SỰ khiến nó viết đúng.**
Đây là hệ quả trực tiếp của luật "MỘT lượt gọi" trong brief — tôi chọn giữ nó
nghiêm, không phá luật để tự xác nhận việc mình vừa sửa. Bằng chứng ở mục 3
là **suy luận từ đúng hai khác biệt đã đo**, không phải một lượt gọi thứ hai.

## 4. Chưa làm được — nói thẳng

1. **FLOW G đủ 6/6 theo đúng tinh thần §18.5 (Sheets THẬT, không phải
   `core.http` tay) vẫn CHƯA đạt.** `piece.*` còn bị khoá `publish_duoc=False`
   cứng trong mã, và cổng chạy (`cau_noi.nop_job`) còn từ chối `piece.*` bằng
   `LoiTienTo` — việc đó thuộc P-C (port `pollingHelper`), không phải P-B.
2. **Chưa xác nhận lại bằng máy** rằng bản vá prompt khiến `ltt-3.5` thật sự
   ngừng mắc hai lỗi trên — xem mục 3, lý do là luật MỘT lượt gọi.
3. Test `test_2935_flow_g.py` (dữ liệu vàng) và `test_4190` (dữ liệu thật)
   giờ SONG SONG tồn tại — không hợp nhất, vì chúng đo hai thứ khác nhau
   (dữ liệu vàng đo cổng biên dịch + báo giá; dữ liệu thật đo model + prompt).

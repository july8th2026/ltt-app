# 05 — AUDIT `bot_gem`

`giaitritruyenthongltt-spec/bot_gem@0bc47735` · `master` · 2026-09-03 11:28 +0700
Bản sao nghiên cứu: `D:\LTT_4BOT_LAB\bot_gem`
146 tệp `.py` · 52.811 dòng — **lớn nhất, rủi ro nhất, và là bot duy nhất có một
điều kiện DỪNG thật.**

⚠️ Kho còn nhánh thứ hai `tich-hop-ltt-llm@8f1bb40b`. Nhánh ấy **ngoài phạm vi
mặc định**, nhưng chính tên nó nói rằng có người đã bắt đầu đúng việc mà audit
này đang bàn. **Phải hỏi chủ dự án nhánh nào là nguồn chân lý trước khi build.**

## 🔴 Bot này KHÔNG gọi API — nó lái trình duyệt

```
109 lần `webdriver` · 108 `selenium` · 16 `undetected_chromedriver`
```

Nó đăng nhập một tài khoản người dùng thật vào Gemini/ChatGPT trên web, gõ
prompt, đợi trả lời, đọc DOM. `undetected_chromedriver` có mặt vì phía kia
**đang cố phát hiện và chặn** đúng việc này.

⇒ Ba hệ quả, và cả ba đều là quyết định của chủ dự án chứ không phải của kỹ thuật:

1. **Đầu ra không tất định** ở mức mạnh hơn "LLM thì không tất định": DOM đổi
   thì bot hỏng, không phải trả lời sai.
2. **Cần năng lực worker `browser`** (`AppManifest.requires`) — LTT có sẵn ô
   này, kèm ghi chú *"cần trình duyệt + IP dân dụng"*.
3. **Rủi ro ToS** thuộc về người vận hành. Kho này đã có tiền lệ được ghi
   (memory *app chataistudio + sidecar Codex*: đăng nhập ChatGPT Plus, ToS-risk
   người dùng chấp nhận) — nên đây là một quyết định **đã từng được đưa ra**, chứ
   không phải một chuyện mới.

## Hai dự án con, và một bản sao byte-identical

```
BOT_VEO3/
  ├ BOT_AUTO_KICHBAN/      bot_bridge.py 836 · gui/frames/settings_chrome.py 1.193
  └ PROMPT_KICHBAN/        core/workflow_engine.py 2.026 · core/gemini_client.py 2.864
                           core/chatgpt_automation.py 1.432  ─┐
gemini_NVCQ - GPT/                                            │ md5 TRÙNG KHỚP
  ├ chatgpt_automation.py 1.432  ─────────────────────────────┘  2929b1f7…
  ├ gemini_automation.py 2.583
  └ character_scene_bot.py 3.063
```

⛔ `chatgpt_automation.py` là **bản sao byte-identical** ở hai nơi. Cộng với 7
module dùng chung của ba bot kia, đây là kho thứ hai chứng minh cùng một thói
quen: chép tệp thay vì chia sẻ.

## Nghiệp vụ thật: `WorkflowEngine` — và nó đã là một workflow engine

`BOT_VEO3/PROMPT_KICHBAN/core/workflow_engine.py` chạy ba bước qua prompt template:

```
step1_character_lock.txt  →  step2_scene_list.txt  →  step3_json_prompt.txt
```

⭐ **Đây là phát hiện đắt nhất của bản audit này.** Bot này không phải "một công
cụ gọi LLM" — nó là một **workflow nhiều bước có trạng thái**, và các hằng số của
nó là tri thức vận hành đã trả giá bằng tài khoản bị throttle:

| Hằng số | Giá trị | Vì sao |
|---|---|---|
| `STEP2_BATCH_SIZE` / `STEP3_BATCH_SIZE` | 10 / 5 | kích thước lô mỗi bước |
| `STEP_BATCH_DELAY` | 8s | *"tăng từ 3s — proven stable trên NVCQ"* |
| `BATCH_REST_INTERVAL` / `_DURATION` | 12 lô / 45s | *"Gemini cho phép ~15-20 prompt/session trước khi throttle"* |
| `BATCH_PROGRESSIVE_DELAY` / `_STEP` / `_CAP` | bật / +3s / 60s | *"chống pattern detection"*; cap thêm vì 100 lô = 1h15 chỉ để chờ |
| `BATCH_NEW_CONV_INTERVAL` | 25 lô | mở hội thoại mới, tránh **ô nhiễm ngữ cảnh** |
| `HISTORY_SCENES_COUNT` | 5 | *"bug cũ: chỉ giữ 2 scene cuối → qua 100+ scenes drift character/style"* |

⛔ **Không hằng số nào ở trên được phép "tối ưu" trong lúc migrate.** Mỗi con số
là một lần hỏng đã xảy ra. MASTER-GUARDRAILS #6 áp đúng ở đây.

## SOURCE MAP

| Module | Vai trò | Critical | Quyết định |
|---|---|---|---|
| `core/workflow_engine.py` (2.026) | ba bước · lô · nhịp · lịch sử cảnh | ✅ | `REUSE_ADAPT` |
| `core/gemini_client.py` (2.864) | lái Gemini web | ✅ | `REUSE_DIRECT` — **đóng băng** |
| `gemini_automation.py` (2.583) | bản thứ hai của cùng việc | ⚠️ | `UNKNOWN` — phải so trước |
| `chatgpt_automation.py` (1.432 ×2) | lái ChatGPT web | ✅ | `REUSE_DIRECT`, gỡ một bản sao |
| `character_scene_bot.py` (3.063) | nhân vật + cảnh, `ProfileRotator` | ✅ | `REUSE_ADAPT` |
| `data/prompts/*.txt` | ba template | ✅ | `REUSE_DIRECT` — **tài sản, không phải mã** |
| `gui/**` (≥5.000) | GUI Tkinter | ❌ | `REWRITE_LTT` |
| `drive_handler_v2.py` · `google_api.py` | Drive/Sheet | ❌ | `DROP_LEGACY` |
| `test_*.py` ở gốc (8 tệp) | kiểm thủ công | ❌ | `DROP_LEGACY` |

## PARITY MATRIX

| Năng lực | Mức | Đo bằng gì |
|---|---|---|
| Ba bước theo đúng thứ tự, đúng template | **P0** | so prompt gửi đi, từng ký tự |
| Kích thước lô 10 / 5 | **P0** | đếm mục mỗi lần gửi |
| Nhịp chờ (8s · +3s · cap 60 · nghỉ 45s/12 lô) | **P0** | dấu thời gian giữa các lần gửi |
| Hội thoại mới sau 25 lô | **P0** | số lần mở hội thoại |
| Giữ 5 cảnh lịch sử | **P0** | nội dung prompt lô thứ n |
| Xoay hồ sơ trình duyệt | P1 | `ProfileRotator` |
| Khôi phục khi DOM đổi / phần tử cũ | P1 | có `test_phase2_stale_element.py` |
| Đầu ra JSON của step3 | **P0** | so schema |

⛔ **Không đòi bằng nhau từng byte cho nội dung LLM sinh ra.** Phép đo là
**cấu trúc và nhịp**, không phải văn bản.

## 🛑 ĐIỀU KIỆN DỪNG — phải hỏi chủ dự án trước Phase 10

1. **Nhánh nào là nguồn chân lý** — `master` hay `tich-hop-ltt-llm`?
2. **Giữ lái trình duyệt, hay chuyển sang API?** Chuyển là **đổi provider** giữa
   lúc migrate, thứ MASTER-GUARDRAILS #6 cấm. Giữ thì App này cần worker có
   `requires=("browser",)` và một tài khoản thật — tức một quyết định vận hành.
3. **Tài khoản nào chạy?** Không có tài khoản thì E2E của App này không đóng được,
   và pack đã lường trước điều đó (`PACK-AUDIT-REPORT`: *"credential/browser E2E
   của GEM có thể cần manual user step"*).

## Còn UNKNOWN

- `gemini_automation.py` (2.583) và `core/gemini_client.py` (2.864) **có thể là
  hai bản của cùng một việc**. Chưa so. Không được viết service khi còn UNKNOWN này.
- `BOT_AUTO_KICHBAN` so với `PROMPT_KICHBAN`: quan hệ chưa xác định.

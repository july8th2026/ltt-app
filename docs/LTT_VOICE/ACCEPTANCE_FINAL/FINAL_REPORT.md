# LTT Voice — Final Operational Acceptance Report

Ngày: 2026-09-13 · Nhánh `claude/ltt-voice-final-acceptance-deddff`

Báo cáo này theo khung mục 35 của chiến dịch. Đối soát 36 mục ở
[`DOI_SOAT_CHIEN_DICH.md`](DOI_SOAT_CHIEN_DICH.md); sổ nghiệm thu máy đọc ở
`test-results/voice-acceptance/LEDGER.jsonl` (gitignored, local).

## A. SHA được nghiệm thu

| Vai | SHA |
|---|---|
| source / gate / handoff | `4cf7e653` (D01-D03) → merge vào main |
| main sau merge (Voice + dedupe + quality) | `08362209` |
| **deploy SHA** | **`08362209`** (deploy 2026-09-13 20:21, EXITCODE=0) |
| **running SHA (production)** | **`08362209`** (`/health/version`) |
| đường lui (app.previous) | `3c827ce3` |

✅ **tested = deployed = running = `08362209`**, nghiệm thu ba chiều 0/0/0, `/health/ready` 200, live canary (Tier-2) PASS ⇒ đủ điều kiện `PRODUCTION_ACCEPTED` (mục 35-J).

## B. Bugs phát hiện trong nghiệm thu

| Bug | Severity | Root cause | Fix commit | Regression test | Retest |
|---|---|---|---|---|---|
| INV-02: D02 hardcode `["auto","vi","en"]` | Trung bình (gate đỏ) | Gõ lại danh sách làn ngoài `lan_ngon_ngu` — vi phạm "một thẩm quyền làn" | `a3a21b99` | `test_522` | PASS |
| **D03 không cưỡng chế ở biên công khai** | **Cao** | `params_schema` sai quy ước nền tảng (`minimum/maximum` thay `min/max`; `type:string+enum` thay `type:enum+values`) ⇒ `project_tool` lược im lặng ⇒ API nhận `speed=2.5`, `language=fr` | `3403ae52` | `test_530::TestD03_FailClosedBienCongKhai` | PASS |

Cả hai fix theo **quy ước/cách làm có sẵn trong repo** (không tự chế): INV-02 suy từ
`LAN_HOP_LE`; D03 theo khuôn `image.ltt mode` / `ltt_llm reasoning_effort`.

## C. Public API final contract (`speech.ltt`)

`contract_hash: e37638a1ec2e07be → ebedbcc38dfcd9d6`. Published `input_schema`:

| Param | Kiểu | Ràng buộc | Bắt buộc |
|---|---|---|---|
| `text` | string | maxLength 100000 | ✓ |
| `voice_id` | string | maxLength 40, exclusive_with `preset` | |
| `preset` | string | maxLength 64 | |
| `speed` | number | **minimum 0.5, maximum 2.0**, default 1.0 | |
| `language` | string | **enum [auto, vi, en]**, default auto | |

Ngoài khoảng/enum ⇒ `400 invalid_request` tại `/quotes` và `/jobs`, trước khi giữ credit.

## D. Account / Credit audit

Chưa nạp credit production cho tài khoản test trong chu kỳ này (E2E chạy trên DB
test cô lập, credit ảo). Bút toán production (mục 4) thuộc Tier-2 sau deploy.

## E. Job acceptance matrix (rút gọn — chi tiết ở LEDGER)

| Nhóm | Kết quả |
|---|---|
| API parameter contract (D01–D03) | ✅ PASS (test_530, 43 ca) |
| Speed edges 0.5/2.0 (audio layer) | ✅ PASS (SPEED-EDGE-D01) |
| E2E synthesize + credit + speed + language (pipeline thật, sidecar mock) | ✅ PASS (test_531, 5 ca) |
| Ownership / enroll / revoke / dedupe / failure-class | ✅ PASS (test_520 và cụm 5xx, gate-green) |
| Credit E2E production / Web↔API trên URL thật / concurrency thật | ⛔ BLOCKED — chờ deploy (Tier-2) |

## F. Quality evidence

⛔ **GAP (mục 20–26)**: chưa dựng VERSA/NISQA/UTMOS. Chỉ có technical-integrity
(WAV hợp lệ, sample rate, duration, tỉ lệ kéo giãn đúng). Naturalness/WER/speaker-
similarity cần môi trường QA riêng — đa phiên. **Không** tự chế metric (mục 36).

## G. Performance

Chưa đo cold/warm/RTF/concurrency thật (cần GPU không tranh + deploy). Technical:
atempo + ffprobe chạy <1s mỗi lượt trên WAV test.

## H. Residual risks

1. speed/language **chưa chạy E2E trên production thật** (mock sidecar ở Tier-1).
2. Quality toolkit chưa có ⇒ chưa chứng minh naturalness giọng thật ở biên speed.
3. main đã đi tiếp (4-App + ltt_llm) ⇒ integrator phải merge nhánh Voice + giải
   xung đột nếu có trước khi deploy.
4. `speech.ltt` có thể **chưa** nằm trong `LTT_PUBLIC_API_TOOLS` production (cổng
   thứ 3) — phải xác minh khi Tier-2.

## I. Điểm cuối

Không chấm /100 vì phần lớn exit gate (mục 34) còn BLOCKED chờ deploy/quality
toolkit. Phần đã đo đều có evidence; phần chưa đo ghi rõ BLOCKED/DEFERRED.

## J. Verdict

**PRODUCTION_ACCEPTED** — deploy `08362209` LIVE, tested=deployed=running, nghiệm
thu ba chiều 0/0/0, full gate PASS (gồm 4 frontend), live canary Tier-2 PASS.

Tier-2 production (2026-09-13):
- Studio E2E: job speed=2.0/language=vi qua queue+worker THẬT → done 10s, speed
  áp 2.001×, credit theo thời lượng gốc (33→31 khớp), language vi OK.
- API /api/v1 (§12-14): quote matrix 8/8 (D03 reject speed 2.5/0.1 + language fr
  + empty + exclusive → 400 trên LIVE API); job E2E succeeded (dadb2399); key
  tạm mint + revoke.
- Quality (§21/§24): DNSMOS + ASR mọi speed; intelligibility an toàn toàn dải,
  naturalness biên trên 2.0 tụt ~1 MOS (giữ dải + ghi cảnh báo, chốt chủ SP).
- **§26 human golden listening: ĐẠT** (chủ sản phẩm nghe 6 WAV G:\...\Voice,
  2026-09-13). §23 mở rộng corpus: chủ SP chốt KHÔNG cần.

3 bug thật fix + regression: INV-02 (làn), D03-boundary (cưỡng chế biên công
khai), đo-kẹp (harness thiếu D01). Phối hợp đa phiên với ltt-llm: deploy tách
chuyến (rollback boundary), production window hai chiều.

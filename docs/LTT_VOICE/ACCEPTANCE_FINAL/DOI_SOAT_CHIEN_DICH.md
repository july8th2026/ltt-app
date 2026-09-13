# Đối soát: Chiến dịch 36 mục ↔ Trạng thái ↔ Plan thực thi

Lập: 2026-09-13 · Nhánh `claude/ltt-voice-final-acceptance-deddff`

Tài liệu này đối soát prompt gốc (FINAL OPERATIONAL ACCEPTANCE CAMPAIGN, 36 mục)
với: (a) việc đã làm, (b) hạ tầng đã có trong repo, (c) ràng buộc môi trường.
Nó thay cho plan cũ `docs/superpowers/plans/2026-09-13-ltt-voice-public-api-speed-language.md`
(plan cũ chỉ phủ D01–D03 = Pha 1 của chiến dịch).

## Ràng buộc môi trường (quyết định cái gì chạy được ở đây)

| Yếu tố | Thực tế |
|---|---|
| Máy | **Production đang sống** (`C:\LTTPlatform`), venv có GPU RTX 5060 Ti |
| Sidecar VieNeu | `LTTStudioVoice` **đang chạy** (cần nạp ENV để gọi) |
| Deploy | **Lane của phiên `ltt-studios-commit-deployment`** — không tự deploy |
| main | Đã đi trước nhánh tôi (4-App + ASV); production deploy `6f160626` @14:48 |
| Quality ML toolkit | **Chưa có** VERSA/NISQA/UTMOS — phải dựng từ đầu, đa phiên |

## Phân loại trạng thái mỗi mục

| Mục | Nội dung | Trạng thái | Ghi chú |
|---|---|---|---|
| 0 | Superpowers bắt buộc | ✅ DONE | brainstorming + writing-plans đã dùng |
| 1 | Decision Lock D01–D08 | ✅ DONE | 8 quyết định đã duyệt phiên trước |
| 2 | Freeze baseline | ✅ DONE | `ACCEPTANCE_FINAL/BASELINE.md` |
| 3 | Tài khoản nghiệm thu | ⏳ DOABLE | `tools/tai_khoan_thu.py` có sẵn |
| 4 | Credit acceptance | ⏳ DOABLE | cần chủ nạp credit hoặc `--nap` cho .local |
| 5 | Public API contract audit | ⏳ DOABLE | bảng parity Web↔API |
| 6 | Không bắt chước API đối thủ | ✅ DONE | D06/D07 đã khoá giữ internal |
| 7 | Acceptance matrix Web/Studio | ⚠️ MỘT PHẦN | browser flows có; 200+ ca là đa phiên |
| 8 | Clone/enroll acceptance | ⚠️ MỘT PHẦN | enroll KHÔNG mở API (consent) |
| 9 | Preset/shared/private voice | ⏳ DOABLE | |
| 10 | Project acceptance | ⏳ DOABLE | |
| 11 | History acceptance | ⏳ DOABLE | |
| 12 | API auth/key/scope | ⏳ DOABLE | test 180 có sẵn |
| 13 | API quote | ⏳ DOABLE | **cốt lõi D01–D03** |
| 14 | API job end-to-end | ⏳ DOABLE | harness đã mở rộng nhận speed/language |
| 15 | Web↔API parity | ⏳ DOABLE | nhóm quan trọng nhất |
| 16 | Security/ownership | ⏳ DOABLE | cần TEST-A + TEST-B |
| 17 | Runtime/fault injection | ⏳ DOABLE | dùng mock layer trước |
| 18 | Concurrency | ⏳ DOABLE | admission serialize GPU |
| 19 | Performance | ⏳ DOABLE | đo, không đặt ngưỡng |
| 20 | External quality toolkit | ❌ GAP LỚN | VERSA/NISQA/UTMOS chưa có, đa phiên |
| 21 | Quality dimensions | ❌ BLOCKED bởi 20 | |
| 22 | PESQ/STOI khi có reference | ❌ BLOCKED bởi 20 | |
| 23 | Quality corpus | ⏳ DOABLE | text corpus không cần ML |
| 24 | Không bịa threshold | ⏳ NGUYÊN TẮC | áp dụng khi có 20 |
| 25 | Output mỗi quality job | ⏳ DOABLE | JSON schema |
| 26 | Human golden listening | ⚠️ CẦN NGƯỜI | chủ hệ thống nghe |
| 27 | Browser real acceptance | ⏳ DOABLE | 5 flow có sẵn + Playwright |
| 28 | Fix-in-place loop | ⏳ QUY TRÌNH | systematic-debugging |
| 29 | Không deploy sau mỗi fix | ✅ ÁP DỤNG | Tier 1 trước |
| 30 | Tier 2 production acceptance | ⛔ CHỜ DEPLOY | sau khi phiên deploy đẩy bản mới |
| 31 | Cleanup policy | ⏳ QUY TRÌNH | revoke key trong finally |
| 32 | GAP đặc biệt A/B/C/D | ⏳ DOABLE | A đã fix (D01–D03) |
| 33 | Acceptance ledger | ⏳ DOABLE | sổ máy đọc |
| 34 | Exit gates | ⏳ TỔNG HỢP | cuối |
| 35 | Final report | ⏳ TỔNG HỢP | cuối |
| 36 | Nguyên tắc cuối | ⏳ NGUYÊN TẮC | xuyên suốt |

## Đường tới hạn (critical path) cho phiên này

Bạn yêu cầu: **chạy test job → ghi tên lỗi → tổng hợp → fix code → gate cuối**.
Ưu tiên đúng vòng lặp đó, trên phần chạy được ngay (Tier 1, không cần deploy,
không cần ML toolkit nặng):

### Pha A — Đóng D01–D03 sạch (đang dở, chặn gate)
- A1. Đồng bộ lại main vào nhánh (main đã đi trước)
- A2. Ghi `docs/PUBLIC_API/CHANGELOG.md` mục **ADDED** speed/language
- A3. Tìm + sửa lỗi mypy `union-attr 92→93` (do harness tôi sửa)
- A4. Commit: rename test + regenerated contract/docs + harness + changelog + mypy
- A5. Chạy full gate trên cây đứng yên → phán quyết sạch

### Pha B — Nghiệm thu vận hành cốt lõi (test job thật → bug ledger)
- B1. Lập `test-results/voice-acceptance/LEDGER.jsonl` (sổ máy đọc, mục 33)
- B2. TEST-A/TEST-B accounts (mục 3) + credit (mục 4)
- B3. Public API contract audit — bảng parity (mục 5, 32-GAP-A)
- B4. API quote matrix (mục 13): speed/language biên, mismatch, invalid → ghi lỗi
- B5. API job E2E (mục 14): quote→submit→poll→done→artifact→credit, speed 0.5/1.0/2.0
- B6. Web↔API parity (mục 15)
- B7. Security/ownership A↔B (mục 16)
- B8. Credit lifecycle (mục 4): rejection/success/refund/busy/double-submit
- **Mỗi FAIL → ghi tên lỗi vào ledger, KHÔNG sửa ngay** (tổng hợp trước)

### Pha C — Tổng hợp + fix (mục 28)
- C1. Tổng hợp bug list từ ledger
- C2. Với mỗi bug: regression test trước → minimal fix → focused test → suite
- C3. Chạy lại ca lỗi + ca liên quan

### Pha D — Gate cuối + bàn giao
- D1. Full gate xanh trên cây sạch
- D2. Ghim SHA HANDOFF_READY_FINAL + đẩy origin
- D3. Bàn giao phiên deploy để merge+deploy
- D4. (sau deploy) Tier 2 production canary (mục 30)

### Deferred (đa phiên, ghi rõ là GAP — mục 36 cấm giả PASS)
- Quality toolkit VERSA/NISQA/UTMOS (mục 20–22, 24) → cần môi trường QA riêng
- Full 200+ ca matrix Web/Studio (mục 7) từng viewport
- Human golden listening (mục 26) → cần chủ hệ thống

## Nguyên tắc thực thi (áp dụng xuyên suốt)
- Không coi HTTP 200 = PASS; không coi job done = audio good (mục 36)
- Không bịa metric/threshold (mục 20, 24)
- Mỗi bug commit riêng, message nêu bug/root cause/fix/evidence (mục 28)
- `SKIP` phải có lý do; `BLOCKED` phải nói thiếu dependency (mục 33)
- Không sửa production làm debugger (mục 29)

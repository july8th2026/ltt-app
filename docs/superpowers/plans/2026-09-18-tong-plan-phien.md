# Tổng plan phiên 17–18/09/2026 — LTT LLM + LTTCODE (bảng theo dõi tiến độ duy nhất)

> Đây là **một** chỗ để xem tiến độ cả phiên. Plan con giữ chi tiết từng bước; bảng này chỉ giữ trạng thái, bằng chứng (SHA/tệp) và thứ tự. Cập nhật bảng này mỗi khi một hạng mục đổi trạng thái — không ghi % ở chỗ khác.
>
> Ký hiệu: ✅ xong (có bằng chứng) · 🔵 đang chạy · ⬜ chưa làm · ⏸ chờ quyết định · ⛔ chặn ngoài phiên · ✖ bỏ (có lý do)

**Plan con (nguồn chi tiết):**
- LLM v2: `docs/superpowers/plans/2026-09-18-ltt-llm-v2-lam-lai-tren-phuong-an-c.md` (bản 2, `88a7910f`)
- Phương án C: `docs/ltt_llm_dual/KE_HOACH_PHUONG_AN_C.md`
- LTTCODE: `D:\LTTCODEAPP\docs\LTTCODE\plans\2026-09-17-ke-hoach-tong-phien.md`, `…\2026-09-17-truoc-build-0.1.5.md`, `…\KIEM_CUOI.md` §10

**Production lúc cập nhật bảng (18/09 ~10:30):** máy A chạy `2b3977ad` (`main` = `88a7910f`, khác production chỉ ở tài liệu); máy B cổng Phương án C bước 3 + engine L-25 (đã gộp `main` `f1d949b5`); LTTCODE 0.1.7 dev 100 %, stable 100 %.

---

## Tiến độ tổng

Trọng số cố định (không đổi giữa các lần cập nhật): A 20 · B 25 · C 10 · E 25 · F 10 · D 10.

| Khối | Trọng số | % xong | Đóng góp | Còn lại |
|---|---|---|---|---|
| A — Nền tảng LTT LLM (Phương án C) | 20 | 100 % | 20 | — |
| B — LTTCODE 0.1.7→0.1.10 build + E2E + phát hành | 25 | 100 % | 25 | 0.1.9 dev (Task 14/15/16), 0.1.10 dev sửa bộ cài xoá tệp cũ — verify_installed PASS trên máy thật; 0.1.10 stable đang dựng |
| C — Tối ưu máy B | 10 | 100 % | 10 | C4 → 3.5 np4 (L-28, đã deploy); làn B `-b/-ub` A–D + E3 + R-17 xong → 3.5 `-b 1024` (L-30, deploy cùng tổng kết) |
| E — LLM v2 | 25 | 100 % | 25 | 19/19 task xong; 17 đo live đạt (lượt ngắn 5–7 s thay vì 9–21 s); 14/15/16 trong LTTCODE 0.1.10 stable |
| F — Dọn tài liệu | 10 | 95 % | 9,5 | 8/8 lô + F5 xong; chờ gộp `main` qua L3 tổng kết |
| D — Tổng kết phiên | 10 | 30 % | 3 | ✅ nhánh tích hợp `phien/tong-ket-18-09` (5 nhánh + Task 17 + làn B), nhật ký; 🔵 L3 đang chạy; còn: khép L3, gộp `main`, deploy A + B, push hai kho, dọn 38 worktree, gỡ luật SSH tạm, env nssm B |
| **Cả phiên** | 100 | | **~92,5 %** | |

> Các lần báo trước (70–74 %) ước không theo trọng số và **cao hơn thực tế**; từ bản này dùng bảng trên.


---

## A — Nền tảng LTT LLM (Phương án C)

| # | Hạng mục | Trạng thái | Bằng chứng |
|---|---|---|---|
| A1 | Đo máy B, khôi phục, ComfyUI Manual | ✅ | `KET_QUA_DO_17_09.md` (nhánh `phien/bench-may-b`, **chưa gộp** → D2) |
| A2 | Chốt tham số: ngân sách `-c − 8.192`, whale 8.192/16.384, LTTCODE `max_tokens` 24.000 | ✅ | DECISION_LOG L-23 |
| A3 | Code bước 1–3 (A xếp lại khi B 429, hồ sơ số một chỗ, B rào vật lý) | ✅ | `dd6f5d55`, `9d48358d` |
| A4 | Gộp + L1 | ✅ | `575798a7` |
| A5 | Deploy B (cổng) → deploy A | ✅ | B 23:03, A 23:29 17/09 |
| A6 | Nghiệm thu production §5.1 | ✅ 7/7 | `NGHIEM_THU_PHUONG_AN_C_17_09.md` (`543e0d50`, `2549161b`) |
| A7 | Sửa cờ whale xoá ở nhịp tim | ✅ | `f54d22db`, deploy `26ed94e5` |
| A8 | Sửa suất `sync` mồ côi khoá 3090 20 phút | ✅ | `a6999888` deploy 04:17 |
| A9 | Dọn cơ chế cũ (13 tên/env, env dịch vụ A/B) | ✅ | rà 18/09: code/env sạch, còn tàn dư tài liệu → E Task 11 |
| A10 | Sửa phát bản LTTCODE lùi về bản đủ điều kiện | ✅ | `2b3977ad` deploy 08:35 |

## B — LTTCODE

| # | Hạng mục | Trạng thái | Bằng chứng |
|---|---|---|---|
| B1 | Nhóm trước build G1a–G9 + chặn đọc thư mục nhạy cảm | ✅ | LTTCODEAPP `146d479`…`e17a583`, `be278a8` |
| B2 | Build 0.1.5 dev | ✅ | `ccc218f` |
| B3 | Tự cập nhật + sao lưu phiên D17 | ✅ | E2E_0.1.5_gui |
| B4 | Gate bản cài | ✅ 63/0/4 | `7c38e75`, 0.1.7: `fad4a6a` |
| B5 | E2E giao diện (ảnh, code, MCP, skill, terminal, lịch hẹn, hooks, song song, chặn đọc) | ✅ | `E2E_0.1.5_gui.md`, hooks 6/6 `76903c3` |
| B5b | Memory bật mặc định + nhớ qua phiên với model thật | ✅ | `f922386`; `MEM-7Q3K` 18/09 08:29 |
| B6 | Phiên dài ~150k | ✅ (trừ cache qua khởi động lại dịch vụ) | nén 157.144→67.866; cache mất khi restart — đúng thiết kế (`KET_QUA_BAO_TRI_18_09`) |
| B7 | Chấm điểm | ✅ 99/131 | `d9f7c95` |
| B8 | 0.1.6 (hỏng 431 cookie) → 0.1.7 sửa + cổng chặn mới | ✅ | `4ba3ccb`, `2e2a91d`, 0.1.6 rollout 0 |
| B9 | 0.1.7 stable 100 % + trang tải | ✅ | `d9f7c95`; rollout 100 lúc 10:2x 18/09 |
| B10 | CI 4/4 xanh | ✅ | `8681126` |
| B11 | Đăng nhập thật phía máy chủ | ✅ 40/40 | `2e2a06f` |
| B12 | Đăng nhập/đăng xuất **trong app** | ✅ | 18/09 09:21: đăng xuất trong app ✅, đăng nhập lại bằng `khach1.thu` qua luồng PKCE thật ✅ (`signed_in.json` = khach1, sidecar sẵn sàng); sau khi máy khởi động lại vẫn đăng nhập `khach1`, sidecar sẵn sàng |
| B13 | Chọn mức suy nghĩ theo model trong app (0.1.8) | ✅ dev · stable đang dựng (100 %) | cài lên máy chủ dự án 13:28 18/09; GUI: 3.8 Nhanh/Cân bằng/Sâu nhất, 3.5 "Bật" |
| B14 | Chứng chỉ EV, máy ảo sạch | ⛔ | ngoài phiên |

## C — Tối ưu máy B

| # | Hạng mục | Trạng thái | Bằng chứng |
|---|---|---|---|
| C1 | Đo cache prompt hai model (99,6 %) | ✅ | `990ce48a` |
| C2 | Bảo trì: `--ctx-checkpoints 8`, `-b 512` (3.8), `-watch-config` | ✅ | `dac815c5` |
| C3 | Cache 24 GB/model + sàn RAM 24 GB (theo chủ dự án) | ✅ | L-25 (`c3b08e3c`…`cfb9d859`), gộp `main` `f1d949b5`; yaml kho = B `168e23c9`; RAM bão hoà 33–35 GiB, cửa sổ ảnh 57,7 GiB, 0 từ chối |
| C4 | Cửa sổ đo (một lần nạp lại, ~90 phút): **số job song song với `-c` GIỮ NGUYÊN** — 3.5 np4/5/6 @262.144, 3.8 np4/5 @221.184 (KV dùng chung `-kvu` không đổi theo slot — `llama-context.cpp:290-291`; chỉ trạng thái DeltaNet + nháp MTP tăng theo slot, `llama-memory-recurrent.cpp:101`, đo 3.5 np3→np4 +150 MiB; chỉ giảm `-c` nếu tràn shared) + ma trận `-b/-ub`; tải đo giống thật (agent, prompt trúng cache, ra ngắn) | ✅ đo + mã (chờ gate + deploy B→A) | đo `4b0515c3` (`KET_QUA_C4_18_09.md`); L-28: **3.5 `-np 4` @262.144** (tổng +15 %, mỗi luồng 57,5 % khi đủ 4 — chấp nhận), **3.8 giữ `-np 3` @221.184**; mã `79c0a4a2` nhánh `phien/np4-ltt35` (yaml + `HO_SO` + test); ma trận `-b/-ub` hoãn |

## E — LLM v2 (plan `2026-09-18-ltt-llm-v2-…`, bản 2)

| Task | Hạng mục | Trạng thái | Ghi chú |
|---|---|---|---|
| 0 | Dọn phiên "Serving v2", tag giữ commit, xoá phiên | ✅ | `4074dc02`, tag `luu-tru/serving-v2/*` |
| 1 | Gộp cấu hình B đang chạy vào `main` (hết DRIFT) | ✅ (trừ làm mới env nssm → D) | `f1d949b5`; `deploy.ps1` nay ghi đè sàn RAM mỗi lần deploy |
| 2 | Lỗi tính tiền `/messages` khi trúng cache (R-04) | ✅ deploy `488a64ed` 11:19 | `9dc8d6f2` (đỏ→xanh, đối chứng, 1.965 test provider đạt) |
| 3 | Catalog mức suy nghĩ theo model | ✅ deploy `fba73f1e` 12:43 (catalog live: 3.8 xhigh/3 mức, 3.5 medium/1 mức) | `2d350f49`…`952a792f`; 3.8 low/medium/xhigh mặc định xhigh, 3.5 một mức cố định |
| 4 | Suy nghĩ do máy chủ quyết, gỡ ghi đè 3 cửa, sàn `max_tokens` 3.5 | ✅ deploy `fba73f1e` 12:43 (L2 5/5 thành phần) | `4eee6881`…`e78e243d`; L-26; 3.5 đồng bộ: máy chủ đặt budget = max_tokens − 512 (≤ 2.048), không trả 400 |
| 5 | 3.8 khai đọc ảnh; test bản sao `-c` | ✅ deploy `488a64ed` 11:19 | `3f6ad81b` (auto_scan_video ghim 3.5 có lý do; 3.268 test đạt) |
| 6 | B gia hạn suất theo tiến triển (bỏ thu cứng 1.200 s) | ✅ deploy cổng B 13:0x (L2 gateway:llm xanh, `c5f8980c`); /health có han_im_lang_s | sau Task 1 |
| 7 | Ước token cận trên (code ×0,74, emoji ×0,16) + overhead template | ✅ deploy B 15:00 + A `51cdd73e` 15:03 | L2 4/4 trên `6b5f9471` (gateway:llm đỏ máy quét bí mật → sửa → xanh), L1 khép trên `51cdd73e`; nghiệm thu A 0 lệch/thiếu/thừa; B /health trần theo model |
| 8 | 413 trước 200 đúng câu từng giao thức | ✅ deploy A `78100df2` 17:34 (+B cổng) | đợt 3; L1 đỏ `test_1480` (dùng hằng đã gỡ ở Task 7) → sửa `9dc0b1c8` → L1 xanh; production: 200K ký tự ⇒ 400 "prompt is too long: 200289 tokens > 186368" trước khi tới B |
| 9 | Tách ngưỡng nén Claude Code/Codex; bộ cài cập nhật khoá LTT | ✅ deploy `488a64ed` 11:19 | `1b143291`, `2c3fbebd` (đo Claude Code 2.1.274: trừ 33k; nay nén 138.458/176.141); phần `examples.py` giao Task 3–4 |
| 10 | Công cụ kiểm định kỳ (+ R-16) | ✅ mã xong (nhánh `phien/kiem-dinh-ky` `19845e9f`, chờ gộp) | canary 0/432 + np4 0/140; needle 100–200K 3.8 đạt 8/8 (#27756); `cong_mtp` 3.5 đạt, 3.8 1/48 rỗng (cần E3 đối chứng — cửa sổ sau); p95 TTFT 32–33 s do prefill dài; RUNBOOK §4b lịch chạy lại |
| 11 | Dọn bản sao gõ tay + tài liệu sai | ✅ deploy đợt 3 `78100df2` | `0f279550`…`e72b6062`; mục adapter LTTCODE ở Task 15 (`eda8313`) |
| 11b | `gate.py --pham-vi` nhận NHIỀU thành phần một lượt | ✅ gộp `main` `78100df2` | `ce67afc4`; dùng ngay cho L2 np4 (5 thành phần một lượt) |
| 12 | Chất lượng 3.5 theo model card + A/B (+ R-10, R-17) | ✅ không đổi production | 402 lượt: presence 1,5 / temp 0,6 / budget 4096 không thắng rõ; **R-10: giữ `base_instructions` rỗng** (58→47, p=0,007); R-17: `preserve_thinking` bị llama.cpp che (`preserve_reasoning`), đo lại với nhiều lượt người dùng |
| 13 | LTTCODE chọn mức suy nghĩ theo model (0.1.8) | ✅ 0.1.8 dev 100 %, kiểm GUI trên máy thật | LTTCODEAPP `a629cd5`, `a224365`, `299e7d5` |
| 14 | LTTCODE: agent `subagent_doc_nhanh` chạy 3.5 (chỉ đọc, không mạng) + trần in-flight theo model (3.8: 3, 3.5: 3) + skill chia việc + eval 20 việc/10 ca chèn lệnh | 🔵 đang làm (chủ dự án duyệt 18/09) | nhánh LTTCODEAPP `phien/subagent-doc-nhanh`; tăng 3 → 6 request song song |
| 15 | LTTCODE: trần 25k token + ≤ 50/60 công cụ | ✅ mã (chờ eval live) | `phien/tran-so-cong-cu`: `2cf4d25`, `eda8313`, `407ebe7`, `0ae47f7`; mặc định 52 → **49**, đủ MCP **57** nhờ plugin `mcp-resources-ltt` (DIV-003) |
| 16 | LTTCODE: nâng bộ skill ngang/hơn Claude Code | ✅ mã (nhánh `phien/nang-skill` `4076b19`) | 29 skill (10 cộng đồng ghim commit); 3.8 98,9 %, âm tính 0/24; 3.5 62,1 % (ít tự gọi `skill` — giới hạn model, dòng định tuyến làm tệ hơn ⇒ gỡ); việc sau: harness gợi ý skill theo từ khoá |
| 17 | Xếp hàng A: một prefill dài mỗi lúc (luồng nhỏ chờ sau prefill 32K ~35 s, C4) | ⬜ | L-28 "phát hiện đi kèm"; đo TTFT người mới đến khi cá voi đang prefill |
| — | R-06, 07, 10, 11, 14, 16, 17, 18, 23 của phiên cũ | ⬜ | xác minh từng mục trên tag lưu trữ |

## F — Dọn tài liệu toàn hệ thống (chủ dự án yêu cầu 18/09; làm SAU khi xong E)

| # | Hạng mục | Trạng thái |
|---|---|---|
| F1 | Lập danh sách dọn (chỉ đọc) | ✅ | `docs/superpowers/plans/2026-09-18-don-tai-lieu.md` — 8 lô, ~5 giờ |
| F2 | Dọn theo lô (mỗi lô một commit): sửa chữ / gắn "ĐÃ GỠ" / chuyển `docs/_luutru` kèm con trỏ / gộp về tệp chủ | ⬜ |
| F3 | Phép chặn tái phát: kiểm tài liệu sống không nhắc tên đã gỡ ngoài đoạn "ĐÃ GỠ" | ⬜ |
| F4 | Dọn memory (chỉ mục + tệp sai) | ⬜ |
| F5 | Sửa số "≤ ~12k token" cũ ở LTTCODEAPP `plans/2026-09-17-bat-cong-cu-harness.md:62` (đã thay bằng 25k ngày 17/09) | ⬜ |

## D — Tổng kết phiên

| # | Hạng mục | Trạng thái |
|---|---|---|
| D1 | Gộp nhánh còn treo: `phien/bench-may-b` (6), `phien/lttcode-skills` (1), `phien/lttcode-updater` (1), các nhánh E | ⬜ |
| D2 | **L3 một lần** trên `main` cuối (sau khi hết pha) → khép nếu đỏ | ⬜ |
| D3 | Deploy nếu có thay đổi sau L1/L2 cuối | ⬜ |
| D4 | Push `origin` cả hai kho | ⬜ |
| D5 | NHAT_KY, memory, xoá luật tạm SSH máy B trong `.claude/settings.local.json` | ⬜ |
| D6 | Dọn worktree tạm của phiên (`-r04`, `-suy-nghi`, `-vision`, `-nen-claude`, `-cache-24`, `-bao-tri-b`, `-phat-hanh`, `-faq-hooks`, `-suat-mo-coi`, `-lttcode-faq`, `-llm-hang-cho`, `-llm-gateway-vatly`, `-bench-b`…) sau khi gộp | ⬜ |

---

## Sự cố trong phiên (đã xử lý)

| Giờ | Sự cố | Xử lý |
|---|---|---|
| 17/09 23:34 | Hai job lớn prefill chồng (cờ whale xoá ở nhịp tim) | `f54d22db` |
| 18/09 ~06:xx | Cache 24 GB làm RAM trống < 48 GB ⇒ B từ chối mọi LLM ~10 phút (không khách bị ảnh hưởng) | hạ 12 GB, rồi chủ dự án yêu cầu 24 GB + sàn 24 GB (C3) |
| 18/09 07:1x | LTTCODE 0.1.6 "Failed to load plugins" (431 do cookie tích tụ) | rollout 0, xoá cookie, 0.1.7 sửa gốc + cổng chặn |
| 18/09 | Hộp cập nhật mở khuất sau cửa sổ chính | `2e2a91d` |
| 18/09 | Suất `sync` mồ côi khoá 3090 20 phút | `a6999888` |
| 18/09 09:24 | **Máy A treo 13 phút** (4 agent pytest `-n 6` cùng lúc + job realesrgan của bot; RAM trống 10,5 GiB) — chủ dự án khởi động lại | `KHAM.bat` xác nhận; luật mới: lệnh nặng của agent chạy qua trình bọc giữ khoá `cpu_nhieu`, `-n` ≤ 4, 1 lượt nặng toàn máy (memory `agent-song-song-phai-xep-hang-khoa-may`); 4 agent chạy tiếp từ worktree, không mất việc |

## Quyết định 18/09 — YaRN / ngữ cảnh 1M: KHÔNG dùng

Không vừa VRAM (3.8 @262K cần ~25,2 GB/24; 1M cần 44 GB; 3.5 @524K thiếu 4,8–7 GB), không có nhu cầu (phiên nén ở 138–176K), llama.cpp còn lỗi mở với qwen35 (#27090, #27756), YaRN tĩnh làm kém văn bản ngắn (Qwen tự cảnh báo). Xem lại khi: có khách cần > 262K + card ≥ 48 GB riêng + hai lỗi đã sửa ⇒ hồ sơ riêng YaRN ×2 (524K) + RULER trước khi mở. Không nâng 3.8 lên 262.144 (tràn VRAM, lợi 18,5 % ngữ cảnh không phiên nào dùng).

## Rủi ro mới cần xử lý sớm

- **llama.cpp #27148 (đang mở):** cache prompt trên RAM có thể lẫn hội thoại của người khác vào slot mới khi tải đồng thời — áp dụng mọi `--cache-ram` khác 0 (kể cả mặc định 8192). ⇒ **E Task 10 (canary cô lập) chạy ngay giờ vắng**; nếu thấy rò rỉ: `--cache-ram 0` cho tới khi có bản vá.

## Chờ chủ dự án

- (không còn) — B12: chủ dự án cho dùng tài khoản thử `tai_khoan_thu.py` để đăng nhập lại (18/09).

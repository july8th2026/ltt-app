# CHECKPOINT — Mobile Pack V1

Tệp này là **thứ duy nhất** prompt `09_RECOVERY_AFTER_COMPACTION.txt` cần đọc để
nối lại việc. Cập nhật cuối mỗi phase, không cuối mỗi lệnh.

Cập nhật lần cuối: **2026-09-05, sau Phase C phần 1.**

## Bối cảnh phiên

| | |
|---|---|
| cây | `D:\LTTSTUDIOSAPP\.claude\worktrees\mobile-v1` |
| nhánh | `phien/mobile-v1`, fork từ `admin-mvp-v3` @ `911cd142` |
| commit gần nhất | `cef1afd3` (dọn chú thích) · `d87b92b9` (checkpoint) · `bec5643d` (Phase B+C) · `65926fc9` (Phase A) |
| nguồn quy trình | `G:\My Drive\AI\A LTT AII\LTT_MOBILE_AUTONOMOUS_PROMPT_PACK_V1` |
| kế hoạch | `docs/MOBILE/00_KE_HOACH.md` |
| dải số test | **700–799** (đã dùng 700, 701) |
| máy chủ đo | `python tools\studio_dev.py --cong 8123 --giu` — **hiện ĐANG TẮT** |
| bảng cho mọi app | `python tools\mobile_qa.py bang` sau khi seed |
| trình duyệt | `playwright-cli` — Chromium + WebKit 26.5 |

⚠️ Cổng **8100 là production đang chạy thật** (`C:\LTTPlatform`). Không đo trên đó.

⚠️ Phiên `LTT Voice autonomous deep audit` làm ở cây chính. Đã báo họ 05/09 rằng
Phase C sẽ sửa `apps/ltt_voice/routes/_p_audio.py`. **Chưa nhận trả lời.**

---

## Trạng thái phase

| phase | trạng thái | bằng chứng |
|---|---|---|
| **A** — kiểm kê + baseline | ✅ PASS | `01_MATRIX.md`, `02_BASELINE.md`, `03_BACKLOG.md`, `anh/` |
| **B** — hợp đồng shared | ✅ PASS | `04_SHARED_CONTRACT.md` — 7/7 năng lực có quyết định |
| **C** — shared media + P0 | 🟡 **PHẦN 1 XONG** | xem dưới |
| D — media generator | ⬜ | |
| E — editor phức tạp | ⬜ | |
| F — bề mặt chuẩn | ⬜ | |
| G — harness + ma trận | ⬜ | |
| H — cổng phát hành cuối | ⬜ | |

## Phase C — đã xong / còn lại

### Đã xong, có bằng chứng

| việc | bằng chứng |
|---|---|
| `platform_core/phat_media.py` — bộ trả lời Range theo RFC 9110 | `test_700` (35 phép kiểm) |
| Migrate `chatltt/_p_media.py` | `test_701` (12 phép kiểm qua HTTP thật) |
| Migrate `ltt_voice/_p_audio.py` | `test_701` + đo curl trên máy chủ 8123 |
| `voice.js` bắt Promise `play()` + đường lui `<audio controls>` | đo trên WebKit: rơi đúng vào đường lui |
| CSS: `viewport-fit=cover` · safe-area · vùng chạm · cỡ chữ ô nhập | sweep trước/sau, 2 trình duyệt |
| `/huong-dan` hết tràn ngang | sweep: 1 → 0 route tràn |

**Số đo trước → sau (390×844, Chromium; WebKit cho cùng kết quả):**

| chỉ số | trước | sau |
|---|---:|---:|
| route tràn ngang | 1 | **0** |
| ô nhập < 16px (cảm ứng) | 55 | **0** |
| ô nhập < 16px (desktop 1440) | 57 | **57** ✅ không đổi |
| vùng chạm < 44px | 468 | **195** |
| vùng chạm < 44px (desktop) | 747 | **747** ✅ không đổi |

**Range trên máy chủ thật (`/ltt-voice/audio/...`):**

```
khong Range   -> 200  accept-ranges: bytes   content-length: 401324
bytes=0-99    -> 206  content-range: bytes 0-99/401324
bytes=1e8-    -> 416  content-range: bytes */401324
```

**Phát thật trên Chromium** (bấm ▶ rồi tua bằng canvas sóng):
`currentTime` 0 → 2,35s → tua → 3,57s / 4,18s; `paused=false`, `readyState=4`,
`error=null`. Request đầu là `bytes=0-` → **206** (đúng ca từng nuốt cả tệp vào RAM).

### 🔴 CÒN LẠI — và một giới hạn phải đọc trước khi làm tiếp

1. **Không đo được phát audio trên WebKit trên máy này.** Bản WebKit của
   Playwright trên Windows **không giải mã nổi cả một WAV `data:` URI tự sinh,
   không qua mạng** — `MediaError.code = 4`, `networkState = 3`. Nó vẫn báo
   `canPlayType('audio/wav') = "probably"`, tức **nó nói dối**. Chromium giải mã
   đúng tệp đó (`loadedmetadata`, `duration = 0.1`).

   ⛔ Nên Gate C của pack — *"Voice play/seek xanh trên Playwright WebKit"* —
   **không thể thoả mãn trên máy này**, và bất kỳ dòng nào ghi "WebKit phát
   được ✅" đều sẽ là bịa. Cái đo được trên WebKit: HTTP/Range (chính WebKit gửi
   Range và nhận 206), bố cục, tràn, vùng chạm, cỡ chữ.
   ⇒ **Phát audio trên Safari phải chuyển sang thiết bị thật.**

2. **Chưa đo waveform với audio dài** (`veSong` fetch + `decodeAudioData` toàn tệp).
3. **Chưa làm ChatLTT composer / bàn phím ảo / streaming / vòng đời.**
4. **Vùng chạm còn 195** — phần lớn là liên kết văn bản trong dòng (WCAG 2.5.8
   miễn trừ). Nhưng còn vài **nút thật** dưới 44px trong app React
   (`run-primary`, `blank-flow`, `primary`, `canvas-home`, `up-history-link`).
   Nguyên nhân là **cùng cái bẫy `:where()` độ đặc hiệu 0**: luật 44px của nền
   tảng thua luật chiều cao của chính component. → **để Phase E xử lý**, vì ép
   `!important` cho chiều cao có thể phá bố cục 4 app React chưa khảo sát.

## Lệnh test đã chạy

| lệnh | thời điểm | kết quả |
|---|---|---|
| `python tools\gate.py --vong-lap` | 15:28 | FAIL (1/21) — cache `--lf` rỗng ở worktree mới |
| `python tools\gate.py --vong-lap` | 15:31 | PASS (21/21) — nhưng `--lf` chạy 0,1s ⇒ **không phải bằng chứng** |
| `python tools\gate.py --vong-lap` | 16:05 | FAIL (4/21) — xuống dòng · nuốt lỗi · tài sản GUI · bộ test |
| `python tools\gate.py --vong-lap` | 16:11 | FAIL (1/21) — chỉ `test_231_nexus` |
| **`python tools\test_nhanh.py`** | 16:20 | ✅ **6050 passed, 32 skipped, 0 failed** + 67 test frontend |

⚠️ `test_231_nexus_e2e::test_MOT_ma_chi_ghep_duoc_MOT_may` đỏ **một lần** trong
lượt song song, rồi xanh khi chạy riêng, xanh với `-n 6` trong tệp nó, xanh cùng
`test_701`, và xanh ở lượt đầy đủ kế tiếp. ⇒ **flake do trạng thái rò giữa tệp**,
không liên quan thay đổi ở đây. Nếu nó đỏ lại thì đó là một việc riêng.

## Ba lần "luật tồn tại mà không làm gì" — đọc trước khi thêm luật CSS

Cùng một hình dạng lỗi lặp ba lần trong phiên này, và **cả ba đều biên dịch được,
đúng cú pháp, không lỗi nào ở đâu cả**:

1. `:where(...)` có độ đặc hiệu **0** → luật cỡ chữ 16px thua mọi luật thành phần.
   Đo lại mới thấy: 52/55 ô nhập vẫn nhỏ.
2. `env(safe-area-inset-*)` trả **0** khi meta viewport thiếu `viewport-fit=cover`.
3. `Cache-Control` mà `chatltt` tự đặt bị `server/app.py:253` ghi đè — **một câu
   lệnh chết từ trước khi tôi chạm vào**.

⇒ Luật CSS/HTTP nào cũng phải **đo lại sau khi thêm**, không được tin là nó chạy.

## Việc tiếp theo (thứ tự)

1. Waveform Voice: đo bộ nhớ/thời gian `decodeAudioData` với audio dài; ngưỡng
   phải **đo được**, không bịa.
2. ChatLTT: composer + bàn phím ảo + streaming + vòng đời (`04_SHARED_CONTRACT.md` B6).
3. Phase D: migrate 5 bản chép Range còn lại sang `phat_media`, có regression test.
4. Cập nhật `03_BACKLOG.md`: P0-1/P0-2 → đã sửa (kèm giới hạn WebKit ở trên);
   thêm mục "nút React < 44px vì `:where()`".

# LTT Voice RC1 — Nghiệm thu **Tầng 1**

> Tầng 1 = mọi bằng chứng lấy được **trước khi deploy**. Tầng 2 (`RELEASED`)
> đòi bằng chứng trên production, định nghĩa ở spec §10.2.

| | |
|---|---|
| Nhánh RC | `claude/ltt-voice-reconciliation-165a40` |
| Trunk | `admin-mvp-v3` (đã hoà vào RC ở `5df81ae1`) |
| Gốc chung | `34b4626e` |
| Spec ràng buộc | `docs/superpowers/specs/2026-09-11-ltt-voice-system-reconciliation-design.md` |
| Kế hoạch | `docs/superpowers/plans/2026-09-11-ltt-voice-rc1.md` |
| Sổ cái | `docs/LTT_VOICE/HOP_NHAT/SO_CAI.json` |
| Nhật ký thi công | `.superpowers/sdd/2026-09-11-ltt-voice-rc1/progress.md` |
| Báo cáo E2E | `.superpowers/sdd/2026-09-11-ltt-voice-rc1/tang1-e2e-report.md` |

---

## 1. Phạm vi thay đổi — đo, không ước

```
git diff --name-only 34b4626e HEAD | wc -l               -> 98 tep
  apps 33 · tests 27 · tools 16 · docs 9 · platform_core 4
  · server 3 · alembic 3 · locale 2 · setup 1
git diff --name-only 34b4626e HEAD -- frontend/ | wc -l  -> 0
```

🔑 **`frontend/` không có một tệp nào đổi.** Con số 0 ấy là thứ duy nhất cho
phép đọc bốn bước `frontend *` BỎ QUA của cổng (§3.1) là vô hại — nó là một
phép đo, không phải một lời trấn an.

---

## 2. Từng bước của kế hoạch (Task 16)

| Step | Việc | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Đối soát sổ cái | **PASS** | `tools/doi_soat_voice.py` → `RESULT: PASS (0 commit chua doi soat, 0 loi hinh dang)` |
| 2 | Đồng bộ trunk | **PASS** | `git log --oneline HEAD..admin-mvp-v3` → rỗng |
| 3 | Cửa sổ yên | **PASS** | `cua_so_yen.py trang-thai` → RẢNH trước mỗi lượt nặng; `grep loi_cho_bo_test tools/gate.py` → khớp (bản MỚI, trần 6 worker) |
| 4 | Cổng đầy đủ | §3 | bản ghi JSON máy sinh |
| 5 | E2E mock + trình duyệt | **PASS** | §4 |
| 6 | Tổng hợp **thật** VI/EN | **PASS** | §5 |
| 7 | Di trú chạy khô | **PASS** (một phát hiện ngoài phạm vi, §6.3) | §6 |
| 8 | Chấm điểm | tài liệu này | §7–§9 |

---

## 3. Cổng chất lượng đầy đủ

Bản ghi máy sinh `test-results/gates/20260911T142721Z-21580.json` (cây gate
riêng `D:\LTTSTUDIOSAPP\.claude\worktrees\ltt-voice-rc1-gate`):

```
ho_so   = day-du
ket_qua = PASS  [4 BUOC TU BO QUA, KHONG PHAI BANG CHUNG:
                 frontend agent-canvas, frontend autosub-studio,
                 frontend prompt-ai-ommi, frontend chatltt]
sha     = 031ac4c25f6569406a4b516255f5c3ed41ddddd6
tong_giay = 939.5
cay_da_doi_giua_chung = False
```

### 3.1 Bốn bước BỎ QUA — nói rõ, không giấu

`tools/gate.py` biến bước frontend thành `bo_qua` khi worktree thiếu
`node_modules/` (không nằm trong git ⇒ **mọi** cây riêng đều thiếu). Đó là
thiết kế có chủ ý, và gate **tự khai** ngay trên dòng `RESULT`.

⇒ Bốn bước ấy **không phải bằng chứng**. Thứ khiến chúng không thành lỗ hổng là
phép đo ở §1: RC1 đổi **0 tệp** dưới `frontend/`.

### 3.2 Lượt cổng cuối

Sau bản ghi trên, RC nhận thêm hai commit **chỉ chạm `tests/browser/*.js`**
(`17e7c97e`, `473b744f`).

Lượt cổng đầy đủ **cuối cùng** chạy trên `473b744f`, bản ghi
`test-results/gates/20260911T183256Z-19848.json`:

```
ho_so   = day-du
ket_qua = PASS  [4 BUOC TU BO QUA, KHONG PHAI BANG CHUNG: frontend x4]
sha     = 473b744f3feb8b46837a351c7156bfa4c8367258
tong_giay = 957.4
cay_da_doi_giua_chung = False
bo test = 10180 passed, 65 skipped, 1 xfailed, 0 failed
```

### 3.3 Hai lượt ĐỎ trước đó — và vì sao chúng không phải lỗi mã

Ghi lại đủ, vì một lượt đỏ bị giấu là một lượt đỏ sẽ quay lại.

**Lượt 1 (`20260911T175649Z-11472`, FAIL 3/33, 5 test đỏ)**

| Test đỏ | Nguyên nhân thật |
|---|---|
| `test_60::test_every_apps_subfolder_has_a_manifest` | `apps/{audio_pause,chataistudio,prompt_canh,transcript,video_assembly}` chỉ còn `__pycache__` sau khi hoà trunk — **thư mục ma**, đúng ca `docs/QUY_TRINH_WORKTREE.md` §1c |
| `test_1004::test_moi_thu_da_xoa_deu_KHONG_con_tren_dia` | như trên (`codex_sidecar`, `apps/chataistudio`) |
| `test_85::test_khong_co_ERROR_hop_dong` | như trên |
| `test_44` (2 ca) | **lỗi của chính báo cáo này**: `tang1-e2e-report.md` §11.2 dán hai chuỗi hex 32 ký tự (`public_id` giọng + vân tay `repr-*.npz`), bộ quét bắt luật `bare_32_char_hex` |

Xử: `git clean -fdX apps/` + `codex_sidecar/`; rút gọn hai chuỗi hex trong báo
cáo (`vc_7090608836…701c`, `repr-12df0b58….npz`) — **rút ngắn chuỗi, không nới
luật quét**.

**Lượt 2 (`20260911T181543Z-14400`, FAIL 1/33, 3 test đỏ)** — do chính lượt dọn
trên gây ra:

```
test_82::test_vendor_engine_co_mat
test_505::test_moi_duong_khai_deu_CO_THAT_tren_dia
test_505::test_DANH_SACH_VAN_CHUYEN_khop_dung_tap_DO_DUOC
```

`git clean -fdX apps/` xoá **mọi** thứ bị gitignore dưới `apps/` — kể cả
`apps/upscalevideo/vendor/` (48 MB) mà `QUY_TRINH_WORKTREE.md` **§1b** bắt phải
có ở mọi worktree. Tức làm đúng §1c thì phá §1b, trong cùng một tài liệu. Xử:
`robocopy` lại vendor từ cây chính (9 tệp, 47,5 MB) — §1b của tài liệu ấy đã
được bổ sung cảnh báo này trong cùng commit.

🔑 Không lượt đỏ nào trong hai lượt chạm tới **mã** của RC1. Nhưng cả hai đều
được ghi ra đây chứ không bị viết lại thành "gate xanh ngay từ đầu".

---

## 4. Playwright — tầng mock (Step 5)

Chi tiết: `tang1-e2e-report.md` §10.

| Luồng | Kết quả |
|---|---|
| D003 — ghi danh bắt khai làn (`voice_language_required`) + ghi danh EN hợp lệ | **PASS** |
| D004 — thẻ làn: LEGACY xác nhận được; `do_asr` chặn đổi ngược | **PASS** |
| T-08 — nghe thử giọng kho chung cho người **không phải chủ** | **PASS** |
| D005 — xoá lịch sử + cảnh báo khối bị ảnh hưởng + dự án "Cần tạo lại" | **PASS** |
| D002 — khai VI + văn bản EN chắc ⇒ `voice_language_mismatch` | **PASS** |
| 6 khung hình × 4 màn (tràn ngang) | **PASS 24/24** |
| 4 lớp bắt lỗi (`console.error` · `pageerror` · `requestfailed` · HTTP ≥400) | **0 vấn đề** sau danh sách cho phép theo từng bước |
| `ltt_voice_golden.js` · `negative.js` · `smoke.js` chạy ngay sau, cùng phiên | **PASS cả ba** |
| `tools/voice_e2e_check.py` | **PASS** |
| `tools/check_voice_qa.py` (rào tĩnh) | **PASS**, không pin nào bị nới |

⚠️ Trình duyệt là **Chromium của `playwright-cli`**, không phải `channel:"chrome"`
như spec §9 viết. Chrome thật là ràng buộc của **Tầng 2** (URL công khai, qua
Cloudflare). Ghi ra đây để không ai đọc §9 rồi tưởng đã làm đúng chữ.

---

## 5. Tổng hợp **thật** VI + EN (Step 6)

Toàn văn: `tang1-e2e-report.md` §11.

- Cổng giọng **THẬT** `127.0.0.1:8120` (dịch vụ `LTTStudioVoice`); token lấy từ
  `C:\LTTPlatform\secrets\app.env` theo quyền chủ dự án cấp — **không in ra**,
  không vào kho.
- CSDL vẫn là `voice-e2e` **cách ly** (hai rào `_guard()` còn nguyên) ⇒ không
  chạm dữ liệu production.
- Giọng EN dựng bằng **ghi danh một clip tiếng Anh thật** (SAPI `Zira` en-US,
  11,79 s, 16 kHz mono PCM) qua đúng cửa `POST /ltt-voice/giong/tao` với
  `ngon_ngu=en`. Engine thật sinh `repr-*.npz` sau 9 giây — tầng mock không tạo
  được tệp ấy.

| Luồng | Kết quả |
|---|---|
| VI — preset `Adam` | **PASS** — WAV 200 + `RIFF`, **không** mang dấu `ltt-voice-mock` |
| EN — giọng `RC1 Real EN` vừa ghi danh | **PASS** — như trên |
| 4 lớp bắt lỗi | **0 vấn đề** |

Một `requestfailed: net::ERR_ABORTED` xuất hiện ở lượt đầu và **đã truy ra
nguyên nhân thật**: `<audio id="lv-player" preload="metadata">` — Chromium huỷ
yêu cầu media sau khi đọc xong phần đầu của một WAV **thật**. Rào được nới
**hẹp bằng ba điều kiện cùng lúc**, và số yêu cầu bị thả được **in ra**
(`473b744f`).

---

## 6. Di trú (Step 7)

### 6.1 Migration

```
alembic upgrade head  (PostgreSQL trong)  -> chay het, khong loi
alembic heads                             -> d9a1f6c2b3e5 (MOT head)
voice_profile.ngon_ngu_nguon              -> CO
```

Chuỗi RC: `e26c9a41d8b5` (scheduler) → `e1a2b3c4d5f6` (`ngon_ngu_nguon`) →
`d9a1f6c2b3e5` (`voice_lich_su`). Hai migration của RC đều **chỉ thêm**.

### 6.2 Diễn tập khôi phục trên lược đồ thật

```
Luoc do goc  : 100 bang, 155 rang buoc
Sau khoi phuc: 100 bang, 155 rang buoc
uq_voice_owner_ten, uq_voice_ref_hash -> CON NGUYEN sau dump/restore
```

### 6.3 Một phát hiện **ngoài phạm vi RC1** — `RESTORE_DRILL=FAIL`

`tools/restore_drill_schema.py` báo `mat rang buoc uq_vps_port_map_cong`. Truy
tới gốc (đo, không đoán):

- `alembic/versions/20260824_1200_vps_mot_ip_moi_vm.py` gọi
  `op.drop_table("vps_port_map")` — bảng ấy bị xoá từ 24/08/2026 (thiết kế
  một-IP-một-VM).
- Đo trên CSDL **nguồn**, trước khi dump: `vps_port_map` **không tồn tại** ⇒
  ràng buộc không mất khi khôi phục, nó **chưa bao giờ có mặt** trong lược đồ
  hiện tại.

⇒ Đây là **danh sách kiểm cũ** nằm trong chính công cụ diễn tập, không phải lỗi
khôi phục, và không dính gì tới Voice. Phần thực chất của diễn tập (100/100
bảng, 155/155 ràng buộc, hai ràng buộc Voice sống sót) **ĐẠT**.

⚠️ Kèm theo: `test_155` tự chú thích là "đối chiếu danh sách này với lược đồ
thật", nhưng gate vẫn xanh trong khi một tên trong danh sách không còn trong
lược đồ ⇒ phép kiểm ấy **chỉ đi một chiều**. Việc sửa thuộc phiên VPS/công cụ;
ghi ra đây để nó không rơi mất.

### 6.4 Công cụ di trú làn ASR — chạy khô

Trên bản sao `voice-e2e` có một giọng mang clip **tiếng Anh thật**:

```
D003 — do lan giong cu bang ASR (CHAY KHO, nguong=0.9, luong=2)
  vce_e2e_legacy_vi  giu nguyen (vi)  do=?/khong co clip nguon (VoiceRef)
  vc_709060883646…   vi -> en  (do_tin=0.998, nguon=do_asr)  [chay kho]
  Xet: 2   Se doi: 1   Da ghi: 0   Khong chac: 1
```

🔑 `do_tin=0.998` là ASR **đo thật** trên tiếng nói thật — không phải một test
tự dựng dữ liệu rồi tự khẳng định kết quả.

---

## 7. Ma trận nghiệm thu Voice (spec §8.2)

| Nhóm | Ca | Kết quả | Bằng chứng |
|---|---|---|---|
| Studio | VI+VI · EN+EN · VI+EN chặn · EN+VI chặn · trộn có dấu ⇒ vi · D002 | **PASS** | `test_355`, `test_384`, `test_522`; Playwright D002; tổng hợp thật VI/EN |
| Giọng | ghi danh bắt khai · consent · làn · active · preview · tắt · thu hồi · `loi` · khai làn · khai ngược `do_asr` chặn · chủ sở hữu | **PASS** | `test_520`, `test_521`, `test_351`, `test_526`; Playwright D003/D004 |
| Kho chung | danh mục · lọc VI/EN · preview cho người không phải chủ · license · đọc được · sửa bị từ chối | **PASS** | `test_528`, `test_508`, `test_526`; Playwright T-08 |
| Dự án | tạo · khối · giọng/khối · tạo một · tạo tất cả · an toàn làn + `ma_loi` · tệp hết hạn ⇒ "cần tạo lại" | **PASS** | `test_357`; Playwright D005 |
| Lịch sử | danh sách · lọc · phát · tải · đọc lại · giọng ôi · lệch làn · xoá (hộp xác nhận nêu khối) · đã tải | **PASS** | `test_525`, `test_348`; Playwright D005 (`/anh-huong` + hộp xác nhận) |
| API | xác thực · kiểm-trước 400 có mã · không giữ tiền khi bị từ chối · job · poll · artifact · hết hạn | **PASS** | `test_524`, `test_503` |
| Runtime | queued · running · done · failed · retry · sidecar bận · không có worker | **PASS** | `test_501`; `apps/ltt_voice/jobs.py` (kích hoạt có điều kiện, `loi` cho lỗi vĩnh viễn) |
| Credit | báo giá · giữ · quyết toán · hoàn · thất bại · thử lại · **nộp trùng ở MỌI cửa** | **PASS** | `test_356` (bánh cóc mọi cửa tiêu tiền) |
| Lưu trữ | cô lập chủ sở hữu · kho chung · nguồn · preview · output · Range · MP3 | **PASS** | `test_343`, `test_346`, `test_901`, `test_500`; cửa phục vụ ở `routes/_p_audio.py` |
| Tổng hợp **thật** VI + EN qua pipeline đầy đủ | | **PASS** | §5 — trước lượt này ô ấy là `BLOCKED` |

---

## 8. Bảng chấm 100 điểm

Khung điểm lấy nguyên từ yêu cầu gốc (spec §8.3). `BLOCKED` = **0 điểm** của
mục ấy.

| Mục | Trần | Chấm | Căn cứ |
|---|--:|--:|---|
| Architecture | 10 | **10** | Spec + 13 bất biến (§5) + sổ cái máy đọc được + `doi_soat_voice.py` PASS ⇒ không commit Voice nào rơi mất (INV-CHU-1) |
| Studio | 10 | **10** | `test_355`/`384`/`522` + Playwright D002 + tổng hợp **thật** VI/EN |
| Language | 10 | **10** | D002/D003/D004 xanh ở cả test lẫn trình duyệt; ASR đo thật `do_tin=0.998` |
| Catalog | 8 | **8** | `test_528`/`508`/`526` + T-08 (người **không phải chủ** nghe được) |
| My Voices | 8 | **8** | `test_520`/`521`/`351`; vòng đời + thu hồi xoá cả `khoa_chung` |
| Projects | 8 | **8** | `test_357` + D005 badge "Cần tạo lại" trên giao diện thật |
| History | 6 | **6** | `test_525`/`348` + `/anh-huong` + hộp xác nhận nêu đúng khối |
| API | 6 | **6** | `test_524` (hook kiểm-trước ở **cả** `/quotes` và `/jobs`) + `test_503` |
| Jobs | 8 | **8** | `test_501`: cổng chết = lỗi hạ tầng · cổng **bận** = xếp lại · trần thời gian mọi cửa · làn worker riêng. ⚠️ ca *"không có worker"* chỉ được phủ **gián tiếp** qua trần runtime bắt job TREO, không có test gọi đúng tên |
| Credit | 8 | **8** | `test_356` — bánh cóc **mọi** cửa tiêu tiền, chốt theo TẬP HỢP |
| Storage | 6 | **6** | `test_343`/`346`/`901`/`500` + cửa phục vụ `voice/chung/*` tra CSDL mỗi lượt |
| GUI | 6 | **6** | 24/24 tổ hợp khung hình, 0 tràn ngang, 0 lỗi 4 lớp |
| Tests/Browser/CI | 4 | **3** | 5 bộ Playwright + rào tĩnh + cổng đầy đủ PASS — **trừ 1**: spec §9 đòi Chrome thật (`channel:"chrome"`) ở tầng này, lượt chạy dùng Chromium của `playwright-cli` |
| Deploy/Rollback | 2 | **2** | Migration chỉ thêm, MỘT head, dump/restore giữ 100/100 bảng + 155/155 ràng buộc; `--dao` đảo được lượt ASR; `app.previous` là đường lui |
| **Tổng** | **100** | **99** | |

Không mục nào `BLOCKED`. Bốn mục mà spec §8.3 đòi "không được BLOCKED"
(Language, Credit, Studio, Jobs) đều đạt trần.

---

## 9. Kết luận

## **`READY_FOR_DEPLOYMENT`** — 99/100 tại `473b744f`

Đủ điều kiện của spec §12: cổng đầy đủ PASS trên **đúng SHA đỉnh RC**, không ô
nào `BLOCKED`, điểm ≥ 98, sổ cái đối soát sạch, migration một head và chỉ thêm.

### 9.1 Ba điều người đọc phải biết trước khi bấm deploy

1. **SHA được cổng chứng nhận là `473b744f`.** Commit tài liệu này nằm **sau**
   nó và chỉ chạm `docs/` + `.superpowers/` (không tệp mã nào) — kiểm bằng
   `git diff --name-only 473b744f HEAD`. Deploy phải đi từ SHA của commit tài
   liệu, và điều lệch duy nhất so với bản đã cổng là tài liệu.
2. **Bốn bước `frontend *` là BỎ QUA, không phải PASS** — vô hại vì RC đổi 0
   tệp dưới `frontend/` (§1), không phải vì chúng "chắc là ổn".
3. **Tầng 2 chưa có gì.** Mọi ô của spec §10.2 (SHA khớp `/health/version`,
   `nghiem_thu_deploy` 0/0/0, `alembic upgrade head` trên production, di trú ASR
   thật, Playwright trên URL công khai, Public API live) đều **chưa chạy** — RC
   này **không** được gọi là `RELEASED`.

### 9.2 Việc còn nợ, không chặn Tầng 1

| Việc | Vì sao không chặn |
|---|---|
| `tools/restore_drill_schema.py` giữ tên `uq_vps_port_map_cong` của một bảng đã xoá 24/08 | Công cụ của hệ VPS; phần thực chất của diễn tập vẫn ĐẠT (§6.3) |
| `test_155` chỉ đối chiếu **một chiều**, nên một tên thừa trong danh sách ấy không làm nó đỏ | cùng hệ, cùng phiên xử |
| Chạy bộ Playwright bằng Chrome thật | là ràng buộc của Tầng 2 (URL công khai qua Cloudflare) — đã trừ 1 điểm ở §8 |
| Ca *"không có worker"* chưa có test gọi đúng tên | phủ gián tiếp bằng trần runtime bắt job TREO |


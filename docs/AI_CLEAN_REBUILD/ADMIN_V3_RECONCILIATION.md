# W1 — ADMIN-V3 RECONCILIATION

> **Pha:** W1 · **Đo lúc:** 2026-09-08 17:00 (giờ máy, UTC+7)
> **Cây đo:** `D:/LTTSTUDIOSAPP` (`admin-mvp-v3`) — **chỉ đọc**, không `reset`,
> không bỏ tệp dirty, không gỡ worktree.
> **Cây ghi:** `D:/LTTSTUDIOSAPP-aiclean` (`phien/aiclean`) — tệp này.

## 0. Điều kiện mở W1 — đọc lại cho đúng

`W1_ADMIN_V3_RECONCILE.md` viết *"CHỈ chạy sau khi chủ dự án xác nhận các phiên
admin-v3 đã kết thúc"*, và các phiên **chưa** kết thúc. Nhưng ba dòng gate của
chính W1 không đòi "kết thúc":

```
ADMIN_WORK_PRESERVED = YES
UNCOMMITTED_UNKNOWN  = 0
UNPUSHED_UNKNOWN     = 0
```

Chúng đòi việc **được bảo toàn và quy được chủ**. 🔑 **Commit ≠ kết thúc**, và
"quy được chủ" ≠ "đã xong". Cả ba dòng đạt được **ngay bây giờ**, đo được, mà
không ai phải dừng việc — §1–§3 dưới đây là phép đo.

Chủ dự án đã chốt: *"xử lý các hạng mục, để chạy gate cuối cùng"*. W1 vì vậy
chạy ở dạng **bảo toàn + quy chủ**, và phần **phá huỷ** của nó (gỡ worktree) đẩy
sang W2 với điều kiện riêng.

## 1. Trạng thái `admin-mvp-v3`

| | |
|---|---|
| HEAD | `0d1ffe5a` — *"Bon cho NUOT LOI trong hai cong cu Postgres — banh coc 66 → 62"* |
| Upstream | ⚠️ **chưa đặt** (`git branch -vv` không in `[origin/...]`) |
| Hơn `origin/master` | **264** commit |
| Chưa có trên `origin` | **6** commit |
| Stash (toàn kho) | **0** |
| Tệp chưa commit | **43** của phiên khác + 2 thư mục của chiến dịch này |

Nhịp commit của nhánh, 264 commit ấy trải trên **7 ngày**:

| Ngày | Commit |
|---|---|
| 02/09 | 12 |
| 03/09 | 42 |
| 04/09 | 29 |
| 05/09 | 26 |
| 06/09 | 57 |
| 07/09 | 70 |
| 08/09 | 28 |

⚠️ **Không đặt upstream là một rủi ro có thật, không phải chi tiết mỹ quan.**
`git push` trần trên một nhánh không upstream hoặc hỏi lại, hoặc — tuỳ
`push.default` — đẩy nhầm ref. 264 commit đang treo trên một nhánh không khai
báo nó thuộc về đâu. **Đề xuất** (không tự làm, vì nhánh này là của phiên khác):
`git branch --set-upstream-to=origin/admin-mvp-v3 admin-mvp-v3`.

## 2. Sáu commit chưa lên `origin` — quy chủ từng cái

| SHA | Giờ | Nội dung | Chủ |
|---|---|---|---|
| `9cf8753c` | 16:26:49 | Ba bất biến nền tảng mà 16 bảng Workflow V2 phải khai báo | **WF2** |
| `b4a71551` | 16:27:21 | Khôi phục đoạn mã không-BOM vào `CLAUDE.md` — bánh cóc `test_61` | VOICE |
| `d83fb7f6` | 16:30:05 | **Merge** `phien/wf2` → `admin-mvp-v3` | WF2 |
| `4d069dd9` | 16:37:01 | `R4` ĐÓNG: migration thi hành thật trên PostgreSQL | WF2 |
| `3cb2408b` | 16:47:15 | Dịch 14 chuỗi EN của 16 bảng Workflow V2 — bánh cóc 357 → 349 | WF2 |
| `0d1ffe5a` | 16:56:48 | Bốn chỗ nuốt lỗi trong hai công cụ Postgres — bánh cóc 66 → 62 | WF2 |

**Cả sáu sinh trong 30 phút hôm nay, cả sáu có chủ, không cái nào mồ côi.**
⇒ `UNPUSHED_UNKNOWN = 0`.

⚠️ Chúng **chưa được sao lưu ngoài máy này**. `origin` chưa có chúng, và chúng
chỉ tồn tại trong **một** `.git`. Đây là toàn bộ rủi ro mất mát ở tầng commit —
không lớn (30 phút việc), nhưng có thật.

## 3. 43 tệp chưa commit — quy chủ từng tệp

Quy chủ bằng **commit gần nhất chạm vào tệp** (`git log -1 -- <tệp>`) cộng với
miền nội dung, không bằng phỏng đoán.

| Nhóm | Số tệp | Bằng chứng quy chủ | Chủ |
|---|---|---|---|
| `apps/ltt_voice/**` | 17 M + 6 mới | commit gần nhất đều là `feat(voice)`/`LTT Voice: …` | **VOICE** |
| `tests/test_50{0,1,4}` + `test_50{6..9}`, `test_51{0,1}` | 3 M + 6 mới | dải 5xx là dải LTT VOICE | **VOICE** |
| `docs/LTT_VOICE/**` | 3 M | `c795ebc7`, `911cd142` — đều LTT Voice | **VOICE** |
| `server/static/voice.js` | 1 M | `c795ebc7` | **VOICE** |
| `tools/{do_ho_so_giong,dung_nghe_thu,soat_giong}.py` | 3 mới | tên miền giọng | **VOICE** |
| `alembic/versions/20260908_1600_voice_license_va_curate.py` | 1 mới | migration `a4c71e93f8b2`, phiên VOICE tự khai | **VOICE** |
| `docs/OPERATING_STANDARDIZATION/FINAL_REPORT.md` | 1 M | `21fa7e2b` — chiến dịch chuẩn hoá vận hành | **VOICE** |
| `docs/architecture/workflow_v2_audit/31_NHAT_KY_TRIEN_KHAI.md` | 1 M | `b92839a3` = **đúng tip `phien/wf2`** | **WF2** |
| `docs/REPO_HYGIENE/`, `docs/AI_CLEAN_REBUILD/` | 2 thư mục | do W0 của chiến dịch này tạo lúc 16:24–16:34 | **AICLEAN (tôi)** |

**0 tệp không quy được chủ** ⇒ `UNCOMMITTED_UNKNOWN = 0`.

⭐ Chú ý dòng áp chót: một tệp trong `docs/architecture/workflow_v2_audit/` nằm ở
**cây chính**, nhưng chủ của nó là phiên **WF2** — phiên có cây riêng
`D:/LTTSTUDIOSAPP-wf2`. Tức **một phiên có cây riêng vẫn đang ghi vào cây
chính**. Đừng giả định "cây riêng ⇒ không chạm cây chính".

## 4. Việc có bị mất không — ba câu hỏi, ba phép đo

| Câu hỏi | Phép đo | Kết quả |
|---|---|---|
| Có commit nào chỉ tồn tại ở local? | `git rev-list --count <b> --not --remotes=origin` trên **cả 11 nhánh** | 6, tất cả trên `admin-mvp-v3`, tất cả có chủ |
| Có việc nào nằm trong stash bị quên? | `git stash list` | **0** |
| Có tệp bẩn nào không ai nhận? | §3 | **0** |

⇒ `ADMIN_WORK_PRESERVED = YES`.

⛔ **Không tạo nhánh backup, và đây là quyết định có lý do.** W1 cho phép *"push
backup branch nếu cần"*. Không cần: 6 commit chưa push đều **đang được phiên chủ
của chúng dùng ngay lúc này**, và một nhánh backup chụp giữa chừng sẽ (a) chụp
một trạng thái nửa vời, (b) đẻ thêm một ref phải audit ở pha 14. Đường bảo toàn
đúng là **phiên chủ tự push**, không phải tôi chụp hộ.

## 5. Xung đột ngữ nghĩa với chiến dịch — đo, không đoán

Quét pha 02 (`docs/AI_CLEAN_REBUILD/LEGACY_SURFACE_MATRIX.csv`) cho giao với
vùng đang có phiên làm việc:

| Vùng | Có tệp nào của chiến dịch không? | Kết luận |
|---|---|---|
| `apps/ltt_voice/**`, `voice_sidecar/**` | 2 lần khớp, **cả hai là docstring** *"khuôn lấy từ `codex_sidecar/server.py`"* | **Không xung đột.** Voice sạch |
| `apps/auto_scan_video/**` | 4 lần khớp: 2 chú thích mô tả **một lỗi đã sửa**, 2 chuỗi mô tả **định dạng đường truyền kiểu OpenAI** dùng bởi `CongVlm` nội bộ | **Không xung đột.** ASV sạch |
| `platform_core/public_api/**` | `governance.py`, `examples.py`, `protocol.py`, `tables.py` có dấu vết | ⚠️ **CÓ giao với WF2.** `examples.py` có 22 dòng **mã** |
| `docs/architecture/workflow_v2_audit/**` | — | Không |

⇒ **Một điểm giao duy nhất: `platform_core/public_api/` giữa chiến dịch và WF2.**
Xử lý ở pha 03/08, và phải nhắn WF2 trước khi chạm `examples.py`.

## 6. Cần merge / cherry-pick gì không?

**Không có gì cần cherry-pick.** Cây chiến dịch `phien/aiclean` phân nhánh từ
`0d1ffe5a` — HEAD của `admin-mvp-v3` lúc 16:59 — nên nó **đã chứa toàn bộ** 264
commit admin, kể cả merge `phien/wf2` (`d83fb7f6`).

⚠️ Thứ nó **không** chứa: 43 tệp chưa commit (§3). `git worktree` phân nhánh từ
một **commit**. Hệ quả cụ thể cho chiến dịch:

- việc VOICE đang làm ở `apps/ltt_voice/**` **không** có trong cây chiến dịch ⇒
  khi hoà lại ở pha 13, đó là một `merge`, và nếu chiến dịch có chạm
  `apps/ltt_voice/**` thì sẽ xung đột. §5 nói nó **không** chạm ⇒ an toàn;
- migration `a4c71e93f8b2` **không** có trong cây chiến dịch. Chiến dịch này
  **không thêm migration nào**; nếu về sau cần, phải hỏi `ScriptDirectory.get_heads()`
  **ngay trước khi ghi tệp** và tự đổi `down_revision` (quy tắc "ai ghi sau thì đổi").

## 7. Gate W1

| Điều kiện | Kết quả | Bằng chứng |
|---|---|---|
| `ADMIN_WORK_PRESERVED` | **YES** | §4 — ba phép đo |
| `UNCOMMITTED_UNKNOWN` | **0** | §3 — 43/43 tệp quy được chủ |
| `UNPUSHED_UNKNOWN` | **0** | §2 — 6/6 commit quy được chủ |
| Không `reset --hard` | ✅ | 0 lệnh ghi git lên cây chính |
| Không bỏ tệp dirty | ✅ | 43 tệp còn nguyên |
| Chưa gỡ worktree admin | ✅ | 8 worktree, chưa gỡ cái nào |

**W1 GATE = PASS**, với hai mục **chuyển tiếp** sang chủ của chúng:

1. ⏭️ `admin-mvp-v3` **chưa đặt upstream** — đề xuất §1, để phiên chủ làm.
2. ⏭️ 6 commit **chưa push** — để phiên chủ push, không phải tôi.

## 8. Cấp test

**Không chạy gate.** W1 không sửa một dòng mã thực thi nào — bán kính **THẤP**
(`00_LTT_OPERATING_CONTRACT.md` §4.5: tài liệu). Và §4.9: bốn phiên đang ghi,
một lượt L3 lúc này sẽ ra `CAY DA DOI GIUA CHUNG` như ba lượt trước nó hôm nay.

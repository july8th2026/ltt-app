# Diễn tập khôi phục backup LTTPlatform — 23/09/2026

Câu hỏi đặt ra: **bản sao lưu `D:\LTTBackups` có khôi phục được thật không?**
Đáp án không nằm ở niềm tin mà ở đo. Công cụ:
`deploy/windows/dien_tap_khoi_phuc.ps1` + `deploy/windows/dien_tap_kiem.py`
(chạy trên CSDL tạm `lttplatform_dienthu_<stamp>`, không đụng live CSDL,
không dừng dịch vụ, tự dọn sau khi xong).

Bản sao lưu dùng để diễn tập: `ltt_data_20260923_023001.zip` (193.733.581 B,
163 entries, dump nội sinh 02:30:14) + `ltt_secrets_20260923_023001.zip`
(3.797 B, chỉ chứa `app.env` 7.077 B).

## Câu 1 — Bản sao lưu mới nhất nạp vào CSDL sạch được không, mất bao lâu?

**Được — XANH, exit 0. Tổng RTO diễn tập: 24,01 s.**

| Bước | Thời gian đo |
|---|---|
| Kiểm toản zip (163 entries) | 0,02 s |
| Chép + giải nén ra `%TEMP%` | 2,01 s |
| Tạo CSDL tạm (superuser) | 0,33 s |
| **pg_restore** (99.373.232 B, `--no-owner -1`) | **19,08 s** |
| Đối chiếu 11 bảng + sạch sổ credit | 2,50 s |
| **alembic upgrade head** (3 migration) | **1,37 s** |
| Kiểm toản zip secrets | ~0 s |

Ước tính khôi phục thật (dừng dịch vụ + bản sao lưu trước + /health/ready)
nằm **dưới 15 phút** — chi tiết thủ công ở `docs/RUNBOOK_KHOI_PHUC.md`.

## Câu 2 — Dữ liệu đủ không?

Trong CSDL tạm sau khi nạp, so với CSDL live đo trực tiếp lúc ~18:15 cùng ngày:

| Chỉ số | Trong dump (02:30) | Live (18:15, +15h45) | Kết luận |
|---|---|---|---|
| users | 35 | 35 | khớp |
| jobs | 7.659 | 7.675 | +16 job sau giờ backup — đúng hướng |
| credit_entries | 45.472 | 46.094 | +622 sau giờ backup |
| api_keys | 4 | 4 | khớp |
| job_events | 103.418 | — | có |
| payment_orders | 11 | — | có |
| credit_packages | 5 | — | có |
| Bảng public | 101 | — | đủ 11 bảng bắt buộc + `alembic_version` |

**Sạch sổ credit (đo trên chính CSDL đã nạp):**

- `so_du = SUM(delta)` đúng với mọi user — **0** user lệch.
- Bút toán mồ côi (credit entry không có user) — **0**.
- User có số dư âm — **0**. Tổng bút toán trong sổ: 70.992.
- Job mồ côi (không có user) — **0**.

Bản sao lưu **đầy đủ** cho 4 nhóm cần: user, sổ credit, job, API key.

## Câu 3 — Dump hỏng có làm diễn tập ĐỎ không, hay xanh giả?

**ĐỎ thật, exit 1.** Chạy lại với dump bị cắt thủ công ở 2 MB
(`-Dam`, phần còn lại giữ nguyên):

- `pg_restore`: **ĐỎ** — `ma 1 - 'end of file' trong stderr: dump co the bi CAT ho`.
- `bang_co_dat`: **ĐỎ** — 0 bảng public (cờ `-1` rollback cả transaction,
  không để CSDL nửa vời).
- `alembic_khop_head`: **ĐỎ** — 0 version trong `alembic_version`.
- `ket_qua = DO`, **exit 1**, RTO 4,68 s (thất bại nhanh), tự dọn CSDL tạm.

**Phát hiện quan trọng (đã sửa trong công cụ):**

1. **Mã xuất pg_restore KHÔNG đủ để bắt dump -Fc bị hỏng.** Dump custom bị
   cắt trả về **rc = 1** ("completed with warnings"), không phải rc ≥ 2.
   Dòng lỗi có dạng `pg_restore: error: could not read from input file:
   end of file` — khác hình dạng `ERROR` của psql nên bộ đếm cảnh báo cũ
   in "0 canh bao" và để bước pg_restore **xanh giả**. Công cụ bây giờ
   đếm cả `pg_restore: error:` trong stderr, đánh đỏ khi rc ≥ 1, và gắn
   nhãn 'end of file' vào báo cáo.
2. **Lưới an toàn thứ hai độc lập:** dù pg_restore "hoàn tất có cảnh báo",
   tầng đối chiếu (`dien_tap_kiem.py`) vẫn đỏ vì CSDL không có bảng. Hai
   lưới, một báo dump hỏng.
3. **Alembic lệch KHÔNG nhất thiết là đỏ** — nó chỉ đỏ khi *runbook không
   nói phải chạy `alembic upgrade head` sau khi khôi phục*. Bằng chứng:
   dump 02:30 mang `alembic_version = e4a19c07b5d2`, head của tree đã
   deploy (`C:\LTTPlatform\app`) là `5e1a9c46b2d7` — lệch đúng 3 migration
   video-crawler (`vc_phien`, `vc_da_tai`, `vc_tai_khoan`, commit 23/09
   00:58) vì migration chỉ áp dụng lúc deploy, còn backup chạy 02:30.
   Đây là hành vi **chuẩn** của vòng đời backup, không phải lỗi bản sao
   lưu. Diễn tập đã chạy thật `alembic upgrade head` lên CSDL tạm
   (1,37 s) và xác minh version sau = head. Quy tắc khôi phục thật đã ghi
   vào `docs/RUNBOOK_KHOI_PHUC.md`.
4. Lỗ hổng còn mở: `deploy/windows/restore.ps1` (đường khôi phục thật)
   **chưa có bước alembic** — đã ghi nhận trong runbook, chưa vá (ngoài
   phạm vi phiên này).

## Câu 4 — Muốn dựng lại máy sạch thì bản sao lưu thiếu gì?

Đo trực tiếp trên `C:\LTTPlatform\data\` lúc 18:20:

| Thứ | Trong backup? | Kích thước đo | Ghi chú |
|---|---|---|---|
| `lttplatform.dump` | Có | 99,4 MB | đã chứng minh nạp lại được |
| `config.json`, `*.enc`, `content_history.db`, `audit_log.jsonl` | Có | 4,6 / 28,7 KB… | đúng mẫu của `backup.ps1` |
| `voice_goc/` + `files_voice/` (nguồn giọng nói) | Có | 25,5 MB / ~92 MB (02:30) | W-KHO: dữ liệu sinh trắc, không tái tạo được — đúng là phải có trong backup |
| `files/voice/` | Có (lúc backup) | live hiện tại 2,47 GB / 241 tệp | phần local theo `LTT_STORAGE_LOCAL_PREFIXES`; đã vào backup dưới `files_voice/` |
| `files/` ngoài `voice/` | **Không** | — | trên R2 — R2 là nguồn, không thiếu |
| `lttcode_releases.json` (+ `.bak-20260920`) | **Không** | 21.841 B / 15.514 B | sổ đăng ký release LTTCODE — nằm ngoài mẫu backup |
| `nexus_versions.json` | **Không** | 3.026 B | sổ đăng ký phiên bản Nexus — nằm ngoài mẫu backup |
| `api_dist/` | **Không** | 307 MB / 17 tệp | sinh lại bằng deploy — chấp nhận được |
| `lttcode_dist/` | **Không** | 3,378 GB / 22 tệp | sinh lại bằng deploy |
| `nexus_dist/` | **Không** | 388 MB / 14 tệp | sinh lại bằng deploy |
| `codex-home/` | **Không** | 107 MB / 5.530 tệp | state công cụ agent — sinh lại được, mất lịch sử phiên |
| `translations/` | **Không** | 36 KB / 2 tệp | file dịch — cần xem ai sinh (babel?) |
| `session_locks/` | Không | 0 tệp | rỗng — không có gì để mất |

Kết luận: **chỉ có DB + cấu hình + giọng nói là không tái tạo được, và ba thứ
ấy đều nằm trong backup.** Ba tệp sổ đăng ký release (`lttcode_releases.json`,
`nexus_versions.json`) và `translations/` nằm ngoài mẫu `backup.ps1` — mất khi
dựng máy sạch; phần lớn tái tạo bằng deploy nhưng cần chủ dự án xác nhận.

## Rủi ro off-site — chưa đạt

**Toàn bộ bản sao lưu nằm trên chính máy production** (`D:\LTTBackups` +
`D:\LTTBackups-secrets`). Sự cố một ổ đĩa, cháy máy, hay ransomware đánh trúng
`C:\` + `D:\` sẽ mất **cả dữ liệu lẫn bản sao lưu** — khi đó không có gì để
khôi phục. `backup.ps1` đã tính tới điều này (tham số `-BackupDir`/`-SecretsDir`
+ lời cảnh báo "Cat mot ban NGOAI may nay (Q28: off-site)") nhưng đồng bộ
off-site **chưa được thiết lập**. Cần quyết định của chủ dự án.

## Việc cần chủ dự án quyết

1. **Off-site cho `D:\LTTBackups`** — chọn đích (ổ USB định kỳ / NAS / bucket
   R2 riêng) và tần suất. Đây là rủi ro lớn nhất còn lại: backup có thể khôi
   phục, nhưng chỉ nếu nó sống ở nơi khác với dữ liệu gốc.
2. **Vá `restore.ps1`** — thêm bước `alembic upgrade head` (chạy từ
   `C:\LTTPlatform\app`, `LTT_DATABASE_URL` trỏ vào CSDL vừa restore) trước
   `Start-Service`; hiện bước này chỉ tồn tại trong runbook và trong công cụ
   diễn tập.
3. **Ba tệp ngoài mẫu backup** — đưa `lttcode_releases.json`,
   `nexus_versions.json` (và `translations/` nếu không sinh lại được) vào
   mẫu `backup.ps1`, hoặc chấp nhận mất và ghi rõ trong runbook.
4. **Diễn tập định kỳ** — `dien_tap_khoi_phuc.ps1` chạy an toàn bất cứ lúc
   nào (không đụng live). Đề nghị chạy hàng tuần và giữ log, để "có thể khôi
   phục" không phai thành "hy vọng có thể khôi phục".

## Phép kiểm đi kèm

- `tests/test_2200_dien_tap_khoi_phuc.py` — 8 test xanh
  (`py -3 -m pytest tests\test_2200_dien_tap_khoi_phuc.py -q`): script không
  gọi đường live, CSDL tạm đúng hình `lttplatform_dienthu_`, regex đọc URL
  giống `restore.ps1`, có bước `alembic upgrade head` ghim URL vào CSDL tạm.
- `py tools/check_so_test.py` — PASS (19/19 số đã dùng).
- Log đầy đủ: `C:\Users\Public\ltt_dienthu_20260923_full.log` (xanh) và
  `C:\Users\Public\ltt_dienthu_neg_20260923.log` (đỏ).

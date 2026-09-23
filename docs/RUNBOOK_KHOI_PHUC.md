# RUNBOOK KHÔI PHỤC LTTPlatform (23/09/2026)

Khôi phục CSDL LTTPlatform từ bản sao lưu. Dựa trên diễn tập thực ngày
23/09/2026 (công cụ `deploy/windows/dien_tap_khoi_phuc.ps1` + `dien_tap_kiem.py`,
kết quả: `docs/reports/dien-tap-khoi-phuc-2026-09-23.md`).

## 1. Bản sao lưu có gì

Mỗi ngày 02:30, task `LTTStudioBackup` chạy `deploy/windows/backup.ps1` và tạo
**hai zip riêng, không bao giờ chung một file** (H35.9):

| Zip | Nội dung |
|---|---|
| `ltt_data_<stamp>.zip` | `config.json`, `*.enc`, `*.db`, `audit_log.jsonl`, **`lttplatform.dump`** (pg_dump -Fc), `voice_goc/` + `files_voice/` (nguồn giọng nói — dữ liệu sinh trắc, W-KHO) |
| `ltt_secrets_<stamp>.zip` | `app.env` (`LTT_TOKEN_ENCRYPTION_KEY`, `LTT_API_KEY_PEPPER`) |

Vì sao tách: một zip chung bị lấy cắp = đọc được token + tấn công khoá API ngoài
tuyến. **Bản sao lưu CHỨA dữ liệu nhạy cảm — bảo vệ như bảo vệ máy chủ.**

Bản sao lưu **không có** (và cách tái tạo):

- `api_dist/`, `lttcode_dist/`, `nexus_dist/`, `codex-home/` — sinh lại được.
- `files/` ngoài `voice/` — nằm trên R2 (R2 là nguồn; `voice/` là local theo
  `LTT_STORAGE_LOCAL_PREFIXES` và đã được vào zip dưới `files_voice/`).

## 2. Kinh nghiệm quan trọng nhất (bắt buộc đọc trước)

> **Sau khi restore dump, PHẢI chạy `alembic upgrade head` TRƯỚC khi khởi động
> dịch vụ.**
>
> `alembic_version` trong dump có thể **cũ hơn head mà code đang chạy cần** — vì
> migration chỉ được áp dụng khi deploy (bước `alembic upgrade head` trong
> `setup/2-cai-dat.ps1`), còn backup chạy mỗi đêm 02:30. Diễn tập 23/09/2026 đo
> thật: dump 02:30 mang `alembic_version = e4a19c07b5d2`, code đã deploy ở head
> `5e1a9c46b2d7` (3 migration của video-crawler `vc_phien`, `vc_da_tai`,
> `vc_tai_khoan` được deploy trong ngày 23/09, trước giờ backup).
>
> Lệch ấy **không nhất thiết là đỏ** — nó chỉ có nghĩa *nếu cứ restore dump rồi
> khởi động dịch vụ, code sẽ không thấy các bảng/cột mới*. Cách xử lý:
>
> ```powershell
> # Trên máy đã cài đặt, chạy ở TREE ĐÃ DEPLOY (không phải thư mục dev):
> cd C:\LTTPlatform\app
> $env:LTT_DATABASE_URL = 'postgresql+psycopg://ltt_app:<mat_khau>@127.0.0.1:5432/lttplatform'
> C:\LTTPlatform\venv\Scripts\python.exe -m alembic upgrade head
> ```
>
> Lấy `<mat_khau>` từ `C:\LTTPlatform\secrets\app.env` (biến `LTT_DATABASE_URL`).
> `platform_core/db.py::database_url()` chỉ đọc biến môi trường này. Sau upgrade
> kiểm tra: `SELECT version_num FROM alembic_version;` phải bằng head của tree
> đã deploy (`python -m alembic heads` tại `C:\LTTPlatform\app`).
>
> **Cài gì vào CSDL trước — restore hay upgrade — phải ra đúng điểm đó. Không
> bao giờ để CSDL ở điểm nửa vời** (nửa dump nửa schema).

## 3. Khi nào dùng cái gì

| Tình huống | Dùng | Vì sao |
|---|---|---|
| Diễn tập / nghiệm thu bản sao lưu | `dien_tap_khoi_phuc.ps1` | Nạp vào **CSDL tạm** `lttplatform_dienthu_<stamp>`, không đụng live CSDL, không dừng dịch vụ. Xong tự động DROP CSDL tạm. |
| Khôi phục thật (CSDL thật, máy còn sống) | `restore.ps1 -Live` | Dừng dịch vụ `LTTStudioWeb`, tạo bản sao lưu trước, `pg_restore --clean --if-exists` vào CSDL thật, khởi động lại. **`restore.ps1` hiện TẠI CHƯA CÓ bước alembic — sau khi chạy xong, chạy mục 4 (phần 5) TRƯỚC khi xem /health/ready.** |
| Máy mới / thay ổ | Chạy `setup/2-cai-dat.ps1` lên CSDL đã restore (có alembic upgrade bên trong) | Máy mới không có code + venv + service; diễn tập không thay thế cài đặt. |

**Lưu ý: `ltt_app` không có `createdb`** (`rolcreatedb=f`) — CSDL tạm phải được
tạo bởi superuser (mật khẩu trong `C:\LTTPlatform\secrets\postgres-superuser.txt`).
`dien_tap_khoi_phuc.ps1` đã làm thay bước đó.

## 4. Diễn tập (an toàn, chạy được bất cứ lúc nào)

```powershell
# Trên máy chủ. Chọn bản sao lưu mới nhất:
& 'D:\LTTSTUDIOSAPP\deploy\windows\dien_tap_khoi_phuc.ps1' `
  -Archive 'D:\LTTBackups\ltt_data_<stamp>.zip' `
  -SecretsArchive 'D:\LTTBackups-secrets\ltt_secrets_<stamp>.zip'
# XANH -> exit 0. Có bất kỳ phép kiểm nào đỏ -> exit 1 + báo cáo JSON.
```

Các bước (mỗi bước có giới hạn thời gian, không có lặp lại vô hạn):

1. **Kiểm toản zip** — mở được, có `lttplatform.dump`.
2. **Chép + giải nén** vào `%TEMP%\ltt_dienthu_<stamp>` (không ghi vào
   `C:\LTTPlatform`, không ghi vào `D:\LTTBackups` — chỉ đọc).
3. **Tạo CSDL tạm** `lttplatform_dienthu_<stamp> OWNER ltt_app` (superuser).
4. **pg_restore** `--no-owner -1` (một transaction: lỗi thì rollback, không để
   CSDL nửa vời).
5. **`dien_tap_kiem.py`** — đối chiếu: 11 bảng phải có dữ liệu (users,
   credit_entries, jobs, job_events, upload_sessions, api_keys, payment_orders,
   credit_packages, app_access, app_projects, alembic_version), **sạch sổ credit**
   (`so_du = SUM(delta)`, không bút toán mồ côi, không user có số dư âm).
6. **Alembic** — đối chiếu `alembic_version` của dump với head của tree đã deploy
   (`C:\LTTPlatform\app`); lệch thì chạy `alembic upgrade head` lên CSDL tạm
   (`LTT_DATABASE_URL` được ghim vào CSDL tạm trong bước này — con process
   không với tới được live CSDL), rồi đọc lại `alembic_version`.
7. **Kiểm toản zip secrets** — mở được, chỉ liệt kê TÊN entries (không giải
   nén, không in giá trị).
8. **finally** — DROP CSDL tạm + xoá thư mục tạm, luôn luôn chạy.

### Đối chứng âm (chống "xanh giả")

```powershell
# 1. Lấy dump thật ra (chép từ trong zip, KHÔNG ghi vào D:\LTTBackups):
$d = "$env:TEMP\ltt_neg"; New-Item -ItemType Directory -Path $d -Force | Out-Null
Expand-Archive 'D:\LTTBackups\ltt_data_<stamp>.zip' -DestinationPath $d -Force
$dumpThat = Join-Path $d 'lttplatform.dump'
# 2. Cắt 2MB đầu tiên thành dump hỏng (giữ byte, không giải nén):
$fs = [IO.File]::OpenRead($dumpThat)
$cut = New-Object byte[] 2097152
[void]$fs.Read($cut, 0, 2097152); $fs.Close()
$cutPath = Join-Path $d 'lttplatform_CUT.dump'
[IO.File]::WriteAllBytes($cutPath, $cut)
# 3. Chạy diễn tập với -Dam chỉ vào dump cắt:
& 'D:\LTTSTUDIOSAPP\deploy\windows\dien_tap_khoi_phuc.ps1' `
  -Archive 'D:\LTTBackups\ltt_data_<stamp>.zip' `
  -Dam $cutPath
```

Phải cho ra **ĐỎ + exit 1** (diễn tập 23/09/2026: 3 phép đỏ — `pg_restore`
'end of file', `bang_co_dat` 0 bảng, `alembic_khop_head` 0 version, RTO 4,68 s).

> **Bẫy: pg_restore với dump -Fc bị cắt trả về mã 1, KHÔNG phải mã 2.**
> `pg_restore: error: could not read from input file: end of file` bị phân loại
> là "hoàn tất có cảnh báo". Mã xuất đơn thân **không bao giờ** đủ để bắt một
> dump hỏng — đó là lý do bước đối chiếu (5) phải tồn tại, và lý do
> `dien_tap_khoi_phuc.ps1` kiểm cả dòng `pg_restore: error:` trong stderr và
> chữ 'end of file'. Nếu chỉ tin mã xuất, diễn tập sẽ **xanh giả** với một
> dump hỏng.

## 5. Khôi phục thật — thủ công

Chạy trên máy chủ, bằng tay, có chủ ý. Mỗi bước kiểm tra TRƯỚC khi sang bước
tiếp theo.

1. **Đón/giữ thời gian sự cố** — ghi rõ lúc phát hiện, việc gì đang chạy
   (worker, job) để biết mất bao nhiêu.
2. **Dừng dịch vụ** `LTTStudioWeb`.
3. **Tạo bản sao lưu trước** (lưới an toàn: `backup.ps1` chỉ đọc `data\` +
   pg_dump live CSDL).
4. **Restore CSDL** — nếu dùng `restore.ps1 -Live` thì bước này nằm bên trong
   script; nếu làm thủ công: `pg_restore -U ltt_app -h 127.0.0.1 -p 5432 -d
   lttplatform --clean --if-exists --no-owner -1 lttplatform.dump`. YÊU CẦU:
   mã 0 **và** không có dòng `pg_restore: error:` trong stderr (xem bẫy mã 1 ở
   mục 4).
5. **`alembic upgrade head`** — xem mục 2. Bước này **không được bỏ qua**
   (`restore.ps1` hiện tại chưa có bước này — đó là lỗ hổng đã ghi nhận và cần
   vá). Đọc lại `alembic_version`: phải bằng head của `C:\LTTPlatform\app`.
6. **Khôi phục files** (`config.json`, `*.enc`, `content_history.db`,
   `audit_log.jsonl`, `voice_goc/`, `files_voice/`) từ `ltt_data_<stamp>.zip`
   vào `C:\LTTPlatform\data\`. **`secrets\app.env` từ zip secrets RIÊNG — so
   sánh trước khi thay, không bao giờ ghi đè âm thầm.**
7. **Khởi động dịch vụ**, kiểm `http://127.0.0.1:8100/health/ready` = 200.
8. **Kiểm danh**: số user, job mới nhất trong `jobs`, bút toán credit mới nhất
   — phải khớp trạng thái cuối cùng của ngày trước đó.
9. Ghi `docs/NHAT_KY.md`: khôi phục từ stamp nào, thời gian, bước nào phải làm
   tay, có lệch alembic không.

## 6. Khi nào không được làm gì

- **KHÔNG** bao giờ `restore.ps1 -Live` mà không có bản sao lưu trước (bước 3).
- **KHÔNG** bao giờ `pg_restore` vào CSDL thật mà không có `-1` (không rollback).
- **KHÔNG** bao giờ để CSDL ở điểm nửa vời (thiếu bảng, thiếu cột) — rollback
  hoặc làm lại từ đầu.
- **KHÔNG** bao giờ chỉ dùng mã xuất của pg_restore để kết luận (mục 4, bẫy
  mã 1).
- **KHÔNG** bao giờ in giá trị từ `app.env` hay `postgres-superuser.txt` ra
  màn hình, log, hay commit.
- **KHÔNG** bao giờ ghi vào `D:\LTTBackups` (ACL chỉ-đọc là CÓ Ý).

## 7. RTO đo thực (23/09/2026)

Diễn tập XANH với bản sao lưu mới nhất (dump 99.373.232 bytes, 101 bảng):

| Bước | Thời gian |
|---|---|
| Kiểm toản zip | 0,02 s |
| Chép + giải nén | 2,01 s |
| Tạo CSDL tạm | 0,33 s |
| **pg_restore** | **19,08 s** |
| Đối chiếu (11 bảng + sạch sổ) | 2,50 s |
| **alembic upgrade head** (3 migration) | **1,37 s** |
| **Tổng (RTO diễn tập)** | **24,01 s** |

Thực tế khôi phục thật thêm thời gian ngoài: dừng dịch vụ, bản sao lưu trước,
khởi động dịch vụ + /health/ready. Ước tính: RTO khôi phục thật **dưới 15 phút**
khi làm theo thủ công mục 5.

Điểm nghẽn vận hành: bản sao lưu `D:\LTTBackups` **nằm CÙNG máy với dữ liệu
đang chạy** — mất máy = mất cả dữ liệu lẫn bản sao lưu. Xem mục "Rủi ro
off-site" trong `docs/reports/dien-tap-khoi-phuc-2026-09-23.md`.

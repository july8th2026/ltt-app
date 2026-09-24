# Làn no-ky-thuat — nợ nhỏ, độc lập (asv-final)

> Nhánh `phien/asv-final-no-ky-thuat`. Test mới: `test_2130`–`test_2132`.
> Ba khoản: F-08 (BigInteger), F-09 (ghi công CC BY), R-06 (`text=True` thiếu `encoding`).

## F-08 — `upload_sessions.expected_size`/`actual_size`: Integer -> BigInteger

- **Vấn đề đo được**: cột `int4` trên PostgreSQL kẹp ở 2 147 483 647 byte
  (2 GiB−1). Làn `tai-len` đã tự vòng tránh bằng `TRAN_BYTE = min(TRAN_BEN_VUNG,
  2**31-1)` trong `apps/auto_scan_video/tai_len.py` và ghi rõ trong
  `L_TAI_LEN.md` §6.3: *"Sửa gốc (BigInteger + migration) để cho làn nền tảng"*.
- **Sửa**: `platform_core/models.py` (`UploadSession.expected_size`,
  `actual_size` → `BigInteger`) + migration mới
  `alembic/versions/20260923_1000_upload_sessions_bigint.py`
  (`d7bc2f8fbf0f`, revises `e4a19c07b5d2`) dùng `batch_alter_table` — cùng
  khuôn với `b2c8e41d5a90` (đã chạy production) để tương thích cả SQLite (test)
  và PostgreSQL (production).
- Gỡ luôn workaround: `tai_len.TRAN_BYTE` nay bằng đúng `TRAN_BEN_VUNG` (2 GiB
  = 2**31) thay vì `2**31-1` — tệp đúng 2 GiB không còn `DataError`. Cập nhật
  `test_2091::test_tran_dung_2GiB_sau_khi_cot_expected_size_la_biginteger`
  (trước đó test này CHỐT hành vi kẹp cũ; nay chốt hành vi đã sửa).
- **Kiểm chứng**:
  - `test_2130_upload_sessions_bigint.py` (2 test): round-trip 3 GiB qua
    `upload_sessions.create()` và qua ORM trực tiếp — giá trị nguyên vẹn sau
    ghi/đọc lại.
  - `tests/test_63_lop_csdl.py` (17 test, gồm
    `test_vong_di_tru_tien_lui_tien`): toàn bộ chuỗi migration base→head chạy
    sạch trên SQLite với migration mới.
  - `tools/do_migration_tren_postgres.py` chạy trên PostgreSQL THẬT (CSDL
    scratch `lttplatform_wf_migration_test_*`, ba rào an toàn tên/DROP đã có
    sẵn trong công cụ) → **RESULT: PASS**, `alembic upgrade base -> head`
    (bao gồm `d7bc2f8fbf0f`) chạy không lỗi trên Postgres thật.
  - `test_2090`, `test_2092`, `test_173_upload_sessions.py` — không hồi quy
    (42 test cùng chạy).

## F-09 — Ghi công CC BY 4.0 (SQUIM_OBJECTIVE)

- **Nguồn chân lý**: `docs/auto_scan_video_final/THIRD_PARTY_METRICS.md` §1 —
  dòng #5 (`pytorch/audio SQUIM_OBJECTIVE`, weights `squim_objective_dns2020.pth`)
  mang giấy phép weights **CC BY 4.0**, bắt buộc ghi công.
- **Bộ đọc mới** `platform_core/third_party_notices.py`: parse bảng §1 của
  `THIRD_PARTY_METRICS.md` thành `list[dict]` (`doc_bang_muc1`), và lọc các
  dòng có `"CC BY"` ở cột License mã/License weights (`can_ghi_cong`,
  `muc_ghi_cong`) — **đọc thẳng tệp tài liệu ở runtime**, không có bảng chép
  tay thứ hai có thể lệch. `docs/` được `git archive` chép nguyên vào bản
  deploy nên đọc an toàn trên production.
- **Bề mặt sản phẩm**: không có sẵn trang "Giới thiệu/Giấy phép" nào trong kho
  (đã rà `server/templates/`, các trang "điều khoản" hiện có đều đặc thù —
  API terms, VPS terms — hoặc trỏ ra ngoài `lttstudios.com`). Thêm route công
  khai (không cần đăng nhập, cùng khuôn lý do với `/api-dieu-khoan`) mới:
  `GET /ghi-cong-ben-thu-ba` (`server/routes/dashboard.py`) +
  `server/templates/ghi_cong_ben_thu_ba.html`, liên kết từ
  `_platform_footer.html` (nhóm "Liên kết pháp lý").
- **i18n**: thêm 6 chuỗi mới vào `locale/en/LC_MESSAGES/messages.po` +
  biên dịch `.mo` bằng tay (không chạy `tools/i18n.py trich` — lệnh này tạo
  diff 16 000+ dòng không liên quan do lệch phiên bản Babel với bản `.po` đã
  commit; đã thử, đã `git checkout` bỏ). Tiện thể vá luôn MỘT chuỗi `VANG`
  không liên quan đã có sẵn trong cây (`giai_doan_ban_bien_tap.py:190`, không
  phải lỗi của làn này) để `tools/check_dich_thieu.py` từ FAIL về PASS.
- **Kiểm chứng**: `test_2131_ghi_cong_ben_thu_ba.py` (8 test) — bộ đọc (đọc
  đúng SQUIM từ tệp thật, `can_ghi_cong` chỉ bắt CC BY, dữ liệu giả lập đúng
  khuôn, tệp thiếu không sập) + trang (`GET` 200 chưa đăng nhập; MỌI dòng
  `muc_ghi_cong()` xuất hiện trên trang bằng chuỗi định danh thật — không chỉ
  đếm số dòng; dòng KHÔNG cần ghi công không bị nhét vào).
- **Giới hạn xác minh đã biết**: không mở được trình duyệt thật lên trang này
  trong phiên này — công cụ chạy tiến trình nền (`run_in_background`) bị từ
  chối quyền trong ngữ cảnh sandbox của làn con, và `preview_start` chỉ đọc
  `.claude/launch.json` của **cây chính** `D:\LTTSTUDIOSAPP` (không phải
  worktree của làn), nơi brief cấm đụng vào. Đã bù bằng vòng test HTTP đầy đủ
  qua `TestClient(create_app())` thật (ASGI + Jinja thật, không mock) — 200 +
  đối chiếu nội dung render — nhưng đây KHÔNG phải một lượt xác minh trên
  trình duyệt thật theo đúng nghĩa CLAUDE.md. Điều phối/làn sau nên mở
  `/ghi-cong-ben-thu-ba` bằng Playwright trên môi trường có thể chạy dev
  server thật để chốt bằng mắt.

## R-06 — `text=True` không khai `encoding` sập trên đường dẫn tiếng Trung

- **Tái hiện THẬT** (không giả lập): `ffprobe` trên một tên tệp tiếng Trung
  không tồn tại → stderr echo lại đúng tên đó bằng UTF-8. Trên Windows,
  `subprocess.run(text=True)` thiếu `encoding` giải mã bằng
  `locale.getpreferredencoding()` (`cp1252` trên máy tiếng Việt) → luồng đọc
  nội bộ (`_readerthread`) sập `UnicodeDecodeError`, nuốt mất `stderr` (rơi
  vào một thread nền, không nổi lên lời gọi chính — còn tệ hơn ném lỗi rõ
  ràng). Đo bằng tay trước khi sửa, xác nhận `encoding="utf-8"` giải quyết.
- **Sửa tại chỗ trong kho** (không chỉ vòng tránh ở bản scratch của làn
  nghiệm thu): `tests/fixtures/asv_e2e.py:soi()` — thêm `encoding="utf-8"`.
- **Quét thêm** `text=True` thiếu `encoding=` VÀ thiếu `errors=` trong
  `tests/` + `tools/`: phần lớn (git, PowerShell, `icacls`, `setx`, gọi
  `pytest`/`gate.py`...) không đụng đường dẫn tệp media thật nên không sửa
  (tránh làm thừa). Hai chỗ THẬT SỰ cùng dạng bug (ffprobe trên đường dẫn tệp
  thật, có thể mang ký tự ngoài ASCII) đã sửa thêm:
  `tools/chay_thu_ltt_voice.py` (đường dẫn `--tai-ve`) và
  `tools/xuat_mau_toc_do.py` (đường dẫn `--ra-dir`).
  `tests/test_2062`, `test_462`, `test_467` cũng gọi `text=True` không
  `encoding` nhưng ĐÃ có `errors="replace"` (không sập, chỉ có thể ra ký tự
  thay thế) và chỉ chạm tệp tổng hợp tên ASCII (`tmp_path`) — không sửa.
- **Kiểm chứng**: `test_2132_r06_text_true_khong_encoding.py` (2 test) —
  (1) `asv_e2e.soi()` trên đường dẫn tiếng Trung không tồn tại chỉ ném
  `CalledProcessError` thật, không `UnicodeDecodeError`; (2) đối chứng: cùng
  lệnh gọi KHÔNG `encoding` tái hiện đúng bẫy gốc (bỏ qua nếu máy chạy không
  phải locale `cp1252`, để không đỏ sai trên máy/CI khác).

## Không đụng

`apps/auto_scan_video/routes.py`, `dich_vu_tao.py`, `qc_ai.py`,
`giai_doan_qc_ai.py`, `hieu_canh.py`, `server/static/asv/` — đúng như brief.
`apps/auto_scan_video/tai_len.py` và `tests/test_2091_...py` có sửa (không
nằm trong danh sách cấm) vì chúng là caller trực tiếp của workaround F-08.

## Việc còn mở cho điều phối

1. Xác minh trực quan `/ghi-cong-ben-thu-ba` trên trình duyệt thật (xem giới
   hạn ở mục F-09).
2. Cân nhắc hạ mốc `tools/check_dich_thieu.moc` (hiện 319 < mốc 327, còn dư)
   — không tự hạ vì đó là quyết định rộng hơn phạm vi làn này.

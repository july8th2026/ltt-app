# 03 — CHECKPOINT TRUTH

> Nguồn: `apps/upscalevideo/checkpoint.py`, `apps/upscalevideo/jobs.py`,
> `tests/test_4904_upscale_correction.py`. **Resume KHÔNG tồn tại — đọc kỹ
> trước khi tin bất kỳ tài liệu cũ nào nói khác.**

## Sự thật save-only

`checkpoint.py` (sau sửa, đổi tên khái niệm thành "sổ tiến độ") có 5 hàm:

| Hàm | Có caller trong `jobs.py`? | Vai trò |
|---|---|---|
| `save_checkpoint` | **Có** — 4 nơi: `stabilize_completed`, `frame_extraction_completed`, `upscale_batch_NNN` (mỗi batch), `output_uploaded` | Ghi một dòng JSON, không bao giờ ném lỗi |
| `load_checkpoint` | **Không** (khoá bởi `test_jobs_khong_he_goi_duong_doc_checkpoint`, AST-scan) | Chỉ để người/công cụ chẩn đoán soi tay |
| `get_job_checkpoints` | **Không** | Như trên |
| `cleanup_job_checkpoints` | **Có** — trong `finally` của `jobs.handle` (`jobs.py:477`), sau sửa | Xoá sổ khi job xong/lỗi |
| `don_so_cu` | Không gọi từ `jobs.py` (là cron/tool ngoài, chưa nối) | Dọn sổ mồ côi > `TTL_NGAY=7` ngày — hót rác cho đường rò `os._exit` (xem `09_FINAL_ARCHITECTURE.md`) |

## Bằng chứng "0 người đọc" (ISSUE G gốc)

`00_CURRENT_TRUTH.md` ISSUE G ghi: *"Đọc: `load_checkpoint` (`checkpoint.py:55`)
và `get_job_checkpoints` (`:75`) không có caller nào trong cả kho."* Sau sửa,
bất biến này được khoá bằng test AST thay vì lời hứa:
`tests/test_4904_upscale_correction.py::test_jobs_khong_he_goi_duong_doc_checkpoint`
duyệt cây cú pháp `jobs.py`, khẳng định không có lời gọi `.load_checkpoint(` hay
`.get_job_checkpoints(` nào. Đây không phải "chưa ai viết đường đọc" — đây là
**cố ý cấm** viết đường đọc cho tới khi có dấu tay (xem dưới).

## Thứ DUY NHẤT thực sự bỏ qua việc đã làm

`jobs.py:312` `if storage.exists(out_key):` — kiểm đầu ra cuối cùng đã có trên
R2 chưa. Đây là idempotency **cả-job** (thô nhưng thật), hoàn toàn không liên
quan đến `checkpoint.py`. Một job retry với `out_key` đã tồn tại thì bỏ qua
toàn bộ pipeline — nhưng nếu chưa có `out_key`, retry làm lại **100%**: tải lại
nguồn, probe lại, tách khung lại, upscale lại mọi batch, kể cả những batch đã
upscale xong ở lượt chạy trước.

## Rò rỉ và cách nó được vá

Bản cũ khai `cleanup_job_checkpoints` nhưng không caller nào gọi nó ⇒ mỗi job
(xong, lỗi, hay sập) để lại `tmp/upscale/<job_id>/*.json` (vài trăm B–1 KB)
**vĩnh viễn**. Sau sửa: `jobs.py` gọi nó trong `finally` cạnh `shutil.rmtree(tmp)`
(`jobs.py:468-479`), bọc `try/except Exception` (dọn rác không được làm đỏ một
job tốt). ⚠️ Vẫn còn MỘT đường rò: khi worker bị `os._exit(3)` lúc hết giờ cứng
(`platform_core/job_runner.py:641-672`, xem `09_FINAL_ARCHITECTURE.md`), khối
`finally` của Python **không chạy** ⇒ sổ của job đó không được dọn ngay. Đây là
lý do `don_so_cu(ttl_ngay=7)` tồn tại như lưới thứ hai — nhưng nó chưa được nối
vào một cron/scheduler trong đợt sửa này (CHƯA ĐO tần suất cần chạy).

## Resume THẬT cần gì (chưa xây)

Ba thứ, theo thứ tự bắt buộc:

1. **Workspace bền** — hiện `jobs.py` dùng `tempfile.mkdtemp(prefix="ltt_upscale_")`
   bị `shutil.rmtree` ngay trong `finally` (`jobs.py:469`). Một checkpoint trỏ
   vào một thư mục sắp biến mất là vô dụng.
2. **Dấu tay (fingerprint)** cho mỗi chặng: tham số job (preset, target_height,
   codec, stabilize, smooth_motion...) + tên/version model + phiên bản pipeline.
   Không có dấu tay, đọc lại một chặng cũ là **nguy hiểm theo nghĩa giao hàng
   sai**: đổi preset giữa hai lần chạy mà vẫn dùng khung đã upscale ở preset cũ
   là trả cho khách một video không đúng cái họ vừa xin.
3. **`resume_if_partial(job_id)`** — hàm đọc dấu tay, so khớp, và quyết định
   chặng nào được bỏ qua. `docs/UPSCALE_V2/P3_CHECKPOINT_PLAN.md:37-55` từng đặc
   tả đúng tên hàm này — **chưa bao giờ được viết**; chỉ nửa `save_` được xây.

⛔ Đừng thêm đường đọc vào `checkpoint.py` mà chưa có (1) và (2) — đây là luật
ghi thẳng trong docstring đầu tệp sau sửa, không phải một gợi ý.

## Test khoá

`tests/test_4904_upscale_correction.py` mục **E**: `test_jobs_khong_he_goi_duong_doc_checkpoint`,
`test_jobs_co_goi_cleanup_don_rac_checkpoint`, `test_don_so_cu_xoa_dung_thu_muc_qua_han_giu_thu_muc_moi`.

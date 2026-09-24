# P4 Task 9 — FLOW B · E trên PostgreSQL THẬT

## Lượt chạy
`tools/check_multiproc.py::_tim_url()` → `LTT_TEST_DATABASE_URL` (CSDL scratch, ⛔ url/mật khẩu không in ra ở đâu), dưới khoá `postgres_test`.

```
collected 12 items ... 12 passed in 14.04s
```
⚠️ **`exit 0` không phải bằng chứng.** Chạy `-rA` để có **TÊN** từng phép, và `collected 12` khớp `12 PASSED` ⇒ không có skip vô hình (`pytestmark = skip_without_postgres()` sẽ cho 12 `SKIPPED`, không phải 0 dòng).

```
PASSED test_FLOW_B_delay_KHONG_GIU_WORKER_NAO
PASSED test_FLOW_B_KHOI_DONG_LAI_worker_giua_chung_run_VAN_XONG
PASSED test_FLOW_B_delay_TRONG_foreach_moi_vong_mot_diem_cho
PASSED test_FLOW_E_hai_nhanh_deu_di_dung_duong[approve-dang-bo]
PASSED test_FLOW_E_hai_nhanh_deu_di_dung_duong[reject-bo-dang]
PASSED test_FLOW_E_HET_HAN_thi_REJECT
PASSED test_FLOW_E_bo_quet_HET_HAN_danh_thuc_run_khong_co_wakeup
PASSED test_doi_chung_call_workflow_NGOAI_foreach_chot_binh_thuong
PASSED test_call_workflow_TRONG_foreach_moi_vong_duoc_chot
PASSED test_webhook_TRUNG_khong_tao_2_run_chot_o_chi_muc_that
PASSED test_khoa_diem_cho_DAI_khong_lam_PostgreSQL_nem
PASSED test_quet_het_han_dung_SO_SANH_BO_DOI_tren_postgres
```

## Bánh cóc cắn thật — tiêm lỗi TRÊN CHÍNH PostgreSQL
```
# bo `vong` khoi `run_con.ap_ket_qua_mot`
PASSED  test_doi_chung_call_workflow_NGOAI_foreach_chot_binh_thuong
FAILED  test_call_workflow_TRONG_foreach_moi_vong_duoc_chot
1 failed, 1 passed
```
⇒ vế đối chứng **phân biệt được thật**, không phải một phép luôn xanh.

## Vì sao phải là PostgreSQL (không phải "cẩn thận hơn")
`test_1720` đã ghi một ca đo được: `started_at` naive trên SQLite, **aware** trên PG, và `dong_co.ttl` ném `TypeError` ở production mà chưa từng lộ. Phase này thêm **bốn** cột thời gian cùng họ, **một so sánh bộ đôi** (`tuple_(het_han_luc, id)` — row-value, hai dialect thực thi khác nhau), và bề rộng `String(120)` của `waitpoint.idempotency_key` (SQLite nuốt, PG ném).

## Điều kiện ra của P4 — đối chiếu
| Điều kiện (spec §19) | Trạng thái |
|---|---|
| FLOW B | ✅ PG |
| FLOW E (cả hai nhánh + hết hạn ⇒ reject) | ✅ PG |
| không worker nào bị giữ trong lúc chờ | ✅ (đo bằng bảng `jobs` rỗng) |
| khởi động lại worker giữa chừng ⇒ run vẫn xong | ✅ (`mot_vong(db_factory)`, phiên mới mỗi lượt) |
| cron bắn đúng **kể cả lỡ lịch** | ✅ nhưng trên **SQLite** (`test_1795`), chưa trên PG |
| webhook trùng không tạo 2 run | ✅ PG (chỉ mục bộ phận thật + đối chứng `IntegrityError`) |

## Chưa làm được
- Playwright trên Canvas cho FLOW E (spec §18.5: *"A, E thêm Playwright"*) — Canvas chưa có node chờ trong palette hình ảnh; ⛔ chưa nghiệm thu trên `https://app.lttstudios.com`.
- `trigger.cron` chưa có phép trên PG; `test_1795` chạy SQLite.

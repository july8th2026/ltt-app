# Làn `cong-noi-bo` — cổng workflow NỘI BỘ của Auto Scan Video

Mã: `apps/auto_scan_video/cong_noi_bo.py` (cổng) · `apps/auto_scan_video/dich_vu_tao.py` (dịch vụ duyệt dùng chung).
Test: `tests/test_2085`–`test_2088`.

## Không phải public API

Không khoá API, không `/api/v1`, không webhook, không trang tài liệu, không `ToolSpec`.
`server/api/inventory.py` giữ nguyên. Người gọi là mã chạy TRONG nền tảng, đã biết
`owner_id` của người dùng mà nó phục vụ. `test_2088` chốt các điều này.

## Hợp đồng

| Hàm | Vào | Ra | Đi qua (cùng đường với route HTML) | Lỗi |
|---|---|---|---|---|
| `submit_run(db, owner_id, YeuCauChay)` | `cai_dat`: hồ sơ chuẩn (khoá `dich_vu_tao.KHOA_NHAN`, gồm `ngon_ngu_nguon`/`ngon_ngu_dich`) + ĐÚNG MỘT nguồn: `upload_id` (phiên tải lên của chính người dùng) hoặc `nguon_run_id` (dùng lại tệp nguồn của một run cũ của chính người dùng) | `PhieuChay(run_id, trang_thai, credit_giu, cai_dat)` | `dich_vu_tao.dung_cai_dat` → `features.tao_run_tu_ve` (= `routes.tao`) | `LoiDauVao`, `LoiKhongTimThay`, `LoiThieuCredit`, `LoiChuaMo` |
| `get_status(db, owner_id, run_id)` | | `TrangThaiChay(trang_thai, ket_thuc, phan_tram, dang_chay, giai_doan[(ten, trang_thai)], giai_doan_hong, loi, loi_co_ma, co_ket_qua, credit_giu, credit_tinh)` | `quan_sat.dong_thoi_gian` bản khách (= `routes.tien_do`) | `LoiKhongTimThay` |
| `cancel_run(db, owner_id, run_id)` | | `TrangThaiChay` | `features.huy_run` (= `routes.huy`). Luỹ đẳng. | `LoiKhongTimThay` |
| `retry_run(db, owner_id, run_id, giai_doan)` | tên giai đoạn trong `pipeline.THEO_TEN` | `KetQuaThuLai(run_id, da_dat_lai)` | `features.thu_lai_giai_doan` (= `routes.thu_lai`) | `LoiDauVao` (tên sai), `LoiKhongTimThay`, `LoiXungDot` (run đã kết thúc, dispatch mơ hồ) |
| `get_result(db, owner_id, run_id)` | | `KetQuaChay(run_id, khoa_video, media_type)` — khoá kho, mở bằng `get_storage().open` | `features.khoa_ket_qua` (= `routes.tai_ket_qua`) | `LoiKhongTimThay`, `LoiXungDot` (chưa có kết quả) |

Mọi lỗi kế thừa `LoiCongNoiBo`, mang `ma` ổn định: `dau_vao_sai` · `khong_tim_thay` ·
`thieu_credit` · `xung_dot` · `chua_mo`. "Không có" và "không phải của bạn" là CÙNG một
lỗi, cùng một câu (I6).

## Bất biến

- **Một đường.** Toàn bộ phép duyệt từng nằm trong thân `routes.tao` đã hạ xuống
  `dich_vu_tao.dung_cai_dat`; route và cổng gọi cùng hàm. Route nhận chuỗi form (JSON),
  cổng nhận giá trị đã giải — cùng validator, cùng câu lỗi, cùng thứ tự kiểm.
  `test_2086` so hồ sơ run tạo qua HTTP thật với run tạo qua cổng: bằng nhau.
- **Duyệt trước credit.** Cặp ngôn ngữ sai (`vi→vi`, `en→zh`, `ja→vi`, `zh→fr`) bị từ chối
  mà không tạo `AsvRun` hay dòng `CreditEntry` nào (`test_2087`).
- **Phạm vi chủ sở hữu** ở tầng dịch vụ (`features.lay_run`, `upload_sessions.owned`):
  không hàm nào nhận khoá kho từ người gọi.
- **Cổng không biết giai đoạn.** `cong_noi_bo.py` chỉ import tầng dịch vụ (`features`,
  `quan_sat`, `dich_vu_tao`, `pipeline` để kiểm tên, `tables`) — `test_2088` chốt bằng AST.
- **Cờ mở sản phẩm** `LTT_AUTO_SCAN_VIDEO` áp cho cả cổng (`dich_vu_tao.da_mo`): tắt ⇒
  `submit_run` ném `LoiChuaMo`.
- **Giao dịch:** mỗi hàm ghi tự `commit`/`rollback` như route. Đưa cho cổng một session riêng.

## Không làm (quyết định của làn)

- **Logo** không có trong cổng: logo đi kèm ảnh (multipart); route vẫn tự đọc và gắn.
  `cai_dat` có khoá `logo` ⇒ `LoiDauVao`.
- **Chưa khai `BE_MAT_CONG_KHAI`.** `test_308` đòi mỗi cạnh app→app đã khai phải có người
  dùng thật, và hôm nay chưa app nào gọi cổng. Không khai = linter đã CHẶN mọi app khác
  import cổng (fail-closed). Người gọi đầu tiên (vd `apps/agent`) thêm cùng commit:
  `("apps.auto_scan_video.cong_noi_bo", ten)` cho `ten` trong `cong_noi_bo.TEN_CONG`, vào CẢ
  `apps/auto_scan_video/__init__.py:BE_MAT_CONG_KHAI` lẫn
  `tools/lint_app_contract.py:APP_DUOC_DUNG_APP[(<app>, "auto_scan_video")]`.
- **Không adapter node workflow.** `platform_core/workflow` gọi năng lực qua `ToolSpec`
  (một job_type, một lần giữ credit); Auto Scan là chuỗi nhiều giai đoạn giữ credit một lần
  trên `run.id`. Một node sẽ bọc năm hàm trên (submit + chờ `get_status`) khi có nhu cầu thật.
- **Nguồn artifact workflow** (`platform_core.models.Artifact`) chưa nhận: bảng này chưa có
  người ghi trong mã sản phẩm.

## Thay đổi ngoài tệp mới

- `routes.py`: `tao` gọi `dich_vu_tao.dung_cai_dat` (854 → 721 dòng); `CO_MO` đọc từ `dich_vu_tao`.
- Test cũ đọc mã nguồn route được trỏ sang `dich_vu_tao.py`: `test_461`, `test_469`, `test_475`.
- `locale/en/LC_MESSAGES/messages.po`: +6 msgid mới (bản EN). Mốc `check_dich_thieu` chưa hạ
  (`--accept` để điều phối).

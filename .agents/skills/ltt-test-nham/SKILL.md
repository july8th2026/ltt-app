---
name: ltt-test-nham
description: Dùng khi vừa sửa mã trong LTTSTUDIOSAPP và cần chạy test cho đúng cụm đó — tìm thành phần bằng thanh_phan.py, chọn tệp test, giới hạn pytest -n, kiểm tải máy trước lệnh nặng. Trỏ về hợp đồng §4.1, §4.5, §4.8 và docs/QUY_TAC_CHAY_LENH_NANG.md §1.
---

# Test nhắm — LTTSTUDIOSAPP

Nguồn: `docs/00_LTT_OPERATING_CONTRACT.md` §4.1 (test nhắm), §4.5 (bán kính),
§4.7 (test nặng), §4.8 (trước lệnh nặng); kỹ thuật chạy test: `AGENTS.md` §4b.

## Các bước

```powershell
python tools\thanh_phan.py --doi              # cây hiện tại chạm thành phần nào
python tools\thanh_phan.py --test <tp>        # tệp test của thành phần (vd app:<slug>)
python tools\thanh_phan.py --do-thi <tp>      # người tiêu thụ, khi bán kính CAO
python -m pytest tests\test_A.py tests\test_B.py -q
```

- **Nặng hay nhẹ thì hỏi `docs/QUY_TAC_CHAY_LENH_NANG.md` §1** — chỉ nơi đó định
  nghĩa, và nó phân loại theo **khả năng đốt CPU**, không theo số tệp test.
- Là lệnh nặng ⇒ trước đó chạy `python tools\cua_so_yen.py trang-thai` và
  `python tools\tai_may.py` (có người giữ khoá hoặc `QUÁ TẢI` → chờ). Trần `-n` là
  `gate.TRAN_N_GO_TAY` — đọc hằng số, ⛔ đừng gõ lại số.
- Bước kiểm tĩnh lẻ (ruff, mypy, i18n, xuống dòng…): chạy đúng công cụ
  `tools\check_<x>.py`; tên lấy ở `tools/gate.py::_steps`.
- Test nạp model thật nằm sau rào `LTT_TEST_NANG` (`tests/rao_chan_nang.py`);
  `-n` không đếm tiến trình con — §4.7.

## Đỏ thì sao

Sửa tại chỗ → chạy lại **đúng** tệp/phép đã đỏ → đi tiếp (§4.6). Loại trừ máy quá
tải và thay đổi có sẵn trên `main` trước khi kết luận lỗi của mình.

## Không làm

- ⛔ `python -m pytest` cho toàn kho — không chạy test frontend, "full xanh" là câu
  sai (§4.3).
- ⛔ Chạy lại lệnh nặng để "xem đã sửa chưa" — dùng công cụ hẹp nhất
  (`docs/QUY_TAC_CHAY_LENH_NANG.md` §3).
- ⛔ Test một trạng thái trung gian đã biết là dở — gộp changeset nguyên tử (§4.4).

Thêm test mới: ba điều cần nhớ ở `AGENTS.md` §4b; số test do
`tools/check_so_test.py` kiểm.

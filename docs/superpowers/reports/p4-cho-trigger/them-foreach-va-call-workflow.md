# Hai việc THÊM (điều phối giao giữa phase)

## A. `foreach` không còn `O(N²/P)`

**Nguồn số đo:** làn p3b, PostgreSQL thật — `docs/superpowers/reports/p3b-do-tai/report.md`.

| N | P | tổng hàng `foreach_muc` đọc | giây |
|---|---|---|---|
| 10 | 8 | 40 | 0,35 |
| 100 | 8 | 1 500 | 2,67 |
| 1000 | 8 | **127 000** | 31,67 |

`vong_lap._muc_theo_chi_so` tải **toàn bảng** mỗi tick rồi bỏ `xong` bằng Python.

**Đã làm:** `foreach.muc_chua_xong()` (keyset `chi_so > :sau` + `LIMIT`, trả **tuple thuần** — `ghi_ket_qua` gọi `expire_all()` nên một hàng ORM cầm sẵn sẽ nạp lại một câu SQL cho **mỗi** lần đọc thuộc tính), `foreach.ket_qua_theo_chi_so()` (một phép `O(N)` **một lần** ở cuối), `_lai_vong` đọc theo lô `LO_DOC = 16`, `ix_foreach_muc_chua_xong` thành `(vong_id, chi_so)`.

**Phép kiểm chốt HÌNH DẠNG, không chốt con số**, và **đếm HÀNG, không đếm CÂU** — báo cáo p3b đã chỉ ra số câu SQL/tick gần như không đổi theo N (226→409), nên một phép đếm câu sẽ báo "không có vấn đề" và **sai**.

```
# tiem loi: LO_DOC = 100000 (tuc doc ca bang)
1 failed, 3 passed   tests/test_1791_wf_foreach_hang_doc.py
# khoi phuc
4 passed
```

**Chưa làm được:** chưa đo lại `N=1000` trên PostgreSQL thật để có con số mới cạnh 127 000 / 31,67 s. Phép kiểm chỉ chứng minh **hình dạng** trên SQLite.

---

## B. `core.call_workflow` trong thân `foreach` — một LỖ TIỀN

**Đo thật (24/09), có đối chứng:**

| Đồ thị | run | node | số run con | `ket_so_luc` |
|---|---|---|---|---|
| `call_workflow` **trong** `foreach` (2 vòng) | `RUNNING` | `f:0/g` WAITING · `f:1/g` WAITING | 2 | **`NULL`** |
| ĐỐI CHỨNG — **ngoài** `foreach` | `SUCCEEDED` | `g` SUCCEEDED | 1 | có |

Cả hai run con **đã xong**. `ket_so_luc IS NULL` ⇒ **khoản giữ chỗ credit vẫn bị giam** tới `TRAN_RUN` 20 giờ. Không ném, không log.

**Nguyên nhân:** `run_con.ap_ket_qua_con` tra ảnh chụp với `vong=()`; sau P3 task C, ảnh chụp node thân nằm ở `f:0/g`.

**Lỗ thứ hai cùng họ:** `bao_cha` hẹn wakeup theo `duong_thi_hanh(parent_node_id)` với `parent_node_id` là id **trần** ⇒ hai vòng cùng một `node_run_id`.

**Đã sửa:** `ap_ket_qua_mot(db, cha, node, vong=())`; `vong_lap._mot_phan_tu` gọi nó với chỉ số vòng của chính nó; `parent_node_id` nay là đường thi hành; `bao_cha` dùng thẳng chuỗi đó (⛔ không mã hoá lần hai — `duong_thi_hanh("f:0/g")` **ném**).

**Hồi quy của chính làn này, vá cùng lúc:** `cho.la_node_cho` trả `True` cho **mọi** node có `cho` khác rỗng ⇒ nhận vơ `core.call_workflow` (`cho=("run_con",)`) ⇒ `tiep_cho` làm **mọi** run có node đó `FAILED` ngay lượt kế tiếp. Nay quyền sở hữu là tập ĐÓNG `KIND_CUA_TOI`.

Đối chứng + tiêm lỗi cả trên SQLite (`test_1797`) lẫn PostgreSQL (`test_1798`).

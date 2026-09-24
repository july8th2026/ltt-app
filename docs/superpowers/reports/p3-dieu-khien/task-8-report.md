# P3 · Task 8 — FLOW A · C · F trên PostgreSQL thật

## Vì sao phải là PostgreSQL, bằng một ca ĐÃ ĐO

`test_1720` ghi lại: `WorkflowRun.started_at` trả về **naive** trên SQLite nhưng
**aware** trên PostgreSQL thật, và phép so trong `dong_co.ttl` ném `TypeError`
ở production — **chưa từng** lộ trên SQLite. Node điều khiển thêm ba thứ nữa mà
SQLite không phân biệt được:

1. `JSON` lồng trong `output_ref` (mảng `results` của `foreach`);
2. khoá ngoại `credit_entries.user_id → users.id` (PostgreSQL ép, SQLite mặc
   định thì không);
3. bề rộng `String(64)` của `Wakeup.node_run_id` — **SQLite nuốt, PostgreSQL ném
   ở ký tự 65**. Đây là chỗ DUY NHẤT phép băm của Task 1 được đo trên một CSDL
   thật sự cưỡng chế bề rộng.

## Cách chạy — và vì sao nó không thể bị bỏ qua trong im lặng

`tests/test_1787_wf_flow_acf_pg.py` đã được thêm vào `TEP_PG` của
`tools/check_multiproc.py` — công cụ đó biến việc bỏ qua thành **một dòng riêng**
trong gate, thay vì một chữ `s` giữa ba nghìn dấu chấm.

Lượt chạy giữ khoá `postgres_test` suốt phép đo (khoá **tài nguyên độc quyền**:
một phiên chen vào giữa `drop_all`/`create_all` làm **hỏng chính phép đo**).
⛔ Không giữ `cpu_nhieu` kèm — theo đúng tiền lệ `gate.py:869`.

## Kết quả

```
$ python tools/check_multiproc.py          # ca TEP_PG, giu postgres_test
[i] da tao CSDL test lttplatform_multiproc_test_cf8d8bd1
24 passed, 1 xfailed in 347.90s (0:05:47)
[i] da xoa CSDL test cua cay nay
```

⚠️ **Con số 24 KHÔNG phải bằng chứng cho phép này** — nó là tổng của cả `TEP_PG`
(`test_214` + `test_1720` + `test_1787`), và một tổng xanh không nói phép nào
của TÔI đã chạy. Nên chạy riêng, in TÊN từng phép, trên cùng CSDL thật:

```
$ pytest -v tests/test_1787_wf_flow_acf_pg.py     # LTT_TEST_DATABASE_URL = CSDL scratch
test_FLOW_A_set_if_http_hoac_stop[1-True]                     PASSED
test_FLOW_A_set_if_http_hoac_stop[99-False]                   PASSED
test_FLOW_A_nhanh_khong_chay_KHONG_TON_TIEN                   PASSED
test_FLOW_C_foreach_5_ket_qua_DUNG_THU_TU                     PASSED
test_FLOW_C_trang_thai_moi_phan_tu_nam_trong_CSDL             PASSED
test_FLOW_C_tran_chi_phi_cua_than_da_duoc_NHAN                PASSED
test_FLOW_F_output_con_ve_cha_va_version_da_GHIM              PASSED
test_FLOW_F_huy_CHA_huy_luon_CON                              PASSED
test_FLOW_F_chu_trinh_bi_tu_choi_luc_PUBLISH                  PASSED
test_FLOW_F_run_con_KHONG_giu_khoan_thu_hai_tren_PG           PASSED
test_wakeup_node_run_id_khong_bao_gio_vuot_cot_tren_PG        PASSED
============================= 11 passed in 12.74s =============================
```

### 🔴 Một bẫy đo lường đã sập ngay trong task này

Lượt chạy ĐẦU TIÊN trả **exit code 0** và giữ khoá 5,9 phút — nhưng tệp ghi lại
**không có một dòng pytest nào**, chỉ có thông điệp của `cua_so_yen`. Nếu nhận
`exit 0` làm bằng chứng thì tôi đã khai "FLOW A/C/F xanh trên PostgreSQL" mà
**không biết phép nào đã chạy**. Đúng bài học đã ghi trong kho: *"stdout gate
chỉ là đuôi"* và *"chạy lại một phép kiểm đỏ không phải bằng chứng"*.

⇒ Chạy lại với `capture_output` tường minh, rồi chạy lần nữa `-v` để có TÊN.

## Ba flow chứng minh ĐÚNG cái gì

| Flow | Phép kiểm | Chứng minh |
|---|---|---|
| A | `test_FLOW_A_set_if_http_hoac_stop` (2 ca) | `set` → `if` → nhánh đúng chạy, nhánh kia **SKIPPED**; nhánh `false` đi `core.stop` ⇒ run SUCCEEDED ngay, node http chưa từng nộp |
| A | `test_FLOW_A_nhanh_khong_chay_KHONG_TON_TIEN` | nhánh SKIPPED **không để lại một job nào** — một job là một bút toán |
| C | `test_FLOW_C_foreach_5_ket_qua_DUNG_THU_TU` | `results == [50, 30, 90, 10, 70]` — **thứ tự đầu vào**, không phải thứ tự hoàn thành; `aggregate sum = 250` |
| C | `test_FLOW_C_trang_thai_moi_phan_tu_nam_trong_CSDL` | `M7`: 5 hàng `foreach_muc` ghi sẵn từ đầu, chỉ số 0–4, tất cả `xong` |
| C | `test_FLOW_C_tran_chi_phi_cua_than_da_duoc_NHAN` | `he_so_lap = {f:1, x:5, fe:1, ngoai:1}` — node NGOÀI thân là đối chứng |
| F | `test_FLOW_F_output_con_ve_cha_va_version_da_GHIM` | `version_id` ghim = id thật; `nodes.g.output.outputs["ra"]` đọc được ở cha |
| F | `test_FLOW_F_huy_CHA_huy_luon_CON` | huỷ cha ⇒ con CANCELLED (đối chứng: trước lượt huỷ con đang sống) |
| F | `test_FLOW_F_chu_trinh_bi_tu_choi_luc_PUBLISH` | `goi_de_quy` |
| F | `test_FLOW_F_run_con_KHONG_giu_khoan_thu_hai_tren_PG` | sổ credit THẬT: `so_da_giu(con) == 0`, `so_da_giu(cha) == estimated_max` |
| — | `test_wakeup_node_run_id_khong_bao_gio_vuot_cot_tren_PG` | khoá băm của Task 1 vừa cột `String(64)` |

## 🔴 FLOW C CHƯA ĐẠT ĐẦY ĐỦ — khai ra, không làm tròn

Spec §18.5 viết thân FLOW C là **app mock** (node job) và đòi *"trần song song
tôn trọng"*. Bản này:

- thân `foreach` chỉ nhận node **inline**; thân có node job bị **từ chối lúc
  publish** (`than_foreach_co_node_job`). Lý do đo được: `node_run` khoá
  `(run_id, node_id)` nên 30 vòng lặp **không có chỗ** cho 30 trạng thái, và mô
  hình C cấm sửa ảnh chụp. Đường ra là khoá `node_run` theo **đường thi hành**
  (đúng cách Activepieces giải, quyết định `000015`) — một migration trên bảng
  đang chạy thật mà plan P3 không mở.
- `parallelism` được ghi vào `ForeachVong` nhưng thân chạy **tuần tự** ⇒ *"trần
  song song tôn trọng"* **chưa đo được**, vì chưa có cái gì chạy song song.

⇒ FLOW C ở đây chứng minh **thứ tự kết quả** và **trạng thái theo chỉ số**,
  KHÔNG chứng minh **app trong thân** và **trần song song**. Điều kiện ra của
  P3 vì vậy **chưa đóng**; nó cần đúng một việc: khoá `node_run` theo đường thi
  hành.

## Điều kiện ra khác, đã đạt

- FLOW A: đạt (HTTP mock — spec cho phép mock ở phase này).
- FLOW F: đạt cả ba vế (output con về cha · huỷ cha huỷ con · chu trình bị từ
  chối lúc publish).

# P5c / Task 6 — Điều kiện ra: FLOW A với HTTP thật · SSRF 10 dải

## FLOW A với HTTP **thật**

`tests/test_2923_flow_a_http_that_pg.py`, thêm vào `TEP_PG`
(`tools/check_multiproc.py`) — bỏ qua vô hình ở đây đắt hơn cả: nó là phép
**duy nhất** đo đường bí mật đi từ kho credential ra dây.

Khác `test_1787` (FLOW A của P3, **http-mock**, không ra mạng): tệp này chạy
`core.http` thật trong đồ thị, hết vòng động cơ, mở socket tới một máy chủ HTTP
thật (cục bộ, cổng 0), trên **PostgreSQL thật**.

Sáu phép, mỗi phép trả lời một câu:

| Phép | Trả lời |
|---|---|
| nhánh `true` gọi HTTP thật | `h` SUCCEEDED, máy chủ nhận **đúng** `Bearer <bí mật>` |
| nhánh `false` | SKIPPED và **0 request** — phép đếm, không phải lập luận |
| `workflow_version` | bí mật **không** ở đó; đối chứng: **ref** thì có |
| `node_run_snapshot` | bí mật không ở đó (bảng CHỈ THÊM ⇒ lọt là lọt vĩnh viễn) |
| đích **dội lại** bí mật ở `X-Echo` | vẫn bị che (che theo TÊN một mình không bắt được) |
| `credential_nhat_ky` | có đúng một dòng `dung` với `(run_id, node_id)` đúng |

⛔ Bộ gác **không** bị vô hiệu: máy chủ giả ở `127.0.0.1` nên phép kiểm đổi
**chính sách** sang `an_toan_mang.CHINH_SACH_NOI_BO` (đã có sẵn cho việc này).
Bộ gác vẫn chạy và vẫn là một bản duy nhất.

```
XANH  6 passed in 11.90s
      python tools/chay_test_pg.py -q tests/test_2923_flow_a_http_that_pg.py
```

## SSRF 10 dải

**Đã có, không viết bản thứ hai.** `tests/test_2910_an_toan_mang.py`
(P5a/P5b) đã chốt `DAI_BI_CHAN` ≥ 10 dải với một phép tự-kiểm
(`test_du_10_dai_that_su_duoc_do`), **và** ba ca bắt buộc của brief đều có phép
riêng: CGNAT `100.64.0.1` (`is_private` → False), multicast `239.255.255.250` /
`224.0.0.1` / `ff02::1` (`is_global` → True), NAT64 `64:ff9b::7f00:1`
(`is_global` → True). `core.http` dùng **chính** bộ gác đó qua
`http_an_toan.tao_client` ⇒ chép một bảng thứ hai ở đây là tạo bản sẽ trôi.

```
XANH  213 passed, 1 failed in 198.59s   (12 tệp, gồm 2910 + 2911 + 2912)
```

## ⚠️ Một phép ĐỎ, đã đo, **nằm ngoài** thay đổi này

`test_211::test_a_decade_of_retention_leaves_the_ledger_and_the_audit_log_intact`
đỏ dưới `-n 6` (`sqlite3.OperationalError: no such table: asv_asset`). Đo cô
lập: nó đỏ khi chạy **một mình** với `-n 6`, và **xanh** với `-n 0` (23 passed).
Đúng khuôn "gate đỏ vì trạng thái ngoài mã".

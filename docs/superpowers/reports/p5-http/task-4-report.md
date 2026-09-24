# P5/T4 — Điều kiện ra

## 1. SSRF: 10 dải (⚠️ phải gồm CGNAT)

`tests/test_2910_an_toan_mang.py::DAI_BI_CHAN` — **16 dải**, mỗi dải một phép kiểm
tham số hoá, mỗi dải ghi RFC làm nguồn:

| # | Địa chỉ | Dải |
|---|---|---|
| 1 | `127.0.0.1` | loopback RFC 1122 |
| 2 | `10.0.0.1` | RFC 1918 lớp A |
| 3 | `172.16.0.1` | RFC 1918 lớp B |
| 4 | `192.168.1.1` | RFC 1918 lớp C |
| 5 | **`100.64.0.1`** | **CGNAT RFC 6598 — `is_private` trả `False`** |
| 6 | **`100.127.255.254`** | **cuối dải CGNAT RFC 6598** |
| 7 | `169.254.169.254` | link-local RFC 3927 + metadata đám mây |
| 8 | `0.0.0.0` | "this network" RFC 1122 |
| 9 | `192.0.0.1` | IETF protocol assignments RFC 6890 |
| 10 | `198.18.0.1` | benchmarking RFC 2544 |
| 11 | `203.0.113.5` | TEST-NET-3 RFC 5737 |
| 12 | `224.0.0.1` | multicast RFC 5771 |
| 13 | `::1` | loopback IPv6 RFC 4291 |
| 14 | `fd00::1` | unique-local IPv6 RFC 4193 |
| 15 | `fe80::1` | link-local IPv6 RFC 4291 |
| 16 | `::ffff:127.0.0.1` | IPv4-mapped IPv6 RFC 4291 |

Cộng hai dải nữa ở mục "khác biệt cố ý": multicast `239.255.255.250` / `ff02::1`
và NAT64 `64:ff9b::7f00:1`.

⭐ `test_du_10_dai_that_su_duoc_do` khoá chính điều kiện ra: `len(DAI_BI_CHAN) >= 10`
**và** `"100.64.0.1"` có mặt — xoá bớt dải thì phép kiểm đỏ, không im lặng teo lại.

## 2. `core.http` gọi được một máy chủ HTTP giả cục bộ

`tests/test_2912_nut_core_http.py` dựng `ThreadingHTTPServer` trên `127.0.0.1`, cổng
**ephemeral** (⛔ không bao giờ 8100 — đó là production).
`test_doi_chung_may_chu_gia_that_su_tra_loi` khẳng định `trang_thai == 200`,
`than == {"ok": True}` **và** máy chủ ghi nhận đúng đường dẫn — ba mệnh đề, không
phải một.

Chiều ngược lại: `test_chinh_sach_mac_dinh_TU_CHOI_chinh_may_chu_cuc_bo` — chính
sách mặc định chặn **đúng** máy chủ vừa gọi được, và `may_chu.da_nhan` rỗng (không
có byte nào đi ra).

## 3. Tổng kết bằng chứng

| Tác vụ | Đỏ | Xanh | Tiêm lỗi |
|---|---|---|---|
| T1 bộ gác | `ImportError: cannot import name 'an_toan_mang'` | 39 passed | 9 failed → 39 passed |
| T2 client | `ModuleNotFoundError: platform_core.http_an_toan` | 11 passed | A 5 failed · B 5 failed → 11 passed |
| T3 node | `ImportError: cannot import name 'http'` | 23 passed | A 17 · B 1 · C 1 failed → 23 passed |
| webhooks (không được đổi) | — | 52 → **52 passed** | — |

## 4. Ghi chú vận hành

- ⛔ Không chạy `tools/gate.py`. Lượt gộp năm tệp test (≥ 3) đi qua
  `chay_nang.py --phien p5`, xếp hàng sau một phiên khác đang giữ `cpu_nhieu`.
- Đồ thị thành phần đã đúng: `thanh_phan.py --do-thi core:an_toan_mang` →
  *được dùng bởi: `core:api_cong_khai`, `core:wf_soan`* — một thay đổi ở bộ gác kéo
  cả hai nơi tiêu thụ.
- `check_so_test.py` → `PASS` (19/19, không thêm số trùng).

## 5. Chưa làm được / cần quyết định

- **`delivery.py` vẫn còn cửa sổ TOCTOU.** Đường webhook production chưa chuyển sang
  transport ghim IP. Đó là thay đổi trên đường đang chạy — ngoài phạm vi làn này.
- **`core.http` chưa vào `nut_loi/__init__.py`** (chờ p3 gộp) và **chưa nối
  `LoiHttp` → FAILED** ở `cau_noi.py` (tệp bị cấm chạm).
- **Không làm OAuth, không làm kho credential** — theo brief. Hệ quả cần nói rõ:
  header `Authorization` hôm nay nằm **trong `WorkflowVersion`**. Phải có kho
  credential trước khi mở node này cho khách.
- `192.88.99.1` (6to4 relay anycast, RFC 7526 đã bỏ) có `is_global == True` và **vẫn
  đi qua**; langchain cũng không chặn.

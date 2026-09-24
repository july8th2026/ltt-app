# Làn p5b-an-toàn — báo cáo

Nhánh `phien/p5b-an-toan`, cây `D:\LTTSTUDIOSAPP-p5b`. ⛔ Không chạm
`platform_core/models.py`, migration, `platform_core/workflow/` (làn p4 sở hữu).

---

## Việc 1 — vá TOCTOU trong `platform_core/public_api/delivery.py`

**Lỗ.** `send_delivery` phân giải DNS **hai** lần: `webhooks.validate_target(url)` để
KIỂM, rồi `urllib` phân giải lại để NỐI. Giữa hai lần đó DNS đổi được ⇒ socket đi tới
một địa chỉ **chưa hề được kiểm** (DNS rebinding, khuôn TOCTOU).

**Vá.** Dùng lại lối **ghim IP** đã port ở `platform_core/http_an_toan.py` (P5/T2) —
⛔ không viết bộ kiểm thứ hai; vị từ chặn vẫn là `platform_core/an_toan_mang.py`.

- `webhooks.py`: tách `chinh_sach_cho()` + `loi_api()` ⇒ `delivery.py` dùng **chung**
  chính sách và **chung** bảng thông báo, không chép lại tập sơ đồ.
- `delivery.py`: `http_an_toan.tao_client(...)` + `client.stream` (cap
  `MAX_RESPONSE_BYTES` giữ nguyên). Vòng lặp redirect viết tay bỏ đi — `httpx` gọi lại
  transport cho **từng hop**, nên mỗi hop vẫn tự đi qua bộ gác.

**Phép tái hiện.** `tests/test_2913_delivery_ghim_ip.py`. `socket.getaddrinfo` giả ghi
lại "tầng socket đã được đưa cái gì" (bắt được **cả** `urllib` lẫn `httpx`, vì
`socket.create_connection` tra `getaddrinfo` như biến toàn cục của mô-đun `socket`).
Bộ phân giải trả `93.184.216.34` lần một và `127.0.0.1` lần hai.
Assert **không** phải "không nhận được gì" (phép đó xanh cả khi test nối dây sai) mà
là: **mọi** host tầng socket nhận đều phải là một địa chỉ ĐÃ QUA BỘ GÁC.

**Đối chứng** (`test_doi_chung_...`, vô hiệu bộ gác **chỉ trong phép đó**): chứng minh
`send_delivery` thật sự mở kết nối tới máy chủ giả và gửi **đúng byte của
`delivery.py`** — `USER_AGENT`, header chữ ký `v1=`, header sự kiện, thân canonical.
Không có nó, mọi phép an toàn phía dưới có thể xanh vì không đo gì.

```
ĐỎ    ValueError: 'ten-doi-ip.test' does not appear to be an IPv4 or IPv6 address
      1 failed, 2 passed in 2.18s
XANH  3 passed in 3.01s
```

**Trước/sau trên đường production đang chạy** (185 webhooks + 202 console + 2910
an_toan_mang + 2911 http_an_toan):

```
TRƯỚC 102 passed, 1 warning in 56.47s
SAU   105 passed, 1 warning in 60.37s     (+3 phép mới)
Thêm  test_183 + test_191 + test_193: 51 passed in 61.75s
```

**Một phép cũ phải viết lại** — `test_202::test_a_resend_revalidates_the_target_before_sending`
đo **cơ chế**: nó thay `webhooks.validate_target` rồi hỏi "hàm đó có được gọi không".
Hàm ấy không còn trên đường đi, nên phép cũ đỏ **dù tính chất chặt hơn trước**. Viết
lại để đo **tính chất**: DNS trỏ ngược vào trong ⇒ bị từ chối, + đối chứng bộ gác thật
sự được hỏi về đúng đích của lượt gửi.

**Chưa làm được / khác đi:**

- `tests/test_2912_nut_core_http.py` **đỏ lúc collect ngay trên `main`**
  (`LoiNut: 'core.http' khai thi_hanh='inline' nhung khong co ham thi hanh`) — trong
  `platform_core/workflow/`, **làn p4 sở hữu**, tôi không chạm. Vì vậy nó nằm ngoài cả
  phép "trước" lẫn "sau".
- Khác biệt hành vi có chủ ý: lỗi kết nối nay là `httpx.ConnectError/...` thay cho
  `urllib.error.URLError` (`outbox.deliver_due` bắt `Exception` và chỉ ghi
  `type(exc).__name__` nên sổ sách không đổi); redirect 303 nay đổi `POST`→`GET` theo
  đúng RFC 9110, bản cũ POST lại.
- ⛔ **Không** chạy `tools/gate.py` (theo brief). `thanh_phan.py --doi` ra 672 tệp test
  vì `webhooks.py` bị nhiều nơi tiêu thụ — đã chạy cụm webhooks/delivery + 3 tệp
  `public_api` liền kề, **chưa** chạy 672 tệp đó.

---

## Việc 2 — ba chỗ SPEC SAI

Tệp: `docs/superpowers/specs/2026-09-22-ltt-workflow-platform-v2-design.md`.
⛔ Chỉ ba mục, không viết lại spec.

### §10 — CGNAT / `is_global`

Đo **trong lượt này**, CPython 3.13.12, máy A, 24/09/2026:

```
ip_address("100.64.0.1").is_private       -> False   (CGNAT, RFC 6598)
ip_address("100.64.0.1").is_global        -> False
ip_address("239.255.255.250").is_global   -> True    (SSDP/UPnP)
ip_address("224.0.0.1").is_global         -> True
ip_address("ff02::1").is_global           -> True
ip_address("64:ff9b::7f00:1").is_global   -> True    (NAT64 RFC 6052 bọc 127.0.0.1)
ip_address("::ffff:127.0.0.1").is_global  -> False
ip_address("192.0.0.170").is_global       -> False
ip_address("203.0.113.5").is_global       -> False
ip_address("fd00:ec2::254").is_global     -> False
```

⇒ danh sách lớp địa chỉ gõ tay thủng ở CGNAT, **và** `is_global` một mình thủng ở
multicast + NAT64. Mục viết lại cho khớp `an_toan_mang.kiem_dia_chi` hiện tại (hợp
**bốn** vế), sửa tên tệp `mang_an_toan.py` → `an_toan_mang.py`, và khai rõ hai thứ
spec ghi mà **mã chưa có**: giới hạn cổng 80/443/8080/8443, và "chỉ `http`/`https`"
(mặc định `ChinhSach.so_do_cho_phep` là `{"https"}`).

### §11.2 — undici

Tự chạy lại bàn thử `spike/egress/` trong lượt này (Node v24.17.0, `npm install` 28
gói; `node_modules` bị `.gitignore` nên phải cài lại):

```
undici global dispatcher + require('https')  -> {"ok":true,"status":200}   LỌT
undici global dispatcher + axios             -> {"ok":true,"status":200}   LỌT
undici global dispatcher + fetch()           -> EGRESS_BLOCKED
net.Socket.prototype.connect + https/axios/fetch -> EGRESS_BLOCKED (cả ba)
node -r preload-socket-only.js piece-https.js          -> EGRESS_BLOCKED   (CHA)
node -r preload-socket-only.js piece-child-process.js  -> CHILD_REACHED 200 (CON)
```

⇒ spec sửa thành: undici dispatcher **không** chặn `require('http'/'https')` (axios lọt
hoàn toàn), lớp **bắt buộc** là `net.Socket.prototype.connect`, `dns.lookup` chỉ là lớp
phụ — **và** vá trong tiến trình **không phải ranh giới an ninh** (`spawnSync` đi vòng
qua tất cả), Job Object **không lọc socket** nên không lấp được, ranh giới thật phải ở
**mức hệ điều hành** và đó là việc **chưa giải**.
Dẫn lại (⛔ không phải phép đo của lượt này): `activepieces#11547` + CVE-2025-68668 —
nguồn là báo cáo `docs/superpowers/reports/p6-egress/spike-chan-egress.md`.

### §11.6 — tên action

Bảng trình bày tên action **đoán trước** như thể đã tra. Đưa cảnh báo lên **trước**
bảng, đổi đầu cột thành "định đưa lên palette — **tên chưa xác minh**", và viết lại
đoạn dưới bảng thành quy trình chốt bằng `xuat_catalog` ở đầu phase 8 (tra → bỏ action
không tồn tại → ⛔ không tự thay → ghi đè bảng kèm tag đã tra). ⛔ Không bịa danh sách
mới; đoạn YouTube ngay dưới bảng (đã tra thật ở tag 0.90.2) được nêu làm mẫu đối chiếu.

**Chưa làm được** (ngoài ba chỗ được giao, ⛔ không tự sửa):

- Tên `mang_an_toan` còn sai ở **ba** chỗ nữa: §15.2 (dòng "SSRF qua `core.http`"),
  §19 (pha 7), §20 (hàng `core.http`).
- §18.4 còn phép kiểm *"Danh sách dải chặn SSRF Python == bản TS"* — phía Python
  **không có** "danh sách dải chặn" để so, nó dùng vị từ `is_global`. Phép kiểm đó
  không thực hiện được như đang viết.

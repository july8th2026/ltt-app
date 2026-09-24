# P5/T1 — Rút bộ gác SSRF thành một nguồn chân lý

## Nguồn đã tra

- **Bản production**: `platform_core/public_api/webhooks.py:145-164` (trước khi rút) —
  vị từ `not address.is_global or str(address) in METADATA_ADDRESSES`.
- **`langchain_core/_security/_policy.py`**, repo `langchain-ai/langchain`, commit
  `7622d3dce760ac4be6d9aef4c653277e06064aea` — liệt kê 15 mạng IPv4 + 8 mạng IPv6,
  trong đó có `100.64.0.0/10` (RFC 6598) và `224.0.0.0/4`. Lấy về: `_extract_embedded_ipv4`
  (NAT64 RFC 6052 / RFC 8215) và khuôn `SSRFPolicy`. **Không** lấy danh sách mạng —
  `is_global` là một mệnh đề, danh sách là thứ phải bảo trì.
- **Đo thật trên CPython 3.13.12** (không suy):
  `is_private("100.64.0.1") == False` · `is_global("239.255.255.250") == True` ·
  `is_global("224.0.0.1") == True` · `is_global("ff02::1") == True` ·
  `is_global("64:ff9b::7f00:1") == True`.

## Dòng đỏ → dòng xanh

```
ĐỎ   E ImportError: cannot import name 'an_toan_mang' from 'platform_core'
     1 error in 0.48s
XANH 39 passed in 0.33s          (tests/test_2910_an_toan_mang.py)
```

Bánh cóc **cắn thật** — tiêm lỗi: thay vị từ bằng danh sách
`is_private/is_reserved/is_loopback/is_link_local/is_unspecified`:

```
TIÊM 9 failed, 30 passed in 0.46s   (gồm 100.64.0.1, 100.127.255.254 — CGNAT)
GỠ   39 passed in 0.32s
```

## Giữ nguyên hành vi — trước và sau

`tests/test_185_public_api_webhooks.py` + `tests/test_202_webhook_console.py`:

```
TRƯỚC 52 passed, 1 warning in 49.25s
SAU   52 passed, 1 warning in 46.60s
```

## HAI khác biệt CỐ Ý (chặt hơn, không lỏng hơn) — phải khai ra

1. **Multicast.** Docstring `webhooks.py` khai `is_global` phủ multicast. **Sai** —
   đo được `is_global("239.255.255.250") == True` (SSDP/UPnP, bàn đạp SSRF trong LAN)
   và `is_global("ff02::1") == True`. Vị từ mới cộng `address.is_multicast`.
2. **NAT64.** `64:ff9b::7f00:1` bọc `127.0.0.1` có `is_global == True`. Gỡ IPv4 lồng
   trong IPv6 trước khi hỏi (port từ langchain, commit trên).

Cả hai có phép kiểm riêng (`test_KHAC_BIET_1_*`, `test_KHAC_BIET_2_*`) và mỗi phép
đều **tự khẳng định `is_global` trả `True`** trước khi đòi bộ gác chặn — nếu CPython
đổi nghĩa `is_global`, phép kiểm đỏ chứ không xanh giả.

## Một fail-open im lặng do chính phép rút ra tạo ra — đã bịt

`tests/test_202_webhook_console.py:42` thay `webhooks._system_resolver` để cả cụm test
không đi ra DNS thật. Nếu `validate_target` truyền `resolver=None` xuống `an_toan_mang`
thì lần thay đó **vô hiệu trong im lặng** và test_202 vẫn xanh trong khi đang gọi DNS
thật. `validate_target` truyền `resolver or _system_resolver`;
`test_webhooks_system_resolver_van_con_cam_duoc_vao` canh chỗ đó.

## Một ratchet regression của `thanh_phan.py` — đã tránh

`tools/thanh_phan.py::_module_duoc_import` đọc AST và chỉ ghi `node.module`, nên
`from platform_core import an_toan_mang` phân giải về `platform_core/` (không ai sở hữu),
và `--pham-vi core:an_toan_mang` ra **0 tệp test** — tức mọi thay đổi bộ gác SSRF sẽ
chạy 0 phép kiểm. Chuyển sang `import platform_core.an_toan_mang as an_toan_mang` ở
`webhooks.py` và tệp test ⇒ `2 thanh phan, 127 tep test`.

## Chưa làm được

- `METADATA_ADDRESSES` hôm nay **thừa**: đo được cả 2 địa chỉ trong tập đã `is_global
  == False`. Giữ nguyên (T1 là phép rút ra) và đã ghi lý do trong mã.
- `192.88.99.1` (6to4 relay anycast, RFC 7526 đã bỏ) có `is_global == True` và **vẫn
  đi qua**. langchain cũng không chặn. Chưa chặn — cần quyết định riêng.

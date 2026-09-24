# P5/T2 — Port `langchain_core/_security` làm nền cho client HTTP an toàn

## Nguồn đã tra (GitHub MCP `get_file_contents`)

Repo `langchain-ai/langchain`, commit `7622d3dce760ac4be6d9aef4c653277e06064aea`:

| Đường dẫn | Kích thước | Lấy gì |
|---|---|---|
| `libs/core/langchain_core/_security/__init__.py` | 1 046 B | — |
| `libs/core/langchain_core/_security/_exceptions.py` | 268 B | — |
| `libs/core/langchain_core/_security/_policy.py` | 10 973 B | `_extract_embedded_ipv4` (NAT64), khuôn `SSRFPolicy` → **T1** |
| `libs/core/langchain_core/_security/_ssrf_protection.py` | 4 611 B | — (lớp bọc pydantic, không hợp) |
| `libs/core/langchain_core/_security/_transport.py` | 8 392 B | **`SSRFSafeSyncTransport` + `ssrf_safe_client`** → T2 |

Tổng ~25 KB (≈ 350 dòng mã thật) — khớp con số trong brief.

## Dùng lại trước, tự viết sau — vì sao **port** chứ không `pip install`

- `langchain_core` **không** là phụ thuộc của kho này (`python -c "import
  langchain_core"` → `ModuleNotFoundError`), và `_security` là mô-đun **riêng tư**
  (tiền tố `_`): không có cam kết tương thích, kéo cả `langchain-core` + `pydantic`
  vào để lấy một transport là giá quá đắt.
- `httpx>=0.28.1` **đã có** (`requirements-server.txt:18`, bản cài 0.28.1) — đúng thứ
  transport cần.
- Lấy **lối làm**, bỏ **danh sách**: vị từ chặn vẫn là `an_toan_mang` (T1). Danh sách
  15 mạng IPv4 + 8 mạng IPv6 của họ đúng nhưng phải bảo trì bằng tay.

## Thứ đáng lấy: **ghim IP**

`public_api/delivery.py` hôm nay kiểm URL rồi đưa cho urllib gọi ⇒ **hai lần phân giải
DNS** cho một request. Kẻ tấn công điều khiển DNS trả địa chỉ công cộng cho lần kiểm và
`127.0.0.1` cho lần nối (DNS rebinding / TOCTOU). Transport ghim IP phân giải **một
lần**, kiểm **mọi** địa chỉ trả về, nối tới đúng địa chỉ đã kiểm, và giữ `Host` +
`sni_hostname` là tên gốc. `follow_redirects` đặt ở client nên httpx gọi lại transport
cho **từng hop** ⇒ không cần vòng lặp redirect viết tay.

## Dòng đỏ → dòng xanh

```
ĐỎ   E ModuleNotFoundError: No module named 'platform_core.http_an_toan'
     1 error in 0.46s
XANH 11 passed in 5.93s          (tests/test_2911_http_an_toan.py)
```

Bánh cóc **cắn thật** — hai phép tiêm lỗi, mỗi phép nhắm một nửa giá trị:

```
TIÊM A  bỏ vòng `kiem_dia_chi`      -> 5 failed, 6 passed in 48.59s
TIÊM B  bỏ ghim IP (nối thẳng tên)  -> 5 failed, 6 passed in 5.24s
GỠ                                  -> 11 passed in 5.93s
```

Hai tập thất bại **khác nhau** — A đánh sập các phép "địa chỉ bị chặn", B đánh sập các
phép "gọi tới được máy chủ giả". Tức hai tính chất được đo riêng, không phải một phép
kiểm gánh cả hai.

## Đối chứng

`test_doi_chung_may_chu_gia_that_su_tra_loi` chứng minh máy chủ HTTP giả (127.0.0.1,
cổng **ephemeral** — ⛔ không bao giờ 8100) có thật và client thật sự gọi tới. Không có
nó, mọi phép "bị chặn" xanh kể cả khi client không gửi gì.
`test_chinh_sach_mac_dinh_TU_CHOI_chinh_may_chu_cuc_bo` là chiều ngược: chính sách
mặc định chặn đúng máy chủ mà đối chứng vừa gọi được.

## Một lỗi của chính tôi, đã sửa

Phép kiểm redirect ban đầu cho hop hai trỏ `https://10.0.0.7/bi-mat` — nhưng chính sách
`CHINH_SACH_NOI_BO` **cho phép** địa chỉ riêng tư, nên nó chạy thật và treo 21 giây
(`httpx.ConnectTimeout` WinError 10060), chứ không phải "bị chặn". Đổi sang
`169.254.169.254`: bị chặn dưới **cả hai** chính sách, và nhân tiện chứng minh cờ "dev"
không mở đường tới kho thông tin đăng nhập của máy ảo.

## Chưa làm được

- **Chỉ bản đồng bộ.** `SSRFSafeTransport` (async) chưa port — `core.http` chạy trong
  worker đồng bộ. Port sau nếu có nơi gọi async thật.
- **Chưa thay `delivery.py`.** Đường webhook production vẫn dùng urllib + vòng lặp
  redirect tay, tức **vẫn còn cửa sổ TOCTOU**. Chuyển nó sang transport này là một
  thay đổi trên đường production đang chạy — ngoài phạm vi làn p5-http, cần quyết định
  riêng.
- **Giới hạn kích thước phản hồi** chưa đặt ở tầng client; `core.http` (T3) tự cắt.

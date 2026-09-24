# P5c / Task 2 — Credential API key + gán cho node

**Lỗ tìm thấy khi đọc mã thật.** `bien_dich._node_loi` ghi **cứng**
`"credential_ref": ""` cho mọi node `core.*` (dòng 412 bản cũ). Một ô **luôn
rỗng** thì không ai gán được khoá, và hệ quả thật là người soạn phải gõ token
vào `params` — tức vào `workflow_version`, bản ghi được **nhân bản** khi khách
"Save as" và trả nguyên vẹn cho trình soạn thảo.

**Đã làm.**

- `_node_loi` đọc `credential_ref` từ draft. Node **không khai** `credential`
  mà bị gán ref ⇒ `LoiBienDich("credential_khong_ho_tro")`. Một hiểu nhầm im
  lặng về bảo mật (tưởng đã gán khoá, thực ra chưa) là thứ tệ nhất.
- `dinh_nghia._kiem_credential`, gọi trong `xuat_ban_draft`: mọi ref phải qua
  `credential.kiem_ref` với `kieu_cho_phep = NodeDefinition.credential`.
  **Chặn ở PUBLISH**, không phải lúc chạy — phát hiện lúc chạy là một run đã
  tiêu tiền rồi mới FAILED.
- ⛔ Không giải mã gì ở đường publish (spec §9.4).
- **MỘT mã** (`credential_khong_hop_le`) cho cả ba ca (không thấy / đã thu hồi
  / sai kiểu): phân biệt chúng ở bề mặt publish là một máy đếm cho người ngoài
  biết id nào tồn tại — cùng bài với `credential._hang` và `public_api/keys.py`.
  Lý do thật đi vào `chi_tiet`, thứ chỉ chủ workflow đọc.
- Credential `api_key`: tên header do `meta.ten_header` khai (mặc định
  `Authorization`), tiền tố tuỳ chọn. `meta` là ô công khai nên nó chỉ mang
  được những thứ **không** bí mật — giá trị vẫn nằm trong lớp mã hoá.

```
ĐỎ    13 failed, 1 passed in 67.90s
XANH  14 passed in 90.62s      tests/test_2921_credential_gan_node.py
```

**Chưa làm được.** Giao diện gán credential trên Inspector (`frontend/`) —
**làn p9 sở hữu** frontend inspector. Hợp đồng đã sẵn: `credential_ref` nằm ở
mức node, `palette_v3.sang_json` đã trả `credential` của từng node.

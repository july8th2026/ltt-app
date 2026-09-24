# P6 · Task 1 — Runner + **AppContainer làm ranh giới**

**Kết quả: ĐẠT, có đối chứng.** Phép nghiệm thu là chính
`spike/egress/piece-child-process.js` (bản sao logic, chạy **bên trong runner
thật** qua piece giả `thoat_bang_tien_trinh_con`, đã **gỡ sạch biến proxy**
trước khi `spawn` để nó không bị proxy của ta chặn thay).

| Lượt | Kết quả |
|---|---|
| **Ngoài vỏ** (đối chứng) | `CHILD_REACHED 200` |
| Trong vỏ, tên miền | `CHILD_BLOCKED ENOTFOUND` |
| Trong vỏ, **IP trần** | `CHILD_BLOCKED EACCES` |
| Cùng vỏ **+ `internetClient`** (đối chứng) | `REACHED 200` |

## 🔴 Đính chính spike P6B

Spike kết luận *"AppContainer chặn cả `spawn` — `ENOENT`"*. **Sai về cơ chế.**
Đo lại: trong vỏ, `spawn('C:\Windows\System32\cmd.exe')` **chạy được**
(`XIN_CHAO`, status 0). Tính chất thật là **tiến trình con kế thừa token
AppContainer**, nên nó ở lại trong ranh giới mạng. Kết luận an ninh không đổi;
lý do thì đổi, và một ngày nào đó ai đó sẽ dựa vào lý do ấy.

## Hai phát hiện tốn một vòng dò mỗi cái

1. **`LOCALAPPDATA` bắt buộc** trong khối môi trường tuỳ biến, nếu không
   `CreateProcessW` trả `win32=203 ERROR_ENVVAR_NOT_FOUND` — câu lỗi không hề
   nhắc AppContainer. Spike không gặp vì nó kế thừa môi trường worker, tức
   đúng thứ ta **không** được làm (97 biến, có bí mật).
2. Cần **cả hai** cờ `--preserve-symlinks` + `--preserve-symlinks-main`; chỉ
   cờ `-main` thì `require('./piece_nap')` chết `EPERM: lstat` ở gốc ổ đĩa.

## Egress hợp lệ

Vỏ không có capability mạng ⇒ lưu lượng hợp lệ đi qua **proxy CONNECT trên
loopback** (`proxy_egress.py`), nơi danh sách miền được áp **ngoài tiến trình
piece** — đúng hình dạng `activepieces#11547` đề xuất, không cần microVM.
Miễn trừ loopback đo được: chưa miễn trừ ⇒ `ETIMEDOUT`; miễn trừ rồi ⇒ 200; và
**miễn trừ không mở Internet** (cùng lượt, `example.com` vẫn TIMEOUT).

⚠️ **IPv6: CHƯA BIẾT.** Máy A không có IPv6 ⇒ đối chứng cũng hỏng. ⛔ Không có
phép kiểm IPv6, và sự vắng mặt ấy là cố ý.

**Máy sản xuất:** `vps_doi_soat_cong.py` **PASS** trước và sau; **0** luật
tường lửa được thêm (tổng vẫn 561).

**Lệnh gỡ:** `python -c "from platform_core.workflow import connector;
connector.go_vo('ltt-connector-runner')"` (gỡ ACL + miễn trừ loopback + hồ sơ
vỏ).

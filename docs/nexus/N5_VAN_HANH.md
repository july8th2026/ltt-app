# N5 — sẵn sàng vận hành: mở cờ, phát hành, và ứng phó sự cố

> Lập 2026-08-19. File này trả lời đúng một câu: **giữa "code xong" và "khách
> dùng thật" còn phải làm gì, theo thứ tự nào, và hỏng thì tắt bằng cách nào.**
>
> Nó KHÔNG mở cờ giúp ai. Bật `LTT_NEXUS` là một hành động có hậu quả (cho phép
> điều khiển máy từ xa), nên nó là **quyết định của người vận hành**, không phải
> một bước script. File này chỉ liệt kê điều kiện và hệ quả.

---

## 1. Năm điều kiện phải xanh TRƯỚC khi bật `LTT_NEXUS`

Fail-closed của Q93 nghĩa là cờ tắt thì **không có gì chạy** — kể cả migration
bảng Nexus. Nên thứ tự bắt buộc là: chuẩn bị hết, migrate, **rồi mới** bật cờ.

| # | Điều kiện | Kiểm bằng | Trạng thái 2026-08-19 |
|---|---|---|---|
| 1 | **Bảng Nexus đã migrate** trên CSDL thật | `alembic current` chứa `b165aa3584e0` và `d649cfad754f` | ⬜ chưa (cờ tắt, bảng chưa dùng) |
| 2 | **Relay sống** và 5 cổng mở từ ngoài | Q96 / `N1_RELAY_RUNBOOK.md` §7 | ✅ 2026-08-19 |
| 3 | **Khoá phát hành đã sinh + ghim** | `RELEASE_PUBLIC_KEY` khác rỗng trong `nexus_agent/updates.py`, khoá riêng cất ngoài repo | ⬜ việc của người — mục 3 |
| 4 | **Bản agent đầu tiên đã dựng + ký + công bố** | `data/nexus/release_manifest.json` có mặt, trang `/nexus/tai` hiện SHA-256 | ⬜ mục 3 |
| 5 | **Sao lưu phủ bảng Nexus** | `tools/restore_drill_schema.py` có 3 ràng buộc UNIQUE của Nexus (đã có) | ✅ có test |

**Vì sao migrate TRƯỚC rồi mới bật cờ, không ngược lại:** vòng dọn presence gác
sau cờ `LTT_NEXUS` (N2.2) — cờ tắt thì nó không truy vấn bảng. Bật cờ khi bảng
chưa có nghĩa là mỗi lượt bảo trì truy vấn một bảng không tồn tại và làm log
ngập. Migrate xong, xác nhận `alembic current`, rồi mới đặt `LTT_NEXUS=1` trong
`secrets/app.env` và khởi động lại dịch vụ.

**Điều kiện 3 và 4 vẫn còn nợ, và chúng là "việc của người" có chủ ý** — vì khoá
riêng phát hành **không được** nằm trên máy chủ hay trong tay tự động hoá (Q95).
Xem mục 3.

---

## 2. Những gì CHƯA sẵn sàng — và vì sao bật cờ vẫn an toàn dù thiếu

Bật `LTT_NEXUS` mở phần **danh tính + ghép + presence + vé + kiểm toán + trang
tải**. Nó **không** mở luồng điều khiển thật, vì luồng đó chưa tồn tại:

| Hạng mục | Trạng thái | Chặn bởi |
|---|---|---|
| Tích hợp engine RustDesk (N3.2) | ⛔ chưa | **Legal review AGPL** (D1/R1) — `03_OSS_LICENSE.md` §7 |
| Đo tỉ lệ P2P/relay + T10 (N1.1/N1.2) | ⬜ chưa | Cần **hai máy client thật** ở hai mạng |
| Thuê bao tháng theo số máy (D3) | ⬜ chưa | Hạng mục riêng — sổ credit không phủ (Q53) |

Nghĩa là ngay cả khi bật cờ, một khách ghép được máy và **thấy nó online**, nhưng
**chưa bấm điều khiển được** — đúng như manifest khai `lifecycle="development"`.
Đây là trạng thái hợp lệ để chạy thử nội bộ hoặc với nhóm nhỏ, **không** phải để
mở bán. Mở bán cần cả ba dòng trên xanh.

---

## 3. Quy trình phát hành một bản agent (điều kiện 3 + 4)

Làm **một lần** cho khoá, rồi **mỗi lần** cho bản mới.

### 3a. Sinh khoá phát hành — một lần, trên máy KHÔNG phải máy chủ web

```
python tools/nexus_release_key.py --out C:\ltt-keys\nexus_release.key
```

Công cụ **từ chối** ghi khoá vào repo/`secrets`/`data` (Q95). Nó in **khoá công
khai**; dán vào `RELEASE_PUBLIC_KEY` trong `nexus_agent/updates.py`, rồi đóng gói
lại agent. Khoá riêng ở lại `C:\ltt-keys\` — **không** commit, **không** lên máy
chủ. Sao lưu nó ngoài máy (mất khoá riêng = không phát hành được bản cập nhật
nào nữa, vì agent chỉ tin khoá đã ghim).

### 3b. Mỗi bản: dựng → ký → công bố

```
# 1. Dung (mot may Windows sach, co PyInstaller):
python tools/build_agent.py --version 1.0.0
#    -> dist/nexus-agent-1.0.0.zip + in SHA-256

# 2. Ky (may giu khoa rieng, KHONG phai may chu web):
python tools/nexus_sign_release.py ^
    --artifact dist/nexus-agent-1.0.0.zip ^
    --version 1.0.0 ^
    --url https://app.lttstudios.com/nexus/tai/nexus-agent-1.0.0.zip ^
    --key C:\ltt-keys\nexus_release.key ^
    --out release_manifest.json
#    -> tu kiem bang verify_manifest truoc khi ghi

# 3. Cong bo:
#    - upload zip len duong dan cua --url (R2/CDN)
#    - dat release_manifest.json vao data/nexus/ tren may chu
#    - mo /nexus/tai kiem SHA-256 hien dung
```

**Ký tách khỏi dựng có chủ ý:** khoá riêng ở máy khác, nên bước 2 chạy ở nơi
khác bước 1. Gộp hai bước là kéo khoá riêng về máy dựng — đúng thứ Q95 cấm.

---

## 4. Giám sát khi đã chạy

| Nhìn gì | Ở đâu | Bất thường nghĩa là |
|---|---|---|
| Vòng dọn presence có chạy đúng một lần mỗi lượt | lease `platform_core/leases.py` | chạy N lần = lease hỏng (bài học H36) |
| Số thiết bị online vs đã ghép | `/nexus` của khách | tất cả offline đột ngột = agent hoặc relay chết |
| Mã ghép hết hạn không ai dùng, theo thời gian | bảng `nexus_enrollments` | một chuỗi dày = có người đang dò mã |
| Relay còn sống | `Get-Service hbbs,hbbr` trên VPS | không Running = phiên mới không kết nối được |

Cảnh báo ops đi qua đúng đường của Public API (`test_222`), **sau lease** — không
dựng đường cảnh báo thứ hai cho Nexus.

---

## 5. Ứng phó sự cố — tắt cái gì, bằng cách nào

Xếp theo mức độ, nhẹ trước.

**Thu hồi MỘT thiết bị bị chiếm.** Khách bấm "Thu hồi" trên `/nexus`, hoặc admin
thu hồi (để lại dấu chủ-thiết-bị đọc được — Q93 ràng buộc 5). Agent tự dừng và
**xoá khoá** ở nhịp kế tiếp; vé đang có chết ngay vì `doi_ve` kiểm lại thiết bị
(N2.3). Không cần đụng cờ.

**Ngắt TOÀN BỘ ghép mới.** Đặt `LTT_NEXUS=0`, khởi động lại dịch vụ. App biến
khỏi catalog, mọi route `/nexus/*` trả 404. **Lưu ý giới hạn:** cờ này chặn
control plane (ghép, cấp vé), **không** tự tắt phiên điều khiển đang chạy qua
relay — luồng đó không đi qua control plane (Q93 ràng buộc 3). Muốn cắt phiên
đang chạy phải dừng relay (dưới đây).

**Dừng relay — cắt mọi phiên đang truyền.** Trên VPS: `Stop-Service hbbs,hbbr`.
Mọi kết nối đang đi qua relay đứt; kết nối P2P trực tiếp có thể còn sống tới khi
hết vé. Đây là "cầu dao tổng" của data plane.

**Khoá riêng phát hành bị lộ — tình huống tệ nhất.** Ai có khoá riêng ký được
bản cập nhật giả cho **mọi** máy đã cài. Ứng phó, theo thứ tự:
1. Sinh khoá mới (mục 3a), ghim khoá công khai mới, dựng agent mới.
2. **Vấn đề:** agent cũ đã ghim khoá cũ, nên chúng **không tự nhận** được agent
   mới qua đường cập nhật (đúng thiết kế — agent chỉ tin khoá ghim). Phải cài
   lại tay trên từng máy, hoặc chấp nhận máy cũ ở lại bản cũ.
3. Đây là lý do khoá riêng **không bao giờ** ở gần máy chủ: bán kính thiệt hại
   của nó là toàn bộ đội máy, nên nó được giữ như tài sản đắt nhất của hệ thống.

---

## 6. Việc còn nợ của N5

- [ ] Sinh khoá phát hành thật + ghim (mục 3a) — **việc của người**.
- [ ] Dựng + ký bản agent đầu (mục 3b), cần một máy Windows sạch có PyInstaller.
- [ ] Migrate bảng Nexus trên CSDL thật, xác nhận `alembic current`.
- [ ] Chạy thử `upgrade → downgrade → upgrade` cho hai migration Nexus trên bản
      sao CSDL production trước khi migrate thật (R10).

# VPS V2 — BẢNG ĐIỂM PHÁT HÀNH

> Chấm theo `CORE/QUALITY_SCORECARD.md` *(tài liệu `CORE/` chưa từng tồn tại trong kho — kiểm 19/09/2026, xem `docs/_luutru/NGOAI_LE_QUET.md`)*. **Ba cột riêng, không trung bình.**
> Trộn một hạ tầng thiếu vào điểm phần mềm là cách để không ai biết cái nào thiếu.

Ngày: 2026-09-09 · Nhánh `claude/ltt-vps-v2-deployment-plan-2cfc36`

---

## 0. Ba con số

| | Điểm | Vì sao không cao hơn |
|---|---:|---|
| **SOFTWARE / CONTROL PLANE** | **91** ⬇ | Chưa có nghiệm thu live (B-04). Mã, test và nghiệm thu trình duyệt đều đủ; thứ thiếu là **bằng chứng trên hạ tầng thật** |
| **LIVE INFRA / RESILIENCE** | **45** | Một node PVE **chạy lồng**, không cụm, không HA, không đích sao lưu độc lập (B-01, B-02) |
| **END-TO-END PRODUCT** | **62** | Bị kéo xuống bởi Backup/DR (trần cứng 50) và bởi hai cái trên |

⛔ **Không** tuyên bố ≥98 ở bất kỳ cột nào. `START_HERE.md` §12 đòi *"critical E2E
green hoặc ghi rõ environment block và cap score"* — ở đây là vế thứ hai.

---

### ⚠️ Đính chính 09/09/2026, 22:45 — vì sao SOFTWARE 94 → 91

Ba con số ở trên chấm **trước** khi có phép đo trên URL công khai thật. Sau khi
deploy, một lượt `curl https://app.lttstudios.com/vps` tìm ra hai rò rỉ đưa nội
bộ ra cho khách (B-08). Cả hai đều **có sẵn trước** chương trình này; không cái
nào bị `test_557` hay `test_559` bắt, vì cả hai bộ đo **mã và render local**.

⭐ Thứ đáng ghi không phải ba điểm bị trừ. Là: dòng ghi chú *"chưa chốt trên URL
   công khai"* nằm ngay trong bảng, đã viết ra, đã đọc qua — và nó đúng là chỗ
   lỗi nằm. Một hạn chế **đã biết và đã ghi** không tự biến thành một phép đo.

⇒ Điều kiện ở §4 thêm một dòng: **SOFTWARE 91 → 94** cần một lượt quét chuỗi cấm
  chạy trên chính `app.lttstudios.com` sau mỗi lần deploy, không phải trên
  `TestClient`.

---

## 1. Từng hạng mục

| Hạng mục | Điểm | Bằng chứng | Trần đang áp |
|---|---:|---|---|
| Kiến trúc control-plane | 96 | `tac_vu.py` + `thao_tac.py`, ADR-01…06 | thiếu live |
| Mô hình trạng thái | 97 | `test_550` (28 ca), 5 khái niệm tách rời + hình chiếu tương thích | — |
| Động cơ thao tác | 95 | `test_551`+`test_552` (40 ca), fake Proxmox **có trạng thái** | — |
| Vòng đời (bật/tắt/khởi động lại) | 95 | `test_553` (21 ca) + nghiệm thu trình duyệt | thiếu live |
| Ảnh chụp | 94 | `test_554`, chờ → xác minh → mới dọn | thiếu live |
| Khôi phục | 93 | `test_554`, không rollback trước khi quan sát được STOPPED | thiếu live |
| **Sao lưu / DR** | **50** | `test_556` (20 ca) — hợp đồng năng lực đúng, **năng lực thì chưa có** | 🔴 **trần cứng của scorecard** |
| Sức chứa | 90 | giữ nguyên `capacity.py` fail-closed, có test cũ | không sửa trong chương trình này |
| Sổ sách | 93 | `test_555` — thu đúng một lần, `paid_until` đơn điệu | thiếu live |
| Mạng | 88 | ràng buộc duy nhất + `doi_chieu` V2 phân 5 mức | chưa diễn tập router reset thật |
| Bảo mật | **88** ⬇ | `test_557` (19 ca) — TLS fail-closed, cách ly ≠ treo ≠ xoá | 🔴 **hạ từ 94**: câu "bí mật không rò" đo trên **mã**, và URL công khai thật rò ở HAI chỗ (B-08) |
| Quan trắc | 93 | `test_558` (17 ca) — im khi khoẻ, khử trùng lặp, không rò UPID | chưa nối vào kênh báo động thật |
| Đối chiếu | 92 | `test_555` — 5 mức, không tự xoá thứ mơ hồ | thiếu live |
| GUI / sự thật sản phẩm | **90** ⬇ | `test_559` (**21 ca**) + nghiệm thu trình duyệt (§2) | 🔴 **hạ từ 95**: đúng cái ghi chú "chưa chốt trên URL công khai" là nơi lỗi nằm |
| Kỹ nghệ test | 95 | 11 tệp mới, 191 ca; ba phép kiểm cũ **viết lại vì chúng không đo thứ chúng khai** | — |
| Nghiệm thu trình duyệt | 90 | 5 trạng thái render đúng, VI+EN, mobile, 0 lỗi console | ⚠️ **local**, chưa phải `app.lttstudios.com` |
| Hạ tầng live | 45 | `manifest.notes` — Proxmox lồng, một node | 🔴 mã không sửa được |
| Sẵn sàng phát hành | — | `lifecycle` **giữ** `development` | B-03 + B-04 |

---

## 2. Nghiệm thu trình duyệt — đã chạy thật

Máy chủ dev cổng 8133, năm máy gieo sẵn ở năm trạng thái. **Không** phải đọc HTML
tĩnh: điều hướng thật, bấm thật, đọc DOM thật.

| Trạng thái | Trang hiện gì | Nút điều khiển | Khối Nguy hiểm |
|---|---|---:|---|
| bình thường | không có cảnh báo | Restart · Stop · Console · Install Windows | ✅ có |
| **đang khởi động lại** | *"Restarting… Waiting for the machine to stop"* | **chỉ Console** | ❌ ẩn |
| mất liên lạc | *"Could not reach the server — the status below is the last reading, not the current one"* | đủ nút | có |
| quá cũ | *"The status below is the last reading and may be out of date"* | đủ nút | có |
| bị cách ly | *"Machine network-quarantined … data and disk are intact, and you can still reach it through the Console"* + lý do | đủ nút | có |

**Ca quan trọng nhất — bấm thật:** bấm `Restart` trên một máy bình thường ⇒ trang
lật sang *"Restarting…"*, mọi nút điều khiển **và** khối Nguy hiểm biến mất, và
badge **vẫn là "Running"**. Máy chưa hề bị khai là đã tắt.

Đó chính là V-01 + V-02 nhìn từ phía khách: bản cũ sẽ hiện "Đã tắt" ngay lúc bấm,
cho một máy vẫn đang chạy.

Kiểm thêm: **0 lỗi console**, **0 request hỏng** (hai 404 duy nhất là do tôi gõ
sai URL thử `/en/vi/...`), CSS có cache-bust `?v=9b7ae80d`, tiếng Việt và tiếng
Anh đều đúng, mobile 375px **không tràn ngang**.

⚠️ **Chưa chốt trên URL công khai.** `CLAUDE.md` luật 17 đòi `https://app.lttstudios.com`
— chỉ làm được **sau** khi deploy, mà deploy nằm ngoài phạm vi phiên này. Nghiệm
thu ở đây là **local render**, và nó không thay được lượt kiểm qua Cloudflare
(cache, CSP biên, minify).

---

## 3. Cổng chất lượng

Lượt cuối trên cây **đứng yên** (không sửa gì trong lúc chạy) — xem §5 của
`FINAL_AUDIT.md` cho kết quả chính xác và cách phân loại từng lỗi.

Bốn bánh cóc chung được **sửa** chứ không được **miễn trừ**:

| Bánh cóc | Trước | Sau |
|---|---|---|
| `nuot loi lang le` | 64 / mốc 62 | **62 / 62** — thu hẹp ngoại lệ, không thêm log rác |
| `mypy` | 4 mã tăng | **thấp hơn mốc cũ 1** (đã hạ mốc) |
| `dich thieu` | +1 mục | **343 / 343** |
| drill khôi phục + xếp loại lưu trữ | thiếu bảng mới | có `Store(...)` **và** hàm dọn thật |

⛔ **Không dùng `--accept` để né một lỗi nào.** Lần hạ mốc duy nhất là `mypy`, và
nó hạ vì số phát hiện **giảm thật**.

---

## 4. Điều kiện để ba con số ở §0 đổi

| Muốn | Phải làm | Ai làm |
|---|---|---|
| SOFTWARE 94 → ~97 | chạy mạch nghiệm thu live trên VM thử (B-04) | vận hành |
| Backup/DR 50 → >90 | dựng đích sao lưu **độc lập** + job xác minh + một lần diễn tập (B-01) | mua/dựng |
| LIVE INFRA 45 → cao hơn | host thứ hai / cụm / UPS (B-02) | mua/dựng |
| `lifecycle` → `released` | B-03 xong, B-04 xong, gate xanh trên cây đã deploy | cả hai |

⚠️ Ba dòng đầu **không** có phần việc của mã. Viết thêm mã không nhích được con
số nào trong đó, và tin rằng nó nhích được là đúng cái mà `QUALITY_SCORECARD.md`
gọi là *score inflation*.

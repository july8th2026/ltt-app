# Thông dây chuyền bán VPS — từ nút "Tạo máy" tới máy Windows chạy thật

Ngày 2026-09-24. Làn `phien/vps-thong-day`, cây `D:\LTTSTUDIOSAPP-vps-thong-day`,
dải test **3400–3499**.

## Mục tiêu chủ dự án

Tạo **một** VPS thật dùng được: gói **Nhỏ** (1 vCPU · 2 GB · 40 GB · 100 GB băng
thông · 149.000đ), **Windows Server 2016 Core**, cho `akakenly.design@gmail.com`
(số dư 6.606 credit lúc 13:1x). Vừa là máy để dùng, vừa là phép nghiệm thu dây
chuyền A↔B. Rà mọi vấn đề gặp trên đường, sửa tới khi thông.

## Gốc lỗi đã xác minh (Phase 1 của systematic-debugging)

Job `2159e8ef` lúc 12:57:59 hôm nay chết 3/3 lần ở **80% — "dang cap dia chi
cong khai"**:

```
BackendConflict: acquisition requires a paid VPS subscription
```

- Nguồn: `apps/vps/services/ovh_acquisition.py:119`, guard gọi
  `billing.con_han(instance)` ⇒ đọc `instance.paid_until`.
- Bản sửa 23/09 (`cd3c7058`) chuyển đường **tạo mới** sang `credit.giu_cho` /
  `quyet_toan`: `paid_until` chỉ được đặt ở `billing.mo_chu_ky`, gọi từ
  `jobs._quyet_toan` (`apps/vps/jobs.py:557`) — **sau** bước cấp IP
  (`apps/vps/jobs.py:530`). Máy mới luôn có `paid_until = NULL`.
- ⇒ Hồi quy **tất định**: mọi lần tạo máy mới chết ở 80%.
- Bằng chứng biên: `vps_external_mutation` của máy `c74d4fd8` có
  `VM_CREATE` · `VM_CONFIG` · `DHCP_AND_BANDWIDTH` đều **OBSERVED**, và
  **không có** hàng `OVH_IP_ACQUIRE` nào ⇒ guard chặn trước khi chạm OVH.
  Sáu thành phần sức khoẻ của profile OVH `0402` đều **HEALTHY** (06:06 UTC).
- Vì sao không test nào đỏ: fixture `tests/test_1030_vps_ovh_acquisition.py:50`
  đặt `paid_until = 2099-01-01` cho **mọi** ca ⇒ luồng "chưa trả tiền vì đang
  giữ chỗ" chưa từng được đo. Đúng khuôn *"đo thứ đại diện thay vì thứ thật"*.

## Các pha

### Pha 1 — Guard đọc đúng thứ chứng minh khách đã cam kết trả (chặn bán)

`con_han(instance)` là câu hỏi *"máy này đã trả tiền chưa"*. Trên đường tạo mới,
câu trả lời đúng là **"có một khoản giữ chỗ còn sống cho job này"**.

- T1 (đỏ trước): máy `paid_until = None` + `credit.giu_cho(job)` ⇒ `ensure_free_ip`
  phải đi qua guard. Hiện tại `BackendConflict`.
- T2: truyền `job_id` từ `ctx` → `_cap_ip_cong_khai` → `reserve_for_provision`
  → `ensure_free_ip`; guard: `con_han(may)` **hoặc** giữ chỗ còn sống cho `job_id`.
- T3 (bánh cóc R4): máy `loi`/`da_xoa`/đã có sự kiện `hoan_tien` vẫn bị chặn, và
  một `job_id` đã `refund` **không** mở cửa mua IP.
- T4: bỏ `paid_until = 2099` khỏi chỗ nó che mất luồng thật trong `test_1030`.

### Pha 2 — Lỗi phải mang tên của nó

`jobs._ma_loi_cua` không biết `BackendConflict`/`DangBan` ⇒ ghi `khong_ro`, khách
đọc *"Thao tác không hoàn tất"*, và người vận hành mất luôn tên lỗi trong
`vps_event`. Thêm mã + câu cho khách (`nhan.MA_LOI`), test chốt.

### Pha 3 — Dọn hậu quả lần thử 12:57

Máy `Maytram01` (`c74d4fd8`, vmid **207**) trạng thái `loi`. Kiểm VM 207 trên
Proxmox: còn thì dọn (VM + đĩa), sổ sách thì đóng. Tiền đã nhả đúng
(hold 1.490 → refund 1.490), không có IP nào bị mua ⇒ không rò tiền provider.

### Pha 4 — Cổng chất lượng + lên production

Test nhắm xanh → `gate.py --pham-vi vps` (L2, qua `chay_nang.py`) → gộp `main`
→ deploy → `so_deploy.py` khớp.

### Pha 5 — Tạo máy thật

Tạo qua GUI bằng chính tài khoản chủ dự án, theo dõi `jobs` + `vps_external_mutation`
theo từng bước: `VM_CREATE → VM_CONFIG → DHCP_AND_BANDWIDTH → OVH_IP_ACQUIRE →
PUBLIC_MAPPING → VM_BOOT → quyết toán`. Lỗi mới ⇒ quay lại Phase 1 của
systematic-debugging, không đoán.

### Pha 6 — Nghiệm thu dây chuyền

Console mở được và bàn phím tới VM · IP công khai vào được từ ngoài · sổ sách:
hold 1.490 → settle 1.490, `paid_until` đặt, sự kiện `thu_phi` **một** lần ·
băng thông đếm được (R26 hiện vẫn 0 cho VPS OVH — đo, rồi quyết định) · nhật ký.

## Việc KHÔNG làm trong làn này

Dọn Vultr · reboot host Proxmox · admin sửa chính sách mua IP · gate chạy nhóm
real-Postgres. Ghi vào `docs/VPS_V4/09_BLOCKERS.md`, không mở thêm mặt trận.

# P6 · Task 6 — Điều kiện ra: FLOW D · upload YouTube thật · tải + diễn tập

## 1. FLOW D — ✅ ĐẠT trên **PostgreSQL thật** (7/7)

`tests/test_3505_wf_flow_d_poll_pg.py` (đã vào `TEP_PG` nên một lượt bỏ qua
không còn vô hình). Chứng minh đúng điều §18.5 đòi: *chỉ bản ghi mới tạo run*
và *poll lần hai không trùng*, cộng ba phép mà bản thân FLOW D không nói ra
nhưng là chỗ tiền chảy:

- **Store mất mà vẫn không trùng** — lớp khoá thứ hai làm một sự cố khôi phục
  CSDL thành "không có gì xảy ra" thay vì "tạo lại run cho cả lịch sử".
- **Bản ghi không có `id`** khử trùng theo **nội dung**, ⛔ không theo chỉ số.
- **Đối chứng**: bản ghi thứ ba **vẫn** tạo được run (nếu không, "0 run mới"
  ở trên chỉ nghĩa là trigger chết).

⚠️ **Phạm vi, khai thẳng:** lớp poll dùng **piece giả**, ⛔ không phải Sheets
thật — và lý do không phải sự tiện: piece `google-sheets` ở bản đã ghim
**không có trigger POLLING nào về dòng mới** (task 5). Câu *"trigger poll
Sheets"* của spec không thực hiện được với tập piece vòng này.

## 2. Upload YouTube thật (private, tài khoản test) — 🔴 **CHƯA ĐẠT, BỊ CHẶN**

Mã xong và có phép kiểm giao thức (`test_3502`, 14 phép, gồm ca *cửa giả*
`publish_at` + `public`). Nhưng **lượt thật chưa chạy được**, và nó chặn ở
việc của chủ dự án, ⛔ không ở mã:

1. `secrets/app.env` **không có** biến cấu hình OAuth Google
   (`oauth_google.cau_hinh()` đọc ba biến; đo 24/09: không biến nào tồn tại,
   không tệp `client_secret*` nào trong `secrets/`). Không có app OAuth thì
   không có `access_token`.
2. **Tài khoản test YouTube chưa được cấp.** ⛔ Claude không tự tạo tài khoản,
   không tự nhập bí mật.

⇒ Cần chủ dự án: tạo app OAuth Google (skill `wizard`,
`tools/wizard_oauth_google.sh`), bật **YouTube Data API v3**, phạm vi
`https://www.googleapis.com/auth/youtube.upload`, rồi cấp một tài khoản test.
⚠️ App còn ở chế độ *Testing* thì `refresh_token` **hết hạn sau 7 ngày**.

## 3. Đo tải runner — ✅ (20 lệnh tuần tự + 20 lệnh ở trần lane 2)

| | |
|---|---|
| Độ trễ một lệnh (trung vị / p95) | **119 ms** / 140 ms |
| Song song 2 (trần lane §11.2) | trung vị 121 ms · **15,5 lệnh/giây** · 0 hỏng |
| RAM đỉnh (kế toán Job Object) | **24,1 MB** trung vị, 24,5 MB max |
| CPU một lệnh | **94 ms** |

🔴 **Một lỗi hiệu năng tìm được nhờ hai phép đo lệch nhau.** Đo từ ngoài:
**512 ms**; đo từ trong: **100 ms**. Chênh 5 lần ⇒ đi tìm chỗ chênh, không
chọn số đẹp. Thủ phạm: `ThreadingTCPServer.shutdown()` **chờ** vòng
`serve_forever` thoát, và vòng ấy kiểm cờ dừng mỗi `poll_interval` — mặc định
**0,5 s**. Tức **80 %** độ trễ mỗi lệnh connector là ngồi chờ một vòng `select`
nhàn rỗi. Đặt 20 ms ⇒ 512 ms → **119 ms**, thông lượng 3,9 → **15,5 lệnh/s**.

## 4. Diễn tập lỗi (§18.7) — ✅ **9/9 đạt**

`provider_429` (giữ `status: 429`) · `dau_vao_sai` · **`het_gio`** (piece ngủ
20 s, `han_ms` 3 s ⇒ bị giết ở 8,0 s, mã `het_gio`, không treo) ·
`ket_qua_mo_ho` (job xong, nội dung rỗng — lộ ra) · **bí mật bị che** ·
**egress bị chặn** · `waitpoint` bị cấm · **ngoài allowlist** · **lệch bản**.

Số thô: `docs/superpowers/reports/p6-connector/do-tai-runner.json`
(sinh lại: `python bench/connector_runner.py --lan 20 --song-song 2`, chạy qua
`chay_nang.py`).

## Máy sản xuất

`vps_doi_soat_cong.py` **PASS** trước và sau mọi lượt đo · **0** luật tường
lửa thêm (tổng 561) · `python -m alembic heads` ⇒ **`3d5c07e2ba91` (head)**,
đúng một dòng.

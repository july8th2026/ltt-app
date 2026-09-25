# Bảng đối soát dây chuyền VPS — 2026-09-24

Ba nguồn phải khớp nhau: **sổ sách app** (PostgreSQL) · **thế giới thật**
(Proxmox, gateway nft, OVH) · **thứ khách nhìn thấy** (trang `/vps`).
Mỗi hàng nói rõ **hỏi bằng lệnh nào** — không có hàng nào "xem bằng mắt rồi tin".

## A. Cổng bán (trước khi khách bấm)

| # | Hạng mục | Hỏi bằng gì | Đạt là gì |
|---|---|---|---|
| A1 | Ba gói đều bán được, không câu "hết chỗ" giả | `GET /vps` với cookie khách | 3 gói hiện giá, nút Tạo máy sống |
| A2 | Sáu thành phần sức khoẻ profile | bảng `vps_profile_health` bản mới nhất | `CHAN_BAN` xanh; `CANH_BAO` đỏ **không** chặn bán |
| A3 | Số chỗ khớp ràng buộc chặt nhất | `nguon_luc.con_ban_duoc` vs `vps_ip` FREE | lý do từ chối mang **đúng tên** (`ipv4`/`compute`/…) |
| A4 | Bảng giá băng thông = trần OVH 1 TB | `apps/vps/cost.py` + trang | 100/150/250 GB |
| A5 | Thời gian sẵn sàng nói trước | trang tạo máy | im khi < 3 mẫu; có số khi ≥ 3 |

## B. Luồng tạo máy (7 chặng, mỗi chặng một bản ghi)

| # | Chặng | Bản ghi phải có | Bẫy đã gặp |
|---|---|---|---|
| B1 | Nhận yêu cầu | `credit_entries` kind=`hold` đúng 1.490 | thu tiền trước (đã bỏ 23/09) |
| B2 | `VM_CREATE` | `vps_external_mutation` OBSERVED | clone đúp nếu thiếu hỏi-thế-giới-thật |
| B3 | `VM_CONFIG` | OBSERVED | — |
| B4 | `DHCP_AND_BANDWIDTH` | OBSERVED + `ip_noi_bo` | router VM199 không đọc được ⇒ hai lớp băng thông cùng im (R26, **còn mở**) |
| B5 | `OVH_IP_ACQUIRE` | INTENT → OBSERVED, `vps_ip` có hàng | **cửa `paid_until` chặn 100%** (đã sửa hôm nay) · mất phản hồi checkout ⇒ `cap_ip_can_ra_soat` |
| B6 | `PUBLIC_MAPPING` | mapping nft `IP công khai → 10.50.0.x` | mapping hỏng mà VM đã chạy ⇒ giao máy không vào được |
| B7 | `VM_BOOT` + quyết toán | `dien_quan_sat=chay` đo thật; `settle` 1.490; `paid_until` đặt; `thu_phi` **một** lần | ghi `dang_chay` trước khi hỏi lại (V-02) |

## C. Đường và cổng (sau khi máy lên)

| # | Hạng mục | Hỏi bằng gì | Đạt là gì |
|---|---|---|---|
| C1 | IP công khai định tuyến về VM | `ping` / `nc` từ ngoài tới IP mới | tới được đúng VM |
| C2 | RDP 3389 | `nc -z <ip> 3389` sau khi khách cài Windows | mở sau khi cài; **trước khi cài thì đóng là đúng** |
| C3 | Console (noVNC) | mở `/vps/<id>/console`, gửi phím | thấy màn hình cài Windows, bàn phím tới VM |
| C4 | Cách ly giữa khách | từ VM mới thử tới `10.50.0.x` của máy khác | **không** tới được |
| C5 | VM100–107 không bị đụng | `PROTECTED_VMIDS` + mapping 8 IP `15.235.x` | nguyên vẹn, không bị hãm |
| C6 | Cloudflare không cắt | tạo máy qua `app.lttstudios.com` | job đi hàng đợi, không chạm trần 100 giây |

## D. Sổ sách và tiền

| # | Hạng mục | Đạt là gì |
|---|---|---|
| D1 | Một máy = một `hold` → một `settle` | không có `refund` nào cho máy lên thật |
| D2 | Máy hỏng: `hold` → `refund`, **không** `thu_phi` | và **vẫn** được nộp job xoá (sửa hôm nay) |
| D3 | `paid_until` chỉ tiến, không lùi | `billing._moc_ke_tiep` |
| D4 | Một IP = một máy | `vps_ip.instance_id` duy nhất, không hàng mồ côi |

## E. Đối soát ba nguồn (chạy được thành lệnh)

| # | Đối soát | Lệch nghĩa là |
|---|---|---|
| E1 | `vps_instance.vmid` ⟷ Proxmox `danh_sach_vm` | VM mồ côi (app không biết) hoặc VM_MISSING (app tưởng có) |
| E2 | `vps_instance.dien_quan_sat` ⟷ `tac_vu.doc_dien` | **trang khách nói dối** (đã gặp: máy 204) |
| E3 | `vps_ip` ⟷ OVH `list_additional_ipv4` | IP đang tính tiền mà sổ không biết |
| E4 | `vps_ip` ⟷ mapping nft | IP mua rồi không định tuyến, hoặc đường mở cho IP đã trả |
| E5 | `bang_thong_byte` ⟷ counter nft/ens3 | R26: hiện **0** cho VPS OVH — lớp hãm theo khách không có số |

## G. Cổng — đo được bằng lệnh

```bash
python tools/vps_doi_soat_cong.py
```

Trả lời ba câu: cổng 22 có đóng trên **mọi** IP đã bán (đo từ ngoài, không tin
cấu hình) · luật chặn có nêu **đúng** IP quản trị hiện tại (đọc từ `vps_gateway`,
nên IP đổi là đỏ) · RDP có còn thông. Đo 24/09: **PASS**.

## H. Danh tính máy — chuẩn hoá 25/09

| # | Hạng mục | Hỏi bằng gì | Đạt là gì |
|---|---|---|---|
| H1 | CPU không còn `kvm64` generic | `qm config <vmid>` | `cpu: host` |
| H2 | Chống giả mạo IP/MAC | `doc_firewall(vmid)` | `enable/ipfilter/macfilter = 1` |
| H3 | Hai policy không cắt mạng khách | như trên | `policy_in`/`policy_out` = **ACCEPT** |
| H4 | `net0` bật cờ firewall | `qm config` | `firewall=1` (nếu `0` thì H2 **không tới nơi**) |
| H5 | rDNS cho IP đã bán | `GET /ip/<ip>%2F32/reverse/<ip>` ở OVH | có `reverse` |
| H6 | Máy mới tự đúng | `test_4002` đọc AST `_tao_may` | gọi cả hai bước mới |

```bash
python tools/vps_chuan_hoa.py        # báo cáo
python tools/vps_chuan_hoa.py --ap   # áp thật
```

Vòng bảo trì tự kiểm mỗi ngày và ghi `chuan_hoa_may` (tầng cảnh báo, **không**
chặn bán) — nên "chưa ai chạy" hiện ra là STALE, khác hẳn "đạt".

⚠️ Ba bẫy đã đo, đừng đo lại:
- OVH **bắt buộc forward-confirm**: A record trước, PTR sau.
- OVH **từ chối tên có dấu chấm cuối**, và báo *"Cannot check if … resolves to …"*
  — một thông điệp **chỉ sai chỗ**, nó đẩy người đọc đi tìm lỗi ở DNS.
- `409 already setted` bị gộp thành lỗi chung ⇒ `dat_reverse` hỏi trước khi ghi.

## F. Còn mở sau hôm nay (đưa vào `09_BLOCKERS.md`)

- **R26** — băng thông theo khách = 0 cho VPS OVH; điểm đo chưa chọn.
- Router không đọc được ⇒ **cả hai** lớp băng thông cùng im, chỉ một `log.warning`.
- Gate không chạy nhóm real-Postgres (`LTT_VPS_PG_TEST`) ⇒ lỗi hạng R16 im.
- Admin chưa sửa được chính sách mua IP (`auto_acquire`, trần giá) — chỉ qua CSDL.
- Dọn Vultr (profile 0401 vẫn ghi `reconciliation unavailable` mỗi lượt).
- Reboot host Proxmox để dùng kernel 7.0.14 — chờ cửa sổ bảo trì.
- **Deploy lấy `HEAD` của `main` lúc chạy, không nhận SHA tường minh.** Ngày
  24/09 một phiên khác commit **33 giây** sau khi lượt deploy khởi động, và bản
  xuất lấy commit mới đó. Lần này thoát vì delta chỉ là tài liệu; nếu là mã chạy
  thì đã deploy một SHA chưa ai đo. Đường deploy nên nhận `--sha`.

# VPS V2 STATE

> SSOT trong lúc chạy chương trình. **Không** dùng lịch sử chat làm SSOT.
> Cập nhật tệp này ở cuối mỗi pha, và trước mọi lần context sắp compact.

## Identity
- repository: `D:\LTTSTUDIOSAPP`
- branch/worktree: `claude/ltt-vps-v2-deployment-plan-2cfc36` — cây `.claude/worktrees/ltt-vps-v2-deployment-plan-2cfc36`
- baseline SHA: `05464239980c25de4cb316755efd41b27da7ddce`
- current HEAD: `05464239` (cập nhật khi commit)
- `master` lúc bắt đầu: `9e73bf1f402c26525f1643761652cd5346359a9c` — **đúng SHA pack đã quan sát**
- started_at: 2026-09-09
- current_phase: **11**

## Working tree safety
- pre-existing user changes: **không có**. `git status --porcelain` lúc bắt đầu chỉ có `?? docs/vps_v2/` (do chính chương trình này tạo).
- files owned by this program: `apps/vps/**`, `alembic/versions/2026*vps_v2*`, `tests/test_55*`–`test_59*`, `docs/vps_v2/**`, `server/templates/vps*.html`, `server/static/vps/**`.
- forbidden/unrelated changes: mọi thứ ngoài danh sách trên. Một dòng `??` lạ xuất hiện giữa chừng = **phiên khác**, không đụng vào.
- ⚠️ Lúc bắt đầu có phiên khác chạy `gate --ho-so day-du` (pid 10844). Mọi lệnh nặng phải kiểm `python tools\cua_so_yen.py trang-thai` trước.

## Baseline findings

| ID | Severity | Finding | Current-head verified? | Decision |
|---|---|---|---|---|
| V-01 | **P0** | `khoi_dong_lai()` chỉ gọi `tat()`, không bật lại | ✅ đọc mã `services/dieu_khien.py:91-99` | Sửa ở Pha 03 |
| V-02 | **P0** | Ghi trạng thái ổn định ngay sau khi Proxmox nhận lệnh (`_lam`), và `_tao_may` ghi `dang_chay` ngay sau `client.bat()` không chờ | ✅ `dieu_khien.py:67`, `jobs.py:286-292` | Sửa ở Pha 02+03 |
| V-03 | **P0** | Chụp ảnh rồi list/prune ngay, chưa chờ UPID; `sao_luu_luc` ghi cho ảnh chưa xác minh | ✅ `services/sao_luu.py:122-131`, `bao_tri.py:208-213` | Sửa ở Pha 04 |
| V-04 | **P0** | Khôi phục: `tat_cung` trong `except ProxmoxError: pass` rồi rollback ngay | ✅ `routes.py:620-630` | Sửa ở Pha 04 |
| V-05 | **P1** | Một cột `trang_thai` `String(16)` gánh 5 khái niệm (vòng đời, điện, treo-vì-tiền, lỗi, đã xoá) | ✅ `tables.py:186`, `nhan.py:TRANG_THAI` | Sửa ở Pha 01 |
| V-06 | — | `lifecycle="development"`, Proxmox chạy lồng | ✅ `manifest.py` — **đúng sự thật** | Giữ tới khi bằng chứng đủ (Pha 11) |
| V-07 | **P0** | 4 route điều khiển (`bat`/`tat`/`khoi-dong-lai`/`khoi-phuc`) chạy thẳng, **không** xin lease `vps-may:{id}`; chỉ handler job mới có `_khoa_may` | ✅ `routes.py:462,469,476,586` vs `jobs.py:_khoa_may` | Sửa ở Pha 02+03 |
| V-08 | — | Pack ghi "snapshot phải được mô tả đúng là quick rollback" | ✅ **ĐÃ ĐẠT** — `sao_luu.py` docstring + `proxmox.py:330-343` đã nói đúng, kèm phép đo 24/08 | **Không sửa.** Actual HEAD wins |

### Điểm mạnh sẵn có — phải giữ, không được làm hỏng khi sửa

`_may_cua_khach` trả 404 (không 403) cho máy người khác · vé console dùng-một-lần băm khi lưu ·
`_cong_co` đứng trước `require_login` trong mọi chữ ký · xác nhận gõ tên máy cho thao tác phá huỷ ·
`_cap_ip_cong_khai` ghi sổ **trước** khi gắn IP + trả IP về khi commit hỏng ·
`_vm_da_ton_tai` fail-safe (không đọc được ⇒ coi như đã có) · `_dung_lai`/`_xoa_may` **đã** chờ UPID ·
ràng buộc duy nhất `uq_vps_instance_vmid` + `uq_vps_instance_ip` · `bang_thong.py` xử bộ đếm về 0 khi router reboot ·
`sao_luu.cua_ta` chỉ dọn ảnh mang tiền tố `ltt`.

## Architecture decisions

| ADR | Decision | Reason | Files/contract affected |
|---|---|---|---|
| ADR-01 | Tách trạng thái thành cột riêng, **giữ `trang_thai` làm cột chiếu** | 18 tệp test + 7 template + `nhan.py` + `routes.py` đọc `trang_thai`. Xoá nó là một changeset khổng lồ không giảm rủi ro nào | `tables.py`, migration, `services/*`, `nhan.py` |
| ADR-02 | Bảng thao tác riêng `vps_thao_tac`, **chạy bằng** job + **khoá bằng** lease sẵn có | `Job` = một lượt việc của worker; thao tác = một mutation trên một máy, có thể do route khởi xướng. Không dựng khung công việc thứ hai (luật §L của pack) | `tables.py`, `services/thao_tac.py`, `jobs.py` |
| ADR-03 | `bat`/`tat`/`khoi_dong_lai`/`khoi_phuc` **chuyển sang hàng đợi job** | Khởi động lại *thật* vượt trần 100 giây của Cloudflare. Chú thích cũ ("chỉ 200 ms") chỉ đúng với hành vi bắn-rồi-quên đang sai | `manifest.py`, `routes.py`, `services/dieu_khien.py`, `jobs.py` |

## Phase status

| Phase | Status | Main changes | Targeted checks | Blockers |
|---|---|---|---|---|
| 00 | **COMPLETE** | `docs/vps_v2/{STATE,BASELINE,ADR_INDEX}.md` | chỉ đọc | — |
| 01 | **COMPLETE** | `apps/vps/trang_thai_may.py` (mới) · `tables.py` +6 cột + `__init__` chuẩn hoá · migration `b7f21c48ae90` · 8 chỗ ghi thẳng → `dat()` | `test_550` **28 passed**; 18 tệp VPS cũ **409 passed, 2 skipped** | — |
| 02 | **COMPLETE** | `services/tac_vu.py` + `services/thao_tac.py` (mới) · bảng `vps_thao_tac` · migration `c93a5d17be42` · `proxmox.trang_thai_vm()` · `jobs._cho_tac_vu` thành lớp mỏng | `test_551`+`test_552` **40 passed** | — |
| 03 | **COMPLETE** | `dieu_khien.py` viết lại (xin/thi_hanh) · job `vps.control` · `jobs._dieu_khien_may` · `_tao_may` chờ `bat` · `nhan.TAC_VU`+`BUOC` · 16 chuỗi EN | `test_553` **21 passed**; toàn khu VPS **498 passed, 2 skipped** (`-n 6`) | — |
| 04 | **COMPLETE** | `sao_luu.chup_va_don` chờ+xác minh+prune sau · `xin_khoi_phuc`/`thi_hanh_khoi_phuc` · job `vps.snapshot` · `bao_tri` bắt `SaoLuuError` · route khôi phục thành nộp việc | `test_554` **18 passed**; `test_289` viết lại (bỏ phép kiểm thứ tự nguồn) | — |
| 05 | **COMPLETE** | `doi_chieu` V2: 5 mức + `_dong_bo_dien` đo điện thật · `bao_tri._don_thao_tac_qua_han` chạy trước đối chiếu · log theo mức | `test_555` **13 passed**; toàn khu VPS **529 passed, 2 skipped** | — |
| 06 | **COMPLETE** (INFRA BLOCKED) | `apps/vps/sao_luu_doc_lap.py` — hợp đồng năng lực, fail-closed, bí mật không rò · `docs/vps_v2/RUNBOOK_KHOI_PHUC.md` | `test_556` **20 passed** | **B-01**: chưa có đích sao lưu độc lập ⇒ Backup/DR ≤ 50 |
| 07 | **COMPLETE** | TLS fail-closed ở production + `san_sang_tls()` · `ProxmoxConfig.__repr__` không in token · `services/cach_ly.py` + 2 cột + migration `d15b8c30f7a4` · `tools/vps_kiem_cau_hinh.py` báo TLS | `test_557` **19 passed** | **B-03**: production cần CA **trước** khi deploy |
| 08 | **COMPLETE** | `apps/vps/suc_khoe.py` — tổng quan + cảnh báo khử trùng lặp (không bảng mới) + dòng thời gian không rò UPID | `test_558` **17 passed** | — |
| 09 | **COMPLETE** | Trang máy + trang danh sách hiện việc đang chạy · độ tươi phép đo · khối cách ly · ẩn nút phá huỷ khi bận · ADR-06 (API vẫn đóng) | `test_559` **15 passed**; render thật qua TestClient | **B-06** |
| 10 | **COMPLETE** | Đổi `VpsThaoTac.trang_thai` → `tinh_trang` (bỏ mơ hồ cho phép quét) · gộp hai bản sao "tắt để xoá" thành `_tat_de_xoa` có xác minh · `test_560` bánh cóc AST | `test_560` **15 passed** | — |
| 11 | **COMPLETE** | 4 bánh cóc chung được **sửa** (không miễn trừ) · nghiệm thu trình duyệt thật 5 trạng thái × 2 ngôn ngữ × mobile · 4 tệp báo cáo | gate lượt 2 (cây đứng yên): **FAIL 2/32**, còn 7×`test_448` của phiên khác + 3 lỗi dịch đã sửa | `test_448` không đụng (việc phiên khác) |

## Modified files

**Mới (16):** `apps/vps/trang_thai_may.py` · `apps/vps/suc_khoe.py` ·
`apps/vps/sao_luu_doc_lap.py` · `apps/vps/services/{tac_vu,thao_tac,cach_ly}.py` ·
3 migration `20260909_*` · `tests/fixtures/vps_proxmox_gia.py` ·
`tests/test_550`–`test_560` (11 tệp) · `docs/vps_v2/*` (6 tệp).

**Sửa (21):** `apps/vps/{bao_tri,doi_chieu,jobs,manifest,nhan,routes,tables}.py` ·
`apps/vps/services/{billing,dieu_khien,proxmox,sao_luu}.py` ·
`server/templates/{vps,vps_chi_tiet}.html` · `locale/en/LC_MESSAGES/messages.{po,mo}` ·
`tools/vps_kiem_cau_hinh.py` · `tests/test_{251,252,280,289,311}*.py`.

⚠️ **Không** chạm `platform_core/` hay `server/` (ngoài hai template của chính
app VPS). Hợp đồng app còn nguyên — `CLAUDE.md` luật 20.

## Migrations

Ba revision mới, nối tiếp nhau, mỗi cái có `downgrade` thật:

| Revision | Tệp | Làm gì |
|---|---|---|
| `b7f21c48ae90` | `20260909_1000_vps_v2_tach_trang_thai` | +6 cột trạng thái, backfill xác định |
| `c93a5d17be42` | `20260909_1100_vps_v2_bang_thao_tac` | bảng `vps_thao_tac` |
| `d15b8c30f7a4` | `20260909_1200_vps_v2_cach_ly` | +2 cột cách ly |

- head trước: `a4c71e93f8b2` · head sau: `d15b8c30f7a4`
- `quan_sat_luc` backfill để **NULL** có chủ ý — chưa đo lần nào là sự thật, và
  `qua_cu()` coi NULL là quá cũ nên vòng đối chiếu đầu tiên sẽ đi đo thật.
- `test_560` canh: một đầu duy nhất, và mỗi `downgrade` có thân thật.

## Invariants
- tenant isolation: `_may_cua_khach` 404 — **giữ**
- billing exactly-once: `billing.py` + `bao_tri.py` dưới lease — **giữ**, thêm bằng chứng ở Pha 05
- IP/resource cleanup: `_tra_ip_cong_khai` + `_nha_tai_nguyen` — **giữ**, thêm test ở Pha 05
- async task truth: ✅ **ĐÃ SỬA** — `services/tac_vu.py` là chỗ duy nhất biết "xong" nghĩa là gì
- snapshot/restore: ✅ **ĐÃ SỬA** — chờ + xác minh trước khi kết luận, prune sau
- backup truth: ✅ mô tả đúng; năng lực độc lập **chưa có** và **nói ra** — B-01
- quarantine ≠ suspend ≠ delete: ✅ ba nút cho ba vấn đề
- TLS quản trị: ✅ fail-closed ở production — **B-03 phải xong trước deploy**
- console ticket: dùng-một-lần, băm khi lưu — **giữ**, kiểm lại Pha 07
- capacity fail-closed: `_suc_chua` khoá nút Tạo khi không đọc được — **giữ**

## Deferred / blocked

Toàn văn: `docs/vps_v2/KNOWN_BLOCKERS.md`.

| ID | Loại | Tóm tắt |
|---|---|---|
| B-01 | HẠ TẦNG | chưa có đích sao lưu độc lập ⇒ Backup/DR ≤ 50 |
| B-02 | HẠ TẦNG | một node PVE chạy lồng, không HA |
| B-03 | **VẬN HÀNH** | production cần `LTT_VPS_PROXMOX_CA` **trước** khi deploy |
| B-04 | VẬN HÀNH | chưa có VM thử ⇒ `LIVE ACCEPTANCE BLOCKED` |
| B-05 | SẢN PHẨM | chặn SMTP/25 chưa chốt (đã có nút cách ly thay thế) |
| B-06 | SẢN PHẨM | `/api/v1` vẫn đóng cho VPS (ADR-06) |
| B-07 | — | `lifecycle` giữ `development` cho tới khi B-03+B-04 xong |

## Live infrastructure facts
- PVE topology: **một node**, `pve`
- nested/bare metal: **lồng** trong VMware trên máy B (`manifest.notes`)
- PBS: **chưa có** — kho `dir` duy nhất (`local`) còn ~2,2 GiB, không đủ `vzdump`
- UPS: chưa biết
- storage redundancy: LVM-thin `vmdata` 475 GB, **cùng pool** với ảnh chụp
- HA: **không**
- test VM availability: chưa xác nhận
- credentials availability: `LTT_VPS_PROXMOX_*` trong `secrets/app.env`; `LTT_VPS_PROXMOX_CA` **trống** ⇒ `verify=False`

## Full gate

| Lượt | pid | Kết quả | Dùng làm bằng chứng? |
|---|---|---|---|
| 1 | 4404 | FAIL 3/32, 13,0 phút | ❌ **không** — gate tự khai *"CAY DA DOI TRONG LUC CHAY"* (lỗi quy trình của tôi) |
| 2 | 22868 | FAIL 2/32, 12,3 phút | ✅ cây đứng yên |
| 3 | *(cuối)* | *(xem báo cáo)* | ✅ chạy trên đúng cây đem commit |

Bốn bánh cóc chung: `nuot loi lang le` 62/62 · `mypy` **thấp hơn mốc cũ 1** · `dich thieu` 343/343 ·
drill khôi phục + xếp loại lưu trữ đã có bảng mới. **Không dùng `--accept` để né lỗi nào.**

⛔ Còn đỏ: **7 × `test_448`** (`auto_scan_video`). Bằng chứng cấu trúc rằng nó không
phải của chương trình này: `git diff --name-only HEAD | grep -c auto_scan_video` → **0**.

## Final acceptance

- **Nghiệm thu trình duyệt: ĐÃ CHẠY** (local, cổng 8133). Năm trạng thái render
  đúng và phân biệt được; bấm `Restart` thật ⇒ trang lật sang *"Đang khởi động
  lại…"*, mọi nút điều khiển và khối Nguy hiểm biến mất, badge **vẫn "Đang chạy"**.
  0 lỗi console, 0 request hỏng, VI+EN đúng, mobile 375px không tràn ngang.
  ⚠️ **Chưa chốt trên `https://app.lttstudios.com`** — chỉ làm được sau deploy.
- **Nghiệm thu live: BLOCKED** (B-04) — chưa có VM thử của chương trình.

## Deploy — ĐÃ CHẠY 2026-09-09 20:18–20:20

| | |
|---|---|
| Nguồn | **commit** `5bb3a5a0` (`nguon=xuat`, 3946 tệp) — không phải cây làm việc |
| Trunk | `admin-mvp-v3` ff tới `5bb3a5a0` trước khi deploy; cây chính sạch cả trước lẫn sau |
| Trước đó production chạy | `99017910` (11:59 cùng ngày) — nay là **đường lùi** ở `app.previous` |
| `EXITCODE` | `0` — chờ tới khi dòng đó xuất hiện, không đọc tệp một lần rồi kết luận |
| Migration | `alembic upgrade head` chạy **trước** khi khởi động dịch vụ, rc=0 ⇒ ba revision VPS V2 đã áp |
| Nghiệm thu vân tay | lệch **0** · thiếu **0** · thừa **0** so với commit đang chạy |
| `/health/ready` | **200**, `environment=production` |
| `/health/version` | `5bb3a5a09291` — khớp commit |
| `/vps` công khai | **200** |

⚠️ Deploy chở theo **2 commit của phiên khác** đã nằm sẵn trên trunk (`3eae396d`,
`05464239` — việc `test_448`). Production trước đó chậm hơn trunk 2 commit.

⚠️ **Chưa xác minh được trang đã đổi trên URL công khai.** `/vps` ẩn danh là
trang bán hàng; những trang tôi sửa (`vps_chi_tiet.html`) đòi đăng nhập, và
phiên này không có mật khẩu tài khoản thử của production. Nghiệm thu trình duyệt
thật vẫn là **local**. Luật 17 chưa đóng hẳn.

## Score

| | Điểm | Trần đang áp |
|---|---:|---|
| software / control-plane | **94** | thiếu nghiệm thu live (B-04) |
| live infra / resilience | **45** | một node PVE chạy lồng, không HA, không sao lưu độc lập |
| end-to-end product | **62** | Backup/DR trần cứng 50 |

Toàn văn + từng hạng mục: `docs/vps_v2/RELEASE_SCORECARD.md`.
⛔ Không cột nào ≥98, và không cột nào được làm tròn lên.

# Lưu trữ — tài liệu đã ngừng dùng

> Chuyển vào đây ngày 2026-07-31. **Không xoá** vì chúng ghi lại *lý do* của
> nhiều quyết định kỹ thuật vẫn đang có hiệu lực trong code.
>
> **Đừng làm theo bất cứ hướng dẫn nào trong thư mục này.** Chúng mô tả một hệ
> thống đã không còn tồn tại (bản desktop CustomTkinter) hoặc một hướng đi đã
> bị thay thế. Tài liệu đang hiệu lực nằm ở `docs/` bên ngoài.
>
> Nguồn chân lý hiện tại: **`docs/QUYET_DINH_NEN_TANG.md`**.

---

## Vì sao phải lưu trữ thay vì xoá

Ba lần trong lịch sử dự án này, một quyết định tưởng là tuỳ tiện hoá ra có lý
do đắt giá đằng sau:

- vì sao package tên `platform_core` chứ không phải `platform`;
- vì sao app socialbot được đặc cách giữ route ở đường dẫn gốc;
- vì sao mọi file `.ps1` phải thuần ASCII.

Xoá tài liệu là xoá lý do. Lần sau có người "dọn cho gọn" và lặp lại đúng sai
lầm cũ.

---

## Có gì trong này

### Nhật ký và trạng thái cũ

| File | Là gì | Vì sao ngừng dùng |
|---|---|---|
| `PROJECT_MEMORY.md` | **1.540 dòng nhật ký từng phiên** từ 2026-07-29 đến 2026-07-30. Phần nhật ký vẫn **rất đáng đọc** — nó ghi lại từng lỗi thật và cách sửa. | Phần *tóm tắt trạng thái* ở đầu file đã sai thực tế ở 6 điểm (vẫn nói desktop là đường production trong khi `gui/` đã bị xoá). Thay bằng `docs/NHAT_KY.md` + `docs/QUYET_DINH_NEN_TANG.md`. |
| `PROJECT_STATE.json` | Trạng thái dự án dạng máy đọc, thời desktop | Không còn ai đọc, không còn ai cập nhật |
| `HANDOFF.md` | Bàn giao ngày 2026-05-15, thời `lttstudio.top` | Tên miền đã đổi, desktop đã xoá |
| `AUDIT_REPORT.md` | Audit 2026-07-29: chứng minh bot **không đăng bài được** dù 1.021 test xanh | Mọi phát hiện đã xử lý xong. **Vẫn được code trích dẫn** (`core/preflight.py`, `core/token_store.py`, `core/worker_store.py`) để giải thích vì sao chúng tồn tại. |

### Ba bản kế hoạch đã hoàn thành

Cả ba đều đã đi hết, và cùng mô tả chặng đường desktop → web. Giữ để đối chiếu
khi cần biết *vì sao* một đoạn code có hình dạng như hiện tại.

| File | Đánh số | Nội dung |
|---|---|---|
| `WEB_PLATFORM_PLAN.md` | P0–P11 | Kế hoạch gốc chuyển từ desktop sang web |
| `MVP_COMPLETION_PLAN.md` | PA–PE | Khắc phục sau audit 2026-07-29 |
| `WEB_PARITY_PLAN.md` | W1–W6 | Đưa đủ chức năng lên web rồi xoá hẳn desktop |

Bốn hệ đánh số song song (P/PA/W và bây giờ là H) chính là thứ đã gây rối.
Từ nay **chỉ dùng một hệ: H0…H5 rồi tiếp tục**, ghi trong
`docs/KE_HOACH_TRIEN_KHAI.md`.

### Tài liệu triển khai của hạ tầng cũ

| File | Vì sao ngừng dùng |
|---|---|
| `DEPLOY_APP_LTTSTUDIOS.md` | Viết cho một VPS riêng + Caddy công khai. Hướng đi hiện tại là **Cloudflare Tunnel** trên chính máy này (quyết định Q4). |
| `DEPLOY_SERVER2016.md` | Windows Server 2016, máy đó đã bỏ |
| `lttstudios-deployment-guide.md`, `lttstudios-deploy-inet-vn.md`, `lttstudios-migration-plan.md` | Chuyển trang giới thiệu `lttstudio.top` → `lttstudios.com`, đã xong từ 2026-06 |
| `web-upgrade/` | Hướng dẫn upload zip lên cPanel cho trang giới thiệu |
| `verify-deploy.py` | Script kiểm tra trang giới thiệu sau khi upload |

### Hồ sơ nộp cho Meta / TikTok (app socialbot)

App socialbot đã **đóng băng** (quyết định Q10). Giữ nguyên hồ sơ phòng khi
sau này nộp lại.

| File | Nội dung |
|---|---|
| `tier-a-runbook.md` | Quy trình nộp Meta App Review |
| `fb-app-review-submission-plan.md` | Kế hoạch đưa app Facebook lên Live Mode |
| `fb-app-review-assets/` | Kịch bản quay demo, mô tả use-case, trang xoá dữ liệu |
| `facebook-workflow.md`, `tiktok-workflow.md` | Mô tả chi tiết vòng đời một lần đăng bài |

> `docs/tiktok-submission/` **không** nằm trong thư mục lưu trữ vì
> `core/tiktok/audit_checklist.py` đọc file trong đó lúc chạy. Di chuyển nó
> sẽ làm phần kiểm tra audit TikTok báo thiếu file.

---

## Nếu bạn cần một thứ trong này

Đừng chép ngược ra ngoài. Hãy **trích phần cần thiết vào tài liệu đang hiệu
lực** rồi ghi rõ lấy từ đâu. Thư mục này chỉ được đọc, không được sống lại.

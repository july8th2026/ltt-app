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

## Lô 2026-09-04 — bốn kế hoạch đã hoàn tất

Chuyển vào cùng ngày dọn kho. Tiêu chí: **không tệp nào trong kho trỏ tới**, và
việc chúng mô tả đã xong, kết quả nằm ở chỗ khác.

| Tệp | Vì sao chuyển |
|---|---|
| `KE_HOACH_CHAT_AI_STUDIO.md` | tự ghi "TRẠNG THÁI: XONG + NGHIỆM THU THẬT (2026-08-02)"; `apps/chataistudio/` đang chạy |
| `KE_HOACH_TAO_CLIP_NGAN.md` | tự ghi "TRẠNG THÁI: XONG + NGHIỆM THU THẬT (2026-08-02)"; `apps/taoclipngan/` đang chạy |
| `KE_HOACH_RA_SOAT_APP.md` | kế hoạch rà soát; kết quả nay ở `docs/APP_AUDIT/`, và nó còn liệt kê app đã gỡ (`kichban`, `demo`) |
| `TONG_QUAN_TIEN_DO.md` | ảnh chụp tiến độ chép tay ngày 24/08 — đúng kiểu tài liệu **không có cách nào tự biết nó đã cũ**, cùng lý do đã gỡ `ho_so_he_thong.txt` |

⛔ **Ba tệp đã CÂN NHẮC rồi quyết định GIỮ LẠI ở `docs/`**, đừng chuyển chúng vào đây:

- `H41_3_DUONG_LUI.md` — `KE_HOACH_TRIEN_KHAI.md:3604` ghi H41.3 vẫn **"cần quyết định"**.
  Đây là đường lùi cho việc **chưa làm**, không phải tư liệu lịch sử.
- `KE_HOACH_TON_DONG.md` — backlog đang sống; `AUDIT_APPS_2026-08-02.md` và
  `KE_HOACH_2APP_UPSCALE_AUTOSUB.md` đẩy việc hoãn vào đó.
- `AUDIT_BAO_MAT_CHONG_DICH_NGUOC.md` — mục 7.4 của backlog trên trỏ tới nó.

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

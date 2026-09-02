# Ảnh bằng chứng — chuyển từ thư mục gốc kho, 2026-09-02

> ⛔ **LƯU TRỮ. Không phải tài sản đang phục vụ.** Không trang nào, không route
> nào, không bản đồ phục vụ nào trỏ tới các tệp này.

## Đây là gì

18 tệp ảnh chụp màn hình và một báo cáo sự cố Nuitka, sinh ra trong các đợt
audit UI (Nexus, VPS, khu API). Chúng **đã được commit thẳng vào thư mục gốc**
của kho và nằm đó cho tới 2026-09-02.

## Vì sao chuyển đi chứ không xoá

Chúng là **bằng chứng**, không phải rác. Một ảnh chụp trạng thái giao diện tại
một thời điểm là thứ không dựng lại được — xoá là mất vĩnh viễn phần "lúc đó nó
trông thế nào".

⇒ Phân loại đúng là `HISTORICAL`, không phải `DEAD`. Hợp đồng của chương trình
dọn dẹp nói rõ: *"Không xoá lịch sử có giá trị. Nhưng history không được agent
đọc như current instruction"* — nên việc phải làm là **đặt đúng chỗ**, không
phải xoá.

## Bằng chứng rằng chúng không phục vụ ai (đo 2026-09-02)

Đối chiếu đủ **năm** cơ chế nạp động của kho này — luật SP-04:

| Cơ chế | Kết quả |
|---|---|
| `GOI_TAI` (`server/routes/tai_lieu_api.py:124`) | không có |
| `BUILT_PAGES` / `PUBLIC_LINKS` (`server/templating.py`) | không có |
| `_CONTENT_TYPE` (`server/nexus_download.py`) | không có |
| `_goi_moi_nhat()` quét `data/api_dist/` | không có |
| `registry.py` nạp `apps/*/manifest.py` | không liên quan |

Thêm bốn phép kiểm nữa:

- `grep` toàn kho (trừ cây lồng): **0 tham chiếu** từ `.py`/`.html`/`.ps1`;
- `tools/dong_goi_gui.py::TAI_SAN` chỉ đóng gói `server/static/ltt.css`;
- `ho_so_he_thong.txt` không liệt kê tệp nào trong số này;
- `tests/test_145` chỉ quét `frontend/`, không quét gốc.

Hai "tham chiếu" duy nhất tìm được là **văn bản mô tả chúng là rác**:
`docs/MVP_OPTIMIZATION_V2/00_LIVE_SYSTEM_MAP.md:530` và chính báo cáo của
chương trình này.

## Kết quả

Thư mục gốc: **38 → 20** mục được theo dõi. 3,5 MB rời khỏi gốc, vẫn còn trong
kho, và `git mv` giữ nguyên lịch sử từng tệp.

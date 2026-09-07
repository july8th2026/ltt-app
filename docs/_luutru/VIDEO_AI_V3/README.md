# LTT VIDEO AI **V3** — tài liệu đã ngừng, giữ làm lịch sử

⛔ **KHÔNG phải nguồn chân lý.** Chương trình V3 đã **dừng ngày 06/09/2026** và
   được thay bằng **V2.1 (WanGP làm engine duy nhất)**. Nguồn chân lý hiện tại
   là `docs/VIDEO_AI_V2/`.

⛔ **Đừng dùng các con số ở đây để quyết định gì hôm nay.** Chúng đo trên một
   ngăn xếp khác (ComfyUI, một bộ model khác, một loại pod khác). `CLAUDE.md`
   nói thẳng vì sao điều này nguy hiểm: *"một bản đồ cũ nguy hiểm hơn không có
   bản đồ, vì nó trả lời tự tin"*.

## Vì sao vẫn giữ

31 tệp này chứa thứ **không dựng lại được**: sổ chi phí thật, kết quả đo thật,
và chuỗi quyết định giải thích *vì sao* V3 đi đường đó rồi dừng. Xoá chúng là
xoá lý do — và lần sau sẽ có người đi lại đúng con đường ấy.

| Nhóm | Tệp | Giá trị còn lại |
|---|---|---|
| Tiền đã tiêu | `COST_LEDGER.csv`, `COST_BUDGET_LEDGER.md` | số **thật**, không ước |
| Kết quả đo | `DO_LUONG_KET_QUA.csv`, `THAM_SO_VA_THOI_GIAN.md` | mốc so sánh cho V2.1 |
| Quyết định | `DECISIONS.md`, `ADR_REMOTE_VIDEO_COMPUTE.md` | vì sao chọn, vì sao bỏ |
| Vận hành cloud | `VAN_HANH_MAY_C.md`, `CLOUD_SAFETY_PLAN.md` | 23 đường REST của nhà cung cấp, đã dò tay |
| Danh mục model | `MODEL_BOM_*.csv`, `OSS_PIPELINE_CATALOG.md` | khảo sát thượng nguồn |

## Xuất xứ

Khôi phục **nguyên byte** ngày 07/09/2026 từ nhánh
`claude/ltt-video-ai-v3-p00-3f5713` (`git show <nhánh>:docs/VIDEO_AI/<tệp>`).

⭐ **Không merge một dòng mã V3 nào.** Kiến trúc V2.1 đã khoá: *"New V2 code:
   import legacy = FORBIDDEN"*, và quyết định `P06` rút thành **"không merge"**.
   Chỉ tài liệu và dữ liệu đo được mang sang.

📌 Vì sao đặt ở `docs/_luutru/`: đó là chỗ kho này **đã** dùng cho tài liệu của
   chương trình ngừng — `TONG_QUAN_TIEN_DO.md` và `KE_HOACH_RA_SOAT_APP.md` nằm
   sẵn ở đấy. Đây là theo quy ước có sẵn, không phải đặt ra chỗ mới.

⚠️ `DO_LUONG_KET_QUA.csv` giữ nguyên kết dòng CRLF của bản gốc. Đó là **nội
   dung**, không phải một lần lật kiểu — `tools/check_xuong_dong.py` đã xác nhận.

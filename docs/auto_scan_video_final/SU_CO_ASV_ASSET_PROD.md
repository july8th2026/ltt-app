# Sự cố production: không có bảng `asv_*` dù alembic báo đã áp dụng

> Phát hiện 23/09/2026 bởi phiên *Phân tích hệ thống VPS* (worker log lặp
> `UndefinedTable: relation "asv_asset" does not exist`, lần đầu 16:28:07).
> Chẩn đoán dưới đây **chỉ đọc**, không ghi một câu lệnh nào vào CSDL.

## Đo được gì (CSDL `lttplatform`, PostgreSQL 17.10)

| Câu hỏi | Trả lời |
|---|---|
| `asv_asset` có không | **KHÔNG** |
| Các bảng `asv_*` khác | **KHÔNG có bảng nào** (0/5: `asv_run`, `asv_stage`, `asv_asset`, `asv_work_item`, `asv_usage`) |
| Còn sót đối tượng tên `asv*` (sequence/index/view) | **Không còn gì** |
| `alembic_version` | `56a971862a15` — head, và `f2b8d16e05a3` (tạo `asv_asset`) **nằm trong tổ tiên** |
| Bảng của migration **mới hơn** (`vc_phien`, `vc_da_tai` — hôm nay) | **CÓ** |
| Tổng số bảng `public` | 105 |

## Kết luận

⇒ **Chuỗi migration đã chạy VƯỢT QUA các migration của ASV, không phải bảng bị
xoá sau đó.** Nếu bảng từng tồn tại rồi bị `DROP`, ta vẫn thấy dấu vết ở chỗ
khác hoặc ít nhất một bảng `asv_*` sống sót; đây là **0/5 và sạch trơn**, trong
khi migration ra đời *sau* (hôm nay) lại có bảng.

⛔ Giả thuyết "diễn tập khôi phục backup làm hỏng" **SAI**:
`docs/reports/dien-tap-khoi-phuc-2026-09-23.md` ghi rõ diễn tập chạy trên CSDL
tạm `lttplatform_dienthu_<stamp>`, *"không đụng live CSDL"*, và lượt hôm qua còn
**thất bại** ở `pg_restore` nên không nạp được gì.

⚠️ `alembic upgrade head` **KHÔNG sửa được**: nó tin rằng đã xong.

## Ảnh hưởng thật

- **Khách: không.** ASV khai `enabled=False` và `/auto-scan-video` trả 404 trên
  production (cờ `LTT_AUTO_SCAN_VIDEO`). Không lần chạy nào tồn tại để mất.
- **Hiện tại:** vòng dọn tài sản hết hạn của worker lỗi mỗi chu kỳ (12 lần tính
  tới 19:43) — rác log, và bộ quét coi như không chạy.
- **Ngày mở khách:** đây là **chặn cứng**. Lần chạy đầu tiên sẽ chết ở `tao_run`.


## Bổ sung 23/09 tối — đối chiếu cơ học (phiên *Phân tích hệ thống VPS*) + kiểm chéo

**Họ dựng chuỗi `down_revision` từ head và gom MỌI `create_table` trong tổ tiên,
so với `pg_tables` thật: 80 bảng khai, thiếu đúng 7 dòng.** Bỏ `vps_port_map`
(bị drop có chủ đích khi VPS chuyển sang một-IP-mỗi-VM, 24/08) thì phần không
giải thích được **chỉ còn ASV — và là TOÀN BỘ 5 bảng của cả 4 migration**, trải
hai ngày khác nhau (01/09 và 03/09), trong khi mọi revision trước và sau đều có
bảng.

**Tôi kiểm chéo hai điều họ chưa loại trừ:**

1. **Không migration nào KHÁC xoá bảng ASV.** Grep `drop_table("asv_…")` toàn
   `alembic/versions/` chỉ khớp đúng bốn tệp ASV — tức hàm `downgrade()` của
   chính chúng. Không ai xoá từ nơi khác.
2. ⚠️ **Mốc "lỗi đầu tiên 13/09" KHÔNG phải lúc bảng biến mất.** Bộ quét tài sản
   (`assets.quet_het_han` + `bao_tri` trong manifest) chỉ ra đời **04/09**
   (`8d56c05d`, pha 27). Trước đó **không câu lệnh nào chạm `asv_asset`**, nên
   không thể có lỗi để mà ghi. 13/09 nhiều khả năng là lần **deploy** đầu tiên
   mang bộ quét lên production — nó nói về lịch deploy, không nói về schema.

⇒ Giả thuyết còn đứng vững nhất: **các migration ASV được đánh dấu đã chạy mà
không thực thi** (`alembic stamp` hoặc đẩy tay qua khối đó). Một biến thể cũng
khớp mọi bằng chứng: ai đó `downgrade` riêng khối ASV (hàm `down()` của chính
chúng xoá sạch, không để lại dấu) rồi `stamp` tiến lên.

⛔ **Log PostgreSQL không phân xử được chuyện này**, và đây là giới hạn của kênh
chứ không phải kết luận: `log_statement` không bật, nên log chỉ ghi LỖI — **0
dòng `CREATE TABLE`** trong toàn bộ log đầu tháng 9. Vắng mặt ở đây không phải
bằng chứng vắng mặt. Muốn truy tiếp phải đọc lịch sử lệnh / log deploy quanh
01–03/09.

## Phương án (⚠️ CẦN CHỦ DỰ ÁN DUYỆT — ghi schema production là thao tác khó đảo)

| # | Cách | Rủi ro | Ghi chú |
|---|---|---|---|
| **A** | Chạy phần `upgrade()` của **đúng 5 migration ASV** trong MỘT giao dịch, rồi đối chiếu `Base.metadata` | Thấp — chỉ `CREATE TABLE/INDEX`, **thêm mới**, không có dữ liệu để mất | Cách chuẩn cho ca "đã stamp nhưng chưa chạy" |
| B | `alembic downgrade` về trước ASV rồi `upgrade head` | **RẤT CAO — cấm** | `downgrade` sẽ chạy `down()` của mọi revision sau đó ⇒ **xoá cả `vc_phien`/`vc_da_tai` và các bảng khác đang có dữ liệu thật** |
| C | Để nguyên tới ngày mở ASV | Không | Log tiếp tục bẩn; nợ vẫn còn nguyên |

**Đề xuất: A**, kèm ba điều kiện: sao lưu CSDL trước, chạy trong một giao dịch
(`BEGIN … COMMIT`, hỏng thì cuộn lại), và đối chiếu sau khi chạy bằng chính
`Base.metadata` chứ không bằng mắt.

## Câu chưa trả lời được (và không nên đoán)

**Vì sao chuỗi vượt qua ASV?** Không còn bằng chứng trong CSDL. Hai khả năng:
`alembic stamp` ở một lần cài/khôi phục nào đó, hoặc migration ASV được **chèn
vào giữa chuỗi** sau khi production đã đi qua điểm đó. Người dùng app chạy
`ltt_app` không có quyền đọc log PostgreSQL (`pg_read_all_settings`), nên muốn
truy ra thủ phạm thì phải đọc log PG bằng quyền cao hơn — việc đó **chưa làm**.

⇒ Nếu chỉ sửa mà không tìm ra nguyên nhân, **không có gì bảo đảm nó không lặp
lại** ở app tiếp theo. Đáng làm trước khi mở khách, không đáng chặn hôm nay.

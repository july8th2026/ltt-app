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


## Nguyên nhân — ĐÃ TRUY RA (23/09 tối, phiên *Phân tích hệ thống VPS* + kiểm chéo)

Mảnh ghép nằm trong `.err.log` của deploy, không phải `.out.log`: alembic ghi qua
`logging` nên ra **stderr**.

1. **Alembic CÓ chạy 01/09 và nói "không có gì để làm".**
   `deploy-20260901-011035.err.log` chỉ có hai dòng khởi tạo context, **không có
   `Running upgrade`** — trong khi 21 lượt deploy khác đều có. Vắng mặt ở đây có
   nghĩa vì có đối chứng.
2. ⚠️ **Dòng `[OK] Lược đồ CSDL đã ở bản mới nhất` KHÔNG phải bằng chứng.**
   `setup/2-cai-dat.ps1:915` in nó **vô điều kiện** sau khi `alembic upgrade head`
   trả mã 0 — mà *"không có gì để làm"* cũng trả 0. Một dòng OK cho một việc
   chưa từng xảy ra.
3. **Khoảng trống lịch sử:** head rời `c7b91e4a2f80` lúc 01/09 23:04, tới 06/09
   08:51 đã ở `7d2c1e9f4a03`, **không lượt deploy nào ở giữa ghi `Running
   upgrade`** ⇒ `alembic_version` bị **đẩy tay** qua **5 revision** (4 ASV +
   `chatltt_cay_hoi_thoai`) mà không thực thi cái nào: `stamp`, hoặc `UPDATE`
   thẳng vào bảng.

**Vì sao chỉ ASV chết mà chatltt thì không** (tôi kiểm chéo, chỉ đọc):
`chatltt_conversation` / `_message` / `_execution` **CÓ** trên production với dữ
liệu thật (220 / 519 / 282 hàng), và **cột khớp tuyệt đối** với bản khai ORM
(10/10 · 11/11 · 24/24, không thiếu không thừa). Chỉ đúng revision bị nhảy tạo
ba bảng đó, và nền tảng **không** dùng `create_all` (`platform_core/db.py:16`)
⇒ ai đó đã tạo chúng **ngoài alembic**, và tạo đúng.

⇒ ASV là app **duy nhất** trong khối bị nhảy mà không ai sửa tay — vì nó
`enabled=False`, không khách nào chạm, nên **không có gì để kêu**. Sự cố nằm im
20 ngày và chỉ lộ ra khi bộ quét tài sản (04/09) được deploy.

### Việc nên làm ngoài phạm vi ASV

`setup/2-cai-dat.ps1:915` in `[OK]` cho cả trường hợp alembic không làm gì. Dòng
OK ấy chính là thứ khiến sự cố này sống sót qua **21 lượt deploy**. Sửa đúng:
đọc stdout của alembic, chỉ in OK khi thấy `Running upgrade` **hoặc** khi đối
chiếu `Base.metadata` với `pg_tables` cho kết quả rỗng.


## Xác nhận độc lập 23/09 tối — và sự cố nay đã CÓ TIẾNG

Phiên *Phân tích hệ thống VPS* đã gộp `main` (`34005462`) hai thứ:

1. `setup/2-cai-dat.ps1` bắt **mọi** luồng alembic bằng `*>` (nó ghi qua
   `logging` = **stderr**; `>` đơn mất sạch — đúng lý do log deploy đầu tháng 9
   trống trơn), đếm `Running upgrade` và in **đúng số** migration vừa chạy.
   *"Đã chạy 4 migration"* và *"không có migration nào để chạy"* không còn in ra
   cùng một dòng chữ.
2. `tools/kiem_luoc_do.py` — đối chiếu `Base.metadata` với `information_schema`
   **cả cột**, gom **theo app**, **không lọc app đang tắt** (lọc ở đây là bỏ qua
   đúng ca cần bắt), chạy ở **mỗi lần deploy**, có bánh cóc chốt rằng nó *được
   gọi* chứ không chỉ tồn tại.

**Chạy thật trên production:**

```
LECH - 5 bang thieu, 0 cot thieu
  app auto_scan_video: thieu 5 bang
```

⭐ **0 cột thiếu trên TOÀN lược đồ** — mở rộng phép kiểm tay của tôi (chatltt
10/10 · 11/11 · 24/24) ra mọi bảng của mọi app. **ASV là sai lệch duy nhất còn
lại trong CSDL production**, và nay mỗi lần deploy sẽ in nó ra.

## Phương án (⚠️ CẦN CHỦ DỰ ÁN DUYỆT — ghi schema production là thao tác khó đảo)

| # | Cách | Rủi ro | Ghi chú |
|---|---|---|---|
| **A** | Chạy phần `upgrade()` của **đúng 5 migration ASV** trong MỘT giao dịch, rồi đối chiếu `Base.metadata` | Thấp — chỉ `CREATE TABLE/INDEX`, **thêm mới**, không có dữ liệu để mất | Cách chuẩn cho ca "đã stamp nhưng chưa chạy" |
| B | `alembic downgrade` về trước ASV rồi `upgrade head` | **RẤT CAO — cấm** | `downgrade` sẽ chạy `down()` của mọi revision sau đó ⇒ **xoá cả `vc_phien`/`vc_da_tai` và các bảng khác đang có dữ liệu thật** |
| C | Để nguyên tới ngày mở ASV | Không | Log tiếp tục bẩn; nợ vẫn còn nguyên |

**Đề xuất: A**, kèm ba điều kiện: sao lưu CSDL trước, chạy trong một giao dịch
(`BEGIN … COMMIT`, hỏng thì cuộn lại), và đối chiếu sau khi chạy bằng chính
`Base.metadata` chứ không bằng mắt.

## Câu còn lại

**Vì sao chuỗi vượt qua ASV?** Không còn bằng chứng trong CSDL. Hai khả năng:
`alembic stamp` ở một lần cài/khôi phục nào đó, hoặc migration ASV được **chèn
vào giữa chuỗi** sau khi production đã đi qua điểm đó. Người dùng app chạy
`ltt_app` không có quyền đọc log PostgreSQL (`pg_read_all_settings`), nên muốn
truy ra thủ phạm thì phải đọc log PG bằng quyền cao hơn — việc đó **chưa làm**.

⇒ Nếu chỉ sửa mà không tìm ra nguyên nhân, **không có gì bảo đảm nó không lặp
lại** ở app tiếp theo. Đáng làm trước khi mở khách, không đáng chặn hôm nay.

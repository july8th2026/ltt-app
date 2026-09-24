# P8 Task 6 — FLOW G (điều kiện ra phase gốc 11)

> §18.5 G — câu *"Đọc Sheet mỗi sáng, lấy READY, tạo video, chờ tôi duyệt"* ⇒
> Agent sinh draft v3 **qua validator không lỗi**, có cron + sheets + filter +
> foreach + video + human.

## Kết quả: **4/6 thành phần**, và hai cái thiếu là phép đo

`tests/test_2935_flow_g.py` — 5 passed in 1,84 s.

| Thành phần | Trạng thái |
|---|---|
| filter | ✅ `core.filter` |
| foreach | ✅ `core.foreach` + `core.foreach_end` |
| video | ✅ `app.video.generate` (registry thật, 19 tool) |
| human | ✅ `core.human` |
| **sheets** | ⛔ **chưa tồn tại** — connector là phase gốc **8**, chưa chạy |
| **cron** | ⛔ **không thể là node** — P4 làm trigger thành **hàng** `workflow_trigger` (`kind`/`config`/`next_fire_at`, ⛔ không có cột `node_id`), khác thiết kế §18.5 giả định |

⭐ Hai dòng ⛔ ấy **được đo, không được giả định**: `test_sau_thanh_phan_FLOW_G_hai_cai_chua_co`
hỏi `nut.tat_ca(cong_cu=<registry thật>)` xem có `*sheet*` / `*cron*` không, và
**đỏ ngay khi chúng xuất hiện** — buộc người thêm Sheets phải nâng FLOW G lên
6/6 thay vì để một phép kiểm xanh nói dối.

## Đã chứng minh được gì

- Draft v3 do planner sinh đi qua **đúng** `bien_dich.bien_dich` (cổng publish),
  `loi == ()`, thứ tự tô-pô thật (`loc` … `duyet`).
- `bao_gia_do_thi` ra trần **> 0**, `bang_gia["video"] > 0`, `he_so_lap["video"]
  == 20` (= `max_items` của `foreach`) ⇒ trần nhân theo vòng, không phải một
  con số phẳng.
- `soan_draft(db=None, …)` chạy được ⇒ **không câu lệnh CSDL nào** chạy trong
  lượt soạn: Agent không publish, không ghi.

## Số đo của lượt gọi model (prompt thật, registry thật)

```
node trong danh muc:  32   (18 `app.*` + 14 `core.*`, chỉ node `publish_duoc`)
ky tu prompt:         20 327
uoc token:            ~5 081
```

## 🔴 CHƯA LÀM ĐƯỢC — nói rõ, không giấu

1. **Chưa gọi model thật một lần nào.** Đường `soan_draft(db, …)` đi qua
   `planner.goi_model` → `admission.acquire`, và `acquire` **GHI** một hàng
   lease. CSDL production là **chỉ đọc** với làn này (CLAUDE.md), nên một lượt
   đo thật sẽ vi phạm luật ấy. Một CSDL scratch cũng không thay được: bản khai
   provider/khoá API sống ở CSDL production. ⇒ Chất lượng đồ thị `ltt-3.5` sinh
   ra **chưa có số**, và bộ test này **không** nói gì về nó.
2. ⚠️ **`tools/chay_test_pg.py` KHÔNG làm `test_2931`/`test_2932` chạy trên
   PostgreSQL.** Chạy thử ra `33 passed`, nhưng fixture `db`
   (`tests/test_1711_wf_luoc_do_dong_co.py:8`) **ghi đè** `LTT_DATABASE_URL`
   bằng một tệp SQLite — nên con số ấy là một phép đo **đọc thứ đại diện**.
   Phép đo PostgreSQL thật của động cơ là ba tệp `*_pg.py`:
   ```
   tools/chay_test_pg.py -q test_1720_wf_dong_co_pg test_1787_wf_flow_acf_pg
                            test_1798_wf_flow_be_pg
   -> 31 passed, 1 xfailed in 63,46 s
   ```
   Chúng phủ động cơ (nơi P8 thêm `tac_tu.tiep_buoc`), ⛔ **không** phủ
   `ai.agent` trên PostgreSQL. Muốn phủ thì phải viết `test_29xx_..._pg.py`
   dùng fixture PG — chưa làm.

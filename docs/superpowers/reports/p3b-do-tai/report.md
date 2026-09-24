# P3b — Đo tải `foreach` 1000 phần tử + trần song song §18.5

Đo trên **PostgreSQL thật** (CSDL scratch, giữ `postgres_test` suốt pha đo, ⛔ không giữ `cpu_nhieu`).
Đồ thị: mảng N phần tử → `core.foreach(max_items=N, parallelism=P)` → một node **job thật**
(`tool text.chat`, qua `Job`/`jobs.complete`) → `core.foreach_end`.

## Việc 1 — `foreach` có còn `O(node đổi)` không? **KHÔNG.**

⚠️ **Câu phép đo trả lời:** mỗi vòng động cơ đọc bao nhiêu **hàng** `ForeachMuc`, so với số phần tử
thực sự đổi trạng thái vòng đó (= `parallelism`). Bọc `vong_lap._muc_theo_chi_so` để đếm.

| N | P | số vòng động cơ | lần gọi | hàng đọc/lần | **tổng hàng đọc** | tổng giây | SQL/tick |
|---|---|---|---|---|---|---|---|
| 10 | 8 | 3 | 4 | 10.0 (=N) | 40 | 0.35 | 226 → 264 |
| 100 | 8 | 14 | 15 | 100.0 (=N) | 1 500 | 2.67 | 226 → 409 |
| 1000 | 8 | 126 | 127 | 1000.0 (=N) | **127 000** | 31.67 | 226 → 409 |

**Hình dạng:** hàng đọc mỗi lần gọi = đúng N ở **mọi** tick, không giảm theo số phần tử đã xong.
Số tick ≈ N/P + 1 ⇒ tổng công ≈ **N²/P**. Dự đoán 1000²/8 = 125 000, đo được 127 000.

⭐ **Số câu SQL mỗi tick gần như KHÔNG đổi theo N** (226→409, ổn định qua cả ba mức). ⇒ **đếm câu
SQL không bắt được lỗi này; phải đếm HÀNG.** Một phép đo "số truy vấn không tăng" ở đây sẽ kết luận
"không có vấn đề" — và sai.

**Nguyên nhân (đã đối chiếu mã):** `platform_core/workflow/nut_loi/vong_lap.py:117`

```python
db.query(ForeachMuc).filter_by(vong_id=vong.id).all()
```

tải **toàn bảng** rồi bỏ `xong` bằng Python ở dòng 211. **Cái suy biến trước tiên là số hàng ORM
nạp mỗi tick** (băng thông CSDL + CPU app), không phải số job hay số câu SQL.

Trần cứng hôm nay (`max_items` ≤ 1000) đã mất **~32 giây bookkeeping thuần** cho MỘT run ở P=8.

⚠️ **Phép đo KHÔNG trả lời:** độ trễ job thật (gọi `jobs.complete` đồng bộ ⇒ 31,67 s là **cận
dưới**) · nhiều run lớn chạy đồng thời · thân có nhiều hơn một node.

## Việc 2 — đếm job đồng thời, **có đối chứng**

Đếm `Job.status IN (queued, running)` ngay sau mỗi tick, trước khi worker giả hoàn tất.

| trần khai (P) | N | max đo được | mẫu theo tick |
|---|---|---|---|
| 4 | 40 | **4** | [4,4,4,4,4,4,4,4,4,4,0] |
| 12 | 40 | **12** | [12,12,12,4,0] |

**Đối chứng:** trần cao hơn cho số đếm cao hơn (12 > 4) ⇒ phép đếm thật sự phản ánh `parallelism`,
không phải đang đo một thứ luôn thấp bất kể trần. Tổng mẫu khớp N.

⚠️ **KHÔNG trả lời:** độ chồng lấp thời gian thực của nhiều worker thật — đây là phép kiểm **logic
nhận job** (`dang_cho >= tran_song_song: break`), không phải đo song song thật.

## Đề nghị (làn p3b **không sửa** — tệp thuộc làn p4)

Lọc `xong=false` **ở SQL** (như `foreach.chi_so_chua_xong` đã làm) thay vì tải cả bảng mỗi tick.

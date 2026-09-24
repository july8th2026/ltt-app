# Làn cache-lease — một tính, các bên kia chờ

Ngày 22/09/2026 · nhánh `phien/asv-final-cache-lease` · test `tests/test_2080_asv_cache_lease.py`.

Tiếp nối `docs/auto_scan_video_v6/PHA25_CACHE_CHUNG.md` §5. Trước làn này, hai lần chạy
cùng khách, cùng video nộp **cùng lúc** đều gọi engine. Lần sau chỉ được dùng cache khi
lần trước đã xong.

## 1. Cơ chế — dùng lại hạ tầng nền tảng, không có khoá thứ hai

| mảnh | dùng lại | ở đâu |
|---|---|---|
| độc quyền tính | `platform_core.leases` (bảng `singleton_leases`: giành bằng INSERT + UNIQUE, hết hạn theo nhịp) | `cache_chung.giu_cho` |
| chờ mà không giữ worker | `platform_core.jobs.DangBan` → `job_runner._provider_failure_kind` = `resource_wait` → `jobs.defer_resource` | `thi_hanh.chay_giai_doan` |
| đập nhịp | luồng daemon, cùng mẫu với lease GPU (`job_runner` `_nhip`) | `cache_chung.GiuCho` |

**Không sửa `platform_core/`.** API hiện có đủ dùng. `leases.heartbeat/release` chỉ đọc
`name` và `holder`, nên `GiuCho` truyền vào một `SingletonLease` tạm, không gắn session.

Luồng trong `chay_giai_doan`, sau khi `cache_chung.lay` trượt (chỉ ở `attempt ≤ 1`, có `khoa_chung`):

1. `giu_cho(kc)` giành lease `asvcc:<58 hex đầu của khoá>`. `name` là cột String(64).
   Mọi thao tác lease đi trong **session riêng**, không commit hay rollback session của giai đoạn.
2. Nếu run khác đang giữ lease thì hàm ném `DangBan(retry_after_s=15)`. Nhánh `except DangBan`
   rollback rồi ném lại. Dòng `asv_stage` giữ nguyên `queued/running` và `job_id`, không bị
   đánh hỏng, không qua `loi.dich_sang_loi_nen_tang`. Worker trả job về `queued` và đẩy lùi
   `next_run_at`. `attempts` không đổi, sổ tiền không bị chạm. Điều phối viên không nộp job mới.
3. Nếu giành được thì **hỏi lại** `lay`: bên kia có thể đã công bố xong và nhả lease giữa
   lần hỏi đầu và lúc giành.
4. Tính, promote, `commit`, rồi `finally: giu.nha()`. Lease chỉ được nhả **sau** khi kết quả
   đã bền, nên bên chờ quay lại là thấy ngay.

Bên chờ quay lại theo nhịp ~15 s. Mỗi lượt chỉ tốn một lần claim và vài câu SELECT. Nếu job có
khai GPU thì nó giữ card trong phần giây đó, không giữ trong lúc chờ.

## 2. Hỏng, chết, huỷ — không bế tắc

| tình huống | lease được nhả thế nào | bên chờ |
|---|---|---|
| engine A ném lỗi, QC chặn, `JobCancelled` | `finally` nhả ngay | tự tính ở lượt kế |
| tiến trình A bị kill hoặc mất điện | luồng nhịp chết theo tiến trình; lease hết hạn sau `TTL_GIU_CHO` = 2 phút | thu hồi (`reclaim_expired`) rồi tự tính |
| A bị huỷ nhưng engine chưa chịu dừng | luồng nhịp hỏi `ctx.is_cancelled()` mỗi `NHIP_GIU_CHO_S` = 30 s; đã huỷ thì thôi đập nhịp | nhận lease sau TTL |
| handler A treo mà tiến trình vẫn sống | ngừng đập nhịp sau `GIU_CHO_TOI_DA_S` = 2 giờ | nhận lease sau TTL |
| hạ tầng lease lỗi (DB) | `giu_cho` trả None, tức tính không có lease | vẫn đúng, chỉ tính hai lần |

⚠️ Lease là **tối ưu hoá, không phải chốt đúng sai**. Kết quả vẫn phải qua `lay`, nơi chủ sở hữu
nằm trong WHERE và từng artifact được kiểm toàn vẹn. Mất lease giữa chừng chỉ khiến hai bên
cùng tính: tốn công nhưng không ra kết quả sai. Vì vậy mọi nhánh lỗi đều rơi về phía **tính**.

## 3. Khoá và chủ sở hữu

Lease dùng đúng `khoa_chung` đã có. Khoá này là sha256 của: phiên bản cache, **owner**, giai đoạn,
hợp đồng, `phien_ban_engine`, checksum của đúng tệp giai đoạn đọc (nguồn hoặc bản 16 kHz), và
đúng các thiết lập giai đoạn đọc (`ngon_ngu_nguon`, `ngon_ngu_dich`, `MODEL_ASR`). Vì owner nằm
trong khoá, hai khách khác nhau có hai lease khác nhau. Không ai phải chờ ai, và thời gian phản
hồi không để lộ việc người kia có cùng tệp (I19).

## 4. Giai đoạn nào được bật

Cơ chế mang tính **chung**: giai đoạn nào có `khoa(...)` khác rỗng thì tự có lease. Muốn bật cho
một giai đoạn, thêm nó vào `GIAI_DOAN_CHUNG` và `dau_vao_noi_dung`. Sau đó `test_478` chốt tập
thiết lập bằng AST.

| giai đoạn | bật? | vì sao |
|---|---|---|
| `audio_prepare` (demucs) | có | chỉ đọc checksum nguồn |
| `transcribe` (ASR) | có | tệp 16 kHz + ngôn ngữ + model |
| OCR / định tuyến nguồn chữ | **không** | chưa có giai đoạn OCR trong `pipeline.CHUOI`. Khi có, chỉ bật sau khi liệt kê đủ đầu vào (khung, vùng, model, ngôn ngữ) và có phép kiểm AST |
| `qc`, `qc_ai` | **không** | chúng chấm **bản kết xuất của chính run**, nên không có hai run trùng đầu vào |
| `edit_plan` trở xuống | **không** | phụ thuộc thiết lập riêng của từng run |

## 5. Bằng chứng — `tests/test_2080_asv_cache_lease.py` (10 xanh, 1 skip)

Tính đồng thời được dựng **tất định**: engine giả của A gọi `chay_giai_doan` của B ngay trong lúc
A đang tính, qua CSDL SQLite tệp thật.

- Hai run đồng thời, cùng khách (chạy cho `audio_prepare` và `transcribe`): engine được gọi
  **1** lần. B nhận `DangBan`, kiểu lỗi là `resource_wait`, dòng stage của B không đổi.
  Lượt sau B dùng lại, với `tu_cache_chung=True`.
- Bên kia công bố giữa lúc B hỏi và lúc B giành: B hỏi lại và không tính.
- Khách khác chạy đồng thời: tính **2** lần, không chờ.
- A hỏng: lease được nhả ngay, B tự tính.
- A chết, lease mồ côi: B chờ (`DangBan`), sau TTL thì thu hồi và tự tính.
- A bị huỷ (`JobCancelled`): lease được nhả, B không kẹt. Khi chủ đã huỷ, luồng nhịp tự dừng.
- 8 luồng tranh cùng một khoá trên SQLite: đúng 1 thắng, 7 chờ.
- Bản PostgreSQL của phép tranh 8 luồng: **skip**, vì máy chưa đặt `LTT_TEST_DATABASE_URL`.
  Phép này sẽ chạy khi có CSDL scratch.

**Đối chứng bằng tiêm lỗi** (sửa mã, chạy, trả nguyên byte). Cả 5 lần tiêm đều làm test đỏ:
bỏ lease (6 đỏ), bỏ bước hỏi lại (1), bỏ nhả lease (6), để `DangBan` rơi vào nhánh đánh hỏng (2),
bỏ kiểm huỷ trong luồng nhịp (1).

## 6. Chưa làm / cần điều phối biết

- Chưa chạy thật qua `job_runner._chay_mot_job` với worker thật. Chuỗi
  `DangBan → resource_wait → defer_resource` là mã nền tảng đã có test riêng, test ở đây khẳng định
  đầu vào của chuỗi đó.
- `defer_resource` ghi sự kiện `resource_wait` với thông điệp khách "Đang chờ tài nguyên xử lý."
  Không có thông điệp riêng cho trường hợp "đang dùng lại kết quả lần chạy khác".
- `tests/test_453` đỏ sẵn trên nền nhánh, không do làn này: `la_tien_trinh_con` ở
  `apps/asv_gpu/do_luong/venv.py`, từ commit e84b22a2.

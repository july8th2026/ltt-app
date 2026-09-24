# Làn tai-len — tải lên tiếp tục được sau khi đứt (asv-final)

> Nhánh `phien/asv-final-tai-len`. Test mới: `test_2090`–`test_2092`.
> Mục tiêu: tệp 2 GB đứt ở 73% thì chạy tiếp từ ~73%, không từ 0%.

## 1. Hiện trạng trước làn này

- `/auto-scan-video/ve` cấp **một** presigned PUT cho cả tệp (`features.tao_ve_tai_len`,
  V6 pha 08). Đứt ở 73% thì gửi lại từ 0%. "Thử lại 3 lần" nghĩa là ba lần gửi lại từ 0%.
- Kho cục bộ (dev/test) không cấp presigned ⇒ `{"mode":"local"}` ⇒ đi form multipart,
  trần 90 MB. Luồng tải lớn **không chạy được ở dev**.

## 2. Tra "dùng lại trước"

| Nơi | Có gì | Kết luận |
|---|---|---|
| `apps/autosubvideo /upload-url`, `taoclipngan`, `taovideo`, `prompt_ai_ommi` | presigned PUT **một lệnh** (`storage.put_url`) | cùng vấn đề, không tiếp tục được |
| `platform_core/storage.py` | không có API multipart (chỉ nhắc trong chú thích) | **phải thêm** |
| `platform_core/upload_sessions.py` | vé theo chủ sở hữu, hạn mức, kiểm magic byte, sweep | **dùng lại nguyên** |
| R2 (developers.cloudflare.com/r2/api/s3/api) | ✅ Create/UploadPart/Complete/Abort/ListParts/ListMultipartUploads; ✅ `Content-MD5` trên UploadPart | chọn S3 multipart |
| R2 multipart-objects | phần ≥ 5 MiB (trừ phần cuối), các phần trừ phần cuối cùng cỡ, ≤ 10 000 phần, lượt dở tự huỷ sau 7 ngày | `CO_PHAN` = 16 MiB cố định |
| tus | cần server tus riêng; tệp đi qua tunnel (trần 100 MB/request vẫn qua được theo phần, nhưng 2 GB chạy qua máy A) | loại: trái với H10 (tệp lớn không qua máy chủ) |
| MD5 trong trình duyệt | WebCrypto không có MD5; noVNC có `md5.js` nhưng là ES module, đổi byte→chuỗi (chậm cho 16 MiB) | vendor **spark-md5 3.0.2** (MIT, npm), sha256 ghi ở `server/static/vendor/spark-md5-3.0.2/NGUON.txt` |

## 3. Thay đổi nền tảng (vì sao và tối thiểu thế nào)

**Vì sao buộc sửa `platform_core/storage.py`:** app không được gọi `boto3` trực tiếp (hợp
đồng đầu tệp storage.py), và `Storage` không có thao tác nào cho phép "hỏi kho phần nào đã
có". Không có API đó thì không có tiếp tục.

Thêm vào `Storage` (mặc định: không hỗ trợ), `LocalStorage`, `R2Storage`, `RoutedStorage`:

```
multipart_supported()                          -> bool
multipart_create(key, content_type)            mở hoặc TÁI DÙNG lượt của key
multipart_part_url(key, n, md5_b64, ttl_s)     R2: presigned UploadPart, content-md5 KÝ vào URL; Local: None
multipart_put_part(key, n, stream, md5_b64, max_bytes)   qua máy chủ; tự kiểm MD5 + trần
multipart_list_parts(key)                      -> [MultipartPart(part_number, size, etag)]
multipart_complete(key, part_count)            thiếu phần -> StorageError
multipart_abort(key)                           -> bool
```

- Định danh bằng **key**, không bằng mã upload: R2 tìm UploadId qua ListMultipartUploads
  (không cache — bộ dọn ở tiến trình worker có thể huỷ bất cứ lúc nào). ⇒ không cột DB mới,
  không migration alembic.
- Local lưu phần ở `<root>/.multipart/<sha256(key)[:32]>/NNNNN.part` + `.md5`; ghép bằng
  ghi tệp tạm rồi `os.replace`. Cùng ngữ nghĩa với R2 để dev/test đi đúng đường production.
- `upload_sessions.sweep`: với phiên PENDING hết hạn, gọi `multipart_abort(key)` trước
  `delete(key)` (qua `getattr` — kho giả trong test không kế thừa `Storage`).

## 4. Luồng ASV

`apps/auto_scan_video/tai_len.py` (nghiệp vụ) + `routes_tai_len.py` (route; `routes.py` có
trần 900 dòng, include ở cuối tệp):

```
POST /auto-scan-video/tai-len                    bắt đầu  -> {upload_id, co, co_phan, so_phan, da_co:[]}
GET  /auto-scan-video/tai-len/{id}               trạng thái -> da_co (phần ĐÚNG cỡ kế hoạch)
POST /auto-scan-video/tai-len/{id}/phan/{n}/ve   vé cho phần n (md5) -> {url, method, headers, co}
PUT  /auto-scan-video/tai-len/{id}/phan/{n}      chỉ kho cục bộ; header Content-MD5 + X-CSRF-Token
POST /auto-scan-video/tai-len/{id}/xong          ghép + upload_sessions.confirm (READY); gọi lại = cùng kết quả
POST /auto-scan-video/tai-len/{id}/huy           huỷ phần ngay, phiên DELETED
```

- Chủ sở hữu: `upload_sessions.owned(user_id, app_slug)` trong truy vấn ⇒ người khác nhận 404.
- CSRF mọi route ghi. Token CSRF chỉ đi kèm vé **cục bộ**, không bao giờ sang R2.
- Hạn trượt 2 h sau mỗi phần (trần 48 h từ lúc tạo) ⇒ lượt bỏ dở hết hạn nhanh, sweep huỷ;
  lượt đang chạy chậm không bị cắt. R2 tự huỷ lượt dở sau 7 ngày là lưới cuối.
- Trần: `TRAN_BYTE = min(2 GiB, 2**31-1)` — xem §6.
- `/tao` giữ nguyên: nhận `upload_id` → `tao_run_tu_ve` (confirm đã READY → soi → promote).
- `/ve` + `features.tao_ve_tai_len` **đã xoá** (đường cũ, không còn người gọi).

Client (`server/static/asv/tai_len.js`, 308/320 dòng): nhớ `upload_id` theo
`name|size|lastModified|type` (localStorage bọc try + bộ nhớ trang); bắt đầu = hỏi trạng thái
trước, chỉ gửi phần còn thiếu; MD5 từng phần bằng spark-md5; thử lại từng phần tối đa 3 lần
trong cùng lượt; hết 3 lần → nút "Thử tải lên lại" (hoặc tải lại trang, chọn lại cùng tệp)
tiếp tục từ phần dở. Thêm chuỗi `tai_tiep_tuc` ("Tiếp tục tải lên từ %(pct)s%…").

## 5. Kiểm chứng

| Tệp | Nội dung | Kết quả |
|---|---|---|
| `test_2090` | storage Local + R2 (moto) + Routed + sweep huỷ lượt dở: tiếp tục sau "tiến trình mới", sha256 khớp, MD5 sai bị từ chối, vượt trần, ghép thiếu phần, huỷ; vé R2 ký `content-md5` | 16 passed |
| `test_2091` | HTTP thật: đứt ở 8/11 phần (73%) → trạng thái trả 1..8 → gửi 9..11 → sha256 khớp; `xong` hai lần; người khác 404 ở cả 5 route; MD5 sai 400 và không tính; sai cỡ 400; ghép thiếu 400; CSRF; số phần ngoài kế hoạch; huỷ dọn phần | 9 passed |
| `test_2092` | bất biến client + vendor sha256 + thứ tự nạp | 6 passed |
| `test_458`, `test_467` | sửa 5 phép kiểm đang chốt đường `/ve` cũ sang đường mới (cùng bất biến) | xem báo cáo |

**Trình duyệt (Playwright, Chromium, máy chủ dev cục bộ `127.0.0.1:8793`, SQLite + LocalStorage
tạm):** MP4 thật 173,1 MB (11 phần). Chặn phần 9 bằng `route.abort("internetdisconnected")`:

```
lần 1: PUT 1..8 xong, PUT 9 ×3 hỏng -> "Tải lên bị gián đoạn…" + nút thử lại, thanh 73%
tải lại trang, chọn lại cùng tệp:
lần 2: data-tiep-tuc-tu=73, "Tiếp tục tải lên từ 73%…", PUT chỉ 9,10,11 -> /xong -> nộp form
       -> /auto-scan-video/run/asvr_… (tạo lần chạy thật)
console: chỉ 3 lỗi ERR_INTERNET_DISCONNECTED cố ý; request hỏng ngoài đó: blob preview (có từ trước)
```

## 6. Quyết định tự chốt / việc còn lại

1. **Chưa kiểm trên R2 thật** (không được đụng bucket production). Phần R2 kiểm bằng moto;
   moto **không** kiểm `Content-MD5` trên UploadPart, nên phép "R2 từ chối thân sai MD5" dựa
   trên tài liệu R2 (✅ Content-MD5). Cần một lượt E2E trên `app.lttstudios.com` sau deploy.
2. **CORS bucket**: trình duyệt PUT thẳng lên R2 cần `Content-MD5` trong AllowedHeaders
   (luật đã ghi `Headers=[*]` ở `docs/KE_HOACH_TON_DONG.md` 4.1b → đủ). Không cần
   `ExposeHeaders: ETag` (ghép lấy ETag từ ListParts). ASV (trước và sau làn này) **không**
   xét cờ `LTT_R2_BROWSER_UPLOAD_ENABLED` như autosubvideo — điều phối nên quyết có nên.
3. **Lỗi tiềm ẩn đã chặn**: `upload_sessions.expected_size` là `Integer` (int4 trên
   PostgreSQL) mà `TRAN_BEN_VUNG` = 2 GiB = 2**31 — tệp đúng 2 GiB sẽ `DataError` 500. Kẹp ở
   `tai_len.TRAN_BYTE`; giao diện vẫn hiển thị 2048 MB. Sửa gốc (BigInteger + migration)
   để cho làn nền tảng.
4. Tải tuần tự từng phần (không song song) — giữ mã nhỏ; thông lượng một luồng lên R2 đủ.
5. `MAX_ACTIVE_BYTES` 2 GiB/khách: một lượt 2 GB bỏ dở chặn lượt mới tới khi hết hạn trượt
   (≤ 2 h) hoặc khách chọn lại cùng tệp (tiếp tục). Chưa có nút "huỷ" trên giao diện — route
   `/huy` đã có.

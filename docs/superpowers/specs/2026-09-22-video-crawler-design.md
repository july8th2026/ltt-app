# Video Crawler ("CÀO NGAY") — Design Spec v1.1

> v1.0 22/09 00:05 (LTTCODE, đã được chủ dự án chốt hướng: "triển khai theo đề xuất" 22/09 00:09 = Approach B).
> v1.1 22/09 (Claude Code tiếp quản): giữ hướng, sửa sai và bổ sung đủ 29 mục §V của SUPER PROMPT.
> Sai đã sửa so với v1.0: (1) registry KHÔNG đặt trong `platform_core/registry.py` (trái luật 9 / AGENTS §8.4) mà trong app;
> (2) yt-dlp là **The Unlicense**, không phải GPL-3.0; (3) bỏ "L3 mỗi phase" — nhịp gate theo hợp đồng §4;
> (4) job model viết theo API thật (`ARCHITECTURE_MAP.md`), không tự đặt cột; (5) audit Viral làm lại có bằng chứng.
> Phản biện độc lập 22/09 (10 điểm, 2 BLOCKER) đã áp vào §8, §12, §13, §14, §18, §21, §26.
> Donor `D:\Viral` @ `368f8be` · LTT `main` @ `e94dd9a2`.

Tài liệu chứng cứ (một nguồn mỗi thứ, spec này không chép lại bảng):
`docs/migrations/video_crawler/` — `AUDIT_VIRAL_CAO_NGAY.md` · `PLATFORM_MATRIX.md` · `ARCHITECTURE_MAP.md` ·
`LICENSE_PROVENANCE.md` · `CODE_REUSE_MATRIX.md` · (sau) `FEATURE_PARITY.md`, `MIGRATION_TRACEABILITY.md`.

## 1. Problem statement
"Cào ngay" của ViralCrawl là công cụ desktop một người dùng: một lượt cào mỗi lúc (`_proc`/`_dang_cao`), tiến độ đọc từ log,
lịch sử jsonl, bốn sổ chống trùng lệch nhau, profile trình duyệt chung máy, và phụ thuộc MediaCrawler (giấy phép cấm thương mại).
Cần một app native trong LTTSTUDIOSAPP làm cùng việc: DISCOVERY + RESOLVE + SELECT/FILTER + QUEUE + DOWNLOAD + METADATA + DEDUP +
PROGRESS + HISTORY, cho nhiều người dùng, nhiều worker, bền trên Postgres. Output là tệp trong LTT Storage, làm đầu vào cho chuỗi LTT.

## 2. Current Viral architecture
Xem `AUDIT_VIRAL_CAO_NGAY.md` §0–§8. Tóm tắt: HTTP server thuần (`W:27`). Ba bộ tải chạy tiến trình con:
yt-dlp cho yt/tt/tw/ig/fb/bilitv, `tai_honggo.py`, MediaCrawler cho dy/bili/xhs/ks/wb. State toàn cục: `_proc`, `_crawl_kq`,
`_tien_do_cao`, `_tasks`. Dừng bằng `taskkill /F /T`.

## 3. Current LTT architecture (điểm ghép)
Xem `ARCHITECTURE_MAP.md`. Các điểm dùng:
- Nộp job: `job_submit.submit_with_credit` + `dedupe_key_for`.
- Handler `handle(params, ctx)`, có `ctx.progress/event/is_cancelled`.
- Lỗi: `jobs.LoiNguoiGoi` = không retry + hoàn tiền; exception khác = retry có giãn cách.
- Trang job sẵn có: `/jobs/{id}`, `/jobs/{id}/progress`, `/jobs/{id}/artifacts/{i}` (tải mọi khoá `*_key`/`*_keys`, đã kiểm chủ).
- Storage: `get_storage().put`. Năng lực worker qua `LTT_WORKER_POOLS`. `secretbox` cho mã hoá.

## 4. Feature parity matrix
Liệt kê khối UI và endpoint donor ở `AUDIT_VIRAL_CAO_NGAY.md` §1–§2. Bảng parity có trạng thái đo được sẽ lập ở S8
(`FEATURE_PARITY.md`); chỉ đánh ✅ khi có test hoặc nghiệm thu trình duyệt trỏ tới. Phạm vi release đầu:

| Khối donor | Release 1 (slice 1) | Sau |
|---|---|---|
| Chọn nền, 4 cách cào (từ khoá/link/kênh/bộ), số lượng | ✅ YouTube | nền khác S6–S7 |
| Xem trước & chọn · Cào hết · Thêm hàng đợi · Huỷ | ✅ | |
| Cào không trùng | ✅ (scope user) | |
| Tiến độ thật, nhật ký hoạt động (timeline job) | ✅ | |
| Thống kê (hôm nay/đang chạy/xong/lỗi) | ✅ đếm job thật | |
| Sort / time filter / language | ⏸ Donor chỉ MediaCrawler đọc (`W:4592-4593`); YouTube không dùng | S6 (Douyin) |
| Đăng nhập nền tảng / cookie | ⏸ YouTube ẩn danh | S6 |

## 5. Platform capability matrix
Sự thật donor: `PLATFORM_MATRIX.md`. Registry đích (§12) chỉ bật nền đã có adapter + test. Release 1: `youtube`.

## 6. Source-code reuse matrix
`CODE_REUSE_MATRIX.md`.

## 7. License / provenance matrix
`LICENSE_PROVENANCE.md`. Chốt: không copy MediaCrawler. yt-dlp dùng làm thư viện. Không tải mã EJS từ GitHub lúc chạy.

## 8. Target architecture (Approach B, kiểm chứng với hợp đồng LTT)
```
UI Jinja+HTMX (apps/video_crawler/templates)            ← capability-driven từ nen_tang.py
   │  routes.py (CHỈ HTTP: login, CSRF, validate qua features)
   ▼
features.py = CrawlApplicationService  (validate theo registry, dựng params, dedup, thống kê, lịch sử)
   │  job_submit.submit_with_credit
   ▼
LTT jobs (Postgres)  ──claim theo requires──►  worker lane
   │                                              ▼
   │                                   jobs.py handle() → adapters/<nền>.py (PlatformAdapter)
   │                                              ▼
   │                                   chuẩn hoá → CrawlItem → storage.put("video_crawler/<owner>/<job>/<id>.mp4")
   ▼
job.result {"muc": [...], "video_keys": [...]}  → /jobs/{id}/artifacts/{i} (tải về, đã kiểm chủ)
```
**Executor boundary:** `requires` khai theo APP, không theo job type (`registry.py:569-576`). Tiền lệ LTT cho "executor ẩn theo
năng lực" là app anh em `surface="runtime"` + `catalog_parent` (`apps/asv_media`, `asv_gpu`, `asv_voice` của Auto Scan Video).
- Slice 1: MỘT app `video_crawler`, `requires=("api",)` + `max_runtime_s={"video_crawler.tai": 7200}`.
  ⚠ Không dùng `("ffmpeg",)`: production `LTT_WORKER_POOLS=api:6, gpu+ffmpeg:1, voice:1` ⇒ app ffmpeg chỉ được làn
  `gpu+ffmpeg` duy nhất nhận, xếp sau job GPU 2 giờ (`jobs.py:245-250`). ffmpeg vẫn có trên máy A; `requires` chỉ là lịch.
- Slice 2 (browser): cần executor `requires=("browser",)` ⇒ thêm thư mục app runtime anh em `apps/video_crawler_browser/`
  theo tiền lệ ASV. **Đây là quyết định cần chủ dự án chốt ở S6** (chỉ đạo "thêm app = MỘT thư mục").
  Không sửa `platform_core`.

## 9. App boundary
Chỉ `apps/video_crawler/**`, `tests/test_19xx_video_crawler_*.py`, `docs/**`. Import `server` chỉ 4 module (AGENTS §8.2b).
Không import app khác (`APP_DUOC_DUNG_APP`). Không `create_all`. Slice 1 **không tạo bảng mới**, vì bảng mới buộc sửa
`platform_core/public_api/governance.py` (test_211).

## 10. Executor/worker boundary
Handler chạy trong worker, không bao giờ trong request. Route chỉ nộp job và đọc DB. Không thread riêng, không subprocess
yt-dlp (dùng Python API). Browser automation không chạy trên web request (S6).

## 11. PlatformAdapter contract (`apps/video_crawler/adapters/base.py`)
```python
class PlatformAdapter(Protocol):
    nen_tang: str                                    # id trong registry
    def kham_pha(self, yeu_cau: YeuCauCao, *, bao_tien_do) -> list[CrawlItem]   # search/link/kênh/bộ → danh sách (không tải)
    def tai(self, item: CrawlItem, thu_muc: Path, *, bao_tien_do) -> TepTai       # tải MỘT mục, ném LoiCao khi hỏng
```
- Capability không hỗ trợ được mô tả trong registry. UI/validate chặn trước, adapter không phải ném "unsupported".
- `check_session/login/healthcheck`: thêm ở S6 khi có nền cần login (YAGNI).
- `bao_tien_do(phan_tram: int, thong_diep: str)`: nơi duy nhất nối tới `ctx.progress` và kiểm huỷ.

## 12. CapabilityRegistry (`apps/video_crawler/nen_tang.py`, một nguồn chân lý)
```python
@dataclass(frozen=True)
class NenTang:
    id: str; ten: str; icon: str; bat: bool
    che_do: frozenset[str]            # {"tu_khoa","link","kenh","bo"}
    xem_truoc: bool; can_dang_nhap: bool; cach_dang_nhap: str   # "" | "qr" | "cookie"
    ten_mien: tuple[str, ...]         # nhận diện link (port từ _LINK_DOM H:16748)
    so_luong_toi_da: int
    adapter: str                      # tên module trong adapters/
    gioi_han: tuple[str, ...]         # chú thích hiển thị
```
Validate backend, dựng form UI, nút login và chọn adapter đều đọc registry này.
Manifest phải khai `capabilities` không rỗng (app customer không có `catalog_parent`, `test_60:62-72`). Thêm một nền = một dòng registry + một adapter.

## 13. Domain / data model

| Khái niệm | Hiện thực | Lý do |
|---|---|---|
| CrawlRequest | `Job` (`video_crawler.kham_pha` / `video_crawler.tai`), `params` | Có sẵn: owner, trạng thái, retry, huỷ, events |
| CrawlItem | DTO `CrawlItem` (id, url, tieu_de, tac_gia, thoi_luong_s, anh_bia, nen_tang) — lưu trong `job.result["muc"]` | Không cần bảng ở slice 1 |
| CrawlAsset | Storage key `video_crawler/<owner_id>/<job_id>/<id>.mp4` + `result["video_keys"]` | Tải về qua `/jobs/{id}/artifacts` |
| CrawlDedupRecord | Slice 1: suy ra từ job `video_crawler.tai` đã xong của cùng owner (`result["muc"][*].id`), lọc trong Python (`result` là JSON, không JSONB — `models.py:296`). ⚠ `jobs.result` bị xoá sau 30 ngày (`governance.py:307`, `job_content.py:103`) ⇒ "không trùng" chỉ nhớ **30 ngày**, ghi rõ trên UI. Bền vĩnh viễn + chặn hai job song song tải cùng video cần bảng `vc_da_tai` ⇒ **CONTRACT GAP-1** (một hàng `governance.STORES`) trình chủ dự án | Một nguồn: kết quả thật, không đánh dấu trước khi tải xong (sửa lỗi donor `W:7228`) |
| CrawlPlatformSession | S6: bảng app `vc_phien` (cookie mã hoá `secretbox`) + governance row ⇒ CONTRACT GAP có chủ đích | |
| CrawlSource (thư viện nguồn) | DEFER S8 | |

Rủi ro đã biết: dedup quét job cũ của user, chi phí tăng theo lịch sử. Giới hạn N job gần nhất; có bảng ở S8 nếu cần đo.

## 14. Job model

| job_type | params (đã validate ở features) | result |
|---|---|---|
| `video_crawler.kham_pha` | `owner_id, nen_tang, che_do, dau_vao, so_luong, khong_trung` | `{"muc": [CrawlItem...], "bo_qua_trung": n}` — miễn phí |
| `video_crawler.tai` | `owner_id, nen_tang, muc: [{id,url,tieu_de}]` (từ xem trước) **hoặc** `nguon: {che_do, dau_vao, so_luong, khong_trung}` (cào hết) | `{"muc": [...+key,size], "video_keys": [...], "loi": [{id, ma, thong_diep}], "bo_qua_trung": n}` |

Nộp bằng `submit_with_credit(..., dedupe_key=dedupe_key_for(...), max_attempts=2)`.
Trần `so_luong` ≤ 20: `/jobs/{id}/artifacts` chỉ liệt kê 20 tệp (`server/routes/jobs.py:39,45`). Trường của mục trong `muc`
không được kết thúc bằng `_key` (nếu không, nó bị coi là tệp tải về và chiếm chỗ trong trần 20). Giá: `kham_pha` = 0;
`tai` = 1 credit × số mục tối đa (giữ chỗ), quyết toán theo số tải được (`result["credit_cost"]`).
**Giá là quyết định sản phẩm — chờ chủ dự án xác nhận trước khi `lifecycle="released"`.**

## 15. Storage / media model
Worker tải vào `tempfile.TemporaryDirectory()`, rồi `get_storage().put(key, f, "video/mp4")`, rồi xoá tạm.
Media handoff sang Auto Scan Video: ASV chỉ nhận `upload_id` của chính nó hoặc multipart (`ARCHITECTURE_MAP` §5).
Không import được app kia ⇒ **CONTRACT GAP (S5)**, trình chủ dự án kèm phương án:
(a) worker tạo `upload_sessions` cho `app_slug="auto_scan_video"`; (b) bổ sung hợp đồng "media asset" ở `platform_core`;
(c) khai cạnh `video_crawler → auto_scan_video` với một bề mặt công khai. Slice 1 dừng ở "tải về".

## 16. Session / login model
S6. Nguyên tắc cứng: profile/cookie theo `(owner_id, nền, tài khoản)`, mã hoá bằng `secretbox`, không vào params/log/URL.
Job browser nhận tham chiếu phiên, không nhận cookie. Không dùng profile chung.

## 17. Dedup model
Hai tầng khác nhau, không trộn:
1. Chống nộp trùng khi job đang chạy: `dedupe_key_for(job_type, params)` (nền tảng).
2. "Cào không trùng": khoá `(owner_id, nen_tang, video_id)`. `video_id` = `info["id"]` của extractor (donor `Y:1930`).
   Chỉ tính mục đã tải xong. Scope = user (một user không ảnh hưởng user khác).

## 18. Cancel / retry model
Huỷ: `POST /jobs/{id}/cancel` của nền tảng (kiểm chủ, hoàn tiền). Handler dừng hợp tác:
- Trong hook yt-dlp phải ném **lớp con của `yt_dlp.utils.DownloadCancelled`**, và đặt `ignoreerrors=False`.
  yt-dlp chỉ ném lại `DownloadCancelled`/`CookieLoadError`; exception khác bị nuốt khi `ignoreerrors` bật
  (`yt_dlp/YoutubeDL.py:1699,1717-1719`). Donor bật `ignoreerrors` (`Y:2023`) — **không** chép.
- Giữa các mục: kiểm `ctx.is_cancelled()`.
- Hook tải và `postprocessor_hooks` (bước ghép ffmpeg không có progress hook) phải gọi `ctx.progress` ít nhất mỗi 60 s
  (ngưỡng mồ côi 5 phút).
- Job kết thúc bằng huỷ hoặc lỗi cuối ⇒ xoá tiền tố `video_crawler/<owner>/<job>/`. Việc dọn job hết hạn chỉ quét `result`
  (`job_content.py:51-74`), nên tệp đã lưu mà chưa vào `result` sẽ mồ côi. Retry: `max_attempts=2`. Lỗi của khách không retry. Mục đã tải lưu dần; lượt thử lại bỏ qua mục có key.

## 19. Error model (`apps/video_crawler/loi.py`, port bảng `W:4897-5005`)

| Mã | Tín hiệu yt-dlp | Loại |
|---|---|---|
| `rieng_tu` | private / sign in to view / members-only | LoiNguoiGoi |
| `khong_ton_tai` | unavailable / removed / 404 | LoiNguoiGoi |
| `url_khong_ho_tro` | Unsupported URL / sai nền | LoiNguoiGoi |
| `gioi_han_tuoi` | age | LoiNguoiGoi |
| `yt_bot` | Sign in to confirm / not a bot | retry (tạm thời) |
| `yt_403` | HTTP 403 / unable to download video data | retry |
| `mang` | timeout / connection reset | retry |
| `chi_la_anh` | No video formats found | ghi vào `loi`, không tính lỗi job |

Job nhiều mục: có ≥ 1 mục tải được ⇒ hoàn tất, ghi `loi`. 0 mục ⇒ ném lỗi đại diện (hoàn tiền). Sửa lỗi donor: không đánh "xong" với 0 video (`W:11652`).
Thông điệp khách lấy từ bảng này; chi tiết thô chỉ ở event `internal` (đã qua `redact_details`).

## 20. Progress / events
`ctx.progress(%)` tính theo `(mục_xong + phần_mục_hiện_tại) / tổng`. Mốc `ctx.stage`: `kham_pha`, `tai`, `luu`.
Event customer: `muc_xong`, `muc_loi`, `bo_qua_trung`. UI poll `/jobs/{id}/progress` của nền tảng. Không progress giả.

## 21. Security
- URL: chỉ http(s); host phải thuộc `ten_mien` của nền (allowlist). Chặn IP literal nội bộ (port donor `Y:1608-1626`).
  LTT siết thêm (donor KHÔNG làm): phân giải tên miền và chặn nếu ra IP nội bộ. `enable_file_urls=False`.
- yt-dlp: `allowed_extractors` chỉ gồm extractor của nền (không `generic`). Không nhận `cookiefile`, `outtmpl`, `exec`, `netrc`
  từ người dùng; `outtmpl` do app đặt. Không `remote_components`. **Không** chép `nocheckcertificate: True` của donor (`Y:2024`).
- `kham_pha` miễn phí nhưng giới hạn tần suất theo user, vì tìm kiếm dồn dập từ IP máy A đẩy YouTube vào bot-check.
- Owner scope: mọi truy vấn lọc `Job.user_id == u.id`; `owner_id` lấy từ phiên, không từ form.
- CSRF trên mọi POST. Giới hạn `so_luong` theo registry. Kích thước tệp tối đa (cấu hình trong app).
- Không log URL có token/cookie.

## 22. UI information architecture
Một trang `/video-crawler`:
1. Thống kê (hôm nay / đang chạy / xong / lỗi — đếm job thật).
2. Lưới chọn nền (sinh từ registry; nền `bat=False` ẩn).
3. Cách cào (chỉ hiện chế độ nền hỗ trợ).
4. Ô nhập, số lượng, "không trùng".
5. Nút: 👁 Xem trước · 🚀 Cào hết · 📋 Thêm hàng đợi.
6. Kết quả xem trước (chọn mục → tải).
7. Hàng đợi của tôi: job đang chạy/xong, tiến độ, huỷ, tải về.

Component hoá bằng partial Jinja; HTMX để poll. Responsive. Không copy `index.html`.

## 23. Pipeline integration
Release 1: tải tệp về. Nối Auto Scan Video theo quyết định CONTRACT GAP §15.

## 24. Testing strategy
- Tệp `tests/test_1900..1919_video_crawler_*.py`. Chạy nhắm theo `thanh_phan.py --test app:video_crawler`.
- Unit/characterization (không mạng): nhận diện nền, đoán chế độ, chuẩn hoá kênh, SSRF, bảng lỗi, dựng tuỳ chọn yt-dlp.
  Adapter test dùng fake `YoutubeDL` trả info-dict. Characterization chỉ lấy từ donor; không có ca "vì mã mới làm thế".
- Integration (sqlite, `_chay_mot_job`): nộp → claim → handler → storage → result → artifacts, huỷ giữa chừng, retry, dedup, owner scope.
- Web: TestClient đăng nhập + CSRF. Trình duyệt: Playwright local, rồi `app.lttstudios.com` sau deploy.
- Mạng thật: một smoke thủ công (không vào bộ test), ghi bằng chứng.
- Gate: test nhắm; L2 `gate.py --pham-vi app:video_crawler` trước deploy giữa phiên; L3 một lần cuối phiên.

## 25. Migration phases
Plan sống: `docs/superpowers/plans/2026-09-22-video-crawler.md` §C (P0–P3, S1–S8, D1, END).

## 26. Rollback strategy
Mã chỉ nằm trong `apps/video_crawler/`. Slice 1 không có migration DB. Tắt bằng cờ env `LTT_VIDEO_CRAWLER` (route 404, tiền lệ
ASV `_cong_co`), vì `enabled=False` không chặn route hay worker. Cờ bật/tắt cho MỌI user; mở thử cho riêng tài khoản test
thì thêm allowlist trong app. Public API đã bị chặn bởi `enabled=False` (`catalog.py:229`). Gỡ hẳn = xoá thư mục + dọn thư mục ma.

## 27. Risks

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| YouTube bot-check/PO token từ IP datacenter | CAO | tuỳ chọn donor (client `web_embedded`, sleep); đo ở D1 trên máy A |
| EJS cần Node + gói ejs; donor tải mã GitHub lúc chạy | TB | gói pip cố định; xác minh ở S3 |
| Cloudflare/R2 lifecycle tự xoá ~7 ngày | TB | ghi rõ thời hạn giữ tệp trên UI; kiểm ở D1 |
| Douyin client viết lại (MediaCrawler cấm) | CAO | S6 chọn nền theo chi phí; Bilibili dự phòng |
| Executor browser cần app runtime thứ hai | TB | chủ dự án chốt ở S6 |
| Dedup quét job cũ chậm | THẤP | giới hạn, đo |

## 28. Deferred scope
Đăng nhập/cookie; Douyin/Bili/XHS/RedNote/KS/TikTok/FB/IG; Honggo; dịch từ khoá; sort/time filter;
theo dõi kênh/automation/hẹn giờ; thư viện nguồn; nối ASV (chờ quyết định); Reddit/Threads (DROP).

## 29. Definition of Done
Theo SUPER PROMPT §AG. Release 1 xong khi YouTube đi đủ chuỗi §R trên `app.lttstudios.com`: UI → validate → submit → claim →
adapter → download → progress → metadata → storage → history → tải về. Có bằng chứng: test nhắm xanh, L2 xanh đúng SHA deploy,
ảnh chụp/log nghiệm thu, không lộ bí mật, review code độc lập. Toàn bộ migration xong khi mọi nền trong phạm vi đã chốt đạt
parity có bằng chứng và L3 xanh.

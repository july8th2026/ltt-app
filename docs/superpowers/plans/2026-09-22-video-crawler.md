# Video Crawler ("CÀO NGAY") — Plan chuẩn hoá (v2, 22/09/2026)

> Thay plan v1 do LTTCODE soạn trong chat 22/09 00:12 (chưa từng lưu ra đĩa).
> Yêu cầu gốc: SUPER PROMPT (bản lưu `C:\Users\Thang Tuong\.claude\ltt\khoi-phuc-2026-09-22\super-prompt.lttcode.md` dòng 2–1481).
> Spec: `docs/superpowers/specs/2026-09-22-video-crawler-design.md` (v1.0, sẽ nâng v1.1 ở P2).
> Cây: `D:\LTTSTUDIOSAPP-video-crawler`, nhánh `phien/video-crawler`, BASE_SHA `e94dd9a2`. Donor: Viral `368f8be`.
> Trạng thái sống của plan = mục §C (bảng pha) + `docs/migrations/video_crawler/SO_LOI.md` — không chỉ trong hội thoại.

---

## A. Rà soát plan v1 và việc LTTCODE đã làm — từng hạng mục, có bằng chứng

Bằng chứng chung: nhánh `phien/video-crawler-migration` (cây `D:\LTTSTUDIOSAPP-video-crawler-migration`)
**0 commit riêng**, toàn bộ mã ở dạng staged + `??` (247 dòng staged + tệp untracked). Main: 548f9d99 (skeleton ghi thẳng vào
main, message sai) → 79f2a776 (vá, tắt app, thêm spec) → f587f497 (rút mã app). Chạy lại test cây cũ 22/09
(`pytest apps/video_crawler/tests -q`, qua `chay_nang.py`): **3 failed, 5 passed**. Năm test xanh đều là mock hoặc import-only.

| # | Hạng mục plan v1 | LTTCODE báo | Thực tế (bằng chứng) | Đúng quy trình? | Xử lý |
|---|---|---|---|---|---|
| 0 | Preflight + đọc contract | xong | Có làm (SHA e3a30d63 / 368f8be) | ✅ | Giữ; làm lại preflight trên e94dd9a2 (đã xong P0) |
| — | Audit Viral | xong | **Subagent audit chết** (transcript dòng 2662), không có tệp audit nào | ❌ | Làm lại P1 |
| — | License | xong | MediaCrawler NON-COMMERCIAL đúng; **yt-dlp "GPL-3.0" SAI** — thật là The Unlicense (GitHub yt-dlp LICENSE @ c7fb478d) | ⚠️ | Sửa ở LICENSE_PROVENANCE + spec |
| — | Spec | xong | Có trên main nhưng thiếu phần lớn 29 mục §V; đề xuất sửa `platform_core/registry.py`; "mỗi phase có gate riêng" | ⚠️ | Nâng v1.1 ở P2 |
| 01 | Skeleton | ✅ "3 tests PASSED" | `routes.py` gọi `user_hien_tai` không import, trả JSON, không template; `templates` là **tệp 0 byte**, không phải thư mục | ❌ | Viết lại |
| 02 | Registry vào `platform_core/registry.py` | — | Plan **vi phạm** CLAUDE.md luật 9 + AGENTS §8.4; mã thật để `capabilities.py` trong app (2 nền tảng) nhưng không ai dùng | ❌ | Registry nằm TRONG app |
| 03 | Job submission | ✅ | `jobs.py` là wrapper submit (sai vai — `jobs.py` phải là `handle(params, ctx)`); không có handler; không giữ credit; test_04 mock hết | ❌ | Viết lại theo ARCHITECTURE_MAP |
| 04 | YouTube adapter | ✅ | search qua URL `results?search_query=` (không escape); **nuốt mọi exception** → job "thành công" rỗng (trái 03_THEM_APP_MOI §2 quy tắc 3); không download | ❌ | Viết lại, TDD bằng fixture info-dict |
| 05 | Storage | ✅ | dùng `storage.put_url` (vé upload trình duyệt) cho output worker; `core_db.session` không tồn tại; test_06 **đỏ** | ❌ | Viết lại |
| 06 | Preview/dedup | — | Không tồn tại | ❌ | Làm mới |
| 07 | Browser worker review | — | Plan đọc `apps/bot/` — **không tồn tại** | ❌ | Audit thật ở P1 (ARCHITECTURE_MAP §7) |
| 08 | UI | ✅ | Chỉ ghi `echo` vào tệp; không có template thật | ❌ | Làm mới, kiểm trình duyệt |
| 09 | Douyin/Bili/XHS | ✅ | Stub rỗng, `import playwright` cấp module; test_07 **đỏ** | ❌ | Chỉ làm sau slice 1, theo bằng chứng |
| 10 | History | — | `history.get_run_details` **không kiểm chủ sở hữu** (IDOR) | ❌ | Làm lại có owner scope |
| 11 | Multi-user QA | — | Không có | ❌ | Làm mới |
| 12 | Parity report | ✅ | FEATURE_PARITY.md đánh ✅ toàn bộ **không có bằng chứng** | ❌ | Bỏ; lập lại từ PLATFORM_MATRIX |
| 13 | Docs | — | Không có | ❌ | Làm mới |
| 14 | "Public launch" `enabled=True` sau L2 | — | Không làm. Plan thiếu deploy, thiếu nghiệm thu trên `app.lttstudios.com` | ⚠️ | Thay bằng deploy giữa phiên + E2E thật |
| 15 | L3 | — | Không làm | — | Giữ: MỘT lần, tổng kết phiên |

**Lỗi quy trình của plan v1 so với luật hiện hành (CLAUDE.md dự án + toàn cục 19/09):**
1. Gate: spec ghi "L3 end of phase" và "mỗi phase có gate riêng" ⇒ trái §4.2 (L3 chỉ tổng kết phiên).
2. CPU: có nhắc `cua_so_yen`, nhưng thiếu `tai_may.py`, thiếu `chay_nang.py` cho lệnh nặng của agent, không giới hạn `-n ≤ 6`.
3. Agent: định chia 3 subagent song song từ Phase 01 ⇒ song song hoá phần móng khi contract chưa ổn (trái SUPER PROMPT §AC).
   Không có worktree/nhánh riêng cho mỗi làn, không chọn model theo loại việc.
4. Ghi thẳng vào cây main. Không có sổ lỗi/ledger. Tuyên bố "✅ PASSED" khi test đỏ.
5. Thiếu các bước: audit Viral, characterization test, alembic cho bảng app, quyết định giá credit, deploy, kiểm trình duyệt, NHAT_KY.

---

## B. Luật vận hành áp cho plan này (một nguồn: CLAUDE.md dự án + mục ⭐ CLAUDE.md toàn cục)

- **Test/gate**: trong phiên chạy test nhắm (`python tools\thanh_phan.py --test app:video_crawler` → `python -m pytest <tệp> -q`).
  Cần gate thì chỉ L1 (`gate.py --doi`) hoặc L2 (`gate.py --pham-vi app:video_crawler`).
  ⛔ Không L3 giữa các pha. L3 MỘT lần khi mọi pha của phiên xong. L3 đỏ ⇒ sửa tại chỗ → chạy lại đúng phép đỏ → `gate.py --doi --tu <sha L3>`.
- **Deploy giữa phiên**: được làm khi L1/L2 xanh trên đúng SHA → gộp main → deploy → nghiệm thu trên `https://app.lttstudios.com`.
  Báo các phiên đang chạy trước (`ListAgents`), vì deploy xuất HEAD của cây chính.
- **CPU**: trước lệnh nặng (gate, từ 3 tệp test trở lên, build) chạy `python tools\cua_so_yen.py trang-thai` + `python tools\tai_may.py`.
  QUÁ TẢI hoặc có người giữ khoá ⇒ chờ. Lệnh nặng của agent đi qua
  `python "C:\Users\Thang Tuong\.claude\ltt\chay_nang.py" --phien <làn> -- <lệnh>`, `-n ≤ 6`.
- **Agent**: số làn = số việc ĐỘC LẬP. Mỗi làn một worktree + nhánh `phien/video-crawler-<làn>`; không hai làn sửa cùng tệp.
  Việc cơ học (chạy test, kiểm kê, adapter theo khuôn đã khoá) dùng `model: sonnet`; thiết kế và gỡ lỗi khó dùng Opus.
  Brief dán `C:\Users\Thang Tuong\.claude\ltt\QUY_TAC_AGENT_VA_TOKEN.md` mục B. Báo cáo ≤ 250 từ. Điều phối review rồi tự gộp.
  ⛔ Không song song hoá phần móng (S1–S2) trước khi contract khoá.
- **Mã**: chỉ trong `apps/video_crawler/` (+ `docs/`, test). Buộc sửa `platform_core/`/`server/` ⇒ lập **CONTRACT GAP**
  (Requirement / Current contract / Why impossible / Minimal change / Affected apps / Compatibility / Tests / Risk) và trình chủ dự án.
- **git**: `git add` tường minh. Dòng `??` lạ là của phiên khác. Không stash/reset/checkout. Ghi tệp không BOM.
- **Bí mật**: cookie/token không vào log, payload, URL, git, docs, frontend.
- **Báo mỗi pha**: PHASE / STATUS / EVIDENCE (lệnh, pass/fail, tệp, SHA) / PARITY GAIN / OPEN FINDINGS / RISKS / NEXT.

---

## C. Bảng pha (trạng thái sống)

| Pha | Nội dung | Làn / agent | Kiểm | Trạng thái |
|---|---|---|---|---|
| P0 | Preflight e94dd9a2, worktree mới, bàn giao | điều phối | — | ✅ 22/09 |
| P1 | Audit: Viral (AUDIT_VIRAL_CAO_NGAY.md, PLATFORM_MATRIX.md) ‖ LTT (ARCHITECTURE_MAP.md) ‖ LICENSE_PROVENANCE.md + CODE_REUSE_MATRIX.md | 2 agent chỉ đọc song song; điều phối kiểm chéo | Mỗi kết luận có tệp:dòng | ✅ `8083d179` (kiểm chéo 4 trích dẫn donor) |
| P2 | Spec v1.1: đủ 29 mục §V, registry trong app, sửa license yt-dlp, mô hình dữ liệu/job/dedup/cancel/lỗi; phản biện bởi reviewer độc lập | điều phối + 1 reviewer (Opus) | self-review + adversarial | ✅ 10 điểm phản biện (2 BLOCKER) đã áp — `3ffea9ae` |
| P3 | Plan task-level cho S1–S5 (exact paths, RED/GREEN, lệnh, commit) — bổ sung vào tệp này §D | điều phối | — | ✅ thay bằng contract khoá `adapters/base.py` + chia làn (tệp tách biệt) |
| S1 | Móng: manifest (tắt, `lifecycle="development"`, `public=False`), registry nền tảng trong app, adapter protocol + DTO, nhận diện URL/nền tảng (characterization theo Viral) | làn A `phien/video-crawler-nen-tang` (sonnet) | test 1900/1901 + test_60 | ✅ `179ccec6` + sửa `ce6f1974` |
| S2 | Chuỗi job: handler discovery + download, bảng app (+ alembic), events/progress thật, cancel theo job/user, dedup scope user, lỗi → exception (hoàn credit), giá credit | điều phối (tuần tự) | test 1904/1905 (chuỗi job thật qua `_chay_mot_job`) | ✅ `1179eff9` |
| S3 | Adapter YouTube (yt-dlp Python API, tuỳ chọn an toàn, fixture info-dict), output vào storage, route tải về có kiểm chủ | làn B `phien/video-crawler-youtube` (Opus) | test 1902/1903 + smoke mạng thật | ✅ `dd80072c` |
| S4 | Route + UI Cào ngay slice 1 (capability-driven, CSRF, poll trạng thái job thật) | điều phối | test 1906 + Playwright dev cô lập (YouTube thật) | ✅ `e4fa4a95`, sửa lỗi GUI `1f356123` |
| S5 | Bàn giao output thành input của Auto Scan Video (theo ARCHITECTURE_MAP §5; có thể là CONTRACT GAP) | điều phối | — | ⏸ CONTRACT GAP-2 (ASV chỉ nhận upload của chính nó) — trình chủ dự án |
| D1 | **Mốc deploy giữa phiên**: L2 xanh đúng SHA → gộp main → deploy → E2E thật trên app.lttstudios.com bằng tài khoản test (khach*.thu) | điều phối | L2 + nghiệm thu §9 | chưa |
| S6 | Slice 2 browser/login (chọn nền tảng theo PLATFORM_MATRIX): định tuyến worker `browser`, session cô lập theo user, QR/login, hết hạn, cancel, dọn browser | 1 làn Opus; CONTRACT GAP nếu cần kho cookie mã hoá | test nhắm + E2E máy residential | chưa |
| S7 | Adapter còn lại (mỗi nền tảng một làn, song song SAU khi S6 khoá interface) | n làn sonnet | test nhắm mỗi làn | chưa |
| S8 | UI parity đủ khối §Q, history/thư viện, multi-user/concurrency QA, security review, parity report thật, MIGRATION_TRACEABILITY, docs | làn theo tệp | test nhắm + trình duyệt | chưa |
| END | L3 MỘT lần → khép nếu đỏ → gộp main → deploy nếu cần → NHAT_KY → báo | điều phối | L3 | chưa |

Điểm dừng hợp lệ (CLAUDE.md luật 2): gate đỏ · thao tác không đảo được · thay đổi không rõ của ai · rủi ro bảo mật · CONTRACT GAP cần chủ dự án.

---

## D. Task-level S1–S5

Đã thi hành (TDD, test viết trước và thấy đỏ). Sổ lỗi + độ phủ: `docs/migrations/video_crawler/SO_LOI.md`.
Test: `tests/test_1900..1906_video_crawler_*.py` (223 phép cùng test_60/211/308/148, qua `chay_nang.py`).

---

## E. "Triển khai full các trang" (chỉ đạo chủ dự án 22/09) — kế hoạch theo đợt

Bằng chứng nền: yt-dlp 2026.03.17 đang cài CÓ extractor cho BiliBili (+ `bilisearch`), BiliIntl, Douyin, TikTok
(+ user/collection/tag), Facebook (+ reel), Instagram (+ user/tag), Twitter, XiaoHongShu, Weibo (+ user/video);
KHÔNG có Kuaishou, Honggo. ⇒ phần lớn nền = adapter mỏng trên `adapters/_ytdlp.py` (không đụng MediaCrawler).

| Đợt | Nền | Chế độ mục tiêu | Cần đăng nhập? | Làn | Trạng thái |
|---|---|---|---|---|---|
| Móng | `adapters/_ytdlp.py` (tách từ youtube) + nhịp tim, lọc live, trần dung lượng, URL chuẩn | — | — | làn `ytdlp` (Opus) | ⏳ |
| A1 | bilibili_tv | link | không | 1 làn sonnet | chờ Móng |
| A2 | tiktok | link, kênh, bộ (tìm từ khoá ⇒ đợt B) | không | 1 làn sonnet | chờ Móng |
| A3 | facebook | link (kênh/Page ⇒ đợt B) | không | 1 làn sonnet | chờ Móng |
| A4 | bilibili (.com) | link, từ khoá (`bilisearch`), kênh (space), bộ (ugc_season) — đo xem ẩn danh được tới đâu | tuỳ đo | 1 làn sonnet | chờ Móng |
| A5 | twitter, instagram, xiaohongshu, weibo, douyin | link — đo ẩn danh; hỏng thì chuyển B | đo | 1 làn / nền (sonnet), smoke thật quyết định | chờ Móng |
| B0 | Phiên đăng nhập theo user: bảng `vc_phien` (cookie mã hoá `secretbox`), nhập cookies.txt trên UI, worker ghi cookiefile TẠM trong thư mục job | — | — | điều phối (Opus) | CONTRACT GAP: 1 hàng `governance.STORES` + alembic |
| B1 | Mở các chế độ cần cookie: tiktok từ khoá, facebook Page, instagram, twitter, douyin/xhs/bilibili khi ẩn danh bị chặn | theo donor | có | mỗi nền 1 làn | sau B0 |
| B2 | QR login (douyin/bilibili/xhs) qua worker `browser` | — | có | app runtime `video_crawler_browser` + làn `browser` trong `LTT_WORKER_POOLS` | chờ chủ dự án bật pool browser |
| C | kuaishou (CAPTCHA, donor ghi "chưa hứa cào ra video"), honggo (CDN chặn IP datacenter) | — | — | đo; không đạt ⇒ DEFER có bằng chứng | sau B |

Registry (`nen_tang.py`) do điều phối sửa khi gộp từng làn (một tệp chung ⇒ không làn nào sửa).
Mỗi nền chỉ bật (`bat=True`) khi có: adapter + test fake + smoke thật ghi vào SO_LOI.md.

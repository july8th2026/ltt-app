# Kế hoạch RÀ SOÁT TOÀN DIỆN từng app (audit + parity + fix bug)

> Lập 2026-08-02. Mục tiêu: soi kỹ TỪNG app đã di trú, đối chiếu tính năng với module
> nguồn (BOT GEMINI / FULL AUTO VIDEO), kiểm hợp đồng nền tảng + credit + bảo mật +
> UX thật, tìm & sửa bug. Tài liệu để DUYỆT phương án + rubric trước khi chạy.

## 0. Đối tượng rà soát (8 app thật + 1 test + 1 đóng băng)

| App | Nguồn đối chiếu | Nhóm | Rủi ro nổi bật cần soi |
|---|---|---|---|
| thumbnail | BOT GEMINI `thumbnail_api` (có `DOI_CHIEU_THUMBNAIL.md`) | api | parity ~93%, fast-follow ảnh ref/batch |
| taoanh | BOT GEMINI `gemini_image` | api | parity, batch/ảnh ref |
| kichban | BOT GEMINI `youtube_script` | api | parity, preset/lịch sử |
| taovideo | BOT GEMINI `seedance_video` | api | credit token thật, asset://, heal, mod-retry |
| autosubvideo | BOT GEMINI `auto_sub_video` | ffmpeg | ffmpeg-PATH worker, font, credit, upload lớn |
| upscalevideo | BOT GEMINI `video_upscale` | gpu | GPU/NVENC, chunk đĩa, credit, seedance-reuse |
| chataistudio | BOT GEMINI `codex` (AI Creative Studio) | chat | sidecar, ToS/quota dùng-chung, streaming, credit |
| taoclipngan | FULL AUTO VIDEO `cut_clip_short` | gpu | title/score trống, ffmpeg-PATH, model stage |
| demo | — | — | app test (kiểm hợp đồng, không doanh thu) |
| socialbot | ⏸️ đóng băng | browser | KHÔNG rà (không phát triển) |

## 1. RUBRIC rà soát — 7 trục (áp cho MỌI app)

Mỗi app chấm từng trục Đạt/Thiếu/Lỗi + ghi bằng chứng (file:line / ảnh browser).

1. **Parity với nguồn** — lập bảng đối chiếu (như `DOI_CHIEU_THUMBNAIL.md`): mọi nhóm
   điều khiển UI + mọi lựa chọn (`_labels.json`) + model + luồng backend. Đạt mốc
   **≥90%** tính năng người dùng (trừ phần desktop/sheet được phép bỏ, ghi lý do).
2. **Hợp đồng app** — manifest đúng (slug riêng, requires, job_types↔credit_cost);
   routes: `require_login` + CSRF; jobs: **idempotent** (resume) + `ctx.progress` +
   NÉM khi lỗi; **KHÔNG sửa platform_core/server** để app chạy.
3. **Credit** — giữ chỗ→quyết toán đúng; **không double-spend**; **không free-ride**
   (đo lượng thật + nâng giữ chỗ TRƯỚC việc nặng); **hoàn** khi lỗi; giá khớp cost.py.
4. **Cô lập & bảo mật** — A-không-đọc-được-B (guard storage key theo user_id, job
   ownership); validate + cap input; CSRF; không lộ secret; CSP đủ (media/img/connect
   -src cho R2 nếu dùng).
5. **Bền vững & lỗi** — đường lỗi/timeout; resume orphan; worker không treo vô hạn;
   dep/model/ffmpeg tìm được TRÊN WORKER (không chỉ shell dev).
6. **UX thật (browser + URL công khai)** — render đúng trên `app.lttstudios.com`
   (không chỉ loopback); 0 console error (trừ CF beacon đã biết); stream/serve/tải
   chạy; cache-bust static; chip không vỡ.
7. **Deps/hạ tầng** — requirements pin cận trên; model stage; NVENC/GPU/ffmpeg ok;
   dịch vụ NSSM liên quan chạy.

## 2. BỐN PHƯƠNG ÁN chạy rà soát — chấm điểm (1–10)

| Tiêu chí | PA-1 Thủ công tuần tự | PA-2 Đa-agent song song | PA-3 HYBRID rubric + ưu tiên rủi ro | PA-4 Tự động + spot-check |
|---|---|---|---|---|
| Toàn diện (coverage) | 8 | 8 | **10** | 5 |
| Bắt bug THẬT (runtime/UX) | **9** | 5 (agent không mở browser) | **9** | 6 |
| Đối chiếu parity vs nguồn | 7 | **9** (đọc song song) | **9** | 3 |
| Tốc độ | 3 | **9** | 8 | **9** |
| Chi phí/công sức | 4 | 7 | 7 | **9** |
| Rủi ro bỏ sót | 6 | 6 | **9** | 4 |
| Tái dùng (rubric+báo cáo lần sau) | 5 | 6 | **9** | 6 |
| **Tổng** | 42 | 50 | **63** | 42 |

- **PA-1 Thủ công tuần tự**: tôi đi từng app đọc code + browser + sửa. Bắt bug thật
  tốt nhưng CHẬM, đơn luồng, tốn context.
- **PA-2 Đa-agent song song**: fan-out mỗi app một agent lập bảng parity + review code
  theo rubric → tôi sửa. Nhanh + parity tốt, NHƯNG agent không mở browser → sót bug
  runtime/UX. Phải ghép thêm lượt browser của tôi.
- **PA-3 HYBRID (ĐỀ XUẤT)**: kết hợp điểm mạnh —
  1. **Tự động nền**: full suite + scan + **linter hợp đồng app** (mới) quét TẤT CẢ app.
  2. **Đa-agent song song**: mỗi app 1 agent → bảng parity (nguồn↔app) + review đối
     kháng theo rubric → **findings có cấu trúc** (kèm file:line, mức P0/P1/P2).
  3. **Tôi phân loại** (thật/giả), **sửa P0/P1**.
  4. **Tôi browser E2E** từng app trên URL công khai — chuẩn vàng bắt bug runtime/UX.
  5. Ưu tiên theo **rủi ro × doanh thu**; ghi báo cáo `AUDIT_APPS_*` + hoãn có lý do.
- **PA-4 Tự động + spot-check**: chỉ test+linter+scan, browser top-3. Rẻ/nhanh nhưng
  nông (sót parity + bug sâu).

**ĐỀ XUẤT: PA-3 HYBRID** — coverage + bắt-bug-thật + parity đều cao, nhanh nhờ song
song, để lại rubric + báo cáo tái dùng cho app sau.

## 3. Thứ tự ưu tiên (rủi ro × doanh thu)

1. **taovideo** (doanh thu cao + credit token phức tạp + asset:///heal).
2. **thumbnail, taoanh, kichban** (doanh thu, parity đã ghi hoãn — soi gap).
3. **autosubvideo, upscalevideo, taoclipngan** (GPU/ffmpeg — bug hạ tầng worker).
4. **chataistudio** (streaming + ToS/quota + credit theo lượt).
5. **demo** (chỉ kiểm hợp đồng).

## 4. Sản phẩm rà soát (output)

- `docs/AUDIT_APPS_2026-08-02.md`: mỗi app một mục — bảng parity %, findings theo 7
  trục (P0/P1/P2 + file:line + cách sửa), trạng thái fix, phần hoãn có lý do.
- **Linter hợp đồng app** (`tools/lint_app_contract.py` — mới, có test): quét mọi
  `apps/*` kiểm cơ học (manifest hợp lệ; routes có require_login+CSRF ở POST; jobs có
  handle; job_types↔credit_cost; storage key guard theo user_id; không import
  platform_core-sửa…). Chạy được lại mỗi lần thêm app.
- Bản vá bug (commit theo app) + full suite xanh + scan 0 + ảnh browser mỗi app.

## 5. Điều kiện & lưu ý

- Kho nguồn (`D:\BOT GEMINI`, `D:\FULL AUTO VIDEO`) **chỉ đọc** khi đối chiếu.
- Browser test dùng **tài khoản test** + **URL công khai** (đã có lệ).
- Bug hạ tầng nền (nếu phát hiện) sửa ở platform + ghi rõ (không lách trong app).
- Việc lớn phát hiện nhưng ngoài phạm vi (vd P3 worker đa tiến trình) → ghi backlog,
  không nhồi vào đợt rà soát.

## 6. CÂU HỎI CẦN CHỐT

1. **Phương án** — PA-3 HYBRID (đề xuất) / PA-1 / PA-2 / PA-4?
2. **Phạm vi sửa trong đợt này** — chỉ **P0/P1** (bug thật + lỗ hổng) / gồm cả **P2**
   (parity fast-follow, nâng cấp nhỏ) / chỉ **báo cáo, chưa sửa** (fix đợt sau)?
3. **Thứ tự** — theo rủi ro×doanh thu (đề xuất) hay bạn muốn app cụ thể trước?

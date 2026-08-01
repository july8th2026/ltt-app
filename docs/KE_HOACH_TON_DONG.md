# Kế hoạch giải quyết hạng mục TỒN ĐỌNG (hợp nhất)

> Lập 2026-08-01. Gom MỌI việc còn treo từ các nguồn: KE_HOACH_TRIEN_KHAI,
> KE_HOACH_DI_TRU_MODULE, DOI_CHIEU_THUMBNAIL, 06_DON_HA_TANG, AUDIT_MVP,
> AGENT_LTT, + 2 bug phát hiện khi nghiệm thu A2. Tài liệu để DUYỆT thứ tự.

## Bảng tổng — 7 nhóm

Effort: S(<½ ngày) · M(1–2 ngày) · L(nhiều ngày) · XL(dự án riêng). Chặn = điều kiện trước.

### Nhóm 1 — Bug + Mở dòng tiền (nhanh, ảnh hưởng rộng) — **P0**
| # | Việc | Effort | Chặn | Ghi chú |
|---|---|---|---|---|
| 1.1 | ~~Bug phiên hết hạn → 404~~ **KHÔNG PHẢI BUG** (2026-08-01) | — | — | Kiểm lại: `require_login` trả **303→/login** đúng, access-middleware fail-open. Curl + trình duyệt đã xác nhận `/taovideo`→`/login`. 404 trước đó là **transient khi deploy restart + cache trình duyệt**, không phải lỗi code. Bỏ khỏi backlog. |
| 1.2 | **Kích hoạt PayOS (H9 go-live)**: thêm `LTT_PAYOS_*` vào `secrets\app.env` + khai webhook | S | user cấp key PayOS | H9 code đã xong; đang tắt mềm → chưa thu tiền tự động được |

### Nhóm 2 — Nợ nền tảng (đòn bẩy cao, dừng nợ càng sớm càng rẻ) — **P0/P1**
| # | Việc | Effort | Chặn | Ghi chú |
|---|---|---|---|---|
| 2.1 | **T0 — ToolSpec vào hợp đồng app** (AGENT_LTT) | M | — | Mỗi app port KHÔNG có T0 = 1 món nợ T0b. Đã 3 app (A1+A2) → nợ đang lớn. Làm sớm thì nợ dừng + mọi app tương lai tự agent-ready |
| 2.2 | **Worker chạy song song job video dài** | M | — | Xác minh: `run_forever` **đơn luồng, 1 tiến trình** → video poll 1–5' CHẶN mọi job khác. `claim()` đã `SKIP LOCKED` nên chạy N worker AN TOÀN. Fix = NSSM chạy 2–3 worker. Không gấp (tiền-ra-mắt) nhưng cần trước khi có tải thật |

### Nhóm 3 — Hoàn thiện app đang có (parity + doanh thu) — **P1**
| # | Việc | Effort | Chặn | Ghi chú |
|---|---|---|---|---|
| 3.1 | **seedance Pha 2** | — | — | ✅ **XONG 2026-08-01 (~90%)**: refs (ảnh inline + asset:// cho ảnh lớn/video/audio) + heal người-thật + ×2 + dịch + output-moderation retry. Kiểm THẬT: video-có-ref + asset:// live. AK/SK + R2 import từ BOT GEMINI. **Còn:** insightface (cần MSVC) cho face chính xác hơn Haar; **upscale = module riêng** (Real-ESRGAN, thuộc Đợt C). |
| 3.2 | thumbnail fast-follow: ảnh tham chiếu + Batch (+Imagen khi gốc có) | S–M | — | Đã ~93%; đây là phần đã ghi hoãn |
| 3.3 | taoanh: Batch (`---` nhiều prompt) + ảnh tham chiếu | S | — | |
| 3.4 | kichban: preset mẫu + lịch sử + copy từng phần | S | — | |

### Nhóm 4 — Mở nhóm tool mới (cần hạ tầng) — **P2**
| # | Việc | Effort | Chặn | Ghi chú |
|---|---|---|---|---|
| 4.1 | **H10 — R2** | — | — | ✅ **XONG 2026-08-01**: R2Storage + url_for presigned + serve thẳng CDN; creds R2 + ModelArk AK/SK import từ BOT GEMINI; kiểm THẬT trên bucket fb-video-storage. Còn **upload thẳng browser→R2** (presigned PUT) làm khi Đợt B cần. |
| 4.2 | **Định tuyến job GPU** (worker theo `requires=gpu`) | M | — | Mở Đợt C |
| 4.3 | Đợt B (ffmpeg): video_chain → auto_sub_video → concat_pro | L | 4.1 | |
| 4.4 | Đợt C (gpu): video_upscale → cut_clip_short | L | 4.1 + 4.2 | |
| 4.5 | gemini_api_chat (giá trị thấp) · Prompt Studio 28k (dự án riêng) | XL | — | Cân nhắc sau |

### Nhóm 5 — AI Agent (track lớn riêng — Q37 chờ duyệt) — **P2/P3**
| # | Việc | Effort | Chặn | Ghi chú |
|---|---|---|---|---|
| 5.1 | T0 (= 2.1) → D1 fan-out (parent_id + agent_runs) | L | 2.1 | |
| 5.2 | D2 planner + validator + báo giá + cổng duyệt | L | D1, ≥4–5 tool khai ToolSpec | |
| 5.3 | D3 verifier + vòng tự sửa | L | D2 | |
| — | Điều kiện mở chặng D: **≥4–5 tool có ToolSpec + T0 xong + (H10 nếu chạm video)** | | | |

### Nhóm 6 — Vệ sinh hạ tầng (phần lớn user thao tác) — **P3**
| # | Việc | Effort | Ghi chú |
|---|---|---|---|
| 6.1 | **Huỷ VPS Vultr `45.32.104.192`** (đốt tiền) | S (user) | ƯU TIÊN tiền — my.vultr.com |
| 6.2 | Tắt CF Web Analytics beacon | S (user) | bỏ 1 lỗi console |
| 6.3 | Remote GitHub Private + push off-site | S | mirror hiện chỉ trên D: |
| 6.4 | IPv6 máy chủ | — | **hoãn** (giá trị thấp) |

### Nhóm 7 — Hardening còn hoãn (AUDIT_MVP) — **P3**
| # | Việc | Effort | Ghi chú |
|---|---|---|---|
| 7.1 | FK constraints (hoãn từ H7) | M | toàn vẹn dữ liệu |
| 7.2 | e2e đa tiến trình (worker+web) | M | test coverage |
| 7.3 | WAF / rate-limit ở edge Cloudflare | S | chống lạm dụng |

## QUYẾT ĐỊNH 2026-08-01 (người dùng)

**Nhóm 5 (AI Agent) + 2.1 (T0 ToolSpec) HOÃN sang dự án RIÊNG** — làm SAU khi đã
đưa hết app vào; người dùng sẽ gọi riêng khi cần. KHÔNG đưa vào quy trình hiện tại
(T0 chỉ có giá trị cho agent). "Triển khai các hạng mục CÒN LẠI".

## Thứ tự đề xuất (near-term) — đã bỏ agent/T0

1. **1.1 Bug 404 phiên hết hạn** — nhỏ, sửa cho MỌI khách. Làm trước. ◄ đang làm
2. **3.1 seedance Pha 2** — hoàn thiện tool doanh thu cao nhất (xác minh AK/SK + face lib trước).
3. **2.2 Worker song song job video dài** — hạ tầng thật (không phải agent).
4. **3.2–3.4 fast-follow** thumbnail/taoanh/kichban (nhỏ).
5. **4.1 H10 R2** — nút cổ chai → **4.2 GPU-route** → **Đợt B** → **Đợt C**.
6. Nhóm 6 vệ sinh + 1.2 PayOS go-live (cần bạn thao tác, chạy song song) + Nhóm 7 hardening.

**Xen kẽ user-action (làm song song, không chặn code):** 6.1 huỷ Vultr, 6.2 beacon,
6.3 GitHub off-site, 1.2 cấp key PayOS.

## Ghi chú phụ thuộc quan trọng
- **H10 (4.1) là nút cổ chai**: chặn B, C, agent-video, serve file lớn bền → nên làm sớm sau khi xong app hiện có.
- **T0 (2.1) rẻ dần theo thời gian ngược**: càng port thêm app trước T0, nợ T0b càng lớn. Ưu tiên.
- seedance Pha 2 (3.1) có **rủi ro phụ thuộc ngoài** (AK/SK + face lib) — xác minh TRƯỚC khi cam kết.

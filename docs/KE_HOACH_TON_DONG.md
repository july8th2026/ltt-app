# Kế hoạch giải quyết hạng mục TỒN ĐỌNG (hợp nhất)

> Lập 2026-08-01. Gom MỌI việc còn treo từ các nguồn: KE_HOACH_TRIEN_KHAI,
> KE_HOACH_DI_TRU_MODULE, DOI_CHIEU_THUMBNAIL, 06_DON_HA_TANG, AUDIT_MVP,
> AGENT_LTT, + 2 bug phát hiện khi nghiệm thu A2. Tài liệu để DUYỆT thứ tự.

## Bảng tổng — 7 nhóm

Effort: S(<½ ngày) · M(1–2 ngày) · L(nhiều ngày) · XL(dự án riêng). Chặn = điều kiện trước.

### Nhóm 1 — Bug + Mở dòng tiền (nhanh, ảnh hưởng rộng) — **P0**
| # | Việc | Effort | Chặn | Ghi chú |
|---|---|---|---|---|
| 1.1 | **Bug phiên hết hạn → 404** ở mọi app path (phải redirect `/login`) | S | — | Phát hiện ở A2; ảnh hưởng MỌI khách; access-middleware trả 404 thay vì đưa về đăng nhập |
| 1.2 | **Kích hoạt PayOS (H9 go-live)**: thêm `LTT_PAYOS_*` vào `secrets\app.env` + khai webhook | S | user cấp key PayOS | H9 code đã xong; đang tắt mềm → chưa thu tiền tự động được |

### Nhóm 2 — Nợ nền tảng (đòn bẩy cao, dừng nợ càng sớm càng rẻ) — **P0/P1**
| # | Việc | Effort | Chặn | Ghi chú |
|---|---|---|---|---|
| 2.1 | **T0 — ToolSpec vào hợp đồng app** (AGENT_LTT) | M | — | Mỗi app port KHÔNG có T0 = 1 món nợ T0b. Đã 3 app (A1+A2) → nợ đang lớn. Làm sớm thì nợ dừng + mọi app tương lai tự agent-ready |
| 2.2 | **Worker chạy song song job video dài** | M | — | Phát hiện ở A2: 1 worker poll video 1–5' sẽ CHẶN mọi job khác. Cần nhiều worker / tách submit-poll |

### Nhóm 3 — Hoàn thiện app đang có (parity + doanh thu) — **P1**
| # | Việc | Effort | Chặn | Ghi chú |
|---|---|---|---|---|
| 3.1 | **seedance Pha 2**: asset:// + refs (ảnh/video/audio) + face-moderation + ×2 + dịch + upscale → parity ~90% | L | **ModelArk AK/SK** + thư viện nhận diện mặt (phải xác minh có không) | Tool video doanh thu cao nhất |
| 3.2 | thumbnail fast-follow: ảnh tham chiếu + Batch (+Imagen khi gốc có) | S–M | — | Đã ~93%; đây là phần đã ghi hoãn |
| 3.3 | taoanh: Batch (`---` nhiều prompt) + ảnh tham chiếu | S | — | |
| 3.4 | kichban: preset mẫu + lịch sử + copy từng phần | S | — | |

### Nhóm 4 — Mở nhóm tool mới (cần hạ tầng) — **P2**
| # | Việc | Effort | Chặn | Ghi chú |
|---|---|---|---|---|
| 4.1 | **H10 — R2**: `Storage.url_for` + presigned + upload thẳng browser→R2 | L | tài khoản R2 | Mở Đợt B/C + serve file lớn bền + agent-video |
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

## Thứ tự đề xuất (near-term)

Cân bằng "nhanh + ảnh hưởng rộng" với "đòn bẩy + mở tiền":

1. **1.1 Bug 404 phiên hết hạn** — nhỏ, sửa cho MỌI khách. Làm trước.
2. **2.1 T0 ToolSpec** — dừng nợ T0b (đang lớn), nền cho agent + mọi app sau. Đòn bẩy cao nhất.
3. **1.2 PayOS go-live** — mở dòng tiền thật (cần bạn cấp key PayOS).
4. **3.1 seedance Pha 2** — hoàn thiện tool doanh thu cao nhất (sau khi xác minh AK/SK + face lib).
5. **4.1 H10 R2** — mở Đợt B + serve file lớn bền + điều kiện agent-video.
6. → Đợt B, GPU-route, Đợt C, chặng D agent, vệ sinh, hardening.

**Xen kẽ user-action (làm song song, không chặn code):** 6.1 huỷ Vultr, 6.2 beacon,
6.3 GitHub off-site, 1.2 cấp key PayOS.

## Ghi chú phụ thuộc quan trọng
- **H10 (4.1) là nút cổ chai**: chặn B, C, agent-video, serve file lớn bền → nên làm sớm sau khi xong app hiện có.
- **T0 (2.1) rẻ dần theo thời gian ngược**: càng port thêm app trước T0, nợ T0b càng lớn. Ưu tiên.
- seedance Pha 2 (3.1) có **rủi ro phụ thuộc ngoài** (AK/SK + face lib) — xác minh TRƯỚC khi cam kết.

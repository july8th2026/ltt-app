# PLAN TRIỂN KHAI CUỐI — A → H

Nguyên tắc: **LẮP TRƯỚC · KIỂM SAU · TỐI ƯU CUỐI.**

Hai mốc tách bạch:
- **BASELINE** (A→G): chạy đúng từ đầu tới cuối. Không cần model tốt nhất, GUI
  đẹp nhất, giá rẻ nhất.
- **OPTIMIZED** (H): **chỉ bắt đầu sau khi chủ dự án nghiệm thu baseline.**

---

## Phase A — Hiểu WanGP ✅ **ĐÃ XONG**

| | |
|---|---|
| Mục tiêu | trích abstraction thật, không ép taxonomy tự nghĩ |
| Đầu ra | `WANGP_ARCHITECTURE_EXTRACTION.md` · `DEEPY_UNKNOWN_GAPS.md` · `WANGP_VS_LTT_RECONCILIATION.md` · `REUSE_DELETE_BUILD_MATRIX.md` · `FINAL_MINIMAL_LTT_WANGP_ARCHITECTURE.md` |
| Dùng lại | — |
| Mã mới | 0 |
| Cổng | 20 mục có `EVIDENCE`; 12 abstraction xoá khỏi kế hoạch |
| Chi phí GPU | **$0** |

## Phase B — WanGP vanilla trên C-CLOUD ✅ **ĐÃ XONG**

| | |
|---|---|
| Mục tiêu | cài được, chạy được, sinh được video thật |
| Dùng lại | `Dockerfile` chính chủ của WanGP; `cloud_api.py`/`video_cloud.py` của V3 |
| Mã mới | `tools/wangp/*` (script đo, không phải sản phẩm) |
| Cổng | ✅ mp4 thật 16,18 MB; `mmgp` 3.7.14; `sageattention` 2.2.0 |
| Chi phí | **$2,81** / trần $6,00 |
| Rollback | môi trường nằm trên volume, xoá pod không mất |

## Phase C — Nghiệm thu năng lực native ⏳ **ĐANG DỞ**

| | |
|---|---|
| Mục tiêu | xác nhận hợp đồng engine bằng **chạy thật**, không bằng đọc |
| Đầu vào | môi trường Phase B trên volume |
| Đã ĐẠT | `submit_task` ✅ · progress 786 sự kiện ✅ · preview 20 ảnh ✅ · **cancel ✅** · `get_default_settings` ✅ |
| **Còn nợ** | **C1** VRAM+tốc độ ở `profile 3` · **C2** huỷ xong GPU có nhả VRAM · **C3** hai ô `NEEDS_LIVE_TEST` của Deepy |
| Mã mới | 0 |
| Cổng nghiệm thu | có số `profile 3` để chốt lớp GPU |
| Chi phí ước | **~$0,50** một lượt |
| ⛔ Điều kiện dừng | không thuê được GPU ở `US-KS-2` ⇒ dừng, báo, **không tự đổi card đắt hơn** |

🔴 **Chặn thật:** `US-KS-2` cạn A100 lúc 06/09; `stop` đã nhả card. Đây là rủi ro
kiến trúc, không phải sự cố — ghi ở `O-007`.

## Phase D — Tích hợp LTT tối thiểu

| | |
|---|---|
| Mục tiêu | app `lttvideo` gọi được WanGP, **không GPU cũng viết được phần lớn** |
| Tệp | `apps/lttvideo/{manifest,routes,jobs,features,cost,kha_nang,ho_so}.py` · `platform_core/wangp_client.py` · template + i18n |
| Dùng lại | `require_login` · `csrf` · `job_runner` · `leases` · `credit` · `storage` · `image_input` · `i18n` · `ltt.css` |
| Mã mới **tối thiểu** | 5 thành phần ở `REUSE_DELETE_BUILD_MATRIX.md` §B |
| Test | đơn vị cho `cost`/`kha_nang`/`ho_so`; hợp đồng app; **dải test 4xx/7xx chưa cấp — phải xin trước** |
| Kiểm biên thật | client gọi WanGP giả lập trước, thật ở E |
| Cổng | `gate.py` xanh; `lint_app_contract` không cảnh báo; ≤900 dòng `routes.py` |
| Chi phí GPU | **$0** |
| Rollback | app chưa `public`, chưa `api_exposed` ⇒ gỡ thư mục là xong |
| ⛔ Dừng nếu | phải sửa `platform_core/` hay `server/` ⇒ **dừng và nói rõ vì sao** |

## Phase E — E2E thật: LTT → WanGP → R2 → cancel/ownership

| | |
|---|---|
| Mục tiêu | chứng minh **biên thật**, không phải mock |
| Phải ĐẠT | ảnh lên R2 có chủ · job qua hàng đợi LTT · sinh thật trên C-CLOUD · **đặt lại tên tệp** · tệp về R2 đúng người · xác minh rồi mới `done` · huỷ lan tới WanGP · credit quyết toán idempotent · dọn scratch |
| Dùng lại | toàn bộ [7]–[11] của bản kiến trúc |
| Mã mới | dán nối, không thêm abstraction |
| Kiểm biên thật | **bắt buộc** — trình duyệt trên `https://app.lttstudios.com`, không chỉ loopback |
| Cổng | `D-V2-009`: **đây là cổng cho phép P06** |
| Chi phí ước | 2–3 lượt sinh |
| Rollback | tắt cờ app |

## Phase F — Cutover + loại bỏ legacy

| | |
|---|---|
| Điều kiện vào | **E PASS** — không có ngoại lệ |
| Việc | tag `video-legacy-final-pre-wangp` trên `claude/ltt-video-ai-v3-p00-3f5713`; **không merge**; quét 7 mẫu ký hiệu chứng minh trunk vẫn 0; quyết số phận volume + endpoint cũ |
| Mã mới | 0 |
| Cổng | 0 tham chiếu thực thi tới runtime V3 trên trunk |
| Chi phí | $0 *(có thể tiết kiệm $21/tháng nếu bỏ volume)* |

## Phase G — Nghiệm thu người dùng

| | |
|---|---|
| Mục tiêu | nhân viên thật làm việc thật |
| Việc | mở cho vài tài khoản nội bộ; thu phản hồi; đo tần suất mơ hồ/thất bại |
| Cổng | **chủ dự án nghiệm thu** ⇒ đây là ranh giới BASELINE / OPTIMIZED |
| ⛔ | cổng thương mại vẫn **ĐÓNG** (`D-V2-011` + giấy phép §5.2(g)) |

## Phase H — Tối ưu · **CHỈ SAU KHI G ĐƯỢC NGHIỆM THU**

Không làm sớm, không làm song song:

`O-006` lớp GPU đúng · `O-007` bỏ/thu volume + cached-model · `O-008` idleTimeout
+ giữ ấm · Deepy tuning · quality benchmark (VBench) · prompt enhancement ·
quality routing · GUI refinement · giảm giá vốn · hậu xử lý · pipeline nhiều bước
· warm pool · multi-GPU.

⛔ **Không mục nào của H được kéo lên trước G.** Đó chính là cách V3 chết: tối ưu
trước khi có đường chạy thật.

---

## Bảng chi phí GPU theo phase

| Phase | GPU | Ước |
|---|---|---|
| A | không | $0 |
| B | đã tiêu | $2,81 |
| C | có | ~$0,50 |
| D | **không** | $0 |
| E | có | ~$2 |
| F | không | $0 |
| G | có | theo mức dùng thật |
| H | có | sau nghiệm thu |

⭐ **Phase D — phần dài nhất — không tốn GPU.** Làm song song với C được.

## Ba luật xuyên suốt

1. **Không thêm abstraction** nếu chưa điền xong khối `NEW COMPONENT` ở
   `REUSE_DELETE_BUILD_MATRIX.md` §B.
2. **Không sửa `platform_core/` hay `server/`** để thêm app. Buộc phải sửa ⇒
   dừng và nói rõ vì sao — dấu hiệu hợp đồng app thiếu.
3. **Mọi việc làm được ở $0 phải xong trước khi bật máy.** Phase A tìm ra hai lỗi
   sẽ cháy một lượt boot bằng cách **đọc mã**.

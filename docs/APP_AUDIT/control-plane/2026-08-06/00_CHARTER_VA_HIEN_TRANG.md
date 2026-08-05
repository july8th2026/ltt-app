# 00 — Charter và hiện trạng đo được

**Mã:** LTT-AQA `AUDIT STANDARD -- app: control-plane`
**Ngày snapshot:** 2026-08-06
**Phạm vi:** hệ điều hành nền tảng — logic vận hành, bố cục mã nguồn, phân loại
và kích thước file, chất lượng hiển thị mobile.
**KHÔNG trong phạm vi:** giá trị sản phẩm của từng app, benchmark đối thủ.
**Môi trường:** fixture cô lập `127.0.0.1:8119`. Không chạm production, không
dùng dữ liệu người dùng thật.
**Ràng buộc phiên:** chỉ phân tích. **Không sửa một dòng mã nào.**

## 1. Lệch chuẩn có chủ ý so với quy tắc, và lý do

Quy tắc §2 buộc báo cáo bốn kết quả gồm **Market Score (M)**. Với hệ điều hành
nội bộ, M đo theo "cùng persona/JTBD" là vô nghĩa: không có sản phẩm nào trên thị
trường cùng job-to-be-done với control plane của riêng LTT, và mọi con số tôi đặt
ra ở đây đều là bịa. Theo tinh thần §3 ("app không dùng AI phải phân bổ 8 điểm AI
trước A0 và ghi lý do"), tôi **công bố M là `không áp dụng`** thay vì gán một số.

Quy tắc §8 (benchmark 5–7 đối thủ) cũng bỏ, cùng lý do. Ghi rõ ở đây để người đọc
sau không tưởng là quên.

## 2. Quy mô đo được

| Khu vực | File | Dòng | Nhận xét |
|---|---:|---:|---|
| `platform_core/` | 37 | 6.030 | trung bình 163 dòng/file |
| `server/` | 47 | 7.570 | trung bình 161 |
| `apps/` | 96 | 17.474 | trung bình 182, **phân tán rất rộng** |
| `core/` (di sản desktop) | 70 | 15.668 | vẫn được `server/services/*` dùng |
| `tools/` | 30 | 4.500 | |
| `tests/` | 140 | 30.954 | **35% tổng mã nguồn** |
| `frontend/` | 43 | 6.440 | 3 bundle React/Vite |

Tổng ~88.600 dòng (không kể `node_modules`).

Tỉ lệ test/mã sản phẩm ≈ **1:1,9**. Đây là con số tốt và giải thích vì sao
2.246 test bắt được hồi quy suốt phiên trước.

## 3. Mười file lớn nhất

| Dòng | File | Đánh giá |
|---:|---|---|
| **1.799** | `apps/prompt_ai_ommi/routes.py` | **quá lớn** — 64 handler một file |
| **1.313** | `apps/agent/routes.py` | **quá lớn** — 48 handler, 95% mã của app |
| **979** | `server/admin.py` | lớn, nhưng là một miền mạch lạc |
| 930 | `core/sheet_runner.py` | di sản |
| 892 | `frontend/agent-canvas/src/CanvasShell.tsx` | lớn với một component React |
| 868 | `apps/autosubvideo/routes.py` | chấp nhận được (19% mã app) |
| 673 | `apps/upscalevideo/routes.py` | chấp nhận được |
| 623 | `platform_core/models.py` | hợp lý cho một lược đồ |
| 607 | `core/tiktok/compliance_guard.py` | di sản |
| 563 | `frontend/prompt-ai-ommi/src/ommiApi.ts` | ngưỡng trên, còn một miền |

## 4. Bố cục từng app

| App | File | Dòng | `routes.py` | % | `services/` |
|---|---:|---:|---:|---:|---|
| agent | 4 | 1.380 | 1.313 | **95%** | không |
| chataistudio | 6 | 764 | 508 | 66% | không |
| demo | 4 | 221 | 123 | 55% | không |
| prompt_ai_ommi | 12 | 3.654 | 1.799 | 49% | **có** |
| taoclipngan | 6 | 859 | 419 | 48% | không |
| thumbnail | 5 | 796 | 377 | 47% | không |
| taoanh | 5 | 603 | 248 | 41% | không |
| upscalevideo | 13 | 1.972 | 673 | 34% | không |
| taovideo | 10 | 1.533 | 513 | 33% | không |
| kichban | 5 | 720 | 228 | 31% | không |
| autosubvideo | 19 | 4.463 | 868 | **19%** | không |
| mediatools | 4 | 450 | 11 | 2% | không |

`autosubvideo` là hình mẫu: 19 file, route chỉ chiếm 19%, phần còn lại tách theo
miền (`segmenter`, `ass_builder`, `jobs`…). `agent` là thái cực ngược lại.

## 5. Quy ước đặt tên file

| | manifest | routes | jobs | features | cost | tables |
|---|---|---|---|---|---|---|
| Số app có | 13/13 | 12/13 | 11/13 | 5/13 | 5/13 | 1/13 |

`manifest.py` + `routes.py` + `jobs.py` là bộ ba ổn định — hợp đồng app hoạt
động. Nhưng **không có quy ước nào cho tầng nghiệp vụ**: `features.py` (5 app),
`cost.py` (5 app), `services/` (1 app), hoặc không có gì. Đây là gốc rễ của việc
`routes.py` phình to: khi không có chỗ mặc định để đặt logic, nó nằm lại trong
route.

## 6. Bằng chứng

| ID | Cấp | Nội dung |
|---|---|---|
| E1-1 | E1 | `wc -l`, `find`, `grep -c` trên toàn repo |
| E1-2 | E1 | Đếm handler bằng `grep -c "^@router\."` |
| E3-1 | E3 | Quét 15 trang ở 390×844 trên Chrome thật |
| E3-2 | E3 | Đo kích thước vùng chạm và tương phản bằng `getBoundingClientRect` + công thức WCAG |

# LTT LLM Dual-Model — chỉ mục (câu hỏi → tệp chủ)

Hai model nhà trên máy B: **LTT-3.8** (Qwen3.8-27B, RTX 3090, chia với model ảnh) và **LTT-3.5**
(Qwen3.5-9B, RTX 5060 Ti). Máy A quyết định nhận (Phương án C, L-23); cổng máy B là rào vật lý.

⛔ Tệp này **không** chép số. Mỗi câu hỏi có đúng MỘT chỗ trả lời:

| Câu hỏi | Hỏi ở đâu |
|---|---|
| Một lượt thật đi qua những đâu, ai gác mỗi chặng (đọc TRƯỚC khi sửa) | `BAN_DO_DUONG_DI.md` |
| Đã quyết gì, vì sao (D01–D09, L-1…L-28, mới nhất ở cuối) | `DECISION_LOG.md` |
| Số theo model: `-c`, `-np`, pool KV, ngưỡng whale, đệm ước | `apps/ltt_llm/ngan_sach.py` (`HO_SO`) |
| Cờ engine máy B đang khai | `llm_gateway/deploy/llama-swap.yaml` |
| Đang trực: deploy, thứ tự A/B, residency 3090, điểm lùi | `RUNBOOK.md` |
| Việc đã làm trên máy thật (nhật ký, có bằng chứng) | `NHAT_KY_TRIEN_KHAI.md` |
| Lỗi đo tải còn mở / đã xử | `SO_LOI_DO_TAI.md` |
| Plan hiện hành | `docs/superpowers/plans/2026-09-18-ltt-llm-v2-lam-lai-tren-phuong-an-c.md` |
| Nghiệm thu Phương án C trên production (17/09) | `artifacts/NGHIEM_THU_PHUONG_AN_C_17_09.md` |
| Cái gì đang sống trên production | `python tools\api_prod_canary.py trang-thai` |

## Lịch sử — ảnh chụp, không phải hiện trạng

| Tệp | Ảnh chụp |
|---|---|
| `00_CURRENT_BASELINE.md` · `01_MULTI_JOB_INHERITANCE.md` · `02_REQUEST_TRACE.md` · `03_GPU_RESOURCE_MAP.md` · `05_COMMUNITY_EVIDENCE.md` · `06_GAP_ANALYSIS.md` | 11/09 (Gate R0–R5, trước khi triển khai) |
| `10_BENCHMARK_P3.md` | 11–12/09 (số đo P3 máy B) |
| `BAN_GIAO_PHIEN.md` · `CMC_SOURCE_STATE.md` | 12/09 |
| `BANG_DOI_SOAT.md` · `BO_DO_CHUAN.md` | 13/09 |
| `AUDIT_API_2026-09-14.md` · `LUAT_DO_SAU_SUAT.md` · `MA_TRAN_TEST_JOB_DAI.md` | 14/09 |
| `KE_HOACH_PHUONG_AN_C.md` | 17/09 — đã thực thi (L-23); §3 là mô hình hiện hành |
| Spec 1 `docs/superpowers/specs/2026-09-11-ltt-llm-dual-model-design.md` | 11/09 |

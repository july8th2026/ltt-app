# HAI MÁY — máy A và máy B, vai trò và phần cứng

> **Nguồn chân lý DUY NHẤT cho câu hỏi "máy nào làm gì, máy nào có card gì".**
> Tệp nào khác khẳng định lại số card hoặc danh sách model của một máy là **sai**
> — sửa ở đó, đừng sửa tệp này cho khớp. `tests/test_3100_hai_may_a_va_b.py`
> chốt điều đó bằng máy.
>
> Lập 2026-09-24, sau khi một phiên viết cả một brief dựa trên giả định *"máy B
> có một card RTX 5060 Ti 16 GB"*. Giả định ấy sai theo **hai** hướng cùng lúc:
> máy B có **hai** card, và card 5060 Ti mà phiên ấy nghĩ tới là card của **máy A**.

---

## 1. 🔴 NGUỒN NHẦM LẪN — **CẢ HAI MÁY ĐỀU CÓ MỘT RTX 5060 Ti**

Thấy chuỗi `5060 Ti` trong một bản ghi, một log, một số đo ⇒ **bạn chưa biết đó
là máy nào**. Tên card không phân biệt được hai máy. Đừng đoán theo tên.

**Phân biệt bằng VIỆC, không bằng tên card:**

| Thấy cái này trong mã / log | Thì đang nói về |
|---|---|
| `platform_core/gpu_lease.py`, bảng `gpu_leases`, `JobContext.gpu_uuid` | **máy A** |
| `llm_gateway/` · `apps/ltt_llm/ngan_sach.py` · `llama-swap` · `qwen38-api`/`qwen35-api` | **máy B** |
| `render_gateway/` · ComfyUI · `gpu_may_b.json` | **máy B** |
| `platform_core/llm/residency.py` (trọng tài) | mã chạy ở **máy A**, phân xử card của **máy B** |

⭐ Cách chắc chắn nhất là **UUID**: mỗi card có UUID riêng, và hai chiếc 5060 Ti
của hai máy có UUID khác nhau. ⛔ Đừng chép UUID vào đây — chúng đã có chủ:

- card của **máy B**: `llm_gateway/deploy/gpu_may_b.json` (chốt bởi
  `tests/test_1200_ghim_gpu_may_b.py`; hai bộ đọc, một nguồn — xem
  `render_gateway/danh_tinh_gpu.py`);
- card của **máy A**: **không khai trong kho** — `gpu_lease.acquire()` dò bằng
  `nvidia-smi` lúc chạy rồi ghi vào bảng `gpu_leases`. Muốn biết hôm nay có gì:
  chạy `nvidia-smi -L` **trên máy A**.

## 2. Vai trò

| | **MÁY A** | **MÁY B** |
|---|---|---|
| vai | **nền tảng + production** | **chỉ nuôi model** |
| chạy gì | app web (cổng 8100), worker + hàng đợi job, PostgreSQL, Cloudflare Tunnel, `C:\LTTPlatform` | `llm_gateway` (LLM) + `render_gateway`/ComfyUI (ảnh) |
| số card | **một** RTX 5060 Ti 16 GB | **hai**: RTX 3090 (`nvidia-smi` index 0) + RTX 5060 Ti |
| card dùng cho | demucs · nhận dạng tiếng · TTS · bộ đo QC (MetricX / ECAPA / SQUIM) | `qwen38-api` trên 3090 · `qwen35-api` trên 5060 Ti · ComfyUI |
| ai cấp card | `platform_core/gpu_lease.py` (lease nguyên tử, `UNIQUE(host, gpu_uuid)`) | `llama-swap` ghim từng model vào một UUID; trọng tài residency ở **máy A** quyết 3090 thuộc LLM hay thuộc ảnh |
| lõi CPU | 20 | — |

⛔ **Máy A là máy production, và là máy dùng chung giữa các phiên.** Lệnh nặng đi
qua `docs/QUY_TAC_CHAY_LENH_NANG.md`. ⛔ Máy B **không** đi đường deploy của nền
tảng (`docs/16_CAP_NHAT_VA_DEPLOY.md` §5).

## 3. ⛔ KHÔNG XÂY MODEL MỚI TRÊN MÁY B — chủ dự án chốt 2026-09-24

Máy B nuôi **đúng hai** model công khai: `ltt-3.8` và `ltt-3.5`. Cần một model
mới ⇒ dựng nó trên **máy A**, không thêm vào máy B.

Vì sao: hai card máy B đã kín (mỗi model thường trú một card, và 3090 còn phải
chia cho ảnh). Thêm model thứ ba là quay lại chế độ swap — nạp lại 15 GB giữa
lượt khách, đúng sự cố mà kiến trúc "hai model hai card, `swap:false`" sinh ra để
diệt.

## 4. Số cụ thể thì hỏi ai — ⛔ đừng chép vào đây

| Câu hỏi | Chủ |
|---|---|
| Đường đi một lượt LLM, suất, pool KV | `docs/ltt_llm_dual/BAN_DO_DUONG_DI.md` |
| Suất · `-c` · ngưỡng whale · tốc độ ước theo model | `apps/ltt_llm/ngan_sach.HO_SO` |
| Tệp GGUF nào, cờ `llama-server` nào | `llm_gateway/deploy/llama-swap.yaml` |
| UUID card máy B | `llm_gateway/deploy/gpu_may_b.json` |
| Ngân sách / giá model ảnh nội bộ | `render_gateway/ngan_sach.py`, `apps/anhnoibo/gia.py` |
| Mod xung nhớ card máy B, khôi phục VGA | `docs/MAY_B_VGA/README.md` |
| Nghiệm thu tải thật xuyên hai máy | `docs/VAN_HANH_THAT.md` |

## 5. Đọc bản ghi cũ thế nào

Kho này có **nhiều bản ghi có ngày** (nhật ký, audit, benchmark, kế hoạch) khai
cấu hình của một thời điểm đã qua. Hai bản ghi hay bị đọc sai nhất:

- máy A **từng có hai** card 5060 Ti (tháng 08/2026). Nay còn **một**. Mọi tài
  liệu viết *"máy A có 2 card"*, *"card thứ hai nằm không"*, *"dual-GPU soak"* là
  **lịch sử** — ví dụ `docs/ANH_NOI_BO/DUNG_HAI_CARD_MAY_A.md`,
  `docs/KE_HOACH_TIEP_2026-08-24.md`.
- máy B **từng chỉ có** RTX 3090 (trước 11/09/2026). Nay có **hai** card. Ví dụ
  `docs/ANH_NOI_BO/CHIA_GPU_HAI_MODEL.md`, `docs/audit_ltt_llm/STATE.md`.

⛔ **Đừng sửa những bản ghi ấy** — sửa một bản ghi có ngày là làm giả bằng chứng.
Đọc chúng như lịch sử, và hỏi tệp này cho cấu hình hôm nay.

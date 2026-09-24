# Thang cổng từng bước cho Auto Scan Video — thiết kế

> Chủ dự án chốt 24/09/2026. Thay cách cũ (chạy cả chuỗi rồi đi tìm lỗi).
> Bối cảnh + dữ liệu vì sao đổi: `docs/auto_scan_video_final/THANG_CONG_TUNG_BUOC.md`

## 1. Quyết định đã chốt (không mở lại trong phạm vi spec này)

| # | quyết định | chốt bởi |
|---|---|---|
| Q1 | Còn khiếm khuyết sau vòng sửa ⇒ **vẫn giao, nhưng khai rõ số liệu**, và khai **trước khi trừ credit** | chủ dự án 24/09 |
| Q2 | Máy B chạy **đúng hai** model: `ltt-3.8`, `ltt-3.5`. ⛔ Không thêm model mới trên B. Model mới (nếu cần) dựng trên **máy A** | chủ dự án 24/09 |
| Q3 | Dịch zh→vi dùng **`ltt-3.5`** (= Qwen3.5-9B GGUF Q6_K) qua **đường ASV hiện có** (`ai.goi_tinh_tien` → `dieu_phoi`). ⛔ Không chuyển sang `runtime_noi_bo` — ASV có sổ tiền riêng `asv_usage`, có chủ ý | chủ dự án 24/09 |
| Q4 | Chân lý nền chất lượng dịch: **FLORES-200** (zh↔vi, người dịch) | chủ dự án 24/09 |
| Q5 | **Tên riêng: phiên Hán-Việt** (张伟 → Trương Vĩ) | chủ dự án 24/09 |
| Q6 | Xác thực bộ chấm bằng cách **soi bản chuẩn FLORES**: mọi phán quyết "dịch sai" trên một bản dịch của người = **báo động giả theo định nghĩa** | chủ dự án 24/09 |
| Q7 | Sản phẩm là **lồng tiếng voice→voice**. Luồng chính lấy lời từ **nghe chép**; **hardsub dùng để ĐỐI CHIẾU**, không phải nguồn chính | chủ dự án 24/09 |
| Q8 | Khoá logic bằng **phương án A**: hợp đồng **phái sinh, máy kiểm** | chủ dự án 24/09 |
| Q9 | Thứ tự siết: **kiểm kê video → văn bản nguồn → dịch** | chủ dự án 24/09 |

⚠️ **Q7 mâu thuẫn với mã hiện tại.** `nguon_loi.dinh_tuyen` mặc định `auto` và ưu tiên
`embedded → ocr → asr`. Đo B0: **cả 4 phim mẫu** có hardsub Hán 98,8–100% ⇒ cả 4 đi
đường `ocr`, **đường `asr` chưa từng chạy thật**. ⇒ Đổi mặc định là một phần của spec này.

## 2. Hai máy (nguồn chân lý cho spec này)

| | MÁY A | MÁY B |
|---|---|---|
| vai | nền tảng + production: app, worker, PostgreSQL, Cloudflare | **chỉ nuôi model**: `llm_gateway` + ComfyUI |
| card | **một** RTX 5060 Ti 16 GB, cấp qua `gpu_lease` | **hai**: RTX 3090 + RTX 5060 Ti |
| chạy gì trên card | demucs · nghe chép · TTS · bộ đo QC | `qwen38-api` (3090) · `qwen35-api` (5060 Ti) |

🔴 **Cả hai máy đều có một RTX 5060 Ti** — tên card **không** phân biệt được máy.
Phân biệt bằng việc: `gpu_lease` ⇒ A; `llm_gateway`/`ngan_sach.py` ⇒ B.

## 3. Hợp đồng mắt xích (phương án A)

Mở rộng `GiaiDoan` trong `apps/auto_scan_video/pipeline.py` — **cùng chỗ** đã khai
`sau=`. ⛔ Không tạo bảng khai thứ hai ở tệp khác.

```python
@dataclass(frozen=True)
class GiaiDoan:
    ten: str
    app_slug: str
    job_type: str
    sau: tuple[str, ...] = ()
    tai_nguyen: str = ""
    tai_nguyen_suat: int = 0
    # ── BỐN TRƯỜNG MỚI ────────────────────────────────────────────
    tien_quyet: tuple[str, ...] = ()      # điều kiện phải đúng; ("",) = khai "không có"
    ma_loi: tuple[str, ...] = ()          # mã lỗi ổn định bước này được phép ném
    do: tuple[str, ...] = ()              # tên phép đo quyết định ĐẠT
```

### Bốn bất biến do máy cưỡng chế

| # | bất biến | vì sao — lỗi đã xảy ra thật |
|---|---|---|
| I1 | bao đóng `sau` phải phủ mọi lần **đọc thật** (quét AST) | N-08: khai trực tiếp hẹp hơn đọc thật ở ≥6 bước; bao đóng đang chịu lực mà không ai khai |
| I2 | `tien_quyet` **không được rỗng** (phải khai `("",)` nếu thật không có) | lượt A chết vì tự khớp giọng **đòi nguồn có tiếng nói** mà không ai viết ra |
| I3 | mọi `ma_loi` phải nằm trong sổ chung, ⛔ không ném chuỗi tự do | G-04: câu giải thích dừng ở cột `error`, khách nhận câu chung chung + nút chắc chắn hỏng |
| I4 | `do` **không được rỗng** | một bước không có phép đo thì không thể "đạt" ⇒ không được vào thang cổng |

## 4. Cổng "đạt" của mỗi bước

```
1. SOÁT MÃ      logic kín chưa · tham số nào là số ĐOÁN · nhánh chết · tiền đề chưa khai
2. TRA NGUỒN    GitHub / model card / tài liệu engine (CLAUDE.md luật 10)
3. HỢP ĐỒNG     khai 4 trường mới; máy kiểm I1–I4
4. SỬA          ⛔ một bước một lượt
5. ĐO           trên video thật, CÓ ĐỐI CHỨNG (tiêm lỗi cũ hoặc chân lý nền tay)
```

⛔ **Ngưỡng đạt viết ra TRƯỚC khi đo.** Đặt ngưỡng sau khi thấy số là hợp lý hoá một
kết quả tồi. Không đạt ⇒ sửa rồi đo lại, ⛔ **không nới ngưỡng**.
⛔ **Không "gần đạt rồi đi tiếp"** — một mắt xích 90% ở đầu chuỗi thì 11 bước sau đứng trên 90%.

## 5. Vật liệu bench (đo B0, 24/09)

| phim | dài | tiếng nói | F0 | hardsub Hán | cảnh |
|---|---|---|---|---|---|
| món ăn | 4:25 | **CÓ** (+5,98 dB) | 160,0 Hz | 100% | 125 |
| cắm trại | 3:10 | **CÓ** (+2,92 dB) | 166,7 Hz | 100% | 100 |
| PUBG | 1:47 | **CÓ** (+3,76 dB) | 188,2 Hz | 98,8% | 18 |
| súng hơi | 4:35 | **không chắc** (−2,9 dB) | 170,2 Hz | 99,5% | 127 |

⭐ **Hardsub là chân lý nền sẵn có cho nghe chép** — bản chữ do người làm phim viết.
⚠️ Nhưng nó có thể **rút gọn** so với lời nói ⇒ là đối chiếu tốt, **không hoàn hảo**;
mọi con số WER đo theo nó phải khai giới hạn đó.
⛔ Phim "súng hơi" **không** dùng cho bench cần tiếng nói (không chắc có giọng).

## 6. Phạm vi — cái KHÔNG làm trong spec này

⛔ Không tái cấu trúc 12 bước thành giao diện cứng (phương án C) — để sau khi luồng chính đạt.
⛔ Không hợp nhất đường tiền ASV vào `runtime_noi_bo` (Q3).
⛔ Không thêm model trên máy B (Q2).
⛔ Không deploy, không `public=True` (§24 đề bài gốc).
⛔ Không mở khách (cờ `LTT_AUTO_SCAN_VIDEO` giữ tắt) ⇒ lớp "chốt trên `app.lttstudios.com`" còn hở, ghi là **chờ chủ dự án cho mở khách**.

## 7. Nợ giữ nguyên, hoãn có chủ ý

`N-01` (giao hàng với 85 khiếm khuyết — Q1 đã định hướng, còn phần hiển thị trước khi
trừ credit) · `N-07` (`so_canh=1` ở lượt A/B trong khi đo trực tiếp 18–127) ·
`N-08` đường **chạy lại** chưa đo · `M-11` (lần chạy mồ côi trong CSDL test) ·
WER hai nhánh `whisperx` ↔ `faster-whisper` chưa ai so.

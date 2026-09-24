# NT_CUOI lượt A — giữ hình · AUTO_MATCH · zh→vi

Nhánh `phien/asvf-nghiem-thu-v2` · 24/09/2026 10:17–10:27 (UTC+7) · **179,4 s**
Phim: `深度解析丨跳伞…` 106,835 s · h264 836×576 · aac · tiếng Trung + hardsub Trung.
Nguồn định nghĩa lượt: `bang_chung/NEN_V3.md` lượt A (23/09).

## Độ trung thực của lượt chạy

| | |
|---|---|
| `LTT_ASV_QC_AI` | **BẬT** |
| model | THẬT (pool khoá → máy B) |
| giọng | THẬT (LTT Voice :8120) — *không tới bước này* |
| **card** | ✅ **ĐƯỢC CẤP** — `GPU-6df3a5c5…` RTX 5060 Ti, `thiet_bi="cuda"` |
| `python_tach` đã ghim | ✅ venv worker (`torch 2.11.0+cu128`) |
| khai của khuôn | *"Mọi pha đòi card đều được card — số giây đo SẢN PHẨM."* |

## Kết quả: `run.status = error` — và **khác** `NEN_V3`

| giai đoạn | trạng thái |
|---|---|
| `media_prepare` · `audio_prepare` · `transcribe` · `edit_plan` | ✅ succeeded |
| `content_process` | ⛔ `failed_terminal` · `ma_loi = "auto_match_thieu_can_cu"` |

Câu khách đọc: *"Chưa đủ căn cứ từ nội dung để tự khớp giọng. Hãy tự chọn một giọng."*

⭐ **Đi xa hơn `NEN_V3`.** Ở lượt nền, preset giữ hình **không chạy** `edit_plan`
(0,0 s) nên hồ sơ nội dung không bao giờ tồn tại. Nay `edit_plan` **succeeded** và
lượt LLM văn bản **đã chạy** (`ho_so_noi_dung`, 4.714 token). Tức bản vá R-01
(`679d8953`) **có tác dụng** — hai preset nay đi chung đường.

## ⛔ Vì sao vẫn chết — nguyên nhân ĐO ĐƯỢC, không phải giả thuyết

```
audio_prepare   f0_trung_vi = 0.0      stem_giu = [drums, bass, other]
transcribe      nguon_loi  = "ocr"     so_tu = 0     engine = rapidocr/PP-OCRv6
                dinh_tuyen = {che_do: auto, ly_do: ["khong_co_phu_de_nhung"]}
```

Hồ sơ giọng của AUTO_MATCH dựng từ **F0 của stem `vocals`**. Trên phim này
`f0_trung_vi = 0,0` — và đó **không phải một lỗi phép đo**: lời thoại của phim này
nằm ở **chữ trên hình** (`nguon_loi="ocr"`, `so_tu=0`), không phải ở tiếng nói.
**Không có tiếng nguồn nào để lấy đặc điểm giọng.**

⇒ Phát biểu đúng của lượt A **không phải** *"R-01 còn chết"* và cũng **không phải**
*"R-01 đã đóng"*, mà là:

> **AUTO_MATCH có một tiền đề CHƯA ĐƯỢC KHAI: nguồn phải có tiếng nói.** Phim
> lấy lời từ hardsub OCR thì tiền đề đó sai, và AUTO_MATCH không thể chạy —
> đúng về mặt logic, nhưng chưa ai viết nó ra ở đâu.

Xem `LOI_TONG.md` **N-06**.

## Sổ sách — đúng

`credit_da_giu = 14` → `hoan_lai = 14` · `da_quyet_toan = true` · `credit_da_tinh = 0`.
Khách không bị thu tiền cho một lượt không giao được hàng.

⭐ Và cửa lỗi hoạt động như G-04 đã sửa: **một mã ổn định**
(`ma_loi="auto_match_thieu_can_cu"`) + một câu khách đọc được + nút "Thử lại bước
này" bị ẩn (thử lại sẽ chắc chắn hỏng).

## Vòng sửa

Không có vòng nào chạy (lượt chết trước QC). Bảng bốn dòng: `0 → 0`,
`cau_khai = "khong co vong sua nao chay"`. ⛔ Lượt A **không** góp dữ liệu cho câu
hỏi 85→85 của N-02.

## Một câu hỏi lượt A mở ra, chưa trả lời

`edit_plan so_canh = 1` cho một phim 106,8 s (lượt B cũng `so_canh = 1`).
`NEN_V3` ghi 6 cảnh. Sau khi đổi bộ dò cảnh sang PySceneDetect (M-03b), phim này
ra **một** cảnh. Preset giữ hình không cắt nên nó vô hại ở đây — nhưng **lượt C**
(`smart_localize`) sẽ dựa vào chính con số đó. ⚠️ Ghi là **câu hỏi**, không phải
kết luận: một phim gameplay quay liên tục có thể thật sự chỉ có một cảnh.

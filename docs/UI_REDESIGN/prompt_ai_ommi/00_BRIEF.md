# H26.8 — Brief Prompt AI

## Đầu vào

- `PromptAIOmmi/MoTa.txt`: đổi tên public thành **Prompt AI**, chắt lọc thư viện
  Prompt Seedance và nâng giao diện theo ảnh.
- `PromptAIOmmi/GiaoDien.png`: dashboard Carbon Red có sidebar, chi phí, ô số,
  phân loại, dự án gần đây và activity.
- App live: slug `prompt_ai_ommi`, URL `/prompt-ai-ommi`, job
  `prompt_ai_ommi.generate`, 10 màn React và bảng `ommi_*` owner-scoped.
- Nguồn `D:\BOT GEMINI\app\modules\seedance`: chỉ đọc.

## Mục tiêu khóa

1. Đổi presentation thành **Prompt AI**, không đổi runtime contract.
2. Dùng hết chiều rộng immersive và biến Tổng quan thành dashboard dữ liệu thật.
3. Bổ sung catalog tích hợp có ích ngay cho user mới.
4. Giữ private-by-default; không có USD/team/shared owner hoặc dữ liệu giả.

## Không làm trong phase

- Không import code/runtime/database hoặc file user từ BOT GEMINI.
- Không đổi provider, worker, giá, job type, route hoặc bảng.
- Không chạy AI provider trong browser audit và không deploy trước H26.12.

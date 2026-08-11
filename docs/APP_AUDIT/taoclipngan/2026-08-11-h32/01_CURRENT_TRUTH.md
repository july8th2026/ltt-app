# H32.4 — Current truth: Tạo Clip ngắn

## Source và hành trình thật

- Source: H.264/AAC, 1920×1080, 30 fps, 265,202 giây, 523.893.381 byte.
- SHA-256 source:
  `B715A4EBA8276321CBC0202A466D2FA2019C20E138DA80D07AD372C766CEB2CD`.
- Upload thẳng browser → storage 523,9 MB pass; source xuất hiện lại trong thư
  viện và được tái sử dụng không upload lại.
- Ba job Fast × 1 clip đều giữ/quyết toán 28 credit. Số dư test lần lượt
  1.000 → 972 → 944 → 916, không rò giữ chỗ.
- Job CPU trước sửa mất khoảng 208 giây. Hai job venv CUDA sau sửa mất khoảng
  138 và 137 giây; GPU 0 từng đạt khoảng 5,2 GB trong phân tích.

## Output cuối đã pass

`20260811_taoclip_fast_talking-head_4x5_15814c05.mp4`

- 35.530.400 byte; SHA-256
  `C3921630416B77FD1B1907FC86EE72953C65EC6650876FB3C255D717188296A3`;
- H.264 `h264_nvenc`, 1080×1350, SAR 1:1, DAR 4:5, 30 fps;
- AAC stereo 44,1 kHz; 18,633 giây; ~15,25 Mbit/s;
- giải mã toàn file bằng FFmpeg: exit 0;
- frame 5 giây: crop giữ chủ thể, caption cháy rõ, không bị cắt.

Output `08643cba` là bằng chứng trước sửa: 1080×1920, SAR 64:45 để giả DAR 4:5.
Không dùng file đó làm bản nghiệm thu. Output 9:16 `dbef51fc` là bằng chứng trước
sửa NVENC và dùng libx264.

## Package

- ZIP chứa MP4, SRT, `package.json`, README.
- Sau sửa, SRT bắt đầu `00:00:00,000`, kết thúc không vượt 19,750 giây; bản cũ
  sai vì bắt đầu theo timeline nguồn ở 39,780 giây.
- File bàn giao ZIP đã được tạo lại với SHA-256
  `A2E6082CA8E0B5DFA929FE7BFFAB2BA443DA8C46397878B5FCD39C86724C9AC7`.

## Browser

- Desktop và mobile 390×844 pass; `scrollWidth == clientWidth == 375`.
- Console sau reload: 0 error, 0 warning; media range request 206 đúng.
- Negative security probe chủ ý trả 400/413 JSON; sau reload console trở lại 0.
- Progress mới tăng một chiều 2→5→…→58→62→97→100 với 26 mốc, thay vì hàng
  trăm activity và có lúc lùi 58→55.

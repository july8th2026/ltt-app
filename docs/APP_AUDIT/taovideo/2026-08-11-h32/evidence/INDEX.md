# Evidence index — H32.5 Seedance

| File | Nội dung |
|---|---|
| `seedance-baseline-desktop.png` | Desktop trước sửa, CTA dưới fold, toolbar cao |
| `seedance-baseline-mobile-library.png` | Mobile library trước sửa |
| `seedance-baseline-mobile-compose.png` | Mobile composer trước sửa, thiếu close rõ |
| `seedance-final-desktop-en.png` | Final EN 1.586×992, 4 state, quote dock |
| `seedance-final-mobile-compose-en.png` | Final EN 390×844, scroll/dock/close tách biệt |
| `seedance-updated-desktop-vi-assets.png` | VI, sidebar mở saved assets thật |
| `seedance-updated-empty-desktop-vi.png` | Empty state theo filter |
| `seedance-updated-mobile-library-vi.png` | VI mobile library, không overflow |

Hai file `seedance-updated-*.png` còn lại là checkpoint giữa vòng lặp visual;
không dùng thay bằng chứng final nếu có file `final-*` tương ứng.

Nguồn tham khảo ngoài repo:
`C:\Users\Thang Tuong\Desktop\AppLttStudio_11082026\TaoVideoSeedance\GiaoDien.png`,
1.606.722 byte, SHA-256
`D3F691FE996970BCC05C8263A643D47941AC0B292DBA06F15DB91E8984DA2032`.

MP4 trong fixture được đọc từ asset test của batch chỉ để browser nhận metadata
và request Range 206. Nó không phải output Seedance và không được đưa vào hồ sơ
kết quả AI.

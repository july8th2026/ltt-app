# L_GIONG_EN — giọng thuyết minh tiếng Anh cho AUTO_MATCH (F-03)

Làn `giong-en`, phiên `asv-final`, 22/09/2026. Nhánh `phien/asv-final-giong-en`.

## Kết luận trước

1. **Không cần tạo giọng mới.** Production **đã có** 17 giọng kho chung làn `en`
   (`dung_chung=True`, `license_status="ok"`, `active`, có biểu diễn). Khách đã thấy
   chúng trong bộ chọn LTT Voice từ 01/09 (`docs/LTT_VOICE/KHO_GIONG/00_KIEM_KE.md`).
   F-03 thật ra là **ASV không nhìn vào kho chung**, không phải "không có giọng".
2. Đã sửa phía ASV: `AUTO_MATCH` có tầng 2 đọc kho chung qua bề mặt khai của LTT Voice.
   Không mở thêm giọng nào cho khách, không đổi preset VieNeu, không đổi catalog/UI/API.
3. 🔴 **Còn MỘT việc dữ liệu cần chủ dự án quyết** (bên dưới): cột `VoiceProfile.gioi`
   của cả 25 giọng kho chung đang **rỗng**. `ung_vien_kho_chung` (cổng chung của LTT Voice)
   bỏ giọng chưa rõ giới ⇒ **trên production hôm nay, `en` + AUTO_MATCH vẫn `CHUA_RANG`**
   cho tới khi cột ấy được điền. Mã đúng; dữ liệu chưa.

## 1. Kho giọng dùng chung — tạo, lưu, làn, lộ ra

| câu hỏi | trả lời (nguồn) |
|---|---|
| Tạo | `tools/nhap_kho_giong_cu.py` (ghi danh qua sidecar, nhập 25 giọng kho cũ 01/09); bật chung `tools/dat_giong_dung_chung.py`; soát xuất xứ `tools/soat_giong.py duyet` (CLI, bắt buộc `--ly-do`) |
| Lưu | `VoiceProfile` (`public_id vc_<32hex>`, `ngon_ngu`, `gioi`, `dung_chung`, `license_status`) + `VoiceRepr` (`.npz` trong storage) — `apps/ltt_voice/tables.py` |
| Làn | `VoiceProfile.ngon_ngu`; chặn lệch làn ở `features._chot_lan` (Q121) |
| Lộ ra | `tham_chieu._dieu_kien_kho_chung()` = `dung_chung AND license_status∈("ok",)` — **một điều kiện** cho bộ chọn (`danh_sach(gom_dung_chung=True)`), cho quyền đọc (`tim_profile(cho_dung_chung=True)`) và cho đường lùi (`ung_vien_kho_chung`) |
| Chỉ nội bộ? | **Không có khái niệm đó.** Giọng dùng được cho khách khác ⇔ ở kho chung ⇔ khách thấy. Giọng `dung_chung=False` chỉ chủ của nó dùng được (`giai_giong` từ chối người khác). Một hạng "nội bộ" sẽ phải sửa cổng quyền của LTT Voice — không làm, và không cần. |

## 2. Nguồn clip / license

Không tải dataset nào (LibriTTS-R / VCTK / Hi-Fi TTS): 17 giọng `en` đã có đã qua soát
xuất xứ (`license_status="ok"` ghi bằng `soat_giong.py`), và thêm giọng mới cho khách
dùng được thì bắt buộc lộ ra (mục 1) — đúng điều brief cấm. Nguồn gốc 17 giọng:
`ghi_chu` JSON `{"nguon": "Voiceclone_TTS", "engine_cu": "xtts", "gioi": ..., "ma_cu": ...}`.

## 3. Đo — 17/17 giọng `en` kho chung, trên máy sinh tiếng THẬT

- Đường: `features.giai_giong` → `features.goi_cong` → sidecar VieNeu :8120 (production,
  tuần tự, 15–29 s/lượt). Chỉ đọc CSDL/kho.
- Kịch bản cố định (70 từ, sha256 `3c519cf99dd279cc…`): *"In the quiet hours before dawn,
  the old fisherman pushed his boat into the water. …belong to everyone else."*
- ASR: faster-whisper 1.2.1 `large-v3` (CPU int8, `language=en`, beam 5) — qua `chay_nang.py`.
- WER/CER: jiwer (lower + bỏ dấu câu). Độ to: ffmpeg `ebur128=peak=true` (Loại A).

| giọng | public_id | WER | CER | dài | từ/phút | LUFS-I | LRA | TP dBFS |
|---|---|---|---|---|---|---|---|---|
| **Douglas — nam, thuyết minh** | `vc_1b65a9e6…` | 0 | 0 | 24,1 | **171,8** | −19,6 | 3,0 | −3,9 |
| Marcus — nam, thuyết minh | `vc_f0a3c379…` | 0 | 0 | 25,3 | 163,6 | −20,7 | 2,8 | **−1,0** |
| Owen — nam, kể chuyện | `vc_526cb3ff…` | 0 | 0 | 23,1 | 179,5 | −19,5 | 2,5 | −2,7 |
| Adrian — nam, thuyết minh | `vc_b24b1aee…` | 0 | 0 | 22,3 | 185,3 | −20,0 | 2,6 | −3,3 |
| Miles — nam, mạng xã hội | `vc_633fcf57…` | 0 | 0 | 22,5 | 184,0 | −20,3 | 3,2 | −3,1 |
| Peter — nam, hội thoại | `vc_d2a0e1da…` | 0 | 0 | 22,5 | 184,0 | −19,7 | 3,3 | −1,2 |
| Nathan — nam, hội thoại | `vc_ad277664…` | 0 | 0 | 22,0 | 188,0 | −20,1 | 2,2 | −2,3 |
| Aaron — nam, phiêu lưu | `vc_aec13571…` | 0 | 0 | 20,8 | 198,8 | −19,0 | 1,9 | −2,6 |
| Julian — nam, thuyết minh | `vc_27af9b75…` | 0 | 0 | 20,6 | 201,2 | −18,2 | 2,0 | −1,0 |
| Robin — giải trí, biến hoá | `vc_b6679551…` | 0 | 0 | 20,5 | 202,0 | −20,3 | 1,4 | −4,5 |
| Ethan — nam, giảng bài | `vc_77d04fc5…` | 0 | 0 | 19,3 | 214,5 | −19,0 | 1,3 | −1,2 |
| Victor — nam, kể chuyện | `vc_c06352ee…` | 0 | 0 | 19,3 | 214,5 | −20,1 | 1,4 | −3,4 |
| Simon — nam, trang nghiêm | `vc_8a9ba87e…` | 0,029 | 0,003 | 19,3 | 214,5 | −21,7 | 3,0 | −1,0 |
| **Clara — nữ, thuyết minh** | `vc_a55b2ad1…` | 0 | 0 | 20,6 | **201,2** | −19,7 | 3,0 | −2,2 |
| Ivy — nữ, thuyết minh | `vc_62bedaf9…` | 0 | 0 | 20,3 | 204,3 | −19,4 | 1,9 | −2,8 |
| Lulu — nữ, hoạt hình | `vc_67071577…` | 0 | 0 | 18,7 | 221,9 | −20,5 | 1,7 | −3,7 |
| Nova — nữ, hoạt hình | `vc_704b9d21…` | 0,015 | 0,011 | 17,1 | 241,5 | −19,1 | 3,4 | −2,2 |

⚠️ **Độ đúng bão hoà**: 15/17 CER = 0 ⇒ CER không phân hạng được. Phân định bằng hai
số Loại A: nhịp gần mốc ~156 từ/phút mà `ngon_ngu.CUM["en"]` hứa với LLM, và dư đỉnh
(TP ≤ −2 dBFS). **Chọn 2**: Douglas (nam; Marcus nhịp gần hơn nhưng đỉnh chạm −1,0) và
Clara (nữ; nhịp gần hơn Ivy, dải động LRA 3,0 vs 1,9). Chưa có lượt **nghe bằng tai**
(tác tử không nghe được) — tệp wav ở scratchpad phiên, sinh lại được bằng đúng đường trên.
Kiểm kê 05/09 ghi DNSMOS của Clara (`bella_nu`) 3,184 — thấp *so với kho này* (dải 2,97–3,55).

## 4. Phía ASV (đã làm, commit trên nhánh)

- `apps/auto_scan_video/rang_giong.py` — `_rang_tu_khop` hai tầng:
  1. giọng mẫu của làn đích — **y nguyên**;
  2. **chỉ khi làn đích không có một giọng mẫu nào** (hôm nay: `en`) → `_rang_kho_chung`:
     lọc `ung_vien_kho_chung(db)` theo làn + **giới** (mặt duy nhất kho chung khai);
     thiếu giới / không có phiên CSDL / không ai khớp ⇒ `CHUA_RANG` (D-V4-04);
     sắp tất định: `UU_TIEN_KHO_CHUNG` (Douglas, Clara — theo số đo) rồi `public_id`;
     `vung`/`phong_cach` ghi vào `can_cu["mat_khong_ap_dung"]` thay vì giả vờ đã khớp.
- Bề mặt khai: `("apps.ltt_voice.tham_chieu", "ung_vien_kho_chung")` ở
  `apps/ltt_voice/__init__.py::BE_MAT_CONG_KHAI` **và** `tools/lint_app_contract.py::APP_DUOC_DUNG_APP`.
- USER_SELECTED không đổi (đã chặn lệch làn; giọng kho chung giải được qua `giai_giong`).
- Test: `tests/test_2095_asv_giong_en_kho_chung.py` (12 phép).

## 5. 🔴 Quyết định cần chủ dự án

**Điền `VoiceProfile.gioi` cho giọng kho chung từ giới đã KHAI trong xuất xứ (`ghi_chu.gioi`
của kho cũ).** 16/17 giọng `en` có giới khai rõ và tên hiển thị cùng nói giới; kiểm kê
05/09 đo F0 khớp 23/25. Ngoại lệ: **Robin** (`khanh_male_entertainment`, khai `male`
nhưng F0 220 Hz, tên không nói giới) — để trống tới khi nghe.

- Hệ quả thấy được với khách: bộ lọc giới ở bộ chọn LTT Voice sẽ **ẩn** các giọng này khi
  lọc giới kia (hôm nay "chưa rõ giới" ⇒ luôn hiện). Không thêm/bớt giọng nào khỏi danh sách.
- Hệ quả phụ tốt: đường lùi `lui_giong` của LTT Voice cho làn `en` bắt đầu có ứng viên
  (hôm nay cũng rỗng vì cùng lý do).
- Làn này **không** ghi CSDL production (chưa có công cụ ghi `gioi` cho kho chung; migration
  `20260907_1400_voice_gioi` cố ý không đoán hộ). Cần: một lệnh `soat_giong.py` kiểu
  `dat-gioi <public_id> nam|nu --ly-do ...` hoặc chủ dự án cho phép một lượt ghi một lần.

# 07 — RELEASE REPORT (2026-09-05)

## Nguyên nhân gốc — một câu

Mã nguồn đúng; **bản đang chạy là bản cũ**. `C:\LTTPlatform\app` giữ một bản chép
từ thời `master`, trong khi nhánh làm việc đã đi trước 94 commit — và không có
endpoint nào nói ra điều đó, nên câu hỏi chỉ trả lời được bằng cách so `md5sum`
hai thư mục bằng tay.

⛔ Không phải cache. Bằng chứng phân biệt: md5 của `/static/voice.js` mà máy chủ
**phục vụ** khớp **chính xác** bản trên đĩa ở thư mục deploy. Cache thì đĩa phải
mới mà phục vụ mới cũ; ở đây cả hai cùng cũ.

## Đã sửa — và bốn thứ trong đó KHÔNG phải triệu chứng ban đầu

| # | vấn đề | ai báo |
|---|---|---|
| 1 | bản deploy cũ 94 commit | ✅ triệu chứng ban đầu |
| 2 | không có cách hỏi bản đang chạy | ⛔ tìm ra khi điều tra (1) |
| 3 | JS đếm UTF-16, Python đếm điểm mã ⇒ `maxlength` cắt nhầm mọi bài có emoji | ⛔ tìm ra |
| 4 | nhập TXT cắt lặng lẽ phần đuôi | ⛔ tìm ra |
| 5 | sóng âm giải mã cả tệp ⇒ ~1,4 GB ở trần mới | ⛔ tìm ra |
| 6 | `100000` vs `100.000` trên cùng một luồng | ⛔ tìm ra |
| 7 | 236 dòng JS "Chạy lô" chết, gửi tới mọi khách | ⛔ tìm ra |

⭐ (3) là thứ đáng kể nhất trong nhóm tìm thêm: **50.001 emoji = 50.001 ký tự với
máy chủ nhưng 100.002 đơn vị mã với ô nhập**, nên trình duyệt cắt mất một nửa
một văn bản máy chủ hoàn toàn chấp nhận — không lỗi nào báo.

## Trần cuối cùng

| hằng số | giá trị | KHÔNG đổi trong lượt này |
|---|---|---|
| `TRAN_KY_TU_CONG_KHAI` | 100.000 | ✅ giữ nguyên |
| `TRAN_MOI_LUOT_SINH` | 1.500 | ✅ giữ nguyên |

⛔ Không hạ 100.000 và không nâng 1.500. Triệu chứng "giao diện hiện 1500" **không
phải** một vấn đề về hằng số; sửa hằng số để hết triệu chứng là sửa cái bóng.

## Tệp đã đổi

**Nền tảng**
- `platform_core/dau_van_tay.py` *(mới)* — bản đang chạy là bản nào
- `platform_core/dinh_dang.py` *(mới)* — `so_viet()`, một quy ước đọc số
- `server/routes/health.py` — `/health/version` trả dấu vân tay thật
- `server/templating.py` — filter `|so` gọi `dinh_dang.so_viet`
- `server/static/voice.js` — `demKyTu`, `soViet`, vượt trần, nhập TXT, `TRAN_GIAY_SONG`, `songDeu`; gỡ 236 dòng Chạy lô
- `server/static/ltt.css` (+ `tools/gui/ltt.css`) — `.vuot-tran`, `.lv-vuot`
- `setup/2-cai-dat.ps1` — ghi `dau_van_tay.json` bằng `Write-NoBom`

**App Voice**
- `templates/ltt_voice_studio.html` — gỡ `maxlength`, thêm `#lv-vuot`, filter `|so`
- `templates/ltt_voice_api.html` — filter `|so`
- `templates/_voice_chon.html`, `_voice_vo.html` — dọn residue Chạy lô
- `manifest.py` — NĂM tab (từ "SÁU"), kèm điều kiện tab thứ sáu được quay lại
- `routes/_chung.py`, `_p_tao.py`, `_p_du_an.py` — `so_viet` trong thông điệp lỗi
- `dieu_khoan.py`, `doc_man_api.py`, `doc_man_lich_su.py`, `du_an.py` — chú thích cũ

**Test / dịch**
- `tests/test_397_ltt_voice_bien_ky_tu.py` *(mới, 32)*
- `tests/test_398_dau_van_tay_ban_chay.py` *(mới, 7)*
- `locale/en/LC_MESSAGES/messages.po` + `.mo`

## Kết quả kiểm

Chi tiết ở `06_TEST_MATRIX.md`. Tóm tắt:

- **Biên**: 1.499 / 1.500 / **1.501** / 3.000 / 10.000 / 100.000 → nhận;
  100.001 → 400 với câu nói rõ. 1.501 ra **2 đoạn**, 100.000 ra **67 đoạn**.
- **Unicode**: 8 mẫu, ô đếm khớp `len()` của máy chủ ở **cả tám**; ba mẫu trong
  đó là ba mẫu bản cũ sai.
- **Nhập TXT**: tệp 100.051 ký tự có BOM + CRLF → BOM bỏ, **không cắt gì**, hai
  dòng báo đúng, nút Tạo tắt.
- **Bố cục**: 1920 / 1366 / 390 — không tràn ngang ở khổ nào; nút Tạo trong
  viewport ở cả ba.
- **Console**: 0 lỗi ngoài dự kiến.

## Trạng thái deploy

Xem `01_RELEASE_DRIFT.md` cho lập luận **vì sao deploy cả nhánh** thay vì
cherry-pick: chỉ cách đó mới khiến "mã đã QA" và "mã sẽ chạy" là cùng một cây.

Điều kiện tiền deploy (theo `deploy-copy-ca-cay-va-alembic-head`):

| điều kiện | trạng thái |
|---|---|
| cây sạch, mọi thay đổi là của phiên này | ✅ 25 tệp, tất cả của lượt này |
| `alembic heads` chỉ một đầu | ✅ `7d2c1e9f4a03` |
| lượt này KHÔNG thêm migration | ✅ |
| phiên khác đang ghi vào cây? | ✅ không — `git status` không có tệp lạ |
| gate đầy đủ | *(xem cuối tệp)* |

⛔ **Bước chạy script cần UAC, và đó là ranh giới của người dùng.**

```powershell
powershell -ExecutionPolicy Bypass -File .\setup\2-cai-dat.ps1
```

Sau khi chạy, xác minh bằng chính cơ chế lượt này dựng ra:

```bash
curl -s https://app.lttstudios.com/health/version
```

Phải thấy `commit` khớp `git rev-parse --short=12 HEAD`, và
`ltt_voice.tran_ky_tu_cong_khai` = 100000.

⚠️ Rồi mới chốt trên **URL công khai** theo quy tắc 5b: loopback bỏ qua
Cloudflare, nên trang có thể đẹp ở `127.0.0.1:8100` mà vỡ với khách thật. Kiểm ô
đếm hiện `100.000` trên `https://app.lttstudios.com/ltt-voice/`.

## Rủi ro còn lại — thật, không phải nghi thức

1. ⚠️ **Ngưỡng sóng âm dựa trên TÍNH TOÁN, không phải ĐO.** Lượt này không có
   sidecar GPU nên không sinh được bản thu dài để kích hoạt `TRAN_GIAY_SONG`.
   Số 96 KB/giây thì chắc (48.000 × 2 byte), phần nhân đôi khi giải mã là hành
   vi tài liệu hoá — nhưng đường `songDeu` **chưa chạy trên một tệp thật**.
2. ⚠️ **`/audio` đọc cả tệp vào RAM máy chủ** (`StreamingResponse(io.BytesIO(data))`).
   Một tệp 483 MB là 483 MB RSS mỗi lượt tải. Cùng lớp lỗi với (5) nhưng ở phía
   máy chủ; **chưa xử lý**, ngoài phạm vi lượt này.
3. ⚠️ **`soViet()` trong `voice.js` là bản sao thứ hai thật** của quy ước đọc số.
   Chưa có phép kiểm nào so nó với `platform_core/dinh_dang.py`.
4. ⚠️ **Dấu vân tay chỉ trả lời cho tiến trình web.** Worker và sidecar chạy tiến
   trình riêng, chưa khai gì; chúng có thể lệch sau một lần restart từng phần.
5. ⚠️ **Đường sinh tiếng đầu-cuối chưa chạy thật trong lượt này** (không có GPU).
   Ghép nhiều đoạn / quyết toán credit / dọn tệp dựa vào bộ test sẵn có, không
   dựa vào quan sát của lượt này.
6. ⚠️ **Ba phiên tương tác khác đang mở trên dự án này.** Deploy chép **cả cây**;
   nếu một phiên ghi vào `D:\LTTSTUDIOSAPP` giữa lúc commit và lúc deploy thì bản
   deploy sẽ mang theo việc dở dang của họ. Kiểm lại `git status` ngay trước khi
   bấm.

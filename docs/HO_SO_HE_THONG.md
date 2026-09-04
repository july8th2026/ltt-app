# Bộ hồ sơ hệ thống — ĐÃ GỠ 2026-09-04

⛔ **`ho_so_he_thong.txt` và `tools/build_system_profile.py` không còn tồn tại.**

Trang này giữ lại vì `docs/NHAT_KY.md` và `docs/PUBLIC_API/PROGRESS.md` còn trỏ
tới nó. Một liên kết chết dẫn người đọc đi tìm rồi tự đoán; một bia mộ nói thẳng
thứ đã mất và thay bằng gì thì không.

## Nó từng là gì

Một ảnh chụp **toàn cây**: bản đồ kiến trúc cộng nguyên văn source text, sinh
tự động, để người mới hoặc một phiên AI định vị code nhanh. `tools/gate.py` có
một bước `--check` chốt nó không được cũ, và `tests/test_177_system_profile.py`
chốt cùng điều đó.

## Vì sao gỡ

Chủ dự án quyết định 2026-09-04: không dùng nữa.

⭐ Và phép đo đứng về phía quyết định đó. Vì nó chụp **cả cây**, nó cũ đi sau
**mỗi** lần bất kỳ ai sửa bất kỳ tệp nào — kể cả một tệp không liên quan gì tới
nó. Hệ quả đo được trong ngày 03–04/09:

- Ba lượt `gate.py` đỏ **chỉ vì** hồ sơ cũ, không vì lỗi nào của sản phẩm. Mỗi
  lượt ~10 phút.
- Một lần merge giữa hai phiên xung đột ở **đúng một tệp**, và tệp đó là nó.
- Mọi phiên phải nhớ chạy lại nó trước khi commit — một bước thủ công mà việc
  quên **không** báo lỗi ngay, chỉ báo ở cuối một lượt gate mười phút sau.

⛔ Bài học chung, không riêng tệp này: **một hiện vật dẫn xuất từ TOÀN BỘ cây
thì mọi thay đổi đều làm nó bẩn.** Chi phí đó phải trả bằng giá trị nó tạo ra;
với một kho mà `grep` và `Glob` trả lời cùng câu hỏi trong nửa giây thì phép
tính không còn cân.

⚠️ Luật *"tệp dẫn xuất — người commit sau cùng mới sinh"* (`AGENTS.md` §10.7)
**vẫn còn nguyên**, vì `tools/gui/ltt.css` cũng chụp cả cây. Gỡ hồ sơ không gỡ
luật ấy.

## Thay bằng gì

Định vị code bằng chính mã nguồn: `grep` / `Glob` trên `apps/`, `platform_core/`,
`server/`. Nguồn chân lý vẫn là `docs/QUYET_DINH_NEN_TANG.md`, rồi
`docs/KE_HOACH_TRIEN_KHAI.md` và `docs/NHAT_KY.md`.

## Những gì đã gỡ theo

| Xoá | |
|---|---|
| `ho_so_he_thong.txt` | 16 MB |
| `tools/build_system_profile.py`, `tools/system_profile/`, `tools/system_profile_config.json` | bộ sinh |
| `tests/test_177_system_profile.py` | phép kiểm cho chính nó |

| Sửa | Vì sao |
|---|---|
| `tools/gate.py` | bỏ bước `system profile` |
| `tools/build_release.py` | hồ sơ nằm trong `REQUIRED_ENTRIES` — để nguyên thì mọi lần dựng gói phát hành đều đỏ vì một tệp không còn ai tạo |
| `tools/scan_source_secrets.py` | gỡ **cả** khai `EXCLUDED_FILE_NAMES` lẫn chỗ dùng — xoá một nửa là `NameError` ngay lần quét đầu |
| `tools/check_ky_tu_dieu_khien.py` | bỏ khỏi `BO_QUA` |
| `platform_core/public_api/governance.py` | bỏ mục `Store` |
| `tests/test_33`, `tests/test_44` | hai phép kiểm canh một sự loại trừ không còn tồn tại |
| `CLAUDE.md`, `AGENTS.md`, `docs/DEVELOPMENT_WORKFLOW.md` | các chỗ **bảo người đọc chạy** một lệnh đã mất |

⭐ Lịch sử git **không** bị viết lại. Tệp vẫn nằm trong các commit cũ; kho không
phình thêm, và một nhánh dùng chung với hai phiên khác thì không ai viết lại
lịch sử một mình được.

# Plan lắp ráp — thay tự suy bằng công cụ cộng đồng

> Lập 2026-09-06 sau khi chủ dự án chỉ ra: quá trình xây dựng **chậm** vì tự suy
> tự viết thay vì lắp ráp thứ đã có. Tài liệu này là **bảng hạng mục**, không
> phải một mục tiêu; mỗi dòng có công sức, lợi ích **đo được**, và rủi ro.

## 0. Bằng chứng — vì sao phải đổi cách làm

Đo trên chính máy này, không suy:

```
DA CAI SAN, KHONG CAU HINH, KHONG DUNG:
  ruff 0.15.9        1.149 loi tren apps/ platform_core/ server/ tools/
  mypy               khong co cau hinh nao
  pre-commit 4.5.1   khong co .pre-commit-config.yaml, khong hook nao
  import-linter      trong khi kho tu viet tools/lint_app_contract.py
  filelock           trong khi cua_so_yen tu viet O_EXCL + do PID + doat khoa treo
  portalocker        nt

KHONG CO TEP CAU HINH NAO:
  pyproject.toml · ruff.toml · .editorconfig · .gitattributes · pytest.ini
```

⭐ `ruff` tìm ra **2 lỗi trong `tools/do_nhanh.py`** — tệp vừa được viết ra để
*chống lỗi*, và vừa được commit. Công cụ ấy đã nằm sẵn trong máy suốt buổi.

🔴 Và trong 1.149 lỗi có **8 `F811 redefined-while-unused`** — đúng lớp lỗi đã
tốn một vòng kiểm tay ở `conftest.py` (nghi hai hàm cùng tên che nhau).

## 1. Phát hiện lớn nhất: **kiểm thử đột biến**

Suốt phiên 06/09, mỗi bánh cóc mới đều được chứng minh bằng tay:

```
tiem lai ban cu -> pytest -> doc returncode -> khoi phuc -> doi chieu sha256
```

Đó **chính là kiểm thử đột biến**, làm thủ công, mỗi lần ~2 phút, và mỗi lần đều
phải tự nhớ làm. `mutmut 3.7.0` và `cosmic-ray 8.7.0` tự động hoá đúng việc ấy —
sinh đột biến, chạy bộ test, báo đột biến nào **sống sót** (tức phép kiểm không
bắt được).

⇒ Nó biến câu hỏi *"phép kiểm này có đo đúng thứ cần đo không"* từ một **kỷ luật
phải nhớ** thành một **con số chạy được**. Đó là lớp C trong `AGENTS.md` §4d,
lớp đã cắn 4 lần trong một buổi.

⚠️ Nhưng nó **đắt về thời gian chạy**: mỗi đột biến là một lượt test. Với bộ
test 8 phút thì không thể chạy toàn kho. ⇒ Chỉ chạy trên **tệp vừa đổi**, và chỉ
ở lượt chốt — giống `diff-cover` chứ không giống gate.

## 2. Bảng hạng mục — hạ tầng

| # | Hạng mục | Đang làm | Lắp bằng | Công | Lợi ích đo được | Rủi ro |
|---|---|---|---|---|---|---|
| **H1** | Lint tĩnh | ≥4 bước gate viết tay | `ruff` *(đã cài)* | 1,5 h | 1.149 lỗi; 323 tự sửa | gate đỏ ngay ⇒ phải chốt mốc |
| **H2** | Mốc kết dòng | `check_xuong_dong.py` | `.editorconfig` + `.gitattributes` | 1 h | xoá **cả lớp** lỗi CRLF | `.gitattributes` sai làm **viết lại cả kho** |
| **H3** | Cổng trước commit | *không có* | `pre-commit 4.5.1` *(đã cài)* | 1 h | cưỡng chế lớp D | **`.git/hooks` dùng chung 4 worktree** |
| **H4** | Timeout test | 1 mốc **chết** | `pytest-timeout` | 20 ph | test treo sẽ **đỏ** thay vì treo | thêm phụ thuộc |
| **H5** | Khoá tệp | `cua_so_yen` tự viết | `filelock` *(đã cài)* làm lõi | 2 h | bỏ mã `O_EXCL` + doạt khoá treo | phải giữ phần khai tài nguyên |
| **H6** | Ranh giới kiến trúc | `lint_app_contract.py` | `import-linter` *(đã cài)* | 2 h | hợp đồng thành **cấu hình** | |
| **H7** | Kiểm thử đột biến | làm **tay** mỗi lần | `mutmut` / `cosmic-ray` | 3 h | tự động hoá lớp C | chậm ⇒ chỉ chạy trên diff |
| **H8** | Độ phủ theo diff | *không có* | `diff-cover` + `pytest-cov` *(đã cài)* | 1 h | biết dòng mới **chưa được phủ** | |
| **H9** | Kiểu tĩnh | *không có cấu hình* | `mypy` *(đã cài)* | 3 h | bắt lỗi hợp đồng hàm (lớp A) | nhiều lỗi cũ ⇒ chốt mốc |
| **H10** | a11y | bộ dò viết tay | `axe-playwright-python 0.1.8` | 3 h | chuẩn WCAG có bảo trì | giữ phần **tràn ngang** (axe không đo) |
| **H11** | Bảo mật | *không có* | `pip-audit 2.10` | 1 h | CVE trong phụ thuộc | `bandit` chỉ khai MacOS/Linux |
| **H12** | Phụ thuộc thừa/thiếu | *không có* | `deptry 0.25` | 1 h | | |

## 3. Bảng hạng mục — sản phẩm còn nợ

| # | Hạng mục | Trạng thái | Chặn bởi |
|---|---|---|---|
| **S1** | Safari thật · bàn phím ảo thật | `REAL_DEVICE=PENDING` | **thiết bị vật lý** — ~30 phút của chủ dự án |
| **S2** | `prompt_ai_ommi` view con | seed **đã có**, vỏ app đo sạch; view con là nút React không `href` | cần kịch bản điều hướng riêng |
| **S3** | Tải lại / nối lại job | không có provider `san_sang` trong môi trường đo | cần provider giả |
| **S4** | `reduced-motion` ở 4 app React | chưa đo | |
| **S5** | Copy IP/token `/vps`, `/developers` | chưa đo (VPS `enabled=False`) | |
| **S6** | Trạng thái loading/empty/error từng bề mặt | chưa đo có hệ thống | |
| **S7** | Trôi giữa kho chính ↔ kho worker | rủi ro tiềm ẩn, thuộc phiên VIDEO AI | |

## 4. Lộ trình — xếp theo *thứ chặn thứ khác*, không theo độ khó

```
Giai doan 1 — NEN (khong the lam sau)          ~3,5 h
   H4  pytest-timeout          20 ph   mot loi DANG SONG
   H2  .editorconfig           1 h     xoa mot LOP loi
   H1  ruff + moc              1,5 h   1.149 loi, va no soi moi thu lam sau

Giai doan 2 — DO DUOC (bien ky luat thanh con so)   ~7 h
   H8  diff-cover              1 h
   H7  mutation testing        3 h     tu dong hoa lop C
   H9  mypy + moc              3 h     bat lop A

Giai doan 3 — THAY LOI TU VIET                  ~7 h
   H5  filelock lam loi        2 h
   H6  import-linter           2 h
   H10 axe-core                3 h

Giai doan 4 — CAN QUYET DINH / CAN NGUOI
   H3  pre-commit              1 h     CHAM 4 worktree -> chu du an quyet
   S1  thiet bi that           30 ph   CHU DU AN, khong ai thay duoc
   H11 H12 S2..S7                      xep sau
```

⇒ **Giai đoạn 1 phải đi trước** vì `ruff`/`.editorconfig` soi mọi thứ làm sau
đó. Làm ngược lại là viết thêm mã rồi mới bật đèn.

## 5. Cái **KHÔNG** thay, và vì sao

⛔ Mỗi công cụ tự viết trong kho đều mang một tri thức mà **không thư viện nào
biết**:

```
"dung them cho nuot loi lang le qua moc 62"     <- lich su, khong phai luat chung
"khoa tai nhap theo PHIEN"                       <- mo hinh 4 phien cua kho nay
"buoc nang phai khai tai nguyen"                 <- hop dong rieng cua gate
"may 10 loi, moi phien dung chung"               <- rang buoc vat ly cua may nay
```

⇒ Kiến trúc đúng là **hai tầng**: thư viện lo 90% tổng quát, bánh cóc riêng lo
10% đặc thù. Thay trọn gói là mất đúng phần đắt nhất.

## 6. Ba điều cần chủ dự án quyết

1. **H3 chạm hạ tầng dùng chung.** `.git/hooks` dùng chung cho cả bốn worktree;
   bật `pre-commit` sẽ chặn ba phiên kia giữa chừng. Theo §4c câu 1, việc này
   không thuộc quyền một phiên.
2. **H1/H9 sẽ đỏ ngay lượt đầu.** Cách đúng là **chốt mốc** theo khuôn
   `check_bo_qua.moc` đã có, không sửa 1.149 lỗi một lần.
3. **Thứ tự sản phẩm vs hạ tầng.** Plan này làm mọi việc **sau đó** nhanh hơn;
   nó không tự đóng S1–S7. Muốn ưu tiên sản phẩm thì đảo lại.

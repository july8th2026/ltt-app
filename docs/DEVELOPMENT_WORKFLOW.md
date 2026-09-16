# QUY TRÌNH LÀM VIỆC — trang chỉ mục

> Tệp này **không định nghĩa quy trình**. Mỗi chủ đề có MỘT tệp chủ; ở đây chỉ có
> con trỏ, các lệnh `thanh_phan.py` và chỗ đọc bản ghi gate. Thấy một câu ở đây
> mâu thuẫn tệp chủ thì tệp chủ đúng — sửa câu ở đây thành con trỏ.

## Ai giữ luật nào

| Chủ đề | Tệp chủ |
|---|---|
| Vòng đời phiên, test/gate, git, commit, gộp `main`, khi nào dừng | `docs/00_LTT_OPERATING_CONTRACT.md` |
| Tạo worktree, kết thúc phiên, gộp `main` (thao tác) | `docs/QUY_TRINH_WORKTREE.md` |
| Lệnh nặng, khoá `cua_so_yen`, máy treo | `docs/QUY_TAC_CHAY_LENH_NANG.md` |
| Deploy, push GitHub, nghiệm thu sau deploy | `docs/16_CAP_NHAT_VA_DEPLOY.md` |
| Kỹ thuật Windows, bố cục app, tệp dùng chung khi hai phiên chung cây | `AGENTS.md` §5 · §8 · §10 |
| Hồ sơ `FAST_BUILD` — lệnh thao tác | `docs/OPERATING_STANDARDIZATION/FAST_BUILD_OPERATOR_GUIDE.md` |
| Một lượt đỏ mà bạn không đổi gì liên quan | hợp đồng §4.6 · `docs/BAY_TRONG_CONG_CHAT_LUONG.md` |

## Phạm vi đến từ đâu — `tools/thanh_phan.py`

Trả lời câu "thay đổi này chạm tới đâu" và "test nhắm của nó là tệp nào".

```powershell
python tools/thanh_phan.py                      # liệt kê thành phần
python tools/thanh_phan.py --doi                # cây hiện tại chạm tới đâu
python tools/thanh_phan.py --do-thi core:tien   # phụ thuộc + người tiêu thụ
python tools/thanh_phan.py --test app:vps       # tệp test của thành phần
```

**Ánh xạ test suy từ `import`, không từ tên tệp.** Đo trên kho này: `thumbnail`
có 2 tệp test mang tên nó nhưng 19 tệp *import* nó — chọn theo tên là bỏ qua
phần còn lại, im lặng.

### ⛔ Ba lớp phụ thuộc mà phép dò tĩnh KHÔNG thấy

Khai trong `tools/thanh_phan.toml` mục `[[canh_dong]]`:

| Lớp | Ví dụ | Còn gì để grep |
|---|---|---|
| dict tra bằng **chuỗi** | `GOI_TAI` phục vụ các tệp `sdk/` ở `/tai/<tên>` | một chuỗi |
| **import động** từ quét thư mục | `registry.py` nạp `apps/*/manifest.py` | tên thư mục |
| **quét thư mục + regex** | `_goi_moi_nhat()` chọn `data/api_dist/*.exe` mới nhất | **không gì cả** |

🔴 Lớp thứ ba nguy hiểm nhất: nội dung nằm trong `data/`, **ngoài git**. Thả một
tệp vào đó là đổi bề mặt công khai — không deploy, không commit, không dòng mã
nào đổi. ⇒ **Trước khi xoá bất cứ tệp nào**, đối chiếu với cả ba lớp.

## Bản ghi gate — `test-results/gates/<id>.json`

Mỗi lượt `gate.py` ghi một bản: SHA, nhánh, cây, hồ sơ, từng bước, thời gian,
thời gian chờ khoá. Đó là câu trả lời cho **"gate nào đã chạy trên mã nào"** —
không phải cuộn lại đầu ra đã mất khi đóng cửa sổ.

`test-results/` nằm trong `.gitignore` **và** trong `/XD` của deploy: không lên
git, không lên production.

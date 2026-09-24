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

## Bản ghi gate — `.gate/<id>.json`

Mỗi lượt `gate.py` ghi một bản: SHA, nhánh, cây, hồ sơ, từng bước, thời gian,
thời gian chờ khoá. Đó là câu trả lời cho **"gate nào đã chạy trên mã nào"** —
không phải cuộn lại đầu ra đã mất khi đóng cửa sổ.

`.gate/` nằm trong `.gitignore` **và** trong `/XD` của deploy: không lên git,
không lên production. Đường dẫn lấy qua `gate.thu_muc_so()`, ⛔ đừng gõ tay.

🔴 **Đổi chỗ 24/09/2026 — trước đó sổ nằm trong `test-results/gates/`.** Đêm
23–24/09 sổ phán quyết của một lô gate **biến mất** khỏi đó giữa hai lượt chạy, và
thủ phạm tới giờ **chưa biết** (ba giả thuyết đã bị loại bằng đo: `git clean -fdX`,
quét toàn máy, Playwright MCP/CLI). Điều **không** phụ thuộc vào thủ phạm là chỗ
đứng: `.gitignore` xếp `/test-results/` ngay dưới tiêu đề `# Playwright CLI temp` —
đó là thư mục **ra** của một công cụ khác, và bộ chạy test của Playwright *dọn sạch
`outputDir` ở đầu mỗi lượt* theo đúng tài liệu của nó.

⛔ Và mất sổ thì **không bao giờ đỏ**: `l3_lai_bi_chan` cố ý **cho qua** khi không
đọc được bản ghi, nên cái cửa "một L3 mỗi nhánh" mở ra **im lặng**. Sổ cũ vẫn được
**đọc** để chuyển giao êm, và đường đọc đó **tự hết hạn** — quá `CUA_SO_L3_LAI_GIO`
thì bản ghi cũ hết hiệu lực phán quyết nên chỗ cũ không còn đóng góp gì.
`tests/test_2170_*.py` chốt cả hai vế.

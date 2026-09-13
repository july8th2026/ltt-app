# QUY TRÌNH LÀM VIỆC — NHIỀU PHIÊN SONG SONG

> Tài liệu **hiện tại**, không phải lịch sử. Nếu một câu ở đây sai so với repo
> thì repo đúng — sửa tài liệu, đừng sửa repo cho khớp tài liệu.

Kho này thường có **ba phiên Claude/Codex chạy cùng lúc**. Tài liệu này nói mỗi
phiên phải làm gì để không giẫm lên nhau.

---

## 1. Bắt đầu một phiên — bốn lệnh

```powershell
python tools/cay_rieng.py liet-ke      # ai đang có cây riêng nào
python tools/cay_rieng.py tao <ten>    # cây + nhánh phien/<ten> cho riêng bạn
cd D:\LTTSTUDIOSAPP-<ten>
python tools/ho_so_cay.py trang-thai   # cây này ở hồ sơ nào, governance có cũ không
python tools/gate.py --doi             # mốc xuất phát, chỉ chạy phần liên quan
git rev-parse main                     # ghi BASE_SHA vào hồ sơ task
```

🔑 Một chiến dịch **dài** trong cây riêng có thể opt-in hồ sơ `FAST_BUILD` —
luật ở `docs/00_LTT_OPERATING_CONTRACT.md` §4.10, thao tác ở
`docs/OPERATING_STANDARDIZATION/FAST_BUILD_OPERATOR_GUIDE.md`.

⛔ **Không sửa code trên cây chính** khi có phiên khác đang chạy. Hai phiên cùng
`Write` một tệp thì bản sau đè bản trước, **im lặng**.

⚠️ **Thay đổi chưa commit KHÔNG đi theo** sang cây mới — `git worktree` phân
nhánh từ một *commit*. Lệnh `tao` in ra số tệp đang dở chính vì lý do đó.

---

## 2. Vòng làm việc

```
sửa  →  gate --doi  →  sửa  →  gate --doi  →  ...  →  gate (đầy đủ)  →  commit
```

🔑 **Bảng "cấp nào chứng minh gì" nay ở `docs/00_LTT_OPERATING_CONTRACT.md` §4** —
một chỗ duy nhất, cạnh giá **đo được** của từng cấp.

*(Tệp này từng giữ bảng đó, và bảng ấy **đúng** — nó là nguồn duy nhất đặt `--doi`
làm vòng lặp mặc định, trong khi `CLAUDE.md` và `AGENTS.md` bảo `--vong-lap`. Hợp
đồng canonical giữ lại lựa chọn của tệp này. Cái bỏ đi chỉ là **bản thứ hai** của
cùng một luật — và con số "~7 phút", vốn đã trôi: đo trên 43 lượt thật là 11,4.)*

---

## 3. Phạm vi đến từ đâu

`tools/thanh_phan.py` trả lời "thay đổi này chạm tới đâu".

```powershell
python tools/thanh_phan.py                      # 37 thành phần
python tools/thanh_phan.py --doi                # cây hiện tại chạm tới đâu
python tools/thanh_phan.py --do-thi core:tien   # phụ thuộc + người tiêu thụ
python tools/thanh_phan.py --test app:vps       # test nào sẽ chạy
```

**Ánh xạ test suy từ `import`, không từ tên tệp.** Đo trên kho này: `thumbnail`
có **2** tệp test mang tên nó nhưng **19** tệp *import* nó. Chọn theo tên là bỏ
qua 17 phép kiểm — im lặng.

### ⛔ Ba lớp phụ thuộc mà phép dò tĩnh KHÔNG thấy

Khai trong `tools/thanh_phan.toml` mục `[[canh_dong]]`, và đây là lý do mục ấy
tồn tại:

| Lớp | Ví dụ | Còn gì để grep |
|---|---|---|
| dict tra bằng **chuỗi** | `GOI_TAI` phục vụ 5 tệp `sdk/` ở `/tai/<tên>` | một chuỗi |
| **import động** từ quét thư mục | `registry.py` nạp `apps/*/manifest.py` | tên thư mục |
| **quét thư mục + regex** | `_goi_moi_nhat()` chọn `data/api_dist/*.exe` mới nhất | **không gì cả** |

🔴 Lớp thứ ba nguy hiểm nhất: nội dung nằm trong `data/`, **ngoài git**. Thả một
tệp vào đó là đổi bề mặt công khai — không deploy, không commit, không dòng mã
nào đổi.

⇒ **Trước khi xoá bất cứ tệp nào**, đối chiếu với cả ba lớp.

---

## 4. Tài nguyên — vì sao đôi khi phiên bạn phải đợi

Một số việc chỉ một lượt được chạy **trên cả máy**: bộ test lấy `-n auto` = mọi
lõi; CSDL test dùng chung; cổng 8100; GPU.

```powershell
python tools/cua_so_yen.py trang-thai   # ai đang giữ gì, từ bao giờ
python tools/cua_so_yen.py nha --ep --tai-nguyen cpu_nhieu   # gỡ MỘT khoá treo
```

⛔ **`nha --ep` không kèm `--tai-nguyen` gỡ TẤT CẢ khoá trên máy**, kể cả khoá
của một lượt gate đang chạy — `--ep` là đường vòng có chủ đích bỏ qua phép đối
chiếu chủ khoá. Gỡ **từng cái**, và chỉ khi `trang-thai` in `CANH BAO: TREO`.

⚠️ `pid` chủ khoá đã biến mất **không** có nghĩa khoá treo — nó có thể đang
**đổi chủ**. `cua_so_yen` tự đoạt khoá treo; không thấy `CANH BAO: TREO` thì
khoá còn hiệu lực. Toàn văn: `docs/QUY_TAC_CHAY_LENH_NANG.md`.

- Hai lượt cần **tài nguyên khác nhau** thì **không** đợi nhau.
- Chỉ lượt **đầy đủ / phạm vi** xếp hàng. `--vong-lap` và `--quick` thì không —
  chặn một vòng lặp ngắn sau một lượt 7 phút là giết đúng cái làm nó hữu dụng.
- Chờ quá hạn thì gate **vẫn chạy**, và nói rõ kết quả có thể bị nhiễu. Một cổng
  chất lượng từ chối chạy vì bận là một cổng không ai dùng.

---

## 5. Tệp dùng chung — quy tắc cứng

| Tệp | Cách chia |
|---|---|
| `server/static/ltt.css` | mỗi khu một **khối có nhãn** ở cuối tệp |
| `locale/en/LC_MESSAGES/messages.po` | **chỉ nối thêm cuối**, đọc lại ngay trước mỗi lần ghi. ⛔ Không chạy `i18n.py trich` |
| `server/templates/_kieu_chung.html`, `base.html` | **nhắn trước khi sửa** — chạm mọi trang của mọi app |
| `CLAUDE.md`, `AGENTS.md`, `tools/gate.py` | chỉ `Edit` khớp chuỗi chính xác |

⛔ **Tệp DẪN XUẤT — người commit SAU CÙNG mới sinh:** `tools/gui/ltt.css`
(`dong_goi_gui.py`) chụp **cả cây**. Sinh giữa chừng là commit một nửa việc
đang dở của phiên khác, dưới tên đợt của mình.

---

## 6. Kết thúc phiên

```powershell
python tools/gate.py                    # đầy đủ, trên cây đứng yên
git add <từng path của mình>            # KHÔNG `git add -A`
git diff --cached                       # kiểm không dính tệp phiên khác
git commit
```

Sau commit, yêu cầu cây sạch và trả handoff theo mẫu canonical ở
`docs/QUY_TRINH_WORKTREE.md` §5. Phiên task dừng tại `HANDOFF_READY_FINAL`:
không tự merge/rebase/push vào `main`, không tự xóa branch/worktree và không mở
feature mới. Canonical integrator nhận HEAD bất biến, review/integrate, chứng
nhận trên `main`, rồi mới retire theo ledger được duyệt.

Nếu `main` đã tiến sau `BASE_SHA`, ghi đúng divergence vào handoff; không tự
merge moving `main` chỉ để làm trạng thái trông mới hơn.

⛔ **Không deploy từ cây riêng.** Máy này LÀ production và deploy chép **cả
cây**. Chốt chặn nằm trong `setup/2-cai-dat.ps1`, được `test_362` giữ.

🔴 **Bất cứ thứ gì còn lại trong cây khi ai đó deploy đều lên production**, kể
cả tệp chưa theo dõi. Không có bước chọn lọc theo phiên. Ngoại lệ duy nhất là
danh sách `/XD` của robocopy (gồm `data secrets logs .git test-results tmp
node_modules …`).

---

## 7. Kết quả gate được lưu lại

Mỗi lượt ghi một bản ghi vào `test-results/gates/<id>.json`: SHA, nhánh, cây,
hồ sơ, từng bước, thời gian, thời gian chờ khoá.

Trả lời câu hỏi **"gate nào đã chạy trên mã nào"** — trước đây chỉ trả lời được
bằng cách cuộn lên đọc lại đầu ra, mà đầu ra thì mất khi đóng cửa sổ.

`test-results/` nằm trong `.gitignore` **và** trong `/XD` của deploy, nên nó
không lên git và không lên production.

---

## 8. Khi gate đỏ mà bạn không đổi gì liên quan

Ba nguyên nhân đã thật sự xảy ra, kiểm theo thứ tự này:

1. **Của phiên khác** — `git status` và `git log -1 -- <tệp>` **trước khi** đi
   sửa. Đã dính: bốn phép kiểm đỏ hoá ra do baseline của phiên kia.
3. **`CÂY ĐÃ ĐỔI TRONG LÚC CHẠY`** — gate tự in dòng này. Kết quả nói về cây lúc
   **bắt đầu**. Đừng trích nó làm bằng chứng.

Đọc `docs/BAY_TRONG_CONG_CHAT_LUONG.md` trước khi tin một dòng `RESULT: PASS`.

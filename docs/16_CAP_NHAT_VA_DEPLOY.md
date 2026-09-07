# Cập nhật, deploy và đẩy mã — quy trình cho MỌI phiên

Viết 04/09/2026, sau khi một phiên đi hết đường này và vấp đúng ba chỗ mà một
phiên khác cũng sẽ vấp.

⭐ **Dùng được từ bất kỳ worktree nào.** Xác thực git nằm ở Windows Credential
   Manager theo **tài khoản Windows**, và mọi phiên đều chạy dưới cùng một tài
   khoản — nên không phiên nào phải cấu hình thêm gì.

---

## 0. Ba sự thật phải biết trước

| | |
|---|---|
| Remote **duy nhất** | `origin` → `github.com/giaitritruyenthongltt-spec/LTTSTUDIOSAPP` (**riêng tư**) |
| Nhánh trunk | `admin-mvp-v3` |
| Remote nằm ở | `D:\LTTSTUDIOSAPP\.git\config` — **dùng chung cho mọi worktree** |

⛔ **`D:\LTTBackups` KHÔNG phải nơi để đẩy mã, và ACL chặn ở đó là CỐ Ý.**

Thư mục ấy chứa `app.env` và dump CSDL **mang bí mật thật**. Hạng mục **W1.5**
của `docs/AUDIT_MVP_2026-07-31.md` yêu cầu đúng điều đang thấy: *"thư mục backup
chỉ SYSTEM/Admin đọc"*. Remote `backup` trỏ vào đó **đã được gỡ 04/09**.

🔴 Nếu một phiên thấy `Access denied` ở `D:\LTTBackups` và định chạy `icacls` để
   "sửa": **đừng.** Đó là gỡ một bản vá bảo mật đã hoàn thành. Bản sao off-site
   nay là **GitHub riêng tư**.

---

## 1. Đồng bộ trước khi làm gì

```bash
git fetch origin
git merge --no-edit origin/admin-mvp-v3      # hoặc ff nếu chưa rẽ nhánh
```

⚠️ Xung đột hay gặp nhất là **hiện vật sinh ra** (bundle `server/static/*/assets`,
`build-meta.json`). Xử bằng cách **dựng lại**, không hoà tay từng dòng:

```bash
cd frontend/<app> && npm run build
```

---

## 2. Cổng chất lượng — và ba cái bẫy của chính nó

```bash
python tools/gate.py --vong-lap    # ~20s, sau MỖI lần sửa
python tools/gate.py               # TRƯỚC khi báo xong / deploy
```

🔴 **`RESULT: PASS` chưa chắc là bằng chứng.** Đọc cả dòng ngoặc vuông:

| Dòng kèm | Nghĩa |
|---|---|
| `[CAY DA DOI GIUA CHUNG - KHONG DUNG LAM BANG CHUNG]` | bạn sửa mã trong lúc gate chạy ⇒ **lượt đó vô giá trị**, chạy lại trên cây đứng yên |
| `[N BUOC TU BO QUA, KHONG PHAI BANG CHUNG: …]` | mấy bước đó **không chạy**, đừng tính là đã kiểm |
| `--vong-lap` / `--quick` | chính dòng `RESULT` của chúng nói nó không phải bằng chứng |

⭐ Trước khi deploy: `git status --porcelain` phải **rỗng**, rồi mới chạy gate.

### ⛔ `pre-commit` xanh là phát biểu về **3/29 bước**, không phải về gate

Đếm 07/09/2026:

```
tong buoc gate      29
co hook tuong ung    3     ruff · kieu xuong dong · ranh gioi import
KHONG co hook       26
```

⇒ Bốn dòng `Passed` sau mỗi `git commit` trả lời một câu **hẹp hơn nhiều** câu
  người ta đọc nó thành. Chúng phủ **~10%** cổng chất lượng.

**Ca thật, cùng ngày:** `tools/nghiem_thu_deploy.py` viết
`lech, thieu, thua, vi_du = 0, 0, 0, []`. `mypy` không suy được kiểu của `[]`
trong một phép gán nhiều đích ⇒ `var-annotated` **44 → 45** ⇒ vượt mốc bánh
cóc. Bốn hook **xanh hết**, và một dòng ấy làm đỏ **hai** bước gate:

```
[LOI] mypy
[LOI] bo test  ->  test_306::test_mypy_hien_tai_dat_moc
```

⭐ **Một nguyên nhân, hai triệu chứng.** Ai đọc bằng *kết quả* mà không đọc
   *nguyên nhân* sẽ đi sửa hai chỗ — và chỗ thứ hai không có gì để sửa.

**Thêm một tệp mới thì chạy trước khi commit** (vài giây, đổi lấy một vòng
gate 12 phút):

```bash
python -m mypy --config-file mypy.ini <tep moi>
python tools/check_i18n.py                 # neu tep co chuoi hien ra cho nguoi dung
python tools/check_dich_thieu.py
```

⛔ Và **đừng `--accept`** để nới mốc cho một chú thích kiểu còn thiếu: đó là
   trả một lỗi vĩnh viễn để mua lại một phút.

*(Danh sách trên không đầy đủ — không thể đầy đủ, vì 26 bước không có hook.
Mệnh đề đáng nhớ là chính con số: `pre-commit` không phải một bản gate thu
nhỏ, nó là **ba** phép kiểm chạy sớm.)*

### 2b. CVE trong phụ thuộc — chạy **trước deploy**, không chạy trong gate

```bash
python tools/check_cve.py
```

⛔ **Cố tình KHÔNG để trong `gate.py`.** Đo 06/09: **49 giây** và nó hỏi PyPI/OSV
qua mạng. Một bước gate đỏ vì **mất mạng** là một bước đỏ vì lý do không liên
quan tới mã — và đó chính là thứ dạy người ta bỏ qua màu đỏ (**Bẫy 26**).
CVE xuất hiện theo **thời gian**, không theo commit, nên hỏi một lần trước khi
giao hàng là đúng nhịp.

⚠️ **Hai con số khác nhau, đừng lứa lẫn.** Công cụ quét **spec** (`requirements*.txt`)
— tức *một lần cài mới sẽ nhận gì*. Muốn biết rủi ro **đang chạy** thì phải
quét venv sản phẩm:

```bash
C:/LTTPlatform/venv/Scripts/python.exe -m pip freeze > %TEMP%/prod.txt

# Bo 3 goi co hau to phien ban local (`+cu128`) — chung khong ton tai tren PyPI.
python - <<'PY'
import os, pathlib
p = pathlib.Path(os.environ["TEMP"])
dong = (p / "prod.txt").read_text(encoding="utf-8").splitlines()
loai = [d for d in dong if "+" in d.split("==")[-1]]
nl = chr(10)          # KHONG viet "\n" o day — xem chu thich duoi
(p / "prod_loc.txt").write_text(
    nl.join(d for d in dong if d not in loai) + nl, encoding="utf-8")
print("quet", len(dong) - len(loai), "| LOAI RA", len(loai), loai)
PY

python -m pip_audit --no-deps -r %TEMP%/prod_loc.txt
```

⛔ **`--no-deps` KHÔNG đủ, dù câu trước đây ở đây nói là đủ.** Đo 07/09/2026:
   với cờ ấy `pip-audit` **vẫn** cố giải `torch==2.11.0+cu128` và chết trước khi
   kiểm gì:

```
ERROR: Could not find a version that satisfies the requirement torch==2.11.0+cu128
ERROR:pip_audit._cli:Failed to install packages
```

   Phải **lọc bỏ** mọi dòng có hậu tố phiên bản local. Trên máy này là ba dòng:
   `torch`, `torchaudio`, `torchvision`.

🔴 **Hệ quả phải nói ra khi báo cáo con số.** Sau khi lọc, kết quả nói về
   **137/140** gói. Ba gói torch **không được kiểm** — không phải "sạch", mà là
   "không biết". Viết *"venv production: 6 lỗ"* mà không kèm mẫu số là biến một
   khoảng trống thành một lời bảo đảm.

⚠️ Đoạn trên dùng `chr(10)` chứ **không** viết `"\n"`, và đó là cố ý: công cụ
   Bash của agent **nuốt một lớp backslash** trên đường truyền, nên một đoạn
   copy nguyên si sẽ nhận `"n"` và ghi ra một tệp một dòng. Kho này đã dính bẫy
   ấy nhiều lần — gần nhất là một ký tự **BEL** lọt vào `KE_HOACH_TRIEN_KHAI.md`
   vì `\a` của `\app.env`.

### 2c. a11y (`axe-core`) — cũng chạy **trước deploy**, không trong gate

```bash
playwright-cli -s=a11y open --browser=chrome     # một lần
MSYS_NO_PATHCONV=1 python tools/check_a11y.py
```

⛔ **Không để trong `gate.py`**, cùng lý do với `check_cve.py`: nó cần **một máy
chủ đang phục vụ** và **một phiên trình duyệt đang mở**. Gate không dựng hai thứ
đó, nên một bước như vậy sẽ đỏ vì **thiếu phiên**, không phải vì mã — **Bẫy 26**.

⚠️ `MSYS_NO_PATHCONV=1` là **bắt buộc** trong Git Bash: thiếu nó, một route
`/` bị MSYS đổi thành `C:/Program Files/Git/` và buổi quét đi vào một URL vô
nghĩa.

⭐ Nó **không thay** `tools/mobile_quet.js`. `axe` không đo **tràn ngang**;
   `mobile_quet` không đo **tương phản màu**. Bỏ cái nào cũng mất một lớp.

---

## 3. Đưa lên trunk

```bash
git -C D:\LTTSTUDIOSAPP merge --ff-only <nhánh-của-bạn>
```

⛔ **Kiểm trước khi ff — production có gì mà nhánh bạn thiếu không?** Deploy chép
**cả cây**, nên một tệp chỉ có ở production sẽ bị xoá lặng lẽ:

```python
# đếm tệp .py chỉ có ở production, phải bằng 0
prod = pathlib.Path("C:/LTTPlatform/app")
for tm in ("apps", "platform_core", "server", "alembic",
           "render_gateway", "llm_gateway"):
    ...
```

---

## 4. Deploy máy A — hai lớp, và **phải** hai lớp

```powershell
Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass',
  '-File','"D:\LTTSTUDIOSAPP\setup\deploy_nang_quyen.ps1"' -Verb RunAs
```

Chủ dự án bấm UAC. Kết quả ghi ở `C:\LTTPlatform\logs\deploy-*.ket.txt`.

⛔ **`EXITCODE` RỖNG khác hẳn `EXITCODE=0`.** Rỗng nghĩa là tiến trình **chưa
   chạy xong** (hoặc chưa chạy). Đừng đọc tệp một lần rồi kết luận — đợi tới khi
   dòng `EXITCODE=` xuất hiện.

⛔ **`setup\2-cai-dat.ps1` TỪ CHỐI chạy từ một worktree.** Deploy chỉ đi từ cây
   chính `D:\LTTSTUDIOSAPP`. Đó là rào chắn đúng: deploy chép cả cây, nên chép từ
   một nhánh riêng là âm thầm đưa việc dở dang lên production.

### Nghiệm thu deploy — đối chiếu băm, đừng tin `EXITCODE`

```bash
python tools/nghiem_thu_deploy.py
```

Nó đọc `dau_van_tay.json` của bản đang chạy để biết máy chủ **khai** mình là
commit nào, rồi so từng tệp `.py` với `git show <sha>:<đường dẫn>`. Rồi
`curl https://app.lttstudios.com/health/ready` phải trả **200**.

⛔ **Đừng so với cây làm việc.** Đo 07/09/2026: cả hai phiên đều viết phép đo
   dạng `for p in (D:/LTTSTUDIOSAPP/server).rglob("*.py")` và nó báo **2 tệp
   lệch** ngay sau một lượt deploy **thành công** — deploy không hỏng, cây đã
   đổi *sau* lúc chép vì một phiên khác vừa commit.

   ⇒ Trong kho nhiều phiên, **cây làm việc không phải một mốc — nó là một mốc
     đang chuyển động.** Thứ duy nhất đứng yên là một commit.

🔴 Và chiều nguy hiểm không phải báo động giả. Là chiều ngược lại: deploy đi từ
   một cây **bẩn** thì phép đo "so với cây" báo **0 lệch**, trong khi máy chủ
   mang thứ không có trong commit nào. Vì vậy công cụ hỏi **cả ba chiều** —
   *lệch*, *thiếu*, và **thừa** (tệp trên máy chủ không có trong commit). Chỉ
   chiều thứ ba bắt được cây bẩn.

⭐ Có răng, kiểm hai chiều: đối chiếu với commit đang chạy → `0/0/0`; đối chiếu
   với commit **liền trước** → đúng **2** tệp lệch và gọi tên chúng.

### Ba mốc đọc được từ đĩa, không suy từ `git log`

| câu hỏi | đọc ở đâu |
|---|---|
| đang chạy bản nào | `curl /health/version`, hoặc `C:\LTTPlatform\app\dau_van_tay.json` |
| **đường lùi là bản nào** | `C:\LTTPlatform\app.previous\dau_van_tay.json` |
| lượt deploy nào, lúc nào | `C:\LTTPlatform\logs\deploy-*.ket.txt` |

⛔ `/health/version` **không** trả lời được câu thứ hai **sau khi đã deploy** —
   lúc đó nó chỉ nói về bản mới. Hỏi nó *sau* chỉ xác nhận việc mình vừa làm;
   nó không kiểm được giả định mình đã đi vào. Xem **Bẫy 30**.

---

## 5. Đẩy GitHub

```bash
git push origin admin-mvp-v3
git push origin <nhánh-của-bạn>
```

Điều kiện tiên quyết, chạy trước mỗi lần đẩy:

```bash
python tools/scan_source_secrets.py      # phải: Findings: 0
```

⭐ Đẩy **sau** khi deploy thành công, không phải trước: đẩy là hành động ra ngoài
   và khó rút lại, nên nó chỉ nên xảy ra khi bản mã ấy đã chứng minh chạy được.

---

## 6. Máy B — không đi qua đường này

Máy B (`render_gateway`, `llm_gateway`, ComfyUI, llama-swap) **không** nhận mã từ
`setup\2-cai-dat.ps1`. SSH ở đó đang `DISABLED` từ 27/08, nên đường duy nhất là
**Nexus** (`command.run`). Xem `docs/ANH_NOI_BO/DECISIONS.md` mục D-06x.

⛔ Hai điều đã trả giá để biết, đừng lặp lại:
- **nạp model đi cổng 8299** (`llm_gateway`), **không** cổng 8280 (llama-swap
  trực tiếp) — đi thẳng là bỏ qua `don_dep.py`, và hai model cùng lên card;
- `vram_ngoai_mb` là phần VRAM **NGOÀI** ComfyUI. Đọc nhầm chiều một lần là kết
  luận sai về ai đang giữ card.

---

## 7. Nhiều phiên cùng lúc

`git worktree list` cho thấy **8 cây**. Trước khi ff trunk hoặc deploy:

1. `git fetch origin && git log --oneline origin/admin-mvp-v3..HEAD` — xem mình
   đang mang gì;
2. `git log --oneline HEAD..origin/admin-mvp-v3` — xem phiên khác đã thêm gì;
3. nếu có, **merge về trước**, chạy gate trên cây đã hợp, rồi mới ff.

⭐ Và **nói với phiên kia** trước khi deploy nếu trunk vừa nhận việc của họ —
   deploy chép cả cây, nên bạn đang đưa mã của họ lên production cùng mã mình.

### 🔴 Cây chính là **bề mặt deploy của MỌI phiên** — giữ nó sạch kể cả khi bạn không deploy

`setup\2-cai-dat.ps1` **từ chối chạy từ worktree**, nên mọi lượt deploy — của
bất kỳ phiên nào — đều chép từ `D:\LTTSTUDIOSAPP`. Và `docs/` **có** trong bản
deploy (`C:\LTTPlatform\app\docs`).

⇒ Một tệp bạn đang sửa dở ở cây chính sẽ lên máy chủ trong lượt deploy của
  **người khác**, dù bạn chưa `git add` gì.

⛔ §2 có câu *"trước khi deploy, `git status --porcelain` phải rỗng"* — nhưng nó
   dặn **người deploy**, mà người deploy thường ngồi ở **worktree khác**. Người
   có khả năng làm bẩn cây chính lại là người **không** đọc dòng ấy, vì họ đâu
   có deploy. Một luật đặt sai người nhận thì coi như không tồn tại.

**Luật cho người ngồi ở cây chính:** khi một phiên khác sắp deploy, đưa cây về
sạch trước. Đã xảy ra 07/09 — hai tệp `.md` sửa dở suýt lên production trong
lượt deploy của phiên ChatLTT.

⚠️ Đừng mặc định `git stash` cho việc này: **`AGENTS.md` §10.3** xếp nó vào
   *"ba cái bẫy của cây dùng chung"* — nó **cuốn cả phần dở của phiên kia** vào
   stash của bạn. Chỉ an toàn khi bạn chắc mình là người duy nhất đang sửa cây
   ấy. Muốn một cây sạch để đo thì dựng riêng:

```bash
git worktree add --detach <tmp> HEAD
git worktree remove --force <tmp>
```

*(Hậu quả nếu bỏ qua **không** phải hỏng chức năng — `.md` không được phục vụ,
không được import, và phép đối chiếu băm chỉ soi `.py` + bundle. Cái hỏng là
mệnh đề **"bản đang chạy = một commit xác định"**, thứ mà `dau_van_tay.json`,
phép đối chiếu băm và `/health/version` cùng dựng lên. Xem **Bẫy 30**.)*

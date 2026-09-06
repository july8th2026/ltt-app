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
python -m pip_audit --no-deps -r %TEMP%/prod.txt
```

`--no-deps` là **bắt buộc**: freeze có `torch==...+cu128` không giải được trên
PyPI, thiếu cờ này `pip-audit` chết trước khi kiểm gì.

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

```python
# 0 tệp .py lệch trên cả 5 gói, và bundle khớp `source_sha256`
```

Rồi `curl https://app.lttstudios.com/health/ready` phải trả **200**.

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

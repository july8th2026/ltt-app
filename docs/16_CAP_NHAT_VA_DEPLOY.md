# Deploy, nghiệm thu và đẩy mã

> **Chủ của**: thao tác deploy máy A, nghiệm thu sau deploy, đẩy GitHub. *Điều kiện*
> (L3 xanh trên đúng SHA, ai deploy, không xin duyệt) thuộc
> `docs/00_LTT_OPERATING_CONTRACT.md` §7–§8, §10b — tệp này không chép lại nhịp.
> Gộp `main` trước khi deploy: `docs/QUY_TRINH_WORKTREE.md` §4.
> Chuyện kể các lần vấp (07/09 dòng `??`, pre-commit 3/29 bước):
> `docs/_luutru/16_CAP_NHAT_VA_DEPLOY_truoc_2026-09-16.md`.

**Ai deploy:** chính phiên vừa gộp `main` — làm rồi báo, không xin duyệt.

## 0. Sự thật nền

| | |
|---|---|
| Remote duy nhất | `origin` → `github.com/giaitritruyenthongltt-spec/LTTSTUDIOSAPP` (**riêng tư**) · cấu hình dùng chung mọi worktree · xác thực qua Windows Credential Manager |
| Trunk | `main` |
| Deploy đi từ | **cây chính** `D:\LTTSTUDIOSAPP` — `setup\2-cai-dat.ps1` **từ chối** chạy từ worktree |
| Deploy chép | **cả cây** (trừ danh sách `/XD` trong `setup\2-cai-dat.ps1`) — kể cả `docs/` và tệp chưa theo dõi |

⛔ `D:\LTTBackups` **không** phải nơi đẩy mã; ACL chặn ở đó là **cố ý** (W1.5) — đừng
`icacls`. Bản sao off-site là GitHub riêng tư.

## 1. Trước khi deploy

```bash
git -C D:\LTTSTUDIOSAPP status --porcelain    # phải RỖNG
```

- ⛔ **Một dòng `??` lạ là một PHIÊN KHÁC đang viết dở**, không phải rác — cho tới khi
  chứng minh ngược lại. Nó sẽ lên production nguyên trạng. Báo phiên đó, **không xoá**,
  không `stash`. `ListAgents` chỉ thấy phiên tồn tại **lúc hỏi**.
- **Báo** các phiên đang chạy rằng bạn sắp deploy (deploy chép cả cây, mang cả mã của
  họ đã vào `main`) — báo, không chờ.
- Có phán quyết xanh trên **đúng SHA** của `main` sắp deploy (hợp đồng §7).
- Migration: `main` mới có head alembic khác bản đang chạy? Đọc trước khi chép.
- Production có tệp mà `main` không có? Deploy chép cả cây nên tệp ấy bị **xoá lặng lẽ**
  — đối chiếu `C:\LTTPlatform\app` với cây trước khi chép.

Ba phép kiểm **cố ý không nằm trong gate** (cần mạng / máy chủ đang chạy / phiên trình
duyệt — đỏ vì môi trường là thứ dạy người ta bỏ qua màu đỏ):

```bash
python tools/scan_source_secrets.py        # Findings: 0 (gate cũng chạy)
python tools/check_cve.py                  # CVE theo requirements*.txt
MSYS_NO_PATHCONV=1 python tools/check_a11y.py   # cần: playwright-cli -s=a11y open --browser=chrome
```

⚠️ `check_cve.py` quét **spec**. Rủi ro **đang chạy** thì quét venv production:
`pip freeze` từ `C:/LTTPlatform/venv`, **lọc bỏ** các dòng có hậu tố local (`+cu128`),
rồi `python -m pip_audit --no-deps -r <tệp đã lọc>`. Báo cáo kèm **mẫu số** — gói bị lọc
là "không biết", không phải "sạch". `axe` không đo tràn ngang: vẫn cần `tools/mobile_quet.js`.

## 2. Deploy máy A

```powershell
Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass',
  '-File','"D:\LTTSTUDIOSAPP\setup\deploy_nang_quyen.ps1"' -Verb RunAs
```

Nâng quyền **im lặng** (`ConsentPromptBehaviorAdmin = 0`) — không có hộp UAC, không
cần ai bấm. Kết quả: `C:\LTTPlatform\logs\deploy-*.ket.txt`.

⛔ `EXITCODE` **rỗng** ≠ `EXITCODE=0`: rỗng là chưa xong. Đợi tới khi dòng xuất hiện.

## 3. Nghiệm thu — đối chiếu băm, đừng tin `EXITCODE`

```bash
python tools/nghiem_thu_deploy.py
curl https://app.lttstudios.com/health/ready     # 200
curl https://app.lttstudios.com/health/version   # đúng SHA vừa deploy
git -C D:\LTTSTUDIOSAPP status --porcelain       # đo LẠI sau robocopy
```

`nghiem_thu_deploy.py` đọc `dau_van_tay.json` của bản **đang chạy**, so **mọi tệp**
với `git show <sha>:<đường dẫn>` theo ba chiều *lệch / thiếu / thừa* (tệp vendor
chép riêng xếp nhóm `van_chuyen`). ⛔ Đừng tự so với **cây làm việc** — cây đang
chuyển động; chỉ commit đứng yên.

| Câu hỏi | Đọc ở đâu |
|---|---|
| đang chạy bản nào | `/health/version` · `C:\LTTPlatform\app\dau_van_tay.json` |
| đường lùi là bản nào | `C:\LTTPlatform\app.previous\dau_van_tay.json` (hỏi **trước** deploy) |
| lượt deploy nào, lúc nào | `C:\LTTPlatform\logs\deploy-*.ket.txt` |

Đổi giao diện ⇒ nghiệm thu trên trình duyệt ở URL công khai (hợp đồng §9).

📌 Nợ còn mở **D1**: `/XD` của robocopy lọc theo **tên thư mục**, không theo trạng
thái git — tệp chưa theo dõi ở thư mục ngoài danh sách vẫn lên production. Vì vậy
bước `status --porcelain` rỗng ở §1 là bắt buộc.

## 4. Đẩy GitHub

Sau khi deploy nghiệm thu xong (đẩy là hành động ra ngoài, khó rút lại):

```bash
python tools/scan_source_secrets.py      # Findings: 0
git push origin main
```

## 5. Máy B — không đi qua đường này

Máy B (`render_gateway`, `llm_gateway`, ComfyUI, llama-swap) **không** nhận mã từ
`setup\2-cai-dat.ps1`. Đường vào hiện hành: **đo**, đừng tin bản chép — memory
*máy B: đường vào* và `docs/ANH_NOI_BO/DECISIONS.md`.

⛔ Nạp model đi cổng **8299** (`llm_gateway`), không cổng 8280 (llama-swap trực tiếp) —
đi thẳng là bỏ qua `don_dep.py`, hai model cùng lên card. `vram_ngoai_mb` là VRAM
**ngoài** ComfyUI.

## 6. Cây chính là bề mặt deploy của MỌI phiên

Mọi lượt deploy chép từ `D:\LTTSTUDIOSAPP`, nên một tệp sửa dở ở cây chính lên máy
chủ trong lượt deploy của **người khác**. ⇒ Không làm việc dở ở cây chính; mỗi phiên
làm trong worktree riêng (hợp đồng §5). Cần một cây sạch để đo:
`git worktree add --detach <tmp> HEAD` — không `stash` cây dùng chung.

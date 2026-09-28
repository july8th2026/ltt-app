# Deploy, nghiệm thu và đẩy mã

> **Chủ của**: thao tác deploy máy A, nghiệm thu sau deploy, đẩy GitHub. *Điều kiện*
> (gate xanh trên đúng SHA — L1/L2 giữa phiên, L3 ở tổng kết phiên; ai deploy;
> không xin duyệt) thuộc
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
| Deploy chép | **bản xuất `git archive` của HEAD cây chính** (từ 08/09, `1e520ae0`) — mọi commit trên `main`, kể cả `docs/` — cộng danh sách vận chuyển `$VAN_CHUYEN` (tệp gitignored production đọc lúc chạy: `apps\*\vendor`, `yolov8n.pt`). Tệp chưa commit **không** lên. Không đọc được commit ⇒ đường lùi chép cây sống (script in cảnh báo) |

⛔ `D:\LTTBackups` **không** phải nơi đẩy mã; ACL chặn ở đó là **cố ý** (W1.5) — đừng
`icacls`. Bản sao off-site là GitHub riêng tư.

## 1. Trước khi deploy

```bash
git -C D:\LTTSTUDIOSAPP status --porcelain    # phải RỖNG
```

- ⛔ **Một dòng `??` lạ là một PHIÊN KHÁC đang viết dở**, không phải rác — cho tới khi
  chứng minh ngược lại. Bản xuất chỉ mang commit nên nó không lên production — trừ khi
  nằm trong `$VAN_CHUYEN` hoặc deploy rơi về đường lùi chép cây sống. Báo phiên đó,
  **không xoá**, không `stash`. `ListAgents` chỉ thấy phiên tồn tại **lúc hỏi**.
- **Báo** các phiên đang chạy rằng bạn sắp deploy (deploy xuất HEAD cây chính, mang cả
  mã của họ đã vào `main`, và khởi động lại dịch vụ) — báo, không chờ.
- Có **gate xanh** trên **đúng SHA** của `main` sắp deploy (hợp đồng §8): giữa phiên
  L1 `gate.py --doi --tu <sha bản đang chạy>` hoặc L2 `--pham-vi <tp>[,<tp>…]` (một lượt cho mọi thành phần chạm); tổng kết phiên L3
  (xanh/đỏ đã khép). ⛔ Không chạy L3 chỉ để deploy; test nhắm một mình không đủ.
- Migration: `main` mới có head alembic khác bản đang chạy? Đọc trước khi chép.
- Production có tệp mà `main` không có? `app\` bị thay toàn bộ bằng bản xuất nên tệp ấy
  bị **xoá lặng lẽ** (trừ `$VAN_CHUYEN`) — đối chiếu `C:\LTTPlatform\app` với commit
  trước khi chép.

### 🔴 Luật này có HAI vế, và vế thứ hai thiếu cho tới 28/09/2026

Câu *"deploy xuất HEAD cây chính ⇒ **báo** các phiên đang chạy trước"* dạy người
**deploy** phải báo. Nó ⛔ **không** dạy người **gộp** phải giữ. Nên nó đọc như đã
đủ, trong khi một nửa cơ chế không tồn tại.

⇒ Vế còn lại, nay là luật:

| ai | làm gì |
|---|---|
| người sắp **gộp `main`** khi biết có phiên đang deploy | **GIỮ LẠI**, ⛔ không gộp cho tới khi bên kia nói đã `git archive` xong |
| người **deploy** | **nhắn một dòng ngay khi `archive` xong** — ⛔ không chờ tới lúc nghiệm thu xong, và ⛔ không để bên kia tự đoán |

🔴 **Vì sao thiếu vế ấy là một lỗ IM LẶNG, ⛔ không phải một bất tiện.** Nếu một
phiên gộp `main` giữa lúc `git archive` chưa chạy, bản deploy mang theo mã **chưa**
nằm trong lượt gate — và ⛔ **không phép kiểm nào trong kho bắt được**:
`nghiem_thu_deploy.py` so bản đang chạy với **một** commit, nên nó vẫn báo *"khớp
tuyệt đối một commit xác định"*. Chỉ là một commit **khác** commit mà gate đã xem.

⭐ Ca thật 28/09: phiên `Auto Scan Video` có ba làn xong, **sẵn sàng gộp**, và tự
giữ lại vì đọc ra chiều thiếu. Nếu họ gộp, tôi đã deploy một SHA chưa bao giờ được
phán quyết, và cả hai phía đều thấy màu xanh.

⚠️ Cùng họ với việc chạy lại `ai_dang_dung_may_chu.py` **ngay trước** `archive`
thay vì tin phép đo lúc chiều: chỗ hở luôn là **khoảng cách giữa lúc đo và lúc
dùng** — ở đây là giữa **lúc gate phán quyết** và **lúc `archive` chụp cây**.

### ⚠️ `main` đi trước production thì GHI khoảng lệch ra

Sau deploy, `main` thường tiếp tục nhận commit. Điều đó bình thường — nhưng
*"lệch bao nhiêu, và lệch ở đâu"* phải nói được, nếu không lần deploy sau ⛔ không
ai biết mình đang mang gì lên.

```bash
SHA=$(curl -s https://app.lttstudios.com/health/version | python -c "import json,sys; print(json.load(sys.stdin)['commit'])")
git -C D:\LTTSTUDIOSAPP log --oneline "$SHA..main"
git -C D:\LTTSTUDIOSAPP diff --name-only "$SHA..main" | sort -u
```

⇒ Nếu mọi commit trong khoảng ấy chỉ chạm `tests/` · `docs/` · `tools/` thì ⛔
**không** cần deploy lại — nhưng hãy **nói ra** là mình đã kiểm, chứ đừng im lặng.

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

📌 Nợ **D1** (`/XD` của robocopy lọc theo tên thư mục, không theo trạng thái git) chỉ
còn ở **đường lùi** chép cây sống — đường chính chép bản xuất commit. Vì vậy bước
`status --porcelain` rỗng ở §1 vẫn giữ.

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

Mọi lượt deploy xuất HEAD của `D:\LTTSTUDIOSAPP`, nên một commit dở trên cây chính
(hoặc tệp sửa dở, nếu rơi về đường lùi) lên máy chủ trong lượt deploy của **người
khác**. ⇒ Không làm việc dở ở cây chính; mỗi phiên
làm trong worktree riêng (hợp đồng §5). Cần một cây sạch để đo:
`git worktree add --detach <tmp> HEAD` — không `stash` cây dùng chung.

### ⚠️ Báo phiên khác trước khi deploy: cơ chế hiện có KHÔNG tin được (đo 23/09/2026)

Hợp đồng bắt **báo các phiên đang chạy trước khi deploy** (`ListAgents`). Đo thật ngày 23/09:
**5/5 tin nhắn liên phiên bị giữ chờ người nhận duyệt và không bao giờ tới Claude bên kia** —
hai tin hỏi phiên VGA về máy B, một tin yêu cầu bản fork dừng tay, và hai tin báo trước deploy
lần này. Tin bị giữ vì phiên nhận chạy ở chế độ quyền khác; chủ phiên phải bấm duyệt, mà không
ai ngồi nhìn.

⇒ **Gửi tin là làm cho có, không phải là đã báo.** Đừng coi "đã gửi" là đã thoả luật.

Ba đường thay thế, theo thứ tự đáng tin:

1. **Hỏi chủ dự án** — người duy nhất thấy được mọi phiên. Một câu trước khi bấm.
2. **Đọc trạng thái thay cho hỏi**: `python tools/cua_so_yen.py trang-thai` cho biết phiên nào
   đang giữ khoá nặng; `git log --oneline -20` cho biết ai vừa gộp gì vào `main`. Cái này
   **không cần ai trả lời**.
3. Gửi tin — vẫn nên gửi, nhưng **không chờ**, và không tính là đã báo.

**Cập nhật 23/09 khuya — mẫu lên 7/7.** Lượt deploy `458f7c64` gửi thêm hai tin (một tin nhắc
phiên đang giữ khoá 47 phút, một tin báo trước deploy): **cả hai đều hết hạn mà không tới nơi**.
Bảy trên bảy trong một ngày. Đây không còn là "có thể không tới" mà là **đường không dùng được**.

⇒ **Điều kiện an toàn thật phải là CƠ HỌC, không phải giao ước.** Lượt deploy này dựa vào hai thứ
không cần ai trả lời:

```bash
git status --porcelain      # RỖNG = không có việc dở của ai để cuốn nhầm
python tools/nghiem_thu_deploy.py   # lệch 0 / thiếu 0 / thừa 0 = khớp tuyệt đối một commit
```

Cái thứ nhất chặn **trước** khi bấm, cái thứ hai chứng minh **sau** khi bấm. Hai phép này đã đủ
làm việc mà giao ước "báo nhau" định làm — và chúng luôn trả lời, kể cả lúc 23 giờ không ai online.

Lượt deploy 23/09 21:00 đi tiếp sau khi hai tin bị giữ: nghiệm thu băm 1 157 tệp lệch 0, nên
không ai bị ảnh hưởng — nhưng đó là may, không phải quy trình.

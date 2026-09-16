# Quy trình worktree — tạo, làm, gộp `main`, gỡ

> **Chủ của**: thao tác tạo worktree, chuẩn bị cây, kết thúc phiên và gộp `main`.
> *Khi nào* chạy test/gate và *điều kiện* gộp `main` thuộc
> `docs/00_LTT_OPERATING_CONTRACT.md` (§4, §7) — tệp này không chép lại.
> Lịch sử vì sao có quy trình này (máy treo 03/09, ba bản `gate.py`):
> `docs/BAY_TRONG_CONG_CHAT_LUONG.md`.

## 1. Tạo cây — mỗi phiên ghi code một worktree riêng sinh từ `main`

Phiên mở bằng app Claude đã đứng sẵn trong một worktree riêng (`.claude/worktrees/…`)
— dùng luôn. Tự tạo thì:

```powershell
python tools\cay_rieng.py tao <ten>      # D:\LTTSTUDIOSAPP-<ten>, nhánh phien/<ten>, từ main
```

Ghi `BASE_SHA` ngay — **SHA**, không phải tên nhánh đang di chuyển:

```powershell
git rev-parse main
git merge-base --is-ancestor main HEAD   # mã khác 0 = cây không sinh từ main -> dừng, đối chiếu
```

⚠️ Thay đổi **chưa commit** không đi theo sang cây mới — worktree phân nhánh từ commit.

## 2. Chuẩn bị cây — tài sản bị gitignore chỉ có ở cây chính

Một vài thứ test cần (nhị phân `vendor`, model) không nằm trong git. Đừng chép
theo bảng — **hỏi cây chính**:

```powershell
git -C D:\LTTSTUDIOSAPP status --ignored --porcelain |
  Where-Object { $_ -like '!!*' -and $_ -notlike '*__pycache__*' -and $_ -notlike '*desktop.ini*' }
```

Chép từng mục sang cây mới (`robocopy <nguồn> <đích> /E` cho thư mục). Thiếu chúng
thì vài test đỏ với thông điệp **không nhắc gì tới worktree** — người đọc đi tìm lỗi
trong mã.

### Sau khi gộp `main` có XOÁ app: dọn thư mục ma

`git` theo dõi tệp, không theo dõi thư mục: app đã xoá vẫn để lại `apps/<app>/` chứa
`__pycache__`, và vài test/lint đỏ vì "thư mục không có manifest".

```powershell
git clean -ndX apps/     # xem trước
git clean -fdX apps/     # xoá thật
```

🔴 `git clean -fdX apps/` **xoá luôn tài sản gitignore ở mục 2** (`apps/*/vendor`).
Chạy xong thì chép lại ngay. ⛔ Đừng hạ mốc `ruff`/`mypy` theo con số giảm sau khi
dọn — cây chưa dọn sẽ đỏ.

## 3. Trong lúc làm

- Test/gate: hợp đồng §4. Lệnh nặng: hợp đồng §4.8.
- Không ghi vào cây của mình khi nó đang chạy gate (hợp đồng §4.9).
- Commit checkpoint thoải mái trên nhánh phiên (`git add` tường minh).

## 4. Kết thúc phiên — gộp `main`

Điều kiện (hợp đồng §7): cây sạch · **giữa phiên** test nhắm xanh (+ L1/L2 khi thay
đổi lan nhiều thành phần), ⛔ không L3 · **gộp để deploy giữa phiên** L1/L2 xanh trên
đúng SHA · **tổng kết phiên** L3 của phiên xanh hoặc đỏ đã khép. **Chính phiên làm việc gộp `main`** — không bàn giao cho ai.

```powershell
# a) main đã đi tiếp kể từ BASE_SHA chưa?
git rev-list --count <BASE_SHA>..main

# b) CHƯA (0): fast-forward cây chính tới nhánh của bạn
git -C D:\LTTSTUDIOSAPP status --porcelain          # xem cây chính có việc dở của ai
git -C D:\LTTSTUDIOSAPP merge --ff-only <nhánh-của-bạn>

# c) ĐÃ đi tiếp: hoà main vào nhánh của bạn, phán quyết chỗ gặp nhau, rồi ff
git merge main
#   giữa phiên : test nhắm chỗ gặp nhau (L1 `gate.py --doi --tu <sha trước khi hoà>` nếu cần)
#   tổng kết   :
python tools\gate.py --doi --tu <sha lượt L3>
git -C D:\LTTSTUDIOSAPP merge --ff-only <nhánh-của-bạn>
```

⛔ **Cây chính `D:\LTTSTUDIOSAPP` có thể mang thay đổi chưa commit của phiên khác.**
`merge --ff-only` tự từ chối nếu nó phải ghi đè chúng — khi đó **dừng** (hợp đồng
§10 mục 1–2): báo phiên đang giữ cây chính, không `stash`, không `checkout --`,
không ép. Gộp lại khi họ đã commit.

Xung đột khi hoà: giải theo **ngữ nghĩa** (ai gọi, runtime, test), không chọn cả tệp
`--ours/--theirs`. Tệp **sinh ra** (vd `tools/gui/ltt.css`) thì sinh lại trên cây đã
hoà — `AGENTS.md` §10.

Sau khi `main` đã nhận: đẩy `origin` và deploy nếu phạm vi cần —
`docs/16_CAP_NHAT_VA_DEPLOY.md`.

### Báo cáo kết phiên

```text
PHIEN_XONG
WORKTREE / BRANCH:
BASE_SHA:
SHA_L3 + KET_QUA:            (và SHA lượt khép/hoà nếu có)
MAIN_SAU_GOP:                 (git rev-parse main)
DEPLOY:                       (SHA đã deploy + /health/version, hoặc "không cần")
RUI_RO_CON_LAI:
```

Ghi các dòng này vào `docs/NHAT_KY.md` cùng lượt.

## 5. Gỡ cây

Chỉ gỡ cây **của mình** khi nhánh đã nằm trong `main`
(`git merge-base --is-ancestor <nhánh> main` trả 0). ⚠️ `git worktree remove` xoá
luôn thứ gitignore bên trong (tài sản đã chép, dữ liệu đo) — lấy ra trước nếu cần.
Không gỡ cây của phiên khác, kể cả khi nó trông bỏ hoang.

Sau một lần máy treo: hộp đen — `docs/QUY_TAC_CHAY_LENH_NANG.md`.

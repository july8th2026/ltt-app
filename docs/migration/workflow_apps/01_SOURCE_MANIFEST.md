# 01 — SOURCE MANIFEST

Bản khai nguồn của chương trình *4 bot → 4 App + Macro Node*.
Đo **2026-09-09 15:20 (UTC+7)**.

⚠️ SHA ở đây là **ảnh chụp lúc bắt đầu**, không phải một cam kết rằng nhánh
đứng yên. Mỗi phase ghi lại SHA thật của lúc nó chạy.

## Nền tảng đích

| Mục | Giá trị |
|---|---|
| Repo | `https://github.com/giaitritruyenthongltt-spec/LTTSTUDIOSAPP` |
| Trunk | `admin-mvp-v3` |
| SHA lúc bắt đầu | `05464239980c25de4cb316755efd41b27da7ddce` |
| Ngày commit | 2026-09-09 14:43:25 +0700 |
| Cây làm việc | `D:\LTTSTUDIOSAPP\.claude\worktrees\ltt-4bot-workflow-app-550cab` |
| Nhánh | `claude/ltt-4bot-workflow-app-550cab` |
| Dải số test được cấp | **1100–1199** (số cao nhất đang dùng trên **mọi** cây: 1004) |

⭐ SHA `990179106f7e80a554f28c41c4745488fb17bbd8` mà prompt pack ghi làm mốc tham
chiếu **vẫn nằm trên trunk** — trunk đã đi thêm 2 commit kể từ đó.

## Bốn repo bot — trong phạm vi

Đo bằng `git ls-remote` (kho riêng tư; truy cập qua credential helper của máy —
API công khai trả `Not Found`).

| Bot | Repo | Nhánh | SHA đầu nhánh 2026-09-09 |
|---|---|---|---|
| Transcript | `giaitritruyenthongltt-spec/bot_transcript` | `main` | `278ed8d7cd27ef1ae07f14eb74e106b0035fcf03` |
| Pause | `giaitritruyenthongltt-spec/bot_pause` | `main` | `97a021a1d6d85453c6b5b751a570b3067a1bb928` |
| GEM | `giaitritruyenthongltt-spec/bot_gem` | `master` | `0bc47735d8ff67aaae7dbbfbdf66851bf9d8c4c7` |
| Video Assembly | `giaitritruyenthongltt-spec/bot_dungvideo` | `main` | `b0e25ed4b8be60e895dcb5787276095fbfae6836` |

`bot_gem` còn một nhánh nữa: `tich-hop-ltt-llm` = `8f1bb40b…`. **Ngoài phạm vi
mặc định** — audit ở phase 04 phải nói rõ nhánh nào là nguồn chân lý trước khi
dùng nó.

`auto-bot`: **ngoài phạm vi**, theo START-HERE §1.

### Bản sao nghiên cứu — đặt ở đâu

`D:\LTT_4BOT_LAB\<repo>` — **ngoài** cây LTT.

🔴 Không clone vào trong `D:\LTTSTUDIOSAPP` dù chỉ tạm. Bản cài chép **cả cây**
bằng `robocopy`, kể cả tệp chưa theo dõi, và danh sách loại trừ không có tên
nào trong đó. Một thư mục "để tạm rồi dọn" là một thư mục sẽ lên máy chủ.

### Điểm vào runtime

| Bot | Điểm vào | Trạng thái |
|---|---|---|
| Transcript | | CHƯA ĐO — phase 02 |
| Pause | | CHƯA ĐO — phase 03 |
| GEM | | CHƯA ĐO — phase 04 |
| Video Assembly | | CHƯA ĐO — phase 05 |

⛔ Bốn ô trống ở trên là **UNKNOWN**, và MASTER-GUARDRAILS cấm biến UNKNOWN
thành một quyết định thiết kế. Chúng được điền bằng cách đọc mã, không bằng cách
đọc README.

## Kiến trúc đích — bất biến

```
APP ─ GUI ─┐
    ─ Node ─┼→ CÙNG service ─→ CÙNG job ─→ hàng đợi → worker → engine → artifact
    ─ API ──┘
```

`GUI result = Node result = API result`, vì cả ba đi qua **một** service và
**một** job handler. App không tự dựng hàng đợi, scheduler, sổ credit, trọng tài
GPU, vòng lặp polling, khung retry hay máy trạng thái riêng.

Hợp đồng app: `docs/03_THEM_APP_MOI.md` · `AGENTS.md` §8.

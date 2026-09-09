# Bảng tiếp nhận governance — 10 cây làm việc

> **Đo 2026-09-09 15:12, trunk `admin-mvp-v3` = `05464239`.**
> Bảng này là một **ảnh chụp**, không phải nguồn chân lý. Hỏi lại bằng
> `python tools\ho_so_cay.py trang-thai` ở chính cây bạn đang đứng.

⛔ **Không cây nào bị sửa để làm ra bảng này.** Mọi phép đo là đọc: `git status
--no-optional-locks`, `rev-list --count`, `rev-parse <ref>:<tệp>`. Không
`reset`, không `stash`, không `checkout` — hợp đồng §5 và §10.

| Cây | Nhánh | HEAD | Đang dở | Thiếu commit trunk | Governance | Hồ sơ | Việc an toàn tiếp theo |
|---|---|---|---:|---:|---|---|---|
| `D:\LTTSTUDIOSAPP` | `admin-mvp-v3` | `05464239` | 0 | 0 | khớp | `NORMAL` (bắt buộc) | không làm gì — đây là cây deploy |
| `.claude\worktrees\auto-scan-video-v4-mvp-7173d9` | `claude/ltt-voice-98-upgrade-9b586f` | `99017910` | 8 | 2 | khớp | `NORMAL` | **đang có phiên** — để chủ cây tự quyết |
| `.claude\worktrees\chatltt-v3-agentic` | `claude/chatltt-v3-agentic` | `139cb1d1` | 0 | 263 | **lệch**: contract · `gate.py` · `thanh_phan.py` | `NORMAL` | sạch & rỗi ⇒ chủ cây `git merge admin-mvp-v3` khi quay lại |
| `.claude\worktrees\ltt-4bot-workflow-app-550cab` | `claude/ltt-4bot-workflow-app-550cab` | `05464239` | 8 | 0 | khớp | **`FAST_BUILD`** sau Phase 00 | cây của chiến dịch 4-bot |
| `.claude\worktrees\ltt-llm-api-http-guide-a3e123` | `claude/ltt-llm-master-upgrade-ddcfc9` | `99017910` | 37 | 2 | khớp | `NORMAL` | **đang có phiên** — không đụng |
| `.claude\worktrees\ltt-video-architecture-recovery-746b24` | `claude/ltt-video-architecture-recovery-746b24` | `a8bd684e` | 17 | 2 | khớp | `NORMAL` | **đang có phiên** — không đụng |
| `.claude\worktrees\video-v2-wangp` | `phien/video-v2-wangp` | `f19b072d` | 0 | 42 | **lệch**: contract · `gate.py` · `thanh_phan.py` | `NORMAL` | sạch & rỗi ⇒ gộp trunk khi có chủ |
| `D:\LTTSTUDIOSAPP-aiclean` | `phien/aiclean` | `ac46d371` | 0 | 5 | **lệch**: `gate.py` | `NORMAL` | sạch & rỗi ⇒ gộp trunk khi có chủ |
| `D:\LTTSTUDIOSAPP-wf2` | `phien/wf2` | `0d1ffe5a` | 0 | 24 | **lệch**: `gate.py` | `NORMAL` | sạch & rỗi ⇒ gộp trunk khi có chủ |
| `D:\LTTSTUDIOSAPP_RELEASE_H42` | `h42-release-clean` | `b4adf873` | 0 | 960 | **lệch**: contract · `gate.py` · `thanh_phan.py` · quy trình worktree | `NORMAL` (nhánh phát hành) | **cố ý đứng yên** — cây phát hành đóng băng, đừng gộp trunk vào |

## Đọc bảng này thế nào

**"Đang dở" > 0 ⇒ có người.** Không phải rác. Hợp đồng §5: một dòng `??` lạ là
một phiên khác đang làm việc. Bốn cây có việc dở lúc đo, và `ListAgents` cùng
lúc đó thấy **4 phiên khác** đang chạy.

**"Đang dở" = 0 ⇒ *không* chứng minh là không có người.** Memory *hai phiên cùng
cây* đã đo được một phiên im 4 giờ 39 phút mà vẫn sống. Vì vậy cột cuối của bốn
cây sạch ghi *"khi có chủ"* chứ không ghi *"làm ngay"*.

**Lệch governance ≠ hỏng.** Nó có nghĩa: một lượt gate ở cây đó chạy một cổng
chất lượng **khác** cổng ở trunk. Với `H42_RELEASE` thì lệch là **đúng** — đó là
một cây phát hành đã đóng băng, và gộp trunk vào nó là làm hỏng chính thứ nó giữ.

## Việc còn lại cho phiên sau

Bốn cây sạch (`chatltt-v3-agentic`, `video-v2-wangp`, `aiclean`, `wf2`) cần đúng
một lệnh, **do chủ cây chạy**, không do phiên này:

```powershell
git -C <đường-dẫn-cây> merge admin-mvp-v3
```

Phiên này **không** chạy hộ. Lý do không phải sự lịch sự: một lệnh `merge` vào
cây người khác có thể xung đột, và người phải giải xung đột đó lại không phải
người gây ra nó.

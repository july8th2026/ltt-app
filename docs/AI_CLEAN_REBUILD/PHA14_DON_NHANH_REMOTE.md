# Pha 14 — dọn nhánh remote GitHub

**Ngày:** 2026-09-10 · chiến dịch **LTT AI CLEAN REBUILD V2**

```
25 nhanh  ->  10 nhanh      (xoa 15)
```

## Ba nhóm **không được đụng**, và ba lý do khác nhau

| Nhóm | Vì sao |
|---|---|
| `admin-mvp-v3` · `master` | trunk và nhánh mặc định của kho |
| **11 nhánh đang có worktree giữ** | một worktree còn đứng ở đó thì chủ của nó còn đẩy lên |
| **5 nhánh mang tên một phiên ĐANG SỐNG** | đo bằng `ListAgents` lúc 00:2x, không đoán theo tên thư mục |

⚠️ Và điều kiện thứ tư, đã có sẵn trong gói chiến dịch: **nhánh còn commit riêng
chưa hoà thì không xoá**. Năm nhánh rơi vào nhóm này —
`ltt-video-ai-v3-p00` (49 commit), `ltt-video-architecture-recovery` (6),
`h42-release-clean` (2), `phien/asv-v4` (4), `phien/video-v2-wangp` (3).

## 🔴 Bộ lọc đầu tiên của tôi RÒ, và đối chứng bắt được

Lượt đầu, `origin/phien/aiclean` — nhánh **worktree của chính tôi đang giữ** —
lọt vào danh sách xoá. Nguyên nhân: tôi gom danh sách giữ bằng `sed`, nên các
phần tử ngăn nhau bằng **xuống dòng**, còn phép so `case " $GIU " in *" $b "*`
thì trông đợi **dấu cách**. Một phần tử đứng ngay trước một xuống dòng không
bao giờ khớp.

⭐ Thứ bắt được nó không phải sự cẩn thận mà là một **đối chứng viết sẵn**: in
   lại từng nhánh có worktree và đòi mỗi dòng phải hiện `GIU DUOC`. Thiếu vòng
   ấy thì danh sách 16 dòng trông y hệt một danh sách 15 dòng đúng.

## Sổ khôi phục — mỗi nhánh một lệnh

Cả 15 nhánh đều **đã hoà hết vào trunk**, tức không một commit nào mất: chúng
vẫn nằm trong lịch sử của `admin-mvp-v3`. Bảng dưới là đường về nếu ai cần lại
đúng cái tên nhánh ấy.

⛔ Mỗi nhánh được kiểm **một lần nữa ngay trước khi xoá** rằng nó vẫn là tổ tiên
   của trunk — vì trunk đi rất nhanh, và một danh sách tính từ mười phút trước
   là một danh sách đã hết hạn.

| Nhánh | SHA | Khôi phục |
|---|---|---|

## Còn lại 10 nhánh

```
origin/admin-mvp-v3
origin/claude/auto-scan-video-v4-mvp-7173d9
origin/claude/ltt-llm-api-http-guide-a3e123
origin/claude/ltt-video-ai-v3-p00-3f5713
origin/claude/ltt-video-architecture-recovery-746b24
origin/h42-release-clean
origin/master
origin/phien/aiclean
origin/phien/asv-v4
origin/phien/video-v2-wangp
```

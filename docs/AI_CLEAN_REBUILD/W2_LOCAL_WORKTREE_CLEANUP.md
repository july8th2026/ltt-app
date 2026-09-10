# W2 — LOCAL WORKTREE CLEANUP

> **Pha:** W2 · **Đo lúc:** 2026-09-08 17:00 · **Cây ghi:** `phien/aiclean`
> Không `rm -rf`. Không xoá nhánh remote (đó là pha 14).

## 1. Cây chiến dịch — ĐÃ TẠO

```
tools/cay_rieng.py tao aiclean
  ->  D:\LTTSTUDIOSAPP-aiclean      nhanh phien/aiclean      ghim 0d1ffe5a
  dai test cua cay nay: 1000-1099   (cao nhat dang dung tren MOI cay: 962)
```

### ⚠️ Cố ý lệch khỏi pack: tên nhánh là `phien/aiclean`, không phải `architecture/ai-clean-rebuild`

Pack đề nghị `architecture/ai-clean-rebuild`. Kho này **đã có** một quy trình
đặt tên và một công cụ cưỡng chế nó: `tools/cay_rieng.py` chỉ sinh
`phien/<tên>` + `D:/LTTSTUDIOSAPP-<tên>`. `CLAUDE.md` luật 2 nói thẳng: *"Đừng
tự sáng tạo quy trình… đừng đẻ ra một luật cạnh tranh."*

⇒ Quy ước kho **thắng** tên gọi của một pack bên ngoài. `phien/aiclean` **LÀ**
nhánh chiến dịch mà pack gọi là `architecture/ai-clean-rebuild`.

### Ba thứ dùng công cụ mới có, `git worktree add` trần thì không

1. **Chép tệp gitignored mà gate đòi** — `apps/upscalevideo/vendor` (48 MB) và
   `yolov8n.pt`. Git không giữ chúng; một `git worktree add` trần cho ra một cây
   mà `upscalevideo` **chết im lặng**.
2. **Cấp dải test 1000–1099**, tra trên **mọi** cây ⇒ không đụng dải phiên khác.
3. **In ra 43 tệp đang dở** của cây chính thay vì im lặng tạo một cây thiếu việc.

⛔ **Không deploy từ cây này.** Chốt chặn thật nằm ở `setup/2-cai-dat.ps1`
(đòi `.git` là **thư mục**, không phải **tệp**), giữ bởi `test_362`.

## 2. Phân loại 8 cây

| # | Cây | Nhánh | Phân loại | Vì sao |
|---|---|---|---|---|
| 1 | `D:/LTTSTUDIOSAPP` | `admin-mvp-v3` | **KEEP** | Cây chính. Deploy chỉ chạy từ đây. 43 tệp dở + 2 phiên sống |
| 2 | `D:/LTTSTUDIOSAPP-aiclean` | `phien/aiclean` | **KEEP** | Cây chiến dịch này |
| 3 | `D:/LTTSTUDIOSAPP-wf2` | `phien/wf2` | **BLOCKED** | Phiên WF2 sống (commit 16:56). Sạch, nhưng đang dùng |
| 4 | `.claude/worktrees/auto-scan-video-v4-mvp-7173d9` | `phien/asv-v4` | **BLOCKED** | Phiên ASV GUI V5 sống (chủ dự án xác nhận) + 33 tệp dở |
| 5 | `.claude/worktrees/video-v2-wangp` | `phien/video-v2-wangp` | **BLOCKED** | Phiên sống |
| 6 | `.claude/worktrees/chatltt-v3-agentic` | `claude/chatltt-v3-agentic` | **ARCHIVE_THEN_REMOVE** *(chờ xác nhận)* | Sạch, 0 unpushed, không nhịp ghi 6h |
| 7 | `.claude/worktrees/ltt-llm-api-http-guide-a3e123` | detached `989353c2` | **ARCHIVE_THEN_REMOVE** *(chờ xác nhận)* | Sạch, tip = `origin/claude/ltt-video-ai-v3-p00-3f5713`, 339 sau master |
| 8 | `D:/LTTSTUDIOSAPP_RELEASE_H42` | `h42-release-clean` | **ARCHIVE_THEN_REMOVE** *(chờ xác nhận)* | Sạch, 672 sau master, ảnh chụp phát hành |

### ⛔ Ba cây #6–#8 KHÔNG được gỡ trong pha này, dù đủ điều kiện `REMOVE_SAFE` trên giấy

`GIT_WORKTREE_REMOTE_POLICY.md` cho `REMOVE_SAFE` khi: không phiên active ·
sạch · không unique commit chưa bảo toàn · không phải trunk/campaign. Cả ba cây
thoả **bốn** điều kiện đo được. Nhưng điều kiện đầu — *"không phiên active"* —
**không phải một thứ đo được**:

⭐ **W0 đã ăn đúng cái bẫy này.** Cây `asv-v4` im **4 giờ 39 phút**,
`find -newermt '-2 hours'` ra **0**, và tôi xếp nó *"chưa kết luận"*. Chủ dự án
cho biết phiên ASV GUI V5 **đang chạy**. Nhịp ghi tệp chứng minh được **sự CÓ
MẶT**, không bao giờ chứng minh **sự VẮNG MẶT**: một phiên đang đọc mã, đang chờ
người, hay đang chạy một lượt gate 12 phút đều ghi ra đúng con số 0 ấy.

⇒ **Một cây chỉ được coi là không có phiên khi chủ dự án nói thế.** Ba cây trên
chờ một câu xác nhận, không chờ thêm một phép đo — không có phép đo nào trả lời
được câu đó.

⚠️ Và `git worktree remove` **xoá âm thầm thứ bị gitignore** trong cây đó
(vendor, model, `test-results/`). Trước khi gỡ bất kỳ cây nào: kiểm tệp
gitignored có giá trị, không chỉ kiểm `git status`.

## 3. Nhánh local không có cây

| Nhánh | Tip | Unpushed | Ghi chú |
|---|---|---|---|
| `master` | `9e73bf1f` | 0 | trunk — **không đụng** |
| `phien/asv` | `706faca5` | 0 | tổ tiên của `phien/asv-v4` |
| `phien/mobile-v1` | `c43d7880` | 0 | — |
| `claude/ltt-video-ai-v3-p00-3f5713` | `989353c2` | 0 | V3 đã DỪNG 06/09, thay bằng V2.1 |

Cả bốn đã có trên `origin` ⇒ không có gì để bảo toàn. **Không xoá nhánh nào ở
pha này** — remote hygiene là pha 14, và nhánh local thì không cản trở gì.

## 4. Gate W2

| Điều kiện | Kết quả | Bằng chứng |
|---|---|---|
| `UNKNOWN_UNIQUE_COMMITS` | **0** | 6 commit chưa push, cả 6 quy được chủ (W1 §2) |
| `READY_FOR_00` | **YES** | Cây chiến dịch tồn tại, nền ghim `0d1ffe5a` |
| Không `rm -rf` trước | ✅ | 0 lệnh xoá |
| Không xoá nhánh remote | ✅ | 0 lệnh — để pha 14 |

**W2 GATE = PASS**, với **3 cây chuyển tiếp** (`ARCHIVE_THEN_REMOVE`, chờ chủ dự
án xác nhận không còn phiên). Việc gỡ chúng **không chặn** pha 00–13: chúng chỉ
chiếm chỗ đĩa, không cản một dòng mã nào.

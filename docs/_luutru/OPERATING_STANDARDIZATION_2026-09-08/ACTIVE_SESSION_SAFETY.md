# ACTIVE SESSION SAFETY — chiến dịch OPERATING STANDARDIZATION

> Chụp lúc **2026-09-08**, đầu chiến dịch. Đây là ảnh chụp, nên nó cũ đi.
> Trước khi tin một dòng nào, chạy lại `git worktree list --porcelain`.

## Cây của chiến dịch này

| | |
|---|---|
| Worktree | `D:\LTTSTUDIOSAPP` (cây chính) |
| Nhánh | `admin-mvp-v3` |
| HEAD lúc bắt đầu | `637878cf` |
| Phiên | `lttstudiosapp-32 [3e9e3e]` |

⛔ **Cây chính KHÔNG phải cây riêng của chiến dịch này.** Nó là bề mặt deploy
của mọi phiên. Chiến dịch chỉ chạm vào tệp luật vận hành, không chạm mã sản phẩm.

## Cây đang sống — KHÔNG gỡ, KHÔNG reset, KHÔNG đổi nhánh

| Worktree | Nhánh | HEAD |
|---|---|---|
| `.claude/worktrees/auto-scan-video-v4-mvp-7173d9` | `phien/asv-v4` | `9d7f7044` |
| `.claude/worktrees/chatltt-v3-agentic` | `claude/chatltt-v3-agentic` | `139cb1d1` |
| `.claude/worktrees/ltt-llm-api-http-guide-a3e123` | *(detached)* | `989353c2` |
| `.claude/worktrees/video-v2-wangp` | `phien/video-v2-wangp` | `1ccfb0b1` |
| `D:\LTTSTUDIOSAPP_RELEASE_H42` | `h42-release-clean` | `b4adf873` |

`ListAgents` lúc bắt đầu thấy **4 phiên bạn** còn sống: `lttstudiosapp-00`,
`lttstudiosapp-83`, `lttstudiosapp-f1`, `lttstudiosapp-6e`.

⚠️ `ListAgents` chỉ thấy phiên **tồn tại lúc hỏi**. Một phiên mở sau đó không có
trong bảng này, và một dòng `??` lạ trong `git status` vẫn là một phiên khác đang
làm việc chứ không phải rác.

## ⛔ Việc dở của phiên KHÁC trong CHÍNH cây này

Cây chính đang bẩn, và **không phải bẩn vì chiến dịch này**. Có một phiên khác
đang làm LTT VOICE ngay trên `admin-mvp-v3`:

```
 M apps/ltt_voice/gia.py                     M server/static/voice.js
 M apps/ltt_voice/manifest.py                M tests/test_500_ltt_voice_nghe_thu.py
 M apps/ltt_voice/nghe_thu.py                M tests/test_501_ltt_voice_hong_hoc.py
 M apps/ltt_voice/routes/_p_tao.py           M tests/test_504_ltt_voice_be_mat_sidecar.py
 M apps/ltt_voice/sidecar_client.py          M docs/LTT_VOICE/DECISIONS.md
 M apps/ltt_voice/templates/ltt_voice_studio.html
 M apps/ltt_voice/vo.py
?? apps/ltt_voice/ho_so_giong.json          ?? tests/test_506_ho_so_giong.py
?? apps/ltt_voice/ho_so_giong.py            ?? tools/do_ho_so_giong.py
```

**Luật cho chiến dịch này:**

- Không `git stash`, không `git checkout --`, không `git reset` — kể cả `--soft`.
- Không commit gộp. Commit của chiến dịch chỉ được liệt kê **đúng tệp của nó**.
- Không chạy `gate.py` đầy đủ mà không hỏi: lượt đó sẽ **đo cả** thay đổi voice
  chưa xong, nên một lượt đỏ có thể không nói gì về chiến dịch này.

## Tệp có nguy cơ đụng nhau

| Tệp | Chủ | Chiến dịch này |
|---|---|---|
| `CLAUDE.md` | dùng chung | **SỬA** — đây là việc chính |
| `AGENTS.md` | dùng chung | **SỬA** |
| `docs/DEVELOPMENT_WORKFLOW.md` | dùng chung | **SỬA** |
| `tools/gate.py` | dùng chung | đọc; sửa tối thiểu nếu cần |
| `docs/LTT_VOICE/**` | phiên voice (đang dở) | ⛔ **KHÔNG chạm** |
| `docs/auto_scan_video_v4/**` | `phien/asv-v4` | ⛔ **KHÔNG chạm** |
| `docs/CHATLTT_V3/**` | `claude/chatltt-v3-agentic` | ⛔ **KHÔNG chạm** |
| `docs/VIDEO_AI_V2/**` | `phien/video-v2-wangp` | ⛔ **KHÔNG chạm** |

⭐ Bốn thư mục `KHÔNG chạm` ở trên **có** chứa luật cadence gate trùng lặp. Cách
xử lý không phải sửa hộ, mà là `SESSION_MIGRATION_NOTE.md`: phiên chủ đọc lại
hợp đồng canonical rồi tự bỏ luật cũ của mình. Sửa hộ một tệp phiên khác đang mở
là tạo xung đột merge cho họ, và họ sẽ giải quyết bằng cách giữ bản của họ.

---

## 🔴 CẬP NHẬT 15:22 — một phiên THỨ HAI vào cây này GIỮA chiến dịch

Ảnh chụp ở đầu tệp này đã cũ sau **hai giờ**. Lúc 15:06–15:22 một phiên khác bắt
đầu ghi **LTT WORKFLOW V2** vào chính cây chính:

```
platform_core/workflow/may_trang_thai.py  15:06     platform_core/workflow/dieu_khien.py  15:20
platform_core/workflow/ket_so.py          15:07     platform_core/workflow/join.py        15:21
platform_core/workflow/he_kieu.py         15:18     platform_core/workflow/foreach.py     15:22
tests/test_958_wf_he_kieu_cong.py         15:17     platform_core/workflow/bao_gia.py
```

⚠️ **`ListAgents` KHÔNG cho biết điều này.** Nó vẫn liệt kê đúng 4 phiên như lúc
09:00 — vì phiên đó đã tồn tại từ trước, chỉ **đổi việc**. Bảng phiên trả lời
"ai đang mở", không trả lời "ai đang ghi vào đâu". Thứ trả lời câu sau là
**`mtime`**.

### Nó đã làm đỏ một phép kiểm của chiến dịch này — và đó là phép kiểm ĐÚNG

`test_145::test_ba_tep_ghi_vao_cay_deu_tra_lai_CA_DAU_THOI_GIAN` báo:

```
ba tep pha 2 lam ban cay: ['platform_core/workflow/he_kieu.py',
                           'tests/test_958_wf_he_kieu_cong.py']
```

Phép kiểm chụp cây trước và sau, rồi so. Hai tệp ấy **xuất hiện giữa lượt chạy**
— không phải do ba tệp pha 2, mà do một người khác đang gõ. Câu báo lỗi nêu đích
danh một nghi phạm vô tội (`Bẫy 8` của `docs/BAY_TRONG_CONG_CHAT_LUONG.md`), và
kết luận đúng là: **lượt đo này nói về một cây đã không còn tồn tại.**

⇒ Ba lý do một lượt `gate.py` đầy đủ **không** được chạy cho chiến dịch này, và
đây là lý do thứ ba: cây không đứng yên đủ lâu để một lượt 11 phút có nghĩa.

### Hệ quả cho lệnh commit

⛔ `git add -A` hay `git add .` lúc này sẽ nuốt **cả Workflow V2 đang viết dở của
người khác** vào commit của chiến dịch. Chỉ liệt kê **tường minh từng tệp**.

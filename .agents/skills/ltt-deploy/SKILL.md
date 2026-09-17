---
name: ltt-deploy
description: Dùng khi chuẩn bị hoặc thực hiện deploy nền tảng LTTSTUDIOSAPP lên máy A (C:\LTTPlatform), nghiệm thu sau deploy, hoặc đẩy main lên GitHub. Nêu điều kiện, lệnh và phép nghiệm thu; trỏ về docs/16_CAP_NHAT_VA_DEPLOY.md và hợp đồng §7–§9.
---

# Deploy máy A — LTTSTUDIOSAPP

Chủ quy trình: `docs/16_CAP_NHAT_VA_DEPLOY.md` (thao tác) ·
`docs/00_LTT_OPERATING_CONTRACT.md` §7–§9 (điều kiện) ·
`docs/QUY_TRINH_WORKTREE.md` §4 (gộp `main` trước). Đọc cả ba trước khi deploy.

## Điều kiện (tóm tắt con trỏ)

1. Đã gộp `main` và có **gate xanh trên đúng SHA deploy** — cấp nào: skill `ltt-gate`
   / hợp đồng §8. Test nhắm một mình không đủ.
2. `git -C D:\LTTSTUDIOSAPP status --porcelain` **rỗng**. ⛔ Dòng `??` lạ là phiên
   khác — báo, không xoá, không `stash` (deploy chép CẢ CÂY, kể cả tệp chưa theo dõi).
3. **Báo** các phiên đang chạy trước khi deploy — báo, không chờ.
4. Migration: head alembic của `main` khác bản đang chạy thì đọc trước.
5. Deploy chỉ đi từ **cây chính** `D:\LTTSTUDIOSAPP`; `setup\2-cai-dat.ps1` từ chối
   worktree (`AGENTS.md` §10.6).

## Lệnh

Nguyên văn lệnh nâng quyền và nơi đọc kết quả (`C:\LTTPlatform\logs\deploy-*.ket.txt`):
`docs/16_CAP_NHAT_VA_DEPLOY.md` §2. ⛔ `EXITCODE` rỗng nghĩa là chưa xong.

## Nghiệm thu (§3 của tệp deploy)

```bash
python tools/nghiem_thu_deploy.py
curl https://app.lttstudios.com/health/ready     # 200
curl https://app.lttstudios.com/health/version   # đúng SHA vừa deploy
git -C D:\LTTSTUDIOSAPP status --porcelain       # đo lại sau robocopy
```

Đổi giao diện ⇒ kiểm trình duyệt trên URL công khai (hợp đồng §9); đổi CSS/JS tĩnh ⇒
cache-bust `?v={{ asset_ver }}` (`CLAUDE.md` luật 7).

## Đẩy GitHub (sau nghiệm thu)

`python tools/scan_source_secrets.py` (Findings: 0) rồi `git push origin main` — §4.

## Không làm

- ⛔ Sửa trực tiếp `C:\LTTPlatform\app\` — bị thay toàn bộ mỗi lần cập nhật.
- ⛔ Máy B (`llm_gateway`, `render_gateway`) không đi đường này — §5.
- ⛔ Deploy khi nhiệm vụ được giao cấm deploy.

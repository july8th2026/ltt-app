---
name: ltt-may-production
description: Dùng trước thao tác có rủi ro trong LTTSTUDIOSAPP — máy dùng chung là máy production, gồm lệnh nặng, git nhiều phiên, bí mật, ghi cấu hình không BOM, .ps1 ASCII, nâng quyền, điều kiện phải dừng. Trỏ về CLAUDE.md, AGENTS.md §3/§5/§10 và hợp đồng §5–§6, §10.
---

# Máy production dùng chung — LTTSTUDIOSAPP

Nguồn: `CLAUDE.md` (luật chết người) · `AGENTS.md` §3 (bí mật), §5 (Windows),
§10 (tệp dùng chung) · `docs/00_LTT_OPERATING_CONTRACT.md` §5–§6, §10 ·
`docs/QUY_TAC_CHAY_LENH_NANG.md`. Đang ở máy chủ nếu `Test-Path C:\LTTPlatform`.

## Lệnh nặng

Gate mọi chế độ · `test_nhanh.py` · ≥ 3 tệp test · `build_system_profile.py` · nạp model:
```powershell
python tools\cua_so_yen.py trang-thai     # có người giữ khoá -> chờ
python tools\tai_may.py                   # QUÁ TẢI -> chờ; BẬN -> thu hẹp
```
pytest gõ tay `-n` ≤ 6. ⛔ `cua_so_yen.py nha --ep` không kèm `--tai-nguyen`. Máy vừa treo: hộp đen trước (§5).

## Git nhiều phiên

- Dòng `??` lạ = **phiên khác**, không phải rác. ⛔ `stash`, `reset --hard`,
  `checkout --`, `clean` lên việc không phải của mình.
- `git add` tường minh từng tệp (không `-A`, không `.`); xem `git diff --cached`.
- Mỗi phiên một worktree (`docs/QUY_TRINH_WORKTREE.md` §1); không gỡ cây người khác.

## Bí mật

- ⛔ Không đưa giá trị bí mật vào mã, tài liệu, log, commit, tóm tắt — chỉ **tên**.
- ⛔ Không commit/chép: `data/config.json` · `data/*.enc` · `secrets/` ·
  `cloudflare/config.yml` · `cloudflare/*.json`.
- `python tools/scan_source_secrets.py` phải 0 finding. ⛔ ACL ở `secrets\` và `D:\LTTBackups` là cố ý — không `icacls`.

## Windows (đã làm sập production)

- Ghi cấu hình **không BOM**:
  `[IO.File]::WriteAllText($path, $text, (New-Object Text.UTF8Encoding($false)))`.
- `.ps1` thuần ASCII. ⛔ Không viết Python inline qua PowerShell — ghi tệp `.py`.
  Giữ kiểu xuống dòng git đang giữ cho từng tệp (`tools/check_xuong_dong.py`).

## Ranh giới

- ⛔ `D:\BOT GEMINI` chỉ đọc (cổng 8000; nền tảng 8100) · không sửa `C:\LTTPlatform\app\`.
- Nâng quyền: `python tools\nang_quyen.py <script.py>` (im lặng, không phải điểm dừng).

## Dừng khi (hợp đồng §10, §10b)

Gate đỏ · thao tác không đảo được trên dữ liệu thật · thay đổi chưa commit không
rõ của ai · rủi ro bảo mật/mất dữ liệu. Ngoài bốn điều đó: làm tiếp, không xin phép.

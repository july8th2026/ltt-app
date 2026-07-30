# LTTStudios.com Migration Plan

> **Mục tiêu**: Chuyển toàn bộ bot từ `lttstudio.top` → `lttstudios.com`, build website mới, không gián đoạn dịch vụ.
>
> **Ngày bắt đầu**: 2026-06-02 • **Người thực thi**: Claude + LE THANH TRUNG

---

## 1. Diagnostic kết quả

Tôi đã probe live cả 2 domain. Kết quả:

| Domain | DNS | HTTP | Note |
|---|---|---|---|
| `lttstudios.com` | ✅ 103.57.220.210 | 403 / 502 | Đã trỏ DNS nhưng **chưa có content** |
| `lttstudio.top` | ✅ 103.72.97.5 | 403 trên mọi path | ⚠️ Site hiện tại **đang lỗi** (Meta reviewer sẽ thấy 403 → reject app) |

→ **2 vấn đề cần fix**:
1. Build content + upload lên `lttstudios.com`
2. Sửa cấu hình hosting để serve files đúng (hoặc verify `.top` đang serve cách nào)

→ **Lưu ý**: 2 domain ở 2 IP khác nhau → KHÔNG phải đang share host. Cần mirror nội dung sang `.com` chứ không phải alias.

---

## 2. Scope migration

### 2.1 Files trong codebase cần update (production)

| Category | Files | Count |
|---|---|---|
| **Config chính** | `data/config.json` | 1 file, 8 refs |
| **Version + License** | `version.py`, `LICENSE` | 2 files, 5 refs |
| **GUI** | `gui/settings_tab.py`, `gui/about_dialog.py`, `gui/tiktok_account_tab.py`, `gui/tiktok_oauth_url_dialog.py` | 4 files |
| **Core logic** | `core/tiktok/auth_manager.py`, `core/tiktok/audit_checklist.py` | 2 files |
| **i18n** | `data/translations/vi.json`, `data/translations/en.json` | 2 files |
| **Dev tools** | `tools/simulate_oauth_flow.py`, `tools/check_oauth_relay.py`, `tools/demo_v2/scene_config.py`, `tools/demo_v2/02_generate_slides.py`, `scripts/_demo_record.py`, `scripts/_demo_record_v3.py`, `scripts/demo_assets/_gen_slides.py` | 7 files |
| **Tests** | `tests/test_28_tiktok_parity.py` | 1 file |
| **Docs** | `docs/_luutru/HANDOFF.md`, `docs/_luutru/PROJECT_STATE.json`, `docs/fb-app-review-submission-plan.md`, `docs/fb-app-review-assets/*.txt`, `docs/tiktok-submission/*` | ~10 files |
| **TOTAL** | | **~30 files** |

### 2.2 Files KHÔNG đụng (historical / backup)

| Path | Lý do |
|---|---|
| `.backup_v2fix/*`, `.backup_multisheet/*`, `.backup_helpsystem/*` | Backup snapshots — giữ nguyên |
| `data/audit_log.jsonl` | Audit trail lịch sử — không sửa |
| `data/config.backup.*.json` | Config backup lịch sử |

### 2.3 Website files cần build mới (upload lên `lttstudios.com`)

| File | Path trên web | Purpose |
|---|---|---|
| `index.html` | `/` | Landing page |
| `privacy.html` | `/legal/privacy.html` | **Required by Meta App Review** |
| `terms.html` | `/legal/terms.html` | **Required by Meta App Review** |
| `data-deletion.html` | `/legal/data-deletion.html` | **Required by Meta App Review** |
| `fb-callback.html` | `/auth/fb-callback.html` | OAuth callback Facebook |
| `callback.html` | `/legal/callback.html` | OAuth callback TikTok |
| `oauth-relay/fetch.php` | `/api/oauth-relay/fetch.php` | TikTok relay (nếu cần) |

---

## 3. Migration phases

```
PHASE A — Code migration               (Claude làm, 30 phút)
  ↓
PHASE B — Build website files          (Claude làm, 30 phút)
  ↓
PHASE C — Upload website lên host      (User làm, 30-60 phút)
  ↓
PHASE D — Update Meta Dashboard URLs   (User làm, 10 phút)
  ↓
PHASE E — Test OAuth flow              (User làm, 10 phút)
  ↓
PHASE F — Submit Business Verify       (User làm, 1-3 ngày chờ)
  ↓
PHASE G — Submit App Review            (User làm, 5-14 ngày chờ)
  ↓
PHASE H — Go Live                      (User làm, 5 phút)
```

---

## 4. Migration rules (cho Claude khi sửa code)

### 4.1 Replace mapping

| Cũ | Mới |
|---|---|
| `https://lttstudio.top` | `https://lttstudios.com` |
| `http://lttstudio.top` | `https://lttstudios.com` |
| `lttstudio.top` (bare) | `lttstudios.com` |
| `www.lttstudio.top` | `www.lttstudios.com` |
| `support@lttstudio.top` | `support@lttstudios.com` |
| `security@lttstudio.top` | `security@lttstudios.com` |
| `licensing@lttstudio.top` | `licensing@lttstudios.com` |

### 4.2 Special cases (giữ nguyên hoặc xử lý đặc biệt)

| Case | Xử lý |
|---|---|
| `lttstudio.top.evil.com` trong test security spoof | **Giữ nguyên** (test case validation) |
| File `data/audit_log.jsonl` | **Không đụng** (lịch sử) |
| Backup folders | **Không đụng** |

### 4.3 Backward compat strategy

Trong Meta Dashboard và bot config, **GIỮ CẢ 2 domain song song** cho 60-90 ngày:
- Meta App Domains: `lttstudio.top` + `lttstudios.com`
- Meta OAuth Redirect URIs: cả 2 callback URL
- Bot config `meta_redirect_uri`: dùng `.com` (cho OAuth mới)
- Token cũ đã save với `.top`: tiếp tục refresh được vì Meta accept cả 2

Sau 60 ngày khi mọi token đã refresh sang `.com` → có thể bỏ `.top` khỏi Meta config + sunset domain.

---

## 5. Rollback plan

Nếu có sự cố sau khi migrate:

| Issue | Rollback |
|---|---|
| `.com` site không load → OAuth break | Đổi `meta_redirect_uri` trong config.json về `.top` (1 dòng); restart bot |
| Bot crash sau update | Restore `config.json` từ `data/config.backup.*.json` |
| Test fail | `git diff` xem file đã sửa, revert specific file |

Backup full project trước khi migrate (recommended):
```bash
cd "C:\Users\Administrator\Desktop"
xcopy "BOT UP FB + TikTok" "BOT UP FB + TikTok.backup-before-migration" /E /I /H
```

---

## 6. Success criteria

Migration **PASS** khi:

| # | Criterion | Verification |
|---|---|---|
| 1 | `grep -r "lttstudio.top" core/ gui/ utils/ data/config.json` → 0 hits | Grep cuối phase A |
| 2 | `https://lttstudios.com/legal/privacy.html` trả 200 OK | `curl -I` |
| 3 | Bot khởi động bình thường sau migration | `python main.py` không error |
| 4 | OAuth flow Facebook qua `.com` thành công | Connect 1 test account |
| 5 | Meta Dashboard cập nhật URLs `.com` | Manual check |
| 6 | Business Verification submitted với `lttstudios.com` | Status "Verifying" |

---

## 7. Timeline cụ thể

| Day | Phase | Owner | Status |
|---|---|---|---|
| **Hôm nay** | A — Code migration | Claude | Đang làm |
| Hôm nay | B — Build website files | Claude | Sau A |
| Hôm nay/mai | C — Upload lên hosting | User | Sau B |
| Mai | D — Update Meta Dashboard | User | Sau C |
| Mai | E — Test OAuth | User | Sau D |
| Mai | F — Submit Business Verification | User | Sau E |
| Mai +3-5d | F xong | (Meta xử lý) | — |
| Mai +5d | G — Submit App Review | User | Sau F |
| Mai +12-20d | G xong | (Meta review) | — |
| Mai +20d | H — Toggle Live | User | Sau G |

---

## 8. Asset deliverables (Claude sẽ tạo)

| Path | Status |
|---|---|
| `docs/lttstudios-migration-plan.md` | ✅ File này |
| `docs/lttstudios-website/index.html` | ⏳ Phase B |
| `docs/lttstudios-website/legal/privacy.html` | ⏳ Phase B |
| `docs/lttstudios-website/legal/terms.html` | ⏳ Phase B |
| `docs/lttstudios-website/legal/data-deletion.html` | ⏳ Phase B (move + update) |
| `docs/lttstudios-website/legal/callback.html` | ⏳ Phase B |
| `docs/lttstudios-website/auth/fb-callback.html` | ⏳ Phase B |
| `docs/lttstudios-website/README.md` | ⏳ Phase B — deployment guide |
| `docs/lttstudios-deployment-guide.md` | ⏳ Phase G — Meta Dashboard + Business Verify steps |

---

**Phiên bản**: 1.0 • **Cập nhật**: 2026-06-02

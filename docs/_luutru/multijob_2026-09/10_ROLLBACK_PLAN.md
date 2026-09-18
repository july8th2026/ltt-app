# 10 — Rollback

| Pha | Rollback | Thời gian | Kiểm sau lui |
|---|---|---|---|
| 0 GPU pin | yaml trước (`deploy.ps1` chụp-trước-khi-đè, `llm_gateway/deploy/deploy.ps1`) + restart `LTTLlamaSwap` | < 1 phút (đã diễn tập 18,9 s — audit `06`) | `/running` + log nạp |
| 1 control plane (N=1) | `git revert` + deploy máy A theo `docs/16_CAP_NHAT_VA_DEPLOY.md`; migration alembic **thêm cột/bảng**, không xoá — bản cũ bỏ qua cột mới | theo đường ray deploy máy A (`app.previous`) | `/health/version`; cửa stream trả 429 như cũ |
| 2 engine N=4 | **một giá trị**: `SO_SLOT_MAY_B = 1` (kéo theo manifest, env gateway, `--parallel`) + yaml hồ sơ trước | deploy máy B + máy A | C1 như mốc; `requests_deferred` = 0 |
| Khẩn cấp không deploy | gateway env `LTT_LLM_MAX_DONG_THOI=1` + `setup/nap_lai_env.ps1` (memory "nssm nướng ENV"), engine vẫn 4 slot nhưng chỉ nhận 1 | vài phút | 429 xuất hiện đúng |

Nguyên tắc: pha 1 **đúng ở N = 1**, nên lui pha 2 không kéo lùi pha 1. Không bước nào xoá dữ liệu tiền;
mọi thay đổi tiền đi kèm phép kiểm bất biến ở `09` §A.

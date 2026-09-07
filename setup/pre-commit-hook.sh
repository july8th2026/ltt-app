#!/bin/sh
# Hook pre-commit - CHIA SE cho CA SAU worktree cua D:\LTTSTUDIOSAPP.
#
# =========================================================================
# [!] `git rev-parse --git-common-dir` = `.git`, nen tep NAY chay o moi
#     worktree. Nhung `tools/` va `.pre-commit-config.yaml` thi MOI CAY MOT
#     BAN - va do 06/09/2026, nam cay con lai deu THIEU:
#
#         auto-scan-video-v4-mvp   thieu check_ruff, check_ranh_gioi, ascii, cau hinh
#         chatltt-v3-agentic       thieu ascii, cau hinh
#         ltt-llm-api-http-guide   thieu check_ruff, check_ranh_gioi, ascii, cau hinh
#         mobile-v1                thieu check_ruff, check_ranh_gioi, ascii, cau hinh
#         video-v2-wangp           thieu check_ranh_gioi, ascii, cau hinh
#
#     Do duoc: chay `pre-commit` o mot cay thieu cau hinh tra **rc=1**
#     (`InvalidConfigError: .pre-commit-config.yaml is not a file`). Cai
#     thang framework vao day nghia la MOI COMMIT o nam cay ay hong ngay -
#     ke ca ba phien dang lam viec.
#
#     => DUONG SUY BIEN phai tuong minh: cay nao CHUA co cau hinh thi hook
#        IM LANG di qua. Enforcement o noi co du do nghe; im lang o noi chua
#        co. Khong cay nao bi phat vi chua kip dong bo.
#
#     Do la cau 1 va cau 2 cua AGENTS.md muc 4c.
# =========================================================================
#
# Bo qua mot lan (chi khi that su can, va noi ro trong commit):
#     git commit --no-verify

# Cay nay chua co cau hinh -> khong co gi de cuong che. Thoat 0, khong on ao.
if [ ! -f .pre-commit-config.yaml ]; then
    exit 0
fi

# Thieu chinh `pre-commit` cung khong duoc chan nguoi ta commit: cong cu vang
# mat la mot van de moi truong, khong phai mot van de ma nguon.
if ! python -c "import pre_commit" >/dev/null 2>&1; then
    echo "  [pre-commit] vang goi \`pre-commit\` - bo qua. Xem requirements-dev.txt"
    exit 0
fi

exec python -m pre_commit hook-impl \
    --config=.pre-commit-config.yaml \
    --hook-type=pre-commit \
    --hook-dir "$(dirname "$0")" \
    -- "$@"

"""L-25 — ngân sách RAM máy B: `--cache-ram` (yaml) và sàn RAM của cổng LLM là MỘT ràng buộc.

Sự cố 18/09: yaml lên `--cache-ram 24576` trong khi `gateway.env` giữ sàn 48 ⇒ hai
cache đầy kéo RAM trống 85,0 → 44,2 GiB và trọng tài cổng B từ chối MỌI lượt ~10
phút. Hai số nằm ở hai tệp, không tệp nào nhắc tệp kia. Tệp này bắt chúng khớp:

* sàn trong `deploy.ps1` (ghi đè `gateway.env` mỗi lần deploy) = mặc định `config.py`;
* 2 × `--cache-ram` + checkpoint sống ngoài trần (np × ctx-checkpoints × ~150 MiB,
  upstream #25437/#28194) + sàn ≤ RAM trống đo được lúc cache rỗng.

Chỉ đọc tệp, không ghi gì vào cây.
"""
from __future__ import annotations

import pathlib
import re

from llm_gateway.config import RAM_TRONG_GB_MAC_DINH

GOC = pathlib.Path(__file__).resolve().parent.parent
YAML_KHO = GOC / "llm_gateway" / "deploy" / "llama-swap.yaml"
DEPLOY = GOC / "llm_gateway" / "deploy" / "deploy.ps1"

#: RAM trống (GiB, psutil) máy B khi HAI model vừa nạp, cache rỗng — đo 18/09
#: (`KET_QUA_BAO_TRI_18_09.md` §2). Đo lại khi đổi model / RAM / dịch vụ trên B.
RAM_TRONG_CACHE_RONG_GIB = 85.0
#: Một checkpoint model lai đo 112–150 MiB (upstream #28194, #24055) — lấy trần.
CHECKPOINT_GIB = 150 / 1024


def _cmd_tho(van: str) -> dict[str, str]:
    import yaml
    doc = yaml.safe_load(van)
    return {ten: str(hs.get("cmd", "")) for ten, hs in (doc.get("models") or {}).items()}


def _co(cmd: str, *ten: str) -> int | None:
    for t in ten:
        m = re.search(rf"(?:^|\s){re.escape(t)}\s+(-?\d+)", cmd)
        if m:
            return int(m.group(1))
    return None


def _san_deploy() -> float:
    van = DEPLOY.read_text(encoding="ascii")          # .ps1 thuần ASCII (CLAUDE.md luật 6)
    m = re.findall(r"\$thamSoA\['LTT_LLM_RAM_TRONG_GB'\]\s*=\s*'(\d+(?:\.\d+)?)'", van)
    assert len(m) == 1, "deploy.ps1 phai dat san RAM dung MOT lan"
    return float(m[0])


def test_san_deploy_BANG_mac_dinh_config():
    assert _san_deploy() == RAM_TRONG_GB_MAC_DINH


def test_deploy_GHI_DE_san_khi_migrate_khong_chi_luc_tao_tep():
    van = DEPLOY.read_text(encoding="ascii")
    assert re.search(r"LTT_LLM_RAM_TRONG_GB\)=", van), "migrate phai ghi de san RAM"
    assert "LTT_LLM_RAM_TRONG_GB=48" not in van


def test_hai_cache_day_cong_san_VUA_ram_trong_luc_cache_rong():
    cmds = _cmd_tho(YAML_KHO.read_text(encoding="utf-8"))
    tong = 0.0
    for ten, cmd in cmds.items():
        if "llama-server" not in cmd:
            continue
        cram = _co(cmd, "--cache-ram", "-cram")
        assert cram is not None and cram > 0, f"{ten}: phai khai --cache-ram > 0 (L-24)"
        np_ = _co(cmd, "-np", "--parallel") or 1
        ckpt = _co(cmd, "--ctx-checkpoints", "-ctxcp", "--swa-checkpoints") or 32
        tong += cram / 1024 + np_ * ckpt * CHECKPOINT_GIB
    assert tong > 0
    du = RAM_TRONG_CACHE_RONG_GIB - tong - RAM_TRONG_GB_MAC_DINH
    assert du >= 4.0, (f"2 cache + checkpoint ({tong:.1f}) + san ({RAM_TRONG_GB_MAC_DINH}) "
                       f"vuot RAM trong luc cache rong ({RAM_TRONG_CACHE_RONG_GIB}): du {du:.1f} GiB")


def test_doi_chung_san_48_cu_voi_cache_24576_THI_DO():
    """Phép kiểm phải đỏ trên đúng cấu hình đã gây sự cố 18/09 (2 × 24 GiB, sàn 48)."""
    tong = 2 * (24576 / 1024 + 3 * 8 * CHECKPOINT_GIB)
    assert RAM_TRONG_CACHE_RONG_GIB - tong - 48.0 < 4.0

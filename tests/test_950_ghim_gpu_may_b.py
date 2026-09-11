"""P0-GPU-PIN (multijob, 2026-09-11) — Qwen trên máy B CHỈ được chạy trên RTX 3090.

🔴 VÌ SAO CÓ PHÉP KIỂM NÀY

Máy B lắp thêm RTX 5060 Ti 16 GB (09/2026). `llama-server --list-devices` in
`CUDA0 = RTX 3090`, `CUDA1 = RTX 5060 Ti`. Với `-ngl 999` mà không ghim thiết bị,
llama.cpp mặc định CHIA LỚP qua mọi GPU nó thấy ⇒ model 27B tự chia sang cả card
5060 Ti — chậm hơn, và trái quyết định của chủ dự án (D-09a: 5060 Ti để dành cho
model khác). Không phép kiểm nào khác đọc được điều này: mọi thứ vẫn "chạy".

⛔ Ghim bằng UUID, không bằng chỉ số — thứ tự liệt kê CUDA đổi được khi lắp/đổi
   khe card; UUID thì không.
"""
from __future__ import annotations

import pathlib

import pytest
import yaml

YAML = pathlib.Path(__file__).resolve().parents[1] / "llm_gateway" / "deploy" / "llama-swap.yaml"

#: UUID của RTX 3090 trên máy B — đo 2026-09-11 bằng Nexus `metrics/gpu`
#: (`docs/multijob/00_BASELINE.md`). Đổi card thật thì đổi ở đây VÀ trong yaml.
UUID_3090 = "GPU-26623278-4fa5-82db-4306-237651b03e78"


@pytest.fixture(scope="module")
def cau_hinh() -> dict:
    return yaml.safe_load(YAML.read_text(encoding="utf-8"))


def test_moi_ho_so_deu_ghim_uuid_3090(cau_hinh):
    ho_so = cau_hinh.get("models") or {}
    assert ho_so, "llama-swap.yaml khong co model nao"
    thieu = {}
    for ten, m in ho_so.items():
        env = [str(x) for x in (m.get("env") or [])]
        if f"CUDA_VISIBLE_DEVICES={UUID_3090}" not in env:
            thieu[ten] = env
    assert not thieu, (
        f"ho so khong ghim 3090 (se tu chia sang 5060 Ti): {thieu}")


def test_khong_ho_so_nao_ghim_bang_chi_so(cau_hinh):
    """`CUDA_VISIBLE_DEVICES=0` trông đúng hôm nay và sai sau lần đổi khe card."""
    for ten, m in (cau_hinh.get("models") or {}).items():
        for x in m.get("env") or []:
            if str(x).startswith("CUDA_VISIBLE_DEVICES="):
                gt = str(x).split("=", 1)[1]
                assert gt.startswith("GPU-"), f"{ten} ghim bang chi so: {x}"


def test_cua_doc_metrics_van_mo(cau_hinh):
    """Bản đang chạy trên máy B có `--metrics` (phiên khác bật); kho không được lùi nó.

    ⭐ Đây là lớp lỗi C-04 của audit: deploy tệp cũ từ kho đè cấu hình mới trên máy.
    `/metrics` là nguồn DUY NHẤT của `requests_deferred` — số báo động khi hai tầng
    admission tính sai (spec §11).
    """
    chung = str((cau_hinh.get("macros") or {}).get("CHUNG") or "")
    assert "--metrics" in chung.split()

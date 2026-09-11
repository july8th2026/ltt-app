"""P0-GPU-PIN (multijob, 2026-09-11) — Qwen trên máy B CHỈ được chạy trên RTX 3090.

🔴 VÌ SAO CÓ PHÉP KIỂM NÀY

Máy B lắp thêm RTX 5060 Ti 16 GB (09/2026). `llama-server --list-devices` in
`CUDA0 = RTX 3090`, `CUDA1 = RTX 5060 Ti`. Với `-ngl 999` mà không ghim thiết bị,
llama.cpp mặc định CHIA LỚP qua mọi GPU nó thấy ⇒ model 27B tự chia sang cả card
5060 Ti — chậm hơn, và trái quyết định của chủ dự án (D-09a: 5060 Ti để dành cho
model khác). Không phép kiểm nào khác đọc được điều này: mọi thứ vẫn "chạy".

⛔ Ghim bằng UUID, không bằng chỉ số — thứ tự liệt kê CUDA đổi được khi lắp/đổi
   khe card; UUID thì không.

🔵 CẬP NHẬT 2026-09-11 (Task 0.2, LTT LLM Dual-Model): UUID không còn hard-code
trong tệp này. `llm_gateway/deploy/gpu_may_b.json` là nguồn chân lý danh tính
GPU (vai -> UUID/PCI/tên/VRAM); test dưới đọc từ đó, để một lần đo lại card
chỉ cần sửa MỘT tệp. `render_gateway/deploy/cai_dat_dich_vu.ps1` (dịch vụ
LTTComfyUI) cũng phải ghim UUID vai `ltt38` — kiểm ở
`test_comfyui_ghim_uuid_3090_trong_cai_dat_dich_vu`.
"""
from __future__ import annotations

import json
import pathlib

import pytest
import yaml

GOC = pathlib.Path(__file__).resolve().parents[1]
YAML = GOC / "llm_gateway" / "deploy" / "llama-swap.yaml"
GPU_JSON = GOC / "llm_gateway" / "deploy" / "gpu_may_b.json"
PS1_COMFY = GOC / "render_gateway" / "deploy" / "cai_dat_dich_vu.ps1"


def _doc_gpu_map(duong: pathlib.Path = GPU_JSON) -> dict[str, dict]:
    """Đọc `gpu_may_b.json` -> {vai: {uuid, pci_bus_id, ten, vram_mib}}."""
    du_lieu = json.loads(duong.read_text(encoding="utf-8"))
    return {x["vai"]: x for x in du_lieu}


def _vai_cho_model(ten_ho_so: str) -> str | None:
    """Ánh xạ tên hồ sơ llama-swap -> vai GPU trong gpu_may_b.json.

    `qwen38-*` là Qwen3.8-27B, chốt CHỈ chạy 3090 (D-09a) -> vai `ltt38`.
    `qwen35-*` (chưa tồn tại trong yaml ở pha này) sẽ là Qwen3.5 -> `ltt35`.
    """
    if ten_ho_so.startswith("qwen38"):
        return "ltt38"
    if ten_ho_so.startswith("qwen35"):
        return "ltt35"
    return None


@pytest.fixture(scope="module")
def gpu_map() -> dict[str, dict]:
    return _doc_gpu_map()


@pytest.fixture(scope="module")
def cau_hinh() -> dict:
    return yaml.safe_load(YAML.read_text(encoding="utf-8"))


def test_gpu_may_b_json_dung_dinh_dang(gpu_map):
    assert set(gpu_map) >= {"ltt38", "ltt35"}, f"thieu vai: {sorted(gpu_map)}"
    assert gpu_map["ltt38"]["uuid"].startswith("GPU-")
    assert gpu_map["ltt35"]["uuid"].startswith("GPU-")
    assert gpu_map["ltt38"]["uuid"] != gpu_map["ltt35"]["uuid"], (
        "hai vai tro ve cung mot UUID - khong the la hai card khac nhau")


def test_moi_ho_so_deu_ghim_uuid_dung_vai(cau_hinh, gpu_map):
    """Nguồn UUID là `gpu_may_b.json` theo vai, không hard-code trong test."""
    ho_so = cau_hinh.get("models") or {}
    assert ho_so, "llama-swap.yaml khong co model nao"
    thieu = {}
    for ten, m in ho_so.items():
        vai = _vai_cho_model(ten)
        if vai is None:
            continue
        uuid_mong_doi = gpu_map[vai]["uuid"]
        env = [str(x) for x in (m.get("env") or [])]
        if f"CUDA_VISIBLE_DEVICES={uuid_mong_doi}" not in env:
            thieu[ten] = {"can": uuid_mong_doi, "co": env}
    assert not thieu, (
        f"ho so khong ghim dung UUID theo vai (gpu_may_b.json): {thieu}")


def test_doi_chung_xoa_dong_env_thi_do(tmp_path, gpu_map):
    """Đối chứng TDD: xoá dòng `env` của MỘT hồ sơ trong một BẢN SAO tạm thời
    (`tmp_path`, không đụng cây thật) thì phép kiểm trên phải báo ĐỎ."""
    cau_hinh_goc = yaml.safe_load(YAML.read_text(encoding="utf-8"))
    ho_so = cau_hinh_goc.get("models") or {}
    ten_dau = next(iter(ho_so))
    ho_so[ten_dau]["env"] = []
    tep_tam = tmp_path / "llama-swap-hong.yaml"
    tep_tam.write_text(yaml.safe_dump(cau_hinh_goc), encoding="utf-8")

    cau_hinh_hong = yaml.safe_load(tep_tam.read_text(encoding="utf-8"))
    thieu = {}
    for ten, m in (cau_hinh_hong.get("models") or {}).items():
        vai = _vai_cho_model(ten)
        if vai is None:
            continue
        uuid_mong_doi = gpu_map[vai]["uuid"]
        env = [str(x) for x in (m.get("env") or [])]
        if f"CUDA_VISIBLE_DEVICES={uuid_mong_doi}" not in env:
            thieu[ten] = env
    assert thieu, "doi chung khong bat duoc: xoa dong env ma van PASS"


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


def test_comfyui_ghim_uuid_3090_trong_cai_dat_dich_vu(gpu_map):
    """ComfyUI (dịch vụ `LTTComfyUI`, `render_gateway/deploy/cai_dat_dich_vu.ps1`)
    cũng phải ghim UUID vai `ltt38` — nó và `qwen38-*` dùng chung một card 24 GB.
    Không ghim thì ComfyUI tự do rơi lên 5060 Ti (D-09a để dành card đó)."""
    noi_dung = PS1_COMFY.read_text(encoding="utf-8")
    uuid_3090 = gpu_map["ltt38"]["uuid"]
    dong_env = f"CUDA_VISIBLE_DEVICES={uuid_3090}"
    assert dong_env in noi_dung, (
        "cai_dat_dich_vu.ps1 khong dat CUDA_VISIBLE_DEVICES cho LTTComfyUI")

    # Phai nam trong khoi cai dat LTTComfyUI (truoc khoi LTTRenderGateway),
    # khong phai mot dong lac cho khac trong tep.
    vi_tri_comfy = noi_dung.index("Dich vu LTTComfyUI")
    vi_tri_env = noi_dung.index(dong_env)
    vi_tri_render = noi_dung.index("Dich vu LTTRenderGateway")
    assert vi_tri_comfy < vi_tri_env < vi_tri_render, (
        "dong CUDA_VISIBLE_DEVICES khong nam trong khoi cai dat LTTComfyUI")


def test_cai_dat_dich_vu_ps1_thuan_ascii():
    """Quy tac 2 cua CLAUDE.md: .ps1 phai thuan ASCII (PowerShell 5.1 doc theo
    ANSI khi khong BOM; mot dau tieng Viet lam hong ca cau lenh)."""
    raw = PS1_COMFY.read_bytes()
    khong_ascii = [b for b in raw if b > 0x7E and b not in (0x0D, 0x0A)]
    assert not khong_ascii, (
        f"cai_dat_dich_vu.ps1 co {len(khong_ascii)} byte khong-ASCII")

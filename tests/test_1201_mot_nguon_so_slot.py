"""Một nguồn cho số slot máy B và pool KV (multijob Task 2).

🔴 VÌ SAO: trước 11/09 có BỐN chỗ cùng khai "1 lượt đồng thời" — `DONG_THOI_MAY_B`,
`manifest.py` (`admission_slots=1`), gateway `LTT_LLM_MAX_DONG_THOI` và `--parallel 1`
trong yaml — và chỉ một cặp có phép kiểm đối chiếu. Đổi một chỗ mà quên chỗ kia thì
hai trần không biết nhau: máy A nhận 4 lượt, máy B trả 429 cho 3.
⭐ Nên phép kiểm này đọc mọi chỗ và bắt chúng đồng ý với hồ sơ `ngan_sach.HO_SO[m]`.
🔴 Phương án C bước 2 (17/09/2026): `SO_SLOT_MAY_B` (một số cho HAI card) và bí danh
`DONG_THOI_MAY_B`/`POOL_KV_MAY_B`/`SO_SLOT` đã gỡ — số slot/pool là của TỪNG hồ sơ.
"""
from __future__ import annotations

import pathlib
import re

import yaml

from apps.ltt_llm import ngan_sach

GOC = pathlib.Path(__file__).resolve().parents[1]


def test_bi_danh_cu_DA_GO():
    """O-12: bí danh là hai tên cho một số — tên thứ hai là chỗ để lệch lần sau."""
    for ten in ("DONG_THOI_MAY_B", "POOL_KV_MAY_B", "SO_SLOT", "SO_SLOT_MAY_B",
                "POOL_KV", "LE"):
        assert not hasattr(ngan_sach, ten), f"ngan_sach con bi danh cu `{ten}`"


def test_manifest_doc_tu_nguon():
    """🔴 HỎI BẰNG `admission_cho(model)`, KHÔNG BẰNG BỘ BA TĨNH (dual-model 2.3).

    Từ 2.3 `text.chat` khai `admission_theo_model`, nên `tool.admission_slots`
    là **0** và `tool.admission_token_pool` là **0** — bản cũ của phép kiểm này
    sẽ đỏ, và đỏ vì một lý do sai: nó đang đọc một trường không còn mang câu trả
    lời chứ không phải vì ai gõ số tay.

    Điều nó ĐO vẫn nguyên: bản khai đọc từ `ngan_sach.py`, không gõ số.
    """
    from apps.ltt_llm.manifest import MANIFEST

    tool = MANIFEST.tools[0]
    for model, id_nb in (("ltt-3.8", "qwen38-api"), ("ltt-3.5", "qwen35-api")):
        h = ngan_sach.HO_SO[id_nb]
        suc = tool.admission_cho(model)
        assert suc is not None, f"{model} khong co trong admission_theo_model"
        assert suc.slots == h.seq_cap
        assert suc.token_pool == h.token_budget
        assert (suc.nguong_whale, suc.dem_uoc, suc.token_anh_toi_thieu,
                suc.token_anh_toi_da) == (
            h.nguong_whale, h.dem_uoc, h.token_anh_toi_thieu,
            h.token_anh_toi_da), model


def test_hai_may_dung_CUNG_MOT_phep_tinh_token_anh():
    """⭐ THAY `test_gateway_TOKEN_GIU_MOI_ANH_khop_ho_so` (28/09/2026).

    Phép cũ đối chiếu HAI HẰNG PHẲNG bằng nhau. Nay chi phí ngữ cảnh của một ảnh
    là một HÀM của kích thước, nên điều phải khớp không còn là một con số mà là
    **cả phép tính**: `platform_core/llm/anh_token.py` ≡ `llm_gateway/anh_token.py`
    (giống hệt từng byte — `tests/test_4203` canh), cộng hai tham số của nó
    (`--image-min-tokens`/`--image-max-tokens`) khớp giữa `HO_SO` và yaml
    (`tests/test_4205` canh).

    ⭐ Đây là bất biến "A nhận ⇒ B nhận" (A ⊆ B), cùng khuôn `uoc_token.py` đã
       giữ cho phần chữ: A giữ chỗ bằng ĐÚNG phép B đếm.

    ⛔ Hằng cũ `TOKEN_GIU_MOI_ANH` vẫn còn ở gateway làm đường lui khi KHÔNG đọc
       được trần engine — nó không còn nằm trên đường tính bình thường, nên phép
       này không đối chiếu nó nữa.
    """
    from llm_gateway import anh_token as at_b
    from platform_core.llm import anh_token as at_a

    assert not hasattr(ngan_sach, "TOKEN_GIU_MOI_ANH_DA_GO"), "canh ten"
    # Cùng phép tính, chứng minh bằng KẾT QUẢ trên đúng bảng đã đo 28/09.
    for rong, cao, mong in ((320, 240, 82), (1024, 768, 770), (1280, 720, 922),
                            (2048, 2048, 4098), (3840, 2160, 4082)):
        for m, h in ngan_sach.HO_SO.items():
            a = at_a.token_anh(rong, cao, toi_thieu=h.token_anh_toi_thieu,
                               toi_da=h.token_anh_toi_da) + at_a.TOKEN_DAU_VISION
            b = at_b.token_anh(rong, cao, toi_thieu=h.token_anh_toi_thieu,
                               toi_da=h.token_anh_toi_da) + at_b.TOKEN_DAU_VISION
            assert a == b == mong, (m, rong, cao, a, b, mong)
    # 770 chỉ đúng cho 1024x768 — KHÔNG phải "chi phí một ảnh".
    assert ngan_sach.TOKEN_MOI_ANH == 770


def test_tools_KHONG_con_khuyen_DONG_THOI_MAY_B():
    """Task 11 (18/09): `DONG_THOI_MAY_B` đã gỡ (L-23) — công cụ đo không được
    khuyên người chạy đặt lại nó (`tools/do_ngan_sach_chuyen_loi_thoai.py` từng in
    *"can ... `DONG_THOI_MAY_B=1`"*). Số suất nay là `HO_SO[m].seq_cap`.

    Ngoại lệ DUY NHẤT: `tools/check_ten_da_go.py` — bộ chặn tên đã gỡ phải gọi
    đúng tên nó chặn (bảng `TEN_DA_GO`), không phải lời khuyên đặt lại."""
    mien = {GOC / "tools" / "check_ten_da_go.py"}
    lech = [f"{p.relative_to(GOC)}:{i}"
            for p in sorted((GOC / "tools").rglob("*.py")) if p not in mien
            for i, dong in enumerate(p.read_text(encoding="utf-8",
                                                 errors="replace").splitlines(), 1)
            if "DONG_THOI_MAY_B" in dong]
    assert not lech, lech


def test_tai_lieu_cu_GAN_da_go_L23():
    """Task 11 (18/09): tài liệu còn tả env/công thức đã gỡ ở L-23 phải mang nhãn
    *ĐÃ GỠ (L-23* — không thì người đọc sau đặt lại một biến không còn tác dụng."""
    cam = (GOC / "docs" / "VLM_NOI_BO" / "CAM_CLI.md").read_text(encoding="utf-8")
    for dong in cam.splitlines():
        if "LTT_LLM_MAX_DONG_THOI" in dong:
            assert "ĐÃ GỠ (L-23" in dong, dong[:120]
    qd = (GOC / "docs" / "QUYET_DINH_NEN_TANG.md").read_text(encoding="utf-8")
    i = qd.index("### Q120 ")
    assert "ĐÃ GỠ (L-23" in qd[i:qd.index("\n###", i + 1)]


def test_manifest_khong_go_so_tay():
    """`admission_slots=1` gõ tay là đúng cái chồng chéo phép kiểm này sinh ra để dẹp."""
    van = (GOC / "apps" / "ltt_llm" / "manifest.py").read_text(encoding="utf-8")
    assert not re.search(r"admission_slots\s*=\s*\d", van)
    assert not re.search(r"admission_token_pool\s*=\s*\d", van)


def test_yaml_so_slot_cua_TUNG_ho_so_khop_so_slot():
    """🔵 `xfail(strict=True, reason="cho Task 3.3")` đã gỡ ngày 12/09.

    Task 3.3 viết lại `llama-swap.yaml` với `-np 3` cho **cả hai** hồ sơ, khớp
    `-np 3` (L-14, `10_BENCHMARK_P3.md` §G1b: 4 slot ở ngữ cảnh đã
    chốt tràn ~400 MiB sang RAM chủ trên 3090). 18/09 (C4, L-28) 3.5 lên `-np 4`
    — phép kiểm này không gõ số, nó chỉ bắt yaml và `HO_SO` bằng nhau.

    ⚠️ VÀ HÌNH DẠNG CỦA PHÉP ĐO ĐỔI, nên phép kiểm phải đổi theo. Bản cũ đọc
       `--parallel` trong **macro `CHUNG`** — một con số dùng chung cho mọi hồ sơ.
       Từ 3.3 con số ấy **không còn dùng chung được**: hai model nằm trên hai card
       kích thước khác nhau (24.576 so với 16.311 MiB), nên số slot là thuộc tính
       của TỪNG hồ sơ. Đọc macro sau 3.3 sẽ ném `ValueError` — và đỏ vì một lý do
       **sai**: nó đang tìm một chỗ không còn mang câu trả lời.

    ⭐ Điều nó đo vẫn nguyên và nay **mạnh hơn**: mọi hồ sơ phải khai đúng số
       slot của nguồn chân lý, chứ không chỉ một con số chung. Và macro **không
       được** khai lại một số slot toàn cục: một con số ở đó sẽ âm thầm áp cho hồ
       sơ tiếp theo ai đó thêm vào, kể cả khi card của nó không chịu nổi.
    """
    cfg = yaml.safe_load((GOC / "llm_gateway" / "deploy" / "llama-swap.yaml")
                         .read_text(encoding="utf-8"))
    macros = cfg.get("macros") or {}
    for ten, mo_ta in macros.items():
        tach = str(mo_ta).split()
        assert "-np" not in tach and "--parallel" not in tach, (
            f"macro {ten} khai lai so slot toan cuc: hai card khac kich thuoc "
            "nen so nay phai nam o TUNG ho so")

    ho_so = cfg.get("models") or {}
    assert ho_so, "llama-swap.yaml khong co ho so nao"
    for ten, m in ho_so.items():
        cmd = str(m["cmd"])
        for khoa, gt in macros.items():
            cmd = cmd.replace("${%s}" % khoa, str(gt))
        tach = cmd.split()
        co = "-np" if "-np" in tach else "--parallel"
        assert co in tach, f"{ten} khong khai so slot (`-np`)"
        so = tach[tach.index(co) + 1]
        assert int(so) == ngan_sach.HO_SO[ten].np, (
            f"llama-swap chay {ten} voi {co} {so} nhung ngan_sach.HO_SO khai "
            f"{ngan_sach.HO_SO[ten].np}")


def test_gateway_so_slot_DOC_tu_yaml_khong_con_mac_dinh_go_tay():
    """🔵 Phương án C bước 3: cổng không còn `LTT_LLM_MAX_DONG_THOI` (mặc định gõ
    tay trong `config.py`, bản sao thứ ba của `-np`). Nó đọc `-np` của TỪNG hồ
    sơ thẳng từ `llama-swap.yaml` — nên đối chiếu với chính yaml (đọc bằng
    PyYAML, độc lập với bộ đọc của cổng), không với một mặc định."""
    from llm_gateway.vat_ly import doc_tep

    van = (GOC / "llm_gateway" / "config.py").read_text(encoding="utf-8")
    assert not re.search(r'_int\("LTT_LLM_MAX_DONG_THOI', van), (
        "config.py lai go tay mot so slot cho cong")
    tep = GOC / "llm_gateway" / "deploy" / "llama-swap.yaml"
    cfg = yaml.safe_load(tep.read_text(encoding="utf-8"))
    cong = doc_tep(tep)
    for ten, m in (cfg.get("models") or {}).items():
        tach = str(m["cmd"]).split()
        assert cong[ten].np == int(tach[tach.index("-np") + 1]), ten
        if ten in ngan_sach.HO_SO:
            assert cong[ten].np == ngan_sach.HO_SO[ten].np, ten


def test_chieu_catalog_mang_pool_nhung_khong_lo_ra_khach():
    from apps.ltt_llm.manifest import MANIFEST
    from platform_core.public_api.catalog import project_tool

    projected = project_tool(MANIFEST, MANIFEST.tools[0])
    assert projected.admission_cho("ltt-3.8").token_pool == ngan_sach.POOL_38
    assert "admission_token_pool" not in projected.to_public_dict()
    assert "admission_theo_model" not in projected.to_public_dict(), (
        "ban chieu cong khai dang lo ten tai nguyen noi bo")


def test_tool_khac_mac_dinh_khong_ap_ngan_sach_token():
    """Mặc định 0 ⇒ mọi tool khác (ảnh, tiếng, video…) không đổi hành vi admission."""
    import dataclasses

    from platform_core.registry import ToolSpec

    mac_dinh = {f.name: f.default for f in dataclasses.fields(ToolSpec)}
    assert mac_dinh["admission_token_pool"] == 0

"""Người chọn model, **dữ liệu WanGP kiểm lại** — không phải ngược lại.

🔴 Bản đầu của phép kiểm này (và của `chon_model.py`) *suy ra* model từ
   `metadata`, và coi "nhiều hơn một model hợp" là lỗi. **Ảnh chụp thật bác nó**
   — xem `test_CA_KHO_thi_MO_HO_nen_du_lieu_KHONG_the_tu_chon`.
"""
from __future__ import annotations

import ast
import json
import pathlib

import pytest

from apps.lttvideo.chon_model import LoiChonModel, hinh_dang_dau_vao, kiem_model
from apps.lttvideo.ho_so import MODEL_THEO_DAU_VAO, WANGP_SHA

ANH_CHUP = (pathlib.Path(__file__).parent / "fixtures" / "wangp_metadata"
            / "1e1dd275.json")


def _kho() -> dict:
    return json.loads(ANH_CHUP.read_text(encoding="utf-8"))["model"]


# ── ảnh chụp là BẰNG CHỨNG, không phải bản chép tay ──────────────────────────


def test_anh_chup_neo_dung_SHA_ma_ho_so_dung():
    """Ảnh chụp nói về **engine bản nào**. Lệch SHA là lệch cả ngữ nghĩa."""
    d = json.loads(ANH_CHUP.read_text(encoding="utf-8"))
    assert d["wangp_sha"] == WANGP_SHA
    assert d["so_model"] == 225


def test_du_lieu_that_dung_khuon_tai_lieu_mo_ta():
    kho = _kho()
    t2v = kho["t2v_2_2"]["capabilities"]
    i2v = kho["i2v_2_2"]
    assert t2v["text_to_video"] is True
    assert t2v["image_to_video"] is False
    assert i2v["capabilities"]["image_to_video"] is True
    assert i2v["media_inputs"]["image"]["start"] is True


# ── vì sao KHÔNG suy ra model từ dữ liệu ─────────────────────────────────────


def test_CA_KHO_thi_MO_HO_nen_du_lieu_KHONG_the_tu_chon():
    """🔴 Số đo trên ảnh chụp thật, 225 model tại SHA ghim:

        chỉ chữ  → **150** model hợp
        có ảnh   →  **83**
        có video → **122**

    Và ngay trong hai model ta dùng, **cả hai** đều khai `text_to_video: true`.
    ⇒ Dữ liệu không xác định duy nhất câu trả lời. Mọi cách gỡ hoà là một bảng
      xếp hạng tự chế đội lốt suy luận.
    """
    kho = _kho()

    def hop(meta, hinh_dang):
        kn = meta.get("capabilities") or {}
        mi = meta.get("media_inputs") or {}
        a, v = mi.get("image") or {}, mi.get("video") or {}
        if hinh_dang == "video":
            return bool(v.get("control") or v.get("continue"))
        if hinh_dang == "anh":
            return bool(kn.get("image_to_video") and a.get("start"))
        return bool(kn.get("text_to_video"))

    dem = {h: sum(1 for m in kho.values() if hop(m, h))
           for h in ("chu", "anh", "video")}
    assert dem["chu"] > 100, dem
    assert dem["anh"] > 50, dem
    assert dem["video"] > 100, dem
    # va hai model ta dung cung nhau o nhanh `chu`
    assert hop(kho["t2v_2_2"], "chu") and hop(kho["i2v_2_2"], "chu")


# ── hình dạng đầu vào ────────────────────────────────────────────────────────


def test_hinh_dang_dau_vao():
    assert hinh_dang_dau_vao(co_anh=False, co_video=False) == "chu"
    assert hinh_dang_dau_vao(co_anh=True, co_video=False) == "anh"
    assert hinh_dang_dau_vao(co_anh=False, co_video=True) == "video"


def test_video_thang_anh_khi_dinh_ca_hai():
    """Video là ràng buộc chặt hơn."""
    assert hinh_dang_dau_vao(co_anh=True, co_video=True) == "video"


# ── hàng rào: bảng chọn phải khớp dữ liệu ────────────────────────────────────


def test_MOI_dong_trong_bang_chon_deu_dung_theo_du_lieu_that():
    """Chốt cả bảng, không chốt từng dòng — thêm một dòng sai là ĐỎ ngay."""
    kho = _kho()
    for hinh_dang, model in MODEL_THEO_DAU_VAO.items():
        kiem_model(model_type=model, hinh_dang=hinh_dang, kho_metadata=kho)


def test_gui_ANH_toi_model_khong_nhan_anh_thi_BI_CHAN():
    """⛔ Đây là lý do hàng rào tồn tại.

    WanGP **bỏ qua** media mà model không nhận — không lỗi, không cảnh báo. Ta
    chỉ biết khi xem video ra và không thấy ảnh của mình trong đó, sau khi đã
    trừ tiền khách.
    """
    with pytest.raises(LoiChonModel) as e:
        kiem_model(model_type="t2v_2_2", hinh_dang="anh", kho_metadata=_kho())
    assert "khung mo dau" in str(e.value)


def test_ten_model_go_sai_thi_BAO_LOI_chu_khong_im_lang():
    with pytest.raises(LoiChonModel) as e:
        kiem_model(model_type="khong_ton_tai", hinh_dang="chu",
                   kho_metadata=_kho())
    assert "anh chup" in str(e.value)


def test_MA_NGUON_khong_duoc_nhac_ten_model_nao():
    """⛔ Bảng chọn ở `ho_so` (cạnh các quyết định khác), không ở đây.

    Đọc **AST** chứ không quét văn bản: bộ quét văn bản sẽ báo động trên chính
    đoạn chú thích giải thích nó — lỗi đã mắc ba lần trong kho này.
    """
    tep = (pathlib.Path(__file__).parent.parent / "apps" / "lttvideo"
           / "chon_model.py")
    cay = ast.parse(tep.read_text(encoding="utf-8"))
    than = [n.value for n in ast.walk(cay)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and len(n.value) < 200]
    for s in than:
        thap = s.lower()
        for c in ("t2v", "i2v", "v2v", "vace", "animate", "wan2", "ltx"):
            assert c not in thap, f"mã nhắc tên model {c!r} trong hằng {s!r}"

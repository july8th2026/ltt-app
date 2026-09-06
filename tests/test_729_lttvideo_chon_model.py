"""Chọn model phải suy từ **dữ liệu WanGP công bố**, không từ tên gán cứng.

⚠️ Fixture dưới đây là bản **tay, tạm**, dựng theo đúng khuôn `metadata` mô tả ở
   `Wan2GP/docs/SETTINGS.md`. Nó sẽ được thay bằng **ảnh chụp thật** lấy từ
   `get_model_schema()` trên pod (việc `T1` của `PLAN_V1_CHI_TIET.md`). Giữ tên
   khoá y hệt tài liệu để lúc thay không phải sửa phép kiểm.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from apps.lttvideo.chon_model import LoiChonModel, chon_model

#: Khuôn theo `SETTINGS.md`. Tên model đặt trung tính **có chủ ý**: phép kiểm
#: không được phụ thuộc vào tên thật, vì mã cũng không được phụ thuộc.
KHO_TAM = {
    "chu_thanh_video": {
        "capabilities": {"text_to_video": True, "image_to_video": False},
        "media_inputs": {"image": {"start": False}, "video": {}},
    },
    "anh_thanh_video": {
        "capabilities": {"text_to_video": False, "image_to_video": True},
        "media_inputs": {"image": {"start": True, "reference": True}, "video": {}},
    },
    "video_dieu_khien": {
        "capabilities": {"text_to_video": False, "image_to_video": False},
        "media_inputs": {"image": {}, "video": {"control": True, "continue": True}},
    },
}


def test_khong_media_thi_chon_model_sinh_tu_CHU():
    assert chon_model(co_anh=False, co_video=False,
                      kho_metadata=KHO_TAM) == "chu_thanh_video"


def test_co_anh_thi_chon_model_nhan_ANH_LAM_KHUNG_MO_DAU():
    assert chon_model(co_anh=True, co_video=False,
                      kho_metadata=KHO_TAM) == "anh_thanh_video"


def test_co_video_thi_chon_model_nhan_VIDEO():
    assert chon_model(co_anh=False, co_video=True,
                      kho_metadata=KHO_TAM) == "video_dieu_khien"


def test_video_thang_anh_khi_dinh_ca_hai():
    """Đính cả hai thì video là ràng buộc chặt hơn — ít model nhận được nó."""
    assert chon_model(co_anh=True, co_video=True,
                      kho_metadata=KHO_TAM) == "video_dieu_khien"


def test_co_anh_ma_model_chi_co_CO_TONG_thi_KHONG_chon():
    """`image_to_video` là cờ tổng; `media_inputs.image.start` mới là lời hứa.

    Một model bật cờ tổng nhưng chỉ nhận ảnh **tham chiếu** thì không làm được
    thứ composer đang hứa ("dùng ảnh của bạn làm khung mở đầu").
    """
    kho = {"chi_tham_chieu": {
        "capabilities": {"image_to_video": True},
        "media_inputs": {"image": {"start": False, "reference": True}},
    }}
    with pytest.raises(LoiChonModel):
        chon_model(co_anh=True, co_video=False, kho_metadata=kho)


def test_khong_co_model_nao_hop_thi_BAO_LOI_chu_khong_tra_bua():
    with pytest.raises(LoiChonModel):
        chon_model(co_anh=True, co_video=False, kho_metadata={})


def test_MO_HO_la_LOI_chu_khong_phai_cho_de_doan():
    """Hai model cùng hợp ⇒ mọi cách xếp hạng ta nghĩ ra đều là bảng tự chế."""
    kho = {
        "a": {"capabilities": {"text_to_video": True}, "media_inputs": {}},
        "b": {"capabilities": {"text_to_video": True}, "media_inputs": {}},
    }
    with pytest.raises(LoiChonModel) as e:
        chon_model(co_anh=False, co_video=False, kho_metadata=kho)
    assert "mo ho" in str(e.value)


def test_MA_NGUON_khong_duoc_nhac_ten_model_nao():
    """⛔ Một tên gán cứng ở đây là một bảng ánh xạ tay, và bảng ấy sẽ trôi.

    Đọc **AST** chứ không quét văn bản: bộ quét văn bản sẽ báo động trên chính
    đoạn chú thích giải thích nó — lỗi đã mắc hai lần trong kho này.
    """
    tep = (pathlib.Path(__file__).parent.parent / "apps" / "lttvideo"
           / "chon_model.py")
    cay = ast.parse(tep.read_text(encoding="utf-8"))
    chuoi = [n.value for n in ast.walk(cay)
             if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    # bo qua docstring: chung la chu thich, khong phai hanh vi
    than = [s for s in chuoi if len(s) < 200]
    cam = ("t2v", "i2v", "v2v", "vace", "animate", "wan2", "ltx", "hunyuan")
    for s in than:
        thap = s.lower()
        for c in cam:
            assert c not in thap, f"mã nhắc tên model {c!r} trong hằng {s!r}"

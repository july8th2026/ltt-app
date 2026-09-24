"""`UU_TIEN_KHO_CHUNG` phải trỏ vào giọng mà PHÉP ĐO chọn, không vào một cái tên.

🔴 Vì sao cần phép kiểm này: hằng số ấy là hai chuỗi `vc_<32hex>` không ai đọc
   được bằng mắt. Ngày ai đó "dọn dẹp" hay chép nhầm một ký tự, mã vẫn chạy —
   `_rang_kho_chung` chỉ thấy một `public_id` không khớp ai, rơi về sắp theo
   `public_id`, và AUTO_MATCH lặng lẽ trả về một giọng khác.

Nguồn số: `docs/auto_scan_video_final/L_DO_GIONG.md` mục 5–6 (23/09/2026).
"""
from __future__ import annotations

import json
import pathlib

from apps.auto_scan_video.rang_giong import UU_TIEN_KHO_CHUNG

KHO = pathlib.Path(r"C:\LTTPlatform\data\voice_goc\kho_chung\manifest.json")

#: `public_id` -> tên hiển thị, cho thông điệp lỗi đọc được.
OWEN = "vc_526cb3ffb0d14558aadf199db27c0507"
CLARA = "vc_a55b2ad1646349469d5c5a39d4d20dc0"
#: Bản CŨ, chọn bằng "nhịp gần 156 từ/phút" — một mốc mà giọng chậm nhất kho
#: (181,9 từ/phút) vẫn vượt 17%. Giữ ở đây để ngày ai đó quay lại nó, phép kiểm
#: nói ra rằng đó là một bước LÙI có tên.
DOUGLAS = "vc_1b65a9e636a54ab59c6a69b8046d3d0a"


def test_mot_nam_mot_nu_va_dung_hai():
    """Hai mục, không hơn: `_rang_kho_chung` lọc giới TRƯỚC rồi mới sắp, nên
    thứ tự này chỉ cần một ứng viên dẫn đầu cho mỗi giới."""
    assert UU_TIEN_KHO_CHUNG == (OWEN, CLARA)


def test_khong_quay_lai_lua_chon_theo_nhip_doc():
    assert DOUGLAS not in UU_TIEN_KHO_CHUNG, (
        "Douglas duoc chon bang 'nhip gan 156 tu/phut', va do 34 luot doc that "
        "cho thay giong cham nhat kho la 181,9 tu/phut — khong ai toi gan moc "
        "do. Xem L_DO_GIONG.md muc 6.1 truoc khi dat lai."
    )


def test_moi_public_id_la_mot_giong_co_that_trong_kho_chung():
    """⛔ Một `public_id` gõ sai KHÔNG làm gì hỏng ồn ào — nó chỉ làm thứ tự ưu
    tiên im lặng biến mất. Phép kiểm này là chỗ duy nhất bắt được."""
    if not KHO.is_file():
        import pytest
        pytest.skip("khong co kho clip goc tren may nay")
    co = {g["public_id"]: g for g in json.loads(KHO.read_text(encoding="utf-8"))["giong"]}
    for pid in UU_TIEN_KHO_CHUNG:
        assert pid in co, f"{pid} khong phai giong nao trong kho chung"
        assert co[pid]["ngon_ngu"] == "en", (pid, co[pid]["ngon_ngu"])
    # Hai muc phai la HAI giong khac nhau — mot danh sach uu tien co hai dong
    # giong het nhau van "chay dung" va van bo mat mot nua.
    assert len(set(UU_TIEN_KHO_CHUNG)) == len(UU_TIEN_KHO_CHUNG)

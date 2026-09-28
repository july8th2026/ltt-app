"""Bánh cóc: tool CHƯA khai đủ hợp đồng V2 chỉ được ÍT ĐI (spec §4.5, §19).

⭐ Chốt TẬP HỢP chứ không chốt SỐ LƯỢNG — cùng bài học `check_so_test`: một
   thiếu sót MỚI vẫn lọt nếu một thiếu sót CŨ được dọn trong cùng lượt.

⚠️ CÁI TỆP NÀY ĐO ĐƯỢC GÌ, nói trước để không ai đọc thừa (vòng sửa 1 Task 7):

   · `idempotency` + `resource` — `nut.chua_du_hop_dong()` đọc được vì cả hai
     mặc định RỖNG: "khai rồi" và "quên khai" phân biệt được.
   · `resource["class"]` — `registry.RESOURCE_KEYS` chỉ đóng **tên khoá**, không
     đóng **giá trị**, và `chua_du_hop_dong` nhận MỌI dict khác rỗng. Nên
     `{"slots": 0}` không có `class` từng tính là "đủ".
     `test_resource_phai_khai_class_thuoc_tu_vung` bịt đúng chỗ đó.
   · `side_effect` — ⛔ KHÔNG đọc được từ registry: `ToolSpec.side_effect` mặc
     định `"external"`, nên một tool khai tường minh và một tool quên khai ra
     cùng một giá trị. Muốn đo thì phải đọc NGUỒN, và đó là việc của
     `test_side_effect_duoc_khai_TUONG_MINH` bên dưới (AST, không import).
"""
from __future__ import annotations

import ast

import pytest

from platform_core import registry
from platform_core.workflow import nut
from platform_core.workflow.cong_cu import tat_ca

#: ⛔ CHỈ ĐƯỢC CO LẠI. Lý do từng tool: plan 02 Task 7 (ba làn VRAM).
CHUA_DU = frozenset({"video.upscale", "image.upscale"})


def test_khong_tool_nao_MOI_bi_thieu():
    thieu = nut.chua_du_hop_dong(tat_ca())
    moi = sorted(set(thieu) - CHUA_DU)
    assert not moi, ("tool MOI thieu truong hop dong V2:\n  "
                     + "\n  ".join(f"{t}: thieu {thieu[t]}" for t in moi))


def test_danh_sach_mien_tru_khong_chua_thu_da_xong():
    thieu = nut.chua_du_hop_dong(tat_ca())
    thua = sorted(CHUA_DU - set(thieu))
    assert not thua, f"`CHUA_DU` con {thua} nhung chung da khai du — go khoi danh sach"


def test_phep_kiem_nay_thuc_su_doc_duoc_registry():
    # Doi chung: `tat_ca()` rong thi hai bai tren deu xanh ma khong do gi.
    # ⚠️ **19 -> 18 va 17 -> 16 (28/09/2026).** `apps/prompt_canh` bi xoa
    #    (`0c2aabab`) va no mang theo DUNG MOT tool `prompt_canh.run` — doc lai
    #    tu `git show 0c2aabab^:apps/prompt_canh/manifest.py:61-64`.
    #    ⭐ Ba diem chot da do de duoc HA moc, khong phai mot:
    #      1. CA BON phep dem tut DUNG 1 (19->18 x3, 17->16), khong phai 2+;
    #      2. `test_khong_app_nao_hong_luc_nap` XANH => khong app nao rung khoi
    #         registry vi sai kieu, tuc so tut KHONG phai do lo hong nay canh;
    #      3. ten tool mat di khop app bi xoa.
    #    ⛔ Thieu bat ky diem nao thi ha moc la GIAU mot hoi quy that.
    assert len(tat_ca()) >= 18


def test_khong_app_nao_hong_luc_nap():
    """⛔ Đối chứng cho MỌI phép kiểm TẬP HỢP trong tệp này.

    Một trường sai KIỂU (vd `resource["slots"]` là chuỗi) làm
    `_validate_hop_dong_v2` ném **bên trong** `discover()`, và `discover()` nuốt
    nó vào `item.error` (`registry.py:1642-1648`). Hậu quả: MỌI tool của app đó
    biến khỏi `tat_ca()` — nên mọi bài dạng "không tool nào thiếu" vẫn XANH,
    chỉ hai phép ĐẾM (`>= 18`, `== 16`) bắt được. Bài này làm cái hỏng lộ ra
    kèm TÊN APP và LỖI, thay vì để đọc một con số đếm lệch rồi đoán.
    """
    hong = [(it.manifest.slug, it.error) for it in registry.discover() if it.error]
    assert not hong, "app khong nap duoc:\n  " + "\n  ".join(
        f"{slug}: {loi}" for slug, loi in hong)


def test_16_tool_len_duoc_palette_workflow():
    # ⭐ Chốt SỐ ở đây là cố ý, ngược với docstring đầu tệp: đây là phép duy
    #    nhất bắt được một app rụng khỏi registry vì sai kiểu (xem
    #    `test_khong_app_nao_hong_luc_nap`). Hai bài cùng canh một lỗ.
    app = {t for t in nut.tat_ca() if t.startswith("app.")}
    assert len(app) == 16, sorted(app)
    assert "app.video.upscale" not in app and "app.image.upscale" not in app


def test_resource_phai_khai_class_thuoc_tu_vung():
    """`resource` khác rỗng CHƯA phải khai đủ — phải nói rõ LỚP tài nguyên.

    `chua_du_hop_dong` chỉ hỏi "dict có rỗng không", nên `{"slots": 0}` đi lọt.
    Mà `class` mới là thứ scheduler dùng để xếp chỗ: thiếu nó thì `vram_min_mb`
    và `slots` không gắn vào tài nguyên nào cả.
    """
    thieu = {ten: cc.resource for ten, cc in tat_ca().items()
             if ten not in CHUA_DU
             and (cc.resource or {}).get("class") not in nut.RESOURCE_CLASS}
    assert not thieu, ("resource thieu `class` hop le "
                       f"(chi {list(nut.RESOURCE_CLASS)}): {thieu}")


# ── `side_effect`: đo bằng NGUỒN, vì registry đã mất dấu ────────────────────

def _khai_side_effect_trong_nguon() -> dict[str, bool]:
    """`{tên tool: có gõ `side_effect=` trong chính lời gọi ToolSpec không}`.

    Đọc AST chứ không import: giá trị sau khi import đã bị mặc định
    `"external"` của `ToolSpec` nuốt mất, không còn phân biệt được.
    """
    ra: dict[str, bool] = {}
    for tep in sorted(registry.APPS_DIR.glob("*/manifest.py")):
        cay = ast.parse(tep.read_text(encoding="utf-8"), filename=str(tep))
        for nut_ in ast.walk(cay):
            if not isinstance(nut_, ast.Call):
                continue
            ham = nut_.func
            ten_ham = (ham.attr if isinstance(ham, ast.Attribute)
                       else getattr(ham, "id", ""))
            if ten_ham != "ToolSpec":
                continue
            kw = {k.arg: k.value for k in nut_.keywords if k.arg}
            ten = kw.get("name")
            if not isinstance(ten, ast.Constant) or not isinstance(ten.value, str):
                pytest.fail(f"{tep.name}: ToolSpec khong khai `name=` hang chuoi "
                            f"(dong {nut_.lineno}) — bai kiem nay khong doc duoc nua")
            ra[ten.value] = "side_effect" in kw
    return ra


def test_may_doc_AST_nay_thuc_su_phan_biet_duoc():
    """Đối chứng: một bài "ai cũng khai" mà máy đọc luôn trả True thì vô nghĩa.

    Hai tool hoãn (`CHUA_DU`) KHÔNG khai `side_effect` trong nguồn, và chúng
    phải hiện ra là `False`. Nếu ngày nào đó chúng được khai, bài này đỏ và
    người sửa phải chọn một tool KHÁC làm mẫu âm — không được xoá đối chứng.
    """
    khai = _khai_side_effect_trong_nguon()
    assert len(khai) >= 18, f"chi doc duoc {len(khai)} ToolSpec trong nguon"
    am = sorted(t for t in CHUA_DU if khai.get(t) is False)
    assert am == sorted(CHUA_DU), (
        "mau am mat: may doc AST khong con phan biet duoc khai/khong khai", khai)


def test_side_effect_duoc_khai_TUONG_MINH():
    """Tool lên palette phải GÕ `side_effect=`, không sống nhờ mặc định.

    Mặc định `"external"` nghĩa là "được thử lại sau khi kiểm khoá khử trùng".
    Một tool `irreversible` (gửi mail, tạo VPS) quên khai sẽ IM LẶNG nhận hành
    vi đó — `registry.py:454-468` mô tả đúng cái giá. Nên ở đây "quên" và
    "cố ý external" bắt buộc phải phân biệt được, và chỗ duy nhất phân biệt
    được là nguồn.
    """
    khai = _khai_side_effect_trong_nguon()
    thieu = sorted(t for t, co in khai.items() if not co and t not in CHUA_DU)
    assert not thieu, f"tool khong go `side_effect=`, an mac dinh external: {thieu}"

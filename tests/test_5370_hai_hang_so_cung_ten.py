"""Hai đại lượng khác nhau ⛔ không được dùng chung một cái tên.

App này từng khai **hai hằng số khác giá trị cùng tên `MAX_SCENES`**:

  · `project_schema.MAX_SCENES = 20`      — số **cảnh kịch bản**
  · `services/storyboard.MAX_SCENES = 60` — số **khung hình** một storyboard

Cả hai con số đều ĐÚNG. Cái sai là cái **tên**: spec §4.3 (S-1…S-5) đã phán
quyết `ommi_scene` là *khung hình*, ⛔ không phải *cảnh kịch bản*, và một cái tên
dùng cho hai đại lượng là cách chắc chắn để người sau thấy `20` cạnh `60` rồi
"sửa cho khớp" — làm vỡ một trong hai đường.

Bài này khoá hai thứ, và cả hai đều đo **hành vi**, ⛔ không đo cách gõ:

1. Hai tên phân biệt được (`storyboard` ⛔ không còn xuất `MAX_SCENES`).
2. `manifest.py` kẹp `scene_count` **theo hằng số**, không theo số gõ tay. Đây
   là bất biến **B-6** (spec §8) áp cho chính app này: `manifest._cost` tính
   TIỀN ở cửa, `jobs.py` làm VIỆC ở worker; hai bên đọc lệch nhau thì khách trả
   tiền cho số cảnh mà đường chạy không giao.
"""
from __future__ import annotations

from apps.prompt_ai_ommi import manifest as mf
from apps.prompt_ai_ommi.project_schema import MAX_SCENES
from apps.prompt_ai_ommi.services import storyboard as sb


def _scene_count_schema() -> list[dict]:
    """`scene_count` trong params_schema của MỌI ToolSpec khai nó."""
    ra = []
    for tool in mf.MANIFEST.tools:
        item = (tool.params_schema or {}).get("scene_count")
        if item:
            ra.append(item)
    return ra


def test_hai_dai_luong_khong_dung_chung_ten():
    assert sb.MAX_KHUNG_HINH == 60
    assert MAX_SCENES == 20
    # ⛔ Ten cu khong duoc song lai: co no la co duong cho hai dai luong nhap lai.
    assert not hasattr(sb, "MAX_SCENES"), (
        "storyboard lai xuat MAX_SCENES — trung ten voi project_schema")


def test_moi_toolspec_khai_scene_count_deu_kep_theo_hang_so():
    """⛔ Không phải phép kiểm chuỗi: đọc giá trị THẬT trong manifest đã dựng."""
    khai = _scene_count_schema()
    # Doi chung: neu khong tim thay khai nao thi phep kiem nay VO NGHIA —
    # mot vong lap tren tap rong luon xanh ma khong chung minh gi.
    assert len(khai) >= 2, f"mong >= 2 ToolSpec khai scene_count, thay {len(khai)}"
    for item in khai:
        assert item["max"] == MAX_SCENES, (
            f"scene_count.max = {item['max']} nhung MAX_SCENES = {MAX_SCENES}")


def test_gia_kep_o_dung_hang_so_chu_khong_o_so_go_tay():
    """Nếu `_cost` kẹp ở một số gõ tay khác `MAX_SCENES`, hai giá này lệch nhau.

    Đây là phép đo **hành vi**: gọi hàm tính giá thật với số cảnh vượt trần và
    với đúng trần. Kẹp đúng ⇒ hai giá bằng nhau.
    """
    for operation in ("director", "storyboard"):
        tai_tran = mf._cost({"operation": operation, "scene_count": MAX_SCENES})
        vuot_tran = mf._cost({"operation": operation, "scene_count": MAX_SCENES + 7})
        assert tai_tran == vuot_tran, (
            f"{operation}: gia o {MAX_SCENES} canh ({tai_tran}) khac gia o "
            f"{MAX_SCENES + 7} canh ({vuot_tran}) — dang kep o so go tay")

    # Tiem loi: mot so DUOI tran phai cho gia KHAC, khong thi phep tren xanh oan
    # vi ham tra hang so bat ke dau vao.
    assert mf._cost({"operation": "director", "scene_count": 1}) != \
        mf._cost({"operation": "director", "scene_count": MAX_SCENES})


def test_tran_so_canh_di_ra_frontend_tu_HANG_SO_backend():
    """Frontend ⛔ không được gõ lại trần — nó phải nhận qua `data-max-scenes`.

    Trước khi có đường này, `StudioShell.tsx` gõ `TRAN_SO_CANH = 20` trong khi
    backend kẹp ở `project_schema.MAX_SCENES = 20`. Hai chỗ khai cùng một đại
    lượng, và chỗ lệch nằm ngay trong `max` của input **khách đang gõ**.

    ⭐ Phép kiểm đo **cả đường**, không đo một đầu: hằng số đi vào ngữ cảnh
    template (`_render_workspace`) và template thật có đúng thuộc tính đó.
    """
    import inspect
    import pathlib

    from apps.prompt_ai_ommi.routes import _shared

    # 1. Ham dung ngu canh template phai DOC hang so, khong go so.
    src = inspect.getsource(_shared._render_workspace)
    assert '"max_scenes": MAX_SCENES' in src, (
        "_render_workspace khong dua MAX_SCENES ra template")
    assert '"max_scenes": 20' not in src, "go tay so 20 thay vi hang so"

    # 2. Template phai THAT SU mang thuoc tinh do (mot bien ngu canh khong ai
    #    doc thi bang khong co).
    html = (pathlib.Path("apps/prompt_ai_ommi/templates")
            / "prompt_ai_ommi_workspace.html").read_text(encoding="utf-8")
    assert 'data-max-scenes="{{ max_scenes }}"' in html

    # 3. Frontend phai DOC dataset do, khong go lai tran.
    tsx = (pathlib.Path("frontend/prompt-ai-ommi/src/main.tsx")
           .read_text(encoding="utf-8"))
    assert "root.dataset.maxScenes" in tsx

    # Doi chung: neu ba phep tren chi la "tim chuoi trong tep" thi mot chuoi bia
    # cung phai KHONG tim thay — khong the ca ba deu xanh vi tep qua lon.
    assert "data-khong-he-ton-tai" not in html

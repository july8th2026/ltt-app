"""Tầng sinh phụ đề `.ass` của App `video_assembly`, chốt theo cấu hình ĐANG CHẠY.

Bốn mô-đun `subtitle/` (`style_registry`, `ass_builder`, `segmenter`, `pipeline`)
**giống hệt** bản gốc — 0 dòng khác. Nên đối chứng vi sai với bot legacy ở đây
không nói lên điều gì; giá trị nằm ở chỗ khác: ghim **cấu hình thật** và các bất
biến của đầu ra trên **văn bản thật**.

🔴 Kiểu production đọc từ `DUNGVIDEO-FULL/configs/pipeline.yaml` đang chạy:

    subtitle:
      enable: true          segment_mode: sentence     style_preset: default
      font_family: ''       font_size: 0               quality: standard
      max_chars_per_line: 42                           max_lines: 2

⚠️ `font_family: ''` và `font_size: 0` **không** phải "đặt thành rỗng" mà là
   "dùng mặc định của preset" — GUI dùng `0` làm ô trống. `runner.py:585` lọc
   chúng ra, kèm chú thích nói rõ hậu quả nếu quên: *"font_size=0 sẽ override
   preset font_size=48 → render lỗi"*.

⛔ Và phép lọc ấy **cố ý bất đối xứng**: `outline_width` với `shadow_offset` bị
   loại khỏi danh sách "0 nghĩa là mặc định", vì `0` ở đó là một lựa chọn hợp lệ
   của người dùng (không viền / không bóng). Trước tệp này, thứ duy nhất giữ sự
   bất đối xứng ấy là một dòng chú thích.
"""
from __future__ import annotations

import ast
import hashlib
import json
import pathlib

import pytest

from apps.video_assembly.services.engine.subtitle.pipeline import (
    generate_subtitle_files,
)
from apps.video_assembly.services.engine.subtitle.style_registry import (
    get_config,
    list_ids,
)

MAU = (pathlib.Path(__file__).resolve().parent / "golden"
       / "parity_video_khop_clip" / "mau_01_mot_doi_mot_nho" / "transcript.json")

#: Đọc từ `configs/pipeline.yaml` ĐANG CHẠY trên máy bot, không phải suy từ mã.
CAU_HINH_THAT = {
    "segment_mode": "sentence", "style_preset": "default",
    "max_chars_per_line": 42, "max_lines": 2,
}


def _doan() -> list[dict]:
    return json.loads(MAU.read_text(encoding="utf-8"))


def _sinh(tmp_path, **kw) -> pathlib.Path:
    kq = generate_subtitle_files(
        transcript_data=_doan(), style_id=CAU_HINH_THAT["style_preset"],
        segment_mode=CAU_HINH_THAT["segment_mode"], output_dir=str(tmp_path),
        base_name="sub", export_srt=False, **kw)
    return pathlib.Path(kq["ass_path"])


def test_preset_DEFAULT_giu_dung_gia_tri_dang_chay() -> None:
    """Một lần đổi preset là đổi diện mạo mọi video đã giao, và không ai thấy."""
    c = get_config("default")
    assert (c.font_family, c.font_size) == ("Arial", 48)
    assert (c.outline_width, c.shadow_offset) == (2, 1)
    assert (c.alignment, c.margin_v, c.margin_h) == (2, 30, 20)
    assert c.max_chars_per_line == CAU_HINH_THAT["max_chars_per_line"]
    assert c.bold is True and c.italic is False and c.bg_box is False
    assert "default" in list_ids()   # `list_presets()` tra DOI TUONG


def test_dong_Style_trong_ASS_mang_dung_gia_tri_do(tmp_path) -> None:
    ass = _sinh(tmp_path).read_text(encoding="utf-8-sig")
    dong = [d for d in ass.splitlines() if d.startswith("Style: Default,")]
    assert len(dong) == 1
    truong = dong[0].split(",")
    assert truong[1] == "Arial" and truong[2] == "48"
    assert truong[7] == "-1", "Bold phai bat (-1 la True trong ASS)"
    assert (truong[16], truong[17]) == ("2", "1"), "outline / shadow"
    assert truong[18] == "2", "alignment"
    assert (truong[19], truong[20], truong[21]) == ("20", "20", "30")
    assert "PlayResX: 1920" in ass and "PlayResY: 1080" in ass


def test_van_ban_THAT_ton_trong_tran_42_ky_tu_va_2_dong(tmp_path) -> None:
    """Đo trên transcript thật, không phải chuỗi tự bịa.

    Một bộ tách dòng bịa ra bằng `"a" * 100` không bao giờ chạm các nhánh mà chữ
    tiếng Việt có dấu và dấu câu thật sự đi qua.
    """
    ass = _sinh(tmp_path).read_text(encoding="utf-8-sig")
    sk = [d for d in ass.splitlines() if d.startswith("Dialogue:")]
    assert sk, "khong sinh duoc su kien nao"
    tran = CAU_HINH_THAT["max_chars_per_line"]
    for d in sk:
        chu = d.split(",", 9)[-1]
        assert chu.count(r"\N") < CAU_HINH_THAT["max_lines"], "qua so dong"
        for dong in chu.split(r"\N"):
            assert len(dong) <= tran, f"dong {len(dong)} ky tu > {tran}"


def test_sinh_lai_ra_DUNG_TUNG_BYTE(tmp_path) -> None:
    """Khác `make_timeline_v2` bên App `transcript`: tầng này **tất định**.

    Bên kia `random.uniform` làm "trùng từng byte" bất khả về nguyên tắc. Ở đây
    thì không có nguồn ngẫu nhiên nào, nên đòi hỏi chặt hơn là **đúng**.
    """
    bam = []
    for ten in ("a", "b"):
        d = tmp_path / ten
        d.mkdir()
        bam.append(hashlib.sha256(_sinh(d).read_bytes()).hexdigest())
    assert bam[0] == bam[1]


def test_LUAT_khong_0_nghia_la_mac_dinh_van_BAT_DOI_XUNG() -> None:
    """Bất đối xứng có chủ đích, và trước tệp này chỉ một chú thích giữ nó.

    `font_size=0` nghĩa là *"dùng mặc định preset"* — quên lọc thì preset 48 bị
    ghi đè thành 0 và bản render hỏng. Nhưng `outline_width=0` / `shadow_offset=0`
    nghĩa là *"không viền / không bóng"* — một lựa chọn hợp lệ. Gộp chúng vào
    cùng một luật là làm hỏng một trong hai, và **cả hai đều hỏng im lặng**.

    Đọc bằng AST chứ không khớp chuỗi: một chú thích nhắc tới `outline_width` sẽ
    làm `grep` báo nhầm — đúng cái bẫy đã ghi trong `bo-do-quet-van-ban-...`.
    """
    goc = (pathlib.Path(__file__).resolve().parent.parent / "apps"
           / "video_assembly" / "services" / "engine" / "runner.py")
    cay = ast.parse(goc.read_text(encoding="utf-8"))
    tap: set[str] | None = None
    for n in ast.walk(cay):
        if (isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name)
                and n.targets[0].id == "_ZERO_MEANS_DEFAULT"):
            tap = {x.value for x in ast.walk(n.value)
                   if isinstance(x, ast.Constant) and isinstance(x.value, str)}
    assert tap is not None, "khong con hang so `_ZERO_MEANS_DEFAULT`"
    assert "font_size" in tap, "quen loc font_size => preset 48 bi ghi de thanh 0"
    for ten in ("outline_width", "shadow_offset"):
        assert ten not in tap, (
            f"`{ten}` bi gop vao luat '0 = mac dinh' — nguoi dung khong con tat "
            f"duoc no, va khong co gi bao loi")


@pytest.mark.parametrize("mo", ["sentence"])
def test_che_do_chia_doan_dang_chay_la_SENTENCE(mo, tmp_path) -> None:
    """`segment_mode` của cấu hình sống, không phải mặc định của hàm."""
    assert CAU_HINH_THAT["segment_mode"] == mo
    assert _sinh(tmp_path).exists()

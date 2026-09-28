"""Spec §4.6 — lược đồ tham số là tập con JSON Schema 2020-12 + ba khoá x-ltt-*.

⚠️ `ToolSpec.params_schema` KHÔNG phải JSON Schema (ledger 22/09). Tệp này là
   chỗ duy nhất biết cả hai từ vựng — không chỗ nào khác được dịch lại.
"""
from __future__ import annotations

import pytest

from platform_core.workflow import luoc_do


def test_nguyen_thuy_sang_json_schema():
    ra = luoc_do.sang_json_schema({
        "prompt": {"type": "string", "required": True, "max_length": 4000},
        "count": {"type": "int", "min": 1, "max": 4, "default": 1},
        "temperature": {"type": "number", "min": 0.0, "max": 2.0},
        "preview": {"type": "bool", "default": False},
    })
    assert ra["type"] == "object" and ra["additionalProperties"] is False
    assert ra["required"] == ["prompt"]
    p = ra["properties"]
    assert p["prompt"] == {"type": "string", "maxLength": 4000}
    assert p["count"] == {"type": "integer", "minimum": 1, "maximum": 4,
                          "default": 1}
    assert p["temperature"] == {"type": "number", "minimum": 0.0, "maximum": 2.0}
    assert p["preview"] == {"type": "boolean", "default": False}


def test_enum_lay_kieu_tu_chinh_gia_tri():
    # `target_height` của `video.upscale` là enum SỐ — ép "string" ở đây làm
    # form gửi "1080" và validator server từ chối.
    ra = luoc_do.sang_json_schema({
        "target_height": {"type": "enum", "values": [1080, 1440], "default": 1080},
        "codec": {"type": "enum", "values": ["h264", "hevc"]},
    })["properties"]
    assert ra["target_height"] == {"type": "integer", "enum": [1080, 1440],
                                   "default": 1080}
    assert ra["codec"] == {"type": "string", "enum": ["h264", "hevc"]}


def test_media_va_json_mang_x_ltt_kieu():
    ra = luoc_do.sang_json_schema({
        "anh": {"type": "image"}, "bo_anh": {"type": "image[]"},
        "cau_hinh": {"type": "json"}, "messages": {"type": "json[]"},
    })["properties"]
    assert ra["anh"] == {"type": "string", "x-ltt-kieu": "image"}
    assert ra["bo_anh"] == {"type": "array", "items": {"type": "string"},
                            "x-ltt-kieu": "image[]"}
    assert ra["cau_hinh"] == {"type": "object", "x-ltt-kieu": "json"}
    assert ra["messages"] == {"type": "array", "items": {"type": "object"},
                              "x-ltt-kieu": "json[]"}


def test_text_va_model_ref_mang_goi_y_widget():
    ra = luoc_do.sang_json_schema({
        "noi_dung": {"type": "text"},
        "model": {"type": "model_ref", "values": ["a", "b"]},
    })["properties"]
    assert ra["noi_dung"]["x-ltt-control"] == "textarea"
    assert ra["model"]["x-ltt-control"] == "dropdown-dong"
    assert ra["model"]["x-ltt-kieu"] == "model_ref"
    assert ra["model"]["enum"] == ["a", "b"]


def test_tham_so_measured_from_bi_danh_dau_may_tu_dien():
    # `duration_s` do nền tảng đo bằng ffprobe — bắt khách nhập là sai, và
    # để nó thành `required` là chặn publish một đồ thị đúng.
    ra = luoc_do.sang_json_schema(
        {"duration_s": {"type": "number", "min": 0, "measured_from": "video_key"}})
    assert ra["required"] == []
    assert ra["properties"]["duration_s"]["x-ltt-control"] == "may_tu_dien"
    assert ra["properties"]["duration_s"]["readOnly"] is True


def test_kieu_la_thi_NEM_chu_khong_im_lang_bo_qua():
    with pytest.raises(luoc_do.LoiLuocDo, match="kieu tham so chua co tu vung"):
        luoc_do.sang_json_schema({"x": {"type": "duong_ong"}})


def test_cong_vao_suy_tu_params_schema():
    vao = dict(luoc_do.cong_vao(
        {"prompt": {"type": "string", "required": True},
         "anh": {"type": "image"},
         "duration_s": {"type": "number", "measured_from": "anh"}}, {}))
    assert vao["prompt"].type == "text" and vao["prompt"].required is True
    assert vao["anh"].type == "image" and vao["anh"].required is False
    # Tham số nền tảng tự điền KHÔNG phải một cổng: không ai nối được vào nó.
    assert "duration_s" not in vao


def test_cong_khai_tay_DE_LEN_phan_suy():
    vao = dict(luoc_do.cong_vao(
        {"transcript": {"type": "json"}}, {"transcript": "document"}))
    assert vao["transcript"].type == "document"


def test_cong_khai_tay_DE_LEN_ca_measured_from():
    # Fix round 1: khai báo tường minh phải thắng suy luận trong MỌI trường
    # hợp, kể cả khi tham số là `measured_from` — spec §4.5. Trước sửa,
    # nhánh `measured_from` bỏ qua tham số này TRƯỚC khi hỏi `cong_khai`.
    vao = dict(luoc_do.cong_vao(
        {"duration_s": {"type": "number", "measured_from": "anh"}},
        {"duration_s": "text"}))
    assert vao["duration_s"].type == "text"


def test_cong_ra_tu_returns():
    ra = dict(luoc_do.cong_ra({"image_keys": "image[]", "prompt": "text"}, {}))
    assert ra["image_keys"].type == "image[]" and ra["image_keys"].multiple is False
    assert ra["prompt"].type == "text"


def test_moi_toolspec_that_dich_duoc_khong_nem():
    # 🔑 Đối chứng: một bảng từ vựng thiếu một dòng trông y hệt một bảng đủ
    #    cho tới khi gặp đúng tool đó.
    from platform_core import registry
    n = 0
    for item in registry.discover():
        if item.error:
            continue
        for t in item.manifest.tools:
            luoc_do.sang_json_schema(t.params_schema or {})
            luoc_do.cong_vao(t.params_schema or {}, (t.cong or {}).get("vao") or {})
            luoc_do.cong_ra(t.returns or {}, (t.cong or {}).get("ra") or {})
            n += 1
    # 🔴 HA 19 -> 18 (28/09): app `prompt_canh` bi xoa o `0c2aabab` (E5),
    #    mang theo ToolSpec `prompt_canh.run`. Ba phep LOAI TRU truoc khi
    #    ha — thieu chung thi ha banh coc la GIAU mot hoi quy that:
    #      1. so tut DUNG 1 (19 -> 18), khong phai 2+;
    #      2. `registry.discover()` bao 0 app nap loi => khong app nao
    #         rung vi sai kieu, tuc khong phai cai lo phep kiem nay canh;
    #      3. tool mat di dung la `prompt_canh.run` (doc tu
    #         `git show 0c2aabab^:apps/prompt_canh/manifest.py`).
    #    ⚠️ Hai tep nay bi BO SOT o luot ha 19->18 dau tien (chi sua
    #    `test_1756`/`test_1758`) vi ca hai phien deu dem tu THONG DIEP LOI
    #    cua mot tap con, khong dem KHANG DINH trong kho.
    assert n >= 18

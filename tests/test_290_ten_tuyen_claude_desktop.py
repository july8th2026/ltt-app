"""Tên tuyến `/messages` dành cho **Claude Desktop** phải lọt bộ lọc của ứng dụng.

🔴 VÌ SAO TỆP NÀY TỒN TẠI — MỘT BUỔI MẤT TRẮNG NGÀY 24/08.

   Claude Desktop ở chế độ `gateway` **lọc danh sách model trước khi hiện
   picker**. Tên không đạt bị bỏ khỏi mảng, picker rỗng, và hậu quả là **nút gửi
   vô hiệu — không log, không toast, không banner**. Cả phím Enter lẫn bấm chuột
   đều im lặng tuyệt đối.

⛔ Triệu chứng KHÔNG chỉ về phía nguyên nhân. Ta lần lượt nghi: khoá sai (đã thử
   thật: khoá trong registry gọi API trả **HTTP 200**), thiếu thư mục dự án (đã
   gắn: vẫn im), rồi mới đọc chính mã của bản cài mới ra.

⭐ LUẬT DƯỚI ĐÂY CHÉP TỪ BẢN CÀI THẬT — `Claude 1.34493.1.0`, tệp
   `app/resources/ion-dist/assets/v1/ce459c687-CEBp0mVy.js`. Nó không phải suy
   đoán từ tài liệu; tài liệu công khai **không** nói gì về bộ lọc này.

⚠️ Bộ lọc là của CLIENT, ta không sửa được. Nên thứ duy nhất ta kiểm soát là
   **tên tuyến**, và test này giữ cho nó không bị "dọn cho gọn" về `ltt_llm`.
"""
from __future__ import annotations

import importlib
import re

import pytest


# ── Luật lọc, chép nguyên từ bản cài ──────────────────────────────────────────

#: `Be` trong mã gốc: tên chứa bất kỳ chuỗi nào ở đây bị **cấm thẳng**.
#: ⚠️ `qwen` nằm trong danh sách này — nên ngay cả tên trung thực nhất
#:    (`qwen3-27b`) cũng **không** dùng được cho bề mặt này.
CAM = re.compile(
    r"ark-code|astron|command-r|deepseek|doubao|gemini|gemma|glm|gpt|grok|"
    r"hermes|hy3|kimi|lfm|\bling\b|llama|longcat|mimo|minimax|mistral|mixtral|"
    r"moonshot|nemotron|openai|phi-|qianfan|qwen|tc-code|\bunic\b|yi-|stepfun|"
    r"step-3|seed-|bytedance|hunyuan|granite|amazon\.nova|nova-|devstral|"
    r"ministral|ernie|codex|arcee|trinity|abab|phi\d|\bk2\.|\bm2\.|jamba|"
    r"arctic|solar|mercury|zamba|kat-coder|\bds-|dpsk")

#: `qe` trong mã gốc, rút gọn phần tên dòng: tên phải **chứa** một trong số này.
PHAI_CHUA = ("claude", "anthropic", "opus", "sonnet", "haiku")


def lot_bo_loc(ten: str) -> bool:
    """`Ke(t)` của ứng dụng, viết lại cho đọc được."""
    t = ten.lower()
    return not CAM.search(t) and any(s in t for s in PHAI_CHUA)


# ── Bộ lọc tự nó phải đúng ────────────────────────────────────────────────────

@pytest.mark.parametrize("ten,mong_doi", [
    ("ltt_llm", False),                 # ⛔ chính là ca đã làm chết nút gửi
    ("qwen3-27b", False),               # ⛔ tên trung thực cũng bị CẤM
    ("ltt-llm-claude-compat", True),    # ✅ tên ta chọn
    ("claude-sonnet-4-5", True),        # ✅ nhưng là tên sản phẩm hãng khác
])
def test_bo_loc_chep_lai_dung_hanh_vi(ten, mong_doi):
    """Chốt chính bản chép của ta, để nó không lệch khỏi bản gốc một cách âm thầm."""
    assert lot_bo_loc(ten) is mong_doi


# ── Tên tuyến của ta ──────────────────────────────────────────────────────────

@pytest.fixture()
def st():
    return importlib.import_module("server.api.streaming")


def test_moi_ten_tuyen_deu_lot_bo_loc(st):
    xau = [t for t in st.TUYEN_TUONG_THICH if not lot_bo_loc(t)]
    assert not xau, (
        f"ten tuyen {xau} KHONG lot bo loc cua Claude Desktop -> picker rong -> "
        f"nut gui vo hieu ma khong bao loi gi")


def test_ten_tuyen_tro_ve_alias_that(st):
    for tuyen, alias in st.TUYEN_TUONG_THICH.items():
        assert st._giai_ten_model(tuyen) == alias


def test_ten_khac_giu_nguyen_de_loi_o_cho_cu(st):
    """Bộ giải tên **không** được nuốt tên sai — lỗi phải nổ ở chốt kiểm cũ."""
    assert st._giai_ten_model("khong-co-that") == "khong-co-that"
    assert st._giai_ten_model("") == ""


def test_alias_dich_ra_phai_la_alias_that_cua_app(st):
    from apps.ltt_llm import features
    for alias in st.TUYEN_TUONG_THICH.values():
        assert alias in features.ALIAS_SANG_ID


def test_ten_tuyen_KHONG_duoc_vao_tu_vung_san_pham(st):
    """Ranh giới: `ALIAS_SANG_ID` là **sản phẩm**, `TUYEN_TUONG_THICH` là **giao thức**.

    Trộn hai thứ thì tên tuyến sẽ rò ra `/api/v1/tools`, bảng giá và tài liệu —
    tức một chi tiết của một client trở thành thứ khách mua.
    """
    from apps.ltt_llm import features
    chung = set(st.TUYEN_TUONG_THICH) & set(features.ALIAS_SANG_ID)
    assert not chung, f"ten tuyen bi lan vao tu vung san pham: {chung}"


def test_khong_muon_ten_san_pham_cua_hang_khac(st):
    """Ta lọt bộ lọc **mà không** khai mình là một model Anthropic có thật.

    Luật chỉ đòi tên *chứa* chuỗi `claude`; nó không đòi một model có thật. Đặt
    `claude-sonnet-4-5` cũng chạy — nhưng khi đó picker nói với khách rằng họ
    đang dùng Claude, trong khi phía sau là model nhà. Đó là một lựa chọn khác
    hẳn, và nếu ai đó đổi sang thì phải là một quyết định có ghi lại.
    """
    for t in st.TUYEN_TUONG_THICH:
        assert t.startswith("ltt-"), (
            f'"{t}" khong con mang nhan LTT - kiem lai xem ta co dang muon ten '
            f"san pham cua hang khac khong")


# ── Công cụ cắm phải khai đúng cái tên đó ─────────────────────────────────────

def test_cong_cu_cam_khai_dung_ten_tuyen(st):
    """Hai nơi cùng nói một cái tên: lệch nhau là cắm xong mà vẫn không chạy."""
    import pathlib
    import sys
    goc = pathlib.Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(goc / "tools"))
    try:
        cam_cli = importlib.import_module("cam_cli")
    finally:
        sys.path.remove(str(goc / "tools"))
    assert cam_cli.MODEL_DESKTOP in st.TUYEN_TUONG_THICH
    assert cam_cli.MODEL_DESKTOP != cam_cli.MODEL, (
        "Claude Desktop KHONG dung chung ten voi cac be mat khac - dung gop lai")

"""
test_806 — cờ `LTT_CHATLTT_V3_TOOLS` và chỗ nối vào `luot.py`. (H44 P03)

Hai mệnh đề, và mệnh đề thứ hai mới là mệnh đề đắt:

  1. Cờ **mặc định TẮT**, và hai cờ **độc lập** với nhau.
  2. Cờ tắt ⇒ `params` gửi lên **giống hệt V1**, không thừa một khoá.

⛔ Mệnh đề 2 là điều kiện của đường lùi (`02_ADR_ORCHESTRATION.md` §7). Nếu cờ
   tắt mà `params` vẫn khác V1 dù chỉ một khoá, thì "tắt cờ để lùi" là một câu
   trong tài liệu chứ không phải một cơ chế.
"""
from __future__ import annotations

import pytest

from apps.chatltt.services import co_v3


@pytest.fixture(autouse=True)
def _sach_co(monkeypatch):
    monkeypatch.delenv(co_v3.CO_TOOLS, raising=False)
    monkeypatch.delenv(co_v3.CO_TOOL_CO_PHI, raising=False)


# ── Cờ ─────────────────────────────────────────────────────────────────────

def test_mac_dinh_TAT_ca_hai():
    assert co_v3.tool_bat() is False
    assert co_v3.tool_co_phi_bat() is False


@pytest.mark.parametrize("gt", ["1", "true", "TRUE", "on", " On "])
def test_cac_cach_viet_duoc_coi_la_bat(monkeypatch, gt):
    monkeypatch.setenv(co_v3.CO_TOOLS, gt)
    assert co_v3.tool_bat() is True


@pytest.mark.parametrize("gt", ["0", "", "yes", "y", "bat", "2", "false"])
def test_moi_thu_khac_la_TAT(monkeypatch, gt):
    """⛔ Fail-closed. Một cờ nhận nhiều cách viết là một cờ mà người ta **tưởng**
    đã bật trong khi chưa — và với V3 thì "tưởng đã bật" nghĩa là tưởng model
    đang dùng tool trong khi nó không."""
    monkeypatch.setenv(co_v3.CO_TOOLS, gt)
    assert co_v3.tool_bat() is False


def test_hai_co_DOC_LAP(monkeypatch):
    """🔴 Bật vòng lặp tool là một mức rủi ro; để model **tự tiêu tiền của
    khách** là mức khác hẳn. Gộp hai cờ là để một lần bật vô tình mở cả hai."""
    monkeypatch.setenv(co_v3.CO_TOOLS, "1")
    assert co_v3.tool_bat() is True
    assert co_v3.tool_co_phi_bat() is False, "co thu hai KHONG duoc keo theo"


def test_doc_MOI_LAN_khong_nho(monkeypatch):
    """Đọc lúc import thì tắt cờ phải khởi động lại dịch vụ — và lúc cần tắt
    gấp là đúng lúc không ai muốn khởi động lại."""
    assert co_v3.tool_bat() is False
    monkeypatch.setenv(co_v3.CO_TOOLS, "1")
    assert co_v3.tool_bat() is True, "doi bien moi truong phai an NGAY"
    monkeypatch.delenv(co_v3.CO_TOOLS)
    assert co_v3.tool_bat() is False


# ── Chỗ nối trong `luot.py` — đọc mã, không cần CSDL ───────────────────────

def _nguon_chay() -> str:
    import inspect

    from apps.chatltt.services import luot
    return inspect.getsource(luot.chay)


def test_luot_dinh_tools_CHI_KHI_co_bat():
    src = _nguon_chay()
    assert "co_v3.tool_bat()" in src, "phai hoi co truoc khi dinh tools"
    assert 'params["tools"]' in src


def test_luot_gui_parallel_tool_calls():
    """[U] `docs/function-calling.md:24` — llama.cpp TẮT gọi song song mặc định.
    Không gửi cờ thì P01 đo 18/18 ra hai lời gọi cũng không bao giờ xảy ra thật."""
    assert 'params["parallel_tool_calls"]' in _nguon_chay()


def test_KHONG_dinh_khoa_tools_khi_khoi_RONG():
    """🔴 `tools: []` ≠ không gửi khoá.

    Có khoá `tools` là **bật cưỡng chế sinh** bằng văn phạm GBNF
    (`01_M1_NATIVE_HAY_GENERIC.md` §5b). Một lượt trò chuyện thường không nên
    đi qua văn phạm chỉ vì cờ đang bật mà chưa tool nào được mời.
    """
    src = _nguon_chay()
    i = src.index("co_v3.tool_bat()")
    khuc = src[i:i + 600]
    assert "if khoi_tools:" in khuc, "phai kiem RONG truoc khi dinh khoa"


def test_co_TAT_thi_params_GIONG_HET_V1():
    """⛔ Điều kiện của đường lùi. Cờ tắt mà `params` vẫn khác V1 dù một khoá
    thì "tắt cờ để lùi" là một câu trong tài liệu, không phải cơ chế."""
    src = _nguon_chay()
    # Ba khoa V1 duoc dung VO DIEU KIEN; hai khoa V3 nam TRONG nhanh cua co.
    i_co = src.index("if co_v3.tool_bat():")
    truoc = src[:i_co]
    assert '"model"' in truoc and '"messages"' in truoc
    assert '"tools"' not in truoc, "khoa tools KHONG duoc dinh ngoai nhanh co"
    assert '"parallel_tool_calls"' not in truoc

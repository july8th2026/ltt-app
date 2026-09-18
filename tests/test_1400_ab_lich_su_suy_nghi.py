"""test_1400 — bộ chấm A/B lịch sử suy nghĩ LTT-3.5 (P3 T1c, R-17). Không gọi máy B."""
from tools import ab_lich_su_suy_nghi as A


def test_cham_tool_lien_tuc():
    luot = [{"tool_calls": [{"name": "read_file", "arguments": {"path": "a.py"}}]},
            {"tool_calls": [{"name": "edit_file", "arguments": {"path": "a.py", "old": "x", "new": "y"}}]},
            {"tool_calls": [{"name": "edit_file", "arguments": {"path": "b.py"}}]}]
    ky_vong = [("read_file", {"path": "a.py"}), ("edit_file", {"path": "a.py"}), ("run_tests", {})]
    assert A.cham_tool(luot, ky_vong) == (2, 3)


def test_cham_tool_dut_giua_chung_tinh_thieu():
    assert A.cham_tool([{"tool_calls": []}], [("read_file", {}), ("run_tests", {})]) == (0, 2)


def test_cham_chat_luong_so_khop_dap_an():
    assert A.cham_dap_an("Kết quả là 42.", "42") is True
    assert A.cham_dap_an("", "42") is False
    assert A.cham_dap_an("1420", "42") is False


def test_kich_ban_tat_dinh():
    assert A._kich_ban(3) == A._kich_ban(3)
    assert A._kich_ban(3)["ky_vong"][0] == ("read_file", {"path": "src/mod_3.py"})


def test_wilson_bao_quanh_ti_le():
    lo, hi = A.wilson(30, 36)
    assert lo < 30 / 36 < hi and 0 <= lo and hi <= 1


def _kq(cl, tl, ctx):
    return {"chat_luong_dung": cl, "tong": 36, "tool_lien_tuc_dung": tl, "tool_tong": 90, "token_ctx_p50": ctx}


def test_phan_quyet_luat_da_khoa():
    assert A.phan_quyet(_kq(30, 80, 5000), _kq(29, 79, 4000))["thang"] == "B"
    # đối chứng: ctx không giảm ⇒ giữ A dù chất lượng ngang
    assert A.phan_quyet(_kq(30, 80, 5000), _kq(30, 80, 5000))["thang"] == "A"
    # chất lượng tụt quá khoảng tin cậy ⇒ giữ A
    assert A.phan_quyet(_kq(30, 80, 5000), _kq(15, 80, 3000))["thang"] == "A"

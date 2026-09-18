"""test_1510 — đọc id phiên client từ header, KHÔNG lưu định danh máy. (T4 P1, R-06/R-07)

Thiết kế: `docs/ltt_llm_dual/artifacts/THIET_KE_R06_R07_ID_PHIEN.md` §1, §2.2, §6.1.

Bộ header dưới đây là bộ **đo thật** 18/09/2026 (máy chủ bắt header cục bộ), không
phải bộ tự nghĩ ra: Claude Code 2.1.275 và Codex CLI 0.145.0 (`codex_exec`). Giá trị
UUID được thay bằng chuỗi cùng hình dạng — hình dạng là thứ bộ đọc cần.

Đối chứng (tiêm lỗi, đã chạy tay khi viết): bỏ bước lọc ký tự ⇒ các ca chèn header
ĐỎ; đảo thứ tự nguồn `phien` ⇒ ca Claude Code/Codex ĐỎ; cho `doc` trả rỗng ⇒ mọi
ca có header ĐỎ (ca "không header" là đối chứng ngược).
"""
from __future__ import annotations

import json

import pytest

from server.api import phien_khach

PHIEN_CC = "829c76f3-5d2a-4b1e-9c3f-38eea5feef82"
AGENT_CC = "a1b2c3d4e5f6a7b8"
PHIEN_CODEX = "01a0b543-7f3e-7c21-9d44-e2a0ef3726b5"
THREAD_CON = "01a0b544-0000-7c21-9d44-000000000abc"
TURN = "019a0c55-1234-7abc-8def-0123456789ab"
INSTALL = "inst-9f8e7d6c5b4a39281706f5e4d3c2b1a0"
DEVICE = "d" * 64


def _claude_code(**them) -> dict:
    """Header Claude Code 2.1.275 gửi tới `ANTHROPIC_BASE_URL` bên thứ ba (đo)."""
    h = {
        "X-Claude-Code-Session-Id": PHIEN_CC,
        "User-Agent": "claude-cli/2.1.275 (external, cli)",
        "X-Stainless-Retry-Count": "0",
        "X-Stainless-Os": "Windows",
        "x-app": "cli",
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    h.update(them)
    return h


def _turn_metadata(**them) -> str:
    d = {
        "installation_id": INSTALL,
        "request_kind": "turn",
        "sandbox": "workspace-write",
        "session_id": PHIEN_CODEX,
        "thread_id": PHIEN_CODEX,
        "thread_source": "user",
        "turn_id": TURN,
        "turn_started_at_unix_ms": 1789000000000,
        "window_id": PHIEN_CODEX + ":0",
        "workspaces": [{"remote": "git@github.com:bi-mat/kho-rieng.git",
                        "commit": "deadbeefcafe"}],
    }
    d.update(them)
    return json.dumps(d)


def _codex(**them) -> dict:
    """Header Codex CLI 0.145.0 (`codex_exec`) gửi tới `base_url` bên thứ ba (đo)."""
    h = {
        "session-id": PHIEN_CODEX,
        "thread-id": PHIEN_CODEX,
        "x-client-request-id": PHIEN_CODEX,
        "x-codex-window-id": PHIEN_CODEX + ":0",
        "x-codex-turn-metadata": _turn_metadata(),
        "x-codex-installation-id": INSTALL,
        "originator": "codex_exec",
        "User-Agent": ("codex_exec/0.145.0 (Windows 10.0.19045; x86_64) "
                       "WindowsTerminal"),
    }
    h.update(them)
    return h


# ── 1-3. Bộ header đo thật ──────────────────────────────────────────────────

def test_claude_code_luong_chinh():
    p = phien_khach.doc(_claude_code())
    assert p.phien == PHIEN_CC
    assert p.nhanh == "", "luong chinh Claude Code khong co agent id"
    assert p.luot == ""
    assert p.ung_dung == "claude-cli/2.1.275", "chi token dau cua User-Agent"


def test_claude_code_sub_agent_la_nhanh():
    p = phien_khach.doc(_claude_code(**{
        "x-claude-code-agent-id": AGENT_CC,
        "x-claude-code-parent-agent-id": "cha-0001"}))
    assert p.phien == PHIEN_CC
    assert p.nhanh == AGENT_CC


def test_codex_phien_nhanh_luot_ung_dung():
    p = phien_khach.doc(_codex(**{"thread-id": THREAD_CON}))
    assert p.phien == PHIEN_CODEX
    assert p.nhanh == THREAD_CON
    assert p.luot == TURN, "chi khoa turn_id cua x-codex-turn-metadata"
    assert p.ung_dung == "codex_exec/0.145.0"


def test_header_khong_phan_biet_hoa_thuong():
    """HTTP/2 hạ chữ thường mọi tên header; Starlette cũng vậy."""
    h = {k.lower(): v for k, v in _claude_code().items()}
    assert phien_khach.doc(h).phien == PHIEN_CC
    h = {k.upper(): v for k, v in _codex().items()}
    assert phien_khach.doc(h).phien == PHIEN_CODEX


def test_doc_duoc_Headers_cua_starlette():
    """Đầu vào thật ở middleware là `request.headers`, không phải dict."""
    from starlette.datastructures import Headers

    raw = [(k.lower().encode("latin-1"), v.encode("latin-1"))
           for k, v in _codex().items()]
    p = phien_khach.doc(Headers(raw=raw))
    assert (p.phien, p.nhanh, p.luot) == (PHIEN_CODEX, PHIEN_CODEX, TURN)


# ── 4. Codex cũ: header gạch dưới ───────────────────────────────────────────

def test_codex_cu_session_id_conversation_id_gach_duoi():
    p = phien_khach.doc({"session_id": PHIEN_CODEX,
                         "conversation_id": THREAD_CON,
                         "originator": "codex_cli_rs"})
    assert p.phien == PHIEN_CODEX
    assert p.nhanh == THREAD_CON
    assert p.ung_dung == "codex_cli_rs", "khong co User-Agent => originator"


def test_thu_tu_nguon_claude_code_truoc_codex():
    """Bảng thứ tự nguồn là DỮ LIỆU một chỗ; header Claude Code thắng."""
    h = _claude_code(**{"session-id": "khac", "session_id": "khac-nua"})
    assert phien_khach.doc(h).phien == PHIEN_CC
    h = {"session-id": "moi", "session_id": "cu"}
    assert phien_khach.doc(h).phien == "moi", "dang gach ngang (moi) truoc gach duoi"


def test_x_ltt_session_id_la_nguon_cuoi():
    """Chừa chỗ cho LTTCODE (hoãn cùng harness T2) — chỉ khi ba nguồn kia vắng."""
    assert phien_khach.doc({"X-LTT-Session-Id": "ltt-1"}).phien == "ltt-1"
    assert phien_khach.doc({"X-LTT-Session-Id": "ltt-1",
                            "session-id": "cx"}).phien == "cx"


# ── 5. ⛔ Không lưu định danh máy ────────────────────────────────────────────

@pytest.mark.parametrize("h", [_codex(), _claude_code()], ids=["codex", "claude"])
def test_KHONG_mang_dinh_danh_may(h):
    """installation_id / device_id / remote git ổn định theo MÁY ⇒ nối được mọi
    phiên của một người qua thời gian. Kiểm bằng `repr` của CẢ đối tượng, không
    theo từng trường — một trường thứ năm thêm sau cũng bị bắt."""
    h = dict(h)
    h["x-claude-code-metadata"] = json.dumps({"device_id": DEVICE})
    r = repr(phien_khach.doc(h))
    for cam in (INSTALL, DEVICE, "github.com", "deadbeefcafe", "Windows",
                "WindowsTerminal", "workspace-write", "external"):
        assert cam not in r, f"lot {cam!r} vao ket qua: {r}"


def test_chi_bon_truong():
    """Khoá tập trường theo TẬP HỢP: thêm một trường mới là phải sửa ở đây."""
    import dataclasses

    assert {f.name for f in dataclasses.fields(phien_khach.PhienKhach)} == {
        "phien", "nhanh", "luot", "ung_dung"}


# ── 6. Đầu vào thù địch ─────────────────────────────────────────────────────

def test_chen_header_bi_loc():
    p = phien_khach.doc({"session-id": "a\r\nX-Evil: 1",
                         "thread-id": "b\nSet-Cookie: x=1"})
    # Giữ [A-Za-z0-9._:-] (cùng luật `llm_gateway/api.py:_id_sach`, nhưng ASCII).
    assert p.phien == "aX-Evil:1"
    assert p.nhanh == "bSet-Cookie:x1"
    for s in (p.phien, p.nhanh):
        assert "\r" not in s and "\n" not in s and " " not in s


def test_ky_tu_khong_ascii_bi_loc():
    """`str.isalnum()` nhận chữ có dấu — cột đếm ký tự, kho khác đếm byte."""
    assert phien_khach.doc({"session-id": "phiên-1"}).phien == "phin-1"


def test_dai_500_cat_64():
    p = phien_khach.doc({"session-id": "x" * 500, "thread-id": "y" * 500})
    assert p.phien == "x" * 64
    assert p.nhanh == "y" * 64


@pytest.mark.parametrize("meta", [
    "{hong json",
    json.dumps(["turn_id", TURN]),
    json.dumps({"khong_co": "turn"}),
    json.dumps({"turn_id": {"long": "nhau"}}),
    json.dumps({"turn_id": None}),
    "",
], ids=["hong", "mang", "thieu", "object", "null", "rong"])
def test_turn_metadata_xau_thi_luot_rong_khong_nem(meta):
    p = phien_khach.doc(_codex(**{"x-codex-turn-metadata": meta}))
    assert p.luot == ""
    assert p.phien == PHIEN_CODEX, "metadata hong khong duoc lam mat cac truong khac"


def test_turn_metadata_1_MiB_khong_parse():
    """Parse có trần 8 KiB: header 1 MiB không được tốn CPU parse JSON."""
    to = _turn_metadata(dem="z" * (1 << 20))
    assert len(to) > 8 * 1024
    assert phien_khach.doc(_codex(**{"x-codex-turn-metadata": to})).luot == ""


def test_turn_metadata_nho_hon_tran_van_doc():
    """Đối chứng cho ca trên: dưới trần 8 KiB thì vẫn đọc (trần không quá chặt)."""
    vua = _turn_metadata(dem="z" * 6000)
    assert len(vua) < 8 * 1024
    assert phien_khach.doc(_codex(**{"x-codex-turn-metadata": vua})).luot == TURN


def test_turn_id_la_so_van_doc():
    assert phien_khach.doc(_codex(**{
        "x-codex-turn-metadata": json.dumps({"turn_id": 42})})).luot == "42"


@pytest.mark.parametrize("ua,mong", [
    ("claude-cli/2.1.275 (external, cli)", "claude-cli/2.1.275"),
    ("codex_exec/0.145.0 (Windows 10.0.19045; x86_64) WindowsTerminal",
     "codex_exec/0.145.0"),
    ("codex_vscode/0.145.0-alpha.1+abc", "codex_vscode/0.145.0-alpha.1+abc"),
    ("python-httpx/0.28.1", "python-httpx/0.28.1"),
])
def test_ung_dung_la_token_dau_user_agent(ua, mong):
    assert phien_khach.doc({"User-Agent": ua}).ung_dung == mong


@pytest.mark.parametrize("ua", [
    "(no product)", "khong-co-phien-ban", "curl/", "ten/abc", "\r\nX: 1/2",
])
def test_user_agent_khong_khop_thi_dung_originator(ua):
    p = phien_khach.doc({"User-Agent": ua, "originator": "codex_exec"})
    assert p.ung_dung == "codex_exec"
    assert phien_khach.doc({"User-Agent": ua}).ung_dung == ""


def test_ung_dung_cat_48():
    p = phien_khach.doc({"User-Agent": "a" * 100 + "/1.0"})
    assert len(p.ung_dung) <= 48
    p = phien_khach.doc({"originator": "o" * 100})
    assert p.ung_dung == "o" * 48


# ── 7. Không header nào ─────────────────────────────────────────────────────

def test_khong_header_nao_thi_bon_chuoi_rong():
    """Đối chứng ngược: bộ đọc không được bịa ra phiên."""
    p = phien_khach.doc({})
    assert (p.phien, p.nhanh, p.luot, p.ung_dung) == ("", "", "", "")
    assert phien_khach.doc(None) == p


def test_header_rong_bo_qua_sang_nguon_ke():
    """Một nguồn có mặt nhưng lọc xong RỖNG thì không được chặn nguồn kế tiếp."""
    p = phien_khach.doc({"X-Claude-Code-Session-Id": "\r\n ",
                         "session-id": PHIEN_CODEX})
    assert p.phien == PHIEN_CODEX

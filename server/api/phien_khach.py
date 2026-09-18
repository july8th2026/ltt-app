"""Đọc id phiên / nhánh / lượt / ứng dụng của CLIENT từ header request. (T4 P1)

Thiết kế: `docs/ltt_llm_dual/artifacts/THIET_KE_R06_R07_ID_PHIEN.md` §1, §2.2.

Câu hỏi nó giúp trả lời: *"lượt X thuộc phiên Claude Code / Codex nào của khách
nào?"*. Kết quả đi vào bốn cột của `public_api_requests` (sổ 30 ngày, luôn gắn
`user_id`), và **dừng ở máy A** — không header nào ở đây được chuyển xuống máy B
(`X-Conversation-Id` làm llama.cpp sinh tiếp sau khi khách ngắt:
`docs/ltt_llm_dual/05_COMMUNITY_EVIDENCE.md`).

Hàm thuần, không I/O: đầu vào là một ánh xạ header, đầu ra bốn chuỗi đã lọc.

⛔ KHÔNG ĐỌC, KHÔNG TRẢ định danh ổn định theo MÁY: `x-codex-installation-id`,
   `installation_id` / `workspaces` / `sandbox` trong `x-codex-turn-metadata`,
   `metadata.user_id` (`device_id`) của Claude Code, cả chuỗi `User-Agent`,
   `X-Stainless-*`. Id phiên là UUID client sinh MỖI phiên; id máy thì nối được
   mọi phiên của một người qua thời gian và qua tài khoản — đúng thứ
   `platform_core/public_api/request_log.py` cam kết không trở thành.
   `test_1510::test_KHONG_mang_dinh_danh_may` khoá bằng `repr` của cả kết quả.

⚠️ Header do khách tự đặt ⇒ tin được đúng bằng một chú thích của khách: chỉ dùng
   để tra sổ **của chính họ** (mọi truy vấn lọc theo `user_id`), không dùng cho
   quyết định nào (tiền, hàng chờ, quyền).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

#: Thứ tự nguồn — DỮ LIỆU một chỗ. Nguồn đầu tiên có giá trị (sau khi lọc) thắng.
#:
#: * `X-Claude-Code-Session-Id` — Claude Code ≥ 2.1 (đo 2.1.275), gửi cả khi
#:   `ANTHROPIC_BASE_URL` trỏ bên thứ ba.
#: * `session-id` / `thread-id` — Codex ≥ 0.14x (`codex-rs/codex-api/src/
#:   requests/headers.rs::build_session_headers`).
#: * `session_id` / `conversation_id` — Codex bản cũ (gạch dưới). Proxy kiểu
#:   nginx mặc định bỏ header có gạch dưới; Cloudflare Tunnel thì không.
#: * `X-LTT-Session-Id` — chừa cho LTTCODE (hoãn cùng harness T2).
NGUON_PHIEN: tuple[str, ...] = (
    "x-claude-code-session-id",
    "session-id",
    "session_id",
    "x-ltt-session-id",
)
#: Nhánh trong phiên: sub-agent của Claude Code (luồng chính thì vắng), thread
#: của Codex (thread gốc = `session-id`, sub-agent khác).
NGUON_NHANH: tuple[str, ...] = (
    "x-claude-code-agent-id",
    "thread-id",
    "conversation_id",
)
#: Codex: một *turn* = nhiều request (vòng tool). Chỉ khoá `turn_id` được đọc.
HEADER_TURN_METADATA = "x-codex-turn-metadata"
KHOA_LUOT = "turn_id"
HEADER_UNG_DUNG = "user-agent"
HEADER_ORIGINATOR = "originator"

#: Trần độ dài — bằng độ dài cột (`platform_core/public_api/tables.py`).
TRAN_ID = 64
TRAN_UNG_DUNG = 48
#: JSON dài hơn thế này thì không parse (đo: 365 byte; có `workspaces` vài trăm
#: byte nữa). Một header 1 MiB không được mua CPU parse JSON trên mỗi request.
TRAN_TURN_METADATA = 8 * 1024

_KY_TU_ID = frozenset("abcdefghijklmnopqrstuvwxyz"
                      "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._:-")
#: Token đầu `User-Agent`: `claude-cli/2.1.275`, `codex_exec/0.145.0`. Phải có
#: phiên bản bắt đầu bằng chữ số — "tên/abc" không phải một token sản phẩm.
_UA = re.compile(r"[A-Za-z0-9_.-]+/[0-9][0-9A-Za-z.+-]*")


@dataclass(frozen=True)
class PhienKhach:
    phien: str = ""
    nhanh: str = ""
    luot: str = ""
    ung_dung: str = ""


def _sach(gia_tri, tran: int = TRAN_ID) -> str:
    """Chỉ giữ `[A-Za-z0-9._:-]` (ASCII), cắt `tran` ký tự.

    ⛔ LỌC CHỨ KHÔNG CHÉP THÔ: chuỗi do khách đặt, đi vào dòng log văn bản và
       một cột CSDL — `\\r\\n` là chèn dòng log. ASCII chứ không `isalnum()`:
       `"phiên"` là 5 ký tự nhưng 6 byte.
    """
    return "".join(c for c in str(gia_tri or "") if c in _KY_TU_ID)[:tran]


def _thuong(headers) -> dict[str, str]:
    """Ánh xạ tên-thường → giá trị ĐẦU TIÊN. Nhận dict lẫn `starlette.Headers`."""
    if headers is None:
        return {}
    ra: dict[str, str] = {}
    try:
        cap = headers.items()
    except AttributeError:
        return {}
    for k, v in cap:
        ra.setdefault(str(k).lower(), str(v) if v is not None else "")
    return ra


def _dau_tien(h: dict[str, str], nguon: tuple[str, ...]) -> str:
    for ten in nguon:
        gia_tri = _sach(h.get(ten, ""))
        if gia_tri:
            return gia_tri
    return ""


def _luot(raw: str) -> str:
    """`turn_id` của `x-codex-turn-metadata`; mọi thứ khác trong JSON bị bỏ."""
    if not raw or len(raw) > TRAN_TURN_METADATA:
        return ""
    try:
        d = json.loads(raw)
    except (ValueError, RecursionError):
        return ""
    if not isinstance(d, dict):
        return ""
    gia_tri = d.get(KHOA_LUOT)
    if isinstance(gia_tri, bool) or not isinstance(gia_tri, (str, int)):
        return ""
    return _sach(gia_tri)


def _ung_dung(h: dict[str, str]) -> str:
    """Tên/phiên bản client — KHÔNG phải cả `User-Agent` (lộ OS, terminal)."""
    khop = _UA.match(h.get(HEADER_UNG_DUNG, "").strip())
    if khop:
        return khop.group(0)[:TRAN_UNG_DUNG]
    return _sach(h.get(HEADER_ORIGINATOR, ""), TRAN_UNG_DUNG)


def doc(headers) -> PhienKhach:
    """Bốn trường phiên client từ header. Không bao giờ ném; thiếu ⇒ chuỗi rỗng."""
    h = _thuong(headers)
    if not h:
        return PhienKhach()
    return PhienKhach(
        phien=_dau_tien(h, NGUON_PHIEN),
        nhanh=_dau_tien(h, NGUON_NHANH),
        luot=_luot(h.get(HEADER_TURN_METADATA, "")),
        ung_dung=_ung_dung(h),
    )

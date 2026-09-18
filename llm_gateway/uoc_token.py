r"""uoc_token.py — ước token vào là CẬN TRÊN, không cần engine (R-2 Phương án C, Task 7).

⛔ HAI BẢN GIỐNG HỆT TỪNG BYTE: ``platform_core/llm/uoc_token.py`` (máy A) và
   ``llm_gateway/uoc_token.py`` (máy B). Máy B không có cây ``platform_core`` (Q102),
   máy A không import gói của máy B — nên chép, và ``test_1470`` so nguồn. Hai bản lệch
   là A giữ chỗ khác số B đếm, và "A nhận ⇒ B nhận" (A ⊆ B) gãy im lặng.

Hàm công khai:

* ``gom_van_ban(x, van_ban, anh)`` — gom MỌI chuỗi của một khối nội dung/tin nhắn (cả
  ``role``, ``tool_calls``, ``tool_use.input``...), tách URL ảnh ra ``anh``.
* ``uoc_chuoi(s)``   — cận trên số token BPE của MỘT chuỗi (chưa tính khuôn chat).
* ``khuon(so_tin, so_tool)`` — cận trên token khuôn chat mà template render thêm.
* ``uoc_than(than)`` — ước cả một body (Chat/Messages/Responses) = văn bản + khuôn.

CHỨNG MINH CẬN TRÊN
===================

(1) Cận cứng, không phụ thuộc số đo. Tokenizer của cả hai model (Qwen3.5-9B và
    Qwen3.8-27B) là BPE **byte-level**: mỗi token phủ ≥ 1 byte UTF-8, và các phép
    gộp không vượt ranh giới **pre-token** (regex tách chữ/số/ký hiệu/khoảng trắng
    trước khi BPE chạy). Nên với mọi đoạn ``c``: ``token(c) ≤ byte(c)``, và token của
    cả chuỗi = tổng token từng pre-token. Mỗi chữ số là MỘT pre-token riêng
    (``\p{N}`` đơn) ⇒ đúng 1 token/chữ số — hệ số 1 ở dưới là chính xác, không đo.

(2) Siết theo lớp — mỗi hệ số ≤ cận byte (1) của đoạn nó áp vào, và không dưới số
    đo lớn nhất của lớp ấy. Chuỗi được chia thành đoạn cùng lớp (xấp xỉ pre-token):
    chữ số ASCII · khoảng trắng · chữ · ký hiệu. Đoạn chữ lại tách ở ranh giới
    hoa/thường (``getElementById`` → get·Element·By·Id) — mỗi "từ con" ≥ 1 token::

        lớp                               hệ số ở đây              căn cứ
        chữ số ASCII                      1 / chữ số               = cận byte; đúng bằng thật (numbers_csv)
        ký hiệu ASCII (dãy n ký tự)       ⌈n/2⌉                    1 ký hiệu = cận byte; cặp ``":`` ``{"``
                                                                   là một token (json_minified 1,09×)
        từ con ASCII CÓ nguyên âm         ⌈n/5⌉                    từ ≤ 9 chữ = 1 token (en_prose)
        từ con ASCII KHÔNG nguyên âm      n (1 / chữ)              = cận byte (hex, base64: chuỗi ngẫu nhiên)
        chữ Latin có dấu (tiếng Việt…)    0,5 / chữ + phần ASCII   vi_markdown ≈ 1,2 token / âm tiết
        chữ hệ khác (Trung, Nhật…)        0,40 / byte              đo 0,31 / byte (cjk_zh) × 1,28
        ký hiệu không ASCII (emoji…)      0,80 / byte              đo 0,64 / byte (emoji) × 1,25
        một dấu cách trước chữ/ký hiệu    0                        dính vào pre-token sau (``" ?\p{L}+"``)
        dãy trắng khác (thụt lề, \n)       ⌈n/2⌉                    ≤ cận byte

    Cộng các đoạn (số thực) rồi làm tròn LÊN một lần. Mọi hệ số ≤ 1 token/byte ⇒ ước
    của một chuỗi không bao giờ vượt cận (1) (test_1470 kiểm ``uoc_chuoi(s) ≤ byte(s)``).

    Kết quả trên ngữ liệu (ước kể cả khuôn ÷ thật): numbers_csv 1,03 · hex 1,06 ·
    tool_calls_history 1,07 · base64 1,08 · json_minified 1,09 · code_py 1,20 ·
    stacktrace 1,21 · tools_60 1,27 · emoji 1,30 · ja_mixed 1,30 · vi_markdown 1,36 ·
    cjk_zh 1,37 · en_prose 1,37.

(3) Khuôn chat (``khuon``): token đặc biệt ``<|im_start|>``, vai, vỏ tool_call, lời
    mở đầu hệ thống — template render thêm, không nằm trong chuỗi khách. Đo trên
    engine b10883 (17/09, cả hai model, ba giao thức, mọi nấc effort): cố định 52
    token, mỗi tin nhắn 7 token ⇒ hằng = đo × ≥ 1,25: **256 + 16/tin**.

    Mỗi tool: số đo 17/09 là **45 BYTE** template render thêm so với JSON gọn (vỏ
    ``{"type": "function", "function": …}``, khoảng trắng sau ``:``/``,``) — byte, không
    phải token. Hằng cũ 64/tool lấy byte làm token VÀ cộng chồng lên phần schema đã
    ước theo lớp ⇒ tools_60 ra 1,79×. Nay đổi byte sang token bằng CHÍNH hệ số lớp ở
    (2): vỏ ``'{"type": "function", "function": }\n'`` = 35 byte ⇒ ``uoc_chuoi`` = 13
    token ⇒ 45 byte ⇒ ⌈45 × 13/35⌉ = **17 token/tool**. Vẫn ≤ 45 (cận byte (1)).
    Đối chứng: bỏ hẳn phần này, tools_60 vẫn 1,09× — tức 17 là biên, không phải chỗ
    phép ước dựa vào.

    Kiểm: ``uoc_than(x) ≥ engine(x)`` với mọi mẫu (test_1470); văn xuôi Anh và
    Markdown tiếng Việt ≤ 1,5 × thật (không lãng phí suất).

⚠️ PHẠM VI. (1) và hệ số chữ số/ký hiệu ASCII là chứng minh. Các hệ số siết khác là
   số đo trên các lớp có trong ngữ liệu; một lớp MỚI chưa đo (vd. chuỗi chữ thường
   ngẫu nhiên dài) phải được thêm vào ngữ liệu và đo trước khi tin hệ số của nó.
   ``DEM_UOC`` (đặt chỗ) và nhánh đếm thật của máy B vẫn đứng sau làm lưới.
"""
from __future__ import annotations

import json
import math
import re

#: Khuôn chat — docstring (3): 256/16 = số đo × ≥ 1,25; 17/tool = 45 byte đổi theo hệ số lớp.
KHUON_CO_DINH = 256
KHUON_MOI_TIN = 16
KHUON_MOI_TOOL = 17

#: Siết theo lớp — docstring (2).
CHU_ASCII_MOI_TOKEN = 5
TOKEN_MOI_BYTE_CHU_KHAC = 0.40
TOKEN_MOI_CHU_LATIN_DAU = 0.5
CHU_KHONG_NGUYEN_AM_MOI_TOKEN = 1
TOKEN_MOI_BYTE_KY_HIEU_KHAC = 0.80
KHOANG_TRANG_MOI_TOKEN = 2
KY_HIEU_ASCII_MOI_TOKEN = 2

_ANH = ("image", "image_url", "input_image")


def gom_van_ban(x, van_ban: list, anh: list) -> None:
    """Gom mọi chuỗi trong ``x`` vào ``van_ban``; URL/base64 ảnh vào ``anh``.

    Đi CẢ tin nhắn chứ không chỉ ``content``: ``tool_calls`` (Chat), ``tool_use.input``
    (Messages), ``function_call.arguments`` (Responses) đều được template render vào
    prompt. Bỏ chúng là ước thiếu đúng ở phiên agent dài (đo: tool_calls_history).
    """
    if isinstance(x, str):
        van_ban.append(x)
        return
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        van_ban.append(str(x))
        return
    if isinstance(x, list):
        for p in x:
            gom_van_ban(p, van_ban, anh)
        return
    if not isinstance(x, dict):
        return
    loai = x.get("type")
    if loai == "image_url":                              # OpenAI Chat
        gt = x.get("image_url")
        anh.append(str(gt.get("url") if isinstance(gt, dict) else gt or ""))
        return
    if loai == "input_image":                            # OpenAI Responses
        anh.append(str(x.get("image_url") or ""))
        return
    if loai == "image":                                  # Anthropic Messages
        nguon = x.get("source") or {}
        if isinstance(nguon, dict):
            du_lieu = nguon.get("data")
            # Anthropic gửi base64 trần, không có tiền tố `data:`.
            anh.append("data:;base64," + str(du_lieu) if du_lieu
                       else str(nguon.get("url") or ""))
        return
    for gt in x.values():
        gom_van_ban(gt, van_ban, anh)


#: Chia chuỗi thành đoạn cùng lớp (xấp xỉ pre-token): chữ số ASCII · khoảng trắng ·
#: chữ (mọi hệ chữ) · ký hiệu (gồm ``_``, emoji, dấu kết hợp, chữ số không ASCII).
_DOAN = re.compile(r"(?P<so>[0-9]+)|(?P<trang>\s+)|(?P<chu>[^\W\d_]+)|(?P<kh>(?:[^\w\s]|_|(?![0-9])\d)+)")


_NGUYEN_AM = frozenset("aeiouyAEIOUY")


def _latin_mo_rong(c: str) -> bool:
    """Chữ Latin có dấu (tiếng Việt, Pháp, Đức...): Latin-1 bổ sung, Latin mở rộng A/B,
    Latin mở rộng bổ sung (U+1E00–U+1EFF — gần hết nguyên âm tiếng Việt)."""
    o = ord(c)
    return 0xC0 <= o <= 0x24F or 0x1E00 <= o <= 0x1EFF


def _tu_con(doan: str) -> list:
    """Tách một đoạn chữ ở ranh giới hoa/thường (``getElementById`` → get·Element·By·Id,
    ``HTTPServer`` → HTTP·Server) — cùng chỗ BPE thường tách."""
    ra, dau = [], 0
    for k in range(1, len(doan)):
        a, b = doan[k - 1], doan[k]
        nxt = doan[k + 1] if k + 1 < len(doan) else ""
        if (a.islower() and b.isupper()) or (a.isupper() and b.isupper() and nxt.islower()):
            ra.append(doan[dau:k])
            dau = k
    ra.append(doan[dau:])
    return ra


def _chu(doan: str) -> float:
    """Một đoạn chữ liền — docstring (2). Mỗi từ con ≥ 1 token."""
    if doan.isascii() and (doan.islower() or doan[1:].islower() or len(doan) == 1):
        # Đường nhanh (đa số văn bản): một từ con ASCII, không đổi hoa/thường bên trong.
        if _NGUYEN_AM.isdisjoint(doan):
            return float(math.ceil(len(doan) / CHU_KHONG_NGUYEN_AM_MOI_TOKEN))
        return float(math.ceil(len(doan) / CHU_ASCII_MOI_TOKEN))
    tong = 0.0
    for tu in _tu_con(doan):
        n_ascii = 0
        co_nguyen_am = False
        phan = 0.0
        for c in tu:
            if c.isascii():
                n_ascii += 1
                co_nguyen_am = co_nguyen_am or c in _NGUYEN_AM
            elif _latin_mo_rong(c):
                phan += TOKEN_MOI_CHU_LATIN_DAU
                co_nguyen_am = True
            else:
                phan += len(c.encode("utf-8")) * TOKEN_MOI_BYTE_CHU_KHAC
        if n_ascii:
            phan += (math.ceil(n_ascii / CHU_ASCII_MOI_TOKEN) if co_nguyen_am
                     else math.ceil(n_ascii / CHU_KHONG_NGUYEN_AM_MOI_TOKEN))
        tong += max(1.0, phan)
    return tong


def _ky_hieu(doan: str) -> float:
    ascii_ = sum(1 for c in doan if c.isascii())
    khac = sum(len(c.encode("utf-8")) for c in doan if not c.isascii())
    return math.ceil(ascii_ / KY_HIEU_ASCII_MOI_TOKEN) + khac * TOKEN_MOI_BYTE_KY_HIEU_KHAC


def uoc_chuoi(s: str) -> int:
    """Cận trên token BPE của MỘT chuỗi — docstring (1)(2). Không tính khuôn."""
    if not s:
        return 0
    tong = 0.0
    n = len(s)
    for m in _DOAN.finditer(s):
        lop, doan = m.lastgroup, m.group()
        if lop == "so":
            tong += len(doan)
        elif lop == "chu":
            tong += _chu(doan)
        elif lop == "kh":
            tong += _ky_hieu(doan)
        elif not (doan == " " and m.end() < n and not s[m.end()].isdigit()):
            # Một dấu cách đứng trước chữ/ký hiệu dính vào pre-token sau (0 token);
            # trước chữ số thì không (``\p{N}`` đứng riêng) — tính như dãy trắng.
            tong += math.ceil(len(doan) / KHOANG_TRANG_MOI_TOKEN)
    return math.ceil(tong)


def uoc_doan(doan) -> int:
    """Tổng ``uoc_chuoi`` của nhiều đoạn (cận trên cộng được vì pre-token không vượt
    ranh giới đoạn — mỗi đoạn là một chuỗi riêng trong template)."""
    return sum(uoc_chuoi(s) for s in doan if s)


def khuon(so_tin: int, so_tool: int) -> int:
    """Token khuôn chat — docstring (3). ``so_tin`` tính cả lời hệ thống."""
    return KHUON_CO_DINH + KHUON_MOI_TIN * max(0, so_tin) + KHUON_MOI_TOOL * max(0, so_tool)


def json_tool(tools) -> str:
    """Dạng chuỗi của khối tool dùng để ước — MỘT dạng cho cả hai máy."""
    return json.dumps(tools, ensure_ascii=False, separators=(",", ":"))


class KhoiTool(dict):
    """Phần tử bọc khối tool trong danh sách ước của máy A (``uoc_tin_nhan``):
    ``KhoiTool(content=json_tool(tools), so_tool=len(tools))``.

    ⛔ KIỂU RIÊNG, không phải một khoá JSON: tin nhắn của khách là ``dict`` thường, nên
       khách không giả được phần tử này để A bỏ qua một phần tin nhắn khi ước.
    """


def gom_than(than: dict, van_ban: list, anh: list) -> tuple:
    """Gom văn bản + ảnh của một body bất kỳ giao thức. Trả ``(so_tin, so_tool)``.

    ``so_tin`` = số tin nhắn/mục + 1 (lời hệ thống — template chèn cả khi khách không gửi).
    """
    gom_van_ban(than.get("system"), van_ban, anh)
    gom_van_ban(than.get("instructions"), van_ban, anh)
    so_tin = 1
    for khoa in ("messages", "input"):
        gt = than.get(khoa)
        if isinstance(gt, str):
            van_ban.append(gt)
            so_tin += 1
        elif isinstance(gt, list):
            gom_van_ban(gt, van_ban, anh)
            so_tin += len(gt)
    so_tool = 0
    for khoa in ("tools", "functions"):
        gt = than.get(khoa)
        if isinstance(gt, list) and gt:
            van_ban.append(json_tool(gt))
            so_tool += len(gt)
    return so_tin, so_tool


def uoc_than(than: dict) -> int:
    """Cận trên token vào (không gồm ảnh) của một body: văn bản + khuôn."""
    van_ban: list = []
    so_tin, so_tool = gom_than(than, van_ban, [])
    return uoc_doan(van_ban) + khuon(so_tin, so_tool)

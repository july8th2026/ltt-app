"""uoc_moi.py — ước số token phải PREFILL MỚI của một lượt. (multijob, TD-6)

⭐ VÌ SAO: "whale" (D-05) phải đo bằng token cần prefill MỚI, không bằng tổng ngữ
   cảnh. Một phiên Codex 150K mà mỗi lượt chỉ thêm 2K là một lượt NHẸ — llama.cpp
   dùng lại cache tiền tố (tải thật 20 ngày: 54 % token ngữ cảnh là cache trúng).
   Coi nó là whale là bắt mọi lượt agent nhường chat ngắn một cách oan.

⭐ CÁCH: chuỗi băm nối tiếp theo từng tin nhắn — `h_i = sha256(h_{i-1} + tin_i)`.
   Lượt tiếp của cùng hội thoại gửi lại toàn bộ lịch sử, nên tiền tố của nó khớp
   chuỗi băm của lượt trước. Phần sau tiền tố khớp dài nhất là phần "mới".
   O(n) theo số tin nhắn, không O(n²).

⛔ CHỈ ẢNH HƯỞNG THỨ TỰ (ai là whale), KHÔNG ảnh hưởng an toàn KV: sổ ngân sách
   luôn đặt TOÀN BỘ ngữ cảnh (phần cache trúng vẫn chiếm ô KV của chuỗi đó). Nhớ
   trong tiến trình (nhiều web worker ⇒ nhớ riêng) là chấp nhận được vì lẽ đó:
   sai thì một lượt bị coi là whale nhầm, không ai bị OOM hay thu sai tiền.
"""
from __future__ import annotations

import hashlib
import json
import threading
from collections import OrderedDict
from typing import Callable

#: Số tài khoản nhớ tối đa trong một tiến trình (LRU).
TOI_DA_TAI_KHOAN = 512
#: Số lượt gần nhất nhớ cho mỗi tài khoản (vài hội thoại song song của một người).
MOI_TAI_KHOAN = 8

_khoa = threading.Lock()
_nho: "OrderedDict[str, list[set[str]]]" = OrderedDict()


def _chuoi_bam(tin_nhan: list) -> list[str]:
    ra, h = [], b""
    for tin in tin_nhan:
        than = json.dumps(tin, ensure_ascii=False, sort_keys=True, default=str)
        h = hashlib.sha256(h + than.encode("utf-8")).digest()
        ra.append(h.hex())
    return ra


def uoc_token_moi(user_id: str, tin_nhan: list, uoc: Callable[[list], int]) -> int:
    """Ước token cần prefill MỚI của lượt này; ghi nhớ nó cho lượt sau.

    `uoc(list) -> int` là phép ước token của app (`executor.estimate_input`) —
    nền tảng không tự đếm token (không import `apps/`).
    """
    tin = list(tin_nhan or [])
    chuoi = _chuoi_bam(tin)
    with _khoa:
        cu = _nho.get(user_id, [])
    k = 0
    for i in range(len(chuoi), 0, -1):
        if any(chuoi[i - 1] in tap for tap in cu):
            k = i
            break
    moi = int(uoc(tin[k:])) if tin[k:] else 0
    with _khoa:
        ds = _nho.pop(user_id, [])
        ds.append(set(chuoi))
        _nho[user_id] = ds[-MOI_TAI_KHOAN:]
        while len(_nho) > TOI_DA_TAI_KHOAN:
            _nho.popitem(last=False)
    return moi


def quen_het() -> None:
    """Cho phép kiểm: xoá bộ nhớ trong tiến trình."""
    with _khoa:
        _nho.clear()

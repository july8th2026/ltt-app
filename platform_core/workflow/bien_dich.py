"""Biên dịch draft v3 (tài liệu soạn thảo) → đồ thị chuẩn `ltt.workflow/3`.

Spec §4.1: trang chỉ là tab bố cục — gộp MỌI trang; id duy nhất toàn tài liệu;
cạnh không nối khác trang. Plan 01a chỉ nhận node app; `core.*` ở plan 04.
"""
from __future__ import annotations

import re
from collections import deque
from typing import Any, Optional

# Gọi qua MÔ-ĐUN (không `from platform_core.workflow.cong_cu import tat_ca`)
# để test monkeypatch được `cong_cu.tat_ca` và thấy bản thay thế ở đây.
from platform_core.workflow import cong_cu as _nguon
from platform_core.workflow.cong_cu import CongCu
from platform_core.workflow.di_tru_m1 import _canh_v3

SCHEMA = "ltt.workflow/3"
_ID = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")
_CU = re.compile(r"^\$([A-Za-z0-9_\-]{1,64})\.([A-Za-z0-9_\-]{1,64})$")
_THAM_CHIEU = re.compile(
    r"^\{\{\s*nodes\.([A-Za-z0-9_\-]{1,64})\.output\.([A-Za-z0-9_\-]{1,64})\s*\}\}$")
_KIND = frozenset({"DATA", "CONTROL", "ERROR"})
_MAX_CONCURRENCY = 16
_TIMEOUT_MAC_DINH = 21600


class LoiBienDich(ValueError):
    def __init__(self, ma: str, thong_diep: str, node_id: str = ""):
        super().__init__(f"{ma}: {thong_diep}")
        self.ma, self.node_id = ma, node_id


def la_tham_chieu(gia_tri: Any) -> Optional[tuple[str, str]]:
    if isinstance(gia_tri, str):
        m = _THAM_CHIEU.match(gia_tri.strip())
        if m:
            return m.group(1), m.group(2)
    return None


def _doi(gia_tri: Any, node_id: str) -> Any:
    """`$a.b` (Canvas cũ) → `{{ nodes.a.output.b }}`; chặn `{{ }}` khác."""
    if isinstance(gia_tri, dict):
        return {k: _doi(v, node_id) for k, v in gia_tri.items()}
    if isinstance(gia_tri, list):
        return [_doi(v, node_id) for v in gia_tri]
    if isinstance(gia_tri, str):
        m = _CU.match(gia_tri.strip())
        if m:
            return "{{ nodes.%s.output.%s }}" % (m.group(1), m.group(2))
        if "{{" in gia_tri and la_tham_chieu(gia_tri) is None:
            raise LoiBienDich("bieu_thuc_chua_ho_tro",
                              "chi ho tro {{ nodes.<id>.output.<cong> }}",
                              node_id)
    return gia_tri


def _tham_chieu_trong(gia_tri: Any) -> set[str]:
    if isinstance(gia_tri, dict):
        return set().union(*(_tham_chieu_trong(v) for v in gia_tri.values())) \
            if gia_tri else set()
    if isinstance(gia_tri, list):
        return set().union(*(_tham_chieu_trong(v) for v in gia_tri)) \
            if gia_tri else set()
    tc = la_tham_chieu(gia_tri)
    return {tc[0]} if tc else set()


def _node(n: dict, cc: dict[str, CongCu]) -> dict:
    nid = str(n.get("id", ""))
    if not _ID.match(nid):
        raise LoiBienDich("id_khong_hop_le", f"id node {nid[:70]!r}", nid[:64])
    loai = str(n.get("type", ""))
    if loai == "tool":
        data = n.get("data") or {}
        ten, params = str(data.get("tool", "")), data.get("params") or {}
        settings = data.get("settings") or {}
    elif loai.startswith("app."):
        ten, params = loai[4:], n.get("params") or {}
        settings = n.get("settings") or {}
    else:
        raise LoiBienDich("loai_node_chua_ho_tro", loai, nid)
    tool = cc.get(ten)
    if tool is None:
        raise LoiBienDich("node_khong_ton_tai", ten, nid)
    return {"id": nid, "type": f"app.{ten}", "type_version": tool.type_version,
            "params": _doi(dict(params), nid),
            "credential_ref": str(n.get("credential_ref") or ""),
            "settings": dict(settings), "thi_hanh": "job"}


def bien_dich(document: dict, *,
              cong_cu: Optional[dict[str, CongCu]] = None) -> dict:
    cc = _nguon.tat_ca() if cong_cu is None else cong_cu
    nodes: list[dict] = []
    edges: list[dict] = []
    trang_cua: dict[str, str] = {}
    for trang in document.get("pages") or []:
        pid = str(trang.get("id", ""))
        for n in trang.get("nodes") or []:
            nd = _node(n, cc)
            if nd["id"] in trang_cua:
                raise LoiBienDich("id_trung", nd["id"], nd["id"])
            trang_cua[nd["id"]] = pid
            nodes.append(nd)
        for c in trang.get("edges") or []:
            e = _canh_v3(c)
            e["kind"] = str(c.get("kind") or "DATA")
            e["condition"] = str(c.get("condition") or "")
            edges.append((pid, e))  # type: ignore[arg-type]
    if not nodes:
        raise LoiBienDich("do_thi_rong", "khong co node nao")

    ra_edges: list[dict] = []
    for pid, e in edges:  # type: ignore[misc]
        a, b = e["source_node"], e["target_node"]
        if a not in trang_cua or b not in trang_cua:
            raise LoiBienDich("canh_khong_hop_le", f"{a}->{b}", b)
        if e["kind"] not in _KIND:
            raise LoiBienDich("canh_khong_hop_le", e["kind"], b)
        if trang_cua[a] != pid or trang_cua[b] != pid:
            raise LoiBienDich("canh_khac_trang", f"{a}->{b}", b)
        ra_edges.append(e)

    # Kahn: thứ tự tô-pô + phát hiện chu trình.
    vao = {n["id"]: 0 for n in nodes}
    ke: dict[str, list[str]] = {n["id"]: [] for n in nodes}
    for e in ra_edges:
        ke[e["source_node"]].append(e["target_node"])
        vao[e["target_node"]] += 1
    q = deque(sorted(k for k, v in vao.items() if v == 0))
    thu_tu: list[str] = []
    while q:
        k = q.popleft()
        thu_tu.append(k)
        for t in sorted(ke[k]):
            vao[t] -= 1
            if vao[t] == 0:
                q.append(t)
    if len(thu_tu) != len(nodes):
        raise LoiBienDich("chu_trinh", "do thi co chu trinh")

    to_tien: dict[str, set[str]] = {k: set() for k in thu_tu}
    for k in thu_tu:
        for t in ke[k]:
            to_tien[t] |= to_tien[k] | {k}
    for n in nodes:
        for dich in _tham_chieu_trong(n["params"]):
            if dich not in to_tien[n["id"]]:
                raise LoiBienDich("tham_chieu_khong_phai_to_tien", dich, n["id"])

    cai_dat = document.get("settings") or {}
    return {
        "schema": SCHEMA, "inputs": [], "outputs": [],
        "settings": {
            "max_concurrency": max(1, min(_MAX_CONCURRENCY,
                                          int(cai_dat.get("max_concurrency", 4)))),
            "timeout_s": int(cai_dat.get("timeout_s", _TIMEOUT_MAC_DINH)),
        },
        "nodes": sorted(nodes, key=lambda n: n["id"]),
        "edges": sorted(ra_edges, key=lambda e: e["id"]),
        "thu_tu": thu_tu,
    }


__all__ = ["SCHEMA", "LoiBienDich", "bien_dich", "la_tham_chieu"]

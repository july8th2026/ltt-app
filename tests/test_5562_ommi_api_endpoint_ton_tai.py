"""Phep kiem o BIEN: moi endpoint `ommiApi.ts` (pha 3) goi PHAI ton tai that
trong router cua app.

Vi sao can rieng phep nay (spec DIEU_HUONG_AGENT.md, muc "Nghiem thu"): app
pha 3 CHUA deploy, nen khong the mo `https://app.lttstudios.com` de bam thu.
Doc lai `.ts`/`.py` roi "tin bang mat" la dung KENH KHAC voi kenh dang hoi
(bai hoc `doc-thu-dai-dien-thay-vi-doc-thu-that`) -- phep nay thay vao do
DOI CHIEU may: lay tap duong dan THAT tu `router.routes` (FastAPI, khong
phai doc lai plan) roi khop voi tung loi goi `request(...)` trich xuat bang
regex tu `ommiApi.ts`. Bat duoc loi go sai URL o CA HAI phia -- dung phia nao
sai cung do.
"""
from __future__ import annotations

import pathlib
import re

from apps.prompt_ai_ommi.routes import router

API = pathlib.Path("frontend/prompt-ai-ommi/src/ommiApi.ts")

# Chi soat phan pha 3 (them 27/09) -- tu dong dau muc them vao cuoi tep. Phan
# cu (resources/library/storyboard/...) khong thuoc pham vi lan J.
_MOC_PHA_3 = "PROMPT AI OMMI pha 3"


def _sau_moc(nguon: str) -> str:
    vi_tri = nguon.index(_MOC_PHA_3)
    return nguon[vi_tri:]


# Bat `request(` hoac `request<Kieu>(` roi doc chuoi dau tien (template hoac
# nhay don/kep -- goi khong co `${...}` khong can template) va, neu co,
# `method: '...'` trong object option ngay sau do (cung mot cau lenh, toi da
# vai dong).
_GOI = re.compile(
    r"request(?:<[^>]*>)?\(\s*[`'\"]([^`'\"]*)[`'\"]"
    r"(?:\s*,\s*\{[^}]*?method:\s*'([A-Z]+)'[^}]*?\})?",
    re.DOTALL,
)


def _duong_frontend() -> list[tuple[str, str]]:
    """Tra ve [(method, duong_da_chuan_hoa), ...] tu cac loi goi `request`."""
    nguon = _sau_moc(API.read_text(encoding="utf-8"))
    ra: list[tuple[str, str]] = []
    for mau, method in _GOI.findall(nguon):
        duong = mau.split("?", 1)[0]  # bo query string
        # `${id}` (bat ky bieu thuc JS nao trong ${...}) -> wildcard "*"
        duong = re.sub(r"\$\{[^}]*\}", "*", duong)
        ra.append((method or "GET", f"/api{duong}"))
    return ra


def _duong_backend() -> set[tuple[str, str]]:
    ra: set[tuple[str, str]] = set()
    for route in router.routes:
        duong = re.sub(r"\{[^}]*\}", "*", route.path)
        for method in getattr(route, "methods", None) or ["GET"]:
            ra.add((method, duong))
    return ra


def _khop(duong_fe: str, duong_be: str) -> bool:
    fe = duong_fe.split("/")
    be = duong_be.split("/")
    if len(fe) != len(be):
        return False
    return all(a == b or a == "*" or b == "*" for a, b in zip(fe, be))


def test_moi_loi_goi_frontend_deu_co_route_that():
    goi = _duong_frontend()
    assert goi, "khong trich xuat duoc loi goi request() nao -- regex sai hay tep rong?"
    be = _duong_backend()
    thieu = [
        (method, duong) for method, duong in goi
        if not any(m == method and _khop(duong, d) for m, d in be)
    ]
    assert thieu == [], f"frontend goi duong khong co that trong router: {thieu}"


def test_doi_chung_mot_duong_bia_phai_do_duoc():
    """Doi chung: mot duong KHONG co trong router phai bi bat, khong thi phep
    tren vo nghia vi "moi thu deu khop".
    """
    be = _duong_backend()
    assert not any(_khop("/api/briefs/xyz/frobnicate", d) for _, d in be)

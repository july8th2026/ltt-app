"""Placeholder cua meta prompt: bang quy doi + bo kiem.

VI SAO CO TEP NAY. Ban goc (`D:\\BOT GEMINI`) dung placeholder CHU HOA khai
tuong minh (`{BRIEF_VI}`, `{DURATION}`...); ben ta truoc day dung chu thuong
TINH trong `prompts/director_user.txt`. Chuyen 12 mau cua ban goc sang ma
khong co bang quy doi thi mau se render ra chuoi `{BRIEF_VI}` NGUYEN VAN roi
gui cho LLM -- khach tra tien cho mot loi nhac hong.

Chi khop `\\{[A-Z][A-Z0-9_]*\\}`. Mau chua vi du JSON (`{"scenes": []}`) la do
KHONG phai placeholder: khop rong tay se coi moi dau ngoac nhon la bien.
"""
from __future__ import annotations

import re

#: `{TEN}` -> nguon gia tri ben ta. Mo ta de nguoi doc biet HOI AI cap gia tri,
#: khong phai de may doc.
NGUON_GIA_TRI: dict[str, str] = {
    "TITLE": "ommi_brief.title",
    "PROJECT_NAME": "AppProject.name (rong neu brief chua gan project)",
    "BRIEF_VI": "ommi_brief.story_vi",
    "DURATION": "ommi_brief.target_duration_sec",
    "SCENES": "ommi_brief.target_scenes",
    "ASPECT_RATIO": "ommi_brief.aspect_ratio",
    "ASPECT": "dong nghia ASPECT_RATIO (mau storyboard dung ten nay)",
    "STYLE_FULL": "composer.style_description(style)",
    "STYLE_POSITIVE": "ommi_style.body",
    "STYLE_NEGATIVE": "ommi_style.negative",
    "ASSET_LIST": "ommi_binding kind=image",
    "VIDEO_LIST": "ommi_binding kind=video",
    "PROMPT": "prompt cua canh (mau storyboard)",
    "REF_NOTE": "ghi chu anh tham chieu cua canh",
    "CHARACTER_DESCRIPTION": "ommi_character.fixed_prompt_block",
}

_MAU = re.compile(r"\{([A-Z][A-Z0-9_]*)\}")


def tim_placeholder(body: str) -> list[str]:
    """Ten cac placeholder xuat hien trong `body`, giu thu tu, khong trung."""
    ra: list[str] = []
    for ten in _MAU.findall(str(body or "")):
        if ten not in ra:
            ra.append(ten)
    return ra


def _co_gia_tri_that(gia_tri) -> bool:
    """Rong hoac chi khoang trang KHONG phai co gia tri.

    Khach de trong o nhap la ca THAT (mau `Ong Ngoai` co 4 bien tu do). Coi
    rong la co gia tri thi mau render ra cau cut dau roi gui LLM.
    """
    if gia_tri is None:
        return False
    if isinstance(gia_tri, str):
        return bool(gia_tri.strip())
    return True


def kiem_placeholder(body: str, khai_bao: list[str],
                     co_gia_tri: dict) -> list[str]:
    """Ten con THIEU. Rong nghia la mau nay render duoc.

    Ba phep, thieu phep nao cung de lot mot dang loi rieng:
      1. bien DUNG trong body ma khong KHAI  -> khong ai biet de hoi khach;
      2. bien KHAI ma khong ai CAP gia tri   -> render ra `{TEN}` nguyen van;
      3. sau render con cap chu hoa nao       -> luoi cuoi, bat ca hai ca tren.
    """
    khai = list(khai_bao or [])
    dung = tim_placeholder(body)
    thieu: list[str] = [t for t in dung if t not in khai]           # phep 1
    for ten in khai:                                               # phep 2
        if not _co_gia_tri_that(co_gia_tri.get(ten)) and ten not in thieu:
            thieu.append(ten)
    if not thieu:                                                  # phep 3
        for ten in tim_placeholder(render(body, co_gia_tri)):
            if ten not in thieu:
                thieu.append(ten)
    return thieu


def render(body: str, co_gia_tri: dict) -> str:
    """Thay `{TEN}` bang gia tri. Ten khong co gia tri thi GIU NGUYEN.

    Giu nguyen chu khong thay bang rong: phep 3 cua `kiem_placeholder` dua vao
    viec ten thieu con hien ra de bat duoc. Thay bang rong la xoa bang chung.
    """
    def _the(m: re.Match) -> str:
        ten = m.group(1)
        gia_tri = co_gia_tri.get(ten)
        return str(gia_tri) if _co_gia_tri_that(gia_tri) else m.group(0)

    return _MAU.sub(_the, str(body or ""))

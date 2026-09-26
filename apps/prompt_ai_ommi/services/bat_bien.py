"""services/bat_bien.py — bat bien o BIEN cho giao bai sang app khac (spec Sec 8).

Thuoc cho dang loi `cho-noi-hai-module-vut-truong-im-lang`: doc sai ten khoa
roi `continue`, vut truong im lang. Goi o DUNG MOT cho — ngay truoc khi tra
ve `params["refs"]` cho job video (`routes/handoff.py`).

Pha 1 CHUA co `services/handoff_stage.py` (do la Pha 2 — ve giao bai
`ommi_handoff`). Pha 2 se IMPORT LAI dung ham nay tu day, khong viet lai.

`has_binding` (quyet dinh D-3, xem dau plan): B-5 can biet canh co
`ommi_binding` hay khong — thong tin nay khong nam trong 3 tham so
(prompt, refs, skipped) ma spec Sec 8 liet ke, nen day la mot tham so tu
khoa THEM, mac dinh `False` giu nguyen hanh vi goi 3-tham so cu.

⚠️ HAI CACH VIET THE, mot khong gian handle (lech spec/plan, DA BAO dieu phoi):
spec Sec 8 phat bieu B-1 theo dang `@IMG_k`/`@VID_k` (dang cua `taovideo`, xem
`tag_map` o Sec 6.2), con `ommi_binding` sinh the dang `@IMAGE_k`/`@VIDEO_k`
va ma vi du cua plan Task 7 chi khop hai dang sau. Neu chi khop MOT dang thi
sang pha 2 — luc prompt da doi the sang `@IMG_k` — se khong con dieu kien nao
bat, va N-1 quay lai IM LANG. Nen o day ca hai dang duoc chuan hoa ve mot
khong gian handle duy nhat (`image_k` / `video_k`) truoc khi so.
"""
from __future__ import annotations

import re

from apps.taovideo.refs import VALID_IMAGE_ROLES

#: `IMAGE` phai dung TRUOC `IMG` trong nhom chon: `re` chon nhanh dau tien
#: khop duoc, nen dao thu tu se lam `@IMAGE_1` bi doc thanh `IMG` + rac.
_TAG_RE = re.compile(r"@(IMAGE|IMG|VIDEO|VID)_(\d+)", re.IGNORECASE)
_HANDLE_RE = re.compile(r"(image|img|video|vid)_(\d+)", re.IGNORECASE)

#: Hai cach viet -> mot loai. Tuple co thu tu co dinh, khong phai dict duyet
#: ngau nhien: ket qua phai TAT DINH (`camera` nam trong `idempotency.key_fields`
#: cua taovideo, va thong bao loi cung phai lap lai duoc).
_LOAI_THEO_TIEN_TO = (("image", "image"), ("img", "image"),
                      ("video", "video"), ("vid", "video"))


def _loai(tien_to: str) -> str:
    thap = tien_to.lower()
    for ten, loai in _LOAI_THEO_TIEN_TO:
        if thap == ten:
            return loai
    return thap


def _chuan_handle(raw: object) -> str:
    """`@IMG_1`, `IMAGE_1`, `image_1` -> `image_1`. Chuoi la giu nguyen (chu
    thuong) de B-2 con bao duoc ten that ma ben goi dua vao."""
    chuoi = str(raw or "").strip().lstrip("@").lower()
    khop = _HANDLE_RE.fullmatch(chuoi)
    if khop is None:
        return chuoi
    return f"{_loai(khop.group(1))}_{khop.group(2)}"


def bat_bien_giao_bai(prompt: str, refs: list[dict], skipped: list[dict],
                      *, has_binding: bool = False) -> None:
    prompt_handles = {f"{_loai(tien_to)}_{so}"
                      for tien_to, so in _TAG_RE.findall(prompt or "")}
    ref_handles = [_chuan_handle(r.get("handle")) for r in (refs or [])]
    skipped_handles = {_chuan_handle(s.get("handle")) for s in (skipped or [])}

    # B-3: mot handle khong duoc xuat hien hai lan trong refs.
    if len(ref_handles) != len(set(ref_handles)):
        raise ValueError(
            "B-3: mot handle xuat hien hai lan trong refs — danh so vo.")

    ref_handle_set = set(ref_handles)

    # B-1: prompt nhac handle nao thi handle do phai co trong refs HOAC skipped.
    #
    # ⭐ Dieu kien `skipped` KHONG duoc bo: anh khach da xoa la ca HOP LE. Bao
    #    do o day la bao dong gia, va nguoi ta se TAT phep kiem di — mat luon
    #    luoi that (bai hoc `banh-coc-do-cach-go-thay-vi-do-tinh-chat`).
    for handle in sorted(prompt_handles):  # sorted: thong bao loi tat dinh
        if handle not in ref_handle_set and handle not in skipped_handles:
            raise ValueError(
                f"B-1: prompt nhac @{handle.upper()} nhung refs khong mang "
                "theo va cung khong nam trong skipped — anh se mat khong ai biet.")

    # B-2: refs mang theo handle nao thi prompt phai nhac handle do.
    for handle in sorted(ref_handle_set):
        if handle not in prompt_handles:
            raise ValueError(
                f"B-2: refs mang theo @{handle.upper()} nhung prompt khong "
                "nhac — tra tien cho anh vo ich.")

    # B-4: role cua ref anh phai thuoc VALID_IMAGE_ROLES.
    for ref in (refs or []):
        if str(ref.get("kind")) == "image":
            role = str(ref.get("role") or "")
            if role not in VALID_IMAGE_ROLES:
                raise ValueError(
                    f"B-4: role {role!r} khong hop le cho anh — ben nhan se "
                    "am tham remap ve reference_image.")

    # B-5: co binding ma ca refs va skipped deu rong la chac chan sai duong doc.
    if has_binding and not refs and not skipped:
        raise ValueError(
            "B-5: canh co ommi_binding nhung refs va skipped deu rong — "
            "bindings co ma khong sinh duoc ref nao, chac chan lech duong doc.")

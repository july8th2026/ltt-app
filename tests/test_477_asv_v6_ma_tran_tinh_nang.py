"""ASV V6 pha 01 + 04 — moi tinh nang Viral co MOT pha V6, khong cai nao bien mat.

🔑 Ma tran V5 co 12 dong `DEFER` khong kem pha V6. Mot `DEFER` khong kem pha la
   cach mot tinh nang bien mat khoi tai lieu ma khong ai quyet dinh bo no — dung
   thu de bai pha 04 cam: *"khong de feature bien mat trong docs"*.

⭐ Chot TAP HOP, khong chot so luong (`banh-coc-cong-chat-luong`): tap ten o ma
   tran V6 phai BANG DUNG tap ten o ma tran V5. Them mot dong vao V5 ma quen anh
   xa -> do. Xoa mot dong khoi V6 -> do. Bia mot dong -> do.
"""
from __future__ import annotations

import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[1]
V5 = GOC / "docs/auto_scan_video_v5/FEATURE_PARITY_MATRIX.md"
V6 = GOC / "docs/auto_scan_video_v6/MA_TRAN_TINH_NANG_V6.md"

PHA_HOP_LE = {"V4", "V5", "LOAI"} | {f"{i:02d}" for i in range(35)}
TRANG_THAI = {"XONG", "MOT_PHAN", "CHUA", "CAN_ADR", "LOAI"}


def _v5() -> dict[str, str]:
    ra = {}
    for l in V5.read_text(encoding="utf-8").splitlines():
        if l.startswith("| ") and not re.match(r"^\|\s*(Feature|-{2,})", l) and "---" not in l:
            c = [x.strip() for x in l.strip().strip("|").split("|")]
            if len(c) >= 6:
                ra[c[0]] = re.sub(r"[`*]", "", c[-1]).strip()
    return ra


def _v6() -> dict[str, tuple[str, str, str]]:
    ra, trong = {}, False
    for l in V6.read_text(encoding="utf-8").splitlines():
        if l.startswith("| Tính năng |"):
            trong = True
            continue
        if not trong or not l.startswith("| ") or set(l) <= set("|- "):
            continue
        c = [x.strip() for x in l.strip().strip("|").split("|")]
        if len(c) >= 5:
            ra[c[0]] = (c[2], c[3], "|".join(c[4:]))
    return ra


def test_ma_tran_V5_con_du_59_dong_de_doi_chieu():
    """Doi chung cho bo phan tich: neu no doc ra 0 dong thi bai duoi xanh-rong."""
    assert len(_v5()) >= 50, len(_v5())


def test_tap_ten_V6_BANG_DUNG_tap_ten_V5():
    v5, v6 = set(_v5()), set(_v6())
    assert not v5 - v6, f"tinh nang BIEN MAT khoi ma tran V6: {sorted(v5 - v6)}"
    assert not v6 - v5, f"tinh nang BIA RA trong ma tran V6: {sorted(v6 - v5)}"


def test_moi_dong_co_PHA_hop_le_va_TRANG_THAI_hop_le():
    for ten, (pha, tt, _) in _v6().items():
        assert pha in PHA_HOP_LE, (ten, pha)
        assert tt in TRANG_THAI, (ten, tt)


def test_KHONG_con_DEFER_tro_trui():
    """🔴 Menh de de bai pha 01: moi dong tung la `DEFER` o V5 nay co mot pha."""
    v5, v6 = _v5(), _v6()
    tung_defer = [t for t, qd in v5.items() if "DEFER" in qd.upper()]
    assert len(tung_defer) >= 10, "bo phan tich khong con thay cac dong DEFER"
    for t in tung_defer:
        pha, tt, _ = v6[t]
        assert "DEFER" not in (pha + tt).upper(), t
        assert pha in PHA_HOP_LE, t


def test_moi_dong_LOAI_deu_co_LY_DO():
    """⛔ Mot dong LOAI khong ly do la mot DEFER doi ten."""
    for ten, (pha, tt, ly_do) in _v6().items():
        if tt == "LOAI" or pha == "LOAI":
            assert len(ly_do.strip()) >= 20, (ten, ly_do)


def test_moi_dong_XONG_tro_toi_CHO_CHUNG_MINH():
    """Mot dong XONG khong tro toi tep/test/commit nao la mot loi tuyen bo."""
    for ten, (_pha, tt, can_cu) in _v6().items():
        if tt == "XONG":
            assert "`" in can_cu, (ten, can_cu)

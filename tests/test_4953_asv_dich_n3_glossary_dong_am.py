"""B14/V3 N3 — glossary sua loi DONG AM cua ASR truoc khi dich, muon
`D:\\Viral\\...\\ai_dich.py:1290-1336 _tom_tat_glossary` (chi doc). Viral do
that 01/09 (gemini-3.1-flash-lite, 300 cue dau): model tu bat 8/8 loi dong am
da liet ke khi duoc dan cau nay.

Ghep vao DUNG loi goi da tra tien san (`ho_so_dich.dung`, MOT lan/video) —
⛔ KHONG them luot goi model moi. Day la mot CUA PHAT HIEN: model tu ghi nghi
van dong am no thay vao `bang_sua_dong_am`, KHONG tu sua ban dich nao — xem
chu thich o `ho_so_dich.KHOA`.
"""
from __future__ import annotations

import ast
import inspect
import json


class _RunGia:
    """Chi ba truong ma `goi_tinh_tien` doc. Khong can CSDL."""

    def __init__(self, credit_held: int = 0) -> None:
        self.id = 1
        self.owner_id = 1
        self.credit_held = credit_held


def test_KHOA_co_bang_sua_dong_am():
    from apps.auto_scan_video import ho_so_dich

    assert "bang_sua_dong_am" in ho_so_dich.KHOA


def test_doc_parse_bang_sua_dong_am_tu_model():
    from apps.auto_scan_video import ho_so_dich

    noi_dung = json.dumps({
        "the_loai": "phim truyen", "so_nguoi_noi": 2,
        "bang_dai_tu": {}, "bang_ten_rieng": {}, "giong_van": "",
        "bang_sua_dong_am": {"武林根": "五灵根", "根国清政": "根骨清正"},
    }, ensure_ascii=False)
    ra = ho_so_dich._doc(noi_dung)
    assert ra["bang_sua_dong_am"] == {"武林根": "五灵根", "根国清政": "根骨清正"}


def test_doc_THIEU_khoa_van_mac_dinh_RONG__tuong_thich_nguoc():
    """⛔ Doi chung: mot phan hoi model CU (chua co khoa nay) van phai doc
    duoc — khong duoc nem chi vi thieu mot khoa MOI.
    """
    from apps.auto_scan_video import ho_so_dich

    noi_dung = json.dumps({
        "the_loai": "phim truyen", "so_nguoi_noi": 2,
        "bang_dai_tu": {}, "bang_ten_rieng": {}, "giong_van": "",
    }, ensure_ascii=False)
    ra = ho_so_dich._doc(noi_dung)
    assert ra["bang_sua_dong_am"] == {}
    assert set(ra) == set(ho_so_dich.KHOA)


def test_bang_sua_dong_am_RONG_van_la_ket_qua_hop_le():
    """`{}` = model khong nghi ngo dong am nao — MOT cau tra loi hop le cho
    phan lon video, khong phai mot loi doc (xem chu thich `_doc`)."""
    from apps.auto_scan_video import ho_so_dich

    noi_dung = json.dumps({
        "the_loai": "x", "so_nguoi_noi": 1, "bang_dai_tu": {},
        "bang_ten_rieng": {}, "giong_van": "", "bang_sua_dong_am": {},
    }, ensure_ascii=False)
    ra = ho_so_dich._doc(noi_dung)
    assert ra["bang_sua_dong_am"] == {}


def test_KHONG_them_luot_goi_LLM_moi__van_dung_MOT_goi_tinh_tien():
    """🔴 N3 CHI sua loi nhac cua loi goi da co — kiem bang AST, khong bang
    van ban ma nguon (chuoi co the doi ma cau truc goi khong doi).
    """
    from apps.auto_scan_video import ho_so_dich

    cay = ast.parse(inspect.getsource(ho_so_dich))
    goi_thuoc_tinh = [n for n in ast.walk(cay)
                      if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
    qua_cua = [c for c in goi_thuoc_tinh if c.func.attr == "goi_tinh_tien"]
    assert len(qua_cua) == 1, (
        f"mong DUNG mot loi goi goi_tinh_tien trong ho_so_dich.py, thay {len(qua_cua)}")


def test_loi_nhac_THAT_khong_kem_vi_du_dich_dong_am_cu_the(monkeypatch):
    """⛔ "Mot vi du trong loi nhac la mot menh lenh ngam" (24/09, bon vi du
    khong dau tung lam tut mot ten von dung) — bat loi nhac THAT SU gui cho
    model (bang cach chan `ai.goi_tinh_tien`), khong phai doan tinh tu docstring:
    loi nhac CHI duoc mo ta HINH DANG can, KHONG duoc dua cap "chu nghe nham"
    cu the nao (kem ca cac vi du minh hoa trong chinh chu thich cua tep nay).
    """
    from apps.auto_scan_video import ai, ho_so_dich

    bat: dict = {}

    def gia(db, run, thao_tac, tin, *, stage, item_key, ctx=None, temperature=None):
        bat["tin"] = tin
        return {"noi_dung": json.dumps({
            "the_loai": "x", "so_nguoi_noi": 1, "bang_dai_tu": {},
            "bang_ten_rieng": {}, "giong_van": "", "bang_sua_dong_am": {},
        }, ensure_ascii=False), "su_dung": None}

    monkeypatch.setattr(ai, "goi_tinh_tien", gia)
    ho_so_dich.dung(None, _RunGia(), {"doan": [{"ma": "seg_0001", "chu": "x"}]})

    he_thong = bat["tin"][0]["content"]
    assert "bang_sua_dong_am" in he_thong
    # Khong dua cap dich-san CU THE (chu Han thuc te tu vi du minh hoa cua
    # chinh chu thich `ho_so_dich.KHOA`) vao loi nhac that su.
    for cum in ("武林根", "五灵根", "根国清政", "根骨清正"):
        assert cum not in he_thong, f"loi nhac ro ri vi du dich san: {cum!r}"


def test_dung_END_TO_END_voi_ban_gia_tra_bang_sua_dong_am(monkeypatch):
    """Goi that `ho_so_dich.dung()` (khong DB) voi mot ban gia model co
    `bang_sua_dong_am`, xac nhan ket qua mang dung truong nay.
    """
    from apps.auto_scan_video import ai, ho_so_dich

    def gia(db, run, thao_tac, tin, *, stage, item_key, ctx=None, temperature=None):
        return {"noi_dung": json.dumps({
            "the_loai": "phim truyen", "so_nguoi_noi": 2,
            "bang_dai_tu": {"我": "toi"}, "bang_ten_rieng": {},
            "giong_van": "", "bang_sua_dong_am": {"根国清政": "根骨清正"},
        }, ensure_ascii=False), "su_dung": None}

    monkeypatch.setattr(ai, "goi_tinh_tien", gia)
    ra = ho_so_dich.dung(None, _RunGia(),
                         {"doan": [{"ma": "seg_0001", "chu": "根国清政"}]})
    assert ra["bang_sua_dong_am"] == {"根国清政": "根骨清正"}


def test_bang_sua_dong_am_CHUA_duoc_long_tieng_doc__ranh_gioi_pham_vi():
    """⚠️ Ghi lai RANH GIOI pham vi cua lan nay: `long_tieng.py` (L1 so huu,
    ⛔ khong duoc cham) chua doc truong `bang_sua_dong_am` — no moi la mot khoa
    DUOC GHI RA (hien trong `tom_tat['ho_so_dich']` qua `giai_doan_noi_dung.py`),
    chua duoc NOI vao loi nhac dich that su. Noi tiep (doc + dan vao
    `long_tieng.loi_nhac`) la viec CUA L1 — bao dieu phoi, khong tu cham vao
    `long_tieng.py`. Test nay se DO (can sua lai) neu ai do noi truong nay vao
    ma khong cap nhat lai chu thich/bao cao.
    """
    from apps.auto_scan_video import long_tieng

    nguon = inspect.getsource(long_tieng.loi_nhac)
    assert "bang_sua_dong_am" not in nguon, (
        "long_tieng.loi_nhac gio DA doc bang_sua_dong_am — cap nhat lai chu "
        "thich pham vi N3 (khong con la cong viec con dang cua L1)")

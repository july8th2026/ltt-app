"""Pha 21 — khach chon duoc that thu san pham hua.

Bon nhom:

  A. Hai preset      — truoc pha 21 khach KHONG co cach nao chon
  B. Chon giong      — khong con "Giọng mặc định", mot lua chon engine tu choi
  C. Bat SOM         — cai gi hong thi hong o CUA, khong o giua chuoi
  D. Khong thuat ngu — khach khong thay ten giai doan, provider hay duong dan
"""
from __future__ import annotations

from apps.auto_scan_video import gia, hop_dong_v4, pipeline


# ══════════════════════════════════════════════════════════════════════════════
#  A. Hai preset
# ══════════════════════════════════════════════════════════════════════════════

def test_ca_HAI_preset_deu_co_trong_bang_cho_khach():
    """🔴 Truoc pha 21, chuoi `preset` **khong xuat hien mot lan nao** trong
    `routes.py` lan giao dien.

    Tuc tinh nang dau bang cua ca ban V4 — hai preset — khach khong co cach nao
    chon, va moi lan chay deu roi ve mac dinh `localize_preserve_picture`. Ca
    duong `smart_localize` ma pha 12 den 18 dung nen la mot duong **khong ai voi
    toi duoc**.
    """
    assert {m for m, _, _ in gia.PRESET_BANG} == set(hop_dong_v4.PRESET)


def test_moi_preset_deu_co_mo_ta_bang_TIENG_VIET_cho_nguoi_dung():
    for ma, ten, mo_ta in gia.PRESET_BANG:
        assert ten and mo_ta, f"{ma} thieu ten hoac mo ta"
        assert len(mo_ta) > 40, f"{ma}: mo ta qua ngan de quyet dinh"


def test_mo_ta_preset_KHONG_dung_thuat_ngu_ky_thuat():
    """⛔ Mo ta viet cho **khach**. Ho quyet dinh dua tren dieu HO quan tam —
    hinh co bi cat khong — chu khong dua tren cach ta lam."""
    cam = ("stream copy", "re-encode", "keyframe", "GOP", "nvenc", "libx264",
           "ffmpeg", "codec", "concat", "encode")
    for ma, ten, mo_ta in gia.PRESET_BANG:
        van = f"{ten} {mo_ta}".lower()
        for t in cam:
            assert t.lower() not in van, f"{ma} lo thuat ngu `{t}`"


def test_preset_CAT_noi_that_ve_CAI_GIA():
    """⚠️ Preset cat ma hoa lai luong hinh, nen ban ra khong con giong het ban goc
    tung diem anh. Giau dieu do di la ban mot thu khac voi thu minh giao."""
    mo_ta = next(m for ma, _, m in gia.PRESET_BANG
                 if ma == hop_dong_v4.PRESET_CAT_THONG_MINH)
    assert "mã hoá lại" in mo_ta or "mã hóa lại" in mo_ta


def test_preset_khong_hop_le_bi_TU_CHOI():
    assert gia.preset_hop_le(hop_dong_v4.PRESET_GIU_HINH)
    assert not gia.preset_hop_le("preset bia dat")
    assert gia.preset_mac_dinh() in hop_dong_v4.PRESET


# ══════════════════════════════════════════════════════════════════════════════
#  B. Chon giong
# ══════════════════════════════════════════════════════════════════════════════

def test_danh_sach_giong_LUON_co_thu_de_chon(db_rong):
    """🔴 Truoc pha 21 giao dien moi khach chon "Giọng mặc định" — mot lua chon
    ma engine **tu choi phuc vu**.

    Pha 09 da bo giong mac dinh im lang (`rang_giong` nem khi `USER_SELECTED`
    khong kem ma giong). Nen mot khach chon o rong se di qua bon giai doan, bi
    giu credit, roi hong o giua chuoi. `V4_MVP_PRODUCT_CONTRACT` goi dung ten cho
    viec do: mot **false feature**.

    ⭐ Cach sua khong phai lam engine de dai hon — la thoi moi mot thu khong co,
       va luon co giong MAU de danh sach khong bao gio rong.
    """
    ds = gia.giong_chon_duoc(db_rong, "khach-chua-co-giong-nao")
    assert ds, "khach chua nhan ban giong nao ma danh sach rong — khong co gi de chon"
    assert all(g["ma"] for g in ds), "mot muc khong co ma — do la o rong doi ten"


def test_giong_MAU_deu_hop_le_voi_engine(db_rong):
    """⛔ Mot muc trong danh sach ma `rang_giong` tu choi la mot cai bay: khach
    chon duoc, va hong o giua chuoi."""
    from apps.auto_scan_video import rang_giong
    from apps.ltt_voice.giong_mau import hop_le

    for g in gia.giong_chon_duoc(db_rong, "uX"):
        if hop_le(g["ma"]):
            kq = rang_giong.rang(
                None, owner_id="uX",
                yeu_cau=rang_giong.tu_thiet_lap(
                    {"che_do_giong": hop_dong_v4.CHE_DO_GIONG_TU_CHON,
                     "giong_id": g["ma"]}))
            assert kq.da_chot, f"giong mau {g['ma']} khong rang duoc"


def test_hai_cach_chon_giong_deu_duoc_khai():
    assert {m for m, _, _ in gia.CHE_DO_GIONG_BANG} == set(hop_dong_v4.CHE_DO_GIONG)
    assert gia.che_do_giong_hop_le(hop_dong_v4.CHE_DO_GIONG_TU_KHOP)
    assert not gia.che_do_giong_hop_le("bia dat")


def test_AUTO_MATCH_noi_THAT_rang_no_chua_san_sang():
    """⚠️ Pha 19 ghi lai rang khong giai doan nao sinh `HoSoNoiDung`, nen tu khop
    se **hoan lai** chu khong chon bua mot giong.

    ⛔ Bay mot lua chon khong chay duoc ma khong noi gi la dung thu
       `V4_MVP_PRODUCT_CONTRACT` goi la "false feature".
    """
    mo_ta = next(m for ma, _, m in gia.CHE_DO_GIONG_BANG
                 if ma == hop_dong_v4.CHE_DO_GIONG_TU_KHOP)
    assert "hoàn thiện" in mo_ta or "chưa" in mo_ta, (
        "AUTO_MATCH duoc bay ra nhu mot tinh nang da chay duoc")


# ══════════════════════════════════════════════════════════════════════════════
#  D. Khong thuat ngu ky thuat trong bang cho khach
# ══════════════════════════════════════════════════════════════════════════════

def test_bang_cho_khach_KHONG_lo_ten_giai_doan():
    van = " ".join(f"{a} {b} {c}" for a, b, c in
                   (*gia.PRESET_BANG, *gia.CHE_DO_GIONG_BANG,
                    *gia.CHE_DO_THOI_GIAN))
    for g in pipeline.CHUOI:
        assert g.ten not in van, f"lo ten giai doan `{g.ten}`"


def test_bang_cho_khach_KHONG_lo_ten_app_noi_bo():
    van = " ".join(f"{a} {b} {c}" for a, b, c in
                   (*gia.PRESET_BANG, *gia.CHE_DO_GIONG_BANG))
    for app in ("asv_media", "asv_gpu", "asv_run", "ltt_llm", "ltt_voice"):
        assert app not in van, f"lo ten app noi bo `{app}`"


def test_ma_preset_trong_bang_KHOP_hop_dong_khong_go_lai_chuoi():
    """⛔ Mot chuoi chep lai la mot chuoi se troi. Bang giao dien phai lay ma tu
    hop dong san pham, khong go lai."""
    import ast
    from pathlib import Path

    van = Path(gia.__file__).read_text(encoding="utf-8")
    cay = ast.parse(van)
    ham = [n for n in ast.walk(cay)
           if isinstance(n, ast.FunctionDef) and n.name == "_preset_bang"][0]
    chuoi = {n.value for n in ast.walk(ham)
             if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    for ma in hop_dong_v4.PRESET:
        assert ma not in chuoi, f"ma preset `{ma}` bi go lai thay vi lay tu hop dong"


# ══════════════════════════════════════════════════════════════════════════════

import pytest  # noqa: E402


@pytest.fixture()
def db_rong(tmp_path, monkeypatch):
    """CSDL rong: du de hoi danh sach giong, khong can chay gi."""
    import platform_core.db as dbmod

    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'gd.db').as_posix()}")
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables

    load_app_tables()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    try:
        yield db
    finally:
        db.close()
        dbmod.reset_engine()


# ══════════════════════════════════════════════════════════════════════════════
#  E. CHINH CAI FORM — qua HTTP that
# ══════════════════════════════════════════════════════════════════════════════
#
# 🔴 **Bon nhom tren khong cham toi route lan giao dien**, va kiem dot bien chi ra
#    dieu do bang tam lo hong lien tiep: bo kiem preset, bo kiem che do giong, bo
#    doi giong, khong luu preset vao `settings`, khong truyen bang cho giao dien,
#    tra lai o "Giọng mặc định"... tat ca deu XANH.
#
# ⛔ Va do la **trong tam cua ca pha 21**. Toi da kiem cac BANG DU LIEU phia sau
#    form thay vi kiem chinh cai form — tuc kiem thu de kiem thay vi thu quan
#    trong.

from tests.test_423_asv_giao_dien import moi_truong  # noqa: E402,F401

GIONG_THU = "Minh \u0110\u1ee9c"


def _nop(client, csrf, tmp_path, ten="a.mp4", **them):
    from tests.fixtures.asv_media import tiny_mp4

    tep = tiny_mp4(tmp_path / ten, duration_s=1.0)
    du_lieu = {"csrf_token": csrf, "che_do": "fit_original",
               "giong_id": GIONG_THU}
    du_lieu.update(them)
    with open(tep, "rb") as f:
        return client.post("/auto-scan-video/tao", data=du_lieu,
                           files={"video": (ten, f, "video/mp4")})


def _settings(run_id: str) -> dict:
    import platform_core.db as dbmod
    from apps.auto_scan_video.tables import AsvRun

    db = next(dbmod.get_session())
    try:
        return dict((db.get(AsvRun, run_id).settings) or {})
    finally:
        db.close()


def test_FORM_hien_du_hai_preset(moi_truong, tmp_path):
    """🔴 Truoc pha 21 form khong co o nao cho preset, nen ca duong
    `smart_localize` la mot duong khach khong voi toi duoc."""
    _app, a, _csrf, _b, _cb = moi_truong
    van = a.get("/auto-scan-video").text
    for ma in hop_dong_v4.PRESET:
        assert f'value="{ma}"' in van, f"form thieu o chon preset `{ma}`"


def test_FORM_khong_con_o_GIONG_MAC_DINH(moi_truong, tmp_path):
    """⛔ Engine tu choi phuc vu no (pha 09). Moi khach chon no la moi ho di qua
    bon giai doan, bi giu credit, roi hong o giua chuoi.

    ## Vi sao phep kiem nay duoc viet lai o V5

    🔴 Ban cu quet **ca trang** tim chuoi `'<option value="">'`. Menh de that su
       can chot la hep hon nhieu: *o chon GIONG khong duoc co lua chon rong*.

       Hai thu do trung nhau chi khi trang co dung MOT `<select>`. V5 them hai o
       loc (gioi · vung), va mot o loc **phai** co muc rong — do la "khong loc
       mat nay", mot lua chon that va hop le. Ban cu bao dong tren chinh no.

    ⭐ Ban viet lai **kho xanh hon**, khong de hon: no khong hoi "chuoi do co
       vang mat khong" ma duyet TUNG `<option>` cua o giong va doi moi muc co
       mot `value` khac rong. Mot o giong co ba muc rong o giua danh sach se bi
       bat o day, trong khi ban cu chi bat duoc neu chuoi khop tung ky tu.
    """
    import re

    _app, a, _csrf, _b, _cb = moi_truong
    van = a.get("/auto-scan-video").text

    khoi = re.search(r'<select[^>]*\bid="asv-giong"[^>]*>(.*?)</select>',
                     van, re.S)
    assert khoi, "khong tim thay o chon giong `#asv-giong` tren trang"
    muc = re.findall(r'<option\s+value="([^"]*)"', khoi.group(1))
    assert muc, "o chon giong khong co muc nao"
    assert all(m.strip() for m in muc), (
        "o chon giong co mot muc RONG — do la 'Giong mac dinh' quay lai")
    assert GIONG_THU in van, "form khong co giong mau nao de chon"


def test_nop_preset_CAT_thi_lan_chay_MANG_dung_preset_do(moi_truong, tmp_path):
    """Menh de trung tam: khach chon duoc, va lua chon do **den duoc** lan chay."""
    from tests.fixtures import asv_media as fx

    fx.require_ffmpeg()
    _app, a, csrf, _b, _cb = moi_truong
    r = _nop(a, csrf, tmp_path, preset=hop_dong_v4.PRESET_CAT_THONG_MINH)
    assert r.status_code == 200, r.text[:300]
    run_id = str(r.url).rstrip("/").rsplit("/", 1)[-1]
    assert _settings(run_id)["preset"] == hop_dong_v4.PRESET_CAT_THONG_MINH


def test_nop_preset_KHONG_CO_THAT_bi_tu_choi_o_CUA(moi_truong, tmp_path):
    """⛔ Mot gia tri khong hop le phai bi tu choi ngay o cua chu khong di xuong
    worker roi hong o giua chuoi."""
    from tests.fixtures import asv_media as fx

    fx.require_ffmpeg()
    _app, a, csrf, _b, _cb = moi_truong
    r = _nop(a, csrf, tmp_path, preset="preset-bia-dat")
    # ⚠️ Route tra **400 kem form va thong bao**, khong phai 200. Do la hanh vi
    #    dung cho mot lan nop sai — va khang dinh `== 200` cua ban dau la cho SAI,
    #    khong phai ma. Cai phai chot la: khong tao duoc lan chay, va khach doc
    #    duoc vi sao.
    assert r.status_code in (200, 400), r.status_code
    assert "/run/" not in str(r.url), "preset bia dat van tao duoc lan chay"
    assert "không hợp lệ" in r.text


def test_TRANG_LOI_van_con_du_lua_chon_de_nop_lai(moi_truong, tmp_path):
    """🔴 Lo hong ma kiem dot bien tim ra: khong ai kiem TRANG LOI.

    Mot khach nop sai se nhan lai form — va neu form do khong con giong nao de
    chon thi ho **ket**: khong sua duoc loi vua bao, va khong co gi de bam.

    ⭐ Trang loi la trang duoc xem NHIEU hon trang binh thuong o dung nhung luc
       nguoi ta buc nhat. No khong duoc phep la ban rut gon cua trang chinh.
    """
    from tests.fixtures import asv_media as fx

    fx.require_ffmpeg()
    _app, a, csrf, _b, _cb = moi_truong
    r = _nop(a, csrf, tmp_path, preset="preset-bia-dat")
    assert "/run/" not in str(r.url)
    assert GIONG_THU in r.text, "trang loi khong con giong nao de chon"
    for ma in hop_dong_v4.PRESET:
        assert f'value="{ma}"' in r.text, f"trang loi thieu o chon preset `{ma}`"


def test_nop_che_do_giong_KHONG_CO_THAT_bi_tu_choi(moi_truong, tmp_path):
    from tests.fixtures import asv_media as fx

    fx.require_ffmpeg()
    _app, a, csrf, _b, _cb = moi_truong
    r = _nop(a, csrf, tmp_path, che_do_giong="bia-dat")
    assert "/run/" not in str(r.url)


def test_nop_KHONG_giong_bi_tu_choi_SOM(moi_truong, tmp_path):
    """⭐ `USER_SELECTED` ma khong co giong thi pha 14 se nem o GIUA chuoi — sau
    khi khach da doi qua bon giai doan va da bi giu credit.

    Mot cau "hay chon mot giong doc" o cua tot hon mot lan chay hong o phut thu
    muoi.
    """
    from tests.fixtures import asv_media as fx

    fx.require_ffmpeg()
    _app, a, csrf, _b, _cb = moi_truong
    r = _nop(a, csrf, tmp_path, giong_id="")
    assert "/run/" not in str(r.url), "tao duoc lan chay khong co giong"
    assert "giọng" in r.text.lower()


def test_khong_nop_preset_thi_ve_MAC_DINH_chu_khong_hong(moi_truong, tmp_path):
    """Tuong thich nguoc: mot client cu khong gui `preset` van chay duoc."""
    from tests.fixtures import asv_media as fx

    fx.require_ffmpeg()
    _app, a, csrf, _b, _cb = moi_truong
    r = _nop(a, csrf, tmp_path)
    run_id = str(r.url).rstrip("/").rsplit("/", 1)[-1]
    assert _settings(run_id)["preset"] == hop_dong_v4.PRESET_MAC_DINH

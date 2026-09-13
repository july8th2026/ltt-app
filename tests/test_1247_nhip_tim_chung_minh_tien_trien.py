"""test_1247 — nhip tim phai chung minh TIEN TRIEN, khong phai su song cua luong.

## Su co (L-08, 13/09/2026) — day moi la ly do lease BAT TU

`admission.keep_alive` dap nhip vo dieu kien:

    while not stop.wait(HEARTBEAT_SECONDS):
        heartbeat_by_id(lease_id)

Nhip ay chung minh **luong con song**, khong chung minh **cong viec con tien
trien**. Hai cau ay tach nhau ra dung luc te nhat: khach cat giua mot luot
stream, generator dong bo bi bo roi va treo vinh vien tai `yield`, nhung luong
nhip van dap deu. Voi `reclaim_expired` thi lease ay trong khoe manh **mai mai**,
nen `ORPHAN_TIMEOUT = 20 phut` KHONG BAO GIO khai hoa.

⇒ Do duoc tren may that: mot suat GPU bi giu **>= 643 s**; sau ban va dau van
  **~225 s**. Khong phai "cham" — la **bat tu**, vi ca ba lop don deu bi cung
  mot loi noi doi bit mat.

⚠️ Lop nay la LUOI, khong phai duong chinh. Duong chinh la `khi_dut`
   (`test_1246`), do duoc la chay o +0,05 s. Luoi nay ton tai de lop cuoi
   (`reclaim_expired`) **voi toi duoc**, chu khong de nhanh.
"""
import time

from platform_core.llm import admission


def _bat_nhip(monkeypatch, nhip: list, nha: list, nhip_s: float = 0.05) -> None:
    """Cat duong CSDL. Bo nay do LUAT DAP NHIP, khong do SQLAlchemy."""
    monkeypatch.setattr(admission, "heartbeat_by_id", lambda i: nhip.append(i))
    monkeypatch.setattr(admission, "release_by_id", lambda i: nha.append(i))
    monkeypatch.setattr(admission, "HEARTBEAT_SECONDS", nhip_s)


def test_het_tien_trien_thi_luong_nhip_TU_NHA(monkeypatch):
    nhip: list = []
    nha: list = []
    _bat_nhip(monkeypatch, nhip, nha)
    con_chay = [True]

    with admission.keep_alive("lease-1", lambda: con_chay[0]):
        time.sleep(0.25)
        n_truoc = len(nhip)
        assert n_truoc >= 1, "chua dap nhip lan nao — phep do khong cham dich"
        con_chay[0] = False            # cong viec dung lai (khach da cat)
        time.sleep(0.3)
        # ⛔ Do BEN TRONG khoi `with`: `finally` cua `keep_alive` cung nha, nen
        #    do sau khi ra khoi khoi thi khong phan biet duoc AI da nha.
        nha_trong_khoi = list(nha)
        n_sau = len(nhip)

    assert nha_trong_khoi == ["lease-1"], (
        f"luong nhip KHONG tu nha khi het tien trien: {nha_trong_khoi}. Lease se "
        "song toi khi co ai do tinh co don ho — tuc la khong bao gio.")
    assert n_sau <= n_truoc + 1, (
        f"van dap them {n_sau - n_truoc} nhip sau khi het tien trien — nhip tim "
        "con dang noi doi voi `reclaim_expired`.")


def test_DOI_CHUNG_khong_co_con_song_thi_nhip_dap_MAI(monkeypatch):
    """⛔ DOI CHUNG — day chinh xac la hanh vi CU, va la cai da lam lease bat tu.

    Khong co ve nay thi ve tren khong chung minh duoc gi: mot nhip tim von da
    tu tat sau vai luot cung se lam ve tren XANH.
    """
    nhip: list = []
    nha: list = []
    _bat_nhip(monkeypatch, nhip, nha)

    with admission.keep_alive("lease-2"):
        time.sleep(0.25)
        n = len(nhip)
        time.sleep(0.25)
        n_sau = len(nhip)
        nha_trong_khoi = list(nha)

    assert n_sau > n, "nhip khong dap — ban gia sai, ve tren vo nghia"
    assert nha_trong_khoi == [], (
        "khong truyen `con_song` ma van tu nha — lop 2 dang chay khi khong duoc "
        "yeu cau, va mot luot prefill dai hop le co the bi giet.")


def test_tran_im_lang_lay_tu_NGUON_chu_khong_phai_so_dep():
    """🔴 Luat cua chinh chuong trinh: moi nguong phai co NGUON.

    Nguon o day la `luong_vlm.mo(timeout_s=900.0)` — `httpx.Client(timeout=900)`
    dat READ timeout, tuc khoang lang HOP LE dai nhat giua hai byte tu may B.
    Dat tran THAP hon la tu giet mot luot prefill dai dang chay dung.
    """
    import inspect

    from platform_core.llm import luong_vlm

    mac_dinh = inspect.signature(luong_vlm.mo).parameters["timeout_s"].default
    assert admission.TRAN_IM_LANG_S >= mac_dinh, (
        f"TRAN_IM_LANG_S={admission.TRAN_IM_LANG_S} thap hon read timeout toi may "
        f"B ({mac_dinh}s). Mot luot prefill dai hop le se bi luong nhip giet oan.")


def test_vi_tu_cua_cua_stream_dung_DUNG_HANG_SO_AY():
    """Noi hai dau lai: cua stream phai HOI `admission.TRAN_IM_LANG_S`.

    ⚠️ Hai cho khai cung mot dieu ma khong ai bat khop — khuon nay da can du an
       nay nhieu lan. Neu `_phat` chep tay mot con so, doi hang so kia se KHONG
       doi hanh vi, va bo test van xanh rong.
    """
    import inspect

    import platform_core.runtime_noi_bo.luong as cua_luong

    ma = inspect.getsource(cua_luong)
    assert "admission.TRAN_IM_LANG_S" in ma, (
        "cua stream khong con doc `admission.TRAN_IM_LANG_S` — hang so da bi "
        "chep tay, va hai cho khai cung mot dieu lai khong ai bat khop.")
    assert "luot.luc_khoi_cuoi = time.monotonic()" in ma, (
        "khong con ai CAP NHAT `luc_khoi_cuoi` moi khoi — vi tu `con_song` se "
        "thay im lang ngay ca khi byte dang chay, va giet mot luot dang song.")

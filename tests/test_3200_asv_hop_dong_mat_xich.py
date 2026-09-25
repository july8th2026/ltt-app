"""Hop dong mat xich ASV: moi giai doan phai KHAI tien de, ma loi va phep do.

Ba bat bien cua `docs/superpowers/specs/2026-09-24-thang-cong-asv-design.md` muc 3:

    I2  `tien_quyet` khong duoc rong  (khai `("",)` khi that khong co)
    I3  moi `ma_loi` phai nam trong SO CHUNG, khong nem chuoi tu do
    I4  `do` khong duoc rong

## Vi sao `("",)` khac `()` — day la ca muc dich cua ba truong nay

🔴 Luot A 24/09 chet o `content_process` voi `auto_match_thieu_can_cu`, va
   nguyen nhan la mot TIEN DE CHUA AI KHAI: che do tu khop giong doi **nguon co
   tieng noi**. Duong that:

       `_giong_da_chot` -> `rang_giong.can_cho_ho_so` -> `ho_so_noi_dung.bao_dam`
       -> F0 doc tu `audio_prepare.outputs.f0_trung_vi` -> `cao_do.gioi_tu_f0`
       tra `""` khi F0 = 0 -> `dac_diem.co_du_de_khop` sai -> `MA_THIEU_CAN_CU`

   Mot tien de khong khai thi khong ai kiem duoc, nen no hien ra nhu mot
   **khiem khuyet** trong khi no la mot **dieu kien**.

⭐ Nen `("",)` = "buoc nay KHONG co tien de", mot cau khai duoc doc; con `()` =
   "chua ai nghi toi", va `thieu_khai()` do. Hai thu do khong duoc trung mot
   cach viet.

⛔ Va phan phan xu nhan CHUOI lam **du lieu** (`thieu_khai(chuoi=...)`), khong
   doc thang `pipeline.CHUOI`. Bai hoc N-08b: mot phep tiem vao `pipeline.py`
   that **chet o luc nap module** (`_kiem_tra_chuoi` chan phu thuoc tien), nen
   no khong bao gio toi phan phan xu — *mot doi chung that bai vi ly do KHAC
   thi khong phai mot doi chung*.
"""
from __future__ import annotations

import dataclasses

from apps.auto_scan_video import ma_loi as ML, pipeline as P

#: Khai tuong minh "khong co" — dung o ca ba truong.
RONG_TUONG_MINH = ("",)


# ══════════════════════════════════════════════════════════════════════════════
#  Task 1 — I2 + I4: ba truong phai duoc khai
# ══════════════════════════════════════════════════════════════════════════════

def test_moi_giai_doan_khai_du_ba_truong_hop_dong():
    """I2 + I4. Rong = chua ai nghi toi; xem docstring dau tep."""
    assert P.thieu_khai() == []


def test_du_13_mat_xich_va_khong_giai_doan_nao_bi_bo_ngoai_phep_kiem():
    """⛔ Mot phep kiem quet-tat-ca chet bang cach quet it hon nguoi doc tuong.

    Con so 12 la con so cua bang cong o plan `2026-09-24-thang-cong-asv.md`.

    ⭐ 12 -> 13 o b4 (25/09): `IMAGE_FINISH` — GIAI DOAN 2, thao tac hinh anh
       tren MP4 da xong. Xem `docs/superpowers/plans/2026-09-25-asv-hai-giai-doan.md`.
    """
    assert len(P.CHUOI) == 13, [g.ten for g in P.CHUOI]
    assert len(P.TEN_GIAI_DOAN) == len(set(P.TEN_GIAI_DOAN))


def test_phan_xu_BAT_DUOC_o_RONG__doi_chung_tren_chuoi_TONG_HOP():
    """⛔ DOI CHUNG cua I2/I4, tren mot chuoi TONG HOP chu khong tren `CHUOI` that.

    🔴 Vi sao khong tiem vao `pipeline.py`: `_kiem_tra_chuoi()` chay o cap module,
       nen mot phep tiem sai cau truc chet luc **import** va khong bao gio toi
       `thieu_khai`. Nhan chuoi lam du lieu thi tiem duoc that.
    """
    day = P.GiaiDoan("day_du", "a", "a.x", tien_quyet=("x",), ma_loi=("y",),
                     do=("z",))
    assert P.thieu_khai(chuoi=(day,)) == []

    # `("",)` la mot cau KHAI -> khong thieu.
    tuong_minh = dataclasses.replace(day, ten="tuong_minh",
                                     tien_quyet=RONG_TUONG_MINH,
                                     ma_loi=RONG_TUONG_MINH, do=RONG_TUONG_MINH)
    assert P.thieu_khai(chuoi=(tuong_minh,)) == []

    # `()` la CHUA AI NGHI TOI -> phai do, va phai noi ro thieu truong nao.
    for truong in ("tien_quyet", "ma_loi", "do"):
        hong = dataclasses.replace(day, ten="hong", **{truong: ()})
        assert P.thieu_khai(chuoi=(hong,)) == [f"hong: thieu {truong}"], truong

    # Thieu ca ba -> liet ke ca ba, khong dung o cai dau tien.
    tron = dataclasses.replace(day, ten="tron", tien_quyet=(), ma_loi=(), do=())
    assert P.thieu_khai(chuoi=(tron,)) == ["tron: thieu tien_quyet",
                                           "tron: thieu ma_loi",
                                           "tron: thieu do"]


def test_tien_quyet_cua_content_process_NOI_RA_dieu_da_lam_chet_luot_A():
    """🔴 Bat bien co noi dung, khong chi co hinh thuc.

    Neu ai do thay dong `tien_quyet` cua `content_process` bang mot cau chung
    chung thi bai nay do — vi con so duy nhat bien ba truong nay tu mot cai form
    thanh mot cai chot la: no co ghi lai ca NGUYEN NHAN THAT khong.
    """
    tq = " | ".join(P.THEO_TEN[P.CONTENT_PROCESS].tien_quyet).lower()
    assert "f0" in tq and "tieng noi" in tq, tq


# ══════════════════════════════════════════════════════════════════════════════
#  Task 2 — I3: so ma loi chung
# ══════════════════════════════════════════════════════════════════════════════

def test_moi_ma_loi_khai_o_giai_doan_deu_co_trong_SO_MA():
    """I3: ⛔ khong nem chuoi tu do.

    🔴 G-04 (do 24/09): cau `rang_giong.vi_sao_chua_rang` dung lai o cot `error`,
       man khach doc `outputs.ma_loi` ⇒ khach nhan mot cau chung chung KEM mot
       nut "Thu lai buoc nay" CHAC CHAN HONG. Mot ma loi khong co cau tuong ung
       la mot cua loi noi doi.
    """
    thieu = [(g.ten, m) for g in P.CHUOI for m in g.ma_loi
             if m and m not in ML.SO_MA]
    assert thieu == [], f"ma khong co cau khach doc duoc: {thieu}"


# ⭐ **`test_moi_ma_trong_SO_MA_deu_khai_chinh_sach_credit` da bi XOA cung
#    `ma_loi.HOAN_CREDIT` — 25/09/2026, gia phang.**
#
#    No chot rang moi ma loi phai khai *"credit co hoan hay khong"*. Duoi gia
#    phang cau hoi ay khong con: tien chi duoc thu khi lan chay ve `done` VA co
#    hien vat giao duoc, nen **moi** ket cuc khac hoan 100 % — khong ma nao
#    khai gi, va khong co gi de lech.
#
# ⛔ Giu lai phep kiem se la giu mot banh coc gac mot **nghia vu ma**: no van
#    xanh, van ton mot luot chay, va van lam nguoi doc tuong co mot duong hoan
#    tien theo ma dang song. `tests/test_3900_asv_gia_phang.py` chot luat that.


def test_SO_MA_KHONG_la_ban_thu_hai_cua_LOI_CO_MA():
    """⛔ Hai cho khai cung mot dieu thi lech am tham — kho nay dinh 3 lan / 2 ngay.

    `quan_sat.LOI_CO_MA` da co truoc. `SO_MA` khong duoc CHEP cau tu no: no phai
    **tro toi** chinh doi tuong do, nen phep kiem so bang `is`, khong so `==`.
    """
    from apps.auto_scan_video import quan_sat

    assert set(quan_sat.LOI_CO_MA) <= set(ML.SO_MA), sorted(
        set(quan_sat.LOI_CO_MA) - set(ML.SO_MA))
    for ma, cau in quan_sat.LOI_CO_MA.items():
        assert ML.SO_MA[ma] is cau, (
            f"{ma}: `SO_MA` giu mot BAN SAO cua cau, khong phai chinh cau cua "
            f"`LOI_CO_MA`. Hai ban se lech.")


def test_SO_MA_khong_chua_ma_nao_khong_he_duoc_nem():
    """⛔ Mot so ma phinh ra vi nguoi ta them ma "cho tuong lai" thi khong con la
    mot ban kiem ke — no thanh mot ban uoc. Moi ma phai co mot giai doan khai no.
    """
    da_khai = {m for g in P.CHUOI for m in g.ma_loi if m}
    assert set(ML.SO_MA) == da_khai, sorted(set(ML.SO_MA) ^ da_khai)


def test_CHI_HAI_mat_xich_co_ma_on_dinh__ghi_lai_HIEN_TRANG():
    """⚠️ MO TA hien trang, khong phai mot bat bien. ⛔ Bai nay KHONG doi sua.

    🔴 Va day la phat hien dat gia cua Task 2: grep ca kho, **mot cho duy nhat**
       nem ngoai le mang `ma_loi=` (`giai_doan_noi_dung.py:142`), cong mot cho
       gian tiep (`giong_noi.py:184` nem lai `GiongKhongHopLe(ma_loi=exc.ma)`,
       chay trong `voice_synthesis`). `thi_hanh.py:565` la nguoi doc duy nhat.

    ⇒ Tuc **10 tren 12** mat xich hong bang chuoi TU DO: `outputs.ma_loi` cua
      chung luon rong, nen G-04 khong phai mot ca le o `content_process` — no la
      hien trang cua ca chuoi. Bai nay bien cau do thanh mot con so DO DUOC.

    ⭐ Ai them ma on dinh cho mot buoc ⇒ bai nay do ⇒ cap nhat con so o day, va
      luc do viec do la mot viec TOT chu khong phai mot hoi quy.
    """
    co_ma = sorted(g.ten for g in P.CHUOI if tuple(g.ma_loi) != RONG_TUONG_MINH)
    assert co_ma == sorted([P.CONTENT_PROCESS, P.VOICE_SYNTHESIS]), co_ma


def test_moi_THAM_CHIEU_trong_tien_quyet_tro_toi_mot_DONG_CO_THAT():
    """⛔ Mot `tep.py:123` tro sai la mot loi nho ma te: no **trong nhu** da duoc
    doi chieu, va nguoi doc sau se tin no.

    🔴 Da xay ra that trong chinh luot nay: ban khai dau tien lay so dong tu ban
       Read (co offset docstring) chu khong tu `grep`, va **9 tham chieu tro lech
       5-20 dong** — mot cai tro vao `thu_muc = Path(tam)` trong khi no dang noi
       ve `if not run.source_key`.

    ⚠️ Bai nay chi chot dong CO TON TAI, ⛔ khong chot no dung NGHIA. No cat duoc
       loai lech re nhat (tep bi rut ngan, tham chieu vuot cuoi tep), khong hon.
    """
    import pathlib
    import re

    goc = pathlib.Path(P.__file__).parent
    hong: list[str] = []
    for g in P.CHUOI:
        for cau in g.tien_quyet:
            for tep, so in re.findall(r"([a-z0-9_]+\.py):([\d,]+)", cau):
                duong = goc / tep
                if not duong.is_file():
                    hong.append(f"{g.ten}: khong co tep {tep}")
                    continue
                tong = len(duong.read_text(encoding="utf-8").splitlines())
                for n in (int(x) for x in so.split(",") if x):
                    if not 1 <= n <= tong:
                        hong.append(f"{g.ten}: {tep}:{n} ngoai tep ({tong} dong)")
    assert hong == [], hong

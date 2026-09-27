"""LAN D — `edit_plan` (giai doan 2): DUNG TRUC, va BAN KHAI khong noi doi.

Ba nhom, ba lop loi khac nhau, ca ba do tren ma VAN HANH:

  §1  TRUC        `edit_plan` do/tach canh tren tep NAO, va `image_finish` cat
                  tep NAO. Hai tep khac nhau ⇒ cat sai cho, im lang.
  §2  BAN KHAI    thong diep ra cho KHACH khong duoc khai mot nguyen nhan ma no
                  ⛔ khong biet (cung lop voi `"VLM de xuat bo"`, `123285ae`).
  §3  CHU THICH   ly le bien minh cho mot bat bien phai con dung sau khi thu tu
                  chuoi doi — mot ly le sai lam nguoi sau sua sai chieu.
"""
from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import (  # noqa: E402
    bien_tap as bt_mod, giai_doan_ban_bien_tap as gdbbt, hop_dong_v4, ke_cat,
    nhap_media, pipeline as P)


# ── Ban gia toi thieu: mot `db` chi tra loi duoc `giai_doan_theo_ten` ─────────

class _Stage:
    def __init__(self, outputs: dict) -> None:
        self.outputs = outputs


class _DbGia:
    """`features.giai_doan_theo_ten` doc qua `db.execute(...)`, nen ta thay
    THANG `features.giai_doan_theo_ten` o tung bai thay vi gia ca ORM."""


class _Run:
    id = "run-4870"
    owner_id = "u-4870"
    source_key = "asv/u-4870/nguon/goc.mp4"


class _KhoGia:
    """`local_path` co san — dung `LocalStorage`, tuc kenh CUC BO."""

    def local_path(self, khoa: str) -> str:
        return f"D:/kho/{khoa}"


def _cai_stage(monkeypatch, theo_ten: dict) -> None:
    from apps.auto_scan_video import features

    monkeypatch.setattr(
        features, "giai_doan_theo_ten",
        lambda db, run_id, ten: theo_ten.get(ten))


# ══════════════════════════════════════════════════════════════════════════════
#  §1  MOT TEP, MOT TRUC
# ══════════════════════════════════════════════════════════════════════════════

KHOA_RENDER = "asv/u-4870/render/abc.mp4"


def test_edit_plan_do_tren_BAN_RA_CUA_RENDER_chu_khong_phai_ban_GOC(monkeypatch):
    """🔴 `image_finish` cat **ban ra cua `render`** (`_khoa_theo_duoi(...RENDER,
    ".mp4")`). Neu `edit_plan` do va tach canh tren ban GOC thi quyet dinh cua no
    nam tren mot truc thoi gian khac voi truc no se duoc thi hanh.

    ⛔ Va day ⛔ khong phai mot lo ngai ly thuyet — xem bai ke tiep: `toc_do` la
       mot tinh nang CHI bat duoc tren dung preset nay.
    """
    _cai_stage(monkeypatch, {
        P.MEDIA_PREPARE: _Stage({"thoi_luong": 100.0,
                                 "khoa_asset": ["asv/u/mp/audio_full.wav"]}),
        P.RENDER: _Stage({"khoa_asset": [KHOA_RENDER]}),
    })
    khoa = gdbbt._khoa_hinh(_DbGia(), _Run())
    assert khoa == KHOA_RENDER, (
        f"edit_plan do tren {khoa!r} nhung image_finish cat {KHOA_RENDER!r} — "
        f"hai truc thoi gian khac nhau")
    assert khoa != _Run.source_key


def test_thieu_ban_ra_RENDER_thi_NEM_chu_khong_LUI_VE_ban_goc(monkeypatch):
    """⛔ Doi chung: mot duong lui im lang ve ban goc CHINH LA con bug tren, chi
    la kho tim hon. Thieu thuong nguon phai la mot loi CO TEN."""
    _cai_stage(monkeypatch, {
        P.MEDIA_PREPARE: _Stage({"thoi_luong": 100.0}),
        P.RENDER: _Stage({"khoa_asset": ["asv/u/render/khong-phai-video.json"]}),
    })
    with pytest.raises(gdbbt.ThieuChiMuc):
        gdbbt._khoa_hinh(_DbGia(), _Run())


def test_do_dai_DO_TU_TEP_chu_khong_tu_ban_khai_cua_media_prepare(monkeypatch):
    """🔴 `toc_do` lam hai con so LECH — va ban khai thuong nguon la con so SAI.

    `media_prepare` khai do dai **NGUON**. `render` ap `setpts=PTS/toc_do` nen
    ban ra ngan hon dung he so do (`bien_tap.moc_ban_ra`). Lay do dai tu ban khai
    la lay do dai cua mot tep khac voi tep dang do.
    """
    _cai_stage(monkeypatch, {
        P.MEDIA_PREPARE: _Stage({"thoi_luong": 100.0}),
        P.RENDER: _Stage({"khoa_asset": [KHOA_RENDER]}),
    })
    # ⭐ 100 s nguon o `toc_do = 1,25` ra 80 s — con so nay la cua `bien_tap`,
    #    ⛔ khong go tay.
    dai_ban_ra = bt_mod.moc_ban_ra(100.0, {"toc_do": 1.25})
    assert dai_ban_ra == pytest.approx(80.0)
    monkeypatch.setattr(nhap_media, "soi",
                        lambda duong, **kw: {"thoi_luong": dai_ban_ra})

    duong, tl = gdbbt._nguon_do_hinh(_DbGia(), _KhoGia(), _Run())
    assert KHOA_RENDER in duong
    assert tl == pytest.approx(dai_ban_ra), (
        f"edit_plan tach canh tren truc {tl} s nhung tep that dai "
        f"{dai_ban_ra} s")


def test_CAI_GIA_cua_truc_lech__ke_cat_NEM_hay_cat_SAI_CHO():
    """⛔ Doi chung cho §1: cho thay cai gia, ⛔ khong chi cho thay luat.

    Mot canh cua NGUON nam ngoai do dai BAN GIAO ⇒ `ke_cat.kiem` nem. Mot canh
    nam trong thi ⛔ khong ai nem gi ca — no chi bi cat **lech 20 %**, va do la
    the loai hong dat hon.
    """
    # (a) canh cuoi cua nguon 100 s roi ra ngoai ban giao 80 s ⇒ NEM.
    with pytest.raises(ke_cat.KeCatError):
        ke_cat.chon([ke_cat.UngVien(bat=90.0, ket=93.0, diem_kem=0.9)],
                    thoi_luong=80.0)
    # (b) canh giua thi KHONG nem — ta cat 20,0..23,0 cua ban giao trong khi
    #     canh kem THAT SU o 16,0..18,4 (= 20/1,25 .. 23/1,25). Im lang.
    ke = ke_cat.chon([ke_cat.UngVien(bat=20.0, ket=23.0, diem_kem=0.9)],
                     thoi_luong=80.0)
    assert ke.co_cat and ke.cat == ((20.0, 23.0),)
    dung = (20.0 / 1.25, 23.0 / 1.25)
    assert ke.cat[0] != dung, "neu hai truc trung nhau thi bai nay vo nghia"


def test_khai_thuong_nguon_DOC_DUOC_bang_banh_coc_pipeline():
    """🔴 `test_3004` do *"khai `sau=` phai phu thu that su doc"* bang cach tim
    `pipeline.X` trong AST cua module. Module nay tung doc thuong nguon bang
    **chuoi van ban** (`"media_prepare"`, `"transcribe"`) ⇒ banh coc do duoc
    **RONG** cho ca giai doan, va mot phep kiem rong thi xanh mai mai.
    """
    ra: set[str] = set()
    for n in ast.walk(ast.parse(inspect.getsource(gdbbt))):
        if (isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
                and n.value.id == "pipeline" and n.attr.isupper()):
            gt = getattr(P, n.attr, None)
            if isinstance(gt, str) and gt in P.TEN_GIAI_DOAN:
                ra.add(gt)
    for can in (P.MEDIA_PREPARE, P.TRANSCRIBE, P.RENDER):
        assert can in ra, (
            f"`{can}` duoc doc bang chuoi van ban chu khong qua `pipeline.*` — "
            f"banh coc test_3004 ⛔ khong thay lan doc nay. Thay duoc: "
            f"{sorted(ra)}")
    # ⛔ Va `sau=` phai thuc su phu chung, neu khong thi day la mot vi pham that.
    assert P.THEO_TEN[P.EDIT_PLAN].sau == (P.RENDER,)


def test_MOT_TRUC__ban_chep_loi_va_canh_KHONG_con_phep_doi_nao():
    """🔴 **B6 (27/09): ba phep doi truc o day BI XOA, ⛔ khong bi sua.**

    Truoc B6: `render` (GD1) ap `setpts=PTS/toc` **roi** `image_finish` (GD2) cat
    tren tep da doi toc. Nen `ci.canh` (tach tu ban ra cua `render`) o truc SAU
    `toc_do`, con `ban_ghi` cua `transcribe` (chay tren `audio_full.wav` cua
    NGUON) o truc NGUON. Hoi *"canh nay co thoai khong"* bang hai truc khac nhau
    la cach mot canh CO tieng bi doc thanh *"khong thoai"* ⇒ ha nguong ⇒ thanh
    ung vien cat ⇒ **mot cau thoai bi cat giua cau**.

    Ban va cu: mot ham `_ban_ghi_truc_ban_giao` doi moc bang tay. Ban va B6: doi
    TRUC DI — `toc_do` ap o cuoi GD2, nen hai ve cua phep so **cung mot truc** va
    ⛔ khong con gi de doi.

    ⭐ Bai nay chot dieu MANH hon ban cu: su lech truc ⛔ khong con **co the xay
       ra**, ⛔ khong phai "da duoc sua dung". Do la khac biet giua mot bat bien
       cau truc va mot phep tinh dung.
    """
    from apps.auto_scan_video import (ban_bien_tap as bbt,
                                      giai_doan_hinh_anh as gdha)

    # (a) ⛔ Ham doi truc ⛔ KHONG con ton tai — o ca hai noi no tung o.
    assert not hasattr(gdbbt, "_ban_ghi_truc_ban_giao"), (
        "phep doi truc ban chep loi con song ⇒ no dang doi mot truc ma GD1 ⛔ "
        "khong con tao ra, tuc dang lam SAI")
    assert not hasattr(gdha, "_khe_thoai_truc_ban_giao"), (
        "phep doi truc khe thoai con song ⇒ nhu tren")

    # (b) Va cung mot truc thi phep so tra dung ma ⛔ khong ai doi gi: cau thoai
    #     o nguon [20 s, 25 s), canh nguon [20 s, 25 s) ⇒ CO thoai.
    goc = {"doan": [{"bat": 20.0, "ket": 25.0, "chu": "mot cau thoai"}]}
    assert bbt._co_thoai(goc, 20.0, 25.0)
    assert not bbt._co_thoai(goc, 30.0, 35.0)


def test_MOT_TRUC__ke_cat_KHONG_con_nhan_bien_tap_nen_KHONG_THE_lech():
    """🔴 **Bat bien cau truc: `_ke_cat` ⛔ khong con tham so `bien_tap`.**

    Truoc B6 no phai nhan ho so DAY DU cua khach chi de doi truc khe thoai. Mot
    tham so nhu the la mot cho co the truyen SAI (hay quen truyen) — va lich su
    cua tep nay chinh la mot lan quen. Nay tham so ⛔ khong ton tai, nen loi ay
    ⛔ khong the tai dien.

    ⚠️ Chot bang `inspect.signature`, ⛔ khong bang chuoi: mot chu thich nhac ten
       `bien_tap` la hop le va ⛔ khong phai loi.
    """
    import inspect

    from apps.auto_scan_video import giai_doan_hinh_anh as gdha

    ts = inspect.signature(gdha._ke_cat).parameters
    assert "bien_tap" not in ts, (
        "`_ke_cat` con nhan `bien_tap` ⇒ van con mot truc thu hai de lech: %s"
        % list(ts))
    assert "thoi_luong" in ts


def test_MOT_TRUC__cong_khong_cat_vao_tieng_chan_dung_tren_truc_NGUON():
    """⭐ **`ke_cat.co_thoai` la cong CUNG** thuc thi *"CHI cat vung KHONG co loi
    thoai"* (chu du an chot). Bai nay do cong ay **tren truc thuc te**.

    Sau B6 `timing_align` va ung vien cat cung o truc NGUON, nen mot cau thoai
    dat tai 25 s ke hoach THAT SU o 25 s cua tep ma GD2 cat:

      · ung vien [25 s, 27 s) **chong lan** ⇒ cong phai CHAN;
      · ung vien [20 s, 23 s) ⛔ khong chong ⇒ cong phai CHO QUA.

    🔴 Truoc B6, ve thu hai la cho con bug nam: khe thoai bi doi ve 20 s nen cong
       CHAN mot ung vien hoan toan hop le — tuc ⛔ khong chi cat sai, ma con **bo
       sot** nhung cho dang cat. Mot phep doi truc sai hong theo CA HAI chieu.
    """
    ke_hoach = {"doan": [{"dat_tai_ms": 25_000, "dai_ms": 3_000}]}
    khe = ke_cat.khe_thoai_tu_ke_hoach(ke_hoach)
    assert khe == ((25.0, 28.0),), khe

    assert ke_cat.co_thoai(khe, 25.0, 27.0), "chong lan thoai ma cong CHO QUA"
    assert not ke_cat.co_thoai(khe, 20.0, 23.0), (
        "⛔ khong chong lan ma cong CHAN — day la chieu hong THU HAI cua mot "
        "phep doi truc sai: bo sot cho dang cat")

    # ⭐ Va cai gia the hien o dau ra cua `ke_cat.chon`, ⛔ chi o ham tren.
    uv_cham = [ke_cat.UngVien(bat=25.0, ket=27.0, diem_kem=0.9)]
    ke = ke_cat.chon(uv_cham, thoai=khe, thoi_luong=80.0)
    assert not ke.co_cat
    assert [b["ly_do"] for b in ke.bo_qua] == [ke_cat.LY_DO_CO_THOAI]

    uv_sach = [ke_cat.UngVien(bat=20.0, ket=23.0, diem_kem=0.9)]
    assert ke_cat.chon(uv_sach, thoai=khe, thoi_luong=80.0).co_cat


# ══════════════════════════════════════════════════════════════════════════════
#  §2  BAN KHAI: ⛔ khong khai mot nguyen nhan minh khong biet
# ══════════════════════════════════════════════════════════════════════════════

class _Canh:
    def __init__(self, ma: str, bat: float, ket: float) -> None:
        self.ma, self.bat, self.ket = ma, bat, ket
        self.khung = ()


class _ChiMuc:
    def __init__(self, n: int) -> None:
        self.canh = tuple(_Canh(f"canh_{i:04d}", float(i - 1), float(i))
                          for i in range(1, n + 1))
        self.thoi_luong = float(n)


def test_THIEU_BAN_CHEP_LOI_khong_duoc_khai_la_khong_doc_duoc_HINH():
    """🔴 Cung lop voi `"VLM de xuat bo"`: mot cau di ra **cho khach** khai mot
    nguyen nhan ma ma ⛔ khong he biet.

    `_do_cac_canh` tra `loai = "thieu_ban_chep_loi"` khi ban ghi rong — hinh doc
    duoc hoan toan, thu thieu la BAN CHEP LOI. Cau cu ghi *"Không đọc được hình
    của 3/3 cảnh"*: dung con so, sai nguyen nhan, va sai ca loi khuyen.
    """
    ci = _ChiMuc(3)
    hong = [{"ma_canh": c.ma, "loai": "thieu_ban_chep_loi"} for c in ci.canh]
    with pytest.raises(gdbbt.ThieuBangChungCanh) as e:
        gdbbt._chot_do_phu(hop_dong_v4.PRESET_CAT_THONG_MINH, ci, (), hong)
    van = str(e.value)
    assert "chép lời" in van, f"khong noi ra nguyen nhan THAT: {van!r}"
    assert "đọc được hình" not in van and "đo được hình" not in van, (
        f"khai mot nguyen nhan no khong biet: {van!r}")


def test_KHONG_DO_DUOC_HINH_van_noi_dung_ve_HINH():
    """⛔ Doi chung: neu cau moi noi ve ban chep loi cho MOI ca thi ta chi doi
    mot ban khai sai bang mot ban khai sai khac."""
    ci = _ChiMuc(2)
    hong = [{"ma_canh": c.ma, "loai": "khong_do_duoc_hinh"} for c in ci.canh]
    with pytest.raises(gdbbt.ThieuBangChungCanh) as e:
        gdbbt._chot_do_phu(hop_dong_v4.PRESET_CAT_THONG_MINH, ci, (), hong)
    van = str(e.value)
    assert "hình" in van and "chép lời" not in van, van


def test_TRON_nhieu_loai_hong_thi_LIET_KE_chu_khong_chon_mot_cai():
    """⭐ Khi ⛔ khong biet nguyen nhan duy nhat thi phai NOI RA la khong biet —
    ⛔ khong duoc chon bua mot trong hai va khai nhu chac chan."""
    ci = _ChiMuc(2)
    hong = [{"ma_canh": "canh_0001", "loai": "thieu_ban_chep_loi"},
            {"ma_canh": "canh_0002", "loai": "khong_do_duoc_hinh"}]
    with pytest.raises(gdbbt.ThieuBangChungCanh) as e:
        gdbbt._chot_do_phu(hop_dong_v4.PRESET_CAT_THONG_MINH, ci, (), hong)
    van = str(e.value)
    for loai in ("thieu_ban_chep_loi", "khong_do_duoc_hinh"):
        assert loai in van, f"{loai} bi giau: {van!r}"


# ══════════════════════════════════════════════════════════════════════════════
#  §3  CHU THICH: ly le bien minh phai con dung sau khi thu tu chuoi doi
# ══════════════════════════════════════════════════════════════════════════════

def test_edit_plan_chay_SAU_cac_buoc_DAT_TIEN__nen_ly_le_re_tien_la_SAI():
    """🔴 `PHU_BANG_CHUNG_TOI_THIEU` bien minh cho mot loi NEM khong-thu-lai bang
    cau *"`edit_plan` chay TRUOC `content_process` va `voice_synthesis` nen mot
    lan tu choi tra lai cho khach ca doan dat nhat cua chuoi"*.

    ⛔ Tu 26/09 no chay `sau=(RENDER,)` — SAU dich, SAU TTS, SAU tron, SAU ket
       xuat. Nem o day ⛔ khong tiet kiem mot giay nao. Bat bien 1,0 co the van
       dung, nhung ly le thi da nguoc, va mot ly le nguoc lam nguoi sua sau can
       nhac sai chieu.

    ⚠️ **Ban sua chu thich KHONG co phep kiem do, va do la mot su that phai noi
       ra.** Ban dau bai nay quet chuoi "chay TRUOC content_process" trong ma
       nguon; nhung mot ghi chu SUA SAI phai duoc phep **trich lai** cau sai de
       giai thich, nen phep quet do bao dong ngay tren ban DA sua — dung lop
       `banh-coc-do-cach-go` ma kho da ghi so. ⇒ O day chi chot **tinh chat do
       duoc** (thu tu chuoi); cau chu thich thi chi nguoi doc kiem duoc.
    """
    thu_tu = {g: i for i, g in enumerate(P.TEN_GIAI_DOAN)}
    for dat_tien in (P.CONTENT_PROCESS, P.VOICE_SYNTHESIS, P.RENDER):
        assert thu_tu[P.EDIT_PLAN] > thu_tu[dat_tien], (
            f"{dat_tien} phai dung TRUOC edit_plan trong CHUOI")


def test_ly_do_KHONG_THU_LAI_khong_duoc_vien_mot_co_che_DA_BI_XOA():
    """🔴 Ly do cu: *"lan hoi lai da xay ra roi, ngay trong giai doan
    (`SO_LAN_DOC_CANH`)"*. `SO_LAN_DOC_CANH` chet cung VLM (Task 22) — mot ly le
    vien den mot co che ⛔ khong con ton tai la mot ly le ⛔ khong ai kiem duoc.

    ⭐ Chot bang **su vang mat cua co che**, ⛔ khong bang su vang mat cua mot
       chuoi ky tu (xem canh bao o bai tren): ngay nao co nguoi them lai mot vong
       hoi lai trong giai doan nay thi bai nay do va ly le kia song lai.
    """
    assert not hasattr(gdbbt, "SO_LAN_DOC_CANH"), (
        "co che hoi lai trong giai doan da song lai — doc lai ly le "
        "KHONG-THU-LAI cua `PHU_BANG_CHUNG_TOI_THIEU`")
    assert not hasattr(gdbbt, "LO_DOC_CANH")

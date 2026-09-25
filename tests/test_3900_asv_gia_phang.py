"""Auto Scan Video — GIA PHANG: `10 credit x so phut video nguon` (25/09/2026).

Chu du an chot, nguyen van:

  > *"ta tam thoi bo qua xay dung. ta cu dat tinh chi phi theo phut video xu ly.
  >  dat tam la 10 credit / 1 phut video. cho gon thay vi combenh cac buoc phuc
  >  tap. ta an dinh nhu the."*

Tep nay chot **bon quyet dinh** di kem con so, va chot chung o cho chung that su
duoc thi hanh — ⛔ khong chot mot bang tai lieu:

  A. Lam tron LEN theo phut bat dau, toi thieu 1 phut — VA luat lam tron duoc
     noi ra TRUOC khi khach bam
  B. Tinh theo do dai NGUON, ⛔ khong theo ban ra
  C. Giu cho khi tao run, thu that khi `done`
  D. 🔴 Khong giao duoc thi KHONG thu (`N-21`) — ke ca `cancelled`

  E. Va mot nhom ve **cau truc**: MOT cho khai, MOT cho tinh

⚠️ Vi sao khong dung con so `10` trong ky vong o duoi: mot phep kiem go lai `10`
   la **ban khai thu ba** cua cung mot con so (sau `gia.py` va sau hoa don), va no
   se troi khoi hai ban kia. Moi ky vong o day dan xuat tu
   `gia.GIA_CREDIT_MOI_PHUT`. ⭐ Ngoai le **co chu dinh**: `test_LAM_TRON_len_theo
   _phut_bat_dau` go tay so phut (1, 1, 2, 4) — do la **luat**, khong phai gia,
   va mot phep kiem lam tron tinh lai phep lam tron thi khong do gi.
"""
from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

import pytest

from apps.auto_scan_video import features, gia, pipeline, quan_sat
from apps.auto_scan_video.tables import (RUN_CANCELLED, RUN_DONE, RUN_ERROR,
                                         AsvRun)

#: Do dai cua fixture video. ⛔ Nhap vao chu khong go lai: fixture doi do dai thi
#: moi ky vong o day doi theo, va ⛔ khong mot con so nao o day tro thanh moc chet.
from tests.fixtures.asv_media import DEFAULT_DURATION_S
from tests.rao_chan_nang import demucs_gia_lap  # noqa: F401  (autouse: chan demucs that)
from tests import test_402_asv_mach_doc_gia as _t402

GOC = Path(__file__).resolve().parents[1]
APP = GOC / "apps" / "auto_scan_video"

# ⭐ Gan ten chu khong `from ... import`: mot fixture nhap vao bang `import` la mot
#    F401 (no khong duoc goi o dau trong tep), va kho nay dem F401 bang banh coc.
db = _t402.db
kho_tam = _t402.kho_tam
asr_gia = _t402.asr_gia
dich_gia = _t402.dich_gia
giong_gia = _t402.giong_gia
_tao_run = _t402._tao_run
_chay_het_hang_doi = _t402._chay_het_hang_doi


# ══════════════════════════════════════════════════════════════════════════════
#  A. Lam tron LEN, toi thieu 1 phut — va khach BIET luat do truoc khi bam
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("giay, phut", [
    (0.0, 1),        # ⛔ San toi thieu: mot lan chay van la mot lan chay
    (1.0, 1),
    (59.0, 1),
    (60.0, 1),       # ⭐ Dung 1 phut la 1 phut, ⛔ khong phai 2
    (61.0, 2),       # ⭐ Hon 1 giay la sang phut thu hai
    (190.0, 4),      # 3 ph 10 s -> 4 phut (vi du chu du an neu ra)
    (600.0, 10),
    (601.0, 11),
])
def test_LAM_TRON_len_theo_phut_bat_dau(giay, phut):
    """⭐ Lam tron LEN chu ⛔ khong lam tron GAN, va do la mot quyet dinh ve LONG
       TIN: khach tu nhan lai duoc con so tu do dai video ho dang nhin.

    ⚠️ Lam tron gan cho ra mot con so ho **phai tin** thay vi kiem: 190 giay lam
       tron gan la 3 phut, va khong co cach nao tu 190 va "3" doan ra duoc luat.
    """
    assert gia.so_phut_tinh_tien(giay) == phut


def test_tinh_credit_la_SO_PHUT_nhan_DON_GIA_khong_gi_khac():
    """⛔ Khong co san, khong co bac, khong co he so an — mot phep nhan."""
    for giay in (0.0, 1.0, 59.0, 60.0, 61.0, 190.0, 3600.0, 7325.0):
        assert gia.tinh_credit(giay) == (
            gia.so_phut_tinh_tien(giay) * gia.GIA_CREDIT_MOI_PHUT)


def test_vi_du_cua_chu_du_an_3ph10s_ra_40_credit():
    """🔑 Mot phep kiem doc len thanh cau chu du an da noi.

    ⛔ `40` KHONG go tay: neu don gia doi thi con so ky vong doi theo, va bai nay
       van con y nghia thay vi thanh mot moc chet phai sua bang tay.
    """
    assert gia.tinh_credit(3 * 60 + 10) == 4 * gia.GIA_CREDIT_MOI_PHUT


def test_KHONG_bao_gio_thu_0_credit_cho_mot_lan_chay():
    """San toi thieu 1 phut nghia la gia luon > 0. Mot lan chay 0 credit la mot
    lan chay khong co ai dong y tra tien, va no se di qua moi cong ngan sach."""
    for giay in (0.0, -5.0, 0.4, None):
        assert gia.tinh_credit(giay) > 0                 # type: ignore[arg-type]


def test_XEM_TRUOC_mang_luat_lam_tron_VA_don_gia_that():
    """🔴 Chu du an chot: *"phai hien cho khach thay luat lam tron truoc khi ho
       bam — mot con so nhay ra sau khi tru tien la cach nhanh nhat de mat long
       tin."*

    ⭐ Nen bai nay ⛔ khong chi kiem "co truong `luat_lam_tron`": no kiem cau do
       **noi dung don gia that** va **noi ra viec lam tron len**. Mot truong
       rong, hay mot cau con `{don_gia}` chua dien, deu lot qua mot phep kiem
       `in` don thuan.
    """
    xem = gia.xem_truoc_chi_phi(190.0)
    cau = xem["luat_lam_tron"]

    assert cau and "{" not in cau, f"cau chua duoc dien tham so: {cau!r}"
    assert str(gia.GIA_CREDIT_MOI_PHUT) in cau, cau
    assert "tròn lên" in cau, cau
    # Va con so di kem phai la con so THAT, khong phai mot uoc quanh no.
    assert xem["credit"] == gia.tinh_credit(190.0)
    assert xem["so_phut"] == 4 and xem["don_gia"] == gia.GIA_CREDIT_MOI_PHUT


def test_xem_truoc_KHONG_con_tra_ve_mot_KHOANG():
    """⭐ Gia phang la mot con so CHINH XAC. Mot "khoang" quanh mot con so chinh
       xac la mot khoang bia ra, va no lam khach chuan bi cho mot so khong bao gio
       xay ra."""
    assert not hasattr(gia, "uoc_khoang"), "khoang uoc cu con song"
    assert not hasattr(gia, "BIEN_DO_UOC")
    assert not hasattr(gia, "uoc_credit"), "cong thuc cu con song canh cong thuc moi"


# ══════════════════════════════════════════════════════════════════════════════
#  B. Do dai NGUON, ⛔ khong do dai BAN RA
# ══════════════════════════════════════════════════════════════════════════════

def test_do_dai_lay_tu_MEDIA_PREPARE_chu_khong_tu_ban_RA(db, kho_tam, tmp_path,
                                                         asr_gia, dich_gia,
                                                         giong_gia):
    """🔑 `media_prepare` soi **tep nguon**; `render` sinh ban ra. Preset "Rut gon
       co bien tap" lam ban ra ngan hon, va khach ⛔ khong duoc thuong cung ⛔ khong
       bi phat vi may cat bao nhieu."""
    run = _tao_run(db, giu=gia.tinh_credit(DEFAULT_DURATION_S),
                   kho=None, tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc={"api", "ffmpeg", "gpu", "voice"})
    db.expire_all()
    run = db.get(AsvRun, run.id)

    giay, nguon_do = features.thoi_luong_nguon_giay(db, run)
    assert nguon_do == features.DO_TU_MACH
    assert giay == pytest.approx(DEFAULT_DURATION_S, abs=0.5)

    # Va con so do dung la con so `media_prepare` da ghi — ⛔ khong mot ban sao.
    gd = features.giai_doan_theo_ten(db, run.id, pipeline.MEDIA_PREPARE)
    assert float((gd.outputs or {})["thoi_luong"]) == giay


def test_CHUA_DO_duoc_do_dai_thi_KHONG_tra_ve_0_lang_le(db, kho_tam):
    """⛔ `0.0` mot minh ⛔ khong phan biet duoc *"video dai 0 giay"* voi *"chua do
       duoc"*. Tien la cho tuyet doi ⛔ khong duoc gop hai trang thai vao mot gia
       tri — kho nay co ca mot ho loi ve viec do."""
    run = _tao_run(db, giu=10)          # chua chay giai doan nao
    giay, nguon_do = features.thoi_luong_nguon_giay(db, run)
    assert (giay, nguon_do) == (0.0, features.CHUA_DO)
    assert features.CHUA_DO != features.DO_TU_MACH


# ══════════════════════════════════════════════════════════════════════════════
#  C. Giu cho khi tao run, thu that khi `done`
# ══════════════════════════════════════════════════════════════════════════════

def test_DONE_thi_thu_dung_gia_phang_va_hoan_phan_du(db, kho_tam, tmp_path,
                                                     asr_gia, dich_gia,
                                                     giong_gia):
    """⭐ Giu **thua** roi hoan: so thu la `tinh_credit(do dai nguon)`, ⛔ khong
       phai `credit_held`, va ⛔ khong phai tong chi phi noi bo do duoc."""
    from platform_core import credit

    giu = gia.tinh_credit(DEFAULT_DURATION_S) + 25        # co tinh giu thua
    run = _tao_run(db, giu=giu, tmp_path=tmp_path)
    truoc_khi_giu = credit.so_du(db, "uA") + giu

    _chay_het_hang_doi(db, nang_luc={"api", "ffmpeg", "gpu", "voice"})
    db.expire_all()
    run = features.lay_run(db, run.id, "uA")

    assert run.status == RUN_DONE
    phai_thu = gia.tinh_credit(DEFAULT_DURATION_S)
    assert int(run.credit_actual) == phai_thu, (
        "so thu khong phai gia phang cua do dai nguon")
    assert credit.so_du(db, "uA") == truoc_khi_giu - phai_thu, (
        "phan giu thua phai duoc hoan lai het")


def test_khach_KHONG_BAO_GIO_tra_hon_so_da_hien_truoc_khi_bam(db, kho_tam,
                                                              tmp_path, asr_gia,
                                                              dich_gia,
                                                              giong_gia):
    """🔴 Chan tren o `credit_held`. Hai phep `ffprobe` tren cung nhung byte phai
       bang nhau; neu chung lech (cong cu doi, tep bi thay), khach van chi tra
       dung so ho da doc — ⛔ khong mot credit nao hon."""
    giu = 1                              # co tinh giu IT hon gia phang
    run = _tao_run(db, giu=giu, tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc={"api", "ffmpeg", "gpu", "voice"})
    db.expire_all()
    run = features.lay_run(db, run.id, "uA")

    assert gia.tinh_credit(DEFAULT_DURATION_S) > giu, "ca thu nay khong con y nghia"
    assert int(run.credit_actual) <= giu


# ══════════════════════════════════════════════════════════════════════════════
#  D. 🔴 Khong giao duoc thi KHONG thu — `N-21`
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("trang_thai", [RUN_ERROR, RUN_CANCELLED])
def test_KHONG_ve_done_thi_KHONG_thu_mot_credit_nao(db, kho_tam, trang_thai):
    """🔴 So loi `N-21`: khach bi tinh tien cho mot luot chay lai. ⛔ Dung tai tao.

    ⭐ Va bai nay **tiem chi phi noi bo truoc**: neu `quyet_toan` con doc
       `tong_da_dung` o duong nay thi no se thu 5, va phep kiem do duoc chinh cho
       de sai. Mot phep kiem chi chay tren mot run 0 chi phi ⛔ khong phan biet
       duoc "khong thu" voi "khong co gi de thu".
    """
    from platform_core import credit
    from apps.auto_scan_video import su_dung as sd

    giu = 30
    run = _tao_run(db, giu=giu)
    truoc_khi_giu = credit.so_du(db, "uA") + giu

    # Mot giai doan DA tieu tien that (5 credit do duoc o so cai).
    sd.ghi(db, run, stage="voice_synthesis", item_key="seg_0",
           su_dung=sd.SuDung(nang_luc="tong_hop_tieng", app_chu="ltt_voice",
                             trang_thai=sd.DA_GIAO, don_vi=sd.KY_TU,
                             so_luong=420.0, credit=5, ma_dispatch="t3900:0"))
    db.commit()
    assert features.tong_da_dung(db, run) == 5, "ca thu nay khong con y nghia"

    features.quyet_toan(db, run, trang_thai_cuoi=trang_thai)
    db.commit()

    assert int(run.credit_actual) == 0, (
        f"lan chay {trang_thai} van bi thu {run.credit_actual} credit")
    assert credit.so_du(db, "uA") == truoc_khi_giu, "hold phai duoc nha HET"


def test_DONE_va_QC_DAT_ma_KHONG_co_tep_nao_giao_thi_thu_0(db, kho_tam):
    """🔴 **Ca THAT, 25/09/2026 (`N-57`), do lan `asv-g17` do tren phim khach.**

        run.status == "done"                ✅
        bao QC `dat` == True                ✅
        render.outputs.khoa_asset == {}     🔴 KHONG MOT TEP NAO VE TAY KHACH

    Duong di: vong sua reset `render` + 5 giai doan → het vong sua → *"con 1 khiem
    khuyet CON LAI — giao hang va de QC lam cong gac"* → `done`.

    ⭐ **Vi sao ca nay lot qua bai `error`/`cancelled` o ngay tren.** Bai do hoi
       *trang thai*, va o day trang thai **dung**: `done` that, QC `dat` that. Cai
       sai la ta doc `done` thanh *"khach da nhan duoc hang"*, trong khi no chi noi
       *"may trang thai da chay het"*. ⇒ Mot phep do tra loi mot cau **khac** cau
       ta dang hoi — cung ho voi moi ca khac cua ngay 25/09.

    ⇒ Nen bai nay dung HIEN VAT: `render` xong, QC `dat`, ma `khoa_asset` rong.
    """
    from platform_core import credit
    from apps.auto_scan_video import su_dung as sd
    from apps.auto_scan_video.tables import STAGE_SUCCEEDED

    giu = 50
    run = _tao_run(db, giu=giu)
    truoc_khi_giu = credit.so_du(db, "uA") + giu

    # Chi phi noi bo DA tieu — neu luat con doc so cai thi no se thu 5.
    sd.ghi(db, run, stage="voice_synthesis", item_key="seg_0",
           su_dung=sd.SuDung(nang_luc="tong_hop_tieng", app_chu="ltt_voice",
                             trang_thai=sd.DA_GIAO, don_vi=sd.KY_TU,
                             so_luong=420.0, credit=5, ma_dispatch="t3900:n57"))

    # ⭐ `render` XONG va QC `dat` — dung hinh dang cua ca that. Chi `khoa_asset`
    #    la rong.
    gd = features.giai_doan_theo_ten(db, run.id, pipeline.RENDER)
    features.cap_nhat_giai_doan(
        db, gd, status=STAGE_SUCCEEDED,
        outputs={"stage": pipeline.RENDER, "khoa_asset": [], "dat": True})
    db.commit()

    assert features.tong_da_dung(db, run) == 5, "ca thu nay khong con y nghia"
    assert not features.co_hien_vat_giao_duoc(db, run)

    features.quyet_toan(db, run, trang_thai_cuoi=RUN_DONE)
    db.commit()

    assert int(run.credit_actual) == 0, (
        f"thu {run.credit_actual} credit cho mot lan GIAO HANG RONG — xem N-57")
    assert credit.so_du(db, "uA") == truoc_khi_giu, "hold phai duoc nha HET"
    # ⛔ Va ta ⛔ KHONG doi trang thai: doi `done` thanh `error` la viec cua may
    #    trang thai (lan `asv-g17`), khong phai cua luat thu tien.
    assert run.status == RUN_DONE


def test_khoa_asset_chi_co_SRT_cung_KHONG_phai_da_giao_hang(db, kho_tam):
    """⛔ `khoa_asset` khac rong ⛔ KHONG dong nghia da giao hang.

    ⭐ `khoa_ket_qua` loc `.mp4` va la **duong duy nhat** nut "Tai ve" cua khach
       co (`routes.tai_ket_qua`). Mot `render` chi dang `.srt` thi danh sach khac
       rong **nhung man hinh cua khach khong co gi bam duoc** — va mot phep kiem
       `khoa_asset != []` se goi do la "da giao".

    ⇒ Day la ly do `co_hien_vat_giao_duoc` uy quyen cho `khoa_ket_qua` thay vi tu
      doc `khoa_asset`: hai cau tra loi la MOT vi chung la mot phep tinh.
    """
    from apps.auto_scan_video.tables import STAGE_SUCCEEDED

    run = _tao_run(db, giu=50)
    gd = features.giai_doan_theo_ten(db, run.id, pipeline.RENDER)
    features.cap_nhat_giai_doan(
        db, gd, status=STAGE_SUCCEEDED,
        outputs={"stage": pipeline.RENDER, "dat": True,
                 "khoa_asset": ["asv/uA/x/long-tieng.srt"]})
    db.commit()

    assert not features.co_hien_vat_giao_duoc(db, run)

    features.quyet_toan(db, run, trang_thai_cuoi=RUN_DONE)
    db.commit()
    assert int(run.credit_actual) == 0


def test_CHI_THU_KHI_GIAO_DUOC_la_MOT_luat_khong_phan_loai_loi_cua_ai():
    """⭐ `loi.phan_loai` tra ve `NGUOI_DUNG` cho ca **that bai cuoi cung cua
       may** — chinh docstring cua no ghi *"`NGUOI_DUNG` o day khong noi 'loi cua
       khach'"*. Dung mot nhan mo ho lam can cu THU TIEN la thu tien theo mot thu
       khong co nghia do.

    ⇒ Tap nay phai chi co `done`. Mot ngay nao do them `error` vao day thi bai nay
      do, va nguoi them phai doc lai `N-21`.
    """
    import ast
    import textwrap

    from apps.auto_scan_video import ma_loi

    assert features.CHI_THU_KHI_GIAO_DUOC == frozenset({RUN_DONE})

    # ⛔ Doc MA, ⛔ khong doc van xuoi: docstring cua `quyet_toan` **noi ve** nhung
    #    cai ten bi cam de giai thich vi sao chung bi cam.
    cay = ast.parse(textwrap.dedent(inspect.getsource(features.quyet_toan)))
    ham = cay.body[0]
    if (ham.body and isinstance(ham.body[0], ast.Expr)
            and isinstance(ham.body[0].value, ast.Constant)):
        ham.body = ham.body[1:]
    ten = {n.attr for n in ast.walk(ham) if isinstance(n, ast.Attribute)}
    ten |= {n.id for n in ast.walk(ham) if isinstance(n, ast.Name)}

    assert "CHI_THU_KHI_GIAO_DUOC" in ten
    assert "co_hien_vat_giao_duoc" in ten
    for cam in ("phan_loai", "HOAN_CREDIT", "NGUOI_DUNG"):
        assert cam not in ten, (
            f"`quyet_toan` phan loai loi bang {cam} — xem docstring cua "
            f"`CHI_THU_KHI_GIAO_DUOC`")

    # ⭐ Va bang phan biet "ma nao duoc hoan" da bi XOA (25/09): duoi gia phang moi
    #    ket cuc khong-giao-duoc deu hoan 100 %, nen mot bang nhu vay phan biet
    #    giua hai thu giong het nhau. ⛔ Dung dung lai no.
    assert not hasattr(ma_loi, "HOAN_CREDIT")


def _dat_lan_chay_da_giao(db, run, giay: float) -> None:
    """Dung hai su that ma luat thu tien doi: **do dai nguon** + **hien vat**.

    ⚠️ Thieu mot trong hai thi `quyet_toan` roi ve mot duong KHAC (duong lui theo
       `credit_held`, hoac duong "khong co hien vat ⇒ thu 0"). Ca hai duong deu
       hop le, nhung chung ⛔ khong phai duong dang duoc kiem — va mot bai xanh nho
       mot duong khac la mot bai xanh gia.
    """
    from apps.auto_scan_video.tables import STAGE_SUCCEEDED

    gd = features.giai_doan_theo_ten(db, run.id, pipeline.MEDIA_PREPARE)
    features.cap_nhat_giai_doan(db, gd, outputs={"stage": pipeline.MEDIA_PREPARE,
                                                 "thoi_luong": float(giay)})
    rd = features.giai_doan_theo_ten(db, run.id, pipeline.RENDER)
    features.cap_nhat_giai_doan(
        db, rd, status=STAGE_SUCCEEDED,
        outputs={"stage": pipeline.RENDER, "dat": True,
                 "khoa_asset": [f"asv/{run.owner_id}/{run.id}/long-tieng.mp4"]})
    db.flush()


def test_quyet_toan_HAI_LAN_khong_doi_gia_cua_mot_run_da_ket_thuc(db, kho_tam):
    """⛔ Job CU khong bao gio bi tinh lai. `advance` duoc chay lai sau khi worker
       chet, va mot lan quyet toan thu hai phai la mot lan khong lam gi."""
    run = _tao_run(db, giu=30)
    _dat_lan_chay_da_giao(db, run, 120.0)
    phai_thu = gia.tinh_credit(120.0)

    features.quyet_toan(db, run, trang_thai_cuoi=RUN_DONE)
    db.commit()
    lan_dau = int(run.credit_actual)
    assert lan_dau == phai_thu > 0, "lan dau phai thu THAT, ⛔ khong phai 0"

    run.credit_held = 999                # keo hold len — mot lan tinh lai se doi so
    db.flush()
    features.quyet_toan(db, run, trang_thai_cuoi=RUN_DONE)
    db.commit()
    assert int(run.credit_actual) == lan_dau, "run da ket thuc bi tinh lai gia"


def test_SO_CAI_van_can_va_so_du_KHONG_AM_sau_mot_luot_day_du(
        db, kho_tam, tmp_path, asr_gia, dich_gia, giong_gia):
    """⛔ Gia phang doi **so** duoc thu, ⛔ khong duoc lam hong SO SACH.

    `su_dung.doi_soat` nem khi `item.credit_actual` lech khoi so cai; `doi_soat_nhanh`
    bay ca hai chieu (don vi co tien ma mat dong · dong so cai mo coi).
    """
    from platform_core import credit
    from apps.auto_scan_video import su_dung as sd

    run = _tao_run(db, giu=gia.tinh_credit(DEFAULT_DURATION_S), tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc={"api", "ffmpeg", "gpu", "voice"})
    db.expire_all()
    run = features.lay_run(db, run.id, "uA")

    sd.doi_soat(db, run)                 # nem neu lech
    ds = quan_sat.doi_soat_nhanh(db, run)
    assert ds["khop"], ds
    assert credit.so_du(db, "uA") >= 0, "so du am"
    assert int(run.credit_actual) <= int(run.credit_held), "thu hon phan da giu"
    # ⛔ `dang_giu` chu khong `so_da_giu`: `so_da_giu` cong cac but toan `hold` va
    #    **khong bao gio** tro ve 0 (but toan la mot so cai, khong phai mot bien
    #    dem). Vi ngu dung la *"con mot khoan giu chua ket so"*.
    assert not credit.dang_giu(db, run.id), "con tien treo tren mot run da xong"


# ══════════════════════════════════════════════════════════════════════════════
#  E. MOT cho khai, MOT cho tinh
# ══════════════════════════════════════════════════════════════════════════════

def _cac_module_asv():
    return [p for p in sorted(APP.glob("*.py")) if p.name != "gia.py"]


#: Moi hang so hinh-dang-gia trong `apps/auto_scan_video`, kem LY DO no duoc phep
#: ton tai. ⛔ Mot ten moi lot vao day phai duoc giai thich, ⛔ khong duoc lam mo di
#: bang mot regex hep hon.
#:
#: ⭐ 25/09: `manifest.GIA_THU_MOI_RUN = 1` da bi **xoa** — hang "gia tam" tu pha 05,
#:    `grep` ca kho chi ra dung dong khai no va ⛔ khong mot nguoi doc nao.
GIA_DUOC_PHEP = {
    # ⭐ Ban khai DUY NHAT cua gia, trong toan bo app.
    "gia.py:GIA_CREDIT_MOI_PHUT",
}


def test_DON_GIA_duoc_khai_dung_MOT_lan_trong_ca_app():
    """🔴 Kho nay co ca mot ho loi *"hai cho khai mot dieu, ⛔ khong ai bat
       khop"*. Mot hang gia thu hai o mot module khac la mot bang gia thu hai, va
       no se troi khoi bang gia that ngay lan dau ai do sua mot con so."""
    khai = set()
    for p in APP.glob("*.py"):
        for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if not isinstance(n, ast.Assign):
                continue
            for dich in n.targets:
                if (isinstance(dich, ast.Name)
                        and re.match(r"^(GIA|DON_GIA|CREDIT)_", dich.id)
                        and isinstance(n.value, ast.Constant)
                        and isinstance(n.value.value, (int, float))):
                    khai.add(f"{p.name}:{dich.id}")
    assert khai == GIA_DUOC_PHEP, khai

    # ⛔ Va hang "gia tam" cu ⛔ khong duoc song lai o bat cu dau.
    toi = Path(__file__).resolve()
    con = []
    for goc_con in ("apps", "platform_core", "server", "tools", "tests"):
        for p in (GOC / goc_con).rglob("*.py"):
            if "__pycache__" in p.parts or p.resolve() == toi:
                continue
            if "GIA_THU_MOI_RUN" in p.read_text(encoding="utf-8"):
                con.append(str(p.relative_to(GOC)))
    assert con == [], f"`GIA_THU_MOI_RUN` da song lai o: {con}"


def test_MOI_loi_giu_cho_deu_di_qua_gia_tinh_credit():
    """⛔ `uoc_luong_credit=` la cua vao duy nhat cua tien vao mot run. Moi loi goi
       phai lay so tu `gia.tinh_credit` — ⛔ khong tu mot phep tinh tai cho, ⛔ khong
       tu mot tham so HTTP."""
    thay = []
    for p in APP.glob("*.py"):
        for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if not isinstance(n, ast.Call):
                continue
            for kw in n.keywords:
                if kw.arg != "uoc_luong_credit":
                    continue
                bt = kw.value
                ten = ""
                if isinstance(bt, ast.Call) and isinstance(bt.func, ast.Attribute):
                    ten = bt.func.attr
                elif isinstance(bt, ast.Name):
                    ten = bt.id
                thay.append(f"{p.name}:{ten}")
    assert thay, "khong tim thay loi goi `tao_run(uoc_luong_credit=...)` nao"
    xau = [t for t in thay if t.rsplit(":", 1)[-1] not in
           ("tinh_credit", "gia_credit")]
    assert not xau, f"nhung cho nay khong lay gia tu `gia.tinh_credit`: {xau}"


def test_ROUTE_khong_biet_don_gia_va_khong_tinh_lai_gi():
    """⭐ Cong thuc gia la mot thu **san pham**, ⛔ khong phai mot hang so hien thi.
       Tinh no o tang HTTP (hay o trinh duyet) la xuat ban no."""
    nguon = (APP / "routes.py").read_text(encoding="utf-8")
    assert "GIA_CREDIT_MOI_PHUT" not in nguon
    assert "so_phut_tinh_tien" not in nguon
    assert "xem_truoc_chi_phi" in nguon, "route phai goi ham da khai, khong tu ghep"


def test_HOA_DON_khong_co_cong_thuc_thu_hai():
    """`hoa_don()["credit"]` phai **la** `tinh_credit`, ⛔ khong phai `so_phut x
       don_gia` go lai — hai phep tinh cung nghia hom nay se lech ngay mai."""
    for giay in (0.0, 30.0, 60.0, 61.0, 190.0, 5400.0):
        hd = gia.hoa_don(giay)
        assert hd["credit"] == gia.tinh_credit(giay)
        assert hd["so_phut"] == gia.so_phut_tinh_tien(giay)
        assert hd["don_gia"] == gia.GIA_CREDIT_MOI_PHUT


# ══════════════════════════════════════════════════════════════════════════════
#  F. Hoa don cua KHACH la MOT dong — do luong theo nang luc ve nhat ky ky thuat
# ══════════════════════════════════════════════════════════════════════════════

def test_HOA_DON_khach_la_MOT_dong_khong_con_bang_theo_nang_luc(
        db, kho_tam, tmp_path, asr_gia, dich_gia, giong_gia):
    """⚠️ Mot bang nam dong cho mot con so PHANG la mot bang **noi doi ve cach
       tinh**: no goi y rang bo mot nang luc di se tra it hon."""
    run = _tao_run(db, giu=gia.tinh_credit(DEFAULT_DURATION_S), tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc={"api", "ffmpeg", "gpu", "voice"})
    db.expire_all()
    run = features.lay_run(db, run.id, "uA")

    t = quan_sat.tom_tat_cho_khach(db, run)
    assert "chi_phi_theo_nang_luc" not in t, "bang theo nang luc con o hoa don khach"

    hd = t["hoa_don"]
    assert hd["da_do_do_dai"] is True
    assert hd["so_phut"] == gia.so_phut_tinh_tien(DEFAULT_DURATION_S)
    assert hd["credit"] == gia.tinh_credit(DEFAULT_DURATION_S)
    assert hd["don_gia"] == gia.GIA_CREDIT_MOI_PHUT
    assert str(gia.GIA_CREDIT_MOI_PHUT) in hd["luat_lam_tron"]


def test_CHUA_do_do_dai_thi_hoa_don_de_None_chu_khong_bia_mot_phut(db, kho_tam):
    """⛔ `None` chu khong `0` va ⛔ khong `1 phut`: truoc khi `media_prepare` chay,
       ta ⛔ khong biet do dai, va bia ra "1 phut" cho mot video 30 phut la mot con
       so se doi ngay truoc mat khach."""
    run = _tao_run(db, giu=10)
    hd = quan_sat.tom_tat_cho_khach(db, run)["hoa_don"]
    assert hd["da_do_do_dai"] is False
    assert hd["so_phut"] is None and hd["credit"] is None
    # Luat lam tron VAN hien: khach can no truoc khi bam, khong phai sau khi do.
    assert hd["luat_lam_tron"]


def test_DO_LUONG_theo_nang_luc_VAN_SONG_o_nhat_ky_KY_THUAT(
        db, kho_tam, tmp_path, asr_gia, dich_gia, giong_gia):
    """⭐ Gia phang bo bang do khoi **hoa don cua khach**, ⛔ khong xoa phep **do**.
       `so_ke` tra loi cau *"cho nao dang dot tien"* — cau cua nguoi van hanh."""
    run = _tao_run(db, giu=gia.tinh_credit(DEFAULT_DURATION_S), tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc={"api", "ffmpeg", "gpu", "voice"})
    db.expire_all()
    run = features.lay_run(db, run.id, "uA")

    vh = quan_sat.dong_thoi_gian(db, run, cho_van_hanh=True)
    assert "so_ke" in vh and "theo_nang_luc" in vh["so_ke"]
    assert "doi_soat" in vh


# ══════════════════════════════════════════════════════════════════════════════
#  G. Duong render — do duoc TRUOC khi no thanh van de
# ══════════════════════════════════════════════════════════════════════════════

def test_DUONG_RENDER_ghi_ca_PRESET_va_duong_di(db, kho_tam):
    """🔴 Gia phang gia thiet **phan lon luot di duong `sao_chep`** (chep luong
       hinh, gan nhu khong ma hoa).

    ⭐ Va bien dieu khien la **PRESET**, ⛔ khong phai tap tinh nang: `che_do_cho`
       nhan dung mot tham so, va cac co bien tap bi `ban_dung.kiem` tu choi tren
       duong `sao_chep` — chung chi song o preset **da ma hoa lai san**.

    ⇒ Nen truong nay ghi **ca hai** de sau mot thang cau *"bao nhieu % luot di
      duong dat, va preset nao?"* tra loi duoc bang **so lieu**, ⛔ khong bang doan
      luc xem hoa don dien.
    """
    from apps.auto_scan_video import cai_dat as cd
    from apps.auto_scan_video import che_do_render as cdr
    from apps.auto_scan_video.hop_dong_v4 import PRESET

    run = _tao_run(db, giu=10)
    dr = quan_sat.dong_thoi_gian(db, run, cho_van_hanh=True)["duong_render"]
    assert dr["duong"] in cdr.CHE_DO
    assert dr["preset"] in PRESET
    # ⭐ Suy tu PRESET da khai (qua `cai_dat.doc`, tuc co ca mac dinh), ⛔ khong tu
    #    du lieu cua lan chay: mot ban bien tap giu TAT CA canh van la preset cat,
    #    va no van phai ma hoa lai (`che_do_render.che_do_cho`).
    assert dr == quan_sat.duong_render_cua(run)
    assert dr["duong"] == cdr.che_do_cho(cd.doc(run).preset)


def test_DUONG_RENDER_do_PRESET_quyet_dinh_chu_KHONG_do_co_tinh_nang():
    """🔴 **Bai nay chot cai co che, vi chinh cho nay tung bi khai SAI.**

    Ban dau `gia.py` ghi *"moi co tinh nang day luot sang `cat_ma_hoa_lai`, nen gia
    thiet gia phang yeu dan"*. Nguoi doc MA bac bo trong nam phut: `che_do_cho` co
    chu ky **mot tham so** — `preset` — nen ⛔ khong mot co nao doi duoc duong di.

    ⇒ Bai nay la cai chot co hoc cho dieu do. Ai them mot tham so thu hai vao
      `che_do_cho` se lam no do, va phai doc lai ghi chu o `gia.py`.
    """
    from apps.auto_scan_video import che_do_render as cdr

    ts = [p for p in inspect.signature(cdr.che_do_cho).parameters]
    assert ts == ["preset"], (
        f"`che_do_cho` nhan {ts} — duong render khong con la mot ham cua RIENG "
        f"preset, nen ghi chu o `gia.py` ve bien dieu khien chi phi da cu")


def test_DUONG_RENDER_o_nhat_ky_KY_THUAT_chu_KHONG_o_hoa_don_khach(db, kho_tam):
    """⛔ Khach tra mot gia phang; duong render la viec cua ta. Lo no ra la mo cua
       cho cau *"sao toi phai tra them vi may cua anh cham hon"* cho mot khoan
       khach ⛔ khong he tra them."""
    import json

    from apps.auto_scan_video import che_do_render as cdr
    from apps.auto_scan_video.hop_dong_v4 import PRESET

    run = _tao_run(db, giu=10)
    van = json.dumps(quan_sat.tom_tat_cho_khach(db, run), ensure_ascii=False)
    assert "duong_render" not in van
    for ma in (*cdr.CHE_DO, *PRESET):
        assert ma not in van, f"lo ma noi bo `{ma}` cho khach"

"""Lat cat giai doan dai — mot giai doan nhieu don vi viec chay thanh NHIEU job
noi tiep nhau, moi job nam gon trong tran cua no.

## Van de (docs/auto_scan_video_v6/CHAN_DOAN_TEST_448.md §10)

ASV nhan video 120 phut. `content_process` chay cac lo dich TUAN TU trong MOT job
co tran 60 phut; o 142 giay/lo chi ~25 lo lot tran — tuc ~20 phut video. Vuot
tran thi `job_runner._het_gio` giet tien trinh va `retry=False` (test_217): lan
chay hong, khach phai tu bam lai. Cung hinh dang do nam o `edit_plan` (VLM moi
canh), `voice_synthesis` (TTS moi doan) va `qc_ai` (lo soat nghia).

## Cach sua: NHUONG truoc khi cham tran, roi NOI TIEP bang job moi

Truoc khi bat dau MOT don vi viec, giai doan hoi `LatCat.nen_nhuong()`:

    da_troi + du_phong(don vi te nhat) > HE_SO_TRAN * tran_job

`du_phong` la thoi gian XAU NHAT cua mot don vi, tinh tu CHINH cac tran timeout
cua lop goi (khong go lai so). Nen neu moi lop goi ton trong timeout cua no thi
job **khong the** cham tran: don vi cuoi cung bat dau khi con du cho cho truong
hop te nhat cua no. Luon lam it nhat MOT don vi moi luot => luon tien.

Nhuong = nem `TiepNoi`. `thi_hanh.chay_giai_doan` bat no, ghi con tro vao
`AsvStage.outputs["tiep_noi"]` va dua giai doan ve `pending`; luot `advance` ke
tiep nop mot job MOI (khoa dedupe `a{attempt}:n{luot}`, KHONG tang `attempt` —
noi tiep khong phai thu lai). Job moi di qua admission `llm_remote` nhu moi job
khac, nen gioi han dong thoi cua nen tang giu nguyen; giua hai luot, run khac
co the chen vao suat do.

⛔ Ngu nghia ban ra KHONG doi: con tro chi noi "da di toi dau"; ket qua tung don
   vi van doc tu diem chot (`su_dung.danh_dau_xong`) nhu mot lan chay lai.
   Nhung don vi da THU va bo qua (canh doc hong, lo QC mo ho) nam TRUOC con tro
   nen luot sau khong thu lai chung — dung nhu lan chay mot mach.

⚠️ Con tro mang `van_tay` cua giai doan: doi dau vao => con tro cu vo hieu.
   `_dat_lai_giai_doan` xoa `outputs` => con tro mat theo, dung y.
"""
from __future__ import annotations

import contextvars
import functools
import inspect
import logging
import time
import uuid
from dataclasses import dataclass

log = logging.getLogger(__name__)

#: Dong ho. Phep kiem thay bang dong ho gia de "chay" 120 phut trong vai giay.
dong_ho = time.monotonic

#: Chi dung toi da phan nay cua tran job. Phan con lai la cho cho viec SAU
#: vong lap (rap ket qua, ghi kho, promote) va cho do lech giua luc
#: `job_runner` bat dong ho canh gio va luc `thi_hanh` bat dau dem.
HE_SO_TRAN = 0.85

#: Muc tieu mem cho MOT luot: qua moc nay (va da lam it nhat mot don vi) thi
#: nhuong du con tran. Ly do: mot job giu suat `llm_remote` hang gio la chan
#: moi run khac; 30 phut la du dai de chi phi noi tiep (vai giay) khong dang ke.
LUOT_MUC_TIEU_S = 30 * 60

#: Tran so luot noi tiep cua MOT giai doan. Moi luot lam >= 1 don vi nen tran
#: nay chi cham khi co loi logic (vd con tro khong tien) — khi do hong han
#: thay vi quay vo han tren may production.
TIEP_NOI_TOI_DA = 500

_BAT_DAU: contextvars.ContextVar[float | None] = contextvars.ContextVar(
    "asv_lat_cat_bat_dau", default=None)
#: Van tay HIEU LUC cua giai doan dang chay (`thi_hanh.van_tay`) — gom moi dau
#: vao + phien ban engine, nen la khoa dung cho con tro cua giai doan khong tu
#: tinh van tay rieng.
_VAN_TAY: contextvars.ContextVar[str] = contextvars.ContextVar(
    "asv_lat_cat_van_tay", default="")


class TiepNoi(Exception):
    """Giai doan nhuong: da lam mot phan, phan con lai chay o job ke tiep.

    ⚠️ KHONG phai loi. `thi_hanh` bat no TRUOC nhanh `except Exception` va ghi
       con tro; no khong bao gio toi `loi.phan_loai`.
    """

    def __init__(self, *, van_tay: str, phien: str, luot: int, vi_tri: int,
                 trang_thai: dict, da_lam: int, da_troi_s: float):
        super().__init__(f"tiep noi luot {luot + 1} tu vi tri {vi_tri}")
        self.van_tay = van_tay
        self.phien = phien
        self.luot = luot
        self.vi_tri = vi_tri
        self.trang_thai = trang_thai
        self.da_lam = da_lam
        self.da_troi_s = da_troi_s


def bat_dau_luot() -> None:
    """Danh dau thoi diem job nay bat dau. `thi_hanh` goi o dau moi job."""
    _BAT_DAU.set(dong_ho())
    _VAN_TAY.set("")


def ket_thuc_luot() -> None:
    """Xoa moc cua job vua xong. `thi_hanh` goi o `finally`."""
    _BAT_DAU.set(None)
    _VAN_TAY.set("")


def dat_van_tay_giai_doan(vt: str) -> None:
    """`thi_hanh` goi truoc khi vao engine."""
    _VAN_TAY.set(str(vt or ""))


@functools.lru_cache(maxsize=None)
def _tran_theo_job_type(app_slug: str, job_type: str) -> int:
    from platform_core import registry
    from platform_core.job_runner import RUNTIME_LIMIT_DEFAULT_S

    for item in registry.discover():
        if item.error or item.manifest.slug != app_slug:
            continue
        return int(item.manifest.runtime_limit_for(
            job_type, default=RUNTIME_LIMIT_DEFAULT_S))
    return int(RUNTIME_LIMIT_DEFAULT_S)


def tran_giai_doan(ten: str) -> int:
    """Tran thoi gian (giay) cua job chay giai doan `ten` — doc tu MANIFEST.

    ⭐ Mot nguon: cung con so `job_runner._canh_gio` dung de giet tien trinh.
    """
    from . import pipeline

    g = pipeline.THEO_TEN[ten]
    return _tran_theo_job_type(g.app_slug, g.job_type)


def han_tien_trinh_con(ten: str, mac_dinh: float, *, toi_thieu: float = 60.0) -> int:
    """Timeout cho MOT tien trinh con dai (demucs, ffmpeg render) cua job nay.

    🔴 Giai doan KHONG chia duoc (mot lan demucs / mot lan render tren ca video)
       van phai co timeout NHO HON tran job. Neu khong, `job_runner._het_gio`
       ban `os._exit(3)` truoc, va tren Windows tien trinh con KHONG chet theo
       cha: demucs mo coi tiep tuc giu GPU sau khi job da bao hong. Timeout cua
       chinh ta thi `kill()` con roi moi nem.

    = min(`mac_dinh`, ngan sach con lai cua job), khong duoi `toi_thieu`.
    """
    bat_dau = _BAT_DAU.get()
    troi = (float(dong_ho()) - bat_dau) if bat_dau is not None else 0.0
    con = HE_SO_TRAN * float(tran_giai_doan(ten)) - troi
    return int(max(toi_thieu, min(float(mac_dinh), con)))


def mac_dinh_tham_so(ham, ten: str) -> float:
    """Gia tri mac dinh cua tham so `ten` cua `ham` — de doc tran timeout cua
    lop duoi thay vi go lai so cua no (CLAUDE.md: hai ban sao troi khoi nhau)."""
    return float(inspect.signature(ham).parameters[ten].default)


#: Phan cong them cho MOT don vi ngoai thoi gian goi model: doc/ghi CSDL,
#: `commit`, doc JSON. Rong rai co y — no chi doi moc nhuong som hon mot chut.
DU_PHONG_NGOAI_GOI_S = 60.0


def timeout_goi_ai(thao_tac) -> float:
    """Tran thoi gian XAU NHAT cua MOT lan `ai.goi_tinh_tien(thao_tac)`.

    Thao tac co khai `ai.NGAN_SACH_RA` thi lay timeout do; khong thi la mac
    dinh cua `dieu_phoi.goi`. Nhan so provider trong `THU_TU_PROVIDER` vi
    `dieu_phoi` thu lan luot tung cai.
    """
    from . import ai

    return ai.timeout_xau_nhat(thao_tac)


@dataclass
class LatCat:
    ten: str
    van_tay: str
    phien: str
    luot: int
    vi_tri: int
    trang_thai: dict
    tran_s: float
    du_phong_s: float
    bat_dau: float
    da_lam: int = 0

    @property
    def noi_tiep(self) -> bool:
        """Day co phai mot luot NOI TIEP (khong phai luot dau) khong."""
        return self.luot > 0

    def da_troi(self) -> float:
        return float(dong_ho()) - self.bat_dau

    def ngan_sach_s(self) -> float:
        return HE_SO_TRAN * self.tran_s

    def nen_nhuong(self) -> bool:
        if self.da_lam < 1:
            return False            # moi luot phai tien it nhat mot don vi
        troi = self.da_troi()
        return (troi + self.du_phong_s > self.ngan_sach_s()
                or troi >= LUOT_MUC_TIEU_S)

    def xong_mot(self) -> None:
        self.da_lam += 1

    def kiem(self, vi_tri: int, trang_thai: dict | None = None) -> None:
        """Goi TRUOC moi don vi. Nem `TiepNoi` neu phai nhuong.

        ⛔ Nguoi goi phai `commit` moi diem chot TRUOC dong nay — `TiepNoi` ket
           thuc job, va thu chua commit thi khong ton tai.
        """
        if self.nen_nhuong():
            raise TiepNoi(van_tay=self.van_tay, phien=self.phien,
                          luot=self.luot, vi_tri=int(vi_tri),
                          trang_thai=dict(trang_thai or self.trang_thai or {}),
                          da_lam=self.da_lam, da_troi_s=round(self.da_troi(), 3))


def con_tro(stage) -> dict:
    """Con tro noi tiep dang luu tren dong giai doan (rong neu khong co)."""
    tn = ((getattr(stage, "outputs", None) or {}).get("tiep_noi")
          if stage is not None else None)
    return dict(tn) if isinstance(tn, dict) else {}


def mo(db, run, ten: str, *, du_phong_s: float, van_tay: str = "") -> LatCat:
    """Mo lat cat cho giai doan `ten` cua `run`. Khoi phuc con tro neu KHOP van tay.

    ⛔ `du_phong_s` >= ngan sach => cau hinh sai (mot don vi te nhat khong vua
       mot job) — hong ngay, khong de job chay roi bi giet.
    """
    from . import features

    tran = float(tran_giai_doan(ten))
    # ⭐ MOT lan doc `_BAT_DAU`, khong hai. Hai lan `.get()` de tra loi mot cau
    #    hoi la hai co hoi de chung lech nhau, va cai lech o day la mot `None`
    #    di vao `bat_dau: float`. Do bang `mypy [arg-type]` 24/09.
    bd = _BAT_DAU.get()
    lc = LatCat(ten=ten, van_tay=str(van_tay or _VAN_TAY.get() or ""), phien=uuid.uuid4().hex[:16],
                luot=0, vi_tri=0, trang_thai={}, tran_s=tran,
                du_phong_s=float(du_phong_s),
                bat_dau=float(dong_ho()) if bd is None else bd)
    if lc.du_phong_s >= lc.ngan_sach_s():
        raise ValueError(
            f"lat_cat {ten}: du phong {lc.du_phong_s:.0f}s >= ngan sach "
            f"{lc.ngan_sach_s():.0f}s cua tran {tran:.0f}s")

    stage = features.giai_doan_theo_ten(db, run.id, ten) if db is not None else None
    tn = con_tro(stage)
    if tn and str(tn.get("van_tay") or "") == lc.van_tay:
        lc.phien = str(tn.get("phien") or lc.phien)
        lc.luot = int(tn.get("luot") or 0)
        lc.vi_tri = int(tn.get("vi_tri") or 0)
        lc.trang_thai = dict(tn.get("trang_thai") or {})
    elif tn:
        log.info("asv lat_cat %s: con tro cu lech van tay — bo, chay tu dau", ten)
    return lc


def ghi_tiep_noi(db, stage, tn: TiepNoi) -> dict:
    """Ghi con tro + dua giai doan ve `pending` de `advance` nop luot ke tiep.

    Tra ve con tro da ghi. Vuot `TIEP_NOI_TOI_DA` => hong HAN (khong quay vo han).
    """
    from . import features
    from .tables import STAGE_PENDING

    luot = int(tn.luot) + 1
    if luot > TIEP_NOI_TOI_DA:
        features.danh_dau_hong(
            db, stage, f"vuot {TIEP_NOI_TOI_DA} luot noi tiep", cuoi_cung=True)
        return {}
    ct = {"van_tay": tn.van_tay, "phien": tn.phien, "luot": luot,
          "vi_tri": int(tn.vi_tri), "trang_thai": dict(tn.trang_thai or {}),
          "luot_truoc": {"da_lam": int(tn.da_lam), "giay": tn.da_troi_s}}
    features.cap_nhat_giai_doan(db, stage, status=STAGE_PENDING,
                                outputs={"tiep_noi": ct}, error="")
    return ct

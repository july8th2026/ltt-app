"""So dang ky bo do cua giai doan `qc_do_luong` — MOT cho gom moi bo do.

    chay_tat_ca(dau_vao: DauVao, *, gpu_uuid, is_cancelled) -> dict[ten, KetQuaBoDo]

Moi bo do tra loi MOT cau hoi bang MOT model da thanh danh, va tra ket qua
**theo doan** (`{ma: {...}}`) hoac trang thai `khong_kha_dung`. Them mot bo do
= them MOT dong vao `BO_DO` (va mot ham `_chay_*` boc module cua no).

## Vi sao chay LAN LUOT, moi bo do mot tien trinh con

Moi bo do nap model len card trong mot tien trinh con cua `venv.chay` roi
**thoat**. Tien trinh thoat la cach duy nhat chac chan tra lai VRAM (CUDA
context, cache allocator cua torch, bo nho rieng cua ctranslate2 — khong cai
nao tra het bang `del model`). Chay lan luot giu dinh VRAM = dinh cua bo do
nang nhat, khong phai tong — va card nay dung chung voi Voice/VLM.

## ⛔ Mot bo do hong KHONG lam hong giai doan

`khong_kha_dung` (thieu venv/model) va `loi` (chay ma hong) deu duoc GHI vao
bao cao roi di tiep. Mot phep do vang mat nghia la "khong biet", khong phai
"co loi" va cung khong phai "dat" — nguoi doc (vong sua) chi hanh dong tren
ket qua `xong`.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from . import giong, squim
from .venv import DoLuongLoi, KhongKhaDung

XONG = "xong"
KHONG_KHA_DUNG = "khong_kha_dung"
LOI = "loi"


@dataclass(frozen=True)
class DauVao:
    """Moi thu mot bo do co the can. Bo do tu lay phan cua no."""

    #: `[{ma, tep, chu}]` — `tep` la WAV da dung (16 kHz mono, da co gian dung
    #: nhu ban phoi), `chu` la kich ban CUOI CUNG da dua cho may doc.
    doan_tieng: list = field(default_factory=list)
    #: `[{ma, nguon, dich}]` — cap cau cho bo do dich (MetricX, lan "dich").
    cap_dich: list = field(default_factory=list)
    ngon_ngu_nguon: str = ""
    ngon_ngu_dich: str = ""
    #: Tu dien ten rieng cua khach — cung tu dien may doc da dung.
    tu_dien: dict = field(default_factory=dict)
    #: Ten model ASR — nguoi goi truyen `giai_doan_chep_loi.MODEL_ASR`.
    model_asr: str = "large-v3"


@dataclass(frozen=True)
class BoDo:
    ten: str
    #: Phien ban cua bo do (model + chuan hoa + tham so). Vao van tay giai doan.
    phien_ban: str
    chay: Callable[..., dict]


def _chay_giong(dv: DauVao, *, gpu_uuid: str, is_cancelled=None) -> dict:
    return giong.do_giong(dv.doan_tieng, ngon_ngu=dv.ngon_ngu_dich,
                          tu_dien=dv.tu_dien, model=dv.model_asr,
                          gpu_uuid=gpu_uuid,
                          is_cancelled=is_cancelled)


def _chay_chat_luong_tieng(dv: DauVao, *, gpu_uuid: str, is_cancelled=None) -> dict:
    return squim.do_squim(dv.doan_tieng, gpu_uuid=gpu_uuid,
                          is_cancelled=is_cancelled)


def _chay_dich(dv: DauVao, *, gpu_uuid: str, is_cancelled=None) -> dict:
    """🔌 CHO CAM bo do dich cua lan "dich" (`do_luong/metricx.py`).

    Hop dong da hen: `do_dich(cap, ngon_ngu_nguon, ngon_ngu_dich, gpu_uuid)
    -> {ma: diem}`. Module chua co trong cay ⇒ `khong_kha_dung`, khong lui.
    """
    try:
        from . import metricx  # type: ignore[attr-defined]
    except ImportError as exc:
        raise KhongKhaDung("chua co bo do dich (do_luong/metricx.py)") from exc
    # ⛔ TU KHOA, khong vi tri: `do_dich` khai `*` sau `cap`. Ban dau cho cam
    #    nay goi theo vi tri va no se nem `TypeError` o dung luot chay that dau
    #    tien — mot loi chi lo ra khi HAI lan gap nhau.
    diem = metricx.do_dich(dv.cap_dich, ngon_ngu_nguon=dv.ngon_ngu_nguon,
                           ngon_ngu_dich=dv.ngon_ngu_dich, gpu_uuid=gpu_uuid,
                           is_cancelled=is_cancelled)
    return {"ket_qua": {str(ma): {"metricx": d} for ma, d in (diem or {}).items()}}


#: 🔑 BANG NAY LA CHINH SACH. Thu tu = thu tu chay.
BO_DO: tuple[BoDo, ...] = (
    BoDo("giong", giong.PHIEN_BAN, _chay_giong),
    BoDo("chat_luong_tieng", squim.PHIEN_BAN, _chay_chat_luong_tieng),
    BoDo("dich", "metricx/lan-dich", _chay_dich),
)


def phien_ban() -> str:
    return ",".join(f"{b.ten}:{b.phien_ban}" for b in BO_DO)


def _can_du_lieu(b: BoDo, dv: DauVao) -> bool:
    if b.ten == "dich":
        return bool(dv.cap_dich)
    return bool(dv.doan_tieng)


def chay_tat_ca(dv: DauVao, *, gpu_uuid: str = "", is_cancelled=None,
                bao=None) -> dict:
    """`{ten: {trang_thai, ket_qua: {ma: {...}}, ly_do, giay}}` — moi bo do."""
    ra: dict = {}
    for i, b in enumerate(BO_DO):
        if is_cancelled is not None and is_cancelled():
            raise DoLuongLoi("da huy")
        if bao:
            bao(i, b.ten)
        t0 = time.monotonic()
        if not _can_du_lieu(b, dv):
            ra[b.ten] = {"trang_thai": KHONG_KHA_DUNG, "ket_qua": {},
                         "ly_do": "khong co du lieu dau vao", "giay": 0.0,
                         "phien_ban": b.phien_ban}
            continue
        try:
            kq = b.chay(dv, gpu_uuid=gpu_uuid, is_cancelled=is_cancelled)
            ra[b.ten] = {"trang_thai": XONG, "ket_qua": dict(kq["ket_qua"]),
                         "ly_do": "", "tai_nguyen": dict(kq.get("tai_nguyen") or {})}
        except KhongKhaDung as exc:
            ra[b.ten] = {"trang_thai": KHONG_KHA_DUNG, "ket_qua": {},
                         "ly_do": str(exc)[:500]}
        except DoLuongLoi as exc:
            if "da huy" in str(exc):
                raise
            ra[b.ten] = {"trang_thai": LOI, "ket_qua": {},
                         "ly_do": str(exc)[-800:]}
        ra[b.ten]["giay"] = round(time.monotonic() - t0, 2)
        ra[b.ten]["phien_ban"] = b.phien_ban
    return ra

"""Cong workflow NOI BO cua Auto Scan Video — nam ham, kieu ro, khong biet giai doan.

Hop dong day du: `docs/auto_scan_video_final/L_CONG_NOI_BO.md`.

## Day KHONG phai public API

Khong khoa API, khong `/api/v1`, khong webhook, khong trang tai lieu. Khong co
`ToolSpec` nao tro toi day (`server/api/inventory.py` giu nguyen). Nguoi goi la
ma CHAY TRONG nen tang (agent/workflow noi bo) da biet `owner_id` cua nguoi
dung ma no dang phuc vu.

## Mot duong, khong phai hai

Moi ham o day goi DUNG dich vu ma route HTML goi:

    submit_run  -> dich_vu_tao.dung_cai_dat -> features.tao_run_tu_ve     (routes.tao)
    get_status  -> quan_sat.dong_thoi_gian (ban khach)                     (routes.tien_do)
    cancel_run  -> features.huy_run                                        (routes.huy)
    retry_run   -> features.thu_lai_giai_doan                              (routes.thu_lai)
    get_result  -> features.khoa_ket_qua                                   (routes.tai_ket_qua)

⛔ Tep nay KHONG import giai doan, Voice, VLM hay FFmpeg (`test_2088` chot bang
   AST). Nguoi goi cong nay khong can — va khong duoc — biet chuoi giai doan.

## Giao dich

Moi ham ghi tu `commit` khi xong va `rollback` khi nem — y het route. Nguoi goi
nen dua mot session RIENG cho cong: rollback cua cong xoa ca thu dang cho trong
session ay.

## Ai duoc goi

Chua app nao. `tools/lint_app_contract.py` chan moi import `apps.auto_scan_video.*`
tu app khac tru ten da khai o `BE_MAT_CONG_KHAI` + `APP_DUOC_DUNG_APP`. Nguoi goi
dau tien them CA HAI ban khai (ten trong `TEN_CONG`) trong CUNG commit voi lan goi
that — `test_308` doi canh khai phai co nguoi dung that.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from platform_core import credit
from platform_core.i18n import _ as _t

from . import dich_vu_tao, features, quan_sat

#: Ten ma nguoi goi dau tien khai vao `BE_MAT_CONG_KHAI`. Cac kieu tra ve khong
#: can import — nguoi goi doc thuoc tinh.
TEN_CONG = ("submit_run", "get_status", "cancel_run", "retry_run", "get_result",
            "YeuCauChay", "LoiCongNoiBo")


# ══════════════════════════════════════════════════════════════════════════════
#  Loi co kieu
# ══════════════════════════════════════════════════════════════════════════════

class LoiCongNoiBo(Exception):
    """Goc moi loi cua cong. `ma` on dinh cho may doc; `str(loi)` cho nguoi doc."""

    ma = "loi"


class LoiDauVao(LoiCongNoiBo):
    """Dau vao sai. Tu choi TRUOC khi giu credit."""

    ma = "dau_vao_sai"


class LoiKhongTimThay(LoiCongNoiBo):
    """Khong co, HOAC khong phai cua `owner_id`. Co y khong phan biet (I6)."""

    ma = "khong_tim_thay"


class LoiThieuCredit(LoiCongNoiBo):
    ma = "thieu_credit"


class LoiXungDot(LoiCongNoiBo):
    """Trang thai khong cho phep (run da ket thuc, chua co ket qua, mo ho...)."""

    ma = "xung_dot"


class LoiChuaMo(LoiCongNoiBo):
    """Co `LTT_AUTO_SCAN_VIDEO` tat: san pham chua mo thi cong cung dong."""

    ma = "chua_mo"


# ══════════════════════════════════════════════════════════════════════════════
#  Kieu vao / ra
# ══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class YeuCauChay:
    """Mot yeu cau tao lan chay.

    `cai_dat` — ho so `cai_dat` chuan (khoa: `dich_vu_tao.KHOA_NHAN`), gom ca
    `ngon_ngu_nguon`/`ngon_ngu_dich`. Gia tri da giai (list/dict), khong phai
    chuoi form.

    Nguon: DUNG MOT trong hai.
      `upload_id`    — mot phien tai len CUA CHINH nguoi dung (app `auto_scan_video`).
      `nguon_run_id` — tai dung tep nguon cua mot run cu CUA CHINH nguoi dung.
    """

    cai_dat: Mapping
    upload_id: str = ""
    nguon_run_id: str = ""


@dataclass(frozen=True)
class PhieuChay:
    run_id: str
    trang_thai: str
    credit_giu: int
    cai_dat: Mapping


@dataclass(frozen=True)
class GiaiDoan:
    ten: str
    trang_thai: str


@dataclass(frozen=True)
class TrangThaiChay:
    run_id: str
    trang_thai: str            # queued | running | done | error | cancelled
    ket_thuc: bool
    phan_tram: int
    dang_chay: str
    giai_doan: tuple           # tuple[GiaiDoan, ...] theo thu tu chuoi
    giai_doan_hong: tuple      # tuple[str, ...]
    loi: str                   # MOT cau an toan cho khach, rong neu khong hong
    loi_co_ma: str
    co_ket_qua: bool
    credit_giu: int
    credit_tinh: int


@dataclass(frozen=True)
class KetQuaThuLai:
    run_id: str
    da_dat_lai: tuple          # giai doan da dat lai (giai doan + cac con cua no)


@dataclass(frozen=True)
class KetQuaChay:
    run_id: str
    khoa_video: str            # khoa kho; mo bang `platform_core.storage.get_storage().open`
    media_type: str = "video/mp4"


# ══════════════════════════════════════════════════════════════════════════════
#  Nam ham
# ══════════════════════════════════════════════════════════════════════════════

def _chu(owner_id) -> str:
    o = str(owner_id or "").strip()
    if not o:
        raise LoiDauVao(_t('Thiếu người dùng đang thực hiện.'))
    return o


def _lay(db, run_id: str, owner_id: str):
    try:
        return features.lay_run(db, str(run_id or ""), owner_id)
    except features.KhongTimThay as exc:
        raise LoiKhongTimThay(str(exc)) from None


def submit_run(db, owner_id: str, yeu_cau: YeuCauChay) -> PhieuChay:
    """Duyet -> giu credit -> tao run -> nop dieu phoi. Mot giao dich."""
    from platform_core.storage import get_storage

    owner_id = _chu(owner_id)
    if not dich_vu_tao.da_mo():
        raise LoiChuaMo(_t('Auto Scan Video chưa mở.'))
    if bool(yeu_cau.upload_id) == bool(yeu_cau.nguon_run_id):
        raise LoiDauVao(_t('Cần đúng một nguồn: upload_id hoặc nguon_run_id.'))
    try:
        # ⭐ Duyet TRUOC — cung ham voi route. Cap ngon ngu sai dung o day,
        #    chua co dong credit nao.
        ho_so = dich_vu_tao.dung_cai_dat(db, owner_id=owner_id,
                                         tho=dict(yeu_cau.cai_dat or {}))
        kho = get_storage()
        if yeu_cau.upload_id:
            run = features.tao_run_tu_ve(db, kho, owner_id=owner_id,
                                         upload_id=yeu_cau.upload_id,
                                         settings=ho_so)
        else:
            run = dich_vu_tao.tao_run_tu_run_cu(
                db, kho, owner_id=owner_id, run_id_nguon=yeu_cau.nguon_run_id,
                settings=ho_so)
        phieu = PhieuChay(run_id=run.id, trang_thai=run.status,
                          credit_giu=int(run.credit_held or 0),
                          cai_dat=dict(run.settings or {}))
        db.commit()
        return phieu
    except credit.ThieuCreditError as exc:
        db.rollback()
        raise LoiThieuCredit(str(exc) or _t('Không đủ credit.')) from None
    except features.KhongTimThay as exc:
        db.rollback()
        raise LoiKhongTimThay(str(exc)) from None
    except features.AsvError as exc:
        # LoiCaiDat, chinh sach media, ve tai len het han/sai: deu la dau vao.
        db.rollback()
        raise LoiDauVao(str(exc)) from None


def get_status(db, owner_id: str, run_id: str) -> TrangThaiChay:
    """Ban KHACH cua tien do — cung du lieu voi manh `tien-do` cua route."""
    from .tables import RUN_TERMINAL

    run = _lay(db, run_id, _chu(owner_id))
    dong = quan_sat.dong_thoi_gian(db, run)
    return TrangThaiChay(
        run_id=run.id, trang_thai=run.status,
        ket_thuc=run.status in RUN_TERMINAL,
        phan_tram=int(dong.get("phan_tram") or 0),
        dang_chay=str(dong.get("dang_chay") or ""),
        giai_doan=tuple(GiaiDoan(ten=m["giai_doan"], trang_thai=m["trang_thai"])
                        for m in dong["giai_doan"]),
        giai_doan_hong=tuple(dong.get("giai_doan_hong") or ()),
        loi=quan_sat.tom_tat_loi_cho_khach(db, run),
        loi_co_ma=str(dong.get("loi_co_ma") or ""),
        co_ket_qua=bool(features.khoa_ket_qua(db, run)),
        credit_giu=int(run.credit_held or 0),
        credit_tinh=int(run.credit_actual or 0))


def cancel_run(db, owner_id: str, run_id: str) -> TrangThaiChay:
    """Huy. Luy dang: huy mot run da ket thuc tra ve trang thai hien tai."""
    owner_id = _chu(owner_id)
    _lay(db, run_id, owner_id)
    try:
        features.huy_run(db, str(run_id), owner_id)
        db.commit()
    except features.AsvError as exc:
        db.rollback()
        raise LoiXungDot(str(exc)) from None
    return get_status(db, owner_id, run_id)


def retry_run(db, owner_id: str, run_id: str, giai_doan: str) -> KetQuaThuLai:
    """Chay lai MOT giai doan hong va cac giai doan an theo no."""
    from . import pipeline

    owner_id = _chu(owner_id)
    if str(giai_doan or "") not in pipeline.THEO_TEN:
        raise LoiDauVao(_t('Không có giai đoạn tên này.'))
    _lay(db, run_id, owner_id)
    try:
        ra = features.thu_lai_giai_doan(db, str(run_id), owner_id, str(giai_doan))
        db.commit()
    except features.KhongTimThay as exc:
        db.rollback()
        raise LoiKhongTimThay(str(exc)) from None
    except features.AsvError as exc:
        # Run da ket thuc, hoac dispatch mo ho can nguoi ket luan.
        db.rollback()
        raise LoiXungDot(str(exc)) from None
    return KetQuaThuLai(run_id=ra["run_id"], da_dat_lai=tuple(ra["da_dat_lai"]))


def get_result(db, owner_id: str, run_id: str) -> KetQuaChay:
    """Khoa kho cua video da long tieng. `LoiXungDot` khi chua co."""
    run = _lay(db, run_id, _chu(owner_id))
    khoa = features.khoa_ket_qua(db, run)
    if not khoa:
        raise LoiXungDot(_t('Lần chạy này chưa có kết quả.'))
    return KetQuaChay(run_id=run.id, khoa_video=khoa)

"""Dich vu TAO lan chay: MOT duong duyet dau vao cho ca route HTML lan cong noi bo.

## Vi sao tep nay ton tai (asv-final, lan `cong-noi-bo`, 22/09)

Truoc tep nay, toan bo phep duyet dau vao cua mot lan chay — che do thoi gian,
preset, cap ngon ngu, giong, vung che, cat dau/cuoi, lop phu, tu dien, phu de,
am thanh — nam **trong than handler `routes.tao`**. Cong noi bo
(`cong_noi_bo.py`) can dung dung phep duyet ay. Chep lai la hai ban cua mot
luat, va hai ban se lech: mot ben chan cap `vi -> vi`, ben kia quen.

⇒ Than duyet ha xuong day. `routes.tao` va `cong_noi_bo.submit_run` goi CUNG
  `dung_cai_dat`, va `test_2086` chot rang cung dau vao cho ra cung ho so.

## Ba luat

1. **Duyet XONG truoc khi giu credit.** Ham nay khong cham tien, khong tao run.
   Moi loi o day la mot `LoiCaiDat` — tuc tu choi o CUA, khong phai mot lan
   chay hong o phut thu muoi.
2. **Thu tu kiem va cau loi GIU NGUYEN nhu route cu.** Khach doc cau loi dau
   tien; doi thu tu la doi cau ho doc.
3. **Nhan ca chuoi JSON (form) lan gia tri da giai (cong noi bo).** Chuoi thi
   giai o day voi cau "khong doc duoc" cua tung truong; gia tri thi di thang vao
   cung ham `chuan_hoa`. Hai kieu dau vao, MOT phep duyet.
"""
from __future__ import annotations

import json
from typing import Mapping

from platform_core.i18n import _ as _t

from . import (am_thanh as am_thanh_mod, bien_tap as bien_tap_mod,
               nguon_loi as nguon_loi_mod,
               cai_dat as cai_dat_mod, cat_dau_cuoi,
               features, gia, hop_dong_v4, lop_phu as lop_phu_mod,
               ngon_ngu as ngon_ngu_mod, phu_de as phu_de_mod, rang_giong,
               tach_tieng as tach_tieng_mod,
               tu_dien as tu_dien_mod, vung_che)


#: Co mo san pham. Tai lieu day du o `routes.CO_MO`. O day vi CA route lan cong
#: noi bo cung doc no: san pham chua mo thi khong cua nao tao duoc lan chay.
CO_MO = "LTT_AUTO_SCAN_VIDEO"


def da_mo() -> bool:
    import os
    return str(os.environ.get(CO_MO, "")).strip() == "1"


class LoiCaiDat(features.AsvError):
    """Dau vao sai. Cau loi da viet cho khach doc. Nem TRUOC khi giu credit."""


#: Khoa ho so ma cua tao nhan. ⛔ `logo` KHONG co: logo di kem anh (multipart),
#: route tu doc va gan sau khi co run. `dac_diem_giong` khong co: chua cua nao
#: sinh ra no. `schema`/`voice_id` la khoa do `cai_dat.chuan_hoa` tu viet — nhan
#: lai de mot ho so doc tu run cu nop lai duoc nguyen ven.
#:
#: 🔑 **`nguon_loi` nam o day du no KHONG con la dieu khien nao** (Task 21,
#:    26/09). Chinh vi cau tren: mot ho so doc tu run cu nop lai phai di qua cua
#:    NGUYEN VEN. Bo ten nay khoi danh sach lam `dung_cai_dat` tu choi ho so cu
#:    voi cau *"Cai dat co truong la"* — tuc bien mot viec DON thanh mot loi cho
#:    khach. Gia tri duoc doc, ghi log, roi VUT (xem duoi).
KHOA_NHAN = frozenset({
    "timing_mode", "preset", "che_do_giong", "giong_id", "ngon_ngu_nguon",
    "ngon_ngu_dich", "vung", "cat", "lop_phu", "tu_dien", "phu_de", "am_thanh",
    "bien_tap", "nguon_loi", "lop",
    cai_dat_mod.KHOA_SCHEMA, cai_dat_mod.KHOA_BI_DANH_GIONG,
})


def _giai(v):
    """Chuoi -> JSON da giai (rong -> None); gia tri khac giu nguyen.

    Nem `ValueError` khi chuoi hong — nguoi goi doi no thanh cau cua truong.
    """
    if isinstance(v, str):
        return json.loads(v) if v.strip() else None
    return v


def _chuoi_json(v) -> str:
    """Gia tri da giai -> chuoi JSON cho cac `tu_form` (chi nhan chuoi)."""
    if v is None or v == "" or v == {}:
        return ""
    if isinstance(v, str):
        return v
    return json.dumps(v, ensure_ascii=False)


def _tu_dien(v) -> dict:
    """Van ban `Ten = cach doc` HOAC dict -> dict, qua CUNG `phan_tich`."""
    if isinstance(v, Mapping):
        dong = []
        for ten, doc in v.items():
            ten, doc = str(ten), str(doc)
            if tu_dien_mod.DAU in ten or "\n" in ten or "\n" in doc:
                raise LoiCaiDat(_t('Từ điển tên riêng không đọc được.'))
            dong.append(f"{ten} {tu_dien_mod.DAU} {doc}")
        v = "\n".join(dong)
    elif v is not None and not isinstance(v, str):
        raise LoiCaiDat(_t('Từ điển tên riêng không đọc được.'))
    try:
        return tu_dien_mod.phan_tich(v or "")
    except tu_dien_mod.TuDienLoi as exc:
        raise LoiCaiDat(str(exc)) from None


def dung_cai_dat(db, *, owner_id: str, tho: Mapping) -> dict:
    """Ho so THO cua mot yeu cau tao -> ho so chuan (`cai_dat.chuan_hoa`).

    Nem `LoiCaiDat`. Khong giu credit, khong tao run, khong commit.
    """
    tho = dict(tho or {})
    la = set(tho) - KHOA_NHAN
    if la:
        raise LoiCaiDat(_t('Cài đặt có trường lạ: {ds}.').format(
            ds=", ".join(sorted(la))))

    che_do = str(tho.get("timing_mode", gia.CHE_DO_MAC_DINH) or "")
    if not gia.che_do_hop_le(che_do):
        raise LoiCaiDat(_t('Chế độ thời gian không hợp lệ.'))

    # ⛔ Rong = mac dinh, **khong** = "nhan bua" (pha 21).
    preset = str(tho.get("preset") or "") or gia.preset_mac_dinh()
    if not gia.preset_hop_le(preset):
        raise LoiCaiDat(_t('Kiểu xử lý không hợp lệ.'))

    # ⭐ Cap ngon ngu kiem o CUA, truoc credit. Nguon `auto` thi TRANSCRIBE
    #    chot lai sau ASR (`ngon_ngu.kiem_nguon_da_doan`).
    try:
        nguon, dich = ngon_ngu_mod.kiem_cap(tho.get("ngon_ngu_nguon"),
                                            tho.get("ngon_ngu_dich"))
    except ngon_ngu_mod.NgonNguError as exc:
        raise LoiCaiDat(str(exc)) from None

    # ⛔ `nguon_loi` KHONG con la mot dieu khien (Task 21, 26/09): MOT duong duy
    #    nhat voice->voice. Khoa van nam trong `KHOA_NHAN` — xem chu thich o do —
    #    va di qua `chuan_che_do` de mot ho so cu mang `"ocr"`/`"embedded"`/`"auto"`
    #    duoc GHI MOT DONG LOG roi quy ve `asr`, ⛔ khong nem vao mat khach.
    #
    # ⛔ Khong tu choi gia tri la nua: khi chi con MOT duong thi "gia tri sai" va
    #    "gia tri cu" khong con phan biet duoc bang gia tri, va mot loi tu choi o
    #    day chi chan duoc chinh ho so ta vua sinh ra hom qua.
    nguon_loi_mod.chuan_che_do(tho.get("nguon_loi"))

    che_do_giong = (str(tho.get("che_do_giong") or "")
                    or hop_dong_v4.CHE_DO_GIONG_MAC_DINH)
    if not gia.che_do_giong_hop_le(che_do_giong):
        raise LoiCaiDat(_t('Cách chọn giọng không hợp lệ.'))

    giong_id = str(tho.get("giong_id") or "")
    bi_danh = str(tho.get(cai_dat_mod.KHOA_BI_DANH_GIONG) or "")
    if bi_danh and giong_id and bi_danh != giong_id:
        # ⛔ Hai ma giong khac nhau cho MOT lan chay — dung loi `voice_id`
        #    tung gay (viet cho giong nay, doc bang giong kia). Tu choi.
        raise LoiCaiDat(_t('Cách chọn giọng không hợp lệ.'))
    giong_id = giong_id or bi_danh

    # ⭐ Bat SOM, TRUOC khi giu credit (V6 pha 19). Xem `rang_giong.kiem_o_cua`.
    try:
        rang_giong.kiem_o_cua(db, owner_id=str(owner_id or ""),
                              che_do=che_do_giong, giong_id=giong_id,
                              ngon_ngu_dich=dich)
    except rang_giong.RangGiongError as exc:
        raise LoiCaiDat(str(exc)) from None

    try:
        ds_vung = vung_che.chuan_hoa(_giai(tho.get("vung")) or [])
    except vung_che.VungLoi as exc:
        raise LoiCaiDat(str(exc)) from None
    except (ValueError, TypeError):
        raise LoiCaiDat(_t('Vùng che không đọc được.')) from None

    try:
        cua_so_cat = cat_dau_cuoi.chuan_hoa(_giai(tho.get("cat")))
    except cat_dau_cuoi.CatLoi as exc:
        raise LoiCaiDat(str(exc)) from None
    except (ValueError, TypeError):
        raise LoiCaiDat(_t('Đoạn cắt không đọc được.')) from None
    # ⭐ CUNG mot cau voi cau giao dien hien khi khoa hai o (`asv-cat-chan`).
    if cua_so_cat and preset != hop_dong_v4.PRESET_CAT_THONG_MINH:
        raise LoiCaiDat(_t(
            'Kiểu “Giữ nguyên hình ảnh” hứa video ra dài đúng bằng video vào, '
            'nên không cắt bớt được. Chọn “Rút gọn có biên tập” nếu bạn muốn cắt.'))

    try:
        ds_lop_phu = lop_phu_mod.chuan_hoa(_giai(tho.get("lop_phu")) or [])
    except lop_phu_mod.LopPhuLoi as exc:
        raise LoiCaiDat(str(exc)) from None
    except (ValueError, TypeError):
        raise LoiCaiDat(_t('Lớp phủ chữ không đọc được.')) from None
    if ds_lop_phu and preset != hop_dong_v4.PRESET_CAT_THONG_MINH:
        raise LoiCaiDat(_t(
            'Kiểu “Giữ nguyên hình ảnh” sao chép nguyên vẹn từng điểm ảnh, nên '
            'không thể vẽ chữ lên hình. Chọn “Rút gọn có biên tập” nếu bạn muốn '
            'thêm lớp phủ chữ.'))

    bang_tu_dien = _tu_dien(tho.get("tu_dien"))

    cai_dat = {"timing_mode": che_do, "preset": preset,
               "che_do_giong": che_do_giong, "giong_id": giong_id,
               "ngon_ngu_nguon": "" if nguon == ngon_ngu_mod.TU_DOAN else nguon,
               "ngon_ngu_dich": dich,
               "vung": ds_vung,
               "tu_dien": bang_tu_dien,
               # ⚠️ Bi danh cu, xem `cai_dat.KHOA_BI_DANH_GIONG`.
               "voice_id": giong_id}
    # ⛔ L4 cua `cat_dau_cuoi` + luat `KHOA_THUA`: khong dung thi KHONG ghi khoa.
    #
    # 🔴 **`nguon_loi` ⛔ KHONG duoc ghi vao day nua** (Task 21, 26/09). Tu 23/09
    #    den `331b9ca3` no da tung bi duyet-roi-khong-ghi, va do la loi G-01. Nay
    #    no bi CO Y khong ghi vi mot ly do khac han: khong con gia tri nao de ghi.
    #    ⛔ Dung doc dong nay nhu mot lan tai pham G-01 — ban sua do la "kiem xong
    #    phai GHI", con day la "khong con gi de kiem".
    if cua_so_cat:
        cai_dat["cat"] = [cua_so_cat[0], cua_so_cat[1]]
    if ds_lop_phu:
        cai_dat["lop_phu"] = ds_lop_phu

    # ⛔ `phu_de.tu_form` chan truc DOT o preset giu hinh, nhung **khong** chan
    #    truc `.srt`. Am thanh khong cham diem anh: ca hai preset.
    try:
        ho_so_phu_de = phu_de_mod.tu_form(_chuoi_json(tho.get("phu_de")),
                                          preset=preset)
        ho_so_am = am_thanh_mod.tu_form(_chuoi_json(tho.get("am_thanh")))
        # Cat khung / zoom / ti le / toc do (asv-final, ADR_BIEN_TAP).
        ho_so_bt = bien_tap_mod.tu_form(_chuoi_json(tho.get("bien_tap")),
                                        preset=preset)
        # Ho so BA LOP nen: giong/nhac/vfx, moi lop bat/gain rieng (B2 + B5).
        ho_so_lop = tach_tieng_mod.tu_form_lop(_chuoi_json(tho.get("lop")))
    except (phu_de_mod.PhuDeLoi, am_thanh_mod.AmThanhLoi,
            bien_tap_mod.BienTapLoi, tach_tieng_mod.LopNenLoi) as exc:
        raise LoiCaiDat(str(exc)) from None
    if ho_so_phu_de:
        cai_dat["phu_de"] = ho_so_phu_de
    if ho_so_am:
        cai_dat["am_thanh"] = ho_so_am
    if ho_so_bt:
        cai_dat["bien_tap"] = ho_so_bt
    if ho_so_lop:
        cai_dat["lop"] = ho_so_lop

    return cai_dat_mod.chuan_hoa(cai_dat)


def tao_run_tu_run_cu(db, kho, *, owner_id: str, run_id_nguon: str,
                      settings: dict):
    """Tao run MOI tren TEP NGUON cua mot run cu CUA CHINH nguoi goi.

    🔑 Quyen so huu giai bang `features.lay_run(..., owner_id)` — mot khoa kho
       khong bao gio den tu nguoi goi. Dung duong soi + uoc gia + `tao_run` y
       het `features.tao_run_tu_ve`; chi khac la tep da nam o khoa ben.
    """
    from . import assets, nhap_media

    cu = features.lay_run(db, run_id_nguon, owner_id)
    if not cu.source_key or not kho.exists(cu.source_key):
        raise LoiCaiDat(_t('Tệp nguồn của lần chạy cũ không còn.'))
    try:
        tt = nhap_media.soi(assets.nguon_soi_duoc(kho, cu.source_key))
        nhap_media.kiem_chinh_sach(tt)
    except nhap_media.MediaError as exc:
        raise LoiCaiDat(str(exc)) from exc
    return features.tao_run(
        db, owner_id=owner_id, source_key=cu.source_key, settings=settings,
        uoc_luong_credit=gia.tinh_credit(float(tt.get("thoi_luong") or 0)))

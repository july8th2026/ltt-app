"""Giai doan VOICE_SYNTHESIS — doc ban dich thanh tieng, TUNG DOAN mot.

N artifact ra: mot tep WAV cho MOI doan, cong mot ban ke `voice_index.json`.

## Vi sao mot tep cho moi doan chu khong mot tep cho ca bai

TIMING dat **tung doan** vao dung khe thoi gian cua no. Mot tep lien mach thi
khong con cho de dat — va neu mot doan phai doc lai (dich sua, giong doi), ca
bai phai doc lai theo.

## Phuc hoi o muc DOAN — Prompt 12 muc 7 va cong thoat

Moi doan co van tay rieng (`giong_noi.van_tay_doan`), va khoa luu tru dan xuat
tu van tay do. Nen khi giai doan chay lai:

  * doan da co artifact **con song va con dung** -> BO QUA, khong goi lai,
    khong tra tien lan hai;
  * chi nhung doan con thieu moi duoc sinh.

⭐ Do la **hat nho nhat an toan** ma cong thoat doi. Hat nho hon (chia mot cau
   thanh hai luot) khong an toan: no doi mot doan thanh hai giong doc khac nhau
   o giua cau.

## Ban va mot dieu KHONG duoc lam o day

⛔ Prompt 12 cam ghep/canh thoi gian trong bo chuyen doi provider. Tep nay sinh
   ra cac doan tieng va **khong** ghep chung. Ghep la viec cua TIMING_ALIGN
   (pha 13), va tron vao day la giau mot quyet dinh timing ben trong mot lop
   provider — noi khong ai di tim no.
"""
from __future__ import annotations

import io
import json
import logging
import tempfile
import time
from pathlib import Path

from platform_core.i18n import _ as _t
from platform_core.storage import Storage

from . import (assets, giong_noi, lat_cat, nan_cho_vua, nan_thoi_luong,
               pipeline, su_dung, van_ban)
from .giai_doan_media import ThieuNguon

log = logging.getLogger(__name__)


class ThieuBanDich(ThieuNguon):
    """Giai doan dich chua sinh ra van ban."""


def _doc_ban_dich(db, kho: Storage, run) -> dict:
    """Van ban da xu ly cua run. Chi doc."""
    from . import features

    truoc = features.giai_doan_theo_ten(db, run.id, pipeline.CONTENT_PROCESS)
    khoa = next((k for k in ((truoc.outputs or {}).get("khoa_asset") or [])
                 if k.endswith(".json")), "") if truoc else ""
    if not khoa:
        raise ThieuBanDich(_t('Chưa có bản dịch để đọc thành tiếng.'))
    with kho.open(khoa) as f:
        tai_lieu = json.loads(f.read().decode("utf-8"))
    van_ban.kiem(tai_lieu)
    return tai_lieu


def chay(db, kho: Storage, *, run, ctx=None) -> dict:
    """Doc tung doan thanh tieng. Bo qua doan da co san va con dung."""
    if not giong_noi.san_sang():
        raise giong_noi.GiongError(
            _t('Máy tạo tiếng nói chưa được thiết lập trên máy chủ này.'))

    tai_lieu = _doc_ban_dich(db, kho, run)
    from . import cai_dat as cd
    cai = cd.doc(run)
    # Tu dien ten rieng cua khach; `{}` khi khong co. Xem `tu_dien.py`.
    tu_dien = dict(cai.tu_dien)

    # 🔴 **Giong lay tu BAN LONG TIENG, khong tu `settings`.**
    #
    #    Pha 14 dong bang giong vao tai lieu vi loi thoai duoc VIET CHO mot giong
    #    — xung ho, giong dieu, do trang trong deu bam vao no. Truoc pha 15, giai
    #    doan nay van tu doc `settings["voice_id"]`, tuc mot lan chay co the viet
    #    loi cho mot giong roi **doc len bang mot giong khac**, va khong cho nao
    #    bao loi vi ca hai deu tim thay mot gia tri hop le cua rieng minh.
    #
    # ⭐ Mot cau hoi ("giong nao?") phai co MOT cho tra loi.
    #
    # 🔴 **V6 pha 19 dong duong lui `or cai.giong_id`, va no KHONG vo hai.**
    #    Voi `AUTO_MATCH`, `settings.giong_id` RONG — giong duoc chot sau, tu ho
    #    so noi dung. Nen mot ban long tieng thieu `ma_giong` se roi xuong `""`,
    #    va `giai_giong("")` tra `(None, ...)`: khong giong tham chieu, tuc
    #    **giong mac dinh cua engine**, khong ai bam nut — dung loi D-V4-04 cam.
    #
    # ⭐ Moi ban long tieng hop le deu CO `ma_giong` (`long_tieng.kiem` doi no
    #    luc ghi), nen voi moi dau vao hop le dau ra khong doi mot byte. Chi dau
    #    vao THIEU truong nay — nay tu choi to thay vi doc bang giong khac.
    ma_giong = str(tai_lieu.get("ma_giong") or "")
    if not ma_giong:
        from .rang_giong import ChuaRangError

        raise ChuaRangError(_t(
            'Bản lồng tiếng không ghi giọng đã chọn — cần chạy lại bước xử lý '
            'nội dung.'))

    # Giai giong MOT LAN cho ca lan chay — day cung la noi quyen so huu giong
    # duoc kiem (I6/I7). Lam lai cho tung doan la N luot tra CSDL cho mot cau
    # tra loi khong doi.
    # 🔴 **`preset=cai_dat.get("preset")` la mot LOI, va no da lam moi lan chay
    #    that hong o dung day (A29-01).**
    #
    #    `settings["preset"]` la preset DUNG PHIM — `localize_preserve_picture`
    #    hay `smart_localize`. Con `ltt_voice.preset` nghia la TEN MOT GIONG
    #    DUNG SAN. Hai nghia cua cung mot tu, o hai app, va khong cho nao trong
    #    ma noi rang chung khac nhau. Do:
    #        giong_mau.hop_le("localize_preserve_picture") -> False
    #
    # ⇒ Khong co "voice preset" nao trong `settings` ca. Chi co MOT ma giong, va
    #   `giong_noi.tach_ma_giong` biet no thuoc o nao.
    #
    # 🔴 **W4': chot lan tren KICH BAN THAT, mot lan, TRUOC luot sinh dau tien.**
    #
    #    `giai_giong` dua van ban + `ngon_ngu_dich` KHAI trong ban long tieng cho
    #    `ltt_voice`, noi `lan_ngon_ngu.quyet_dinh` phan xu. Lech lan ⇒
    #    `GiongKhongHopLe(voice_language_mismatch)` truoc khi ton mot giay GPU.
    #
    # ⭐ Ca kich ban, khong tung doan: ban long tieng la MOT ngon ngu (no khai
    #    vay), va mot doan le chen mot cau trich tieng Anh khong duoc lam hong ca
    #    lan chay. Chot tung doan con doi N luot doc kho giong cho mot cau tra loi.
    muc_goc = list(tai_lieu.get("muc") or [])
    # ── GOP KHE (D5) — tang RIENG, TRUOC bac thang nan cho vua ─────────────
    #
    # 🔴 **Day la cho `gop_khe` DIEU KHIEN THAT, ⛔ khong con la mot con so bao
    #    cao.** Truoc 25/09 cho nay chi tinh `so_khe_neu_gop` roi vut.
    #
    # ⭐ Vi sao gop TRUOC: `nan_cho_vua` sua MOT CAU cho vua khe cua chinh no va
    #    ⛔ khong bao gio doi ranh gioi khe. `gop_khe` doi chinh cac KHE. Gop truoc
    #    ⇒ bac thang phan quyet tren mot khe RONG HON, nen no it phai goi model.
    #    Do tren luot that `asvr_9fc9cc89`: 106 -> 59 khe, khe trung vi 1,71 ->
    #    2,24 s, so doan bi phan quyet duoi mot am tiet 100/106 -> 39/59.
    #
    # ⛔ Mot khe gop van sinh **MOT** tep tieng, va `ban_ke` van co **MOT dong cho
    #    MOI `ma` goc** (`nan_thoi_luong.no_ban_ke`) — bat bien cua
    #    `giai_doan_thoi_gian.py:88-89` ⛔ khong bi pha. Va phu de van la mot o
    #    cho MOI `ma` goc: o phu de chi chua 84 ky tu, con tran gop la 220
    #    (`nan_thoi_luong.TRAN_KY_TU_GOP`).
    nhom = nan_thoi_luong.nhom_chi_so(
        _khe_bao_cao_tu_muc(muc_goc), tran_tang_toc=nan_cho_vua.tran_co_gian())
    muc = [_gop_mot_nhom([muc_goc[k] for k in g]) for g in nhom]

    ref_b64, preset = giong_noi.giai_giong(
        db, owner_id=run.owner_id, voice_id=ma_giong,
        van_ban="\n".join(str(m.get("chu") or "") for m in muc),
        ngon_ngu=str(tai_lieu.get("ngon_ngu_dich") or ""))

    phan: list[dict] = []
    ban_ke: list[dict] = []
    # 🔑 Doan bi vong sua goi DOC LAI (doc sai / khong vua): lay mot LUOT DOC
    #    MOI. Van tay cu = khoa cu = tep cu; khong muoi van tay thi "doc lai" tra
    #    ve dung ban da bi bao sai. Xem `_lan_doc_lai`.
    lan_lai = _lan_doc_lai(db, run)
    cac_nan: list[nan_cho_vua.KetQuaNan] = []
    # ⭐ Buoc 0.5 (25/09): MOI LUOT DOC mot dong — giay DO DUOC luc ay, khong phai
    #    giay cuoi cung. `cac_nan`/`tung_doan` chi giu giay sau khi da nan xong,
    #    nen truoc buoc nay khong ai tinh duoc mot ban sua nguong tiet kiem bao
    #    nhieu luot goi may B. Xem `nan_cho_vua.ban_ghi_luot_doc`.
    luot_doc: list[dict] = []
    da_sinh = 0
    # 🔑 **Hai dong ho, va thieu chung thi khong ai sua duoc giai doan nay.**
    #
    #    Luot nghiem thu nen v3 (23/09) do duoc `voice_synthesis` = 943 giay cho
    #    mot phim 107 giay va **khong tach duoc con so ay**: bao cao chi biet
    #    tong. Phai do lai ngoai duong san pham (`tools/do_toc_do_giong.py`) moi
    #    biet 751 giay la LLM viet lai chu khong phai may sinh tieng (241 giay).
    #
    # ⭐ Hai con so nay di vao `tom_tat`, tuc vao bang chung cua MOI luot chay
    #    ve sau. "Cham" khong con la mot cam giac.
    dong_ho = {"giay_tts": 0.0, "giay_llm_nan": 0.0}

    # 🔑 LAT CAT (`lat_cat.py`): ~2.000 doan cua 120 phut video khong vua MOT
    #    job. Don vi te nhat = (VONG_TOI_DA + 1) luot TTS + VONG_TOI_DA lan xin
    #    viet lai, moi cai o tran timeout cua lop goi.
    from . import ai as _ai
    lc = lat_cat.mo(db, run, pipeline.VOICE_SYNTHESIS,
                    du_phong_s=((nan_cho_vua.VONG_TOI_DA + 1) * _timeout_tts()
                                + nan_cho_vua.VONG_TOI_DA
                                * lat_cat.timeout_goi_ai(_ai.RUT_NGAN_CHO_VUA)
                                + lat_cat.DU_PHONG_NGOAI_GOI_S))
    da_lat = _doc_lat(db, run, lc) if lc.noi_tiep else {}

    with tempfile.TemporaryDirectory(prefix="asv-voice-") as tam:
        thu_muc = Path(tam)

        for i, m in enumerate(muc, start=1):
            if ctx is not None and getattr(ctx, "is_cancelled", None) and ctx.is_cancelled():
                raise giong_noi.GiongError(_t('Phiên chạy đã bị huỷ giữa chừng.'))
            if ctx is not None and getattr(ctx, "progress", None):
                ctx.progress(int(5 + 85 * i / max(1, len(muc))),
                             _t('Đang đọc thành tiếng'))
            # ⭐ Nhip tien do MANG BO DEM (log van hanh, 25/09) — khac `progress`
            #    o tren (bac thang % cho khach): day la con so THAT cho van
            #    hanh, tu nem qua `JobContext.progress_counter` neu thieu bo
            #    dem. Mac dinh 30s/5 don vi la du thua: do thuc te giai doan
            #    nay ~1.610s / ~67 doan (docs/NHAT_KY.md muc 7) — ~24s/doan —
            #    nen 5 don vi da vuot 30s, ra ~13 dong cho ca 27 phut.
            if ctx is not None and getattr(ctx, "progress_counter", None):
                ctx.progress_counter(i, len(muc), don_vi="doan")

            khe = nan_cho_vua.khe_cua(m)

            # ⭐ Doan DA SINH o luot truoc cua CUNG lat cat: dung lai y nguyen
            #    ban ke cua luot do (ke ca cau da nan + so vong). Di duong cache
            #    thuong se tra `tu_cu=True` va — voi doan da nan — tim theo van
            #    tay cau GOC nen khong thay, sinh lai: ban ra khac lan mot mach.
            lat = da_lat.get(str(m["ma"])) if (i - 1) < lc.vi_tri else None
            if lat is not None:
                kq = nan_cho_vua.ket_luan(
                    m["ma"], chu=str(lat["chu"]), giay=float(lat["giay"]),
                    khe=khe, so_vong=int(lat["so_vong"]))
                cac_nan.append(kq)
                # ⚠️ `lat["ban_ke"]` la mot DANH SACH tu 25/09 (mot khe gop tra
                #    ve nhieu dong). Ban ghi cu la mot dict — nhan ca hai, vi mot
                #    luot noi tiep co the doc diem chot cua luot truoc ban nang.
                _cu = lat["ban_ke"]
                ban_ke.extend(dict(x) for x in
                              (_cu if isinstance(_cu, list) else [_cu]))
                if lat.get("phan"):
                    phan.append(dict(lat["phan"]))
                da_sinh += int(lat.get("so_luot_doc") or 0)
                # ⭐ Lat cat truoc DA DOC that, chi khong phai trong luot nay:
                #    khong mang ban ghi sang thi bao cao cua mot video 120 phut
                #    (nhieu lat) chi noi ve lat cuoi.
                luot_doc.extend(dict(d) for d in (lat.get("luot_doc") or []))
                continue

            chu = str(m["chu"])
            so_vong = 0
            vt = _van_tay(m["ma"], chu, ma_giong, preset, tu_dien=tu_dien,
                          lan=lan_lai.get(m["ma"], 0))

            # ── Phuc hoi o muc DOAN ───────────────────────────────────────
            khoa_ben = assets.dat_khoa(owner_id=run.owner_id, run_id=run.id,
                                       stage=pipeline.VOICE_SYNTHESIS,
                                       van_tay=vt, duoi="wav")
            khoa_tam_cu = assets.khoa_staging(
                owner_id=run.owner_id, run_id=run.id,
                stage=pipeline.VOICE_SYNTHESIS, van_tay=vt, duoi="wav")
            cu = _doan_con_dung(db, kho, run, khoa_ben)
            if cu is None:
                # 🔴 **Mot doan con nam trong STAGING van la doan ta DA TRA TIEN.**
                #
                #    Doan tieng chi thanh `AsvAsset` o cuoi giai doan, khi
                #    `thi_hanh` promote ca lo. Nen mot lan truot o doan thu ba
                #    lam hai doan dau **mat het dau vet co the dung lai** —
                #    trong khi tep cua chung van nam nguyen trong kho duoi khoa
                #    staging, va so cai da ghi rang chung DA GIAO.
                #
                # ⭐ Do duoc o pha 23: mot lan truot o doan ba lam luot chay lai
                #    goi may sinh tieng **6 lan cho 3 doan**. Rang buoc
                #    `UNIQUE(run_id, ma_dispatch)` che mat dieu do — no chan lan
                #    GHI thu hai, khong chan lan LAM thu hai.
                #
                # ⛔ Khoa staging mang van tay cua chinh doan (chu + giong +
                #    preset), nen mot tep tim thay o day dung la tep cua doan
                #    nay chu khong phai cua mot lan chay khac; va no van bi do
                #    lai bang `kiem_tep_tieng` truoc khi duoc tin.
                cu = _doan_trong_staging(kho, khoa_tam_cu)
                if cu is not None:
                    phan.append({"staging_key": khoa_tam_cu, "kind": "audio",
                                 "duoi": "wav", "van_tay": vt})
            if cu is not None:
                kq = nan_cho_vua.ket_luan(m["ma"], chu=chu, giay=float(cu),
                                          khe=khe, so_vong=0)
                ban_ke.extend(nan_thoi_luong.no_ban_ke(
                    {"ma": m["ma"], "khoa": khoa_ben, "chu": chu,
                     "giay": float(cu), "tu_cu": True, **_ke_nan(kq)},
                    m["_thanh_vien"]))
                cac_nan.append(kq)
                continue

            lc.kiem(vi_tri=i - 1)
            sinh_truoc = da_sinh
            # Ban ghi rieng cua doan nay, de luot NOI TIEP dung lai duoc.
            luot_cua_doan: list[dict] = []

            # ── Bac thang nan cho vua (pha 15) ────────────────────────────
            #
            # ⛔ Vong nay co TRAN CUNG. Mot vong lap "sua cho toi khi vua" tren
            #    mot dich vu tra tien la mot hoa don khong co day.
            while True:
                _t0 = time.monotonic()
                wav, _headers = giong_noi.doc_mot_doan(
                    chu, ref_b64=ref_b64, preset=preset,
                    tu_dien_rieng=tu_dien or None)
                dong_ho["giay_tts"] += time.monotonic() - _t0
                # ⛔ Kiem TRUOC khi coi doan la xong (muc 8). Do tren TEP THAT,
                #    khong tin header cua may sinh tieng — cung ly do
                #    `apps/ltt_voice` doi chieu hai phia va ghi log khi lech.
                tep = thu_muc / f"{m['ma']}.wav"
                tep.write_bytes(wav)
                giay = giong_noi.kiem_tep_tieng(str(tep))
                da_sinh += 1
                # ⭐ Buoc 0.5: ghi NGAY sau khi do, TRUOC moi quyet dinh — mot
                #    dong so lieu them ⛔ khong duoc doi mot quyet dinh nao, nen
                #    no dung o day chu khong nam trong nhanh `if` nao.
                _bg = nan_cho_vua.ban_ghi_luot_doc(m["ma"], vong=so_vong,
                                                   giay=giay, khe=khe)
                luot_doc.append(_bg)
                luot_cua_doan.append(_bg)

                # 🔴 `nen_viet_lai`, KHONG `can_nan` (chot 25/09): mot doan qua
                #    NGAN van "khong vua" (no vao `tom_tat` nhu the), nhung
                #    ⛔ khong duoc goi model keo dai — `thoi_gian.lap_ke_hoach`
                #    da biet nuot khoang lang, va 0/5 he khao sat co ve nay.
                if not nan_cho_vua.nen_viet_lai(giay, khe):
                    break
                if so_vong >= nan_cho_vua.VONG_TOI_DA:
                    break

                # ⭐ Chi viet lai MOT doan. Sinh lai ca kich ban vi mot cau khong
                #    vua la dieu `V4_RESOURCE_CPU_GPU_POLICY` cam dich danh — va
                #    no cung lam hong hoa don cua ca tram cau con lai.
                _t0 = time.monotonic()
                try:
                    moi_chu = _viet_lai(db, run, m, chu=chu, giay=giay, khe=khe,
                                        so_vong=so_vong, ctx=ctx)
                except _KhongNanDuoc:
                    dong_ho["giay_llm_nan"] += time.monotonic() - _t0
                    break
                dong_ho["giay_llm_nan"] += time.monotonic() - _t0
                if moi_chu == chu:
                    # Model tra ve y nguyen: vong sau se cho ra dung ket qua nay.
                    break
                chu = moi_chu
                so_vong += 1
                vt = _van_tay(m["ma"], chu, ma_giong, preset,
                              tu_dien=tu_dien, lan=lan_lai.get(m["ma"], 0))

            kq = nan_cho_vua.ket_luan(m["ma"], chu=chu, giay=giay, khe=khe,
                                      so_vong=so_vong)
            cac_nan.append(kq)

            khoa_ben = assets.dat_khoa(owner_id=run.owner_id, run_id=run.id,
                                       stage=pipeline.VOICE_SYNTHESIS,
                                       van_tay=vt, duoi="wav")
            khoa_tam = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                                           stage=pipeline.VOICE_SYNTHESIS,
                                           van_tay=vt, duoi="wav")
            with open(tep, "rb") as f:
                kho.put(khoa_tam, f, content_type="audio/wav")

            phan_moi = {"staging_key": khoa_tam, "kind": "audio", "duoi": "wav",
                        "van_tay": vt}
            # ⭐ `chu` = cau CUOI CUNG may da doc (sau nan). `qc_do_luong` cham
            #    WER so voi chinh cau nay, khong phai cau truoc khi nan.
            # ⭐ MOT tep tieng, NHIEU dong `ban_ke` — mot dong cho MOI `ma` goc
            #    cua nhom, `giay` chia theo am tiet. Bat bien cua
            #    `giai_doan_thoi_gian.py:88-89` ⛔ khong bi pha.
            ke_moi = nan_thoi_luong.no_ban_ke(
                {"ma": m["ma"], "khoa": khoa_ben, "chu": chu, "giay": giay,
                 **_ke_nan(kq)},
                m["_thanh_vien"])
            phan.append(phan_moi)
            ban_ke.extend(ke_moi)

            # ⭐ Ghi so cai **mot lan cho moi doan da giao**, kem so giay THAT.
            #    `UNIQUE(run_id, ma_dispatch)` chan lan ghi thu hai neu giai doan
            #    chay lai — nen "dung mot lan" la mot rang buoc cua CSDL chu
            #    khong phai mot loi hua cua ma.
            _ghi_so(db, run, ma=m["ma"], van_tay=vt, giay=giay, kq=kq)
            su_dung.danh_dau_xong(db, run, stage=pipeline.VOICE_SYNTHESIS,
                                  item_key=m["ma"], fingerprint=vt,
                                  outputs={"khoa": khoa_ben, "giay": giay,
                                           "trang_thai": kq.trang_thai,
                                           "so_vong": kq.so_vong,
                                           # Du de luot noi tiep dung lai
                                           # y nguyen (xem `_doc_lat`).
                                           "lat": {"phien": lc.phien,
                                                   "chu": chu,
                                                   "giay": giay,
                                                   "so_vong": so_vong,
                                                   "so_luot_doc":
                                                       da_sinh - sinh_truoc,
                                                   # Buoc 0.5: ban ghi tung luot
                                                   # doc cua doan nay.
                                                   "luot_doc": luot_cua_doan,
                                                   "phan": phan_moi,
                                                   # ⚠️ DANH SACH tu 25/09: mot
                                                   # khe gop tra ve nhieu dong.
                                                   "ban_ke": ke_moi}})
            db.commit()
            lc.xong_mot()

        # ── Ban ke: cai TIMING doc de biet doan nao o dau ─────────────────
        goi = json.dumps({"schema": 1, "doan": ban_ke}, sort_keys=True,
                         ensure_ascii=False).encode("utf-8")
        vt_ke = assets.bam(goi)[:32]
        khoa_ke = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                                      stage=pipeline.VOICE_SYNTHESIS,
                                      van_tay=vt_ke, duoi="json")
        kho.put(khoa_ke, io.BytesIO(goi), content_type="application/json")
        phan.append({"staging_key": khoa_ke, "kind": "json", "duoi": "json",
                     "van_tay": vt_ke})

        # ⭐ Dem tren dong DAU cua moi nhom: mot tep = mot luot sinh. Dong di theo
        #    ⛔ khong phai mot doan "moi sinh" hay "dung lai" nao ca.
        ke_dau = [d for d in ban_ke if not nan_thoi_luong.la_dong_theo_sau(d)]
        return {
            "phan": phan,
            "tom_tat": {
                # 🔴 **HAI con so, ⛔ khong mot.** `nan_cho_vua.tom_tat` khai
                #    `so_doan` = so KHE DOC (= so tep tieng sinh ra); khoa duoi
                #    day khai so `ma` cua `content.json`. Tu khi `gop_khe` dieu
                #    khien that chung ⛔ khong con bang nhau, va gop chung lam mot
                #    la lam bao cao noi doi ve chi phi TTS.
                # ⛔ Va ⛔ KHONG ghi de `so_doan` o day: mot khoa hai chu so huu la
                #    dung cai bay kho nay da tra gia (`test_4700` chot).
                "so_ma_noi_dung": len(muc_goc),
                "so_khe_da_gop": sum(1 for g in nhom if len(g) > 1),
                # ⚠️ **Hai con so, khong phai mot.** `so_doan_moi_sinh` dem DOAN;
                #    `so_luot_doc` dem LUOT GOI may sinh tieng — mot doan phai
                #    nan hai vong la ba luot. Gop chung lam mot se lam bao cao
                #    chi phi noi doi ngay o cho no quan trong nhat, va lam mat
                #    mot menh de ma `test_409` da chot dung.
                "so_doan_moi_sinh": len(muc) - sum(1 for d in ke_dau
                                                   if d.get("tu_cu")),
                "so_luot_doc": da_sinh,
                "so_doan_dung_lai": sum(1 for d in ke_dau if d.get("tu_cu")),
                # ⭐ `giay_tep` cua dong dau = do dai THAT ca tep; `giay` cua no
                #    chi la PHAN cua rieng no. Cong `giay` cua moi dong cung ra
                #    dung tong ay (`chia_giay` bao toan tong), nhung cong
                #    `giay_tep` la cong mot con so mot lan cho moi nhom — ro rang
                #    hon, va ⛔ khong phu thuoc vao phep chia.
                "tong_giay": round(sum(float(d.get("giay_tep") or d["giay"])
                                       for d in ke_dau), 2),
                # ⭐ Xem `dong_ho` o dau ham: hai con so nay tra loi *"giai doan
                #    nay cham vi cai gi"* ma khong phai do lai ngoai san pham.
                "giay_tts": round(dong_ho["giay_tts"], 2),
                "giay_llm_nan": round(dong_ho["giay_llm_nan"], 2),
                "preset": str(preset or ""),
                "ma_giong": ma_giong,
                **nan_cho_vua.tom_tat(cac_nan, tung_luot_doc=luot_doc),
            },
        }


def _khe_bao_cao_tu_muc(muc: list[dict]) -> list[nan_thoi_luong.Khe]:
    """`muc` (danh sach doan cua `content.json`) -> `Khe` cho `gop_khe`.

    ⭐ `moc_sau` = `bat` cua doan KE TIEP trong `muc`: moi doan trong `muc` da
       la `for_dubbing=True` (`ban_bien_tap.doan_giu_lai` loc doan bi cat truoc
       do, o CONTENT_PROCESS) — dung dinh nghia "bien co that ke tiep" cua
       open-dubbing ma `nan_thoi_luong.Khe` doi hoi, khong phai mot hang so.
       Doan CUOI khong co doan sau de muon: lay chinh `ket` cua no (ngan_sach_s
       = khe_s, khong muon).

    `am_tiet` dem theo dung dinh nghia da co san cua kho nay
    (`ngon_ngu.py:47-49`: tieng Viet — dem TU cach nhau boi khoang trang la
    dem AM TIET, "cung mot phep"), khong phai mot cach dem moi bia ra.
    """
    n = len(muc)
    ra: list[nan_thoi_luong.Khe] = []
    for i, m in enumerate(muc):
        bat = float(m.get("bat") or 0.0)
        ket = max(bat, float(m.get("ket") or 0.0))
        moc_sau = float(muc[i + 1].get("bat") or ket) if i + 1 < n else ket
        chu = str(m.get("chu") or "")
        ra.append(nan_thoi_luong.Khe(
            ma=str(m.get("ma") or ""), bat=bat, ket=ket,
            moc_sau=max(moc_sau, ket), am_tiet=len(chu.split()), chu=chu))
    return ra


def _gop_mot_nhom(thanh_vien: list[dict]) -> dict:
    """Mot NHOM muc lien ke -> mot muc "khe da gop" de DOC mot luot.

    ⭐ `ma` cua thanh vien DUNG DAU duoc dung lam `ma` cua ca nhom — ⛔ khong bia
       ra mot `ma` moi. So cai (`UNIQUE(run_id, ma_dispatch)`), diem chot
       (`su_dung.danh_dau_xong`) va van tay tep deu bam vao `ma`, nen mot `ma`
       tong hop se la mot khoa ⛔ khong doi chieu duoc voi `content.json`.

    ⭐ `_thanh_vien` mang theo CAC MUC GOC — `no_ban_ke` can `chu` va `bat`/`ket`
       cua tung `ma` de tra lai mot dong `ban_ke` cho moi cai.

    ⛔ Nhom mot thanh vien tra ve mot ban SAO co `_thanh_vien` do dai 1, ⛔ khong
       phai chinh `muc` goc: mot hinh dang duy nhat cho ca hai ca thi nguoi doc
       xuoi dong ⛔ khong phai hoi "cai nay co `_thanh_vien` khong".
    """
    dau = thanh_vien[0]
    return {**dau,
            "chu": " ".join(str(m.get("chu") or "") for m in thanh_vien).strip(),
            "goc": " ".join(str(m.get("goc") or "") for m in thanh_vien).strip(),
            "bat": float(dau.get("bat") or 0.0),
            "ket": float(thanh_vien[-1].get("ket") or 0.0),
            "_thanh_vien": [dict(m) for m in thanh_vien]}


def _timeout_tts() -> float:
    """Tran timeout cua MOT luot TTS: mac dinh cua `sidecar_client.noi`, vi
    `giong_noi.doc_mot_doan` -> `ltt_voice.features.goi_cong` khong truyen
    `timeout` (xem docstring `goi_cong`)."""
    from apps.ltt_voice import sidecar_client

    return lat_cat.mac_dinh_tham_so(sidecar_client.noi, "timeout")


def _doc_lat(db, run, lc) -> dict:
    """`{ma_doan: ban ghi lat}` cua cac doan da sinh o luot truoc CUNG phien."""
    from . import features

    ra: dict = {}
    for it in features.cac_don_vi(db, run.id, pipeline.VOICE_SYNTHESIS):
        lat = (it.outputs or {}).get("lat")
        if isinstance(lat, dict) and lat.get("phien") == lc.phien:
            ra[str(it.item_key)] = lat
    return ra


class _KhongNanDuoc(RuntimeError):
    """Khong xin duoc cau viet lai — dung bac thang o day, khong lam hong ca run."""


def _lan_doc_lai(db, run) -> dict[str, int]:
    """`{ma: so vong sua da dat lai doan nay o voice_synthesis}` — tu SO CAI.

    Doc cac dong vong sua (`jobs.NANG_LUC_VONG_SUA`) ma `_sua_chua_neu_can` ghi
    TRUOC khi dat lai: mot con so ben qua worker chet, va la ham cua du lieu
    da ghi chu khong phai cua mot bo dem trong bo nho.
    """
    from . import sua_chua
    from .jobs import DON_VI_SUA, NANG_LUC_VONG_SUA

    ke = [dict(getattr(d, "ghi_chu", None) or {})
          for d in su_dung.cac_dong(db, run, stage=pipeline.QC, item_key=DON_VI_SUA)
          if d.nang_luc == NANG_LUC_VONG_SUA]
    return sua_chua.lan_doc_lai(ke)


def _van_tay(ma: str, chu: str, ma_giong: str, preset: str, *,
             tu_dien: dict, lan: int = 0) -> str:
    """Van tay cua MOT doan tieng.

    🔑 Gom **van ban da nan** chu khong phai van ban goc: sau mot vong nan, doan
       nay la ket qua cua mot cau KHAC, va dung lai tep cu la giao mot cau ma ta
       vua quyet dinh la khong vua.
    """
    vt = giong_noi.van_tay_doan(ma_doan=ma, chu=chu, voice_id=ma_giong,
                                preset=str(preset or ""),
                                tu_dien=tu_dien or None)
    if not lan:
        # ⛔ `lan=0` giu NGUYEN van tay cu: moi doan chua tung bi sua dung lai
        #    cache y nhu truoc.
        return vt
    import hashlib
    return hashlib.sha256(f"{vt}|doc_lai:{int(lan)}".encode()).hexdigest()[:len(vt)]


def _ke_nan(kq) -> dict:
    """Phan cua ban ke ma TIMING doc de biet doan nao can co gian."""
    d = {"khe": round(kq.khe, 3), "trang_thai_nan": kq.trang_thai,
         "so_vong_nan": kq.so_vong}
    if kq.he_so_co_gian and kq.he_so_co_gian != 1.0:
        d["he_so_co_gian"] = kq.he_so_co_gian
    return d


def _viet_lai(db, run, m: dict, *, chu: str, giay: float, khe: float,
              so_vong: int, ctx=None) -> str:
    """Nho model viet lai MOT cau cho vua khe. Nem `_KhongNanDuoc` neu khong duoc.

    ⛔ Mot lan xin viet lai hong **khong duoc** lam hong ca giai doan: cau hien
       tai van doc duoc, chi la khong vua — va bac thang con mot nac nua (co
       gian) truoc khi phai bo cuoc. Nen loi o day dung o day.
    """
    from . import ai, cai_dat as cd

    try:
        kq = ai.goi_tinh_tien(
            db, run, ai.RUT_NGAN_CHO_VUA,
            nan_cho_vua.loi_nhac_nan(m, chu_hien_tai=chu, giay_do_duoc=giay,
                                     khe=khe,
                                     ngon_ngu_dich=cd.doc(run).ngon_ngu_dich),
            stage=pipeline.VOICE_SYNTHESIS,
            item_key=f"nan:{m['ma']}:{so_vong}", ctx=ctx)
        # 🔴 Cung mot loi voi `giai_doan_noi_dung`, tim ra o pha 22: `noi_dung`
        #    la CHUOI phan hoi tho cua model, va `doc_nan` goi `.get` tren no.
        #    `ai.doc_ket_qua` la buoc doc-va-kiem-luoc-do bi bo quen o ca hai
        #    cho. (Truoc 09/09 no la `ai.doc_json(kq.get("noi_dung") ...)`, va
        #    cach boc ay vut mat `finish_reason` — xem `ai._vi_sao_rong`.)
        return nan_cho_vua.doc_nan(
            ai.doc_ket_qua(kq, ai.RUT_NGAN_CHO_VUA))
    except (ai.AiError, ai.AiMoHo, giong_noi.MayBan,
            nan_cho_vua.NanError) as exc:
        # 🔴 **`MayBan` PHAI nam trong danh sach nay, va no tung khong.**
        #
        #    06/09 mot ban va o `ai.goi` doi may-ban tu `AiError` sang `MayBan`
        #    de nen tang doc duoc "cho tai nguyen" thay vi "that bai". Dung o
        #    tang do — nhung `MayBan` ke thua `RuntimeError`, KHONG ke thua
        #    `AiError`, nen tu do no **lot qua** tay bat nay.
        #
        # \u26d4 Hau qua do duoc o luot nghiem thu 07/09 16:58:
        #    `voice_synthesis failed_terminal | ltt_llm: ban` — dung dieu
        #    docstring ngay tren cam: *"mot lan xin viet lai hong khong duoc lam
        #    hong ca giai doan"*. Mot ban va o tang duoi doi hanh vi o tang tren
        #    ma khong ai rà, vi phep kiem cua no chi do tang duoi.
        #
        # \u2b50 Va bo nac rut ngan KHONG im lang: `nan_cho_vua.ket_luan` xep doan
        #    vao `VUA` / `CO_GIAN` / `CAN_SUA`, ca ba deu vao `tom_tat`, va
        #    `CAN_SUA` chay thang vao vong sua. Nen "may ban -> xuong nac co
        #    gian" la suy giam CO GHI SO, khong phai mat mat am tham.
        #
        # \u26a0\ufe0f Vi sao KHONG de no bay len de job duoc hoan: `voice_synthesis`
        #    la giai doan DAI NHAT va no khong khai `llm_remote`, nen hoan ca
        #    giai doan vi mot cau khong rut ngan duoc la vut di toan bo tieng da
        #    doc trong luot do. Bac thang nan sinh ra dung de xu ly ca nay.
        log.info("khong nan duoc doan %s: %s", m.get("ma"), exc)
        raise _KhongNanDuoc(str(exc)) from exc


def _ghi_so(db, run, *, ma: str, van_tay: str, giay: float, kq) -> None:
    """Ghi MOT dong so cai cho mot doan tieng DA GIAO.

    ⭐ Don vi la **giay**, khong phai luot: khach tra tien cho do dai tieng noi
       duoc sinh ra, va mot doan dai gap ba lan mot doan khac thi khong the tinh
       bang nhau. `su_dung.GIAY` co san cho viec do.
    """
    try:
        su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key=ma,
                    su_dung=su_dung.SuDung(
                        nang_luc="tong_hop_tieng", app_chu="ltt_voice",
                        trang_thai=su_dung.DA_GIAO, don_vi=su_dung.GIAY,
                        so_luong=float(giay), credit=0,
                        ma_dispatch=f"giong:{ma}:{van_tay[:16]}",
                        ghi_chu={"trang_thai_nan": kq.trang_thai,
                                 "so_vong": kq.so_vong}))
    except su_dung.DaGhiRoi:
        # ⭐ Rang buoc `UNIQUE(run_id, ma_dispatch)` vua chan mot lan tinh tien
        #    thu hai cho cung mot doan. Do la thanh cong, khong phai loi.
        log.info("so cai da co doan tieng %s - bo qua lan ghi trung", ma)


def _doan_trong_staging(kho: Storage, khoa_tam: str):
    """So giay cua mot doan con nam trong staging, hoac None.

    Khong doi mot ban ghi `AsvAsset` — do la thu chua kip ghi khi giai doan
    truot giua chung. Nhung van **do lai tren tep that**: mot tep dang do trong
    kho trong y het mot tep xong.
    """
    try:
        if not kho.exists(khoa_tam):
            return None
        duong = kho.local_path(khoa_tam) if hasattr(kho, "local_path") else None
        if not duong:
            return None
        return giong_noi.kiem_tep_tieng(duong)
    except Exception as loi_doc:    # noqa: BLE001 - khong doc duoc = khong dung lai
        # ⛔ Khong nuot im: mot tep staging khong doc duoc **khong** phai su co
        #    (ta chi don gian sinh lai doan do), nhung neu no xay ra o MOI doan
        #    thi phep dung lai da chet mot cach im lang va hoa don tang len ma
        #    khong ai thay. Mot dong log la thu duy nhat phan biet hai canh do.
        log.info("khong dung lai duoc doan trong staging %s (%s)",
                 khoa_tam, type(loi_doc).__name__)
        return None


def _doan_con_dung(db, kho: Storage, run, khoa: str):
    """Thoi luong cua mot doan da co san VA con dung, hoac None.

    Hai dieu kien, ca hai bat buoc (I10): ban ghi con, **va** tep con song va
    con dung checksum. "Co mot tep dung ten" khong phai la cache hop le (O13).
    """
    from .tables import ASSET_OK, AsvAsset
    from sqlalchemy import select

    row = db.execute(select(AsvAsset).where(
        AsvAsset.storage_key == khoa,
        AsvAsset.owner_id == run.owner_id)).scalars().first()
    if row is None:
        return None
    if assets.kiem_toan_ven(db, kho, row) != ASSET_OK:
        return None
    duong = kho.local_path(khoa) if hasattr(kho, "local_path") else None
    if not duong:
        return 0.0      # khong doc duoc duong dan cuc bo: tin ban ghi da kiem
    try:
        return giong_noi.kiem_tep_tieng(duong)
    except giong_noi.GiongError:
        return None

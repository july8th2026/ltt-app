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
from pathlib import Path

from platform_core.i18n import _ as _t
from platform_core.storage import Storage

from . import (assets, giong_noi, long_tieng, nan_cho_vua, pipeline,
               su_dung, van_ban)
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
    cai_dat = run.settings or {}

    # 🔴 **Giong lay tu BAN LONG TIENG, khong tu `settings`.**
    #
    #    Pha 14 dong bang giong vao tai lieu vi loi thoai duoc VIET CHO mot giong
    #    — xung ho, giong dieu, do trang trong deu bam vao no. Truoc pha 15, giai
    #    doan nay van tu doc `settings["voice_id"]`, tuc mot lan chay co the viet
    #    loi cho mot giong roi **doc len bang mot giong khac**, va khong cho nao
    #    bao loi vi ca hai deu tim thay mot gia tri hop le cua rieng minh.
    #
    # ⭐ Mot cau hoi ("giong nao?") phai co MOT cho tra loi. `settings` chi con la
    #    duong lui cho nhung run cu chua co truong nay.
    ma_giong = str(tai_lieu.get("ma_giong") or cai_dat.get("voice_id") or "")

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
    ref_b64, preset = giong_noi.giai_giong(
        db, owner_id=run.owner_id, voice_id=ma_giong)

    muc = list(tai_lieu.get("muc") or [])
    phan: list[dict] = []
    ban_ke: list[dict] = []
    cac_nan: list[nan_cho_vua.KetQuaNan] = []
    da_sinh = 0

    with tempfile.TemporaryDirectory(prefix="asv-voice-") as tam:
        thu_muc = Path(tam)

        for i, m in enumerate(muc, start=1):
            if ctx is not None and getattr(ctx, "is_cancelled", None) and ctx.is_cancelled():
                raise giong_noi.GiongError(_t('Phiên chạy đã bị huỷ giữa chừng.'))
            if ctx is not None and getattr(ctx, "progress", None):
                ctx.progress(int(5 + 85 * i / max(1, len(muc))),
                             _t('Đang đọc thành tiếng'))

            khe = nan_cho_vua.khe_cua(m)
            chu = str(m["chu"])
            so_vong = 0
            vt = _van_tay(m["ma"], chu, ma_giong, preset)

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
                ban_ke.append({"ma": m["ma"], "khoa": khoa_ben,
                               "giay": float(cu), "tu_cu": True,
                               **_ke_nan(kq)})
                cac_nan.append(kq)
                continue

            # ── Bac thang nan cho vua (pha 15) ────────────────────────────
            #
            # ⛔ Vong nay co TRAN CUNG. Mot vong lap "sua cho toi khi vua" tren
            #    mot dich vu tra tien la mot hoa don khong co day.
            while True:
                wav, _headers = giong_noi.doc_mot_doan(chu, ref_b64=ref_b64,
                                                       preset=preset)
                # ⛔ Kiem TRUOC khi coi doan la xong (muc 8). Do tren TEP THAT,
                #    khong tin header cua may sinh tieng — cung ly do
                #    `apps/ltt_voice` doi chieu hai phia va ghi log khi lech.
                tep = thu_muc / f"{m['ma']}.wav"
                tep.write_bytes(wav)
                giay = giong_noi.kiem_tep_tieng(str(tep))
                da_sinh += 1

                if not nan_cho_vua.can_nan(giay, khe):
                    break
                if so_vong >= nan_cho_vua.VONG_TOI_DA:
                    break

                # ⭐ Chi viet lai MOT doan. Sinh lai ca kich ban vi mot cau khong
                #    vua la dieu `V4_RESOURCE_CPU_GPU_POLICY` cam dich danh — va
                #    no cung lam hong hoa don cua ca tram cau con lai.
                try:
                    moi_chu = _viet_lai(db, run, m, chu=chu, giay=giay, khe=khe,
                                        so_vong=so_vong, ctx=ctx)
                except _KhongNanDuoc:
                    break
                if moi_chu == chu:
                    # Model tra ve y nguyen: vong sau se cho ra dung ket qua nay.
                    break
                chu = moi_chu
                so_vong += 1
                vt = _van_tay(m["ma"], chu, ma_giong, preset)

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

            phan.append({"staging_key": khoa_tam, "kind": "audio", "duoi": "wav",
                         "van_tay": vt})
            ban_ke.append({"ma": m["ma"], "khoa": khoa_ben, "giay": giay,
                           **_ke_nan(kq)})

            # ⭐ Ghi so cai **mot lan cho moi doan da giao**, kem so giay THAT.
            #    `UNIQUE(run_id, ma_dispatch)` chan lan ghi thu hai neu giai doan
            #    chay lai — nen "dung mot lan" la mot rang buoc cua CSDL chu
            #    khong phai mot loi hua cua ma.
            _ghi_so(db, run, ma=m["ma"], van_tay=vt, giay=giay, kq=kq)
            su_dung.danh_dau_xong(db, run, stage=pipeline.VOICE_SYNTHESIS,
                                  item_key=m["ma"], fingerprint=vt,
                                  outputs={"khoa": khoa_ben, "giay": giay,
                                           "trang_thai": kq.trang_thai,
                                           "so_vong": kq.so_vong})
            db.commit()

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

        return {
            "phan": phan,
            "tom_tat": {
                "so_doan": len(muc),
                # ⚠️ **Hai con so, khong phai mot.** `so_doan_moi_sinh` dem DOAN;
                #    `so_luot_doc` dem LUOT GOI may sinh tieng — mot doan phai
                #    nan hai vong la ba luot. Gop chung lam mot se lam bao cao
                #    chi phi noi doi ngay o cho no quan trong nhat, va lam mat
                #    mot menh de ma `test_409` da chot dung.
                "so_doan_moi_sinh": len(muc) - sum(1 for d in ban_ke if d.get("tu_cu")),
                "so_luot_doc": da_sinh,
                "so_doan_dung_lai": sum(1 for d in ban_ke if d.get("tu_cu")),
                "tong_giay": round(sum(float(d["giay"]) for d in ban_ke), 2),
                "preset": str(preset or ""),
                "ma_giong": ma_giong,
                **nan_cho_vua.tom_tat(cac_nan),
            },
        }


class _KhongNanDuoc(RuntimeError):
    """Khong xin duoc cau viet lai — dung bac thang o day, khong lam hong ca run."""


def _van_tay(ma: str, chu: str, ma_giong: str, preset: str) -> str:
    """Van tay cua MOT doan tieng.

    🔑 Gom **van ban da nan** chu khong phai van ban goc: sau mot vong nan, doan
       nay la ket qua cua mot cau KHAC, va dung lai tep cu la giao mot cau ma ta
       vua quyet dinh la khong vua.
    """
    return giong_noi.van_tay_doan(ma_doan=ma, chu=chu, voice_id=ma_giong,
                                  preset=str(preset or ""))


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
    from . import ai

    try:
        kq = ai.goi_tinh_tien(
            db, run, ai.RUT_NGAN_CHO_VUA,
            nan_cho_vua.loi_nhac_nan(m, chu_hien_tai=chu, giay_do_duoc=giay,
                                     khe=khe),
            stage=pipeline.VOICE_SYNTHESIS,
            item_key=f"nan:{m['ma']}:{so_vong}", ctx=ctx)
        # 🔴 Cung mot loi voi `giai_doan_noi_dung`, tim ra o pha 22: `noi_dung`
        #    la CHUOI phan hoi tho cua model, va `doc_nan` goi `.get` tren no.
        #    `ai.doc_json` la buoc doc-va-kiem-luoc-do bi bo quen o ca hai cho.
        return nan_cho_vua.doc_nan(
            ai.doc_json(kq.get("noi_dung") or "", ai.RUT_NGAN_CHO_VUA))
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

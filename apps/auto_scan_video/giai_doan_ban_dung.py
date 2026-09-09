"""Giai doan COMPOSE — dung ban dung, va doi chieu MOI tham chieu truoc render.

Mot artifact ra:

    render_manifest.json   ban dung   (kind=json)

⛔ Giai doan nay **khong sinh media**. Prompt 14 cam ro, va ly do la ranh gioi
   G9: tron bien tap vao thi hanh nghia la mot lan doi cong cu render keo theo
   mot lan chay lai ca chuoi AI o thuong nguon.

## Viec that su cua giai doan nay

Dung mot tai lieu thi de. Phan dat gia la **doi chieu moi tham chieu TRUOC khi
ton mot suat render** (Prompt 14 muc 5):

  * moi khoa trong ban dung phai tro toi mot `AsvAsset` **cua chinh chu so huu**;
  * moi artifact do phai con song va con dung checksum;
  * moi doan trong ke hoach phai co mot tep tieng that.

Mot ban dung tro toi mot artifact khong con la mot lan render that bai o phut
thu muoi — sau khi da chiem suat, da tai tep, da giai ma. Bat o day ton vai mili
giay.
"""
from __future__ import annotations

import io
import json

from platform_core.i18n import _ as _t
from platform_core.storage import Storage

from . import assets, ban_dung, nhap_media, pipeline, thoi_gian
from .giai_doan_media import ThieuNguon
from .tables import ASSET_OK


class ThieuDauVao(ThieuNguon):
    """Thieu mot trong cac tai lieu thuong nguon."""


def _khoa_json(db, run, ten_giai_doan: str) -> str:
    from . import features
    s = features.giai_doan_theo_ten(db, run.id, ten_giai_doan)
    return next((k for k in ((s.outputs or {}).get("khoa_asset") or [])
                 if k.endswith(".json")), "") if s else ""


def _khoa_theo_duoi(db, run, ten_giai_doan: str, duoi: str) -> str:
    from . import features
    s = features.giai_doan_theo_ten(db, run.id, ten_giai_doan)
    return next((k for k in ((s.outputs or {}).get("khoa_asset") or [])
                 if k.endswith(duoi)), "") if s else ""


def _doc(kho: Storage, khoa: str) -> dict:
    with kho.open(khoa) as f:
        return json.loads(f.read().decode("utf-8"))


def _khoa_master(db, kho, run) -> str:
    """Khoa ban phoi am do pha 16 sinh ra o `TIMING_ALIGN`.

    ⛔ Thieu no thi trinh render khong co tieng. Bat o day — luc dung ban dung —
       chu khong o giua mot luot ffmpeg da chiem suat render.
    """
    from . import features, pipeline

    gd = features.giai_doan_theo_ten(db, run.id, pipeline.TIMING_ALIGN)
    khoa = [k for k in (((gd.outputs or {}) if gd else {}).get("khoa_asset") or [])
            if str(k).endswith(".wav")]
    if not khoa:
        raise ban_dung.BanDungError(_t('Chưa có bản phối âm để dựng bản dựng.'))
    return khoa[0]


def _khoa_con_dung(db, kho: Storage, run) -> set[str]:
    """Moi khoa artifact CUA CHINH chu so huu, da kiem toan ven.

    ⭐ Kiem toan ven **o day**, khong tin cot `integrity` da luu: ban ghi noi
       `ok` tu lan kiem truoc, con tep thi co the da bien mat trong khoang giua.
    """
    from sqlalchemy import select

    from .tables import AsvAsset

    hang = db.execute(select(AsvAsset).where(
        AsvAsset.run_id == run.id,
        AsvAsset.owner_id == run.owner_id)).scalars().all()
    return {a.storage_key for a in hang
            if assets.kiem_toan_ven(db, kho, a) == ASSET_OK}


def chay(db, kho: Storage, *, run, ctx=None) -> dict:
    """Doc ke hoach + ban ke tieng -> ban dung, da doi chieu day du."""
    khoa_kh = _khoa_json(db, run, pipeline.TIMING_ALIGN)
    if not khoa_kh:
        raise ThieuDauVao(_t('Chưa có kế hoạch thời gian để dựng.'))
    khoa_ke = _khoa_json(db, run, pipeline.VOICE_SYNTHESIS)
    if not khoa_ke:
        raise ThieuDauVao(_t('Chưa có bản kê tiếng để dựng.'))
    khoa_nen = _khoa_theo_duoi(db, run, pipeline.AUDIO_PREPARE, ".wav")
    if not khoa_nen:
        raise ThieuDauVao(_t('Chưa có nhạc nền để dựng.'))
    if not run.source_key:
        raise ThieuDauVao(_t('Phiên chạy không có tệp nguồn.'))

    if ctx is not None and getattr(ctx, "progress", None):
        ctx.progress(20, _t('Đang dựng bản dựng'))

    ke_hoach = _doc(kho, khoa_kh)
    thoi_gian.kiem(ke_hoach)          # con dat hop dong sau khi doc lai (I8)
    ban_ke = _doc(kho, khoa_ke)

    # ── Cach render, va cac khoang hinh duoc giu (pha 17) ──────────────────
    #
    # ⭐ Ca hai suy tu **khai bao** (preset) va tu **ban do** ma pha 16 da luu
    #    cung ke hoach — khong tinh lai tu du lieu. Tinh lai mot quyet dinh da
    #    chot la mo duong cho hai cau tra loi khac nhau cho cung mot cau hoi.
    from . import ban_do_thoi_gian, cat_dau_cuoi, che_do_render as cdr, hop_dong_v4

    preset = str((run.settings or {}).get("preset") or hop_dong_v4.PRESET_MAC_DINH)
    cach = cdr.che_do_cho(preset)
    ban_do = ban_do_thoi_gian.BanDoThoiGian.tu_dict(ke_hoach.get("ban_do") or {})
    khoang = list(ban_do.giu)

    # ── Cua so cat dau/cuoi (V6 pha 10) ────────────────────────────────────
    #
    # ⭐ Mot phep GIAO tai dung mot diem, va no phai o **sau** `ban_do.giu`:
    #    ban bien tap la quyet dinh hinh anh co tham quyen (xem `pipeline.py`,
    #    `V4-R07`), con cua so cat la mot lop THU HEP dat len tren no. Lam nguoc
    #    lai — cat truoc roi moi hoi ban do — la de khach vut mat mot canh ma
    #    chinh sach da quyet giu, roi khong ai ghi lai chuyen do.
    #
    # ⚠️ CHI o duong cat, cung khuon ba tang voi `vung` phia duoi. Nhung ly do
    #    thi KHAC, va cho khac nhau moi la cho quan trong: vung che khong the co
    #    o `-c:v copy` vi mot rang buoc VAT LY (khong khung hinh nao duoc giai
    #    ma), con trim thi `-ss`/`-to` lam duoc — no bi cam vi mot quyet dinh
    #    SAN PHAM (`DUNG_SAI_DO_DAI_S`: video ra dai bang video vao).
    #
    # ⛔ Va o day khong tin giao dien: giao dien an hai tay cam khi preset la
    #    giu hinh, nhung mot yeu cau dung tay van toi duoc.
    if cach == cdr.CAT_MA_HOA_LAI:
        khoang = cat_dau_cuoi.giao(
            khoang, (run.settings or {}).get("cat"),
            float(ke_hoach.get("tong_ms") or 0) / 1000.0)

    # 🔴 **Doc `ctx.gpu_uuid` O DAY la mot phep do sai cho, va no da lam
    #    B24-01 khong the sua duoc bang mot dong khai bao.**
    #
    #    COMPOSE va RENDER la HAI job. Mot lease GPU song theo job, nen ke ca khi
    #    COMPOSE duoc cap card, lease do da duoc tra lai truoc khi RENDER bat
    #    dau — con COMPOSE thi chi dung 300 giay de dung mot tep JSON. Tuc dong
    #    cu hoi "toi co card khong" o dung cho ma cau tra loi khong bao gio co
    #    nghia cho cho se dung no.
    #
    # ⇒ O day ta ghi **tran khai bao**: may nay lam duoc gi. RENDER — noi lease
    #   that su ton tai — chi duoc HA xuong CPU, khong bao gio duoc nang len.
    #   Mot ban dung vi the van tat dinh: no noi "toi da xin nvenc", va ban ghi
    #   cua lan chay noi "toi da duoc cap hay khong".
    bo_ma_hoa = (cdr.chon_bo_ma_hoa(cho_phep_gpu=True)
                 if cach == cdr.CAT_MA_HOA_LAI else "")

    ban = ban_dung.dung(
        khoa_video=run.source_key,
        khoa_nen=khoa_nen,
        khoa_master=_khoa_master(db, kho, run),
        ke_hoach=ke_hoach,
        ban_ke_tieng=ban_ke,
        phien_ban_ffmpeg=nhap_media.phien_ban_ffmpeg(),
        tong_giay=float(ke_hoach.get("tong_ms") or 0) / 1000.0,
        che_do=cach, bo_ma_hoa=bo_ma_hoa, khoang_giu=khoang,
        preset=preset,
        # ⭐ Vung che di tu `run.settings` — noi `routes.tao` da ghi CHUNG SAU
        #    KHI `vung_che.chuan_hoa` duyet. Khong chuan hoa lai o day: hai lan
        #    chuan hoa la hai bo luat se lech, va ban da luu moi la ban that.
        #
        # ⚠️ Chi truyen o duong CAT. O duong sao chep, `ban_dung.kiem` se tu
        #    choi — va tu choi o day thi khach mat mot lan chay da tra tien.
        #    Giao dien khong cho ve vung khi preset la giu hinh, nhung mot yeu
        #    cau dung tay van co the toi, nen cho nay khong duoc tin giao dien.
        vung=((run.settings or {}).get("vung") or ()
              if cach == cdr.CAT_MA_HOA_LAI else ()))

    # 🔑 Muc 5: doi chieu MOI tham chieu TRUOC khi ton mot suat render.
    if ctx is not None and getattr(ctx, "progress", None):
        ctx.progress(60, _t('Đang đối chiếu tài nguyên'))
    hop_le = _khoa_con_dung(db, kho, run)
    hop_le.add(run.source_key)        # tep nguon khong phai `AsvAsset`
    ban_dung.kiem(ban, khoa_hop_le=hop_le)

    goi = json.dumps(ban, sort_keys=True, ensure_ascii=False).encode("utf-8")
    with kho.open(khoa_kh) as f:
        cs_kh = assets.bam(f.read())
    vt = ban_dung.van_tay_ban_dung(
        checksum_ke_hoach=cs_kh, khoa_video=run.source_key,
        khoa_nen=khoa_nen,
        phien_ban_ffmpeg=(ban.get("cong_cu") or {}).get("ffmpeg", ""))

    khoa = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                               stage=pipeline.COMPOSE, van_tay=vt, duoi="json")
    kho.put(khoa, io.BytesIO(goi), content_type="application/json")

    if ctx is not None and getattr(ctx, "progress", None):
        ctx.progress(95, _t('Đang lưu kết quả'))

    return {
        "phan": [{"staging_key": khoa, "kind": "json", "duoi": "json",
                  "van_tay": vt}],
        "tom_tat": ban_dung.tom_tat(ban),
    }

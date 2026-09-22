"""Giai doan RENDER — thi hanh mot ban dung da luu, va CHI thu do.

Mot artifact ra:

    <van_tay>.mp4    ban long tieng hoan chinh   (kind=video)

## Vi sao giai doan nay khong duoc biet gi ve thuong nguon

⛔ Prompt 15 cam ro: khong goi chep loi, khong goi model, khong goi may sinh
   tieng. Va no khong chi la mot luat ve pham vi — no la thu lam cho **cong
   thoat cua pha nay** co nghia: *mot ban dung da luu, MOT MINH, phai tai tao
   duoc tep ket qua*. Neu trinh render con hoi them mot cau nao o thuong nguon
   thi menh de do sai, va mot lan render lai sau su co se keo theo mot lan goi
   model — tuc tra tien lan hai cho cung mot ban dich.

⇒ Dau vao cua giai doan nay dung mot thu: `render_manifest.json` cua COMPOSE.

## Thu tu bat buoc: tam -> ffprobe -> promote (muc 8, muc 10)

Ket qua duoc ghi vao mot thu muc tam **theo tung lan chay**, soi bang ffprobe,
roi moi promote. Ba buoc do khong doi cho nhau duoc:

  * ghi thang vao kho la de lai mot tep dang do khi bi ngat — va mot tep dang do
    trong kho **trong y het** mot ket qua that (muc 10);
  * promote truoc khi soi la cong bo mot ket qua chua ai kiem;
  * soi ma khong ghi tam thi khong co gi de soi.

Thu muc tam bi xoa **du that bai hay khong** (`TemporaryDirectory`), nen mot lan
render hong khong de lai vai tram MB rac tren dia may chu.
"""
from __future__ import annotations

import json
import logging
import subprocess
import tempfile
from pathlib import Path

from platform_core.i18n import _ as _t
from platform_core.storage import Storage

from . import assets, ban_dung, ket_xuat, lat_cat, nhap_media, pipeline
from .giai_doan_media import ThieuNguon, _duong_doc_duoc
from .tables import ASSET_OK

log = logging.getLogger(__name__)

#: Tran thoi gian cho MOT lan render. Rong hon tran cua giai doan khac vi day la
#: buoc duy nhat doc va ghi lai toan bo luong hinh — nhung van huu han: mot lan
#: `-c:v copy` khong bao gio dang chay hang gio, nen vuot tran nghia la ket.
TIMEOUT_RENDER = 3600


class ThieuBanDung(ThieuNguon):
    """Chua co ban dung de render."""


def _khoa_ban_dung(db, run) -> str:
    from . import features
    s = features.giai_doan_theo_ten(db, run.id, pipeline.COMPOSE)
    return next((k for k in ((s.outputs or {}).get("khoa_asset") or [])
                 if k.endswith(".json")), "") if s else ""


def _tai_ve(kho: Storage, khoa: str, dich: Path) -> str:
    """Tai mot artifact ve duong cuc bo TA TU DAT TEN.

    ⭐ Ten tep cuc bo la `<so thu tu>.<duoi>`, khong phai ten trong khoa. Hai ly
       do, ca hai da tra gia o pha truoc:

         * do dai duong — MAX_PATH tren Windows la 260, va mot ten tep 64 ky tu
           hex nhan them mot goc thu muc tam la du de vuot (xem
           `assets.DAI_VAN_TAY_TRONG_KHOA`);
         * argv — khong mot manh nao do khach dat ten duoc di vao dong lenh.
    """
    dich.parent.mkdir(parents=True, exist_ok=True)
    with kho.open(khoa) as f:
        dich.write_bytes(f.read())
    return str(dich)


def chay(db, kho: Storage, *, run, ctx=None) -> dict:
    """Ban dung -> tep mp4 da kiem. Khong goi mot giai doan thuong nguon nao."""
    khoa_ban = _khoa_ban_dung(db, run)
    if not khoa_ban:
        raise ThieuBanDung(_t('Chưa có bản dựng để kết xuất.'))

    hoi_huy = None
    if ctx is not None and getattr(ctx, "is_cancelled", None):
        hoi_huy = ctx.is_cancelled
    bao = None
    if ctx is not None and getattr(ctx, "progress", None):
        bao = ctx.progress

    # 🔴 **Chu thich cu o day noi "KHONG xin GPU", va no dung cho MOT preset.**
    #
    #    `-c:v copy` that su khong cham bo ma hoa — nhung `smart_localize` khong
    #    di duong `copy`, no cat-noi roi **ma hoa lai**. Ban khai cua `asv_media`
    #    nay da xin `gpu_vram_mb` cho `asv_media.render` (500 MiB, do that), nen
    #    `ctx.gpu_uuid` co the co gia tri, va day la noi duy nhat cau tra loi do
    #    con song khi ffmpeg thuc su chay.
    #
    # ⭐ `ctx.gpu_env()` an toan khi goi vo dieu kien: khong co card thi no tra
    #    ve moi truong nguyen ven.
    co_gpu = bool(str(getattr(ctx, "gpu_uuid", "") or "")) if ctx is not None else False

    with kho.open(khoa_ban) as f:
        ban = json.loads(f.read().decode("utf-8"))
    # Doc lai thi kiem lai (I8): mot artifact hop le luc ghi van co the da bi
    # sua, va day la lan cuoi truoc khi no dieu khien mot tien trinh con.
    ban_dung.kiem(ban)

    if bao:
        bao(5, _t('Đang đối chiếu tài nguyên'))

    # ── Doi chieu TRUOC khi tai mot byte nao (muc 3) ─────────────────────────
    hop_le = _khoa_con_dung(db, kho, run)
    hop_le.add(run.source_key or "")
    ban_dung.kiem(ban, khoa_hop_le=hop_le)

    lop = ban["tieng"]["lop"]
    tong_giay = float((ban.get("ra") or {}).get("thoi_luong_giay") or 0)

    # 🔑 Thu muc tam mang `run.id`: hai lan chay song song khong the dam nhau,
    #    va mot thu muc sot lai truy nguoc duoc ve mot lan chay cu the.
    #    Cat ngan `run.id` vi cung ly do voi `assets.DAI_*` — MAX_PATH.
    with tempfile.TemporaryDirectory(
            prefix=f"asv-render-{str(run.id)[:12]}-") as tam:
        thu_muc = Path(tam)
        duong_video = _duong_doc_duoc(kho, run.source_key, thu_muc)
        # 🔴 **BAN PHOI, khong phai ban nen.** Tim ra o pha 22 bang cach do am
        #    luong tep ra: -18,69 LUFS (dich -14) va dinh that **+4,1 dB**
        #    (tran -1,5) — ho so cua mot dong tin hieu chua he di qua
        #    `loudnorm`. Vi dong nay tai ve `tieng.nen`, moi video giao cho
        #    khach mang **nhac nen tach ra tu ban goc va khong co mot cau long
        #    tieng nao**.
        #
        # ⭐ Khong phep kiem nao bat duoc vi ca hai nua deu dung: pha 16 chung
        #    minh ban phoi dung, pha 17 chung minh cau lenh render dung — chi
        #    khong ai doi chieu rang cau lenh do doc dung TRUONG nao. Chinh
        #    `ban_dung.dung()` viet o tren no: *"thu trinh render THUC SU doc la
        #    master"*, va dong nay doc `nen`.
        khoa_master = str(((ban["tieng"].get("master") or {}).get("khoa") or ""))
        if not khoa_master:
            raise ket_xuat.KetXuatError(_t('Bản dựng thiếu bản phối âm để kết xuất.'))
        duong_master = _tai_ve(kho, khoa_master, thu_muc / "master.wav")
        duong_lop = [_tai_ve(kho, l["khoa"], thu_muc / f"s{i}.wav")
                     for i, l in enumerate(lop)]

        # ⭐ Chu cua lop phu di ra TEP, khong di ra dong lenh. Do duoc: mot chuoi
        #    tieng Viet co dau, mot dau `:` hay mot dau `\` trong `text=` deu lam
        #    ffmpeg tu choi ca chuoi loc — xem bang do o dau `lop_phu.py`.
        #
        # ⚠️ Ghi vao `thu_muc` cua chinh lan chay nay: no bi xoa **du that bai
        #    hay khong** (`TemporaryDirectory`), nen mot cau chu cua khach khong
        #    o lai tren dia sau khi job xong.
        from . import lop_phu as _lp
        duong_chu = _lp.viet_tep_chu(
            list((ban.get("hinh") or {}).get("lop_phu") or ()), thu_muc)

        # ⭐ Logo la ARTIFACT trong kho, nen no di duong `_tai_ve` y het lop
        #    tieng — khong phai duong tep tam nhu chu cua lop phu.
        #
        # ⚠️ Duoi tep giu nguyen tu KHOA: ffmpeg chon bo giai ma theo noi dung
        #    chu khong theo duoi, nhung mot `.png` doc ra `.bin` lam moi lan doc
        #    log ve sau kho hon ma khong duoc gi.
        ds_logo_ban = list((ban.get("hinh") or {}).get("logo") or ())
        duong_logo = [
            _tai_ve(kho, str(l["khoa"]),
                    thu_muc / f"logo{i}{Path(str(l['khoa'])).suffix or '.png'}")
            for i, l in enumerate(ds_logo_ban)]

        # ⭐ `.ass` di duong y het chu cua lop phu: sinh o thu muc TAM cua lan
        #    chay nay, xoa cung no. Su kien da duoc CHOT o COMPOSE va nam trong
        #    ban dung — o day khong tinh lai mot moc nao.
        #
        # ⚠️ Kich thuoc khung la BAT BUOC ve noi dung: `build_ass` tinh co chu
        #    va le theo no. Mac dinh 1920x1080 ap len mot video doc cho ra phu
        #    de nho bang mot phan ba, dat sai le, **khong bao mot loi nao**.
        from . import phu_de as _pd
        _ho_so_pd = (ban.get("hinh") or {}).get("phu_de") or None
        _goi_su_kien = (_ho_so_pd or {}).get("su_kien") or []
        duong_ass = _pd.viet_tep_ass(
            _ho_so_pd, _goi_su_kien, thu_muc,
            # ⭐ `PlayRes` = khung BAN RA (asv-final): sau cat khung / doi ti le,
            #    phu de dat theo man hinh khach xem, khong theo khung nguon.
            rong=ban_dung.khung_ra(ban.get("hinh") or {})[0],
            cao=ban_dung.khung_ra(ban.get("hinh") or {})[1])

        duong_ra = str(thu_muc / "ra.mp4")
        bo_thuc = ket_xuat.bo_ma_hoa_thuc_te(ban, co_gpu=co_gpu)
        khai = str((ban.get("hinh") or {}).get("bo_ma_hoa") or "")
        if khai and bo_thuc != khai:
            log.info("ha bo ma hoa %s -> %s: khong duoc cap GPU", khai, bo_thuc)
        cmd = ket_xuat.dung_lenh(
            ban, ffmpeg_bin=nhap_media.media.ffmpeg_bin(),
            duong_video=duong_video, duong_master=duong_master,
            duong_lop=duong_lop, duong_ra=duong_ra, bo_ma_hoa=bo_thuc,
            duong_chu=duong_chu, duong_logo=duong_logo,
            duong_ass=duong_ass)

        if bao:
            bao(15, _t('Đang kết xuất video'))

        try:
            duoi = ket_xuat._chay_co_tien_do(
                # `TIMEOUT_RENDER` BANG tran job render (3.600) — job bi giet
                # truoc va ffmpeg mo coi. Kep vao ngan sach con lai (`lat_cat`).
                cmd, tong_giay=tong_giay,
                timeout=lat_cat.han_tien_trinh_con(pipeline.RENDER,
                                                   TIMEOUT_RENDER),
                hoi_huy=hoi_huy,
                # ⭐ Goi vo dieu kien: khong co card thi `gpu_env` tra ve moi
                #    truong nguyen ven, nen duong `preserve` khong doi hanh vi.
                env=(ctx.gpu_env() if ctx is not None
                     and getattr(ctx, "gpu_env", None) else None),
                # Tien do cua ffmpeg (0-100) duoc ep vao khoang 15-95 cua giai
                # doan: 0-15 la tai tep, 95-100 la soi va promote.
                bao_tien_do=(lambda p: bao(15 + p * 0.8, _t('Đang kết xuất video')))
                if bao else None)
        except subprocess.TimeoutExpired as exc:
            raise ket_xuat.KetXuatError(_t('Kết xuất quá hạn.')) from exc
        except ket_xuat.KetXuatError:
            # 🔑 Ho so chan doan DA CHE, giu lai de tra loi "vi sao lan do hong"
            #    ma khong lo bo cuc dia hay ten nguoi dung Windows (muc 9).
            log.warning("render that bai: %s", json.dumps(
                ket_xuat.ho_so_chan_doan(ban, cmd, goc_tam=str(thu_muc)),
                ensure_ascii=False))
            raise

        if bao:
            bao(95, _t('Đang kiểm tệp kết quả'))

        # ── ffprobe TRUOC khi promote (muc 8) ────────────────────────────────
        tt = ket_xuat.kiem_tep_ra(duong_ra, ban, soi=nhap_media.soi)

        vt = _van_tay(kho, khoa_ban, ban)
        khoa = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                                   stage=pipeline.RENDER, van_tay=vt, duoi="mp4")
        with open(duong_ra, "rb") as f:
            kho.put(khoa, f, content_type="video/mp4")

        # ── `.srt` la MOT BAN GIAO, khong phai mot tep trung gian ───────────
        #
        # 🔑 **Vi sao no sinh o RENDER chu khong o COMPOSE**, du du lieu da san
        #    sang tu COMPOSE: `thi_hanh` dat `la_ban_giao = ten == RENDER`, va
        #    ban giao la thu **khong co han**. Sinh o COMPOSE thi tep phu de cua
        #    khach mang `HAN_TRUNG_GIAN = 30 ngay` trong khi video thi khong —
        #    tuc mot nua ban giao tu bien mat sau mot thang, im lang.
        phan = [{"staging_key": khoa, "kind": "video", "duoi": "mp4",
                 "van_tay": vt, "parent_keys": [khoa_ban]}]
        duong_srt = _pd.viet_tep_srt(_ho_so_pd, _goi_su_kien, thu_muc)
        if duong_srt:
            khoa_srt = assets.khoa_staging(
                owner_id=run.owner_id, run_id=run.id, stage=pipeline.RENDER,
                van_tay=vt, duoi="srt")
            with open(duong_srt, "rb") as f:
                kho.put(khoa_srt, f, content_type="application/x-subrip")
            phan.append({"staging_key": khoa_srt, "kind": "subtitle",
                         "duoi": "srt", "van_tay": vt,
                         "parent_keys": [khoa_ban]})

    return {
        "phan": phan,
        "tom_tat": {
            "thoi_luong_giay": round(float(tt["thoi_luong"]), 3),
            "co_byte": int(tt["co_byte"]),
            "codec_video": tt["codec_video"],
            "codec_tieng": tt["codec_tieng"],
            "so_lop_tieng": len(lop),
            "chan_doan": " | ".join((duoi or "").split(" | ")[-2:]),
        },
    }


def _van_tay(kho: Storage, khoa_ban: str, ban: dict) -> str:
    """Van tay cua tep ra. Doi ban dung HAY doi cach dung lenh deu doi no (O13).

    ⭐ `PHIEN_BAN_KET_XUAT` nam trong van tay chinh la thu lam cong thoat cua pha
       nay dung duoc: doi cach dung lenh ffmpeg ma van tay khong doi thi mot lan
       chay lai se **dung lai tep cu** va khong ai thay cach dung lenh moi.

    🔴 **`PHIEN_BAN_CHE_DO` them o V6 pha 11, va no vá mot lo co that.**

       Cau tren hua *"doi cach dung lenh deu doi no"*. Nhung `dung_lenh` chi
       DAN chuoi loc lai; nguoi dung no la `che_do_render.loc_cat_noi`. Nen mot
       thay doi trong chinh cho ay — doi cach lam mo, doi thu tu chang, them
       `drawtext` — cho ra **cung mot ban dung** va **cung mot van tay**, trong
       khi tep ra da khac.

       ⛔ Va no khong bao gio no. No hien ra nhu mot lan chay lai "nhanh bat
          thuong" tra ve dung tep cu — thu ma `assets.py` goi ten la *"sot tham
          so = serve nham"*.

    ⚠️ `PHIEN_BAN_CHE_DO` khong the thay cho `ban_dung`: `vung` va `lop_phu` nam
       TRONG ban dung nen chung da vao `cs`. Hai so nay chot hai thu khac nhau —
       *du lieu* va *ma sinh ra lenh* — va ca hai deu doi duoc doc lap.
    """
    import hashlib

    from . import che_do_render as cdr

    with kho.open(khoa_ban) as f:
        cs = assets.bam(f.read())
    goi = json.dumps({"ban_dung": cs,
                      "ket_xuat": ket_xuat.PHIEN_BAN_KET_XUAT,
                      "che_do": cdr.PHIEN_BAN_CHE_DO,
                      "ffmpeg": (ban.get("cong_cu") or {}).get("ffmpeg", "")},
                     sort_keys=True)
    return hashlib.sha256(goi.encode("utf-8")).hexdigest()


def _khoa_con_dung(db, kho: Storage, run) -> set[str]:
    """Moi khoa artifact CUA CHINH chu so huu, da kiem toan ven.

    Kiem lai o day thay vi tin cot `integrity`: COMPOSE da kiem, nhung giua
    COMPOSE va RENDER co the la hang gio xep hang, va mot tep het han trong
    khoang do se lam ffmpeg hong o phut thu muoi thay vi o day.
    """
    from sqlalchemy import select

    from .tables import AsvAsset

    hang = db.execute(select(AsvAsset).where(
        AsvAsset.run_id == run.id,
        AsvAsset.owner_id == run.owner_id)).scalars().all()
    return {a.storage_key for a in hang
            if assets.kiem_toan_ven(db, kho, a) == ASSET_OK}

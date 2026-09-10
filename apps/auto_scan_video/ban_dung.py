"""BAN DUNG (RenderManifest) — mo ta day du mot lan render, bang DU LIEU.

## Vi sao ban dung la DU LIEU chu khong phai mot chuoi lenh

Cach de hon la sinh san chuoi `ffmpeg -i ... -filter_complex ...` roi luu no.
Nhung nhu the la **dinh quyet dinh bien tap vao mot phien ban ffmpeg**: doi cu
phap bo loc, hay doi encoder, la phai chay lai ca chuoi AI o thuong nguon chi de
sinh lai mot chuoi lenh.

⇒ Ban dung mo ta **cai gi**, khong mo ta **lam the nao**. Trinh render doc no roi
  tu dung lenh. Do la ranh gioi G9 doi (composer ≠ renderer), va cai gia phai
  tra neu tron hai thu lai la mot lan doi cong cu keo theo mot lan tinh lai tien.

## Vi sao MVP khong dung duoc logic bien tap di san

`DUNGVIDEO-FULL/engine/assemble.py:1040 build_video_from_timeline` cat clip, ma
hoa lai, ghep xfade — toan bo la duong **cat dung**, va `MVP_CONTRACT.md` §4 da
hoan het (D-ASV-02). Thu con dung la `Cut_only ver2/.../ffmpeg_edit_cutonly.py:323
replace_audio`:

    -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -movflags +faststart -shortest

Do dung la hinh dang render cua MVP: **thay tieng, giu nguyen hinh**.

## Tham chieu, khong phai duong dan

⛔ Ban dung KHONG BAO GIO chua duong dan tuyet doi. Mot lan chay lai co the roi
   vao worker khac, va mot duong dan `C:\\...\\tmp\\abc` cua may khac la mot ban
   dung khong dung duoc — hong theo kieu "tep khong ton tai", tuc chi vao sai cho.
   No chua **khoa luu tru**, va trinh render tu giai chung.

⛔ Va no khong chua bi mat nao: khong khoa API, khong token, khong payload cua
   provider (Prompt 14 muc 4). Ban dung duoc luu ben vung va doc lai duoc, nen
   moi thu trong no la thu chiu duoc viec bi doc.
"""
from __future__ import annotations

import hashlib
import json

from platform_core.i18n import _ as _t

#: ⬆️ 1 -> 2 (V5): them `hinh.vung`. Ban dung SCHEMA 1 khong co khoa do,
#:    va do la khac biet co nghia — khong phai mot mang rong.
SCHEMA_BAN_DUNG = 2

#: Chinh sach dau ra. Ke thua tu `assemble.py:199-207` va `replace_audio`.
CODEC_TIENG = "aac"
BITRATE_TIENG = "192k"
TAN_SO_RA = 48000
SO_KENH_RA = 2
#: `copy` — khong bao gio ma hoa lai luong hinh (D-ASV-03).
CHE_DO_HINH = "copy"

#: Doi khi doi bat ky chinh sach nao o tren. Vao van tay (O13).
PHIEN_BAN_BAN_DUNG = 1


class BanDungError(ValueError):
    """Ban dung khong dung duoc."""


def dung(*, khoa_video: str, khoa_nen: str, ke_hoach: dict,
         ban_ke_tieng: dict, phien_ban_ffmpeg: str,
         tong_giay: float, khoa_master: str = "", che_do: str = "",
         bo_ma_hoa: str = "", khoang_giu=None, preset: str = "",
         vung=None, lop_phu=None, cao_khung: int = 0,
         ds_logo=None, rong_khung: int = 0) -> dict:
    """Dung ban dung tu cac tai lieu chinh tac. Khong cham mot tep media nao.

    `ke_hoach`      ket qua cua `thoi_gian.lap_ke_hoach`
    `ban_ke_tieng`  `{doan: [{ma, khoa, giay}]}` do VOICE sinh ra
    `khoa_master`   ban phoi am cua pha 16 — **thu ma trinh render doc**
    `che_do`        `che_do_render.SAO_CHEP` hoac `CAT_MA_HOA_LAI`
    `bo_ma_hoa`     bo ma hoa da chon (chi co nghia khi ma hoa lai)
    `khoang_giu`    cac khoang NGUON duoc giu, theo thu tu — chi cho preset cat

    🔴 **Pha 17 them `khoa_master`, va no thay the mot thu chu khong bo sung.**

       Truoc do trinh render tu tron: nen + N lop tieng + `loudnorm`, ngay trong
       lenh render. Pha 16 dung mot BAN PHOI hoan chinh — neu render van tu tron
       thi ban phoi do la mot artifact **ton ffmpeg de sinh ra va khong ai doc**,
       dung cai loi pha 14 vua go bo o cho khac.

    ⭐ Nen tu pha 17: mot nguon hinh, mot nguon tieng. Cac lop van duoc ghi lai
       trong ban dung — chung la **ho so** cua quyet dinh thoi gian, van con
       nguyen gia tri khi can truy vet — nhung trinh render khong con dung chung
       de tron nua.
    """
    from . import che_do_render as cdr

    if not khoa_video:
        raise BanDungError(_t('Bản dựng thiếu luồng hình nguồn.'))
    if not khoa_nen:
        raise BanDungError(_t('Bản dựng thiếu nhạc nền.'))
    che_do = str(che_do or cdr.SAO_CHEP)
    if che_do not in cdr.CHE_DO:
        raise BanDungError(_t('Bản dựng khai cách render không hợp lệ.'))
    khoang_giu = [(float(b), float(k)) for b, k in (khoang_giu or ())]
    if che_do == cdr.CAT_MA_HOA_LAI and not khoang_giu:
        raise BanDungError(
            _t('Bản dựng cắt nối nhưng không khai khoảng nào được giữ.'))

    khoa_theo_ma = {str(d["ma"]): str(d.get("khoa") or "")
                    for d in (ban_ke_tieng.get("doan") or [])}

    lop: list[dict] = []
    for d in (ke_hoach.get("doan") or []):
        ma = str(d["ma"])
        if int(d.get("dai_ms") or 0) <= 0:
            # Doan da bi cat o TIMING (vuot tran troi). Bo qua, nhung QC dem no
            # qua `so_doan_bi_cat` cua ke hoach (T12) — khong lam mat dau vet.
            continue
        khoa = khoa_theo_ma.get(ma, "")
        if not khoa:
            raise BanDungError(
                _t('Đoạn {ma} có trong kế hoạch nhưng không có tệp tiếng.')
                .format(ma=ma))
        lop.append({
            "ma": ma,
            "khoa": khoa,
            "dat_tai_ms": int(d["dat_tai_ms"]),
            #: `1.0` = khong doi toc. Trinh render chi ap `atempo` khi > 1.
            "he_so_toc": float(d["he_so_toc"]),
        })

    ban = {
        "schema": SCHEMA_BAN_DUNG,
        "phien_ban": PHIEN_BAN_BAN_DUNG,
        # 🔑 **Preset di theo ban dung, va do la mot lop bao ve chu khong phai
        #    mot ghi chu.** Trinh render doi chieu `che_do_cho(preset)` voi
        #    `cach_render`: mot ban dung khai "giu nguyen hinh anh" ma lai xin ma
        #    hoa lai se hong o cong cuoi, truoc khi ton mot suat render.
        #
        # ⭐ Truoc pha 17 lop bao ve nay la mot chot vo dieu kien trong trinh
        #    render ("khong bao gio ma hoa lai"). Pha 17 phai noi no ra — va
        #    `test_427` da luong truoc chinh viec do, kem canh bao rang cach noi
        #    SAI la xoa han chot: khi do preset giu hinh mat bao ve **im lang**.
        "preset": str(preset or ""),
        # ── Hinh: mot nguon; SAO CHEP hoac CAT-NOI roi ma hoa lai ────────
        #
        # 🔑 `che_do` la thu trinh render doc de chon duong. `che_do_hinh` giu
        #    lai ten cu (`copy`) cho preset giu hinh de khong pha ho so cu.
        "hinh": {
            "khoa": khoa_video,
            "che_do": CHE_DO_HINH,
            "cach_render": che_do,
            "bo_ma_hoa": str(bo_ma_hoa or ""),
            "khoang_giu": [[round(b, 4), round(k, 4)] for b, k in khoang_giu],
            # ── Vung che (V5) ────────────────────────────────────────────
            #
            # 🔴 Chi co nghia o duong CAT. Lam mo mot vung doi hoi mot BO LOC,
            #    va mot bo loc doi hoi giai ma roi ma hoa lai — trong khi duong
            #    `sao_chep` di bang `-c:v copy`, noi khong co cho nao dat bo loc
            #    vao. `kiem()` cuong che dieu do, xem o duoi.
            #
            # ⭐ Luu CA KHI RONG, va do la co y: mot ban dung khong co khoa
            #    `vung` va mot ban dung co `vung: []` la hai thu khac nhau voi
            #    nguoi doc lai — cai dau la ban dung dung SCHEMA CU.
            "vung": [dict(v) for v in (vung or ())],
            # ── Lop phu chu (V6 pha 11) ──────────────────────────────────
            #
            # 🔴 Cung rang buoc VAT LY voi `vung`: `drawtext` la mot bo loc, va
            #    mot bo loc doi hoi giai ma. Duong `sao_chep` khong giai ma
            #    khung nao, nen khong co khung nao de ve len. `kiem()` cuong
            #    che, giao dien noi truoc.
            "lop_phu": [dict(l) for l in (lop_phu or ())],
            # 🔑 Chieu cao khung NGUON. No o day vi mot ly do do duoc: `borderw`
            #    cua `drawtext` **khong nhan bieu thuc** (`borderw=H*0.004` lam
            #    ffmpeg tra "Invalid argument"), nen do day vien phai duoc tinh
            #    ra pixel TRUOC khi dung chuoi loc. Xem `lop_phu.vien_px`.
            #
            # ⚠️ Luu ca khi khong co lop phu: mot ban dung khong co khoa nay va
            #    mot ban dung co `cao_khung: 0` la hai thu khac nhau voi nguoi
            #    doc lai.
            "cao_khung": int(cao_khung or 0),
            # ── Logo (V6 pha 08b) ────────────────────────────────────────
            #
            # 🔴 Cung rang buoc VAT LY voi `vung` va `lop_phu`: `overlay` la
            #    mot bo loc, bo loc doi hoi giai ma, `-c:v copy` khong giai
            #    ma khung nao.
            #
            # ⚠️ KHAC hai thu kia o mot cho: moi logo la mot **khoa luu tru**,
            #    nen no phai nam trong tap doi chieu `khoa_hop_le` cua
            #    `kiem()`. Mot dong chu thi khong the "khong ton tai".
            "logo": [dict(l) for l in (ds_logo or ())],
            #: Chieu RONG khung nguon. Cung ly do voi `cao_khung`: be rong
            #: logo phai duoc tinh ra pixel truoc khi dung chuoi loc.
            "rong_khung": int(rong_khung or 0),
        },
        # ── Tieng: BAN PHOI da dung o pha 16 ────────────────────────────
        #
        # ⭐ `nen` va `lop` van o day lam HO SO cua quyet dinh thoi gian — chung
        #    tra loi "cau nay dat o dau, vi sao" khi can truy vet. Nhung thu
        #    trinh render THUC SU doc la `master`.
        "tieng": {
            "master": {"khoa": str(khoa_master or "")},
            "nen": {"khoa": khoa_nen},
            "lop": lop,
            "tan_so": TAN_SO_RA,
            "so_kenh": SO_KENH_RA,
        },
        # ── Chinh sach dau ra ────────────────────────────────────────────
        "ra": {
            "container": "mp4",
            "codec_tieng": CODEC_TIENG,
            "bitrate_tieng": BITRATE_TIENG,
            "faststart": True,
            #: Thoi luong MONG DOI. Trinh render doi chieu ban that voi so nay;
            #: lech qua nguong la mot loi, khong phai mot ghi chu.
            "thoi_luong_giay": round(float(tong_giay), 3),
        },
        # ── Phien ban cong cu, DONG BANG (Prompt 14 muc 6) ──────────────
        #
        # ⭐ Mot ban dung khong ghi phien ban cong cu la mot ban dung khong tai
        #    lap duoc: nang ffmpeg roi render lai co the ra tep khac, va khong
        #    co gi trong ho so noi vi sao.
        "cong_cu": {"ffmpeg": str(phien_ban_ffmpeg or "khong-ro")},
    }
    kiem(ban)
    return ban


def kiem(ban: dict, *, khoa_hop_le: set[str] | None = None) -> None:
    """Kiem ban dung. Nem `BanDungError` kem ly do cu the.

    `khoa_hop_le` — neu dua vao, MOI khoa trong ban dung phai nam trong tap nay.
    Do la phep kiem cua Prompt 14 muc 5: **doi chieu moi tham chieu TRUOC khi
    ton tai nguyen render**. Mot ban dung tro toi mot artifact khong con la mot
    lan render that bai o phut thu muoi, sau khi da chiem mot suat ffmpeg.
    """
    if not isinstance(ban, dict):
        raise BanDungError(_t('Bản dựng không đúng định dạng.'))
    if int(ban.get("schema") or 0) != SCHEMA_BAN_DUNG:
        raise BanDungError(_t('Bản dựng thuộc phiên bản cấu trúc khác.'))

    hinh = ban.get("hinh") or {}
    if not hinh.get("khoa"):
        raise BanDungError(_t('Bản dựng thiếu luồng hình nguồn.'))
    if hinh.get("che_do") != CHE_DO_HINH:
        # 🔑 D-ASV-03. Mot ban dung khai `che_do` khac `copy` la mot ban dung se
        #    ma hoa lai hinh cua khach — tieu GPU va mat chat luong cho mot viec
        #    ho khong yeu cau.
        raise BanDungError(
            _t('Bản dựng khai chế độ hình khác "copy" — MVP không mã hoá lại hình.'))

    # ── Vung che chi song duoc o duong CAT (V5) ─────────────────────────────
    #
    # 🔴 Day khong phai mot chinh sach ta chon, no la mot rang buoc VAT LY.
    #
    #    Duong `sao_chep` phat `-c:v copy`: byte hinh di thang tu nguon sang tep
    #    ra, khong giai ma lan nao. Khong co khung hinh nao ton tai trong bo nho
    #    de ma sua mot vung diem anh cua no. Muon lam mo thi phai giai ma — tuc
    #    thoi `copy` — tuc pha vo ca D-ASV-03 lan loi hua cua preset giu hinh
    #    (*"hinh anh duoc sao chep nguyen ven, khong giam chat luong"*).
    #
    # ⛔ Nen mot ban dung vua `sao_chep` vua co vung la mot ban dung **khong the
    #    thi hanh dung**. Neu no lot qua day, `ket_xuat` se lang le bo qua vung
    #    va giao mot video khong che gi — khach tra tien cho mot thu khong xay
    #    ra, dung kieu that bai ma pha 27 vua go bo o cho khac.
    #
    # ⇒ Chan o day, va giao dien noi truoc cho khach de ho khong bao gio ve mot
    #   vung roi moi biet no vo nghia.
    from . import che_do_render as _cdr
    if hinh.get("vung") and hinh.get("cach_render") != _cdr.CAT_MA_HOA_LAI:
        raise BanDungError(_t(
            'Vùng che chỉ dùng được với kiểu xử lý có biên tập lại hình.'))

    # ── Lop phu chu: cung mot rang buoc, va no phai duoc VIET RA rieng ──────
    #
    # ⛔ Khong gop hai chot lam mot dieu kien `or`. Hai tinh nang khac nhau thi
    #    hai cau tra loi khac nhau: khach ve mot O CHE va khach go mot DONG CHU
    #    la hai viec, va mot cau chung chung buoc ho phai doan minh vua lam gi
    #    sai. `test_453` goi ten cho lo nguoc lai — nang luc co ma khong ai di
    #    tren duong; o day thi la duong co ma bien bao noi sai loi.
    if hinh.get("lop_phu") and hinh.get("cach_render") != _cdr.CAT_MA_HOA_LAI:
        raise BanDungError(_t(
            'Lớp phủ chữ chỉ dùng được với kiểu xử lý có biên tập lại hình.'))

    # 🔴 Do day vien tinh bang PIXEL, nen no can chieu cao khung. Mot ban dung
    #    co lop phu ma khong khai `cao_khung` se hong o TRINH RENDER — tuc sau
    #    khi da chiem mot suat ffmpeg va tai vai tram MB. Chan o day.
    if hinh.get("lop_phu") and int(hinh.get("cao_khung") or 0) <= 0:
        raise BanDungError(_t(
            'Bản dựng có lớp phủ chữ nhưng không khai chiều cao khung hình.'))

    # ── Logo: cung ba chot, va mot chot THU TU chi no moi co ────────────────
    if hinh.get("logo") and hinh.get("cach_render") != _cdr.CAT_MA_HOA_LAI:
        raise BanDungError(_t(
            'Logo chỉ dùng được với kiểu xử lý có biên tập lại hình.'))
    if hinh.get("logo") and int(hinh.get("rong_khung") or 0) <= 0:
        raise BanDungError(_t(
            'Bản dựng có logo nhưng không khai chiều rộng khung hình.'))
    for _l in (hinh.get("logo") or []):
        if not _l.get("khoa"):
            raise BanDungError(_t('Bản dựng có logo thiếu khoá lưu trữ.'))

    tieng = ban.get("tieng") or {}
    if not (tieng.get("nen") or {}).get("khoa"):
        raise BanDungError(_t('Bản dựng thiếu nhạc nền.'))
    # 🔴 **Them o pha 22, va no la nua con thieu cua mot loi da giao hang.**
    #
    #    Ham nay doi `nen` phai co tu pha 16, nhung khong bao gio doi `master` —
    #    trong khi `master` moi la thu trinh render doc. Ket qua: mot ban dung
    #    **khong co ban phoi** van qua duoc moi phep kiem, va `giai_doan_ket_xuat`
    #    lang le render bang `nen`. Do la nhac nen tach ra tu ban goc: khach nhan
    #    ve mot video khong co mot cau long tieng nao.
    #
    # ⇒ Mot truong ma trinh render BAT BUOC phai co thi phai duoc kiem o day.
    if not (tieng.get("master") or {}).get("khoa"):
        raise BanDungError(_t('Bản dựng thiếu bản phối âm.'))

    truoc_ket = None
    for lop in (tieng.get("lop") or []):
        if not lop.get("khoa"):
            raise BanDungError(
                _t('Lớp tiếng {ma} thiếu khoá lưu trữ.').format(
                    ma=lop.get("ma", "?")))
        dat = int(lop.get("dat_tai_ms", -1))
        if dat < 0:
            raise BanDungError(_t('Bản dựng có mốc thời gian âm.'))
        if float(lop.get("he_so_toc", 1.0)) < 1.0:
            # Cham lai KHONG nam trong mo hinh: ADR-003 chi dung tang toc de TRA
            # NO. Mot he so < 1 la mot phep bien doi khong ai quyet dinh.
            raise BanDungError(_t('Bản dựng có hệ số tốc độ nhỏ hơn 1.'))
        if truoc_ket is not None and dat < truoc_ket - 200:
            raise BanDungError(_t('Bản dựng có hai lớp tiếng chồng quá 200 ms.'))
        truoc_ket = dat

    if khoa_hop_le is not None:
        # ⭐ `master` nam trong tap doi chieu nay tu pha 22: mot khoa ma trinh
        #    render se doc ma khong co trong kho la mot lan render hong o giua
        #    chung, sau khi da tai vai tram MB.
        moi = {hinh["khoa"], tieng["nen"]["khoa"], tieng["master"]["khoa"]}
        moi |= {lop["khoa"] for lop in (tieng.get("lop") or [])}
        # 🔑 Logo la mot artifact THAT, nen no phai qua cung mot cua doi chieu.
        #    Mot ban dung tro toi mot logo khong con la mot lan render hong o
        #    giua chung — sau khi da tai vai tram MB.
        moi |= {str(l.get("khoa") or "") for l in (hinh.get("logo") or [])}
        thieu = sorted(moi - khoa_hop_le)
        if thieu:
            raise BanDungError(
                _t('Bản dựng trỏ tới {n} tài nguyên không tồn tại.').format(
                    n=len(thieu)))

    # ⛔ Khong bi mat nao duoc phep nam trong ban dung (muc 4).
    goi = json.dumps(ban, ensure_ascii=False).lower()
    for cam in ("credential", "token", "api_key", "secret", "password",
                "authorization"):
        if cam in goi:
            raise BanDungError(
                _t('Bản dựng chứa trường nhạy cảm: {ten}.').format(ten=cam))


def van_tay_ban_dung(*, checksum_ke_hoach: str, khoa_video: str,
                     khoa_nen: str, phien_ban_ffmpeg: str) -> str:
    """Van tay. Doi bat ky dau vao hay chinh sach nao deu doi van tay (O13)."""
    goi = json.dumps({
        "ke_hoach": checksum_ke_hoach,
        "video": khoa_video,
        "nen": khoa_nen,
        "ffmpeg": phien_ban_ffmpeg,
        "codec": CODEC_TIENG,
        "bitrate": BITRATE_TIENG,
        "tan_so": TAN_SO_RA,
        "so_kenh": SO_KENH_RA,
        "che_do_hinh": CHE_DO_HINH,
        "phien_ban": PHIEN_BAN_BAN_DUNG,
        "schema": SCHEMA_BAN_DUNG,
    }, sort_keys=True)
    return hashlib.sha256(goi.encode("utf-8")).hexdigest()


def tom_tat(ban: dict) -> dict:
    """Con so cho tien do va QC. Khong co loi thoai, khong co duong dan."""
    lop = (ban.get("tieng") or {}).get("lop") or []
    return {
        "so_lop_tieng": len(lop),
        "so_lop_tang_toc": sum(1 for l in lop if float(l["he_so_toc"]) > 1.0),
        "che_do_hinh": (ban.get("hinh") or {}).get("che_do", ""),
        # ⭐ Them o pha 22. `che_do_hinh` luon la `copy` (ten cu, giu cho ho so
        #    cu doc duoc), nen truoc do BAN TOM TAT khong noi duoc lua chon co
        #    hau qua nhat cua ca ban dung: sao chep luong hinh hay cat-noi roi ma
        #    hoa lai. Mot ban tom tat de nguoi van hanh doc ma bo qua dieu do thi
        #    hai lan chay khac han nhau trong y het nhau.
        "cach_render": (ban.get("hinh") or {}).get("cach_render", ""),
        "thoi_luong_giay": (ban.get("ra") or {}).get("thoi_luong_giay", 0),
        "ffmpeg": (ban.get("cong_cu") or {}).get("ffmpeg", ""),
    }

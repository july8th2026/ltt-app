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

SCHEMA_BAN_DUNG = 1

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
         tong_giay: float) -> dict:
    """Dung ban dung tu cac tai lieu chinh tac. Khong cham mot tep media nao.

    `ke_hoach`      ket qua cua `thoi_gian.lap_ke_hoach`
    `ban_ke_tieng`  `{doan: [{ma, khoa, giay}]}` do VOICE sinh ra
    """
    if not khoa_video:
        raise BanDungError(_t('Bản dựng thiếu luồng hình nguồn.'))
    if not khoa_nen:
        raise BanDungError(_t('Bản dựng thiếu nhạc nền.'))

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
        # ── Hinh: mot nguon, SAO CHEP ────────────────────────────────────
        "hinh": {"khoa": khoa_video, "che_do": CHE_DO_HINH},
        # ── Tieng: nen + cac lop tieng dat theo ke hoach ─────────────────
        "tieng": {
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

    tieng = ban.get("tieng") or {}
    if not (tieng.get("nen") or {}).get("khoa"):
        raise BanDungError(_t('Bản dựng thiếu nhạc nền.'))

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
        moi = {hinh["khoa"], tieng["nen"]["khoa"]}
        moi |= {lop["khoa"] for lop in (tieng.get("lop") or [])}
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
        "thoi_luong_giay": (ban.get("ra") or {}).get("thoi_luong_giay", 0),
        "ffmpeg": (ban.get("cong_cu") or {}).get("ffmpeg", ""),
    }

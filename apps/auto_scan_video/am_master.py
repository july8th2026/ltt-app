"""Ban phoi am cuoi: nen (da bo giong goc) + cac doan tieng Viet da nan.

⛔ **Khong mot loi goi model nao trong tep nay.** Pha 16 cam ro. Tat ca o day la
   so hoc va ffmpeg — tat dinh, chay lai cho ket qua giong het.

## Vi sao khong phai mot lenh ffmpeg duy nhat

Cach "sach" nhat la mot `filter_complex` voi N+1 dau vao: nen, cong tung doan
tieng, moi doan mot `adelay`. Voi mot phim co 400 doan thoai thi:

  * dong lenh dai hang chuc nghin ky tu — Windows cat o **32.767** ky tu, va no
    cat **im lang**: ffmpeg nhan mot bieu thuc loc bi cut cut, roi bao mot loi
    cu phap khong lien quan gi toi nguyen nhan;
  * do thi loc co 400 nhanh, va bo nho ffmpeg tang theo so nhanh chu khong theo
    do dai tieng.

⭐ Nen ta gom theo **lo**: moi lo `DOAN_MOI_LO` doan thanh mot ban tieng dai bang
   ca bai, roi tron cac ban lo lai. Cung mot ket qua, so nhanh moi lan chay bi
   chan, va do dai dong lenh khong con phu thuoc do dai phim.

## Vi sao `amix` chu khong phai `overlay`/`concat`

Cac doan tieng **khong** noi duoi nhau: chung nam o nhung moc rieng, co the co
khoang lang giua, va (trong tran cho phep) co the cham nhau. `concat` gia dinh
noi duoi nhau; `amix` cong tin hieu tai moi thoi diem — dung mo hinh cua bai
toan.

⛔ `amix` mac dinh **chia trung binh** theo so dau vao (`normalize=1`), tuc them
   mot doan tieng lam nho ca ban nen. Luon `normalize=0` roi chuan am luong mot
   lan o cuoi.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from platform_core import media
from platform_core.i18n import _ as _t

from .nhap_media import MediaError, _chay

#: Doi khi doi cach dung ban phoi. Vao van tay.
PHIEN_BAN_MASTER = 1

#: So doan tieng moi lo. Xem ghi chu dau tep ve vi sao khong lam mot lan.
#:
#: ⚠️ 24 la con so an toan cho dong lenh, CHUA DO ve toc do. Moi doan them vao
#:    mot lo lam do thi loc rong ra mot nhanh; moi lo them vao lam them mot lan
#:    giai ma/ma hoa. Diem toi uu nam o dau thi phai do, va pha 21 do.
DOAN_MOI_LO = 24

#: Dang cua ban phoi. Trung voi `tach_tieng` de khong phai doi tan so o giua.
TAN_SO = 44100
SO_KENH = 2

#: Am luong dich cua ban ra. Muon tu `tach_tieng` — mot con so, mot cho khai.
def lufs_dich() -> float:
    from .tach_tieng import LUFS_DICH

    return float(LUFS_DICH)


def dinh_that_db() -> float:
    from .tach_tieng import DINH_THAT_DB

    return float(DINH_THAT_DB)


#: He so am luong cua NEN khi co tieng noi de len.
#:
#: 🔴 Khong phai mot lua chon tham my: neu nen giu nguyen muc thi giong Viet phai
#:    to hon nen moi nghe ro, va lam giong to hon la dua no toi tran cat ngon.
#:    Ha nen xuong la cach cac ban long tieng that lam ("ducking"), va -6 dB la
#:    muc thuong dung: nghe van con nhac, nhung loi thoai noi len tren.
#:
#: ⚠️ CHUA DO tren ban that. Chon theo huong an toan cho de nghe ro loi. Pha 21
#:    do lai bang mot phep do tach biet giong/nen.
NEN_GIAM_DB = -6.0


class MasterError(MediaError):
    """Khong dung duoc ban phoi."""


def _delay_ms(t: float) -> int:
    return max(0, int(round(float(t) * 1000.0)))


def bieu_thuc_lo(so_dau_vao: int, moc_ms: list[int], he_so: list[float]) -> str:
    """Bieu thuc `filter_complex` cho MOT lo doan tieng.

    Moi dau vao: `atempo` (neu can co gian) -> `adelay` -> gom lai bang `amix`.

    ⛔ `atempo` chi nhan he so trong `[0,5; 100]` mot lan goi. Tran co gian cua ta
       la 1,15 nen mot lan la du — nhung viec do phai duoc NOI RA, khong de nguoi
       sau nang tran roi gap mot loi ffmpeg kho hieu.
    """
    if so_dau_vao <= 0:
        raise MasterError(_t('Lô trộn không có đoạn nào.'))
    phan = []
    for i in range(so_dau_vao):
        chuoi = f"[{i}:a]"
        h = float(he_so[i]) if i < len(he_so) else 1.0
        if abs(h - 1.0) > 1e-6:
            if not (0.5 <= h <= 2.0):
                raise MasterError(
                    _t('Hệ số co giãn {h} ngoài khoảng một lần `atempo`.')
                    .format(h=round(h, 3)))
            chuoi += f"atempo={h:.6f},"
        # ⚠️ `all=1` — bai hoc thu hai mang tu trinh render cu sang. Thieu no
        #    thi `adelay` **chi tre kenh dau**, va tieng lech hai ben tai: hong
        #    theo kieu nghe thay duoc nhung rat kho goi ten.
        #
        # ⭐ `aformat` tren TUNG dau vao, TRUOC khi tron: tieng do may TTS sinh
        #    ra va nhac nen do demucs tach ra khong cung tan so/so kenh, va de
        #    `amix` tu xu ly la de no chon gium — no chon theo dau vao dau tien.
        chuoi += (f"adelay={moc_ms[i]}:all=1,"
                  f"aformat=sample_fmts=fltp:sample_rates={TAN_SO}:"
                  f"channel_layouts=stereo[v{i}];")
        phan.append(chuoi)
    nhan = "".join(f"[v{i}]" for i in range(so_dau_vao))
    # ⛔ `normalize=0`: xem ghi chu dau tep.
    phan.append(f"{nhan}amix=inputs={so_dau_vao}:normalize=0:"
                f"dropout_transition=0[ra]")
    return "".join(phan)


def tron_lo(duong_vao: list[str], moc_ms: list[int], he_so: list[float],
            dich: str, *, tong_giay: float, hoi_huy=None,
            timeout: int = 1800) -> str:
    """Tron MOT lo doan tieng thanh mot ban dai bang ca bai."""
    if len(duong_vao) != len(moc_ms):
        raise MasterError(_t('Số đoạn và số mốc không khớp.'))
    Path(dich).parent.mkdir(parents=True, exist_ok=True)

    cmd = [media.ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error"]
    for d in duong_vao:
        cmd += ["-i", d]
    cmd += ["-filter_complex", bieu_thuc_lo(len(duong_vao), moc_ms, he_so),
            "-map", "[ra]",
            # ⭐ `-t` chan ban lo dung bang ca bai: mot doan dat gan cuoi va dai
            #    hon phan con lai se keo ban ra dai them, va cai do tich luy qua
            #    tung lo thanh mot ban phoi dai hon video.
            "-t", f"{max(0.001, float(tong_giay)):.3f}",
            "-ac", str(SO_KENH), "-ar", str(TAN_SO), "-c:a", "pcm_s16le", dich]
    try:
        r = _chay(cmd, timeout=timeout, hoi_huy=hoi_huy)
    except subprocess.TimeoutExpired as exc:
        raise MasterError(_t('Trộn lô tiếng quá hạn.')) from exc
    if r.returncode != 0:
        raise MasterError(_t('Trộn lô tiếng thất bại: {loi}').format(
            loi=(r.stderr or b"").decode("utf-8", "replace")[-300:]))
    return dich


def tron_cuoi(nen: str, cac_lo: list[str], dich: str, *, tong_giay: float,
              hoi_huy=None, timeout: int = 1800) -> str:
    """Tron ban nen (da ha muc) voi cac ban lo tieng, roi chuan am luong.

    ⭐ Chuan am luong **mot lan o cuoi**, khong phai o tung lo: `loudnorm` doi
       muc cua ca dong tin hieu, nen chay no tren tung manh roi cong lai cho ra
       mot ket qua khong ai du doan duoc.
    """
    Path(dich).parent.mkdir(parents=True, exist_ok=True)
    cmd = [media.ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error",
           "-i", nen]
    for d in cac_lo:
        cmd += ["-i", d]

    n = 1 + len(cac_lo)
    phan = [f"[0:a]volume={NEN_GIAM_DB}dB,"
            f"aformat=sample_fmts=fltp:sample_rates={TAN_SO}:"
            f"channel_layouts=stereo[nen];"]
    for i in range(1, n):
        phan.append(f"[{i}:a]aformat=sample_fmts=fltp:sample_rates={TAN_SO}:"
                    f"channel_layouts=stereo[t{i}];")
    nhan = "[nen]" + "".join(f"[t{i}]" for i in range(1, n))
    phan.append(f"{nhan}amix=inputs={n}:normalize=0:dropout_transition=0[tron];")
    # ⚠️ `dual_mono=true` — mot bai hoc DA TRA GIA o pha 18 cua ban truoc, mang
    #    sang day nguyen ven: mot doan tieng MONO da qua `aformat` thanh stereo
    #    se bi `loudnorm` **do to hon thuc te 3 dB** neu thieu co nay. May sinh
    #    tieng tra ve mono, nen truong hop do khong phai gia dinh — no la duong
    #    chay binh thuong.
    #
    # ⭐ Va no la loai khiem khuyet khong bao gio duoc bao cao: khach khong nghe
    #    ra "sai 3 dB", ho chi thay ban long tieng "hoi to".
    phan.append(f"[tron]loudnorm=I={lufs_dich()}:TP={dinh_that_db()}"
                f":LRA=11:dual_mono=true[ra]")

    cmd += ["-filter_complex", "".join(phan), "-map", "[ra]",
            "-t", f"{max(0.001, float(tong_giay)):.3f}",
            "-ac", str(SO_KENH), "-ar", str(TAN_SO), "-c:a", "pcm_s16le", dich]
    try:
        r = _chay(cmd, timeout=timeout, hoi_huy=hoi_huy)
    except subprocess.TimeoutExpired as exc:
        raise MasterError(_t('Trộn bản phối quá hạn.')) from exc
    if r.returncode != 0:
        raise MasterError(_t('Trộn bản phối thất bại: {loi}').format(
            loi=(r.stderr or b"").decode("utf-8", "replace")[-300:]))
    return dich


def chia_lo(n: int, *, moi_lo: int | None = None) -> list[tuple[int, int]]:
    """Chia `n` doan thanh cac lo `[bat, ket)`.

    ⛔ `moi_lo=None` chu khong phai `moi_lo=DOAN_MOI_LO`: mot gia tri mac dinh
       duoc gan LUC DINH NGHIA HAM, nen doi hang so sau do khong doi duoc gi.
       Bai hoc nay tra gia o pha 14 (`long_tieng.chia_lo`).
    """
    k = max(1, int(moi_lo if moi_lo is not None else DOAN_MOI_LO))
    return [(i, min(n, i + k)) for i in range(0, max(0, n), k)]


def van_tay_master(*, van_tay_nen: str, van_tay_ke_hoach: str,
                   van_tay_ban_do: str, phien_ban_ffmpeg_: str) -> str:
    """Van tay cua ban phoi.

    Nam thanh phan, thieu bat cu cai nao deu lam cache noi doi: ban nen · ke
    hoach dat doan · ban do cat · phien ban cong cu · phien ban ma.
    """
    goi = json.dumps({
        "nen": van_tay_nen,
        "ke_hoach": van_tay_ke_hoach,
        "ban_do": van_tay_ban_do,
        "ffmpeg": phien_ban_ffmpeg_,
        "nen_giam_db": NEN_GIAM_DB,
        "lufs": lufs_dich(),
        "dinh": dinh_that_db(),
        "phien_ban": PHIEN_BAN_MASTER,
    }, sort_keys=True)
    return hashlib.sha256(goi.encode("utf-8")).hexdigest()


def kiem_ban_ra(duong: str, *, mong_doi_giay: float, dung_sai_giay: float) -> dict:
    """Do ban phoi THAT va doi chieu voi thoi luong mong doi.

    ⛔ Do tren TEP, khong tin bat cu con so nao ta tu tinh: ca pha nay la mot
       chuoi phep tinh, va mot phep tinh sai se cho ra mot ke hoach dep va mot
       tep sai. Chi phep do tren tep moi phan biet duoc hai thu do.
    """
    from . import nhap_media, tach_tieng

    tt = nhap_media.soi(duong)
    if tt["tan_so"] != TAN_SO:
        raise MasterError(_t('Bản phối sai tần số lấy mẫu.'))
    if tt["so_kenh"] != SO_KENH:
        raise MasterError(_t('Bản phối sai số kênh.'))
    lech = float(tt["thoi_luong"]) - float(mong_doi_giay)
    if abs(lech) > float(dung_sai_giay):
        raise MasterError(
            _t('Bản phối lệch thời lượng {lech} giây so với dự kiến.')
            .format(lech=round(lech, 3)))
    am = tach_tieng.do_am_luong(duong)
    return {"thoi_luong": round(float(tt["thoi_luong"]), 3),
            "lech_giay": round(lech, 3), **am}

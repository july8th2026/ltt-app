r"""SOAT XUAT XU + CURATE mot giong — nua con lai cua U-05/U-04.

## ⛔ Vi sao tep nay PHAI ton tai, va vi sao thieu no la mot loi NANG

`tham_chieu._dieu_kien_kho_chung()` chi cho giong co `license_status == "ok"`
ra kho chung. Migration dat MOI dong thanh `"cho_soat"`.

Neu khong co duong nao GHI cot ay, cong ay la mot **canh cua mot chieu khong co
chia**: truoc ban va, `dung_chung=True` la du; sau ban va no la CAN nhung KHONG
DU, va dieu kien du thi khong dat toi duoc.

⭐ Do dung la lop loi `DECISIONS.md::DV-010` da ghi — *"ba duong ong co du khop
   noi ma chua bao gio co nuoc"* — va lan nay no bi mac boi chinh luot sua viet
   canh bao ve no. Mot bang doc duoc ma khong ai ghi trong **y het** mot bang
   dang hoat dong.

## 🔴 VI SAO LA MOT CONG CU DONG LENH, KHONG PHAI MOT NUT TREN WEB

Day la mot phan quyet ve **quyen**, khong phai mot thao tac van hanh:

- No khong dao nguoc duoc ve mat thuc te. Mot giong da ra kho chung la mot giong
  moi tai khoan da co the doc, va viec rut lai khong lay lai duoc nhung gi da
  sinh ra.
- No can **bang chung ngoai he thong** — giay uy quyen, dieu khoan cua ben cap
  giong, mot email. Khong thu nao trong so do nam trong CSDL.
- Va no can mot NGUOI chiu trach nhiem. Mot nut tren web moi nguoi ta bam;
  mot lenh CLI buoc nguoi ta go ly do.

⇒ Bat buoc `--ly-do` o CA HAI chieu. Duyet ma khong ghi can cu thi ban ghi
  license tro thanh mot o trong dep de — va no sinh ra de duoc trich dan trong
  mot tranh chap.

## Dung

    python tools\soat_giong.py xem
    python tools\soat_giong.py xem --tat-ca

    python tools\soat_giong.py duyet   <public_id> --ly-do "..."
    python tools\soat_giong.py tu-choi <public_id> --ly-do "..."
    python tools\soat_giong.py thieu-bang-chung <public_id> --ly-do "..."

[!] `duyet` chi doi `license_status`. No KHONG bat `dung_chung`. Hai buoc, vi
    do la hai cau hoi khac nhau: *"xuat xu co ro khong"* va *"ta co MUON mang
    no ra kho chung khong"*.
"""
from __future__ import annotations

import argparse
import sys

#: `lenh` -> (license_status, trang_thai_curate)
#:
#: [!] Bang nay la NGUON DUY NHAT cua phep anh xa. Go tay tung nhanh trong ham
#:     `main` la cach hai lenh doi hai kieu roi lech nhau.
ANH_XA = {
    "duyet": ("ok", "accepted"),
    "tu-choi": ("tu_choi", "rejected"),
    "thieu-bang-chung": ("thieu_bang_chung", "rejected"),
}

#: Do dai toi thieu cua ly do. Khong phai de lam kho nguoi dung.
#:
#: [!] Mot ly do "ok" hay "x" la mot o da dien ma khong phai mot cau tra loi, va
#:     no te hon o trong: o trong thi nguoi doc biet la chua ai soat, con "ok"
#:     thi trong nhu da soat.
LY_DO_TOI_THIEU = 12


def _phien():
    from platform_core.db import get_session
    return get_session()


def _in_bang(cac) -> None:
    print(f"{'public_id':<24} {'license':<18} {'curate':<12} {'chung':<6} ten")
    print("-" * 88)
    for ho_so, cur in cac:
        print(f"{ho_so.public_id:<24} {ho_so.license_status:<18} "
              f"{(cur.trang_thai_curate if cur else '-'):<12} "
              f"{('CHUNG' if ho_so.dung_chung else '-'):<6} {ho_so.ten_hien_thi}")
        if cur is not None and cur.ly_do_loai:
            print(f"{'':<24} ly do: {cur.ly_do_loai}")


def _lay(db, public_id: str):
    from sqlalchemy import select

    from apps.ltt_voice.tables import VoiceProfile, VoiceQualityProfile
    ho_so = db.execute(select(VoiceProfile).where(
        VoiceProfile.public_id == public_id)).scalar_one_or_none()
    if ho_so is None:
        return None, None
    cur = db.execute(select(VoiceQualityProfile).where(
        VoiceQualityProfile.profile_id == ho_so.id)).scalar_one_or_none()
    return ho_so, cur


def _xem(db, tat_ca: bool) -> int:
    from sqlalchemy import select

    from apps.ltt_voice.tables import VoiceProfile
    q = select(VoiceProfile).order_by(VoiceProfile.dung_chung.desc(),
                                      VoiceProfile.tao_luc.desc())
    ds = list(db.execute(q).scalars())
    if not tat_ca:
        # Mac dinh chi hien thu DANG CHO mot quyet dinh: giong dung chung ma
        # chua duoc duyet. Do la danh sach viec, khong phai ca kho.
        ds = [g for g in ds if g.dung_chung and g.license_status != "ok"]
        if not ds:
            print("Khong giong dung chung nao dang cho soat. (`--tat-ca` de "
                  "xem het.)")
            return 0
    _in_bang([(g, _lay(db, g.public_id)[1]) for g in ds])
    return 0


def _dat(db, public_id: str, lenh: str, ly_do: str, nguoi: str) -> int:
    from apps.ltt_voice.tables import VoiceQualityProfile

    lic, cur_tt = ANH_XA[lenh]
    ho_so, cur = _lay(db, public_id)
    if ho_so is None:
        print(f"⛔ Khong co giong `{public_id}`.")
        return 2

    truoc = ho_so.license_status
    ho_so.license_status = lic
    if cur is None:
        cur = VoiceQualityProfile(profile_id=ho_so.id)
        db.add(cur)
    cur.trang_thai_curate = cur_tt
    # [!] GHI LY DO O CA HAI CHIEU. `ly_do_loai` mang ten "ly do LOAI" nhung no
    #     giu can cu cua moi phan quyet - ke ca phan quyet DUYET. Mot ban ghi
    #     chi giai thich duoc mot nua so quyet dinh la mot ban ghi se bi hoi
    #     dung vao nua con lai.
    cur.ly_do_loai = ly_do
    cur.nguoi_soat = nguoi
    db.commit()

    print(f"{public_id}: license {truoc} -> {lic} · curate {cur_tt}")
    print(f"  ly do : {ly_do}")
    print(f"  nguoi : {nguoi}")
    if truoc == "ok" and lic != "ok" and ho_so.dung_chung:
        # [!] RUT LICENSE THI XOA LUON BAN NGHE THU KHO CHUNG DA DUNG.
        #     Lop 1 - CUA DOC: tu RC1 (eb896da7) `routes/_p_audio.py` chi phuc
        #     vu `voice/chung/*.wav` khi giong CON dung_chung + license ok +
        #     active (tra CSDL), nen ngay sau lenh nay tep da KHONG tai duoc.
        #     Lop 2 - O DAY: xoa TAI NGUON, vi day la tieng noi cua mot nguoi
        #     that - khong de no nam lai trong kho sau khi giay to bi rut. Cung
        #     lop voi `giong_vong_doi.khoa_da_biet` (thu hoi / doi lan).
        #
        #     Best-effort nhu `_p_giong._xoa_khoa`: phan quyet da commit, mot
        #     kho chap khong duoc lam no nem - nhung phai NOI RA de xoa tay.
        from apps.ltt_voice import nghe_thu
        from platform_core.storage import get_storage
        khoa = nghe_thu.khoa_chung(str(ho_so.public_id))
        try:
            get_storage().delete(khoa)
        except Exception as e:  # noqa: BLE001 - xem tren
            # ASCII co y: `print` mot emoji tren console cp1252 se nem
            # UnicodeEncodeError - dung ngay trong nhanh "khong duoc nem".
            print(f"  [!] KHONG xoa duoc ban nghe thu kho chung `{khoa}` "
                  f"({e!r}) - cua doc da chan no, nhung tep VAN nam trong "
                  "kho: xoa tay.")
    if lic == "ok" and not ho_so.dung_chung:
        # [!] NOI RA, KHONG TU BAT. Duyet xuat xu va quyet dinh mang ra kho
        #     chung la hai cau hoi khac nhau, va gop chung lai la cach mot lenh
        #     "ghi nhan giay to" bong tro thanh mot lenh xuat ban.
        print("  ⚠️ Giong nay CHUA `dung_chung`. Xuat xu da ro, nhung no van "
              "chua ra kho chung — do la mot quyet dinh RIENG.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Soat xuat xu + curate giong")
    sp = ap.add_subparsers(dest="lenh", required=True)

    p_xem = sp.add_parser("xem", help="liet ke giong dang cho soat")
    p_xem.add_argument("--tat-ca", action="store_true", help="hien ca kho")

    for ten in ANH_XA:
        p = sp.add_parser(ten)
        p.add_argument("public_id")
        p.add_argument("--ly-do", required=True,
                       help="can cu cua phan quyet — BAT BUOC ca hai chieu")
        p.add_argument("--nguoi", default="", help="ai soat (mac dinh: user OS)")

    a = ap.parse_args(argv)

    # [!] KIEM DAU VAO TRUOC KHI MO KET NOI, khong phai sau.
    #
    #     Ban dau mo phien CSDL roi moi kiem `--ly-do`, va no sai theo hai
    #     huong cung luc: mot ket noi mo ra cho mot dau vao chac chan bi tu
    #     choi, va mot phep kiem thuan-dau-vao bong doi mot CSDL song de chay.
    #     Vong thu hai la vong dat: no lam phep kiem cua chinh no thanh mot
    #     phep kiem tich hop.
    ly_do = ""
    nguoi = ""
    if a.lenh != "xem":
        ly_do = (a.ly_do or "").strip()
        if len(ly_do) < LY_DO_TOI_THIEU:
            print(f"⛔ `--ly-do` phai it nhat {LY_DO_TOI_THIEU} ky tu. Mot ly do "
                  f"'ok' la mot o da dien ma khong phai mot cau tra loi.")
            return 2
        import getpass
        nguoi = (a.nguoi or getpass.getuser() or "?")[:36]

    gen = _phien()
    db = next(gen)
    try:
        if a.lenh == "xem":
            return _xem(db, a.tat_ca)
        return _dat(db, a.public_id, a.lenh, ly_do, nguoi)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


if __name__ == "__main__":
    sys.exit(main())

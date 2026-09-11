"""CAT DAU CUOI — cua so thoi gian khach chon de giu lai.

## Mot module rieng, cung ly do voi `vung_che`

Quy tac thoi gian phai dung o ba noi: khi khach keo (giao dien), khi ta luu
(`run.settings`), khi ta thi hanh (`giai_doan_ban_dung`). Ba noi doc mot module
thi chung khong the lech nhau.

## Bon luat — CHUNG mot bo voi `vung_che`, khong phai mot bo thu hai

**L1 — Toa do la PHAN SO 0..1 cua THOI LUONG, khong bao gio giay.**
Y het L1 cua `vung_che`, chi doi truc. Mot con so tinh bang giay tro thanh sai
ngay khi ban proxy xem truoc co do dai khac ban goc. Doi sang giay xay ra dung
MOT cho — `giai_doan_ban_dung`, noi biet thoi luong that.

**L2 — Sai thi TU CHOI, khong DOAN.** Cua so nguoc (`den <= tu`) khong duoc tu
dao lai. Mot cua so bi "sua ho" thanh hop le se duoc thi hanh — tuc ta cat mot
doan khach khong chon, va khach khong co cach nao biet.

**L3 — CHI o preset cat.** Preset giu hinh di `-c:v copy` va hua *"do dai ra
bang do dai vao"* (`hop_dong_v4.DUNG_SAI_DO_DAI_S = 0.50`). Cat thi pha loi hua
ay.

⚠️ **L3 khac han L3 cua `vung_che`, va cho khac nhau moi la cho quan trong.**
   Vung che khong the co o preset giu hinh vi mot rang buoc **VAT LY**:
   `-c:v copy` khong giai ma khung nao, nen khong co diem anh nao de sua. Trim
   thi lam duoc ve mat ky thuat — `-ss`/`-to` cat duoc tren stream copy. No bi
   cam vi mot quyet dinh **SAN PHAM**.

⇒ Nen dung noi "khong the" voi trim. Noi "khong o che do nay", va noi ly do.

**L4 — `(0.0, 1.0)` ≡ VANG MAT.** Khong thu hep gi thi khong ghi gi. Nguoc lai
moi van tay cu doi trong khi khong mot khung hinh nao doi — tuc phuc vu lai
toan bo cache cho khong viec gi. Cung luat L4 cua `vung_che`, phat bieu tren
truc thoi gian.

⭐ Va cua so nay **tu duoc van tay hoa**: no thu hep `ban_do.giu`, `khoang_giu`
   da nam trong ban dung, va ban dung da nam trong van tay. Khong can them mot
   truong nao vao `van_tay_che_do` — khac han `vung_che`, thu **phai** duoc
   them tay vao bam.
"""
from __future__ import annotations

from platform_core.i18n import _ as _t

from . import hinh_hoc

#: Cua so ngan hon the thi moi phep chia thoi gian phia sau vo: `nan_cho_vua`
#: chia do dai tieng doc cho do dai khe, va mot khe vai phan tram giay cho ra
#: mot he so nen khong bo loc nao thuc hien duoc.
TOI_THIEU = 0.02


class CatLoi(ValueError):
    """Cua so cat khong dung. Thong bao LA cau tieng Viet cho khach doc."""


def chuan_hoa(tho) -> tuple[float, float] | None:
    """`[bat_dau, ket_thuc]` phan so -> cap da duyet, hoac `None` neu ca video.

    ⛔ **Khong sua ho.** Xem L2 o dau tep.
    """
    if tho is None or (isinstance(tho, (str, list, tuple)) and len(tho) == 0):
        return None
    # ⭐ Di tru sang `hinh_hoc` o pha 08b. Chan `NaN`/`inf` la CUNG mot luat
    #    voi `vung_che` va `lop_phu`; ba ban cua no la ba ban se lech im lang.
    #
    # ⚠️ Nhung phep so sanh `a < b` thi O LAI DAY, va do la ranh gioi dung:
    #    `hinh_hoc.so_phan_so` doc MOT so trong MOT khoang. Quan he giua HAI so
    #    la luat cua chinh truc nay (mot cua so cat), khong phai luat chung —
    #    gom no vao module chung se buoc module do biet ve khai niem "cua so",
    #    tuc keo mot khai niem cua mien nay vao mot cho chi biet hinh hoc.
    try:
        a, b = tho
    except (TypeError, ValueError):
        raise CatLoi(_t('Đoạn cắt không đọc được.')) from None
    _ngoai = _t('Đoạn cắt phải nằm trong video và điểm đầu phải trước điểm cuối.')
    a, b = [hinh_hoc.so_phan_so(
        x, thap=0.0, cao=1.0, loi=CatLoi,
        khong_doc_duoc=_t('Đoạn cắt không đọc được.'),
        ngoai_khoang=_ngoai) for x in (a, b)]
    if not (0.0 <= a < b <= 1.0):
        raise CatLoi(
            _t('Đoạn cắt phải nằm trong video và điểm đầu phải trước điểm cuối.'))
    if b - a < TOI_THIEU:
        raise CatLoi(_t('Đoạn cắt quá ngắn.'))
    if a == 0.0 and b == 1.0:
        return None                      # L4
    return (a, b)


def giao(khoang, cua_so, thoi_luong: float) -> list[tuple[float, float]]:
    """Giao cac khoang GIU voi cua so cat. Don vi vao/ra deu la GIAY.

    ⛔ Nem `CatLoi` khi cua so khong cham khoang giu nao.

       `ban_dung.dung` cung nem cho ca nay, nhung thong diep cua no noi ve *"ban
       dung khong co khoang nao"* — mot khach vua keo hai tay cam khong co cach
       nao noi cau do voi viec ho vua lam. Loi phai ke ten thu khach vua cham.
    """
    if not cua_so or thoi_luong <= 0:
        return [(float(b), float(k)) for b, k in khoang]
    tu, den = cua_so[0] * thoi_luong, cua_so[1] * thoi_luong
    ra: list[tuple[float, float]] = []
    for b, k in khoang:
        b, k = max(float(b), tu), min(float(k), den)
        if k - b > 0:
            ra.append((b, k))
    if not ra:
        raise CatLoi(
            _t('Đoạn cắt bạn chọn không còn lại phần nào để dựng. '
               'Hãy chọn một đoạn khác.'))
    return ra

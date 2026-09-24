"""VUNG CHE — hop toa do chuan hoa ma khach ve tren khung hinh.

## Mot module rieng, khong phai vai ham trong `routes.py`

`routes.py` chi lo HTTP (hop dong app, tran 900 dong). Cai o day la **quy tac
hinh hoc**, va no phai dung o ca ba noi: khi khach ve (giao dien), khi ta luu
(ban dung), va khi ta thi hanh (trinh render). Ba noi doc cung mot module thi
chung khong the lech nhau.

## Bon luat, va ca bon deu do mot he thong khac tra gia de hoc

`docs/auto_scan_video_v5/VIRAL_RENDER_FEATURE_MAP.md` §3 ghi day du xuat xu.
Tom tat vi sao chung o day:

**L1 — Toa do la PHAN SO 0..1, khong bao gio pixel.**
Video doi do phan giai (proxy xem truoc 480p, ban goc 1080p, ban ra sau khi
doi ti le) thi mot hop tinh bang pixel tro thanh sai o hai trong ba ban. Mot
hop tinh bang phan so dung o ca ba.

**L2 — Sai dinh dang hay ngoai khoang thi TU CHOI, khong DOAN.**
He thong tham chieu doc `"y0,y1"`; sai thi tra `None` va **khong doan**. Day la
hanh vi dung, va ly do sau hon: mot hop bi "sua hoc" thanh mot hop hop le se
duoc thi hanh — tuc ta che nham mot vung khach khong chon, va khach khong co
cach nao biet. Tu choi o cua thi ho biet ngay.

**L3 — Bien doi hinh lam hop ra ngoai khung thi LOAI hop, khong KEP ve bien.**
🔴 Day la luat dat nhat trong bon. He thong tham chieu tung kep ve bien, va
   `localize.py:675` ghi lai hau qua (loi zoom 2026-07): kep ve bien **che nham
   mot vung trong** — dung cho chu da bien mat khoi khung. Tuc bug khong hien ra
   nhu "thieu mot o che", no hien ra nhu "co mot vet mo la o goc man hinh".

⭐ **asv-final 22/09 (`ADR_BIEN_TAP.md`): `zoom`/`crop`/`reframe` da mo, va L3
   dung THEO CAU TRUC chu khong bang mot ham anh xa:** vung che ap TRUOC chang
   khung trong chuoi loc (toa do nguon), nen vung nam ngoai cua so cat chi don
   gian khong con trong khung — khong co gi de kep. Bang chung do tren tep ra:
   `test_2062::test_L3_vung_che_NGOAI_cua_so_cat_khong_de_lai_vet`.

⚠️ (Lich su) **L3 chua co ma o day, va do la co y.** `zoom` dang bi
   `hop_dong_v4.CAM_TRONG_MVP` cam, nen mot ham anh xa toa do se **khong co
   nguoi goi** — va `test_453` goi dung ten cho thu do: mot nang luc viet xong
   roi quen noi vao mach. Ban dau toi co viet no; gate chan lai, va gate dung.

⇒ Luat song o **tai lieu** cho toi khi tinh nang duoc mo:
  `docs/auto_scan_video_v5/V5_UI_INFORMATION_ARCHITECTURE.md` §11 luat 3 ghi ca
  cong thuc (`p' = 0.5 + Z*(p - 0.5)`) lan bang chung. Ngay mot ADR-V5 mo `zoom`,
  viec dau tien la hien thuc no **kem phep kiem cho hop bi cat mat**.

**L4 — Vung phai vao khoa bam cua ban dung.**
Doi vung ma khoa khong doi la phuc vu lai ket qua cu. Cuong che o
`ban_dung.py`, khong o day — nhung ghi o day vi day la noi nguoi doc dang nghi
ve vung.
"""
from __future__ import annotations

from platform_core.i18n import _ as _t

from . import hinh_hoc

#: Che kin mot vung bang mot o mo. Khong xoa gi — chi lam khong doc duoc.
LOAI_LAM_MO = "lam_mo"

#: Danh dau noi co chu goc, de trinh dung KHONG dat phu de dich chong len do.
#:
#: ⚠️ Day **khong** phai "dot phu de vao hinh": `CAM_TRONG_MVP` cam
#:    `subtitle_burn` vi `apps/autosubvideo` da so huu viec do. Vung nay chi
#:    mang mot y nghia AM: *dung ve gi o day*.
LOAI_DANH_DAU_PHU_DE = "danh_dau_phu_de"

LOAI: tuple[str, ...] = (LOAI_LAM_MO, LOAI_DANH_DAU_PHU_DE)

#: ⛔ Danh sach nay CO Y ngan. Cac loai vung khac cua he thong tham chieu — xoa
#:    bang dien nen, tu do logo, logo cua toi, chu watermark — deu dang `DEFER`
#:    trong `FEATURE_PARITY_MATRIX.md`, hai vi chua do VRAM va hai vi nam trong
#:    `HAU_MVP`. Them mot ma vao day ma khong do truoc la mo mot job GPU khong
#:    khai — dung dieu `pipeline.py` da ghi la mot chot tai, khong phai mot chi
#:    tiet toi uu.

#: So vung toi da mot lan chay. Khong phai mot gioi han ky thuat — mot man hinh
#: co hai muoi o che la mot man hinh khach da lac huong, va moi vung la mot bo
#: loc ffmpeg nua trong cung mot lan encode.
SO_VUNG_TOI_DA = 12

#: Canh nho nhat, tinh theo phan so. Mot hop 0,002 rong la mot lan click nham
#: chu khong phai mot y dinh, va no van ton mot bo loc.
CANH_TOI_THIEU = 0.01


class VungLoi(ValueError):
    """Toa do khong dung. Thong bao LA cau tieng Viet cho khach doc."""


def _so(gia_tri, ten: str) -> float:
    """Doc mot toa do phan so. Luat song o `hinh_hoc`, cau tieng Viet o day.

    🔑 **Di tru o pha 08b, va no khong doi mot hanh vi nao.** Ban cu chan `NaN`
       va `inf` bang dung hai dong ay; `hinh_hoc.so_phan_so` chan cung hai thu
       do va nem cung hai cau ay.

    ⭐ Ly do di tru: ba ban cua mot quy tac la ba ban se lech IM LANG — mot ban
       quen chan `NaN` van xanh o moi phep kiem cua chinh no, vi `float("nan")`
       doc duoc va MOI phep so sanh voi no deu `False`.

    ⚠️ Cau noi voi khach thi KHONG gom: no phai noi ve thu khach vua lam
       (*"vùng che"*, *"lớp phủ"*, *"logo"*), va mot cau chung chung buoc ho doan
       minh sai o dau.
    """
    return hinh_hoc.so_phan_so(
        gia_tri, thap=0.0, cao=1.0, loi=VungLoi,
        khong_doc_duoc=_t('Vùng che có toạ độ không đọc được.'),
        ngoai_khoang=_t('Vùng che nằm ngoài khung hình.'))


def chuan_hoa_mot(tho: dict) -> dict:
    """Mot hop tho tu giao dien -> mot hop da kiem. Nem `VungLoi` khi sai.

    ⛔ **Khong sua hoc.** Hop nguoc (y1 < y0) bi TU CHOI chu khong bi doi cho —
       xem L2 o dau tep. Mot hop bi doi cho la mot hop khach khong ve.
    """
    if not isinstance(tho, dict):
        raise VungLoi(_t('Vùng che không đọc được.'))

    loai = str(tho.get("loai") or "").strip()
    if loai not in LOAI:
        raise VungLoi(_t('Loại vùng che không hợp lệ.'))

    y0 = _so(tho.get("y0"), "y0")
    y1 = _so(tho.get("y1"), "y1")
    x0 = _so(tho.get("x0"), "x0")
    x1 = _so(tho.get("x1"), "x1")
    if y1 - y0 < CANH_TOI_THIEU or x1 - x0 < CANH_TOI_THIEU:
        raise VungLoi(_t('Vùng che quá nhỏ hoặc bị vẽ ngược.'))

    ra = {"loai": loai, "y0": y0, "y1": y1, "x0": x0, "x1": x1}

    # Khoang thoi gian: rong = ap ca video. Luat o `hinh_hoc.khoang_thoi_gian`.
    #
    # ⚠️ Ban cu o day KHONG chan `NaN` cho `tu_giay`/`den_giay` (chi ban cua
    #    `lop_phu` co). Di tru mang phep chan ay sang day — tuc no SIET hon ban
    #    cu, khong phai loi ngang.
    ra.update(hinh_hoc.khoang_thoi_gian(
        tho, loi=VungLoi,
        khong_doc_duoc=_t('Khoảng thời gian của vùng che không đọc được.'),
        khong_hop_le=_t('Khoảng thời gian của vùng che không hợp lệ.')))
    return ra


def chuan_hoa(danh_sach) -> list[dict]:
    """Ca mang vung. Rong la hop le — phan lon lan chay khong co vung nao."""
    if danh_sach in (None, "", []):
        return []
    if not isinstance(danh_sach, (list, tuple)):
        raise VungLoi(_t('Danh sách vùng che không đọc được.'))
    if len(danh_sach) > SO_VUNG_TOI_DA:
        raise VungLoi(_t('Quá nhiều vùng che trong một lần chạy.'))
    return [chuan_hoa_mot(v) for v in danh_sach]

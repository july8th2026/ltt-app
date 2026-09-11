"""LOGO — mot ANH khach dan len khung hinh, o toa do phan so.

## Vi sao mot module rieng chu khong phai mot `loai` cua `lop_phu`

Hai thu dung chung mot bo loc ho hang (`overlay` vs `drawtext`) va dung chung
bon luat hinh hoc — nhung ba thu quan trong nhat cua chung thi khac han:

    lop phu chu : phong chu · vien · bang ma · **noi dung do khach GO**
    logo        : mot ARTIFACT trong kho · ti le khung · **do khach TAI LEN**

⛔ Va cai thu ba moi la ly do tach: mot logo la mot **khoa luu tru**, tuc no
   mang theo quyen so huu, vong doi, va mot cau hoi *"khoa nay co that su cua
   nguoi dang goi khong"* ma mot chuoi chu khong bao gio phai tra loi.

## Bon luat hinh hoc — dung cua `vung_che`, thi hanh o `hinh_hoc`

L1 phan so 0..1 · L2 sai thi TU CHOI khong DOAN · L3 ra ngoai khung thi LOAI
khong KEP · L4 phai vao van tay.

## 🔴 Co logo tinh bang PIXEL, va do la mot phep DO chu khong phai mot lua chon

Do tren may nay, nam cach dat co logo trong `filter_complex`:

    [1:v][0:v]scale2ref=w=iw*0.20:h=ow/mdar[lg][v]     OK
    [1:v]scale=w=128:h=-1[lg]                          OK
    ... ,format=rgba,colorchannelmixer=aa=0.5[lg]      OK  (do mo)
    ... :enable=between(t\\,a\\,b)                       OK
    [1:v]scale=w=127:h=-1[lg]  (chieu le)              OK

⇒ **Ca `scale2ref` lan `scale` px deu chay.** Nen day khong phai mot lua chon
  bi ep — no la mot lua chon, va ly do chon `scale` px:

  1. `scale2ref` **da bi danh dau deprecated** o dong ffmpeg moi. No chay tren
     may nay hom nay; mot ngay nao do no bien mat, va thu bat duoc dieu do se
     la mot phep kiem **nam sau rao `LTT_TEST_NANG`** — tuc mot phep kiem
     khong chay trong gate. Loi se toi tay khach truoc khi toi tay ta.
  2. Ta **da** mang `cao_khung` trong ban dung tu pha 11 (vi `borderw` khong
     nhan bieu thuc). Them `rong_khung` la mot truong nua trong cung mot dict,
     va no lam chuoi loc **doc duoc**: mot con so pixel that thay vi mot phep
     chia phu thuoc `mdar`.

⚠️ Cai gia: `rong_khung` phai co that. `ban_dung.kiem` tu choi mot ban dung co
   logo ma thieu no — cung khuon voi `cao_khung`.
"""
from __future__ import annotations

from platform_core.i18n import _ as _t

from . import hinh_hoc

#: So logo toi da mot lan chay. Nho hon `lop_phu` co y: moi logo la mot dau vao
#: ffmpeg NUA, mot phep giai ma nua, va mot artifact nua phai kiem quyen so huu.
SO_LOGO_TOI_DA = 2

#: Be rong logo, tinh theo PHAN SO be rong khung (L1). 0,03 tren 1920 la 58 px —
#: nho nhat con nhan ra; 0,4 la gan nua khung, da la mot lop phu chu khong phai
#: mot dau hieu.
RONG_TOI_THIEU = 0.03
RONG_TOI_DA = 0.40
RONG_MAC_DINH = 0.15

DO_MO_MAC_DINH = 1.0
DO_MO_TOI_THIEU = 0.05


class LogoLoi(ValueError):
    """Logo khong dung. Thong bao LA cau tieng Viet cho khach doc."""


def _so(gia_tri, *, thap: float, cao: float) -> float:
    return hinh_hoc.so_phan_so(
        gia_tri, thap=thap, cao=cao, loi=LogoLoi,
        khong_doc_duoc=_t('Logo có giá trị không đọc được.'),
        ngoai_khoang=_t('Logo có giá trị ngoài khoảng cho phép.'))


def chuan_hoa_mot(tho: dict) -> dict:
    """Mot logo tho tu giao dien -> mot ban da kiem. Nem `LogoLoi` khi sai.

    ⛔ **`khoa` KHONG duoc kiem quyen so huu o day.** Ham nay thuan hinh hoc; no
       khong co `db`, khong co `kho`, va khong biet ai dang goi. Kiem quyen o
       day se la mot phep kiem **trong veo** — no se nhin mot chuoi va noi "co".

    ⇒ Va cau hoi ay khong duoc TRA LOI o `features.gan_logo` — no **bien mat**
      o do: anh den tu chinh POST tao lan chay, khong tu mot ten do khach doc
      ra. Mot cau hoi khong ton tai thi khong the tra loi sai.
    """
    if not isinstance(tho, dict):
        raise LogoLoi(_t('Logo không đọc được.'))

    # 🔑 **`khoa` KHONG bat buoc, va do la mot quyet dinh hop dong.**
    #
    #    Anh di cung POST tao lan chay, va khoa artifact duoc MAY CHU dat sau khi
    #    `run.id` ton tai (`features.gan_logo`). Nen luc client gui, no chua the
    #    biet khoa — va **doi no gui mot khoa** la day no toi cho bia ra mot chuoi
    #    gia, roi ta ghi de len. Mot hop dong day nguoi ta toi viec bia du lieu la
    #    mot hop dong sai.
    #
    # ⚠️ Nhung khi khoa CO mat (doc lai tu `run.settings`), hinh dang cua no van
    #    phai dung: mot khoa chua `..` hay mot URL la mot khoa khong the do ta
    #    sinh ra. Quyen so huu thi khong kiem o day — xem docstring.
    khoa = str(tho.get("khoa") or "").strip()
    if khoa and (".." in khoa or "://" in khoa or khoa.startswith("/")):
        raise LogoLoi(_t('Logo trỏ tới một tệp không hợp lệ.'))

    ra = {
        "x": _so(tho.get("x"), thap=0.0, cao=1.0),
        "y": _so(tho.get("y"), thap=0.0, cao=1.0),
        "rong": _so(tho.get("rong", RONG_MAC_DINH),
                    thap=RONG_TOI_THIEU, cao=RONG_TOI_DA),
        "do_mo": _so(tho.get("do_mo", DO_MO_MAC_DINH),
                     thap=DO_MO_TOI_THIEU, cao=1.0),
    }
    if khoa:
        ra["khoa"] = khoa
    ra.update(hinh_hoc.khoang_thoi_gian(
        tho, loi=LogoLoi,
        khong_doc_duoc=_t('Khoảng thời gian của logo không đọc được.'),
        khong_hop_le=_t('Khoảng thời gian của logo không hợp lệ.')))
    return ra


def chuan_hoa(danh_sach) -> list[dict]:
    """Ca mang logo. Rong la hop le — phan lon lan chay khong co logo nao."""
    if danh_sach in (None, "", []):
        return []
    if not isinstance(danh_sach, (list, tuple)):
        raise LogoLoi(_t('Danh sách logo không đọc được.'))
    if len(danh_sach) > SO_LOGO_TOI_DA:
        raise LogoLoi(_t('Tối đa {n} logo trong một lần chạy.').format(
            n=SO_LOGO_TOI_DA))
    return [chuan_hoa_mot(v) for v in danh_sach]


def rong_px(mot: dict, rong_khung: int) -> int:
    """Be rong logo tinh bang PIXEL. Xem doan "co logo tinh bang PIXEL" o dau tep.

    ⚠️ Lam CHAN: `libx264` va `h264_nvenc` deu tu choi chieu le o `yuv420p` (lay
       mau 2x2), va thong bao cua ffmpeg khi do bao mot loi khoi tao encoder,
       khong nhac gi toi `scale`.

    ⭐ Do duoc: mot logo chieu LE (`scale=w=127`) van chay — vi `overlay` dan no
       len mot khung chan. Nhung ta khong dua vao dieu do: `scale` cua ffmpeg
       lam tron chieu con lai theo ti le, va mot chieu le o day co the thanh mot
       chieu le o cho khac sau nay.
    """
    rong = int(rong_khung or 0)
    if rong <= 0:
        raise LogoLoi(_t('Không biết chiều rộng khung hình để đặt logo.'))
    return max(2, (round(rong * float(mot["rong"])) // 2) * 2)

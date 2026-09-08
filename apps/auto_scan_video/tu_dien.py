"""Tu dien ten rieng cua khach: cach doc mot cai ten, do khach dat.

`apps/ltt_voice/text_pipeline.chuan_hoa` da nhan `tu_dien_rieng` tu truoc, va
`giong_noi` da truyen no suot bon cho. Thu duy nhat thieu la mot duong de khach
**cap** du lieu ay — nen tep nay khong them nang luc nao, no mo mot van da co.

## Bon luat, va ly do tung cai

**1. Sai thi TU CHOI, khong DOAN.** Mot dong `Nguyen Van A - Nguyen Van Ây`
   khong duoc tu hieu thanh dau `=`. Doan dung mot lan thi lan sau khach tin
   rang ta luon doan dung, va cai sai thu hai di thang vao tep tieng ho tra tien.

**2. Rong DONG NGHIA voi vang mat.** `{}` va `None` phai cho ra **cung** mot
   van tay. Neu khong, moi lan chay cu se doi van tay khi tinh nang nay len
   san, va ca kho tieng da sinh bi vut di ma khong ai yeu cau.

**3. No PHAI vao van tay doan.** Day la luat quan trong nhat va la thu de quen
   nhat: hai tu dien khac nhau tren **cung** mot cau chu se cho hai tep tieng
   khac nhau. Neu van tay khong doc tu dien, hai ket qua ay dung chung mot khoa
   luu tru, va khach thu hai nhan tieng cua khach thu nhat.

**4. Co tran.** Mot tu dien di **vao moi doan** cua mot lan chay, nen no nam
   trong vong lap noi tien duoc tinh. Mot tu dien khong tran la mot hoa don
   khong co day — cung ly do `giai_doan_giong` dat tran cho vong nan cho vua.
"""
from __future__ import annotations

from platform_core.i18n import _ as _t

#: Tran so muc. Du cho ten nguoi, dia danh, thuong hieu trong mot video; khong
#: du de bien o nay thanh mot kho du lieu.
SO_MUC_TOI_DA = 50

#: Tran do dai moi ve. Mot "ten rieng" dai hon the khong con la ten rieng.
DAI_TOI_DA = 80

#: Dau ngan cach DUY NHAT. Xem luat 1.
DAU = "="


class TuDienLoi(ValueError):
    """Khach nhap sai. Loi cua NGUOI DUNG, khong phai loi he thong."""


def phan_tich(tho: str) -> dict:
    """Van ban nhieu dong -> dict. Nem `TuDienLoi` neu sai.

    Moi dong: `Ten = cach doc`. Dong trong bi bo qua; dong khong co dau `=`
    thi **nem**, khong bo qua — mot dong bi lang le bo qua la mot cai ten khach
    tuong da duoc sua.
    """
    if not tho or not tho.strip():
        return {}

    ra: dict[str, str] = {}
    for so, dong in enumerate(tho.splitlines(), start=1):
        dong = dong.strip()
        if not dong:
            continue
        if DAU not in dong:
            raise TuDienLoi(_t(
                "Dòng %(so)d thiếu dấu bằng. Mỗi dòng viết dạng: Tên = cách đọc"
            ) % {"so": so})
        ten, _, doc = dong.partition(DAU)
        ten, doc = ten.strip(), doc.strip()
        if not ten or not doc:
            raise TuDienLoi(_t(
                "Dòng %(so)d thiếu tên hoặc cách đọc."
            ) % {"so": so})
        if len(ten) > DAI_TOI_DA or len(doc) > DAI_TOI_DA:
            raise TuDienLoi(_t(
                "Dòng %(so)d dài quá %(dai)d ký tự."
            ) % {"so": so, "dai": DAI_TOI_DA})
        if ten in ra:
            # ⛔ Khong lay cai sau de len cai truoc. Hai cach doc cho mot ten la
            #    mot mau thuan cua khach, va chon ho mot cai la doan.
            raise TuDienLoi(_t(
                "Tên %(ten)s được khai hai lần với hai cách đọc khác nhau."
            ) % {"ten": ten})
        ra[ten] = doc
        if len(ra) > SO_MUC_TOI_DA:
            raise TuDienLoi(_t(
                "Tối đa %(n)d mục trong một lần chạy."
            ) % {"n": SO_MUC_TOI_DA})
    return ra

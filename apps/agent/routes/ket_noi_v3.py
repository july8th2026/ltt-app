"""Cua HTTP cho **ket noi** cua khach (lan UI-5) — liet ke / tao / thu hoi.

## 🔴 VI SAO MO-DUN NAY TON TAI

`platform_core/credential.py` da hoan chinh tu 24/09: no ma hoa, xoay khoa
duoc, ghi nhat ky, va `dinh_nghia._kiem_credential` **chan o publish** khi mot
node doi `credential` ma thieu `credential_ref`. Do duoc 28/09 tren cong publish
that (`xuat_ban_draft`, mot node moi do thi, tham so da day du):

    node trong so node                            : 72
    node DOI credential                           : 34
    publish duoc khi KHONG co `credential_ref`    : 27
    publish duoc khi CO `credential_ref` dung kieu : 60
    => 33 node bi khoa dung MOT ly do: thieu ref

Va khong mot cua HTTP nao cho khach **tao** mot ref. Huy hieu *"Can ket noi"*
tren node noi dung su that, nhung no chi vao mot canh cua khong ton tai.

⇒ Mo-dun nay la **day noi**, khong phai mot lop luu tru thu hai. ⛔ Khong ma
  hoa gi o day, ⛔ khong doc `bi_mat_ma_hoa`, ⛔ khong them khoa nao vao `meta`.
  Moi duong di qua `platform_core.credential`.

## Ba luat bao mat, co hoc chu khong bang loi dan

1. **Be mat ra ngoai la `preview` + `meta`.** `credential.liet_ke` liet ke
   tuong minh tung khoa; mo-dun nay khong them khoa nao. ⛔ `bi_mat_ma_hoa`
   khong bao gio roi vao mot phan hoi.
2. **`meta` la o CONG KHAI.** Mot khoa trong `credential.META_CAM` gui len bi
   `_kiem_meta` nem `meta_co_bi_mat` ⇒ 422. Ta khong loc tay o day: mot ban
   loc thu hai se troi khoi ban goc.
3. **404 cho ca "khong co" va "cua nguoi khac".** `credential._hang` da loc
   `owner_id` **ngay trong truy van** va nem `khong_thay` cho ca hai ca — cung
   khuon `drafts_v3._cua_toi`. Phan biet hai ca la mot may dem cho nguoi ngoai
   biet id nao ton tai.

## ⭐ Hai TANG xac thuc (Q4 = C, chu du an chot 28/09 va nhan rui ro)

    self   khach mang bi mat cua chinh minh   -> CHAY THAT, day du
    cloud  LTT quan ly OAuth app              -> CAU TRUC + trang thai ro rang

Tang `cloud` chi bat cho mot nha cung cap khi **ca hai** bien moi truong
`LTT_OAUTH_<NHA_CUNG_CAP>_CLIENT_ID` va `..._CLIENT_SECRET` co mat. Thieu mot
cai ⇒ nha cung cap do bao `chua_cau_hinh`, kem **ten bien can dat**, va giao
dien noi thang *"LTT chua cau hinh cho nha cung cap nay"*.

🔴 Dang ky OAuth app voi Google/Slack/GitHub/Notion la viec **chi chu du an lam
   duoc** (dashboard ngoai, bi mat vao `secrets/app.env`). ⛔ Khong mot dong ma
   nao o day tu nhap bi mat, va ⛔ khong co luong gia vo hoat dong. Huong dan
   tung buoc: `tools/wizard_oauth_cloud.sh` (sinh boi lan UI-5).

⛔ Tang `cloud` KHONG suy tu mot danh sach nha cung cap go tay. Nguon la
   `connector.doc_catalog()` — nha cung cap nao co piece doi `oauth2` thi moi
   co the co mot OAuth app cua LTT. Mot piece moi vao catalog tu xuat hien o
   day; mot danh sach go tay thi khong.
"""
from __future__ import annotations

import logging
import os
import re

from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from apps.agent.routes._shared import _user, _verify_json_csrf, router
from platform_core import credential as kho
from platform_core.i18n import _ as _t
from platform_core.workflow import connector, nut
from server.auth.session import require_login
from server.deps import get_db

#: Tang xac thuc. Danh sach DONG — mot tang thu ba se phai khai o day va o
#: giao dien cung luc, chu khong lot qua bang mot chuoi tu do.
TANG_SELF = "self"
TANG_CLOUD = "cloud"

#: Chi `oauth2` can mot OAuth app dang ky truoc ⇒ chi no co tang `cloud`.
#: Moi `kieu` con lai la bi mat khach tu mang, khong co gi cho LTT quan ly.
KIEU_CAN_OAUTH_APP = ("oauth2",)

#: Hinh dang bi mat cua tung `kieu` — khoa BAT BUOC khach phai gui.
#: ⛔ Danh sach dong: mot khoa la trong bi mat la mot truong khong ai tiem, va
#:    no se ngoi trong kho da ma hoa cho tới lúc có người gỡ lỗi lúc chạy.
KHOA_BI_MAT = {
    "api_key": ("gia_tri",),
    "bearer": ("gia_tri",),
    "basic": ("ten_dang_nhap", "mat_khau"),
    "oauth2": ("client_id", "client_secret"),
    "google_service_account": ("json_khoa",),
    "piece_custom": ("gia_tri",),
}

#: Khoa hien bang o **che** (`type=password`). Moi khoa KHONG o day van la bi
#: mat va van duoc ma hoa — che hay khong chi la chuyen nguoi ben canh doc duoc
#: man hinh. `ten_dang_nhap`/`client_id` khong phai bi mat nen de nhin thay
#: giup khach kiem lai ma khong phai go lai.
KHOA_CHE = frozenset({"gia_tri", "mat_khau", "client_secret", "json_khoa"})

#: Khoa can o NHIEU DONG (mot JSON service account dai hang chuc dong).
KHOA_NHIEU_DONG = frozenset({"json_khoa"})

#: Ten ket noi do khach dat — gioi han bang chinh cot (`Credential.ten`).
_log = logging.getLogger(__name__)

_DAI_TEN = 120
#: `nha_cung_cap` la mot slug, khong phai chu tu do: no di vao ten bien moi
#: truong (`LTT_OAUTH_<...>_CLIENT_ID`), nen mot khoang trang o day la mot bien
#: khong bao gio doc duoc.
_SLUG = re.compile(r"^[a-z0-9_]{0,40}$")


def _bien_moi_truong(ma: str) -> tuple[str, str]:
    """Hai bien moi truong cua OAuth app do LTT quan ly cho nha cung cap `ma`.

    ⭐ MOT cho sinh ten bien, dung boi ca cua `/nha-cung-cap` va wizard. Hai
       cho sinh doc lap thi wizard huong dan dat mot bien ma may chu doc mot
       bien khac — va no im lang, vi "chua cau hinh" la mot trang thai hop le.
    """
    hoa = ma.upper()
    return (f"LTT_OAUTH_{hoa}_CLIENT_ID", f"LTT_OAUTH_{hoa}_CLIENT_SECRET")


def _nha_cung_cap_cua_piece(piece: str) -> str:
    """`@activepieces/piece-google-drive` -> `google_drive`.

    ⛔ Khong mot bang tra nao: catalog khai `piece`, ta chi chuan hoa hinh
       dang. Mot piece moi khong doi mot dong nao o day.
    """
    duoi = str(piece or "").rsplit("/", 1)[-1]
    for tien_to in ("piece-", "piece_"):
        if duoi.startswith(tien_to):
            duoi = duoi[len(tien_to):]
            break
    return duoi.replace("-", "_").lower()


def _nha_cung_cap_cua_node(loai: str) -> str:
    """Nha cung cap cua mot node KHONG phai piece (`connector.youtube.upload`).

    Lay doan giua cua `type`. ⛔ Khong ap cho `core.*`: `core.http` goi tuy y
    dia chi nao, nen no khong thuoc nha cung cap nao — va mot OAuth app cua LTT
    cho "http" la vo nghia.
    """
    phan = str(loai or "").split(".")
    if len(phan) >= 3 and phan[0] != "core":
        return phan[1].lower()
    return ""


def _so_nha_cung_cap() -> dict:
    """`{ma: {ten, kieu, node_type}}` — dung tu catalog piece + so node loi.

    ⭐ Nguon la `nut.tat_ca()`, tuc **cung so** ma palette va cong publish doc.
       Mot nha cung cap chi xuat hien khi co that mot node doi credential cua
       no; khong co node thi khong co dong nao moi khach ket noi.
    """
    theo_type = {str(m.get("type")): _nha_cung_cap_cua_piece(m.get("piece", ""))
                 for m in connector.doc_catalog()}
    ra: dict[str, dict] = {}
    for loai, nd in nut.tat_ca().items():
        kieu = tuple(getattr(nd, "credential", ()) or ())
        if not kieu:
            continue
        ma = theo_type.get(loai) or _nha_cung_cap_cua_node(loai)
        if not ma:
            continue
        muc = ra.setdefault(ma, {"ma": ma, "kieu": set(), "node_type": set()})
        muc["kieu"].update(kieu)
        muc["node_type"].add(loai)
    return ra


def _tang_cua(ma: str, kieu: set) -> dict:
    """Trang thai tang `cloud` cua mot nha cung cap. ⛔ Khong tra bi mat nao —
    chi mot cai co `san_sang` va TEN hai bien can dat."""
    bien = _bien_moi_truong(ma)
    if not any(k in kieu for k in KIEU_CAN_OAUTH_APP):
        return {"co_tang_cloud": False, "san_sang": False, "ly_do": "",
                "bien_moi_truong": []}
    du = all(str(os.environ.get(b, "")).strip() for b in bien)
    return {"co_tang_cloud": True, "san_sang": du,
            # ⭐ Mot ma, khong mot cau — giao dien dich no. Mot cau tieng Viet
            #   tu may chu thi UI-10 khong bo chuoi cung duoc.
            "ly_do": "" if du else "chua_cau_hinh",
            "bien_moi_truong": list(bien)}


def _nhan_khoa() -> dict:
    """`{kieu: [{ten, nhan, che, nhieu_dong}]}` — nhan NGUOI DOC cho tung o.

    🔴 Bang nhan nay o MAY CHU, khong o frontend (spec §6 luat 3, banh coc
       `test_967`): frontend sinh form tu day, nen mot `kieu` moi khai o day la
       mot o moi hien ra, khong phai mot dong sua trong TypeScript.

    ⛔ Dung trong ham chu khong o muc mo-dun: `_t()` o muc mo-dun dong bang
       ngon ngu luc import, va may chu phuc vu nhieu ngon ngu trong mot tien
       trinh.
    """
    nhan = {
        ("api_key", "gia_tri"): _t('Khoá API'),
        ("bearer", "gia_tri"): _t('Token'),
        ("basic", "ten_dang_nhap"): _t('Tên đăng nhập'),
        ("basic", "mat_khau"): _t('Mật khẩu'),
        ("oauth2", "client_id"): _t('Client ID'),
        ("oauth2", "client_secret"): _t('Client Secret'),
        ("google_service_account", "json_khoa"): _t('JSON khoá dịch vụ'),
        ("piece_custom", "gia_tri"): _t('Giá trị'),
    }
    return {kieu: [{"ten": k,
                    # ⛔ Khong roi ve mot chuoi rong: mot o khong nhan la mot o
                    #    khach khong biet phai dan gi vao.
                    "nhan": nhan.get((kieu, k), k),
                    "che": k in KHOA_CHE,
                    "nhieu_dong": k in KHOA_NHIEU_DONG}
                   for k in khoa]
            for kieu, khoa in KHOA_BI_MAT.items()}


@router.get("/api/v3/ket-noi/nha-cung-cap")
def v3_nha_cung_cap(_identity: str = Depends(require_login)):
    """Danh muc nha cung cap + tang kha dung. ⛔ Khong doc CSDL cua ai ca.

    Giao dien dung cua nay de biet: node dang chon thuoc nha cung cap nao, tang
    `cloud` co bat khong, va neu khong thi chu du an phai dat bien nao. Nho vay
    frontend **khong** giu mot bang ten nha cung cap (`test_967`).
    """
    so = _so_nha_cung_cap()
    ds = []
    for ma in sorted(so):
        muc = so[ma]
        ds.append({"ma": ma, "kieu": sorted(muc["kieu"]),
                   "node_type": sorted(muc["node_type"]),
                   **_tang_cua(ma, muc["kieu"])})
    return JSONResponse({"tang": [TANG_SELF, TANG_CLOUD],
                         "kieu": list(kho.KIEU),
                         "khoa_bi_mat": _nhan_khoa(),
                         "nha_cung_cap": ds})


def _sang_json(muc: dict) -> dict:
    """Mot hang `credential.liet_ke` -> JSON.

    ⛔ Liet ke tuong minh, y het `liet_ke`: mot cot moi them vao `Credential`
       khong duoc tu chay ra Internet. `datetime` -> ISO o day chu khong de
       FastAPI tu doan, de hai cua khong tra hai dang.
    """
    def gio(v):
        return v.isoformat() if v is not None else None

    return {"id": muc["id"], "kieu": muc["kieu"],
            "nha_cung_cap": muc["nha_cung_cap"], "ten": muc["ten"],
            "preview": muc["preview"], "pham_vi": list(muc["pham_vi"] or []),
            "meta": dict(muc["meta"] or {}),
            "het_han_luc": gio(muc["het_han_luc"]),
            "thu_hoi_luc": gio(muc["thu_hoi_luc"]),
            "dung_lan_cuoi": gio(muc["dung_lan_cuoi"]),
            "created_at": gio(muc["created_at"])}


@router.get("/api/v3/ket-noi")
def v3_danh_sach_ket_noi(request: Request, kieu: str = "",
                         nha_cung_cap: str = "",
                         _identity: str = Depends(require_login),
                         db: Session = Depends(get_db)):
    """Ket noi cua **chinh nguoi dang dang nhap**.

    `kieu` la danh sach ngan cach dau phay (`NodeDefinition.credential` cua
    node dang chon). ⭐ Loc o may chu chu khong o trinh duyet: o chon phai
    khong bao gio moi mot ket noi ma cong publish se tu choi.

    ⭐ Ket noi DA THU HOI van ra, kem `thu_hoi_luc` — an chung di thi khach thay
      ket noi "bien mat" va tao mot cai thu hai trung ten. Giao dien khoa chung,
      khong xoa chung khoi mat.
    """
    user = _user(request)
    loc_kieu = {k.strip() for k in str(kieu or "").split(",") if k.strip()}
    la = sorted(loc_kieu - set(kho.KIEU))
    if la:
        # ⛔ Mot `kieu` lạ la mot loi cua ben goi, khong phai mot bo loc rong:
        #    tra rong o day nghia la o chon im lang trong trong khi khach CO
        #    ket noi — va khong ai biet vi sao.
        raise HTTPException(status_code=422,
                            detail={"ma": "kieu_sai", "thong_diep": _t(
                                'Loại kết nối không được hỗ trợ.')})
    ds = [_sang_json(m) for m in kho.liet_ke(db, user.id)]
    if loc_kieu:
        ds = [m for m in ds if m["kieu"] in loc_kieu]
    if nha_cung_cap:
        ds = [m for m in ds if m["nha_cung_cap"] == nha_cung_cap]
    return JSONResponse({"items": ds})


def _bi_mat_tu_body(kieu: str, body: dict):
    """`bi_mat` da kiem hinh dang. ⛔ Khong bao gio log, khong bao gio tra lai.

    Moi khoa BAT BUOC cua `kieu` phai co mat va khong rong; ⛔ khoa la bi TU
    CHOI (khong nuot lang le): mot khoa go sai ten la mot bi mat khach TUONG da
    dat, thuc ra chua — va no chi lo ra luc chay, sau khi run giu tien.
    """
    tho = body.get("bi_mat")
    if not isinstance(tho, dict):
        raise HTTPException(status_code=422,
                            detail={"ma": "bi_mat_sai_hinh_dang",
                                    "thong_diep": _t('Thiếu thông tin bí mật.')})
    can = KHOA_BI_MAT[kieu]
    thieu = [k for k in can if not str(tho.get(k, "")).strip()]
    la = [k for k in tho if k not in can]
    if thieu or la:
        # ⛔ `chi_tiet` mang TEN KHOA, khong bao gio mang GIA TRI.
        raise HTTPException(
            status_code=422,
            detail={"ma": "bi_mat_sai_hinh_dang",
                    "thong_diep": _t('Thiếu thông tin bí mật.'),
                    "thieu": sorted(thieu), "khoa_la": sorted(la)})
    ra = {k: str(tho[k]) for k in can}
    # ⭐ MOT khoa ten `gia_tri` thi gui CHUOI, khong gui dict. Hai duong luu ra
    #    **cung mot** JSON (`credential._dong_goi` boc chuoi thanh
    #    `{"gia_tri": ...}`) va `_mo_goi` tra lai dung chuoi — nhung `_preview`
    #    thi khac: dict di qua `json.dumps` nen 4 ky tu cuoi la `42"}` thay vi
    #    4 ky tu cuoi cua CHINH khoa. Mot `preview` vo nghia lam ca cot do mat
    #    tac dung: khach khong nhan ra khoa nao la khoa nao.
    if list(ra) == ["gia_tri"]:
        return ra["gia_tri"]
    return ra


@router.post("/api/v3/ket-noi")
async def v3_tao_ket_noi(request: Request,
                         _identity: str = Depends(require_login),
                         db: Session = Depends(get_db)):
    """Tao mot ket noi cho chinh nguoi dang dang nhap.

    Than: `{kieu, ten, nha_cung_cap?, bi_mat:{...}, pham_vi?, meta?, tang?}`.

    ⭐ `tang` mac dinh `self`. `tang=cloud` bi TU CHOI khi nha cung cap chua co
       OAuth app cua LTT — va do la ca duong duy nhat hom nay, vi ⛔ khong mot
       bi mat nao cua chu du an duoc nhap bang ma. Xem docstring mo-dun.
    """
    body = await request.json()
    _verify_json_csrf(request, body)
    user = _user(request)
    kieu = str(body.get("kieu") or "").strip()
    if kieu not in KHOA_BI_MAT or kieu not in kho.KIEU:
        raise HTTPException(status_code=422,
                            detail={"ma": "kieu_sai", "thong_diep": _t(
                                'Loại kết nối không được hỗ trợ.')})
    ncc = str(body.get("nha_cung_cap") or "").strip().lower()
    if not _SLUG.match(ncc):
        raise HTTPException(status_code=422,
                            detail={"ma": "nha_cung_cap_sai",
                                    "thong_diep": _t(
                                        'Nhà cung cấp không hợp lệ.')})
    tang = str(body.get("tang") or TANG_SELF).strip() or TANG_SELF
    if tang not in (TANG_SELF, TANG_CLOUD):
        raise HTTPException(status_code=422,
                            detail={"ma": "tang_sai", "thong_diep": _t(
                                'Tầng xác thực không hợp lệ.')})
    if tang == TANG_CLOUD:
        so = _so_nha_cung_cap().get(ncc) or {"kieu": set()}
        trang = _tang_cua(ncc, set(so["kieu"]))
        if not trang["san_sang"]:
            # 🔴 KHONG bia mot luong chay duoc: thieu OAuth app thi khach phai
            #    biet ngay, chu khong publish xong roi hong luc chay.
            raise HTTPException(
                status_code=422,
                detail={"ma": "cloud_chua_cau_hinh",
                        "thong_diep": _t(
                            'LTT chưa cấu hình cho nhà cung cấp này. Hãy tự '
                            'mang ứng dụng của bạn.'),
                        "bien_moi_truong": trang["bien_moi_truong"]})
    bi_mat = _bi_mat_tu_body(kieu, body)
    meta = body.get("meta")
    if meta is not None and not isinstance(meta, dict):
        raise HTTPException(status_code=422,
                            detail={"ma": "meta_sai", "thong_diep": _t(
                                'Thông tin kèm theo không hợp lệ.')})
    try:
        c = kho.tao(db, owner_id=user.id, kieu=kieu, nha_cung_cap=ncc,
                    ten=str(body.get("ten") or "")[:_DAI_TEN],
                    bi_mat=bi_mat,
                    pham_vi=[str(x) for x in (body.get("pham_vi") or [])],
                    meta=dict(meta or {}))
    except kho.LoiCredential as loi:
        # ⭐ `meta_co_bi_mat` den tu `_kiem_meta` — mot khoa trong `META_CAM`.
        #    Ta KHONG loc tay truoc do: mot ban loc thu hai se troi khoi ban
        #    goc, va ban goc la ban chan that.
        raise HTTPException(status_code=422,
                            detail={"ma": loi.ma, "thong_diep": _t(
                                'Không tạo được kết nối.')}) from loi
    db.commit()
    ds = [m for m in kho.liet_ke(db, user.id) if m["id"] == c.id]
    return JSONResponse(_sang_json(ds[0]), status_code=201)


@router.delete("/api/v3/ket-noi/{ket_noi_id}")
async def v3_thu_hoi_ket_noi(request: Request, ket_noi_id: str,
                             _identity: str = Depends(require_login),
                             db: Session = Depends(get_db)):
    """Thu hoi = **xoa bi mat** (`credential.thu_hoi`), hang o lai lam bang
    chung mot run da dung gi.

    ⛔ Ket noi cua tai khoan KHAC tra **404**, khong 403: `credential._hang`
       loc `owner_id` ngay trong truy van va khong phan biet "khong co" voi
       "cua nguoi khac".
    """
    try:
        body = await request.json()
    except Exception:                               # noqa: BLE001
        # ⛔ Thân RỖNG ở đây làm bánh cóc `check_silent_except` TĂNG (53 → 54)
        #    và ⇒ `main` đỏ ở bước gate `nuot loi lang le` cho MỌI phiên.
        #    `pre-commit --all-files` ⛔ không phủ bước này — nó là bước GATE,
        #    không phải hook, nên một lượt pre-commit xanh không nói gì về nó.
        #
        # ⚠️ `debug` chứ không `warning`: thân rỗng ở đây là đường HỢP LỆ
        #    (khách gửi DELETE không kèm thân), nên một dòng mỗi lượt sẽ là rác.
        #    Nhưng nó phải có MỘT dòng, vì `except Exception` cũng bắt cả lỗi
        #    đọc thân bị cắt giữa đường — và ca đó thì đáng thấy.
        # ⚠️ Thong diep log viet KHONG DAU: banh coc `check_i18n` coi mot chuoi
        #    co dau la chuoi hien cho khach va doi boc `_()`. Log la cho NGUOI
        #    VAN HANH doc, ⛔ khong dich — nen ca kho viet log khong dau.
        _log.debug("ket_noi_v3: than request khong phai JSON, coi nhu rong",
                   exc_info=True)
        body = {}
    _verify_json_csrf(request, body if isinstance(body, dict) else {})
    user = _user(request)
    try:
        kho.thu_hoi(db, ket_noi_id, owner_id=user.id)
    except kho.LoiCredential as loi:
        db.rollback()
        raise HTTPException(status_code=404,
                            detail={"ma": loi.ma, "thong_diep": _t(
                                'Không tìm thấy kết nối.')}) from loi
    db.commit()
    return JSONResponse({"ok": True})

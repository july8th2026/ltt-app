"""ASV V6 pha 06 — kien truc frontend cua man Studio.

Pha 06 doi mot thu duy nhat: `server/static/asv.js` (1.154 dong, mot IIFE) tro
thanh tam module duoi `server/static/asv/`.

🔑 **Mot cuoc tach chi co gia tri neu no khong the tu lien lai.** Xoa mot tep
   phinh la viec cua mot buoi chieu; giu cho no dung moc lai la viec cua mot
   banh coc. Nen tep nay chot ba thu:

     · TAP HOP module — khong phai so luong (`banh-coc-cong-chat-luong`)
     · TRAN dong cho TUNG module
     · MOT nguon danh sach duy nhat cho ba noi tung co the troi khoi nhau

⛔ Va no chot ca chieu **duong**: chi kiem *"asv.js da bien mat"* thi mot cay
   xoa sach ca tam module cung xanh. *"Da gom ve mot chu"* va *"da vut mat
   luat"* trong giong het nhau khi ta chi dem su vang mat.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

from tests import asv_js

GOC = Path(__file__).resolve().parents[1]
TINH = GOC / "server" / "templating.py"
THU_MUC = GOC / "server" / "static" / "asv"
MAU = GOC / "apps" / "auto_scan_video" / "templates" / "asv_trang_chinh.html"

#: Tran dong cho MOT module. Do nhat hien tai la `asv/vung.js` = 237 dong, nen
#: 320 cho du dat de khong bao dong gia va van con xa 1.154.
#:
#: ⚠️ Con so nay khong phai mot y kien tham my. No la thu duy nhat ngan mot
#:    module lon dan tro lai thanh chinh cai tep pha 06 vua go — va no phai bi
#:    NHIN LAI, khong duoc NOI RA, moi khi co ai cham tran. Noi tran la bo mat
#:    cau hoi ma banh coc dang hoi.
TRAN_DONG = 320


def _ds() -> tuple[str, ...]:
    return asv_js.ds_module()


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Tap hop module — ba noi phai noi cung mot dieu
# ══════════════════════════════════════════════════════════════════════════════

def test_tep_phinh_cu_da_bien_mat():
    """Nua AM. Mot minh no khong chung minh gi — xem `§1` cua tep nay."""
    assert not (GOC / "server" / "static" / "asv.js").exists(), (
        "server/static/asv.js van con — pha 06 chua thuc su tach")


def test_MOI_module_khai_bao_deu_ton_tai_va_chay_duoc():
    """Nua DUONG thu nhat: danh sach khong tro vao khoang khong."""
    ds = _ds()
    assert len(ds) >= 5, f"chi co {len(ds)} module — day chua phai mot cuoc tach"
    for m in ds:
        p = asv_js.duong(m)
        assert p.is_file(), f"{m} duoc khai nhung khong co tren dia"
        assert p.read_bytes(), f"{m} rong"


def test_KHONG_co_module_mo_coi_trong_thu_muc():
    """Nua DUONG thu hai, va la nua bat duoc kieu hong IM LANG nhat.

    Mot tep `.js` nam trong `server/static/asv/` ma khong co trong
    `ASV_STUDIO_JS` thi **trang khong bao gio nap no**. Khong loi nao o dau ca:
    tinh nang do don gian la khong ton tai, va ma nguon cua no van nam do trong
    nhu dang chay.

    ⭐ Cung hinh dang voi `nang-luc-co-nhung-khong-ai-di-tren-duong`: hoi "co
       duong khong" roi phai hoi tiep "co xe tren duong khong".
    """
    tren_dia = {"asv/" + p.name for p in sorted(THU_MUC.glob("*.js"))}
    khai = set(_ds())
    assert tren_dia == khai, (
        f"lech giua thu muc va `ASV_STUDIO_JS`:\n"
        f"  co tep, khong ai nap : {sorted(tren_dia - khai)}\n"
        f"  khai, khong co tep   : {sorted(khai - tren_dia)}")


def test_moi_module_deu_duoc_CACHE_BUST():
    """Quy tac 6 cua `CLAUDE.md`. Thieu mot module trong bo bam thi `?v=` cua no
    khong doi khi noi dung doi — khach nhan ban CU tu Cloudflare toi het TTL, va
    trang van render dep."""
    cay = ast.parse(TINH.read_text(encoding="utf-8"))
    ten_bo = {}
    for n in cay.body:
        if isinstance(n, ast.Assign):
            for d in n.targets:
                if isinstance(d, ast.Name) and d.id in (
                        "ASV_STUDIO_JS", "TAI_SAN_CO_VERSION"):
                    ten_bo[d.id] = n.value
    assert "TAI_SAN_CO_VERSION" in ten_bo, "khong thay TAI_SAN_CO_VERSION"

    # ⭐ Doc bang AST, va CHAP NHAN dang `(...) + ASV_STUDIO_JS`: chinh phep noi
    #    ay la thu lam viec "quen mot module" tro thanh bat kha.
    v = ten_bo["TAI_SAN_CO_VERSION"]
    assert isinstance(v, ast.BinOp) and isinstance(v.op, ast.Add), (
        "TAI_SAN_CO_VERSION khong con noi ASV_STUDIO_JS vao — mot danh sach "
        "chep tay se troi khi them module")
    assert isinstance(v.right, ast.Name) and v.right.id == "ASV_STUDIO_JS", (
        "ve phai cua phep noi khong phai ASV_STUDIO_JS")


def test_template_PHAT_the_script_tu_danh_sach_chu_khong_go_tay():
    """Cho thu ba. Go tay tung dong `<script>` la tao mot danh sach thu hai."""
    van = MAU.read_bytes().decode("utf-8")
    assert "asv_studio_js" in van, (
        "template khong lap qua `asv_studio_js` — dang go tay duong dan")
    go_tay = re.findall(r'src="/static/asv/[^"]+\.js', van)
    assert not go_tay, f"template van go tay duong dan module: {go_tay}"


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Chong moc lai
# ══════════════════════════════════════════════════════════════════════════════

def test_KHONG_module_nao_vuot_tran_dong():
    """Banh coc thuc su cua pha nay.

    ⛔ Thieu no thi "tach lam tam tep" chi la mot trang thai nhat thoi: mot pha
       sau them 200 dong vao `asv/vung.js`, roi mot pha nua them 300, va sau
       nam pha ta co lai dung mot tep phinh — chi la no khong con ten `asv.js`.
    """
    qua = {}
    for m in _ds():
        n = len(asv_js.duong(m).read_bytes().decode("utf-8").splitlines())
        if n > TRAN_DONG:
            qua[m] = n
    assert not qua, (
        f"module vuot tran {TRAN_DONG} dong: {qua}. Tach tiep, dung noi tran — "
        "noi no la bo mat cau hoi ma banh coc nay dang hoi")


def test_CHI_MOT_module_tao_khong_gian_ten():
    """`window.ASV` phai co dung mot chu. Hai cho gan la mot cho ghi de cho kia,
    va thu bi mat se la nhung nguoi dang ky da dang ky truoc do."""
    tao = [m for m in _ds() if "window.ASV =" in asv_js.doc(m)]
    assert tao == ["asv/nen.js"], (
        f"`window.ASV` duoc gan o {tao} — phai dung mot cho, va la `asv/nen.js`")


def test_nen_js_nap_TRUOC_moi_module_khac():
    """Rang buoc thu tu DUY NHAT con lai. Bay tep kia doc lap voi nhau vi moi
    loi goi cheo module xay ra luc SU KIEN chu khong luc NAP."""
    assert _ds()[0] == "asv/nen.js", (
        f"module dau tien la {_ds()[0]}, khong phai `asv/nen.js` — cac module "
        "khac se doc `window.ASV` truoc khi no ton tai")


def test_moi_module_phu_deu_CHAN_khi_khong_phai_man_Studio():
    """`asv.js` cu mo dau bang `if (!form) return;` — mot trang khac nap nham thi
    no im lang chu khong nem. Tach ra tam tep thi **tung tep** phai giu loi hua
    do, khong phai mot tep giu ho bay tep kia."""
    thieu = [m for m in _ds() if m != "asv/nen.js"
             and "!window.ASV || !ASV.co" not in asv_js.doc(m)]
    assert not thieu, (
        f"{thieu} khong chan khi trang khong phai man Studio")


def test_be_mat_cong_khai_ngoai_nen_la_TOI_THIEU():
    """Mot module chi duoc treo len `ASV` thu ma module KHAC that su goi.

    🔑 Day la cho mot cuoc tach de bien thanh mot cuoc doi ten: neu moi module
       treo het ham cua no len `ASV`, ta co lai mot khong gian ten phinh — dung
       cai giant form cu, chi khac la no mang dau cham.

    ⭐ Hom nay dung MOT: `asv/xem_truoc.js` phai biet tep se di duong nao truoc
       khi do kich thuoc, va cau tra loi song o `asv/tai_len.js`.
    """
    treo = set()
    for m in _ds():
        if m == "asv/nen.js":
            continue
        treo |= set(re.findall(r"ASV\.([A-Za-z_][A-Za-z0-9_]*)\s*=", asv_js.doc(m)))
    assert treo == {"benVungKieuDuocKhong"}, (
        f"be mat cheo module da rong ra: {sorted(treo)}. Moi ten them vao day "
        "la mot rang buoc moi giua hai tep vua duoc tach roi")


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Thu tung song trong tep phinh, va phai con song
# ══════════════════════════════════════════════════════════════════════════════

def test_thu_tu_giua_thoi_luong_va_ve_lai_KHONG_con_la_mot_chu_thich():
    """🔴 Truoc pha 06 thu tu nay duoc giu bang mot dong chu thich:

        // ⚠️ `batCat` TRUOC `veLai`: no dat `thoiLuongVideo` ...
        batCat(giay);
        veLai();

    Mot chu thich giu duoc thu tu chung nao hai dong con nam canh nhau. Tach ra
    tam tep thi no khong giu duoc gi — nen luat phai doi cho: `phatCoVideo` dat
    `ASV.thoiLuongVideo` **truoc khi goi bat ky nguoi dang ky nao**.

    ⭐ Sau doi nay rang buoc BIEN MAT thay vi duoc chep sang mot chu thich moi.
       Do la ranh gioi CO HOC thang giao uoc — `luat-viet-ra-khong-mien-nhiem-
       cho-nguoi-viet`.
    """
    nen = ast.parse("0")   # cho ruff khong keu bien khong dung
    assert nen is not None

    van = asv_js.doc("asv/nen.js")
    i = van.index("phatCoVideo: function")
    j = van.index("}", van.index("goiHet(dsCoVideo", i))
    than = van[i:j]
    assert "api.thoiLuongVideo = giay;" in than, (
        "`phatCoVideo` khong dat `thoiLuongVideo`")
    assert (than.index("api.thoiLuongVideo = giay;")
            < than.index("goiHet(dsCoVideo")), (
        "`phatCoVideo` goi nguoi dang ky TRUOC khi dat `thoiLuongVideo` — thu "
        "tu lai tro thanh mot rang buoc an, dung cai pha 06 vua go")


def test_bon_ban_sao_cua_phep_hoi_preset_da_gom_lam_MOT():
    """Bon module tung chep NGUYEN ba dong doc `data-preset-can`. Mot ban sao la
    mot ban se lech, va lech im lang."""
    chep = [m for m in _ds() if m != "asv/nen.js"
            and "data-preset-can" in asv_js.doc(m)]
    assert not chep, (
        f"{chep} van tu doc `data-preset-can` — phai hoi qua `ASV.hopPreset`")
    dung = [m for m in _ds() if "ASV.hopPreset(" in asv_js.doc(m)]
    assert len(dung) >= 4, (
        f"chi {len(dung)} module dung `ASV.hopPreset` — bon khoi dieu khien "
        "(vung, cat, lop phu, logo) deu phai di qua no")
# ══════════════════════════════════════════════════════════════════════════════
#  §4  `[hidden]` phai thang — mot loi CHI trinh duyet thay
# ══════════════════════════════════════════════════════════════════════════════

CSS = GOC / "server" / "static" / "ltt.css"


def test_hidden_THANG_moi_luat_display_tren_man_Studio():
    """🔴 Do o pha 06 tren trinh duyet that: BA phan tu mang `hidden` van render.

        #asv-tai      <- `.asv-tai{display:flex}`      khoi tien do tai len
        #asv-tai-lai  <- `.btn{display:inline-flex}`   nut "Thu tai len lai"
        #asv-lop      <- svg lop ve vung che

    Thu khach nhin thay: mot nut **"Thu tai len lai"** ngay khi mo trang, giai
    thich mot su co chua he xay ra.

    ⛔ Khong mot phep kiem nao hien co thay duoc. Markup DUNG (`hidden` co that),
       JS DUNG (khong ai bat no hien), chi CSS lat nguoc y dinh — va `hidden` la
       thuoc tinh o bang kieu cua TRINH DUYET, nen bat ky luat `display` nao cua
       ta cung de bep no.

    ⭐ Man Voice da dinh dung bay nay truoc, va chu thich cua ho trong `ltt.css`
       da rut ra dung ket luan: *"mot DANH SACH LOP chi bao ve nhung gi da tung
       hong"* — ho thu liet ke bon lop, roi no tai dien trong mot gio o `.btn`.
       Nen bai nay chot mot luat CHUNG cho ca man, khong chot mot danh sach.

    ⚠️ Va no chot ca `!important`: khong co do dac hieu nao thang duoc mot luat
       tac gia khac tru khi ta ra khoi cuoc thi do dac hieu.
    """
    css = CSS.read_bytes().decode("utf-8")
    # Hai phep kiem RIENG, khong mot chuoi bac cau qua dau xuong dong:
    # ltt.css tron CRLF va LF (3.118 / 545), nen mot cai neo di qua ket
    # dong la mot cai neo se dut khi co ai sua tep bang cong cu khac.
    assert ".asv-trang [hidden]" in css, (
        "mat bo chon HAU DUE - luat chi con phu chinh phan tu goc")
    assert ".asv-trang[hidden]{display:none!important}" in css, (
        "khong con luat `[hidden]` chung cho man Studio — mot luat `display` "
        "bat ky se lat nguoc `hidden`, va khong phep kiem nao khac thay duoc")


def test_luat_do_KHONG_bi_thu_hep_thanh_mot_danh_sach_lop():
    """Doi chung cho bai tren, va no chot dung cai da hong mot lan.

    Mot ban "sua" thu hep luat ve `.asv-tai[hidden], #asv-tai-lai[hidden]` van
    lam bai tren xanh neu ta chi tim chuoi con. Nen bai nay hoi phia DUONG: bo
    chon phai la dang **hau due** (`.asv-trang [hidden]`), tuc phu moi phan tu
    trong man — ke ca nhung phan tu chua ton tai.
    """
    css = CSS.read_bytes().decode("utf-8")
    i = css.index(".asv-trang [hidden],")
    khoi = css[i:css.index("}", i) + 1]
    assert "[hidden]" in khoi and "!important" in khoi
    # Khong duoc co lop cu the nao ben trong bo chon — mot cai ten lop o day la
    # dau hieu luat da tro lai thanh mot danh sach.
    bo_chon = khoi.split("{")[0]
    lop = [x for x in bo_chon.replace(",", " ").split()
           if x.startswith(".") and x not in (".asv-trang", ".asv-trang[hidden]")
           and not x.startswith(".asv-trang")]
    assert not lop, f"bo chon da co lop cu the {lop} — luat dang tro thanh mot danh sach"

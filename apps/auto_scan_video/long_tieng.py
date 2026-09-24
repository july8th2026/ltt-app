"""Ban long tieng — loi thoai tieng Viet cho **dung nhung doan duoc giu lai**.

## Vi sao khong phai "ban dich"

V2 dich ca ban chep loi, tung cau mot, khong biet gi ngoai cau do. San pham V4
la **long tieng**, va hai viec do khac nhau o cho quan trong nhat: mot ban dich
dung la mot ban dich dung; mot cau long tieng dung con phai **vua mieng nguoi
noi, vua canh phim, va vua giong da chon**.

Nen moi doan o day di kem mot ngu canh ma mot cau dich khong can:

    van ban goc · **thoi luong goc** · y nghia/cam xuc cua canh ·
    hai doan giu lai ke ben · dac diem giong dich

⭐ `thoi_luong` co mat tu day chu khong doi den pha 15: pha 15 **rut ngan cho
   vua**, va rut ngan mot cau viet ma khong biet no phai dai bao nhieu la sua
   mot thu le ra khong nen sai ngay tu dau. Cho model biet truoc thi phan lon
   cac cau khong can sua lan hai.

## ⛔ Ban chep loi nguon la BAT BIEN

Tep nay chi **doc** `transcript.json`. Ban chep loi la bang chung ve thu may
nghe duoc; ban long tieng la mot dien giai cua no. Ghi de dien giai len bang
chung la mat kha nang tra loi cau hoi *"no doc ra tu cai gi"* khi khach khieu
nai — va do la cau hoi ton tien nhat.

## Vi sao ma doan phai la KHOA, khong duoc la VI TRI

Mot lo gui 12 doan; model tra ve 11. Neu ta ghep ket qua theo **vi tri** thi tu
doan thu k tro di **moi cau bi gan cho doan ben canh** — va no khong hong o dau
ca: tai lieu van du truong, van hop le, chi la tu giua phim tro di loi thoai
lech mot cau. Ghep theo **ma** thi truong hop do thanh mot loi "thieu doan X",
noi ra duoc va thu lai duoc.

## Bang tu vung DONG, khong phai van ban tu do

`CAM_XUC` va `KIEU_NOI` la tuple dong. Mot truong cam xuc tu do se tra ve
"hoi buon", "buon man mac", "sad" va "u sau" cho cung mot thu, va ha nguon
(pha 15 chon nhip, pha 17 chon giong) khong dung duoc gi trong so do.
"""
from __future__ import annotations

import hashlib
import json

from platform_core.i18n import _ as _t

#: Doi bat cu thu gi o duoi day thi tang so nay — no di vao van tay.
#:
#: 2 (23/09/2026): loi nhac mang `do_dai_toi_da` — mot TRAN DEM DUOC cho moi
#: doan, tinh tu `ngon_ngu.ngan_sach_do_dai` (nhip DO DUOC 3,35 am tiet/giay
#: thay cho con so 4,5 chua do). Doi ban long tieng da sinh, nen phai doi van tay.
PHIEN_BAN_LONG_TIENG = 2

SCHEMA_LONG_TIENG = "asv.long_tieng.v1"

#: Bang tu vung DONG cho sac thai. Ha nguon doi sang tham so tong hop tieng noi.
CAM_XUC = ("trung_tinh", "vui", "buon", "gian", "cang_thang", "trang_trong",
           "than_mat", "hoi_hop")

#: Bang tu vung DONG cho loi noi.
KIEU_NOI = ("doi_thoai", "ke_chuyen", "thuyet_minh", "reo_ho", "thi_tham")

#: So doan moi lan goi model.
#:
#: ⭐ Nho hon `dich_thuat.DOAN_MOI_LO = 20` co y: moi doan o day mang theo ngu
#:    canh canh + hai doan ke, nen mot lo 20 doan lam loi nhac dai gap may lan
#:    va day phan cuoi ra khoi phan model chu y ky nhat. 12 la cho de moi lo van
#:    du ngan cho model giu duoc mach, va mot lo hong chi mat 12 doan.
#:
#: ⚠️ CHUA DO tren du lieu that — chon de an toan, khong de toi uu. Pha 21 do lai.
DOAN_MOI_LO = 12

#: So doan giu lai ke ben duoc dua vao lam ngu canh (moi phia).
#:
#: 🔑 Ngu canh phai lay tu cac doan **DUOC GIU**, khong phai cac doan ke nhau
#:    trong ban goc. Sau khi cat, cau dung truoc mot cau trong ban ra co the la
#:    mot cau cach do ba phut trong ban goc — va do moi la cau khan gia vua nghe.
NGU_CANH_KE = 2

#: Do dai toi da cua mot cau goc dua vao loi nhac (ky tu). Cat de mot doan hong
#: khong lam no ca lo.
GOC_TOI_DA = 600

#: 🔑 **Quy tac TEN RIENG — chi cho dich VI, va cho do la MOT PHAN CUA LUAT.**
#:
#: ⚠️ `ngon_ngu_dich` ⛔ khong phai luon la `vi`: `DICH_HOP_LE` cho ca `en`
#:    (`ngon_ngu.kiem_cap`). *"Phien am HAN-VIET"* la luat cua tieng Viet; ap no
#:    khi dich sang tieng Anh la dung ho **F-05** (loi nhac ghi cung "tieng Viet"
#:    cho moi nguon). ⇒ Chen co dieu kien, ⛔ khong chen vo dieu kien.
#:
#: ⭐ **Vi du VIET DUNG Y NHU DAU RA MONG MUON — co dau day du.** Ban v2 cua
#:    `dich_thuat` viet vi du KHONG DAU (`Truong Vi`) va model **chep HINH DANG
#:    cua vi du**: mot ten von dung (`李宗盛`) tut thanh khong dau. Lan v3 viet
#:    co dau thi het. (`B2_DICH.md` §4c)
#:
#: ⚠️ **Vi sao no la mot `{"role", "content"}` chu khong phai mot chuoi tran.**
#:    `check_i18n._la_tin_nhan_model` nhan mot loi nhac **theo HINH DANG**: chuoi
#:    nam o khoa `"content"` cua mot dict co ca khoa `"role"` thi la tin nhan gui
#:    model, ⛔ khong phai chu tren man hinh (`check_i18n.py:149`). No ⛔ **khong
#:    leo qua mot phep gan**, nen viet `X = "…Bắc Kinh…"` lam banh coc i18n do
#:    (da do that: `long_tieng.py 0 -> 1` — va banh coc nay tinh **theo tung tep**,
#:    nen mot o cung du do).
#: ⛔ Boc `_()` sai theo huong NGUY HIEM: loi nhac se doi theo ngon ngu giao dien
#:    cua khach — mot thiet lap hien thi lang le doi HANH VI dich.
#: ⇒ Khai dung thu no VON LA — mot **manh cua tin nhan he thong** — thi ca bo dem
#:    lan nguoi doc deu thay dung. ⛔ Day khong phai viet de lach bo dem.
QUY_TAC_TEN_RIENG_VI = {"role": "system", "content": (
    "- TEN RIENG — hoi HAI cau, THEO THU TU:\n"
    "  1. Ten nay DA CO loi viet quen trong tieng Viet chua? Neu CO thi dung "
    "DUNG loi quen do, bat ke no la nguoi, noi chon hay to chuc. "
    "Vi du: 首尔 -> Seoul, 东京 -> Tokyo, 北京 -> Bắc Kinh, 上海 -> Thượng Hải, "
    "重庆 -> Trùng Khánh, 李宗盛 -> Lý Tông Thịnh, 李小龙 -> Lý Tiểu Long, "
    "腾讯 -> Tencent, 华为 -> Huawei.\n"
    "  2. Neu KHONG co loi quen, hoac ban khong chac, thi moi xet LOAI. "
    "Nguoi hoac dia danh: phien AM HAN-VIET, CO DAU tieng Viet day du. "
    "Vi du: 张伟 -> Trương Vĩ, 小美 -> Tiểu Mỹ, 王芳 -> Vương Phương. "
    "KHONG dich nghia den, KHONG doi sang tieng Anh, KHONG dung binh am, "
    "KHONG bo dau. To chuc, thuong hieu, ten san pham: GIU NGUYEN DANG goc, "
    "KHONG phien am Han-Viet va KHONG dich nghia den.\n"
    "  Mot ten xuat hien nhieu lan phai duoc xu ly GIONG NHAU o moi lan.\n")}

#: ⭐ **DUONG B — model tu khai cho no khong chac.** ⛔ CHI THU, ⛔ khong hien
#: cho khach, ⛔ khong lai vong sua, ⛔ khong chan gi. Dung no vao viec gi la
#: quyet dinh cua chu du an.
#:
#: Do that tren ban nen (`B2_DICH.md` §4i, `tools/bench_b2_duong_b_tu_khai.py`):
#:   · do nhay  **4/7** ca thuat ngu da biet hong (`师傅`, `烧酒`, `掐雷`, `纯白给`)
#:   · do on    **19 muc / 3 011 ky tu goc = 0,63 %** — ngan du de soi tay
#:   · gia      **+1 truong**, ~0 luot goi them (di kem luot dich)
#:
#: ⭐ Tac dung phu dang gia hon chinh no: no khai ca **loi CHEP LOI**
#:    (`避不住`, `提炼枪`, `此一听`) — tuc thu §4e can de tach loi ASR khoi loi
#:    dich, mot viec ta ⛔ chua co cach nao khac lam.
#:
#: 🔴 **RANH GIOI, giu nguyen van:** *model biet no khong biet TU; no khong biet
#:    no hieu sai CAU.* **0 %** o lop ngu phap — `补人`, `热胀冷缩`, `这才是`
#:    (ra *"Moi day moi la"* thay vi *"Day moi la"*) deu KHONG duoc khai.
#:    ⇒ ⛔ Dung doc cot nay nhu mot bo do chat luong.
#:
#: ⛔ **Cau hoi co y TRUNG TINH va KHONG mot vi du nao.** ⛔ Khong noi "chuyen
#:    nganh", ⛔ khong noi "tieng long", ⛔ khong dua mot ca nao trong 7 ca da
#:    hong vao: *mot vi du trong loi nhac la mot menh lenh ngam* (§4c) — mach thi
#:    ta do chinh loi mach cua minh.
QUY_TAC_TU_KHAI = {"role": "system", "content": (
    "- Trong moi doan, them khoa \"khong_chac\": danh sach nhung tu hoac cum "
    "TRONG CAU GOC ma ban khong chac chan ve cach chuyen. De danh sach RONG "
    "neu ban chac chan het.\n")}


class LongTiengError(ValueError):
    """Ban long tieng khong dung hop dong."""


class ThieuDoan(LongTiengError):
    """Model khong tra ve du cac doan da gui."""


# ══════════════════════════════════════════════════════════════════════════════
#  Chia lo — giu NGUYEN dinh danh
# ══════════════════════════════════════════════════════════════════════════════

def chia_lo(doan: list[dict], *, moi_lo: int | None = None) -> list[list[dict]]:
    """Chia theo thu tu nguon. Khong sap xep lai, khong gom theo canh.

    ⛔ Gom theo canh nghe co ly (cung canh thi cung ngu canh) nhung no pha vo
       thu tu thoi gian trong loi nhac, va mach hoi thoai la thu model can nhat.

    🔴 **`moi_lo=None` chu khong phai `moi_lo=DOAN_MOI_LO`.** Mot gia tri mac
       dinh duoc gan **luc dinh nghia ham**, mot lan, khi module nap. Nen ban dau
       viet `moi_lo: int = DOAN_MOI_LO` thi doi `DOAN_MOI_LO` sau do — bang cau
       hinh hay bang `monkeypatch` — **khong doi duoc gi**, va cho hong im lang:
       ham van chay, van tra ve ket qua hop le, chi la voi kich thuoc lo cu.

    ⭐ Tim ra khi mot phep kiem dat `DOAN_MOI_LO = 1` de tao nhieu lo va van chi
       thay MOT lo. Mot num van trong nhu da chinh ma khong chinh gi la thu tra
       gia dat nhat: no lam moi phep do sau do noi ve mot cau hinh khong ton tai.
    """
    doan = list(doan or [])
    n = max(1, int(moi_lo if moi_lo is not None else DOAN_MOI_LO))
    return [doan[i:i + n] for i in range(0, len(doan), n)]


def ngu_canh_ke(tat_ca: list[dict], vi_tri: int, *, ke: int | None = None) -> dict:
    """Cac doan GIU LAI ngay truoc/sau, theo thu tu ban ra — khong phai ban goc.

    `ke=None` chu khong phai `ke=NGU_CANH_KE`: cung ly do nhu `chia_lo`.
    """
    ke = NGU_CANH_KE if ke is None else int(ke)
    truoc = [str(d.get("chu") or "") for d in tat_ca[max(0, vi_tri - ke):vi_tri]]
    sau = [str(d.get("chu") or "")
           for d in tat_ca[vi_tri + 1:vi_tri + 1 + ke]]
    return {"truoc": [t for t in truoc if t], "sau": [t for t in sau if t]}


# ══════════════════════════════════════════════════════════════════════════════
#  Loi nhac
# ══════════════════════════════════════════════════════════════════════════════

def loi_nhac(lo: list[dict], *, tat_ca: list[dict], ngon_ngu_goc: str,
             dac_diem_giong: dict, y_canh: dict | None = None,
             ngon_ngu_dich: str = "vi") -> list[dict]:
    """Dung loi nhac cho MOT lo. Tra ve `messages` cho `ai.goi_tinh_tien`.

    ⛔ Yeu cau tra ve JSON co khoa la **ma doan**, khong phai mot mang. Xem ghi
       chu dau tep ve vi sao vi tri khong dung lam dinh danh duoc.
    """
    from . import ngon_ngu

    y_canh = y_canh or {}
    muc = []
    chi_so = {d.get("ma"): i for i, d in enumerate(tat_ca)}
    for d in lo:
        ma = str(d.get("ma") or "")
        goc = str(d.get("chu") or "")[:GOC_TOI_DA]
        try:
            dai = max(0.0, float(d.get("ket", 0)) - float(d.get("bat", 0)))
        except (TypeError, ValueError):
            dai = 0.0
        m = {"ma": ma, "goc": goc, "thoi_luong_giay": round(dai, 2),
             # 🔑 **TRAN DEM DUOC, khong phai mot nhip de model tu nhan.**
             #    Xem `ngon_ngu.ngan_sach_do_dai`. Truoc 23/09 cho nay chi co
             #    `thoi_luong_giay`, va pha 15 phai don hau qua bang 11 luot
             #    viet lai / 751 giay tren mot phim 107 giay.
             "do_dai_toi_da": ngon_ngu.ngan_sach_do_dai(dai, ngon_ngu_dich),
             "ke_ben": ngu_canh_ke(tat_ca, chi_so.get(ma, 0))}
        y = y_canh.get(ma)
        if y:
            m["y_canh"] = y
        muc.append(m)

    c = ngon_ngu.cum(ngon_ngu_dich)
    # ⛔ Quy tac ten rieng CHI cho dich `vi` — xem `QUY_TAC_TEN_RIENG_VI`.
    ten_rieng = (QUY_TAC_TEN_RIENG_VI["content"]
                 if ngon_ngu.chuan_dich(ngon_ngu_dich) == ngon_ngu.VI else "")
    he_thong = (
        f"Ban la bien tap vien long tieng {c['tieng']}. Ban KHONG dich tung chu: "
        f"ban viet lai cau thoai sao cho {c['nguoi']} nghe thay tu nhien, dung y, "
        "va **doc vua khoang thoi gian da cho**.\n"
        "Quy tac:\n"
        "- Giu nguyen y nghia va thai do cua cau goc.\n"
        f"- Do dai cau phai doc vua `thoi_luong_giay` ({c['nhip']}).\n"
        f"- **KHONG QUA `do_dai_toi_da` {c['don_vi']}** — dem lai truoc khi tra ve.\n"
        f"  Thieu mot chut thi duoc; qua mot chut thi cau bi tran sang canh sau.\n"
        "- Giu mach voi cac cau o `ke_ben` — do la nhung cau khan gia vua nghe "
        "va sap nghe, sau khi da cat.\n"
        "- Xung ho va giong dieu hop voi `giong` da chon.\n"
        "- Khong them thong tin khong co trong cau goc.\n"
        + ten_rieng + QUY_TAC_TU_KHAI["content"] +
        f"- `cam_xuc` phai la MOT trong: {', '.join(CAM_XUC)}.\n"
        f"- `kieu_noi` phai la MOT trong: {', '.join(KIEU_NOI)}.\n"
        "Tra ve DUY NHAT mot doi tuong JSON:\n"
        '{"doan": {"<ma doan>": {"chu": "...", "cam_xuc": "...", '
        '"kieu_noi": "...", "nhan_manh": ["..."], "khong_chac": ["..."]}}}\n'
        "Khoa phai la MA DOAN da cho, khong duoc doi, khong duoc bo sot.")

    nguoi_dung = json.dumps({
        "ngon_ngu_goc": str(ngon_ngu_goc or ""),
        "giong": dict(dac_diem_giong or {}),
        "doan": muc,
    }, ensure_ascii=False, sort_keys=True)

    return [{"role": "system", "content": he_thong},
            {"role": "user", "content": nguoi_dung}]


# ══════════════════════════════════════════════════════════════════════════════
#  Doc phan hoi
# ══════════════════════════════════════════════════════════════════════════════

#: So muc `khong_chac` giu lai moi doan. Do that: **19 muc / 3 011 ky tu goc =
#: 0,63 %** tren ba phim (`B2_DICH.md` §4i) — nen tran nay ⛔ khong phai mot cai
#: kep, no la mot **chan tren cho truong hop benh ly** (model xa danh sach).
KHONG_CHAC_TOI_DA = 8

#: Do dai toi da cua MOT muc `khong_chac` (ky tu). Muc that la mot tu/cum trong
#: cau goc (`掐雷`, `纯白给`), nen mot chuoi dai hon the la model dang viet van —
#: cat de mot phan hoi lac de ⛔ khong phinh so cai.
KHONG_CHAC_DAI_TOI_DA = 40


def _chuoi_ngan(x) -> list[str]:
    """Danh sach chuoi da cat tran. ⛔ Khong nem — moi dang sai deu ra `[]`.

    🔑 **Vi sao khoan dung o day nhung nghiem khac o `chu`.** `chu` la **thu san
       pham**: sai luoc do o do phai thanh loi. `khong_chac` la mot **cot chan
       doan** ⛔ khong ai o ha nguon doc — de no lam hong mot lo loi thoai da tra
       tien la doi mot thu dat lay mot thu khong dat.
    """
    if not isinstance(x, list):
        return []
    ra = []
    for m in x[:KHONG_CHAC_TOI_DA]:
        # 🔴 `str(m or "")` chu KHONG duoc — no gop `None` voi moi gia tri FALSY
        #    khac: `0`, `False`, `0.0` deu thanh chuoi rong roi bi bo **im lang**.
        #    Mot phep kiem da bat dung ca do (`list(range(50))` ra 7 muc chu
        #    khong phai 8). Cung ho loi voi "hai trang thai gop thanh mot gia tri".
        t = ("" if m is None else str(m)).strip()[:KHONG_CHAC_DAI_TOI_DA]
        if t:
            ra.append(t)
    return ra


def doc_chuyen(goi: dict, ma_da_gui: set[str]) -> dict:
    """`{ma: {chu, cam_xuc, kieu_noi, nhan_manh}}` — chi cho nhung ma DA GUI.

    ⛔ Ma la nem `ThieuDoan` khi thieu, khong phai lang le tra ve it hon: nguoi
       goi khong the phan biet "model bo sot" voi "lo nay it doan" neu ta chi tra
       ve mot dict ngan hon.

    ⛔ Va **bo di** nhung ma khong duoc gui: mot model bia them ma la mot doan
       loi thoai gan cho mot doan hinh khong ton tai.
    """
    tho = (goi or {}).get("doan")
    if not isinstance(tho, dict):
        raise LongTiengError(_t('Model không trả về bảng đoạn.'))

    ra: dict[str, dict] = {}
    for ma, v in tho.items():
        ma = str(ma)
        if ma not in ma_da_gui or not isinstance(v, dict):
            continue
        chu = str(v.get("chu") or "").strip()
        if not chu:
            continue
        cx = str(v.get("cam_xuc") or "").strip()
        kn = str(v.get("kieu_noi") or "").strip()
        nm = v.get("nhan_manh")
        ra[ma] = {
            "chu": chu,
            # ⭐ Ngoai bang tu vung thi ve MAC DINH chu khong nem: mot sac thai
            #    la khong doc duoc khong dang lam hong ca lo, va `trung_tinh` la
            #    mot cau tra loi dung khi ta khong biet. Sai luoc do o `chu` moi
            #    la loi — do la thu san pham.
            "cam_xuc": cx if cx in CAM_XUC else CAM_XUC[0],
            "kieu_noi": kn if kn in KIEU_NOI else KIEU_NOI[0],
            "nhan_manh": [str(x) for x in nm][:8] if isinstance(nm, list) else [],
            # ⭐ **`khong_chac` — chi THU, ⛔ khong lam gi voi no.** Xem
            #    `QUY_TAC_TU_KHAI` va `B2_DICH.md` §4i. Doc **khoan dung**: vang
            #    mat, sai kieu, hay rong deu ra `[]` — ⛔ mot cot chan doan
            #    KHONG duoc lam hong mot lo loi thoai.
            "khong_chac": _chuoi_ngan(v.get("khong_chac")),
        }

    thieu = sorted(ma_da_gui - set(ra))
    if thieu:
        raise ThieuDoan(_t('Thiếu lời thoại cho {n} đoạn.').format(n=len(thieu)))
    return ra


# ══════════════════════════════════════════════════════════════════════════════
#  Dung tai lieu
# ══════════════════════════════════════════════════════════════════════════════

def dung(ban_ghi_giu: dict, chuyen: dict, *, ma_giong: str, van_tay_ban: str,
         provider: str, model: str, ngon_ngu_dich: str = "vi") -> dict:
    """Dung ban long tieng tu ban chep loi DA LOC + bang `{ma: ket qua}`.

    ⭐ Tai lieu nay la mot **sieu tap** cua tai lieu van ban cu, khong phai mot
       hinh dang moi: no van co `schema`/`doan[].ma,bat,ket,goc,chu` nen
       `van_ban.kiem` va cac giai doan ha nguon (pha 15-17) doc duoc nguyen ven.
       Doi hinh dang o day de "cho sach" se bat pha 15, 16, 17 va QC cung doi
       trong mot lan — va do la cach mot pha bien thanh bon.
    """
    from . import van_ban

    doan_goc = list((ban_ghi_giu or {}).get("doan") or [])
    if not doan_goc:
        raise LongTiengError(_t('Không có đoạn nào được giữ lại để lồng tiếng.'))
    if not ma_giong:
        raise LongTiengError(_t('Chưa ràng giọng nên chưa thể viết lời thoại.'))

    ra = []
    thieu = []
    for d in doan_goc:
        ma = str(d.get("ma") or "")
        kq = chuyen.get(ma)
        if not kq:
            thieu.append(ma)
            continue
        ra.append({
            "ma": ma,
            "bat": float(d.get("bat") or 0.0),
            "ket": float(d.get("ket") or 0.0),
            "goc": str(d.get("chu") or ""),
            "chu": str(kq.get("chu") or ""),
            "cam_xuc": kq.get("cam_xuc") or CAM_XUC[0],
            "kieu_noi": kq.get("kieu_noi") or KIEU_NOI[0],
            "nhan_manh": list(kq.get("nhan_manh") or []),
        })
    if thieu:
        raise ThieuDoan(_t('Thiếu lời thoại cho {n} đoạn.').format(n=len(thieu)))

    return {
        "schema": van_ban.SCHEMA_VAN_BAN,
        # 🔑 Khoa la `muc`, khong phai `doan` — do la ten ma `van_ban.kiem` va
        #    `giai_doan_giong` doc. Lan dau toi viet `doan` vi doc danh sach
        #    truong trong ham dung thay vi doc **dict no thuc su phat ra**, va
        #    ca chuoi hong o giai doan sau voi mot thong bao khong lien quan
        #    ("van ban da xu ly khong co muc nao").
        # 🔑 N-21: hang cua CHINH loi nhac nay, ⛔ khong phai hang cua
        #    `dich_thuat`. Truoc 24/09 hai thu dung chung mot hang, nen sua loi
        #    nhac dich lam van tay long tieng doi theo.
        "loi_nhac": van_ban.PHIEN_BAN_LOI_NHAC_LONG_TIENG,
        "schema_long_tieng": SCHEMA_LONG_TIENG,
        "phien_ban_long_tieng": PHIEN_BAN_LONG_TIENG,
        "ngon_ngu_goc": str((ban_ghi_giu or {}).get("ngon_ngu") or ""),
        "ngon_ngu_dich": str(ngon_ngu_dich or "vi"),
        "provider": str(provider or ""),
        "model": str(model or ""),
        # 🔑 Giong bi **DONG BANG** vao tai lieu. Doi giong sau khi da viet loi la
        #    doi ca cach xung ho va giong dieu cua tung cau — nen no phai lam van
        #    tay doi, tuc lam tai lieu nay vo hieu, chu khong duoc am tham dung
        #    loi cu voi mot giong khac.
        "ma_giong": str(ma_giong),
        #: Ban bien tap ma tap doan nay duoc loc ra tu do.
        "van_tay_ban": str(van_tay_ban or ""),
        "muc": ra,
    }


def kiem(tai_lieu: dict, ban_ghi_giu: dict | None = None) -> None:
    """Nem `LongTiengError` neu tai lieu khong dung hop dong.

    Phu kin **chinh xac**: khong thua mot ma, khong thieu mot ma, dung thu tu.
    """
    from . import van_ban

    van_ban.kiem(tai_lieu, None)

    if str(tai_lieu.get("schema_long_tieng") or "") != SCHEMA_LONG_TIENG:
        raise LongTiengError(_t('Bản lồng tiếng sai lược đồ.'))
    if not str(tai_lieu.get("ma_giong") or ""):
        raise LongTiengError(_t('Bản lồng tiếng không ghi giọng đã chọn.'))

    for d in tai_lieu.get("muc") or []:
        if d.get("cam_xuc") not in CAM_XUC:
            raise LongTiengError(_t('Sắc thái không nằm trong bảng cho phép.'))
        if d.get("kieu_noi") not in KIEU_NOI:
            raise LongTiengError(_t('Lối nói không nằm trong bảng cho phép.'))

    if ban_ghi_giu is not None:
        can = [str(d.get("ma") or "") for d in (ban_ghi_giu.get("doan") or [])]
        co = [str(d.get("ma") or "") for d in (tai_lieu.get("muc") or [])]
        if co != can:
            # ⛔ Hai huong hong khac han nhau, va thong bao phai noi ro huong nao:
            #    thua = mot cau duoc doc len cho mot doan hinh **da bi cat**;
            #    thieu = mot doan hinh con do ma **im lang**.
            thua = sorted(set(co) - set(can))
            thieu = sorted(set(can) - set(co))
            raise LongTiengError(
                _t('Bản lồng tiếng không phủ đúng phần giữ lại: '
                   'thừa {thua}, thiếu {thieu}.')
                .format(thua=len(thua), thieu=len(thieu)))


def van_tay_long_tieng(*, checksum_ban_ghi: str, van_tay_ban: str, ma_giong: str,
                       provider: str, model: str, ngon_ngu_dich: str = "vi") -> str:
    """Van tay cua ban long tieng.

    Nam thanh phan, va thieu bat cu cai nao deu lam cache noi doi:
    noi dung nguon · **ban bien tap** (doi phan giu lai) · **giong** (doi xung ho
    va giong dieu) · provider/model · phien ban ma.
    """
    goi = json.dumps({
        "ban_ghi": checksum_ban_ghi,
        "ban": van_tay_ban,
        "giong": ma_giong,
        "ngon_ngu_dich": ngon_ngu_dich,
        "provider": provider,
        "model": model,
        "phien_ban": PHIEN_BAN_LONG_TIENG,
        "schema": SCHEMA_LONG_TIENG,
    }, sort_keys=True)
    return hashlib.sha256(goi.encode("utf-8")).hexdigest()


def tom_tat(tai_lieu: dict) -> dict:
    doan = list(tai_lieu.get("muc") or [])
    dem: dict[str, int] = {}
    for d in doan:
        c = str(d.get("cam_xuc") or "")
        dem[c] = dem.get(c, 0) + 1
    return {
        "so_doan": len(doan),
        "ma_giong": str(tai_lieu.get("ma_giong") or ""),
        "van_tay_ban": str(tai_lieu.get("van_tay_ban") or ""),
        "sac_thai": dem,
        "so_ky_tu": sum(len(str(d.get("chu") or "")) for d in doan),
    }

"""Nhan dien watermark/logo tinh trong video — CONG CU DO cua V6 pha 13.

⛔ **Tep nay song o `tools/`, khong o `apps/`, va do la mot phan quyet.**

   Pha 13 hoi *"auto-detect watermark; remove/inpaint chi bat neu quality/
   resource gate dat"*. Ba vong do cho ra:

     · cong TAI NGUYEN **DAT** — `delogo` ton 8,9e-5 s/khung, tuc 4,8 s cho mot
       video 30 phut tren ngan sach 540 s;
     · cong CHAT LUONG **KHONG DAT** — bo do nay khong tim "watermark", no tim
       **vung TINH**, va vung tinh bao gom ca noi dung.

   ⇒ Viec xoa bi chan **khong phai vi dat** — no re — ma vi **khong chi dung
     duoc cho can xoa**.

⭐ Nen day la mot cong cu da tao ra mot QUYET DINH, khong phai mot nang luc san
   pham. Chuyen no vao `apps/` sau nay phai la mot quyet dinh co y thuc, khong
   phai mot dong import.

Xem `docs/auto_scan_video_v6/PHA13_NHAN_DIEN_WATERMARK.md` cho toan bo so do.

---


## Cau hoi ma pha 13 dat ra, va cau no KHONG dat ra

De bai: *"Auto-detect watermark/logo; benchmark CPU/GPU; remove/inpaint **chi bat
neu quality/resource gate dat**."*

⛔ Nen ket cuc hop le hoan toan co the la **do xong roi de TAT**. Theo thang diem
   V6, mot tinh nang *"chi co UI nhung output khong doi"* duoc **toi da 40** —
   tuc mot nut "Xoa watermark" khong lam gi la mot khoan LO diem, khong phai mot
   khoan hoa von. Module nay do; viec bat hay khong la mot quyet dinh co so.

## Nguyen ly: watermark tinh la vung KHONG DOI trong khi canh thi doi

Mot dau tinh (logo dai, ban quyen, tag mang xa hoi) giu nguyen diem anh qua
thoi gian. Nen phep do la **do lech chuan theo THOI GIAN** cua tung o luoi qua
N khung hinh lay mau. O nao dung im trong khi phan con lai doi la mot ung vien.

⚠️ Va do la cho phep do nay de sai theo hai huong, nen ca hai deu bi chan
   tuong minh:

**① Canh vốn dĩ tinh.** Mot video la anh tinh, mot canh quay co dinh khong ai
   cu dong — o nao cung "on dinh", va bo do se bao ca khung hinh la watermark.
   ⇒ Neu ti le o tinh vuot `TRAN_TI_LE_TINH` thi **tu choi ket luan** thay vi
     tra ve mot danh sach vo nghia. Mot bo do biet noi *"toi khong do duoc"* la
     mot bo do dung duoc; mot bo do luon tra loi thi khong.

**② Vien den / letterbox.** Hai thanh den tren duoi cung "on dinh" tuyet doi.
   Chung khac watermark o cho **khong co chi tiet**: do lech chuan theo KHONG
   GIAN trong o gan bang 0. Mot logo thi co bien, co chu, co canh.
   ⇒ Hai truc do phai duoc hoi RIENG. Gop chung lai la dung cai loi ma
     `hinh_hoc` ton tai de tranh: mot phep do tra loi hai cau hoi.

## ⭐ Tach PHEP DO khoi VIEC DOC TEP, co chu dinh

`do_tu_khung(mang)` khong biet gi ve ffmpeg. Ba loi ich, va loi ich thu ba moi
la ly do:

  1. kiem duoc ma khong can encode gi;
  2. doi chung tiem duoc thang vao mang so;
  3. **chan luon duong "do bang cach doc mot ban ghi cu"** — ham nay khong co
     duong nao lay du lieu ngoai doi so cua no. Xem
     `chay-rieng-tren-may-ranh-chi-la-bac-mot`: thoi luong 1,65 giay tung lo ra
     mot phep do thuc chat chi doc mot tep.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field

#: Ten schema cua ket qua. Ket qua nay se di vao `outputs` cua `media_prepare`,
#: tuc vao mot ban ghi ben lau — nen no phai tu khai nhu moi ban ghi khac.
SCHEMA = "asv.watermark.v1"
PHIEN_BAN_DO = 1

#: So khung lay mau. 12 la mot su danh doi da do (xem `PHA13_*.md`): duoi 8 thi
#: mot canh chuyen dong cham cho ra o "on dinh" gia, tren 16 thi chi phi tang ma
#: ket qua khong doi.
SO_KHUNG_MAU = 12

#: Chieu rong luoi (so o). Cao suy ra tu ti le khung de o luon vuong.
#:
#: ⚠️ 32 o ngang tren mot khung 1920 la ~60px mot o. Mot logo goc man thuong
#:    chiem 2-4 o. Luoi min hon bat duoc dau nho hon nhung cung bat duoc nhieu
#:    NHIEU hon — va nhieu o day co gia: mot vung che thua cho khach la mot vung
#:    hinh bi mo ma ho khong yeu cau.
LUOI_NGANG = 32

#: Do lech chuan theo THOI GIAN (thang 0..255) duoi muc nay thi coi la "dung im".
NGUONG_ON_DINH = 2.5

#: Do lech chuan theo KHONG GIAN trong mot o. Duoi muc nay thi o do **phang** —
#: mot thanh vien den, mot manh troi, khong phai mot dau.
NGUONG_CHI_TIET = 6.0

#: Ti le o "dung im" ma tren do ta TU CHOI ket luan (canh von di tinh).
TRAN_TI_LE_TINH = 0.60

#: 🔴 **Nguong TUYET DOI mot minh khong du, va phep do dau tien da chung minh.**
#:
#:    Tren mot canh nhieu ngau nhien (khong co dau nao ngoai cai ta cay vao), bo
#:    do tra ve **BAY** dau: mot dau that va **sau** dau mot-o co `on_dinh`
#:    2,2-2,35 — dung duoi nguong 2,5. Do khong phai loi cai dat: voi ~544 o,
#:    mot vai o roi vao duoi cua phan bo la chuyen phai xay ra.
#:
#: ⚠️ Va nguong tuyet doi con hong theo huong NGUOC lai: mot canh toi hoac it
#:    tuong phan co do lech thap o KHAP NOI, nen moi o deu "dung im" va bo do
#:    bao ca khung hinh la watermark.
#:
#: ⇒ Tieu chi thu hai la TUONG DOI: mot dau phai tinh hon han **trung vi** cua
#:   chinh khung hinh do. Hai tieu chi noi VA voi nhau — chat hon ca hai, va moi
#:   cai bit mot huong hong cua cai kia.
TI_LE_SO_TRUNG_VI = 0.35

#: 🔴 **TRUC THU HAI — do doc cua ANH TRUNG BINH theo thoi gian.**
#:
#:    Truc 1 (phuong sai theo thoi gian) gia dinh watermark DUNG IM. Dung cho
#:    mot dau DUC; sai cho mot dau **ban trong suot** — ma do moi la dang pho
#:    bien, vi diem cua watermark la khong che mat noi dung.
#:
#: ⛔ Do duoc tren ba nguon dong voi watermark `white@0.55`: ti le
#:    `on_dinh_trong_hop / trung_vi` la **1,46 · 0,92 · 1,24**, trong khi truc 1
#:    can **< 0,35**. Ca ba deu `do_duoc=True` va deu tra ve **0 dau** — mot am
#:    tinh gia IM LANG, dang te nhat.
#:
#: ⭐ Lay TRUNG BINH N khung: nen chuyen dong trung binh hoa ve mot mang muot,
#:    con lop phu tinh dong gop mot hang so o MOI khung nen no song sot nguyen
#:    bien. Do doc khong gian cua anh trung binh vi the cao o mep dau.
#:
#:    Do truoc khi dung (ti le doc trong hop / trung vi): mandelbrot **5,80**,
#:    life **1,84**, smptebars+xoay **10,35**, testsrc2 **23,67**.
#:
#: ⚠️ `life` chi 1,84 nen nguong phai nam duoi do. Va con so nay **hieu chinh
#:    tren bon nguon tong hop** — chua phai tren noi dung that. Ghi vao phan
#:    "con no" cua bao cao pha 13.
#: ⛔ **KHONG DUNG NUA — giu lai vi so do, khong vi ma.**
#:
#:    Truc 2 da duoc dung va do day du. No **tim duoc** watermark ban trong suot
#:    o ca ba nguon dong, nhung kem duong tinh gia khong chap nhan duoc:
#:
#:      mandelbrot       2 dau, mot hop **125 o** phu gan het khung
#:      life             2 dau, ca hai dung cho nhung vo manh
#:      smptebars+xoay   **17 dau**
#:
#:    Mot bo do de nghi 17 vung che sai con TE HON mot bo do khong tim thay gi:
#:    vung che la nang luc DOI DIEM ANH, nen mot de nghi sai khong phien ha —
#:    no pha hinh cua khach vinh vien trong tep ra.
#:
#: ⭐ Da thu loc bang mot truc thu BA — `doc(mean)/mean(doc)`, tuc *"bien o cho
#:    nay co dung yen khong"*. No **khong tach duoc**: trong hop 0,763-0,987 so
#:    voi trung vi khung 0,620-0,946 (cach biet 1,03-1,40), va p90 cua khung da
#:    la 0,825-1,000 — tuc mot phan muoi khung hinh da nam ngang muc cua chinh
#:    cai dau ta muon tim.
#:
#: ⇒ Ket luan pha 13: nhan dien dau **DUC** dat; nhan dien dau **BAN TRONG SUOT
#:   tren nen dong** CHUA DAT bang cac thong ke re tien nay.
#:
#: 🔑 Giu hang so va so do o day thay vi xoa sach: nguoi doc sau se co cung y
#:    tuong ay — no la y tuong tu nhien nhat — va xoa dau vet la moi ho di lai
#:    dung ba vong do nay.
TI_LE_DOC_TOI_THIEU = 1.6

#: So o toi thieu de goi la mot dau.
#:
#: ⭐ Khong phai mot con so lam dep: mot o cua luoi 32 la ~3% chieu rong, tuc
#:    duoi `logo.RONG_TOI_THIEU` (0,03) — mot vung che be hon the la thu khach
#:    khong yeu cau va khong nhin thay.
SO_O_TOI_THIEU = 2

#: Ly do tu choi. Chuoi on dinh vi chung di vao ban ghi va vao giao dien.
LY_DO_CANH_TINH = "canh_tinh"
LY_DO_THIEU_KHUNG = "thieu_khung"

#: 🔴 **Mot lan tu choi phai noi TU CHOI VI SAO.**
#:
#:    Do duoc o ca 5 va ca 3: ca hai deu cho `ti_le_o_tinh = 1,0`, tuc ca hai
#:    deu bi rao ① chan. Nhung chung la hai the gioi khac han:
#:
#:      ca 3  anh tinh lap lai     chi_tiet trung vi ~74   -> canh von di tinh
#:      ca 5  canh toi, it tuong phan  chi_tiet trung vi ~4,4  -> khong DO duoc
#:
#: ⇒ Gop hai cai lam mot nhan la bao khach *"video cua ban la anh tinh"* trong
#:   khi su that la *"video cua ban qua toi de bo do nay noi duoc gi"*. Cau thu
#:   nhat sai; cau thu hai con goi y duoc mot viec lam duoc (tang sang roi do
#:   lai). Truc `chi_tiet` phan biet duoc, va no da co san.
LY_DO_TUONG_PHAN_THAP = "tuong_phan_thap"


@dataclass(frozen=True)
class Dau:
    """Mot dau tinh tim duoc. Toa do CHUAN HOA 0..1, khong bao gio pixel.

    ⭐ Cung he toa do voi `vung_che` — co chu dinh. Mot dau tim duoc phai **dan
       thang vao duoc** o "vung che" ma khach da co, khong phai mot he toa do
       thu hai cho khach tu doi.
    """

    x0: float
    y0: float
    x1: float
    y1: float
    #: Do lech chuan theo thoi gian, cang thap cang tinh.
    on_dinh: float
    #: Do lech chuan theo khong gian, cang cao cang co chi tiet.
    chi_tiet: float
    #: So o luoi gop thanh dau nay.
    so_o: int

    def sang_vung(self, loai: str = "lam_mo") -> dict:
        """Doi sang dang `vung_che` nhan. Mot ham, khong phai mot doan chep tay."""
        return {"loai": loai, "x0": self.x0, "y0": self.y0,
                "x1": self.x1, "y1": self.y1}


@dataclass(frozen=True)
class KetQua:
    """⛔ Mot ket qua LUON tu giai thich. `ds` rong co the co hai nghia hoan
    toan khac nhau — *"da do, khong co dau nao"* va *"khong do duoc"* — va gop
    hai nghia do vao mot danh sach rong la dung cai loi ma
    `khong-doi-chung-thi-so-khong-khong-phai-phat-hien` mo ta: mot so 0 trong
    giong het mot phat hien.
    """

    do_duoc: bool
    ds: tuple[Dau, ...] = ()
    ly_do: str = ""
    ti_le_o_tinh: float = 0.0
    so_khung: int = 0
    schema: str = SCHEMA

    def sang_dict(self) -> dict:
        return {"schema": self.schema, "phien_ban": PHIEN_BAN_DO,
                "do_duoc": self.do_duoc, "ly_do": self.ly_do,
                "ti_le_o_tinh": round(self.ti_le_o_tinh, 4),
                "so_khung": self.so_khung,
                "ds": [{"x0": round(d.x0, 4), "y0": round(d.y0, 4),
                        "x1": round(d.x1, 4), "y1": round(d.y1, 4),
                        "on_dinh": round(d.on_dinh, 3),
                        "chi_tiet": round(d.chi_tiet, 3),
                        "so_o": d.so_o} for d in self.ds]}


def _gop_o(o_tot: set[tuple[int, int]]) -> list[list[tuple[int, int]]]:
    """Gom cac o ke nhau (4 huong) thanh cum. Duyet theo chieu rong, khong de quy.

    ⚠️ Khong de quy co ly do: mot vung tinh lon (ca mot canh quay co dinh lot
       qua rao ①) co the co hang nghin o, va Python dung o ~1.000 muc de quy.
       Mot bo do bao `RecursionError` tren mot video hop le la mot bo do hong.
    """
    con = set(o_tot)
    cum = []
    while con:
        goc = con.pop()
        nhom = [goc]
        hang_doi = [goc]
        while hang_doi:
            c, h = hang_doi.pop()
            for dc, dh in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                k = (c + dc, h + dh)
                if k in con:
                    con.discard(k)
                    nhom.append(k)
                    hang_doi.append(k)
        cum.append(nhom)
    return cum


def do_tu_khung(khung) -> KetQua:
    """Do tren mot mang `(N, H, W)` xam uint8. **Khong cham dia, khong cham mang.**

    Tra `KetQua` tu giai thich. Xem docstring dau tep cho hai rao ① va ②.
    """
    import numpy as np

    a = np.asarray(khung)
    if a.ndim != 3 or a.shape[0] < 3:
        return KetQua(do_duoc=False, ly_do=LY_DO_THIEU_KHUNG,
                      so_khung=int(a.shape[0]) if a.ndim == 3 else 0)

    n, cao, rong = a.shape
    canh = max(4, rong // LUOI_NGANG)          # canh o, tinh bang pixel
    so_c, so_h = rong // canh, cao // canh
    if so_c < 2 or so_h < 2:
        return KetQua(do_duoc=False, ly_do=LY_DO_THIEU_KHUNG, so_khung=n)

    f = a[:, :so_h * canh, :so_c * canh].astype("float32")
    # (N, so_h, canh, so_c, canh) -> gop hai truc pixel lai cho tung o
    o = f.reshape(n, so_h, canh, so_c, canh).transpose(0, 1, 3, 2, 4)
    o = o.reshape(n, so_h, so_c, canh * canh)

    # ① truc THOI GIAN: trung binh o qua tung khung, roi do lech giua cac khung
    tb_khung = o.mean(axis=3)                        # (N, so_h, so_c)
    on_dinh = tb_khung.std(axis=0)                   # (so_h, so_c)
    # ② truc KHONG GIAN: chi tiet ben trong o, lay trung binh qua cac khung
    chi_tiet = o.std(axis=3).mean(axis=0)            # (so_h, so_c)

    # 🔴 **HAI cau hoi, HAI phep do — va gop chung lai da lam rao ① chet.**
    #
    #    Rao ① hoi *"ca canh nay co dung im khong"*: mot cau TUYET DOI.
    #    Viec chon ung vien hoi *"o nao tinh HON HAN phan con lai"*: mot cau
    #    TUONG DOI.
    #
    # ⚠️ Ban dau toi dung mot bien `tinh` cho ca hai. Do tren mot canh tinh
    #    hoan toan: `on_dinh` khong bang 0 ma la **bui lam tron float32** (toi
    #    da 2,3e-5). Truc tuyet doi ra dung **1,0**; truc tuong doi dem bui so
    #    voi bui ra **0,27** — duoi tran 0,60, nen rao ① khong bao gio ban.
    #
    # ⭐ Cung bai hoc ma `hinh_hoc` duoc sinh ra de ghi: mot phep do tra loi hai
    #    cau hoi la mot phep do se tra loi sai mot trong hai.
    tinh_tuyet_doi = on_dinh < NGUONG_ON_DINH
    ti_le = float(tinh_tuyet_doi.mean())
    if ti_le > TRAN_TI_LE_TINH:
        # Rao ①: tu choi ket luan thay vi tra rac — kem LY DO phan biet duoc.
        ly_do = (LY_DO_CANH_TINH if float(np.median(chi_tiet)) >= NGUONG_CHI_TIET
                 else LY_DO_TUONG_PHAN_THAP)
        return KetQua(do_duoc=False, ly_do=ly_do,
                      ti_le_o_tinh=ti_le, so_khung=n)

    # ⚠️ San duoi cho trung vi: so sanh voi mot trung vi bang bui la so sanh vo
    #    nghia. Rao ① da chan ca canh tinh, nhung mot canh GAN tinh (ti le vua
    #    duoi tran) van co trung vi rat nho, va san nay giu phep so sanh co nghia.
    trung_vi = max(float(np.median(on_dinh)), 0.05)
    tinh = tinh_tuyet_doi & (on_dinh < TI_LE_SO_TRUNG_VI * trung_vi)

    # Rao ②: o phang (vien den, manh troi) khong phai mot dau.
    #
    # ⛔ **CHI truc 1 (dau DUC). Truc 2 da duoc dung, do, va GO BO.**
    #    Xem `TI_LE_DOC_TOI_THIEU` cho toan bo so do va ly do.
    tot = tinh & (chi_tiet >= NGUONG_CHI_TIET)
    o_tot = {(int(c), int(h)) for h, c in zip(*np.nonzero(tot), strict=True)}

    ds = []
    for nhom in _gop_o(o_tot):
        if len(nhom) < SO_O_TOI_THIEU:
            continue
        cs = [c for c, _ in nhom]
        hs = [h for _, h in nhom]
        ds.append(Dau(
            x0=min(cs) * canh / rong, x1=(max(cs) + 1) * canh / rong,
            y0=min(hs) * canh / cao, y1=(max(hs) + 1) * canh / cao,
            on_dinh=float(on_dinh[hs, cs].mean()),
            chi_tiet=float(chi_tiet[hs, cs].mean()),
            so_o=len(nhom)))
    # Dau lon truoc: mot logo goc man dang quan tam hon mot o le.
    ds.sort(key=lambda d: (-d.so_o, d.y0, d.x0))
    return KetQua(do_duoc=True, ds=tuple(ds), ti_le_o_tinh=ti_le, so_khung=n)


def _lenh_mot_khung(duong: str, *, giay: float, rong: int,
                   ffmpeg: str) -> list[str]:
    """Lenh lay DUNG MOT khung tai moc `giay`. Tach rieng de kiem duoc.

    🔑 `-ss` **truoc** `-i` la tim-den-DAU-VAO: ffmpeg nhay toi khung khoa gan
       moc roi giai ma mot khung. Chi phi la mot hang so — mot lan nhay cong mot
       GOP — **khong phu thuoc thoi luong video**.

    ⛔ Dat `-ss` SAU `-i` se bien no thanh tim-den-DAU-RA: ffmpeg giai ma tu dau
       tep roi vut bo, tuc chi phi ti le voi `giay`. Cung mot co, hai ben cua
       `-i`, hai hang do phuc tap.
    """
    return [ffmpeg, "-hide_banner", "-loglevel", "error",
            "-ss", f"{max(giay, 0.0):.3f}", "-i", duong,
            "-frames:v", "1", "-vf", f"scale={rong}:-2,format=gray",
            "-f", "rawvideo", "-pix_fmt", "gray", "-"]


def _moc_lay_mau(thoi_luong: float, so_khung: int) -> list[float]:
    """Cac moc thoi gian, TRAI DEU va tranh hai dau mut.

    ⚠️ Tranh mut vi hai ly do cu the: khung dau thuong la mot the tieu de tinh,
       va khung cuoi thuong la mot man hinh den. Ca hai deu lam rao ① bắn nham.
    """
    if not thoi_luong or thoi_luong <= 0:
        return [0.0]
    n = max(1, int(so_khung))
    return [thoi_luong * (i + 0.5) / n for i in range(n)]


def lay_khung(duong: str, *, so_khung: int = SO_KHUNG_MAU,
              rong: int = 480, ffmpeg: str = "ffmpeg", thoi_luong: float = 0.0,
              chi_khung_khoa: bool = True):
    """Lay toi da `so_khung` khung xam. MOT lan goi ffmpeg.

    🔴 **`-vf fps=N` KHONG lam ffmpeg doc it di.** No giai ma **moi khung** roi
       vut bot cho du nhip. Voi mot video 30 phut o 30fps do la 54.000 khung
       duoc giai ma de lay ra 12 — tuc mot luot giai ma DAY DU dat ngay trong
       `media_prepare`, giai doan hien chi mat vai giay.

    ⭐ `-skip_frame nokey` giai ma **chi khung khoa**. Mot watermark tinh co mat
       tren khung khoa het nhu tren khung khac, nen phep do khong mat gi; so
       khung phai giai ma tut tu ca luong xuong con vai tram.

    ⛔ Va duong cu van con duoi mot co: mot dinh dang khong co khung khoa doc
       duoc phai **lui** ve duong day du chu khong tra ve rong. Mot bo do im
       lang la mot bo do bao *"khong co watermark"* — va do la mot cau tra loi
       sai, khong phai mot cau tra loi thieu.
    """
    import numpy as np

    goi = []
    for t in _moc_lay_mau(thoi_luong, so_khung):
        p = subprocess.run(_lenh_mot_khung(duong, giay=t, rong=rong,
                                           ffmpeg=ffmpeg),
                           capture_output=True, check=False)
        if p.returncode == 0 and p.stdout:
            goi.append(p.stdout)
    if not goi:
        return np.zeros((0, 0, 0), dtype="uint8")

    # ⛔ Moi khung phai CUNG kich thuoc. Mot tep doi do phan giai giua chung
    #    (co that: quang cao chen vao) se cho hai kich thuoc khac nhau, va gop
    #    chung lai bang `frombuffer` se ra mot mang vo nghia thay vi mot loi.
    co = max(set(len(x) for x in goi), key=[len(x) for x in goi].count)
    goi = [x for x in goi if len(x) == co]
    p_stdout = b"".join(goi)
    tong = len(p_stdout)
    # Suy chieu cao tu so byte: `scale=rong:-2` giu ti le nen cao khong biet truoc.
    cao = 0
    for thu in range(2, 4000, 2):
        if co % (rong * thu) == 0 and co // (rong * thu) == 1:
            cao = thu
            break
    if cao < 2:
        return np.zeros((0, 0, 0), dtype="uint8")
    n = tong // (rong * cao)
    if n < 1:
        return np.zeros((0, 0, 0), dtype="uint8")
    return np.frombuffer(p_stdout[:n * cao * rong],
                         dtype="uint8").reshape(n, cao, rong)


def do(duong: str, *, thoi_luong: float = 0.0, ffmpeg: str = "ffmpeg") -> KetQua:
    """Doc video roi do. Vo mong quanh `do_tu_khung`."""
    return do_tu_khung(lay_khung(duong, ffmpeg=ffmpeg, thoi_luong=thoi_luong))


# ══════════════════════════════════════════════════════════════════════════════
#  Cong tai nguyen cho viec XOA
# ══════════════════════════════════════════════════════════════════════════════

#: 🔴 **Nhan dien va XOA la hai bai toan cach nhau mot bac do lon.**
#:
#:    Nhan dien doc `SO_KHUNG_MAU` khung — mot hang so, khong phu thuoc do dai
#:    video. Xoa (inpaint) phai sua **moi khung**, tuc chi phi ti le voi ca do
#:    dai LAN do phan giai.
#:
#: ⚠️ Va tran gio cua job da la mot rang buoc DANG MO: `CHAN_DOAN_TEST_448.md`
#:    §10 ghi ASV nhan video **120 phut** trong khi tran job la **60 phut**, va o
#:    142 giay/lo chi ~20 phut video lot qua. Them mot luot sua tung khung vao
#:    mot ngan sach da thieu la lam no thieu nang hon.
#:
#: ⇒ Nen cong nay hoi mot cau duy nhat, va hoi bang SO DO DUOC, khong bang y kien.
TRAN_JOB_GIAY = 3600.0

#: Phan ngan sach job toi da duoc phep danh cho viec xoa watermark.
#:
#: ⛔ Khong phai 100%: xoa watermark la mot buoc PHU. Mot buoc phu an het ngan
#:    sach cua buoc chinh thi lan chay hong, va no hong o giai doan sau — tuc
#:    sau khi khach da cho.
PHAN_NGAN_SACH_TOI_DA = 0.15


@dataclass(frozen=True)
class CongXoa:
    """Phan quyet cua cong tai nguyen, kem SO da do."""

    mo: bool
    ly_do: str
    giay_uoc: float = 0.0
    tran_giay: float = 0.0
    do: dict = field(default_factory=dict)


def cong_xoa(*, giay_moi_khung: float, so_khung_video: float,
             tran_job_giay: float = TRAN_JOB_GIAY) -> CongXoa:
    """Co du ngan sach de xoa watermark khong. **Chi so, khong y kien.**

    `giay_moi_khung` phai la mot phep DO tren may that, khong phai mot uoc luong
    muon tu mot bai bao — `doi-chieu-cong-dong-truoc-moi-pha`: muon nguong thi
    phai do lai.
    """
    tran = tran_job_giay * PHAN_NGAN_SACH_TOI_DA
    uoc = float(giay_moi_khung) * float(so_khung_video)
    if giay_moi_khung <= 0 or so_khung_video <= 0:
        return CongXoa(mo=False, ly_do="chua_do",
                       giay_uoc=0.0, tran_giay=tran)
    mo = uoc <= tran
    return CongXoa(
        mo=mo,
        ly_do="du_ngan_sach" if mo else "vuot_ngan_sach",
        giay_uoc=uoc, tran_giay=tran,
        do={"giay_moi_khung": giay_moi_khung, "so_khung_video": so_khung_video,
            "phan_ngan_sach_toi_da": PHAN_NGAN_SACH_TOI_DA})


def bao_cao_json(kq: KetQua) -> str:
    return json.dumps(kq.sang_dict(), sort_keys=True, ensure_ascii=False)

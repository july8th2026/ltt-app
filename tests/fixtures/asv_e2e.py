"""Nguon THAT cho nghiem thu dau-cuoi (pha 22) — va cac cua duoc THAY THE.

## Vi sao khong dung `asv_media.tiny_mp4`

`tiny_mp4` la mot am **sin** 440 Hz tren mot khung hinh tinh. No dung cho thu no
sinh ra: mot dau vao xac dinh, khong ban quyen, khong PII (xem docstring cua no).
Nhung mot nghiem thu chuc nang khong the chay tren no:

    khong co loi noi   -> ASR that tra ve KHONG DOAN, va `TRANSCRIBE` dung khi
                          tu choi. Moi tep test chay het chuoi vi vay deu phai
                          thay ASR bang mot ban ghi gia (`asv_media.ban_ghi_gia`).
    khong co cat canh  -> `SCENE_ANALYZE` khong co gi de phan tich, nen ban bien
                          tap khong co quyet dinh nao de ra.
    khong co nguoi noi -> phan vai khong co gi de tach.

⇒ Tuc moi thu **rieng cua V4** — doc canh, ban bien tap, chon giu/cat — deu chay
  tren dau vao khong kich hoat duoc chung. Do la ly do pha 22 ton tai.

## Vi sao SAPI, va vi sao no KHONG phai mot ban gia lap

Windows co san `System.Speech` (SAPI 5) voi nam giong en-US cai dat sang. No
sinh ra **tieng noi that**: song am that, phu am that, ngat nghi that, hai giong
phan biet duoc. `faster-whisper` chep lai duoc no — va do la phep thu: neu ASR
that doc ra dung cau ta da doc vao, thi dau vao la tieng noi that chu khong phai
mot dang song trong giong tieng noi.

⭐ Va no khong keo theo ban quyen, khong PII, khong can mang, khong can khoa —
   dung ba tinh chat da khien `asv_media` chon lavfi ngay tu dau. Chi khac la no
   con **noi duoc**.

⛔ Diem no KHONG chung minh, va bao cao pha 22 phai noi thang: SAPI la giong
   **tieng Anh**. No dung duoc cho ban **NGUON** (video nuoc ngoai — dung ca boi
   canh san pham), va no **khong** thay duoc `LTTStudioVoice` o dau ra. Chat
   luong long tieng tieng Viet chi dong lai duoc bang mot lan chay that qua
   sidecar :8120.
"""
from __future__ import annotations

import array
import json
import math
import re
import statistics
import shutil
import subprocess
import unicodedata
import wave
from dataclasses import dataclass, field
from pathlib import Path

from .asv_media import ffmpeg_bin

#: Giong SAPI dung cho ban nguon. Hai giong khac gioi de phan vai co viec that.
GIONG_NAM = "David"
GIONG_NU = "Zira"

#: Do phan giai va nhip khung cua ban nguon. Nho de nhanh, du lon de NVENC khong
#: roi vao bay kich thuoc toi thieu (`platform_core/media.py:174`).
KHUNG_HINH = "640x360"
NHIP_KHUNG = 24


@dataclass(frozen=True)
class Loi:
    """Mot cau thoai trong ban nguon, kem SU THAT ta biet truoc khi chay."""

    ma: str
    chu: str
    giong: str
    #: Giay bat dau trong ban nguon hoan chinh.
    bat: float
    #: Do dai that do duoc sau khi tong hop.
    giay: float = 0.0


@dataclass(frozen=True)
class Canh:
    ten: str
    bat: float
    ket: float
    #: Bieu thuc lavfi dung sinh hinh cho canh nay.
    hinh: str


@dataclass
class SuThat:
    """Nhung gi ta BIET ve ban nguon truoc khi bat cu giai doan nao chay.

    🔑 Mot nghiem thu doi chieu dau ra voi cai nay chu khong doi chieu voi chinh
       no. Khong co su that doc lap thi moi phep kiem dau-cuoi chi con noi duoc
       "chuoi chay xong", chu khong noi duoc "chuoi chay **dung**".
    """

    duong: str = ""
    thoi_luong: float = 0.0
    canh: list[Canh] = field(default_factory=list)
    loi: list[Loi] = field(default_factory=list)

    def moc_cat_canh(self) -> list[float]:
        return [c.bat for c in self.canh[1:]]


# ══════════════════════════════════════════════════════════════════════════════
#  SAPI
# ══════════════════════════════════════════════════════════════════════════════

def co_sapi() -> bool:
    """Co may doc tieng noi ngoai tuyen khong. Khong bao gio nem."""
    try:
        import win32com.client  # noqa: F401
    except Exception:           # noqa: BLE001 - thieu la mot cau tra loi
        return False
    try:
        _giong_sapi()
        return True
    except Exception:           # noqa: BLE001
        return False


def _giong_sapi():
    import win32com.client as w

    may = w.Dispatch("SAPI.SpVoice")
    return may, may.GetVoices()


def noi(chu: str, dest: Path, *, giong: str = GIONG_NAM, toc_do: int = 0) -> Path:
    """Doc `chu` thanh mot tep WAV THAT. `toc_do` la thang SAPI (-10..10)."""
    import win32com.client as w

    may, ds = _giong_sapi()
    chon = None
    for i in range(ds.Count):
        if giong.lower() in ds.Item(i).GetDescription().lower():
            chon = ds.Item(i)
            break
    if chon is None:
        raise RuntimeError(f"khong co giong SAPI ten {giong!r}")

    dest.parent.mkdir(parents=True, exist_ok=True)
    tep = w.Dispatch("SAPI.SpFileStream")
    tep.Open(str(dest), 3)          # SSFMCreateForWrite
    try:
        may.Voice = chon
        may.Rate = int(toc_do)
        may.AudioOutputStream = tep
        may.Speak(chu)
    finally:
        tep.Close()
        may.AudioOutputStream = None
    return dest


def giay_wav(duong: Path) -> float:
    with wave.open(str(duong), "rb") as f:
        return f.getnframes() / float(f.getframerate() or 1)


# ══════════════════════════════════════════════════════════════════════════════
#  Ban nguon
# ══════════════════════════════════════════════════════════════════════════════

#: Kich ban nguon. Tieng Anh — dung boi canh san pham (video nuoc ngoai vao,
#: ban long tieng tieng Viet ra) va dung thu ASR that doc duoc.
#:
#: ⚠️ Cau chu can DAI vua du: mot cau hai tu bi `faster-whisper` gop hoac bo, va
#:    khi do phep doi chieu that bai vi ly do khong lien quan gi den ASV.
KICH_BAN: tuple[tuple[str, str, str], ...] = (
    ("l1", GIONG_NAM,
     "Good morning everyone, and welcome to the workshop on video localization."),
    ("l2", GIONG_NU,
     "Thank you. Can you show us how the first example actually works in practice?"),
    ("l3", GIONG_NAM,
     "Of course. The system reads the picture first, and only then decides what to keep."),
    ("l4", GIONG_NU,
     "That is a much better order than translating everything before looking at it."),
)

#: Hinh cua tung canh. Khac han nhau de bo loc `select='gt(scene,0.4)'` bao that.
#:
#: 🔑 Canh THU TU khong co loi thoai nao — va do la chu dich. Mot preset "cat
#:    thong minh" phai co it nhat mot ung vien cat ro rang de nghiem thu tra loi
#:    duoc cau hoi "no CO cat khong", chu khong phai "no khong co gi de cat".
HINH_CANH: tuple[str, ...] = (
    "smptebars",
    "testsrc2",
    "color=c=0x101830",
    "testsrc",
)

#: Do dai canh im lang o cuoi. Dai hon `canh.CANH_NGAN_NHAT_S` de no khong bi
#: gop vao canh truoc.
CANH_IM_LANG_S = 5.0

#: Khoang lang giua hai cau, giay. Du de `silencedetect` tach duoc cau.
LANG_GIUA = 1.2
#: Khoang lang dau va cuoi ban nguon.
LANG_BIEN = 0.8


def _chay(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, capture_output=True)


def nguon_hoi_thoai(thu_muc: Path, *, giu_wav: bool = False) -> SuThat:
    """Dung mot MP4 nhieu canh co HOI THOAI THAT. Tra ve su that di kem.

    Ban dung tach lam hai nua doc lap roi mux:

        tieng  — N tep SAPI noi tiep nhau, chen khoang lang do duoc
        hinh   — N canh lavfi noi bang `concat`, cat cung o cho khong co tieng

    ⭐ Cat canh dat vao GIUA khoang lang, khong dat giua cau. Mot cau bi cat doi
       lam ban bien tap phai chon giu hay bo mot nua cau — mot tinh huong that
       nhung khong phai tinh huong nghiem thu duong chinh nen do.
    """
    binary = ffmpeg_bin()
    if not binary:
        raise RuntimeError("khong co ffmpeg")
    if not co_sapi():
        raise RuntimeError("khong co SAPI")

    thu_muc.mkdir(parents=True, exist_ok=True)
    tam = thu_muc / "_e2e"
    tam.mkdir(exist_ok=True)

    # ── 1. Doc tung cau, do do dai THAT ────────────────────────────────────
    loi: list[Loi] = []
    moc = LANG_BIEN
    for ma, giong, chu in KICH_BAN:
        wav = noi(chu, tam / f"{ma}.wav", giong=giong)
        d = giay_wav(wav)
        loi.append(Loi(ma=ma, chu=chu, giong=giong, bat=moc, giay=d))
        moc += d + LANG_GIUA
    # Cau cuoi + mot khoang bien + MOT CANH IM LANG han hoi o cuoi.
    tong = round(moc - LANG_GIUA + LANG_BIEN + CANH_IM_LANG_S, 3)

    # ── 2. Ghep ban tieng: lang + cau + lang + cau ... ─────────────────────
    vao: list[str] = []
    loc: list[str] = []
    for i, l in enumerate(loi):
        vao += ["-i", str(tam / f"{l.ma}.wav")]
        loc.append(f"[{i}:a]aresample=48000,aformat=sample_fmts=s16:channel_layouts=mono,"
                   f"adelay={int(round(l.bat * 1000))}:all=1[a{i}]")
    # 🔑 **Mot nen lien tuc, va no khong phai trang tri.**
    #
    #    Mot video that gan nhu luon co nen — nhac, tieng dong, tieng phong. Ban
    #    nguon chi co loi noi tren nen IM LANG lam demucs tra ve ba stem gan nhu
    #    rong, va khi do ban phoi cuoi cung co do dong am luong (LRA) rat lon:
    #    do that o luot dau tien la **19,7 LU**. Voi mot LRA nhu vay, `loudnorm`
    #    khong the dat -14 LUFS ma van giu dinh that <= -1,5 dB — chinh no bao
    #    `target_offset: 1.20` — nen QC T4 hong vi **ban nguon**, khong phai vi
    #    san pham.
    #
    # ⛔ Va do la cach mot bo nghiem thu noi doi theo huong nguy hiem nhat: bao
    #    mot khiem khuyet khong co that, roi co nguoi di "sua" nguong QC cho vua
    #    voi mot dau vao khong ai gap ngoai doi.
    vao += ["-f", "lavfi", "-i",
            f"anoisesrc=d={tong}:c=pink:a=0.05",
            "-f", "lavfi", "-i",
            f"sine=frequency=110:duration={tong}"]
    i_nen, i_sine = len(loi), len(loi) + 1
    loc.append(f"[{i_nen}:a]aresample=48000,aformat=sample_fmts=s16:"
               f"channel_layouts=mono,volume=-6dB[nen]")
    loc.append(f"[{i_sine}:a]aresample=48000,aformat=sample_fmts=s16:"
               f"channel_layouts=mono,volume=-20dB[hum]")
    tron = "".join(f"[a{i}]" for i in range(len(loi))) + "[nen][hum]"
    loc.append(f"{tron}amix=inputs={len(loi) + 2}:normalize=0,"
               f"apad,atrim=0:{tong},asetpts=N/SR/TB[out]")
    tieng = tam / "tieng.wav"
    _chay([binary, "-hide_banner", "-loglevel", "error", "-y", *vao,
           "-filter_complex", ";".join(loc), "-map", "[out]",
           "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "1", str(tieng)])

    # ── 3. Hinh: cat canh roi vao GIUA khoang lang ─────────────────────────
    #
    # Hai cho cat: sau cau 1 va sau cau 3. Nen ba canh, va moi canh chua it
    # nhat mot cau tron ven.
    cat1 = round(loi[0].bat + loi[0].giay + LANG_GIUA / 2, 3)
    cat2 = round(loi[2].bat + loi[2].giay + LANG_GIUA / 2, 3)
    #: Canh cuoi bat dau sau khi cau cuoi da doc xong -> khong co loi thoai nao.
    cat3 = round(loi[-1].bat + loi[-1].giay + LANG_BIEN, 3)
    bien = [0.0, cat1, cat2, cat3, tong]
    canh: list[Canh] = []
    phan: list[Path] = []
    for i, hinh in enumerate(HINH_CANH):
        bat, ket = bien[i], bien[i + 1]
        canh.append(Canh(ten=f"c{i + 1}", bat=bat, ket=ket, hinh=hinh))
        p = tam / f"canh{i}.mp4"
        # ⚠️ `color=c=...` DA co dau `=`, nen noi them tham so phai bang `:`.
        #    Noi bang `=` cho ra `color=c=0x101830=size=...` va ffmpeg tra ma
        #    loi -22 khong kem mot dong giai thich nao.
        noi_ts = ":" if "=" in hinh else "="
        _chay([binary, "-hide_banner", "-loglevel", "error", "-y",
               "-f", "lavfi", "-i",
               f"{hinh}{noi_ts}size={KHUNG_HINH}:rate={NHIP_KHUNG}"
               f":duration={ket - bat:.3f}",
               "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
               "-g", str(NHIP_KHUNG), str(p)])
        phan.append(p)

    ds = tam / "canh.txt"
    ds.write_text("".join(f"file '{p.as_posix()}'\n" for p in phan), encoding="ascii")
    hinh_noi = tam / "hinh.mp4"
    _chay([binary, "-hide_banner", "-loglevel", "error", "-y",
           "-f", "concat", "-safe", "0", "-i", str(ds), "-c", "copy", str(hinh_noi)])

    # ── 4. Mux ────────────────────────────────────────────────────────────
    ra = thu_muc / "nguon_hoi_thoai.mp4"
    _chay([binary, "-hide_banner", "-loglevel", "error", "-y",
           "-i", str(hinh_noi), "-i", str(tieng),
           "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
           "-shortest", str(ra)])

    if not giu_wav:
        for p in tam.glob("*.wav"):
            if p.name != "tieng.wav":
                p.unlink(missing_ok=True)

    return SuThat(duong=str(ra), thoi_luong=tong, canh=canh, loi=loi)


# ══════════════════════════════════════════════════════════════════════════════
#  Cac cua duoc THAY THE — khai bao, khong giau
# ══════════════════════════════════════════════════════════════════════════════
#
# 🔑 Danh sach nay la mot **ban khai**, va bao cao nghiem thu doc thang tu no.
#    Mot nghiem thu noi "chay that" ma khong noi duoc cho nao khong that thi
#    khong phai mot nghiem thu — no la mot loi qua quyet.
#
# ⛔ Va `test_448` chot rang moi ten trong day CON TON TAI. Mot bao cao goi ten
#    mot cua da bi doi ten la mot bao cao ve mot chuong trinh khong con nua.

@dataclass(frozen=True)
class CuaThayThe:
    #: Module.ten cua cua bi thay.
    ten: str
    #: Vi sao khong chay duoc that TREN MAY NAY.
    ly_do: str
    #: Cai gi con lai la that o phia sau cua do.
    con_that: str


THAY_THE: tuple[CuaThayThe, ...] = (
    CuaThayThe(
        ten="platform_core.llm.dieu_phoi.goi",
        ly_do="khoa provider nam trong C:\\LTTPlatform\\secrets (ACL chan doc); "
              "mot bo nghiem thu khong duoc doi hoi mot khoa tra tien",
        con_that="ai.goi (thu tu provider, ban do model, tran token, phan loai mo ho) "
                 "va ai.goi_tinh_tien (cua chan ngan sach, so cai su_dung, "
                 "UNIQUE(run_id, ma_dispatch)) deu chay that"),
    CuaThayThe(
        ten="apps.auto_scan_video.giong_noi.doc_mot_doan",
        ly_do="LTTStudioVoice :8120 doi LTT_VOICE_SIDECAR_TOKEN, cung nam trong "
              "secrets bi ACL chan",
        con_that="tieng tra ve la WAV THAT do SAPI sinh, nen bac thang nan cho vua, "
                 "phep kiem tep tieng, tron nen, chuan am luong va ket xuat deu "
                 "lam viec tren song am that"),
    CuaThayThe(
        ten="apps.auto_scan_video.giong_noi.giai_giong",
        ly_do="giai giong doc kho giong cua LTT VOICE; khong co sidecar thi khong "
              "co ban giong nao de giai",
        con_that="quyen so huu giong duoc kiem rieng o test_409/test_435"),
    CuaThayThe(
        ten="apps.auto_scan_video.giong_noi.san_sang",
        ly_do="hoi sidecar :8120 tra 401 khong token",
        con_that="duong tu choi khi sidecar vang duoc kiem rieng o test_409"),
)


def _mo_ta_thao_tac(thao_tac) -> str:
    return getattr(thao_tac, "ma", "")


def _bo_dau(chu: str) -> str:
    """Bo dau tieng Viet. SAPI doc en-US, dau tieng Viet lam no nga giong."""
    tach = unicodedata.normalize("NFD", chu)
    khong_dau = "".join(c for c in tach if unicodedata.category(c) != "Mn")
    return khong_dau.replace("\u0111", "d").replace("\u0110", "D")


def dat_cua_model(monkeypatch, *, su_that: SuThat | None = None):
    """Thay **mot mieng**: luot HTTP toi model. Moi tang tren no chay that.

    ⭐ Thay o `dieu_phoi.goi` chu khong o `ai.goi_tinh_tien` (nhu
       `asv_media.cua_ai_gia` lam) la co chu dich: `goi_tinh_tien` la duong
       **tra tien** — cua chan ngan sach, ghi so cai, chan ghi trung. Thay no di
       thi bai nghiem thu khong con noi gi ve hoa don, va hoa don la mot trong
       nhung thu pha 22 phai chung minh.
    """
    from platform_core.llm import cong_vlm
    from apps.auto_scan_video import ai, long_tieng

    dem: dict[str, int] = {}

    def tra(noi_dung: dict) -> cong_vlm.KetQuaChat:
        van = json.dumps(noi_dung, ensure_ascii=False)
        return cong_vlm.KetQuaChat(
            noi_dung=van, model="qwen38-thay-the",
            su_dung=cong_vlm.SuDung(token_vao=len(van) // 4,
                                    token_ra=len(van) // 4, dang_tin=True))

    def gia(db, *, messages, thu_tu_provider, model_theo_provider=None,
            max_tokens=None, temperature=None, on_dispatch=None,
            on_rejected=None, **kw):
        # ⭐ Nen tang goi `on_dispatch` NGAY TRUOC khi ra mang. Goi lai o day de
        #    ngu nghia dispatch ben vung (I5) van duoc chay that.
        # ⚠️ MOT tham so — dung nhu `dieu_phoi.goi:210` goi. Ban dau o day
        #    truyen ca ten model, va `JobContext.provider_dispatched` nem
        #    "takes from 1 to 2 positional arguments but 3 were given" o giua
        #    chuoi. Mot ban thay the sai chu ky la mot ban thay the kiem chinh
        #    no chu khong kiem san pham.
        if on_dispatch is not None:
            on_dispatch("ltt_llm")

        goi_vao = messages[-1].get("content")
        if isinstance(goi_vao, list):       # tin nhan da phuong thuc (VLM)
            goi_vao = " ".join(p.get("text", "") for p in goi_vao
                               if isinstance(p, dict))
        than = _doc_goi(str(goi_vao or ""))
        ma = _doan_thao_tac(str(goi_vao or ""), than)
        dem[ma] = dem.get(ma, 0) + 1
        return tra(_phan_hoi(ma, than, long_tieng, su_that))

    monkeypatch.setattr("platform_core.llm.dieu_phoi.goi", gia)
    # ⛔ `ai` phai van la nguoi goi that: khong dung toi no o day, chi giu tham
    #    chieu de mot lan doi ten lo ra ngay thay vi thanh mot cua chet.
    assert callable(ai.goi_tinh_tien)
    return dem


def _doc_goi(van: str) -> dict:
    dau, cuoi = van.find("{"), van.rfind("}")
    if dau < 0 or cuoi <= dau:
        return {}
    try:
        ra = json.loads(van[dau:cuoi + 1])
    except ValueError:
        return {}
    return ra if isinstance(ra, dict) else {}


def _doan_thao_tac(van: str, than: dict) -> str:
    """Nhan ra thao tac tu chinh goi tin — khong doi ai truyen ten vao.

    ⚠️ `dieu_phoi.goi` khong nhan `thao_tac`; no chi thay `messages`. Nen ban
       thay the phai doc ra tu noi dung, va no phai doc **theo hinh dang goi
       tin** chu khong theo mot chuoi tieng Viet trong prompt: mot cau chu trong
       prompt doi la mot ban thay the hong lang le.
    """
    from apps.auto_scan_video import ai

    # 🔴 **Nhan dien nay tung doc mot hinh dang goi tin KHONG TON TAI.**
    #    No cho mot khoa `canh` o goc — mot API doc-hang-loat ma
    #    `hieu_canh.loi_nhac_canh` chua bao gio gui: cua that hoi **mot canh mot
    #    lan**, va tin hieu do duoc di kem la `{bat, ket, dai_giay, so_khung,
    #    co_thoai}`. Ban thay the vi the khong bao gio nhan ra thao tac doc canh,
    #    va no khong lo ra vi khong nguoi goi nao ton tai de chay no.
    if "co_thoai" in than and "dai_giay" in than:
        return ai.DOC_CANH.ma
    if "the_loai" in than or "ho_so" in than:
        return ai.HO_SO_NOI_DUNG.ma
    if "khe" in than or "giay" in than:
        return ai.RUT_NGAN_CHO_VUA.ma
    if "kiem" in than or "cau_hoi" in than:
        return ai.QC_NGU_NGHIA.ma
    if "doan" in than:
        return ai.DICH_THUAT.ma
    return ai.DICH_THUAT.ma


def _phan_hoi(ma: str, than: dict, long_tieng, su_that) -> dict:
    """Phan hoi dung luoc do cua tung thao tac, BAM VAO dau vao.

    🔴 Mot ban thay the tra ve du lieu co dinh khong bao giờ phat hien duoc loi
       ghep sai ma doan — do la ly do `asv_media.cua_ai_gia` cung bam vao dau
       vao, va ly do do khong yeu di khi ta xuong sau mot tang.
    """
    from apps.auto_scan_video import ai

    if ma == ai.DOC_CANH.ma:
        # 🔑 **Bam vao dau vao, khong tra so co dinh.** Mot canh khong co loi
        #    thoai nao va ngan la ung vien bo; mot canh co thoai thi giu. Do la
        #    phan doan mot VLM se dua ra, va no la thu duy nhat lam bai nghiem
        #    thu noi duoc dieu gi ve `_quyet_dinh_mot_canh`: neu ban thay the
        #    luon tra "giu" thi phep kiem "cat duoc it nhat mot canh" xanh hay
        #    do khong con phu thuoc vao san pham nua.
        co_thoai = bool(than.get("co_thoai"))
        return {
            "loai": "hoi_thoai" if co_thoai else "chuyen_canh",
            "chu_the": ["nguoi noi"] if co_thoai else [],
            "hanh_dong": "dang noi" if co_thoai else "khong co hanh dong ro",
            "cam_xuc": "trung tinh",
            "quan_trong": 0.75 if co_thoai else 0.1,
            "de_xuat": "giu" if co_thoai else "bo",
            "do_tin": 0.9,
            "ly_do": ("canh co loi thoai" if co_thoai
                      else "canh khong co loi thoai nao va khong co hanh dong ro"),
            "canh_bao": [],
        }
    if ma == ai.HO_SO_NOI_DUNG.ma:
        return {"the_loai": "huong_dan", "nhip": "vua",
                "gioi": "nam", "vung": "bac", "phong_cach": "than_mat"}
    if ma == ai.RUT_NGAN_CHO_VUA.ma:
        chu = str(than.get("chu") or "")
        # Rut that: bo tu cuoi. Mot ban "rut ngan" tra ve y nguyen se lam bac
        # thang nan tuong model bo cuoc, va che mat loi neu vong lap hong.
        tu = chu.split()
        return {"doan": " ".join(tu[:-1]) if len(tu) > 3 else chu}
    if ma == ai.QC_NGU_NGHIA.ma:
        return {"dat": True, "ly_do": "ban thay the: khong danh gia noi dung"}

    # DICH_THUAT / CHUYEN_LOI_THOAI
    #
    # ⚠️ Cau NGUON nam o khoa `goc`, khong phai `chu` — `long_tieng.loi_nhac`
    #    gui `{ma, goc, ke_ben, thoi_luong_giay}`. Doc nham khoa cho ra chuoi
    #    rong, va `doc_chuyen` bo moi muc rong, nen ca lo bao "thieu loi thoai".
    return {"doan": {
        str(d["ma"]): {"chu": _dich_gia(str(d.get("goc") or d.get("chu") or ""),
                                        su_that),
                       "cam_xuc": long_tieng.CAM_XUC[0],
                       "kieu_noi": long_tieng.KIEU_NOI[0],
                       "nhan_manh": []}
        for d in (than.get("doan") or [])}}


#: Tu dien dich **co dinh**, de ban long tieng ra la tieng Viet that chu khong
#: phai mot chuoi bia. Chi phuc vu kich ban tren; cau la thi giu nguyen y.
TU_DIEN: dict[str, str] = {
    "l1": "Chào buổi sáng mọi người, và chào mừng đến với buổi hướng dẫn về "
          "bản địa hoá video.",
    "l2": "Cảm ơn anh. Anh có thể cho chúng tôi xem ví dụ đầu tiên hoạt động "
          "thế nào không?",
    "l3": "Tất nhiên rồi. Hệ thống đọc hình ảnh trước, rồi mới quyết định giữ "
          "lại những gì.",
    "l4": "Đó là một thứ tự tốt hơn nhiều so với dịch tất cả trước khi nhìn "
          "vào nó.",
}


def _dich_gia(chu: str, su_that) -> str:
    """Tra ban dich tieng Viet cua cau GAN NHAT trong kich ban.

    ⭐ Khop theo noi dung chu khong theo ma doan: ma doan do ASR sinh ra, con
       kich ban thi khong biet ASR se dat ten gi. Khop bang tu chung nhieu nhat.
    """
    if not su_that:
        return chu
    chuan = _chuan(chu)
    tot, diem = "", 0
    for l in su_that.loi:
        chung = len(set(_chuan(l.chu).split()) & set(chuan.split()))
        if chung > diem:
            tot, diem = l.ma, chung
    return TU_DIEN.get(tot, chu) if diem >= 2 else chu


def _chuan(chu: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", chu.lower()).strip()


def dat_cua_giong(monkeypatch, thu_muc: Path, *, toc_do: int = 0):
    """Thay may sinh tieng bang SAPI — song am THAT, do dai THAT.

    ⛔ Doc `chu` sau khi BO DAU: SAPI la giong en-US, va dau tieng Viet lam no
       doc tung ky tu. Bo dau cho ra mot chuoi am tiet gan hon, va — quan trong
       hon — mot **do dai** ti le voi do dai cau that, tuc bac thang nan cho vua
       nhan duoc tin hieu that de lam viec.
    """
    from apps.auto_scan_video import giong_noi

    thu_muc.mkdir(parents=True, exist_ok=True)
    dem = {"lan": 0}

    def doc(chu: str, **kw):
        dem["lan"] += 1
        tep = thu_muc / f"sapi_{dem['lan']:03d}.wav"
        noi(_bo_dau(str(chu)), tep, giong=GIONG_NU, toc_do=toc_do)
        return tep.read_bytes(), {"x-thay-the": "sapi"}

    monkeypatch.setattr(giong_noi, "san_sang", lambda: True)
    monkeypatch.setattr(giong_noi, "giai_giong", lambda db, **kw: (None, "bac"))
    monkeypatch.setattr(giong_noi, "doc_mot_doan", doc)
    return dem


# ══════════════════════════════════════════════════════════════════════════════
#  Do dac tren dau ra
# ══════════════════════════════════════════════════════════════════════════════

#: Khoa bi BO khoi moi tep bang chung truoc khi ghi ra kho.
KHOA_KHONG_CONG_BO = ("khoa_asset", "khoa", "van_tay_ban", "van_tay", "run_id")

_HEX32 = re.compile(r"^[0-9a-f]{32}")


def sach_de_cong_bo(gt):
    """Bo khoa luu tru va rut gon van tay truoc khi ghi mot tep bang chung.

    🔴 **Khong phai lam dep — la mot cong cua chinh kho nay.**
       `tests/test_44_release_build` quet bi mat tren TOAN BO noi dung phat hanh,
       va luat `bare_32_char_hex` bao dong tren moi chuoi 32 ky tu hex. Pha 22
       dinh lan dau (**44** bao dong tu mot tep bang chung), pha 24 dinh lai
       (**75**) — cung mot loi, o mot tep khac, vi ham lam sach nam trong tep
       test cua pha 22 chu khong nam o cho ai cung thay.

    ⭐ Nen no o day: MOT cho, va tep bang chung thu ba se khong phai hoc lai.

    ⛔ Va phep quet do dung: mot bao cao nghiem thu hay do dac khong can mot khoa
       luu tru nao ca. No can CON SO.
    """
    if isinstance(gt, dict):
        return {k: sach_de_cong_bo(v) for k, v in gt.items()
                if k not in KHOA_KHONG_CONG_BO}
    if isinstance(gt, list):
        return [sach_de_cong_bo(v) for v in gt]
    if isinstance(gt, str) and _HEX32.match(gt):
        return gt[:12] + "..." + gt[32:]
    return gt


def soi(duong: str) -> dict:
    """ffprobe -> dict. Dung cho phep kiem tren TEP RA, khong tren bao cao."""
    ff = shutil.which("ffprobe") or "ffprobe"
    ra = subprocess.run(
        [ff, "-v", "error", "-print_format", "json", "-show_format",
         "-show_streams", str(duong)], capture_output=True, text=True, check=True)
    return json.loads(ra.stdout)


def muc_theo_cua_so(duong: str, *, cua_so_s: float = 0.2) -> list[float]:
    """RMS (dBFS) cua tung cua so lien tiep. Giai ma that, tinh o day.

    ⭐ Tu tinh thay vi doc `silencedetect`: mot ban long tieng CO GIU NEN thi
       khong co giay nao im lang, nen `silencedetect` tra ve dung mot vung tu
       dau den cuoi va khong noi duoc gi. Do that tren tep ra cua lan chay:
       `mean_volume -15,9 dB`, va o MOI nguong tu -30 den -16 dB ket qua deu la
       mot vung duy nhat.

    ⇒ Cai phan biet loi thoai voi nen khong phai "co tieng hay khong" ma la
      **cao hon nen bao nhieu**. Do la mot phep do tuong doi, nen no can muc cua
      tung cua so chu khong can mot nguong tuyet doi.
    """
    binary = ffmpeg_bin()
    tan_so = 8000
    r = subprocess.run(
        [binary, "-hide_banner", "-loglevel", "error", "-i", str(duong),
         "-vn", "-ac", "1", "-ar", str(tan_so), "-f", "s16le", "-"],
        capture_output=True, check=True)
    mau = array.array("h")
    mau.frombytes(r.stdout[: len(r.stdout) // 2 * 2])
    n = max(1, int(tan_so * cua_so_s))
    ra: list[float] = []
    for i in range(0, len(mau) - n + 1, n):
        tong = 0
        for x in mau[i:i + n]:
            tong += x * x
        rms = math.sqrt(tong / n) / 32768.0
        ra.append(20.0 * math.log10(rms) if rms > 1e-9 else -120.0)
    return ra


def vung_co_tieng(duong: str, *, tren_nen_db: float = 2.0,
                  cua_so_s: float = 0.5,
                  ngan_nhat_s: float = 1.0) -> list[tuple[float, float]]:
    """Cac khoang mA MUC CAO HON NEN `tren_nen_db` dB. Do tren song am that.

    Muc nen lay bang **trung vi** cua tat ca cua so: mot ban long tieng noi
    khoang mot phan ba thoi luong, nen trung vi roi vao nen chu khong roi vao
    loi thoai.

    Tra ve `[(bat, ket), ...]` — thu duy nhat khong the bi mot bao cao noi doi.

    ⚠️ **+2 dB, khong phai +6.** Do that tren tep ra cua mot lan chay day du:
       nen nam o -18/-19 dB, loi thoai long o -13/-15 dB — tuc chi hon nen
       **khoang 4 dB**. Mot nguong +6 dB tim duoc **khong vung nao**, va bao cao
       se noi "khong co tieng long" ve mot tep nghe ro tung cau.

    ⭐ Ban than con so 4 dB la mot phat hien cua pha 22, khong phai mot tham so
       cua phep do: `am_master.NEN_GIAM_DB` ha nen **deu -6 dB tren ca bai** chu
       khong ha rieng luc co loi thoai, va chinh chu thich cua no ghi "CHUA DO
       tren ban that". Day la lan do dau tien.
    """
    muc = muc_theo_cua_so(duong, cua_so_s=cua_so_s)
    if not muc:
        return []
    nen = statistics.median(muc)
    nguong = nen + float(tren_nen_db)

    vung: list[tuple[float, float]] = []
    bat = None
    for i, m in enumerate(muc):
        if m >= nguong and bat is None:
            bat = i
        elif m < nguong and bat is not None:
            vung.append((bat, i))
            bat = None
    if bat is not None:
        vung.append((bat, len(muc)))

    toi_thieu = max(1, int(round(ngan_nhat_s / cua_so_s)))
    return [(round(b * cua_so_s, 3), round(k * cua_so_s, 3))
            for b, k in vung if (k - b) >= toi_thieu]


def phu_song_loi(vung, loi, *, bien_s: float = 1.5) -> list[dict]:
    """Moi cau nguon co mot vung CO TIENG nao trong tep ra trum len khong.

    ⭐ Day la phep doi chieu voi SU THAT DOC LAP: cau thoai o giay bao nhieu la
       thu ta biet truoc khi chay, khong phai thu doc lai tu bao cao.
    """
    ra = []
    for l in loi:
        b, k = float(l.bat) - bien_s, float(l.bat) + float(l.giay) + bien_s
        co = any(not (kk <= b or bb >= k) for bb, kk in vung)
        ra.append({"ma": l.ma, "bat": round(float(l.bat), 2),
                   "ket": round(float(l.bat) + float(l.giay), 2), "co_tieng": co})
    return ra

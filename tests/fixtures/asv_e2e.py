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
import shutil
import subprocess
import unicodedata
import wave
from contextlib import contextmanager
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


#: 🔑 Bat bang `LTT_ASV_GIONG_THAT=1` **va** co `LTT_VOICE_SIDECAR_TOKEN`.
#:
#: ⛔ Doi CA HAI, khong chi mot. Chi doi co cai thu nhat thi mot lan quen dat
#:    token cho ra mot luot chay hong giua chung voi `401`, sau khi da ton
#:    demucs va ASR; doi ca hai thi no lang le lui ve SAPI va **noi ra trong
#:    bao cao** rang no da lui.
BIEN_GIONG_THAT = "LTT_ASV_GIONG_THAT"

#: 🔑 Bat bang `LTT_ASV_MODEL_THAT=1` **va** co `LTT_DATABASE_URL`.
#:
#: ⛔ Doi ca `LTT_DATABASE_URL` chu khong doi mot bien khoa nao, va do la co y:
#:    khoa cua may B khong nam trong mot bien moi truong — no la mot DONG POOL
#:    trong CSDL, va `api_pool.chon_key` la thu duy nhat biet chon dong nao.
#:    Doi mot bien khoa o day se moi nguoi go tay mot khoa vao shell, tuc dung
#:    cai ma pool sinh ra de khong ai phai lam.
BIEN_MODEL_THAT = "LTT_ASV_MODEL_THAT"

#: Thu muc chu du an tha PHIM KHACH THAT vao.
#:
#: 🔴 **Day la chan cuoi cung cua G17, va la chan DUY NHAT may nay khong tu lam
#:    duoc.** Pha 28 liet ke ba thu thieu — model that, giong that, phim that.
#:    Hai thu dau dong lai bang phep do o pha 29. Thu thu ba thi khong: mot ban
#:    nguon tong hop co the giong that ve CAU TRUC (hai giong, bon canh, mot
#:    canh khong thoai) nhung no khong mang thu khien phim that kho — tieng on
#:    phong, giong chong len nhau, nhac nen that, cat canh khong sach.
#:
#: ⚠️ Va phim that KHONG di kem `SuThat`. Voi ban tong hop ta biet truoc cau
#:    thoai nam o giay nao; voi phim khach thi khong. Nen bai chay tren phim
#:    that chot IT hon — nhung thu no chot lai la thu khong the tu dung ra:
#:    duong chay co song sot khong, QC co dat khong, muc am co dung khong,
#:    preset cat co that su cat khong.
THU_MUC_PHIM_THAT = Path(__file__).resolve().parent / "asv_e2e_that"

#: Duoi tep duoc coi la phim nguon. Khong nhan `.wav`/`.mp3`: bai nay nghiem thu
#: ca duong hinh, mot tep chi co tieng se hong o RENDER voi mot thong bao khong
#: lien quan gi toi thu dang duoc do.
DUOI_PHIM = (".mp4", ".mov", ".mkv", ".webm", ".m4v")


def phim_khach_that() -> tuple[Path, ...]:
    """Cac tep phim chu du an da tha vao `asv_e2e_that/`, da sap xep.

    ⛔ Tra ve rong khi khong co tep nao — **khong nem**. Bai goi no phai
       `skip` kem mot ly do goi ten dung thu con thieu, va bao cao nghiem thu
       phai GHI viec vang mat do. Mot chan G17 con ho ma khong ai nhin thay
       trong bang chung thi chang khac gi no da dong.
    """
    if not THU_MUC_PHIM_THAT.is_dir():
        return ()
    return tuple(sorted(
        t for t in THU_MUC_PHIM_THAT.iterdir()
        if t.is_file() and t.suffix.lower() in DUOI_PHIM))


#: URL cua CSDL giu POOL KHOA. ⛔ Mot bien RIENG, khong dung `LTT_DATABASE_URL`:
#: bien do bi `moi_truong` ghi de bang SQLite dung-mot-lan **truoc khi** than
#: bai test chay, nen doc no o day se luon thay CSDL rong cua bo test.
BIEN_POOL_URL = "LTT_ASV_POOL_URL"


def dung_model_that() -> bool:
    """Luot chay nay co goi model tren may B THAT khong."""
    import os

    # 🔴 **Doc `BIEN_POOL_URL`, KHONG doc `LTT_DATABASE_URL`.**
    #
    #    Fixture `moi_truong` ghi de `LTT_DATABASE_URL` bang mot SQLite
    #    dung-mot-lan **truoc khi** than bai test chay. Mot phep kiem "co dat
    #    khong" tren bien do se noi CO trong khi cai duoc dat la CSDL RONG cua
    #    bo test — va hau qua la `api_pool.chon_key` nem `ThieuKeyError`, roi
    #    `dieu_phoi.goi` doc do thanh "provider nay khong phuc vu duoc" va nem
    #    `KhongCoProviderNao`: mot thong bao khong nhac gi toi CSDL, sau khi da
    #    ton demucs va ASR. Da dinh dung nhu vay mot lan.
    url = str(os.environ.get(BIEN_POOL_URL, "")).strip().lower()
    return (str(os.environ.get(BIEN_MODEL_THAT, "")).strip() == "1"
            and url.startswith(("postgres://", "postgresql://",
                                "postgresql+psycopg://",
                                "postgresql+psycopg2://")))


def nap_khoa_pool(db, *, provider: str = "ltt_llm") -> int:
    """Chep cac dong khoa `provider` tu POOL THAT sang CSDL cua bo test.

    Tra ve so dong da chep. `0` nghia la pool that khong co khoa nao dung duoc
    — mot ket qua co that, khong phai mot loi cua ham nay.

    ⛔ CHI DOC production. Mo mot engine RIENG, `SELECT`, dong. Khong ghi, khong
       xoa, khong dung `Base.metadata` len no.

    🔑 Chep nguyen `credential_enc` — mot Fernet token. Ma o day **khong bao gio
       nhin thay ban ro**; khoa giai nam trong `app.env` va chi
       `api_keys.lay_credential` dung toi no, dung luc goi.

    ⭐ Va chep sang CSDL RIENG cua bo test co mot loi phu dang ke: moi bo dem
       `last_used_at` / `error_count` / cooldown cua luot nghiem thu **khong**
       ghi vao dong khoa that. Tai cua bo test khong lam ban thong ke cua khoa
       production.
    """
    import os

    from sqlalchemy import create_engine, inspect as sa_inspect, select
    from sqlalchemy.orm import Session as SaSession

    from platform_core.models import ApiKey

    url = str(os.environ.get(BIEN_POOL_URL, "")).strip()
    if not url:
        return 0

    may = create_engine(url, pool_pre_ping=True)
    try:
        with SaSession(may) as phien:
            hang = list(phien.execute(
                select(ApiKey).where(ApiKey.provider == provider,
                                     ApiKey.enabled.is_(True),
                                     ApiKey.owner_user_id == "")).scalars())
            # ⚠️ Doc HET gia tri ra dict TRUOC khi dong phien: mot doi tuong ORM
            #    da tach khoi phien se nem `DetachedInstanceError` o lan doc
            #    thuoc tinh dau tien, va thong bao do khong nhac gi toi phien.
            cot = [c.key for c in sa_inspect(ApiKey).mapper.column_attrs]
            goi = [{k: getattr(k_row, k) for k in cot} for k_row in hang]
    finally:
        may.dispose()

    for g in goi:
        db.add(ApiKey(**g))
    db.flush()
    return len(goi)


def dung_giong_that() -> bool:
    """Luot chay nay co goi LTTStudioVoice THAT khong."""
    import os

    return (str(os.environ.get(BIEN_GIONG_THAT, "")).strip() == "1"
            and bool(str(os.environ.get("LTT_VOICE_SIDECAR_TOKEN", "")).strip()))


#: DANH MUC moi cua co the bi thay, kem ly do. ⚠️ Day KHONG con la "nhung cua da
#: bi thay trong luot nay" — cai do phu thuoc vao mot cong tac luc chay, va bao
#: cao phai ghi thu DA XAY RA chu khong ghi thu co the xay ra.
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

    if dung_model_that():
        # ⭐ Khong thay gi: `dieu_phoi.goi` se chon khoa that tu pool, mo luong
        #    toi may B, va tra ve thu model that noi. Day la thu dong G9 —
        #    "shot boundaries + samples -> ltt_llm_vision" chi that su duoc
        #    chung minh khi co mot luot goi that.
        #
        # ⚠️ Va no TIEU TOKEN THAT tren may B. Do la dien va thoi gian GPU cua
        #    chinh chu du an, khong phai tien tra cho ben thu ba — nhung no van
        #    la mot lan chay co gia, nen no phai duoc BAT ro rang chu khong roi
        #    vao mac dinh.
        dem["model_that"] = True
        return dem

    monkeypatch.setattr("platform_core.llm.dieu_phoi.goi", gia)
    # ⛔ `ai` phai van la nguoi goi that: khong dung toi no o day, chi giu tham
    #    chieu de mot lan doi ten lo ra ngay thay vi thanh mot cua chet.
    assert callable(ai.goi_tinh_tien)
    dem["da_thay"] = CUA_MODEL
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
    # ⭐ **Hinh dang goi tin cua `HO_SO_NOI_DUNG`, khong phai mot chu trong
    #    prompt.** `hieu_canh.loi_nhac_ho_so` gui kem khoi so lieu TAT DINH cua
    #    `ho_so_noi_dung.bang_chung` — `f0_trung_vi` + `ky_tu_moi_giay` la hai
    #    khoa khong thao tac nao khac co. Truoc 23/09 nhanh nay chi nhan ra
    #    `the_loai`/`ho_so` (hai khoa cua PHAN HOI, khong phai cua YEU CAU), nen
    #    mot loi nhac ho so that se roi xuong `DICH_THUAT` va tra ve mot hinh
    #    dang `doc_ho_so` khong doc duoc.
    if "f0_trung_vi" in than or "ky_tu_moi_giay" in than:
        return ai.HO_SO_NOI_DUNG.ma
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
        # 🔴 **Hai loi trong ba dong cu, va ca hai deu im lang.**
        #    (a) ba mat nam PHANG o goc, nhung `hieu_canh.doc_ho_so` doc chung
        #        trong `dac_diem_giong` ⇒ ho so ra rong ⇒ `AUTO_MATCH` van
        #        `CHUA_RANG`, tuc ban thay the "tra loi" ma khong tra loi gi;
        #    (b) `phong_cach: "than_mat"` khong co trong catalog
        #        (`giong_mau.NHAN_PHONG_CACH`) ⇒ `giong_mau.loc` tra ve rong.
        #    Ca hai khong lo ra vi thao tac nay chua tung co nguoi goi.
        #
        # ⭐ `vung` de RONG: mot phim tieng Trung khong noi gi ve giong vung
        #    mien tieng Viet, nen mot ban thay the khai no la dang bia ra mot
        #    rang buoc ma duong that se phai noi long di.
        from apps.ltt_voice.giong_mau import UU_TIEN_PHONG_CACH

        return {"the_loai": "huong_dan", "nhip": "vua",
                "giong_dieu": "than mat", "khan_gia": "nguoi hoc",
                "tom_tat": "mot buoi huong dan ngan",
                "dac_diem_giong": {
                    "gioi": "nam", "vung": "",
                    "phong_cach": min(UU_TIEN_PHONG_CACH,
                                      key=UU_TIEN_PHONG_CACH.get)}}
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
    """Tra ban dich tieng Viet cua cau GAN NHAT trong kich ban, **theo ty le**.

    ⭐ Khop theo noi dung chu khong theo ma doan: ma doan do ASR sinh ra, con
       kich ban thi khong biet ASR se dat ten gi. Khop bang tu chung nhieu nhat.

    🔴 **Va phan tra ve phai CAN DOI VE DO DAI voi manh nguon.**

       Ban dau ham nay tra ve NGUYEN cau tieng Viet cho bat ky manh nao khop tu
       hai tu tro len. ASR tach ban nguon thanh 6 doan, gom "Thank you." va
       "Of course." — moi cai duoi mot giay — va ca hai nhan ve mot cau hai
       menh de. Voi giong SAPI dieu do vo hai: no doc chuoi da bo dau rat nhanh.
       Voi giong THAT thi mot khe 0,6 giay nhan ~6 giay tieng, va `timing_align`
       chet dung nhu no nen chet: "he so co gian 11.304 ngoai khoang mot lan
       atempo".

    ⇒ Cat ban dich theo dung ty le so tu cua manh nguon tren cau nguon. Mot
      trinh dich that dich "Thank you." thanh "Cam on.", khong thanh mot cau
      hai menh de — va do dai moi la thu bac thang nan cho vua dang do.
    """
    if not su_that:
        return chu
    chuan = _chuan(chu)
    tot, diem, cau_nguon = "", 0, ""
    for l in su_that.loi:
        chung = len(set(_chuan(l.chu).split()) & set(chuan.split()))
        if chung > diem:
            tot, diem, cau_nguon = l.ma, chung, l.chu
    if diem < 2:
        return chu
    dich = TU_DIEN.get(tot, chu)

    # Ty le so tu: manh nguon / cau nguon. Kep vao (0, 1].
    tu_manh = len(chuan.split()) or 1
    tu_cau = len(_chuan(cau_nguon).split()) or 1
    ty_le = min(1.0, tu_manh / tu_cau)
    if ty_le >= 0.85:
        return dich

    tu_dich = dich.split()
    lay = max(2, round(len(tu_dich) * ty_le))
    ra = " ".join(tu_dich[:lay]).rstrip(",;:")
    return ra if ra.endswith(".") else ra + "."


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

    if dung_giong_that():
        # ⭐ Khong thay gi ca: `giong_noi.san_sang` se hoi sidecar that,
        #    `giai_giong` doc kho giong that, va `doc_mot_doan` sinh tieng Viet
        #    that. Day la thu dong duoc nua bang chung ngoai cua G11/G12/G17 —
        #    SAPI la giong en-US va khong bao gio noi duoc gi ve chat luong
        #    long tieng tieng Viet.
        dem["giong_that"] = True
        return dem

    monkeypatch.setattr(giong_noi, "san_sang", lambda: True)
    monkeypatch.setattr(giong_noi, "giai_giong", lambda db, **kw: (None, "bac"))
    monkeypatch.setattr(giong_noi, "doc_mot_doan", doc)
    dem["da_thay"] = CUA_GIONG
    return dem


#: Ba cua ma `dat_cua_giong` thay khi chay o che do SAPI.
CUA_GIONG = ("apps.auto_scan_video.giong_noi.san_sang",
             "apps.auto_scan_video.giong_noi.giai_giong",
             "apps.auto_scan_video.giong_noi.doc_mot_doan")

#: Cua ma `dat_cua_model` thay.
CUA_MODEL = ("platform_core.llm.dieu_phoi.goi",)


def cua_da_thay(*dem: dict) -> tuple[str, ...]:
    """Ten nhung cua THUC SU bi thay trong luot chay nay, da sap xep.

    ⭐ Doc tu chinh cac bo dem ma `dat_cua_*` tra ve, khong tu mot danh sach
       doan truoc. Mot ban khai doan truoc se dung cho toi ngay ai do them mot
       cong tac thu ba — va luc do bao cao se noi sai ve chinh luot chay dang
       ghi, im lang.
    """
    ra: set = set()
    for d in dem:
        ra |= set((d or {}).get("da_thay") or ())
    return tuple(sorted(ra))


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
    # R-06: `text=True` KHONG khai `encoding` -> tren Windows Python doan
    # bang locale (`cp1252` may tieng Viet), va no VO ngay khi `-show_format`
    # tra ve ten tep/tag co ky tu tieng Trung that (video nghiem thu). ffprobe
    # luon ghi JSON UTF-8 bat ke locale may, nen ep `encoding="utf-8"` la
    # dung, khong phai chon tam.
    ra = subprocess.run(
        [ff, "-v", "error", "-print_format", "json", "-show_format",
         "-show_streams", str(duong)], capture_output=True, text=True,
        encoding="utf-8", check=True)
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


def _phan_vi(gia_tri: list, p: float) -> float:
    """Phan vi thu `p` (0..1) cua mot day so. Khong noi suy — lay mau that.

    ⛔ Khong dung `statistics.quantiles`: no noi suy giua hai mau, va voi 54 mau
       thi mot gia tri noi suy khong ung voi cua so nao co that. O day ta muon
       "muc cua mot cua so yen", khong muon mot con so trung binh giua hai cua.
    """
    q = sorted(gia_tri)
    return q[max(0, min(len(q) - 1, int(p * (len(q) - 1))))]


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

    🔴 **NEN lay o PHAN VI 20, khong lay o TRUNG VI — va day la mot dinh chinh
       cua pha 27, co so do di kem.**

       Ban cu lay trung vi, kem mot tien de viet thang ra: *"mot ban long tieng
       noi khoang mot phan ba thoi luong, nen trung vi roi vao nen"*. Tien de do
       phu thuoc vao **nguon co bao nhieu doan im lang** — mot thu ban than phep
       do khong kiem soat.

       Pha 27 noi VLM vao mach, `smart_localize` lan dau thuc su cat mot canh
       khong loi thoai, va tien de vo ngay. Do duoc tren cung mot lan chay, hai
       ban ra cua hai preset:

           preserve  n=64  p20 -17,73  p50 -17,07  ->  trung vi: 4 vung
           cat       n=54  p20 -17,80  p50 -16,48  ->  trung vi: 1 vung

       Bo 5 giay duoi cung (phan im nhat) day trung vi len **0,6 dB**, va chi
       tung do da lam bao cao noi "khong co doan nao noi len tren nen" ve mot
       tep co cau truc tieng **giong het** ban kia — 44 cua so dau cua hai chuoi
       muc TRUNG KHIT nhau, chung chi tach o dung cho bi cat.

       Voi nen = p20 thi ca hai deu ra **6 vung**, tuc phep do noi cung mot dieu
       ve hai tep giong nhau.

    ⭐ Va p20 la dinh nghia dung hon cua "nen": nen la phan YEN cua phan bo, nen
       lay no o phia duoi phan bo chu khong lay o giua. Trung vi chi dung khi ta
       biet truoc rang qua nua thoi luong la nen — mot dieu ta khong biet.
    """
    muc = muc_theo_cua_so(duong, cua_so_s=cua_so_s)
    if not muc:
        return []
    nen = _phan_vi(muc, 0.20)
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


# ══════════════════════════════════════════════════════════════════════════════
#  CARD GPU, va KHOA MAY — hai thu khuon nay TUNG do sai
# ══════════════════════════════════════════════════════════════════════════════
#
# 🔴 **Truoc 24/09 khuon nghiem thu do CHINH NO, khong do san pham.**
#
#    `test_448._chay_hang_doi` dong vai worker that, nhung no dung
#    `JobContext(job.id)` — KHONG co `gpu_uuid`. Worker that lam khac
#    (`platform_core/job_runner.py:299`):
#
#        ctx = JobContext(job_id, gpu_uuid=(lease.gpu_uuid if lease else ""))
#
#    Card den tu `gpu_lease`. Thieu no thi `ctx.has_gpu` la False va
#    `ctx.gpu_env()` khong ghim `CUDA_VISIBLE_DEVICES`, nen demucs va ASR chay
#    tren **CPU** — va moi con so giay trong bao cao la so cua KHUON, khong phai
#    cua san pham. Do 23/09 (lan `toc-do-gpu`): demucs GPU 42,2 s vs CPU 72,0 s
#    tren cung phim. Mot bao cao hieu nang dung de quyet dinh, nen sai 30 s moi
#    pha khong phai mot sai so — no la mot cau tra loi khac.
#
# 🔴 **Va khoa `cpu_nhieu` boc CA luot chay, ke ca luc CHO.**
#
#    NEN_V3 do `voice_synthesis` 937 s tren 1191 s, va gan het so do la mot lan
#    goi HTTP sang sidecar hoac may B. Giu `cpu_nhieu` suot 20 phut do lam ca may
#    doi mot luot dang **cho mang**. Su co 23/09: mot lan giu 51 phut o CPU
#    6-8 %, sau lung 6 luot.
#
#    ⇒ Luat chu du an chot 23/09: khoa boc **dung lenh TINH**, khong boc viec
#      DOI. Nen o day `cpu_nhieu` boc **tung job nang** va nha ngay khi job xong.
#
# ⚠️ `may_tao_tieng` thi NGUOC LAI, va tron hai loai khoa lam mot la mot loi
#    khac. `cpu_nhieu` chia **suc tinh** ⇒ giu luc cho la phi may.
#    `may_tao_tieng` chia **mot tai nguyen doc quyen** (mot dich vu NSSM duy
#    nhat o :8120) ⇒ mot phien chen vao giua lam **hong chinh phep do** (so
#    LUFS/MOS mang tieng cua luot khac). Nen no phai duoc giu SUOT pha giong.

#: Cac `job_type` thuc su dot suc tinh cua may nay. Khoa `cpu_nhieu` chi boc
#: chung. Nguon: ban khai cua `apps/asv_gpu/manifest.py` va
#: `apps/asv_media/manifest.py` — khong doan theo ten.
#:
#: ⛔ `*.voice_synthesis` KHONG o day: no la mot chuoi lan goi HTTP sang sidecar
#:    :8120 va tien trinh worker chi ngoi doi. Xem `may_tao_tieng` duoi.
PHA_NANG_CPU = frozenset({
    "asv_gpu.audio_prepare",        # demucs htdemucs
    "asv_gpu.transcribe",           # faster-whisper / WhisperX large-v3
    "asv_gpu.qc_do_luong",          # ASR lan cuoi + SQUIM_OBJECTIVE
    "asv_media.compose",            # ffmpeg tron
    "asv_media.render",             # ffmpeg ma hoa lai
    "asv_media.qc",                 # giai ma ca tep + VMAF
})

#: Cac `job_type` dung MAY SINH TIENG. Tai nguyen doc quyen ⇒ giu suot pha.
PHA_MAY_TAO_TIENG = frozenset({
    "asv_voice.voice_synthesis",
    "asv_media.voice_synthesis",
})

#: Cac `job_type` la mot lan CHO (mang, may B, sidecar). ⛔ Khong khoa `cpu_nhieu`.
#: Giu o day de mot phep kiem doi chieu duoc, chu khong de ma doc no.
PHA_CHO = frozenset({
    "auto_scan_video.advance",
    "auto_scan_video.edit_plan",
    "auto_scan_video.content_process",
    "auto_scan_video.qc_ai",
    "asv_media.content_process",
    "asv_media.timing_align",
    "asv_voice.voice_synthesis",
    "asv_media.voice_synthesis",
})


class KhongCoCardError(RuntimeError):
    """May khong co GPU nao — mot luot nghiem thu PHAI dung, khong chay CPU.

    🔑 Vi sao dung chu khong chay tiep: mot luot chay CPU van ra tep dung duoc,
       nen no **xanh**, va bao cao cua no mang nhung con so giay khong ai doi
       chieu duoc voi san pham. Mot phep do sai ve phia "trong giong ket qua
       that" te hon mot phep do khong chay.
    """


def doi_hoi_card() -> list:
    """Danh sach GPU cua may. Nem `KhongCoCardError` neu khong co cai nao.

    ⚠️ **`torch.cuda.is_available()` KHONG tra loi duoc cau hoi nay cho ASR.**
       CTranslate2 (ruot cua faster-whisper) mang CUDA/cuDNN RIENG, khong dung
       cai cua torch. Nen `cuda True` + card ranh van co the cho mot lan ASR tut
       ve CPU trong im lang. Ham nay chi tra loi "may co card khong"; con
       "ASR co DUNG card khong" phai doc tu chinh lan chay (xem `khai_card`).
    """
    from platform_core import gpu as gpu_mod
    gpus = list(gpu_mod.list_gpus())
    if not gpus:
        raise KhongCoCardError(
            "May khong co GPU nao. Mot luot nghiem thu tren CPU se ra tep dung "
            "duoc nhung moi con so giay se la so cua khuon, khong phai cua san "
            "pham (demucs CPU 72,0 s vs GPU 42,2 s, do 23/09). Dung o day.")
    return gpus


@contextmanager
def card_cho_job(job_type: str, job_id: str, *, worker_id: str = "w-nghiem-thu"):
    """Giu card cho MOT job dung nhu worker that. Yields `(gpu_uuid, het_gpu)`.

    🔑 Goi **chinh** `job_runner._vram_can` va `job_runner._giu_gpu`, khong go
       lai phep chon. Mot ban sao se lech o mot nhanh nao do, va nhanh lech se
       la nhanh it duoc chay nhat (cung bai hoc `_provider_failure_kind` da ghi
       trong `test_448._chay_hang_doi`).

    `het_gpu=True` = loai job nay CAN card, may CO card, nhung dang bi giu het.
    Worker that tra job ve hang doi trong truong hop do; nguoi goi phai lam y het.

    ⭐ `_giu_gpu` tu nha lease o `finally`, ke ca khi handler nem — nen khong co
       duong nao ra khoi khoi `with` nay ma con giu card.
    """
    from platform_core.job_runner import _giu_gpu, _vram_can

    need_mb = _vram_can(job_type)
    with _giu_gpu(worker_id, job_id, job_type, need_mb) as (lease, het_gpu):
        yield ((lease.gpu_uuid if lease is not None else ""), bool(het_gpu))


def khai_card(nhat_ky: list[dict]) -> dict:
    """Card CO duoc cap khong, tren tung pha — de bao cao khong noi doi.

    ⛔ Ham nay KHONG suy ra "ASR chay tren GPU". No chi khai: pha nay doi card
       (`can_card`), va pha nay **duoc** card (`gpu_uuid` khac rong). Chenh lech
       giua hai cot la cho nguoi doc phai nghi ngo con so giay.
    """
    can = [d for d in nhat_ky if d.get("can_card")]
    doi = sorted({str(d["job_type"]) for d in can})
    duoc = sorted({str(d["job_type"]) for d in can if d.get("gpu_uuid")})
    thieu = sorted({str(d["job_type"]) for d in can if not d.get("gpu_uuid")})
    return {
        "pha_doi_card": doi,
        "pha_duoc_card": duoc,
        "pha_doi_card_ma_KHONG_duoc": thieu,
        # 🔑 **MOT PHAN QUYET, khong de nguoi doc tu tru hai danh sach.**
        #
        #    Bai hoc cua chinh lan nay (K-01): bao cao `NEN_V3` co day du con so
        #    giay, va khong ai nhan ra chung la so CPU — vi khong dong nao noi
        #    ra. Mot bao cao bat nguoi doc tu so hai cot roi tu ket luan la mot
        #    bao cao se duoc doc sai, va se duoc doc sai theo huong co loi.
        #
        # ⚠️ `thieu` khac rong = co pha doi card ma khong duoc ⇒ pha do chay CPU
        #    ⇒ con so giay cua NO do KHUON. Khong phai ca luot: cac pha khac van
        #    do that, nen cau khai phai chi dung pha nao.
        "do_khuon_khong_do_san_pham": bool(thieu),
        "cau_khai": (
            "Moi pha doi card deu duoc card — so giay do SAN PHAM."
            if doi and not thieu else
            "KHONG pha nao doi card — luot nay khong noi gi ve hieu nang GPU."
            if not doi else
            "⛔ " + ", ".join(thieu) + " DOI card ma KHONG duoc ⇒ chung chay "
            "CPU, va con so giay cua chung la so cua KHUON, khong phai cua san "
            "pham (demucs CPU 72,0 s vs GPU 42,2 s, do 23/09)."),
        # ⚠️ Va mot dieu ham nay KHONG biet, nen no phai noi ra chu khong im:
        "chua_tra_loi": (
            "Card duoc CAP khong tuong duong ASR DUNG card: CTranslate2 (ruot "
            "cua faster-whisper) mang CUDA/cuDNN rieng, khong dung cua torch. "
            "Mot lan ASR tut ve CPU tren mot card da duoc cap van khop moi con "
            "so o day."),
    }


class KhoaTheoPha:
    """Khoa may boc **tung pha tinh**, khong boc ca luot chay.

    Dung nhu mot `with` ngoai cung cua luot, roi goi `quanh_job` cho tung job::

        with fx.KhoaTheoPha("asvf-nghiem-thu-v2") as khoa:
            for job in ...:
                with khoa.quanh_job(job.job_type):
                    handler(...)

    Ba hanh vi, ba ly do khac nhau:

    ``cpu_nhieu``      giu quanh MOT job nang, nha ngay khi job xong.
                       (chia suc tinh ⇒ giu luc cho la phi may)
    ``may_tao_tieng``  giu tu job giong DAU TIEN den het luot.
                       (tai nguyen doc quyen ⇒ ai chen vao lam hong phep do)

    ⚠️ **Vi sao `may_tao_tieng` giu tiep qua `qc_ai`, `qc`, `render` — chu khong
       nha ngay khi `voice_synthesis` bao `succeeded`.** Thoat nhin day giong K-02
       (giu khoa luc khong dung), va no KHAC o mot diem quyet dinh: phan quyet cua
       `qc_ai`/`qc_do_luong` co the day lan chay **NGUOC ve** `voice_synthesis`
       (`sua_chua`: `doc_sai` -> doc lai doan, `dich_sai` -> dich lai roi doc lai;
       xem M-01, M-02, M-07). Tuc trong suot cac pha QC, may sinh tieng la thu
       **co the can lai bat cu luc nao**.
    ⇒ Nha ra roi gianh lai la mo dung cai cua M-07 canh bao: mot phien khac chen
      vao giua, va vong sua "doc lai" do mot may da mang tieng cua luot khac.
    ⛔ Khac biet that giua hai khoa: `cpu_nhieu` nha ra roi gianh lai chi **cham
       hon**; `may_tao_tieng` nha ra roi gianh lai co the **sai ket qua**.
    con lai            KHONG khoa gi. `advance`, `edit_plan`, `content_process`,
                       `qc_ai` la nhung lan goi mang — chung chay NGOAI khoa.
    """

    def __init__(self, phien: str, *, bat: bool = True, so_loi: int = 0,
                 giu_suot: tuple = ()):
        #: Khoa giu SUOT ca luot, giu ngay tu `__enter__`.
        #:
        #: ⚠️ `postgres_test` thuoc nhom nay, va **khong** duoc chuyen sang giu
        #:    theo pha: khuon nghiem thu goi `Base.metadata.drop_all()` tren CSDL
        #:    scratch DUNG CHUNG (`test_423.moi_truong`). Mot phien chen vao giua
        #:    khong lam luot nay cham — no lam luot kia thay `relation "jobs" does
        #:    not exist` (su co 17/09, `tests/test_1500`). Do la khoa tai nguyen
        #:    DOC QUYEN, khong phai khoa suc tinh.
        #:
        #: ⛔ Va no phai duoc giu TRUOC khi `moi_truong` chay, tuc truoc than bai
        #:    test — xem `test_3001` dat bo canh khoa DAU danh sach tham so.
        self.giu_suot = tuple(giu_suot)
        self.phien = phien
        self.bat = bat
        self.so_loi = so_loi
        #: Ten tai nguyen -> `CuaSoYen` dang giu (chi cho khoa giu DAI).
        self._giu_dai: dict = {}
        #: Nhat ky de mot phep kiem doi chieu duoc: (job_type, tai_nguyen).
        self.da_khoa: list = []

    def _cua_so(self, tai_nguyen: str, lenh: str):
        import sys as _sys
        goc = str(Path(__file__).resolve().parents[2])
        if goc not in _sys.path:
            _sys.path.insert(0, goc)
        from tools.cua_so_yen import CuaSoYen
        return CuaSoYen(self.phien, lenh, bat=self.bat, so_loi=self.so_loi,
                        tai_nguyen=(tai_nguyen,))

    @contextmanager
    def quanh_job(self, job_type: str):
        """Giu dung nhung khoa job nay can, va chi trong thoi gian no chay."""
        can = ()
        if job_type in PHA_MAY_TAO_TIENG:
            can += ("may_tao_tieng",)
            # Giu DAI: mo mot lan, khong dong giua pha giong.
            if "may_tao_tieng" not in self._giu_dai:
                cs = self._cua_so("may_tao_tieng", "nghiem thu ASV - pha giong")
                cs.__enter__()
                self._giu_dai["may_tao_tieng"] = cs
        if job_type in PHA_NANG_CPU:
            can += ("cpu_nhieu",)
        self.da_khoa.append((job_type, tuple(sorted(can))))
        if "cpu_nhieu" in can:
            # Giu NGAN: mo va dong quanh dung mot job tinh.
            with self._cua_so("cpu_nhieu", f"nghiem thu ASV - {job_type}"):
                yield tuple(sorted(can))
        else:
            yield tuple(sorted(can))

    def __enter__(self):
        for tn in sorted(self.giu_suot):
            cs = self._cua_so(tn, f"nghiem thu ASV - ca luot ({tn})")
            cs.__enter__()
            self._giu_dai[tn] = cs
        return self

    def __exit__(self, *_exc) -> None:
        for cs in list(self._giu_dai.values()):
            try:
                cs.__exit__(None, None, None)
            except Exception:               # noqa: BLE001 - nha khoa khong duoc nuot
                pass
        self._giu_dai.clear()


#: Venv cua WORKER — noi `torch` co CUDA. ⛔ KHONG phai trinh thong dich chay test.
VENV_WORKER = Path(r"C:\LTTPlatform\venv\Scripts\python.exe")


def ghim_python_co_card(monkeypatch) -> dict:
    """Ep tien trinh con demucs chay bang venv WORKER. Tra ve loi khai.

    🔴 **Do that 24/09, luot B tren phim khach that.** Nen tang cap card DUNG
       (`gpu_lease` giu that, `JobContext.gpu_uuid` khac rong) va tien trinh con
       van nem `ThieuCard` — vi bo nghiem thu chay bang **trinh thong dich test**,
       va o do `torch` la `2.11.0+cpu`, `cuda False`. Venv worker
       (`C:/LTTPlatform/venv`) la `2.11.0+cu128`, `cuda True`.

    ⛔ Va khong co cach nao dung MOT trinh thong dich cho ca hai:
       `setup/nghiem_thu_asv.ps1` giai thich ro venv san pham **co y** khong cai
       pytest. pytest can trinh thong dich nay, demucs can trinh thong dich kia.

    ⚠️ **Bai hoc hai chieu, va chieu thu hai moi la cai bat ngo.** Brief cua lan
       canh bao *"`torch.cuda.is_available()` True KHONG chung minh
       faster-whisper dung duoc card"*. Do that o day la **anh guong cua no**:
       tren trinh thong dich test `torch.cuda` la **False** trong khi
       `ctranslate2.get_cuda_device_count()` tra **1**. Hai chong CUDA doc lap,
       va mot bien bool khong noi thay ca hai duoc — theo ca hai huong.

    ⇒ Nen ham nay chi ghim duong demucs, va **khai ra** rang duong ASR la mot cau
      hoi KHAC, phai doc tu chinh lan chay.
    """
    from apps.auto_scan_video import tach_tieng

    co = VENV_WORKER.is_file()
    if co:
        monkeypatch.setenv(tach_tieng.BIEN_PYTHON_TACH, str(VENV_WORKER))
    return {
        "python_tach": str(VENV_WORKER) if co else "(khong thay venv worker)",
        "da_ghim": co,
        "vi_sao": ("tien trinh con demucs phai chay bang venv co torch CUDA; "
                   "trinh thong dich chay pytest la ban CPU-only"),
        "chua_tra_loi": ("Duong ASR (faster-whisper/CTranslate2) KHONG di qua "
                         "bien nay. CT2 mang CUDA rieng — do 24/09: tren trinh "
                         "thong dich test `torch.cuda` False ma "
                         "`ctranslate2.get_cuda_device_count()` = 1. Phai doc "
                         "tu chinh lan chay, khong suy ra tu day."),
    }

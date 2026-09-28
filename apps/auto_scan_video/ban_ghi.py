"""Hop dong BAN GHI chinh tac (TranscriptDocument) cua Auto Scan Video.

## Vi sao can mot hop dong rieng thay vi truyen thang ket qua cua engine

`apps/autosubvideo/transcription.py:162 transcribe_file` tra ve mot tu dien cua
**engine**: `{segments, language, engine, alignment_status, fallback_reason}`.
Do la hop dong cua mot cong cu, va no doi khi cong cu doi — whisperx va
faster-whisper da tra ve hai hinh dang hoi khac nhau ngay hom nay.

Bon giai doan ha nguon (CONTENT, VOICE, TIMING, COMPOSE) khong duoc phu thuoc
vao hinh dang do. Chung phu thuoc vao hop dong o day (O11).

## Ma doan (segment id) — vi sao la vi tri, va vi sao the la du

Ma co dang `seg_0001`. No **khong** bam theo noi dung, va do la mot lua chon
co y:

  * Ban ghi la mot artifact NGUYEN KHOI. No duoc tinh lai tron ven hoac khong
    tinh lai gi ca — van tay (§ `van_tay_ban_ghi`) quyet dinh dieu do.
  * Neu ban ghi duoc tinh lai va phep chia doan doi, thi moi thu ha nguon **phai**
    tinh lai theo — va no se, vi van tay cua ban ghi nam trong van tay cua chung
    (`thi_hanh._gom_dau_vao`). Mot ma bam theo noi dung se cho hai doan giong
    nhau o hai cho cung mot ma, va do la mot loi lineage tram hon.

⇒ Ma la **dinh danh trong mot ban ghi**, khong phai dinh danh toan cuc. Muc 4
  cua Prompt 10 doi "stable segment IDs": chung on dinh trong pham vi ma chung
  co nghia, va vuot ra ngoai pham vi do thi khong ma nao on dinh duoc.

## Ban thoi gian la BAT BUOC

Mot doan khong co `start`/`end` hop le se lam TIMING_ALIGN khong con gi de bam
vao, va loi se hien ra o cuoi day chuyen chu khong o day. Nen ban ghi bi **tu
choi** ngay khi dung, thay vi duoc luu roi lam vo mot giai doan xa hon.
"""
from __future__ import annotations

import hashlib
import json

from platform_core.i18n import _ as _t

#: Phien ban HINH DANG cua ban ghi. Doi khi cau truc doi — di vao van tay, nen
#: mot lan doi lam moi ban ghi cu vo hieu thay vi bi doc bang luat moi.
SCHEMA_BAN_GHI = 1

# ⛔ Bang chung nguoi noi (pha 07: `phan_vai`/`nguoi_noi`) DA RUT 22/09
#    (asv-final): san pham la MOT giong thuyet minh, khong bo phan nao doc
#    nhan nguoi noi — phan vai chi ton GPU. Ban ghi cu con truong `phan_vai`
#    van hop le: `kiem()` khong doc no.

#: Sai so cho phep khi doi chieu moc thoi gian cua tu voi cua doan. Engine lam
#: tron o cho khac nhau, nen mot phep so bang tuyet doi se do vi lam tron.
SAI_SO_S = 0.05


class BanGhiError(ValueError):
    """Ban ghi khong dat hop dong."""


def _lam_sach(van_ban: object) -> str:
    """⛔ Nhan `object`, ⛔ khong phai `str`: than ham VON da nhan `None` va moi
    thu khac (`str(van_ban or "")`), va nguoi goi truyen `tu.get(khoa)` — mot
    gia tri JSON co the vang mat. Chu ky hep hon than ham la mot loi khai bao."""
    return " ".join(str(van_ban or "").split())


#: Ten khoa chua CHU cua mot tu, theo tung engine. ⛔ **Ca hai deu hop le** —
#: day khong phai mot engine viet sai chinh ta, ma hai hop dong that.
#:
#: 🔴 **Su co 24/09 (N-17, he qua thu hai).** Ham nay tung chi doc `"text"`:
#:
#:      whisperx/alignment.py   word_segment = {"word": word_text}      -> "word"
#:      transcription.py:239    {"start":…, "end":…, "text":…}          -> "text"
#:
#:    ⇒ Tren nhanh MAC DINH (`whisperx`, `canh_chinh="aligned"`) moi tu deu cho
#:    `chu = ""` roi bi `continue` **im lang**: `so_tu` = **0**, trong khi nhanh
#:    LUI cho **1031**. Ta tra tien cho `load_align_model` + `align` — buoc dat
#:    nhat cua nhanh — roi **nem ket qua di**, va nhanh `aligned` cho ra dung thu
#:    `unaligned` cho, chi cham hon.
#:
#: ⛔ Khong phep kiem nao do, vi bo sot **khong lam sai ket qua** — no chi lam mat
#:    kha nang PHAN BIET. Do la ly do `kiem()` nay co bat bien `canh_chinh`.
KHOA_CHU_TU = ("text", "word")


def _chu_tu(tu: dict) -> str:
    """Chu cua mot tu, doc duoc CA HAI hinh dang engine. ⛔ Dung chon mot ben."""
    for khoa in KHOA_CHU_TU:
        chu = _lam_sach(tu.get(khoa))
        if chu:
            return chu
    return ""




def chuan_hoa(thoi: dict, *, thoi_luong_nguon: float = 0.0,
              nguon_loi: str = "asr", dinh_tuyen: dict | None = None) -> dict:
    """Ket qua tho cua engine -> ban ghi chinh tac. Nem `BanGhiError` neu khong dat.

    Bo doan RONG thay vi giu: mot doan khong co chu la mot doan khong co gi de
    dich va khong co gi de doc, nhung no VAN chiem mot khe thoi gian — va TIMING
    se chen mot khoang lang vao dung cho do.
    """
    doan_tho = list((thoi or {}).get("segments") or [])
    ra: list[dict] = []
    # ⭐ Dem tung LY DO bo, khong chi dem tong: ba nguyen nhan duoi day doi hoi ba
    #    hanh dong khac han nhau (sua khoa · sua model can chinh · bao loi engine).
    bo_khong_chu = bo_thieu_moc = bo_moc_nguoc = 0

    for tho in doan_tho:
        van_ban = _lam_sach(tho.get("text"))
        if not van_ban:
            continue
        try:
            bat, ket = float(tho.get("start")), float(tho.get("end"))
        except (TypeError, ValueError) as exc:
            raise BanGhiError(_t('Bản ghi có đoạn thiếu mốc thời gian.')) from exc
        if ket <= bat:
            raise BanGhiError(_t('Bản ghi có đoạn với mốc thời gian không hợp lệ.'))

        tu = []
        for t in (tho.get("words") or []):
            chu = _chu_tu(t)
            if not chu:
                bo_khong_chu += 1
                continue
            try:
                tb, tk = float(t.get("start")), float(t.get("end"))
            except (TypeError, ValueError):
                # 🔴 **Bo, nhung ⛔ KHONG im lang.** WhisperX that su de mot so tu
                #    khong can duoc (ky tu ngoai tu dien cua model can chinh,
                #    chu so) va khi do `word_segment` **khong co** khoa
                #    `start`/`end` — `alignment.py` chi gan khi khong phai NaN.
                #    Bo 3 tu khac han bo 900 tu, ma neu chi `continue` thi hai ca
                #    trong **y het nhau** o moi cho doc sau nay.
                bo_thieu_moc += 1
                continue
            if tk < tb:
                bo_moc_nguoc += 1
                continue
            tu.append({"bat": tb, "ket": tk, "chu": chu})

        doan = {"bat": bat, "ket": ket, "chu": van_ban, "tu": tu}
        # Provenance (22/09): do tin 0..1 cua NGUON (OCR: diem nhan dang trung
        # binh cac khung). ASR (faster-whisper qua autosubvideo) khong tra do
        # tin theo doan ⇒ vang mat, KHONG bia mot con so.
        if tho.get("confidence") is not None:
            doan["do_tin"] = round(float(tho["confidence"]), 4)
        ra.append(doan)

    if not ra:
        raise BanGhiError(_t('Không nghe được lời nói nào trong tệp.'))

    ra.sort(key=lambda d: (d["bat"], d["ket"]))
    for i, d in enumerate(ra, start=1):
        d["ma"] = f"seg_{i:04d}"

    ban = {
        "schema": SCHEMA_BAN_GHI,
        "ngon_ngu": str((thoi or {}).get("language") or ""),
        "engine": str((thoi or {}).get("engine") or ""),
        # ⭐ Giu lai NGUYEN VAN trang thai canh chinh cua engine. `whisperx` canh
        #    theo tung tu; faster-whisper thi khong, va no tu khai
        #    `fallback_unaligned`. Giau khac biet do la hua mot do chinh xac
        #    thoi gian ma ta khong co.
        "canh_chinh": str((thoi or {}).get("alignment_status") or ""),
        # 🔴 **VI SAO roi, khong chi ROI HAY KHONG.**
        #
        #    `transcription.py` phan biet duoc hai ca rat khac nhau:
        #      `whisperx_sidecar_unavailable`  -> **chua cau hinh** (moi truong)
        #      `<chuoi ngoai le>`              -> sidecar CO nhung **hong**
        #    ...roi ASV chi giu `canh_chinh` va **vut** `fallback_reason`.
        #
        # ⛔ Hai trang thai do ra **cung mot ban chep trong y het nhau**, nen nguoi
        #    doc `outputs` khong the biet nen di BAT SIDECAR hay di SUA no. Do that
        #    24/09: bench B1 thay `fallback_unaligned` va phai doc MA NGUON moi biet
        #    ly do — trong khi `apps/autosubvideo/jobs.py:154` da mang ca hai truong
        #    di tiep tu lau.
        "ly_do_roi": str((thoi or {}).get("fallback_reason") or ""),
        "thoi_luong_nguon": float(thoi_luong_nguon or 0.0),
        # 🔑 Nguon goc loi thoai. Tu 26/09 (Task 21) chi con MOT gia tri:
        #    `asr` — xem `nguon_loi.py`. Ban ghi truoc 22/09 khong co khoa nay =
        #    `asr`; ban ghi 22–26/09 co the mang `ocr`/`embedded` va do la ban ghi
        #    THAT cua mot duong da bo ⇒ ⛔ khong viet lai, khong xoa.
        #
        # ⚠️ Truong nay GIU du chi con mot gia tri: no la PROVENANCE cua ban ghi,
        #    khong phai mot lua chon. Bo no di se lam mot ban ghi cu (mang `ocr`)
        #    va mot ban ghi moi trong nhu nhau.
        "nguon_loi": str(nguon_loi or "asr"),
        # 🔴 **Tu bi BO, theo LY DO.** ⛔ Khong duoc rut gon thanh mot con so
        #    tong: *"bo 900 tu vi sai khoa"* la mot loi chuong trinh, *"bo 3 tu
        #    vi model can chinh khong co ky tu do"* la hanh vi binh thuong cua
        #    engine. Mot con so gop lai khong phan biet duoc hai ca do.
        "tu_bi_bo": {"khong_chu": bo_khong_chu, "thieu_moc": bo_thieu_moc,
                     "moc_nguoc": bo_moc_nguoc},
        # 🔴 **Tham số engine đi CÙNG bản ghi.** Một bản chép lời không tái lập
        #    được thì mọi con số đo trên nó — kể cả điểm DỊCH của B2 — cũng không
        #    tái lập được. ⛔ Đừng để người sau phải đi đọc mã ở commit nào đó.
        "tham_so_engine": dict((thoi or {}).get("tham_so") or {}),
        "doan": ra,
    }
    if dinh_tuyen:
        ban["dinh_tuyen"] = dinh_tuyen
    kiem(ban)
    return ban


def kiem(ban: dict) -> None:
    """Kiem mot ban ghi. Nem `BanGhiError` kem ly do cu the.

    Chay ca luc tao lan luc doc lai tu kho: mot artifact hop le luc ghi van co
    the bi sua sau do, va I8 noi DONE phai keo theo mot ket qua **con dung**.
    """
    if not isinstance(ban, dict):
        raise BanGhiError(_t('Bản ghi không đúng định dạng.'))
    if int(ban.get("schema") or 0) != SCHEMA_BAN_GHI:
        raise BanGhiError(_t('Bản ghi thuộc phiên bản cấu trúc khác.'))

    doan = ban.get("doan")
    if not isinstance(doan, list) or not doan:
        raise BanGhiError(_t('Bản ghi không có đoạn nào.'))

    ma_da_thay = set()
    truoc_ket = None
    for d in doan:
        ma = d.get("ma")
        if not ma or ma in ma_da_thay:
            raise BanGhiError(_t('Bản ghi có mã đoạn trùng hoặc thiếu.'))
        ma_da_thay.add(ma)

        bat, ket = float(d.get("bat", -1)), float(d.get("ket", -1))
        if bat < 0 or ket <= bat:
            raise BanGhiError(_t('Bản ghi có đoạn với mốc thời gian không hợp lệ.'))
        if truoc_ket is not None and bat + SAI_SO_S < truoc_ket:
            # ⛔ Doan chong len nhau la mot loi CHET NGUOI o ha nguon: TIMING se
            #    chen hai doan tieng vao cung mot khe, va ban long tieng se co
            #    hai giong noi de len nhau.
            raise BanGhiError(_t('Bản ghi có hai đoạn chồng thời gian lên nhau.'))
        truoc_ket = ket

        if not _lam_sach(d.get("chu")):
            raise BanGhiError(_t('Bản ghi có đoạn rỗng.'))

        for t in (d.get("tu") or []):
            tb, tk = float(t.get("bat", -1)), float(t.get("ket", -1))
            if tb < bat - SAI_SO_S or tk > ket + SAI_SO_S:
                raise BanGhiError(
                    _t('Bản ghi có từ nằm ngoài đoạn chứa nó.'))

    # 🔴 **BAT BIEN: `aligned` PHAI co moc tung tu.** ⛔ Khong phai canh bao nhe.
    #
    #    `canh_chinh` la mot **loi hua** ma ha nguon tin: `timing_align` doc co do
    #    va lam viec nhu the moi doan co moc ben trong. Su co 24/09 (N-17): co ghi
    #    `"aligned"` trong khi ban ghi mang **0 tu** — mot khoi 24 giay khong mot
    #    moc nao ben trong. Hai trang thai rat khac nhau deo **cung mot nhan**, va
    #    khong phep kiem nao do vi khong con so nao SAI, chi mat kha nang phan biet.
    #
    # ⇒ Nhan phai duoc mot cai may bat khop, khong phai mot con nguoi nho ra.
    if str(ban.get("canh_chinh") or "") == "aligned":
        if not sum(len(d.get("tu") or []) for d in doan):
            raise BanGhiError(_t(
                'Bản ghi khai đã căn chỉnh nhưng không có mốc từng từ nào.'))
    # 🔴 **N-39, 25/09: `sum` o tren la mot bat bien cap BAN GHI, ma khuyet tat
    #    nam o cap DOAN.** Do duoc: `v1/seg_0083` co `tu=[]` trong khi ban ghi
    #    mang 1.157 tu ⇒ **lot**. Chinh doan ay la mot **ao giac credit phu de**
    #    (`中文字幕志愿者 …`, kieu hong da biet cua Whisper tieng Trung o CUOI
    #    tep), khe `0,034 s` — va no DA duoc dich va se duoc doc thanh tieng.
    #
    # ⭐ Cung ho *"tong che mot so 0"*: mot tong khac 0 ⛔ khong noi duoc rang
    #    **moi** doan khac 0.
    #
    # ⛔ Va vi sao o day ⛔ KHONG `raise` theo tung doan: mot doan thieu moc tu
    #    co the la engine **that su** khong can duoc mot ky tu la — nem loi se
    #    **giet ca mot ban ghi** vi mot doan. Quyet dinh LOC hay GIU doan ao giac
    #    la quyet dinh **cham san pham**, va no thuoc ve chu du an.
    # ⇒ Buoc dung o day la lam no **NHIN THAY DUOC**: dem va dua ra `tom_tat`
    #   (di vao `stage.outputs`). ⛔ Mot con so 0 im lang la thu da giau no.


def dem_doan_thieu_moc_tu(ban: dict) -> int:
    """So doan ⛔ KHONG co mot moc tu nao, tren mot ban ghi khai `aligned`.

    `0` tren nhanh `fallback_unaligned` la **dung ky vong**, nen chi dem khi
    nhan la `aligned` — ⛔ khong tra mot con so co nghia khac duoi cung mot ten.
    """
    if str(ban.get("canh_chinh") or "") != "aligned":
        return 0
    return sum(1 for d in (ban.get("doan") or []) if not (d.get("tu") or []))


#: 🔴 N-39 — nguong TOC DO NGUON de nghi mot doan la AO GIAC ASR (ky tu/giay).
#:
#: ⛔ **KHONG lot theo MAU CHU** (`中文字幕志愿者`…): mot danh sach den thi **gion**,
#:    va no bo sot moi ao giac co chu khac. Ta lot theo **CAU TRUC**.
#:
#: ⭐ **HIEU CHINH tren 188 doan that cua ba phim** (25/09), ⛔ khong phai mot so
#:    nghi ra:
#:
#:        doan CO moc tu (n=187): trung vi 5,68 · p95 8,27 · **MAX 9,43** kt/s
#:        ca ao giac `v1/seg_0083`                     : **294,1** kt/s  (31x max)
#:
#:    `30,0` nam o **3,2x** muc that cao nhat da do, va **1/10** ca ao giac —
#:    ⭐ rong rai ve **ca hai** phia. Do tren 187 doan that: **0 doan** cham toi.
NGUONG_KY_TU_MOI_GIAY = 30.0


#: B13 B1 (28/09, asvr_47327a869a8f4597960048f09064740) — tin hieu AO GIAC THU
#: BA, doc lap voi (a)/(b) o `nghi_ao_giac`: doan la khuc con cua chinh
#: `initial_prompt` ta truyen cho whisperx (`whisperx_runner.MAU_CO_DAU_CAU`,
#: ghim vao `ban["tham_so_engine"]["initial_prompt"]` boi `chuan_hoa()`). Day
#: la phep DOI CHIEU dau vao — ta biet NGUYEN VAN chuoi da truyen, khong phai
#: doan noi dung nhu (a)/(b).
#:
#: ⭐ Ca that N-39/B1 duoc dung de hieu chinh: doan ao giac `v1/seg_0024`
#:    (64,27–65,17 s) mang van ban `中文字幕志愿者`... khong, mang
#:    `中文普通话句子` — **khop 7 ky tu** voi khuc giua prompt
#:    `以下是中文普通话句子。`. Doan nay CO moc tu (7/0,90 s = 7,8 kt/s) nen
#:    (a)/(b) khong tin hieu nao cham toi — day chinh la ly do can mot tin
#:    hieu THU BA doc lap.
#:
#: ⚠️ **Rui ro duong tinh gia**: prompt chua cac khuc con NGAN co the la loi
#:    thoai that (vd `中文`, `句子`). `4` la nguong DUOI muc that (7) va TREN
#:    muc an toan (mot khop 2 ky tu nhu `中文` trong mot cau thoai that KHONG
#:    duoc gan co) — khong phai so nghi ra, xem test doi chung am.
NGUONG_KY_TU_VONG_LAI_PROMPT = 4


def _vong_lai_prompt(chu_tho: str, prompt: str) -> dict | None:
    """Van ban doan co la khuc con (>= `NGUONG_KY_TU_VONG_LAI_PROMPT` ky tu, sau
    khi bo khoang trang) cua `prompt` khong?

    ⛔ So khop CHINH XAC (substring), khong phai tuong tu mo ho: ta biet dung
    chuoi da truyen vao engine, nen day la doi chieu dau vao chu khong phai
    doan tu noi dung.
    """
    chu_gon = "".join(str(chu_tho or "").split())
    prompt_gon = "".join(str(prompt or "").split())
    if len(chu_gon) < NGUONG_KY_TU_VONG_LAI_PROMPT or not prompt_gon:
        return None
    if chu_gon not in prompt_gon:
        return None
    return {
        "ly_do": "vong_lai_initial_prompt",
        "khop_ky_tu": len(chu_gon),
        "nguong": NGUONG_KY_TU_VONG_LAI_PROMPT,
    }


def nghi_ao_giac(doan: dict, *, canh_chinh: str,
                 initial_prompt: str = "") -> dict | None:
    """Doan nay co phai AO GIAC ASR khong? `None` = khong nghi.

    HAI DUONG doc lap, mot trong hai du la nghi:

    **Duong 1 — VONG LAI PROMPT** (B13 B1, 28/09, xem `_vong_lai_prompt`): van
    ban doan la khuc con cua `initial_prompt` ta tu truyen vao whisperx. Doc
    lap voi `canh_chinh`/moc tu/toc do — day la doi chieu dau vao, khong phai
    suy doan tu cau truc ket qua.

    **Duong 2 — HAI tin hieu CAU TRUC cung dong y** (N-39) — ⛔ mot minh thi
    khong du:

        (a) ZERO moc tu, trong mot ban ghi khai `aligned`
        (b) toc do nguon BAT KHA: > `NGUONG_KY_TU_MOI_GIAY`

    ⛔ **(a) mot minh** se loai mot **cau that** ma engine khong can noi (ky tu
       la) ⇒ mat noi dung cua khach.
    ⛔ **(b) mot minh** co the bat mot khe bi **cat sai**, ⛔ khong phai ao giac.
    ⭐ Hai cai cung dong y thi gan nhu chac chan ⛔ khong phai tieng nguoi.

    ⚠️ Vi sao do **toc do NGUON** chu khong do **he so nen** (2,41x that so voi
       89,56x cua ca ao giac): he so nen can **ban dich**, ma o buoc nay ban dich
       ⛔ chua ton tai. Cung mot hien tuong, phat hien SOM hon mot giai doan —
       va do la truoc khi khach **tra tien dich**.
    """
    chu_tho = str(doan.get("chu") or "")
    dai = float(doan.get("ket", 0)) - float(doan.get("bat", 0))

    if initial_prompt:
        vong = _vong_lai_prompt(chu_tho, initial_prompt)
        if vong:
            return {**vong, "khe_s": round(dai, 3) if dai > 0 else 0.0,
                    "so_ky_tu": len("".join(chu_tho.split()))}

    if str(canh_chinh or "") != "aligned":
        return None
    if doan.get("tu"):
        return None                       # (a) khong thoa
    chu = "".join(chu_tho.split())
    if not chu or dai <= 0:
        return None
    cps = len(chu) / dai
    if cps <= NGUONG_KY_TU_MOI_GIAY:
        return None                       # (b) khong thoa
    return {
        "ly_do": "zero_moc_tu_va_toc_do_bat_kha",
        "ky_tu_moi_giay": round(cps, 1),
        "nguong": NGUONG_KY_TU_MOI_GIAY,
        "khe_s": round(dai, 3),
        "so_ky_tu": len(chu),
    }


def danh_dau_nghi_ao_giac(ban: dict) -> int:
    """Gan co `nghi_ao_giac` vao doan bi nghi. Tra ve SO doan da gan.

    ⛔ **DANH DAU, ⛔ KHONG XOA.** Doan o lai trong ban ghi cung **ly do** va
       **cac con so** da kich hoat no. ⭐ Danh dau thi **dao nguoc duoc**; xoa
       thi khong — va ta ⛔ khong xoa du lieu cua khach vi mot **suy doan**.

    ⇒ Buoc DICH va buoc DOC TIENG doc co nay de **BO QUA** doan ay: khach ⛔ khong
      tra tien cho mot cau vo nghia va ⛔ khong nghe thay no.
      ⚠️ Viec NOI co vao hai buoc do nam o `giai_doan_noi_dung.py` / `long_tieng.py`
         — **lan khac so huu**. Ham nay chi SINH ra co.

    🔑 B13 B1: `initial_prompt` doc tu `ban["tham_so_engine"]` — day la cho
       DUY NHAT ban ghi mang lai chuoi da truyen cho engine (xem
       `whisperx_runner.py` va `chuan_hoa()`).
    """
    canh = str(ban.get("canh_chinh") or "")
    prompt = str((ban.get("tham_so_engine") or {}).get("initial_prompt") or "")
    dem = 0
    for d in ban.get("doan") or []:
        co = nghi_ao_giac(d, canh_chinh=canh, initial_prompt=prompt)
        if co:
            d["nghi_ao_giac"] = co
            dem += 1
    return dem


#: B13 B2 (28/09) — CUA A: ty le PHU SONG/THOI LUONG NGUON duoi nguong nay ⇒
#: canh bao van hanh (⛔ khong chan luot).
#:
#: ⭐ Can cu: luot that `asvr_47327a869a8f4597960048f09064740` — 78 doan,
#:    phu_song 211,56 / thoi_luong 275,04 = **76,9 %**, va do THAT SU la mot
#:    loi ASR (8 lo hong, lo lon nhat 32,5 s). `0,80` nam TREN muc that hong
#:    (76,9 %) mot bien do vua du (~3 diem) de khong sat nut ma cung khong qua
#:    rong — day la canh bao, khong phai cong chan, nen thien ve BAT som hon
#:    la bo sot.
NGUONG_TY_LE_PHU_SONG = 0.80

#: CUA B: MOT lo hong DON LE (khong tieng, giua hai doan hoac o hai dau ban
#: ghi) dai hon nguong nay (giay) ⇒ canh bao.
#:
#: ⭐ Can cu: cung luot do — 8 lo hong **2,1–7,4 s** la BINH THUONG cua mot
#:    phim co doi thoai (⛔ khong duoc keu — bai hoc bao dong gia da ghi trong
#:    kho), lo hong THAT su la loi = **32,5 s**. `15,0` la TRUNG BINH NHAN cua
#:    hai muc (`sqrt(7,4 * 32,5) ≈ 15,5`, lam tron xuong) — bien do ~2,1x ve
#:    CA HAI phia tren thang log, cung logic hieu chinh doi xung nhu
#:    `NGUONG_KY_TU_MOI_GIAY` o tren.
NGUONG_LO_HONG_S = 15.0


def do_phu_song(ban: dict, *, thoi_luong: float) -> dict:
    """Hai CUA doc lap tren `phu_song` — con so DA CO SAN trong `tom_tat()`
    nhung chua ai doc (B13 B2).

    CUA A (tong): ty le `phu_song / thoi_luong` duoi `NGUONG_TY_LE_PHU_SONG`.
    CUA B (cuc bo): MOT lo hong (khong tieng — giua hai doan lien tiep, truoc
    doan dau, hoac sau doan cuoi) dai hon `NGUONG_LO_HONG_S`.

    ⛔ **Vi sao PHAI ca hai, khong phai mot**: mot tong 90 % van co the giau
       mot ho 30 giay (nhieu doan ngan phu day cho, mot ho lon lot giua);
       nguoc lai mot phim THAT SU it loi co tong thap ma ⛔ khong ho nao —
       CUA A mot minh se keu oan cho ca hai truong hop nhu nhau. Ham nay tra
       ve con so cho CA HAI cua, ⛔ khong rut gon thanh mot co bool.

    ⚠️ Day la **canh bao van hanh** (`log.warning` + con so vao `outputs`),
       ⛔ KHONG chan luot chay: mot phim it loi la hop le.
    """
    doan = sorted(ban.get("doan") or [],
                  key=lambda d: (float(d.get("bat", 0)), float(d.get("ket", 0))))
    thoi_luong = float(thoi_luong or 0.0)
    phu_song = sum(float(d["ket"]) - float(d["bat"]) for d in doan)

    lo_hong: list[float] = []
    truoc = 0.0
    for d in doan:
        bat = float(d["bat"])
        if bat > truoc:
            lo_hong.append(bat - truoc)
        truoc = max(truoc, float(d["ket"]))
    if thoi_luong > truoc:
        lo_hong.append(thoi_luong - truoc)

    ty_le = (phu_song / thoi_luong) if thoi_luong > 0 else 1.0
    lo_lon_nhat = max(lo_hong) if lo_hong else 0.0

    return {
        "ty_le_phu_song": round(ty_le, 4),
        "nguong_ty_le": NGUONG_TY_LE_PHU_SONG,
        "canh_bao_ty_le": bool(thoi_luong > 0 and ty_le < NGUONG_TY_LE_PHU_SONG),
        "lo_hong_lon_nhat_s": round(lo_lon_nhat, 2),
        "so_lo_hong_qua_nguong": sum(1 for g in lo_hong if g > NGUONG_LO_HONG_S),
        "nguong_lo_hong_s": NGUONG_LO_HONG_S,
        "canh_bao_lo_hong": bool(lo_lon_nhat > NGUONG_LO_HONG_S),
    }


def van_tay_ban_ghi(*, checksum_tieng: str, model: str, ngon_ngu: str,
                    phien_ban_ma: int, nguon_loi: str = "") -> str:
    """Van tay cua ban ghi (Prompt 10 muc 7).

    Bon thanh phan, va ly do tung cai:
      `checksum_tieng`  doi tieng vao       -> phai chep lai
      `model`           doi model ASR       -> ket qua khac han
      `ngon_ngu`        ep ngon ngu khac    -> ket qua khac han
      `phien_ban_ma`    doi cach chuan hoa  -> hinh dang khac
    """
    goi = json.dumps({
        "tieng": checksum_tieng,
        "model": model,
        "ngon_ngu": ngon_ngu,
        "schema": SCHEMA_BAN_GHI,
        "ma": int(phien_ban_ma),
        # `che_do:nguon:engine` — cung tieng, khac nguon loi = ban ghi khac.
        **({"nguon_loi": nguon_loi} if nguon_loi else {}),
    }, sort_keys=True)
    return hashlib.sha256(goi.encode("utf-8")).hexdigest()


def tom_tat(ban: dict) -> dict:
    """Vai con so cho tien do va cho log. Khong co noi dung loi thoai.

    ⛔ Khong dua `chu` vao day: tom tat di vao `stage.outputs` va vao log, va
       loi thoai cua khach khong thuoc ve mot dong log.
    """
    doan = ban.get("doan") or []
    return {
        "so_doan": len(doan),
        "so_tu": sum(len(d.get("tu") or []) for d in doan),
        # 🔴 N-39: mot doan `aligned` ma ⛔ khong co moc tu nao. > 0 la dau hieu
        #    ao giac ASR (credit phu de cuoi tep) hoac mot doan khong can duoc.
        "so_doan_thieu_moc_tu": dem_doan_thieu_moc_tu(ban),
        # 🔴 N-39: doan DA duoc gan co (hai tin hieu cung dong y).
        #    ⭐ Khac `so_doan_thieu_moc_tu`: cai kia la NGHI, cai nay la CHOT.
        "so_doan_nghi_ao_giac": sum(
            1 for d in doan if d.get("nghi_ao_giac")),
        "ngon_ngu": ban.get("ngon_ngu", ""),
        "engine": ban.get("engine", ""),
        "canh_chinh": ban.get("canh_chinh", ""),
        # ⛔ Di theo `canh_chinh` len `outputs`: mot co "da roi" ma khong kem ly do
        #    bat nguoi doc di doc ma nguon.
        "ly_do_roi": ban.get("ly_do_roi", ""),
        "nguon_loi": ban.get("nguon_loi", "asr"),
        # ⭐ Di len `outputs` cung `so_tu`: mot `so_tu` thap chi tra loi duoc
        #    *"vi sao thap"* khi no di kem so tu DA BI BO va ly do bo.
        "tu_bi_bo": dict(ban.get("tu_bi_bo") or {}),
        # ⭐ Lên `outputs` để một lượt đo bất kỳ tái lập được đường chép lời đã
        #    sinh ra số của nó. ⛔ Không rút gọn thành "đã ghim".
        "tham_so_engine": dict(ban.get("tham_so_engine") or {}),
        "phu_song": round(
            sum(float(d["ket"]) - float(d["bat"]) for d in doan), 2),
    }

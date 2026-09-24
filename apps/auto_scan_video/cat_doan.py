"""Cat lai doan dai thanh KHE LONG TIENG, bang chinh moc tung tu cua engine.

## Vi sao can buoc nay — do 24/09, doc tu GOI DA CAI

Nhanh mac dinh (`whisperx`, `canh_chinh="aligned"`) tra ve **~24 giay mot doan**
tren ca ba phim Han, trong khi hardsub cua chinh phim do cho **2,4 giay**. Voi
san pham long tieng, **phan doan CHINH LA san pham**: moi doan la mot khe de dat
cau tieng Viet, va mot khe 24 giay lien mach thi `timing_align` khong con gi de
canh.

⛔ **Khong phai vi `chunk_size=30`.** WhisperX **da** chia khoi VAD 30 giay thanh
   CAU ngay trong `align()` — no goi NLTK Punkt (`alignment.py:190-196`). Thu
   hong la Punkt **khong co mo hinh cho tieng Han**:

       whisperx/utils.py:130-150   PUNKT_LANGUAGES  — khong co 'zh', khong co 'ja'
       whisperx/alignment.py:190   punkt_lang = PUNKT_LANGUAGES.get(lang, 'english')

   ⇒ van Han roi vao mo hinh **tieng Anh**, ma Punkt tieng Anh cat theo `.` + dau
   cach — van Han dung `。` va khong co dau cach. Do that tren goi da cai
   (whisperx 3.8.6, `D:\\LTTWhisperX`):

       '大家好今天…。首先…。然后…。'  (44 ky tu, 3 cau)  -> Punkt en cho  1  span
       'Hello everyone. Today… First…'                  -> Punkt en cho  3  span

   ⇒ Ca khoi ~30 giay ve lam MOT `aligned_subsegment`. Do chinh la con so 24 s.

⭐ Ha `chunk_size` KHONG sua duoc benh nay: khoi co nho lai thi Punkt van khong
   tim ra ranh gioi cau nao trong van Han, va ta mat 3,6x toc do cua duong batched.

## Nguon — ⛔ ta KHONG la nguoi dau tien giai bai nay

| nguon | la gi | dung gi o day |
|---|---|---|
| `m-bain/whisperX` **issue #1310** (MO) | *"Why WhisperX's sentence segmentation not working for Chinese?"* — dung trieu chung cua ta, chi dung `alignment.py` dong 195-200 | xac nhan nguyen nhan, khong phai ta suy ra |
| `m-bain/whisperX` **PR #1466** (MO, dong #1310) | *"Split Chinese and Japanese into sentences during alignment"* — them `CJKSentenceSplitter` vao `whisperx/utils.py` | ⭐ **luat cat o day chep theo PR nay** (BSD-2-Clause) |
| `m-bain/whisperX` **issue #519** (MO) | so cai cua ca ho ve cat phu de theo dau cau; #829 bi dong lam **trung** #519 (collaborator, 16/02/2026) | cho thay upstream chua chot, nen ta khong cho |
| `whisperx/SubtitlesProcessor.py` (co trong goi da cai) | bo cat theo `，`/lien tu, zh: `max_line_length=30` | ⛔ **khong dung** — xem duoi |
| `jianfch/stable-ts` (MIT) | `WhisperResult('audio.json')` + `regroup` — gom/tach lai ket qua CO SAN, khong chay lai whisper | ⛔ **khong dung** — xem duoi |

**Vi sao khong `SubtitlesProcessor`** du no da nam san trong goi: khi mot mach chu
vuot `max_line_length` ma khong co dau phay, no cat o **DIEM GIUA**
(`determine_advanced_split_points`: `midpoint = normal_round((last_split_point + i) / 2)`).
Do la **cat giua cau** — voi ban phu de thi chi xau, voi ban LONG TIENG thi khe
chua **nua y** va cau dich sai nghia. ⛔ Rang buoc cua viec nay cam dieu do.
(Va no con mang loi #1089: `save()` khong ghi gi khi `advanced_splitting=False`.)

**Vi sao khong `stable-ts`** du giay phep MIT va no **nhan duoc ket qua co san**
(khong bat chay lai whisper — da kiem): no la mot goi **chua cai** tren may nay, va
no giai dung bai toan ma `CJKSentenceSplitter` cua PR #1466 giai bang ~60 dong
khong phu thuoc. ⭐ Them mot goi de lam mot viec ta da co ma nguon upstream cho la
doi lay mot bien moi ma khong doi lay gi.

## NGUONG — tra tu quy chuan CONG BO, ⛔ khong tu dat

Netflix Timed Text Style Guide (doc 24/09):

| so | nguon |
|---|---|
| khe toi da **7,0 giay** | *General Requirements* (bai 215758617) — *"Maximum duration: 7 seconds per subtitle event"* |
| khe toi thieu **5/6 giay** (0,833) | cung bai — *"Minimum duration: 5/6 of a second per subtitle event"* |
| **16 ky tu/dong**, toi da 2 dong ⇒ 32 ky tu | *Chinese (Simplified)* (bai 215986007) — *"Character Limitation: 16 characters per line"* |
| toc do doc **9 ky tu/giay** (nguoi lon) | cung bai — *"Adult programs: Up to 9 characters per second"* |

⛔ 32 ky tu va 9 kt/s la **chi bao**, khong phai cong: chung noi ve ban DICH tieng
Viet se dat vao khe, chua ton tai o buoc nay.

## Luat cat — chi cat o DAU CAU, ⛔ khong bao gio giua cau

1. Cat sau moi **dau ket cau** (`。！？．!?.`) theo dung luat cua PR #1466: `.`
   chi ket cau khi sau no la khoang trang/het chuoi; `．` khong ket cau khi nam
   giua hai chu so; `!`/`?` khong ket cau khi truoc no la chu cai ASCII
   (`Yahoo!`, `?q=1`). Dau dong (`」』）…`) di theo cau no dong.
2. Manh nao van dai hon **7,0 s** ⇒ cat tiep sau **dau phay** (`，,、`). Dau phay
   van la mot cho ngat THAT cua nguoi viet, khong phai mot diem giua tu dat.
3. Manh nao ngan hon **0,833 s** ⇒ **gop lai** vao manh truoc (nguong toi thieu
   cua Netflix).
4. Het cach ⇒ **DE NGUYEN va KHAI RA** (`so_doan_qua_dai`, `so_doan_khong_cho_ngat`).
   ⛔ Khong che bua cho du so doan.

⭐ Luat 4 la ly do ham nay tra ve mot **chan doan** chu khong chi tra ve doan.
   Mot bo cat "luon dat" la mot bo cat da cat giua cau o dau do.
"""
from __future__ import annotations

#: Dau KET CAU. ⛔ Chep tu `CJK_TERMINATORS` cua whisperX PR #1466
#: (`whisperx/utils.py`, BSD-2-Clause) — khong tu soan mot bang khac.
KET_CAU = "。！？．!?."

#: Dau DONG (ngoac/nhay dong) — thuoc ve cau no dong: 「もう終わりです。」
#: ⛔ `"` va `'` CO Y vang mat: cung mot ky tu vua mo vua dong, nen coi no la dau
#:    dong se nuot luon dau mo cua cau ke tiep (ghi chu cua chinh PR #1466).
DAU_DONG = "」』）］｝〉》”’)]}"

#: Dau PHAY — cho ngat hang hai, chi dung khi mot manh van vuot `KHE_TOI_DA_S`.
DAU_PHAY = "，,、"

CHU_SO = "0123456789０１２３４５６７８９"

#: Netflix Timed Text Style Guide — *General Requirements* (bai 215758617).
#: ⛔ Hai so nay la QUY CHUAN CONG BO, khong phai so ta chon. Doi chung thi doi
#:    ca nguon, dung sua mot ben.
KHE_TOI_DA_S = 7.0
KHE_TOI_THIEU_S = 5.0 / 6.0

#: Netflix *Chinese (Simplified)* (bai 215986007). ⭐ CHI BAO, khong phai cong —
#: chung noi ve ban dich se dat vao khe, chua ton tai o buoc nay.
KY_TU_MOI_DONG = 16
DONG_TOI_DA = 2
KY_TU_MOI_GIAY = 9

#: Ngon ngu viet KHONG co dau cach giua tu. ⛔ Khop `whisperx.alignment
#: .LANGUAGES_WITHOUT_SPACES` — cung tap hop, cung ly do.
KHONG_DAU_CACH = ("zh", "ja")


def _chu(tu: dict) -> str:
    """Chu cua mot tu. Hai engine dat hai TEN khac nhau cho cung mot thu.

    🔴 **`whisperx` dung `word`, `faster-whisper` (qua `transcription.py`) dung
       `text`.** `ban_ghi.chuan_hoa` chi doc `text` ⇒ tren nhanh MAC DINH moi moc
       tung tu bi **vut im lang**, va do dung la thu duong sua nay can. Doc tu ma
       nguon 24/09: `whisperx/alignment.py:354  word_segment = {"word": word_text}`
       vs `transcription.py:239  {"start":…, "end":…, "text":…}`.
    """
    return str(tu.get("word") or tu.get("text") or "")


def _ket_cau(chuoi: str, i: int) -> bool:
    """Dau o `i` co THAT SU ket mot cau khong.

    ⛔ Chep nguyen luat cua `CJKSentenceSplitter._ends_sentence` (whisperX PR
       #1466). Ba ngoai le duoi day deu la ca THAT ma PR do da co phep kiem.
    """
    dau = chuoi[i]
    truoc = chuoi[i - 1] if i else ""
    sau = chuoi[i + 1] if i + 1 < len(chuoi) else ""
    if dau == ".":
        # `.` la dau thap phan it nhat cung thuong nhu dau cham cau. Punkt chi
        # ngat khi sau no la khoang trang — lam y he: "3.14" nguyen, "你好. 再见." ngat.
        return sau == "" or sau.isspace()
    if dau == "．":
        # `．` ket cau trong loi viet 「，．」, nhung cung la dau thap phan toan rong.
        return not (truoc in CHU_SO and sau in CHU_SO)
    if dau in "!?":
        # `!`/`?` nam trong tu Latin va URL nhung trong van Han: Yahoo!ニュース, ?q=1.
        return not (truoc.isascii() and truoc.isalnum())
    return True


def _mach_chu(tu_list: list[dict], *, lien: bool) -> tuple[str, list[int]]:
    """Noi chu cua cac tu thanh mot mach, kem vi tri BAT DAU cua tung tu trong mach.

    ⭐ Cat tren mach chu cua CHINH DANH SACH TU chu khong tren `segment["text"]`:
       ranh gioi ta xuat ra phai la ranh gioi cua mot TU co moc thoi gian. Cat
       tren mot chuoi khac roi anh xa nguoc lai la them mot cho de lech.
    """
    noi = "" if lien else " "
    mach, moc = "", []
    for t in tu_list:
        if mach and noi:
            mach += noi
        moc.append(len(mach))
        mach += _chu(t)
    return mach, moc


def _cho_ngat(mach: str, moc: list[int], bang_dau: str) -> set[int]:
    """Chi so TU cuoi cung cua moi manh, cat sau `bang_dau`.

    Tra ve tap chi so tu ma SAU no duoc phep ngat. ⛔ Khong bao gio tra ve mot
    chi so khong dung sau mot dau cau — do la ca duy nhat bi cam.
    """
    if not mach:
        return set()
    ngat: set[int] = set()
    i, n = 0, len(mach)
    while i < n:
        if mach[i] not in bang_dau or (bang_dau is KET_CAU
                                       and not _ket_cau(mach, i)):
            i += 1
            continue
        cuoi = i + 1
        # Mot MACH dau ket lien nhau ket MOT cau, khong phai nhieu: 「！？」
        while cuoi < n and mach[cuoi] in bang_dau:
            cuoi += 1
        while cuoi < n and mach[cuoi] in DAU_DONG:
            cuoi += 1
        # Tu nao chua ky tu cuoi cung cua manh nay thi la tu CUOI cua manh.
        for k in range(len(moc) - 1, -1, -1):
            if moc[k] < cuoi:
                ngat.add(k)
                break
        i = cuoi
    ngat.discard(len(moc) - 1)          # ngat o cuoi doan khong phai mot nhat cat
    return ngat


def _bat(tu_list: list[dict]):
    for t in tu_list:
        g = t.get("start")
        if isinstance(g, (int, float)):
            return float(g)
    return None


def _ket(tu_list: list[dict]):
    for t in reversed(tu_list):
        g = t.get("end")
        if isinstance(g, (int, float)):
            return float(g)
    return None


def _manh(tu_list: list[dict], ngat: set[int]) -> list[list[dict]]:
    ra, dem = [], []
    for k, t in enumerate(tu_list):
        dem.append(t)
        if k in ngat:
            ra.append(dem)
            dem = []
    if dem:
        ra.append(dem)
    return ra


def _gop_manh_ngan(manh: list[list[dict]]) -> list[list[dict]]:
    """Gop manh ngan hon `KHE_TOI_THIEU_S` vao manh TRUOC no.

    Nguong toi thieu cua Netflix (bai 215758617). Mot khe 0,3 giay khong doc kip
    mot cau tieng Viet nao, nen chia ra khong duoc gi ma mat mot cho ngat.
    """
    ra: list[list[dict]] = []
    for m in manh:
        b, k = _bat(m), _ket(m)
        ngan = b is not None and k is not None and (k - b) < KHE_TOI_THIEU_S
        if ra and ngan:
            ra[-1].extend(m)
        else:
            ra.append(m)
    return ra


def _cat_mot_doan(doan: dict, *, lien: bool) -> tuple[list[dict], dict]:
    """Mot doan tho -> danh sach doan tho + chan doan. ⛔ Chi cat o dau cau."""
    tu_list = [t for t in (doan.get("words") or []) if _chu(t).strip()]
    chan = {"khong_cho_ngat": 0, "qua_dai": 0, "khong_co_moc_tu": 0}
    try:
        d_bat, d_ket = float(doan.get("start")), float(doan.get("end"))
    except (TypeError, ValueError):
        return [doan], chan
    if (d_ket - d_bat) <= KHE_TOI_DA_S:
        return [doan], chan                     # da vua khe, khong dung vao
    if not tu_list:
        # ⛔ Khong co moc tung tu thi KHONG cat: cat theo ti le ky tu la bia moc.
        chan["khong_co_moc_tu"] = 1
        chan["qua_dai"] = 1
        return [doan], chan

    mach, moc = _mach_chu(tu_list, lien=lien)
    manh = _gop_manh_ngan(_manh(tu_list, _cho_ngat(mach, moc, KET_CAU)))

    # Manh nao van qua dai ⇒ thu cat tiep SAU DAU PHAY (van la cho ngat that).
    lai: list[list[dict]] = []
    for m in manh:
        b, k = _bat(m), _ket(m)
        if b is None or k is None or (k - b) <= KHE_TOI_DA_S:
            lai.append(m)
            continue
        m_mach, m_moc = _mach_chu(m, lien=lien)
        lai.extend(_gop_manh_ngan(_manh(m, _cho_ngat(m_mach, m_moc, DAU_PHAY))))
    manh = lai

    ra: list[dict] = []
    for m in manh:
        b, k = _bat(m), _ket(m)
        if b is None or k is None or k <= b:
            # Manh khong co moc dung duoc ⇒ tra ve nguyen doan, ⛔ khong bia moc.
            chan["khong_cho_ngat"] = 1
            chan["qua_dai"] = 1
            return [doan], chan
        moi = dict(doan)
        moi.pop("confidence", None) if doan.get("confidence") is None else None
        moi["start"], moi["end"] = b, k
        moi["words"] = m
        moi["text"] = ("" if lien else " ").join(_chu(t) for t in m).strip()
        ra.append(moi)
        if (k - b) > KHE_TOI_DA_S:
            chan["qua_dai"] += 1
    if len(ra) == 1:
        chan["khong_cho_ngat"] = 1
    return ra, chan


def cat_lai(tho: dict, *, ngon_ngu: str = "") -> tuple[dict, dict]:
    """Ket qua THO cua engine -> ket qua tho da cat lai + **chan doan**.

    ⭐ Tra ve chan doan la bat buoc, khong phai tien nghi: mot bo cat "luon dat"
       la mot bo cat da cat giua cau o dau do. Nguoi doc phai thay duoc **bao
       nhieu doan ta KHONG cat duoc**.

    ⛔ Khong chay lai ASR, khong dung den card: chi doc moc tung tu da co.
    """
    nn = (str(ngon_ngu or tho.get("language") or "")).lower()[:2]
    lien = nn in KHONG_DAU_CACH
    doan_tho = list((tho or {}).get("segments") or [])
    ra: list[dict] = []
    chan = {"so_doan_truoc": len(doan_tho), "so_doan_sau": 0,
            "so_doan_qua_dai": 0, "so_doan_khong_cho_ngat": 0,
            "so_doan_khong_co_moc_tu": 0, "ngon_ngu": nn,
            "khe_toi_da_s": KHE_TOI_DA_S, "khe_toi_thieu_s": KHE_TOI_THIEU_S,
            "nguon_luat": "whisperX PR #1466 (CJKSentenceSplitter) · "
                          "Netflix TTSG 215758617 + 215986007"}
    for d in doan_tho:
        moi, c = _cat_mot_doan(d, lien=lien)
        ra.extend(moi)
        chan["so_doan_qua_dai"] += c["qua_dai"]
        chan["so_doan_khong_cho_ngat"] += c["khong_cho_ngat"]
        chan["so_doan_khong_co_moc_tu"] += c["khong_co_moc_tu"]
    chan["so_doan_sau"] = len(ra)
    moi_tho = dict(tho)
    moi_tho["segments"] = ra
    moi_tho["cat_lai"] = chan
    return moi_tho, chan

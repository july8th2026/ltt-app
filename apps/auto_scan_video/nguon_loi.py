"""DINH TUYEN nguon loi thoai cho TRANSCRIBE — co ghi nguon goc (provenance).

    phu de nhung (luong text trong container)  -> doc thang       nguon_loi=embedded
    hardsub chu Han dot vao hinh               -> OCR (RapidOCR)  nguon_loi=ocr
    con lai                                    -> ASR (whisper)   nguon_loi=asr

Che do (`CaiDat.nguon_loi`): `auto` (mac dinh, thu theo thu tu tren) | `embedded`
| `ocr` | `asr`. Che do EP ma nguon khong co ⇒ `KhongCoNguon` (khach doc duoc) —
⛔ khong lui im lang sang nguon khac. Che do `auto` lui sang buoc sau va GHI ly
do vao `dinh_tuyen.ly_do` (di vao tom tat giai doan, nguoi van hanh thay).

## Vi sao OCR chi nhan chu Han

Benchmark (`docs/auto_scan_video_final/L_OCR.md`) chi do tren hardsub tieng
Trung, va o do OCR THANG ASR ro ret ve chu (CER). Hardsub Latin (en/vi) chua co
bang chung — PP-OCRv6 small co doc Latin nhung dau tieng Viet chua do — nen
`auto` chi nhan ket qua OCR khi >= `TI_LE_HAN_TOI_THIEU` ky tu la chu Han, va
nguon khach khai (neu co) la `zh`.

## OCR va ASR ket hop the nao

Do tren clip (L_OCR.md §4): voi Douyin, hardsub LA ban lời thoai da duoc bien tap
(dung chu, dung dau cau), va moc thoi gian hien phu de lech moc ASR trong vong
mot khung lay mau. Nen OCR la NGUON CHU VA NGUON THOI GIAN; ASR khong chay tren
nhanh OCR (tiet kiem mot luot whisper large-v3 tren GPU).
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from platform_core.i18n import N_, _ as _t

from . import phu_de_cung

AUTO = "auto"
EMBEDDED = "embedded"
OCR = "ocr"
ASR = "asr"
CHE_DO_HOP_LE = (AUTO, EMBEDDED, OCR, ASR)
CHE_DO_MAC_DINH = AUTO

#: Phien ban logic dinh tuyen (+ logic hardsub). Vao PHIEN_BAN_MA cua TRANSCRIBE.
PHIEN_BAN_DINH_TUYEN = f"{1}.{phu_de_cung.PHIEN_BAN}"

#: Codec phu de dang CHU ffmpeg xuat ra SRT duoc. Phu de anh (PGS, DVD) khong co
#: chu de doc — di tiep sang buoc sau.
CODEC_CHU = frozenset({"subrip", "srt", "ass", "ssa", "mov_text", "webvtt", "text"})

#: Ma ngon ngu ISO 639-2 cua luong -> ma hop dong.
_MA_LUONG = {"chi": "zh", "zho": "zh", "chs": "zh", "cht": "zh", "zh": "zh",
             "eng": "en", "en": "en", "vie": "vi", "vi": "vi"}

#: Pass 1 (tim dai): so khung full-frame rai deu ca video.
SO_KHUNG_DO = 40
#: Pass 2 (doc dai): khung/giay. Do trong L_OCR.md §3.
FPS_DOC = 4.0
TI_LE_HAN_TOI_THIEU = 0.8


class KhongCoNguon(ValueError):
    """Che do EP mot nguon ma video khong co nguon do. Thong diep cho khach."""


def chuan_che_do(gia_tri) -> str:
    v = str(gia_tri or "").strip().lower()
    return v if v in CHE_DO_HOP_LE else CHE_DO_MAC_DINH


#: Nhan cho KHACH doc, theo CHE DO ho chon o Studio. `N_` = danh dau de trich.
#:
#: ⭐ Nhan noi **viec gi xay ra**, khong noi ten ky thuat: khach khong biet
#:    "OCR" hay "ASR" la gi, nhung ho biet "chu chay tren hinh" va "nghe roi
#:    chep". Cung luat voi `routes.NHAN_GIAI_DOAN`.
NHAN_CHE_DO = {
    AUTO: N_("Tự chọn nguồn tốt nhất"),
    EMBEDDED: N_("Phụ đề có sẵn trong tệp"),
    OCR: N_("Chữ chạy trên hình"),
    ASR: N_("Nghe tiếng rồi chép lại"),
}

#: Mo ta mot dong cho tung che do — cai gia phai tra khi EP mot nguon.
MO_TA_CHE_DO = {
    AUTO: N_("Ưu tiên phụ đề có sẵn, rồi tới chữ trên hình, cuối cùng mới nghe chép."),
    EMBEDDED: N_("Chỉ dùng phụ đề chữ nhúng trong tệp. Video không có thì dừng lại."),
    OCR: N_("Chỉ đọc chữ in trên khung hình. Video không có chữ thì dừng lại."),
    ASR: N_("Bỏ qua mọi phụ đề, nghe tiếng trong video rồi chép lại."),
}

#: Nhan cho nguon THAT da dung, hien o man mot lan chay.
#:
#: ⛔ KHAC `NHAN_CHE_DO`: `auto` la mot loi khai LUC NOP, khong bao gio la mot
#:    ket qua. Mot bang chung ghi "Tu chon nguon tot nhat" tra loi sai cau hoi
#:    duy nhat khach hoi o man do — *"lan chay nay lay loi tu dau"*.
NHAN_NGUON_THAT = {
    EMBEDDED: N_("Phụ đề có sẵn trong tệp"),
    OCR: N_("Chữ chạy trên hình"),
    ASR: N_("Nghe tiếng rồi chép lại"),
}


def cho_giao_dien() -> list[tuple[str, str, str]]:
    """`(ma, nhan, mo_ta)` cho tung che do — MOT nguon voi phep duyet o tren.

    ⛔ Khong go bon chuoi `auto`/`embedded`/`ocr`/`asr` vao template: `dinh_tuyen`
       o tep nay la nguoi duy nhat biet chung nghia la gi.
    """
    return [(m, NHAN_CHE_DO[m], MO_TA_CHE_DO[m]) for m in CHE_DO_HOP_LE]


#: Tran thoi gian cho tien trinh con (test_451: MOI loi goi phai co tran —
#: mot ffprobe treo tren tep hong se giu mot suat worker vo han).
TRAN_FFPROBE_S = 120
TRAN_RUT_SRT_S = 300


# ── 1. Phu de nhung ─────────────────────────────────────────────────────────

def luong_phu_de(duong_video: str) -> list[dict]:
    """Moi luong phu de: `{"chi_so", "codec", "ngon_ngu", "chu": bool}`."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "s", "-show_entries",
         "stream=index,codec_name:stream_tags=language", "-of", "json", duong_video],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=TRAN_FFPROBE_S)
    if r.returncode != 0:
        return []
    ra = []
    for i, s in enumerate((json.loads(r.stdout or "{}").get("streams") or [])):
        codec = str(s.get("codec_name") or "")
        ma = str((s.get("tags") or {}).get("language") or "").lower()
        ra.append({"chi_so": i, "codec": codec, "ngon_ngu": _MA_LUONG.get(ma, ""),
                   "chu": codec in CODEC_CHU})
    return ra


_MOC = re.compile(r"(\d+):(\d{2}):(\d{2})[,.](\d{1,3})")


def _giay(g) -> float:
    h, mi, s, ms = g
    return int(h) * 3600 + int(mi) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000.0


def doc_srt(van_ban: str) -> list[dict]:
    """SRT -> segments `{start,end,text,words,confidence}`. Bo the dinh dang."""
    ra = []
    for khoi in re.split(r"\r?\n\s*\r?\n", van_ban.strip()):
        dong = [d for d in khoi.splitlines() if d.strip()]
        for i, d in enumerate(dong):
            moc = _MOC.findall(d)
            if "-->" in d and len(moc) == 2:
                a, b = _giay(moc[0]), _giay(moc[1])
                chu = " ".join(dong[i + 1:])
                chu = re.sub(r"<[^>]+>|\{[^}]*\}", "", chu).strip()
                if chu and b > a:
                    ra.append({"start": a, "end": b, "text": chu, "words": [],
                               "confidence": 1.0})
                break
    return ra


def doc_phu_de_nhung(duong_video: str, *, ngon_ngu_khai: str = "") -> dict | None:
    """Ket qua dang engine tu luong phu de CHU, hoac None."""
    luong = [s for s in luong_phu_de(duong_video) if s["chu"]]
    if ngon_ngu_khai:
        khop = [s for s in luong if s["ngon_ngu"] == ngon_ngu_khai]
        luong = khop or [s for s in luong if not s["ngon_ngu"]]
    if not luong:
        return None
    s = luong[0]
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-nostdin", "-i", duong_video,
         "-map", f"0:s:{s['chi_so']}", "-f", "srt", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=TRAN_RUT_SRT_S)
    seg = doc_srt(r.stdout) if r.returncode == 0 else []
    if not seg:
        return None
    return {"segments": seg,
            "language": s["ngon_ngu"] or ngon_ngu_khai or doan_chu_viet(
                "".join(x["text"] for x in seg)),
            "engine": f"embedded/{s['codec']}", "alignment_status": "embedded",
            "_dinh_tuyen": {"luong": s["chi_so"], "codec": s["codec"]}}


#: Chu cai CHI tieng Viet co (khong co trong tieng Anh / Phap / ...).
_CHU_VIET = set("ăâđêôơưĂÂĐÊÔƠƯạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ")


def doan_chu_viet(chu: str) -> str:
    """Luong phu de KHONG gan the ngon ngu: nhan he chu (tat dinh, khong model).

    Chu Han >= 80% ⇒ `zh`; co chu cai rieng cua tieng Viet ⇒ `vi`; con Latin ⇒
    `en`. Ngoai ba he nay ⇒ rong, va `kiem_nguon_da_doan` tu choi voi khach.
    """
    if phu_de_cung.ti_le_chu_han(chu) >= TI_LE_HAN_TOI_THIEU:
        return "zh"
    if any(c in _CHU_VIET for c in chu):
        return "vi"
    chu_cai = [c for c in chu if c.isalpha()]
    if chu_cai and all(c.isascii() for c in chu_cai):
        return "en"
    return ""


# ── 2. Hardsub ──────────────────────────────────────────────────────────────

def _runner() -> Path:
    return Path(__file__).resolve().parents[1] / "asv_gpu" / "do_luong" / "ocr_khung.py"


def doc_hardsub(duong_video: str, *, thoi_luong: float, ctx=None,
                chay=None) -> tuple[dict | None, dict]:
    """(ket qua dang engine | None, chan doan). Nem `venv.KhongKhaDung`.

    `chay` = ham chay runner (mac dinh `do_luong.venv.chay`) — test thay duoc.
    """
    if chay is None:
        from apps.asv_gpu.do_luong import venv
        chay = venv.chay
    kw = {"gpu_uuid": "",               # ⛔ OCR chay CPU: khong gianh card voi Voice/VLM
          "is_cancelled": getattr(ctx, "is_cancelled", None) if ctx else None}
    fps_do = min(1.0, SO_KHUNG_DO / max(1.0, float(thoi_luong or 0)))
    p1 = chay(_runner(), {"video": duong_video, "fps": fps_do}, **kw)
    dai = phu_de_cung.phat_hien_dai(p1["khung"], rong=p1["rong"], cao=p1["cao"])
    cd = {"engine": p1.get("engine", ""), "dai": dai,
          "ms_khung_do": p1.get("ms_moi_khung")}
    if not dai:
        return None, cd
    cat = [0, dai["y0"], p1["rong"], dai["y1"] - dai["y0"]]
    p2 = chay(_runner(), {"video": duong_video, "fps": FPS_DOC, "cat": cat}, **kw)
    seg = phu_de_cung.dung_dong_thoi_gian(p2["khung"], cao_chu=dai["cao_chu"],
                                          fps=FPS_DOC, thoi_luong=thoi_luong,
                                          rong=p1["rong"])
    cd["ms_khung_doc"] = p2.get("ms_moi_khung")
    cd["so_dong"] = len(seg)
    if not seg:
        return None, cd
    tat_ca = "".join(s["text"] for s in seg)
    cd["ti_le_han"] = round(phu_de_cung.ti_le_chu_han(tat_ca), 3)
    return ({"segments": seg, "language": "zh", "engine": p1.get("engine", "ocr"),
             "alignment_status": "ocr_frame"}, cd)


# ── 3. Dinh tuyen ───────────────────────────────────────────────────────────

def dinh_tuyen(duong_video: str, *, che_do: str, ngon_ngu_khai: str,
               thoi_luong: float, ctx=None, chay=None) -> tuple[dict | None, dict]:
    """(ket qua dang engine, hoac None = chay ASR) + ban ghi dinh tuyen.

    Ban ghi dinh tuyen: `{"che_do", "nguon_loi", "ly_do": [..], ...}`.
    """
    from apps.asv_gpu.do_luong import venv

    che_do = chuan_che_do(che_do)
    dt: dict = {"che_do": che_do, "ly_do": []}
    if che_do == ASR:
        dt["nguon_loi"] = ASR
        return None, dt

    if che_do in (AUTO, EMBEDDED):
        tho = doc_phu_de_nhung(duong_video, ngon_ngu_khai=ngon_ngu_khai)
        if tho:
            dt.update(nguon_loi=EMBEDDED, **tho.pop("_dinh_tuyen"))
            return tho, dt
        if che_do == EMBEDDED:
            raise KhongCoNguon(_t('Video không có phụ đề nhúng dạng chữ.'))
        dt["ly_do"].append("khong_co_phu_de_nhung")

    if che_do == AUTO and ngon_ngu_khai not in ("", "zh"):
        dt["ly_do"].append("ocr_chi_do_cho_zh")
    else:
        try:
            tho, cd = doc_hardsub(duong_video, thoi_luong=thoi_luong, ctx=ctx, chay=chay)
            dt["ocr"] = cd
        except (venv.KhongKhaDung, venv.DoLuongLoi) as exc:
            if che_do == OCR:
                raise KhongCoNguon(_t('Bộ OCR chưa sẵn sàng trên máy chủ.')) from exc
            dt["ly_do"].append("ocr_khong_kha_dung")
            tho = None
        if tho and (che_do == OCR or dt["ocr"].get("ti_le_han", 0) >= TI_LE_HAN_TOI_THIEU):
            dt["nguon_loi"] = OCR
            return tho, dt
        if che_do == OCR:
            raise KhongCoNguon(_t('Không tìm thấy phụ đề cứng trong hình.'))
        if tho:
            dt["ly_do"].append("ocr_khong_phai_chu_han")
        elif "ocr_khong_kha_dung" not in dt["ly_do"]:
            dt["ly_do"].append("khong_co_hardsub")

    dt["nguon_loi"] = ASR
    return None, dt

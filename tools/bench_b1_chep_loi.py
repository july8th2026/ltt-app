"""bench_b1_chep_loi.py — cong B1: do NGHE CHEP (`transcribe`) vs hardsub.

    python tools/bench_b1_chep_loi.py --phim "<duong dan.mp4>"
    python tools/bench_b1_chep_loi.py --tu-kiem       # doi chung, khong can phim

## Mat xich DAU TIEN cua thang cong

Moi buoc sau dung tren van ban nguon ma `transcribe` tao ra. Mot loi o day khong
dung yen: no di vao ban dich, vao loi doc, vao QC ngu nghia, roi hien ra o mot chi
so khac han — va nguoi doc se di sua nham cho.

## ⚠️ CHAN LY NEN LA HARDSUB, VA NO KHONG HOAN HAO

Hardsub la **ban chu do nguoi lam phim viet**, khong phai ban ghi loi noi. Xem
`docs/auto_scan_video_final/B1_CHEP_LOI.md` §2 — gioi han do di kem MOI con so, ke
ca trong ban ghi JSON (`gioi_han`).

## ⛔ Nguong nam o TAI LIEU, ma chi doc lai

`NGUONG_WER`/`NGUONG_CER` phai khop `B1_CHEP_LOI.md` §1, va
`tests/test_3008::test_NGUONG_doc_tu_TAI_LIEU...` chot dieu do. Hai cho khai mot
con so ma khong ai bat khop la bay da ghi trong so may nay.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import unicodedata
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

#: Nguong DAT cua cong B1. ⛔ Khop `B1_CHEP_LOI.md` §1 — dung sua mot ben.
#:
#: ⚠️ `NGUONG_WER` duoc viet cho mot **ti le TU sai**. Do 24/09 cho thay tren van Han
#:    `jiwer` dem theo **DONG** (xem `do_hai_ban`), nen ap 0,25 cho con so do la ap
#:    mot nguong **chua tung duoc hieu chinh** cho don vi do — hai dong lech mot chu
#:    da cho 0,50. ⛔ Khong noi nguong, cung khong am tham dung no cho mot don vi
#:    khac: cau hoi dang o cho dieu phoi (`B1_CHEP_LOI.md` §1b).
NGUONG_WER = 0.25
NGUONG_CER = 0.12

#: CONG: lech so doan toi da. ⛔ **Doi VAI ngay 24/09, SAU khi thay so — khai thang.**
#:
#: 🔴 **Phan biet hai viec, vi mot cai bi cam va mot cai khong:**
#:      ⛔ NOI mot nguong sau khi thay so  = hop ly hoa mot ket qua toi. CAM.
#:      ⭐ SIET mot phep tu "chi bao" thanh "chan", khi so lieu cho ta mot LY DO
#:         ta chua tung co: duoc, **neu khai ro**.
#:
#:    Ly do moi: luc dat muc 0,20 ta **chua biet cu gop nay ton tai**. Phim 1 cho
#:    `lech_doan = 0,8922` — whisperx gop 9 cau thanh 1 (11 doan / 255,9 s = **23,3
#:    giay mot doan**) trong khi hardsub la 2,4 s. Nay ta biet no **giet buoc sau**:
#:    voi san pham long tieng, **phan doan CHINH LA san pham** — moi doan la mot khe
#:    de dat cau tieng Viet, va mot khe 23 giay lien mach thi `timing_align` khong
#:    con gi de canh.
#:
#: ⛔ Va con so `0,20` **khong doi**. Chi doi VAI cua no.
#:
#: 🔴 **CER mot minh de HO cau truc.** CER tinh tren van ban NOI LIEN nen no khong
#:    thay **so doan** — ma moi doan la **mot khe long tieng**. Mot ban chep gop hai
#:    cau lam mot, hoac tach mot cau lam ba, co the cho CER rat dep ma **canh thoi
#:    gian hong** — va buoc canh thoi gian se lanh hau qua, khong phai buoc chep loi.
#:    Luot nen da co trieu chung dung ho: **6 doan cho 107 giay**.
#:
#: ⚠️ **0,20 la con so dieu phoi CHON, CHUA HIEU CHINH** (khai thang 24/09). Nen no
#:    khong phan xu: vuot muc nay thi `dat` KHONG doi, nhung ban ghi bat phai co mot
#:    **loi giai thich bang van ban**. ⛔ "Da bao cao" khong phai "da giai thich".
NGUONG_LECH_DOAN = 0.20
#: Ten cu, giu de khong vo nguoi goi cu. ⛔ Dung dung cho ma moi.
MUC_NHIN_LECH_DOAN = NGUONG_LECH_DOAN

#: Gioi han cua chan ly nen, di kem MOI ban ghi. ⛔ Khong rut gon cau nay: nguoi
#: trich so doc JSON, khong doc `.md`.
GIOI_HAN_CHAN_LY_NEN = (
    "Hardsub la BAN CHU do nguoi lam phim viet, khong phai ban ghi loi noi: no co "
    "the RUT GON loi noi (bo tu dem, gop cau), viet lai cho gon man hinh, hoac bo "
    "han doan khong quan trong. Moi nguyen nhan do day WER LEN. ⇒ WER THAP la bang "
    "chung manh; WER CAO la bang chung YEU va phai soi tay truoc khi quy cho engine."
)

#: Phim BI LOAI khoi bench, kem ly do. ⛔ Mot phim khong co tieng noi se cho mot con
#: so trong nhu that bai cua engine.
PHIM_LOAI = {
    "真人气枪游戏红蓝双方对决": "B0 ghi 'khong chac co giong' — khong do duoc "
                                "duong nghe chep tren mot phim khong co tieng noi.",
}

_DAU_CAU = re.compile(r"[^\w\s]", re.UNICODE)
_NHIEU_TRANG = re.compile(r"\s+")


def chuan_hoa(chu: str) -> str:
    """Bo HINH THUC, giu NOI DUNG.

    ⛔ Duoc bo: dau cau, khoang trang thua, khac biet NFC/NFKC, hoa/thuong.
    ⛔ KHONG duoc bo: chu. Mot ham chuan hoa qua tay (vi du bo het ky tu khong phai
       Han) keo WER xuong mot cach GIA TAO — va no trong y het mot engine tot.

    ⚠️ **Khong tu che phep tach tu tieng Trung.** Van ban Han khong co khoang trang,
       nen WER theo "tu" tren tieng Trung it nghia hon CER; ca hai deu duoc bao cao
       va CER moi la so dang tin o day. Mot bo tach tu tu che se tao ra mot don vi
       do khong ai kiem duoc.
    """
    v = unicodedata.normalize("NFKC", str(chu or "")).lower()
    v = _DAU_CAU.sub(" ", v)
    return _NHIEU_TRANG.sub(" ", v).strip()


#: Khoi chu Han (CJK Unified Ideographs + phan mo rong hay gap).
_KHOI_HAN = ((0x4E00, 0x9FFF), (0x3400, 0x4DBF), (0xF900, 0xFAFF),
             (0x20000, 0x2A6DF))

#: Ti le chu Han de goi mot ban van la "van Han". 0,3 chu khong phai 0,5: mot ban
#: chep Han thuong co lan so, ten rieng Latin va dau cau — nhung mot ban van Latin
#: thuan thi ti le nay la 0.
TI_LE_HAN = 0.3


def la_van_han(chu: str) -> bool:
    """Ban van nay co phai **chu Han** khong — hoi TINH CHAT, khong suy tu ti le.

    🔴 **Ban dau ham nay khong ton tai, va cho goi no suy bang `so_ky_tu >= 2 *
       so_don_vi`.** Do la mot phep suy GIAN TIEP, va no sai ngay o ca thu hai:
       `"the quick brown fox jumps"` co 21 ky tu / 5 tu = 4,2 ⇒ bi xep thanh "dong".

    ⇒ Thu ta thuc su muon biet la *"van nay co khoang trang giua cac tu khong"*, va
      cach hoi thang la **dem chu Han**. Mot phep suy gian tiep se sai o dung nhung
      ca nguoi ta khong nghi toi — o day la moi van ban Latin co tu dai.
    """
    v = [c for c in str(chu or "") if not c.isspace()]
    if not v:
        return False
    han = sum(1 for c in v
              if any(a <= ord(c) <= b for a, b in _KHOI_HAN))
    return (han / len(v)) >= TI_LE_HAN


def _ky_tu(chu: str) -> str:
    """Chuoi ky tu cho CER: bo ca khoang trang."""
    return chuan_hoa(chu).replace(" ", "")


def do_hai_ban(tham_chieu: str, doc_ra: str) -> dict:
    """CER + ti le DON VI sai giua hai ban van. Dung `jiwer`, khong tu go Levenshtein.

    🔴 **`jiwer.wer` tach bang KHOANG TRANG, va van Han khong co khoang trang.**

       Do that 24/09 tren mot dong phu de Han:

           "深度解析跳伞慢了该怎么打"   ->  jiwer thay **1 'tu'**, that ra 12 KY TU
           hai ban chep lech DUNG MOT chu  ->  "wer" = **0,50**, CER = 0,0417

    ⇒ Cai ta goi la "WER" tren van Han thuc ra la **TI LE DONG SAI**. Goi no la WER
      la **dat ten rong hon thu no do** — dung bay `pham-vi-phep-do-hep-hon-loi-
      tuyen-bo`, va nguoi sau se so no voi WER cua bang xep hang the gioi, **hai thu
      khong cung don vi**.

    ⚠️ Va truong nay **doi nghia theo ngon ngu**: van Latin co khoang trang nen no
       DUNG la ti le tu sai; van Han thi la ti le dong sai. ⇒ Ban ghi luon kem
       `don_vi_ti_le` + `so_don_vi` de nguoi doc biet minh dang cam con so gi.
    """
    import jiwer

    tc, dr = chuan_hoa(tham_chieu), chuan_hoa(doc_ra)
    if not tc:
        return {"ti_le_don_vi_sai": float("nan"), "cer": float("nan"),
                "trong": True, "don_vi_ti_le": "khong xac dinh", "so_don_vi": 0}
    so_don_vi = len(tc.split())
    so_ky_tu = len(_ky_tu(tham_chieu))
    don_vi = "dong" if la_van_han(tc) else "tu"
    return {
        "ti_le_don_vi_sai": round(float(jiwer.wer(tc, dr)), 4),
        "cer": round(float(jiwer.cer(_ky_tu(tham_chieu), _ky_tu(doc_ra))), 4),
        "don_vi_ti_le": don_vi, "so_don_vi": so_don_vi, "so_ky_tu": so_ky_tu,
        "trong": False,
    }


def lam_hong(chu: str, *, ti_le: float = 0.3, seed: int = 0) -> str:
    """Lam hong `ti_le` so tu — DOI CHUNG cho chinh bo do.

    ⛔ Khong co phep nay thi mot WER thap co the chi la bo do hong, va no se IM LANG
       cho moi engine dat. Tat dinh theo `seed` de doi chung lap lai duoc.
    """
    tu = chuan_hoa(chu).split()
    if not tu:
        return ""
    r = random.Random(seed)
    so = max(1, int(len(tu) * ti_le))
    vi_tri = r.sample(range(len(tu)), min(so, len(tu)))
    for i in vi_tri:
        tu[i] = "x" + tu[i][::-1]
    return " ".join(tu)


def lech_doan(so_doan_asr: int, so_doan_hardsub: int) -> float:
    """|asr - hardsub| / hardsub. `nan` khi hardsub rong (khong chia cho 0).

    ⛔ Tra `nan`, KHONG tra 0: "khong lech" va "khong do duoc" la hai dieu khac
       nhau, va gop chung thanh mot so 0 lam mot phim khong co hardsub trong nhu
       mot phim khop hoan hao ("hai trang thai gop thanh mot gia tri").
    """
    if not so_doan_hardsub:
        return float("nan")
    return round(abs(int(so_doan_asr) - int(so_doan_hardsub))
                 / float(so_doan_hardsub), 4)


def _lech_dat(so_doan_asr: int, so_doan_hardsub: int) -> bool:
    """`lech_doan` co trong cong khong. `nan` (khong do duoc) ⇒ **KHONG dat**.

    ⛔ `nan <= x` la False trong Python, va o day do la hanh vi DUNG: mot phim
       khong co hardsub thi ta **khong biet** cau truc co dung khong, va "khong
       biet" khong duoc tinh la "dat".
    """
    import math

    l = lech_doan(so_doan_asr, so_doan_hardsub)
    return (not math.isnan(l)) and l <= NGUONG_LECH_DOAN


def gop_ket_qua(*, cer: float, so_dong_nguon: int, so_dong_hardsub: int,
                engine: str, co_card: bool, ti_le_don_vi_sai: float = float("nan"),
                don_vi_ti_le: str = "", phim: str = "", ghi_chu: str = "",
                giai_thich_lech_doan: str = "") -> dict:
    """Ban ghi MOT phim. ⛔ Luon mang `gioi_han`, `chan_ly_nen` va `don_vi_ti_le`.

    ⚠️ `dat` chi xet **CER**. Ti le don vi sai duoc BAO CAO nhung khong phan xu, vi
       nguong 0,25 duoc viet cho ti le TU sai va tren van Han don vi la DONG.
       ⛔ Do la mot cau hoi dang cho dieu phoi, khong phai mot nguong da noi.
    """
    return {
        "phim": phim,
        "ti_le_don_vi_sai": ti_le_don_vi_sai, "don_vi_ti_le": don_vi_ti_le,
        "cer": cer,
        "dat": bool(cer <= NGUONG_CER
                    and _lech_dat(so_dong_nguon, so_dong_hardsub)),
        "dat_xet_tren": ("CER <= NGUONG_CER VA lech_doan <= NGUONG_LECH_DOAN "
                         "(xem `don_vi_ti_le` ve ti le kia — no KHONG phan xu)"),
        "nguong": {"wer": NGUONG_WER, "cer": NGUONG_CER},
        "so_dong_nguon": so_dong_nguon, "so_dong_hardsub": so_dong_hardsub,
        # ── CAU TRUC: thu CER khong thay ────────────────────────────────────
        "so_doan_asr": so_dong_nguon,
        "so_doan_hardsub": so_dong_hardsub,
        "lech_doan": lech_doan(so_dong_nguon, so_dong_hardsub),
        "nguong_lech_doan": NGUONG_LECH_DOAN,
        "lech_doan_dat": _lech_dat(so_dong_nguon, so_dong_hardsub),
        "can_giai_thich_lech_doan": not _lech_dat(so_dong_nguon, so_dong_hardsub),
        # ⭐ Moc tham chieu TOT NHAT cho "mot khe dai bao nhieu": chinh hardsub —
        #    phan doan do NGUOI LAM PHIM chon cho chinh noi dung nay.
        "giay_moi_doan_asr": None, "giay_moi_doan_hardsub": None,
        "giai_thich_lech_doan": giai_thich_lech_doan,
        "engine": engine, "co_card": bool(co_card),
        # 🔑 HAI truong nay di theo con so, khong nam o cuoi bao cao.
        "chan_ly_nen": "hardsub",
        "gioi_han": GIOI_HAN_CHAN_LY_NEN,
        "ghi_chu": ghi_chu,
    }


def do_mot_phim(duong: str) -> dict:
    """Do WER/CER cua duong NGHE CHEP tren mot phim, lay hardsub lam doi chieu.

    ⚠️ **Chan ly nen la hardsub, va no co the RUT GON loi noi** — xem
       `GIOI_HAN_CHAN_LY_NEN`. Con so tra ve noi *"ASR va hardsub khac nhau bao
       nhieu"*, khong noi *"ASR sai bao nhieu"*; phep do nay **khong tach duoc**
       phan nao thuoc ve ai.

    Cach do: chay `transcribe` HAI lan tren cung mot phim —
    `nguon_loi=asr` (duong do) va `nguon_loi=ocr` (chan ly nen) — roi so.

    ⚠️ CHUA NOI vao khuon `chay_mot_buoc`: xem `B1_CHEP_LOI.md` §4. Ham nay hien
       tra ve mot ban ghi RONG kem `ly_do`, ⛔ khong tra ve mot con so gia.
    """
    ten = Path(duong).stem
    for xau, vi_sao in PHIM_LOAI.items():
        if xau in ten:
            return {"phim": ten, "bo_qua": True, "ly_do": vi_sao}
    return {"phim": ten, "chua_do": True,
            "ly_do": "buoc 4 cua Task 6 chua chay — xem B1_CHEP_LOI.md §4",
            "gioi_han": GIOI_HAN_CHAN_LY_NEN, "chan_ly_nen": "hardsub"}


def _tu_kiem() -> int:
    """Doi chung khong can phim: ban chep hong phai lam WER vot len."""
    that = "今天 我们 来 做 烤 牛肠 非常 好吃 大家 一起 来 看 看 吧"
    tot = do_hai_ban(that, that)
    hong = do_hai_ban(that, lam_hong(that, ti_le=0.3, seed=7))
    # Va MOT dong Han khong dau cach — de thay don vi doi nghia the nao.
    han = do_hai_ban("深度解析跳伞慢了该怎么打\n教你用细节操作来化解危机",
                     "深度解析跳伞慢了该怎么打\n教你用细节操作化解危机")
    print(json.dumps({"giong_het": tot, "lam_hong_30pt": hong,
                      "van_Han_lech_MOT_chu": han,
                      "nguong": {"cer": NGUONG_CER,
                                 "ti_le_don_vi_sai": "CHUA CO NGUONG"}},
                     ensure_ascii=False, indent=1))
    ok = tot["ti_le_don_vi_sai"] == 0.0 and hong["ti_le_don_vi_sai"] > 0.15
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--phim", default="")
    ap.add_argument("--tu-kiem", action="store_true")
    a = ap.parse_args(argv)
    if a.tu_kiem or not a.phim:
        return _tu_kiem()
    print(json.dumps(do_mot_phim(a.phim), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# ═════════════════════════════════════════════════════════════════════════════
# THƯỚC THAY THẾ cho `lech_doan` — ⛔ viết TRƯỚC khi đo, ngưỡng không chỉnh sau
#
# 🔴 **Vì sao `lech_doan` bị BỎ, không phải bị sửa.** Tiêm lỗi 24/09 (§8.3) cho:
#
#       v2 · cắt MÁY MÓC mỗi 2,0 s  ->  95 đoạn  ->  0,1121  ✅ XANH
#       v2 · cắt theo CÂU           ->  74 đoạn  ->  0,3084  ⛔ ĐỎ
#
#    Cổng **thưởng** đúng hành vi ràng buộc **cấm** (cắt giữa câu) và **phạt**
#    hành vi đúng. Luật đã ghi trong sổ máy này: *phép đo lệch về phía hành động
#    thì phải BỎ, không phải sửa*.
#
# ⭐ **Gốc bệnh:** `lech_doan` so **SỐ LƯỢNG**. Một tỉ số đếm không phân biệt được
#    *cắt đúng chỗ* với *cắt đủ nhiều* — nên **bất kỳ bộ băm ngu ngốc nào** ra
#    ~95 mẩu đều qua.
#
# ⛔ **Và bỏ nó KHÔNG làm B1 đạt.** Bỏ một thước hỏng ⇒ B1 **không còn cổng phân
#    đoạn nào** ⇒ **kém chắc chắn hơn**, không tốt hơn.
#
# ⛔ **KHÔNG gộp hai vế dưới đây thành một điểm F1.** Gộp lại là dựng lại đúng
#    bệnh vừa giết `lech_doan`: một số tổng hợp cho phép một vế tồi được vế kia
#    che. Báo **hai số**, cạnh nhau.
# ═════════════════════════════════════════════════════════════════════════════

#: Sai số khi đối chiếu một chỗ ngắt với ranh giới dòng phụ đề cứng.
SAI_SO_CHO_NGAT_S = 0.3

#: ⚠️ **NGƯỠNG DO TA ĐẶT** — ⛔ không có trong quy chuẩn nào, khai thẳng.
#:
#: Căn cứ: ràng buộc sản phẩm nói **cắt giữa câu TỆ HƠN gộp**. Một chỗ ngắt không
#: rơi vào ranh giới thật nào **là** một nhát cắt giữa câu. ⇒ Quá 10 % chỗ ngắt
#: sai là đã vi phạm ràng buộc một cách **hệ thống**, không phải nhiễu.
#: ⛔ Con số này viết ra **trước** khi đo bản của ta, và ⛔ không chỉnh sau.
NGUONG_CHINH_XAC_CHO_NGAT = 0.90

#: Trần độ dài một khe — *Netflix TTSG General Requirements*, bài **215758617**
#: (*"Maximum duration: 7 seconds per subtitle event"*). ⛔ Quy chuẩn **không cho
#: ngoại lệ** nào, nên ngưỡng là **1,00**: mọi đoạn phải ≤ 7,0 s.
KHE_TOI_DA_S = 7.0
NGUONG_TI_LE_TRONG_TRAN = 1.00

#: Sàn độ dài — cùng bài (*"Minimum duration: 5/6 of a second"*). ⭐ **CHỈ BÁO**,
#: ⛔ không phán xử: đoạn **cuối phim** có thể ngắn tự nhiên vì phim hết.
KHE_TOI_THIEU_S = 5.0 / 6.0

#: *Chinese (Simplified)*, bài **215986007** (*"Up to 9 characters per second"*).
#: ⭐ **CHỈ BÁO**: nó nói về **bản dịch tiếng Việt** sẽ đặt vào khe, mà bản đó
#: **chưa tồn tại** ở bước này. ⛔ Không được dùng phán xử ở B1.
KY_TU_MOI_GIAY = 9


def _moc_ranh_gioi(doan: list[dict]) -> list[float]:
    ra: set[float] = set()
    for d in doan:
        for khoa in ("bat", "ket"):
            g = d.get(khoa)
            if isinstance(g, (int, float)):
                ra.add(round(float(g), 3))
    return sorted(ra)


def chinh_xac_cho_ngat(doan_asr: list[dict], doan_hardsub: list[dict]) -> dict:
    """VẾ 1 — bao nhiêu phần chỗ ngắt CỦA TA rơi trúng một ranh giới thật.

    Trả lời đúng một câu: *"ta có cắt giữa câu không"*. Bộ băm mỗi 2,0 giây
    **chết** ở đây, vì chỗ ngắt của nó rơi vào giữa lời nói.

    ⚠️ **GIỚI HẠN, ⛔ phải đọc cùng con số:** phép này đo thứ ta **CẤM**, ⛔ không
       đo thứ ta **CẦN**. Nó **không phạt việc cắt QUÁ ÍT** — một bản ghi có đúng
       **một** đoạn dài 25 giây, mà hai đầu trùng đầu/cuối phim, vẫn đạt **1,00**.
       Chính `do_dai_theo_quy_chuan` (vế 2) gánh phần đó. ⇒ ⛔ Đừng đọc vế này một
       mình, và ⛔ đừng gộp hai vế thành một điểm.
    """
    ta = _moc_ranh_gioi(doan_asr)
    that = _moc_ranh_gioi(doan_hardsub)
    if not ta or not that:
        return {"ti_le": None, "dat": False,
                "ly_do": "một bên không có ranh giới nào — ⛔ không kết luận"}
    khop = sum(1 for m in ta
               if any(abs(m - h) <= SAI_SO_CHO_NGAT_S for h in that))
    ti_le = round(khop / len(ta), 4)
    return {"ti_le": ti_le, "khop": khop, "tong_cho_ngat": len(ta),
            "tong_ranh_gioi_that": len(that), "sai_so_s": SAI_SO_CHO_NGAT_S,
            "nguong": NGUONG_CHINH_XAC_CHO_NGAT,
            "nguong_do_ai_dat": "TA ĐẶT — ⛔ không có trong quy chuẩn nào",
            "dat": ti_le >= NGUONG_CHINH_XAC_CHO_NGAT,
            "gioi_han": "⛔ KHÔNG phạt việc cắt quá ít: một đoạn 25 s vẫn có thể "
                        "đạt 1,00. Vế `do_dai_theo_quy_chuan` gánh phần đó."}


def do_dai_theo_quy_chuan(doan_asr: list[dict]) -> dict:
    """VẾ 2 — độ dài đoạn so với quy chuẩn. ⭐ **KHÔNG cần chân lý nền nào.**

    Tự nó đứng được: quy chuẩn nói một khe phụ đề tối đa **7,0 giây**
    (Netflix TTSG **215758617**), và điều đó đúng bất kể phim nào. Gộp-tất và
    khối 30 giây **chết** ở đây.

    ⛔ Ngưỡng là **1,00** vì quy chuẩn không cho ngoại lệ nào — ⛔ không phải một
       con số ta chọn cho dễ qua.
    """
    do_dai = []
    for d in doan_asr:
        b, k = d.get("bat"), d.get("ket")
        if isinstance(b, (int, float)) and isinstance(k, (int, float)):
            do_dai.append(float(k) - float(b))
    if not do_dai:
        return {"ti_le_trong_tran": None, "dat": False,
                "ly_do": "không đoạn nào có mốc — ⛔ không kết luận"}
    trong_tran = sum(1 for g in do_dai if g <= KHE_TOI_DA_S)
    ti_le = round(trong_tran / len(do_dai), 4)
    return {"ti_le_trong_tran": ti_le, "so_doan": len(do_dai),
            "so_qua_tran": len(do_dai) - trong_tran,
            "dai_nhat_s": round(max(do_dai), 2),
            "trung_binh_s": round(sum(do_dai) / len(do_dai), 2),
            "khe_toi_da_s": KHE_TOI_DA_S, "nguong": NGUONG_TI_LE_TRONG_TRAN,
            "nguon_nguong": "Netflix TTSG General Requirements, bài 215758617",
            "dat": ti_le >= NGUONG_TI_LE_TRONG_TRAN,
            # ⭐ CHỈ BÁO, ⛔ không phán xử — xem hằng số.
            "chi_bao_duoi_san": sum(1 for g in do_dai if g < KHE_TOI_THIEU_S),
            "khe_toi_thieu_s": round(KHE_TOI_THIEU_S, 4)}


def cap_thuoc_phan_doan(doan_asr: list[dict], doan_hardsub: list[dict]) -> dict:
    """HAI số cạnh nhau. ⛔ **Không có số thứ ba gộp chúng lại.**

    ⛔ Cố ý **không** trả về một điểm tổng hợp (F1, trung bình, tích). Gộp lại là
       dựng lại đúng bệnh đã giết `lech_doan`: một vế tồi được vế kia che.
    """
    ve1 = chinh_xac_cho_ngat(doan_asr, doan_hardsub)
    ve2 = do_dai_theo_quy_chuan(doan_asr)
    return {"chinh_xac_cho_ngat": ve1, "do_dai_theo_quy_chuan": ve2,
            "dat": bool(ve1.get("dat")) and bool(ve2.get("dat")),
            "⛔": "hai vế đọc RIÊNG. Không gộp thành một điểm."}

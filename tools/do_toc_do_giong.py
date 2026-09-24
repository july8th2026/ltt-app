"""Do PHAN RA thoi gian cua giai doan VOICE_SYNTHESIS: TTS hay LLM viet lai?

## Cau hoi no tra loi

Luot nghiem thu nen v3 (23/09, `docs/auto_scan_video_final/bang_chung/NEN_V3.md`)
do duoc `voice_synthesis` = **937-943 giay** cho mot phim **107 giay**, voi 6
doan, 17 luot doc va 11 luot `rut_ngan_cho_vua` (50.144 token). Bao cao do KHONG
tach duoc con so ay: no chi biet tong.

⛔ Va khong tach duoc thi khong sua duoc. "Rut ngan bac thang" va "tang toc may
   sinh tieng" la hai viec khac han nhau, va chon nham mot cai la mot pha lam
   viec doi lay mot phan tram.

## Cach do

Dung **chinh sau doan cua luot ay** — van ban that, khe that, ban goc tieng
Trung that — roi goi tung cua MOT lan:

    TTS : `giong_noi.doc_mot_doan` -> giay tuong, giay am thanh, RTF, am tiet/giay
    LLM : `ai.goi(RUT_NGAN_CHO_VUA)` -> giay tuong, token vao/ra, khoi suy nghi

⭐ Do RIENG hai cua chu khong do mot vong lap: mot vong lap tra ve mot tong, va
   mot tong la dung thu ta da co.

## Vi sao `am tiet/giay` co mat o day

`ngon_ngu.CUM[vi]["nhip"]` noi voi model rang tieng Viet doc "khoang 4,5 am
tiet/giay". Neu con so do lech that, thi **moi cau cua luot dau deu dai sai**,
va bac thang nan chi dang di don mot cai do dat sai tu goc. Cung mot luot goi
TTS tra loi duoc ca hai cau hoi, nen do luon.

## Bien can

`LTT_ASV_POOL_URL` (cho phan LLM) va `LTT_VOICE_SIDECAR_TOKEN` (cho phan TTS) —
nap tu `app.env` boi nguoi goi. ⛔ Cong cu nay khong doc `app.env`, khong in mot
gia tri bi mat nao.

Phan TTS giu khoa `may_tao_tieng` cua `cua_so_yen` (CLAUDE.md luat 3).
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import statistics
import sys
import tempfile
import time

GOC = pathlib.Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

#: Sau doan THAT cua luot nen v3 (`nen_v3_us_smart_localize.json`):
#: `goc` = ban chep loi ASR tieng Trung · `chu` = cau tieng Viet may DA doc
#: · `khe` = do dai doan trong ban goc (giay).
#:
#: ⛔ Khong bia them doan nao: co lo cua giai doan nay la SO DOAN CUA PHIM, va
#:    mot doan tu nghi ra se keo trung binh ve phia do dai toi chon.
DOAN_THAT: tuple[dict, ...] = (
    {"ma": "seg_0001", "khe": 19.879,
     "goc": "如果跳散慢呢该怎么打这人落地房子都不进那他肯定是捡到枪了现在最好的办法"
            "就是赶紧进楼来把枪啊光子这人肯定会往里面冲架着门口往左边走用提炼枪让他"
            "来接子弹跳散慢会让我们错失进攻的机会接下来别人会源源不断的进攻我们一定"
            "要想办法把楼给守住手滑了不好意思",
     "chu": "Nếu nhảy dù chậm thì đánh ra sao? Hắn đáp xuống mà không vào nhà, "
            "chắc hẳn đã nhặt được súng. Cách tốt nhất lúc này là lao thẳng vào "
            "trong lấy súng ngay, Photon. Hắn sẽ chắc chắn xông vào, ta canh cửa "
            "sẵn, vòng sang bên trái, giữ súng nhắm sẵn, bắt hắn phải nhận đạn. "
            "Nhảy chậm sẽ khiến ta mất cơ hội tấn công, địch liên tục áp lên, "
            "mình phải giữ cho được tòa nhà. Lỡ tay rồi, xin lỗi với mọi người nhé."},
    {"ma": "seg_0002", "khe": 17.172,
     "goc": "楼梯来脚步了我们现在这个血量可以说天崩开局如果想完成极限反杀那接下来这个"
            "操作你们一定要学一下趁敌人还没上来咱们直接趴下用盒子当掩体他就发现不了"
            "我们开个玩笑啊盒子是不能当掩体的这里我们特意往墙角多走那两步才趴下为的"
            "就是卡敌人视野差让他第一时间看不到我们位置",
     "chu": "Cầu thang có tiếng chân rồi. Máu hiện tại có thể nói là mở đầu cực "
            "tệ. Muốn phản sát cực đại thì thao tác sau này các bạn phải học. "
            "Nhân địch chưa lên, mình nằm xuống, dùng thùng làm vật cản, hắn khó "
            "thấy. Trêu thôi, thùng không cản được. Mình đi thêm vài bước sát góc "
            "rồi mới nằm, để né góc nhìn địch, khiến hắn không thấy mình ngay."},
    {"ma": "seg_0003", "khe": 13.818,
     "goc": "这个时候你们仔细听楼下又来人了打药的时候不要待在原地镇敌人还没到我们可以"
            "先把有利的位置选下来只要我们占据了地形优势来再多的人也不用怕你们玩的时候"
            "千万别冲这么快速度越快损失的反应时间就越多一旦我们拉出去这人几乎没有反应时间",
     "chu": "Lúc này nghe kỹ, dưới lầu lại có người. Khi uống thuốc, đừng đứng "
            "yên. Địch chưa tới, mình chọn trước vị trí tốt. Có lợi thế địa hình "
            "thì địch đông mấy cũng không sợ. Các bạn chơi đừng lao nhanh thế. "
            "Tốc độ càng cao, thời gian phản ứng càng ít. Một khi mình kéo ra, "
            "địch gần như không kịp phản ứng."},
    {"ma": "seg_0004", "khe": 14.553,
     "goc": "看到没有这就是纯白给这个时候外面的脚步越来越多全都是冲着我们来的趁现在"
            "赶紧把人补了这里要注意不要把大量的时间用在补人身上没补掉就赶紧回头小心"
            "身后的人真正的高手从来都不会盲目进攻先掐个假雷看他会如何应对",
     "chu": "Thấy chưa, đây là tự chui đầu vào bẫy. Lúc này tiếng chân ngoài kia "
            "càng ngày càng nhiều, toàn nhắm vào mình. Nhân lúc này nhanh xử "
            "người đi. Chú ý, đừng tốn quá nhiều thời gian hạ địch. Chưa hạ được "
            "thì quay lại ngay, đề phòng người phía sau. Cao thủ thật chẳng bao "
            "giờ tấn công mù quáng, thả quả lựu đạn giả trước để xem địch phản "
            "ứng thế nào."},
    {"ma": "seg_0005", "khe": 25.542,
     "goc": "这人很稳啊看来是遇到高手了哎不是这哥们居然是来救人的这人的操作你们可千万"
            "别学啊楼下还有脚步他们不敢上来那我们就直接掐雷此一听有人又跳伞回来了至于"
            "这里的细节咱们直接把雷丢在二楼门口防止楼顶的人跳下来真是说什么来什么他冲"
            "这么快肯定是想下楼帮队友假装本人把他队友骗上来这人也是犯了同样的错误冲太"
            "快就会失去开枪的机会",
     "chu": "Người này vững quá, xem ra gặp cao thủ rồi. À không, tên này lại là "
            "đi cứu người. Cách chơi của hắn, các bạn đừng học. Dưới lầu vẫn còn "
            "tiếng chân, địch không dám lên, thì mình thả lựu đạn trước. Nghe lại "
            "đây, có người nhảy dù trở lại. Chi tiết chỗ này, mình ném thẳng lựu "
            "đạn ra cửa tầng hai, phòng người trên sân thượng nhảy xuống. Thật "
            "đúng là nói gì có nấy. Hắn lao nhanh thế, chắc muốn xuống dưới cứu "
            "đội bạn. Giả làm chính chủ để lừa đối thủ lên. Người này cũng sai y "
            "hệt, lao quá nhanh thì sẽ mất cơ hội nổ súng."},
    {"ma": "seg_0006", "khe": 4.553,
     "goc": "直接拿下最后问你们个问题如果攻楼的时候遇到这种卡着楼梯的你们会怎么办",
     "chu": "Xử luôn. Cuối cùng hỏi các bạn: khi tấn công tòa nhà gặp địch canh "
            "cầu thang thế này, bạn sẽ làm gì?"},
)

#: Giong cua luot nen v3 — mot giong DUNG SAN cua `ltt_voice`.
GIONG_MAC_DINH = "Minh Đức"


def dem_am_tiet(chu: str) -> int:
    """Am tiet tieng Viet = tu cach nhau bang khoang trang (bo dau cau rieng).

    ⭐ Dung voi tieng Viet vi chinh ta cua no la **am tiet roi**: moi am tiet
       mot tu. Khong dung cho tieng Anh — cho do dem TU, va `ngon_ngu.CUM[en]`
       cung khai nhip theo tu.
    """
    return len([t for t in re.findall(r"\S+", str(chu or "")) if re.search(r"\w", t)])


# ══════════════════════════════════════════════════════════════════════════════
#  Cua TTS
# ══════════════════════════════════════════════════════════════════════════════

def _do_tts(doan: tuple[dict, ...], *, giong: str, vong: int,
            giu_wav: str = "") -> list[dict]:
    """Goi may sinh tieng THAT, mot doan mot luot. Tra ve mot dong moi luot."""
    from apps.auto_scan_video import giong_noi

    if not giong_noi.san_sang():
        print("  [!!] Sidecar LTT VOICE khong san sang. Dung phan TTS.")
        return []

    voice_id, preset = giong_noi.tach_ma_giong(giong)
    print(f"  giong: voice_id={voice_id!r} preset={preset!r}")
    ra: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="do_toc_do_") as tam:
        for v in range(vong):
            for m in doan:
                tep = pathlib.Path(tam) / f"{m['ma']}_{v}.wav"
                t0 = time.monotonic()
                try:
                    wav, _h = giong_noi.doc_mot_doan(
                        m["chu"], ref_b64=None, preset=preset or None)
                    tep.write_bytes(wav)
                    giay_am = giong_noi.kiem_tep_tieng(str(tep))
                    nhan = "ok"
                except Exception as exc:                    # noqa: BLE001
                    giay_am = 0.0
                    nhan = f"{type(exc).__name__}: {exc}"
                tuong = time.monotonic() - t0
                n = dem_am_tiet(m["chu"])
                dong = {"ma": m["ma"], "vong": v, "nhan": nhan,
                        "giay_tuong": round(tuong, 2),
                        "giay_am": round(giay_am, 2),
                        "rtf": round(tuong / giay_am, 3) if giay_am else 0.0,
                        "am_tiet": n,
                        "am_tiet_moi_giay": round(n / giay_am, 3) if giay_am else 0.0,
                        "khe": m["khe"], "chu": m["chu"],
                        "lech_khe": round((giay_am - m["khe"]) / m["khe"], 4)}
                if giu_wav and nhan == "ok":
                    d16 = pathlib.Path(giu_wav) / f"cu_{m['ma']}_{v}.wav"
                    d16.parent.mkdir(parents=True, exist_ok=True)
                    if _dung_16k(str(tep), str(d16)):
                        dong["tep_16k"] = str(d16)
                ra.append(dong)
                print(f"    TTS {m['ma']} v{v}: tuong {tuong:6.1f}s  am "
                      f"{giay_am:6.2f}s  RTF {dong['rtf']:5.2f}  "
                      f"{dong['am_tiet_moi_giay']:.2f} am tiet/giay  "
                      f"lech khe {dong['lech_khe']:+.1%}  {nhan[:40]}", flush=True)
    return ra


# ══════════════════════════════════════════════════════════════════════════════
#  Cua LLM
# ══════════════════════════════════════════════════════════════════════════════

def _mo_db():
    """SQLite TAM + khoa `ltt_llm` chep tu pool that (chi doc).

    Khuon lay nguyen tu `tools/do_ngan_sach_chuyen_loi_thoai.py`: mot CSDL tam
    de `api_pool` co cho ghi `provider_state`, con khoa thi doc tu pool that —
    `error_count` cua luot do khong lam ban thong ke khoa production.
    """
    tam = pathlib.Path(tempfile.mkdtemp(prefix="ltt_do_toc_do_")) / "do.db"
    os.environ["LTT_DATABASE_URL"] = f"sqlite:///{tam.as_posix()}"
    import platform_core.db as dbmod

    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())

    from tests.fixtures import asv_e2e

    so = asv_e2e.nap_khoa_pool(db)
    db.commit()
    print(f"  [OK] nap {so} dong khoa `ltt_llm` tu pool that (chi doc)")
    return db, so


def _do_llm(doan: tuple[dict, ...], *, vong: int, cho_ban: float,
            ban_toi_da: int, tts: list[dict],
            muc_nghi: str | None = None) -> list[dict]:
    """Goi `RUT_NGAN_CHO_VUA` THAT, mot doan mot luot."""
    from apps.auto_scan_video import ai, nan_cho_vua

    db, so_khoa = _mo_db()
    if not so_khoa:
        print("  [!!] Pool that khong co khoa `ltt_llm` nao dung duoc. Dung.")
        return []

    # Do dai DO DUOC cua doan — lay tu phan TTS neu co, khong thi lay khe*1,2
    # (mot luot khong vua dien hinh cua luot nen v3).
    do_duoc = {}
    for d in tts:
        if d["nhan"] == "ok" and d["giay_am"]:
            do_duoc.setdefault(d["ma"], []).append(d["giay_am"])

    ra: list[dict] = []
    for v in range(vong):
        for m in doan:
            giay = (statistics.mean(do_duoc[m["ma"]]) if do_duoc.get(m["ma"])
                    else m["khe"] * 1.2)
            msg = nan_cho_vua.loi_nhac_nan(
                m, chu_hien_tai=m["chu"], giay_do_duoc=giay, khe=m["khe"],
                ngon_ngu_dich="vi")
            for lan in range(ban_toi_da + 1):
                t0 = time.monotonic()
                try:
                    kq = ai.goi(db, ai.RUT_NGAN_CHO_VUA, msg,
                                muc_nghi=muc_nghi)
                    chu_moi = nan_cho_vua.doc_nan(
                        ai.doc_ket_qua(kq, ai.RUT_NGAN_CHO_VUA))
                    nhan = "ok"
                except Exception as exc:                    # noqa: BLE001
                    kq = {}
                    chu_moi = ""
                    nhan = f"{type(exc).__name__}: {exc}"
                tuong = time.monotonic() - t0
                if "MayBan" not in nhan:
                    break
                if lan >= ban_toi_da:
                    print("     [!!] May B BAN het so lan cho. Dung.")
                    return ra
                print(f"     [..] May B BAN ({tuong:.1f}s). Cho {cho_ban:.0f}s "
                      f"roi thu lai chinh luot nay.", flush=True)
                time.sleep(cho_ban)

            sd = kq.get("su_dung")
            dong = {"ma": m["ma"], "vong": v, "nhan": nhan,
                    "giay_tuong": round(tuong, 2),
                    "token_vao": int(getattr(sd, "token_vao", 0) or 0),
                    "token_ra": int(getattr(sd, "token_ra", 0) or 0),
                    "suy_nghi_ky_tu": len(str(kq.get("suy_nghi") or "")),
                    "finish_reason": str(kq.get("finish_reason") or ""),
                    "muc_nghi": str(muc_nghi or "(mac dinh may chu)"),
                    # ⭐ CAU DA VIET LAI, khong chi so token: mot ban do toc do
                    #    khong duoc phep im lang ve chat luong cua thu nhanh hon.
                    "chu_moi": chu_moi,
                    "am_tiet_vao": dem_am_tiet(m["chu"]),
                    "am_tiet_ra": dem_am_tiet(chu_moi)}
            ra.append(dong)
            print(f"    LLM {m['ma']} v{v}: tuong {tuong:6.1f}s  "
                  f"vao {dong['token_vao']:6,}  ra {dong['token_ra']:6,}  "
                  f"suy nghi {dong['suy_nghi_ky_tu']:6,} ky tu  "
                  f"am tiet {dong['am_tiet_vao']:3d}->{dong['am_tiet_ra']:3d}  "
                  f"{dong['finish_reason'] or '-':8s} {nhan[:40]}", flush=True)
    return ra


# ══════════════════════════════════════════════════════════════════════════════
#  Cua VONG DAU — viet loi thoai roi DOC NO, dung chuoi that
# ══════════════════════════════════════════════════════════════════════════════

def _dung_16k(nguon: str, dich: str) -> bool:
    """WAV 16 kHz mono cho bo do `giong` (khuon cua `tools/do_giong_hieu_chinh`)."""
    import subprocess

    r = subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error",
                        "-i", nguon, "-ac", "1", "-ar", "16000", dich],
                       capture_output=True)
    return r.returncode == 0


def _do_vong_dau(doan: tuple[dict, ...], *, giong: str, vong: int,
                 cho_ban: float, ban_toi_da: int,
                 giu_wav: str = "") -> list[dict]:
    """`chuyen_loi_thoai` THAT -> `doc_mot_doan` THAT -> co vua khe khong.

    🔑 Day la phep do tra loi cau *"ban sua co an khong"*: no di **ca hai** cua
       cua vong dau, tren dung sau doan cua luot nen v3, va dem so doan phai
       nan. Do rieng loi nhac (dem am tiet cua van ban) khong tra loi duoc, vi
       cau hoi that la *"doc ra co vua khong"*.
    """
    from apps.auto_scan_video import ai, giong_noi, long_tieng, nan_cho_vua

    if not giong_noi.san_sang():
        print("  [!!] Sidecar LTT VOICE khong san sang. Dung.")
        return []
    db, so_khoa = _mo_db()
    if not so_khoa:
        print("  [!!] Pool that khong co khoa `ltt_llm` nao dung duoc. Dung.")
        return []

    _voice_id, preset = giong_noi.tach_ma_giong(giong)
    # Hinh dang `ban_ghi_giu.doan` ma `long_tieng.loi_nhac` doi.
    lo = [{"ma": m["ma"], "chu": m["goc"], "bat": 0.0, "ket": m["khe"]}
          for m in doan]
    ra: list[dict] = []

    with tempfile.TemporaryDirectory(prefix="do_vong_dau_") as tam:
        for v in range(vong):
            msg = long_tieng.loi_nhac(lo, tat_ca=lo, ngon_ngu_goc="zh",
                                      dac_diem_giong={}, ngon_ngu_dich="vi")
            for lan in range(ban_toi_da + 1):
                t0 = time.monotonic()
                try:
                    kq = ai.goi(db, ai.CHUYEN_LOI_THOAI, msg)
                    chuyen = long_tieng.doc_chuyen(
                        ai.doc_ket_qua(kq, ai.CHUYEN_LOI_THOAI),
                        {m["ma"] for m in doan})
                    nhan = "ok"
                except Exception as exc:                    # noqa: BLE001
                    chuyen = {}
                    nhan = f"{type(exc).__name__}: {exc}"
                giay_viet = time.monotonic() - t0
                if "MayBan" not in nhan:
                    break
                if lan >= ban_toi_da:
                    print("     [!!] May B BAN het so lan cho. Dung.")
                    return ra
                print(f"     [..] May B BAN ({giay_viet:.1f}s). Cho {cho_ban:.0f}s.",
                      flush=True)
                time.sleep(cho_ban)

            print(f"    VIET v{v}: {giay_viet:.1f}s cho ca lo {len(doan)} doan "
                  f"({nhan[:60]})", flush=True)
            if nhan != "ok":
                continue

            for m in doan:
                chu = str((chuyen.get(m["ma"]) or {}).get("chu") or "")
                tep = pathlib.Path(tam) / f"{m['ma']}_{v}.wav"
                t0 = time.monotonic()
                try:
                    wav, _h = giong_noi.doc_mot_doan(chu, ref_b64=None,
                                                     preset=preset or None)
                    tep.write_bytes(wav)
                    giay_am = giong_noi.kiem_tep_tieng(str(tep))
                    nhan_d = "ok"
                except Exception as exc:                    # noqa: BLE001
                    giay_am = 0.0
                    nhan_d = f"{type(exc).__name__}: {exc}"
                tuong = time.monotonic() - t0
                le = nan_cho_vua.lech(giay_am, m["khe"]) if giay_am else 0.0
                dong = {"ma": m["ma"], "vong": v, "nhan": nhan_d, "chu": chu,
                        "giay_viet_ca_lo": round(giay_viet, 2),
                        "giay_tuong": round(tuong, 2),
                        "giay_am": round(giay_am, 2),
                        "am_tiet": dem_am_tiet(chu),
                        "khe": m["khe"],
                        "lech_khe": round(le, 4),
                        "can_nan": bool(nan_cho_vua.can_nan(giay_am, m["khe"]))
                        if giay_am else True}
                # ⭐ Giu tep 16 kHz de bo do WER/CER (`--che-do wer`) cham tren
                #    DUNG tieng vua sinh — khong phai mot ban do lai sau do.
                if giu_wav and nhan_d == "ok":
                    d16 = pathlib.Path(giu_wav) / f"{m['ma']}_{v}.wav"
                    d16.parent.mkdir(parents=True, exist_ok=True)
                    if _dung_16k(str(tep), str(d16)):
                        dong["tep_16k"] = str(d16)
                ra.append(dong)
                print(f"    DOC {m['ma']} v{v}: am {giay_am:6.2f}s  khe "
                      f"{m['khe']:6.2f}s  lech {le:+7.1%}  "
                      f"{'CAN NAN' if dong['can_nan'] else 'vua   '}  "
                      f"{dong['am_tiet']:3d} am tiet  {nhan_d[:30]}", flush=True)
    return ra


# ══════════════════════════════════════════════════════════════════════════════
#  Bao cao
# ══════════════════════════════════════════════════════════════════════════════

def _do_wer(goi_vong_dau: dict) -> dict:
    """Cham WER/CER cua bo do `giong` tren tieng VUA SINH o `--che-do vong-dau`.

    🔑 Cau hoi no tra loi: *"cau ngan hon co bi doc sai hon khong"*. Nguong o
       `sua_chua.NGUONG_DOC_SAI` da hieu chinh tren 50 doan that (lan `giong`);
       mot ban sua toc do khong duoc lam no do.
    """
    from apps.asv_gpu.do_luong import bo_do
    from apps.auto_scan_video import sua_chua

    # ⭐ Nhan CA hai nguon: `vong-dau` (van ban MOI) va `tts` (van ban CU cua
    #    luot nen v3) — de "truoc" va "sau" duoc cham bang cung mot bo do.
    # ⛔ Nhan phai mang theo NGUON: hai ve dung cung bo ma doan (`seg_0001`...),
    #    nen mot nhan `seg_0001_0` cho ca hai lam mot ve **de len ve kia** va
    #    bang ket qua tro thanh mot bang khong biet no dang noi ve van ban nao.
    nguon = [("moi", d) for d in goi_vong_dau.get("vong_dau") or []] + \
            [("cu", d) for d in goi_vong_dau.get("tts") or []]
    ds = [{"ma": f"{n}_{d['ma']}_{d.get('vong', 0)}", "tep": d["tep_16k"],
           "chu": d["chu"]} for n, d in nguon if d.get("tep_16k")]
    if not ds:
        print("  [!!] Khong co tep 16k nao (chay `--che-do vong-dau --giu-wav`).")
        return {}
    kq = bo_do.chay_tat_ca(bo_do.DauVao(doan_tieng=ds, ngon_ngu_dich="vi"))
    g = kq.get("giong") or {}
    if g.get("trang_thai") != bo_do.XONG:
        print(f"  [!!] bo do `giong`: {g.get('trang_thai')} "
              f"({str(g.get('ly_do') or '')[:120]})")
        return {"trang_thai": g.get("trang_thai"), "ly_do": g.get("ly_do")}

    nguong = sua_chua.NGUONG_DOC_SAI["vi"]
    tung = []
    for ma, r in (g.get("ket_qua") or {}).items():
        wer, cer = float(r.get("wer", 0)), float(r.get("cer", 0))
        doc_sai = wer > nguong["wer"] and cer > nguong["cer"]
        tung.append({"ma": ma, "wer": round(wer, 4), "cer": round(cer, 4),
                     "doc_sai": doc_sai, "doc_ra": str(r.get("doc_ra") or "")})
        print(f"    WER {ma}: wer {wer:.4f}  cer {cer:.4f}  "
              f"{'DOC SAI' if doc_sai else 'dat'}")
    wers = [d["wer"] for d in tung]
    cers = [d["cer"] for d in tung]
    return {"nguong": dict(nguong), "so_doan": len(tung),
            "so_doc_sai": sum(1 for d in tung if d["doc_sai"]),
            "wer_lon_nhat": round(max(wers), 4) if wers else None,
            "wer_trung_binh": round(statistics.mean(wers), 4) if wers else None,
            "cer_lon_nhat": round(max(cers), 4) if cers else None,
            "cer_trung_binh": round(statistics.mean(cers), 4) if cers else None,
            "tung_doan": tung}


def _tom_tat_vong_dau(vd: list[dict]) -> dict:
    ok = [d for d in vd if d["nhan"] == "ok" and d["giay_am"]]
    if not ok:
        return {}
    return {
        "so_doan": len(ok),
        "so_can_nan": sum(1 for d in ok if d["can_nan"]),
        "ti_le_can_nan": round(sum(1 for d in ok if d["can_nan"]) / len(ok), 3),
        "lech_khe_trung_binh": round(statistics.mean(
            d["lech_khe"] for d in ok), 4),
        "lech_khe_lon_nhat": round(max(d["lech_khe"] for d in ok), 4),
        "lech_khe_nho_nhat": round(min(d["lech_khe"] for d in ok), 4),
        "giay_tts_tong": round(sum(d["giay_tuong"] for d in ok), 1),
    }


def _tom_tat(tts: list[dict], llm: list[dict]) -> dict:
    ok_t = [d for d in tts if d["nhan"] == "ok" and d["giay_am"]]
    ok_l = [d for d in llm if d["nhan"] == "ok"]
    t = {}
    if ok_t:
        t = {
            "so_luot": len(ok_t),
            "giay_tuong_trung_binh": round(statistics.mean(
                d["giay_tuong"] for d in ok_t), 2),
            "giay_tuong_tong": round(sum(d["giay_tuong"] for d in ok_t), 1),
            "giay_am_tong": round(sum(d["giay_am"] for d in ok_t), 1),
            "rtf_trung_binh": round(statistics.mean(d["rtf"] for d in ok_t), 3),
            "am_tiet_moi_giay_trung_binh": round(statistics.mean(
                d["am_tiet_moi_giay"] for d in ok_t), 3),
            "am_tiet_moi_giay_nho_nhat": round(min(
                d["am_tiet_moi_giay"] for d in ok_t), 3),
            "am_tiet_moi_giay_lon_nhat": round(max(
                d["am_tiet_moi_giay"] for d in ok_t), 3),
        }
        if len(ok_t) > 1:
            t["am_tiet_moi_giay_do_lech_chuan"] = round(statistics.stdev(
                d["am_tiet_moi_giay"] for d in ok_t), 3)
    l = {}
    if ok_l:
        l = {
            "so_luot": len(ok_l),
            "giay_tuong_trung_binh": round(statistics.mean(
                d["giay_tuong"] for d in ok_l), 2),
            "giay_tuong_tong": round(sum(d["giay_tuong"] for d in ok_l), 1),
            "token_ra_trung_binh": round(statistics.mean(
                d["token_ra"] for d in ok_l), 1),
            "suy_nghi_ky_tu_trung_binh": round(statistics.mean(
                d["suy_nghi_ky_tu"] for d in ok_l), 1),
        }
    ra = {"tts": t, "llm": l}
    # 🔑 Phan ra cua luot nen v3: 17 luot TTS + 11 luot LLM = 937-943 giay.
    #    Ta do MOT luot moi cua, roi NHAN — va noi ro day la mot phep quy chieu
    #    chu khong phai mot phep do cua chinh luot ay.
    if t and l:
        uoc_t = t["giay_tuong_trung_binh"] * 17
        uoc_l = l["giay_tuong_trung_binh"] * 11
        ra["quy_chieu_nen_v3"] = {
            "ghi_chu": "17 luot TTS + 11 luot LLM cua luot nen v3, tinh tu "
                       "trung binh do duoc o day (khong phai do lai luot ay)",
            "uoc_giay_tts": round(uoc_t, 1),
            "uoc_giay_llm": round(uoc_l, 1),
            "uoc_tong": round(uoc_t + uoc_l, 1),
            "do_that_cua_nen_v3": 942.7,
        }
    return ra


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--che-do", dest="che_do", default="ca-hai",
                    choices=("tts", "llm", "ca-hai", "vong-dau", "wer"))
    ap.add_argument("--giu-wav", dest="giu_wav", default="",
                    help="thu muc giu WAV 16 kHz cua `vong-dau` (cho `wer`)")
    ap.add_argument("--goi", default="",
                    help="tep JSON cua luot `vong-dau` (cho `--che-do wer`)")
    ap.add_argument("--vong", type=int, default=1, help="so vong (mac dinh 1)")
    ap.add_argument("--giong", default=GIONG_MAC_DINH)
    ap.add_argument("--ra", default="", help="tep JSON ghi ket qua")
    ap.add_argument("--phien", default="fix-toc-do",
                    help="ten phien giu khoa `may_tao_tieng`")
    ap.add_argument("--khong-khoa", action="store_true", dest="khong_khoa")
    ap.add_argument("--cho-ban", type=float, default=45.0, dest="cho_ban")
    ap.add_argument("--ban-toi-da", type=int, default=20, dest="ban_toi_da")
    # ⛔ `none` khong co trong danh sach: `ltt_llm` tu choi no tu 14/09.
    ap.add_argument("--muc-nghi", dest="muc_nghi", default=None,
                    choices=("low", "medium", "xhigh"),
                    help="ep muc suy nghi cho phep do (mac dinh: cua thao tac)")
    args = ap.parse_args()

    tts: list[dict] = []
    llm: list[dict] = []
    vd: list[dict] = []

    if args.che_do == "wer":
        if not args.goi:
            print("Can `--goi <tep JSON cua luot vong-dau>`.")
            return 2
        goi_vd = json.loads(pathlib.Path(args.goi).read_bytes().decode("utf-8"))
        tt = _do_wer(goi_vd)
        print()
        print(json.dumps({k: v for k, v in tt.items() if k != "tung_doan"},
                         ensure_ascii=False, indent=2))
        if args.ra:
            pathlib.Path(args.ra).write_bytes(
                json.dumps(tt, ensure_ascii=False, indent=1).encode("utf-8"))
            print(f"\n  [OK] ghi {args.ra}")
        return 0

    if args.che_do == "vong-dau":
        from tools.cua_so_yen import CuaSoYen

        if not str(os.environ.get("LTT_ASV_POOL_URL", "")).strip():
            print("BO QUA: chua co LTT_ASV_POOL_URL.")
            return 0
        with CuaSoYen(args.phien, "do_toc_do_giong vong dau",
                      bat=not args.khong_khoa, cho_toi_da_s=3600,
                      tai_nguyen=("may_tao_tieng",)):
            vd = _do_vong_dau(DOAN_THAT, giong=args.giong, vong=args.vong,
                              cho_ban=args.cho_ban, ban_toi_da=args.ban_toi_da,
                              giu_wav=args.giu_wav)
        goi = {"vong_dau": vd, "tom_tat": _tom_tat_vong_dau(vd)}
        print()
        print(json.dumps(goi["tom_tat"], ensure_ascii=False, indent=2))
        if args.ra:
            pathlib.Path(args.ra).write_bytes(
                json.dumps(goi, ensure_ascii=False, indent=1).encode("utf-8"))
            print(f"\n  [OK] ghi {args.ra}")
        return 0

    if args.che_do in ("tts", "ca-hai"):
        from tools.cua_so_yen import CuaSoYen

        with CuaSoYen(args.phien, "do_toc_do_giong TTS",
                      bat=not args.khong_khoa, cho_toi_da_s=3600,
                      tai_nguyen=("may_tao_tieng",)):
            tts = _do_tts(DOAN_THAT, giong=args.giong, vong=args.vong,
                          giu_wav=args.giu_wav)

    if args.che_do in ("llm", "ca-hai"):
        if not str(os.environ.get("LTT_ASV_POOL_URL", "")).strip():
            print("BO QUA phan LLM: chua co LTT_ASV_POOL_URL.")
        else:
            llm = _do_llm(DOAN_THAT, vong=args.vong, cho_ban=args.cho_ban,
                          ban_toi_da=args.ban_toi_da, tts=tts,
                          muc_nghi=args.muc_nghi)

    goi = {"tts": tts, "llm": llm, "tom_tat": _tom_tat(tts, llm)}
    print()
    print(json.dumps(goi["tom_tat"], ensure_ascii=False, indent=2))
    if args.ra:
        pathlib.Path(args.ra).write_bytes(
            json.dumps(goi, ensure_ascii=False, indent=1).encode("utf-8"))
        print(f"\n  [OK] ghi {args.ra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

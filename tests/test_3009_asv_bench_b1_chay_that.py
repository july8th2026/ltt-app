"""Bench B1 — chạy THẬT một phim: `transcribe` hai lượt (asr đo · ocr chân lý nền).

Gated: `LTT_ASV_B1=1` + `LTT_TEST_NANG=1`. ⛔ Không chạy trong gate.

    set LTT_TEST_NANG=1 & set LTT_ASV_B1=1 & set LTT_ASV_B1_PHIM=<đường dẫn>
    python -m pytest tests/test_3009_asv_bench_b1_chay_that.py -q -s

⚠️ **Đọc `docs/auto_scan_video_final/B1_CHEP_LOI.md` phần đầu trước khi đọc số.**
Bảng kết quả **bất đối xứng**: ĐẠT kết luận ngay; TRƯỢT chưa kết luận được gì cho
tới khi soi tay.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from tests import rao_chan_nang
from tests import test_423_asv_giao_dien as _mt

moi_truong = _mt.moi_truong

BIEN = "LTT_ASV_B1"
CHI_KHI_BAT = pytest.mark.skipif(
    not (os.environ.get(BIEN) or "").strip(),
    reason=f"bench B1 (ASR tren card). Bat bang {BIEN}=1")


def _whisperx_co() -> str:
    """Duong sidecar WhisperX, hoac `""`. ⛔ Khong in gia tri bi mat nao."""
    from apps.autosubvideo import transcription

    return transcription._sidecar_python()        # noqa: SLF001


def _doc_van_ban(run_id: str, ten_gd: str) -> str:
    """Van ban cua mot giai doan, doc NGAY trong luot chay.

    ⛔ Doc sau luot la doc mot kho da bi xoa — xem ghi chu o cho goi.
    """
    import platform_core.db as dbmod
    from platform_core.storage import get_storage

    from apps.auto_scan_video import features

    db = next(dbmod.get_session())
    try:
        gd = features.giai_doan_theo_ten(db, run_id, ten_gd)
        khoa = next((k for k in ((gd.outputs or {}).get("khoa_asset") or [])
                     if str(k).endswith(".json")), "")
        if not khoa:
            return ""
        with get_storage().open(khoa) as f:
            ban = json.loads(f.read().decode("utf-8"))
    finally:
        db.close()
    return " ".join(str(d.get("chu") or d.get("text") or "")
                    for d in (ban.get("doan") or ban.get("segments") or []))


def _phim() -> Path | None:
    p = (os.environ.get("LTT_ASV_B1_PHIM") or "").strip()
    return Path(p) if p and Path(p).is_file() else None


@rao_chan_nang.NANG
@CHI_KHI_BAT
def test_BENCH_B1_mot_phim(moi_truong, tmp_path, monkeypatch):  # noqa: F811
    """Chạy `transcribe` HAI lượt trên cùng một phim rồi so.

    ⛔ **Ghi TRIỆU CHỨNG trước, quy nguyên nhân sau.** Đây là lượt đầu tiên đường
       `asr` chạy thật (Task 5 vừa đổi mặc định), nên xác suất gặp một **tiền đề
       chưa khai** là cao. Lượt A 24/09 là tiền lệ: `auto_match_thieu_can_cu` mất ba
       vòng mới tách được khỏi kết luận *"AUTO_MATCH là đường chết"*.
    """
    from apps.auto_scan_video import pipeline as P
    from tests.fixtures import asv_e2e as fx
    from tests.fixtures import asv_mot_buoc as mb
    from tools import bench_b1_chep_loi as b

    phim = _phim()
    if phim is None:
        pytest.skip("dat LTT_ASV_B1_PHIM=<duong dan phim>")
    for xau, vi_sao in b.PHIM_LOAI.items():
        if xau in phim.stem:
            pytest.skip(f"phim bi LOAI: {vi_sao}")

    fx.doi_hoi_card()
    ra: dict = {"phim": phim.name, "buoc": []}

    def _chay(ten_gd: str, nguon_loi: str, gieo=None) -> dict:
        t0 = time.time()
        kq = mb.chay_mot_buoc(
            moi_truong, ten_giai_doan=ten_gd,
            cai_dat={"nguon_loi": nguon_loi}, duong_video=str(phim),
            gieo=gieo, xin_card=True, monkeypatch=monkeypatch)
        kq["giay"] = round(time.time() - t0, 1)
        kq["nguon_loi_ep"] = nguon_loi
        ra["buoc"].append(kq)
        return kq

    # 🔴 **`media_prepare` phai chay THAT truoc.** `transcribe` doc ban WAV 16 kHz
    #    tu `outputs["khoa_asset"]` cua no (`giai_doan_chep_loi._khoa_tieng_asr`),
    #    va do phai la mot khoa KHO that — khong bia duoc.
    #
    # ⛔ Do that 24/09: ban dau bench gieo `"bench:<ten phim>.wav"` va chet o
    #    `StorageError: key khong hop le`. Trieu chung chi vao KHO, nguyen nhan la
    #    khuon chua bao gio tao ban tieng.
    mp = _chay(P.MEDIA_PREPARE, "asr")
    khoa_wav = next((k for k in (mp["outputs"].get("khoa_asset") or [])
                     if str(k).endswith(".wav")), "")
    if not khoa_wav:
        # ⛔ GHI TRUOC khi dung — mot buoc hong van la mot ket qua.
        d = Path(os.environ.get("LTT_ASV_B1_RA") or (tmp_path / "b1.json"))
        d.parent.mkdir(parents=True, exist_ok=True)
        d.write_text(json.dumps(fx.sach_de_cong_bo(ra), ensure_ascii=False,
                                indent=1), encoding="utf-8")
        pytest.fail(f"media_prepare khong ra ban WAV: {mp['trang_thai']} — "
                    f"{mp['loi'][:200]} | ban ghi: {d}")

    asr = _chay(P.TRANSCRIBE, "asr", gieo={P.MEDIA_PREPARE: khoa_wav})
    ocr = _chay(P.TRANSCRIBE, "ocr", gieo={P.MEDIA_PREPARE: khoa_wav})

    # ── VAN BAN: doc TRONG luot chay ────────────────────────────────────────
    #
    # 🔴 **Kho tam chet cung luot.** `moi_truong` tro kho vao `tmp_path`, va pytest
    #    chi giu ba thu muc gan nhat. Luot do dau tien 24/09 ghi `outputs` roi di
    #    tim van ban SAU khi luot ket thuc — luc do artifact da bien mat, va 8 ph 35
    #    tinh toan khong cho ra duoc mot con so CER nao.
    # ⇒ Doc ngay, o day.
    for k in (asr, ocr):
        k["van_ban"] = _doc_van_ban(k["run_id"], P.TRANSCRIBE)
        k["so_ky_tu_van_ban"] = len(k["van_ban"])

    # ── NHANH ENGINE: khai ra, va khong do nham nhanh trong im lang ─────────
    #
    # 🔴 **Do that 24/09, luot dau:** `engine="faster-whisper"`,
    #    `canh_chinh="fallback_unaligned"` — tuc nhanh WhisperX KHONG chay. Nguyen
    #    nhan la **moi truong cua bench**: `LTT_WHISPERX_PYTHON` khong duoc nap
    #    (no nam trong `C:\LTTPlatform\secrets\app.env`), nen
    #    `transcription.whisperx_available()` tra False.
    #
    # ⛔ Va do la dung lop loi K-01: khuon do **chinh no** chu khong do san pham.
    #    Mot con so 362 s cua nhanh LUI khong noi duoc gi ve nhanh MAC DINH.
    ra["nhanh_engine"] = {
        "engine": asr["outputs"].get("engine", ""),
        "canh_chinh": asr["outputs"].get("canh_chinh", ""),
        "ly_do_roi": asr["outputs"].get("ly_do_roi", ""),
        "whisperx_cau_hinh": bool(_whisperx_co()),
        "khai": ("nhanh MAC DINH (whisperx, co can chinh)"
                 if asr["outputs"].get("canh_chinh") == "aligned"
                 else "nhanh LUI (faster-whisper, KHONG can chinh) — "
                      "moc thoi gian khong can di thang vao `timing_align`"),
    }

    # ── DO: CER + ti le don vi sai + cau truc ──────────────────────────────
    so_do = b.do_hai_ban(ocr["van_ban"], asr["van_ban"])
    ra["do"] = b.gop_ket_qua(
        phim=phim.name, cer=so_do["cer"],
        ti_le_don_vi_sai=so_do["ti_le_don_vi_sai"],
        don_vi_ti_le=so_do["don_vi_ti_le"],
        so_dong_nguon=int(asr["outputs"].get("so_doan") or 0),
        so_dong_hardsub=int(ocr["outputs"].get("so_doan") or 0),
        engine=str(asr["outputs"].get("engine") or ""),
        co_card=bool(asr["card"]["duoc_card"]))

    # 🔴 **GHI BANG CHUNG TRUOC, IN SAU. Da mat 8 ph 57 vi lam nguoc.**
    #
    #    Do that 24/09: lan chay dau tien lam xong CA ffmpeg lan hai luot ASR (537 s),
    #    roi chet o dong `print` ten phim — `UnicodeEncodeError: 'charmap'`, vi stdout
    #    duoi lop boc la cp1252 con ten phim la chu Han. Ban ghi JSON nam SAU cac
    #    `print`, nen **khong mot byte bang chung nao song sot**.
    #
    # ⛔ Day la lan THU HAI cung mot lop loi trong phien nay: `_giu_tang_vat` va
    #    khoi do tep ban giao cua `_mot_luot` da xoa bao cao cua luot B theo dung
    #    cach nay (`f18cca12`). Sua o mot cho khong sua duoc cho khac — nen luat phai
    #    la mot LUAT, khong phai mot ban va: **moi thu sau khi cong viec xong la
    #    BAO CAO, va bao cao khong duoc giet ket qua.**
    duong_ra = Path(os.environ.get("LTT_ASV_B1_RA") or (tmp_path / "b1.json"))
    duong_ra.parent.mkdir(parents=True, exist_ok=True)
    duong_ra.write_text(json.dumps(fx.sach_de_cong_bo(ra), ensure_ascii=False,
                                   indent=1), encoding="utf-8")

    def _in(dong: str) -> None:
        """In ma KHONG BAO GIO nem.

        ⛔ `sys.stdout` cua tien trinh con co the la cp1252; mot ten phim chu Han
           lam `print` nem `UnicodeEncodeError` va giet ca lan chay. Mot dong log
           khong duoc quyen lam dieu do.
        """
        import sys as _s
        try:
            print(dong)
        except Exception:                       # noqa: BLE001
            bo = (getattr(_s.stdout, "encoding", None) or "ascii")
            print(dong.encode(bo, "replace").decode(bo, "replace"))

    _in("")
    _in("=== B1 · " + phim.name + " ===")
    for k in (mp, asr, ocr):
        _in(f"  {k['giai_doan']:16} {k['nguon_loi_ep']:4} "
            f"{k['trang_thai']:16} {k['giay']:6.1f}s "
            f"card={k['card']['duoc_card']} loi={k['loi'][:80]!r}")
        _in("           outputs: " + json.dumps(
            {x: y for x, y in k["outputs"].items()
             if not isinstance(y, (list, dict))}, ensure_ascii=False)[:300])
    d = ra["do"]
    _in(f"  CER {d['cer']}  (nguong {d['nguong']['cer']}) -> "
        f"{'DAT' if d['dat'] else 'TRUOT'}")
    _in(f"  ti le {d['don_vi_ti_le']} sai: {d['ti_le_don_vi_sai']} (KHONG phan xu)")
    _in(f"  doan asr={d['so_doan_asr']} hardsub={d['so_doan_hardsub']} "
        f"lech={d['lech_doan']} can_giai_thich={d['can_giai_thich_lech_doan']}")
    _in(f"  nhanh engine: {ra['nhanh_engine']['khai']}")
    if ra["nhanh_engine"]["ly_do_roi"]:
        _in(f"     ly do roi: {ra['nhanh_engine']['ly_do_roi'][:120]}")
    _in(f"  ban ghi: {duong_ra}")

    # ⛔ Không `assert` gì về chất lượng ở đây: lượt đầu tiên là để THẤY, không để
    #    phán xử. Phán quyết ĐẠT/KHÔNG viết vào `B1_CHEP_LOI.md` §5 sau khi soi số.
    assert ra["buoc"], "khong buoc nao chay"

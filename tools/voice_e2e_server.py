r"""
voice_e2e_server.py — may chu LTT Voice CO LICH LAM VIEC THAT, cho E2E tang CI.

    # cua so 1: cong giong GIA LAP
    python tools\voice_mock_sidecar.py --cong 8131 --token mock-token
    # cua so 2: may chu + worker trong-tien-trinh, tro vao cong gia lap
    python tools\voice_e2e_server.py --cong 8129
    # cua so 3: lay cookie phien cho Playwright
    python tools\voice_e2e_server.py --cong 8129 --cookie

## Khac `studio_dev.py` o cho nao, va vi sao can ca hai

`studio_dev.py` dat mot token GIA (`studio-dev-token-gia`) va ghi lich su THANG
vao bang `Job` — no de **soi giao dien**, va no tu khai: bam Tao se 401. Dung cho
viec cua no.

Tep nay lam viec KHAC: no chay mot **worker trong tien trinh** va tro
`sidecar_client` vao **cong giong gia lap** (`voice_mock_sidecar.py`), nen bam
Tao -> job THAT chay het duong ong THAT:

    route -> submit_with_credit -> hang doi -> claim -> jobs.handle ->
    features.goi_cong -> sidecar HTTP (gia lap) -> ffprobe -> kho -> quyet toan credit

⇒ Day la tang duy nhat kiem duoc golden path "Tao -> queued -> done -> phat ->
   tai" ma KHONG can GPU. Tieng la GIA LAP (xem `voice_mock_sidecar.py`).

## 🔴 CACH LY KHOI PRODUCTION — HAI RAO + BA VO HIEU HOA MAT PHANG DUNG CHUNG

May nay LA production (`C:\LTTPlatform`). Nen:

  · RAO 1  `LTT_VOICE_E2E=1` phai duoc dat (tep nay tu dat).
  · RAO 2  `LTT_DATABASE_URL` PHAI chua chuoi `voice-e2e` — sqlite dung mot lan
           duoi `tmp/voice_e2e/`. Khong khop -> tu choi chay.
  · Kho: `LocalStorage(tmp/voice_e2e/kho)` — KHONG cham kho that.
  · GPU: `job_runner._vram_can` bi ep ve 0 trong tien trinh nay, nen worker
         KHONG cham mat phang claim GPU dung chung (`C:\ProgramData\gpu_claims`).
  · Admission (`vieneu_gpu`): DB-backed, nam trong sqlite CACH LY nay.
  · Worker service that (`LTTStudioWorker`) poll CSDL PRODUCTION, khong poll
    sqlite nay — hai hang doi khong gap nhau.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

THU_MUC = os.path.join(ROOT, "tmp", "voice_e2e")
CSDL = os.path.join(THU_MUC, "voice-e2e.db")           # chuoi 'voice-e2e' = RAO 2
KHO = os.path.join(THU_MUC, "kho")
EMAIL = "voice-e2e@test.local"
MAT_KHAU = "khong-phai-mat-khau-that-12"
CONG_MAC_DINH = 8129
MOCK_CONG_MAC_DINH = 8131
MOCK_TOKEN = "mock-token"


def _dat_moi_truong(mock_cong: int) -> None:
    os.environ["LTT_VOICE_E2E"] = "1"
    os.environ["LTT_DATABASE_URL"] = "sqlite:///" + CSDL.replace("\\", "/")
    os.environ["LTT_ENV"] = "development"
    os.environ.setdefault("LTT_SESSION_SECRET", "voice-e2e-khong-bi-mat")
    os.environ.pop("TURNSTILE_SECRET_KEY", None)
    # 🔴 Tro `sidecar_client` vao cong GIA LAP, khong vao 8120 that.
    os.environ["LTT_VOICE_SIDECAR_PORT"] = str(mock_cong)
    os.environ["LTT_VOICE_SIDECAR_TOKEN"] = MOCK_TOKEN


def _guard() -> None:
    if os.environ.get("LTT_VOICE_E2E") != "1":
        raise SystemExit("RAO 1: can LTT_VOICE_E2E=1 (tep nay tu dat).")
    if "voice-e2e" not in (os.environ.get("LTT_DATABASE_URL") or ""):
        raise SystemExit("RAO 2: LTT_DATABASE_URL phai chua 'voice-e2e' — tu choi "
                         "chay tren mot CSDL khac.")


def seed(mock_cong: int, lam_lai: bool = True) -> str:
    if lam_lai and os.path.isdir(THU_MUC):
        shutil.rmtree(THU_MUC, ignore_errors=True)
    os.makedirs(THU_MUC, exist_ok=True)
    _dat_moi_truong(mock_cong)
    _guard()

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models          # noqa: F401
    import apps.ltt_voice.tables         # noqa: F401
    import apps.ltt_voice.tables_du_an   # noqa: F401
    from platform_core import registry
    registry.load_app_tables()
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core.storage import LocalStorage, set_storage
    set_storage(LocalStorage(KHO))

    from platform_core import credit
    from platform_core.users import UserError, tao_nguoi_dung

    gen = dbmod.get_session()
    db = next(gen)
    try:
        try:
            u = tao_nguoi_dung(db, email=EMAIL, password=MAT_KHAU, is_verified=True)
            db.commit()
            uid = str(u.id)
        except UserError:
            db.rollback()
            from sqlalchemy import select

            from platform_core.models import User
            uid = str(db.execute(select(User).where(User.email == EMAIL))
                      .scalar_one().id)
            print("  [OK] dung lai tai khoan da co")
            return uid
        # ⛔ CHAM SO TIEN GIA LAP: `cap_tay` ghi vao sqlite cach ly nay, khong
        #    phai so credit that. 1000 credit du cho nhieu luot E2E.
        credit.cap_tay(db, uid, 1000, by="voice-e2e")
        _seed_giong(db, uid)
        _seed_du_an(db, uid)
        # RC1 (Task 15) — du lieu THEM cho bo Playwright vinh vien
        # (tests/browser/ltt_voice_rc1.js): giong LEGACY + DO_ASR (D004), giong
        # KHO CHUNG co san nghe thu (T-08), mot luot Lich su DA CO TIENG gan vao
        # mot khoi Du an (D005). Seed DEV-ONLY, chi chay duoi RAO 1/RAO 2 o tren.
        _seed_rc1(db, uid)
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    print(f"  [OK] seed xong: {THU_MUC}")
    print(f"       tai khoan: {EMAIL}  (uid {uid})")
    return uid


def _seed_giong(db, uid: str) -> None:
    """Mot giong da nhan ban, dang dung — de man 'Giong cua toi' co du lieu."""
    from apps.ltt_voice.tables import VoiceProfile, VoiceRepr

    p = VoiceProfile(public_id="vce_e2e_natural_vi", owner_id=uid,
                     ten_hien_thi="Giong E2E - Natural VI", ngon_ngu="vi",
                     trang_thai="active")
    db.add(p)
    db.flush()
    db.add(VoiceRepr(profile_id=p.id, ref_id=0, engine="vieneu",
                     storage_key="voice/repr/e2e.bin",
                     fingerprint="e2e", trang_thai="dang_dung"))


def _seed_du_an(db, uid: str) -> None:
    """Mot du an co khoi — de man 'Du an' khong o trang thai rong."""
    from apps.ltt_voice.tables_du_an import VoiceBlock, VoiceProject

    d = VoiceProject(public_id="prj_e2e_0001", owner_id=uid,
                     ten="Kich ban E2E", trang_thai="nhap")
    db.add(d)
    db.flush()
    for i, t in enumerate([
            "Xin chao, day la khoi thu nhat cua du an E2E.",
            "Va day la khoi thu hai, mot cau dai hon mot chut de co gi ma doc."]):
        db.add(VoiceBlock(project_id=d.id, thu_tu=float(i + 1), text=t,
                          trang_thai="moi"))


def _tep_wav_toi_thieu() -> bytes:
    """WAV PCM 16-bit, mot kenh, 16 kHz, mot phan muoi giay im lang — HOP LE
    (RIFF/WAVE that, dung `wave` chuan cua Python), khong phai bytes gia.

    Du de cac cua doc audio (`_p_audio.audio`, `platform_core.phat_media`)
    phuc vu duoc (200 + RIFF hop le). KHONG mang dau van tay
    `ltt-voice-mock` cua `voice_mock_sidecar.py` — khong can: hai flow RC1
    dung tep nay (T-08, D005) chi kiem HTTP status + hinh dang RIFF, khong
    doi noi dung tieng THAT hay tieng GIA LAP.
    """
    import io
    import wave

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * 1600)
    return buf.getvalue()


def _seed_rc1(db, uid: str) -> None:
    """RC1 (Task 15) — du lieu THEM cho bo Playwright vinh vien
    (`tests/browser/ltt_voice_rc1.js`). DEV-ONLY: chi chay duoi RAO 1
    (`LTT_VOICE_E2E=1`) + RAO 2 (`LTT_DATABASE_URL` chua `voice-e2e`) da kiem
    o `_guard()`, tu `seed()` goi ham nay TRUOC KHI kiem do.

    Bon manh, moi manh phuc vu DUNG MOT flow RC1 (xem task-15-brief.md):

      ① giong LEGACY (`ngon_ngu_nguon="mac_dinh_cu"`) — D004, the giong hien
         "Xac nhan ngon ngu cua giong nay".
      ② giong DO_ASR (`ngon_ngu_nguon="do_asr"`) — D004, KHONG co form doi
         lan tren the (khai nguoc phai bi chan o server, khong co cua bam).
      ③ giong KHO CHUNG (`dung_chung=True`, `license_status="ok"`), chu la
         MOT TAI KHOAN KHAC — T-08: nut nghe thu cua no phai tra 200 cho
         chinh khach E2E dang dang nhap (mot NGUOI KHONG PHAI CHU). Tep nghe
         thu THAT nam san trong kho, dung DUNG khoa `nghe_thu.khoa_chung` —
         vong bao tri (`nghe_thu.bao_tri`) khong chay trong may chu E2E nay.
      ④ mot job `ltt_voice.synthesize` DA `done` voi tep audio THAT trong
         kho, gan vao KHOI THU BA (sau hai khoi da seed o `_seed_du_an`) cua
         du an `prj_e2e_0001` — D005: xoa luot nay o Lich su phai lam khoi do
         chuyen sang "Can tao lai" (`du_an.trang_thai_hien`, suy TU
         `Job.content_expired_at`, khong tu cot `trang_thai` da ghi).
    """
    import io

    from sqlalchemy import select

    from apps.ltt_voice import nghe_thu
    from apps.ltt_voice.manifest import MANIFEST
    from apps.ltt_voice.tables import VoiceProfile, VoiceRepr
    from apps.ltt_voice.tables_du_an import VoiceBlock, VoiceProject
    from platform_core.models import Job
    from platform_core.storage import get_storage

    kho = get_storage()
    wav = _tep_wav_toi_thieu()

    # ① D004 — dong CU (truoc D003): lan la MOT MAC DINH COT, chua ai khai.
    p1 = VoiceProfile(public_id="vce_e2e_legacy_vi", owner_id=uid,
                      ten_hien_thi="Giong E2E - Legacy VI", ngon_ngu="vi",
                      ngon_ngu_nguon="mac_dinh_cu", trang_thai="active")
    db.add(p1)
    db.flush()
    db.add(VoiceRepr(profile_id=p1.id, ref_id=0, engine="vieneu",
                     storage_key="voice/repr/e2e-legacy.bin",
                     fingerprint="e2e-legacy", trang_thai="dang_dung"))

    # ② D004 — da qua PHEP DO ASR; khai nguoc lai bi CHAN
    # (`voice_language_measured`), va the giong KHONG hien form doi lan.
    p2 = VoiceProfile(public_id="vce_e2e_do_asr_en", owner_id=uid,
                      ten_hien_thi="Giong E2E - Do ASR EN", ngon_ngu="en",
                      ngon_ngu_nguon="do_asr", trang_thai="active")
    db.add(p2)
    db.flush()
    db.add(VoiceRepr(profile_id=p2.id, ref_id=0, engine="vieneu",
                     storage_key="voice/repr/e2e-asr.bin",
                     fingerprint="e2e-asr", trang_thai="dang_dung"))

    # ③ T-08 — KHO CHUNG cua nen tang, CHU la mot tai khoan KHAC (gia lap
    # "khong phai chu" cho chinh khach E2E dang dang nhap). `license_status`
    # phai la "ok" (`tham_chieu.LICENSE_CHO_PHEP`) va `trang_thai="active"` —
    # thieu mot trong hai thi `_giong_chung_dang_hop_le()` (`_p_audio.py`) tu
    # choi phuc vu.
    p3 = VoiceProfile(public_id="vce_e2e_kho_chung", owner_id="vce-e2e-chu-khac",
                      ten_hien_thi="Giong E2E - Kho chung", ngon_ngu="vi",
                      ngon_ngu_nguon="khai_bao", trang_thai="active",
                      dung_chung=True, license_status="ok")
    db.add(p3)
    db.flush()
    db.add(VoiceRepr(profile_id=p3.id, ref_id=0, engine="vieneu",
                     storage_key="voice/repr/e2e-chung.bin",
                     fingerprint="e2e-chung", trang_thai="dang_dung"))
    kho.put(nghe_thu.khoa_chung(p3.public_id), io.BytesIO(wav),
           content_type="audio/wav")

    # ④ D005 — mot job DA XONG, tep audio THAT trong kho, gan vao khoi THU BA
    # (thu_tu=3.0, sau hai khoi da seed o `_seed_du_an`) cua du an
    # `prj_e2e_0001`.
    van_ban_job = "Khoi co tieng, cho luot xoa Lich su (RC1 D005)."
    job = Job(user_id=uid, app_slug=MANIFEST.slug,
             job_type="ltt_voice.synthesize",
             params={"text": van_ban_job, "owner_id": uid, "nguon": "du_an"},
             status="done")
    db.add(job)
    db.flush()
    khoa_audio = f"voice/out/{uid}/{job.id}/tieng.wav"
    kho.put(khoa_audio, io.BytesIO(wav), content_type="audio/wav")
    job.result = {"audio_key": khoa_audio, "duration_s": 1.6, "credit_cost": 5}
    db.flush()

    du_an = db.execute(select(VoiceProject)
                       .where(VoiceProject.public_id == "prj_e2e_0001")
                       ).scalar_one()
    db.add(VoiceBlock(project_id=du_an.id, thu_tu=3.0, text=van_ban_job,
                      trang_thai="xong", job_id=str(job.id),
                      audio_key=khoa_audio, giay=1.6, credit=5))


# ── worker trong tien trinh ──────────────────────────────────────────────────

def _vong_worker(stop: threading.Event) -> None:
    """Nhat va chay job trong CHINH tien trinh may chu.

    ⛔ Ep `_vram_can -> 0` de KHONG cham mat phang claim GPU dung chung. Tieng
       la gia lap nen khong can GPU that; ep 0 la cach chac chan nhat de duong
       `_giu_gpu` short-circuit (`need_mb <= 0 -> yield None, False`).
    """
    from platform_core import job_runner

    # ⛔ Ep nhu cau VRAM ve 0 -> `_giu_gpu` short-circuit -> KHONG cham GPU.
    def _khong_gpu(job_type: str) -> int:
        return 0
    job_runner._vram_can = _khong_gpu

    caps = {"voice", "audio", "api", "cpu"}
    while not stop.is_set():
        try:
            co = job_runner._chay_mot_job("voice-e2e-worker", capabilities=caps)
        except Exception as e:                       # noqa: BLE001
            print(f"  [worker] loi mot luot: {type(e).__name__}: {e}", flush=True)
            co = False
        if not co:
            stop.wait(0.4)


def lay_cookie(cong: int) -> str:
    import re
    import urllib.error
    import urllib.parse
    import urllib.request

    goc = f"http://127.0.0.1:{cong}"
    bo = urllib.request.HTTPCookieProcessor()
    mo = urllib.request.build_opener(bo)
    with mo.open(f"{goc}/login", timeout=15) as r:
        html = r.read().decode("utf-8", "replace")
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    if not m:
        raise SystemExit("khong lay duoc csrf_token — may chu da chay chua?")
    du_lieu = urllib.parse.urlencode({
        "username": EMAIL, "password": MAT_KHAU, "csrf_token": m.group(1)}).encode()
    try:
        mo.open(urllib.request.Request(f"{goc}/login", data=du_lieu), timeout=15)
    except urllib.error.HTTPError as e:
        if e.code not in (302, 303):
            raise
    for c in bo.cookiejar:
        if "session" in c.name.lower():
            return f"{c.name}={c.value}"
    raise SystemExit(f"khong thay cookie phien; co: {[c.name for c in bo.cookiejar]}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cong", type=int, default=CONG_MAC_DINH)
    ap.add_argument("--mock-cong", type=int, default=MOCK_CONG_MAC_DINH)
    ap.add_argument("--cookie", action="store_true",
                    help="in cookie phien roi thoat (may chu phai dang chay)")
    ap.add_argument("--giu", action="store_true",
                    help="khong xoa du lieu cu truoc khi seed")
    a = ap.parse_args(argv)

    if a.cookie:
        print(lay_cookie(a.cong))
        return 0

    seed(a.mock_cong, lam_lai=not a.giu)
    _dat_moi_truong(a.mock_cong)
    _guard()

    from server.app import create_app
    app = create_app(env={
        "LTT_ENV": "development",
        "LTT_SESSION_SECRET": os.environ["LTT_SESSION_SECRET"],
        "LTT_ADMIN_USERNAME": "",
        "LTT_ADMIN_PASSWORD_HASH": "",
    })

    stop = threading.Event()
    t = threading.Thread(target=_vong_worker, args=(stop,), name="voice-e2e-worker",
                         daemon=True)
    t.start()

    import uvicorn
    print(f"  Voice E2E: http://127.0.0.1:{a.cong}/ltt-voice", flush=True)
    print(f"  Cong giong GIA LAP mong doi o 127.0.0.1:{a.mock_cong} "
          f"(chay voice_mock_sidecar.py truoc).", flush=True)
    try:
        uvicorn.run(app, host="127.0.0.1", port=a.cong, log_level="warning")
    finally:
        stop.set()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

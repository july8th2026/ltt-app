r"""do_llm_cong_asv.py — DO cong LLM noi bo tren dung duong Auto Scan Video di.

    python tools\do_llm_cong_asv.py --pha khai,cong,goi,temp,seed,dich

## Cau hoi no tra loi

Ma KHAI mot dieu (`manifest.model_llm_noi_bo = "ltt-3.8"`,
`ai.MODEL_THI_GIAC_NOI_BO = "ltt-3.5"`), chu du an noi *"cong llm noi bo goi
qua 3.5"*. Hai loi khai khong bat khop duoc bang cach doc them ma — chung chi
bat khop duoc bang cach HOI CONG THAT roi doc **truong `model` trong phan
hoi**. Do la viec cua tep nay.

## ⛔ DI DUNG DUONG SAN PHAM

`ai.goi` (ASV) va `dieu_phoi.goi` (nen tang) — ca hai di qua `api_pool`. Khong
mo mot duong HTTP thu hai de "do cho nhanh": mot duong khong phai duong khach
di se tra loi ve mot he thong khong phai he thong dang ban.

Ngoai le DUY NHAT: `CongVlm.health()` / `CongVlm.models()` — do la hai cua
CHI-DOC cua **chinh lop cong san pham**, va chung la nguon duy nhat noi duoc
`--reasoning-budget` may B dang chay that su la bao nhieu.

## Bien can

Tep tu doc `C:\LTTPlatform\secrets\app.env` (can quyen Administrator). Khong in
mot gia tri nao. Khoa goi may B khong nam trong bien moi truong — no la mot
dong POOL trong CSDL, nen phai co `LTT_DATABASE_URL` +
`LTT_TOKEN_ENCRYPTION_KEY` de `api_pool.chon_key` chon duoc dong nao.

## ⛔ TRAN DONG THOI

CLAUDE.md toan cuc: toi da 2 request `ltt-3.8` + 2 `ltt-3.5` cung luc tren toan
may. Tep nay goi TUAN TU (mot request mot luc) — tran duoc ton trong ke ca khi
chay hai ban sao cua no.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import statistics
import sys
import time

GOC = pathlib.Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

APP_ENV = pathlib.Path(r"C:\LTTPlatform\secrets\app.env")
BO_CAP = GOC / "docs/auto_scan_video_final/l_dich/bo_cap_co_nhan.json"
THU_MUC_PHIM = pathlib.Path.home() / "Desktop" / "TEST VIDEO"

#: Lo dich THAT: doan zh lay tu `bo_cap_co_nhan.json` (faster-whisper large-v3
#: tren 4 clip that, giu nguyen loi ASR). ⛔ Khong bia doan zh: mot doan sach se
#: do mot he thong khong co that.
LO = 12


# ══════════════════════════════════════════════════════════════════════════════
#  Moi truong
# ══════════════════════════════════════════════════════════════════════════════

def _nap_app_env() -> int:
    """Nap `app.env` vao TIEN TRINH NAY. ⛔ Khong in mot gia tri nao."""
    if not APP_ENV.exists():
        raise SystemExit(f"khong thay {APP_ENV}")
    n = 0
    for dong in APP_ENV.read_text(encoding="utf-8", errors="replace").splitlines():
        d = dong.strip()
        if not d or d.startswith("#") or "=" not in d:
            continue
        ten, gt = d.split("=", 1)
        ten = ten.strip()
        if ten:
            os.environ[ten] = gt
            n += 1
    if not os.environ.get("LTT_DATABASE_URL"):
        raise SystemExit("app.env khong co LTT_DATABASE_URL")
    os.environ["LTT_ASV_POOL_URL"] = os.environ["LTT_DATABASE_URL"]
    return n


def _mo_db():
    """CSDL tam DA NAP KHOA tu pool that — khuon `asv_e2e.nap_khoa_pool`.

    ⛔ Chep sang CSDL RIENG: bo dem `last_used_at`/`error_count` cua luot do nay
       khong lam ban thong ke khoa production.
    """
    import tempfile

    tam = pathlib.Path(tempfile.mkdtemp(prefix="ltt_do_llm_cong_")) / "do.db"
    that = os.environ["LTT_DATABASE_URL"]
    os.environ["LTT_DATABASE_URL"] = f"sqlite:///{tam.as_posix()}"
    import platform_core.db as dbmod

    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    from tests.fixtures import asv_e2e

    so = asv_e2e.nap_khoa_pool(db)
    db.commit()
    os.environ["LTT_DATABASE_URL"] = that
    return db, so


def _cua_so_hoac_loi(ai, thao_tac) -> int | str:
    """`cua_so_ngu_canh(t)`, hoac TEN LOAI ngoai le neu no no.

    ⛔ Khong tra `0` khi khong doc duoc. `0` la mot gia tri HOP LE trong cot
       "cua so" (mot thao tac khong ghim ngu canh), nen mot phep do khong chay
       duoc tra `0` la mot bao cao SAI chu khong phai mot bao cao thieu — va bao
       cao nay chinh la thu nguoi ta doc de chot ngan sach.

    ⭐ Cung khuon voi dong ngay tren no trong `pha_khai` (`mid =
       f"<{type(exc).__name__}>"`) — mot cot khong doc duoc trong nhu NHAU o ca
       hai cho.
    """
    try:
        return int(ai.cua_so_ngu_canh(thao_tac))
    except Exception as exc:                                     # noqa: BLE001
        return f"<{type(exc).__name__}>"


def _base_url_ltt_llm(providers) -> str:
    """`base_url` cua provider `ltt_llm` trong registry.

    ⛔ `providers.get` tra `Provider | None`. Registry chua khai `ltt_llm` (may
       moi, CSDL scratch, app.env thieu) => `prov.base_url` la `AttributeError`
       tho giua mot cong cu do luong, va nguoi chay doc mot vet `NoneType` thay
       vi biet minh thieu cau hinh. Do bang `mypy [union-attr]` 24/09.
    """
    prov = providers.get("ltt_llm")
    if prov is None:
        raise SystemExit(
            "registry khong co provider `ltt_llm` — chay `python tools\\doctor.py` "
            "hoac kiem `app.env`; cong cu nay khong tu doan base_url.")
    return (prov.base_url or "").rstrip("/")


# ══════════════════════════════════════════════════════════════════════════════
#  Pha KHAI — ASV yeu cau model nao (doc registry LUC CHAY)
# ══════════════════════════════════════════════════════════════════════════════

def pha_khai() -> dict:
    from platform_core import providers
    from platform_core.llm import canonical

    from apps.auto_scan_video import ai, manifest

    ra: dict = {"manifest_model_llm_noi_bo": manifest.MANIFEST.model_llm_noi_bo,
                "MODEL_THI_GIAC_NOI_BO": ai.MODEL_THI_GIAC_NOI_BO,
                "ALIAS_SANG_ID": dict(canonical.ALIAS_SANG_ID),
                "thao_tac": {}}
    print("\n[KHAI] ASV yeu cau model nao — doc registry LUC CHAY")
    print(f"  manifest.model_llm_noi_bo = {ra['manifest_model_llm_noi_bo']!r}")
    print(f"  ai.MODEL_THI_GIAC_NOI_BO  = {ra['MODEL_THI_GIAC_NOI_BO']!r}")
    print(f"  canonical.ALIAS_SANG_ID   = {ra['ALIAS_SANG_ID']}")
    print(f"\n  {'thao tac':<18s} {'thi giac':<9s} {'model ASV xin':<14s} "
          f"{'muc nghi':<9s} {'cua so':>9s}  tran ra/timeout")
    for t in ai.THAO_TAC:
        try:
            mid = ai.model_cho(t)
        except Exception as exc:                                 # noqa: BLE001
            mid = f"<{type(exc).__name__}>"
        cs = _cua_so_hoac_loi(ai, t)
        tran, cho = ai.ngan_sach_cho(t)
        kn = providers.model_capabilities(mid) or {}
        ra["thao_tac"][t.ma] = {
            "can_thi_giac": t.can_thi_giac, "model_asv_xin": mid,
            "muc_nghi_khai": t.muc_nghi, "cua_so": cs,
            "tran_token_ra": tran or ai.tran_token_ra(),
            "timeout_s": cho, "vision_registry": bool(kn.get("vision")),
        }
        print(f"  {t.ma:<18s} {str(t.can_thi_giac):<9s} {mid:<14s} "
              f"{(t.muc_nghi or '(may chu)'):<9s} {cs:>9,}  "
              f"{tran or ai.tran_token_ra():,}/{cho or '(mac dinh)'}")
    return ra


# ══════════════════════════════════════════════════════════════════════════════
#  Pha CONG — cong THAT khai gi (health + /v1/models), qua chinh lop CongVlm
# ══════════════════════════════════════════════════════════════════════════════

def _cong_vlm(db, ten_model: str, timeout_s: float = 60.0):
    """`CongVlm` dung `base_url` cua registry + credential tu `api_pool`.

    ⛔ Credential KHONG duoc in, khong duoc ghi vao bao cao.
    """
    import httpx

    from platform_core import api_keys, api_pool, providers
    from platform_core.llm.cong_vlm import CongVlm
    from platform_core.models import APIKEY_CAT_CHAT

    base = _base_url_ltt_llm(providers)
    key = api_pool.chon_key(db, category=APIKEY_CAT_CHAT, model=ten_model or None,
                            thu_tu_provider=["ltt_llm"])
    cred = api_keys.lay_credential(db, key)
    client = httpx.Client(timeout=timeout_s)

    def goi(method, path, *, json=None, timeout=None):
        r = client.request(method, base + path, json=json,
                           headers={"Authorization": f"Bearer {cred}"},
                           timeout=timeout or timeout_s)
        try:
            return r.status_code, r.json(), dict(r.headers)
        except ValueError:
            return r.status_code, {}, dict(r.headers)

    return CongVlm(goi=goi, timeout_s=timeout_s), base


def pha_cong(db) -> dict:
    print("\n[CONG] cong THAT khai gi — /health + /v1/models (lop CongVlm)")
    ra: dict = {}
    try:
        cong, base = _cong_vlm(db, "qwen38-api")
    except Exception as exc:                                     # noqa: BLE001
        print(f"  [HONG] khong dung duoc CongVlm: {type(exc).__name__}: {exc}")
        return {"loi": f"{type(exc).__name__}: {exc}"}
    # base_url co the mang cong; khong co bi mat trong no, in duoc.
    ra["base_url"] = base
    print(f"  base_url = {base}")
    try:
        h = cong.health()
        ra["health"] = {
            "models": h.get("models"), "models_la": h.get("models_la"),
            "thuong_nguon": h.get("thuong_nguon"),
            "vat_ly": h.get("vat_ly"), "tran": h.get("tran"),
            "gioi_han": h.get("gioi_han"), "trong_tai": h.get("trong_tai"),
            "gpu": h.get("gpu"),
        }
        vl = ((h.get("vat_ly") or {}).get("theo_model") or {})
        print(f"  models cong khai : {h.get('models')}")
        print(f"  nguon vat ly     : {(h.get('vat_ly') or {}).get('nguon')}")
        for m, v in sorted(vl.items()):
            print(f"    {m:<14s} ctx={v.get('ctx'):>8}  np={v.get('np')}  "
                  f"reasoning_budget={v.get('reasoning_budget')}")
        print(f"  tran input_tokens: {(h.get('tran') or {}).get('input_tokens')}")
    except Exception as exc:                                     # noqa: BLE001
        print(f"  [HONG] health: {type(exc).__name__}: {exc}")
        ra["health_loi"] = f"{type(exc).__name__}: {exc}"
    try:
        ds = cong.models()
        ra["v1_models"] = [{"id": d.get("id"), "owned_by": d.get("owned_by")}
                           for d in ds]
        print(f"  /v1/models       : {[d.get('id') for d in ds]}")
    except Exception as exc:                                     # noqa: BLE001
        print(f"  [HONG] /v1/models: {type(exc).__name__}: {exc}")
        ra["v1_models_loi"] = f"{type(exc).__name__}: {exc}"
    return ra


# ══════════════════════════════════════════════════════════════════════════════
#  Du lieu THAT
# ══════════════════════════════════════════════════════════════════════════════

def _doan_zh(n: int = LO) -> list[dict]:
    """Doan zh THAT tu `bo_cap_co_nhan.json` (ASR that, giu nguyen loi ASR)."""
    d = json.loads(BO_CAP.read_text(encoding="utf-8"))
    muc = list(d["muc"])[:n]
    moc, ra = 0.8, []
    for m in muc:
        dai = round(max(0.8, len(str(m["zh"])) / 4.5), 2)
        ra.append({"ma": f"s{m['id']}", "chu": str(m["zh"]),
                   "bat": moc, "ket": round(moc + dai, 2),
                   "vi_tham_chieu": str(m.get("vi") or "")})
        moc = round(moc + dai + 0.9, 2)
    return ra


def _khung(so: int = 2) -> tuple[bytes, ...]:
    """Khung JPEG THAT tu mot clip trong `Desktop\\TEST VIDEO`."""
    import cv2

    phim = sorted(THU_MUC_PHIM.glob("*.mp4"))
    if not phim:
        raise SystemExit(f"khong thay clip nao trong {THU_MUC_PHIM}")
    cap = cv2.VideoCapture(str(phim[0]))
    tong = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    ra = []
    for i in range(so):
        cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, int(tong * (i + 1) / (so + 1))))
        ok, anh = cap.read()
        if not ok:
            continue
        h, w = anh.shape[:2]
        if w > 768:
            anh = cv2.resize(anh, (768, int(h * 768 / w)))
        ok, buf = cv2.imencode(".jpg", anh, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if ok:
            ra.append(bytes(buf))
    cap.release()
    return tuple(ra)


def _loi_nhac(thao_tac_ma: str, doan: list[dict]) -> list:
    from apps.auto_scan_video import hieu_canh, long_tieng, qc_ai

    if thao_tac_ma == "chuyen_loi_thoai":
        return long_tieng.loi_nhac(
            doan, tat_ca=doan, ngon_ngu_goc="zh", ngon_ngu_dich="vi",
            dac_diem_giong={"gioi_tinh": "nu", "toc_do": "vua"})
    if thao_tac_ma == "qc_ngu_nghia":
        return qc_ai.loi_nhac_ngu_nghia(
            [{"ma": d["ma"], "goc": d["chu"], "chu": d["vi_tham_chieu"]}
             for d in doan], ngon_ngu_dich="vi")
    if thao_tac_ma == "doc_canh":
        return hieu_canh.loi_nhac_canh(
            "c1", " ".join(d["chu"] for d in doan[:4]), 2,
            {"co_mat": True, "chu_tren_hinh": True}, _khung(2))
    raise SystemExit(f"chua co loi nhac cho {thao_tac_ma}")


# ══════════════════════════════════════════════════════════════════════════════
#  Mot luot goi — qua `ai.goi` (duong ASV)
# ══════════════════════════════════════════════════════════════════════════════

def _mot_luot(db, thao_tac, messages, *, tran: int = 0, cho=None,
              muc_nghi=None) -> dict:
    from apps.auto_scan_video import ai

    t0 = time.monotonic()
    kq, loi = {}, ""
    try:
        kq = ai.goi(db, thao_tac, messages, max_tokens=int(tran or 0),
                    timeout_s=cho, muc_nghi=muc_nghi)
    except Exception as exc:                                     # noqa: BLE001
        loi = f"{type(exc).__name__}: {str(exc)[:160]}"
    giay = time.monotonic() - t0
    sd = kq.get("su_dung")
    nd = str(kq.get("noi_dung") or "")
    luoc_do = ""
    if not loi:
        try:
            ai.doc_ket_qua(kq, thao_tac)
        except Exception as exc:                                 # noqa: BLE001
            luoc_do = f"{type(exc).__name__}: {str(exc)[:160]}"
    return {
        "thao_tac": thao_tac.ma, "giay": round(giay, 2),
        "model_cong_tra": str(kq.get("model") or ""),
        "finish_reason": str(kq.get("finish_reason") or ""),
        "token_vao": int(getattr(sd, "token_vao", 0) or 0),
        "token_ra": int(getattr(sd, "token_ra", 0) or 0),
        "token_cache": int(getattr(sd, "token_vao_cache", 0) or 0),
        "do_dang_tin": bool(getattr(sd, "dang_tin", False)),
        "ky_tu_suy_nghi": len(str(kq.get("suy_nghi") or "")),
        "ky_tu_noi_dung": len(nd),
        # 🔴 "RONG MA BAO THANH CONG": cong tra 200, khong loi, ma `content`
        #    rong. `model-nha-tren-may-b` ghi day la loi DA GAP.
        "rong_ma_thanh_cong": bool(not loi and not nd.strip()),
        "loi": loi, "luoc_do": luoc_do,
        "noi_dung_dau": nd[:180].replace("\n", " "),
    }


def _tom_tat(ban: list[dict]) -> dict:
    g = sorted(r["giay"] for r in ban if not r["loi"])
    if not g:
        return {"n": 0, "n_ok": 0}
    def _pct(p):
        i = min(len(g) - 1, max(0, int(round((len(g) - 1) * p))))
        return round(g[i], 1)
    ok = [r for r in ban if not r["loi"]]
    return {
        "n": len(ban), "n_ok": len(ok),
        "p50_s": _pct(0.50), "p95_s": _pct(0.95),
        "min_s": round(g[0], 1), "max_s": round(g[-1], 1),
        "token_vao_trung_vi": int(statistics.median(r["token_vao"] for r in ok)),
        "token_ra_trung_vi": int(statistics.median(r["token_ra"] for r in ok)),
        "model_cong_tra": sorted({r["model_cong_tra"] for r in ok}),
        "so_rong_ma_thanh_cong": sum(1 for r in ban if r["rong_ma_thanh_cong"]),
        "so_luoc_do_sai": sum(1 for r in ban if r["luoc_do"]),
        "so_loi": sum(1 for r in ban if r["loi"]),
    }


def pha_goi(db, vong: int) -> dict:
    from apps.auto_scan_video import ai

    doan = _doan_zh(4)
    bo = [("chuyen_loi_thoai", ai.CHUYEN_LOI_THOAI),
          ("qc_ngu_nghia", ai.QC_NGU_NGHIA),
          ("doc_canh", ai.DOC_CANH)]
    ra: dict = {"vong": vong, "lo_doan": len(doan), "chi_tiet": {}, "tom_tat": {}}
    print(f"\n[GOI] {vong} vong moi thao tac, TUAN TU (ton trong tran dong thoi)")
    for ten, tt in bo:
        try:
            msg = _loi_nhac(ten, doan)
        except Exception as exc:                                 # noqa: BLE001
            print(f"  [BO QUA] {ten}: {type(exc).__name__}: {exc}")
            continue
        tran, cho = ai.ngan_sach_cho(tt)
        ban = []
        for i in range(vong):
            r = _mot_luot(db, tt, msg, tran=tran, cho=cho)
            ban.append(r)
            print(f"  {ten:<18s} vong {i+1:>2}  {r['giay']:>6.1f}s  "
                  f"model={r['model_cong_tra'] or '-':<12s} "
                  f"fr={r['finish_reason'] or '-':<8s} "
                  f"vao={r['token_vao']:>6} ra={r['token_ra']:>6} "
                  f"nghi={r['ky_tu_suy_nghi']:>6} nd={r['ky_tu_noi_dung']:>6}"
                  f"{'  RONG-MA-THANH-CONG' if r['rong_ma_thanh_cong'] else ''}"
                  f"{('  ' + r['loi']) if r['loi'] else ''}"
                  f"{('  LUOCDO ' + r['luoc_do']) if r['luoc_do'] else ''}")
        ra["chi_tiet"][ten] = ban
        ra["tom_tat"][ten] = _tom_tat(ban)
        print(f"  => {ten}: {ra['tom_tat'][ten]}")
    return ra


# ══════════════════════════════════════════════════════════════════════════════
#  Pha TEMP — cong dang ap `temperature` mac dinh nao
# ══════════════════════════════════════════════════════════════════════════════

CAU_HOI_ENTROPY = [
    {"role": "user", "content":
     "Ke mot danh tu tieng Viet chi mot loai trai cay. "
     "Tra loi DUY NHAT mot tu, khong giai thich, khong dau cau."}]


def _goi_tho(db, model_id: str, messages: list, *, max_tokens: int,
             temperature=None, them=None, timeout_s: float = 240.0) -> dict:
    """Goi qua `dieu_phoi.goi` — duong nen tang, van di qua `api_pool`.

    ⭐ Dung o day chu khong `ai.goi` vi hai pha nay can hai num ma `ai.goi` KHONG
       phoi ra: `temperature` tuong minh va `them` (de gui `seed`). Ca hai van
       la tham so cua chinh ham san pham.
    """
    from platform_core.llm import dieu_phoi

    t0 = time.monotonic()
    try:
        kq = dieu_phoi.goi(db, messages=messages, thu_tu_provider=["ltt_llm"],
                           model_theo_provider={"ltt_llm": model_id},
                           max_tokens=max_tokens, temperature=temperature,
                           them=them, timeout_s=timeout_s)
    except Exception as exc:                                     # noqa: BLE001
        return {"giay": round(time.monotonic() - t0, 2),
                "loi": f"{type(exc).__name__}: {str(exc)[:200]}"}
    return {
        "giay": round(time.monotonic() - t0, 2), "loi": "",
        "model_cong_tra": kq.model, "finish_reason": kq.finish_reason,
        "noi_dung": (kq.noi_dung or "").strip(),
        "token_vao": kq.su_dung.token_vao, "token_ra": kq.su_dung.token_ra,
        "token_cache": kq.su_dung.token_vao_cache,
        "do_dang_tin": kq.su_dung.dang_tin,
        "ky_tu_suy_nghi": len(kq.suy_nghi or ""),
    }


def pha_temp(db, vong: int, model_id: str) -> dict:
    """KHONG khai `temperature` vs khai `0.0` — do BANG HANH VI.

    ⛔ Khong co endpoint nao noi ra `temperature` mac dinh, nen doc mot hang so
       trong `llama-swap.yaml` cua KHO khong chung minh may B dang chay so do.
       Cai chung minh duoc la HANH VI: neu bo trong ma van ra nhieu dap an khac
       nhau, con `temperature=0` ra mot dap an lap lai, thi mac dinh cua cong
       **khong phai 0** — tuc duong song ASV dang lay mau ngau nhien.
    """
    print(f"\n[TEMP] {vong} luot KHONG khai temperature vs {vong} luot temp=0.0"
          f" tren {model_id}")
    ra: dict = {"model": model_id, "vong": vong}
    for nhan, temp in (("khong_khai", None), ("temp_0", 0.0)):
        ban = []
        for i in range(vong):
            r = _goi_tho(db, model_id, CAU_HOI_ENTROPY, max_tokens=2048,
                         temperature=temp)
            ban.append(r)
            print(f"  {nhan:<11s} {i+1:>2}  {r['giay']:>6.1f}s  "
                  f"{(r.get('noi_dung') or r['loi'])[:70]!r}")
        dap = [r.get("noi_dung", "") for r in ban if not r["loi"]]
        ra[nhan] = {"dap_an": dap, "so_khac_nhau": len(set(dap)),
                    "n_ok": len(dap), "ban": ban}
        print(f"  => {nhan}: {len(set(dap))} dap an khac nhau / {len(dap)} luot")
    return ra


# ══════════════════════════════════════════════════════════════════════════════
#  Pha SEED — cong co NHAN `seed` khong, va no CO HIEU LUC khong
# ══════════════════════════════════════════════════════════════════════════════

def pha_seed(db, vong: int, model_id: str, seed: int = 20260924) -> dict:
    """CUNG mot dau vao, CUNG mot seed, `vong` lan. Giong nhau het = tai lap duoc.

    ⛔ Day la phep do QUYET DINH cho cau "ban dich co tai lap duoc khong".
       `-np 3` + continuous batching + `--spec-type draft-mtp` deu co the pha
       tinh tat dinh ngay ca khi seed duoc nhan — nen phai DO, khong doc ma.
    """
    doan = _doan_zh(4)
    msg = _loi_nhac("chuyen_loi_thoai", doan)
    print(f"\n[SEED] {vong} luot CUNG dau vao, seed={seed}, tren {model_id}")
    ban = []
    for i in range(vong):
        r = _goi_tho(db, model_id, msg, max_tokens=16384,
                     them={"seed": seed}, timeout_s=300.0)
        ban.append(r)
        print(f"  luot {i+1}  {r['giay']:>6.1f}s  ra={r.get('token_ra', 0):>6}  "
              f"{(r.get('noi_dung') or r['loi'])[:90]!r}")
    ok = [r["noi_dung"] for r in ban if not r["loi"]]
    # Doi chung: cung dau vao, KHONG seed.
    print("  -- doi chung: KHONG gui seed --")
    ban_kh = []
    for i in range(vong):
        r = _goi_tho(db, model_id, msg, max_tokens=16384, timeout_s=300.0)
        ban_kh.append(r)
        print(f"  (dc) luot {i+1}  {r['giay']:>6.1f}s  "
              f"{(r.get('noi_dung') or r['loi'])[:90]!r}")
    ok_kh = [r["noi_dung"] for r in ban_kh if not r["loi"]]
    ra = {
        "model": model_id, "seed": seed, "vong": vong,
        "co_seed": {"n_ok": len(ok), "so_khac_nhau": len(set(ok)),
                    "dong_nhat": len(set(ok)) == 1 and len(ok) == vong,
                    "ban": ban},
        "khong_seed": {"n_ok": len(ok_kh), "so_khac_nhau": len(set(ok_kh)),
                       "ban": ban_kh},
    }
    print(f"  => co seed : {len(set(ok))} ket qua khac nhau / {len(ok)} luot")
    print(f"  => khong   : {len(set(ok_kh))} ket qua khac nhau / {len(ok_kh)} luot")
    return ra


# ══════════════════════════════════════════════════════════════════════════════
#  Pha DICH — 3.8 vs 3.5 cho DUNG viec dich zh->vi, qua loi nhac SAN PHAM
# ══════════════════════════════════════════════════════════════════════════════

def pha_tat_dinh(db, vong: int, model_id: str) -> dict:
    """CUNG lo dich, `temperature=0.0`, `vong` lan. Doi chung cua pha SEED.

    🔴 Pha `seed` tra loi *"seed co lam ban dich tai lap duoc khong"* — va neu
       cau tra loi la KHONG thi con mot cau nua chua duoc tra: **co cach nao
       khac khong?** Khong hoi no thi ket luan "ban dich khong tai lap duoc" la
       mot loi khai ve CA HE THONG dua tren MOT num duy nhat da thu.

    ⭐ Va phep do nay con lam mot viec thu hai: no la bang chung MANH NHAT ve
       `temperature` mac dinh. Neu `temp=0` cho ra ket qua lap lai trong khi
       KHONG KHAI cho ra 5 ket qua khac nhau tren cung dau vao, thi mac dinh cua
       cong **khong phai 0** — do la mot ket luan doc duoc tu hanh vi, khong phai
       tu mot hang so trong tep cau hinh cua kho (tep tren may B moi la tep chay).
    """
    doan = _doan_zh(4)
    msg = _loi_nhac("chuyen_loi_thoai", doan)
    print(f"\n[TAT DINH] {vong} luot CUNG dau vao, temperature=0.0, tren {model_id}")
    ban = []
    for i in range(vong):
        r = _goi_tho(db, model_id, msg, max_tokens=16384, temperature=0.0,
                     timeout_s=300.0)
        ban.append(r)
        print(f"  luot {i+1}  {r['giay']:>6.1f}s  ra={r.get('token_ra', 0):>6}  "
              f"{(r.get('noi_dung') or r['loi'])[:90]!r}")
    ok = [r["noi_dung"] for r in ban if not r["loi"]]
    ra = {"model": model_id, "vong": vong, "n_ok": len(ok),
          "so_khac_nhau": len(set(ok)),
          "dong_nhat": bool(ok) and len(set(ok)) == 1 and len(ok) == vong,
          "ban": ban}
    print(f"  => temp=0: {len(set(ok))} ket qua khac nhau / {len(ok)} luot")
    return ra


def _rut_chu(tho, ma: str) -> str:
    """Cau tieng Viet cua `ma`, doc KHOAN DUNG ca `dict` lan `list`."""
    if isinstance(tho, dict):
        v = tho.get(ma)
        if isinstance(v, dict):
            return str(v.get("chu") or "")
        return str(v or "")
    if isinstance(tho, list):
        for v in tho:
            if isinstance(v, dict) and str(v.get("ma") or "") == ma:
                return str(v.get("chu") or "")
    return ""


def pha_dich(db, lo: int, lap: int) -> dict:
    from platform_core.llm import gia_token

    from apps.auto_scan_video import ai, long_tieng

    doan = _doan_zh(lo)
    msg = _loi_nhac("chuyen_loi_thoai", doan)
    tran, cho = ai.ngan_sach_cho(ai.CHUYEN_LOI_THOAI)
    ra: dict = {"n_doan": len(doan), "lap": lap,
                "ma_doan": [d["ma"] for d in doan], "theo_model": {}}
    print(f"\n[DICH] zh->vi, lo {len(doan)} doan THAT, x{lap} moi model, "
          f"loi nhac SAN PHAM (`long_tieng.loi_nhac`)")
    for bi_danh, mid in (("ltt-3.8", "qwen38-api"), ("ltt-3.5", "qwen35-api")):
        ban, cap = [], []
        for i in range(lap):
            r = _goi_tho(db, mid, msg, max_tokens=tran, timeout_s=float(cho or 300))
            ban.append(r)
            print(f"  {bi_danh}  lan {i+1}  {r['giay']:>6.1f}s  "
                  f"model={r.get('model_cong_tra', '-')}  "
                  f"vao={r.get('token_vao', 0)} ra={r.get('token_ra', 0)}  "
                  f"{r['loi'][:90]}")
            if r["loi"]:
                continue
            try:
                goi = ai.doc_json(r["noi_dung"], ai.CHUYEN_LOI_THOAI)
            except Exception as exc:                             # noqa: BLE001
                r["luoc_do"] = f"{type(exc).__name__}: {str(exc)[:160]}"
                continue
            tho = goi.get("doan")
            # 🔴 HINH DANG `doan` LA MOT PHEP DO, khong phai mot chi tiet ky
            #    thuat. `long_tieng.doc_chuyen` doi mot **dict theo ma**; mot
            #    model tra ve MANG lam no nem `LongTiengError` — tuc model do
            #    khong dung duoc cho thao tac nay du no goi thanh cong, du no
            #    re hon, va du ban dich tung cau doc len van hay. Do 23/09:
            #    `ltt-3.5` tra `"doan": [...]` ngay lan goi dau.
            r["hinh_dang_doan"] = type(tho).__name__
            # ⭐ Doc bang DUNG ham san pham, khong bang mot ban doc rieng cua
            #    cong cu do: mot ban doc rong rai hon se bao "dung duoc" ve mot
            #    phan hoi ma san pham se tu choi.
            try:
                doc = long_tieng.doc_chuyen(goi, {d["ma"] for d in doan})
                r["ban_doc_san_pham"] = "dat"
                r["so_doan_doc_duoc"] = len(doc)
            except Exception as exc:                             # noqa: BLE001
                r["ban_doc_san_pham"] = f"{type(exc).__name__}: {str(exc)[:160]}"
                r["so_doan_doc_duoc"] = 0
            if i == 0:
                # ⚠️ De CHAM DIEM thi doc KHOAN DUNG (nhan ca mang), vi cau hoi
                #    "ban dich hay den dau" khac cau hoi "san pham doc duoc
                #    khong". Tron hai cau lai thi mot model sai hinh dang se co
                #    diem chat luong RONG — va mot tap rong khong phai mot phep
                #    do, no la mot cho trong doc len nhu "khong co loi nao".
                for d in doan:
                    cap.append({"ma": d["ma"], "nguon": d["chu"],
                                "dich": _rut_chu(tho, d["ma"])})
        chi_phi = None
        xong = [r for r in ban if not r["loi"]]
        if xong:
            # ⛔ `SuDung` THAT, khong phai `SimpleNamespace`: `gia_token.tinh`
            #    doc `token_vao_moi` (mot `@property` tru phan cache), nen mot
            #    vat the gia thieu dung cai thuoc tinh quyet dinh gia.
            from platform_core.llm.cong_vlm import SuDung
            do = SuDung(token_vao=xong[0]["token_vao"],
                        token_ra=xong[0]["token_ra"],
                        token_vao_cache=xong[0].get("token_cache", 0) or 0,
                        dang_tin=True)
            try:
                cp = gia_token.tinh(do, bi_danh)
                chi_phi = {"mcredit": cp.tong_mcredit,
                           "credit": cp.tong_credit_lam_tron_len,
                           "phien_ban_gia": cp.phien_ban_gia}
            except Exception as exc:                             # noqa: BLE001
                chi_phi = {"loi": f"{type(exc).__name__}: {exc}"}
        ra["theo_model"][bi_danh] = {
            "model_id": mid, "ban": ban, "tom_tat": {
                "n": len(ban), "n_ok": len(xong),
                "giay": [r["giay"] for r in ban],
                "token_vao": [r.get("token_vao", 0) for r in ban],
                "token_ra": [r.get("token_ra", 0) for r in ban],
                "model_cong_tra": sorted({r.get("model_cong_tra", "")
                                          for r in xong}),
            },
            "chi_phi_mot_luot": chi_phi,
            "cap_de_cham": cap,
        }
    return ra


# ══════════════════════════════════════════════════════════════════════════════
#  Pha CHAM — chat luong ban dich, bang MetricX-24 QE DA CO TRONG KHO
# ══════════════════════════════════════════════════════════════════════════════

def pha_cham(doc: str, gpu_uuid: str = "") -> dict:
    """Cham `cap_de_cham` cua pha `dich` bang `apps.asv_gpu.do_luong.metricx`.

    ⛔ Khong tu che thang diem. MetricX-24 QE la bo do DA GHIM trong kho (ban +
       sha256 o `_metricx/phien_ban.json`), va nguong san pham `NGUONG_DO` da
       duoc do tren bo cap co nhan cua ta (`L_DICH.md`). Mot thang tu nghi ra o
       day se khong so sanh duoc voi bat cu so nao da cong bo.
    """
    from apps.asv_gpu.do_luong import metricx

    d = json.loads(pathlib.Path(doc).read_text(encoding="utf-8"))
    dich = d.get("dich") or {}
    ra: dict = {"nguon_ban_ghi": doc, "nguong_zh_vi": metricx.NGUONG_DO[("zh", "vi")],
                "thang_diem": metricx.THANG_DIEM, "thap_la_tot": metricx.THAP_LA_TOT,
                "theo_model": {}}
    print("\n[CHAM] MetricX-24 QE (thang 0..25, THAP LA TOT), "
          f"nguong san pham zh->vi = {ra['nguong_zh_vi']}")
    for bi_danh, khoi in (dich.get("theo_model") or {}).items():
        cap = [c for c in (khoi.get("cap_de_cham") or []) if c.get("dich")]
        if not cap:
            print(f"  [BO QUA] {bi_danh}: khong co cap nao dich duoc")
            ra["theo_model"][bi_danh] = {"n": 0}
            continue
        diem = metricx.do_dich(cap, ngon_ngu_nguon="zh", ngon_ngu_dich="vi",
                              gpu_uuid=gpu_uuid)
        gt = [diem[c["ma"]] for c in cap if c["ma"] in diem]
        ra["theo_model"][bi_danh] = {
            "n": len(gt), "diem_tung_ma": diem,
            "trung_vi": round(statistics.median(gt), 2) if gt else None,
            "trung_binh": round(sum(gt) / len(gt), 2) if gt else None,
            "min": round(min(gt), 2) if gt else None,
            "max": round(max(gt), 2) if gt else None,
            "so_vuot_nguong": sum(1 for g in gt if g > ra["nguong_zh_vi"]),
        }
        print(f"  {bi_danh}: n={len(gt)} trung_vi="
              f"{ra['theo_model'][bi_danh]['trung_vi']} "
              f"trung_binh={ra['theo_model'][bi_danh]['trung_binh']} "
              f"vuot_nguong={ra['theo_model'][bi_danh]['so_vuot_nguong']}")
    return ra


# ══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pha", default="khai,cong,goi,temp,seed,dich")
    ap.add_argument("--doc", default="", help="ban ghi JSON de pha `cham` doc")
    ap.add_argument("--vong", type=int, default=10)
    ap.add_argument("--vong-temp", type=int, default=6)
    ap.add_argument("--vong-seed", type=int, default=5)
    ap.add_argument("--lo", type=int, default=LO)
    ap.add_argument("--lap-dich", type=int, default=2)
    ap.add_argument("--ra", default="")
    args = ap.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    pha = [p.strip() for p in args.pha.split(",") if p.strip()]
    # ⭐ `cham` KHONG goi may B, nen no khong duoc doi `app.env` va khong duoc
    #    mo pool khoa: mot pha chi cham diem tren ban ghi da co phai chay duoc
    #    tren mot may khong co bi mat nao.
    can_cong = [p for p in pha if p != "cham"]
    db = None
    if can_cong:
        n = _nap_app_env()
        print(f"[OK] nap {n} bien tu app.env (khong in gia tri nao)")
        db, so_khoa = _mo_db()
        print(f"[OK] nap {so_khoa} dong khoa `ltt_llm` tu pool that (chi doc)")
        if not so_khoa:
            print("[!!] pool that khong co khoa `ltt_llm` nao. Dung.")
            return 1

    bao: dict = {"khi": time.strftime("%Y-%m-%d %H:%M:%S"), "pha": pha}
    if "khai" in pha:
        bao["khai"] = pha_khai()
    if "cong" in pha:
        bao["cong"] = pha_cong(db)
    if "goi" in pha:
        bao["goi"] = pha_goi(db, args.vong)
    if "temp" in pha:
        bao["temp"] = pha_temp(db, args.vong_temp, "qwen38-api")
    if "seed" in pha:
        bao["seed"] = pha_seed(db, args.vong_seed, "qwen38-api")
    if "dich" in pha:
        bao["dich"] = pha_dich(db, args.lo, args.lap_dich)
    if "tatdinh" in pha:
        bao["tat_dinh"] = pha_tat_dinh(db, args.vong_seed, "qwen38-api")
    if "cham" in pha:
        if not args.doc:
            print("[!!] pha `cham` can `--doc <ban ghi pha dich>.json`")
            return 1
        bao["cham"] = pha_cham(args.doc)

    if args.ra:
        p = pathlib.Path(args.ra)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(bao, ensure_ascii=False, indent=1),
                     encoding="utf-8")
        print(f"\n[OK] ghi {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

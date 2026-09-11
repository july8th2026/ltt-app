r"""
check_voice_qa.py — CONG chat luong cho LTT Voice + cac RAO CHONG-XANH-GIA.

    python tools\check_voice_qa.py           # rao TINH (nhanh, khong dung server)
    python tools\check_voice_qa.py --e2e      # them: chay voice_e2e_check.py

## Vi sao co tep nay

Bo test Voice DA chay trong gate (qua `test_nhanh.py`). Cai gate THIEU la mot lop
canh **chinh bo bang chung Voice khong tu rong ruot di** — dung lop loi ma
`docs/BAY_TRONG_CONG_CHAT_LUONG.md` va CLAUDE.md canh:

  · mot suite ten "live" lang le dung tieng GIA LAP;
  · so test tu tut ve 0 (thu thap rong) ma dong RESULT van xanh;
  · trinh duyet khong thuc su mo ma flow van "pass";
  · may chu E2E vo tinh tro vao CSDL / cong giong PRODUCTION.

Cac rao o day la TINH (doc tep, khong import ma app, khong dung server) nen chay
trong gate ~1 giay. Tang chay-that (`--e2e`) tu dung mock + server cach ly.

## ⛔ TINH KHONG PHAI BANG CHUNG HANH VI

Rao tinh chi chung minh HINH DANG dung: tep con do, nhan mock con do, ranh gioi
con do. No KHONG chung minh golden path chay. Bang chung hanh vi la `--e2e`
(mock) va tang LIVE (`chay_thu_ltt_voice.py`). Dong RESULT noi ro no la loai nao.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _doc(rel: str) -> str:
    p = os.path.join(ROOT, rel)
    if not os.path.isfile(p):
        return ""
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()


# 🔴 TAP HOP tep test Voice — CHOT THEO TEN, khong theo SO LUONG.
#
#    `banh-coc-chi-bao-ve-thu-no-nhin-thay` + `banh coc chot TAP HOP khong chot
#    SO LUONG`: mot moc tong co cua hoan doi mot-doi-mot (xoa mot tep, them mot
#    tep, tong khong doi). Chot theo TEN thi xoa/doi-ten bat ky tep nao la ĐO;
#    them tep moi thi tu do.
VOICE_TESTS = [
    "test_337_ltt_voice_gia.py", "test_338_ltt_voice_hop_dong.py",
    "test_340_ltt_voice_trang_render.py", "test_342_ltt_voice_noi_dai.py",
    "test_344_ltt_voice_vo.py", "test_345_ltt_voice_giong_mau.py",
    "test_346_ltt_voice_cua_audio.py", "test_347_ltt_voice_studio.py",
    "test_348_ltt_voice_lich_su.py", "test_349_ltt_voice_ky_tu_an.py",
    "test_350_ltt_voice_du_an.py", "test_352_ltt_voice_tiep_can.py",
    "test_353_voice_sidecar_bo_do.py", "test_364_ltt_voice_man_api.py",
    "test_375_ltt_voice_nop_lai_khong_trung.py", "test_376_cong_chat_luong_voice.py",
    "test_397_ltt_voice_bien_ky_tu.py", "test_500_ltt_voice_nghe_thu.py",
    "test_501_ltt_voice_hong_hoc.py", "test_902_voice_song_khong_ve_cho_khong.py",
]

#: Cong cu tang LIVE — KHONG duoc dinh toi cong GIA LAP.
LIVE_TOOLS = ["tools/chay_thu_ltt_voice.py", "tools/cong_chat_luong_voice.py"]

#: Flow trinh duyet — phai co du rao rieng cua chung.
BROWSER_FLOWS = ["tests/browser/ltt_voice_golden.js",
                 "tests/browser/ltt_voice_negative.js",
                 "tests/browser/ltt_voice_smoke.js",
                 "tests/browser/ltt_voice_rc1.js"]

#: RC1 (Task 15, spec §9) — flow rieng phai lap DU 6 khung hinh.
BROWSER_FLOW_RC1 = "tests/browser/ltt_voice_rc1.js"
KHUNG_HINH_RC1 = ((1280, 720), (1366, 768), (1440, 900), (1920, 1080),
                  (390, 844), (768, 1024))

#: THAT (Task 15) — chay cong giong THAT, GAC bang
#: LTT_VOICE_SIDECAR_TOKEN. KHONG nam trong BROWSER_FLOWS (rao rieng ben
#: duoi kiem ca hinh dang gac lan bon loai bat loi) va KHONG bao gio duoc
#: CHAY boi rao tinh nay — chi bi PIN hinh dang.
BROWSER_FLOW_THAT = "tests/browser/ltt_voice_that.js"

MOCK = "tools/voice_mock_sidecar.py"
E2E_SERVER = "tools/voice_e2e_server.py"
E2E_CHECK = "tools/voice_e2e_check.py"


def rao_tinh() -> list[str]:
    loi: list[str] = []

    # G-INV: tap hop test Voice khong duoc rong rot di.
    thieu = [t for t in VOICE_TESTS if not os.path.isfile(os.path.join(ROOT, "tests", t))]
    if thieu:
        loi.append(f"INVENTORY: {len(thieu)} tep test Voice bien mat (doi ten/xoa?): {thieu}")

    # G-MOCK-LABEL: mock phai tu khai GIA LAP tren ca ba kenh.
    m = _doc(MOCK)
    if not m:
        loi.append(f"THIEU {MOCK}")
    else:
        for dau in ("X-Voice-Mock", '"mock"', "ltt-voice-mock", "SIMULATED"):
            if dau not in m:
                loi.append(f"MOCK-LABEL: {MOCK} thieu dau tu-khai-gia-lap {dau!r}")

    # G-LIVE-PURITY: cong cu LIVE KHONG duoc dinh toi mock/e2e (mock ro vao suite
    # "live" la dung ca lop loi anti-false-green cam).
    for t in LIVE_TOOLS:
        src = _doc(t)
        if not src:
            loi.append(f"THIEU cong cu LIVE {t}")
            continue
        for cam in ("voice_mock_sidecar", "voice_e2e_server", "voice_e2e_check"):
            if cam in src:
                loi.append(f"LIVE-PURITY: {t} dinh toi {cam} — mock RO vao tang LIVE")

    # G-E2E-ISOLATION: may chu E2E phai co CA HAI rao + ep VRAM ve 0.
    s = _doc(E2E_SERVER)
    if not s:
        loi.append(f"THIEU {E2E_SERVER}")
    else:
        for dau in ("LTT_VOICE_E2E", "voice-e2e", "_vram_can"):
            if dau not in s:
                loi.append(f"E2E-ISOLATION: {E2E_SERVER} thieu rao cach ly {dau!r}")

    # G-E2E-CHECK: checker phai tu khai la mock (khong bi doc nham la LIVE).
    c = _doc(E2E_CHECK)
    if not c:
        loi.append(f"THIEU {E2E_CHECK}")
    elif "PASS (mock)" not in c or "SIMULATED" not in c:
        loi.append(f"E2E-CHECK: {E2E_CHECK} khong tu khai la mock (thieu 'PASS (mock)'/'SIMULATED')")

    # G-BROWSER-GUARD: moi flow phai (a) tro loopback CACH LY, khong production;
    # (b) co it nhat mot `throw` (co the ĐO that su); golden phai canh loi console.
    for fp in BROWSER_FLOWS:
        js = _doc(fp)
        if not js:
            loi.append(f"THIEU flow {fp}")
            continue
        if "app.lttstudios.com" in js:
            loi.append(f"BROWSER: {fp} tro toi PRODUCTION — flow QA chi chay loopback")
        if "127.0.0.1:8129" not in js:
            loi.append(f"BROWSER: {fp} khong tro may chu E2E cach ly 127.0.0.1:8129")
        if "throw new Error" not in js:
            loi.append(f"BROWSER: {fp} khong co `throw` nao — mot flow khong the ĐO la vo dung")
    gold = _doc(BROWSER_FLOWS[0])
    if gold and "console" not in gold:
        loi.append("BROWSER: golden flow khong thu loi console (rao 'browser thuc su mo')")
    if gold and "RIFF" not in gold and "0x52" not in gold:
        loi.append("BROWSER: golden flow khong khang dinh WAV that (RIFF) — co the xanh rong")

    # G-BROWSER-RC1 (Task 15): flow RC1 phai bat DU 4 loai bat loi (console
    # error/pageerror/requestfailed/HTTP>=400) VA lap DU 6 khung hinh (spec
    # §9) — thieu mot khung la mot man hinh khong duoc kiem tran ngang ma
    # khong ai bao.
    rc1 = _doc(BROWSER_FLOW_RC1)
    if not rc1:
        loi.append(f"THIEU flow {BROWSER_FLOW_RC1}")
    else:
        for dau in ("page.on('console'", "page.on('pageerror'",
                   "page.on('requestfailed'", "page.on('response'"):
            if dau not in rc1:
                loi.append(f"BROWSER-RC1: {BROWSER_FLOW_RC1} thieu bat loi {dau!r}")
        for w, h in KHUNG_HINH_RC1:
            if f"[{w}, {h}]" not in rc1:
                loi.append(f"BROWSER-RC1: {BROWSER_FLOW_RC1} thieu khung hinh {w}x{h}")
        if "LTT_QA_BASE_URL" not in rc1:
            loi.append(f"BROWSER-RC1: {BROWSER_FLOW_RC1} khong ho tro tang-2 LTT_QA_BASE_URL")

        # G-BROWSER-RC1-XOACHO (fix round 1/5): moi luong phai TU xoa danh
        # sach cho-phep-400 cua rieng no truoc khi chay — thieu buoc nay, mot
        # `choPhep400(...)` cua luong TRUOC ro sang luong SAU va che mat mot
        # 400/500 bat ngo. Nam luong ⇒ it nhat nam lan goi `xoaCho(`.
        if rc1.count("xoaCho(") < 5:
            loi.append(f"BROWSER-RC1: {BROWSER_FLOW_RC1} goi xoaCho() duoi 5 lan "
                       "- cho-phep-400 co the ro tu luong truoc sang luong sau")

        # G-BROWSER-RC1-TANG2 (fix round 1/5): buoc XOA lich su (D005) la
        # KHONG THE DAO NGUOC — phai co bien phat hien loopback, gac
        # LTT_QA_CHO_XOA quanh buoc XOA, VA it nhat ba duong SKIP (D004,
        # T-08, D005 phu thuoc seed _seed_rc1, chi ton tai tren loopback).
        if "LA_LOOPBACK" not in rc1:
            loi.append(f"BROWSER-RC1: {BROWSER_FLOW_RC1} thieu bien phat hien loopback "
                       "(LA_LOOPBACK) - khong the gac buoc seed/XOA khoi tang-2")
        if "LTT_QA_CHO_XOA" not in rc1:
            loi.append(f"BROWSER-RC1: {BROWSER_FLOW_RC1} thieu gac LTT_QA_CHO_XOA "
                       "quanh buoc XOA lich su (D005) - nguy co xoa that tren tang-2")
        if rc1.count("SKIP") < 3:
            loi.append(f"BROWSER-RC1: {BROWSER_FLOW_RC1} thieu duong SKIP cho cac luong "
                       "phu thuoc seed tren tang-2 (D004/T-08/D005)")

    # G-BROWSER-THAT (Task 15): flow THAT phai GAC bang
    # LTT_VOICE_SIDECAR_TOKEN (khong tu chay, khong tu doan mot may chu that
    # nao, KHONG tu dat bien do), in SKIP khi vang token, va van phai bat DU
    # 4 loai bat loi + ho tro tang-2 tren nhanh chay that.
    that = _doc(BROWSER_FLOW_THAT)
    if not that:
        loi.append(f"THIEU flow {BROWSER_FLOW_THAT}")
    else:
        if "app.lttstudios.com" in that:
            loi.append(f"BROWSER: {BROWSER_FLOW_THAT} tro toi PRODUCTION — flow QA chi chay loopback")
        if "127.0.0.1:8129" not in that:
            loi.append(f"BROWSER: {BROWSER_FLOW_THAT} khong tro may chu cach ly 127.0.0.1:8129")
        if "throw new Error" not in that:
            loi.append(f"BROWSER: {BROWSER_FLOW_THAT} khong co `throw` nao")
        if "LTT_VOICE_SIDECAR_TOKEN" not in that:
            loi.append(f"BROWSER-THAT: {BROWSER_FLOW_THAT} khong gac bang LTT_VOICE_SIDECAR_TOKEN")
        if ("process.env.LTT_VOICE_SIDECAR_TOKEN =" in that
                or "process.env.LTT_VOICE_SIDECAR_TOKEN=" in that):
            loi.append(f"BROWSER-THAT: {BROWSER_FLOW_THAT} TU DAT LTT_VOICE_SIDECAR_TOKEN — cam")
        if "SKIP" not in that:
            loi.append(f"BROWSER-THAT: {BROWSER_FLOW_THAT} khong in SKIP khi vang token")
        for dau in ("page.on('console'", "page.on('pageerror'",
                   "page.on('requestfailed'", "page.on('response'"):
            if dau not in that:
                loi.append(f"BROWSER-THAT: {BROWSER_FLOW_THAT} thieu bat loi {dau!r}")
        if "LTT_QA_BASE_URL" not in that:
            loi.append(f"BROWSER-THAT: {BROWSER_FLOW_THAT} khong ho tro tang-2 LTT_QA_BASE_URL")

    # G-MOCK-CUA-DAI: mock phai phu ba cua duong van ban dai (lo-ra-tep, ghep-tep,
    # stream) — thieu mot cua la duong van ban dai roi vao 404 ma khong ai bao.
    for cu in CUA_MOCK_BAT_BUOC:
        if cu not in m:
            loi.append(f"mock thieu cua {cu} — duong van ban dai se khong duoc phu")

    return loi


def chay_e2e() -> int:
    print("\n[--e2e] chay voice_e2e_check.py (tu dung mock + server cach ly)...")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "voice_e2e_check.py")],
                       cwd=ROOT)
    return r.returncode


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--e2e", action="store_true",
                    help="chay them tang golden+negative (mock) — CAN thoi gian + cong")
    a = ap.parse_args(argv)

    loi = rao_tinh()
    print("=" * 70)
    if loi:
        print(f"  🔴 CONG ĐO — {len(loi)} rao chong-xanh-gia gay:")
        for d in loi:
            print(f"     {d}")
        print("\nRESULT: FAIL")
        return 1
    print(f"  ✅ RAO TINH XANH — {len(VOICE_TESTS)} tep test Voice con du, mock tu "
          f"khai gia lap, tang LIVE sach, may chu E2E cach ly, {len(BROWSER_FLOWS)} "
          f"flow co rao.")
    print("  ⚠️ Day la rao HINH DANG, KHONG phai bang chung hanh vi. Bang chung:")
    print("     `--e2e` (mock) + tang LIVE (chay_thu_ltt_voice.py).")

    if a.e2e:
        rc = chay_e2e()
        if rc != 0:
            print("\nRESULT: FAIL (e2e)")
            return rc
        print("\nRESULT: PASS (rao tinh + e2e mock)")
        return 0

    print("\nRESULT: PASS (rao tinh) — KHONG phai bang chung hanh vi; xem `--e2e`")
    return 0


#: Ba cua mock BAT BUOC phai co de duong van ban dai (lo-ra-tep + ghep-tep) va
#: phat dan (stream) khong roi vao 404. Them sau — CHOT theo TEN CUA, khong
#: theo so luong — cung ly do VOICE_TESTS chot theo ten o tren.
#:
#: ⚠️ Dat TRUOC `if __name__ == "__main__":` chu khong sau: tep nay tu goi
#:    `main()` o cuoi khi chay nhu script, nen mot hang dinh nghia SAU khoi do
#:    khong ton tai luc `rao_tinh()` chay toi no (NameError, da do that).
CUA_MOCK_BAT_BUOC = ("/v1/speech", "/v1/speech-dai", "/v1/batch",
                     "/v1/lo-ra-tep", "/v1/ghep-tep", "/v1/stream")


if __name__ == "__main__":
    raise SystemExit(main())

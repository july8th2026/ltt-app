# -*- coding: utf-8 -*-
"""thu_luong_treo.py -- Prompt 06 §1, ca "hung stream". Chay TREN MAY B.

Chi mo va CAT ket noi HTTP. Khong dung tien trinh nao, khong doi cau hinh nao,
khong ghi gi ngoai mot tep ket qua.

## Vi sao ca nay dang mot bo do rieng

No la phep THU HOI QUY cho su co 31/08 -- mot suat dong thoi bi ro vi `finally`
cua generator KHONG BAO GIO chay: generator chua chay dong dau tien thi chua co
`finally` de chay, nen tai nguyen xin TRUOC generator ma nha TRONG generator la
mot duong ro. Sau su co, suat duoc nha o BA tang (BackgroundTask cua Starlette,
`dong()` tach khoi vong lap, va han giu suat).

Bo test don vi da chot ca ba tang. Cai bo test KHONG chot duoc la: ba tang do co
con dung khi ket noi dut DOT NGOT tren mot dich vu that, duoi uvicorn that,
khong phai duoi TestClient.

## Cat kieu gi

`SO_LINGER (1, 0)` -> gui RST thay vi FIN. Do la khach RUT MANG, khong phai
khach dong tab tu te. Truong hop kho hon, va la truong hop that hay gap hon.
"""
from __future__ import annotations

import json
import socket
import struct
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CONG = "http://127.0.0.1:8299"
TOK = ""
for _d in Path(r"C:\ProgramData\LTTLlm\gateway.env").read_text(
        encoding="utf-8-sig").splitlines():
    if _d.startswith("LTT_LLM_TOKEN="):
        TOK = _d.split("=", 1)[1].strip()

RA: list[str] = []


def ghi(s: str = "") -> None:
    RA.append(str(s))
    print(s, flush=True)


def health() -> dict:
    # ⭐ `/health` DOI XAC THUC (401 neu thieu). Do la dung theo §2: chi so van
    #    hanh chi tiet khong nen mo cho ai cung xem. Phat hien luc 23:33 vi ban
    #    dau to nay khong gui token.
    try:
        yc = urllib.request.Request(
            CONG + "/health", headers={"User-Agent": "ltt-thu/1.0",
                                       "Authorization": f"Bearer {TOK}"})
        with urllib.request.urlopen(yc, timeout=8) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:                                      # noqa: BLE001
        return {"loi": f"{type(e).__name__}: {e}"}


def do_be_mat_cong_khai() -> None:
    """§2: duong nao tra loi KHI KHONG CO TOKEN, va no lo ra nhung gi?

    Mot cong chi co `/health` co xac thuc thi thieu LIVENESS: bo cham soc dich
    vu (NSSM, k8s, uptime robot) khong cam token, nen no khong phan biet duoc
    "dich vu chet" voi "dich vu song nhung tu choi ta".
    """
    ghi("-- §2: be mat KHONG XAC THUC (do xem cai gi tra loi ma khong can token)")
    for duong in ("/health", "/live", "/healthz", "/v1/models", "/metrics", "/"):
        try:
            yc = urllib.request.Request(CONG + duong,
                                        headers={"User-Agent": "ltt-thu/1.0"})
            with urllib.request.urlopen(yc, timeout=6) as r:
                than = r.read(400).decode("utf-8", "replace").replace("\n", " ")
                ghi(f"     {duong:<12} {r.status}  {than[:150]}")
        except urllib.error.HTTPError as e:
            ghi(f"     {duong:<12} {e.code}")
        except Exception as e:                                  # noqa: BLE001
            ghi(f"     {duong:<12} {type(e).__name__}")
    ghi("")


#: Ten truong THAT, lay tu than `/health` that luc 23:36 -- KHONG doan.
#:
#: 🔴 BAN DAU TO NAY DOAN SAI TEN, va do la mot suyt-nua nghiem trong: no doc
#:    `dang_giu` (khong ton tai) -> `.get()` tra None -> `None == 0` la False ->
#:    no in "KHONG DAT -- RO SUAT quay lai" voi giong chac nich, trong khi he
#:    thong hoan toan lanh lan va cai sai la CHINH NO.
#:
#: ⇒ Bai hoc khong phai "kiem tra ten truong". La: mot truong THIEU phai lam
#:   phep do VO, khong duoc lang le thanh None roi di tiep. Cung lop loi voi
#:   nuot ngoai le, va `check_silent_except` ton tai chinh vi lop loi nay.
class ThieuTruong(RuntimeError):
    """Than /health khong co truong ta can -- phep do VO, khong phai KHONG DAT."""


def _lay(h: dict, *duong: str):
    nut = h
    for k in duong:
        if not isinstance(nut, dict) or k not in nut:
            raise ThieuTruong("/health thieu truong " + ".".join(duong)
                              + f" (co: {list(nut) if isinstance(nut, dict) else type(nut)})")
        nut = nut[k]
    return nut


def suat() -> str:
    h = health()
    if "loi" in h:
        return f"(khong doc duoc: {h['loi'][:70]})"
    g = _lay(h, "gioi_han")
    return (f"dang_chay={_lay(g, 'dang_chay')}/{_lay(g, 'max_dong_thoi')} "
            f"giu_lau_nhat={_lay(g, 'giu_lau_nhat_giay')}s "
            f"da_thu_hoi={_lay(g, 'da_thu_hoi')}")


def cat_giua_luong(cho_s: float) -> None:
    """Mo mot luong, doi `cho_s` giay cho no chay, roi cat bang RST."""
    than = json.dumps({"model": "qwen38-api", "max_tokens": 900, "stream": True,
                       "messages": [{"role": "user",
                                     "content": "Viet mot bai 600 tu ve mua thu."}]})
    s = socket.create_connection(("127.0.0.1", 8299), timeout=20)
    try:
        s.sendall(
            (f"POST /v1/chat/completions HTTP/1.1\r\n"
             f"Host: 127.0.0.1:8299\r\n"
             f"Authorization: Bearer {TOK}\r\n"
             f"Content-Type: application/json\r\n"
             f"User-Agent: ltt-thu/1.0\r\n"
             f"Content-Length: {len(than)}\r\n"
             f"Connection: close\r\n\r\n{than}").encode())
        time.sleep(cho_s)
    finally:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
        s.close()


def main() -> int:
    ghi(f"THU LUONG TREO -- Prompt 06 §1   {time.strftime('%Y-%m-%d %H:%M:%S')}")
    if not TOK:
        ghi("KHONG CO TOKEN -- dung")
        return 1
    h = health()
    if "loi" in h:
        ghi(f"CONG KHONG SONG: {h['loi']} -- dung")
        return 1
    do_be_mat_cong_khai()
    ghi(f"nen ban dau: {suat()}")
    ghi(f"han giu suat: {_lay(h, 'gioi_han', 'han_giu_s')}s")
    ghi("")

    # Ba moc cat khac nhau. Moc la thu QUAN TRONG: cat TRUOC khi generator chay
    # dong dau tien la duong ro cu, cat GIUA chung la duong thong thuong.
    for i, (nhan, cho) in enumerate((
            ("cat RAT SOM (0.3s) -- truoc khi generator kip chay dong dau", 0.3),
            ("cat SOM (1.5s)", 1.5),
            ("cat GIUA LUONG (4s)", 4.0)), 1):
        ghi(f"  lan {i}: {nhan}")
        try:
            cat_giua_luong(cho)
        except Exception as e:                                  # noqa: BLE001
            ghi(f"     (loi khi cat: {type(e).__name__}: {e})")
        time.sleep(1.0)
        ghi(f"     ngay sau khi cat: {suat()}")

    ghi("")
    ghi("  theo doi 30s xem suat co tu nha khong:")
    for i in range(6):
        time.sleep(5)
        ghi(f"   +{(i + 1) * 5:>2}s: {suat()}")

    g = _lay(health(), "gioi_han")
    chay, thu_hoi = _lay(g, "dang_chay"), _lay(g, "da_thu_hoi")
    ok = chay == 0
    ghi("")
    ghi(f"  KET LUAN: {'DAT' if ok else 'KHONG DAT'} -- dang_chay={chay} (mong doi 0)")
    if not ok:
        ghi("     => RO SUAT quay lai. Day la hoi quy cua su co 31/08.")
        ghi(f"     => han giu suat la {_lay(g, 'han_giu_s')}s; neu no nha SAU moc")
        ghi("        do thi chan cuoi lam viec, con hai tang tren da hong.")
    elif thu_hoi == 0:
        # ⭐ Day moi la ket qua manh. Khong phai "luoi an toan da do duoc", ma
        #    "no chua bao gio phai do" -- hai tang tren tu nha suat, chan cuoi
        #    cung nam yen. Neu `da_thu_hoi` > 0 thi suat VAN ve 0 nhung bang mot
        #    duong khac, va do la mot tin xau doi lot tin tot.
        ghi(f"     ⭐ da_thu_hoi={thu_hoi}: chan cuoi (han giu {_lay(g, 'han_giu_s')}s)")
        ghi("        KHONG PHAI DO. Hai tang tren tu nha suat truoc khi den luot no.")
    else:
        ghi(f"     ⚠️ da_thu_hoi={thu_hoi}: suat CO ve 0, nhung bang CHAN CUOI chu")
        ghi("        khong phai bang duong thuong. Tin xau doi lot tin tot --")
        ghi("        hai tang tren dang khong lam viec, dieu tra truoc khi mung.")
    ghi("")
    ghi("  ⚠️ Doc ket qua nay dung pham vi: no chung minh CONG khong ro suat.")
    ghi("     No KHONG noi gi ve tien cua khach -- duong tinh tien nam o may A")
    ghi("     va can mot khoa /api/v1 that de do, thu ma phien nay khong co.")

    Path(r"H:\LTT_LLM\work\ket_luong_treo.txt").write_text(
        "\n".join(RA), encoding="utf-8")
    ghi("DA LUU: H:\\LTT_LLM\\work\\ket_luong_treo.txt")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

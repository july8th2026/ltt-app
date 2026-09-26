"""⛔ CONG CU NAY KHONG CHAY DUOC LENH. Giu lai lam bang chung, dung tin no.

## 🔴 Ban goc khai mot dieu SAI, va khai rat chac

Docstring cu viet: *"termproxy la mot shell **root** tren node. **Da thu that**"*.
Do 26/09/2026 — doc dung 8 giay dau cua websocket, thu ma ban goc `ra.clear()` roi
bo di ma khong ai xem:

    'OKpve login: '

⇒ Termproxy cua NODE cho mot man hinh **dang nhap**, khong phai mot shell. Moi dong
  lenh gui vao bi go vao cho **ten dang nhap**, roi no cho mat khau — mat khau root
  cua host thi ta khong co. Nen cong cu **chua bao gio chay duoc mot lenh nao**.

Vi sao khong ai thay: ban goc thoat vong doc **ngay khi thay dau hieu ket thuc lan
dau** — tuc ngay o dong terminal VONG LAI lenh minh vua gui — roi in phan truoc do.
Ket qua la no in lai dung dong lenh, trong y nhu mot dau ra rong. Toi sua vong doc
(doi dau hieu lan thu HAI) va van khong co gi: luc ay moi ra la khong co shell.

⚠️ No con gay hai theo mot huong khac: ban ra soat 25/09 xep cong cu nay la mot
   **rui ro an ninh** ("shell root tren node, khong hoi lai, khong hoan tac"). Rui
   ro do **khong ton tai**. Mot loi khai sai trong tai lieu tao ra ca mot muc rui ro
   gia — va no lam nguoi doc sau bot chu y cho nhung rui ro that.

## Muon co shell that thi lam gi

- Hau het viec ha tang lam duoc qua REST API. Tai ISO chang han: `download-url` doi
  `Sys.Modify` tren `/`, nhung `upload` chi doi `Datastore.AllocateTemplate` ⇒ tai
  ve may minh roi `curl -F` len (da lam duoc 26/09; `urllib` bi ngat giua duong).
- Viec that su can shell: can mat khau root cua host hoac mot khoa SSH them vao
  node — ca hai la viec cua chu du an.

⇒ Tep nay giu lai vi no ghi mot **ket luan sai da tung duoc tin**, va vi vong doc
  websocket trong no dung duoc cho console cua **GUEST** (`qemu/<vmid>/termproxy` —
  console that cua may khach, khong phai man hinh dang nhap cua host).
"""
from __future__ import annotations

import argparse
import asyncio
import io
import os
import pathlib
import ssl
import sys
import urllib.parse
import warnings

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
warnings.filterwarnings("ignore")

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)

#: Dau hieu bao "lenh da chay xong". Termproxy la mot shell tuong tac — khong co
#: ma thoat, khong co ranh gioi giua hai lenh. Khong in mot dau hieu rieng thi
#: khong biet luc nao doc xong, va ket qua se bi cat ngang mot cach ngau nhien.
XONG = "___LTT_XONG___"


def _nap_env() -> None:
    goc = pathlib.Path(__file__).resolve().parents[1]
    for tep in (r"C:\LTTPlatform\secrets\app.env", str(goc / "secrets" / "app.env")):
        p = pathlib.Path(tep)
        if not p.exists():
            continue
        for d in p.read_text(encoding="utf-8-sig").splitlines():
            if "=" in d and not d.strip().startswith("#"):
                k, v = d.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


async def _chay(kich_ban: str, cho_giay: float) -> str:
    import websockets

    from apps.vps.services.proxmox import client_tu_moi_truong

    c = client_tu_moi_truong()
    node = c.config.node
    ve = c._goi("POST", f"/nodes/{node}/termproxy") or {}
    goc = str(c.config.base_url).rstrip("/").replace("https://", "wss://", 1)
    url = (f"{goc}/api2/json/nodes/{node}/vncwebsocket"
           f"?port={ve['port']}"
           f"&vncticket={urllib.parse.quote(str(ve['ticket']), safe='')}")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    hdr = {"Authorization":
           f"PVEAPIToken={c.config.token_id}={c.config.token_secret}"}

    ra: list[str] = []
    async with websockets.connect(url, ssl=ctx, additional_headers=hdr,
                                  subprotocols=["binary"], open_timeout=30) as ws:
        # Termproxy doi mot dong `user:ticket` truoc khi noi shell vao.
        await ws.send(f"{ve['user']}:{ve['ticket']}\n")

        async def doc(giay: float, can: int = 1) -> None:
            """Doc toi khi thay dau hieu `can` lan, hoac het gio.

            🔴 `can=2` cho luot chay lenh, va do la ca sua 26/09/2026: termproxy
               **VONG LAI** ca dong lenh, gom ca `echo ___LTT_XONG___`. Ban cu thoat
               ngay khi thay dau hieu LAN DAU — tuc ngay o dong vong lai, **truoc
               khi lenh kip chay**. Ket qua: moi lenh doc tra ve dung mot dong lenh
               + chu "echo", va nguoi dung ket luan "cong cu khong tra dau ra".
            """
            het = asyncio.get_event_loop().time() + giay
            while asyncio.get_event_loop().time() < het:
                try:
                    m = await asyncio.wait_for(ws.recv(), timeout=0.6)
                except asyncio.TimeoutError:
                    if "".join(ra).count(XONG) >= can:
                        return
                    continue
                ra.append(m.decode("utf-8", "replace")
                          if isinstance(m, bytes) else str(m))
                if "".join(ra).count(XONG) >= can:
                    return

        await doc(3.0)
        ra.clear()
        lenh = f"{kich_ban}\necho {XONG}\n"
        await ws.send(f"0:{len(lenh)}:{lenh}")
        await doc(cho_giay, can=2)
    return "".join(ra)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("lenh", nargs="?", help="doan bash chay tren node")
    ap.add_argument("--tep", help="doc doan bash tu mot tep")
    ap.add_argument("--cho", type=float, default=90.0, help="cho toi da (giay)")
    args = ap.parse_args()

    kich_ban = args.lenh or ""
    if args.tep:
        kich_ban = pathlib.Path(args.tep).read_text(encoding="utf-8")
    if not kich_ban.strip():
        print("Chua co lenh nao.")
        return 2

    _nap_env()
    ra = asyncio.run(_chay(kich_ban, args.cho))
    # 🔴 Dau hieu xuat hien HAI lan, va ban cu lay lan dau nen no in ra dung
    #    DONG LENH chu khong phai dau ra:
    #
    #      <termproxy VONG LAI ca dong lenh, gom ca `echo ___LTT_XONG___`>
    #      <dau ra that>
    #      ___LTT_XONG___          <- dau hieu THAT
    #
    #    `split(XONG)[0]` cat o lan VONG LAI => tra ve phan truoc no, tuc chinh
    #    doan lenh. Do 26/09/2026: moi lenh doc deu tra ve dung mot dong lenh +
    #    chu "echo", va toi da ket luan "cong cu khong tra dau ra" — no co tra,
    #    chi bi cat sai cho.
    #
    # ⇒ Doan GIUA hai dau hieu moi la dau ra. Con mot dau hieu (shell khong vong
    #   lai) thi doan dau la dau ra.
    phan = ra.split(XONG)
    if len(phan) < 3:
        # Chi MOT dau hieu = chi co dong VONG LAI; lenh chua he chay.
        print("KHONG CHAY DUOC LENH. Termproxy cua node cho mot man hinh "
              "dang nhap ('pve login:'), khong phai shell — xem docstring "
              "dau tep.", file=sys.stderr)
        print("  (nhan duoc: " + repr(ra[:120]) + ")", file=sys.stderr)
        return 3
    print(phan[1].replace(chr(13) + chr(10), chr(10)).strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

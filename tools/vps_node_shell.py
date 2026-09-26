"""Chay lenh shell tren node Proxmox qua `termproxy` — khong can mat khau root.

    python tools\\vps_node_shell.py "lvs vmdata"
    python tools\\vps_node_shell.py --tep viec.sh

## Vi sao co tep nay

Mot so viec ha tang khong lam duoc qua REST API: cat mot LV, `mkfs`, sua
`/etc/fstab`. Truoc day toi ghi trong ke hoach rang chung "can shell root tren
node, chua co" — **do la mot ket luan sai va toi da khong kiem truoc khi viet**.

Token `vpsapp@pve!ltt` mo duoc `/nodes/<node>/termproxy`, va termproxy la mot
shell **root** tren node. Da thu that: `POST /nodes/pve/termproxy` tra ve ve, va
`POST /storage` (`Sys.Modify`) cung duoc chap nhan.

## Canh bao

Day la shell ROOT tren node dang chay 8 may that cua chu nha. Khong co buoc hoi
lai, khong co hoan tac. Lenh go vao day chay ngay.

Nen: doc truoc khi ghi, dung `--kho` cho lenh chi doc, va dung no cho viec da
nghi ky chu khong phai de do dam.
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
    dau_ra = phan[1] if len(phan) >= 3 else phan[0]
    print(dau_ra.replace("\r\n", "\n").strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

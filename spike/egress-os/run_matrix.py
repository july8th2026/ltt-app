"""Driver spike p6b: chay ma tran (launcher x piece x mode) va in JSON ket qua.

Launcher = cach KHOI CHAY tien trinh khong tin cay. Piece = kieu ma doc hai.
Mode = kieu egress. Moi o tra ve REACHED / BLOCKED / SKIP / LOI.

    python run_matrix.py --launcher L0_doi_chung
    python run_matrix.py --launcher L2_appcontainer_none
    python run_matrix.py --launcher L2_appcontainer_net

Ket qua gom vao ket_qua/<launcher>.json.
"""

import argparse
import json
import os
import pathlib
import socket
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
STAGE = os.environ.get("P6B_STAGE", "")
LAUNCHER_PY = str(HERE / "launch_appcontainer.py")

PIECES = {
    "truc_tiep": "probe.js",
    "spawn_node_con": "piece-spawn-node.js",
    "spawn_curl_con": "piece-spawn-curl.js",
}
MODES = ["tcp_host", "tcp_rawip", "tcp_ipv6", "udp"]


def giai_ten():
    ip4 = ip6 = ""
    try:
        ip4 = socket.getaddrinfo("example.com", 80, socket.AF_INET)[0][4][0]
    except Exception:
        pass
    try:
        ip6 = socket.getaddrinfo("example.com", 80, socket.AF_INET6)[0][4][0]
    except Exception:
        pass
    return ip4, ip6


def phan_xu(text):
    t = (text or "").strip()
    last = ""
    for line in t.splitlines():
        line = line.strip()
        if line.startswith(("REACHED", "BLOCKED", "SKIP", "CHILD_")):
            last = line
    if not last:
        return "LOI", t.replace("\n", " | ")[:200]
    body = last[len("CHILD_"):] if last.startswith("CHILD_") else last
    if body.startswith("REACHED"):
        return "REACHED", last
    if body.startswith("BLOCKED"):
        return "BLOCKED", last
    return "SKIP", last


def chay_o(launcher, piece_file, mode, ip4, ip6):
    env = dict(os.environ)
    env.update({"MODE": mode, "IP4": ip4, "IP6": ip6})

    if launcher == "L0_doi_chung":
        exe = os.path.join(STAGE, "node.exe") if STAGE else "node"
        cmd = [exe, "--preserve-symlinks-main", os.path.join(STAGE or str(HERE), piece_file)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=90, env=env)
        return phan_xu((r.stdout or "") + "\n" + (r.stderr or ""))

    if launcher == "L1_fw_localuser" or launcher == "L1_fw_program":
        # Luat tuong lua da duoc dat SAN o ngoai (xem bao cao); o day chi chay nhu L0.
        exe = os.path.join(STAGE, "node.exe")
        cmd = [exe, "--preserve-symlinks-main", os.path.join(STAGE, piece_file)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=90, env=env)
        return phan_xu((r.stdout or "") + "\n" + (r.stderr or ""))

    if launcher.startswith("L2_appcontainer"):
        caps = "internetClient" if launcher.endswith("_net") else "none"
        ten = "ltt-p6b-net" if caps != "none" else "ltt-p6b-spike"
        ra = os.path.join(STAGE, f"out_{launcher}_{piece_file}_{mode}.txt")
        cmd = [
            sys.executable, LAUNCHER_PY, "--ten", ten, "--caps", caps, "--ra", ra,
            "--cho-ms", "40000",
            "--", os.path.join(STAGE, "node.exe"), "--preserve-symlinks-main",
            os.path.join(STAGE, piece_file),
        ]
        # DEVNULL chu KHONG phai pipe: tien trinh trong AppContainer ke thua moi handle
        # co the ke thua cua launcher, KE CA dau ra pipe. Neu no treo, `capture_output`
        # se ket o buoc doc pipe ngay ca khi launcher da thoat (da dinh mot lan o 24/09).
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=120, env=env)
        try:
            return phan_xu(pathlib.Path(ra).read_text(errors="replace"))
        except Exception as e:
            return "LOI", f"khong doc duoc {ra}: {e}"

    raise SystemExit(f"launcher chua biet: {launcher}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--launcher", required=True)
    a = p.parse_args()

    if not STAGE:
        raise SystemExit("thieu bien moi truong P6B_STAGE (thu muc dan dung co node.exe + *.js)")

    ip4, ip6 = giai_ten()
    rows = []
    for piece_name, piece_file in PIECES.items():
        for mode in MODES:
            try:
                verdict, detail = chay_o(a.launcher, piece_file, mode, ip4, ip6)
            except subprocess.TimeoutExpired:
                verdict, detail = "BLOCKED", "DRIVER_TIMEOUT"
            except Exception as e:
                verdict, detail = "LOI", str(e)[:200]
            rows.append({"launcher": a.launcher, "piece": piece_name, "mode": mode,
                         "verdict": verdict, "detail": detail})
            print(f"{a.launcher:28} {piece_name:16} {mode:11} -> {verdict:8} {detail[:70]}", flush=True)

    out_dir = HERE / "ket_qua"
    out_dir.mkdir(exist_ok=True)
    (out_dir / f"{a.launcher}.json").write_text(
        json.dumps({"ip4": ip4, "ip6": ip6, "rows": rows}, indent=2), encoding="utf-8"
    )
    print(f"\nDa ghi {out_dir / (a.launcher + '.json')}")


if __name__ == "__main__":
    main()

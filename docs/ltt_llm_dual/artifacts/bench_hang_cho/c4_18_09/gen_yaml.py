"""Sinh bien the llama-swap.yaml cho C4 tu ban goc (byte), chi doi dong -np / -c / -b -ub trong tung khoi model.

    python gen_yaml.py goc.yaml ra.yaml --m38 np=4,c=221184 --m35 np=5
Giu nguyen ket dong, khong BOM, kiem ASCII.
"""
import argparse
import re
import sys


def khoi(lines, ten):
    bd = next(i for i, l in enumerate(lines) if l.rstrip("\r\n") == "  %s:" % ten)
    kt = next(i for i in range(bd + 1, len(lines))
              if re.match(r"^  [a-z0-9-]+:\s*$", lines[i].rstrip("\r\n")) or re.match(r"^[a-z]", lines[i]))
    return bd, kt


def sua(lines, ten, spec):
    if not spec:
        return
    kv = dict(x.split("=") for x in spec.split(","))
    bd, kt = khoi(lines, ten)
    doi = {}
    for i in range(bd, kt):
        l = lines[i]
        eol = l[len(l.rstrip("\r\n")):]
        s = l.rstrip("\r\n")
        m = re.match(r"^(\s+)-np (\d+)$", s)
        if m and "np" in kv:
            lines[i] = "%s-np %s%s" % (m.group(1), kv["np"], eol); doi["np"] = doi.get("np", 0) + 1
        m = re.match(r"^(\s+)-c (\d+)$", s)
        if m and "c" in kv:
            lines[i] = "%s-c %s%s" % (m.group(1), kv["c"], eol); doi["c"] = doi.get("c", 0) + 1
        m = re.match(r"^(\s+)-b (\d+) -ub (\d+)$", s)
        if m and ("b" in kv or "ub" in kv):
            lines[i] = "%s-b %s -ub %s%s" % (m.group(1), kv.get("b", m.group(2)), kv.get("ub", m.group(3)), eol)
            doi["b"] = doi.get("b", 0) + 1
    need = {"np": "np", "c": "c"}
    for k in kv:
        if k in ("b", "ub"):
            if doi.get("b") != 1:
                # them dong -b/-ub sau dong -np neu model chua co
                j = next(i for i in range(bd, kt) if re.match(r"^\s+-np \d+\s*$", lines[i]))
                ind = re.match(r"^(\s+)", lines[j]).group(1)
                eol = lines[j][len(lines[j].rstrip("\r\n")):]
                lines.insert(j + 1, "%s-b %s -ub %s%s" % (ind, kv.get("b", "2048"), kv.get("ub", "512"), eol))
                doi["b"] = 1
        elif doi.get(need[k]) != 1:
            sys.exit("khong thay dong %s trong %s (%s)" % (k, ten, doi))
    print(ten, kv, "OK")


ap = argparse.ArgumentParser()
ap.add_argument("goc")
ap.add_argument("ra")
ap.add_argument("--m38", default="")
ap.add_argument("--m35", default="")
a = ap.parse_args()
raw = open(a.goc, "rb").read()
assert not raw.startswith(b"\xef\xbb\xbf")
lines = raw.decode("ascii").splitlines(keepends=True)
sua(lines, "qwen38-api", a.m38)
sua(lines, "qwen35-api", a.m35)
out = "".join(lines).encode("ascii")
open(a.ra, "wb").write(out)
print("wrote", a.ra, len(out))

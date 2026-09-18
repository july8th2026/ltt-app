"""Sinh bien the llama-swap.yaml cho lane B (18/09 toi) tu ban goc (byte). Mo rong c4_18_09/gen_yaml.py:
them `spec=0` (bo dong `--spec-type draft-mtp ...` cua khoi model - E3: khong MTP).

    python gen_yaml_laneb.py goc.yaml ra.yaml --m38 b=1024,ub=512 --m35 b=1024,ub=512
    python gen_yaml_laneb.py goc.yaml ra.yaml --m38 np=1,spec=0
Giu nguyen ket dong, khong BOM, kiem ASCII; in so dong doi de doi chieu.
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
    xoa = []
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
        if re.match(r"^\s+--spec-type \S+", s) and kv.get("spec") == "0":
            xoa.append(i); doi["spec"] = doi.get("spec", 0) + 1
    for i in reversed(xoa):
        del lines[i]
    if ("b" in kv or "ub" in kv) and doi.get("b") != 1:
        j = next(i for i in range(bd, kt) if re.match(r"^\s+-np \d+\s*$", lines[i]))
        ind = re.match(r"^(\s+)", lines[j]).group(1)
        eol = lines[j][len(lines[j].rstrip("\r\n")):]
        lines.insert(j + 1, "%s-b %s -ub %s%s" % (ind, kv.get("b", "2048"), kv.get("ub", "512"), eol))
        doi["b"] = 1
    for k in ("np", "c", "spec"):
        if k in kv and doi.get(k) != 1:
            sys.exit("khong thay dong %s trong %s (%s)" % (k, ten, doi))
    print(ten, kv, "OK", doi)


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

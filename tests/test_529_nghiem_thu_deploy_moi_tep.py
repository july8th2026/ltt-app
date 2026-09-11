import hashlib, importlib.util, pathlib
GOC = pathlib.Path(__file__).resolve().parents[1]


def _m():
    s = importlib.util.spec_from_file_location("ntd", GOC / "tools" / "nghiem_thu_deploy.py")
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def test_bam_git_khop_git():
    assert _m().bam_git(b"abc\n") == hashlib.sha1(b"blob 4\0abc\n").hexdigest()


def test_so_ca_JS_va_TEMPLATE():
    m = _m()
    tc = {"server/static/voice.js": m.bam_git(b"a"), "apps/x/t.html": m.bam_git(b"b")}
    ra = m.so_sanh(tc, {"server/static/voice.js": b"KHAC", "apps/x/t.html": b"b",
                        "apps/x/moi.css": b"c"})
    assert ra["lech"] == ["server/static/voice.js"]
    assert ra["thua"] == ["apps/x/moi.css"] and ra["thieu"] == []

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


def test_thua_duoi_mau_DA_KHAI_khong_tinh_la_loi():
    m = _m()
    tc = {"apps/x/t.py": m.bam_git(b"a")}
    ra = m.so_sanh(tc, {"apps/x/t.py": b"a",
                        "apps/upscalevideo/vendor/engine/models/x.bin": b"Z"},
                   van_chuyen=[r"apps\*\vendor"])
    assert ra["thua"] == []
    assert ra["van_chuyen"] == ["apps/upscalevideo/vendor/engine/models/x.bin"]


def test_thua_KHONG_duoc_khai_van_that_bai():
    m = _m()
    tc = {"apps/x/t.py": m.bam_git(b"a")}
    ra = m.so_sanh(tc, {"apps/x/t.py": b"a", "apps/x/rac.tmp": b"Z"},
                   van_chuyen=[r"apps\*\vendor"])
    assert ra["thua"] == ["apps/x/rac.tmp"]
    assert ra["van_chuyen"] == []


def test_doc_van_chuyen_doc_duoc_tu_setup_that():
    m = _m()
    assert r"apps\*\vendor" in m.doc_van_chuyen()


def test_mau_KHONG_khop_doan_moi_MOT_PHAN():
    """Fix round 2 — mau dang Windows `apps/*/vendor` phai khop THEO DOAN, khong khop
    chuoi con. Ba duong gan giong deu KHONG duoc khai; chi duong thuc su
    nam duoi thu muc `vendor/` moi duoc khai."""
    m = _m()
    tc = {"apps/x/t.py": m.bam_git(b"a")}
    tren_may = {
        "apps/x/t.py": b"a",
        "apps/upscalevideo/vendor_x.py": b"Z1",
        "apps/upscalevideo/vendor_extra/readme.txt": b"Z2",
        "apps/other/some_vendor_thing/file.bin": b"Z3",
        "apps/upscalevideo/vendor/engine/models/x.bin": b"Z4",
    }
    ra = m.so_sanh(tc, tren_may, van_chuyen=[r"apps\*\vendor"])
    assert ra["van_chuyen"] == ["apps/upscalevideo/vendor/engine/models/x.bin"]
    assert ra["thua"] == [
        "apps/other/some_vendor_thing/file.bin",
        "apps/upscalevideo/vendor_extra/readme.txt",
        "apps/upscalevideo/vendor_x.py",
    ]


def test_doc_van_chuyen_bo_qua_moi_gia_trong_chu_thich(tmp_path):
    """Fix round 2 — mot cau van/chu thich nhac toi `$VAN_CHUYEN = @('apps')`
    PHAI bi bo qua; chi khai bao THAT (ngoai chu thich) moi duoc doc."""
    m = _m()
    gia = tmp_path / "gia_2-cai-dat.ps1"
    gia.write_text("# vi du cu (KHONG dung nua): $VAN_CHUYEN = @('apps')\n$khac = 1\n$VAN_CHUYEN = @(\n    'apps\\*\\vendor',\n    'yolov8n.pt'\n)\n", encoding="ascii")
    assert m.doc_van_chuyen(gia) == ['apps\\*\\vendor', "yolov8n.pt"]


def test_doc_van_chuyen_khong_doc_duoc_NEM_LOI_THAT(tmp_path):
    """Fix round 2 — khong tim thay `$VAN_CHUYEN` phai NEM LOI, khong duoc
    lang le tra ve danh sach rong (an toan gia)."""
    m = _m()
    gia = tmp_path / "khong_co_van_chuyen.ps1"
    gia.write_text("$khac = 1\n", encoding="ascii")
    try:
        m.doc_van_chuyen(gia)
        assert False, "phai nem RuntimeError"
    except RuntimeError:
        pass

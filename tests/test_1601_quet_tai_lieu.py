import json, subprocess, sys
from pathlib import Path


def chay(tmp_path, noi_dung, tu_dien):
    (tmp_path / "docs").mkdir()
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "co_that.py").write_text("x", encoding="utf-8")
    (tmp_path / "docs" / "a.md").write_text(noi_dung, encoding="utf-8")
    (tmp_path / "tu_dien.md").write_text(tu_dien, encoding="utf-8")
    out = tmp_path / "o.json"
    subprocess.run([sys.executable, str(Path("tools/quet_tai_lieu.py").resolve()), "docs",
                    "--goc", str(tmp_path), "--tu-dien", str(tmp_path / "tu_dien.md"),
                    "--json", str(out)], check=True, cwd=tmp_path)
    return json.loads(out.read_text(encoding="utf-8"))


def test_bat_tham_chieu_chet_va_bo_qua_tham_chieu_song(tmp_path):
    kq = chay(tmp_path, "chạy `tools/co_that.py` rồi `tools/da_xoa.py`\n", "")
    assert [r["mau"] for r in kq if r["loai"] == "CHET"] == ["tools/da_xoa.py"]


def test_bat_thuat_ngu_da_bi_thay(tmp_path):
    tu_dien = "| cũ | mới | nguồn |\n|---|---|---|\n| canonical integrator | chính phiên tự gộp main | hợp đồng §6 |\n"
    kq = chay(tmp_path, "chờ canonical integrator duyệt\n", tu_dien)
    assert kq[0]["loai"] == "THAY" and kq[0]["goi_y"] == "chính phiên tự gộp main"

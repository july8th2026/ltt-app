import json, subprocess, sys
from pathlib import Path


def chay(tmp_path, noi_dung, tu_dien):
    (tmp_path / "docs").mkdir(exist_ok=True)
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


def test_bo_dong_da_ghi_ngoai_le_theo_tep_va_mau(tmp_path):
    (tmp_path / "docs" / "_luutru").mkdir(parents=True)
    (tmp_path / "docs" / "_luutru" / "NGOAI_LE_QUET.md").write_text(
        "| tệp | dòng | lý do |\n|---|---|---|\n| `docs/a.md` | 1 | bảng người đọc, máy bỏ qua |\n\n"
        "| tệp | mẫu | lý do |\n|---|---|---|\n| `docs/a.md` | `tools/ngoai_kho/*` | kho khác |\n",
        encoding="utf-8")
    kq = chay(tmp_path, "`tools/ngoai_kho/x.py` và `tools/da_xoa.py`\n", "")
    assert [r["mau"] for r in kq] == ["tools/da_xoa.py"]

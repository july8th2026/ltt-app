"""test_535 — trọng số YOLO nằm NGOÀI `app\\` để không bị tải lại sau mỗi deploy.

🔴 16/09/2026: `yolov8s.pt` (tier chất lượng cao của taoclipngan) không nằm trong danh
sách vận chuyển của deploy; ultralytics tải 21,5 MB từ GitHub vào cwd = `C:\\LTTPlatform\\app`
— thư mục mỗi lần deploy xoá sạch — nên job đầu tiên sau MỖI deploy tải lại.
"""
from __future__ import annotations

from pathlib import Path

from cutclipshort.adapters.yolo import YOLOAdapter

f = YOLOAdapter._persistent_or_name


def test_ban_van_chuyen_trong_cwd_duoc_uu_tien(tmp_path):
    (tmp_path / "yolov8n.pt").write_bytes(b"x")
    assert f("yolov8n.pt", {"LTT_DATA_DIR": str(tmp_path / "data")}, tmp_path) == "yolov8n.pt"


def test_khong_co_trong_cwd_thi_tro_ve_thu_muc_ben_duoi_data(tmp_path):
    ra = f("yolov8s.pt", {"LTT_DATA_DIR": str(tmp_path / "data")}, tmp_path / "app")
    assert Path(ra) == tmp_path / "data" / "models" / "yolo" / "yolov8s.pt"
    assert Path(ra).is_absolute() and Path(ra).parent.is_dir()


def test_bien_rieng_thang_data_dir(tmp_path):
    ra = f("yolov8s.pt", {"LTT_DATA_DIR": str(tmp_path / "data"),
                          "LTT_YOLO_WEIGHTS_DIR": str(tmp_path / "w")}, tmp_path)
    assert Path(ra) == tmp_path / "w" / "yolov8s.pt"


def test_khong_co_env_nen_tang_giu_hanh_vi_cu(tmp_path):
    assert f("yolov8s.pt", {}, tmp_path) == "yolov8s.pt"


def test_ultralytics_tai_VAO_duong_tuyet_doi(tmp_path, monkeypatch):
    """Đối chứng với mã ultralytics THẬT đang cài: đường tuyệt đối chưa tồn tại ⇒
    `safe_download(file=<đúng đường đó>)`, không phải cwd."""
    import pytest
    dl = pytest.importorskip("ultralytics.utils.downloads")
    goi = {}
    monkeypatch.setattr(dl, "safe_download", lambda url, file, **k: goi.update(url=url, file=str(file)))
    dich = tmp_path / "data" / "models" / "yolo" / "yolov8s.pt"
    dl.attempt_download_asset(str(dich))
    assert goi["file"] == str(dich)
    assert goi["url"].endswith("/yolov8s.pt")
